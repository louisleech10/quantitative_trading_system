# Reconcile — 20260823-gap3ux-x-review-r8

**來源** 20260823-gap3ux-x-review-r8-codex.md, 20260823-gap3ux-x-review-r8-composer.md, 20260823-gap3ux-x-review-r8-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**輪次事實**：三家全員產出，Verdict 一致「需修訂後定版」。findings 17 條
（codex 6／composer 5／grok 6）。**首次補丁包模式**——三家共交 7 份補丁包
（`handoffs/patches/20260823-gap3ux-r8-*.md`），新流程之交付形態確立。

🔴 **使用者 2026-08-23 追加裁定：「就做到完整 Frozen，不用管輪次」**
⇒ R3 consult 所訂之「硬輪上限 ≤2 輪」**由使用者解除**；改以 FROZEN 四條件為唯一終點。
（該上限原意是防止無限迴圈，使用者評估後選擇以完成度為準。此為使用者權責，非放水。）

### 群集 A — 議題一成立：答案窗屬 IC 分析參數，不屬 `/search` 匯出（**三家一致**）
**ID**：GROK-R8-P0-01、COMPOSER-R8-P0-01
**使用者原話**：「條件 IC 本來就算一種類型的 IC-Analysis，條件給定應該就是要在 IC 分析的頁面，
而不是 `/search` 吧」。
**三家裁定＝成立**（composer「已獲碼證支持」；grok「現行 SPEC ⇒ **錯層**，且強迫為換 h
而重匯出未變之事件事實批」）。
碼證：`label`（0／1）來自 t0 之 `positive_case`、不看答案窗；`ic_feed.py` 之「v1 不重算」
為版本限制非能力限制；`pipeline.bars_from_kline_cache` 已是服務端取 bars 唯一入口。
**處置＝ACCEPT**：D-3(a)／Task 4.1／4.1b／V-6／§A 之「主答案窗在匯出層」須改為
「答案窗為 IC 分析參數」。補丁包：`-arch-shift.md`、`-arch-analyze-time-label.md`、
`-codex-analysis-label.md`。

### 群集 B — 🔴 purge／embargo 洩漏（**推翻主委之 assumed**；三家中兩家獨立命中）
**ID**：CODEX-R8-P0-02、GROK-R8-P0-02
**內容**：主委於 R8 brief 之 assumed 寫「`label_value` 改分析時計算後，PIT 正確性可由既有
`decision_time_rule`／`feature_cutoff_rule` 保證，**不需新機制**」——**被推翻**。
`event_split` 之 embargo 仍可能沿用匯出時烤入之舊 `label_end_ms − label_start_ms`
⇒ **IC 頁選較長答案窗時 purge 小於實際 label window ⇒ train/test 洩漏**，違反 §C0。
**處置＝ACCEPT，本群集為本輪最高優先**：分析時 h 一旦可變，
embargo 必須**由分析時之 h 重新導出**，且須有機械斷言（改大 h ⇒ purge 同步變大）。

### 群集 C — `decision_offset_bars > 0` 時 IC picker 之時間戳錯位
**ID**：CODEX-R8-P0-03
**內容**：IC picker 目前把 **t0** 當 feature timestamp，未映射到 `decision_at`／
`last_bar_open_ms` ⇒ `k > 0` 時特徵截止與事件 label 對不到同一決策時點。
**處置＝ACCEPT**（補丁包 `-codex-pit-wiring.md`）。

### 群集 D — Task 7.0b 落在錯誤生命週期，須 REOPEN 重寫
**ID**：GROK-R8-P1-01、COMPOSER-R8-P0-02
**內容**：R7 群集 E 才把 Task 7.0b 補成「`POST /api/v1/case/label-values`＋
匯出 `buildEventContractRecords` 只得經此取 `label_value`」；議題一成立後，
該 API 與呼叫點落在**匯出**生命週期 ⇒ 原單位可稱 CLOSED，
**架構上必須 REOPEN 並重寫為分析時路徑**（以 `bars_from_kline_cache`＋`align_events` 於分析時算）。
**處置＝ACCEPT**。

### 群集 E — Task 7.6 邊界與議題一直接衝突
**ID**：COMPOSER-R8-P1-03
**內容**：Task 7.6「邊界：**不允許**在 IC 頁修改批次設定」與議題一（答案窗應在 IC 頁給定）互斥；
只改 D-3 不改 7.6 ⇒ Agent 會在 IC 頁只做唯讀揭露而**無處設定** `horizon_bars`。
**處置＝ACCEPT**：須區分「批次**事實**欄（唯讀）」與「**分析參數**（可設定）」。

