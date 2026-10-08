# FRAMEPATH 處置表逐檔分析 brief（主委 → 分析子代理）

你是唯讀分析員。repo＝/Users/louis/Desktop/quantitative_trading_system（cwd 已在此）。
**禁止修改 repo 任何檔案**；只准讀檔、`git show 6e07e0ad:<path>`、grep，以及 `venv/bin/python -m pytest --collect-only -q -o addopts=--import-mode=importlib -p no:cacheprovider <檔>`（只收集，不執行）。
**禁止執行任何測試**（本機 8GB，真實資料測試只准主委單組串行跑）。
產出寫到你被指定之 scratchpad JSON 檔（只寫該檔）。

## 背景
票 FRAMEPATH（規格全文 docs/FRAMEPATH_SPEC.md，必讀 §C、Phase 1–3 全部 Task）刪除特徵工廠之非 CGSA 舊引擎（frame，`FFACT_USE_CGSA=0`）與舊特徵 h5（`*_factory.h5`）讀寫鏈。
本步驟要凍結「測試／腳本處置表」：受影響檔中，每個會因刪除而壞、或本身就是 frame 對照臂之測試／片段，要列一筆操作。
基準 commit＝6e07e0ad（現行工作樹之 .py 與它相同，可直接讀現行檔；行號以 `git show 6e07e0ad:<path>` 為準）。

## 生產碼改動模型（實作後之行為；判斷測試會不會壞的唯一依據）
Phase 1（Task 1.2–1.5）：
1. `FFACT_USE_CGSA` 生產碼零讀取：`FeatureFactory._cgsa_enabled`、`MultiTFGenerator._cgsa_enabled` 刪除；一律走 CGSA。設 `FFACT_USE_CGSA=0` 不再有作用（不報錯、照走 CGSA）。monkeypatch `_cgsa_enabled` 之測試會 AttributeError。
2. 新具名例外 `CGSARegistryRequiredError`（定義於 momentum/FeatureEngineering/feature_factory.py）：`self._cgsa_registry is None` 時，L3 分派（`_layer3_*` 串流條件改 `persist_mode in {"streaming","hybrid"}`，其後非串流分支保留給 `in_memory`）、`_layer6_5_preprocessing`（:3413–3420 之記憶體 transform 分支刪除）、`_layer7_validate_and_persist`（非 CGSA 體 :4484–4617 刪除）一律拋此例外。即：未經 `generate_features` 準備 registry、直接呼叫這些方法之測試會壞（in_memory 級距之 L3 非串流分支除外）。
3. `FeatureFactory._combine_layers` 改 context 白名單：只收 `layer3_input`、`layer4_input`；其他 context（含 `layer6_5_input`、`layer7_final`、`multi_tf_merged`、`multi_tf_layers`、`multi_tf_legacy_merged`、預設值 `"unknown"`、任意字串）一律拋 `CGSARegistryRequiredError`。
4. L4：`apply_to != "layer1_and_raw"` 一律強制改 `layer1_and_raw`（原本只在 CGSA 時強制）。
5. 單週期 `generate_features` 尾段 :569–597 frame 分支刪除；`_prepare_cgsa_registry` 之環境早退刪除（恆建 registry）；`run_ic_first` :2895 之環境守衛刪除。
6. 多週期：`MultiTFGenerator._generate_multi_tf_legacy` 與其專用 helper、`MultiTFGenerator._combine_layers`（零呼叫者）刪除；`generate_multi_tf` 唯一走 `_generate_multi_tf_cgsa`（registry 為 None ⇒ 拋具名例外）；`MultiTFGenerator._apply_timeframe_tag` 之 registry 為 None 側刪除（None ⇒ 拋具名例外；非 None ⇒ 原樣回傳）。
7. `FeatureFactory._legacy_native_row_maps` 刪；`FeaturePreprocessor.set_no_start_calibration()` 改無參數、`_no_start_native_maps` 消費邏輯刪除。
8. `memory_budget.py:178` 之 `NON_ARM_FFACT_KEYS` 刪 `"FFACT_USE_CGSA"` 列（掃描對齊測試會受影響）。
9. Task 1.4：三檔（feature_factory／multi_tf_generator／feature_preprocessor）內刪後零引用之 def 一併刪（只被已刪測試引用者視為零引用）；被保留之 CGSA 測試引用者保留。
10. `scripts/fix_spec_v1_to_v1_1.py` 整檔刪除（Phase 1）。
Phase 2（Task 2.1–2.4）：
11. `FeatureStorage.save_factory_output`、`save_metadata_json`、`load_factory_output` 刪除；`FeatureFactory._try_load_cache`、`_last_generation_from_cache` 與 generate_features 之快取查詢刪除（`force_regenerate` 參數保留）。
12. `FeatureLibrary`（feature_library.py:205–215）無 hash 之 h5 後備刪除：V2 manifest 找不到 ⇒ `FeatureNotFoundError`；`coverage_analyzer` 只走 V2／FeatureReader（`_resolve_feature_file_path` 之 h5、h5py 讀取、legacy 掃描分支刪）。
13. API：`api/services/feature_factory_service.py` 非 `.json` 之 task 路徑 ⇒ `ValueError`（「舊 factory h5 已不支援」＋路徑），route 轉 HTTP 400；`_load_hdf5_features_df` 等 h5 後備刪；`FeatureBrowserService` 之 `.h5`／`.hdf5` 分支與 `_load_hdf5_features`、`_find_dataset_group` 刪；`register_hdf5_for_browse` 端點保留但非 `.json` ⇒ 400；`kline_cache.h5` 相關不動；case 特徵 h5（`load_features_from_hdf5`／`save_features_to_hdf5`）不動；IC h5 不動。
14. 前端只改註解／文案（`frontend/src/lib/types.ts` 之 `hdf5_relative_path` 註解）。
Phase 3（Task 3.1–3.2）：scripts 逐檔處置（見 SPEC Task 3.1 列表）；`tests/_golden/batch2d/control.json` 刪、`tests/fixtures/golden/multi_symbol_c3/` 三檔刪；`batch2d/cgsa_baseline.json`、`failopen/baseline.json` 不得改。

