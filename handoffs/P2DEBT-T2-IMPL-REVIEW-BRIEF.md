# 票 2 data_cache redirect 實作審查 brief(給 grok+composer 雙家族)
Task-id: p2debt-t2 | Chair: Claude | Date: 2026-07-12

## 審查標的
票 2 = IC persist 寫入 data_cache 的測試隔離守衛(redirect)。process-global redirect gate
+ S1-S11 seam manifest + digest oracle(per-file sha256)+ mutation canary + golden A/B/C。
實作者=Codex(多輪 C-1~C-5);審查=你(實作者不自審,雙家族)。

## 驗收現況(final6 receipt 20260712T003131Z-p2debt-t2-impl-final6, exit_code=0)
- V1 9p / V2 2p / V5 3p / V7 133p+8skip,五 set DIGEST_DIFF_EMPTY=1。
- V6:9 passed + 23 既有紅(main@492c4cc 基線,非票 2 引入),V6_NO_NEW_RED=1+DIGEST=1;
  準則經 C-4 grok+composer 雙 STAMP 修訂(見 handoffs/P2DEBT-T2-C4-REVIEW-{grok,composer}.md)。

## 票 2 檔案 scope(審這些)
新增:
- tests/fixtures/ic_persist_redirect.py / _plugin.py / _manual.py
- tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt
- tests/momentum/Analysis/test_ic_persist_redirect_{golden_ab,unit,inventory,isolation}.py
- scripts/run_ic_persist_hermetic.sh
- docs/P2DEBT_T2_DCREDIRECT_{SPEC,TODO}.md
修改(加 redirect mark/包裝):
- tests/conftest.py
- tests/api/test_{export_api,ic_analysis_api,ic_analysis_service,ic_deep_analysis}.py
- tests/momentum/Analysis/test_{ic_1a_cut1_golden,ic_1a_cut1_oos,lightgbm_analyzer,
  lightgbm_edge_cases,xgboost_protocol_methods}.py
- tests/momentum/test_{ic_e2e,ic_feature_filter,lightgbm_analyzer_phase3,
  xgboost_protocol_methods_phase3}.py、tests/test_feature_factory_e2e.py

## ⚠️ 混雜檔警示(commit scoping,請評估)
下列 freeze/baseline 生成腳本工作樹改動**混雜票 2 與票 5**:
- tests/golden/ic_phase1_1a_cut1/freeze_baseline.py、freeze_baseline_new.py
- tests/golden/ic_phase1_contract/freeze_baseline.py
- tests/fixtures/gen_ic_run_selector_baseline.py
票 2 部分=`+from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect`
+ `with run_with_manual_redirect():` 包裝 main();票 5 部分=h5_existing 快取邏輯、
config_override 寫死(854d444 註記,flag-off golden 語意)。**請判定 commit 時票 2 是否只取
redirect hunk(git add -p 分離),票 5 hunk 留待票 5**——或整檔一起走。給明確建議。
純票 5(不在票 2 scope,禁 commit):tests/golden/*/baseline_*.json、l65/test_inventory.txt。

## 請各自獨立產出(adversarial;VERIFY-EXEMPT:doc-example:p2debt-t2-brief 指示性,非驗證斷言)
1. redirect 守衛正確性:寫路徑真被導向犧牲根?讀寫同根?有無殘留繞過守衛的寫點(C-5 型)?
   digest oracle 是否可證偽(mutation canary 有效)?process-global gate 過 asyncio.to_thread 邊界安全?
2. 測試設計嚴謹:golden A/B/C sha256 oracle 是否真鎖行為?skip 白名單 anchor 正確(C-1 教訓)?
   V6 nodeid gate 可證偽(C-4 已驗正反極性)?
3. 接縫完整:S1-S11 manifest 有無再遺漏寫點(C-5 補了 lightgbm save + _persist_outputs)?
4. commit scoping:混雜檔建議。
輸出:handoffs/P2DEBT-T2-IMPL-REVIEW-{grok,composer}.md,verdict=APPROVE 或 BLOCK+可證偽反例。
只准寫你的產出檔;禁改實作/測試/生產碼。
