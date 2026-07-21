#!/usr/bin/env python3
"""IC 1d B0 baseline 凍結腳本（Task 0.1）。

用法:
  python scripts/ic1d_baseline_freeze.py --profile p0
  python scripts/ic1d_baseline_freeze.py --profile p1   # B1 後重跑
  python scripts/ic1d_baseline_freeze.py --profile p3   # B3 後重跑

D-9 關鍵契約（與 ic1cfr_stopgap_freeze 的 `_ic_cache` 手塞路徑相反）:
  close carrier **必須**經 production `analyze()` → `_stage4_ic_calculation`
  (`ic_filter_orchestrator.py:2913-2930`) 寫入 `ic_results["close_series"]`，
  再由 analyze 收尾寫入 `_ic_cache`。**禁**手動塞 `_ic_cache["close_series"]`。

輸出:
  handoffs/ic1d_baseline/p0_before.json               （--profile p0；僅確定性 canonical）
  handoffs/ic1d_baseline/p0_before.provenance.json    （volatile sidecar；不參與 deep no-op）
  handoffs/ic1d_baseline/p1_after_rename.json
  handoffs/ic1d_baseline/p1_after_rename.provenance.json
  handoffs/ic1d_baseline/p3_after_failclosed.json
  handoffs/ic1d_baseline/p3_after_failclosed.provenance.json
  handoffs/ic1d_baseline/analyzer_oracle.json          （固定種子 real-OLS）

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

OUT_DIR = REPO_ROOT / "handoffs" / "ic1d_baseline"
KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ic_api_real_kline.py"

PROFILE_FILENAMES: dict[str, str] = {
    "p0": "p0_before.json",
    "p1": "p1_after_rename.json",
    "p3": "p3_after_failclosed.json",
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

    # C3：源端 close 必須有效（非空非全 NaN）；all-NaN raise 屬另票 production-hardening
    source_close = pd.to_numeric(kline["close"], errors="coerce")
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


def build_baseline_payload(
    report: Any,
    *,
    profile: str,
    source_close_finite: Optional[str] = None,
    cache_close_finite: Optional[str] = None,
) -> dict[str, Any]:
    """組 p0/p1/p3 **golden** JSON 本體（僅確定性 canonical 內容）。

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
    """`p0_before.json` → `p0_before.provenance.json`。"""
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
    # 源端 close 有效（C3）；cache 內 close 可能因 production reindex 產 NaN，不放寬檢查
    src_finite_label = _finite_count_label(source_close)
    cache_close = None
    if orch._ic_cache is not None:
        cache_close = orch._ic_cache.get("close_series")
    cache_finite_label = _finite_count_label(
        cache_close if isinstance(cache_close, pd.Series) else None
    )
    logger.info(
        "source_close_finite=%s cache_close_finite=%s "
        "(C3 source gate only; cache all-NaN = production-hardening 另票)",
        src_finite_label,
        cache_finite_label,
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
    out_path = OUT_DIR / golden_name
    sidecar_path = provenance_sidecar_path(out_path)
    raw_digest = _write_json(out_path, payload)
    prov_digest = _write_json(sidecar_path, provenance)

    oracle = build_analyzer_oracle()
    oracle_path = OUT_DIR / "analyzer_oracle.json"
    oracle_digest = _write_json(oracle_path, oracle)

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
    print(f"wrote {oracle_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"analyzer_oracle_sha256={oracle_digest}")
    print(f"analyzer_oracle.alpha={oracle.get('alpha')}")
    print(f"analyzer_oracle.r_squared={oracle.get('r_squared')}")
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
        help="baseline profile: p0 | p1 | p3",
    )
    args = parser.parse_args(argv)
    return freeze_profile(args.profile)


if __name__ == "__main__":
    raise SystemExit(main())