## 判斷規則（「是否 frame-only」是語意判斷，逐項給理由）
- 只是設 `FFACT_USE_CGSA`（任何值）之 env 行／dict 鍵／關鍵字引數，且剝掉後測試在 CGSA 下仍成立、斷言意義不變 ⇒ **不列操作**（nodeid keep；實作者只剝該鍵，驗證器之正規化視為相等）。⚠ 若剝掉 `=0` 後測試在 CGSA 下會失敗或斷言變得無意義（例：斷言 `*_factory.h5` 存在、斷言 frame 與 CGSA 不同）⇒ 須列操作。
- frame 對照臂（參數化之 frame／legacy 值、frame 與 CGSA 比對斷言、`*_factory.h5` 產物斷言）⇒ `delete-node`（parametrize 元素／函式內敘述／整函式）。
- 整支測試只驗 frame 行為 ⇒ `delete-node`（category def）整函式刪；其 nodeid（含全部參數化 id）標 delete。
- 混合測試：刪掉 frame 敘述後剩餘仍有效 ⇒ 逐敘述 `delete-node`（category stmt）；剩餘需改寫才成立 ⇒ `rewrite`（整函式改寫，**附改寫後函式全文**＋「須保留之原斷言」HEAD 行號清單——這些敘述須逐字留在新全文中；理由寫明）。不得放寬 CGSA 斷言換綠。
- 被刪之 frame 測試若承載某 CGSA 也該有之驗證意圖（NaN／inf gate、partial、跨 symbol 隔離、時間序…），查是否已有 CGSA 測試覆蓋；未覆蓋 ⇒ 用 `rewrite` 把該測試改為 CGSA 版承接（不能「新增」函式到既有檔；只能 rewrite／rename 既有函式），並在 `coverage_note` 寫明。
- helper／fixture／import 只服務已刪 frame 測試且刪後會成為死碼 ⇒ 可列 `delete-node`（非必要；只在其殘留會壞或誤導時列）。
- 非 factory 用途之 h5（kline_cache.h5、case 特徵、IC fixture、通用 mock 之 `.h5` 字串）⇒ 保留不列。
- 母體外檔（直接呼叫改動函式者）同樣判斷。
- phase：該操作必須在哪個 Phase 之批完成（測試在 Phase 1 改動後就會壞 ⇒ 1；只因 Phase 2 刪 h5 鏈才壞 ⇒ 2；scripts／golden ⇒ 3，除 `scripts/fix_spec_v1_to_v1_1.py`=1）。

