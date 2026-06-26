# IC Phase 1 1-contract SPEC — Codex Adversarial Review

## Verdict：需修補後派工

SPEC 方向（contract-first）合理，但目前不可派工。主要問題不是欄位少，而是幾個被當成事實的前提未被契約化：per-symbol 後 positional purge 是否仍代表時間 purge、同 endpoint 版本化如何不破壞既有前端/子端點、artifact 物理格式如何滿足全表可篩與跨 tier，以及「只加 surface、舊路徑 byte 不變」和實際任務改動範圍互相拉扯。

## Findings

### 1. [BLOCKING] High — per-symbol split 只解決跨 symbol 邊界，沒有解決單 symbol 內 positional purge 的時間語義

證據：SPEC §A：「兩工具切分用 positional integer index」；Task 1.3：「per-symbol 套用既有 split()」；Task 1.4：「索引與直接呼叫 split() per-symbol 等價」。原始碼 `CombinatorialPurgedCV._apply_purge_embargo()` 用 `mask[purge_start:purge_end]`，`WalkForwardValidator._generate_rolling_splits()` 用 `test_start = train_end + purge_gap`。

會怎麼失敗：per-symbol 後如果單一 symbol 內有 missing bars、交易所停牌/資料缺洞、重複 timestamp、未排序 timestamp，`purge_gap=5` 只代表 5 row，不代表 5 個連續 bar 或 5 小時。這會讓 lookahead leakage gate 形式上通過，但實際時間上 purge/embargo 不足；反方向也可能過度 purge，降低樣本穩定性。這正中使用者點名的 (d) 正確性紅線。

修法：SplitPlan/adapter 必須把 purge/embargo 單位明確化（rows vs timedeltas），並在 adapter 入口 fail-closed 驗證每個 symbol 內 timestamp 單調遞增、無重複、符合 expected freq 或明確允許 gap 並用 timestamp-based purge。測試要用真實 kline 製造 gap/重排/重複 timestamp 反例，不能只測 BTC 尾接 ETH 頭。

### 2. [BLOCKING] High — SPEC 要求 fail-closed，但複用的 CPCV 既有行為會自動降低 embargo

證據：SPEC §V：「[C-3] 洩漏反例必須真的 raise，不得降級為 warning」；Task 1.4：「不改 walk_forward_validator/combinatorial_purged_cv 任何一行」。原始碼 `combinatorial_purged_cv.py` 在 train empty 時 `logger.warning("...自動降低 embargo")`，並暫時把 `self.config.embargo_pct` 減半重算。

會怎麼失敗：adapter 若「不改 CPCV」且只包裝 split()，會繼承 silent relaxation。這和 fail-closed contract 衝突：極端資料或小樣本時，實作可能為了產生 split 自動放寬 embargo，導致 leakage protection 被弱化但測試仍綠。

修法：contract 要明確要求 IC adapter 在呼叫前後檢測 effective purge/embargo 是否等於 requested，或新增 strict mode 包裝器，發現 CPCV fallback/empty-train relaxation 時 raise `CrossSymbolLeakageError` 或 structured skipped。若不能改 CPCV，adapter 必須獨立重建/驗證 returned train/test index 的實際 embargo 距離。

### 3. [BLOCKING] High — 「只加 contract surface、舊路徑 byte 不變」和 Task 3.1/3.2 的實作範圍矛盾

證據：Manifest：「不改既有 IC 計算數值」；SPEC §G：「本刀只加契約 surface，不改計算 → 必須 byte 級一致」；但 Task 3.1 新增 `ic_artifact_writer.py` 寫真實 IC 輸出，Task 3.2 要 `IcAnalysisService.get_result()` 加版本化分支，§R 又說 `ic_response_v2` feature flag 預設 off。

會怎麼失敗：執行 agent 可能在同一刀同時接入 artifact 生成與 response 改版，實際觸碰現有 result path。即使 IC 數值不變，JSON shape、response size、None/NaN serialization、result timing、artifact side effect 都可能變。現有前端 `useICAnalysis.ts` 直接把 `/result/{taskId}` 當 `ICReport`；其他 route（decay/quantile/correlation/grouped/export）也讀 `get_result()` 的舊 dict。

修法：把 flag-off 行為寫成可測 contract：`ic_response_v2=false` 時 `/result/{task_id}` byte-for-byte 等於 baseline，且不生成/不要求 artifact；`true` 時才返回 v2 envelope。Task 3.1 若只是 schema/writer contract，不應接進 task result path；若要接入，則本刀不再是純 surface，§G/§R/驗證需重寫。

### 4. [MAJOR] High — API 版本化選「同 endpoint + schema_version」但沒有定義 negotiation，向後相容不可驗

