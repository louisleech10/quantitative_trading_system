# P2DEBT-T1 SPEC R2 Codex 閉合複驗
Task-id: p2debt-t1 | Date: 2026-07-11 | Reviewer: codex | 對方 re-verify 產出未讀

## 逐 finding receipt
- B-CODEX-1 — CLOSED。`template_check.sh spec canonical-missing-receipt.md` → rc=1，關鍵行 `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：raw_data.index 是 DatetimeIndex`。
- B-CODEX-1 正例 — CLOSED。同一 tmp 副本加 `FACT-RECEIPT: receipt-abc`後重跑 → rc=0，`TEMPLATE PASS`。R2 Task 1.2 負/正 fixture 已改 canonical 形狀。
- B-CODEX-2/RISK-HIT 負例 — CLOSED。`template_check.sh spec canonical-missing-risk-hit.md` → rc=1，stdout 含 `§RISK 缺 RISK-HIT`；R2 新函式固定 rc=1+訊息 oracle，移除 gate 會使測試 FAIL。
- B-CODEX-2/uppercase 負例 — CLOSED。`gate.sh dispatch ... --adversarial uppercase-verdict.md` → rc=1，`缺 Verdict 行 ...（D-1 拒發）`；R2 新函式固定 rc=1+訊息 oracle。
- B-CODEX-2/移除 receipt 負例 — CLOSED。與 B-CODEX-1 同一 DatetimeIndex 正/負對已實跑；移除正例 receipt 即轉 rc=1。
- M-CODEX-1 — CLOSED。`git blame -L 89,143 scripts/template_check.sh` 顯示 RISK-HIT/C3 為 `f5850c6`；`git blame -L 205,210 scripts/gate.sh` 顯示 D-1 為 `5407d49`，R2 歸因一致。
- M-CODEX-2 — CLOSED。R2 §V 已明載 D-1 只驗錨點、不解析 APPROVED/REJECTED；`Verdict: REJECTED` 非 ADV tmp 已進 reconcile 路徑（rc=1，非 D-1）。
- B 案機檢形狀 — CLOSED。依 R2 在 `docs/VERIFY_GATE_SPEC.md` tmp 副本加 `RISK-HIT: b` + 2×receipt，`template_check.sh spec` → rc=0，`TEMPLATE PASS`，非 stub 錨點。

## 新 finding
- NEW-CODEX-R2-1 — BLOCKING。R2 Task 1.2b 規定 `grep -n 'pytest -k test_mutation_' scripts/mutation_probe_check.sh` 卻記成只「印出 `74:→ 跑...`」；實跑 rc=0 同時印出 L15 與 `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"`，R2 receipt 遗漏一行且 L74 transcript 少 `echo "..."`。
- 可證實的精準命令 receipt：`grep -n '^echo "→ 跑 mutation 探針: pytest -k test_mutation_' scripts/mutation_probe_check.sh` → rc=0，唯一 stdout 為 `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"`。
- 影響：R2 會要求實作把不精確的「真實 FACT-RECEIPT」寫入生產 SPEC，違反本任務的 non-stub/實跑 receipt 要求；需小改 R2 命令與 stdout 後再 stamp。

Verdict: BLOCK — NEW-CODEX-R2-1：Task 1.2b mutation FACT-RECEIPT 與實際 grep stdout 不一致
