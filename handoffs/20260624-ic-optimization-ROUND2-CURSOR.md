# IC-Analysis 架構優化 — Round 2 互審詰問

> READ-ONLY 審查；已對照三份 Round-1 方案與 repo 關鍵路徑。以下供 Round 3 收斂。

---

## 1. 收斂點（三方已同意）

| # | 共識主張 | 證據 |
|---|---------|------|
| C1 | **根因是 stage0 全量物化**；430K×20K 在任何 tier 都不可走現行 pandas 全矩陣路徑 | 三份 §0/§1；`ic_filter_orchestrator.py:992` `features[:]`；`1612` |
| C2 | **IC 對每欄獨立** → 欄投影 + 分塊串流在數學上可行；`FeatureReader.load_columns_v2` / L7 group 讀取是基礎設施 | Claude §0；Codex §1；Cursor §1.2；`feature_reader.py:115–160` |
| C3 | **rolling_ic 全量序列不可保留**（430K 欄）；只保留 per-feature 聚合（ICIR/IC mean/std）+ top-N 事後重算 | 三份 stage4；`ic_engine.py:268–302` 現況 dict-of-lists |
| C4 | **redundancy / centrality / orthogonalize 必須 candidate-only**，不得對 430K 做 O(n²)/O(n³) | 三份 stage6 + deep 10 |
| C5 | **staged screening**：廉價全量 IC 粗篩 → 僅 survivors 做 decay/grouped/deep | Claude §1.2；Codex `CandidateSet`；Cursor 5a/5b |
| C6 | **cross-sectional 禁止 `pd.concat` 多 symbol 全 panel** | Codex §Cross-sectional；Cursor §Cross-Sectional；`ic_analysis_service.py:130–154` |
| C7 | **P0 止血**：GroupedConfig crash、timestamp ms/s、decay 14K warnings、`asyncio.to_thread` | 三份 epic E0/IC-CRASH |
| C8 | **幽靈 `feature_filter`**：API 有、核心 `ICConfig` 無、orchestrator 零處理 | Codex §4；Cursor §API；`ic_models.py:15,71` → `ic_config_schema.py` 無 `feature_filter` → `ic_analysis_service.py:967–970` |
| C9 | **NaN gate 0.9 不弱化**；chunk 內逐批驗證 | 三份 §3；`ic_filter_orchestrator.py:1348–1350` |
| C10 | **resume/fingerprint 防 stale cache**；per-symbol 隔離 key 含 `config_hash` | 三份 §1.3/§3 |
| C11 | **輸出最小化**：430K summary 落 Parquet artifact；API/WS 只返 top-N + counts | 三份 §4/§5 |
| C12 | **Golden 必做**：串流 vs 全載 IC 等價、timestamp 四路徑、GroupedConfig 不崩潰 | 三份 §5 |

---

## 2. 分歧點（逐項裁決）

### D1 — 每 tier `chunk_cols` 數字

| Agent | 8GB | 16GB | 24GB | 32GB |
|-------|-----|------|------|------|
| Claude | **2,000** | ~4K（未列表） | — | **16,000** |
| Codex | **512** | 1,024 | 2,048 | 4,096 |
| Cursor | **2,048** | 4,096 | 8,192 | 12,288 |

**記憶體模型差異**：
- Codex 含 rank+rolling 安全預估 + 35%/60% RAM 上限（Codex §1 表）。
- Cursor 峰值只算 `chunk×rows×4×2.5`（Cursor §1.2 表 ≈390MB@8GB），**未計入** `compute_rolling_ic` 的 ranked matrix（`ic_engine.py:289–291`）與 `_rolling_corr_matrix` 輸出（`:298–301`）。
- 實算：2048 欄 × 20K rank float64 ≈ **327MB**；rolling corr `(T_win×2048)` ≈ **327MB/window**；3 windows ≈ **1.3GB** chunk 內 — 8GB 仍可行，但非 390MB。

