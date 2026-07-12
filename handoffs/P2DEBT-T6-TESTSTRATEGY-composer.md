# 票6 測試策略 — Composer 獨立建議
Task-id: p2debt-t6 | Advisor: Composer | Date: 2026-07-12 | 唯讀諮詢

## 一句話結論
**採 B 的集中化變體（D：單一 session 級真 kline fixture + 去重），並從票6 拆成獨立 test-modernization epic** — 23 測試的價值在 API 契約覆蓋而非合成噪音本身，一改共用 fixture 即可同時滿足 `return_5`/12h cadence/尾端 NaN 護欄且守鐵律，比逐層修假資料或全刪都划算。

## 1. A / B / C / 第四選項

| 選項 | 判斷 | 理由 |
|------|------|------|
| **A 全刪** | 反對 | 7+9+7 測試覆蓋 export 格式、task 生命週期、422/404、deep-analysis 序列化等 API 契約；刪除後無同級替代（`test_ic_response_v2.py` 用 golden JSON mock，不走真管線）。 |
| **B 真 kline fixture** | **贊成（核心）** | 根因是 3 份檔案各自 `_write_*` + `rng.normal`，與引擎 fail-closed 護欄（`return_5`、12h timestamp、horizon 尾 NaN、`validate_alignment`）結構性衝突；真 kline 切片一次生成 features/labels/meta → session 跑完 `/analyze` → 23 測共用 task_id，改動面小、效益最大。 |
| **C 分類處理** | 贊成（實作細節） | 與 B 不矛盾：**不需 IC 結果的**（404/422/validation-only）保留零 fixture 或假路徑；**需 completed task 的**走同一真 kline bundle。C 是 B 的分層，不是第三條路。 |
| **D（建議第四選項）** | **優於純 B** | **B + 集中化 + 去重**：新增 `tests/fixtures/ic_api_real_kline.py`（或 conftest session fixture），取代 `export_task` / `ic_analysis_task` / `sample_paths` 三份重複 builder；票6 原 scope「rename label」變成此 fixture 的副產物。 |

**不建議的第四選項（排除）**：
- **Service mock 取代真管線**：HTTP 層可 mock，但這 23 測的設計意圖是「API + 真 IC 任務狀態」；mock 會與 `test_ic_analysis_service.py` 的真 oracle 測試分工不清，且違反「觸 IC ingest 即算資料正確性路徑」的 spirit。
- **commit 預烘焙 HDF5 golden**：可行但 artifact 治理成本高；session tmp 從 manifest 驗過的 kline **即時**切片更符既有 `requires_kline_data` / `DATA_MANIFEST.json` 模式。

## 2. 真 kline fixture 切片建議

**首選：`ETHUSDT / 12h / 512 rows / offset 200`**

| 維度 | 建議 | 依據 |
|------|------|------|
| Symbol | **ETHUSDT** | `tests/fixtures/DATA_MANIFEST.json` 有完整指紋；`test_l65_native_tf_real_eth.py` 已確立為 correctness 參照幣；比 TESTUSDT 假 symbol 更貼 meta 契約。 |
| Timeframe | **12h** | 三份 API fixture 的 meta 均寫 `12h`；IC xsec/oracle 測試亦以 12h 為主；須用 kline 真 `timestamp`（43200s 間隔），禁用 `np.arange(n)`。 |
| 列數 | **512**（可接受下限 **256**） | 原合成 120–180 列在護欄收緊後不足；512 足 IC summary + deep-analysis `factor_return`（top_n=3）且 session 只算一次。 |
| 切片位置 | **`[200:712]`**（中段） | 避開序列首尾 warmup/缺 bar；1696 總列中段穩定。 |
| Features | **6–8 列，由 kline 衍生** | 例：`close`, `log_return_1`, `volume`, `hl_range`, 簡單 rolling mean/std（全 float32）；**禁止** `rng.normal` 特徵矩陣。 |
| Labels | **`return_5`**，尾 **5 列 NaN** | 對齊 `test_ic_1eb_b4_fullstack._run_full_analyze_e2e` 與 `validate_alignment`；forward log-return 由 slice 的 close 手算（可參 `test_ic_analysis_service._kline_forward_log_oracle`）。 |
| Meta | `symbol=ETHUSDT`, `timeframe=12h`, `case_id=ic_api_real_kline` | 與 h5 內 timestamp/label 一致。 |
| 建置方式 | `requires_kline_data("ETHUSDT","12h", min_rows=712)` → 切片 → 寫 h5 → **一次** `POST /analyze`（lenient thresholds 同現 fixture）→ session 共用 `task_id` | 參照模式：`conftest.requires_kline_data` + `test_ic_1eb_b4_fullstack` 寫 h5 契約；**勿**抄 `test_phase6_end_to_end.load_sample_data`（路徑仍指向過期 `data_cache/kline_cache.h5`）。 |

