# 章程驗證 + 過往工作測試差距稽核（Composer 獨立）

> 對照：`docs/TEST_DESIGN_CHARTER.md` vs `handoffs/20260627-TEST-DESIGN-CHARTER-COMPOSER.md`；實讀 `test_ic_1a_cut1_*`、`tests/golden/ic_phase1_contract/`、Phase0 相關測試（2026-06-27）。

---

## 任務1:章程驗證

### 漏項(原版有最終稿無)

1. **§E / §F 完整模組對照表被外置**：Composer 原版含 E1–E5（Feature Factory / IC / 回測 / Cache / API）逐列「模組→風險→必做類別→具體測試/待補」；§F 含 F-IC-1..9、F-MC、F-ST-1..6、F-ML、F5 門檻溯源。最終稿僅摘要 bullet +「全表見 Composer 補全 §E/§F」——**章程本身不可自洽執行**，依賴未入 docs/ 的 handoff。
2. **A2 最低 MR 具名集合（MR-L1/L2/L3）**：Composer 明列三條（test 標籤 future k 置亂→train IC 不變；train 末段刪除→test IC 不變；test 特徵×常數→Spearman IC 不變）。最終稿 A2 只寫「≥2 條 MR」，**丟失可機械勾選的清單**。
3. **B1 最低 mutation probe 具名集合**：Composer 列「移除 purge / train-test 顛倒 fit / cache key 少 symbol → 必紅」。最終稿 B1 有概念但**無最低三探針列舉**。
4. **§0 對 Claude 草稿的獨立裁決表**：Composer 開頭 10 行裁決表（sha256 float 不專業、Hypothesis 必補等）與理由——最終稿併入 §0 分級後**整表消失**，審查追溯性變弱。
5. **成本分層原則**：Composer §0 原則 #2「PR / nightly / pre-release / manual tier-matrix 與 marker 對齊」——最終稿 A18 有 marker 名稱但**未保留成本分層敘述**。
6. **A5 與 A14 分工說明**：Composer 明寫「A2=因果/洩漏 MR；A5=代數/守恆 property（不含未來資料語義）」——最終稿 §A 5 與 14 並列但**分工語句缺失**，易混用。
7. **各 A 類別維度表**：Composer 每類有「維度 | 測什麼 | 過關條件」三列表（如 A1 來源真實性/schema/值守恆/隔離/血緣）。最終稿壓成單段 bullet，**A12 Pydantic↔TS 對照、A19 progress 單調等細節縮水**。
8. **Codex 獨有類別（reconcile 時未完整併入）**：
   - 獨立 **「多 symbol / cross-sectional」** 類（Codex §A-10：per-timestamp rank、symbol matrix、leave-one-out）——最終稿僅散見 A9，**cut2 前必測項無專章**。
   - **回測真實性專章**（Codex §A-11：同 bar stop/TP 優先序、unknown exit 不可 silent、MAE/MFE 手算）——最終稿 §E 一行帶過，**§A 無對應編號**。
   - **d-star strong/weak/exact column fingerprint**（Codex §B Cache 細項）——最終稿 §E 僅「d_star cache key 含 symbol」。
9. **§F 檢定 ID 遺漏**：Composer 有 **F-IC-9**（decay profile 形狀契約）、**F-ST-6**（commission±50% 穩健）——最終稿 §F 未列。
10. **Codex §C 統計補項**：sign test / Wilcoxon / White Reality Check·SPA——最終稿未收。
11. **pytest marker 清單不完整**：Codex 建議增 `real_data`、`flaky_quarantine`、`property`、`metamorphic`；Composer A18 列 `requires_kline`/`network`/`tier_matrix`。最終稿 A18 列後者但**實 repo `pytest.ini` 仍無這些 marker 註冊**（僅 slow/integration/perf 等）——章程寫了但未標「待建」，與 §H「缺 marker」略矛盾。

### 錯誤/誤併

