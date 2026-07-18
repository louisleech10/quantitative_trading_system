#!/usr/bin/env python3
"""LA-2 B0: 可重現改前 golden baseline（四面 legacy + control + 軌2 index identity）。

SPEC: docs/IC_LA2_SPEC.md §G / B0.1
TODO: docs/IC_LA2_TODO.md Task 0.1（U6/U19）

入口契約（T7 / analyzer 直呼，禁 orch.analyze 副作用）:
  - kline: data_cache/feature_klines/kline_cache.h5 → /{SYMBOL}/{tf}/data
  - features: 複用 LA-0 真實 HDF5（非合成）
  - 四面 caller:
      ① pattern → PatternExtractor.extract_decision_rules
      ② regime_fit_global → RegimeDetector.detect(expanding=False)
      ③ factor → FactorOrthogonalizer.gram_schmidt/pca + FactorExposureAnalyzer
      ④ model → XGBoostAnalyzer.train_model + service 全矩陣
         (predictions/recommend_k/precision@K/expectancy/sharpe/
          bootstrap_ci/permutation/fold_importance/shap；
          cross_symbol 明列 exclude)
  - winsorized **不列** baseline（DEC-1 禁用 → oracle=raises）
  - persist 隔離：不觸發產線 save_report / data_cache/reports

四面鍵 (PATH_KEYS):
  pattern / regime_fit_global / factor / model

control:
  regime_pit (expanding=True) / factor_disabled / pattern_not_extracted

--check assert:
  ① 兩 input kline sha literal 重驗
  ② C-2 early-flip manifest 兩側 len>0
  ③ 軌2 index identity 記錄 + baseline 四面鍵齊全
  ④ model.service_matrix 全矩陣鍵 + exclude 明列
  ⑤ 凍結 file sha256 + 每面關鍵 value hash literal（竄改任一面 → FAIL）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Optional

import h5py
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from momentum.factories import (  # noqa: E402
    create_bootstrap_estimator,
    create_expectancy_calculator,
    create_factor_exposure_analyzer,
    create_factor_orthogonalizer,
    create_kline_storage_manager,
    create_pattern_extractor,
    create_regime_detector,
    create_xgboost_analyzer,
)

# ---------------------------------------------------------------------------
# 凍結常數
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).resolve().parent
INPUTS_DIR = OUTPUT_DIR / "inputs"
KLINE_CACHE_DIR = "data_cache/feature_klines"
KLINE_H5_PATH = REPO_ROOT / KLINE_CACHE_DIR / "kline_cache.h5"
KLINE_H5_GROUP_TEMPLATE = "/{symbol}/{timeframe}/data"
SCHEMA_VERSION = "la2_b0_v1"
CONTROL_SCHEMA_VERSION = "la2_b0_control_v1"

# U6 cold-start dataset sha literals（與 LA-1 同源檔）
EXPECTED_KLINE: dict[tuple[str, str], dict[str, Any]] = {
    ("BTCUSDT", "1h"): {
        "rows": 20352,
        "sha16": "1c93c37938a4917a",
    },
    ("ETHUSDT", "12h"): {
        "rows": 1696,
        "sha16": "00d1ee985ad3f09f",
    },
}

# Canonical mutation 常數（SPEC §G；內嵌禁口頭改）
M_TRUNC_RATIO = 0.75  # n_keep = int(0.75 * n)
EARLY_WINDOW_RATIO = 2.0 / 3.0  # early = [0, int(2/3 * n_keep))

# 四面鍵（--check assert ③；winsorized 除外）
PATH_KEYS = (
    "pattern",
    "regime_fit_global",
    "factor",
    "model",
)

CONTROL_KINDS = (
    "regime_pit",
    "factor_disabled",
    "pattern_not_extracted",
)

# 特徵輸入：沿用 LA-0 已物化真實 features（非合成）
LA0_INPUTS_DIR = REPO_ROOT / "tests" / "golden" / "la0" / "inputs"

RUNS: list[dict[str, str]] = [
    {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "config_hash": "4a8a0b3726cc906ab3534994605e77f5",
        "baseline_name": "BTCUSDT_1h_baseline.json",
        "la0_h5_glob": "BTCUSDT_1h_*_a0_tail2000.h5",
    },
    {
        "symbol": "ETHUSDT",
        "timeframe": "12h",
        "config_hash": "e53e22906c35363757f4cd49d27f973e",
        "baseline_name": "ETHUSDT_12h_baseline.json",
        "la0_h5_glob": "ETHUSDT_12h_*_a0_tail2000.h5",
    },
]

# model 訓練固定參數（可重現；禁隨機漂移）
XGB_BASELINE_PARAMS: dict[str, Any] = {
    "n_estimators": 30,
    "max_depth": 3,
    "learning_rate": 0.1,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "reg_lambda": 1.0,
    "reg_alpha": 0.0,
    "min_child_weight": 1,
    "random_state": 42,
    "n_jobs": 1,
    "tree_method": "hist",
    "eval_metric": "auc",
    "use_label_encoder": False,
}
EVAL_SIZE = 0.2
CV_FOLDS = 3
HORIZON_BARS = 1  # binary label = sign of next-bar simple return

# B0-F2：凍結 baseline file sha256 literal（--check 竄改任一面值 → FAIL）
# 由 write 後重算填入；改 n_rules / train_auc / labels 等任一面 → 檔案 digest 必變。
EXPECTED_BASELINE_FILE_SHA256: dict[str, str] = {
    "BTCUSDT_1h_baseline.json": (
        "5db5cb62a74ee4b4f244af1fadcd01424ac4b57c40f15c70475f60f0301e49d2"
    ),
    "ETHUSDT_12h_baseline.json": (
        "1151631e933c5f0c2b89bd3831e5552e89b8a6a64fc45be562a14c3f013c9244"
    ),
}

# 每面關鍵 value hash 欄位（相對 baseline root 的 dotted path）
FACE_VALUE_HASH_PATHS: tuple[str, ...] = (
    "pattern.n_rules",
    "pattern.threshold_value_sha256",
    "pattern.confidence_value_sha256",
    "regime_fit_global.labels_sha256",
    "regime_fit_global.name_set_sha256",
    "factor.gram_schmidt.value_sha256",
    "factor.pca.value_sha256",
    "factor.exposure.beta_neutral_value_sha256",
    "model.performance_value_sha256",
    "model.service_matrix.matrix_value_sha256",
    "model.index_identity.fit_idx_hash",
    "model.index_identity.eval_idx_hash",
    "control.regime_pit.labels_sha256",
)

# write 後 stamp；--check 比對（竄改任一面值 → FAIL）
EXPECTED_FACE_VALUE_HASHES: dict[str, dict[str, Any]] = {
    "BTCUSDT_1h_baseline.json": {
        "control.regime_pit.labels_sha256": "dce7c33c76c8d4c530d2013470d26e4186a85a0a4b59509f02b7b2916d3186af",
        "factor.exposure.beta_neutral_value_sha256": "2fc88ac6c6a42294b30fddda46e5d2d475b6c0c123b00dab7c278be00b8766de",
        "factor.gram_schmidt.value_sha256": "9ff82b0fa1b88d182a2e052988aa580e2fed8d68d82d3cee9bbb4ae7f0a260e5",
        "factor.pca.value_sha256": "23d66d29e38c834b4548b1d9a616682afbabe16081d4ee5a5876739c569d8ed2",
        "model.index_identity.eval_idx_hash": "2f18a447cc0e3afe5e7fce2e879b987891f09c4290cc98f1d62a622eedd2816a",
        "model.index_identity.fit_idx_hash": "0d10b5c25c1690d937b0f9beb47a825b9c5c3599a9264853eb41a84ee168a61f",
        "model.performance_value_sha256": "0c62130cbde8e65a4a241d771cb27d60ee61a17aec2ed377a2ff4616dcc3c22d",
        "model.service_matrix.matrix_value_sha256": "26b4c0c8d500dee05c87eb357e8ff51046b3dbf0b29136fbdd8592fe45d131b1",
        "pattern.confidence_value_sha256": "8d3e0c3f8556c0665c4b10bc0453449c59e47caa164e8a3d9640574bd108ea4e",
        "pattern.n_rules": 6,
        "pattern.threshold_value_sha256": "0c253b46367fdc3e765403ac5c91aa0ca36e16fd8ccff22286fc8ab30bd0bc20",
        "regime_fit_global.labels_sha256": "267f795ed303c9117a20e09025c2c08038e1e685247fbb4b2b618700e2b1101e",
        "regime_fit_global.name_set_sha256": "77607ef9f51409176605c820717e1e73ad602f2ef8840b4e179d52ceab1066cb",
    },
    "ETHUSDT_12h_baseline.json": {
        "control.regime_pit.labels_sha256": "bd529dd3905f10ab7cbe1d06809b89571aaea9632b6f368b247a07ffe529799c",
        "factor.exposure.beta_neutral_value_sha256": "4ebf98c408eb8ff7acdf6ec0fe833d416125ff72936e8b4576c560034a0d6de7",
        "factor.gram_schmidt.value_sha256": "95f53add33db873106783c5a6a416cbf93fdc9ec27a38aeb2e5c801213b6d74e",
        "factor.pca.value_sha256": "2ff63630b2d08acaa37626771a9696010330d3fadb02e3b36f508b5eb06bcc33",
        "model.index_identity.eval_idx_hash": "3c062920a9d64447d12b59dba8b7cf4448a7d61f900b5b0b66cf4e9ff9a9ae5a",
        "model.index_identity.fit_idx_hash": "96f4490491734dc4345339789408cad5ac83bac8b37a634c963a4f9ddfa926b1",
        "model.performance_value_sha256": "7d22764ba7a0b577fed49a0b025aa63ee14c845f9999248f031228fd97a0dc62",
        "model.service_matrix.matrix_value_sha256": "80866e511e5c9f6b07ce9556439e92c6906c8ae88a2a668e1ad67664cbfb7d2e",
        "pattern.confidence_value_sha256": "0e6b4ef7d14173c9ee01e397c36d70acaa9b13682549b6ef829221af74465bc2",
        "pattern.n_rules": 8,
        "pattern.threshold_value_sha256": "fb2e5821d88520df337ac3f71244c576521bfb65e5515c1ebd7dac92e3c1ebb5",
        "regime_fit_global.labels_sha256": "73de118ed59c97271c2fc9ef19f1c50851dbdbea0e8748ef37b8585001b3c3e4",
        "regime_fit_global.name_set_sha256": "77607ef9f51409176605c820717e1e73ad602f2ef8840b4e179d52ceab1066cb",
    },
}

# service 全矩陣鍵（F1；exclude 明列）
SERVICE_MATRIX_KEYS: tuple[str, ...] = (
    "predictions",
    "precision_at_k",
    "recommend_k",
    "expectancy",
    "sharpe_proxy",
    "bootstrap_ci",
    "permutation_importance",
    "fold_importance_stability",
    "shap_sample",
    "cross_symbol_validation",
)

SERVICE_MATRIX_EXCLUDES: dict[str, str] = {
    "cross_symbol_validation": (
        "B0 single-symbol face cannot run batch LOSO multi-symbol path "
        "(xgboost_batch_service:907-933); freeze deferred to B4 U17 "
        "deterministic top-2 eligible symbols smoke; marked excluded+reason"
    ),
    "regime_analysis": (
        "feature HDF5 無 Market_Phase 欄；xgboost_task_service 同條件 skip "
        "(None)；非本面 freeze 目標"
    ),
}


# ---------------------------------------------------------------------------
# Hash / JSON helpers
# ---------------------------------------------------------------------------
def _json_default(obj: Any) -> Any:
    """numpy / pandas 純量 → Python 原生（禁 int64 炸 json）。"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        if not np.isfinite(f):
            raise ValueError(f"non-finite float in baseline: {f}")
        return f
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
            allow_nan=False,
            default=_json_default,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_float_array(values: Any) -> str:
    """穩定 hash float 陣列（NaN→sentinel 後 tobytes）。"""
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    out = arr.copy()
    nan_mask = ~np.isfinite(out)
    out[nan_mask] = -9.87654321e30
    payload = out.tobytes(order="C") + f"|nan_count={int(nan_mask.sum())}".encode()
    return _sha256_bytes(payload)


