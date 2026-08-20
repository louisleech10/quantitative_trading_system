# GAP-3 EVENT SPEC R1 adversarial review — grok

family: grok
task-id: 20260820-GAP3-X-REVIEW-R1
scope: `docs/GAP3_EVENT_SPEC.md` @ `e0af4a3d`（sha256 `d0babfea8f24…`）；對照 `白話說明/GAP-3事件型討論.md` §7.5；禁改碼
brief: `handoffs/20260820-gap3-spec-r1-BRIEF.md`

---

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

## §7.5 逐條對應表（第一項工作）

| 層 | 條目 | SPEC 落點 | 判 |
|---|---|---|---|
| 1 | U1 A/B/C/兩段式；只多或只空；finlab 報酬表 | §A 已確認；B2.1；§N-2 | 沒漏／沒錯 |
| 1 | U2 CSV＋搜尋條件＋實際漲幅 | B1.0 `search_rule_summary`／`label_value` | 沒漏 |
| 1 | U3 先討論 | 已由 8/20「開 SPEC」覆寫；不必進實作 Task | 合理省略 |
| 1 | U4 決策 t₀ open 或 t₀−k；特徵任意 TF；反例種類選填 | D2；AR-1；B1.0／B1.5；AR-2 | 形式待 AR-1；見 P1-01 |
| 1 | U4b 標籤 t₀ close／預設 close_to_close；兩數並排 | D1（改寫 C1 預設）；D1-4；D4-2 | 預設改寫正確；缺錨≠decision 不變式→P1-01 |
| 1 | U5 規模舉例不寫死 | §A；B2.3 tier 降級 | 沒漏 |
| 1 | U6 G1–G6 完整產生器／search | B3.1–B3.2；AR-5 | 落批 OK；驗收表稀疏→P2-05 |
| 1 | U7 升級不翻掉 | B3.2／B5.2 | 沒漏 |
| 1 | U8 LGBM/XGB 不影響設計 | B4.1 | 沒漏 |
| 1 | U9→K3 連續觸發 | B1.2 | 沒漏 |
| 1 | U10 前端三頁落點 | B5.2 | 沒漏 |
| 1 | U11 全 K 線一次建完整 | D4；B2.5 | 沒漏 |
| 1 | U12 多標的必要；#4 邊界 | B1.3；AR-3；§N-5 | 沒漏（邊界交 AR-3） |
| 1 | U13 一份 SPEC＋B1–B5 | §P；AR-4 | 沒漏 |
| 1 | 8/20 五點（提早買／c2c／TF 不寫死／反例選填／規模舉例） | D1／D2／U4／U5／AR-1／AR-2 | 沒漏；c2c⊕t₀−k 交互見 P1-01 |
| 2 | J1 case-control＋全 K 驗證 | D4；J1 敘述於 D4 頭 | 沒漏 |
| 2 | J2 跨 TF；決策前已收盤 | D2 per-TF cutoff | 沒漏 |
| 2 | J3 不切固定窗；取決策列 | B1.1／特徵路徑敘述 | 沒漏（無獨立 Task，可接受） |
| 2 | J4 反例種類分報；＝兩段式合體 | B1.5；B2.2 | 沒漏 |
| 2 | J5 時間出場；TB 殘留 | B2.1；§N-1 | 沒漏 |
| 2 | J6 pooled 最小 | B1.3；§N-5 | 沒漏 |
| 2 | J7 序列 IC 九成可用；補對齊／0-1／報酬表／入口 | B2.*；B5.2 | 沒漏 |
| 2 | J8 IC→ML→全 K 評 | B4.1；B2.5 | 沒漏 |
| 2 | J9 情境維度 | B1.0 `scenario` | 沒漏 |
| 2 | J10 共用條件引擎 | D3；B3.1–B3.2 | 沒漏 |
| 3 | R2 C1→D1（⊕U4b） | §0 D1 | 預設改寫正確；見 P1-01／P1-03 |
| 3 | R2 C2→D2 | §0 D2；B1.1 | 沒漏；`observed_through≤decision_at` 正確一般化 R2「≤t0」 |
| 3 | R2 C3→D3 | §0 D3；B3.1 | 沒漏（編號 D3≠synth「D2」僅改號） |
| 3 | R2 C4→D4 | §0 D4；B2.5 | 沒漏 |
| 3 | R2 C5 | B1.2；§N-4 | 沒漏 |
| 3 | R2 C6 | B1.3；AR-3；§N-5 | 沒漏 |
| 3 | R2 C7 三表／T8-10／DSR | B2.1-3；B1.0；B4.2 | 批號跟 C9 非 C7→P2-04 |
| 3 | R2 C8 K7 | B3.3；FACT bars_since=0 | 沒漏 |
| 3 | R2 C9 分批 | §P B1–B5；AR-4／AR-5 | 沒漏；B3 依賴宣告→P1-02 |
| 4 | R1 六時間欄 | D2-1 | 沒漏 |
| 4 | R1 ms 閘 | D2-3；B1.0⑤ | 沒漏 |
| 4 | R1 taxonomy 正交欄 | B1.0 選填 | 沒漏 |
| 4 | R1 legacy 不沿用（CaseRecord／silent continue／`_select_negative`） | §C；B1.0 不可做；FACT xgb continue；§N-7 platform_* 留位不實作 | **無污染** |
| 4 | R1 C-情境反例／預設 close 決策 | **不取**；D2-2 明寫 A/B 不受 trigger_open 已知限制 | **無污染** |
| 5 | survivor 升版／SplitPlan 不動／capability／CHARTER／GAP-1／成熟度禁區 | B2.4；B1.3；§V；B4.2；§C／§A | 沒漏 |

