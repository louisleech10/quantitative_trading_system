# IC 1e+1b 統計嚴謹度充分性諮詢（Composer 獨立作答）

**TASK_ID**: ic1eb-rigor-composer  
**角色**: 統計嚴謹度諮詢（唯讀）  
**依據**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` v2.1、生產碼 grep/讀碼、低成本實測 receipt  
**日期**: 2026-07-09  
**獨立性**: 不參照其他委員產出

---

## Q1 檢定層：bar-level NW t-test 是否為業界/計量標準且足夠？

### 結論
**是——對「單特徵、時間序列 IC 是否顯著偏離零」這一層篩選，bar-level 貢獻序列 + Newey–West HAC t 檢定在量化研究與計量慣例中屬標準做法，且對本刀 scope 足夠；不必把 stationary bootstrap 升為生產 default kernel。**

### 依據（文獻/慣例）
| 做法 | 慣例出處 | 與本刀對應 |
|------|----------|------------|
| 對 moment 序列做 HAC 推斷 | Newey & West (1987, *Econometrica*); Andrews (1991) automatic bandwidth | D-A：`auto_bw=int(4*(n/100)^(2/9))` 對齊 statsmodels `maxlags=None` |
| 金融時間序列相依下檢定 mean | Cochrane, *Asset Pricing* (HAC on excess returns / moments); Campbell–Lo–MacKinlay 資產定價實證慣例 | `z_t=u_t·v_t` 序列視為可檢定 moment，NW 修正 lag 相依 |
| 重疊 forward return 的 MA 結構 | 重疊觀測文獻（如 Hansen–Hodrick 類） | `L≥h-1` 硬下限合理 |
| Rank IC 顯著性 | Spearman ρ 的漸近檢定；實務常以 rank 轉換後序列做 t/HAC（非 rolling 平滑序列） | 否決 pooled rolling IC（lag-1 ρ≈0.98）是正確的 |

### 與現況病灶對照（讀碼）
- 現行 `statistical_validator.py:95-128`：對 **三窗 rolling IC 串接** 跑 i.i.d. `ttest_1samp`——在高度自相關下反保守（SPEC §A FACT-RECEIPT）。
- v2.1 D-A 改為 **test 段逐 bar `z_t` + NW**：對象與相依結構匹配，屬實質修正而非裝飾。

### 替代方案評估
| 替代 | 優點 | 缺點 | 本刀建議 |
|------|------|------|----------|
| **Stationary bootstrap** (Politis–Romano 1994) | 弱相依下 pivot 更穩；短樣本有時優於漸近 NW | 生產成本高；block 長度/seed 治理；與 HAC 雙軌維護 | **測試驗證腿**（D-B circular block）✓；**不升級為 default** |
| **Block bootstrap 生產 kernel** | 可建非參數 p 分布 | m≈5000+ features × bootstrap B 次 → 算力/可重現性負擔 | 登記 §N epic（SPEC 已登記） |
| **對 rolling IC 均值做 HAC** | 直覺上「檢定 IC 均值」 | w=63 時有效相依階數≈w−1，短 test 段不可行；檢定對象是平滑人工序列 | SPEC 明文否決 ✓ |
| **Fisher z 精確轉換** | ρ 的經典漸近 | 與 bar-level product-moment 不同；全樣本 rank 使 z_t 非嚴格 i.i.d. | 本刀已披露 `mean(z)≠ρ`；z 僅供 HAC 截距檢定可接受 |

### 實測 receipt（低成本）
```text
# AR(1) φ=0.9 null, n=500, seed=42
iid p=0.3471  NW p=0.6663  lag1_acf=0.884  maxlags=5
→ 舊法在強相依 null 上未膨脹（此例）；病灶在 pooled rolling 高 acf 假陽性，非「任何相依都膨脹」
# oracle: statsmodels OLS(z~1, cov_type=HAC, use_t=True) 與手刻公式一致（SPEC M-I 守衛）
```

### Q1 裁決
- **default kernel = bar-level NW**：✅ 可凍結  
- **stationary bootstrap**：後續選項/epic，非本刀阻塞

---

## Q2 多重比較層：BH / BY / Romano–Wolf 推薦

### 結論
**特徵高度相關時 BH 的 PRDS 假設確實可能不成立，實務上可能略偏樂觀；但對大規模探索性特徵篩選，BH-FDR 仍是量化 ML 特徵工廠的主流 default。BY 更保守但通常不過度；Romano–Wolf/Westfall–Young 理論上更貼相依結構，但算力與工程複雜度不適合作本刀 default。**

### 依據
| 方法 | 文獻 | 相依假設 | 慣例用途 |
|------|------|----------|----------|
| **BH-FDR** | Benjamini & Hochberg (1995) | PRDS / 正相依下 FDR 控制 | 高通量假設檢驗、基因/因子篩選；Harvey–Liu–Zhu (2016) 後因子研究仍常用 FDR 族 |
| **BY-FDR** | Benjamini & Yekutieli (2001) | **任意相依** FDR 控制 | 保守 fallback；懲罰因子 `c(m)=Σ1/i` |
| **Romano–Wolf** | Romano & Wolf (2005) | 重抽樣 stepdown，弱相依 | 資產定價多假設同步檢定（bootstrap stepdown） |
| **Westfall–Young** | Westfall & Young (1993) | permutation/stepdown | 與 RW 同族，小樣本多重檢定 |

### PRDS 與特徵相關
- 候選特徵來自同一 FF pipeline，**跨特徵 p 值高度正相關**常見 → PRDS 違反時 BH 可能 **低估 FDR**（非必然，但為已知風險）。
- 本刀緩解（已入 SPEC）：**evaluated = stage5 全欄 finite p**、禁止 selection-conditioning 縮水 `n_tests`（D-C）——這比換 FDR 公式更關鍵。
- **BY 是否過度保守？** 一般為 BH 的 `O(log m)` 倍；獨立 p 下 BY/BH mean q 比≈1.10（本環境實測）。m≈5000 時 `log m` 倍仍可能明顯收緊，但屬「可選保守模式」而非失控。

### 實測 receipt
```text
# BH 手刻 vs statsmodels multipletests fdr_bh → allclose True
# 6 p-values: hand=[0.006,0.03,0.06,0.075,0.24,0.8] == statsmodels
```

### 明確推薦（本刀 + ROADMAP）

| 層級 | 推薦 | 理由 |
|------|------|------|
| **本刀 default** | **BH-FDR（`fdr_bh`）**，α 由 `p_value_max` + event tier 映射（D-E） | 與既有 `adjust_multiple_comparisons` 一致；算力可承受；SelectionScope 契約已鎖 `n_tests` |
| **本刀內建選項（config）** | **Bonferroni**（已實作）、**FDR off → raw HAC p**（對照腿） | 極保守 / 消融對照 |
| **登記後續選項（§N / 新 epic）** | **BY-FDR**（`fdr_by`）、**Romano–Wolf stepdown**（需 block bootstrap 聯合 null） | 使用者要「任意相依保證」或「同步控制族錯誤」時啟用 |
| **不作 default** | Romano–Wolf / Westfall–Young | m~5000+ 每次重抽樣 × 特徵相關矩陣 → 與 FF 效能目標衝突；需專門預算與 seed 治理 |

### Q2 裁決
- **default = BH**：✅  
- **BY / RW**：後續選項，非本刀阻塞  
- **建議最小文檔增補**：report metadata 標 `fdr_assumption_note="BH assumes PRDS; correlated features may yield slight FDR optimism"`（披露，非改算法）

---

## Q3 更上層：White RC / Hansen SPA / Deflated Sharpe / PBO

### 結論
**同意——上述方法屬「策略回測 / 組合選擇 / 研究流程 data-snooping」層，非 IC Gatekeeper 單特徵顯著性刀 scope；應另立 epic 登記。**

### 依據
| 方法 | 層級 | 解決問題 |
|------|------|----------|
| White Reality Check (2000) | 多策略回測 | 最佳策略是否優於基準（資料窺探） |
| Hansen SPA (2005) | 多模型比較 | 上界修正後仍顯著？ |
| Deflated Sharpe (Bailey & López de Prado) | 策略績效 | 試了多少次才「看起來好」 |
| PBO (Bailey et al.) | CV / 回測過擬合 | 樣內最優的樣外失敗機率 |

IC Gatekeeper stage5 回答的是：**在固定 label/test 段上，各 feature 的 bar-level IC 是否顯著 ≠ 0，並對 m 個特徵做 FDR**。這不涵蓋：
- 跨策略/跨參數網格的 **superior predictive ability**；
- 回測 Sharpe 的 **試驗次數膨脹**；
- 整條 ML pipeline 的 **nested selection**。

### 邊界說明（避免誤解）
- 本刀 FDR **不能替代** RC/SPA/PBO；兩層應串聯：特徵篩選（本刀）→ 策略回測顯著性（另 epic）。
- SPEC §N 已登記 deep path、`bootstrap_estimator` 泛化——與本 Q 一致。

### Q3 裁決
**同意另立 epic**；不納入 1e+1b 驗收阻塞項。

---

## Q4 IC Gatekeeper 其餘統計面盤點（讀碼實核）

讀碼範圍：`statistical_validator.py`、`monotonicity_tester.py`、`ic_engine.py`、`ic_filter_orchestrator.py`（stage5/thresholds）、`event_filter.py`、`ic_config_schema.py`。

| # | 項目 | 現況（檔:行） | 推斷/檢定？ | 判定 | 1e+1b 覆蓋？ | ROADMAP 優先序 |
|---|------|---------------|-------------|------|--------------|----------------|
| 1 | **ICIR 門檻** | `ic_engine.py:305-328` 計算；`ic_filter_orchestrator.py:2587-2588` 硬閘 `icir_min` | 無；`ICIR=mean/std(rolling IC)` 描述性 | **可接受描述性統計**；風險=把點估當確定 | 否 | **P2** — 可選：對 rolling IC 序列做 HAC 得 ICIR 信賴區間（診斷欄，非硬閘） |
| 2 | **ic_hit_rate 門檻** | `ic_engine.py:321`；閘 `ic_hit_rate_min`（預設 0.55, `ic_config_schema.py:105`） | 無；未做 binomial / HAC sign test | **實質統計風險（低–中）**：樣本內比例門檻無不確定性 | 否 | **P2** — 描述性保留；若硬閘需 sign-test + FDR 另刀 |
| 3 | **monotonicity_score** | `monotonicity_tester.py:68-82` 單調步長比例；閘 `monotonicity_score_min`（0.6） | 無；啟發式 0–1 分數 | **可接受描述性統計** | 否 | **P3** — 維持 heuristic；報告標「非檢定」 |
| 4 | **long_short t-test** | `monotonicity_tester.py:127-131` `ttest_ind` i.i.d.；`pvalue` **未進** `_apply_thresholds` | 有算 p，但**未用於篩選**；僅可選 `long_short_spread.min_spread` 幅度閘 | **實質統計風險（中）** 若未來接線 p 閘；現況風險受限 | 否 | **P2** — 接線前須 HAC/block；現狀 disclosure 即可 |
| 5 | **ic_decay 指數擬合** | `ic_engine.py:332-366,915-976` `curve_fit`；`r2≥0.5` 分類；**僅 warning**（`_collect_ic_decay_warnings`） | 無推斷；非線性最小二乘 | **可接受描述性統計** | 否 | **P4** — 診斷；不擋 selection |
| 6 | **grouped_ic 子樣本** | `ic_engine.py:381-416` by_year/quarter 逐段 `compute_ic` | 無；無多重比較 | **可接受描述性統計** | 否 | **P4** — 1f schema；子樣本推斷另 epic |
| 7 | **event tier 樣本判準** | `event_filter.py:128-144` tier→`adjusted_p_threshold`；orchestrator `2255-2260` 覆寫 `p_value_max` | 啟發式樣本量分層，非統計檢定 | **可接受工程政策**；1e+1b D-E 改為調 **FDR α** | **部分**（D-E） | **P3** — metadata 披露 `alpha_source`（SPEC 已有） |
| 8 | **cross_sectional p** | `ic_filter_orchestrator.py:1050-1096` i.i.d. t，`p_value=None` | 錯誤/缺失推斷 | **實質統計風險** | **是**（D-H） | **P1** — 本刀已納入 |
| 9 | **pooled rolling i.i.d. p** | `statistical_validator.py:24-32,118-119` | 反保守 | **高風險** | **是**（D-A） | **P0** — 本刀核心 |
| 10 | **裸 p 無 FDR** | `_apply_thresholds:2590-2593`；`adjust_multiple_comparisons` 零 caller | 多重比較未控 | **高風險** | **是**（D-C） | **P0** — 本刀核心 |
| 11 | **前端 i.i.d. t/CI 推導** | SPEC §A：`ICSummaryTable.resolveTStat/resolveConfidenceInterval` | 與後端不一致 | **實質風險（展示層）** | **是**（D-F） | **P1** — 本刀 |

### Q4 優先序摘要（供 ROADMAP）
1. **P0（本刀）**：pooled i.i.d. → HAC；BH-FDR + SelectionScope  
2. **P1（本刀）**：xsec p 填值；前端刪 i.i.d. 推導  
3. **P2（後續）**：ICIR/hit_rate/long_short 若升級為推斷閘；BY/RW FDR 選項  
4. **P3–P4（低）**：monotonicity/ic_decay/grouped 維持描述性 + 披露

---

## Q5 總裁決：v2.1 SPEC 是否「夠嚴謹可凍結」？

### 結論
**統計實質上足夠嚴謹，可凍結為 Phase 1 IC 特徵篩選的顯著性層標準。** 本刀鎖定了兩個最高風險病灶（錯誤檢定對象 + 無 FDR），並以 oracle、mutation、SelectionScope、測試側 block bootstrap 形成可證偽驗收閉環。未覆蓋項（PBO/SPA、monotonicity 推斷、BY/RW）已可邊界化登記，不構成 freeze 阻塞。

### 若堅持「更嚴」的最小修訂（非必須）
1. **metadata 一行披露**：BH PRDS 假設與高相關特徵風險（Q2）。  
2. **§N 登記**：`significance.fdr.method` 未來允許 `fdr_by` | `romano_wolf`（實作後續 epic）。  
3. **§N 登記**：`monotonicity_score` / `ic_hit_rate` / `ic_decay` = 描述性，非本刀推斷範圍（Q4 防誤讀）。  
4. **程序性**：v2.1 標「待 R2 閉合複驗」——Composer R2 已 APPROVE；**Codex R3 程序閉合**屬編排 gate，非統計實質 amend。

### 與「夠嚴謹」的邊界聲明
- 本刀嚴謹度目標 = **單期、單 label、大 m 特徵探索的 IC 顯著性 + FDR**（Harvey-Liu 因子篩選層）。  
- **不是** 全研究流程 data-snooping 終局答案（Q3）。  
- **不是** 非參數 bootstrap 或逐步相依 FDR 的理論最優解（Q1–Q2 刻意取工程可重現折衷）。

**RIGOR-VERDICT: FREEZE-OK**

---

## 機讀摘要

```
RIGOR-VERDICT: FREEZE-OK
Q1_DEFAULT_KERNEL: bar_level_spearman_nw_hac
Q1_FUTURE_OPTION: stationary_block_bootstrap_production
Q2_DEFAULT_FDR: fdr_bh
Q2_FUTURE_OPTIONS: fdr_by, romano_wolf_stepdown
Q3_BACKTEST_EPICS: white_rc, hansen_spa, deflated_sharpe, pbo — OUT_OF_SCOPE
Q4_P0_COVERED_BY_SPEC: pooled_iid_p, naked_p, selection_scope
Q4_P1_COVERED_BY_SPEC: xsec_p, frontend_iid_derivation
Q4_P2_BACKLOG: icir_hitrate_longshort_inference, fdr_dependence_options
```

---

ASSUMPTIONS_VERIFIED: (1) 現行生產碼仍為 pooled rolling i.i.d. p + 裸 p 閘（`statistical_validator.py:118-119`, `ic_filter_orchestrator.py:2590-2593`）；(2) `adjust_multiple_comparisons`/`_fdr_bh` 與 statsmodels `multipletests(fdr_bh)` 一致（實測 allclose）；(3) AR(1) null 下 NW 不必然比 i.i.d. 更寬，病灶在 rolling 串接高 acf（SPEC 與實測一致）；(4) monotonicity `long_short.pvalue` 未進 threshold 鏈（`monotonicity_tester.py:127-131`, `_apply_thresholds` 無 p 欄）；(5) ic_decay/grouped_ic 僅報告/警告，非硬閘（讀碼確認）

TESTS_RUN: `python -c` AR(1) NW vs iid（見 Q1 receipt）; `python -c` BH hand vs statsmodels（見 Q2 receipt）; 讀碼 grep `statistical_validator.py`, `monotonicity_tester.py`, `ic_engine.py`, `ic_filter_orchestrator.py`, `event_filter.py`

FAILURES_SEEN: none

SCOPE_CHANGES: none（唯讀諮詢；僅寫入本檔）

STATUS: DONE
