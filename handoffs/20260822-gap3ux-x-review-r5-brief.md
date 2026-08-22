# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R5（三家全員）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／
canonical 四欄／Verdict）。findings 用 canonical ID `## <FAMILY>-R5-P<0-3>-<NN>`
（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
零 findings ⇒ `## <FAMILY>-R5-P3-00` sentinel（須含斷言欄與碼證欄）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷／輸入檔**，非 gating 檔；
  勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。

---

## 🔴 本輪之方法論（沿用 R4，實測有效；請先讀完再開工）

R4 首次改用下列三項，量到的差異寫在這裡供你判斷本輪是否仍該這樣做：

**一、主委不指定審查方向。**
R1–R3 三份 brief 共 **10 處**「請攻 X」，而 R3 的 18 條 findings 幾乎全落在點名的軸上。
R4 改為零指令後，同一份 SPEC 多出 **5 條前三輪無人觸及**之 findings，
其中 CODEX-R4-P0-02（D-7 L3 與實碼呼叫鏈矛盾）是 SPEC 與程式碼的真矛盾。
⇒ 本 brief **不含任何「請攻」「重點看」「最重要的是」之句**。
各家**獨立盤點整份 SPEC**，切入點與優先序自定。
下方「主委之未證假設」是**揭露**，不是攻擊清單；你判斷不重要就略過，
你判斷 brief 沒列到的地方更關鍵就去那裡。

**二、fact 全部為可重跑 receipt。** 本 brief 無「主委實讀」。每條 fact 附命令：
```
bash handoffs/20260822-gap3ux-x-review-r5-facts.sh      # 14 條，逐條印命令與 stdout，rc=0
python3 handoffs/20260822-gap3ux-x-review-r5-dims.py    # 六維度契約路徑（遞迴，不預設層級）
```
主委當時輸出留存於 `handoffs/20260822-gap3ux-x-review-r5-facts.out`，可直接 diff。
**你重跑的輸出與該檔不同 ⇒ 以你的為準並開 finding。**

**三、標的版本鎖定。** 見下節 sha256；審查期間主委不改該檔。

---

## 審查標的（版本鎖定）

- 檔案：`docs/GAP3_EVENT_UX_SPEC.md`
- **sha256：`64a22dc689b18b180a72c41c8f232152e6c4739bd3a73a28bd40f55d222df228`**
- 行數：1169　　repo HEAD（產 receipt 當下）：`44bf726c`（branch `main`）
  🔴 **以 sha256 為準，非以 HEAD 為準**：本輪之 receipt 腳本與 brief 於派工後才 commit，
  屆時 HEAD 會前進但**標的檔不變** ⇒ 只有 sha256 不符才代表標的被動過。

**開工第一件事**：`shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`。
與上列**不符即停下**，把不符情形寫成 findings 第一條後結束。

**標的性質**：**規格**，尚未實作。要 review 的是
「這份規格若被照做，會不會做出錯的東西 / 會不會有東西沒被規定到」。

---

## 本輪之標的變更：R4 十九條之處置

R4 三家 Verdict 一致「需修訂後定版」，19 條**全數 ACCEPT、0 條 REJECT、0 條降為具名殘留**
（§C0 條文 2）。reconcile：`handoffs/reconcile/20260822-gap3ux-x-review-r4/synth.md`。
本版即該修訂。SPEC 900→1169 行、Task 38→41、§V 16→18。

| 群集 | R4 findings | 處置落點 |
|---|---|---|
| A | CODEX-R4-P0-01／COMPOSER-R4-P0-01／COMPOSER-R4-P0-02／GROK-R4-P0-01 | 新增 **Task 7.0**；改寫 **Task 7.1／7.2／V-11** 為三層驗證（集合／round-trip／非 enum 欄）；比對基準由 `enum` 改為 `accepted` 減 `pathExclusions` |
| B | CODEX-R4-P1-03／COMPOSER-R4-P1-03／GROK-R4-P0-02 | **§G 新增 S-1..S-8** canonical serialization；Task 2.2 改為純引用 |
| C | CODEX-R4-P1-04／COMPOSER-R4-P1-01／COMPOSER-R4-P1-02／GROK-R4-P0-03 | 新增 **Task 7.6／7.7**、**V-14／V-15**；**§N 之 #8／#10 殘留撤回**改為 Task 7.7 |
| D | CODEX-R4-P1-05／COMPOSER-R4-P1-04／GROK-R4-P1-01 | **Task 7.1「邊界」**加路徑級限制；**深度公式**落 Task 2.1b，由 1.9／V-12 引用 |
| E | CODEX-R4-P0-02 | **Task 1.12** 增 `run_event_study_only()` 契約＋`event_split_plan is None` 時 `ci` 標 unavailable |
| F | CODEX-R4-P1-06 | **Task 7.5** 明定 `control_kind` 唯一傳遞點＋混值 fail-closed＋`not_computed` schema |
| G | CODEX-R4-P1-07 | **Task 1.10** 增信任邊界（系統產生欄 vs 外部上傳欄）＋改名 mutation |
| H | GROK-R4-P1-02 | **§D-7 L1 改寫**；SPEC 新增第 3 條 `SYNC-FORBID` |
| I | COMPOSER-R4-P2-01 | **Task 6.0 補完整命令**；`template_check.sh` 新增佔位形態偵測 |

