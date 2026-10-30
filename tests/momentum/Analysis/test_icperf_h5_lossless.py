"""ICPERF Task 0.4 ⑫（docs/ICPERF_SPEC.md v5.35 第 138 行、「邊界」段末 v5.34 輸出契約增列）：IC 交接 h5／filtered HDF5
逐欄 float32 無損判定之具名 oracle 測試。

定義（SPEC ⑫「修正」欄）：欄之 float64 有限值 x 轉 float32 後須（a）有限性逐元不變（不溢位為 ±inf）且（b）相異有限值
個數不變（不併值 ⇒ 排名與 Spearman 與 float64 逐位元相同）；原生 float16／float32 欄恆無損。無損欄存 float32
`features`；不無損欄存 float64 `features_f64`，`feature_names` 為全序、`f64_columns`（int 索引）記不無損欄位置；讀端依全序
還原原欄序與 dtype；舊格式檔（無 `features_f64`）讀回不變。

oracle＝`_oracle_lossless`（numpy `np.unique`／`np.isfinite` 逐欄獨立重算，**不呼叫產品 helper**）與 `scipy.stats`
（`spearmanr`／`pearsonr`）；資料＝真實 kline `data_cache/feature_klines/kline_cache.h5`（BTCUSDT 1h；價格水準欄＝EMA233
of close、OBV 型欄＝以真實 volume 累積），禁合成 fixture 取代真實資料驗收。

路徑清單（每路一案，非同案多幣種重複）：
- P1 全無損（真實 2,000 列；原生 float32 欄＋float64 欄而無併值）⇒ 檔案佈局與舊格式同（無 `features_f64`）、`features`
  與舊寫法位元相同；
- P2 部分不無損（真實全史；EMA233／OBV 型欄併值）⇒ `features_f64` 恰為 oracle 判不無損之欄、`f64_columns` 為其全序索引；
  另證舊寫法（一律 float32）在同資料上 Spearman 與 float64 不同（測試可鑑別）；
- P3 全不無損（`features` 寬 0）；
- P4 含 NaN／±inf 與溢位（float64 有限而 float32 溢位為 inf ⇒ 判準 (a)）；
- P5 舊格式檔讀回不變；
- P6 寫端兩處（交接 h5 `_write_features_h5`、filtered HDF5 `save_filtered_features`）與讀端（orchestrator
  `_load_features_hdf5`、`scripts/ic1eb_b5_replay.py` `_load_h5_features`、`scripts/icperf_freeze_baseline.py`
  `_write_stage5_subset`）皆經測；
- P7 `f64_columns` 損壞（越界／重複／長度不符）⇒ 讀端 fail-closed；
- 邊界單元（快速層，精確 oracle）：相鄰相異值相差小於／大於一個 float32 ulp、溢位、下溢併 0、原生 float16／float32、
  全 NaN 欄、零列。
"""

from __future__ import annotations

import importlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import h5py
import numpy as np
import pandas as pd
import pytest
from scipy import stats

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
HEAVY_MARKERS = ("slow", "requires_kline")
PRODUCT_MODULE = "momentum.core.h5_feature_precision"
PEARSON_REL_TOL = 1e-6
HORIZON = 5
SYMBOL = "BTCUSDT"
TF = "1h"


# ── 共用監看（同 test_icperf_deep_factor_return.py） ──────────────────────────────────────────────


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """標 slow 或 requires_kline 而未在共用監看下執行 ⇒ True（共用監看對子行程恆注入 `WATCHDOG_STACK_FILE`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """本檔真實資料測試於執行端自證經共用監看，未經即 FAIL。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


# ── 獨立 oracle（numpy／scipy；不呼叫產品 helper） ────────────────────────────────────────────────


def _oracle_lossless(col: pd.Series) -> bool:
    """SPEC ⑫ 判準之逐欄獨立重算：原生 float16／float32 ⇒ True；否則 float64 值 x 與 x.astype(float32) 須有限性逐元相同
    且相異有限值個數（`np.unique`）相同。"""
    if col.dtype in (np.float16, np.float32):
        return True
    x = np.asarray(col, dtype=np.float64)
    y = x.astype(np.float32)
    fx, fy = np.isfinite(x), np.isfinite(y)
    if not np.array_equal(fx, fy):
        return False
    return int(np.unique(x[fx]).size) == int(np.unique(y[fy]).size)


