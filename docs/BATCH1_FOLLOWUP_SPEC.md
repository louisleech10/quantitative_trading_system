# Batch1 Follow-up 小修包（N3/N4/N6/N7 + timeframes metadata）— SPEC V3

> 來源：HANDOFF 第 1 批 + `docs/DSTAR_FRACDIFF_NONCGSA_FINDING.md`（d* 項抽出）+ 雙家族 adversarial reconcile：
> Codex r1（16 findings，V1 判重作）→ V2 → Codex r2（5 BLOCKING/2 MAJOR，`handoffs/...-codex-r2.md`）+ Composer 獨立版（1 BLOCKING/3 MAJOR，`handoffs/...-composer.md`）→ **本 V3 逐條收斂**。
> 日期：2026-06-12　|　manifest：`docs/BATCH1_FOLLOWUP_MANIFEST.md` V3（[B1-1]~[B1-10]）　|　TODO：`docs/BATCH1_FOLLOWUP_TODO.md` V3　|　決策簡述：`docs/BATCH1_FOLLOWUP_DECISION.md`

## §RISK 風險分級 [B1-10]
- **大小**：**大**。命中 **(a)**（N6 改 NaN gate 觀測量、N3 改 winsor 數值參數來源）+ **(b)**（`feature_factory.py`/`feature_storage.py`/`feature_validator.py`/`multi_tf_generator.py` 共用路徑）。
- 流程：Codex 實作 + Composer code review；本 V3 已含雙家族 adversarial 收斂；派工前雙家族對 V3 確認。

## §A 假設與待使用者確認（雙家族獨立覆核 + V3 勘誤）
- **已驗證事實**（2026-06-12 Claude 自驗 + Codex/Composer 各自以 rg/sed/pytest 獨立覆核，行號為證據錨點）：
  - **N4**：`feature_factory.py:2790-2810` 讀 `tests/_golden/failopen/max_nan_ratio.json`（296B，sha256=dadc1da8...0189ee0b 三方一致）；讀失敗 raise。實測門檻值 `BTCUSDT/12h=0.16346...`（Composer 實測，N6 fixture 門檻綁定用）。
  - **N6**：stream validation dict（`feature_storage.py:1127-1135`）**固定缺** `nan_ratio`；`feature_factory.py:3079` 固定走 `1.0-coverage` fallback。scan 對照組 `:2632-2768` warmup-aware。**`_abnormal_nan_count`（:2773-2787）為 2D 入參、回傳 int 總和；all-NaN 欄（has_valid=False）`abnormal=total_nan`（fail-closed）——V2 寫 abnormal=0 是錯誤陳述，Codex r2 B1 勘誤，V3 以此為準**。
  - **N6 掛點勘誤（Composer P2）**：`_write_group` 的 `nan_mask = np.isnan(array)` 在 **`feature_storage.py:917-918`**（V2 寫 938-943 錯誤）。
  - **N7**：multi-TF `multi_tf_generator.py:1464-1473` 產 `L{n}:{tf}`；manifest `feature_storage.py:571-601` 裸 `L{n}`（raw_v2/processed_v2 契約 :521-539）。**單 TF metadata 組裝有兩處**：`feature_factory.py:3070-3071`（stream CGSA）與 **`:3325-3326`（legacy L7 `_layer7_validate_and_persist`；非 CGSA 單 TF 與 multi-TF legacy 都走此，Composer P1）**。**`failure_reasons` 現行已是扁平字串 `L{n}:<reason>`**（`feature_storage.py:582`，Codex r2 B3 勘誤——非結構化 tuple）。V2 的 `:3219` 錨點錯誤（該行是 quality gate 呼叫），刪除。
  - **N3**：`feature_validator.py:179-209` 寫死 252/63；`__init__`（:49-56）無 config 注入；public 驗證入口 `validate_factory_output`，factory 呼叫點 **`feature_factory.py:3340`**；**API standalone caller `api/services/feature_task_service.py:185`**（Codex r2 B2 點名，V3 已盤入）；`WinsorConfig.window=252` 無 min_periods 欄（`feature_config.py:165-171`）；L6.5 公式 `min(window,max(20,window//4))`（`feature_preprocessor.py:156-158`；252→63、100→25）。
  - **T5**：producer 3 處（`multi_tf_generator.py:327/619/1376`）；momentum/api/frontend 無消費者；**`scripts/` 有 2 個消費者**（`scripts/profile_multi_tf_baseline.py:414`、`scripts/profile_v6v7_comparison.py:466`，Composer P4 勘誤——V2「無任何其他消費者」限定範圍錯誤）；tests 4 處舊鍵；manifest 單 TF 已用 `present_timeframes`（:598）。
  - **回歸 bundle**：78 collected / **78 passed**（Codex 199.09s、Composer 217.79s 各自實跑一致）[B1-8]。
