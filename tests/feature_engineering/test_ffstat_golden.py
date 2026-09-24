"""FF-STAT §G golden 與 Task 4.1（docs/FFSTAT_SPEC.md §G）。

基準由 `handoffs/run_receipts/ffstat_probes/freeze_baseline.py --refreeze-baseline` 於動工前 HEAD 凍結至
`tests/_golden/ffstat/baseline.json`（L6.5 append 模式：基礎欄不被改寫、平穩化另存衍生欄）。實作前應為紅。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pyarrow.parquet as pq
import pytest

from tests.feature_engineering import ffstat_helpers as h
from tests.feature_engineering.ffstat_helpers import base_fingerprints, column_fingerprint  # noqa: F401  與凍結腳本同一定義

_SKIP = ("timestamp", "__index_level_0__", "index")
_REPO = Path(__file__).resolve().parents[2]


def derived_names(root: Path) -> set:
    return {n for p in root.rglob("*_L65.parquet") for n in pq.ParquetFile(p).schema_arrow.names if n not in _SKIP}


@pytest.fixture(scope="module")
def baseline() -> Dict[str, Any]:
    return json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def on_run(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("ffstat_golden_on")
    try:
        h.prepare_stat_env(mp, tmp)
        root, _, result = h.run_stat(tmp, h.stat_payload())
        return {"root": root, "result": result}
    finally:
        mp.undo()


def test_golden_baseline_frozen_before_change(baseline: Dict[str, Any]) -> None:
    """§G 凍結：基準存在、含逐欄四 hash、衍生欄集合與基準決策；列數與欄數非空。"""
    assert baseline["rows"] > 0 and len(baseline["base"]) > 1000 and baseline["derived"]
    assert set(baseline["decisions"]) == set(baseline["base"])
    assert sum(d["name_exempt"] for d in baseline["decisions"].values()) > 0


def test_golden_base_names_and_rows_equal(baseline: Dict[str, Any], on_run: Dict[str, Any]) -> None:
    """§G ①：基礎欄名集合全等、列數全等。"""
    fp = base_fingerprints(on_run["root"])
    assert set(fp) == set(baseline["base"])
    assert {tuple(v["shape"]) for v in fp.values()} == {(baseline["rows"],)}


def test_golden_base_values_unchanged_trim0(baseline: Dict[str, Any], on_run: Dict[str, Any]) -> None:
    """§G ②（FFACT_WARMUP_TRIM=0）：基礎欄四 hash 逐欄與基準全等（非平穩化路徑零變動）。"""
    fp = base_fingerprints(on_run["root"])
    diff = [c for c in baseline["base"] if fp.get(c) != baseline["base"][c]]
    assert diff == [], diff[:5]


def test_golden_base_values_unchanged_trim1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G ②（FFACT_WARMUP_TRIM=1）：同 trim 設定下平穩化開與關兩次之基礎欄四 hash 全等（公開域不因校準域而變）。"""
    h.prepare_stat_env(monkeypatch, tmp_path / "on", FFACT_WARMUP_TRIM="1")
    root_on, _, _ = h.run_stat(tmp_path / "on", h.stat_payload())
    h.prepare_stat_env(monkeypatch, tmp_path / "off", FFACT_WARMUP_TRIM="1")
    root_off, _, _ = h.run_stat(tmp_path / "off", h.stat_payload(fracdiff=False, adf=False))
    assert base_fingerprints(root_on) == base_fingerprints(root_off)


def test_golden_derived_consistent_with_decisions(baseline: Dict[str, Any], on_run: Dict[str, Any]) -> None:
    """§G ②′：改後衍生欄集合與逐欄決策一致（有 `_fracdiff` ⇔ fracdiff、有 `_diffK` ⇔ ADF 差分 K 階）；
    摘要與逐欄重新計數一致。與基準相比之決策改變由 `test_golden_receipt_change_report` 驗。"""
    derived = derived_names(on_run["root"])
    dec = h.decisions(on_run["result"])
    for col, d in dec.items():
        assert (f"{col}_fracdiff" in derived) == bool(d["fracdiff"]), col
        order = next((k for k in (1, 2) if f"{col}_diff{k}" in derived), 0)
        assert order == int(d["adf_differenced"] or 0), col
    # 摘要（契約 metadata_keys.summary）須與逐欄資料重新計數一致（r18 codex P2-05）
    summary = on_run["result"].metadata[h.META["summary"]]
    assert set(h.CONTRACT["summary_fields"]) <= set(summary)
    assert summary["tested"] == len(dec)
    assert summary["fracdiff"] == sum(1 for d in dec.values() if d["fracdiff"])
    assert summary["adf_diff_1"] == sum(1 for c in dec if f"{c}_diff1" in derived)
    assert summary["adf_diff_2"] == sum(1 for c in dec if f"{c}_diff2" in derived)
    for key, event in (("search_failed", "search_failed"), ("cache_read_failed", "cache_read_failed"),
                       ("cache_write_failed", "cache_write_failed")):
        assert summary[key] == sum(1 for d in dec.values() if h.EVENTS[event] in d["events"])


