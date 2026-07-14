# DECOUPLE-FIX4 TODO　(v2 / DRAFT / 基於 docs/DECOUPLE_FIX4_SPEC.md r2 / 2026-07-14;r1 依三家 adversarial BLOCKING/MAJOR 全修)

## 階段 1 SPEC 索引(100% 覆蓋追溯;r2 依 ADV-CODEX-8 改 ID 表)
| ID | SPEC 原文節錄(≤30字) | 本檔位置 |
|---|---|---|
| Task 0 | 「G1 修前基準+G2 場景盤點,唯讀」 | Task 0 |
| Task 1 | 「死碼修復+來源契約(d 紅線)」 | Task 1.1 |
| Task 2 | 「load_row_index_v2 呼叫點改 create_feature_reader」 | Task 1.2 |
| Task 3 | 「去 module-level singleton default」 | Task 1.3 |
| Task 4 | 「公開委派 API,Analysis 不碰 private」 | Task 1.4 |
| G1 | 「行為不變(path 流)…禁 aggregate sum」 | Task 0/1.1 |
| G2 | 「run 選擇正確性…三場景」 | Task 0/1.1 |
| T1a-T1e | 「pytest tests/api/test_ic_transform_feature_loading.py」 | Task 1.1 驗證 |
| T2a/T2b | 「cgsa or row_index 綠;grep→0」 | Task 1.2 驗證 |
| T3a/T3b | 「scanner R4 PASS;batch 三檔+新檔 0 failed」 | Task 1.3 驗證 |
| T4a/T4b/T4c | 「grep→0;coverage 綠;公開==私有」 | Task 1.4 驗證 |
| M1-M4 | 「四 mutant 實跑…還原後全綠」 | Phase 測試 |
| RISK-HIT | 「b,d」 | §0 |
- 合計:Task×5(含 Task 0)、Golden×2、測試驗證 ID×12(T1a-e,T2a-b,T3a-b,T4a-c)、mutation×4。無「等/以此類推」。

## §0 全域規則與約束(執行端讀完即可遵守)
- **解耦 7 條**(canonical=CLAUDE.md「The 7 Decoupling Rules」;r2 依 ADV-CODEX-7 補全):R1 momentum 不 import api(本票不碰);**R2 跨域走 Protocol**(Task 1.4:Analysis 只准經公開 API);**R3 api 用 factory**(Task 1.1/1.2 正是修此;禁新增 concrete 建構);**R4 services 不互 import**(Task 1.3 正是修此;禁 None+lazy import 繞道);R5 config 單源/R6 測試獨立 pytest/R7 DTO 不跨界(本票不碰,不得引入新違規)。
- 修完 `bash scripts/check_decoupling.sh` 預期 **R2=5/R3=10/R4=0(合計 15)**(r2 依 ADV-GROK-2 更正;R2-4 只消 private 呼叫,import 紅字留白名單票——**看到 R2 仍=5 是正確結果,不得越界去消**)。
- **Task 1 來源契約(凍結,不得自行變更)**:explicit `features_path` 最優先 → 無 path 才 `self._feature_library.load(symbol, timeframe, config_hash=req_config_hash)`;禁 library-first。
- 引用 SPEC §A receipt;涉型別/形狀斷言自附 FACT-RECEIPT 實跑。
- 不可違反:不弱化 NaN/inf gate、不改輸出大小、禁合成 fixture、不寫 `data_cache/`(既有運行產物除外)。
- 防假綠:不得放寬/刪除既有斷言;G1 禁 aggregate sum hash(用有序序列化 sha256+`assert_frame_equal(check_exact=True, check_dtype=True)`)。
- Logging:`get_logger(__name__)`;Task 1.1 保留 warning log。
- 兩輪斷路器:任何 Task 卡 2 輪 → 停手回報。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B0 | Task 0 | 無 | 唯讀取證須在改碼前(G1 修前基準) | 小 |
| B1 | Task 1.1-1.4 | B0 | 四修復互獨立、一次派工、各自獨立 commit | 中 |

