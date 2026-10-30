"""IC 交接 h5／filtered HDF5 之逐欄 float32 無損判定與讀寫（ICPERF Task 0.4 ⑫，docs/ICPERF_SPEC.md v5.35 第 138 行）。

判準（SPEC ⑫「修正」欄）：欄之 float64 值 x 轉 float32 後須
  (a) 有限性逐元不變（float64 有限而 float32 溢位為 ±inf ⇒ 不無損；NaN／±inf 本身照舊）；且
  (b) 相異有限值個數不變（不併值；float32 捨入為單調不減映射 ⇒ 個數不變即相異值間之全序不變 ⇒ 排名與 Spearman 與
      float64 逐位元相同）。
原生 float16／float32 欄恆無損（float16→float32 為精確擴張）。

檔案佈局（v5.34 輸出契約增列）：無損欄存 float32 資料集 `features`（依全序之相對序）；不無損欄存 float64 資料集
`features_f64`，並存 `f64_columns`（int64，嚴格遞增之全序索引）；`feature_names`（由呼叫端寫）為全序。全部無損 ⇒ 不寫
`features_f64`／`f64_columns`，佈局與舊格式（僅 `features`）相同。讀端以 `read_feature_frame` 依全序還原原欄序與 dtype；
舊格式檔（無 `features_f64`）讀法與舊碼相同（`pd.DataFrame(features[:])`）。

本模組為純函式＋以呼叫端傳入之 h5py 群組物件讀寫，不 import `api/`；`api/` 經 `momentum.core` 取用（解耦 R3 豁免）。
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

F32_DATASET = "features"
F64_DATASET = "features_f64"
F64_INDEX_DATASET = "f64_columns"

#: 判定時每塊之最大元素數（float64 8 bytes ⇒ 每塊約 32 MiB；float32 副本與排序副本另計同量級），限峰值記憶體
_CHUNK_ELEMS = 1 << 22

_NATIVE_LOSSLESS = (np.dtype(np.float16), np.dtype(np.float32))


def _distinct_finite_counts_sorted(ordered: np.ndarray) -> np.ndarray:
    """已逐欄排序之 2D 陣列之逐欄相異有限值個數（與 `np.unique` 同語意：-0.0 與 0.0 視為相同；±inf／NaN 不計）。"""
    ordered_finite = np.isfinite(ordered)
    is_new = np.empty(ordered.shape, dtype=bool)
    is_new[0] = ordered_finite[0]
    is_new[1:] = ordered_finite[1:] & (ordered[1:] != ordered[:-1])
    return is_new.sum(axis=0)


def _block_lossless(block64: np.ndarray) -> np.ndarray:
    """float64 2D 區塊逐欄判 float32 往返無損（溢位為判準 (a) 之預期情形，不發警告）。

    只排序一次：float32 捨入為單調不減映射 ⇒ 逐欄排序後之 float64 陣列轉 float32 仍為排序（NaN 仍排末），逐元有限性之
    改變（溢位）與欄內排列無關，故 (a)(b) 兩判準皆可於同一排序結果上判定。"""
    ordered64 = np.sort(block64, axis=0)  # -inf … 有限 … +inf … NaN
    with np.errstate(over="ignore"):
        ordered32 = ordered64.astype(np.float32)
    finite_same = (np.isfinite(ordered64) == np.isfinite(ordered32)).all(axis=0)
    out = finite_same.copy()
    cand = np.flatnonzero(finite_same)
    if cand.size == out.size:
        out = _distinct_finite_counts_sorted(ordered64) == _distinct_finite_counts_sorted(ordered32)
    elif cand.size:
        out[cand] = (_distinct_finite_counts_sorted(ordered64[:, cand])
                     == _distinct_finite_counts_sorted(ordered32[:, cand]))
    return out


def float32_lossless_mask(values: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
    """逐欄判定 float32 往返是否無損（SPEC ⑫ 判準 (a)(b)；原生 float16／float32 恆 True）。

    Args:
        values: DataFrame（逐欄 dtype）或 2D ndarray（整體 dtype）。

    Returns:
        長度＝欄數之 bool 陣列；零列 ⇒ 全 True。
    """
    if isinstance(values, pd.DataFrame):
        dtypes = list(values.dtypes)
        n_rows, n_cols = values.shape
    else:
        arr = np.asarray(values)
        if arr.ndim != 2:
            raise ValueError(f"float32_lossless_mask 需 2D 輸入，實得 ndim={arr.ndim}")
        n_rows, n_cols = arr.shape
        dtypes = [arr.dtype] * n_cols
    mask = np.ones(n_cols, dtype=bool)
    if n_rows == 0 or n_cols == 0:
        return mask
    cand = np.array([i for i, dt in enumerate(dtypes)
                     if not (isinstance(dt, np.dtype) and dt in _NATIVE_LOSSLESS)], dtype=np.int64)
    if cand.size == 0:
        return mask
    step = max(1, _CHUNK_ELEMS // max(1, n_rows))
    for start in range(0, cand.size, step):
        cols = cand[start:start + step]
        if isinstance(values, pd.DataFrame):
            block = values.iloc[:, cols].to_numpy(dtype=np.float64)
        else:
            block = np.asarray(values)[:, cols].astype(np.float64)
        mask[cols] = _block_lossless(block)
    return mask


def write_feature_datasets(group: Any, frame: pd.DataFrame, *, compression: Optional[str] = "gzip") -> np.ndarray:
    """依逐欄無損判定寫 `features`（float32）與（若有不無損欄）`features_f64`／`f64_columns`；`feature_names` 由呼叫端寫，
    其順序須＝`frame.columns`（全序）。

    全部無損 ⇒ `features`＝`frame.to_numpy(dtype=float32)`（與舊寫法位元相同），不寫另兩資料集。

    Returns:
        不無損欄之全序索引（int64，可為空）。
    """
    mask = float32_lossless_mask(frame)
    lossy = np.flatnonzero(~mask).astype(np.int64)
    if lossy.size == 0:
        data32 = frame.to_numpy(dtype=np.float32)
    else:
        data32 = frame.iloc[:, np.flatnonzero(mask)].to_numpy(dtype=np.float32)
    _create(group, F32_DATASET, data32, compression)
    if lossy.size:
        _create(group, F64_DATASET, frame.iloc[:, lossy].to_numpy(dtype=np.float64), compression)
        group.create_dataset(F64_INDEX_DATASET, data=lossy)
    return lossy


def _create(group: Any, name: str, data: np.ndarray, compression: Optional[str]) -> None:
    # 零元素資料集不可分塊壓縮（h5py 需正之 chunk 維度）⇒ 不壓縮
    if compression is None or data.size == 0:
        group.create_dataset(name, data=data)
    else:
        group.create_dataset(name, data=data, compression=compression)


def feature_layout(group: Any) -> Tuple[int, int, np.ndarray]:
    """回 (列數, 全序欄數, 不無損欄全序索引)；並驗 `f64_columns` 綱要（缺一、越界、非嚴格遞增、長度或列數不符 ⇒
    ValueError，拒讀而不默默錯置欄序）。舊格式 ⇒ 索引為空。"""
    ds32 = group.get(F32_DATASET)
    if ds32 is None:
        raise ValueError(f"{F32_DATASET} dataset missing")
    has64, hasidx = F64_DATASET in group, F64_INDEX_DATASET in group
    if not has64 and not hasidx:
        # 舊格式：不加驗（讀法與舊碼相同，由 DataFrame 建構自行報形狀錯）
        width = int(ds32.shape[1]) if ds32.ndim >= 2 else 1
        return int(ds32.shape[0]), width, np.empty(0, dtype=np.int64)
    if has64 != hasidx:
        raise ValueError(f"{F64_DATASET} 與 {F64_INDEX_DATASET} 須同時存在")
    if ds32.ndim != 2:
        raise ValueError(f"{F32_DATASET} 須 2D，實得 shape={ds32.shape}")
    ds64 = group[F64_DATASET]
    idx = np.asarray(group[F64_INDEX_DATASET][:])
    if ds64.ndim != 2 or ds64.shape[0] != ds32.shape[0]:
        raise ValueError(f"{F64_DATASET} shape={ds64.shape} 與 {F32_DATASET} shape={ds32.shape} 列數不符")
    if idx.ndim != 1 or not np.issubdtype(idx.dtype, np.integer):
        raise ValueError(f"{F64_INDEX_DATASET} 須為 1D 整數，實得 dtype={idx.dtype} ndim={idx.ndim}")
    if idx.size != ds64.shape[1]:
        raise ValueError(f"{F64_INDEX_DATASET} 長度 {idx.size} != {F64_DATASET} 欄數 {ds64.shape[1]}")
    total = int(ds32.shape[1] + ds64.shape[1])
    idx = idx.astype(np.int64)
    if idx.size and (idx.min() < 0 or idx.max() >= total or np.any(np.diff(idx) <= 0)):
        raise ValueError(f"{F64_INDEX_DATASET} 須為 [0, {total}) 內嚴格遞增之索引")
    return int(ds32.shape[0]), total, idx


def read_feature_frame(group: Any, columns: Optional[Sequence[str]], index: Any) -> pd.DataFrame:
    """讀特徵矩陣並依全序還原原欄序與 dtype（無損欄 float32、不無損欄 float64）。

    Args:
        group: h5py 群組（含 `features`，可含 `features_f64`／`f64_columns`）。
        columns: 全序欄名；None 或空 ⇒ `feature_{i}`。
        index: DataFrame 索引（長度須＝列數）。
    """
    _rows, total, idx = feature_layout(group)
    names = list(columns) if columns else [f"feature_{i}" for i in range(total)]
    if idx.size == 0:
        return pd.DataFrame(group[F32_DATASET][:], columns=names, index=index)
    if len(names) != total:
        raise ValueError(f"feature_names 長度 {len(names)} != 全序欄數 {total}")
    f32_pos = np.setdiff1d(np.arange(total, dtype=np.int64), idx, assume_unique=True)
    part32 = pd.DataFrame(group[F32_DATASET][:], index=index)
    part64 = pd.DataFrame(group[F64_DATASET][:], index=index)
    combined = pd.concat([part32, part64], axis=1, ignore_index=True)
    order = np.argsort(np.concatenate([f32_pos, idx]), kind="stable")
    out = combined.iloc[:, order]
    out.columns = names
    return out


def f32_dataset_positions(full_positions: np.ndarray, f64_index: np.ndarray, total: int) -> Tuple[np.ndarray, np.ndarray]:
    """全序欄位置 → (`features` 內之欄位置, `features_f64` 內之欄位置)；輸入已排序，分別回落於兩資料集者（皆依輸入相對序）。"""
    full_positions = np.asarray(full_positions, dtype=np.int64)
    is64 = np.isin(full_positions, f64_index)
    f32_pos = np.setdiff1d(np.arange(total, dtype=np.int64), f64_index, assume_unique=True)
    return np.searchsorted(f32_pos, full_positions[~is64]), np.searchsorted(f64_index, full_positions[is64])
