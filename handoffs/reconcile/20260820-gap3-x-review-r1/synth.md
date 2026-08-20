# Reconcile — 20260820-gap3-x-review-r1

**來源** 20260820-gap3-spec-r1-codex.md, 20260820-gap3-spec-r1-composer.md, 20260820-gap3-spec-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-20）

三家共 **15 條** findings（codex 8＝1 BLOCKING＋7 MAJOR／composer 2 MAJOR／grok 3 MAJOR＋2 MINOR），下列十三群集**引用全部 15 條，0 掉項**。
審查標的＝`docs/GAP3_EVENT_SPEC.md` @ e0af4a3d（#d0babfea8f24）。三家皆提交 §7.5 逐條對應表；**三家一致**：無整條取材遺漏、無 R1 C-情境反例／舊 `CaseRecord`／「換時間戳共用 IC」污染；U4b 對 R2 C1 預設之改寫被正確落地。
獨立性註記：composer 與 grok **彼此獨立**抓到 B3 依賴缺 B2.5 邊（X10）；composer 與 grok 對 AR-1 **獨立**收斂到同一形式（`decision_offset_bars`＋衍生 `decision_at_ms`），恰為 codex P0-01 要求之「單一可序列化形式」——判非附和。

Verdict：**需修補後合併**——十三群集全部寫回 SPEC（修訂版）後派 R2 複審（原提出方閉合驗證，章程 §B8）；無全域停工 BLOCKING（codex P0-01 屬「reconcile 必須裁定的契約形式」，本輪 X1 已裁）；AR-1..AR-6 全數裁定（見 X1／X4／X6／X3／Verdict 末）。AR-4＝維持一份 SPEC＋B1–B5（三家一致）；AR-5＝產生器維持 B3、MVP 不前移 B2（三家一致；前移僅得於 TODO 階段由主委明示）。

### X1 — AR-1 定形：`decision_offset_bars` 單一可序列化形式（codex P0 ⊕ composer/grok AR-1 獨立同型）
**引用**: CODEX-R1-P0-01
**處置＝改 §0 D1/D2＋Task B1.0/B1.1＋§G-2**：匯入欄＝`t0`（錨；epoch ms UTC；＝觸發根 open_time）＋`decision_offset_bars`（int ≥0，預設 0；語意＝決策時點為 t₀ 往前第 k 根**錨定 TF** bar 之 open；0＝t₀ open）。**不設** ms 覆寫欄（單一表示法；composer 之負號慣例不採，取無負號版）。`decision_at_ms` 由 `align_events` 推導寫入 receipt（含 `t0_ms/decision_offset_bars/decision_at_ms` 三欄並排）；validator 增 `decision_at ≤ t0_open_ms`；缺 bar 無法推導 ⇒ reason `missing_bar`。`entry_price_semantic` 值集＝`{trigger_open, trigger_close, next_open, decision_bar_open, decision_bar_close}`（字面唯一住契約檔）。§G-2 golden 加 k=0 與 k>0 各一 exact receipt oracle。

### X2 — label 錨不變式：label 錨＝t₀ close、與 decision_at 永遠脫鉤（grok 唯一提出；三家 AR-1 裁決相容）
**引用**: GROK-R1-P1-01
**處置＝改 §0 D1 加硬條款**：(i) label 錨＝t₀ close，`decision_offset_bars>0` 不改變錨；(ii) 條件 IC 只吃匯入之 `label_value`（缺值處置見 X3），**禁止**以 `decision_at` 列 join 主線 `return_N`（`return_N[decision_at]` 錨在 decision close ≠ t₀ close）；(iii) B2.3 驗收加 t₀−k 手算案例斷言 label 錨不隨 decision 移動。