**裁決**：**採 Codex tier 表為初始預設（512@8GB）**，由 `ICMemoryGovernor` 在 **禁止 chunk 內存 rolling dict** 的前提下 microbench 上調。Claude/Cursor 的 2K@8GB 可作 profiling 後上限，不可作 day-1 預設。

**證據**：Codex §1 表；Cursor §1.2 表 vs `ic_engine.py:288–301`；Claude §1.1。

---

### D2 — Staged screening 切點與是否漏交互效應

| Agent | 粗篩時點 | 粗篩依據 | 深析觸發 |
|-------|---------|---------|---------|
| Claude | **Stage A**（全特徵串流） | coverage/variance/dead + `\|IC\|/\|ICIR\|` | Stage B 僅 survivors |
| Codex | **Stage5 後** `CandidateSet` | FDR/p-value/ICIR 全量 metric table | Stage6/deep |
| Cursor | **5a**（ic_scores only）→ **5b**（passed 欄投影） | 5a: FDR/threshold；5b: monotonicity/coverage/turnover | stage6 ≤200 欄 |

**交互效應風險**：
- 任何 **IC-only 前置截斷** 會漏「單欄弱、組合強」因子（Claude §7 Q2 自承）。
- Codex/Cursor 的 redundancy truncation 會漏未入 candidate 的共線關係（Codex §5 明示）。

**裁決**：
1. **5a/5b 切分（Cursor）最乾淨**：FDR 只需 O(C) metric table（`ic_filter_orchestrator.py:1187–1191`），monotonicity 需欄值（`:1173–1175`）→ 5b 投影 K 欄。
2. Stage A 只做 **零/低成本 gate**（NaN/constant/coverage/metadata filter），**不用 IC 門檻硬砍** 進正式 gate。
3. 交互效應：**不納入 P0 正式 gate**；若要做，標 `exploratory_pairwise` + 明確 candidate 上限，不可 silent default。

**證據**：Claude §1.2, §7.2；Codex §2 Stage5/6, §5；Cursor §Stage5 表；`ic_filter_orchestrator.py:1173–1191`。

---

### D3 — Cross-sectional 架構

| Agent | 方案 | 100 symbol 峰值估算 |
|-------|------|---------------------|
| Claude | 對齊時間軸的 **survivors 子集**（未給公式） | 未量化 |
| Codex | **timestamp-major 或 feature-chunk-major**；8GB 再拆 subchunk 64–128 欄或 row block 1K | 100×20K×512 = **4.1GB raw**；subchunk 後 **205MB** |
| Cursor | **long panel 串流**；每 timestamp 載 `N_sym × C_survivor`，C_survivor≤500 | 100×500×8B×20K 若物化仍大；按 timestamp 切片才安全 |

**裁決**：**Codex feature-chunk-major × Cursor per-symbol survivor 粗篩（≤500）混合**：
```
for chunk_cols in manifest:
  for symbol in symbols:
    X = load_columns_v2(symbol, chunk_cols)  # 20K rows
  for t_block in row_blocks:
    rank_corr_across_symbols(X[t_block], labels[t_block])
```
8GB：**512 欄 × 100 sym × 1000 rows × 4B ≈ 205MB**（Codex §Cross-sectional）。**禁止** Cursor 式「先 per-symbol IC 粗筛至 500 再 cross-sectional」作**唯一**正式路徑（Codex §7 自警 + Cursor §1.5）— 可作 optional fast path。

**證據**：Claude §1.3；Codex §Cross-sectional；Cursor §1.5, §Cross-Sectional；`ic_analysis_service.py:143–154`。

---

### D4 — Redundancy / deep 候選上限

| Agent | corr 上限 | VIF/orthogonalize | centrality |
|-------|-----------|-------------------|------------|
| Claude | survivors（**無硬數字**） | survivors | survivors |
| Codex | **500–3,000**（tier 分級） | 8GB k≤300；32GB k≤1,000 | k 500–2,000 |
| Cursor | **200**（沿用 schema） | **n≤100@8GB / ≤200@32GB** | C≤50 |

