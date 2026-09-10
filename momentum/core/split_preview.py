"""Chronological holdout 之**列計畫**唯一實作（EVTLABEL Task 2.2／3.3；R3 `CODEX-R1-P1-04`）。

出生理由：`docs/EVTLABEL_SPEC.md` Task 3.3 之顯式模式 fast-fail 需要在**進 preprocessing 之前**
先估「驗證段有幾個正例／反例」，而 orchestrator 的 `_build_holdout_split_plan` 也要算同一件事。
若兩端各寫一份算術，兩份會漂——R3 三家一致要求抽成單一純函式，並拒絕「事後以
`preview_mismatch` 欄位容忍分歧」的方案（同函式同輸入卻不一致＝bug，不是可揭露的差異）。

🔴 純算術、無副作用、不 import `api`（解耦 R1）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Optional

import numpy as np
import pandas as pd


def holdout_test_row_index(
    n_rows: int,
    *,
    oos_test_size: float,
    purge_gap: int,
    embargo: int,
) -> np.ndarray:
    """回 test 段之**位置索引**（`index_kind="positional"`）。

    定義（與 `ic_filter_orchestrator._build_holdout_split_plan` 逐字相同）：
        split_point = floor((1 - oos_test_size) * n_rows)
        test_rows   = arange(split_point + purge_gap + embargo, n_rows)

    train 段（`arange(0, split_point)`）**不在本函式範圍**：它不需要被預檢共用，
    留在原處可避免把「切分計畫」整包搬家而動到 golden。

    參數皆為已解析之最終值——`purge_gap` 必須是呼叫端算好的
    `max(effective_horizon, label_window_rows)`，本函式**不猜、不查 config**。
    """
    n = int(n_rows)
    split_point = int(np.floor((1.0 - float(oos_test_size)) * n))
    start = split_point + int(purge_gap) + int(embargo)
    return np.arange(start, n, dtype=int)


def holdout_split_point(n_rows: int, *, oos_test_size: float) -> int:
    """train／test 的分界位置（供預檢與診斷；與上式同源）。"""
    return int(np.floor((1.0 - float(oos_test_size)) * int(n_rows)))


#: int64 時間戳之「看起來是秒」判定門檻。2001-09-09 之後的 epoch **毫秒**皆 > 1e12，
#: 而 epoch **秒** 在 2286 年前都 < 1e10 ⇒ 1e11 是一個兩邊都留了一個數量級餘裕的界。
#: 🔴 **本常數是單位政策的唯一真相源**——`split_projection` 亦 import 它，
#: 不得任一端手寫字面量（B2b review：codex／grok／主委**三方獨立**命中該重複）。
MS_MAGNITUDE_FLOOR = 1e11
#: 舊名保留給既有 caller（本檔內部用）。
_MS_MAGNITUDE_FLOOR = MS_MAGNITUDE_FLOOR


def assert_epoch_ms_array(
    values: Any, *, role: str, strictly_increasing: bool = False
) -> np.ndarray:
    """把整數時間戳陣列驗成 **epoch 毫秒**，逐元素檢查；不合規即 raise。

    🔴 **逐元素**而非 `np.all`（B2b review `CODEX-R1-P1-03`）：原本寫成
    `np.all(np.abs(values) < FLOOR)` ⇒ **混合**單位（部分秒、部分毫秒）時 `all` 為 False，
    直接**放行**。混合單位不是「其中一種」，是資料壞掉，必須擋。

    與 `_as_ms`（scalar 版）共用 `MS_MAGNITUDE_FLOOR`——單位政策只有一份。

    `strictly_increasing`：**只有 `feature_index` 需要**（下游以 `row_index[0]` 取「最早時刻」）。
    事件欄（`feature_cutoff_ms` 等）**本來就可以重複**——兩個事件落在同一根 bar 是正常的——
    故預設 `False`。把單調性套到事件欄上會誤擋合法輸入（主委實作時當場踩到）。
    """
    arr = np.asarray(values)
    if arr.size == 0:
        return arr.astype("int64")
    if not np.issubdtype(arr.dtype, np.integer):
        # 🔴 **cast 之前**驗 finite（B2b R2 之 I2；grok／composer）：
        #    `astype("int64")` 會把 NaN 變成 0（或未定義值）⇒ `feature_cutoff_ms == 0`
        #    的事件可能被誤判成 train，且**完全靜默**。
        as_float = np.asarray(arr, dtype="float64")
        if not np.isfinite(as_float).all():
            n_bad = int((~np.isfinite(as_float)).sum())
            raise ValueError(
                f"{role}: 含 {n_bad} 個 NaN／inf——`astype(int64)` 會把它們變成 0 而不報錯"
                "（fail-closed）"
            )
        if not np.all(as_float == np.floor(as_float)):
            raise ValueError(f"{role}: 含非整數值——時間戳必須是整數毫秒（fail-closed）")
        arr = as_float.astype("int64")
    nonzero = arr[arr != 0]
    if nonzero.size:
        looks_seconds = np.abs(nonzero) < MS_MAGNITUDE_FLOOR
        if looks_seconds.any():
            n_bad = int(looks_seconds.sum())
            if n_bad == nonzero.size:
                raise ValueError(
                    f"{role}: looks like epoch seconds, expected milliseconds"
                    "（FF run 的 timestamps.parquet 是秒；餵進來前先 ×1000）"
                )
            raise ValueError(
                f"{role}: **混合**時間單位——{n_bad}/{nonzero.size} 個值看起來是秒、"
                "其餘看起來是毫秒。混合不是『其中一種』，是資料壞掉（fail-closed）"
            )
    # 🔴 **嚴格遞增**（B2b R2 之 I1；grok／codex／主委三方獨立收斂）：
    #    下游以 `index[test_rows[0]]` 當「測試段最早時刻」；索引若非遞增，那個值就不是最早的
    #    ⇒ 答案窗比較用到錯的邊界，且**不拋任何例外**。`diff > 0` 一併涵蓋重複時間戳
    #    （重複會讓集合成員判定失去唯一性）。
    if strictly_increasing and arr.size > 1:
        diffs = np.diff(arr)
        if not np.all(diffs > 0):
            n_bad = int((diffs <= 0).sum())
            first = int(np.argmax(diffs <= 0))
            kind = "重複" if int(diffs[first]) == 0 else "逆序"
            raise ValueError(
                f"{role}: 時間戳非嚴格遞增——第 {first + 1} 個位置{kind}"
                f"（共 {n_bad} 處）。下游以 row_index[0] 取『最早時刻』，非遞增即算錯（fail-closed）"
            )
    return arr.astype("int64")


def assert_positional_rows(
    rows: Any, *, n: int, role: str, require_sorted: bool = True
) -> np.ndarray:
    """把 positional row index 驗成 `0 <= i < n` 且無重複；不合規即 raise。

    🔴 出生理由（B2b review `CODEX-R1-P1-03`）：numpy 對**負索引**會回捲，
    `index[-3]` 會靜默取到尾端第三列 ⇒ 錯誤的 train／test 歸屬而**不拋任何例外**。
    """
    raw = np.asarray(rows)
    if raw.size == 0:
        return raw.astype(int)
    # 🔴 **cast 之前**驗整數性（B2b R2 之 I4；codex／composer）：
    #    `np.asarray(..., dtype=int)` 對 0.5 會截斷成 0 ⇒ **靜默改變歸屬**，
    #    那不是型別噪音，是錯的答案。（主委原判「維持現狀」，依較嚴版推翻。）
    if not np.issubdtype(raw.dtype, np.integer):
        as_float = np.asarray(raw, dtype="float64")
        if not np.isfinite(as_float).all():
            raise ValueError(f"{role}: row_index 含 NaN／inf（fail-closed）")
        if not np.all(as_float == np.floor(as_float)):
            raise ValueError(
                f"{role}: row_index 含非整數值——`dtype=int` 會截斷（0.5→0）而靜默改變歸屬"
                "（fail-closed）"
            )
    arr = np.asarray(raw, dtype=int)
    if arr.min() < 0:
        raise ValueError(
            f"{role}: row_index 含負值 {int(arr.min())}——numpy 會回捲成尾端列，"
            "靜默給出錯誤歸屬（fail-closed）"
        )
    if arr.max() >= int(n):
        raise ValueError(
            f"{role}: row_index 最大值 {int(arr.max())} 超出 universe 長度 {int(n)}（fail-closed）"
        )
    if np.unique(arr).size != arr.size:
        raise ValueError(f"{role}: row_index 有重複位置（fail-closed）")
    # 🔴 **順序**也要驗（B2b R3 之 `CODEX-R3-P1-02`）：範圍與唯一性都對、但**反序**時
    #    `row_index[0]` 就不是「最早的那一列」⇒ `test_start_ms` 取到最晚的 test row，
    #    跨進實際 test 首根的 train 事件會留在 train。與 index 反序是同一個洞的另一半。
    if require_sorted and arr.size > 1 and not np.all(np.diff(arr) > 0):
        raise ValueError(
            f"{role}: row_index 非嚴格遞增——下游以 row_index[0] 取『最早的列』，"
            "反序即算錯（fail-closed）"
        )
    return arr


def _as_ms(index: Any, position: int) -> int:
    """取 `index[position]` 並正規化為 **epoch 毫秒 int**。

    🔴 SPLITUNIFY 之時鐘一律 epoch **毫秒**，與 `ic_filter_orchestrator._normalize_ic_time_index`
    （那支是**「秒」語意**，餵毫秒會 raise）**不同源，不得混用**——見 SPEC C-4（R2 之 D7）。

    🔴 **int64 輸入必須是毫秒，是秒就 raise**（B1 review `GROK-R1-P2-02`）：
    `data_cache/features/**/timestamps.parquet` 存的正是 epoch **秒**，直通就會得到
    year=1970 的「邊界」而**不拋任何例外**，B2b／B3 複用後答案窗比較會靜默錯 1000 倍。
    本守衛與 `_normalize_ic_time_index` 的「looks like milliseconds」互為反向對稱。
    （主委寫探針時已踩過這個坑一次，卻沒在本函式設防——所以補成機械閘，不靠記得。）

    **時區**：`pd.Timestamp(value).value` 回的是 **UTC 納秒**，故 tz 換算正確——
    naive 與 UTC 逐值相同、非 UTC 時區會依實際絕對時刻位移（主委實跑：Asia/Tokyo 差 9 小時）。
    ⇒ 本函式不會弄錯時區，但**要求同一票內的 `feature_index` 時區慣例一致**；
    一端 naive、一端非 UTC tz-aware 會得到不同邊界（SPEC C-0「必須共用同一個 universe」
    在時區維度上的延伸）。
    """
    value = pd.Index(index)[position]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return int(pd.Timestamp(value).value // 10 ** 6)
    as_int = int(value)
    if as_int and abs(as_int) < _MS_MAGNITUDE_FLOOR:
        raise ValueError(
            f"_as_ms: index[{position}]={as_int} looks like epoch seconds, expected milliseconds"
            "（SPLITUNIFY 時鐘一律毫秒；FF run 的 timestamps.parquet 是秒，餵進來前先 ×1000）"
        )
    return as_int


def holdout_boundary(
    feature_index: Any,
    *,
    oos_test_size: float,
    purge_gap: int,
    embargo: int,
) -> Dict[str, Any]:
    """canonical 邊界之**唯一**產生點（SPLITUNIFY Task 2.1／SPEC C-0）。

    回 `{"train_row_index", "test_row_index", "train_end_ms", "test_start_ms"}`。

    出生理由：事件路徑與 IC 路徑若各自算一次邊界，**即使公式相同也會分歧**——
    因為兩端的 universe 不同。實測（`handoffs/20260911-probe-splitunify-universe-gap.py`、
    receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`）：
    真實 ETHUSDT 1h 20352 列，未裁切時 features 與 bars 逐值相同；EVTALIGN 裁頭尾後
    邊界位移 5 根→2h、24 根→10h、168 根→67h。⇒ **必須共用同一個 universe 與同一支函式**。

    🔴 **本函式以既有兩支定義自身**（`holdout_split_point` ＋ `holdout_test_row_index`），
    不引入第二份切分算術；`M-SU-11` 之 mutation 即針對此。

    🔴 **ms 只供揭露與 `boundary_hash`，禁回流做成員（∈）判定**——成員判定一律走
    `feature_index[row_index]` 的**集合**語意（SPEC C-4）。ms 之導出寫死為
    `train_end_ms = as_ms(feature_index[train_rows[-1]])`、
    `test_start_ms = as_ms(feature_index[test_rows[0]])`（R2 之 D6：v2 只寫「回傳 ms」
    沒寫怎麼導出，實作端寫成 `feature_index[split_point]`（略過 purge／embargo）也能過
    原本的同源自證）。

    🔴 `purge_gap`／`embargo` 是 **row 單位且已包含在 `test_row_index[0]` 這個起點裡**
    （`holdout_test_row_index` ＝ `arange(split_point + purge_gap + embargo, n)`）
    ⇒ 下游做答案窗判定時**不得**再以毫秒相減（SPEC C-4 第一段；R4 之 F1）。

    參數皆為呼叫端算好的最終值——`purge_gap` 須是
    `max(effective_horizon, label_window_rows)`，本函式**不猜、不查 config**。
    """
    index = pd.Index(feature_index)
    if index.size:
        # 邊界 builder 與投影共用同一組不變式（B2b R2 之 I1/I2、R3 之 J1）。
        # 🔴 `DatetimeIndex` **也要驗**——R2 我只補了數值分支，Datetime 分支直接繞過，
        #    等於只修了一半（`CODEX-R3-P1-01`／`GROK-R3-P1-01` 兩家獨立命中）。
        if isinstance(index, pd.DatetimeIndex):
            if index.hasnans:
                raise ValueError("holdout_boundary: feature_index 含 NaT（fail-closed）")
            assert_epoch_ms_array(
                (index.asi8 // 10 ** 6).astype("int64"),
                role="holdout_boundary: feature_index",
                strictly_increasing=True,
            )
        else:
            assert_epoch_ms_array(
                np.asarray(index), role="holdout_boundary: feature_index",
                strictly_increasing=True,
            )
    n = int(len(index))
    if n == 0:
        # 無 universe 即無邊界；回空計畫會讓下游把「沒切」誤讀成「切了但都空」。
        raise ValueError("holdout_boundary: feature_index 為空——無 universe 即無 canonical 邊界")

    split_point = holdout_split_point(n, oos_test_size=oos_test_size)
    train_rows = np.arange(0, split_point, dtype=int)
    test_rows = holdout_test_row_index(
        n, oos_test_size=oos_test_size, purge_gap=purge_gap, embargo=embargo
    )
    return {
        "train_row_index": train_rows,
        "test_row_index": test_rows,
        # 空段回 None，**不得**回 -1 或 0——那會被下游當成「1970 年」或「有值」。
        "train_end_ms": _as_ms(index, int(train_rows[-1])) if train_rows.size else None,
        "test_start_ms": _as_ms(index, int(test_rows[0])) if test_rows.size else None,
    }


def boundary_hash(test_timestamps_ms: Any) -> str:
    """canonical 測試段之 `boundary_hash`（SPLITUNIFY Task 4.1 要點 1）。

    定義逐字：**sorted、int64 毫秒、無空白 JSON** 之 sha256。
    三個約束各有理由，缺一個就不是同一個雜湊：
      · sorted ⇒ 兩端若以不同順序枚舉同一段，雜湊仍相同（比的是**集合**，不是列舉順序）；
      · int64 毫秒 ⇒ 秒／毫秒混用會得到不同雜湊（單位政策共用 `assert_epoch_ms_array`）；
      · 無空白 JSON ⇒ 序列化風格不影響值。

    🔴 空測試段回**空陣列的雜湊**而不是空字串——空字串會與「沒算」混淆。

    🔴 **兩道 fail-closed（B4 review R1：codex／grok 各自實跑命中）**：
      ①**拒收 datetime-like 輸入**——`DatetimeIndex` 進來會以**奈秒**入雜湊，
        於是「同一組時刻」的 ms 陣列與 DatetimeIndex 得到**不同**雜湊
        （codex 實測 `same_instants_same_hash False`）。同一段兩個雜湊＝這個雜湊沒有意義。
        呼叫端請自己轉成 epoch 毫秒 int64（型別驅動，不猜單位）。
      ②**拒收重複時刻**——`sorted` 之後重複值會留在 payload 裡，
        於是「同一個集合」因為來源重複與否得到不同雜湊（codex 實測 `duplicate_accepted`）。
        測試段的時刻本來就該唯一；重複代表上游把某一列算了兩次。
    """
    raw = np.asarray(test_timestamps_ms)
    if raw.dtype.kind in ("M", "m"):
        raise ValueError(
            "boundary_hash: 收到 datetime-like 輸入（dtype="
            f"{raw.dtype}）——會以奈秒入雜湊，同一組時刻會得到兩個不同的雜湊。"
            "請由呼叫端轉成 epoch 毫秒 int64 再傳（fail-closed，不代為換算）"
        )
    values = assert_epoch_ms_array(raw, role="boundary_hash: test_timestamps_ms")
    ints = [int(v) for v in values.tolist()]
    if len(set(ints)) != len(ints):
        dupes = sorted({v for v in ints if ints.count(v) > 1})[:5]
        raise ValueError(
            f"boundary_hash: 測試段時刻有重複 {dupes}——同一個集合會因為來源重複與否"
            "得到不同雜湊，且重複代表上游把某一列算了兩次（fail-closed）"
        )
    payload = json.dumps(sorted(ints), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def count_binary_classes_in_rows(
    binary_labels: Optional[Mapping[int, int]],
    feature_index: Any,
    row_index: Any,
) -> Optional[Dict[str, int]]:
    """數「落在 `row_index` 這些列上的 0/1 標籤」各有幾個；`binary_labels` 為 None ⇒ 回 None。

    EVTLABEL Task 3.3（B3 review R1 修補）：本函式是**唯一**的計數實作。

    🔴 出生理由：原版把「測試段是哪幾列」在 service 端重算一次（自組 purge/embargo、
    自取 config），三家實測證明那份重建**必然**與 orchestrator 分歧。改為由呼叫端交出
    **已經算好的** `row_index`（orchestrator 的 `test_plan.row_index`），本函式只做計數 ——
    沒有第二份切分算術，就沒有可漂的東西。

    `binary_labels` 之鍵＝特徵列時間戳（feature_cutoff_ms），與 `feature_index` 同單位。
    不在 `feature_index` 上的鍵（期間對齊時已被剔除的事件）不計入，也不 raise。
    """
    if binary_labels is None:
        return None
    index = pd.Index(feature_index)
    rows = np.asarray(row_index, dtype=int)
    if len(rows) == 0:
        return {"n_pos": 0, "n_neg": 0}
    selected_index = index[rows]
    # 🔴 `binary_labels` 之鍵是 **epoch 毫秒整數**，而特徵索引通常是 `DatetimeIndex`
    #    （內部 ns）。不換算就永遠對不上 ⇒ 計數恆為 0 ⇒ 明示模式恆 raise、auto 恆退回報酬版，
    #    而且**不會拋任何例外**。本 bug 由 Task 3.4 的 selection-scope 測試抓出來。
    if isinstance(selected_index, pd.DatetimeIndex):
        selected = set((selected_index.asi8 // 10**6).astype("int64").tolist())
    else:
        selected = set(np.asarray(selected_index).tolist())
    n_pos = sum(1 for key, lab in binary_labels.items() if int(lab) == 1 and key in selected)
    n_neg = sum(1 for key, lab in binary_labels.items() if int(lab) == 0 and key in selected)
    return {"n_pos": int(n_pos), "n_neg": int(n_neg)}
