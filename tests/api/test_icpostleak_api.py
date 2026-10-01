"""ICPOSTLEAK Phase 2（docs/ICPOSTLEAK_SPEC.md v4）：IC 頁「套用後處理」改用正式實作、ratio-unsafe 欄明示排除、保序去重。

經真服務路徑 `ic_analysis_service._apply_transforms_sync`（註冊假任務、特徵檔為真實 kline 欄之 parquet）；
寫檔之相對路徑 `data_cache/reports` 以 `monkeypatch.chdir(tmp_path)` 導向 tmp。參數單一落點：
`tests/_golden/icpostleak/contract.json`。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import PreprocessingConfig
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as h

REPO = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPO / "tests/_golden/icpostleak/contract.json").read_text(encoding="utf-8"))
COMBOS: List[List[str]] = CONTRACT["combos"]
RANK_W = int(CONTRACT["rank_window"])
Z_WINDOWS: List[int] = [int(w) for w in CONTRACT["zscore_windows"]]
UNSAFE = "ohlc_pattern_CDLDOJI"  # `_is_ratio_unsafe_column`：第二段為 pattern 類


def _real_frame(extra_unsafe: bool = False) -> pd.DataFrame:
    k = CONTRACT["kline"]
    frame = h.kline_frame(symbol=k["symbol"], timeframe=k["timeframe"]).iloc[: k["rows"]][k["columns"]].astype(float)
    if extra_unsafe:
        frame[UNSAFE] = frame[k["columns"][0]].to_numpy()  # 值取真實 kline；欄名使其為 ratio-unsafe
    return frame


def _service():
    from api.services.ic_analysis_service import ic_analysis_service

    return ic_analysis_service


def _run(tmp_path: Path, frame: pd.DataFrame, steps: List[str], selected: Optional[List[str]] = None,
         zscore_windows: Optional[List[int]] = None, tag: str = "t") -> Dict:
    """註冊假任務並經真服務路徑跑；回傳 {"result": 回應 dict, "frame": 落盤 DataFrame}。"""
    svc = _service()
    path = tmp_path / f"feat_{tag}.parquet"
    frame.to_parquet(path)
    tid = f"icpostleak_{tag}"
    svc._tasks[tid] = {"req_features_path": str(path), "result": {"analysis_status": "ok_oos", "oos_guarantees": True}}
    try:
        result = svc._apply_transforms_sync(tid, list(selected or frame.columns), "rank" in steps, "zscore" in steps,
                                            "gaussian" in steps, RANK_W, list(zscore_windows or Z_WINDOWS))
    finally:
        svc._tasks.pop(tid, None)
    return {"result": result, "frame": pd.read_hdf(result["output_path"], key="features")}


def _formal(frame: pd.DataFrame, steps: List[str], zscore_windows: Optional[List[int]] = None) -> pd.DataFrame:
    """Task 2.1 之映射：縮尾／fracdiff／ADF 關、replace、rank 窗、zscore 窗排序、gaussian 開關 → transform_selected。"""
    cfg = PreprocessingConfig(
        enabled=True, mode="replace",
        winsorization={"enabled": False}, fractional_differencing={"enabled": False}, adf_differencing={"enabled": False},
        rank_transform={"enabled": "rank" in steps, "window": RANK_W, "apply_to": "all"},
        adaptive_zscore={"enabled": "zscore" in steps, "windows": sorted(zscore_windows or Z_WINDOWS), "apply_to": "all"},
        gaussian_normalize={"enabled": "gaussian" in steps, "apply_to": "all"},
    )
    out = FeaturePreprocessor(cfg.model_dump()).transform_selected(list(frame.columns), {"ic_page": frame}, config=cfg)
    return out["ic_page"]


# ---------------------------------------------------------------- Task 2.1 驗證

@pytest.mark.parametrize("steps", COMBOS, ids=["+".join(c) for c in COMBOS])
def test_phase2_perturb_last_row_prefix_unchanged(steps: List[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """①：最後一列 ×50 ⇒ 前段逐位元組不變（改前只勾 gaussian 時 4039 格改變，收據見契約）。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame()
    base = _run(tmp_path, frame, steps, tag="a")["frame"].to_numpy(dtype=np.float64)
    pert = frame.copy()
    pert.iloc[-1, :] = pert.iloc[-1, :] * CONTRACT["perturb"]["factor"]
    moved = _run(tmp_path, pert, steps, tag="b")["frame"].to_numpy(dtype=np.float64)
    assert np.array_equal(base[:-1], moved[:-1], equal_nan=True)