### X3 — `label_value` 條件必填＋AR-6 裁決（v1 不重算、探針留殘留）
**引用**: CODEX-R1-P1-02
**處置＝改 §0 D1-3＋B1.0＋B2.3**：`statistic_kind=conditional_ic` 之 `label_value`＝**條件必填**；缺 ⇒ `capability_status=unavailable` reason=`missing_label_value`（字面入契約檔）；v1 不重算、不留「重算或拒絕」二選一給 TODO。**AR-6 裁決＝維持 §N 殘留**（codex＋composer 同判；grok 主張 B1 可選 task——分歧處置：採多數＋較小 scope；grok 之 `label_probe_mismatch` loud 欄設計原文收錄於 §N-8 條目，日後升級直接取用；觸發條件具體化＝「使用者要求，或匯入資料品質事故」）。

### X4 — AR-2 定形：反例自動分類契約（codex 挑戰 ⊕ composer/grok AR-2 裁決合併）
**引用**: CODEX-R1-P1-03
**處置＝改 Task B1.0/B1.5/B2.2**：B1.0 契約增 `counterexample_classifier_config`（門檻/單位/預設值之唯一列舉處）；分類定義＝direction-aware signed return、錨同 D1（t₀ close）；`kind_source ∈ {user, platform_auto}`；使用者手標優先、平台只補缺、不回寫；user/platform 衝突 ⇒ 保留 user＋報告附 `platform_suggested_kind` 留痕（composer）；**邊界同時滿足多類 ⇒ `unclassifiable`（不猜；grok 較嚴版；composer 之 c>b>a precedence 不採——避免「取保守」變相猜測）**；答案窗不完整 ⇒ `unclassifiable`、不進分層分母；B1.5/B2.2 驗收加逐類 exact boundary＋conflict case。

### X5 — T8/T9/T10 條件必填 schema（codex 唯一提出）
**引用**: CODEX-R1-P1-04
**處置＝改 Task B1.0**：條件化必填——事件宣告用到跨標的參照 ⇒ T8 `reference_symbols[]` 子物件全欄必填；`event_origin=model`（T9）⇒ `source_model` 全欄＋availability receipt 必填，缺 ⇒ `research_only` 或拒；`event_shape=interval`（T10）⇒ start/end/端點語意/overlap identity 必填；不得以自由 `meta` 補洞；未用該形狀之事件不受影響（v1 scope 不變）。

### X6 — 多標的 estimand 下游強制消費＋AR-3 裁決（codex 挑戰 ⊕ 三家 AR-3 一致）
**引用**: CODEX-R1-P1-05
**處置＝改 Task B2.1/B2.2/B2.3/B2.5/B4.1**：`event_split_plan`＋cluster manifest 列為五個 Task 之**必需輸入**（各 Task 改法/驗證欄補斷言）；每張表/報告必列 macro primary、micro sensitivity、raw/effective n、cluster CI、`degraded`、LOSO/held-out status；未 cluster 調整 ⇒ 禁 formal pooled inference。**AR-3 裁決**：多標的＝必要宣稱（U12）；`n_symbols==1` ⇒ `degraded:single_symbol`（exploratory 可跑不禁）；#4 不關閉、不做 cross-sectional/GEE（§N-5 維持）。

### X7 — 特徵物化 Task 缺口（codex 唯一提出）
**引用**: CODEX-R1-P1-06
**處置＝新增 Task B1.6「特徵物化與決策列選取」**：連續 per-TF Feature Factory 物化（全歷史或 ≥ 最長 lookback＋warmup 之段）→ `decision_at` as-of 取事件列 → 輸出 `features_at_decision`＋`feature_manifest_hash`＋per-TF warmup/NaN 行為；因果 invariant（截斷未來資料結果不變）測試；B1.4 輸入改為 B1.6 產出；B3.3 檔案落點寫死＝新檔 `state_counters.py`（不留「或擴 derived_operators」二選一）。

### X8 — mutation contract 補強（codex 挑戰 ⊕ composer M5 缺口同源）
**引用**: CODEX-R1-P1-07
**處置＝改 §V**：M1–M8 逐條補 baseline/mutation diff/命令/預期 rc/輸入 digest；M1 改「failures 記帳被吞（drop 不寫 reason）⇒ 紅」（B1.1 API 為回傳 failures，非 raise baseline）；M2 改「`feature_cutoff` 選入 decision_at 之後**下一實際 TF bar** ⇒ PIT oracle 紅」（跨 TF 可重現）；M5 綁 X9 公式＋手算權重和；M8 固定 seed＋CI 判定式；新增 M9（offset 推導竄改 k→k−1 ⇒ §G-2 紅）、M10（AR-2 邊界改猜測 ⇒ 紅）、M11（`degraded` 標記移除 ⇒ 紅）、M12（T9 availability 檢查移除 ⇒ 紅）。