**速度**：session scope + 單次 analyze ≈ 數秒級一次性成本；23 測試本身仍為 HTTP 斷言，CI 可接受。

**備選**：若 deep-analysis 模組在 512 列仍慢，可將 deep 專用 fixture 拉到 **768 列**，但先統一 512 試跑再調。

## 3. 建議刪除或合併的測試（非全刪）

**建議刪 3、保留 20**（去重，不損覆蓋）：

| 檔案 | 刪除候選 | 理由 |
|------|----------|------|
| `test_ic_deep_analysis.py` | `test_feature_list` | 與 `test_list_available_features_success` 同路由同斷言，純重複。 |
| 同上 | `test_full_analysis` | 與 `test_full_analysis_endpoint` 同流程（POST full-analysis → wait → GET result）。 |
| 同上 | `test_deep_analysis_start` **或** `test_deep_analysis_result` | 二者均被 `test_start_deep_analysis_and_get_result` 覆蓋；保留最完整的那一個 + numpy 序列化測即可。 |

**明確保留（勿刪）**：
- 所有 **404/422**（`export_unknown_task_404`、`invalid_format_422`、`deep_analysis_request_validation_top_n` 等）— 無需真 kline。
- `test_deep_analysis_result_serializes_numpy_scalars` — 測 JSON 序列化，直接 patch service state，與 kline 無關，有獨立價值。
- `test_ic_analysis_api.test_ic_config_update` — 無 completed task 依賴。
- `test_export_api` 全系列 — export 路由與 `test_ic_analysis_api` 的 export 子集路徑不同（`/export/{id}/csv_summary` vs `/export-csv/{id}`）。

## 4. 是否從票6 拆成獨立 epic

**是，應拆。**

| 維度 | 說明 |
|------|------|
| 原票6 | 「label→return_5 rename」— 表面 1 欄位，實為 symptom。 |
| 實際工作量 | 3 fixture builder 合併、真 kline 切片契約、meta/h5 schema 對齊、`test_ic_e2e.py` 同病（亦 `rng.normal`，應列入同一 epic 但可 Phase 2）。 |
| 風險類型 | 命中鐵律 (a) 數值/資料品質 + (d) ML/IC 正確性；非 P2 債「rename」能裝下。 |
| 建議結構 | **Epic: `IC-API-TEST-MODERNIZATION`** — Phase 1: 共用真 kline session fixture + 23 測綠 + 去重 3；Phase 2: `test_ic_e2e.py` 與其他 API synthetic 清單；Phase 3: 文件化「API 測試分層：零 fixture / session real-kline / full FF pipeline」。 |
| 票6 剩餘 | 僅追蹤「護欄已滿足」的驗收 gate，不再承載 fixture 重構 implementation。 |

## 5. 與主委 B 的差異（可挑戰點）

1. **更強調 D（集中 fixture 檔 + 去重）**，避免 B 變成三份檔案各改一遍仍留 drift。
2. **symbol 建議 ETHUSDT 而非 BTCUSDT**：manifest 兩者皆有；ETH 已有 real-kline L6.5 先例，slice 文檔可复用。
3. **`test_phase6_end_to_end.py` 不宜作直接範本**：路徑與 schema 均過期；應以 `conftest.requires_kline_data` + `test_ic_1eb_b4_fullstack` 為準。
4. **票6 必須降級為 epic 子任務**，否則「rename 完成」會被誤標 DONE 而 synthetic 仍違規。

## 6. 風險與踩坑

- 缺 `data_cache/feature_klines/kline_cache.h5` 時應 **pytest.fail**（同 `requires_kline_data`），非 skip — 與 correctness 測試一致。
- h5 group 路徑：API 測試用 flat `data/` group（現行写法），引擎測試常用 `BTCUSDT/12h/` — 改 fixture 時須確認 loader 兩種皆支援（現合成測試用 flat `data/`，保持即可）。
- deep-analysis 測試 `module` scope fixture 與 export `session` scope 可統一為 **session**，減少重複 analyze。
- 去重刪測試須在 epic 收尾報告明示（防「假綠 by 刪 assertion」誤解）。

---
**ASSUMPTIONS_VERIFIED**: 已讀 `handoffs/P2DEBT-T6-TESTSTRATEGY-CHAIR.md`；已 grep/read `tests/api/test_{export,ic_analysis,ic_deep}_*.py`、`tests/conftest.py`、`tests/fixtures/DATA_MANIFEST.json`、`tests/test_phase6_end_to_end.py`、`tests/momentum/test_ic_1eb_b4_fullstack.py`、`tests/api/test_ic_analysis_service.py`（oracle 模式）。未跑 pytest（唯讀任務）。
**SCOPE**: 僅產出本檔，未改碼。
**STATUS**: DONE（諮詢產物）
