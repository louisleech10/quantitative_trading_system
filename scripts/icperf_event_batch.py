"""ICPERF Task 0.3：事件匯入批之建批（docs/ICPERF_SPEC.md §G (7)、Task 0.3「事件匯入批」；ICPERF-BUDGET-10）。

現存匯入批於可用資料格窗內皆不足 `min_events` 30 筆（BTCUSDT 12h 於 `A_BTCUSDT_12h` 窗內最多 27 筆；1h 者皆 ETHUSDT
14 筆）⇒ 依使用者 2026-10-29「3.資料不足就要補齊到可以跑和測試」以真實 kline 時間戳依下列明列規則建一批，經服務匯入
入口 `EventImportService.import_records` 落檔（`data_cache/events/`）：

- 資料格：長資料格 L（`icperf_freeze_baseline.LONG_CELL`；sidecar `output_window` 為窗、`source` 為 kline 來源）。
- 事件（因果，只用 0..t）：窗內第 t 根之 close > 前 `BREAKOUT_BARS` 根（不含 t）之 high 最大值。
  `BREAKOUT_BARS`＝6（ICPERF SPEC v5.38 Task 0.3 ①：原 24 根之批〔93 筆〕切分後測試段只 19 筆 < `min_test_events` 30 ⇒
  IC 統計全 null；L 格窗 2,000 根上依各門檻試算之測試段筆數〔grid 第 1,625 根起〕：24⇒19、12⇒28、10⇒31、8⇒36、6⇒41，取 6
  ＝總 203 筆、測試段約 41 筆，對 30 有餘裕且仍為「突破前 N 根高點」之同一規則族；N 以根數計，不假設交易時段）。
- 標籤（前瞻，宣告 `lookahead_bars_declared`＝`HORIZON_BARS`）：close[t+h] > close[t] ⇒ 1，否則 0（close_to_close）；
  t+h 超出窗末之事件不收。
- 其餘欄位：方向 long、進場價 trigger_close、decision_offset_bars 0、scenario B、control_kind
  user_labeled_same_trigger（同現存使用者批）、label_origin platform_generator（規則產生之標籤，契約
  `optional_fields.label_origin` 之列舉值）。

用法：`venv/bin/python scripts/icperf_event_batch.py [--validate-only] [--out <FACT-RECEIPT JSON>]`（秒級，非重型）。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
BREAKOUT_BARS = 6
HORIZON_BARS = 12
RULE_ID = f"icperf-t03:breakout{BREAKOUT_BARS}:close_gt_prior_high:h{HORIZON_BARS}"
SOURCE_NAME = "icperf-task03-event-batch"


def _freeze_module() -> Any:
    spec = importlib.util.spec_from_file_location("icperf_freeze_baseline_eb", REPO / "scripts" / "icperf_freeze_baseline.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _cell_window() -> Dict[str, Any]:
    """L 格 sidecar 之標的、主週期、輸出段與 kline 來源。"""
    fb = _freeze_module()
    side = json.loads((REPO / fb.LONG_CELL_ROOT.format(cell=fb.LONG_CELL) / "numview_cell.json").read_text(encoding="utf-8"))
    return {"cell": fb.LONG_CELL, "symbol": side["symbol"], "timeframe": side["primary_tf"],
            "output_window": list(side["output_window"]), "source": side["source"]}


def build_records(cell: Dict[str, Any]) -> Dict[str, Any]:
    """依模組說明之規則自真實 kline 建事件列；回 {"records", "kline_digest", "n_bars"}。"""
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(cell["source"], "r") as f:
        data = f[f"{cell['symbol']}/{cell['timeframe']}/data"][:]
    ts = data["timestamp"].astype("int64")
    unit = "ms" if int(ts[-1]) > 10 ** 12 else "s"
    idx = pd.to_datetime(ts, unit=unit, utc=True)
    frame = pd.DataFrame({"high": data["high"].astype("float64"), "close": data["close"].astype("float64")}, index=idx)
    start, end = (pd.Timestamp(t) for t in cell["output_window"])
    win = frame.loc[start:end]
    prior_high = frame["high"].shift(1).rolling(BREAKOUT_BARS, min_periods=BREAKOUT_BARS).max().loc[start:end]
    future_close = win["close"].shift(-HORIZON_BARS)
    t0_ms = (win.index.asi8 // 1_000_000).astype("int64")
    kline_digest = hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest()
    records: List[Dict[str, Any]] = []
    for i, (t, close) in enumerate(win["close"].items()):
        if not (close > prior_high.iloc[i]) or not np.isfinite(future_close.iloc[i]):
            continue
        records.append({
            "event_id": f"{cell['symbol']}:{cell['timeframe']}:{int(t0_ms[i])}", "symbol": cell["symbol"],
            "timeframe": cell["timeframe"], "t0": int(t0_ms[i]), "decision_offset_bars": 0,
            "entry_price_semantic": "trigger_close", "direction": "long", "scenario": "B",
            "label": int(future_close.iloc[i] > close),
            "label_definition": {"rule_id": RULE_ID, "label_return_mode": "close_to_close",
                                 "window": {"horizon_bars": HORIZON_BARS},
                                 "canonical_digest": hashlib.sha256(RULE_ID.encode("utf-8")).hexdigest()},
            "control_kind": "user_labeled_same_trigger", "label_origin": "platform_generator",
            "source_file_digest": kline_digest,
            "data_snapshot_digest": f"kline_cache:{cell['symbol']}:{cell['timeframe']}:{int(ts[-1])}",
            "lookahead_bars_declared": {cell["timeframe"]: HORIZON_BARS},
        })
    return {"records": records, "kline_digest": kline_digest, "n_bars": int(len(win))}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--validate-only", action="store_true", help="只驗契約、不落檔")
    parser.add_argument("--out", type=Path, default=None, help="FACT-RECEIPT JSON")
    args = parser.parse_args(argv)
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from api.services.case_import_service import EventImportRejectedError, EventImportService

    cell = _cell_window()
    built = build_records(cell)
    records = built["records"]
    upload = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    try:
        resp = EventImportService().import_records(records, source_name=SOURCE_NAME, upload_bytes=upload,
                                                  validate_only=bool(args.validate_only))
    except EventImportRejectedError as exc:
        reasons = sorted({(f.field, f.reason) for f in exc.payload.failures or []})
        print(json.dumps({"rejected": exc.payload.message, "reasons": reasons,
                          "first": [f.model_dump() for f in (exc.payload.failures or [])[:3]]},
                         ensure_ascii=False, indent=1, default=str), file=sys.stderr)
        return 1
    labels = [int(r["label"]) for r in records]
    receipt = {"rule": {"rule_id": RULE_ID, "breakout_bars": BREAKOUT_BARS, "horizon_bars": HORIZON_BARS,
                        "doc": "scripts/icperf_event_batch.py 模組說明"},
               "cell": cell, "n_window_bars": built["n_bars"], "kline_sha256": built["kline_digest"],
               "n_events": len(records), "n_label_1": sum(labels), "n_label_0": len(labels) - sum(labels),
               "import_id": resp.import_id, "stored_path": resp.stored_path, "n_valid": resp.n_valid,
               "warnings": list(resp.warnings), "lookahead_declaration": resp.lookahead_declaration,
               "upload_sha256": resp.upload_sha256, "validate_only": bool(args.validate_only)}
    text = json.dumps(receipt, ensure_ascii=False, indent=1, default=str)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
