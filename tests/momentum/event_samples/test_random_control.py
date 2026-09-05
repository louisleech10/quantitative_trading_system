"""GAP-3 `G3-D2` D5.2 — `sample_random_bars` 之驗收（`D-001` D5.2 (i)–(vii)）。

資料一律真實 kline（`data_cache/feature_klines/kline_cache.h5`），禁合成 bar。
"""

from __future__ import annotations

import numpy as np
import pytest

from momentum.Analysis.event_samples import all_bars_eval as _ab
from momentum.Analysis.event_samples import random_control as rc
from momentum.Analysis.event_samples.import_contract import (
    ContractValidationError,
    validate_event_import,
)
from momentum.Analysis.event_samples.random_control import (
    RandomControlError,
    _allocate,
    sample_random_bars,
)
from tests.momentum.event_samples.helpers import load_bars

SYMBOL = "ETHUSDT"
TF = "12h"
HORIZON = 2


@pytest.fixture(scope="module")
def bars():
    return load_bars(SYMBOL, (TF,))


def _cols(bars):
    df = bars[SYMBOL][TF]
    return df["open_time_ms"].to_numpy(), df["close_time_ms"].to_numpy()


def _triggers(bars, idxs=(200, 400, 700), horizon: int = HORIZON):
    ot, ct = _cols(bars)
    return [
        {"event_id": f"t{n}", "symbol": SYMBOL, "timeframe": TF,
         "t0_ms": int(ot[i]), "label_end_ms": int(ct[i + horizon])}
        for n, i in enumerate(idxs)
    ]


def _spec(bars, *, lo=100, hi=900, seed=20260905, n_requested=40,
          neighborhood=2, embargo=6, threshold=0.02, horizon=HORIZON, direction="long"):
    ot, _ = _cols(bars)
    return {
        "universe": {"symbol": SYMBOL, "timeframe": TF,
                     "start_ms": int(ot[lo]), "end_ms": int(ot[hi])},
        "strata": {"symbol": SYMBOL, "timeframe": TF,
                   "period": {"start_ms": int(ot[lo]), "end_ms": int(ot[hi])},
                   "direction": direction},
        "allocation": "proportional_to_candidates",
        "exclusion": {"trigger_ids_digest": "", "neighborhood_bars": neighborhood,
                      "embargo_bars": embargo},
        "label_rule": {"threshold": threshold, "horizon_bars": horizon},
        "seed": seed,
        "n_requested": n_requested,
        "replacement": False,
    }


# ── (i) 同 seed 同 universe ⇒ sample_ids_digest 相等 ───────────────────────

def test_i_same_seed_same_digest(bars):
    a = sample_random_bars(bars, _spec(bars), _triggers(bars), scenario="C")[1]
    b = sample_random_bars(bars, _spec(bars), _triggers(bars), scenario="C")[1]
    assert a["sample_ids_digest"] == b["sample_ids_digest"]
    assert a["n_drawn"] == b["n_drawn"] > 0          # 正向對照：不是「兩邊都空所以相等」


# ── (ii) 改 seed ⇒ 必不等 ─────────────────────────────────────────────────

def test_ii_seed_changed_digest_differs(bars):
    a = sample_random_bars(bars, _spec(bars, seed=1), _triggers(bars), scenario="C")[1]
    b = sample_random_bars(bars, _spec(bars, seed=2), _triggers(bars), scenario="C")[1]
    assert a["sample_ids_digest"] != b["sample_ids_digest"]


# ── (iii) 抽中 bar 對每個觸發事件皆在排除區間外 ────────────────────────────

def test_iii_drawn_bars_outside_every_exclusion_window(bars):
    ot, ct = _cols(bars)
    trig = _triggers(bars)
    spec = _spec(bars)
    recs, receipt = sample_random_bars(bars, spec, trig, scenario="C")
    assert recs, "候選非空時應抽得到（否則本條為空迴圈假綠）"
    idx_of = {int(t): i for i, t in enumerate(ot)}
    n = int(spec["exclusion"]["neighborhood_bars"])
    e = int(spec["exclusion"]["embargo_bars"])
    for r in recs:
        i = idx_of[int(r["t0"])]
        for t in trig:
            t0_idx = idx_of[int(t["t0_ms"])]
            end_idx = int(np.searchsorted(ct, int(t["label_end_ms"])))
            assert i < t0_idx - n or i > end_idx + e, (
                f"抽中 index {i} 落在觸發 {t['event_id']} 之 [{t0_idx - n}, {end_idx + e}] 內")
    assert receipt["candidate_count"] > receipt["n_drawn"]


