# FFPROD 特徵生產層普查 — SPEC

> 版本：v2（2026-10-26；規格審查 r1 處置〔收斂檔 `handoffs/reconcile/20261026-ffprod-x-review-r1/synth.md`〕：①L2 單一來源不變式〔公開結果＝落盤群組＝L5／L6 實收 L2 欄〕入 Task 2.1 量測與 Phase 3 L2 施工之驗收；②§G 格補 L2 三條生產臂〔`L2.polars`、`L2.pandas_serial`、`L2.pandas_parallel`〕；③全特徵候選逾 8 GB ⇒ 效能／記憶體／檔案大小記 blocked-by 硬體，不以較小規模之數字代替；④校準域縮尾核心〔legacy〕與公開主群組〔快速核心〕之並存列為改值候選；⑤§C 刪「JSON 契約為單一真相源」之過期敘述〔v1 已改一次性收據〕；⑥§N 舊策略特徵管線〔`FeatureExtractor`→HDF5→ML 服務〕合併為一條並附呼叫鏈）。前版 v1（2026-10-26；初稿，依偵察諮詢 r1 收斂檔 `handoffs/reconcile/20261026-ffprod-x-consult-r1/synth.md` 與主委獨立版 `handoffs/20261026-ffprod-x-consult-r1-claude.md`）。
> 來源：`docs/TICKET_ORDER.md` 第 9 列（全票排序第 9 步，吸收原「縮尾重複」與 `docs/NUMVIEW_SPEC.md` §N R2／R5）　|　日期：2026-10-26　|　對應 TODO：`docs/manifests/FFPROD.json`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（CLAUDE.md 任務分派規則）。
- **命中高風險原則**：(a) 特徵數值與落盤精度；(b) 特徵工廠共用路徑（L2、L6.5、多週期、落盤）與 IC 前處理；(c) 量測→使用者裁定→施工→重凍多 phase；(d) IC 選欄所吃之特徵值與縮尾。
- RISK-HIT: a,b,c,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（下列 8 條 FACT-RECEIPT）：
  - FACT-RECEIPT: `sed -n 1984,2008p momentum/FeatureEngineering/feature_factory.py` → 印出 `result = engine.compute_all_polars(layer1, data, indicator_specs)` 後於 `if self._cgsa_registry is not None:` 內逐類 `category_frame = engine.compute_category(...)`、`self._persist_layer2_category_group(category, category_frame)`（主委 實跑 2026-10-26）
  - FACT-RECEIPT: `jq -r '.cells[] | "\(.cell_id) \(.max_abs)"' handoffs/run_receipts/20261024-numview-l2-arm-matrix.json` → 印出 `A_BTCUSDT_1h 0.0`、`B_BTCUSDT_1h_4h 0.0078125`、`C_BTCUSDT_1h 0.00048828125`、`A_BTCUSDT_12h 0.0`（主委 實跑 2026-10-26）
  - FACT-RECEIPT: `sed -n 47,49p handoffs/run_receipts/numview_probes/l2_source_effect.py` → 印出 `eating = [u for u in uses if u["l2_columns"]]`（L5／L6 呼叫實收 L2 欄；收據 A 8、B 14 次）（主委 實跑 2026-10-26）
  - FACT-RECEIPT: `sed -n 127,136p momentum/FeatureEngineering/preprocessing/_numba_transforms.py` → 印出 `mean = bn.move_mean(arr, window=window, min_count=min_periods, axis=0).astype(np.float32)`、`std = bn.move_std(...).astype(np.float32)`（主委 實跑 2026-10-26）
  - FACT-RECEIPT: `sed -n 3171,3177p momentum/FeatureEngineering/feature_factory.py` → 印出 `_build_l7_raw_preprocessing_config` 對 `rank_transform`、`adaptive_zscore`、`gaussian_normalize` 一律 `_set_preprocessing_step_enabled(..., False)`（主委 實跑 2026-10-26）
  - FACT-RECEIPT: `sed -n 112,125p momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py` → 印出 `sample = clean_values[-max(1, int(sample_size)) :]`；`sed -n 112,120p momentum/FeatureEngineering/preprocessing/_fast_adf_numba.py` → 印出 `values = values[: int(sample_size)]`（主委 實跑 2026-10-26）
  - FACT-RECEIPT: `sed -n 738,745p momentum/FeatureEngineering/feature_factory.py` → 印出 `if not data.empty and not preserve_dtype:` `data = self._ensure_float32(data)`（主委 實跑 2026-10-26）
  - FACT-RECEIPT: `grep -rn "save_features_to_hdf5\|load_features_from_hdf5" api momentum` → 命中 `api/services/feature_task_service.py:197`、`xgboost_task_service.py:187`、`model_task_service.py:171`、`shap_analysis_service.py:71`、`:133`（主委 實跑 2026-10-26）
