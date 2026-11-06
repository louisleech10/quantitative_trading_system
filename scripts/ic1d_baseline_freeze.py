#!/usr/bin/env python3
"""IC 1d 現行基準凍結腳本（原 B0 Task 0.1；ICPERF 諮詢 r119 改版）。

用法:
  python scripts/ic1d_baseline_freeze.py --profile current

r119（`handoffs/reconcile/20261106-icperf-x-consult-r119/synth.md`）：基準移至受版控之 `tests/_golden/ic1d/`，只留
現行基準 `current.json`（舊 p0／p1／p3 係收盤價載體全空時產生之錯值，退役）；寫檔前先驗 (1) 收盤價載體非空、索引等
於特徵索引、全有限且逐時刻等於源端同時刻收盤價，(2) factor_exposure 與獨立參考實作逐值一致——任一不符即拒寫。
analyzer OLS oracle 改由測試內即時計算，本腳本不再輸出。

D-9 關鍵契約（與 ic1cfr_stopgap_freeze 的 `_ic_cache` 手塞路徑相反）:
  close carrier **必須**經 production `analyze()` → `_stage4_ic_calculation`
  (`ic_filter_orchestrator.py:2913-2930`) 寫入 `ic_results["close_series"]`，
  再由 analyze 收尾寫入 `_ic_cache`。**禁**手動塞 `_ic_cache["close_series"]`。

輸出:
  tests/_golden/ic1d/current.json               （--profile current；僅確定性 canonical）
  tests/_golden/ic1d/current.provenance.json    （volatile sidecar；不參與數值比對）

凍結合約（B0fix-provenance）:
  被 diff 的 golden 只含確定性內容（results / module_summary / fixture_sha256 /
  source_close_finite / cache_close_finite / counts / canonical_sha256）。
  generated_at / generated_by / profile / total_execution_time_s / lineage
  一律寫 sidecar，零-allow deep no-op 跨 profile 可比。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import h5py
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

OUT_DIR = REPO_ROOT / "tests" / "_golden" / "ic1d"
KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ic_api_real_kline.py"

PROFILE_FILENAMES: dict[str, str] = {
    "current": "current.json",
}
ALLOWED_PROFILES: frozenset[str] = frozenset(PROFILE_FILENAMES)

# analyzer real-OLS 固定種子（P1 逐欄比對用；不經 deep 管線）
ANALYZER_ORACLE_SEED = 20260721
ANALYZER_ORACLE_N = 120
ANALYZER_ORACLE_N_FACTORS = 3

# 漂移欄（canonical hash 剔除）。golden 已不含 volatile provenance，
# 此集為防禦性殘留（若 sidecar 誤併入或歷史欄位回潮）。
# 注意：profile / generated_by 亦不在 golden；勿再寫入被 diff 本體。
CANONICAL_EXCLUDE_JSON_PATHS: frozenset[str] = frozenset(
    {
        "generated_at",
        "generated_by",
        "profile",
        "lineage",
        "lineage.generated_at",
        "total_execution_time_s",
        "deep_analysis_errors.*.timestamp",
    }
)

# golden 禁止出現的 volatile 頂層鍵（sidecar 專用）
GOLDEN_VOLATILE_TOP_KEYS: frozenset[str] = frozenset(
    {
        "generated_at",
        "generated_by",
        "profile",
        "lineage",
        "total_execution_time_s",
    }
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def _is_non_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return not math.isfinite(float(value))
    return False


def _sanitize_for_strict_json(obj: Any) -> Any:
    """遞迴轉 JSON 可序列化；非有限 number → null（禁止 NaN 字面落檔）。"""
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_strict_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_strict_json(v) for v in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return _sanitize_for_strict_json(asdict(obj))
    if isinstance(obj, np.ndarray):
        return _sanitize_for_strict_json(obj.tolist())
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        fv = float(obj)
        return fv if math.isfinite(fv) else None
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if _is_non_finite_number(obj):
        return None
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, pd.Series):
        return _sanitize_for_strict_json(obj.to_dict())
    if isinstance(obj, pd.DataFrame):
        return _sanitize_for_strict_json(obj.to_dict(orient="list"))
    return obj


def _path_matches_exclude(path: str, patterns: frozenset[str]) -> bool:
    """精確 JSON-path 匹配：點分隔；pattern 中 * 僅匹配單一 list index 段。"""
    if path in patterns:
        return True
    parts = path.split(".")
    for pattern in patterns:
        p_parts = pattern.split(".")
        if len(p_parts) != len(parts):
            continue
        ok = True
        for pp, actual in zip(p_parts, parts):
            if pp == "*":
                if not actual.isdigit():
                    ok = False
                    break
                continue
            if pp != actual:
                ok = False
                break
        if ok:
            return True
    return False


def strip_canonical_excludes(
    obj: Any,
    *,
    path: str = "",
    patterns: frozenset[str] = CANONICAL_EXCLUDE_JSON_PATHS,
) -> Any:
    """回傳剔除精確 JSON-path 漂移欄後的 deep copy。"""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            child = f"{path}.{k}" if path else str(k)
            if _path_matches_exclude(child, patterns):
                continue
            out[str(k)] = strip_canonical_excludes(v, path=child, patterns=patterns)
        return out
    if isinstance(obj, list):
        out_list: list[Any] = []
        for i, v in enumerate(obj):
            child = f"{path}.{i}" if path else str(i)
            if _path_matches_exclude(child, patterns):
                continue
            out_list.append(strip_canonical_excludes(v, path=child, patterns=patterns))
        return out_list
    return obj


def canonical_sha256(payload: dict[str, Any]) -> str:
    """剔漂移 path 後 sort_keys dump → sha256。"""
    stripped = strip_canonical_excludes(payload)
    text = json.dumps(stripped, sort_keys=True, allow_nan=False, ensure_ascii=False)
    if not text.endswith("\n"):
        text = text + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    """寫 sort_keys JSON，回傳檔案 sha256。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, allow_nan=False, ensure_ascii=False)
    if not text.endswith("\n"):
        text = text + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_h5(
    path: Path,
    key: str,
    values: np.ndarray,
    timestamps: np.ndarray,
    names: list[str],
) -> None:
    """以 IC reader 使用的 flat data/ group schema 寫入暫存 H5。"""
    with h5py.File(path, "w") as handle:
        if key == "features":
            # FFNAME SPEC v18 Task 3.4 之 IC 交接 h5 命名世代閘：寫出端蓋現行版（特徵由現行碼自真實 kline 即時算出）；
            # 缺此屬性時讀取端 FeatureNamingVersionError（ICPERF ㊻ 施工時發現本檔 5 條整合測試自 FFNAME 起紅）
            from momentum.FeatureEngineering.feature_naming import stamp_h5_feature_naming_version

            stamp_h5_feature_naming_version(handle.attrs)
        group = handle.create_group("data")
        group.create_dataset(key, data=values, compression="gzip")
        group.create_dataset("timestamps", data=timestamps, compression="gzip")
        name_key = "feature_names" if key == "features" else "label_names"
        dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(
            name_key, data=np.asarray(names, dtype=object), dtype=dtype
        )


