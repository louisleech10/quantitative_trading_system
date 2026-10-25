"""FFPROD Task 1.2：縮尾有效設定入逐欄處理紀錄（SPEC `docs/FFPROD_SPEC.md` Task 1.2）。

契約 `momentum/FeatureEngineering/contracts/run_provenance.json` 新增鍵 `winsor_effective_fields`（逐欄紀錄之縮尾有效設定欄名
清單，皆屬 `record_columns`：`winsor_method`、`winsor_lower_q`、`winsor_upper_q`、`winsor_sigma_k`、`winsor_window`、
`winsor_min_periods`、`winsor_compute_dtype`；分位端點沿用產品碼 transform context 之 `_q` 鍵名）與值集
`winsor_method_record_values`（`disabled`、`passthrough`、`not_selected`）；欄 `winsor_method` 值域＝契約
`winsor_method_values` ∪ `winsor_method_record_values`。真實 kline 短窗生成沿 `tests/feature_engineering/preprov_helpers.py`
之格（`h1_stat_on` 縮尾開〔生產預設 quantile〕、變體 `h1_winsor_sigma` 縮尾 sigma、`h1_pp_off` 前處理關、`ratio_unsafe`
比值不安全欄原值通過），逐格單行程串行。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import preprov_helpers as ph


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("ffprod_winsor_prov"))


def _fields() -> List[str]:
    return [str(f) for f in rp.load_contract()["winsor_effective_fields"]]


def _table(runs: ph.RunCache, cell: str) -> pd.DataFrame:
    handle = runs.get(cell)
    return ph.provenance_table(handle.run_dir, "raw")


# ---------------------------------------------------------------------------------------------- 驗證

def test_winsor_effective_fields_are_record_columns() -> None:
    contract = rp.load_contract()
    fields = _fields()
    assert fields == ["winsor_method", "winsor_lower_q", "winsor_upper_q", "winsor_sigma_k", "winsor_window",
                      "winsor_min_periods", "winsor_compute_dtype"]
    assert set(fields) <= set(contract["record_columns"])


def _assert_applied_params(applied: pd.DataFrame, method: str) -> None:
    """逐 method 分支斷言全部有效設定欄：quantile ⇒ 兩分位端點有值、sigma k 為空；sigma ⇒ sigma k 有值、端點為空；
    兩者之滾動窗、最少有效值、計算精度皆有值（產品碼之 transform context 鍵 `winsor_lower_q`／`winsor_upper_q`／
    `winsor_window`／`winsor_min_periods`，`feature_preprocessor.py` 之 `_rolling_window`／`_rolling_min_periods`）。"""
    assert len(applied) > 0
    assert set(applied["winsor_method"]) == {method}
    endpoints = applied[["winsor_lower_q", "winsor_upper_q"]]
    if method == "quantile":
        assert endpoints.notna().all().all() and applied["winsor_sigma_k"].isna().all()
    else:
        assert applied["winsor_sigma_k"].notna().all() and endpoints.isna().all().all()
    for field in ("winsor_window", "winsor_min_periods", "winsor_compute_dtype"):
        assert applied[field].notna().all(), field
    assert (applied["winsor_min_periods"] <= applied["winsor_window"]).all()


def test_applied_quantile_columns_record_all_params(runs: ph.RunCache) -> None:
    table = _table(runs, "h1_stat_on")
    _assert_applied_params(table[table["winsorization"] == "applied"], "quantile")


def test_applied_sigma_columns_record_all_params(runs: ph.RunCache) -> None:
    table = _table(runs, "h1_winsor_sigma")
    _assert_applied_params(table[table["winsorization"] == "applied"], "sigma")


def test_recorded_method_values_follow_contract(runs: ph.RunCache) -> None:
    contract = rp.load_contract()
    allowed = set(rp.contract_value_set(contract, "winsor_method_values")) | set(
        rp.contract_value_set(contract, "winsor_method_record_values"))
    for cell in ("h1_stat_on", "h1_winsor_sigma", "h1_pp_off", "ratio_unsafe"):
        assert set(_table(runs, cell)["winsor_method"]) <= allowed, cell


def test_old_record_contract_version_rejected(runs: ph.RunCache) -> None:
    """舊紀錄（新欄出現前之契約版本）讀取 ⇒ 依 PRE-PROV 既有舊格式處置：契約版本不符即 `ProvenanceIntegrityError`。"""
    handle = runs.get("h1_stat_on")
    pointer = dict(ph.provenance_pointer(handle.run_dir, "raw"))
    pointer["contract_version"] = int(rp.load_contract()["version"]) - 1
    with pytest.raises(rp.ProvenanceIntegrityError, match="紀錄契約版本"):
        rp.read_provenance_table(handle.run_dir, pointer)


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_03_winsor_disabled_recorded_as_disabled(runs: ph.RunCache) -> None:
    table = _table(runs, "h1_pp_off")
    assert len(table) > 0
    assert set(table["winsor_method"]) == {"disabled"}


def test_boundary_04_ratio_unsafe_passthrough_recorded(runs: ph.RunCache) -> None:
    table = _table(runs, "ratio_unsafe")
    unsafe = table[table["terminal"] == "ratio_unsafe"]
    assert len(unsafe) > 0
    assert set(unsafe["winsor_method"]) == {"passthrough"}


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_missing_winsor_method_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：組表時把 `winsor_method` 清空 ⇒ 寫入端之契約驗證拒收（`ProvenanceError`）。另起根、不經模組倉。"""
    real_build = rp.build_provenance_table

    def broken(*args: Any, **kwargs: Any) -> pd.DataFrame:
        table = real_build(*args, **kwargs)
        table["winsor_method"] = None
        return table

    monkeypatch.setattr(rp, "build_provenance_table", broken)
    with pytest.raises(rp.ProvenanceError):
        ph.generate_short_run(tmp_path, "h1_stat_on")
