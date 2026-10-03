"""RATIOUNSAFE Phase 2／Task 3.1（docs/RATIOUNSAFE_SPEC.md v5）：L6.5 registry 兩入口全分支跳過 ratio-unsafe 欄、
append 臂、校準順序、native 強制臂、§G S1 落盤路徑基準、`transform_selected` 契約。

- 分支強制：參數單一落點 `tests/_golden/ratiounsafe/contract.json` 之 `branches`（沿用 ICPOSTLEAK contract 之 env／spy 鍵）。
- 非 ratio-unsafe 欄之 oracle＝同一分支、同設定、**只含非 ratio-unsafe 欄**之群組之輸出（逐位元組）；
  ratio-unsafe 欄之 oracle＝輸入（registry 以 float32 儲存）。
- 真實輸入：`data_cache/feature_klines/kline_cache.h5`（TA-Lib 於真實 kline 計算）；禁合成 fixture。
- §G：`scripts/freeze_ratiounsafe_baseline.py`（動工前 `--stage before` 產 `baseline.json`；Task 2.1 驗收、使用者核可後
  `--stage after` 產 `baseline_after.json`）。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering import feature_naming as fn
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import ffstat_helpers as h

REPO = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPO / "tests/_golden/ratiounsafe/contract.json").read_text(encoding="utf-8"))
BRANCHES: Dict[str, dict] = CONTRACT["branches"]
UNSAFE = [c["name"] for c in CONTRACT["branch_columns"]["unsafe"]]
SAFE = [c["name"] for c in CONTRACT["branch_columns"]["safe"]]

_spec = importlib.util.spec_from_file_location("freeze_ratiounsafe_baseline",
                                               REPO / "scripts/freeze_ratiounsafe_baseline.py")
freeze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(freeze)


# ---------------------------------------------------------------- 輸入與分支執行

def _branch_frame(columns: Optional[List[str]] = None) -> pd.DataFrame:
    import talib

    k = CONTRACT["branch_kline"]
    base = h.kline_frame(symbol=k["symbol"], timeframe=k["timeframe"]).iloc[: k["rows"]]
    o, hi, lo, c = (base[x].to_numpy(dtype=np.float64) for x in ("open", "high", "low", "close"))
    data = {}
    for spec in CONTRACT["branch_columns"]["unsafe"]:
        data[spec["name"]] = getattr(talib, spec["fn"])(o, hi, lo, c).astype(np.float64)
    for spec in CONTRACT["branch_columns"]["safe"]:
        data[spec["name"]] = getattr(talib, spec["fn"])(c, **spec["args"])
    frame = pd.DataFrame(data, index=base.index)
    return frame[columns] if columns else frame


def _config(mode: str = "replace", zscore: Optional[List[int]] = None, fracdiff: bool = False) -> dict:
    return {
        "enabled": True, "mode": mode, "causal_preprocessing": True,
        "winsorization": {"enabled": True, "method": "quantile", "quantile_range": [0.01, 0.99], "window": 252,
                          "apply_to": "all"},
        "fractional_differencing": {"enabled": bool(fracdiff)},
        "adf_differencing": {"enabled": False},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": bool(zscore), "windows": list(zscore or [100]), "apply_to": "all"},
        "gaussian_normalize": {"enabled": False},
    }


def _registry_with(tmp_path: Path, frame: pd.DataFrame, group_id: str, tf: str = "12h"):
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    registry = ColumnGroupRegistry(work_dir=tmp_path / f"registry_{group_id}")
    group = ColumnGroup(group_id=group_id, layer=LayerSource.L1, timeframe=tf, data_source="ohlc",
                        indicator="RATIOUNSAFE", columns=tuple(frame.columns), shape=(0, 0), dtype="float32",
                        disk_path=None)
    group = registry.save_data(group, frame.to_numpy(dtype=np.float32))
    return registry, group


def _run_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, branch: str, frame: pd.DataFrame,
                cfg: Optional[dict] = None, mode: str = "replace", tag: str = "g",
                sink_log: Optional[list] = None) -> pd.DataFrame:
    spec = BRANCHES[branch]
    for key, value in spec.get("env", {}).items():
        monkeypatch.setenv(key, value)
    if "patch_shard_bytes" in spec:
        from momentum.FeatureEngineering.utils import hardware_utils

        monkeypatch.setattr(hardware_utils, "get_cgsa_shard_bytes", lambda: int(spec["patch_shard_bytes"]))
    calls: List[str] = []
    if spec.get("spy"):
        real = getattr(FeaturePreprocessor, spec["spy"])

        def _spy(self, *args, **kwargs):
            calls.append(spec["spy"])
            return real(self, *args, **kwargs)

        monkeypatch.setattr(FeaturePreprocessor, spec["spy"], _spy)
    pre = FeaturePreprocessor(cfg or _config(mode))
    registry, group = _registry_with(tmp_path / f"{branch}_{tag}", frame, f"12h_L1_ratiounsafe_{tag}")
    if spec["entry"] == "transform_registry_groups":
        pre.transform_registry_groups(registry, n_workers=int(spec.get("n_workers", 1)))
        out = pd.DataFrame(registry.load_data(group.group_id), columns=list(frame.columns), index=frame.index)
    else:
        parts: Dict[str, np.ndarray] = {}

        def _sink(group_id, columns, data, source_group_id, source_disk_path, cleanup_source) -> None:
            if sink_log is not None:
                sink_log.append((str(group_id), tuple(str(c) for c in columns)))
            arr = np.asarray(data, dtype=np.float64)
            for i, name in enumerate(columns):
                parts[str(name)] = arr[:, i].copy()

        pre.transform_registry_groups_to_sink(registry, _sink, n_workers=1)
        names = list(frame.columns) if mode == "replace" else sorted(parts)
        out = pd.DataFrame({c: parts[c] for c in names}, index=frame.index)
    if spec.get("spy"):
        assert calls, f"具名分支 {branch} 未執行 {spec['spy']}"
    return out


def _as_stored(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(np.float32).astype(np.float64)


BRANCH_IDS = sorted(BRANCHES)


# ---------------------------------------------------------------- Task 2.1：逐分支

@pytest.mark.parametrize("branch", BRANCH_IDS)
def test_mixed_group_unsafe_passthrough_safe_unchanged(branch: str, tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    mixed = _run_branch(monkeypatch, tmp_path, branch, _branch_frame(), tag="mixed")
    safe_only = _run_branch(monkeypatch, tmp_path, branch, _branch_frame(SAFE), tag="safe")
    stored = _as_stored(_branch_frame())
    for col in UNSAFE:
        assert np.array_equal(mixed[col].to_numpy(), stored[col].to_numpy(), equal_nan=True), col
    for col in SAFE:
        assert np.array_equal(mixed[col].to_numpy(), safe_only[col].to_numpy(), equal_nan=True), col


@pytest.mark.parametrize("branch", BRANCH_IDS)
def test_boundary_01_all_unsafe_group_passthrough_and_sink_complete(branch: str, tmp_path: Path,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界①：全 ratio-unsafe 群組 ⇒ 無轉換、run 完成且輸出收齊全部欄。"""
    frame = _branch_frame(UNSAFE)
    out = _run_branch(monkeypatch, tmp_path, branch, frame, tag="allunsafe")
    assert list(out.columns) == UNSAFE
    assert np.array_equal(out.to_numpy(), _as_stored(frame).to_numpy(), equal_nan=True)


