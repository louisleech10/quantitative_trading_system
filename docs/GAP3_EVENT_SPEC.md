# GAP-3 事件型分析（外部標註正反例匯入 → PIT 對齊 → 條件 IC／ML）— SPEC

> 來源 PLAN/診斷：`白話說明/GAP-3事件型討論.md`（第 12 版；**§7.5 五層取材優先序＝本 SPEC 唯一取材地圖**）；consult R1 `handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md`（C1–C6）；consult R2 `handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md`（C1–C9＝K1–K10 技術定案）；**adversarial R1 收斂 `handoffs/reconcile/20260820-gap3-x-review-r1/synth.md`（15 findings 十三群集 X1–X13 全部寫回；AR-1..AR-6 裁定）**；**R2 收斂 `handoffs/reconcile/20260820-gap3-x-review-r2/synth.md`（composer/grok sentinel 0 findings；codex 6 條 Y1–Y6 全部寫回：entry 映射表 D1-6／分類公式與預設值／`counterexample_kind_effective` derived 值集／mutation 逐條命令與 fixture 身分／M8 permutation quantile／control_kind validator 矛盾解除）**；**R3 收斂 `handoffs/reconcile/20260820-gap3-x-review-r3/synth.md`（composer/grok sentinel；codex 4 條 Z1–Z4 全部寫回：receipt 兩層 schema／`drop_threshold` 預設收回待白話閘裁 x／D4 改 effective 欄／M8 三道防退化硬檢）**
> ｜日期：2026-08-20｜對應 TODO：`docs/GAP3_EVENT_TODO.md`（本 SPEC 白話閘定版後生成）
> ｜票：`docs/IC_QUANT_GAP_REGISTRY.md` #3；使用者 2026-08-20 裁定「討論收案、新 session 起草 SPEC」
> ｜**對抗審第一項工作（強制）**：拿 §7.5 五層清單**逐條**比對本 SPEC——沒漏、沒錯、沒被舊結論污染（衝突時新使用者意圖蓋過舊委員結論；R1 之 C-情境反例結論不取；舊 `CaseRecord`／`_select_negative_timestamps` 語意不取）。第二項＝裁 §A 之 AR-1..AR-6。

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：大（新契約 SoT＋新純函式模組群＋`ic_survivor_contract` 升版＋三入口頁面升級；接 CLAUDE.md 任務分派規則）。
- **命中高風險原則**：
  (a) 數值/資料品質——PIT 對齊、標籤價格語意、固定分母；任一錯＝系統性 look-ahead 或橡皮數字；
  (b) 跨模組共用路徑——`momentum/Analysis/`（IC 主線三入口消費事件樣本）、`ic_survivor_contract.json`（升版影響 validator/consumer/golden）、`operator_registry`（新變化類特徵）、`api/`＋`frontend/`（B5）；
  (d) ML/回測正確性——事件樣本是 ML 訓練集入口；case-control 抽樣誤讀＝把樣本勝率當實盤勝率。
- RISK-HIT: a,b,d
- 命中 (a)(d) ⇒ **§G 必填、adversarial review 必跑**（三家全員：依 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行）。
- `momentum/factories.py` 出口：B1–B4 新純函式由測試與（B2）`ICFilterOrchestrator` 內部消費，**不需新出口**；B5 API 接線若需服務端消費者，屆時新增 `create_event_sample_pipeline()` 一個出口（R3 解耦），TODO 階段定簽名。

## §0 前置裁決（D 系列＝R2 C1–C4 合併 2026-08-20 使用者增補；本節＝取材合併後「最完整精確」之點）

**D1 — 標籤與價格語意（R2 C1 ⊕ U4b 改寫）**
1. 契約必填 `entry_price_semantic ∈ {trigger_open, trigger_close, next_open, decision_bar_open, decision_bar_close}`（**事件頂層欄**，與 `label_definition` 平級——R1 X11／X1；字面唯一住契約檔）＋`label_return_mode ∈ {open_to_close, open_to_horizon_close, close_to_close}`（屬 `label_definition`）。
2. **預設 `close_to_close`（U4b；改寫 R2 C1 之「A/B 預設 `open_to_horizon_close`」）**：標籤基準一律相對 **t₀ close**——與 IC 主線 label 同語意（`label_generator.py:40-47` 之 `close.shift(-h)/close-1`），條件 IC 直接吃；「基準價語意」欄保留以防未寫明。
3. 條件 IC（`statistic_kind=conditional_ic`）之 `label_value`＝**條件必填**（R1 X3）：缺 ⇒ `capability_status=unavailable` reason=`missing_label_value`（字面入契約檔）；**v1 不重算**使用者 label（一致性探針＝§N-8）——不留「重算或拒絕」二選一給 TODO。**禁止**把「語意不同的」序列型 `return_N` 靜默當事件 label；`label_return_mode ≠ close_to_close` 而沿用主線 label ⇒ 必標 `label_price_mismatch=true`。
4. 誠實揭露（U4b／§2-2）：**實際進場價**（open 或 t₀−k）之持有報酬與**標籤基準**（t₀ close）報酬為兩個數，全部 K 線驗證兩數並排、不混。
5. **label 錨不變式（R1 X2）**：label 錨＝t₀ close，與 `decision_at` **永遠脫鉤**（`decision_offset_bars>0` 不改變錨）；**禁止**以 `decision_at` 列 join 主線 `return_N`（該列 `return_N` 錨在 decision close ≠ t₀ close）；B2.3 驗收含 t₀−k 手算案例斷言錨不隨 decision 移動。
6. **entry 語意 → bar/price 唯一映射（R2 Y1）**：`trigger_open`＝t₀ bar 之 open；`trigger_close`＝t₀ bar 之 close；`next_open`＝t₀ 之後下一根**錨定 TF** bar 之 open；`decision_bar_open`／`decision_bar_close`＝decision bar（t₀−k）之 open／close。`entry_at`＝該 bar 對應時點（open 語意＝bar open_time、close 語意＝bar close_time）；validator 檢 `decision_at ≤ entry_at`；receipt 增 `entry_at_ms`＋`entry_price_source{bar_open_ms, field}`。所有「entry 依契約語意」處一律指本條。

**D2 — PIT 時間軸與對齊收據（R2 C2 ⊕ R1 C1 六時間欄 ⊕ 8/20 t₀−k 擴充）**
1. 六時間欄不變式（validator 機械檢查）：`observed_through ≤ feature_cutoff[tf] ≤ decision_at ≤ entry_at ≤ label_start < label_end`；`feature_cutoff` **per-TF 展開**，規則＝`max{bar.close_ms ≤ decision_at}`（12h t₀ 對 1h/4h 在 UTC 整點為常見特例，一律走 as-of）。
2. 決策時點單一表示法（R1 X1＝AR-1 定形）：匯入欄＝`t0`（錨；epoch ms UTC；＝觸發根 open_time）＋`decision_offset_bars`（int ≥0，預設 0；語意＝決策時點為 t₀ 往前第 k 根**錨定 TF** bar 之 open；0＝t₀ open）；**不設** ms 覆寫欄（單一表示法）；`decision_at_ms` 由對齊函式推導寫入 receipt（`t0_ms/decision_offset_bars/decision_at_ms` 三欄並排）；validator 增 `decision_at ≤ t0_open_ms`；缺 bar 無法推導 ⇒ `missing_bar`。特徵截止跟著 decision_at 走。A/B 之「事件在未來」⇒ `event_known_at_decision=false`、特徵 `observed_through ≤ decision_at`、選樣可用結果欄（分路徑見 D3）；`trigger_bar_open` 語意之決策只在 receipt 能證明事件於 open 前已知時合法（R1 C1-3），A/B 預測型**不**受此限（其事件本來就在未來、不進特徵）。
3. 時間戳單一單位 **epoch ms UTC**；量級像秒卻宣告 ms（或相反）⇒ 拒絕（R1 C2；ms 單位閘）。
4. 對齊收據兩層（R2 Y1／R3 Z1；兩層皆入 SoT、§G-2 驗兩層）：**事件級**每事件一列 `{t0_ms, decision_offset_bars, decision_at_ms, entry_at_ms, entry_price_source{bar_open_ms, field}}`；**per-TF** 每事件 × 每 TF 一列 `{feature_cutoff_ms, last_bar_open_ms, last_bar_close_ms, row_id}`。失敗**枚舉**（聯集，R2 C2）：`invalid_timestamp_unit／timezone_missing／missing_bar／duplicate_bar／unsorted_bar／no_boundary_match／feature_after_decision／entry_before_decision／label_window_incomplete／nonpositive_reference_price／nan_or_inf_feature／reference_symbol_unavailable／warmup_insufficient_<tf>／tf_boundary_ambiguous`；逐事件寫 reason，**禁 silent `continue`**（現雛形 `xgboost_batch_service.py:621,651` 之靜默跳過不沿用）。

