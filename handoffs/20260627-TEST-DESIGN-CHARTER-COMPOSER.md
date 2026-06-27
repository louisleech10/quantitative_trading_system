# 測試設計 & 驗證審查章程（Composer 獨立補全 v1）

> **定位**：回答「此 ML 量化交易專案 + 現有 code，該做哪些測試類別、過關條件為何、測試設計本身如何受審」。
> **方法**：獨立審閱 `handoffs/20260627-TEST-DESIGN-CHARTER-CLAUDE-DRAFT.md`，不附和其框架；以測試工程 + 量化實務標準補缺、收緊門檻、對應本 repo 具體模組。
> **用途**：往後每份 SPEC 的「測試章程」須從 §A 勾選 + §E 對照表填寫；§B 為 meta-審查紀律；§F 為統計檢定清單。

---

## §0 對 Claude 草稿的獨立裁決（先講缺口，再給完整表）

| 草稿項 | 裁決 | 理由 |
|--------|------|------|
| §A 全表 13 類 | **保留骨架，但 3/4/5/10 門檻過鬆或混層** | 「sha256 全表」對 float 特徵不專業；「統計檢定通過」無檢定名稱=不可證偽；性質測試與 metamorphic 未分級 |
| 缺 property-based | **必補** | 專案已有 permutation/cache 不變量（`test_failopen_correctness` V-7），但未制度化 Hypothesis 覆蓋 split mask、aligner、metrics |
| 缺 metamorphic | **必補** | IC 洩漏測試本質是 metamorphic（`test_winsor_bounds_from_train_only`）；需明確列為一類並規範 MR 集合 |
| 缺 fuzzing | **條件必補** | API/Pydantic 邊界、config override 巢狀 dict、HDF5 路徑 — 適合 structure fuzz，不適合對 OHLCV 亂數 fuzz 當正確性 oracle |
| 缺 CI flaky 治理 | **必補** | HANDOFF 已記錄 `tests/api` IC timeout；無 marker 分層 + quarantine 紀律會持續假綠/假紅 |
| 缺 test data 版本化 | **必補** | `kline_cache.h5`、golden JSON 無統一 manifest → 換機/換 cache 時 golden 漂移無法歸因 |
| §B mutation | **方向對，操作化不足** | 須定義「人工 mutation probe」最低集合與 smoke 分級，不必強制 mutmut |
| 缺 differential / oracle 分層 | **必補** | 向量化回測 vs 慢速 reference、rank-IC vs `scipy.stats` — 草稿未要求雙實作比對 |
| 缺 fault/chaos | **高風險區必做** | resume、RunLease、batch 中斷、CGSA memmap — 僅 happy path 不足 |
| 缺觀測性/契約測試 | **API 層必做** | `metadata.scope`、`applied:false` vs OOS 語義 — 須契約測試防誤判 |

**新增核心原則（草稿未寫）**：
1. **Oracle 分級**：每條測試須標 `ORACLE={EXACT|TOLERANCE|METAMORPHIC|STATISTICAL|SMOKE}`；僅前四類可計入「正確性保證」。
2. **成本分層**：PR 必跑 / nightly / pre-release / manual tier-matrix — 與 `@pytest.mark.slow` 對齊並擴充。
3. **真實資料政策**：資料正確性類 **禁止** 合成 OHLCV 作唯一 oracle；允許合成作 **邊界退化** 或 **雙實作對照** 的輔助。

---

## §A 測試類別地圖（完整版）

圖例：**✦** = 本專案高風險預設必做；**ORACLE** = 允許的判定方式；**過** = 專業過關條件（可機械驗證）。

### A1. ✦ 資料正確性 / 完整性 / 血緣（Data Correctness）

