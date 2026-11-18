# TESTSEL I4g 每次 pytest 之固定啟動負擔（套件與 conftest 改用到才載入）— SPEC

> 狀態：草案 v1。
> 來源：大綱 `handoffs/20261116-testsel-route-outline.md` 末節「現行完成計畫」I4g 列（判準 S2：`--collect-only` 牆鐘 ≤ 3 秒）；事實與原型 `runs/testsel_route/i4g/i4g_facts.md`。
> 業界出處（判準 P0）：PEP 562 模組層 `__getattr__`／`__dir__` 延遲匯出（https://peps.python.org/pep-0562/）；pytest fixture 只在被測試請求時執行（https://docs.pytest.org/en/stable/how-to/fixtures.html），故只為 fixture 所用之重依賴可移入 fixture 執行路徑。

## §RISK 風險分級
- **大小**：中（改 `momentum/FeatureEngineering/__init__.py` 匯出方式與 `tests/conftest.py` 匯入時點；不改任何函式、類別、數值與匯入後之物件）。
- **命中高風險原則**：(b) 跨模組共用路徑——套件 `__init__` 為全部 `momentum.FeatureEngineering.*` 匯入必經；conftest 作用於全部 pytest。
- RISK-HIT: b

## §A 假設與待使用者確認
- 已驗證事實：`runs/testsel_route/i4g/i4g_facts.md`（含 2026-11-19 原型）。
- 原型（同命令各 3 次中位，`/usr/bin/time -p venv/bin/python -m pytest -p no:cacheprovider -q --co tests/registry/test_conftest_seed.py`）：改前 4.25 秒（3.89／4.25／4.54）、原型 2.58 秒（3.40／2.18／2.58）；收集本身 0.27 秒。
- 已確認：使用者 2026-11-18 晚「我要睡了，盡可能快速和平行進行，有問題你跟委員共識決定，不要停下來」。
- 待確認：無。

## §C 約束
- 匯入後之物件不變：`momentum.FeatureEngineering.<名>` 與子模組中同名物件為同一物件；`__all__` 內容不變。
- 副作用時點不變：`pd.read_hdf` 相容補丁仍於套件 `__init__` 執行時（即任何 `momentum.FeatureEngineering.*` 匯入時）生效。
- conftest 之隔離重導（`DEFAULT_REGISTRY_PATH`、`FeatureStorage.__init__` 預設根）與 Binance `Client.ping` 離線存根仍於 conftest 載入時生效（須早於任何服務單例與 `api.main` 匯入）。
- 不改任何測試斷言；conftest 延遲匯入之名稱維持模組全域名（TESTREG V19 以函式內綁定名正規化為序號，改為區域名會使斷言字串改變而誤報；事實檔已記）。
- 不改產品碼其他檔、不改 numba 快取、不改 pytest 外掛清單。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I4G-BUDGET-1 | 收案前對最終程式各一次（`scripts/run_watched.py` 背景）：`tests/feature_engineering/test_ff_cross_symbol_value_isolation.py::test_v5_slow_solo_a_equals_batch_b_then_a_artifacts`；`tests/test_feature_factory_e2e.py::test_standard_preset_btcusdt`（全規模層 `@pytest.mark.fullscale`，命令須加 `--run-fullscale`，否則被全規模層延後） | 兩條為請求 `requires_kline_data` 之受影響 nodeid 中 ledger ≥ 60 秒者；I4g 之獨有路徑（fixture 內延遲匯入）已由快速層同 fixture 之 113 條覆蓋；收案仍跑一次係 `docs/TEST_SELECTION.md` §4「收案……§3 選中之全部測試（含重型）對最終程式跑一次」 | 2 nodeid | ledger 加總 2075 秒、保守上界 2591 秒（`runs/testsel_route/i4g/fu_dur.log`）；實跑（最終程式）：前者 `1 passed … in 47.59s`（`runs/testsel_route/i4g/heavy_close.log`），後者 `1 passed in 522.33s`（`runs/testsel_route/i4g/heavy_fullscale.log`），皆 rc=0；兩條本身規模必要性見 §N E-1 | 無 |
| TESTSEL-I4G-BUDGET-2 | 全套 `pytest --co -q -p no:cacheprovider tests` 改前（HEAD 碼）改後各一次（`scripts/run_watched.py` 背景） | 全部測試檔之匯入路徑（套件 `__init__` 延遲匯出後任一模組匯入錯誤即收集錯誤）；收集數改前改後相同 | 全套收集 ×2 | 開跑前量級估計每次 ≤ 300 秒；實跑改前 `14830 tests collected in 6.73s`、改後 `14830 tests collected in 8.09s`，監看牆鐘各 12 秒（`runs/testsel_route/i4g/collect_{before,after}.log`） | 無 |