**D3 — 條件引擎欄位角色隔離（R2 C3）**
1. 所有 expression／欄位分三角色：`feature`（必 `available_at ≤ feature_cutoff`）／`selection_predicate`（可含未來欄，**只進抽樣 provenance**）／`label`（只進結果欄）；等價欄位登記 `column_role ∈ {pit_feature, trigger_outcome, future_outcome}`。
2. typed safe-subset AST＋canonical expression digest＋欄位角色清單＋最大 lookback；純函式落 `momentum/Analysis/event_samples/condition_engine.py`；`/search` 與 IC `event_filter` **皆 adapter**；多組 label 用 `label_id` manifest（非布林覆寫）。
3. legacy `df.eval` 路徑（`event_filter.py:55-105`）保留為既有遮罩 adapter；新產生器未通過角色隔離 receipt 前**不得宣稱「已共用完整引擎」**；`allowed_filtering_params={'price_change'}`（`requests.py:50`）改為契約化允許清單。
4. 匯出 ML 特徵表時 assert 無 `future_*`／`trigger_outcome` 角色欄（case-control 選樣可看答案，特徵不可）。

**D4 — 全部 K 線驗證＝固定分母 evaluation manifest（R2 C4；U11 一次建完整；整票靈魂 J1 的機器形）**
1. all-bars evaluation manifest 以 `decision_at` 為索引，只納 `eligible`（答案窗完整、資料連續、價格有效、PIT 合法）；報 `n_total／n_eligible／n_labeled／n_unknown／n_tail_excluded／n_missing`＋reason。
2. 輸出：precision／recall／F1／PR 曲線＋AUC／PR-AUC／lift（top-q% 與固定閾值）／confusion matrix／訊號頻率／簡單 signed 持有報酬（**實際進場價 → 答案窗末 close**，與 D1-4 並排揭露）／按 symbol、direction、**`counterexample_kind_effective`（derived 欄；R3 Z3）**、時間段分層＋CI（分層報表列 `n_unclassifiable`）。
3. `prevalence_learn` 與 `prevalence_full` **必**並排＋`sample_design=case_control` 揭露＋lift；缺任一 ⇒ `capability_status=unavailable`，reason=`missing_prevalence_disclosure`。
4. **不做**（不碰回測層；成熟度地圖）：倉位、手續費/滑價、複利、資金曲線、turnover/capacity、triple-barrier 最佳化、long-short 組合。

## §A 假設與待使用者確認

**已驗證事實（FACT-RECEIPT；15 條，皆可由 repo 內命令重現）**

- FACT-RECEIPT: `sed -n '40,47p' momentum/FeatureEngineering/labels/label_generator.py` → 印出 `ret = close.shift(-horizon) / close - 1` 與 `generate_return` 同式（IC 主線 label＝close-to-close；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '99,103p' api/models/requests.py` → 印出 `price_change_method: ... default=PriceChangeMethodEnum.CLOSE_TO_CLOSE`（/search 預設 close-to-close；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '38,55p' api/models/requests.py` → 印出 `allowed_filtering_params = {'price_change'}`＋參數不在集合即 `ValueError`（/search 篩選僅一參數；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '1229,1241p;1293,1297p' momentum/DataExtraction/case_search_engine.py` → 印出 CLOSE_TO_CLOSE 分支 `df['close'].pct_change()`；`future_{bar}bar_return = (close.shift(-bar) - close) / close`（未來欄以 close 為分母；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '617,655p' api/services/xgboost_batch_service.py` → 印出 `features_df['timestamp_sec'] == case_ts` 精確相等對齊、找不到 `continue`、NaN `continue`、y 由 `case.positive_case` 建（舊雛形對齊＝不沿用清單之碼證；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '16,30p' api/models/case_models.py` → 印出 `CaseRecord` 僅 `case_id/symbol/timeframe/timestamp/positive_case(+source_file/import_time)`（無決策時點/方向/label manifest；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '35,37p' api/services/case_import_service.py` → 印出 `REQUIRED_COLUMNS = ['symbol', 'timestamp', 'Positive_case']`（現匯入僅三必填欄；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '131,134p' api/models/case_models.py` → 印出 `timeframe: Union[str, List[str]]`（批次抓取已支援多 TF 列表；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '55,105p' momentum/Analysis/event_filter.py` → 印出 `apply_filter` 對任意欄 `df.eval(query, engine="python")`、回 `mode/query/n_events/tier`，無欄位角色（Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '361,387p' momentum/core/contracts.py` → 印出 `SplitPlan` 之 `purge_semantic ∈ {rows, timedelta}`、`symbol: Optional[str]`，無事件 label interval/overlap cluster 欄（Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '256,285p' momentum/Analysis/contracts/ic_survivor_contract.json` → 印出 `event_definition_keys` 僅 `definition_hash/timestamps_hash/mode/n_events/n_timestamps_requested` 五鍵、`additional_properties:false`（擴欄必先升版；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `grep -n "UNWIRED_MODULES" momentum/Analysis/model_config.py` → 印出 `68: UNWIRED_MODULES: frozenset = frozenset({"probability_calibration", "sample_weight"})`（sample_weight 未接線；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `grep -RInE 'bars_since|consecutive_|run_length|streak' momentum/FeatureEngineering | wc -l` → 印出 `0`；`grep -n "ts_argmax\|ts_argmin" momentum/FeatureEngineering/operators/derived_operators.py` → 印出 `435:/439:` 定義行（K7 缺口存在、已有算子不重做；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `sed -n '150,154p' api/models/ic_models.py` → 印出 `event_query` 與 `event_timestamps` 欄（IC 後端已收事件清單；Claude 實跑 2026-08-20）
- FACT-RECEIPT: `grep -rn "feature_cutoff" momentum/ | wc -l` → 印出 `0`（per-TF 特徵截止不存在、須新建；Claude 實跑 2026-08-20）

**待使用者確認（未確認前不得實作）**：**待確認：無**（產品語意 U1–U13＋8/20 五點已全數裁定；技術取捨依 2026-08-18 裁定交委員會）。

**對抗審裁決紀錄（AR 系列；R1 三家已全數裁定——`handoffs/reconcile/20260820-gap3-x-review-r1/synth.md`）**

- **AR-1 決策時點 t₀−k 契約形式** → **已裁（X1）**：`t0`＋`decision_offset_bars`（int ≥0，預設 0）、`decision_at_ms` 由對齊推導、不設 ms 覆寫欄；`entry_price_semantic` 值集擴 `decision_bar_open/decision_bar_close`；六欄不變式不破＋`decision_at ≤ t0_open_ms`；規格見 D1-1/D2-2。
- **AR-2 反例自動分類規則** → **已裁（X4）**：`counterexample_classifier_config` 入契約檔；direction-aware signed return、錨＝t₀ close；user 優先、platform 只補缺不回寫、衝突留痕 `platform_suggested_kind`；多類邊界 ⇒ `unclassifiable` 不猜；規格見 Task B1.0/B1.5。
- **AR-3 多標的必要化與 #4 邊界** → **已裁（X6）**：多標的＝必要宣稱；`n_symbols==1` ⇒ `degraded:single_symbol`（exploratory 可跑）；`event_split_plan` 為 B2 各表＋B4.1 必需輸入；#4 不關閉、不做 cross-sectional/GEE。
- **AR-4 一份 SPEC vs 拆兩份** → **已裁（三家一致）**：維持一份 SPEC＋B1–B5；TODO 階段若 B3/B5 膨脹再評估。
- **AR-5 產生器 G1–G6 落哪批** → **已裁（三家一致）**：維持 B3；MVP 不前移 B2（B2 靈魂＝K8 優先）；前移僅得於 TODO 階段由主委明示。
- **AR-6 label 一致性探針** → **已裁（X3；採 2:1 多數＋較小 scope）**：維持 §N-8 殘留（`needs-research`）；配套硬規則＝`conditional_ic` 缺 `label_value` ⇒ `unavailable:missing_label_value`、v1 不重算；grok 之 `label_probe_mismatch` 設計收錄於 §N-8 供日後升級。

**已確認結果**

