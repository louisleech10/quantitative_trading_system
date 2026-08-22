# GAP-3 UAT 缺口 SPEC — R5 十三條之**修法指定**輪（主委照抄實作）

brief-kind: consult

## 範本
**全文照做** `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1／§3：
findings 用 canonical ID `## <FAMILY>-R2-P<0-3>-<NN>`，每條含 `**斷言**`／`**碼證**`／`**來源摘要**` 三欄；
§0 挑戰本 brief 之前提；結尾給 **Verdict**。零 findings ⇒ `## <FAMILY>-R2-P3-00` sentinel（仍含三欄）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷／輸入檔**，非 gating 檔；勿 STAMP-BLOCK。

---

## 🔴 本輪與 review 輪不同：請你們**指定修法**，不是找問題

**使用者 2026-08-22 逐字裁定**：
> 「乾脆你直接問委員要怎麼修，然後照著做?」

**理由（量化事實，非推測）**：R5 的 13 條 findings 中，**5 條是主委 R4 修訂自行引入的**；
R4 的 19 條中亦有 3 條如此。兩輪自傷共 8 條，形態高度一致——
**「改了某處的權威定義，未同步所有複述它的位置」**。
`feedback_cross_reference_sync` 載此類錯已犯 8 次，R5 為第 9 次，
且發生在主委剛為前 8 次做完機械閘之後（該閘只驗 §D→§P，不驗 §P↔§V，正是 V-11 破口）。

⇒ 出錯的那一步是**「主委選擇怎麼修」**。本輪把該步交給你們：
**逐條給出可直接照抄的修法**，主委不自行發揮。

### 每條回覆之必填四欄（🔴 第 4 欄是本輪重點）
1. **改哪裡**：檔案路徑 ＋ 章節／Task 編號 ＋ 可唯一定位之錨點原文
2. **改成什麼**：可直接貼進 SPEC 的**成品文字**（不是「應該要…」之描述）
3. **怎麼驗**：該改動之驗收斷言與 mutation（改壞須紅）
4. 🔴 **必須同步哪些其他位置**：本改動一旦落地，SPEC 內**還有哪些地方複述或依賴同一定義**、
   各自要改成什麼。**這欄直接對症本輪之 8 條自傷**；若你判斷沒有其他同步點，請明寫「無」並說明何以確信。

**若三家給出互斥修法**：主委會在具體提案之間裁決並記錄理由，不會另創第四種。
**若你認為某條之正確處置是「不修、改為明文不做」**，也請照四欄寫出來（含為何不違反 §C0）。

---

## 審查標的（版本鎖定）

- 檔案：`docs/GAP3_EVENT_UX_SPEC.md`
- **sha256：`64a22dc689b18b180a72c41c8f232152e6c4739bd3a73a28bd40f55d222df228`**（1169 行）
- **開工第一件事**：`shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`；不符即停下並在第一條回報。
- R5 收斂檔：`handoffs/reconcile/20260822-gap3ux-x-review-r5/synth.md`（十一群集之逐條歸屬）
- R5 三家原文：`handoffs/20260822-gap3ux-x-review-r5-{codex,composer,grok}.md`

---

## 待指定修法之十一群集（群集 J 已由主委自行修好，不在本輪）

| 群集 | R5 findings | 待你們指定修法之問題 |
|---|---|---|
| **A** | COMPOSER-R5-P1-01、GROK-R5-P0-01 | V-11 仍寫 `contractAccepted`，與 Task 7.1／7.2 之 `selectable(path,dim)` 雙源（共三處）。**併請裁結構題**：§V 是否應由「複述斷言」改為「只引用 Task ID」？是否該加機械閘擋「§V 出現與 §P 重複之斷言字面」？此為本類錯之**根因修法**——請直接裁，不要交回主委決定 |
| **B** | CODEX-R5-P0-05 | §G S-1..S-8 未定義 dict→sha256 bytes 之完整 encoder（JSON separators／escaping／UTF-8／結尾 newline／特殊 float 之位元組形式）。請給可直接寫進 SPEC 之 encoder 規格 |
| **C** | GROK-R5-P1-01 | Task 7.5 之三組報酬表與 S-1「頂層八鍵不得增減」互斥。三種掛法（`strata.by_label`／三次呼叫外包／新頂層）擇一並說明為何；且須同時給 G-2 之更新規則 |
| **D** | GROK-R5-P1-02、CODEX-R5-P1-04 | `horizon_bars → ms` 之 timeframe 來源未定（事件列 tf／run 的 tf／批內多 TF 取 max／拒收），選 1h 或 12h 得相反結果。另 Task 7.7 目前不可執行（`/features/runs` 未把 manifest `time_range` 帶進 `RunInfo`） |
| **E** | COMPOSER-R5-P1-02 | Task 7.7 左界未扣 `decision_offset_bars`，`k > 0` 時有 fail-open 窗口 |
| **F** | CODEX-R5-P0-01 | 匯出仍固定取 `future_${horizon}bar_return`，與宣告之 `entry_price_semantic`／`decision_offset_bars`／`label_return_mode` 可不一致（觸及數值正確性，依 §C0 不得降殘留） |
| **G** | CODEX-R5-P0-02 | `counterexample_kind` 為逐列選填欄，卻被 Task 7.0／7.1 接成批次 scalar 選項；無 unset／混合列契約 |
| **H** | CODEX-R5-P0-03 | 路徑級限制只擋 A／B，放行 `two_stage`，但 `two_stage` 同樣無 producer／provenance。另 `source_file_digest` 排除 future 欄，rename／篩選後深度證據不足 |
| **I** | CODEX-R5-P1-06 | `mixed_control_kind_in_batch` 未登記任何契約 SoT（違反 §C／D-6）；`platform_same_trigger_rule` 在 Task 7.5 之全體組語意未定義 |
| **K** | CODEX-R5-P1-08 | §A 同時把 A-6 標為「請使用者於白話閘確認」與「待使用者確認：無」，兩者互斥。併問：此類「需使用者確認」項在 SPEC 中之正確標法 |