## 操作種類與定位器（AST 定位一律對 HEAD 6e07e0ad 版；行號用 HEAD 版）
- `delete-node`（.py）：`locator` 之 category：
  - `{"category":"def","qualname":"test_x"}` 或 `"TestCls.test_m"`（模組／類別層之 def／class）
  - `{"category":"dict_item","target":"_PATH_ENV","path":["legacy"]}`（模組層 `NAME = {...}`；path 可多步，字串＝dict 鍵、整數＝序列索引，最後一步為字串鍵）
  - `{"category":"seq_elem","target":"EXPECTED","path":[0]}`（模組層 list／tuple／set 字面元素；最後一步為整數索引；set 依原始碼順序）
  - `{"category":"import_alias","lineno":12,"name":"load_factory_output"}`（name＝asname 或 name）
  - `{"category":"parametrize_elem","qualname":"test_x","decorator_index":0,"index":1}`（第 k 個 decorator 須為 `*.parametrize(...)`；刪 argvalues 第 i 元素，若有同長 `ids=[...]` 字面一併刪第 i 個）
  - `{"category":"stmt","qualname":"test_x","lineno":120,"end_lineno":124}`（該 def 內任意深度之單一敘述，lineno／end_lineno 須精確；模組層敘述用 qualname `"<module>"`）
- `rename`（.py）：`{"locator":{"category":"def","qualname":"test_old"},"new_name":"test_new"}`（函式其餘不變）
- `rewrite`（.py）：`{"locator":{"category":"def","qualname":"test_x"},"rewrite":{"reason":"…","preserved_assertion_lines":[HEAD行號…],"new_source":"def test_x(...):\n    ..."}}`（new_source＝完整函式含 decorator，縮排從 0 起；保留斷言＝HEAD 中起於該行之單一敘述，須逐字出現於 new_source）
- `delete-json-path`（.json）：`{"pointer":"/0"}`（RFC 6901）
- `replace-file`（非 .py、非 .json）：`{"new_content":"<新檔全文>"}`
- `delete-file`（任一）：整檔刪（目錄要逐檔列）

## 輸出格式（寫入指定 JSON 檔）
```json
{
  "group": "G?",
  "files": [
    {
      "path": "tests/…",
      "verdict": "no-op" | "ops",
      "reason": "一兩句：為何不列操作／列了哪些",
      "evidence": ["HEAD 行號或 grep 結果之具體碼證…"],
      "ops": [
        {"phase":1, "kind":"delete-node", "locator":{…}, "frame_basis":"為何這是 frame 專屬（引行號）", "deleted_nodeids":["tests/…::test_x[frame]"], "coverage_note":"刪後之驗證意圖由何 CGSA 測試承接（路徑::名）或 n/a"},
        {"phase":1, "kind":"rewrite", "locator":{…}, "rewrite":{…}, "frame_basis":"…", "deleted_nodeids":[], "renamed_nodeids":{"舊":"新"}, "coverage_note":"…"}
      ],
      "uncertain": ["拿不準之處（主委會實跑確認）"]
    }
  ]
}
```
`deleted_nodeids`：此操作使之消失之 HEAD nodeid（以 `--collect-only -q -o addopts=--import-mode=importlib` 之字面為準，參數化 id 逐字）。整檔刪除須列該檔全部 nodeid。
每個指派給你的檔都要有一筆（含 no-op）。拿不準就寫進 `uncertain`，不要猜。
