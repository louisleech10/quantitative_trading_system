"""ICPOSTLEAK Phase 1（docs/ICPOSTLEAK_SPEC.md v4）：rank／zscore／gaussian 全分支之窗未滿遮罩、時間序 fail-closed、
既有測試 oracle 更新之機械核對。

設計：
- **逐步驟 oracle**（§G）：依正式順序 rank→gaussian→zscore，每步取上一步 oracle 輸出 → 呼叫該分支之生產數值核心
  （本票不改之函式）→ 以本檔獨立實作之輸入錨點遮罩（`_oracle_mask`；不呼叫生產 `stable_mask`）遮之。
  🔴 實作約束：遮罩須施於**呼叫點**（核心外），核心本身不得內含遮罩——否則 oracle 取到已遮之核心輸出，
  「錨點改用輸出」之 mutant 會存活。
- 真實輸入：`data_cache/feature_klines/kline_cache.h5`（`ffstat_helpers.kline_frame()`）；禁合成 fixture
  （邊界單元測試之最小陣列除外，其值取自真實 kline 切片）。
- 參數單一落點：`tests/_golden/icpostleak/contract.json`。
實作前應為紅（`stable_mask.mask_incomplete_window_by_input_2d`／`time_order.assert_strictly_increasing_time_index`
為 NotImplementedError 空殼、各分支尚未接遮罩）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.preprocessing import stable_mask, time_order
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as h

REPO = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPO / "tests/_golden/icpostleak/contract.json").read_text(encoding="utf-8"))
ORDER: List[str] = CONTRACT["order"]
COMBOS: List[List[str]] = CONTRACT["combos"]
BRANCHES: Dict[str, dict] = CONTRACT["branches"]
RANK_W = int(CONTRACT["rank_window"])
Z_WINDOWS: List[int] = [int(w) for w in CONTRACT["zscore_windows"]]


# ---------------------------------------------------------------- 輸入與設定

def _real_frame() -> pd.DataFrame:
    """§G 輸入集：真實 BTCUSDT 1h 前 3000 根之 close、volume、3 個真實 L1 特徵欄（TA-Lib 於真實 kline 計算，首段 NaN
    為自然暖身），另加人工晚生欄（close 前 400 列 NaN，驗錨點非 0）。"""
    import talib

    k = CONTRACT["kline"]
    base = h.kline_frame(symbol=k["symbol"], timeframe=k["timeframe"]).iloc[: k["rows"]]
    frame = base[k["columns"]].astype(np.float64).copy()
    for spec in k["l1_features"]:
        args = [base[c].to_numpy(dtype=np.float64) for c in spec["inputs"]]
        frame[spec["name"]] = getattr(talib, spec["fn"])(*args, **spec["args"])
    late = frame[k["columns"][0]].copy()
    late.iloc[: k["late_born_nan_rows"]] = np.nan
    frame[k["late_born_column"]] = late
    return frame


def _config(steps: List[str], mode: str = "replace") -> dict:
    return {
        "enabled": True,
        "mode": mode,
        "causal_preprocessing": True,
        "winsorization": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "rank_transform": {"enabled": "rank" in steps, "window": RANK_W, "apply_to": "all"},
        "adaptive_zscore": {"enabled": "zscore" in steps, "windows": list(Z_WINDOWS), "apply_to": "all"},
        "gaussian_normalize": {"enabled": "gaussian" in steps, "apply_to": "all"},
    }


def _set_branch_env(monkeypatch: pytest.MonkeyPatch, branch: str) -> None:
    for key, value in BRANCHES[branch]["env"].items():
        monkeypatch.setenv(key, value)


def _run_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, branch: str, steps: List[str],
                frame: pd.DataFrame, mode: str = "replace", spec_override: Optional[dict] = None) -> pd.DataFrame:
    """以指定分支跑一次生產轉換，回傳輸出（replace 模式欄序同輸入；append 模式含衍生欄、依欄名排序）。
    `spec_override`：非逐組合分支（如 chunked）之設定，形同契約 branches 之一項。"""
    spec_all = dict(BRANCHES.get(branch, {}), **(spec_override or {}))
    for key, value in spec_all.get("env", {}).items():
        monkeypatch.setenv(key, value)
    pre = FeaturePreprocessor(_config(steps, mode))
    if spec_all["entry"] == "transform":
        return pre.transform(frame.copy())
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    spec = spec_all
    if "patch_shard_bytes" in spec:  # 繞過 get_cgsa_shard_bytes 之 32 MiB 下限，使小群組亦分片
        from momentum.FeatureEngineering.utils import hardware_utils

        monkeypatch.setattr(hardware_utils, "get_cgsa_shard_bytes", lambda: int(spec["patch_shard_bytes"]))
    calls: List[str] = []
    if spec.get("spy"):  # 具名分支須真的執行該待測物
        real = getattr(FeaturePreprocessor, spec["spy"])

        def _spy(self, *args, **kwargs):
            calls.append(spec["spy"])
            return real(self, *args, **kwargs)

        monkeypatch.setattr(FeaturePreprocessor, spec["spy"], _spy)
    registry = ColumnGroupRegistry(work_dir=tmp_path / f"registry_{branch}_{'_'.join(steps)}")
    group = ColumnGroup(group_id="1h_L1_icpostleak", layer=LayerSource.L1, timeframe="1h", data_source="close",
                        indicator="ICPOSTLEAK", columns=tuple(frame.columns), shape=(0, 0), dtype="float32",
                        disk_path=None)
    group = registry.save_data(group, frame.to_numpy(dtype=np.float32))
    if "patch_shard_bytes" in spec:
        assert getattr(group, "shards", ()), "前提：群組已分片"
    if spec_all["entry"] == "transform_registry_groups":
        pre.transform_registry_groups(registry, n_workers=int(spec.get("n_workers", 1)))
        if spec.get("spy"):
            assert calls, f"具名分支 {branch} 未執行 {spec['spy']}"
        return pd.DataFrame(registry.load_data(group.group_id), columns=list(frame.columns), index=frame.index)
    # sink 入口（一般／sharded／chunked 由契約 env 切換）：收集各輸出部分，依欄名重組
    parts: Dict[str, np.ndarray] = {}

    def _sink(group_id, columns, data, source_group_id, source_disk_path, cleanup_source) -> None:
        arr = np.asarray(data, dtype=np.float64)
        for i, name in enumerate(columns):
            parts[str(name)] = arr[:, i].copy()

    pre.transform_registry_groups_to_sink(registry, _sink, n_workers=1)
    if spec.get("spy"):
        assert calls, f"具名分支 {branch} 未執行 {spec['spy']}"
    names = [str(c) for c in frame.columns] if mode == "replace" else sorted(parts)
    assert set(names) <= set(parts), sorted(parts)
    return pd.DataFrame({c: parts[c] for c in names}, index=frame.index)


# ---------------------------------------------------------------- 獨立遮罩與 oracle

def _oracle_mask(output: np.ndarray, step_input: np.ndarray, window: int) -> np.ndarray:
    """§C 輸入錨點遮罩之獨立實作（逐欄迴圈；不呼叫生產 stable_mask）。"""
    out = np.array(output, dtype=np.float64, copy=True)
    for j in range(out.shape[1]):
        finite = np.flatnonzero(np.isfinite(step_input[:, j]))
        cut = out.shape[0] if finite.size == 0 else min(int(finite[0]) + int(window) - 1, out.shape[0])
        out[:cut, j] = np.nan
    return out


def _gaussian_window(pre: FeaturePreprocessor) -> int:
    """§C：gaussian 之因果排名窗＝`_rolling_window()`（winsor 窗 → rank 窗 → 252）。"""
    return int(pre._rolling_window())


def _kernel_step(branch: str, pre: FeaturePreprocessor, step: str, values: np.ndarray, columns: List[str]) -> np.ndarray:
    """該分支之單步生產數值核心（未遮罩）。"""
    clip = pre.gaussian_config.get("clip_range", [0.001, 0.999])
    if step == "gaussian":
        w = _gaussian_window(pre)
        return np.asarray(pre._gaussian_2d(values, lower=float(clip[0]), upper=float(clip[1]), causal=True,
                                           window=w, min_periods=pre._rolling_min_periods(w)), dtype=np.float64)
    if branch in ("legacy", "optimized"):
        if step == "rank":
            return np.asarray(pre._rolling_rank_2d_v2(values, RANK_W), dtype=np.float64)
        return np.asarray(pre._rolling_zscore_2d(values, list(Z_WINDOWS), 1e-8, mode="replace"), dtype=np.float64)
    if branch == "polars":
        from momentum.FeatureEngineering.polars_adapter import (
            pandas_to_polars,
            polars_l65_adaptive_zscore,
            polars_l65_rank_transform,
            polars_to_pandas,
        )

        # 同生產入口之轉換（float32＋NaN→null；`_transform_single_polars` 經 pandas_to_polars）
        pl_df = pandas_to_polars(pd.DataFrame(values, columns=columns))
        if step == "rank":
            pl_df = polars_l65_rank_transform(pl_df, columns=columns, window=RANK_W)
        else:
            pl_df = polars_l65_adaptive_zscore(pl_df, columns=columns, window=Z_WINDOWS[0], epsilon=1e-8)
        return polars_to_pandas(pl_df)[columns].to_numpy(dtype=np.float64)
    from momentum.FeatureEngineering.preprocessing._numba_transforms import transform_array_fast

    return np.asarray(transform_array_fast(values.astype(np.float32), winsorize=False, rank=step == "rank",
                                           rank_window=RANK_W, zscore=step == "zscore",
                                           zscore_window=Z_WINDOWS[0]), dtype=np.float64)


def _step_window(pre: FeaturePreprocessor, step: str) -> int:
    return RANK_W if step == "rank" else (_gaussian_window(pre) if step == "gaussian" else Z_WINDOWS[0])


def _polars_roundtrip(values: np.ndarray, columns: List[str]) -> np.ndarray:
    """Polars 臂之每次 pandas↔polars 往返（`pandas_to_polars`：float32＋NaN→null；`polars_to_pandas`）。"""
    from momentum.FeatureEngineering.polars_adapter import pandas_to_polars, polars_to_pandas

    return polars_to_pandas(pandas_to_polars(pd.DataFrame(values, columns=columns)))[columns].to_numpy(dtype=np.float64)


def _oracle(branch: str, steps: List[str], frame: pd.DataFrame) -> np.ndarray:
    """逐步驟 oracle。Polars 分支重放 `_transform_single_polars` 之轉換序：入口 `pandas_to_polars`（float32＋null）、
    gaussian 前後各一次 pandas↔polars 往返（`_apply_gaussian_normalize` 回落）、出口 `polars_to_pandas`。"""
    pre = FeaturePreprocessor(_config(steps))
    columns = [str(c) for c in frame.columns]
    values = frame.to_numpy(dtype=np.float64)
    if branch == "polars":
        values = _polars_roundtrip(values, columns)
    elif branch.startswith("registry"):
        values = _f32(values)  # registry `save_data(..., float32)` 入口
    for step in ORDER:
        if step not in steps:
            continue
        values = _oracle_mask(_kernel_step(branch, pre, step, values, columns), values, _step_window(pre, step))
        if branch == "polars":
            values = _polars_roundtrip(values, columns)  # 每步結果回存 polars（float32）
        elif branch.startswith("registry"):
            values = _f32(values)  # registry 群組陣列為 float32，每步結果回存（sink 出口亦 cast float32）
    return values


def _f32(values: np.ndarray) -> np.ndarray:
    """float32 取整後回 float64 比較（registry 落盤／群組陣列之 dtype）。"""
    return np.asarray(values, dtype=np.float32).astype(np.float64)


def _first_finite(arr: np.ndarray) -> List[int]:
    return [int(np.argmax(np.isfinite(arr[:, j]))) if np.isfinite(arr[:, j]).any() else -1 for j in range(arr.shape[1])]


def _expected_first_finite(frame: pd.DataFrame, steps: List[str]) -> List[int]:
    """純整數公式：輸入首個有限值 ＋ Σ(各啟用步驟窗 − 1)（正式順序）；超過列數 ⇒ −1（全 NaN）。"""
    pre = FeaturePreprocessor(_config(steps))
    add = sum(_step_window(pre, s) - 1 for s in ORDER if s in steps)
    out = []
    for first in _first_finite(frame.to_numpy(dtype=np.float64)):
        cut = first + add if first >= 0 else -1
        out.append(cut if 0 <= cut < len(frame) else -1)
    return out


# ---------------------------------------------------------------- Phase 1 驗證（Task 1.1）

@pytest.mark.parametrize("branch", list(BRANCHES))
@pytest.mark.parametrize("steps", COMBOS, ids=["+".join(c) for c in COMBOS])
def test_phase1_stepwise_oracle_bytes_equal(branch: str, steps: List[str], tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    """§G ①②：每分支 × 七組合，輸出與該分支逐步驟 oracle 逐位元組相同（含 NaN 位置），首個有限值列＝整數公式。"""
    frame = _real_frame()
    got = _run_branch(monkeypatch, tmp_path, branch, steps, frame).to_numpy(dtype=np.float64)
    want = _oracle(branch, steps, frame)
    assert got.shape == want.shape
    assert np.isfinite(want).sum() > 0, "前提：遮罩後仍有可比之有限值"
    assert _first_finite(got) == _expected_first_finite(frame, steps)
    assert np.array_equal(got, want, equal_nan=True), (branch, steps)


@pytest.mark.parametrize("steps", COMBOS, ids=["+".join(c) for c in COMBOS])
def test_phase1_branch_parity_mask_positions(steps: List[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.1 ②：四分支之逐欄首個有限值列完全相同（數值依分支各自 oracle，見上）。"""
    frame = _real_frame()
    firsts = {}
    for branch in BRANCHES:
        with monkeypatch.context() as mp:
            firsts[branch] = _first_finite(_run_branch(mp, tmp_path, branch, steps, frame).to_numpy(dtype=np.float64))
    assert len({tuple(v) for v in firsts.values()}) == 1, firsts