- 每批快速層：pytest 自身 fixture 解析（`item.fixturenames`）列出請求 `requires_kline_data`／`synthetic_l65_dataset` 之全部 115 條 nodeid（`runs/testsel_route/i4g/list_fixture_users.py`），扣除上列兩條重型之 113 條（`tests/registry/fixtures/i4g_affected_fast.txt`，pytest 原生 `@參數檔`；ledger 加總 44 秒、保守上界 574 秒）＋驗收檔＋三個套件層級名稱使用者＋`tests/registry/test_testsel_hermetic.py`、`tests/registry/test_conftest_seed.py`。改前同組（整檔版、扣兩條重型）於 HEAD 實跑 `206 passed, 3 deselected, 3 xfailed … in 282.97s`、rc=0（`runs/testsel_route/i4g/gate_baseline_head.log`）。

## §B 四項平衡實測
- 耗時：判準 S2——同命令改前改後各 3 次中位；驗收＝改後中位 ≤ 3 秒（原型 2.58 秒）；收據 `runs/testsel_route/i4g/s2_after_*_time.txt`。另量全套 `pytest --co -q` 改前改後各 1 次牆鐘供參。
- 記憶體：收集期少載 statsmodels／scipy.stats／numba 預編路徑；以 `/usr/bin/time -l` 記同命令峰值 RSS 改前改後各 3 次中位。
- 精度、檔案大小：不涉（不改數值與輸出）。

## §P Phase 與依賴

### Phase 1（依賴：I6 已提交 f18630b1）
**Task 1.1 — 套件 `__init__` 改 PEP 562 延遲匯出**
- 改法：`momentum/FeatureEngineering/__init__.py` 保留 `import pandas as pd`、`import h5py` 與 `pd.read_hdf` 相容補丁；七個匯出名（FeatureExtractor、StrategyParams、FeatureValidator、FeatureStorage、FeatureFactory、FeatureGenerationResult、ConfigManager）改由模組層 `__getattr__` 首次取用時自子模組載入並快取於模組全域；加 `__dir__` 回傳模組全域名＋`__all__`；`__all__` 不變。
- **驗證**（新測試檔 `tests/registry/test_i4g_lazy_imports.py`）：
  - `test_i4g_submodule_import_does_not_load_heavy_chain`：子行程 `import momentum.FeatureEngineering.feature_registry` 後 `sys.modules` 不含 `momentum.FeatureEngineering.feature_factory`、`momentum.FeatureEngineering.feature_validator`、`statsmodels`。改壞對照：恢復急切匯入 ⇒ 轉紅。
  - `test_i4g_package_names_identical_to_submodule_objects`：`__all__` 每名 `getattr(套件, 名) is getattr(子模組, 名)`；`from momentum.FeatureEngineering import FeatureExtractor, StrategyParams` 可用。
  - `test_i4g_first_access_via_package_then_cached`：新子行程匯入套件後、取用前 `dir()` 含 `__all__` 且未載重鏈、`vars(pkg)` 無快取；先由套件取得每名 ⇒ 與其後子模組物件同一且已快取於模組全域。
  - `test_i4g_mock_patch_package_name_enter_and_restore`：`unittest.mock.patch("momentum.FeatureEngineering.FeatureFactory")` 進入時替換、退出時恢復同一物件。
  - `test_i4g_read_hdf_patch_applied_on_any_submodule_import`：子行程只匯入一個子模組後 `pandas.read_hdf.__name__ == "_read_hdf_compat"`。
  - `test_i4g_unknown_attribute_raises`：未知名 ⇒ `AttributeError`。
  - 回歸：三個套件層級名稱使用者 `tests/test_phase6_end_to_end.py`、`tests/test_phase3_feature_extractor.py`、`tests/momentum/test_feature_extractor.py`；收案前全套 `pytest --co -q` 改前改後各一次，收集數相同、無匯入錯誤（收據 `runs/testsel_route/i4g/collect_{before,after}.log`；不寫成測試：收集數隨測試增刪而變，固定基準會過期；全套收集實測改前 6.73 秒、改後 8.09 秒（監看牆鐘各 12 秒））。
- **邊界**：子模組直接匯入（`from momentum.FeatureEngineering.feature_factory import FeatureFactory`）照舊急切載入其自身依賴；`mock.patch("momentum.FeatureEngineering.FeatureFactory")` 經 `__getattr__` 解析後寫入模組全域，語意同前。`momentum/FeatureEngineering/feature_factory.py:141`、`:147` 之模組層 `warnings.filterwarnings("once", …)`（pandas nanops 溢位、statsmodels OLS log(0) 之 RuntimeWarning 顯示次數）改為 feature_factory 首次匯入時才安裝：會執行特徵工廠之行程必已匯入之，行為同前；只匯入其他子模組之行程改走 Python 預設（同位置一次），僅影響警告顯示次數、不影響數值。
- **存活至**：永久。
- **覆蓋風險**：依賴「匯入任一子模組即順帶載入 feature_factory 等」之隱性副作用者（`grep` 未見屬性式取用；由全套收集與受影響快速層承接）。
- 不可做：不得移除或延後 `pd.read_hdf` 補丁；不得改子模組內容。

