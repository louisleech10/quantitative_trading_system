# Reconcile — 20260822-gap3-b5-review-r3

**來源** 20260822-gap3-b5-review-r3-codex.md, 20260822-gap3-b5-review-r3-composer.md, 20260822-gap3-b5-review-r3-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置（主委 Claude 裁決；R2 三條 CLOSED＋一條 OPEN 續修、R3 新四條全修）

**Verdict**: 需修補後合併——CODEX-R2-P1-01／P1-02／P2-01 與 GROK-R2-P2-01 CLOSED；**CODEX-R2-P1-03 判 OPEN 成立**（我只擋掉錯誤用法、沒給可成功的驗證路徑），本輪補完；R3 新 4 條（2×P1、1×P2、含三家同抓之 plain_docs）全數採納。R4 由原提出方重跑閉合 → 三家 RECONCILE-STAMP → 交使用者 UAT。

**修後實測（receipt `handoffs/run_receipts/20260822T014000Z-gap3-b5-r3-fix-gate.log`；數字自 receipt 複製）**：`tests/api -k gap3_import` **15 passed**／rc=0；`tests/momentum/event_samples/` **230 passed**／rc=0；`feature_engineering`＋`strategy_validation` **289 passed**／rc=0；`npx vitest run gap3 pendingFeatures` 4 files／**22 passed**；`npm run build` rc=0。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| Z1 digest 驗證缺可用路徑（R2 OPEN 續修） | CODEX-R2-P1-03 | **採納（補完）**：檔案端點增選用 `source_file`（契約所指來源檔）；`verify_source_digest=true` 時以**該檔**位元組逐列對證，未附 ⇒ 400 `source_file_required_for_verify`（顯式引導，不讓使用者收一堆 mismatch）；`/search` 匯出同時下載 companion `*.source.json`（其 sha256 === `source_file_digest`），`source_file_text` 入回傳體。測試：兩檔齊 ⇒ 200＋`source_digest_verified=true`；缺 source_file ⇒ 400；來源檔竄改 ⇒ 422 `digest_mismatch` |
| Z2 我的回歸測試沒真的驗到（假綠） | CODEX-R3-P2-03 | **採納**：原測試定義 spy 卻未接上、只斷言 counts ⇒ 舊錯位可通過。改為 monkeypatch `_all_bars_for_events` 注入攔截器，**直接斷言** `scores[(sym, t₀−k)] == 1.0` 且 `scores[(sym, t₀)] == 0.0`、全表訊號數 == 3。此條是「防假綠」紀律的正面案例——committee 抓到我寫了個不會紅的測試 |
| Z3 匯出缺 horizon 欄未事前提示 | CODEX-R3-P1-02 | **採納**：`/search` 增答案窗選單（1–12 根）傳入匯出器；匯出前若 `n_missing_label_value > 0` 以 confirm 明示「N/M 筆缺 future_{h}bar_return ⇒ 條件 IC 會 unavailable」並可取消；匯出器回傳 `n_missing_label_value`。測試：組裝器計數＋頁面接線字面斷言 |
| Z4 plain_docs Gate 於 HEAD 紅（**第三次**） | CODEX-R3-P1-01, GROK-R3-P0-01, COMPOSER-R3-P2-01 | **採納**：看板隨本輪同 commit 更新（R2／R3 紀錄）。**根因是我的流程病**——修補 commit 只顧碼、把白話同步留到收尾；已改為固定動作：`git add` 後、`commit` 前先跑 `plain_docs_sync_check.sh --staged`，紅就一起 add（摩擦八十九） |
| Z5 R2 其餘閉合 | CODEX-R2-P1-01, CODEX-R2-P1-02, CODEX-R2-P2-01, GROK-R2-P2-01 | **CLOSED**（原提出方重跑：決策根訊號＋mixed-k 拒、label_value 取 future_Nbar_return、disclosure 不過量、計數敘事訂正） |

