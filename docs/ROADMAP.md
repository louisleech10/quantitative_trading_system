# ROADMAP — 量化交易系統戰術路線圖
> 單一現役戰術 roadmap。**即時任務狀態**看 `HANDOFF.md`；**決策理由**看 memory；本檔=中長期 epic 排序與範圍。
> 維護:完成項移到「已完成」、新需求加到對應優先級、範圍/決策變更標日期。**每次 commit 一併更新本檔**(2026-06-26 使用者定)。最後更新 2026-07-02。

當前階段:**V1.0 工具階段** — crypto 單市場研究管線(探索 → 發現 Pattern → ML 優化 → 回測)。願景 V1→V2→V3 見 `PRODUCT_VISION.md`。

---

## 🔥 進行中 / 下一步（優先序）

### P0 — 驗收防偽閘 verify-gate（2026-07-01 FF 驗收捏造事故後立,擋「宣稱已驗≠真驗」）
- **範圍**:`docs/VERIFY_GATE_SPEC.md` v2.1(P0-FF-3「align mutation真紅」不實事故 → run receipt + claim checker + enforcement 三層)。
- **狀態(2026-07-02)= epic B1-B5 全落地**:B1 receipt(`d3870c4`)、B2 claim checker(`a1d3638`,V7誤報=0)、B4+B5 provenance/RESULT硬欄位(`6c0a6b0`,Codex 6 BLOCKING 閉合)、B3 enforcement 三層+health(本次 commit;Codex 4 BLOCKING 閉合檔載「FINAL VERDICT: APPROVED」;governance 75 tests VERIFY:20260701T235954Z-governance-b3-final)。PreToolUse hook 已生效;git hooks 用 `bash scripts/install_verify_hooks.sh` 安裝。殘餘=誠實邊界(careless-proof+tamper-evident,非防惡意)。
- **全系統紅隊 ✅(本次 commit)**:三方(Claude+Codex+Composer)紅隊抓 7 洞(env-prefix繞閘/docs走私/模糊洗白/假歸屬自我認證/路徑正規化/無逃生程序/provenance未接線),全修+Codex閉合R1-R7 CLOSED;淨判斷「仍有洞需緊>過嚴」。88 governance tests。
- **接續**:FF P0-FF-3 用帶 receipt 管線重驗(5 mutation 探針已真跑通過 VERIFY:20260702T020806Z-mutation-test_ff_multitf_truncation_mr;B2 回歸進行中)。

### P0 — IC Gatekeeper 開發 + 真實端到端測試
- **為何**:FF 已收尾,pipeline 下一站。現況 79 IC 單元測試**全合成資料**,從未真實 kline 端到端驗證。
- **範圍**:限 crypto(三方 2026-06-17 定,見 [[project-datasource-ff-ic-assessment]]);真實 kline 跑 IC Gatekeeper(12+10 模組) 端到端 + 驗證。
- **★施工藍圖(2026-06-24 四家委員會地圖)**:`handoffs/20260624-ic-map-WHOLEMAP.md`(5 階段 28 種分析全棧盤點 + 系統性發現 A-H)。盤出主流程**幾乎無防偽護網**:
  - **🎯 絕對優先(正確性紅線/生死)**:事件 case-control 套件(主戰場全缺)、train/test 切分(主路徑無)、FDR 接線(幽靈,43萬≈21,500假陽性)、Net IC 量綱錯誤、factor_attribution NaN 繞過。
  - **🚨 P0 止血**:grouped/decay 崩潰、幽靈開關群(feature_filter/turnover/slippage)、靜默空圖、大尺度 cap。
  - **大尺度(430K)架構**:見 `handoffs/20260624-ic-optimization-CONVERGED.md`(串流分塊不物化全矩陣)。每優先項走完整 SPEC 管線。
