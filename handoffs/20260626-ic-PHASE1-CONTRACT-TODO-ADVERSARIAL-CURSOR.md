# IC Phase 1 1-contract — TODO Adversarial Review（Composer 2.5 / CURSOR）

> 審查對象：`docs/IC_PHASE1_CONTRACT_TODO.md`（對照 `docs/IC_PHASE1_CONTRACT_SPEC.md` v2、reconcile R1–R9）
> 範本：V13 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`
> 審查者：獨立（未參與 TODO 撰寫；未讀 CODEX 同輪 TODO review）

## Verdict：需修補後派工

TODO 相較 SPEC v2 大幅改善（WF 無 `split()`、gap 反例、embargo strict、三 Golden、Parquet、覆蓋表齊全）。但仍有數個 **冷啟動邏輯空殼** 與 **批次/驗收順序矛盾**，執行端若照現稿開寫會在 Task 1.4（embargo 怎麼算）、3.1（門檻多少）、3.2（route 未列 scope、baseline 尚未存在）、橫向 tier 表（數字未寫死）處卡住或腦補錯誤。

---

## Findings（依 V13 §0 挑戰前提置前）

### 挑戰前提 / 被當成事實的未驗證假設

#### F0-1. [MAJOR] High — Task 1.4 預設 (A)「包 `_generate_rolling_splits` 即可行」未驗證輸出形狀可映射 SplitPlan

**證據**：Task 1.4 實作要點 2：「包裝 `_generate_rolling_splits`…**預設 (A)**…可行」；實碼 `walk_forward_validator.py:256–273` 回傳 `List[Tuple[Tuple[int,int], Tuple[int,int]]]`（train/test **區間**），非 CPCV `split()` 的 `(train_idx, test_idx)` 整數陣列。

**會怎麼失敗**：冷啟動 agent 假設 WF 與 CPCV 同形狀，直接 `np.array_equal` 對照 CPCV 測試會寫錯；`time_bounds`/`row_index`/`embargo` 填法無規格，SplitPlan 語義在 WF path 上不一致。

**修法**：Task 1.4 補偽碼：區間→`np.arange(start,end)` 展開、`SplitPlan.embargo` 從 `WalkForwardConfig` 哪欄來、每 fold 一個 plan 還是 train+test 各一；驗證加 `test_adapter_wraps_wf` 與 CPCV 分開斷言。

---

#### F0-2. [MAJOR] Medium — `contracts.ICResult` 加 `eval_status` 與現行 IC JSON 路徑脫鉤，G1 可能「假綠」

**證據**：Task 2.2 改 `contracts.py::ICResult`；`grep ICResult momentum/Analysis`→**0 使用**；`get_result` 現走 `task_info["result"]` dict（`ic_analysis_service.py:275–288`）→ `_to_json_compatible`，**不經** `contracts.ICResult`。

**會怎麼失敗**：只改 dormant DTO + 單元測 constructed `ICResult`，G1 `test_flag_off_deep_equal_baseline` 仍綠，但 eval_status 契約從未進真實 report pipeline；1b/Phase 3 接線時才爆。

**修法**：Task 2.2 明訂 Phase 1 範圍是「DTO surface only」並在驗證區分 **contract unit** vs **integration（report 路徑仍無 eval_status 鍵）**；或加 Task 標記「接線留 1b」且 G1 斷言的是 `get_result` dict 鍵集合不變。

---

### 本輪必查 7 點（派工指令專項）

#### 必查-1. 冷啟動可執行性（§1.10）

| Task | 判定 | 摘要 |
|------|------|------|
| 1.1–1.3, 2.1–2.3 | 可執行 | ≥3 要點、邊界≥2、Test ID 具體 |
| **1.4** | **邏輯空** | embargo effective/requested **無公式**；WF 區間→索引未寫 |
| **3.1** | **不可測** | `tracemalloc peak < 門檻` **無數字**；`horizon` 來源未訂 |
| **3.2** | **邏輯空** | `ICArtifactQueryParams` 無 enum/運算子白名單；`top-N` N 值未寫 |
| 4.1 | **阻塞** | `config_hash` 仍為 `<TODO: 執行端凍結前…>` 佔位 |

**F1. [BLOCKING] High — Task 1.4 strict embargo 偵測缺少 effective vs requested 可執行定義**

**證據**：Task 1.4 實作要點 3：「重算 **effective embargo**（train 與 test 最近邊界的實際距離），`if effective < requested: raise EmbargoRelaxedError`」；CPCV 實碼 `embargo_len = int(n_samples * self.config.embargo_pct)`（`combinatorial_purged_cv.py:191`），`SplitPlan.embargo: int` 與 `embargo_pct` **無轉換規則**。

**會怎麼失敗**：三個 agent 實作三種 requested（pct×n、purge_gap 同單位、config 原值），strict 測試與生產語義不一致；CPCV `/2` 降級（L75–79）可能測不到。

**修法**：寫死：`requested_embargo_rows = int(n_samples * embargo_pct)`；`effective = min(test_min - train_max - 1, …)` 對每 test group；降級判定含「CPCV 是否執行過 L75–79 分支」（可比對前後 `embargo_pct` 或重跑 `_apply_purge_embargo` 不帶降級）。補進 Task 1.4 偽碼與 `test_adapter_detects_embargo_relaxation` 構造步驟。

---

**F2. [BLOCKING] High — Task 3.1 `test_artifact_filter_no_full_load` 門檻未量化（貌似有內容但邏輯空）**

**證據**：Task 3.1 驗證：「`tracemalloc` peak **< 門檻**」；SPEC §V tier 表：「8GB…**待 TODO 量測寫死**」——TODO **未填**。

**會怎麼失敗**：執行端自訂 500MB 或 8GB 都能「通過」；8GB tier OOM 或假綠。

**修法**：§0 或 Task 3.1 增 tier 表（8/16/32GB：`max_write_rss_mb`、`max_filter_read_rss_mb`、`page_size_cap`、測試用 N_features/N_rows）；或明訂「B3 動工前跑 `scripts/profile_*` 填數字」為 Gate。

---

**F3. [MAJOR] High — Task 3.1 `ICArtifactSchema.horizon` 與輸入 `ICResult` 無映射**

**證據**：Task 3.1 欄位含 `horizon:int`；`contracts.py:283–297` 之 `ICResult` **無 horizon**；IC 引擎 per-horizon 在 `ic_engine.py` decay 路徑，非單一 DTO 列。

**會怎麼失敗**：writer 猜一列一 feature 或展開多 horizon；G2 sha256 與下游 SSOT 漂移。

**修法**：明訂 long layout 一 row = `(feature, horizon)`；writer 輸入型別改 `Iterable[ICArtifactRow]` 或從 report `summary_table` 欄位映射表。

---

#### 必查-2. 上輪 BLOCKING 是否真落地

| 上輪項 | TODO 落地 | 判定 |
|--------|-----------|------|
| ① WF 無 split → 包 `_generate_rolling_splits` | Task 1.4 要點 2，不可改 wf | ✅ 方向對；❌ 區間映射未寫（見 F0-1） |
| ② 單 symbol gap → fail-closed 測試 | Task 1.3 `test_single_symbol_gap_blocked` + kline 刪 3 bar | ✅ |
| ③ CPCV embargo 降級 strict | Task 1.4 要點 3 + `EmbargoRelaxedError` | ⚠️ 有方向無公式（F1） |
| ④ flag-off byte 不變 | Task 2.2 不序列化 eval_status；3.2 deep-equal；3.1 不接 result path | ⚠️ 見 F4–F6 |

**F4. [MAJOR] High — Task 3.2 未列 `api/routes/ic_analysis.py`，`?schema_version=2` negotiation 無法落地**

**證據**：SPEC Task 3.2 / §A：「同 endpoint + `?schema_version=2`」；TODO Task 3.2 修改檔僅 `ic_models.py`、`config.py`、`ic_analysis_service.py`；現 route `get_result(task_id: str)` **無** Query（`ic_analysis.py:62–69`）。

**會怎麼失敗**：只改 service 簽名，HTTP 永遠走 v1；`test_v2_envelope_shape` 無法從 route 測。

**修法**：Task 3.2 修改檔加 `api/routes/ic_analysis.py::get_result` 加 `schema_version: Optional[int] = Query(None)` 並傳入 service；驗證用 `TestClient` 打 `/result/{id}?schema_version=2`。

---

**F5. [MAJOR] High — G1 baseline 與 B4 驗收順序矛盾（forward dependency）**

**證據**：Task 3.2 驗證含 `test_flag_off_deep_equal_baseline`（需 `baseline_btc_1h.json`）；Task 4.1 才「凍結前」產 baseline，且 `config_hash` 仍為佔位；§B：B4 在 B5 **之前**。

**會怎麼失敗**：B4 Gate 必紅或 agent 跳過測試假綠；違反防假綠原則。

**修法**：二選一寫死：(A) baseline 生成移入 B3 末 / B4 前置 Task 0（動工第一天跑 BTC/1h 填 hash）；(B) Task 3.2 驗證僅 smoke，G1 完整 deep-equal **只在 B5** 跑，B4 Gate 不含 G1。

---

**F6. [MAJOR] Medium — Task 2.2/3.2 標了 caller 檢查點，但無 decay/quantile/correlation/grouped/export 回歸 Test ID**

**證據**：Task 3.2「既有 caller：route…decay/quantile/correlation/grouped/export…**flag off 時行為不變,需確認**」；驗證僅 `test_flag_off_deep_equal_baseline`（`/result`）。實碼 decay/quantile/correlation/grouped 皆 `get_result` 後取子鍵（`ic_analysis.py:215–277`）；export filtered 亦 `get_result`（L321）。

**會怎麼失敗**：`get_result` 內部 normalization 微變（鍵順序、None 處理）→ 子端點靜默壞；G1 只蓋 `/result` 全 dict。

**修法**：加 `test_flag_off_subroutes_unchanged`：對 baseline task 比對 decay/quantile/correlation/grouped 回應 hash；或明列「子端點與 `/result` 同源 dict，G1 通過即涵蓋」並寫進驗證邏輯。

---

#### 必查-3. 覆蓋追溯 [C-1..C-12] + R1–R9

**F7. [MINOR] Medium — [C-11] 無獨立 Task，僅散落各 Task「修改 contracts / ic_models」**

**證據**：§自檢寫 [C-11]→各 Task；Manifest [C-11] 要求兩側 DTO 放置 + Rule 7。

**會怎麼失敗**：漏 `api/models` 側某 DTO 或誤 cross-import；僅靠 4.1 grep 事後抓。

**修法**：Task 4.1 或 §0 加可執行檢查：`grep -r "from api.models" momentum/core` 與反向皆 0；或 [C-11] 專項子任務。

其餘 [C-1..C-10][C-12]、R1–R9 與 §自檢映射 **一致，無掉項**（[C-10] HTTP 降 Phase 3 已與 SPEC §N 對齊）。

#### 必查-4. 批次依賴拓撲 §B

- B1→B2→B3→B4→B5 **無反向 batch 依賴** ✅
- **F5** B4 驗證依賴 B5 產物 ⚠️（見上）
- B1 標「純 dataclass」但含 Task 2.2 修改既有 `ICResult` — **MINOR** 敘述不精確，不阻塞

#### 必查-5. 語義 / 既有 caller

見 **F0-2、F6**；補充：`_to_json_compatible` 對 dataclass 無條件 `asdict`（`ic_analysis_service.py:1098–1099`），Task 2.2「檢查 _to_json_compatible」**未給修改指令**——若未來 result 樹含帶 `eval_status` 的 dataclass 會破 G1。

#### 必查-6. 量化正確性殘留（purge_semantic rows 債 + gap 偵測）

**F8. [MAJOR] Medium — `purge_semantic="rows"` 已知債未在 §0 醒目標記；gap 偵測算法仍模糊**

**證據**：Task 1.1 欄位預設 `purge_semantic="rows"`（註 1a 在 SPEC §P，**TODO §0 未列已知債**）；Task 1.3 要點 2③「`expected_freq` 給定但 ts 與 freq 不符（有 gap）」——**未指定**判定算法（最大間隔？`pd.infer_freq`？容差？）。

**會怎麼失敗**：agent 實作過鬆→rows-purge 洩漏漏網；過嚴→真實 kline 誤殺；執行端不知這是 Phase 1 刻意債還是終態。

**修法**：§0 增「**已知技術債**」：`purge_semantic` 預設 rows，1a 改 timedelta；Phase 1 靠 1.3+expected_freq **擋 gap 上 rows-purge**。Task 1.3 補：`gap if max(diff(ts)) > pd.Timedelta(expected_freq) * (1+atol)` 等可複製偽碼。

**正面**：Task 1.3 已有 `test_single_symbol_gap_blocked` 真實 kline 反例 ✅（較 SPEC v1 明顯改進）。

#### 必查-7. 使用者橫向考量（tier / artifact 延遲 / atomic write）

- **atomic write**：Task 3.1 `temp + os.replace` ✅ 可執行
- **tier 表 / page_size / RSS**：**F2** 未寫死 ❌
- **artifact 寫入延遲**：無 cold-read 延遲基準（SPEC reconcile 曾要求 10K/100K/430K）— **MINOR**，可併入 F2 量測 Task
- **跨 tier 8–32GB**：§0 原則有提，Task 3.1 僅 `tracemalloc` 無分 tier 命令

---

### V13 §1 十類快掃

| # | 類別 | 結果 |
|---|------|------|
| 1 | 矛盾/互斥 | 有 — B4 驗收 vs B5 baseline（F5）；Manifest [C-4] 仍寫 WF `split()`（TODO 已修正，追溯 MINOR） |
| 2 | 漏項/端到端 | 有 — route schema_version（F4）；子端點回歸（F6） |
| 3 | 不可測驗收 | 有 — RSS 門檻（F2）；embargo 公式（F1） |
| 4 | 可疑 quant 假設 | 有 — rows purge 債 + gap 算法（F8）；WF=CPCV 形狀（F0-1） |
| 5 | 過度工程 | 無 |
| 6 | OOM/並行 | 有 — tier 未量化（F2） |
| 7 | Cache 正確性 | 無（本刀 artifact 不接 task path） |
| 8 | API/型別/相容 | 有 — route 漏（F4）；ICArtifactQueryParams 空殼（F3 同族） |
| 9 | 測試品質 | 有 — G1 時序（F5）；子端點（F6） |
| 10 | Agent 可執行性 | 有 — 1.4/3.1/3.2/4.1 佔位（F1–F3、F5） |

### V13 §2 錨點 / 獵空殼

- TODO §0 / §B / 各 Task 驗證·邊界·不可做：**齊全**，非表頭空殼 ✅
- **邏輯空殼**：Task 1.4 embargo 公式、3.1 門檻、3.2 query enum、4.1 config_hash → **BLOCKING/MAJOR**（上列）

---

## 被當成事實的未驗證假設（§0 匯總）

1. **WF `_generate_rolling_splits` 輸出可直接等價 CPCV `split()` 索引** — 未驗證；實碼為區間 tuple（F0-1）。
2. **`contracts.ICResult` 是現行 `get_result` JSON 的序列化來源** — 錯；現為 analyzer report dict（F0-2）。
3. **「重算 effective embargo」語意自明** — 未驗證；CPCV 用 `embargo_pct` 非 SplitPlan.embargo（F1）。
4. **B4 可跑 G1 deep-equal** — 未驗證；baseline 在 B5 才凍結（F5）。
5. **改 service 即完成 API negotiation** — 未驗證；route 未入 scope（F4）。

無其他將「待量測」冒充「已寫死」者；SPEC §A 已驗證事實 TODO 有繼承（WF 無 split、kline 路徑等）。

---

## 修補優先序（給 reconcile）

1. **P0**：F1 embargo 公式 + F2 tier/RSS 數字 + F4 route scope + F5 baseline/B4 順序（寫死 A 或 B）
2. **P1**：F0-1 WF 映射偽碼、F3 horizon 映射、F8 purge 債 §0 + gap 算法、F6 子端點測試
3. **P2**：F0-2 ICResult 與 report 路徑關係、F7 [C-11] 檢查

修補後可重新 gate → Frozen → 派 B1。

---

ASSUMPTIONS_VERIFIED: 已讀 TODO/SPEC/reconcile/manifest/V13 範本；已 grep/實讀 `walk_forward_validator.py:256-273`、`combinatorial_purged_cv.py:75-79,191`、`ic_analysis_service.py:275-288,1098-1099`、`ic_analysis.py:62-277`、`contracts.py:283-297`；ICResult 在 momentum/Analysis 零引用
TESTS_RUN: none（文檔 adversarial review）
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