@pytest.mark.parametrize("branch", ["polars", "legacy"])
def test_phase1_append_mode_each_window_masked(branch: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G ②（append）：zscore 窗 [100, 252] 之每個衍生欄各自自輸入首個有限值起遮 `窗−1` 列。"""
    frame = _real_frame()
    got = _run_branch(monkeypatch, tmp_path, branch, ["zscore"], frame, mode="append")
    columns = [str(c) for c in frame.columns]
    values = frame.to_numpy(dtype=np.float64)
    if branch == "polars":  # append 回落 pandas：入口與回存各一次 float32 往返
        values = _polars_roundtrip(values, columns)
    by_window = FeaturePreprocessor(_config(["zscore"], "append"))._rolling_zscore_2d(values, list(Z_WINDOWS), 1e-8,
                                                                                       mode="append")
    for window in Z_WINDOWS:
        cols = [f"{c}_zscore_{window}" for c in frame.columns]
        assert all(c in got.columns for c in cols), (window, list(got.columns))
        want = _oracle_mask(np.asarray(by_window[window], dtype=np.float64), values, window)
        if branch == "polars":
            want = _polars_roundtrip(want, cols)
        actual = got[cols].to_numpy(dtype=np.float64)
        assert _first_finite(actual) == [f + window - 1 for f in _first_finite(values)], window
        assert np.array_equal(actual, want, equal_nan=True), window  # 全陣列：成熟區段之值亦逐位元組比


def test_phase1_registry_chunked_append_masked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.1（registry chunked）：`_stream_single_group_chunked_to_sink` 只於 requires_slow（append 模式）觸發，
    每塊呼叫 `_transform_single`（legacy；append 停用 optimized）⇒ 以 append＋split 門檻 2 實跑，spy 證明執行該待測物，
    各窗衍生欄與 legacy append oracle 全陣列逐位元組相同。"""
    cfg = CONTRACT["registry_chunked_append"]
    frame = _real_frame()
    got = _run_branch(monkeypatch, tmp_path, "registry_chunked", cfg["steps"], frame, mode=cfg["mode"],
                      spec_override={"env": cfg["env"], "entry": "transform_registry_groups_to_sink", "spy": cfg["spy"]})
    values = _f32(frame.to_numpy(dtype=np.float64))  # registry `save_data(..., float32)` 入口
    by_window = FeaturePreprocessor(_config(cfg["steps"], "append"))._rolling_zscore_2d(values, list(Z_WINDOWS), 1e-8,
                                                                                         mode="append")
    for window in Z_WINDOWS:
        cols = [f"{c}_zscore_{window}" for c in frame.columns]
        assert all(c in got.columns for c in cols), (window, list(got.columns))
        want = _f32(_oracle_mask(np.asarray(by_window[window], dtype=np.float64), values, window))  # sink 出口 float32
        assert np.array_equal(got[cols].to_numpy(dtype=np.float64), want, equal_nan=True), window


@pytest.mark.parametrize("branch", list(BRANCHES))
def test_phase1_causal_perturb_last_row(branch: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.1 ③：最後一列 ×50 ⇒ 前 2999 列逐位元組不變（三項全開）。"""
    frame = _real_frame()
    steps = ["rank", "zscore", "gaussian"]
    base = _run_branch(monkeypatch, tmp_path, branch, steps, frame).to_numpy(dtype=np.float64)
    pert = frame.copy()
    pert.iloc[CONTRACT["perturb"]["row"], :] = pert.iloc[CONTRACT["perturb"]["row"], :] * CONTRACT["perturb"]["factor"]
    moved = _run_branch(monkeypatch, tmp_path, branch, steps, pert).to_numpy(dtype=np.float64)
    assert np.array_equal(base[:-1], moved[:-1], equal_nan=True)


# ---------------------------------------------------------------- Task 1.1 邊界

def test_boundary_01_all_nan_column_stays_nan() -> None:
    """邊界①：步驟輸入全 NaN 之欄 ⇒ 輸出全 NaN、不拋錯。"""
    real = _real_frame()["close"].to_numpy(dtype=np.float64)[:600]
    inp = np.column_stack([real, np.full_like(real, np.nan)])
    out = stable_mask.mask_incomplete_window_by_input_2d(inp.copy(), inp, 100)
    assert np.isnan(out[:, 1]).all()
    assert np.isnan(out[:99, 0]).all() and np.isfinite(out[99:, 0]).all()


def test_boundary_02_late_born_column_anchor_at_its_first_finite() -> None:
    """邊界②：晚生欄 ⇒ 錨點自該欄首個有限值起算（非第 0 列）。"""
    real = _real_frame()["close"].to_numpy(dtype=np.float64)[:800]
    late = real.copy()
    late[:400] = np.nan
    inp = np.column_stack([real, late])
    out = stable_mask.mask_incomplete_window_by_input_2d(inp.copy(), inp, 100)
    assert _first_finite(out) == [99, 499]


def test_boundary_03_rows_fewer_than_window_all_nan() -> None:
    """邊界③：列數 < window ⇒ 全 NaN、不拋錯。"""
    real = _real_frame()[["close", "volume"]].to_numpy(dtype=np.float64)[:50]
    out = stable_mask.mask_incomplete_window_by_input_2d(real.copy(), real, 100)
    assert out.shape == real.shape and np.isnan(out).all()


def test_boundary_04_chain_first_finite_accumulates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界④：rank→gaussian→zscore 鏈式之首個有限值列＝輸入首個有限值＋Σ(窗−1)（legacy 分支實跑）。"""
    frame = _real_frame()
    steps = ["rank", "zscore", "gaussian"]
    got = _run_branch(monkeypatch, tmp_path, "legacy", steps, frame).to_numpy(dtype=np.float64)
    expected = _expected_first_finite(frame, steps)
    assert expected[0] == 0 + (RANK_W - 1) + (RANK_W - 1) + (Z_WINDOWS[0] - 1)
    assert _first_finite(got) == expected


def test_boundary_05_zscore_constant_window_keeps_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界⑤：zscore 常數窗（std＝0）於遮罩後區段沿用現行 `where(std > 0, 0)` ⇒ 0.0（非 NaN、非 inf）。"""
    frame = _real_frame()[["close"]].iloc[:600].copy()
    frame.iloc[300:, 0] = float(frame.iloc[299, 0])  # 真實值延續成常數段
    got = _run_branch(monkeypatch, tmp_path, "legacy", ["zscore"], frame).to_numpy(dtype=np.float64)[:, 0]
    assert np.isnan(got[: Z_WINDOWS[0] - 1]).all()
    assert (got[300 + Z_WINDOWS[0]:] == 0.0).all()


# ---------------------------------------------------------------- Task 1.2 時間序

def _dt_frame(index: pd.DatetimeIndex) -> pd.DataFrame:
    real = _real_frame()["close"].to_numpy(dtype=np.float64)[: len(index)]
    return pd.DataFrame({"close": real}, index=index)


@pytest.mark.parametrize("case", ["reverse", "duplicate", "single_disorder"])
def test_time_order_non_increasing_raises(case: str) -> None:
    """Task 1.2：倒序／重複／單點亂序 ⇒ ValueError，訊息含首個違規位置。"""
    idx = pd.date_range("2026-01-01", periods=300, freq="h", tz="UTC")
    if case == "reverse":
        idx, pos = idx[::-1], 1
    elif case == "duplicate":
        idx, pos = idx.insert(150, idx[149]), 150
    else:
        values = list(idx)
        values[200], values[201] = values[201], values[200]
        idx, pos = pd.DatetimeIndex(values), 201
    frame = _dt_frame(idx)
    with pytest.raises(ValueError, match=rf"\b{pos}\b"):
        FeaturePreprocessor(_config(["rank"])).transform(frame)


def test_time_order_strictly_increasing_ok() -> None:
    idx = pd.date_range("2026-01-01", periods=300, freq="h", tz="UTC")
    FeaturePreprocessor(_config(["rank"])).transform(_dt_frame(idx))


def test_boundary_06_range_index_not_checked() -> None:
    """Task 1.2 邊界①：RangeIndex（L7 raw 讀回）不檢、不拋。"""
    time_order.assert_strictly_increasing_time_index(pd.RangeIndex(10)[::-1], where="test")


def test_boundary_07_length_zero_one_no_raise() -> None:
    """Task 1.2 邊界②：長度 0／1 不拋。"""
    for n in (0, 1):
        time_order.assert_strictly_increasing_time_index(
            pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC"), where="test")


# ---------------------------------------------------------------- Task 1.3 既有測試 oracle 更新之機械核對

def _grep_oracle_files() -> List[str]:
    rule = CONTRACT["oracle_update_grep"]
    proc = subprocess.run(["grep", "-rlE", rule["regex_ere"], rule["root"], f"--include={rule['include']}"],
                          cwd=REPO, capture_output=True, text=True, check=False)
    files = sorted(p for p in proc.stdout.splitlines() if p and p not in rule["exclude_self"])
    return files


def test_boundary_08_oracle_update_files_keep_assertions() -> None:
    """Task 1.3 邊界①：受影響測試檔清單＝重產 grep；各檔斷言類行數不少於凍結值（退役須於契約逐條登記理由）。"""
    assert _grep_oracle_files() == sorted(CONTRACT["oracle_update_files"])
    pat = re.compile(CONTRACT["oracle_update_counts_rule"]["assert_regex_ere"])
    retired = CONTRACT.get("oracle_update_retired", {})
    for path, frozen in CONTRACT["oracle_update_counts_frozen"].items():
        lines = (REPO / path).read_text(encoding="utf-8").splitlines()
        now = sum(1 for line in lines if pat.search(line))
        assert now + len(retired.get(path, [])) >= frozen["assert_like"], (path, now, frozen)


def test_boundary_09_oracle_update_files_add_no_skip_or_xfail() -> None:
    """Task 1.3 邊界②：受影響測試檔之 skip／xfail 行數不多於凍結值（fixture 過短須加大列數，不得暫避）。"""
    pat = re.compile(CONTRACT["oracle_update_counts_rule"]["skip_regex_ere"])
    for path, frozen in CONTRACT["oracle_update_counts_frozen"].items():
        lines = (REPO / path).read_text(encoding="utf-8").splitlines()
        assert sum(1 for line in lines if pat.search(line)) <= frozen["skip_xfail"], path


# ---------------------------------------------------------------- mutants（§V；結果須翻轉）

def _identity(output, step_input, window):
    return np.array(output, copy=True)


def _anchor_on_output(output, step_input, window):
    return _oracle_mask(output, output, window)


def _window_minus_two(output, step_input, window):
    return _oracle_mask(output, step_input, int(window) - 2)


@pytest.mark.parametrize("branch", list(BRANCHES))
def test_mutation_mask_identity_is_caught(branch: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：遮罩 identity（逐分支各一）⇒ 該分支輸出 ≠ oracle。"""
    monkeypatch.setattr(stable_mask, "mask_incomplete_window_by_input_2d", _identity)
    frame = _real_frame()
    got = _run_branch(monkeypatch, tmp_path, branch, ["rank"], frame).to_numpy(dtype=np.float64)
    assert not np.array_equal(got, _oracle(branch, ["rank"], frame), equal_nan=True)


@pytest.mark.parametrize("mutant", [_anchor_on_output, _window_minus_two], ids=["anchor_on_output", "window_minus_two"])
def test_mutation_mask_anchor_or_window_is_caught(mutant: Callable, tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：錨點改用輸出首個有限值／窗改 `window−2` ⇒ 首個有限值列 ≠ 整數公式（rank→gaussian，legacy）。"""
    monkeypatch.setattr(stable_mask, "mask_incomplete_window_by_input_2d", mutant)
    frame = _real_frame()
    steps = ["rank", "gaussian"]
    got = _run_branch(monkeypatch, tmp_path, "legacy", steps, frame).to_numpy(dtype=np.float64)
    assert _first_finite(got) != _expected_first_finite(frame, steps)


def test_mutation_append_masks_first_window_only_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：append 模式只遮第一個 zscore 窗 ⇒ 第二窗衍生欄首個有限值列 ≠ 輸入首個有限值＋窗−1。"""
    real = stable_mask.mask_incomplete_window_by_input_2d

    def _first_window_only(output, step_input, window):
        return real(output, step_input, window) if int(window) == Z_WINDOWS[0] else np.array(output, copy=True)

    monkeypatch.setattr(stable_mask, "mask_incomplete_window_by_input_2d", _first_window_only)
    frame = _real_frame()
    got = _run_branch(monkeypatch, tmp_path, "legacy", ["zscore"], frame, mode="append")
    cols = [c for c in got.columns if str(c).endswith(f"_zscore_{Z_WINDOWS[1]}")]
    inputs = _first_finite(frame.to_numpy(dtype=np.float64))
    assert _first_finite(got[cols].to_numpy(dtype=np.float64)) != [f + Z_WINDOWS[1] - 1 for f in inputs]


def test_mutation_parallel_slice_skips_gaussian_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：切片並行路徑回到改前（融合核心、無 gaussian 後置、無遮罩）⇒ registry_parallel_split 輸出 ≠ oracle。"""

    def _old_slice(self, array_slice, transform_context):
        fast = transform_context["transform_array_fast"]
        return fast(np.ascontiguousarray(array_slice, dtype=np.float32),
                    winsorize=bool(transform_context.get("do_winsorize", True)),
                    rank=bool(transform_context.get("do_rank", False)),
                    rank_window=int(transform_context.get("rank_window", 252)),
                    zscore=bool(transform_context.get("do_zscore", False)),
                    zscore_window=int(transform_context.get("zscore_window", 100)))

    monkeypatch.setattr(FeaturePreprocessor, "_transform_array_slice", _old_slice)
    frame = _real_frame()
    steps = ["gaussian"]
    spec = dict(BRANCHES["registry_parallel_split"])
    spec.pop("spy", None)
    got = _run_branch(monkeypatch, tmp_path, "registry_parallel_split", steps, frame,
                      spec_override=spec).to_numpy(dtype=np.float64)
    assert not np.array_equal(got, _oracle("registry_parallel_split", steps, frame), equal_nan=True)


def test_mutation_time_order_check_removed_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：移除時間序檢查 ⇒ 倒序輸入不再拋錯（入口須經 `time_order.assert_strictly_increasing_time_index` 呼叫）。"""
    monkeypatch.setattr(time_order, "assert_strictly_increasing_time_index", lambda index, *, where: None)
    idx = pd.date_range("2026-01-01", periods=300, freq="h", tz="UTC")[::-1]
    FeaturePreprocessor(_config(["rank"])).transform(_dt_frame(idx))  # 不拋 ⇒ 正常版之 raises 測試為可證偽
