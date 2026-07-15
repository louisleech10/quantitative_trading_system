# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-15 | **Branch**: main | **狀態**: pivot → 先做 1c-FR-FULL 再回 1d(使用者 2026-07-15 定)

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
- **▶ 下一步:LA-0(P0)remediation** — 開工前聯合偵察(Claude+三委員)P0-1 rolling IC 窗內 rank(啟用既有 `_rolling_spearman`)+P0-2 stage5 分位 PIT+P0-3 stage1 fallback→SPEC 起草→三家 adversarial→凍結→實作→三家 DATA-CORRECT(a,d)。FR v0.4 SPEC 已凍結就緒,併入統一 PIT helper。
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
