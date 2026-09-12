# SPLITUNIFY D-001 閉合確認 R11（codex）
task-id: 20260911-SPLITUNIFY-X-REVIEW-R11
family: codex
findings-round: R11
SCOPE: 只讀 closure；未改 tracked 檔、未 commit/push、未跑 tests/governance 全套。

## CODEX-R11-P1-01
**斷言**: R10-P1-02 尚未閉合；D-001:69/76/132 採時間序往返，但 D-001:123 仍要求 frame-order `_local_ordinals_for_symbol(...) == row_index_local`，與新判準互斥，且 M-SU-D1-15 又要求該 helper 變異應紅。
**碼證**: 實跑 `split_per_symbol(..., purge_semantic="timedelta")` 於亂序時間 `[2h,0h,3h,1h]` rc=0，producer rows=`[1,3]`/`[0,2]`；時間序 `sorted_positions=[1,3,0,2]`、正確 local=`[0,1]` 往返為 True，但 helper 回 `[1,3]`，不等於 `[0,1]`。若照 :123 驗收，合法亂序輸入會被誤擋。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238:69,76,123,131-132,161；`momentum/core/contracts.py:504-519,656-692`。
必答1：R10-P1-01 的固定 universe 直接竄改 local ordinal 會改變指紋，入口重驗主張在此模型下成立；本 finding 不否定該局部結論。必答2：固定 index 下未找到碰撞；缺欄／空字串應在入口先 fail-closed（D-001:71,81-82），但實作尚未存在，故未宣稱 runtime coverage。必答3：正確亂序往返 True；正向位移 `[1,2]` 產生 `[3,0]` 必不等，能抓真正錯值；另一 symbol 若數值同為 `[0,1]` 會相等但語意已同值。必答4：SU-RESID-5 可延至 b8 後，因投影只讀 local；它仍是既有全框 consumer 風險。必答5：不可進實作，須先刪除 :123 舊判準並使 ASSERT／mutation 同向。

## CODEX-R11-P2-02
**斷言**: 時間序往返式未明定先驗 local ordinal 範圍；Python 負索引可使錯誤 `row_index_local` 通過「等值」attest，故「錯寫必不等」不是普遍成立。
**碼證**: 隔離探針 `sorted_positions=np.array([10,20,30]); row_index=np.array([30]); row_index_local=np.array([-1])` → `sorted_positions[row_index_local]=[30]`，比較為 True；同一探針正向位移 `[1,2]` 對 `[1,3]` 為 False。需在索引前以 `0 <= local < len(sorted_positions)`（並驗整數、唯一、時間序）fail-closed。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md:67,69,78-81,131；`momentum/core/split_preview.py:123-176` 的既有 positional guard 可供複用。
必答1：R10-P1-01 的指紋仍可抓固定 feature index 下的 local 變更；本 finding 是 producer attest predicate 的邊界缺口。必答2：固定 payload 下無位置碰撞實例，但負索引在入口前已令 roundtrip 相等，若不先做範圍閘即繞過。必答3：正向位移會紅；負值反例會通過；另一 symbol 的同值 local 不能證明來源，但不造成數值差異。必答4：SU-RESID-5 與此獨立；其延後不改變本 finding。必答5：需補明確範圍閘後才可 proceed。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF、CLAUDE、R11 brief、D-001、SPLITUNIFY TODO、template、R10 synth；中間網格 probe returned；亂序 timedelta producer 與 time-order/helper 對照已實跑。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238`；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/core/test_split_contract.py` → 83 passed；隔離 probes rc=0。
FAILURES_SEEN: 亂序 probe 首次以 epoch-ms 數字餵既有 contracts 正規化而得 OutOfBoundsDatetime；改用 Datetime 值後同一案例 rc=0；未跑 governance 全套。
SCOPE_CHANGES: 僅新增本交件檔；未改 tracked code/data、未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；review only，未改產品數值、schema、golden 或輸出大小。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r11-codex.md
TMP_CLEANUP: `find /tmp -maxdepth 1 -mindepth 1 -iname '*workdir*'` 無候選；已保留 `/tmp/claude-501`。
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238 task:20260911-SPLITUNIFY-X-REVIEW-R11
VERDICT: blocked
BLOCKED-BY: CODEX-R11-P1-01,CODEX-R11-P2-02
CLOSED:
STATUS: DONE
