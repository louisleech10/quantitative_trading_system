#!/usr/bin/env python3
"""IC1C-FR-STOPGAP §G baseline 凍結腳本(Task 0.1 / B0).

用法:
  python scripts/ic1cfr_stopgap_freeze.py --before
  python scripts/ic1cfr_stopgap_freeze.py --check-nodeids
  python scripts/ic1cfr_stopgap_freeze.py --after-default   # Phase 1 佔位
  python scripts/ic1cfr_stopgap_freeze.py --after-explicit  # Phase 1 佔位

--before:
  1) 真-kline fixture 跑 run_deep_analysis(全模組 enabled)→
     handoffs/ic1cfr_stopgap_baseline/before.json (sort_keys, 原值含漂移欄)
  2) canonical hash(剔除精確 JSON-path 漂移欄後 sha256)→ before.sha256
  3) 凍 factory allowlist + pytest baseline nodeids
  4) lineage: fixture_sha256 / git_head

零 runtime 變更:僅新增本腳本與 handoffs/ 產物。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "handoffs" / "ic1cfr_stopgap_baseline"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ic_api_real_kline.py"
KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
BEFORE_JSON = OUT_DIR / "before.json"
BEFORE_SHA = OUT_DIR / "before.sha256"
FACTORY_ALLOWLIST = OUT_DIR / "factory_allowlist.txt"
PYTEST_NODEIDS = OUT_DIR / "pytest_baseline_nodeids.txt"

# 與 B0 / Gate B2 相同 suite 與收集規則(T-S10)
PYTEST_SUITE_ARGS: tuple[str, ...] = (
    "tests/momentum/",
    "tests/api/",
    "tests/phase26/",
    "-q",
)

ALL_DEEP_MODULES: tuple[str, ...] = (
    "factor_returns",
    "factor_centrality",
    "trend_analysis",
    "parameter_sensitivity",
    "rolling_oos",
    "factor_orthogonalization",
    "factor_exposure",
    "long_short_analysis",
    "feature_quality_diagnostics",
    "net_ic_analysis",
)

# ---------------------------------------------------------------------------
# Canonical hash 精確 JSON-path 排除清單(T-S1 / SPEC §G / 使用者:勿廣義刪 key)
# 路徑語意:點分隔;「*」僅匹配 list index(一層)。artifact dump 仍保原值。
# 不得列入 results.factor_returns 本體值欄。
# ---------------------------------------------------------------------------
CANONICAL_EXCLUDE_JSON_PATHS: frozenset[str] = frozenset(
    {
        # DeepAnalysisReport 壁鐘 / 執行時長
        "report.total_execution_time_s",
        # envelope 生成時間(若存在)
        "generated_at",
        "lineage.generated_at",
        # SkippedResult 錯誤時間戳(list 索引以 * 匹配)
        "report.deep_analysis_errors.*.timestamp",
        # §G 比對排除頂層計數(factor_returns 狀態改變後必漂;before 重跑亦保留一致規則)
        "report.completed_count",
        "report.skipped_count",
        "report.failed_count",
        "report.deep_analysis_summary.completed",
        "report.deep_analysis_summary.skipped",
        "report.deep_analysis_summary.failed",
    }
)

# factory / direct consumer 掃描正規化規則(B0 artifact 與 Task 1.3 測試共用語意)
# 字串拆開避免本腳本被 rg 自命中(scanner self-noise)
FACTORY_CREATE_SYMBOL = "create_factor_return" + "_analyzer"
DIRECT_CTOR_PATTERN = r"FactorReturn" + r"Analyzer\("
# factory 定義檔本身不算 caller
FACTORY_DEFINITION_FILE = "momentum/factories.py"
# 本 freeze 腳本不入 allowlist(掃描器/註解非 production consumer)
SCANNER_SELF_REL = "scripts/ic1cfr_stopgap_freeze.py"


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
    """遞迴轉 JSON 可序列化;非有限 number → null(禁止 NaN 字面落檔)."""
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
    return obj


def _path_matches_exclude(path: str, patterns: frozenset[str]) -> bool:
    """精確 JSON-path 匹配:點分隔;pattern 中 * 僅匹配單一 list index 段."""
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
    """回傳剔除精確 JSON-path 漂移欄後的 deep copy(不改原 artifact)."""
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
    """T-S1:hash 前 canonicalize(剔漂移 path),sort_keys dump 後 sha256."""
    stripped = strip_canonical_excludes(payload)
    text = json.dumps(stripped, sort_keys=True, allow_nan=False, ensure_ascii=False)
    if not text.endswith("\n"):
        text = text + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    """寫 sort_keys JSON,回傳檔案 sha256(raw bytes,非 canonical)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, allow_nan=False, ensure_ascii=False)
    if not text.endswith("\n"):
        text = text + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_fixture_frames() -> tuple[pd.DataFrame, pd.Series, list[str]]:
    from momentum.factories import create_kline_storage_manager
    from tests.fixtures.ic_api_real_kline import (
        FEATURE_NAMES,
        SYMBOL,
        TIMEFRAME,
        build_real_kline_frames,
    )

    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"fixture missing: {FIXTURE_PATH}")
    if not KLINE_CACHE.is_file():
        raise FileNotFoundError(f"requires_kline: missing {KLINE_CACHE}")

    storage = create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent))
    kline = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    if kline is None or getattr(kline, "empty", True):
        raise RuntimeError(f"requires_kline: no data for {SYMBOL}/{TIMEFRAME}")

    features, labels = build_real_kline_frames(kline)
    return features, labels, list(FEATURE_NAMES)


