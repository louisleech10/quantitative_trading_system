"""FF-STAT Task 1.2：刪免檢清單，開啟平穩化時逐欄檢定（docs/FFSTAT_SPEC.md §C「逐欄檢定」）。

實作前應為紅。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as h


@pytest.fixture(scope="module")
def stat_run(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("ffstat_all_tested")
    try:
        h.prepare_stat_env(mp, tmp)
        _, _, result = h.run_stat(tmp, h.stat_payload())
        return {"decisions": h.decisions(result), "names": list(result.metadata["feature_names"])}
    finally:
        mp.undo()


def test_every_column_entering_step_has_pvalue(stat_run: Dict[str, Any]) -> None:
    """Task 1.2 驗證：開啟平穩化之真實輕量 run 中，進入步驟之每欄皆有 ADF p 值紀錄（欄集合＝基礎欄集合）。"""
    baseline = json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))
    dec = stat_run["decisions"]
    assert set(dec) == set(baseline["base"])
    assert all(isinstance(d["adf_pvalue"], float) for d in dec.values())


def test_boundary_03_formerly_name_exempt_columns_are_tested(stat_run: Dict[str, Any]) -> None:
    """Task 1.2 邊界①：基準中被名字免檢之欄（含 Ratio／Cross）於改後皆有 p 值。"""
    baseline = json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))
    exempt = [c for c, d in baseline["decisions"].items() if d["name_exempt"]]
    assert exempt and any("Cross" in c or "Ratio" in c for c in exempt)
    dec = stat_run["decisions"]
    assert all(isinstance(dec[c]["adf_pvalue"], float) for c in exempt)


def test_boundary_04_adf_apply_to_all_tests_each_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.2 邊界②：ADF 差分 `apply_to=all` 路徑亦逐欄檢定（fracdiff 關閉，只開 ADF 差分）。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    payload = h.stat_payload(fracdiff=False)
    payload["preprocessing"]["adf_differencing"]["apply_to"] = "all"
    _, _, result = h.run_stat(tmp_path, payload)
    dec = h.decisions(result)
    baseline = json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))
    assert set(dec) == set(baseline["base"])
    assert all(isinstance(d["adf_pvalue"], float) for d in dec.values())


def test_adf_safe_skip_config_section_rejected() -> None:
    """Task 1.2 驗證：設定帶 `adf_safe_skip` 段 ⇒ 設定驗證拋錯並指名已移除。"""
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    payload = h.stat_payload()
    payload["preprocessing"]["adf_safe_skip"] = {"enabled": True}
    with pytest.raises(ValueError, match="adf_safe_skip"):
        factory._resolve_config(payload)


def test_mutation_name_exemption_reinstated_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ①：判定退回欄名子字串免檢（名字免檢之欄不進 ADF）⇒ 邊界①必紅。"""
    from momentum.FeatureEngineering.utils.adf_safe_skip import is_safe_skip

    real = FeaturePreprocessor._get_non_stationary_columns

    def _mutant(self, df):
        return real(self, df[[c for c in df.columns if not is_safe_skip(str(c))]])

    monkeypatch.setattr(FeaturePreprocessor, "_get_non_stationary_columns", _mutant)
    h.prepare_stat_env(monkeypatch, tmp_path)
    _, _, result = h.run_stat(tmp_path, h.stat_payload())
    mutated = {"decisions": h.decisions(result)}
    with pytest.raises(AssertionError):
        test_boundary_03_formerly_name_exempt_columns_are_tested(mutated)
