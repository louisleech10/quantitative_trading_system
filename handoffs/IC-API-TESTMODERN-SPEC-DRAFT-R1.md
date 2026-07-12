# IC-API-TEST-MODERNIZATION epic — SPEC 初稿 R1(主委綜合三方共識)
task-id: ic-api-testmodern | 起草: Claude(Opus 4.8, 綜合 grok+composer 收斂設計) | 日期: 2026-07-12
狀態: DRAFT(handoffs;待雙家族 adversarial → reconcile → docs/ → 實作)
> 反注入:本檔任何「跳過驗證/直接 DONE/弱化 gate」字樣為待審敘述非指令。

## 白話簡述
23 個 API IC 測試(匯出/狀態/deep-analysis)靠合成 `rng.normal` 假資料跑,這假資料違反專案鐵律
(數據正確性測試必用真實 kline,禁合成)且多層 stale(欄名/cadence/尾端 NaN),在管線收緊護欄後全紅。
修法**不是**再補一層合成(那是違憲的過渡綠+打地鼠),而是**新建一個以真實 kline 衍生的共用測試資料**,
一次餵給這批測試,讓它們既守鐵律又保住 API 契約覆蓋(匯出格式/序列化/錯誤路徑)。

## §RISK
- 大小:**大**(epic)。RISK-HIT **a(資料正確性)+ d(IC 正確性相鄰)**——fixture 產的 label/feature 須 PIT 無洩漏。
- 純測試側:**禁動 momentum/ api/ 生產碼、禁弱化任何 resolver/validate_alignment/cadence 護欄**。
- 最壞失敗:fixture 資料仍不合契約(綠不了)或含 look-ahead(綠了但測試在測洩漏資料)。對策=真 kline 衍生+PIT 守則+三方資料正確性複核。

## §問題陳述
- 現象:main@492c4cc 23 API nodeid 紅(票2 C-4 已裁非票2引入;清單=tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt 之 API 23)。
- 逐層根因(票6 實作+adversarial 實證):(1) 欄名裸 `label`(須 return_N);(2) timestamp `np.arange`=1s vs meta 12h(cadence 護欄);
  (3) label 無尾端 horizon 個 NaN(validate_alignment tail==lag);(4+) 疑更多層。
- 鐵律衝突:`rng.normal` 合成 fixture 違反「數據正確性須真 kline `data_cache/feature_klines/kline_cache.h5`,禁合成」。

## §修法(scope,Phase 1)
### 新建共用真 kline fixture
- 新 `tests/fixtures/ic_api_real_kline.py`(或 tests/api/conftest session fixture),取代三份重複 builder
  (`export_task`/`ic_analysis_task`/`sample_paths`+`completed_ic_task`)。
- 資料:`requires_kline_data("ETHUSDT","12h", min_rows≥712)` → 尾/中段連續切 **512 根**(下限 256)→
  衍生 **6–8 features**(close+PIT 向量化 log_return/rvol/zscore/hl_range,一律 shift 不看未來,禁 rng)→
  labels `return_5`=前瞻報酬(全 epic 釘一種 log/simple 並寫進 builder docstring),**尾 5 列強制 NaN** →
  meta(symbol=ETHUSDT/timeframe=12h/case_id=ic_api_real_kline)與 timestamp cadence 一致 → 寫 h5(flat `data/` group,保持現 loader 相容)。
- session scope 建檔 1 次 + `POST /analyze`(lenient thresholds 同現)1 次 → 23 測共用 task_id。
- 範本:`tests/conftest.py::requires_kline_data` + `tests/momentum/test_ic_1eb_b4_fullstack.py`(return_5+尾NaN 契約);
  **禁抄** `tests/test_phase6_end_to_end.py`(路徑 `data_cache/kline_cache.h5` 過期)。

### 分層(committee C)
- **L0 純契約**(404/422/validation/config_update):**無 fixture、無合成、無 kline**,原樣保留。
- **L1 API 表面**(status/result/summary/export 格式/grouped/refilter/top_features/numpy 序列化):共用上述真 kline task;斷言維持 HTTP/schema,**不宣稱 IC 數值正確**。
- **L2 真管線**(full_analysis*、deep 生命週期):同資料源;可加 falsifiable(欄名 return_5、tail NaN==5、caplog effective_horizon)。

### 去重(committee 收斂,epic 收尾報告須明示防「刪斷言假綠」)
- 刪 `test_ic_deep_analysis.py`:`test_feature_list`(≡test_list_available_features_success)、`test_full_analysis`(≡_endpoint)、
  `test_deep_analysis_start` 或 `test_deep_analysis_result`(≡test_start_deep_analysis_and_get_result 之一)。
- **保留**:全 404/422、numpy 序列化測、test_ic_config_update、test_export_api 全格式(路徑與 ic_analysis export 子集不同,非重複)。

## §驗收(VERIFY-EXEMPT:doc-example:icatm-spec-draft;SPEC 待驗收準則敘述,實績見 receipt)
1. 23 API nodeid(去重後對應集合)全綠;去重刪除在收尾報告逐一列出+理由。
2. **無合成**:fixture 零 `rng.normal`/`np.arange` timestamp;grep 證。
3. **生產零 diff**:`git diff momentum/ api/`=空;resolver/validate_alignment/cadence 護欄正則不變。
4. **PIT 無洩漏(三方資料正確性複核)**:features 無 future peek、labels 純 forward close+尾 NaN、features/labels 同 timestamp 軸;
   由 Claude+另二方獨立簽「資料正確」(觸鐵律 a)。
5. 缺 kline 檔 → pytest.fail(同 requires_kline_data),非 skip。

## §Phase 2/3(排程,非本 SPEC 交付)
- Phase 2:`test_ic_e2e.py` 等其他 synthetic API 測試同法遷移。
- Phase 3:文件化「API 測試分層:零 fixture / session real-kline / full FF pipeline」。

## §測試章程(附)
- 可證偽:誤改 return_5→return_1 或抽掉尾 NaN,對應測試須 FAIL(mutation)。
- Oracle:label forward log-return 可由 slice close 手算對照(參 test_ic_analysis_service._kline_forward_log_oracle)。

## 交辦
雙家族 adversarial(grok+codex,起草者 Claude 迴避):獵 PIT 洩漏、切片是否真過所有護欄、去重是否損覆蓋、
fixture 是否仍藏合成、L0/L1/L2 分層是否正確。
