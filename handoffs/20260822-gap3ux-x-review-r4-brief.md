# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R4（三家全員）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／
canonical 四欄／Verdict）。findings 用 canonical ID `## <FAMILY>-R4-P<0-3>-<NN>`
（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
零 findings ⇒ `## <FAMILY>-R4-P3-00` sentinel（須含斷言欄與碼證欄）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷／輸入檔**，非 gating 檔；
  勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。

---

## 🔴 本輪之方法論變更（與 R1–R3 不同，請先讀完再開工）

2026-08-22 三家 consult 對「主委工作方法」之評估結論：codex／grok 判**有系統性問題**、
composer 判**需改進**，0 家判可接受。其中三項與本 brief 直接相關，本輪逐項改掉：

**變更一：主委不指定審查方向。**
composer 量化證據：R1–R3 三份 brief 共 **10 處**「請攻 X」，而 R3 的 18 條 findings
**幾乎全落在主委點名的軸上** ⇒ 前三輪測到的是「主委已經懷疑的地方」，不是「SPEC 的實際弱點」。
⇒ 本 brief **不含任何「請攻」「重點看」「最重要的是」之句**。
請三家**各自獨立盤點整份 SPEC**，自行決定切入點與優先序。
下方「主委之未證假設」只是**揭露主委心裡的不確定處**，**不是**指派給你們的攻擊清單；
你判斷它們不重要就略過，你判斷 brief 沒列到的地方更關鍵就去那裡——那正是本輪想量到的東西。

**變更二：fact 全部改為可重跑 receipt。**
codex 指出 R1–R3 之 `fact-verified` 多為「查證＝主委實讀」，委員無法獨立重現，
也無法偵測主委讀錯或讀到 stale 版本。
⇒ 本 brief **不再出現「主委實讀」**。每條 fact 都由命令產出，你可自行重跑：
```
bash handoffs/20260822-gap3ux-x-review-r4-facts.sh      # 14 條，逐條印命令與 stdout，rc=0
python3 handoffs/20260822-gap3ux-x-review-r4-dims.py    # 六維度契約路徑（遞迴，不預設層級）
```
主委當時的完整輸出留存於 `handoffs/20260822-gap3ux-x-review-r4-facts.out`，可直接 diff。
**若你重跑的輸出與該檔不同，以你重跑的為準，並開一條 finding。**

**變更三：標的版本鎖定。**
codex 指出 R3 之審查鏈未鎖定同一份 SPEC，委員讀到 stale 版本、結果不可重現。
⇒ 見下節之 sha256；**審查期間主委不改該檔**。

---

## 審查標的（版本鎖定）

- 檔案：`docs/GAP3_EVENT_UX_SPEC.md`
- **sha256：`3bc04411cdf2d1663626d0128e7d462c03f3228a9d1d3ee86f0cd3854dea58b9`**
- 行數：900　　repo HEAD：`01b8e9ef`（branch `main`）
  （SPEC 本身最後一次改動在 `4e2871cd`；其後兩個 commit 只加 handoffs receipt，未動標的檔，
  故 sha256 不變——以 sha256 為準，非以 HEAD 為準。）

**開工第一件事**：`shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`。
與上列**不符即停下**，把不符情形寫成 findings 第一條後結束——不要繼續審一份無法被重現的標的。

**標的性質**：這是**規格**，尚未實作。不要 review 程式碼實作品質；
要 review 的是「這份規格若被照做，會不會做出錯的東西 / 會不會有東西沒被規定到」。

---

## 必查涵蓋面（指定「哪些面向必須有你的判斷」，不指定結論）

以下六項是**涵蓋面**，不是方向。每一項的結論由你自己得出；你也可以在清單之外開任何 finding。