- **誠實標注 assumed**：
  - 「production 部署無 tests/」——無部署證據；[B1-1] 增 packaging 證據步驟兜底，不依賴此假設。
  - 「N6 fallback 真實 run 誤標 partial」——code-supported 推論；[B1-3] 雙層測試（含真 kline）為驗證閘，先紅後綠。
- **待使用者確認：無**（技術決策含 V3 新增三項——per-call API、failure_reasons 規則、真 kline gate——已記 DECISION 文檔可否決）。
- **已確認結果**：第 1 批範圍/順序使用者 2026-06-12 拍板；升大為 CLAUDE.md 規則強制。

## §C 約束
- 解耦：`grep -r "from api\." momentum/` → 0；新共用純函式限 `momentum/FeatureEngineering/utils/`（nan_stats.py、winsor_params.py、layer_ids.py）；`feature_storage` 禁 import `feature_factory`。
- 不可違反：**不弱化 NaN/inf gate**——abnormal 語義以現行 `_abnormal_nan_count` 為準（**含 all-NaN→abnormal=total_nan**），以 [B1-7] 凍結之 reference cases 鎖定，禁任何方向改義；不擅改輸出大小；manifest 契約不動。
- 共用路徑/下游：`quality_status` 值域不變（API `completed_degraded` 映射 `feature_factory_service.py:246,626` 不動）；FROZEN_TESTS 斷言不可放寬。
- hot-path 記憶體 [B1-9]：統計掛 `feature_storage.py:917-918` 既有 nan_mask，禁新增全寬臨時陣列。

## §G Golden / Baseline（命中 (a) 必填）[B1-7]
- **凍結時機**：production 改動前，`scripts/freeze_batch1_baseline.py` 於 HEAD 產 `tests/_golden/batch1_followup/baseline.json`，**單獨 commit**。
- **baseline 內容**：
  1. winsor 預設（252）與 w100 行為 hash（合成 fixture：rng(20260612)，1000×3，leading 60 NaN / mid-hole 5 NaN / ±8σ outliers）。
  2. `_default_max_nan_ratio("BTCUSDT","12h")` 現值。
  3. **nan_stats reference cases**（Codex r2 B1）：empty / all-NaN / leading-only / trailing-only / mid-hole / 跨 chunk 邊界 6 案例，HEAD `_abnormal_nan_count` 輸出整數凍結——對拍 oracle 獨立於改後程式，防同源。
  4. **perf 基準**（Codex r2 B5）：2000×20000 stream write（固定 shard/worker 參數）warmup 1 輪丟棄後 median-of-3 wall 秒數 + tracemalloc 峰值 bytes。
- **hash 定義（唯一，三處同文）**：`mask=np.isnan(arr)`；`value_hash=sha256(np.where(mask,0.0,arr).astype(np.float64).tobytes())`；`mask_hash=sha256(mask.tobytes())`。
- **通過條件（可證偽）**：(1) 比對測試只讀，缺檔=FAIL 禁 skip；(2) winsor 缺省路徑 hash exact==baseline，**且最終經 public `FeatureValidator` 路徑**（非 kernel 直呼，Codex r2 M7）；(3) max_nan_ratio exact；(4) nan_stats 6 案例==reference（含 all-NaN==total_nan）；(5) N6 雙向：純 warmup→complete、mid-hole（abnormal/total>0.17>門檻 0.16346）→partial；(6) w100 時 validator 與 L6.5 resolver 同得 min_periods=25；(7) perf：wall≤baseline×1.15、峰值≤baseline×1.10。任一超出=FAIL 不 merge。

## §P Phase 與依賴
> P0 先行；P1-P4 互不依賴、各自獨立 commit。自檢：無 forward dependency；Task 2.1 reference oracle 由 P0 凍結（非同源）。