### 群集 F — A-6 不得默認作廢，須有取代裁定
**ID**：CODEX-R8-P1-04
**內容**：§A、Phase 4、V-6 仍把舊的「主答案窗在匯出層」當權威，
若議題一成立卻無新的使用者白話閘或取代裁定，A-6 會變成懸空。
**處置＝ACCEPT**：以**使用者 2026-08-23 之原話**（「條件給定應該就是要在 IC 分析的頁面」）
作為 A-6 之**取代裁定**入 §A，並註明其為使用者主動提出、三家碼證確認。
⇒ FROZEN 條件③（A-6 經使用者確認）**以此取代裁定滿足**。

---

## 🔴 主委自傷（本輪 6 條；新流程首次實測**未能防住**）

**誠實歸因**：本輪自傷**全部落在主委自建之工具與 receipt**，不在「補丁包指導下之 SPEC 編輯」
——因為主委在補丁包送達前就先把工具寫好了。⇒ 新流程之核心機制本輪**尚未被實測到**。

### 群集 G — `facts.sh` F-14 之 rc 假綠（**CLAUDE.md 已載之坑，主委再犯**）
**ID**：GROK-R8-P1-02、CODEX-R8-P1-05
**內容**：F-14 以 `cmd; echo count_audit=$?` 結尾 ⇒ `spec_count_audit` 回 2 時
`emit` 取到的是 `echo` 的 rc（0）⇒ `rc_all=0`，「五閘皆 rc=0」之 fact **總碼假綠**。
與 CLAUDE.md 之「`cmd | head` 讀到的是 head 的 rc；**rc 一律直接取**」同型。
**處置＝ACCEPT，主委直接修**（補丁包 `-gate-receipt.md`／`-harness-f14-prereview.md`）。

### 群集 H — `gap3ux_pre_review.sh` 指向過期 facts（**「加閘未同步清單」第三次**）
**ID**：COMPOSER-R8-P1-01、GROK-R8-P1-03
**內容**：`FACTS` 硬編碼 `…-r7-facts.sh`，而本輪已是 `…-r8-facts.sh`
⇒ 計數稽核閘掃 stale receipt。**主委上一輪才為此病做了「唯一入口」，結果入口自己指向過期檔。**
**處置＝ACCEPT，主委直接修**：改為**不寫死輪次**（掃 `handoffs/*-facts.sh` 之最新者或由參數傳入）。

### 群集 I — 閘數用語在三份文件互斥
**ID**：COMPOSER-R8-P1-02、GROK-R8-P2-01
**內容**：角色卡「五閘（含 locus）」／brief「六閘／六支」／HANDOFF「六支」又「五支＋locus」
⇒ Agent 與主委可各取一字面更新而再犯計數漂移；R8 facts 之 F-14 標題亦仍寫「五支」。
**處置＝ACCEPT，主委直接修**：閘之**權威清單唯一在 `gap3ux_pre_review.sh`**，
其餘文件一律**不寫數字**、改為「見該檔」。

### 群集 J — `patch_locus_check.py` 比主委宣稱的弱
**ID**：CODEX-R8-P1-06
**內容**：該閘只以 **dirty worktree 之檔名集合**判定 locus，**不檢查 anchor 或 diff hunk**
⇒ 同檔之無關修改、或既有 dirty 檔，即可被誤算為「補丁已套用」。
**處置＝ACCEPT，主委直接修**（補丁包 `-codex-gate-locus.md`）：
須驗到 **anchor 層級**（該 locus 所指之錨點確實出現在 diff hunk 內）。
⚠️ 主委在 HANDOFF／角色卡曾以「diff 觸及集合 ⊇ SYNC-LOCI」描述其強度，
**該描述高於實際能力**，須一併訂正。

---

### 未採納 / 降級
無。17 條全數 ACCEPT，0 條 REJECT、0 條降為具名殘留（§C0 條文 2）。

### 自傷絕對數趨勢（依 GROK-R3-P2-01 之裁定，並列絕對數）
R4 **3** → R5 **5** → R6 **6** → R7 **7** → R8 **6**。**尚未下降。**
本輪之 6 條全在工具／receipt 層，新流程之核心（補丁包指導 SPEC 編輯）本輪未被實測。

