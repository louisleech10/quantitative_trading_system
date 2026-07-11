# IC 1e+1b B5 Code Review — Codex

審查對象：Grok 的 G-1/G-2/G-3 與 Claude 的 1a 解鎖；自報未採信。SPEC reconcile body hash=`b77932d8…`，雙 stamp APPROVED。

1. **G-1 — PASS（附非阻塞 FINDING）**：`test_ic_1eb_b5_golden.py:44-87` 唯讀載入 manifest、驗 inputs、覆蓋 13 顆；`assert_g1_invariant` 逐一比五 hash、order、三種 series hash；helper 直接復用 capture 的 hash/patch。快顆實跑 `1 passed in 16.24s`；將 expected `values_sha256` 改成 0×64 後實跑轉紅。FINDING：`ic1eb_b5_replay.py:165-195` 對 xsec reader 的任意 Exception 都改走非 capture 的 premat fallback，若 fallback 恰可滿足欄位，便不是同構重放。
   - 可證偽反例：改 `ic_mean` 一位或 feature order，五 hash/order 會紅；令 reader 丟非資料缺失例外而 premat 欄完整，可證明 catch-all 會換程序。

2. **G-2 — PASS（方向措辭限於證據）**：生成器為 `scripts/ic1eb_g2_golden_diff.py`。抽樣 `long_BTCUSDT_12h_f754aad4 / close_12h_momentum_MACD-Hist_55-233-34_Momentum_L55`：`p_iid` 復算=`1.5706764709679516e-26`，`p_hac` report/diff=`0.3740857985595313`，BH q 復算=`0.7277137800103383`（report=`…382`），pass `True→False`、reason=`removed:p_value`；window_63 lag-1=`0.9794826792`。273/273 old-only 均 `p_hac>p_iid` 且均因 p 閘；5160/5482 全體 comparable p 上升。真資料 p_hac 的獨立 statsmodels 抽算兩次逾 60s 已棄；另跑 kernel oracle `1 passed in 1.29s`，故不宣稱該真資料 p_hac 已獨立復算。
   - 可證偽反例：將該列 q 改 1e-3，`multipletests(..., fdr_bh)` 復算立即不等；「273 全為高自相關」仍未逐列量測，只能聲稱轉紅方向與抽樣高自相關相符。

3. **G-3 — FINDING（BLOCKING）**：四測實跑 `4 passed in 12.86s`，xsec exception type 對 receipt；但 `test_ic_1eb_b5_golden.py:93-120` 只證 p=NaN，沒有依 prompt/SPEC 斷言「p 閘 fail」；`:149-153` 在 expected_raise receipt 缺失時 skip，而非 fail-closed。現有 `test_passes_threshold_inverse_and_nan` 只傳 `None`，未把上述三種 kernel NaN 接到 stage5 閘。
   - 可證偽反例：讓 stage5 對 NaN p 放行而保持 kernel 回 NaN，B5 三個 NaN 測試仍綠；刪 manifest 的 expected_raise entry，xsec 測試變 SKIP 而非紅。

4. **newpath freeze — PASS**：manifest 有 13 report、per-run name-set/p-q-t aggregate hash、passed hash、G-1 hashes、fraction；13/13 report streaming sha 與 manifest 相符，per-feature diff sha 相符，manifest sha=`0aa54b2d…` 與 MD 相符。12h 實數為 0/499 或 1/498–500（0–0.002008），與 manifest/MD 一致且非大量失效。
   - 可證偽反例：改任一 report 一 byte，`report_sha256` 鏈立即斷。

5. **1a 解鎖 — FINDING（BLOCKING）**：兩 golden 檔 sha 與新 meta 相符，測試本輪完成且編排端已報 2 passed；但 provenance 不成立。854d444、c0b29ac、現行 `freeze_baseline.py:99-107` 都沒有 flag-off override，而 `ic_train_test_split` 自 d3b2dff 引入即預設 `True`，不是「預設漂移」；現行 old baseline scope=null/FDR ON，meta 宣告的 freeze command 會跑 scope=test，不能重產它。`freeze_baseline_new.py:146-153` 又把 reproduction command 錯寫成 old script，meta request 也漏 `config_override`。`original_regen/README:3-4` 稱依原程序且雙 commit 內容相等，但只留一份 artifact，且 archive sha=`f4046d33…` 與 Grok c0b 記錄 `2b5e4ca6…` 不同；`quarantine/README:5-6` 仍稱現況 2 skip/B5 待辦，現已失真。
   - 可證偽反例：依 meta 原命令跑 old freeze，輸出 scope=test 而非 baseline_old 的 scope=null；若雙 commit normalized 相等，應保留兩份 hash/receipt，現有產物無法驗證此主張。

TESTS_RUN：G-1 fast 1p；G-1 values-hash mutation red；G-3 4p；1a 命令完成（編排端另驗 2p）；HAC oracle 1p；freeze/report/hash/fraction 與 G-2 sample ad-hoc 復算。兩個真資料 p_hac probe 各逾 60s 終止。
SCOPE_CHANGES：僅新增本檔；l65 inventory `git status` 無變更，未 restore。NUMERIC_OR_SCHEMA_IMPACT：審查未改數值/schema。

VERDICT: BLOCK
