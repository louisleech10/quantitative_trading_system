# Handoff
**Agent**: Claude(Fable 5) | **Time**: 2026-07-17 | **Branch**: **main**(LA-1 已合併+push) | **狀態**: ✅ **LA-1(P1)完工並合併 main**——五洩漏全修+三方 DATA-CORRECT PASS

## ▶▶ 下一站:LA-2(P2 前瞻收尾)——**新 session 從這裡開始**
- **範圍(P2,來自 master `handoffs/ICLOOKAHEAD-MASTER.md` P2 節)**:①**winsorized label** 禁用/PIT(`label_generator.py:71-80` `return_type=winsorized` 全期裁尾;預設 simple 不走,條件觸發)②**model OOT-only 契約**(lightgbm/xgboost/calibration/sample_weight/probability_calibrator 的 post-fit 指標對全樣本/caller array→改 train/test 紀律)③**條件模組 train-fit/標註**(`factor_orthogonalizer`/`factor_exposure_analyzer` 預設 OFF、`pattern_extractor` 全 quantile 門檻、`regime_detector._fit_global`〔expanding=False 全期 fit;LA-1 已鎖 IC/XGBoost caller 不傳 False,LA-2 完整因果化〕)。
- **性質**:P2 = **條件式/預設不走/model**——比 P0/P1(預設路徑)低風險,但要把前瞻整治 epic 完整收掉。
- **資源分配已決(2026-07-17 使用者)=全力 Phase 1**:LA-2→1c-FR-FULL→1d→1f 收完才啟 Phase 2A。
- **如何開始(新 session,照 LA-0/LA-1 範本)**:①開場先稽核 HANDOFF/ROADMAP/master vs repo 實況(鐵律)②走完整大任務管線:**聯合偵察(Claude+三委員平行,聚焦 P2 三點)**→SPEC 起草(Claude)→三家 adversarial→凍結(freeze-stamp)→TODO→逐批 Grok 實作+**Codex+Composer 雙家 review**(機器閘門 `review_quorum_check.sh`;實作者不自審)→每批過 review commit→三方 DATA-CORRECT(a,d 高風險)。③範本=`handoffs/LA1-*`(recon/SPEC/TODO/DATACORRECT 全套)。
- **複用**:`momentum/Analysis/pit_stats.py` 七原語(LA-0 建;winsorized label 用 `pit_expanding_bounds`,同 P1-2/P0-2 家族)。
- **前置**:LA-1 已合併 main(merge `8214d5f`);LA-2 從 main 起(建議另開 branch `feat/ic-la2-p2-impl`)。
- **相關 memory**:`project_ic_analysis_lookahead_remediation`、`feedback_code_review_two_families`、`feedback_recon_joint_with_committee`、`reference_codex_luna_effort_eval`(codex=Luna/xhigh)。
- **⚠️ 勿重工**:全 IC look-ahead 盤點已完成(master 含 P0/P1/P2 全清單+實跑證);LA-2 偵察=**從 master P2 起、聚焦三點**,不重掃全模組。

## ✅ LA-1(P1)look-ahead 完工並合併 main(merge 8214d5f;branch feat/ic-la1-p1-impl 已刪)
- **五洩漏全修**:B0 baseline(707ab82)→B1 regime PIT〔P1-1 rule 分位/P1-1b fallback/P1-1c kmeans Segment-causal〕(aa2e7bd)→B2 long_short qcut PIT〔RB-3 feature 原時序+Policy-Strict〕(dba5716)→B3 fallback loud〔root 紅標+G-A2+禁內層 persist+五 oracle〕(38f164c)→B4 golden 重基準+control 全樹凍結(e7da153)→B4 reverse-check symbol-aware(7629022)。
- **每批 Grok 實作→Codex+Composer 雙家 review(每批抓真 finding/假綠)→finding-closure→commit**。codex 假綠嗅覺全程關鍵(B0 validator 只比 path+index/B1-B2 測 helper 不測產線 mutant/B4 control 投影漏 raw leaf)。
- **✅ 三方 DATA-CORRECT PASS**:Claude(綠測+code-level 洩漏真除)/Codex-Luna(diff 審+親自 mutate 驗)/Composer(BTC69/ETH65 partition);Grok=實作者不簽。三方各自 adversarial 證三洩漏可證偽(P1-1c MUTANT_FLIP=1 等)。收官抓到 golden 帳本 bug(reverse-check symbol 盲,非產線洩漏)→BTC+ETH 對稱 reverse 修畢。審計 handoffs/LA1-B42-DATACORRECT-{claude,codex,composer}.md。
- **治理**:SPEC v0.4.3+TODO v2.3 雙凍結(4輪 SPEC adversarial+5輪 freeze-stamp+2輪 TODO;三家 hash gate PASS)。scope=P1-1/1b/1c(kmeans 使用者裁併入完整修)+P1-2+P1-3;FR/`_fit_global` §N exclude。