def prepare_real_kline_inputs(
    work_dir: Path,
) -> tuple[Path, Path, Path, Any, pd.Series]:
    """自真實 kline 建 features/labels/meta 暫存檔；回傳 source close（有效性檢查用）。

    不手塞 `_ic_cache`；close 僅供 C3 源端有效性斷言與 同源比對。
    """
    from momentum.factories import create_kline_storage_manager
    from tests.fixtures.ic_api_real_kline import (
        FEATURE_NAMES,
        SYMBOL,
        TIMEFRAME,
        build_real_kline_frames,
    )

    if not KLINE_CACHE.is_file():
        raise FileNotFoundError(f"requires_kline: missing {KLINE_CACHE}")
    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"fixture missing: {FIXTURE_PATH}")

    storage = create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent))
    kline = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    if kline is None or getattr(kline, "empty", True):
        raise RuntimeError(f"requires_kline: no data for {SYMBOL}/{TIMEFRAME}")

    # C3：源端 close 必須有效（非空非全 NaN）。r119：以 kline 之 timestamp 欄為索引（不經產品時間軸正規化），
    # 供凍結前逐時刻比對 cache 收盤價載體（`validate_baseline_close_carrier`）。
    source_close = pd.Series(
        pd.to_numeric(kline["close"], errors="coerce").to_numpy(dtype=np.float64),
        index=pd.Index(pd.to_numeric(kline["timestamp"], errors="raise").astype(np.int64), name="timestamp"),
        name="close",
    )
    if source_close.empty or bool(source_close.isna().all()):
        raise RuntimeError(
            "C3 FAIL: source kline close is empty or all-NaN "
            f"(symbol={SYMBOL} tf={TIMEFRAME})"
        )

    features, labels = build_real_kline_frames(kline)
    timestamps = features.index.to_numpy(dtype=np.int64, copy=True)

    features_path = work_dir / "features.h5"
    labels_path = work_dir / "labels.h5"
    meta_path = work_dir / "meta.json"
    _write_h5(
        features_path,
        "features",
        features.to_numpy(dtype=np.float64),
        timestamps,
        list(FEATURE_NAMES),
    )
    _write_h5(
        labels_path,
        "labels",
        labels.to_numpy(dtype=np.float64)[:, None],
        timestamps,
        ["return_5"],
    )
    meta: dict[str, Any] = {
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "case_id": "ic1d_baseline",
    }
    meta.update(
        {
            name: {
                "name": name,
                "category": "price_derived",
                "layer": 1,
                "data_source": "kline",
            }
            for name in FEATURE_NAMES
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return features_path, labels_path, meta_path, storage, source_close


def _build_advanced_config() -> Any:
    """advanced preset + factor_exposure enabled（其餘 deep 模組亦開，供 force 可選）。"""
    from momentum.Analysis.ic_config_schema import ICConfig

    raw = ICConfig().model_dump(by_alias=True)
    raw["feature_tiers"]["active_preset"] = "advanced"
    for section in (
        "factor_return",
        "factor_centrality",
        "trend_analysis",
        "parameter_sensitivity",
        "rolling_oos",
        "factor_orthogonalization",
        "factor_exposure",
        "long_short_analysis",
        "feature_quality_diagnostics",
        "net_ic_analysis",
    ):
        if isinstance(raw.get(section), dict):
            raw[section]["enabled"] = True
    return ICConfig.model_validate(raw)


def run_production_deep_analysis(
    *,
    force_modules: Optional[list[str]] = None,
) -> tuple[Any, Any, pd.Series]:
    """真實 kline → analyze（production close carrier）→ run_deep_analysis。

    回傳 (orchestrator, DeepAnalysisReport, source_close)。
    **不**寫入 `_ic_cache["close_series"]`；close 僅由 production 路徑注入。
    """
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    work_dir = Path(tempfile.mkdtemp(prefix="ic1d_baseline_"))
    features_path, labels_path, meta_path, kline_reader, source_close = (
        prepare_real_kline_inputs(work_dir)
    )

    config = _build_advanced_config()
    orch = ICFilterOrchestrator(config)
    # 禁寫 data_cache/reports（不改 production；僅測/腳本側旗標）
    orch._suppress_persist = True

    logger.info(
        "running production analyze (close carrier via _stage4_ic_calculation:2913-2930)"
    )
    orch.analyze(
        features_path=str(features_path),
        labels_path=str(labels_path),
        meta_path=str(meta_path),
        kline_reader=kline_reader,
    )

    # D-9：close 必須已由 production 路徑進入 cache（非本腳本手塞）
    if orch._ic_cache is None:
        raise RuntimeError("FAIL: _ic_cache is None after analyze()")
    close_series = orch._ic_cache.get("close_series")
    if close_series is None:
        raise RuntimeError(
            "FAIL D-9: _ic_cache['close_series'] is None after production analyze(); "
            "close carrier did not flow through :2913-2930"
        )

    modules = force_modules or ["factor_exposure"]
    logger.info("running run_deep_analysis force_modules=%s", modules)
    report = orch.run_deep_analysis(force_modules=list(modules))
    return orch, report, source_close


def _extract_portfolio_exposure(fe_body: Any) -> Optional[dict]:
    """自 factor_exposure 結果取 portfolio_exposure（頂層或 payload.summary）。"""
    if not isinstance(fe_body, dict):
        return None
    pe = fe_body.get("portfolio_exposure")
    if isinstance(pe, dict) and pe:
        return pe
    payload = fe_body.get("payload")
    summary: Any = None
    if is_dataclass(payload) and not isinstance(payload, type):
        summary = getattr(payload, "summary", None)
    elif isinstance(payload, dict):
        summary = payload.get("summary")
    if isinstance(summary, dict):
        pe2 = summary.get("portfolio_exposure")
        if isinstance(pe2, dict) and pe2:
            return pe2
    return None


def _finite_count_label(series: Optional[pd.Series]) -> str:
    """回傳 `finite/total` 字串；series 為 None 時 `none`。"""
    if series is None:
        return "none"
    arr = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    n_fin = int(np.isfinite(arr).sum())
    return f"{n_fin}/{len(arr)}"


class BaselineIntegrityError(RuntimeError):
    """r119：基準寫入前之完整性檢查不通過（拒寫，既有基準檔不變）。"""


def _epoch_keys(index: pd.Index, unit_ref: pd.Index) -> np.ndarray:
    """特徵時間索引 → 與源端 timestamp 欄同單位之整數 epoch（獨立於產品之時間軸正規化）。
    源端單位依數量級判定：> 1e11 ⇒ 毫秒，否則秒。"""
    unit = "ms" if len(unit_ref) and int(np.max(np.abs(unit_ref.to_numpy(dtype=np.int64)))) > 10**11 else "s"
    if isinstance(index, pd.DatetimeIndex):
        utc = index.tz_convert("UTC") if index.tz is not None else index.tz_localize("UTC")
        ns = utc.asi8
        return ns // (10**6 if unit == "ms" else 10**9)
    return pd.to_numeric(pd.Series(index), errors="raise").to_numpy(dtype=np.int64)


def validate_baseline_close_carrier(source_close: pd.Series, cache_close: Any, feature_index: pd.Index) -> None:
    """r119（CODEX-R119-P2-02、GROK-R119-P1-02）：IC1D 基準之收盤價載體須非空、索引等於特徵索引、全部有限，且逐時刻
    等於源端同時刻收盤價（`source_close` 以 kline timestamp 欄為索引）；任一不符 ⇒ BaselineIntegrityError。
    產品通用載體容許真實缺價（`_validate_close_carrier` 只擋全空），本檢查只用於此固定全有限基準。"""
    if not isinstance(cache_close, pd.Series) or len(cache_close) == 0:
        raise BaselineIntegrityError(f"cache 收盤價載體為空或非 Series（{type(cache_close).__name__}）")
    if not cache_close.index.equals(feature_index):
        raise BaselineIntegrityError("cache 收盤價載體索引不等於特徵索引")
    values = pd.to_numeric(cache_close, errors="coerce").to_numpy(dtype=np.float64)
    n_fin = int(np.isfinite(values).sum())
    if n_fin != len(values):
        raise BaselineIntegrityError(f"cache 收盤價載體有非有限值：有效 {n_fin}/{len(values)}")
    keys = _epoch_keys(feature_index, source_close.index)
    expected = source_close.reindex(pd.Index(keys)).to_numpy(dtype=np.float64)
    if not np.array_equal(values, expected):
        bad = int(np.sum(~(values == expected)))
        raise BaselineIntegrityError(f"cache 收盤價載體與源端同時刻收盤價不等：{bad}/{len(values)} 根")


def verify_exposure_independent_oracle(orch: Any, report: Any) -> dict[str, Any]:
    """r119（CODEX-R119-P1-01 等）：同一次執行之實際輸入（候選欄、cache 特徵與收盤價載體、有效設定）跑獨立曝險參考實作
    （`tests/momentum/Analysis/test_icperf_deep_orth_exposure.py` 之 `ref_factor_exposure_analyzer`，不呼叫產品模組）並
    逐欄比對（數值 rtol 1e-12、NaN 位置、欄集合、集中度離散欄）；不一致 ⇒ BaselineIntegrityError。回比對摘要。"""
    from tests.momentum.Analysis.test_icperf_deep_orth_exposure import (
        _all_consistent,
        compare_factor_exposure_analyzer,
    )

    cache = orch._ic_cache or {}
    names = [str(f["feature_name"]) for f in (report.candidate_selection or {}).get("features") or []]
    if not names:
        raise BaselineIntegrityError("深度分析候選欄為空，無從驗證 factor_exposure")
    factors = cache["features_df"][names]
    fe_cfg = orch._config.factor_exposure
    product = asdict(report)["results"]["factor_exposure"]
    res = compare_factor_exposure_analyzer(product, factors, cache.get("close_series"),
                                           str(fe_cfg.neutralization_mode), int(fe_cfg.neutralization_lookback),
                                           float(fe_cfg.max_single_exposure))
    bad = _all_consistent(res)
    if bad:
        raise BaselineIntegrityError(f"factor_exposure 與獨立參考實作不一致：{bad[:5]}")
    rels = [float(r["max_rel_diff"]) for r in res.values() if r.get("max_rel_diff") is not None]
    return {"n_fields": len(res), "features": names, "neutralization_mode": str(fe_cfg.neutralization_mode),
            "max_rel_diff": max(rels) if rels else None}


def build_baseline_payload(
    report: Any,
    *,
    profile: str,
    source_close_finite: Optional[str] = None,
    cache_close_finite: Optional[str] = None,
) -> dict[str, Any]:
    """組 **golden** JSON 本體（僅確定性 canonical 內容）。

    oracle 取得（C2）：module_summary **直接**自 DeepAnalysisReport.module_summary，
    非 `_serialize_deep_analysis`（該 serializer 只出 module_statuses）。

    C：`source_close_finite` / `cache_close_finite` 外顯進 golden（例 `1696/1696`、
    `0/512`）；**不**對 cache finite 做 >0 斷言（production reindex 全 NaN 另票）。

    volatile provenance（generated_at / generated_by / profile / lineage /
    total_execution_time_s）**不**寫入 golden；見 `build_provenance_sidecar`。
    `profile` 參數僅供呼叫端對齊 API，不進 golden 本體。
    """
    del profile  # 不進 golden；保留參數相容既有 caller / 測試

    # 直接取 report 屬性（BLOCKING C2）
    module_summary = dict(getattr(report, "module_summary", {}) or {})
    results_raw = getattr(report, "results", {}) or {}
    results = _sanitize_for_strict_json(results_raw)

    fe_status = module_summary.get("factor_exposure")
    if fe_status == "skipped":
        raise SystemExit(
            f"FAIL: module_summary.factor_exposure={fe_status!r} must not be 'skipped'"
        )

    fe_body = results_raw.get("factor_exposure") if isinstance(results_raw, dict) else None
    pe = _extract_portfolio_exposure(fe_body)
    if not pe:
        raise SystemExit(
            "FAIL: results.factor_exposure portfolio_exposure missing or empty"
        )

    fixture_sha = (
        _sha256_file(FIXTURE_PATH) if FIXTURE_PATH.is_file() else None
    )
    # 僅確定性內容（跨 profile 應 byte/結構一致 → deep no-op 零-allow PASS）
    payload: dict[str, Any] = {
        "results": results if isinstance(results, dict) else {},
        "module_summary": module_summary,
        "fixture_sha256": fixture_sha,
        "completed_count": int(getattr(report, "completed_count", 0) or 0),
        "skipped_count": int(getattr(report, "skipped_count", 0) or 0),
        "failed_count": int(getattr(report, "failed_count", 0) or 0),
    }
    # C：close finite 外顯進 golden（源端 + cache carrier；不放寬有效性 gate）
    if source_close_finite is not None:
        payload["source_close_finite"] = source_close_finite
    if cache_close_finite is not None:
        payload["cache_close_finite"] = cache_close_finite

    leaked = GOLDEN_VOLATILE_TOP_KEYS.intersection(payload.keys())
    if leaked:
        raise SystemExit(
            f"FAIL: golden must not contain volatile keys: {sorted(leaked)}"
        )

    # hash over 確定性內容（尚無 canonical_sha256 鍵；亦不含 profile/壁鐘）
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def build_provenance_sidecar(
    report: Any,
    *,
    profile: str,
    golden_filename: str,
    source_close_finite: Optional[str] = None,
    cache_close_finite: Optional[str] = None,
) -> dict[str, Any]:
    """組 volatile provenance sidecar（不參與 deep no-op 比對）。

    欄位：generated_at / generated_by / profile / total_execution_time_s /
    lineage（整段）/ golden 檔名 / finite labels（複本便於 audit）。
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    fixture_sha = (
        _sha256_file(FIXTURE_PATH) if FIXTURE_PATH.is_file() else None
    )
    sidecar: dict[str, Any] = {
        "generated_at": generated_at,
        "generated_by": f"ic1d_baseline_freeze --profile {profile}",
        "profile": profile,
        "golden_filename": golden_filename,
        "total_execution_time_s": float(
            getattr(report, "total_execution_time_s", 0.0) or 0.0
        ),
        "lineage": {
            "fixture_sha256": fixture_sha,
            "fixture_path": FIXTURE_PATH.relative_to(REPO_ROOT).as_posix(),
            "git_head": _git_head(),
            "kline_cache": KLINE_CACHE.relative_to(REPO_ROOT).as_posix(),
            "generated_at": generated_at,
            "close_carrier": "production:_stage4_ic_calculation:2913-2930",
            "d9": "no_ad_hoc_ic_cache_close_series",
        },
        "canonical_exclude_json_paths": sorted(CANONICAL_EXCLUDE_JSON_PATHS),
    }
    if source_close_finite is not None:
        sidecar["source_close_finite"] = source_close_finite
    if cache_close_finite is not None:
        sidecar["cache_close_finite"] = cache_close_finite
    return sidecar


def provenance_sidecar_path(golden_path: Path) -> Path:
    """`current.json` → `current.provenance.json`。"""
    return golden_path.with_name(f"{golden_path.stem}.provenance.json")


def build_analyzer_oracle() -> dict[str, Any]:
    """固定種子直接呼叫 calculate_factor_attribution（caller=0，不經 deep）。

    B0 只 dump 現行欄位：alpha / r_squared / unexplained（==alpha）/ factor_betas / attribution。
    intercept 於 B1 正名後補。
    """
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer

    rng = np.random.default_rng(ANALYZER_ORACLE_SEED)
    n = ANALYZER_ORACLE_N
    portfolio = pd.Series(rng.normal(0.0, 0.01, n), name="portfolio")
    factor_returns = pd.DataFrame(
        rng.normal(0.0, 0.01, (n, ANALYZER_ORACLE_N_FACTORS)),
        columns=[f"f{i + 1}" for i in range(ANALYZER_ORACLE_N_FACTORS)],
    )
    analyzer = FactorExposureAnalyzer(config={})
    result = analyzer.calculate_factor_attribution(portfolio, factor_returns)

    alpha = result.get("alpha")
    r_squared = result.get("r_squared")
    unexplained = result.get("unexplained")
    # 現行契約：成功時 unexplained == alpha（同一 beta[0]）
    oracle: dict[str, Any] = {
        "generated_by": "ic1d_baseline_freeze.build_analyzer_oracle",
        "seed": ANALYZER_ORACLE_SEED,
        "n_rows": n,
        "n_factors": ANALYZER_ORACLE_N_FACTORS,
        "schema_note": (
            "B0 dumps existing keys only; intercept arrives in B1. "
            "unexplained==alpha under current analyzer contract."
        ),
        "alpha": float(alpha) if alpha is not None and math.isfinite(float(alpha)) else None,
        "r_squared": (
            float(r_squared)
            if r_squared is not None and math.isfinite(float(r_squared))
            else None
        ),
        "unexplained": (
            float(unexplained)
            if unexplained is not None and math.isfinite(float(unexplained))
            else None
        ),
        "factor_betas": _sanitize_for_strict_json(result.get("factor_betas") or {}),
        "attribution": _sanitize_for_strict_json(result.get("attribution") or {}),
    }
    return oracle


def freeze_profile(profile: str) -> int:
    """執行指定 profile 的 baseline dump。"""
    if profile not in ALLOWED_PROFILES:
        raise SystemExit(
            f"FAIL: unknown --profile {profile!r}; allowed={sorted(ALLOWED_PROFILES)}"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    orch, report, source_close = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )
    src_finite_label = _finite_count_label(source_close)
    cache = orch._ic_cache or {}
    cache_close = cache.get("close_series")
    cache_finite_label = _finite_count_label(
        cache_close if isinstance(cache_close, pd.Series) else None
    )
    # r119：寫任何檔之前驗收盤價載體與獨立 oracle；不符 ⇒ BaselineIntegrityError（既有基準檔不變）
    validate_baseline_close_carrier(source_close, cache_close, cache["features_df"].index)
    oracle_check = verify_exposure_independent_oracle(orch, report)
    logger.info(
        "source_close_finite=%s cache_close_finite=%s exposure_oracle_fields=%s",
        src_finite_label,
        cache_finite_label,
        oracle_check["n_fields"],
    )

    golden_name = PROFILE_FILENAMES[profile]
    payload = build_baseline_payload(
        report,
        profile=profile,
        source_close_finite=src_finite_label,
        cache_close_finite=cache_finite_label,
    )
    provenance = build_provenance_sidecar(
        report,
        profile=profile,
        golden_filename=golden_name,
        source_close_finite=src_finite_label,
        cache_close_finite=cache_finite_label,
    )
    provenance["exposure_oracle_check"] = oracle_check  # r119：獨立 oracle 比對摘要（含實際最大相對差）
    out_path = OUT_DIR / golden_name
    sidecar_path = provenance_sidecar_path(out_path)
    raw_digest = _write_json(out_path, payload)
    prov_digest = _write_json(sidecar_path, provenance)

    fe_status = payload["module_summary"].get("factor_exposure")
    fe_body = (payload.get("results") or {}).get("factor_exposure") or {}
    pe_keys = list((fe_body.get("portfolio_exposure") or {}).keys())
    lineage = provenance.get("lineage") or {}

    # 摘要（供 receipt；hot loop 不 log）
    print(f"wrote {out_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"raw_sha256={raw_digest}")
    print(f"canonical_sha256={payload['canonical_sha256']}")
    print(f"wrote {sidecar_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"provenance_sha256={prov_digest}")
    print(f"module_summary.factor_exposure={fe_status}")
    print(f"portfolio_exposure_n_keys={len(pe_keys)}")
    print(f"close_carrier={lineage.get('close_carrier')}")
    print(f"source_close_finite={payload.get('source_close_finite')}")
    print(f"cache_close_finite={payload.get('cache_close_finite')}")
    print(f"exposure_oracle_fields={oracle_check['n_fields']} features={len(oracle_check['features'])} "
          f"max_rel_diff={oracle_check['max_rel_diff']!r}")
    print(f"git_head={lineage.get('git_head')}")
    print(f"profile={provenance.get('profile')}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="IC 1d B0 baseline freeze (production close carrier, D-9)"
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(ALLOWED_PROFILES),
        help="baseline profile: current",
    )
    args = parser.parse_args(argv)
    return freeze_profile(args.profile)


if __name__ == "__main__":
    raise SystemExit(main())
