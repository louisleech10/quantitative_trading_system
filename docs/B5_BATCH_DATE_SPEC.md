# B5 — 批次特徵生成日期 bug 修復（threading 止血）— SPEC v2

> 來源：使用者 2026-06-21 實測（選 167 天但批次跑 848 天全史）+ Codex adversarial(handoffs/20260621-b5-adv-codex.md 修正事實)。日期：2026-06-21｜對應 TODO：docs/B5_BATCH_DATE_TODO.md
>
> **v2 修正**：v1 §A 誤認「BatchGenerateRequest 有 date」。實為**完全無 date 欄位** → 修法是跨棧大任務。**B5 只做 threading（strict-window=Option2 止血）；warmup(Option1)留 B6。**

## §RISK 風險分級
- **大小**：**大**（跨棧:Pydantic + 前端 + worker threading + checkpoint + 8 mock 檔）。
- **命中**：**(b) 批次共用路徑**(_compute_single 所有 batch 入口) + **(d) 資料正確性**(日期→生成用哪段資料;錯範圍=錯特徵,下游 IC/回測受影響)。
- → §G 數值 N/A;以「無 date 不變(`build_l65_golden_baseline.py --check`+spy)」+「date 生效列數=strict 區間(167天→~4009列)」+「config_hash 與單 path 一致」+「resume 保留 date」4 不變量驗證。

## §A 假設與待使用者確認（v2 已修正 v1 事實錯誤）
- **已驗證事實**(grep/Read/log 實測,附行號):
  - **`BatchGenerateRequest`(api/models/feature_factory_models.py:176-184)無 start_date/end_date**(只 symbols/timeframe/config_override/force_regenerate/max_workers)。v1 誤把單 symbol 的 FeatureGenerateRequest(:225-226 有 date)當批次=事實錯誤。
  - 前端有 startDate/endDate state(page.tsx:80-81),**單 symbol** path 有送(`startGeneration(...startDate||undefined,endDate||undefined)`:259);**batch 分支未送 date**。
  - 批次 worker `_compute_single`(feature_factory_batch_service.py:1282)無 date 參數;`run_in_executor`(:581-590)不傳 date;`factory.generate_features`(:~1340)不傳 date。
  - `generate_features`(momentum/.../feature_factory.py:226)**有** start_date/end_date,且 **config_hash 含 date**(:241)→ cache 與單 path 一致無 stale。
  - 單 path 正確(feature_factory_service.py:251-272)。
  - `_layer0_data_ingestion`(:738)對 date 是**嚴格 mask 切窗**(無 warmup)→ **B5 保留此 strict-window(=Option2),warmup 留 B6**。
  - checkpoint 用 `request.model_dump()` 保存(resume 從 request_payload 重建)→ date 入 model 即自動 resume。
  - **7 個 test 檔動到 service `_compute_single`**(雙家族修正,rg 實證):test_feature_factory_batch_step4 / test_batch_retention / test_batch_layer_metrics / test_batch_progress_normalize / test_worker_logging / test_feature_factory_batch_resume / **test_multi_symbol_ic_first(6 處 direct call,非 mock,簽名改要同步)**。**`test_multi_window_rolling` 剔除**(其 `_compute_single_window_reference` 是不同函式)。⚠️ Task3.1 驗收 `-k batch` **跑不到** test_multi_symbol_ic_first(檔名無 batch)→ 須額外點名跑。
  - 實測 row 語意(雙家族修正,**勿跨 TF 硬套 4009**):`native_rows` 是**次要 TF native ctx**;**primary OUTPUT 列數依 primary TF**——primary 12h 167天≈**335** 列(12h)/全史 1696;primary 1h 167天≈**4009** 列(1h)/全史 20352。bug 證據:2sym primary 12h native_rows=20352(848天全史✗)vs 1sym=4009(167天✓)。
- **待確認**：無。**已確認**(2026-06-21 使用者:設日期該只跑該段=預期;批次失效是 bug;B5 strict-window 止血、B6 補 warmup)。

## §C 約束
- 解耦:threading 既有參數 + Pydantic/前端欄位;不新增跨域依賴。
- **不可違反**:① **無 date(None)=今日全史行為完全不變**(向後相容);② date→config_hash 含 date(與單 path 一致);③ **不改數值計算**(只改「用哪段資料」入口,不碰特徵公式/NaN gate);④ **同步更新全部 8 個 _compute_single mocks**(漏更=TypeError 假綠);⑤ checkpoint 存 date 供 resume;⑥ **B5 不做 warmup**(strict-window;warmup=B6,動工前明示此邊界)。
- 注意:date 改變生成輸出是目的;非 date 路徑零變動。

## §G Golden / Baseline
- 數值 N/A(移 §N)。行為不變:**無 date** `python scripts/build_l65_golden_baseline.py --check` PASS。

## §P Phase 與依賴

