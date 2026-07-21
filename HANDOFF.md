# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-22 | **Branch**: **main** | **狀態**: 1d attribution 六批(B0-B5)完工並三方簽核;已 commit+push

## ▶ 下一站:1f 空圖整治(Phase 1 kernel 最後一塊)
- **1f**:IC 分析圖表面板在「無資料/計算失敗/載入中」時靜默顯示空白圖 → 改成誠實標示狀態(同 1d/B3 精神,前端圖表層誠實化)。收完 1f = Phase 1 收尾,才啟 Phase 2A(資源分配已決 2026-07-17)。
- 優先序(ROADMAP):1d✅ > 1f > Phase 2A/3 >> 票A >> 票B。

## ✅ 1d attribution 六批完工(2026-07-22;已 commit+push)
- 清債:B1 intercept 正名 / B2 NaN·inf·輸出溢位·index fail-closed(unavailable 三鍵+status:ok+reason 優先序+attribution_min_rows wiring) / B3 幽靈 factor_attribution 顯式 unavailable+completed_partial 外顯+D-12 三計數點。B0 golden 工具+baseline;B4 7 支 mutation 探針+機械 gate;B5 前端消費端適配。
- 管線:每批 Grok 實作+Codex+Composer 雙審(adversarial 勝簽核)+agy 實習獵手+Claude 獨立驗+閉合再驗+quorum+批間 Gate。三方 DATA-CORRECT 經 scope reconcile 一致 IN-SCOPE-PASS(`handoffs/1d-DATACORRECT-SCOPE-RECONCILE.md`)。
- 端到端 receipt 見 `handoffs/1d-DATACORRECT-claude.md`(真 kline;後端測試/mutation gate/golden comparator/前端 build 之實跑輸出皆載於該檔與各批 closure)。

## 📌 1d follow-up 兩票(ROADMAP 已明列防丟)
- **FU-1**:exposure 家族 fillna fail-closed 化(中度,factor_exposure 預設關;§N 他票;階段=1f 後 fail-closed sweep)。
- **FU-2**:cache close all-NaN carrier index 對齊(**票A/票B 硬前置**——接真歸因前必修;golden 已外顯 cache_close_finite 藏不住)。

## 制度里程碑
- **agy(Gemini3.6)code review 實習制**落地 ORCH §1 層3i+記憶;實戰抓真 bug(B0 3個/B2⑤/B5⑥最早提)+Claude 三分濾誤升;advisory 不算 quorum。
- Grok proven 配方(禁 --permission-mode)見記憶 reference_grok_cli_invocation。

## 📌 pre-existing 債(非 1d)
Rule 4 pattern_management:78、ModuleUnavailableError 死碼。
