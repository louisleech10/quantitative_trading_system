# IC1EB-SPECADV-R2-composer — v2 閉合複驗 (Composer 家族 R2)

**TASK_ID**: `ic1eb-specadv-r2-composer`  
**審查對象**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` v2 + `docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` v2  
**R1 來源**: `handoffs/IC1EB-SPECADV-composer.md` (ADV-COMPOSER-1~13)  
**日期**: 2026-07-09  
**角色**: R1 原提出方 — 獨立覆核 §ADV-RESOLUTION 逐項真閉合（不憑「已修」字樣）

---

## Verdict: APPROVE

全 13 項 ADV-COMPOSER 於 SPEC/TODO 原文已具 normative 修法 + 可證偽驗收錨點；重跑 VERIFY7 / VERIFY2·4 / 邊界探針與 R1 主張一致。下列 NEW-ISSUE 均 **NON-BLOCKING**（文案精度 / §P 摘要漏項），不阻 freeze 派工。

---

## 逐條覆核 (ADV-COMPOSER-1~13)

### ADV-COMPOSER-1 | 統計假設當事實 | **CLOSED**

**R1 要求**: §A 增 H0 / 全樣本 rank / NW 漸近 / 適用邊界 = assumption；§V 短樣本 receipt。

**v2 原文證據**:
- SPEC §A L49–53「**統計假設(v2,COMPOSER-1;assumption 非 fact**…)」：H0=bar-level Spearman ρ=0；全樣本 rank 弱相依「**這是假設**」；NW 漸近 + h>1 MA(h-1)；`mean(z)` 非恰等 ρ。
- SPEC §V L131：「短樣本/大 h **邊界 receipt**(n≈下限、h∈{1,5,63},COMPOSER-1)」。
- TODO T-1.1a/c：h∈{1,5,63}、n∈{64,512}、邊界表（⑤n=下限±1）。

**覆核**: 假設已從 FACT 降級；邊界可證偽（T-1.1a/c + M-C）。**真閉合**。

---

### ADV-COMPOSER-2 | auto_bw 無 normative 公式 | **CLOSED**

**R1 要求**: 寫死 `auto_bw` 或單一路徑；與 VERIFY7 statsmodels 一致。

**v2 原文證據**:
- SPEC D-A L56: `` **`auto_bw = int(4*(n_valid/100)**(2/9))`** ``。
- TODO Task 1.1 要點 3 同式 + 「寫死,禁其他頻寬規則」。

**重跑 VERIFY7** (2026-07-09):
```bash
source venv/bin/activate && python3 -c "
import numpy as np, statsmodels.api as sm
def spec(n): return int(4*(n/100)**(2/9))
rng = np.random.default_rng(0)
for n in [8,10,32,64,100,200,500,1000]:
    z = rng.normal(size=n)
    se_explicit = sm.OLS(z, np.ones(n)).fit(cov_type='HAC', cov_kwds={'maxlags': spec(n)}).bse
    se_auto = sm.OLS(z, np.ones(n)).fit(cov_type='HAC', cov_kwds={'maxlags': None}).bse
    assert np.allclose(se_explicit, se_auto, rtol=1e-12)