- B0→B1 Gate:`handoffs/DECOUPLE-FIX4-G-RECEIPT.md` 存在且含 G1 修前基準(4 類有序 sha256)+G2 雙 config run 清單;registry 缺雙 config → 停工上報。
- B1 驗收 Gate:T1a-e/T2a-b/T3a-b/T4a-c 全 PASS+G1/G2 PASS+M1-M4 mutation receipt(kill 後還原全綠)+scanner 15(5/10/0)。

### Batch 派工 prompt(可直接複製)
- B0:「讀 docs/DECOUPLE_FIX4_TODO.md §0+Task 0,唯讀取證產出 handoffs/DECOUPLE-FIX4-G-RECEIPT.md;不得改任何 source/測試/data_cache。」
- B1:「讀 docs/DECOUPLE_FIX4_TODO.md §0+Task 1.1-1.4(冷啟動自足),逐 Task 實作+自跑驗證命令+M1-M4 mutation receipt,各 Task 獨立 commit(不 push);結構化收尾(ASSUMPTIONS_VERIFIED/TESTS_RUN/FAILURES_SEEN)。」

## Phase 1 — 修復 4 筆真違規(完成後:scanner R4=0/R3=10/R2=5,IC transform 來源契約凍結且 library 分支釘 hash 生效)

