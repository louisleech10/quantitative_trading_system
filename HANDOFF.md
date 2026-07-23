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

## ✅ 委員文件收斂方法 epic — 完工上線(2026-07-23;commit 27b499d)
**全鏈落地(6 批 B1-B6)**:SPEC v3+TODO v3 三家審+戳記(sha256:29d9fa62/8dd8df24)→B0地基(151)→B1變異先紅→B2 canonical ID+digest+空殼機檢→B3目錄鎖+gate掛載+反bypass硬化(5 env override 全綁 GOVERNANCE_TEST_HARNESS)→B4 self-check+DEGRADED_PENDING狀態機→B5 5oracle+非循環90%水位(dogfood 機器驗證「32 findings 0掉項」)→B6語意charter+收編。**pytest tests/governance -q → 215 passed/xfail=0**。每批 Grok 實作/Codex+Composer 雙家 review/Claude 獨立驗+finding closure;codex 逐批深度對抗(並發競態/env bypass/循環coverage/裸ID冒充)全修。commits 9dac863→27b499d。工具上線:`scripts/completeness_check.sh`(--lock 正式入口)+`scripts/replay_convergence_coverage.sh`+`scripts/write_committee_accepted.sh`+`templates/COMMITTEE_{FINDING,SEMANTIC_REVIEW}_TEMPLATE.md`。
**殘留 backlog(非阻擋,下一小批)**:composer B6-P1-01/P2 producer hardening 建議;B1 receipt 位置/norecursedirs 覆寫預設(P2/P3 carry-forward)。

