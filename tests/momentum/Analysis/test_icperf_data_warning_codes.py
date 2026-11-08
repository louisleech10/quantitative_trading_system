"""ICPERF SPEC v5.85 Task 0.6 (d2)：資料不足警示代碼與 detail 鍵集合之單一落點契約測試。

契約 `momentum/Analysis/contracts/data_warning_codes.json`（施工前為空殼 ⇒ 本檔應為紅）：
`{"codes": {<代碼>: {"detail_keys": [<鍵>...] | null}}, "precedence": [<代碼>...]}`。現行三碼（㊹）須登記；本票新增之
固定 L HAC 小樣本碼 `small_sample_fixed_lag` 須登記且 detail 含 (d) 欄位；`precedence` 為一個結果同時符合多碼時之擇一順序
（高者先），須與產品碼行為一致。產品碼（momentum/ 全部）產生之代碼、API 模型（`api/models/ic_models.py`
`DataWarningCode`）與前端型別皆須與契約一致（不得自訂鍵或拼接字串）。
"""
from __future__ import annotations

import ast
import json
import re
import typing
from pathlib import Path
from typing import Any, Dict, Set

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
CONTRACT = REPO / "momentum" / "Analysis" / "contracts" / "data_warning_codes.json"
TYPES_TS = REPO / "frontend" / "src" / "lib" / "types.ts"
EXISTING_CODES = ["warning_not_evaluated", "persistence_not_estimable", "small_effective_sample"]
NEW_HAC_CODE = "small_sample_fixed_lag"
D_FIELDS = {"feature", "method", "n_obs", "horizon_bars", "need", "have", "reason"}


def _raw() -> Dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _contract() -> Dict[str, Any]:
    return _raw()["codes"]


