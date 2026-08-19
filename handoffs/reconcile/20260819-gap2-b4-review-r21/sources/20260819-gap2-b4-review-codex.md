# GAP-2 B4 Code Review — CODEX（task-id: 20260819-GAP2-B4-REVIEW-R21）
## Verdict
需修補後進 B5：兩個 P1 均為可局部修補的落盤／provenance 問題；未見需重作的數值或契約根本缺陷。
## 段 A
Task 4.0–4.3 逐條符合；兩插入點、fallback try/finally、root OOS 唯一注入、xsec N/A、顯式 persist kwargs、cache snapshot、A1-1/A1-6 字面均有實作與測試碼證；報告落盤順序與 override provenance 見 P1。
## 段 B
B1 A1-10 是行為 canonicalization，不是重新凍結換綠；split_label＋summary/filter exact 足證行為，config hash drift 另留 legacy 稽核；B2/B3、B5–B10、B12 可接受。B4 除 P1-02 外合理；B11 receipt 對證 600 次 spy、wall 94.2s、RSS 612761600，建議標 slow/獨立 receipt 但非阻擋 finding。
## 段 C
receipt `20260819T002456Z` 七條 mutation 全 RED/還原 GREEN；`_diff_summary` 使用 1e-12；fit_scope-root 與 cold-call persist 均是真 seam。實跑兩案 `2 passed in 134.54s`，③ 走 ok 分支、未 skip。
## 段 D
真實 ETHUSDT/12h fixture：正常 `status=ok, fit_scope=train, survivors=2, n_regressions=4, root=(ok_oos,True,"oos")`；事件 fallback 為 `fit_scope=train` 但 `(False,"full_sample_research_only")`；倖存者 payload `n_samples_total=1696`，row identity 及 24 鍵 validator 通過。
## 段 E
G2-R1/R2/R3/R5 觸發均未成立；xsec N/A 與倖存者檔落地不等於 #4 完工、ML 穩定、二次選擇政策或 holdout-only 主線升級。
## CODEX-R21-P1-01
**斷言**: `metadata.survivor_output` 只存在於回傳中的 report，未寫入同次落盤的 `ic_report_*.json`，違反報告鏡像與互指契約。
**碼證**: `ic_filter_orchestrator.py:4049` 先呼叫 `save_report`，`:4062-4074` 才注入 survivor object；`ic_reporter.py:833-837` 立即 JSON dump。VERIFY `venv/bin/python -c ...` → `IN_MEMORY_SURVIVOR True`, `DISK_SURVIVOR False`。
**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5;momentum/Analysis/ic_reporter.py#73006e6bb658
[P1] 信心度=10/10；下游只讀 persisted report 時拿不到 survivor path/sha/status。應在 survivor metadata 注入後再保存 report，或等價保證落盤 JSON 含五鍵。
## CODEX-R21-P1-02
**斷言**: `config_override` 改變 IC method 時，倖存者 provenance 的 `ic_method` 仍取建構時基礎 config，非本次 effective config。
**碼證**: `analyze()` 的 effective `config` 來自 `:4303-4310` override merge；`_write_survivor_output:4156` 卻讀 `self._config.ic_calculation.methods[0]`。VERIFY override `{"ic_calculation":{"methods":["kendall"]}}` → `OVERRIDE_METHOD spearman`，而 `OVERRIDE_CONFIG_HASH True`。
**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5;momentum/Analysis/ic_config_schema.py#d7b736fce3a5
[P1] 信心度=10/10；結果的 provenance 會誤導重現／消費端，且同型 `label_return_type` 也使用基礎 config。將 effective config 顯式傳到 persist 或保存當次 config，再取規定欄位。
## 被當成事實的未驗證假設（§0）
無；A1-10、測試前提、B4 receipt 與本輪兩個 runtime VERIFY 均已核對。
ASSUMPTIONS_VERIFIED: SPEC/TODO/AMENDMENTS、HANDOFF/CLAUDE 已讀；fixture、fallback、probe、golden、wiring 與兩個 P1 runtime 行為已實跑或讀 receipt。
TESTS_RUN: `venv/bin/python -m pytest ...::test_forced_full_sample_fallback ...::test_file_exists_validates_names_and_sha -q` rc=0（2 passed）；`gap2_freeze_golden.py --check` rc=0；`ic_wiring_check.sh` rc=0；B4 probe receipt rc=0。
FAILURES_SEEN: none；SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: 未改實作，finding 僅要求修補落盤與 provenance 來源；HANDOFF_OUTPUT: `handoffs/20260819-gap2-b4-review-codex.md`。
STATUS: DONE