def _oracle_mask(frame: pd.DataFrame) -> np.ndarray:
    return np.array([_oracle_lossless(frame.iloc[:, i]) for i in range(frame.shape[1])], dtype=bool)


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    return float(stats.spearmanr(x, y).statistic)


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    return float(stats.pearsonr(x, y).statistic)


def _same_float(a: float, b: float) -> bool:
    """逐位元相同（NaN 視為相同）。"""
    return (math.isnan(a) and math.isnan(b)) or a == b


def _assert_ic_preserved(inp: pd.DataFrame, back: pd.DataFrame, label: pd.Series, *, tag: str) -> None:
    """寫讀往返後：每欄 Spearman（scipy）與 float64 輸入逐位元相同、Pearson 相對差 ≤ 1e-6（兩者同一有限遮罩）。"""
    lab = np.asarray(label, dtype=np.float64)
    for name in inp.columns:
        x = np.asarray(inp[name], dtype=np.float64)
        z = np.asarray(back[name], dtype=np.float64)
        assert np.array_equal(np.isfinite(x), np.isfinite(z)), f"{tag}:{name}：有限性遮罩於往返後改變"
        m = np.isfinite(x) & np.isfinite(lab)
        assert int(m.sum()) >= 30, f"前提：{tag}:{name} 有效對 ≥ 30"
        s_in, s_back = _spearman(x[m], lab[m]), _spearman(z[m], lab[m])
        assert _same_float(s_in, s_back), f"{tag}:{name}：Spearman {s_back!r} != float64 輸入 {s_in!r}"
        p_in, p_back = _pearson(x[m], lab[m]), _pearson(z[m], lab[m])
        assert abs(p_back - p_in) <= PEARSON_REL_TOL * abs(p_in), \
            f"{tag}:{name}：Pearson 相對差 {abs(p_back - p_in) / abs(p_in):.3e} > 1e-6"


# ── 真實資料 ──────────────────────────────────────────────────────────────────────────────────────


def _real_kline(rows: int | None) -> pd.DataFrame:
    """真實 BTCUSDT 1h（kline 檔原生 float32 欄）；rows=None ⇒ 全史。"""
    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        ds = f[f"{SYMBOL}/{TF}/data"]
        data = ds[:] if rows is None else ds[-rows:]
    idx = pd.DatetimeIndex(pd.to_datetime(data["timestamp"].astype("int64"), unit="s"), name="timestamp")
    return pd.DataFrame({"close": data["close"], "volume": data["volume"]}, index=idx)


def _real_features(rows: int | None) -> Tuple[pd.DataFrame, pd.Series]:
    """因果特徵（只用 0..t）：close（原生 float32）、ret1／dev20（float64 比值）、ema233（價格水準，float64）、
    obv（以真實 volume 累積，float64）；標籤＝h=5 前瞻簡單報酬（float64）。"""
    k = _real_kline(rows)
    c64 = k["close"].astype(np.float64)
    v64 = k["volume"].astype(np.float64)
    feats = pd.DataFrame({
        "close": k["close"],
        "ret1": c64.pct_change(),
        "dev20": c64 / c64.rolling(20).mean() - 1.0,
        "ema233": c64.ewm(span=233, adjust=False).mean(),
        "obv": (np.sign(c64.diff().fillna(0.0)) * v64).cumsum(),
    }, index=k.index)
    label = (c64.shift(-HORIZON) / c64 - 1.0).rename("label")
    return feats, label


def _prod() -> Any:
    """待測產品模組（實作前不存在 ⇒ 該測試 FAIL，非整檔收集錯誤）。"""
    return importlib.import_module(PRODUCT_MODULE)


def _write_handoff(path: Path, frame: pd.DataFrame) -> None:
    from api.services.ic_analysis_service import ICAnalysisService

    ICAnalysisService._write_features_h5(path, SYMBOL, TF, frame)


def _write_filtered(path: Path, frame: pd.DataFrame) -> None:
    from momentum.Analysis.ic_reporter import ICReporter

    ICReporter({}).save_filtered_features(frame, list(frame.columns), str(path))


