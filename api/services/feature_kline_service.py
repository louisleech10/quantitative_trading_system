"""
Feature Factory 專屬 K 線下載服務

與 batch_download_service.py（案例 K 線）完全獨立。
支援：
  - 任意 symbol 清單（加密貨幣 / 股票代碼 / 期貨合約等）
  - ALL_USDT 快捷鍵 → 展開為 Binance 所有 USDT 交易對
  - 獨立儲存路徑 data_cache/feature_klines/
  - 任意開始/結束日期（非 lookback/forward）
  - 任意多時間框架批次下載
  - 非同步進度追蹤
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from api.core.config import settings
from api.core.logging import get_logger
from momentum.factories import (
    create_binance_provider,
    create_kline_download_service,
    create_kline_storage_manager,
)

logger = get_logger("api.feature_kline_service")


def _sanitize_for_json(obj: Any) -> Any:
    """遞迴將 h5py/numpy 純量轉為 Python 原生型別，確保 FastAPI 可序列化。"""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


# 支援的時間框架清單（與 case_models.py 保持一致）
SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]


class FeatureKlineTaskStatus:
    """Feature K 線下載任務進度物件"""

    def __init__(self, task_id: str, total: int) -> None:
        self.task_id = task_id
        self.status: str = "pending"          # pending | running | completed | failed
        self.total_jobs: int = total           # symbol × timeframe 的組合數
        self.completed_jobs: int = 0
        self.failed_jobs: int = 0
        self.current_symbol: Optional[str] = None
        self.current_timeframe: Optional[str] = None
        self.error_messages: List[str] = []
        self.created_at: datetime = datetime.now(timezone.utc)
        self.finished_at: Optional[datetime] = None

    @property
    def progress_percent(self) -> float:
        if self.total_jobs == 0:
            return 0.0
        return round(self.completed_jobs / self.total_jobs * 100, 1)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "progress_percent": self.progress_percent,
            "current_symbol": self.current_symbol,
            "current_timeframe": self.current_timeframe,
            "error_messages": self.error_messages[-20:],  # 最多顯示最後 20 條錯誤
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class FeatureKlineService:
    """
    Feature Factory 專屬 K 線下載服務

    特點：
    1. 完全不依賴案例清單（CaseStorage）
    2. 使用獨立儲存目錄 data_cache/feature_klines/
    3. 支援 ALL_USDT 展開
    4. 進度追蹤保存在記憶體（與 batch_download_service 相同的模式）
    """

    def __init__(self) -> None:
        # 獨立儲存路徑，與案例 K 線分開
        feature_kline_dir = str(settings.data_cache_path / "feature_klines")
        self._storage = create_kline_storage_manager(cache_dir=feature_kline_dir)
        self._download_service = create_kline_download_service(
            storage_manager=self._storage
        )
        # 必須手動注冊 BinanceProvider，否則 download_klines(source='binance') 會報 UnknownSource
        try:
            binance_provider = create_binance_provider()
            self._download_service.registry.register("binance", binance_provider)
            logger.info("FeatureKlineService: BinanceProvider 已註冊")
        except Exception as exc:
            logger.error(f"FeatureKlineService: 註冊 BinanceProvider 失敗：{exc}", exc_info=True)
            raise
        self._tasks: Dict[str, FeatureKlineTaskStatus] = {}

    # ──────────────────────────────────────
    # Public API
    # ──────────────────────────────────────

    def expand_symbols(self, raw_symbols: List[str]) -> List[str]:
        """
        展開 ALL_USDT 為所有 Binance USDT 交易對，其餘原樣回傳。

        Args:
            raw_symbols: 使用者輸入的 symbol 清單（可含 ALL_USDT）

        Returns:
            展開後的 symbol 清單（已去重）
        """
        result: List[str] = []
        for sym in raw_symbols:
            if sym.upper() == "ALL_USDT":
                usdt_pairs = self._get_all_usdt_pairs()
                result.extend(usdt_pairs)
                logger.info(f"ALL_USDT 展開為 {len(usdt_pairs)} 個交易對")
            else:
                result.append(sym.upper())

        # 去重保留順序
        seen: set = set()
        deduped = [s for s in result if not (s in seen or seen.add(s))]  # type: ignore[func-returns-value]
        return deduped

    def create_download_task(
        self,
        symbols: List[str],
        timeframes: List[str],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> str:
        """
        建立下載任務，回傳 task_id。

        Args:
            symbols: 展開後的 symbol 清單
            timeframes: 時間框架清單
            start_date: 起始日期字串 "YYYY-MM-DD"，None 表示從最早開始
            end_date:   結束日期字串 "YYYY-MM-DD"，None 表示到今天

        Returns:
            task_id (str)
        """
        total_jobs = len(symbols) * len(timeframes)
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = FeatureKlineTaskStatus(task_id, total_jobs)
        logger.info(
            f"建立 Feature K 線下載任務 {task_id}：{len(symbols)} 個標的 × "
            f"{len(timeframes)} 個時間框架 = {total_jobs} 個工作"
        )
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """取得任務進度字典，任務不存在回傳 None。"""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def execute_download(
        self,
        task_id: str,
        symbols: List[str],
        timeframes: List[str],
        start_date: Optional[str],
        end_date: Optional[str],
        force_redownload: bool = False,
    ) -> None:
        """
        同步執行下載（由 FastAPI BackgroundTasks 呼叫）。

        遍歷所有 symbol × timeframe 組合，逐一下載並更新進度。
        """
        task = self._tasks.get(task_id)
        if task is None:
            logger.error(f"任務 {task_id} 不存在")
            return

        task.status = "running"

        # 解析日期範圍 — 必須使用 naive UTC datetime。
        # BinanceProvider.fetch_klines 內部以 datetime.utcfromtimestamp（naive）
        # 建立 current_start，若傳入 aware datetime 則 naive/aware 比較會拋出 TypeError。
        try:
            start_dt: datetime = (
                datetime.strptime(start_date, "%Y-%m-%d")
                if start_date
                else datetime(2017, 1, 1)  # Binance 主網啟動，確保涵蓋所有幣種歷史
            )
            end_dt: datetime = (
                datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                if end_date
                else datetime.utcnow()
            )
        except ValueError as exc:
            task.status = "failed"
            task.error_messages.append(f"日期格式錯誤：{exc}")
            task.finished_at = datetime.now(timezone.utc)
            return

        failed_count = 0
        for symbol in symbols:
            for tf in timeframes:
                task.current_symbol = symbol
                task.current_timeframe = tf
                try:
                    logger.info(f"下載 {symbol} {tf} ({start_dt.date()} → {end_dt.date()}) …")
                    self._download_service.download_klines(
                        source="binance",
                        symbol=symbol,
                        timeframe=tf,
                        start_time=start_dt,
                        end_time=end_dt,
                        save_to_storage=True,
                    )
                    task.completed_jobs += 1
                    logger.info(
                        f"[{task.completed_jobs}/{task.total_jobs}] "
                        f"{symbol} {tf} 下載完成"
                    )
                    # 若指定了 end_date，修剪超出請求範圍的 K 線
                    # append_klines 只合併、不截斷，若之前已有更晚的資料需要主動裁切
                    if end_dt is not None:
                        try:
                            from datetime import timezone as _tz
                            end_ts_sec = int(end_dt.replace(tzinfo=_tz.utc).timestamp())
                            df_current = self._storage.read_klines(symbol, tf, validate_continuity=False)
                            if df_current is not None and len(df_current) > 0:
                                excess_mask = df_current['timestamp'] > end_ts_sec
                                excess_count = int(excess_mask.sum())
                                if excess_count > 0:
                                    df_trimmed = df_current[~excess_mask].copy().reset_index(drop=True)
                                    self._storage.write_klines(symbol, tf, df_trimmed)
                                    logger.info(
                                        f"修剪 {excess_count} 根超出 end_date "
                                        f"{end_dt.date()} 的 K 線：{symbol}/{tf}"
                                    )
                        except Exception as trim_exc:
                            logger.warning(f"修剪超範圍 K 線失敗 {symbol}/{tf}：{trim_exc}")
                    # 下載成功後自動執行品質檢查，將結果寫入 warning
                    try:
                        report = self._storage.get_data_quality_report(symbol, tf)
                        integrity = report.get("integrity", {})
                        if not integrity.get("is_valid", True):
                            for err in integrity.get("errors", []):
                                task.error_messages.append(f"[品質警告] {symbol} {tf}：{err}")
                                logger.warning(f"品質檢查發現問題 {symbol}/{tf}：{err}")
                        for warn in integrity.get("warnings", []):
                            logger.info(f"品質提示 {symbol}/{tf}：{warn}")
                        stats = integrity.get("stats", {})
                        logger.info(
                            f"品質檢查通過 {symbol}/{tf}：is_valid={integrity.get('is_valid')}, "
                            f"bars={stats.get('total_bars', 'N/A')}"
                        )
                    except Exception as qe:
                        logger.warning(f"品質檢查執行失敗 {symbol}/{tf}：{qe}")
                except Exception as exc:
                    failed_count += 1
                    task.failed_jobs += 1
                    msg = f"{symbol} {tf}：{exc}"
                    task.error_messages.append(msg)
                    logger.warning(f"下載失敗 {msg}")

        task.status = (
            "completed" if failed_count == 0
            else "partial" if task.completed_jobs > 0
            else "failed"
        )
        task.current_symbol = None
        task.current_timeframe = None
        task.finished_at = datetime.now(timezone.utc)
        logger.info(
            f"任務 {task_id} 結束：completed={task.completed_jobs}, "
            f"failed={task.failed_jobs}"
        )

    def list_downloaded(self) -> List[Dict]:
        """
        列出已下載的所有 (symbol, timeframe) 組合及基本統計。

        使用 get_cache_index()（O(1) 索引讀取）+ get_metadata() 取得每組的
        row_count 與時間範圍，避免 read_klines 全量載入 HDF5。

        Returns:
            List of {"symbol", "timeframe", "row_count", "start_date", "end_date"}
        """
        try:
            cache_index = self._storage.get_cache_index()
            entries: List[Dict] = []
            for symbol, tfs in cache_index.items():
                for tf in tfs:
                    try:
                        meta = self._storage.get_metadata(symbol, tf)
                        if meta is None:
                            continue

                        total_bars = int(meta.get("total_bars", 0))
                        # BinanceProvider 已將 Binance 毫秒時間戳轉為秒（÷1000）
                        start_ts = meta.get("time_range_start")
                        end_ts = meta.get("time_range_end")

                        start_date_str = (
                            datetime.utcfromtimestamp(int(start_ts)).strftime("%Y-%m-%d")
                            if start_ts else ""
                        )
                        end_date_str = (
                            datetime.utcfromtimestamp(int(end_ts)).strftime("%Y-%m-%d")
                            if end_ts else ""
                        )

                        # 品質檢查（輕量版：只取 is_valid / errors / warnings）
                        is_valid: Optional[bool] = None
                        quality_errors: List[str] = []
                        quality_warnings: List[str] = []
                        try:
                            qr = _sanitize_for_json(
                                self._storage.get_data_quality_report(symbol, tf)
                            )
                            integrity = qr.get("integrity", {})
                            is_valid = integrity.get("is_valid")
                            quality_errors = integrity.get("errors", [])
                            quality_warnings = integrity.get("warnings", [])
                        except Exception as qe:
                            logger.debug(f"品質檢查失敗 {symbol}/{tf}：{qe}")

                        entries.append({
                            "symbol": symbol,
                            "timeframe": tf,
                            "row_count": total_bars,
                            "start_date": start_date_str,
                            "end_date": end_date_str,
                            "is_valid": is_valid,
                            "quality_errors": quality_errors,
                            "quality_warnings": quality_warnings,
                        })
                    except Exception as exc:
                        logger.debug(f"讀取 {symbol}/{tf} 元資料失敗：{exc}")
            return entries
        except Exception as exc:
            logger.error(f"列出已下載資料失敗：{exc}", exc_info=True)
            return []

    def get_quality_report(self, symbol: str, timeframe: str) -> Dict:
        """
        取得指定 (symbol, timeframe) 的數據品質報告。

        呼叫 KlineStorageManager.get_data_quality_report 執行完整性檢查：
          - 時間連續性（irregular gaps）
          - 重複 timestamp
          - OHLC 合理性（high >= low / open / close）
          - taker_ratio 範圍（0~1）
          - volume 非負

        Returns:
            {symbol, timeframe, metadata, integrity:{is_valid, errors, warnings, stats}}
        """
        try:
            raw = self._storage.get_data_quality_report(symbol, timeframe)
            # h5py 讀取 HDF5 attrs 時回傳 numpy 純量（numpy.bool_、numpy.int64等），
            # FastAPI jsonable_encoder 無法處理，必須先轉為 Python 原生型別。
            return _sanitize_for_json(raw)
        except Exception as exc:
            logger.error(f"品質報告生成失敗 {symbol}/{timeframe}：{exc}", exc_info=True)
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "is_valid": False,
                "error": str(exc),
            }

    # ──────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────

    def _get_all_usdt_pairs(self) -> List[str]:
        """從 Binance 取得所有 USDT 交易對。API key 不可用時回傳空清單。"""
        try:
            import requests  # 輕量 HTTP，不引入 binance-python

            resp = requests.get(
                "https://api.binance.com/api/v3/exchangeInfo",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            pairs = [
                s["symbol"]
                for s in data.get("symbols", [])
                if s.get("status") == "TRADING"
                and s.get("symbol", "").endswith("USDT")
            ]
            return sorted(pairs)
        except Exception as exc:
            logger.error(f"取得 ALL_USDT 失敗：{exc}")
            return []


# ── 單例工廠 ──────────────────────────────
_service_instance: Optional[FeatureKlineService] = None


def get_feature_kline_service() -> FeatureKlineService:
    """回傳全域單例（FastAPI 啟動後共用）。"""
    global _service_instance
    if _service_instance is None:
        _service_instance = FeatureKlineService()
    return _service_instance
