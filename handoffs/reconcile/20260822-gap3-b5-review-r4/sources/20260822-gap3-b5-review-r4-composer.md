# GAP-3 B5 review R4 — composer（閉合輪：COMPOSER-R3-P2-01 CLOSED ＋ sentinel）

task-id: 20260822-GAP3-B5-REVIEW-R4  
family: composer  
brief-kind: review  
brief: handoffs/20260822-gap3-b5-review-r4-brief.md  
R3 修補 diff: `git diff 1c54049b..HEAD`  
R3 收斂: handoffs/reconcile/20260822-gap3-b5-review-r3/synth.md  
修後 receipt: handoffs/run_receipts/20260822T014000Z-gap3-b5-r3-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP 並交使用者 UAT（B5 Gate 本輪全綠；COMPOSER-R3-P2-01 CLOSED；本輪無新 finding）

### 必答

1. **己方 R3 各條 CLOSED／OPEN ＋他家複核**

   | ID | 原提出方 | 本輪處置 | composer 立場 | RECHECK 摘要 |
   |---|---|---|---|---|
   | **COMPOSER-R3-P2-01** | COMPOSER | **CLOSED** | 原提出方重跑 | `bash scripts/plain_docs_sync_check.sh` → **rc=0**，stdout「✓ 白話說明 全數同步（受管 10 檔）」；R3 修法（看板隨 commit 更新＋`git add` 後 `--staged`）已落地 |
   | CODEX-R2-P1-03 | CODEX | （待 codex 標 CLOSED） | **複核同意 CLOSED** | `pytest tests/api -q -k "gap3_import and (verify or companion)"` → **3 passed** rc=0；兩檔齊＋verify ⇒ 200＋`source_digest_verified=true`；缺 source_file ⇒ 400 `source_file_required_for_verify`；竄改 ⇒ 422 `digest_mismatch` |
   | CODEX-R3-P1-01 | CODEX | （待 codex 標 CLOSED） | **複核同意 CLOSED** | 同 COMPOSER-R3-P2-01：`plain_docs_sync_check` **rc=0** |
   | CODEX-R3-P1-02 | CODEX | （待 codex 標 CLOSED） | **複核同意 CLOSED** | `npx vitest run gap3` → **18 passed** rc=0；`page.tsx:526-535` 傳 `horizonBars`＋`n_missing_label_value` confirm；`eventExport.ts:121` 回傳缺欄計數 |
   | CODEX-R3-P2-03 | CODEX | （待 codex 標 CLOSED） | **複核同意 CLOSED** | `pytest … -k decision_bar` → **1 passed** rc=0；in-memory 探針：`wrong_vals[i]_assertions_would_pass=False`、`falsifiable=True`（錯位索引不會假綠） |
   | GROK-R3-P0-01 | GROK | （待 grok 標 CLOSED） | **複核同意 CLOSED** | `plain_docs_sync_check` **rc=0**（與 GROK-R3-P0-01 根因同型，R3 修補已解） |

