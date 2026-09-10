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


def test_disclosure_scoped_to_consumed_events_only():
    """R1 `CODEX-R1-P1-01`：混 symbol 批中，揭露分母必須＝實際被消費的事件（非本次 symbol 者要排除）。"""
    wins = _windows(3) + [
        _Win("BTCUSDT:12h:900", "BTCUSDT", "12h", 900, 900, 900, 900 + H12),
        _Win("BTCUSDT:12h:901", "BTCUSDT", "12h", 901, 901, 901, 901 + H12),
    ]
    recs = [
        {"event_id": w.event_id, "symbol": w.symbol, "timeframe": "12h", "label": 1 if w.symbol == "ETHUSDT" else 0}
        for w in wins
    ]
    consumed = [w.event_id for w in wins if w.symbol == "ETHUSDT"]
    rule = build_event_label_rule(
        normalized_spec=SPEC_H1, windows=wins, records=recs,
        feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
        label_source="event_label_value", statistic_kind="conditional_ic",
        n_events_consumed=len(consumed), consumed_event_ids=consumed,
    )
    # 被排除的 BTC 兩筆（label=0）不得計入
    assert rule["imported_binary_label"] == {"present": True, "n_pos": 3, "n_neg": 0, "used": False}
    assert rule["n_events_consumed"] == 3
    assert rule["uniqueness"]["n_eff"] == 3  # 只算 ETH 三筆，且彼此不重疊

    # 不給 consumed_event_ids ⇒ 沿用全批（單 symbol 批等價；此處證明差異真的存在）
    all_rule = build_event_label_rule(
        normalized_spec=SPEC_H1, windows=wins, records=recs,
        feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
        label_source="event_label_value", statistic_kind="conditional_ic", n_events_consumed=5,
    )
    assert all_rule["imported_binary_label"]["n_neg"] == 2


def test_consumed_ids_mismatch_is_loud():
    """id 不同源 ⇒ 必須 raise，不得靜默產出空揭露（報告顯示 0 事件卻宣稱成功）。"""
    with pytest.raises(ValueError, match="無交集"):
        build_event_label_rule(
            normalized_spec=SPEC_H1, windows=_windows(3), records=_records(2, 1),
            feature_timeframe="1h", timeframe_seconds=TF_SECONDS,
            label_source="event_label_value", statistic_kind="conditional_ic",
            n_events_consumed=3, consumed_event_ids=["不存在的 id"],
        )


def test_uniqueness_matches_bruteforce_and_scales():
    """R1 `CODEX-R1-P1-02` 三家同判：改 O(n log n) 後語意必須逐筆等同暴力法，且萬級不阻塞。"""
    import random
    import time as _time

    from momentum.Analysis.event_label_mode import uniqueness_from_windows

    def brute(win_list):
        n = len(win_list)
        counts = []
        pairs = 0
        for i, (s_i, e_i) in enumerate(win_list):
            c = 0
            for j, (s_j, e_j) in enumerate(win_list):
                if s_i < e_j and s_j < e_i:
                    c += 1
                    if j > i:
                        pairs += 1
            counts.append(max(1, c))
        w = [1.0 / c for c in counts]
        return {"mean": sum(w) / n, "min": min(w), "n_eff": sum(w), "n_overlapping_pairs": pairs}

    rng = random.Random(20260910)
    for _ in range(20):  # 隨機重疊形態（含巢狀、同端點、完全重合）
        raw = []
        for _k in range(rng.randint(2, 25)):
            start = rng.randrange(0, 50) * 10
            raw.append((start, start + rng.choice([10, 20, 50, 100])))
        wins = [_Win(f"e{i}", "S", "12h", s, s, s, e) for i, (s, e) in enumerate(raw)]
        got = uniqueness_from_windows(wins)
        exp = brute(raw)
        assert got["n_overlapping_pairs"] == exp["n_overlapping_pairs"]
        assert got["n_eff"] == pytest.approx(exp["n_eff"])
        assert got["min"] == pytest.approx(exp["min"])

    # 規模：10,000 事件（匯入 50MiB 檔頂之同階）之揭露不得成為阻塞
    big = [_Win(f"b{i}", "S", "12h", i * H12, i * H12, i * H12, i * H12 + 3 * H12) for i in range(10_000)]
    t0 = _time.perf_counter()
    out = uniqueness_from_windows(big)
    elapsed = _time.perf_counter() - t0
    assert elapsed < 2.0, f"10k 事件之 uniqueness 揭露耗時 {elapsed:.2f}s（O(n²) 回歸）"
    assert out["n_eff"] > 0


def test_unknown_mode_formula_is_none_not_blank():
    assert return_formula("weird_mode", "trigger_close") is None
    assert return_formula(None, None) is None


