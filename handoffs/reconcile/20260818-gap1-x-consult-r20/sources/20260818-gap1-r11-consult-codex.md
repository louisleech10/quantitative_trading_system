# GAP-1 G1-R11 諮詢 — Sharpe 常數／近常數序列

## Metadata

- task-id: `20260818-GAP1-X-CONSULT-R20`
- family: `CODEX`
- round: `R20`
- mode: 唯讀研究；未改碼、未改測試、未 commit、未 push
- scope: `compute_sharpe`、PBO path-level Sharpe、業界實作與文獻之零波動處理
- conclusion: 採 exact all-equal guard（主委方案的語意），不採相對容差；見 `CODEX-R20-P2-01`

## Scope

本產出只回答 brief 的 A–E，並把「常數」限定為輸入陣列的 exact encoded values 全相等。它不主張從 float64 反推出原始十進位字串或業務上的「意圖相等」。

## Mechanical precondition

- 本檔是 consult producer artifact；沒有建立 reconcile session，也沒有宣稱 RECONCILE final stamp。
- `completeness_check.sh --single ... --family codex` 會在檔案完成後執行；其 rc 是本輪交件的機械驗收結果。
- 本輪沒有可依賴的 SPEC/TODO RECONCILE-STAMP；brief 明確將本輪定義為唯讀研究。

## §0 挑戰前提

| brief 前提 | 查證結果 | 證據 |
|---|---|---|
| `compute_sharpe` 以 `std == 0.0` 判退化 | 確認 | `momentum/Analysis/strategy_validation/sharpe.py:73-90`；函式 docstring 與實際分支一致。 |
| 80 個 `0.01` 可得非零 std 與巨大 SR | 確認 | timeout probe：`std=1.7456682121588365e-18`、`ptp=0.0`、`value_per_period=5728465426791027.0`。 |
| `np.ptp(np.full(80, 0.01)) == 0.0` | 確認 | 同一 probe；`np.all(values == values[0])` 亦為真。 |
| 業界主流多數不特判／inf／NaN，且無相對容差 | 部分確認、需收窄措辭 | 本輪讀 empyrical、quantstats、vectorbt、pandas、SciPy；前四者的 Sharpe／std-like 路徑沒有相對容差，SciPy `zmap` 有 exact all-equal guard。不能把五個來源外推成全業界定律。 |
| 真實資料管線不會產生同一意圖值的不同 double | 未能確認；反例可構造 | 同一 float32 值升成 float64 仍全相等；但 `float('0.01')` 與 `float('0.010000000000000002')` 是不同 double。管線在 `returns_contract.py:73-78` 先做 pandas pct-change，再轉 float64，已失去原始十進位 provenance。 |
| exact-equality 修法不改 PBO golden 三案例 | shadow probe 確認 | 未改碼，以 `np.ptp==0` shadow guard 跑三案：noise `0.6482683982683982`、alpha-detectable `0.0`、alpha-undetectable `0.5411255411255411`；各 `exclusions=0`、`skipped=0`、`used=924`。 |

## A. 業界／科學 Python 實作

本輪實際讀取五個真實 source；以下的「無 ε」只對列出的版本／commit 路徑負責，不外推所有金融軟體。