| 維度 | 測什麼 | 過關條件 |
|------|--------|----------|
| 來源真實性 | L0 讀 `kline_cache.h5`、adapter fetch | `skip` 僅當檔案缺失且測試標 `requires_kline`；**不得**用隨機 OHLCV 冒充「資料正確性」主測 |
| Schema/dtype | index `int64` epoch **秒**、欄位名、HDF5 compound | 契約 assert + 真實檔案 smoke；違反即 BLOCKING（V2 timestamp 事故） |
| 值守恆 | merge 前後列數、單調 ts、OHLC 關係 `low≤open,close≤high` | 全量或窗口內 **100%** 列檢查，非抽樣 |
| 隔離 | symbol A 特徵不含 B 的價格/欄位 | permutation + 並行 batch 後 per-symbol hash 不變 |
| 血緣 | `config_hash`、manifest、`feature_run_dir` 一致 | mismatch **raise**，測試預期 `ICReadError` 等 |

**ORACLE**：`EXACT`（schema/count）+ `METAMORPHIC`（隔離）。

---

### A2. ✦ 防洩漏 / 前瞻 / PIT（Leakage & Causality）

| 維度 | 測什麼 | 過關條件 |
|------|--------|----------|
| Split 契約 | `purge_gap ≥ label_horizon`、`embargo`、train/test 不交疊 | 契約單元 + 真實 IC 路徑；違反 `ValueError` |
| Fit-on-train | winsor/standardize/coverage 只用 `fit_mask` | **Metamorphic**：test 區極端值擾動 → train 區輸出 **bitwise 相等**；test 區可被 clip |
| 特徵因果 | rolling/lag/MTF align 不用未來 bar | 凍結 bar 子集 + 截斷資料重算 → 歷史段 **不變** |
| 評估範圍 | IC 報告 `metadata.scope=test`；`applied:false` ≠ OOS | 契約測試：fallback 路徑不得進 FDR/排序主榜 |
| Rows vs timedelta purge | `purge_semantic` 分支 | 不規則 ts → `irregular_ts` raise（已產品決策），測試鎖死 |

**ORACLE**：`METAMORPHIC`（主）+ `EXACT`（契約欄位）。

**最低 MR 集合（每個改 split/preprocess/align 的 Task 至少覆蓋 2 條）**：
- MR-L1：test 標籤未來 k 期置亂 → train IC 不變
- MR-L2：train 末段刪除 → test IC 不變
- MR-L3：test 特徵乘常數 → Spearman IC 不變（rank 不變時）

---

### A3. ✦ 數值正確性 / Golden / 決定性（Numerical & Golden）

**修正草稿**：float 表不可用裸 `sha256`；分三層：

| 層級 | 適用 | 過關條件 |
|------|------|----------|
| L1 整數/邏輯 | mask、count、index、bool gate | `==` 或 `pd.testing.assert_index_equal` |
| L2 浮點特徵 | 特徵矩陣、IC 彙總 | **分欄策略**：`nan` 位置 exact；finite 值 `abs≤1e-9` 或 `rel≤1e-7`（與 `test_ic_1a_cut1_golden` 一致）；**禁止**放寬既有 tolerance |
| L3 整表指紋 | 回歸監控 | canonical hash（sorted columns + fixed endian float64 view）— 用於 **回歸告警**，非唯一 oracle |

| 維度 | 測什麼 | 過關條件 |
|------|--------|----------|
| NaN/inf gate | L7 validator、preprocess | inf → reject/clip；非法比例 > 閾值 → fail-closed |
| 決定性 | 同 seed、同 thread 數 | 兩次 run canonical hash 相等；**豁免清單寫死** `{generated_at, run_id, wall_time}` |
| Flag 相容 | G-OLD flag-off | deep-equal baseline JSON（pop 豁免後） |
| 優化等價 | Numba on/off、fast path | `TOLERANCE` 雙路徑 max diff ≤ 既有 frozen budget |

**ORACLE**：`EXACT` | `TOLERANCE` | `METAMORPHIC`（雙路徑）。

---

### A4. 量化 / 統計嚴謹（Quantitative Rigor）

見 **§F 完整檢定清單**。過關總則：
- 每個 **對外門檻**（IC min、FDR q、Sharpe cut）須有 **文件化依據**（樣本量公式或引用文獻/內部 calibration run ID）
- 檢定結論須報 **效應量 + 不確定性區間**，非僅 p-value
- 多重比較場景 **禁止** 逐特徵裸 p-value 排序而不校正

**ORACLE**：`STATISTICAL`（需預註 α、n_min、校正方法）。