### Phase 0 — Golden baseline（依賴：無；**第一個 commit**）[B1-7]
**Task 0.1 — freeze script + baseline + 只讀比對測試**
- 檔案：`scripts/freeze_batch1_baseline.py`、`tests/_golden/batch1_followup/baseline.json`、`tests/feature_engineering/test_batch1_followup.py::TestGolden`。
- 改法：§G 四類內容；腳本冪等（重跑相同 exit 0 / 不同 exit 1 印 diff）；測試缺檔 `pytest.fail`。
- 驗證：腳本兩次 exit 0 且檔 byte 同（shasum）；`pytest -k golden -q` HEAD 綠；rm baseline 後紅（FAIL 非 skip）。
- 邊界：全 NaN 欄 winsorize 不拋錯；json 損壞=FAIL。
- 不可做：測試內禁寫 baseline；禁 skip；禁非確定來源。

### Phase 1 — N4 resource（依賴：P0）[B1-1]
**Task 1.1 — production-owned copy + 可注入常數 + packaging 證據**
- 檔案：`momentum/FeatureEngineering/_resources/max_nan_ratio.json`（byte-copy）；`feature_factory.py` module 常數 `_MAX_NAN_RATIO_ARTIFACT_PATH = Path(__file__).parent / "_resources/max_nan_ratio.json"`；`_default_max_nan_ratio` 改讀常數，raise（:2808-2810）不動。
- packaging 證據（Codex r2 M6）：`rg -l "pyproject|setup.py" --max-depth 1` 確認部署型態——無 wheel 打包（source-deploy）→ 證據（命令+輸出）入交接文件；若有打包設定 → 補 package-data 宣告 + `importlib.resources` 讀取測試（兩種結果都是確定步驟，非裁量）。
- 驗證：`-k n4`——(1) `_default_max_nan_ratio("BTCUSDT","12h")==baseline` exact；(2) monkeypatch 常數指向不存在路徑 → `pytest.raises(RuntimeError)`；(3) 兩 json sha256 ==。
- 邊界：json 損壞/缺 ratios 鍵 → RuntimeError（既有，加覆蓋）。
- 不可做：禁改 artifact 內容；禁 fallback 預設值；禁刪 test oracle；禁測試改真檔。

### Phase 2 — N6 quality metric（依賴：P0）[B1-2][B1-3][B1-9]
**Task 2.1 — `utils/nan_stats.py`（語義==現行，含 all-NaN=total_nan）**
- 檔案：新 `utils/nan_stats.py`：`abnormal_nan_count(values: np.ndarray) -> int`（2D，語義逐行對齊 `_abnormal_nan_count` :2773-2787 **含 `np.where(has_valid, total-leading-trailing, total_nan)`**）+ `class ColumnNanAccumulator`（O(1) 標量狀態：total/nan_total/leading_nan/trailing_nan_run/seen_valid；`update(mask_chunk_1col)` 跨 chunk；`abnormal()`：**`seen_valid=False → nan_total`**，否則 `nan_total-leading-trailing`）。`FeatureFactory._abnormal_nan_count` 改委派。
- 驗證：`-k nan_stats`——(1) [B1-7] 6 個 reference cases（P0 凍結，獨立 oracle）整數 exact ==；(2) 200 隨機案例：accumulator 分 3 chunk 餵 == `abnormal_nan_count` 一次算；(3) all-NaN 欄 == total_nan（顯式單測）。
- 邊界：空陣列→0；單 NaN 值→1（all-NaN 語義）；跨 chunk 邊界（valid 在 chunk1 末/NaN 跨 chunk2 首）。
- 不可做：禁全寬陣列；禁任何方向改義（reference oracle 鎖）；utils 禁 import factory/storage。

**Task 2.2 — stream producer 產 nan_ratio + 消費端唯一語義**
- 檔案：`feature_storage.py::_write_group`（掛點 **:917-918** 既有 nan_mask）per-column accumulator 跨 shard；group 收尾 `sum(abnormal)/sum(total)`（分母 0→0.0）進 validation dict（:1127-1135）；`feature_factory.py:3079` 缺鍵 → `logger.warning(...)` + 沿用 `1.0-coverage` 不變。
- 驗證：`-k n6`——(1) 真 ColumnGroupRegistry（tmp）3 欄（純 warmup / **mid-hole abnormal/total>0.17**（手算入註解，>門檻 0.16346，Composer P5）/ 乾淨）→ `write_raw_from_registry_stream` → summary nan_ratio == `abnormal_nan_count` 手算 → `_apply_runtime_quality_gate` 雙向（complete/partial）；(2) 測試先紅後綠（紅證據入交接文件）；(3) 缺鍵 dict → caplog warning + 行為同舊。
- 邊界：空 group→0.0；全 NaN 欄→abnormal=total_nan 計入分子。
- 不可做：禁改門檻；禁動 scan 路徑（:3224、:2632）；禁繞過 Task 2.1 函式；禁全寬陣列；storage 禁 import factory。