1. **§E/§F「見 Composer 補全」= 誤併未完成**：標題寫「三方收斂 v1」，卻把可執行主表留在外部 handoff，**違反「每份 SPEC 附測試章程」的自包含要求**。
2. **§A 條目 5 標 ORACLE: METAMORPHIC**：Composer A5 為 property oracle（代數/守恆），與 A14 metamorphic **語義不同**；併成 METAMORPHIC **走樣**（Hypothesis 冪等 ≠ 洩漏 MR）。
3. **Codex §0 五級（correctness/contract/regression/smoke/perf）與 Composer Oracle 五級（EXACT/TOLERANCE/…）**：最終稿只保留後者，**未對照映射**——舊 SPEC 若用 Codex 詞彙會對不上。
4. **A10 效能 ORACLE 寫「SMOKE 上界+A7」**：把 perf 上界標成 SMOKE 可接受，但未強調「A7 等價缺失 = BLOCKING」在 §0 分級表重複——**perf PR 門檻分散**，易漏讀。
5. **§H「可當範本：IC 1a leakage…」**：實測 rolling IC **無** scipy 差分（見任務2）——§H 與 §E「ic_engine rolling vs scipy 待補」一致，但「可當範本」易**高估** 1a 數值 oracle 覆蓋。

### 仍遺漏/門檻問題

1. **DATA_MANIFEST**：A17 要求 `tests/fixtures/DATA_MANIFEST.json`——repo **不存在**；golden/kline 漂移無機械 FAIL（§H 已列缺口，但 A17 過關條件仍像已落地）。
2. **G-OLD/G-NEW skip 策略 vs B2**：章程要求主正確性 blocking on real kline；`test_ic_1a_cut1_golden.py` 用 `pytest.skip("baseline absent")`——章程 A17/A18 **未明確**「correctness job 缺 golden = FAIL 非 skip」（Composer A17 有「CI required check 分開」但未入最終稿細節）。
3. **requires_kline marker 未落地**：多數 1a/contract 測試直接讀 `kline_cache.h5`，**無 mark**；缺檔時 pytest 硬 fail 或 golden skip，**不符合 A18 分層敘述**。
4. **Hypothesis 基建**：A5 要求 ≥100 組 `@given`——requirements 仍無 hypothesis（Codex 已點名）——最終稿只括號「需補」。
5. **雙家族 reconcile 後仍缺 Codex 回測/跨截面專章**：高風險 (d) 區在 §A 地圖上**不完整**。

### 章程自相矛盾或不可執行

| 矛盾 | 說明 |
|------|------|
| §G 模板 vs §E/§F | SPEC 須填 §F 檢定項，但 §F 全表不在 docs/ |
| A18 markers vs pytest.ini | 章程列 marker 名，repo 未註冊 → CI 無法依章程分 job |
| B1 mutation 必備 vs 無探針清單 | 要求 P0 有 probe，但未列 1a 最低集 → 接回時無法機械驗 |
| A17 manifest 過關 vs 檔案缺失 | 寫「漂移→明確 FAIL」，實務 golden 缺檔是 skip |

---

## 任務2:差距稽核(優先序)

### 方法

實讀 4× `test_ic_1a_cut1_*.py`（34 tests）、`tests/golden/ic_phase1_contract/`（3 files + baseline meta）、Phase0：`test_ic_phase0_golden.py`、`test_ic_feature_filter.py`、`test_ic_timeaxis.py`、`test_ic_crash_real_config.py`、`tests/momentum/core/test_split_contract.py`；交叉 `test_ic_engine.py`（scipy 對照）。

**Oracle 標記**：EXACT / TOLERANCE / METAMORPHIC / STATISTICAL / SMOKE；P0–P3 對照章程 §0/§B1。

---

### 1a 第一刀 — 現有測試分級（摘要）

