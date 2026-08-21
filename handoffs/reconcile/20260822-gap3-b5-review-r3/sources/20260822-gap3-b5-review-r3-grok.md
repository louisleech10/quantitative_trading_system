# GAP-3 B5 review R3 — grok（閉合輪）

task-id: 20260822-GAP3-B5-REVIEW-R3
family: grok
brief-kind: review
brief: handoffs/20260822-gap3-b5-review-r3-brief.md
R2 修補 diff: `git diff c062dcda..HEAD`
R2 收斂: handoffs/reconcile/20260821-gap3-b5-review-r2/synth.md
修後 receipt: handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log

## Verdict：需修補後再 stamp／交使用者 UAT（本家 R2 1/1 CLOSED；CODEX R2 四條複核同意 CLOSED；本輪新 1×P0＝plain_docs Gate 於 HEAD 紅）

### 必答

1. **己方 R2／他家 R2：CLOSED／OPEN（附重跑）**  
   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | GROK-R2-P2-01 | **CLOSED** | R3 brief／R2 synth／receipt 三者皆寫 event_samples **230**；本輪 `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → **230 passed** rc=0。計數敘事已與 receipt 對齊（摩擦八十八）。 |
   | CODEX-R2-P1-01 | **複核同意 CLOSED** | `pipeline._all_bars_for_events`：訊號標決策根 `vals[i-k]=1`；混合 k ⇒ `not_computed:batch_not_single_valued`；`signal_mapping.indexed_at=decision_bar_open_ms`。`pytest …/test_pipeline.py -q -k decision_bar` → **1 passed**。 |
   | CODEX-R2-P1-02 | **複核同意 CLOSED** | `eventExport.ts` 取 `future_{horizon}bar_return`、short 取負、缺欄不寫＋`skipped`；回傳 `label_value_source`。vitest `gap3_event_import_form` 斷言 h=2→0.031／h=4→0.077／short 負／缺欄 skipped → **passed**（合跑 gap3+pendingFeatures **21 passed**）。 |
   | CODEX-R2-P1-03 | **複核同意 CLOSED** | JSON 端點 `verify_source_digest=true` ⇒ 400 `verify_unsupported_on_json_endpoint`；檔案端點 description 明限。`pytest tests/api -q -k "gap3_import and verify"` → **2 passed**；全 `-k gap3_import` → **14 passed**。 |
   | CODEX-R2-P2-01 | **複核同意 CLOSED** | `EventTablesPanel` disclosure 渲染 rule／estimand_note／label_threshold_note／manifest／signal_mapping；vitest `event-allbars-disclosure` 逐項斷言 → **passed**。 |

2. **修補是否引入新問題（brief Q2 四點）？**  
   - ①**訊號標決策根 × `entry_price_semantic=trigger_open`**：`evaluate_all_bars` 以觸發根 i 取 `scores[ot[i-k]]`、entry=`open_[i]`（trigger_open）。pipeline 把 score=1 寫在決策根索引 ⇒ 於觸發根求值時命中訊號、進場仍為觸發根 open。語意自洽（決策在 t₀−k 已知、進場在 t₀ open）；與 D1-6 五值不變。**不開 finding**。  
   - ②**`label_value` 缺 horizon 欄**：不寫欄＋`skipped`＋條件 IC loud unavailable；JSON 含 `note`／`label_value_source`。`/search` 匯出 UI 未 toast skipped 數（只下載檔）——屬可讀性，消費端仍 loud；assumed「優於寫錯值」攻擊不推翻。**不開 P0/P1**（UI 前提示可作後續 UX，非本輪語意回歸）。  
   - ③**JSON 拒 verify**：契約 `source_file_digest`＝來源檔 sha256；JSON body ≠ 來源檔 ⇒ 顯式 400 正確。檔案端點仍可用；export `verify_note` 已提示勿開。使用者有來源檔 ⇒ 走檔案端點。**不開 finding**。  
   - ④**disclosure 欄位**：揭露 rule／estimand／threshold／manifest 摘要／訊號對映計數——皆為 estimand 可讀性所需，非內部秘密。**不開 finding**。  
   - **本輪新 finding**：R2 修補 commit `1c54049b` 動了 WATCHED（`event_samples/`＋測試）卻未更新 `白話說明/GAP-3施工進度.md` ⇒ HEAD `plain_docs_sync_check` **rc=1**，而 brief／receipt／commit 訊息宣稱 rc=0 → **GROK-R3-P0-01**。

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**  
   **不可**——本輪實測：`tests/api -k gap3_import` **14 passed**；`event_samples/` **230 passed**；vitest gap3+pendingFeatures **21 passed**；`plain_docs_sync_check` **rc=1**（GROK-R3-P0-01）。`npm run build` 依 brief「只准一家跑一次」引修後 receipt rc=0，未並行重跑。須先更新 `白話說明/GAP-3施工進度.md`（與 WATCHED 同 commit 或之後）使 plain_docs 綠，再 stamp／UAT。

### 己方 R2 閉合（原提出方重跑）

**Closure P2-01（GROK-R2-P2-01）— CLOSED**  
- 原主張：R2 brief／R1 synth 寫 event_samples **232**，receipt／HEAD 實為 **229**。  
- 本輪：R3 brief L29／R2 synth L12／receipt 段「230 passed」／`rc_event_samples=0` 一致；本輪重跑 **230 passed** rc=0（R2 修補新增 1 條 pipeline decision_bar 測試：229→230）。  
- 測：`venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 230 passed；`grep -E '230 passed|rc_event_samples' handoffs/run_receipts/20260822T003000Z-gap3-b5-r2-fix-gate.log` 命中。

