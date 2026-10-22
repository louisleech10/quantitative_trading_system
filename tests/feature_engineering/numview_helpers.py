"""NUMVIEW（docs/NUMVIEW_SPEC.md §G、§V、Task 0.5／1.5）驗收共用 helper。

- §G 值指紋包裝（Task 0.5，R3-C／R4-A）：呼叫 `preprov_helpers.value_fingerprints`（唯一 oracle），另加
  `column_order_sha256`（manifest 宣告群組順序內之欄名序列 sha256）、逐欄 `values_native`（讀回陣列以其落盤原生
  dtype 之位元組：NaN 位置以該 dtype 之 0 取代、little-endian、C 連續，之 sha256；逐位元判定之唯一值鍵）與
  mean／std／nan_ratio（只報不判）。不得改用 `ffstat_helpers.public_fingerprints`。
- IC 頁 h5 之 DataFrame 版（`frame_fingerprints`）依同欄位定義計算，dtype 取 pandas dtype 字面、原生 dtype 取
  DataFrame 欄之 numpy dtype。
- 沿用基準相容條件（`assert_legacy_compatible`）：沿用之 `tests/_golden/preprov/pre_change_fingerprints.json` 所記
  `dtype` 全為 `float`／`halffloat` 方可以 dtype 相等＋float32 `values` 相等視同原生逐位元相等；遇其他 dtype ⇒ 斷言紅。
- 決定紀錄讀取（`decision`／`core_selector`）：Task 1.5 之 `tests/_golden/numview/decisions.json`（schema 定義於
  Task 0.3 之 `tests/_golden/numview/preregistered_criteria.json`）；`core_selector` 依決定輸出
  `tests/feature_engineering/test_numview_core.py` 之 `-k` 表示式（SPEC Task 3.1–3.3 ASSERT 行之條件選取）。

已實作（NUMVIEW b1）：值指紋包裝與決定紀錄讀取；`decision`／`core_selector` 於決定紀錄（Task 1.5）產出前 fail-closed 拋錯。
命令列：`venv/bin/python -m tests.feature_engineering.numview_helpers core-selector` 印 `-k` 表示式（Task 1.5 後可用）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

REPO: Path = Path(__file__).resolve().parents[2]
GOLDEN_DIR: Path = REPO / "tests" / "_golden" / "numview"
PRE_CHANGE_FINGERPRINTS_PATH: Path = GOLDEN_DIR / "pre_change_fingerprints.json"
#: 判準檔 v1 之檔名路徑（`test_numview_criteria.CRITERIA_V1` 即此；不代表現行判準——現行判準一律經
#: `current_criteria_path()`：v1／v2 恰一存在者，SPEC Task 0.3 邊界①）
CRITERIA_PATH: Path = GOLDEN_DIR / "preregistered_criteria.json"
CRITERIA_V2_PATH: Path = GOLDEN_DIR / "preregistered_criteria_v2.json"
DECISIONS_PATH: Path = GOLDEN_DIR / "decisions.json"
REFREEZE_RECEIPT_PATH: Path = GOLDEN_DIR / "refreeze_receipt.json"
LEGACY_BASELINE_PATH: Path = REPO / "tests" / "_golden" / "preprov" / "pre_change_fingerprints.json"
NUMVIEW_CONTRACT_PATH: Path = REPO / "momentum" / "FeatureEngineering" / "contracts" / "numeric_view.json"
RECEIPTS_DIR: Path = REPO / "handoffs" / "run_receipts"
KLINE_PATH: Path = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"

#: 沿用基準之相容 dtype（Arrow 型別字面；float16／float32 轉 float32 為精確；SPEC §G R4-A）
LEGACY_COMPATIBLE_DTYPES = ("float", "halffloat")

#: 新凍結值指紋之逐位元比對鍵（SPEC §G 通過條件：dtype、nan、values_native、column_set_sha256、column_order_sha256）
BITWISE_COLUMN_KEYS = ("dtype", "nan", "values_native")
BITWISE_TABLE_KEYS = ("column_set_sha256", "column_order_sha256")

#: Phase 3 決定點鍵（SPEC Task 3.1–3.3 ASSERT 行之 WHEN 鍵）
CORE_DECISION_KEYS = ("d_postic", "d_mtf", "d_memmap", "d_winsor_dtype", "d_codec", "d_l2")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def current_criteria_path() -> Path:
    """現行事前登記判準檔：`CRITERIA_PATH`（v1）與 `CRITERIA_V2_PATH`（v2）恰一存在者；皆在或皆無 ⇒ RuntimeError
    （同 `test_numview_criteria._criteria_path` 與邊界 05 之「兩檔名恰一存在」）。刻意不用 assert：本函式被測試呼叫，
    無斷言即不被 TESTREG 展開為測試之斷言元素（不擾動既有斷言之正規化序號）。"""
    if CRITERIA_PATH.is_file() == CRITERIA_V2_PATH.is_file():
        raise RuntimeError(f"判準檔 v1／v2 須恰一存在（v1={CRITERIA_PATH.is_file()}、v2={CRITERIA_V2_PATH.is_file()}）")
    return CRITERIA_V2_PATH if CRITERIA_V2_PATH.is_file() else CRITERIA_PATH


def values_native_sha256(values: np.ndarray) -> str:
    """原生 dtype 位元組之 sha256（SPEC §G R4-A）：NaN 位置以該 dtype 之 0 取代、轉 little-endian、C 連續後雜湊。
    float64 陣列只差小於 float32 解析度者（例 `1.0` 與 `1.0 + 2**-40`）須得不同值。
    非數值（object 等）dtype ⇒ TypeError（無原生位元組語意，不得雜湊指標）。"""
    arr = np.asarray(values)
    if arr.dtype.kind not in "biufc":
        raise TypeError(f"values_native_sha256 只接受數值 dtype，實得 {arr.dtype}")
    if arr.dtype.kind in "fc":
        arr = np.where(np.isnan(arr), arr.dtype.type(0), arr)
    little = arr.astype(arr.dtype.newbyteorder("<"), copy=False)
    return _sha256(np.ascontiguousarray(little).tobytes())


def column_order_sha256(names: Sequence[str]) -> str:
    """欄名序列（保序、不排序）以換行連接之 UTF-8 sha256（SPEC §G R3-C）。"""
    return _sha256("\n".join(str(n) for n in names).encode("utf-8"))


def _column_set_sha256(names: Sequence[str]) -> str:
    """排序欄名以換行連接之 sha256（＝`preprov_helpers.value_fingerprints` 之 `column_set_sha256` 定義）。"""
    return _sha256("\n".join(sorted(str(n) for n in names)).encode("utf-8"))


def _float32_entry(native: np.ndarray) -> Dict[str, str]:
    """`preprov_helpers.value_fingerprints` 之逐欄 `nan`／`values` 定義（float32 NaN 遮罩 packbits、NaN→0 之 float32）。"""
    arr = np.asarray(native, dtype=np.float32)
    nan = np.isnan(arr)
    return {"nan": _sha256(np.packbits(nan).tobytes()),
            "values": _sha256(np.where(nan, np.float32(0), arr).tobytes())}


def _report_stats(native: np.ndarray) -> Dict[str, Optional[float]]:
    """只報不判之逐欄統計（mean／std 只取有限值、float64 累積；nan_ratio＝NaN 比例；無有限值 ⇒ None）。"""
    arr = np.asarray(native, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    nan_ratio = float(np.isnan(arr).mean()) if arr.size else None
    if finite.size == 0:
        return {"mean": None, "std": None, "nan_ratio": nan_ratio}
    return {"mean": float(finite.mean()), "std": float(finite.std()), "nan_ratio": nan_ratio}


def fingerprints(run_dir: Path, artifact_kind: str = "raw") -> Dict[str, Any]:
    """run 目錄之 §G 值指紋：`preprov_helpers.value_fingerprints` 之輸出，另於每欄加 `values_native`、`mean`、`std`、
    `nan_ratio`，於表層加 `column_order_sha256`（manifest 宣告群組順序內之欄名序列）。只讀 manifest 宣告之群組檔。"""
    import pyarrow.parquet as pq

    from tests.feature_engineering import preprov_helpers as ph

    base = ph.value_fingerprints(Path(run_dir), artifact_kind)
    order: List[str] = []
    for path in ph.declared_group_files(Path(run_dir), artifact_kind):
        table = pq.read_table(str(path))
        for name in table.column_names:
            if name in ph.NON_FEATURE_COLUMNS:
                continue
            native = np.asarray(table.column(name).to_numpy(zero_copy_only=False))
            entry = base["columns"][name]
            entry["values_native"] = values_native_sha256(native)
            entry.update(_report_stats(native))
            order.append(str(name))
    if sorted(set(order)) != sorted(base["columns"]) or len(order) != len(set(order)):
        raise AssertionError(f"{run_dir}/{artifact_kind}：宣告群組之欄序與 value_fingerprints 欄集合不一致或有重複欄")
    base["column_order_sha256"] = column_order_sha256(order)
    return base


def frame_fingerprints(frame: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame 版（IC 頁 h5 輸出；SPEC §G G1）：欄位定義同 `fingerprints`，dtype 取 pandas dtype 字面，
    `values_native` 依 DataFrame 欄之 numpy dtype，`column_order_sha256` 依 DataFrame 欄序。欄名重複 ⇒ ValueError。"""
    names = [str(c) for c in frame.columns]
    if len(names) != len(set(names)):
        raise ValueError(f"frame_fingerprints：欄名重複 {sorted({n for n in names if names.count(n) > 1})}")
    columns: Dict[str, Dict[str, Any]] = {}
    for position, name in enumerate(names):
        series = frame.iloc[:, position]
        native = series.to_numpy()
        entry: Dict[str, Any] = {"dtype": str(series.dtype)}
        entry.update(_float32_entry(native))
        entry["values_native"] = values_native_sha256(native)
        entry.update(_report_stats(native))
        columns[name] = entry
    return {"columns": columns, "column_set_sha256": _column_set_sha256(names),
            "column_order_sha256": column_order_sha256(names)}