| source | zero / near-zero 行為 | `ptp`／all-equal／相對容差 |
|---|---|---|
| [empyrical `stats.py`](https://raw.githubusercontent.com/quantopian/empyrical/master/empyrical/stats.py#L607-L672) `sharpe_ratio` | `len < 2` 先回 NaN；其後 `np.divide(nanmean, nanstd)` 直接除。exact zero-mean/zero-std 會是 NaN，非零均值／zero std 依 NumPy 產生 inf。 | 無 zero-std 分支、無 ε、無 `ptp`／all-equal。 |
| [QuantStats `stats.py`](https://raw.githubusercontent.com/ranaroussi/quantstats/main/quantstats/stats.py#L771-L824) `sharpe` | `divisor = returns.std(ddof=1)`，再 `returns.mean() / divisor`；沒有 zero guard。zero denominator 的 scalar 結果依 pandas/NumPy 除法為 inf 或 NaN。 | 無相對容差、無 `ptp`／all-equal。 |
| [vectorbt `returns/nb.py`](https://raw.githubusercontent.com/polakowo/vectorbt/master/vectorbt/returns/nb.py#L309-L319) `sharpe_ratio_1d_nb` | 明確 `if std == 0.0: return np.inf`；它把 exact zero volatility 視為 inf，而不是 NaN。 | 只有 exact `std == 0.0`；無 ε、無 `ptp`／all-equal。 |
| pandas 2.3.2 `pandas/core/nanops.py:908-1020` | `nanstd` 呼叫 `sqrt(nanvar)`；`nanvar` 以 sum/mean 與 `(avg-values)**2` 的兩遍計算，沒有先問所有元素是否相等。因此 exact encoded constant 可能因 mean 累加捨入留下非零 variance。 | 無相對容差、無 all-equal guard；這正能重現本票的浮點殘差來源。 |
| SciPy 1.13.1 `scipy/stats/_stats_py.py:620-667,780-826,2798-2811,3088-3103` | `tstd` 只是 `sqrt(tvar)`，沒有 zero guard；但 SR-like 的 `zmap` 另以 `_isconst` exact equality 判定常數，設置 std 避免除零並把該輸出設 NaN。 | exact all-equal；無相對容差。SciPy 的做法支持「先判 exact equality，再決定退化」的語意，但 `zmap` 的回傳契約不是 Sharpe 契約。 |

### A 結論

沒有一個本輪列出的 Sharpe 實作採用相對容差。觀察到的慣例不是單一業界標準：empyrical／quantstats 直接除、vectorbt 回 inf、專案契約要求 NaN＋非 ok；SciPy 的另一個標準化統計則示範了 exact all-equal guard。這支持以契約而非外部套件偶然輸出決定本專案行為。

## B. 文獻

1. **Sharpe (1994), *The Sharpe Ratio***：Stanford 原文以 differential return 的平均與標準差定義 ex ante／ex post Sharpe；ex post 的實作例是 `AVERAGE(C1:C60)/STDEV(C1:C60)`（[原文 §The Ex Post Sharpe Ratio](https://web.stanford.edu/~wfsharpe/art/sr/SR.htm#THE_EX_POST_SHARPE_RATIO)）。文中沒有對零標準差另立 ε、容差或 all-equal 規則。若分母為零，定義本身是奇異／無有限比率；這不等於應回報一個巨大有限 SR。
2. **Lo (2002), *The Statistics of Sharpe Ratios***：原文把 SR 寫成 `(mu - Rf) / sigma`，樣本估計由 mean 與 variance 得到（[PDF p.37，原文行 73–96](https://traders.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf)）。IID 推導假設有限 mean／variance（p.38，行 181–192），delta-method 導數含 `1/sigma` 與 `1/sigma^3`（p.38–39，行 228–240）；`sigma=0` 因而是公式的奇異邊界，不是可用相對 ε 修補的正常估計情形。本文未提出 zero-volatility 的 sentinel 或容差。
3. **Bailey & López de Prado (2014), *The Deflated Sharpe Ratio***：PSR/DSR 使用樣本長度、前四階矩、SR estimates 的 variance 與試驗數（[PDF p.8–9，原文行 270–323](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)）；其說明也明確把 estimated SR 建在 mean 與 standard deviation estimates 上。所查定義／推導段沒有 zero-volatility 特例、ε 或 `ptp` 規則。

### B 結論

文獻支持「零波動時統計量不可計算／需由上游標記不可用」而非「塞入 ε 使 SR 變成大數」。文獻沒有替本專案選出某個相對容差；因此自創 `1e-12` 類常數沒有文獻依據。

## C. 主委方案的反例與資料管線

### C1. `ptp==0` 的邊界

- 對已通過 finite gate 的 ndarray，`np.ptp(values) == 0.0` 與所有 encoded values 相等的意圖一致；`np.all(values == values[0])` 更直接，避免用 `max-min` 做額外浮點運算，也避免極端有限值 range 的溢位警告。
- `[0.01, 0.01, 0.010000000000000002]` 的第三個值是不同 float64；本 probe 的 `ptp=1.734723475976807e-18`，故 exact-equality guard 不會把它當常數。這不是 guard 漏掉「已知相同 double」，而是輸入本身並非 encoded constant。
- `np.full(80, np.float32(0.01), dtype=np.float64)` 的每項升轉結果相同，`ptp=0`；重複同一 CSV token 在本地 pandas 2.3.2 parser 也得到相同 double。這兩個常見路徑不構成反例。
- 但不同運算路徑可以產生同一實數意圖的不同 binary encoding，例如 Python `float('0.01')` 與 `float('0.010000000000000002')`；一旦輸入已轉成 float64，沒有原始 decimal/provenance 就無法可靠判斷使用者意圖。相對容差可把它們合併，卻同時會把真實極低波動序列合併，且需要未授權的新常數。

### C2. 本專案路徑

- `momentum/Analysis/strategy_validation/returns_contract.py:73-78` 從 equity curve 做 `pct_change()` 後 `to_numpy(dtype=float)`；這是計算後的浮點序列，不保留原始文字精度。
- `sharpe.py:82` 再以 `np.asarray(..., dtype=float).ravel()` 收口；因此常數判定應明確寫成 exact encoded equality，而不是聲稱「同一十進位值」的語義 canonicalization。
- 實作上建議使用 `std == 0.0 or np.all(values == values[0])`。brief 提出的 `np.ptp(values) == 0.0` 可行，但 `all` 形式更接近斷言且少一次 range 算術；finite gate 已先行，所以 NaN 不會污染 equality。

## D. 對 PBO 的影響

`momentum/Analysis/strategy_validation/pbo.py:143-154` 的 `_sharpe_pp_1d` 複製了 `compute_sharpe` 的 n<2／finite／std guard；若修法只改 `sharpe.py`，PBO 會與主 Sharpe 語意分叉。因此同一 logical patch 必須同步改兩個 guard，或抽出共用 exact-equality predicate（是否抽 helper 由實作 review 決定，本輪不改碼）。

### 實跑 receipt

1. `timeout 120 venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_pbo.py -q` → **17 passed**, 2 precision-loss warnings，rc=0。三個 golden 測試均 PASS。
2. shadow probe（未修改 repository；僅以 `patch.object(pbo, '_sharpe_pp_1d', shadow)` 注入 `std==0 or np.ptp==0`）加 `timeout 120`，尾端 `STATUS: DONE` →
   - noise: `value=0.6482683982683982`, `exclusions=0`, `skipped=0`, `used=924`
   - alpha-detectable: `value=0.0`, `exclusions=0`, `skipped=0`, `used=924`
   - alpha-undetectable: `value=0.5411255411255411`, `exclusions=0`, `skipped=0`, `used=924`
   - shadow `np.full(80, 0.01)` → NaN；shadow `0.01 + linspace(0, 1e-9, 80)` → finite。

因此 exact-equality guard 不改 golden 三案例，也不改其 path exclusion 計數；它只修正本來應被判定為 exact constant、但被 variance reduction rounding 產生非零 std 的輸入。

## E. 修法歸類

判定：**實作 bug 修補，不是語意變更**。

理由：Task 1.2 的既有字面契約已寫「常數序列 ⇒ 退化 ⇒ NaN＋status 非 ok」，而 `std == 0.0` 只是目前用來近似判常數的實作；在 exact encoded constant 上被浮點累加誤差繞過，是實作未忠實實現既有契約。`ptp/all_equal` 不會把真正有 distinct encoded observations 的 `0.01 + 1e-9*k` 誤殺，故沒有引入「近常數皆退化」的新語意。

建議後續走小任務＋三家 code review，至少覆蓋：`compute_sharpe` exact non-binary constant 回 NaN、`0.01 + 1e-9*k` 仍 finite、PBO `_sharpe_pp_1d` 與主函式一致、以及既有 PBO golden 三案不變。若未來要把不同 double 視為同一 decimal/業務值，才是另立 precision/provenance 語意，需另開票，不應在本修補中塞相對容差。

## CODEX-R20-P2-01

**斷言**: `ptp == 0`／`all(values == values[0])` 只辨識 exact encoded equality，不能辨識「同一數學／十進位意圖但不同 double 表示」；採主委方案時必須把這個 scope 寫進契約或測試說明，否則使用者可能把不同 double 誤讀成 guard 漏判。

**碼證**: `momentum/Analysis/strategy_validation/sharpe.py:82-92` 先將輸入收口為 float64，再以 std 判退化；timeout probe 觀測 `np.full(80,0.01)` 的 `ptp=0.0` 但 std `1.7456682121588365e-18`、SR `5728465426791027.0`；同 probe 的 `[0.01,0.01,0.010000000000000002]` 為 `ptp=1.734723475976807e-18`；`returns_contract.py:73-78` 的 pct-change→float64 路徑沒有原始 decimal provenance。

**來源摘要**: `momentum/Analysis/strategy_validation/sharpe.py#cdaa1007c3b7`

正文：這是非阻塞的語意邊界，不是要求發明 ε。exact-equality 修補可先收斂 G1-R11；後續若產品真的需要 decimal-level canonicalization，應另定輸入精度／來源契約，並用可追溯 provenance，而不是在 Sharpe 分母上增加全域相對容差。`np.all(values == values[0])` 比 `np.ptp(values) == 0.0` 更直接；兩者都不應被描述成「數學實數相等」判定。

## Verdict

- [x] **CONDITIONAL — 採主委方案**：將退化判定擴為 `std == 0.0 or exact all-equal`；不採相對容差；PBO 同步採同一語意。
- [ ] 改為相對容差
- [ ] 維持現狀不修

條件只有一個：實作與測試需明示這是 encoded-value equality，並同步覆蓋 `compute_sharpe` 與 `_sharpe_pp_1d`。本輪沒有改碼或替主委建立 final stamp。

## Source index

- `momentum/Analysis/strategy_validation/sharpe.py` — sha256 `cdaa1007c3b7ca02c075f3a5c4ebc68107af7e2e2eed41f394d1bffc3d270fcf`
- `momentum/Analysis/strategy_validation/pbo.py` — sha256 `740afb68f1eaec06a93ed255f7278d7aa366f9678ecc91c6de27320a39a2a14a`
- `momentum/Analysis/strategy_validation/returns_contract.py` — source path／行號如上；本輪未改
- `tests/momentum/Analysis/strategy_validation/test_pbo.py` — sha256 `dcdb0a2621632e3641e190549bbd945df2023cf05631e5b9d3378179d5ccacb8`
- `tests/momentum/Analysis/golden/gap1_reference_cases.json` — sha256 `09a04b67168d571f1b1ec48cbfbfa0c402fd301bccd09a5b60d15bad1e95c418`
- local packages: pandas `2.3.2`, sha256 `pandas/core/nanops.py#909a58a96838`; SciPy `1.13.1`, sha256 `scipy/stats/_stats_py.py#ecdcb8f5f058`

STATUS: DONE
