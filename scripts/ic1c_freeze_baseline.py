#!/usr/bin/env python3
"""IC1C baseline 凍結腳本(Task 0.1 / G-OLD; Phase1 G-NEW; Phase2 G-NEW2)。

用法:
  python scripts/ic1c_freeze_baseline.py --baseline old
  python scripts/ic1c_freeze_baseline.py --baseline new   # Phase 1:雙 run 三 profile
  python scripts/ic1c_freeze_baseline.py --baseline new2  # Phase 2 佔位
  python scripts/ic1c_freeze_baseline.py --self-test      # allowlist 負例

G-NEW:主 result=GROSS_ONLY(cost_enabled=False);次 result_cost_enabled=COST_ENABLED@10bps;
diff 對照寫死 allowlist(非自生成)。產出: handoffs/ic1c_baseline/g_{old,new,new2}.{json,sha256}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "handoffs" / "ic1c_baseline"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ic_api_real_kline.py"
KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"

# 注入特徵名(TODO Task 0.1 ④ 真 fixture 名;G-NEW 三注入 r5)
INJECT_TURNOVER_MISSING = "oc_return"
INJECT_GROSS_IC_MISSING = "hl_range"
INJECT_NEGATIVE_TURNOVER = "zscore_20"
# G-NEW/G-NEW2 不變欄比對排除集(三注入特徵)
G_COMPARE_EXCLUDE = frozenset(
    {INJECT_TURNOVER_MISSING, INJECT_GROSS_IC_MISSING, INJECT_NEGATIVE_TURNOVER}
)
# G-NEW 直開成本固定測試值(COST_ENABLED 樣本 run)
G_NEW_COST_BPS = 10.0

# ---------------------------------------------------------------------------
# Frozen 必變/允許變動 allowlist(T-F14)——寫死常數,禁由實際 diff 自生成
# 主結果=G-NEW GROSS_ONLY(config 預設 cost_enabled=False)
# ---------------------------------------------------------------------------
FEATURE_MUST_REMOVE_KEYS: frozenset[str] = frozenset({"net_ic"})
FEATURE_MUST_PRESERVE_KEYS: frozenset[str] = frozenset({"gross_ic", "turnover"})

# 主結果 GROSS_ONLY:相對 G-OLD feature 允許移除/新增/值變
FEATURE_GROSS_ALLOWED_REMOVED: frozenset[str] = frozenset(
    {
        "net_ic",
        "cost_bps",
        "cost_sensitivity",
        "breakeven_cost_bps",
        "profitable_after_cost",
    }
)
FEATURE_GROSS_ALLOWED_ADDED: frozenset[str] = frozenset(
    {
        "turnover_semantics",
        "net_factor_return",
    }
)
FEATURE_GROSS_ALLOWED_VALUE_CHANGE: frozenset[str] = frozenset(
    {
        "capacity",  # +calibration:"uncalibrated"
    }
)

# 次結果 COST_ENABLED 樣本(cost_enabled=True@10bps)相對 G-OLD
FEATURE_COST_ALLOWED_REMOVED: frozenset[str] = frozenset({"net_ic"})
FEATURE_COST_ALLOWED_ADDED: frozenset[str] = frozenset(
    {
        "turnover_semantics",
        "net_factor_return",
        "cost_drag_return",
        "cost_semantics",
    }
)
FEATURE_COST_ALLOWED_VALUE_CHANGE: frozenset[str] = frozenset(
    {
        "capacity",
        "breakeven_cost_bps",  # float → unavailable union
        "profitable_after_cost",  # bool → unavailable union
        "cost_bps",  # 5.0 → 10.0
        "cost_sensitivity",  # net_ic 列 → cost_drag_return 列
    }
)

# summary 級(主結果 GROSS_ONLY;含固定 value change 舊→新語意)
SUMMARY_ALLOWED_REMOVED: frozenset[str] = frozenset(
    {
        "avg_ic_loss_pct",
        "rank_correlation_gross_vs_net",
    }
)
SUMMARY_ALLOWED_ADDED: frozenset[str] = frozenset(
    {
        "evaluable_count",
        # COST_ENABLED 次結果才有 avg_cost_drag_return;主 GROSS 無
    }
)
SUMMARY_ALLOWED_VALUE_CHANGE: frozenset[str] = frozenset(
    {
        "total_analyzed",  # 5→4(第三注入 zscore_20 negative_turnover)
        "profitable_count",  # 3→0(1c evaluable 恒 0)
    }
)
# 固定 value change 期望(new 端);old 端不寫死以容 G-OLD 再凍
SUMMARY_REQUIRED_NEW_VALUES: dict[str, Any] = {
    "total_analyzed": 4,
    "profitable_count": 0,
    "evaluable_count": 0,
}

# COST_ENABLED 次結果 summary 額外允許
SUMMARY_COST_ALLOWED_ADDED: frozenset[str] = frozenset(
    {
        "evaluable_count",
        "avg_cost_drag_return",
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


def _sanitize_for_strict_json(
    obj: Any,
    path: str = "",
    non_finite_fields: list[str] | None = None,
) -> Any:
    """遞迴將非有限 number 轉 null,並記錄路徑(供 non_finite_fields)。"""
    if non_finite_fields is None:
        non_finite_fields = []

    if isinstance(obj, dict):
        return {
            str(k): _sanitize_for_strict_json(
                v,
                f"{path}.{k}" if path else str(k),
                non_finite_fields,
            )
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [
            _sanitize_for_strict_json(v, f"{path}[{i}]", non_finite_fields)
            for i, v in enumerate(obj)
        ]
    if _is_non_finite_number(obj):
        non_finite_fields.append(path if path else "<root>")
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        fv = float(obj)
        if not math.isfinite(fv):
            non_finite_fields.append(path if path else "<root>")
            return None
        return fv
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _load_fixture_frames() -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """依 tests/fixtures/ic_api_real_kline.py 衍生 features/labels(不跑 full deep pipeline)。"""
    from momentum.factories import create_kline_storage_manager
    from tests.fixtures.ic_api_real_kline import (
        FEATURE_NAMES,
        SYMBOL,
        TIMEFRAME,
        build_real_kline_frames,
    )

    if not KLINE_CACHE.is_file():
        raise FileNotFoundError(f"requires_kline: missing {KLINE_CACHE}")

    storage = create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent))
    kline = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    if kline is None or getattr(kline, "empty", True):
        raise RuntimeError(f"requires_kline: no data for {SYMBOL}/{TIMEFRAME}")

    features, labels = build_real_kline_frames(kline)
    return features, labels, list(FEATURE_NAMES)


def _spearman_ic_mean(feature: pd.Series, labels: pd.Series) -> float:
    aligned = pd.concat(
        [feature.rename("f"), labels.rename("y")],
        axis=1,
    ).dropna()
    if len(aligned) < 2:
        return float("nan")
    corr = spearmanr(
        aligned["f"].to_numpy(dtype=np.float64),
        aligned["y"].to_numpy(dtype=np.float64),
    ).correlation
    if corr is None or not np.isfinite(corr):
        return float("nan")
    return float(corr)


def _build_summary_and_turnover(
    features: pd.DataFrame,
    labels: pd.Series,
    feature_names: list[str],
) -> tuple[dict[str, dict], dict[str, float]]:
    """排序後逐 feat 建 summary(ic_mean=spearman)+turnover_data(quantile_turnover)。"""
    from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer

    ta = TurnoverAnalyzer({})
    # 確定性:feature 名排序
    ordered = sorted(feature_names)
    summary: dict[str, dict] = {}
    turnover_data: dict[str, float] = {}
    for name in ordered:
        series = features[name]
        summary[name] = {"ic_mean": _spearman_ic_mean(series, labels)}
        turnover_data[name] = float(ta.compute_quantile_turnover(series))
    return summary, turnover_data


def _inject_skipped(
    summary: dict[str, dict],
    turnover_data: dict[str, float],
) -> None:
    """具名 skipped 注入(真 fixture 特徵名)。"""
    if INJECT_TURNOVER_MISSING not in summary:
        raise KeyError(
            f"inject target missing from summary: {INJECT_TURNOVER_MISSING!r}"
        )
    if INJECT_GROSS_IC_MISSING not in summary:
        raise KeyError(
            f"inject target missing from summary: {INJECT_GROSS_IC_MISSING!r}"
        )
    turnover_data.pop(INJECT_TURNOVER_MISSING, None)
    summary[INJECT_GROSS_IC_MISSING]["ic_mean"] = float("nan")


def _default_net_ic_config() -> dict[str, Any]:
    """現行 default config(對齊 NetICAnalysisConfig / ic_config.yaml 現值)。"""
    return {
        "enabled": True,
        "default_cost_bps": 5.0,
        "slippage_bps": 2.0,
        "cost_scenarios": [1, 3, 5, 10, 20],
        "participation_rate": 0.01,
    }


def freeze_old() -> Path:
    """Task 0.1 G-OLD:fixture 衍生 → batch_analyze → g_old.{json,sha256}。"""
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer

    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"fixture missing: {FIXTURE_PATH}")

    features, labels, feature_names = _load_fixture_frames()
    summary, turnover_data = _build_summary_and_turnover(
        features, labels, feature_names
    )
    _inject_skipped(summary, turnover_data)

    analyzer = NetICAnalyzer(_default_net_ic_config())
    raw_result = analyzer.batch_analyze(summary, turnover_data)

    non_finite_fields: list[str] = []
    sanitized = _sanitize_for_strict_json(
        raw_result, path="result", non_finite_fields=non_finite_fields
    )
    # 路徑記相對 result 內容更易讀
    cleaned_paths = [
        p[len("result.") :] if p.startswith("result.") else p
        for p in non_finite_fields
    ]

    payload: dict[str, Any] = {
        "fixture_sha256": _sha256_file(FIXTURE_PATH),
        "git_head": _git_head(),
        "generated_by": "ic1c_freeze_baseline --baseline old",
        "non_finite_fields": sorted(cleaned_paths),
        "feature_names_input": sorted(feature_names),
        "injected_skips": {
            "turnover_missing": INJECT_TURNOVER_MISSING,
            "gross_ic_missing": INJECT_GROSS_IC_MISSING,
        },
        "result": sanitized,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "g_old.json"
    out_sha = OUT_DIR / "g_old.sha256"

    text = json.dumps(payload, sort_keys=True, allow_nan=False, ensure_ascii=False)
    # 尾端換行固定,避免跨工具 hash 漂移
    if not text.endswith("\n"):
        text = text + "\n"
    out_json.write_text(text, encoding="utf-8")

    digest = hashlib.sha256(out_json.read_bytes()).hexdigest()
    # shasum -c 格式:相對 repo root 路徑(執行端於 root 驗)
    rel = out_json.relative_to(REPO_ROOT).as_posix()
    out_sha.write_text(f"{digest}  {rel}\n", encoding="utf-8")

    print(f"wrote {rel}")
    print(f"sha256={digest}")
    print(f"features={len((sanitized or {}).get('features') or {})}")
    print(f"non_finite_fields={len(cleaned_paths)}")
    return out_json


def _inject_skipped_g_new(
    summary: dict[str, dict],
    turnover_data: dict[str, float],
) -> None:
    """G-NEW 三注入:turnover_missing / gross_ic NaN / negative turnover。"""
    _inject_skipped(summary, turnover_data)
    if INJECT_NEGATIVE_TURNOVER not in summary:
        raise KeyError(
            f"inject target missing from summary: {INJECT_NEGATIVE_TURNOVER!r}"
        )
    turnover_data[INJECT_NEGATIVE_TURNOVER] = -0.2


def _canonical_cost_drag(cost_bps: float, turnover: float) -> float:
    """獨立 oracle(T-F5):禁 import net_ic_analyzer;內嵌 numpy 一行。"""
    # 與 analyzer 公式同形,但不得 import analyzer
    return float((float(cost_bps) / 10000.0) * float(turnover))


def _profile_keys_for_feature(feat: dict[str, Any]) -> frozenset[str]:
    return frozenset(feat.keys())


def _expected_skip_reasons() -> dict[str, str]:
    return {
        INJECT_TURNOVER_MISSING: "turnover_missing",
        INJECT_GROSS_IC_MISSING: "gross_ic_missing",
        INJECT_NEGATIVE_TURNOVER: "negative_turnover",
    }


def _assert_g_new_profiles(
    features: dict[str, dict],
    *,
    expected_non_skip_schema: frozenset[str],
    profile_label: str,
) -> None:
    """鍵集合 == SCHEMA_*(import 專檔,禁複製)。"""
    from tests.momentum.Analysis.test_net_ic_schema_profiles import SCHEMA_SKIPPED

    expected_skip_reason = _expected_skip_reasons()
    saw_gross_or_cost = 0
    saw_skipped = 0
    for name, feat in features.items():
        if not isinstance(feat, dict):
            raise SystemExit(f"G-NEW FAIL: feature {name!r} not dict")
        keys = _profile_keys_for_feature(feat)
        if name in expected_skip_reason:
            if keys != SCHEMA_SKIPPED:
                raise SystemExit(
                    f"G-NEW FAIL[{profile_label}]: {name} keys "
                    f"{sorted(keys)} != SCHEMA_SKIPPED"
                )
            if feat.get("reason") != expected_skip_reason[name]:
                raise SystemExit(
                    f"G-NEW FAIL[{profile_label}]: {name} reason="
                    f"{feat.get('reason')!r} expected "
                    f"{expected_skip_reason[name]!r}"
                )
            saw_skipped += 1
            continue
        if feat.get("skipped"):
            raise SystemExit(
                f"G-NEW FAIL[{profile_label}]: unexpected skip on {name}: {feat}"
            )
        if keys != expected_non_skip_schema:
            raise SystemExit(
                f"G-NEW FAIL[{profile_label}]: {name} keys {sorted(keys)} "
                f"!= expected {sorted(expected_non_skip_schema)}"
            )
        saw_gross_or_cost += 1
    if saw_skipped != len(expected_skip_reason):
        raise SystemExit(
            f"G-NEW FAIL[{profile_label}]: expected "
            f"{len(expected_skip_reason)} SKIPPED, got {saw_skipped}"
        )
    if saw_gross_or_cost < 1:
        raise SystemExit(
            f"G-NEW FAIL[{profile_label}]: expected ≥1 non-skip profile samples"
        )


def _compare_gross_turnover_to_gold(
    new_features: dict[str, dict],
    old_features: dict[str, dict],
) -> list[str]:
    """① 不變欄 gross_ic/turnover vs G-OLD;排除三注入特徵。"""
    errors: list[str] = []
    for name, old_feat in old_features.items():
        if name in G_COMPARE_EXCLUDE:
            continue
        if old_feat.get("skipped"):
            continue
        new_feat = new_features.get(name)
        if not isinstance(new_feat, dict) or new_feat.get("skipped"):
            errors.append(f"{name}: missing in G-NEW or skipped unexpectedly")
            continue
        for field in ("gross_ic", "turnover"):
            ov = old_feat.get(field)
            nv = new_feat.get(field)
            if ov is None or nv is None:
                errors.append(f"{name}.{field}: missing old={ov!r} new={nv!r}")
                continue
            if not math.isclose(float(ov), float(nv), rel_tol=0.0, abs_tol=0.0):
                # byte-level: require exact float equality after JSON roundtrip
                if float(ov) != float(nv):
                    errors.append(
                        f"{name}.{field}: G-OLD={ov!r} G-NEW={nv!r} (must be equal)"
                    )
    return errors


def _canonical_recompute_check(features: dict[str, dict]) -> list[str]:
    """③ 全量 cost_drag 獨立重算 atol=1e-12;負/非有限須 SKIPPED。"""
    errors: list[str] = []
    for name, feat in features.items():
        if feat.get("skipped"):
            reason = feat.get("reason")
            # 注入負值必須是 negative_turnover;其他 skip 不重算
            if reason == "negative_turnover":
                continue
            if reason in ("non_finite_turnover", "turnover_missing", "gross_ic_missing"):
                continue
            continue
        t = feat.get("turnover")
        bps = feat.get("cost_bps")
        drag = feat.get("cost_drag_return")
        if t is None or bps is None or drag is None:
            errors.append(f"{name}: missing turnover/cost_bps/cost_drag_return for recompute")
            continue
        tf = float(t)
        if (not math.isfinite(tf)) or tf < 0.0:
            errors.append(
                f"{name}: non-finite or negative turnover must be SKIPPED, got t={t!r}"
            )
            continue
        expected = _canonical_cost_drag(float(bps), tf)
        if abs(float(drag) - expected) > 1e-12:
            errors.append(
                f"{name}: cost_drag_return={drag!r} != canonical {expected!r}"
            )
        # sensitivity 每階亦對
        for row in feat.get("cost_sensitivity") or []:
            if not isinstance(row, dict):
                errors.append(f"{name}: cost_sensitivity row not dict")
                continue
            exp_row = _canonical_cost_drag(float(row["cost_bps"]), tf)
            if abs(float(row["cost_drag_return"]) - exp_row) > 1e-12:
                errors.append(
                    f"{name}: sensitivity cost_bps={row['cost_bps']} "
                    f"drag={row['cost_drag_return']!r} != {exp_row!r}"
                )
    return errors


def _key_set_diff(
    old_d: dict[str, Any],
    new_d: dict[str, Any],
) -> tuple[set[str], set[str], set[str]]:
    """回傳 (removed, added, value_changed)。"""
    old_keys = set(old_d.keys()) if isinstance(old_d, dict) else set()
    new_keys = set(new_d.keys()) if isinstance(new_d, dict) else set()
    removed = old_keys - new_keys
    added = new_keys - old_keys
    changed: set[str] = set()
    for k in old_keys & new_keys:
        if old_d.get(k) != new_d.get(k):
            changed.add(k)
    return removed, added, changed


def _validate_feature_diff_against_allowlist(
    name: str,
    old_f: dict[str, Any],
    new_f: dict[str, Any],
    *,
    allowed_removed: frozenset[str],
    allowed_added: frozenset[str],
    allowed_value_change: frozenset[str],
    profile_label: str,
) -> list[str]:
    """對單一 feature 用寫死 allowlist 驗 diff;未核可欄位→error。"""
    from tests.momentum.Analysis.test_net_ic_schema_profiles import SCHEMA_SKIPPED

    errors: list[str] = []
    if not isinstance(new_f, dict):
        return [f"allowlist[{profile_label}]: {name} new not dict"]
    if not isinstance(old_f, dict):
        old_f = {}

    # 新端 SKIPPED:只允許 SCHEMA_SKIPPED 鍵;舊非 skip→skip 時移除不限 allowlist
    if new_f.get("skipped"):
        keys = set(new_f.keys())
        if keys != set(SCHEMA_SKIPPED):
            extra = keys - set(SCHEMA_SKIPPED)
            missing = set(SCHEMA_SKIPPED) - keys
            if extra:
                errors.append(
                    f"allowlist[{profile_label}]: {name} SKIPPED has "
                    f"unapproved keys {sorted(extra)}"
                )
            if missing:
                errors.append(
                    f"allowlist[{profile_label}]: {name} SKIPPED missing "
                    f"{sorted(missing)}"
                )
        return errors

    # 舊 SKIPPED、新非 skip:不在本批預期(注入集固定)
    if old_f.get("skipped") and not new_f.get("skipped"):
        errors.append(
            f"allowlist[{profile_label}]: {name} was SKIPPED in G-OLD, "
            f"unexpected non-skip in G-NEW"
        )
        return errors

    removed, added, changed = _key_set_diff(old_f, new_f)

    for k in sorted(removed):
        if k not in allowed_removed:
            errors.append(
                f"allowlist[{profile_label}]: {name} removed unapproved key {k!r}"
            )
    for k in sorted(added):
        if k not in allowed_added:
            errors.append(
                f"allowlist[{profile_label}]: {name} added unapproved key {k!r}"
            )
    for k in sorted(changed):
        if k in FEATURE_MUST_PRESERVE_KEYS and name not in G_COMPARE_EXCLUDE:
            errors.append(
                f"allowlist[{profile_label}]: {name}.{k} must be preserved "
                f"old={old_f.get(k)!r} new={new_f.get(k)!r}"
            )
        elif k not in allowed_value_change and k not in FEATURE_MUST_PRESERVE_KEYS:
            errors.append(
                f"allowlist[{profile_label}]: {name} value change on "
                f"unapproved key {k!r}"
            )

    for k in FEATURE_MUST_REMOVE_KEYS:
        if k in new_f:
            errors.append(
                f"allowlist[{profile_label}]: {name} must remove {k!r} but still present"
            )
    return errors


def _validate_summary_diff_against_allowlist(
    old_summary: dict[str, Any],
    new_summary: dict[str, Any],
    *,
    allowed_removed: frozenset[str],
    allowed_added: frozenset[str],
    allowed_value_change: frozenset[str],
    profile_label: str,
) -> list[str]:
    """summary 級 allowlist;含固定 new 端 value。"""
    errors: list[str] = []
    if not isinstance(old_summary, dict):
        old_summary = {}
    if not isinstance(new_summary, dict):
        return [f"allowlist[{profile_label}]: summary new not dict"]

    removed, added, changed = _key_set_diff(old_summary, new_summary)
    for k in sorted(removed):
        if k not in allowed_removed:
            errors.append(
                f"allowlist[{profile_label}]: summary removed unapproved key {k!r}"
            )
    for k in sorted(added):
        if k not in allowed_added:
            errors.append(
                f"allowlist[{profile_label}]: summary added unapproved key {k!r}"
            )
    for k in sorted(changed):
        if k not in allowed_value_change:
            errors.append(
                f"allowlist[{profile_label}]: summary value change on "
                f"unapproved key {k!r} "
                f"old={old_summary.get(k)!r} new={new_summary.get(k)!r}"
            )
    for k, expected_new in SUMMARY_REQUIRED_NEW_VALUES.items():
        if k not in new_summary:
            errors.append(
                f"allowlist[{profile_label}]: summary missing required key {k!r}"
            )
            continue
        if new_summary.get(k) != expected_new:
            errors.append(
                f"allowlist[{profile_label}]: summary {k} expected new="
                f"{expected_new!r} got {new_summary.get(k)!r}"
            )
    return errors


def _validate_diff_against_allowlist(
    old_features: dict[str, dict],
    new_features: dict[str, dict],
    old_summary: dict[str, Any],
    new_summary: dict[str, Any],
    *,
    allowed_removed: frozenset[str],
    allowed_added: frozenset[str],
    allowed_value_change: frozenset[str],
    summary_allowed_added: frozenset[str],
    profile_label: str,
) -> list[str]:
    """全量 feature+summary 對照寫死 allowlist;未核可→error。"""
    errors: list[str] = []
    names = sorted(set(old_features) | set(new_features))
    for name in names:
        old_f = old_features.get(name) or {}
        new_f = new_features.get(name) or {}
        errors.extend(
            _validate_feature_diff_against_allowlist(
                name,
                old_f if isinstance(old_f, dict) else {},
                new_f if isinstance(new_f, dict) else {},
                allowed_removed=allowed_removed,
                allowed_added=allowed_added,
                allowed_value_change=allowed_value_change,
                profile_label=profile_label,
            )
        )

    errors.extend(
        _validate_summary_diff_against_allowlist(
            old_summary,
            new_summary,
            allowed_removed=SUMMARY_ALLOWED_REMOVED,
            allowed_added=summary_allowed_added,
            allowed_value_change=SUMMARY_ALLOWED_VALUE_CHANGE,
            profile_label=profile_label,
        )
    )

    def _has_net_ic(obj: Any) -> bool:
        if isinstance(obj, dict):
            if "net_ic" in obj:
                return True
            return any(_has_net_ic(v) for v in obj.values())
        if isinstance(obj, list):
            return any(_has_net_ic(v) for v in obj)
        return False

    if _has_net_ic(new_features) or _has_net_ic(new_summary):
        errors.append(
            f"allowlist[{profile_label}]: net_ic key present in G-NEW output tree"
        )
    return errors


def _build_diff_manifest(
    old_features: dict[str, dict],
    gross_features: dict[str, dict],
    cost_features: dict[str, dict],
    old_summary: dict[str, Any],
    gross_summary: dict[str, Any],
    cost_summary: dict[str, Any],
) -> dict[str, Any]:
    """機器可讀 manifest:逐 feature 舊→新 + 寫死 allowlist 常數快照。"""

    def _per_feature_entries(
        new_features: dict[str, dict],
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name in sorted(set(old_features) | set(new_features)):
            old_f = old_features.get(name, {})
            new_f = new_features.get(name, {})
            if not isinstance(old_f, dict):
                old_f = {}
            if not isinstance(new_f, dict):
                new_f = {}
            removed, added, changed = _key_set_diff(old_f, new_f)
            changed_values: dict[str, Any] = {}
            for k in sorted(changed):
                changed_values[k] = {"old": old_f.get(k), "new": new_f.get(k)}
            out[name] = {
                "removed_keys": sorted(removed),
                "added_keys": sorted(added),
                "changed_values": changed_values,
                "unchanged_keys": sorted(
                    (set(old_f) & set(new_f)) - changed
                ),
            }
        return out

    def _summary_entry(old_s: dict[str, Any], new_s: dict[str, Any]) -> dict[str, Any]:
        removed, added, changed = _key_set_diff(old_s, new_s)
        value_changes = {
            k: {"old": old_s.get(k), "new": new_s.get(k)} for k in sorted(changed)
        }
        return {
            "old_keys": sorted(old_s.keys()),
            "new_keys": sorted(new_s.keys()),
            "removed_keys": sorted(removed),
            "added_keys": sorted(added),
            "value_changes": value_changes,
        }

    return {
        "generated_by": "ic1c_freeze_baseline --baseline new",
        "compare_exclude_features": sorted(G_COMPARE_EXCLUDE),
        "g_new_cost_bps": G_NEW_COST_BPS,
        "profiles": {
            "primary": "SCHEMA_GROSS_ONLY+SCHEMA_SKIPPED (cost_enabled=False default)",
            "secondary": (
                f"SCHEMA_COST_ENABLED+SCHEMA_SKIPPED "
                f"(cost_enabled=True @ {G_NEW_COST_BPS}bps)"
            ),
        },
        "allowlist": {
            "feature_must_remove": sorted(FEATURE_MUST_REMOVE_KEYS),
            "feature_must_preserve": sorted(FEATURE_MUST_PRESERVE_KEYS),
            "feature_gross_allowed_removed": sorted(FEATURE_GROSS_ALLOWED_REMOVED),
            "feature_gross_allowed_added": sorted(FEATURE_GROSS_ALLOWED_ADDED),
            "feature_gross_allowed_value_change": sorted(
                FEATURE_GROSS_ALLOWED_VALUE_CHANGE
            ),
            "feature_cost_allowed_removed": sorted(FEATURE_COST_ALLOWED_REMOVED),
            "feature_cost_allowed_added": sorted(FEATURE_COST_ALLOWED_ADDED),
            "feature_cost_allowed_value_change": sorted(
                FEATURE_COST_ALLOWED_VALUE_CHANGE
            ),
            "summary_allowed_removed": sorted(SUMMARY_ALLOWED_REMOVED),
            "summary_allowed_added_gross": sorted(SUMMARY_ALLOWED_ADDED),
            "summary_allowed_added_cost": sorted(SUMMARY_COST_ALLOWED_ADDED),
            "summary_allowed_value_change": sorted(SUMMARY_ALLOWED_VALUE_CHANGE),
            "summary_required_new_values": dict(SUMMARY_REQUIRED_NEW_VALUES),
        },
        "summary_gross": _summary_entry(old_summary, gross_summary),
        "summary_cost_enabled": _summary_entry(old_summary, cost_summary),
        "per_feature_gross": _per_feature_entries(gross_features),
        "per_feature_cost_enabled": _per_feature_entries(cost_features),
        "rules": {
            "net_ic_forbidden": True,
            "gross_ic_turnover_equal_except_injects": True,
            "allowlist_source": "hardcoded_constants_not_auto_from_diff",
        },
    }


def self_test_allowlist_rejects_bogus() -> None:
    """codex 反例自測:注入 bogus_unapproved_field / bogus_summary 必紅。

    供腳本 --self-test 與 T1 共用;失敗 raise AssertionError。
    """
    old_f: dict[str, Any] = {
        "gross_ic": 0.05,
        "turnover": 0.3,
        "net_ic": 0.04,
        "cost_bps": 5.0,
        "capacity": {"capacity_tier": "unknown", "estimated_capacity_usd": None},
        "cost_sensitivity": [],
        "breakeven_cost_bps": 1.0,
        "profitable_after_cost": True,
    }
    new_f_ok: dict[str, Any] = {
        "gross_ic": 0.05,
        "turnover": 0.3,
        "turnover_semantics": "membership_change_both_legs_per_bar",
        "capacity": {
            "capacity_tier": "unknown",
            "estimated_capacity_usd": None,
            "calibration": "uncalibrated",
        },
        "net_factor_return": {
            "status": "unavailable",
            "value": None,
            "reason": "canonical_factor_return_series_not_built (1c-FR)",
        },
    }
    # 正例:allowlist 內變更應無錯
    ok_errors = _validate_feature_diff_against_allowlist(
        "feat_ok",
        old_f,
        new_f_ok,
        allowed_removed=FEATURE_GROSS_ALLOWED_REMOVED,
        allowed_added=FEATURE_GROSS_ALLOWED_ADDED,
        allowed_value_change=FEATURE_GROSS_ALLOWED_VALUE_CHANGE,
        profile_label="selftest-ok",
    )
    if ok_errors:
        raise AssertionError(f"self-test positive case unexpectedly failed: {ok_errors}")

    # 反例 feature:bogus_unapproved_field
    new_f_bogus = dict(new_f_ok)
    new_f_bogus["bogus_unapproved_field"] = 123
    bog_errors = _validate_feature_diff_against_allowlist(
        "feat_bogus",
        old_f,
        new_f_bogus,
        allowed_removed=FEATURE_GROSS_ALLOWED_REMOVED,
        allowed_added=FEATURE_GROSS_ALLOWED_ADDED,
        allowed_value_change=FEATURE_GROSS_ALLOWED_VALUE_CHANGE,
        profile_label="selftest-bogus",
    )
    if not any("bogus_unapproved_field" in e for e in bog_errors):
        raise AssertionError(
            f"self-test MUST reject bogus_unapproved_field, got: {bog_errors}"
        )

    # 反例 summary:bogus_summary
    old_s = {
        "avg_ic_loss_pct": 0.1,
        "profitable_count": 3,
        "rank_correlation_gross_vs_net": 1.0,
        "total_analyzed": 5,
    }
    new_s_bogus = {
        "total_analyzed": 4,
        "evaluable_count": 0,
        "profitable_count": 0,
        "bogus_summary": True,
    }
    sum_errors = _validate_summary_diff_against_allowlist(
        old_s,
        new_s_bogus,
        allowed_removed=SUMMARY_ALLOWED_REMOVED,
        allowed_added=SUMMARY_ALLOWED_ADDED,
        allowed_value_change=SUMMARY_ALLOWED_VALUE_CHANGE,
        profile_label="selftest-summary",
    )
    if not any("bogus_summary" in e for e in sum_errors):
        raise AssertionError(
            f"self-test MUST reject bogus_summary, got: {sum_errors}"
        )


def freeze_new() -> Path:
    """Phase 1 G-NEW:雙 run 三 profile+獨立 oracle+allowlist diff_manifest。

    主結果 result:config 預設 cost_enabled=False → SCHEMA_GROSS_ONLY + SKIPPED。
    次結果 result_cost_enabled:cost_enabled=True@10bps → SCHEMA_COST_ENABLED + SKIPPED。
    """
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
    from tests.momentum.Analysis.test_net_ic_schema_profiles import (
        SCHEMA_COST_ENABLED,
        SCHEMA_GROSS_ONLY,
    )

    # allowlist 自測先跑(codex 反例);失敗不得凍基線
    self_test_allowlist_rejects_bogus()

    old_path = OUT_DIR / "g_old.json"
    if not old_path.is_file():
        raise FileNotFoundError(
            f"G-OLD missing at {old_path}; run --baseline old first"
        )
    old_payload = json.loads(old_path.read_text(encoding="utf-8"))
    old_result = old_payload.get("result") or {}
    old_features = old_result.get("features") or {}
    old_summary = old_result.get("summary") or {}

    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"fixture missing: {FIXTURE_PATH}")

    features, labels, feature_names = _load_fixture_frames()
    summary, turnover_data = _build_summary_and_turnover(
        features, labels, feature_names
    )
    _inject_skipped_g_new(summary, turnover_data)

    # --- run A:預設 cost_enabled=False → GROSS_ONLY + SKIPPED ---
    cfg_gross = {
        "enabled": True,
        "cost_enabled": False,
        "participation_rate": 0.01,
    }
    raw_gross = NetICAnalyzer(cfg_gross).batch_analyze(summary, turnover_data)

    # --- run B:直開 cost_enabled+10bps → COST_ENABLED + SKIPPED ---
    cfg_cost = {
        "enabled": True,
        "cost_enabled": True,
        "cost_bps": G_NEW_COST_BPS,
        "participation_rate": 0.01,
    }
    raw_cost = NetICAnalyzer(cfg_cost).batch_analyze(summary, turnover_data)

    non_finite_fields: list[str] = []
    sanitized_gross = _sanitize_for_strict_json(
        raw_gross, path="result", non_finite_fields=non_finite_fields
    )
    sanitized_cost = _sanitize_for_strict_json(
        raw_cost, path="result_cost_enabled", non_finite_fields=non_finite_fields
    )
    cleaned_paths: list[str] = []
    for p in non_finite_fields:
        if p.startswith("result_cost_enabled."):
            cleaned_paths.append(p[len("result_cost_enabled.") :])
        elif p.startswith("result."):
            cleaned_paths.append(p[len("result.") :])
        else:
            cleaned_paths.append(p)
    cleaned_paths = sorted(set(cleaned_paths))

    gross_features = (sanitized_gross or {}).get("features") or {}
    gross_summary = (sanitized_gross or {}).get("summary") or {}
    cost_features = (sanitized_cost or {}).get("features") or {}
    cost_summary = (sanitized_cost or {}).get("summary") or {}

    # ② profile 鍵集合:主 GROSS_ONLY、次 COST_ENABLED、兩者皆含 SKIPPED
    _assert_g_new_profiles(
        gross_features,
        expected_non_skip_schema=SCHEMA_GROSS_ONLY,
        profile_label="GROSS_ONLY",
    )
    _assert_g_new_profiles(
        cost_features,
        expected_non_skip_schema=SCHEMA_COST_ENABLED,
        profile_label="COST_ENABLED",
    )

    # ① gross_ic/turnover vs G-OLD(兩 run 皆驗,排除三注入)
    for label, feats in (("GROSS_ONLY", gross_features), ("COST_ENABLED", cost_features)):
        eq_errors = _compare_gross_turnover_to_gold(feats, old_features)
        if eq_errors:
            for e in eq_errors:
                print(f"G-NEW FAIL[{label}]: {e}", file=sys.stderr)
            raise SystemExit(1)

    # ③ canonical recompute(僅 COST_ENABLED 有 cost_drag)
    re_errors = _canonical_recompute_check(cost_features)
    if re_errors:
        for e in re_errors:
            print(f"G-NEW FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)

    # ⑤ allowlist 驗 diff(非自生成假綠)
    man_errors = _validate_diff_against_allowlist(
        old_features,
        gross_features,
        old_summary,
        gross_summary,
        allowed_removed=FEATURE_GROSS_ALLOWED_REMOVED,
        allowed_added=FEATURE_GROSS_ALLOWED_ADDED,
        allowed_value_change=FEATURE_GROSS_ALLOWED_VALUE_CHANGE,
        summary_allowed_added=SUMMARY_ALLOWED_ADDED,
        profile_label="GROSS_ONLY",
    )
    man_errors.extend(
        _validate_diff_against_allowlist(
            old_features,
            cost_features,
            old_summary,
            cost_summary,
            allowed_removed=FEATURE_COST_ALLOWED_REMOVED,
            allowed_added=FEATURE_COST_ALLOWED_ADDED,
            allowed_value_change=FEATURE_COST_ALLOWED_VALUE_CHANGE,
            summary_allowed_added=SUMMARY_COST_ALLOWED_ADDED,
            profile_label="COST_ENABLED",
        )
    )
    if man_errors:
        for e in man_errors:
            print(f"G-NEW FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)

    manifest = _build_diff_manifest(
        old_features,
        gross_features,
        cost_features,
        old_summary,
        gross_summary,
        cost_summary,
    )

    payload: dict[str, Any] = {
        "fixture_sha256": _sha256_file(FIXTURE_PATH),
        "git_head": _git_head(),
        "generated_by": "ic1c_freeze_baseline --baseline new",
        "non_finite_fields": cleaned_paths,
        "feature_names_input": sorted(feature_names),
        "injected_skips": {
            "turnover_missing": INJECT_TURNOVER_MISSING,
            "gross_ic_missing": INJECT_GROSS_IC_MISSING,
            "negative_turnover": INJECT_NEGATIVE_TURNOVER,
        },
        "cost_config": {"cost_enabled": False},
        "cost_config_enabled_run": {
            "cost_enabled": True,
            "cost_bps": G_NEW_COST_BPS,
        },
        "result": sanitized_gross,
        "result_cost_enabled": sanitized_cost,
    }

    # ④ JSON strict
    text = json.dumps(payload, sort_keys=True, allow_nan=False, ensure_ascii=False)
    if not text.endswith("\n"):
        text = text + "\n"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "g_new.json"
    out_sha = OUT_DIR / "g_new.sha256"
    out_manifest = OUT_DIR / "diff_manifest.json"

    out_json.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(out_json.read_bytes()).hexdigest()
    rel = out_json.relative_to(REPO_ROOT).as_posix()
    out_sha.write_text(f"{digest}  {rel}\n", encoding="utf-8")

    man_text = json.dumps(
        manifest, sort_keys=True, allow_nan=False, ensure_ascii=False, default=str
    )
    if not man_text.endswith("\n"):
        man_text = man_text + "\n"
    out_manifest.write_text(man_text, encoding="utf-8")

    n_gross = sum(
        1 for v in gross_features.values() if isinstance(v, dict) and not v.get("skipped")
    )
    n_cost = sum(
        1 for v in cost_features.values() if isinstance(v, dict) and not v.get("skipped")
    )
    n_skip = sum(
        1 for v in gross_features.values() if isinstance(v, dict) and v.get("skipped")
    )
    print(f"wrote {rel}")
    print(f"sha256={digest}")
    print(
        f"profiles=GROSS_ONLY:{n_gross}+COST_ENABLED:{n_cost}+SKIPPED:{n_skip} "
        f"features={len(gross_features)}"
    )
    print(f"diff_manifest={out_manifest.relative_to(REPO_ROOT).as_posix()}")
    print(f"non_finite_fields={len(cleaned_paths)}")
    return out_json


def freeze_new2() -> None:
    raise NotImplementedError(
        "G-NEW2 freeze is Phase 2 (B2); implement after API wiring"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IC1C baseline freeze")
    parser.add_argument(
        "--baseline",
        choices=("old", "new", "new2"),
        help="which baseline to freeze",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run allowlist bogus-field negative self-test only",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        self_test_allowlist_rejects_bogus()
        print("self-test PASS: bogus_unapproved_field/bogus_summary rejected")
        return 0
    if not args.baseline:
        parser.error("--baseline is required unless --self-test")
    if args.baseline == "old":
        freeze_old()
        return 0
    if args.baseline == "new":
        freeze_new()
        return 0
    if args.baseline == "new2":
        freeze_new2()
        return 1
    parser.error(f"unknown baseline: {args.baseline}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NotImplementedError as exc:
        print(f"NotImplementedError: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
