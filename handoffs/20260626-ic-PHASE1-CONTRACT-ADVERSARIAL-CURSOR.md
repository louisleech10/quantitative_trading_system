# IC Phase 1 1-contract — SPEC Adversarial Review（Composer 2.5 / Cursor）

> 審查對象：`docs/IC_PHASE1_CONTRACT_SPEC.md`  
> 對照：`handoffs/20260625-ic-PHASE1-CONTRACT-MANIFEST.md`、`handoffs/20260625-ic-PHASE1-BRIEF.md`、`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`  
> 範本：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13  
> STRICTNESS：MAXIMUM  
> 獨立審查；未讀同輪 Codex 報告全文。

---

## Verdict：需修補後派工

契約優先方向與 [C-3] 跨 symbol 紅線方向正確，但 SPEC 含**可證偽錯誤前提**（WalkForward 無 `split()`）、**(d) 紅線未覆蓋單 symbol 內時間不連續**、§G Golden 關鍵參數外推至 TODO、以及 Task 3.x artifact/API 契約空殼。修補前派工高機率實作卡死或假綠。

---

## Findings（挑戰前提置頂）

### [BLOCKING] High — §A 把「兩工具皆有 split()」當已驗證事實，與程式不符

**證據**：§A L18「兩工具切分用 positional…`CombinatorialPurgedCV.split()`…」；Task 1.4 L69–70「`create_walk_forward_validator`/`create_combinatorial_purged_cv` 的 `split()`」。  
**實測**：`grep "def split" momentum/Analysis/model_validation/walk_forward_validator.py` → **0**；僅 `combinatorial_purged_cv.py:41` 有 `split()`。`WalkForwardValidator` 對外是 `validate(model_factory, X, y, feature_names)`，內部 `_generate_rolling_splits()` 回傳 index range tuples，非 sklearn-style `split()` iterator。

**會怎麼失敗**：Agent 依 Task 1.4 寫 adapter「逐 symbol 呼叫其 split()」→ WalkForward 路徑無法編譯或需擅自改 `walk_forward_validator.py`（違反 Task 1.4「不可做」）。

**修法**：§A 改為「CPCV 有 `split()`；WF 僅有 `_generate_rolling_splits` / `validate`」。Task 1.4 明訂 WF adapter 策略：① 抽出/包裝 `_generate_rolling_splits` 為契約級 `iter_split_indices(n_samples)`（允許改 WF **或** ② Phase 1 僅 adapter CPCV，WF 標 Phase 1a 依賴）。不可再寫兩者皆有 `split()`。

---

### [BLOCKING] High — [C-3] per-symbol 只解跨 symbol；單 symbol 內 positional purge 在 gap/缺 bar 時仍可洩漏（使用者點名 Q-4 / (d)）