---

### A5. 不變量 / 性質測試（Invariant & Property-Based）

| 類型 | 測什麼 | 過關條件 |
|------|--------|----------|
| 代數不變量 | IC rank 對單調變換、winsor 冪等、align 冪等 | 對 **≥100** 組隨機合法輸入（Hypothesis `@given` 或 seeded loop）成立 |
| 守恆 | 資金曲線起點、持倉 bound、prob ∈ [0,1] | 性質失敗即 shrink 出最小反例並 **固定為回歸用例** |
| 組合不變量 | symbol 順序、cache 冷/熱 | 已有 V-7 模式，推廣到 batch resume 後 |

**與 A2 分工**：A2 = 因果/洩漏 MR；A5 = 代數/守恆 property（不含「未來資料」語義）。

**ORACLE**：`METAMORPHIC` | property oracle。

**建議工具**：`hypothesis`（numpy/pandas strategies）；`assume()` 過濾非法 OHLC。

---

### A6. 邊界 / 退化 / 錯誤分類（Boundary & Degradation）

| 情境 | 預期行為 | 過關條件 |
|------|----------|----------|
| 空/單列/全 NaN | 明確 raise 或 empty result + `eval_status` | **禁止** silent NaN 傳播進 IC 排序 |
| 不規則 ts | IC rows purge | `irregular_ts` → raise（非 fallback） |
| insufficient data | default-ON split | `applied:false` + 仍產 report + **不得**標 test OOS |
| 極端價格/零 volume | L0/L1 | graceful skip 或 gate fail，有分類 log |
| API 無效 symbol | non-retryable | HTTP/WS 錯誤碼契約 |

**ORACLE**：`EXACT`（exception 類型 / status enum）。

---

### A7. 行為不變型重構（Refactoring Parity）

| 維度 | 過關條件 |
|------|----------|
| 輸出值 | L2 tolerance 或 L1 exact |
| 輸出形狀 | `(n_rows, n_cols)`、檔案大小差 ≤ 0.5% 須 **明示批准** |
| 效能 | 可變快，語義不可變 |

**ORACLE**：`TOLERANCE` + optional perf budget。

---

### A8. ✦ 整合 / 真實管線（Integration & Materialized Path）

| 層級 | 路徑 | 過關條件 |
|------|------|----------|
| G-OLD | flag-off / 舊預設 | materialized `analyze()` 或 `generate_features()` **端到端** |
| G-NEW | 新預設 | 同上 + 新契約欄位 |
| Service | `api/services/*` + worker | 真實 kline **或** tmp_path symlink kline + hermetic `data_cache` diff 空 |

**教訓（IC 1a）**：unit fixture 抓不到 `_slice_by_mask` index bug — **任何改主流程的 Task 至少 1 條 G-NEW/G-OLD**。

**ORACLE**：`TOLERANCE` golden 或 `EXACT` JSON 子集。

---

### A9. ✦ 跨 tier / 多 symbol / OOM / Resume / Fault

| 維度 | 過關條件 |
|------|----------|
| RAM tier | 8/16/24/32GB **語義一致**（允許時間差）；用 `@pytest.mark.tier_matrix` 或 perf smoke JSON |
| 多 symbol | N≥2 真實 symbol 串行/並行；per-symbol artifact 隔離 |
| Resume | 中斷後續跑 → 無孤兒 temp、無重複列、manifest 一致 |
| RunLease | 雙進程同 key → 一方等待或 fail closed |
| OOM | 降級路徑（offload/CGSA）觸發後結果仍 **TOLERANCE** 等價 |

**ORACLE**：`METAMORPHIC`（中斷前後）+ `TOLERANCE`。

---

### A10. 效能 / 回歸（Performance Regression）

| 維度 | 過關條件 |
|------|----------|
| 基線 | committed budget JSON（如 `test_batch1_followup` frozen budget） |
| 規模化 | 時間複雜度 **不得** 從 O(n) 悄悄變 O(n²)（固定 n 序列 benchmark） |
| 語義學 | perf 改動 **必附** A7 等價測試；僅 perf PR 無等價 → BLOCKING |