def _safe_ic_mean(feature: pd.Series, labels: pd.Series) -> float | None:
    aligned = pd.concat([feature.rename("f"), labels.rename("y")], axis=1).dropna()
    if len(aligned) < 2:
        return None
    corr = aligned["f"].corr(aligned["y"])
    if corr is None or not np.isfinite(float(corr)):
        return None
    return float(corr)


def _build_orchestrator_with_real_kline() -> Any:
    """以真-kline fixture 餵 IC cache,全模組 enabled(advanced + force_modules)."""
    from momentum.Analysis.ic_config_schema import ICConfig
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    features, labels, feature_names = _load_fixture_frames()

    # advanced: deep_analysis=True, disabled_modules=[]
    raw = ICConfig().model_dump(by_alias=True)
    raw["feature_tiers"]["active_preset"] = "advanced"
    # 明示各 deep 模組 enabled=True(全模組 enabled 契約)
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
    config = ICConfig.model_validate(raw)

    orch = ICFilterOrchestrator(config)
    # rolling_ic: 自 feature 衍生確定性序列(與 phase26 seed 形狀同構)
    rolling_ic = {
        name: {
            "30": (0.02 * features[name].rolling(20, min_periods=1).mean().fillna(0.0)).tolist()
        }
        for name in feature_names
    }
    # production icir 形狀為 {feat: {icir, ic_mean, ...}};orthogonalizer 可能 skip(現況,零 runtime 改)
    icir = {
        name: {
            "ic_mean": _safe_ic_mean(features[name], labels),
            "ic_std": 1.0,
            "icir": 0.1,
            "ic_hit_rate": 0.5,
        }
        for name in feature_names
    }
    orch._ic_cache = {
        "features_df": features,
        "label_series": labels,
        "metadata": {},
        "icir": icir,
        "rolling_ic": rolling_ic,
        "ic_decay": {},
        "grouped_ic": {},
        "event_info": {},
        "stage0_log": {},
        "preproc_log": {},
    }
    orch._monotonicity_cache = {name: {} for name in feature_names}
    orch._filtered_features_df = features[feature_names].copy()
    orch._report = {
        "summary_table": [
            {
                "feature_name": name,
                "ic_mean": _safe_ic_mean(features[name], labels),
                "icir": 0.1,
            }
            for name in feature_names
        ],
        "turnover_analysis": {
            name: {"quantile_turnover": 0.2} for name in feature_names
        },
    }
    return orch