def _hash_bool_array(values: Any) -> str:
    arr = np.asarray(values, dtype=np.bool_).reshape(-1)
    return _sha256_bytes(arr.tobytes(order="C") + f"|n={arr.size}".encode())


def _hash_string_set(items: list[str]) -> str:
    return _sha256_bytes("\n".join(sorted(str(x) for x in items)).encode("utf-8"))


def _hash_string_array(values: Any) -> str:
    arr = np.asarray(values, dtype=object).reshape(-1)
    joined = "\n".join(str(x) for x in arr.tolist())
    return _sha256_bytes(joined.encode("utf-8") + f"|n={arr.size}".encode())


def _hash_index_identity(idx: Any) -> str:
    """軌2 fit/eval index identity（ndim==1 int64 bytes + sha256）。"""
    arr = np.ascontiguousarray(np.asarray(idx, dtype=np.int64).reshape(-1))
    if arr.ndim != 1:
        raise RuntimeError(f"index identity requires ndim==1, got {arr.ndim}")
    return _sha256_bytes(arr.tobytes(order="C") + f"|n={arr.size}".encode())


def _json_safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(f):
        return None
    return float(f)


# ---------------------------------------------------------------------------
# Canonical mutation helpers
# ---------------------------------------------------------------------------
def m_trunc_n_keep(n: int) -> int:
    """M-trunc：截尾保留前 75%。"""
    return int(M_TRUNC_RATIO * int(n))


def early_window_end(n_keep: int) -> int:
    """early window = [0, int(2/3 * n_keep))。"""
    return int(EARLY_WINDOW_RATIO * int(n_keep))


# ---------------------------------------------------------------------------
# Kline receipt / features I/O
# ---------------------------------------------------------------------------
def _kline_group_dataset_sha16(symbol: str, timeframe: str) -> tuple[int, str]:
    """回傳 (rows, sha256 前 16 hex) — 對 structured dataset 全欄位 bytes。"""
    group_key = KLINE_H5_GROUP_TEMPLATE.format(symbol=symbol, timeframe=timeframe)
    key = group_key.lstrip("/")
    with h5py.File(KLINE_H5_PATH, "r") as handle:
        if key not in handle:
            raise RuntimeError(f"kline group missing: {group_key} in {KLINE_H5_PATH}")
        data = handle[key][()]
    rows = int(data.shape[0]) if hasattr(data, "shape") else 0
    sha16 = hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest()[:16]
    return rows, sha16


def verify_kline_receipts() -> None:
    """--check assert ①：兩 input sha literal 重驗。"""
    if not KLINE_H5_PATH.is_file():
        raise SystemExit(f"kline cache missing (read-only required): {KLINE_H5_PATH}")
    for (symbol, timeframe), expected in EXPECTED_KLINE.items():
        rows, sha16 = _kline_group_dataset_sha16(symbol, timeframe)
        if rows != int(expected["rows"]):
            raise SystemExit(
                f"kline rows mismatch {symbol}/{timeframe}: "
                f"got {rows} expected {expected['rows']}"
            )
        if sha16 != expected["sha16"]:
            raise SystemExit(
                f"kline sha16 mismatch {symbol}/{timeframe}: "
                f"got {sha16} expected {expected['sha16']}"
            )
        print(
            f"[gen_baseline] kline OK {symbol}/{timeframe} "
            f"rows={rows} sha16={sha16}"
        )


