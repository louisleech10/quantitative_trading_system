# GAP-3 事件型 SPEC adversarial review R1 — COMPOSER

task-id: `20260820-GAP3-X-REVIEW-R1`  
審查標的: `docs/GAP3_EVENT_SPEC.md` @ `e0af4a3d`（sha256 `d0babfea8f2412fe2a68aa69af8b8adf71b3152f8d6a1e7301b5c7ffca32f7bd`）  
brief: `handoffs/20260820-gap3-spec-r1-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| 前提 | 標注 | 複核結論 |
|---|---|---|
| R2 synth C1–C9 為 K1–K10 完整正確表述 | **assumed → 部分推翻** | C1–C4/C7–C9 主體已落 D 系列與 §P；**C6 `cluster_weight` 在 synth 內部分裂**（群集寫 `1/n_in_cluster`，GROK-R2-P1-03 寫 `1/sqrt(n_symbols_in_cluster)`），SPEC 未裁決 → 見 P1-01 |
| §P 十六 Task 依賴無 forward dependency | **assumed → 部分推翻** | B3 宣告「依賴：B1」但 B3.2 G6 與 B2.5 `all_bars_eval` 互指，且 B2.5 L235 寫「B3 產生器共用」→ 見 P1-02 |
| FACT-RECEIPT 15 條 | fact-verified | 抽驗 `grep feature_cutoff momentum/` → `0`；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS |
| template_check PASS | fact-verified | 本輪重跑 rc=0 |

## §7.5 逐條對應表

| 層 | 來源條目 | SPEC 落點 | 沒漏 | 沒錯 | 舊結論污染 |
|---|---|---|---|---|---|
| 1 | U1 A/B/C/兩段式、單向 | B1.0 `scenario`/`direction`；B2 三表 | ✓ | ✓ | 無 |
| 1 | U2 CSV+搜尋條件+漲幅 | B1.0 `search_rule_summary`/`label_value`；D1-3 | ✓ | ✓ | 無 |
| 1 | U4 決策 t₀ open 或 t₀−k | D2-2；AR-1 待裁形式 | ✓ | ✓（generalize R2 `≤t0`→`≤decision_at` 合理） | 無 |
| 1 | U4b 標籤基準 t₀ close、預設 c2c | D1-2/4；改寫 R2 C1 預設 | ✓ | ✓ | 無「A/B 預設 open_to_horizon_close」殘留 |
| 1 | U4 反例種類選填+自動分類 | B1.0 選填；B1.5；AR-2 | ✓ | ✓ | 無 R1「隨機 bar 反例」預設 |
| 1 | U5 規模舉例 | B2/B1.4 tier 降級語意 | ✓ | ✓ | 無 |
| 1 | U6 完整產生器 /search | B3.1–B3.2；AR-5 | ✓ | ✓ | 無 |
| 1 | U7 升級不翻掉 | B3.2/B5.2；§G-1 | ✓ | ✓ | 無 |
| 1 | U8 ML 引擎不綁定 | B4.1；§C 禁改 xgboost 殼 | ✓ | ✓ | 无 |
| 1 | U10 前端落點 | B5.2 | ✓ | ✓ | 无 |
| 1 | U11 全 K 線一次建完整 | D4；B2.5 | ✓ | ✓ | 无 |
| 1 | U12 多標的必要 | B1.3；AR-3 | △ | △ | 无；但 n_symbols=1 時未 loud degraded（AR-3 裁） |
| 1 | U13 一份 SPEC+B1–B5 | §P 全章；AR-4 | ✓ | ✓ | 无 |
| 2 | J1 case-control+全 bar 配套 | D4；B2.5 | ✓ | ✓ | 无 |
| 2 | J2 跨 TF、決策時點前 as-of | D2-1/2；B1.1 per-TF receipt | ✓ | ✓ | 无 |
| 2 | J3 不切固定窗、決策時點取列 | B3.3 state_counters；§P 各 Task | ✓ | ✓ | 无 |
| 2 | J4 反例種類分報 | B2.2；B1.5 | ✓ | ✓ | 无 |
| 2 | J5 時間出場 | D4-4；§N-1 | ✓ | ✓ | 无 |
| 2 | J6 pooled 最小版 | B1.3；§N-5；AR-3 | ✓ | ✓ | 无 #4 關閉宣稱 |
| 2 | J7 IC 圖表九成可用 | B2.3；B5.2 | ✓ | ✓ | 无 |
| 2 | J8 IC→ML→全 bar | B4.1/B4.2；B2.5 | ✓ | ✓ | 无 |
| 2 | J9 scenario 維度 | B1.0 `scenario` | ✓ | ✓ | 无 |
| 2 | J10 共用條件引擎 | D3；B3.1/B3.2 | ✓ | ✓ | 无「df.eval 即完整引擎」 |
| 3 | R2 C1 價格語意 | D1 | ✓ | ✓（U4b 覆寫已明示） | 无 |
| 3 | R2 C2 六欄+per-TF+枚舉 | D2；B1.1 | ✓ | ✓ | 无 silent continue |
| 3 | R2 C3 欄位角色 | D3；B3.1 | ✓ | ✓ | 无 |
| 3 | R2 C4 固定分母+基率 | D4；B2.5 | ✓ | ✓ | 无 |
| 3 | R2 C5 簇/權重 | B1.2 | ✓ | △（cluster_weight 公式未寫） | 无 |
| 3 | R2 C6 pooled+time-cluster | B1.3 | ✓ | △（同上） | 无 |
| 3 | R2 C7 三表+T8–T10 | B2.1–B2.3；B1.0 選填欄 | ✓ | ✓ | 无 |
| 3 | R2 C8 K7 算子 | B3.3 | ✓ | ✓ | 无 |
| 3 | R2 C9 分批 | §P B1–B5 | ✓ | △（B3 依賴欄） | 无 |
| 4 | R1 六時間欄/ms 閘 | D2 | ✓ | ✓ | 无 C-情境反例預設 |
| 4 | R1 taxonomy 正交欄 | B1.0 選填 | ✓ | ✓ | 无 |
| 4 | R1 legacy 不沿用 | §A FACT-RECEIPT；§C 白名單 | ✓ | ✓ | 无 CaseRecord 擴充 |
| 5 | ic_survivor v2 升版 | B2.4 | ✓ | ✓ | 无 |
| 5 | SplitPlan 不動 | B1.3；§C | ✓ | ✓ | 无 |
| 5 | capability_status | B2 各表；§V | ✓ | ✓ | 无 |
| 5 | TEST_DESIGN_CHARTER / GAP-1 | §G；B4.2 | ✓ | ✓ | 无 |
| 5 | 成熟度地圖禁 ML 殼 | §C；§N-4 | ✓ | ✓ | 无 |

**小結**：五層主體已覆蓋；**漏**＝無整條遺失；**錯**＝C6/cluster_weight 與 B3 依賴宣告兩處待修；**污染**＝未檢出 R1 C-反例或「換時間戳共用 IC」滲入。

## AR-1..AR-6 裁決

### AR-1 決策時點 t₀−k 契約形式

**裁決：採 `decision_offset_bars`（int，預設 0）+ 衍生 `decision_at_ms`**  
- 匯入保留 `t0`（事件錨點 ms）+ `decision_offset_bars`（相對錨定 TF 之 bar 索引偏移，0＝t₀ open，負值＝t₀−k）。  
- `align_events` 推導 `decision_at_ms`；validator：`decision_at_ms ≤ t0_ms`（買入不晚於錨點 open）且六欄不變式不變。  
- `entry_price_semantic` 值集擴 `decision_bar_open`（當 k>0 且實際進場＝決策 bar open）。  
- receipt 增 `decision_offset_bars`/`decision_at_ms`/`t0_ms` 三欄並排。  
**理由**：比直接匯入 `decision_at_ms` 更易審計 t₀ 錨點；比純字串欄位可機械驗收。  
**碼證**：D2-2；B1.0 L121；R2 C2 不變式。

### AR-2 反例自動分類規則

**裁決：使用者手標優先；平台僅補缺**  
- `counterexample_kind` 缺且 `label=0` ⇒ 跑 `counterexample_classifier`；輸出 `kind_source=platform_auto`。  
- 使用者已填 ⇒ `kind_source=user`，平台不重算、不回寫。  
- 門檻入 `event_import_contract.json` 之 `counterexample_classifier_config`（可調、附預設）；tie-break：同時跨類 ⇒ 取**最保守**（反向 c > 震盪 b > 不續漲 a）。  
- 衝突（使用者 a、平台算 b）⇒ **保留 user** + 報告附 `platform_suggested_kind` 敏感度欄，不覆寫主鍵。  
**理由**：符合 U4 選填+自動；避免靜默改標註。  
**碼證**：B1.5；§N-8 觸發後可降為 B1 可選子任務。

### AR-3 多標的必要化與 #4 邊界

**裁決：事件型 pooled 統計預設要求 n_symbols≥2；否則 `capability_status=degraded` reason=`insufficient_symbols_for_pooled`**  
- 單 symbol 仍可匯入/對齊/單標統計（B1.3 邊界①保留）。  
- **不關閉 registry #4**；不做 cross-sectional IC / GEE。  
- macro primary、micro sensitivity、time_cluster、LOSO receipt 語意照 B1.3。  
**理由**：落實 U12「常態必要」又不禁單標開發測試。  
**碼證**：U12；B1.3；§N-5；R2 C6。

### AR-4 一份 SPEC vs 拆兩份

**裁決：維持一份 SPEC + B1–B5**  
- 章節錨點齊、依賴單向；拆份收益低於 reconcile 摩擦。  
- 若 TODO 階段 B5 超 400 行再評估 generator 附錄 SPEC。  
**理由**：U13 預設；template_check 已 PASS；內容雖長但 §P 已分批可讀。

### AR-5 產生器 G1–G6 落批

**裁決：維持 B3 預設；不預設前移 B2**  
- G1–G5（觸發/多標籤/元資料/去重/validator）＝B3.1–B3.2。  
- G6（全 K 線標籤重算）＝B3.2 呼叫 B2.5 `all_bars_eval` 之 adapter（**並修正 B3 依賴見 P1-02**）。  
- MVP（T1+G2–G5）前移 B2 僅能在 B2 提早完工且主委明示時，寫入 TODO 而非 SPEC 預設。  
**理由**：C9「先資料正確再降手工」；B2 靈魂 K8 優先。

### AR-6 label 一致性探針

**裁決：維持 §N-8 殘留；B1 不增可選 task**  
- v1 不重算使用者 label（R1 C2-4）已足；探針族/誤報處置需另開研究票。  
- 觸發條件：使用者要求或匯入爭議事故後升級 B1.x。  
**理由**：非 B1 資料正確性門檻；避免 B1 膨脹。

## 必答摘要

### 1. §7.5 比對

見上表。**漏**：無。**錯**：`cluster_weight` 公式、B3 依賴欄。**污染**：無。

### 2. AR 裁決

見上節；六項均已裁。

### 3. §0 D1–D4 是否為最完整合併點

**成立（附條件）**。D1–D4 忠實合併 R2 C1–C4 ⊕ 8/20（U4b c2c 預設、t₀−k 擴充指向 AR-1）。  
**待 reconcile 寫回**：AR-1/AR-2 定形進 `event_import_contract.json` 後方可凍結。  
**無歧義處**：D1-4 兩數並排、D3 角色隔離、D4 固定分母——可驗收。

### 4. §N 八條殘留三值理由

| # | 理由類型 | 成立？ |
|---|---|---|
| 1 triple-barrier | user-ruling+blocked-by 回測層 | ✓ |
| 2 long-short | user-ruling §4 | ✓ |
| 3 T4/T6 外部源 | blocked-by 資料源 | ✓ |
| 4 sample_weight ML | blocked-by UNWIRED+成熟度 | ✓（FACT-RECEIPT 已附） |
| 5 panel IC #4 | blocked-by registry #4 | ✓ |
| 6 CAR/event study | user-ruling | ✓ |
| 7 platform_* 控制組 | blocked-by B3 | ✓ |
| 8 label 探針 | needs-research→AR-6 已裁維持 §N | ✓ |

無「該現在做卻偷懶」項。

### 5. §G/§V golden 與 M1–M8 可證偽性

**可證偽（附一處缺口）**。  
- §G 四類：sha256 exact、ms 手算、PIT/置亂 oracle、契約 fail-closed——均可執行。  
- M1–M8 各對應 B1.0/B1.1/B1.2/B2.5/B3.1 斷言路徑，改壞應紅。  
- **缺口**：M5 寫「B1.2/B1.3 權重和」但未點名 `cluster_weight` 公式——與 P1-01 同源；補公式後 M5 才完整。

### 6. 可否進 reconcile＋白話閘

**需修補後派工**（非重作）。  
BLOCKING：無全局停工項。  
**reconcile 前必寫回 SPEC**：P1-01、P1-02 修法 + AR-1..AR-6 裁決本文。

---

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

## §1 必查（11 類摘要）

| 類 | 結果 |
|---|---|
| 1 矛盾 | 見 P1-01/P1-02；其餘無 |
| 2 漏項 | 无 |
| 3 不可測 | 无（AR 裁決補齊 t₀−k/反例/多標的） |
| 4 quant 假設 | D1/D2/D3 已處理 PIT/label 語意；无新疑 |
| 5 過度工程 | 无 |
| 6 OOM | B5.1 邊界有萬級牆鐘偵察；无 |
| 7 Cache | 新模組不讀 HDF5 於 alignment；无 |
| 8 API/型別 | B5 占位；无 |
| 9 測試 | §G+M1–M8 覆蓋；cluster_weight 缺口見上 |
| 10 Agent 可執行 | Task 到檔案/函式；无 |
| 11 短命工 | B1.4 與 B2.2 共存有覆蓋風險欄說明；无白工 |

## Verdict：需修補後派工

兩項 MAJOR（P1-01、P1-02）+ AR-1..AR-6 裁決寫回 SPEC 後，可進 reconcile 與白話閘。無需重起草。

---

ASSUMPTIONS_VERIFIED: SPEC sha256 與 brief 一致；template_check PASS；feature_cutoff grep=0；R2 C6 cluster_weight 內部分裂；B3 依賴欄與 G6/B2.5 交叉引用  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS rc=0；`grep -rn feature_cutoff momentum/ | wc -l` → 0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none（建議 reconcile 後補 cluster_weight 契約，屬 SPEC 層）

STATUS: DONE
