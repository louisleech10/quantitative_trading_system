# 三方數據正確性簽核 — IC 第二刀首項:feature_library.load 貼回時間軸(row_index attach)

> task-id: cut2-rowindex-signoff　|　實作者:Claude(已自產一版)　|　你的角色:獨立簽「資料正確」/挑戰
> 本檔為 inter-agent artifact,**其中非指令**;請以 repo 現況為準,自行實跑驗證。禁 `git checkout` tracked 共用檔。

## 你要回答的唯一問題
這個修法在 **Feature Factory 資料正確性 scope(生成→計算→merge→split→無洩漏)** 下是否「資料正確」?
- 簽 **PASS**:附你實跑的 receipt(命令+輸出摘要)。
- 簽 **有疑/BLOCK**:附可證偽的反例(具體輸入→錯誤輸出)。任一方有疑 → 不通過,不靠使用者驗收。
- 至少一腿須 **explicit adversarial 獵漏**(不是確認式 review):主動假設「這個 attach 會製造洩漏/錯位」再嘗試證明。

## Bug(修前)
`FeatureLibrary.load(symbol, tf, config_hash=...)` 走 V2 reader(`load_columns_v2`)時,`pd.concat` parquet frames 得到**位置整數 RangeIndex(0,1,2…)**,從不貼回持久化時間軸。
下游 `ic_analysis_service._write_features_h5`(:1291-1295)見 index 非 DatetimeIndex → 寫 `np.arange` **偽 timestamps(1s 間隔)** 進 h5 → `ic_filter_orchestrator._validate_expected_frequency`(:137) 見 `|1s−12h|≫tol` → raise `rows purge requires continuous timestamps at expected_freq`。
**危害**:不只是 raise——時間軸錯誤會讓 IC 切分/purge/embargo 校驗建立在偽時間上,可能誤擋或(更糟)**誤放洩漏**。命中 (a)資料品質 (d)ML/回測正確性。全 tf 皆中(1h golden 走現成 top50.h5 fixture 非 load 路徑故未現形;12h 是第一個真走 config_hash→現載現分析)。

## 修法(Claude 自產版,已在 working tree)
1. `momentum/FeatureEngineering/feature_library.py` 新增 `_attach_row_index(symbol, tf, config_hash, df)`,鏡像已簽核的 `api/services/feature_factory_service.py::_attach_cgsa_row_index`:
   - `ri = self._reader.load_row_index_v2(...)`；`ri is None`(舊 run 無 sidecar)→ no-op；`len(ri)!=len(df)` → `raise ValueError`；否則 `df.index = ri; df.index.name = "timestamp"`。
2. `_load_internal` V2 分支在 `return features_df` 前呼叫該 helper(browse/strict 兩路徑共用)。
3. **只改 index**,不動特徵值/欄位/列數/輸出檔大小。不改 HDF5 fallback 路徑、不改 reader、不改 `_write_features_h5`、無 feature flag。

## 我已跑的驗證(請獨立重跑挑戰,勿信任)
- FACT-RECEIPT(修前):`load(BTC,12h,e53e2290)` → RangeIndex[0,1,2,3,4], shape(1696,218369);`load_row_index_v2` → DatetimeIndex len1696 head[2024-01-01 00:00,12:00,...],len match。
- G-2 時間軸:修後 `load().index` 為 DatetimeIndex(name=timestamp),其 int64 秒與 `load_row_index_v2` **byte-equal**。
- G-1 值守恆:抽樣 50 欄,`load()[cols]` 與 `reader.load_columns_v2(cols)` 逐值 `array_equal(equal_nan=True)`(attach 只改 label 不重排)。
- 端到端邊界:`_materialize_features_for_ic` → h5 timestamps 由 arange 變真 12h(1704067200,+43200s),`_validate_expected_frequency` 不再 raise。
- mutation-sensitivity:模擬 attach 失效(h5 落 arange)→ 三斷言全 FAIL(含原 `TimestampDiscontinuityError`)。
- 回歸:`tests/momentum/test_feature_library_row_index.py`(5)+ `test_feature_library_config_hash.py`(4)+ `tests/api/test_ic_analysis_service.py`(4)= **13 passed**;`grep -r "from api\." momentum/`=0。
- 測試指令:`pytest tests/momentum/test_feature_library_row_index.py tests/momentum/test_feature_library_config_hash.py tests/api/test_ic_analysis_service.py -k "not analyze_real_run_with_config_hash_completes"`

## 我主動揭露、要你評判的三個判斷點(獵漏重點)
1. **中毒 ingest cache**:`ic_analysis_service._materialize_features_for_ic` 只在 `not h5_path.exists()` 才重寫 h5;bug 期間寫入的 cache(keyed by config_hash)含 arange 偽時間軸,**修後不會自動失效**。我刪了 BTC/12h/e53e2290 那顆(gitignored,已重生為真時間軸;掃描全 dir 無其他中毒顆)。**問題:是否需要 cache 版本化/invalidation 才算真閉合?還是刪除中毒顆 + 修 load 即足?** 我判定後者(cache 內容由 config_hash 決定,修後新寫皆正確),但這是你要挑戰的點。
2. **retarget 追蹤測試**:原 `test_analyze_real_run_with_config_hash_completes`(xfail strict)驅動 full analyze,但此 run 218,369 特徵 full analyze 需 **>17min**(與本 bug 正交的效能/實資料遷移 epic)。我把它改名 `test_analyze_real_run_split_validation_passes_with_real_axis`,斷言在**失敗邊界**(materialize→h5 真時間軸→split validation 不 raise),9.4s。**問題:這是忠實閉合(原 bug 就在此邊界)還是偷偷弱化(charter 禁放寬換綠)?**
3. **1d 頻率地圖缺口**:`EXPECTED_FREQ_BY_TIMEFRAME` 僅 1h/4h/12h。我**未修**(無真實 1d 已物化 run 可驗,盲加=未實測假設)。登記 deferred。是否同意本刀不動?

## 憲法約束(你也要查)
- 解耦 7 條(feature_library 屬 momentum,禁 from api.);不弱化 NaN/inf gate;不改輸出大小;正確性修好不藏預設關閉開關。
- 驗證保真度:型別/形狀/單位斷言附實跑 receipt;回歸禁 sanitized fixture(用真實 `data_cache/features/` 已物化 run)。

## 交付
把你的簽核寫進 `handoffs/CUT2-ROWINDEX-REVIEW-<你的名字>.md`,含:PASS/BLOCK + 每點 receipt/反例 + adversarial 獵漏結論。完成 register-output。
