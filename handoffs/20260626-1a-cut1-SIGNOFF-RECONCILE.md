# 1a 第一刀 — 三方數據簽核 reconcile（R1：未通過，2 真 LEAK 待修）

> Claude(leg1) ✅ / Composer ✅(4 MINOR) / **Codex ❌ 不簽**(自挑戰抓 2 真 LEAK)。
> 鐵律：任一方有疑→不通過。又一次 [[feedback_adversarial_beats_signoff]]（Claude+Composer confirm-review 漏，Codex 作者自挑戰用真實 kline 反例現形）。

## 必修（BLOCKING，Codex 反例證明）
- **[LEAK-1] rolling OOS 含 purge rows**：`_stage4_ic_calculation` 用全段算 `rolling_ic_full`(含 purge 行)再切 test 端點；首批 test rolling 視窗成員含 purge 行，purge 行 forward label 引用 test 價格 → 污染 test IC/ICIR/passed_features。反例：只擾動 purge label → test rolling IC 變(ICIR 1.34→1.16)。
  **修法**：flag-on rolling 輸入須**排除 purge rows**——只用 `train_mask | test_mask` 的 allowed rows 重組 universe 再算 rolling；保留視窗成員不得含 `~train_mask & ~test_mask`。
- **[LEAK-2] winsorize type-feature 分支用全段**：`data_preprocessor.py:100` `_is_type_feature(series)` 對 full series 判斷（fit_mask 只用於後續 quantile）；test 值翻轉 skip→winsorize 並改 train 輸出。反例復現。
  **修法**：type-feature 判斷改用 **fit slice**（`_select_fit_series`），不得由 test 分布決定 preprocessing 分支。逐一審「先分類再 fit」型邏輯，非只看統計量是否用 fit_mask。

## 一併修（Composer 抓，潛在/可維護）
- **[FIX-embargo] embargo>0 未推遲 test 起點**（Composer #1 ADV-9）：`test_rows = arange(split_point+effective_purge, n)` 未加 embargo；config_override 設 embargo>0 時 test 含 embargo 禁區。修：test 起點 `+ config.embargo`；補 embargo>0 可證偽測試。
- **[FIX-test] purge-hole 不變量測試**（Codex MINOR#3 / Composer#4）：`test_ic_1a_cut1_oos.py` 用 `test_mask=~train_mask`(無 purge gap)→驗不到 LEAK-1。改用真實 `_build_holdout_split_plan()` 產生的 train/test mask（含 purge gap），加「擾動 purge rows label 不得改變 test rolling IC/ICIR」不變量（會抓 LEAK-1）+「test-only 值不得改變 winsorize 分支/train 輸出」（會抓 LEAK-2）。

## Follow-up（cut1 範圍外，§N 登記，不阻本刀）
- Composer #2：次路徑 `reanalyze_with_thresholds`/deep analysis 未帶 split_context（`_ic_cache` 不存 split_context）→ cut2/follow-up。
- Composer #3：stage4 回傳全段 `label_series`（主鏈 stage5/6 已自 slice，安全）→ rename/註記。

## 環境註記
- Codex pytest 2 error+1 fail＝read-only sandbox 寫 `data_cache/reports`/tmp_path 受限,非真失敗。G-OLD deep-equal 已由 **Claude + Composer 在可寫環境 PASS**。

## 下一步
派 Codex 修 LEAK-1/LEAK-2/FIX-embargo + 強化測試(purge-hole 不變量) → 重跑 → **三方重簽**(Codex 反例須轉為「擾動 purge/test 不再改變 test 指標」PASS;Composer 重查;Claude 重審)。三方齊 PASS 才凍 G-NEW + 切 default ON。
