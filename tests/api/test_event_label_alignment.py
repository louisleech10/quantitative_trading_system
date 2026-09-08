"""EVTALIGN Task 2.1（D）：驗證對象＝實際被消費的 label；`label_kind` 由 `label_source` 綁定。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 2.1　TODO：Task 2.1

逐條對應：
- 同尾事件模式之合法密集 label（tail_nans=0）⇒ **通過**（GROK-R1-P0-02）→ `*_dense_*`
- 事件 label 與 feature index 錯位 ⇒ 仍 raise → `*_misaligned_*`
- `(event_id, timestamp, label_value)` 整批平移一格 ⇒ raise（R2 三家）→ `*_shifted_*`／`*_triple_bound_*`
- `label_source` 缺席 ⇒ raise，不得預設（§C-7）→ `*_missing_source_*`
- forward_return 被消費序列須為已驗來源之值保持限制 → `*_forward_return_restriction_*`
- 端到端（真實 la0 fixture）：事件路徑報告帶 `label_kind=event_given` 與逐事件消費 label → `*_e2e_*`

mutation：D1 值比對拿掉 ⇒ shifted 紅；D2 缺 label_source 預設 ⇒ missing_source 紅；
D3 service 三元組值比對拿掉 ⇒ triple_bound 紅；A4 對 event_given 套尾端 NaN 契約 ⇒ dense 紅。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from api.services.ic_analysis_service import _assert_event_triple_bound
from momentum.core.contracts import (
    LABEL_KIND_EVENT_GIVEN,
    LABEL_KIND_FORWARD_RETURN,
    AlignmentSpec,
    AlignmentViolationError,
    derive_label_kind,
    validate_alignment,
    validate_consumed_label,
    validate_event_given,
)

N = 40
IDX = pd.date_range("2024-01-01", periods=N, freq="12h")


def _ms(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.asi8 // 10**6).astype("int64")


def _features(index=IDX) -> pd.DataFrame:
    return pd.DataFrame({"f1": np.arange(len(index), dtype=float)}, index=index)


def _dense_label(index=IDX, seed=7) -> pd.Series:
    return pd.Series(np.random.default_rng(seed).normal(0, 0.02, len(index)), index=index, name="label")


def _expected(label: pd.Series) -> dict:
    return {int(t): float(v) for t, v in zip(_ms(label.index), label.to_numpy())}


def test_event_given_dense_same_tail_label_passes_but_forward_return_contract_would_not():
    label = _dense_label()
    out = validate_consumed_label(
        _features(), label, label_kind=LABEL_KIND_EVENT_GIVEN, expected_values=_expected(label)
    )
    assert out["label_kind"] == "event_given" and out["checked_samples"] == N
    # 對照：同一條密集 label（tail_nans=0）若套 forward_return 尾端契約會被誤判——這就是為何要分派
    with pytest.raises(AlignmentViolationError, match="trailing NaN count must equal lag"):
        validate_alignment(
            _features(), label,
            AlignmentSpec(feature_ts_col="timestamp", target_ts_col="timestamp", lag=2, freq=pd.Timedelta("12h")),
        )


def test_event_label_misaligned_index_still_raises():
    label = _dense_label()
    shifted_index = IDX + pd.Timedelta("12h")
    misaligned = pd.Series(label.to_numpy(), index=shifted_index, name="label")
    with pytest.raises(AlignmentViolationError, match="timestamps must match exactly"):
        validate_event_given(_features(), misaligned, expected_values=_expected(label))


def test_event_values_shifted_by_one_row_raise():
    """整批平移一格：timestamp 都在、值都有限、index 也對——舊三檢查全過，只有逐筆值比對抓得到。"""
    label = _dense_label()
    rotated = pd.Series(np.roll(label.to_numpy(), 1), index=IDX, name="label")
    with pytest.raises(AlignmentViolationError, match="consumed label mismatches producer value"):
        validate_event_given(_features(), rotated, expected_values=_expected(label))


def test_event_missing_timestamp_and_nonfinite_keep_loud_messages():
    label = _dense_label()
    exp = _expected(label)
    exp_missing = dict(list(exp.items())[:-1])
    with pytest.raises(AlignmentViolationError, match="event_label_values missing"):
        validate_event_given(_features(), label, expected_values=exp_missing)
    bad = label.copy()
    bad.iloc[3] = np.inf
    exp_bad = _expected(bad)
    with pytest.raises(AlignmentViolationError, match="non-finite"):
        validate_event_given(_features(), bad, expected_values=exp_bad)


def test_event_owner_binding_one_event_per_row():
    label = _dense_label()
    exp = _expected(label)
    owners = {int(t): f"ev{i:03d}" for i, t in enumerate(_ms(IDX))}
    out = validate_event_given(_features(), label, expected_values=exp, event_owners=owners)
    assert out["consumed_event_labels"] == {owners[int(t)]: float(v) for t, v in zip(_ms(IDX), label)}
    missing_owner = dict(owners)
    missing_owner.pop(int(_ms(IDX)[5]))
    with pytest.raises(AlignmentViolationError, match="no event_id bound"):
        validate_event_given(_features(), label, expected_values=exp, event_owners=missing_owner)
    dup = dict(owners)
    dup[int(_ms(IDX)[6])] = dup[int(_ms(IDX)[5])]
    with pytest.raises(AlignmentViolationError, match="more than one consumed row"):
        validate_event_given(_features(), label, expected_values=exp, event_owners=dup)


def test_label_kind_missing_source_raises_and_unknown_raises():
    with pytest.raises(AlignmentViolationError, match="label_source missing"):
        derive_label_kind(None)
    with pytest.raises(AlignmentViolationError, match="unknown label_source"):
        derive_label_kind("something_else")
    assert derive_label_kind("event_label_value") == LABEL_KIND_EVENT_GIVEN
    assert derive_label_kind("mainline_return_N") == LABEL_KIND_FORWARD_RETURN
    label = _dense_label()
    with pytest.raises(AlignmentViolationError, match="requires the producer's expected_values"):
        validate_consumed_label(_features(), label, label_kind=LABEL_KIND_EVENT_GIVEN)
    with pytest.raises(AlignmentViolationError, match="unknown label_kind"):
        validate_consumed_label(_features(), label, label_kind="forged", expected_values=_expected(label))


def test_forward_return_restriction_must_preserve_values():
    source = _dense_label()
    source.iloc[-2:] = np.nan  # 來源已過 validate_alignment（含尾端 NaN）
    rows = IDX[[1, 5, 9, 38, 39]]
    subset = source.loc[rows]
    out = validate_consumed_label(
        _features(rows), subset, label_kind=LABEL_KIND_FORWARD_RETURN, source_series=source
    )
    assert out == {"label_kind": "forward_return", "checked_samples": 5}
    tampered = subset.copy()
    tampered.iloc[1] += 1e-3
    with pytest.raises(AlignmentViolationError, match="value-preserving restriction"):
        validate_consumed_label(_features(rows), tampered, label_kind=LABEL_KIND_FORWARD_RETURN, source_series=source)
    foreign = pd.Series(subset.to_numpy(), index=rows + pd.Timedelta("1h"))
    with pytest.raises(AlignmentViolationError, match="not a subset of the validated source"):
        validate_consumed_label(_features(foreign.index), foreign, label_kind=LABEL_KIND_FORWARD_RETURN, source_series=source)
    with pytest.raises(AlignmentViolationError, match="requires the validated source_series"):
        validate_consumed_label(_features(rows), subset, label_kind=LABEL_KIND_FORWARD_RETURN)


def _report(consumed: dict, label_source: str = "event_label_value") -> dict:
    return {"metadata": {"nested": {"event_filter": {"label_source": label_source, "consumed_event_labels": consumed}}}}


def test_service_triple_bound_rotated_labels_raise():
    by_id = {"ev0": 0.1, "ev1": 0.2, "ev2": 0.3}
    staged = {"event_label_by_id": by_id}
    assert _assert_event_triple_bound(staged, _report(dict(by_id))) is None
    rotated = dict(zip(by_id, np.roll(list(by_id.values()), 1)))
    with pytest.raises(ValueError, match="consumed label .* != produced label"):
        _assert_event_triple_bound(staged, _report(rotated))
    with pytest.raises(ValueError, match="was not produced by this event batch"):
        _assert_event_triple_bound(staged, _report({"ev9": 0.1}))
    with pytest.raises(ValueError, match="lacks consumed_event_labels"):
        _assert_event_triple_bound(staged, _report({}))
    with pytest.raises(ValueError, match="lacks metadata.event_filter"):
        _assert_event_triple_bound(staged, {"metadata": {}})
    # 事件不足 fallback：沒有被消費之事件 label，已由 conditional_ic_abandoned loud 揭露 ⇒ 不重判
    assert _assert_event_triple_bound(staged, _report({}, label_source="mainline_return_N")) is None


def test_e2e_event_path_reports_event_given_kind_and_consumed_labels():
    """真實 la0 fixture：事件 label 覆寫後之序列被驗、報告帶 label_kind 與 {event_id: label}。"""
    from tests.momentum.helpers.ichc_run import feature_index, run_analyze

    idx = feature_index(80)
    rng = np.random.default_rng(20260908)
    lv = {int(t.value // 10**6): float(v) for t, v in zip(idx, rng.normal(0, 0.02, len(idx)))}
    owners = {t: f"ev{i:03d}" for i, t in enumerate(lv)}
    ctx = {  # survivor v2 六鍵（conditional_ic run 之 build_survivor_output 對此 fail-closed）
        "event_manifest_hash": "1" * 64, "label_definition_hash": "2" * 64,
        "decision_time_rule": "t0_open_minus_k_bars", "feature_cutoff_rule": "max_close_ms_le_decision_at",
        "label_window_rule": "close_to_close:horizon_bars=2", "control_kind": "user_labeled_same_trigger",
    }
    report = run_analyze(
        {"event_filter": {"enabled": True, "min_events": 30}},
        event_timestamps=list(lv), event_label_values=lv, event_label_owners=owners, event_context=ctx,
    )
    ef = report["metadata"]["event_filter"]
    assert ef["label_source"] == "event_label_value" and ef["label_kind"] == "event_given"
    consumed = ef["consumed_event_labels"]
    assert ef["consumed_event_count"] == len(consumed) > 0
    assert all(consumed[owners[t]] == lv[t] for t in lv if owners[t] in consumed)
    # service 端最後一腿：回綁產生者之逐事件 label
    _assert_event_triple_bound({"event_label_by_id": {owners[t]: lv[t] for t in lv}}, report)


# ───────────── R3 D5 閉合：鷹架違規延後裁定（三家一致 CODEX/COMPOSER/GROK-R3-P1-01）─────────────

_BASE_S, _STEP_S, _N_FEAT, _N_CLOSE = 1_704_067_200, 43_200, 157, 200
_GAP = range(60, 72)  # close 中段缺 12 根 ⇒ 鷹架覆蓋率紅（grok R3 反例形態）
_META = {"symbol": "BTCUSDT", "timeframe": "12h", "f1": {"name": "f1", "category": "trend", "layer": 1}}


class _GapReader:
    def read_klines(self, _s, _t):
        keep = [i for i in range(_N_CLOSE) if i not in _GAP]
        idx = pd.Index(_BASE_S + np.asarray(keep, dtype=np.int64) * _STEP_S, name="timestamp")
        return pd.DataFrame({"close": np.linspace(100.0, 200.0, _N_CLOSE)[keep]}, index=idx)


def _feat_df() -> pd.DataFrame:
    idx = pd.Index(_BASE_S + np.arange(_N_FEAT, dtype=np.int64) * _STEP_S, name="timestamp")
    return pd.DataFrame({"f1": np.arange(_N_FEAT, dtype=np.float64)}, index=idx)


def _config(event_enabled: bool, min_events: int):
    from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config

    data = load_ic_config().model_dump()
    data["event_filter"] = {**data.get("event_filter", {}), "enabled": event_enabled, "min_events": min_events}
    return ICConfig.model_validate(data)


def _scaffold_with_deferred_violation(config):
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    o = ICFilterOrchestrator(config)
    features = _feat_df()
    label, _ = o._stage2_label_generation(None, _META, config, _GapReader(), features_df=features, defer_alignment_error=True)
    assert o._deferred_scaffold_violation is not None and "coverage too low" in str(o._deferred_scaffold_violation)
    return o, features, label


def _event_inputs(features: pd.DataFrame, rows=range(100, 130)) -> tuple[list, dict]:
    ms = (pd.to_datetime(features.index, unit="s").asi8[list(rows)] // 10**6).astype("int64")
    return [int(t) for t in ms], {int(t): float(0.01 * (i + 1)) for i, t in enumerate(ms)}


def test_scaffold_violation_is_immediate_without_defer_flag():
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    config = _config(False, 1)
    with pytest.raises(AlignmentViolationError, match="coverage too low"):
        ICFilterOrchestrator(config)._stage2_label_generation(None, _META, config, _GapReader(), features_df=_feat_df())


def test_scaffold_violation_deferred_when_overridden_by_event_labels():
    """鷹架紅（K 線缺口）但事件 label 合法 ⇒ 不擋；info 揭露延後訊息；被消費的那條以 event_given 驗。"""
    config = _config(True, 5)
    o, features, label = _scaffold_with_deferred_violation(config)
    ts, lv = _event_inputs(features)
    f_out, l_out, info = o._stage3_event_filter(
        features, label, _META, config, _GapReader(), event_timestamps=ts, event_label_values=lv
    )
    assert info["label_source"] == "event_label_value" and info["label_kind"] == "event_given"
    assert "coverage too low" in info["scaffold_alignment_deferred"]
    assert len(l_out) == len(ts) and np.array_equal(l_out.to_numpy(), np.asarray([lv[t] for t in sorted(lv)]))
    assert o._deferred_scaffold_violation is None


def test_scaffold_violation_reraised_when_consumed():
    """鷹架未被覆寫（filter 未啟用／事件不足 fallback）⇒ 它就是最終 label ⇒ 原樣 raise，不因事件模式放行。"""
    # ① filter 未啟用
    config = _config(False, 5)
    o, features, label = _scaffold_with_deferred_violation(config)
    ts, lv = _event_inputs(features)
    with pytest.raises(AlignmentViolationError, match="coverage too low"):
        o._stage3_event_filter(features, label, _META, config, _GapReader(), event_timestamps=ts, event_label_values=lv)
    # ② 事件不足 ⇒ mainline_return_N fallback 消費鷹架
    config = _config(True, 1000)
    o, features, label = _scaffold_with_deferred_violation(config)
    with pytest.raises(AlignmentViolationError, match="coverage too low"):
        o._stage3_event_filter(features, label, _META, config, _GapReader(), event_timestamps=ts, event_label_values=lv)
