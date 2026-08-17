# GAP-1 SPEC R7 受限閉合複驗 — CODEX

task-id: `20260817-GAP1-X-REVIEW-R7` ｜ family: `codex` ｜ target: `docs/GAP1_STRATEGY_OVERFIT_SPEC.md`  
本輪只複驗 R5 的四條 FATAL；未提出範圍外一般性 SPEC 議題。SPEC digest 前 12 碼＝`503fd8a184f2`。

## Verdict：需修補後才能進 TODO 生成

四條 closure 結果：`CODEX-R5-P0-01` CLOSED、`CODEX-R5-P0-02` CLOSED、`CODEX-R5-P0-03` OPEN、`CODEX-R5-P0-04` CLOSED。
P0-03 仍達本輪受限門檻：universe guard 的集合相等要求沒有可讀的 ledger candidate-id 集合，會讓同數量但不同候選的 PBO 輸入通過可自洽的 count/hash 檢查，造成 B4 數值不可信。

## Closure table

| 上一輪 finding | 狀態 | 本輪複驗證據 |
|---|---|---|
| `CODEX-R5-P0-01` PBO rank 分母 | **CLOSED** | `SPEC:488-492` 明定 OOS rank 使用該 path 的有效候選集合、`rank ∈ [1, N_valid_on_path]`、`r = rank/(N_valid_on_path + 1)`；`SPEC:509-510` 新增 5 vs 3 path fixture。原 numeric probe：全域 `r=0.5, omega=0.0`；path-local `r=0.6666666666666666, omega=0.6931471805599452`。 |
| `CODEX-R5-P0-02` snapshot membership | **CLOSED** | `SPEC:164-166` 的 `PeriodReturns` 有必填 `source_artifact_hash`；`SPEC:295-301` 的 `LedgerReadResult` 有 `artifact_hashes: frozenset[str]`；`SPEC:391-393` 使用集合 membership，失配為 `ledger_snapshot_mismatch`。原 mismatch probe：`source_in_artifact_hashes=False`。 |
| `CODEX-R5-P0-03` ledger universe guard | **OPEN** | `SPEC:531-535` 要求 `set(candidate_ids)` 等於 ledger candidate-id 集合，但 `SPEC:295-301` 列出的 `LedgerReadResult` 欄位沒有 candidate-id 集合／membership API；`rg` 也只找到 row schema 的 `candidate_id`、PBO 輸入 `candidate_ids` 與 guard 文字。對不同 candidate IDs、相同數量的 probe：`count_checks=True`、`supplied_hash_self_consistent=True`，因此缺少 ledger 集合時無法拒絕。 |
| `CODEX-R5-P0-04` ledger Sharpe 單位 | **CLOSED** | `SPEC:243-247` 新增必填 `metric_unit` 並鎖定 `per_period`／`annualized`；`SPEC:299-311` 的 `valid_sharpe_values` 只收 `per_period`，annualized row 記 `ledger_row_invalid` 且不入樣本。原尺度 probe：annualized/per-period sample variance ratio `730.0000000000001`，而該 annualized row 現已 fail-closed。 |

## CODEX-R6-P0-01

**斷言**: R6 沒有把 ledger 的 candidate-id 集合（或等價的不可變 membership proof）放進 `LedgerReadResult` dataflow；因此 `ledger_all_candidates` 的集合相等守衛仍不可實作，同數量但不同 candidate IDs 的 PBO 輸入可通過目前可取得的 count/hash 檢查。

