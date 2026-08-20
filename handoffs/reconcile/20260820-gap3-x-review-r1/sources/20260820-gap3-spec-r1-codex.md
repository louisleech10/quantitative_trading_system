# GAP-3 事件型 SPEC 初稿 adversarial review R1 — codex

審查標的：`docs/GAP3_EVENT_SPEC.md` @ `e0af4a3d9836374ba134d538d64384ee279003b0`。

審查範圍：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`§7.5` 五層取材地圖、R2 C1–C9、R1 未被 R2 覆蓋的六時間欄／ms 單位閘／taxonomy／legacy 清單，以及既有契約 pointer。

查核摘要：標的 SHA-256 為 `d0babfea8f2412fe2a68aa69af8b8adf71b3152f8d6a1e7301b5c7ffca32f7bd`，與 brief 一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`、rc=0。

### §0 前提挑戰與 fact / assumption

- fact-verified：HEAD 為 brief 指定 commit；標的 SHA-256 與 brief 一致。
- fact-verified：SPEC template check 通過；selected FACT-RECEIPT 已重跑，包含 `label_generator.py` 的 close-to-close、`requests.py` 的 CLOSE_TO_CLOSE 預設、舊 `xgboost_batch_service.py` 的精確 timestamp 對齊與 silent skip、`SplitPlan` 欄位、`UNWIRED_MODULES` 的 `sample_weight`、以及變化類算子 grep=0。
- assumption challenged：R2 synth C1–C9 的技術結論大致已回填，但 T8/T9/T10 的條件必填性、multi-symbol estimand 的下游傳遞、以及 AR-1/AR-2 的可執行形式仍未完成，因此「§0 是最完整精確合併點」目前只成立到可進 reconcile 草案，不成立到可凍結／派工。
- assumption verified：§P 的批次依賴沒有發現把後批產出當前批輸入的 forward dependency；B2.5 對 B3/B4 的描述是後續消費關係，不是反向排程依賴。`存活至` 與 `覆蓋風險` 欄大多已具體填寫，但 §N-7 另有循環 blocker，見 `CODEX-R1-P1-08`。

### §7.5 逐條對應表

判定：`OK` = 有落點且語意可接受；`PARTIAL` = 有落點但存在本報告 finding；`GOV` = 流程性來源，不是 runtime contract。

| layer | 條目 | SPEC 落點 | 判定 |
|---|---|---|---|
| U | U1 目標 A/B/C/兩段式、一次一方向、事件後報酬表 | B1.0 `direction`/`scenario`；B2.1；§N-2 | OK |
| U | U2 外部正反例、CSV、搜尋條件、連續漲幅 | B1.0 `label_value`/`search_rule_summary`；B5.1 legacy adapter | OK |
| U | U3 先討論、再 SPEC、再實作 | §A 待確認／§P review gate | GOV；無 runtime 遺漏 |
| U | U4 決策 t₀ open 或 t₀ 前 k、特徵跟隨決策 | D2；B1.0；B1.1 | PARTIAL；AR-1，`CODEX-R1-P0-01` |
| U | U4b label 基準 t₀ close、close-to-close、進場報酬另列 | D1-2、D1-4、B2.1/B2.3 | OK；實作形式仍受 AR-1/label 缺值規則約束 |
| U | U5 規模只是例子、不寫死 | B1.3 tier；B2.1 config horizon；B2.3 tier 降級 | OK |
| U | U6 完整事件產生器、落點 `/search` | B3.1/B3.2；B5.1 | PARTIAL；`platform_*` scope 與 §N-7 未閉合 |
| U | U7 現有頁面升級、不翻掉 | §C 白名單；B3.2；B5.1/B5.2 | OK |
| U | U8 LightGBM/XGBoost 選擇不影響設計 | B4.1 | OK |
| U | U9 連續觸發交 K3 | B1.2 primary/sensitivity policy | OK；cluster weight 仍需精確驗收 |
| U | U10 前端 `/search`、`/data-preparation`、`/ic-analysis` | B5.2 | OK |
| U | U11 全部 K 線驗證一次建完整 | D4；B2.5；§G | OK；§V mutation 覆蓋仍不足，見 `CODEX-R1-P1-07` |
| U | U12 多標的為常態必要、#4 邊界 | B1.3；§N-5 | PARTIAL；下游表與 ML 未強制消費 macro/micro/cluster，見 `CODEX-R1-P1-05` |
| U | U13 一份 SPEC、B1–B5、每批 review/stamp | §P 及各 phase 依賴 | OK；AR-4/AR-5 見後 |
| 8/20 | ① t₀−k 擴充 | D2-2；B1.0/B1.1；§G-2 | PARTIAL；AR-1 未定形，見 `CODEX-R1-P0-01` |
| 8/20 | ② label default close-to-close | D1-2；B1.0 | OK；沒有被舊 R2 open-based default 污染 |
| 8/20 | ③ TF 組合不寫死、per-TF as-of | D2-1；B1.1；§G-2 | OK；golden 用 1h/4h/12h 是代表案例，不是契約限制 |
| 8/20 | ④ 反例種類選填、平台可自動分類 | D2-2；B1.0；B1.5；B2.2 | PARTIAL；門檻/tie-break/衝突處置未定，見 `CODEX-R1-P1-03` |
| 8/20 | ⑤ 規模不寫死 | B1.3/B2.1/B2.3/B5.1 | OK |
| J | J1 case-control 必須全 K 線驗證 | D4；B2.5 | OK |
| J | J2 跨 TF 只用決策前收盤、各 TF 收據 | D2；B1.1 | OK |
| J | J3 不切固定窗、連續算特徵、取決策列 | B1.4 的 `features_at_decision`；B3.3 | PARTIAL；缺 feature materialization / decision-row contract，見 `CODEX-R1-P1-06` |
| J | J4 反例種類分報、兩段式分層 | B1.5；B2.2 | PARTIAL；同 AR-2，見 `CODEX-R1-P1-03` |
| J | J5 第一版時間出場、不碰回測 | D4-4；B2.1；§N-1 | OK |
| J | J6 pooled 最小版、同時刻簇、#4 不關閉 | B1.3；§N-5 | PARTIAL；下游統計未強制傳遞，見 `CODEX-R1-P1-05` |
| J | J7 既有 IC 大部分共用、需 event wiring | B2.3；§G-1 | PARTIAL；`label_value` optional 與 conditional IC strict input 矛盾，見 `CODEX-R1-P1-02` |
| J | J8 IC → ML pattern → all-bars 驗證 | B2.5；B4.1/B4.2 | OK；mutation/ledger 驗收仍需補強 |
| J | J9 A/B/C/兩段式是 scenario 維度 | B1.0 `scenario`；D2 | OK |
| J | J10 generator 與 IC filter 共用純函式底層 | D3；B3.1/B3.2 | OK；legacy `df.eval` 未被誤宣稱為新 SoT |
| R2 | C1 label/entry price 語意 | D1 | OK；已正確以 U4b 覆蓋舊 open-based default；AR-1 仍影響 entry 形式 |
| R2 | C2 per-TF cutoff、六時間欄、loud reason | D2；B1.1 | OK；t₀−k 形式另列 AR-1 |
| R2 | C3 三角色、typed AST/digest、adapter | D3；B3.1/B3.2 | OK |
| R2 | C4 fixed denominator、prevalence、lift、no backtest | D4；B2.5 | OK；可證偽 mutation 仍不足，見 `CODEX-R1-P1-07` |
| R2 | C5 primary policy、UTC duration、uniqueness、sample_weight 未接線 | B1.2；§N-4 | PARTIAL；cluster weight 與下游 estimand 未完整落地 |
| R2 | C6 pooled macro/micro、time cluster、#4 boundary | B1.3；§N-5 | PARTIAL；見 `CODEX-R1-P1-05` |
| R2 | C7 三表 estimand/CI、T8/T9/T10、DSR/PBO after return series | B2.1–B2.3；B4.2；B1.0 optional objects | PARTIAL；T8/T9/T10 conditional requiredness 缺失，見 `CODEX-R1-P1-04` |
| R2 | C8 reuse existing operators、add state counters | B3.3 | PARTIAL；feature materialization 與 task file ambiguity，見 `CODEX-R1-P1-06` |
| R2 | C9 B1→B2→B3→B4→B5 batch ordering | §P | OK；但 §N-7 的 B3 blocker 循環，見 `CODEX-R1-P1-08` |
| R1 | 六時間欄 invariant | D2-1；B1.1 | OK；AR-1 尚未提供可序列化 input form |
| R1 | epoch ms UTC 單位閘 | D2-3；B1.0/B1.1 | OK |
| R1 | taxonomy 正交欄 | B1.0 `taxonomy` | OK |
| R1 | legacy 不沿用 `CaseRecord`/舊 negative timestamp 語意 | B1.0、§C、B5.1；未引用 `_select_negative_timestamps` | OK |
| pointer | `ic_survivor_contract` version 1→2 | B2.4 | OK |
| pointer | `SplitPlan`/rows purge 與事件 interval purge 分離 | B1.3；§C | OK |
| pointer | `capability_status`/reason | D4；B1.3/B1.4/B2.2/B2.3/B2.5；§V | PARTIAL；多標的 degraded 傳遞尚未被所有報表要求 |
| pointer | `TEST_DESIGN_CHARTER` | §C、§G、§V | OK |
| pointer | GAP-1 DSR/PBO/MinBTL | B4.2；§N-4 | OK |
| pointer | 成熟度地圖、禁改 ML 殼、不碰回測 | §RISK、§C、§N、B4/B5 不可做 | OK |

### AR-1..AR-6 裁決

#### AR-1：決策時點 t₀−k 契約形式 — 不通過，先修後 reconcile

目前 D2 只同時寫「t₀ open 或 t₀−k」、`k` 是契約欄，且 D1 說 `entry_price_semantic` 需另擴 `decision_bar_open`；B1.0 只寫「決策時點欄」，未指定 canonical 欄名、ms/bars 的 SoT、t₀ anchor 的 open/close 定義、負 offset 的表示、`entry_at` 如何由 decision rule 推導，以及答案窗端點是否包含。這不是可由 TODO 自行決定的實作細節，而是 PIT contract。

裁決：保留 t₀−k 產品語意；在 reconcile 寫回前，必須選定一個可序列化形式（例如明確的 offset/rule 欄＋由 validator 推導 `decision_at_ms`，而不是同時接受多種自由字串），並固定 t₀ anchor、bar open/close、entry price source、label window endpoint。B1.1/§G-2 必須各有 k=0 與 k>0 的 exact receipt oracle；無法證明決策前已知時，需拒絕 trigger-open 或降為確認／下一根進場。對應 finding：`CODEX-R1-P0-01`。

#### AR-2：反例自動分類 — 不通過，先修後實作 B1.5

目前 B1.5 只有 a/b/c 的白話描述、可調門檻與「使用者手標優先」；沒有 direction-aware signed return 定義、門檻單位與預設、答案窗多個門檻同時成立時的 precedence/tie-break、手標與平台分類衝突時是否保留 discrepancy，以及 `unclassifiable` 是否進分母。B2.2 卻把 a/b/c 當必要分層。

裁決：保留 `counterexample_kind` 選填與 `kind_source`；先定 config SoT 的門檻及單位、分類優先序、手標優先但衝突留痕、答案窗不完整必為 `unclassifiable` 且不可假填。分類不得改寫使用者 label，也不得把分類結果當 label。對應 finding：`CODEX-R1-P1-03`。

#### AR-3：多標的必要化與 registry #4 邊界 — 邊界可通過，但需補 downstream gate

裁決：U12 應維持「事件型 IC/ML 必須多標的 pooled」，而 #4 仍只負責正式 cross-sectional/panel estimator；B1.3 的 per-symbol split、macro primary、micro sensitivity、time cluster、LOSO/held-out receipt 是合理邊界。可是 B2.1/B2.2/B2.3/B2.5/B4.1 沒有共同要求消費同一 `event_split_plan` 的 macro/micro、cluster-robust/bootstrap、degraded 與 LOSO receipt，因此目前只能算「B1 有計畫」，不能算整票契約閉合。對應 finding：`CODEX-R1-P1-05`。

#### AR-4：一份 SPEC vs 拆兩份 — 維持一份，通過但有條件

一份 SPEC＋B1–B5 的分批結構可以保留，因為每批已有檔案、依賴、驗證、存活至與覆蓋風險欄，且 review/stamp 是 phase gate。暫不拆；TODO 必須維持每批可獨立驗收，不能把「完整 generator」「前端」「UAT」的未決細節藏到最後一批。

#### AR-5：G1–G6 落批 — 維持 B3，不前移 MVP 到 B2

B2 已含三張表、survivor v2、all-bars evaluator，且 B3 需先完成 typed condition engine 才能安全處理 future outcome/多 label。把 generator MVP 前移 B2 會使 B2 同時承擔契約、統計、全 K 線與 condition engine，增加 phase 交叉依賴；目前 B3 落點較可收斂。B3.2 的 `platform_*` scope 另需明確化，見 `CODEX-R1-P1-08`。

#### AR-6：label 一致性探針 — 留在 §N 殘留，不列 B1 optional task

v1 已明文「不重算使用者 label」，而一致性探針的涵蓋 label family、誤報處置與是否阻擋匯入尚未定。裁決為：核心 v1 對 conditional IC 若無連續 `label_value` 應明確 `unavailable`，不以未定義的重算補洞；price-return-threshold 探針留 §N，只有日後定出 family、輸入、容差與 conflict receipt 才能另列 task。對應 finding：`CODEX-R1-P1-02`。

### §0 D1–D4「最完整精確合併點」裁決

- D1：語意方向正確，已以 U4b 覆蓋 R2 舊的 A/B open-based default；但 optional `label_value` 與 B2.3 strict continuous input 的矛盾要先收斂。
- D2：六欄、per-TF as-of、ms gate、loud reason 正確；t₀−k 的可序列化形式仍缺，AR-1 未完成。
- D3：三角色、future selection 與 ML feature 隔離、typed AST/digest、adapter 邊界完整。
- D4：fixed denominator、eligible/reason、prevalence/lift 與不碰回測完整；但 §V 尚未證明各 mutation 可抓壞行為。

總裁決：D1–D4 可作 reconcile 的工作基礎，尚不能稱為可直接凍結／派工的「最完整精確」版本。

### §N 八條殘留三值理由裁決

1. triple-barrier：`user-ruling`＋回測層 blocker 成立。
2. long-short：`user-ruling` 成立。
3. T4/T6：外部資料源 blocker 成立。
4. GBDT `sample_weight`：ML 殼未接線且成熟度約束成立。
5. 正式 panel IC：registry #4 blocker 與本票 pooled 原語邊界成立。
6. CAR/AAR／即時 NLP：使用者重定義 scope 成立。
7. `platform_*` 控制組：目前理由不成立到可凍結程度。B3 是本票同一 SPEC 的既定 phase，不能單獨作為永久 blocker；而 B3.2 又宣稱完整 generator、B1.0 又把 `platform_*` 留位。需在 reconcile 明定「本票明確不實作 platform_*」並以 user-ruling/second-version scope 登記，或把它納入 B3 的可驗收 task。對應 finding：`CODEX-R1-P1-08`。
8. label consistency probe：`needs-research:AR-6` 可成立，但 AR-6 已裁定留在 §N；需補明「缺 probe 不影響 v1 匯入，conditional IC 缺 label_value 直接 unavailable」的觸發語意。

### §G/§V golden 與 M1–M8 可證偽性

目前 G1–G4 的方向與高風險防護正確，且真實 kline、exact ms receipt、sha256、PIT 後移、unit gate、prevalence disclosure 等錨點足夠作為骨架。但 M1–M8 尚不能逐條宣稱「改壞必 FAIL」：M1 的敘述是 `raise` 改 silent continue，而 B1.1 的 API 是回傳 `failures`，沒有 baseline raise contract；M2 的 `< decision_at+1bar` 不是跨 TF/不規則 bar 可重現的後移定義；M5 沒指定 cluster weight/cluster bootstrap 的 canonical assertion；M8 只有「仍顯著則 oracle 紅」而未指定可執行的 CI 判定與輸入 digest。另缺 AR-1、AR-2、macro/micro 傳遞及 T9 availability 的 mutation。見 `CODEX-R1-P1-07`。

### §1 必查 11 類摘要

1. 矛盾／互斥：有，AR-1、`label_value` optional vs conditional IC strict input。
2. 漏項／端到端：有，feature materialization、multi-symbol estimand 下游傳遞、T8/T9/T10 conditional validation。
3. 不可測驗收：有，AR-1/AR-2 與 M1/M2/M5/M8。
4. Quant 假設：有，若未固定 t₀−k/entry/label 及 pooled estimand，會產生 PIT/estimand 偏移。
5. 過度工程：無獨立 BLOCKING；一份 SPEC 可保留，按 phase 收斂。
6. OOM／並行：無新增已證明的 SPEC 缺陷；B5 萬級事件僅列實測待辦，不能在本輪假設已通過。
7. Cache 正確性：無新增直接 finding；T8 reference digest 的條件必填性仍需修補。
8. API／型別／相容：有，AR-1 欄位形式與 T8/T9/T10 conditional schema 未定。
9. 測試品質：有，mutation 設計尚不能證明 M1–M8 全部抓改壞。
10. Agent 可執行性：有，feature materialization 缺 task；AR-1/AR-2 仍要求 agent 自行決定契約。
11. 必要性／短命工：有，§N-7 將同票 B3 當 blocker，需明確 scope 或收回 task。

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
