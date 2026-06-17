# Handoff
**Agent**: Claude | **Time**: 2026-06-17 | **Branch**: main

## 本輪完成:#4 batch_alias Phase 1+2(批次一次命名,解 100 symbol 改名 100 次)
完整中-大管線走完,**Codex code review APPROVE**,本 commit 收尾。
- **規格**:SPEC/TODO/MANIFEST V4(docs/BATCH_ALIAS_*.md),經 **4 輪 Codex adversarial**(r1 FAIL 2B/4M/2m → r2 → r3 → r4 PASS),每輪抓真實缺口逐輪收斂:batch_id 跨進程鏈→禁 mutable self 顯式穿透→multi-TF 主路徑遺漏→6 個 _layer7 呼叫點全涵蓋。
- **實作**:Composer 2.5 寫 P1(後端 registry/API/cleanup)+P2(前端 Explorer/Run 管理分組+整批 rename)。
- **協調者驗收抓並修 3 bug(防假綠生效)**:① registry.add 新 entry 無條件 pop batch_alias→僅 batch_id is None 時 pop;② 前端新測試漏 import jest-dom;③ 6 個 test fake factory 的 _layer7 簽名缺 batch_id=None(Codex review 抓到的回歸,跨 8 檔 17 失敗)。
- **驗收**:後端 100 passed(含 test_batch_alias 17+所有 _layer7 回歸+run_lifecycle)、前端 39 passed(新 16)、npm run build 過、解耦 0、Codex review r2 APPROVE。
- **語義**:三態 overwrite(同 batch_id 保留 batch_alias/換 batch_id reset/None merge-preserve);batch_alias 不覆寫 per-run alias;set_batch_alias 對 deleting→409;auto-cleanup 候選+mark_deleting 都護 batch_alias。

## 已知無關問題(非本任務)
- frontend `strategy-components.test.tsx` pre-existing 壞(缺 @/components/strategy/SignalTooltip,commit 6be0862,未碰 strategy)。

## 架構評估(2026-06-17 三方委員會:Claude+Codex+Composer 一致,評估檔 handoffs/20260617-datasource-ff-assessment-{codex,composer}.md)
使用者問:① 串 Glassnode/CoinGecko/台股/美股 易嗎 ② FF 夠不夠、可否往 IC Gatekeeper。
- **Q1 不能輕易達成**:adapter 抽象在但產線只 crypto 單通道。阻斷:fetch_aligned inner-join 跨頻率不相容(P0)、股票交易日曆全缺(P0)、雙 registry 假象、crypto taker 硬耦合、**:4109 ref-cache 硬寫 BTCUSDT=現有 bug**。前置:adapter metadata 合約+AsOf/PIT 對齊層+MarketCalendar+移除 BTC 硬編碼。
- **Q2 crypto 域有條件 GO 往 IC Gatekeeper**:FF crypto 研究級已足;IC Gatekeeper 已大量建好(ICFilterOrchestrator 8 階段+20+ 分析器),接點=V2 manifest+L7 raw parquet。GO 條件:限 crypto kline_cache、走 IC-First、強制 selection_window/split、修 :4109、真實 kline 端到端三方簽核。
- **PIT 稽核**:L3/L4/multi-TF/L6.5-winsor(預設 causal)安全;⚠️ 兩風險:(a) causal_preprocessing=False→全樣本 winsor 洩漏;(b) FracDiff d* 只前 500 bar 校準→regime drift。
- **使用者待決(我已問,未答)**::4109 bug 現在修(全管線高風險(d)) vs 記待辦。新源另立 epic 與 IC 解耦(三方共識)。

## 待辦 ticket(另開)
- **[新-高] feature_factory.py:4109 ref-cache 硬寫 ("BTCUSDT",tf)**:多 symbol 批次跨截面靜默用錯 ref,影響現有 crypto 正確性;命中 (d),建議推 IC 前先修。
- **[新] 多數據源 epic**(與 IC 解耦):adapter metadata 合約/AsOf PIT 對齊/MarketCalendar/企業行動;CoinGecko<Glassnode<台股美股 難度遞增。
- **[新] L6.5 洩漏防護**:確認 UI 預設 causal_preprocessing=True+IC-First;d* walk-forward 重估評估。
- float16 strict/training 讀升 float32 可選後續(docs/FLOAT16_STORAGE_EVALUATION.md)。
- CGSA raw-sink ADF/d* tier-gated 並行(需 24/32GB 硬體)。
- batch_alias Phase 3:一等 batch entity(batches.json),目前 batch_id/batch_alias 存 run registry([BA-9])。

## 執行端分工(2026-06-15 使用者定)
- 中/大實作=Composer 2.5 + Codex review;小=Claude 自己做。技術決策走委員會;中途自主 commit。