def _has_finite_numeric_leaf(obj: Any) -> bool:
    if isinstance(obj, dict):
        return any(_has_finite_numeric_leaf(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_finite_numeric_leaf(v) for v in obj)
    if isinstance(obj, bool):
        return False
    if isinstance(obj, (int, float, np.integer, np.floating)):
        return math.isfinite(float(obj))
    return False


def freeze_before() -> int:
    """Task 0.1 --before: dump before.json + canonical hash + allowlist + nodeids."""
    from datetime import datetime, timezone

    orch = _build_orchestrator_with_real_kline()
    report = orch.run_deep_analysis(force_modules=list(ALL_DEEP_MODULES))

    report_dict = _sanitize_for_strict_json(asdict(report))
    if not isinstance(report_dict, dict):
        raise SystemExit("FAIL: report serialize not dict")

    module_summary = report_dict.get("module_summary") or {}
    fr_status = module_summary.get("factor_returns")
    fr_body = (report_dict.get("results") or {}).get("factor_returns")
    if fr_status != "completed":
        raise SystemExit(
            f"FAIL: module_summary.factor_returns={fr_status!r} expected 'completed'"
        )
    if not isinstance(fr_body, dict) or not fr_body:
        raise SystemExit("FAIL: results.factor_returns missing or empty")
    if not _has_finite_numeric_leaf(fr_body):
        raise SystemExit("FAIL: results.factor_returns has no finite numeric leaf")

    generated_at = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "generated_by": "ic1cfr_stopgap_freeze --before",
        "lineage": {
            "fixture_sha256": _sha256_file(FIXTURE_PATH),
            "fixture_path": FIXTURE_PATH.relative_to(REPO_ROOT).as_posix(),
            "git_head": _git_head(),
            "kline_cache": KLINE_CACHE.relative_to(REPO_ROOT).as_posix(),
            "generated_at": generated_at,
        },
        "canonical_exclude_json_paths": sorted(CANONICAL_EXCLUDE_JSON_PATHS),
        "report": report_dict,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_digest = _write_json(BEFORE_JSON, payload)
    canon = canonical_sha256(payload)
    # shasum -c 友好:記錄 canonical hash(T-S1 重跑一致者)
    rel = BEFORE_JSON.relative_to(REPO_ROOT).as_posix()
    BEFORE_SHA.write_text(f"{canon}  {rel}\n", encoding="utf-8")

    # 重算自磁碟確認 dump 保原值後 canonicalize 可重現
    disk_payload = json.loads(BEFORE_JSON.read_text(encoding="utf-8"))
    disk_canon = canonical_sha256(disk_payload)
    if disk_canon != canon:
        raise SystemExit(
            f"FAIL: canonical recompute mismatch in-memory={canon} disk={disk_canon}"
        )

    allowlist_text = freeze_factory_allowlist()
    FACTORY_ALLOWLIST.write_text(allowlist_text, encoding="utf-8")

    nodeids = collect_pytest_failed_nodeids()
    PYTEST_NODEIDS.write_text(
        "\n".join(nodeids) + ("\n" if nodeids else ""),
        encoding="utf-8",
    )

    print(f"wrote {rel}")
    print(f"raw_sha256={raw_digest}")
    print(f"canonical_sha256={canon}")
    print(f"module_summary.factor_returns={fr_status}")
    print(f"factor_returns_finite_leaves=yes")
    print(f"factory_allowlist={FACTORY_ALLOWLIST.relative_to(REPO_ROOT).as_posix()}")
    print(f"pytest_baseline_nodeids={len(nodeids)}")
    print(f"fixture_sha256={payload['lineage']['fixture_sha256']}")
    print(f"git_head={payload['lineage']['git_head']}")
    return 0


def _rel_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _rg_lines(pattern: str, *paths: str) -> list[str]:
    """跑 rg -n;無命中時 exit 1 → 回空 list."""
    cmd = ["rg", "-n", pattern, *paths]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit("FAIL: rg not found on PATH") from exc
    if proc.returncode not in (0, 1):
        raise SystemExit(f"FAIL: rg exit={proc.returncode}: {proc.stderr}")
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return lines


def normalize_factory_scan_hits(
    create_hits: Iterable[str],
    direct_hits: Iterable[str],
) -> dict[str, list[str]]:
    """正規化 factory caller / direct consumer 掃描結果(B0 與 Task 1.3 共用規則).

    - factory callers: 命中 `create_factor_return_analyzer` 且**非** factories.py 定義檔
    - direct consumers: 命中 `FactorReturnAnalyzer(` 的 file:line(含 factories 定義體)
    - 路徑相對 repo root;去重後排序
    """
    factory_callers: set[str] = set()
    for line in create_hits:
        # format: path:lineno:content
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        rel = parts[0].replace("\\", "/")
        if rel.startswith("./"):
            rel = rel[2:]
        if rel == SCANNER_SELF_REL or rel.endswith("/" + SCANNER_SELF_REL):
            continue
        if rel == FACTORY_DEFINITION_FILE or rel.endswith("/" + FACTORY_DEFINITION_FILE):
            # 定義不算 caller
            continue
        factory_callers.add(rel)

    direct_consumers: set[str] = set()
    for line in direct_hits:
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        rel = parts[0].replace("\\", "/")
        if rel.startswith("./"):
            rel = rel[2:]
        if rel == SCANNER_SELF_REL or rel.endswith("/" + SCANNER_SELF_REL):
            continue
        lineno = parts[1]
        if not lineno.isdigit():
            continue
        direct_consumers.add(f"{rel}:{lineno}")

    return {
        "factory_callers": sorted(factory_callers),
        "direct_consumers": sorted(direct_consumers),
    }


def freeze_factory_allowlist() -> str:
    """rg 掃描並寫成可機讀 allowlist 文字."""
    create_hits = _rg_lines(
        FACTORY_CREATE_SYMBOL,
        "momentum",
        "api",
        "scripts",
        "tests",
    )
    direct_hits = _rg_lines(
        DIRECT_CTOR_PATTERN,
        "momentum",
        "api",
        "scripts",
        "tests",
    )
    norm = normalize_factory_scan_hits(create_hits, direct_hits)

    # 欄位分隔用 ASCII RS 風格明確標記,避免空白被顯示吞掉:
    # 每行: <kind>|<path-or-path:line>
    lines = [
        "# IC1CFR-STOPGAP B0 factory allowlist (frozen)",
        f"# scanner: rg -n {FACTORY_CREATE_SYMBOL!r} + rg -n {DIRECT_CTOR_PATTERN!r}",
        "# rules: factory definition (momentum/factories.py) excluded from factory_callers;",
        "#        direct_consumers keep file:line including factories.py definition body;",
        f"#        scanner self ({SCANNER_SELF_REL}) excluded.",
        "# format: factory_caller|<relpath> OR direct_consumer|<relpath>:<lineno>",
        "# section: factory_callers",
    ]
    for item in norm["factory_callers"]:
        lines.append(f"factory_caller|{item}")
    lines.append("# section: direct_consumers")
    for item in norm["direct_consumers"]:
        lines.append(f"direct_consumer|{item}")
    lines.append("")
    return "\n".join(lines)


def _parse_pytest_failed_nodeids(stdout: str, stderr: str = "") -> list[str]:
    """解析 pytest -q 輸出中的 failed + collection-error nodeid.

    支援:
      - short summary: `FAILED path::test` / `ERROR path::test`
      - collection errors: `ERROR tests/foo.py` 或 `ERROR collecting ...`
        （僅真 file-level 行，不含 `::`；避免 path.py::test 被 (\S+\\.py) 截前綴）
      - progress 行: `path::test FAILED`
    """
    text = stdout + "\n" + stderr
    nodeids: set[str] = set()

    # short test summary / progress: FAILED|ERROR <nodeid>
    for m in re.finditer(
        r"^(?:FAILED|ERROR)\s+(\S+::\S+)",
        text,
        flags=re.MULTILINE,
    ):
        nodeids.add(m.group(1).strip())

    # progress-style: <nodeid> FAILED|ERROR
    for m in re.finditer(
        r"^(\S+::\S+)\s+(?:FAILED|ERROR)\b",
        text,
        flags=re.MULTILINE,
    ):
        nodeids.add(m.group(1).strip())

    # collection errors without :: (file-level only; 行內不得含雙冒號)
    for line in text.splitlines():
        if "::" in line:
            continue
        m = re.match(r"^ERROR\s+(?:collecting\s+)?(\S+\.py)\b", line)
        if m:
            nodeids.add(m.group(1).strip())

    # pytest -q 末端 ERRORS 區塊
    for m in re.finditer(
        r"^=+\s*ERRORS\s*=+$([\s\S]*?)(?:^=+|\Z)",
        text,
        flags=re.MULTILINE,
    ):
        block = m.group(1)
        for m2 in re.finditer(r"^_\s+ERROR\s+collecting\s+(\S+)", block, flags=re.MULTILINE):
            path = m2.group(1).strip()
            # collecting 目標應為檔案路徑；若含 :: 則不當 file-level
            if "::" not in path:
                nodeids.add(path)
        for m2 in re.finditer(r"^ERROR\s+(\S+::\S+)", block, flags=re.MULTILINE):
            nodeids.add(m2.group(1).strip())

    return sorted(nodeids)


def collect_pytest_failed_nodeids() -> list[str]:
    """自跑與 B0/B2 相同 suite,回傳 failed+collection-error nodeid 排序集.

    fail-closed: pytest returncode != 0 且無法解析出任何 failure/collection
    receipt 時 SystemExit(1)（禁止回空集合讓 check_nodeids 假綠）。
    returncode==0 且空集 = 全綠，合法。
    """
    cmd = [str(REPO_ROOT / "venv" / "bin" / "pytest"), *PYTEST_SUITE_ARGS]
    if not Path(cmd[0]).is_file():
        cmd = [sys.executable, "-m", "pytest", *PYTEST_SUITE_ARGS]
    print(f"running: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    # 合併 stdout/stderr;pytest 可能把 summary 打到任一端
    nodeids = _parse_pytest_failed_nodeids(proc.stdout, proc.stderr)
    # fail-closed: rc 非 0 且無完整 failure/collection receipt → 禁止空集當通過
    if proc.returncode != 0 and not nodeids:
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        stderr_summary = (proc.stderr or proc.stdout or "")[-2000:]
        print(
            "FAIL: pytest returncode non-zero but no failure/collection nodeids "
            "parsed (INTERNALERROR / interrupt / exit 5 no-tests / unparseable). "
            f"returncode={proc.returncode}\n"
            f"stderr_summary:\n{stderr_summary}\n"
            f"combined_tail:\n{combined[-2000:]}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return nodeids


def check_nodeids() -> int:
    """Gate B2 機械差集:新增 failed/error nodeid 非空 → exit 1."""
    if not PYTEST_NODEIDS.is_file():
        print(
            f"FAIL: baseline missing {PYTEST_NODEIDS}; run --before first",
            file=sys.stderr,
        )
        return 1
    baseline = {
        ln.strip()
        for ln in PYTEST_NODEIDS.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }
    current = set(collect_pytest_failed_nodeids())
    new_failures = sorted(current - baseline)
    resolved = sorted(baseline - current)
    print(f"baseline_nodeids={len(baseline)}")
    print(f"current_nodeids={len(current)}")
    print(f"new_failures={len(new_failures)}")
    print(f"resolved_since_baseline={len(resolved)}")
    if new_failures:
        print("NEW_FAILURES:")
        for n in new_failures:
            print(f"  {n}")
        return 1
    print("check-nodeids: PASS (no new failures vs baseline)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IC1CFR stopgap §G freeze")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--before", action="store_true", help="Freeze pre-stopgap baseline")
    mode.add_argument(
        "--after-default",
        action="store_true",
        help="Post-stopgap default-off golden (Phase 1)",
    )
    mode.add_argument(
        "--after-explicit",
        action="store_true",
        help="Post-stopgap force_modules golden (Phase 1)",
    )
    mode.add_argument(
        "--check-nodeids",
        action="store_true",
        help="Diff current suite failures vs B0 pytest_baseline_nodeids.txt",
    )
    args = parser.parse_args(argv)

    if args.after_default:
        raise NotImplementedError(
            "--after-default is Phase 1 (B1); implement after default-off + sanitizer"
        )
    if args.after_explicit:
        raise NotImplementedError(
            "--after-explicit is Phase 1 (B1); implement after ModuleUnavailableError path"
        )
    if args.check_nodeids:
        return check_nodeids()
    if args.before:
        return freeze_before()
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NotImplementedError as exc:
        print(f"NotImplementedError: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