1. **全棧三欄稽核**（本輪新列為必查）。
   對本 SPEC 涵蓋到的每一項能力，逐項查三欄：
   ① **後端 code** 是否存在　② **前端 UI** 是否存在　③ **wiring** 是否真的接上（呼叫端有沒有傳）。
   三欄任一缺即為缺口，兩端都有但沒接＝靜默失效。
   立此項之事故背景：GAP-3 B1–B5 已經三輪 code review 蓋章，**仍漏接六個維度**；
   原因是前三輪審的都是「SPEC 有沒有被正確實作」，而 SPEC 沒要求接、實作沒接就不算違規
   ⇒ **規格層的漏，審查層抓不出來**。
   涵蓋面**不限事件型**：IC 分析頁、Feature Library、案例搜尋 `/search` 皆在內。

2. **R3 十八條之 CLOSED／OPEN**。你自己提的逐條標並附碼證；他家提的標「複核同意／異議」。

3. **R3 遺留四條（D／E／F／G）之現行處置是否足夠**（爭點見下節；主委不列結論）。
   §C0 禁止把正確性類問題降級為具名殘留放行——請據此判定「足夠」的門檻。

4. **§C0 收斂標準在 SPEC 全文是否被實際遵守**：有無放水語、有無把數值正確性或資料洩漏類
   問題以「留實作階段」「屬工程增強」等方式繞過。

5. **§P 之 38 個 Task 五欄（內容／驗證／存活至／覆蓋風險／邊界／不可做）是否逐條可執行**。
   ⚠️ 特別說明其中一段的可信度：主委於本輪開工前剛把 **26 條「覆蓋風險：無」改寫為實質理由**
   （commit `8a89a4c3`），**這批改寫是主委單方產出、未經任何人審查**，其中包含主委自行加上的
   數條跨 Task 同步義務與三條新驗收斷言（Task 1.12 ④／Task 3.1 落檔殘留／Task 7.1 golden 回歸）。
   此段與 SPEC 其餘部分**同等受審**，不因「剛做完」而享有推定正確。

6. **Verdict**：可定版／需修訂後定版／不可定版。

---

## R3 遺留之四條（列爭點，不列結論）

| 代號 | 爭點原文 |
|---|---|
| **D** | Task 7.2 之機械閘「契約 enum 元素數 `==` UI 選項數」可被 disabled 控制項湊過；且 `control_kind` 之 `enum` 為 4 值而 `accepted` 為 3 值（`platform_random_bars` 恆拒，見 F-03），兩數不等使該斷言之基準本身定義不明。 |
| **E** | Phase 7 之全棧接線未涵蓋 **IC 分析頁**與 **Feature Library 之 `time_range`** 對證。 |
| **F** | **G-2 之 canonical serialization 仍未定義。** 主委 R2 裁「留實作階段」，被三家推翻；R3 後仍未補。 |
| **G** | A／B 兩型之**機械式深度定義**；以及選 A／B 時「label 來源不變」之語意漂移。 |

四條在 SPEC 檔頭已列為「未 FROZEN、待 R4 裁定」。主委**不提出**建議處置，避免再次錨定。

---

## 本 brief 前提

### fact-verified（每條可重跑；命令即查證方式）

fact-verified: 標的 SPEC 之 sha256 ＝ `3bc04411cdf2d1663626d0128e7d462c03f3228a9d1d3ee86f0cd3854dea58b9`、900 行
  → `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md; wc -l < docs/GAP3_EVENT_UX_SPEC.md`（facts.sh F-01）

fact-verified: Phase 7 六維度分佈於契約之**三個不同巢狀層級**——`required_fields` 四個、
  `optional_fields` 一個（`counterexample_kind`）、`required_fields/label_definition/fields` 一個
  （`label_return_mode`）
  → `python3 handoffs/20260822-gap3ux-x-review-r4-dims.py`（facts.sh F-02）

fact-verified: 六維度之 enum 元素數 ＝ scenario 4／control_kind 4（`accepted` 3）／
  entry_price_semantic 5／label_return_mode 3／decision_offset_bars 無 enum（int, min=0）／
  counterexample_kind 3
  → `python3 handoffs/20260822-gap3ux-x-review-r4-dims.py --counts`（facts.sh F-03）

fact-verified: 契約有**六份**獨立 reason／flag 清單，長度分別為
  `import_failure_reasons` 15／`alignment_failure_reasons` 14／`capability_unavailable_reasons` 3／
  `split_purge_reasons` 1／`split_loud_flags` 1／`degraded_flags` 2
  → facts.sh F-04