### X9 — `cluster_weight` 公式收斂（composer 唯一提出；R2 synth 內部張力裁定）
**引用**: COMPOSER-R1-P1-01
**處置＝改 Task B1.3＋契約檔**：primary `cluster_weight = 1/n_events_in_time_cluster`（R2 synth C6 **群集正文**收斂值；附錄 GROK-R2-P1-03 之 `1/sqrt(n_symbols_in_cluster)` 為單家原始提案、非群集收斂結論——本輪明文裁定 1/n）；bootstrap over clusters＝敏感度；字面唯一入契約檔；B1.3 驗證加手算小例（同簇權重和＝1）。

### X10 — B3 依賴補 B2.5 邊＋G6 禁平行實作（composer/grok 獨立同判）
**引用**: COMPOSER-R1-P1-02, GROK-R1-P1-02
**處置＝改 §P Phase B3 標題＋Task B3.2**：B3 依賴改「B1＋B2.5」；B3.2 明寫 G6＝呼叫 `evaluate_all_bars`、**禁平行實作**；驗證加 G6 adapter 呼叫 B2.5 之整合測試一條。

### X11 — `entry_price_semantic` 頂層化（grok 唯一提出）
**引用**: GROK-R1-P1-03
**處置＝改 Task B1.0**：`entry_price_semantic` 升事件頂層（與 `label_definition` 平級；R2 C1 原意即並列硬欄）；`label_definition` 只留 rule_id/canonical_digest/window/label_return_mode；持有報酬公式讀頂層 entry 語意。

### X12 — 文字修正兩處（grok MINOR）
**引用**: GROK-R1-P2-04, GROK-R1-P2-05
**處置**：§P B4 加腳註「K6 落批以 R2 C9 為準，覆寫 C7 正文之 B3 批號」；B3.2 驗證展開為 G1–G6 六條逐項斷言（含 G2 多組 label 一次設定、G3 方向/情境/答案窗/規則摘要自動存、G5 一鍵合規檔、G6 綁 X10）。

### X13 — §N-7 `platform_*` 循環 scope 解除（codex 唯一提出）
**引用**: CODEX-R1-P1-08
**處置＝改 §N-7＋Task B3.2＋B1.0**：拆兩半——`platform_same_trigger_rule` **收回為 B3.2 可驗收能力**（產生器多組 label 天然產同觸發控制組；輸出過 B1.0 validator、`control_kind` 正確標記；驗收加一條）；`platform_random_bars` 留殘留改 `needs-research:隨機 bar 控制組之 estimand 與抽樣契約未定義（R1 已判時間分離隨機反例＝廢答案設計，禁隱式 fallback）`；循環解除（B3 不再是自票 blocker）。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01

**斷言**: t₀−k 的 decision/entry 契約沒有可執行的 canonical 形式；D2 的六欄 invariant 仍不足以防止不同 agent 對 offset、bar 端點與 entry price 做不同解讀。