def _read_features_h5(path: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    group_key = f"{symbol}/{timeframe}"
    with h5py.File(path, "r") as file:
        group = file[group_key]
        feats = group["features"][()]
        names = [
            n.decode("utf-8") if isinstance(n, (bytes, bytearray)) else str(n)
            for n in group["feature_names"][()]
        ]
        timestamps = group["timestamps"][()]
    index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None)
    return pd.DataFrame(feats, columns=names, index=index)


def _resolve_la0_feature_inputs(run: dict[str, str]) -> tuple[Path, Path]:
    """解析 LA-0 已物化真實 features（唯讀來源）→ 複製到 la2/inputs。"""
    matches = sorted(LA0_INPUTS_DIR.glob(run["la0_h5_glob"]))
    if not matches:
        raise RuntimeError(
            f"LA-0 feature input missing for {run['symbol']}/{run['timeframe']}: "
            f"{LA0_INPUTS_DIR}/{run['la0_h5_glob']}"
        )
    src_h5 = matches[0]
    src_meta = Path(str(src_h5).replace(".h5", "_meta.json"))
    if not src_meta.is_file():
        raise RuntimeError(f"LA-0 meta missing: {src_meta}")

    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    dst_h5 = INPUTS_DIR / src_h5.name
    dst_meta = INPUTS_DIR / src_meta.name
    # B0-F6：內容 sha 判定（禁 size/mtime 假相等 stale-copy）
    if not dst_h5.exists() or _sha256_file(dst_h5) != _sha256_file(src_h5):
        shutil.copy2(src_h5, dst_h5)
    if not dst_meta.exists() or _sha256_file(dst_meta) != _sha256_file(src_meta):
        shutil.copy2(src_meta, dst_meta)
    return dst_h5, dst_meta


def _write_face_config(symbol: str, timeframe: str, face: str, body: dict[str, Any]) -> Path:
    """inputs/* 各面 config JSON（return_type/expanding/factor.enabled/pattern split）。"""
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    path = INPUTS_DIR / f"{symbol}_{timeframe}_{face}_config.json"
    path.write_bytes(_canonical_json_bytes(body))
    return path


def _load_kline_close_volume(
    symbol: str, timeframe: str
) -> tuple[pd.Series, Optional[pd.Series], pd.Series]:
    """真實 kline close/volume/timestamp（RangeIndex 時以 timestamp 欄重建 index）。"""
    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    raw = kline_reader.read_klines(symbol, timeframe)
    if raw is None or raw.empty:
        raise RuntimeError(f"empty kline for {symbol}/{timeframe}")
    if "timestamp" not in raw.columns:
        raise RuntimeError(f"{symbol}/{timeframe}: kline missing `timestamp` column")
    ts = raw["timestamp"]
    # Series.dt.tz_convert（非 DatetimeIndex.tz_convert）
    idx = pd.to_datetime(ts, unit="s", utc=True).dt.tz_convert(None)
    close = pd.Series(raw["close"].astype(float).to_numpy(), index=idx, name="close")
    volume = None
    if "volume" in raw.columns:
        volume = pd.Series(
            raw["volume"].astype(float).to_numpy(), index=idx, name="volume"
        )
    return close, volume, ts


def _binary_label_from_close(close: pd.Series, horizon: int = HORIZON_BARS) -> pd.Series:
    """simple forward return sign → {0,1}（真實 close，非合成）。"""
    fwd = close.pct_change(periods=horizon).shift(-horizon)
    y = (fwd > 0).astype(float)
    y[fwd.isna()] = np.nan
    return y