def test_decision_change_report_counts_exactly() -> None:
    """§G ②′ 報告函式之鑑別力（純邏輯、手算期望）：兩欄改變（一欄原屬名字免檢）、一欄不變、一欄只在一邊。"""
    base = {"a": {"fracdiff": False, "adf_diff_order": 0, "name_exempt": True},
            "b": {"fracdiff": True, "adf_diff_order": 0, "name_exempt": False},
            "c": {"fracdiff": False, "adf_diff_order": 1, "name_exempt": False},
            "only_base": {"fracdiff": False, "adf_diff_order": 0, "name_exempt": False}}
    now = {"a": {"fracdiff": False, "adf_differenced": 1}, "b": {"fracdiff": True, "adf_differenced": None},
           "c": {"fracdiff": True, "adf_differenced": 0}, "only_now": {"fracdiff": True, "adf_differenced": 0}}
    rep = h.decision_change_report(base, now)
    assert rep["changed_count"] == 2 and set(rep["changed_columns"]) == {"a", "c"}
    assert rep["by_kind"] == {"(False, 0)->(False, 1)": 1, "(False, 1)->(True, 0)": 1}
    assert rep["name_exempt_changed"] == ["a"]


def test_golden_receipt_change_report(baseline: Dict[str, Any], on_run: Dict[str, Any]) -> None:
    """§G ②′／Task 4.1 收據（r19 codex P2-04）：最新 `handoffs/run_receipts/*-ffstat-golden.json`
    （由 `ffstat_probes/golden_receipt.py` 產出）之逐欄決策與本次 run 相同（fracdiff、ADF 階數、d），
    且其 `change_report` 等於以收據逐欄決策對基準獨立重算之結果。"""
    receipts = sorted((_REPO / "handoffs" / "run_receipts").glob("*-ffstat-golden.json"))
    assert receipts, "缺 golden 收據：須跑 handoffs/run_receipts/ffstat_probes/golden_receipt.py"
    receipt = json.loads(receipts[-1].read_text(encoding="utf-8"))
    dec = h.decisions(on_run["result"])
    key = ("fracdiff", "adf_differenced", "d")
    assert {c: [d[k] for k in key] for c, d in receipt["decisions"].items()} == \
        {c: [d[k] for k in key] for c, d in json.loads(json.dumps(dec)).items()}
    assert receipt["change_report"] == json.loads(json.dumps(h.decision_change_report(baseline["decisions"],
                                                                                      receipt["decisions"])))


def test_boundary_21_both_off_identical_to_baseline_base(baseline: Dict[str, Any], tmp_path: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界①：fracdiff 與 ADF 差分皆關閉 ⇒ 基礎欄與基準逐位元組相同、無任何衍生欄、無平穩化決策。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False))
    assert base_fingerprints(root) == baseline["base"]
    assert derived_names(root) == set()
    assert not result.metadata.get(h.META["decisions"])


def test_mutation_fracdiff_overwrites_base_is_caught(baseline: Dict[str, Any], tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """§G 鑑別力：fracdiff 結果改寫回基礎欄（非平穩化路徑被動到）⇒ ② 之逐欄比對必紅。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    def _mutant(result, column, fracdiff_series, mode):
        result[column] = fracdiff_series

    monkeypatch.setattr(FeaturePreprocessor, "_assign_fracdiff_result", staticmethod(_mutant))
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _, result = h.run_stat(tmp_path, h.stat_payload())
    with pytest.raises(AssertionError):
        test_golden_base_values_unchanged_trim0(baseline, {"root": root, "result": result})


def _cost_probe():
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "handoffs" / "run_receipts" / "ffstat_probes" / "cost_probe.py"
    spec = importlib.util.spec_from_file_location("ffstat_cost_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cost_probe_verdict_flags_over_tier_and_leftover() -> None:
    """Task 4.1 驗證（r18 codex P1-04、r19 codex P2-03）：成本探針之判定——tier run 任一階段（校準／交接／公開）
    之 USS 合計峰值 9 GiB 且 rc=0 ⇒ 失敗；tier run 缺交接階段峰值 ⇒ 失敗；RSS 合計超過而 USS 未超過 ⇒ 不失敗
    （共享頁不重計）；暫存殘留 ⇒ 失敗；皆正常 ⇒ 通過。"""
    probe = _cost_probe()
    ok_row = {"symbol": "BTCUSDT", "timeframe": "1h", "n": 500, "rc": 0, "calibration_tmp_leftover": 0}
    ok_tier = {"rc": 0, **{f"peak_{m}_{s}_bytes": 3 * probe.GIB for m in ("rss", "uss") for s in probe.STAGES}}
    assert probe.verdict([ok_row], ok_tier) == []
    for stage in probe.STAGES:
        assert probe.verdict([ok_row], {**ok_tier, f"peak_uss_{stage}_bytes": 9 * probe.GIB}), stage
    assert probe.verdict([ok_row], {**ok_tier, "peak_rss_handoff_bytes": 9 * probe.GIB}) == []
    no_handoff = {k: v for k, v in ok_tier.items() if "handoff" not in k}
    assert probe.verdict([ok_row], no_handoff)
    assert probe.verdict([{**ok_row, "calibration_tmp_leftover": 1}], ok_tier)
    assert probe.verdict([{**ok_row, "rc": 1}], ok_tier)