---

## 必查涵蓋面（指定「哪些面向必須有你的判斷」，不指定結論）

以下七項是**涵蓋面**，不是方向。結論由你自己得出；也可在清單之外開任何 finding。

1. **R4 十九條逐條 CLOSED／OPEN**。你自己提的附碼證；他家提的標「複核同意／異議」。
   🔴 R3→R4 的教訓是「修了但沒修淨」與「修補自己引入新缺口」各出現過
   ——請以**反例重跑**判定閉合，不以「SPEC 有寫」判定。

2. **全棧三欄稽核**（後端 code／前端 UI／wiring）。對本 SPEC 涵蓋到的每項能力逐項查三欄：
   ① 後端 code 是否存在 ② 前端 UI 是否存在 ③ wiring 是否真的接上（呼叫端有沒有傳）。
   三欄任一缺即為缺口；兩端都有但沒接＝靜默失效。
   涵蓋面**不限事件型**：IC 分析頁、Feature Library、`/search` 皆在內。
   立此項之背景：GAP-3 B1–B5 已三輪 code review 蓋章仍漏接六個維度
   ——規格層的漏，審查層抓不出來。

3. **R4 新增之三個 Task（7.0／7.6／7.7）與 §G S-1..S-8 是否逐條可執行**。
   這些是**本輪新產出、未經任何人審查**之內容。

4. **§C0 收斂標準在 SPEC 全文是否被實際遵守**：有無放水語、有無把數值正確性或資料洩漏類
   問題以「留實作階段」「屬工程增強」等方式繞過。

5. **§P 之 41 個 Task 各欄（內容／驗證／存活至／覆蓋風險／邊界／不可做）是否逐條可執行**，
   以及**跨 Task 之相依與同步義務是否互相一致**（R4 已抓到過「對一個不存在的定義下義務」
   與「檔頭禁殘留而 §N 仍殘留」兩種內部矛盾，皆為主委改寫時自行引入）。

6. **本批之實作順序是否可行**：SPEC 現有多組「A 先 B 後」之宣告
   （7.0→7.1→7.2、4.2→7.5、5.2→7.5、3.2→3.3、4.3→5.3、4.1b→7.3、1.10→1.11→1.12）。

7. **Verdict**：可定版／需修訂後定版／不可定版。

---

## 本 brief 前提

### fact-verified（每條可重跑；命令即查證方式）

fact-verified: 標的 SPEC 之 sha256 ＝ `64a22dc689b18b180a72c41c8f232152e6c4739bd3a73a28bd40f55d222df228`、1169 行
  → `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md; wc -l < docs/GAP3_EVENT_UX_SPEC.md`（facts.sh F-01）

fact-verified: Phase 7 六維度分佈於契約之**三個不同巢狀層級**——`required_fields` 四個、
  `optional_fields` 一個（`counterexample_kind`）、`required_fields/label_definition/fields` 一個
  （`label_return_mode`）
  → `python3 handoffs/20260822-gap3ux-x-review-r5-dims.py`（facts.sh F-02）

fact-verified: 六維度之 enum 元素數 ＝ scenario 4／control_kind 4（`accepted` 3）／
  entry_price_semantic 5／label_return_mode 3／decision_offset_bars 無 enum（int, min=0）／
  counterexample_kind 3
  → `python3 handoffs/20260822-gap3ux-x-review-r5-dims.py --counts`（facts.sh F-03）

fact-verified: 契約有**六份**獨立 reason／flag 清單，長度分別為
  `import_failure_reasons` 15／`alignment_failure_reasons` 14／`capability_unavailable_reasons` 3／
  `split_purge_reasons` 1／`split_loud_flags` 1／`degraded_flags` 2
  → facts.sh F-04