### Task 0 — §G receipt(SPEC ref:§G/Task 0)
- 輸入/輸出:輸入=現行 code+真實 registry(`data_cache/features/registry.json`,11 entries,BTCUSDT/12h 雙 config 已證存在);輸出=`handoffs/DECOUPLE-FIX4-G-RECEIPT.md`。
- 實作要點:①G1 修前基準:對真實存在的 features 檔(真實 ic_ingest_cache/*.h5 或 registry run 的真實 parquet 檔路徑,receipt 記選擇),以現行 `_load_features_for_transforms` 等效邏輯(直呼該 method 或等價 pd.read_hdf/read_parquet,記明)讀出 DF,存 4 類有序 sha256:`sha256(df.index 序列化 bytes)`/`sha256(",".join(df.columns))`/`sha256(df.to_numpy().tobytes())`(欄序固定)/`sha256(df.isna().to_numpy().tobytes())`+shape+per-col dtype;②G2 盤點:`create_feature_library()._registry` 實跑列出 ≥2 config 的 symbol/tf(hash 全印);③receipt 記完整命令+stdout。
- 修改檔案:無(receipt 新建;臨時腳本放 scratch/ 或 python -c)。既有 caller:N/A。
- 不可做:不改 source/測試;不寫 data_cache/;無雙 config run 時不得造假 → 上報。
- 邊界:(1) ic_ingest_cache 無現成 .h5 → 用 registry parquet 真實檔並記明;(2) 多組雙 config → 任選記明。
- 風險緩解:§G「FAIL→停工上報」。
- 驗證:receipt 存在且含 G1 基準(shape/dtype/4 sha256)+G2 run 清單(≥2 config hash 實印);缺一即 B1 不啟動。

### Task 1.1 — R3-10:`_load_features_for_transforms` 來源契約(SPEC ref:Task 1;RISK d)
- 輸入/輸出:輸入=Task 0 receipt;輸出=修改後 helper+caller+新測試檔。
- 實作要點:①`_apply_transforms_sync`(L925-930)讀 `task_info.get("req_config_hash")` 傳入 helper;②helper `_load_features_for_transforms(self, symbol, timeframe, features_path, config_hash=None)`:**分支順序=features_path 先**(現有讀檔邏輯原樣搬,不動);無 path 且有 symbol/tf → `return self._feature_library.load(symbol, timeframe, config_hash=config_hash)`(try/except 保留 warning log;except 後=現行「無可用來源」錯誤路徑,exception type/message receipt 記);③刪 `from momentum.FeatureEngineering.feature_library import FeatureLibrary`+`FeatureLibrary()` 死碼;④全缺行為不變(receipt)。
- 修改檔案:`api/services/ic_analysis_service.py` `_load_features_for_transforms`(L991)+`_apply_transforms_sync`(L925-930);新建 `tests/api/test_ic_transform_feature_loading.py`。既有 caller:僅 L930(codex 實證)。
- 不可做:不修 L183-193 `_registry` 穿透;不採 library-first;不動 `_materialize_features_for_ic`/float32 寫入;不擴 URI 支援(known limitation)。
- 邊界:(1) `req_features_path` 為 `parquet:...` URI → 行為維持現狀(不支援);(2) registry 無該 run → load raise → 錯誤路徑==修前。
- 風險緩解:G1/G2+M1-M4。
- 驗證:`pytest tests/api/test_ic_transform_feature_loading.py -q` 0 failed:**T1a** path+symbol/tf 並存 → 讀 path 且 library mock `assert_not_called`;**T1b** 無 path+pinned hash → mock 斷言 `load` kwargs `config_hash==pinned`;**T1c** 無 path+None → kwargs None;**T1d** load raise → exception type==修前(斷言具體 type);**T1e** 全缺 → ==修前。+G1(修後重跑 4 sha256==修前基準)+G2 三場景 PASS。

### Task 1.2 — R3-9:改走 factory(SPEC ref:Task 2)
- 輸入/輸出:輸入=無前置;輸出=呼叫點改 factory。
- 實作要點:①FACT-RECEIPT `sed -n '273,279p' momentum/factories.py`(簽名 `Optional[str]=None`,相容已證);②`from momentum.factories import create_feature_reader`(函式內,位置同原 L5454);③`reader = create_feature_reader(str(self._cgsa_feature_base_path(context)))`;後續呼叫不動。
- 修改檔案:`api/services/feature_factory_service.py` L5450 附近 CGSA row_index helper(函式名以實檔為準,receipt 記)。既有 caller:CGSA 路徑,簽名不變無同步。
- 不可做:不動同檔 run_locks/run_paths/hardware_utils import;不改回傳型別。
- 邊界:(1) config_hash 缺 → 上游 ValueError 不變;(2) factory 回傳 FeatureReader 具 `load_row_index_v2`(已證)。
- 風險緩解:⊘(同義改寫)。
- 驗證:**T2a** `pytest tests/api -k "cgsa or row_index" -q` 0 failed;**T2b** `grep -c "feature_reader import FeatureReader" api/services/feature_factory_service.py` 輸出 `0`。

### Task 1.3 — R4-1:必填注入(SPEC ref:Task 3)
- 輸入/輸出:輸入=無前置;輸出=adapter 必填+組裝點同步+新測試檔。
- 實作要點:①刪 `api/services/feature_factory_batch_adapters.py:9` import;②兩 class `__init__(self, service: Any)` 必填(禁 None default/lazy import);③`api/main.py:59-60` 改 `FeatureFactoryBrowseAdapter(feature_factory_service)`/`FeatureFactoryQualityAdapter(feature_factory_service)`(L29 已有 import);④`tests/performance/step6_multitf_batch_benchmark.py`:**補 `from api.services.feature_factory_service import feature_factory_service`** 後 L148-149 兩 call 傳入;⑤顯式注入 3 檔 6 call(retention 1/quality 4/resume 1)不動;⑥新建 `tests/api/test_batch_adapters_injection.py`:無參建構 `pytest.raises(TypeError)`×2 class+main/benchmark 組裝 import+construction 冒煙(不執行 benchmark 主體)。
- 修改檔案:`api/services/feature_factory_batch_adapters.py`(兩 `__init__`)、`api/main.py`、`tests/performance/step6_multitf_batch_benchmark.py`、新建 `tests/api/test_batch_adapters_injection.py`。既有 caller:上列全部(無參點僅 2 檔 4 call,三家實證)。
- 不可做:不引 service locator;不動 adapter 其他方法;不跑 benchmark 主體。
- 邊界:(1) 無參建構 → TypeError fail-fast(負向測試);(2) stub service 可注入(既有測試證)。
- 風險緩解:⊘。
- 驗證:**T3a** `bash scripts/check_decoupling.sh` Rule 4=PASS(0);**T3b** `pytest tests/api/test_batch_retention.py tests/api/test_feature_factory_batch_quality.py tests/api/test_feature_factory_batch_resume.py tests/api/test_batch_adapters_injection.py -q` 0 failed。

### Task 1.4 — R2-4:去 private(SPEC ref:Task 4)
- 輸入/輸出:輸入=無前置;輸出=公開 staticmethod+coverage 4 處改呼叫+新測試檔。
- 實作要點:①`momentum/FeatureEngineering/feature_reader.py` 增 `@staticmethod def get_v2_artifact(manifest: Dict[str, Any], kind: str)` = `return FeatureReader._get_v2_artifact(manifest, kind)`(委派;private 保留);docstring 標 stable public;②`momentum/Analysis/coverage_analyzer.py` **4 處**(L136/403/415/500)改 `FeatureReader.get_v2_artifact(...)`;L96 `V2_MANIFEST_NAME` 不動;③新建 `tests/momentum/test_feature_reader_public_artifact.py`:公開==私有(含 missing-key 案例)。
- 修改檔案:`momentum/FeatureEngineering/feature_reader.py`、`momentum/Analysis/coverage_analyzer.py`、新建 `tests/momentum/test_feature_reader_public_artifact.py`。既有 caller:private 僅 coverage+feature_reader 自身(grep 已證)。
- 不可做:不改 `_get_v2_artifact` 內部;不刪 private;L14 concrete import 保留;不重構 coverage 其他部分。
- 邊界:(1) manifest 缺 kind key → 公開==私有(`==` 斷言入測試);(2) 第三 caller → grep 全 repo 0 行。
- 風險緩解:⊘。
- 驗證:**T4a** `grep -rn "_get_v2_artifact" momentum/Analysis api --include="*.py"` 輸出 0 行;**T4b** `pytest tests/momentum -k coverage -q` 0 failed;**T4c** `pytest tests/momentum/test_feature_reader_public_artifact.py -q` 0 failed。

### Phase 1 測試 + Phase Gate
- 單元:T1a-e/T3 負向+冒煙/T4c 等值。邊界:各 Task 邊界入測試或 receipt。效能:⊘。
- mutation(§V,RISK d):**M1**=library 分支換回 `FeatureLibrary()` → T1b/T1c FAIL;**M2**=刪 path fallback 分支 → T1a FAIL;**M3**=library 分支硬寫 `config_hash=None` → T1b FAIL;**M4**=library 移到 path 前 → T1a FAIL。四 mutant 實跑輸出貼 receipt 後還原,還原後全綠。
- Phase Gate:T1a-e+T2a-b+T3a-b+T4a-c+G1/G2+M1-M4 全 PASS;`bash scripts/check_decoupling.sh` = **R2=5/R3=10/R4=0(合計 15)**;`pytest tests/api tests/momentum -q` 無新紅(pytest collect 副作用檔 `tests/golden/l65/test_inventory.txt` 依慣例 revert)。

## 階段 3 自檢(0 FAIL)
- 追溯:階段 1 表全 ID ↔ Task/Gate 一一對應,合計可機算(5 Task/2 Golden/12 測試 ID/4 mutation)。
- 深度:每 Task 要點≥3+簽名、檔案到函式、邊界≥2、驗證可證偽 ✓;新測試檔全數列入「修改檔案」(r2 修 ADV-CODEX-4)✓。
- 語義:Task 1.1 與 1.2 不同檔;1.3 不碰 1.2 檔;來源契約與 RECONCILE「改用 self._feature_library」一致且經 r2 凍結 ✓;G1 前置由 Task 0 產出 ✓。
- 全棧跨層:純後端,⋅跳過。
- 錨點:`## §0`/`## §B`/每 Task 驗證·邊界·不可做 ✓。

## 階段 4 Frozen 前 handoff
SPEC=docs/DECOUPLE_FIX4_SPEC.md TODO=docs/DECOUPLE_FIX4_TODO.md FOCUS=r2 修訂閉合確認(三家 BLOCKING/MAJOR 是否全關)
狀態:**Frozen**(2026-07-14 三家閉合重驗全 VERDICT: FROZEN-OK,見 handoffs/DECOUPLE-FIX4-ADV-{codex,composer,grok}.md 閉合節)
