# ICPOSTLEAK 第 1 批審碼 R2 — codex

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R2
brief-kind: review
審查標的：40f863d4、SPEC v4、manifest、r1 收斂檔與本家兩條 r1 findings。唯讀審查；未重開 brief 已排除之 Phase 1／2 主體。產品實跑均在 `/tmp/review-7e8d/work`，先呼叫 `_isolate.isolate()` 與 `isolate_dstar_cache()`，Numba 快取在本次 tmp；真實 kline H5 使用複本。

## CODEX-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；本家 r1 兩條已閉合。已觸發之數值殘留仍是真實資料品質問題，本輪支持以附量測依據之 needs-research 維持殘留，而非未驗成本即更換大型 registry 核心。

**碼證**: 隔離複本執行 `env PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python run_review.py` → rc=0，時間序 8 passed；舊 diff 寫法 mutant 2 failed／3 passed；49 例重產 branchdiff，`cmp handoffs/run_receipts/20261002-icpostleak-branch-diff.json /tmp/review-7e8d/branchdiff.json` → rc=0。`probe_candidate.py` 最終 rc=0，七組 float32 輸入之候選 registry 對 legacy 全陣列 exact equality；現有 HDF5 loader 保留真實資料之 float64。下列必答載明限制、成本與 §N 處置。

**類別**: other

**來源摘要**: momentum/FeatureEngineering/preprocessing/time_order.py#7e2a2b8d3cdd;momentum/FeatureEngineering/preprocessing/feature_preprocessor.py#f8086a000344;docs/ICPOSTLEAK_SPEC.md#ca7efa80b0f9;handoffs/run_receipts/20261002-icpostleak-branch-diff.json#8fcb13eb146f

### 必答 (1a)／(1b)：r1 原反例閉合

(1a) CODEX-R1-P2-01、CODEX-R1-P2-02 均 CLOSED。時間序修補未改數值轉換核心或合法索引之行為；量級交付已補足。

(1b) `run_review.py` 以 pytest.main 選跑以下完整 node 函式，參數化不刪例：

- `tests/feature_engineering/test_icpostleak.py::test_time_order_non_increasing_raises`（五例）
- `tests/feature_engineering/test_icpostleak.py::test_time_order_strictly_increasing_ok`
- `tests/feature_engineering/test_icpostleak.py::test_boundary_06_range_index_not_checked`
- `tests/feature_engineering/test_icpostleak.py::test_boundary_07_length_zero_one_no_raise`

命令選項 `-q -p no:cacheprovider --tb=short` → 8 passed in 0.10s，pytest rc=0。真實 kline 第一時間戳 `2024-01-01 UTC` 與 NaT 組成二列索引，兩種順序分別拋出位置 1／0；這是 r1 的最小反例重跑。將模組函式暫時替換成改前 `bad = np.flatnonzero(np.diff(index.asi8) <= 0)`、位置 `bad[0]+1`，重跑第一個 node → NaT 兩例 `DID NOT RAISE`，其餘三例通過，2 failed／3 passed in 0.07s，pytest rc=1；替換隨即還原，runner 最終 rc=0。產品碼 `time_order.py:21-25` 直接比較相鄰 int64 並合併 isna，亦避免大跨度時間戳相減溢位。長度 0／1 例外仍遵守既定 SPEC。

同 runner 使用 `_real_frame()`、`_run_branch()` 與 contract 之七分支×七組合，去 spy 後產 49 例 npz，再呼叫交付的 `branchdiff()`；42 對、shape mismatch 0、NaN／有限位置不一致 0、最大相對差 58.82005852248459、最大絕對差 0.09747552871704102，觸發 true。重產 JSON 與交付檔 cmp rc=0，不僅比 summary。候選探針再呼叫交付 locate，`cmp handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json /tmp/review-7e8d/locate.json` → rc=0。NaN payload／signed zero 的原始 bytes 不在這兩份收據之比較定義內；未宣稱另驗。

### 必答 (2a)／(2b)：assumed 與四個未查面

(2a) assumed①在目前 repo 生產分派之碼證範圍成立；不是任意外部直接呼叫的不可達保證。assumed②只能限於現行持久化標準路徑，作為所有 IC 頁輸入的前提不成立。未查1 未找到帶選欄之 factory post-IC 生產 caller；未查2 有輕量成本反證，未證 full-scale 安全；未查3 不能把 Polars 4.7e-5 等同 float32 回存誤差；未查4 原相對差符合 SPEC，近零放大另作解释，不能重定分母消除觸發。