def _align_xy(
    features_df: pd.DataFrame, close: pd.Series
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[int]]:
    """features ∩ close 對齊；丟 NaN label；回傳 X, y, row positions, unix timestamps。"""
    y_full = _binary_label_from_close(close.reindex(features_df.index))
    aligned = features_df.copy()
    aligned["__y__"] = y_full
    clean = aligned.dropna(axis=0, how="any")
    if len(clean) < 100:
        raise RuntimeError(f"aligned samples too few: {len(clean)}")
    y = clean["__y__"].to_numpy(dtype=np.int64)
    X = clean.drop(columns=["__y__"])
    # positional index identity（在 clean 內 0..n-1；供 fit/eval hash）
    positions = np.arange(len(clean), dtype=np.int64)
    if isinstance(clean.index, pd.DatetimeIndex):
        ts_list = [int(x) for x in (clean.index.asi8 // 10**9).tolist()]
    else:
        ts_list = list(range(len(clean)))
    # 至少兩類
    if len(np.unique(y)) < 2:
        raise RuntimeError("binary label has <2 classes after dropna")
    return X, y, positions, ts_list


# ---------------------------------------------------------------------------
# Face runners（analyzer 直呼）
# ---------------------------------------------------------------------------
def _run_pattern_face(
    X: pd.DataFrame,
    y: np.ndarray,
    model: Any,
) -> dict[str, Any]:
    """C-2：PatternExtractor.extract_decision_rules — 門檻 + confidence 凍結。"""
    extractor = create_pattern_extractor()
    feature_names = list(X.columns)
    rules = extractor.extract_decision_rules(
        model=model,
        X=X,
        y=y,
        feature_names=feature_names,
        top_n=10,
        min_support=10,
    )
    rules_payload: list[dict[str, Any]] = []
    thresholds: list[float] = []
    confidences: list[float] = []
    for rule in rules:
        body = rule.to_dict()
        # 強制 Python 原生（numpy 純量 → float/int）
        safe_conds: list[dict[str, Any]] = []
        for cond in body.get("feature_conditions") or []:
            if not isinstance(cond, dict):
                continue
            t = _json_safe_float(cond.get("threshold"))
            safe_conds.append(
                {
                    "feature": str(cond.get("feature")),
                    "operator": str(cond.get("operator")),
                    "threshold": t,
                }
            )
            if t is not None:
                thresholds.append(t)
        c = _json_safe_float(body.get("confidence"))
        if c is not None:
            confidences.append(c)
        rules_payload.append(
            {
                "rule_id": int(body.get("rule_id") or 0),
                "condition": str(body.get("condition") or ""),
                "support": int(body.get("support") or 0),
                "confidence": c,
                "lift": _json_safe_float(body.get("lift")),
                "feature_conditions": safe_conds,
            }
        )

    # 亦凍結 top-5 特徵 raw quantiles（legacy 全樣本門檻來源）
    quantiles: dict[str, dict[str, float]] = {}
    for fname in feature_names[:5]:
        series = X[fname]
        q = series.quantile([0.25, 0.5, 0.75])
        quantiles[fname] = {
            "q25": float(q.loc[0.25]),
            "q50": float(q.loc[0.5]),
            "q75": float(q.loc[0.75]),
        }

    return {
        "caller": "PatternExtractor.extract_decision_rules",
        "n_rules": len(rules_payload),
        "rules": rules_payload,
        "threshold_value_sha256": _hash_float_array(thresholds),
        "confidence_value_sha256": _hash_float_array(confidences),
        "base_prob": _json_safe_float(float(np.mean(y))) if len(y) else None,
        "feature_quantiles": quantiles,
        "n_samples": int(len(y)),
        "n_features": int(X.shape[1]),
    }


def _pattern_early_flip_manifest(X: pd.DataFrame, y: np.ndarray) -> dict[str, Any]:
    """C-2 early-flip：full vs M-trunc 門檻/confidence 在 early window 的翻轉集合。

    門檻：同一特徵 q50 full vs trunc 是否不同（特徵級）。
    confidence：固定 threshold=full q50，mask 後 y.mean full vs trunc early 段是否不同。
    """
    n = int(len(X))
    n_keep = m_trunc_n_keep(n)
    early_end = early_window_end(n_keep)
    X_full = X
    X_trunc = X.iloc[:n_keep]
    y_trunc = y[:n_keep]

    threshold_flip_features: list[str] = []
    confidence_flip_features: list[str] = []
    for fname in list(X.columns)[: min(8, X.shape[1])]:
        q_full = float(X_full[fname].quantile(0.5))
        q_trunc = float(X_trunc[fname].quantile(0.5))
        if not np.isclose(q_full, q_trunc, atol=1e-12, rtol=0.0):
            threshold_flip_features.append(fname)

        # confidence：full 門檻套 full-y vs trunc-y 的 early 區段
        mask_full = X_full[fname].to_numpy() > q_full
        mask_trunc = X_trunc[fname].to_numpy() > q_full  # 同門檻，測 y 域洩漏
        # early window confidence（support 足夠才比）
        early_idx = np.arange(min(early_end, n_keep))
        if early_idx.size == 0:
            continue
        mf = mask_full[early_idx]
        mt = mask_trunc[early_idx]
        y_early_full = y[early_idx]
        y_early_trunc = y_trunc[early_idx]
        if mf.sum() >= 5 and mt.sum() >= 5:
            conf_f = float(y_early_full[mf].mean())
            conf_t = float(y_early_trunc[mt].mean())
            if not np.isclose(conf_f, conf_t, atol=1e-12, rtol=0.0):
                confidence_flip_features.append(fname)
        # 亦比 full-sample confidence vs trunc-sample confidence（legacy look-ahead 證）
        if mask_full.sum() >= 10 and mask_trunc.sum() >= 10:
            conf_all = float(y[mask_full].mean())
            conf_tr = float(y_trunc[mask_trunc].mean())
            if not np.isclose(conf_all, conf_tr, atol=1e-12, rtol=0.0):
                if fname not in confidence_flip_features:
                    confidence_flip_features.append(fname)

    return {
        "mutation": {
            "m_trunc_ratio": M_TRUNC_RATIO,
            "n": n,
            "n_keep": n_keep,
            "early_window": [0, early_end],
            "early_window_ratio": EARLY_WINDOW_RATIO,
        },
        "pattern": {
            "threshold_flip_features": threshold_flip_features,
            "confidence_flip_features": confidence_flip_features,
            "n_threshold_flip": len(threshold_flip_features),
            "n_confidence_flip": len(confidence_flip_features),
        },
    }


def _run_regime_face(
    close: pd.Series,
    volume: Optional[pd.Series],
    *,
    expanding: bool,
) -> dict[str, Any]:
    """C-1：RegimeDetector.detect — expanding=False → _fit_global legacy。"""
    detector = create_regime_detector(n_clusters=4, lookback=55)
    result = detector.detect(close, volume, expanding=expanding)
    labels = [str(x) for x in result.labels]
    if isinstance(close.index, pd.DatetimeIndex):
        ts_list = [int(x) for x in (close.index.asi8 // 10**9).tolist()]
    else:
        ts_list = list(range(len(labels)))
    name_set = sorted(set(labels))
    # element payload：labels + timestamps（禁 aggregate-only；LA-1 範式）
    # JSON 鍵一律 Python 原生型別
    ts_list_i = [int(t) for t in ts_list]
    return {
        "caller": (
            "RegimeDetector.detect(expanding=False→_fit_global)"
            if not expanding
            else "RegimeDetector.detect(expanding=True→PIT)"
        ),
        "expanding": bool(expanding),
        "method": str(result.method),
        "n_clusters": int(result.n_clusters),
        "len": int(len(labels)),
        "name_set": name_set,
        "name_set_sha256": _hash_string_set(name_set),
        "labels_sha256": _hash_string_array(labels),
        "timestamps_sha256": _hash_string_array([str(t) for t in ts_list_i]),
        "value_counts": {
            k: int(sum(1 for x in labels if x == k)) for k in name_set
        },
        "labels": labels,
        "timestamps": ts_list_i,
    }


def _run_factor_face(
    factors: pd.DataFrame,
    market_proxy: pd.Series,
    *,
    enabled: bool,
) -> dict[str, Any]:
    """C-3：GS/PCA/exposure（enabled=True legacy；control 走 disabled）。"""
    if not enabled:
        return {
            "caller": "factor_modules_skipped",
            "enabled": False,
            "skipped": True,
            "reason": "control factor.enabled=False",
        }

    orth = create_factor_orthogonalizer({})
    exposure = create_factor_exposure_analyzer(
        {"max_single_exposure": 0.4, "neutralization_mode": "none"}
    )

    gs_df, gs_meta = orth.gram_schmidt(factors)
    pca_df, pca_meta = orth.pca_orthogonalize(factors)

    # legacy market_proxy = forward label（DEC-3 修前）；此處凍結改前值
    proxy = market_proxy.reindex(factors.index)
    positions = pd.Series(1.0 / max(len(factors.columns), 1), index=factors.index)
    # portfolio exposure vs factor matrix
    try:
        port_exp = exposure.calculate_portfolio_exposure(
            positions=positions.fillna(0.0),
            factor_values=factors.fillna(0.0),
        )
        exp_payload = {
            "exposure_sha256": _hash_float_array(port_exp.to_numpy(dtype=float)),
            "factors": {str(k): _json_safe_float(v) for k, v in port_exp.items()},
        }
    except Exception as exc:  # noqa: BLE001 — baseline 必須可序列化失敗原因
        exp_payload = {"error": str(exc), "exposure_sha256": None}

    # beta neutralization summary (uses market_proxy — legacy forward)
    neutralized = exposure.neutralize_factor_matrix(
        factor_values=factors,
        market_proxy=proxy,
        mode="beta_neutral",
    )
    neut_hash = _hash_float_array(neutralized.to_numpy(dtype=float).reshape(-1))

    gs_vals = (
        gs_df.to_numpy(dtype=float).reshape(-1)
        if not gs_df.empty
        else np.asarray([], dtype=float)
    )
    pca_vals = (
        pca_df.to_numpy(dtype=float).reshape(-1)
        if not pca_df.empty
        else np.asarray([], dtype=float)
    )

    return {
        "caller": (
            "FactorOrthogonalizer.gram_schmidt/pca_orthogonalize + "
            "FactorExposureAnalyzer.*"
        ),
        "enabled": True,
        "gram_schmidt": {
            "method": gs_meta.get("method"),
            "correlation_before": _json_safe_float(gs_meta.get("correlation_before")),
            "correlation_after": _json_safe_float(gs_meta.get("correlation_after")),
            "priority_order": list(gs_meta.get("priority_order") or []),
            "value_sha256": _hash_float_array(gs_vals),
            "nan_mask_sha256": _hash_bool_array(~np.isfinite(gs_vals)),
            "shape": list(gs_df.shape),
            "skipped": bool(gs_meta.get("skipped", False)),
        },
        "pca": {
            "method": pca_meta.get("method"),
            "n_components": pca_meta.get("n_components"),
            "explained_variance_ratio": list(
                pca_meta.get("explained_variance_ratio") or []
            ),
            "value_sha256": _hash_float_array(pca_vals),
            "nan_mask_sha256": _hash_bool_array(~np.isfinite(pca_vals)),
            "shape": list(pca_df.shape),
            "skipped": bool(pca_meta.get("skipped", False)),
        },
        "exposure": {
            **exp_payload,
            "beta_neutral_value_sha256": neut_hash,
            "proxy_kind_legacy": "forward_label_series",
            "proxy_sha256": _hash_float_array(
                proxy.to_numpy(dtype=float)
            ),
        },
        "n_samples": int(len(factors)),
        "n_factors": int(factors.shape[1]),
    }


def _time_series_fit_eval_indices(n: int, eval_size: float = EVAL_SIZE) -> tuple[np.ndarray, np.ndarray]:
    """legacy train_model time_series_split 的 fit/eval 位置（無 shuffle）。"""
    split_idx = int(n * (1.0 - eval_size))
    if split_idx < 1 or split_idx >= n:
        raise RuntimeError(f"invalid split_idx={split_idx} for n={n}")
    fit_idx = np.arange(0, split_idx, dtype=np.int64)
    eval_idx = np.arange(split_idx, n, dtype=np.int64)
    return fit_idx, eval_idx


def _to_jsonable(obj: Any) -> Any:
    """service 結果 → JSON-safe（禁 NaN；大陣列改 sha）。"""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return _json_safe_float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return _json_safe_float(float(obj))
    if isinstance(obj, np.ndarray):
        return {
            "shape": list(obj.shape),
            "value_sha256": _hash_float_array(obj.astype(float).reshape(-1))
            if np.issubdtype(obj.dtype, np.number)
            else _sha256_bytes(obj.tobytes()),
        }
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        # 長 list 改 hash 摘要，避免 baseline 暴脹
        if len(obj) > 64 and all(
            isinstance(x, (int, float, np.floating, np.integer)) for x in obj[:8]
        ):
            try:
                return {
                    "n": len(obj),
                    "value_sha256": _hash_float_array(obj),
                }
            except Exception:  # noqa: BLE001
                pass
        return [_to_jsonable(x) for x in obj]
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return _to_jsonable(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return _to_jsonable(
            {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        )
    return str(obj)


def _run_model_service_matrix(
    analyzer: Any,
    X: pd.DataFrame,
    y: np.ndarray,
    timestamps: list[int],
    price_changes: np.ndarray,
) -> dict[str, Any]:
    """B0-F1：凍 legacy model service 全矩陣（鏡像 xgboost_task_service 產線 post-fit）。

    呼叫 analyzer/factories 與 `api/services/xgboost_task_service.py` 同方法序列：
    predictions → precision@K → recommend_k → expectancy/sharpe → bootstrap_ci →
    permutation → fold_importance → shap_sample。
    難凍項見 SERVICE_MATRIX_EXCLUDES（明列理由，非默默漏）。
    """
    feature_names = list(X.columns)
    case_ids = [f"case_{i}" for i in range(len(X))]
    matrix: dict[str, Any] = {
        "caller_path": (
            "mirrors api.services.xgboost_task_service."
            "XGBoostTaskService._run_xgboost_analysis post-fit matrix"
        ),
        "exclude": dict(SERVICE_MATRIX_EXCLUDES),
    }

    # 1. predictions（service: get_predictions）
    predictions_output = analyzer.get_predictions(X, y, case_ids)
    y_pred_proba = np.asarray(
        [p.predicted_proba for p in predictions_output.predictions],
        dtype=np.float64,
    )
    proba_summary = None
    if hasattr(predictions_output, "proba_summary") and predictions_output.proba_summary is not None:
        ps = predictions_output.proba_summary
        proba_summary = _to_jsonable(ps)
    matrix["predictions"] = {
        "n": int(len(y_pred_proba)),
        "proba_sha256": _hash_float_array(y_pred_proba),
        "proba_summary": proba_summary,
        "legacy_scope": "full_sample_pool",  # 軌2 樂觀；B2 改 OOT 分列
    }

    # 2. precision@K + recommend_k
    pak = analyzer.calculate_precision_at_k(X, y)
    pak_dict = pak.to_dict() if hasattr(pak, "to_dict") else _to_jsonable(pak)
    recommended = analyzer.recommend_k(
        y_true=y,
        y_pred_proba=y_pred_proba,
        target_precision=0.75,
    )
    matrix["precision_at_k"] = {
        **_to_jsonable(pak_dict),
        "recommended_k": recommended.get("recommended_k"),
        "recommended_threshold": _json_safe_float(recommended.get("threshold")),
        "recommended_precision": _json_safe_float(recommended.get("precision")),
    }
    matrix["recommend_k"] = {
        "recommended_k": recommended.get("recommended_k"),
        "threshold": _json_safe_float(recommended.get("threshold")),
        "precision": _json_safe_float(recommended.get("precision")),
        "target_precision": 0.75,
    }

    # 3. expectancy + sharpe_proxy（factories，同 service）
    expectancy_payload: Optional[dict[str, Any]] = None
    sharpe_proxy_val: Optional[float] = None
    try:
        calc = create_expectancy_calculator()
        thr = float(recommended.get("threshold") or 0.6)
        exp_result = calc.estimate_expectancy(
            price_changes=price_changes,
            predicted_proba=y_pred_proba,
            threshold=thr,
        )
        trade_returns = price_changes[y_pred_proba >= thr]
        sharpe_proxy_val = calc.calculate_sharpe_proxy(
            trade_returns if len(trade_returns) > 0 else np.array([])
        )
        expectancy_payload = {
            **_to_jsonable(
                exp_result.to_dict() if hasattr(exp_result, "to_dict") else exp_result
            ),
            "sharpe_proxy": _json_safe_float(sharpe_proxy_val),
            "threshold_used": thr,
        }
    except Exception as exc:  # noqa: BLE001
        expectancy_payload = {"error": str(exc)}
    matrix["expectancy"] = expectancy_payload
    matrix["sharpe_proxy"] = _json_safe_float(sharpe_proxy_val)

    # 4. bootstrap_ci（n_bootstrap=200 同產線）
    bootstrap_ci: dict[str, Any] = {}
    try:
        boot = create_bootstrap_estimator()
        for metric in ("auc", "pr_auc"):
            try:
                ci_result = boot.bootstrap_confidence_interval(
                    y_true=y,
                    y_pred_proba=y_pred_proba,
                    metric=metric,
                    n_bootstrap=200,
                    confidence=0.9,
                )
                bootstrap_ci[metric] = _to_jsonable(
                    ci_result.to_dict() if hasattr(ci_result, "to_dict") else ci_result
                )
            except Exception as exc:  # noqa: BLE001
                bootstrap_ci[metric] = {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        bootstrap_ci = {"error": str(exc)}
    matrix["bootstrap_ci"] = bootstrap_ci

    # 5. permutation importance（service: n_repeats=5）
    try:
        perm = analyzer.calculate_permutation_importance(X, y, 5)
        matrix["permutation_importance"] = _to_jsonable(
            perm.to_dict() if hasattr(perm, "to_dict") else perm
        )
    except Exception as exc:  # noqa: BLE001
        matrix["permutation_importance"] = {"error": str(exc)}

    # 6. fold importance stability
    try:
        fold_stab = analyzer.calculate_fold_importance_stability(
            X, y, CV_FOLDS, True, timestamps
        )
        matrix["fold_importance_stability"] = _to_jsonable(
            fold_stab.to_dict() if hasattr(fold_stab, "to_dict") else fold_stab
        )
    except Exception as exc:  # noqa: BLE001
        matrix["fold_importance_stability"] = {"error": str(exc)}

    # 7. shap_sample（service: max 200, rng seed 42）
    max_shap_samples = 200
    sample_size = min(len(X), max_shap_samples)
    rng = np.random.default_rng(42)
    sample_indices = rng.choice(len(X), size=sample_size, replace=False)
    sample_indices_sorted = np.sort(sample_indices)
    if isinstance(X, pd.DataFrame):
        sample_values = X.iloc[sample_indices_sorted].to_numpy(dtype=float)
    else:
        sample_values = np.asarray(X, dtype=float)[sample_indices_sorted]
    matrix["shap_sample"] = {
        "sample_size": int(sample_size),
        "feature_names": feature_names,
        "indices_sha256": _hash_index_identity(sample_indices_sorted.astype(np.int64)),
        "samples_sha256": _hash_float_array(sample_values.reshape(-1)),
        "shape": list(sample_values.shape),
    }

    # 8. cross_symbol — excluded（明列）
    matrix["cross_symbol_validation"] = {
        "excluded": True,
        "reason": SERVICE_MATRIX_EXCLUDES["cross_symbol_validation"],
        "value": None,
    }

    # 矩陣整體 value hash（--check / F2）
    matrix_for_hash = {
        k: matrix.get(k)
        for k in SERVICE_MATRIX_KEYS
        if k in matrix
    }
    matrix["matrix_value_sha256"] = _sha256_bytes(
        json.dumps(
            matrix_for_hash,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    )
    matrix["matrix_keys"] = list(SERVICE_MATRIX_KEYS)
    present = [k for k in SERVICE_MATRIX_KEYS if k in matrix]
    matrix["matrix_keys_present"] = present
    missing = [k for k in SERVICE_MATRIX_KEYS if k not in matrix]
    if missing:
        raise RuntimeError(f"service matrix missing keys: {missing}")
    return matrix


def _run_model_face(
    X: pd.DataFrame,
    y: np.ndarray,
    timestamps: list[int],
    price_changes: np.ndarray,
) -> tuple[dict[str, Any], Any]:
    """軌2：XGBoostAnalyzer.train_model + service 全矩陣 + fit/eval index identity。"""
    n = len(y)
    fit_idx, eval_idx = _time_series_fit_eval_indices(n, EVAL_SIZE)
    fit_hash = _hash_index_identity(fit_idx)
    eval_hash = _hash_index_identity(eval_idx)

    analyzer = create_xgboost_analyzer()
    # 覆寫 default params 以固定可重現
    analyzer.default_params = {**analyzer.default_params, **XGB_BASELINE_PARAMS}
    performance = analyzer.train_model(
        X=X,
        y=y,
        feature_names=list(X.columns),
        early_stopping_rounds=5,
        eval_size=EVAL_SIZE,
        xgboost_params=XGB_BASELINE_PARAMS,
        cv_folds=CV_FOLDS,
        time_series_split=True,
        timestamps=timestamps,
    )

    # ModelPerformance → dict（兼容 dataclass / 物件）
    if hasattr(performance, "__dict__"):
        perf_raw = dict(performance.__dict__)
    elif isinstance(performance, dict):
        perf_raw = dict(performance)
    else:
        perf_raw = {"repr": repr(performance)}

    # 可 JSON 化
    perf_json: dict[str, Any] = {}
    for k, v in perf_raw.items():
        if k.startswith("_"):
            continue
        if isinstance(v, (int, str, bool)) or v is None:
            perf_json[k] = v
        elif isinstance(v, float):
            perf_json[k] = _json_safe_float(v)
        elif isinstance(v, (list, dict)):
            try:
                json.dumps(v, allow_nan=False)
                perf_json[k] = v
            except (TypeError, ValueError):
                perf_json[k] = str(v)
        else:
            fv = _json_safe_float(v)
            perf_json[k] = fv if fv is not None else str(v)

    # importance top（in-sample research 欄位，legacy 全樣本）
    try:
        importance = analyzer.calculate_feature_importance(
            list(X.columns), method="gain", top_n=10
        )
        if isinstance(importance, dict):
            imp_payload = {
                str(k): _json_safe_float(v) for k, v in importance.items()
            }
        elif isinstance(importance, list):
            imp_payload = {
                str(getattr(fi, "feature", i)): _json_safe_float(
                    getattr(fi, "importance", None)
                )
                for i, fi in enumerate(importance)
            }
        else:
            imp_payload = {"raw": str(importance)}
    except Exception as exc:  # noqa: BLE001
        imp_payload = {"error": str(exc)}

    # B0-F1 service 全矩陣
    service_matrix = _run_model_service_matrix(
        analyzer, X, y, timestamps, price_changes
    )

    model = analyzer.model
    payload = {
        "caller": "XGBoostAnalyzer.train_model(time_series_split=True)",
        "service_caller": (
            "mirrors api.services.xgboost_task_service post-fit matrix"
        ),
        "n_samples": int(n),
        "n_features": int(X.shape[1]),
        "eval_size": EVAL_SIZE,
        "cv_folds": CV_FOLDS,
        "xgboost_params": dict(XGB_BASELINE_PARAMS),
        # 軌2 index identity（provenance oracle 用）
        "index_identity": {
            "fit_idx_hash": fit_hash,
            "eval_idx_hash": eval_hash,
            "fit_len": int(fit_idx.size),
            "eval_len": int(eval_idx.size),
            "fit_start": int(fit_idx[0]) if fit_idx.size else None,
            "fit_end": int(fit_idx[-1]) if fit_idx.size else None,
            "eval_start": int(eval_idx[0]) if eval_idx.size else None,
            "eval_end": int(eval_idx[-1]) if eval_idx.size else None,
            "split_kind": "time_series_prefix",
        },
        "model_performance": perf_json,
        "feature_importance_gain_top": imp_payload,
        "service_matrix": service_matrix,
        "performance_value_sha256": _hash_float_array(
            [
                perf_json.get("train_auc")
                if perf_json.get("train_auc") is not None
                else float("nan"),
                perf_json.get("cv_auc_mean")
                if perf_json.get("cv_auc_mean") is not None
                else float("nan"),
                perf_json.get("cv_auc_std")
                if perf_json.get("cv_auc_std") is not None
                else float("nan"),
                perf_json.get("overfitting_score")
                if perf_json.get("overfitting_score") is not None
                else float("nan"),
            ]
        ),
    }
    return payload, model


def _build_control_payload(
    regime_pit: dict[str, Any],
    factor_disabled: dict[str, Any],
) -> dict[str, Any]:
    """control 三路徑摘要（deep-equal 用；非修改路徑）。"""
    return {
        "schema_version": CONTROL_SCHEMA_VERSION,
        "kinds": list(CONTROL_KINDS),
        "regime_pit": {
            "labels_sha256": regime_pit.get("labels_sha256"),
            "len": regime_pit.get("len"),
            "name_set": regime_pit.get("name_set"),
            "value_counts": regime_pit.get("value_counts"),
            "expanding": True,
        },
        "factor_disabled": factor_disabled,
        "pattern_not_extracted": {
            "extracted": False,
            "reason": "control: IC/model default path does not call extract_decision_rules",
        },
    }


# ---------------------------------------------------------------------------
# Per-symbol baseline
# ---------------------------------------------------------------------------
def run_one(run: dict[str, str]) -> dict[str, Any]:
    symbol = run["symbol"]
    timeframe = run["timeframe"]
    config_hash = run["config_hash"]

    h5_path, meta_path = _resolve_la0_feature_inputs(run)
    print(f"[gen_baseline] {symbol}/{timeframe}: features={h5_path.name}")

    features_df = _read_features_h5(h5_path, symbol, timeframe)
    close, volume, _kline_ts = _load_kline_close_volume(symbol, timeframe)

    # features 與 kline 對齊（features 可能是 tail 子集）
    close_feat = close.reindex(features_df.index)
    if close_feat.isna().all():
        # B0-F6：禁 silent tail-align（timestamp 不重疊 → hard fail）
        raise RuntimeError(
            f"{symbol}/{timeframe}: features index does not overlap kline "
            "timestamps; refusing silent tail-align (B0-F6). "
            "Check LA-0 feature HDF5 timestamps vs kline_cache.h5."
        )
    n_aligned = int(close_feat.notna().sum())
    if n_aligned < max(50, int(0.5 * len(features_df))):
        raise RuntimeError(
            f"{symbol}/{timeframe}: sparse kline overlap "
            f"({n_aligned}/{len(features_df)}); refusing silent fill"
        )
    vol_feat = volume.reindex(features_df.index) if volume is not None else None

    X, y, _positions, timestamps = _align_xy(features_df, close_feat)

    # face configs → inputs/*
    _write_face_config(
        symbol,
        timeframe,
        "pattern",
        {
            "face": "pattern",
            "caller": "PatternExtractor.extract_decision_rules",
            "split": None,
            "note": "legacy full-sample quantiles + y[mask].mean confidence",
        },
    )
    _write_face_config(
        symbol,
        timeframe,
        "regime_fit_global",
        {
            "face": "regime_fit_global",
            "caller": "RegimeDetector.detect",
            "expanding": False,
            "n_clusters": 4,
            "lookback": 55,
        },
    )
    _write_face_config(
        symbol,
        timeframe,
        "factor",
        {
            "face": "factor",
            "enabled": True,
            "modules": ["gram_schmidt", "pca", "exposure"],
            "proxy_kind_legacy": "forward_label_series",
        },
    )
    _write_face_config(
        symbol,
        timeframe,
        "model",
        {
            "face": "model",
            "caller": "XGBoostAnalyzer.train_model",
            "time_series_split": True,
            "eval_size": EVAL_SIZE,
            "cv_folds": CV_FOLDS,
            "xgboost_params": XGB_BASELINE_PARAMS,
            "return_type": "simple",
        },
    )

    # price_changes = next-bar simple return（service expectancy 用）
    price_changes = (
        close_feat.pct_change()
        .shift(-1)
        .reindex(X.index)
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
    )

    # ---- ④ model（先跑，供 pattern 用同一 model）----
    t0 = time.perf_counter()
    model_payload, model = _run_model_face(X, y, timestamps, price_changes)
    sm = model_payload.get("service_matrix") or {}
    print(
        f"[gen_baseline] {symbol}/{timeframe}: model "
        f"fit_hash={model_payload['index_identity']['fit_idx_hash'][:12]}… "
        f"service_keys={sm.get('matrix_keys_present')} "
        f"wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- ① pattern ----
    t0 = time.perf_counter()
    pattern_payload = _run_pattern_face(X, y, model)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: pattern "
        f"n_rules={pattern_payload['n_rules']} wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- ② regime_fit_global（全期 kline close，非 features tail）----
    t0 = time.perf_counter()
    regime_payload = _run_regime_face(close, volume, expanding=False)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: regime_fit_global "
        f"n={regime_payload['len']} names={regime_payload['name_set']} "
        f"wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- control regime_pit ----
    t0 = time.perf_counter()
    regime_pit = _run_regime_face(close, volume, expanding=True)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: control regime_pit "
        f"n={regime_pit['len']} wall={time.perf_counter()-t0:.2f}s"
    )

    # ---- ③ factor enabled=True ----
    t0 = time.perf_counter()
    # market_proxy legacy = forward simple return on feature index
    fwd_label = close_feat.pct_change().shift(-1)
    factor_payload = _run_factor_face(X, fwd_label, enabled=True)
    print(
        f"[gen_baseline] {symbol}/{timeframe}: factor "
        f"gs={factor_payload.get('gram_schmidt', {}).get('shape')} "
        f"wall={time.perf_counter()-t0:.2f}s"
    )

    factor_disabled = _run_factor_face(X, fwd_label, enabled=False)
    control_payload = _build_control_payload(regime_pit, factor_disabled)

    # ---- C-2 early-flip manifest ----
    early_flip = _pattern_early_flip_manifest(X, y)

    rows, sha16 = _kline_group_dataset_sha16(symbol, timeframe)
    baseline: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "spec_ref": "docs/IC_LA2_SPEC.md §G / B0.1",
        "todo_ref": "docs/IC_LA2_TODO.md Task 0.1",
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "kline_h5_group": KLINE_H5_GROUP_TEMPLATE.format(
            symbol=symbol, timeframe=timeframe
        ),
        "input_contract": {
            "features_h5": str(h5_path.relative_to(REPO_ROOT)),
            "meta_json": str(meta_path.relative_to(REPO_ROOT)),
            "kline_cache": str(KLINE_H5_PATH.relative_to(REPO_ROOT)),
            "kline_rows": rows,
            "kline_sha16": sha16,
            "callers": {
                "pattern": "PatternExtractor.extract_decision_rules",
                "regime_fit_global": "RegimeDetector.detect(expanding=False)",
                "factor": "FactorOrthogonalizer + FactorExposureAnalyzer",
                "model": "XGBoostAnalyzer.train_model(time_series_split=True)",
            },
            "winsorized_listed": False,
            "note": "winsorized excluded (DEC-1 disable → oracle=raises)",
        },
        "canonical_mutation": {
            "m_trunc": "n_keep=int(0.75*n)",
            "m_trunc_ratio": M_TRUNC_RATIO,
            "early_window": "[0, int(2/3*n_keep))",
            "early_window_ratio": EARLY_WINDOW_RATIO,
        },
        # 四面
        "pattern": pattern_payload,
        "regime_fit_global": regime_payload,
        "factor": factor_payload,
        "model": model_payload,
        # control
        "control": control_payload,
        "early_flip_manifest": early_flip,
    }
    return baseline


# ---------------------------------------------------------------------------
# --check / main
# ---------------------------------------------------------------------------
def _assert_early_flip_sides(manifest: dict[str, Any], name: str) -> None:
    """--check assert ②：C-2 early-flip 門檻/confidence 兩側 len>0。"""
    pattern = (manifest or {}).get("pattern") or {}
    n_th = int(pattern.get("n_threshold_flip") or 0)
    n_cf = int(pattern.get("n_confidence_flip") or 0)
    # 兩側 = threshold 側 + confidence 側（TODO: C-2 early-flip manifest 兩側 len>0）
    if n_th <= 0 or n_cf <= 0:
        raise SystemExit(
            f"{name}: C-2 early-flip sides empty "
            f"(n_threshold_flip={n_th}, n_confidence_flip={n_cf}); "
            "expected both > 0"
        )
    if len(pattern.get("threshold_flip_features") or []) != n_th:
        raise SystemExit(f"{name}: threshold_flip_features length mismatch")
    if len(pattern.get("confidence_flip_features") or []) != n_cf:
        raise SystemExit(f"{name}: confidence_flip_features length mismatch")


def _assert_model_index_identity(model: dict[str, Any], name: str) -> None:
    """--check assert ③a：軌2 index identity 記錄齊全。"""
    idx = (model or {}).get("index_identity") or {}
    for key in ("fit_idx_hash", "eval_idx_hash", "fit_len", "eval_len"):
        if key not in idx or idx[key] in (None, "", 0):
            # fit_len/eval_len 允許 >0 檢查
            if key in ("fit_len", "eval_len") and int(idx.get(key) or 0) > 0:
                continue
            if key.endswith("_hash") and isinstance(idx.get(key), str) and len(idx[key]) == 64:
                continue
            raise SystemExit(f"{name}: model.index_identity missing/invalid {key}={idx.get(key)!r}")
    if int(idx.get("fit_len") or 0) <= 0 or int(idx.get("eval_len") or 0) <= 0:
        raise SystemExit(f"{name}: model.index_identity fit/eval len must be >0")
    if not isinstance(idx.get("fit_idx_hash"), str) or len(idx["fit_idx_hash"]) != 64:
        raise SystemExit(f"{name}: fit_idx_hash must be sha256 hex")
    if not isinstance(idx.get("eval_idx_hash"), str) or len(idx["eval_idx_hash"]) != 64:
        raise SystemExit(f"{name}: eval_idx_hash must be sha256 hex")
    # recompute from lengths + split contract
    n = int(idx["fit_len"]) + int(idx["eval_len"])
    fit_idx, eval_idx = _time_series_fit_eval_indices(n, EVAL_SIZE)
    if _hash_index_identity(fit_idx) != idx["fit_idx_hash"]:
        raise SystemExit(f"{name}: fit_idx_hash recompute mismatch")
    if _hash_index_identity(eval_idx) != idx["eval_idx_hash"]:
        raise SystemExit(f"{name}: eval_idx_hash recompute mismatch")


def _assert_path_keys(baseline: dict[str, Any], name: str) -> None:
    """--check assert ③b：四面鍵齊全（winsorized 除外）。"""
    missing = [k for k in PATH_KEYS if k not in baseline]
    if missing:
        raise SystemExit(f"{name}: baseline missing PATH_KEYS {missing}")
    if "winsorized" in baseline:
        raise SystemExit(f"{name}: winsorized must not be listed in baseline")
    # control 亦需存在
    if "control" not in baseline:
        raise SystemExit(f"{name}: baseline missing control")
    control = baseline["control"]
    for kind in CONTROL_KINDS:
        if kind not in control:
            raise SystemExit(f"{name}: control missing kind {kind!r}")


def _dotted_get(obj: Any, path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def extract_face_value_hashes(baseline: dict[str, Any]) -> dict[str, Any]:
    """抽出每面關鍵值（供 F2 freeze / dump）。"""
    out: dict[str, Any] = {}
    for path in FACE_VALUE_HASH_PATHS:
        out[path] = _dotted_get(baseline, path)
    return out


def _assert_service_matrix(model: dict[str, Any], name: str) -> None:
    """--check：service 全矩陣鍵齊 + exclude 明列。"""
    sm = (model or {}).get("service_matrix")
    if not isinstance(sm, dict):
        raise SystemExit(f"{name}: model.service_matrix missing (B0-F1)")
    for key in SERVICE_MATRIX_KEYS:
        if key not in sm:
            raise SystemExit(f"{name}: service_matrix missing key {key!r}")
    mv = sm.get("matrix_value_sha256")
    if not isinstance(mv, str) or len(mv) != 64:
        raise SystemExit(f"{name}: service_matrix.matrix_value_sha256 invalid")
    excl = sm.get("exclude") or {}
    for ek, reason in SERVICE_MATRIX_EXCLUDES.items():
        if ek not in excl:
            raise SystemExit(f"{name}: service_matrix.exclude missing {ek!r}")
        if not excl.get(ek):
            raise SystemExit(f"{name}: service_matrix.exclude[{ek!r}] empty reason")
    # cross_symbol must be explicit excluded
    csv = sm.get("cross_symbol_validation") or {}
    if not csv.get("excluded"):
        raise SystemExit(f"{name}: cross_symbol_validation must be excluded at B0")


def _assert_frozen_value_hashes(data: dict[str, Any], name: str, path: Path) -> None:
    """B0-F2：file sha256 literal + 每面關鍵值 literal；竄改任一面 → FAIL。"""
    file_sha = _sha256_file(path)
    expected_file = EXPECTED_BASELINE_FILE_SHA256.get(name) or ""
    if not expected_file or len(expected_file) != 64:
        raise SystemExit(
            f"{name}: EXPECTED_BASELINE_FILE_SHA256 not frozen "
            f"(got {expected_file!r}); re-run --write and stamp literals"
        )
    if file_sha != expected_file:
        raise SystemExit(
            f"{name}: baseline file sha256 mismatch "
            f"(got={file_sha} expected={expected_file}) — face value freeze FAIL"
        )
    expected_faces = EXPECTED_FACE_VALUE_HASHES.get(name) or {}
    if not expected_faces:
        raise SystemExit(
            f"{name}: EXPECTED_FACE_VALUE_HASHES empty; stamp after --write"
        )
    live = extract_face_value_hashes(data)
    for k in FACE_VALUE_HASH_PATHS:
        if k not in expected_faces:
            raise SystemExit(f"{name}: frozen face hash missing key {k!r}")
        if live.get(k) != expected_faces[k]:
            raise SystemExit(
                f"{name}: face value hash mismatch at {k}: "
                f"got={live.get(k)!r} expected={expected_faces[k]!r}"
            )


def write_baselines() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    verify_kline_receipts()
    written: list[Path] = []
    for run in RUNS:
        baseline = run_one(run)
        out = OUTPUT_DIR / run["baseline_name"]
        out.write_bytes(_canonical_json_bytes(baseline))
        file_sha = _sha256_file(out)
        faces = extract_face_value_hashes(baseline)
        print(
            f"[gen_baseline] wrote {out.name} "
            f"sha256={file_sha} "
            f"keys={list(PATH_KEYS)}"
        )
        print(
            f"[gen_baseline] FACE_HASHES[{out.name!r}] = "
            f"{json.dumps(faces, ensure_ascii=False, sort_keys=True)}"
        )
        written.append(out)
    return written


def check_baselines() -> None:
    """--check：kline / early-flip / index / PATH_KEYS / service matrix / value freeze。"""
    verify_kline_receipts()  # assert ①
    for run in RUNS:
        path = OUTPUT_DIR / run["baseline_name"]
        if not path.is_file():
            raise SystemExit(f"baseline missing: {path} (run without --check first)")
        data = json.loads(path.read_text(encoding="utf-8"))
        name = path.name
        # assert ② C-2 early-flip
        _assert_early_flip_sides(data.get("early_flip_manifest") or {}, name)
        # assert ③ 軌2 + 四面
        _assert_model_index_identity(data.get("model") or {}, name)
        _assert_path_keys(data, name)
        # assert service 全矩陣（F1）
        _assert_service_matrix(data.get("model") or {}, name)
        # kline receipt 內嵌一致
        expected = EXPECTED_KLINE[(run["symbol"], run["timeframe"])]
        ic = data.get("input_contract") or {}
        if int(ic.get("kline_rows") or -1) != int(expected["rows"]):
            raise SystemExit(
                f"{name}: embedded kline_rows mismatch "
                f"{ic.get('kline_rows')} vs {expected['rows']}"
            )
        if str(ic.get("kline_sha16") or "") != expected["sha16"]:
            raise SystemExit(
                f"{name}: embedded kline_sha16 mismatch "
                f"{ic.get('kline_sha16')} vs {expected['sha16']}"
            )
        # assert F2 凍結 value hash
        _assert_frozen_value_hashes(data, name, path)
        print(
            f"[gen_baseline] check OK {name} "
            f"threshold_flip={(data.get('early_flip_manifest') or {}).get('pattern', {}).get('n_threshold_flip')} "
            f"confidence_flip={(data.get('early_flip_manifest') or {}).get('pattern', {}).get('n_confidence_flip')} "
            f"fit_hash={((data.get('model') or {}).get('index_identity') or {}).get('fit_idx_hash', '')[:12]} "
            f"file_sha={_sha256_file(path)[:16]}"
        )
    print(
        "[gen_baseline] --check PASS "
        "(kline / C-2 early-flip / index+PATH_KEYS / service_matrix / frozen value hash)"
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="LA-2 B0 gen_baseline")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify frozen baselines (exit 0 iff 3 asserts pass)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate baseline JSON from real kline+features",
    )
    args = parser.parse_args(argv)

    if args.check and not args.write:
        check_baselines()
        return 0

    # default / --write：產生後若 --check 再驗
    write_baselines()
    if args.check:
        check_baselines()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
