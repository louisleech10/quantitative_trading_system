# SPLITUNIFY C10 決斷輪（R2）：投影在事件路徑無落點，三個方案擇一

brief-kind: consult
task-id: 20260911-SPLITUNIFY-X-DECISION-R2
findings-round: R2

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0（挑戰前提）與 canonical finding
四欄格式**全文照做**；findings 用 `## <FAMILY>-R2-P<0-3>-<NN>`，結尾附 **Verdict**。
**禁改碼**；碼證以檔案:行號指名。

## 這是什麼

R1 三家審已收斂 13 群集（`handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md`），
其中 12 群集有明確處置，**只剩 C10 無方案**。本輪要的是**一個可執行的裁定**，不是選項清單。
使用者已離線並授權「有問題找委員會討論共識，做完前不要停下來」⇒ 本輪結論直接進 SPEC v2。

## C10 是什麼（主委在 R1 自產版提出，三家皆未提）

consult D1 裁定「事件切分改為由時間切分**投影**」。R1 三家給的投影簽名都要求呼叫端持有
`feature_index`。**但事件路徑沒有這個東西。**

fact-verified: `EventSplitPlan` 之唯一 producer ＝ `split_events`
（`momentum/Analysis/event_samples/event_split.py:41`），唯一呼叫點
`momentum/Analysis/event_samples/pipeline.py:691`
← `grep -rn "split_events" momentum api tests | grep -v event_split.py:`。

fact-verified: 該呼叫點之唯一**生產** caller ＝ `api/services/case_import_service.py:1610`
（`self._pipeline.run_with_params(records, bars, test_fraction=..., embargo_ms=..., tier_min_test_events=...)`），
參數不含任何 `SplitPlan`（`pipeline.py:507-517`）。

fact-verified: 該路徑亦**沒有特徵列 universe**：`run_with_params` 建的 `EventPipelineConfig`
不帶 `feature_config`（`pipeline.py:512-516`），故 `_materialize` 直接回 `None, None, None`
（`pipeline.py:654-657`）。

fact-verified: IC 側的 `SplitPlan` 由 `ic_filter_orchestrator._build_holdout_split_plan`
（`:561`，docstring 逐字「建立**單幣** chronological holdout」）在**另一個 service** 建立，
呼叫點 `:1256`；`index_kind="positional"`（`:602`），`row_index` 是對 `features_df` 的位置索引。
R1（R4：services 不互 import；R1：momentum 不 import api）擋住兩者直接傳遞。

## 主委已做的實測（方案 2 已出局，別再提）

主委原傾向「canonical 邊界下傳、兩端各自以自己的 universe 用同一純函式算」（方案 2）。
**自己的探針把它否證了。**

探針：`handoffs/20260911-probe-splitunify-universe-gap.py`
receipt：`handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`（rc=1）

- 真實 ETHUSDT 1h（FF run `4a8a0b3726cc906ab3534994605e77f5`，20352 列）**未裁切**時，
  features 與 bars 兩個 universe 逐值相同，邊界相同。
- EVTALIGN 之期間對齊會裁頭尾。裁切後邊界位移實測：
  頭尾各裁 1 根 ⇒ 0 h；5 根 ⇒ −2 h；24 根 ⇒ −10 h；168 根 ⇒ −67 h。

⇒ 只要特徵被裁過，兩端各自算的邊界就分歧。方案 2 仍是兩份算術，違反 C-2。**出局。**

## 🔴 必答（給**可執行的裁定**，不是選項清單）

### 1. C10 三選一（必須選一個，並寫判準）

**方案 1 — 投影上移到 IC 側，事件掃描端不再自產驗證段數字**
- 事件掃描報告之 `summary.split` 改 `{"status":"unavailable","reason":"canonical_split_owned_by_ic_analysis"}`。
- 代價：`event_forward_return_table` 只取 test 段事件（`momentum/Analysis/event_samples/tables.py:305`），
  失去切分輸入後該表要怎麼辦？（全樣本＋loud 揭露？還是一起 unavailable？）**請正面答。**