**主委自陳**：Z4 是同一批第三次犯同一條；Z2 是我交出「看起來有驗、實際不會紅」的測試——兩者都不是知識問題而是紀律問題，已各自機械化（commit 前跑 --staged；回歸測試必須斷言被監視的中間值而非只看結果 counts）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01
**斷言**: k>0 訊號改標 decision bar、mixed-k 拒收已 CLOSED。 **碼證**: `pipeline.py:122-166` 以 `vals[i-k]` 建 score；`test_pipeline.py -k decision_bar`→1 passed，n_signal_bars=3、k=2、mixed-k=batch_not_single_valued。 **來源摘要**: momentum/Analysis/event_samples/pipeline.py#db3d29667082；tests/momentum/event_samples/test_pipeline.py#fc12718ec299；CLOSED。
## CODEX-R2-P1-02
**斷言**: label_value 改取同 horizon future_Nbar_return、short 取負、缺欄不寫並記 skipped 已 CLOSED。 **碼證**: `eventExport.ts:81-120`；`npx vitest run gap3`→17 passed，覆蓋 h=2/h=4/short/缺欄。 **來源摘要**: frontend/src/lib/eventExport.ts#8966db1df2a1；CLOSED。
## CODEX-R2-P1-03
**斷言**: JSON verify 拒收已落地，但 `/search` export 仍沒有可成功走 verify 的檔案路徑，原 finding OPEN。 **碼證**: exporter `eventExport.ts:27-37,65-66,117-120` hash canonical source cases；file route `case.py:151-155` 傳整個 upload bytes；contract 要求檔內 `source_file_digest`（event_import_contract.json:5-10,50）；verify 測試只有 `test_gap3_import.py:207-220` mismatch，fresh verify→2 passed。 **來源摘要**: frontend/src/lib/eventExport.ts#8966db1df2a1；api/routes/case.py#03a4cf0c2baa；momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e；OPEN：需提供可驗證的 canonical/source bytes 對證設計。
## CODEX-R2-P2-01
**斷言**: all-bars estimand disclosure 已 CLOSED，未見過量內部欄位外洩。 **碼證**: `EventTablesPanel.tsx:106-123` 僅渲染 rule/note、horizon/threshold/direction/entry/k/eligibility、signal counts；`npx vitest run gap3`→17 passed。 **來源摘要**: frontend/src/components/ic-analysis/EventTablesPanel.tsx#5e3cffae61e9；CLOSED。
## CODEX-R3-P1-01
**斷言**: R2 修補後 B5 Gate 的 plain-docs 關卡實際為 rc1，receipt/brief 的 rc0 敘事與 HEAD 不一致，阻擋 stamp/UAT。 **碼證**: `bash scripts/plain_docs_sync_check.sh` stdout→`GAP-3施工進度.md` last update bcabb668 落後 watched 1c54049b，`rc=1`；腳本 `plain_docs_sync_check.sh:199-215` 對此返回 1。 **來源摘要**: scripts/plain_docs_sync_check.sh#1d127ae13f1a；白話說明/GAP-3施工進度.md#91cce3238294；[P1] confidence=10/10；同步看板後重跑同命令。
## CODEX-R3-P1-02
**斷言**: realtime `/search` 匯出未先提示缺 horizon 欄時，整批可無 label_value，使用者後續 conditional IC 只能 loud unavailable。 **碼證**: `search/page.tsx:520-524` 未傳 horizon/未檢查缺欄；`case_search_engine.py:1527-1532` realtime 保留尾端；`eventExport.ts:61,83-86` 預設 h=2 且缺欄省略；`ic_feed.py:44-46`→missing_label_value。 **來源摘要**: frontend/src/app/search/page.tsx#04ac28eca77b；frontend/src/lib/eventExport.ts#8966db1df2a；momentum/Analysis/event_samples/ic_feed.py#5710f3436654；[P1] confidence=9/10；匯出前統計缺欄並提示/阻擋或明選 horizon。
## CODEX-R3-P2-03
**斷言**: 新增 decision-root regression test 沒有驗 score 實際落在 t0-k，因 `spy` 未 monkeypatch 且 `captured` 只斷言非 None，舊錯位可通過。 **碼證**: `test_pipeline.py:101-110` 定義 spy 但直接呼叫 `p.analyze_tables`；`112-115` 只驗 counts/config，`captured` 未被使用；該測試 fresh→1 passed。 **來源摘要**: tests/momentum/event_samples/test_pipeline.py#fc12718ec299；[P2] confidence=10/10；patch evaluator 或直接斷言 decision-bar score=1、t0 score=0。
FAILURES_SEEN: `plain_docs_sync_check.sh` fresh rc1；R2 receipt 內記錄的 rc0 與目前 HEAD 不符；其餘本輪 Gate 命令通過。
SCOPE_CHANGES: none；未改產品碼、測試、data_cache、root HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: review-only；未修改輸出；標記 digest verify closure、label_value availability、plain-doc Gate 與 regression coverage。
HANDOFF_OUTPUT: handoffs/20260822-gap3-b5-review-r3-codex.md
HANDOFF_NOT_UPDATED: root HANDOFF.md 由 Claude 維護；本檔為本任務唯一產出。
STATUS: DONE
## COMPOSER-R3-P2-01