**ORACLE**：SMOKE 時間上界 + A7 語義 oracle。

---

### A11. 架構契約 / 解耦（Architecture Contract）

| 檢查 | 過關條件 |
|------|----------|
| `grep -r "from api\." momentum/` | 0 |
| services 互引 | 0 |
| factories | 測試只 `create_*`，不 direct engine import |
| DTO 邊界 | `api/models` ↔ `contracts.py` 無交叉 import |

**ORACLE**：`EXACT`（腳本 exit 0）。

---

### A12. API / 型別 / 相容（API & Schema Contract）

| 維度 | 過關條件 |
|------|----------|
| Pydantic ↔ TS | 欄位名/optional/required 對照表或 codegen 單測 |
| WS 協議 | message schema、terminal state 不變 |
| 向後相容 | 新參數有 default；舊 client payload 仍 200 |
| eval_status | legacy feature 不進榜 — response snapshot |

**ORACLE**：`EXACT` contract + snapshot（快照變更需 REVIEW）。


---

### A13. 冪等 / 重現性（Idempotency & Reproducibility）

| 維度 | 過關條件 |
|------|----------|
| 同 config_hash | 兩次 persist → 讀回 hash 相等 |
| cold vs hot cache | 已有 `test_v7_cache_cold_hot_identical` 模式 |
| Optuna seed | 同 seed 同 study 參數軌跡（允許浮點末位差） |
| 平行度 | `NUMBA_NUM_THREADS=1` 於 CI correctness；perf job 另跑 |

**ORACLE**：`TOLERANCE` canonical hash。

---

### A14. **新增** Metamorphic Testing（變換關係）

**定義**：已知變換 T，滿足 `Q(S) = Q(T(S))` 或 `Q(T(S))` 可解析變化。

| 領域 | 變換 T | 預期 Q |
|------|--------|--------|
| IC Spearman | feature × c (c>0) | IC 不變 |
| label | label 整體 shift（在 purge 外） | rolling IC 序列不變 |
| winsor | 重複 winsor | 等於一次 winsor |
| MTF | 多餘高頻未用欄位 | 輸出不變 |
| 回測 | 同時 scale price & ATR | 交易次數/方向不變 |

**過關**：每模組 **≥3** 條 MR，且 **≥1** 條在真實 kline 路徑執行。

**ORACLE**：`METAMORPHIC`。

---

### A15. **新增** Differential / Dual-Oracle（雙實作對照）

| 對照 | 過關條件 |
|------|----------|
| `VectorizedBacktest` vs 逐 bar reference | 交易 list 等價（價格 tolerance 1e-8） |
| rank IC vs `scipy.stats.spearmanr` | max abs diff ≤ 1e-12（小樣本） |
| fast winsor vs legacy | `test_perf_winsor_identical` 模式 |
| pandas rolling vs numba | frozen subset |

**ORACLE**：`TOLERANCE` vs trusted slow oracle。

---

### A16. **新增** Fuzzing / Robustness（結構魯棒）

| 目標 | 方法 | 過關條件 |
|------|------|----------|
| `ICConfig` / FF config JSON | 隨機巢狀、缺欄、型別錯 | **不 crash** → ValidationError 可預期 |
| 檔案路徑 | 不存在 HDF5、壞 manifest | 分類錯誤 + non-retryable |
| WebSocket payload | 畸形 JSON | 連線不掛、錯誤帧 |

**禁止**：對 OHLCV 數值 unrestricted fuzz 當「正確性通過」。

**ORACLE**：`EXACT`（exception 類型）| `SMOKE`（不 segfault）。

---

### A17. **新增** Test Data 版本化 & Golden 治理

| 項目 | 規範 |
|------|------|
| Kline | `tests/fixtures/DATA_MANIFEST.json`：`kline_cache.h5` sha256、symbols、TF、row counts、凍結日期 |
| Golden JSON | 檔名含 `config_hash`；側車 `.meta.json` 記錄：git commit、manifest hash、freeze 命令 |
| 缺失策略 | `pytest.importorskip` / `skipif not path` + **CI required check 分開**： correctness job 須有 cache |
| 更新流程 | golden 變更 = **獨立 PR** + adversarial + 三方簽核（資料類） |