- `2026-08-19/20 使用者裁決 U1–U13＋8/20 五點`（唯一權威＝討論文檔 §7＋§8 第 8/11 版；本 SPEC 全篇據此）：目標 A/B/C/兩段式全要、一次只多或只空；正反例外部標好＋CSV＋搜尋條件一起匯入、正反例附實際漲幅；**U4** 決策時點＝t₀ open 或 t₀−k、特徵＝決策時點前任意 TF 數值與變化、反例多種全標 0＋種類欄選填；**U4b** 標籤基準＝t₀ close、close-to-close；**U5** 規模只是舉例、統計不寫死規模（樣本不足走 tier 降級、標不可算）；**U6** 事件產生器完整版列入開發、落點 `/search` 升級；**U7** 現有頁面升級不翻掉；**U8** LightGBM/XGBoost 之選不影響設計、之後再議；**U10** 前端落點＝產/匯入在 `/search`＋`/data-preparation`、分析在 `/ic-analysis` 加事件模式；**U11** 全部 K 線驗證一次建完整；**U12** 多標的＝常態必要；**U13** 一份 SPEC＋B1–B5＝Phase、每批三家 review＋戳記才進下批。
- `2026-08-17 使用者裁定（成熟度地圖）`：僅 Feature Factory 完整、IC 進行中；ML/回測/Optimization 不完整層，其內部結構不得作為設計依據；**禁改 `xgboost_batch_service` 訓練殼；不碰回測層**。
- `2026-08-05 使用者裁定（面向未來不溯及既往）`：舊 `cases.json` 不遷移；legacy 匯入路徑顯式 migration 或拒絕、禁 silent coerce（R1 C2-1）。
- `2026-08-20 委員 R2 verdict`：可進 decision-gated SPEC 起草；U 系列無一技術不可行；J1–J10 無一推翻。

## §C 約束

- 解耦 7 條相關項：R1 `momentum/` 不 import `api/`（新模組全在 `momentum/Analysis/event_samples/`＋`momentum/FeatureEngineering/operators/`）；R3 服務經 factories（B5 才觸及）；R5 config 單一來源（新設定入既有 config schema，禁散落常數）；R6 `pytest tests/momentum/` 獨立跑；R7 DTO 不跨界（事件契約 dataclass 住 `momentum/`，`api/models/` 只做 request/response 殼）。
- 不可違反原則：不弱化 NaN/inf gate（對齊失敗＝loud 枚舉，禁 fillna/跳過）；資料真實性（§G 用真實 kline；統計 oracle 可用合成**因子/label 序列**——`docs/TEST_DESIGN_CHARTER.md` §F 允許，禁合成價格）；不擅改輸出大小（IC 主線既有報告鍵集不變，只新增）。
- **成熟度約束**：`api/services/xgboost_*`、`momentum/Optimization/`、回測層内部**不得作為設計依據**；kline 層「可能變更」⇒ 事件契約只綁 `symbol/timeframe/bar 邊界/時區/snapshot digest`，**不綁 HDF5 佈局**（R1 C6-3）。
- **R5 A′ 語意原樣保留**（R1 C4；ROADMAP 要求）：條件 IC fallback 時 `event_timestamps` 透傳＋one-shot guard 不動；fallback ⇒ `fallback_requested_scope`＋`degraded` 標示，禁把事件丟掉。
- **新資料結構一律 JSON SoT**（範本鐵律；出生事故 P1-6）：所有新欄位名/枚舉值/reason 字面**只**在 Task B1.0 之 `momentum/Analysis/contracts/event_import_contract.json` 出現一次（survivor 擴欄住 `ic_survivor_contract.json` v2）；本 SPEC 其餘章節與 TODO 只 pointer，不複列欄位表。
- **允許改動之既有檔白名單（唯此；新建檔見各 Task）**：
  1. `momentum/Analysis/contracts/ic_survivor_contract.json`＋`survivor_contract.py`：**只在 Task B2.4** version 1→2 擴 event object，同步 validator/consumer/golden。
  2. `momentum/Analysis/ic_filter_orchestrator.py`：**只在 Task B2.3** 接事件樣本條件 IC（沿既有 `event_timestamps` 入口；不改既有 stage 語意與既有報告鍵）。
  3. `momentum/Analysis/event_filter.py`：**只在 Task B3.2** 掛 adapter（既有遮罩語意不變）。
  4. `momentum/FeatureEngineering/operators/`＋`operator_registry`：**只在 Task B3.3** 新增 state-counter 算子註冊（既有算子不動）。
  5. `api/models/`＋`api/routes/`＋`api/services/`（case/search/ic 路徑）與 `frontend/src/`：**只在 B5**；`/case/import` 舊路徑＝legacy adapter（顯式 migration 或拒絕）。
  6. 對應既有測試檔：只新增斷言，禁放寬。
  **不改**：`xgboost_batch_service` 訓練殼、`label_generator.py`、`SplitPlan`（`momentum/core/contracts.py`；事件層另建 manifest，不動 row identity 契約）、回測層、`pattern_extractor` 既有簽名（B4 只新增消費側）。

## §G Golden / Baseline

- **feature/kline 條件**：涉事件對齊/特徵取列/全 K 線驗證 ⇒ **必用真實 kline `data_cache/feature_klines/kline_cache.h5`**（禁合成 fixture 充當價格）；統計類 oracle（置亂、AUC 邊界）可用合成因子/label **序列**（章程 §F）。
- **凍結時機 / reference 設定**：Task B2.3 動工前（首次觸碰 IC 主線檔），以既有 ICHC golden 流程（`tests/momentum/helpers/ichc_run.run_analyze()`＋`tests/golden/la0/inputs/` 真實 kline 衍生 fixture）跑預設 config，凍結 baseline canonical **sha256** 於 `handoffs/run_receipts/gap3_golden_pre.json`（路徑寫死；scrub 規格沿 GAP-2 `gap2_freeze_golden.py` 手法，TODO 階段列細目；檔內附 fixture sha256＋config_hash）。
- **baseline 內容（四類）**：
  1. **行為不變型（序列型主線）**：B2.3/B2.4/B3.2 各接線後，同 fixture 同 config 之序列型報告 canonical **sha256 與 pre 檔 exact 相等**（事件欄位全不觸發時）；`summary_table` 逐 feature 逐鍵 `abs≤atol=1e-12`；任何差異列鍵＋diff＝FAIL。
  2. **對齊 golden（真實 kline 手算對照）**：自真實 kline 取 ≥3 個 t₀（12h UTC 整點、非整點邊界、資料末端），對 1h/4h/12h 各 TF **手算** `feature_cutoff[tf]`（`max{close_ms ≤ decision_at}`）與六時間欄，斷言 receipt 逐欄 **整數 ms exact（==，容差 0）**；含 `decision_offset_bars=0`、`k>0`、`entry_price_semantic=next_open` 三形 exact receipt oracle（R1 X1／R2 Y1，含 `entry_at_ms`＋`entry_price_source` 欄）；資料末端案例預期 `label_window_incomplete` 拒絕。
  3. **自檢 oracle**：(i) label 置亂（固定 seed）⇒ 二元辨別/條件 IC 全部落 chance-level CI 內（門檻以 CI 表述、不寫死數字）；(ii) PIT 後移 oracle：`feature_cutoff` 人為後移一根 ⇒ validator **必 raise**；(iii) ms 單位閘：秒級 timestamp 宣告 ms ⇒ 拒絕。
  4. **契約 oracle**：匯入檔過 `validate_event_import()` fail-closed（缺必填鍵/多未知鍵/枚舉外值/二元任務缺一類別 `missing_control_group`/digest 篡改 ⇒ 拒）；survivor v2 檔過升版後 validator。
- **通過條件（可證偽，容差分尺度）**：1 sha256 exact＋`atol=1e-12`；2 ms 整數 `==`；3 (i) CI 判定（固定 seed，重跑 sha256 相等） (ii)(iii) rc!=0；4 fail-closed 逐條。報酬/統計類浮點對照 `abs≤atol=1e-12 或 rel≤rtol=1e-9`（float64；float32 放寬 `rtol=1e-6`）。超出即列出項目＋實際 diff＝FAIL。

## §P Phase 與依賴（分批＝K10/C9；每批三家 code review＋三家戳記才進下批＝U13）

> 批次原則（C9）：每批可讀輸出＋golden/negative oracle＋依賴欄；B1 失敗不得靠後批占位或全票 UAT 遮蔽。B1 先能驗證資料正確 → B2 能看統計與實盤 estimand（C4＝整票靈魂故 K8 在 B2）→ B3 降低手工（產生器；AR-5）→ B4 找 pattern → B5 上 UI。

### Phase B1 — 匯入契約＋PIT 對齊＋樣本 manifest＋切分＋特徵物化＋自檢 oracle（依賴：無；批內順序 B1.0 → B1.1 → B1.2 → B1.3 → B1.6 → B1.4 → B1.5）

