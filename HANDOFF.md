# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-19 | **Branch**: **main** | **狀態**: ✅ **1c-FR-FULL 完工並合併 main;下一站=1d attribution**

## ✅ 1c-FR-FULL 完工並合併 main(merge ca872d5,已 push;branch feat/ic-1cfr-full-impl 可刪)
- canonical=單標的逐因子擇時多空(PIT expanding,winsorize 四方一致移除);功能 enabled=True 上線。
- TODO R1→R3.1 四輪 adversarial 凍結 → 7 批 B0-F5(Grok 實作/Codex+Composer 雙審,每批 Claude 獨立驗) → **三方 DATA-CORRECT 全 PASS**(Claude+Codex adversarial+Composer;PIT無前瞻+跨symbol隔離+hash+正名)。
- final gate 94 passed 0 skip/xfail + net_ic 36;check-nodeids REAL_EXIT=0;decoupling R2=1 R3=17 R4=2。
- 產物:`momentum/Analysis/factor_return_analyzer.py`(手刻 `_pit_expanding_position`+`FactorTimingReturnSeries`+`get_series_map()`)、series owner `orchestrator._factor_return_series`、`FactorReturnChart`/`NetICChart`。審計 handoffs/1cFRFULL-*+ic1cfr_full_baseline/(gitignored 本地;json/txt 已 commit)。
- 踩坑:派工勿加 `&`(detach harness,用 run_in_background:true);`pytest|tee`/`|tail` 遮蔽 exit code(Claude 一度誤報 check-nodeids exit0,codex 抓到→驗 gate 用真實 `echo $?` 不經管線)。

## ▶ 下一站=1d attribution(偵察已完成,四方 CONVERGED;handoffs/1d-RECON-*)
**scope(使用者 2026-07-15 定)**: 正名 + NaN fail-closed + **幽靈接線修復**;真 residual IC 歸 Phase 2B(1d 不做)。
- **幽靈接線**:`factor_exposure_analyzer.py:104-148 calculate_factor_attribution` 全 production path **未接**(只有定義+測試呼叫);`_run_factor_exposure:1924-1977` 回寫死 stub;orchestrator `:1959-1970` 巢狀+頂層雙層鏡像 `factor_betas/alpha/r_squared/unexplained`(頂層 `factor_betas`=曝險錯標)。
- **🔑 接真方法本卡 1c-FR-FULL(現已解鎖)**:`_run_factor_exposure` 手上只有 feature 水準值+label+等權 positions,**無 factor_returns 序列**;硬接會誤把 feature 當因子報酬迴歸(新事故)。**1c-FR-FULL 已提供 `get_series_map()` PIT 序列**→ 評估是否用它接真 attribution,或維持正名+fail-closed 為主。
- **正名**:`unexplained`(:147)= `beta[0]` = 與 alpha 同值(非殘差);另 `factor_betas`(=曝險)、UI `FeatureTierPanel.tsx:50`「因子曝險歸因」混用。
- **NaN fail-closed(1d 核心)**:`:112` dropna 靜默丟列 + `:114-121` 樣本不足(<10列)靜默回全 NaN/空 dict;雙檔測試 `test_nan_factor_returns_exposure`/`test_factor_attribution_insufficient_rows`(momentum+phase25 孿生)固化靜默→須去固化。
- **默認他票**(改 Radar 主圖,非 attribution):`:36/44/54/59/64/73`(neutralize)、`:84`(vol)、`:94/101`(portfolio exposure)、`:155`(concentration)。
- **開工**:大任務管線=開場稽核 HANDOFF/ROADMAP vs repo→SPEC(Claude 起草)→三家 adversarial→凍結→TODO→逐批 Grok 實作+Codex+Composer 雙審→三方 DATA-CORRECT。範本=handoffs/1cFRFULL-*+LA2-* 全套。**先聯合偵察複核**(1d-RECON 是 2026-07-15,開工前抽驗行號是否漂移)。

## 📌 慣例/環境(沿用)
- 派工走 `scripts/cx_run.sh <codex|grok|composer> <brief> <output> [effort]`(絕對路徑+固定 template)。Grok=實作者;reviewer=Codex+Composer;gate.sh dispatch/artifact 開 token+register-output;RECONCILE-STAMP 機檢(reconcile_stamps_check.sh)。
- 每批 Claude 獨立驗 diff+跑驗收+mutation 可證偽(monkeypatch→FAIL 才算有牙),再雙審閉合(原提出方 re-verify)。
- 委員 /tmp workdir 收尾清理(留 claude-501);`tests/golden/l65/test_inventory.txt` 勿 commit(collect 副作用)。
- pre-existing:decoupling baseline R2=1 R3=17 R4=2(另票);IC 跑 feature_filter 別全量(OOM)。
