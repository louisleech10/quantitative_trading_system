# RESULT — tgf-b1-impl（TEMPLATE_GATE_FIX Batch B1）

## 結構欄位（必填，枚舉值）

STATIC_CHECK=PASS
RUNTIME_CHECK=PASS
MUTATION_CHECK=N/A:B2 才有 mutation case 驗收
RECEIPTS=["tgf-b1-freeze-13","tgf-b1-default-exit1","tgf-b1-bypass-rc0","tgf-b1-pending-rc1"]
OPEN_PENDING=[]

## 摘要

Task 1.1/1.2 完成：13 個 gate fixture（7 繞過＋1 維持 FAIL＋5 正樣本）、`POSITIVE_SAMPLES.txt`、`scripts/test_template_check.sh`（--freeze / --mutate 契約）、`EXPECTED.txt`（§G 先驗手填）、`BASELINE_BEFORE.txt`（--freeze 實測）、`MUTATION.txt`（4 列骨架）。

<!-- claim-context: discussion -->
- 未改 `scripts/template_check.sh`（B2 範圍）。
- `spec_verified_bypass` 初版因 hollow「驗證」bullet 誤擋 exit 1；改為 `### 已驗證事實` 子標題＋邊界行去「驗證」字面後重現繞過 exit 0。
- `todo_bad` 邊界行含「驗證」觸發 hollow；改寫後 exit 0。
- BASELINE 與現行機檢一致：7 繞過=0、pending=1、pending_none_variant=1（誤擋）、5 正樣本=0。

## ASSUMPTIONS_VERIFIED

- 現行 `template_check.sh` 對 7 支繞過探針 exit 0（baseline 實測，見 BASELINE_BEFORE.txt）。
- `spec_pending_unresolved.md` exit 1（facts-resolved 正例）。
- EXPECTED.txt 依 SPEC §G 手填（Phase 2 目標），非跑後回填；預設 `test_template_check.sh` exit 1。

## TESTS_RUN

```bash
ls tests/gate_fixtures/*.md | wc -l          # 13
bash scripts/test_template_check.sh --freeze && wc -l < tests/gate_fixtures/BASELINE_BEFORE.txt  # 13
bash scripts/test_template_check.sh; echo $?  # 1
bash scripts/template_check.sh spec tests/gate_fixtures/spec_verified_bypass.md; echo $?  # 0
bash scripts/template_check.sh spec tests/gate_fixtures/spec_pending_unresolved.md; echo $?  # 1
wc -l < tests/gate_fixtures/EXPECTED.txt  # 13
file tests/gate_fixtures/*.md  # UTF-8 text, LF
```

## FAILURES_SEEN

- spec_verified_bypass / todo_bad 初版 hollow 誤擋 → 已修 fixture 文案，第二輪全過。

## SCOPE_CHANGES

none

## NUMERIC_OR_SCHEMA_IMPACT

none（僅新增 tests/gate_fixtures/* 與 scripts/test_template_check.sh）

STATUS: DONE
