# MR 5F2P 診斷三方 reconcile（Claude 編，round 2）

> 2026-07-03 | 三腿：MRFAIL-{CODEX,COMPOSER}.md + FACTS 內 Claude 腿 + Claude artifact 追蹤（本檔 §New）
> 待兩委員 append RECONCILE-STAMP。

## §New Claude artifact 追蹤（兩腿都沒跑完的那步，已完成）

pytest-82 殘留 artifacts 實測（`test_fracdiff_truncation_invar0/features/BTCUSDT/1h/{46acde…,4de8d…}/raw/1h_L2_Momentum_chunk4.parquet`，欄 `volume_1h_momentum_MACDEXT-Hist_13-55-13_Momentum_L144`）：
- full(2081) leading_nan=210,total_nan=210；trunc(2071) leading_nan=210,total_nan=211。
- 前綴唯一 NaN 分歧 = **idx 508（內部單點，非前導帶）**：full=-8.72、trunc=NaN；idx 509 兩者皆有限但值不同（-11.48 vs -8.555）；idx 510 起完全一致。
- 型態=「近零分母 cell 的 finite↔NaN 翻面 + 鄰點值差」，**非決策翻面型、非 NaN band 位移型**。

## 三方收斂結果

| 議題 | Codex | Composer | Claude | 收斂 |
|---|---|---|---|---|
| B2 根因 | FFT convolve 捨入（**已複現**：FFT prefix drift ~1.5e-10、direct conv 精確 0） | 同（HIGH），parallel 以 probe 排除 | float 抖動假說 | ✅ **FFT 捨入，非洩漏** |
| B1 根因 | 縮窄：materialization/上游，非 max_lag | 同；點名 float16/32 codec 依全窗值域選型 plausible；ADF disabled 擊斃 Claude 假說 | ADF 假說（❌被擊斃）→ artifact 證據支持 codec/近零分母敏感 | ✅ 縮窄至 **materialization 精度路徑**（首選：per-column codec 依全窗 stats → 長度洩入精度 → 近零分母 cell 放大） |
| Q3 定性 | pre-existing（blame+判準） | pre-existing | pre-existing | ✅ **兩者皆 pre-existing，被 xfail 遮蔽；非本 epic 引入** |
| Task 1.4 掃描 | 成立 | 成立（grep 無第二推導點） | — | ✅ 不被推翻 |
| Q4 | 已修（窗長由 `_fracdiff_window_bars` 推導） | — | — | ✅ |

## 裁決案（供兩委員核可）

1. **B2 修法（本 epic 內收）**：`_hurst_prior._convolve_1d` 的 FFT 分支改為 fracdiff 路徑一律 direct convolution（現行 max_lag≤252、典型 50，O(n·w) 廉價；FFT 門檻 4096 是舊大窗遺產）。**不放寬 atol**。
   - **定序防衝突（證據已落）**：修後對照（R vs G1/G2，FFT 尚在）已完成——receipt 檔載「PASSED=True, failures=[]」且逐條件：條件1 R vs G2 全欄 0 差異（BTC/ETH 皆 fd_diff=0, nonfd=0）、條件2 R vs G1 非 fracdiff 0 差異+fracdiff 4546/3435 欄不同+G1 實際 max_lag=208 落檔、條件3 G2'（真 config 路徑）vs R 全欄 0 差異、條件4 R/G2' resolved max_lag==50（出處：handoffs/run_receipts/20260703T085226Z-fracdiff-maxlag-postfix-compare.json）。§G 條件 1/2/3/4 以 FFT 一致基礎閉合，max_lag 隔離已證；conv 修復隨後獨立 commit，其 oracle = 尾擾 MR 轉綠 + 截斷 MR 的 fracdiff 值 gate 綠 + 全 fracdiff 護網 mutation 綠。兩段分開，等價鏈不混。
2. **B1 處置（본 epic 內：定性+精確 xfail；修復另立案）**：root cause 已縮窄未單行定位（codec 假說需 storage 層 trace）。截斷 MR 的 warmup mask gate 對該類 cell 維持紅 → `test_fracdiff_truncation_invariant` 暫掛 **新 reason 的 xfail(strict)**：「pre-existing materialization 精度路徑截斷變異（非 max_lag；證據=MRFAIL 三腿+idx508 artifact）；修法=storage codec/精度 epic」。**d\* gate 與 fracdiff 值 gate 已由 mutation 探針+尾擾 MR（conv 修後）覆蓋**，不因此 xfail 失去 max_lag 防護。
   - ROADMAP 立案「FF materialization 截斷變異（codec 依全窗 stats）」P1，附全部證據連結。
3. **簽核範圍聲明**：三方值守恆簽核文件必載「B1 pre-existing 殘留、影響=近零分母 cell 級 NaN/精度翻面、與 max_lag 修復無關」——IC 定版重生成前使用者可見。
4. Q4 修復隨 B2 conv 修復一起入下一輪 slow 驗證（目標：尾擾 MR 綠、3 mutation 綠、截斷 MR 僅剩 B1 xfail）。

> 版本歷史：v1 遭 codex REJECTED（2026-07-03 sha256:06cea176… task:fracdiff-maxlag-mrfail-stamp-codex-20260703，理由：裁決案1把 §G 閉合寫成既成事實但 compare receipt 未產出——防偽紀律正確攔截）。v2=補上 20260703T085226Z receipt 實據後重送（本區上方為 v2 本體）。

## 戳記區（委員 append，勿改上文）
RECONCILE-STAMP: codex APPROVED 2026-07-03 sha256:c317de8f368b86b8e18796cf954502b8993823167fc1157a9b1db10292a4fa3b task:fracdiff-maxlag-mrfail-stamp2-codex-20260703
RECONCILE-STAMP: composer APPROVED 2026-07-03 sha256:c317de8f368b86b8e18796cf954502b8993823167fc1157a9b1db10292a4fa3b task:fracdiff-maxlag-mrfail-stamp2-composer-20260703