**碼證**: `docs/GAP3_EVENT_SPEC.md:22,29,67-70,105,121-126` 同時使用「t₀ open／t₀−k」「k 為契約欄」「形式屬 AR-1」，但未固定欄名、單位、anchor、endpoint 或推導規則。`VERIFY`: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`、rc=0；`docs/GAP3_EVENT_SPEC.md:28-31` 的 invariant 只約束已產出的 receipt，不能定義輸入。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d

[BLOCKING] 信心度=High。若 B1.0 允許自由寫「t₀−k」或同時接受 bar offset/ms timestamp，B1.1 可能在不同 TF 取不同 bar，造成 PIT 與 entry/label mismatch；§G-2 也無法重現。修法：在 reconcile 決定單一 input representation、t₀ anchor、offset sign/unit、bar open/close、entry price source、label endpoint 與 invalid-case reason；derived `decision_at`/`entry_at` 由 validator/receipt 產生，並為 k=0 與 k>0 各加 exact golden。

## CODEX-R1-P1-02

**斷言**: D1 允許平台依契約重算連續 label，但 B1.0 將 `label_value` 設為選填且 v1 不重算，B2.3 又只接受連續 `label_value`；同一份事件在缺值時沒有唯一結果。

**碼證**: `docs/GAP3_EVENT_SPEC.md:23-25` 寫「使用者附 `label_value` 或平台重算」；`:121-124` 把 `label_value` 列選填並寫 v1 不重算；`:210-219` 又寫 conditional IC 只吃連續 `label_value`、全缺即 `unavailable`。`VERIFY`: `sed -n '40,47p' momentum/FeatureEngineering/labels/label_generator.py` → close-to-close `close.shift(-horizon)/close - 1`；`sed -n '99,103p' api/models/requests.py` → CLOSE_TO_CLOSE 預設。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d

[MAJOR] 信心度=High。修法：v1 明確選一條：conditional IC 的 `label_value` 變成該統計的條件必填，缺值固定輸出既有 `unavailable` reason 且不重算；或另立明確、可驗收的重算 task。依 AR-6 裁決，本輪建議前者，並將一致性探針保留 §N；不得讓 TODO agent 自行在「缺值時重算或拒絕」之間選擇。

## CODEX-R1-P1-03

**斷言**: 反例自動分類的 a/b/c 契約未定門檻、方向符號、優先序、手標衝突 receipt 與分母處置，因此 B1.5/B2.2 的分層結果不可重現。

**碼證**: `docs/GAP3_EVENT_SPEC.md:67-72,175-184,199-205` 只寫「門檻可調」「使用者手標優先」「依 t₀ 走勢分 a/b/c」「tie-break 依 AR-2」，未指定 threshold unit/value、signed long/short 判定或多類同時命中的 precedence。`VERIFY`: `grep -n 'counterexample_kind\|kind_source\|AR-2' docs/GAP3_EVENT_SPEC.md` → 只見欄位與待裁決錨點，無分類公式。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d

[MAJOR] 信心度=High。修法：AR-2 固定 config SoT 的 signed return/方向化門檻、優先序、`kind_source`、user/platform conflict receipt；答案窗不完整輸出 `unclassifiable` 且不假填、不把分類當 label。B2.2 驗收應包含每一類的 exact boundary 與 conflict case。

## CODEX-R1-P1-04

**斷言**: T8/T9/T10 在 B1.0 全列為選填，沒有依 `event_source`/`event_origin`/`event_shape` 條件化必填，會允許不可重建的跨標的、模型訊號或 interval event 進入後續統計。

**碼證**: `docs/GAP3_EVENT_SPEC.md:121-126` 將 `reference_symbols[]`、`source_model`、`event_interval` 都列在選填；同一段只對 T9 在「若有」時寫 `available_at ≤ decision_at`。R2 C7 要求 T8 reference alignment/digest、T9 model provenance/availability、T10 interval endpoints/overlap identity；B2/B4 沒有補條件驗證。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d; 白話說明/GAP-3事件型討論.md#7c884b1cdb70

[MAJOR] 信心度=High。修法：保留 v1 不實作未啟用事件種類的 scope，但對已宣告使用的形狀加 conditional schema：cross-symbol/reference feature 必須有 reference symbol/timeframe/alignment/snapshot；model-origin event 必須有 model/artifact/split/feature digest 與 availability receipt；`event_shape=interval` 必須有 start/end/endpoint semantics/overlap identity。未滿足時 fail-closed 或 `research_only`，不能由自由 `meta` 補洞。

## CODEX-R1-P1-05

**斷言**: U12/K4 的 multi-symbol macro/micro/time-cluster 計畫只在 B1.3 宣告，B2 三表、B2.5 all-bars 與 B4 ML 沒有強制消費同一 estimand/cluster receipt，因此事件型 IC/ML 仍可退化成每 symbol 分報或 raw pooled。

**碼證**: `docs/GAP3_EVENT_SPEC.md:153-162` 定義 B1.3 的 macro primary、micro sensitivity、cluster、LOSO；但 `:188-219` 的三表只要求 `symbol/time/cluster` 分層，`:232-241` 的 all-bars 只列 symbol/direction/kind/time，`:280-300` 的 pattern/ledger 沒有 macro/micro 或 cluster-robust/LOSO gate。R2 C6 要求 pooled 後的 macro/micro、同時刻 cluster、degraded 與 held-out-symbol receipt。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d; 白話說明/GAP-3事件型討論.md#7c884b1cdb70

[MAJOR] 信心度=High。修法：把 `event_split_plan`/cluster manifest 設為 B2.1/B2.2/B2.3/B2.5/B4.1 的必需輸入；每張表與 ML report 明列 macro primary、micro sensitivity、raw/effective n、cluster CI/Bootstrap、degraded 與 LOSO/held-out-symbol status。未做 cluster adjustment 時禁止 formal pooled inference，不能只在 B1.3 報一次。

## CODEX-R1-P1-06

**斷言**: SPEC 沒有一個 task 明確規定 Feature Factory 在連續資料上物化各 TF 特徵、依 decision_at 取單一事件列並攜帶 feature manifest；B1.4 直接接收 `features_at_decision`，B3.3 只新增算子，J3 的核心資料路徑因此可被遺漏或誤做成每案例固定窗。

**碼證**: 討論檔 J3/S3.4 要求「全部 K 線連續算特徵、每案例取決策時點那一列」；`docs/GAP3_EVENT_SPEC.md:131-140` 明說 B1.1 不在 alignment 內算特徵，`:164-173` 的 B1.4 只接 `features_at_decision`，`:267-276` 的 B3.3 只描述新 state-counter 的 lookback/as-of，沒有連續 Feature Factory materialization/row-selection task 或 golden。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d

[MAJOR] 信心度=High。修法：在 B1.1/B1.4 或新增明確 task 固定「全歷史／連續 TF 特徵 → decision_at as-of → event row」的輸入輸出、`feature_manifest_hash`、每 TF warmup/NaN 行為與截斷未來 invariant；B3.3 的 operator 檔案也應在 TODO 前選定，不保留「新增檔或擴既有檔」二選一。

## CODEX-R1-P1-07

**斷言**: §G/§V 的 M1–M8 目前不是逐條可執行、可證偽的 mutation contract，不能支持「每個改壞必 FAIL」的宣稱。

**碼證**: `docs/GAP3_EVENT_SPEC.md:99-108` 與 `:337-351` 宣告 golden/mutation；M1 寫 `raise → silent continue`，但 `:133-140` 的 B1.1 API 是回傳 `(receipts, failures)` 且沒有 raise baseline；M2 以 `< decision_at+1bar` 描述後移，未定 per-TF bar identity；M5 只說權重和斷言，未定 cluster weight canonical formula；M8 只說 permutation 後仍顯著則 oracle 紅。`VERIFY`: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS，表示錨點存在，不代表 mutation 語義已閉合。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d; templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#ab5f208a57a6

[MAJOR] 信心度=High。修法：每個 M 項補 baseline function/fixture、精確 mutation diff、命令、預期 rc、輸入 digest 與失敗斷言；M1 改成 failures ledger 被吞掉的明確變異，M2 改成「選入 decision_at 之後的下一個實際 TF bar」；M5 選定 cluster weight 或 cluster bootstrap oracle；M8 固定 seed/CI 判定。補 AR-1/AR-2、multi-symbol degraded、T9 availability 的 negative oracle。

## CODEX-R1-P1-08

**斷言**: §N-7 把本票 B3 產生器當成 `platform_*` 的 blocker，但 B3 同時是本 SPEC 的既定 phase 且 B3.2 宣稱完整 generator，造成「同票 phase 既是依賴又是本票完成條件」的循環 scope；目前不能判定是合法殘留或漏列 task。

**碼證**: `docs/GAP3_EVENT_SPEC.md:121` 將 `platform_*` 留枚舉並寫「B3 產生器落地後啟用」；`:243-265` 將 B3.1/B3.2 定為完整事件產生器；`:364-373` 又將 `platform_*` 登記為 `blocked-by:B3 產生器`，觸發條件仍寫「B3 完工後由 TODO 排入或轉殘留」。R2 C9 只把 T4/T6 外部資料源列為 blocked-by，未把同票 B3 當外部 blocker。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d; 白話說明/GAP-3事件型討論.md#7c884b1cdb70

[MAJOR] 信心度=High。修法：在 reconcile 二選一並寫死：①本票 v1 明確不實作 `platform_*`，將理由改成明確 scope/user-ruling/second-version 並登記；或 ②把 platform control sampling 的輸入、輸出、negative oracle 加進 B3 task。不能以 B3 自己作為 blocker 又宣稱 B3 完整交付。

### Verdict

需修補後派工。可以進 reconcile＋白話閘準備，但在白話閘前必須收斂 `CODEX-R1-P0-01` 的 AR-1 PIT contract；並修補 P1 的 label 缺值、AR-2 分類、T8/T9/T10 conditional schema、multi-symbol downstream estimand、feature materialization、mutation contract 與 §N-7 scope。未修補前不可宣稱 D1–D4 已達可凍結的「最完整精確」版本，也不可派發 B1 implementation token。

ASSUMPTIONS_VERIFIED: target commit/hash；template_check PASS；selected §A FACT-RECEIPT outputs；R2 C1–C9 與 R1 retained source 已逐段對照；§P 未發現 forward dependency。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`, rc=0；selected `sed`/`grep` receipts → outputs match cited facts；`sha256sum docs/GAP3_EVENT_SPEC.md` → `d0babfea8f24…`, brief match。
FAILURES_SEEN: none in template/hash/fact rechecks; review findings are unresolved SPEC contract gaps, not test failures.
SCOPE_CHANGES: no code/SPEC changes; created only `handoffs/20260820-gap3-spec-r1-codex.md`.
NUMERIC_OR_SCHEMA_IMPACT: no implementation/output changes; findings concern unresolved contract/schema acceptance semantics only.
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r1-codex.md`.
STATUS: DONE
## COMPOSER-R1-P1-01

**斷言**: `time_cluster_id`/`cluster_weight` 的 estimand 在 R2 synth 內部分裂（`1/n_in_cluster` vs `1/sqrt(n_symbols_in_cluster)`），而 SPEC §P B1.3 只列欄位名未給公式，違反 JSON SoT 原則，實作者會選出互不相容的 pooled SE。

**碼證**: `handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md` C6 群集 L44 `cluster_weight（1/n_in_cluster 或 bootstrap）` vs 同檔 GROK-R2-P1-03 L209 `1/sqrt(n_symbols_in_cluster)`；`docs/GAP3_EVENT_SPEC.md` B1.3 L157 僅寫 `` `cluster_weight` `` 無公式。RECHECK: `rg -n "cluster_weight" docs/GAP3_EVENT_SPEC.md handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md`

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24

[MAJOR] 信心度=High。修法：在 AR-3 reconcile 一併裁決 primary＝`cluster_weight=1/n_events_in_time_cluster`（同 UTC bucket 跨 symbol 事件等權），bootstrap over clusters 為敏感度；寫入 `event_import_contract.json` 唯一枚舉；B1.3 驗證增手算小例權重和=1。否則 macro/micro 與 cluster-robust CI 不可比。

## COMPOSER-R1-P1-02

**斷言**: Phase B3 宣告「依賴：B1」，但 B3.2 目標含 G6「全 K 線標籤重算」，且 B2.5 明示「B3 產生器共用標籤重算」——Phase 依賴圖缺少 B2（至少 B2.5），違反 brief 要求攻「存活至/覆蓋風險」與 forward dependency。

**碼證**: `docs/GAP3_EVENT_SPEC.md` L243 `### Phase B3 — …（依賴：B1`；L257 B3.2「同引擎做全 K 線標籤重算」；L235 B2.5「B3 產生器共用標籤重算（G6）」。RECHECK: 對照 §P 各 Phase 依賴欄與 G6 討論檔 §6 產生器第 6 點。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24

