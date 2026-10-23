"""NUMVIEW Task 0.5（docs/NUMVIEW_SPEC.md §G R3-C／R4-A、§V oracle ⑦）：§G 值指紋包裝（`numview_helpers`）之可證偽單元驗收。

受測＝`tests/feature_engineering/numview_helpers.py` 之 `frame_fingerprints`、`values_native_sha256`、`column_order_sha256`、
`assert_legacy_compatible`、`bitwise_diff`（Task 0.5 實作）。輸入一律取自真實 kline（`ffstat_helpers.kline_frame`，唯讀
`data_cache/feature_klines/kline_cache.h5`）之欄；唯一字面陣列＝SPEC Task 0.5 明示之 `1.0` 與 `1.0 + 2**-40`。
不生成特徵（秒級）。

驗證（SPEC Task 0.5「dtype、欄集合、欄序、原生位元組各一案可證偽」＋沿用基準相容斷言）：
- dtype 案：同值、一欄 float32 對 float64 ⇒ 指紋 `dtype` 不同、`bitwise_diff` 非空；
- 欄集合案：增／刪一欄 ⇒ `column_set_sha256` 不同；
- 欄序案：兩欄對調 ⇒ `column_order_sha256` 不同而 `column_set_sha256` 相同；
- 原生位元組案：兩 float64 欄只差小於 float32 解析度（`1.0` 對 `1.0 + 2**-40`；另以真實欄重做）⇒ `values_native` 不同而
  float32 `values` 相同，`bitwise_diff` 判不等；
- 沿用基準相容：含 `double` 欄之舊基準形指紋 ⇒ `assert_legacy_compatible` 拋 AssertionError；真實沿用基準
  `LEGACY_BASELINE_PATH` 全部格／標的／artifact 皆通過；
- NaN 案：`values_native` 之 NaN 位置以該 dtype 之 0 取代 ⇒ 只差「NaN 對 0」之兩陣列只於 `nan` 鍵不同；
- 位元組序／連續性：big-endian 或非 C 連續之輸入與其 little-endian C 連續複本同雜湊；
- `frame_fingerprints` 之 `nan`／`values` 欄位定義＝`preprov_helpers.value_fingerprints`（float32 遮罩 packbits、NaN→0 之
  float32）；`column_order_sha256`＝保序欄名以換行連接之 UTF-8 sha256。
mutation（SPEC §V）：包裝改為 `ffstat_helpers.public_fingerprints` 式輸出（無 dtype／column_set／column_order）⇒ dtype、欄集合、
欄序三案翻紅；`bitwise_diff` 改用 float32 `values` 判定 ⇒ 原生位元組案翻紅。
測試接縫（Task 0.5 實作須提供）：`frame_fingerprints(df)` 回 `{"columns": {欄: {"dtype","nan","values","values_native",…}},
"column_set_sha256", "column_order_sha256"}`；`bitwise_diff` 回差異字串清單，每條含欄名（或表層鍵名）；呼叫端經模組屬性取用
（本檔以 monkeypatch 替換模組屬性做 mutation）。
實作前應為紅（helper 為 NotImplementedError）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable, Dict, List, Mapping

import numpy as np
import pandas as pd
import pytest

from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import numview_helpers as nh

pytestmark = pytest.mark.requires_kline

#: SPEC Task 0.5 明示之字面（兩 float64 值只差小於 float32 解析度）
SPEC_ONE = 1.0
SPEC_ONE_PLUS = 1.0 + 2 ** -40


# ---------------------------------------------------------------------------------------------- 真實輸入

_KLINE_CACHE: Dict[str, pd.DataFrame] = {}


def _kline() -> pd.DataFrame:
    """真實 BTCUSDT 1h kline（`ffstat_helpers.kline_frame` 預設；唯讀）；同模組只讀一次。"""
    if "frame" not in _KLINE_CACHE:
        frame = fsh.kline_frame()
        assert len(frame) > 1000 and frame.shape[1] >= 3, f"真實 kline 列數或欄數不足：{frame.shape}"
        _KLINE_CACHE["frame"] = frame
    return _KLINE_CACHE["frame"].copy()


def _real_columns(n: int = 3) -> List[str]:
    """真實 kline 前 n 個數值欄名（不寫死欄名）。"""
    frame = _kline()
    cols = [c for c in frame.columns if np.issubdtype(frame[c].dtype, np.floating)]
    assert len(cols) >= n, f"真實 kline 數值欄不足 {n}：{cols}"
    return cols[:n]


def _f32_exact_frame() -> pd.DataFrame:
    """真實欄先轉 float32 再轉回 float64（值於 float32 可精確表示；dtype 案需「同值不同 dtype」）。"""
    frame = _kline()[_real_columns(3)]
    return frame.astype(np.float32).astype(np.float64)


def _independent_values_native(values: np.ndarray) -> str:
    """測試端獨立重算（SPEC §G R4-A 之定義）：NaN→該 dtype 之 0、little-endian、C 連續之位元組 sha256。"""
    arr = np.asarray(values)
    native = arr.dtype.newbyteorder("<")
    clean = np.where(np.isnan(arr), arr.dtype.type(0), arr).astype(native, copy=False)
    return hashlib.sha256(np.ascontiguousarray(clean).tobytes()).hexdigest()


def _independent_order_sha(names: List[str]) -> str:
    return hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()


def _public_style_fingerprints(frame: pd.DataFrame) -> Dict[str, Any]:
    """mutant：`ffstat_helpers.public_fingerprints` 式輸出（每欄只 `nan`／`values`，無 dtype、無表層欄集合／欄序鍵）。"""
    columns: Dict[str, Dict[str, str]] = {}
    for name in frame.columns:
        arr = np.asarray(frame[name].to_numpy(), dtype=np.float32)
        nan = np.isnan(arr)
        columns[str(name)] = {"nan": hashlib.sha256(np.packbits(nan).tobytes()).hexdigest(),
                              "values": hashlib.sha256(np.where(nan, np.float32(0), arr).tobytes()).hexdigest()}
    return {"columns": columns}


def _float32_values_bitwise_diff(before: Mapping[str, Any], after: Mapping[str, Any], *, legacy: bool = False) -> List[str]:
    """mutant：逐位元判定改用 float32 轉型之 `values`（SPEC §V「逐位元判定改用 float32 轉型之 values」）。"""
    out: List[str] = []
    for name in sorted(set(before["columns"]) | set(after["columns"])):
        b = before["columns"].get(name, {})
        a = after["columns"].get(name, {})
        if b.get("values") != a.get("values") or b.get("nan") != a.get("nan"):
            out.append(f"{name}: values")
    return out


# ---------------------------------------------------------------------------------------------- oracle（經模組屬性呼叫受測者）

def _diff_safe(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
    """`nh.bitwise_diff`（經模組屬性）；指紋缺鍵而無法判別（mutant 輸出）⇒ 回空清單＝未判出差異。"""
    try:
        return list(nh.bitwise_diff(before, after))
    except KeyError:
        return []


def dtype_case_violations() -> List[str]:
    """dtype 案：同值、第一欄 float32 對 float64 ⇒ `dtype` 不同、float32 `values` 相同、`bitwise_diff` 指出該欄。"""
    base = _f32_exact_frame()
    col = str(base.columns[0])
    narrowed = base.copy()
    narrowed[col] = narrowed[col].astype(np.float32)
    assert np.array_equal(narrowed[col].to_numpy(np.float64), base[col].to_numpy(), equal_nan=True), "前提：兩欄值須相同"
    fa, fb = nh.frame_fingerprints(base), nh.frame_fingerprints(narrowed)
    out: List[str] = []
    da, db = fa["columns"][col].get("dtype"), fb["columns"][col].get("dtype")
    if da is None or db is None or da == db:
        out.append(f"dtype 未區分：{da!r} vs {db!r}")
    if fa["columns"][col].get("values") != fb["columns"][col].get("values"):
        out.append("同值之 float32 values 不應不同（前提失效）")
    if not any(col in d for d in _diff_safe(fa, fb)):
        out.append("bitwise_diff 未指出 dtype 不同之欄")
    return out


def column_set_case_violations() -> List[str]:
    """欄集合案：增一欄、刪一欄 ⇒ `column_set_sha256` 皆不同，`bitwise_diff` 非空。"""
    frame = _kline()[_real_columns(3)]
    base = frame.iloc[:, :2]
    added = frame.iloc[:, :3]
    dropped = frame.iloc[:, :1]
    fp = nh.frame_fingerprints(base)
    out: List[str] = []
    for label, other in (("增一欄", added), ("刪一欄", dropped)):
        fo = nh.frame_fingerprints(other)
        if fp.get("column_set_sha256") is None or fp.get("column_set_sha256") == fo.get("column_set_sha256"):
            out.append(f"{label}：column_set_sha256 未區分")
        if not _diff_safe(fp, fo):
            out.append(f"{label}：bitwise_diff 未判不等")
    return out


def column_order_case_violations() -> List[str]:
    """欄序案：兩欄對調 ⇒ `column_order_sha256` 不同、`column_set_sha256` 相同、各欄逐欄指紋相同、`bitwise_diff` 非空。"""
    frame = _kline()[_real_columns(2)]
    swapped = frame[list(reversed(list(frame.columns)))]
    fa, fb = nh.frame_fingerprints(frame), nh.frame_fingerprints(swapped)
    out: List[str] = []
    if fa.get("column_order_sha256") is None or fa.get("column_order_sha256") == fb.get("column_order_sha256"):
        out.append("column_order_sha256 未區分欄序")
    if fa.get("column_set_sha256") is None or fa.get("column_set_sha256") != fb.get("column_set_sha256"):
        out.append("欄序對調不應改變 column_set_sha256")
    if fa["columns"] != fb["columns"]:
        out.append("欄序對調不應改變逐欄指紋")
    if not _diff_safe(fa, fb):
        out.append("bitwise_diff 未判出欄序不同")
    return out


def _native_pairs() -> List[Dict[str, Any]]:
    """原生位元組案之輸入對：SPEC 字面 `1.0`／`1.0 + 2**-40`，與真實欄（float32 可精確表示者）加 |x|·2**-40 之擾動。"""
    real = _f32_exact_frame().iloc[:, [0]]
    col = str(real.columns[0])
    bumped = real.copy()
    bumped[col] = real[col] + np.abs(real[col]) * 2.0 ** -40
    assert np.array_equal(bumped[col].astype(np.float32).to_numpy(), real[col].astype(np.float32).to_numpy()), \
        "前提：擾動須小於 float32 解析度（轉 float32 後相等）"
    assert not np.array_equal(bumped[col].to_numpy(), real[col].to_numpy()), "前提：擾動須改變 float64 位元組"
    return [
        {"label": "spec_literal", "col": "x",
         "a": pd.DataFrame({"x": np.array([SPEC_ONE], dtype=np.float64)}),
         "b": pd.DataFrame({"x": np.array([SPEC_ONE_PLUS], dtype=np.float64)})},
        {"label": "real_column", "col": col, "a": real, "b": bumped},
    ]


def native_bytes_case_violations() -> List[str]:
    """原生位元組案：`values_native` 不同、float32 `values` 相同、`bitwise_diff` 指出該欄（逐位元判定以 values_native 為準）。"""
    out: List[str] = []
    for pair in _native_pairs():
        col = pair["col"]
        fa, fb = nh.frame_fingerprints(pair["a"]), nh.frame_fingerprints(pair["b"])
        ca, cb = fa["columns"][col], fb["columns"][col]
        if ca.get("values") != cb.get("values"):
            out.append(f"{pair['label']}：float32 values 應相同（前提）")
        if ca.get("values_native") is None or ca.get("values_native") == cb.get("values_native"):
            out.append(f"{pair['label']}：values_native 未區分小於 float32 解析度之差")
        if not any(col in d for d in _diff_safe(fa, fb)):
            out.append(f"{pair['label']}：bitwise_diff 未判不等")
    return out


# ---------------------------------------------------------------------------------------------- 驗證

def test_dtype_case_falsifiable() -> None:
    """dtype 案（SPEC Task 0.5、R3-C）。"""
    assert dtype_case_violations() == []


def test_column_set_case_falsifiable() -> None:
    """欄集合案（SPEC Task 0.5、R3-C）。"""
    assert column_set_case_violations() == []


def test_column_order_case_falsifiable() -> None:
    """欄序案（SPEC Task 0.5、R3-C；`value_fingerprints` 之 `names = sorted(columns)` 不含欄序，由包裝補）。"""
    assert column_order_case_violations() == []


def test_native_bytes_case_falsifiable() -> None:
    """原生位元組案（SPEC Task 0.5、R4-A：`1.0` 與 `1.0 + 2**-40`；另以真實欄重做）。"""
    assert native_bytes_case_violations() == []


def test_values_native_sha256_matches_definition_on_real_columns() -> None:
    """`values_native_sha256`＝NaN→0、little-endian、C 連續之原生位元組 sha256（測試端獨立重算；float64 與 float32 兩寬度）。"""
    frame = _kline()[_real_columns(2)]
    checked = 0
    for col in frame.columns:
        x = frame[col].to_numpy(dtype=np.float64).copy()
        x[::97] = np.nan
        for arr in (x, x.astype(np.float32)):
            assert nh.values_native_sha256(arr) == _independent_values_native(arr), f"{col}/{arr.dtype}"
            checked += 1
    assert checked >= 4


def test_column_order_sha256_matches_definition() -> None:
    """`column_order_sha256`＝保序（不排序）欄名以換行連接之 UTF-8 sha256；對調即不同。"""
    names = [str(c) for c in _real_columns(3)]
    assert nh.column_order_sha256(names) == _independent_order_sha(names)
    assert nh.column_order_sha256(names) != nh.column_order_sha256(list(reversed(names)))


def test_frame_fingerprints_preprov_fields_match_definition() -> None:
    """`frame_fingerprints` 之 `nan`／`values`／`column_set_sha256` 欄位定義＝`preprov_helpers.value_fingerprints`
    （float32 NaN 遮罩 packbits sha256、NaN→0 之 float32 sha256、排序欄名以換行連接之 sha256）；dtype＝pandas dtype 字面；
    `values_native` 依欄之 numpy dtype；`column_order_sha256` 依 DataFrame 欄序。"""
    frame = _kline()[_real_columns(3)].copy()
    first = str(frame.columns[0])
    frame.loc[frame.index[::53], first] = np.nan
    frame[str(frame.columns[1])] = frame[str(frame.columns[1])].astype(np.float32)
    fp = nh.frame_fingerprints(frame)
    assert set(fp["columns"]) == {str(c) for c in frame.columns}
    for name in frame.columns:
        native = frame[name].to_numpy()
        arr32 = np.asarray(native, dtype=np.float32)
        nan = np.isnan(arr32)
        entry = fp["columns"][str(name)]
        assert entry["dtype"] == str(frame[name].dtype)
        assert entry["nan"] == hashlib.sha256(np.packbits(nan).tobytes()).hexdigest()
        assert entry["values"] == hashlib.sha256(np.where(nan, np.float32(0), arr32).tobytes()).hexdigest()
        assert entry["values_native"] == _independent_values_native(native)
    names = sorted(str(c) for c in frame.columns)
    assert fp["column_set_sha256"] == hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()
    assert fp["column_order_sha256"] == _independent_order_sha([str(c) for c in frame.columns])


def test_nan_replaced_by_zero_only_nan_key_differs() -> None:
    """NaN 案（SPEC §G R4-A：NaN 位置以該 dtype 之 0 取代）：只差「NaN 對 0」之兩真實欄 ⇒ `values_native` 與 `values`
    相同、`nan` 不同、`bitwise_diff` 非空；float64 與 float32 兩寬度皆然。"""
    col = _real_columns(1)[0]
    base = _kline()[col].to_numpy(dtype=np.float64)
    idx = np.arange(5, base.size, 211)
    assert idx.size > 0
    for dtype in (np.float64, np.float32):
        with_nan = base.astype(dtype).copy()
        with_zero = base.astype(dtype).copy()
        with_nan[idx] = np.nan
        with_zero[idx] = dtype(0)
        assert nh.values_native_sha256(with_nan) == nh.values_native_sha256(with_zero), dtype
        fa = nh.frame_fingerprints(pd.DataFrame({col: with_nan}))
        fb = nh.frame_fingerprints(pd.DataFrame({col: with_zero}))
        assert fa["columns"][col]["values_native"] == fb["columns"][col]["values_native"]
        assert fa["columns"][col]["values"] == fb["columns"][col]["values"]
        assert fa["columns"][col]["nan"] != fb["columns"][col]["nan"]
        assert any(col in d for d in nh.bitwise_diff(fa, fb))


def test_values_native_endianness_and_contiguity_invariant() -> None:
    """位元組序／連續性：big-endian 與非 C 連續（跨步視圖）之輸入與其 little-endian C 連續複本同雜湊（真實欄）。"""
    col = _real_columns(1)[0]
    x = _kline()[col].to_numpy(dtype=np.float64).copy()
    x[::101] = np.nan
    reference = nh.values_native_sha256(np.ascontiguousarray(x.astype("<f8")))
    big = x.astype(">f8")
    assert big.dtype.byteorder == ">"
    assert nh.values_native_sha256(big) == reference
    holder = np.empty(x.size * 2, dtype=np.float64)
    holder[::2] = x
    strided = holder[::2]
    assert not strided.flags["C_CONTIGUOUS"]
    assert nh.values_native_sha256(strided) == reference
    x32 = x.astype(np.float32)
    assert nh.values_native_sha256(x32.astype(">f4")) == nh.values_native_sha256(np.ascontiguousarray(x32))
    assert nh.values_native_sha256(x32) != reference, "寬度不同之原生位元組不得同雜湊"


def test_legacy_shape_with_double_column_rejected() -> None:
    """沿用基準相容（SPEC §G R4-A）：舊基準形指紋含 `double`（float64）欄 ⇒ `assert_legacy_compatible` 拋 AssertionError。"""
    baseline = json.loads(nh.LEGACY_BASELINE_PATH.read_text(encoding="utf-8"))
    cell = sorted(baseline["cells"])[0]
    symbol = sorted(baseline["cells"][cell])[0]
    artifact = sorted(baseline["cells"][cell][symbol])[0]
    fp = copy.deepcopy(baseline["cells"][cell][symbol][artifact])
    victim = sorted(fp["columns"])[0]
    fp["columns"][victim]["dtype"] = "double"
    assert "double" not in nh.LEGACY_COMPATIBLE_DTYPES
    with pytest.raises(AssertionError):
        nh.assert_legacy_compatible(fp)


def test_real_legacy_baseline_all_cells_compatible() -> None:
    """真實沿用基準 `LEGACY_BASELINE_PATH` 之每格每標的每 artifact 皆通過相容斷言（不拋）。"""
    baseline = json.loads(nh.LEGACY_BASELINE_PATH.read_text(encoding="utf-8"))
    checked = 0
    for cell, symbols in sorted(baseline["cells"].items()):
        for symbol, artifacts in sorted(symbols.items()):
            for artifact, fp in sorted(artifacts.items()):
                assert fp["columns"], f"{cell}/{symbol}/{artifact} 無欄"
                nh.assert_legacy_compatible(fp)
                checked += 1
    assert checked >= len(baseline["cells"]) >= 1


# ---------------------------------------------------------------------------------------------- mutation

@pytest.mark.parametrize("case", [dtype_case_violations, column_set_case_violations, column_order_case_violations],
                         ids=["dtype", "column_set", "column_order"])
def test_mutation_public_fingerprints_style_wrapper_flips_cases(case: Callable[[], List[str]],
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC §V、R3-C）：值指紋包裝改為 `public_fingerprints` 式（無 dtype／column_set／column_order）⇒ dtype、
    欄集合、欄序三案之檢查翻紅（回非空違規）。"""
    monkeypatch.setattr(nh, "frame_fingerprints", _public_style_fingerprints)
    violations = case()
    assert violations, "mutant 存活：public_fingerprints 式包裝下本案仍判通過"


