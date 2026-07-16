# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-16 | **Branch**: **feat/ic-la0-p0-impl**(9 commits,未 push) | **狀態**: ✅ **LA-0(P0)全數完成**——三 P0 洩漏修復+雙家 review+三方 DATA-CORRECT PASS

## ✅ LA-0(P0)look-ahead 整治 完工(branch feat/ic-la0-p0-impl,9 commits)
- **三個 P0 look-ahead 修復**(每批 Grok 實作→Codex+Composer 雙家 review→codex 每批抓真finding→finding-closure→commit):
  - **B2 P0-1**(9d98c89):rolling IC spearman 全序列 pre-rank→窗內 rank(pit_stats.rolling_window_rank_corr)
  - **B3 P0-2**(7debf8e):stage5 mono/turnover 全窗 qcut→PIT(§P0-2-AGG pit_pool);turnover S2 n-1→n warmup null;前端 null 相容
  - **B4 P0-3**(00efd6b):stage1 preprocessor fit_mode 四出口(unset→fail-closed);**codex 抓到 _is_type_feature 讀未來的真洩漏**已修(改 metadata 判定)
- **基礎**:B1 pit_stats 七原語(2dd4601,§MS first_valid canonical);B0 改前 golden baseline(cea27de,legacy 引擎 element級+分層manifest)
- **收官 B6**(921382c):golden 重基準(split-ON+OFF live deep-equal)+機器可讀歸因表(0 unexpected/control-stable)+validator 擋洗歸因(4種wash mutation打紅)+跨symbol隔離。**三方 DATA-CORRECT: Claude+Codex+Composer 皆 PASS**。
- **治理**:SPEC v0.5.3+TODO v2.3 凍結(7f5834e;4輪SPEC adversarial+6輪freeze-stamp+3輪TODO;三家 hash gate PASS);FR descope 移 1c-FR-FULL epic。
- **流程 scar+閘門**(9b61b5f/5390c2b):中/大 code review=Codex+Composer 雙家(ORCH §1;我曾憑印象只派單家連錯三批)→做成機器閘門 review_quorum_check.sh 接 gate.sh(派 impl-b<N> 前驗前批 quorum,不足拒token,descoped 批次跳過)。CLAUDE.md/memory 訂正。
- **審計**:handoffs/LA0-*(gitignored 本地);attribution=tests/golden/la0/attribution.json。

## ▶▶ 下一站:LA-1(P1 look-ahead 收尾)——新 session 從這裡開始
- **範圍(P1,預設開著但非硬閘,來自 master `handoffs/ICLOOKAHEAD-MASTER.md` P1 節)**:①**regime** `ic_engine.py:1091-1098` rule `nanpercentile(vol,80/20)` **全期** vol 分位→污染 grouped IC(`include_regime_analysis=True` 預設)②**long_short** `long_short_analyzer.py:202` 全序列 qcut(deep 預設 enabled)③fallback silent 紅標。**複用 LA-0 建好的 `momentum/Analysis/pit_stats.py` 七原語**(regime→`pit_expanding_quantile`/percentile;long_short→`pit_expanding_qcut_label`,同 P0-2 家族)。
- **如何開始(新 session)**:①開場先稽核 HANDOFF/ROADMAP/master vs repo 實況(鐵律)②走完整大任務管線:聯合偵察(Claude+三委員平行,聚焦 P1 兩點)→SPEC 起草(Claude)→三家 adversarial→凍結(freeze-stamp)→TODO→逐批 Grok 實作+**Codex+Composer 雙家 code review**(機器閘門 `review_quorum_check.sh` 已強制;grok 實作者不自審)→每批過 review 後 commit→B6 式三方 DATA-CORRECT。③參考 LA-0 全套審計檔 `handoffs/LA0-*` 當範本。
- **前置**:LA-0 branch `feat/ic-la0-p0-impl` 已 push+PR(見下);LA-1 可另開 branch(基於 LA-0 或 main-merged 後)。
- **相關 memory**:`project_ic_analysis_lookahead_remediation`、`feedback_code_review_two_families`(中/大雙家 review)、`feedback_recon_joint_with_committee`。
- **⚠️ deferred(勿現在做)**:粗/精篩 funnel + IC-PERF(特徵上限保護)=**整個 IC Gatekeeper 完成後**才做(使用者 2026-07-16 定,memory `project_ic_feature_selection_funnel`);過渡期跑 IC 傳 feature_filter 別丟全量(否則 OOM)。pre-existing 7 紅(redirect state-leak 測試順序污染,非本 epic)另票。

