# GAP-3 B5 review R5 — composer（閉合輪：CODEX-R4-P1-01 複核 CLOSED ＋ sentinel）

task-id: 20260822-GAP3-B5-REVIEW-R5  
family: composer  
brief-kind: review  
brief: handoffs/20260822-gap3-b5-review-r5-brief.md  
R4 修補 diff: `git diff 013aa69f..HEAD`  
R4 收斂: handoffs/reconcile/20260822-gap3-b5-review-r4/synth.md  
修後 receipt: handoffs/run_receipts/20260822T023000Z-gap3-b5-r4-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP 並交使用者 UAT（B5 Gate 本輪全綠；CODEX-R4-P1-01 複核同意 CLOSED；本輪無新 finding）

### 必答

1. **CODEX-R4-P1-01 CLOSED／OPEN ＋ composer 複核**

   | ID | 原提出方 | 本輪處置 | composer 立場 | RECHECK 摘要 |
   |---|---|---|---|---|
   | **CODEX-R4-P1-01** | CODEX | （待 codex 標 CLOSED） | **複核同意 CLOSED** | `pytest tests/api -q -k "gap3_import and same_file"` → **1 passed** rc=0；同檔＋verify ⇒ 400 `source_file_must_differ_from_event_file`（非 digest_mismatch）；關閉 verify 同檔 ⇒ 200；distinct companion 路徑仍 200（`test_gap3_import_verify_with_companion_source_file_passes`） |

2. **R4 修補是否引入新問題（brief 三點＋assumed）**

   | 攻擊點 | 判定 | 碼證 |
   |---|---|---|
   | ① 同檔比對 `src_bytes == content` 全等，大檔記憶體／效能 | **不開 finding** | `case.py:153-155` 在 `file.read()` 之後做 O(n) 位元組比對；`EventImportService.MAX_FILE_SIZE = 50 * 1024 * 1024`（`case_import_service.py:616`）上限內兩份 bytes 本已在記憶體，額外成本＝一次全等掃描，可接受 |
   | ② 關閉 verify 時同檔上傳仍正常收 | **成立** | `test_gap3_import_verify_same_file_rejected_explicitly` 末段：同檔雙欄＋`validate_only=true`（無 verify）⇒ **200**；`test_gap3_import_file_verify_requires_source_file` 關 verify ⇒ **200** |
   | ③ `source_file` 為選用 multipart，既有只傳 `file` 零影響 | **成立** | `case.py:142` Optional；未附 `source_file` 且 `verify_source_digest=false`（預設）⇒ 16 條 `gap3_import` 全綠，含 JSON／CSV 舊路徑 |
   | **assumed**：「verify 只接受相異來源檔」為最終設計 | **攻擊不推翻（不開 finding）** | 路由層 400＋訊息、Query description、UAT B2b 三態與 `test_gap3_import_verify_same_file_rejected_explicitly` 一致；自我指涉在數學上不可能，改為機械拒收優於 digest_mismatch 噪音 |

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**

   **是（composer 本輪 APPROVED）**——本輪實跑與 receipt 對齊：`gap3_import` **16 passed** rc=0；`event_samples/` **230 passed** rc=0；`plain_docs_sync_check` **rc=0**。`npm run build` 依 brief 只准一家跑——引 receipt／R4 各家 rc=0，本輪未重跑。

## COMPOSER-R5-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R4-P1-01 修補 RECHECK 全綠且複核同意 CLOSED；R4 修補（同檔 400 `source_file_must_differ_from_event_file`、description／docstring、UAT B2b）未引入可證偽 P0–P2 新缺陷；brief assumed「verify 只接受相異來源檔」攻擊不推翻。

**碼證**: `bash scripts/plain_docs_sync_check.sh` → rc=0；`pytest tests/api -q -k "gap3_import and same_file"` → **1 passed** rc=0（400 `source_file_must_differ_from_event_file`＋關 verify 200）；`pytest tests/api -q -k "gap3_import and verify"` → **4 passed** rc=0；`pytest tests/api -q -k gap3_import` → **16 passed** rc=0；`pytest tests/momentum/event_samples/ -q` → **230 passed** rc=0。修法落點：`case.py:144-175` 同檔拒收＋缺 source 400；`test_gap3_import.py:254-271` B2b 三態；`case_import_service.py:616` 50MB 上限。

**來源摘要**: handoffs/20260822-gap3-b5-review-r5-brief.md#023236a1ee38；handoffs/reconcile/20260822-gap3-b5-review-r4/synth.md#b0ed06929605；handoffs/run_receipts/20260822T023000Z-gap3-b5-r4-fix-gate.log#3a9c5359d734；api/routes/case.py#505fef777e42；tests/api/test_gap3_import.py#ed9d2ec4d7de；scripts/plain_docs_sync_check.sh#1d127ae13f1a

正文：閉合輪義務＝複核 CODEX-R4-P1-01 CLOSED ＋掃 R4 修補引入面；兩項皆通過。不受理 SPEC/TODO 重審／G3-R11／ML／效能門檻／R1–R4 已裁 CLOSED 再議。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

brief assumed「verify 只接受相異來源檔」已攻擊（上表）不推翻；receipt 數字本輪 **fact-verified**（非推理）。

## VERIFY（本輪複驗）

```
bash scripts/plain_docs_sync_check.sh → rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and same_file" → 1 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k "gap3_import and verify" → 4 passed rc=0
venv/bin/python -m pytest tests/api/ -q -k gap3_import → 16 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 230 passed rc=0
npm run build → 未本輪重跑（brief 禁並行）；引 receipt rc=0
```

ASSUMPTIONS_VERIFIED: 上述命令＋`case.py:139-177`／`test_gap3_import.py:207-271`／`case_import_service.py:616` 對讀  
TESTS_RUN: 見 VERIFY  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；R4 修補之 400 kind 為預期行為，本輪未再改）  
OUTPUT: handoffs/20260822-gap3-b5-review-r5-composer.md  
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
