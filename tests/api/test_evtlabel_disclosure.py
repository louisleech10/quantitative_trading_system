"""EVTLABEL Task 1.1：`metadata.event_label_rule` 揭露——鍵集＝契約、單位換算、0/1 存在與否、非事件 run 不寫。

SPEC：`docs/EVTLABEL_SPEC.md` Task 1.1　TODO：Task 1.1

值取自受理 run receipt（2026-09-10 §A）：165 事件、label 136/29、12h 事件×1h 特徵、h=1 c2c ⇒ 視窗 12 根。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from momentum.Analysis.event_label_mode import (
    build_event_label_rule,
    event_label_rule_keys,
    load_event_label_mode_contract,
    return_formula,
)

TF_SECONDS = {"1h": 3600, "12h": 43200, "4h": 14400}
H12 = 43_200_000


@dataclass(frozen=True)
class _Win:
    event_id: str
    symbol: str
    timeframe: str
    decision_at_ms: int
    entry_at_ms: int
    label_start_ms: int
    label_end_ms: int


def _windows(n: int, tf: str = "12h", bars: int = 1, bar_ms: int = H12):
    out = []
    for i in range(n):
        t0 = 1_735_776_000_000 + i * 2 * bar_ms
        out.append(_Win(f"ETHUSDT:{tf}:{t0}", "ETHUSDT", tf, t0, t0, t0, t0 + bars * bar_ms))
    return out


def _records(n_pos: int, n_neg: int, with_label: bool = True):
    recs = []
    for i in range(n_pos + n_neg):
        r = {"event_id": f"e{i}", "symbol": "ETHUSDT", "timeframe": "12h", "t0": 1_735_776_000_000 + i}
        if with_label:
            r["label"] = 1 if i < n_pos else 0
        recs.append(r)
    return recs


SPEC_H1 = {"horizon_bars": 1, "entry_price_semantic": "trigger_close", "label_return_mode": "close_to_close", "decision_offset_bars": 0}


def test_keys_equal_contract_and_receipt_values():
    rule = build_event_label_rule(
        normalized_spec=SPEC_H1, windows=_windows(165), records=_records(136, 29),
        feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
        label_source="event_label_value", statistic_kind="conditional_ic", n_events_consumed=165,
    )
    assert set(rule) == set(event_label_rule_keys())
    assert rule["h_unit"] == load_event_label_mode_contract()["h_unit_value"]
    assert rule["event_timeframe"] == "12h" and rule["feature_timeframe"] == "1h"
    assert rule["feature_bars_per_event_bar"] == 12 and rule["ratio_integral"] is True
    assert rule["label_window_feature_bars"] == 12  # h=1 c2c ⇒ 一根 12h ＝ 12 根 1h
    assert rule["imported_binary_label"] == {"present": True, "n_pos": 136, "n_neg": 29, "used": False}
    assert rule["n_events_consumed"] == 165
    assert rule["label_source"] == "event_label_value" and rule["statistic_kind"] == "conditional_ic"
    assert "close[t0+h]" in rule["return_formula"] and "trigger_close" not in rule["return_formula"]


def test_window_taken_from_receipt_not_recomputed_from_h():
    # o2hc h=12：收據視窗 13 根 12h（open 起算）⇒ 156 根 1h；不得用 h×bar 重算成 144
    spec = {"horizon_bars": 12, "entry_price_semantic": "trigger_open", "label_return_mode": "open_to_horizon_close", "decision_offset_bars": 0}
    rule = build_event_label_rule(
        normalized_spec=spec, windows=_windows(5, bars=13), records=_records(3, 2),
        feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
        label_source="event_label_value", statistic_kind="conditional_ic", n_events_consumed=5,
    )
    assert rule["label_window_feature_bars"] == 156
    assert "price[trigger_open]" in rule["return_formula"]


def test_mixed_timeframes_degrade_ratio():
    wins = _windows(3, tf="12h") + _windows(2, tf="4h", bar_ms=14_400_000)
    rule = build_event_label_rule(
        normalized_spec=SPEC_H1, windows=wins, records=_records(3, 2),
        feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
        label_source="event_label_value", statistic_kind="conditional_ic", n_events_consumed=5,
    )
    assert rule["event_timeframe"] == "mixed"
    assert rule["feature_bars_per_event_bar"] is None and rule["ratio_integral"] is False
    assert rule["label_window_feature_bars"] == 12  # 取 max


def test_legacy_records_without_label_column():
    rule = build_event_label_rule(
        normalized_spec=SPEC_H1, windows=_windows(4), records=_records(2, 2, with_label=False),
        feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
        label_source="event_label_value", statistic_kind="conditional_ic", n_events_consumed=4,
    )
    assert rule["imported_binary_label"] == {"present": False, "n_pos": 0, "n_neg": 0, "used": False}


def test_uniqueness_disclosure_matches_overlap_definition():
    from momentum.Analysis.event_label_mode import uniqueness_from_windows

    # 三事件、視窗 12h：A[0,12h) B[6h,18h) C[24h,36h) ⇒ A/B 相交、C 獨立 ⇒ w=(1/2,1/2,1)、n_eff=2、pairs=1
    h = H12
    wins = [
        _Win("a", "S", "12h", 0, 0, 0, h),
        _Win("b", "S", "12h", 0, 0, h // 2, h // 2 + h),
        _Win("c", "S", "12h", 0, 0, 2 * h, 3 * h),
    ]
    u = uniqueness_from_windows(wins)
    assert u == {"mean": pytest.approx(2 / 3), "min": 0.5, "n_eff": pytest.approx(2.0), "n_overlapping_pairs": 1}
    assert uniqueness_from_windows([]) == {"mean": None, "min": None, "n_eff": None, "n_overlapping_pairs": None}
    # 受理批形狀：165 事件、間距 2 根 12h、視窗 1 根 ⇒ 全不相交 ⇒ n_eff=165
    rule = build_event_label_rule(
        normalized_spec=SPEC_H1, windows=_windows(165), records=_records(136, 29),
        feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
        label_source="event_label_value", statistic_kind="conditional_ic", n_events_consumed=165,
    )
    assert rule["uniqueness"]["n_eff"] == 165 and rule["uniqueness"]["n_overlapping_pairs"] == 0


def test_unknown_mode_formula_is_none_not_blank():
    assert return_formula("weird_mode", "trigger_close") is None
    assert return_formula(None, None) is None


def test_service_hook_writes_key_only_on_event_path_and_without_split():
    from api.services.ic_analysis_service import _inject_isolation_source, _inject_label_rule_disclosure

    prepared = SimpleNamespace(
        normalized_spec_bytes=json.dumps(SPEC_H1).encode("utf-8"),
        windows=_windows(165),
    )
    staged = {
        "prepared": prepared,
        "records": tuple(_records(136, 29)),
        "timeframe_seconds": TF_SECONDS,
        "event_label_by_id": {f"e{i}": 0.0 for i in range(165)},
    }
    report = {"metadata": {"timeframe": "1h", "event_filter": {"label_source": "event_label_value", "statistic_kind": "conditional_ic"}}}
    _inject_isolation_source(staged, report)  # 切分未套用（無 ic_train_test_split）⇒ isolation 不寫、label 規則仍寫
    assert "isolation" not in report["metadata"]
    rule = report["metadata"]["event_label_rule"]
    assert rule["label_window_feature_bars"] == 12 and rule["imported_binary_label"]["n_pos"] == 136

    non_event = {"metadata": {"timeframe": "1h"}}
    _inject_label_rule_disclosure({}, non_event)  # 無 prepared（非事件）⇒ 不寫
    assert "event_label_rule" not in non_event["metadata"]


def test_contract_key_drift_is_fail_closed(monkeypatch):
    import momentum.Analysis.event_label_mode as m

    good = dict(load_event_label_mode_contract())
    bad = dict(good)
    bad["event_label_rule_keys"] = list(good["event_label_rule_keys"]) + ["extra_key"]
    monkeypatch.setattr(m, "load_event_label_mode_contract", lambda: bad)
    with pytest.raises(ValueError, match="鍵集與契約不符"):
        m.build_event_label_rule(
            normalized_spec=SPEC_H1, windows=_windows(2), records=_records(1, 1),
            feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
            label_source="x", statistic_kind="y", n_events_consumed=2,
        )