def _read_orchestrator(path: Path) -> pd.DataFrame:
    from momentum.factories import create_ic_analyzer

    df, _meta = create_ic_analyzer()._load_features_hdf5(str(path))
    return df


def _read_replay(path: Path) -> pd.DataFrame:
    from scripts.ic1eb_b5_replay import _load_h5_features

    return _load_h5_features(path, SYMBOL, TF)


def _group_layout(path: Path, key: str) -> Dict[str, Any]:
    with h5py.File(path, "r") as f:
        g = f[key]
        out: Dict[str, Any] = {"keys": set(g.keys()), "features": g["features"][:]}
        out["names"] = [n.decode() if isinstance(n, bytes) else str(n) for n in g["feature_names"][:]]
        if "features_f64" in g:
            out["features_f64"] = g["features_f64"][:]
            out["f64_columns"] = g["f64_columns"][:]
        return out


def _assert_layout(layout: Mapping[str, Any], frame: pd.DataFrame, mask: np.ndarray, *, tag: str) -> None:
    """檔案佈局 == SPEC ⑫：`features`＝無損欄 float32（全序相對序）；有不無損欄 ⇒ `features_f64`（float64，位元同輸入）
    與 `f64_columns`（int 索引）；全無損 ⇒ 不寫兩者（佈局同舊格式）。"""
    assert layout["names"] == list(frame.columns), f"{tag}：feature_names 非全序"
    lossless_idx = np.flatnonzero(mask)
    lossy_idx = np.flatnonzero(~mask)
    feats = layout["features"]
    assert feats.dtype == np.float32 and feats.shape == (len(frame), lossless_idx.size), f"{tag}：features 形狀／dtype"
    exp32 = frame.iloc[:, lossless_idx].to_numpy(dtype=np.float32)
    assert np.array_equal(feats.view(np.uint32), exp32.view(np.uint32)), f"{tag}：features 非輸入之 float32 位元"
    if lossy_idx.size == 0:
        assert layout["keys"] == {"features", "timestamps", "feature_names"}, f"{tag}：全無損應同舊格式佈局"
        return
    assert {"features_f64", "f64_columns"} <= layout["keys"], f"{tag}：缺 features_f64／f64_columns"
    f64 = layout["features_f64"]
    assert f64.dtype == np.float64 and f64.shape == (len(frame), lossy_idx.size), f"{tag}：features_f64 形狀／dtype"
    exp64 = frame.iloc[:, lossy_idx].to_numpy(dtype=np.float64)
    assert np.array_equal(f64.view(np.uint64), exp64.view(np.uint64)), f"{tag}：features_f64 非輸入之 float64 位元"
    assert np.issubdtype(layout["f64_columns"].dtype, np.integer), f"{tag}：f64_columns 非整數"
    assert layout["f64_columns"].tolist() == lossy_idx.tolist(), f"{tag}：f64_columns != oracle 不無損欄之全序索引"


def _assert_readback(back: pd.DataFrame, frame: pd.DataFrame, mask: np.ndarray, *, tag: str) -> None:
    """讀端依全序還原原欄序與 dtype：無損欄 float32（＝輸入之 float32）、不無損欄 float64（位元同輸入）。"""
    assert list(back.columns) == list(frame.columns), f"{tag}：讀回欄序"
    assert len(back) == len(frame), f"{tag}：讀回列數"
    for i, name in enumerate(frame.columns):
        got = back.iloc[:, i].to_numpy()
        if mask[i]:
            exp = frame.iloc[:, i].to_numpy(dtype=np.float32)
            assert got.dtype == np.float32 and np.array_equal(got.view(np.uint32), exp.view(np.uint32)), \
                f"{tag}:{name}：無損欄讀回非 float32 輸入值"
        else:
            exp = frame.iloc[:, i].to_numpy(dtype=np.float64)
            assert got.dtype == np.float64 and np.array_equal(got.view(np.uint64), exp.view(np.uint64)), \
                f"{tag}:{name}：不無損欄讀回非 float64 原值"


