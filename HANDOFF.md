# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-22 | **Branch**: **main** | **狀態**: **委員文件收斂方法 epic 進行中**——地基已修(151/0綠 commit 574efba),★下一步=起草實作 SPEC(見下方分支線)。〔IC全棧健檢 Step1 完工/pipeline活洞H1-H7 皆暫緩分支〕

## ▶ IC 全棧健檢 epic — Step 1 完工,下一站 Step 2
**定案交付物**:`handoffs/20260722-ic-map-WHOLEMAP-v2.md`(取代 06-24 v1;**已過三家完整性複驗+closure 親簽 APPROVED**)。joint recon=Claude+codex+composer+grok 三正式家族 + agy 實習;四家獨立版=`…-ic-discovery-{claude,codex,composer,grok}.md`;brief=`…-BRIEF.md`;複驗=`…-reconcile-verify-*.md`;戳記=`…-reconcile-stamp-*.md`。
**制度教訓(2026-07-22 使用者抓包)**:Claude 手動 merge 委員產物**必掉項**(首版漏~15項,三家 reconcile-verify 才抓全);已補記憶 `feedback_reconcile_committee_stamp`:任何 Claude 多方綜合須跑原提出方完整性複驗+戳記、逐字全讀勿 grep 抄捷徑;機器閘門只擋實作派工是 discovery 綜合滑過的洞。
**Step 1 主要發現(全對碼驗證)**:
- 🕳孤兒:`coverage_analysis`(raw孤兒但summary間接可見)、`diversification_metrics`(全孤兒)、`factor_orthogonalization`(孤兒+👻)、summary_table子欄、`ic_autocorr`(單家待複核)
- ⛓️‍💥斷線:**Deep雙store不hydrate**(後端有值深頁空)、`cross_symbol_validation`鎖deep tab、**xsec filter_log schema錯接**(NaN)、turnover/equity tab錯位
- 👻幽靈開關6個(ic_method/winsor/return_type/ic_autocorr/redundancy/vif)+ai_summary語意幽靈
- ⚠️**silent-0瀰漫**(codex修正,agy「全乾淨」錯):ICDecay/Centrality/LongShort/Quality/OOS缺欄補0,Trend缺signal顯「正常」
- 🔧v1已閉合delta:attribution(1d)/Net IC量綱(1c)/factor_returns(1c-FR)
- 📋狀態契約不一致(base用`{}`表缺→前端無法區分未啟用/失敗/不足/未接)=Step3閘門核心
**Step 2 待辦**:現況表 vs 業界 → 缺口+優先序(agy提10項gap見v2 §B:覆蓋率/多元化/正交化面板/自相關/單調性檢定/alpha換手比/板塊分層/OOS哨兵/provenance);**複審4 deferred該否提前**(funnel/capacity/regime IC/walk-forward+CPCV)。Step3=建typed契約SoT+wiring閘門(編碼無孤兒/無斷線/空態誠實/統一狀態契約),順手修原1f。Step4=跑閘門確認閉合。
**核心共識**:①audit先天不完整→time-box不追完美 ②手動快照會腐爛→做成機器閘門自守 ③分層防禦(typed契約+wiring閘門[查對應/空態/不崩,不查值/不查好看]+adversarial+里程碑複審)。

