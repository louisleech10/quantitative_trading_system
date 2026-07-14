# DECOUPLE-FIX4 — 解耦 triage 真違規 4 筆修復 — SPEC

> 來源 PLAN/診斷：handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md(四家戳記 PASS)　|　日期：2026-07-14(r2,依三家 adversarial 修訂:ADV-{GROK,COMPOSER,CODEX} 全 BLOCKING/MAJOR 已吸收)　|　對應 TODO：docs/DECOUPLE_FIX4_TODO.md

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：中(4 個 contained 修復,但 Task 1 碰 IC 特徵來源選擇)。
- **命中高風險原則**：(b) 跨模組共用路徑;(d) ML/回測正確性(Task 1 的來源選擇錯誤=silent wrong-run 特徵餵給 transform)。
- RISK-HIT: b,d
- 命中 (d) → §G 必填、adversarial review 必跑(r1 已跑三家,BLOCKING 修訂即本 r2)。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**(receipt;r2 依三家 VERIFY 修正×3)：
  - FACT-RECEIPT: `grep -n "def _load_features" api/services/ic_analysis_service.py` → `991: def _load_features_for_transforms(`(grok/composer/codex 三家實跑一致;**實名=`_load_features_for_transforms`,instance method,簽名 `(self, symbol, timeframe, features_path)`**;r1 誤寫 `_load_features` 已更正)。
  - FACT-RECEIPT: codex 實跑 `inspect` → `FeatureLibrary.load(self, symbol, timeframe, *, config_hash=None, ...)`——**config_hash 是既有可選 keyword**;缺席時 `find_latest_materialized`(feature_library.py L108-114)。
  - FACT-RECEIPT: codex 實跑 `sed data_cache/features/registry.json` → registry 11 entries,**同一 BTCUSDT/12h 至少 2 個 materialized config**(e53e…/f754…) → latest≠pinned 是真實場景非假想;且 registry 欄位=`hdf5_relative_path` 指向 `feature_manifest.json`,**非**可直讀 `.parquet/.h5`。
  - FACT-RECEIPT: 三家實跑 caller 鏈 → `start_analysis` 存 `req_config_hash`(L76)但 `_apply_transforms_sync`(L925-930)**不讀**;`_materialize_features_for_ic` 用 `library.load(..., config_hash=...)`(L1255-1258)後 `_write_features_h5` 以 **float32** 寫 `data_cache/reports/ic_ingest_cache/*.h5`(L1302);production caller 僅同檔 L930。
  - FACT-RECEIPT: `sed -n '273,279p' momentum/factories.py`+codex 實跑 → `create_feature_reader(feature_base_path: Optional[str]=None) -> FeatureReader`,positional str 相容(Task 2 安全)。
  - FACT-RECEIPT: 三家 `rg "FeatureFactory(Browse|Quality)Adapter\("` → **無參建構=2 檔 4 個 call**(`api/main.py:59,60`+`tests/performance/step6_multitf_batch_benchmark.py:148,149`);**顯式注入=3 檔 6 個 call**(retention 1/quality 4/resume 1);`api/main.py:29` 已 import `feature_factory_service`,**benchmark 檔目前無此 import(須補)**。(r1「4 測試檔其中 2 檔顯式」計數不實,已更正)
  - FACT-RECEIPT: `grep -n "_get_v2_artifact\|V2_MANIFEST_NAME" momentum/Analysis/coverage_analyzer.py` → **4 處 private 呼叫**(L136/403/415/500)**+1 處公開常數**(L96);`_get_v2_artifact` 已是 `@staticmethod`。