- **待使用者確認**（未確認前不得施工 Phase 3）：Phase 2 量測後之改值項逐項取捨（L2 單一來源擇臂、sigma 高精度、zscore 最少有效值數統一、d\* 取樣方向統一、層間 dtype 統一、校準域與公開主群組之縮尾核心統一、縮尾唯一責任端與 IC 頁開關）——依 `docs/TICKET_ORDER.md` 第 9 列「改特徵值或輸出檔者先報使用者」。
- **已確認結果**：2026-10-24 使用者（`docs/TICKET_ORDER.md:33`）「是不是該普查特徵生產層的計算是不是最平衡解，確保特徵層程式和計算只有一套最平衡解的算法？」「我印象小數據量和大數據量的測試可能不是線性，無法用推測的」。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條、優化優先序（跨 tier 可重複＞多 symbol 穩定＞資料品質＞速度＞輸出大小）、不弱化 NaN／inf gate、不擅改輸出大小。
- 2026-09-29 dtype 裁定（`docs/FFSTAT_SPEC.md:221`，使用者「維持自動選（建議）」）：落盤依值域逐段選 float16／float32，不重議；本票只改計算精度與實作數。
- 量測＝路徑覆蓋（使用者 2026-10-22）：每格附獨有分支；正確性以秒～分級真實資料 oracle；效能、記憶體、檔案大小只每個改值候選一格全特徵真實資料；禁幣種×週期×組合乘積；無收據前不寫快慢與可行。
- 資料一律真實 `data_cache/feature_klines/kline_cache.h5`（12h 用長歷史檔，沿 NUMVIEW 判準 `cell_rules.kline_source`），禁合成 fixture。
- 不改 post-IC 轉換（NUMVIEW 已定：IC 頁與 IC-first 同一 `pandas_legacy`、輸出 float32）。
- 研究設計不寫死 24h／UTC／加密貨幣特有假設。
- 本票不新增常駐契約或清單檢查：盤點（Task 0.1）與量測（Task 2.1）為一次性收據，使用者裁定記於 §A；唯一常駐測試為 §G 值指紋對照與 Phase 3 各施工項之單元測試。施工清單 `docs/manifests/FFPROD.json` 於本 SPEC 凍結後依 `templates/TODO_GENERATION_PROMPT.md` 生成。

## §G Golden / Baseline
- **條件**：涉特徵生成與計算 ⇒ 真實 kline；改前基準於 Phase 0 凍結。
- **凍結時機與設定**：Task 0.2 於施工前 HEAD 以其路徑覆蓋格生成，存 `tests/_golden/ffprod/pre_change_fingerprints.json`（值指紋沿 `tests/feature_engineering/preprov_helpers.py` 之 `value_fingerprints`：逐欄原生 dtype 位元組 sha256、NaN 遮罩、欄名與欄序）。
- **通過條件**：Phase 1 之收斂 ⇒ 全格逐位元等於凍結值；Phase 3 之改值項 ⇒ 只限使用者核可之目標欄（決定紀錄 `changed_targets`）不等，其餘逐位元相等；超出即列欄與實際差 = FAIL。

