# GAP-2a/2b recon；task-id=20260818-GAP2-X-CONSULT-R1；family=codex；round=R1
模式=consult/read-only；只新增本檔，未改 code、test、SPEC、HANDOFF.md；task-specific GAP-2 SPEC/TODO 未提供且 brief 明定本輪 pre-SPEC。
結論=需帶回委員會修正設計後才足以起 SPEC；R1 非零 finding，GAP-2a 仍可先做純函式/獨立 oracle，GAP-2b 先做契約。
1-2 定義：candidate-only residual 與 partial correlation 不等價；Pearson 應對 x、y 同時以 train-fit S 殘差化；Spearman 必須明定 rank/PIT 語意與順序依賴。
3 組合：single-asset longitudinal IC 可做 equal_z/sign-frozen 與 train-fit IC-weighted，但權重/符號/正規化需 train-only 冻結，delta composite 要 paired block CI；OLS/Ridge 留 ML 邊界。
4 放置：stage6 後若直接吃 filtered_df，split 路徑拿到的是 test rows；純 IC 應吃完整 post-event frame 加 RowMaskPlan，並在凍結選擇後只報告 test。
5 契約：survivor 需有 label/horizon/timeframe/symbol、ordered feature_set_hash、base_universe_hash、結構化 sample_scope/row_identity_hash、split/fit/PIT、selection/FDR、input/config/schema hashes、stats/CI/status/provenance；RowMaskPlan/SelectionScope 以 digest/reference 關聯，不能只靠 metadata。
6 測試：scipy/閉式 oracle、train-fit/test-apply、NaN/inf/warmup、order/mask/hash mutation、label/feature permutation、paired CI；每個新增測試檔需 mutation probe 或明確 N/A。
7 範圍：B1 pure marginal IC+oracle 獨立有價值；B2 combiner standalone/default-off；B3 strict JSON+artifact persistence；B4 orchestrator/report/TS wiring 最後，GAP-3 不混入。
8 blocker：現有 `ok_oos` 只證明 split/preprocessing applied，不證明 test 未被 selection/tuning 消費；需 nested/frozen-selection 或降級為 research/report-only 才能立 SPEC。
## CODEX-R1-P0-01
**斷言**：目前 holdout 的 test 同時供 stage4 IC、stage5 threshold/FDR、stage6 redundancy，`_resolve_root_status` 仍可給 `ok_oos`；任何 marginal/combiner 接在此後都會把選擇結果誤標獨立 OOS。**碼證**：`ic_filter_orchestrator.py:1028-1045,3059-3228,3318-3363,1153-1176`；採用 train/validation 做選擇、凍結 final test 報告，或明確 `in_sample_research_only`/nested split。**來源摘要**：momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c
## CODEX-R1-P1-02
**斷言**：brief 的「candidate residualized against S」不可直接命名 marginal/partial IC：partial Pearson 要 residualize candidate 與 label，現有 Gram-Schmidt 還是 full-sample、順序依賴且只回傳 Q/variance；Spearman rank 後再 residualize 與 residual 後 Spearman 不是同一統計量。**碼證**：`factor_orthogonalizer.py:25-63,122-142`；契約須分 `partial_pearson`/`semi_partial`/`spearman_variant`、fit scope、intercept、排序與 S order invariance。**來源摘要**：momentum/Analysis/factor_orthogonalizer.py#989b9e4b2101；`momentum/core/contracts.py#8a1415d6ea01`。
## CODEX-R1-P1-03
**斷言**：`run_deep_analysis()` 預設以 `_filtered_features_df` 作 candidate，而 split 下 stage6 的 `filtered_df` 是 test-only；這與 train-fit/test-apply marginal projection 所需的完整 post-preprocessing/event frame 不相容，且 rolling/PIT marginal 會另需 warmup/fallback 標記。**碼證**：`ic_filter_orchestrator.py:973-990,1038-1045,1840-1847,3318-3363`；輸入應拆成 full frame、train mask、test mask、frozen survivor set，禁止把 test selection 當 fit data。**來源摘要**：momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c
## CODEX-R1-P1-04
**斷言**：目前無 `sample_scope` 欄位；event timestamps 在 report 被移除只留計數，HDF5 只存 status/OOS/time/task，ICArtifact/FilteredFeatureSet 也沒有可驗證 artifact identity，故 consumer 無法重建 exact rows 或防 stale/cross-symbol cache。**碼證**：`event_filter.py:66-105`、`ic_filter_orchestrator.py:2770-2776`、`ic_reporter.py:774-802`、`contracts.py:323-347,681-746`；新增 strict additionalProperties=false survivor envelope，至少含 row identity/event-definition/input-label/config/split/PIT hashes、scope_id、symbol/tf/horizon、ordered features、stats/CI/status。**來源摘要**：momentum/Analysis/event_filter.py#e2c89cb3ad7c；momentum/Analysis/ic_reporter.py#e7eb62b1699e；momentum/core/contracts.py#8a1415d6ea01。
## CODEX-R1-P1-05
**斷言**：新增 survivor report section 不能只加 JSON：現有 contract validator/reporter/TS `ICReport`/`ic_wiring_check.py` 都固定五節；若契約獨立，主 IC report 應只放 pointer/status，否則必須同步四方與測試，避免 frontend/consumer ghost field。**碼證**：`ic_report_contract.json:27-47`、`ic_reporter.py:315-360`、`frontend/src/lib/types.ts:2036-2165`、`scripts/ic_wiring_check.py:30-36,115-126`；目前 wiring check 已實跑只覆蓋五節。**來源摘要**：momentum/Analysis/contracts/ic_report_contract.json#6937da262f；scripts/ic_wiring_check.py#bdf0f75f4271；frontend/src/lib/types.ts#e92be7b6da87。
## CODEX-R1-P1-06
**斷言**：單一「候選是 S 的線性組合 ⇒ marginal≈0」oracle 只對明確 Pearson 線性投影/同 sample/同 schema 成立，對 Spearman、缺失、權重重估與 test-fit 不成立；缺 mutation/paired CI 會讓錯誤實作假綠。**碼證**：`docs/TEST_DESIGN_CHARTER.md:7-61,82-105` 已要求 mutation、F-IC-3/4/8、F-MC-1/2；新增測試須覆蓋 remove-projection、test-fit、reverse-mask、shuffle-S、label permutation、weight-unfreeze、hash/symbol mismatch。**來源摘要**：docs/TEST_DESIGN_CHARTER.md#e9be08bb5d5f。
## 判定與文獻
文獻錨點：[Brown/Hendrix partial correlation](https://onlinelibrary.wiley.com/doi/10.1002/9781118445112.stat06488)、[Grinold–Kahn](https://www.mheducation.com/highered/mhp/product/active-portfolio-management-quantitative-approach-producing-superior-returns-selecting-superior-returns-controlling-risk.html)、[Qian–Hua–Sorensen](https://www.routledge.com/Quantitative-Equity-Portfolio-Management-Modern-Techniques-and-Applications/author/p/book/9781584885580)、[López de Prado](https://www.wiley-vch.de/de/fachgebiete/finanzen-wirtschaft-recht/advances-in-financial-machine-learning-978-1-119-48208-6)；支持 residual/多因子/金融 OOS 方向，不替代本 repo oracle。
ASSUMPTIONS_VERIFIED: brief scope/rulings、split masks、stage5/6 test slicing、root status、orthogonalizer semantics、contract/TS/wiring gaps、test charter、dirty worktree 與 /tmp 頂層檢查均已讀/實查；無 GAP-2 SPEC/TODO 可核對。
TESTS_RUN: `venv/bin/python scripts/ic_wiring_check.py` → rc=0，R1a(24)/R1b(16)/R2(11)/R3(5) 全綠；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-recon-codex.md --family codex` → rc=0，6 IDs 格式合規（首跑 rc=1 的 11 位 digest 已修正）。
FAILURES_SEEN: 誤以 bash 執行 Python wiring script（shell syntax/command-not-found），已改用上述正確命令通過；`ps aux` 受環境 operation not permitted，未據此宣稱 process 清空。
SCOPE_CHANGES: none；僅新增本交接報告；未改 `data_cache/`、程式、測試、SPEC、根 HANDOFF；/tmp 未見可清理之匹配 workdir，保留規則 `claude-501`。
NUMERIC_OR_SCHEMA_IMPACT: 未改現有數值、schema 或輸出；本檔只提出待核准的 strict survivor contract 欄位與 OOS 分層建議。
STATUS: DONE
