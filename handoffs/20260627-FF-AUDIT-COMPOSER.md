# Feature Factory 正確性 Scoping 稽核 — Composer 獨立稿

> 任務：按 `docs/TEST_DESIGN_CHARTER.md` §0 Oracle + §E1，實讀 FF 核心碼與測試，對 6 GIGO 致命軸分級現況、標缺口、給 scoping 判斷。
> 方法：獨立讀碼（非附和 `handoffs/20260627-FF-AUDIT-CLAUDE-DRAFT.md`）；抽查 ~40 測試檔 + 全軸 grep；FF 相關測試檔約 133（含 feature_engineering/cgsa/l65/failopen/operators 等）。
> 信心：`partial` — 未跑 mutation probe 留證、未全量 pytest；分類依檔案內容與章程對照。

---

## 1. Scoping 總判（地基）

| 維度 | 判斷 | 理由（一句） |
|------|------|-------------|
| **整體地基** | **有疑** | 對齊/L6.5 因果/整合 MR 有真 kline 硬測；但 **L1 原子指標幾乎無 differential**，且章程要求的「截斷未來 bar」MR 全庫缺席。 |
| 需否深稽 | **要，但分軸** | 軸 2/3/4/6 可收斂補洞；軸 1 需專項 A15 _campaign_（指標面太大，不能靠 golden 一檔蓋過）。 |
| 最該先補 | ① L1 vs TALib 抽樣 differential；② 全管線「未來 bar 不影響歷史」MR；③ `requires_kline` job 缺檔 FAIL + DATA_MANIFEST。 |

**與 Claude 草稿分歧（重要）**
- 草稿正確指出「問題在嚴謹度非有無」；但 **低估軸 1 系統性風險**（operators/L3 有 oracle，L1 幾乎 smoke）。
- 草稿把 `test_cross_symbol_features` 當軸 6 線索 — **誤導**：該檔測 legacy `FeatureExtractor` 命名/分布，**不是** CGSA/FF 生成隔離；真隔離在 `test_failopen_correctness` V-7 + `test_cgsa_multi_symbol_isolation`。
- 草稿未強調：**failopen V-5/V-6/V-7 已是 FF 整合因果/隔離的主力**，強度高于多數 golden 檔。

---

## 2. 六軸測試嚴謹度分級

圖例：**P0**=correctness+可證偽意向；**P1**=regression/golden；**P2**=contract；**P3**=smoke/perf。Oracle：EX/TOL/META/STAT/SMK。

### 軸 1 — 特徵計算正確性（operators / indicators / L1–L3）

| 測試資產 | Oracle | P級 | 保證 | 評語 |
|----------|--------|-----|------|------|
| `tests/test_numba_rolling.py` | TOL | **P0** | correctness | L3 fused rolling vs pandas；覆蓋 mean/std/min/max/rank/skew 等；**真 differential**。 |
| `tests/test_feature_factory_operators.py` | TOL | **P1** | correctness(partial) | derived/lag/worldquant **單點**手算；TALib 僅 2 指標 spot check；需 kline 否則 skip。 |
| `tests/test_multi_window_rolling.py` | TOL | P1 | regression | rolling aggregator 路徑等價。 |
| `tests/feature_engineering/test_numeric_guards.py` | TOL | P1 | correctness | safe_denominator 防 1e14；**邊界代數**，非全管線。 |
| `tests/test_fracdiff_fft_opt.py` | TOL | P1 | correctness+perf | FFT vs `np.convolve`；**合成序列**，非真 kline fracdiff 語義。 |
| `tests/feature_engineering/preprocessing/test_l65_v2_transforms.py` | TOL | P1 | regression | L6.5 變換 vs scipy ndtri 等。 |
| `tests/test_polars_phase4.py` | TOL/SMK | P2–P3 | contract/perf | polars 分支；部分 inf 掃描。 |
| `tests/momentum/test_feature_extractor.py` | SMK | **P3** | smoke | legacy extractor；非 7-layer FF 主路徑。 |
| **L1 atomic（~13 模組 via TALibWrapper）** | — | **缺口** | — | **無**系統性 TALib/scipy 對照；生產指標數百列僅靠「能算出來」。 |

**軸 1 小結**：L3 rolling + L2 derived **有** reference；**L1 是 GIGO 最大單點** — 公式錯則下游全錯，現況 mostly smoke。