**過關**：任何 golden 測試可追溯到 manifest 條目；manifest 漂移 → 測試 **明確 FAIL** 而非 silent 更新。

---

### A18. **新增** CI Flaky / Quarantine 治理

| 規則 | 內容 |
|------|------|
| Markers | `slow`, `integration`, `requires_kline`, `network`, `tier_matrix` — **PR 預設排除 slow** |
| Quarantine | 連續 3 次 main 無關失敗 → `@pytest.mark.quarantine` + issue ID；**不**刪 assert |
| Timeout | IC API 測試：mock 網路或 mark `network`；禁止與 correctness 同 job 無超時裸跑 |
| 並行 | `pytest-xdist` 與 RunLease 測試分組；檔案系統測試用 `tmp_path` |
| 重試 | 僅 `network`/`flaky` mark 允許 `pytest-rerunfailures` ≤2；correctness **禁止** rerun |

**過關**：CI 文件化 job 矩陣；quarantine 測試不計入 merge gate 但須週期修復。

---

### A19. **新增** 觀測性 / 運維契約（Observability Contract）

| 維度 | 測什麼 |
|------|--------|
| Progress | layer % monotonic、RSS 欄位型別 |
| Batch state | terminal vs completed 語義（HANDOFF 殘留項） |
| Error 分類 | retryable 標籤影響 worker 行為 |
| Metadata | `scope`、`applied`、`eval_status` 必達前端型別 |

**ORACLE**：`EXACT` on critical metadata。

---

### A20. **新增** ML 校準 / 對抗（Calibration & Adversarial ML）

| 維度 | 過關條件 |
|------|----------|
| 機率校準 | Brier score / reliability diagram 單調性（有校準器時） |
| 標籤洩漏探針 | 打亂 label → AUC/IC 降至 null 附近 |
| 特徵置換 | 單特徵 shuffle → IC 崩潰 |
| Walk-forward / CPCV | factory 存在即 **至少 smoke** 覆蓋 API |

**ORACLE**：`STATISTICAL` + `METAMORPHIC`。

---

## §B 測試設計審查紀律（Meta-QA）

### B1. 可證偽分級（強化草稿 mutation 條款）

| 級別 | 定義 | Merge 是否計入正確性 |
|------|------|----------------------|
| **P0 正確性** | 有 mutation probe：人工注入已知 bug（如拿掉 `fit_mask`）必 FAIL | 是 |
| **P1 回歸** | Golden/tolerance 對真實路徑 | 是 |
| **P2 契約** | schema/status enum | 是（API） |
| **P3 Smoke** | 只 assert 非空/200/有欄位 | **否** |

**最低 mutation probe 集合（改動相關模組時抽 1 條）**：
- 移除 purge → 測試必紅
- train/test 顛倒 fit → 測試必紅
- cache key 少 symbol → 隔離測試必紅

做不到 → 降級 P3 並 **禁止** 在 SPEC 寫「資料正確性已驗證」。

### B2. 真實路徑（保留並加硬）

- Sanitized fixture 僅用於 **A6 邊界** 或 **A15 慢速 oracle 的輸入**
- 主正確性路徑：`data_cache/feature_klines/kline_cache.h5` 或 byte-faithful 錄製（含 **index dtype + 單位**）
- Symlink kline + hermetic tmp `data_cache`（`test_b4_hermetic_data_cache_diff_empty` 模式）算真實路徑

### B3. 防假綠（保留）

- diff 既有 assert；放寬 tolerance 須 SPEC 明列 + adversarial
- 禁止 `pytest.skip` 把 failing 變 skipped completed

### B4. 覆蓋追溯矩陣

SPEC 須附表：

```
| 性質 ID | 類別 | Oracle | 測試檔:函式 | Mutation probe |
```

缺口 = BLOCKING。

### B5. 測試章程 adversarial（保留）

- 攻擊 **測試** 非實作：弱 oracle、合成掩蓋、缺少 MR、無 manifest
- 雙家族：實作 review + 測試 design review **分開出 finding**

### B6. **新增** 統計檢定設計審查

