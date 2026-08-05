# GOVB0-B3-REVIEW — codex；受審 commit `18cfdd2`
## Verdict
需修補後派工；FINDINGS_COUNT: 5；BLOCKING: 3；出場判準未通過。
## §0 前提宣告
FACT-VERIFIED：`grep -c '^{' tests/governance/fixtures/gate_invariance_corpus.txt`=30；extract `--check`=OK rows=29、sha=`f4f54d…`；A 未刪條目。
FACT-VERIFIED：`pytest tests/governance/test_gate_lexical_contract.py -q`=8 passed、`test_gate_decision.py -q`=6 passed、`test_gate_deny_fields.py -q`=24 passed，均 rc=0。
FACT-VERIFIED：`pytest tests/governance -q`=751 passed/273.78s/rc=0；`RECONCILE-STAMP` composer/grok/codex 均 APPROVED；audit 大小/latency 依 brief OUT-OF-SCOPE 未稽核。
ASSUMED-攻擊結果：抽取器目前涵蓋現有 command-bearing TEST-2.* 轉向，未發現當前 TODO 漏抽；但 reverse-1 mutation 非真 mutation（CODEX-R2-P2-04）。11 契約各有 TP/TN（50 rows）成立。
## 逐項核對表
1a–1c 排除清單：fixture 可由 TODO 重現且 sidecar 一致；A=30；反向-2 對命中 A/B 的 flip 實測翻轉；反向-1 只有 tautological helper check，見 CODEX-R2-P2-04。
2a–2c fail-closed：11 個代表性真派工簡單向量皆 rc=2；但 quote-nested command substitution、quoted env assignment、>8KiB suffix 會放行，三條 BLOCKING。
3a–3f：11×TP/TN、26-row proto parity、heredoc FC/OK、11 mutation 均現有測試通過；合法雙 heredoc 第二 body 含命令字樣會誤擋，見 CODEX-R2-P2-05；B3 commit 另含未列入本 Task 的 scripts/tmp artifacts，作 scope note。
## CODEX-R1-P1-01
**斷言**: `echo "$(codex exec x)"` 與 `echo "`codex exec x`"` 是可執行真派工卻 ALLOW；**碼證**: `_gate_lex.sh:143-166,196-203,305-311` 對整個 quote span 把空白改 US；**來源摘要**: `scripts/_gate_lex.sh#86ffda54b321`; [BLOCKING] 信心度=High；修法：double-quote state 內對 `$()`/backtick 建 nested command scan；RECHECK：`GATE_DIR_OVERRIDE=$(mktemp -d) bash scripts/gate_check.sh <<<"$(jq -n --arg cmd 'echo "$(codex exec x)"' '{tool_name:"Bash",tool_input:{command:$cmd}}')"`，目前 rc=0，應 rc=2。
## CODEX-R1-P1-02
**斷言**: 合法 quoted env assignment 後的家族 CLI 被放行；**碼證**: `gate_check.sh:167-169` 只剝 `[A-Za-z0-9_./:@%+=,-]+`；`FOO="bar" codex exec x` 舊 snapshot rc=2、新 rc=0；**來源摘要**: `scripts/gate_check.sh#2ec2254dba3a`; [BLOCKING] 信心度=High；修法：quote-aware assignment-word tokenizer，保留 `$()` 防護且不漏掉引號值；RECHECK：以同一 payload 分別執行 `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` 與 `scripts/gate_check.sh`，期望 2/2。
## CODEX-R1-P1-03
**斷言**: 真派工位於第 8192 byte 後會被截斷而 ALLOW；**碼證**: `_gate_lex.sh:291-305` `raw` 只取前 8192；`x×9000; codex exec x` 舊 rc=2、新 rc=0；**來源摘要**: `scripts/_gate_lex.sh#86ffda54b321`; [BLOCKING] 信心度=High；修法：完整掃描，或超長時 fail-closed 並保留可證明的界線；RECHECK：`prefix=$(printf 'x%.0s' {1..9000}); cmd="$prefix; codex exec x"; payload=$(jq -n --arg cmd "$cmd" '{tool_name:"Bash",tool_input:{command:$cmd}}'); GATE_DIR_OVERRIDE=$(mktemp -d) bash scripts/gate_check.sh <<<"$payload"`，目前 rc=0，應 rc=2。
## CODEX-R2-P2-04
**斷言**: exclusion reverse-1 mutation 沒有驗證判定流程；**碼證**: `test_gate_deny_fields.py:530-557` 只對非 flip victim 再呼叫 `_flip_matches_command` 並 assert `hit is None`，未改 gate/test subject、未執行 altered `excluded` trace；**來源摘要**: `tests/governance/test_gate_deny_fields.py#e64635d078c5`; [MAJOR/non-blocking] 信心度=High；`pytest ... -k invariance_exclude_nonflip_mutation`=1 passed 只證明 helper；修法：真實注入 victim 後要求 mutation test 轉紅；RECHECK：該 pytest 應在移除 reverse-1 assertion 的 mutation 下 rc≠0。
## CODEX-R2-P2-05
**斷言**: 多 heredoc 的第二個 body 未被消耗，body 中的 `codex exec x` 被誤擋；**碼證**: `_gate_lex.sh:99-135` 找到第一個 `<<` 後即消耗其 body，未排程同一 header 的後續 delimiter；`cat <<A <<B\nbodyA\nA\ncodex exec x\nB\ntrue` 新 gate rc=2，shell heredoc 語意應 ALLOW；**來源摘要**: `scripts/_gate_lex.sh#86ffda54b321`; [MINOR] 信心度=High；修法：先收集 header 全部 heredoc delimiter 再按序消耗，補第二 body TP；RECHECK：上述 payload 應 rc=0，並加入反向 mutation。
## 出場判準核算
TESTS_RUN：extract check OK；lex 8、decision 6、deny 24、governance 751 全 rc=0；bash -n gate/lex rc=0；restore script rc=128（`.git/index.lock` 無權限），以 apply_patch 還原 golden inventory，`git status --short tests/golden/` 為空。FAILURES_SEEN：上述 3 BLOCKING＋1 MAJOR＋1 MINOR；SCOPE_CHANGES：無程式/測試/TODO/SPEC 修改，既有 workspace 變更保留；NUMERIC_OR_SCHEMA_IMPACT：無；OUTPUT: `handoffs/20260805-govb0-b3-review-codex.md`。
STATUS: DONE
