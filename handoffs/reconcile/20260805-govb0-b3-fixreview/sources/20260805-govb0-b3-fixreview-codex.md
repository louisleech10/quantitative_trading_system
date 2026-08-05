# GOVB0-B3-FIXREVIEW — codex
## Verdict: 需修補後重審 — FINDINGS_COUNT: 4; BLOCKING: 2
## 被當成事實的未驗證假設（§0）
8192 上限、正常超長指令發生率與「C4 是 true mutation」均未由現有證據證成；RECONCILE-STAMP 三枚均已 APPROVED。
## CODEX-R14-P0-01
**斷言**: `gate(_check)?.sh` 任意位置子字串排除是真繞道，不能接受為「擋意外不防蓄意」邊界；應只豁免整條 gate invocation。
**碼證**: `scripts/gate_check.sh:211-216`；無 token 獨立 probe `codex exec x; echo scripts/gate.sh`、comment、長前綴 chain、`scripts/gate_check.sh` 均 `rc=0`，裸 `codex exec x` `rc=2`。
**來源摘要**: scripts/gate_check.sh#c680a558d851；[BLOCKING] 信心度=High；修法建議為解析完整命令段，僅整條命令為 gate invocation 時排除。
## CODEX-R14-P0-02
**斷言**: `_max_lex=8192` 對所有超長命令 blanket fail-closed，沒有量測或規格依據，將 B-15 的誤擋摩擦換成未量測的新誤擋；需先修正。
**碼證**: `_gate_lex.sh:355,362-366`；`echo`+8200 字元新版 `rc=2`、pre-Phase2 `rc=0`；4,000,048-byte stdin `rc=2`、3,911ms；audit 718 個 gate_deny JSON 僅 51 有 cmd_head、667 無完整 command，無法導出發生率。
**來源摘要**: scripts/_gate_lex.sh#f54c3baad924；docs/GOVB0_FRICTION_TODO.md#37d1c0067780；[BLOCKING] 信心度=High；修法建議為完整輸入的 O(n) 掃描，無一般逃生口。
## CODEX-R14-P2-03
**斷言**: C4 測試不是 brief 要求的 true mutation；它只在同一測試內建立 `poisoned` Python list，未複製/執行 altered subject，因此移除新增斷言可維持綠燈。
**碼證**: `test_gate_deny_fields.py:590-654` 只有 `_reverse1_holds()`、list 注入與 `pytest.raises`；targeted test `1 passed`，沒有 before/after altered-test rc 對照。
**來源摘要**: tests/governance/test_gate_deny_fields.py#03bbf7630df2；[MAJOR/non-blocking] 信心度=High；修法建議為隔離副本移除 C4 修法並實跑同一驗收測試，確認 rc 由 pass 轉 fail。
## CODEX-R14-P2-04
**斷言**: 實作端就地改寫 `Internal Frozen` TODO 違反文件自身修訂程序；C5 選 (a) 並非 brief 允許的選項。
**碼證**: `docs/GOVB0_FRICTION_TODO.md:3,10-11` 明定 Frozen 且須走延伸檔不得就地改；工作區 diff 在 line 338 新增 HTML comment。
**來源摘要**: docs/GOVB0_FRICTION_TODO.md#37d1c0067780；[MAJOR/non-blocking] 信心度=High；修法建議為把決策記錄移至 amendment/extension artifact，TODO 就地變更由主委另行處置。
## 複核結果
目標1：1a `rc=2`；1b 第二次獨立 latency `cold_ms=72.8, second_ms=72.1, rc=0`（首次 108.8/128.2 未過，門檻仍 `<100ms`）；1c `rc=2, 3,911ms`；1d C2=`2/2/2/0`；1e C3=`2/2/0/0`；1f C4 true before/after 未證；1g C5/8 rows targeted checks 綠。
目標2：2a 刪除僅 C4 舊恆真 mutation block；2b enum/diff 未變；2c corpus A diff=0、兩 SHA=`b45fff972a9f`；2d `python3 scripts/extract_phase2_expected_flips.py --check` `rc=0`, `rows=37`，8 maintain rows 均機械產生。目標3：不可接受；TODO 應走延伸檔，非就地 HTML comment。
## 出場判準核算
4 findings ≤5，但 BLOCKING=2；B3 未通過，不應進 B4。C6、B4+、SPEC/TODO 重開、audit 封存/大小及措辭均 OUT-OF-SCOPE。
ASSUMPTIONS_VERIFIED: 獨立 probes、C2/C3/C1 targeted tests、C5/差集檢查與三枚 APPROVED stamp 已實跑；C4 true mutation 與 8192 發生率未驗證。
TESTS_RUN: `pytest tests/governance -q` → 759 passed rc=0；`pytest tests/governance/test_gate_decision.py -q` → 13 passed；`pytest tests/governance/test_gate_lexical_contract.py -q` → 8 passed；`--check` rc=0。
FAILURES_SEEN: latency 首跑 cold=108.8ms/second=128.2ms，重跑通過；`restore_golden_inventory.sh` rc=128，sandbox 禁止建立 `.git/index.lock`，inventory `git diff --quiet` rc=0；一條含 `claude-501`+`find -print` 的確認命令被既有 gate 誤擋，已拆分重跑。
SCOPE_CHANGES: 本 agent 未改受審碼、測試、TODO、SPEC；產出 `handoffs/20260805-govb0-b3-fixreview-codex.md`；清理兩個本任務 temp workdir，保留 `/private/tmp/claude-501`。 NUMERIC_OR_SCHEMA_IMPACT: none。
STATUS: DONE