fact-verified: `dedupe.py:20` `_POLICY_BY_SCENARIO` 已按四種 scenario 分流
  （`C: cluster_first`，`A/B/two_stage: all_with_uniqueness`），`:126-128` 未知 scenario 直接 raise
  → facts.sh F-05

fact-verified: `frontend/src/lib/eventExport.ts` 之五處寫死＝`:92 decision_offset_bars: 0`／
  `:93 entry_price_semantic ?? 'trigger_open'`／`:95 scenario ?? 'C'`／`:102 label_return_mode: 'close_to_close'`／
  `:104 control_kind: 'user_labeled_same_trigger'`；`counterexample_kind` 在該檔**完全未出現**
  → facts.sh F-06

fact-verified: `/search` 之呼叫端 `page.tsx:522-527` 只傳 `timeframe`／`conditions`／
  `priceChangeMethod`／`horizonBars`，六維度之 opts **一個都沒傳**（`opts` 介面已有 `scenario?`／
  `entryPriceSemantic?`，見 `eventExport.ts:15`）
  → facts.sh F-07

fact-verified: `event_forward_return_table` 定義於 `momentum/Analysis/event_samples/tables.py:88`
  → facts.sh F-08

fact-verified: `ic_feed.py` 之 `decision_time_rule` 與 `feature_cutoff_rule` 決定特徵截止時點
  → facts.sh F-09

fact-verified: 本 SPEC 之三支機械閘現況皆 rc=0
  （`doc_format_precheck.sh`／`spec_ruling_task_sync.sh`／`quant_standard_check.sh`）
  → facts.sh F-14

fact-verified: `grep -c "覆蓋風險：無" docs/GAP3_EVENT_UX_SPEC.md` ＝ **0**（改寫前為 26）；
  `grep -c "^- 覆蓋風險" docs/GAP3_EVENT_UX_SPEC.md` ＝ **38** ＝ Task 總數
  → 直接重跑該二命令

### assumed（主委之未證假設；**揭露用，非攻擊清單**）

以下是主委自知未證的地方。列出來是為了不讓主委的盲點靜默通過，**不是**要你們照單處理。
你可以全部略過。清單之外的東西同樣（甚至更）值得看。

assumed: 「lookahead 深度 ＝ label 定義所引用之最遠未來根數」此一通則對四種 scenario 皆成立。
assumed: D-7 之三層（L1 registry／L2 強制宣告／L3 禁進切分）合起來足以擋住 label 洩漏。
assumed: Phase 7 之六維度已是「後端有能力、前端沒接」之完整清單，事件型以外無同類殘留。
assumed: 本輪新加之三條驗收斷言（Task 1.12 ④／3.1 落檔殘留 `== 0`／7.1 golden byte 級回歸）
  寫法正確且真能證偽。
assumed: 26 條覆蓋風險改寫中，主委自行推導的跨 Task 同步義務與 SPEC 現有條文無矛盾。
assumed: SPEC 現行之 Phase 相依聲明（Phase 2 不依賴 Task 1.2 端點、Phase 4 不依賴 Phase 1 等）正確。

---

## 不受理範圍（本輪明示，避免無終點審查）

- 純事件研究模式（使用者裁定另立模組，見 §N）
- #9b 規模防護本體（排 GAP-6）
- 標籤方法論討論（使用者裁定排在整個系統完成之後）
- `tests/api` 既有紅 10 failed + 3 errors（R2 已 byte-identical 基準對證，非本批造成）
- 實作細節之程式碼審查（標的是尚未實作的規格）
- 治理流程本身（gate／債帳／戳記機制）——本輪標的是量化規格

---

## 產出

canonical 四欄 findings（含對 R3 十八條之 CLOSED／OPEN）＋ **Verdict**。
**禁改碼、禁改 SPEC**（只產 review 檔）。
收尾只清你自己的 workdir（**勿動 `/private/tmp/claude-501/`**）。
