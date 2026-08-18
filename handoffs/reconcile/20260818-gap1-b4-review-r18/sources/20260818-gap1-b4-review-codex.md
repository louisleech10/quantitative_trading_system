# GAP-1 B4 code review｜family=codex｜task-id=20260818-GAP1-B4-REVIEW-R18
Review target: commit `763b9d56`; review scope follows `handoffs/20260818-gap1-b4-review-BRIEF.md`; no code/SPEC/TODO/commit/push changes.
Verdict: 需修補後收工；無 P0；3 個 P1、3 個 P2；A1-23 #3/#4/#5 可接受，#6/#8/#9 需處置如下。
段 A：4.1 CSCV lazy/budget/boundary、4.3 provenance/type/三項守衛、2.4 W1/W4/rc=0/1/2 基線符合；4.2 的 exclusions 與 rank denominator 不符合字面/原典。
段 B：向量化 lock 未覆蓋近常數；W3 passthrough 非封閉；ledger 靜態化今日等價；len mismatch 死分支因守衛先跑可接受；golden hash、完整 mu、provenance 可接受；OOS rank 母體與 exclusions 不可接受；雙冠測試為廉價綠燈。
段 C：探針 20/20 皆 rc=1 且 assertion FAILED，baseline/post-restore 各 266 passed；wiring 六 mutation 與 baseline 均過，但未覆蓋下列 W2/W3/雙冠/近常數反例。
段 D：`C(12,6)=924`、`C(14,7)=3432`、`C(16,8)=12870`；`1205/12` 塊為 `[101]*5+[100]*7`；`16,2000` 超 20M；golden 0.6483/0.0000/0.5411 與 `mu=0.00010684346079267205` 均由既有 gate/receipt 鎖定；原典 Algorithm 2.3 使用全 N rank。
## CODEX-R18-P1-01
**斷言**：champion OOS 非有限時，同一候選被 `n_path_exclusions` 重複計數，審計欄位與 TODO「每候選每 path 一次」不符。 **碼證**：`pbo.py:213-218` 先以 `len(path_valid)-len(oos_valid)` 計入，再因 `not math.isfinite(oos_all[pos[champ]])` 額外 `n_excl += 1`；`test_pbo.py:190-206` 只斷言 `>=1`。 **來源摘要**：`momentum/Analysis/strategy_validation/pbo.py#4b8fae455bda8a7324c9fb9403f9f4b7a6bc1c0f`；`docs/GAP1_STRATEGY_OVERFIT_TODO.md#1b5b3d3609caa876648e52399b15fa27491431f7`。
## CODEX-R18-P1-02
**斷言**：實作把 OOS 非有限的其他候選從 rank 母體刪除並用 `len(oos_valid)+1`，改變 Frozen TODO 的 `len(valid_cols)+1` 及 Algorithm 2.3 的全 N 母體，會改變 PBO。 **碼證**：`pbo.py:213-224` 建 `oos_valid`、`oos_vals` 後以 `len(oos_valid)+1` 計 `r`；TODO `:398-406` 要求 `oos_metrics` 對 `valid_cols` 且 `r=rank/(len(valid_cols)+1)`，原典 Algorithm 2.3 PDF pp.10-11 明定 OOS rank 為 N strategies 且 `N+1`。 **來源摘要**：`momentum/Analysis/strategy_validation/pbo.py#4b8fae455bda8a7324c9fb9403f9f4b7a6bc1c0f`；`docs/GAP1_STRATEGY_OVERFIT_TODO.md#1b5b3d3609caa876648e52399b15fa27491431f7`；[Bailey et al. Algorithm 2.3](https://www.carmamaths.org/resources/jon/backtest2.pdf)#4b0d8f9e3d7a。
## CODEX-R18-P1-03
**斷言**：W3 的 passthrough 判定可被非 reason 欄位/變數繞過 fail-closed gate，且同檔頂層常數替換忽略區域遮蔽。 **碼證**：`strategy_wiring_check.py:123-139` 對任意 `Attribute` 放行、對任意字串 `Subscript` 放行、`.get` 不核對第一參數；`:199-214` 將頂層常數套用到所有 scope。反例形態 `reason=obj.payload`、`reason=obj["dynamic_key"]`、局部 f-string 變數遮蔽同名頂層常數均不會列 `[unresolved]`；現有六 mutation 未覆蓋。 **來源摘要**：`scripts/strategy_wiring_check.py#517578808275821cc6bc59b7ee41f90137a49127`；`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#56cde5ed7a83ca32fc9e1ceb2871ff59513e0077`。
## CODEX-R18-P2-04
**斷言**：④b 雙冠測試沒有證明取最小原始索引，是廉價綠燈。 **碼證**：`test_pbo.py:170-187` 只斷言 `got.n_paths_used==2`；兩個 `rankdata` 斷言作用於獨立常數陣列，沒有讀 `got.logits_*`，錯取欄 3 仍可全綠。 **來源摘要**：`tests/momentum/Analysis/strategy_validation/test_pbo.py#4211eb848533efcff9313afeb0cc2bed01609c64`；TODO `:417` 的 ④b。
## CODEX-R18-P2-05
**斷言**：向量化 Sharpe 等價鎖不足以支持替代字面 `compute_sharpe`，近常數欄的 reduction/精確 std 差異可能改變 champion 或退化判定。 **碼證**：`pbo.py:136-153` 用 `sub.mean(axis=0)/sub.std(axis=0)`，參考 `_metric` `:129-133` 走 `compute_sharpe`；`test_pbo.py:126-140` 只測隨機欄、精確常數 `0.5`、NaN、n<2，沒有 A1-23 指出的近常數 case。 **來源摘要**：`momentum/Analysis/strategy_validation/pbo.py#4b8fae455bda8a7324c9fb9403f9f4b7a6bc1c0f`；`tests/momentum/Analysis/strategy_validation/test_pbo.py#4211eb848533efcff9313afeb0cc2bed01609c64`。
## CODEX-R18-P2-06
**斷言**：W2 將任意字串 `ast.Constant` 當作 reason 已接線，未阻擋只存在於 docstring/未使用常數的死枚舉。 **碼證**：`strategy_wiring_check.py:187-188` 收集所有字串常數，`:280-282` 只檢查每個契約 reason 是否在集合；可新增 `UNUSED="new_reason"` 或 docstring 後仍 rc=0，現有 `test_dead_enum_reason_is_red` 只測完全不存在。 **來源摘要**：`scripts/strategy_wiring_check.py#517578808275821cc6bc59b7ee41f90137a49127`；TODO `:445-457` 要求「死枚舉即紅」。
ASSUMPTIONS_VERIFIED: `git show 763b9d56 --stat` matches B4 target; `bash scripts/gap1_b1_mutation_probe.sh` baseline/post-restore 266 passed and 20/20 mutants rc=1 with FAILED>=1; `bash -n scripts/strategy_wiring_check.sh` rc=0; `bash scripts/strategy_wiring_check.sh` rc=0 with W1..W4; target files `git diff --quiet` rc=0; `mu`/golden values and numeric counts checked from target tests/golden and brief receipt.
TESTS_RUN: `bash scripts/gap1_b1_mutation_probe.sh` = rc=0; `bash -n scripts/strategy_wiring_check.sh` = rc=0; `bash scripts/strategy_wiring_check.sh` = rc=0; brief fact-verified `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` = 269 passed.
FAILURES_SEEN: ad hoc direct Python counterexample was blocked by the repository PreToolUse debt gate; no source mutation remained; no finding depends on that unrun probe.
SCOPE_CHANGES: only `handoffs/20260818-gap1-b4-review-codex.md` added; no code/SPEC/TODO/data_cache change, no commit/push; pre-existing dirty files preserved.
NUMERIC_OR_SCHEMA_IMPACT: reviewer made no changes; findings P1-01/P1-02 concern PBO audit counter and rank denominator semantics; no output file/schema was changed.
HANDOFF_OUTPUT: `handoffs/20260818-gap1-b4-review-codex.md`
STATUS: DONE