[MAJOR] 信心度=High。修法：B3 依賴改為「B1、B2（B2.5 all_bars_eval）」；B3.2 驗證增一條 G6 adapter 呼叫 B2.5 之整合測試；或將 G6 從 B3.2 拆為 B2.6 並讓 B3.2 只產事件檔。否則 agent 可能並行 B2/B3 導致 G6 接口不存在。

## GROK-R1-P1-01

**斷言**: SPEC §0 D1-2／D1-3 在 U4b 預設 `close_to_close` 且決策時點可為 t₀−k 時，未鎖「標籤錨點永遠是 t₀ close、禁止以 `decision_at` 列去 join 主線 `return_N`」；實作者可把「條件 IC 直接吃」誤讀成在決策列重用序列型 label，造成系統性錯估。

**碼證**: D1-2 原文「標籤基準一律相對 **t₀ close**……條件 IC 直接吃」；D1-3 只在 `label_return_mode ≠ close_to_close` 時強制 `label_price_mismatch`，**未**覆蓋 `mode=close_to_close` 但 `decision_at ≠ t₀`（t₀−k）之錯 join。對照 U4b（討論 §7）與 FACT `label_generator.py:40-47`＝`close.shift(-h)/close-1`（錨在**該列 close**）。當 `decision_at=t₀−k` 時，決策列之 `return_N`＝相對 decision close，≠ 相對 t₀ close。AR-1 尚開放形式，但 D1 已宣稱「最完整精確合併點」卻缺此不變式。`VERIFY`: `sed -n '21,25p' docs/GAP3_EVENT_SPEC.md`；`sed -n '40,47p' momentum/FeatureEngineering/labels/label_generator.py`。`RECHECK`: 以 `decision_offset_bars=k>0` 手算一列，斷言事件 `label_value` 必須用 t₀ close 錨、且 validator 拒 `return_N[decision_at]` 當事件 label。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d