def test_mutation_bitwise_diff_on_float32_values_flips_native_case(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC §V、R4-A）：`bitwise_diff` 改用 float32 轉型之 `values` 判定 ⇒ 原生位元組案翻紅。"""
    monkeypatch.setattr(nh, "bitwise_diff", _float32_values_bitwise_diff)
    violations = native_bytes_case_violations()
    assert any("bitwise_diff 未判不等" in v for v in violations), violations


# ---------------------------------------------------------------------------------------------- 群組粒度（SPEC §G：全特徵格 C）

def _two_group_run(tmp_path: Any, mutate: str = "") -> Any:
    """以正式 `FeatureStorage.write_raw` 寫兩群組之 run（欄取自真實 kline 末 400 根，float64）；`mutate` 改壞一處後回 run 目錄。"""
    from pathlib import Path

    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    k = _kline().iloc[-400:]
    g1 = k[["open", "high"]].astype(np.float64).reset_index(drop=True)
    g2 = k[["low", "close", "volume"]].astype(np.float64).reset_index(drop=True)
    if mutate == "value":
        g2.loc[100, "close"] = g2.loc[100, "close"] + 1.0
    elif mutate == "subfloat32":
        g2.loc[100, "close"] = g2.loc[100, "close"] + 2.0 ** -30 * abs(g2.loc[100, "close"])
    elif mutate == "order":
        g2 = g2[["close", "low", "volume"]]
    elif mutate == "rename":
        g2 = g2.rename(columns={"volume": "volume_x"})
    elif mutate == "nan_inserted":
        g2.loc[5, "low"] = np.nan
    elif mutate == "dtype":
        g2["close"] = g2["close"].astype(np.float32)
    storage = FeatureStorage(str(Path(tmp_path) / mutate if mutate else Path(tmp_path) / "base"))
    raw_dir = storage.write_raw("BTCUSDT", "1h", f"cfg_{mutate or 'base'}", {"ga": g1, "gb": g2},
                                row_index=pd.DatetimeIndex(k.index))
    return raw_dir.parent


@pytest.mark.parametrize("mutate, key, changed_group", [
    ("value", "values", "gb"), ("value", "values_native", "gb"), ("subfloat32", "values_native", "gb"),
    ("order", "table:column_order_sha256", None), ("rename", "table:column_set_sha256", None),
    ("nan_inserted", "nan", "gb"), ("dtype", "dtype", "gb"),
])
def test_group_fingerprints_falsifiable(tmp_path: Any, mutate: str, key: str, changed_group: Any) -> None:
    """群組粒度值指紋（`numview_helpers.group_fingerprints`）可證偽：群組內一值 +1、小於 float32 解析度之 float64 差、欄序、
    欄名、插入 NaN、dtype float64→float32 ⇒ 對應群組或表層雜湊改變；未改之群組逐鍵不變；`bitwise_diff` 指出差異。"""
    base = nh.group_fingerprints(_two_group_run(tmp_path), "raw")
    after = nh.group_fingerprints(_two_group_run(tmp_path, mutate), "raw")
    assert base["granularity"] == "group" and base["column_count"] == 5
    assert set(base["columns"]) == set(after["columns"]) and len(base["columns"]) == 2
    if key.startswith("table:"):
        table_key = key.split(":", 1)[1]
        assert base[table_key] != after[table_key], mutate
    else:
        group = next(g for g in base["columns"] if changed_group in g)
        assert base["columns"][group][key] != after["columns"][group][key], (mutate, key)
        other = next(g for g in base["columns"] if changed_group not in g)
        assert base["columns"][other] == after["columns"][other], "未改之群組須逐鍵不變"
    assert nh.bitwise_diff(base, after) != [], mutate
    if mutate == "subfloat32":
        group = next(g for g in base["columns"] if "gb" in g)
        assert base["columns"][group]["values"] == after["columns"][group]["values"], "float32 值須相同（差小於其解析度）"


def test_group_fingerprints_identical_rewrite_equal(tmp_path: Any) -> None:
    """對照：同值重寫兩次 ⇒ 群組粒度值指紋逐鍵相同、`bitwise_diff` 為空。"""
    from pathlib import Path

    a = nh.group_fingerprints(_two_group_run(Path(tmp_path) / "a"), "raw")
    b = nh.group_fingerprints(_two_group_run(Path(tmp_path) / "b"), "raw")
    assert a["columns"] == b["columns"] and a["column_order_sha256"] == b["column_order_sha256"]
    assert nh.bitwise_diff(a, b) == []
