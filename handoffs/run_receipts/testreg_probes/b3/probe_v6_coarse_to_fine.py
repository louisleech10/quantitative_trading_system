"""TESTREG b3 Task 3.1 題一探針（非正式測試；只在暫存 worktree 複製到 tests/feature_engineering/ 後執行）。

目的：①量 PROBEWINSOR 後 V-6 同型設定改為主流「粗接細」（主 1h、training [1h, 12h]）之單項耗時；
②驗 V-6 之獨立 oracle `_independent_asof_index_map` 用於粗接細時與生產 `TimeframeAligner.build_asof_index_map`
逐列相等（擷取條件以週期長度判定，不以列數），且 compact=0 時 `_align_group_array` 全欄 byte 等於 oracle 聚集。
用法（暫存 worktree 根）：cp <本檔> tests/feature_engineering/test_zz_probe_c2f.py &&
  venv/bin/python -m pytest -q -p no:cacheprovider -p no:testreg_recorder tests/feature_engineering/test_zz_probe_c2f.py -k <mode>
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from tests.feature_engineering import test_failopen_correctness as fc


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: AlignmentMode, use_searchsorted: bool) -> dict:
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    captured: dict = {"map_count": 0, "group_count": 0, "column_count": 0, "maps": []}
    active: dict = {}
    original_build = TimeframeAligner.build_asof_index_map
    original_align = MultiTFGenerator._align_group_array

    def _capturing_build(primary_s, source_s, *, source_dur_ns, primary_dur_ns, mode):  # noqa: ANN001
        idx_map = original_build(primary_s, source_s, source_dur_ns=source_dur_ns,
                                 primary_dur_ns=primary_dur_ns, mode=mode)
        if int(source_dur_ns) != int(primary_dur_ns):
            oracle = fc._independent_asof_index_map(
                primary_s, source_s,
                source_dur_s=int(source_dur_ns // fc.NS_PER_SECOND),
                primary_dur_s=int(primary_dur_ns // fc.NS_PER_SECOND),
                mode=str(mode),
            )
            assert np.array_equal(oracle, idx_map)
            active["idx_map"] = oracle
            active["n_primary"] = len(primary_s)
            captured["map_count"] += 1
            captured["maps"].append({
                "n_primary": int(len(primary_s)), "n_source": int(len(source_s)),
                "valid": int((oracle >= 0).sum()), "source_dur_s": int(source_dur_ns // fc.NS_PER_SECOND),
            })
        return idx_map

    def _capturing_align(src_data, idx_map, n_primary):  # noqa: ANN001
        aligned = original_align(src_data, idx_map, n_primary)
        oracle = active.get("idx_map")
        if isinstance(oracle, np.ndarray) and active.get("n_primary") == n_primary:
            src = np.asarray(src_data, dtype=np.float32)
            expected = fc._oracle_aligned_columns(oracle, src, n_primary)
            fc._assert_oracle_aligned_byte_equal(expected, np.asarray(aligned, dtype=np.float32))
            captured["group_count"] += 1
            captured["column_count"] += int(src.shape[1])
        return aligned

    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "0")
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1" if use_searchsorted else "0")
    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(_capturing_build))
    monkeypatch.setattr(MultiTFGenerator, "_align_group_array", staticmethod(_capturing_align))
    factory = fc._make_factory(monkeypatch, tmp_path)
    start, end = fc._short_window_dates(14)
    t0 = time.perf_counter()
    result = factory.generate_features(
        fc.BASELINE_SYMBOL, "1h",
        config_override=fc._multi_tf_payload(timeframes={
            "primary": "1h", "training": ["1h", "12h"], "alignment_mode": mode.value}),
        force_regenerate=True, start_date=start, end_date=end, persist=False,
    )
    captured["seconds"] = time.perf_counter() - t0
    captured["feature_count"] = int(result.feature_count)
    captured["rows"] = int(len(result.features_df))
    return captured


@pytest.mark.parametrize("mode", [AlignmentMode.OPEN_MINUS, AlignmentMode.CLOSE_TIME], ids=["open_minus", "close_time"])
def test_probe_coarse_to_fine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: AlignmentMode) -> None:
    cap = _run(monkeypatch, tmp_path, mode, use_searchsorted=True)
    print(f"\nPROBE mode={mode.value} seconds={cap['seconds']:.1f} rows={cap['rows']} features={cap['feature_count']} "
          f"maps={cap['maps']} groups={cap['group_count']} cols={cap['column_count']}")
    assert cap["map_count"] >= 1 and cap["group_count"] >= 1