**Task B1.0 — 事件匯入契約 JSON SoT＋validator**
- 目標：所有事件欄位名/枚舉值/reason 字面只在一個檔出現；匯入 fail-closed。
- 檔案：新增 `momentum/Analysis/contracts/event_import_contract.json`＋`momentum/Analysis/event_samples/import_contract.py::load_event_import_contract()／validate_event_import()`（純函式）。
- 既有 caller/影響面：新建無 caller；`CaseRecord`／`/case/import` 不動（B5 才接 legacy adapter）。
- 改法（欄位**唯一列舉處**＝契約檔；下為規格要求，非複列）：
  - 必填：`event_id`、`symbol`、`timeframe`（錨定 TF）、`t0`（epoch ms UTC；事件錨點＝觸發根 open_time）、`decision_offset_bars`（int ≥0，預設 0；R1 X1＝AR-1 定形，語意見 D2-2）、`entry_price_semantic`（**頂層**，值集見 D1-1；R1 X11）、`direction ∈ {long, short}`（U1：一次只研究一向，匯入批內單值）、`scenario`（A/B 預測型／C 確認型／兩段式；D2 分路徑鍵）、`label ∈ {0,1}`、`label_definition{rule_id, canonical_digest, window, label_return_mode(預設 close_to_close)}`（D1；**不含** entry 語意——R1 X11）、`control_kind`（R1 C2 四值入 schema 閉集；validator accepted＝`{user_labeled_same_trigger, user_labeled_other, platform_same_trigger_rule}`、`platform_random_bars` 恆拒 reason=`not_implemented_platform_random_bars`（§N-7 解除前）——R2 Y6；**B1 批只有 `user_labeled_*` 生產者**，`platform_same_trigger_rule` 自 B3.2 起由產生器產出、過**同一** validator（無 profile 分裂）；二元任務缺類別 ⇒ `missing_control_group`）、`source_file_digest`、`data_snapshot_digest`。
  - 選填：`label_value`（連續；`conditional_ic` 之**條件必填**——D1-3）、`counterexample_kind`（a/b/c）＋`kind_source ∈ {user, platform_auto}`（R1 X4）、`search_rule_summary`（U2：當時搜尋條件）、taxonomy 正交欄（R1 C6：`event_source/observable_family/event_origin/event_shape/label_kind`）＋`event_type_tag` 自由標籤、`meta`。
  - **條件必填（R1 X5）**：事件宣告用到跨標的參照 ⇒ T8 `reference_symbols[]{symbol,timeframe,alignment_rule,snapshot_digest}` 全欄必填；`event_origin=model` ⇒ T9 `source_model{model_id,version,artifact_digest,split_plan_hash,feature_manifest_hash,available_at}` 全欄＋availability receipt 必填（`available_at ≤ decision_at` 否則 `research_only`/拒——R2 C7）；`event_shape=interval` ⇒ T10 `event_interval{start,end,endpoints_inclusive}`＋overlap identity 必填；不得以自由 `meta` 補洞。
  - **分類 config（R1 X4／R2 Y3）**：`counterexample_classifier_config`（門檻/單位/預設值之唯一列舉處）住本契約檔；分類定義＝direction-aware signed return、錨＝t₀ close（同 D1；公式見 Task B1.5）。匯入欄 `counterexample_kind` 值集＝`{a_trigger_no_follow, b_range, c_drop}`（僅使用者填；出現 `unclassifiable` ⇒ validator 拒）；分類器輸出為 **derived 欄** `counterexample_kind_effective ∈ {a_trigger_no_follow, b_range, c_drop, unclassifiable}`（住 manifest；兩值集皆字面入契約檔）；分層報表一律消費 derived 欄，`unclassifiable` 不進分層分母、單獨列 `n_unclassifiable`。
  - 衍生欄（對齊/組樣本寫入 receipt/manifest，**非匯入欄**）：六時間欄、`event_known_at_decision`、`dedupe_cluster_id`、`overlap_set_hash`、`uniqueness_weight`、`time_cluster_id`、`cluster_weight`。
  - v1 不重算使用者 label（一致性探針＝AR-6）；hash 相同不證內容正確（誠實邊界入 `_doc`）。
- **驗證**：`pytest tests/momentum/event_samples/test_import_contract.py -q` rc=0；斷言①頂層鍵集 `==` 契約列舉②枚舉值閉集③缺必填/多未知鍵/枚舉外值 ⇒ `ContractValidationError`④二元任務單類別 ⇒ `missing_control_group`⑤ ms 量級閘（`t0 < 10^12` 宣告 ms ⇒ 拒）。
- **邊界**：①空 CSV/空列表 ⇒ loud 拒②重複 `event_id` ⇒ 拒③`label_value` 與 `label` 矛盾（值缺失容許、型別錯拒）④T9 `available_at > decision_at` ⇒ `research_only`/拒。
- **存活至**：全票完工後保留；未來事件型所有匯入之唯一契約。
- **覆蓋風險**：無（B2.4 只動 survivor 契約，不動本檔；AR-1/AR-2 定形寫入本檔一次）。
- 不可做：不得在 SPEC/TODO/程式註解複列鍵表；不得沿用/擴充 `CaseRecord` 充當契約；不得實作 `platform_*` 抽樣。

**Task B1.1 — PIT 對齊純函式＋per-TF 收據**
- 目標：D2 全落地——六時間欄推導、per-TF feature_cutoff、失敗枚舉 loud。
- 檔案：新增 `momentum/Analysis/event_samples/alignment.py::align_events(events, bars_by_tf, config) -> (receipts, failures)`（純函式；吃已載入之 bar 表，不讀 HDF5——kline 隔離）。
- 既有 caller/影響面：新建無 caller；B1.4/B2 消費 receipts。
- 改法：逐事件逐 TF 推導收據列；不變式 violate ⇒ 該事件入 `failures` 帶 reason（D2-4 枚舉）；輸出 `n_dropped_by_reason` 摘要；**無任何 silent skip 分支**。
- **驗證**：`pytest tests/momentum/event_samples/test_alignment.py -q` rc=0（含 §G-2 真實 kline 手算對照）；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_alignment.py -q WHEN mutation=cutoff_shift_one_bar THEN rc!=0`。
- **邊界**：①t₀ 在資料末端（答案窗未完）⇒ `label_window_incomplete`②缺 bar/亂序/重複 bar ⇒ 各對應枚舉③`decision_at` 早於資料起點 ⇒ `warmup_insufficient_<tf>`④非整點 TF 邊界 ⇒ as-of 取列非報錯。
- **存活至**：全票完工後保留；B2 三表與全 K 線驗證之對齊底座。
- **覆蓋風險**：無。
- 不可做：不得用「時間戳剛好相等」對齊；不得對失敗事件 `continue` 不記帳；不得在本函式內算特徵。

**Task B1.2 — 去重/簇/唯一性權重 manifest（K3/C5）**
- 目標：連續觸發與重疊答案窗變成可重現的事件 manifest。
- 檔案：新增 `momentum/Analysis/event_samples/dedupe.py::build_event_manifest(receipts, policy_config) -> manifest`。
- 既有 caller/影響面：新建無 caller；B1.3/B2 消費。
- 改法：manifest 每事件 `observation_interval/label_start/label_end/dedupe_cluster_id/overlap_set_hash/uniqueness_weight`；`cluster_gap` 以 **UTC duration**（預設＝答案窗 duration）非 row count；跨 symbol 同時刻與 interval overlap 一併 union；primary policy **事前固定依情境**：C＝`cluster_first`、A/B＝`all_with_uniqueness`（`w_i=1/overlap_count` 於 label 窗）；A/B 全留之顯著性**必**配 cluster-robust/bootstrap，無修正 raw-all 禁出；另一 policy＝**預先登記之敏感度**，報告 `sensitivity_flip: bool`；報 `n_events_raw/n_events_effective/overlap_fraction`。
- **驗證**：`pytest tests/momentum/event_samples/test_dedupe.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q WHEN scenario=C policy=primary THEN rc=0`（斷言簇首代表＝interval 最早）；權重和/簇計數對手算小例 exact。
- **邊界**：①單事件（無重疊）⇒ weight=1、自成簇②全部同刻（極端簇）⇒ effective n=1 級③缺 interval ⇒ fail-closed（R2 C5）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無（B4 之 GBDT 權重消費列 §N 殘留，不回頭改本 manifest）。
- 不可做：權重不進 ML 訓練（`UNWIRED_MODULES` 含 `sample_weight`；§N-4）；不得以 row count 當 gap 單位；不得把兩種 policy 都當 confirmatory。

**Task B1.3 — per-symbol 時間切分＋interval-aware purge＋跨標的 time-cluster（K4/C6；U12 多標的必要）**
- 目標：多標的合併樣本的切分與統計單位正確。
- 檔案：新增 `momentum/Analysis/event_samples/event_split.py::split_events(manifest, split_config) -> event_split_plan`。
- 既有 caller/影響面：新建無 caller；**不改 `SplitPlan`**（row identity 契約另軌；事件層自帶 interval purge）。
- 改法：每標的各自按時間切＋緩衝 ≥ 答案窗；事件 interval 跨界 ⇒ purge；`time_cluster_id=floor(decision_at_ms/bucket)`（bucket 預設＝觸發 TF 一根）＋`cluster_weight = 1/n_events_in_time_cluster`（primary；R1 X9 裁定＝R2 C6 群集正文收斂值，附錄單家 `1/sqrt` 提案不採；bootstrap over clusters＝敏感度；字面唯一入契約檔）；統計 primary＝macro（symbol 等權）、micro（event 等權）＝敏感度；報 `n_symbols/per-symbol n/n_time_clusters/avg_cluster_size`；未做 cluster 調整 ⇒ `degraded`；跨 symbol 泛化宣稱須 LOSO/held-out-symbol receipt；test 段事件數 < tier 下限 ⇒ loud `insufficient_events_in_test`，**不**回退全樣本（R1 C3-3）。
- **驗證**：`pytest tests/momentum/event_samples/test_event_split.py -q` rc=0；斷言①跨界事件被 purge（手造小例 exact）②禁 positional index（斷言 split 依 ms 時間非列號）③macro/micro 兩統計皆輸出且標示④手算小例：同 time_cluster 權重和＝1（`atol=1e-12`；R1 X9）。
- **邊界**：①單 symbol ⇒ 退化為單標的切、macro==micro②某 symbol 事件全在 train ⇒ 該 symbol 不進 test 統計並報欄③同刻全 symbol 觸發 ⇒ cluster n=1。
- **存活至**：全票完工後保留；#4 開票時之可複用原語（AR-3）。
- **覆蓋風險**：無。
- 不可做：不重建 cross-sectional IC、不做 random-effects/GEE、不宣稱關閉 registry #4（§N-5）。

**Task B1.4 — 單特徵二元 baseline＋自檢 oracle 載體（R1 C5-2）**
- 目標：B1 有統計載體可掛 label 置亂與 PIT 後移 oracle（oracle 需要載體＝R1 採 codex 版之理由）。
- 檔案：新增 `momentum/Analysis/event_samples/baseline.py::single_feature_binary_baseline(features_at_decision, labels, event_split_plan) -> report`。
- 輸入來源：`features_at_decision`＝**Task B1.6 產出**（含 `feature_manifest_hash`；R1 X7）；`event_split_plan`＝B1.3。
- 既有 caller/影響面：新建無 caller。
- 改法：對每特徵單獨算 OOS AUC/PR-AUC（test 段 only）＋BH-FDR；chance-level oracle＝**permutation quantile**（R2 Y5／R3 Z4 防退化）：固定 seed、`N_perm=1000`，per `statistic_kind` 以置亂分布 `[q_{0.025}, q_{0.975}]` 為帶（AUC null 中心 0.5、PR-AUC null 中心＝prevalence、IC null 中心 0，皆由置亂分布自然給出）；**三道硬檢**——(i) 分布非退化：`variance > 0` 且 `n_unique_perm_stats > 1`，否則 oracle 自身 FAIL；(ii) 斷言至少一排列 ≠ identity（seed＋排列 digest 寫 receipt）；(iii) 帶判定用經驗分位；輸出掛 `statistic_kind=binary_discrimination`。
- **驗證**：`pytest tests/momentum/event_samples/test_baseline_oracle.py -q` rc=0；label 置亂（固定 seed）⇒ 全特徵落 CI 內；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_baseline_oracle.py -q WHEN mutation=pit_shift THEN rc!=0`。
- **邊界**：①one-class（test 段單類）⇒ `capability_status=unavailable`②特徵全 NaN ⇒ loud 拒。
- **存活至**：B2 三表落地後降級為自檢工具（保留不刪）。
- **覆蓋風險**：B2.2 之辨別表為其超集——不刪本 task 產出（oracle 載體長期保留），故無覆蓋。
- 不可做：不做多特徵組合（B4）；不接 DSR/PBO（AUC 禁直接餵——R2 C7）。