**證據**：§A L18「purge/embargo 用連續切片 `mask[purge_start:purge_end]`」（`combinatorial_purged_cv.py:191–195`）；Task 1.3 驗證僅「BTC 尾接 ETH 頭」跨幣種反例 + symbol 純度；Manifest [C-1] 要求「index/**timestamp-based，非僅 positional**」，但 adapter 只包 positional `split()`。  
**業界/地圖**：`handoffs/ic-map-trail/20260624-ic-map-STAGE3-CODEX.md` 已記「purge_gap 是固定 row count，不保證匹配 horizon/timeframe/event span」。

**會怎麼失敗**：真實 `kline_cache.h5` 若有缺 bar、維護停機、或 `dropna` 後 index 非等距，`purge_gap=5` 列 ≠ 5 個交易日/5×1h bar；train 末段 label horizon 重疊仍進 test → **單 symbol 內 lookahead**。per-symbol 包裝無法修復。

**修法**：契約層新增（Phase 1 至少簽名 + 測試骨架）：`TimestampContinuitySpec` 或 `SplitPlan.time_bounds` 強制附帶 `expected_freq` + `validate_monotonic_timestamps(ts)`；purge/embargo 契約欄位註明 **semantic=rows 非 calendar** 並在 1a 改為 time-based purge。§V 邊界目錄勾「亂序 timestamp」但未勾「**缺 bar / 非等距 index**」→ 補可證偽測試：合成缺 3 bar 的 BTC 1h 子集，assert positional purge 與 calendar purge 不等價時 **fail-closed**（raise 或 SkippedResult），不得靜默通過 [C-3]。

---

### [MAJOR] High — §A「30 測試驗 purge/embargo 正確」過度陳述；全為 synthetic，未碰真實 kline / gap

**證據**：§A L17「30 個既有測試全 PASS（含…purge/embargo 正確性）」。  
**實測**：`tests/momentum/Analysis/model_validation/test_combinatorial_purged_cv.py` 15 個 + `test_walk_forward_validator.py` 15 個 = 30 ✓；但**全部**依 `synthetic_binary_data` fixture，無 timestamp、無缺 bar、無 `kline_cache.h5`。

**會怎麼失敗**：委員會/三方簽核以「既有 30 測試」當 (d) 已證 → 在真實 IC 路徑上洩漏仍可能發生，與三方簽核鐵律 #2 精神衝突。

**修法**：§A 改為「30 測試覆蓋 ML 孤島 **synthetic** split 不重叠/邊界；**不含**真實 kline 時間軸 purge」。Phase 1 新增測試義務寫進 §G/§V，不可引用既有 30 測試代替 [C-3]/gap 測試。

---

### [MAJOR] High — [Q-1] 預設 HDF5 與 codebase 方向、FF-explorer 需求、跨 tier 載入不一致

**證據**：Task 3.1 L99「writer 寫 HDF5，預設格式見 [Q-1]」；使用者要求 artifact「全表可篩/排序（FF-explorer 式）」。  
**對照 codebase**：`momentum/FeatureEngineering/feature_reader.py` 標「V7 unified…**Parquet-only, no HDF5**」；`ic_engine.py` L7 raw 路徑用 **per-group parquet**；`ic_filter_orchestrator.py` 讀 filtered **HDF5** 是舊路徑。

**會怎麼失敗**：430K features × horizons 的 columnar filter/sort：HDF5 需整表或整 group 載入 → **8GB tier OOM**；Parquet + predicate pushdown 為業界慣例（quant research artifact 多 parquet/arrow）。與 Phase 3 串流 parquet 脊骨不一致 → 二次遷移。

**修法**：[Q-1] 決策寫死前補 §P 權衡表：檔案大小（壓縮比）、篩選延遲（cold read 10K/100K/430K rows）、8GB/32GB peak RSS、與 `feature_reader` 對齊。建議預設 **Parquet**（或 Arrow IPC）+ schema_version；若堅持 HDF5，Task 3.1 必須寫 chunk 佈局、`read(path, filters)` 的 **不載全表** 保證與 tier RAM 上限。

---

### [MAJOR] Medium — [Q-2] 同 endpoint + `schema_version` 未規範 flag-off 語義與 TS 消費者分支成本

**證據**：Task 3.2 L106–107「同 endpoint 加 `schema_version`+`artifact_uri`」；§R `ic_response_v2` 預設 off；`frontend/src/lib/types.ts` 多處可選 `schema_version`。  
**缺口**：無「flag off 時 response **byte-for-byte** 與 baseline 相同」的可執行斷言；無 `ICResultV2Response` 與現有 `get_result()` dict 的欄位對照表。

**會怎麼失敗**：前端 `useICAnalysis` / `page.tsx` 假設巢狀 JSON 全在 payload；加 v2 後即使 flag off，`_to_json_compatible` 或 Pydantic 路徑若多序列化 `eval_status` 等欄 → **§G Golden 靜默失敗**。新 endpoint `/v2/` 雖多路由，但型別單一、較不易誤接。

**修法**：Task 3.2 增「相容矩陣」表：flag off / on / 缺 artifact 三態預期 JSON；驗證必含 `ic_response_v2=false` 時與 `baseline_btc_1h.json` 的 **deep equality**（非僅「舊欄仍存在」）。記錄 `ic_response_v2` 設定位置（`api/core/config.py` 現無此 key）。

---

### [MAJOR] Medium — [Q-3] 漸進遷移未規範雙路徑一致性與 artifact 生命週期

**證據**：Task 3.1「不刪舊 JSON」；Task 3.2「保留舊欄」；無 artifact 與 in-memory `task_info["result"]` 同步策略。  
**會怎麼失敗**：v2 開啟後 top-N 來自 artifact 篩選、舊欄仍來自 memory JSON → **同一 task 兩套數值**；retry/resume 後 artifact 孤兒檔。漸進期最長多久、誰為 source of truth 未寫 → Agent 自行假設。

**修法**：§C 或 Task 3.2 加「single source of truth」：v2 on 時 summary 必須由 artifact 衍生（或明訂允許不一致並標 deprecated）；artifact 路徑命名含 `task_id`+`config_hash`+`schema_version`；刪 task 時 artifact GC 策略（可 Phase 1 標 N/A 但須寫清風險）。

---

### [MAJOR] High — §G Golden 關鍵 `config_hash` 外推至 TODO，凍結流程不可執行

**證據**：§G L40「**BTC/1h, config_hash 寫死於 TODO**」；Task 4.1 依賴該 baseline。TODO 檔「待生成」。  
**會怎麼失敗**：動工前無法跑 §G 要求之 baseline；實作者自行選 config_hash → Golden 不可比、三方簽核無錨點。

**修法**：凍結前在 SPEC §G 寫死 `config_hash`（或明確「用 feature_library 最新 BTC 1h run」+ 指紋命令）；附一條可複製的 baseline 生成命令與預期 sha256 占位流程。

---

### [MAJOR] High — §G「byte 級不變」與 Task 2.2 / 3.2 改共用 DTO、service 路徑張力

**證據**：§G L42「本刀只加契約 surface，不改計算 → 必須 byte 級一致」；Task 2.2 `ICResult` 加 `eval_status`；Task 3.2 改 `get_result()`；`get_result` 現走 `result` dict → `_to_json_compatible`（`ic_analysis_service.py:275–288`）。  
**會怎麼失敗**：若任何路徑把 `ICResult` dataclass 納入 `result` 或 `asdict` 多一欄；或 v2 分支改 normalization 順序 → Golden IC 數值或 JSON shape 漂移。Golden 僅 **BTC/1h 單 symbol longitudinal**，不覆蓋 cross_sectional（`ic_filter_orchestrator.analyze_cross_sectional`）與多 symbol 堆疊。

**修法**：§G 限定 Golden 範圍（僅 flag off + 單 symbol longitudinal + 固定 ICConfig）；Task 2.2 驗證加「既有 `to_dict`/JSON 路徑無新鍵」。cross_sectional 標「本刀 Golden 不覆蓋，C-3 不適用語義待 1a 補」。

---

### [MAJOR] Medium — [C-10] Artifact 讀取端點契約空殼（§2 獵空殼）

**證據**：Task 3.2 L107「新增讀 artifact 的篩選端點契約（query: sort_by/filter/page）」— 無 route path、無 Pydantic model 名、無 `api/routes/` 檔案、無分頁上限與 auth。Manifest [C-10] 要求「前端/後端如何按需讀」。

**會怎麼失敗**：Agent 各寫各的 query 語義；前端 FF-explorer 式篩選無法對接；大 page size → OOM。

**修法**：補最小契約：`GET /api/v1/ic-analysis/tasks/{task_id}/artifact` + `ICArtifactQueryParams` 欄位表（sort_by enum、filter 運算子、page_size cap 按 tier）；或明訂「Phase 1 僅 writer/read Python API，HTTP 端點 Phase 3」並降 Manifest [C-10] scope。

---

### [MAJOR] Medium — [C-8] `ICArtifactSchema` 欄位未定義；「byte 級 round-trip」無 schema 錨點

**證據**：Task 3.1 L100–101「schema = per-feature × per-horizon 指標 + scope 標記 + eval_status…」無具體列名；驗證 `test_artifact_roundtrip` 要求 byte 級 + NaN mask hash。  
**會怎麼失敗**：writer/reader 各猜欄位；與現有 `ICResult`（`contracts.py:283–297` 無 horizon 維度）對齊不明；per-horizon 表形狀未訂。

**修法**：§P Task 3.1 附欄位表（至少：feature_name, horizon, ic_mean, ic_std, icir, p_value, eval_status, selection_scope_id）與 storage layout（long vs wide）；對齊 `ic_decay_horizons` 等現有引擎輸出。

---

### [MAJOR] Medium — 橫向：跨 tier / 檔案大小 / 計算穩定性缺口（使用者點名 #6）

| 面向 | SPEC 缺口 | 失敗模式 |
|------|-----------|----------|
| 數據品質 | CPCV `embargo` 清空 train 時**自動降 embargo**（`combinatorial_purged_cv.py:76–80`）未在契約標為弱化行為 | 靜默縮小 embargo → 洩漏增加 |
| 計算時間 | 全表 artifact 每次 run 必寫；無 tier 分級、無「Phase 1 小尺度」列數上限 | 45K+ feature run 寫檔主導延遲 |
| 計算穩定性 | `max_paths` 抽樣用 `rng=42` 但未寫入 SplitPlan 指紋 | 難重現、難除錯 |
| 跨 hardware tier | 無 8GB artifact peak RSS gate；Task 3.1 `read(filters)` 無 memory bound | 8GB OOM |
| 檔案大小 | 無壓縮/filter 統計目標 | disk 爆、CI 慢 |
| 業界標準 | purge 以 **row** 計；IC label horizon 未綁定 | 與 Lopez de Prado 時間 purge 不符 |

**修法**：§V 增 tier 表（8/16/32GB max artifact MB、max page_size）；契約記錄 CPCV embargo 降級為 `SkippedResult` 或 warning 契約；`SplitPlan` 含 `purge_semantic: Literal["rows","timedelta"]` 預設 rows 並標 1a 改進項。

---

### [MINOR] Medium — Manifest [C-1]「非僅 positional」與 Task 1.4 adapter 僅包 CPCV positional 索引

**證據**：Manifest L16 vs Task 1.4 改法。  
**修法**：Task 1.1 明訂 `SplitPlan` 以 `timestamp` 為 canonical、`row_index` 為 derived；adapter 必須附 `time_bounds` 自 kline index。

---

### [MINOR] Low — cross_sectional 模式未進 [C-3] 範圍

**證據**：`ic_filter_orchestrator.analyze_cross_sectional` 按 timestamp 橫截面 rank；SPEC [C-3] 只談堆疊 per-symbol split。  
**修法**：§N 或 §C 登記「cross_sectional 的 split/leakage 契約 Phase 1 不涵蓋」。

---

## §1 必查（10 類）

1. **矛盾/互斥**：有 — WalkForward `split()` vs 程式；Manifest timestamp-based vs adapter positional；§G 不變 vs Task 3.1/3.2 改 service。
2. **漏項/端到端**：有 — [C-10] HTTP 契約；`ic_response_v2` config；artifact cache key；cross_sectional；resume 時 artifact 路徑。
3. **不可測驗收**：有 — `config_hash` 在 TODO；artifact filter 無延遲/RSS 門檻；[C-7] `validate_alignment` 僅 NotImplementedError（可接受若標清）。
4. **可疑 quant 假設**：有 — row purge vs horizon；缺 bar；embargo 自動降級（見上）。
5. **過度工程**：無 — 契約層規模合理。
6. **OOM/並行**：有 — 全表 HDF5/無 tier cap（見上）。
7. **Cache 正確性**：有 — artifact 路徑未含 symbol/config_hash/version 組合規則。
8. **API/型別/相容**：有 — v2/off 矩陣缺失；Pydantic↔TS 未列。
9. **測試品質**：有 — 依賴 synthetic ML 測試聲稱 purge 已證；Golden 單一場景。
10. **Agent 可執行性**：有 — Task 1.4 WF `split()` 不可執行；Task 3.2 端點模糊。

## §2 範本錨點 + 獵空殼

- §RISK/§A/§C/§G/§P/§V/§R/§N：**齊全**。
- §G：有容差與 hash，但 **config_hash 外推 TODO** → 部分空殼。
- §G aggregate 風險：已要求 value hash + NaN mask — **足夠**。
- 空殼 Task：**3.1 schema 列**、**3.2 篩選端點**、**1.4 WF adapter API**。

## §3 不可違反原則

- 未要求刪特徵/弱化 NaN gate。
- **風險**：既有 CPCV embargo 降級行為若被契約默認接受，與「最高數據品質」精神衝突 — 建議契約層顯式標記，非靜默。

---

## 被當成事實的未驗證假設（§0）

| # | SPEC 陳述 | fact / assumption | 作者驗證？ |
|---|-----------|-------------------|------------|
| 1 | 兩 ML 工具皆有 `split()` 產出 `(train_idx,test_idx)` | **False**（僅 CPCV） | §A 聲稱已驗證 — **錯** |
| 2 | 30 測試證明 purge/embargo 在 IC 場景正確 | assumption（synthetic only） | 未用 kline/gap |
| 3 | per-symbol 包裝即可防 (d) 洩漏 | assumption | 未驗單 symbol 缺 bar |
| 4 | `purge_gap` 語意與 IC label horizon 對齊 | assumption | 程式為 row count |
| 5 | Phase 1 改動「必須 byte 級一致」 | 需條件（flag off、不接計算路徑） | Golden 未凍結 |
| 6 | HDF5 為合理預設 artifact | assumption | 未比 parquet/tier |
| 7 | 同 endpoint schema_version 足夠相容 | assumption | 無 flag-off byte 測試 |
| 8 | 漸進遷移可安全共存 | assumption | 無 SSOT 規則 |

---

## ASSUMPTIONS_VERIFIED

- `CombinatorialPurgedCV.split()` + `_apply_purge_embargo` 連續切片：`combinatorial_purged_cv.py:41–45,181–197`（實讀）。
- `WalkForwardValidator` **無** `def split`：`walk_forward_validator.py` grep 0。
- ML 孤島測試 15+15=30，fixture=`synthetic_binary_data`（實數檔案列舉）。
- `ICResult` 現欄位：`contracts.py:283–297`；`get_result` JSON 路徑：`ic_analysis_service.py:275–288`。
- V7 feature reader Parquet-only：`feature_reader.py` docstring。

## TESTS_RUN

- `grep "def split" momentum/Analysis/model_validation/walk_forward_validator.py`
- `grep "^def test_" tests/momentum/Analysis/model_validation/`（計數）
- 原始碼實讀 CPCV/WF/contracts/ic_analysis_service

## FAILURES_SEEN

none（審查任務，未跑 pytest）

## SCOPE_CHANGES

none（僅審查）

## NUMERIC_OR_SCHEMA_IMPACT

審查結論：SPEC 若按現稿實作，高機率觸及 `ICResult` schema、`get_result` JSON shape、新 artifact 二進制格式；§G 宣稱不變需收窄範圍方可成立。

## HANDOFF_NOT_UPDATED

唯讀 adversarial review；依執行合約不覆寫根 `HANDOFF.md`。

---

STATUS: DONE
