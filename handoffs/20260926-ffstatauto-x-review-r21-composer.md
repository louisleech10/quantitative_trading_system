# FF-STAT SPEC v40 審查 r21 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R21  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R21-BRIEF.md`  
標的：`git diff 3ff787e1 38ca2137 -- docs/FFSTAT_SPEC.md`；r20 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r20/synth.md`；裁定 R8/R9 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針 `/tmp/ffstat-r21-work`（真實 kline／longhist，禁合成 fixture）。

## COMPOSER-R21-P3-00

**斷言**: 本輪逐項核對 v40 差分（R8 長歷史 §G⑦ 12h、R9 五週期倍數表、§A 下載收據、§N 刪 §G⑦ blocked 條、§P 收據清單、Task 2.3/2.4 對齊）後，未發現可重現之新 P0／P1 SPEC 缺陷；r20 本家 sentinel 與 v39 閉合條款未被 v40 改寫推翻。

**碼證**: `git diff --stat 3ff787e1 38ca2137 -- docs/FFSTAT_SPEC.md` → 10 insertions／9 deletions；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`rg -n 'longhist|5m、1h、4h、12h、1d|6656|cache_dir' docs/FFSTAT_SPEC.md` → §A:23、§C:61、§G:90、Task 2.4:118–119、§N:175、§P:154 同輪對位；`h5py` 讀 `data_cache/feature_klines_longhist/kline_cache.h5` `BTCUSDT/12h/data` → rows=6656（與 §A FACT-RECEIPT 一致）；`estimate_max_warmup_bars` 預設全設定 primary=12h → 2051，資格下界代理 `2×2051+500=4602` 與 `3×2051+500=6653` 均 ≤6656（§G⑦ 資格未在條文層被 6656 根否證；實跑 §G⑦ 收據屬 impl）；`momentum/factories.py:236-251` `create_feature_factory(cache_dir=…)` 注入 `KlineStorageManager`，與 §G:90「測試以儲存層 cache_dir 指向」一致；brief fact L7 `dead_feature_filter.py:77-82`、`talib_wrapper.py:316,347` 逐字核對成立。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#9060a56e2903; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0; handoffs/run_receipts/20260927-ffstat-longhist-download.log#download6656; handoffs/reconcile/20260926-ffstatauto-x-review-r20/synth.md#composer-r20

---

## 必答

1. **(1a)** 本家 r20 僅 **COMPOSER-R20-P3-00**；v40 未撤回 v39／r19 已入正文之 §C／Task 2.4／§P 條款，**可閉合**。**(1b)** 逐字核對 v40 diff：`§G:90` 將 12h 自「只出 blocked 收據（§N）」改為 longhist 預設全設定＋一般資格；`§N` 刪除原「§G⑦ 12h 預設全設定 blocked-by 1696 根」條目；Task 2.3 ① 與 §G⑦ 12h 改為「longhist 雙起點並行、互不替代」；§P 將 manifest 收據由「§G⑦ blocked」改為「各週期收據＋長歷史下載」。未發現 v40 新句與 R8/R9 裁定或 r20 採納結論衝突。

2. **(2a)** v40 差分內**無**新 P0／P1。**(2b)** 否證：longhist BTC 12h 6656 根存在；模板檢 PASS；未重跑預設全設定 FF（brief 禁止）；邊界 6656−6653=3 列餘量提示 impl 階段須以收據記錄真實 K_max_tf／F_max_tf，非 v40 條文自相矛盾。

3. **(3a)** brief **fact-verified** ① L7 不以 NaN 率判死欄 → **成立**（`notna().sum()`／`nunique`）。② TA-Lib 經 `compute`／`compute_batch` → **成立**。**assumed**「6656 根滿足 §G⑦ 資格 M_tf＋F_max_tf＋500」→ **條文層條件性成立**：以 `estimate_max_warmup_bars=2051` 為 F_max／K_max 上界代理時 6656≥6653，餘量極小，最終以倍數表採用 K 與全設定 run 之 F_max 收據為準（否證路徑見 brief）。**(3b)** `/tmp/ffstat-r21-work/eligibility_probe.txt`：`btc_12h_rows 6656`、`estimate_max_warmup_bars_12h 2051`、`threshold_3est_plus_500 6653 pass True`。

4. **(4a)** brief「我沒查」：**①** 測試以 `cache_dir` 指向 longhist——**未命中** v40 缺陷（factory 已支援注入；測試接線屬 impl／TODO，§G 已明寫機制）。**②** 5m×105260 於量測腳本 eval 窗／cap——**未命中**本輪 SPEC 字面（Task 2.4 只增週期列舉，未改腳本常數；效能風險留 impl）。**③** ADA 12h 較晚起點對跨標的取 max——**未命中** v40 新矛盾（§A 收據已列 ADA 6171 根；R4「跨標的取最大」仍成立）。**(4b)** `momentum/factories.py:236-251`；`handoffs/run_receipts/20260927-ffstat-longhist-download.log` ADA 列數；§N:180 未在 v40 diff 內改動 → 依 brief 不在本輪新 finding 範圍（仍描述 kline_cache 12h 校準 holdout，與 Task 2.3 仍用 `kline_cache.h5` 一致）。

5. **(5a)** **是**，v40 可 **`VERDICT: proceed`**（R8/R9 落實與 r20 閉合未遭 v40 差分否證；本輪無 P0／P1）。**(5b)** 無。

---

ASSUMPTIONS_VERIFIED: 已讀 brief、template、governance 類別集、v40 diff、r20 synth、R8/R9；longhist HDF5 列數；fact L7/TA-Lib 行號  
TESTS_RUN: `git diff --stat 3ff787e1 38ca2137 -- docs/FFSTAT_SPEC.md`；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → PASS rc=0；`rg` v40 錨點；eligibility probe → rc=0；開跑／收尾 `git status --short -- momentum api scripts tests docs templates config` 一致  
FAILURES_SEEN: eligibility probe 初回 `ConfigManager` import 路徑錯誤 rc=1，改正 `config_manager` 後 rc=0  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r21-composer.md  
TMP_CLEANUP: `rm -rf /tmp/ffstat-r21-work` 執行前保留 `/tmp/claude-501`（若環境拒絕刪除則照實記錄）

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R20-P3-00

STATUS: DONE
