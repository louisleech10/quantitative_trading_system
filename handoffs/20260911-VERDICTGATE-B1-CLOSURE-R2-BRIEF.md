# VERDICTGATE B1 閉合確認輪（codex 重驗 CODEX-R1-P0-01）

brief-kind: closure
task-id: 20260911-VERDICTGATE-B1-REVIEW-R2
findings-round: R2

🔴 **這是閉合確認（closure），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套。**
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；末段機械裁決塊必填（`CLOSED:` 列你重驗後確認閉合之 ID）。

## 你要做的事
你 R1 提出 `CODEX-R1-P0-01`（cutoff 後 `committee_output` 有 sequence 無 `round_id` ⇒ 帳本 rc=2 ⇒ gate 拒發）。主委修法（commit 見 `git log -1`）：
- `scripts/audit_events.json`：四個新事件標 `round_scoped: false`；`committee_output.fields` 加可選 `round_id`。
- `scripts/_debt_ledger_core.py::build_rounds`：`round_scoped: false` 之事件跳過（仍計序號連續性）。
- `scripts/gate.sh register-output`：review／stamp 兩路皆帶該輪 `round_id`。
- 另修一條主委自查（K2）：你 R1 交件檔**漏寫 `STATUS: DONE`** ⇒ 自動註冊靜默跳過；現改「有 `STATUS: DONE` 或 `VERDICT:` 行即嘗試」。你的 R1 產出已由主委手動註冊（audit family=codex verdict=blocked）。

**重跑你的反例**（唯讀）：`bash scripts/debt_ledger.sh --has-open` 與 `--list` 對真 audit 須 rc∈{0,1}（不得 2）；`grep '"event": "committee_output"' .claude/gate/audit.log | grep '"sequence"'` 之列現在應含 `round_id`（本輪你自己的產出登記後可再驗）。閉合 ⇒ `CLOSED: CODEX-R1-P0-01`；未閉合 ⇒ `BLOCKED-BY:` 並寫 canonical finding `## CODEX-R2-P<x>-<NN>`。

## 必答
1. `round_scoped: false` 讓四事件不進 round 債務數學——是否有任何既有消費端（`debt_ledger --list`／`reconcile_build`／`verify_task_provenance.py`／`verification_claim_check.py`）反而**需要**它們有 round_id？實跑唯讀命令。
2. 你 R1 交件檔為何沒有 `STATUS: DONE`？（是 CLI 慣例把它印到 stdout 而非寫入檔？）這影響 K2 修法是否足夠。
3. 可否收 B1？

## 交件形態
至少一個 canonical heading（零 findings 用 sentinel `## CODEX-R2-P3-00`）；末段 `VERDICT:`／`BLOCKED-BY:`／`CLOSED:`；**請在檔內寫 `STATUS: DONE`**。

## 前提
fact-verified: 修後 `pytest tests/governance/test_verdictgate_p1.py tests/governance/test_registry_v2_shape.py tests/governance/test_debt_ledger.py` → 61 passed；mutation 12 條 UNCOVERED=0；真 audit `debt_ledger --has-open` rc=0（R1 債已清；派工後預期值: rc=1——本輪開債後為 OPEN，仍非 2）。
assumed: 無其他消費端依賴新四事件之 round_id（主委只 smoke 了 provenance／claim_check／reconcile_build --help）⇒ 否證觀測：必答 1 任一命令 rc=2。／我跑了：**部分**。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