## §P Phase 與依賴

### Phase 0 — 契約、判準、改前基準（依賴：無）
**Task 0.1 — 並存實作盤點收據**
- 目標：每一種計算之並存實作、分派條件、生產呼叫鏈一次盤清。　檔案：新建收據 `handoffs/run_receipts/<日期>-ffprod-inventory.json`（一次性盤點，不設常駐驗證測試）。　既有 caller：無。
- 改法：合併偵察 r1 兩家盤點與主委版（收斂檔群集 A–J 與主委版第二節）；每組列實作（path＋函式）、分派條件（path:line）、生產呼叫者（path:line）或無生產呼叫者之 `grep` 命令與輸出、處置候選（保留／刪除／量測）。
- **驗證**：收據每個「無生產呼叫者」項附 `grep -rn "<函式名>" momentum api` 之實跑輸出（只命中定義行）；每個「量測」項對應 Task 2.1 之一個候選。
- **邊界**：①同名函式於多檔（依 path＋函式定位）；②只經字串查表呼叫之方法（如 `rolling_aggregator.AGGREGATORS`）以字串字面 grep 計為呼叫者。
- **存活至**：本票交付後保留（Task 1.1 刪除依據）。
- **覆蓋風險**：無。
- 不可做：不在本 Task 改任何產品碼；不建常駐之清單檢查測試（盤點為一次性收據）。

**Task 0.2 — 估時與改前基準凍結**
- 目標：施工前 HEAD 之值指紋。　檔案：新建 `scripts/ffprod_freeze_baseline.py`、`tests/_golden/ffprod/pre_change_fingerprints.json`、`tests/feature_engineering/test_ffprod_gate.py`（§G 對照）。
- 改法：格只取覆蓋獨有分支之最少集合（A 單週期 1h、A 12h、B 多週期 1h＋4h、C 全特徵 1h，另依盤點補 sigma 縮尾開、fracdiff／ADF 開之單週期格；L2 三條生產臂各至少一格——`L2.polars`〔預設〕、`L2.pandas_serial`〔`FFACT_USE_POLARS=0`、`FFACT_L2_CATEGORY_WORKERS=1`〕、`L2.pandas_parallel`〔`FFACT_USE_POLARS=0`、workers>1〕，以 A 單週期 1h 加環境覆寫為之，不另加幣種）；先估時（>30 分之跑先白話告知使用者）；逐格生成並寫值指紋與生成身分（HEAD、設定、資料集 sha256）。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q` 於凍結 HEAD 全綠（重生成之值指紋 sha256 逐位元等於凍結值）；同格重跑兩次值指紋相同。
- **邊界**：①凍結中途中斷 ⇒ 未完成格不寫入；②某格於 8 GB 不可跑 ⇒ 標 blocked-by 硬體並列 §N。
- **存活至**：本票交付後保留（Phase 3 只重凍使用者核可之 `changed_targets`）。
- **覆蓋風險**：Phase 3 局部重凍。
- 不可做：不在凍結前改任何產品碼；不以多幣種重複同一分支湊格。

### Phase 1 — 不改值之收斂（依賴：Phase 0）
**Task 1.1 — 刪除無生產呼叫者之並存實作**
- 目標：契約 `no_production_caller` 且處置 `remove` 者刪除。　檔案：依契約清單；同步刪改只測該等實作之測試（同提交登記審清單）。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q` 全綠（§G 全格值指紋 sha256 逐位元等於凍結值）；被刪函式名 `grep -rn` 於 `momentum api tests` 零命中；`bash scripts/check_decoupling.sh` 之 `R2=… R3=… R4=…` 摘要行不增。
- **邊界**：①僅 `scripts/` 呼叫之實作（如 `transform_registry_groups` 只 `scripts/freeze_ratiounsafe_baseline.py`）——該腳本為已收案票之凍結工具時，連同改寫或標記該腳本停用並列理由；②動態 import／字串查表呼叫者以 Task 0.1 邊界②處理。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不刪有生產呼叫者之實作；不以「看起來沒人用」代替 grep 證據。