**Task 1.2 — conftest 重依賴改用到才載入**
- 改法：`tests/conftest.py` 移除模組層 `pandas`、`momentum.factories`、`scripts.build_l65_golden`、`tests.fixtures.data_manifest` 匯入（:41–60）；新增模組層函式 `_ic_deps()` 以 `global` 綁定 `create_kline_storage_manager`、`verify_kline_entry`、`ManifestValidationError`、`make_synthetic_l65_dataset`（首次呼叫時匯入），`synthetic_l65_dataset` 與 `requires_kline_data` 於使用前呼叫之；`pd` 僅供型別註解，改 `if TYPE_CHECKING:` 匯入；無使用之 `TEST_INVENTORY_PATH`、`write_test_inventory_from_nodeids`、`_IC_DEPS_AVAILABLE` 刪除（`grep` 僅定義行）。隔離重導（:27–34）與 Binance 存根（:65–70）不動。
- **驗證**（同檔 `tests/registry/test_i4g_lazy_imports.py`；S2 改後中位 ≤ 3 秒）：
  - `test_i4g_conftest_collect_does_not_import_factories`：子行程對一個治理測試檔 `--collect-only` 後（以 `-p` 小外掛於 `pytest_collection_finish` 記錄 `sys.modules`）不含 `momentum.factories`、`statsmodels`。改壞對照：恢復模組層匯入 ⇒ 轉紅。
  - `bash`：`venv/bin/python scripts/testreg.py check --helpers tests/conftest.py` rc=0（無 V19）。
  - 回歸：`tests/registry/test_testsel_hermetic.py`（隔離重導）、請求 `requires_kline_data` 之測試（`grep -rln requires_kline_data tests`）與 `synthetic_l65_dataset` 之測試之快速層全綠。
  - S2 收據：改後 3 次中位 ≤ 3 秒。
- **邊界**：缺 IC 依賴之輕量環境中，治理測試不觸發 `_ic_deps()`；IC fixture 被請求時才拋 `ModuleNotFoundError`（原為載入時容錯為 None 後於使用時拋 TypeError）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得改隔離重導與離線存根之生效時點；不得改任何 fixture 回傳值。

## §V 驗證策略與邊界測試目錄
- 單元：Task 1.1、1.2 所列；回歸：全套 `--collect-only`＋受影響快速層（依 `docs/TEST_SELECTION.md` §5）；時間：S2 三次中位收據。
- 收案機械邊界：manifest `docs/manifests/TESTSELI4G.json` 之 `gate_cmd`。
- 防假綠：延遲載入以子行程 `sys.modules` 斷言（不受本行程已載入之干擾）；改壞對照實跑。

## §R 回退
- 單一 commit；回退＝revert。

## §N N/A 登記
- §G：N/A — 不改數值、特徵或 ML 路徑。
- 收案重型兩條之逐條規模分析（讀碼，本項完成）：
  - `tests/test_feature_factory_e2e.py::test_standard_preset_btcusdt`（:158–170）：獨有覆蓋＝standard preset 全部指標×週期之 inf 品質閘（:157 註解；`test_standard_preset_btcusdt_narrow`〔:173–189〕斷言相同但只含各類別首指標最短兩週期）；覆蓋維度為指標廣度、非資料列數。對 I4g 改動（匯入時點）無快速層以外之獨有失敗路徑——快速層 narrow 版已走同一 `generate_features` 全鏈匯入。
  - `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py::test_v5_slow_solo_a_equals_batch_b_then_a_artifacts`（:475）：獨有覆蓋＝全鏈 L1–L6 之 solo(A) 對 batch B→A 之 A artifact 一致；現行碼實跑 47.59 秒（< 60 秒，依 `docs/TEST_SELECTION.md` §4 實屬快速層；ledger 1546 秒為舊值）。對 I4g 改動同上無獨有失敗路徑。
- E-1：上列兩條本身之縮小（全規模者縮列數後 inf 案例是否仍被觸發；ledger 舊值更新）——為何現在不做: blocked-by: 縮小即改寫既有測試之資料與斷言，須先數值實測縮小後 inf 案例仍出現，並走 TESTREG 改寫收據（V19 斷言多重集合比對），屬大綱 I8 慢測試處置之規格與審查；本項 I4g 依 `docs/TEST_SELECTION.md` §4 已對最終程式實跑兩條皆通過。
- 殘留：Binance `Client.ping` 存根之 `binance.client` 匯入（約 0.35 秒）維持於 conftest 載入時——為何現在不做: blocked-by: 離線鐵則須早於任何 `api.main` 匯入生效（計畫審 r1 約束），延遲會使收集期觸外網；改以 `pytest_configure` 等更早時點不減成本。
