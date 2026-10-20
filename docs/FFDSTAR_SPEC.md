# FFDSTAR（PRE-PROV）— 每次特徵產出之逐欄執行紀錄與 IC 讀取身分 — SPEC

> 來源：偵察 r4 收斂檔 `handoffs/reconcile/20260921-ffdstar-x-consult-r4/synth.md`（主委獨立版 `handoffs/20260921-ffdstar-x-consult-r4-claude.md`）；範圍權威 `docs/TICKET_ORDER.md` 第 7 列　|　日期：2026-10-19　|　對應 TODO：`docs/manifests/FFDSTAR.json`
> 版本：v4（2026-10-20；第 2 批實作期發現兩事併入：§V 補 replace 模式格〔生產預設〕、Task 1.2 平行轉序列回退之序列重跑自原始輸入開始〔既有雙重差分缺陷〕；隨第 2 批審碼一併審）。v3（2026-10-19；審查 r5／r6 修訂與 Task 1.1 盤點草稿所揭缺口併入，處置見 `handoffs/reconcile/20260921-ffdstar-x-review-r5/synth.md`、`20260921-ffdstar-x-review-r6/synth.md`）。v2（2026-10-19；FF-STAT、FF-NAME 收案後依現況全文重寫，落點、紀錄範圍與 fact-key 內容皆以本版為準；先前版本之定性與輪次見 `handoffs/reconcile/20260921-ffdstar-x-consult-r1/synth.md`、`20260921-ffdstar-x-review-r2`、`20260924-ffdstar-x-review-r3`）。

## §RISK 風險分級
- **大小**：大（`docs/TICKET_ORDER.md` 標中；依 CLAUDE.md 判準命中 (a)(b)(d)，以大任務管線執行）。
- **命中高風險原則**：(a) 資料品質——IC ingest 快取以設定身分為鍵、有檔即沿用 ⇒ 同 config_hash 重生後 IC 分析非本次 run 之特徵值；紀錄若與實際執行不符即為假證據；(b) 跨模組共用路徑——`momentum/FeatureEngineering/{feature_storage,feature_factory,feature_reader,feature_library}.py`、`preprocessing/feature_preprocessor.py`、`momentum/Analysis/{ic_engine,ic_filter_orchestrator,survivor_contract}.py`、`api/services/ic_analysis_service.py`；(d) ML 正確性——IC 選欄所據之特徵值身分。
- RISK-HIT: a,b,d
- 命中 (a)(d) ⇒ §G 必填、adversarial review 必跑。