## ⚙ Codex 模型評測(使用者 2026-07-17)
- backing GPT-5.6 Sol medium→**Luna**;effort MAX→**xhigh**。**皆無能力退步,與 Sol medium 基線持平**(假綠嗅覺/誠實斷路器/RFC6901 深度同級;MAX 285k vs xhigh 299k token 相近)。xhigh 對 review/DATA-CORRECT 型任務夠用。評測 handoffs/CODEX-LUNA-MAX-EVAL-{claude,grok}.md。

## 📌 已收官/背景
- **✅ 合併 main 完成**(merge `8214d5f`;本地+遠端 branch 已刪);/tmp log+.DS_Store 已清;432MB 舊 epic baseline 使用者定留著。
- **✅ IC Gatekeeper 七 Phase 全景已補進 ROADMAP canonical 表**(`c50d79e`)——防再遺漏;funnel/IC-PERF=Phase 3+4、regime 驗證=Phase 4 獨立票條件觸發(memory `project_regime_ic_validation_positioning`)。
- **regime-conditional IC 驗證**(使用者關注):kmeans 非最佳實務+小樣本雜訊→歸 Phase 4 獨立票、條件觸發(現 grouped_ic 只進報告非 gate,不污染核心篩選)。
- pre-existing 7 紅(redirect state-leak 測試順序)非本 epic 另票;funnel/IC-PERF=Phase 3/4(Gatekeeper 後段)。

## (以下歷史)LA-1 實作細節

## ▶ 實作進度
- **✅ B0 commit 707ab82**:雙家過(codex 2 BLOCKING→fix→CLOSED)。
- **✅ B3 commit 38f164c**:fallback loud 全套(root 紅標 fail-closed/禁內層 persist/五 oracle 28 gate 測/前端)。review=Composer APPROVE;**Codex 9 findings 兩輪 fix**;**B3-TEST-01 兩輪未閉→斷路器委員會**(Claude+codex+composer 三方設計 callback 真鏈測試,SYNTHESIS 零自由度)→Grok 實作 6 測→codex CLOSURE-3 APPROVE。共用檔(test_la1_lookahead.py/allowlist)隨 B1 commit。
- **✅ B1 commit aa2e7bd**(2026-07-17):regime PIT 三點全落(rule 分位/fallback 真值表/kmeans Segment-causal)。review 三輪 fix:codex 3B(expanding guard 過寬/測試假綠改產線/xgboost exact)+composer 2B(allowlist path≠schema/warmup mutation 缺)+**編排端抽驗抓 allowlist 缺 regime_kmeans rows(fix3)**→雙家重跑反例全 CLOSED+APPROVE。契約漂移裁定:collect==10(+production_mutations_red,雙家 accept+docstring 修)。
- **✅ B2 commit dba5716**:long_short PIT(RB-3 原時序分箱/Policy-Strict/固定 q/migration 6 列)。review=Composer APPROVE;Codex 5B(RB-3 假綠測 helper 不測 analyze/私加 bin_min_samples 入口/skip 語意/±inf gate/validator scope 漂移〔編排端裁追認〕)→fix→全 CLOSED+APPROVE。
- **▶ B4 收官(接近完工)**:golden 重基準+歸因對帳+5 wash+跨 symbol 全落。review 多輪:codex B4 四輪(control 三輪常數→無 artifact→投影→**委員會 full-tree**〔黑名單 scrub+RFC6901 denylist+兩跑 receipt+sentinel,handoffs/LA1-B4CONTROL-COMMITTEE-SYNTHESIS.md〕)+allowlist 補列 supp/supp2(owning-batch 授權,BTC41+ETH119 exact+9 discriminator 修+added_key 綁 symbol 雙錨);composer APPROVE;freeze 指紋 re-stamp(codex 追認 `2e0991f4…`)。golden **45 passed**、--check exit 0(6 control artifact)。**唯一 open=B4-CODEX-1 control 終閉**(進行中 blrzecoyh)。
- **⚙ Codex 模型換 GPT-5.6 Luna MAX(使用者 2026-07-17)**:smoke PASS(讀檔理解精準);終閉任務=能力評測主樣本;Claude+委員平行評 vs Sol medium(handoffs/CODEX-LUNA-MAX-EVAL-*)。
- **✅ B4 commit e7da153**(control 全樹凍結+歸因+補列)。
- **▶ B4.2 三方 DATA-CORRECT(進行中,抓到真 golden 帳本 bug)**:
  - Claude leg ✅ PASS(綠測+code-level 洩漏真除);handoffs/LA1-B42-DATACORRECT-claude.md。
  - **三方一致:三洩漏修法資料正確**(各自 adversarial mutation 證可證偽,P1-1c MUTANT_FLIP=1 等)。
  - **Composer+Claude 獨立重現 `test_regime_pit[kmeans]` FAIL**(reverse-check 紅,1493s)。**根因(Grok 診斷+實證)**:reverse-check symbol 盲——跑 BTC kmeans 卻要求 allowlist **所有** regime_kmeans row(含 56 個 ETH-only 特徵真 row)都在 BTC 產出裡。**非 allowlist 錯**(ETH row 是 ETH forward 需要的真 diff),是**測試斷言 bug**。
  - **Grok 修**(僅改 test_la1_lookahead.py reverse-check→symbol-aware:path 在 BTC baseline 且 old==B0 才要求 BTC 產出;ETH row skip 但加 `n_cross_symbol_skipped>0` 防刪;BTC 斷言未弱化+加 n_xgb_allow>0)。Claude diff 審=**非假綠**(加嚴非弱化)。
  - **⚠️ 待複驗提**:ETH 無獨立 reverse 覆蓋(既存缺口,非本次引入)——ETH phantom row 目前偵測不到,codex 複驗應補 ETH reverse 或明列債。
  - **⚙ Codex 模型 MAX→xhigh**(第二步):MAX 兩軸樣本皆無退步(終閉自校欄位/DATA-CORRECT 自發 mutation A/B);xhigh 樣本=codex-xhigh DATA-CORRECT(bbaoqaw34,與 grok 改測試並行故 verdict 混淆,主要當能力樣本)。評測 handoffs/CODEX-LUNA-MAX-EVAL-*。
