"""
lstm_engine.py
==============

LSTM / Transformer 序列模型引擎（骨幹版）。

設計原則（參考 docs/FEATURE_LIBRARY_FIRST_PRINCIPLES_REDESIGN.md 第 12 節）：
- 輸入：連續原始 OHLCV K 線（來自 kline_cache.h5），或已計算特徵的 DataFrame
- 輸出：每個時間步的分類機率 prob (0~1)，與 XGBoostAnalyzer.predict_proba 接口相同
- Mode C 用途：全時間序列滾動預測（3.5M 樣本）
- Mode A/D 用途：事件前兆 sliding window（14,600 次 × window=48 根 1h K線）

依賴：
- torch（lazy import，不影響系統啟動）
- numpy, pandas（已有）

未來優化路徑：
  V1：2 層 LSTM + Sigmoid（本檔案實作的骨幹）
  V2：加入 Attention Mechanism
  V3：Transformer Encoder（multi-head self-attention）
  V4：Optuna 超參數搜索（接入現有 OptimizationTaskService）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 資料結構定義
# ─────────────────────────────────────────────

@dataclass
class SequenceModelConfig:
    """LSTM/Transformer 模型設定"""
    # 序列參數
    window_size: int = 48          # 滑動窗口長度（根 K 線数）
    stride: int = 1                # 滑動步幅（1 = 密集，window_size = 不重疊）
    # 模型架構
    hidden_size: int = 128         # LSTM 隱藏層維度
    num_layers: int = 2            # LSTM 層數
    dropout: float = 0.2           # Dropout 比率
    bidirectional: bool = False    # 是否雙向 LSTM（回測場景須 False，避免未來洩漏）
    # 訓練參數
    epochs: int = 50
    batch_size: int = 256
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    # 其他
    random_seed: int = 42
    device: str = "auto"           # "auto" | "cpu" | "mps" | "cuda"


@dataclass
class SequenceModelResult:
    """訓練結果"""
    train_loss_history: List[float] = field(default_factory=list)
    val_loss_history: List[float] = field(default_factory=list)
    best_val_loss: float = float("inf")
    best_epoch: int = 0
    train_auc: float = 0.0
    val_auc: float = 0.0
    n_train_samples: int = 0
    n_val_samples: int = 0
    n_features: int = 0
    window_size: int = 0


# ─────────────────────────────────────────────
# 主引擎
# ─────────────────────────────────────────────

class LSTMEngine:
    """
    LSTM 序列模型引擎

    與 XGBoostAnalyzer 保持相同的關鍵接口：
    - train_model(X, y) -> SequenceModelResult
    - predict_proba(X)  -> np.ndarray (shape: [n_samples])

    X 接受兩種格式：
    - 2D: (n_samples, n_features)  → 自動 reshape 為 (n_windows, window_size, n_features)
    - 3D: (n_windows, window_size, n_features)  → 直接使用

    典型用途：
    1. 事件前兆模式（Mode A）：X.shape = (14600, 48, 30)
       window_size=48 根 1h K線，top-30 IC 特徵
    2. 模式 C 連續預測：X.shape = (3500000, 48, features)
       用 build_sliding_window(df_features) 預先切割
    """

    def __init__(self, config: Optional[SequenceModelConfig] = None):
        self.config = config or SequenceModelConfig()
        self._model = None          # torch.nn.Module（lazy init）
        self._device = None         # torch.device（lazy init）
        self._feature_size: Optional[int] = None
        self._is_trained = False

    # ── 公開接口 ─────────────────────────────

    def build_sliding_window(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        label_col: Optional[str] = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        將連續 DataFrame 切割成 sliding window 張量。

        Args:
            df: 連續時間序列 DataFrame（來自 kline_cache.h5）
            feature_cols: 要使用的特徵欄位名稱
            label_col:    標籤欄位名稱（為 None 時只回傳 X）

        Returns:
            X: np.ndarray, shape (n_windows, window_size, n_features), dtype float32
            y: np.ndarray or None, shape (n_windows,), dtype int32
        """
        ws = self.config.window_size
        stride = self.config.stride
        features = df[feature_cols].values.astype(np.float32)
        n = len(features)

        # 計算窗口起始索引
        starts = np.arange(0, n - ws, stride)
        if len(starts) == 0:
            raise ValueError(
                f"資料長度 {n} 小於 window_size {ws}，無法切割窗口。"
            )

        X = np.stack([features[s : s + ws] for s in starts], axis=0)
        logger.info(
            f"build_sliding_window: {n} rows → {len(starts)} windows "
            f"(window={ws}, stride={stride}, features={len(feature_cols)})"
        )

        if label_col is None:
            return X, None

        labels = df[label_col].values
        y = np.array([labels[s + ws - 1] for s in starts], dtype=np.int32)
        return X, y

    def train_model(
        self,
        X: np.ndarray,
        y: np.ndarray,
        val_ratio: float = 0.2,
    ) -> SequenceModelResult:
        """
        訓練 LSTM 模型。

        Args:
            X: 特徵張量。
               - 2D (n_samples, n_features)：自動 reshape，需要 n_samples % window_size == 0 或先用 build_sliding_window
               - 3D (n_windows, window_size, n_features)：直接使用
            y: 標籤陣列 (n_windows,)，二元分類 0/1
            val_ratio: 驗證集比例

        Returns:
            SequenceModelResult
        """
        torch = self._import_torch()
        X3d = self._ensure_3d(X)
        n_windows, ws, n_features = X3d.shape
        self._feature_size = n_features

        # ── 切分訓練 / 驗證（時序不打亂，保持時間順序）──
        split = int(n_windows * (1 - val_ratio))
        X_train, X_val = X3d[:split], X3d[split:]
        y_train, y_val = y[:split], y[split:]

        device = self._get_device(torch)
        model = self._build_model(torch, n_features)
        model.to(device)

        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        # 對類別不平衡做加權（正例通常較少）
        pos_weight_val = float((y_train == 0).sum()) / max((y_train == 1).sum(), 1)
        criterion = torch.nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor([pos_weight_val], device=device)
        )

        train_loader = self._make_loader(torch, X_train, y_train, shuffle=False)
        result = SequenceModelResult(
            n_train_samples=len(y_train),
            n_val_samples=len(y_val),
            n_features=n_features,
            window_size=ws,
        )

        best_state = None
        for epoch in range(1, self.config.epochs + 1):
            train_loss = self._train_epoch(torch, model, train_loader, optimizer, criterion, device)
            val_loss, val_auc = self._eval_epoch(torch, model, X_val, y_val, criterion, device)

            result.train_loss_history.append(train_loss)
            result.val_loss_history.append(val_loss)

            if val_loss < result.best_val_loss:
                result.best_val_loss = val_loss
                result.best_epoch = epoch
                result.val_auc = val_auc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    f"Epoch {epoch:3d}/{self.config.epochs} | "
                    f"train_loss={train_loss:.4f} | val_loss={val_loss:.4f} | val_auc={val_auc:.4f}"
                )

        if best_state is not None:
            model.load_state_dict(best_state)

        self._model = model
        self._device = device
        self._is_trained = True
        logger.info(
            f"訓練完成：best_epoch={result.best_epoch}, best_val_loss={result.best_val_loss:.4f}, "
            f"val_auc={result.val_auc:.4f}"
        )
        return result

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        回傳每個窗口的正類機率（與 XGBoostAnalyzer 接口一致）。

        Args:
            X: 2D 或 3D numpy array，格式同 train_model

        Returns:
            np.ndarray, shape (n_windows,), dtype float32, 值域 [0, 1]
        """
        if not self._is_trained or self._model is None:
            raise RuntimeError("模型尚未訓練，請先呼叫 train_model()")

        torch = self._import_torch()
        X3d = self._ensure_3d(X)
        self._model.eval()
        self._model.to(self._device)

        tensor = torch.tensor(X3d, dtype=torch.float32, device=self._device)
        with torch.no_grad():
            logits = self._model(tensor).squeeze(-1)  # (n_windows,)
            probs = torch.sigmoid(logits).cpu().numpy().astype(np.float32)

        return probs

    def save_model(self, path: str) -> None:
        """儲存模型權重至 .pt 檔案（限 data_cache/models/ 目錄）"""
        if not self._is_trained:
            raise RuntimeError("模型尚未訓練")
        torch = self._import_torch()
        safe_path = self._resolve_model_path(path)
        torch.save(
            {
                "model_state": self._model.state_dict(),
                "config": self.config,
                "feature_size": self._feature_size,
            },
            safe_path,
        )
        logger.info(f"模型已儲存：{safe_path}")

    def load_model(self, path: str) -> None:
        """從 .pt 檔案載入模型權重"""
        torch = self._import_torch()
        safe_path = self._resolve_model_path(path)
        checkpoint = torch.load(safe_path, map_location="cpu")
        self.config = checkpoint["config"]
        self._feature_size = checkpoint["feature_size"]
        device = self._get_device(torch)
        model = self._build_model(torch, self._feature_size)
        model.load_state_dict(checkpoint["model_state"])
        model.to(device)
        self._model = model
        self._device = device
        self._is_trained = True
        logger.info(f"模型已載入：{safe_path}")

    # ── 私有工具 ─────────────────────────────

    @staticmethod
    def _import_torch():
        try:
            import torch  # noqa: PLC0415
            return torch
        except ImportError as exc:
            raise ImportError(
                "LSTMEngine 需要 PyTorch。請執行：pip install torch"
            ) from exc

    def _get_device(self, torch):
        if self._device is not None:
            return self._device
        if self.config.device == "auto":
            if torch.backends.mps.is_available():
                dev = torch.device("mps")
            elif torch.cuda.is_available():
                dev = torch.device("cuda")
            else:
                dev = torch.device("cpu")
        else:
            dev = torch.device(self.config.device)
        logger.info(f"LSTMEngine 使用裝置：{dev}")
        self._device = dev
        return dev

    def _build_model(self, torch, n_features: int):
        """建立 LSTM PyTorch 模型"""
        cfg = self.config

        class _LSTMModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.lstm = torch.nn.LSTM(
                    input_size=n_features,
                    hidden_size=cfg.hidden_size,
                    num_layers=cfg.num_layers,
                    batch_first=True,
                    dropout=cfg.dropout if cfg.num_layers > 1 else 0.0,
                    bidirectional=cfg.bidirectional,
                )
                out_dim = cfg.hidden_size * (2 if cfg.bidirectional else 1)
                self.dropout = torch.nn.Dropout(cfg.dropout)
                self.fc = torch.nn.Linear(out_dim, 1)

            def forward(self, x):
                # x: (batch, seq_len, features)
                out, _ = self.lstm(x)
                last = out[:, -1, :]          # 只取最後一個時間步
                out = self.dropout(last)
                return self.fc(out)            # (batch, 1)

        return _LSTMModel()

    def _make_loader(self, torch, X: np.ndarray, y: np.ndarray, shuffle: bool = False):
        """建立 DataLoader"""
        dataset = torch.utils.data.TensorDataset(
            torch.tensor(X, dtype=torch.float32),
            torch.tensor(y, dtype=torch.float32),
        )
        return torch.utils.data.DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            shuffle=shuffle,
        )

    def _train_epoch(self, torch, model, loader, optimizer, criterion, device) -> float:
        model.train()
        total_loss = 0.0
        for X_batch, y_batch in loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            logits = model(X_batch).squeeze(-1)
            loss = criterion(logits, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item() * len(y_batch)
        return total_loss / len(loader.dataset)

    def _eval_epoch(self, torch, model, X: np.ndarray, y: np.ndarray, criterion, device) -> Tuple[float, float]:
        model.eval()
        with torch.no_grad():
            X_t = torch.tensor(X, dtype=torch.float32, device=device)
            y_t = torch.tensor(y, dtype=torch.float32, device=device)
            logits = model(X_t).squeeze(-1)
            loss = criterion(logits, y_t).item()
            probs = torch.sigmoid(logits).cpu().numpy()

        try:
            from sklearn.metrics import roc_auc_score  # noqa: PLC0415
            auc = float(roc_auc_score(y, probs)) if len(np.unique(y)) > 1 else 0.0
        except ImportError:
            auc = 0.0

        return loss, auc

    @staticmethod
    def _ensure_3d(X: np.ndarray) -> np.ndarray:
        if X.ndim == 3:
            return X.astype(np.float32)
        if X.ndim == 2:
            # (n_samples, n_features) → unsqueeze timestep dimension
            # 假設呼叫者已用 build_sliding_window，這裡只做保護性 reshape
            return X[:, np.newaxis, :].astype(np.float32)
        raise ValueError(f"X 維度必須為 2 或 3，實際為 {X.ndim}")

    @staticmethod
    def _resolve_model_path(path: str) -> Path:
        allowed_root = Path("data_cache/models").resolve()
        target = Path(path).expanduser().resolve()
        if target.suffix != ".pt":
            raise ValueError("LSTM 模型檔案必須為 .pt")
        if allowed_root != target and allowed_root not in target.parents:
            raise ValueError("模型路徑必須在 data_cache/models/ 下")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
