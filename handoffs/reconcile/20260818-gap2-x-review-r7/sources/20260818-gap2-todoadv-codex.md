# GAP-2a／2b TODO adversarial review R7（codex）
## CODEX-R7-P1-01
**斷言**: B4 目前沒有可直接落地的 call graph 同時傳入 typed `fit_scope` 並讓 persist 讀到 stage6b/event cache：`_stage7_report` 在建 `_ic_cache` 前呼叫 persist，fallback 又遞迴呼叫 `analyze()` 未傳 `fit_scope`。
**碼證**: VERIFY `rg -n 'self\._persist_outputs|self\._ic_cache = \{' momentum/Analysis/ic_filter_orchestrator.py` → `3432` 早於 `3449`；`nl -ba ...:1065-1117` → fallback 於 `1109` 遞迴 `analyze()`；**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22
[MAJOR] 信心度=High；依 TODO 201–203、220 的既定介面會先遇到空 cache／缺 fit scope，或重算／重複 persist；需補明確的 cache 建立順序與 fallback 內部 typed 傳遞點。
## CODEX-R7-P1-02
**斷言**: `build_survivor_output` 的宣告參數與 B4 caller 不足以組出 required contract：簽名漏列後文要求的 `summary_by_feature`，現有 persist 路徑也未傳 `features_path`、label hash、event identity 或可供 report-ref 驗證的已存在 report path；fixture `case_id` 為 null 且現行 fallback 為 `ic_gatekeeper`。
**碼證**: VERIFY `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:151-155,217-222`；`nl -ba momentum/Analysis/ic_filter_orchestrator.py:3377-3464,3789-3852`；`jq -c '{case_id:(.case_id//null),symbol,timeframe}' tests/golden/la0/inputs/*_meta.json` → `case_id:null`；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；tests/momentum/helpers/ichc_run.py#1f41f9e5e8d8
[MAJOR] 信心度=High；agent 必須自行改變 signature、state 或 persist ordering 才能取得 provenance／row identity／IC snapshot，且 golden 的 `case_id=gap2_golden` 沒有現有 caller 入口；需在 TODO 明列資料 owner、report 兩階段寫入與固定 case_id 來源。
## CODEX-R7-P1-03
**斷言**: B4 benchmark 只有 `n_regressions==600` 與 receipt 存在，沒有 wall-time／RSS 的通過上限，因此可在資源失控時仍綠，不能證明 §V 宣稱的 OOM／跨 tier 保護。
**碼證**: VERIFY `rg -n 'n_regressions|receipt 只記錄不設閾值|資源上限不由' docs/GAP2_MARGINAL_IC_TODO.md docs/GAP2_MARGINAL_IC_SPEC.md` → TODO 236、SPEC 279 明示只記錄不設閾值；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d
[MAJOR] 信心度=High；計數 gate 只能限制呼叫數，不能限制每次 lstsq 的實際時間／峰值記憶體；需有已批准的 baseline/上限，或把 receipt 明確降級為觀測資料並移除資源通過宣稱。
## CODEX-R7-P1-04
**斷言**: B1→B2 gate 的 `pytest ... -k load ...test_marginal_ic.py` 對所有指定檔案套用同一 keyword，可能只跑 loader 而完全不跑 marginal tests；Task 1.3 也只說「B1 十條」未給可唯一執行的 V_ID/file/sed/pytest rows。
**碼證**: VERIFY `pytest --collect-only -q tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/test_ic_1eb_b4_fullstack.py -k load` → `collected 25 / 25 deselected / 0 selected`、rc=5；TODO 32、96–100 僅列聚合命令／數量；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22
[MAJOR] 信心度=High；gate 可錯把部分綠當 B1 全綠，mutation probe 亦需自行發明目標行；需拆成兩條測試命令並列出十條唯一 mutation mapping。
## CODEX-R7-P1-05
**斷言**: B5 同時要求顯示「非獨立 OOS 驗證」且測試不得包含「獨立 OOS 驗證」，但前者字串本身包含後者 substring。
**碼證**: VERIFY shell substring check → `required_warning=yes`；TODO 256 要求顯示該句，259 要 `not.toContain` 且全域規則 16 禁該字樣；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d
[MAJOR] 信心度=High；B5 的正確文案會使其自身 negative assertion 失敗；需改用不含該連續字串的語意等價警語，並同步 SPEC/TODO/test oracle。
## Verdict: 需修補後派工（B1 核心統計可在 gate 修正後先行）
**必答1–6**: 1) 1.0–2.1 偽碼大致可執行，1.3、3.1、4.1/4.2、4.0 caller 仍需自行判斷；2) D1–D7/D3′/D3″、§G/§V/§C/§N 有落點，漂移集中於上述 lifecycle、signature、文案與 gate；3) B1/B2/B3 拓撲可獨立，B4→B5 依賴合理但 B4 目前不綠；4) bench 無閾值、`-k load`、mutation rows 空泛是主要取巧面；5) oracle 多數可證偽，probe 對映與 B5 substring 需修；6) 整票不可 Frozen，BLOCKING 清單為 P1-01/02/03/04/05。
**ASSUMPTIONS_VERIFIED**: stamps consult/R1–R6 各 rc=0；A1 `persist_suppressed` 只增既有 reasons 值、不增 schema key，無需 A1 延伸檔；A2 AST 常數與 loader 的 prefix/SoT 語意未被明確定義；A3 false；A4 部分成立；A5 false；A6 store custom path 可接，但需修 B5 文案與 B4 backend wiring。
**TESTS_RUN**: `template_check todo` rc=0；`todo_spec_crosscheck` rc=0；current `ic_wiring_check.sh` rc=0（R3 仍只報 5 sections）；reconcile stamps 七檔 rc=0；上述 `-k load` probe rc=5/0 selected。
**FAILURES_SEEN**: `-k load` 類比 collect probe intentional rc=5；其餘驗證命令通過；未修改 SPEC/TODO/程式。
**SCOPE_CHANGES**: none；只新增本交接檔。
**NUMERIC_OR_SCHEMA_IMPACT**: none to repo output；審查指出 benchmark acceptance 與 lifecycle/schema input gaps，未改數值、契約或輸出大小。
**HANDOFF_OUTPUT**: `handoffs/20260818-gap2-todoadv-codex.md`；task-id=20260818-GAP2-X-REVIEW-R7。
STATUS: DONE
