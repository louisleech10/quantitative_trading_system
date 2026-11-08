"""ICPERF SPEC v5.85 Task 0.6 (c)④：CPCV 完整模式預設 `max_paths=None` 逐組迭代全部路徑；抽樣只作明示選項並回報實際／總路徑數。

被測：`momentum/Analysis/model_validation/combinatorial_purged_cv.py`（現行預設 max_paths=50 且超過即以 seed 42 隨機抽，
施工前 ⇒ 本檔應為紅）。施工後契約：`CPCVConfig().max_paths is None`；`split` 產生 C(n_groups, n_test_groups) 條路徑，
測試組集合等於 `itertools.combinations` oracle；明示 `max_paths` 時 `path_summary()` 回
`{"total_paths", "used_paths", "sampled", "seed"}`；`config/model_config.yaml` 之 cpcv.max_paths 預設為 null。
資料：真實 ETHUSDT 12h kline 之報酬特徵（只用其列軸切分）。
"""
from __future__ import annotations

import math
from itertools import combinations
from pathlib import Path
from typing import Any, List, Tuple

import numpy as np
import pandas as pd
import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"


@pytest.fixture(scope="module")
def X() -> pd.DataFrame:
    from momentum.factories import create_kline_storage_manager
    if not CACHE.is_file():
        pytest.fail(f"requires_kline: missing {CACHE}")
    kline = create_kline_storage_manager(cache_dir=str(CACHE.parent)).read_klines("ETHUSDT", "12h",
                                                                                   validate_continuity=False)
    close = pd.to_numeric(kline["close"], errors="coerce")
    feats = pd.DataFrame({"ret_1": close.pct_change(), "ret_5": close.pct_change(5)}).dropna().reset_index(drop=True)
    assert len(feats) >= 1200
    return feats.iloc[:1200]