Verdict：需修補後合併（17 條全數 ACCEPT；議題一成立且為 A-6 之取代裁定；
群集 B 之 purge 洩漏為最高優先；主委 6 條工具自傷直接修。
使用者已解除輪次上限 ⇒ 續派至 FROZEN 四條件全滿足）

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R8-P0-01

**斷言**: 把答案窗移出 `/search` 後，現行契約與 IC 分析呼叫鏈沒有分析時計算 `label_value` 的端到端 producer；新批次會落入 `missing_label_value`，而不是在 IC 頁依條件／答案窗重算。

**碼證**: `frontend/src/lib/eventExport.ts:81-105` 仍在匯出時讀 `future_${horizon}bar_return` 並寫 `label_value`；`EventImportPicker.tsx:45-52` 只回傳 import ID＋t0 timestamps；`useICAnalysis.ts:269-287` 只送 `event_timestamps`；`api/services/ic_analysis_service.py:229-238` 只傳 `event_timestamps`，`rg -n 'build_event_ic_inputs' api/services api/routes` 無 service caller；`ic_feed.py:44-46` 對缺值直接回 `unavailable:missing_label_value`；`import_contract.py:152-168` 仍要求 `label_definition.window.horizon_bars`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5; frontend/src/lib/eventExport.ts#b2024ac8970f; frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456; frontend/src/hooks/useICAnalysis.ts#e05507ee38ed; api/services/ic_analysis_service.py#c3459aa2e6a6; momentum/Analysis/event_samples/ic_feed.py#5710f3436654; momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e

[BLOCKING] 信心度=High。R8 的方向不是被碼證推翻，而是尚未成為閉合架構：IC 頁現有 `horizons` 是報告 horizon 集合，`event_query` 也只是 feature filter，不是 label condition。須明訂事件事實層、分析 label spec、批次契約版本／legacy 行為、IC request/response、後端 bars producer、`ic_feed` 呼叫點與 provenance；不得只把 Task 7.0b 的 `/search` cases API 改名。

## CODEX-R8-P0-02

**斷言**: 即使新增分析時計算 label，現行 IC split/purge 仍在事件 label 注入前依 labels/default horizon 建立；IC 頁選較長答案窗時可能 purge 小於實際 label window，違反 §C0 的 leakage gate。

**碼證**: `api/models/ic_models.py:133-165` 沒有 analysis-time label/horizon 欄位；`ic_filter_orchestrator.py:920-949` 先以 `_resolve_effective_label_horizon(config, labels_df)` 建 holdout split；`ic_filter_orchestrator.py:2728-2774` 無 labels 時從 config default 產生 `return_{horizon}`；`ic_filter_orchestrator.py:360-378` 以該 horizon 建 purge；`EventAnalyzeRequest.horizons` (`api/models/event_import_models.py:83-91`) 只控制事件報酬表，不是 IC label window。RECHECK：上述 `nl -ba` 命令可重跑。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5; api/models/ic_models.py#fbc974fb7fa4; api/models/event_import_models.py#919507b8ad19; momentum/Analysis/ic_filter_orchestrator.py#935fb860c6b1; momentum/Analysis/event_samples/pipeline.py#db3d29667082

[BLOCKING] 信心度=High。h=7 若仍依 labels/default h=1 或 h=5 建 split，train 尾端答案窗可跨入 test；這是數值正確性缺口，不可列殘留。修法須讓本次 `event_label_spec.horizon_bars` 在 split 建立前成為唯一 purge 下界，並以 h=1/7、尾端不足、真實 kline golden＋mutation 驗證「改 h 但不改 purge」必紅。

## CODEX-R8-P0-03

**斷言**: `decision_offset_bars > 0` 時，IC picker 目前把 t0 當成 feature timestamp，沒有映射到 `decision_at`／`last_bar_open_ms`；因此特徵截止與事件 label 對不到同一決策時點。

