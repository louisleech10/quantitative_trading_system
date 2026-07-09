# IC1EB-SPECADV-composer — SPEC/TODO Adversarial Review (Composer 家族)

**TASK_ID**: `ic1eb-specadv-composer`  
**審查對象**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` v1 (草案) + `docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` v1 (DRAFT)  
**模板**: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13  
**PLAN**: N/A  
**日期**: 2026-07-09  
**角色**: 獨立 adversarial reviewer（未參照 Codex 家族審查產出）

---

## Verdict：需修補後派工

**Verdict: REJECT**（含 BLOCKING findings；修補後可重審）

---

## Findings

### §0 前提挑戰（假設 vs 事實）

#### ADV-COMPOSER-1 | MAJOR | 信心度: High
- **證據**: SPEC §A D-A「`z_t=u_t·v_t`(Spearman ρ 的逐 bar 貢獻;mean(z)≈IC)」；§A「待確認:無」
- **問題**: 將「逐 bar 乘積序列 + NW 可合法檢定 Spearman ρ=0」陳述為已定事實，未列 (i) 全樣本 rank 使 `{z_t}` 非獨立、(ii) h>1 時 forward label 重疊的 MA 結構、(iii) 需 mixing/漸近條件。§A 未標 assumption。
- **失敗後果**: Agent 照字面實作，審核以為統計前提已三方簽核，實際在短樣本/高 h 下 p 值仍可能反保守或與文獻不一致。
- **建議修法**: §A 增「Statistical assumptions」子節：明列 H0=bar-level Spearman ρ=0、全樣本 rank、NW 漸近、maxlags 下限 h-1 的適用邊界；§V 增短樣本/h 大場景 hermetic receipt。
- **RECHECK**: 修 SPEC 後 grep `assumption|待確認`；重跑 §V M-A/M-C + 短 test 段 (n_valid≈max(8,2·maxlags)) 邊界 pytest。

#### ADV-COMPOSER-2 | MAJOR | 信心度: High
- **證據**: TODO Task 1.1 實作要點 3「`effective_maxlags = max(auto_bw, horizon-1)`, auto_bw=Newey-West 自動頻寬(statsmodels … 或手刻 Bartlett)」
- **問題**: `auto_bw` 無 normative 公式；statsmodels `maxlags=None` 行為未寫入 SPEC（實測為 `int(4*(n/100)^(2/9))` 量級，版本相依）。允許「手刻 Bartlett」時 Agent 無法唯一決定 auto_bw。
- **失敗後果**: 雙實作路徑（statsmodels vs 手刻）產生不同 maxlags → se/p 分叉，T-1.1a oracle 與生產不一致。
- **建議修法**: SPEC D-A + Task 1.1 寫死 `auto_bw = floor(4 * (n_valid/100)**(2/9))`（或明定「生產必須 statsmodels OLS HAC 且先算 auto_bw 再 max(h-1)」單一路徑）；§G oracle 同式。
- **RECHECK**:
  ```
  VERIFY: python -c "import numpy as np,statsmodels.api as sm;n=500;z=np.random.default_rng(0).normal(n);m=sm.OLS(z,np.ones(n)).fit(cov_type='HAC',cov_kwds={'maxlags':None});..."
  ```
  對照 SPEC 公式與 `effective_maxlags` 實作一致。

#### ADV-COMPOSER-3 | NON-BLOCKING | 信心度: High
- **證據**: §A FACT-RECEIPT「window_63 序列 lag-1 自相關 ≈0.984」
- **問題**: 宣稱為偵察 fact；獨立複驗同型合成資料得 ≈0.978（同數量級，非 byte 相等）。
- **失敗後果**: 無（方向性 fact 成立）；若寫死 0.984 作測試門檻可能誤殺。
- **建議修法**: 改為「≈0.98 量級」或附 seed/資料 receipt。
- **RECHECK**: 重跑 VERIFY1 腳本，確認 lag-1 ρ>0.95。

---

### 統計 kernel / 驗收

#### ADV-COMPOSER-4 | BLOCKING | 信心度: High
- **證據**: TODO Task 1.1 實作要點 4「`p=2*sf(|t|, df=n_valid-1)`」；§G「oracle=statsmodels(OLS z_t~1, cov_type=HAC)… se/t/p `allclose(rtol=1e-8)`」；T-1.1a「statsmodels oracle allclose(rtol=1e-8,含 … p)」
- **問題**: statsmodels HAC 的 p 值用**漸近 Normal**（`use_t=False`），SPEC/TODO 用 **t(n-1)**；t/se 可一致但 p  systematically 偏離，n=32 時相對差 ~1.6%（VERIFY2/VERIFY4）。
- **失敗後果**: T-1.1a 必紅或 Agent 為通過 oracle 改寫 p 公式與 SPEC 衝突；Gate B1 阻塞。
- **建議修法**: 統一一種：① oracle 與生產皆 Normal（改 SPEC p 公式 + 更新 D-A 一句話）；或 ② oracle 只比 se/t，p 用 binomial/容差帶；禁止三者混用。
- **RECHECK**:
  ```
  VERIFY: python -c "import numpy as np,statsmodels.api as sm;from scipy import stats;..."
  # 断言 abs(p_t - p_norm)/p_t > 1e-8 在 n=32 成立；修 SPEC 后 T-1.1a 全绿
  pytest tests/momentum/test_statistical_validator.py -k T-1.1a -q
  ```

#### ADV-COMPOSER-5 | BLOCKING | 信心度: High
- **證據**: 同 ADV-COMPOSER-2；§G oracle 要求 maxlags 同源
- **問題**: `maxlags=max(auto_bw, h-1)` 在 auto_bw 未定義時為**不可測需求**（§1 類別 3）；M-C 可證偽 h-1 下限，但 auto 腿無 golden。
- **失敗後果**: Agent 自行發明 auto_bw → 與 oracle 分叉；h=1 vs h=63 行為不可審計。
- **建議修法**: 與 ADV-COMPOSER-2 合修：寫死 auto_bw 公式或禁手刻、強制 statsmodels 單路徑。
- **RECHECK**: M-C mutation + T-1.1a 含 h∈{1,5,63} maxlags receipt。

#### ADV-COMPOSER-6 | MAJOR | 信心度: High
- **證據**: TODO Task 1.1「`ic_hat=mean(z)`(僅供內部,不覆蓋既有 ic_mean 欄)」；`_build_summary_table` 現行 `ic_mean` 來自 `icir_item`（rolling IC 窗均值，`ic_engine.py:318`）；D-A 檢定 bar-level `mean(z)`
- **問題**: 縱向路徑 **p 值檢定對象**（test 段 bar-level Spearman 貢獻均值）與 **UI 展示 ic_mean**（預設 window_63 rolling IC 序列均值）非同一估計量；VERIFY8 同段資料 `mean(z)` 與 `spearmanr` 亦有小偏差。
- **失敗後果**: 使用者見 ic_mean=0.05 顯著但 p 很大（或反之），質疑平台；selection 決策與展示脫節。
- **建議修法**: §A/D-F 明文披露；或 summary 增 `ic_mean_test`（kernel 點估）與 `ic_mean`（描述性 rolling）並列；threshold 只綁檢定欄位。
- **RECHECK**: 真小樣本 stage5 單測：`|ic_mean - mean(z)|` 記錄於 threshold_log/metadata，非零時 UI 有說明。

#### ADV-COMPOSER-7 | MAJOR | 信心度: High
- **證據**: SPEC D-F「刪 resolveTStat/SE 前端推導」；TODO Task 4.2 列刪 `:75-95/:127`；`ICSummaryTable.tsx:116-137` `resolveConfidenceInterval` 仍用 `1.96*SE` i.i.d.
- **問題**: D-F 欄位語意遷移不完整；cross_sectional CI 仍前端 i.i.d. 推導，與 D-H/HAC 後端 p/t 並存矛盾。
- **失敗後果**: 前端顯示「假精確」CI，與後端 HAC 敘事衝突。
- **建議修法**: Task 4.2 增刪/停用 `resolveConfidenceInterval`（無後端 CI 則 `'--'`）；§C consumer map 第 9 項補列。
- **RECHECK**: `npm run build` + grep `resolveConfidenceInterval|1.96` 於 `ICSummaryTable.tsx` 僅剩註釋或零。

#### ADV-COMPOSER-8 | MAJOR | 信心度: Medium
- **證據**: SPEC §G G-3 / TODO Task 1.1「`n_valid<max(8, 2*effective_maxlags)→NaN`」；§A h 同源 MA(h-1)
- **問題**: 常數 `8` 無出處；h=63 時 `2*maxlags≥124`，12h 短 test 段大量 feature fail-closed（Task 5.1 僅一句帶過）。
- **失敗後果**: 短窗 run 幾乎全 feature p=NaN→全滅；使用者以為 bug。
- **建議修法**: §A 解釋 8 的統計來源或改為 `max(2*maxlags, min_n_from_power)` 並附 power 表；§V 增 12h 真資料 fail-closed 比例 receipt（非 blocking merge，但須預期管理）。
- **RECHECK**: 12h 3sym 小跑統計 `fraction_nan_p` 落 threshold_log 並寫入 G-2 diff。

---

### FDR / α / 前端

#### ADV-COMPOSER-9 | NON-BLOCKING | 信心度: High
- **證據**: SPEC D-C / TODO Task 2.2「NaN p 不入 BH」+「evaluated_features=[finite p]」+ `_passes_threshold` None/NaN→False（`ic_filter_orchestrator.py:2960-2961`）
- **問題**: 設計一致；但 Task 2.2 未明示 `universe_features` 含 NaN-p feature 而 `n_tests` 僅 finite——與 D-D 一致，建議 Task 2.3 加一句避免 Agent 把 NaN 欄塞進 evaluated。
- **失敗後果**: 低（契約已有）；若誤塞則 n_tests 膨脹 FDR 反保守。
- **建議修法**: Task 2.3 增「evaluated 嚴格=finite p 子集；NaN 僅在 universe」。
- **RECHECK**: T-2.3b mutation n_tests+1→raise。

#### ADV-COMPOSER-10 | MAJOR | 信心度: High
- **證據**: SPEC D-E「low_confidence→α=max(p_value_max,0.10)」；現行 `event_filter.py:128-144` 還有 **marginal** tier(0.05)；TODO T-2.2c 只列 sufficient/low_confidence 四格
- **問題**: marginal 行為未定義於 α 表（推論=同 sufficient，但未寫）；Agent 可能誤用 `adjusted_p_threshold` 舊覆蓋語意。
- **失敗後果**: marginal tier α 與 event_filter 返回值漂移。
- **建議修法**: Task 2.2c 擴為 3 tier×fdr 六格；明寫 marginal→`p_value_max`。
- **RECHECK**: pytest T-2.2c 含 tier=marginal 斷言。

#### ADV-COMPOSER-11 | NON-BLOCKING | 信心度: High
- **證據**: SPEC D-G「FDR 預設 ON」；`icAnalysisStore.ts:78,104` conservative/intermediate `fdr_correction: false`；`getEffectiveConfig`(:290-325) 無 fdr 映射（VERIFY 已確認）
- **問題**: 現狀 fact 正確；Task 4.2 計劃改 preset——SPEC 應標「現狀 vs 目標」避免 §A 讀成已落地。
- **失敗後果**: 審查誤以為前端已預設 ON。
- **建議修法**: §A FACT-RECEIPT 增「前端 preset 現況 2/3 false，Task 4.2 改 true」。
- **RECHECK**: Task 4.2 完成後 grep preset `fdr_correction: true`×3。

---

### Agent / 測試 / Golden

#### ADV-COMPOSER-12 | NON-BLOCKING | 信心度: Medium
- **證據**: TODO Task 1.1 簽名 `method: str="spearman"` 無 pearson 分支
- **問題**: 參數幽靈；`ic_engine` 支援 pearson。
- **失敗後果**: Agent 實作 pearson 或未實作卻保留參數。
- **建議修法**: 刪 method 參數或 §N 登記 pearson 另立。
- **RECHECK**: grep `method=` kernel 呼叫僅 spearman。

#### ADV-COMPOSER-13 | NON-BLOCKING | 信心度: High
- **證據**: Task 5.1 G-1「改前(git stash 或基準 commit 產物)」
- **問題**: Agent 可執行性偏弱（需指定 baseline commit SHA/tag，非「自行 stash」）。
- **失敗後果**: Golden G-1 不可復現。
- **建議修法**: §G 寫死 baseline commit（1-align 後某 SHA）或 harness 內嵌 frozen p_iid snapshot。
- **RECHECK**: T-5.1 命令不依賴互動 git stash。

---

## §1 十類必查結論

| # | 類別 | 結論 |
|---|------|------|
| 1 | 矛盾/互斥 | **有** — HAC p 值 t vs Normal oracle（ADV-COMPOSER-4）；auto_bw 雙路徑（ADV-COMPOSER-2/5） |
| 2 | 漏項/端到端 | **有** — D-F 未覆蓋 CI 推導（ADV-COMPOSER-7）；marginal tier 測試漏（ADV-COMPOSER-10） |
| 3 | 不可測驗收 | **有** — T-1.1a p allclose 1e-8 與 oracle 衝突；auto_bw 未定（ADV-COMPOSER-4/5） |
| 4 | 可疑 quant 假設 | **有** — 全樣本 rank、ic_mean vs mean(z) 雙軌（ADV-COMPOSER-1/6/8） |
| 5 | 過度工程 | **無** |
| 6 | OOM/並行 | **無**（per-feature 迴圈已述；無 ProcessPool 巢狀） |
| 7 | Cache 正確性 | **無**（本刀不動 cache key） |
| 8 | API/型別/相容 | **有（MAJOR）** — 舊 report 無新欄 Task 4.2 已列 optional；CI 推導遺漏（ADV-COMPOSER-7） |
| 9 | 測試品質 | **有** — M-A/M-B/M-C 設計紮實；oracle 不一致使單元 gate 不可信（ADV-COMPOSER-4） |
| 10 | Agent 可執行性 | **有** — auto_bw、G-1 baseline、ic_mean 雙軌披露不足（ADV-COMPOSER-2/5/6/13） |

---

## §2 範本錨點 + 空殼獵取

### 錨點落實
| 錨點 | 狀態 |
|------|------|
| §RISK + RISK-HIT | ✅ `RISK-HIT: a,b,d` |
| §A + FACT-RECEIPT | ✅ 有 receipt 摘要；部分宣稱需降級為 assumption（ADV-COMPOSER-1/3/11） |
| §C consumer map | ✅ 10 項有檔案:行號 |
| §G Golden | ✅ G-1/G-2/G-3 有數值/ hash token；G-2 依賴未凍 baseline commit（ADV-COMPOSER-13） |
| §P/§V/§R/§N | ✅ 齊；§N 合理登記 deep/bootstrap 範圍 |
| TODO §0 解耦 | ✅ 7 條子集 + fail-closed + data_cache 紅線 |

### 空殼獵取
逐 Task 讀取：**無 BLOCKING 空殼**。各 Task 含檔案、函式、邊界、驗證 token（T-x/M-x）。  
輕微空泛：Task 1.1 `auto_bw` 一句帶過（見 ADV-COMPOSER-2）；Task 5.1 G-1 baseline 來源模糊（ADV-COMPOSER-13）。

---

## §3 不可違反原則對照

- **跨 tier 重複穩定**: 未要求削弱；maxlags 公式寫死後可測 — 待修 ADV-COMPOSER-2。
- **多 symbol OOM**: 無額外 ProcessPool — OK。
- **數據品質**: FDR 全 evaluated、fail-closed NaN — 方向正確；禁止 fake Golden — §G 明確。
- **不假最佳化**: 否決 rolling IC 檢定、HAC 無 production off — 符合；**不得**為通過 T-1.1a 弱化 p 比對或刪 M-A。

---

## 被當成事實的未驗證假設（§0）

1. D-A：NW on `z_t` = 合法 Spearman ρ=0 檢定（ADV-COMPOSER-1）— assumption，非 fact。
2. `max(8, 2·maxlags)` 樣本下限（ADV-COMPOSER-8）— 常數未驗。
3. statsmodels `maxlags=None` 作 auto_bw 可复现（ADV-COMPOSER-2）— 實測有規律但未写入 SPEC。
4. §A lag-1≈0.984 — **fact 方向成立**（VERIFY1: 0.978221 @ n=500 合成）。
5. BH 手刻 ≡ statsmodels — **fact 成立**（VERIFY3: max diff 0.0）。
6. statsmodels 0.14.6 + cov_hac OK — **fact 成立**（VERIFY2: version 0.14.6）。
7. 前端 fdr 斷鏈 — **fact 成立**（grep + `getEffectiveConfig` 無 fdr；preset 2/3 false）。
8. `adjust_multiple_comparisons` 零 production caller — **fact 成立**（grep 僅 tests + validator 定義）。
9. cross_sectional `p_value: None` — **fact 成立**（`ic_filter_orchestrator.py:1088`）。
10. `_apply_thresholds` 裸 p≤p_value_max — **fact 成立**（`:2590-2593`）。

---

## VERIFY 實跑摘要（§A 義務）

```bash
# VERIFY1 pooled n + lag-1
flattened_n_obs 1293 ; window_63 lag1_autocorr 0.978221

