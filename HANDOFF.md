# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-22 | **Branch**: **main** | **狀態**: 1d 六批完工並 push main(f2de34f);下一站=IC 全棧健檢 epic

## ▶ 下一站(新 session 開工塊):IC 全棧健檢 epic(吸收原 1f 空圖)
**動機(使用者定 2026-07-22)**:2026-06-24 WHOLEMAP 已隔月過時(1a/1e/1b/1c/1c-FR/1c-FR-FULL/LA 整治/1d 全落地,資料路徑/enabled/schema 增減);且要以量化業界觀點檢視功能有無遺漏。
**核心共識**:①任何 audit/roadmap 先天不完整,增減必然 → 不追求完美,time-box。②手動快照會腐爛 → 把發現**做成機器閘門**(審一次、以後自守),不重複人工審。③**分層防禦**:架構逼 typed 契約(工具看得到大宗)+wiring 閘門(查對應/空態/不崩,**不查值正確/不查好看**)+adversarial review(抓繞過契約的)+里程碑複審(兜底);無單層完整,靠疊。
**執行順序(定案)**:
1. **盤點現況(discovery sweep)**=起點:Claude+三委員(含 agy 實習)平行偵察,產「後端產出／前端消費／wiring／空態」**四欄現況表**;當場浮現既有幽靈圖表/斷線/靜默空圖。(20+ IC 圖表元件見 frontend/src/components/ic-analysis/)
2. **quant gap analysis**:現況表 vs 業界最佳實務 → 缺口+優先序;**複審 4 個 deferred 該不該提前**(feature selection funnel=Phase3/capacity 未校準低優先/regime IC=Phase4 條件/walk-forward+CPCV=複用 ML 孤島)。
3. **建 typed 契約 SoT + wiring 閘門**:形式化現況成機器可讀契約+自動閘門(編碼不變式:無孤兒輸出/無斷線/空態誠實);順手修 #1 幽靈=原 1f 空圖誠實化。
4. **跑閘門確認閉合**:對現況跑新閘門確認幽靈都關,之後自動守。
**起手**:照慣例偵察=Claude+三委員平行(memory `feedback_recon_joint_with_committee`);參考底稿 `handoffs/20260624-ic-map-WHOLEMAP.md`(舊版,須複核勿盡信)。

## ✅ 1d attribution 六批完工(2026-07-22;commit f2de34f push main)
清債:B1 intercept 正名/B2 NaN·inf·溢位·index fail-closed(unavailable 三鍵)/B3 幽靈 factor_attribution 顯式 unavailable+completed_partial 外顯+D-12 三計數。B0 golden 工具/B4 7 探針+機械 gate/B5 前端三態 union。每批 Grok 實作+Codex+Composer 雙審+agy 實習+Claude 獨立驗+閉合+quorum+Gate;三方 DATA-CORRECT scope reconcile 一致 IN-SCOPE-PASS。receipt 見 handoffs/1d-DATACORRECT-*。
**1d follow-up 兩票(ROADMAP 已明列防丟)**:FU-1 exposure fillna fail-closed 化(中,預設關);FU-2 cache all-NaN carrier index 對齊(票A/票B 硬前置)。

## 制度里程碑
agy(Gemini3.6)code review 實習制上線(ORCH §1 層3i;advisory 不算 quorum);Grok proven 配方見記憶 reference_grok_cli_invocation。

## 📌 pre-existing 債(非 1d/非本 epic)
Rule 4 pattern_management:78、ModuleUnavailableError 死碼。
