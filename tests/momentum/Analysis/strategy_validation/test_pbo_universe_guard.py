"""Task 4.3 驗證：候選宇宙污染防護（唯一成功路徑＝ledger_all_candidates 且集合／count 三方／canonical hash 三項全符）。

⑤d（A1-4）：三項全符 ⇒ status ok 且 universe_scope=="ledger_recorded_only"——本欄位存在之理由＝守衛**不**證明 ledger 自身完整
（`CODEX-R8-P0-01`；殘留 G1-R9：生產者若只寫入事後 top-K，三項全符仍 ok），故 Task 3.3 據此強制降級。
mutation §V-6（移除 universe_provenance 檢查）⇒ ① 轉紅。
"""

import math

import numpy as np
import pytest

from momentum.Analysis.strategy_validation.ledger import LedgerReadResult
from momentum.Analysis.strategy_validation.pbo import (
    UniverseProvenance,
    candidate_set_hash,
    check_universe_provenance,
    probability_of_backtest_overfitting,
)


def _ledger(ids):
    ids = list(ids)
    return LedgerReadResult(
        n_candidates_considered=len(ids), n_evaluated=len(ids), n_valid_metrics=len(ids), n_failed_or_pruned=0,
        n_rows_rejected=0, n_is_lower_bound=True, n_for_dsr=len(ids), snapshot_hash="s",
        artifact_hashes=frozenset({"h"}), candidate_ids=frozenset(ids), n_semantics="unknown",
        valid_sharpe_values=(), status="ok", reason="",
    )


def _prov(ids, **over):
    base = dict(selection_free=True, source="ledger_all_candidates", candidate_set_hash=candidate_set_hash(ids),
                candidate_count=len(ids), declared_by="test")
    base.update(over)
    return UniverseProvenance(**base)


_IDS = [f"c{i}" for i in range(50)]
_M = np.random.default_rng(0).standard_normal((40, 50)) * 0.01


def _pbo(prov, ids=_IDS, ledger="default"):
    return probability_of_backtest_overfitting(
        returns_matrix=_M[:, : len(ids)], n_obs=40, n_candidates=len(ids), candidate_ids=ids, s_blocks=2,
        selection_metric="mean_return", universe_provenance=prov,
        ledger_result=_ledger(_IDS) if ledger == "default" else ledger,
    )


def test_selection_free_false_is_contaminated():
    """① selection_free=False ⇒ status!=ok、isnan(value)、reason universe_selection_contaminated。"""
    got = _pbo(_prov(_IDS, selection_free=False))
    assert got.status != "ok" and math.isnan(got.value)
    assert got.reason == "universe_selection_contaminated"
    assert got.universe_scope is None


def test_unknown_source_and_none_raise():
    """②③ 未知 source ⇒ raise；None ⇒ raise。"""
    with pytest.raises(ValueError):
        _pbo(_prov(_IDS, source="my_grid"))
    with pytest.raises(ValueError):
        _pbo(None)
    with pytest.raises(ValueError):
        check_universe_provenance(None, _IDS, 50, _ledger(_IDS))


def test_external_declared_and_full_grid_are_unverifiable():
    """④ external_declared ⇒ unverifiable；④b full_grid 自洽（hash／count 正確）仍 unverifiable（無例外）。"""
    for src in ("external_declared", "full_grid"):
        got = _pbo(_prov(_IDS, source=src))
        assert got.status != "ok" and got.reason == "universe_provenance_unverifiable"
        assert got.universe_scope is None


def test_ledger_all_candidates_missing_ledger_or_ids_is_unverifiable():
    """⑤ ledger_all_candidates 缺 ledger_result／候選 ids 不符 ⇒ unverifiable。"""
    assert check_universe_provenance(_prov(_IDS), _IDS, 50, None) == ("unavailable", "universe_provenance_unverifiable")
    got = _pbo(_prov(_IDS), ledger=None)
    assert got.reason == "universe_provenance_unverifiable"


def test_top10_subset_with_correct_self_hash_is_rejected():
    """⑤b 50 選 top-10、自算 hash 正確 ⇒ 仍拒（集合≠ledger 集合、count≠n_candidates_considered）。"""
    top10 = _IDS[:10]
    got = _pbo(_prov(top10), ids=top10)  # ledger 仍為 50
    assert got.status != "ok" and got.reason == "universe_provenance_unverifiable"


def test_same_count_different_set_is_rejected():
    """⑤b2 50 vs 50 但 1 id 不同 ⇒ 仍拒。"""
    ids = _IDS[:-1] + ["c999"]
    got = _pbo(_prov(ids), ids=ids)
    assert got.status != "ok" and got.reason == "universe_provenance_unverifiable"


def test_wrong_hash_or_wrong_count_is_rejected():
    """自備 hash 不作證明：hash 錯／count 錯（其餘皆符）⇒ 拒。"""
    assert check_universe_provenance(_prov(_IDS, candidate_set_hash="0" * 64), _IDS, 50, _ledger(_IDS))[1] == "universe_provenance_unverifiable"
    assert check_universe_provenance(_prov(_IDS, candidate_count=49), _IDS, 50, _ledger(_IDS))[1] == "universe_provenance_unverifiable"


def test_all_three_match_is_ok_with_universe_scope_ledger_recorded_only():
    """⑤c 三項全符 ⇒ ok；⑤d（A1-4）status ok 且 universe_scope=='ledger_recorded_only'。

    🔴 本欄位存在之理由：三項守衛只證「PBO 之候選集合＝ledger 記錄之集合」，**不**證「ledger 記錄了全部試過的候選」
    （生產者事後只寫 top-K 仍全符；`CODEX-R8-P0-01`／殘留 G1-R9）⇒ Task 3.3 見此值強制降級。
    """
    assert check_universe_provenance(_prov(_IDS), _IDS, 50, _ledger(_IDS)) == ("ok", "")
    got = _pbo(_prov(_IDS))
    assert got.status == "ok"
    assert got.universe_scope == "ledger_recorded_only"


def test_provenance_post_init_type_checks():
    with pytest.raises(ValueError):
        UniverseProvenance(selection_free=1, source="full_grid", candidate_set_hash="x", candidate_count=1, declared_by="t")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        UniverseProvenance(selection_free=True, source="", candidate_set_hash="x", candidate_count=1, declared_by="t")
    with pytest.raises(ValueError):
        UniverseProvenance(selection_free=True, source="full_grid", candidate_set_hash="x", candidate_count=-1, declared_by="t")