def assert_legacy_compatible(fingerprint: Mapping[str, Any]) -> None:
    """沿用基準相容斷言（SPEC §G R4-A）：`fingerprint["columns"][*]["dtype"]` 皆屬 `LEGACY_COMPATIBLE_DTYPES`，
    否則 AssertionError（列出不相容欄；該欄須於 Task 0.5 以 `values_native` 重凍，不得以 float32 鍵通過）。"""
    bad = sorted(f"{name}:{entry.get('dtype')!r}" for name, entry in fingerprint["columns"].items()
                 if entry.get("dtype") not in LEGACY_COMPATIBLE_DTYPES)
    assert not bad, (f"沿用基準含非 {LEGACY_COMPATIBLE_DTYPES} 之欄 {len(bad)} 個（須以 values_native 重凍）："
                     f"{bad[:10]}")


#: 沿用基準（legacy）之逐欄比對鍵：dtype、float32 `values`，另比 `nan`（float32 `values` 以 0 代 NaN，遮罩須另比；SPEC §C）
_LEGACY_COLUMN_KEYS = ("dtype", "nan", "values")
_LEGACY_TABLE_KEYS = ("column_set_sha256",)


def bitwise_diff(before: Mapping[str, Any], after: Mapping[str, Any], *, legacy: bool = False) -> List[str]:
    """兩份值指紋之逐位元差異清單（空＝相等）。新凍結（`legacy=False`）比 `BITWISE_COLUMN_KEYS` 與
    `BITWISE_TABLE_KEYS`；沿用基準（`legacy=True`）先 `assert_legacy_compatible(before)`，再比 `dtype` 與 float32
    `values`（另比 `nan` 遮罩）、`column_set_sha256`。atol=0、rtol=0（SPEC §G 通過條件）。
    指紋缺比對鍵 ⇒ KeyError（無從判定，不得視為相等）。每條差異以欄名或表層鍵名起首。"""
    if legacy:
        assert_legacy_compatible(before)
    column_keys = _LEGACY_COLUMN_KEYS if legacy else BITWISE_COLUMN_KEYS
    table_keys = _LEGACY_TABLE_KEYS if legacy else BITWISE_TABLE_KEYS
    out: List[str] = []
    b_cols, a_cols = before["columns"], after["columns"]
    for name in sorted(set(b_cols) | set(a_cols)):
        if name not in a_cols:
            out.append(f"{name}: 只在改前")
            continue
        if name not in b_cols:
            out.append(f"{name}: 只在改後")
            continue
        for key in column_keys:
            if b_cols[name][key] != a_cols[name][key]:
                out.append(f"{name}: {key} 不同（{b_cols[name][key]!r} → {a_cols[name][key]!r}）")
    for key in table_keys:
        if before[key] != after[key]:
            out.append(f"{key}: 不同")
    return out