[MAJOR] 信心度=High。會怎麼失敗：B2.3 條件 IC 在 t₀−k 路徑靜默吃錯 horizon 錨點，報表看起來「與主線同語意」實則估錯。修法：D1 增一條硬不變式——(i) label 錨＝`t0` close（與 `decision_at` 脫鉤）；(ii) 條件 IC 只吃匯入／契約重算之 `label_value`，**禁止**以 `decision_at` 對齊主線 `return_N` 列；(iii) AR-1 定形時同步寫入 B1.0／B2.3 驗收。此條須在 reconcile 寫回後才能凍結；不阻進入 reconcile（AR-1 本就是處置槽）。

---

## GROK-R1-P1-02

**斷言**: §P Phase B3 標題宣告「依賴：B1」，但 B2.5 與 B3.2 交叉要求 G6（全部 K 線標籤重算）共用 B2.5 evaluator，依賴圖少宣告對 B2 的邊，違反 brief 前提「依賴宣告無 forward／語意正確」之可執行性。

**碼證**: `### Phase B3 …（依賴：B1；落批＝AR-5…）`（SPEC:243）；B2.5「B3 產生器共用標籤重算（G6）」（:235）；B3.2「U6/G1–G6」「G1–G6 逐項對應驗收」（:256-260）；討論檔 G6＝「同一個引擎也拿來做全部 K 線驗證的標籤重算」（§6 末第 6 點）。B3 若只依 B1 開工，G6 無 `evaluate_all_bars` 可調（除非重寫一份——與「共用」矛盾）。非 forward dependency，屬**缺先序依賴**。`VERIFY`: `sed -n '232,261p' docs/GAP3_EVENT_SPEC.md`；`sed -n '211,219p' 白話說明/GAP-3事件型討論.md`。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/20260820-gap3-spec-r1-BRIEF.md#03919820cf8c

