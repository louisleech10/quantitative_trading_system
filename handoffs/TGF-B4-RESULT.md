# RESULT — tgf-b4-impl（TEMPLATE_GATE_FIX Batch B4）

## 結構欄位（必填，枚舉值）

STATIC_CHECK=PASS
RUNTIME_CHECK=PASS
MUTATION_CHECK=N/A:B4 無 mutation case
RECEIPTS=["tgf-b4-gate-fixtures-5","tgf-b4-smoke-low","tgf-b4-real-gate","tgf-b4-matrix-13","tgf-b4-grandfather-scan"]
OPEN_PENDING=[]

## 摘要

Task 6.1/6.2 完成：`gate.sh` 加 `--reconcile`、D-1 Verdict 行檢、D-2 BLOCKING/ID: 處置映射閉合；5 gate fixture；7 處舊錨點歸零；`coverage_check.sh` 輸出改名 ID PRESENCE；`RESULT_TEMPLATE` 加 TESTS_RUN↔RECEIPTS 映射行；新建 `docs/TEMPLATE_GATE_FIX_GRANDFATHER.md`。

<!-- claim-context: discussion -->
- `gate_no_verdict.md` 初版註解含 Verdict 字面 → D-1 被繞過；改註解 + Verdict 檢測改 `Verdict[[:space:]]*[:：]`。
- 真 gate 與矩陣回歸均 exit 0；未動 token 簽發/audit 邏輯。

## ASSUMPTIONS_VERIFIED

- D-1 檢測：`Verdict[[:space:]]*[:：]` 行（非全文 Verdict 子字串）。
- `gate_reconcile_complete.md` 戳記無 `task:` → provenance 跳過（既有 reconcile_stamps_check 行為）。
- 舊格式 adversarial（無 BLOCKING 且無 `ID: ADV-*`）走 grandfather，不強制 `--reconcile`。

## TESTS_RUN

```bash
# ① 5 gate fixture（依序 1/1/1/1/0）
rm -rf /tmp/tgf-gate-test && mkdir -p /tmp/tgf-gate-test
GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --risk high \
  --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md \
  --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md \
  --adversarial tests/gate_fixtures/gate_no_verdict.md \
  --intent test --facts-asked none-needed:test --review-role single-executor:n/a --template "跟過:test"
# ERROR: 檔缺 Verdict 行（D-1）→ exit 1

GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --risk high \
  --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md \
  --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md \
  --adversarial tests/gate_fixtures/gate_blocking_no_reconcile.md \
  --intent test --facts-asked none-needed:test --review-role single-executor:n/a --template "跟過:test"
# ERROR: --reconcile 必填（D-2）→ exit 1

GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --risk high \
  --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md \
  --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md \
  --adversarial tests/gate_fixtures/gate_id_major_no_reconcile.md \
  --intent test --facts-asked none-needed:test --review-role single-executor:n/a --template "跟過:test"
# ERROR: --reconcile 必填（D-2，MAJOR+ID:）→ exit 1

GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --risk high \
  --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md \
  --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md \
  --adversarial tests/gate_fixtures/gate_reconcile_missing_id.md \
  --reconcile tests/gate_fixtures/gate_reconcile_missing_id_reconcile.md \
  --intent test --facts-asked none-needed:test --review-role single-executor:n/a --template "跟過:test"
# ERROR: 缺 ADV-COMPOSER-2 處置行 → exit 1

GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --risk high \
  --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md \
  --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md \
  --adversarial tests/gate_fixtures/gate_reconcile_complete.md \
  --reconcile tests/gate_fixtures/gate_reconcile_complete_reconcile.md \
  --intent test --facts-asked none-needed:test --review-role single-executor:n/a --template "跟過:test"
# GATE PASS → exit 0

# ② 低風險 smoke
GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --intent test --risk low \
  --facts-asked none-needed:test --review-role single-executor:n/a --template "n/a:test"
# GATE PASS → exit 0

# ③ 舊錨點歸零
grep -c "§1\.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md
# CLAUDE.md:0 scripts/gate.sh:0 docs/MULTI_AGENT_ORCHESTRATION.md:0

# ④ COVERAGE PASS 字面
grep -rn "COVERAGE PASS" scripts/ --include="*.sh" | wc -l
# 0

# ⑤ TESTS_RUN 映射行
grep -c "TESTS_RUN" templates/RESULT_TEMPLATE.md
# 1

# ⑥ GRANDFATHER 含 IC_PHASE0_SPEC
grep -c "IC_PHASE0_SPEC" docs/TEMPLATE_GATE_FIX_GRANDFATHER.md
# ≥1

# ⑦ 矩陣回歸
bash scripts/test_template_check.sh; echo $?
# MATRIX PASS → 0

# ⑧ 真 gate（不帶 GATE_DIR_OVERRIDE）
bash scripts/gate.sh dispatch --intent "TGF-B4 post-change token regression" --risk low \
  --facts-asked none-needed:tgf-b4-impl --review-role single-executor:n/a \
  --template "n/a:tgf-b4-token-regression"
# GATE PASS → exit 0
```

## FAILURES_SEEN

- `gate_no_verdict.md` 註解含 Verdict 字面 → D-2 誤擋；修正 fixture 文案 + D-1 regex 收斂。

## SCOPE_CHANGES

none

## NUMERIC_OR_SCHEMA_IMPACT

- `coverage_check.sh` 輸出字串 `COVERAGE PASS/FAIL` → `ID PRESENCE PASS/FAIL`（語意誠實命名，不影響 exit code 語義）。
- `gate.sh` 新增 `--reconcile` token 欄位記錄；未改簽發/時效邏輯。

STATUS: DONE
