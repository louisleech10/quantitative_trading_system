#!/usr/bin/env python3
"""IC1C-FR-STOPGAP / 1c-FR-FULL §G baseline 凍結腳本(Task 0.1 / B0 + FULL B0.1).

用法:
  python scripts/ic1cfr_stopgap_freeze.py --before
  python scripts/ic1cfr_stopgap_freeze.py --check-nodeids
  python scripts/ic1cfr_stopgap_freeze.py --after-default   # Phase 1 佔位
  python scripts/ic1cfr_stopgap_freeze.py --after-explicit  # Phase 1 佔位
  # 1c-FR-FULL B0.1 profiles:
  python scripts/ic1cfr_stopgap_freeze.py --profile before-full \\
      --fixture ic_api_real_kline --out handoffs/ic1cfr_full_baseline/before.json
  python scripts/ic1cfr_stopgap_freeze.py --profile after-full \\
      --fixture ic_api_real_kline --out handoffs/ic1cfr_full_baseline/after_full.json

--before:
  1) 真-kline fixture 跑 run_deep_analysis(全模組 enabled)→
     handoffs/ic1cfr_stopgap_baseline/before.json (sort_keys, 原值含漂移欄)
  2) canonical hash(剔除精確 JSON-path 漂移欄後 sha256)→ before.sha256
  3) 凍 factory allowlist + pytest baseline nodeids
  4) lineage: fixture_sha256 / git_head

--profile before-full / after-full (1c-FR-FULL B0.1):
  真-kline 跑 deep analysis → --out JSON + 印 sha256;
  before-full 期望 FR unavailable(stopgap 現態)+非 FR 模組 path 值;
  after-full 同結構骨架(F0 後重凍 ok union;本批僅旗標/骨架);
  before-full 另凍 decoupling_baseline.txt(R2/R3/R4 計數).

零 runtime 變更:僅新增本腳本與 handoffs/ 產物。
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "handoffs" / "ic1cfr_stopgap_baseline"
FULL_BASELINE_DIR = REPO_ROOT / "handoffs" / "ic1cfr_full_baseline"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ic_api_real_kline.py"
KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
BEFORE_JSON = OUT_DIR / "before.json"
BEFORE_SHA = OUT_DIR / "before.sha256"
FACTORY_ALLOWLIST = OUT_DIR / "factory_allowlist.txt"
PYTEST_NODEIDS = OUT_DIR / "pytest_baseline_nodeids.txt"
FULL_BEFORE_JSON = FULL_BASELINE_DIR / "before.json"
FULL_AFTER_JSON = FULL_BASELINE_DIR / "after_full.json"
DECOUPLING_BASELINE = FULL_BASELINE_DIR / "decoupling_baseline.txt"
ALLOWED_FIXTURES: frozenset[str] = frozenset({"ic_api_real_kline"})
FULL_PROFILES: frozenset[str] = frozenset({"before-full", "after-full"})

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
# B1 退修:AST 掃描(import alias + Call 計數,同行多 ctor 不去重)
FACTORY_CREATE_SYMBOL = "create_factor_return" + "_analyzer"
DIRECT_CLASS_NAME = "FactorReturn" + "Analyzer"
# factory 定義檔本身不算 caller
FACTORY_DEFINITION_FILE = "momentum/factories.py"
# 本 freeze 腳本不入 allowlist(掃描器/註解非 production consumer)
SCANNER_SELF_REL = "scripts/ic1cfr_stopgap_freeze.py"
# AST 掃描根目錄
SCAN_ROOTS: tuple[str, ...] = ("momentum", "api", "scripts", "tests")
# §G 非 FR 比對時額外剔除的 path 前綴(factor_returns 本體屬 scope-expected)
FR_SCOPE_PATH_PREFIXES: tuple[str, ...] = (
    "report.results.factor_returns",
    "report.module_summary.factor_returns",
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


def _rel_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _ast_collect_calls_in_file(
    path: Path,
    *,
    target_names: frozenset[str],
) -> list[tuple[int, int]]:
    """AST 掃描單一 .py:回傳 (lineno, col_offset) 的 Call 命中(含 alias).

    - 追蹤 ``from X import Target as Alias`` / ``import X; X.Target``
    - 只計 Call node(``Alias(...)`` / ``Target(...)``);同行多 ctor 各計一次
    - 不計 ``Target.method(...)``(Attribute 呼叫,非建構)
    """
    try:
        src = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []

    # local name → whether it resolves to a target symbol
    aliases: dict[str, str] = {}
    hits: list[tuple[int, int]] = []

    class Visitor(ast.NodeVisitor):
        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
            for alias in node.names:
                raw = alias.name
                asname = alias.asname or raw
                if raw in target_names:
                    aliases[asname] = raw
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
            # ``import momentum.Analysis.factor_return_analyzer as fra`` 不直接給 class 名
            # 僅當 module 末端名恰好是 target 時(罕見)才記;一般 ctor 走 From-import
            for alias in node.names:
                raw = alias.name.split(".")[-1]
                asname = alias.asname or raw
                if raw in target_names:
                    aliases[asname] = raw
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
                if name in target_names or name in aliases:
                    hits.append((node.lineno, node.col_offset))
            elif isinstance(func, ast.Attribute):
                # module.FactorReturnAnalyzer(...) form
                if func.attr in target_names:
                    hits.append((node.lineno, node.col_offset))
            self.generic_visit(node)

    # also treat bare target name as callable without import(tests that do from-import
    # are covered; definition sites import locally inside function — ImportFrom visitor
    # still sees them when walking the whole module tree)
    Visitor().visit(tree)
    return hits


def scan_factor_return_consumers_ast(
    roots: Iterable[str] = SCAN_ROOTS,
) -> dict[str, list[str]]:
    """AST 掃描 factory callers + direct FactorReturnAnalyzer ctor 消費者.

    - factory_callers: 檔相對路徑(factories.py 定義檔排除;scanner self 排除)
    - direct_consumers: ``path:line:col``(同行多 ctor 不去重;含 factories 定義體)
    """
    factory_targets = frozenset({FACTORY_CREATE_SYMBOL})
    direct_targets = frozenset({DIRECT_CLASS_NAME})

    factory_callers: set[str] = set()
    direct_consumers: list[str] = []

    for root_name in roots:
        root = REPO_ROOT / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            rel = _rel_posix(path)
            if rel == SCANNER_SELF_REL or rel.endswith("/" + SCANNER_SELF_REL):
                continue
            # factory calls
            for lineno, _col in _ast_collect_calls_in_file(path, target_names=factory_targets):
                if rel == FACTORY_DEFINITION_FILE or rel.endswith(
                    "/" + FACTORY_DEFINITION_FILE
                ):
                    continue
                factory_callers.add(rel)
            # direct ctors — 每 Call 一筆 path:line:col(不去重)
            for lineno, col in _ast_collect_calls_in_file(path, target_names=direct_targets):
                direct_consumers.append(f"{rel}:{lineno}:{col}")

    direct_consumers_sorted = sorted(
        direct_consumers,
        key=lambda s: (
            s.rsplit(":", 2)[0],
            int(s.rsplit(":", 2)[1]),
            int(s.rsplit(":", 2)[2]),
        ),
    )
    return {
        "factory_callers": sorted(factory_callers),
        "direct_consumers": direct_consumers_sorted,
    }


def normalize_factory_scan_hits(
    create_hits: Iterable[str] | None = None,
    direct_hits: Iterable[str] | None = None,
) -> dict[str, list[str]]:
    """正規化 factory caller / direct consumer(B0 與 Task 1.3 共用).

    B1 起優先走 AST(``scan_factor_return_consumers_ast``)。
    仍接受舊 rg 行格式作向後相容,但測試應改呼叫 AST 入口。
    """
    if create_hits is None and direct_hits is None:
        return scan_factor_return_consumers_ast()

    # legacy rg path(保留給任何仍傳 rg 行的呼叫端)
    factory_callers: set[str] = set()
    for line in create_hits or []:
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        rel = parts[0].replace("\\", "/")
        if rel.startswith("./"):
            rel = rel[2:]
        if rel == SCANNER_SELF_REL or rel.endswith("/" + SCANNER_SELF_REL):
            continue
        if rel == FACTORY_DEFINITION_FILE or rel.endswith("/" + FACTORY_DEFINITION_FILE):
            continue
        factory_callers.add(rel)

    direct_consumers: list[str] = []
    for line in direct_hits or []:
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
        # legacy 無 col → 用 0;多 ctor 同行無法區分(故應改 AST)
        direct_consumers.append(f"{rel}:{lineno}:0")

    return {
        "factory_callers": sorted(factory_callers),
        "direct_consumers": sorted(direct_consumers),
    }


def _direct_consumer_line_key(entry: str) -> str:
    """``path:line:col`` → ``path:line``(與 B0 舊 allowlist 比對用)."""
    parts = entry.rsplit(":", 2)
    if len(parts) == 3 and parts[1].isdigit():
        return f"{parts[0]}:{parts[1]}"
    return entry


def compare_consumer_allowlist(
    current: dict[str, list[str]],
    frozen: dict[str, set[str]],
) -> tuple[list[str], list[str]]:
    """回傳 (extra_factory_callers, extra_direct_consumers).

    direct: 以 path:line 計數(Counter);現況 count > 凍結 count → 多出的每次算一 extra。
    支援舊凍結檔(path:line,無 col)與新 AST 輸出(path:line:col)。
    """
    extra_callers = sorted(set(current["factory_callers"]) - frozen["factory_callers"])

    frozen_line_counts: Counter[str] = Counter()
    for item in frozen["direct_consumers"]:
        frozen_line_counts[_direct_consumer_line_key(item)] += 1

    current_line_counts: Counter[str] = Counter()
    for item in current["direct_consumers"]:
        current_line_counts[_direct_consumer_line_key(item)] += 1

    extra_direct: list[str] = []
    for key, cur_n in sorted(current_line_counts.items()):
        frozen_n = frozen_line_counts.get(key, 0)
        if cur_n > frozen_n:
            for i in range(frozen_n, cur_n):
                extra_direct.append(f"{key}#occ{i + 1}")
    return extra_callers, extra_direct


def freeze_factory_allowlist() -> str:
    """AST 掃描並寫成可機讀 allowlist 文字."""
    norm = scan_factor_return_consumers_ast()

    # 欄位分隔用 ASCII RS 風格明確標記,避免空白被顯示吞掉:
    # 每行: <kind>|<path-or-path:line:col>
    lines = [
        "# IC1CFR-STOPGAP B0 factory allowlist (frozen)",
        f"# scanner: AST Call of {FACTORY_CREATE_SYMBOL!r} + {DIRECT_CLASS_NAME!r}",
        "# rules: factory definition (momentum/factories.py) excluded from factory_callers;",
        "#        direct_consumers keep path:line:col (multi-ctor on same line not deduped);",
        f"#        scanner self ({SCANNER_SELF_REL}) excluded; import aliases tracked.",
        "# format: factory_caller|<relpath> OR direct_consumer|<relpath>:<lineno>:<col>",
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
    # 必須像測試路徑(含 / 或 tests 前綴)。拒絕 log 偽陽性:
    #   "ERROR    momentum.Analysis.ic_filter_orchestrator:ic_filter_orchestrator.py:1800 ..."
    # (pytest Captured log / logger:pathname:lineno 格式)
    for line in text.splitlines():
        if "::" in line:
            continue
        m = re.match(r"^ERROR\s+(?:collecting\s+)?(\S+\.py)\b", line)
        if not m:
            continue
        path = m.group(1).strip()
        if "/" not in path and not path.startswith("tests"):
            continue
        # logger pathname 常含 "pkg.mod:file.py" 單冒號前綴
        if re.match(r"^[A-Za-z_][\w.]*:", path):
            continue
        nodeids.add(path)

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


AFTER_DEFAULT_JSON = OUT_DIR / "after_default.json"
AFTER_EXPLICIT_JSON = OUT_DIR / "after_explicit.json"
UNAVAILABLE_REASON = "ls_returns_timestamp_misaligned (1c-FR-FULL)"


def _report_dict_from_orch(force_modules: list[str] | None) -> dict[str, Any]:
    orch = _build_orchestrator_with_real_kline()
    report = orch.run_deep_analysis(force_modules=force_modules)
    report_dict = _sanitize_for_strict_json(asdict(report))
    if not isinstance(report_dict, dict):
        raise SystemExit("FAIL: report serialize not dict")
    return report_dict


def _is_fr_scope_path(path: str) -> bool:
    for prefix in FR_SCOPE_PATH_PREFIXES:
        if path == prefix or path.startswith(prefix + "."):
            return True
    return False


def _leaf_paths(obj: Any, *, path: str = "") -> dict[str, Any]:
    """展開 JSON 樹為 path→leaf 值(dict/list 繼續;葉含 null/bool/number/str)."""
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        if not obj:
            out[path] = {}
            return out
        for k, v in obj.items():
            child = f"{path}.{k}" if path else str(k)
            out.update(_leaf_paths(v, path=child))
        return out
    if isinstance(obj, list):
        if not obj:
            out[path] = []
            return out
        for i, v in enumerate(obj):
            child = f"{path}.{i}" if path else str(i)
            out.update(_leaf_paths(v, path=child))
        return out
    out[path] = obj
    return out


def compare_non_fr_paths_exact(
    before_payload: dict[str, Any],
    after_payload: dict[str, Any],
    *,
    exclude: frozenset[str] = CANONICAL_EXCLUDE_JSON_PATHS,
) -> list[str]:
    """§G 非 FR 逐 JSON-path exact compare(atol=0).

    排除:canonical exclude 清單 + factor_returns scope path。
    回傳 path diff 字串列表;空=通過。
    """
    before_stripped = strip_canonical_excludes(before_payload, patterns=exclude)
    after_stripped = strip_canonical_excludes(after_payload, patterns=exclude)

    # 只比 report.results[非 FR] 與非 FR module_summary 等;用全樹 leaf 後濾 FR scope
    before_leaves = {
        p: v
        for p, v in _leaf_paths(before_stripped).items()
        if p.startswith("report.") and not _is_fr_scope_path(p)
    }
    after_leaves = {
        p: v
        for p, v in _leaf_paths(after_stripped).items()
        if p.startswith("report.") and not _is_fr_scope_path(p)
    }

    diffs: list[str] = []
    all_paths = sorted(set(before_leaves) | set(after_leaves))
    for p in all_paths:
        if p not in before_leaves:
            diffs.append(f"+ {p} = {after_leaves[p]!r} (only in after)")
            continue
        if p not in after_leaves:
            diffs.append(f"- {p} = {before_leaves[p]!r} (only in before)")
            continue
        bv = before_leaves[p]
        av = after_leaves[p]
        if bv != av:
            # 浮點欄亦 atol=0(SPEC §G)
            diffs.append(f"~ {p}: before={bv!r} after={av!r}")
    return diffs


def assert_non_fr_exact_vs_before(
    after_payload: dict[str, Any],
    *,
    before_path: Path = BEFORE_JSON,
    mode: str = "after",
) -> None:
    """讀 before.json 與 after payload 做 §G 非 FR exact;FAIL 列 path diff."""
    if not before_path.is_file():
        raise SystemExit(f"FAIL {mode}: missing before baseline {before_path}")
    before_payload = json.loads(before_path.read_text(encoding="utf-8"))
    if not isinstance(before_payload, dict):
        raise SystemExit(f"FAIL {mode}: before.json root not dict")
    diffs = compare_non_fr_paths_exact(before_payload, after_payload)
    if diffs:
        print(f"FAIL {mode}: non-FR path diffs ({len(diffs)}):", file=sys.stderr)
        for d in diffs[:200]:
            print(f"  {d}", file=sys.stderr)
        if len(diffs) > 200:
            print(f"  ... and {len(diffs) - 200} more", file=sys.stderr)
        raise SystemExit(f"FAIL {mode}: non-FR exact compare failed ({len(diffs)} paths)")


def self_prove_non_fr_gate_reds_on_tamper(
    after_payload: dict[str, Any],
    *,
    before_path: Path = BEFORE_JSON,
) -> None:
    """自證:刻意改一個非 FR 模組值 → compare 必紅(否則 gate 無牙)."""
    before_payload = json.loads(before_path.read_text(encoding="utf-8"))
    tampered = json.loads(json.dumps(after_payload))
    results = (tampered.get("report") or {}).get("results") or {}
    # 挑一個非 FR 模組注入可觀測漂移
    target_mod = None
    for name in sorted(results.keys()):
        if name == "factor_returns":
            continue
        if isinstance(results[name], dict):
            target_mod = name
            break
    if target_mod is None:
        raise SystemExit("FAIL self-prove: no non-FR module in after results to tamper")
    # 注入明確假值
    results[target_mod] = dict(results[target_mod])
    results[target_mod]["__ic1cfr_tamper_probe__"] = 0.123456789
    diffs = compare_non_fr_paths_exact(before_payload, tampered)
    probe_hits = [d for d in diffs if "__ic1cfr_tamper_probe__" in d]
    if not probe_hits:
        raise SystemExit(
            "FAIL self-prove: tampering non-FR module did not produce path diff "
            f"(gate toothless; target={target_mod})"
        )
    print(f"self-prove non-FR gate red OK: target={target_mod} diffs={len(probe_hits)}")


def freeze_after_default() -> int:
    """§G after-default: pure default-off → factor_returns not_run + 無 results 節.

    以 force_modules=全模組除 factor_returns 跑(對照 before 的非 FR 節);
    factor_return 不在 force 且 default-off → not_run。
    另做 §G 非 FR 逐 path exact vs before.json。
    """
    from datetime import datetime, timezone

    force = [m for m in ALL_DEEP_MODULES if m != "factor_returns"]
    report_dict = _report_dict_from_orch(force)

    module_summary = report_dict.get("module_summary") or {}
    fr_status = module_summary.get("factor_returns")
    results = report_dict.get("results") or {}
    if fr_status != "not_run":
        raise SystemExit(
            f"FAIL after-default: module_summary.factor_returns={fr_status!r} expected 'not_run'"
        )
    if "factor_returns" in results:
        raise SystemExit(
            "FAIL after-default: results.factor_returns present (expected absent under not_run)"
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "generated_by": "ic1cfr_stopgap_freeze --after-default",
        "lineage": {
            "fixture_sha256": _sha256_file(FIXTURE_PATH),
            "fixture_path": FIXTURE_PATH.relative_to(REPO_ROOT).as_posix(),
            "git_head": _git_head(),
            "kline_cache": KLINE_CACHE.relative_to(REPO_ROOT).as_posix(),
            "generated_at": generated_at,
            "mode": "after-default",
        },
        "canonical_exclude_json_paths": sorted(CANONICAL_EXCLUDE_JSON_PATHS),
        "report": report_dict,
    }

    # §G: 非 FR 逐 path exact vs before + 自證 gate 有牙
    assert_non_fr_exact_vs_before(payload, mode="after-default")
    self_prove_non_fr_gate_reds_on_tamper(payload)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_digest = _write_json(AFTER_DEFAULT_JSON, payload)
    canon = canonical_sha256(payload)
    rel = AFTER_DEFAULT_JSON.relative_to(REPO_ROOT).as_posix()
    print(f"wrote {rel}")
    print(f"raw_sha256={raw_digest}")
    print(f"canonical_sha256={canon}")
    print(f"module_summary.factor_returns={fr_status}")
    print("factor_returns_results_absent=yes")
    print("non_fr_exact_vs_before=pass")
    return 0


def freeze_after_explicit() -> int:
    """§G after-explicit: force_modules 含 factor_returns → §U union + summary unavailable.

    另做 §G 非 FR 逐 path exact vs before.json。
    """
    from datetime import datetime, timezone

    report_dict = _report_dict_from_orch(list(ALL_DEEP_MODULES))

    module_summary = report_dict.get("module_summary") or {}
    fr_status = module_summary.get("factor_returns")
    fr_body = (report_dict.get("results") or {}).get("factor_returns")
    if fr_status != "unavailable":
        raise SystemExit(
            f"FAIL after-explicit: module_summary.factor_returns={fr_status!r} "
            "expected 'unavailable'"
        )
    if not isinstance(fr_body, dict):
        raise SystemExit("FAIL after-explicit: results.factor_returns missing or not dict")
    if fr_body.get("status") != "unavailable":
        raise SystemExit(
            f"FAIL after-explicit: union status={fr_body.get('status')!r} expected unavailable"
        )
    if fr_body.get("value") is not None:
        raise SystemExit("FAIL after-explicit: union value must be null")
    reason = str(fr_body.get("reason") or "")
    if UNAVAILABLE_REASON not in reason and "ls_returns_timestamp_misaligned" not in reason:
        raise SystemExit(f"FAIL after-explicit: unexpected reason={reason!r}")
    if _has_finite_numeric_leaf(fr_body):
        raise SystemExit("FAIL after-explicit: factor_returns still has finite numeric leaf")

    errors = report_dict.get("deep_analysis_errors") or []
    for err in errors:
        if isinstance(err, dict) and err.get("module_name") == "factor_returns":
            raise SystemExit(
                "FAIL after-explicit: factor_returns must not appear in deep_analysis_errors"
            )

    generated_at = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "generated_by": "ic1cfr_stopgap_freeze --after-explicit",
        "lineage": {
            "fixture_sha256": _sha256_file(FIXTURE_PATH),
            "fixture_path": FIXTURE_PATH.relative_to(REPO_ROOT).as_posix(),
            "git_head": _git_head(),
            "kline_cache": KLINE_CACHE.relative_to(REPO_ROOT).as_posix(),
            "generated_at": generated_at,
            "mode": "after-explicit",
        },
        "canonical_exclude_json_paths": sorted(CANONICAL_EXCLUDE_JSON_PATHS),
        "report": report_dict,
    }

    assert_non_fr_exact_vs_before(payload, mode="after-explicit")
    self_prove_non_fr_gate_reds_on_tamper(payload)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_digest = _write_json(AFTER_EXPLICIT_JSON, payload)
    canon = canonical_sha256(payload)
    rel = AFTER_EXPLICIT_JSON.relative_to(REPO_ROOT).as_posix()
    print(f"wrote {rel}")
    print(f"raw_sha256={raw_digest}")
    print(f"canonical_sha256={canon}")
    print(f"module_summary.factor_returns={fr_status}")
    print("factor_returns_union=unavailable")
    print("factor_returns_finite_leaves=no")
    print("non_fr_exact_vs_before=pass")
    return 0


def _resolve_out_path(profile: str, out: str | None) -> Path:
    """解析 --out;預設 before.json / after_full.json under full baseline dir."""
    if out:
        path = Path(out)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path
    if profile == "before-full":
        return FULL_BEFORE_JSON
    if profile == "after-full":
        return FULL_AFTER_JSON
    raise SystemExit(f"FAIL: unknown profile for out path: {profile!r}")


def freeze_decoupling_baseline(*, out_path: Path = DECOUPLING_BASELINE) -> str:
    """跑 check_decoupling.sh,寫 R2/R3/R4 計數 baseline 一行.

    現況 pre-existing 債 R2=1 R3=17 R4=2;gate=baseline-delta 不增。
    """
    script = REPO_ROOT / "scripts" / "check_decoupling.sh"
    if not script.is_file():
        raise SystemExit(f"FAIL: missing {script}")
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    matches = re.findall(r"R2=\d+ R3=\d+ R4=\d+", combined)
    if not matches:
        raise SystemExit(
            "FAIL: check_decoupling.sh produced no R2=… R3=… R4=… line; "
            f"returncode={proc.returncode}\ntail:\n{combined[-1500:]}"
        )
    # 取最後一筆(腳本可能多行;canonical 為總結行)
    line = matches[-1]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = line if line.endswith("\n") else line + "\n"
    out_path.write_text(text, encoding="utf-8")
    rel = out_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    print(f"wrote {rel}: {line}")
    return line


def _assert_fixture_name(fixture: str | None) -> None:
    name = fixture or "ic_api_real_kline"
    if name not in ALLOWED_FIXTURES:
        raise SystemExit(
            f"FAIL: unknown --fixture {name!r}; allowed={sorted(ALLOWED_FIXTURES)}"
        )
    if not FIXTURE_PATH.is_file():
        raise SystemExit(f"FAIL: fixture missing: {FIXTURE_PATH}")
    if not KLINE_CACHE.is_file():
        raise SystemExit(f"FAIL: requires_kline: missing {KLINE_CACHE}")


def _build_full_profile_payload(
    profile: str,
    report_dict: dict[str, Any],
) -> dict[str, Any]:
    """1c-FR-FULL baseline payload:頂層 results + report + lineage."""
    from datetime import datetime, timezone

    generated_at = datetime.now(timezone.utc).isoformat()
    results = report_dict.get("results") or {}
    module_summary = report_dict.get("module_summary") or {}
    if not isinstance(results, dict):
        raise SystemExit(f"FAIL {profile}: report.results not dict")
    return {
        "generated_at": generated_at,
        "generated_by": f"ic1cfr_stopgap_freeze --profile {profile}",
        "profile": profile,
        "lineage": {
            "fixture_sha256": _sha256_file(FIXTURE_PATH),
            "fixture_path": FIXTURE_PATH.relative_to(REPO_ROOT).as_posix(),
            "git_head": _git_head(),
            "kline_cache": KLINE_CACHE.relative_to(REPO_ROOT).as_posix(),
            "generated_at": generated_at,
            "mode": profile,
            "fixture": "ic_api_real_kline",
        },
        "canonical_exclude_json_paths": sorted(CANONICAL_EXCLUDE_JSON_PATHS),
        # 頂層 results / module_summary:TODO B0.1 驗收「頂層 results 鍵集合」
        "results": results,
        "module_summary": module_summary,
        "deep_analysis": report_dict,
        "report": report_dict,
    }


def freeze_profile_before_full(*, out: str | None = None, fixture: str | None = None) -> int:
    """1c-FR-FULL B0.1: stopgap 現態(FR unavailable)+非 FR 模組 path 值.

    寫 --out(預設 handoffs/ic1cfr_full_baseline/before.json)+印 sha256;
    並凍 decoupling_baseline.txt。
    """
    _assert_fixture_name(fixture)
    out_path = _resolve_out_path("before-full", out)

    report_dict = _report_dict_from_orch(list(ALL_DEEP_MODULES))
    module_summary = report_dict.get("module_summary") or {}
    fr_status = module_summary.get("factor_returns")
    fr_body = (report_dict.get("results") or {}).get("factor_returns")

    if fr_status != "unavailable":
        raise SystemExit(
            f"FAIL before-full: module_summary.factor_returns={fr_status!r} "
            "expected 'unavailable' (stopgap 現態)"
        )
    if not isinstance(fr_body, dict):
        raise SystemExit("FAIL before-full: results.factor_returns missing or not dict")
    if fr_body.get("status") != "unavailable":
        raise SystemExit(
            f"FAIL before-full: union status={fr_body.get('status')!r} expected unavailable"
        )
    if fr_body.get("value") is not None:
        raise SystemExit("FAIL before-full: union value must be null under stopgap")
    reason = str(fr_body.get("reason") or "")
    if UNAVAILABLE_REASON not in reason and "ls_returns_timestamp_misaligned" not in reason:
        raise SystemExit(f"FAIL before-full: unexpected reason={reason!r}")
    if _has_finite_numeric_leaf(fr_body):
        raise SystemExit("FAIL before-full: factor_returns still has finite numeric leaf")

    # 非 FR 模組至少一節有內容(path 值凍結用)
    results = report_dict.get("results") or {}
    non_fr = [k for k in results if k != "factor_returns"]
    if not non_fr:
        raise SystemExit("FAIL before-full: no non-FR module results to freeze")

    payload = _build_full_profile_payload("before-full", report_dict)
    if "results" not in payload:
        raise SystemExit("FAIL before-full: payload missing top-level results")

    raw_digest = _write_json(out_path, payload)
    canon = canonical_sha256(payload)
    try:
        rel = out_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        rel = str(out_path)

    # decoupling baseline(B0.1 硬性)
    decouple_line = freeze_decoupling_baseline()

    print(f"wrote {rel}")
    print(f"raw_sha256={raw_digest}")
    print(f"canonical_sha256={canon}")
    print(f"module_summary.factor_returns={fr_status}")
    print("factor_returns_union=unavailable")
    print(f"non_fr_modules={sorted(non_fr)}")
    print(f"decoupling_baseline={decouple_line}")
    print(f"sha256sum {rel} = {raw_digest}")
    return 0


def freeze_profile_after_full(*, out: str | None = None, fixture: str | None = None) -> int:
    """1c-FR-FULL after-full:同結構骨架;F0 後期望 ok union,本批僅旗標/骨架.

    現況(pre-F0)FR 仍可能 unavailable——仍寫 JSON+sha256 供管線可跑;
    F0 gate 重凍時若 status==ok 則記錄 schema_version 等。
    """
    _assert_fixture_name(fixture)
    out_path = _resolve_out_path("after-full", out)

    report_dict = _report_dict_from_orch(list(ALL_DEEP_MODULES))
    module_summary = report_dict.get("module_summary") or {}
    fr_status = module_summary.get("factor_returns")
    fr_body = (report_dict.get("results") or {}).get("factor_returns")
    results = report_dict.get("results") or {}
    if not isinstance(results, dict) or not results:
        raise SystemExit("FAIL after-full: report.results missing or empty")

    payload = _build_full_profile_payload("after-full", report_dict)
    # F0 後:ok union 形狀註記(骨架已支援;未達 ok 不硬 fail——本批 B0 僅骨架)
    if isinstance(fr_body, dict) and fr_body.get("status") == "ok":
        value = fr_body.get("value") or {}
        if isinstance(value, dict):
            payload["after_full_notes"] = {
                "factor_returns_status": "ok",
                "schema_version": value.get("schema_version"),
                "semantics": value.get("semantics"),
            }
    else:
        payload["after_full_notes"] = {
            "factor_returns_status": fr_status,
            "note": (
                "pre-F0 scaffold: FR not yet ok union; re-freeze after F0 for "
                "canonical after_full hashes"
            ),
        }

    raw_digest = _write_json(out_path, payload)
    canon = canonical_sha256(payload)
    try:
        rel = out_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        rel = str(out_path)

    print(f"wrote {rel}")
    print(f"raw_sha256={raw_digest}")
    print(f"canonical_sha256={canon}")
    print(f"module_summary.factor_returns={fr_status}")
    print(f"after_full_notes={payload.get('after_full_notes')}")
    print(f"sha256sum {rel} = {raw_digest}")
    return 0


def freeze_profile(
    profile: str,
    *,
    out: str | None = None,
    fixture: str | None = None,
) -> int:
    """分派 --profile before-full / after-full."""
    if profile not in FULL_PROFILES:
        raise SystemExit(
            f"FAIL: unknown --profile {profile!r}; allowed={sorted(FULL_PROFILES)}"
        )
    if profile == "before-full":
        return freeze_profile_before_full(out=out, fixture=fixture)
    return freeze_profile_after_full(out=out, fixture=fixture)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IC1CFR stopgap / FULL §G freeze")
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
    mode.add_argument(
        "--profile",
        choices=sorted(FULL_PROFILES),
        help="1c-FR-FULL baseline profile: before-full | after-full",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (profiles only; default under handoffs/ic1cfr_full_baseline/)",
    )
    parser.add_argument(
        "--fixture",
        default="ic_api_real_kline",
        help="Fixture name (only ic_api_real_kline; real kline, no synthetic)",
    )
    args = parser.parse_args(argv)

    if args.profile:
        return freeze_profile(args.profile, out=args.out, fixture=args.fixture)
    if args.after_default:
        return freeze_after_default()
    if args.after_explicit:
        return freeze_after_explicit()
    if args.check_nodeids:
        return check_nodeids()
    if args.before:
        return freeze_before()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