**裁決**：
- **corr：200**（已有 `ic_config_schema.py:155` `max_features_for_correlation: int = 200`）— 320KB corr matrix，三方應統一引用此欄位，Codex 3000 **拒絕**（32GB 上 O(n³) VIF 仍危險）。
- **VIF：n≤100@8GB, ≤200@32GB**（Cursor）。
- **orthogonalize/PCA：C≤30@8GB, ≤50@32GB**（Cursor deep 表更保守，優於 Codex 1000）。
- 超截斷必標 `redundancy_input_truncated=true`（Codex §5）。

**證據**：`ic_config_schema.py:155`；Codex §Stage6, §Deep；Cursor §Stage6, §Deep 表。

---

### D5 — Streaming winsor/zscore：兩遍 vs t-digest vs 跳過

| Agent | 方案 |
|-------|------|
| Claude | 兩遍 **或** t-digest（開放問題 §7.4） |
| Codex | 逐欄即可；跨欄統計 → `requires_candidate_set` |
| Cursor | 兩遍 p1/p99；**或消費 L7 processed**（FF 已做則 skip + byte-faithful 驗證） |

**裁決**：**優先 L7 processed artifact**（Cursor §Stage1）— IC 不應重複 winsorize 除非 golden 證明 FF 未做。若必須 IC 側做：**train-window 兩遍**（Cursor §3 PIT preprocessing），t-digest 僅作 exploratory。Claude 的 t-digest 預設 **否**（準則 ③ 無 golden 前有損風險）。

**證據**：Claude §2 stage1, §7.4；Codex §Stage1；Cursor §Stage1, §3, §7.2。

---

### D6 — 是否重用 `compute_ic_from_l7_raw`

| Agent | 立場 |
|-------|------|
| Claude | 提 `load_columns_v2`，未強調既有函式 |
| Codex | 新建 `FeatureMatrixSource` + chunk engine |
| Cursor | **主路必須收斂至** `compute_ic_from_l7_raw` 模式 |

**裁決**：**採 Cursor** — 已有 group 串流 + fingerprint + cache hit（`ic_engine.py:104–266`），`analyze()` 主路（`:209` via materialize）應 **extend 而非 parallel rewrite**。Codex 的 `FeatureMatrixSource` 可作 orchestrator 介面名，實作對齊 L7 raw path。

**證據**：Cursor §0, §Stage4a；`ic_engine.py:104–266`；`ic_analysis_service.py:189–216` 仍走 materialize+HDF5。

---

### D7 — `max_features=30` 語義

| Agent | 方案 |
|-------|------|
| Claude | Stage A metadata filter + 審計 log |
| Codex | 改名 `preview_limit`；**預設分析全部** |
| Cursor | metadata 先濾；`max_features` **stage5a 後** top-N；硬 cap 需 UI 明示 |

**裁決**：**Codex 命名 + Cursor 時點**：
- `max_features` → API 層改名 `preview_limit`（或 report-only）。
- metadata include/exclude/pattern：**stage0 catalog**（零成本）。
- **禁止 stage0 截斷**（Cursor §API 211–214）。
- 前端 `icAnalysisStore.ts:187` `max_features: 30` 目前誤導（三份一致）。

**證據**：Codex §4 幽靈 feature_filter；Cursor §API；`frontend/src/store/icAnalysisStore.ts:187`；`ic_config_schema.py` 無 `feature_filter`。

---

### D8 — Rolling ICIR：Welford vs prefix sums vs 全序列

| Agent | 方案 |
|-------|------|
| Claude | 串流摘要，未指定算法 |
| Codex | prefix sums / rolling window sums |
| Cursor | **Welford** 串流；top-N 才重算完整序列 |

**裁決**：**Cursor Welford + Codex prefix sums 二選一需 golden 定案**；Round 3 前用 20 欄×5K 列 fixture 驗 `icir` mean/std/hit_rate 與現行 `compute_icir`（`ic_engine.py:304–328`）一致。stride>1、window 邊界（Cursor §7.3）**必測**。

**證據**：Cursor §1.2, §4.1, §7.3；Codex §4；`ic_engine.py:304–328`。

