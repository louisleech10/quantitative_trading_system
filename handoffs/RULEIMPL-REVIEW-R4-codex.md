# RULEIMPL R4 複驗 — Codex（R4）
審查客體：`handoffs/RULEIMPL-REVIEW-codex.md` 七條 BLOCKING、`handoffs/RULEIMPL-SPEC-DRAFT-R4.md`；依 `RULE-PROPOSAL-RECONCILE.md` v2 忠實度複驗。

1. **CLOSED — schema 必填表**：Phase 0 已逐欄凍結 `author_family/purpose/generator/inputs/config/parameters/selection/exclusions/output_schema/output_paths/falsifiability/execution_envelope/content_invariants/disposable`，缺欄、未知 disposable、reviewer=author、少於兩個非作者家族及 task provenance 不合法均定 FAIL；F7、V-M1–M5 提供可證偽面。
2. **STILL-OPEN — grandfather**：收緊政策文字與 V-T10 已補，但 checker 只有檔案/paired-file CLI，稿內未凍結「新建／任一 commit 變更／產尺語義 diff」相對哪個 git ref、如何取得 base、無 git context 時如何 fail；D4 cutoff 仍「待鎖」。因此實作者可用 mtime、HEAD、staged diff 或當日日期做出互不相容結果，尚非唯一機械語義。
3. **CLOSED — 聯檢 CLI**：已凍結 `template_check.sh todo <todo> --spec <spec>`、缺配對與 task-id mismatch 失敗、`gate.sh dispatch` 傳入成對檔，並有 V-T7–V-T10。
4. **STILL-OPEN — 條文 3 欄位**：六欄與各反事實維度已加入；但 approval-manifest 必填 schema 不含 `counterfactual_classification` 或其 digest，SPEC 又允許外部 path，故分類內容可變而不改 envelope body hash。Task 2.1 只機檢 `unknown`，沒有「任一 yes + 舊 REVIEW hash 必 FAIL」、超 envelope、缺 `mechanical_source/range` 的驗收案例；尚不能機械保證 yes/unknown 回委員會。
5. **CLOSED — envelope/manifest 拆分**：run 前 immutable approval envelope 與成功後原子發布 derived run-manifest 已拆開；失敗不發布、stamp 可重用、`--` argv round-trip 與 V-G9–G12 已覆蓋原發布循環。
6. **STILL-OPEN — exit-code + digest**：`exit_code==0`、receipt/audit digest、獨立目錄與 outputs exact-set 已入規格；但 `command_sha256 與 receipt 一致` 沒有凍結 command 的 canonical serialization 或要求由 `command` 重算，V-C/V-G 亦缺 command tamper 測試。V-G5 僅「改 receipt 且不動 audit」，未覆蓋原修文要求的「改 receipt 後重算內容 hash」以證明語義 hash 仍會拒收。
7. **STILL-OPEN — IC1EB sidecar 過渡**：白名單、immutable baseline hash、有效／過期／缺 sidecar 三測已補；但 sidecar 的 `approver/expires_at/category/reason` 沒有 body digest、核可戳記或與正式 SPEC hash 綁定，consumer 只驗非空 approver/未過期，改寫 expiry 後仍可 PASS，未達「已核可、具期限」的防竄改過渡。

ASSUMPTIONS_VERIFIED: 逐段靜態核對 R4 §C/§P/§V/§N/TODO 與原七條修文，並讀現行 `verification_claim_check.py`、`run_with_receipt.py` 的 receipt/audit 邊界。
TESTS_RUN: `sed`/`nl`/`rg` 唯讀檢查；未跑 pytest（本輪只審文件，未實作）。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增本檔。
NUMERIC_OR_SCHEMA_IMPACT: none（審查指出治理 schema 尚缺綁定，未修改 schema/數值碼）。
VERDICT: BLOCK