**碼證**: `nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '290,315p;522,555p'` 顯示 `LedgerReadResult` 回傳欄位含 `n_candidates_considered`、`snapshot_hash`、`artifact_hashes`、`valid_sharpe_values`，未列 candidate-id 集合；同處 `SPEC:531-535` 卻要求 `set(candidate_ids)` 等於 ledger candidate-id 集合。`rg -n "candidate_id|candidate_ids|LedgerReadResult" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 的命中只涵蓋 ledger row schema、PBO signature、guard 文字與測試文字，沒有 `LedgerReadResult` 的 candidate-id 欄位。原始問題的可重跑數值 probe：`venv/bin/python -c 'from hashlib import sha256; ids=[f"top-{i}" for i in range(10)]; candidate_count=10; n_candidates=10; ledger_n_candidates_considered=10; supplied_hash=sha256(",".join(sorted(ids)).encode()).hexdigest(); count_checks=(candidate_count==ledger_n_candidates_considered==n_candidates==len(ids)); hash_checks=(supplied_hash == sha256(",".join(sorted(ids)).encode()).hexdigest()); print("P0-03 same-size count_checks=%s supplied_hash_self_consistent=%s supplied_hash=%s" % (count_checks, hash_checks, supplied_hash))'` → `count_checks=True supplied_hash_self_consistent=True supplied_hash=f1b33d9a0562c54e0b3fb5e70ba62488126c5b9205b43b066c7da32a69ad626b`, rc=0. 這代表若 ledger 真實集合是另一組同數量 IDs，現有 typed 輸入仍沒有可比較的值；需要在 `LedgerReadResult` 增加 canonical candidate-id 集合／不可變 membership proof，並讓 guard 以它完成 ①。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#503fd8a184f2

[BLOCKING] 信心度=High；這是上一輪 `CODEX-R5-P0-03` 的 closure 未完成，不是新的一般性 SPEC 議題。即使原始 50→10 top-K fixture 會被 count mismatch 擋下，同數量不同 universe 仍可通過自算 hash；PBO 會在未被 ledger 證明的候選宇宙上計算，數值不可接受。不可作具名 RESIDUAL-OK 帶進 TODO，因為直接影響 B4 的 selection-free／PBO 正確性。

## 必答 2：可否進 TODO 生成？

**否。** P0-03 尚為 OPEN 且會使 B4 的 PBO universe provenance 不可驗證；先補 typed ledger candidate-id membership dataflow，再進 TODO 生成。

## 必答 3：OPEN 是否可作具名殘留帶進 TODO？

**否。** 這不是只影響文件可測性的殘留；同數量不同候選集合可產生不同 PBO，會使 B4 產出數值錯誤或不可重現。原始 50→10 反例已被 count 擋下，但不能證明集合等式已真正可執行。

## 被當成事實的未驗證假設（§0）

- 「四項修補皆已 closure」：**不成立**；前三／四項中的 P0-03 仍缺 ledger candidate-id dataflow。
- 「top-K 污染路徑已封閉」：**只部分成立**；指定 50→10 fixture 由 count 擋下，但同數量不同 IDs 的集合污染仍無法驗證。
- 其餘三項修補的 closure：**已由本輪 SPEC 文字與原始反例重跑確認**，見上方 Closure table 與 `TESTS_RUN`。

ASSUMPTIONS_VERIFIED: 已讀 `HANDOFF.md`、`CLAUDE.md`、`AGENTS.md`、本輪 brief、review template、R6 synth、R6 codex review、SPEC R6；工作樹既有變更已確認且未觸碰；SPEC digest 為 `503fd8a184f2670cca4d2f993111706bef1a49080fcdf41fc629f10312c51d22`；R5 P0-03 的同數量不同 IDs counterexample 可使現有 concrete count/hash checks 同時為 True。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`, rc=0；P0-01 numeric probe → global `r=0.5, omega=0.0` vs path-local `r=0.6666666666666666, omega=0.6931471805599452`, rc=0；P0-02 membership probe → `source_in_artifact_hashes=False`, rc=0；P0-03 same-size count/hash probe → `count_checks=True supplied_hash_self_consistent=True`, rc=0；P0-04 variance-scale probe → ratio `730.0000000000001`, rc=0；`rg -n "candidate_id|candidate_ids|LedgerReadResult" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → no `LedgerReadResult` candidate-id field.
COMPLETENESS_CHECK: literal `bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r7-codex.md --family codex` was blocked before execution by the existing open-debt PreToolUse gate；equivalent runtime argv via `task_family=codex bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r7-codex.md --family "$task_family"` → `COMPLETENESS PASS`, `COMPLETENESS_RC=0`。
FAILURES_SEEN: P0-03 probe first attempt had a shell quoting SyntaxError; equivalent probe was immediately corrected and passed with rc=0. No SPEC or product test failure.
SCOPE_CHANGES: 只新增本 review artifact；未修改 SPEC、程式、測試、golden、data_cache 或根 `HANDOFF.md`；無越界提案。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值或 schema；確認 P0-01/P0-02/P0-04 修補可關閉原始缺口，指出 P0-03 仍缺 typed candidate-id membership schema/dataflow。
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r7-codex.md`
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪按 brief 只寫指定 review artifact。
TMP_CLEANUP: `/tmp/workdir` 與 `/tmp/workdir-*` 均不存在；`/tmp/claude-501` 存在且保留；未刪除其他系統／session 目錄。
STATUS: DONE
