使用者可稽核：cat .claude/gate/audit.log
# 分階段 — Composer 2.5（Cursor）

**§0 一句話：有條件同意 Claude——「正確性邏輯先於大尺度」對，但把「大尺度架構」整包丟到 Phase 3 太晚；應改成「薄串流脊骨 + RowMask/split 契約」與 Phase 1 並行，而非 correctness-then-streaming 兩段式。**

---

## 1. §0 核心排序：正確性先修 vs streaming-first

**同意一半，反對「串流整包後置」。**

| Claude 說對的 | 我 challenge 的 |
|---|---|
| FDR 演算法、Net IC 公式、HAC/block bootstrap **語義**不會因串流而報廢 | **接線面**會白做：若 1a 做成「materialize 後切 DataFrame」，串流落地時要重寫成 `RowMaskPlan`（CONVERGED A1/A9 B6） |
| 方法未驗前就全量串流重寫 = 高風險 | 反過來：**不繞 materialize，45K 連 Phase 0 止血後仍不可互動**——scale 不是「未來需求」，是現況 blocker |
| scale-dependent 項可小尺度驗演算法再接串流 | 有些項**不是**「演算法對了再接」，而是**資料契約**：split_id、train-only winsor、per-symbol isolation 必須在 `FeatureMatrixSource` 層定義，晚做 = 雙份 golden |

**會不會白做？分三類：**

1. **不會白做（可先做）**：FDR BH 純函式、Net IC 量綱、factor_attribution 接線、靜默空圖 schema、WS/to_thread。
2. **半白做（介面要對）**：train/test——若只做 post-materialize slice，串流時重做 mask；應直接以 **RowMaskPlan / split_id** 為 1a 交付物。
3. **必須等薄串流（或至少等 direct L7）**：430K 全量 FDR、redundancy O(n²)、Stage4 rolling 前置物化、cross-sectional concat——WHOLEMAP G + CONVERGED A2/A4/A5。

**我的 §0 主張：「雙軌收斂」，不是二選一。**

```
軌 A（正確性語義）: 0 → 1b/1c/1f 幽靈與公式 → 1a 以 mask 契約落地
軌 B（薄串流脊骨）: 0 → direct L7 繞 materialize → Stage A 串流 + candidate cap
收斂點: 1a mask 與軌 B 的 RowMaskPlan 同一抽象；之後 FDR/顯著性只吃 MetricSink
```

純 streaming-first 我不同意（方法紅線未 golden 就上大管線風險高）；純 correctness-first 我也不同意（主戰場事件研究上游仍卡在 45K 假篩選）。

---

## 2. Phase 2（case-control）vs Phase 3（430K）誰先？

**主張：Phase 2「薄 MVP」可與 Phase 3「薄脊骨」並行；全功能 case-control 不應等全量 Phase 3，但「大規模因子宇宙篩選」必須等 Phase 3 Stage A。**

| 維度 | 事件研究（你的主戰場） | 430K×百 symbol |
|---|---|---|
| 列數 | 稀疏、小 | 巨大 |
| 當前 blocker | `event_timestamps` 死線、靜默 fallback 全樣本（WHOLEMAP F） | materialize、無 cap、幽靈 feature_filter（WHOLEMAP G/A） |
| 是否需全量串流 | **否**——事件窗 + 少數候選因子 | **是**——全特徵 screening |

**排序主張：**

1. **先**（與 Phase 1 重疊）：事件路徑 **fail-closed**（不足事件報錯，禁止靜默全樣本）+ `event_timestamps` 接通——這是 P0 正確性，比完整 matching 更急。
2. **並行**：direct L7 + feature_filter 真落地 + Stage A 串流（解「選哪 45K 因子做事件」上游）。
3. **後**：matching、波動率調整、完整 purged event OOS 套件——可分期，不擋薄 MVP。

**反對 Claude「Phase 2 整包在 Phase 3 前/後二選一」。** 你的日常工作流是事件，但事件研究**依賴**「因子從哪來」；45K 幽靈全跑時，事件 IC 的輸入 universe 本身就是錯的。故 **Phase 0 的 IC-FEATURE-GUARD 其實是 Phase 2 的前置，不是純效能**。

---

## 3. Phase 內依賴是否正確？

### 3.1 「1a 是 1b / 1e 前提」——**過強，應拆成「接線」vs「語義」**

| 項目 | Claude 依賴 | 我的判斷 |
|---|---|---|
| 1b FDR | 需 1a | **接線**不需；**報告語義**需（in-sample p 做 FDR 仍會假綠，但比「完全沒呼叫」好）。可 1b-wire ∥ 1a-core，golden 標 `scope=in_sample` |
| 1e 顯著性 HAC | 需 1a | **部分同意**。HAC 修的是 rolling IC 自相關，與 train/test **正交**；與 1a 的關係是「eval window 標籤」，非演算法前提 |
| 1c Net IC | 未寫依賴 | 應 **∥ 1a**；但 slippage_bps 幽靈（WHOLEMAP A）應同捆，否則公式對了 cost 仍假 |
| 1d attribution | 未寫依賴 | 獨立，應 **提前到 Phase 1 前半**（雷達假歸因 = 使用者可見謊言） |

### 3.2 「Phase 2 需 Phase 1a 全部」——**否，需的是子集**

Phase 2 真正硬依賴：

- split / purged 語義（1a 的 **mask 契約**，不是全套 winsorize 管線）
- fail-closed 事件路徑（WHOLEMAP F，Claude 有寫但未標 P0）
- FDR **語義**（事件多重檢定時）