@pytest.mark.parametrize("steps", COMBOS, ids=["+".join(c) for c in COMBOS])
def test_phase2_output_equals_formal_transform_selected(steps: List[str], tmp_path: Path,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """②：IC 頁輸出與同映射之 transform_selected 逐位元組相同（同欄序）；transforms_applied 依正式順序。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame()
    got = _run(tmp_path, frame, steps)
    want = _formal(frame, steps)
    assert list(got["frame"].columns) == list(want.columns)
    assert np.array_equal(got["frame"].to_numpy(dtype=np.float64), want.to_numpy(dtype=np.float64), equal_nan=True)
    assert got["result"]["transforms_applied"] == [s for s in CONTRACT["order"] if s in steps]


def test_phase2_zscore_window_order_insensitive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """③：zscore_windows=[252, 100] 與 [100, 252] 輸出相同（主窗＝最小窗）。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame()
    a = _run(tmp_path, frame, ["zscore"], zscore_windows=[100, 252], tag="z1")["frame"].to_numpy(dtype=np.float64)
    b = _run(tmp_path, frame, ["zscore"], zscore_windows=[252, 100], tag="z2")["frame"].to_numpy(dtype=np.float64)
    assert np.array_equal(a, b, equal_nan=True)


def test_phase2_no_full_sample_rank_and_no_old_order_text() -> None:
    """④⑥：手寫全樣本排名字面與舊順序文案於三落點皆不存在。"""
    service = (REPO / "api/services/ic_analysis_service.py").read_text(encoding="utf-8")
    assert CONTRACT["full_sample_rank_literal"] not in service
    for rel in ("api/models/ic_models.py", "api/services/ic_analysis_service.py", "api/routes/ic_analysis.py"):
        text = (REPO / rel).read_text(encoding="utf-8")
        for phrase in CONTRACT["old_order_phrases"]:
            assert phrase not in text, (rel, phrase)


def test_phase2_selected_features_deduplicated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """⑦：selected_features 含重複名 ⇒ 輸出欄不重複、selected_feature_count＝去重後數（保序）。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame()
    got = _run(tmp_path, frame, ["rank"], selected=["volume", "close", "volume"])
    assert list(got["frame"].columns) == ["volume", "close"]
    assert got["result"]["selected_feature_count"] == 2


# ---------------------------------------------------------------- Task 2.1 邊界

def test_boundary_10_partial_and_total_missing_features(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界①：部分不存在 ⇒ 只轉存在者；全不存在 ⇒ ValueError。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame()
    got = _run(tmp_path, frame, ["rank"], selected=["close", "no_such_col"])
    assert list(got["frame"].columns) == ["close"]
    with pytest.raises(ValueError):
        _run(tmp_path, frame, ["rank"], selected=["no_such_col"], tag="m")


def test_boundary_11_all_switches_off_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界②：三開關全關 ⇒ ValueError（維持現行）。"""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _run(tmp_path, _real_frame(), [])


def test_boundary_12_window_longer_than_rows_all_nan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界③：請求窗 > 資料列數 ⇒ 全 NaN、不拋錯。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame().iloc[:200]
    got = _run(tmp_path, frame, ["rank"])["frame"]
    assert len(got) == 200 and got.isna().all().all()


def test_boundary_13_reversed_time_index_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界④：檔案輸入之 DatetimeIndex 倒序 ⇒ ValueError（不靜默輸出）。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame().iloc[:400].copy()
    frame.index = pd.date_range("2026-01-01", periods=400, freq="h", tz="UTC")[::-1]
    with pytest.raises(ValueError):
        _run(tmp_path, frame, ["rank"])


# ---------------------------------------------------------------- Task 2.2

def test_phase2_ratio_unsafe_excluded_and_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2：混入 1 個 ratio-unsafe 欄 ⇒ 輸出欄數＝選中數−1、excluded_features 恰列該欄（reason 前綴契約）。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame(extra_unsafe=True)
    got = _run(tmp_path, frame, ["rank"])
    assert UNSAFE not in got["frame"].columns and got["frame"].shape[1] == frame.shape[1] - 1
    excluded = got["result"]["excluded_features"]
    assert [e["name"] for e in excluded] == [UNSAFE]
    assert excluded[0]["reason"].startswith(CONTRACT["excluded_reason_prefix"])


def test_phase2_all_ratio_unsafe_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match=re.escape(UNSAFE)):
        _run(tmp_path, _real_frame(extra_unsafe=True), ["rank"], selected=[UNSAFE])


def test_boundary_14_no_unsafe_reports_empty_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 邊界①：無 ratio-unsafe 欄 ⇒ excluded_features == []。"""
    monkeypatch.chdir(tmp_path)
    assert _run(tmp_path, _real_frame(), ["rank"])["result"]["excluded_features"] == []


def test_boundary_15_duplicate_numeric_and_unsafe_counted_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 邊界②：numeric 與 ratio-unsafe 各重複一次 ⇒ 去重後各計一次。"""
    monkeypatch.chdir(tmp_path)
    got = _run(tmp_path, _real_frame(extra_unsafe=True), ["rank"], selected=["close", UNSAFE, "close", UNSAFE])
    assert list(got["frame"].columns) == ["close"]
    assert [e["name"] for e in got["result"]["excluded_features"]] == [UNSAFE]
    assert got["result"]["selected_feature_count"] == 1


def test_phase2_response_model_accepts_excluded_features() -> None:
    """回應 schema 只新增選填欄 excluded_features（既有欄不變）。"""
    from api.models.ic_models import ApplyTransformsResponse

    fields = ApplyTransformsResponse.model_fields
    assert "excluded_features" in fields and not fields["excluded_features"].is_required()
    for name in ("task_id", "selected_feature_count", "transforms_applied", "output_path", "output_rows", "output_cols"):
        assert name in fields


