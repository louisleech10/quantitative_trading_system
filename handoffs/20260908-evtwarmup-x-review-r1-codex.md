## Verdict：需修補後派工；未發現新增 P0，發現 4 個 P1。
必答：1a 分流可繞且會誤判；1b disabled/empty 合法入口可能被擋；2a 第三 status 非必然必要但現有二值契約不足；2b `degraded_full_sample` 會誤導；3a ICIR 會靜默退化且部分排序會炸；3b global byte-identical 目前不成立；4a 批次順序可執行但 golden 互斥未解；4b 改測試 assertion 有換綠風險；5 無 ≥10× 過度工程；6 須先修文件契約。
類別覆核（1–11）：1=P1-01/04；2=P1-02/04；3=P1-04；4 quant=無公式變更；5=無；6=無；7=無；8=P1-02；9=P1-04；10=P1-04；11=無。
## CODEX-R1-P1-01
**斷言**: `event_label_values is not None` 不能直接等同「事件 label 已被消費」；現行前檢可能放行主線或將空 dict 當事件 label。
**碼證**: SPEC §C-3/TODO Task1.1 同時列入口鍵與 `label_source`，但 TODO 又規定 disabled/空 dict 視主線；`ic_filter_orchestrator.py:1074-77,1144-49,3204-21,3257-60,3333-49,3361-69` 顯示前檢早於 stage3 產生者判定；RECHECK: `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '1074,1149p;3204,3221p;3257,3260p;3333,3369p'`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d
MAJOR 信心度=High；disabled 時 stage3 明確回 `mode=none`，空 dict 在 enabled 分支仍進 given-label 驗證，可能繞 bar gate 或以 NaN/缺值失敗。修法是先定義完整 truth table，令同一個「實際被消費」predicate 同時供 precheck、stage4、fallback rerun；不得用 raw non-None 取代它。
## CODEX-R1-P1-02
**斷言**: Task1.2 要求的 `degraded_insufficient_test_events` 與現有 root/status、survivor、前端二值契約不相容；只加字串會被吞成 full-sample 或 fail-closed 拒收。
**碼證**: `normalize_analysis_status` 明定兩值；root resolver 只回兩值；survivor validate/build 只接受兩值；TS `ICReport` 只宣告兩值、Banner 文案固定 full-sample；VERIFY: `normalize_third=degraded_full_sample`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;momentum/Analysis/ic_reporter.py#73006e6bb658;momentum/Analysis/survivor_contract.py#eb9ecff6333b;frontend/src/lib/types.ts#7612e6b1d329;frontend/src/components/ic-analysis/DegradedBanner.tsx#948bd7a9a5d
MAJOR 信心度=High；若維持二值，`fit_mode=train_mask` 的 holdout run 會被標成 `full_sample_research_only`；若新增第三值，persist/export/API/scan/pass_class/UI 全要同步。文件須先選定「二值＋結構化 reason」或完整三值矩陣，並給 `oos_downgrade`、pass_class、消費端與 `min_test_events=0` 的一致契約；不能僅在 orchestrator 加值。
## CODEX-R1-P1-03
**斷言**: 跳過事件路徑 `icir_min` 後，TODO 指定的 tiebreaker `ic_mean` fallback 尚未落到實際 ICIR 消費者，會造成靜默排序退化或 TypeError。
**碼證**: `_apply_thresholds` 在 `ic_filter_orchestrator.py:4220-50` 無事件參數；stage6 將 `ic_scores` 傳入 redundancy `:3931-35`；`redundancy_filter.py:378-87` 缺/非有限 icir 回 `-inf`、不讀 `ic_mean`；reporter `:403-11,572-78` 與 orchestrator `:2903-06` 仍按 icir 排序。VERIFY: `tiebreaker_nan_score=-inf`、`mixed_icir_sort=TypeError`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;momentum/Analysis/redundancy_filter.py#5f57224be356;momentum/Analysis/ic_reporter.py#73006e6bb658;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d
MAJOR 信心度=High；NaN/None ICIR 會讓冗餘挑選把有 IC mean 的特徵視為 `-inf`，混合 None/float 的報告排序可直接炸。修法須列出 stage6、top-features、AI/export、survivor 的讀取點，僅對明定 tiebreaker/呈現排序做安全 fallback，保留 NaN/inf gate，並分別釘事件與全域測試。
## CODEX-R1-P1-04
**斷言**: Task2.1 的 global disclosure 與逐位元組 golden、以及 TFWINDOW 的生產接線與新 gate，目前互相矛盾且缺少可執行 artifact。
**碼證**: TODO 要求兩路徑寫 `ic_window_disclosure` 且 SPEC §C-2/G 要 global 逐鍵不變；`_build_report_metadata` 會保留新增 metadata (`ic_filter_orchestrator.py:4301-33`)，而 `scripts/gap2_freeze_golden.py:40-63` 僅 scrub 固定鍵。`test_ic_1a_cut1_oos.py:129-155` 直呼 stage4，不能證明 analyze→metadata timeframe 注入。VERIFY `for p ...; test -e "$p"` 對 `tests/api/test_evtwarmup.py`, `tests/api/test_tfwindow.py`, `tests/golden/tfwindow/rolling_keys_1h.json`, mutation script, phase gate 均輸出 MISSING。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;docs/TFWINDOW_SPEC.md#6dc2c594ede4;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d;scripts/gap2_freeze_golden.py#a3e234e4fc75;tests/momentum/Analysis/test_ic_1a_cut1_oos.py#99ad604dc54d
MAJOR 信心度=High；若 disclosure 進 global 報告，完整 canonical 會變但 probe 子投影可能假綠；若只改 `window_5` assertion，則可能未測到 production setter。文件須先明定 disclosure 是否在 byte-locked projection 外、補齊 1h/missing/invalid production-path golden、mutation、gate 與測試檔，再派工。§N：EW-RESID-1=user-ruling 成立；EW-RESID-2/3=needs-research 理由成立，30 目前是經驗地板而非 power 事實。
## 被當成事實的未驗證假設（§0，逐一列）
- `event_label_values is not None` 等同實際 event consumption：未被現行 stage3 證實，已列 CODEX-R1-P1-01。
- TFWINDOW 的手動/單測時間週期證據等同 production wiring 已覆蓋：未驗證，且指定 production-path artifact 尚不存在，已列 CODEX-R1-P1-04。
ASSUMPTIONS_VERIFIED: 三份 template_check TEMPLATE PASS；baseline probe rc=0 且 sha256=af73d325e0c476196a39f15479446145b5deab7651e8210bd23fe34ad3d04226、與既有 golden=True。 TESTS_RUN: `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` rc=0；`bash scripts/template_check.sh spec docs/TFWINDOW_SPEC.md` rc=0；`bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` rc=0；completeness 未執行。
FAILURES_SEEN: `bash scripts/gate.sh dispatch` rc=1，既有委員會債帳本的本輪 review 為 OPEN，拒發 fresh token，故 completeness 被 PreToolUse gate 阻止。 SCOPE_CHANGES: 僅新增本審查交接檔；未改碼、既有 dirty files 保留。 NUMERIC_OR_SCHEMA_IMPACT: 審查指出潛在 status/metadata/schema 影響；本次未修改數值、schema、golden 或輸出。
HANDOFF_OUTPUT: `handoffs/20260908-evtwarmup-x-review-r1-codex.md`。
STATUS: BLOCKED — completeness_check 未能執行：PreToolUse 要求 fresh dispatch token，但 gate.sh 因本輪 OPEN 委員會債拒發。
