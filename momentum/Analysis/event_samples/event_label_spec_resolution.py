"""SPLITUNIFY `Task 10.4`：分析用標籤參數之**單一解析入口**（`R5-C10` 1.–2.）。

出生理由（v7 `R5-C10`）：事件掃描端與 IC 端各自導出 `event_label_spec` 之預設，
兩端對同一批事件算出**不同的答案窗與決策根**，切分邊界因此相差一整個週期。
⇒ 值域檢查、深度宣告讀取、預設導出與四鍵補齊一律**只有這一份**；
兩端都呼叫它，不得各自再寫一份。

🔴 **本模組為純函式，不 import `api/`**（Rule 1）：HTTP 狀態碼與 `detail` 形狀留在 route，
本層只以**具名例外**表達錯誤。route 把例外映射成既有的 `kind` 字面與回應
（`Task 10.4` 不可做第五條：不得改 IC route 之錯誤 `kind` 字面與回應）。

🔴 **值域不手刻**：`decision_offset_bars` 之 `min`／`max` 由契約
`momentum/Analysis/contracts/event_import_contract.json` 導出——手刻永遠補不完，
因為值域是資料、不是程式碼（該病灶在 route 內已被連補四刀：型別、缺、值域、bool 子型別）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence


class EventLabelSpecError(Exception):
    """解析失敗之具名例外；`kind` 逐字對應 route 既有之錯誤字面。

    🔴 `kind` 是**契約**，不是訊息：route 依它映射 422 之 `detail.kind`，
    前端與既有測試釘住該字面。新增錯誤型別必須同時在 route 端登記。
    """

    def __init__(self, kind: str, message: str) -> None:
        self.kind = str(kind)
        self.message = str(message)
        super().__init__(f"{self.kind}: {self.message}")


@dataclass(frozen=True)
class ResolvedEventLabelSpec:
    """解析結果。`spec` 恆為**恰四鍵**（normalizer 對多一鍵少一鍵皆 fail-closed）。"""

    spec: Dict[str, Any]
    lookahead_bars_declared: Dict[str, int]
    seed_note: str
    decision_offset_bars_record_values: List[int]
    trigger_timeframes: List[str]
    mixed_timeframe: bool


def _scan_decision_offset_bars(
    records: Sequence[Mapping[str, Any]], *, k_min: Optional[int], k_max: Optional[int],
) -> tuple:
    """掃 records 之 `decision_offset_bars`，回 `(值集合, 是否有缺, 不合契約之值)`。

    🔴 三者**必須分開**（route 端連四輪修補之教訓）：
      - 缺：歷史批之合法形狀（全批一致即放行）。
      - 型別錯：`bool` 是 `int` 之子型別且 `True` 會被當成 1 ⇒ 一律視為型別錯，不是 k=1。
      - 值域外：與型別錯同一類「落檔已損壞」，不另立第四個 kind。
    """
    values, missing, invalid = set(), False, []
    for r in records:
        v = r.get("decision_offset_bars")
        if v is None:
            missing = True
        elif isinstance(v, bool) or not isinstance(v, int):
            invalid.append(v)
        elif (k_min is not None and v < k_min) or (k_max is not None and v > k_max):
            invalid.append(v)
        else:
            values.add(int(v))
    return values, missing, invalid


def resolve_event_label_spec(
    records: Sequence[Mapping[str, Any]],
    *,
    requested_spec: Optional[Mapping[str, Any]],
    declared_receipt: Optional[Mapping[str, Any]],
    k_domain: Mapping[str, Optional[int]],
    batch_label: str = "",
) -> ResolvedEventLabelSpec:
    """由 records、批次深度宣告與請求覆寫，導出**唯一**之分析用 `event_label_spec`。

    參數：
      `records`：該批已落檔之事件列（呼叫端負責查出；本層不碰儲存）。
      `requested_spec`：使用者明給之鍵（**一律優先**；本函式只補沒給的）。
      `declared_receipt`：批次層 `{"lookahead_bars_declared": {...}}`；
        缺時退回逐列欄（第一列），再缺即 `missing_lookahead_declaration`。
        🔴 深度是**批次層 receipt**、住在 payload 頂層，不是每一列上——
        只讀 `records[0]` 對真實批次會拿到 `{}` 而使分析根本跑不完。
      `k_domain`：`{"min": ..., "max": ...}`，由契約導出（呼叫端取自 pipeline 出口）。
      `batch_label`：只用於錯誤訊息之可讀性（例：import_id）。

    邊界（`Task 10.4` 之⑥⑦）：
      ⑥ 混週期批 ⇒ 回「當根」預設並在 `seed_note` 說明**未自動依深度選擇**；
      ⑦ `decision_offset_bars` 值域外 ⇒ `EventLabelSpecError("invalid_decision_offset_bars", …)`。
    """
    recs = [dict(r) for r in records]
    if not recs:
        raise EventLabelSpecError(
            "empty_event_batch", f"事件批 {batch_label!r} 沒有任何 records",
        )
    k_min, k_max = k_domain.get("min"), k_domain.get("max")
    k_values, _k_missing, k_invalid = _scan_decision_offset_bars(
        recs, k_min=k_min, k_max=k_max,
    )
    if k_invalid:
        raise EventLabelSpecError(
            "invalid_decision_offset_bars",
            (
                f"事件批 {batch_label!r} 之 decision_offset_bars 有不合契約的值"
                f"（{k_invalid[:3]}）。契約要求本欄為 int"
                f"{'' if k_min is None else f'>={k_min}'}"
                f"{'' if k_max is None else f'<={k_max}'}"
                "；出現其他型別或超出值域代表落檔已損壞或繞過了匯入驗證，分析層不猜測其意圖。"
            ),
        )

    declared = (declared_receipt or {}).get("lookahead_bars_declared")
    if not isinstance(declared, dict) or not declared:
        row_level = recs[0].get("lookahead_bars_declared")
        declared = row_level if isinstance(row_level, dict) and row_level else None
    if not declared:
        raise EventLabelSpecError(
            "missing_lookahead_declaration",
            (
                f"事件批 {batch_label!r} 沒有答案窗深度宣告"
                "（批次 receipt 之 lookahead_bars_declared 與逐列欄皆缺）——"
                "purge 下界無從導出，故不進行分析。請重新匯入並填寫深度宣告。"
            ),
        )

    spec: Dict[str, Any] = dict(requested_spec or {})
    trigger_tfs = sorted({str(r.get("timeframe")) for r in recs if r.get("timeframe")})
    mixed_tf = len(trigger_tfs) > 1
    if mixed_tf:
        # 混 tf 批**不自動選深度**：各 tf 之「一根」長度不同，取任一個都是猜。
        preset_entry, preset_mode, preset_h = "trigger_open", "open_to_close", 1
        seed_note = "混合 timeframe 批，請手動設定量法與 h（未自動依深度選擇）"
    else:
        depth = int(declared.get(trigger_tfs[0], 0)) if trigger_tfs else 0
        if depth >= 1:
            preset_entry, preset_mode, preset_h = "trigger_open", "open_to_horizon_close", depth
            seed_note = f"本次量法＝持有（預設依宣告深度；續漲需手動選）；h＝{depth}（初始＝宣告深度）"
        else:
            preset_entry, preset_mode, preset_h = "trigger_open", "open_to_close", 1
            seed_note = "本次量法＝當根（預設依宣告深度；續漲需手動選）；當根不用 h"
    spec.setdefault("entry_price_semantic", preset_entry)
    spec.setdefault("label_return_mode", preset_mode)
    # 🔴 「當根」下 `horizon_bars` 仍送 1（inert 哨兵）：`event_label_spec` 恆為恰四鍵。
    spec.setdefault("horizon_bars", preset_h)
    # 🔴 分析用 k 之初始值＝**契約 min 之常數**，不取自該批宣告——
    #    「這批當初宣告過 k=1」與「這次分析要用 k=1」沒有必然關係。
    spec.setdefault("decision_offset_bars", int(k_min if k_min is not None else 0))

    return ResolvedEventLabelSpec(
        spec=spec,
        lookahead_bars_declared=dict(declared),
        seed_note=seed_note,
        decision_offset_bars_record_values=sorted(k_values),
        trigger_timeframes=trigger_tfs,
        mixed_timeframe=mixed_tf,
    )


__all__ = [
    "EventLabelSpecError",
    "ResolvedEventLabelSpec",
    "resolve_event_label_spec",
]