**污染掃描**: 全文無「換時間戳即可共用 IC」；無沿用 `CaseRecord` 充契約；無 `_select_negative_timestamps` 語意；舊 xgb 精確相等對齊列為不沿用碼證。衝突處新使用者意圖蓋過舊委員結論（C1 預設、t₀−k、A/B 反例）。

---

## AR-1..AR-6 裁決（第二項工作）

### AR-1 — 決策時點 t₀−k 契約形式
**裁決**: 採 **`t0`（錨，epoch ms）＋`decision_offset_bars`（int≥0，預設 0）**；receipt 必寫推導之 `decision_at_ms`。允許選填覆寫 `decision_at_ms` 僅當與 offset 推導一致（否則拒）。`entry_price_semantic` 值集擴 `{trigger_open, trigger_close, next_open, decision_bar_open, decision_bar_close}`。六欄不變式維持，`feature_cutoff[tf]=max{close_ms≤decision_at}`。**硬附加（接 P1-01）**: label 錨永遠 `t0` close；`decision_at < t0` 合法（A/B）；禁止 `decision_at` 列 join `return_N`。  
**理由**: offset 可重現、可審；純 ms 覆寫難審；與 U4「獨立欄＋特徵跟著決策走」一致且不破 C2。

### AR-2 — 反例自動分類
**裁決**: `counterexample_kind` 選填；缺值才跑平台分類；**使用者手標優先**（衝突不覆寫手標）；輸出必帶 `kind_source∈{user,platform_auto}`；門檻入 config（可調），邊界 tie-break＝`unclassifiable`（不猜）。a/b/c 操作定義寫進 B1.0 契約 `_doc`＋B1.5 測試向量。  
**理由**: 符合 U4「選填＋可自動」；避免平台覆蓋使用者標註。

### AR-3 — 多標的必要化與 #4 邊界
**裁決**: 事件型 IC／ML **宣稱**須在多標的合併樣本上跑（U12）；K4 之 macro primary＋micro 敏感度＋time-cluster＋LOSO receipt＋未 cluster⇒`degraded` **足夠**本票。本票**不**關閉 #4、不重建 cross-sectional／GEE（§N-5 成立）。單標的僅允許 exploratory 並標 `degraded:single_symbol`。  
**理由**: 與 R2 C6／U12 一致；邊界清楚。

### AR-4 — 一份 SPEC vs 拆兩份
**裁決**: **維持一份 SPEC＋B1–B5**。產生器＋前端不另拆檔；批間戳記已是閘。若後續 B3 範圍在 TODO 膨脹再評估拆檔——現況未過大。  
**理由**: U13 預設；十六 Task 在單檔可導航；拆檔代價＞收益。

### AR-5 — G1–G6 落批
**裁決**: **維持 B3**（不把 MVP 前移 B2）。B2 已含三表＋survivor＋全 K 線靈魂（C4）；再塞產生器會擠壓 K8 驗收。  
**理由**: 跟 C9 主委交集原則；B2 餘裕不應用來前置 U6 完整版。

### AR-6 — label 一致性探針
**裁決**: **B1 可選 task**（非 B1 出口硬門檻；不進 §N）。範圍限 `price_return_threshold` 一族 vs 契約重算之 close_to_close；誤報⇒報告欄 `label_probe_mismatch`＋loud，**不**自動改使用者 label（v1 仍不重算覆蓋）。Reconcile 後刪 §N-8。  
**理由**: 探針便宜且擋匯入錯誤；放 §N 會丟掉 B1 最早能抓的資料品質閘。