**不需要等**：1f 靜默空圖、1c Net IC、全平台 winsorize 重構。

### 3.3 Phase 0 漏項（依賴圖缺口）

CONVERGED A9 **B7 時間軸秒/毫秒**、**by_volatility fail-closed** 在 crash 分析裡是 P0，Claude Phase 0 只列 GroupedConfig crash，**應併入 Phase 0**（否則 grouped 修了仍軸錯）。  
**turnover.enabled / slippage_bps 幽靈** 未進任何 Phase——應在 Phase 1 前半，與 1c 同 sprint。

---

## 4. 漏排、粒度、工時

### 4.1 漏排或歸位模糊

| 發現 | WHOLEMAP | Claude 計畫 | 建議 |
|---|---|---|---|
| cross-sectional 空殼 (H) | ②-④ 多分析回空 | 未單列 | 併入串流軌 **S3**，或標「模式限制」產品決策 |
| Pooled/Panel IC (①3) | ❌ | Phase 4 | 若主戰場是事件+panel，可升到 Phase 2 後段 |
| walk-forward / purged CPCV 孤島 | ③ | Phase 2 順帶 | 應明確：**复用 ML 孤島** vs **重寫**——工時差 3-5× |
| IC-PERF cancel / stage4 進度 | crash P1 | 未列 | Phase 0.5 UX，否則 45K 仍「可跑但不可中止」 |
| preview_limit 改名 | CONVERGED A8 | Phase 0 feature_guard | 同意，但需 API schema 版本化（CONVERGED C4） |

### 4.2 Phase 切太粗

- **Phase 1 六項一籃**：建議拆 **1-wire（FDR/attribution/幽靈 toggle）** vs **1-split（mask + winsor train-only）**——前者 3-5d，後者 1-2w（碰 orchestrator + golden）。
- **Phase 4 混產品與研究嚴謹度**：IC→ML 橋（產品）vs DSR/PBO（研究）應分 Phase，使用者價值曲線不同。

### 4.3 工時量級（粗估，供收斂）

| Phase | Claude 標籤 | 我的估計 | 備註 |
|---|---|---|---|
| 0 止血 | 小 | **3-5 人日** | 合理；加 B7/by_volatility +1-2d |
| 1 正確性 | 中 | **2-4 週** | Claude 低估；1a 若碰全 orchestrator + golden |
| 2 case-control | 大 | **4-8 週** | 六子能力全做是獨立 epic；薄 MVP 2 週可交付 |
| 3 大尺度 | 大 | **4-6 週** | CONVERGED E2-E6；可拆 S1(1w)/S2(2w)/S3(2w) |
| 4-5 | 中-大 | **各 2-4 週** | Agent 層強依賴 1+結構化輸出，不宜更早 |

---

## 5. 我的 Phase 排序（可執行版）

### Wave 0 — 能用（3-5d，無爭議）
IC-CRASH · IC-FEATURE-GUARD · IC-UX-ERR · decay log 聚合 · **B7 timestamp** · **by_volatility fail-closed**

### Wave 1 — 能信（雙軌並行，2-3w）

**軌 A — 語義/接線（可小 run golden）**  
1d attribution 或 UI 標 proxy · 1b FDR 接線（標 in_sample）· 1c Net IC + slippage · 1f 靜默空圖 · turnover 幽靈

**軌 B — 薄串流脊骨**  
direct L7 繞 materialize · Stage A exact IC + MetricSink · redundancy/candidate cap 200

**軌 C — 事件止血（主戰場前置）**  
event_timestamps 接通 · 事件不足 **fail-closed**（禁靜默全樣本）

### Wave 2 — 主戰場 MVP（2-3w，依賴 Wave 1 的 1a-mask + 軌 C）
顯式事件清單 ingestion · 事件前窗對齊 · 基礎 case-control IC · 事件 OOS（purged CV 最小版）· 事件維度 FDR

### Wave 3 — 規模完備（2-4w，與 Wave 2 尾段重疊）
Stage B candidate-only deep · cross-sectional exact · 輸出 top-N + Parquet artifact · resume/checkpoint

### Wave 4 — 整合研究（2-4w）
1e HAC/block bootstrap（rolling）· IC→ML 橋 · 多因子組合/邊際 IC · Pooled IC

### Wave 5 — 策略層 + Agent（之後）
DSR/PBO/MinBTL · 結構化 IC 報告 · Agent 顧問層

---

## 6. 與 Claude 方案對照（決策表）

| 決策點 | Claude | Composer 2.5 |
|---|---|---|
| §0 總序 | 正確性 → 大尺度後置/平行 | **雙軌收斂**；薄串流脊骨與 1a **同週啟動** |
| 2 vs 3 | 留給委員會；隱含 2 在 3 前 | **2 薄 MVP ∥ 3 薄脊骨**；全量 screening 等 S2 |
| 1a→1b/1e | 硬依賴 | **接線可並行**；語義/標籤依賴 1a-mask |
| Phase 0 | 4 項 | **+B7 +by_volatility +（可選）cancel** |
| 最大風險 | 1a 做在錯抽象上 | **1a 必須產出 RowMaskPlan 契約**，否則串流時重做 |

---

**收斂建議（給使用者拍板的一題）**：  
是否接受 **「Wave 1 雙軌」**——一邊修公式/幽靈/事件 fail-closed，一邊上 direct L7 + Stage A，以 **同一 mask/split 契約** 收斂——而不是「先把 Phase 1 全做完再開 Phase 3」？  
這一題定案後，其餘 Phase 內順序可機械展開成 SPEC/TODO。
