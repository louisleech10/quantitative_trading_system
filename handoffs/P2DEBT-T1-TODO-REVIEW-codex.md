# P2DEBT-T1 TODO R1 adversarial review — Codex

- 日期：2026-07-11；task-id：`p2debt-t1`
- 對照：`handoffs/P2DEBT-T1-SPEC-DRAFT-R3.md` → `handoffs/P2DEBT-T1-TODO-DRAFT-R1.md`

## Coverage receipts
- §P：Task 1.1/1.2/1.2b/1.3 分別落於 TODO L82–107/L111–138/L142–166/L170–185；內容、檔案、oracle 均逐項保留。
- §V 負例：①→1.2.5 (L124,207)；②→1.1.4 (L95,208)；③→1.2.2 (L121,209)；極性與字串 oracle 未軟化。
- §C：四檔 scope、禁 `scripts/`、禁弱斷言/skip、真實 production path、canonical fact-scope、前後快照、解耦均落於 L37–51，且各 Task 再列不可做。
- 結論：未發現 §P/§V/§C 遺漏或 scope creep；但驗收命令有下列 BLOCKING 失真。

## Spot-run receipts（read-only；pytest 禁 pyc/cache）
- `echo 'VERDICT: APPROVED' | grep -qE 'Verdict[[:space:]]*[:：]' ...` → `NO_MATCH`，exit 0。
- `grep -n 'Task)' scripts/gate_check.sh` → `37:  Task)`，exit 0。
- `grep -n '^echo "→ 跑 mutation 探針: pytest -k test_mutation_' scripts/mutation_probe_check.sh` → `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"`，exit 0。
- `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest ...::test_b5_spec_fact_receipt_missing_fails -v -p no:cacheprovider` → collected 1；現況按預期 FAIL（先報缺 RISK-HIT/C3，證明 node/命令真實）。
- `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` → exit 1；現況精確列缺 RISK-HIT + 2× FACT-RECEIPT。

## Findings
- **BLOCKING B1 (High)** TODO L151 的 `... | grep -q 'RISK-HIT'` 極性反了：在已知壞基線精確實跑竟 exit 0；修好後因錯誤字串消失反而 exit 1。改成 fail-on-presence 的可執行命令（例如 `! ... | grep -q ...`）或只用完整 checker exit 0。
- **BLOCKING B2 (High)** TODO L154、L235 的 `bash ...; echo $?` 會遮蔽 checker exit；精確實跑顯示 checker FAIL/印 `1`，但整體命令 exit 0。驗收 gate 必直接保留 checker 非零（或先存 rc、印出後 `exit "$rc"`）。
- **BLOCKING B3 (High)** TODO L46/L199/L222–228 要求「派工前快照 vs 完工後 diff」，卻未給 snapshot 取得物、識別碼或可執行比較命令；L199 只寫 `git diff --name-only（相對派工前快照）`，冷啟動執行端仍須重造 gate，且可能退化成 SPEC 明禁的全域 dirty-tree diff。補明確 pre-snapshot receipt + post-compare 命令與四檔 whitelist oracle。
- **MINOR M1 (High)** Phase Gate L193–195 混用 bare `pytest`，其餘閉合命令用 `venv/bin/python -m pytest`；統一成專案 venv，避免 cold-start PATH 差異。

未附 `RECONCILE-STAMP APPROVED`：B1–B3 修補並重跑後才可核可。
Verdict: BLOCK — 驗收命令有反向判定、exit masking，且 scope snapshot gate 不可直接執行
