# GAP-3 B5 review R5 — grok（閉合輪：複核 CODEX-R4-P1-01；掃 R4 修補引入面）

task-id: 20260822-GAP3-B5-REVIEW-R5
family: grok
brief-kind: review
brief: handoffs/20260822-gap3-b5-review-r5-brief.md
R4 修補 diff: `git diff 013aa69f..HEAD`
R4 收斂: handoffs/reconcile/20260822-gap3-b5-review-r4/synth.md
修後 receipt: handoffs/run_receipts/20260822T023000Z-gap3-b5-r4-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP／交使用者 UAT（CODEX-R4-P1-01＝複核同意 CLOSED；本輪無新 finding）

### 必答

1. **CODEX-R4-P1-01：複核同意 CLOSED**

   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | CODEX-R4-P1-01 | **複核同意 CLOSED** | 路由層 `api/routes/case.py:155-163`：`verify_source_digest and src_bytes is not None and src_bytes == content` ⇒ 400 `source_file_must_differ_from_event_file`（訊息含 `*.source.json`／關閉 verify）。本輪 `pytest tests/api -q -k "gap3_import and same_file"` → **1 passed** rc=0（live log：`kind=source_file_must_differ_from_event_file`，非一串 `digest_mismatch`）；`-k "gap3_import and verify"` → **4 passed** rc=0（含缺 source_file 400／companion 200／竄改 422／同檔 400）；`-k "gap3_import and companion"` → **1 passed**；全 `-k gap3_import` → **16 passed**。description／`import_records` docstring／UAT B2b 已對齊「必須另附相異來源檔」。 |

2. **修補是否引入新問題（brief Q2 三點）？**

   - ①**`src_bytes == content` 全等與大檔記憶體／效能**：兩邊在比對前已 `await *.read()` 進記憶體；`EventImportService.MAX_FILE_SIZE = 50MB` 只擋事件檔（`parse_upload`），companion 路徑在 R3 已同等讀滿。全等位元比對為既有緩衝上之 O(n)，相對 JSON 解析／契約驗證可忽略。**非本輪修補引入的新問題**。不開 finding。
   - ②**關閉 verify 時同檔上傳仍應正常收**：`test_gap3_import_verify_same_file_rejected_explicitly` 末段：同檔雙欄、無 `verify_source_digest` ⇒ **200**（本輪 same_file 探針實跑確認）。**行為正確**。不開 finding。
   - ③**`source_file` 選用 multipart、只傳 `file` 的呼叫端**：`File(None)`＋`verify_source_digest` 預設 `False`；未開 verify 時不要求／不拒 `source_file`。既有「只傳 file」路徑零影響（`test_gap3_import_file_verify_requires_source_file` 關 verify ⇒ 200；全套 16 passed）。**零影響**。不開 finding。

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**

   **可以（grok 本輪）**——本輪實跑：`tests/api -k gap3_import` **16 passed** rc=0；`-k "gap3_import and same_file"` **1 passed**；`-k "gap3_import and verify"` **4 passed**；`-k companion` **1 passed**；`bash scripts/plain_docs_sync_check.sh` →「全數同步（受管 10 檔）」**rc=0**。`tests/momentum/event_samples/` **230 passed**／`npm run build`／`npx vitest run gap3` 引修後 receipt `20260822T023000Z-…`（brief 禁並行 build；event_samples 全套以主委 receipt 為準）。前提：同輪 codex 對 CODEX-R4-P1-01 標 CLOSED、三家無新 BLOCKING。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：「verify 只接受相異來源檔」為最終設計（不再追求同檔相容——自我指涉不可能），文件與 UAT 已一致 | **成立（攻擊不推翻）** | 事件列含 `source_file_digest`＝來源檔 sha256；若對「含 digest 欄的事件檔自身」取 sha256，digest 欄會改變雜湊輸入 ⇒ 不可能自洽。路由以專屬 400 取代一堆 `digest_mismatch` 為正確 UX。description／service docstring／UAT B2b 三態（companion 過／缺 source 400／同檔 400）與行為一致。另尋「剝掉 digest 再 hash 事件檔」會改 provenance 語意＝錯誤方向。 |
