"""ICFIRSTALIGN 乙 Task 1.4：IC cache 重用之計算身分（docs/ICFIRSTALIGN_SPEC.md v17）。

同一精簡真實 CGSA complete run（S2，`source_run_status=complete`），以 label L0（中段注入一個 NaN）計算全窗 IC
並落 cache，再刪 raw/（cache 重用路徑只在 raw 不存在時觸發）。每一測試前自備份還原 cache JSON。
只容 threshold 不同；任一身分欄不同或舊 fingerprint 缺欄 ⇒ 拒用；raw 不存在 ⇒ `ICCacheRawUnavailableError`。
實作前應為紅：現行只核 symbol／tf／config_hash／有效列數（容差 10），跨窗、換方法、換 label 值皆被重用。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from momentum.Analysis import ic_engine as ice
from momentum.Analysis.ic_engine import ICEngine
from momentum.core.icfirstalign_errors import ICCacheRawUnavailableError
from momentum.FeatureEngineering.feature_reader import FeatureReader
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(600)

IDENTITY_FIELDS = list(h.CONTRACT["cache_identity_fields"])


def _window(axis: pd.DatetimeIndex) -> Dict[str, str]:
    return {"start": str(axis[0]), "end": str(axis[-1])}


@pytest.fixture(scope="module")
def cached(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("icfa_cache")
    root = h.isolated(mp, tmp)
    _, result = h.generate_s2(root)
    config_hash = str(result.metadata["config_hash"])
    reader = FeatureReader(str(root))
    axis = reader.load_row_index_v2(h.SYMBOL, h.PRIMARY, config_hash)
    label0 = h.forward_return_label()
    nan_ts = axis[len(axis) // 2]
    label0.loc[nan_ts] = np.nan  # 窗內一個 NaN（供「NaN 位置互換」案例）
    # r23：本檔驗 Task 1.4，不得依賴 Task 1.1。寫 cache 時測試端把 raw 群組讀回接上 sidecar 時間軸
    # （HEAD 之 pd.read_parquet 讀回為 RangeIndex，時間字串選窗會 TypeError）；Task 1.1 落地後讀回已帶同一軸，此包裝不改值。
    real_read = pd.read_parquet

    def read_with_axis(*a: Any, **k: Any) -> pd.DataFrame:
        frame = real_read(*a, **k)
        if len(frame) == len(axis) and not isinstance(frame.index, pd.DatetimeIndex):
            frame.index = axis
        return frame

    with pytest.MonkeyPatch.context() as rp:
        rp.setattr(pd, "read_parquet", read_with_axis)
        ICEngine({"methods": ["spearman"]}).compute_ic_from_l7_raw(
            h.SYMBOL, h.PRIMARY, config_hash, label0, feature_reader=reader, ic_threshold=0.02,
            label_horizon="1", selection_window=_window(axis))
    run = h.run_dir(root, config_hash)
    selected = run / f"ic_selected_features_{h.SYMBOL}_{h.PRIMARY}.json"
    backup = tmp / "ic_selected.backup.json"
    shutil.copy2(selected, backup)
    shutil.rmtree(run / "raw")
    yield {"root": root, "config_hash": config_hash, "reader": reader, "axis": axis, "label0": label0,
           "nan_ts": nan_ts, "selected": selected, "backup": backup, "run": run}
    mp.undo()


@pytest.fixture()
def c(cached: Dict[str, Any]) -> Dict[str, Any]:
    shutil.copy2(cached["backup"], cached["selected"])
    return cached


def _request(c: Dict[str, Any], label: pd.Series, **kwargs: Any):
    kwargs.setdefault("label_horizon", "1")
    kwargs.setdefault("selection_window", _window(c["axis"]))
    kwargs.setdefault("ic_threshold", 0.02)
    kwargs.setdefault("method", "spearman")
    return ICEngine({"methods": ["spearman", "pearson"]}).compute_ic_from_l7_raw(
        h.SYMBOL, h.PRIMARY, c["config_hash"], label, feature_reader=c["reader"], **kwargs)


def _finite_pair(c: Dict[str, Any]):
    lab = c["label0"]
    inside = [t for t in c["axis"] if np.isfinite(lab.get(t, np.nan))]
    a, b = inside[10], inside[20]
    assert lab[a] != lab[b]
    return a, b


def _variant(c: Dict[str, Any], kind: str):
    """回傳 (label, 額外 kwargs)：單獨改動一個身分欄。"""
    label = c["label0"].copy()
    axis = c["axis"]
    if kind == "method":
        return label, {"method": "pearson"}
    if kind == "label_horizon":
        return label, {"label_horizon": "2"}
    if kind == "selection_window_start":
        return label, {"selection_window": {"start": str(axis[5]), "end": str(axis[-1])}}
    if kind == "selection_window_end":
        return label, {"selection_window": {"start": str(axis[0]), "end": str(axis[-6])}}
    if kind == "split_id":
        return label, {"split_id": "split-b"}
    if kind == "label_swap_finite":
        a, b = _finite_pair(c)
        label[a], label[b] = label[b], label[a]
        return label, {}
    if kind == "label_swap_nan":
        a, _ = _finite_pair(c)
        label[c["nan_ts"]], label[a] = label[a], np.nan
        return label, {}
    raise AssertionError(kind)


VARIANTS = ["method", "label_horizon", "selection_window_start", "selection_window_end", "split_id",
            "label_swap_finite", "label_swap_nan"]


@pytest.mark.parametrize("kind", VARIANTS)
def test_identity_change_rejected_fail_closed(c: Dict[str, Any], kind: str) -> None:
    """單獨改動一個身分欄 ⇒ 拒用；raw 不存在 ⇒ `ICCacheRawUnavailableError`（不得重用全窗分數）。"""
    label, kw = _variant(c, kind)
    with pytest.raises(ICCacheRawUnavailableError):
        _request(c, label, **kw)


def test_feature_axis_change_rejected(c: Dict[str, Any]) -> None:
    """特徵軸（raw sidecar 時間戳）改變 ⇒ 拒用。"""
    manifest = json.loads((c["run"] / "feature_manifest.json").read_text(encoding="utf-8"))
    path = c["run"] / manifest["row_index"]["path"]
    original = path.read_bytes()
    try:
        table = pq.read_table(str(path))
        shifted = pa.array(table.column("timestamp").to_numpy() + 3600)
        pq.write_table(table.set_column(0, "timestamp", shifted), str(path))
        with pytest.raises(ICCacheRawUnavailableError):
            _request(c, c["label0"])
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize("field", IDENTITY_FIELDS)
def test_old_fingerprint_missing_field_rejected(c: Dict[str, Any], field: str) -> None:
    """舊 fingerprint 逐一缺每一必要身分欄 ⇒ 拒用。"""
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    assert field in payload["data_fingerprint"], f"fingerprint 未寫入身分欄 {field}"
    del payload["data_fingerprint"][field]
    c["selected"].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ICCacheRawUnavailableError):
        _request(c, c["label0"])


def test_fingerprint_writes_all_identity_fields(c: Dict[str, Any]) -> None:
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    assert set(IDENTITY_FIELDS) <= set(payload["data_fingerprint"])
    assert payload["data_fingerprint"]["source_run_status"] == "complete"


def test_boundary_01_old_cache_without_new_fields_rejected(c: Dict[str, Any]) -> None:
    """Task 1.4 邊界①：HEAD 格式之舊 cache（無任何新身分欄）⇒ 拒用。"""
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    for f in ("method", "selection_window_start", "selection_window_end", "feature_axis_sha256", "label_sha256"):
        payload["data_fingerprint"].pop(f, None)
    c["selected"].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ICCacheRawUnavailableError):
        _request(c, c["label0"])


def test_boundary_02_same_values_different_timestamps_rejected(c: Dict[str, Any]) -> None:
    """Task 1.4 邊界②：label 值同而時間戳不同 ⇒ 拒用。"""
    label = c["label0"].copy()
    label.index = label.index + pd.Timedelta(hours=12)
    with pytest.raises(ICCacheRawUnavailableError):
        _request(c, label)


def _subsecond_window(c: Dict[str, Any]) -> Dict[str, str]:
    """起點晚 0.5 秒之選窗（真實軸上即少選首列；審碼 b1 r1 codex P1-01 之反例）。"""
    return {"start": str(c["axis"][0] + pd.Timedelta(milliseconds=500)), "end": str(c["axis"][-1])}


def test_subsecond_window_change_rejected(c: Dict[str, Any]) -> None:
    """選窗端點只差次秒（實際選列不同）⇒ 身分不同、拒用（身分不得截至整秒）。"""
    with pytest.raises(ICCacheRawUnavailableError):
        _request(c, c["label0"], selection_window=_subsecond_window(c))


def test_subsecond_label_index_change_rejected(c: Dict[str, Any]) -> None:
    """label 值同而時間戳只差次秒 ⇒ label 指紋不同、拒用。"""
    label = c["label0"].copy()
    label.index = label.index + pd.Timedelta(milliseconds=500)
    assert ice.label_fingerprint(label) != ice.label_fingerprint(c["label0"])
    with pytest.raises(ICCacheRawUnavailableError):
        _request(c, label)


def test_mutation_window_bound_truncated_to_seconds(c: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：選窗身分改回截至整秒 ⇒ 次秒不同之選窗被重用（`test_subsecond_window_change_rejected` 翻轉）。"""
    def truncated(value: Any) -> Any:
        if value is None or value == "":
            return None
        return int(pd.Timestamp(value).floor("s").value)

    monkeypatch.setattr(ice, "_window_bound", truncated)
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    for key in ("selection_window_start", "selection_window_end"):  # 舊 cache 之身分改寫為同一截秒表示，只留次秒差
        payload["data_fingerprint"][key] = truncated(_window(c["axis"])[key.rsplit("_", 1)[1]])
    c["selected"].write_text(json.dumps(payload), encoding="utf-8")
    result = _request(c, c["label0"], selection_window=_subsecond_window(c))
    assert result.data_fingerprint["cache_status"] == "reused_from_cache"


