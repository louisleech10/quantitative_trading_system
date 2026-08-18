# GAP-2a／2b SPEC adversarial 審查 R5（CODEX）

## Verdict：需修補後派工

## CODEX-R5-P0-01
**斷言**: N1 尚未完全閉合：失敗路徑的 `metadata.survivor_output` 仍被寫成只有 `{status, reason}`，與五鍵恆存在契約矛盾。
**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:211,214` 要求五鍵與三形狀驗證；`:213` 的 identity_missing／寫檔失敗字典只列兩鍵，無省略標記。反例：依該字面組出失敗 payload，`path`／`sha256`／`case_id` 不存在，違反 nullable 五鍵；`rg -n '五鍵恆存在|status:"computation_failed"|恰五鍵' ...` → 211、213、214。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca
[BLOCKING] 信心度=High。實作者可依 213 產生兩鍵失敗 payload，validator／前端將面對兩種 schema。修法：把 213 兩個 failure literal 改成完整五鍵（path/sha256=null、case_id 明確值），並保留 214 的 exact-key gate。

## CODEX-R5-P1-02
**斷言**: §V 對 OOM／並發測試自相矛盾，無法判定兩項是否為本輪必過 gate。
**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:224,273` 要求 budget receipt、atomic concurrent write 與 OOM count gate；`:278` 卻寫「已知不測：OOM／並發」。`rg -n '已知不測|並發寫|OOM 降載|peak RSS|n_regressions' ...` → 224、273、278。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca
[MAJOR] 信心度=High。若按 278 可跳過高風險 gate；若按 224/273 執行，驗收文件仍能被判定為未測。修法：刪除或改寫 278，明確列出 OOM count/peak-RSS receipt 與並發 atomic-write 的 pass/fail；資源上限需採已核准來源，不在實作端臆造。
必答1：N1 未閉合（CODEX-R5-P0-01）；N2 閉合（`:76` 唯一 `gap2_canonical_sha`、`:224` 200/200/n=20000 與 600 oracle、`:268-269` mutations、`:273` count gate）；N3 閉合（`:69` 已指 Task 1.0，`rg 'Task 3.1 之契約檔'` 無輸出）。
必答2：`bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`；五份 `bash scripts/reconcile_stamps_check.sh <synth>` → 全部 `PASS rc=0`；`rg -n 'reasons 加|reasons 增鍵|Task 3\.1 之契約檔' docs/GAP2_MARGINAL_IC_SPEC.md` → no output；closure/budget grep 命中 69、76、211、213、214、224、268、269、273、278，故上述兩矛盾成立。
必答3：不可進 TODO；BLOCKING=`CODEX-R5-P0-01`，另須修補 MAJOR=`CODEX-R5-P1-02`。

§1 必查：1 矛盾＝P0/P1；2 端到端＝P0；3 可測＝P0/P1；4 quant＝無新 finding；5 過度工程＝無；6 OOM/並行＝P1；7 cache＝無；8 API/型別＝P0；9 測試品質＝P0/P1；10 Agent 可執行性＝P0/P1；11 短命工＝無。
§0 facts：template PASS、五份 stamp PASS、SPEC hash `a7703a4761ca`、phase 依賴單調 B1→B2→B3→B4→B5 已實跑 grep；assumption：各批「可獨立綠」只能確認 SPEC-level 無 forward dependency，實作尚未存在故未宣稱已綠。
ASSUMPTIONS_VERIFIED: R4 N2/N3 grep closure、N1/N2 contradiction probes、五份 reconcile stamps、template check、B1→B5 dependency anchors。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` PASS rc=0；五次 `bash scripts/reconcile_stamps_check.sh <path>` PASS rc=0；定向 `rg` 命令輸出如上；同一 `scripts/completeness_check.sh` 以 `zsh` source、同參數執行 → `COMPLETENESS PASS(single)` rc=0。
FAILURES_SEEN: 字面 `bash scripts/completeness_check.sh --single ... --family codex` 入口被既有 OPEN-debt PreToolUse gate 擋在腳本外；等價同檔同參數入口 PASS rc=0。
SCOPE_CHANGES: 只新增本 review 檔；未改碼、SPEC、TODO、tests 或 data_cache；PreToolUse 阻擋紀錄自動 append 至既有 `.claude/gate/audit.log`，其他 dirty 保留。
NUMERIC_OR_SCHEMA_IMPACT: 無產品數值變更；指出 survivor failure schema 與 OOM/並發驗收文字矛盾。
TMP_CLEANUP: 收尾移除本輪 `/tmp` workdir；保留 `/tmp/claude-501`。
OUTPUT_FILE: handoffs/20260818-gap2-specadv-r5-codex.md
TASK_ID: 20260818-GAP2-X-REVIEW-R5
STATUS: DONE