證據：SPEC §A [Q-2] 預設「同 endpoint 加 `schema_version` 欄 + `artifact_uri`」；Task 3.2：「保留舊欄（[Q-3] 漸進）；新增讀 artifact 的篩選端點契約（query: sort_by/filter/page）」；目前 route `api/routes/ic_analysis.py` 的 `/result/{task_id}` 無 response_model，frontend `ICReport` 沒有 `schema_version`/`artifact_uri`/`top_n_summary`。

會怎麼失敗：同 endpoint 如果直接新增 envelope，舊前端找不到 `summary_table`/`ic_decay`；如果把新欄塞進舊 dict，大 run 又可能仍帶全表，違反「response 不含全表」。此外沒有 query/header/request 欄位指定 v1/v2，無法同時保證舊客戶端和新客戶端得到各自 schema。

修法：SPEC 必須先定 API negotiation：例如 `/result/{task_id}?schema_version=2` 或 `/result-v2/{task_id}`，並列出 v1/v2 response JSON 最小 schema、Pydantic model、TS interface、default 行為、deprecation gate。artifact filter endpoint 也要有確切 path、query 型別、排序欄位白名單、pagination cursor/limit、404/410/partial 狀態。

### 5. [MAJOR] High — 舊 JSON 共存策略沒有解決雙寫一致性與「全表不回 JSON」的內在衝突

證據：Task 3.1：「不刪舊 JSON 路徑（共存，[Q-3]）」；Task 3.2：「舊欄仍存在（向後相容斷言）」以及「大 run → response 不含全表（size 斷言）」。

會怎麼失敗：若舊欄仍承載完整 `summary_table`，大 run response size 仍爆；若舊欄只留 top-N，舊客戶端語義變了；若 JSON 與 artifact 雙寫完整結果，會有排序/filter/FDR scope/eval_status 不一致風險。SPEC 沒有要求 artifact 和 legacy JSON 的 row identity/hash 一致，也沒有定義遷移期間哪個是 source of truth。

修法：定義 migration matrix：小 run 是否雙寫全表、大 run 是否 v1 禁用或回 409/指向 export、v2 artifact 是否唯一 source of truth。新增一致性驗證：legacy summary subset 必須是 artifact 按同 sort/filter 取 top-N 的結果，feature id/order/hash 一致；禁止兩套獨立計算。

### 6. [MAJOR] Medium — Artifact 預設 HDF5 沒有物理 layout/index contract，無法保證全表可篩、跨 tier、檔案大小與業界慣例

證據：SPEC §A [Q-1]：「預設 HDF5（與 data_cache 一致）vs parquet」；Task 3.1：「writer `write(results, path)`/`read(path, filters)` 支援按需篩選/分頁」；使用者點名要權衡「檔案大小 / 篩選效率 / 跨 hardware tier(8-32GB) / 量化業界慣例」。

會怎麼失敗：HDF5 是否可高效 filter 取決於 dataset layout、chunking、索引、string encoding、compression、metadata organization。SPEC 只說 `.h5` 和 `read(filters)`，沒有要求 predicate pushdown、columnar layout、row group/chunk size、排序 key、atomic write、partial read memory cap。實作可能寫成單一 pandas HDF table 或整表載入再 filter，在 8GB tier 失敗；也可能錯失 parquet/arrow 對表格掃描與跨語言工具的優勢。

修法：不要在 SPEC 內把 HDF5 預設變成派工命令。先補一個 artifact format decision record：HDF5 vs parquet/arrow/duckdb 的比較，以目標規模、查詢模式（sort_by/filter/page）、8GB memory cap、文件大小、NaN/inf fidelity、atomicity 為 gate。若仍選 HDF5，必須指定 layout/chunk/compression/index 與「filter 不整表載入」的測試。

### 7. [MAJOR] High — Golden baseline 覆蓋不足，抓不住本刀最可能破壞的 artifact/API/split contract

證據：§G 只指定「BTC/1h」和「現有 IC longitudinal 主流程」；baseline 內容是「抽樣 value hash + feature 名稱集合 sha256 + 數量/schema + NaN mask hash」；Task 4.1 才集合多個測試，但 §G 的簽核點仍是單 symbol。

會怎麼失敗：單 BTC/1h longitudinal baseline 不能發現 cross-symbol leakage、per-symbol adapter gap 問題、API v2 envelope 破壞前端、artifact roundtrip filter 不一致、舊 JSON/top-N subset 不一致。且「抽樣 value hash」不是 byte 級全值守恆，局部 feature 漂移可能被抽樣漏掉。

修法：§G 分成三個 golden：v1 JSON byte-stability（flag off）、artifact full-table roundtrip（所有 feature rows/value/NaN/inf/status hash，不抽樣）、multi-symbol split/leakage golden（至少 BTC+ETH 真實 kline，含 gap/unsorted negative case）。每個 golden 明確命令、輸出檔、hash 粒度和 fail output。

### 8. [MAJOR] Medium — `RowMaskPlan`/`SplitPlan` 欄位允許 mask 或 index，但缺 canonical identity，會造成 scope/artifact 無法對齊