**Task B1.5 — 反例自動分類（U4；AR-2 定形後實作）**
- 目標：`counterexample_kind` 缺值時平台依 t₀ 走勢自動分類 a/b/c，門檻可調。
- 檔案：新增 `momentum/Analysis/event_samples/counterexample_classifier.py`（純函式）。
- 既有 caller/影響面：新建無 caller；B2 分層報表消費。
- 改法（R1 X4＝AR-2 定形；R2 Y2 公式寫死）：`dir∈{+1(long),−1(short)}`；`R0 = dir·(close_t0−open_t0)/open_t0`（t₀ 自身走勢）、`Rw = dir·(close_labelEnd−close_t0)/close_t0`（答案窗走勢；錨＝t₀ close 同 D1；aggregation＝label window 末 close）。分類（僅 `label=0`、`counterexample_kind` 缺值時執行）：**a**＝`R0 ≥ trigger_threshold ∧ Rw ≤ follow_threshold`；**b**＝`|R0| ≤ range_threshold`；**c**＝`R0 ≤ −drop_threshold`。預設（可調；字面唯一住 `counterexample_classifier_config`）：`trigger_threshold=0.05`、`follow_threshold=0.0`、`range_threshold=0.01`（三者源＝使用者 §2-4 原文：漲≥5%／續漲分界／上下 1%）；**`drop_threshold` 無預設（`default=null`）**——使用者原文只寫「跌 x%」、x 從未裁定（R3 Z2）：未設 ⇒ c 類判定**不啟用**、僅由 a/b 與 `unclassifiable` 覆蓋（fail-closed 不發明數字）；x 值**列入白話閘問題**請使用者裁，裁後寫入契約 default。輸出 derived 欄 `counterexample_kind_effective`＋`kind_source=platform_auto`；使用者已標 ⇒ 不重算不回寫（`kind_source=user`）；user/platform 衝突 ⇒ 保留 user＋報告附 `platform_suggested_kind` 留痕；**同時滿足多條 ⇒ `unclassifiable`（不猜）**。
- **驗證**：`pytest tests/momentum/event_samples/test_counterexample_classifier.py -q` rc=0（手造三類小例 exact；boundary fixtures：每門檻取 `=`、`+1e-9`、`−1e-9` 三點落位 exact——R2 Y2；conflict case 斷言主鍵保留＋`platform_suggested_kind` 出現；多類邊界 ⇒ `unclassifiable`）。
- **邊界**：①走勢同時滿足多類 ⇒ `unclassifiable`（不進分層分母）②答案窗不完整 ⇒ `unclassifiable` 非亂填③user 有標且 platform 建議不同 ⇒ 主鍵不變、留痕欄出現。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不回寫使用者手標欄；不把自動分類當 label（它只是報表分層鍵）。

**Task B1.6 — 特徵物化與決策列選取（R1 X7 新增；批內順序在 B1.3 之後、B1.4 之前）**
- 目標：把 J3「全部 K 線連續算特徵、每案例取決策時點那一列」落成有契約的資料路徑，杜絕「每案例固定窗」誤實作。
- 檔案：新增 `momentum/Analysis/event_samples/feature_materialization.py::materialize_features_at_decision(receipts, bars_by_tf, feature_config) -> (features_at_decision, feature_manifest_hash)`（純函式；呼叫既有 Feature Factory，不重實作特徵）。
- 既有 caller/影響面：B1.4/B2/B4 之特徵輸入唯一來源；Feature Factory 本體不改。
- 改法：連續 per-TF 物化（全歷史或 ≥ 最長 lookback＋warmup 之段——結果須與全史算一致，§3.4 已證）→ 對每事件以 `decision_at` per-TF as-of 取列（規則同 D2-1）→ 輸出事件×特徵表＋`feature_manifest_hash`（特徵名集＋config digest）；per-TF warmup 不足 ⇒ NaN 前綴入對齊失敗枚舉 `warmup_insufficient_<tf>`；NaN 語意不填 0。
- **驗證**：`pytest tests/momentum/event_samples/test_feature_materialization.py -q` rc=0；①真實 kline 上「足長段物化」vs「全史物化」取同事件列逐值 `atol=1e-12` 一致②因果 invariant：截斷 `decision_at` 之後的資料重算，事件列逐值不變（exact）③`feature_manifest_hash` 決定性（同 config 重跑 sha256 相等）。
- **邊界**：①事件 `decision_at` 早於 warmup 完成點 ⇒ 該事件入失敗清單非 NaN 混入②多 TF 特徵欄名衝突 ⇒ loud 拒。
- **存活至**：全票完工後保留；B2/B4 特徵路徑底座。
- **覆蓋風險**：無。
- 不可做：不切「每案例固定 N 根」窗當訓練單位；不在本函式內做特徵選擇；不引入 `shift(-n)` 未來欄。

### Phase B2 — 三張表＋survivor 契約升版＋全部 K 線驗證（依賴：B1）

