# Handoff
**Agent**: Claude | **Time**: 2026-07-06 | **Branch**: main

## ★制度層總審查 epic — 實質完成(A 憲法 + B 腳本 + U-13 慣例)

### 進度
- **Phase A**(憲法重構+合約補齊)✅ commit(0e974a1 等)。
- **Phase B**(治理腳本 U-9/12/14/15)✅ commit f86a714+push:兩層 sync+選層反向檢查、gate DENY 落 audit、pre-commit index-only 尾空白 auto-fix、gate.sh 用法模板+新 dispatch.sh。governance 140 passed/9 pre-existing。
- **Phase C**:**U-13**(批次戳記慣例+同檔並發序列化)✅ 本次寫進 ORCH §戳記後。**U-20/U-21 裁決本身=先別做**(U-20 累積 violation 證據再機械化;U-21 維持 scorecard 不裁定)→ 屬長期觀察項,非待辦。
- **結論:制度層 epic 的可實作項全數完成**;U-20/21 為 standing 監測項。

### 實質下一站 = IC Analysis(前置已解除)
- **FF 測試資料 ✅ 就緒**(使用者確認):`data_cache/features/{BTC,ETH,BCH}USDT/1h/…`,batch alias「FF for IC Analysis Test」;3 symbol × (1h native + **12h 對齊欄位**,`raw/` 內 `1h_*`+`12h_*` parquet)×~437k 特徵;**max_lag 修正後生成**(使用者確認,不用重生)。d_star 在 feature_preprocessing/。
- **A/B/C 不影響 IC 數值**(純治理/流程工具,不碰 FF/IC/fracdiff 計算)→ IC 驗證不需因 A/B/C 重跑。
- **IC 待驗項**(ROADMAP P0 IC Phase1):第一刀(單幣縱向接線)✅ 完成 → **下一個=第二刀 `analyze_cross_sectional` 防洩漏**;續 1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖;另 P0.5 grouped_ic 崩潰止血。目標=79 全合成 IC 測試換真實 kline 端到端。**建議新 session 起跑**(context 乾淨)。
- **⚠️ IC 前置(恢復前第一步)= IC SPEC conformance pass**:實測 4 份 IC_*_SPEC(PHASE0/1a_CUT1/CONTRACT/RUN_SELECTOR)都**過不了現行 `template_check`**(缺 `RISK-HIT:` 宣告行;PHASE0/CONTRACT 另缺 §A FACT-RECEIPT 格式);TODO 全過。**非 A/B/C 造成**(template gate 早於 INSTREV 演進;IC SPEC 是之前寫的,同 `VERIFY_GATE_SPEC.md` b5 紅那類)。不補→`gate.sh dispatch --spec` 會 fail-closed 擋派工。修法=結構補錨點,**不改 IC 設計/數值**;RISK-HIT 反映真實風險(IC 命中 (a)數值+(d)ML 正確性),FACT-RECEIPT 須對 §A 型別斷言附**真跑** receipt(禁塞假湊過)→ 逐檔帶 context 做,列為 IC 第一子步驟。A/B/C 對 IC 文件唯一牽連=U-14 claim-check(handoffs/docs 的 operational claim commit 時須 backing/register-output)。

### 技術債(另記,不擋)
- governance 9 pre-existing 紅(b4/b5/r7:舊 spec/fixture 不符演進後 template_check/D-1/provenance)。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員派工帶 --task-id+--output,產出後 register-output。
- 執行端產物不可信;接回只讀 diff+測試+摘要,diff 既有測試斷言防假綠;**執行端不得 git checkout tracked 共用檔**。
