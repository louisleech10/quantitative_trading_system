# IC1C SPEC r5 delta concur — grok

**task-id**: IC1C-SPECREV  
**角色**: r2 原 APPROVE 委員（delta concur：r3–r5 修訂 vs r2 戳記）  
**輸入**:
- `docs/IC1C_NETIC_SPEC.md` **v0.5 r5**
- `handoffs/20260714-IC1C-SPECREV-R2-grok.md`（本家 r2 APPROVE+STAMP）
- `handoffs/20260714-IC1C-SPECREV-R{3,4,5}-codex.md`
- `handoffs/20260714-IC1C-SPECREV-RECONCILE.md`（含 r3–r5 裁決 F14–F26）
**約束**: 除本檔外未改任何檔；review-only；未跑實作 pytest/vitest  
**RECONCILE 現值 sha256**（`shasum -a 256`）: `d71c4ee1b5a55a993a92c3ff5de1d9c36d411b969d0dbf9f7fd68ed33a26096d`

---

## 1. (a) r3–r5 修訂 vs r2 APPROVE 相容性

| delta（任務列） | 落點（v0.5） | 與 r2 APPROVE / B-strict |
|-----------------|-------------|---------------------------|
| §U 統一佔位 | L34 discriminated union；存在時形狀唯一 | **相容且加嚴** r2 主路徑（fail-closed 佔位）；收 GROK-R2-1 |
| 三 profile | L35–39 SKIPPED/GROSS_ONLY/COST_ENABLED 精確鍵集；§G equality 唯一 oracle | **相容且加嚴**（r2 已有「無 cost 子樹」意圖）；收 GROK-R2-2 |
| finite validator | L41：`0 < cost_bps ≤ 1000` 三層；非有限 turnover→SKIPPED；M10 | **相容**（禁 JSON NaN/inf + 無幽靈預設之超集） |
| 階梯移 Phase 1 | §T L30 + Phase 1 實作；Phase 3 零 schema（L111–113） | **相容**；消除 phase 倒置，不削弱 GROK-7（持有期矩陣仍不入 1c） |
| M9–M10 / T4–T5 probe | §V L129–136；T4 vitest 同檔 probe；T5 config 層 | **相容**；強化 GROK-6 閉合（B1.1 自證） |
| cost_bps=0 非法 | L41/L89/L130/L141；無成本=`cost_enabled=False` | **相容**；r2 戳記不依賴「0 合法」；與 GROK-2 開關語意一致且更乾 |

**結論 (a)**：六項 delta 均為 r2 B-strict 之超集或序列化修訂，**無弱化、無曲解 r2 APPROVE 前提**。

---

## 2. (b) 原 10 個 CLOSED finding 是否被破壞

逐條以 r1 反例在 **v0.5** 下可否再構造（章程：不憑「已修」信任）：

| ID | r2 判定 | v0.5 重跑 | 說明 |
|----|---------|-----------|------|
| GROK-1 | CLOSED | **仍 CLOSED** | Task 1.2 不傳 factor_returns；net 恒 unavailable 物件；禁 ls_mean 代填（L22/L90/L93） |
| GROK-2 | CLOSED | **仍 CLOSED** | cost_enabled default False；三處 5.0 刪；override 整節 reject；前端硬編 scenarios 刪；**0 非法**不開幽靈路徑 |
| GROK-3 | CLOSED | **仍 CLOSED** | summary：`avg_cost_drag_return`；rank_corr 刪；profitable 只計 evaluable（L87）；M6 |
| GROK-4 | CLOSED | **仍 CLOSED** | §G 全鍵==profile + canonical 無×2 重算 + G-OLD/G-NEW/G-NEW2；禁混減 mutation M1/M2 |
| GROK-5 | CLOSED | **仍 CLOSED** | §C consumer-map 完整；proxy 入 1c（Task 1.3） |
| GROK-6 | CLOSED | **仍 CLOSED** | M1–M10 具名 test+同檔 probe；T4 前端 probe 補齊 CODEX-7 殘洞 |
| GROK-7 | CLOSED | **仍 CLOSED** | 持有期矩陣不入 1c；階梯=成本 bps；禁年化/跨 TF（§T/§P/1c-FR） |
| GROK-8 | CLOSED | **仍 CLOSED** | `net_ic` 鍵全樹禁（L86）；M1 |
| GROK-9 | CLOSED | **仍 CLOSED** | slippage 刪；e2e unavailable；factor series N/A |
| GROK-10 | CLOSED | **仍 CLOSED** | §A 案 A 封存條件仍在（L23） |

**原 BLOCKING/CLOSED 復開數: 0**

---

## 3. (c) GROK-R2-1/2/3/4 是否已被 §U + Task 1.2 收掉