def _emitted_codes(path: Path) -> Set[str]:
    """讀碼：`out["data_warning"] = "<字面>"`、`{"data_warning": "<字面>"}` 與 `data_warning="<字面>"` 之字面代碼。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value == "data_warning":
                    found |= {c.value for c in ast.walk(node.value)
                              if isinstance(c, ast.Constant) and isinstance(c.value, str)}
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "data_warning" and isinstance(v, ast.Constant) \
                        and isinstance(v.value, str):
                    found.add(v.value)
        elif isinstance(node, ast.keyword) and node.arg == "data_warning" and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            found.add(node.value.value)
    return found


def test_boundary_01_contract_registers_existing_and_new_codes() -> None:
    codes = _contract()
    assert set(EXISTING_CODES) <= set(codes), "㊹ 已上線三碼須登記"
    assert codes["persistence_not_estimable"]["detail_keys"] is None
    assert codes["warning_not_evaluated"]["detail_keys"] is None
    assert NEW_HAC_CODE in codes, "固定 L HAC 小樣本碼須登記（SPEC (d)）"


def test_boundary_02_small_sample_detail_keys_match_product() -> None:
    from momentum.Analysis import hac_ewc
    detail = hac_ewc.small_sample_warning(n_obs=60, horizon=24, method="spearman", alpha=0.05, rho_hat=0.95)
    assert detail is not None, "此組 n、h、φ 須觸發警示（n/h=2.5）"
    assert sorted(detail) == sorted(_contract()["small_effective_sample"]["detail_keys"])


def test_boundary_03_all_product_codes_registered() -> None:
    registered = set(_contract())
    emitted: Dict[str, Set[str]] = {}
    for p in sorted((REPO / "momentum").rglob("*.py")):
        codes = _emitted_codes(p)
        if codes:
            emitted[str(p.relative_to(REPO))] = codes
    assert emitted, "產品碼應有 data_warning 字面代碼"
    bad = {f: sorted(c - registered) for f, c in emitted.items() if c - registered}
    assert not bad, f"產品碼產生未登記代碼：{bad}"


def test_boundary_04_frontend_types_match_contract() -> None:
    ts = TYPES_TS.read_text(encoding="utf-8")
    unions = re.findall(r"data_warning\?:\s*([^;]+);", ts)
    assert unions, "前端須定 data_warning 型別"
    codes = set(_contract())
    for u in unions:
        lits = set(re.findall(r"'([a-z_]+)'", u))
        assert lits == codes, f"前端代碼聯集須等於契約：{sorted(lits ^ codes)}"
    for code, spec in _contract().items():
        if spec["detail_keys"] is None:
            continue
        ts_type = spec.get("ts_type")
        assert ts_type, f"{code} 之 detail 須於契約登記前端型別名 ts_type"
        m = re.search(rf"export interface {re.escape(ts_type)} \{{([^}}]*)\}}", ts)
        assert m, f"前端須定 {ts_type}（{code}）"
        ts_keys = set(re.findall(r"^\s*([a-z_]+)\??:", m.group(1), flags=re.M))
        assert ts_keys == set(spec["detail_keys"]), f"{ts_type} 鍵集合須等於契約 {code}.detail_keys"
    assert _contract()["small_effective_sample"].get("ts_type") == "HacDataWarningDetail"
    ts_types = {s["ts_type"] for s in _contract().values() if s["detail_keys"] is not None}
    detail_fields = re.findall(r"data_warning_detail\?:\s*([^;]+);", ts)
    assert len(detail_fields) == len(unions), "每個帶 data_warning 之結果列型別須同帶 data_warning_detail"
    for f in detail_fields:
        used = set(re.findall(r"\b([A-Z][A-Za-z0-9]+)\b", f))
        assert ts_types <= used, f"結果列 data_warning_detail 型別須涵蓋各碼 detail 型別：缺 {sorted(ts_types - used)}"


def _hac_rows() -> Dict[str, Any]:
    """真實產生端之警示結果：EWC 路徑之 small_effective_sample detail、固定 L 路徑之 small_sample_fixed_lag 結果。"""
    from momentum.Analysis import hac_ewc
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series
    ewc_detail = hac_ewc.small_sample_warning(n_obs=60, horizon=24, method="spearman", alpha=0.05, rho_hat=0.95)
    fixed = _compute_hac_on_ic_series(np.array([0.2, -0.1, 0.4, 0.3, -0.2, 0.5, 0.1]), horizon=1, maxlags=1)
    return {"small_effective_sample": {"feature": "f", "data_warning": "small_effective_sample",
                                       "data_warning_detail": ewc_detail},
            NEW_HAC_CODE: {"feature": "f", "data_warning": fixed.get("data_warning"),
                           "data_warning_detail": fixed.get("data_warning_detail")}}


def test_boundary_05_api_response_roundtrip_and_rejects_unregistered() -> None:
    """API 端：DataWarningCode 與契約相等；分頁回應之列經 Pydantic 驗證往返保留警示，未登記碼或缺 detail 鍵即拒。"""
    from pydantic import ValidationError
    from api.models import ic_models
    lit = getattr(ic_models, "DataWarningCode", None)
    assert lit is not None, "api/models/ic_models.py 須定 DataWarningCode（SPEC (d2)）"
    assert set(typing.get_args(lit)) == set(_contract())
    for code, row in _hac_rows().items():
        page = ic_models.ICSummaryPageResponse.model_validate(
            {"total": 1, "offset": 0, "limit": 1, "sort_by": "icir", "sort_order": "desc", "rows": [row]})
        back = page.model_dump()["rows"][0]
        assert back["data_warning"] == code and set(back["data_warning_detail"]) == \
            set(_contract()[code]["detail_keys"]), f"{code} 經回應模型往返須完整保留"
    bad_code = dict(_hac_rows()[NEW_HAC_CODE], data_warning="not_registered")
    with pytest.raises(ValidationError):
        ic_models.ICSummaryPageResponse.model_validate(
            {"total": 1, "offset": 0, "limit": 1, "sort_by": "icir", "sort_order": "desc", "rows": [bad_code]})
    row = _hac_rows()[NEW_HAC_CODE]
    missing = dict(row, data_warning_detail={k: v for k, v in row["data_warning_detail"].items() if k != "need"})
    with pytest.raises(ValidationError):
        ic_models.ICSummaryPageResponse.model_validate(
            {"total": 1, "offset": 0, "limit": 1, "sort_by": "icir", "sort_order": "desc", "rows": [missing]})


def test_boundary_06_new_codes_detail_cover_d_fields() -> None:
    new_codes = [c for c in _contract() if c not in EXISTING_CODES]
    assert NEW_HAC_CODE in new_codes, "至少須有本票新增之固定 L HAC 碼，否則本檢查空轉"
    assert "lag" in (_contract()[NEW_HAC_CODE]["detail_keys"] or ()), "固定 L 路徑適用 lag，須登記於 detail（SPEC (d)）"
    for code, spec in _contract().items():
        if code in EXISTING_CODES:
            continue
        keys = set(spec["detail_keys"] or ())
        assert D_FIELDS <= keys, f"{code} 之 detail 須含 (d) 欄位：缺 {sorted(D_FIELDS - keys)}"


def test_boundary_07_precedence_registered_and_matches_product() -> None:
    from momentum.Analysis.statistical_validator import _longitudinal_result
    prec = _raw()["precedence"]
    assert set(prec) == set(_contract()), "precedence 須恰含全部代碼"
    assert [c for c in prec if c in EXISTING_CODES] == EXISTING_CODES, "㊹ 現行擇一順序"
    both = _longitudinal_result({}, ewc_dof=None, inference_status="ok", data_warning_detail={"n_obs": 1},
                                persistence_not_estimable=True, warning_not_evaluated=True)
    assert both["data_warning"] == "warning_not_evaluated"
    pers = _longitudinal_result({}, ewc_dof=None, inference_status="ok", data_warning_detail={"n_obs": 1},
                                persistence_not_estimable=True)
    assert pers["data_warning"] == "persistence_not_estimable"
    assert prec == EXISTING_CODES + [NEW_HAC_CODE], "新碼排在 ㊹ 三碼之後（兩者分屬固定 L 與 EWC 路徑、互斥，見 boundary_08）"


def test_boundary_08_fixed_lag_and_ewc_codes_mutually_exclusive() -> None:
    """固定 L 路徑只出 small_sample_fixed_lag 或無警示；EWC 路徑不出 small_sample_fixed_lag（擇一順序因而不會互相遮蔽）。"""
    from momentum.Analysis import statistical_validator as sv
    x = pd.Series([0.1, -0.2, 0.3, 0.05, -0.1, 0.2, 0.15, -0.05, 0.12, -0.3] * 3, name="f")
    y = pd.Series([0.02, -0.01, 0.03, 0.0, -0.02, 0.01, 0.02, -0.01, 0.015, -0.03] * 3)
    fixed_small = sv.compute_hac_ic_statistics(pd.DataFrame({"f": x[:7]}), y[:7], horizon=1, method="spearman",
                                               alpha=0.05, maxlags=1)["f"]
    assert fixed_small["data_warning"] == NEW_HAC_CODE
    ewc = sv.compute_hac_ic_statistics(pd.DataFrame({"f": x}), y, horizon=1, method="spearman", alpha=0.05)["f"]
    assert ewc["data_warning"] != NEW_HAC_CODE


def test_mutation_product_detail_key_dropped_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞產品（small_sample_warning 少回一鍵）⇒ boundary_02 之一致性斷言翻紅。"""
    from momentum.Analysis import hac_ewc
    real = hac_ewc.small_sample_warning

    def broken(*args: Any, **kwargs: Any) -> Any:
        d = real(*args, **kwargs)
        return {k: v for k, v in d.items() if k != "phi_hat"} if d is not None else d

    monkeypatch.setattr(hac_ewc, "small_sample_warning", broken)
    with pytest.raises(AssertionError):
        test_boundary_02_small_sample_detail_keys_match_product()