- **剩餘**:kmeans 修轉綠確認→codex+composer 複驗 grok 測試改(防假綠+ETH reverse 缺口)→三方乾淨重簽→commit phantom 修→LA-1 完工。
- 審計:handoffs/LA1-B{0,1,3}-{IMPL,REVIEW}-*+LA1-B3TEST01-COMMITTEE-*(含 SYNTHESIS)。

## 🔒 雙凍結紀錄
- **SPEC** `docs/IC_LA1_SPEC.md` **v0.4.3**(file sha `41499dae…`);凍結檔 `handoffs/LA1-SPEC-FREEZE-RECONCILE.md`(canonical 戳記 task `20260716-la1-freeze5-*`,register-output×3,`reconcile_stamps_check.sh` **PASS** body sha `3dd1e94c…`);史料 `-history.md`。freeze 5 輪:codex 連 3 輪 REJECT 抓真洞(B1.3 邊界舊句/§A 基數 8→12〔grok 同抓〕/migration 幽靈列+`:23` 非 nodeid)。
- **TODO** `docs/IC_LA1_TODO.md` **v2.3**(sha `316d4c90…`):R1 三家 adversarial(8 BLOCKING:B0 入口契約/predeclare 流程/骨架雞蛋/偽碼壓縮/oracle 重編/測試域矛盾/int80 raise 錯/覆蓋表假陽性)→v2→R2(composer/grok 可 Frozen;codex 3 殘)→v2.1-2.3 codex closure 鏈(R3/R4/R5)→**FROZEN-OK**(`handoffs/LA1-TODO-ADV-R5-codex.md`)。reconcile=`handoffs/LA1-TODO-ADV-RECONCILE.md`。
- **實作合約**:Grok 實作(依額度)/Codex+Composer 雙家 review(機器閘門 review_quorum_check.sh)/每批過 review 即 commit/B4 三方 DATA-CORRECT。批次 DAG=B0→{B1,B2,B3}→B4(TODO §B)。

