# VERDICTGATE B4 閉合確認輪（codex＋grok 各自重驗自己的 R1 findings）

brief-kind: closure
task-id: 20260911-VERDICTGATE-B4-REVIEW-R2
findings-round: R2

🔴 **這是閉合確認（closure），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套；禁在本 repo commit／push。**
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；末段三行機械塊只准值集；`CLOSED:` 只列**你自己家族**重驗後確認閉合之 ID（不得列他家）；**`STATUS: DONE` 逐字**。
🔴 隔離實驗之指令列與暫存路徑不得含任何委員家族名稱（`gate_check` 會誤判派工）。

## 你要做的事（各家只看自己的）
主委修法（commit 見 `git log -1`；收斂檔 `handoffs/reconcile/20260911-verdictgate-b4-review-r1/synth.md`）：
- **N1**（`CODEX-R1-P1-01`）：`synth_attribution_hook.sh` 之 `SYNTH_ATTR_MODULE` 覆寫只在 `GOVERNANCE_TEST_HARNESS=1` 生效；正式路徑固定 `scripts/_synth_attr.py`。重跑你的反例：`env -u GOVERNANCE_TEST_HARNESS SYNTH_ATTR_MODULE=<不存在> bash scripts/synth_attribution_hook.sh`（stdin JSON 指向掉 ID 之 synth）應 rc=2。
- **N2**（`CODEX-R1-P1-02`／`GROK-R1-P1-01`）：`_synth_attr.py` 封閉文法——token 整詞（`_token_whole`）；延後目標 `DEFER_TARGET_RE`＋單一目標＋說明只准 `（`／`(` 起；存在性 `_target_in_todo` 整詞。重跑你的 probe：`不採納`／`延後→備忘`／`延後→Task`／`延後→Task、9.9`／`延後→E-4、E-9`／`延後→E-4（理由`（TODO 含各子字串）皆須 rc=1；`延後→E-4（理由）` rc=0。
- **N3**（`CODEX-R1-P2-03`／`GROK-R1-P2-01`）：恆真測試已刪，改為真驅動兩支 bash 包裝（`test_41_hook_and_gate_wrappers_agree_on_complete_fixture`／`…_differ_only_on_draft_rows`）＋mutation M26（hook 改跑 gate 模式必紅）。請審是否真可證偽。
- 程序：本輪 synth 是新閘上線後第一份——主委寫入時被 hook 擋一次（處置欄含字面延後箭號被判延後處置，改措辭後過）。此「處置欄描述文字誤觸 token」是否為可接受之閘語意？（主委立場：是——處置欄只放處置，描述放群集欄。）

## 必答
1. 你的各條在修後是否閉合（各重跑反例＋附 rc）？
2. N2 封閉文法是否還有縫（多個延後箭號、`Task N.N` 後接 `.`、殘留 ID 含小寫）？
3. 可否收 B4？

## 交件形態
至少一個 canonical heading（零新 findings 用 sentinel `## <FAMILY>-R2-P3-00`）；末段三行機械塊；`STATUS: DONE`。

## 前提
fact-verified: 修後 `pytest tests/governance/test_verdictgate_p4.py` 28 passed；hook 7；debt_clear 30；mutation `handoffs/20260911-verdictgate-mutate-b4.py` 15/15 UNCOVERED=0（主委 2026-09-11）。
fact-verified: R1 synth 經新閘（hook＋`reconcile_cluster_attribution_check.sh --todo docs/VERDICTGATE_TODO.md`）rc=0 後清債；`debt_ledger --has-open` rc=0（派工後預期值: rc=1——本輪 OPEN，非 2）。
assumed: 你 R1 之 probe 腳本仍可重跑（/tmp 已清）⇒ 否證觀測：重建 probe 時行為與 R1 描述不同。／我跑了：**沒跑**（你的 probe 不在 repo）。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
