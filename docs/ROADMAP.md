# ROADMAP — 量化交易系統戰術路線圖
> 單一現役戰術 roadmap。**即時任務狀態**看 `HANDOFF.md`；**決策理由**看 memory；本檔=中長期 epic 排序與範圍。
> 維護:完成項移到「已完成」、新需求加到對應優先級、範圍/決策變更標日期。最後更新 2026-06-23。

當前階段:**V1.0 工具階段** — crypto 單市場研究管線(探索 → 發現 Pattern → ML 優化 → 回測)。願景 V1→V2→V3 見 `PRODUCT_VISION.md`。

---

## 🔥 進行中 / 下一步（優先序）

### P0 — IC Gatekeeper 開發 + 真實端到端測試
- **為何**:FF 已收尾,pipeline 下一站。現況 79 IC 單元測試**全合成資料**,從未真實 kline 端到端驗證。
- **範圍**:限 crypto(三方 2026-06-17 定,見 [[project-datasource-ff-ic-assessment]]);真實 kline 跑 IC Gatekeeper(12+10 模組) 端到端 + 驗證。
- **狀態**:未啟動。

### P1 — Productionization Epic（全棧參數持久化）★上線前置
- **為何**:任一特徵/模型要上線推論前必做,否則 train/serve 分布偏移、模型靜默失效。三方三輪盤點 CONVERGED。
- **權威範圍清單**:`docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md`(全棧三層)。
- **子項(優先序)**:
  1. **fracdiff d\* 持久化 / 固定參考**(最高;同時解 cross-window 可重現 + train/serve;見 [[project-dstar-first500-optiona]])。大任務,命中 (d),走完整管線。
  2. A-schema:訓練特徵清單 pin(上線同欄位)。
  3. A4 safe_denominator 改 causal;A5 labels winsor 改 train-split 或棄用。
  4. B 累積(OBV/AD/ADOSC/SAR)一致 reset + state;C L5 reference 可得性。
  5. IC/ML 層:模型權重 + scaler 統計 + 選中特徵集 + 校準映射 隨模型留存。
  6. Optimization 層:Optuna best params 隨部署留存。
- **狀態**:盤點完成(inventory),修法未啟動。V1 未上線故非急,**上線觸發即啟動**。守則已加 serving-parity 判斷樹(`FEATURE_DEVELOPER_CHECKLIST.md`)防新組件再引入未留存參數。

---

## 🅿️ 已決定擱置（非急,有觸發再啟）
- **B7 L6.5 並行**(P2):MTF 細→粗罕見,ThreadPool 需 nogil 才 4.3x。見 [[project-mtf-direction-b7-parked]]。
- **T-A per-layer 串流釋放**(P1,磁碟):scaffold 已存,砍 RSS 峰值根本解。磁碟再緊則啟。
- **T-B float16 暫存 / T-D 28GB 取證 / gstack 清理**:低優先。
- 既有壞測試:`frontend/src/__tests__/strategy-components.test.tsx` 缺 SignalTooltip(可另開小修)。

---

## 🔭 未來 Epic（更遠,待 V1 穩固）
- **多資產擴充**:台指期 / 美指期 + 基本面/總經/月季報/籌碼/三大法人。核心=**PIT 對齊**(公告時戳 + vintage),幾乎全「粗→細」(見 [[project-mtf-direction-b7-parked]])。新數據源另立 epic。
- **V2.0 對話式研究** / **V3.0 自主研究員**(見 PRODUCT_VISION)。

---

## ✅ 近期已完成（2026-06）
- **FF 一致性整併**:Q5/B1/B2/B3/B5/B6/B4/B8(觀測性 + 批次日期修復 + warmup-then-trim + 批次刪除/保留 UX)。每項走完整管線。
- **Feature Explorer 圖表修復**:Y 軸貼合線 + Shift+滾輪 Y 縮放(rolling band 不撐爆 domain)。
- **d\* 實證量化**:三方證 Option A 非二階(cross-window selection 不穩),固定參考為修法(納入 P1 epic)。見 [[project-dstar-first500-optiona]]。
- **上線須留存參數盤點**:三方三輪 CONVERGED,產出 P1 epic 的精確範圍清單。見 [[project-stateful-param-audit]]。