---

### D9 — Decay / grouped 範圍

| Agent | decay | grouped |
|-------|-------|---------|
| Claude | survivors only；R2 低 **不 early-skip 改 metadata** | survivors + 修契約 |
| Codex | chunk 內多 horizon 向量化 | row mask × chunk |
| Cursor | **ICIR top-500**；低 R² 不 fit | survivors ≤500 |

**裁決**：
- decay：**top-500**（Cursor，可配置）— 430K 全算不可行（`ic_engine.py:342–347` horizon×全欄）。
- grouped：**survivors ≤500** + 修 `model_dump()`（三份 P0）。
- R2 低：**metadata 標記，不 silent skip**（Claude §2 decay 行 — 優於 Cursor「低 R² 不 fit」若后者意味丟欄位）。

**證據**：Claude §2；Cursor §4b/4c, §5 表；`ic_filter_orchestrator.py:1139` 傳 `GroupedConfig` 物件 → `ic_engine.py:377` `.get()` **必崩**。

---

### D10 — Epic 優先序命名

| Claude | Codex | Cursor |
|--------|-------|--------|
| IC-STREAM P0 | Epic C+D P0 | E1 Streaming P0 |
| IC-SCREEN P0 | Epic B | E2 |
| IC-CRASH P0 | Epic A | E0 |
| IC-UX-ERR P0 | Epic A | E0 |
| IC-CORRECT P1 | 散落 A/G | E0 部分 |

**裁決**：統一為 **E0→E1→E2→E3→E4→E5→E6**（Cursor §6 最可執行）；Claude 的 IC-STREAM/IC-SCREEN 對應 E1/E2。

---

## 3. 三方都漏的（共同盲點）

| # | 盲點 | 嚴重度 | 證據 |
|---|------|--------|------|
| B1 | **`feature_library.load()` 仍全欄投影** → materialize 前已 34GB+ | **P0** | `feature_library.py:129–146` `load_columns_v2(..., columns=ALL)` → `_materialize_features_for_ic:1123–1136` |
| B2 | **Stage0 metadata 校驗 O(C) Python loop** 430K 次，串流前即卡死 | **P1** | `ic_filter_orchestrator.py:1337–1346` |
| B3 | **`by_volatility: true` 幽靈旗標** — schema 預設 true 但 `compute_grouped_ic` 無分支 | **P0 正確性** | `ic_config_schema.py:80` vs `ic_engine.py:399–417`（僅 `by_regime` 含 high_vol/low_vol `:1075–1076`） |
| B4 | **`factor_exposure` positions bug**：`len(factor_values)` = **列數**非特徵數 | **P1 正確性** | `ic_filter_orchestrator.py:843` `1.0 / max(1, len(factor_values))` |
| B5 | **`start_analysis` 仍同步阻塞 event loop**；`to_thread` 只在 `start_full_analysis` | **P0 UX** | `ic_analysis_service.py:209` vs `:670`；`routes/ic_analysis.py:38` 主 UI 路徑 |
| B6 | **主 pipeline 零 `selection_window`/`split_id`** — PIT/train-val-test 只在 `compute_ic_from_l7_raw` 存在 | **P0 洩漏風險** | `ic_engine.py:446–454` vs orchestrator grep 0 matches |
| B7 | **HDF5 materialize 寫 timestamp 為秒**；`_get_time_index` numeric 假設 **ms** | **P0** | `_write_features_h5:1162` `// 10**9` vs `ic_engine.py:1025` `unit="ms"` |
| B8 | **`_ic_cache` 跑完仍存全量 `features_df` + `rolling_ic`** | **P1 OOM** | `ic_filter_orchestrator.py:1300–1311` |
| B9 | **`_tasks` 純記憶體** — server restart 後 resume 失效 | **P1** | `ic_analysis_service.py:40`；Cursor §7.10 僅 Cursor 提 |
| B10 | **cross-sectional label 對齊** — `_append_cross_sectional_labels` 無三方審計 | **P1 洩漏** | `ic_analysis_service.py:148–152` |
| B11 | **FF 430K 欄根因**（indicator 笛卡爾積）— 僅 Cursor 提，無治理方案 | **產品** | Cursor §7.5 |
| B12 | **Cursor rolling 記憶體 "~64 TB" 算錯** — 實為 **~64 GB/window** | 文件品質 | 430K×19940×8B ≈ 68.6GB（Cursor §1.1 表） |
| B13 | **orphan run 無 `row_index`** fallback 策略未定 | **P1** | `feature_reader.py:171–182` `return None` |
| B14 | **disk spill retention** — 430K×N symbol parquet 長期用量 | **P2** | 無人給 retention policy |
| B15 | **deep 模組 tier preset 與 RAM 掛鉤** — schema 有 `foundation/intermediate/advanced` 但未與 chunk governor 聯動 | **P2** | `ic_config_schema.py:284–287` |