def _decision_record(key: str) -> Mapping[str, Any]:
    assert DECISIONS_PATH.is_file(), f"決定紀錄不存在：{DECISIONS_PATH}（Task 1.5 未產出）"
    data = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    records = data.get("decisions") if isinstance(data, Mapping) else None
    assert isinstance(records, Mapping), "決定紀錄之 decisions 須為 {決定點鍵: 紀錄} 物件"
    record = records.get(key)
    assert isinstance(record, Mapping), f"決定紀錄缺決定點 {key}"
    assert "key" not in record or record["key"] == key, f"決定紀錄 {key} 之內嵌 key={record['key']!r} 與物件鍵不同"
    return record


def decision(key: str) -> str:
    """決定紀錄（`DECISIONS_PATH`；全票唯一形 `{criteria_sha256, decisions: {<決定點鍵>: record}, measurement_limitations}`）
    中決定點 `key`（`CORE_DECISION_KEYS` 之一，或 `d_icpage_arm`／`d_research`）之 `record["choice"]`（如
    `polars_float64`／`retain`）；檔缺、鍵缺或 `choice` 缺 ⇒ AssertionError（fail-closed）。"""
    choice = _decision_record(key).get("choice")
    assert isinstance(choice, str) and choice, f"決定紀錄 {key} 缺 choice"
    return choice