- **待使用者確認**：無(修法遵 RECONCILE 戳記裁決+使用者 2026-07-14「照順序完成三段」指令;來源優先序屬技術決策,依三家 adversarial 一致建議採 path-first,不問使用者)。
- **已確認結果**：`2026-07-14 使用者指示「修那 4 個小地方 → 建放行清單機制 → 幾件不急的整理 => 照你的順序完成上述三項」`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條(CLAUDE.md canonical 表);修完 `check_decoupling.sh` 紅字只准減不准增(現況 R2=5/R3=12/R4=1;**修後預期 R2=5/R3=10/R4=0,合計 15**——R2-4 只消 private 呼叫,concrete import 行留白名單票,故 R2 不減)。
- **Task 1 來源契約(本 SPEC 核心,r2 凍結)**:`_load_features_for_transforms` 的來源優先序=**①explicit `features_path` 最優先**(保 golden replay 語意+現行有效行為零變)**②無 path 時 `self._feature_library.load(symbol, timeframe, config_hash=req_config_hash)`**(釘 IC 分析當時的 run;req_config_hash 為 None 時=latest,與 IC 主路徑 L193-205 同語意)。禁 library-first。
- 其他:coverage_analyzer 是 Analysis 共用路徑;adapter 改必填後全部無參建構點(main+benchmark)須同步;不弱化 NaN/inf gate、不改輸出大小、不寫 `data_cache/`(除既有 ic_ingest_cache 正常運行產物)。