def _roundtrip_all(tmp_path: Path, frame: pd.DataFrame, label: pd.Series, mask: np.ndarray, *, tag: str) -> Dict[str, Any]:
    """兩寫端 × 全讀端；回四項平衡量測（檔案大小、寫讀時間）。"""
    prod = _prod()
    # 匯入成本不計入寫讀時間
    importlib.import_module("api.services.ic_analysis_service")
    importlib.import_module("momentum.Analysis.ic_filter_orchestrator")
    handoff, filtered = tmp_path / f"{tag}_handoff.h5", tmp_path / f"{tag}_filtered.h5"
    t0 = time.perf_counter()
    _write_handoff(handoff, frame)
    t_write = time.perf_counter() - t0
    _write_filtered(filtered, frame)
    _assert_layout(_group_layout(handoff, f"{SYMBOL}/{TF}"), frame, mask, tag=f"{tag}/handoff")
    _assert_layout(_group_layout(filtered, "filtered"), frame, mask, tag=f"{tag}/filtered")
    t0 = time.perf_counter()
    with h5py.File(handoff, "r") as f:
        g = f[f"{SYMBOL}/{TF}"]
        names = [n.decode() if isinstance(n, bytes) else str(n) for n in g["feature_names"][:]]
        prod.read_feature_frame(g, names, pd.RangeIndex(len(frame)))
    t_read = time.perf_counter() - t0
    readers = {"orchestrator": _read_orchestrator(handoff), "replay": _read_replay(handoff)}
    with h5py.File(filtered, "r") as f:
        g = f["filtered"]
        names = [n.decode() if isinstance(n, bytes) else str(n) for n in g["feature_names"][:]]
        readers["filtered/helper"] = prod.read_feature_frame(g, names, pd.RangeIndex(len(frame)))
    for rname, back in readers.items():
        _assert_readback(back, frame, mask, tag=f"{tag}/{rname}")
        _assert_ic_preserved(frame, back, label, tag=f"{tag}/{rname}")
    return {"handoff_bytes": handoff.stat().st_size, "write_s": t_write, "read_s": t_read}


def _old_format_bytes(tmp_path: Path, frame: pd.DataFrame, dtype: Any, tag: str) -> int:
    """對照：同一資料以一律 `dtype` 之單一 `features` 寫出（舊寫法＝float32）之檔案大小（timestamps／feature_names 同交接檔）。"""
    p = tmp_path / f"{tag}_{np.dtype(dtype).name}.h5"
    with h5py.File(p, "w") as f:
        g = f.create_group(f"{SYMBOL}/{TF}")
        g.create_dataset("features", data=frame.to_numpy(dtype=dtype), compression="gzip")
        g.create_dataset("timestamps", data=frame.index.view("int64") // 10**9, compression="gzip")
        g.create_dataset("feature_names", data=np.array(list(frame.columns), dtype=object),
                         dtype=h5py.string_dtype(encoding="utf-8"))
    return p.stat().st_size


# ── 快速層：判定函式之精確邊界（oracle 為上方 numpy 逐欄重算） ─────────────────────────────────────


def test_lossless_mask_exact_boundaries() -> None:
    """邊界逐一對 oracle：相差 2⁻³⁰（< float32 ulp@1＝2⁻²³）之兩相異值 ⇒ 併值、不無損；相差 2⁻²⁰ ⇒ 無損；1e39（float64
    有限、float32 溢位 inf）⇒ 不無損；1e-50 與 0 ⇒ 下溢併 0、不無損；含 NaN／±inf 而有限值無併 ⇒ 無損；原生 float16／
    float32 ⇒ 無損；全 NaN ⇒ 無損；零列 ⇒ 全無損。"""
    prod = _prod()
    frame = pd.DataFrame({
        "merge_sub_ulp": np.array([1.0, 1.0 + 2.0 ** -30, 2.0, 3.0]),
        "keep_super_ulp": np.array([1.0, 1.0 + 2.0 ** -20, 2.0, 3.0]),
        "overflow": np.array([1.0, 1e39, 2.0, 3.0]),
        "underflow_merge": np.array([0.0, 1e-50, 2.0, 3.0]),
        "nan_inf_ok": np.array([np.nan, np.inf, -np.inf, 0.5]),
        "native_f32": np.array([1.0, 1.0 + 2.0 ** -23, 2.0, 3.0], dtype=np.float32),
        "native_f16": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float16),
        "all_nan": np.full(4, np.nan),
    })
    expected = _oracle_mask(frame)
    assert expected.tolist() == [False, True, False, False, True, True, True, True], "前提：oracle 邊界判定"
    got = np.asarray(prod.float32_lossless_mask(frame), dtype=bool)
    assert got.tolist() == expected.tolist()
    empty = frame.iloc[:0]
    assert np.asarray(prod.float32_lossless_mask(empty), dtype=bool).tolist() == [True] * frame.shape[1]