### 他家 R2 條目（複核同意／異議）

| ID | 複核 | 證據摘要 |
|---|---|---|
| CODEX-R2-P1-01 | **複核同意 CLOSED** | `pipeline.py:122-167`；`-k decision_bar` 1 passed |
| CODEX-R2-P1-02 | **複核同意 CLOSED** | `eventExport.ts:81-119`；vitest label_value 斷言綠 |
| CODEX-R2-P1-03 | **複核同意 CLOSED** | `api/routes/case.py:166-171`；`-k "gap3_import and verify"` 2 passed |
| CODEX-R2-P2-01 | **複核同意 CLOSED** | `EventTablesPanel.tsx:114-124`；disclosure testid 綠 |

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：全 K 線 rule＝事件成員、`label_threshold=0.0` 且 disclosure 已揭露「非模型預測力」⇒ estimand 誤讀風險可接受 | **成立（攻擊不推翻）** | disclosure 可見 rule／estimand_note／threshold_note；辨別表仍 `not_computed:no_model_scores…`（G3-R9）。不開 finding。 |
| **assumed**：`label_value` 缺欄 ⇒ 不寫＋skipped＋條件 IC loud unavailable 優於寫語意不符之值 | **成立（攻擊不推翻）** | 缺欄不靜默填 price_change；消費端 unavailable。UI 未 toast 不推翻此 tradeoff。 |
| fact-verified: api 14／event_samples 230／vitest 21／plain_docs rc=0／build rc=0 | **部分不實** | api／event_samples／vitest 本輪重跑與 receipt 一致。**plain_docs「rc=0」於 HEAD 不實**（receipt 綠＝commit 前 git-log 視窗；落地後 WATCHED 新於 施工進度）→ GROK-R3-P0-01。build 引 receipt，未本輪重跑。 |

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

## 被當成事實的未驗證假設（§0）

見上表；新增揭露＝brief／receipt「plain_docs rc=0」於 HEAD 偽 fact-verified（GROK-R3-P0-01）。其餘 assumed 攻擊不推翻。CODEX R2 四條修補語意攻擊（①–④）不成立。

ASSUMPTIONS_VERIFIED: 己方 GROK-R2-P2-01 計數已與 receipt／HEAD 對齊 230→CLOSED；CODEX-R2-P1-01/02/03／P2-01 碼與 RECHECK 全綠→複核同意 CLOSED；Q2①決策根×trigger_open 自洽、②缺欄 fail-loud、③JSON 拒 verify 正確、④disclosure 非洩密；plain_docs 於 HEAD rc=1 而敘事稱 0
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar` → 1 passed rc=0；`venv/bin/python -m pytest tests/api -q -k "gap3_import and verify"` → 2 passed rc=0；`venv/bin/python -m pytest tests/api -q -k gap3_import` → 14 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 230 passed rc=0（首跑曾 4×RunBusyError 鎖競爭，單跑重測全綠）；`cd frontend && npx vitest run gap3 pendingFeatures` → 4 files／21 passed rc=0；`bash scripts/plain_docs_sync_check.sh` → **rc=1**；`npm run build` 未本輪重跑（brief 禁並行），引 receipt rc=0
FAILURES_SEEN: event_samples 首跑 4 failed（RunBusyError ETHUSDT/12h lock）→ 單跑重測 230 passed；plain_docs rc=1＝本輪 finding
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260822-gap3-b5-review-r3-grok.md

STATUS: DONE