2. **修補是否引入新問題（brief 四點＋兩條 assumed）**

   | 攻擊點 | 判定 | 碼證 |
   |---|---|---|
   | ① `source_file` 為 multipart 選用欄，未附時既有呼叫端行為不變 | **成立** | `case.py:142-165`：`source_file` Optional；`verify_source_digest=false` 且未附 source_file ⇒ `test_gap3_import_file_verify_requires_source_file` 200；既有 JSON/CSV 路徑未改 |
   | ② verify 未附 source_file ⇒ 400 後「上傳檔即來源檔」是否還有路 | **assumed 成立（不開 finding）** | 顯式 400＋訊息引導 companion `.source.json`；**可成功路徑**：事件檔作 `file`、companion 作 `source_file`（`test_gap3_import_verify_with_companion_source_file_passes`）；若 digest 確實綁 upload bytes 本身，同一 bytes 可同時放兩欄——但 `/search` 匯出 digest 綁 `canonicalSourceText`（非事件 JSON body），須用 companion，與 `verify_note` 一致 |
   | ③ 匯出雙檔連續 `link.click()` 被擋風險 | **UI 便利性（不開 finding）** | `page.tsx:537-548` 同一次 user gesture 內同步兩次 click；brief 標非正確性；部分瀏覽器可能只下載第一檔——使用者可重按或手動存 companion |
   | ④ horizon 選單預設 2 與 `label_definition.window.horizon_bars` 一致 | **成立** | `page.tsx:54` `useState(2)`；`526` 傳 `horizonBars: eventHorizonBars`；`eventExport.ts:61,101` 同一 `horizon` 寫入 `window.horizon_bars` 與 `future_{h}bar_return` |
   | **assumed**：companion `*.source.json` 欄位集足作 provenance | **成立（攻擊不推翻）** | `eventExport.ts:28-37` canonical＝symbol/timeframe/timestamp/positive_case/price_change；vitest `createHash('sha256').update(out.source_file_text)` === `source_file_digest`；契約 `source_file_digest` 綁「搜尋來源」非完整事件列——與 `source_digest_of` 敘事一致 |

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**

   **是（composer 本輪 APPROVED）**——本輪全子集與 receipt 對齊：`gap3_import` **15 passed**；`event_samples/` **230 passed**；`gap3` vitest **18 passed**；`pendingFeatures` **22 passed**；`plain_docs_sync_check` **rc=0**。`npm run build` 依 brief 只准一家跑——引 receipt rc=0，本輪未重跑。

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R3-P2-01 重跑 CLOSED；他家 R3 修補 RECHECK 全綠且複核同意 CLOSED；R3 修補未引入可證偽 P0–P2 缺陷；brief 兩條 assumed（同源雙欄／companion 欄位集）攻擊不推翻。

**碼證**: `bash scripts/plain_docs_sync_check.sh` → rc=0；`pytest tests/api -q -k gap3_import` → **15 passed** rc=0；`pytest tests/api -q -k "gap3_import and (verify or companion)"` → **3 passed** rc=0；`pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar` → **1 passed** rc=0；`pytest tests/momentum/event_samples/ -q` → **230 passed** rc=0；`cd frontend && npx vitest run gap3` → **18 passed** rc=0；`npx vitest run gap3 pendingFeatures` → **22 passed** rc=0。in-memory falsifiability：`wrong_vals[i]_assertions_would_pass=False`。修法落點：`case.py:142-165` source_file+verify；`eventExport.ts:60-121` horizon+companion；`page.tsx:526-548` confirm+雙下載；`test_pipeline.py:101-130` score 攔截斷言。

**來源摘要**: handoffs/reconcile/20260822-gap3-b5-review-r3/synth.md#eaec8254b879；handoffs/run_receipts/20260822T014000Z-gap3-b5-r3-fix-gate.log#3f37d9e7b733；scripts/plain_docs_sync_check.sh#1d127ae13f1a；frontend/src/lib/eventExport.ts#8966db1df2a1；frontend/src/app/search/page.tsx#04ac28eca77b；tests/api/test_gap3_import.py#fc12718ec299

正文：閉合輪義務＝原提出方重跑 COMPOSER-R3-P2-01 ＋複核他家 CLOSED ＋掃 R3 修補新問題；三項皆通過。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

brief 兩條 assumed 已攻擊（上表）均成立；receipt「plain_docs rc=0」本輪 **fact-verified**（與 R3 HEAD 紅不同，R3 修補後已綠）。

## VERIFY（本輪複驗）

```
bash scripts/plain_docs_sync_check.sh → rc=0
venv/bin/python -m pytest tests/api/ -q -k gap3_import → 15 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and (verify or companion)" → 3 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar → 1 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 230 passed rc=0
cd frontend && npx vitest run gap3 → 18 passed rc=0
cd frontend && npx vitest run gap3 pendingFeatures → 22 passed rc=0
in-memory falsifiability probe → correct_index_assertions_pass=True, falsifiable=True
npm run build → 未本輪重跑（brief 禁並行）；引 receipt rc=0
```

ASSUMPTIONS_VERIFIED: 上述命令＋`case.py:139-167`／`eventExport.ts:27-124`／`page.tsx:54,526-548`／`pipeline.py:135-151`／`test_pipeline.py:101-130` 對讀  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；R3 修補之 schema／雙檔下載為預期行為，本輪未再改）  
OUTPUT: handoffs/20260822-gap3-b5-review-r4-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