[MAJOR] 信心度=High。會怎麼失敗：TODO／實作代理按標題只等 B1 stamp 就開 B3.2，G6 驗收空心或複製一套 all-bars 邏輯（雙實作漂移）。修法：B3 依賴改 `B1+B2`（或至少 B2.5）；若 AR-5 維持產生器在 B3，於 B3.2 明寫「G6＝呼叫 B2.5 `evaluate_all_bars`，禁平行實作」。逐 Task「存活至／覆蓋風險」欄本身無「B1 產物被 B3 刪」短命工；本 finding 攻的是依賴語意，非存活欄空殼。

---

## GROK-R1-P1-03

**斷言**: D1 把 `entry_price_semantic` 與 `label_return_mode` 寫成對等契約欄，但 B1.0 把 `entry_price_semantic` 嵌進 `label_definition{…}`；在 U4b「進場價 ≠ 標籤基準、兩數並排」下，嵌套形狀會誘導實作者用進場語意去定義標籤錨點。

**碼證**: D1-1「契約必填 `entry_price_semantic`…＋`label_return_mode ∈ {…}`」（SPEC:22）；D1-4「實際進場價…與標籤基準…兩個數…並排、不混」（:25）；B1.0「`label_definition{rule_id, canonical_digest, window, label_return_mode(預設 close_to_close), entry_price_semantic}`」（:121）。R2 C1 處置亦將二者並列為契約硬欄，非 label 子物件。JSON SoT 只能有一種形狀——SPEC 內部未收斂。`VERIFY`: `sed -n '21,25p;120,122p' docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d0babfea8f24; handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d

[MAJOR] 信心度=High。修法：B1.0 升 `entry_price_semantic` 為事件頂層（或與 `label_definition` 平級）；`label_definition` 只留錨點／window／`label_return_mode`；持有報酬公式讀頂層 entry 語意。與 P1-01 一併在 reconcile 寫回。

---

## GROK-R1-P2-04

**斷言**: brief 前提「R2 synth C1–C9 是 K1–K10 完整且正確表述」不完全成立：C7 正文把 DSR/PBO 寫在 B3，C9 主委定案放 B4；SPEC 正確跟 C9，但未註記「以 C9 覆寫 C7 批號」，TODO 作者若只讀 C7 會排錯批。

**碼證**: R2 synth C7「DSR/PBO…只在 B3 規則→…ledger 後接」（synth ~L49）；C9「B4 pattern／DSR-PBO 橋」（~L56-59）；SPEC B4.2（:291-300）跟 C9。其餘 C1–C6／C8 與 SPEC §0／§P 對得上；C1 預設已被 U4b 改寫且 D1 有標註。`VERIFY`: `sed -n '46,59p' handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md`；`sed -n '278,300p' docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md#5c091a8f2d0d; docs/GAP3_EVENT_SPEC.md#d0babfea8f24