def _test_group_sets(cv: Any, X: pd.DataFrame, n_groups: int) -> List[Tuple[int, ...]]:
    size = len(X) // n_groups
    out = []
    for _, test_idx in cv.split(X):
        groups = sorted({int(i) // size for i in test_idx if int(i) // size < n_groups})
        out.append(tuple(groups))
    return out


def test_boundary_01_default_is_full_mode(X: pd.DataFrame) -> None:
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CPCVConfig, CombinatorialPurgedCV
    assert CPCVConfig().max_paths is None, "完整模式預設 max_paths=None"
    cv = CombinatorialPurgedCV({"n_groups": 12, "n_test_groups": 2, "purge_gap": 5, "embargo_pct": 0.01})
    got = _test_group_sets(cv, X, 12)
    assert len(got) == math.comb(12, 2) == 66
    assert sorted(got) == sorted(combinations(range(12), 2)), "測試組集合須等於 itertools.combinations oracle"


def test_boundary_02_explicit_sampling_reports_actual_and_total(X: pd.DataFrame) -> None:
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    cv = CombinatorialPurgedCV({"n_groups": 12, "n_test_groups": 2, "purge_gap": 5, "embargo_pct": 0.01,
                                "max_paths": 50})
    got = _test_group_sets(cv, X, 12)
    assert len(got) == 50 and set(got) <= set(combinations(range(12), 2))
    summary = cv.path_summary()
    assert summary == {"total_paths": 66, "used_paths": 50, "sampled": True, "seed": 42}


def test_boundary_03_full_mode_summary_not_sampled(X: pd.DataFrame) -> None:
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    cv = CombinatorialPurgedCV({"n_groups": 6, "n_test_groups": 2, "purge_gap": 5, "embargo_pct": 0.01})
    list(cv.split(X))
    assert cv.path_summary() == {"total_paths": 15, "used_paths": 15, "sampled": False, "seed": None}


def test_boundary_04_config_default_null() -> None:
    cfg = yaml.safe_load((REPO / "config" / "model_config.yaml").read_text(encoding="utf-8"))
    found = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "max_paths":
                    found.append(v)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(cfg)
    assert found and all(v is None for v in found), f"config/model_config.yaml 之 max_paths 預設須為 null：{found}"


def test_boundary_05_api_request_default_and_no_arbitrary_cap() -> None:
    """API：CPCVRequest 預設 max_paths=None（完整模式）；明示大值不受無依據之上界拒；服務轉出之設定沿用完整模式。"""
    from api.models.model_enhancement import CPCVRequest
    from api.services.model_enhancement_service import ModelEnhancementService
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    req = CPCVRequest(model_task_id="t")
    assert req.max_paths is None
    assert CPCVRequest(model_task_id="t", max_paths=500).max_paths == 500, "抽樣數為使用者明示選項，不設無依據上界"
    cfg = ModelEnhancementService._request_to_config(None, req)
    assert CombinatorialPurgedCV(cfg).config.max_paths is None
    cfg50 = ModelEnhancementService._request_to_config(None, CPCVRequest(model_task_id="t", max_paths=50))
    assert CombinatorialPurgedCV(cfg50).config.max_paths == 50


def _binary_target(X: pd.DataFrame) -> np.ndarray:
    return (X["ret_1"].shift(-1).fillna(0.0).to_numpy() > 0).astype(int)


def test_boundary_06_validate_response_reports_path_summary(X: pd.DataFrame) -> None:
    """validate 之實際回應帶 path_summary（總數、實際數、是否抽樣、seed）。"""
    from sklearn.linear_model import LogisticRegression
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    cv = CombinatorialPurgedCV({"n_groups": 4, "n_test_groups": 2, "purge_gap": 5, "embargo_pct": 0.01})
    out = cv.validate(lambda: LogisticRegression(max_iter=200), X, _binary_target(X), list(X.columns))["cpcv"]
    assert out["path_summary"] == {"total_paths": 6, "used_paths": 6, "sampled": False, "seed": None}
    assert out["n_paths"] == 6
    cv2 = CombinatorialPurgedCV({"n_groups": 4, "n_test_groups": 2, "purge_gap": 5, "embargo_pct": 0.01,
                                 "max_paths": 3})
    out2 = cv2.validate(lambda: LogisticRegression(max_iter=200), X, _binary_target(X), list(X.columns))["cpcv"]
    assert out2["path_summary"] == {"total_paths": 6, "used_paths": 3, "sampled": True, "seed": 42}


def test_boundary_07_full_mode_split_is_lazy(X: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> None:
    """完整模式逐組迭代：取第一條路徑前只消費一組 combinations（不一次物化全部組合）。"""
    import momentum.Analysis.model_validation.combinatorial_purged_cv as mod
    consumed = {"n": 0}
    real = mod.combinations

    def counting(it: Any, r: int) -> Any:
        for c in real(it, r):
            consumed["n"] += 1
            yield c

    monkeypatch.setattr(mod, "combinations", counting)
    cv = mod.CombinatorialPurgedCV({"n_groups": 12, "n_test_groups": 2, "purge_gap": 5, "embargo_pct": 0.01})
    next(iter(cv.split(X)))
    assert consumed["n"] == 1, f"取第一條路徑前消費了 {consumed['n']} 組"


def test_boundary_08_validate_consumes_split_lazily(X: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> None:
    """validate 於處理第一條路徑（第一次 fit）前不得預先耗盡 split。"""
    from sklearn.linear_model import LogisticRegression
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    cv = CombinatorialPurgedCV({"n_groups": 6, "n_test_groups": 2, "purge_gap": 5, "embargo_pct": 0.01})
    yielded = {"n": 0}
    at_first_fit: List[int] = []
    real_split = cv.split

    def counting_split(*a: Any, **k: Any) -> Any:
        for item in real_split(*a, **k):
            yielded["n"] += 1
            yield item

    class Spy(LogisticRegression):
        def fit(self, *a: Any, **k: Any) -> Any:
            if not at_first_fit:
                at_first_fit.append(yielded["n"])
            return super().fit(*a, **k)

    monkeypatch.setattr(cv, "split", counting_split)
    cv.validate(lambda: Spy(max_iter=200), X, _binary_target(X), list(X.columns))
    assert at_first_fit == [1], f"第一次 fit 前已產生 {at_first_fit} 條路徑"


def test_mutation_truncated_combinations_detected(X: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞（模組內 combinations 只回前 10 組）⇒ boundary_01 之 oracle 對照翻紅。"""
    import momentum.Analysis.model_validation.combinatorial_purged_cv as mod
    real = mod.combinations
    monkeypatch.setattr(mod, "combinations", lambda it, r: list(real(it, r))[:10])
    with pytest.raises(AssertionError):
        test_boundary_01_default_is_full_mode(X)
