# Batch1 Follow-up TODO V3（DRAFT｜基於 SPEC V3｜2026-06-12）

> 追溯：manifest [B1-1]~[B1-10]；SPEC Task 0.1/1.1/2.1/2.2/2.3/2.4/3.1/4.1/4.2 共 **9 Task**；§G 通過條件 7。
> V2→V3：Codex r2 BLOCKING 1-5 + MAJOR 6-7、Composer P1-P8 全收斂（all-NaN=total_nan、per-call API、failure_reasons 扁平字串規則、:917-918/:3325-3326 錨點勘誤、真 kline gate、perf 基準比對、scripts/ scope）。

## §0 全域規則與約束
- 解耦：momentum/ 禁 `from api.`（驗收 `grep -r "from api\." momentum/` → 0）；新純函式限 `momentum/FeatureEngineering/utils/`（nan_stats.py、winsor_params.py、layer_ids.py）；feature_storage 禁 import feature_factory。
- 不可違反：不弱化 NaN/inf gate——abnormal 語義==現行 `_abnormal_nan_count`（feature_factory.py:2773-2787），**all-NaN 欄 abnormal=total_nan**，以 P0 凍結 reference cases 鎖定，禁任何方向改義；不擅改輸出大小；manifest raw_v2/processed_v2 契約不動。
- hot-path：stream 統計掛 `feature_storage.py:917-918` 既有 `nan_mask = np.isnan(array)`，禁全寬新陣列。
- Logging：momentum/ 用 `logging.getLogger(__name__)`；熱迴圈禁 log。
- 防假綠：禁放寬/刪既有斷言；FROZEN_TESTS 不動；允許更新僅 N7/T5 格式/鍵名字串（4 處舊鍵測試），逐條登記 `handoffs/20260612-batch1-followup.md`；回歸 bundle pass ≥ 78。
- 紀律：禁動 `data_cache/feature_klines/`（讀可、寫禁）、根 HANDOFF.md、templates/、docs/*SPEC|TODO|PLAN*.md。BLOCKED 即停（`STATUS: BLOCKED — <問題>`）。

## §B 批次執行策略（[B1-10]）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| P0 | 0.1 | 無（**第一個 commit**） | oracle 先行防自我認證 | 小 |
| P1 | 1.1 | P0 | resource 獨立回退 | 小 |
| P2 | 2.1→2.2→2.3→2.4 | P0 | quality metric 同域 | 中 |
| P3 | 3.1 | P0 | winsor config 獨立回退 | 中 |
| P4 | 4.1、4.2 | P0 | metadata 契約同域 | 中 |

- 每批收尾：該批 `-k` 綠 + 累計 `pytest tests/feature_engineering/test_batch1_followup.py -q` 綠（slow 標記項至少完整跑一次，紀錄輸出）。
- 總 Gate：回歸 bundle（7 檔，§0 防假綠節同 V2 清單）exit 0 且 **pass ≥ 78**（[B1-8]）+ `grep -r "from api\." momentum/` → 0 + `! grep -rn "actual_timeframes" momentum/ api/ frontend/src scripts/`。

## Phase 0 — Golden baseline（[B1-7]）

### Task 0.1 — freeze script + baseline + 只讀比對測試
- SPEC ref：Task 0.1/§G。
- 輸出：`scripts/freeze_batch1_baseline.py` + `tests/_golden/batch1_followup/baseline.json` + `TestGolden`。baseline 鍵：
  `winsor_default_value_hash/mask_hash`、`winsor_w100_value_hash/mask_hash`、`winsor_w100_min_periods`、`max_nan_ratio_btc_12h`、`nan_stats_reference`（6 案例 dict）、`perf_wall_seconds`、`perf_peak_bytes`。
- 實作要點：
  1. winsor fixture：`np.random.default_rng(20260612)` 1000×3（col0 前 60 NaN、col1 中段 5 NaN、col2 ±8σ outliers）；hash 唯一定義 `mask=np.isnan(arr)`、`value_hash=sha256(np.where(mask,0.0,arr).astype(np.float64).tobytes())`、`mask_hash=sha256(mask.tobytes())`。
  2. **nan_stats_reference（Codex r2 B1）**：6 案例（empty、all-NaN(50 列)、leading-only(前 30 NaN)、trailing-only(後 30 NaN)、mid-hole(中段 7 NaN)、cross-chunk(有效值止於第 333 列、NaN 跨 333/334 chunk 邊界)）以 **HEAD `FeatureFactory._abnormal_nan_count`** 算出整數凍結（獨立 oracle）。
  3. **perf 基準（Codex r2 B5）**：2000 cols×20000 rows 真 stream write（tmp registry、固定 shard rows=4096、單 worker），warmup 1 輪丟棄、median-of-3 wall + tracemalloc 峰值。
  4. w100 案例：HEAD validator 不可配置 → 腳本直呼 `rolling_winsorize_array(window=100, min_periods=25)` 凍結期望（最終測試走 public 路徑比對，Codex r2 M7）。
  5. 冪等：重跑相同 exit 0；不同 exit 1 印 diff。測試只讀，缺檔/損壞 `pytest.fail`。
- 修改檔案：3 新檔。既有 caller：無。
- 不可做：測試內禁寫 baseline；禁 skip；禁非確定來源（perf 除外，其為同機統計量）。
- 邊界：全 NaN 欄 winsorize 不拋錯；腳本兩次 byte 相同（perf 鍵豁免、容差寫死於腳本比對邏輯=不比 perf 鍵）。
- 風險緩解：[B1-7]。
- 驗證：`python scripts/freeze_batch1_baseline.py` 兩次 exit 0；`pytest -k golden -q` HEAD 綠；`rm baseline` 後紅（FAIL 非 skip）。

## Phase 1 — N4 resource（[B1-1]）

### Task 1.1 — production-owned copy + 可注入常數 + packaging 證據
- SPEC ref：Task 1.1。
- 實作要點：
  1. `cp tests/_golden/failopen/max_nan_ratio.json momentum/FeatureEngineering/_resources/`（byte-copy 禁重序列化）。
  2. `feature_factory.py` module 頂部 `_MAX_NAN_RATIO_ARTIFACT_PATH = Path(__file__).parent / "_resources/max_nan_ratio.json"`；`_default_max_nan_ratio`（:2790-2810）改讀常數；raise 不動。
  3. packaging 證據（Codex r2 M6）：repo 根 `ls pyproject.toml setup.py 2>/dev/null` ——無 → source-deploy 證據（命令+輸出）入交接文件；有 → 補 package-data + `importlib.resources` 測試。兩種結果都是確定步驟。
  4. sha256 防漂移斷言（tests oracle vs _resources）。
- 修改檔案：`feature_factory.py::_default_max_nan_ratio`+常數；新 `_resources/max_nan_ratio.json`。caller：`_apply_runtime_quality_gate`（:2824）唯一、簽名不變。
- 不可做：禁改 artifact 內容；禁 fallback；禁刪 test oracle；禁測試改真檔（monkeypatch 常數）。
- 邊界：json 損壞→RuntimeError；缺 ratios 鍵→RuntimeError。
- 風險緩解：[B1-1]。
- 驗證：`pytest -k n4 -q` 綠——(1) `_default_max_nan_ratio("BTCUSDT","12h")==baseline["max_nan_ratio_btc_12h"]`；(2) monkeypatch `_MAX_NAN_RATIO_ARTIFACT_PATH`→不存在 → `pytest.raises(RuntimeError)`；(3) 兩 json sha256 ==。

## Phase 2 — N6 quality metric（[B1-2][B1-3][B1-9]）

### Task 2.1 — `utils/nan_stats.py`（all-NaN=total_nan）
- SPEC ref：Task 2.1。
- 輸出：
  ```python
  def abnormal_nan_count(values: np.ndarray) -> int:
      # 2D 入參；語義逐行對齊 feature_factory.py:2773-2787：
      # abnormal = np.where(has_valid, total_nan - leading - trailing, total_nan)  ← all-NaN 計全部
  class ColumnNanAccumulator:
      total: int; nan_total: int; leading_nan: int; trailing_nan_run: int; seen_valid: bool
      def update(self, nan_mask_chunk: np.ndarray) -> None: ...   # 單欄 1D mask 切片，跨 chunk
      def abnormal(self) -> int:
          # seen_valid=False → nan_total（fail-closed）；否則 nan_total - leading_nan - trailing_nan_run
  ```
- 實作要點：1) update 標量狀態機（未見 valid 前 NaN 計 leading；見 valid 後 NaN 累 trailing_run、再見 valid 歸中段）；2) `FeatureFactory._abnormal_nan_count` 改 `return abnormal_nan_count(values)` 委派；3) oracle=P0 凍結 reference（非同源）。
- 修改檔案：新 utils/nan_stats.py；feature_factory.py:2773 委派。caller：`_scan_cgsa_registry_validation`（:2692）經委派不變。
- 不可做：禁全寬陣列；禁改義（含 all-NaN 方向）；utils 禁 import factory/storage。
- 邊界：空陣列→0；單 NaN 值→1（all-NaN 語義）；cross-chunk（reference 案例 6）。
- 風險緩解：[B1-2]（Codex r2 B1）。
- 驗證：`pytest -k nan_stats -q` 綠——(1) 6 reference cases 整數 exact==baseline；(2) 200 隨機案例 accumulator(3 chunk)==abnormal_nan_count(一次)；(3) all-NaN==total_nan 顯式斷言。

### Task 2.2 — stream producer 產 nan_ratio
- SPEC ref：Task 2.2。
- 實作要點：1) `_write_group` 掛點 **feature_storage.py:917-918** 既有 nan_mask，per-column `ColumnNanAccumulator`（dict by column，跨 shard）；2) group 收尾 `sum(abnormal)/sum(total)`（分母 0→0.0）→ validation dict（:1127-1135）加 `"nan_ratio"`；3) `feature_factory.py:3079` 缺鍵 → `logger.warning("[L7] stream validation missing nan_ratio; using warmup-inclusive 1-coverage fallback")` + 算式不變；4) 整合測試先寫先紅（紅輸出入交接文件）。
- 修改檔案：feature_storage.py::_write_group + validation dict；feature_factory.py::_layer7_raw_from_cgsa_pipeline（:3079 一帶）。scan 路徑（:3224、:2632）禁動。
- 不可做：禁改門檻；禁動 scan；禁自寫判定（必用 Task 2.1）；禁全寬陣列；storage 禁 import factory。
- 邊界：空 group→0.0；全 NaN 欄 abnormal=total_nan 計入分子；缺鍵防禦 caplog。
- 風險緩解：[B1-2][B1-3]（Codex r2 B2 收斂語義）。
- 驗證：`pytest -k n6 -q` 綠——(1) 真 ColumnGroupRegistry（tmp）3 欄：純 warmup(前 80/400 NaN) / **mid-hole(中段 72/400 NaN → abnormal/total=0.18>0.17>門檻 0.16346，手算入註解，Composer P5)** / 乾淨 → `write_raw_from_registry_stream` → summary `nan_ratio`==手算 → `_apply_runtime_quality_gate`：warmup 情境 `=="complete"`、mid-hole `=="partial"`；(2) 實作前紅；(3) 缺鍵 dict→warning+行為同舊。

### Task 2.3 — perf gate（基準比對）
- SPEC ref：Task 2.3。
- 實作要點：1) 與 P0 perf 基準**完全同參數**重跑（2000×20000、shard 4096、單 worker、warmup 1 丟棄、median-of-3）；2) 斷言 `wall<=baseline*1.15`、`peak<=baseline*1.10`；3) 結構斷言：`ColumnNanAccumulator.update` 吃 20M-element mask 後 tracemalloc 增量 `<1024` bytes；4) `@pytest.mark.slow`。
- 修改檔案：僅測試檔（benchmark helper 可與 freeze script 共用 import 自 scripts/）。
- 不可做：禁 production flag；禁抽樣；禁調鬆門檻（1.15/1.10 寫死）。
- 邊界：小 shard（512）一輪 < 同門檻；單欄 group 不除零。
- 風險緩解：[B1-9]（Codex r2 B5、Composer P6）。
- 驗證：`pytest -k perf_smoke -q`（slow）綠，斷言式如上三條（`<=`）。

### Task 2.4 — 真實 kline gate（鐵律，禁 skip）
- SPEC ref：Task 2.4。
- 實作要點：1) `data_cache/feature_klines/kline_cache.h5` BTCUSDT/12h 2024-06-01~2024-12-01 → 真實 CGSA `generate_features(persist=True, tmp 輸出目錄)`；2) 讀回 stream summary：`"nan_ratio" in summary`；3) 對已寫盤 arrays 以 `abnormal_nan_count` 重算 == summary 值；4) `quality_status` 與重算+門檻判定一致；5) `@pytest.mark.slow`；kline 檔不存在 → `pytest.fail`（禁 skip）。
- 修改檔案：僅測試檔。
- 不可做：禁合成替代；禁寫 data_cache/feature_klines；禁 skip。
- 邊界：真實資料無 mid-hole → 仍斷言鍵存在+重算一致（complete 向）；生成 abort → FAIL。
- 風險緩解：[B1-3]（Codex r2 B4；驗證保真度鐵律）。
- 驗證：`pytest -k real_kline -q`（slow）綠，三項 `==` 斷言。

## Phase 3 — N3 winsor config（[B1-5]）

### Task 3.1 — per-call API + 共用 resolver
- SPEC ref：Task 3.1。
- 實作要點：
  1. 新 `utils/winsor_params.py::resolve_winsor_min_periods(window:int)->int`（`min(window,max(20,window//4))`；`window<=0`→ValueError）；`feature_preprocessor.py:156-158` 改 import（行為不變）。
  2. `FeatureValidator.validate_factory_output(result, *, winsor_window: Optional[int]=None)`、`winsorize(df, *, window: Optional[int]=None)`：`if window is None: window=252`（**禁 `or 252`**）；`window<=0`→ValueError（resolver 內已 raise，呼叫前顯式判一次）；min_periods=resolver(window)。**禁 constructor kwarg/setter**（per-call 唯一，Codex r2 B2）。
  3. factory 呼叫點 `feature_factory.py:3340` → `validate_factory_output(result, winsor_window=config.preprocessing.winsorization.window)`（config 取值點實作端確認 :3340 所在函式可及 config，不可及則沿呼叫鏈顯式傳參，禁存 self 狀態）。
  4. API caller `api/services/feature_task_service.py:185` `validator.validate(...)` 不傳參=252 不變（聲明入交接文件）；caller 盤點 `rg "validate_factory_output|FeatureValidator\(" momentum/ api/ tests/` 全清單入交接文件。
- 修改檔案：utils/winsor_params.py（新）；feature_validator.py（:179-209 + validate_factory_output 簽名）；feature_preprocessor.py（:156-158 import）；feature_factory.py（:3340 傳參）。
- 不可做：禁 kernel 改動；禁 PIT 變更；禁新增 config 欄；禁 constructor/setter 注入；禁 `or 252`。
- 邊界：rows<min_periods 全不裁剪（首 62 列數值斷言）；window=1→min_periods=1；window=0→ValueError。
- 風險緩解：[B1-5]（Codex r2 B2/M7、Composer P7）。
- 驗證：`pytest -k n3 -q` 綠——(1) 缺省經 **public validator** hash==baseline；(2) `resolve_winsor_min_periods(100)==25` 且 public w100 hash==baseline w100；(3) 首 min_periods-1 列不變；(4) L6.5 標記 True→`_last_winsorization_count==0`/False→`==1`；(5) `window=0`→`pytest.raises(ValueError)`；(6) 回歸 bundle ≥78。

## Phase 4 — metadata 契約（[B1-4][B1-6]）

### Task 4.1 — N7 冪等 canonicalizer + 三組裝點
- SPEC ref：Task 4.1。
- 實作要點：
  1. 新 `utils/layer_ids.py::qualify_failed_layer_id(entry:str, tf:str)->str` + `qualify_failed_layer_ids(entries, tf)`：規則（保序）——`^L\d+:\d+[hdm]($|:)`→不變；`^L\d+$`→補 `:{tf}`；`^(L\d+):(.*)$`→首冒號後插 tf；`^timeframe:`→不變。**冪等**。
  2. 套用三點（確定 scope）：`feature_factory.py:3070-3071`（stream CGSA：failed_layers+failure_reasons）、**`:3325-3326`（legacy L7，Composer P1）**、`multi_tf_generator.py:546`（worker 聚合，冪等安全）。manifest 衍生（feature_storage.py:560-601）不動。
  3. 硬編預期防同源：stream 與 legacy 各自 `["L3:12h"]`、`["L3:12h:boom"]` 式 list；reason 含冒號案例 `L3:network:timeout`→`L3:12h:network:timeout`。
  4. 舊裸格式 manifest fixture（json）→ 讀組 metadata → 限定格式。
- 修改檔案：utils/layer_ids.py（新）；feature_factory.py 兩處；multi_tf_generator.py:546 一處。caller：`_apply_failed_layer_metadata`（:1478）格式已同不動。
- 不可做：禁動 manifest 格式/schema version；禁改 quality_status；禁動 expected/present_layers；scan-CGSA（:3142-3226）out-of-scope。
- 邊界：layer+TF 失敗並存（`^L\d+:` 與 `^timeframe:` 互斥）；無失敗 `[]`；病態 reason="4h:x" 依規則視為已限定（已知限制，登記交接文件）。
- 風險緩解：[B1-4]（Codex r2 B3、Composer P1/P3）。
- 驗證：`pytest -k n7 -q` 綠——(1) stream/legacy/multi-TF 三路徑全 match `^L\d+:\d+[hdm](:|$)` 且==硬編 list 保序；(2) 冪等（套兩次==一次）；(3) `timeframe:` 條目不變；(4) 舊 fixture 兼容；(5) 既有測試格式更新逐條登記。

### Task 4.2 — T5 `present_timeframes` + scripts scope
- SPEC ref：Task 4.2。
- 實作要點：1) `multi_tf_generator.py` 新 `_present_timeframes(self, skipped)->List[str]`（保序）+ :327/:619/:1376 替換 + 鍵名 `present_timeframes`；2) **scripts 2 檔同步改鍵**（profile_multi_tf_baseline.py:414、profile_v6v7_comparison.py:466，Composer P4）；3) 舊 task record 無讀取端→不遷移不 alias（聲明交接文件+PR）；4) 4 個既有測試更新逐條登記。
- 修改檔案：multi_tf_generator.py + 2 scripts + 4 測試檔。
- 不可做：禁動 manifest `present_timeframes`（feature_storage.py:598）；禁 alias；禁改 skipped_timeframes。
- 邊界：skipped=全部→`[]`；保序 list==非 set。
- 風險緩解：[B1-6]（Composer P4、Codex r1 M13）。
- 驗證：`pytest -k t5 -q` 綠——三路徑 metadata==硬編預期保序；shell gate `! grep -rn "actual_timeframes" momentum/ api/ frontend/src scripts/`（exit 0）。

## Phase 總測試 + Gate
- 單元：nan_stats（reference 6+隨機 200）/ resolver / canonicalizer 冪等 / golden 只讀。整合：真 registry→stream→gate、**真 kline（slow 禁 skip）**、N7 雙路徑、T5 三路徑。效能：基準比對+O(1) 結構斷言。
- 總 Gate（§B）：本批全綠（slow 完整跑一次留輸出）+ 回歸 bundle exit 0 且 pass≥78 + 兩條 grep gate。

## 派工 Prompt（[B1-10]）
> 前置：repo 根、branch main、venv。讀 SPEC V3 + 本 TODO 對應 Phase。
> P0 最先單獨 commit；P1-P4 順序任意各自獨立 commit（`[P_n]` 標籤）。
> N6 整合測試先寫先紅（紅輸出入交接文件）。Task 2.4 真 kline 禁 skip。
> 交接寫 `handoffs/20260612-batch1-followup.md`：每 Task 函式級變更、測試輸出原文、caller 盤點、4 處舊鍵測試更新逐條、packaging 證據、Task 4.1 worker 聚合核驗、已知限制登記。
> 禁：§0 紀律全部；BLOCKED 即停。

## 階段 3 自檢（0 FAIL）
1. 追溯：[B1-1]→1.1；[B1-2]→2.1/2.2；[B1-3]→2.2/2.4；[B1-4]→4.1；[B1-5]→3.1；[B1-6]→4.2；[B1-7]→0.1；[B1-8]→§0/§B；[B1-9]→2.3+2.1 不可做；[B1-10]→§B/派工 Prompt。10/10 ✓
2. 深度：9 Task 均 ≥3 要點+函式級檔案+≥2 邊界+可證偽驗證 ✓
3. 語義：all-NaN 與既有實作對齊（V2 錯誤已修）；oracle P0 凍結非同源；utils 三檔無循環 import；per-call API 無共享狀態 ✓
4. 全棧跨層：純 momentum+scripts（§N 登記）⋅API 值域不變
5. 錨點：§0/§B/9 Task 驗證·邊界·不可做 ✓
