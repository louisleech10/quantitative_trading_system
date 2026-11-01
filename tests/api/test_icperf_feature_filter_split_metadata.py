"""ICPERF Task 0.4 ㊶：帶 feature_filter 之 IC 報告切分 metadata（`docs/ICPERF_SPEC.md` v5.56 Task 0.4 擴列表 ㊶）。

## 這批測試在防什麼

`_apply_feature_filter` → `_filter_metadata_for_columns` 原本剔除「非選中特徵之 dict 值鍵」——全域鍵
`ic_train_test_split`、`ic_window_disclosure`、`period_alignment`、`label_mode` 等也是 dict ⇒ 一併被剔除。
已切分之請求（train／test 1600／395）於帶 feature_filter 時報告標 `analysis_status`＝`degraded_full_sample`
（`_downgrade_branch` 判 `no_holdout_evidence`），不報錯；前端 IC 頁帶 feature_filter 亦中。

## 路徑覆蓋

- 秒級（明列邊界輸入）：特徵鍵（選中／未選中）、全域 dict 鍵、全域純量鍵、特徵名以外之 dict 鍵四類；
  feature_filter 未給／空設定兩條早退分支 metadata 原樣。
- 真實資料（requires_kline）：L 格交接 h5 之真實欄子集（200 欄，seeded 巢狀、值照抄）上同一切分請求有／無
  feature_filter（選其 100 欄）之報告——`ic_train_test_split` 逐鍵相等、
  `analysis_status` 相同、全域 dict 鍵集合相同、報告之特徵鍵 ⊆ 請求選欄。

mutation：還原「剔除非選中之 dict 值鍵」⇒ 秒級與真實資料案皆紅。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import FeatureFilterSchema, ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

REPO = Path(__file__).resolve().parents[2]
FREEZE_SCRIPT = REPO / "scripts" / "icperf_freeze_baseline.py"
HEAVY_MARKERS = ("slow", "requires_kline")


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """同 test_icperf_correctness.py：本檔真實資料測試須經共用監看（`scripts/run_watched.py`）執行。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


# ── 秒級：明列邊界輸入 ──────────────────────────────────────────────────────────────────────────────────
FEATURES = ("f_a", "f_b", "f_c")
SPLIT_META = {"requested": True, "applied": True, "oos_guarantees": True, "train_rows": 6, "test_rows": 2}
WINDOW_META = {"window_unit": "bars", "timeframe": "4h"}


def _frame_and_meta() -> tuple:
    idx = pd.date_range("2025-05-29 16:00", periods=10, freq="4h")
    df = pd.DataFrame({name: np.arange(10, dtype=float) + i for i, name in enumerate(FEATURES)}, index=idx)
    meta: Dict[str, Any] = {name: {"category": "trend", "data_source": "close", "family": name} for name in FEATURES}
    meta.update({"symbol": "BTCUSDT", "timeframe": "4h", "ic_train_test_split": dict(SPLIT_META),
                 "ic_window_disclosure": dict(WINDOW_META), "label_mode": {"effective": "imported_binary"}})
    return df, meta


def test_feature_filter_keeps_global_metadata_and_drops_unselected_features() -> None:
    df, meta = _frame_and_meta()
    orch = ICFilterOrchestrator(ICConfig())
    out_df, out_meta, info = orch._apply_feature_filter(df, meta, FeatureFilterSchema(include_features=["f_b"]))
    assert list(out_df.columns) == ["f_b"] and info["feature_filter_applied"] is True
    # oracle：特徵鍵只留選中者；其餘（非特徵）鍵逐鍵原樣
    expected = {k: v for k, v in meta.items() if k not in FEATURES or k == "f_b"}
    assert out_meta == expected
    assert out_meta["ic_train_test_split"] == SPLIT_META


@pytest.mark.parametrize("ff", [None, FeatureFilterSchema()])
def test_feature_filter_early_returns_keep_metadata(ff: Any) -> None:
    df, meta = _frame_and_meta()
    out_df, out_meta, info = ICFilterOrchestrator(ICConfig())._apply_feature_filter(df, meta, ff)
    assert out_meta == meta and list(out_df.columns) == list(FEATURES)
    assert info["feature_filter_applied"] is False


def test_feature_filter_split_status_matches_unfiltered() -> None:
    """同一 metadata 有／無 feature_filter ⇒ `_resolve_root_status` 相同（舊碼帶 filter 判 degraded_full_sample）。"""
    df, meta = _frame_and_meta()
    orch = ICFilterOrchestrator(ICConfig())
    _, filtered, _ = orch._apply_feature_filter(df, meta, FeatureFilterSchema(include_features=["f_a", "f_c"]))
    assert ICFilterOrchestrator._resolve_root_status(filtered) == ICFilterOrchestrator._resolve_root_status(meta)
    assert ICFilterOrchestrator._resolve_root_status(filtered) == ("ok_oos", True)