(2b) assumed①／未查1：`rg -n '_layer6_5_preprocessing|_layer6_5_post_ic' momentum api --glob '*.py' --hidden` 僅列 factory 的三個定義／包裝位置及 `timeframe/multi_tf_generator.py:1432`。後者經 `_execute_l65_with_degradation` 傳 merged_df、config，沒有 selected_features；`feature_factory.py:2965` 因 None 走 `_layer6_5_pre_ic`，`:2971-2973` 三項強制 False。`_build_l7_raw_preprocessing_config` 同樣三項 False。`:3069-3116` 的 post-IC 若被外部直接呼叫，確實可在 `_cgsa_registry` 非空時落入 `:3136-3150` registry，但目前沒有該帶選欄之生產 caller。真正 `run_ic_first` 在 `:2730` 經 transform_selected；IC 頁 `ic_analysis_service.py:2923` 亦走該入口。本家沒有實跑完整 multi-TF／IC-First 生成，故不把搜尋閉包誇大為執行期不可達證明。

assumed②：`feature_storage.py:47-49`、`:2239`、`:2420-2421`、`:2689-2690` 支持標準落盘經 float32 邊界；V7 還可編成 float16，不宜逐字稱全部 H5 float32。IC 頁 `ic_analysis_service.py:3001-3005` 對明示 features_path 直接 pd.read_hdf／pd.read_parquet，無 dtype 限制；FeatureReader 也依 Arrow schema to_pandas，沒有統一轉 float64 的保證。`probe_candidate.py` 把本轮 `_real_frame()` 真實欄寫到 tmp HDF5，再經真正 `_load_features_for_transforms(None, None, None, path)` 讀回，輸出 `H5_LOADER_DTYPES ['float64'] equal True`。這證明受支援之讀入路徑可接受 float64；沒有聲稱主機目前某個正式產品 H5 已是 float64。

未查2：同資料先轉 float32，再沿欄軸重複 32 次作為明示成本工作負載（3000×192、576000 格；不是新增市場樣本）。JIT 預熱後串行比較 `transform_array_fast(x, winsorize=False, rank=False, zscore=True, zscore_window=100)` 與 `_rolling_zscore_2d(x, [100], 1e-8)`，以 perf_counter、tracemalloc 量測：fast 0.003617833s／9,216,384 bytes；float64 0.037660833s／27,678,667 bytes；兩出口均 float32。約 10.4× 時間、3.0× 配置峰值；這是單次微探針、非 RSS、非硬性門檻、未含群組並行／磁碟／mask 成本。float64 核心 pandas rolling 建立多份 full-size 中間陣列，這個成本與 `feature_preprocessor.py:2767-2787` 碼證相符；不能推論現有大群組在 8GB 上一定安全或一定 OOM。

未查3：以同一真實 frame 先 cast float32，legacy／Polars／registry 同輸入比較：

| 步驟 | 分支 | 最大絕對差 | 最大相對差（legacy 非零） |
|---|---|---:|---:|
| rank | Polars、registry | 0 | 0 |
| zscore | Polars | 3.629922866821289e-5 | 0.00839050645856116 |
| zscore | registry | 0.038481950759887695 | 0.08091652406364638 |
| rank+zscore | Polars | 1.52587890625e-5 | 1.0 |
| rank+zscore | registry | 0.08045291900634766 | 58.82005852248459 |

因此 rank 同值差異可由共用 float32 輸入消除，但 zscore 差異沒有消失。locate 重跑之 Polars zscore 最大差格為 EMA21 第903列：legacy 0.7839558124542236、Polars 0.7839084267616272，float64 局部窗直接計算 0.7839557899042652，差 4.738569259643555e-5，遠高於該值一次 float32 捨入。此證明兩條計算路徑不同，沒有下游指標／容差來源可斷言「已足」；本家不發明統計容差或把量測升格為已證明的 ML 結果錯誤。

未查4：`probe_change_report.py:100-113` 以 |legacy| 為分母，零值另記 count／max absolute，finite mismatch 計入 diff_cells；與目前 SPEC 所定量級及 r1 要求一致。58.8 在接近零 z 值處確有放大，但 registry 的 0.038／0.080 與同 float32 輸入之結果表明不只是分母病態。若原始 x 的窗 std 用來正規化，應計算 `|x_a-x_b|/std`；zscore 出口已無量綱，其絕對差本身可解讀為標準化單位差，不宜再直接除以原始價格 std 形成不同單位。該額外診斷不能替換本輪既定 >1e-3 的觸發，也不能刪近零格。

### 必答 (3a)／(3b)：§N 殘留處置

(3a) 維持殘留，理由值為 `needs-research`。具體待研究事項是大型 registry 群組之數值改善與 8GB 記憶體／時間成本，以及生產可達 Polars 臂之剩餘精度差；不是「之後再說」。原定觸發已成立，數字如上，不能改寫成未觸發或將問題銷帳。這項處置支持本批收批，沒有把已定之遮罩／因果修補降格。