[MINOR] 信心度=High。修法：§P B4 或 §0 腳註一行「K6 落批以 R2 C9 為準，覆寫 C7 正文 B3」。非停工項。

---

## GROK-R1-P2-05

**斷言**: B3.2 寫「G1–G6 逐項對應驗收」但 SPEC 未把討論檔六點展開成可勾選驗收表，代理可能只測「能產事件＋過 validator」而漏 G2 多標籤一次設定／G3 方向·情境·答案窗·規則摘要自動存。

**碼證**: 討論 §6 末完整版 1–6（觸發任意 FF＋結果欄；多組 label；方向／情境／答案窗／規則摘要；產生期去重回報；一鍵合規檔；同引擎全 K 線標籤重算）。SPEC B3.2 驗證句只顯式提「十類①②③⑩代表案例」與「G4 去重回報」（:261），G2／G3／G5／G6 無對應 ASSERT 列舉。`VERIFY`: `sed -n '211,219p' 白話說明/GAP-3事件型討論.md`；`sed -n '256,265p' docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: 白話說明/GAP-3事件型討論.md#7c884b1cdb70; docs/GAP3_EVENT_SPEC.md#d0babfea8f24

[MINOR] 信心度=Medium。修法：B3.2 驗證改為 G1…G6 六條 ASSERT（或 pointer 到契約／TODO 表）；G6 並綁 P1-02 之 B2.5 呼叫。不阻 reconcile。

---