**方案 3 — 事件掃描端載入同一 post-trim feature universe**
- `EventImportService` 須解析一個 FF run 並取得裁切後的 `features_df.index`。
- 代價：該 endpoint 目前完全不碰 FF run（`api/services/case_import_service.py:1560-1628`
  只載 `bars_from_kline_cache`）；新增 features_run_id 參數＝跨棧改動（請求模型、前端、契約）。
  **請評估這是不是本票該吃的範圍。**

**方案 4（主委新提）— 不合併，改為消歧義＋揭露**
- 承認兩個 endpoint 切的是**不同母體**（IC 切特徵列、事件掃描切事件），故不存在單一邊界。
- 只有 IC 報告的數字叫「驗證段」；事件掃描端的數字改名為
  「事件掃描內部訓練／評分切分」，並標 `split_authority: "event_local_non_canonical"`。
- 代價：consult D1「事件切分改為投影」需部分改寫；C-1「邊界唯一」降級為
  「命名唯一＋權威唯一」。**這是不是在用改名迴避問題？請正面打。**

### 2. 如果選方案 4，C-2（禁第二份算術）還成立嗎？

兩份算術仍然存在，只是不再同名。這是可接受的分期，還是 consult D1 被實質推翻？
請給判準（看碼證，不數人頭）。

### 3. 使用者實際會看到什麼

使用者的原始抱怨是「同一批事件、同一次 UAT 看到兩個互相矛盾的驗證段數字」。
你選的方案，**使用者在畫面上還會不會看到兩個數字**？若會，第二個數字叫什麼、
旁邊寫什麼才不會再誤導？請寫出**實際字串**。

### 4. R1 的 12 個已收斂群集，有沒有哪一條因為 C10 的裁定而失效或需要改寫？

逐條看 `handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md` 之群集表，
指名受影響者（尤其 C2 投影簽名、C5 clusters／summary、C7 消費者處置）。

### 5. 批次是否要重排

若選方案 1 或 4，B2（純函式＋golden）與 B3（接線）的內容會變。請給新的四批切分，
或說明原切分仍成立。

## 停輪條件

① 必答 1–5 皆有明確立場（不得只列選項）；② 必答 1／3 有具體檔案:行號或實際字串；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭），主委依較嚴版本收斂並具名殘留。
④ 禁以「三家零 finding」當停輪理由——零 finding 須走 sentinel 契約。

## 本 brief 之前提（逐條標）

fact-verified: 方案 2 已被實測否證 → 上方 receipt，rc=1，逐值表已附。

fact-verified: `split_events` 唯一呼叫點與唯一生產 caller → 上方 grep 命令。

fact-verified: 事件掃描端無 feature universe → `pipeline.py:512-516` 與 `:654-657` 逐行。

assumed: `event_forward_return_table` 在沒有切分時仍有意義（可退回全樣本＋揭露）
← 否證觀測：該表之統計定義本身要求 OOS，全樣本版會被誤讀為 OOS 結果。
／我跑了：**沒跑**，只讀了 `tables.py:298-310`。請正面打（必答 1）。

assumed: 使用者只在意「不要看到兩個同名數字」，不在意兩個切分在數學上是否同源
← 否證觀測：使用者曾要求「表頭一律用統計學／業界標準名」，暗示他在意語意正確而非只是不衝突。
／我跑了：**沒跑**（使用者離線中，不問）。請正面打（必答 3）。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| 前端是否已有元件同時顯示這兩個數字 | 方案 4 改名後前端仍並列兩個「驗證段」 | cost |
| `event_forward_return_table` 之 CI／bootstrap 是否依賴 test 段大小 | 方案 1 退回全樣本後 CI 寬度失真 | cost |

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與 R1 synth（findings 寫進你自己的交件檔）。
- 不得跑 `pytest tests/governance`（小時級）。
- 既有紅基準見 `HANDOFF.md`「既有紅盤點」（`tests/momentum/Analysis` 20 條，非本票造成）。
- 收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（一句話裁定＋最小落地步驟）。