def test_lossless_mask_ndarray_matches_oracle() -> None:
    """ndarray 輸入（float64 2D）逐欄同 oracle；float32 ndarray 恆全無損。"""
    prod = _prod()
    arr = np.array([[1.0, 1.0], [1.0 + 2.0 ** -30, 1.0 + 2.0 ** -20], [5.0, 5.0]])
    exp = _oracle_mask(pd.DataFrame(arr))
    assert np.asarray(prod.float32_lossless_mask(arr), dtype=bool).tolist() == exp.tolist() == [False, True]
    assert np.asarray(prod.float32_lossless_mask(arr.astype(np.float32)), dtype=bool).tolist() == [True, True]


@pytest.mark.parametrize("bad", ["out_of_range", "duplicate", "length_mismatch", "unsorted"])
def test_corrupt_f64_columns_fail_closed(tmp_path: Path, bad: str) -> None:
    """P7：`f64_columns` 損壞 ⇒ 讀端（共用 helper 與 orchestrator）拒讀，不得默默錯置欄序（資料內容與判定無關，只驗綱要）。"""
    from momentum.factories import stamp_h5_feature_naming_version

    prod = _prod()
    idx = {"out_of_range": [1, 5], "duplicate": [1, 1], "length_mismatch": [1], "unsorted": [2, 1]}[bad]
    p = tmp_path / "bad.h5"
    with h5py.File(p, "w") as f:
        stamp_h5_feature_naming_version(f.attrs)
        g = f.create_group(f"{SYMBOL}/{TF}")
        g.create_dataset("features", data=np.zeros((3, 1), dtype=np.float32))
        g.create_dataset("features_f64", data=np.zeros((3, 2), dtype=np.float64))
        g.create_dataset("f64_columns", data=np.asarray(idx, dtype=np.int64))
        g.create_dataset("timestamps", data=np.arange(3, dtype=np.int64))
        g.create_dataset("feature_names", data=np.array(["a", "b", "c"], dtype=object),
                         dtype=h5py.string_dtype(encoding="utf-8"))
    with h5py.File(p, "r") as f:
        with pytest.raises(ValueError):
            prod.read_feature_frame(f[f"{SYMBOL}/{TF}"], ["a", "b", "c"], pd.RangeIndex(3))
    with pytest.raises(Exception) as exc:
        _read_orchestrator(p)
    assert "f64_columns" in str(exc.value)


# ── 真實資料（requires_kline） ────────────────────────────────────────────────────────────────────


@pytest.mark.requires_kline
def test_p1_all_lossless_real_kline(tmp_path: Path) -> None:
    """P1：真實 2,000 列之 close（原生 float32）、ret1／dev20（float64、oracle 判無損）⇒ 佈局同舊格式、往返 Spearman 逐位元同。"""
    feats, label = _real_features(2000)
    frame = feats[["close", "ret1", "dev20"]]
    mask = _oracle_mask(frame)
    assert mask.all(), f"前提：oracle 判全無損（實得 {dict(zip(frame.columns, mask.tolist()))}）"
    assert frame["ret1"].dtype == np.float64 and frame["close"].dtype == np.float32, "前提：dtype 混合"
    assert np.asarray(_prod().float32_lossless_mask(frame), dtype=bool).tolist() == mask.tolist()
    m = _roundtrip_all(tmp_path, frame, label, mask, tag="p1")
    print(f"[⑫ P1] rows={len(frame)} cols={frame.shape[1]} lossy=0 handoff_bytes={m['handoff_bytes']} "
          f"write_s={m['write_s']:.4f} read_s={m['read_s']:.4f}")