**Task 1.2 — 縮尾有效設定入逐欄處理紀錄**
- 目標：PRE-PROV 逐欄紀錄可回答「實際用哪種縮尾、哪些參數」。　檔案：`momentum/FeatureEngineering/contracts/run_provenance.json`（逐欄紀錄增縮尾 method、分位端點或 sigma k、窗、最少有效值、計算精度）；`preprocessing/feature_preprocessor.py` 紀錄寫入點；讀取 API。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py tests/feature_engineering/test_ffprod_winsor_provenance.py -q` 全綠：§G 全格特徵值指紋 sha256 逐位元等於凍結值；新欄於縮尾開之格非空、關之格為 `disabled`；舊紀錄（無新欄）讀取 ⇒ 依 PRE-PROV 既有舊格式處置。mutation：寫入時漏記 method ⇒ 契約驗證拒收。
- **邊界**：①縮尾關 ⇒ 新欄記 disabled 而非空值；②比值不安全欄原值通過 ⇒ 記 passthrough。
- **存活至**：本票交付後保留（Task 3.6 依之判唯一責任端）。
- **覆蓋風險**：無。
- 不可做：不改縮尾算法本身。

### Phase 2 — 改值候選之量測與使用者白話閘（依賴：Phase 1）
**Task 2.1 — 改值候選量測**
- 目標：對 §A 所列每個改值候選，以 Task 0.2 格與判準量「改前／改後」之值差、IC 翻轉、速度、峰值記憶體、輸出檔大小。　檔案：新建 `scripts/ffprod_measure.py`、收據 `handoffs/run_receipts/<日期>-ffprod-candidates.json`。
- 改法：候選以環境或探針切換（不改正式碼），每候選一格全特徵真實資料量效能與記憶體。
- **驗證**：收據 `handoffs/run_receipts/<日期>-ffprod-candidates.json` 每候選有值差摘要（變動欄數、最大絕對差、NaN 遮罩差欄數）、IC 正負號翻轉與選欄進出數、耗時秒數、峰值 RSS 位元組、輸出檔位元組；候選集合 == Task 0.1 收據之「量測」項集合（主委收件時 `jq` 核對）。
- **邊界**：①某候選於全特徵格逾 8 GB ⇒ 該候選之效能、記憶體、檔案大小記 blocked-by 硬體（RM-FULLSCALE），不以較小規模之數字代替；值差與判準仍於可跑之格量並標其規模；②候選間交互（例 sigma 與層間 dtype）⇒ 單獨與合併各一次；③L2 候選另量 registry 落盤群組（逐類 concat）對公開結果、對 L5／L6 實收 L2 欄之值差（三者兩兩比）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不在量測前改正式碼；不以小樣本推論大規模（使用者 2026-10-24）。

**Task 2.2 — 白話閘與決定紀錄**
- 目標：逐候選向使用者白話報告差距與建議，取得裁定。　檔案：本 SPEC §A「已確認結果」逐候選記使用者裁定（日期＋逐字）與 `changed_targets`（欄集合），並據以修訂 Phase 3 各 Task。
- **驗證**：§A 之已確認結果條數 == Task 2.1 收據候選數；Phase 3 每 Task 引用其對應之已確認結果行（審碼核對）。
- **邊界**：①使用者選保留現狀 ⇒ 該候選不施工、具名登記差異上界；②使用者要求再量 ⇒ 回 Task 2.1。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不以委員共識代替使用者裁定（本項為使用者明定「先報使用者」）。

### Phase 3 — 改值施工（依賴：Phase 2 之對應裁定）
**Task 3.x — 依裁定施工**（每候選一 Task；候選清單與施工細節於 Task 2.2 後以 SPEC 修訂版具體化）
- 目標：只留裁定之一套實作，刪其餘；重凍 `changed_targets`。
- **驗證**：`venv/bin/python -m pytest tests/feature_engineering/test_ffprod_gate.py -q` 全綠：非 `changed_targets` 之欄值指紋 sha256 逐位元等於凍結值；`changed_targets` 之新值指紋等於 Task 2.1 收據之改後值指紋；該組被淘汰實作之函式名 `grep -rn` 於 `momentum api` 零命中。
- **邊界**：①多週期與單週期皆覆蓋；②續跑（CGSA 葉）與 IC 快取之身分隨改值失效（沿 NUMVIEW algorithm_id）；③L2 施工項另新增單元測試：公開結果、registry 落盤群組逐類 concat、L5／L6 實收 L2 欄三者之欄集合、欄序、NaN 遮罩與原生 dtype 值位元組相同（mutation：落盤之 category_frame 任一欄加 1e-3 而公開結果不變 ⇒ 紅）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：未經裁定之候選不得施工。

### Phase 4 — 文件同步（依賴：Phase 3）
**Task 4.1 — 文件與狀態**
- 目標：白話縮尾三端責任表（特徵階段 L6.5、IC 分析前處理 `momentum/Analysis/data_preprocessor.py`、IC 後轉換〔縮尾關〕）、ROADMAP／TICKET_ORDER／HANDOFF 狀態。
- **驗證**：`bash scripts/gen_fact_key_blocks.sh --check` rc=0；白話網頁同 commit 重生。
- **邊界**：①生成區塊不手改；②凍結 SPEC 不改字面。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不改 TICKET_ORDER 之順序與範圍欄。

## §V 驗證策略與邊界測試目錄
- **mutation**：每個驗正確性之測試附可證偽設計（引 `docs/TEST_DESIGN_CHARTER.md`）；Task 0.1／0.2／1.2 之 mutation 如各 Task 所列。
- 測試層級：契約單元（秒級）、真實資料 oracle（分級）、§G 全格對照、每改值候選一格全特徵效能。
- **防假綠**：既有測試斷言不放寬；刪改測試同提交登記審清單（使用者 2026-10-17 裁定）。
- **邊界目錄**：全 NaN 列（縮尾、zscore 最少有效值數）、大尺度低波動欄（sigma 精度）、校準序列長於 N（d\* 取樣方向）、多週期與單週期（層間 dtype）、registry 有無與 Polars 有無（L2）。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert；Phase 3 每候選一 commit；§G 不符不合併。

## §N N/A 登記與殘留
- **FFPROD-R1 舊策略特徵管線（含 HDF5 存法與舊手寫指標）**——呼叫鏈：`api/routes/feature_engineering.py:20` → `api/services/feature_task_service.py`（`:82` `create_feature_extractor()` 之 `extract_features_from_strategy`，即 `momentum/factories.py` 之 `FeatureExtractor`，經`indicators/{ema,rsi,macd}_extractor.py` 與 `strategy_registry.py`〔RSI 非 Wilder 平滑〕）→ `:197` `save_features_to_hdf5` → 讀取端 `api/services/xgboost_task_service.py:187`、`model_task_service.py:171`、`shap_analysis_service.py:71`、`:133` `load_features_from_hdf5`。此管線不經特徵工廠（`FeatureFactory`），不屬本票「特徵生產層」之並存實作——`為何現在不做: blocked-by:ML 與策略模組重建（其讀取端 XGBoost／model／SHAP 與策略特徵抽取屬模組成熟度地圖之不完整層；FF／IC-first 之 processed 唯一正式存法為 V2）`；觸發：ML 或策略開票；登記處：本 SPEC §N、RM-FFPROD。
- **FFPROD-R3 跨市場量測**（台股、美股、期貨）— `為何現在不做: blocked-by:PRE-MARKET-DATA（無該市場資料）`；觸發：跨市場資料到位；登記處：本 SPEC §N。