---

### 軸 2 — 生成期因果 / 無前瞻

| 測試資產 | Oracle | P級 | 保證 | 評語 |
|----------|--------|-----|------|------|
| `preprocessing/test_causal_winsor.py` | META | **P0** | correctness | 尾端擾動→歷史 winsor/gaussian/fracdiff/native **不變**；覆蓋 L6.5 多路徑。 |
| `preprocessing/test_ff_causal_golden.py` | META+TOL | **P0** | correctness | rolling quantile oracle + 擾動 MR；e2e `generate_features` 僅 **no inf** smoke。 |
| `preprocessing/test_causal_pin_force.py` | META | P0 | correctness | causal 強制釘死 + fracdiff/native 擾動。 |
| `test_failopen_correctness.py` **V-5** | META | **P0** | correctness | **截短 end_date** → warmup 後 prefix **byte 相等**；真 kline + 全層 fast config。 |
| `test_failopen_correctness.py` **V-5 L5** | META | P0 | correctness | cross-sectional enabled 同上。 |
| `test_mtf_align_golden.py` `_assert_no_lookahead` | META | P0 | correctness | 對齊 map：`source_close <= decision`；真 BTC kline。 |
| `test_timeframe_aligner.py` | EX+META | P0 | correctness | 單元 as-of；**明文修過** row-0 lookahead。 |
| `test_feature_factory_operators.py` lag | TOL | P2 | contract | `shift(lag)` 單點；**無**「改未來 bar」MR。 |
| **章程 MR：截斷/追加未來 HF bar → 歷史特徵不變** | — | **缺口** | — | **全庫 grep 零匹配**；V-5 測的是 **縮短視窗 end**，不是 bar 級因果 MR。 |

**軸 2 小結**：L6.5 + 對齊 map + 視窗 prefix **強**；**L1–L4 層級、bar 級未來截斷 MR 缺** — 這是章程 §E1 點名待補項，應視 BLOCKING。

---

### 軸 3 — 多 TF 對齊（PIT）

| 測試資產 | Oracle | P級 | 保證 | 評語 |
|----------|--------|-----|------|------|
| `test_failopen_correctness.py` **V-6** 系列 | TOL+EX | **P0** | correctness | 手寫 as-of oracle vs `TimeframeAligner` + pipeline **byte**；真 kline；含 close_time 邊界。 |
| `test_mtf_align_golden.py` | META+TOL | **P0** | correctness | 真 kline；open_minus/close_time；CGSA×searchsorted 矩陣等價。 |
| `test_timeframe_aligner.py` | EX | P0 | correctness | 單元；ms 索引 synthetic。 |
| `test_multi_tf_golden_equivalence.py` | TOL | P1 | regression | **全 stub factory**；驗路徑等價，**非**因果 MR。 |
| `test_searchsorted_align.py` / `test_cgsa_compact_alignment.py` | TOL | P1–P2 | regression/perf | 實作等價；依賴合成或短窗。 |
| `test_cgsa_multi_tf.py` | SMK/TOL | P2 | contract | 整合 smoke 為主。 |

**軸 3 小結**：對齊 **核心邏輯已 P0**（V-6 + mtf_align_golden）；缺口在 **(a) 未來 bar MR**（同軸 2）、**(b) production preset 全欄矩陣**（現多用 minimal/fast config）。

---

### 軸 4 — L6.5 preprocessing（winsor / fracdiff / d* / cache）

| 測試資產 | Oracle | P級 | 保證 | 評語 |
|----------|--------|-----|------|------|
| `preprocessing/test_causal_winsor.py` 等 | META+TOL | **P0** | correctness | 見軸 2。 |
| `preprocessing/test_d_star_col_fingerprint.py` | EX | **P1** | correctness(contract) | strong/weak/exact fingerprint **單元**；合成 `np.linspace`。 |
| `preprocessing/test_d_star_isolation.py` | EX | P1 | correctness | symbol/TF 路徑隔離 **tmp_path 單元**。 |
| `preprocessing/test_d_star_stale_invalidation.py` 等 | EX | P1 | regression | 原子寫入/過期。 |
| `preprocessing/test_l65_native_tf_real_eth.py` | TOL | P1 | correctness | **真 ETH kline**；native TF 路徑。 |
| `golden/l65/test_l65_golden.py` | EX | P2 | regression | tier 結構/合成 baseline **存在性**；非數值 oracle。 |
| `test_winsorize_partition_opt.py` | TOL | P1 | perf+correctness | partition quantile vs reference。 |
| `test_perf_winsor_identical.py` | TOL | P2 | perf(A7) | fast vs legacy 等價。 |
| **d* 真管線 + 跨 symbol mutation probe** | — | **缺口** | — | 單元強、整合弱；章程 B1「cache key 少 symbol」**無留證 probe**。 |

