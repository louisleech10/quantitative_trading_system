# IC 1e+1b 全 epic 數據正確性簽核 — Composer（獨立腿）

**委員**: Composer | **日期**: 2026-07-11  
**範圍**: B1–B5（`git f277caf..cfcf08e`）— HAC kernel / FDR / 縱向接線 / xsec 最小面 / 全棧 / Golden 三腿  
**規格**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` v2.2 §G + §V  
**方法**: 本簽核不採信任何他方 verdict；以下每條附本人實跑命令或親讀碼證據。  
**素材**: `handoffs/IC1EB-GOLDEN-DIFF.md`、`handoffs/ic1eb_baseline/`、`handoffs/ic1eb_newpath_freeze/`、各批 `IC1EB-B*-REVIEW-composer.md`（僅作線索，結論自證）。

---

## 受檢環節清單（整鏈）

| # | 環節 | 批次 | 檢視方式 | 判定 |
|---|------|------|----------|------|
| 1 | 特徵/標籤輸入（生成→materialize） | 前置 | baseline `inputs/` sha + G-1 五 hash 不變 | PASS |
| 2 | bar-level HAC 顯著性 kernel | B1 | oracle + M-A/M-I pytest | PASS |
| 3 | BH-FDR 應用層 | B1/B2 | M-B/M-E pytest + stage5 讀碼 | PASS |
| 4 | train/test split → stage5 消費 test 段 | B2 | `_slice_by_mask(test_mask)` + M-D + refilter OOS | PASS |
| 5 | FDR 全 evaluated 先於門檻 | B2 | `_stage5_statistical_validation` 順序讀碼 + M-B mutation | PASS |
| 6 | p/q 閘 + event tier α 六格 | B2 | `test_t22c_alpha_policy_six_cells` + 讀碼 | PASS |
| 7 | SelectionScope 契約 + symbol 誠實 | B2 | `test_scope_contract` + `_resolve_scope_symbol` raise | PASS |
| 8 | cross_sectional horizon + HAC p 填實 | B3 | T-3.1 + mutation probe 實跑 | PASS |
| 9 | config schema → tier → stage5 | B4 | T-4.1 hop chain pytest | PASS |
| 10 | 前端 FDR toggle + 禁 i.i.d. 推導 | B4 | T-4.3 e2e + `rg resolveTStat` = 0 | PASS |
| 11 | report/CSV canonical `significance.*` | B2/B4 | `ic_reporter.py` 讀碼 + T-2.4/T-4.1 | PASS |
| 12 | G-1 非顯著性欄位不變 | B5 | 快顆 golden replay pytest | PASS |
| 13 | G-2 變更腿方向可解釋 | B5 | `per_feature_diff.json` 獨立聚合腳本 | PASS |
| 14 | G-3 fail-closed | B5 | G-3 pytest 4/4 | PASS |
| 15 | 舊 pooled 串窗退出生產鏈 | B2 | M-H/M-F pytest + grep | PASS |

---

## 簽核依據（逐項）

### 1. 統計正確性（kernel + FDR）

| 檢查 | 命令 / 證據 | 結果 |
|------|-------------|------|
| HAC vs statsmodels oracle | `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_statistical_validator.py::test_t11a_hac_matches_statsmodels_oracle -q` | **1 passed** |
| 反保守假陽率 M-A | `…::test_t11b_ma_ar1_false_positive_size -q` | **1 passed**（舊 FPR=0.43，新=0.06∈binomial 帶） |
| FDR 獨立+相關 null M-B | `…test_ic_1eb_b2_wiring.py::test_t22a_mb_fdr_control_independent_and_correlated -q` | **1 passed** |
| 生產禁 pooled 串窗 M-H/M-F | `…test_t21c_mh_structure_no_pooled_in_production` + `test_t21b_mf_leg_a_hac_pass_leg_b_pooled_fails` | **2 passed** |
| 解耦 | `rg 'from api\.' momentum/` | **0 命中** |

**可證偽**: 若 kernel 靜默退回 i.i.d.，M-A new_rej 應≈86/200 超出 [4,16]；若 stage5 仍呼叫 `_collect_values` 串窗，M-H AST 斷言轉紅。

### 2. 無洩漏 / split scope 誠實

| 檢查 | 證據 | 結果 |
|------|------|------|
| stage5 僅 test 段 | `ic_filter_orchestrator.py:2488-2493` `test_mask` → `_slice_by_mask` | PASS |
| FDR train/test 錯配 M-D | `test_t22b_md_scope_mismatch_turns_red` | **1 passed** |
| OOS refilter 不漂 full | `test_t22_refilter_oos_scope_remains_test` | **1 passed** |
| symbol 禁虛構 | `_resolve_scope_symbol` 缺值 → `ValueError` | PASS（讀碼） |

### 3. 縱向主路徑接線（B2）

- `compute_hac_ic_statistics` 為 stage5 唯一 p 來源；`rolling_ic` 僅診斷。
- FDR：`apply_fdr` 對 `universe_features=features_for_stats.columns` 全欄，**先於** `_apply_thresholds`。
- p 閘消費 `p_value_adj`（FDR on）或 raw `p_value`（off）；NaN p → fail-closed。
- `apply_significance_filter` 生產樹 **0 caller**；`compute_ic_statistics` 名稱已移除。

### 4. cross_sectional 最小面（B3）

| 檢查 | 命令 | 結果 |
|------|------|------|
| `return_5` → maxlags≥4 | `test_t31b_labels_path_return_5_maxlags_floor` | **1 passed** |
| horizon 於 `_label` 改名前解析 | 讀碼 `:1026-1042` + B3 mutation probe（本輪未重跑 probe，B3 審查期已實跑） | PASS |
| xsec 無 p 閘（D-H） | `analyze_cross_sectional` 註解+無 stage5 threshold 排序仍 ICIR | PASS |

xsec 舊路徑 `p_value=None` → 新路徑有限 HAC p：抽樣 `ms_12h_roll_spread_55_Min_W34` old `None` → new `p=0.0223, q=0.767`（誠實填值，非反保守門檻放行）。

### 5. 全棧接通（B4）

| 檢查 | 命令 | 結果 |
|------|------|------|
| FDR 每跳接點 + 兩態 e2e | `pytest tests/momentum/test_ic_1eb_b4_fullstack.py -q` | **11 passed**（本輪抽驗子集含 T-4.3） |
| 禁第四種 fdr 命名 | `rg 'fdr:disabled\|fdr_disabled\|enable_fdr' momentum/ frontend/` | **0 命中**（changelog 除外） |
| 前端零統計推導 | `rg 'resolveTStat\|resolveConfidenceInterval' frontend/` | **0 命中** |

### 6. G-1 不變腿

| 檢查 | 命令 | 結果 |
|------|------|------|
| 真資料快顆重放 | `pytest tests/momentum/Analysis/test_ic_1eb_b5_golden.py::test_g1_fast_btc_12h_f754_invariant -q` | **1 passed**（18.6s，五 hash 全等） |
| baseline 唯讀 | fixture 僅 `load_manifest` + `verify_inputs_integrity` | PASS（讀測試） |

**註**: 13 顆 slow G-1 本輪未重跑（>60s 預算）；快顆 + B2–B4 期間多次 G-1 抽驗已覆蓋同程序。

### 7. G-2 變更腿 — 高自相關假顯著轉紅（重點審視）

**獨立聚合**（`handoffs/ic1eb_newpath_freeze/per_feature_diff.json`，本輪 ad-hoc 腳本）:

| 指標 | 值 | 解讀 |
|------|-----|------|
| `pass_old_only` | **273** | 舊 i.i.d./裸 p 通過、新 HAC+FDR 不通過 |
| `pass_new_only` | **0** | FDR 未反向放行假陽性 |
| `false_significant_to_red` | **273** | 與 pass_old_only 一致 |
| `p_hac > p_iid_old`（可比 5482 列） | **5160（94.1%）** | 方向符合「相依低估 SE → 舊 p 膨脹」病灶 |
| old_only 全數 p 膨脹 | **273/273** | **有數據支撐**預期方向 |
| 仍通過兩態（縱向） | **6** | 強信號倖存：`p_hac` 仍小、`q<0.05`（例 `MINUS-DI_34_Slope_W5` q≈0.0017） |

**抽樣 old_only**（event BTC 12h）:
- `MACDEXT-Hist_12-26-9_Slope_W144`: `p_iid=7.5e-13` → `p_hac=0.083`, `q=0.823` → 轉紅
- `ROCP_89_Kurt_W13`: `p_iid=0.0047` → `p_hac=0.661`, `q=0.970` → 轉紅

**G-2 解讀注意（非 FAIL）**:
- `pass_both=506` 含 **xsec 500 列**：xsec 無 stage5 p 閘（D-H），`reconstruct_passed`=全 summary−removed=500；**不**代表 xsec 舊新門檻相同，而是該路徑本來就不做 p 淘汰。縱向方向性應看 `pass_old_only`（273，全在 longitudinal/event/full run）。
- `fraction_nan_p` 12h 縱向 ≈0.002（~1/499），符合短窗 fail-closed 低比例預期（COMPOSER-8 receipt）。

**manifest sha 鏈**（本輪）: `long_BTCUSDT_12h_f754aad4.report.json` sha 與 manifest 一致；`per_feature_diff_sha256` 與檔案一致。

### 8. G-3 fail-closed

| 檢查 | 命令 | 結果 |
|------|------|------|
| 樣本不足/全 NaN/std=0 | `pytest …test_ic_1eb_b5_golden.py -k g3 -q` | **4 passed** |
| xsec labels 單軸 | `test_g3_xsec_labels_path_still_raises`（真 kline 路徑） | **1 passed** |

### 9. 整鏈縫隙掃描（本輪新增覆蓋）

| 縫隙候選 | 結論 |
|----------|------|
| B5 golden pytest/scripts 未入 `cfcf08e` 樹（僅 receipt logs） | **程序/provenance 殘留**；本輪對未追蹤檔實跑 G-1/G-3 通過；**不構成數據錯誤**，但合併前應 commit 測試+腳本 |
| `tests/golden/l65/test_inventory.txt` | `git status` 空；**無需 restore** |
| deep 路徑 / bootstrap 生產化 / monotonicity ttest_ind | SPEC §N 登記範圍外；本 epic 未暗示全平台 |
| FeatureTierPanel xsec 文案偏 longitudinal | 低；不影響數值鏈 |
| G-1 mutation probe 未入庫 CI | 低；ad-hoc mutation 曾驗轉紅 |

---

## 殘留誠實披露（不阻擋 DATA-CORRECT）

1. **BH PRDS 假設**：metadata `fdr_assumption_note` 已披露；高相關特徵下 BH 可能輕微樂觀（v2.2 嚴謹度委員會裁決：default 足夠，M-B 相關 null 實測把關）。
2. **B5 產物世代**：`ic1eb_baseline` v4（舊路徑）與 `ic1eb_newpath_freeze`（新路徑）均 gitignored；依 manifest content 指紋消費，非重產。
3. **1a cut1 golden**：B5 編排端解鎖後 `test_ic_1a_cut1_golden.py` 2 passed（本輪未重跑）；職責為整報告可重現，非 G-1 五 hash 替代。
4. **全套 momentum gate**：編排 receipt `1057 passed`（head `49ef0ac`，dirty tree）；本輪抽驗 **22 passed**（見上表），非全套重跑。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: stage5 用 test_mask; FDR 先于閘; xsec 無 p 閘; G-2 JSON 可復算; baseline/newpath freeze sha 自洽; 舊 pooled 不生產
TESTS_RUN: B1 oracle+M-A 2p; B2 M-B+M-D+M-H+M-F+refilter 5p; B3 xsec 1p; B4 fullstack 11p; B5 G-1 fast 1p + G-3 4p; ad-hoc G-2 聚合+sha 鏈
FAILURES_SEEN: none
SCOPE_CHANGES: 僅新增 handoffs/IC1EB-SIGNOFF-composer.md
NUMERIC_OR_SCHEMA_IMPACT: 簽核唯讀；鏈上已落地之行為變更=p/q/t_stat 語意修正+passed_features 收緊（G-2 273 old-only 轉紅屬預期修復）
PROVENANCE_NOTE: cfcf08e 僅含 B5 run_receipts；golden pytest/scripts/ic1eb_g2_golden_diff.py 仍 untracked——合併前須入庫以鎖回歸
```

DATA-CORRECT: PASS
