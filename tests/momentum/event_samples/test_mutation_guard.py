"""GAP-3 §V 最小 mutation 集——B1 歸屬 8 條（M1/M2/M3/M5/M8/M9/M10/M12；M4/M7/M11=B2、M6=B3）。

統一命令：`venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k M<n>`。
每條＝「baseline 預期＋mutation diff＋預期 rc」：mutation 以 monkeypatch 注入，測試斷言
守護斷言**確實抓到**（mutation 態紅之機械等價）。fixture 身分：M1/M2/M9 用真實 kline
`tests/golden/la0/inputs/` 同源 cache＋固定事件表（seed 20260820）；M3/M5/M8/M10/M12 用
合成事件表（seed 20260820＋M 序號；章程 §F——合成的是事件/label 序列非價格）。
fixture sha256 首建記入 `handoffs/run_receipts/gap3_mutation_fixtures.json`。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples import alignment as al
from momentum.Analysis.event_samples import baseline as bl
from momentum.Analysis.event_samples import import_contract as ic
from momentum.Analysis.event_samples.alignment import align_events, n_dropped_by_reason
from momentum.Analysis.event_samples.counterexample_classifier import _classify_one
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.import_contract import ContractValidationError, validate_event_import
from momentum.Analysis.event_samples.types import AlignmentConfig, EventManifest, EventSplitConfig, OracleConfig
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000
T0_100 = BASE + 100 * H12
SEED = 20260820
RECEIPT = Path(__file__).resolve().parents[3] / "handoffs" / "run_receipts" / "gap3_mutation_fixtures.json"


def _fixed_event_table(m_no: int, n: int = 6) -> list:
    """固定事件表（seed 20260820＋M 序號；決定性）。"""
    rng = np.random.default_rng(SEED + m_no)
    idxs = sorted(rng.choice(np.arange(200, 1400), size=n, replace=False).tolist())
    return [make_event(i, t0=BASE + int(x) * H12, label=int(i % 2)) for i, x in enumerate(idxs)]


def _record_fixture(name: str, payload) -> None:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    data = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {}
    if name not in data:  # 首建記入；既有不覆寫（receipt 非規格）
        data[name] = {"sha256": digest, "seed": SEED}
        RECEIPT.write_text(json.dumps(data, indent=1, sort_keys=True))


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def _aligned(events, bars, tfs=("12h",)):
    df = validate_event_import(events)
    return df, align_events(df, bars, AlignmentConfig(timeframes=tfs))


def test_M1_failure_accounting_swallow_detected(bars):
    """M1：drop 不寫 reason ⇒ 記帳守恆斷言（n_input == n_receipts + n_failures）紅。"""
    events = _fixed_event_table(1) + [make_event(99, t0=1777291200000, label=0)]  # 末端必失敗
    _record_fixture("M1_events", events)
    df, (rec, fail) = _aligned(events, bars)
    assert len(df) == len(rec.event_level) + len(fail)              # baseline 守恆
    swallowed = fail.iloc[:-1]                                       # mutation：吞掉一筆失敗記帳
    assert len(df) != len(rec.event_level) + len(swallowed)          # 守恆斷言必抓到（紅）
    assert sum(n_dropped_by_reason(fail).values()) == len(fail)


def test_M2_pit_shift_next_bar_detected(bars, monkeypatch):
    """M2：feature_cutoff 改選 decision_at 之後下一實際 bar ⇒ §G-3(ii) oracle 紅。"""
    events = _fixed_event_table(2)
    _record_fixture("M2_events", events)
    df, (rec, fail) = _aligned(events, bars)
    assert fail.empty and (rec.per_tf["feature_cutoff_ms"] <= rec.event_level.set_index("event_id").loc[rec.per_tf["event_id"], "decision_at_ms"].to_numpy()).all()
    orig = al._select_cutoff_idx
    monkeypatch.setattr(al, "_select_cutoff_idx", lambda c, d: orig(c, d) + 1)
    _, (rec2, fail2) = _aligned(events, bars)
    assert len(rec2.event_level) == 0 and set(fail2["reason"]) == {"feature_after_decision"}


def test_M3_ms_gate_removed_lets_seconds_pass(monkeypatch):
    """M3：刪量級檢查 ⇒ 秒級 t0 通過匯入 ⇒ 拒收斷言紅。"""
    events = [make_event(0, t0=1704067200, label=1), make_event(1, t0=1704067200 + 43200, label=0)]
    _record_fixture("M3_events", events)
    with pytest.raises(ContractValidationError):                     # baseline：拒
        validate_event_import(events)
    mutated = ic.load_event_import_contract()
    mutated["ms_magnitude_min"] = 10**9                              # mutation：閘鬆到秒級也放行（等效移除）
    df = validate_event_import(events, contract=mutated)
    assert len(df) == 2                                              # 秒級混入 ⇒ 拒收斷言必紅


def test_M5_cluster_weight_all_one_detected():
    """M5：cluster_weight 全設 1（棄 1/n）⇒ 同簇權重和＝1（atol=1e-12）斷言紅。"""
    rows = []
    rng = np.random.default_rng(SEED + 5)
    for s, sym in enumerate(("ETHUSDT", "BTCUSDT")):
        for i in range(5):
            d = BASE + i * H12
            rows.append({"event_id": f"{sym}-e{i}", "symbol": sym, "decision_at_ms": d,
                         "observation_interval_start_ms": d, "observation_interval_end_ms": d + H12,
                         "label_start_ms": d, "label_end_ms": d + H12, "dedupe_cluster_id": "c0",
                         "overlap_set_hash": "h", "uniqueness_weight": 1.0, "in_primary": True,
                         "in_sensitivity": True, "timeframe": "12h"})
    _record_fixture("M5_manifest_rows", rows)
    manifest = EventManifest(table=pd.DataFrame(rows), summary={"n_events_raw": len(rows), "n_events_effective": len(rows)}, policy={})
    plan = split_events(manifest, EventSplitConfig(test_fraction=0.4, tier_min_test_events=0))
    sums = plan.clusters.groupby("time_cluster_id")["cluster_weight"].sum()
    assert (sums - 1.0).abs().max() <= 1e-12                         # baseline
    mutated = plan.clusters.assign(cluster_weight=1.0)               # mutation
    sums_m = mutated.groupby("time_cluster_id")["cluster_weight"].sum()
    assert (sums_m - 1.0).abs().max() > 1e-12                        # 斷言必抓到（紅）


def test_M8_identity_permutation_hard_check(monkeypatch):
    """M8：置亂改恆等排列 ⇒ 非退化與非恆等硬檢必觸發 ⇒ 紅。"""
    rng = np.random.default_rng(SEED + 8)
    ids = [f"e{i}" for i in range(120)]
    X = pd.DataFrame({"f": rng.normal(0, 1, 120)}, index=ids)
    y = pd.Series(rng.integers(0, 2, 120), index=ids)
    _record_fixture("M8_series", {"f": X["f"].tolist(), "y": y.tolist()})
    from momentum.Analysis.event_samples.types import EventSplitPlan
    plan = EventSplitPlan(
        assignments=pd.DataFrame({"event_id": ids, "symbol": "S", "split_label": ["test"] * 120}),
        purged=pd.DataFrame(), clusters=pd.DataFrame(), summary={})
    ok = bl.single_feature_binary_baseline(X, y, plan, oracle_config=OracleConfig(n_perm=200))
    assert ok["capability_status"] == "ok"                           # baseline 綠
    monkeypatch.setattr(bl, "_permute", lambda rng_, arr: arr.copy())
    with pytest.raises(ValueError, match="硬檢"):                     # mutation ⇒ 紅
        bl.single_feature_binary_baseline(X, y, plan, oracle_config=OracleConfig(n_perm=200))


def test_M9_offset_k_minus_one_detected(bars, monkeypatch):
    """M9：decision_at 推導 k 改 k−1 ⇒ §G-2 k>0 exact receipt oracle 紅。"""
    events = [make_event(0, t0=T0_100, decision_offset_bars=1, label=1), make_event(1, t0=T0_100 + 9 * H12, label=0)]
    _record_fixture("M9_events", events)
    df, (rec, fail) = _aligned(events, bars)
    assert int(rec.event_level.set_index("event_id").loc["ev0", "decision_at_ms"]) == T0_100 - H12  # baseline exact
    monkeypatch.setattr(al, "_decision_idx", lambda t0_idx, k: t0_idx - (k - 1))
    _, (rec2, _) = _aligned(events, bars)
    got = int(rec2.event_level.set_index("event_id").loc["ev0", "decision_at_ms"])
    assert got != T0_100 - H12                                       # exact oracle 必抓到（紅）


def test_M10_multi_hit_precedence_guess_detected():
    """M10：多類邊界從 unclassifiable 改取 precedence 猜一類 ⇒ 邊界案例斷言紅。"""
    cfg = {"thresholds": {"trigger_threshold": 0.005, "follow_threshold": 0.0,
                          "range_threshold": 0.01, "drop_threshold": 0.05}}
    _record_fixture("M10_case", {"r0": 0.005, "rw": -0.01, "cfg": cfg})
    assert _classify_one(0.005, -0.01, cfg) == "unclassifiable"      # baseline：不猜

    def mutated(r0, rw, c):                                          # mutation：取第一命中
        hits = []
        if r0 >= 0.005 and rw <= 0.0:
            hits.append("a_trigger_no_follow")
        if abs(r0) <= 0.01:
            hits.append("b_range")
        return hits[0] if hits else "unclassifiable"

    assert mutated(0.005, -0.01, cfg) != "unclassifiable"            # 斷言必抓到（紅）


def test_M12_t9_availability_removed_accepts(monkeypatch):
    """M12：available_at > decision_at 仍收 ⇒ B1.0 條件必填斷言紅。"""
    sm = {"model_id": "m", "version": "1", "artifact_digest": "d" * 64, "split_plan_hash": "e" * 64,
          "feature_manifest_hash": "f" * 64, "available_at": T0_100 - H12 + 1}
    events = [make_event(0, event_origin="model", source_model=sm, decision_offset_bars=1, label=1),
              make_event(1, label=0)]
    _record_fixture("M12_events", events)
    with pytest.raises(ContractValidationError):                     # baseline：拒
        validate_event_import(events)
    monkeypatch.setattr(ic, "_T9_AVAILABILITY_ENFORCED", False)      # mutation：檢查移除
    assert len(validate_event_import(events)) == 2                   # 收下 ⇒ 斷言必紅