def test_boundary_02_compact_native_passthrough_expands_to_primary_rows(tmp_path: Path,
                                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界②＋native 強制臂：compact-aligned 混合群組經 to_sink，確實走 native；ratio-unsafe 欄展開後＝原值展開，
    列數＝主週期列數；非 ratio-unsafe 欄＝同設定只含非 ratio-unsafe 欄之 native 輸出。"""
    from tests.feature_engineering.preprocessing.test_l65_native_tf import _make_compact_registry, _make_idx_map_uniform

    arm = CONTRACT["native_arm"]
    for key, value in arm["env"].items():
        monkeypatch.setenv(key, value)
    calls: List[object] = []
    real_native = FeaturePreprocessor._maybe_run_native_l65_to_sink

    def _spy(self, *args, **kwargs):
        result = real_native(self, *args, **kwargs)
        calls.append(result)
        return result

    monkeypatch.setattr(FeaturePreprocessor, "_maybe_run_native_l65_to_sink", _spy)

    def _run(columns: List[str], sub: str) -> Dict[str, np.ndarray]:
        frame = _branch_frame(columns)
        source = frame.to_numpy(dtype=np.float32)
        idx_map = _make_idx_map_uniform(source.shape[0], int(arm["ratio"]))
        registry = _make_compact_registry(tmp_path / sub, source=source, idx_map=idx_map, columns=tuple(columns))
        parts: Dict[str, np.ndarray] = {}

        def _sink(group_id, cols, data, *rest) -> None:
            arr = np.asarray(data, dtype=np.float64)
            for i, name in enumerate(cols):
                parts[str(name)] = arr[:, i].copy()

        FeaturePreprocessor(_config()).transform_registry_groups_to_sink(registry, _sink, n_workers=1)
        return {"parts": parts, "idx_map": idx_map, "source": source}

    mixed = _run(UNSAFE + SAFE, "mixed")
    assert calls and calls[-1] is not None, "未走 native 分支"
    safe_only = _run(SAFE, "safe")
    n_primary = len(mixed["idx_map"])
    for j, col in enumerate(UNSAFE):
        expanded = mixed["source"][mixed["idx_map"], j].astype(np.float64)
        assert mixed["parts"][col].shape[0] == n_primary
        assert np.array_equal(mixed["parts"][col], expanded, equal_nan=True), col
    for col in SAFE:
        assert np.array_equal(mixed["parts"][col], safe_only["parts"][col], equal_nan=True), col


@pytest.mark.parametrize("branch", ["registry_sink_sharded", "registry_chunked"])
def test_boundary_03_shard_structure_unchanged(branch: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界③：全 ratio-unsafe 群組之 sink 呼叫結構（輸出群組名序列、各次欄名）＝同形非 ratio-unsafe 群組。"""
    log_u: list = []
    log_s: list = []
    unsafe_frame = _branch_frame(UNSAFE)
    safe_frame = _branch_frame(SAFE)
    safe_frame.columns = [f"close_trend_SHAPE_{i}" for i in range(len(SAFE))]
    _run_branch(monkeypatch, tmp_path, branch, unsafe_frame, tag="shape", sink_log=log_u)
    _run_branch(monkeypatch, tmp_path / "s", branch, safe_frame, tag="shape", sink_log=log_s)
    assert [g for g, _ in log_u] == [g for g, _ in log_s]
    assert [len(c) for _, c in log_u] == [len(c) for _, c in log_s]


def test_append_arm_no_unsafe_derivatives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    arm = CONTRACT["append_arm"]
    cfg = _config(mode="append", zscore=arm["zscore_windows"])
    mixed = _run_branch(monkeypatch, tmp_path, arm["branch"], _branch_frame(), cfg=cfg, mode="append", tag="app")
    safe_only = _run_branch(monkeypatch, tmp_path, arm["branch"], _branch_frame(SAFE), cfg=cfg, mode="append",
                            tag="appsafe")
    derived_unsafe = [c for c in mixed.columns if any(c.startswith(u + "_") for u in UNSAFE)]
    assert derived_unsafe == []
    stored = _as_stored(_branch_frame())
    for col in UNSAFE:
        assert np.array_equal(mixed[col].to_numpy(), stored[col].to_numpy(), equal_nan=True), col
    assert set(safe_only.columns) <= set(mixed.columns)
    for col in safe_only.columns:
        assert np.array_equal(mixed[col].to_numpy(), safe_only[col].to_numpy(), equal_nan=True), col


# ---------------------------------------------------------------- 校準順序

def _packet(frame: pd.DataFrame, tf: str, n: int, output_start: pd.Timestamp):
    from momentum.FeatureEngineering.preprocessing import calibration as cal

    before = frame.loc[frame.index < output_start]
    values = {fn.tag_timeframe(c, tf): before[c].dropna().to_numpy(dtype=np.float64)[-n:] for c in frame.columns}
    last = {fn.tag_timeframe(c, tf): before[c].dropna().index[-1] for c in frame.columns}
    key = cal.CalibrationKey(symbol="BTCUSDT", timeframe=tf, output_start=output_start, config_hash="ratiounsafe",
                             n=n, column_set_digest=cal.column_set_digest(sorted(values)))
    return cal.CalibrationPacket(key=key, values=values, last_calibration_ts=last,
                                 calibration_source_sha256="ratiounsafe-test")


def _calibrated_run(tmp_path: Path, extra_columns_in_prepare: bool, captured: list,
                    monkeypatch: pytest.MonkeyPatch):
    from momentum.FeatureEngineering.preprocessing import calibration as cal

    k = CONTRACT["branch_kline"]
    full = _branch_frame()
    pre = FeaturePreprocessor(_config(fracdiff=True))
    n = pre._stationarity_n_for(k["timeframe"])
    first_valid = int(np.max([np.flatnonzero(full[c].notna().to_numpy())[0] for c in full.columns]))
    output_start = full.index[first_valid + n]
    packet = _packet(full, k["timeframe"], n, output_start)
    safe_tagged = sorted(fn.tag_timeframe(c, k["timeframe"]) for c in SAFE)
    pre.set_calibration({k["timeframe"]: cal.restrict_packet(packet, safe_tagged)}, symbol="BTCUSDT",
                        output_start=output_start, config_hash="ratiounsafe")
    real_prepare = FeaturePreprocessor._prepare_calibration

    def _spy(self, columns_by_timeframe):
        snapshot = {tf: sorted(map(str, cols)) for tf, cols in columns_by_timeframe.items()}
        captured.append(snapshot)
        if extra_columns_in_prepare:  # mutant：分類晚於校準準備 ⇒ ratio-unsafe 欄進入準備欄集合
            columns_by_timeframe = {tf: sorted(set(cols) | set(UNSAFE)) for tf, cols in snapshot.items()}
        return real_prepare(self, columns_by_timeframe)

    monkeypatch.setattr(FeaturePreprocessor, "_prepare_calibration", _spy)
    public = full.loc[full.index >= output_start]
    registry, _ = _registry_with(tmp_path, public, "12h_L1_ratiounsafe_cal")
    parts: Dict[str, np.ndarray] = {}

    def _sink(group_id, columns, data, *rest) -> None:
        arr = np.asarray(data, dtype=np.float64)
        for i, name in enumerate(columns):
            parts[str(name)] = arr[:, i].copy()

    pre.transform_registry_groups_to_sink(registry, _sink, n_workers=1)
    return public, parts


def test_calibration_excludes_unsafe_before_prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list = []
    public, parts = _calibrated_run(tmp_path, False, captured, monkeypatch)
    assert captured, "未呼叫 _prepare_calibration"
    assert not any(set(UNSAFE) & set(cols) for snap in captured for cols in snap.values())
    stored = _as_stored(public)
    for col in UNSAFE:
        assert np.array_equal(parts[col], stored[col].to_numpy(), equal_nan=True), col


def test_mutation_late_classification_fails_with_safe_only_packet(tmp_path: Path,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    with pytest.raises(CalibrationError):
        _calibrated_run(tmp_path, True, [], monkeypatch)


# ---------------------------------------------------------------- mutant：跳過判定

def test_mutation_skip_never_alters_unsafe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant②：跳過判定恆 False ⇒ ratio-unsafe 欄被轉換（與輸入不等）。"""
    monkeypatch.setattr(fn, "ratio_unsafe_category", lambda column: None)
    out = _run_branch(monkeypatch, tmp_path, "registry_sink", _branch_frame(), tag="mutF")
    stored = _as_stored(_branch_frame())
    assert not all(np.array_equal(out[c].to_numpy(), stored[c].to_numpy(), equal_nan=True) for c in UNSAFE)


def test_mutation_skip_always_leaves_safe_untransformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant③：跳過判定恆 True ⇒ 非 ratio-unsafe 欄亦原值（與只含非 ratio-unsafe 欄之轉換輸出不等）。"""
    safe_only = _run_branch(monkeypatch, tmp_path, "registry_sink", _branch_frame(SAFE), tag="mutTs")
    monkeypatch.setattr(fn, "ratio_unsafe_category", lambda column: "pattern")
    out = _run_branch(monkeypatch, tmp_path, "registry_sink", _branch_frame(), tag="mutT")
    assert not all(np.array_equal(out[c].to_numpy(), safe_only[c].to_numpy(), equal_nan=True) for c in SAFE)


# ---------------------------------------------------------------- §G S1 落盤路徑（生產入口，經 generate_features）

@pytest.fixture(scope="module")
def before() -> dict:
    return json.loads((REPO / "tests/_golden/ratiounsafe/baseline.json").read_text(encoding="utf-8"))


def _is_unsafe(col: str) -> bool:
    return fn.is_ratio_unsafe_column(col)


def test_g_s1_off_conservation(before: dict) -> None:
    """§G ①②③：S1-off（dead-drop 關）名稱集合／欄數／列數不變；非 ratio-unsafe 欄逐欄值與 NaN mask 不變；
    ratio-unsafe 欄＝前處理關之原值。"""
    got = freeze.s1_record("off", True)
    b, raw = before["s1_off"], before["s1_off_preprocessing_disabled"]
    assert (got["names_sha256"], got["n_columns"], got["n_rows"]) == (b["names_sha256"], b["n_columns"], b["n_rows"])
    for col, dig in got["columns"].items():
        want = raw["columns"][col] if _is_unsafe(col) else b["columns"][col]
        assert dig == want, col


def test_g_s1_on_column_set_and_values(before: dict) -> None:
    """§G ④⑤：S1-on 非 ratio-unsafe 欄名稱與值不變；新增欄＝改前被剔除且原值不死之 ratio-unsafe 欄；刪減為空。"""
    got = freeze.s1_record("on", True)
    b, raw = before["s1_on"], before["s1_on_preprocessing_disabled"]
    got_names, before_names = set(got["names"]), set(b["names"])
    assert {c for c in got_names if not _is_unsafe(c)} == {c for c in before_names if not _is_unsafe(c)}
    for col in got_names:
        if not _is_unsafe(col):
            assert got["columns"][col] == b["columns"][col], col
    expected_new = {c for c in raw["names"] if _is_unsafe(c)} - before_names
    assert got_names - before_names == expected_new
    assert before_names - got_names == set()


def test_multi_tf_names_unchanged(before: dict) -> None:
    """Task 1.3：12h＋4h 精簡設定之落盤欄名集合改前改後相同。"""
    names = freeze.multi_tf_names()
    assert names == before["multi_tf_names"]["names"]


def test_after_baseline_regression() -> None:
    """Task 2.2：改後基準（使用者核可後寫出）為落盤路徑之永久回歸基準。"""
    after = json.loads((REPO / "tests/_golden/ratiounsafe/baseline_after.json").read_text(encoding="utf-8"))
    for arm in ("off", "on"):
        got = freeze.s1_record(arm, True)
        want = after[f"s1_{arm}"]
        assert (got["names_sha256"], got["n_rows"]) == (want["names_sha256"], want["n_rows"])
        assert got["columns"] == want["columns"]


def test_boundary_01_failopen_baseline_untouched() -> None:
    """Task 2.2 邊界①：本票不改 failopen 基準。"""
    import subprocess

    rc = subprocess.run(["git", "diff", "--quiet", "--", "tests/_golden/failopen/baseline.json"], cwd=REPO).returncode
    assert rc == 0


def test_boundary_02_after_baseline_not_written_before_branch_tests_pass() -> None:
    """Task 2.2 邊界②：改後基準記錄之階段為 after，且其 S1 兩臂之 ratio-unsafe 欄值＝前處理關之原值（即 Task 2.1 已生效）。"""
    after = json.loads((REPO / "tests/_golden/ratiounsafe/baseline_after.json").read_text(encoding="utf-8"))
    before_ = json.loads((REPO / "tests/_golden/ratiounsafe/baseline.json").read_text(encoding="utf-8"))
    assert after["stage"] == "after"
    raw = before_["s1_off_preprocessing_disabled"]["columns"]
    for col, dig in after["s1_off"]["columns"].items():
        if _is_unsafe(col):
            assert dig == raw[col], col


def test_mutation_after_baseline_detects_reverted_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：生產判定恆回 None（L6.5 重新轉換 ratio-unsafe 欄）⇒ S1-off 之 ratio-unsafe 欄與改後基準不等（回歸基準有鑑別力）。"""
    after = json.loads((REPO / "tests/_golden/ratiounsafe/baseline_after.json").read_text(encoding="utf-8"))
    unsafe_cols = [c for c in after["s1_off"]["columns"] if _is_unsafe(c)]  # 先於 mutant 判定
    assert unsafe_cols
    monkeypatch.setattr(fn, "ratio_unsafe_category", lambda column: None)
    got = freeze.s1_record("off", True)
    assert any(got["columns"][c] != after["s1_off"]["columns"][c] for c in unsafe_cols)


# ---------------------------------------------------------------- Task 3.1：transform_selected

def test_transform_selected_excludes_tagged_unsafe() -> None:
    frame = _branch_frame()
    frame.columns = [fn.tag_timeframe(c, "12h") for c in frame.columns]
    selected = list(frame.columns)
    out = FeaturePreprocessor(_config()).transform_selected(selected, {"g": frame}, None)
    cols = {c for df in out.values() for c in df.columns}
    assert not cols & {fn.tag_timeframe(c, "12h") for c in UNSAFE}
    assert {fn.tag_timeframe(c, "12h") for c in SAFE} <= cols


def test_boundary_01_transform_selected_all_unsafe_returns_empty() -> None:
    """Task 3.1 邊界①（IC-first）：全選帶標記 ratio-unsafe 欄 ⇒ 既有契約回空 dict（不拋錯）。"""
    frame = _branch_frame(UNSAFE)
    frame.columns = [fn.tag_timeframe(c, "12h") for c in frame.columns]
    assert FeaturePreprocessor(_config()).transform_selected(list(frame.columns), {"g": frame}, None) == {}