| 檔案 | 測試數 | P0 可證偽 | 主要 Oracle | 備註 |
|------|--------|-----------|-------------|------|
| `test_ic_1a_cut1_leakage.py` | 5 | 4 | METAMORPHIC | 真 kline；test 區擾動→train 不變；legacy fit_mask=None 相容 |
| `test_ic_1a_cut1_split.py` | 13 | 6 | EXACT | purge≥horizon、gap fail-closed、pipeline order；`test_split_valid_passes`≈SMOKE |
| `test_ic_1a_cut1_oos.py` | 14 | 5 | METAMORPHIC+EXACT | `test_purge_label_mutation_*` 為真 mutation probe；多測試 mock stage4/5 |
| `test_ic_1a_cut1_golden.py` | 2 | 0* | TOLERANCE | *缺 baseline/input → **skip**，不算 merge gate |

**ic_engine rolling IC vs scipy**：`test_ic_engine.test_compute_ic_matches_scipy` 僅 **逐點** Spearman/Pearson；`test_compute_rolling_ic_and_icir` 只 assert `len>0`、`icir>0`（**SMOKE**）。**1a cut1 全路徑無 rolling-vs-scipy 差分（A15 缺口）**。

**章程 MR-L1/L2/L3 對照**：
- MR-L1（purge 外 label shift→rolling IC 不變）：**部分** `test_purge_label_mutation_does_not_change_test_rolling_ic`（purge 區 label 擾動）。
- MR-L2（train 末段刪除→test IC 不變）：**無**。
- MR-L3（feature×常數→Spearman IC 不變）：**無**（IC 路徑）。

**B1 mutation probe 對照**：
- 移除 purge → **有** `test_holdout_purge_covers_horizon`（purge_gap-1 ValueError）。
- train/test 顛倒 fit → **無專用 probe**（leakage MR 間接覆蓋 train-only fit，未 assert「顛倒必紅」）。
- cache key 少 symbol → **不屬 1a scope**。

---

### 1-contract golden — 現有測試分級

| 檔案 | Oracle | P 級 | 評語 |
|------|--------|------|------|
| `test_split_contract.py` | EXACT | P0/P2 | 強：真 kline + CrossSymbol/TimestampDiscontinuity/SplitPair L1–L4 |
| `test_split_leakage_golden.py` | EXACT+METAMORPHIC | P0 | 真 BTC+ETH；反例必 fail-closed |
| `test_baseline_frozen.py` | SMOKE | P3 | **僅** baseline 檔存在 + sha256；不跑 analyze |
| `test_ic_split_adapter.py` | EXACT | P2 | CPCV/WF 包裝 + 真 kline integrity |

契約層 **split 正確性強**；**端到端 IC baseline 與 1a golden 重疊且可 skip**。

---

### Phase 0 — 現有測試分級

| 檔案 | Oracle | P 級 | 評語 |
|------|--------|------|------|
| `test_ic_timeaxis.py` | EXACT | P0 | 秒/毫秒 epoch、implausible ts fail-closed；`by_volatility`→NotImplemented |
| `test_ic_feature_filter.py` | EXACT | P2 | stable sort truncate、empty→InvalidInputError；45000 col perf 標 slow |
| `test_ic_phase0_golden.py` | TOLERANCE | P1† | **6 列合成** grouped/decay/filter baseline；†不可算 A1 資料正確性 |
| `test_ic_crash_real_config.py` | SMOKE | P3 | GroupedConfig 不崩潰；assert 有 `by_year` key，**無 IC 數值 oracle** |

Phase0 **止血（timestamp/by_volatility fail-closed/feature_filter）有效**；**grouped/decay golden 仍合成 toy，非章程 B2 主路徑**。

---

### 必補(正確性高風險,附模組+為何+建議測試類別)