print('VERIFY7: all n se_match=True')
"
# 輸出: VERIFY7: all n se_match=True
```
statsmodels 源碼 `sandwich_covariance.py:396` 為 `int(np.floor(4*(n_periods/100.)**(2./9.)))`，對正 n 與 SPEC `int(...)` 等價。

**覆核**: 公式寫死且與 statsmodels `maxlags=None` 行為一致。**真閉合**。

---

### ADV-COMPOSER-3 | 0.984 寫死 | **CLOSED**

**v2 原文證據**: SPEC §A L37「lag-1 自相關 **≈0.98 量級**」；保留 R1 雙家族 0.984/0.978 註記、不當門檻。

**覆核**: 已降級為量級陳述。**真閉合**。

---

### ADV-COMPOSER-4 | p 分布 t vs Normal 分叉 | **CLOSED**

**R1 要求**: 統一 oracle + 生產 p；消除 VERIFY2/4 分叉。

**v2 原文證據**:
- D-A L55: `` **p=2·t.sf(|t|, df=n_valid-1)**(單一定義,禁 Normal) ``。
- D-A L58: oracle `` use_t=True `` + **M-I 守衛**（Normal p ≠ oracle p）。
- TODO Task 1.1 要點 4–5 + T-1.1d (M-I)。

**重跑 VERIFY2/4** (2026-07-09):
```bash
source venv/bin/activate && python3 <<'PY'
import numpy as np, statsmodels.api as sm
from scipy import stats
rng = np.random.default_rng(0)
n=32; z=rng.normal(n); L=max(int(4*(n/100)**(2/9)),0)
ft=sm.OLS(z,np.ones(n)).fit(cov_type='HAC',cov_kwds={'maxlags':L},use_t=True)
fn=sm.OLS(z,np.ones(n)).fit(cov_type='HAC',cov_kwds={'maxlags':L},use_t=False)
p_manual=2*stats.t.sf(abs(ft.tvalues[0]),df=n-1)
print('p_manual==p_use_t', np.isclose(p_manual, ft.pvalues[0], rtol=1e-8))
print('p_normal!=p_use_t', not np.isclose(fn.pvalues[0], ft.pvalues[0], rtol=1e-8))
PY
# p_manual==p_use_t True ; p_normal!=p_use_t True
```
分叉仍存在於 **錯誤路徑**（use_t=False），但 SPEC 已禁 Normal、oracle 強制 use_t=True、M-I 可證偽靜默回歸。

**覆核**: R1 BLOCKING 分叉已在 normative 層消除。**真閉合**。

---

### ADV-COMPOSER-5 | auto_bw 未定義致 maxlags 不可測 | **CLOSED**

**v2 原文證據**: 與 ADV-2/4 合修；D-A L56–57 `L=max(auto_bw,h-1)` + cap；T-1.1a「h∈{1,5,63}」；M-C mutation。

**覆核**: auto_bw 已寫死 + h 腿有 golden。**真閉合**。

---

### ADV-COMPOSER-6 | ic_mean 雙軌 | **CLOSED**

**v2 原文證據**:
- D-F L64: `ic_mean`=rolling 描述性；檢定=bar-level；metadata `` tested_estimator="bar_level_spearman" ``；tooltip 明示；threshold 只綁檢定欄。
- TODO Task 4.2 要點 ⑥ ic_mean tooltip。

**覆核**: 披露 + metadata + UI 三點齊；不新增欄位屬合理 scope 控制。**真閉合**。

---

### ADV-COMPOSER-7 | CI 前端推導漏列 | **CLOSED**

**v2 原文證據**:
- §C consumer map #9 L80: 刪 `resolveTStat` **與 `resolveConfidenceInterval :116-137`**。
- D-F L64 / TODO Task 4.2 要點 ④：刪 CI 推導、無後端 CI→`'--'`；T-4.2 grep 驗收。

**覆核**: SPEC/TODO 已 normative 覆蓋 R1 漏項（生產碼現仍存 `resolveConfidenceInterval` 屬未實作預期，不影響 spec 閉合）。**真閉合**。

---

### ADV-COMPOSER-8 | 樣本下限 8 無出處 + fraction_nan_p | **CLOSED**

**v2 原文證據**:
- D-A L57 / G-3 L90: `` n_valid < max(8, 2*L) ``；註「8=rank corr 最小意義樣本,**對齊 1-align oracle 下限**」。
- §G G-2 L88 + TODO Task 5.1: **`fraction_nan_p`**（12h 短窗 fail-closed 比例）。

**出處覆核**:
- 1-align 可驗：`docs/IC_PHASE1_1A_ALIGN_SPEC.md` L75「Tier-2 … **有效樣本<8→raise**」。
- 「rank corr 最小意義樣本」仍為假設性表述（見 NEW-ISSUE-3）。

**邊界探針** (h=1): n=8 為首个 pass（`n<max(8,2L)` false）；n=3–7 fail-closed；h=63 需 n≥124。與 D-A 自洽。

**覆核**: 8 有 1-align 交叉引用 + fraction_nan_p receipt 錨定 G-2。**真閉合**（rank-corr 文獻句為弱出處，不阻派工）。

---

### ADV-COMPOSER-9 | evaluated 嚴格性 | **CLOSED**

**v2 原文證據**: TODO Task 2.3 不可做「**evaluated 嚴格=finite p 子集,NaN-p feature 僅得在 universe**」；T-2.3b mutation。

**覆核**: **真閉合**。

---

### ADV-COMPOSER-10 | marginal tier α 未定 | **CLOSED**

**v2 原文證據**:
- D-E L63: `` **marginal→α=p_value_max** ``；六格。
- TODO Task 2.2 要點 ③ + T-2.2c「sufficient/**marginal**/low_confidence × fdr on/off」。

**覆核**: 與 `event_filter.py:142-143` marginal→0.05 現況一致且已寫入測試格。**真閉合**。

---

### ADV-COMPOSER-11 | preset 現況 vs 目標 | **CLOSED**

**v2 原文證據**: §A L40「preset 現況 foundation/intermediate=false、advanced=true(**現況陳述**;目標=Task 4.2 三者改 true)」；TODO Task 4.2 要點 ①。

**覆核**: **真閉合**。

---

### ADV-COMPOSER-12 | method 幽靈參數 | **CLOSED**

**v2 原文證據**: TODO Task 1.1 簽名無 `method`；「spearman only,COMPOSER-12」；§N pearson 另立。

**覆核**: **真閉合**。

---

### ADV-COMPOSER-13 | G-1 git stash 陷阱 | **CLOSED**

**v2 原文證據**:
- §G L89: baseline=編排端 snapshot 落 `handoffs/ic1eb_baseline/`（含 HEAD sha）；**禁 git stash/checkout**。
- TODO §0 + Task 5.1 要點 ① 同。

**覆核**: 可執行、非互動 git 依賴。**真閉合**。

---

## NEW-ISSUE（v2 新增文字掃描）

| ID | 嚴重度 | 描述 | 證據 |
|---|---|---|---|
| NEW-ISSUE-1 | NON-BLOCKING | §P Task 1.1 一行摘要(L97)僅列 `n_valid<max(8,2·maxlags)`，**漏列** D-A/TODO 的 `L≥n_valid-1` cap | SPEC §P L97 vs D-A L57 / TODO Task 1.1 要點 1 |
| NEW-ISSUE-2 | NON-BLOCKING | M-I / D-A 寫「n=32 差~1.6%」為單一 receipt；重跑 seed  sweep 得 **0.17%–2.44%**（皆足以 `not allclose`） | 本輪 python seed sweep；不影響 M-I 可證偽性 |
| NEW-ISSUE-3 | NON-BLOCKING | 「8=rank corr 最小意義樣本」無文獻引；可驗部分僅 1-align Tier-2 有效樣本<8→raise | `IC_PHASE1_1A_ALIGN_SPEC.md:75` |
| NEW-ISSUE-4 | —（已排除） | R1 疑慮 **auto_bw=0**：探針顯示 n≥1 時 `int(4*(n/100)^(2/9))≥1`，h=1 時 L≥1，**不觸發** auto_bw=0 | n=1..9 探針 |
| NEW-ISSUE-5 | —（已排除） | cap 規則自洽：`L≥n-1` 與 `n<max(8,2L)` 聯立；h=63 短窗大量 NaN 已由 fraction_nan_p 預期管理 | 邊界表探針 h=1,h=63 |

**無 BLOCKING NEW-ISSUE**。

---

## §ADV-RESOLUTION 對照摘要

| Finding | R2 狀態 |
|---|---|
| COMPOSER-1 | CLOSED |
| COMPOSER-2 | CLOSED |
| COMPOSER-3 | CLOSED |
| COMPOSER-4 | CLOSED |
| COMPOSER-5 | CLOSED |
| COMPOSER-6 | CLOSED |
| COMPOSER-7 | CLOSED |
| COMPOSER-8 | CLOSED |
| COMPOSER-9 | CLOSED |
| COMPOSER-10 | CLOSED |
| COMPOSER-11 | CLOSED |
| COMPOSER-12 | CLOSED |
| COMPOSER-13 | CLOSED |

---

ASSUMPTIONS_VERIFIED: statsmodels 0.14.6；`auto_bw=int(4*(n/100)^(2/9))` 與 `maxlags=None` HAC se 全 n 探針一致(VERIFY7)；`p=2*t.sf` 與 `use_t=True` oracle 一致、與 Normal 可分(M-I)；n≥1 時 auto_bw≥1；fail-closed 邊界 h=1 n=8 起 pass、h=63 n≥124；1-align Tier-2 有效樣本<8→raise 可 grep；lag-1 已改量級陳述

TESTS_RUN: `python3` VERIFY7(se_match n∈{8,10,32,64,100,200,500,1000}); VERIFY2/4(p_manual/oracle/Normal); M-I seed sweep n=32; fail-closed 邊界表 h=1,h=63; auto_bw min 探針 n=1..9; grep SPEC/TODO/1A_ALIGN 錨點；**未跑 pytest**（spec 閉合複驗，無生產碼改動）

FAILURES_SEEN: none

SCOPE_CHANGES: none（僅產出 `handoffs/IC1EB-SPECADV-R2-composer.md`）

STATUS: DONE
