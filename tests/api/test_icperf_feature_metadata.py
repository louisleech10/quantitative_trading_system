"""ICPERF Task 0.4 ㉜（docs/ICPERF_SPEC.md v5.39）：IC 頁特徵 metadata 三欄（category、data_source、layer）自特徵庫
持久化來源取得並記來源（`metadata_source`，三欄同出一次欄名解析，單一字串同時適用三欄）；取不到 ⇒ 值 None＋原因，
不以預設值（`unknown`／`1`）冒充。

改前（`api/services/ic_analysis_service.py:3510-3536`）：只讀 `feature_catalog_cache.parquet`（CGSA 瀏覽頁之快取，特徵生成不產
出；A 格與全 repo 皆無此檔）之 category／layer、無 data_source；檔缺或欄缺 ⇒ `category: unknown`、`layer: 1` ⇒
`grouped_ic.by_category` 全落 unknown、`by_data_source` 空、`by_layer` 全為 1 而被判已驗。

oracle（與產品獨立，不經 `parse_feature_name`／`feature_layer`）：
- category／data_source：欄名為身分之唯一序列化（文法 `<source>_<tf>_<category>_<indicator>…`，段間 `_`、段內不含 `_`，
  `momentum/FeatureEngineering/feature_naming.py` 檔頭），測試端以 `str.split("_")` 取第 3、1 段；data_source 另與生成期
  ColumnGroup registry（`cgsa_work/manifest.json` 之 L1 群組 `data_source`）逐欄對證。
- layer：生成期落盤之 provenance（`provenance/raw_columns.parquet` 之 `layer` 欄，`LayerSource` 字面）對映 API 層字彙
  （`feature_naming.feature_layer` 之 `layer1`…`layer6_5`）。
- 分組 IC：以 oracle 之分組成員、`scipy.stats.spearmanr` 於逐特徵非缺值配對重算（任一側常數 ⇒ NaN）。
資料：A 格 `data_cache/numview_freeze_runs/A_BTCUSDT_1h__default`（真實 BTCUSDT 1h run，500 列×3,632 欄）與真實 kline
`data_cache/feature_klines/kline_cache.h5`；邊界案（不合文法、label 欄、catalog 錯值、快取格式世代、None 不入組）為明列輸入之秒級測試。
隔離：`_materialize_features_for_ic` 之快取目錄與 catalog 讀取皆為相對 cwd ⇒ 每案 chdir 至 tmp。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis.ic_engine import ICEngine
from momentum.factories import create_feature_library, create_kline_storage_manager

REPO = Path(__file__).resolve().parents[2]
A_CELL = REPO / "data_cache" / "numview_freeze_runs" / "A_BTCUSDT_1h__default"
A_FEATURES_ROOT = A_CELL / "features"
SYMBOL, TF, A_HASH = "BTCUSDT", "1h", "e0b9095cff6a9395c008accc86a3d269"
A_RUN_DIR = A_FEATURES_ROOT / SYMBOL / TF / A_HASH
KLINE_DIR = REPO / "data_cache" / "feature_klines"
FIELDS = ("category", "data_source", "layer")
#: `LayerSource`（column_group.py:12-18）→ `feature_naming.feature_layer` 字彙（feature_naming.py:364-380）
LAYER_FROM_PROVENANCE = {"L1": "layer1", "L2": "layer2", "L3": "layer3", "L4": "layer4", "L5": "layer5",
                         "L6": "layer6", "L6.5": "layer6_5"}
GROUPED_CONFIG = {"by_year": False, "by_quarter": False, "by_regime": False, "by_category": True,
                  "by_data_source": True, "by_layer": True, "method": "spearman"}
OLD_NS = 1_600_000_000_000_000_000
REL_TOL = 1e-12  # SPEC v5.39 Task 0.3 ④：直接統計量相對 1e-12

# 明列之真實欄名（取自 A 格 provenance；涵蓋 close／hl／meta 三來源、layer1／2／3／6 四層）
NAME_CLOSE_L1 = "close_1h_trend_BBANDS-Lower_13"
NAME_CLOSE_L3 = "close_1h_trend_BBANDS-Lower_13_Kurt-W13"
NAME_HL_L1 = "hl_1h_trend_MIDPRICE_13"
NAME_HL_L2 = "hl_1h_trend_MIDPRICE_13~144_Ratio"
NAME_META_L6 = "meta_1h_meta_time-day-of-week"


# ---------------------------------------------------------------- oracle


def oracle_name_fields(name: str) -> Tuple[str, str]:
    """欄名文法之獨立切段：(category, data_source)＝(第 3 段, 第 1 段)。"""
    segs = str(name).split("_")
    assert len(segs) >= 4, f"欄名段數不足：{name!r}"
    return segs[2], segs[0]


def oracle_spearman(x: pd.Series, y: pd.Series) -> float:
    """逐特徵非缺值配對之 Spearman；配對 < 2 或任一側常數 ⇒ NaN。"""
    xv = np.asarray(x, dtype=np.float64)
    yv = np.asarray(y, dtype=np.float64)
    mask = ~(np.isnan(xv) | np.isnan(yv))
    xv, yv = xv[mask], yv[mask]
    if xv.size < 2 or np.all(xv == xv[0]) or np.all(yv == yv[0]):
        return float("nan")
    return float(stats.spearmanr(xv, yv).correlation)


def assert_ic_equal(actual: float, expected: float, where: str) -> None:
    if np.isnan(expected):
        assert np.isnan(actual), f"{where}：預期 NaN，得 {actual!r}"
        return
    assert np.isfinite(actual), f"{where}：預期 {expected!r}，得 {actual!r}"
    assert abs(actual - expected) <= REL_TOL * max(abs(expected), 1e-300), f"{where}：{actual!r} ≠ {expected!r}"


def feature_entries(meta: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """`_meta.json` 之逐特徵項（dict 值；頂層 symbol 等為非 dict；run 身分 `ff_run_identity` 雖為 dict 但非特徵）。"""
    return {k: v for k, v in meta.items() if isinstance(v, dict) and k != "ff_run_identity"}


# ---------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def a_grid(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    """A 格：經生產端 `_materialize_features_for_ic` 物化之 `_meta.json`，與同一 FeatureLibrary 載入之特徵矩陣。"""
    assert A_RUN_DIR.is_dir(), f"A 格資料不存在（FAIL，非 skip）：{A_RUN_DIR}"
    work = tmp_path_factory.mktemp("icperf_meta_a")
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(work)
        service = ICAnalysisService()
        service._feature_library = create_feature_library(A_FEATURES_ROOT)  # noqa: SLF001
        features_df, _identity = service._feature_library.load_with_identity(SYMBOL, TF, config_hash=A_HASH)
        _h5_path, meta_path = service._materialize_features_for_ic(SYMBOL, TF, A_HASH)
        meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    provenance = pd.read_parquet(A_RUN_DIR / "provenance" / "raw_columns.parquet", columns=["output_column", "layer"])
    registry = json.loads((A_CELL / "cgsa_work" / "manifest.json").read_text(encoding="utf-8"))
    return {"features": features_df, "meta": meta, "provenance": provenance, "registry": registry}


# ---------------------------------------------------------------- 真實資料（A 格）


@pytest.mark.requires_kline
def test_a_grid_metadata_three_fields_equal_persisted_values(a_grid: Dict[str, Any]) -> None:
    """㉜ 驗證：A 格請求之 metadata 三欄與特徵庫持久化值逐欄相等、來源 `feature_name`、無預設值冒充；
    三欄各 ≥ 2 種值（分組 IC 三鍵才有 ≥ 2 組）。"""
    entries = feature_entries(a_grid["meta"])
    prov = a_grid["provenance"]
    prov_layer = dict(zip(prov["output_column"].astype(str), prov["layer"]))
    assert set(entries) == set(map(str, a_grid["features"].columns)) == set(prov_layer), "metadata 欄集合≠特徵庫欄集合"
    assert a_grid["meta"].get("feature_metadata_version") == 2, "缺 metadata 格式世代（舊格式快取將被沿用）"

    for name, entry in entries.items():
        category, source = oracle_name_fields(name)
        assert entry["name"] == name
        assert entry["category"] == category, f"{name}：category {entry['category']!r} ≠ 欄名段 {category!r}"
        assert entry["data_source"] == source, f"{name}：data_source {entry['data_source']!r} ≠ 欄名段 {source!r}"
        assert prov_layer[name] in LAYER_FROM_PROVENANCE, f"provenance 出現未對映之層 {prov_layer[name]!r}"
        assert entry["layer"] == LAYER_FROM_PROVENANCE[prov_layer[name]], (
            f"{name}：layer {entry['layer']!r} ≠ provenance {prov_layer[name]!r}")
        assert entry["metadata_source"] == "feature_name", f"{name}：來源 {entry['metadata_source']!r}"
        assert "metadata_missing_reason" not in entry, f"{name}：可得卻記缺：{entry.get('metadata_missing_reason')!r}"

    # data_source 與生成期 ColumnGroup registry 逐欄對證（L1 群組之 data_source 為輸入來源；L2 起為 `derived` 不對證）
    checked = 0
    for group in a_grid["registry"]["groups"]:
        if group["layer"] != "L1" or group["data_source"] in ("derived", "mixed"):
            continue
        for untagged in group["columns"]:
            head, rest = str(untagged).split("_", 1)
            tagged = f"{head}_{group['timeframe']}_{rest}"
            assert entries[tagged]["data_source"] == group["data_source"], f"{tagged}：≠ registry {group['data_source']!r}"
            checked += 1
    assert checked == sum(1 for v in prov_layer.values() if v == "L1"), "registry L1 欄數≠provenance L1 欄數（對證不完整）"

    for field in FIELDS:
        values = {entry[field] for entry in entries.values()}
        assert len(values) >= 2, f"{field} 只有 {values!r}（分組 IC 該鍵不足 2 組）"


@pytest.mark.requires_kline
def test_a_grid_grouped_ic_by_metadata_matches_scipy(a_grid: Dict[str, Any]) -> None:
    """㉜ 驗證：以 A 格 metadata 跑 `ICEngine.compute_grouped_ic` 之 by_category／by_data_source／by_layer 各 ≥ 2 組，
    組別與成員等於 oracle 分組，逐組逐特徵以 scipy 重算相等（真實 kline 一根前向報酬為標籤）。
    特徵子集：每個 (category, data_source, layer) 組合取 sorted 前 4 欄（每組至少一欄，含 NaN 欄與無 NaN 欄兩條 IC 路徑）。"""
    features_all: pd.DataFrame = a_grid["features"]
    entries = feature_entries(a_grid["meta"])
    prov_layer = dict(zip(a_grid["provenance"]["output_column"].astype(str), a_grid["provenance"]["layer"]))
    combos: Dict[Tuple[str, str, str], List[str]] = {}
    for name in sorted(map(str, features_all.columns)):
        category, source = oracle_name_fields(name)
        combos.setdefault((category, source, LAYER_FROM_PROVENANCE[prov_layer[name]]), []).append(name)
    subset = [n for members in combos.values() for n in members[:4]]
    features = features_all[subset]

    kline = create_kline_storage_manager(cache_dir=str(KLINE_DIR)).read_klines(SYMBOL, TF)
    close = pd.Series(kline["close"].to_numpy(dtype=np.float64),
                      index=pd.to_datetime(kline["timestamp"].to_numpy(), unit="s"))
    label = (close.shift(-1) / close - 1.0).reindex(features.index).rename("label")
    assert int(label.notna().sum()) >= 400, f"前提不成立：標籤有限列 {int(label.notna().sum())}"
    raw = pd.DataFrame({"close": close.reindex(features.index)})

    grouped = ICEngine({"methods": ["spearman"]}).compute_grouped_ic(features, label, raw, a_grid["meta"], GROUPED_CONFIG)

    has_nan = features.isna().any()
    assert bool(has_nan.any()) and bool((~has_nan).any()), "前提不成立：子集未同時含 NaN 欄與無 NaN 欄"
    for key, field_idx in (("by_category", 0), ("by_data_source", 1), ("by_layer", 2)):
        expected_groups: Dict[str, List[str]] = {}
        for combo, members in combos.items():
            expected_groups.setdefault(combo[field_idx], []).extend(members[:4])
        actual = grouped[key]
        assert len(actual) >= 2, f"{key} 只有 {list(actual)}"
        assert set(actual) == set(expected_groups), f"{key} 組別 {sorted(actual)} ≠ oracle {sorted(expected_groups)}"
        for group, members in expected_groups.items():
            assert set(actual[group]) == set(members), f"{key}/{group} 成員不符"
            for feature in members:
                assert_ic_equal(float(actual[group][feature]), oracle_spearman(features[feature], label),
                                f"{key}/{group}/{feature}")


# ---------------------------------------------------------------- 明列邊界輸入（秒級）


def test_unparseable_and_label_names_recorded_missing_not_defaulted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """㉜「取不到 ⇒ 記原因、不以預設值冒充」：不合文法之欄名與 `label_*` 欄 ⇒ 三欄 None、來源 `missing`、記原因；
    合文法者三欄取自欄名身分、來源 `feature_name`。"""
    monkeypatch.chdir(tmp_path)
    bad, label_col = "legacy_rsi14", "label_return_1"
    meta = ICAnalysisService()._build_ic_metadata_from_run(SYMBOL, TF, None, [NAME_HL_L2, bad, label_col])

    good = meta[NAME_HL_L2]
    assert (good["category"], good["data_source"], good["layer"]) == ("trend", "hl", "layer2")
    assert good["metadata_source"] == "feature_name" and "metadata_missing_reason" not in good

    for name, reason_prefix in ((bad, "feature_name_unparseable"), (label_col, "label_column")):
        entry = meta[name]
        assert entry["name"] == name
        assert all(entry[f] is None for f in FIELDS), f"{name}：以預設值冒充 {entry!r}"
        assert entry["metadata_source"] == "missing"
        assert str(entry["metadata_missing_reason"]).startswith(reason_prefix), entry["metadata_missing_reason"]


def test_catalog_only_enumerates_names_values_from_feature_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """catalog 存在而呼叫端未給欄名（`_write_ic_meta_json` 路徑）⇒ 欄名取自 catalog，三欄仍取自欄名身分：
    catalog 之缺值（None）與錯值不得流入（改前：None ⇒ unknown／1，錯值原樣沿用）。"""
    monkeypatch.chdir(tmp_path)
    catalog_dir = tmp_path / "data_cache" / "features" / SYMBOL / TF / "h1"
    catalog_dir.mkdir(parents=True)
    pd.DataFrame([
        {"name": NAME_CLOSE_L3, "category": None, "layer": None},
        {"name": NAME_META_L6, "category": "momentum", "layer": "layer9"},
    ]).to_parquet(catalog_dir / "feature_catalog_cache.parquet", index=False)

    meta = ICAnalysisService()._build_ic_metadata_from_run(SYMBOL, TF, "h1", [])
    assert set(feature_entries(meta)) == {NAME_CLOSE_L3, NAME_META_L6}
    assert {f: meta[NAME_CLOSE_L3][f] for f in FIELDS} == {"category": "trend", "data_source": "close", "layer": "layer3"}
    assert {f: meta[NAME_META_L6][f] for f in FIELDS} == {"category": "meta", "data_source": "meta", "layer": "layer6"}


def _explicit_frame() -> pd.DataFrame:
    """明列輸入：12 列小時軸，四欄（兩來源、三層）＋不合文法欄；值為固定整數序列之排列（含一個 NaN）。"""
    index = pd.date_range("2024-01-01", periods=12, freq="h")
    return pd.DataFrame({
        NAME_CLOSE_L1: [3, 1, 4, 1.5, 5, 9, 2, 6, 5.5, 3.5, 8, 7],
        NAME_CLOSE_L3: [2, 7, 1, 8, 2.5, 8.5, 1.5, 8.2, 2.8, 4, 5, np.nan],
        NAME_HL_L1: [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, -1],
        NAME_HL_L2: [1, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10, 12],
        "legacy_rsi14": [5, 4, 6, 3, 7, 2, 8, 1, 9, 0, 10, -1],
    }, index=index, dtype=np.float64)


def test_missing_metadata_not_grouped_by_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """None 值不成組（`ic_engine._compute_metadata_groups` 跳過 None）：不合文法欄不入任何分組，其餘分組＝欄名身分；
    逐組逐特徵 scipy 重算相等。改前：不合文法欄落 `unknown` 組、`by_data_source` 空、`by_layer` 全為 1。"""
    monkeypatch.chdir(tmp_path)
    frame = _explicit_frame()
    label = pd.Series([0.3, -0.1, 0.2, 0.05, -0.4, 0.6, -0.2, 0.1, 0.0, 0.25, -0.05, 0.15], index=frame.index)
    meta = ICAnalysisService()._build_ic_metadata_from_run(SYMBOL, TF, None, list(frame.columns))
    grouped = ICEngine({"methods": ["spearman"]}).compute_grouped_ic(
        frame, label, pd.DataFrame({"close": np.arange(12.0) + 100}, index=frame.index), meta, GROUPED_CONFIG)

    expected = {
        "by_category": {"trend": [NAME_CLOSE_L1, NAME_CLOSE_L3, NAME_HL_L1, NAME_HL_L2]},
        "by_data_source": {"close": [NAME_CLOSE_L1, NAME_CLOSE_L3], "hl": [NAME_HL_L1, NAME_HL_L2]},
        "by_layer": {"layer1": [NAME_CLOSE_L1, NAME_HL_L1], "layer2": [NAME_HL_L2], "layer3": [NAME_CLOSE_L3]},
    }
    for key, groups in expected.items():
        assert set(grouped[key]) == set(groups), f"{key}：{sorted(grouped[key])}"
        for group, members in groups.items():
            assert set(grouped[key][group]) == set(members)
            for feature in members:
                assert_ic_equal(float(grouped[key][group][feature]), oracle_spearman(frame[feature], label),
                                f"{key}/{group}/{feature}")


class _StubIdentity:
    """非 legacy 之 run 身分（沿用判定只讀 `legacy` 與 `to_dict()`）。"""

    legacy = False

    def to_dict(self) -> Dict[str, Any]:
        return {"symbol": SYMBOL, "tf": TF, "config_hash": "h1", "content_sha256": "a" * 64}


class _StubLibrary:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def load_with_identity(self, symbol: str, timeframe: str, *, config_hash: Optional[str] = None) -> Any:
        return self._frame.copy(), _StubIdentity()


def test_stale_metadata_format_rewrites_meta_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """交接快取：h5 與 `_meta.json` 身分相同而 `_meta.json` 為改前格式（無 `feature_metadata_version`、以預設值填）⇒
    只重寫 `_meta.json`（h5 不重寫）且新 meta 帶世代與三欄真值；再呼叫一次 ⇒ 兩者皆沿用。改前：舊 meta 被沿用。"""
    monkeypatch.chdir(tmp_path)
    writes: List[str] = []
    real_write = ICAnalysisService._write_features_h5

    def counting(path: Any, *args: Any, **kwargs: Any) -> Any:
        writes.append(str(path))
        return real_write(path, *args, **kwargs)

    monkeypatch.setattr(ICAnalysisService, "_write_features_h5", staticmethod(counting))
    service = ICAnalysisService()
    service._feature_library = _StubLibrary(_explicit_frame().drop(columns=["legacy_rsi14"]))  # noqa: SLF001
    h5_path, meta_path = (Path(p) for p in service._materialize_features_for_ic(SYMBOL, TF, "h1"))
    assert len(writes) == 1

    stale = json.loads(meta_path.read_text(encoding="utf-8"))
    stale.pop("feature_metadata_version", None)
    for name in feature_entries(stale):
        stale[name] = {"name": name, "category": "unknown", "layer": 1}
    meta_path.write_text(json.dumps(stale, ensure_ascii=False), encoding="utf-8")
    for p in (h5_path, meta_path):
        os.utime(p, ns=(OLD_NS, OLD_NS))
    writes.clear()

    service._materialize_features_for_ic(SYMBOL, TF, "h1")
    assert writes == [] and h5_path.stat().st_mtime_ns == OLD_NS, "meta 格式過期卻重寫 h5"
    assert meta_path.stat().st_mtime_ns != OLD_NS, "改前格式之 _meta.json 被沿用"
    fresh = json.loads(meta_path.read_text(encoding="utf-8"))
    assert fresh.get("feature_metadata_version") == 2
    assert fresh["ff_run_identity"] == _StubIdentity().to_dict()
    assert {f: fresh[NAME_HL_L1][f] for f in FIELDS} == {"category": "trend", "data_source": "hl", "layer": "layer1"}

    for p in (h5_path, meta_path):
        os.utime(p, ns=(OLD_NS, OLD_NS))
    service._materialize_features_for_ic(SYMBOL, TF, "h1")
    assert writes == [] and h5_path.stat().st_mtime_ns == OLD_NS and meta_path.stat().st_mtime_ns == OLD_NS, "現行格式卻重寫"


@pytest.mark.requires_kline
@pytest.mark.parametrize("labels_path", [None, "labels.h5"])
def test_cross_sectional_run_passes_close_and_metadata(labels_path: Optional[str]) -> None:
    """ICPERF Task 0.4 ㊱ 服務端接線：跨標的請求把逐列收盤（kline 導出標籤時）與逐特徵 metadata 交給
    `analyze_cross_sectional`。oracle：收盤以 h5py 直讀 `kline_cache.h5` 之 (timestamp, close) 逐 (時點, 標的) 對照；
    metadata 以欄名 `split("_")` 取第 3、1 段（同檔頭 oracle）。給 labels_path ⇒ 不讀 kline、close 為 None。"""
    import asyncio
    from unittest.mock import MagicMock

    import h5py

    from api.models.ic_models import ICAnalyzeRequest

    symbols = ["BTCUSDT", "ETHUSDT"]
    kline: Dict[str, pd.Series] = {}
    with h5py.File(REPO / "data_cache" / "feature_klines" / "kline_cache.h5", "r") as handle:
        for sym in symbols:
            data = handle[f"{sym}/{TF}/data"][-400:]
            kline[sym] = pd.Series(
                data["close"].astype(np.float64),
                index=pd.DatetimeIndex(pd.to_datetime(data["timestamp"].astype(np.int64), unit="s")),
            )
    frames: Dict[str, pd.DataFrame] = {}
    for offset, sym in enumerate(symbols):
        idx = kline[sym].index[:-1]
        idx = idx[(np.arange(len(idx)) % (5 + offset)) != 0]  # 兩標的各缺不同根 ⇒ 驗逐標的對齊
        values = np.log(kline[sym]).diff().reindex(idx).to_numpy()
        frames[sym] = pd.DataFrame({NAME_CLOSE_L1: values, NAME_HL_L1: values[::-1].copy()}, index=idx)

    service = ICAnalysisService()
    library = MagicMock()
    library.load_multi.return_value = frames
    service._feature_library = library  # noqa: SLF001
    analyzer = MagicMock()
    analyzer.analyze_cross_sectional.return_value = {"summary_table": []}
    request = ICAnalyzeRequest(
        features_path="unused.h5", mode="cross_sectional", symbols=symbols, timeframe=TF, labels_path=labels_path
    )
    service._tasks["t-xs"] = {"task_id": "t-xs", "status": "running", "result": None, "error": None}  # noqa: SLF001
    asyncio.run(service._run_analysis("t-xs", analyzer, request, None))  # noqa: SLF001

    kwargs = analyzer.analyze_cross_sectional.call_args.kwargs
    metadata = kwargs["feature_metadata"]
    for name in (NAME_CLOSE_L1, NAME_HL_L1):
        parts = name.split("_")
        assert (metadata[name]["category"], metadata[name]["data_source"]) == (parts[2], parts[0])
    if labels_path is not None:
        assert kwargs["close"] is None
        return
    close = kwargs["close"]
    features = kwargs["features"]
    assert close.index.equals(features.index)
    expected = np.array(
        [kline[sym].loc[ts] for ts, sym in features.index], dtype=np.float64
    )
    np.testing.assert_array_equal(close.to_numpy(dtype=np.float64), expected)
    assert close.dtype == np.float64