- 每個 `STATISTICAL` 測試須預註：H0/H1、α、n_min、多重比較策略、是否條件於同一 data slice
- 禁止 **data snooping**：用 test 集調門檻再報 test 績效

### B7. **新增** Fixture 審計清單

每個 fixture 標：
- `FAITHFUL | SYNTHETIC | MOCK`
- 覆蓋的真實契約欄位列表
- 已知不覆蓋項（例如 ms vs s）

---

## §C 流程接入點

| 階段 | 動作 |
|------|------|
| SPEC | 從 §A 勾選 + 填 §E 對照 + §F 檢定項；產「測試章程」附 B4 矩陣 |
| Adversarial | 專審測試章程（B5）+ 統計設計（B6） |
| 實作 | 先寫 P0/P1 再寫 feature code（TDD for leakage/numerics） |
| 接回 | Claude 抽 mutation（B1）；diff assert（B3）；核 G-NEW 是否真跑 |
| 資料三方簽核 | A1+A2+A8 真實 kline；Composer/Codex/Claude 獨立 |
| Release | tier-matrix + full slow + manifest 版本對齊 |

---

## §D 取捨與不做清單

| 不做 / 降級 | 原因 |
|-------------|------|
| 全庫 mutmut CI | 成本過高；用 B1 人工 probe 替代 |
| OHLCV 數值 fuzz 當 oracle | 無金融語義 |
| 100% line coverage gate | 不保證量化正確性 |
| 合成 kline 三方簽核 | 違反 Data Truth 原則 |
| 每 PR 全 tier-matrix | 放 nightly；PR 跑縮影 tier |

---

## §E 本專案高風險模組 → 必測清單

### E1. Feature Factory（`momentum/FeatureEngineering/`）

| 模組 | 風險 | 必做類別 | 具體測試 / 待補 |
|------|------|----------|----------------|
| L0 `_layer0_data_ingestion` | epoch 秒 vs ms | A1,A8 | `test_v2_timestamp_golden`；擴展多 TF |
| `MultiTFGenerator` / `TimeframeAligner` | PIT、對齊錯位 | A2,A14,A15 | `test_mtf_align_golden`；**補** MR：截斷高頻未來 bar |
| L6.5 causal winsor / fracdiff | 非因果、cache 污染 | A2,A3,A9 | `test_ff_causal_golden`, `test_causal_winsor`；d_star cache key 含 symbol |
| `_d_star_cache.DStarCache` | 跨 symbol、部分失效 | A1,A9,A13 | value_fp 局部失效；**補** 跨 symbol 檔名隔離 |
| `FeatureStorage` / `RunLease` | 雙寫、鎖 | A9,A13 | **補** 雙進程 lease 競爭 |
| `feature_factory.generate_features` | 7 層整合 | A8,A7 | G-NEW full run（縮窗可）；batch resume |
| Warmup / trim | 誤裁切 | A6,A19 | `test_b6_warmup_trim` |
| Failopen 路徑 | 語義分歧 | A7,A15 | `test_failopen_frozen_diff`, V-7 系列 |
| IC-first pipeline | L7 raw → IC 讀取 | A1,A8 | `test_ic_first_pipeline`, manifest hash |
| Batch multi-symbol | 順序/並行污染 | A1,A9 | `test_v7_symbol_order_permutation_invariant`, `test_multi_symbol_ic_first` |
| Progress / RSS | 假進度 | A19 | API normalize 測試 |

### E2. IC Gatekeeper（`momentum/Analysis/`）

| 模組 | 風險 | 必做類別 | 具體測試 / 待補 |
|------|------|----------|----------------|
| `ic_filter_orchestrator` split | purge/horizon | A2,A8 | `test_ic_1a_cut1_split`, `test_ic_1a_cut1_leakage` |
| `DataPreprocessor` | train-only fit | A2,A14 | winsor/coverage/standardize MR |
| `analyze()` OOS | scope 語義 | A8,A12 | `test_ic_1a_cut1_oos`, golden G-NEW |
| `ic_engine` rolling IC | 算法錯 | A15,A5 | **補** vs scipy；window 邊界 |
| cross_sectional | 未接 split（cut2） | A2,A8 | cut2 上線後 G-NEW 必做 |
| FDR / `eval_status`（1b） | 多重比較 | A4,A12 | **待建** BH-FDR 金樣本 |
| `_deep_analysis_cache` | stale hit | A13,A6 | **補** config 變更 invalidation |
| `reanalyze_with_thresholds` | 次路徑無 split | A2 | cut2 前標 known gap |
| L7 raw manifest | hash mismatch | A1 | `ICReadError` 契約 |
| Default-ON fallback | 假 OOS | A6,A12 | `applied:false` 契約測試 |

