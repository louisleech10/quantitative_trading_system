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


# ---------------------------------------------------------------- 輸入與分支執行（共用 scripts/freeze_ratiounsafe_baseline.py）

ORACLE = json.loads((REPO / CONTRACT["branch_oracle_path"]).read_text(encoding="utf-8"))


def _branch_frame(columns: Optional[List[str]] = None) -> pd.DataFrame:
    return freeze.branch_frame(columns)


def _config(mode: str = "replace", zscore: Optional[List[int]] = None, fracdiff: bool = False) -> dict:
    return freeze.l65_config(mode, zscore, fracdiff)


def _registry_with(tmp_path: Path, frame: pd.DataFrame, group_id: str, tf: str = "12h"):
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    registry = ColumnGroupRegistry(work_dir=tmp_path / f"registry_{group_id}")
    group = ColumnGroup(group_id=group_id, layer=LayerSource.L1, timeframe=tf, data_source="ohlc",
                        indicator="RATIOUNSAFE", columns=tuple(frame.columns), shape=(0, 0), dtype="float32",
                        disk_path=None)
    group = registry.save_data(group, frame.to_numpy(dtype=np.float32))
    return registry, group


def _run(branch: str, frame: pd.DataFrame, tmp_path: Path, tag: str, require_spy: bool = True,
         cfg: Optional[dict] = None, sink_log: Optional[list] = None) -> pd.DataFrame:
    calls: List[str] = []
    out = freeze.run_branch(branch, frame, tmp_path, cfg=cfg, tag=tag, sink_log=sink_log, spy_calls=calls)
    spy = BRANCHES[branch].get("spy")
    if require_spy and spy:
        assert calls, f"具名分支 {branch} 未執行 {spy}"
    return out


