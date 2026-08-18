# GAP-1 G1-R11 諮詢 — grok | task-id=20260818-GAP1-X-CONSULT-R20

brief-kind=consult；家族=grok；輪次=R20；禁改碼／禁 commit／禁 push；只產本檔。

## Verdict：採主委方案（`std==0.0 or np.ptp(values)==0.0`）；反對相對容差；不維持現狀

理由（一句）：業界 Sharpe 實作對零波動要嘛直接除、要嘛 **精確** `std==0`→NaN／inf，**無相對容差、無 ptp**；本專案 SPEC／TODO 驗收字面是「**常數序列** ⇒ NaN」，而 `std==0.0` 無法辨識「全元素同一 double、但樣本標準差因求和捨入非精確 0」之常數（實測 80×`0.01` → `ptp==0` 且 `std≈1.75e-18` → 巨大 SR），故改用 `ptp==0`（或 `max==min`）是對「常數」量測的實作修補，不是另發明 ε。

建議落地：小任務改 `sharpe.py:89` 與 `pbo._sharpe_pp_1d` 同步；更新 `test_vectorized_sharpe_matches_compute_sharpe` 對 `0.01` 欄之斷言（巨大有限 → NaN）；三家 review。**勿**加相對容差。

---

## §0 挑戰前提

| # | 前提（來源） | 判定 | 證據摘要 |
|---|---|---|---|
| F1 | `compute_sharpe` 退化條件為 `std == 0.0`（`sharpe.py:89`） | **fact 成立** | 本輪讀碼：`:88-90` `if std == 0.0 or not np.isfinite(std)` |
| F2 | 80×`0.01` → `std≈1.75e-18`、SR≈5.7e15、非 NaN | **fact 成立** | 本輪實跑：`std=1.7456682121588365e-18`、`value_per_period=5728465426791027.0`、`status=ok`；`ptp=0.0` |
| F3 | `np.ptp(np.full(80,0.01))==0.0` | **fact 成立** | 同上實跑 |
| A1 | 業界主流對 std=0 多數不特判或回 inf／NaN，且無相對容差 | **assumed → 坐實** | 見段 A：≥5 套件源碼；Sharpe 路徑無相對 ε、無 ptp |
| A2 | 真實資料管線不會產生「同一數學值、不同 double」之常數序列 | **部分不成立** | 見段 C：`0.01` 與 `0.1*0.1` 異源混合會；CSV／同構 float32→64／常見字面構造則不會 |
| A3 | `ptp==0` 修法不改 golden 三案例 | **assumed → 坐實** | 見段 D：`test_pbo.py` 17 passed；noise 矩陣 `any_ptp0=0`；模擬 ptp 謂詞對 golden 基底無新增退化欄 |

---

## A. 業界實作（源碼行號）

| 套件 | 位置 | std=0／近 0 怎麼辦 | 相對容差？ | ptp／all-equal？ |
|---|---|---|---|---|
| **empyrical** | `empyrical/stats.py` `sharpe_ratio` ≈L700–717 | `nanmean/nanstd` 直接 `np.divide` 再乘 √ann；無特判（0 分母 → NaN／±inf） | **無** | **無** |
| **quantstats** | `quantstats/stats.py` `sharpe` ≈L841–892 | `returns.mean()/divisor`（`std(ddof=1)`）；無零檢查。`sortino` ≈L1041：`downside==0`→NaN。`risk_return_ratio` ≈L2404：`std==0`→NaN | **無**（僅精確 `==0`） | **無** |
| **ffn** | `ffn/core.py` `calc_sharpe` ≈L1434–1458 | `np.divide(mean, std)` + `errstate(divide/invalid=ignore)` → 可出 inf／NaN。`calc_information_ratio` ≈L1484：`diff_std==0`→**0.0**。年化 sharpe 外層 `if yearly_vol > 0`（精確） | **無** | **無** |
| **vectorbt** | `vectorbt/returns/nb.py` `sharpe_ratio_1d_nb` L338–348 | **`if std == 0.0: return np.inf`**（精確相等 → +inf） | **無** | **無** |
| **pyfolio** | `pyfolio/timeseries.py` L262–290 | 直接 `return ep.sharpe_ratio(...)`（委派 empyrical） | **無** | **無** |
| **pandas** | `pandas/core/nanops.py` `nanstd` | 純樣本標準差；80×`0.01` 仍得 `std≈5.2e-18≠0`（本輪實跑）；無「近常數」語意 | **無** | **無** |

附註：empyrical／vectorbt 的 **beta** 路徑有 `variance < 1e-30 → nan` 絕對地板，但那是 **beta 變異數**，**不是** Sharpe 的相對容差；Sharpe 本身不用。

