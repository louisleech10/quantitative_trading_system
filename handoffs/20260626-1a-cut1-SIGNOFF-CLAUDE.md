# 1a 第一刀 — 三方數據簽核：Claude 獨立簽核（leg 1）

> 我獨立驗收（不信執行端 DONE），自跑測試 + diff 防假綠 + 讀核心實作 diff + 回歸判定。

## 結論：Claude ✅ 簽「資料正確、無洩漏」（待 Codex/Composer 兩腿）

## 我實際做了什麼（可證偽）
1. **獨立跑 1a 全測試**：`pytest test_ic_1a_cut1_{split,leakage,oos,golden}.py test_factories.py` → **27 passed**（執行端報 25，含 factory 2 共 27）。
2. **防假綠**：`git diff --name-only | grep test` → **無既有 tracked 測試檔被改**（1a 測試全為新檔），既有斷言未被放寬/刪除。
3. **回歸判定**：tests/api IC 測試 13 ERROR → `git stash` 1a tracked 改動後在**乾淨 HEAD 同樣 13 ERROR** → 確認**既有 deep-analysis/export task 超時 flaky，非 1a 回歸**。stash pop 已還原。
4. **解耦**：`grep -rE "from api\." momentum/`→0；`check_decoupling_phase4.sh` PASS（含 135 strategy tests）。
5. **G-OLD byte 守恆**：flag-off deep-equal baseline（pop `generated_at`）PASS。

## 核心防洩漏邏輯審查（讀 diff）
- **train-only fit**（`data_preprocessor.py`）：`fit_mask` 貫穿 winsor/standardize/coverage/constant；fit 用 `df.loc[mask]`（train 子集）、apply 仍全段；length 不符/全 False→raise；None→全段（byte 守恆）。ffill 全段＝causal 無 lookahead。**正確**。
- **holdout + purge**（`_build_holdout_split_plan`）：positional；`split_point=floor((1-oos_test_size)*n)`；`effective_purge=max(purge_gap,horizon)`；test 起點=`split_point+effective_purge` → **purge 區行不入 train 也不入 test**；`purge_gap<horizon→raise`。**杜絕 train 末標籤用 test 價格**。
- **horizon fallback**：`_resolve_effective_label_horizon` = `default_horizon in horizons ? : horizons[0]`，與 stage2 一致 → purge 綁對 horizon。
- **遮罩跨 stage**（`_derive_stage_masks`）：用 train/test `time_bounds`(timestamp) ∩ current index；event_filter 後**重導**；overlap→raise → **event_filter 刪列不錯位**。
- **OOS 口徑**：stage4 IC 用 test 子集；rolling 全段算後 `_slice_rolling_ic_to_test`（option A warmup，無洩漏：報告值在 test 索引）；warmup 不足→skipped；decay/stage5/stage6 用 test。**口徑一致**。
- **flag gating**：flag-off→split_context=None→全原路徑。**byte 守恆**。

## 我未能獨立完全確認、交給另兩腿 adversarial 重點查
- rolling option A 的 `_slice_rolling_ic_to_test` 是否真的只保留 test 時間索引、無 train 期 IC 值混入 icir/p。
- `_derive_stage_masks` 對「event_filter 在 train/test 邊界附近刪列」的極端情形是否仍時間互斥。
- min_test_rows=131 對 BTC/1h（20352 列、test 20%≈4070）充足，但其他 tf 待 cut1 範圍外。
