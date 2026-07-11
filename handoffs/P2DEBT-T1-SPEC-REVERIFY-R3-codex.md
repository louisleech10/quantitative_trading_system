# P2DEBT-T1 SPEC R3 Codex 單點閉合複驗
Task-id: p2debt-t1 | Date: 2026-07-11 | Reviewer: codex

## NEW-CODEX-R2-1 — CLOSED
- 原反例重跑：`grep -n 'pytest -k test_mutation_' scripts/mutation_probe_check.sh` → rc=0；stdout 為 L15 註解與 L74 echo 兩行，證實 R2 命令確實不精準。
- R3 修正版實跑：`grep -n '^echo "→ 跑 mutation 探針: pytest -k test_mutation_' scripts/mutation_probe_check.sh` → rc=0；唯一 stdout 為 `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"`。
- byte compare：從 R3 Task 1.2b receipt 抽出命令與 stdout 後比較 UTF-8 bytes，結果 `command_byte_equal=True`（98/98 bytes）、`stdout_byte_equal_excluding_terminal_lf=True`（62/62 bytes）。程序 raw stdout 為 63 bytes，唯一額外 byte 是正常行尾 `0a`；R3 Markdown 記錄的是不含行尾 LF 的可見 stdout。
- raw stdout hex：`37343a6563686f2022e2869220e8b791206d75746174696f6e20e68ea2e9879d3a20707974657374202d6b20746573745f6d75746174696f6e5f20242a220a`；R3 記錄 stdout hex 同前但不含末尾 `0a`。

## R2 → R3 spot-check
- `diff -u handoffs/P2DEBT-T1-SPEC-DRAFT-R2.md handoffs/P2DEBT-T1-SPEC-DRAFT-R3.md` 僅有兩個 hunk：Task 1.2b mutation receipt 單行修正，以及檔尾新增空行 + `R3-CLOSURE`。
- 除上述 targeted fix 與 closure 記錄外，R3 相對 R2 無其他內容變更。

## 結論
- `NEW-CODEX-R2-1` 已由可重放命令與 byte-level receipt 比對關閉；無新 finding。

RECONCILE-STAMP APPROVED (p2debt-t1 R3, codex, 2026-07-11)
Verdict: APPROVE