## 🔧 分支線:委員文件收斂方法 epic(歷史;已完工見上)
**緣起**:使用者連抓 Claude 綜合多錯(reconcile未複驗/grok誤read-only/#9家數)→ 病灶=Claude 手抄合併委員產物必掉項。目標:機械可證的文件收斂,**擋意外 90-95% 不防蓄意**(使用者定)。
**✅ SPEC v3 定版+commit(`08eb7fe` push main)**:`docs/CONVERGENCE_METHOD_SPEC.md`(TEMPLATE PASS;7 Phase/9 Task;R1-R6+C1-C17 全落地)。審查鏈=v1 三家對抗(codex REJECT 4P0/grok+composer CONDITIONAL)→機械 reconcile 32 findings→17 群集(`…-review-RECONCILE.md` 逐ID對帳0掉項)→v2 全收口→§B8 閉合(grok+composer APPROVED/codex 抓3殘留 BLOCKED)→v3 精修(C2 逐案polarity矩陣+M4b排除/C7 Oracle④純body-hash去forward-dep/M3釐清)→**codex 閉合輪2 APPROVED=三家全 APPROVED**。closure 檔=`…-closure-{grok,composer}.md`+`…-closure2-codex.md`(簡化戳記;正式 sha256 戳記留派實作前)。
**✅ ① 正式 RECONCILE-STAMP 完成**:`reconcile_stamps_check.sh` PASS(codex+composer+grok 全 APPROVED,body sha256:03cf9083;committee_dispatch task:20260722-conv-recstamp-* 留痕+register-output)。
**✅ ② TODO v3 三家全 APPROVED + 正式戳記 PASS**:`docs/CONVERGENCE_METHOD_TODO.md`(TEMPLATE PASS;§0/§B 6 批次+9 Task+內嵌 polarity 矩陣+偽碼+真實函式名)。審查鏈=v1 三家(codex REJECT 4P0/grok+composer CONDITIONAL)→reconcile 48→26 群集 0 掉項→v2→§B8 閉合(各抓 v2 改字新洞)→v3 精修 7 殘留→round2 收斂單一殘留(M3/全紅用字,掃 L40/42/72/75/78 改齊)→最終確認輪 grok(bqkrndn4b)+composer(b4y79w3yx)+codex(blmzdcoon)**全 APPROVED**。TODO reconcile 戳記 `reconcile_stamps_check.sh` PASS(body sha256:8dd8df24)。〔插曲:codex round2 `buxa1jpim` 卡死 codex_models_manager infra hang→殺進程重派,非審查問題〕
**▶ ③ 實作 6 批次 B1-B6 進行中**(見 TODO §B)。**✅ B1 完工+commit(`9dac863` push)**:8先紅+M3守衛+M4b OOS+pytest.ini norecursedirs;Claude 獨立驗(8 failed 2 passed/主 suite 151)+Codex+Composer 雙家 APPROVE(僅 P2/P3 carry-forward:receipt 位置 handoffs/mutation-red.receipt vs TODO 寫 reconcile/<session>/、norecursedirs 覆寫預設)。**✅ B2 完工+commit(`70f7af6`)**:canonical ID 整行 anchored+FAMILY allowlist+_validate_finding_body(斷言+碼證)+source digest+DEGRADE 命名空間+範本。codex REQUEST-CHANGES(ID 未錨定整行)→Claude inline fix(anchored ^…$+尾隨文字回歸測試)→codex 複驗 CLOSED。157 passed。
**▶ B3 實作+獨立驗 PASS,雙家 review 中**(`boe4bu3dr`/`bi837u704`):Task3.1 sources.lock schema v1+roster+拒收(symlink/late/README/version)+拒 ADVISORY_ONLY+write_sources_lock.sh;Task3.2 gate.sh `_run_completeness_gate` 掛現有派實作閘。獨立驗:mutation_red 1 failed(m2 B5 owner)/9 passed、governance **163**、gate.sh 語法 OK+reconcile 戳記未破。**▶ B3 fix 輪進行中**(`bcd6vnek8`):雙家 review 抓 7 findings→4 群集(全 B3 引入):BC1 env-override bypass(兩家都抓,反 bypass 紅線)/BC2 `--adversarial waived:` 繞 completeness+**gate 咬到自己 epic meta 派工回歸**/BC3 gate 測試假綠(路徑子字串)/BC4 lock /var vs /private/var 路徑不正規化。Claude 已 inline 修 BC2 結構性 engagement(`_run_completeness_gate` 非 handoffs/reconcile/<session>/ →略過,解封自我派工);Grok 修剩餘 BC1 env 守衛(GOVERNANCE_TEST_HARNESS=1 才認否則 fail-closed)/BC2 waived-for-convergence/BC3 測試真測+斷言收緊/BC4 realpath 統一。fix brief=`…-CONVERGENCE-B3-FIX-BRIEF.md`。**B3 fix 複驗**:composer **APPROVED**(4 findings CLOSED);codex 抓**新 P0-03**(ID_PATTERN/ALLOW_ID_PATTERN_OVERRIDE 另一 env bypass,BC1 漏網)+P2-01(--force 重寫 FROZEN lock)+P1-04(scope)→**Claude inline 補守衛**(ID_PATTERN+--force 皆綁 GOVERNANCE_TEST_HARNESS=1)+2 測試(168 passed);P1-04 裁定=convergence-session-scoped(SPEC 專屬+不防蓄意,waived 故意漏--reconcile=out-of-scope)。**codex 複驗2 進行中**(`bhorxx3br`)。**✅ B3 完全閉合+commit(`cfa6ab2`)**:兩家 APPROVED;反 bypass 面掃淨(RECONCILE_STAMPS/COMPLETENESS_CHECK/ALLOW_ARGV/ID_PATTERN/--force 五 env override 全綁 GOVERNANCE_TEST_HARNESS=1);168 passed。
**✅ B4 完全閉合+commit(`19a579e`)**(VERIFY-EXEMPT:doc-example:b4):self-check+write-once(O_EXCL 防競態)+DEGRADED_PENDING exit3;codex 深度對抗 6 P1(並發競態/degrade roster/expiry)→fix→再抓 2 boundary(roster唯一性/coverage write-once)→fix2→codex 複驗 CLOSED;獨立驗 governance 187。
**✅ B5 完全閉合+commit(`7b1193d`)**:5 oracle+非循環 90%水位量測(dogfood 本epic review→reconcile 32/32 機器驗證「0掉項」,抽ID→0.96875列缺項)+m2/m2b 轉綠。雙家抓 4 群集(B5C1 循環coverage兩家BLOCKING/B5C2非冪等/B5C3 nested-tail/B5C4缺ID不可稽核)→Grok fix→兩家 APPROVE(codex 條件 fixture cleanup:已清 WHOLEMAP/pipeline 18+21 注入 heading,預設 replay rc=0);198 passed。
**▶ B6 實作+獨立驗(213 passed/xfail=0/mutation_red 收編)+fix 輪進行中**:語意 charter+committee_accepted producer+行為 oracle+移除 norecursedirs。雙家 review:composer APPROVE;codex **1 BLOCKING**(CODEX-B6-P1-01:producer 太寬鬆,只檢 Fresh:NONE marker 就取 union,未驗語意欄位/拒裸 ID 清單冒充語意審;composer 同處標非阻擋)→**Grok fix 中**(`bz31bnhhk`;producer 改結構化 charter parser+拒裸ID清單+2反例測試)。**接續**:收 fix→獨立驗→codex 複驗閉合→commit B6→**epic 完工**(6 批 B1-B6 全落地,收斂方法上線)。**殘留 backlog**:composer P1-01/P2 producer hardening 建議(下一小批)。
**權限**:gate.sh/template/git/pytest 已在 allow(靜默);codex/grok/cursor-agent/reconcile_stamps_check.sh 不在→彈窗(使用者調模式中);**勿用 `rm`(命中 ask 規則)/勿 gate.sh 接 pipe**。
**派實作 token 配方(踩過的坑,存查)**:`gate.sh dispatch --spec docs/CONVERGENCE_METHOD_SPEC.md --reconcile <spec reconcile> --adversarial <同一 spec reconcile> --task-id conv-impl-b<N>-grok --risk high --template "n/a:impl 非產SPEC" --review-role ... --facts-asked ...`。**坑**:①--adversarial 檔須含 `Verdict:` 行(D-1;已加到 SPEC reconcile body,重算 hash 29d9fa62 重戳)②高風險仍須 --template(給 n/a:)。SPEC v3 commit 08eb7fe;TODO v3 commit 79e045a。
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