@pytest.mark.requires_kline
def test_p2_partial_lossy_real_kline(tmp_path: Path) -> None:
    """P2：真實全史；EMA233（價格水準）與 OBV 型（真實 volume 累積）欄 float32 併值 ⇒ 存 `features_f64`；其餘無損欄存
    float32。另證舊寫法（一律 float32）之 Spearman 在至少一不無損欄與 float64 不同（測試可鑑別改壞）。記四項平衡量測。"""
    feats, label = _real_features(None)
    frame = feats[["close", "ret1", "dev20", "ema233", "obv"]]
    mask = _oracle_mask(frame)
    assert not mask[3] and not mask[4], f"前提：ema233／obv 不無損（oracle {mask.tolist()}）"
    assert mask[0], "前提：原生 float32 close 無損"
    lab = np.asarray(label, dtype=np.float64)
    differs = []
    for i in np.flatnonzero(~mask):
        x = frame.iloc[:, i].to_numpy(dtype=np.float64)
        mm = np.isfinite(x) & np.isfinite(lab)
        if not _same_float(_spearman(x[mm], lab[mm]), _spearman(x.astype(np.float32)[mm].astype(np.float64), lab[mm])):
            differs.append(frame.columns[i])
    assert differs, "前提：舊寫法（一律 float32）於不無損欄之 Spearman 與 float64 不同（否則本測試無鑑別力）"
    assert np.asarray(_prod().float32_lossless_mask(frame), dtype=bool).tolist() == mask.tolist()
    m = _roundtrip_all(tmp_path, frame, label, mask, tag="p2")
    b32 = _old_format_bytes(tmp_path, frame, np.float32, "p2")
    b64 = _old_format_bytes(tmp_path, frame, np.float64, "p2")
    print(f"[⑫ P2] rows={len(frame)} cols={frame.shape[1]} lossy={int((~mask).sum())} ({differs} Spearman 舊法不同) "
          f"handoff_bytes={m['handoff_bytes']} old_all_f32_bytes={b32} all_f64_bytes={b64} "
          f"write_s={m['write_s']:.4f} read_s={m['read_s']:.4f}")


@pytest.mark.requires_kline
def test_p3_all_lossy_real_kline(tmp_path: Path) -> None:
    """P3：只含不無損欄（真實全史 EMA233、OBV）⇒ `features` 寬 0、全部入 `features_f64`；讀回欄序與值不變。"""
    feats, label = _real_features(None)
    frame = feats[["ema233", "obv"]]
    mask = _oracle_mask(frame)
    assert not mask.any(), "前提：兩欄皆不無損"
    _roundtrip_all(tmp_path, frame, label, mask, tag="p3")


@pytest.mark.requires_kline
def test_p4_nan_inf_overflow_real_kline(tmp_path: Path) -> None:
    """P4：真實 2,000 列 dev20（暖機 NaN）再置 ±inf 於固定位置（有限值無併 ⇒ 無損，NaN／inf 位置往返不變）；ema233⁹
    （真實價格之 9 次方 ≈1e44，float64 有限、float32 溢位）⇒ 判準 (a) 不無損、存 float64。"""
    feats, label = _real_features(2000)
    dev = feats["dev20"].copy()
    dev.iloc[[100, 500]] = np.inf
    dev.iloc[[300, 900]] = -np.inf
    big = feats["ema233"] ** 9
    frame = pd.DataFrame({"dev20_inf": dev, "ema233_pow9": big, "close": feats["close"]}, index=feats.index)
    mask = _oracle_mask(frame)
    assert mask.tolist() == [True, False, True], f"前提：oracle {mask.tolist()}"
    assert np.isfinite(big).all() and not np.isfinite(big.astype(np.float32)).all(), "前提：float32 溢位"
    assert np.asarray(_prod().float32_lossless_mask(frame), dtype=bool).tolist() == mask.tolist()
    _roundtrip_all(tmp_path, frame, label, mask, tag="p4")
    back = _read_orchestrator(tmp_path / "p4_handoff.h5")
    for name in ("dev20_inf", "ema233_pow9"):
        x, z = frame[name].to_numpy(dtype=np.float64), back[name].to_numpy(dtype=np.float64)
        for pred in (np.isnan, np.isposinf, np.isneginf):
            assert np.array_equal(pred(x), pred(z)), f"{name}：{pred.__name__} 位置往返改變"