(3b) 這是資料品質問題，修正方向合理且已有可行性證據：`probe_candidate.py` 僅在 tmp monkeypatch numba helper 之單步 zscore 呼叫為 `_rolling_zscore_2d(arr, [window], epsilon)`，其餘核心／mask 不改；共用 float32 真實輸入，七組合 registry 與 legacy 的全陣列數值及 NaN 位置 exact equality 全 True、max_abs 全0。該候選證明可改善核心，不證 full-scale 成本可接受。本輪成本反證及目前生產入口三項关闭，使「立即用現有 pandas full-array 核心替換」的收益／成本尚不足以直接採納。

主委立場有兩個需要修正的部分：① float32 輸入只消除 rank 同值集合差異，registry rank+zscore 仍可差 0.08045，不能把組合最大差全歸 rank 量化；②只替換 registry 並把 §N「各分支核心不一致」整條標已處理會漏掉仍可達 Polars 之差异，也未驗大型 registry 成本。若後續採 registry 修法，其 §N 處置只能表述 registry 子項已處理，Polars 與 float64 輸入量化之子項仍具名保留；本輪没有修改 SPEC／manifest。既有 registry 單步差異非本批引入之主委判定未由本家重生改前 baseline；本家維持其為 brief 已驗證事實，未冒稱獨立重驗。

### 必答 (4a)／(4b)：是否可收第 1 批

(4a) 可以，依本家 (3a) 維持附數字的 needs-research 殘留處置。原反例閉合、量級收據完整且可重生、生產分派碼證與候選成本均支持此判斷；停輪依據是上述具體核對，不是因 sentinel 而停輪。r1 已通過之主體／前端未重跑；本輪没有新增生產 P0／P1 反例。

(4b) 擋收第 1 批之 P0／P1：none。

### 實跑、失敗與範圍界線

- cwd `/tmp/review-7e8d/work`：`env PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python run_review.py` → rc=0；8 passed、預期舊核心 mutant 2 failed／3 passed，49 例 dump、float32 三組分支比較、成本量測完成。
- 同 cwd／直譯器／環境之 `probe_candidate.py` → 首跑 rc=1，僅本家 npz 的欄名陣列誤為 object，locate 以 allow_pickle=False 讀入而拒絕；候選七組及 H5 loader 已完成。修正自產 npz 欄名為 Unicode、未改產品／交付腳本後重跑 → rc=0，`CANDIDATE_COMPLETE`、七組全等及 locate 完成。沒有放寬生產測試斷言。
- 兩份 JSON 對交付收據 `cmp` 均 rc=0；`cmp /tmp/review-7e8d/status-before /tmp/review-7e8d/status-final` → rc=0。狀態命令皆為 `git status --short -- momentum api frontend tests templates config`，既有 dirty cache／golden 未改。
- 未跑慢閘、全量 18 檔、瀏覽器、完整 FF 生成、下游 ML、正式大型群組成本。本家没有啟動其他委員或重測試並行；沒有修改主樹 data_cache、產品碼、測試、文檔、git。

ASSUMPTIONS_VERIFIED: NaT 兩原反例 fail-closed、旧 mutant 可鑑別；49 例跨分支／locate 收據重生相同；目前 repo registry 三項分派關閉之碼證；H5 loader 可保留 float64；float64 候選七組數值全等與輕量配置成本，完整大型成本未驗證。
TESTS_RUN: run_review.py rc=0（8 passed、預期 mutant rc=1）；probe_candidate.py 最終 rc=0；兩收據 cmp rc=0；產品狀態 cmp rc=0。
FAILURES_SEEN: 預期 NaT 舊 mutant 兩紅；本家欄名 npz object serialization 導致 locate 首跑 rc=1，Unicode 修正後 rc=0；無產品修補。
SCOPE_CHANGES: none；主樹僅新增指定交件；其餘實跑及候選替換均 /tmp 複本。
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）；未核可產品輸出大小／schema／dtype 改動。
HANDOFF_NOT_UPDATED: 本輪 brief 唯讀，依 AGENTS 規則不另寫狀態交接，根 HANDOFF.md 未改。
產出: handoffs/20261001-icpostleak-b1-review-r2-codex.md

交件檢查：`bash scripts/completeness_check.sh --single handoffs/20261001-icpostleak-b1-review-r2-codex.md --family codex --round-id 7e8dc118-da89-4cc4-ac6e-c4eec06ee55a` 首跑 rc=1（本家漏填 sentinel 類別）；就地補 `**類別**: other` 後 rc=0，`COMPLETENESS PASS(single)`，1 個 canonical ID。
最後範圍檢查：`cmp /tmp/review-7e8d/status-before /tmp/review-7e8d/status-cleanup` → rc=0；快照均來自指定之 `git status --short -- momentum api frontend tests templates config`。
清理：`rm -r /tmp/review-7e8d` → rc=0；`test ! -e /tmp/review-7e8d && test -d /tmp/claude-501` → rc=0。本次 workdir 已清除，claude-501 保留；其他 session／系統工作目錄未動。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R1-P2-01,CODEX-R1-P2-02