---

## 本 brief 前提

### fact-verified（每條可重跑；命令即查證方式）

fact-verified: 標的 SPEC 之 sha256 ＝ `64a22dc689b18b180a72c41c8f232152e6c4739bd3a73a28bd40f55d222df228`、1169 行
  → `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md; wc -l < docs/GAP3_EVENT_UX_SPEC.md`

fact-verified: R5 三家 findings 數 ＝ codex 8／composer 2／grok 3，Verdict 三家一致「需修訂後定版」
  → `for f in codex composer grok; do grep -c "^## [A-Z]*-R5-P" handoffs/20260822-gap3ux-x-review-r5-$f.md; done`
  ＋ `grep -h "^## Verdict" handoffs/20260822-gap3ux-x-review-r5-*.md`

fact-verified: R5 收斂檔之 completeness 與 cluster attribution 皆 rc=0；R5 委員債已銷帳
  → `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260822-gap3ux-x-review-r5/sources.lock --synth handoffs/reconcile/20260822-gap3ux-x-review-r5/synth.md`
  ＋ `bash scripts/debt_ledger.sh --has-open`（rc=0）

fact-verified: 本 brief 之 receipt 產生器已修 CODEX-R5-P1-07（未開 pipefail ⇒ 假 rc=0）：
  加 `set -o pipefail` 後立即暴露 F-11 指向不存在路徑（`momentum/Analysis/case_search_engine.py`，
  實為 `momentum/DataExtraction/case_search_engine.py`），修正後 **14 條真的全 rc=0**
  → `bash handoffs/20260822-gap3ux-x-review-r5-facts.sh`（rc=0）；
  留存輸出 `handoffs/20260822-gap3ux-x-review-r5-facts.out`，可 diff

fact-verified: 六維度分佈於契約之三個不同巢狀層級；`control_kind` enum 4 而 `accepted` 3
  → `python3 handoffs/20260822-gap3ux-x-review-r5-dims.py --counts`

fact-verified: `dedupe.py:113` 之 manifest `ctx_cols` ＝
  `("event_id","symbol","timeframe","label","scenario","direction")`，**無 `control_kind`**
  → `sed -n '105,118p' momentum/Analysis/event_samples/dedupe.py`

fact-verified: `event_forward_return_table`（`tables.py:88`）之 `event_split_plan` 必填，
  `:113` 直接 `.clusters.set_index(...)`；回傳頂層八鍵見 `:171-181`
  → `sed -n '88,120p;165,182p' momentum/Analysis/event_samples/tables.py`

fact-verified: `RunInfo`（`api/models/feature_factory_models.py:116-133`）無 `time_range`；
  `feature_reader.py:455` 之 manifest artifact 有 `time_range: {start, end}`，legacy run 為兩者皆 `None`
  → `sed -n '116,133p' api/models/feature_factory_models.py`；`sed -n '450,470p' momentum/FeatureEngineering/feature_reader.py`

### assumed（主委之未證假設；揭露用）

assumed: 十一群集之切分正確，無兩條 findings 被錯併或錯拆。
assumed: 群集 J（`facts.sh` pipefail）確實只是工具 bug，不影響任何 SPEC 判斷。
assumed: 「由委員指定修法、主委照抄」能降低自傷率——**本輪即該假設之實驗**。
assumed: R5 之 13 條已涵蓋 R4 修訂引入之全部缺口（可能仍有未被發現者）。

---

## 不受理範圍

- 純事件研究模式、#9b 規模防護本體、標籤方法論討論（皆使用者裁定另立）
- `tests/api` 既有紅 10 failed + 3 errors
- **G-7 scope 淨差之既有紅**：基準點凍結於 2026-08-07、至今 503 個 commit，
  被標檔案最後改動者為 8/18–8/21 之前幾個 session；修它等同為 503 個 commit 重宣告 scope manifest
  （使用者 2026-08-14 裁定治理不再擴建）
- 實作細節之程式碼審查（標的是尚未實作的規格）
- **本輪不受理「再找新問題」**：若你在指定修法時順帶發現新缺口，請單獨列為 P 級 finding，
  但**不得**取代四欄修法指定——本輪之交付物是修法，不是清單。

---

## 產出

十一群集之**逐條四欄修法指定** ＋ **Verdict**（本批修法是否足以進 R6 複審）。
**禁改碼、禁改 SPEC**（只產 consult 檔；修法由主委照抄實作）。
收尾只清你自己的 workdir（**勿動 `/private/tmp/claude-501/`**）。