**碼證**: `frontend/src/lib/api.ts:1042-1048` 的 `eventT0MsToIcTimestamps` 直接取每列 `t0/1000`；`EventImportPicker.tsx:51-52` 將該結果送給 `onPick`；`ic_feed.py:51-58` 的合法事件 label map key 卻來自 receipt `last_bar_open_ms`；`ic_filter_orchestrator.py:2895-2904` 以 feature index 的 epoch ms 查該 map；SPEC Task 7.7 雖要求 `max_close_ms <= decision_at`，Task 7.6 只要求揭露五維度，沒有這條實際 picker→analyze wiring。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5; frontend/src/lib/api.ts#a70a519560b7; frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456; momentum/Analysis/event_samples/ic_feed.py#5710f3436654; momentum/Analysis/ic_filter_orchestrator.py#935fb860c6b1

[BLOCKING] 信心度=High。Task 7.2 明確允許輸入非零 k，不能以目前 default 0 當作安全假設。修法須由後端 receipt 產生 per-event decision timestamp／feature row mapping，前端不可自行由 t0 推導；k=3、混 TF、重複 feature row 與未知 TF 均需 fail-closed receipt。

## CODEX-R8-P1-04

**斷言**: A-6 不能因議題一而默認作廢；現行 §A、Phase 4、V-6 仍把舊的「主答案窗在匯出層」當權威，卻沒有新的使用者白話閘或取代裁定。

**碼證**: SPEC `:241-258` 將 A-6 定義為附帶 horizon 不改 `label_value` 且確認前不得 FROZEN；`:841-850` 的 Task 4.1 驗收 `window.horizon_bars==4` 且 `label_value==future_4bar_return`；`:1541` 的 V-6 重述同一行為。R8 brief 要求回答 A-6 是否作廢，但沒有 user-visible confirmation receipt。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5

[MAJOR] 信心度=High。正確處置是「舊 A-6（D-3(a)）作廢，新增 A-6′：分析時計算之答案窗／label_value，仍待使用者白話確認」，並同步 §A、檔頭 FROZEN 句、D-3/D-7、Task 4.1/4.1b/4.1c、Task 7.0b/7.4/7.6、V-6 與白話勾選表；未確認前不能宣稱架構已接受。

## CODEX-R8-P1-05

**斷言**: R8 facts receipt 與派審前入口目前能把失敗機械閘報成成功：F-14 用最後一個 `echo` 蓋掉 count-audit rc，且 `gap3ux_pre_review.sh` 仍掃 R7 facts，不掃 R8 facts。

**碼證**: `python3 scripts/spec_count_audit.py --check docs/GAP3_EVENT_UX_SPEC.md handoffs/20260823-gap3ux-x-review-r8-facts.sh --baseline handoffs/run_receipts/gap3ux-spec-count-baseline.txt` → `COUNT_DIRECT_RC=2`（R8 字面未進 baseline）；`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh` → F-14 `count_audit=2` 但 `FACTS_WRAPPER_RC=0`；`bash scripts/gap3ux_pre_review.sh` → `PRE_REVIEW_RC=0`；`scripts/gap3ux_pre_review.sh:20` 仍為 `FACTS=...review-r7-facts.sh`。

**來源摘要**: handoffs/20260823-gap3ux-x-review-r8-facts.sh#a3d9fdfb26af; scripts/gap3ux_pre_review.sh#e489b7908fdb; scripts/spec_count_audit.py#27b09e0ffb52; handoffs/run_receipts/gap3ux-spec-count-baseline.txt#4fa233d48b9a

[MAJOR] 信心度=High。這直接使 brief 的「fact 全可重跑」與 FROZEN 六閘條件不可信。修法：F-14 以 fail-propagating compound command 執行五閘、pre-review 改用 R8 facts、重產 baseline，再以直接命令和 wrapper rc 同時驗證；不得只看最後 echo。

## CODEX-R8-P1-06

**斷言**: `patch_locus_check.py` 的實作只以 dirty worktree 的檔名集合判定 locus，且沒有檢查 anchor 或 diff hunk；同檔無關修改／既有 dirty 檔即可被誤算為補丁已套用。

**碼證**: `scripts/patch_locus_check.py:87-111` 以 `git diff --name-only` 加 `git status --porcelain -uall` 建 `changed_files`；`:144-155` 只檢查 `f in touched`，讀到的 `anchor` 未參與判定。當前 `git status --porcelain -uall` 已有既存 `.claude/gate/audit.log`、`.probe_ic*.sh` 與 receipt 檔，證明工作樹並非本補丁專屬。

**來源摘要**: scripts/patch_locus_check.py#010a10e9e16d; docs/GAP3_EVENT_UX_ROLE_CARD.md#（角色卡文件未變更；其誠實邊界與本碼證對照）