---

## §1 必查摘要（11 類）

1. **矛盾/互斥**: D1 對等欄 vs B1.0 嵌套（P1-03）；B3 依賴 vs G6／B2.5（P1-02）；R2 C7/C9 批號（P2-04）。D1 預設與 U4b 一致。
2. **漏項**: G1–G6 驗收表未展開（P2-05）；其餘 U/J/C/R1 層見對應表——無產品漏項。
3. **不可測驗收**: §G 四類＋M1–M8 具 sha256／atol／rc；可證偽。無。
4. **可疑 quant**: P1-01（c2c⊕t₀−k 錯 join）為本輪主攻。其餘 PIT／分母／角色隔離在 D2–D4 到位。
5. **過度工程**: 無；純函式模組切分合理；未引入分散式。
6. **OOM/並行**: B5.1 萬級牆鐘列偵察；無巢狀池風險。無。
7. **Cache**: 事件契約綁 snapshot digest；不綁 HDF5 佈局（§C）。無。
8. **API/相容**: legacy adapter 顯式；survivor v1→v2；CaseRecord 不充數。無。
9. **測試品質**: 真實 kline golden＋mutation 目錄具體；置亂／PIT／ms／分母／角色／基率／權重皆有 M#。無空殼 §G。
10. **Agent 可執行性**: Task 有檔案＋函式名＋驗證命令；P1-02／P1-03／P2-05 為殘餘歧義。
11. **必要性/短命工**: 逐 Task「存活至／覆蓋風險」已填；B1.4 明寫保留作 oracle 載體、不被 B2.2 刪——無 Phase1-被-Phase3-刪型白工。無額外短命工。

## §2 範本錨點／空殼／§N

- §RISK／§A／§C／§G／§P／§V／§R／§N 皆實填；RISK-HIT a,d ⇒ §G 有數值 token。
- FACT-RECEIPT 15 條：本輪抽樣複驗 `label_generator`／`requests.py` allowed_filtering／xgb continue／CaseRecord／REQUIRED_COLUMNS／UNWIRED／feature_cutoff=0／bars_since=0／ic_models event_*／SplitPlan／survivor keys／template_check → 與宣稱一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`。
- **§N 八條**: (1)(2)(6) user-ruling 成立；(3)(4)(5) blocked-by 成立（#4／資料源／UNWIRED+成熟度）；(7) blocked-by B3 可接受；(8) needs-research:AR-6 → 本輪裁 B1 可選後應刪殘留。**無「該現在做卻偷懶塞殘留」項**（在 AR-6 採可選 task 前提下）。

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 |
|---|---|
| §A 15 條 FACT-RECEIPT | **fact-verified**（本輪抽樣重跑一致） |
| template_check PASS | **fact-verified**（本輪重跑） |
| R2 C1–C9 完整且正確 | **assumed 部分不成立**（C7↔C9 批號张力；P2-04）；SPEC 未照抄錯誤批號 |
| §P 依賴／存活語意正確 | **assumed 部分不成立**（B3 缺 B2 邊；P1-02）；存活欄無短命工白工 |
| D1「條件 IC 直接吃」在 t₀−k 下可直接成立 | **assumed 不成立**（P1-01） |

---

## 必答（brief）

1. **§7.5 表**: 見上。漏＝G 驗收展開不足（P2-05）、D1 錨不變式（P1-01）、B3 依賴（P1-02）、entry 欄位形狀（P1-03）。錯＝未見與 U 系列直接衝突。污染＝未見。
2. **AR-1..AR-6**: 見上節裁決。
3. **D1–D4 合併點**: D2–D4 嚴謹可驗收；**D1 在 t₀−k 交互上尚未「最完整精確」**（P1-01／P1-03）——進 reconcile 寫回後可成立。
4. **§N 三值理由**: 成立；AR-6 裁完後刪 §N-8。
5. **§G／M1–M8**: 可證偽；能抓 silent continue、cutoff 後移、ms 閘、ineligible 入分母、權重全 1、角色檢查移除、基率欄移除、oracle 空心。
6. **能否進 reconcile＋白話閘**: **可以進 reconcile**；**無 P0 須先改稿**。凍結／白話閘前必須處置寫回 P1-01..03；P2 可隨 reconcile 順手改。

## Verdict：可進 reconcile＋白話閘（凍結前須寫回 P1）

需修補後凍結；不需重作 SPEC。對齊 §7.5 整體忠實；主風險在 U4b⊕t₀−k 的 label 錨契約（P1-01）與 §P B3 依賴漏邊（P1-02）。

STATUS: DONE