# VERIFY2 statsmodels + p distribution mismatch
statsmodels 0.14.6 ; HAC p(normal)=0.8841704 ; p(t-dist)=0.8843179 ; diff≈1.5e-4

# VERIFY3 FDR hand vs statsmodels
max diff 0.0

# VERIFY4 n=32 relative p diff ~1.6%
n=32 rel_diff=0.016105

# VERIFY7 statsmodels maxlags=None matches int(4*(n/100)^(2/9)) for n∈{100,200,500,1000}

# VERIFY8 mean(z) vs spearman same segment: 0.086272 vs 0.086561 (not identical)

# grep: getEffectiveConfig 290-325 無 fdr_correction
# grep: STAGE_OVERRIDE_PATHS 73-79 無 fdr
```

---

ASSUMPTIONS_VERIFIED: §A 病灶①②、幽靈函式零 caller、statsmodels 0.14.6、BH 恆等、前端 fdr 斷鏈、cross_sectional p=None、lag-1 高自相關量級（獨立 VERIFY1）；HAC p oracle t vs Normal 不一致（VERIFY2/4）；statsmodels auto maxlags≈floor(4*(n/100)^(2/9))（VERIFY7）；mean(z)≠展示 ic_mean 路徑（VERIFY8+ic_engine:318）

TESTS_RUN: `python` VERIFY1-4/7-8 腳本（見上）；`grep` statistical_validator/orchestrator/frontend store；未跑 pytest（本輪唯讀審查）

FAILURES_SEEN: none（審查階段無修復迭代）

SCOPE_CHANGES: none（僅產出 `handoffs/IC1EB-SPECADV-composer.md`）

STATUS: DONE