證據：Task 1.1：「`row_index: np.ndarray`（或 timestamp 陣列）」；Task 1.2：「`mask: np.ndarray[bool]` 或 `row_index: np.ndarray`」；Task 2.1/3.1 要把 split/scope/eval_status 寫進 artifact。

會怎麼失敗：mask 是相對於哪個 dataframe/order？row_index 是 positional、original integer index、timestamp，還是 MultiIndex？如果 artifact 只保存 feature metrics 而不保存 canonical row universe id，後續 FDR scope、split label、event mask、artifact filter 都可能對不上。這也是 positional-index 事故的同類風險。

修法：契約必須定 canonical row identity：至少 `(symbol, timestamp, timeframe)` 或 explicit `row_id` + source frame hash/order hash。`RowMaskPlan` 不應允許 ambiguous union 而無 discriminator；需要 `index_kind: positional|timestamp|row_id`、`base_universe_hash`、`length`、`time_bounds`。

### 9. [MINOR] Medium — `ICResult.eval_status` 預設 EVALUATED 可能讓未遷移路徑假裝已評估

證據：Task 2.2：「`ICResult.eval_status: EvaluationStatus = EVALUATED`；既有 ICResult 無欄位 → 預設 EVALUATED（Golden byte 不變）」；同段又說 `not_evaluated` 是防漏安全機制。

會怎麼失敗：所有 legacy result 在沒有 scope/evaluation audit 的情況下都被標成 EVALUATED。若 Phase 1 後某些新 path 漏填 eval_status，default 會掩蓋漏評估，和「防漏」語義相反。

修法：保留 legacy JSON byte stability 可以不序列化新欄，但內部新契約物件應要求明確 eval_status，或用 `UNKNOWN_LEGACY`/`UNSPECIFIED` 作為 adapter 邊界狀態，排序/FDR 前只接受 explicit EVALUATED。

### 10. [MINOR] High — 範本錨點齊全，但 TODO 前仍有空泛實作點會讓 agent 自行發明

證據：Task 3.1：「schema = per-feature × per-horizon 指標 + scope 標記 + eval_status 旗標 + schema_version」沒有列具體欄位；Task 3.2：「query: sort_by/filter/page」沒有型別；§R：「feature flag（`ic_response_v2`，預設 off）」但沒有配置位置。

會怎麼失敗：不同 agent 會各自決定欄名、sort enum、filter DSL、feature flag source（env/config/request），導致 API/TS/backend artifact 三邊不一致。

修法：TODO 生成前補最小 schema 表：欄名、dtype、nullable、排序/篩選允許欄位、schema_version 型別、flag config path、API examples。

## 10 類必查覆蓋

1. 矛盾/互斥：有。Finding 3、5。
2. 漏項/端到端：有。Finding 4、6、8、10。
3. 不可測驗收：有。Finding 6、7。
4. 可疑 quant 假設：有。Finding 1、2、9。
5. 過度工程：無 blocking；contract-first 合理，但 artifact writer/API branch 可能超出「純 surface」，見 Finding 3。
6. OOM/並行：有。Finding 6；未定 partial read memory cap。
7. Cache/Artifact 正確性：有。Finding 5、6、7；atomic write/stale invalidation 未具體化。
8. API/型別/相容：有。Finding 4、5、10。
9. 測試品質：有。Finding 7；單 BTC/1h golden 不足。
10. Agent 可執行性：有。Finding 10。

## 被當成事實的未驗證假設（§0）

- 「per-symbol 套用既有 positional split 即可防洩漏」：只驗證了不跨 symbol；未驗證單 symbol timestamp 連續、無 gap、row purge 等價於 time purge。
- 「CPCV/WF 既有 split 可直接複用且不弱化 gate」：CPCV 已有自動降低 embargo 的 fallback，和 fail-closed 未對齊。
- 「同 endpoint 加 schema_version 可向後相容且減少前端返工」：未定 negotiation/default 行為，現有 frontend `ICReport` 並無 v2 envelope 型別。
- 「舊 JSON 共存 + 大 run response 不含全表」可同時成立：未定 v1/v2 source of truth、雙寫一致性和小/大 run 分界。
- 「HDF5 是合適 artifact 預設」：未提供對 parquet/arrow/duckdb 的實測或查詢模式比較，也未定 HDF5 layout。
- 「BTC/1h longitudinal golden 足以證明行為不變」：不能覆蓋 multi-symbol split、artifact/API、filter/pagination、cross-tier partial read。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、指定派工 prompt、V13 review template、SPEC、manifest、brief、CONVERGED plan；抽查 CPCV/WF split 原始碼、contracts/API model/service/result route/frontend ICReport 型別。
TESTS_RUN: read-only review，未跑 pytest；使用 `sed`/`rg`/`wc` 做文件與程式碼證據檢查。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查文件，未改實作/schema）
STATUS: DONE
