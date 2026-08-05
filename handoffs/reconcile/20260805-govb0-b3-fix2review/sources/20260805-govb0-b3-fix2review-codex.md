# GOVB0-B3-FIX2REVIEW — codex 確認審查
## Verdict：有根本缺陷；B3 不通過，觸發 epic 收斂斷路器。
FINDINGS_COUNT: 2；BLOCKING=2；NEW-DEFECT-INTRODUCED=2。
## CODEX-R15-P0-01
**斷言**: D-1 的 self-gate 豁免仍以首行 grep 命中，跨行後的真派工可被放行。
**碼證**: `scripts/_gate_lex.sh:351-360`；`bash scripts/gate_check.sh` 對 `bash scripts/gate.sh\ncodex exec hi` 與 `bash scripts/gate_check.sh\ngrok -m x -p y` 均實測 `rc=0`；分號同型向量 `rc=2`。RECHECK 可用 `jq -nc --arg c $'bash scripts/gate.sh\ncodex exec hi' '{tool_name:"Bash",tool_input:{command:$c}}'` 產 payload 後以 here-string 直接呼叫 gate。
**來源摘要**: `scripts/_gate_lex.sh#debe1484a7e5` / `scripts/gate_check.sh#b454a55ea513`
[BLOCKING|P0] 信心度=High；`NEW-DEFECT-INTRODUCED`。`grep` 逐行處理使 `\n` 未被 `[... ]` 檢查，後續正則又非全字串錨定；修法方向是以跨行狀態機確認整體單一簡單命令後才豁免。
## CODEX-R15-P0-02
**斷言**: D-2 移除 8192 硬頂後，含引號/特殊字元的 4MB 路徑仍非 O(n)，且對應 harmless-oversize 測試缺真 mutation 牙齒。
**碼證**: `scripts/_gate_lex.sh:76-81,143-180,382-390` 以 awk 全量字串反覆拼接；4,000,057-byte 合法 JSON `echo "<4MB>"` 經 `timeout 30 ... bash scripts/gate_check.sh < file` 實測 `rc=124`、`real 30.01s`；plain 4MB tail 向量則 `4,000,063B rc=2 real 5.65s`。C1 hard-cap mutant 對 `echo`+8200B 實測 `rc=0`，所以 `test_21_d2_harmless_oversize_allows` 仍會綠。
**來源摘要**: `scripts/_gate_lex.sh#debe1484a7e5` / `tests/governance/test_gate_decision.py#5d5fe4fb59e2`
[BLOCKING|P0] 信心度=High；`NEW-DEFECT-INTRODUCED`。原本前綴截斷遮住此 quadratic path，現行修法把任意長特殊輸入送入非 O(n) 前處理；需重審 C1 設計並補 quoted/特殊字元大輸入與 harmless case 的逐測試 mutation。
## 1a–1i 判定
1a FAIL/BLOCKING/NEW：跨行 self-gate bypass；1b PASS：`pytest ...::test_20_proto_parity_26 -q` 與 targeted suite 綠；1c FAIL/BLOCKING：quoted 4MB `rc=124`；1d PASS（門檻未動，`test_debt_gate` 三次 rc=0，canonical cold/second=`78.8/73.9`,`98.4/79.4`,`78.1/79.8ms`；raw diagnostic 曾 `120.8ms`）；1e PASS：plain 4MB tail `rc=2,5.65s`；1f PASS：C4 subject `ok rc=0`、mutant `rc=1`，`pytest ...::test_01_invariance_exclude_nonflip_mutation -q` rc=0；1g PASS：`extract_phase2_expected_flips.py --check` rc=0、TODO diff rc=0；1h FAIL：四新增 oversize/D-1 tests 中 harmless case 在對應 C1 mutant 仍 rc=0；1i FAIL：新跨行 fail-open 即 1a。
## §0 假設攻擊結果
D-2 O(n)：plain path 通過但一般特殊 path 被 30s timeout 證偽；D-3 C4：隔離 subject 真實執行前後 `0/1` 已驗；四條新增測試逐條 mutation：suffix、gate-substr、4MB-tail 可轉紅，harmless-oversize 不轉紅。
## 出場判準核算
findings=2（≤3）；BLOCKING=2（要求 0）；`NEW-DEFECT-INTRODUCED` 存在 ⇒ 不通過，不進 B4，交 epic committee 重審 C1。
## 被當成事實的未驗證假設（§0）
D-2 O(n)（未通過 quoted 4MB）；D-3 true mutation（已通過）；新增四測逐條 mutation（至少 harmless case 未通過）。
ASSUMPTIONS_VERIFIED: `pytest` targeted 50 passed；latency node 3 次皆 rc=0；plain/quoted 4MB、跨行 probe、C4 before/after、D4 check 均有上列實跑 receipt。
TESTS_RUN: `pytest tests/governance/test_gate_decision.py tests/governance/test_gate_lexical_contract.py tests/governance/test_gate_deny_fields.py -q` → 50 passed；latency node 3 runs → rc=0；`python3 scripts/extract_phase2_expected_flips.py --check` → OK rows=37 rc=0；D3 subject → 0/1；4MB probes → harmless 0, tail 2, quoted timeout 124。
FAILURES_SEEN: D-1 跨行 self-gate 放行；D-2 quoted 4MB timeout；D2 harmless oversize mutation remains green；均未修復（review 禁改碼）。
SCOPE_CHANGES: none；未改 tracked code/test/SPEC/TODO，未 commit/push，未碰 `data_cache/`。
NUMERIC_OR_SCHEMA_IMPACT: review only；未修改輸出 schema/數值/檔案大小。
OUTPUT_FILE: `handoffs/20260805-govb0-b3-fix2review-codex.md`。
TMP_CLEANUP: 本輪產物已清理；`/tmp/claude-501` 保留。
STATUS: BLOCKED — NEW-DEFECT-INTRODUCED，D-1/D-2 fail-open/performance 缺口需 epic committee 重審。