| 優先 | 模組 | 為何高風險 | 建議測試類別 / Oracle |
|------|------|------------|------------------------|
| **P0-1** | `ic_engine.compute_rolling_ic` | 1a OOS 報告核心指標；現僅 SMOKE，point IC 有 scipy 但 **rolling 無** | **A15** TOLERANCE：小窗 frozen subset vs `scipy.stats.spearmanr` 逐窗 ≤1e-12 |
| **P0-2** | IC 1a OOS 全路徑 | `test_oos_ic_rolling_warmup` 只 assert `ic_mean != full_sample`，**非 trusted oracle** | **A15+A8**：同上 + 真 analyze 路徑比對 stage4 rolling 序列 |
| **P0-3** | 防洩漏 MR 覆蓋 | 章程 MR-L2/L3 **缺失**；僅 purge 區 mutation | **A2/A14 METAMORPHIC**：train 尾刪除；feature×c>0 Spearman 不變（含 OOS slice） |
| **P0-4** | B1 train/test 顛倒 probe | 無「故意 fit on test → 現有 MR 必 FAIL」回歸 | **B1 人工 probe**：注入 `_stage1` fit_mask=test_mask 的 failing test（或 parametrize bug hook） |
| **P0-5** | G-OLD/G-NEW golden | `pytest.skip if absent` → **CI 可无 baseline 绿** | **A17/A8**：correctness job 缺 baseline/input **FAIL**；或 `@pytest.mark.requires_kline` + 专用 job；补 DATA_MANIFEST |
| **P0-6** | `stage5` 统计（1a 已接 OOS） | 无 F-IC-2/8 STATISTICAL 断言；`test_summary_and_threshold_same_scope` 用 **注入假 ic_results** | **A4 STATISTICAL**：合成 IC 序列已知 t/p + train vs test diff CI（F-IC-8）；真实路径 smoke 不足 |
| **P1-1** | Phase0 grouped/decay | 6-row synthetic ≠ 真实 kline 形狀 | **A1+A8**：用 `kline_seconds.csv` 或真 kline 扩 golden；保留 synthetic 仅 A6 |
| **P1-2** | `applied:false` API 契約 | 仅 engine `test_fallback_insufficient_data_*`；前端 metadata 误判 OOS 风险 | **A12 EXACT**：`test_ic_response_v2` / WS payload assert `scope!=test` when `applied:false` |
| **P1-3** | 1-contract baseline | `test_baseline_frozen` 仅 SMOKE | **A8 TOLERANCE**：跑 freeze 命令 regenerate 或 compare 子集 JSON（与 1a golden 去重策略） |

---

### 可延後

| 項目 | 理由 |
|------|------|
| cross_sectional cut2 G-NEW | HANDOFF 下一刀；章程 §E 已标待建 |
| FDR BH 金样本 (1b) | Phase 1b 未开工 |
| Hypothesis 全库 A5 | 基建 + 成本；先用 B1 人工 probe |
| F-IC-4 Newey-West / F-IC-6 标签置乱 | 1a 后增强；非 cut1 阻塞 |
| tier_matrix / quarantine marker 统一 | CI 治理；不改数值正确性 |
| d-star strong/weak fingerprint 全量 | FF 域；非 1a/Phase0 回归面 |
| 回测 A15 双实现 / 同 bar 歧义 | 回测 Epic；与 IC Phase1 解耦 |
| reanalyze_with_thresholds split | HANDOFF 已知 cut2 项 |
| `test_ic_crash_real_config` 升级为数值 oracle | 当前 SMOKE 已满足 Phase0「不崩」止血 |

---

## 结构化收尾

```
ASSUMPTIONS_VERIFIED:
  - 已读 docs/TEST_DESIGN_CHARTER.md、handoffs/20260627-TEST-DESIGN-CHARTER-COMPOSER.md、CODEX 版摘要
  - 已实读 test_ic_1a_cut1_{leakage,split,oos,golden}.py 全部 34 tests
  - 已实读 ic_phase1_contract 3 test modules + test_split_contract.py + Phase0 4 files
  - test_ic_engine.py: point IC scipy yes; rolling IC scipy no (grep+read)
  - pytest.ini: 无 requires_kline/network/tier_matrix marker
  - tests/fixtures/DATA_MANIFEST.json: 不存在

TESTS_RUN: none（文档/稽核任务）

FAILURES_SEEN: none

SCOPE_CHANGES: none（仅新增本 handoff）

NUMERIC_OR_SCHEMA_IMPACT: none

HANDOFF_NOT_UPDATED: 执行合约：不写根 HANDOFF.md
```

STATUS: DONE