---

## 4. 正確性紅線爭議

### 4.1 可接受（需 disclosure，非 default 語義變更）

| 優化 | 語義 | 必要 golden |
|------|------|------------|
| 欄 chunk exact IC/Spearman | **不變** | 小矩陣 streaming ≡ full path |
| metric table spill | **不變** | passed 集合一致 |
| decay top-500 only | **變**（非 top-500 無 decay 欄） | report `decay_scope` |
| grouped survivors only | **變** | report `grouped_scope` |
| redundancy top-200 | **變**（相對全量 passed） | `redundancy_input_truncated` |
| rolling 序列 top-N retain | **變**（deep trend/centrality 範圍） | centrality k≤50 子集 golden |

### 4.2 不可接受（紅線）

| 做法 | 原因 |
|------|------|
| stage0 `max_features=30` 靜默截斷 | 漏因子 + UI 誤導（`icAnalysisStore.ts:187`） |
| approximate corr sketch 作 **default gate** | Codex §5 明示僅 exploratory |
| 弱化 NaN/inf/float16 gate | 準則 ③ |
| early-skip 未評估 feature 標為 failed | Codex §3 `not_evaluated` 規則 |
| cross-symbol 共用 winsor/zscore 統計 | 準則 ③ 跨 symbol 污染 |
| test set 參與 FDR/redundancy 排序 | Codex §3 Train/val/test |
| `by_volatility` 靜默 no-op | schema 預設 true 但無實作 — **fail-closed 或實作** |
| IC 側 winsorize 用全樣本含 test | 洩漏；必須 train-window only |

### 4.3 必須 golden 的清单（Round 3 前）

1. **`test_ic_streaming_equivalence`** — 10–100 欄，full vs chunk，atol=1e-10  
2. **`test_grouped_ic_groupedconfig`** — `model_dump()` 路徑  
3. **`test_timestamp_unit_inference`** — 秒/ms/DatetimeIndex/HDF5-ingest 四路徑（B7）  
4. **`test_welford_icir_equivalence`** — stride/window 邊界  
5. **`test_feature_filter_not_stage0_truncate`**  
6. **`test_cross_symbol_isolation`** — cache key + fingerprint  
7. **`test_resume_no_stale_chunk`**  
8. **真實 kline golden**（準則 ③⑥）— 合成只測 OOM 行為，不簽核數值  
9. **`test_selection_window_pit`** — 主 orchestrator 接線後（B6）

---

## 5. 收斂建議（Round 3 方案骨架 + Epic 優先序）

### 5.1 目標架構（一句話）

**L7 group 串流 IC（extend `compute_ic_from_l7_raw`）→ O(C) metric spill → 5b 欄投影 → ≤200 redundancy → top-N report**；任何時刻峰值 ≤ tier 35% RAM。

### 5.2 模組契約

```
Manifest/FeatureMatrixSource
  → RowMaskPlan (event_filter, 未來: selection_window)
  → ChunkICWorker (group 級, chunk_cols=tier表)
      → ic_scores.parquet (append-only)
      → checkpoint.json (stage, group_id, fingerprint)
  → Stage5a: FDR/threshold on parquet only
  → Stage5b: load_columns_v2(passed[:K], K≤2000)
  → Stage6: redundancy ≤200, VIF ≤100@8GB
  → Stage7: API top_n=30 + artifact URIs
  → Deep: only stage6 filtered_df cols ≤200
```