def test_iii_counterexample_zero_neighborhood_still_excludes_post_window(bars):
    """反例（`D-001` D5.2 (iii) 逐字）：`neighborhood=0, embargo=6` 時，
    某觸發之**前一根**若同時落在**另一個**觸發之後鄰域內，仍不得被抽中。

    🔴 這條擋的是「只算自己那一段」的實作——那種寫法在單一觸發下全綠。
    """
    ot, ct = _cols(bars)
    # 兩個相鄰觸發：後者之 t0 前一根落在前者之 label_end+embargo 內。
    i1, i2 = 300, 304
    trig = [
        {"event_id": "a", "symbol": SYMBOL, "timeframe": TF,
         "t0_ms": int(ot[i1]), "label_end_ms": int(ct[i1 + HORIZON])},
        {"event_id": "b", "symbol": SYMBOL, "timeframe": TF,
         "t0_ms": int(ot[i2]), "label_end_ms": int(ct[i2 + HORIZON])},
    ]
    # 前置條件斷言：i2-1 確實落在 a 的 [t0, label_end+embargo] 內（否則本條沒覆蓋到）
    assert i1 <= i2 - 1 <= (i1 + HORIZON) + 6
    spec = _spec(bars, lo=250, hi=400, neighborhood=0, embargo=6, n_requested=200)
    recs, _ = sample_random_bars(bars, spec, trig, scenario="C")
    drawn = {int(r["t0"]) for r in recs}
    assert int(ot[i2 - 1]) not in drawn
    assert drawn, "本區間應有候選（正向對照）"


# ── (iv) 分層配額比例 ─────────────────────────────────────────────────────

def test_iv_allocate_pure_function_three_to_one():
    """🔴 比例規則以**純函式**驗（3:1 精確可構造）。

    真實 kline 之逐月候選數不會剛好是 3:1，硬去湊會變成「調參數直到綠」；
    分層配額本身是純函式，直接餵 3:1 是更強的斷言（值精確、可證偽）。
    整合面之不變式由下一條在真實資料上守。
    """
    # n_target == total ⇒ 全取（3:1 之候選全部入選）
    assert _allocate(40, [("A", 30), ("B", 10)]) == {"A": 30, "B": 10}
    # 3:1 之嚴格比例：20 × 30/40 = 15、20 × 10/40 = 5
    assert _allocate(20, [("A", 30), ("B", 10)]) == {"A": 15, "B": 5}
    # 最大餘數：37 × 30/40 = 27.75 → base 27（frac .75）；37 × 10/40 = 9.25 → base 9（frac .25）
    #   餘 1 給小數大的 A ⇒ 28/9（**禁 round**：round 會給出 28/9 之外的分配且和可能 != 37）
    assert _allocate(37, [("A", 30), ("B", 10)]) == {"A": 28, "B": 9}
    # 同分餘數依 key UTF-8 升冪（決定性）：A 與 B 之小數部分相同，餘額只夠一個時 A 先拿。
    #   total=12、n_target=7 ⇒ C base 5（frac .833）、A/B base 0（frac .583）；餘 2 ⇒ C、再 A。
    assert _allocate(7, [("A", 1), ("B", 1), ("C", 10)]) == {"A": 1, "B": 0, "C": 6}
    #   餘額 2 且 A/B 同分 ⇒ 兩者各拿一個（不是全給 C）
    assert _allocate(10, [("A", 1), ("B", 1), ("C", 10)]) == {"A": 1, "B": 1, "C": 8}
    # 候選總數 ≤ n_target ⇒ 全取，不得超抽（逐層 n_drawn ≤ n_candidates）
    assert _allocate(50, [("A", 3), ("B", 4)]) == {"A": 3, "B": 4}
    # 逐層上界之通則：任何合法輸入下 base ≤ 候選數
    for n in (1, 7, 19, 40):
        got = _allocate(n, [("A", 30), ("B", 10)])
        assert sum(got.values()) == n
        assert got["A"] <= 30 and got["B"] <= 10


def test_iv_per_stratum_invariants_on_real_bars(bars):
    _, receipt = sample_random_bars(bars, _spec(bars), _triggers(bars), scenario="C")
    ps = receipt["per_stratum"]
    assert len(ps) >= 2, "universe 應跨多個自然月（否則分層這件事沒被測到）"
    assert sum(s["n_drawn"] for s in ps) == receipt["n_drawn"] == receipt["n_requested"]
    for s in ps:
        assert 0 <= s["n_drawn"] <= s["n_candidates"]
    assert sum(s["n_candidates"] for s in ps) == receipt["candidate_count"]
    # 最大餘數之保證：每層之 n_drawn 與精確比例相差 < 1
    total = receipt["candidate_count"]
    for s in ps:
        exact = receipt["n_drawn"] * s["n_candidates"] / total
        assert abs(s["n_drawn"] - exact) < 1.0, f"{s['key']}：{s['n_drawn']} vs 精確 {exact}"


