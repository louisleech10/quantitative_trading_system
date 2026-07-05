# RESULT — tgf-b2-impl-r2（TEMPLATE_GATE_FIX Batch B2 重做）

## 結構欄位（必填，枚舉值）

STATIC_CHECK=PASS
RUNTIME_CHECK=PASS
MUTATION_CHECK=PASS
RECEIPTS=["tgf-b2-r2-matrix-13","tgf-b2-r2-mutate-a1","tgf-b2-r2-mutate-a3","tgf-b2-r2-mutate-a4","tgf-b2-r2-mutate-a5","tgf-b2-r2-selfcheck-spec","tgf-b2-r2-selfcheck-todo"]
OPEN_PENDING=[]

## 摘要

Task 2.1–2.4 重做完成：`scripts/template_check.sh` 硬化 §A fact-scope 狀態機、RISK-HIT 宣告制、TODO per-Task 三欄、RESULT 交叉規則＋待確認 regex。`scripts/test_template_check.sh --mutate` 改 cp 備份還原（不再 git checkout）、進 mutate 前強制矩陣全綠（exit 2 拒跑）、還原後比對 pre-mutate 快照（非過期 BASELINE_BEFORE）。 〔REF:handoffs/2026-07-04-TGF-TODO-ADV-RECONCILE.md〕

<!-- claim-context: discussion -->
- 上輪 tgf-b2-impl：未 commit 實作即跑 --mutate → `git checkout` 還原沖回 HEAD，矩陣紅 + diff 空（自毀事故）。
- 本輪 defect 修正：① cp 備份還原 ② mutate 前置全綠 gate ③ 還原驗證改比 tmp_actual（=EXPECTED）非 BASELINE_BEFORE。 〔REF:handoffs/2026-07-04-TGF-TODO-ADV-RECONCILE.md〕 〔SUPERSEDED:首輪 tgf-b2-impl 紅燈紀錄由本 r2 輪修復取代〕
- commits：`f5850c6`（Phase 2 硬化 + mutate cp）、`fix` commit（還原比對修正）；未 push。

## ASSUMPTIONS_VERIFIED

- 13 fixture 矩陣與 EXPECTED.txt 一致（`bash scripts/test_template_check.sh` exit 0）。
- `docs/TEMPLATE_GATE_FIX_SPEC.md` / `docs/TEMPLATE_GATE_FIX_TODO.md` 自檢 exit 0。
- 4 mutation（A-1/A-3/A-4/A-5）破壞轉紅、cp 還原後矩陣與破壞前一致、`git diff --exit-code scripts/template_check.sh` 淨。
- RISK-HIT grep 支援 markdown bullet 前綴（`- RISK-HIT:`）；fact-scope 僅 `###` / `- **` 同級子段標題切換，巢狀 bullet 不誤退出。

## TESTS_RUN

```bash
bash scripts/test_template_check.sh; echo $?
# MATRIX PASS: 全 13 fixture 與 EXPECTED 一致 → 0

bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md; echo $?
# TEMPLATE PASS (spec) → 0

bash scripts/template_check.sh todo docs/TEMPLATE_GATE_FIX_TODO.md; echo $?
# TEMPLATE PASS (todo) → 0

for id in A-1 A-3 A-4 A-5; do bash scripts/test_template_check.sh --mutate $id; echo "mutate $id=$?"; done
# MUTATE PASS: A-1 / A-3 / A-4 / A-5 → 各 0

git diff --exit-code scripts/template_check.sh; echo $?
# 0（mutation 序列後工作區淨）
```

## MUTATION_CHECK

本批=PASS。4 case receipt：

| id | sed 破壞 | 轉紅摘要 |
|---|---|---|
| A-1 | `FACT-RECEIPT:`→`FACT-RECEIPTX:` | spec_good_full、spec_risk_false_positive 等 receipt 檢查失效（繞過探針仍綠） |
| A-3 | `RISK-HIT:`→`RISK-HITX:` | 全 spec 缺宣告檢查；spec_pending_none_variant 等正樣本誤擋 |
| A-4 | `### Task`→`### TaskX` | todo_good_full 轉 1（per-Task 切塊失效） |
| A-5 | `RECEIPTS=`→`RECEIPTSX=` | 三支 result fixture 全轉 1（含 discussion 探針） |

## FAILURES_SEEN

- 上輪 tgf-b2-impl：`--mutate` 用 `git checkout` 還原未 commit 改動 → 實作自毀、驗收矩陣紅。
- 本輪 debug-1：fact-scope 將 `###` 下 `- raw_data` 內容 bullet 誤判為同級子段退出 → 修正為僅 `###` / `- **` 標題切換。
- 本輪 debug-2：還原後比 BASELINE_BEFORE（修前 baseline）→ 全 mutation FAIL；改比 pre-mutate 快照。

## SCOPE_CHANGES

none（僅 `scripts/template_check.sh`、`scripts/test_template_check.sh`；MUTATION.txt 已於 B1 commit）

## NUMERIC_OR_SCHEMA_IMPACT

none（機檢加嚴；EXPECTED.txt / gate.sh 未動）

STATUS: DONE
