"""GAP-3 UX **Task 7.0b** — 分析時 `label_value` producer（SPEC L2348–2844）。

## 這個模組為什麼存在

`label_value` 原本由**匯出端**（前端 `eventExport.ts`）寫進事件檔。§D-3′ 把它撤掉之後，
現況是：**真實使用者路徑沒有任何 producer**——`/search` 匯出的批次不含 `label_value`，
CSV 不自帶就永遠 `missing_label_value`，條件 IC 對真實批次根本跑不起來。
本模組補的是這個洞。

## 兩階段，不是一個函式

公開**恰兩個**階段函式（SPEC R10，`CODEX-R10-P0-03`）：

- `prepare_analysis_windows()` — 階段 2。**唯一**產生 receipt 與其 hash 之處。
- `resolve_label_value_at_analyze()` — 階段 5。吃階段 2 之**物件**，**不得**重跑 `align_events`。

R9 版只有一個函式同時做 windows 與 values，結果「明示兩階段」只停在散文層：
coverage／split／labels 三個 consumer 各自呼叫它一次，就各自重跑對齊、各自拿到一份 window
——purge 用一份、label 用另一份，正是 §D-3′-a 要根除的東西。

## 為什麼 hash 相同還不夠（R11）

`prepare_analysis_windows` 是**決定性**的 ⇒ 三個 consumer 各自呼叫也會得到**相同 hash**，
「hash 相同」擋不住重入。所以另加 `prepared_token`：**非決定性**，同輸入兩次呼叫必不同值。
驗收比對 token 就能分辨「同一次呼叫傳下去」與「各自重算出巧合相同的值」。

## frozen 的三個陷阱（R12／R13，三家全員實跑打穿）

1. `dataclasses.replace` 會**重跑** `__post_init__` ⇒ 本類別**不得有 `__post_init__`**；
   hash 與 token 皆為建構參數，`replace` 原樣攜帶。
2. frozen 是**淺層** ⇒ `.windows` 若是普通 dict／list，consumer 改一列就能讓內容與 hash 不一致。
   故一律 `tuple[frozen dataclass, ...]`，**禁任何 dict／list／可變容器出現在欄位型別中**。
3. `MappingProxyType` **不隔離建構時傳入的 mutable dict alias** ⇒ 持有原 dict 者改值即改
   receipt，且 `replace` 會把同一個 proxy 帶到 `prepared1`，兩者一起變。
   故 per-symbol purge 亦為 `tuple[SymbolPurgeRow, ...]`，不是 Mapping。

## R3 邊界（跨界的是型別，不是 import）

`api/` 只能經 `momentum.factories.create_event_sample_pipeline()` 的出口取用本模組
（`scripts/check_decoupling_imports.py` 是 **import 規則**，會當場擋掉直接 import）。
🔴 **具名例外**：交接檔寫「出口一律回純資料，例外型別不跨界」，而本模組的
`PreparedAnalysisWindows` **會跨界到 `api/services/ic_analysis_service.py`**。
這是刻意的：SPEC ⑩(ii″) 要求 manifest／split／materialize／`ic_feed` 四處收到的物件
**皆 `is prepared1`**，那是**身分**比對，dict 往返做不到。實查 R3 掃描器只驗 import、
不驗回傳型別 ⇒ 機械閘不會紅，但慣例確實被破，故在此具名。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.canonical_serialize import (
    canonical_event_table_bytes,
    canonical_event_table_sha256,
)
from momentum.Analysis.event_samples.keys import (
    event_direction_sign,
    event_scope_key,
    event_trigger_timeframe,
)
from momentum.Analysis.event_samples.types import AlignmentConfig

# ---------------------------------------------------------------------------
# §F-1′ 支援矩陣（封閉）與 §F-2′ reason
# ---------------------------------------------------------------------------

#: 五個 entry 語意（D1-6 之封閉集合；順序＝契約 `entry_price_semantic.enum`）。
ENTRY_PRICE_SEMANTICS: Tuple[str, ...] = (
    "trigger_open", "trigger_close", "next_open", "decision_bar_open", "decision_bar_close",
)
#: 三個報酬 mode（順序＝契約 `label_return_mode.enum`）。
LABEL_RETURN_MODES: Tuple[str, ...] = (
    "open_to_close", "open_to_horizon_close", "close_to_close",
)

#: 🔴 **幾何上必拒之對**（`D-001` D4.2；R1 `CODEX-R1-P1-01`／`GROK-R1-P1-01` 實跑確認）。
#  形狀＝`{mode: (entry, ...)}`，與契約 `label_definition.fields.label_return_mode.rejected_pairs`
#  **同形狀**（前端鏡像逐鍵對證；本常數與契約之一致性由 `test_gap3_label_feasible_bounds` 守）。
#
#  為什麼是這兩對：`open_to_close` 令 `label_start = entry_at`、`end_idx = entry_idx`；
#  當 entry 之 `field == "close"`（`trigger_close`／`decision_bar_close`）時
#  `entry_at = ct[entry_idx]` 而 `label_end = ct[entry_idx]` ⇒ **窗長 0**
#  ⇒ 三段鏈 `decision_at <= label_start < label_end` 必然 `no_boundary_match`。
#  真實 kline 實跑 k∈{0,2} 皆得 0 窗（見 `D-001` D4.2）。
REJECTED_PAIRS: Mapping[str, Tuple[str, ...]] = MappingProxyType({
    "open_to_close": ("trigger_close", "decision_bar_close"),
})

#: 🔴 §F-1′ 支援矩陣之**唯一**來源（`D-001` Task D4.2）：封閉之 `(entry, mode)` **對**集合。
#  ＝5 entry × 3 mode 之全積**減去** `REJECTED_PAIRS` ⇒ **13 對**。
#  🔴 `decision_offset_bars`（k）與 `horizon_bars`（h）**不參與本集合**：
#     k 只受**契約值域**（`>= 0`，由 normalizer 擋）與**逐事件成對可行域** `feasible(e, k, h)` 限制，
#     h 同理。把 k 寫進矩陣（D1.3 之舊形狀）表達不了「k 與 h 在 `decision_bar_* × open_to_horizon_close`
#     下互相耦合」，那正是 D4.2 要交付的東西。
#
#  🔴 **本集合以「全積減拒收」導出，不手列 13 條**：手列會與 `REJECTED_PAIRS` 漂移，
#     而漂移的方向是**多支援一對** ⇒ fail-open。
SUPPORTED_PAIRS: frozenset = frozenset(
    (entry, mode)
    for mode in LABEL_RETURN_MODES
    for entry in ENTRY_PRICE_SEMANTICS
    if entry not in REJECTED_PAIRS.get(mode, ())
)

#: §F-2′ 之 reason。**字面只引用 Task 1.1 之登記處**，本模組不自寫登記祈使句、不自行計數。
UNSUPPORTED_REASON = "label_producer_unsupported_for_declared_semantics"
#: 🔴 `D-001` D4.2：幾何零窗之**專屬** reason（登記於契約 `capability_unavailable_reasons`）。
#  與 `UNSUPPORTED_REASON` 分開的理由：前者是「這個組合永遠算不出來，換 k／h 也沒用」，
#  後者是「這個組合本批不支援」。合成一個字面會讓 UI 對使用者說錯話
#  （叫他去調 k，而那一對調到天荒地老都是 0 窗）。
ZERO_LENGTH_LABEL_WINDOW_REASON = "zero_length_label_window"

#: normalizer 之鍵集與**固定鍵序**（R13 定死）。多一鍵／少一鍵／型別不符 ⇒ fail-closed。
_SPEC_KEYS: Tuple[str, ...] = (
    "horizon_bars",
    "entry_price_semantic",
    "label_return_mode",
    "decision_offset_bars",
)
_SPEC_TYPES: Mapping[str, type] = {
    "horizon_bars": int,
    "entry_price_semantic": str,
    "label_return_mode": str,
    "decision_offset_bars": int,
}


class LabelProducerError(ValueError):
    """producer 之 fail-closed 例外。**不回退預設值、不做型別轉換。**"""


# ---------------------------------------------------------------------------
# 容器（全部 frozen；欄集逐字照 SPEC，不得多欄少欄）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WindowRow:
    """單一事件之分析時窗。欄集**恰七鍵**（SPEC (β)），按 `event_id` UTF-8 升冪排列。

    🔴 `symbol`／`timeframe` 之來源**唯一**為 `keys.py` 之兩個 accessor（見該檔）。
    `timeframe` 是**觸發** TF，與 `per_tf` 的特徵 TF 不同語意。
    """

    event_id: str
    symbol: str
    timeframe: str
    decision_at_ms: int
    entry_at_ms: int
    label_start_ms: int
    label_end_ms: int


@dataclass(frozen=True)
class PerTfRow:
    """逐 (event_id, timeframe) 之特徵截止點。欄集**恰三鍵**（SPEC R12）。

    這是 coverage／Task 7.7／§G G-3／`ic_feed` 之**唯一**讀取路徑——
    任何一處改成回頭自己算 cutoff，就是第二份實作。
    """

    event_id: str
    timeframe: str
    feature_cutoff_ms: int


@dataclass(frozen=True)
class EntryPriceRef:
    """單一事件之 **entry 基準價座標**（`D-001` Task D4.1）。欄集**恰三鍵**。

    🔴 為什麼是側載（batch 級 tuple）而不是 `WindowRow` 第八鍵：`WindowRow` 之七鍵被
    §G G-3 之 signature 對證引用，加鍵要同步動 G-3（與 `direction_sign` 同一理由）。

    🔴 為什麼 producer 不自己從 `entry_price_semantic` 推 `(bar, field)`：那會是 D1-6
    映射的**第二份實作**。值逐字取自 `align_events` 收據之
    `entry_price_source_bar_open_ms`／`entry_price_source_field`，本模組只搬不算。
    """

    event_id: str
    bar_open_ms: int
    field: str


@dataclass(frozen=True)
class SymbolPurgeRow:
    """逐 symbol 之 purge 下界。欄集**恰兩鍵**，按 `symbol` UTF-8 升冪。

    🔴 型別是 tuple 不是 Mapping（R14）：`MappingProxyType` 擋得住 proxy 上的寫入，
    但擋不住「持有建構時那個 dict 的人改值」，而 `replace` 會把同一個 proxy 帶到 `prepared1`
    ⇒ 兩者一起變。兩家獨立 probe 打穿過這個寫法。
    """

    symbol: str
    purge_lower_bound_ms: int


@dataclass(frozen=True)
class PreparedAnalysisWindows:
    """階段 2 之產出。**不得有 `__post_init__`**（R13 (α)：`replace` 會重跑它，hash／token 會被重算）。

    欄集逐字照 SPEC L2385–2400。所有集合型欄位皆為 tuple／frozenset，無可變容器。
    """

    supported: bool
    windows: Tuple[WindowRow, ...]
    analysis_alignment_receipt_hash: str
    per_tf: Tuple[PerTfRow, ...]
    normalized_spec_bytes: bytes
    allowed_event_ids: frozenset
    purge_lower_bound_ms_by_symbol: Tuple[SymbolPurgeRow, ...]
    prepared_token: str
    reason: Optional[str]
    #: 🔴 **`D-005` 之 A-023**（第十欄）：`+1`（long）／`-1`（short）。
    #  掛在**批次層**而非 `WindowRow`，理由是碼證不是偏好：
    #  ① SPEC L3073-3076 之分類表把 `direction` 列為**批次事實欄**，L3075 逐字寫
    #     「它決定 short 取負」；
    #  ② `import_contract.py:694-696` 已對混方向 fail-closed（`direction_mixed_in_batch`）
    #     ⇒ 做成逐列欄會**造出一個可表達但非法的狀態**，批次 scalar 讓它連表達都表達不出來；
    #  ③ `WindowRow` 之七鍵被 §G G-3 之 signature 對證引用，改它要同步動 G-3。
    #  🔴 **失效觸發**：日後若解除 `direction_mixed_in_batch`，本形狀失效，
    #     須改為 grok 主張之逐列欄版（`WindowRow` 第八鍵）。見 `D-005` A-023 之擇取理由節。
    #  🔴 **無預設值**：沒有方向就不該有 prepared 物件。給預設（例如 `0` 或 `1`）等於
    #     讓「忘了傳」靜默變成一個合法值，而 `0` 會把所有 label 歸零、`1` 會讓 short 反號。
    direction_sign: int
    #: 🔴 **`D-001` Task D4.1**（第十一欄）：與 `windows` **同序同長**之 entry 基準價座標。
    #  `open_to_*` 語意之基準價取自這裡，不再回落 `label_start_ms` 那根的 close
    #  ——在連續 crypto 網格下 `trigger_open` 之 `entry_at == ot[t0_idx] == ct[t0_idx-1]`，
    #  用 close 取價會**靜默**取到 t₀−1 的收盤價（別名錯價，值合法故不會紅）。
    #  🔴 **無預設值**：預設空 tuple 會讓「忘了傳」在 `open_to_*` 下靜默變成全 None。
    entry_price_refs: Tuple[EntryPriceRef, ...]
    #: 🔴 **`D-001` D1.6**（第十二欄）：本批 `event_known_at_decision` 之**相異值集合**（已排序）。
    #  D2-2 單一表示法下恆為 `(False,)`——但**照實帶**，不是寫死：
    #  它是揭露欄的資料來源（IC 分析頁要告訴使用者「這批事件在決策當下都還沒發生」）。
    #
    #  🔴 為什麼掛在這裡而不是讓服務層自己算：服務層拿不到 `align_events` 的收據
    #  （`PreparedAnalysisWindows` 是唯一跨界型別，見檔頭 R3 具名例外），要它自己算
    #  就得在 `api/` 重寫一次 `decision_at >= ct[t0_idx]` ⇒ 第二份實作、必然漂移。
    #  🔴 **不進 `_receipt_hash`**（`D-001` D1.2 明文）：本欄是 D2-2 的恆等式，不是批次身分。
    event_known_at_decision_values: Tuple[bool, ...]


@dataclass(frozen=True)
class AnalysisLabelResult:
    """階段 5 之產出（`GROK-R2-P1-02`：結構化物件，不是裸 map）。"""

    supported: bool
    label_values: Mapping[str, Optional[float]]
    analysis_alignment_receipt_hash: str
    prepared_token: str
    reason: Optional[str]


# ---------------------------------------------------------------------------
# 唯一 normalizer（R13 定死）
# ---------------------------------------------------------------------------

def normalize_event_label_spec(event_label_spec: Any) -> Dict[str, Any]:
    """`event_label_spec` → 固定鍵序之 dict。**唯一** normalizer。

    🔴 **型別判定用 `type(v) is int` / `type(v) is str`，不用 `isinstance`**（R14，三家命中）：
    `isinstance(True, int)` 為真，而 §G S-9 白名單同時含 `bool` 與 `int`
    ⇒ `horizon_bars=True` 會通過寬鬆檢查、卻序列化成 `true` 而不是 `1`，產出**不同 bytes**。
    `numpy.int64` 同理。⇒ 一律 fail-closed，**不得**先 `int()` 轉換。

    🔴 多一鍵／少一鍵皆 fail-closed，**不做預設值填補**：少一鍵就填預設，等於讓
    「使用者沒選」與「使用者選了剛好等於預設的值」變成同一件事，而前者本該問清楚。
    """
    if not isinstance(event_label_spec, Mapping):
        raise LabelProducerError(
            f"event_label_spec 須為 Mapping，實得 {type(event_label_spec).__name__}"
        )
    got = set(event_label_spec)
    want = set(_SPEC_KEYS)
    if got != want:
        raise LabelProducerError(
            f"event_label_spec 鍵集須恰為 {sorted(want)}，實得 {sorted(got)}"
            "（多一鍵／少一鍵皆 fail-closed，不補預設值）"
        )
    out: Dict[str, Any] = {}
    for key in _SPEC_KEYS:  # 固定鍵序；輸出直接餵 S-9 encoder
        value = event_label_spec[key]
        expected = _SPEC_TYPES[key]
        if type(value) is not expected:
            raise LabelProducerError(
                f"event_label_spec[{key!r}] 須為 {expected.__name__}，"
                f"實得 {type(value).__name__}（禁 bool／numpy 純量；不轉型）"
            )
        out[key] = value
    if out["horizon_bars"] < 1:
        raise LabelProducerError(
            f"event_label_spec['horizon_bars'] 須 >= 1，實得 {out['horizon_bars']}"
        )
    if out["decision_offset_bars"] < 0:
        raise LabelProducerError(
            f"event_label_spec['decision_offset_bars'] 須 >= 0，實得 {out['decision_offset_bars']}"
        )
    return out


def normalized_spec_bytes_of(event_label_spec: Any) -> bytes:
    """normalizer 之輸出經 §G S-9 encoder 產出之 **exact bytes**。

    🔴 相等判定一律**位元組相等**，不是 `dict ==`、不是 `json.dumps` 比字串（R13）。
    這是 `resolve` 與 `prepare` 綁定的唯一憑據：否則可以用 `h=7` prepare 拿到 hash／token，
    再用 `h=3` resolve，兩者仍回同一 hash／token 而驗收全綠
    ——那就是 purge 用 h=7、label 用 h=3，§D-3′-a 要根除者的復發。
    """
    return canonical_event_table_bytes(normalize_event_label_spec(event_label_spec))


def spec_is_supported(normalized: Mapping[str, Any]) -> bool:
    """§F-1′ 支援矩陣＝查 `SUPPORTED_PAIRS`（`D-001` D4.2）。

    🔴 判定＝**成對** ∧ `k >= 0`；`horizon_bars` 不參與（任意正整數皆可）。
       `k >= 0` 之下界來自契約（normalizer 已擋負值）；此處再判一次是因為本函式
       也被 golden loader 與前端對證閘直接呼叫，不保證都走過 normalizer。
    🔴 擴充支援域一律改 `REJECTED_PAIRS`／兩個 enum tuple，**不得**在此加 `or` 分支
       ——加了就有第二份矩陣，而 UI 之可選集合是由契約導出的，兩份必然漂移。
    🔴 **k 的上界不在這裡**：那是逐事件的 `feasible(e, k, h)`（需要 bar 表），
       支援與否是**批次前**就能答的問題，可行與否要看資料。混在一起會讓
       「這個語意組合沒交付」與「這批資料的暖機不夠」回同一個 reason。
    """
    return (
        (normalized["entry_price_semantic"], normalized["label_return_mode"]) in SUPPORTED_PAIRS
        and int(normalized["decision_offset_bars"]) >= 0
    )


def unsupported_reason_for(normalized: Mapping[str, Any]) -> Optional[str]:
    """不支援之 reason 字面；支援 ⇒ `None`（`D-001` D4.2）。

    兩個字面**互斥**：幾何零窗之兩對回 `ZERO_LENGTH_LABEL_WINDOW_REASON`，
    其餘不支援情形回 `UNSUPPORTED_REASON`。
    """
    if spec_is_supported(normalized):
        return None
    entry = normalized["entry_price_semantic"]
    mode = normalized["label_return_mode"]
    if entry in REJECTED_PAIRS.get(mode, ()):
        return ZERO_LENGTH_LABEL_WINDOW_REASON
    return UNSUPPORTED_REASON


# ---------------------------------------------------------------------------
# `D-001` D4.2：逐事件成對可行域（純函式；以 bar index 閉式算，**不重跑對齊**）
# ---------------------------------------------------------------------------

def entry_bar_index(entry: str, *, t0_idx: int, k: int) -> int:
    """D1-6 之 entry bar index（**只算 index，不取價、不判邊界**）。

    🔴 這**不是** `alignment._entry_mapping` 的第二份實作：那支同時回 `field` 並對
    `next_open` 之越界 raise；本函式只做 index 算術，供可行域閉式使用。
    兩者之 index 部分逐字相同，一致性由 `test_gap3_label_rawbar_oracle` 之期望表守
    （該表獨立寫死 `(offset, field)`，兩邊同時錯才會漏）。
    """
    if entry in ("trigger_open", "trigger_close"):
        return t0_idx
    if entry == "next_open":
        return t0_idx + 1
    if entry in ("decision_bar_open", "decision_bar_close"):
        return t0_idx - k
    raise LabelProducerError(f"未知之 entry_price_semantic：{entry!r}（封閉集合，不猜）")


def end_bar_index(mode: str, *, t0_idx: int, entry_idx: int, h: int) -> int:
    """三個 mode 之 `end_idx`（逐字對應 `alignment.align_events` 之三分支）。"""
    if mode == "close_to_close":
        return t0_idx + h
    if mode == "open_to_close":
        return entry_idx
    if mode == "open_to_horizon_close":
        return entry_idx + h
    raise LabelProducerError(f"未知之 label_return_mode：{mode!r}（封閉集合，不猜）")


def feasible(
    event_id: str,
    k: int,
    h: int,
    *,
    mode: str,
    entry: str,
    t0_idx: int,
    n_bars: int,
    coverage_ok: bool,
) -> bool:
    """逐事件成對可行性謂詞（`D-001` D4.2 之**唯一**定義）。

    `feasible(e, k, h) = (t0_idx − k ≥ 0) ∧ (end_idx(e, k, h) ≤ n_bars − 1) ∧ coverage_ok(e, k)`

    🔴 **不是** k∈ℕ × h∈ℕ，也**不是**兩個獨立區間：`decision_bar_* × open_to_horizon_close`
    之 `end_idx = t0_idx − k + h` 使 k 與 h **耦合**（k 變大反而讓 end 條件變鬆）。
    這正是本謂詞取代「兩個 range」的理由。

    🔴 **誠實邊界（`D-001` D4.2 R4 `CODEX-R4-P2-01`／`GROK-R4-P2-01`）**：本謂詞只涵蓋
    **幾何／coverage** 三條（對應 `warmup_insufficient_*`／`label_window_incomplete`／coverage）。
    `align_events` 之 `missing_bar`／`nonpositive_reference_price`／`entry_before_decision`／
    `feature_after_decision` **不納入**：超出上界 ⇒ 幾何上必失敗；在上界內 ⇒ **不保證**零 failures。
    UI 與驗收文案不得把「≤ 上界」寫成全批成功保證。

    🔴 `next_open` 之 `entry_idx = t0_idx + 1` 也受 `≤ n_bars − 1` 約束——但那條只在
    `end_idx` 一併涵蓋（`open_to_*` 之 end 由 entry 導出；`close_to_close` 之 end 與 entry 無關，
    故 `next_open × close_to_close` 於資料末端之 `missing_bar` 屬上列**未涵蓋**之 loud 失敗）。
    """
    if h < 1:
        raise LabelProducerError(f"{event_id}: h 須 >= 1，實得 {h}")
    if k < 0:
        raise LabelProducerError(f"{event_id}: k 須 >= 0，實得 {k}")
    if t0_idx - k < 0:
        return False
    entry_idx = entry_bar_index(entry, t0_idx=t0_idx, k=k)
    if end_bar_index(mode, t0_idx=t0_idx, entry_idx=entry_idx, h=h) > n_bars - 1:
        return False
    return bool(coverage_ok)


@dataclass(frozen=True)
class EventGeometry:
    """`feasible_bounds` 之逐事件輸入（純索引；由 `records` ＋ bar 表導出，不經對齊）。"""

    event_id: str
    t0_idx: int
    n_bars: int
    #: 🔴 coverage 之**上界索引**：`decision_idx >= coverage_min_idx` 才有 per-TF feature cutoff。
    #  ＝各分析 TF 之首根 `close_time_ms` 在錨定 TF `open_time_ms` 上的 `searchsorted(left)`。
    coverage_min_idx: int


@dataclass(frozen=True)
class FeasibleBounds:
    """兩個**條件上界**（`D-001` D4.2）＋其狀態字面。

    🔴 狀態欄是**封閉集合**而不是「用 None 表達三種意思」：`None` 同時要表示
    「無可行值」與「本 mode 無上界」時，UI 只能猜，而猜錯的方向是**謊報安全**。
    """

    #: `min_e max{k : feasible(e, k, h_selected)}`；`k_status != "bounded"` 時為 `None`。
    k_max_feasible_at_h: Optional[int]
    #: `min_e max{h : feasible(e, k_selected, h)}`；`h_status != "bounded"` 時為 `None`。
    h_max_feasible_at_k: Optional[int]
    #: `"bounded"`｜`"no_feasible_k"`（該 h 下全批無可行 k）
    k_status: str
    #: `"bounded"`｜`"no_feasible_h"`｜`"h_inert_for_mode"`（`open_to_close`：end 與 h 無關 ⇒ 無幾何上界）
    h_status: str


def _max_feasible_k(g: EventGeometry, h: int, *, mode: str, entry: str) -> Optional[int]:
    """單事件之 `max{k : feasible(e, k, h)}`；無可行 k ⇒ `None`。**閉式，O(1)**。

    🔴 為什麼一次判定就夠（不是掃描）：三條約束對 k 皆單調——
    ① `t0_idx − k ≥ 0` 與 ③ coverage 皆在 k **越小越鬆**，故上界 `k_hi = min(t0_idx, t0_idx − coverage_min_idx)`；
    ② `end_idx ≤ n_bars − 1` 之 `end_idx` 對 k 之斜率為 `0`（非 decision_bar entry，或 `close_to_close`）
       或 `−1`（`decision_bar_* × open_to_*`）⇒ 在 `k_hi` 處**最鬆**。
    ⇒ 三條同時在 `k_hi` 最鬆 ⇒ `k_hi` 不可行 ⇒ 任何 k 皆不可行。
    """
    k_hi = min(g.t0_idx, g.t0_idx - g.coverage_min_idx)
    if k_hi < 0:
        return None
    if not feasible(g.event_id, k_hi, h, mode=mode, entry=entry,
                    t0_idx=g.t0_idx, n_bars=g.n_bars, coverage_ok=True):
        return None
    return k_hi


def _max_feasible_h(g: EventGeometry, k: int, *, mode: str, entry: str) -> Tuple[Optional[int], str]:
    """單事件之 `(max{h : feasible(e, k, h)}, status)`。

    🔴 「h 是否參與 end」**機械導出**（比較 `end_bar_index` 於 h=1 與 h=2），
    不是把 `open_to_close` 寫死在條件式裡——寫死就會與 `end_bar_index` 漂移。
    """
    if g.t0_idx - k < 0 or k > g.t0_idx - g.coverage_min_idx:
        return None, "no_feasible_h"
    entry_idx = entry_bar_index(entry, t0_idx=g.t0_idx, k=k)
    e1 = end_bar_index(mode, t0_idx=g.t0_idx, entry_idx=entry_idx, h=1)
    e2 = end_bar_index(mode, t0_idx=g.t0_idx, entry_idx=entry_idx, h=2)
    if e1 == e2:  # h 不參與 end ⇒ 無幾何上界（值本身亦不隨 h 變）
        return (None, "h_inert_for_mode") if e1 <= g.n_bars - 1 else (None, "no_feasible_h")
    # 斜率為 +1 ⇒ `end(h) = e1 + (h − 1)` ⇒ `h <= n_bars − 1 − e1 + 1`
    h_hi = g.n_bars - 1 - e1 + 1
    if h_hi < 1:
        return None, "no_feasible_h"
    if not feasible(g.event_id, k, h_hi, mode=mode, entry=entry,
                    t0_idx=g.t0_idx, n_bars=g.n_bars, coverage_ok=True):
        return None, "no_feasible_h"
    return h_hi, "bounded"


def event_geometries(
    records,
    bars_by_tf,
    *,
    timeframes: Sequence[str],
) -> Tuple[EventGeometry, ...]:
    """`records` ＋ bar 表 → 逐事件之純索引幾何（**不呼叫 `align_events`**）。

    🔴 `t0` 不是錨定 TF 之 bar open ⇒ 該事件**略過**（不猜最近的一根）：那是
    `no_boundary_match`，屬對齊層 loud 失敗，不在幾何可行域之責任範圍。
    🔴 `coverage_min_idx` 取**各分析 TF 首根 close** 之最大者在錨定 TF `open_time_ms` 上之
    `searchsorted(left)`——逐字對應 `align_events` 的 `_select_cutoff_idx(...) < 0 ⇒
    warmup_insufficient_<sub_tf>`。
    """
    out: List[EventGeometry] = []
    tfs = tuple(str(t) for t in timeframes)
    for rec in _records_as_tuple(records):
        symbol = event_scope_key(rec)
        tf = event_trigger_timeframe(rec)
        sym_bars = bars_by_tf.get(symbol) or {}
        anchor = sym_bars.get(tf)
        if anchor is None or len(anchor) == 0:
            continue
        ot = anchor["open_time_ms"].to_numpy()
        t0 = int(rec["t0"])
        pos = int(ot.searchsorted(t0))
        if pos >= len(ot) or int(ot[pos]) != t0:
            continue  # no_boundary_match：不在幾何可行域之責任範圍
        first_closes = []
        for sub_tf in (tfs or (tf,)):
            sub = sym_bars.get(sub_tf)
            if sub is None or len(sub) == 0:
                first_closes = None
                break
            first_closes.append(int(sub["close_time_ms"].to_numpy()[0]))
        if first_closes is None:
            continue  # missing_bar：同上，loud 失敗不在本函式責任內
        cov_ms = max(first_closes)
        out.append(EventGeometry(
            event_id=str(rec["event_id"]),
            t0_idx=pos,
            n_bars=int(len(ot)),
            coverage_min_idx=int(ot.searchsorted(cov_ms, side="left")),
        ))
    return tuple(out)


def feasible_bounds(
    records,
    bars_by_tf,
    *,
    event_label_spec,
    timeframes: Sequence[str],
) -> FeasibleBounds:
    """兩個條件上界（`D-001` D4.2；＝`D-006` D4.2 實作要點②之 `bounds()`）。

    🔴 **函式名與 `D-006` 之 `bounds` 不同**：`bounds` 是模組級通用名，與呼叫端之區域變數
    衝突風險高；語意與簽章不變（多一個 `timeframes`，因為 coverage 條件是 per-TF 的，
    `D-006` 之三參數表達不了它——這是**細化不是弱化**）。

    🔴 **不重跑對齊**：只用 `searchsorted` 取 index。
    🔴 **min over events**：任一事件不可行即拉低全批上界——上界是**給 UI 顯示的建議**，
       不是輸入鎖（`D-001` 明文）。
    🔴 **誠實邊界**：coverage 條件以對齊層之 per-TF warmup（首根 close ≤ decision_at）代之。
       現行階段 3a（`check_feature_run_coverage`）為**批次級 pass/fail、不剔除任何列**
       ⇒ per-event feature coverage 恆真，兩者一致；日後 3a 若改為逐列剔除，本函式須
       改吃該剔除結果，否則上界會**高報**。具名殘留 `B4-COVERAGE-1`。
    """
    normalized = normalize_event_label_spec(event_label_spec)
    entry = normalized["entry_price_semantic"]
    mode = normalized["label_return_mode"]
    k_sel = int(normalized["decision_offset_bars"])
    h_sel = int(normalized["horizon_bars"])

    geoms = event_geometries(records, bars_by_tf, timeframes=timeframes)
    if not geoms:
        return FeasibleBounds(None, None, "no_feasible_k", "no_feasible_h")

    k_vals = [_max_feasible_k(g, h_sel, mode=mode, entry=entry) for g in geoms]
    if any(v is None for v in k_vals):
        k_max, k_status = None, "no_feasible_k"
    else:
        k_max, k_status = min(int(v) for v in k_vals), "bounded"

    h_pairs = [_max_feasible_h(g, k_sel, mode=mode, entry=entry) for g in geoms]
    h_statuses = {s for _, s in h_pairs}
    if "no_feasible_h" in h_statuses:
        h_max, h_status = None, "no_feasible_h"
    elif h_statuses == {"h_inert_for_mode"}:
        h_max, h_status = None, "h_inert_for_mode"
    else:
        # 混合狀態不可能（status 由 mode 決定、全批同 mode）；防禦性 fail-closed。
        vals = [v for v, s in h_pairs if s == "bounded"]
        if len(vals) != len(h_pairs):
            raise LabelProducerError(
                f"feasible_bounds: 同批 h 狀態不一致（{sorted(h_statuses)}）——mode 應決定狀態，拒絕猜"
            )
        h_max, h_status = min(int(v) for v in vals), "bounded"
    return FeasibleBounds(k_max, h_max, k_status, h_status)


# ---------------------------------------------------------------------------
# 階段 2：prepare-windows
# ---------------------------------------------------------------------------

def _records_as_tuple(records: Any) -> Tuple[Mapping[str, Any], ...]:
    """`records` 之 normalized shape：`tuple[Mapping[str, Any], ...]`（R27）。

    🔴 存取法一律 key access。此處只做形狀正規化，**不改值、不補欄**。
    """
    if isinstance(records, pd.DataFrame):
        return tuple(records.to_dict("records"))
    out: List[Mapping[str, Any]] = []
    for row in records:
        if not isinstance(row, Mapping):
            raise LabelProducerError(
                f"records 每列須為 Mapping（key access），實得 {type(row).__name__}"
            )
        out.append(row)
    return tuple(out)


def _analysis_copy(
    records: Tuple[Mapping[str, Any], ...],
    normalized: Mapping[str, Any],
) -> pd.DataFrame:
    """建**分析用副本**：把 spec 之四值覆寫到記錄副本之對應欄（in-memory）。

    🔴 **不回寫**匯出檔／已落檔事件批——分析參數只作用於本次分析（Task 7.6 之同一原則）。
    🔴 `label_definition.window.horizon_bars` 在**匯入檔**裡的語意是 D-7 深度宣告，
    分析層**禁止**把它讀成答案窗；此處是把**分析用的** h 寫進副本，方向相反，不要混。
    """
    rows: List[Dict[str, Any]] = []
    for rec in records:
        row = dict(rec)
        row["decision_offset_bars"] = normalized["decision_offset_bars"]
        row["entry_price_semantic"] = normalized["entry_price_semantic"]
        ld = dict(row.get("label_definition") or {})
        ld["label_return_mode"] = normalized["label_return_mode"]
        window = dict(ld.get("window") or {})
        window["horizon_bars"] = normalized["horizon_bars"]
        ld["window"] = window
        row["label_definition"] = ld
        rows.append(row)
    return pd.DataFrame(rows)


def _windows_from_receipts(event_level: pd.DataFrame) -> Tuple[WindowRow, ...]:
    """`event_level` → `tuple[WindowRow, ...]`，按 `event_id` **UTF-8 升冪**。"""
    rows = [
        WindowRow(
            event_id=str(r["event_id"]),
            symbol=str(r["symbol"]),
            timeframe=str(r["timeframe"]),
            decision_at_ms=int(r["decision_at_ms"]),
            entry_at_ms=int(r["entry_at_ms"]),
            label_start_ms=int(r["label_start_ms"]),
            label_end_ms=int(r["label_end_ms"]),
        )
        for r in event_level.to_dict("records")
    ]
    return tuple(sorted(rows, key=lambda w: w.event_id.encode("utf-8")))


def _refs_from_receipts(event_level: pd.DataFrame) -> Tuple[EntryPriceRef, ...]:
    """`event_level` → `tuple[EntryPriceRef, ...]`，按 `event_id` **UTF-8 升冪**。

    🔴 排序鍵與 `_windows_from_receipts` **逐字相同**，這就是「同序同長」之來源；
    兩者讀同一個 frame，故不會有一邊有、一邊沒有的列。
    """
    rows = [
        EntryPriceRef(
            event_id=str(r["event_id"]),
            bar_open_ms=int(r["entry_price_source_bar_open_ms"]),
            field=str(r["entry_price_source_field"]),
        )
        for r in event_level.to_dict("records")
    ]
    return tuple(sorted(rows, key=lambda e: e.event_id.encode("utf-8")))


def _known_at_decision_values(event_level: pd.DataFrame) -> Tuple[bool, ...]:
    """`event_level` → `event_known_at_decision` 之**相異值集合**（`False` 在前）。

    🔴 **只搬不算**：值由 `align_events` 寫入，本函式不重算 `decision_at >= ct[t0_idx]`。
    🔴 欄位不存在 ⇒ 回**空 tuple**（不是 `(False,)`）：空與 `(False,)` 語意不同——
       前者是「這批沒有這項事實」，後者是「這批全部為 False」。填 `(False,)` 會讓
       「對齊層忘了寫這一欄」看起來像正常結果。
    """
    if "event_known_at_decision" not in event_level.columns:
        return ()
    return tuple(sorted({bool(v) for v in event_level["event_known_at_decision"].tolist()}))


def _per_tf_from_receipts(per_tf: pd.DataFrame) -> Tuple[PerTfRow, ...]:
    """`per_tf` → `tuple[PerTfRow, ...]`，按 `(event_id, timeframe)` **UTF-8 升冪**。"""
    rows = [
        PerTfRow(
            event_id=str(r["event_id"]),
            timeframe=str(r["timeframe"]),
            feature_cutoff_ms=int(r["feature_cutoff_ms"]),
        )
        for r in per_tf.to_dict("records")
    ]
    return tuple(sorted(rows, key=lambda p: (p.event_id.encode("utf-8"), p.timeframe.encode("utf-8"))))


def purge_lower_bound_rows(
    windows: Sequence[WindowRow],
    *,
    lookahead_bars_declared: Mapping[str, int],
    timeframe_seconds: Mapping[str, int],
    symbols: Sequence[str],
) -> Tuple[SymbolPurgeRow, ...]:
    """§D-3′-a（ii）權威式之**唯一**實作。

    ```
    lookahead_depth_ms(e) = lookahead_bars_declared[e.timeframe] * timeframe_seconds[e.timeframe] * 1000
    label_window_ms(e)    = row(e).label_end_ms - row(e).label_start_ms
    purge_lower_bound_ms(scope) = max over e in scope of max(lookahead_depth_ms(e), label_window_ms(e))
    ```

    🔴 `timeframe_seconds` 是**注入之 map**（R22），**不是** module-level `TIMEFRAME_SECONDS`
    ——在此直讀 module 常數，就等於讓 gate 與 producer 各拿一份可能不同步的表。
    🔴 定義域＝`prepared0.windows`（**對齊成功者**）。對齊失敗之列**沒有 `WindowRow`**，
    公式對它無定義（R26／R27）⇒ 不進 purge、不進 split；但其 `timeframe` **仍留在鍵集內**。
    🔴 `symbols` ＝ **pre-coverage 之 symbol 集合**：某 symbol 於 coverage 後全數消失時，
    該列**仍留在 tuple 內**（R14）。split 讀到不在本次 assignments 的 symbol **略過即可，
    不得 fail**——它只是個沒被用到的下界，不是錯誤。
    """
    by_symbol: Dict[str, int] = {}
    for w in windows:
        tf = w.timeframe
        if tf not in lookahead_bars_declared:
            raise LabelProducerError(
                f"lookahead_bars_declared 缺 timeframe {tf!r}（fail-closed；深度宣告是批次層屬性）"
            )
        if tf not in timeframe_seconds:
            raise LabelProducerError(
                f"timeframe_seconds 缺 timeframe {tf!r}（fail-closed；禁在此直讀 module 常數補上）"
            )
        depth_ms = int(lookahead_bars_declared[tf]) * int(timeframe_seconds[tf]) * 1000
        window_ms = int(w.label_end_ms) - int(w.label_start_ms)
        value = max(depth_ms, window_ms)
        prev = by_symbol.get(w.symbol)
        by_symbol[w.symbol] = value if prev is None else max(prev, value)
    # 🔴 鍵集恰等於 pre-coverage 之 symbol 集合；無 window 之 symbol 下界為 0（沒有事件可 purge）。
    for symbol in symbols:
        by_symbol.setdefault(symbol, 0)
    return tuple(
        SymbolPurgeRow(symbol=s, purge_lower_bound_ms=int(by_symbol[s]))
        for s in sorted(by_symbol, key=lambda x: x.encode("utf-8"))
    )


def project_purge(rows: Sequence[SymbolPurgeRow]) -> Mapping[str, int]:
    """`tuple[SymbolPurgeRow, ...]` → `EventSplitConfig.embargo_ms_by_symbol` 之 Mapping。

    🔴 **唯一合法取值路徑**（R16 具名）：不具名的話，實作者會自己發明一條，
    而最常見的發明是「取全批 max」——那是 §D-3′-a（ii）明禁的 per-scope 冒充。

    🔴 **重複 symbol ⇒ raise**（R17 ①）：dict 生成式會把重複列**靜默折疊**成最後一筆，
    而如果 expected 也用 dict 生成式建，兩邊會相等而綠。所以這裡用例外當 oracle，不用等式。
    """
    seen: Dict[str, int] = {}
    for row in rows:
        if row.symbol in seen:
            raise ValueError(
                f"project_purge: symbol {row.symbol!r} 重複出現（fail-closed）——"
                "dict 會靜默折疊重複列，等式比對抓不到，故在此 raise"
            )
        seen[row.symbol] = int(row.purge_lower_bound_ms)
    # 🔴 回 read-only view（§D-3′-a（ii) 之偽碼逐字）：投影只在呼叫 `split_events` 之當下產生、
    #    用完即棄。回可變 dict 會讓「不得掛回 `PreparedAnalysisWindows`」這條只剩紀律。
    return MappingProxyType(seen)


def _batch_direction_sign(records: Tuple[Mapping[str, Any], ...]) -> int:
    """批內單一方向乘號（`D-005` A-023 第 3 條）。混方向 ⇒ raise。

    🔴 這是**第二道**檢查，不是重做匯入層那道。`import_contract.py:694-696` 已對混方向
    fail-closed，但 prepare 吃的是**本模組自己組的分析用副本**——只信上游，等於把不變式的
    維護責任交給一個本模組管不到的地方。
    """
    if not records:
        raise LabelProducerError("records 為空，無法導出批次 direction（fail-closed）")
    signs = {event_direction_sign(r) for r in records}
    if len(signs) != 1:
        raise LabelProducerError(
            f"批內 direction 不一致（得到 {sorted(signs)}）——"
            "契約 `direction_mixed_in_batch` 已禁；混方向批次無單一 label 符號可言"
        )
    return signs.pop()


def _receipt_hash(
    *,
    event_import_id: str,
    normalized_spec_bytes: bytes,
    windows: Tuple[WindowRow, ...],
    per_tf: Tuple[PerTfRow, ...],
    direction_sign: int,
    entry_price_refs: Tuple[EntryPriceRef, ...],
) -> str:
    """分析時 receipt 之 hash。**決定性**：同輸入同值。

    🔴 與 `prepared_token` 刻意相反：hash 決定性、token 非決定性。
    只有兩者並用才分得出「同一次呼叫傳下去」與「各自重算出巧合相同的值」。

    🔴 **payload 之唯一合法形狀＝下列六個頂層鍵、此固定序**（`D-001` Task D4.1 code fence，
    覆寫原檔 §D-3′-a（iii）之三鍵 fence——原檔 fence 與本函式**既有分叉**，非本次造成，
    已具名於 `D-001` §N）。增鍵／減鍵／改序皆改 hash ⇒ 不得為了「順手」而動。
    """
    payload = {
        "event_import_id": event_import_id,
        # 🔴 `D-005` A-023 第 5 條：`direction_sign` **必須**進 hash 輸入。
        #    否則同一批以 long 與 short 各 prepare 一次會得到**相同 hash**，而兩者的
        #    `label_values` 正負相反 ⇒ 驗收 ⑩「三處讀到同一 hash」會在錯誤前提下全綠。
        "direction_sign": int(direction_sign),
        "normalized_spec_bytes": normalized_spec_bytes.decode("utf-8"),
        "windows": [
            [w.event_id, w.symbol, w.timeframe, w.decision_at_ms,
             w.entry_at_ms, w.label_start_ms, w.label_end_ms]
            for w in windows
        ],
        "per_tf": [[p.event_id, p.timeframe, p.feature_cutoff_ms] for p in per_tf],
        # 🔴 `D-001` D4.1：entry 基準價座標進 hash ⇒ 同一批以不同 entry 語意 prepare
        #    會得到不同 hash。沒有這鍵，`trigger_open × open_to_close` 與
        #    `trigger_close × open_to_close` 之 `windows` 若恰好同值就會撞 hash。
        "entry_price_refs": [
            [e.event_id, e.bar_open_ms, e.field] for e in entry_price_refs
        ],
    }
    return canonical_event_table_sha256(payload)


def prepare_analysis_windows(
    records,
    bars_by_tf,
    *,
    event_label_spec,
    event_import_id,
    lookahead_bars_declared,
    timeframe_seconds) -> PreparedAnalysisWindows:
    """階段 2（prepare-windows）：唯一產生 receipt 與其 hash 之處。"""
    normalized = normalize_event_label_spec(event_label_spec)
    spec_bytes = canonical_event_table_bytes(normalized)
    token = uuid.uuid4().hex  # 🔴 非決定性：同輸入兩次呼叫必不同值（R11 之 2.）

    rows = _records_as_tuple(records)
    # 🔴 鍵集自 `records` 凍結（pre-alignment）⇒ **不隨對齊結果變動**（R11 之 P0 不變式）。
    symbols = sorted({event_scope_key(r) for r in rows}, key=lambda s: s.encode("utf-8"))
    tf_keys = sorted({event_trigger_timeframe(r) for r in rows}, key=lambda s: s.encode("utf-8"))
    # 🔴 `D-005` A-023：批次方向乘號。在**不支援分支之前**就導出——
    #    方向缺失／混方向是資料問題，不該因為 spec 剛好不支援而被略過不報。
    direction_sign = _batch_direction_sign(rows)

    supported = spec_is_supported(normalized)
    # 🔴 **不支援時仍然對齊、仍然產窗**——只有「值」被扣住（§F-2′ 落在階段 5）。
    #    理由是 SPEC 驗收 ④ 明白要求：`decision_offset_bars=3`（不支援）之批次，
    #    仍須能斷言該 eid 之 `WindowRow.decision_at_ms < t0`，用來證明 **k 的映射真的生效了**
    #    而不是被忽略。若在這裡就早退回空窗，那條斷言沒有東西可斷。
    #    ⇒ `supported=False` 的語意是「**不會有 label_value**」，不是「什麼都不算」。
    events = _analysis_copy(rows, normalized)
    receipts, _failures = align_events(
        events, bars_by_tf, AlignmentConfig(timeframes=tuple(tf_keys))
    )
    windows = _windows_from_receipts(receipts.event_level)
    entry_price_refs = _refs_from_receipts(receipts.event_level)
    known_values = _known_at_decision_values(receipts.event_level)
    per_tf = _per_tf_from_receipts(receipts.per_tf)
    purge_rows = purge_lower_bound_rows(
        windows,
        lookahead_bars_declared=lookahead_bars_declared,
        timeframe_seconds=timeframe_seconds,
        symbols=symbols,
    )
    return PreparedAnalysisWindows(
        supported=supported,
        windows=windows,
        analysis_alignment_receipt_hash=_receipt_hash(
            event_import_id=str(event_import_id),
            normalized_spec_bytes=spec_bytes,
            windows=windows,
            per_tf=per_tf,
            direction_sign=direction_sign,
            entry_price_refs=entry_price_refs,
        ),
        per_tf=per_tf,
        normalized_spec_bytes=spec_bytes,
        # 🔴 **初值＝通過驗證之全部 event_id**（R13 (e)）：初值未定的話，
        #    「還沒過 coverage」與「coverage 剔光了」在下游看起來一模一樣。
        allowed_event_ids=frozenset(w.event_id for w in windows),
        purge_lower_bound_ms_by_symbol=purge_rows,
        prepared_token=token,
        # 🔴 `D-001` D4.2：reason 由 `unsupported_reason_for` 導出（幾何零窗之兩對走
        #    專屬字面 `zero_length_label_window`），**不在此二選一硬寫**。
        reason=unsupported_reason_for(normalized),
        direction_sign=direction_sign,
        entry_price_refs=entry_price_refs,
        event_known_at_decision_values=known_values,
    )


def apply_event_coverage(
    prepared: PreparedAnalysisWindows,
    allowed_event_ids,
) -> PreparedAnalysisWindows:
    """階段 3b：把 coverage 之過濾結果寫回，**回傳新物件**。

    🔴 **禁原地寫入**（frozen ⇒ `TypeError`）；一律 `dataclasses.replace`。
    🔴 hash 與 `prepared_token` **原樣攜帶**（本類別無 `__post_init__` ⇒ `replace` 不會重算）
    ⇒ `prepared0 is not prepared1` 而兩者 token／hash 相同，這正是驗收 (ii′) 的形狀。
    🔴 過濾集合**只能縮不能擴**：coverage 的職責是剔除，多出來的 id 代表上游串錯了。
    """
    new_ids = frozenset(str(e) for e in allowed_event_ids)
    if not new_ids <= prepared.allowed_event_ids:
        extra = sorted(new_ids - prepared.allowed_event_ids)
        raise LabelProducerError(
            f"apply_event_coverage: allowed_event_ids 不得擴張，多出 {extra[:5]}"
            "（coverage 只負責剔除；多出來代表來源不是同一次 prepare）"
        )
    return replace(prepared, allowed_event_ids=new_ids)


# ---------------------------------------------------------------------------
# 階段 5：materialize values
# ---------------------------------------------------------------------------

def _close_at(bars: pd.DataFrame, close_time_ms: int) -> Optional[float]:
    """取 `close_time_ms` 那一根的 close。找不到 ⇒ `None`（**不猜最近的一根**）。"""
    ct = bars["close_time_ms"].to_numpy()
    matches = (ct == close_time_ms).nonzero()[0]
    if len(matches) != 1:
        return None
    value = float(bars["close"].to_numpy()[int(matches[0])])
    return value if value == value and value > 0 else None  # NaN 自身不等於自身


def _price_at(bars: pd.DataFrame, bar_open_ms: int, field: str) -> Optional[float]:
    """取 `open_time_ms == bar_open_ms` **唯一**那一根的 `field` 欄。

    找不到／不唯一／欄位不存在 ⇒ `None`（**不猜最近的一根、不回落 close**）。
    🔴 對照 `_close_at` 之索引鍵是 `close_time_ms`；本函式是 `open_time_ms`——
    兩者在連續網格下**相差一根**，混用即為 D4.1 要根除的別名錯價。
    """
    if field not in bars.columns:
        return None
    ot = bars["open_time_ms"].to_numpy()
    matches = (ot == bar_open_ms).nonzero()[0]
    if len(matches) != 1:
        return None
    value = float(bars[field].to_numpy()[int(matches[0])])
    return value if value == value and value > 0 else None


def resolve_label_value_at_analyze(
    prepared,
    bars_by_tf,
    *,
    event_label_spec) -> AnalysisLabelResult:
    """階段 3：依 F-1′ 支援矩陣產生 `label_value`；偏離即 `supported=False`。

    🔴 **spec 綁定**（R12 `CODEX-R12-P1-05`）：本函式收到的 spec 經**同一 normalizer ＋
    S-9 encoder** 產出 bytes 後，與 `prepared.normalized_spec_bytes` **不逐位元組相等 ⇒ fail-closed**。
    沒有這條就能用 `h=7` prepare、`h=3` resolve，兩者回同一 hash／token 而驗收全綠。

    🔴 **不得重跑 `align_events`**：窗一律取自 `prepared.windows`。
    🔴 **尾端不足 ⇒ 該 eid 之值為 `None` 且不進 IC**（loud），**禁填 0**——
    0 是一個合法的報酬值，填了就分不出「沒漲跌」與「算不出來」。
    """
    incoming = normalized_spec_bytes_of(event_label_spec)
    if incoming != prepared.normalized_spec_bytes:
        return AnalysisLabelResult(
            supported=False,
            label_values={},
            analysis_alignment_receipt_hash=prepared.analysis_alignment_receipt_hash,
            prepared_token=prepared.prepared_token,
            reason=UNSUPPORTED_REASON,
        )
    if not prepared.supported:
        return AnalysisLabelResult(
            supported=False,
            label_values={},
            analysis_alignment_receipt_hash=prepared.analysis_alignment_receipt_hash,
            prepared_token=prepared.prepared_token,
            reason=prepared.reason or UNSUPPORTED_REASON,
        )

    # 🔴 `D-001` D4.1：取價分派之**唯一**依據＝normalized spec 之 `label_return_mode`。
    #    不得回頭讀 `entry_price_semantic` 自判 open/close（那是 D1-6 映射的第二份實作，
    #    映射之唯一實作在 `alignment._entry_mapping`，其結果已逐字搬進 `entry_price_refs`）。
    mode = normalize_event_label_spec(event_label_spec)["label_return_mode"]
    refs_by_id = {e.event_id: e for e in prepared.entry_price_refs}
    missing_ref = False

    values: Dict[str, Optional[float]] = {}
    for w in prepared.windows:
        if w.event_id not in prepared.allowed_event_ids:
            continue
        sym_bars = bars_by_tf.get(w.symbol) or {}
        bars = sym_bars.get(w.timeframe)
        if bars is None:
            values[w.event_id] = None
            continue
        if mode == "close_to_close":
            # 🔴 基準價＝`label_start_ms` 那根的 close（＝t₀ 之 close，錨與 entry 無關＝D1-5）。
            #    時間戳取自 align_events 之收據，本函式不自行推導是哪一根。
            base = _close_at(bars, int(w.label_start_ms))
        else:
            # 🔴 `open_to_close`／`open_to_horizon_close`：基準價＝entry bar 之 `field`。
            #    `alignment` 對兩 mode 皆令 `label_start = entry_at`；不等 ⇒ 上游串錯，
            #    **fail-closed 而非回落**（回落會取到別名的 t₀−1 close，值合法故永遠不會紅）。
            if int(w.label_start_ms) != int(w.entry_at_ms):
                raise LabelProducerError(
                    f"{w.event_id}: {mode} 之 label_start_ms({w.label_start_ms}) "
                    f"≠ entry_at_ms({w.entry_at_ms})——收據與 mode 不一致，拒絕取價"
                )
            ref = refs_by_id.get(w.event_id)
            if ref is None:
                # fail-closed：沒有座標就沒有基準價，**不得**回落 `_close_at`。
                missing_ref = True
                values[w.event_id] = None
                continue
            base = _price_at(bars, int(ref.bar_open_ms), ref.field)
        end = _close_at(bars, int(w.label_end_ms))
        # 🔴 `D-005` A-023 第 4 條：**乘號在 producer，不在編排層**。
        #    下游（`ic_feed` → `ic_filter_orchestrator`）是純複製，不會補這個乘號；
        #    且 SPEC 已寫死 producer 級 mutation「short 不取負 ⇒ ②」，
        #    乘號挪到 caller 之後那條 mutation 就打不到東西（`COMPOSER-R2-P2-01`／`GROK-R2-P2-01`）。
        values[w.event_id] = (
            None if base is None or end is None
            else prepared.direction_sign * (end - base) / base
        )
    return AnalysisLabelResult(
        supported=True,
        label_values=values,
        analysis_alignment_receipt_hash=prepared.analysis_alignment_receipt_hash,
        prepared_token=prepared.prepared_token,
        # 🔴 缺 `entry_price_refs` ⇒ 該 eid 之值為 `None` 且 **reason 非空**（loud）。
        #    字面沿用已登記之 `UNSUPPORTED_REASON`（契約 `capability_unavailable_reasons`
        #    為封閉集合，本模組不得自寫新字面——新 reason 之登記屬 D1.1 契約票）。
        reason=UNSUPPORTED_REASON if missing_ref else None,
    )
