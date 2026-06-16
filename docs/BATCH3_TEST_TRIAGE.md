# 第 3 批：既有測試紅 triage 分類（2026-06-15）

> 來源：`pytest -m "not slow and not legacy"` 全跑（2731s，43 failed + 7 error + 2679 passed + 35 skipped）。
> 慢測（l65 全寬 ADF 等）未納本輪，另計。

## A1 — 本輪（batch1/batch2）引入的回歸（我負責，已/將修）

| 測試 | 根因 | 處置 | 狀態 |
|---|---|---|---|
| test_failopen_frozen_diff / test_failopen_matrix | batch1(T5 present_timeframes)、batch2(browse ID full-hash) 改既有斷言未登記 FF_FAILOPEN_FROZEN_TESTS.md（守門測試，不在當初回歸 bundle） | 補登記兩 wildcard 行 | ✅ 已修（2 passed） |
| test_phase2 test_registry_upserts_... | batch2 registry `add` 改 merge-preserve，保留既有 created_at；測試斷言舊覆寫(200) | **委員會技術問題**（見下）→ 修測試/產品 | 待委員會 |

**鐵律應用**：守門測試 frozen_diff/matrix 證明「批次驗收矩陣必含下游消費者測試」——batch1/2 的回歸 bundle 漏了這兩個 meta 測試。下次 bundle 須含之。

### 委員會技術問題 Q1（retention 正確性）
batch2 merge-preserve 保留 created_at。但 retention「per (s,tf) 留最近 5 個未命名」依 created_at 降序排。**若 created_at 凍結在首次生成，重跑舊 config 不刷新「最近」→ 可能被誤清**（剛用過卻被當舊的刪）。
- 選項 A：merge-preserve 只保 alias，created_at 於重生成時刷新（retention 用「最後生成」語義）。
- 選項 B：新增 `last_generated_at` 欄，retention 改依此排；created_at 維持「首次」。
- 選項 C：維持現狀（created_at=首次），接受重跑不刷新 recency。
→ 委員會裁定後修 test_phase2 對應。

## C — 關聯 #2 d* fracdiff（由 #2 吸收，本輪不單獨修）

| 測試 | 根因 |
|---|---|
| test_l65_golden tier2a「Synthetic d_star output is empty」(GoldenBuildError) | **同批不同根因**（委員會更正）：golden builder 讀過時 private `_d_star_cache` dict（非 frame no-op）——#2 同 PR 分開修（見 BATCH2D manifest [D2-6]） |

## B — 既有殭屍/滯後測試（batch-3 backlog 本體，~39，分簇處置）

> 特徵：測試 fixture/mock/期望落後於「刻意的 API 變更」，非產品 bug。判斷「更新測試 vs 刪殭屍 vs 真缺陷」每簇走委員會。

| 簇 | 測試數 | 根因（一行 traceback） | 初判 |
|---|---|---|---|
| phase_d_granular_control | 7 (ERROR) | FileNotFoundError docs/FRONTEND_INTEGRATION_GUIDE.md | 文件已移除→測試過時（更新指向或刪） |
| memory_chunking MultiTFColumnBatchMerge | 5 | TypeError `_merge_asof_align()` missing source_tf/primary_tf | 簽名變更，測試滯後（更新呼叫） |
| l7_parallel_persist + l7_persist_perf | 9 | TypeError fake_persist() unexpected kwarg compression_level；unpack 5≠4 | 簽名變更，測試 helper 滯後 |
| hardware_utils + hardware_api | 5 | Mock/Mock division；tier config dict 增鍵(chunk_bars 等) | tier config 刻意擴充，測試滯後 |
| feature_factory_config | 2 | config defaults 斷言（新 sections） | schema 擴充，測試滯後 |
| cgsa_resume | 5 | ValueError unpack 5≠4；TypeError 簽名 | 簽名變更，測試滯後 |
| feature_storage float32 | 1 | assert 'mixed' == 'float32' | dtype 報告改 'mixed'（batch1 已見），測試滯後 |
| optimization_e2e | 6 | （SPEC 點名 engine_partial 等）需逐一看 | **可能含真缺陷**，委員會細查 |
| optimization_perf / multi_window_perf | 2 | speedup < 門檻（perf marker） | perf 非 blocking（pytest.ini 定）→ 降級/標 xfail |
| ic_first_pipeline memory_budget | 1 | （AttributeError _storage?）需看 | 細查 |
| winsorize_partition_opt | 1 | 需看 | 細查 |
| v2_timestamp_golden G1/G2 | 1 | golden allowlist unchanged | golden 漂移，細查 |

