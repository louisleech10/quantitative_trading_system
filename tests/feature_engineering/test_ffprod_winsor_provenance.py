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

import sys
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


#: `winsor_compute_dtype`＝縮尾界線所依滾動統計量之 dtype。現行（Phase 3 前）兩 method、numba 與 pandas 兩臂皆為 float32：
#: sigma 之滾動均值／標準差 `move_mean(...).astype(np.float32)`（`_numba_transforms.py`），quantile 之界線
#: `rolling_quantile_2d` 回 `np.float32`；pandas 臂其後之裁切於 float64 進行，不改統計量 dtype。
EXPECTED_COMPUTE_DTYPE = "float32"


def expected_settings(cell: str) -> Dict[str, Any]:
    """由格之設定（`preprov_helpers.cell_spec(cell)` 之 payload）與 `WinsorConfig` 預設獨立導出之有效設定（不讀紀錄表、
    不經 preprocessor）。min_periods 依 L6.5 既有公式 min(window, max(20, window // 4)) 於本處獨立重寫。"""
    from momentum.FeatureEngineering.feature_config import WinsorConfig

    raw = dict(ph.cell_spec(cell)["payload"].get("preprocessing", {}).get("winsorization", {}))
    cfg = WinsorConfig(**raw)
    window = int(cfg.window)
    out: Dict[str, Any] = {"winsor_method": cfg.method, "winsor_window": window,
                           "winsor_min_periods": min(window, max(20, window // 4)),
                           "winsor_compute_dtype": EXPECTED_COMPUTE_DTYPE,
                           "winsor_lower_q": None, "winsor_upper_q": None, "winsor_sigma_k": None}
    if cfg.method == "quantile":
        out["winsor_lower_q"], out["winsor_upper_q"] = float(cfg.quantile_range[0]), float(cfg.quantile_range[1])
    else:
        out["winsor_sigma_k"] = float(cfg.sigma_k)
    return out


def _assert_applied_params(applied: pd.DataFrame, expected: Dict[str, Any]) -> None:
    """逐列逐欄等於獨立導出之有效設定（空值欄須為空；非空值欄須相等）。"""
    assert len(applied) > 0
    for field, value in expected.items():
        column = applied[field]
        if value is None:
            assert column.isna().all(), field
        else:
            assert (column == value).all(), f"{field}：期望 {value!r}，實得 {sorted(set(column.astype(str)))[:3]}"


def test_applied_quantile_columns_record_all_params(runs: ph.RunCache) -> None:
    table = _table(runs, "h1_stat_on")
    _assert_applied_params(table[table["winsorization"] == "applied"], expected_settings("h1_stat_on"))


def test_applied_sigma_columns_record_all_params(runs: ph.RunCache) -> None:
    table = _table(runs, "h1_winsor_sigma")
    _assert_applied_params(table[table["winsorization"] == "applied"], expected_settings("h1_winsor_sigma"))


def test_mutation_wrong_param_value_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：紀錄表之值非空但錯（sigma k、window、min periods、分位端點）⇒ 兩 method 之紀錄案轉紅；正確值 ⇒ 綠。
    以 monkeypatch 置換紀錄表來源（不生成）。"""
    module = sys.modules[__name__]
    cases = (("h1_winsor_sigma", test_applied_sigma_columns_record_all_params,
              (("winsor_sigma_k", 999.0), ("winsor_window", 1), ("winsor_min_periods", 1))),
             ("h1_stat_on", test_applied_quantile_columns_record_all_params, (("winsor_upper_q", 0.5),)))
    for cell, case, mutants in cases:
        good = pd.DataFrame([{**expected_settings(cell), "winsorization": "applied"}])
        monkeypatch.setattr(module, "_table", lambda _runs, _cell, t=good: t)
        case(None)
        for field, bad in mutants:
            monkeypatch.setattr(module, "_table", lambda _runs, _cell, t=good.assign(**{field: bad}): t)
            with pytest.raises(AssertionError):
                case(None)


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
