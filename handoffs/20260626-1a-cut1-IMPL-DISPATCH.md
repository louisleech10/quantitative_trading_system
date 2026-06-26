# 1a 第一刀 — Codex 實作派工指令（B1-B5）

你是嚴謹的實作者。**先完整讀**（讀不到要求貼全文，不得假裝）：
- SPEC：`docs/IC_PHASE1_1a_CUT1_SPEC.md`（規格，含 §C 約束/§G Golden/§N N/A）
- TODO：`docs/IC_PHASE1_1a_CUT1_TODO.md`（逐 Task 檔案到函式 + §B 批次 + 派工塊）
- 憲法：`CLAUDE.md`、`docs/DEVELOPMENT_GUIDE.md`（解耦 7 條、不可違反原則、命名、測試慣例）

## 範圍與鐵律
- **實作 §B 的 B1→B2→B3→B4→B5（依序）**。B6（三方簽核 + 凍 G-NEW + 切 default ON）**不在你範圍**，由 Claude 主導。
- **flag `ic_train_test_split` 一律預設 OFF**，不得切 ON（簽核後 Claude 才切）。
- **真實資料**：所有資料正確性測試用 `data_cache/feature_klines/kline_cache.h5`，**禁合成 fixture 代替**。
- **防假綠**：不得放寬/刪除既有測試斷言；gap/purge<horizon/跨 symbol 反例必真 `pytest.raises`，不得降級 warning；train 段擾動不得改變 test 結果。
- **不可做（§N + 各 Task）**：不改 service/前端；不重寫 CPCV/WF 切分數學；不改 `contracts.py`/`ic_split_adapter.py` 既有方法內部；不用 `index_kind="timestamp"`（用 positional + time_bounds）；不刪舊全段路徑（flag off 共存）。
- **G-OLD baseline 已由規劃端凍**於 `tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h_a384e6d2.json`（config_hash `a384e6d22ca15fc639757cb3162e7cb3`）；B5 Task 5.2 令 flag-off deep-equal 此檔，**不得重凍**。

## 測試檔授權（修正：原派工塊漏列）
- **每批「允許改檔」清單，一律含該批各 Task 驗證所列的 pytest 測試檔**——這些新測試檔（`tests/momentum/test_factories.py`、`tests/momentum/Analysis/test_ic_1a_cut1_split.py`、`test_ic_1a_cut1_leakage.py`、`test_ic_1a_cut1_oos.py`、`tests/golden/ic_phase1_1a_cut1/test_ic_1a_cut1_golden.py`）**是 Task 交付物，由你建立**。
- 測試檔可新增/修改；但**不得放寬或刪除既有（其他）測試的斷言**換綠燈。
- `tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h_a384e6d2.json` 已存在（G-OLD），**唯讀不得改**；deep-equal 比較時兩側 pop `generated_at`。

## B3 卡關根因修正（Claude 查證，2026-06-26）
- **B1+B2 已 PASS（11 測試綠），working tree 已留存；本次從 B3 續做。**
- **B3 block 根因＝你的測試 fixture 用了無效值 `max_fill_forward=0`**（`test_ic_1a_cut1_leakage.py:44,110,116`）。pandas `ffill(limit=0)` 直接 raise「Limit must be greater than 0」。**真實 config 預設＝3**（`ic_config_schema.py:31`），生產從不傳 0（G-OLD baseline 用預設 3 凍成功）。
- **修法**：測試 fixture 一律用**有效值**（`max_fill_forward>=1`，建議用真實預設 3）。`test_coverage_from_train_only` 要驗「coverage 只看 train」用**注入 NaN 列**即可，不需也不該把 fill limit 設 0。`test_preprocess_legacy_no_mask_unchanged` 用真實預設跑。
- 修好 fixture 後 B3 應綠 → 續 B4、B5。

## 每批次流程（嚴格）
1. 依該批派工塊（TODO §B）的「允許改檔」實作，逐 Task 達成驗證。
2. 跑該批驗收 pytest + `grep -rE "from api\." momentum/ | wc -l`==0。**綠燈才進下一批**。
3. 每批結束在 `handoffs/20260626-1a-cut1-IMPL-CODEX.md` **追加**一段：批次、改了哪些檔/函式、跑了哪些 test（名稱）、pass/fail、遇到的問題。

## 斷路器（鐵律）
- 任一批次 bug/test/疑問**自己弄 ≤ 2 輪仍失敗 → 立即停手**，在 handoff 寫 `STATUS: BLOCKED — <精確原因 + 你試了什麼 + 卡在哪>`，**不准 solo 連續試錯燒額度**。Claude 會開委員會。
- 不確定規格意圖 → 在 handoff 標 `NEEDS-CLARIFY: <問題>`，不自行假設。

## 完成輸出
全部 B1-B5 綠燈 → handoff 末尾 `STATUS: DONE — B1-B5 complete, flag default OFF, G-OLD deep-equal PASS`。
任一卡關 → `STATUS: BLOCKED — ...`。