### E3. 回測（`momentum/Strategy/`）

| 模組 | 風險 | 必做類別 | 具體測試 / 待補 |
|------|------|----------|----------------|
| `VectorizedBacktest` | look-ahead、信號時點 | A2,A14 | **補** 信號延遲 1 bar MR；現有多為 smoke |
| `performance_metrics` | 年化因子、DD | A15,A4 | **補** 手算 Sharpe/MDD 對照 |
| `position_sizing` | Kelly cap | A5,A6 | 邊界：0 倉、max cap |
| Optuna `StrategyBacktestObjective` | overfit | A4,A20 | integration smoke；**補** CPCV/walk-forward 煙霧 |
| Commission/slippage | 雙計/漏計 | A15 | 單筆交易 PnL 手算 |

### E4. Cache / 儲存（`data_cache/` 語義）

| 模組 | 風險 | 必做類別 | 具體測試 / 待補 |
|------|------|----------|----------------|
| `config_hash` 組成 | 錯 hash 命中舊檔 | A1,A13 | `test_feature_library_config_hash` |
| Feature run 目錄 | 跨 run 讀錯 | A1 | manifest + path 契約 |
| Batch retention / orphan | 誤刪 | A9,A19 | `test_b4_bulk_delete_orphan`, hermetic diff |
| API `data_cache_path` | 污染生產 | A8 | monkeypatch tmp_path 預設 |
| CGSA memmap / resume | 孤兒檔 | A9 | `test_cgsa_resume` |

### E5. API / WebSocket（`api/`）

| 模組 | 風險 | 必做類別 | 具體測試 / 待補 |
|------|------|----------|----------------|
| IC analysis WS | timeout/flaky | A18,A12 | mock transport；mark `network` |
| Feature factory batch | resume 語義 | A8,A9 | `test_feature_factory_batch_resume` |
| Response v2 | 型別漂移 | A12 | `test_ic_response_v2` |
| XGBoost training gate | 錯誤放行 | A6,A20 | `test_xgboost_training_gate` |

---

## §F 量化 / 統計檢定清單（具體可執行）

### F1. IC / 因子評估

| ID | 檢定/量度 | H0 / 用途 | 最低報告 | 本專案觸發點 |
|----|-----------|-----------|----------|--------------|
| F-IC-1 | Spearman/Pearson IC | — | IC mean, std, n_periods | `ic_engine`, summary_table |
| F-IC-2 | IC 序列 t 檢定（mean IC=0） | H0: μ_IC=0 | t, p, **IC mean**, n_eff | 單因子報告；n_eff≥30 才報 |
| F-IC-3 | Fisher z + CI | — | 95% CI on mean IC | 取代只看點估計 |
| F-IC-4 | Newey-West 調整 | 自相關 | 調整後 SE on mean IC | rolling IC 自相關>0.1 時 **必做** |
| F-IC-5 | ICIR 穩定性 | — | ICIR, rolling ICIR std | `ICIRConfig` |
| F-IC-6 | 標籤置亂 | H0: IC=0 | permuted IC << real | **P0 metamorphic** |
| F-IC-7 | 特徵置換 | H0: 無預測力 | shuffled IC ≈ 0 | 篩選前 sanity |
| F-IC-8 | 結構斷點 | 穩定性 | train vs test IC diff + CI overlap | 1a OOS 必報 |
| F-IC-9 | 衰減 profile | — | IC decay lag 單調（非檢定，形狀契約） | `test_ic_decay_log` 擴展 |

### F2. 多重比較 / 特徵篩選（Phase 1b+）