# ---------------------------------------------------------------- mutants（§V；結果須翻轉）

def test_mutation_full_sample_rank_restored_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：IC 頁所呼叫之 transform_selected 改為全樣本排名＋ppf（即手寫版之洩漏）⇒ ①之判準翻轉（前段改變）。"""
    from scipy.stats import norm

    def _leaky(self, selected, groups, config=None):
        return {gid: df[[c for c in selected if c in df.columns]].rank(pct=True, axis=0).clip(0.001, 0.999).apply(norm.ppf)
                for gid, df in groups.items()}

    monkeypatch.setattr(FeaturePreprocessor, "transform_selected", _leaky)
    monkeypatch.chdir(tmp_path)
    frame = _real_frame()
    base = _run(tmp_path, frame, ["gaussian"], tag="la")["frame"].to_numpy(dtype=np.float64)
    pert = frame.copy()
    pert.iloc[-1, :] = pert.iloc[-1, :] * CONTRACT["perturb"]["factor"]
    moved = _run(tmp_path, pert, ["gaussian"], tag="lb")["frame"].to_numpy(dtype=np.float64)
    assert not np.array_equal(base[:-1], moved[:-1], equal_nan=True)


def test_mutation_gaussian_last_order_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：IC 頁所呼叫之 transform_selected 改為 rank→zscore→gaussian 舊順序 ⇒ ②之判準翻轉（與正式順序不等）。"""
    monkeypatch.chdir(tmp_path)
    frame = _real_frame()
    steps = ["rank", "zscore", "gaussian"]
    want = _formal(frame, steps)
    real = FeaturePreprocessor.transform_selected

    def _old_order(self, selected, groups, config=None):
        staged = groups
        for one in (["rank"], ["zscore"], ["gaussian"]):
            cfg = PreprocessingConfig(
                enabled=True, mode="replace", winsorization={"enabled": False},
                fractional_differencing={"enabled": False}, adf_differencing={"enabled": False},
                rank_transform={"enabled": "rank" in one, "window": RANK_W, "apply_to": "all"},
                adaptive_zscore={"enabled": "zscore" in one, "windows": sorted(Z_WINDOWS), "apply_to": "all"},
                gaussian_normalize={"enabled": "gaussian" in one, "apply_to": "all"})
            staged = real(FeaturePreprocessor(cfg.model_dump()), selected, staged, config=cfg)
        return staged

    monkeypatch.setattr(FeaturePreprocessor, "transform_selected", _old_order)
    got = _run(tmp_path, frame, steps)["frame"]
    assert not np.array_equal(got.to_numpy(dtype=np.float64), want.to_numpy(dtype=np.float64), equal_nan=True)


def test_mutation_unsorted_zscore_windows_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：不排序 zscore 窗 ⇒ [252, 100] 與 [100, 252] 之 transform_selected 輸出不同（③之判準有鑑別力）。"""
    frame = _real_frame()

    def _unsorted(windows: List[int]) -> np.ndarray:
        cfg = PreprocessingConfig(
            enabled=True, mode="replace",
            winsorization={"enabled": False}, fractional_differencing={"enabled": False}, adf_differencing={"enabled": False},
            rank_transform={"enabled": False}, gaussian_normalize={"enabled": False},
            adaptive_zscore={"enabled": True, "windows": windows, "apply_to": "all"},
        )
        return FeaturePreprocessor(cfg.model_dump()).transform_selected(list(frame.columns), {"g": frame}, config=cfg)[
            "g"].to_numpy(dtype=np.float64)

    assert not np.array_equal(_unsorted([252, 100]), _unsorted([100, 252]), equal_nan=True)


def test_mutation_excluded_features_not_filled_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：ratio-unsafe 判定失效（IC 頁須經 `feature_preprocessor._is_ratio_unsafe_column` 判定）⇒ excluded_features
    不再列出該欄（Task 2.2 之判準翻轉）。"""
    from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fp

    monkeypatch.setattr(fp, "_is_ratio_unsafe_column", lambda col: False)
    monkeypatch.chdir(tmp_path)
    got = _run(tmp_path, _real_frame(extra_unsafe=True), ["rank"])
    assert [e["name"] for e in got["result"].get("excluded_features", [])] != [UNSAFE]


def test_mutation_dedup_removed_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：移除去重（以 transform_selected 直接吃重複清單）⇒ 輸出欄重複（⑦之判準有鑑別力）。"""
    frame = _real_frame()
    cfg = PreprocessingConfig(
        enabled=True, mode="replace",
        winsorization={"enabled": False}, fractional_differencing={"enabled": False}, adf_differencing={"enabled": False},
        rank_transform={"enabled": True, "window": RANK_W, "apply_to": "all"},
        adaptive_zscore={"enabled": False}, gaussian_normalize={"enabled": False},
    )
    out = FeaturePreprocessor(cfg.model_dump()).transform_selected(["volume", "close", "volume"], {"g": frame}, config=cfg)
    assert list(out["g"].columns) != ["volume", "close"]