[MAJOR] 信心度=High。這會錯誤歸責「已列 locus 而主委未改齊」與「補丁已套用」，正好繞過 R3 新流程的目的。修法須以指定 base/snapshot 的實際 diff hunk 驗 anchor，並加同檔無關行、既存 dirty 檔、缺 anchor 三個反測；檔名集合只能作輔助，不得作通過條件。

### R7 十二條修訂複審

R7 群集 A、B、C、D、F、G：CLOSED（現行 SPEC 已含五閘 receipt、§F-2 純引用、Task 7.7 epoch 秒格式、`control_kind`、registry 內容正確性、§G S-9 浮點/跨環境 digest）；群集 E：R7 原 finding 的 `/case/label-values` API 形狀已補入 SPEC，**但在 R8 新架構下重新 OPEN 為 IC service wiring 缺口**，已由 P0-01 覆蓋。未把 R7 已修正文字重複計為 finding。

### 全棧三欄與必查類別

後端 code：P0-01/P0-02；前端 UI：P0-01/P1-04；wiring：P0-01/P0-03。矛盾/漏項/不可測：P0-01、P1-04；quant/PIT/leakage：P0-02/P0-03；API/型別/相容：P0-01；測試 golden：P0-02/P0-03；cache/OOM/過度工程/必要性短命工：本輪無新增 finding。C0 已讀且未主張放寬；但新架構的分析 label golden 尚未存在，不能以既有事件 G-2 代替。

### 被當成事實的未驗證假設（§0）

- 「把答案窗移到 IC 頁後，既有 `decision_time_rule`／`feature_cutoff_rule` 自動足以保證 PIT」：未驗證；split horizon 與 decision timestamp wiring 尚未接通。
- 「A-6 隨架構調整自然作廢」：未經使用者白話確認；只能提出 A-6′ 取代裁定。
- 「R8 六閘已全綠」：被直接 count-audit rc=2 與 F-14 wrapper 假綠反駁。
- 「patch locus 已由檔名集合充分封閉」：與腳本未使用 anchor/diff hunk 的實作不符。