> **B2 全批共同約束（R1 X6＝AR-3 落地）**：B2.1/B2.2/B2.3/B2.5（及 B4.1）之**必需輸入**＝B1.3 `event_split_plan`＋cluster manifest；每張表/報告必列 macro primary、micro sensitivity、raw/effective n、cluster CI、`degraded`（含 `degraded:single_symbol`）、LOSO/held-out status；未 cluster 調整 ⇒ **禁 formal pooled inference**。各 Task 驗證含此共同約束斷言。

**Task B2.1 — 事件後報酬表（K5/C7-i；finlab 型；U1）**
- 目標：事件後多 horizon 報酬分布表；不需反例。
- 檔案：新增 `momentum/Analysis/event_samples/tables.py::event_forward_return_table(...)`。
- 既有 caller/影響面：新建無 caller。
- 改法：signed `(exit_h−entry)/entry`（entry＝D1-6 映射表唯一定義；D1-4 兩數並排）；多 horizon（config 化，不寫死 5/10/20/45）；平均/中位/勝率/樣本數；按 direction/scenario/symbol/time/cluster 分層；CI 用 cluster bootstrap/HAC；`statistic_kind=event_return`。
- **驗證**：`pytest tests/momentum/event_samples/test_tables.py -q -k forward_return` rc=0（手造小例 exact；CI 固定 seed 決定性）。
- **邊界**：①horizon 超出資料 ⇒ 該格 `n` 反映排除、不灌 0②單事件 ⇒ CI `unavailable`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不合併三表為總分（禁單一數字混報——R2 C7）。

**Task B2.2 — 正反例辨別表（K5/C7-ii）**
- 目標：0/1 分得開嗎——OOS only、按反例種類與兩段式腿分層。
- 檔案：`tables.py::binary_discrimination_table(...)`（擴 B1.4 baseline 為正式表）。
- 既有 caller/影響面：B1.4 baseline（共用計算核心）。
- 改法：只用 OOS score；AUC/PR-AUC/rank-biserial/prevalence/threshold/confusion/lift；按 **`counterexample_kind_effective`（derived 欄——R2 Y3）** a/b/c 與兩段式腿分層（三種反例＝兩段式合體——J4/S3.5；`unclassifiable` 不進分層分母、列 `n_unclassifiable`）；one-class ⇒ `unavailable`；`statistic_kind=binary_discrimination`。
- **驗證**：`pytest tests/momentum/event_samples/test_tables.py -q -k discrimination` rc=0；label 置亂 oracle 沿 B1.4。
- **邊界**：①某 kind 層樣本 0 ⇒ 該層 `unavailable` 非空表②分層後 one-class 同上。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無（B1.4 不被刪，見其欄）。
- 不可做：AUC 不餵 DSR/PBO；不報 in-sample 分數。

**Task B2.3 — 條件 IC 接線（K5/C7-iii；J7/S3.9；R5 A′ 保留）**
- 目標：事件子樣本上跑既有 IC 全流程；label 用連續 `label_value`。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py`（白名單 §C-2；沿既有 `event_timestamps` 入口）＋`event_samples/` 之餵入層。
- 既有 caller/影響面：IC 三入口（`analyze`/`refilter`/`analyze_full`）；**既有 stage 語意與報告鍵不變**（§G-1 golden 看住）。
- 改法：條件 IC 只吃連續 `label_value`（D1-3；y=0/1 **不**當 return IC——R1 C5-1）；沿 stage3/4/5＋A′ fallback 透傳＋one-shot guard 原樣；`statistic_kind=conditional_ic`；`sample_scope.kind=event`。
- **驗證**：`pytest tests/momentum/ -q -k "gap3 and conditional_ic"` rc=0；§G-1 行為不變 golden exact；A′ fallback 案例斷言 `event_timestamps` 透傳＋`degraded` 標示。
- **邊界**：①事件數 < tier 下限 ⇒ 既有 tier 降級語意（U5）②`label_value` 缺 ⇒ `unavailable:missing_label_value`（D1-3；**不重算**）③t₀−k 手算案例：label 錨不隨 decision 移動（D1-5）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 stage3/4/5 內部；不把 mismatch 語意的主線 `return_N` 靜默當事件 label（D1-3）。

**Task B2.4 — `ic_survivor_contract` v2 升版（R1 C4）**
- 目標：事件型倖存者可被下游安全消費。
- 檔案：`ic_survivor_contract.json`（version 1→2）＋`survivor_contract.py` validator/consumer 同步＋golden 同步。
- 既有 caller/影響面：GAP-2b 契約消費側（現唯讀）；`additional_properties:false` ⇒ **先升版再寫 payload**。
- 改法：event object 擴 `event_manifest_hash/label_definition_hash/decision_time_rule/feature_cutoff_rule/label_window_rule/control_kind`（字面唯一住契約檔）；`fallback_requested_scope`＋`degraded` 保留。
- **驗證**：`pytest tests/momentum/Analysis/test_survivor_contract.py -q` rc=0（v2 鍵集斷言；v1 檔案讀入之相容/拒絕行為斷言）。
- **邊界**：①v1 舊檔 ⇒ 顯式版本判別（讀舊版或拒，禁 silent coerce）②新欄缺 ⇒ 拒。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不動 GAP-2 既有 v1 欄語意；不在 SPEC/程式複列鍵表。

**Task B2.5 — 全部 K 線驗證 evaluator（K8/C4＝D4 全落地；U11 一次建完整）**
- 目標：整票靈魂的機器形——固定分母＋基率並排＋lift。
- 檔案：新增 `momentum/Analysis/event_samples/all_bars_eval.py::evaluate_all_bars(model_scores_or_rule, bars, manifest_config) -> report`。
- 既有 caller/影響面：新建無 caller；B4 消費（評 ML 訊號）；B3 產生器共用標籤重算（G6）。
- 改法：D4 全文為規格；evaluation manifest 落檔可審計；與序列型全 bar IC 並排（J7-4）。
- **驗證**：`pytest tests/momentum/event_samples/test_all_bars_eval.py -q` rc=0；真實 kline 小段手算分母 exact；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_all_bars_eval.py -q WHEN mutation=ineligible_in_denominator THEN rc!=0`；缺基率欄 ⇒ `unavailable:missing_prevalence_disclosure`。
- **邊界**：①資料末端 bars ⇒ `n_tail_excluded` 記帳②多組條件同時命中 ⇒ `event_id/label_id` 保留多標籤或契約明定 precedence，禁默默覆蓋（R2 C4 引 codex P0-03）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：D4-4 不做清單（倉位/費用/複利/資金曲線/turnover/capacity/triple-barrier/long-short）。

### Phase B3 — 完整版事件產生器＋變化類特徵（依賴：**B1＋B2.5**（G6 呼叫 all-bars evaluator——R1 X10）；AR-5 已裁維持本批）

**Task B3.1 — 條件引擎純函式（K9/C3＝D3 全落地）**
- 目標：typed AST＋欄位角色＋digest 的事件產生核心。
- 檔案：新增 `momentum/Analysis/event_samples/condition_engine.py`。
- 既有 caller/影響面：新建無 caller；B3.2 adapter 消費。
- 改法：D3 全文為規格；safe-subset（已註冊欄位、比較/布林/區間/缺值運算）；輸出 canonical digest、角色清單、max lookback；多組 label ⇒ `label_id` manifest；去重在產生期（G4）；輸出過 B1.0 validator（G5）。
- **驗證**：`pytest tests/momentum/event_samples/test_condition_engine.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_condition_engine.py -q WHEN expression_role=feature column=future_return THEN rc!=0`（future 欄進 feature 必拒）。
- **邊界**：①未註冊欄位 ⇒ 拒②表達式空/恆真 ⇒ loud③digest 決定性（同式異白排序 ⇒ 同 digest）。
- **存活至**：全票完工後保留；IC 事件遮罩之長期底層（J10）。
- **覆蓋風險**：無。
- 不可做：不得以 `df.eval` 任意字串為核心；不得讓 `selection_predicate` 欄流入特徵表（D3-4）。