**軸 4 小結**：因果 winsor/fracdiff **達 P0**；d* cache **單元 P1**，真 batch 路徑 + B1 mutation **未閉環**。

---

### 軸 5 — NaN/inf gate + warmup trim

| 測試資產 | Oracle | P級 | 保證 | 評語 |
|----------|--------|-----|------|------|
| `test_b6_warmup_trim.py` | EX+META | **P0–P1** | correctness | 16 用例：estimate/ingest/trim/insufficient/CGSA/IC-first；多數需 kline（skip）。 |
| `test_failopen_winsor.py` | META | P1 | correctness | validator winsor 因果。 |
| `test_ff_causal_golden.py` e2e | SMK | P3 | smoke | 僅 `not isinf`。 |
| `test_feature_factory_e2e.py` | SMK | P3 | smoke | inf 掃描；舊路徑。 |
| L7 streaming/codec tests | EX | P2 | contract | inf 欄位契約。 |

**軸 5 小結**：warmup **設計完整**（B6 是軸內範本）；**production L6.5+fracdiff 全開時 inf/NaN 全表掃描**仍稀疏；kline 缺失 → skip 降信心。

---

### 軸 6 — 跨 symbol 隔離（生成期）

| 測試資產 | Oracle | P級 | 保證 | 評語 |
|----------|--------|-----|------|------|
| `test_failopen_correctness.py` **V-7** | META | **P0–P1** | correctness | cross_symbol hash 不變、order permutation、cold/hot；**真 kline 短窗**。 |
| `test_cgsa_multi_symbol_isolation.py` | EX | P2 | contract | CGSA shard 路徑隔離；合成矩陣。 |
| `preprocessing/test_d_star_isolation.py` | EX | P1 | correctness | d* 檔案路徑隔離（單元）。 |
| `test_cross_symbol_features.py` | SMK | **P3** | smoke | **legacy**；合成隨機價；查命名 — **不可當隔離證據**。 |
| `test_multi_symbol_parallel.py` | TOL/SMK | P2–P3 | perf/smoke | 並行；非 byte 隔離 oracle。 |
| **雙進程 RunLease 競爭** | — | **缺口** | — | 章程 §E1 點名待補。 |

**軸 6 小結**：V-7 **實質覆蓋**生成隔離；CGSA/d* 單元補強；**並行 lease + d* 整合 mutation 缺**。

---

## 3. 高風險缺口 — 優先序

| 優先 | 缺口 | 模組 | 為何 GIGO 致命 | 建議測試（章程類別） |
|------|------|------|----------------|---------------------|
| **P0-1** | L1 原子指標無 reference | `atomic/*` + `talib_wrapper` | 單公式錯 → 全特徵錯 → IC 全錯 | **A15**：真 kline 抽樣 N 指標 × M 窗 vs TALib；finite TOL + NaN mask EXACT |
| **P0-2** | 未來 bar 因果 MR 缺席 | `feature_factory` / `multi_tf_generator` | 特徵生成偷看未來，IC 切分救不了 | **A2/A14 MR**：對固定歷史段，追加/截斷未來 HF bar → 歷史列 bitwise 不變 |
| **P0-3** | `requires_kline` 缺檔 skip | 多 golden/failopen | CI 假綠；partial confidence 漂升 full | **A17/A18**：`DATA_MANIFEST.json` + correctness job 缺 kline **FAIL** |
| **P1-1** | L4 lag 無因果 MR | `lag_processor.py` | `shift(-k)` 即前瞻 | **A14**：尾端擾動不影響 `Lag_k` 歷史；反向 shift mutation 必紅 |
| **P1-2** | d* B1 mutation 無留證 | `_d_star_cache.py` | 跨 symbol 污染靜默 | **B1 probe**：patch 去掉 symbol in key → `test_d_star_isolation` / V-7 必紅 |
| **P1-3** | production preset G-NEW | `generate_features` 7-layer | minimal/fast 遮掉 L5/fracdiff 組合 | **A8 G-NEW**：真 kline 縮窗 production-like config + TOL golden |
| **P2-1** | RunLease 雙進程 | `run_locks.py` | 雙寫/孤兒 | **A9/A13** 競爭測試 |
| **P2-2** | Polars vs pandas 全層 | `polars_adapter` | 分支漂移 | **A7/A15** 等價（已有 phase4 片段） |