def test_boundary_03_threshold_only_reuses_and_reselects(c: Dict[str, Any]) -> None:
    """Task 1.4 邊界③：只改 threshold ⇒ 重用並只重選。"""
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    result = _request(c, c["label0"], ic_threshold=0.05)
    assert result.data_fingerprint["cache_status"] == "reused_from_cache"
    expected = sorted(f for f, v in payload["ic_scores"].items() if v is not None and np.isfinite(v) and abs(v) >= 0.05)
    assert sorted(result.selected) == expected


@pytest.mark.parametrize("tz", ["UTC", "Asia/Taipei", "America/New_York", "naive", "epoch"])
def test_same_utc_instant_representations_reuse(c: Dict[str, Any], tz: str) -> None:
    """同一 UTC 時刻之不同表示（任一時區 tz-aware、UTC tz-naive、epoch 秒）⇒ 同一指紋、重用。"""
    label = c["label0"].copy()
    utc = label.index.tz_localize("UTC")
    if tz == "naive":
        label.index = utc.tz_localize(None)
    elif tz == "epoch":
        label.index = pd.Index((utc.asi8 // 10**9).astype(np.int64))
    else:
        label.index = utc.tz_convert(tz)
    assert ice.label_fingerprint(label) == ice.label_fingerprint(c["label0"])
    result = _request(c, label)
    assert result.data_fingerprint["cache_status"] == "reused_from_cache"


@pytest.mark.parametrize("kind", ["method", "label_horizon", "selection_window_start", "selection_window_end",
                                  "split_id", "label_swap_finite", "label_swap_nan"])
def test_mutation_identity_field_comparison_removed(c: Dict[str, Any], monkeypatch: pytest.MonkeyPatch,
                                                    kind: str) -> None:
    """mutant：自 `CACHE_IDENTITY_FIELDS` 移除對應欄之比對 ⇒ 該改動被重用（拒用斷言翻轉）。"""
    field = {"method": "method", "label_horizon": "label_horizon",
             "selection_window_start": "selection_window_start",
             "selection_window_end": "selection_window_end", "split_id": "split_id",
             "label_swap_finite": "label_sha256", "label_swap_nan": "label_sha256"}[kind]
    monkeypatch.setattr(ice, "CACHE_IDENTITY_FIELDS", tuple(f for f in ice.CACHE_IDENTITY_FIELDS if f != field))
    label, kw = _variant(c, kind)
    result = _request(c, label, **kw)
    assert result.data_fingerprint["cache_status"] == "reused_from_cache"


def _shift_feature_axis(c: Dict[str, Any]) -> Any:
    manifest = json.loads((c["run"] / "feature_manifest.json").read_text(encoding="utf-8"))
    path = c["run"] / manifest["row_index"]["path"]
    original = path.read_bytes()
    table = pq.read_table(str(path))
    pq.write_table(table.set_column(0, "timestamp", pa.array(table.column("timestamp").to_numpy() + 3600)), str(path))
    return lambda: path.write_bytes(original)


def test_mutation_feature_axis_comparison_removed(c: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（r23）：移除 `feature_axis_sha256` 之比對 ⇒ 特徵軸改變仍被重用（`test_feature_axis_change_rejected` 翻轉）。"""
    monkeypatch.setattr(ice, "CACHE_IDENTITY_FIELDS",
                        tuple(f for f in ice.CACHE_IDENTITY_FIELDS if f != "feature_axis_sha256"))
    restore = _shift_feature_axis(c)
    try:
        assert _request(c, c["label0"]).data_fingerprint["cache_status"] == "reused_from_cache"
    finally:
        restore()


@pytest.mark.parametrize("field", ["symbol", "tf", "config_hash"])
def test_fingerprint_identity_value_tampered_rejected(c: Dict[str, Any], field: str) -> None:
    """r23：cache 內 fingerprint 之 symbol／tf／config_hash 與請求不等 ⇒ 拒用（值比對，不只存在性）。"""
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    payload["data_fingerprint"][field] = str(payload["data_fingerprint"][field]) + "_other"
    c["selected"].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ICCacheRawUnavailableError):
        _request(c, c["label0"])


@pytest.mark.parametrize("field", ["symbol", "tf", "config_hash"])
def test_mutation_identity_value_comparison_removed(c: Dict[str, Any], monkeypatch: pytest.MonkeyPatch,
                                                   field: str) -> None:
    """mutant（r23）：移除該欄之比對 ⇒ 竄改後仍被重用。"""
    monkeypatch.setattr(ice, "CACHE_IDENTITY_FIELDS", tuple(f for f in ice.CACHE_IDENTITY_FIELDS if f != field))
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    payload["data_fingerprint"][field] = str(payload["data_fingerprint"][field]) + "_other"
    c["selected"].write_text(json.dumps(payload), encoding="utf-8")
    assert _request(c, c["label0"]).data_fingerprint["cache_status"] == "reused_from_cache"