def _as_stored(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(np.float32).astype(np.float64)


def _assert_matches_oracle(out: pd.DataFrame, oracle: Dict[str, Dict[str, str]],
                           allowed_original: List[str] = ()) -> None:
    """safe 欄（含 append 衍生欄）逐欄＝改前 oracle（HEAD 產之只含 safe 欄群組輸出）；輸出欄集合**恰為**
    oracle 鍵 ∪ `allowed_original`（混合群組之 ratio-unsafe 原始欄；其值另有原值斷言）——多欄或缺欄皆紅（審查 r6 codex P1-01）。"""
    assert set(out.columns) == set(oracle) | set(allowed_original), (
        sorted(set(out.columns) ^ (set(oracle) | set(allowed_original))))
    for col, want in oracle.items():
        assert freeze.column_digest(out[col]) == want, col


BRANCH_IDS = sorted(BRANCHES)


# ---------------------------------------------------------------- Task 2.1：逐分支

@pytest.mark.parametrize("branch", BRANCH_IDS)
def test_mixed_group_unsafe_passthrough_safe_matches_frozen_oracle(branch: str, tmp_path: Path) -> None:
    mixed = _run(branch, _branch_frame(), tmp_path, tag="mixed")
    stored = _as_stored(_branch_frame())
    for col in UNSAFE:
        assert np.array_equal(mixed[col].to_numpy(), stored[col].to_numpy(), equal_nan=True), col
    _assert_matches_oracle(mixed, ORACLE[branch], UNSAFE)
    derived_unsafe = [c for c in mixed.columns if any(c.startswith(u + "_") for u in UNSAFE)]
    assert derived_unsafe == []


@pytest.mark.parametrize("branch", BRANCH_IDS)
def test_safe_only_group_matches_frozen_oracle(branch: str, tmp_path: Path) -> None:
    """非 ratio-unsafe 群組之行為不變（改前 oracle 逐位元組）。"""
    _assert_matches_oracle(_run(branch, _branch_frame(SAFE), tmp_path, tag="safe"), ORACLE[branch])


@pytest.mark.parametrize("branch", BRANCH_IDS)
def test_boundary_01_all_unsafe_group_passthrough_and_sink_complete(branch: str, tmp_path: Path) -> None:
    """Task 2.1 邊界①：全 ratio-unsafe 群組 ⇒ 無轉換（正確實作可不呼叫轉換 helper，故不要求 spy）、run 完成、
    輸出收齊全部原始欄且無衍生欄。"""
    frame = _branch_frame(UNSAFE)
    out = _run(branch, frame, tmp_path, tag="allunsafe", require_spy=False)
    assert list(out.columns) == UNSAFE
    assert np.array_equal(out.to_numpy(), _as_stored(frame).to_numpy(), equal_nan=True)


def test_boundary_02_compact_native_passthrough_expands_to_primary_rows(tmp_path: Path) -> None:
    """Task 2.1 邊界②＋native 強制臂：compact-aligned 混合群組經 to_sink、確實走 native；ratio-unsafe 欄展開後＝原值展開、
    列數＝主週期列數；safe 欄＝改前 oracle。"""
    calls: List[object] = []
    mixed = freeze.run_native(UNSAFE + SAFE, tmp_path / "mixed", native_calls=calls)
    assert calls and calls[-1] is not None, "未走 native 分支"
    n_primary = len(mixed["idx_map"])
    for j, col in enumerate(UNSAFE):
        expanded = mixed["source"][mixed["idx_map"], j].astype(np.float64)
        assert mixed["parts"][col].shape[0] == n_primary
        assert np.array_equal(mixed["parts"][col], expanded, equal_nan=True), col
    assert set(mixed["parts"]) == set(ORACLE["native_arm"]) | set(UNSAFE), sorted(mixed["parts"])
    for col, want in ORACLE["native_arm"].items():
        assert freeze.column_digest(mixed["parts"][col]) == want, col


@pytest.mark.parametrize("branch", ["registry_sink_sharded", "registry_chunked"])
def test_boundary_03_shard_structure_unchanged(branch: str, tmp_path: Path) -> None:
    """Task 2.1 邊界③：全 ratio-unsafe 群組之 sink 呼叫結構（輸出群組名序列、各次欄數）＝同形非 ratio-unsafe 群組。"""
    log_u: list = []
    log_s: list = []
    safe_frame = _branch_frame(SAFE)
    safe_frame.columns = [f"close_trend_SHAPE_{i}" for i in range(len(SAFE))]
    _run(branch, _branch_frame(UNSAFE), tmp_path, tag="shape", require_spy=False, sink_log=log_u)
    _run(branch, safe_frame, tmp_path / "s", tag="shape", require_spy=False, sink_log=log_s)
    if BRANCHES[branch].get("mode") == "append":  # append：衍生欄另以 `<group>_L65_chunk*` 送出，只比原始欄之輸出
        log_u = [(g, c) for g, c in log_u if "_L65" not in g]
        log_s = [(g, c) for g, c in log_s if "_L65" not in g]
    assert log_u, "sink 未收到原始欄輸出"
    assert [g for g, _ in log_u] == [g for g, _ in log_s]
    assert [len(c) for _, c in log_u] == [len(c) for _, c in log_s]


def test_append_arm_no_unsafe_derivatives(tmp_path: Path) -> None:
    arm = CONTRACT["append_arm"]
    cfg = _config(mode="append", zscore=arm["zscore_windows"])
    mixed = _run(arm["branch"], _branch_frame(), tmp_path, tag="app", cfg=cfg)
    derived_unsafe = [c for c in mixed.columns if any(c.startswith(u + "_") for u in UNSAFE)]
    assert derived_unsafe == []
    stored = _as_stored(_branch_frame())
    for col in UNSAFE:
        assert np.array_equal(mixed[col].to_numpy(), stored[col].to_numpy(), equal_nan=True), col
    _assert_matches_oracle(mixed, ORACLE["append_arm"], UNSAFE)


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
    out = _run("registry_sink", _branch_frame(), tmp_path, tag="mutF")
    stored = _as_stored(_branch_frame())
    assert not all(np.array_equal(out[c].to_numpy(), stored[c].to_numpy(), equal_nan=True) for c in UNSAFE)


def test_mutation_skip_always_leaves_safe_untransformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant③：跳過判定恆 True ⇒ 非 ratio-unsafe 欄亦原值，與改前 oracle 不等。"""
    monkeypatch.setattr(fn, "ratio_unsafe_category", lambda column: "pattern")
    out = _run("registry_sink", _branch_frame(), tmp_path, tag="mutT", require_spy=False)
    assert any(freeze.column_digest(out[c]) != ORACLE["registry_sink"][c] for c in SAFE)


def test_mutation_branch_transform_disabled_caught_by_frozen_oracle(tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（審查 r5 codex P1-02）：sharded 分支之快速轉換改為恆等 ⇒ ratio-unsafe 原值與全 unsafe 斷言可綠，
    但 safe 欄與改前 oracle 不等（凍結 oracle 有鑑別力；混合 vs 只含 safe 之即時對照會被同一 mutant 騙過）。"""
    monkeypatch.setattr(FeaturePreprocessor, "_registry_fast_transform",
                        lambda self, arr, ctx, *a, **k: np.array(arr, copy=True))
    out = _run("registry_sink_sharded", _branch_frame(SAFE), tmp_path, tag="mutId")
    assert any(freeze.column_digest(out[c]) != ORACLE["registry_sink_sharded"][c] for c in SAFE)


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


def test_boundary_02_labels_not_routed_through_storage_tagging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 1.3 邊界②：S1 實際生成時，storage 寫檔段（`write_raw_from_registry_stream`）收到之 registry 群組欄不含任何
    `label_` 欄（labels 走獨立 labels_df，不經標記段）；且寫檔段確實被呼叫。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    seen: List[str] = []
    real = FeatureStorage.write_raw_from_registry_stream

    def _spy(self, symbol, tf, config_hash, registry, *args, **kwargs):
        for _, group in registry.iter_all():
            seen.extend(str(c) for c in group.columns)
        return real(self, symbol, tf, config_hash, registry, *args, **kwargs)

    monkeypatch.setattr(FeatureStorage, "write_raw_from_registry_stream", _spy)
    freeze.s1_record("off", True)
    assert seen, "storage 寫檔段未被呼叫"
    assert not [c for c in seen if c.startswith("label_")]


def test_multi_tf_names_unchanged(before: dict) -> None:
    """Task 1.3：12h＋4h 精簡設定之落盤欄名，非 ratio-unsafe 欄改前改後相同、無刪減；新增者只准 ratio-unsafe 欄
    （該設定 dead-drop 預設開，§C 例外：改前被 L6.5 抹 0 而判死之 ratio-unsafe 欄恢復；實作期實測 +19、全屬 pattern）。"""
    got = set(freeze.multi_tf_names())
    want = set(before["multi_tf_names"]["names"])
    assert {c for c in got if not _is_unsafe(c)} == {c for c in want if not _is_unsafe(c)}
    assert want - got == set()
    assert all(_is_unsafe(c) for c in got - want), sorted(c for c in got - want if not _is_unsafe(c))


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


def test_mutation_extra_safe_derivative_rejected_by_exact_column_set(tmp_path: Path,
                                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（審查 r6 codex P1-01）：append 分支多產一個 safe 衍生欄 ⇒ 精確欄集合比對紅（子集比對會放過）。"""
    real = FeaturePreprocessor._transform_single

    def _extra(self, df, *args, **kwargs):
        out = real(self, df, *args, **kwargs)
        if self.mode == "append":
            out = out.copy()
            for col in [c for c in df.columns if c in SAFE]:
                out[f"{col}_unexpected"] = out[col]
        return out

    monkeypatch.setattr(FeaturePreprocessor, "_transform_single", _extra)
    arm = CONTRACT["append_arm"]
    out = _run(arm["branch"], _branch_frame(SAFE), tmp_path, tag="mutExtra",
               cfg=_config(mode="append", zscore=arm["zscore_windows"]))
    assert {f"{c}_unexpected" for c in SAFE} <= set(out.columns), "前提：mutant 確實增欄"
    with pytest.raises(AssertionError):
        _assert_matches_oracle(out, ORACLE["append_arm"])


# ---------------------------------------------------------------- 審碼 r1 修補（全 ratio-unsafe 群組之校準與 inplace 不覆寫）

def _all_unsafe_with_stationarity(tmp_path: Path, entry: str):
    """全 ratio-unsafe 群組、平穩化開（fracdiff）、無任何校準封包 ⇒ 兩入口皆須原值完成（審碼 r1 codex P1-01）。"""
    frame = _branch_frame(UNSAFE)
    pre = FeaturePreprocessor(_config(fracdiff=True))
    pre.set_calibration({}, symbol="BTCUSDT", output_start=frame.index[-1], config_hash="ratiounsafe")
    registry, group = _registry_with(tmp_path, frame, f"12h_L1_ratiounsafe_stat_{entry}")
    if entry == "inplace":
        done = pre.transform_registry_groups(registry, n_workers=1)
        out = pd.DataFrame(registry.load_data(group.group_id), columns=list(frame.columns), index=frame.index)
    else:
        parts: Dict[str, np.ndarray] = {}

        def _sink(group_id, columns, data, *rest) -> None:
            arr = np.asarray(data, dtype=np.float64)
            for i, name in enumerate(columns):
                parts[str(name)] = arr[:, i].copy()

        done = pre.transform_registry_groups_to_sink(registry, _sink, n_workers=1)
        out = pd.DataFrame({c: parts[c] for c in frame.columns}, index=frame.index)
    return frame, out, done


@pytest.mark.parametrize("entry", ["inplace", "sink"])
def test_all_unsafe_group_with_stationarity_needs_no_packet(entry: str, tmp_path: Path) -> None:
    frame, out, done = _all_unsafe_with_stationarity(tmp_path, entry)
    assert done == 1
    assert np.array_equal(out.to_numpy(), _as_stored(frame).to_numpy(), equal_nan=True)


def _overwrites_for_all_unsafe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> List[str]:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    seen: List[str] = []
    real = ColumnGroupRegistry.overwrite_data

    def _spy(self, group_id, *args, **kwargs):
        seen.append(str(group_id))
        return real(self, group_id, *args, **kwargs)

    monkeypatch.setattr(ColumnGroupRegistry, "overwrite_data", _spy)
    frame = _branch_frame(UNSAFE)
    registry, group = _registry_with(tmp_path, frame, "12h_L1_ratiounsafe_noow")
    FeaturePreprocessor(_config()).transform_registry_groups(registry, n_workers=1)
    out = registry.load_data(group.group_id)
    assert np.array_equal(np.asarray(out, dtype=np.float64), _as_stored(frame).to_numpy(), equal_nan=True)
    return seen


def test_inplace_all_unsafe_group_not_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 改法：inplace 入口不覆寫全 ratio-unsafe 群組（審碼 r1 codex P2-02）。"""
    assert _overwrites_for_all_unsafe(tmp_path, monkeypatch) == []


def test_mutation_inplace_skip_removed_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：入口之全 ratio-unsafe 判定失效（consumer 判定恆 False）⇒ 群組被派發並覆寫（不覆寫斷言有鑑別力）。"""
    from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fp_mod

    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    monkeypatch.setattr(fp_mod, "is_ratio_unsafe_column", lambda column: False)
    seen: List[str] = []
    real = ColumnGroupRegistry.overwrite_data

    def _spy(self, group_id, *args, **kwargs):
        seen.append(str(group_id))
        return real(self, group_id, *args, **kwargs)

    monkeypatch.setattr(ColumnGroupRegistry, "overwrite_data", _spy)
    registry, _ = _registry_with(tmp_path, _branch_frame(UNSAFE), "12h_L1_ratiounsafe_mutow")
    FeaturePreprocessor(_config()).transform_registry_groups(registry, n_workers=1)
    assert seen == ["12h_L1_ratiounsafe_mutow"]
