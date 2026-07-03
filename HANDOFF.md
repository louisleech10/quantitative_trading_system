# Handoff
**Agent**: Claude | **Time**: 2026-07-03 | **Branch**: main

## fracdiff max_lag 大 epic（P1-FF-6 併入）✅ 主體完成（本次 commit）
- **修復**：`_resolve_fracdiff_max_lag` seam（auto=calibration_bars//10=50，len(df) 解耦）+ config 顯式 `max_lag: Field(ge=0)`（修掉 pydantic 靜默丟棄=逃生口本是幽靈）+ fracdiff FFT 卷積改 direct（`_hurst_prior._convolve_1d`+孿生 `_frac_diff_convolve`，尾擾捨入洩前綴）。
- **值守恆三方簽核 PASS**：Claude+Codex(adversarial)+Composer 檔載「PASS」（出處:20260703-FRACDIFF-MAXLAG-CONSERVATION-{claude,codex,composer}.md）。§G 四條件檔載「passed=true, failures=[]」（出處:run_receipts/20260703T085226Z-fracdiff-maxlag-postfix-compare.json）：修後 auto≡修前 pin50 全欄 digest 0 差異、非 fracdiff 0 差異、G2' config 路徑≡修後。
- **⚠️ 兩 MR 未轉綠（誠實 xfail，reason 已換）**：掀開後暴露 pre-existing **storage codec bug**（per-column float16/32 依全窗值域選型→精度不可比；已確認根因，R3 雙戳記，ROADMAP 新 P1 立案）。max_lag 面護網=d\* gate+3 mutation 探針（094044Z PASSED）+full_fit/calibration 單邊控制（132059Z 檔載「1 passed」）+P1-FF-6 七 mutant（053419Z）。
- **Composer code review 閉合**：檔載「FINAL VERDICT: APPROVED」（出處:20260703-FRACDIFF-MAXLAG-REVIEWCLOSE-composer.md）。
- **b6 golden 已重生**：test_warmup_flag_off_golden_baseline_check 檔載「1 passed」（修後 max_lag 行為）。
- 管線留痕：雙家族 adversarial+3 輪委員會+4 份雙戳記 reconcile 全 register（audit.log）；golden 大檔（7.5GB artifacts+397/199MB json）已 gitignore，入庫證據=SUMMARY+compare receipt。

## 次站
1. **IC 用 FF 定版重生成**：使用者手動觸發；先討論 config/symbols/TF（10×3 全量）。B1 codec 殘留對固定窗全量跑無影響（單 run 自洽），已載簽核聲明。
2. storage codec epic（P1，ROADMAP 新節）：修完兩 fracdiff MR xfail 轉綠。
3. Review NON-BLOCKING 跟進項見 REVIEWCLOSE-composer.md。

## 鐵律（慢測試/執行）
- generate_features ~20分/次;slow 跑後 `./scripts/restore_golden_inventory.sh`;長測試後清 pytest 舊輪次(留 pytest-current)。
- HANDOFF/commit 寫「已驗/passed」須帶 VERIFY:<receipt-id> 或「檔載『…』(出處:檔名)」。委員會過程檔派工帶 --task-id+--output,產出後 register-output。
- pre-existing 失敗=test_ic_engine(非深稽)。派工執行端可能誤還原根 HANDOFF——commit 前重驗內容。