ASSUMPTIONS_VERIFIED: 標的 sha256=01cf2468573ff5、1580 行；R8 facts 14 條命令輸出可重跑但 F-14 compound masks count-audit；IC service/前端/`ic_feed` 呼叫鏈以 `rg`/`nl` 逐項核對；R7 A-G 修訂文字逐項抽驗。
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md; wc -l docs/GAP3_EVENT_UX_SPEC.md` → sha/1580；`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh` → wrapper rc=0 但 F-14 count_audit=2；直接 `spec_count_audit.py --check ...r8-facts.sh` → rc=2；`bash scripts/gap3ux_pre_review.sh` → rc=0；未修改 code/SPEC，未跑完整 pytest。
FAILURES_SEEN: R8 F-14 direct count-audit rc=2 被 facts wrapper 遮蔽；此為 finding，未自行修改。
SCOPE_CHANGES: none；只新增本輪 review 與補丁包，未改 code、SPEC、data_cache、根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值/schema；指出分析 label producer、purge、timestamp mapping 與契約分層之待修影響。
HANDOFF_OUTPUT: handoffs/20260823-gap3ux-x-review-r8-codex.md
PATCH_OUTPUTS: handoffs/patches/20260823-gap3ux-r8-codex-analysis-label.md; handoffs/patches/20260823-gap3ux-r8-codex-pit-wiring.md; handoffs/patches/20260823-gap3ux-r8-codex-gate-locus.md
STATUS: DONE
## COMPOSER-R8-P0-01

**斷言**: 使用者 2026-08-23 架構調整（答案窗屬 IC 分析、非 `/search` 匯出）已獲碼證支持，但 SPEC 仍採 D-3(a) 並在 Task 4.1／V-6／A-6 綁定「主答案窗」與匯出時 `label_value`／`horizon_bars`，與已裁定方向互斥。

**碼證**: `nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '113,119p'` → D-3 仍寫「仍綁單一主答案窗」；`nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '841,850p'` → Task 4.1 驗收仍要求 `window.horizon_bars == 4`；`nl -ba frontend/src/app/search/page.tsx | sed -n '53,54,526,1568'` → `/search` 仍有 `eventHorizonBars`；brief 議題一碼證 `sed -n '75,85p' frontend/src/lib/eventExport.ts` → `label` 來自 `positive_case`、`label_value` 來自 `future_{h}bar_return`。RECHECK：套用 `handoffs/patches/20260823-gap3ux-r8-arch-shift.md` 後 `rg '主答案窗' docs/GAP3_EVENT_UX_SPEC.md` 僅剩歷史註記。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f; frontend/src/app/search/page.tsx#01cf2468573f

[BLOCKING] 信心度=High。Agent 依現行 SPEC 實作會固化錯誤層次（匯出時烤答案窗），使用者比較 horizon 仍須重匯出，與使用者裁定及 §C0 相悖。修法：採補丁包 D-3(d) 改寫 §A A-6、Task 4.x、V-6；移除 `/search` 主答案窗 UI。

---

## COMPOSER-R8-P0-02

**斷言**: Task 7.0b 之 `POST /api/v1/case/label-values` 仍設計為 `/search` 匯出時由 `cases` 列讀 `future_{horizon}bar_return` 產生 `label_value`；若議題一成立，producer 須改為 IC 分析路徑、以 `bars_from_kline_cache`＋`align_events` 於分析時計算，並補 §G 分析時 golden，否則 R7 群集 E 之修復在錯誤層次閉合。

**碼證**: Task 7.0b L1162-1163「在矩陣內 ⇒ `label_value` 取 `future_{horizon_bars}bar_return`」；L1167-1169 端點 `POST /api/v1/case/label-values`、request 含 `cases`（`/search` 結果列）；`momentum/Analysis/event_samples/ic_feed.py:4-5` 載明 v1 不重算為版本限制；`pipeline.py:78-82` `bars_from_kline_cache` 為服務端唯一入口；`alignment.py:154-168` 已可由 `horizon_bars`＋bars 推導 `label_end_ms`。RECHECK：改寫後 `rg 'future_\\{horizon_bars\\}bar_return' docs/GAP3_EVENT_UX_SPEC.md` 於 Task 7.0b 區段為 0。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f; momentum/Analysis/event_samples/pipeline.py#01cf2468573f

[BLOCKING] 信心度=High。主委若套用 R7 版 7.0b 而不隨架構調整，會把錯誤 producer 焊死在匯出 API，IC 頁仍無法「同批事件改 horizon 重跑」。修法：見 arch-shift 補丁（IC 端點、`buildEventContractRecords` 不寫 `label_value`、§G 分析時 golden）。

---

## COMPOSER-R8-P1-01

**斷言**: `scripts/gap3ux_pre_review.sh` 之 `FACTS` 仍指向 `handoffs/20260823-gap3ux-x-review-r7-facts.sh`，而 R8 brief／facts 已為 `…-r8-facts.sh` ⇒ 計數稽核閘掃描 stale receipt，與 R6/R7「加閘未同步清單」同型整合自傷。

**碼證**: `grep '^FACTS=' scripts/gap3ux_pre_review.sh` → `FACTS=handoffs/20260823-gap3ux-x-review-r7-facts.sh`；`ls handoffs/20260823-gap3ux-x-review-r8-facts.sh` 存在；`grep r7-facts scripts/narrow_check_router.sh` → 仍引用 r7。RECHECK：套用 gate-receipt 補丁後兩處皆為 r8。

**來源摘要**: scripts/gap3ux_pre_review.sh#01cf2468573f; handoffs/20260823-gap3ux-x-review-r8-facts.sh#01cf2468573f

[MAJOR] 信心度=High。不直接改壞 SPEC，但派審前閘可能漏掃 R8 facts 內新增字面，下一輪 fact-verified 不可信。修法：`handoffs/patches/20260823-gap3ux-r8-gate-receipt.md`。

---

## COMPOSER-R8-P1-02

**斷言**: brief fact-verified 宣稱「六支機械閘」（含 `patch_locus_check`），但 R8 `facts.sh` F-14 標題仍寫「五支」且只跑四支獨立腳本＋count_audit，未以 `gap3ux_pre_review.sh` 為唯一入口 ⇒ 與角色卡／brief 閘數敘述漂移（R7 群集 A 同型再現）。

**碼證**: brief L151「六支機械閘」；`handoffs/20260823-gap3ux-x-review-r8-facts.sh` L75 標「五支」；F-14 命令無 `gap3ux_pre_review.sh`、無 `patch_locus_check`；`bash scripts/gap3ux_pre_review.sh` 無參數時跳過 locus（預期行為，但 brief「六支」易誤讀為預設即六）。RECHECK：F-14 改跑 `gap3ux_pre_review.sh` 並更新標題為「五閘＋可選 locus」。

**來源摘要**: handoffs/20260823-gap3ux-x-review-r8-brief.md#01cf2468573f; handoffs/20260823-gap3ux-x-review-r8-facts.sh#01cf2468573f

[MAJOR] 信心度=High。違反「fact 全可重跑」之閘清單一致性；委員只信 F-14 會誤判 locus 閘狀態。修法：gate-receipt 補丁。

---

## COMPOSER-R8-P1-03

**斷言**: Task 7.6 邊界寫「不允許在 IC 頁修改批次設定」，與議題一裁定（答案窗為 IC 分析參數、應在 IC 頁給定）直接衝突；若只改 D-3 不改 7.6，Agent 會在 IC 頁只做唯讀揭露而無處設定 `horizon_bars`。

**碼證**: Task 7.6 L1416-1417「**不允許**在 IC 頁修改批次設定」；brief 議題一要求答案窗改由 IC 分析頁給定。RECHECK：7.6 邊界改為「五維度契約唯讀；分析參數（horizon 等）可於 IC 頁設定、不寫回匯出檔」。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f

[MAJOR] 信心度=High。架構調整後 IC 頁必須有分析參數 UI；現行禁令會阻擋合法實作路徑。修法：併入 arch-shift 補丁 Task 7.6 邊界段。

---

## GROK-R8-P0-01

**斷言**: 條件 IC 之答案窗／`label_value` 應於 IC 分析頁分析時給定與計算；現行 SPEC 以 D-3(a)／A-6／Task 4.1／7.0b 把「主答案窗烤進 `/search` 匯出」定為條件 IC 權威 ⇒ 錯層，且強迫為換 h 而重匯出未變事件事實批。

**碼證**: `sed -n '75,85p' frontend/src/lib/eventExport.ts` → `label`←`positive_case`，`label_value`←`future_${horizon}bar_return`。`sed -n '1,6p' momentum/Analysis/event_samples/ic_feed.py` →「v1 不重算」。`sed -n '76,82p' momentum/Analysis/event_samples/pipeline.py` → `bars_from_kline_cache` 唯一入口。SPEC：`sed -n '113,119p;241,258p;841,850p;1150,1178p' docs/GAP3_EVENT_UX_SPEC.md`（D-3(a)／A-6／4.1／7.0b 匯出 API）。RECHECK：重跑上列；確認無「條件 IC 必須在 search 選窗」之碼證反例。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f；frontend/src/lib/eventExport.ts；momentum/Analysis/event_samples/ic_feed.py

[BLOCKING] 信心度=High。修法＝套用 `handoffs/patches/20260823-gap3ux-r8-arch-analyze-time-label.md`；A-6→A-6′ 白話閘。

---

## GROK-R8-P0-02

**斷言**: 若採分析時 `label_value`／h，卻假設「既有 `decision_time_rule`／`feature_cutoff_rule` 已足夠、不需新機制」，則 `event_split` 仍可能用匯出烤入之舊 `label_end_ms−label_start_ms` 當 embargo ⇒ 分析改大 h 時 purge 偏小，構成 train/test 洩漏（§C0）。

**碼證**: `sed -n '58,61p' momentum/Analysis/event_samples/event_split.py` → `embargo = … int(window.max())` 且 `embargo < window.max()` raise；window 來自事件列之 label 窗。`ic_feed.py:75-77` 特徵截止與 `label_window_rule` 分開。brief assumed L169-170。RECHECK：設想同批匯出 `horizon_bars=3`、IC 頁選 h=7 且不重算 label_*_ms——對照 split 公式。

**來源摘要**: momentum/Analysis/event_samples/event_split.py；handoffs/20260823-gap3ux-x-review-r8-brief.md；docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f

[BLOCKING] 信心度=High。修法＝同架構補丁之 D-7「分析時窗」＋ golden／mutation（改 h 不重算 embargo ⇒ 紅）。

---

## GROK-R8-P1-01

**斷言**: R7 群集 E 已把 Task 7.0b 補成「`POST /api/v1/case/label-values`＋匯出 `buildEventContractRecords` 只得經此取 `label_value`」；在議題一成立後，該 API／呼叫點落在**錯誤生命週期（匯出）**——原單位可稱 CLOSED，架構上必須 REOPEN 並重寫為分析時路徑，否則 Agent 會把錯層實作到 Frozen。

**碼證**: `sed -n '1164,1194p' docs/GAP3_EVENT_UX_SPEC.md`（端點＋前端呼叫點）。對照 P0-01 碼證。RECHECK：grep Task 7.0b 是否仍要求 search 匯出呼叫 label-values。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f

[MAJOR] 信心度=High。修法＝架構補丁 §5（7.0b′）；禁止先實作匯出 API 再搬（白工）。

---

## GROK-R8-P1-02

**斷言**: `handoffs/20260823-gap3ux-x-review-r8-facts.sh` F-14 以 `cmd; echo count_audit=$?` 結尾，使 `spec_count_audit` 回傳 2 時 emit 仍見 **rc=0**，進而 `rc_all=0`——「五閘皆 rc=0」之 fact 總碼假綠（與 CLAUDE.md「`$?` 經 pipe／尾命令」同型）。

**碼證**: `sed -n '75,79p' handoffs/20260823-gap3ux-x-review-r8-facts.sh`。實跑：`python3 scripts/spec_count_audit.py --check docs/GAP3_EVENT_UX_SPEC.md --baseline handoffs/run_receipts/gap3ux-spec-count-baseline.txt` ⇒ rc=2（消失 r7-facts「五支機械閘」）；同命令經 `; echo count_audit=$?` 之 compound ⇒ **rc=0**。本輪 `facts.sh` 輸出含 `count_audit=2` 且 `rc_all=0`。RECHECK：重跑上列兩命令。

**來源摘要**: handoffs/20260823-gap3ux-x-review-r8-facts.sh#a3d9fdfb26af；handoffs/run_receipts/gap3ux-spec-count-baseline.txt

[MAJOR] 信心度=High。修法＝`handoffs/patches/20260823-gap3ux-r8-harness-f14-prereview.md` §1。

---

## GROK-R8-P1-03

**斷言**: `scripts/gap3ux_pre_review.sh` 硬編碼 `FACTS=handoffs/20260823-gap3ux-x-review-r7-facts.sh`，而本輪 brief／可重跑 receipt 已是 `…r8-facts.sh`；count-audit 對 SPEC＋r8-facts 與現行 baseline 配對 ⇒ rc=2，但 pre_review 因仍掃 r7 而顯示全綠——「唯一閘清單」與本輪 fact 腳本脫節（同型 R6/R7「加閘未進清單」）。

**碼證**: `sed -n '19,44p' scripts/gap3ux_pre_review.sh` → FACTS=r7。`python3 scripts/spec_count_audit.py --check docs/GAP3_EVENT_UX_SPEC.md handoffs/20260823-gap3ux-x-review-r8-facts.sh --baseline handoffs/run_receipts/gap3ux-spec-count-baseline.txt` ⇒ rc=2（＋r8／−r7 字面）。`bash scripts/gap3ux_pre_review.sh` ⇒ rc=0。RECHECK：同上。

**來源摘要**: scripts/gap3ux_pre_review.sh#e489b7908fdb；handoffs/20260823-gap3ux-x-review-r8-facts.sh#a3d9fdfb26af

[MAJOR] 信心度=High。修法＝harness 補丁 §2–3（改 FACTS＋重產 baseline）。

---

## GROK-R8-P2-01

**斷言**: 閘數權威用語在 ROLE_CARD「五閘（含 locus）」、brief「六閘／六支」、HANDOFF「六支」又「五支＋locus」之間互斥，Agent／主委可各取一字面更新 F-14／角色卡而再犯計數漂移。

**碼證**: `grep -n '五閘\|六閘\|五支\|六支' docs/GAP3_EVENT_UX_ROLE_CARD.md handoffs/20260823-gap3ux-x-review-r8-brief.md HANDOFF.md`。RECHECK：同一 grep。

**來源摘要**: docs/GAP3_EVENT_UX_ROLE_CARD.md；handoffs/20260823-gap3ux-x-review-r8-brief.md

[MINOR] 信心度=High。修法＝harness 補丁 §4：常駐五支＋有補丁時 locus＝最多六；禁「五閘（含 locus）」。

---