### 5.3 Epic 優先序（合併三版）

| 順序 | Epic | 內容 | 準則 |
|------|------|------|------|
| **E0** | Hotfix | `GroupedConfig.model_dump()`；timestamp infer；`by_volatility` fail-closed/實作；decay warning 聚合；**`start_analysis` → `to_thread`**；factor_exposure positions 修 | ①③④ |
| **E1** | Streaming Core | 跳過 `_materialize_features_for_ic` 全載；orchestrator 收斂 `compute_ic_from_l7_raw`；Welford/prefix ICIR；`_ic_cache` 瘦身；ICMemoryGovernor（**初始 chunk= Codex 表**） | ①②④ |
| **E2** | Contract | `feature_filter`/`preview_limit`；metadata catalog filter；5a/5b 切分；stage0 metadata 校驗改 manifest/sampling | ③⑤ |
| **E3** | Regime/Decay | decay top-500；grouped survivors≤500；low R² metadata-only | ④⑥ |
| **E4** | Cross-Symbol | 移除 concat；feature-chunk × symbol 串流；survivor 可選 fast path | ②③⑥ |
| **E5** | Deep Caps | corr≤200, VIF≤100, PCA≤30@8GB；truncation disclosure | ①④⑥ |
| **E6** | Golden+Bench | 上述 golden + per-tier CI OOM gate + 430K synthetic stress | ③⑥ |

### 5.4 Round 3 仍須議決（未解）

| ID | 問題 | 建議 Round 3 產出 |
|----|------|-------------------|
| R3-1 | Welford vs prefix sums — 哪個作 ICIR 標準實作 | 實測 + golden 二選一 |
| R3-2 | L7 processed vs IC 兩遍 winsorize — 是否 skip stage1 | byte-faithful 抽樣比對 FF artifact |
| R3-3 | chunk_cols 上調節奏 — 固定表 vs runtime governor | microbench script + tier CI |
| R3-4 | cross-sectional 是否允許 per-symbol pre-screen 作 fast path | 產品決策 + 文件 |
| R3-5 | `selection_window` 接入主 orchestrator 的 split 語義 | spec + golden |
| R3-6 | orphan `row_index=None` fallback | fail-closed vs 讀 parquet index |
| R3-7 | 430K 欄 FF 治理（hard cap vs 使用者確認） | 與 FF 委員會聯合 |
| R3-8 | spill retention / disk budget | 配置 + 清理 job |
| R3-9 | persistent task registry（API restart resume） | 設計 sketch |
| R3-10 | HDF5 legacy path — 何時 fail-closed 要求 L7 V2 | tier×C×R 公式 gate |

### 5.5 對三份的自詰（誠實漏洞）

**Claude**：chunk 2K@8GB 缺 rolling 峰值核算；Stage A `\|ICIR\|` 粗篩與「不漏交互」矛盾未解；epic 未列 `_materialize` 短路。

**Codex**：redundancy 500–3000 與既有 schema 200 衝突且 O(n³) 危險；最完整但 **未強調** `compute_ic_from_l7_raw` 可直接 adopt；READ-ONLY 聲明正確。

**Cursor（本 agent Round-1）**：rolling **64 TB 應為 ~64 GB/window**；memory 表未含 rank/rolling；`chunk_cols=2048@8GB` 偏 aggressive 缺 Codex 式 safety cap；**優勢**是 5a/5b、L7 reuse、Welford、epic 順序 — 應作 Round 3 骨架基底，數字與記憶體模型需修正。

---

**Round 3 開場建議**：以 Cursor epic 骨架 + Codex tier 數字 + Claude staged screening 命名開會；第一個投票項：**E0 範圍是否納入 B3/B4/B6/B7**（四方盲點，非原 E0 範圍，但皆 P0 正確性）。