---

## 4. Claude 草稿可能漏掉的 FF 風險軸

1. **Legacy vs 主路徑混淆**：`FeatureExtractor` / `test_cross_symbol_features` 仍掛在 tests/，易誤判覆蓋；主路徑是 `feature_factory.py` 7-layer + CGSA。
2. **IC-first / L7 raw streaming 順序**：`test_ic_first_pipeline.py`、`test_l7_raw_streaming.py` — 消費者閘與 raw metadata；錯序可讓 IC 讀到未 trim 暖機區（與軸 5 交界）。
3. **L5 cross-sectional 參考標的**：V-5 L5 只測 prefix；未測「參考 symbol 未來資料」是否污染（cut2 前風險）。
4. **config_hash / feature_schema_hash 漂移**：`test_feature_library_config_hash.py` 等測契約；與 d* fingerprint 交互未在真 run 驗證。
5. **epoch 秒契約**：`test_v2_timestamp_golden.py` 偏 CGSA manifest mock；L0 真 ingestion 多 TF 仍靠間接證據（mtf golden 用秒）。
6. **fail-open 語義**：failopen 系列測 **降級不崩**；與 **correctness** 分開 — 勿把 V-3 frozen baseline（P1 regression）當 P0。
7. **章程基礎設施欠帳**：`pytest.ini` marker 未建、`DATA_MANIFEST` 不存在 — 影響所有軸信心標記。

---

## 5. Mutation probe（§B1）現況 — FF

| Probe 類型 | 狀態 | 證據 |
|------------|------|------|
| 因果擾動（尾端改值歷史不變） | **有** | `test_causal_winsor.py`、`test_ff_causal_golden.py` |
| 對齊 lookahead 反例 | **有（單元）** | `test_before_baseline_shows_lookahead`、`test_timeframe_aligner` |
| cache key 少 symbol | **無留證** | 單元測試存在，未見 patch+fail 紀錄 |
| train/test 顛倒 | N/A FF | IC 層 |
| 故意 `-shift` lag | **無** | — |

→ 聲稱 P0 的 FF 測試，多數 **缺 B1 留證**；依章程只能標 `partial confidence`。

---

## 6. 建議深稽範圍（scoping 結論）

| 區塊 | 深稽？ | 深度 |
|------|--------|------|
| L1 atomic | **必** | 全量抽樣 A15 + 優先高 fan-out 指標 |
| MTF align | 收斂即可 | 補 P0-2 MR + close_time production 欄位 |
| L6.5 causal | 收斂即可 | 補 d* B1 + 真 batch |
| L3 rolling | 低 | 已 P0 |
| Warmup/B6 | 低 | 補 kline FAIL 非 skip |
| Cross-symbol | 中 | V-7 保留 + lease + d* 整合 |
| failopen/frozen | **勿升級為 correctness** | 維持 P1 regression |

**一句話**：FF **不是沒測**，也 **不能算穩** — 對齊與 L6.5 因果有真 kline P0 資產；**上游 L1 計算與 bar 級因果 MR 是 IC GIGO 的未關門**。

---

## 7. 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - 實讀 charter §0/§E1、Claude 草稿、tf_aligner/lag_processor/_d_star_cache 介面
  - 抽查 failopen V-5/V-6/V-7、mtf_align_golden、causal_winsor、numba_rolling、cross_symbol_features 全文/摘要
  - grep「截斷/未來 bar/future bar」MR → 0 匹配
  - DATA_MANIFEST.json → 不存在
TESTS_RUN: none（read-only scoping 稽核）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅新增本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_NOT_UPDATED: 執行合約 — 不重寫根 HANDOFF.md
```

STATUS: DONE
