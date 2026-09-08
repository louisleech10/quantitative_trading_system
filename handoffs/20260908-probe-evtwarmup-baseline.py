#!/usr/bin/env python
"""EVTWARMUP §A／§G 基線探針：改前之事件路徑降級形狀＋rolling 視窗未換算之事實。

    venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py [--write]

輸出（--write 時落 tests/golden/evtwarmup/baseline.json）：
- engine_timeframe_key_present：`ICConfig().ic_calculation.model_dump()` 是否含 `timeframe`（預期 False）
- adjusted_windows_default／adjusted_windows_1h：`_adjust_rolling_windows` 無 timeframe vs 手塞 1h
- event_run：真實 la0 fixture＋80 事件之 `ic_train_test_split.applied`／`oos_downgrade.reason`／`event_filter.label_source`
- global_run：同 fixture 無事件之 `ic_train_test_split`（改後**必須逐鍵不變**）
🔴 誠實邊界：fixture 為 12h／1696 根；使用者實機為 1h／20k 根。基線釘的是**形狀**（降級與否、原因、鍵集），不是使用者的數字。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
OUT = REPO / "tests" / "golden" / "evtwarmup" / "baseline.json"


def main() -> int:
    from momentum.Analysis.ic_config_schema import ICConfig
    from momentum.Analysis.ic_engine import ICEngine
    from tests.momentum.helpers.ichc_run import feature_index, run_analyze

    cfg = ICConfig()
    dump = cfg.ic_calculation.model_dump()
    engine = ICEngine(dump)
    engine_1h = ICEngine({**dump, "timeframe": "1h"})
    facts = {
        "engine_timeframe_key_present": "timeframe" in dump,
        "engine_timeframe_attr": engine._timeframe,
        "adjusted_windows_default": engine._adjust_rolling_windows(list(cfg.ic_calculation.rolling_windows)),
        "adjusted_windows_1h": engine_1h._adjust_rolling_windows(list(cfg.ic_calculation.rolling_windows)),
        "reference_tf": cfg.ic_calculation.icir.reference_tf,
        "min_events": cfg.event_filter.min_events,
        "icir_min": cfg.thresholds.icir_min,
    }

    ctx = {"event_manifest_hash": "1" * 64, "label_definition_hash": "2" * 64,
           "decision_time_rule": "t0_open_minus_k_bars", "feature_cutoff_rule": "max_close_ms_le_decision_at",
           "label_window_rule": "close_to_close:horizon_bars=2", "control_kind": "user_labeled_same_trigger"}
    idx = feature_index(80)
    rng = np.random.default_rng(20260908)
    lv = {int(t.value // 10**6): float(v) for t, v in zip(idx, rng.normal(0, 0.02, len(idx)))}
    ev = run_analyze({"event_filter": {"enabled": True, "min_events": 30}},
                     event_timestamps=list(lv), event_label_values=lv,
                     event_label_owners={t: f"ev{i:03d}" for i, t in enumerate(lv)}, event_context=ctx)
    gl = run_analyze(None)

    def pick(rep):
        m = rep.get("metadata") or {}
        return {
            "ic_train_test_split": m.get("ic_train_test_split"),
            "oos_downgrade": m.get("oos_downgrade"),
            "analysis_status": rep.get("analysis_status"),
            "oos_guarantees": rep.get("oos_guarantees"),
            "event_filter_label_source": (m.get("event_filter") or {}).get("label_source"),
            "event_filter_tier": (m.get("event_filter") or {}).get("tier"),
            "n_summary_rows": len(rep.get("summary_table") or []),
        }

    payload = {"facts": facts, "event_run": pick(ev), "global_run": pick(gl)}
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1, default=str)
    print(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    print(f"\nsha256 = {digest}")
    if "--write" in sys.argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text + "\n", encoding="utf-8")
        print(f"已寫入 {OUT.relative_to(REPO)}")
    elif OUT.is_file():
        cur = hashlib.sha256(OUT.read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest()
        print(f"與既有 golden 相同？ **{cur == digest}**")
        return 0 if cur == digest else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