| fact-verified: api 16／event_samples 230；同檔+verify⇒400 `source_file_must_differ…`；companion⇒200；缺 source⇒400；關 verify 同檔⇒200 | **本輪子集實核成立；event_samples／FE build／vitest 引 receipt** | 本輪：api 16、same_file 1、verify 4、companion 1、plain_docs rc=0。230／build／vitest 引 `20260822T023000Z-gap3-b5-r4-fix-gate.log`（禁並行 build）。 |

## GROK-R5-P3-00

**斷言**: 本輪逐項核對後無 finding——CODEX-R4-P1-01 複核同意 CLOSED（同檔+verify ⇒ 400 `source_file_must_differ_from_event_file`，非 digest_mismatch；distinct companion 仍 200）；R4 修補（同檔全等拒、description／docstring／UAT B2b）未引入可證偽 P0–P2 新缺陷（①既有 50MB 緩衝上比對無新增記憶體問題②關 verify 同檔 200③選用 source_file 零影響）；brief assumed「只接受相異來源檔」攻擊不推翻。

**碼證**: `pytest tests/api -q -k "gap3_import and same_file"` → **1 passed** rc=0（400 `source_file_must_differ_from_event_file`＋關 verify 同檔 200）；`-k "gap3_import and verify"` → **4 passed** rc=0；`-k companion` → **1 passed**；`-k gap3_import` → **16 passed** rc=0；`bash scripts/plain_docs_sync_check.sh` → rc=0。落點：`api/routes/case.py:144-175`；`api/services/case_import_service.py:712-716`；`tests/api/test_gap3_import.py:254-271`；`docs/GAP3_UAT_CHECKLIST.md` B2b。event_samples 230／FE build／vitest 引 receipt（brief 禁並行 build）。

**來源摘要**: handoffs/20260822-gap3-b5-review-r5-brief.md#023236a1ee38；handoffs/reconcile/20260822-gap3-b5-review-r4/synth.md#b0ed06929605；handoffs/run_receipts/20260822T023000Z-gap3-b5-r4-fix-gate.log#3a9c5359d734；api/routes/case.py#505fef777e42；api/services/case_import_service.py#7959d0436e57；tests/api/test_gap3_import.py#ed9d2ec4d7de；docs/GAP3_UAT_CHECKLIST.md#9c00fc41592c

正文：閉合輪義務＝複核 CODEX-R4-P1-01＋掃本輪修補引入面＋攻擊 assumed；三項皆通過。不受理 SPEC/TODO 重審／G3-R11／ML／效能門檻／R1–R4 已裁 CLOSED 再議。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

見上表；assumed「只接受相異來源檔」攻擊不推翻。fact-verified 子集本輪實核；event_samples／build／vitest 引 receipt。

ASSUMPTIONS_VERIFIED: CODEX-R4-P1-01 同檔+verify⇒400 source_file_must_differ_from_event_file（非 digest_mismatch）＋companion 200＋缺 source 400＋關 verify 同檔 200→複核同意 CLOSED；Q2①既有緩衝比對無新記憶體問題②關 verify 同檔 200③選用 source_file 零影響；assumed「相異來源檔」攻擊不推翻；plain_docs HEAD rc=0
TESTS_RUN: `pytest tests/api -q -k "gap3_import and same_file"` → 1 passed rc=0；`pytest tests/api -q -k "gap3_import and verify"` → 4 passed rc=0；`pytest tests/api -q -k "gap3_import and companion"` → 1 passed rc=0；`pytest tests/api -q -k gap3_import` → 16 passed rc=0；`bash scripts/plain_docs_sync_check.sh` → rc=0；`npm run build`／`npx vitest run gap3`／`pytest tests/momentum/event_samples/ -q` 未本輪重跑（brief 禁並行 build；230 引 receipt `20260822T023000Z-gap3-b5-r4-fix-gate.log`）
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260822-gap3-b5-review-r5-grok.md

STATUS: DONE
