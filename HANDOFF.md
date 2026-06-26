# Handoff
**Agent**: Claude | **Time**: 2026-06-27 | **Branch**: main

## ✅ 完成:IC Phase 1 — 1a 第一刀(單幣縱向 train/test 切分接線)
讓 1-contract 防洩漏紅線真正生效於 IC 主流程 `analyze()`:holdout 切分 + winsor/standardize/coverage/constant **train-only fit** + IC/統計在 test(OOS) 報告 + **purge_gap≥label horizon**(防前瞻)。**三方數據簽核 PASS,default ON。**

### 全程(完整管線,留痕 handoffs/20260626-1a-cut1-*)
- 規劃:BRIEF→manifest(26 ID)→SPEC/TODO v2(docs/IC_PHASE1_1a_CUT1_*)→**兩輪雙家族 adversarial**(共 9 BLOCKING 全納)→Frozen,四機檢 PASS。
- 實作:Codex B1-B5;**三方簽核 R1 抓 2 真 LEAK**(rolling 含 purge / winsor type 分支用全段)→修→R2 三方齊 PASS。
- **凍 G-NEW(真實全 run)抓到 _slice_by_mask index 整合 bug + grouped raw 對齊** → FIX2 → 真實 run 成功。
- **切 default ON 量爆炸半徑** → default-ON 語義委員會定案**分因回退**(insufficient→full-sample+標記;irregular_ts→維持 raise) → FIX3。
- 驗收:34 測試 PASS、3 洩漏不變量、G-OLD flag-off deep-equal、G-NEW(scope=test)、解耦 0;tests/api 既有 timeout 經 clean-HEAD 確認**非 1a 回歸**(env/網路 flaky)。

### 教訓/紀錄
- [[feedback_adversarial_beats_signoff]]:Claude+Composer confirm PASS 漏的洩漏,Codex 作者自挑戰反例現形。
- 驗證面逐層擴大(單元→簽核→真實全 run→default-ON 爆炸半徑)各抓不同層 bug。
- G-OLD/G-NEW baseline 大檔已 gitignore(skip-if-absent,本地用 freeze 腳本再生)。

## ★殘留/follow-up(§N,非阻塞)
- fallback 的 `applied:false`/`reason` 僅內部,輸出層只 surface `metadata.scope`(test vs full);安全(fallback≠test 不誤判 OOS)但 reason 透明度可補。
- 次路徑 reanalyze_with_thresholds/deep analysis 未帶 split_context → cut2。
- stage4 回傳全段 label_series(主鏈已 slice,介面 rename)。
- tests/api IC task 既有 timeout(env 網路 flaky)+ skipped 標 completed 語義 → 獨立修。

## ★下一個:1a 第二刀 = cross_sectional 防洩漏(analyze_cross_sectional),再 1-align→1b FDR→...(見 ROADMAP / phasing-CONVERGED §Phase1)
