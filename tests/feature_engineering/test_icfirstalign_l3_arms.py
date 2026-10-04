"""ICFIRSTALIGN 乙 Task 4.0：L3 非串流臂不得丟表（docs/ICFIRSTALIGN_SPEC.md v18）。

正式生成 L3 串流分支以 `_ = aggregator.compute_all(..., persist_callback=persister)` 呼叫後回空表；不支援 callback 之臂
（`FFACT_L3_STREAMING=0`、`FFACT_L3_MULTI_WINDOW=0`、`FFACT_USE_NUMBA_ROLLING=0`、numba 例外後備）回傳完整表卻被丟棄。
主委實跑（2026-10-04）：S2 預設臂 raw 20 個 L3 群組；`FFACT_USE_NUMBA_ROLLING=0` 時 0 個。
oracle：同一 run 內 spy `RollingAggregator.compute_all` 之回傳表（轉 float32、依時間戳對齊、欄名標記週期）
＝raw 之 L3 欄（前處理關，使 raw 即層值）。預設臂對照 HEAD 凍結之 tests/_golden/icfirstalign/l3_default_arm.json。
實作前應為紅：非預設臂 raw 無 L3 欄、`_persist_l3_returned_table` 不存在。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from momentum.core.icfirstalign_errors import L3PersistConflictError
from momentum.FeatureEngineering import feature_naming as fn
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.operators import numba_rolling
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from scripts.freeze_icfirstalign_baseline import l3_digests
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(600)

GOLDEN = json.loads((h.REPO / "tests/_golden/icfirstalign/l3_default_arm.json").read_text(encoding="utf-8"))
ARMS = {
    "numba_off": {"FFACT_USE_NUMBA_ROLLING": "0"},
    "streaming_off": {"FFACT_L3_STREAMING": "0"},
    "multi_window_off": {"FFACT_L3_MULTI_WINDOW": "0"},
}


def _no_preprocessing() -> Dict[str, Any]:
    return h.s2_payload(preprocessing={"enabled": False})


def _run_recording(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env: Dict[str, str],
                   payload: Dict[str, Any] = None) -> Dict[str, Any]:
    root = h.isolated(monkeypatch, tmp_path)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    returned: List[pd.DataFrame] = []
    real = RollingAggregator.compute_all

    def spy(self: RollingAggregator, *args: Any, **kwargs: Any) -> Any:
        out = real(self, *args, **kwargs)
        if isinstance(out, pd.DataFrame) and not out.empty:
            returned.append(out.copy())
        return out

    monkeypatch.setattr(RollingAggregator, "compute_all", spy)
    _, result = h.generate_s2(root, payload or _no_preprocessing())
    config_hash = str(result.metadata["config_hash"])
    return {"root": root, "config_hash": config_hash, "returned": returned}


def _raw_l3(run: Dict[str, Any]) -> pd.DataFrame:
    reader = FeatureReader(str(run["root"]))
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, run["config_hash"], artifact_kind="raw")
    cols = sorted(c for name, g in manifest["artifacts"]["raw"]["groups"].items() if "_L3_" in name
                  for c in g.get("columns", []))
    frame = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, run["config_hash"], cols) if cols else pd.DataFrame()
    if cols:
        frame.index = reader.load_row_index_v2(h.SYMBOL, h.PRIMARY, run["config_hash"])
    return frame


def _expected_from_returned(run: Dict[str, Any], axis: pd.DatetimeIndex) -> pd.DataFrame:
    """oracle：回傳表 → 欄名標記 12h、index 轉 UTC 時間、取 raw 軸之列、轉 float32。"""
    table = pd.concat(run["returned"], axis=1)
    idx = table.index
    if not isinstance(idx, pd.DatetimeIndex):
        ints = np.asarray(idx, dtype=np.int64)
        idx = pd.DatetimeIndex(pd.to_datetime(ints, unit="ms" if ints.max() > 10**11 else "s"))
    table = table.set_axis(idx, axis=0)
    table.columns = [fn.tag_timeframe(str(c), h.PRIMARY) for c in table.columns]
    return table.reindex(axis).astype(np.float32)


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_non_default_arm_persists_returned_l3_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arm: str) -> None:
    run = _run_recording(monkeypatch, tmp_path, ARMS[arm])
    raw = _raw_l3(run)
    assert run["returned"], "該臂應回傳非空 L3 表"
    assert not raw.empty, f"{arm}：L3 欄不得被丟棄"
    expected = _expected_from_returned(run, raw.index)
    assert sorted(raw.columns) == sorted(expected.columns)
    for col in raw.columns:
        np.testing.assert_array_equal(raw[col].to_numpy(dtype=np.float32), expected[col].to_numpy(dtype=np.float32))


def test_numba_exception_fallback_persists_returned_l3_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any, **k: Any) -> Any:
        raise RuntimeError("injected numba failure")

    monkeypatch.setattr(numba_rolling, "fused_rolling_stats_multi_window", boom)
    run = _run_recording(monkeypatch, tmp_path, {})
    raw = _raw_l3(run)
    assert not raw.empty
    expected = _expected_from_returned(run, raw.index)
    assert sorted(raw.columns) == sorted(expected.columns)


def test_default_arm_l3_groups_bytes_equal_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """預設臂（numba 多窗串流）之 raw L3 欄與 HEAD 凍結逐位元組相等（S2，前處理同 golden）。"""
    root = h.isolated(monkeypatch, tmp_path)
    for key in ("FFACT_USE_NUMBA_ROLLING", "FFACT_L3_STREAMING", "FFACT_L3_MULTI_WINDOW", "FFACT_L3_PERSIST_MODE"):
        monkeypatch.delenv(key, raising=False)
    _, result = h.generate_s2(root)
    assert l3_digests(root, str(result.metadata["config_hash"])) == GOLDEN["columns"]


def test_boundary_01_rolling_disabled_no_l3_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.0 邊界①：回傳空表且 callback 0 次（L3 未啟用）⇒ 無 L3 欄、無錯誤。"""
    payload = _no_preprocessing()
    payload["rolling_aggregation"] = {"enabled": False}
    run = _run_recording(monkeypatch, tmp_path, {"FFACT_USE_NUMBA_ROLLING": "0"}, payload)
    assert _raw_l3(run).empty
    assert hasattr(FeatureFactory, "_persist_l3_returned_table")


def test_boundary_02_callback_and_returned_table_conflict_raises(tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.0 邊界②：回傳非空且 callback 亦收到欄 ⇒ `L3PersistConflictError`（不得雙寫）。"""
    root = h.isolated(monkeypatch, tmp_path)
    real = RollingAggregator.compute_all

    def both(self: RollingAggregator, base: pd.DataFrame, persist_callback: Any = None, **kwargs: Any) -> Any:
        out = real(self, base, **kwargs)
        if persist_callback is not None and not out.empty:
            persist_callback("injected_step", out.iloc[:, :1])
        return out

    monkeypatch.setattr(RollingAggregator, "compute_all", both)
    with pytest.raises(L3PersistConflictError):
        h.generate_s2(root, _no_preprocessing())


def test_mutation_returned_table_dropped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：`_persist_l3_returned_table` 改 no-op（恢復丟表）⇒ 非預設臂 raw 無 L3 欄。"""
    monkeypatch.setattr(FeatureFactory, "_persist_l3_returned_table", lambda self, *a, **k: None)
    run = _run_recording(monkeypatch, tmp_path, ARMS["numba_off"])
    assert _raw_l3(run).empty
