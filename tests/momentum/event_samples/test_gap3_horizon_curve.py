"""GAP-3 UX Task 4.2 驗證（-k horizon_curve）：事件後報酬表之 horizon 集合由**呼叫端**決定。

TODO Task 4.2：
- 邊界①：列數 `== len(horizons)`。
- 「只改要算哪些 horizon；**不改**每個 horizon 之計算式。」
- 「不可做：**不得因列數變多而改變 `n_eff` 之定義**。」

🔴 本檔刻意用「同一批事件、兩組不同 horizons」對比，而不是只驗一組的列數——
只驗一組的話，把計算式改壞、或把 `n_effective` 改成隨列數變動，本檔照樣綠。
"""

from __future__ import annotations

import numpy as np
import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.tables import event_forward_return_table
from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig, EventSplitConfig
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def _pipeline(bars, idxs, labels):
    events = [make_event(i, t0=BASE + n * H12, label=labels[i]) for i, n in enumerate(idxs)]
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    man = build_event_manifest(rec, DedupePolicyConfig(scenario="C"), events=df)
    plan = split_events(man, EventSplitConfig(test_fraction=0.4, tier_min_test_events=0))
    return rec, man, plan


def _table(bars, man, rec, plan, horizons):
    return event_forward_return_table(
        man, rec, bars, plan, {"horizons": list(horizons), "seed": 1, "n_boot": 50}
    )


def test_gap3_horizon_curve_row_count_equals_len_horizons(bars):
    """邊界①：三個不同大小的 horizon 集合 ⇒ 每個表之列數各自 `== len(horizons)`。

    🔴 三組而非一組：單組通過不了「列數其實寫死」這個反例。
    """
    rec, man, plan = _pipeline(bars, [300, 600, 900], [1, 0, 1])
    for horizons in ([1, 2, 4], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [3]):
        rep = _table(bars, man, rec, plan, horizons)
        assert rep["horizons"] == list(horizons)
        assert len(rep["sensitivity_micro"]) == len(horizons)
        assert len(rep["uniqueness_weighted"]) == len(horizons)
        assert sorted(int(k) for k in rep["sensitivity_micro"]) == sorted(horizons)


def test_gap3_horizon_curve_per_horizon_values_do_not_depend_on_the_set(bars):
    """「只改要算哪些 horizon；**不改**每個 horizon 之計算式」。

    同一個 h 在「短集合」與「完整曲線」裡算出來的每一個統計量須**逐值相等**
    ——若某天有人把計算式改成依賴集合（例如跨 h 正規化），本條會紅。
    """
    rec, man, plan = _pipeline(bars, [300, 600, 900], [1, 0, 1])
    short = _table(bars, man, rec, plan, [1, 2, 4])
    full = _table(bars, man, rec, plan, list(range(1, 13)))

    for h in ("1", "2", "4"):
        for block in ("sensitivity_micro", "uniqueness_weighted"):
            a, b = short[block][h], full[block][h]
            assert set(a) == set(b), f"{block}[{h}] 之鍵集隨 horizon 集合改變"
            for key in a:
                if isinstance(a[key], (int, float)) and not isinstance(a[key], bool):
                    if np.isnan(float(a[key])):
                        assert np.isnan(float(b[key])), f"{block}[{h}].{key} NaN 狀態不一致"
                    else:
                        assert float(a[key]) == pytest.approx(float(b[key]), abs=1e-12), \
                            f"{block}[{h}].{key} 隨 horizon 集合改變"
                else:
                    assert a[key] == b[key], f"{block}[{h}].{key} 隨 horizon 集合改變"


def test_gap3_horizon_curve_n_eff_definition_is_not_row_count(bars):
    """**不可做**：不得因列數變多而改變 `n_eff` 之定義。

    `n_effective` 是**權重和**（事件唯一性），與「算了幾個 horizon」無關。
    本條同時釘住兩件事：①同一 h 之 `n_effective` 不隨集合大小變 ②它不等於列數
    （否則「把 n_eff 改成 len(horizons)」這種改壞法會躲過上一條的逐值比對嗎？不會，
    但這條讓失效模式的名字直接寫在測試名上，日後讀 receipt 的人不必反推）。
    """
    rec, man, plan = _pipeline(bars, [300, 600, 900], [1, 0, 1])
    short = _table(bars, man, rec, plan, [1, 2, 4])
    full = _table(bars, man, rec, plan, list(range(1, 13)))

    for h in ("1", "2", "4"):
        n_eff_short = float(short["uniqueness_weighted"][h]["n_effective"])
        n_eff_full = float(full["uniqueness_weighted"][h]["n_effective"])
        assert n_eff_short == pytest.approx(n_eff_full, abs=1e-12), "n_effective 隨 horizon 集合改變"
        assert n_eff_short != pytest.approx(float(len(full["horizons"])), abs=1e-12) or n_eff_short == pytest.approx(
            float(len(short["horizons"])), abs=1e-12
        ), "n_effective 疑似退化成列數"
        # 前置：這批確實有事件，否則上面的比較會退化成 0 == 0
        assert short["sensitivity_micro"][h]["n"] > 0


def test_gap3_horizon_curve_rejects_empty_and_nonpositive_and_duplicate(bars):
    """呼叫端傳進來的集合仍受既有 fail-closed 守衛約束（S-9 ⑦ 之重複 h 亦然）。"""
    rec, man, plan = _pipeline(bars, [300, 600], [1, 0])
    for bad in ([], [0], [-1], [1, 0, 2]):
        with pytest.raises(ValueError):
            _table(bars, man, rec, plan, bad)
    with pytest.raises(ValueError):
        _table(bars, man, rec, plan, [1, 3, 3, 7])