## ▶ LA-1(P1 look-ahead 收尾)當前進度
- **✅ 開場稽核**:HANDOFF vs repo 抓 2 處漂移(P1-1 行號實為 ic_engine:1106-1107;開關真名=`by_regime`+`include_regime_analysis` 雙閘)。
- **✅ 聯合偵察(4方)**:`handoffs/LA1-RECON-{claude,codex,composer,grok}.md`+`LA1-RECON-SYNTHESIS.md`。洩漏三點實跑證實(Grok+Composer 真 kline receipt;codex HDF5 逾時斷路器誠實 BLOCKED)。委員修我 8 處(B1 percent/fraction 單位陷阱=BLOCKING 等)。
- **✅ 使用者裁定×2**:①P1-1b(`regime_detector:306` kmeans fallback 同族洩漏)併入 LA-1 ②**P1-1c(kmeans 主路徑 `_align_labels:257` 全期命名洩漏,R1 codex 抓)併入 LA-1 完整修**;XGBoost 未開始使用可動;**LightGBM 0 hits 不受影響**(caller 圖實跑)。
- **✅ SPEC 4 輪 adversarial**:v0.1→R1(三家 8 BLOCKING:D1 guard 空殼/P1-2 退化非 NaN/紅標雙軌/kmeans 非 control/空 vol/真值表/xgboost caller/DAG)→v0.2→R2(B1.3 因果區間自相矛盾〔我寫錯,composer 37/50 flip 實證〕/G-A schema 不可實作/**P1-2 第三層洩漏=future-label availability 污染 dropna 後分箱,codex N3**/B0 覆蓋)→v0.3→R3(name_map same-model namespace〔codex+grok 雙家獨立抓〕/prefix 契約互斥/carrier 未鎖/migration 表矛盾)→**v0.4**(template PASS)。
- **▶ 進行中:freeze-stamp R4**(背景 task `20260716-la1-freeze1-{codex,composer,grok}`):v0.4 body sha256=`98b9b740…f53cdbb`,戳記收 `handoffs/LA1-SPEC-FREEZE-RECONCILE.md`。全 APPROVED → `reconcile_stamps_check.sh` 機檢 → 凍結。
- **audit 鏈**:`handoffs/LA1-SPEC-ADV-{R1×3,R2×3,R3×3}+RECONCILE×3`(gitignored 本地)。

## SPEC v0.4 關鍵定案(docs/IC_LA1_SPEC.md)
- **scope**:P1-1(regime rule 全期分位)+P1-1b(fallback 同病)+P1-1c(kmeans fit+命名 Segment-causal 完整因果化,偽碼鎖 SPEC)+P1-2(long_short qcut PIT+Policy-Strict require_full_q+feature 原時序分箱)+P1-3(fallback loud:root `analysis_status` 單名+G-A2+禁內層 persist+5 bypass oracle+carrier 鎖死)。FR/`_fit_global` §N exclude。
- **DAG**:B0(baseline 含 kmeans/xgboost legacy)→{B1 regime,B2 long_short,B3 fallback loud 並行}→B4(golden/歸因 5-wash/三方 DATA-CORRECT)。
- **golden**:control deep-equal(regime OFF/LS OFF/非觸發 fallback;kmeans**不是**control);修改路徑歸因表(class {P1-1,P1-1b,P1-1c,P1-2,P1-3-obs}+exact path/index/old-new)。dataset receipt:BTC/1h rows=20352 sha₁₆=1c93c379…;ETH/12h rows=1696 sha₁₆=00d1ee98…。

## 凍結後下一步(照 LA-0 範本)
①`reconcile_stamps_check.sh handoffs/LA1-SPEC-FREEZE-RECONCILE.md codex,composer,grok` PASS ②TODO 起草(Claude,`docs/IC_LA1_TODO.md`,template PASS+SPEC ID 覆蓋表)③TODO 三家 adversarial→凍結 ④逐批 Grok 實作+**Codex+Composer 雙家 review**(機器閘門 `review_quorum_check.sh`;實作者不自審)⑤每批過 review 即 commit(建議另開 branch `feat/ic-la1-p1-impl`)⑥B4 三方 DATA-CORRECT。

## 📌 慣例/環境(沿用)
- Grok=實作者(`--sandbox workspace`);reviewer=Codex+Composer;gate.sh dispatch 開 token;committee 產出 register-output。
- 委員 /tmp workdir 收尾清理(保留 claude-501);pytest collect 副作用 `tests/golden/l65/test_inventory.txt` 勿 commit。
- pre-existing 7 紅(redirect state-leak 測試順序污染)非本 epic 另票;IC 過渡期跑 feature_filter 別全量(OOM,funnel deferred 整個 Gatekeeper 完成後)。

## ⚠️ 未 commit
docs/IC_LA1_SPEC.md(治理中,凍結後隨治理產物一起 commit)、docs/API_SPECIFICATION.md(session 前既存尾空白)、docs/IC_LA1_SPEC 相關 handoffs(gitignored)。docs/workflow_diagram.png+scratch/(session 前既存,非本工作)。
