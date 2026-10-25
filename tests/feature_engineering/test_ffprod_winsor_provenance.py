"""FFPROD Task 1.2：縮尾有效設定入逐欄處理紀錄（SPEC `docs/FFPROD_SPEC.md` Task 1.2）。

契約 `momentum/FeatureEngineering/contracts/run_provenance.json` 新增鍵 `winsor_effective_fields`（逐欄紀錄之縮尾有效設定欄名
清單，皆屬 `record_columns`）；欄 `winsor_method` 值域＝契約 `winsor_method_values` ∪ {`disabled`, `passthrough`, `not_selected`}
（後三者亦由契約列）。真實 kline 短窗生成沿 `tests/feature_engineering/preprov_helpers.py` 之格（`h1_stat_on` 縮尾開〔生產預設
quantile〕、`h1_pp_off` 前處理關、`ratio_unsafe` 比值不安全欄原值通過），逐格單行程串行。
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
    assert "winsor_method" in fields
    assert set(fields) <= set(contract["record_columns"])


def test_applied_columns_record_method_and_params(runs: ph.RunCache) -> None:
    table = _table(runs, "h1_stat_on")
    applied = table[table["winsorization"] == "applied"]
    assert len(applied) > 0
    methods = set(rp.contract_value_set(rp.load_contract(), "winsor_method_values"))
    assert set(applied["winsor_method"]) <= methods
    quantile = applied[applied["winsor_method"] == "quantile"]
    assert quantile["winsor_lower"].notna().all() and quantile["winsor_upper"].notna().all()
    assert applied["winsor_compute_dtype"].notna().all()


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