**Task B3.2 — `/search` 與 `event_filter` adapter（U6/G1–G6；U7 升級不翻掉）**
- 目標：產生器能力全開（任意 FF 特徵＋t₀ 結果＋未來結果欄觸發；多組 label 一次設定；方向/情境/答案窗/規則摘要自動存；一鍵產合規事件檔；同引擎做全 K 線標籤重算）。
- 檔案：`momentum/Analysis/event_filter.py`（掛 adapter；遮罩語意不變）；`/search` 後端 adapter 於 B5 接 API（本批先 `momentum/` 層）。
- 既有 caller/影響面：IC 事件遮罩既有 caller（§G-1 看住）；`allowed_filtering_params` 契約化（D3-3）。
- 改法：兩殼皆薄 adapter；G6＝**呼叫 B2.5 `evaluate_all_bars`，禁平行實作**（R1 X10）；產生器多組 label 產同觸發控制組——`control_kind=platform_same_trigger_rule` 於本 Task 啟用（R1 X13）；產出直接過 B1.0 validator。
- **驗證**：`pytest tests/momentum/event_samples/test_generator_adapters.py -q` rc=0，G1–G6 逐項斷言（R1 X12）：G1 任意 FF 特徵＋t₀ 結果＋未來結果欄觸發（十類中 ①②③⑩ 代表案例各一）；G2 多組 label 一次設定（`label_id` manifest）；G3 方向/情境/答案窗/規則摘要自動存；G4 去重回報原始/去重後數；G5 一鍵合規檔（輸出過 B1.0 validator）；G6 呼叫 B2.5 之整合測試（禁平行實作）；另 `platform_same_trigger_rule` 控制組產出過 validator＋`control_kind` 正確標記（R1 X13）。
- **邊界**：①條件命中 0 事件 ⇒ loud 空結果非錯②既有 `event_filter` query 路徑行為不變斷言。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：未過角色隔離 receipt 前不宣稱共用完整引擎（D3-3）；不動 `/search` 前端（B5）。

**Task B3.3 — 變化類特徵算子（K7/C8）**
- 目標：補 `bars_since_cross/consecutive_run/bars_since_threshold/window_max_ratio/cross_count`；已有算子不重做。
- 檔案：新增 `momentum/FeatureEngineering/operators/state_counters.py`（落點寫死，不擴 `derived_operators`——R1 X7）＋`operator_registry` 註冊。
- 既有 caller/影響面：Feature Factory pipeline；既有 `ts_argmax/ts_argmin/slope` 等**不動**。
- 改法：每算子只看 `[t−lookback+1, t]`、輸出 `max_lookback/warmup/as-of` 中繼資料；NaN 語意明定不填 0；過 Feature Factory 因果/golden 紀律（三方數據正確性簽核鐵律適用）。
- **驗證**：`pytest tests/momentum/feature_engineering/ -q -k state_counters` rc=0（手算小例 exact；因果測試：截斷未來資料結果不變）。
- **邊界**：①窗內無交叉 ⇒ NaN 或哨兵值（契約定，非 0）②warmup 不足 ⇒ NaN 前綴。
- **存活至**：全票完工後保留（Feature Factory 永久算子）。
- **覆蓋風險**：無。
- 不可做：不重做已存在算子；不引入跨列未來資訊（`shift(-n)` 禁）。

### Phase B4 — pattern＋DSR/PBO 橋（依賴：B2、B3）

> K6（DSR/PBO）落批以 R2 **C9 為準（B4）**，覆寫 C7 正文之 B3 批號（R1 X12）。

**Task B4.1 — pattern 抽取（J8：IC 篩 → ML 組合）**
- 目標：在學習段找多特徵組合 pattern；ML 殼不動。
- 檔案：`momentum/Analysis/` 既有 `pattern_extractor`／GBDT 分析器之消費側新函式（`event_samples/pattern_bridge.py`）；**禁改 `xgboost_batch_service` 訓練殼**。
- 既有 caller/影響面：吃 B1 manifest＋B2.4 survivor v2；`SplitPlan` train fail-closed（R1 C5-3）。
- 改法：訓練只在事件樣本 train 段；score 只在 test 段報；引擎 LightGBM/XGBoost 之選不影響契約（U8）；必需輸入含 B1.3 `event_split_plan`＋cluster manifest，報告列 macro/micro、`degraded`、LOSO status（R1 X6 共同約束）。
- **驗證**：`pytest tests/momentum/event_samples/test_pattern_bridge.py -q` rc=0（train/test 隔離斷言；置亂 oracle 沿用）。
- **邊界**：①特徵數 > 樣本可撐 ⇒ 依 IC 粗篩先行（J8）②test 段 one-class ⇒ `unavailable`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不動 ML 殼；`sample_weight` 不接訓練（§N-4）；不在全樣本 fit。

**Task B4.2 — 規則 → return series → candidate ledger → DSR/PBO（K6/C7；GAP-1 對接）**
- 目標：找到的規則/訊號以同 entry/exit 語意轉 OOS return series，接 GAP-1 DSR/PBO/MinBTL。
- 檔案：新增 `event_samples/candidate_ledger.py`；消費 `strategy_validation/pbo.py`／`min_btl.py`（不改其簽名）。
- 既有 caller/影響面：GAP-1 產物（唯讀消費）。
- 改法：每 candidate 記 provenance；`n_trials` **從 ledger 讀**，禁 request 任意填；AUC/PR-AUC/rank-biserial **不**直接餵 return-based DSR/PBO；每 oracle 記命令/seed/輸入 digest/預期 fail-pass。
- **驗證**：`pytest tests/momentum/event_samples/test_candidate_ledger.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q WHEN input_metric=auc target=dsr THEN rc!=0`。
- **邊界**：①ledger 空 ⇒ DSR/PBO `unavailable`②return series 長度不足 MinBTL 前提 ⇒ loud。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不為 AUC 自創 MinBTL 數字；不跳過 ledger 直餵。

### Phase B5 — 持久化/API/前端占位/UAT（依賴：B1–B4）

**Task B5.1 — API 接線＋legacy adapter**
- 目標：匯入新 schema 上線；舊路徑顯式處置。
- 檔案：`api/models/`＋`api/routes/case*`＋`api/services/case_import_service.py`（新 schema 沿 `case.py` 路徑）；批次抓 K 線概念保留（lookback＋forward＋warmup；多 TF 已支援）。
- 既有 caller/影響面：`/case/import` 舊格式 ⇒ legacy adapter（顯式 migration 提示或拒絕，禁 silent coerce）；舊 `cases.json` 不遷移。
- 改法：request/response 殼只透傳，驗證在 `momentum/` 純函式（R7）；factories 出口按 §RISK 末行。
- **驗證**：`pytest tests/api/ -q -k gap3_import` rc=0（新 schema 過、舊格式得顯式錯誤訊息、無靜默轉換）。
- **邊界**：①混合新舊欄 CSV ⇒ 拒＋指出缺欄②大檔（萬級事件）⇒ 分頁/串流不 OOM（實測記錄牆鐘——R1 C6-4 偵察待辦）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `xgboost_batch_service`；契約檢查單一真相源在 `momentum/` 純函式（`import_contract.py`），API 層不得重複實作同一套檢查。

**Task B5.2 — 前端（U10 落點；占位規則沿 `pendingFeatures` registry）**
- 目標：產/匯入在 `/search`＋`/data-preparation`；分析在 `/ic-analysis` 加事件模式；事件型獨有兩表只在事件模式顯示。
- 檔案：`frontend/src/`（三頁升級；不翻掉——U7）；「從已匯入案例選事件」入口（S3.9-5）。
- 既有 caller/影響面：`/ic-analysis` 既有圖表全共用（九成可用——J7）；vitest registry 防漂移沿既有機制。
- 改法：第一版報告/前端＝功能殼＋兩張新表；UAT 等整票（P10）。
- **驗證**：`cd frontend && npm run build` rc=0；vitest 對事件模式入口與兩表渲染之測試 rc=0。
- **邊界**：①未匯入任何事件 ⇒ 事件模式入口 empty state②後端 `unavailable` reason ⇒ 前端顯示原因非空白。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不另開分析頁（兩份殼——U10 理由）；前端不重算任何統計。

