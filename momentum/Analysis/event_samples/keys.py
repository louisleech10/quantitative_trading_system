"""GAP-3 UX **Task 7.0b** — 事件記錄之 scope／觸發 TF 之**唯一**取值點（SPEC L2487–2500）。

為什麼要有這個檔（不是為了包一層）：`symbol` 這個值在本 epic 有**三個以上**的資料路徑會讀到
（alignment 之 `WindowRow`、hash 之 `event_level`、`event_split` 之 `groupby`、
purge 之 per-symbol 下界、depth map 查表…），而 SPEC R19 已定死
「`symbol` 須與 `event_split.py` 之 `groupby("symbol")` 鍵**同一個值**」。
各處自己 `rec["symbol"]` 讀一次，任何一處日後改成「從檔名推」「從 UI 選單帶」就會靜默分叉
——那正是 §D-3′-a（ii）禁止的 per-scope 冒充。把取值收斂成一個函式，
分叉就變成**改這個檔**這件看得見的事。

🔴 **存取法定死為 key access**（SPEC R27／R28）：一律 `record["symbol"]`，
   **禁** attribute access（`record.symbol`）、**禁** `records[event_id]` 之 id 下標。
   理由：`records` 之 normalized shape 為 `tuple[Mapping[str, Any], ...]`，
   同一物件在 SPEC 內時而 attribute 時而 subscript 就會寫出不可執行的式子
   （R26 主委即因此寫出 `set(e.timeframe for r in records)`）。
   若需按 id 查詢，**先建** `Mapping[event_id, row]` 再 `by_id[eid]["symbol"]`。

🔴 **`timeframe` 為觸發 TF**，與 `per_tf` 之特徵 TF 集合**不同語意**（見 §D-3′-a（ii））。
   兩者都叫 timeframe，混用會讓 purge 下界用錯換算基準。

🔴 **具名邊界（SPEC R20／R21）**：本檔**不**枚舉 consumer 數量、**不**做 AST 掃描強制。
   R20 已刪除「consumer 恰三處」之枚舉（漏算 purge rows／depth 查表／digest keyset），
   R21 把 AST 斷言降為「待裁定」。⇒ 「所有讀取皆須經本檔」是**規範陳述**，
   目前**靠紀律**維持，沒有機械閘。具名殘留見 `docs/GAP3UX_IMPL_HANDOFF.md`。
"""

from __future__ import annotations

from typing import Any, Mapping


class EventKeyError(ValueError):
    """事件記錄缺鍵／型別不符。**fail-closed**：不回退預設值、不猜。"""


def _require_str(record: Mapping[str, Any], field: str) -> str:
    """取一個必為**非空 `str`** 之欄；缺鍵／型別不符／空字串一律 raise。

    🔴 **不做型別轉換**：`str(record[field])` 會把 `None` 變成 `'None'`、把 `float('nan')`
    變成 `'nan'`，兩者都會成為一個看起來合法的 scope 鍵，而 `groupby` 會照樣分組
    ——錯得無聲無息。寧可在這裡炸。
    """
    if not isinstance(record, Mapping):
        raise EventKeyError(
            f"事件記錄須為 Mapping（key access），實得 {type(record).__name__}；"
            "禁 attribute access（SPEC Task 7.0b R27／R28）"
        )
    if field not in record:
        raise EventKeyError(f"事件記錄缺必要欄 {field!r}（fail-closed，不補預設值）")
    value = record[field]
    # 🔴 `type(v) is str` 而非 `isinstance`：str 子類別（含 numpy.str_）之序列化結果
    #    未必與 str 相同，而本值會進 hash 輸入與 groupby 鍵。同 §F-1′ normalizer 之判準。
    if type(value) is not str:
        raise EventKeyError(
            f"事件記錄之 {field!r} 須為 str，實得 {type(value).__name__}（fail-closed，不轉型）"
        )
    if not value:
        raise EventKeyError(f"事件記錄之 {field!r} 為空字串（fail-closed）")
    return value


def event_scope_key(record: Mapping[str, Any]) -> str:
    """事件之 split scope 鍵。**唯一**取值點。

    回傳值須與 `momentum/Analysis/event_samples/event_split.py` 之
    `manifest.table.groupby("symbol")` 鍵**逐字相同**——purge 下界是 per-symbol 的，
    兩邊若不同源，某個 symbol 的下界就會套到另一個 symbol 身上。
    """
    return _require_str(record, "symbol")


#: `direction` 字面 → `label_value` 之乘號。**封閉兩值**，沒有第三個合法輸入。
_DIRECTION_SIGN: Mapping[str, int] = {"long": 1, "short": -1}


def event_direction_sign(record: Mapping[str, Any]) -> int:
    """事件之方向乘號（`+1`／`-1`）。**唯一**取值點（`D-005` 之 A-023）。

    為什麼要有這個：SPEC Task 7.0b 驗收 ② 要求 short 之 `label_value` 為 long 的相反數，
    而**下游沒有任何一層會補這個乘號**——主委實跑
    `ic_filter_orchestrator.py:2894-2908` 只做 missing 檢查／`float()`／finite gate／建 Series，
    `ic_feed.py:80` 是純複製。⇒ producer 不乘，short 批次的條件 IC 符號就整個反轉。

    🔴 **缺鍵／`None`／大小寫變體一律 raise，不補預設**：
    `record.get("direction", "long")` 這種寫法會讓「沒宣告方向」與「宣告為 long」變成同一件事，
    但前者是資料缺失、後者是使用者的選擇。把兩者混起來，錯的那半數字看起來完全正常。
    """
    value = _require_str(record, "direction")
    if value not in _DIRECTION_SIGN:
        raise EventKeyError(
            f"事件記錄之 'direction' 須為 {sorted(_DIRECTION_SIGN)} 之一，實得 {value!r}"
            "（fail-closed；大小寫變體亦不接受——契約枚舉是小寫）"
        )
    return _DIRECTION_SIGN[value]


def event_trigger_timeframe(record: Mapping[str, Any]) -> str:
    """事件之**觸發** TF。**唯一**取值點。

    🔴 這不是特徵 TF：`per_tf` 收據裡的 timeframe 是「要產特徵切片的那些 TF」，
    可以有多個；本函式回的是「t0 落在哪個 TF 的 bar open 上」，每個事件恰一個。
    深度／窗寬換算成 ms 時用的是**本值**（§D-3′-a（ii）之逐列換算，非批內 max／min）。
    """
    return _require_str(record, "timeframe")