## (歷史)LA-0 進行細節

## 🔒 (歷史)LA-0(P0)雙凍結——治理階段收尾
- **SPEC**: `docs/IC_LA0_SPEC.md` **v0.5.3 frozen** | **TODO**: `docs/IC_LA0_TODO.md` **v2.3 frozen** | **凍結戳記**: `handoffs/LA0-SPEC-FREEZE-RECONCILE.md`(三家 codex/composer/grok APPROVED,body sha256=`4a666775…`,`reconcile_stamps_check.sh ... codex,composer,grok` **PASS**)
- **治理歷程**: 偵察 4 方→SPEC 4 輪 adversarial(v0.1→v0.5.3)+6 輪 freeze-stamp→使用者裁 FR descope→TODO 3 輪 adversarial(v1→v2.3)。全審計檔 `handoffs/LA0-*`。
- **範圍(誠實)**: P0 三點(rolling IC 窗內 rank / stage5 分位門檻 PIT / stage1 fit_mode 四出口)+ pit_stats 七原語。**FR 已 descope**(FR-FULL 未建,移 1c-FR-FULL epic)。
- **實作合約**: Grok 實作(依額度)/另一方 code review(不自審)/B6 三方 DATA-CORRECT 簽核(含 S2 turnover size n-1→n 明確項)/兩輪斷路器/reconcile 未全 APPROVED→BLOCKED。
- **✅ B0 baseline 完成 + code review 通過**(Grok 實作→codex review 抓 3 項→Grok fix→codex 複驗全 CLOSED):`tests/golden/la0/{gen_baseline.py,BTCUSDT_1h_baseline.json(sha a25e9c12),ETHUSDT_12h_baseline.json(sha e7dc6844),attribution_allowlist.json,before_perf_telemetry_receipt.json,inputs/*}`。schema=`la0_b0_v2`;element 級逐值+timestamp+emitted-end(§G L1 可機械驗,抽驗 64/64 atol=1e-12);分層 manifest(seed la0_b0_stratified_v1,BTC passed=3/rej=12、ETH passed=2/rej=12 兩側可測翻轉);data_cache clean(reporter side effect 導 tmp)。審計 `handoffs/LA0-B0{,FIX}-REVIEW-codex.md`。
- **✅ B1(pit_stats 七原語)完成 + composer review 可過**:`momentum/Analysis/pit_stats.py`(7 原語+pit_valid_mask,MIN_SAMPLES=100,PIT_STATS_VERSION=la0_b1_v1)+`tests/momentum/test_pit_stats.py`(35 passed)+`tests/momentum/test_la0_lookahead.py`(骨架+fixture,B2-B6 skip placeholder)。composer 6 項全 PASS+真 mutation 抽驗(A-E 各打紅);§MS first_valid dense→99/含NaN→119、Numba/chunk 等價、rolling≠global pre-rank(diff 0.161)、B2+ 零 diff。審計 `handoffs/LA0-B1-REVIEW-composer.md`。
- **▶ 進行中:B2(P0-1 rolling IC 窗內 rank)**(Grok 實作):改 `ic_engine.py::compute_rolling_ic` spearman 分支呼 `pit_stats.rolling_window_rank_corr`;填 `test_la0_lookahead.py::test_rolling_ic_pit` mutation;既有測試 migration(test_ic_engine.py 4 nodeid)。**第一個改 IC 引擎核心的批次**。
- **⚠️ 流程修正(使用者 2026-07-15,scar:單家 review 連錯三批)**:中/大 code review=**Codex+Composer 雙家**(ORCH §1 早已明寫,我憑印象只派單家 B0/B1/B2 連錯+誤稱規則沒寫)。**已做成機器閘門** `scripts/review_quorum_check.sh` 接入 `gate.sh`:派 impl-b<N>(N≥1)前自動驗前批 ≥2 非實作者家族 review,不足→拒 token(從 task_id 推導,無 flag 可繞;已測 B0 FAIL/B1/B2 PASS)。CLAUDE.md/memory 已訂正。**Grok=實作者,reviewer 必為 Codex+Composer(勿讓 grok 自審)**。
- **✅ 使用者裁定=每批過雙家 review 後 commit**(給下批乾淨 diff)。分支 **`feat/ic-la0-p0-impl`**。
- **✅ B0/B1/B2 雙家 review 全過 + 已 commit**(5 commits):9b61b5f 閘門+CLAUDE.md / 7f5834e SPEC+TODO / cea27de B0 baseline(legacy 改前,composer 抓污染已重釘 sha a25e9c12/e7dc6844) / 2dd4601 B1 pit_stats(codex 二審 REQUEST-CHANGES ①簽名漂移⑤discriminator→B1-fix 兩輪→codex ①⑤ CLOSED) / 9d98c89 B2 rolling IC(codex+composer PASS)。**每批 reviewer=Codex+Composer(grok=實作者不自審)**。
- **✅ B3(P0-2 mono+turnover PIT)雙家過 + commit**(7debf8e):composer APPROVE + codex 二審 FAIL(③turnover first_valid被null違RULING-5 ⑥contract test假綠)→B3-fix(first_valid=0.0+建真contract test)→codex ③⑥ CLOSED。前端 npm build 綠。
- **▶ B4(P0-3 fit_mode)實作完成、雙家 review 有分歧、B4-fix 中**:composer APPROVE(十項全PASS)但 **codex REQUEST-CHANGES 抓 3 FAIL,其中 #4 是 composer 漏的真 look-ahead**:①**#4** winsorize `_is_type_feature` 讀完整未來序列判 winsorize 分支(截尾True/加未來False)——正是本 epic 要滅的洩漏 ②**#5** constant/coverage 雙重 warmup(first-valid 99→198,多丟99bars)③**#6** API deep-key 真路徑測試(tests/api/test_ic_deep_analysis.py)未交付 ④golden hang(test_flag_off_deep_equal_baseline)待釐清=B6重基準漂移 vs B4卡死。→ B4-fix 派工中(#4 type 改 metadata判定去未來/#5 mask正確組合/#6 補API test/hang診斷)。**雙家再次擋下真洩漏,單家會漏。**
- **▶ 下一步:B4-fix→codex 複驗 #4#5#6 CLOSED→commit B4 → B6 三方 DATA-CORRECT(含 S2 + golden 重基準)。**
- **分支 feat/ic-la0-p0-impl 已 6 commits**(閘門/SPEC-TODO/B0/B1/B2/B3)。未 push(待使用者)。

