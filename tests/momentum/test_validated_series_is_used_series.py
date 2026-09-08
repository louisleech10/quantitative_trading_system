"""EVTALIGN Task 2.2：跨模式不變式——被驗的 series ＝ 被 IC 消費的 series。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 2.2　TODO：Task 2.2

使用者的擔心（「除了事件模式，其他模式也不能被這種鷹架…影響專案名譽」）機械化：
對每個**實際可觸發**的情境（不照後端 enum，那會漏掉事件模式），以 spy 記錄
「最後一次交給驗證契約（`validate_alignment`／`validate_consumed_label`）的 label series」與
「進入 `_stage4_ic_calculation` 的 label series」，斷言兩者 index 相等且逐值相等（NaN 位置亦同）。

- `global_with_labels`：stage0 預載路徑（`_load_labels_hdf5` 以真實 kline 產生之同尾 label 取代）
- `global_without_labels`：stage2 由 kline 生成
- `event`：stage3 以 `event_label_values` 覆寫 ⇒ 最後一次驗證必須是 `event_given`，且消費的是覆寫後那條
- `cross_sectional`：**not_applicable**（`EA-RESID-2`：模組未完工、無守衛）——以「源碼確無守衛呼叫」斷言留痕，
  日後補上守衛時本案例轉紅，提醒把該情境納入不變式。

情境清單為模組級常數 `SCENARIOS`；新增模式未列入 ⇒ `test_scenario_list_is_closed` 紅。
mutation（`--phase 2`）：A6a 在 global 路徑回傳與已驗序列不同的 series ⇒ global 情境紅；
A6b 在 event 覆寫後回傳不同 series ⇒ event 情境紅。
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from tests.momentum.helpers.ichc_run import KLINE_CACHE_DIR, feature_index, fixture_paths, run_analyze

#: 情境清單（模組級常數；新增模式必須加在這裡，否則不變式測試不涵蓋它）
SCENARIOS = ("global_with_labels", "global_without_labels", "event", "cross_sectional")
NOT_APPLICABLE = {
    "cross_sectional": "EA-RESID-2：橫截面路徑（analyze_cross_sectional）未完工、不呼叫任何對齊守衛；"
    "使用者 2026-09-07 裁定「未驗過的模組沒有守衛不是缺陷」。本情境無中間序列可比，標 not_applicable。",
}
CTX = {
    "event_manifest_hash": "1" * 64, "label_definition_hash": "2" * 64,
    "decision_time_rule": "t0_open_minus_k_bars", "feature_cutoff_rule": "max_close_ms_le_decision_at",
    "label_window_rule": "close_to_close:horizon_bars=2", "control_kind": "user_labeled_same_trigger",
}


def _snap(series: pd.Series) -> tuple[pd.Index, np.ndarray]:
    idx = series.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.to_datetime(idx, unit="s")
    return pd.DatetimeIndex(idx), np.asarray(series.to_numpy(dtype="float64"), dtype="float64").copy()


class _Spy:
    """記錄每次驗證的目標序列與每次進 stage4 的序列（時間順序）。"""

    def __init__(self):
        self.validated: list[tuple[str, tuple]] = []
        self.consumed: list[tuple] = []

    def install(self, monkeypatch):
        real_va = orch_mod.validate_alignment
        real_vc = orch_mod.validate_consumed_label
        real_s4 = ICFilterOrchestrator._stage4_ic_calculation
        spy = self

        def va(feature_data, target_data, spec, **kw):
            spy.validated.append(("forward_return", _snap(target_data)))
            return real_va(feature_data, target_data, spec, **kw)

        def vc(feature_data, target_data, **kw):
            out = real_vc(feature_data, target_data, **kw)
            spy.validated.append((str(kw.get("label_kind")), _snap(target_data)))
            return out

        def s4(self_o, features_df, label_series, *args, **kwargs):
            spy.consumed.append(_snap(label_series))
            return real_s4(self_o, features_df, label_series, *args, **kwargs)

        monkeypatch.setattr(orch_mod, "validate_alignment", va)
        monkeypatch.setattr(orch_mod, "validate_consumed_label", vc)
        monkeypatch.setattr(ICFilterOrchestrator, "_stage4_ic_calculation", s4)


def _same(a: tuple, b: tuple) -> bool:
    return a[0].equals(b[0]) and np.array_equal(a[1], b[1], equal_nan=True)


def _coterminal_labels_from_real_kline() -> pd.DataFrame:
    """以生產 label_generator＋真實 kline 產生同尾預載 label（走 stage2 同一條生成路徑）。"""
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    h5, meta_path = fixture_paths()
    o = create_ic_analyzer()
    features, features_meta = o._load_features_hdf5(str(h5))
    meta = o._load_meta_json(str(meta_path)) or features_meta
    reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    _, labels_df = o._stage2_label_generation(None, meta, o._config, reader, features_df=features)
    return labels_df


def _run(scenario: str, monkeypatch) -> None:
    if scenario == "global_without_labels":
        run_analyze(None)
    elif scenario == "global_with_labels":
        labels_df = _coterminal_labels_from_real_kline()
        monkeypatch.setattr(ICFilterOrchestrator, "_load_labels_hdf5", lambda self_o, _p: labels_df.copy())
        run_analyze(None)
    elif scenario == "event":
        idx = feature_index(80)
        rng = np.random.default_rng(20260908)
        lv = {int(t.value // 10**6): float(v) for t, v in zip(idx, rng.normal(0, 0.02, len(idx)))}
        owners = {t: f"ev{i:03d}" for i, t in enumerate(lv)}
        run_analyze({"event_filter": {"enabled": True, "min_events": 30}},
                    event_timestamps=list(lv), event_label_values=lv, event_label_owners=owners, event_context=CTX)
    else:  # pragma: no cover - 由 SCENARIOS 閉合測試保證不會到這
        raise AssertionError(f"未知情境 {scenario}")


def test_scenario_list_is_closed():
    """新增模式須列入 SCENARIOS；橫截面之 not_applicable 理由須具名。"""
    assert set(NOT_APPLICABLE) <= set(SCENARIOS)
    assert len(SCENARIOS) >= 4 and len(set(SCENARIOS)) == len(SCENARIOS)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_validated_series_is_used_series(scenario, monkeypatch):
    if scenario in NOT_APPLICABLE:
        src = inspect.getsource(ICFilterOrchestrator.analyze_cross_sectional)
        assert "validate_alignment" not in src and "validate_consumed_label" not in src, (
            f"{scenario} 出現守衛呼叫——請把該情境從 NOT_APPLICABLE 移除並補進不變式。理由曾為：{NOT_APPLICABLE[scenario]}"
        )
        return  # not_applicable（理由見 NOT_APPLICABLE；非靜默 skip）

    spy = _Spy()
    spy.install(monkeypatch)
    _run(scenario, monkeypatch)

    assert spy.consumed, f"{scenario}：stage4 未被呼叫"
    assert spy.validated, f"{scenario}：沒有任何驗證呼叫——鷹架以外的路徑也必須驗"
    kind, validated = spy.validated[-1]
    consumed = spy.consumed[-1]
    assert _same(validated, consumed), (
        f"{scenario}：最後被驗的 series（{kind}）≠ 進入 IC 的 series——存在「驗 A 用 B」"
    )
    if scenario == "event":
        assert kind == "event_given", f"事件模式最後一次驗證必須是 event_given，得 {kind}"
        # 鷹架（stage2 forward_return）被覆寫丟棄：它**不**等於被消費的那條
        scaffold = [s for k, s in spy.validated if k == "forward_return"]
        assert scaffold and not _same(scaffold[-1], consumed)
    else:
        assert kind == "forward_return"
