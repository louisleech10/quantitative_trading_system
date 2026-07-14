#!/usr/bin/env python3
"""IC1C baseline 獨立內容 validator(T-F5:producer 不得自證)。

用法:
  python scripts/ic1c_validate_baseline.py handoffs/ic1c_baseline/g_old.json

驗收(Task 0.1 ⑥):
  - feature 數 ≥ N(fixture 特徵數 - 2)
  - 必含兩 skipped 路徑(oc_return turnover_missing、hl_range gross_ic_missing)
  - 鍵數/型別基本契約
  - fixture_sha256 與現檔 tests/fixtures/ic_api_real_kline.py 一致
  - JSON 可 strict 載入(無 NaN 字面)
  任一不符 → exit 1
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ic_api_real_kline.py"

# 與 freeze 腳本一致的真 fixture 注入名
INJECT_TURNOVER_MISSING = "oc_return"
INJECT_GROSS_IC_MISSING = "hl_range"


def _fail(msg: str) -> None:
    print(f"VALIDATE FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_feature_count() -> int:
    """從 fixture 模組讀 FEATURE_NAMES 長度(不改 fixture)。"""
    # 輕量 parse:import 模組常數
    sys.path.insert(0, str(REPO_ROOT))
    from tests.fixtures.ic_api_real_kline import FEATURE_NAMES

    return len(FEATURE_NAMES)


def _assert_no_nonfinite_literals(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_nonfinite_literals(v, f"{path}.{k}" if path else str(k))
        return
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_no_nonfinite_literals(v, f"{path}[{i}]")
        return
    if isinstance(obj, float) and not math.isfinite(obj):
        _fail(f"non-finite float at {path}: {obj!r}")


def _validate_g_old(payload: dict[str, Any]) -> None:
    # lineage
    for key in ("fixture_sha256", "git_head", "generated_by"):
        if key not in payload:
            _fail(f"missing lineage key: {key}")
        if not isinstance(payload[key], str) or not payload[key]:
            _fail(f"lineage key {key} must be non-empty str")

    if payload["generated_by"] != "ic1c_freeze_baseline --baseline old":
        _fail(f"unexpected generated_by: {payload['generated_by']!r}")

    if not FIXTURE_PATH.is_file():
        _fail(f"fixture file missing: {FIXTURE_PATH}")
    expected_fx = _sha256_file(FIXTURE_PATH)
    if payload["fixture_sha256"] != expected_fx:
        _fail(
            f"fixture_sha256 mismatch: baseline={payload['fixture_sha256']} "
            f"current={expected_fx}"
        )

    if "result" not in payload or not isinstance(payload["result"], dict):
        _fail("missing result dict")

    result = payload["result"]
    features = result.get("features")
    if not isinstance(features, dict):
        _fail("result.features must be dict")

    n_fixture = _fixture_feature_count()
    min_features = n_fixture - 2
    if len(features) < min_features:
        _fail(
            f"feature count {len(features)} < min {min_features} "
            f"(fixture={n_fixture}-2)"
        )

    # 必含兩 skipped 路徑
    if INJECT_TURNOVER_MISSING not in features:
        _fail(f"missing injected feature {INJECT_TURNOVER_MISSING!r}")
    oc = features[INJECT_TURNOVER_MISSING]
    if not isinstance(oc, dict) or oc.get("skipped") is not True:
        _fail(f"{INJECT_TURNOVER_MISSING} must be skipped=True")
    if oc.get("reason") != "turnover_missing":
        _fail(
            f"{INJECT_TURNOVER_MISSING} reason want turnover_missing "
            f"got {oc.get('reason')!r}"
        )

    if INJECT_GROSS_IC_MISSING not in features:
        _fail(f"missing injected feature {INJECT_GROSS_IC_MISSING!r}")
    hl = features[INJECT_GROSS_IC_MISSING]
    if not isinstance(hl, dict) or hl.get("skipped") is not True:
        _fail(f"{INJECT_GROSS_IC_MISSING} must be skipped=True")
    if hl.get("reason") != "gross_ic_missing":
        _fail(
            f"{INJECT_GROSS_IC_MISSING} reason want gross_ic_missing "
            f"got {hl.get('reason')!r}"
        )

    # 非 skipped 必須含現行錯誤鍵 net_ic(故意保留作對照)
    non_skipped = [
        (name, row)
        for name, row in features.items()
        if isinstance(row, dict) and not row.get("skipped")
    ]
    if not non_skipped:
        _fail("expected at least one non-skipped feature for net_ic key check")
    for name, row in non_skipped:
        if "net_ic" not in row:
            _fail(f"non-skipped feature {name!r} missing net_ic key (G-OLD 必含)")
        if not isinstance(row["net_ic"], (int, float)):
            _fail(f"{name}.net_ic must be number, got {type(row['net_ic'])}")
        # 現行 schema 核心鍵
        for req in ("gross_ic", "turnover", "cost_bps"):
            if req not in row:
                _fail(f"{name} missing key {req}")
            if not isinstance(row[req], (int, float)):
                _fail(f"{name}.{req} must be number")

    # summary 型別
    summary = result.get("summary")
    if not isinstance(summary, dict):
        _fail("result.summary must be dict")
    if "total_analyzed" not in summary or not isinstance(
        summary["total_analyzed"], int
    ):
        _fail("summary.total_analyzed must be int")
    if "profitable_count" not in summary or not isinstance(
        summary["profitable_count"], int
    ):
        _fail("summary.profitable_count must be int")

    # non_finite_fields 清單型別
    nff = payload.get("non_finite_fields")
    if nff is not None:
        if not isinstance(nff, list) or not all(isinstance(x, str) for x in nff):
            _fail("non_finite_fields must be list[str]")

    _assert_no_nonfinite_literals(payload)

    # 鍵集合:lineage + result 最小集合
    required_top = {
        "fixture_sha256",
        "git_head",
        "generated_by",
        "result",
    }
    missing = required_top - set(payload.keys())
    if missing:
        _fail(f"missing top-level keys: {sorted(missing)}")

    print("VALIDATE OK")
    print(f"  features={len(features)} (min={min_features})")
    print(f"  skipped: {INJECT_TURNOVER_MISSING}=turnover_missing, "
          f"{INJECT_GROSS_IC_MISSING}=gross_ic_missing")
    print(f"  non_skipped_with_net_ic={len(non_skipped)}")
    print(f"  fixture_sha256={payload['fixture_sha256'][:16]}...")
    print(f"  git_head={payload['git_head'][:12]}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "usage: python scripts/ic1c_validate_baseline.py "
            "<path/to/g_old.json>",
            file=sys.stderr,
        )
        return 2

    path = Path(args[0])
    if not path.is_file():
        _fail(f"file not found: {path}")

    try:
        # allow_nan=False:若檔內有 NaN 字面,json 標準庫仍會 parse 成 float nan
        # 在部分 Python 會拒;統一用 strict load 再掃非有限
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        _fail(f"invalid JSON: {exc}")

    if not isinstance(payload, dict):
        _fail("top-level must be object")

    # 以檔名推斷 baseline 類型;目前僅 g_old 實作
    name = path.name
    if name.startswith("g_old"):
        _validate_g_old(payload)
        return 0
    if name.startswith("g_new"):
        _fail(f"validator for {name} not implemented yet (Phase 1/2)")
        return 1

    _fail(f"unrecognized baseline filename: {name}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
