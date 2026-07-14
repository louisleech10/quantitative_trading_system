# IC1C SPEC r2 閉合重驗 (Composer)

Task-id: IC1C-SPECREV-R2 | Reviewer: composer | Date: 2026-07-14  
SPEC: `docs/IC1C_NETIC_SPEC.md` v0.2 r2 | r1: `handoffs/20260714-IC1C-SPECREV-composer.md`  
RECONCILE: `handoffs/20260714-IC1C-SPECREV-RECONCILE.md` (17 筆全 ACCEPT)

---

## 1. r1 Finding 逐一閉合

| ID | r1 嚴重度 | 判決 | r2 對應段落 | r1 反例在 r2 下是否仍可構造 |
|----|-----------|------|-------------|---------------------------|
| COMPOSER-1 | BLOCKING | **CLOSED** | §A RULING-FINAL B-strict; Task 1.2(:80-82) fail-closed `unavailable+reason`; 拆票 1c-FR(:102-103); RECONCILE F1 | **否**。r1 反例=直接 `batch_analyze(..., factor_returns=dict)` → TypeError / `net_mean` e2e。r2 明確「不傳 factor_returns」、刪 finite-float e2e、改斷言 `status==unavailable`。codex 勝訴（ls_returns 錯位）合理，export-series 移 1c-FR 前置，非曲解。 |
| COMPOSER-2 | BLOCKING | **CLOSED** | Task 1.2(:80-82) 依賴矩陣「1c 內 net_ic 不依賴 factor_return」; 輸出顯式 unavailable; RECONCILE F2 | **否**。r1 反例=兩模組全綠但 `net_factor_return` 鍵永不出現（靜默）。r2 要求鍵存在且 `reason` 非空；通道實作延後 1c-FR，1c 範圍內 fail-closed 可接受。 |
| COMPOSER-3 | BLOCKING | **CLOSED** | §C(:31-51) 完整 manifest 16 項; RECONCILE F8 | **否**。r1 列之 ic_reporter/frontend/types/tests/factories/turnover proxy/NetICChart 0.1 fallback 均已入表；僅改 §C 舊檔仍假綠之路徑被 manifest+§V 改寫表封死。 |
| COMPOSER-4 | BLOCKING | **CLOSED** | Task 2.1(:89-94); §R(:126-127); §V M5/M7; RECONCILE F4/F12 | **否**。r1 三層 5bps fallback+override 繞過：r2 刪 schema/YAML/analyzer 預設、typed nested request、HTTP 邊界 422、override reject、`cost_enabled` default=False。§R 釐清 `modules.net_ic_analysis=True` 且無成本欄=gross-only 無幽靈 5bps，解 r1 §R 矛盾。 |
| COMPOSER-5 | BLOCKING | **CLOSED** | §G(:53-63); Task 1.1 summary 契約; RECONCILE F7 | **否**。r1 反例=改 gross_ic 來源(:1947) golden 仍綠。r2 全鍵集合 equality+canonical 全量重算+不變欄 byte 級+mutation 綁定；`avg_ic_loss_pct`/舊 rank_corr 刪除；skipped 入 G-OLD。 |
| COMPOSER-6 | BLOCKING | **CLOSED** | Task 1.1(:72-76) 禁 `net_ic` 鍵含別名; Task 2.2 軸改 cost_drag; Task 3.1 sensitivity 改掃 cost_drag; RECONCILE F5/F6 | **否**。r1 反例=保留 `net_ic` 別名少改前端。r2 F6「裁死」刪鍵+M1 全樹 grep；圖表/reporter 改名列於 §C+Task 2.2。 |
| COMPOSER-7 | NON-BLOCKING | **CLOSED** | §A RULING-FINAL B-strict; §A 案 A 封存(:23); RECONCILE F13 | N/A（裁決項）。三家收斂 B+codex fail-closed，與 r1 RULING:B 一致且更嚴。 |
| COMPOSER-8 | NON-BLOCKING | **CLOSED** | §V(:105-122) M1–M8 property 矩陣+改寫表; RECONCILE F10 | **否**。M5–M7 補齊；phase24 `default==5`/export fixture/proxy 四腿計費均列為「舊斷言錯」。 |
| COMPOSER-9 | NON-BLOCKING | **PARTIALLY** | §T(:25-29) `turnover_semantics`; Task 3.1(:99-100); RECONCILE F11 收斂 | **邊際可構造**。持倉 1w/rebalance 12h 使用者仍可能誤讀 per-rebalance drag；r2 已加雙 semantics+禁年化 UI 註記，持有期矩陣依 reconcile 不入 1c→1c-FR。殘留為產品教育風險，非 SPEC 缺口。 |
| COMPOSER-10 | NON-BLOCKING | **CLOSED** | Task 1.1 邊界 turnover=0→null+reason; Task 1.2 依賴矩陣; F9 RECONCILE | **否**。breakeven inf→null+reason；factor_return 關/net_ic 開→unavailable 非 e2e 衝突。 |