**結論 A**：主委 assumed「無相對容差」成立；業界亦**無**人以 `ptp`／`all equal` 當 Sharpe 退化條件。本專案若加 `ptp==0`，是比業界更對準「常數序列」字面，且與既有 `std==0` 並存、不引入自創 ε。

---

## B. 文獻

- **Sharpe (1994)** *The Sharpe Ratio*：SR＝超額報酬／σ；σ＝0 時比值在定義上不適合作為風險資產排序指標（無風險／退化邊界），文獻未給「近零波動」之相對 ε。
- **Lo (2002)** *The Statistics of Sharpe Ratios*：推導 SR 抽樣分配時假設 σ>0；未定義相對容差把近常數抹成退化。
- **Bailey & López de Prado (2012 PSR／2014 DSR)**：PSR／DSR／Mertens V[SR] 皆以觀測 SR 與高階矩為輸入，分母含 σ 或 V[SR]；σ→0 時觀測 SR→±∞、檢定語意崩壞——實務上應標 **unavailable／degenerate**，而非用自創相對 ε 把「數學上巨大但有限」的近常數 SR 改寫成 0。文獻**沒有**授權 `std <= ε·|mean|` 這類參數。

與主委立場一致：近常數但 `ptp>0`（真實微擾）之巨大 SR 是公式正確輸出；應用 DSR／顯示層處理，不該在 `compute_sharpe` 用 ε 抹掉。

---

## C. 主委方案反例（異 double 表示）

本輪探針（`/tmp/grok-gap1-r20`）：

| 構造 | `ptp==0`？ | 說明 |
|---|---|---|
| `np.full(80, 0.01)` | **是** | G1-R11 本尊；`ptp` 修法可抓 |
| CSV 字串 `'0.01'`×20 → `loadtxt` | **是** | 同構解析 |
| `float32(0.01)`→`float64` 同陣列 | **是** | 每元素同一位元型樣 |
| `[0.01, float('0.01'), 1e-2, 10**-2, 1/100]` | **是** | 常見字面／運算同構 |
| `[0.01, 0.1*0.1, …]`（`0.1*0.1 == nextafter(0.01)`） | **否** | 異源構造；`ptp≈2.2e-10` |
| brief 例 `[0.01, 0.01, 0.010000000000000002]` | **否** | 第三值＝`nextafter(0.01,1)`；`all_eq=False` |

**判定**：assumed「管線不會產生異 double」**不絕對成立**——只要把 `0.01` 字面與 `0.1*0.1`（或其它進位路徑）混進同一序列就會。但：

1. 同構生產路徑（常數廣播、CSV 同字串、同 dtype 轉型）**不會**踩雷，而 G1-R11 的 80×`0.01` 正是同構路徑。
2. 異源微差之 `ptp>0` 表示序列在 IEEE 意義上**不是**常數；其 std 是真實（極小）變異，巨大 SR 與「`0.01+1e-9·k`」同類——主委原文已主張**不該**用 ε 抹掉。
3. 因此該反例**不能**用來否定 `ptp==0`，也不能拿來為相對容差辯護。

---

## D. 對 PBO／golden 的影響

命令：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_pbo.py -q --tb=line`  
結果：**17 passed**，rc=0（約 5.14s）。

- golden 三案例（noise／alpha_detectable／alpha_undetectable）基底＝`default_rng(20260817).standard_normal((1200,50))*0.01`：模擬 `ptp==0` 謂詞 → **`any_ptp0=0`、`new_deg_via_ptp=0`**，不改變 band 斷言。
- `test_constant_slices_produce_exclusions_and_all_degenerate` 用全零（`std` 已精確 0）——行為不變。
- **會變的只有** `test_vectorized_sharpe_matches_compute_sharpe` 對 `sub[:,7]=0.01` 的「巨大有限且 `|SR|>1e6`」斷言（檔內已標 G1-R11 殘留）：修 `ptp` 後該欄應改斷言 **NaN／退化**——這是修法本身的驗收翻轉，不是 golden 三案例。

---

## E. 修法歸類

**判定：實作 bug 修補（對齊 SPEC 字面「常數序列 ⇒ NaN」），非語意變更。**

依據：

1. SPEC Task 1.2 驗證句（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` ≈L154–155）寫的是「**常數序列** ⇒ isnan …」，不是「僅當 `std` 位元精確等於 0.0」。
2. 現行 `std==0.0` 對「全元素同一 double」之常數**失敗**（F2），故實作未覆蓋 SPEC 驗收意圖。
3. `ptp==0` **不**改變「真實微擾近常數 → 巨大有限 SR」之語意（主委明示保留）；只補「同值常數被求和捨入騙過」的洞。
4. 無新魔法常數 → 符合專案「禁自創常數」精神。