# ── 真實資料（requires_kline）：L 格同一切分請求有／無 feature_filter ──────────────────────────────────────
#: 交接 h5 之真實欄子集（`icperf_freeze_baseline._write_stage5_subset`：同一 seeded 巢狀規則，值逐位元照抄）——
#: 「無 feature_filter」須跑交接 h5 之全部欄，L 格全欄（3,632）之 IC 實測約 37 分鐘
#: （`runs/icperf/icperf-volprobe-20261101-011249-_e4o5cya/ic_report_long/capture/run.log` 03:02→03:39），
#: 而切分與 metadata 之路徑與欄數無關 ⇒ 以真實欄子集為無 filter 之母體，有 filter 者選其一半。
REAL_SUBSET_COLS = 200
REAL_FILTER_COLS = 100
#: 與選欄無關之全域 dict 鍵（存在與否、值須相同）
GLOBAL_SPLIT_KEYS = ("ic_train_test_split", "ic_window_disclosure", "period_alignment", "split_unify")
#: 全域鍵內隨選欄而變之子鍵：`ic_window_disclosure.ic_mean_source`＝各 ic_mean 來源之**特徵數**（實跑：200 欄
#: {pooled_point_ic 6, rolling_mean 182, unavailable 11}，100 欄另一組）——是逐特徵計數之彙總，非切分資訊
PER_FEATURE_COUNT_SUBKEYS = ("ic_mean_source",)


def _without_per_feature_counts(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if k not in PER_FEATURE_COUNT_SUBKEYS}
    return value


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.mark.requires_kline
def test_feature_filter_split_metadata_on_real_l_cell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import h5py

    from api.services.ic_analysis_service import FEATURE_KLINE_CACHE_DIR
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    fb = _load("icperf_freeze_baseline", FREEZE_SCRIPT)
    base = fb.default_request("ic_report_long")
    cwd = fb._prepare_cwd(tmp_path / "cwd")
    monkeypatch.chdir(cwd)
    svc = fb._ic_service(base, tmp_path / "registry.json")
    h5_path, meta_path = svc._materialize_features_for_ic(base["symbol"], base["timeframe"], base["config_hash"])
    sub_h5, sub_meta = fb._write_stage5_subset(Path(h5_path), Path(meta_path), REAL_SUBSET_COLS, fb.SEED,
                                               tmp_path / "subset")
    with h5py.File(sub_h5, "r") as f:
        g = f[f"{base['symbol']}/{base['timeframe']}"]
        all_cols = {n.decode() if isinstance(n, bytes) else str(n) for n in g["feature_names"][:]}
    assert len(all_cols) == REAL_SUBSET_COLS
    names = set(sorted(all_cols)[:REAL_FILTER_COLS])
    reader = create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR)

    def _analyze(feature_filter: Any) -> dict:
        override = svc._build_config_override(fb._ic_analyze_request({**base, "feature_filter": feature_filter}))
        return create_ic_analyzer(override).analyze(features_path=str(sub_h5), labels_path="",
                                                    meta_path=str(sub_meta), config_override=override,
                                                    kline_reader=reader)

    rep_full = _analyze(None)
    rep_filt = _analyze({"include_features": sorted(names)})
    md_full, md_filt = rep_full["metadata"], rep_filt["metadata"]
    assert md_full.get("feature_filter_applied") is not True and md_filt.get("feature_filter_applied") is True

    split_full = md_full.get("ic_train_test_split")
    assert isinstance(split_full, dict) and split_full.get("applied") is True, "L 格未走樣本外切分（前提不成立）"
    assert md_filt.get("ic_train_test_split") == split_full
    assert rep_filt["analysis_status"] == rep_full["analysis_status"]
    for key in GLOBAL_SPLIT_KEYS:
        assert (key in md_filt) == (key in md_full), key
        if key in md_full:
            assert _without_per_feature_counts(md_filt[key]) == _without_per_feature_counts(md_full[key]), key
    glob_full = {k for k, v in md_full.items() if isinstance(v, dict) and str(k) not in all_cols}
    glob_filt = {k for k, v in md_filt.items() if isinstance(v, dict) and str(k) not in all_cols}
    assert glob_filt == glob_full, (sorted(glob_full - glob_filt), sorted(glob_filt - glob_full))
    feat_keys = {str(k) for k in md_filt if str(k) in all_cols}
    assert feat_keys and feat_keys <= names, sorted(feat_keys - names)[:5]