## §G Golden / Baseline（高風險(d)必填;r2 依 ADV-COMPOSER-2/5、ADV-CODEX-2/3 重設計）
- **feature/kline 條件**:不適用(不生成/計算/merge/split 特徵,只改讀取來源選擇);驗證用真實 registry run 的 .parquet/manifest 與真實 ic_ingest_cache .h5,禁合成 fixture。
- **r1 的「A==B 全項等值」設計作廢**——理由(三家實證):現行 fallback 讀 float32 materialized HDF5,library 回傳全精度,兩者**設計上就不 byte-equal**;且 registry 無可直讀 features_path。
- **r2 Golden = 兩件可證偽的事**(receipt 存 `handoffs/DECOUPLE-FIX4-G-RECEIPT.md`):
  - **G1 行為不變(path 流)**:對真實 task 語意(symbol/tf/features_path 齊備,用真實 ic_ingest_cache/*.h5 或真實 registry parquet 路徑),修前 vs 修後 helper 回傳 DataFrame `pd.testing.assert_frame_equal(check_exact=True, check_dtype=True)` 全等+有序序列化 sha256(index bytes/columns bytes/values bytes/NaN mask bytes 各自 sha256,**禁 aggregate sum**)。修前基準在改碼前實跑凍結。
  - **G2 run 選擇正確性(library 流,新生效能力)**:用真實 registry 的 BTCUSDT/12h 雙 config 場景——①傳 `config_hash=舊hash` → 載入 run 的 manifest/config_hash 斷言==舊hash(**非 latest**);②`config_hash=None` → ==`find_latest_materialized` 所選;③explicit path+symbol/tf 並存 → 讀 path(G1 同路)。三場景 receipt 附實跑 stdout。
- **通過條件(可證偽)**:G1 全等式 PASS+G2 三場景斷言 PASS;任一 FAIL → 停工上報委員會。真實 registry 若缺雙 config 場景 → 不得造假,上報(§A receipt 已證存在,預期不觸發)。

## §P Phase 與依賴

### Phase 1 — 全部 4 Task(依賴:Task 0→Task 1;Task 1-4 互獨立,各自獨立 commit)

**Task 0 — §G receipt(G1 修前基準+G2 場景盤點,唯讀)**
- 目標:改碼前凍結 G1 修前基準+列出 G2 可用雙 config run。檔案:無(新建 receipt 檔)。
- 改法:見 §G;腳本可放 `scratch/`或直接 python -c,receipt 記完整命令。
- 驗證:`handoffs/DECOUPLE-FIX4-G-RECEIPT.md` 存在,含 G1 基準 4 類有序 sha256+G2 場景 run 清單(registry 實跑列出,含 ≥2 config 的 symbol/tf)。
- 邊界:(1) registry 空 → 上報不造假;(2) 多組雙 config → 任選一組並記明。
- 不可做:不改任何 source/測試;不寫 data_cache/。

**Task 1 — R3-10:`_load_features_for_transforms` 死碼修復+來源契約(d 紅線)**
- 目標:實作 §C 來源契約。檔案:`api/services/ic_analysis_service.py` `_load_features_for_transforms`(L991)+caller `_apply_transforms_sync`(L925-930)。
- 改法:①`_apply_transforms_sync` 讀 `task_info.get("req_config_hash")` 傳入 helper(helper 簽名加 `config_hash: Optional[str] = None` 參數——**這是串既有欄位,非新 API**);②helper 內:先 `features_path` 分支(現有讀檔邏輯原樣不動);無 path 且有 symbol/tf → `return self._feature_library.load(symbol, timeframe, config_hash=config_hash)`;刪 `from momentum.FeatureEngineering.feature_library import FeatureLibrary` 與 `FeatureLibrary()` 死碼;③library 分支包 try/except 保留 warning log,except 後行為=現行「無可用來源」錯誤路徑(實跑 receipt 記 exception type/message);④全缺(symbol/tf/path 皆無)行為不變(實跑 receipt)。
- 既有 caller:僅 L930(codex 實證),同步於 ①。
- 驗證:`pytest tests/api/test_ic_transform_feature_loading.py -q` 0 failed,測項=T1a explicit path 優先(path+symbol/tf 並存 → 讀 path,library mock `assert_not_called`);T1b 無 path+pinned hash → `load` 收到 `config_hash==pinned`(mock 斷言 kwargs);T1c 無 path+hash=None → load 收 None;T1d load raise → 錯誤路徑行為==修前(斷言 exception type);T1e 全缺 → ==修前。+§G G1/G2 receipt PASS。
- 邊界:(1) `req_features_path` 為 `parquet:{symbol}:{hash}` URI(L510 列表用格式)→ 非檔案路徑,現行 fallback 本就不支援,**行為維持現狀,SPEC 標 known limitation 不擴**;(2) registry 無該 run → load raise → T1d 路徑。
- 不可做:不修 L183-193 `_registry` 穿透;不改 `library.load` 本體;不採 library-first;不動 `_materialize_features_for_ic`/float32 寫入。

**Task 2 — R3-9:feature_factory_service 改走 factory**
- 目標:`load_row_index_v2` 呼叫點改 `create_feature_reader`。檔案:`api/services/feature_factory_service.py` L5454-5457(CGSA row_index helper,函式名以實檔為準)。
- 改法:`from momentum.factories import create_feature_reader`(函式內,位置同原);`reader = create_feature_reader(str(self._cgsa_feature_base_path(context)))`(簽名相容已 receipt)。
- 驗證:`pytest tests/api -k "cgsa or row_index" -q` 0 failed;`grep -c "feature_reader import FeatureReader" api/services/feature_factory_service.py` 輸出 `0`。
- 邊界:(1) config_hash 缺 → 上游 ValueError 不變;(2) factory 回傳 FeatureReader 具 `load_row_index_v2`(codex receipt 已證)。
- 不可做:不動同檔 run_locks/run_paths/hardware_utils import。

**Task 3 — R4-1:batch_adapters 必填注入(composition root)**
- 目標:去 module-level singleton default。檔案:`api/services/feature_factory_batch_adapters.py`(兩 `__init__`)、`api/main.py:59-60`、`tests/performance/step6_multitf_batch_benchmark.py`(**須補 `from api.services.feature_factory_service import feature_factory_service` import 後傳入兩 call**;main.py L29 已有 import)、新增測試檔 `tests/api/test_batch_adapters_injection.py`。
- 改法:刪 adapters L9 import;`__init__(self, service: Any)` 必填(禁 None default/lazy import);組裝點如上同步;顯式注入的 3 檔 6 call 不動。
- 驗證:`bash scripts/check_decoupling.sh` Rule 4 段=PASS(0 violations);`pytest tests/api/test_batch_retention.py tests/api/test_feature_factory_batch_quality.py tests/api/test_feature_factory_batch_resume.py tests/api/test_batch_adapters_injection.py -q` 0 failed(新檔含:無參建構 `pytest.raises(TypeError)`;benchmark/main 組裝 import+construction 冒煙——不執行 benchmark 主體)。
- 邊界:(1) 無參建構 → TypeError fail-fast(新負向測試);(2) stub service 注入可行(既有測試即證)。
- 不可做:不引入 service locator;不動 adapter 其他方法;不跑昂貴 benchmark 主體。

**Task 4 — R2-4:coverage_analyzer 去 private**
- 目標:公開委派 API,Analysis 不碰 private。檔案:`momentum/FeatureEngineering/feature_reader.py`(新增公開 staticmethod)、`momentum/Analysis/coverage_analyzer.py`(**4 處呼叫** L136/403/415/500;L96 `V2_MANIFEST_NAME` 公開常數用法不變)、新增測試 `tests/momentum/test_feature_reader_public_artifact.py`。
- 改法:`@staticmethod def get_v2_artifact(manifest, kind)` = `return FeatureReader._get_v2_artifact(manifest, kind)`(委派;private 原名保留);docstring 標 stable public;coverage 4 處改公開名。
- 驗證:`grep -rn "_get_v2_artifact" momentum/Analysis api --include="*.py"` 輸出 0 行;`pytest tests/momentum -k coverage -q` 0 failed;新測試(公開==私有,含 missing-key 案例 `==` 斷言)0 failed。
- 邊界:(1) manifest 缺 kind key → 公開版與 private 回傳 `==`(委派保證+測試釘);(2) 第三 caller → `grep -rn "_get_v2_artifact" --include="*.py" api momentum | grep -v feature_reader.py` 輸出 0 行。
- 不可做:不改 `_get_v2_artifact` 內部邏輯;不刪 private;L14 concrete import **保留**(白名單票);不重構 coverage 其他部分。

## §V 驗證策略與邊界測試目錄
- **mutation(RISK d,Task 1;r2 依 ADV-CODEX-6 擴充)**:M1=library 分支換回 `FeatureLibrary()` → T1b/T1c 必 FAIL;M2=刪 features_path fallback 分支 → T1d(或 T1a)必 FAIL;M3=**漏傳 config_hash**(library 分支硬寫 None) → T1b 必 FAIL;M4=**library 移到 path 之前** → T1a 必 FAIL。四 mutant 實跑輸出貼 receipt 後還原,還原後全綠。引 `docs/TEST_DESIGN_CHARTER.md`。
- 測試層級:單元(T1a-e/Task 3 負向+組裝冒煙/Task 4 等值)、整合(batch 三測試檔)、Golden(G1/G2 receipt)、邊界(各 Task 列 2)。全部 `pytest tests/...` 獨立跑。
- **防假綠**:不得放寬/刪除既有斷言;review 方 diff 測試檔;G1 禁 aggregate sum hash(有序序列化 sha256)。
- 邊界目錄:空DF(T1 fallback)/API重啟(Task 3 fail-fast)適用;全NaN/Inf/std=0/並發/OOM 不適用(零數值計算變更)。

## §R 回退
- 4 Task 獨立 commit 可單獨 revert;無 schema/數據變更。Task 1 若 G1/G2 FAIL → 不 merge、上報。不加 feature flag(fail-fast 設計+「驗過就別預設關閉」鐵律)。

## §N N/A 登記
- (feature/kline 三方簽核計畫之豁免理由已寫在 §G 本體:不生成/計算/merge/split 特徵,僅讀取來源選擇;§G 本體已填 G1/G2,不豁免。)
- §V 邊界目錄之全NaN/Inf/std=0/重複timestamp/並發寫/OOM/浮點reduction:N/A — 零數值計算變更。