## 🔧 分支線:委員文件收斂方法 epic(2026-07-22;IC reconcile 手抄事故衍生;**進行中**)
**緣起**:使用者連抓 Claude 綜合多錯(reconcile未複驗/grok誤read-only/#9家數)→ 病灶=Claude 手抄合併委員產物必掉項。目標:機械可證的文件收斂,**擋意外 90-95% 不防蓄意**(使用者定)。
**★下一步(接續點)**:**SPEC v2 已起草+過三家審+reconcile 完**=`docs/CONVERGENCE_METHOD_SPEC.md`(TEMPLATE PASS;7 Phase/9 Task;R1-R6+C1-C17 全落地)。三家審結果:codex **REJECT**(4P0)/grok+composer **CONDITIONAL-APPROVE**;32 findings→17 群集(`…-review-RECONCILE.md` 逐ID對帳0掉項)全 ACCEPT 修入 v2(5 P0群集=C1 digest欄/C2禁XFAIL/C3刪advisory逃生/C4 R6水位釘死/C7 forward-dep)。**閉合複驗結果**:grok+composer **APPROVED**;codex **BLOCKED**(3 殘留:C2 red-receipt含糊/C7 Oracle④語意stamp forward-dep/新P1 M3一詞多義)→Claude 出 **v3** 精準收口(9機械案逐案polarity矩陣+M4b排除/Oracle④純body-hash去forward-dep/M3釐清)。**接續**:codex 閉合複驗2 進行中(`bbpe7lvgh`;產物→`…-closure2-codex.md`)→codex APPROVED 湊齊三家 RECONCILE-STAMP→機檢 `reconcile_stamps_check.sh`→commit SPEC+起 TODO→實作(雙家 code review)。SPEC 未 commit(待閉合)。⚠️codex 閉合已進第2輪,若再 BLOCKED→斷路器開委員會。
**定案**:`handoffs/20260722-CONVERGENCE-METHOD-FINAL.md`(§七三家CONDITIONAL APPROVE,動工限先修地基)。產物鏈:CONVERGENCE-METHOD-SPEC→method-redteam-*(打破7攻擊)→MANIFEST-CONSENSUS(+agy)→CONVERGENCE-METHOD-FINAL→final-review-*。
**✅ 地基已修(commit 574efba push)**:governance suite 146→**151 passed/0紅**(CLAUDE.md去寫死家數→pointer/gitignore run_receipts/b5 fixture補Task);`scripts/completeness_check.sh` 紅隊加固版入repo(STRICT=1/heading錨定;只擋dropped-ID非語意)。**地基剩(c)變異測試先寫紅**=併入實作SPEC。
**制度教訓已入記憶** `feedback_reconcile_committee_stamp`:Claude多方綜合須原提出方完整性複驗+逐字全讀勿grep抄捷徑。

## 🕳 另一分支 backlog:Gate 現行活洞 H1-H7(對碼證實,獨立於上;暫緩)
設計檔`docs/PIPELINE_INTEGRITY_AUDIT_DESIGN.md`(push GitHub)+`handoffs/…-UNION.md`(A-G,~24節點/C1-C27/N1-N24)。H1 `gate_check.sh:47`無grok+cx_run/timeout全繞;H2 stamp預設codex,composer不含grok;H3 risk=low/waived旁路;H4無jq fail-open;H5 token kind級;H6 grok不在ADV provenance;+codex R2加P8-P12(touch造token/偽stamp/postflight size-only)。**未動工,待收斂方法後再排**。

## ✅ 1d attribution 六批完工(2026-07-22;commit f2de34f push main)
清債:B1 intercept 正名/B2 NaN·inf·溢位·index fail-closed(unavailable 三鍵)/B3 幽靈 factor_attribution 顯式 unavailable+completed_partial 外顯+D-12 三計數。B0 golden 工具/B4 7 探針+機械 gate/B5 前端三態 union。每批 Grok 實作+Codex+Composer 雙審+agy 實習+Claude 獨立驗+閉合+quorum+Gate;三方 DATA-CORRECT scope reconcile 一致 IN-SCOPE-PASS。receipt 見 handoffs/1d-DATACORRECT-*。
**1d follow-up 兩票(ROADMAP 已明列防丟)**:FU-1 exposure fillna fail-closed 化(中,預設關);FU-2 cache all-NaN carrier index 對齊(票A/票B 硬前置)。

## 制度里程碑
agy(Gemini3.6)code review 實習制上線(ORCH §1 層3i;advisory 不算 quorum);Grok proven 配方見記憶 reference_grok_cli_invocation。

## 📌 pre-existing 債(非 1d/非本 epic)
Rule 4 pattern_management:78、ModuleUnavailableError 死碼。