**斷言**: HEAD 上 `plain_docs_sync_check.sh` 實跑 **rc=1**——`白話說明/GAP-3施工進度.md` 最後提交 bcabb668（R1 看板），WATCHED 路徑已在 **1c54049b**（R2 五條修補）改動；與 brief／receipt fact-verified「plain_docs rc=0」不一致，stamp 前須 doc 同步。

**碼證**: `bash scripts/plain_docs_sync_check.sh` → rc=1，stdout「✗ 過期: 白話說明/GAP-3施工進度.md … WATCHED 最後改動 1c54049b，晚於本檔 bcabb668」；`git log -1 --oneline 白話說明/GAP-3施工進度.md` → bcabb668；`git log -1 --oneline momentum/Analysis/event_samples/pipeline.py` → 1c54049b。`RECHECK:` 更新看板 R2 修補摘要後重跑 plain_docs 須 rc=0。

**來源摘要**: handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log#c8f2a1b0e3d4；handoffs/20260822-gap3-b5-review-r3-brief.md#f9e8d7c6b5a4；scripts/plain_docs_sync_check.sh#1a2b3c4d5e6f

正文：[MINOR] 信心度=High。不影響產品行為或 pytest/vitest 子集；屬 Gate 完整性／敘事對帳（摩擦八十八同類）。修法：同 commit 或 stamp 前 commit 更新 `白話說明/GAP-3施工進度.md`（R2 修補＋計數 230／api 14）。Codex／Grok 對 R2 產品修補之 CLOSED 複核不受阻。

## GROK-R2-P2-01

**斷言**: （閉合）R3 敘事與 receipt／本輪重跑之 event_samples 計數已對齊為 **230 passed**；原「232 vs 229」漂移已消除。

**碼證**: brief L29「230 passed」；synth L12／Y5「現值 230」；receipt「230 passed」「rc_event_samples=0」；本輪 `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → **230 passed** rc=0。STATUS=**CLOSED**。

**來源摘要**: handoffs/20260822-gap3-b5-review-r3-brief.md#98c1218c7733；handoffs/reconcile/20260821-gap3-b5-review-r2/synth.md#eaec8254b879；handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log#3f37d9e7b733

正文：原提出方重跑閉合；不進本輪 OPEN 分母。

## GROK-R3-P0-01

**斷言**: R2 修補 commit `1c54049b` 變更了 `白話說明/GAP-3施工進度.md` 的 WATCHED（`momentum/Analysis/event_samples/`、`tests/momentum/event_samples/`），但該看板最後更新仍停在 `bcabb668`，故 HEAD 上 `bash scripts/plain_docs_sync_check.sh` **rc=1**；同時 R3 brief／修後 receipt／commit 訊息宣稱 plain_docs rc=0——B5 Gate 於 HEAD 未過，不可 stamp。

**碼證**: 本輪 `bash scripts/plain_docs_sync_check.sh` → stdout「過期: 白話說明/GAP-3施工進度.md」、WATCHED 最後改動 `1c54049b`、本檔最後更新 `bcabb668`、**rc=1**（直接取 rc，未經 pipe）。`git show --name-only 1c54049b` 含 `pipeline.py`／`test_pipeline.py`／`白話說明/…討論紀錄.md`，**不含** `GAP-3施工進度.md`。receipt L95–96 寫「全數同步」「rc_plain_docs=0」——該 receipt 與程式改動同 commit 打包，git-log 判準在 commit **之後**才變紅（commit 前未落地之 WATCHED 不入 last_w）。`RECHECK:` `bash scripts/plain_docs_sync_check.sh`；修法＝更新 `白話說明/GAP-3施工進度.md`（記載 R2 五條修補）並與其實作同 commit 或之後提交，使 last_f 不早於 last_w。

**來源摘要**: handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log#3f37d9e7b733；handoffs/20260822-gap3-b5-review-r3-brief.md#98c1218c7733；scripts/plain_docs_sync_check.sh#1d127ae13f1a；白話說明/GAP-3施工進度.md#91cce3238294

正文：[BLOCKING] 信心度=High。同型於 GROK-R1-P0-01（plain_docs Gate）；本次為 R2 修補引入之回歸，非舊帳重議。擋 stamp／UAT。不改產品行為碼；只補看板時序。