| ID | 檢定 | 過關 | 觸發 |
|----|------|------|------|
| F-MC-1 | Benjamini–Hochberg FDR | q 明訂（如 0.1）；**僅對 `eval_status=valid` + scope=test** | 特徵數 m>10 |
| F-MC-2 | 有效 m 記錄 | 報告 m、拒絕數、fallback 未進 m | `applied:false` 排除 |
| F-MC-3 | 家族 wise error | 不得逐特徵獨立宣稱「顯著」無校正 | reporter 輸出審計 |

### F3. 策略 / 回測 / 優化

| ID | 檢定/量度 | 用途 | 過關 |
|----|-----------|------|------|
| F-ST-1 | Sharpe 年化 | 頻率一致 | 手算對照 `freq` 參數 |
| F-ST-2 | Deflated Sharpe Ratio (DSR) | 多重試錯修正 | Optuna trials>10 時 **建議必報** |
| F-ST-3 | PBO (CSCV) | overfit 機率 | 重大策略發布前 |
| F-ST-4 | Bootstrap equity CI | 不確定性 | 報告 5%/95% Sharpe CI |
| F-ST-5 | 交易次數 n_trades | 效力 | n<30 不得宣稱「顯著獲利」 |
| F-ST-6 | 成本敏感度 | 穩健 | commission±50% 方向不變（探索性） |

### F4. ML 驗證（`model_validation/`）

| ID | 方法 | 過關 |
|----|------|------|
| F-ML-1 | Walk-forward | 至少 3 fold smoke；無 test 洩漏 |
| F-ML-2 | Combinatorial Purged CV | purge≥horizon 契約測試 |
| F-ML-3 | Adversarial validation | 特徵分佈可分 → 報警 |
| F-ML-4 | Learning curve | 高方差診斷（非 gate） |
| F-ML-5 | 機率校準 | Brier ↓ vs 未校準 |

### F5. 門檻溯源（凡 SPEC 寫死數字）

| 欄位 | 須附 |
|------|------|
| min IC / min ICIR | 樣本量公式或 calibration run ID |
| FDR q | 業務可接受 FDR 文件 |
| purge_gap | = f(horizon) 推導 |
| winsor % | 對 tail 敏感度的 sensitivity（可選） |

**測試化**：對 F-IC-2/F-MC-1 用 **合成 IC 序列**（非合成價格）構造已知 p/FDR 場景，assert 決策邊界。

---

## §G SPEC 測試章程模板（複製用）

```markdown
### 測試章程 — <Task ID>

**風險原則**: (a)(b)(c)(d) 命中項
**必做類別**: A1, A2, …
**Oracle 矩陣**:
| 性質 | 類別 | Oracle | 測試 | Mutation |
|------|------|--------|------|----------|
**統計 (§F)**: F-IC-2, F-MC-1, …
**真實路徑**: G-OLD / G-NEW / hermetic
**資料 manifest**: kline_cache.h5@<sha>
**CI**: PR=nightly=slow 標記
**已知不測**: …
```

---

## §H 與現有測試資產對照（健康度）

| 已有（可當範本） | 缺口 |
|------------------|------|
| IC 1a leakage/split/oos/golden | cross_sectional、FDR、deep cache invalidation |
| failopen V-7 系列 | Hypothesis 化、正式 DATA_MANIFEST |
| mtf_align_golden | 截斷未來 bar MR |
| b4 hermetic data_cache | 推廣到所有 batch API 測試 |
| vectorized_backtest 邊界 | 缺 A15 雙實作、look-ahead MR |
| `@pytest.mark.slow` 部分存在 | 缺 quarantine/network/tier_matrix 統一 |

---

## 收尾報告

```
ASSUMPTIONS_VERIFIED: 已讀 Claude 草稿、HANDOFF、tests/ 抽樣（IC 1a、failopen V-7、mtf golden、backtest、hermetic b4）；模組路徑與現有測試名稱來自 repo grep/read
TESTS_RUN: none（文件任務）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅新增 handoffs 檔）
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_NOT_UPDATED: 使用者指令僅產章程檔；根 HANDOFF 由 Claude 維護
```

STATUS: DONE