流程建議：小任務＋三家 review（改 `sharpe.py` + `pbo._sharpe_pp_1d` + 翻轉具名測試斷言）；**不必**開延伸檔／adversarial（除非審查反對「常數＝ptp0」之定義）。Registry G1-R11 可自 needs-research 降為可修小缺陷。

---

## GROK-R20-P2-01

**斷言**: 業界主流 Sharpe 實作（empyrical／quantstats／ffn／vectorbt／pyfolio）對零波動皆不採相對容差、亦不採 `ptp`／`all-equal`；要嘛直接除（得 NaN／inf），要嘛精確 `std==0`→NaN／inf／0.0。

**碼證**: 本輪下載並標行號：empyrical `sharpe_ratio` L700–717 直接 `nanmean/nanstd` divide；quantstats `sharpe` L892 無零檢、`sortino` L1041 `downside==0`→nan、`risk_return_ratio` L2404 `std==0`→nan；ffn `calc_sharpe` L1456–1458 `np.divide`+errstate、`information_ratio` L1484 `diff_std==0`→0.0；vectorbt `sharpe_ratio_1d_nb` L346–347 `if std==0.0: return np.inf`；pyfolio L290 委派 empyrical。相對容差搜尋於上列函式體 → 0 命中。

**來源摘要**: handoffs/20260818-gap1-r11-consult-BRIEF.md#0daaf5679e9c

[MAJOR] 信心度=High。坐實 brief assumed A；支持「反對相對容差」。本專案加 `ptp==0` 是比業界更貼「常數」字面的補洞，不是跟風發明 ε。

---

## GROK-R20-P2-02

**斷言**: `ptp==0`（並存既有 `std==0`）是對 SPEC「常數序列⇒NaN」驗收句的實作修補，不是 Task 1.2 已蓋章「近常數微擾得巨大 SR」語意之變更；golden 三案例不受影響。

**碼證**: SPEC ≈L154–155 驗「常數序列」；`sharpe.py:89` 僅 `std==0.0`。本輪：`np.full(80,0.01)` → `ptp=0`、`std≈1.75e-18`、現行 `status=ok` 且 SR≈5.7e15；擬修謂詞 `std==0 or ptp==0` 對該欄為 True、對 `0.01+1e-9·arange` 為 False。`pytest .../test_pbo.py -q` → 17 passed；golden noise 矩陣 `any_ptp0=0`。

**來源摘要**: momentum/Analysis/strategy_validation/sharpe.py#cdaa1007c3b7

[MAJOR] 信心度=High。歸類＝小任務 bugfix＋三家 review；同步 `_sharpe_pp_1d`；翻轉 `test_vectorized_sharpe_matches_compute_sharpe` 對欄 7 之 `|SR|>1e6` 斷言為 NaN。

---

## GROK-R20-P2-03

**斷言**: brief assumed「真實管線不會產生同一數學值之不同 double」不完全成立（`0.01` 與 `0.1*0.1` 可共存於一序列且 `ptp≠0`），但此反例屬 IEEE 真實微差、與主委保留之「近常數微擾」同類，**不**構成反對 `ptp` 修法或改採相對容差之理由。

**碼證**: `0.1*0.1` bits=`4576918229304087676`＝`nextafter(0.01)`；`0.01` bits=`4576918229304087675`；混合序列 `ptp>0`、`all_eq=False`。對照：CSV `'0.01'`、`float32→float64` 同構、`[0.01,1e-2,1/100]` → 皆 `ptp==0`。

**來源摘要**: handoffs/20260818-gap1-r11-consult-BRIEF.md#0daaf5679e9c

[MAJOR] 信心度=High。建議文件化：常數判定＝「輸入陣列元素位元全等」（`ptp==0`），不保證跨異源浮點表達式之「數學相等」。

---

ASSUMPTIONS_VERIFIED: F1–F3 重跑成立；A1 業界無相對容差坐實；A2 部分證偽（異源 double）；A3 golden 不受 ptp 影響坐實；文獻結構支持零波動＝退化／未定義、無 ε。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_pbo.py -q --tb=line` → 17 passed rc=0；本地探針（80×0.01／ptp／異 double／CSV／float32）見段 C–D。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀；僅新增本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼；建議修法若落地會讓 `0.01` 常數欄由巨大 SR 改 NaN——屬 G1-R11 意圖）
OUTPUT: handoffs/20260818-gap1-r11-consult-grok.md
STATUS: DONE