fact-verified: `dedupe.py:20` `_POLICY_BY_SCENARIO` 已按四種 scenario 分流；
  `:113` 之 manifest context `ctx_cols` ＝ `("event_id","symbol","timeframe","label","scenario","direction")`
  → facts.sh F-05；`sed -n '105,118p' momentum/Analysis/event_samples/dedupe.py`

fact-verified: `frontend/src/lib/eventExport.ts` 之五處寫死＝`:92`／`:93`／`:95`／`:102`／`:104`；
  `counterexample_kind` 在該檔**完全未出現**
  → facts.sh F-06

fact-verified: `/search` 呼叫端 `page.tsx:522-527` 只傳 `timeframe`／`conditions`／
  `priceChangeMethod`／`horizonBars`，六維度之 opts 一個都沒傳
  → facts.sh F-07

fact-verified: `event_forward_return_table` 定義於 `momentum/Analysis/event_samples/tables.py:88`，
  其 `event_split_plan` 參數**必填**且 `:113` 直接 `.clusters.set_index(...)`
  → facts.sh F-08；`sed -n '88,120p' momentum/Analysis/event_samples/tables.py`

fact-verified: `EventImportPicker.tsx:9` 之 `onPick: (importId: string, icTimestamps: number[]) => void`
  ——只有兩個參數，不傳批次語意
  → `grep -n "onPick" frontend/src/components/ic-analysis/EventImportPicker.tsx`

fact-verified: `RunInfo`（`api/models/feature_factory_models.py:116-133`）**無 `time_range`**，
  而 `feature_reader.py:455` 之 manifest artifact **有** `time_range: {start, end}`
  （legacy run 為 `{start: None, end: None}`）
  → facts.sh F-13；`sed -n '116,133p' api/models/feature_factory_models.py`

fact-verified: 本 SPEC 之三支機械閘現況皆 rc=0
  （`doc_format_precheck.sh`／`spec_ruling_task_sync.sh`／`quant_standard_check.sh`）→ facts.sh F-14

fact-verified: `grep -c "覆蓋風險：無" docs/GAP3_EVENT_UX_SPEC.md` ＝ **0**；
  `grep -c "^- 覆蓋風險" docs/GAP3_EVENT_UX_SPEC.md` ＝ **41** ＝ Task 總數
  → 直接重跑該二命令

### assumed（主委之未證假設；**揭露用，非攻擊清單**）

以下是主委自知未證之處。列出是為了不讓盲點靜默通過，**不是**要你們照單處理。
你可以全部略過；清單之外的東西同樣（甚至更）值得看。

assumed: R4 十九條之處置皆對症，未引入新的內部矛盾。
assumed: §G 之 S-1..S-8 涵蓋了 `event_forward_return_table` 輸出之全部序列化歧義。
assumed: Task 7.1 之 `pathExclusions`（`/search` 只開 C／two_stage）不違反使用者
  「系統不得寫死任一 scenario」之裁定——理由是 CSV 匯入路徑四種全開。
assumed: Task 1.12 之 `run_event_study_only()` 在 `event_split_plan is None` 時把 `ci` 標
  unavailable 是正確處置（cluster bootstrap 無 cluster 資訊時不得產出區間）。
assumed: Task 7.7 之 containment policy（右界須含 `horizon_bars`）足以擋住特徵覆蓋不足。
assumed: 「lookahead 深度 ＝ max(宣告 window, 所有引用欄之標註深度)」對四種 scenario 皆成立。
assumed: Phase 7 之涵蓋面（`/search`＋`/data-preparation`＋IC 頁＋Feature Library）已完整，
  無其他「後端有能力、前端沒接」之殘留。

---

## 不受理範圍（本輪明示，避免無終點審查）

- 純事件研究模式（使用者裁定另立模組，見 §N）
- #9b 規模防護本體（排 GAP-6）
- 標籤方法論討論（使用者裁定排在整個系統完成之後）
- `tests/api` 既有紅 10 failed + 3 errors（非本批造成）
- **G-7 scope 淨差之既有紅**：其基準點凍結於 2026-08-07，至今 503 個 commit，
  被標之檔案最後改動者為 8/18–8/21 之前幾個 session；屬結構性既有紅，非本批造成，
  修它等同為 503 個 commit 重宣告 scope manifest（使用者 2026-08-14 裁定治理不再擴建）
- 實作細節之程式碼審查（標的是尚未實作的規格）
- 治理流程本身（gate／債帳／戳記機制）

---

## 產出

canonical 四欄 findings（含對 R4 十九條之 CLOSED／OPEN）＋ **Verdict**。
**禁改碼、禁改 SPEC**（只產 review 檔）。
收尾只清你自己的 workdir（**勿動 `/private/tmp/claude-501/`**）。
