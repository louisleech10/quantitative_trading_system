# RESULT — tgf-b4-hotfix（W3 戳記閘 --reconcile 分流死鎖修復）

## 結構欄位（必填，枚舉值）

STATIC_CHECK=PASS
RUNTIME_CHECK=PASS
MUTATION_CHECK=N/A:hotfix 無 mutation case
RECEIPTS=["tgf-b4-hotfix-positive","tgf-b4-hotfix-negative","tgf-b4-hotfix-fixtures-5","tgf-b4-hotfix-matrix-13","tgf-b4-hotfix-smoke"]
OPEN_PENDING=[]

## 摘要

`gate.sh` W3 reconcile 核可閘：`--reconcile` 已提供且非 waived 時改對 reconcile 單檔跑 `reconcile_stamps_check`；未提供時維持對 `--adversarial` foreach（舊式內嵌戳記）。修復新語義下 findings 檔無 `## 戳記` 導致實作派工永遠 FAIL 的死鎖。

<!-- claim-context: discussion -->
- 根因：B4 將 `--adversarial` 改為 findings 檔、`--reconcile` 為戳記載體，但 W3 仍 foreach adversarial 跑戳記檢。
- 配套：`gate_reconcile_complete_reconcile.md` 補 `## 戳記`（維持 fixture 5 exit 0；反例 ② 仍因 D-2 缺處置行 exit 1）。

## ASSUMPTIONS_VERIFIED

- 正例：`handoffs/2026-07-04-TGF-TODO-ADV-RECONCILE.md` 含 canonical 戳記 → W3 PASS。
- 反例：stub reconcile 對真實 adversarial → D-2 拒發 exit 1（早於 W3）。
- 舊式無 `--reconcile`：W3 仍 foreach adversarial（未回歸驗證單獨 case，fixture 1–3 無 reconcile 不涉及 W3）。

## TESTS_RUN

```bash
# ① 正例
GATE_DIR_OVERRIDE=/tmp/tgf-hotfix bash scripts/gate.sh dispatch --risk high \
  --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md \
  --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md \
  --adversarial 'handoffs/2026-07-04-TGF-TODO-ADV-CODEX.md,handoffs/2026-07-04-TGF-TODO-ADV-COMPOSER.md' \
  --reconcile handoffs/2026-07-04-TGF-TODO-ADV-RECONCILE.md \
  --intent t --facts-asked none-needed:t --review-role single-executor:n/a --template '跟過:t'
# RECONCILE-STAMP PASS → GATE PASS → exit 0

# ② 反例（同命令，stub reconcile）
GATE_DIR_OVERRIDE=/tmp/tgf-hotfix bash scripts/gate.sh dispatch --risk high \
  --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md \
  --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md \
  --adversarial 'handoffs/2026-07-04-TGF-TODO-ADV-CODEX.md,handoffs/2026-07-04-TGF-TODO-ADV-COMPOSER.md' \
  --reconcile tests/gate_fixtures/gate_reconcile_complete_reconcile.md \
  --intent t --facts-asked none-needed:t --review-role single-executor:n/a --template '跟過:t'
# ERROR: reconcile 缺 finding 處置行（D-2）→ exit 1

# ③ 5 gate fixture 矩陣
# fixture1–4 exit=1; fixture5 exit=0 → 1/1/1/1/0

# ④ 矩陣回歸
bash scripts/test_template_check.sh; echo $?
# MATRIX PASS → 0

# ⑤ 真 gate 低風險 smoke
bash scripts/gate.sh dispatch --intent "TGF-B4-hotfix smoke" --risk low \
  --facts-asked none-needed:tgf-b4-hotfix --review-role single-executor:n/a \
  --template "n/a:tgf-b4-hotfix-smoke"
# GATE PASS → exit 0
```

## FAILURES_SEEN

none

## SCOPE_CHANGES

- `tests/gate_fixtures/gate_reconcile_complete_reconcile.md`：補 `## 戳記` + APPROVED 行（新語義下 W3 檢 reconcile 單檔；不修則 fixture 5 由 0→1）。

## NUMERIC_OR_SCHEMA_IMPACT

none（gate 分流邏輯；未改 token/audit 簽發）

STATUS: DONE