**Task 2.3 — perf gate（基準比對，無 production flag）**（Codex r2 B5、Composer P6）
- 改法：P0 已凍結 perf 基準（同機）；本測試以**相同參數**重跑 benchmark（warmup 1 丟棄、median-of-3、固定 shard/workers），比對 [§G #7] 門檻；`@pytest.mark.slow`。另：單元級結構斷言——`ColumnNanAccumulator.update` 於 20M-element mask 下 tracemalloc 增量 < 1KB（O(1) 狀態證明）。
- 驗證：`-k perf_smoke -q`（slow）綠：`wall_post <= baseline_wall*1.15`、`peak_post <= baseline_peak*1.10`、accumulator 增量 <1024 bytes。
- 邊界：小 shard（8GB tier 模擬）同參數一輪 < 門檻。
- 不可做：禁新增 production 開關 flag；禁抽樣跳欄；禁調鬆門檻。

**Task 2.4 — 真實 kline gate**（Codex r2 B4；驗證保真度鐵律不得降級）[B1-3]
- 改法：`data_cache/feature_klines/kline_cache.h5` BTCUSDT/12h（2024-06-01~2024-12-01 切片，與 FINDING 實測同範圍）經真實 CGSA `generate_features`（persist→tmp 目錄）→ 讀回 stream summary：含 `nan_ratio` 鍵、值 == 對已寫盤 arrays 以 `abnormal_nan_count` 重算、`quality_status` 與重算結果一致判定；`@pytest.mark.slow`；kline 檔不存在 → `pytest.fail`（不得 skip——此 gate 是鐵律要求）。
- 驗證：`-k real_kline -q`（slow）綠；斷言含上述三項 `==`。
- 邊界：真實資料無 mid-hole 時仍斷言 nan_ratio 鍵存在與重算一致（complete 向）；abort/部分失敗 → 測試 FAIL 非 skip。
- 不可做：禁合成資料替代；禁寫 data_cache/feature_klines；禁因慢改 skip。

### Phase 3 — N3 winsor config（依賴：P0）[B1-5]
**Task 3.1 — per-call 參數定案 + 共用 resolver**
- **API 定案（Codex r2 B2；拒 setter——無共享 mutable state）**：`validate_factory_output(result, *, winsor_window: Optional[int]=None)`、`winsorize(df, *, window: Optional[int]=None)`；`window is None → 252`（顯式判 None，**禁 `or 252`**）；`window<=0 → ValueError`；min_periods=`resolve_winsor_min_periods(window)`（新 `utils/winsor_params.py`，公式自 `feature_preprocessor.py:156-158` 抽出，preprocessor 改 import 行為不變）。
- 接線：factory 呼叫點 `feature_factory.py:3340` 傳 `config.preprocessing.winsorization.window`；**API caller `feature_task_service.py:185` 不傳參**（維持 252 既有行為，聲明入交接文件）；caller 盤點 `rg "validate_factory_output|FeatureValidator\(" momentum/ api/ tests/` 全清單入交接文件。
- 驗證：`-k n3`——(1) 缺省經 public validator → hash==baseline exact；(2) `resolve_winsor_min_periods(100)==25` 且 public validator w100 hash==baseline w100；(3) 首 `min_periods-1` 列不裁剪；(4) `_l65_winsorization_applied` True→count==0 / False→==1；(5) `window=0` → `pytest.raises(ValueError)`（**非靜默 252**）；(6) preprocessor 改 import 後回歸 bundle ≥78。
- 邊界：rows<min_periods 全不裁剪；window=1→min_periods=1。
- 不可做：禁 kernel 改動；禁 PIT 語義變更；禁新增 config 欄；禁 constructor kwarg/setter（per-call 唯一路徑）。

### Phase 4 — metadata 契約（依賴：P0）[B1-4][B1-6]
**Task 4.1 — N7 冪等 canonicalizer，三組裝點確定 scope**
- 檔案：新 `utils/layer_ids.py`：`qualify_failed_layer_id(entry: str, tf: str) -> str`（規則：match `^L\d+:\d+[hdm]($|:)`→不變；match `^L\d+$`→`+":{tf}"`；match `^(L\d+):(.*)$`（reason 形）→ 首冒號後插 tf 成 `L{n}:{tf}:{reason}`；其他（如 `timeframe:{tf}`）→不變）+ list 版。**冪等**（重複套用不變）。
- 套用點（確定，非條件）：`feature_factory.py:3070-3071`（stream CGSA）、**`:3325-3326`（legacy L7）**、`multi_tf_generator.py:546`（worker 聚合；冪等故已限定條目安全）。manifest 衍生（`feature_storage.py:560-601`）**不動**。
- 防同源：stream 與 **legacy** 兩路徑各自硬編預期（如 `["L3:12h"]`、`failure_reasons ["L3:12h:boom"]`）；舊裸格式 manifest fixture → 出限定格式；reason 含冒號案例（`L3:network:timeout`→`L3:12h:network:timeout`）顯式測試。
- 驗證：`-k n7`——(1) stream/legacy/multi-TF 三路徑 metadata 全 match `^L\d+:\d+[hdm](:|$)` 且==硬編 list（保序）；(2) 冪等性（套兩次==套一次）；(3) `timeframe:{tf}` 條目不變；(4) 既有測試僅格式字串更新逐條登記。
- 邊界：layer+TF 失敗並存；無失敗 `[]`；reason 以 `\d+[hdm]:` 開頭的病態案例（如 reason="4h:x"）→ 依規則視為已限定不重插，登記為已知限制（發生率≈0，交接文件記錄）。
- 不可做：禁動 manifest 格式/schema version；禁改 quality_status 判定；禁動 expected/present_layers；scan-CGSA 路徑（:3142-3226 無 completeness）out-of-scope 登記（Composer P8）。

**Task 4.2 — T5 `present_timeframes` + scripts scope**
- 檔案：`multi_tf_generator.py` 新 `_present_timeframes()` + 3 處替換；**`scripts/profile_multi_tf_baseline.py:414`、`scripts/profile_v6v7_comparison.py:466` 同步改鍵名**（Composer P4）；4 個既有測試更新逐條登記。
- 驗證：`-k t5`——三路徑 metadata == 硬編預期保序 list；shell gate：`! grep -rn "actual_timeframes" momentum/ api/ frontend/src scripts/`（範圍含 scripts/）。
- 邊界：skipped=全部→`[]`；保序。
- 不可做：禁動 manifest `present_timeframes`；禁 alias；禁改 skipped_timeframes。

## §V 驗證策略與邊界測試目錄
- 層級：單元（nan_stats reference+對拍、resolver、canonicalizer 冪等）/ Golden（P0 只讀 exact）/ 整合（真 registry→stream→gate；**真 kline gate（Task 2.4，slow，禁 skip）**；N7 stream+legacy 雙路徑；T5 三路徑）/ 效能（基準比對+O(1) 結構斷言）。
- 防假綠：diff 既有斷言；FROZEN_TESTS 不動；允許更新僅 N7/T5 格式/鍵名字串逐條登記；oracle 全部 P0 凍結非同源。
- 回歸 bundle [B1-8]：7 檔 exit 0 且 pass ≥ 78。
- 邊界目錄：空DF ✓(0.1,2.2) / 全NaN ✓(2.1 all-NaN=total_nan) / 跨 chunk ✓(2.1) / 寬 group OOM ✓(2.3) / 真實資料 ✓(2.4) / 並發 ⋅不適用 / resume ⋅不適用（manifest 不動）。

## §R 回退
- P0-P4 各自獨立 commit（message 帶 `[P_n]`）；utils 新檔互不 import 可隨所屬 Phase revert；Golden/真 kline gate FAIL → 不 merge；發現未列消費者 → 停手回報。

## §N N/A 登記
- 全棧跨層：N/A——API 契約值域不變、前端無引用（§A grep 驗證，scripts/ 已列入 scope）。
- resume/checkpoint：N/A——manifest 契約不動。
- scan-CGSA completeness 組裝：N/A（out-of-scope）——`:3142-3226` 現無 failed_layers 組裝、當前主路徑為 stream（Composer P8 登記）。
- 其餘必填段皆填。