#: 決定值 → `test_numview_core.py` 分支記號（SPEC Task 3.1–3.3 ASSERT … WHEN … 行）
_CORE_TOKENS: Dict[str, Dict[str, str]] = {
    "d_postic": {"polars_float64": "postic_float64", "retain": "postic_retained"},
    "d_mtf": {"unify": "mtf_dtype", "retain": "mtf_retained"},
    "d_memmap": {"decouple": "memmap_dtype", "retain": "memmap_retained"},
    "d_winsor_dtype": {"unify": "(winsor_dtype and not winsor_dtype_retained)", "retain": "winsor_dtype_retained"},
    "d_codec": {"provenance": "codec_by_provenance", "retain": "codec_retained"},
    "d_l2": {"unify": "l2_unified", "retain": "l2_named"},
}
_CORE_ALWAYS = "core_always"


def core_selector() -> str:
    """依決定紀錄輸出 `test_numview_core.py` 之 pytest `-k` 表示式（SPEC Task 3.1–3.3 之 ASSERT … WHEN … 行：
    每個決定點恰選其一支）。決定紀錄缺或任一決定點缺 ⇒ 拋錯（呼叫端之 `-k` 因而為空 ⇒ 全部分支皆跑 ⇒ 必紅，fail-closed）。
    分支記號（決定值 → 記號）：d_postic polars_float64→`postic_float64`／retain→`postic_retained`；d_mtf unify→`mtf_dtype`／
    retain→`mtf_retained`；d_memmap decouple→`memmap_dtype`／retain→`memmap_retained`；d_winsor_dtype
    unify→`(winsor_dtype and not winsor_dtype_retained)`／retain→`winsor_dtype_retained`；d_codec
    provenance→`codec_by_provenance`／retain→`codec_retained`；d_l2 unify→`l2_unified`／retain→`l2_named`；另恆含
    `core_always`。輸出＝`core_always or <六記號 or 連接>`。記號間之子字串碰撞已逐對檢查：唯一者為
    `winsor_dtype` ⊂ `winsor_dtype_retained`，故以 `and not` 排除。決定值不屬該點之兩支 ⇒ ValueError。"""
    tokens = [_CORE_ALWAYS]
    for key in CORE_DECISION_KEYS:
        choice = decision(key)
        mapping = _CORE_TOKENS[key]
        if choice not in mapping:
            raise ValueError(f"決定紀錄 {key}={choice!r} 不屬 {sorted(mapping)}")
        tokens.append(mapping[choice])
    return " or ".join(tokens)


def _main(argv: Sequence[str]) -> int:
    if list(argv) == ["core-selector"]:
        print(core_selector())
        return 0
    print("用法: python -m tests.feature_engineering.numview_helpers core-selector", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
