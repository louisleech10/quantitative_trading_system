"""FF-STAT §G／Task 4.1 golden 收據（docs/FFSTAT_SPEC.md §G、Task 4.1；r19 codex P2-04）。

以與 `test_ffstat_golden.py::on_run` 相同之輕量真實設定跑一次（隔離 tmp 與 d* 快取），輸出
`handoffs/run_receipts/<日期>-ffstat-golden.json`：
- `decisions`：逐欄決策（校準範圍、N、p 值、fracdiff、d、ADF 階數、事件）；
- `change_report`：與凍結基準相比之決策改變（`ffstat_helpers.decision_change_report`，逐欄舊→新、分類計數、原名字免檢者）；
- `base_digest_before`／`base_digest_after`：基礎欄四 hash 全表之 sha256（改前＝凍結基準），及 `base_changed_columns`。
實作完成前執行會因 metadata 無決策而失敗（非 0）。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/golden_receipt.py
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from _isolate import isolate  # noqa: E402  須先於任何 momentum／helper 匯入

ISOLATED_ROOT = isolate()

from _isolate import isolate_dstar_cache  # noqa: E402
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

isolate_dstar_cache(ISOLATED_ROOT)
REPO = Path(__file__).resolve().parents[3]


def _digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def main() -> int:
    baseline = json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))
    root, _, result = h.run_stat(ISOLATED_ROOT / "run", h.stat_payload())
    decisions = json.loads(json.dumps(h.decisions(result), default=str))
    base_after = h.base_fingerprints(root)
    out = REPO / "handoffs" / "run_receipts" / f"{_dt.date.today():%Y%m%d}-ffstat-golden.json"
    out.write_text(json.dumps({
        "spec": "docs/FFSTAT_SPEC.md §G / Task 4.1",
        "symbol": h.SYMBOL, "timeframe": h.PRIMARY_TF, "window": list(h.WINDOW),
        "decisions": decisions,
        "change_report": h.decision_change_report(baseline["decisions"], decisions),
        "base_digest_before": _digest(baseline["base"]), "base_digest_after": _digest(base_after),
        "base_changed_columns": sorted(c for c in baseline["base"] if base_after.get(c) != baseline["base"][c]),
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
