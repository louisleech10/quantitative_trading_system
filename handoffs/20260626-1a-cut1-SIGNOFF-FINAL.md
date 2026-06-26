# IC Phase 1 1a 第一刀 — 三方數據正確性簽核：PASS（最終，R2）

> 鐵律（2026-06-09）：split/leakage 正確性須 Claude+Codex+Composer 三方獨立簽，真實 kline，不靠使用者驗收。

## 三方齊簽 PASS（R2，修補後）
- **Claude ✅**：獨立自跑 30 測試 + 防假綠（無既有斷言放寬）+ 回歸判定（tests/api 13 ERROR 為既有 flaky 非 1a）+ 核心 diff 審查（train-fit/holdout/purge/mask/OOS）+ G-OLD deep-equal PASS。
- **Composer ✅（非作者）**：R2 獨立重跑 R1 兩反例——LEAK-1 purge 擾動 rolling/icir Δ=0、LEAK-2 type-only 分支不變；**且確認修補前模擬會 FAIL（新測試真可證偽）**；30 PASS、解耦 0、G-OLD PASS。
- **Codex ✅（作者自挑戰）**：R2 重跑 R1 原反例——`LEAK1_ROLLING_EQUAL True`/`ICIR_EQUAL True`/`ALLOWED_EXCLUDES_PURGE True`、`LEAK2_TRAIN_OUTPUT_EQUAL True`；舊行為模擬 `OLD_WOULD_EQUAL False`（可證偽）。

## 收斂軌跡（adversarial 抓到 confirm-review 漏的洞 → 修 → 再挑戰）
- R1：Codex 作者自挑戰用真實 kline 反例抓 2 真 LEAK（Claude+Composer confirm-review 皆漏）→ [[feedback_adversarial_beats_signoff]]。
  - LEAK-1：rolling OOS 把 purge rows 算進 test 視窗（purge forward label 引用 test 價格）。
  - LEAK-2：winsorize type-feature skip 分支用全段資料（test 值翻轉分支改 train 輸出）。
- 修：LEAK-1 rolling 改用 `train|test` allowed universe 排除 purge hole；LEAK-2 type 判斷改 fit slice；embargo 接線；補 3 不變量測試。
- R2：兩反例經三方獨立重驗**真關閉**，新測試經模擬確認**真可證偽**。

## 已關閉的洩漏向量
- train-only fit（winsor/standardize/coverage/constant + type-feature 分支皆 fit slice）。
- holdout purge_gap >= effective horizon（含 horizon fallback）；purge 行不入 train/test。
- rolling OOS option A warmup 排除 purge hole（只 train|test allowed universe）。
- stage5 monotonicity/coverage/turnover + passed_features 同源 OOS；decay/grouped/redundancy test scope。
- embargo 推遲 test 起點。
- `_derive_stage_masks` time_bounds 重導 + overlap raise（event_filter 後不錯位）。
- flag-off G-OLD deep-equal（pop generated_at）byte 守恆。

## 殘留（cut2/follow-up，§N，不阻本刀）
- 次路徑 reanalyze_with_thresholds/deep analysis 未帶 split_context（cut2）。
- stage4 回傳全段 label_series（主鏈已 slice，rename/註記）。
- 部分 stage5 測試用 mock ic_results（補真實鏈 E2E，可維護性）。

## 驗收
30 測試 PASS；解耦 grep=0 + check_decoupling_phase4 PASS（135）；真實 kline_cache.h5；G-OLD byte 守恆。**簽核通過 → 凍 G-NEW + 切 default ON。**