# ── (v) period 無交集 ⇒ random_control_period_mismatch ────────────────────

def test_v_period_disjoint_raises(bars):
    ot, _ = _cols(bars)
    spec = _spec(bars)
    spec["strata"]["period"] = {"start_ms": int(ot[1000]), "end_ms": int(ot[1200])}
    with pytest.raises(RandomControlError) as ei:
        sample_random_bars(bars, spec, _triggers(bars), scenario="C")
    assert ei.value.reason == "random_control_period_mismatch"


# ── (vi) 產出全過同一 validator（無 profile 分裂） ─────────────────────────

def test_vi_records_pass_same_validator(bars):
    recs, receipt = sample_random_bars(bars, _spec(bars), _triggers(bars), scenario="C")
    df = validate_event_import(recs, random_control_spec=receipt)
    assert len(df) == len(recs) == receipt["n_drawn"]
    assert {r["control_kind"] for r in recs} == {"platform_random_bars"}
    assert {r["label_origin"] for r in recs} == {"platform_random"}
    assert {r["label_definition"]["label_return_mode"] for r in recs} == {"close_to_close"}
    assert {r["label_definition"]["rule_id"] for r in recs} == {"random_control:label_rule"}

    # 🔴 過的是**同一支**：把 spec 拿掉就該被同一支 validator 擋（證明不是繞過）
    with pytest.raises(ContractValidationError):
        validate_event_import(recs)


# ── (vii) mutation：改 embargo_bars ⇒ digest 必變 ─────────────────────────

def test_vii_embargo_changed_digest_differs(bars):
    a = sample_random_bars(bars, _spec(bars, embargo=6), _triggers(bars), scenario="C")[1]
    b = sample_random_bars(bars, _spec(bars, embargo=30), _triggers(bars), scenario="C")[1]
    assert a["sample_ids_digest"] != b["sample_ids_digest"]


def test_vii_neighborhood_changed_digest_differs(bars):
    a = sample_random_bars(bars, _spec(bars, neighborhood=0), _triggers(bars), scenario="C")[1]
    b = sample_random_bars(bars, _spec(bars, neighborhood=25), _triggers(bars), scenario="C")[1]
    assert a["sample_ids_digest"] != b["sample_ids_digest"]


# ── label 路徑：唯一 producer，且 horizon 改變會改 label ───────────────────