### 委員會技術問題 Q2（殭屍處置原則）
~39 個多為「測試落後於刻意 API 變更」。批量處置原則需委員會定：
- 「更新測試對齊新簽名」vs「刪除測試（功能已移除/被取代）」vs「揭露真產品缺陷」的判準。
- optimization_e2e 6 紅是否含真缺陷（SPEC 曾點名 engine_partial）。

## 執行順序（依賴）
1. A1 frozen 文件 ✅ → A1 phase2（委員會 Q1）
2. #2 d* fracdiff 大型管線（吸收 C）
3. B 殭屍分簇修（委員會 Q2 定原則後派執行端）
4. #3 tier profile（#2 後）

## 委員會三方裁定（2026-06-15，Codex+Composer 獨立調查一致 + Claude reconcile）
> 報告：handoffs/20260615-batch3-committee-{codex,composer}.md。資料正確性鐵律滿足（三方一致）。

| Q | 裁定 | 修法 | 信心 |
|---|---|---|---|
| Q1 retention | **B** | 加 `last_generated_at`：每次同 key add 刷新之；auto_cleanup/「最近未命名」改依 `last_generated_at` 排序（legacy 無此欄 fallback `created_at`）；created_at 維持首次+merge-preserve；非破壞性遷移。修 phase2 + lifecycle 測試證明「重跑舊未命名 run 回到保留 5 內，alias/created_at 不變」 | 0.95 |
| Q3 winsorize | **非 production bug，測試過時** | production causal rolling 正確（commit fff522b 因果化）；測試誤比 causal vs global。拆 `test_transform_single_optimized_df_end_to_end`：causal 模式比 rolling PIT oracle；`causal_preprocessing=False` 才比 `_winsorize_2d_inplace`/nanquantile。保留 future-perturbation 不變量。**禁改 production 回 full-sample、禁放寬容差** | 0.99 |
| Q4 golden | **刻意 schema bump** | raw_v1→raw_v2（commit 7427c72）。更新 `tests/_golden/v2_ts/g1_baseline_fingerprint.json` 的 `manifest_allowlist.feature_schema_hash`→`93ef6756efafdba58023f6c09f9ac872c11f19ccf1c754952b7cfc4153016468`；加註綁 schema_version。不重生其他指紋 | 0.99 |
| Q5 engine | **tail-risk 正常，CGSA metadata 缺口** | streaming CGSA 硬寫 metadata `feature_names=[]`（commit 816b3f8）。**採保守版（Codex 輸出大小警告）**：E2E 測試改查 CGSA registry/manifest schema 驗 `tr_` 在/`ms_` 缺 + 加 `failed_engines==("microstructure",)`/`engine_partial` 斷言；**不**把上千欄名灌進 production response（違反最小輸出原則） | 0.97 |

## B 殭屍剩餘簇（執行端逐簇判：test-lag 更新 vs 真缺陷 BLOCKED）
phase_d 缺 doc(7)/memory_chunking 簽名(5)/l7_parallel_persist(9)/hardware(5)/config defaults(2)/cgsa_resume(5)/feature_storage mixed dtype(1)。原則：對齊刻意 API 變更=更新測試（禁放寬斷言遮真 bug）；功能已移除=刪測試；疑真缺陷（尤其碰 merge 對齊/resume/dtype 溢位等資料正確性）=停手標 BLOCKED 回報委員會。