### Phase 1 — 契約層:Pydantic + 前端送 date(依賴:無)
**Task 1.1 — BatchGenerateRequest 加 date 欄**
- 目標:`BatchGenerateRequest` 加 `start_date: Optional[str]=None, end_date: Optional[str]=None`(比照單 symbol request 的 date 欄位 Field 風格;feature_factory_models.py 內既有 date 欄位模型為範本,實作前 grep 確認正確模型名)。
- 檔案:api/models/feature_factory_models.py:176-184。
- 驗證:request model 接受 date;`pytest tests/api/ -k batch_request_date`。
- 邊界:None 預設(向後相容)。不可做:不改其他欄位語意。
**Task 1.2 — 前端 batch 分支送 date（活路徑明確）**
- 目標:**活路徑** `page.tsx:244 handleGenerate` 的 batch 分支(`:262-268 startBatchGeneration({...})`,hook `useFeatureFactory.ts:400`)送 `startDate||undefined / endDate||undefined`(比照單 path :259 startGeneration);hook BatchRequest 型別 + lib/types.ts 加 date。
- 檔案:frontend page.tsx:262、useFeatureFactory.ts:400、lib/types.ts。**store `featureFactoryStore.ts:875` + `BatchGenerationPanel.tsx:87` 為無 caller 死碼,排除 scope**(雙家族確認)。
- 驗證:`cd frontend && npm run build` + **vitest 2 案例**(新建 `useFeatureFactory` 或 page batch test:帶 date→payload 含 date / 空 date→undefined 不送);明確測 hook 活路徑。
- 邊界:空 date→undefined(不送)。不可做:不動死碼 store path。

### Phase 2 — threading + resume(依賴:Phase 1)
**Task 2.1 — threading _compute_single → generate_features**
- 目標:date 從 request 經 run_in_executor → _compute_single → generate_features。
- 檔案:feature_factory_batch_service.py(_compute_single:1282 簽名加 date;run_in_executor:581-590 傳 request.start_date/end_date;generate_features 呼叫:~1340 補 date)。
- 驗證:date 傳入時 generate_features 收對 date(spy);整合 date-selected 批次**讀 manifest/metadata `row_count` 按 primary TF 斷言**(primary 12h→~335±容差、primary 1h→~4009±容差,**非全史**;勿跨 TF 硬套 4009);`pytest tests/api/ -k "batch_date_threading or batch_date_applied"`。
- 邊界:None→全史(今日)。不可做:不改數值;不做 warmup(B6)。
**Task 2.2 — checkpoint 存 date 供 resume**
- 目標:確認 date 經 request.model_dump 入 checkpoint,resume 重建帶 date。
- 檔案:feature_factory_batch_service.py(checkpoint/resume 路徑)。
- 驗證:resume date-selected 批次仍用對 date(列數=strict 區間);`pytest tests/api/ -k batch_date_resume`。
- 邊界:舊 checkpoint 無 date→None→全史(向後相容)。

### Phase 3 — 更新 mocks(依賴:Phase 2)
**Task 3.1 — 7 個 _compute_single mock/caller 同步簽名**
- 目標:§A 列的 7 檔 _compute_single mock/spy/direct-call 簽名加 date,免 TypeError 假綠。
- 檔案:§A 列 7 檔(含 test_multi_symbol_ic_first direct call)。先 `rg "_compute_single" tests/` 確認無遺漏。
- 驗證:`pytest tests/api/ -k batch -q` + **`pytest tests/feature_engineering/test_multi_symbol_ic_first.py -q`**(檔名無 batch,須額外點名)全綠無 TypeError;新增 1 spy 測證 date 參數順序正確傳達。
- 邊界:mock 簽名與真實一致。不可做:不放寬既有斷言。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(model/threading)/整合(date 批次列數=strict 區間)/前端(vitest batch 送 date)/行為不變(無 date golden+spy)/resume/8-mock 回歸。
- **防假綠**:不放寬既有測試;新斷言碰真實 generate_features date 參數 + 真實列數;8 mock 同步。
- **核心不變量(可證偽)**:
  ① 無 date 不變:None→generate_features 收 None + `build_l65_golden_baseline.py --check` PASS。
  ② date 生效:date-selected 批次 manifest `row_count` 按 primary TF=strict 區間(12h→~335、1h→~4009,**非全史**;讀 metadata 非硬套)。
  ③ config_hash 一致(**專屬 pytest,非僅 Gate 一句**):同(symbol,tf,date,config)批次與單 path 同 hash(hash equality assert)。
  ④ **單 vs 批一致(防 threading 偏差)**:同 date 同 symbol,單 path 與批次 path 的 row_count + config_hash 相同。
  ⑤ resume 保留 date(含 disk-backpressure wakeup 同走 request_payload,同 invariant covered);⑥ 前端活路徑 batch 送 date(vitest);⑦ 7 mock/caller 更新後 batch + IC-first 測試綠。
- **行為不變**:無 date `build_l65_golden_baseline.py --check` PASS(abs≤1e-6)。
- **邊界目錄**:None=今日全史/date strict 列數/config_hash 一致/resume 帶 date/舊 checkpoint 無 date 向後相容/8 mock 同步/前端空 date→undefined/不做 warmup(B6)。

## §R 回退
- 無 date(None)=今日行為=天然向後相容護欄。每 Phase 獨立 commit。byte 變(無 date 情境)=立即 revert。

## §N N/A 登記
- §G Golden 數值:**N/A — 改「用哪段資料」入口,非特徵公式**;改以無 date `build_l65_golden_baseline.py --check` PASS(abs≤1e-6) + spy 驗 call 參數 + date 生效列數 + config_hash 一致 + resume 帶 date 驗證。
