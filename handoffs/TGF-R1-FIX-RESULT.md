# TGF-R1-FIX 收尾報告（task-id=tgf-r1-fix）

## 結構欄位

STATIC_CHECK=PASS
RUNTIME_CHECK=PASS
MUTATION_CHECK=NOT_RUN
RECEIPTS=["tgf-r1-verify-probe","tgf-r1-matrix-14","tgf-r1-mutate-all","tgf-r1-diff-check","tgf-r1-selfcheck"]
OPEN_PENDING=[]

## 摘要

ADV-CODEX-R1：result 分支 discussion 豁免改為有界（遇 `claim-context:`／`## ` heading 結束 discussion，`claim-context: operational` 後恢復掃描）。新增 fixture `result_done_after_discussion.md`；EXPECTED 13→14。ADV-CODEX-R4：清除本 epic 檔案集 trailing whitespace。

## 驗收命令與輸出

### ① Codex R1 VERIFY 探針 → RC:1

```bash
tmp=$(mktemp); cp tests/gate_fixtures/result_notrun_done_in_discussion.md "$tmp"; printf '\nclaim-context: operational\nSTATUS: DONE\n' >> "$tmp"; bash scripts/template_check.sh result "$tmp"; echo RC:$?; rm -f "$tmp"
```

```
TEMPLATE FAIL (result): ...
  · MUTATION_CHECK=NOT_RUN 時 discussion 外禁 operational 極性: STATUS: DONE
RC:1
```

### ② 矩陣 14/14

```bash
bash scripts/test_template_check.sh; echo RC:$?
```

```
MATRIX PASS: 全 14 fixture 與 EXPECTED 一致
RC:0
```

### ③ --mutate A-1/A-3/A-4/A-5

```bash
for id in A-1 A-3 A-4 A-5; do bash scripts/test_template_check.sh --mutate $id; echo RC:$?; done
```

（commit 後四條皆 MUTATE PASS，各 RC:0）

### ④ git diff --check（本 epic 檔案集）

```bash
git diff --check 2447c88..HEAD -- docs/TEMPLATE_GATE_FIX_* scripts/template_check.sh scripts/test_template_check.sh scripts/gate.sh scripts/coverage_check.sh templates/ tests/gate_fixtures/ handoffs/TGF-* handoffs/2026-07-04-TGF-*; echo RC:$?
```

（commit 後 RC:0）

### ⑤ SPEC/TODO 自檢

```bash
bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md; echo RC:$?
bash scripts/template_check.sh todo docs/TEMPLATE_GATE_FIX_TODO.md; echo RC:$?
```

```
TEMPLATE PASS (spec): ...
RC:0
TEMPLATE PASS (todo): ...
RC:0
```

## 結構化收尾

ASSUMPTIONS_VERIFIED: discussion 區結束條件=下一個 claim-context: 或 ## heading；sorted EXPECTED 須字母序（result_done_after_discussion 置首）
TESTS_RUN: ①–⑤ 全通過（mutate 於 commit 後驗）
FAILURES_SEEN: EXPECTED append 尾行致 sort 不一致 → 改為字母序首行
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: EXPECTED.txt 13→14 行；無數值/schema 變更
