# SPLITUNIFY 第 9 批（b9）偵察 consult — 多 TF 複合鍵與下游單鍵面

brief-kind: consult
task-id: 20260911-SPLITUNIFY-B9-CONSULT-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼**（本輪為偵察，不是實作）。

## 這一輪的目的

b8 已結案。下一批 `b9` 的標的是殘留 **`SU-RESID-2`（多 TF 之 `(event_id, timeframe)` 複合鍵）**，
目前狀態為 `needs-research`、且 `D-001` 明文「不在本延伸範圍」。
本輪**不做實作、也不寫規格**，只做**偵察**：把「要改什麼、改了會連動什麼、哪些地方會靜默錯」
攤開，作為後續 SPEC 的輸入。

依 `D-001` 第 189 行，下游單鍵面**須一併處理**者共六處（皆在
`momentum/Analysis/event_samples/`）：`feature_materialization`／`baseline`／`pattern_bridge`／
`tables`／`ic_feed`／`dedupe`（cluster 折疊）。

## 前提（範本 §0；請逐條挑戰）

fact-verified: `SU-RESID-2` 現況為「每事件恰一個 selected per_tf row，否則 raise」之 fail-closed
→ `docs/SPLITUNIFY_TODO.md:470`
fact-verified: `D-001` 明列六個下游單鍵面須一併處理，且未完成前多 TF 同批維持 fail-closed
→ `docs/SPLITUNIFY_SPEC.D-001.md:11,189`
fact-verified: 主委初步 grep 已在五個檔找到單鍵假設 → `feature_materialization.py:53`
（`merge(..., on="event_id", validate="many_to_one")`）、`:132`（`set_index("event_id")`）；
`pattern_bridge.py:125`；`tables.py:214,229`；`ic_feed.py:108,109,118`；`dedupe.py:120`
（`validate="one_to_one"`）

assumed: 六個檔就是**全部**的單鍵消費面
→ 否證觀測：指出第七個依賴「event_id 唯一」的消費點（含 API 層、前端、golden 基準檔）／
我跑了: 只 grep 了 `event_samples/` 目錄的六個檔，**未**掃 `api/`、`frontend/`、`tests/golden/`
assumed: 複合鍵可在不動 `EventSplitPlan.assignments` schema 的前提下落地
→ 否證觀測：給出必須改 schema 的具體消費點／我跑了: **沒跑**，這是待你們判定的核心問題
assumed: 現行 fail-closed 真的擋得住多 TF 同批（不是宣稱）
→ 否證觀測：構造一個多 TF 事件批，證明它**沒有**被擋、或被擋在錯誤的地方／
我跑了: **沒跑**，請實跑驗證

## 必答（成對，缺一不算完成）

1. **消費面盤點**：除了 D-001 列的六處，還有哪些地方依賴「`event_id` 唯一」？
   請給檔案:行號。若你認為六處就是全部，說明你掃了哪些範圍才得出這個結論。
2. **失效形態**：對每一處，多 TF 複合鍵成立後會**怎麼壞**？請分「會報錯」與
   **「會靜默取到錯的值」**兩類——後者才是真正危險的（例如 `set_index` 後
   `.loc[eid]` 在非唯一索引下回傳 Series 而非純量）。各給至少一個具體例子。
3. **schema 影響**：`EventSplitPlan.assignments`／`receipts.per_tf`／`clusters` 三者
   是否必須改 schema？若必須，哪些 golden 基準會位移？
4. **cluster 折疊**：`dedupe` 的 cluster 折疊在複合鍵下語意是什麼——
   同一事件的不同 TF 應該折成一個 cluster，還是各自獨立？給出你的立場與理由。
5. **現行 fail-closed 的真實性**：請**實跑**一個多 TF 事件批，確認它確實被擋、
   且擋在合理的位置（不是靠下游某個 `validate=` 意外爆掉）。附輸出。

## 停輪條件

①必答 1–5 皆有立場；②必答 2、5 須附**實跑或具體反例**，不得只讀碼推論；
③🔴 **禁以「無 finding」當停輪**；④本輪為偵察，**不得**提交規格草案或程式修改。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R1-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。
`CLOSED:` 欄**只列你自己家族**開過的 ID；本輪為首輪，通常留空（**不得**寫 `none`）。
裁決塊三行分寫：

```
VERDICT: proceed
BLOCKED-BY:
CLOSED:
```