---
## (以下為歷史 context,LA-0 前)

## ⏸ 1d 已 park(偵察完成、成果保留,待 1c-FR-FULL 後恢復)
- **原因**:四方偵察揭「幽靈接線修復」在 1d 內做不到——`_run_factor_exposure` 無 `portfolio_returns`/`factor_returns` 通道,factor_returns 模組 default-off raise `ModuleUnavailableError`;硬接=誤把 feature 當因子報酬。真報酬序列通道正是 1c-FR-FULL 要建的 → 使用者裁定**先 1c-FR-FULL 再回 1d**。
- **1d 偵察成果(恢復時直接用)**:`handoffs/1d-RECON-{claude,codex,composer,grok}.md` + `1d-RECON-SYNTHESIS.md`。四方 CONVERGED。scope=正名(unexplained≡alpha+雙層幽靈 factor_betas 錯標)+ NaN fail-closed(核心 :112 dropna + :114-121 樣本不足假成功 + 雙檔測試去固化)+ 幽靈清除;exposure/neutralize fillna 家族他票;真 residual IC 歸 Phase 2B。
- **恢復時序**:1c-FR-FULL 建好因子報酬通道後,1d 才能真接迴歸方法。

## ▶ 下一步:1c-FR-FULL(大)——canonical timestamp-aligned factor-portfolio return series 重建
- **範圍**:修 ls_returns reset_index 位置錯位 + 模組資料通道 + breakeven/profitable 實值(取代 1c 內 unavailable 態)。
- **前身**:1c-FR-STOPGAP 已 default-off 下架錯位輸出(B0-B2:8be3056/41c26e0/81724c7);FULL = 正式重建正確序列。docs/IC1CFR_STOPGAP_{SPEC,TODO}.md 為背景。
- **流程(新規 2026-07-15)**:開工前偵察=**Claude + 三委員平行聯合**(見 memory feedback_recon_joint_with_committee)→ 收斂 → SPEC 起草(Claude)→ 三家 adversarial → 凍結 → TODO → Grok 實作/Codex+Composer 審。
- **✅ 聯合偵察完成**:`handoffs/1cFRFULL-RECON-{claude,codex,composer,grok}.md` + `1cFRFULL-RECON-SYNTHESIS.md`。根因=`factor_return_analyzer.py:70-71,:87` reset_index+iloc 位置相減(overlap=0 三方實跑)。**三委員修正 Claude 版**:monotonicity 非同 iloc 病(位置相減在前端 Equity 圖);reporter `sharpe` vs `sharpe_ratio` 鍵錯位。
- **✅ canonical 定案=P1**(使用者 2026-07-15):單標的、逐因子、擇時多空報酬序列(feature∈top→+ret;∈bottom→−ret;中間→0)。**必正名**「單標的因子擇時多空報酬」禁冒充橫截面。P3 橫截面另立未來 epic(非取代,並存)。詳見 memory project_1cfr_full_p1_canonical + `1cFRFULL-RECON-SYNTHESIS.md`。
- **次要 SPEC 待裁(走委員 adversarial 不問使用者)**:中間分位 0 vs NaN、enabled 預設(驗後應 ON)、Equity 圖資料源統一、qcut look-ahead(傾向另票)、Newey-West(二期)、net_ic breakeven/profitable 接 P1 回填。
- **✅ SPEC v0.2**:`docs/IC1CFR_FULL_SPEC.md`(template PASS)。R1 三家 adversarial 全 CONVERGED「需修補」→ 收斂 8 BLOCKING+MAJOR,reconcile `1cFRFULL-SPEC-ADV-R1-RECONCILE.md` 逐一裁決:B1 序列 artifact 通道/B2 公式鎖(mid=0 全序列)/B3 §U discriminator+reporter unwrap/B4 §G 數值 atol+hash/B5 breakeven 閉式(20bps hand-calc)/B7 PRESET-RULING/B8 F4依賴F0-F2。
- **✅ 使用者裁定(2026-07-15)**:**本票一併修 PIT**(P1 分位改 expanding point-in-time,乾淨無前瞻)→ **enabled 預設 ON**(符合 feedback_no_default_off)。
- **✅ R2 三家複驗**:R1 全 CLOSED;R2 新開 PIT scope 補洞(§G 6-bar hand-calc/warmup config/PIT 分位演算法/**winsorize 亦 PIT**〔composer 抓〕/turnover 尺度/§U 分層/consumer-map 補/F2 出口枚舉/F3 fixture)→ **v0.3 全數補齊**(具體 6-bar hand-calc position=[0,0,0,-1,1,0]、warmup_periods=20、winsorize_mode:pit_expanding、M-winsorize/M-turnover mutation)。
- **✅ R3 三家複驗**:R2 OPEN 全 CLOSED,唯一剩 BLOCKING=**Claude hand-calc 數字手算錯**(與 qcut 演算法矛盾,codex/grok 實跑抓)→ v0.4 改 7-bar **pandas 實跑鎖定**(feature=[20,40,10,55,30,5,50]→position=[0,0,-1,1,0,-1,1],mean=0.0042857,已二次獨立實跑 True);winsorize 分位鎖 0.01/0.99;**look-ahead 全檔稽核**(使用者提問觸發:signal 級僅 qcut+winsorize 皆修 PIT;nanstd skip 守衛/quantile_summary 描述性標註,非 signal)。
- **✅ R4**:Codex+Composer FREEZE-OK(各自重跑 7-bar pandas 一致);Grok 抓 winsorize 小樣本內插誤 clip(「無 outlier→identity」不成立)→ 鎖 `winsorize_min_samples=100`(n<100 no-op)。
- **▶ 專項 look-ahead 稽核(使用者 2026-07-15 要求)**:三家各自逐行掃 factor-return 整條路徑(analyzer 每方法+orchestrator 接線+**上游 feature/label**+net_ic turnover),交叉覆核 Claude 四項(qcut/winsorize 已修 PIT;nanstd/quantile_summary 非 signal)。派工中(`b37i60186`/`b7eb99p2c`/`b3kmxcbz2`)。**凍結等此稽核**(可能補 SPEC)。
- **✅ FR 專項 look-ahead 稽核(三家)**:確認 Claude 四項正確但**不完整**——Codex+Composer 抓到**上游洩漏**:①stage1 特徵 winsorize/zscore(fit_mask=None 全期;split 路徑 test 安全)②`return_type=winsorized` label 全期裁尾。綜合 `1cFRFULL-LOOKAHEAD-SYNTHESIS.md`。
- **🔺 使用者裁定(2026-07-15)=深修**:不做有界修,**盤點全 IC Analysis 的 look-ahead 疑慮**(升級成 IC-ANALYSIS-LOOKAHEAD-AUDIT epic)。理由=第一性原理,回測生死類直接完整修(見 memory feedback_first_principles_fix_now)。
- **✅ IC Analysis look-ahead 全面盤點完成(四方 CONVERGED)**:`ICLOOKAHEAD-MASTER.md`。結構性瀰漫;**split 只擋 stage1 winsorize 一部分**。**P0(預設必踩)**:①`ic_engine:290` rolling IC spearman **全序列 pre-rank**(污染 ICIR/門檻/deep 全鏈;`_rolling_spearman` 窗內版存在未用)②stage5 mono/turnover 全窗 qcut→門檻淘汰(預設 0.6)③stage1 winsorize/zscore full-sample fallback。**P1**:regime 分位/long_short/fallback silent/FR。四方實跑證(截未來 bar→早期輸出變)。
- **✅ 使用者裁定(2026-07-15)=先 P0 統一整治,FR 併入**。歷史釐清:IC 之前只做「OOS切分+stage1 train-fit」防線,從未審分析模組內部計算→切分給假安心感(見 memory project_ic_analysis_lookahead_remediation)。
- **▶ LA-0(P0)進行中——聯合偵察✅ 收斂**:`handoffs/LA0-RECON-{claude,codex,composer,grok}.md`+`LA0-RECON-SYNTHESIS.md`。四方 CONVERGED(codex 撞兩輪斷路器 BLOCKED 但讀碼結論被 composer+grok 獨立 receipt 佐證)。**十項修正 Claude 底稿(C1-C10)**:①Fix-A 效能已否證(45s/6400×)→定 **Fix-B 窗內 rank+向量化/Numba**,A 僅 slow oracle ②統一 helper=**原語家族**(rolling_window_rank_corr **非** expanding;expanding quantile/winsorize 另族;P0-1 禁 expanding 冒充)③**OOS split 不擋 P0-1**(rank 在 train∪test)④P0-2 另有 `turnover:49,92` 全域 rank 洩漏(rank_change,317/400 最敏感)⑤zscore **非預設**(standardize=none 不在 schema);預設洩漏主體=percentile winsorize ⑥P0-3 **四出口**(train_mask/pit_expanding/full_sample紅標/unset→fail-closed);最危險=`_run_full_sample_fallback:1015`⑦mono PIT 後**仍輸出 scalar**(不破前端)⑧P0-3=**條件觸發結構性 P0**(split 主幹 train-fit 本身正確)⑨constant/coverage 於 fit_mask=None 亦改特徵宇宙 ⑩P1-3 非全 silent(metadata 已標 oos_guarantees=False)。P1-1/P1-2 不升本票 P0,LA-0 helper 預留 API,LA-1 修。
- **✅ LA-0 SPEC v0.1 起草完成**(吸收 C1-C10,template PASS):`docs/IC_LA0_SPEC.md`。RISK-HIT:a,b,c,d;§P DAG=LA0-0(pit_stats 原語家族)→{LA0-1 P0-1 窗內rank / LA0-2 P0-2 分位+rank_change PIT / LA0-3 P0-3 fit_mode四出口}→LA0-4 FR併入→LA0-5 測試/golden。LA0-RULING 四待裁(走委員):①Fix-B numpy(~0.57s)非Numba ②mono 進閘PIT版(保scalar) ③fit_mode四出口(unset→fail-closed) ④golden 歸因表。
- **✅ 三家 adversarial R1 完成 + reconcile**:`handoffs/LA0-SPEC-ADV-{codex,composer,grok}.md` + `LA0-SPEC-ADV-R1-RECONCILE.md`。三家皆「不可凍結」,收斂 **6 BLOCKING + 5 MAJOR**。關鍵裁決:①**B1 perf**——composer 測逐特徵迴圈 26-83s vs grok 測每窗跨特徵向量化 1-3s,兩 receipt 合證→定案 grok 式向量化(Numba 非本票)+perf gate ≤3s;codex 疑 161k features 待 R2 查證是否跑 filtered ②**B2 mono**——codex 退閘 vs composer/grok 進閘,解法=進閘①+鎖 §P0-2-AGG pit_pool 公式+M-lookahead 主錨改 early bin_t(非 scalar);退閘為 R2 fallback ③**B5 helper**——三家抓缺 `pit_expanding_rank`+qcut 回 label→擴為六原語 ④**B6**——codex 抓 turnover 有 time_series 陣列被前端消費(SPEC「仍 scalar」不實)→鎖 warmup null policy ⑤B3 §G 索引集合+per-t min_samples ⑥B4 歸因表 machine-readable+強制 control 列。M1-M5:fit_mode caller 表/schema default=unset fail-closed/DAG 鬆 LA0-4/遷移矩陣/scope 誠實。
- **✅ R2 三家複驗 + reconcile → v0.3**:`LA0-SPEC-R2-{codex,composer,grok}.md`+`LA0-SPEC-R2-RECONCILE.md`。R2:**B2/M1/M2/M5 CLOSED**(B2 確認**不需退閘**,pit_pool early bin_t n_diff=0);**B1/B6 三家一致 STILL-OPEN** + codex 精讀抓 B3 索引 off-by-one/B4 JSON 未落文/B5 缺 MAD 原語/M3 caller/M4 cache key。v0.3 全關:B1=correctness 優先不擋 merge+Numba/chunked+**相對 SLA ≤50×**(絕對秒在 161k universe 無意義,codex 實跑 batch N100=4s/N150=6.5s 破舊 gate)+chunk 不改結果;B6=**warmup null 保原長**(不裁除,RULING-5);B3 索引改 `[m,n-TR)`+emitted ends;B4 JSON schema+predeclare;B5 加 `pit_expanding_mad`+簽名鎖;M3 逐 caller;M4 regime+cache key。
- **✅ SPEC v0.3**(template PASS):`docs/IC_LA0_SPEC.md`(七原語、§P0-2-AGG、RULING-5 warmup、相對 SLA)。
- **✅ R3**:composer/grok 判可凍結;**codex 精讀抓 5 殘留**(B1 perf 契約矛盾/B3 §V:138 off-by-one/B5 六原語 stale+mad 回傳/M3 caller 錯類/M4 refilter 無 key)——Claude **實測驗證全為真** → v0.4 逐一關閉(perf 改 non-blocking telemetry+correctness 優先/§V 索引同步[m,n-TR)/七原語+mad 回(median,mad)/caller 改正+加真 caller/refilter revalidate)。
- **✅ SPEC v0.4**(template PASS):`docs/IC_LA0_SPEC.md`。
- **✅ SPEC v0.4.1 正式凍結**:freeze-stamp R1 codex+grok REJECT(§C:55↔62 refilter 矛盾,composer 漏)→ v0.4.1 修兩處一致 → R2 三家全 APPROVED(task `20260715-la0-freeze2-{codex,composer,grok}`,body sha256=`5316428…`)→ `reconcile_stamps_check.sh handoffs/LA0-SPEC-FREEZE-RECONCILE.md codex,composer,grok` **PASS**。provenance 已 register-output 指向凍結檔。
- **✅ 使用者 checkpoint(2026-07-15)=直接進實作**。
- **✅ TODO 起草(template PASS,Internal DRAFT)**:`docs/IC_LA0_TODO.md`。§B 批次 DAG=B0(baseline 凍結)→B1(pit_stats 七原語)→{B2 P0-1/B3 P0-2/B4 P0-3/B5 FR}→B6(tests/golden/歸因)。含 SPEC ID 100% 覆蓋追溯表。
- **✅ TODO 三家 adversarial 完成 + reconcile**:`LA0-TODO-ADV-{codex,composer,grok}.md`+`LA0-TODO-ADV-RECONCILE.md`。三家皆「不可 Frozen」(codex 10 BLOCKING+2 MAJOR)。**在寫碼前**抓到兩項觸及 SPEC:
  - **S1 FR descope(scope 變更,知會使用者)**:`_run_factor_return:1808` 現直接 `ModuleUnavailableError`——**FR-FULL 未建**(stopgap default-off)。LA0-4「FR 併入/byte 一致」是假前提。**裁決=FR 移出 LA-0**,LA-0 只交付 pit_stats 原語(FR-ready);FR 實接線歸**獨立 1c-FR-FULL epic**(對齊原始分工)。
  - **S2 turnover 輸出大小**:現碼 `diff().dropna()` 長度 n-1;RULING-5 warmup=null 保源長 n=相對 legacy **+1**,「大小不變」不實 → 裁為**刻意 schema 變更**(對齊源 index,JSON null),須前端/API contract test + B6 三方明確簽核。
  - 純 TODO 級 T1-T10:B0 baseline 須可重現 stage1/4/5/七原語簽名鎖死/constant-coverage per-bar ruling/Numba+chunk 落 TODO/allowlist 移 B0 前 predeclare/M3-leakage 測試改 pytest.raises 列全 nodeid/fit_mode 進 ic_config_schema+yaml/mutation nodeid+跨symbol perturb oracle/既有測試逐列 migration。
- **✅ SPEC v0.5.1 重凍結**:freeze3 codex REJECT(§C:55↔62 已 v0.4.1 修;再抓 LA0-5 依賴殘留 LA0-4)→ v0.5.1 修 → freeze4 三家 APPROVED(task `20260715-la0-freeze4-*`,body sha256=`cdb2d3c…`)→ `reconcile_stamps_check.sh` **PASS**。codex 連兩輪抓 descope 交叉引用殘留(機器 hash gate 價值)。
- **✅ TODO v2 三家 adversarial(2 輪)+ reconcile**:v2(T1-T10 CLOSED 除 T4/T5/T10 外殘留)→ v2.1。TODO v2 揭一項觸及 SPEC:**C-T2 first-valid 語意錯**(hard-code index=min_samples,無 NaN 第 100 有效樣本是 t=99)→ **SPEC v0.5.2 新增 §MS 唯一定義**(min_samples=COUNT;valid⟺effective_count≥m;first_valid=computed)。TODO v2.1 套 T1(B0 輸入契約)/T3(per-bar mask)/T6(leakage 全 nodeid)/T7(schema+standardize+API 真路徑)/T8(test 骨架移 B1)/T9(migration nodeid)/S2(types.ts null 契約)。
- **▶ 進行中:合併最終輪**(背景 `20260715-la0-freeze5-{codex,composer,grok}`):SPEC v0.5.2 §MS 蓋戳(body sha256=`f992277…`)+ TODO v2.1 複驗。全 APPROVED → SPEC+TODO 雙凍結。
- **▶ 下一步:雙凍結 → B0 baseline(gen_baseline 可重現 stage1/4/5+allowlist predeclare)→ 逐批派工實作(Grok)+ 另一方 review + B6 三方 DATA-CORRECT(含 turnover size S2 明確簽核)**。
- **✅ 治理產物已 commit+push**(2026-07-15,branch `docs/ic-lookahead-remediation-gov`,commit `3da0a0a`):docs/IC1CFR_FULL_SPEC.md v0.4 + HANDOFF + ROADMAP + gate audit。審計鏈 handoffs/ 為 gitignored 本地工作檔(未進版,符慣例)。
- **➡️ 下個 session 從這裡接手 LA-0(P0)**:①聚焦偵察(Claude+三委員)**只針對 P0 三點**——P0-1 rolling IC 窗內 rank(啟用 `_rolling_spearman`)/P0-2 stage5 分位 PIT/P0-3 stage1 fallback→②SPEC 起草→③三家 adversarial→④凍結→⑤實作+三家 DATA-CORRECT。FR v0.4 SPEC 併入統一 PIT helper。
- **⚠️ 勿重工**:全 33 模組 look-ahead 盤點**已完成**(master=handoffs/ICLOOKAHEAD-MASTER.md,含 P0/P1/P2 全清單+實跑證,gitignored 本地在)。新 session 的偵察=**從 master 起、聚焦 P0**,**不要**再全模組重掃。P1/P2 待 P0 後續 Phase。

## ✅ 上個 session 完成(兩票全入版 push)
1. **1c Net IC 量綱正確化**:治理(SPEC 五輪+TODO 六輪三家 adversarial)+實作 B0-B3 四批(f1d85c5/2133c77/04ac6fb/77af3d3)。B-strict=禁 IC 減報酬率/`net_ic` 鍵全樹禁絕/成本去 ×2/成本前端輸入 fail-closed(5bps 寫死三處拔除)/per-rebalance 語意註記。docs/IC1C_NETIC_{SPEC,TODO}.md。
2. **1c-FR-STOPGAP(錯位因子報酬輸出止血)**:四方委員會揭「無消費者」前提不成立(錯位 ls_returns 預設 enabled+活在 reporter/UI)→使用者裁定立即止血。實作 B0-B2 三批(8be3056/41c26e0/81724c7)+缺口補提(4481c53:phase29 quarantine 漏 git add)。default-off 三態契約+統一收斂 sanitizer(codex 三輪實證揪 save_report/cache-hit/cache force-merge 三洩漏路徑)+AST consumer guard+前端兩圖三態下架。docs/IC1CFR_STOPGAP_{SPEC,TODO}.md。

## 之後排序
④ **1d attribution**(park 中,見上;1c-FR-FULL 後恢復)。
⑥ 1f 空圖 schema flatten→實測→AI Agent。

## 📌 慣例/環境
- Grok 審查/實作一律 `--sandbox workspace` 直接寫檔;grok 家族入 `reconcile_stamps_check.sh` 第二參數。
- pytest collect 副作用 `tests/golden/l65/test_inventory.txt` 每次 revert(勿 commit)。
- `docs/API_SPECIFICATION.md` 有 1 行尾空白未 commit(session 前既存,非本工作;小債另清)。
- 全套件 baseline nodeids=77(1cfr B0 凍結),止血後 current=44;`scripts/ic1cfr_stopgap_freeze.py --check-nodeids` 為 fail-closed 機械 gate。
- 全套件既有紅(~數十)非近期引入;`--before`/`--check-nodeids` 跑全套件約 >10 分鐘(本機易逾時,可交委員代驗)。
- 派工三家 code review 一律另一方(實作者不自審);兩輪解不了交委員會/斷路器換手。

## ⚠️ 未 commit
docs/API_SPECIFICATION.md(session 前既存尾空白,非本工作)。其餘全入版。