def test_label_path_is_label_from_rule_only(bars, monkeypatch):
    """🔴 執行期事實：label 必須真的經 `_label_from_rule`，且**不得**呼叫 `evaluate_condition`。

    只驗「值看起來合理」對「另寫一份等價公式」這種壞法會綠——那正是 D-001
    要求「唯一標籤路徑」的原因（兩份實作必然漂移）。
    """
    calls = []
    real = _ab._label_from_rule

    def spy(sign, close, i, horizon, threshold):
        calls.append((sign, i, horizon, threshold))
        return real(sign, close, i, horizon, threshold)

    monkeypatch.setattr(_ab, "_label_from_rule", spy)
    recs, _ = sample_random_bars(bars, _spec(bars), _triggers(bars), scenario="C")
    assert len(calls) == len(recs) > 0
    assert {c[2] for c in calls} == {HORIZON}
    assert {c[3] for c in calls} == {0.02}
    assert {c[0] for c in calls} == {1.0}          # long ⇒ +1
    # 🔴 「不呼叫條件引擎」以 **AST** 判定，不用 grep：模組 docstring 就寫著
    #    `evaluate_condition` 這個字（在解釋為什麼不呼叫），字串比對會打到自己的說明文字
    #    ——那種測試是「改壞也不會紅、寫對反而紅」的反向假綠。
    import ast

    tree = ast.parse(open(rc.__file__, encoding="utf-8").read())
    called = {
        n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", None)
        for n in ast.walk(tree) if isinstance(n, ast.Call)
    }
    assert "evaluate_condition" not in called
    imported = {
        alias.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for alias in n.names
    } | {
        alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names
    } | {
        n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not any("condition" in str(name) for name in imported), f"不得 import 條件引擎：{imported}"
    # 正向對照：AST 真的抓得到呼叫（否則上面兩條可能只是解析失敗後的空集合）
    assert "_label_from_rule" in called


def test_horizon_change_changes_labels(bars):
    a = sample_random_bars(bars, _spec(bars, horizon=2), _triggers(bars), scenario="C")[0]
    b = sample_random_bars(bars, _spec(bars, horizon=8), _triggers(bars), scenario="C")[0]
    la = {r["event_id"]: r["label"] for r in a}
    lb = {r["event_id"]: r["label"] for r in b}
    shared = set(la) & set(lb)
    assert shared, "兩次抽樣應有共同 event（否則本條比不到 label）"
    assert any(la[e] != lb[e] for e in shared), "改 horizon_bars 應改變 label 集合"


def test_short_direction_flips_sign(bars):
    long_recs = sample_random_bars(bars, _spec(bars), _triggers(bars), scenario="C")[0]
    short_recs = sample_random_bars(
        bars, _spec(bars, direction="short"), _triggers(bars), scenario="C")[0]
    lv = {r["event_id"]: r["label_value"] for r in long_recs}
    sv = {r["event_id"]: r["label_value"] for r in short_recs}
    shared = [e for e in set(lv) & set(sv) if abs(lv[e]) > 1e-12]
    assert shared
    for e in shared:
        assert lv[e] == pytest.approx(-sv[e])


# ── label_rule 之 fail-closed ─────────────────────────────────────────────

def test_label_rule_missing_reason(bars):
    spec = _spec(bars)
    del spec["label_rule"]
    with pytest.raises(RandomControlError) as ei:
        sample_random_bars(bars, spec, _triggers(bars), scenario="C")
    assert ei.value.reason == "random_control_label_rule_missing"


def test_label_rule_param_conflicting_with_spec_is_rejected(bars):
    """參數與 spec 兩份 `label_rule` 不一致 ⇒ 拒（不設優先序）。"""
    with pytest.raises(RandomControlError) as ei:
        sample_random_bars(bars, _spec(bars), _triggers(bars),
                           {"threshold": 0.09, "horizon_bars": 2}, scenario="C")
    assert ei.value.reason == "random_control_label_rule_missing"


@pytest.mark.parametrize(
    "bad",
    [{"threshold": 0, "horizon_bars": 2},         # int 冒充 float
     {"threshold": 0.02, "horizon_bars": 0},      # 零長答案窗
     {"threshold": 0.02}],                        # 缺葉
    ids=["int_threshold", "zero_horizon", "missing_leaf"],
)
def test_label_rule_shape_fail_closed(bars, bad):
    spec = _spec(bars)
    spec["label_rule"] = bad
    with pytest.raises(RandomControlError) as ei:
        sample_random_bars(bars, spec, _triggers(bars), scenario="C")
    assert ei.value.reason == "random_control_label_rule_missing"


# ── 邊界：候選 0 ／跨 symbol ／缺鍵 ────────────────────────────────────────

def test_zero_candidates_yields_empty_batch(bars):
    """候選 0（universe 完全被排除區間覆蓋）⇒ 抽 0 筆，不炸、不補。"""
    ot, ct = _cols(bars)
    trig = [{"event_id": "a", "symbol": SYMBOL, "timeframe": TF,
             "t0_ms": int(ot[300]), "label_end_ms": int(ct[302])}]
    spec = _spec(bars, lo=299, hi=303, neighborhood=5, embargo=5, n_requested=10)
    recs, receipt = sample_random_bars(bars, spec, trig, scenario="C")
    assert recs == [] and receipt["n_drawn"] == 0 and receipt["candidate_count"] == 0
    assert receipt["per_stratum"] == []


def test_cross_symbol_universe_rejected(bars):
    trig = _triggers(bars)
    trig[0]["symbol"] = "BTCUSDT"
    with pytest.raises(RandomControlError) as ei:
        sample_random_bars(bars, _spec(bars), trig, scenario="C")
    assert ei.value.reason == "random_control_period_mismatch"


def test_trigger_receipt_missing_key_rejected(bars):
    trig = _triggers(bars)
    del trig[1]["label_end_ms"]
    with pytest.raises(RandomControlError) as ei:
        sample_random_bars(bars, _spec(bars), trig, scenario="C")
    assert ei.value.reason == "random_control_period_mismatch"


def test_receipt_shape_matches_contract_schema(bars):
    """receipt 之鍵集恰為契約 `random_control_spec.fields`（多一鍵少一鍵皆紅）。"""
    from momentum.Analysis.event_samples.import_contract import load_event_import_contract

    _, receipt = sample_random_bars(bars, _spec(bars), _triggers(bars), scenario="C")
    declared = load_event_import_contract()["receipt_schema"]["batch"]["random_control_spec"]["fields"]
    assert set(receipt) == set(declared)
    assert receipt["generator_version"] == rc.GENERATOR_VERSION
    assert receipt["allocation"] == "proportional_to_candidates"
    assert receipt["replacement"] is False


def test_scenario_is_keyword_only_without_default():
    """`scenario` 無預設 ⇒ 呼叫端必須顯式給（猜一個會讓對照批走不同去重 policy）。"""
    import inspect

    p = inspect.signature(sample_random_bars).parameters["scenario"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


# ── D5.4 golden：抽樣決定性之外部凍結 ───────────────────────────────────────

def _golden_paths():
    from pathlib import Path
    root = Path(__file__).resolve().parents[3] / "tests" / "golden" / "gap3_random_control"
    return sorted(root.glob("*.json"))


def test_d54_golden_files_registered_and_nonempty():
    """凍結檔存在且與登記處同集合（防「golden 目錄空著也算過」）。"""
    from tests.golden.gap3_random_control import cases as reg

    names = {p.name for p in _golden_paths()}
    assert names == {str(c["file_name"]) for c in reg.CASES}
    assert len(names) >= 2, "至少兩個 seed（單一 seed 證明不了決定性以外的事）"


@pytest.mark.parametrize("path", _golden_paths(), ids=lambda p: p.name)
def test_d54_golden_check_passes(bars, path):
    """`--check` 之逐案比對：重跑抽樣須逐項等於凍結值。"""
    from tests.golden.gap3_random_control.loader import check_golden, load_golden

    case = load_golden(path)
    report = check_golden(case, bars)
    assert report.ok, report.diffs
    assert case.n_drawn > 0 and case.labels, "正向對照：凍結檔非空"
    assert len(case.per_stratum) >= 2, "universe 應跨月分層（D-001 D5.4 邊界）"


@pytest.mark.parametrize(
    ("field", "mutate"),
    [
        ("neighborhood_bars", lambda s: s["exclusion"].__setitem__("neighborhood_bars", 40)),
        ("embargo_bars", lambda s: s["exclusion"].__setitem__("embargo_bars", 60)),
        ("seed", lambda s: s.__setitem__("seed", 123456)),
        ("horizon_bars", lambda s: s["label_rule"].__setitem__("horizon_bars", 9)),
    ],
    ids=["neighborhood", "embargo", "seed", "horizon"],
)
def test_d54_golden_negative_mutations_are_detected(bars, field, mutate):
    """mutation：改任一抽樣輸入 ⇒ `check_golden` **必紅**（否則 golden 只是裝飾）。"""
    from dataclasses import replace

    from tests.golden.gap3_random_control.loader import check_golden, load_golden

    case = load_golden(_golden_paths()[0])
    spec = {k: (dict(v) if isinstance(v, dict) else v) for k, v in dict(case.spec).items()}
    mutate(spec)
    mutated = replace(case, spec=spec)
    report = check_golden(mutated, bars)
    assert not report.ok, f"改 {field} 之後 golden 竟仍通過（比對沒有真的在比）"


def test_d54_golden_period_mismatch_raises(bars):
    """period 錯位 ⇒ 產生器 raise（loader 讓它穿透為紅，不吞成 diff）。"""
    from dataclasses import replace

    from tests.golden.gap3_random_control.loader import check_golden, load_golden

    ot, _ = _cols(bars)
    case = load_golden(_golden_paths()[0])
    spec = {k: (dict(v) if isinstance(v, dict) else v) for k, v in dict(case.spec).items()}
    spec["strata"] = {**spec["strata"], "period": {"start_ms": int(ot[1200]), "end_ms": int(ot[1400])}}
    with pytest.raises(RandomControlError) as ei:
        check_golden(replace(case, spec=spec), bars)
    assert ei.value.reason == "random_control_period_mismatch"


def test_d54_golden_loader_fail_closed_on_missing_key(tmp_path):
    """缺必要鍵 ⇒ loader raise（不補預設、不靜默跳過）。"""
    import json as _json

    from tests.golden.gap3_random_control.loader import GoldenError, load_golden

    raw = _json.loads(_golden_paths()[0].read_text(encoding="utf-8"))
    del raw["sample_ids_digest"]
    p = tmp_path / "broken.json"
    p.write_text(_json.dumps(raw), encoding="utf-8")
    with pytest.raises(GoldenError):
        load_golden(p)