**Task B5.3 — UAT＋收尾**
- 目標：整票 UAT（含 GAP-1/GAP-2 前例之收尾件）：白話看板更新、殘留登記 registry、HANDOFF/ROADMAP 同步。
- 檔案：`白話說明/`＋`docs/IC_QUANT_GAP_REGISTRY.md`＋`HANDOFF.md`。
- 既有 caller/影響面：無程式面。
- 改法：UAT 腳本走真實流程（匯入 → 對齊 → 三表 → 全 K 線 → 報告）；殘留逐條入 registry。
- **驗證**：整票端到端 `pytest tests/momentum/event_samples/ -q` rc=0＋`cd frontend && npm run build` rc=0＋`bash scripts/plain_docs_sync_check.sh` rc=0；UAT checklist 檔逐項附實跑命令與 rc，使用者驗收簽字。
- **邊界**：UAT 發現缺陷 ⇒ 回對應批修，不在 B5 打補丁繞過。
- **存活至**：epic CLOSED。
- **覆蓋風險**：無。
- 不可做：不以 UAT 遮蔽 B1–B4 未驗收項（C9）。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a,d ⇒ 附可證偽/mutation 設計（引 `docs/TEST_DESIGN_CHARTER.md`）。最小 mutation 集（R1 X8＋R2 Y4 逐條可執行化）：**統一命令**＝`venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k M<n>`；**fixture 身分**＝M1/M2/M4/M9 用真實 kline `tests/golden/la0/inputs/` 既有 fixture＋固定事件表（seed 20260820）、M3/M5–M8/M10–M12 用合成事件表（seed 20260820＋M 序號；章程 §F 合法——合成的是事件/label 序列非價格）；fixture sha256 於首次建立記入 `handoffs/run_receipts/gap3_mutation_fixtures.json`（**誠實邊界**：SPEC 無法預寫尚不存在檔案之 digest——那是 receipt 非規格）；**TODO 逐字抄本表、不得增刪**。每條=「baseline 預期＋mutation diff＋預期 rc」：
  - M1 失敗記帳被吞：baseline＝`align_events` 對每個 dropped 事件寫 reason 入 `failures`；mutation＝drop 但不寫 reason（`n_dropped_by_reason` 總數 < 實際 drop 數）⇒ `test_alignment.py` 記帳守恆斷言（`n_input == n_receipts + n_failures`）紅，rc!=0。
  - M2 PIT 後移（跨 TF 可重現形）：mutation＝`feature_cutoff[tf]` 改選「`decision_at` 之後**下一實際 TF bar**」⇒ §G-3(ii) oracle（比對手算 receipt exact）紅，rc!=0。
  - M3 ms 單位閘移除：mutation＝刪量級檢查 ⇒ 秒級 `t0` 測資通過匯入 ⇒ `test_import_contract.py` 拒收斷言紅，rc!=0。
  - M4 分母竄改：mutation＝`evaluate_all_bars` 把 `label_window_incomplete` bars 計入 `n_eligible` ⇒ 真實 kline 小段手算分母 exact 斷言紅，rc!=0。
  - M5 權重歸一：mutation＝`cluster_weight` 全設 1（棄 `1/n_events_in_time_cluster`——X9 公式）⇒ B1.3 同簇權重和＝1（`atol=1e-12`）斷言紅，rc!=0。
  - M6 角色隔離移除：mutation＝condition_engine 允許 `future_*` 欄過 `feature` 角色 ⇒ B3.1 ASSERT（`WHEN expression_role=feature column=future_return THEN rc!=0`）反轉＝測試紅。
  - M7 基率欄移除 ⇒ B2.5 `unavailable:missing_prevalence_disclosure` 斷言紅，rc!=0。
  - M8 置亂 oracle 空心防護（R2 Y5／R3 Z4 定式）：baseline＝固定 seed 置亂 label 後，各 `statistic_kind` 觀測值落 **permutation quantile 帶**（B1.4 定式：`N_perm=1000`＋三道硬檢——非退化 `variance>0`／`n_unique>1`、非恆等斷言、經驗分位）；mutation＝把置亂改為恆等排列 ⇒ 非退化與非恆等硬檢**必觸發** ⇒ 紅，rc!=0（「觀測值∈觀測值」假綠路徑已封死）。
  - M9 offset 推導竄改：mutation＝`decision_at_ms` 推導 k 改 k−1 ⇒ §G-2 k>0 exact receipt oracle 紅，rc!=0（R1 X1）。
  - M10 分類猜測：mutation＝多類邊界從 `unclassifiable` 改取 precedence 猜一類 ⇒ B1.5 邊界案例斷言紅，rc!=0（R1 X4）。
  - M11 `degraded` 標記移除：mutation＝單 symbol 或未 cluster 調整時不標 `degraded` ⇒ B1.3/B2 共同約束斷言紅，rc!=0（R1 X6）。
  - M12 T9 availability 檢查移除：mutation＝`available_at > decision_at` 仍收 ⇒ B1.0 條件必填斷言紅，rc!=0（R1 X5）。
- **estimand 隔離**：`statistic_kind ∈ {event_return, binary_discrimination, conditional_ic}` 三值分節、禁合併總分；capability 枚舉沿 `ic_report_contract.json`（ref，不重定義）。
- 測試層級：單元（純函式手算小例）／整合（真實 kline 端到端 B1→B2）／Golden（§G 四類）／邊界（下勾選）。全部可 `pytest tests/momentum/...` 獨立跑，不需 `run_api.py`。
- **防假綠**：diff 既有測試斷言，不得放寬/刪除換綠燈；每批 review brief 附既有測試 diff。
- **邊界目錄**（勾選→Task）：空DF（B1.0/B1.1）／全NaN列（B1.1/B1.4）／Inf（對齊 `nan_or_inf_feature`）／重複·亂序 timestamp（B1.1 枚舉）／資料末端截斷（B1.1/B2.5）／單類別（B1.4/B2.2）／同刻極端簇（B1.2/B1.3）／萬級事件牆鐘（B5.1 實測記錄）。
- **偵察待辦**（R1 C6-4；TODO 階段補、不阻 SPEC）：外部源現有程式面、Feature Factory 多 TF as-of 工具現況、萬級事件 bootstrap 牆鐘、`two_stage_search` 欄位對照全表。

## §R 回退

- 每批（B1–B5）獨立 commit 序列，可按批 revert；批間依賴單向（B2 依 B1……），revert 後批不傷前批。
- IC 主線接線（B2.3/B3.2）＝加法式（事件欄位不觸發即原行為），§G-1 行為不變 golden 為回退判準：golden FAIL ⇒ 不 merge。
- 新功能驗證 PASS 後**預設 ON**（2026-07 使用者定：驗過不藏開關後面）；flag 只作逃生口。

## §N N/A 登記與殘留（三值理由；凍結時同步登記 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」，ROADMAP 只放 pointer）

**N/A 段**：本 SPEC 無任何被省略之必填段（全範本錨點皆已實填）。

**殘留（本票不做）**

1. **triple-barrier／出場最佳化** — `為何現在不做: user-ruling:2026-08-19 J5/U 系列（第一版＝時間出場；事件後報酬表回答「何時出」）＋blocked-by:回測層（成熟度地圖不完整層，出場最佳化必碰）`；觸發：使用者提出且回測層成熟；登記處：registry「GAP-3 殘留」。
2. **long-short 組合（同時多空兩籃子）** — `為何現在不做: user-ruling:2026-08-19 §4（一次只研究一向；組合建構屬另一層問題）`；觸發：使用者提出；登記處：同上。
3. **T4 衍生品/微結構、T6 新聞/鏈上事件型** — `為何現在不做: blocked-by:外部資料源未接入（K 線算不出）`；觸發：資料源 epic 落地（契約欄位已留——B1.0 taxonomy）；登記處：同上。
4. **uniqueness/cluster 權重接 GBDT `sample_weight` 訓練** — `為何現在不做: blocked-by:ML 殼 UNWIRED_MODULES 含 sample_weight（FACT-RECEIPT）＋成熟度地圖禁改訓練殼；B1 權重只進 manifest/統計有效 n（R2 C5）`；觸發：ML 殼允許接線閘開啟；登記處：同上。
5. **正式 panel IC（cross-sectional 重建、random-effects/GEE）** — `為何現在不做: blocked-by:registry #4 獨立票（本票只蓋可複用原語：per-symbol 切分＋合併統計＋time-cluster——AR-3 邊界確認）`；觸發：#4 開票；登記處：registry #4。
6. **金融 CAR/AAR event study、即時 NLP 事件** — `為何現在不做: user-ruling:2026-08-19（使用者重定義本票＝匯入標註樣本分析，非 event study；R1 C6 明列不支援）`；觸發：使用者提出新需求另開票；登記處：registry「GAP-3 殘留」。
7. **`platform_random_bars` 控制組自動抽樣** — `為何現在不做: needs-research:隨機 bar 控制組之 estimand 與抽樣契約未定義（R1 consult 已判「時間分離隨機反例」＝廢答案設計，禁隱式 fallback）`；觸發：委員會定出抽樣契約與 estimand；登記處：registry「GAP-3 殘留」。（R1 X13 拆分：`platform_same_trigger_rule` **不是殘留**——已收回為 Task B3.2 可驗收能力，循環 scope 解除。）
8. **label 一致性探針**（v1 不重算使用者 label）— `為何現在不做: needs-research:探針族（price_return_threshold 一族）之涵蓋範圍與誤報處置未定義（R1 X3＝AR-6 裁定維持殘留，2:1 多數＋較小 scope）`；觸發：使用者要求，或匯入資料品質事故；日後升級直接取 grok 設計＝探針比對匯入 `label_value` vs 契約重算 close_to_close、誤報 ⇒ 報告欄 `label_probe_mismatch` loud、不自動改 label；登記處：同上。配套硬規則已入 D1-3（缺 `label_value` ⇒ `unavailable:missing_label_value`，不重算補洞）。
