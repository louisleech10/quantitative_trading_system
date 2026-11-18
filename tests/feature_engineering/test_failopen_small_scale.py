"""TESTSEL I10 姊妹測試：failopen v3 大型基準測試所經程式路徑之小規模驗證（真實 kline 短窗、少量欄）。

大型測試 `test_failopen_correctness.py::test_v3_ethusdt_1h_matches_frozen_baseline`（365 天、91,809 欄，產物含 13 個
CGSA shard 檔）與 `::test_v3_multi_tf_btc_matches_frozen_baseline`（1h 主＋12h 訓練，179,456 欄）原樣保留、列豁免；
本檔以凍結腳本同類設定（close 來源、縮尾開、fracdiff／ADF／rank／zscore／gaussian 關；L1 精簡為 trend 兩指標、L2–L4
預設）驗其獨有路徑：
① CGSA 分片串流：分片目標壓到 64 KiB 使少量欄亦走分片（registry 分片寫入、分片讀回、L7 raw 分片串流落盤），
   斷言分片 run 與不分片 run 之 registry 各群組原生值、落盤 raw 之值逐位元相同，且確實一側有分片、一側沒有；
② 多週期合併（粗週期 12h 對齊到細週期 1h 主軸、compact 對齊＋idx_map 落盤＋讀回展開）：攔截產線 as-of 索引，
   與手寫獨立 oracle 逐元素相等；每個 compact 群組之落盤 idx_map＝oracle，讀回之邏輯矩陣＝依 oracle 由原生列展開
   （逐位元，含無來源列為 NaN）。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.utils import hardware_utils
from tests.feature_engineering.test_failopen_correctness import (
    BASELINE_SYMBOL,
    ETH_SYMBOL,
    NS_PER_SECOND,
    _hash_dataframe_canonical,
    _independent_asof_index_map,
    _make_factory,
    _narrow_atomic_indicators,
    _persisted_frame,
    _short_window_dates,
)

TINY_SHARD_BYTES = 64 * 1024
WINDOW_DAYS = 14


def _payload(training: list[str], primary: str) -> dict:
    """凍結腳本 `_fixed_config_payload` 同類設定（縮尾開、其餘前處理關、close 來源）＋精簡 L1。"""
    return {
        "timeframes": {"primary": primary, "training": list(training), "alignment": "point_in_time",
                       "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "preprocessing": {
            "winsorization": {"enabled": True},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
        },
        "atomic_indicators": _narrow_atomic_indicators(),
    }


def _generate(monkeypatch: pytest.MonkeyPatch, root: Path, *, persist: bool, shard_bytes: int | None):
    """呼叫順序＝先不分片、後分片（分片目標之替身由 monkeypatch 於測試結束還原）。"""
    if shard_bytes is not None:
        monkeypatch.setattr(hardware_utils, "get_cgsa_shard_bytes", lambda: shard_bytes)
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(root / "cgsa"))
    factory = _make_factory(monkeypatch, root, feature_root=root / "features")
    start, end = _short_window_dates(WINDOW_DAYS, ETH_SYMBOL, "1h")
    result = factory.generate_features(ETH_SYMBOL, "1h", config_override=_payload(["1h"], "1h"),
                                       force_regenerate=True, start_date=start, end_date=end, persist=persist)
    return factory, result


def _registry_values(registry) -> dict:
    out = {}
    for gid, group in registry.iter_all():
        data = np.asarray(registry.load_data_native(gid), dtype=np.float32)
        out[gid] = (tuple(group.columns), np.isnan(data), np.where(np.isnan(data), 0, data).view(np.uint32))
    return out


@pytest.mark.requires_kline
def test_cgsa_sharded_registry_equals_unsharded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """① registry：分片 run 與不分片 run 之群組集合、欄序、原生值與 NaN 位置逐位元相同。"""
    plain_factory, _ = _generate(monkeypatch, tmp_path / "plain", persist=False, shard_bytes=None)
    plain_registry = plain_factory._cgsa_registry
    assert plain_registry is not None
    assert not any(g.is_sharded for _, g in plain_registry.iter_all()), "不分片 run 不得有分片群組（對照組失效）"
    plain = _registry_values(plain_registry)

    shard_factory, _ = _generate(monkeypatch, tmp_path / "shard", persist=False, shard_bytes=TINY_SHARD_BYTES)
    shard_registry = shard_factory._cgsa_registry
    sharded_ids = [gid for gid, g in shard_registry.iter_all() if g.is_sharded]
    assert sharded_ids, "分片目標壓小後無任何分片群組（分片路徑未走到）"
    sharded = _registry_values(shard_registry)

    assert sorted(sharded) == sorted(plain)
    bad = [gid for gid in plain
           if plain[gid][0] != sharded[gid][0] or not np.array_equal(plain[gid][1], sharded[gid][1])
           or not np.array_equal(plain[gid][2], sharded[gid][2])]
    assert bad == [], f"分片與不分片之群組值不等：{bad[:5]}（分片群組 {len(sharded_ids)} 個）"


@pytest.mark.requires_kline
def test_cgsa_sharded_persisted_raw_equals_unsharded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """① 落盤：分片 run 之 L7 raw（分片串流寫出）與不分片 run 逐位元相同；分片 run 確有 shard 檔、不分片 run 沒有。"""
    plain_factory, plain_result = _generate(monkeypatch, tmp_path / "plain", persist=True, shard_bytes=None)
    plain_hash = _hash_dataframe_canonical(_persisted_frame(plain_factory, plain_result, ETH_SYMBOL, "1h"))
    plain_files = [p.name for p in (tmp_path / "plain" / "features").rglob("*") if p.is_file()]

    shard_factory, shard_result = _generate(monkeypatch, tmp_path / "shard", persist=True, shard_bytes=TINY_SHARD_BYTES)
    shard_hash = _hash_dataframe_canonical(_persisted_frame(shard_factory, shard_result, ETH_SYMBOL, "1h"))
    shard_files = [p.name for p in (tmp_path / "shard" / "features").rglob("*") if p.is_file()]

    assert not [n for n in plain_files if "shard" in n], "不分片 run 不得有 shard 檔（對照組失效）"
    assert [n for n in shard_files if "shard" in n], "分片 run 無 shard 落盤檔（分片串流路徑未走到）"
    assert shard_hash == plain_hash


def _coarse_to_fine_compact_problems(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, coarse_tf: str) -> list[str]:
    """1h 主＋`coarse_tf` 訓練之 compact 合併對獨立 oracle 之不符清單（空＝全等）；同下方 12h 測試之檢查（以清單回報）。"""
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    captured: list[tuple[np.ndarray, np.ndarray, int]] = []
    original_build = TimeframeAligner.build_asof_index_map

    def _capturing_build(primary_s, source_s, *, source_dur_ns, primary_dur_ns, mode):  # noqa: ANN001
        idx_map = original_build(primary_s, source_s, source_dur_ns=source_dur_ns,
                                 primary_dur_ns=primary_dur_ns, mode=mode)
        if len(source_s) < len(primary_s):
            oracle = _independent_asof_index_map(
                np.asarray(primary_s), np.asarray(source_s), source_dur_s=int(source_dur_ns // NS_PER_SECOND),
                primary_dur_s=int(primary_dur_ns // NS_PER_SECOND), mode=str(mode))
            captured.append((oracle, np.asarray(idx_map), int(source_dur_ns // NS_PER_SECOND)))
        return idx_map

    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "1")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa"))
    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(_capturing_build))
    factory = _make_factory(monkeypatch, tmp_path, feature_root=tmp_path / "features")
    start, end = _short_window_dates(WINDOW_DAYS)
    result = factory.generate_features(BASELINE_SYMBOL, "1h", config_override=_payload(["1h", coarse_tf], "1h"),
                                       force_regenerate=True, start_date=start, end_date=end, persist=False)
    problems: list[str] = []
    if int(result.feature_count) <= 0:
        problems.append("feature_count=0")
    from momentum.core.constants import TIMEFRAME_SECONDS

    mine = [(o, p) for o, p, dur in captured if dur == TIMEFRAME_SECONDS[coarse_tf]]
    if not mine:
        problems.append(f"未攔截到 {coarse_tf}→1h 之 as-of 索引")
    problems += [f"idx_map≠oracle#{i}" for i, (o, p) in enumerate(mine) if not np.array_equal(o, p)]
    problems += [f"oracle 空轉#{i}" for i, (o, _p) in enumerate(mine) if not (o >= 0).any()]
    registry = factory._cgsa_registry
    compact = [(gid, g) for gid, g in registry.iter_all()
               if g.is_compact_aligned and g.alignment.source_timeframe == coarse_tf]
    if not compact:
        problems.append(f"無 {coarse_tf} compact 對齊群組")
    for gid, group in compact:
        stored = np.load(group.alignment.idx_map_path, allow_pickle=False)
        if not any(o.shape == stored.shape and np.array_equal(o, stored) for o, _p in mine):
            problems.append(f"{gid}：落盤 idx_map≠oracle")
            continue
        native = np.asarray(registry.load_data_native(gid), dtype=np.float32)
        expected = np.full((stored.shape[0], native.shape[1]), np.nan, dtype=np.float32)
        valid = stored >= 0
        expected[valid] = native[stored[valid]]
        logical = np.asarray(registry.load_data(gid), dtype=np.float32)
        finite = ~np.isnan(expected)
        if logical.shape != expected.shape or not np.array_equal(np.isnan(logical), np.isnan(expected)) or \
                not np.array_equal(logical[finite].view(np.uint32), expected[finite].view(np.uint32)):
            problems.append(f"{gid}：讀回展開≠oracle")
    return problems


@pytest.mark.requires_kline
def test_multi_tf_fine_1h_coarse_4h_compact_alignment_matches_oracle(monkeypatch: pytest.MonkeyPatch,
                                                                     tmp_path: Path) -> None:
    """ffprod gate B 格（1h＋4h）之合併路徑小規模姊妹：4h→1h（週期比 4，非 12h 之 12）之 as-of 索引、落盤 idx_map、讀回展開
    皆等於獨立 oracle（逐位元）。"""
    assert _coarse_to_fine_compact_problems(monkeypatch, tmp_path, "4h") == []


@pytest.mark.requires_kline
def test_multi_tf_coarse_to_fine_compact_alignment_matches_oracle(monkeypatch: pytest.MonkeyPatch,
                                                                  tmp_path: Path) -> None:
    """② 1h 主＋12h 訓練（同凍結腳本多週期單元之方向）：12h→1h 之 as-of 索引、落盤 idx_map 與讀回展開皆等於獨立 oracle。"""
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    captured: list[tuple[np.ndarray, np.ndarray]] = []
    original_build = TimeframeAligner.build_asof_index_map

    def _capturing_build(primary_s, source_s, *, source_dur_ns, primary_dur_ns, mode):  # noqa: ANN001
        idx_map = original_build(primary_s, source_s, source_dur_ns=source_dur_ns,
                                 primary_dur_ns=primary_dur_ns, mode=mode)
        if len(source_s) < len(primary_s):
            oracle = _independent_asof_index_map(
                np.asarray(primary_s), np.asarray(source_s), source_dur_s=int(source_dur_ns // NS_PER_SECOND),
                primary_dur_s=int(primary_dur_ns // NS_PER_SECOND), mode=str(mode))
            captured.append((oracle, np.asarray(idx_map)))
        return idx_map

    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "1")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa"))
    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(_capturing_build))
    factory = _make_factory(monkeypatch, tmp_path, feature_root=tmp_path / "features")
    start, end = _short_window_dates(WINDOW_DAYS)
    result = factory.generate_features(BASELINE_SYMBOL, "1h", config_override=_payload(["1h", "12h"], "1h"),
                                       force_regenerate=True, start_date=start, end_date=end, persist=False)
    assert int(result.feature_count) > 0
    assert captured, "未攔截到任何粗→細之 as-of 索引（多週期合併路徑未走到）"
    for oracle, prod in captured:
        assert np.array_equal(oracle, prod)
        assert (oracle >= 0).any(), "oracle 無任何有效對應（空轉）"

    registry = factory._cgsa_registry
    compact = [(gid, g) for gid, g in registry.iter_all() if g.is_compact_aligned]
    assert compact, "無 compact 對齊群組（compact 合併路徑未走到）"
    oracles = [o for o, _ in captured]
    for gid, group in compact:
        stored = np.load(group.alignment.idx_map_path, allow_pickle=False)
        assert any(o.shape == stored.shape and np.array_equal(o, stored) for o in oracles), gid
        native = np.asarray(registry.load_data_native(gid), dtype=np.float32)
        expected = np.full((stored.shape[0], native.shape[1]), np.nan, dtype=np.float32)
        valid = stored >= 0
        expected[valid] = native[stored[valid]]
        logical = np.asarray(registry.load_data(gid), dtype=np.float32)
        assert logical.shape == expected.shape, gid
        assert np.array_equal(np.isnan(logical), np.isnan(expected)), gid
        finite = ~np.isnan(expected)
        assert np.array_equal(logical[finite].view(np.uint32), expected[finite].view(np.uint32)), gid