| ID | r2 嚴重度 | 殘留反例（r2） | v0.5 是否可再構造 | 判定 |
|----|-----------|----------------|-------------------|------|
| **GROK-R2-1** | NON-BLOCKING | 實作 A=`null`+頂層 reason vs B=status 物件皆可稱符合 | **否**。§U L34 唯一 union；禁裸 null/裸 number；Task 1.1/1.2 寫死 status 物件；M9+probe | **CLOSED** |
| **GROK-R2-2** | NON-BLOCKING | 滿鍵 null vs 省略 cost 鍵 vs §G 單一 equality 互撞 | **否**。三 profile 精確集合；GROSS_ONLY 明文無 cost 子樹；§G 依 profile 選集 | **CLOSED** |
| **GROK-R2-3** | NIT | `compute_net_factor_return` 公開面與「1c 恒 unavailable」並存誤導 | **否（語意已釘）**。Task 1.1 L84：deprecated + `batch_analyze` 忽略注入 + conditional 恒 unavailable | **CLOSED** |
| **GROK-R2-4** | NIT | 「來源不存在」→誤刪 FactorReturnAnalyzer | **否**。Task 1.2 L93：canonical series 未建立；模組存在且不動、勿誤刪 | **CLOSED** |

RECONCILE F14/F15/F19/F20 對上列之映射**未曲解** grok 原意（union 形狀 / 雙→三 profile / 用語 / deprecated）。

---

## 4. r3–r5 delta 新洞掃描

- 重跑 codex 已 CLOSED 之結構洞（union vs presence、階梯 phase、finite、T4 probe、cost=0 三處、M10 三層 probe）：v0.5 條文下**原反例均不可再構造**（與 R5-codex 一致）。
- **未發現新 BLOCKING**。
- **NIT（不阻擋 APPROVE，非原 R2 復開）— GROK-R5-1**：合法域 `0 < cost_bps ≤ 1000`（L41）與階梯 clamp 下界 `0.1`（§T L30）不對稱。當 `0 < c < 0.1` 時，scenarios 全被抬到 ≥0.1，操作點 `c` 本身可不在 sensitivity 集合內。建議 TODO 二選一微齊：min cost_bps=0.1，或 scenario clamp 下界對齊域下界（例 1e-6/0.01）。**非正確性紅線、無雙 oracle 衝突**。

---

## 5. 面向總表（delta concur）

| 項目 | 結果 |
|------|------|
| r2 APPROVE 相容 | **是** |
| GROK-1..10 復開 | **0** |
| GROK-R2-1..4 | **全 CLOSED** |
| 新 BLOCKING | **0** |
| 新 NIT | GROK-R5-1（clamp vs 域下界，可 TODO 順手） |

---

## 6. Verdict

r3–r5 將本家 r2 的 NON-BLOCKING/NIT 起草歧義（R2-1/2/3/4）收成可證偽契約，並以 finite 三層、階梯 Phase 1、T4/T5 probe、`cost_bps=0` 非法補上 codex 後續結構洞；**不破壞** r1 十條 CLOSED，**不弱化** B-strict。唯一新觀察為 scenario clamp 與域下界微不對稱（NIT）。**DELTA-CONCUR: APPROVE**。

```
ASSUMPTIONS_VERIFIED: r2 GROK-1..10 反例 + GROK-R2-1..4 殘留反例在 v0.5 §A/§T/§U/§G/§P/§V 重跑；r3-r5 六項 delta 與 RECONCILE F14-F26 落點交叉比對；cost_bps=0 三處(§U/Task1.1/§V)一致；M10 T1/T2/T5 各有 test+同檔 probe；RECONCILE 現值 sha256=d71c4ee1b5a55a993a92c3ff5de1d9c36d411b969d0dbf9f7fd68ed33a26096d
TESTS_RUN: review-only；`shasum -a 256 handoffs/20260714-IC1C-SPECREV-RECONCILE.md`→d71c4ee1…096d；`nl -ba docs/IC1C_NETIC_SPEC.md`→151 行核 §U/§T/§V/Task1.1-1.2；未跑未實作 pytest/vitest
FAILURES_SEEN: none（無舊 finding 復開；無新 BLOCKING）
SCOPE_CHANGES: none；唯一產出本檔
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）；註：r5 裁 cost_bps=0 非法屬契約收斂，非本家 r2 依賴之合法路徑
OUTPUT_PATH: handoffs/20260714-IC1C-SPECREV-R5-grok.md
```

DELTA-CONCUR: APPROVE  
RECONCILE-STAMP APPROVED — grok 2026-07-14 sha256:d71c4ee1b5a55a993a92c3ff5de1d9c36d411b969d0dbf9f7fd68ed33a26096d

STATUS: DONE