## §A 假設與待使用者確認
- **已驗證事實**（FACT-RECEIPT 10 條）：
  - 逐欄決策已收集、從未落盤。FACT-RECEIPT: `sed -n 3880,3922p momentum/FeatureEngineering/feature_factory.py` → 印出 `raw_path, stream_summary = self._storage.write_raw_from_registry_stream(` 於 `:3880`，`self._capture_stationarity_decisions(preprocessor, config)` 於 `:3922`（writer 返回之後）（主委 實跑 2026-10-19）
  - writer 於 manifest 合併前已持有前處理器。FACT-RECEIPT: `sed -n 1212,1225p momentum/FeatureEngineering/feature_storage.py` → 印出 `preprocessor.stationarity_failure_reasons()` 於 manifest 合併前，與註解 `（§C 不新增 manifest 鍵）`（主委 實跑 2026-10-19）
  - 合併以覆寫為之。FACT-RECEIPT: `sed -n 516,529p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 印出 `self._decisions[key] = record`；`sed -n 4170,4180p momentum/FeatureEngineering/feature_factory.py` → 印出 `merged[name] = record`（主委 實跑 2026-10-19）
  - raw 安裝先於 manifest 合併，來源已刪之晚期失敗保留新 raw。FACT-RECEIPT: `sed -n 1232,1300p momentum/FeatureEngineering/feature_storage.py` → 印出 `os.replace(temp_artifact_dir, final_artifact_dir)` 後才 `self._atomic_merge_feature_manifest_v2(`，例外分支 `preserve_temp = source_deleted`（主委 實跑 2026-10-19）
  - IC-first 落 processed 後刪整個 raw。FACT-RECEIPT: `sed -n 2995,3004p momentum/FeatureEngineering/feature_factory.py` → 印出 `if cleanup_raw and raw_path.exists():` … `_ic_shutil.rmtree(raw_path)`（主委 實跑 2026-10-19）
  - IC ingest 快取鍵與沿用條件。FACT-RECEIPT: `sed -n 3287,3306p api/services/ic_analysis_service.py` → 印出 `safe_key = f"{symbol}_{timeframe}_{hash_key}"`、`if not h5_path.exists() or not self._ic_handoff_h5_current(h5_path):`、`if not meta_path.exists():`（主委 實跑 2026-10-19）
  - IC-first JSON 快取身分無值身分。FACT-RECEIPT: `sed -n 39,50p momentum/Analysis/ic_engine.py` → 印出 `CACHE_IDENTITY_FIELDS` 十欄（symbol、tf、config_hash、method、label_horizon、selection_window_start、selection_window_end、split_id、feature_axis_sha256、label_sha256）（主委 實跑 2026-10-19）
  - 生產寫入點只有兩個。FACT-RECEIPT: `git ls-files -z momentum api | xargs -0 grep -nE '\.write_raw\(|\.write_processed\(|write_raw_from_registry_stream\('` → 印出 `feature_factory.py:2986` `storage.write_processed(`、`feature_factory.py:3880`、定義 `feature_storage.py:738`；`write_raw`（`feature_storage.py:704`）無生產呼叫者（主委 實跑 2026-10-19）
  - 倖存者契約之 provenance 鍵封閉。FACT-RECEIPT: `jq -c '.provenance_keys.additional_properties' momentum/Analysis/contracts/ic_survivor_contract.json` → 印出 `false`（主委 實跑 2026-10-19）
  - 輸出增量實測（BTCUSDT/12h 全特徵 run：204,150 欄、L1＋L2 決策欄 43,536、247 群組、run 590 MB、manifest 58,947,580 B）。FACT-RECEIPT: `venv/bin/python <scratchpad>/preprov_size.py data_cache/features/BTCUSDT/12h/0729db3a2de860b6c7d01be16ca22d22/feature_manifest.json` → 印出 `A_inline_decisions_indent2 16347513`、`A_inline_winsor_per_column_indent2 17405793`、`B_sidecar_decisions_parquet_zstd 610310`、`B_sidecar_winsor_per_column_parquet_zstd 662945`、`A_inline_group_status_indent2 37712`、`read_seconds_parquet_decisions 0.0268`、`read_seconds_manifest_json_now 0.225`（主委 實跑 2026-10-19；收據 `handoffs/run_receipts/20261019-preprov-output-size-approval.json`）
- **待確認**：無
- **已確認結果**：2026-10-19 使用者核可輸出增量之存法標準（逐字「我期望的是記錄的數據是準確，檔案盡可能小，讀取盡可能快且精準，但我不知道哪個比較好」）⇒ 逐欄紀錄另存 run 目錄內壓縮 parquet、manifest 只放摘要與指紋（估約 +1.3 MB／全特徵 run，+0.2%）；實作後以真實生成重量，明顯超出估算須再報（Task 3.2）。2026-08-05 使用者定：修正只考慮以後、不回溯舊資料。2026-10-02 使用者定：開發期資料皆可重新產生、不需相容或遷移（`docs/TICKET_ORDER.md:9`）。

## §C 約束
- 解耦 7 條：紀錄收集、序列化、身分解析置 `momentum/`；`api/` 只經 `momentum` 公開函式取身分，不自組；不新增服務互相 import。
- 不可違反原則：**不改任何特徵值、NaN 遮罩、欄集合、欄順序、dtype、`config_hash`、`feature_schema_hash`**；不弱化 NaN／inf 閘；不放寬既有測試斷言；不得寫死加密貨幣／24h／UTC 假設（紀錄之時間欄沿用既有 UTC 表示，不新增時間單位假設）。
- **契約單一真相源**：逐欄紀錄之欄位、各步驟狀態值集、群組轉換臂值集、manifest `provenance` 物件與 run 身分物件之鍵，一律定義於 `momentum/FeatureEngineering/contracts/run_provenance.json`；本 SPEC 與測試只 pointer，不另列舉。
- **推翻既有約定**：`feature_storage.py:1224-1225` 之「§C 不新增 manifest 鍵」於本票失效（新增鍵為本票目的），該註解同步刪除。
- **嚴禁慢閘**：寫入端之雜湊於寫檔當下計算；讀取端只驗宣告檔存在、路徑在 run 內（stat 級）與紀錄檔 sha256（約 1 MB）；不在每次讀取重算特徵檔雜湊。
- **刻意可見差異（全部設定）**：
  - D1 run 目錄新增 `provenance/` 子目錄：raw 紀錄檔一個；IC-first 另有 processed 紀錄檔一個（檔名見契約）。
  - D2 manifest 每個 artifact 節點新增 `content_sha256` 與 `provenance` 物件（鍵見契約）；`generation_metadata` 原有鍵不刪不改（`raw_artifact_applied` 等保留為設定紀錄，不作執行證據）。
  - D3 前處理決策合併遇同鍵且值不逐項相同 ⇒ 拋錯使 run 失敗（改前後寫勝）。
  - D4 raw 安裝前先將舊 manifest 之 raw 節點標為不完整；任何失敗後該 run 不可被讀為完整。
  - D5 IC：ingest 快取（h5 與 `_meta.json`）以 run 身分驗證、不符或缺鍵即重建；交接 h5 寫 `metadata_json`（含 run 身分）；IC-first JSON 快取身分加 `content_sha256`；IC 報告 metadata、倖存者 provenance、API 結果帶同一 run 身分物件（倖存者契約版本 +1）。
  - D6 無新鍵之舊 run／舊快取：特徵讀取不受影響；IC 快取一律不沿用（重建）；紀錄讀取回具名「無紀錄」錯誤。
- 範圍外：臂／算法 fingerprint 入不可變身分（第 8 步 NUMVIEW）；縮尾唯一責任端（第 9 步）；FFSTORE 快照版本（第 14 步）；FF 生成提速（使用者 2026-10-11 延後）。

## §G Golden / Baseline
- **feature/kline 條件**：適用。驗收一律用真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。
- **值不變之承接**：既有凍結之值指紋（`tests/_golden/{failopen,framepath,ffstat,ffname,icfirstalign,probewinsor,ratiounsafe}` 中之逐欄值／NaN 遮罩／dtype／欄集合指紋）修改前後**逐位元相同**；任一值指紋改變 ⇒ FAIL，不得重凍。
- **結構凍結之重凍**：凡比對 run 目錄檔案集合、manifest 全文或其鍵集合之凍結項，因 D1／D2 必變；只准重凍「新增之 `provenance/` 檔與 manifest 新鍵」，重凍收據逐項列出差異路徑且證明其餘逐位元相同。**證法（第 4 批盤點後定案）**：於同一次改後之真實 run，把 manifest 之新鍵（各 artifact 節點之 `content_sha256`、`provenance`）與 `provenance/` 路徑剝除後依原凍結算法重算，須逐位元等於現行凍結值（現行凍結值出自改前碼）；相等 ⇒ 其餘部分逐位元不變得證，才以含新鍵之值重凍；不等 ⇒ 不重凍、停下歸因。此法取代改前／改後雙 worktree 重跑（凍結值只存雜湊、需真實生成，雙 worktree 使生成成本加倍而證明力相同）；工具 `scripts/preprov_refreeze.py`，收據 `tests/_golden/preprov/refreeze_receipt.json`。受影響項（盤點 `handoffs/run_receipts/20261020-ffdstar-b4-plan.md`）：failopen BTC multi_tf 產物清單、framepath 10 格 `manifest_sha256`，及其下游 FF-NAME 重凍收據綁定與 framepath 歷史格檢查；fftfmeta 之 `manifest_stripped_sha256` 為 FF-NAME 收案時已登記之既有漂移，不重凍、只核對新鍵為其唯一新差異。
- **讀取方式先行**：凍結腳本與測試輔助凡以檔名掃描 run 目錄取特徵者（至少 `scripts/freeze_failopen_baseline.py:260,425`、`scripts/freeze_framepath_baseline.py:415`、`tests/feature_engineering/ffstat_helpers.py:66,233,346,363,442,577`；Task 1.6 以 grep 窮舉），先改為依 manifest 宣告之群組讀取，於**改前碼態**重算其值指紋等於現行凍結值，再套 Phase 1 生產改動。
- **改前基準**：Phase 1 動工前 HEAD 之真實 kline 短窗格（§V 格子）完整生成之公開值指紋（逐欄 float32 值 sha256＋NaN 遮罩 sha256＋dtype＋欄名集合 sha256，同 `tests/feature_engineering/ffstat_helpers.py` 之 `public_fingerprints` 式），存 `tests/_golden/preprov/pre_change_fingerprints.json`；改後同格逐位元相同（atol=0、rtol=0；紀錄不改任何值，不設容差）。

## §P Phase 與依賴
> 執行序＝ Task 1.1 → 1.6 → 1.2 → 1.3 → 1.4 → 1.5 → 2.1 → 2.2 → 2.3 → 2.4 → 3.1 → 3.2（1.6 讀取方式先行，見 §G）。自檢：無 forward dependency。

### Phase 1 — 特徵工廠端逐欄紀錄（依賴：無；FF-NAME 已收案）

**Task 1.1 — 離開路徑盤點與契約 JSON**
- 目標：以碼證列出 L6.5（raw-sink、in-place、native 子實例、post-IC）每一步驟之每條實際離開路徑，定稿紀錄契約。　檔案：新建 `momentum/FeatureEngineering/contracts/run_provenance.json`；盤點對象 `feature_preprocessor.py` 之 `transform_registry_groups_to_sink`、`_transform_single*`、`_apply_fractional_differencing*`、ADF 差分、縮尾、rank、zscore、gaussian、ratio-unsafe passthrough、native 成功／回退、`transform_selected`；`feature_storage.py` 之 dead-drop；`feature_factory.py` 之失敗群組。　既有 caller／影響面：新建，無 caller。
- 改法：契約含——逐欄紀錄欄位與型別（輸出欄名、原生週期、層、群組 id、各步驟狀態、平穩化決策欄、事件、終態）；各步驟狀態封閉值集（每值附 `_sources`：至少一個 `path:line` 離開點）；群組轉換臂與回退值集；manifest `provenance` 物件鍵；run 身分物件鍵；紀錄檔相對路徑。值樣式 `^[a-z][a-z0-9_]*$`。**不得杜撰無離開點之值；每個離開點須有對應值。**
- **驗證**：`pytest tests/feature_engineering/test_preprov_contract.py` 全綠，其中：①契約每個狀態值之 `_sources` 每個 `path:line` 須位於特徵工廠寫入路徑之檔（`momentum/FeatureEngineering/preprocessing/` 下、`feature_storage.py`、`feature_factory.py`），且該行所屬之單一陳述式為對紀錄函式之呼叫、實參含該值之字串字面——指向無關可執行行、或他域含同字面之行（例 `momentum/Analysis/ic_engine.py:167` 回傳 `"applied"`）即紅；②契約值皆合樣式；③Task 3.1 驗收格之實際紀錄中出現之值集合 ⊆ 契約值集，且契約中每個值至少被一格或一條單元案例產出（未產出之值須於契約 `_unreachable` 具名並附碼證理由）。mutation：契約刪一個實際會出現之值 ⇒ ③紅。
- **邊界**：①statsmodels 不可用之 fracdiff 早退；②目標層外之欄（fracdiff 不涵蓋）；③平穩化關閉時平穩化決策欄全 null，fracdiff／ADF 之步驟狀態各為契約中表示「關閉」之值（步驟狀態欄不得為 null）。
- **契約補充**：SPEC 驗收中具名之 `applied`（縮尾）、`ratio_unsafe`（終態）、`polars`（post-IC 群組臂）須存在於契約對應值集（測試先斷言其存在）；`_unreachable` 形為 `{<值>: {"reason": <文字>, "_sources": [<path:line>, …]}}`；`content_sha256` 項之 `dtype` 為該檔各欄 Arrow 型別去重排序後以 `|` 連接之字串；SPEC 以語意指稱之值（總開關關閉之步驟狀態、ADF 檢定例外之事件）由契約 `named_values` 給出其字面（Task 1.1 填入，測試經之查值、不寫死字面）。
- **存活至**：本票交付後保留（契約為唯一真相源）。
- **覆蓋風險**：無。
- **盤點輸入**：草稿 `handoffs/run_receipts/20261019-ffdstar-task11-inventory-draft.md`（HEAD 2609aa1f 唯讀盤點，約 120 個錨點）；實作以碼為準重核。草稿揭示之定案：①總開關關閉（不建前處理器）⇒ writer 對全部欄全部步驟記「總開關關閉」之值；raw 路徑強制關之 rank／zscore／gaussian 與 post-IC 強制關之縮尾／fracdiff／ADF 記「關閉」之值（使用者原設定已在 `preprocessing_config_enabled`）；②in-place 路徑（`transform_registry_groups` 及其子路徑）無生產呼叫者 ⇒ 只在該路徑可產生之值列 `_unreachable`；③群組回退可多重（native 回退與 fracdiff parallel→serial 回退可同群發生）⇒ 契約另設回退值集，manifest 群組之 `fallback` 為清單；④numba 快速核心對整個陣列同式套用、無逐欄跳過分支 ⇒ 快速臂之逐欄狀態於其呼叫點依群組記錄（ratio-unsafe 遮罩欄除外），週期由呼叫端傳入；⑤`_transform_single` optimized 分支於記錄脈絡設定前返回（`feature_preprocessor.py:2957` 附近）⇒ 脈絡須於分支前設定。
- 不可做：不得改任何步驟之條件與數值。只為記錄而補之 `else`／`for…else` 分支（不改條件、不改數值、不改控制流去向）允許，視為記錄點而非轉換判斷分支。

**Task 1.6 — 測試輔助與凍結腳本改依 manifest 宣告讀取（先於生產改動）**
- 目標：消除「以檔名掃描 run 目錄當特徵」之讀法，使新增紀錄檔不被誤讀。　檔案：`git ls-files -z tests scripts | xargs -0 grep -nE 'rglob\(|glob\('` 命中且作用於特徵 run 目錄者（至少 §G 所列）；新增 `tests/feature_engineering/preprov_helpers.py`（依 manifest 列群組檔之單一函式）。　既有 caller／影響面：各凍結腳本與其測試、`ffstat_helpers` 之全部呼叫者。
- 改法：特徵檔集合一律自 manifest artifact 節點之 `groups[*].path` 與 row index 宣告導出；凍結腳本之「run 目錄全部檔」雜湊改為「manifest 宣告檔＋manifest 本身」；未宣告檔出現於 run 目錄 ⇒ 輔助函式拋錯（不靜默忽略）。
- **驗證**：於**改前生產碼態**對既有凍結項重算值指紋，逐項等於現行凍結值（不重凍）；`pytest` 逐檔明列受影響之凍結測試全綠。掃描點清冊 `tests/_golden/preprov/reader_inventory.json` 列 `tests/`、`scripts/` 受版控 .py 中全部 `glob(`／`rglob(`／`iterdir(`／`os.listdir(`／`os.walk(` 呼叫點（`path:line`），每點分類 `feature_run`（以檔名列舉 run 目錄並把所得檔當特徵讀取、指紋、計數或改寫者，須改依 manifest）或 `unrelated`（附一句理由；含只做位元組快照、殘檔／版面斷言、尋找 manifest 或 run 目錄、量測大小者——其中位元組快照之變動由 §G 結構重凍承接）；清冊鍵為（路徑、所在函式限定名、呼叫文字、出現序），行號僅供參考；測試以 AST 重掃，清冊外之新呼叫點、或 `feature_run` 類仍以檔名掃描者即紅；另以本票 TODO 提交 `2609aa1f` 之清冊為凍結基準：既有 `feature_run` 條目只准因呼叫點消失（改依 manifest）而離開清冊，不得改標為 `unrelated`（改標即紅；新條目之分類於審碼時審）。mutation：輔助函式改回 `rglob("*.parquet")` 且 run 目錄放入一個非宣告 parquet ⇒ 新增之 `test_preprov_helpers.py` 案例紅；自清冊刪一個 `feature_run` 點 ⇒ 紅。
- **邊界**：①processed artifact 之群組與 `processed_timestamps.parquet`；②IC-first 已刪 raw 之 run（只剩 processed）；③多週期 run 之群組。
- **存活至**：本票交付後保留。
- **覆蓋風險**：Task 3.1 之結構重凍會再動凍結檔之結構項，值指紋項不動。
- 不可做：不得重凍任何值指紋；不得以「排除特定檔名」代替依 manifest 讀取。

**Task 1.2 — 前處理器之逐欄執行狀態收集**
- 目標：run 層級累加每個輸入欄之各步驟實際狀態、平穩化決策、群組轉換臂與回退、失敗群組。　檔案：`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`（Task 1.1 盤出之全部離開點；`_record_decision`、`_merge_decisions_from`、`failed_groups`）；`momentum/FeatureEngineering/feature_factory.py` 之 `_capture_stationarity_decisions`。　既有 caller／影響面：`stationarity_decisions()`、`stationarity_failure_reasons()` 之回傳格式不變（FF-STAT 呼叫者不受影響）。
- 改法：新增 run 層級之執行紀錄容器（不被 per-transform 重設；鍵＝(原生週期, L6.5 所見欄名)）；各離開點以契約值記狀態，成功亦記；平穩化關閉時亦記縮尾等步驟狀態；native 子實例之紀錄於丟棄前併回 owner；native 失敗回退記回退值於群組臂；ratio-unsafe passthrough 記終態；`_merge_decisions_from` 與 `_capture_stationarity_decisions` 改為同鍵且值不逐項相同即拋 `ProvenanceConflictError`（逐項相同則冪等）。公開存取：`FeaturePreprocessor.execution_records() -> Dict[Tuple[str, str], Dict[str, Any]]`（逐欄）與 `execution_groups() -> Dict[str, Dict[str, Any]]`（逐群組臂、回退、狀態、失敗原因）。`ProvenanceError` 系列加入 `NON_DEGRADABLE_ERRORS`（`feature_preprocessor.py:107-111`）；現行未重拋該集合之降級分支——包住 `_find_min_d` 之 `except Exception`（`:3543` 附近，否則紀錄錯誤會被轉成 d* 搜尋失敗而續跑）與 parallel→serial 回退（`:3780` 附近）——補「屬該集合即重拋」。parallel→serial 回退時，失敗嘗試已寫入之該批紀錄先整批撤回再由 serial 重記（紀錄以嘗試為單位，避免同鍵不同值誤觸衝突）。🔴 **同處之既有數值缺陷一併修正（b2 實作期發現）**：現行回退之 serial 重跑沿用失敗之 parallel 嘗試已就地改寫之資料框，replace 模式下失敗前已寫回之欄會被分數差分兩次（append 模式無害）；修正為 serial 自該批原始輸入重跑。此為唯一刻意之數值改動，只發生於 parallel 失敗之降級路徑，正常路徑值不變（§G 改前基準格不觸發該路徑）；驗收：replace 模式強制 parallel 失敗之輸出逐位元等於純 serial 輸出，mutation：serial 改回沿用已改寫之資料框 ⇒ 紅。`_get_non_stationary_columns`（`:4137` 附近）為 fracdiff 與 ADF 共用 ⇒ 加步驟參數以分別記錄。ADF 檢定拋例外時現行碼以 p=1.0 續行（`:3472` 附近、`_slow_path_parallel.py:119` 附近）⇒ 只記事件與狀態、不改行為（見 §N FFDSTAR-R3）。
- **驗證**：`pytest tests/feature_engineering/test_preprov_collect.py` 全綠：①單元（真實 kline 短窗之群組）每個輸入欄恰一筆、各步驟狀態皆屬契約；②native 成功與回退各一案，回退案之欄狀態來自回退路徑且群組臂為回退值；③衝突案拋 `ProvenanceConflictError`。mutation：刪任一離開點之紀錄呼叫 ⇒ ①紅；`_merge_decisions_from` 改回覆寫 ⇒ ③紅；縮尾成功不記 ⇒ ①紅。
- **邊界**：①群組全為 ratio-unsafe；②`eligible_columns` 為空；③parallel fracdiff 多 worker 結果合併（重複鍵拒收）；④append 模式衍生欄（`_fracdiff`／`_diff1`／`_diff2`）以父欄關聯記終態。
- **存活至**：本票交付後保留（Task 1.3／1.4 消費）。
- **覆蓋風險**：無。
- 不可做：不得改任何步驟之條件與數值；不得以 log 解析取得狀態。

**Task 1.3 — raw 紀錄檔、內容身分與 manifest（單一提交點）**
- 目標：writer 於安裝前寫紀錄檔與內容身分，manifest 合併為唯一提交點。　檔案：`momentum/FeatureEngineering/feature_storage.py` 之 `write_raw_from_registry_stream`、`_atomic_merge_feature_manifest_v2`、`_build_feature_manifest_v2`；新建 `momentum/FeatureEngineering/run_provenance.py`（序列化、內容身分、讀取驗證之純函式）。　既有 caller／影響面：`feature_factory.py:3880`；多標的 worker 與批次經同一 writer。
- 改法：①群組 part id 寫入 `group_manifest` 前碰撞即拋錯；②自前處理器紀錄＋dead-drop 結果＋群組 manifest 組逐欄紀錄表，窮盡性檢查（列之輸出欄名集合 ＝ manifest 群組欄聯集 ∪ dead-drop 欄，逐名、無重複）不過即拋錯；③每個群組檔與 row index 檔寫畢時計 sha256，組 `content_sha256`（契約定義之排序組成：相對路徑、欄名、列數、dtype、檔案 sha256、row index sha256）；④紀錄檔以 zstd parquet 寫入暫存 `provenance/` 並計其 sha256；row index 檔（`timestamps.parquet`；現行 `feature_storage.py:1138-1142` 於安裝前直接寫入 run 根）改為同樣先寫入暫存根；⑤對 run 根之任何寫入前，先將舊 manifest 之 raw 節點標為不完整（原子寫）；⑥安裝 raw、row index 檔與紀錄檔（各自先將舊檔移為備份），任一失敗且來源未刪 ⇒ 三者皆自備份回復並回復舊 manifest 節點；來源已刪 ⇒ 不回復、manifest 維持不完整（fail-closed）；⑦manifest 合併寫入 `content_sha256` 與 `provenance` 物件（含路徑、sha256、列數、契約版本、各步驟各狀態計數、群組表：臂、狀態、失敗原因）。任一步失敗 ⇒ 例外上拋、run 失敗。例外型別：檔案寫入失敗以原例外（如 `OSError`）上拋不包裝；part id 碰撞與紀錄鍵重複拋 `ProvenanceConflictError`；窮盡性不符拋 `ProvenanceExhaustivenessError`。刪 `:1224-1225` 之舊註解。
- **驗證**：`pytest tests/feature_engineering/test_preprov_writer.py` 全綠：①真實短窗生成後紀錄檔存在、sha256 等於 manifest 宣告；②窮盡性逐名；③`content_sha256` 以獨立實作（測試內自讀檔計算）重算相等；④注入紀錄檔寫入失敗（唯讀目錄）⇒ 生成失敗、manifest 無完整 raw 節點；⑤注入 manifest 合併失敗於安裝後 ⇒ run 不可被 `consumer="strict"` 讀為完整；⑤b 既有完整 run 重跑，於新 row index 寫出後、manifest 合併前注入 `OSError` ⇒ 舊 raw、舊 row index、舊 manifest 三者逐位元組回復，或 run 不可被讀為完整（不得出現舊特徵＋新時間軸）；⑥part id 碰撞案拋錯。mutation：`content_sha256` 漏 row index ⇒ 只改時間軸之案③紅；紀錄檔寫入改為吞例外 ⇒ ④紅；略過⑤ ⇒ ⑤紅。
- **邊界**：①dead-drop 開啟且有被剔欄；②多週期 run（同名不同週期之輸出欄以落盤名區分）；③多標的 worker 路徑；④平穩化關閉。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得改群組檔內容與命名；不得把紀錄檔列入 manifest 特徵群組。

**Task 1.4 — processed 紀錄檔（post-IC）**
- 目標：IC-first 之 post-IC 轉換同樣記逐欄狀態與臂。　檔案：`feature_preprocessor.py` 之 `transform_selected`；`feature_storage.py` 之 `write_processed`；`feature_factory.py:2986`。　既有 caller／影響面：`run_ic_first`。
- 改法：`transform_selected` 之 post-IC 前處理器沿用 Task 1.2 容器；回傳形態不變，紀錄經呼叫者實例之 `last_post_ic_execution()`（回 `execution_records()`／`execution_groups()` 同形之二元組）取得；`write_processed` 新增必填關鍵字參數 `execution`（該二元組），同 Task 1.3 ①–⑦ 之 processed 版（含 `processed_timestamps.parquet`〔現行 `feature_storage.py:1400-1405` 安裝前直接寫入〕納入同一暫存、備份與回復；驗證另含 Task 1.3 ⑤b 之 processed 版）；零選欄時紀錄為零列，manifest processed 節點 `provenance.summary.selected_columns == 0` 以區分「零選欄」與「未寫紀錄」。processed 紀錄之母體＝IC 選欄全集：寫入 processed 之欄記終態「已寫出」；選欄不在 raw（`feature_preprocessor.py:683` 附近）與入口剔除之 ratio-unsafe 欄（`:585` 附近）各記其終態，窮盡性＝processed 群組欄聯集 ∪ 上述兩類欄 ＝ 選欄全集（紀錄檔另一檔名、`content_sha256` 含 `processed_timestamps.parquet`）。processed 節點不覆寫 raw 節點之 `provenance`；raw 被刪後 raw 紀錄檔仍保留（位於 `provenance/`）。
- **驗證**：`pytest tests/feature_engineering/test_preprov_processed.py` 全綠：①真實短窗 IC-first 後 processed 紀錄逐選欄恰一筆、臂＝`polars`；②`cleanup_raw` 後 raw 紀錄檔仍在且 sha256 符合 manifest；③IC 選擇為空時 processed 紀錄為零列且狀態可區分「零選欄」。mutation：raw 紀錄檔改放 `raw/` 內 ⇒ ②紅。
- **邊界**：①選欄全不在 raw；②gaussian 開啟。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得改 post-IC 轉換之數值或臂選擇。

**Task 1.5 — 紀錄讀取函式**
- 目標：提供唯一之紀錄讀取入口供下游（第 9、11 步）使用。　檔案：`momentum/FeatureEngineering/feature_reader.py`（新增 `load_provenance_v2(symbol, tf, config_hash, artifact_kind)`，經 `_parse_manifest_file` 之單一 manifest 邊界）；`run_provenance.py`。　既有 caller／影響面：新建，無 caller。
- 改法：讀 manifest 宣告之紀錄檔、驗存在、路徑在 run 內、sha256 相符、契約版本相符，回 DataFrame；無 `provenance` 物件之舊 run 拋 `ProvenanceMissingError`；不符拋 `ProvenanceIntegrityError`。
- **驗證**：`pytest tests/feature_engineering/test_preprov_reader.py` 全綠：正常讀回與寫入表逐位元相同；竄改紀錄檔一位元組 ⇒ `ProvenanceIntegrityError`；舊 run ⇒ `ProvenanceMissingError`；路徑含 `..` ⇒ 拒讀。mutation：略過 sha256 比對 ⇒ 竄改案紅。
- **邊界**：①processed 與 raw 兩種 artifact；②raw 已刪之 run 讀 raw 紀錄。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：讀取端不得重算特徵檔雜湊（慢閘）。

### Phase 2 — IC 讀取保留 run 身分、快取依身分失效（依賴：Task 1.3）

**Task 2.1 — run 身分物件**
- 目標：IC 自同一次 manifest 解析取得 run 身分並隨資料傳遞。　檔案：`run_provenance.py`（`resolve_run_identity(manifest, artifact_kind)`）；`momentum/FeatureEngineering/feature_library.py`（新增 `load_with_identity(symbol, timeframe, config_hash=None, **同 load 之參數) -> Tuple[pd.DataFrame, RunIdentity]`；`load` 回傳形態不變，給既有 caller）。　既有 caller／影響面：`api/services/ic_analysis_service.py` 之 `_materialize_features_for_ic`。
- 改法：身分鍵依契約（symbol、tf、config_hash、feature_schema_hash、feature_naming_version、artifact_kind、content_sha256、provenance_sha256）；`feature_schema_hash` 取該 artifact 節點之值，節點無則取 manifest 頂層；**讀取一致性（第 3 批審碼 r1 增修）**：`load_with_identity`（及其共用之內部載入）全程只解析一次 manifest，欄位清單、群組檔讀取與 row index 讀取皆以該次解析之 manifest 與 run 目錄為準（不再各自重解析）；讀取結束時以 manifest 檔位元組 sha256 與起始時比對（單一確認點、比內容），不同即拋錯拒讀（讀取期間同 run 被重生或替換），不得以任一份身分標記另一份資料；缺 `content_sha256` 之舊 run 身分標 `legacy`。身分物件在一切輸出中之鍵名統一為 `ff_run_identity`。
- **驗證**：`pytest tests/feature_engineering/test_preprov_identity.py` 全綠：身分取值與 manifest 逐鍵相等；同一次 `load` 內 manifest 解析次數不因本 Task 增加（以計數 monkeypatch 斷言）。mutation：身分改取第二次解析之 manifest 且其間 manifest 被替換 ⇒ 不一致案紅。
- **邊界**：①`config_hash` 未指定（latest 解析後才定身分）；②舊 run。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：`api/` 不得自組身分。

**Task 2.2 — ingest 快取依身分失效**
- 目標：IC ingest h5 與 `_meta.json` 只在身分相符時沿用。　檔案：`api/services/ic_analysis_service.py` 之 `_materialize_features_for_ic`、`_ic_handoff_h5_current`、`_write_features_h5`。　既有 caller／影響面：IC 分析服務全部入口。
- 改法：交接 h5 於 orchestrator 讀取之同一位置（`ic_filter_orchestrator.py:5848` 讀 `group.attrs["metadata_json"]`，寫入端寫於該 group 屬性）寫 `metadata_json`，其內 `ff_run_identity` 為 run 身分；`_meta.json` 同鍵；沿用條件＝h5 與 `_meta.json` 皆帶與本次相同之身分且命名世代現行；否則兩者一併重寫；身分為 `legacy` ⇒ 不沿用。快取檔名保留可讀前綴，`latest` 一律以解析後身分判定。呼叫端自帶 `features_path`（`_write_ic_meta_json`，`ic_analysis_service.py:3355`）之路徑非讀自特徵產出，`ff_run_identity` 寫 `null` 並於報告標示來源為外部檔，不得冒充 run 身分。
- **驗證**：`pytest tests/api/test_preprov_ingest_cache.py` 全綠：①同身分第二次呼叫沿用（不重寫，以 mtime 與寫入計數斷言）；②真實短窗 run 重生而值改變（隔離資料副本中改一根 K 線）⇒ h5 與 meta 皆重寫且 orchestrator 讀得之 `metadata_json` 身分為新值；③舊格式快取（無身分屬性）⇒ 重寫。mutation：沿用條件拿掉 `content_sha256` ⇒ ②紅；只重寫 h5 不重寫 meta ⇒ ②紅。
- **邊界**：①快取目錄不存在；②h5 損毀（OSError）⇒ 重寫。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得以 mtime 或檔案大小代替身分。

**Task 2.3 — IC-first JSON 快取身分**
- 目標：`ic_selected_features_*.json` 之沿用須值身分相符。　檔案：`momentum/Analysis/ic_engine.py` 之 `CACHE_IDENTITY_FIELDS`、`_request_identity`、`_build_data_fingerprint`。　既有 caller／影響面：`compute_ic_from_l7_raw`。
- 改法：身分欄加 `content_sha256`（自 manifest raw 節點取，raw 已刪時 manifest 仍在）；缺即拒用；`_build_data_fingerprint` 之 `source_checksum` 來源改為 `content_sha256`（manifest 無 `source_checksum` 鍵）。
- **驗證**：`pytest tests/momentum/Analysis/test_preprov_ic_cache.py` 全綠：同身分沿用；`content_sha256` 不同 ⇒ 拒用並拋既有 `ICCacheRawUnavailableError`；舊 JSON 無該欄 ⇒ 拒用。既有 `tests/momentum/Analysis/test_icfirstalign_cache.py` 全綠（斷言不放寬）。mutation：自 `CACHE_IDENTITY_FIELDS` 移除新欄 ⇒ 不同身分案紅。
- **邊界**：①raw 已刪且 manifest raw 節點無 `content_sha256`；②threshold 不同而其餘相同（仍沿用）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得放寬既有十欄之任一欄。

**Task 2.4 — IC 輸出帶 run 身分**
- 目標：報告、倖存者、API 結果可追溯讀到之 run。　檔案：`momentum/Analysis/ic_filter_orchestrator.py`（報告 metadata、倖存者 provenance 組裝）；`momentum/Analysis/contracts/ic_survivor_contract.json`（`provenance_keys` 加 `ff_run_identity`、`version` +1）；`momentum/Analysis/survivor_contract.py`；`api/services/ic_analysis_service.py`（結果透傳）。　既有 caller／影響面：倖存者讀取端（`docs/IC_QUANT_GAP_REGISTRY.md` 所列消費者）須接受新版本。
- 改法：同一 run 身分物件寫入報告 metadata 與倖存者 provenance；倖存者 `config_hash`（IC 設定雜湊）語意不變。契約版本 +1 之連動：`survivor_contract.py:281` 之舊版訊息判斷改讀契約版本常數而非字面 2；既有斷言版本為 2 之測試（`tests/momentum/Analysis/test_survivor_contract.py:56,176,190,617`）改斷言新版本（測試改動依 2026-10-17 裁定登記審清單）；`build_survivor_output` 之新參數須為必填，其呼叫者（orchestrator 與既有測試之 `_build_kwargs`）同步。
- **驗證**：`pytest tests/momentum/Analysis/test_preprov_survivor_identity.py` 全綠：真實短窗 IC 分析之報告與倖存者 `ff_run_identity` 等於 Task 2.1 身分；倖存者契約驗證器拒收缺該鍵之新版本輸出；既有倖存者契約測試全綠。mutation：倖存者改寫入 ingest 快取檔之舊身分 ⇒ 身分相等案紅。
- **邊界**：①事件型路徑（`_run_event_label_stages`）同樣帶身分；②IC 選擇為空。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得改倖存者既有鍵之語意。

### Phase 3 — 真實資料驗收與輸出重量（依賴：Phase 1、2）

**Task 3.1 — 整合驗收與結構重凍**
- 目標：真實 kline 全格驗紀錄與實際執行一致、值不變、IC 快取正確失效。　檔案：`tests/feature_engineering/test_preprov_acceptance.py`；`tests/_golden/preprov/`；結構重凍之凍結檔（Task 1.6 所列）。　既有 caller／影響面：凍結檔之結構項。
- 改法：§V 格子逐格單行程串行跑；值指紋對 `tests/_golden/preprov/pre_change_fingerprints.json` 逐位元比；結構凍結項依 §G 重凍並出差異收據。
- **驗證**：`pytest tests/feature_engineering/test_preprov_acceptance.py` 全綠（§V oracle ①–⑥）；受影響凍結測試全綠；重凍收據 `tests/_golden/preprov/refreeze_receipt.json` 列出之差異路徑只含 `provenance/` 與 manifest 新鍵（測試斷言之）。
- **邊界**：見 §V 邊界目錄。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得重凍值指紋；不得以合成 fixture 代替真實 kline。

**Task 3.2 — 輸出增量重量**
- 目標：以真實生成量紀錄檔與 manifest 增量，與核可估算對照。　檔案：`tests/_golden/preprov/output_size.json`；量測腳本 `scripts/preprov_output_size.py`。　既有 caller／影響面：無。
- 改法：對 Task 3.1 各格及一個全特徵設定之 run（若本機可跑；否則以 Task 3.1 最大格外推並明示）量紀錄檔位元組、manifest 增量、讀取時間。
- **驗證**：腳本 rc=0，收據含逐格絕對位元組、佔 run 百分比、讀取秒數；全特徵 run 紀錄檔合計 > 2.6 MB（估算兩倍）⇒ 主委白話報使用者再核可。
- **邊界**：①小 run 百分比失真 ⇒ 同報絕對值；②多標的逐標的報；③任一 artifact 缺 `provenance` 指標、紀錄檔不存在或 parquet metadata 不可讀 ⇒ 寫錯誤收據並 rc=1，不以 0 累計。
- **存活至**：本票交付後保留為收據。
- **覆蓋風險**：無。
- 不可做：不得以「檔很小」略過與核可估算之對照。

## §V 驗證策略與邊界測試目錄
- **格子**（真實 kline、短窗、逐格單行程串行）：🔴 **前處理 mode 兩值皆須涵蓋**——生產預設為 replace（`feature_config.py` `mode: str = "replace"`），既有測試輔助多為 append；replace 才會走 numba 快速臂、shard 串流等路徑。故另設 replace 格：1h 單週期平穩化開＋縮尾開、1h 主＋12h 訓練週期，其 numba／shard／split 臂與回退值須於驗收實際產出（不得因格子只用 append 而列 `_unreachable`）。以下格除另註外為 append：單週期 1h；1h 主＋12h 訓練週期（使 native-tf 子實例路徑實際執行）；多標的 worker（兩標的；worker 不帶起訖日、全史、平穩化關，只驗 oracle ①④⑥——平穩化與縮尾 oracle ②③ 由單標的格承擔，writer 與前處理器為同一實作）；平穩化開＋縮尾開；平穩化關＋縮尾開；前處理總開關關；含 ratio-unsafe 群組；dead-drop 開啟；IC-first（含 `cleanup_raw`）。
- **oracle**（皆不讀紀錄自證）：①窮盡性——紀錄輸出欄名集合 ＝ manifest 群組欄聯集 ∪ dead-drop 欄，逐名；②`d` 獨立重算——取紀錄之 `d` 以 `_frac_diff_ffd` 對同校準前史＋公開段重算，與落盤值依 schema dtype 逐位元相等；③縮尾狀態——`applied` 之欄以同參數獨立縮尾重算等於落盤值，`ratio_unsafe` 終態之欄落盤值等於 L6.5 前值，縮尾關閉格無任何 `applied`；④內容身分——測試內自讀檔獨立重算 `content_sha256` 相等；⑤IC 快取——同身分沿用、值改變之重生必重建且報告身分為新值；⑥值不變——公開值指紋與改前基準逐位元相同。
- **mutation**（各 Task 已列者彙總，Task 3.1 以 monkeypatch 對真實格重跑）：刪縮尾成功紀錄；`d` 寫固定值；回退路徑不記；子實例併回改覆寫；略過 dead-drop 終態；紀錄檔列入特徵群組；`content_sha256` 漏 row index；ingest 沿用條件拿掉身分；IC-first 快取身分移除新欄；紀錄寫入吞例外。每個 mutant 須由對應 oracle 轉紅。
- **測試層級**：單元＋真實 kline 整合＋凍結對照；可 `pytest tests/feature_engineering/...` 獨立跑，不需 `run_api.py`。
- **防假綠**：既有測試斷言 diff 不放寬；測試刪改依 2026-10-17 裁定登記審清單。
- **估時**（本機 8 GB）：每格短窗生成約 1–5 分鐘（PROBEWINSOR 同型格實測量級），全格約 30–60 分鐘；超過 30 分鐘之跑開跑前列格數×估時報使用者。
- **邊界目錄**：空 DF（零選欄）✔ Task 1.4／全 NaN 欄 ✔ Task 1.2 邊界②／重複鍵 ✔ Task 1.2、1.3／寫入失敗與晚期失敗 ✔ Task 1.3／竄改與路徑逃逸 ✔ Task 1.5／舊 run 與舊快取 ✔ Task 1.5、2.2、2.3／並發寫：單 run 單寫者（既有 manifest 鎖），✗。

## §R 回退
- 每 Phase 獨立 commit、可單獨 revert；Phase 2 revert 後 IC 回到現行快取行為（含現存缺陷）；Phase 1 revert 後新 run 無紀錄，既有讀取不受影響（D6）。
- 值指紋任一改變 ⇒ 不合併。

## §N N/A 登記與殘留

### N/A
- 無。

### 殘留
- **FFDSTAR-R1 既有 7 個共用 d* 快取檔之來源 run 不明** — `為何現在不做: user-ruling:2026-08-05 使用者定死「修正只考慮以後，不把舊錯誤包回來」`；觸發：使用者要求回溯查證某既有 run 之 d*；登記處：本 SPEC §N。本票之後新 run 之 d* 以 run 內紀錄為準，共用快取只作快取。
- **FFDSTAR-R2 `/api/v1/features/generate` 回之 `task_id` 於任務查詢端點查無** — `為何現在不做: needs-research:API 任務登記路徑是否為既知設計（屬 api/ 任務登記，與本票之 run 紀錄與 IC 身分無資料依賴）`；觸發：下一次動 `api/services/feature_factory_service.py` 之任務登記或前端依賴該端點時；登記處：本 SPEC §N。
- 舊編號之「決策 148 欄對 L1＋L2 候選」：由 Task 3.1 oracle ① 直接回答，於本票收案時關閉，不再列殘留。
- **FFDSTAR-R3 ADF 檢定拋例外時以 p=1.0 視為非平穩續行**（`feature_preprocessor.py:3472` 附近、`_slow_path_parallel.py:119` 附近）— `為何現在不做: needs-research:該行為改為 fail-closed 或保留屬平穩化判定之數值政策（改之即改輸出值，違本票不改值之約束），須以真實資料量測例外發生率後定`；本票先使其可見（逐欄事件與狀態）；觸發：Task 3.1 驗收格或任一真實 run 紀錄出現該事件；登記處：本 SPEC §N。
- **FFDSTAR-R4 快速臂與 pandas 臂之邊界行為不一致**（zscore 窗清單為空時快速臂以 100 照做、未知縮尾 method 快速臂當 quantile 而 legacy 臂拋錯；盤點草稿所揭）— `為何現在不做: blocked-by:全票排序第 8 步 NUMVIEW（post-IC 正式臂政策：統一或具名保留，docs/TICKET_ORDER.md:42）`；本票只記實際所走之臂；觸發：NUMVIEW 開工；登記處：本 SPEC §N。
- **FFDSTAR-R5 `tests/feature_engineering/test_ffname_refreeze.py::test_k2_sidecar_per_name_equal[failopen]` 恆紅**（`k2_artifacts_unavailable`：FF-NAME 依名比對之 sidecar 存於 FF-NAME session 之 scratchpad，已刪；本票改動前即紅、無 `bytes_unbound`，第 4 批審碼 r1 三家判非本票 blocking）— `為何現在不做: needs-research:該檢查依賴不入版控之暫存 sidecar，修法（以精簡依名摘要入版控或重產 sidecar；後者需 FF-NAME 新舊碼全窗對證約 3.5–5 小時）須先定，屬 FF-NAME 驗收設計而非本票紀錄功能`；觸發：下一次動 failopen 凍結或 FF-NAME 依名比對工具時；登記處：本 SPEC §N、白話說明/還沒做的事.md。
- **FFDSTAR-R6 多週期 run 之 manifest `generation_metadata` 無 `column_set_reasons`**（單週期由 `feature_factory._stable_start_metadata` 寫入；多週期 failopen 實跑之診斷收據 handoffs/run_receipts/ffdstar_b4_failopen_diag/README.md）— `為何現在不做: needs-research:FFSTAT §C 欄集合差異收據於多週期是否應合併各週期剔除原因屬 FF-STAT 範圍；本票之逐欄終態與 dead-drop 已由紀錄檔與群組表涵蓋，不依賴該鍵`；觸發：多週期 run 之欄集合差異收據被消費或 FF-STAT 相關票開工；登記處：本 SPEC §N、白話說明/還沒做的事.md。
- R3 觸發核對（2026-10-20）：三次全特徵 BTCUSDT 12h run（含兩次平穩化開）之紀錄檔皆無 `adf_test_error` 事件，未觸發。

## §K 本 SPEC 註冊之 fact-key

> 下列區塊由 `scripts/fact_keys.json` 生成，禁手改。逐欄紀錄欄位與值集之唯一真相源為契約 JSON，以下只列落點與身分之定案。

### K-1 紀錄落點與身分

<!-- BEGIN GENERATED: ffdstar-receipt-schema -->
| 序 | 欄 | 型別／值集 | 說明 |
|---|---|---|---|
| 010 | 紀錄檔落點 | run 目錄內 `provenance/` 子目錄；raw 與 processed 各一檔（檔名定義於契約 JSON） | 不放 `raw/` 內——IC-first 於 processed 落盤後刪整個 raw（`feature_factory.py:2997-3004`）；不放共用目錄——須與 run 同生命週期 |
| 020 | 紀錄檔格式 | zstd 壓縮 parquet，每個輸出欄一列（寬表：各步驟一欄） | 使用者 2026-10-19 核可之存法（準確、檔小、讀快）；全特徵 run 估約 +1.3 MB |
| 030 | manifest 新鍵 | 每個 artifact 節點之 `content_sha256` 與 `provenance` 物件（鍵定義於契約 JSON） | manifest 只放路徑、sha256、列數、契約版本、各步驟各狀態計數、群組表；不內嵌逐欄紀錄 |
| 040 | 提交點 | manifest 合併為唯一提交點；安裝前先使舊 raw 節點不完整 | 任一步失敗 ⇒ run 失敗、不可被讀為完整 |
| 050 | 內容身分 `content_sha256` | 排序之（相對路徑、欄名、列數、dtype、檔案 sha256）＋ row index 檔 sha256 之 sha256 | 與 `config_hash`（設定）、`feature_schema_hash`（欄集合）正交，三者不得互相代替；紀錄檔 sha256 不入內容身分 |
| 060 | run 身分物件 | 鍵定義於契約 JSON；自同一次 manifest 解析取得 | IC ingest 快取、交接 h5 `metadata_json`、IC-first JSON 快取、報告、倖存者、API 結果共用；缺 `content_sha256` 之舊 run 標 `legacy`、快取不沿用 |
| 070 | 讀取端驗證 | 宣告檔存在、路徑在 run 內、紀錄檔 sha256 相符 | 不在每次讀取重算特徵檔雜湊（慢閘） |
<!-- END GENERATED: ffdstar-receipt-schema -->

### K-2 值集來源與約束

<!-- BEGIN GENERATED: ffdstar-skip-reasons -->
| 序 | 值 | 語意 |
|---|---|---|
| 010 | 值集唯一來源 | 各步驟狀態、群組轉換臂與回退、終態之封閉值集只定義於 `momentum/FeatureEngineering/contracts/run_provenance.json`（SPEC Task 1.1）；本表與測試不另列舉 |
| 020 | 值樣式 | 每個值合 `^[a-z][a-z0-9_]*$`；說明文字不得作值 |
| 030 | 值之碼證 | 每個值附 `_sources`（至少一個 `path:line` 實際離開點）；無離開點之值不得存在，每個離開點須有對應值；驗收未產出之值須列於契約 `_unreachable` 並附碼證理由 |
| 040 | 紀錄母體 | 逐欄紀錄之輸出欄名集合 ＝ manifest 群組欄聯集 ∪ dead-drop 欄（逐名、無重複）；平穩化決策欄非空之列 ＝ 本 run 實際進入平穩化步驟之輸入欄 |
<!-- END GENERATED: ffdstar-skip-reasons -->