**r1 BLOCKING 6/6 → CLOSED。NON-BLOCKING 3 CLOSED + 1 PARTIALLY（可接受）。**

---

## 2. RECONCILE 曲解檢查

| 主題 | 判定 |
|------|------|
| F1 / COMPOSER-1 + codex fail-closed 拆 1c-FR | **無曲解**。RECONCILE 正確記錄：我 r1 首選 export `ls_return_series` 被 codex 錯位實證否決；1c 改 unavailable 佔位、canonical 構造獨立拆票。 |
| F3 去 ×2 | 非我 r1 主 finding；§T 公式 `cost_bps×turnover`+M8 與 codex 證據一致。 |
| F11 持有期矩陣不入 1c | **無曲解**。我 r1 建議可選「有效持有期」欄；reconcile 收斂為 semantics 標籤+1c-FR 矩陣，屬範圍裁決非扭曲原意。 |
| F2 / COMPOSER-2 | **無曲解**。接受「1c 內不依賴 factor_return」+1c-FR 前置，與我建議的硬依賴+skipped 在 1c 語意下等價（unavailable 取代靜默 skip）。 |

---

## 3. r2 新引入洞（本輪新 finding）

### COMPOSER-R2-1 — `net_factor_return` 佔位形狀 Task 1.1 vs 1.2 略不一致

**嚴重度**: NON-BLOCKING

**證據**: Task 1.1(:73) schema 速記 `net_factor_return: null+reason`; Task 1.2(:81) 具體 `{"status":"unavailable","reason":"..."}`; F9 DTO 講 scalar `number|null+reason`。

**反例**: 實作者依 1.1 輸出頂層 `reason` 字串 vs 依 1.2 輸出 status 物件 → 前端/types 契約分裂。

**建議**: TODO 生成時統一為單一 `MetricUnavailable{status,reason}` 形狀（與 breakeven 等 null+reason 同 pattern）。

### COMPOSER-R2-2 — route 422 無獨立 Task bullet

**嚴重度**: NON-BLOCKING

**證據**: §C#10 + Task 2.1 要求 HTTP 邊界 422；現 `api/routes/ic_analysis.py:107-118` 僅轉發 service（r1 先 200 後驗路徑）。SPEC 未列獨立「改 route」子任務。

**反例**: 僅改 service 背景驗證、route 不攔 → M4/M7 假綠。

**建議**: `IC1C_NETIC_TODO.md` Task 2.1 子項明列 route pre-validate 或 Pydantic 在 FastAPI 層同步 422。

### COMPOSER-R2-3 — Phase 1 summary `profitable_count`/`evaluable_count` 恒 0 的 UI 語意

**嚴重度**: NON-BLOCKING

**證據**: Task 1.1(:75) `evaluable_count` 在 1c 恒 0、`profitable_count` 只計 evaluable → 1c 內恒 0。

**反例**: UI 顯示「0 個盈利因子」被讀成「全虧」而非「尚未建立報酬序列(1c-FR)」。

**建議**: Task 2.2 或 types 加 `summary.evaluation_status: "awaiting_1c_fr"` 或隱藏 profitable 區塊至 1c-FR。

---

## 4. 閉合重驗摘要

| 類別 | 計數 |
|------|------|
| r1 BLOCKING 關閉 | 6/6 |
| r1 NON-BLOCKING 關閉 | 3/4（COMPOSER-9 PARTIALLY 可接受） |
| r2 新 finding BLOCKING | 0 |
| r2 新 finding NON-BLOCKING | 3 |
| RECONCILE 曲解 | 0 |

**實碼抽驗（唯讀，驗證 r2 仍描述現況 bug）**: `net_ic_analyzer.py:81` 仍 `compute_net_ic`; `ic_config_schema.py:268` 仍 `default=5.0`; `NetICChart.tsx:13,25` 仍 `useState(5)`+turnover fallback 0.1; `_run_net_ic` 仍未傳 factor_returns(:1956)。符合預期——本輪審的是 SPEC r2 閉合度，非實作完成度。

```
ASSUMPTIONS_VERIFIED: docs/IC1C_NETIC_SPEC.md v0.2 全文; RECONCILE 17 筆對照; r1 十筆反例逐條映射; grep 現碼與 r1 證據一致
TESTS_RUN: 未跑 pytest（SPEC 閉合唯讀審）; shasum RECONCILE
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: r2 定義新 schema（禁 net_ic、cost_drag_return、unavailable 佔位）—審查確認閉合，待實作
```

SPEC-REVIEW-R2: APPROVE
RECONCILE-STAMP APPROVED — composer 2026-07-14 sha256:d94d4c14cfa8f88abea661f72a725ae7a44b45e7c371c8dc945dd61d614b72e7
