# RESULT — tgf-b3-impl（TEMPLATE_GATE_FIX Batch B3）

## 結構欄位（必填，枚舉值）

STATIC_CHECK=PASS
RUNTIME_CHECK=PASS
MUTATION_CHECK=N/A:本批僅改 templates，未動 template_check.sh
RECEIPTS=["tgf-b3-task31-grep","tgf-b3-task32-grep","tgf-b3-task41-grep","tgf-b3-task51-grep","tgf-b3-matrix-13"]
OPEN_PENDING=[]

## 摘要

Task 3.1/3.2/4.1/5.1 範圍內三個 template 檔已更新（詳見 git diff）。`spec_good_full` 維持合規（VERIFY: tgf-b3-task31-grep）；13 fixture 矩陣與 EXPECTED 一致（VERIFY: tgf-b3-matrix-13）。

## ASSUMPTIONS_VERIFIED

- `templates/SPEC_TEMPLATE.md` 基線 60 行，改後 65 行（delta=5 ≤ 13）。
- `spec_good_full.md` 已合規，未因範本教學更新而需同步改 fixture。
- 未動 `template_check.sh` / `gate.sh` / `EXPECTED.txt`（TODO §0 紅線）。

## TESTS_RUN

```bash
# Task 3.1
grep -c "FACT-RECEIPT" templates/SPEC_TEMPLATE.md
# 2

grep -c "RISK-HIT" templates/SPEC_TEMPLATE.md
# 2

grep -c "刪除本 HTML 註解" templates/SPEC_TEMPLATE.md
# 1

bash scripts/template_check.sh spec tests/gate_fixtures/spec_good_full.md; echo $?
# TEMPLATE PASS (spec): tests/gate_fixtures/spec_good_full.md ...
# 0

# Task 3.2
grep -c "kline_cache.h5" templates/SPEC_TEMPLATE.md
# 1

grep -c "TEST_DESIGN_CHARTER" templates/SPEC_TEMPLATE.md
# 1

before=60; after=$(wc -l < templates/SPEC_TEMPLATE.md); test $((after-before)) -le 13 && echo DELTA_OK
# DELTA_OK (after=65, delta=5)

# Task 4.1
grep -c "RECHECK" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
# 2

grep -c "STRICTNESS" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
# 0

grep -c "VERIFY:" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
# 1

grep -c "ADV-CODEX" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
# 1

grep -c "解耦" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
# 1

wc -l < templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
# 62 (≤ 78)

# Task 5.1
grep -c "copilot-instructions" templates/TODO_GENERATION_PROMPT.md || echo 0
# 0

grep -c "AGENTS.md" templates/TODO_GENERATION_PROMPT.md
# 1

grep "無條件讀" templates/TODO_GENERATION_PROMPT.md | grep -cE "ARCHITECTURE|DEVELOPMENT_GUIDE|copilot" || echo 0
# 0

grep -c "manifest ID" templates/TODO_GENERATION_PROMPT.md
# 1

# Matrix
bash scripts/test_template_check.sh; echo $?
# MATRIX PASS: 全 13 fixture 與 EXPECTED 一致
# 0
```

## FAILURES_SEEN

none

## SCOPE_CHANGES

none（僅 `templates/SPEC_TEMPLATE.md`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/TODO_GENERATION_PROMPT.md` + 本 RESULT 檔）

## NUMERIC_OR_SCHEMA_IMPACT

none（範本教學文字；機檢腳本與 EXPECTED 未動）

STATUS: DONE
