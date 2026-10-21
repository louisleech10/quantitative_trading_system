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

本檔為 TODO 階段空殼（Task 0.5／1.5 實作）：函式體 `raise NotImplementedError`；常數與路徑可直接使用。
命令列：`venv/bin/python -m tests.feature_engineering.numview_helpers core-selector` 印 `-k` 表示式（Task 1.5 後可用）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

REPO: Path = Path(__file__).resolve().parents[2]
GOLDEN_DIR: Path = REPO / "tests" / "_golden" / "numview"
PRE_CHANGE_FINGERPRINTS_PATH: Path = GOLDEN_DIR / "pre_change_fingerprints.json"
CRITERIA_PATH: Path = GOLDEN_DIR / "preregistered_criteria.json"
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


def values_native_sha256(values: np.ndarray) -> str:
    """原生 dtype 位元組之 sha256（SPEC §G R4-A）：NaN 位置以該 dtype 之 0 取代、轉 little-endian、C 連續後雜湊。
    float64 陣列只差小於 float32 解析度者（例 `1.0` 與 `1.0 + 2**-40`）須得不同值。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def column_order_sha256(names: Sequence[str]) -> str:
    """欄名序列（保序、不排序）以換行連接之 UTF-8 sha256（SPEC §G R3-C）。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def fingerprints(run_dir: Path, artifact_kind: str = "raw") -> Dict[str, Any]:
    """run 目錄之 §G 值指紋：`preprov_helpers.value_fingerprints` 之輸出，另於每欄加 `values_native`、`mean`、`std`、
    `nan_ratio`，於表層加 `column_order_sha256`（manifest 宣告群組順序內之欄名序列）。只讀 manifest 宣告之群組檔。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def frame_fingerprints(frame: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame 版（IC 頁 h5 輸出；SPEC §G G1）：欄位定義同 `fingerprints`，dtype 取 pandas dtype 字面，
    `values_native` 依 DataFrame 欄之 numpy dtype，`column_order_sha256` 依 DataFrame 欄序。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def assert_legacy_compatible(fingerprint: Mapping[str, Any]) -> None:
    """沿用基準相容斷言（SPEC §G R4-A）：`fingerprint["columns"][*]["dtype"]` 皆屬 `LEGACY_COMPATIBLE_DTYPES`，
    否則 AssertionError（列出不相容欄；該欄須於 Task 0.5 以 `values_native` 重凍，不得以 float32 鍵通過）。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def bitwise_diff(before: Mapping[str, Any], after: Mapping[str, Any], *, legacy: bool = False) -> List[str]:
    """兩份值指紋之逐位元差異清單（空＝相等）。新凍結（`legacy=False`）比 `BITWISE_COLUMN_KEYS` 與
    `BITWISE_TABLE_KEYS`；沿用基準（`legacy=True`）先 `assert_legacy_compatible(before)`，再比 `dtype` 與 float32
    `values`、`column_set_sha256`。atol=0、rtol=0（SPEC §G 通過條件）。"""
    raise NotImplementedError("NUMVIEW Task 0.5")


def decision(key: str) -> str:
    """決定紀錄（`DECISIONS_PATH`；全票唯一形 `{criteria_sha256, decisions: {<決定點鍵>: record}, measurement_limitations}`）
    中決定點 `key`（`CORE_DECISION_KEYS` 之一，或 `d_icpage_arm`／`d_research`）之 `record["choice"]`（如
    `polars_float64`／`retain`）；檔缺、鍵缺或 `choice` 缺 ⇒ AssertionError（fail-closed）。"""
    raise NotImplementedError("NUMVIEW Task 1.5")


def core_selector() -> str:
    """依決定紀錄輸出 `test_numview_core.py` 之 pytest `-k` 表示式（SPEC Task 3.1–3.3 之 ASSERT … WHEN … 行：
    每個決定點恰選其一支）。決定紀錄缺或任一決定點缺 ⇒ 拋錯（呼叫端之 `-k` 因而為空 ⇒ 全部分支皆跑 ⇒ 必紅，fail-closed）。
    分支記號（決定值 → 記號）：d_postic polars_float64→`postic_float64`／retain→`postic_retained`；d_mtf unify→`mtf_dtype`／
    retain→`mtf_retained`；d_memmap decouple→`memmap_dtype`／retain→`memmap_retained`；d_winsor_dtype
    unify→`(winsor_dtype and not winsor_dtype_retained)`／retain→`winsor_dtype_retained`；d_codec
    provenance→`codec_by_provenance`／retain→`codec_retained`；d_l2 unify→`l2_unified`／retain→`l2_named`；另恆含
    `core_always`。輸出＝`core_always or <六記號 or 連接>`。記號間之子字串碰撞已逐對檢查：唯一者為
    `winsor_dtype` ⊂ `winsor_dtype_retained`，故以 `and not` 排除。"""
    raise NotImplementedError("NUMVIEW Task 1.5")


def _main(argv: Sequence[str]) -> int:
    if list(argv) == ["core-selector"]:
        print(core_selector())
        return 0
    print("用法: python -m tests.feature_engineering.numview_helpers core-selector", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