@pytest.mark.requires_kline
def test_p5_old_format_reads_unchanged_real_kline(tmp_path: Path) -> None:
    """P5：舊格式檔（HEAD 寫法：只 `features` float32）由 orchestrator／replay／共用 helper 讀回 == 舊讀法
    `pd.DataFrame(features[:])`（值逐位元、dtype float32、欄序、索引）。"""
    from momentum.factories import stamp_h5_feature_naming_version

    feats, _ = _real_features(2000)
    frame = feats[["close", "ret1", "ema233", "obv"]]
    mat = frame.to_numpy(dtype=np.float32)
    ts = frame.index.view("int64") // 10**9
    p = tmp_path / "old.h5"
    with h5py.File(p, "w") as f:
        stamp_h5_feature_naming_version(f.attrs)
        g = f.create_group(f"{SYMBOL}/{TF}")
        g.create_dataset("features", data=mat, compression="gzip")
        g.create_dataset("timestamps", data=ts, compression="gzip")
        g.create_dataset("feature_names", data=np.array(list(frame.columns), dtype=object),
                         dtype=h5py.string_dtype(encoding="utf-8"))
    exp_orch = pd.DataFrame(mat, columns=list(frame.columns), index=pd.Index(ts, name="timestamp"))
    pd.testing.assert_frame_equal(_read_orchestrator(p), exp_orch, check_exact=True)
    exp_replay = pd.DataFrame(mat, columns=list(frame.columns),
                              index=pd.to_datetime(ts, unit="s", utc=True).tz_localize(None))
    pd.testing.assert_frame_equal(_read_replay(p), exp_replay, check_exact=True)
    with h5py.File(p, "r") as f:
        got = _prod().read_feature_frame(f[f"{SYMBOL}/{TF}"], list(frame.columns), pd.Index(ts, name="timestamp"))
    pd.testing.assert_frame_equal(got, exp_orch, check_exact=True)


def _write_meta(path: Path, names: List[str]) -> None:
    meta: Dict[str, Any] = {"symbol": SYMBOL, "timeframe": TF, "config_hash": "x", "ff_run_identity": None}
    meta.update({n: {"source": "real_kline"} for n in names})
    path.write_text(json.dumps(meta), encoding="utf-8")


@pytest.mark.requires_kline
def test_p6_freeze_subset_reader_supports_f64(tmp_path: Path) -> None:
    """P6：`scripts/icperf_freeze_baseline.py` `_write_stage5_subset`（讀交接 h5 之子集）：新格式來源 ⇒ 子集內每欄值與
    dtype 同來源（不無損欄仍 float64）；舊格式來源（全無損）⇒ 子集佈局同舊格式、值同舊法（float32）。"""
    from scripts.icperf_freeze_baseline import _write_stage5_subset

    prod = _prod()
    feats, _ = _real_features(None)
    for tag, cols in (("mixed", ["close", "ret1", "dev20", "ema233", "obv"]), ("lossless", ["close"])):
        frame = feats[cols]
        mask = _oracle_mask(frame)
        src_dir = tmp_path / tag
        src_dir.mkdir()
        src_h5, src_meta = src_dir / "src.h5", src_dir / "src_meta.json"
        _write_handoff(src_h5, frame)
        _write_meta(src_meta, cols)
        n = len(cols) - 1 if len(cols) > 1 else 1
        out_h5, _out_meta = _write_stage5_subset(src_h5, src_meta, n, 20261027, tmp_path / f"{tag}_out")
        chosen = np.sort(np.random.default_rng(20261027).permutation(len(cols))[:n])
        sub = frame.iloc[:, chosen]
        sub_mask = mask[chosen]
        layout = _group_layout(out_h5, f"{SYMBOL}/{TF}")
        _assert_layout(layout, sub, sub_mask, tag=f"freeze/{tag}")
        with h5py.File(out_h5, "r") as f:
            g = f[f"{SYMBOL}/{TF}"]
            back = prod.read_feature_frame(g, list(sub.columns), pd.RangeIndex(len(sub)))
        _assert_readback(back, sub, sub_mask, tag=f"freeze/{tag}")
