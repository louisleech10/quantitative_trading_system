"""Task B4.2 驗證：W8 entry×exit 一致性（D1-6 五種 entry 語意各一真實 kline 手算 exact；exit＝label_end close）；
ASSERT input_metric=auc target=dsr ⇒ MetricTypeError（機械拒）；ledger 空 ⇒ unavailable；n_trials 只從 ledger 讀；
MinBTL 前提不足 ⇒ loud；PBO 聯集觀測軸。帳本導到 tmp（不碰真實 results/）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples import candidate_ledger as cl
from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.candidate_ledger import (
    CandidateReturns, LedgerKey, MetricTypeError, record_candidate, run_dsr_pbo, to_return_series,
)
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.types import AlignmentConfig
from momentum.Analysis.strategy_validation import ledger as ledger_mod
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000
KEY = LedgerKey(research_session_id="gap3-b4-test", dataset_key="ETHUSDT-12h")
LD = {"rule_id": "rule-x", "canonical_digest": "c" * 64, "window": {"horizon_bars": 2}, "label_return_mode": "close_to_close"}


@pytest.fixture(autouse=True)
def _redirect_ledger_root(tmp_path, monkeypatch):
    def _fake_path(*, research_session_id, dataset_key):
        return tmp_path / "strategy_validation" / f"{research_session_id}__{dataset_key}.jsonl"
    monkeypatch.setattr(ledger_mod, "ledger_path", _fake_path)
    return tmp_path


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def _events(semantic, idxs, direction="long", k=0):
    evs = [make_event(i, t0=BASE + x * H12, label=int(i % 2), entry_price_semantic=semantic, direction=direction,
                      decision_offset_bars=k) for i, x in enumerate(idxs)]
    df = validate_event_import(evs)
    rec, fail = align_events(df, load_bars("ETHUSDT", ("12h",)), AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    return df, rec


# ---- W8：五種 entry 語意各一手算 exact；exit＝label_end close ----
@pytest.mark.parametrize("semantic,k", [("trigger_open", 0), ("trigger_close", 0), ("next_open", 0),
                                        ("decision_bar_open", 1), ("decision_bar_close", 1)])
def test_to_return_series_hand_exact_each_entry_semantic(bars, semantic, k):
    idxs = [300, 420, 555]
    df, rec = _events(semantic, idxs, k=k)
    g = bars["ETHUSDT"]["12h"]
    o, c = g["open"].to_numpy(), g["close"].to_numpy()
    sig = pd.Series(True, index=df["event_id"])
    s = to_return_series(sig, {"ETHUSDT": g}, semantic, LD, rec, events=df)
    assert list(s.index) == [f"ev{i}" for i in range(3)]                 # 依 entry_at 排序
    for i, x in enumerate(idxs):
        entry = {"trigger_open": o[x], "trigger_close": c[x], "next_open": o[x + 1],
                 "decision_bar_open": o[x - k], "decision_bar_close": c[x - k]}[semantic]
        exit_ = c[x + 2]                                                   # close_to_close：label_end＝t0+h 根 close
        assert s[f"ev{i}"] == pytest.approx(exit_ / entry - 1.0, abs=1e-15)
    assert s.attrs["t_semantics"] == "trade_level" and s.attrs["span_years"] > 0 and len(s.attrs["source_artifact_hash"]) == 64


def test_to_return_series_short_sign_and_threshold(bars):
    df, rec = _events("trigger_open", [300, 420], direction="short")
    g = bars["ETHUSDT"]["12h"]
    scores = pd.Series([0.9, 0.1], index=df["event_id"])
    s = to_return_series(scores, {"ETHUSDT": g}, "trigger_open", LD, rec, events=df)
    assert list(s.index) == ["ev0"]                                        # 0.1 < 0.5 非訊號
    assert s["ev0"] == pytest.approx(-(g["close"].to_numpy()[302] / g["open"].to_numpy()[300] - 1.0), abs=1e-15)


def test_to_return_series_w8_mismatch_rejected(bars):
    df, rec = _events("trigger_open", [300, 420])
    g = bars["ETHUSDT"]["12h"]
    sig = pd.Series(True, index=df["event_id"])
    with pytest.raises(ValueError, match="entry_semantic"):
        to_return_series(sig, {"ETHUSDT": g}, "next_open", LD, rec, events=df)
    with pytest.raises(ValueError, match="label_definition"):
        to_return_series(sig, {"ETHUSDT": g}, "trigger_open", {**LD, "window": {"horizon_bars": 3}}, rec, events=df)
    with pytest.raises(ValueError):
        to_return_series(sig, {"ETHUSDT": g}, "trigger_open", LD, rec)      # 缺 events context
    with pytest.raises(ValueError, match="無對齊收據"):
        to_return_series(pd.Series(True, index=["ghost"]), {"ETHUSDT": g}, "trigger_open", LD, rec, events=df)


# ---- 合成 candidate return series（事件／報酬序列合成合法，章程 §F）----
def _cand(cid, n=40, mu=0.002, seed=1, span_years=2.0, ids=None, entry_ms=None):
    rng = np.random.default_rng(seed)
    ids = ids or [f"e{i:03d}" for i in range(n)]
    n = len(ids)
    entry_ms = entry_ms or {e: BASE + i * H12 for i, e in enumerate(ids)}
    s = pd.Series(rng.normal(mu, 0.02, n), index=ids, name="hold_return")
    s.attrs.update({"span_years": span_years, "entry_semantic": "trigger_open", "label_definition": LD,
                    "t_semantics": "trade_level", "entry_at_ms_by_event": dict(entry_ms)})
    s.attrs["source_artifact_hash"] = cl.receipt_digest(s)                  # 與 to_return_series 同一收據 digest
    return CandidateReturns(candidate_id=cid, returns=s)


def _meta(cr, **over):
    base = {"candidate_id": cr.candidate_id, "evaluation_id": f"eval-{cr.candidate_id}", "returns": cr,
            "rule_digest": "r" * 64, "seed": 7, "input_digest": "i" * 64, "command": "pytest -k candidate_ledger",
            "expected": "pass", "ts": "2026-08-21T00:00:00Z"}
    base.update(over)
    return base


def test_ledger_empty_unavailable():
    rep = run_dsr_pbo(KEY, {"a": _cand("a")})
    assert rep["capability_status"] == "unavailable" and rep["ledger"]["status"] == "unavailable"
    assert rep["dsr"]["status"] == "unavailable" and rep["pbo"]["status"] == "unavailable"
    assert rep["n_trials_source"] == "ledger"


def test_record_then_n_from_ledger_dsr_pbo_eligibility(_redirect_ledger_root):
    cands = {c: _cand(c, mu=m, seed=i) for i, (c, m) in enumerate([("a", 0.004), ("b", 0.0), ("c", -0.002)])}
    for cr in cands.values():
        record_candidate(KEY, _meta(cr))
    lr = ledger_mod.read_trial_ledger(research_session_id=KEY.research_session_id, dataset_key=KEY.dataset_key)
    assert lr.status == "ok" and lr.n_for_dsr == 3 and len(lr.valid_sharpe_values) == 3
    rep = run_dsr_pbo(KEY, cands, target_sharpe=0.5, s_blocks=4)
    assert rep["capability_status"] == "ok" and rep["champion"] == "a"
    assert rep["dsr"]["n_trials_used"] == 3 and rep["dsr"]["status"] == "ok"   # N 從 ledger（非 request）
    assert rep["dsr"]["variance_source"] == "ledger_cross_trial"
    assert rep["pbo"]["status"] == "ok" and rep["pbo"]["universe_scope"] == "ledger_recorded_only"
    assert rep["pbo"]["n_obs"] == 40 and 0.0 <= rep["pbo"]["value"] <= 1.0
    assert rep["eligibility"]["n_source"] == "ledger" and rep["eligibility"]["trials_used"] == 3
    # provenance sidecar 存在且含 rule_digest／seed／input_digest／expected
    import json
    prov = (_redirect_ledger_root / "strategy_validation" / f"{KEY.research_session_id}__{KEY.dataset_key}.provenance.jsonl").read_text().splitlines()
    assert len(prov) == 3 and all({"rule_digest", "seed", "input_digest", "expected", "command"} <= set(json.loads(p)) for p in prov)


def test_auc_fed_to_dsr_rejected_mechanically():
    """ASSERT：input_metric=auc target=dsr ⇒ rc!=0（MetricTypeError；不靠文件約定）。"""
    auc_like = CandidateReturns(candidate_id="a", returns=pd.Series([0.73], index=["e0"]), metric_kind="auc")
    with pytest.raises(MetricTypeError):
        run_dsr_pbo(KEY, {"a": auc_like})
    with pytest.raises(MetricTypeError):
        record_candidate(KEY, _meta(auc_like))
    for kind in ("pr_auc", "rank_biserial", "AUC"):
        with pytest.raises(MetricTypeError):
            run_dsr_pbo(KEY, {"a": CandidateReturns("a", _cand("a").returns, metric_kind=kind)})
    named = _cand("a").returns.rename("auc")                                # 以 Series 名偷渡亦拒
    with pytest.raises(MetricTypeError):
        run_dsr_pbo(KEY, {"a": CandidateReturns("a", named)})
    with pytest.raises(MetricTypeError):
        run_dsr_pbo(KEY, {"a": pd.Series([0.1, 0.2])})                       # 非 typed 容器
    with pytest.raises(MetricTypeError):
        record_candidate(KEY, _meta(_cand("a"), metric_kind="auc"))


def test_min_btl_shortfall_loud():
    cands = {c: _cand(c, mu=m, seed=i, span_years=0.05) for i, (c, m) in enumerate([("a", 0.004), ("b", 0.0)])}
    for cr in cands.values():
        record_candidate(KEY, _meta(cr))
    rep = run_dsr_pbo(KEY, cands, target_sharpe=0.5, s_blocks=4)
    assert rep["eligibility"]["eligible"] is False and rep["eligibility"]["loud"] == "return_series_shorter_than_min_btl"
    assert rep["eligibility"]["required_years_upper_bound"] > rep["eligibility"]["available_years"]


def test_single_candidate_pbo_unavailable_and_obs_below_blocks():
    a = _cand("a")
    record_candidate(KEY, _meta(a))
    rep = run_dsr_pbo(KEY, {"a": a})
    assert rep["pbo"]["status"] == "unavailable" and rep["pbo"]["reason"] == "single_candidate"
    assert rep["dsr"]["n_trials_used"] == 1 and rep["dsr"]["sr0"] == 0.0   # N=1 ⇒ SR0=0
    b = _cand("b", n=5, seed=3)
    record_candidate(KEY, _meta(b))
    rep2 = run_dsr_pbo(KEY, {"a": _cand("a", n=5), "b": b}, s_blocks=8)
    assert rep2["pbo"]["reason"] == "n_obs_below_s_blocks"


def test_record_guards_and_ledger_mismatch_unverifiable():
    a = _cand("a")
    with pytest.raises(TypeError):
        record_candidate("not-a-key", _meta(a))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        record_candidate(KEY, {k: v for k, v in _meta(a).items() if k != "rule_digest"})
    with pytest.raises(ValueError):
        run_dsr_pbo(KEY, {"zzz": a})                                         # key ≠ candidate_id
    # ledger 只記 a、輸入 a+b ⇒ universe guard unverifiable（禁跳過 ledger 直餵）
    record_candidate(KEY, _meta(a))
    rep = run_dsr_pbo(KEY, {"a": a, "b": _cand("b", seed=2)}, s_blocks=4)
    assert rep["capability_status"] == "unavailable" and rep["reason"] == "universe_provenance_unverifiable"
    assert rep["pbo"]["status"] == "unavailable" and rep["dsr"]["status"] == "unavailable"   # CODEX-R1-P1-02：未記帳候選不得成 champion
    assert rep["candidate_set_mismatch"] == {"input": ["a", "b"], "ledger": ["a"]}


def test_disguised_score_series_rejected():
    """COMPOSER-R1-P1-01／GROK-R1-P2-01 RECHECK：metric_kind 預設＋分數數列（無 to_return_series 收據 attrs）⇒ MetricTypeError。"""
    s = pd.Series([0.9, 0.85, 0.72], index=["e0", "e1", "e2"], name="hold_return")
    s.attrs.update({"span_years": 2.0})
    with pytest.raises(MetricTypeError):
        run_dsr_pbo(KEY, {"a": CandidateReturns("a", s)})
    with pytest.raises(MetricTypeError):
        record_candidate(KEY, _meta(CandidateReturns("a", s)))
    s2 = pd.Series([0.73, 0.81, 0.66], index=["e0", "e1", "e2"], name="score")
    with pytest.raises(MetricTypeError):
        run_dsr_pbo(KEY, {"a": CandidateReturns("a", s2)})
    single = _cand("a").returns.iloc[:1]                                   # 單一值非序列
    with pytest.raises(MetricTypeError):
        run_dsr_pbo(KEY, {"a": CandidateReturns("a", single)})
    # 收據鍵不全／t_semantics 錯／hash 非 64hex／span≤0／時序收據未覆蓋 ⇒ 各拒
    for tweak in ({"t_semantics": "bar_count"}, {"source_artifact_hash": "zz"}, {"span_years": 0.0},
                  {"entry_at_ms_by_event": {"e000": 1}}):
        bad = _cand("a").returns.copy()
        bad.attrs = {**_cand("a").returns.attrs, **tweak}
        with pytest.raises(MetricTypeError):
            run_dsr_pbo(KEY, {"a": CandidateReturns("a", bad)})


def test_unlogged_candidate_cannot_be_champion():
    """CODEX-R1-P1-02 RECHECK：ledger 只記 logged；輸入 unlogged（attrs.hash 借 logged 之 H）⇒ DSR／MinBTL 皆 unavailable。"""
    logged = _cand("logged", mu=0.0)
    record_candidate(KEY, _meta(logged))
    un = _cand("unlogged", mu=0.01, seed=9)                                 # 收據合法但未記帳
    rep = run_dsr_pbo(KEY, {"unlogged": un})
    assert rep["capability_status"] == "unavailable" and rep["dsr"]["status"] == "unavailable"
    assert rep["eligibility"]["status"] == "unavailable" and "champion" not in rep


def test_pbo_observation_axis_by_entry_time_not_lexicographic(monkeypatch):
    """CODEX-R1-P1-03／COMPOSER-R1-P2-02／GROK-R1-P1-01 RECHECK：event_id 字串序與時間序相反 ⇒ 矩陣列仍依 entry_at_ms。"""
    ids = [f"evt_{i}" for i in (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)]            # 時間序：evt_10 最早
    entry = {e: BASE + i * H12 for i, e in enumerate(ids)}
    a = _cand("a", ids=ids, entry_ms=entry, seed=1)
    b = _cand("b", ids=ids[::2], entry_ms={e: entry[e] for e in ids[::2]}, seed=2)
    for cr in (a, b):
        record_candidate(KEY, _meta(cr))
    captured = {}
    import momentum.Analysis.event_samples.candidate_ledger as mod
    orig = mod.probability_of_backtest_overfitting

    def spy(**kw):
        captured["M"] = kw["returns_matrix"].copy()
        return orig(**kw)

    monkeypatch.setattr(mod, "probability_of_backtest_overfitting", spy)
    rep = run_dsr_pbo(KEY, {"a": a, "b": b}, s_blocks=4)
    assert rep["pbo"]["status"] == "ok"
    M = captured["M"]
    np.testing.assert_allclose(M[:, 0], a.returns.loc[ids].to_numpy())       # 列序＝時間序（evt_10 在第 0 列）
    assert rep["pbo"]["observation_axis_first_last_entry_ms"] == [entry["evt_10"], entry["evt_1"]]
    assert M[1, 1] == 0.0 and M[0, 1] == b.returns.loc["evt_10"]             # b 未出手者 0
    # 跨候選同事件時間戳衝突 ⇒ fail-closed
    c = _cand("c", ids=ids[:4], entry_ms={**{e: entry[e] for e in ids[:4]}, "evt_9": entry["evt_9"] + 1}, seed=3)
    record_candidate(KEY, _meta(c))
    with pytest.raises(ValueError, match="不一致"):
        run_dsr_pbo(KEY, {"a": a, "b": b, "c": c}, s_blocks=4)


def test_stale_receipt_after_copy_mutation_rejected(bars):
    """CODEX-R2-P1-02 RECHECK：to_return_series 真實產出 copy 後原地改值 ⇒ hash 與 values 不符 ⇒ MetricTypeError；未改者通過。"""
    df, rec = _events("trigger_open", [300, 420, 555])
    g = bars["ETHUSDT"]["12h"]
    s = to_return_series(pd.Series(True, index=df["event_id"]), {"ETHUSDT": g}, "trigger_open", LD, rec, events=df)
    assert cl.receipt_digest(s) == s.attrs["source_artifact_hash"]
    cl._assert_return_series(CandidateReturns("a", s), "t")                 # 真實產出通過
    mutated = s.copy()
    mutated.iloc[0] += 0.123
    assert mutated.attrs["source_artifact_hash"] == s.attrs["source_artifact_hash"]   # pandas copy 帶舊 hash
    with pytest.raises(MetricTypeError, match="stale"):
        run_dsr_pbo(KEY, {"a": CandidateReturns("a", mutated)})
    with pytest.raises(MetricTypeError, match="stale"):
        record_candidate(KEY, _meta(CandidateReturns("a", mutated)))
    reindexed = s.copy()
    reindexed.index = [f"x{i}" for i in range(len(s))]                       # 改 index 亦 stale
    reindexed.attrs["entry_at_ms_by_event"] = {f"x{i}": v for i, v in enumerate(s.attrs["entry_at_ms_by_event"].values())}
    with pytest.raises(MetricTypeError, match="stale"):
        run_dsr_pbo(KEY, {"a": CandidateReturns("a", reindexed)})


def test_sidecar_first_and_ledger_without_provenance_unavailable(_redirect_ledger_root, monkeypatch):
    """CODEX-R2-P1-01 RECHECK：①sidecar 先寫——帳本 append 失敗只留 provenance 孤兒、N 不變；
    ②帳本有列但無 sidecar ⇒ run_dsr_pbo unavailable:provenance_incomplete；③provenance_reconcile 可驗證 orphan。"""
    import json
    a = _cand("a")
    # ① 帳本 append 失敗
    orig = ledger_mod.append_trial_attempt
    monkeypatch.setattr(ledger_mod, "append_trial_attempt", lambda **kw: (_ for _ in ()).throw(OSError("ledger write unavailable")))
    with pytest.raises(OSError):
        record_candidate(KEY, _meta(a))
    monkeypatch.setattr(ledger_mod, "append_trial_attempt", orig)
    root = _redirect_ledger_root / "strategy_validation"
    assert not (root / f"{KEY.research_session_id}__{KEY.dataset_key}.jsonl").exists()
    assert (root / f"{KEY.research_session_id}__{KEY.dataset_key}.provenance.jsonl").exists()
    rep = run_dsr_pbo(KEY, {"a": a})
    assert rep["ledger"]["status"] == "unavailable"                         # N 不受孤兒 provenance 影響
    recon = cl.provenance_reconcile(KEY)
    assert recon["provenance_without_ledger"] == ["a"] and recon["complete"] is False
    # ② 直接寫帳本列（繞過 record_candidate）⇒ 無 sidecar ⇒ unavailable
    b = _cand("b", seed=2)
    ledger_mod.append_trial_attempt(research_session_id=KEY.research_session_id, dataset_key=KEY.dataset_key, record={
        "research_session_id": KEY.research_session_id, "dataset_key": KEY.dataset_key, "candidate_id": "b",
        "evaluation_id": "eval-b", "attempt_index": 0, "state": "complete", "metric_name": "sharpe", "metric_value": 0.1,
        "metric_unit": "per_period", "metric_valid": True, "input_artifact_hash": b.returns.attrs["source_artifact_hash"],
        "ts": "2026-08-21T00:00:00Z"})
    rep2 = run_dsr_pbo(KEY, {"b": b})
    assert rep2["capability_status"] == "unavailable" and rep2["reason"] == "provenance_incomplete"
    assert rep2["dsr"]["status"] == "unavailable" and rep2["provenance_reconcile"]["ledger_without_provenance"] == ["b"]
    # ③ 正常路徑：sidecar＋帳本齊 ⇒ ok
    c = _cand("c", seed=3)
    record_candidate(KEY, _meta(c))
    record_candidate(KEY, _meta(b, evaluation_id="eval-b2"))                # 補 b 之 provenance
    rep3 = run_dsr_pbo(KEY, {"b": b, "c": c}, s_blocks=4)
    assert rep3["capability_status"] == "ok" and rep3["provenance_reconcile"]["complete"] is True
    prov_lines = (root / f"{KEY.research_session_id}__{KEY.dataset_key}.provenance.jsonl").read_text().splitlines()
    assert {json.loads(p)["candidate_id"] for p in prov_lines} == {"a", "b", "c"}


def test_record_requires_command_and_expected_before_any_write(_redirect_ledger_root):
    """CODEX-R1-P1-04 RECHECK：缺 command／expected 或 expected 非 pass|fail ⇒ 拒，且帳本與 sidecar 皆未建立。"""
    a = _cand("a")
    for bad in ({"command": None}, {"command": "  "}, {"expected": None}, {"expected": "maybe"}):
        with pytest.raises(ValueError):
            record_candidate(KEY, _meta(a, **bad))
    root = _redirect_ledger_root / "strategy_validation"
    assert not root.exists() or not any(root.iterdir())
    record_candidate(KEY, _meta(a))
    import json
    prov = (root / f"{KEY.research_session_id}__{KEY.dataset_key}.provenance.jsonl").read_text().splitlines()
    assert json.loads(prov[0])["command"] and json.loads(prov[0])["expected"] == "pass"