def test_service_hook_writes_key_only_on_event_path_and_without_split():
    from api.services.ic_analysis_service import _inject_isolation_source, _inject_label_rule_disclosure

    wins = _windows(165)
    prepared = SimpleNamespace(
        normalized_spec_bytes=json.dumps(SPEC_H1).encode("utf-8"),
        windows=wins,
    )
    # 🔴 id 必須與 windows 同源（service 之 `event_label_by_id` 就是由 windows 逐筆建的）；
    #    不同源時 `build_event_label_rule` 會 fail-closed（見 test_consumed_ids_mismatch_is_loud）。
    recs = [
        {"event_id": w.event_id, "symbol": w.symbol, "timeframe": "12h", "label": 1 if i < 136 else 0}
        for i, w in enumerate(wins)
    ]
    staged = {
        "prepared": prepared,
        "records": tuple(recs),
        "timeframe_seconds": TF_SECONDS,
        "event_label_by_id": {w.event_id: 0.0 for w in wins},
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


def _staged_and_report(*, label_source: str):
    """與上方 service hook 測試同源之 fixture（165 事件、136 正／29 反）。"""
    wins = _windows(165)
    prepared = SimpleNamespace(
        normalized_spec_bytes=json.dumps(SPEC_H1).encode("utf-8"), windows=wins,
    )
    recs = [
        {"event_id": w.event_id, "symbol": w.symbol, "timeframe": "12h", "label": 1 if i < 136 else 0}
        for i, w in enumerate(wins)
    ]
    staged = {
        "prepared": prepared, "records": tuple(recs), "timeframe_seconds": TF_SECONDS,
        "event_label_by_id": {w.event_id: 0.0 for w in wins},
    }
    statistic = "binary_discrimination" if label_source == "imported_binary_label" else "conditional_ic"
    report = {"metadata": {"timeframe": "1h", "event_filter": {
        "label_source": label_source, "statistic_kind": statistic}}}
    return staged, report

# ══════════════════════════════════════════════════════════════════════════
# EVTLABEL Task 3.6：報告必須說出「主統計是哪一個」
# ══════════════════════════════════════════════════════════════════════════


def test_binary_run_discloses_primary_statistic_and_effect_gate():
    """🔴 summary 表同時有 `ic_mean` 與 `rank_biserial` 兩欄（報酬版留第二欄）。

    不揭露主統計 ⇒ 使用者無從得知**倖存者是依哪一欄篩出來的**。
    """
    from api.services.ic_analysis_service import _inject_label_rule_disclosure

    staged, report = _staged_and_report(label_source="imported_binary_label")
    report["metadata"]["thresholds"] = {"rank_biserial_min": 0.10}
    report["metadata"]["event_filter"]["permutation_receipt"] = {"seed": 7, "n_perm": 200}
    report["metadata"]["event_filter"]["negative_control"] = {"n_observed": 3, "q95": 1}
    _inject_label_rule_disclosure(staged, report)
    rule = report["metadata"]["event_label_rule"]
    assert rule["primary_statistic"] == "rank_biserial"
    assert rule["secondary_statistic"] == "ic_mean"
    assert rule["effect_gate"] == {"field": "abs(rank_biserial)", "min": 0.10}
    assert rule["imported_binary_label"]["used"] is True
    assert rule["permutation_receipt"]["n_perm"] == 200
    assert rule["negative_control"]["q95"] == 1


def test_return_rule_run_does_not_get_binary_disclosure():
    """報酬版 run ⇒ 不寫這些鍵（否則報告會宣稱用了 0/1）。"""
    from api.services.ic_analysis_service import _inject_label_rule_disclosure

    staged, report = _staged_and_report(label_source="event_label_value")
    _inject_label_rule_disclosure(staged, report)
    rule = report["metadata"]["event_label_rule"]
    for key in ("primary_statistic", "effect_gate", "permutation_receipt", "negative_control"):
        assert key not in rule, f"報酬版不該有 {key}"
    assert rule["imported_binary_label"]["used"] is False


def test_effect_gate_min_is_not_hardcoded_when_thresholds_absent():
    """門檻取不到 ⇒ 寫 None，**不猜**、不硬編第二份預設值。"""
    from api.services.ic_analysis_service import _inject_label_rule_disclosure

    staged, report = _staged_and_report(label_source="imported_binary_label")
    report["metadata"].pop("thresholds", None)
    _inject_label_rule_disclosure(staged, report)
    assert report["metadata"]["event_label_rule"]["effect_gate"]["min"] is None


def test_light_view_keeps_label_mode_and_rule():
    """🔴 `CODEX-R1-P1-04`（B5 review）：前端固定請求 `view=light`。

    `label_mode`（模式 banner）與 `event_label_rule`（規則揭露）若不在 light 白名單裡，
    **正常回應中這兩塊會整個消失**——後端寫了、前端也接了，但中間被投影掉。
    這正是本 epic 反覆出現的「兩端都有、但沒接上」。
    """
    import json
    from pathlib import Path

    keep = json.loads(
        (Path(__file__).resolve().parents[2]
         / "momentum/Analysis/contracts/ic_result_paging_contract.json").read_text(encoding="utf-8")
    )["metadata_keep_keys"]
    assert "label_mode" in keep, "light 視圖會吃掉模式 banner 的資料來源"
    assert "event_label_rule" in keep, "light 視圖會吃掉 label 規則揭露"
    # 既有鍵不得被我擠掉
    for existing in ("event_filter", "isolation", "survivor_output", "period_alignment"):
        assert existing in keep