- **分階段執行計畫(四家收斂)**:`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`(七 Phase,contract-first+雙軌)。
- **決策**:walk-forward/CPCV **复用 ML 孤島**非重寫;contract-first 不硬接舊全 DataFrame 路徑。
- **狀態(2026-06-26)**:
  - **Phase 0 止血+正確性硬閘 ✅ 完成**(commit `11507f5`):CRASH/TIMEAXIS/BYVOL/FEATURE-GUARD/DECAY-LOG/UX-ERR 六 epic + 實機 45k smoke。
  - **Phase 1 正確性 kernel + contract 🔵 進行中**:
    - **1-contract ✅ 完成**(commit `e857834`):契約 DTO + 洩漏紅線(三方簽核,8 LEAK 全閉)+ Parquet artifact + API 版本化。
    - **1a 第一刀(單幣縱向接線)✅ 完成**:契約紅線接進 IC 主流程 `analyze()`——holdout 切分 + train-only fit(winsor/std/coverage/constant)+ OOS 報告 + purge≥horizon 防前瞻 + allowed_symbols/expected_freq 落實。**兩輪雙家族 adversarial(9 BLOCKING)+ 三方數據簽核 PASS(R1 抓 2 LEAK→修→R2)+ G-NEW 真實全 run 抓 2 整合 bug→修。default ON,OOS 不可行時分因回退(資料不足→full-sample 標記;時間軸壞→fail-closed)**。docs/IC_PHASE1_1a_CUT1_{SPEC,TODO}。
    - **下一段 = 1a 第二刀(cross_sectional `analyze_cross_sectional` 防洩漏)**;續 1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖。
  - Phase 2A(事件 case-control 主戰場)/Phase 3(430K 串流)/2B/4/5 未啟動。詳 phasing-CONVERGED 七 Phase。

### P0.5 — IC 效能 + grouped_ic 崩潰止血(已盤點,可立即動)
- **為何**:使用者實測選 run 跑 analyze 卡死+崩潰;三方 reconcile 完成。
- **Epic**:`handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`(IC-CRASH/IC-FEATURE-GUARD/IC-UX-ERR=P0;IC-PERF=P1)。**狀態**:reconcile 完成,實作未啟動。

### P2 — IC 輸出 Agent-readable + 顧問層(V2 願景地基)
- **為何**:使用者要 AI Agent 直接讀 IC 輸出、像委員會討論、回饋「哪些特徵/參數真的較好」+ 點破盲點。**前提=先修上面正確性**(否則 Agent 讀到污染數字會自信推薦過擬合假因子)。
- **範圍**:① IC 輸出結構化可機讀(穩定 schema);② 輸出含 FDR/OOS/DSR 嚴謹度指標(讓 Agent 分辨真好 vs 過擬合);③ Agent 解讀/委員會式討論層。**依賴**:P0 正確性紅線。**狀態**:概念,未規劃。

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
- **FF preset 盤點/移除**（2026-06-29 使用者提,B2 後啟）：未用/未測 preset(professional_full / ml_optimized / trend_focused / intermediate_research / fibonacci_full / basic_essential…)= 死碼/可能 config bug 的未測路徑。使用者從沒用過 professional_full、想移除但未討論。**範圍**:盤點每 preset 有無真 caller、前端真送哪些、哪些從沒被測 → 給清單再決定移除。命中跨模組共用路徑(config_manager/前端 toggle)→ 走完整管線。B2 因果測試已改 base/full 全特徵(不綁 preset)。
- **多資產擴充**:台指期 / 美指期 + 基本面/總經/月季報/籌碼/三大法人。核心=**PIT 對齊**(公告時戳 + vintage),幾乎全「粗→細」(見 [[project-mtf-direction-b7-parked]])。新數據源另立 epic。
- **V2.0 對話式研究** / **V3.0 自主研究員**(見 PRODUCT_VISION)。

---

## ✅ 近期已完成（2026-06）
- **FF 一致性整併**:Q5/B1/B2/B3/B5/B6/B4/B8(觀測性 + 批次日期修復 + warmup-then-trim + 批次刪除/保留 UX)。每項走完整管線。
- **Feature Explorer 圖表修復**:Y 軸貼合線 + Shift+滾輪 Y 縮放(rolling band 不撐爆 domain)。
- **d\* 實證量化**:三方證 Option A 非二階(cross-window selection 不穩),固定參考為修法(納入 P1 epic)。見 [[project-dstar-first500-optiona]]。
- **上線須留存參數盤點**:三方三輪 CONVERGED,產出 P1 epic 的精確範圍清單。見 [[project-stateful-param-audit]]。
