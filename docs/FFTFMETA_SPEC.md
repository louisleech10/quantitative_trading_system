# FF-TFMETA：多週期 run 之 completeness 由 MultiTF producer 一次形成 — SPEC

> 來源 PLAN/診斷：`docs/FFDEFECT_DECISION.md` 第二節（缺陷 B；定性輪 `handoffs/reconcile/20260921-ffdefect-x-consult-r1/synth.md`）　|　日期：2026-09-24　|　對應 TODO：`docs/manifests/FFTFMETA.json`（五類落點 manifest；本 SPEC 定案後依 TODO_GENERATION_PROMPT 覆寫既有樣本）
> 版本：v3（r2 收斂 `handoffs/reconcile/20260924-fftfmeta-x-review-r2/synth.md`：Task 1.3 記憶體欄隨 flush 往返、parallel worker 回傳六層狀態、resume 閘不改而以可 resume 組態驗收、IC-first 保留根之全部 completeness 與品質欄、§G 加降級單週期 reference）；v2（r1 收斂 `handoffs/reconcile/20260924-fftfmeta-x-review-r1/synth.md`：層失敗集合對齊 `FAILOPEN_LAYER_FAILURE_STATUSES`、resume 保存逐週期層狀態、legacy 路徑契約改為 meta.json、IC-first 二次寫入保留週期欄、品質降級同步定範圍、registry 迭代介面更正）

## §RISK 風險分級
- **大小**：大（CLAUDE.md 任務分派規則：命中 a、b）。
- **命中高風險原則**：(a) 資料品質 metadata——`feature_manifest.json` 之 completeness 欄與 `quality_status` 為下游判定 run 是否完整、可否重用之依據；(b) 跨模組共用路徑——`feature_storage.py`／`feature_factory.py`／`multi_tf_generator.py`／`core/column_group_registry.py` 之 persist 與 resume 鏈，另經 `result.metadata` 流入 `api/services/feature_factory_service.py` 之 `task_record.json`。
- 不命中 (c)：只對新 run 生效，每 Phase 可單獨 revert，無資料遷移。不命中 (d)：不改任何特徵值、欄名、欄數、列數。
- RISK-HIT: a,b

## §A 假設與待使用者確認
- **已驗證事實**（7 條 FACT-RECEIPT，皆附 `.py` 路徑與行號）：
  - FACT-RECEIPT: `jq -c '{present_timeframes,expected_timeframes,failed_timeframes,quality_status}' data_cache/features/ETHUSDT/1h/d9935491cea49e8cada481a8bf9487d6/feature_manifest.json` → 印出 `{"present_timeframes":["1h"],"expected_timeframes":["1h"],"failed_timeframes":[],"quality_status":"complete"}`（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `jq -c '.metadata | {present_timeframes,skipped_timeframes,expected_timeframes,failed_timeframes,tr:.config_used.timeframes.training}' <同 run>/task_record.json` → 印出 `{"present_timeframes":["1h","12h"],"skipped_timeframes":[],"expected_timeframes":null,"failed_timeframes":null,"tr":["1h","12h"]}`（主委 實跑 2026-09-23）——健康多週期 run 之 task record 缺 `expected_timeframes`／`failed_timeframes`。
  - FACT-RECEIPT: `grep -n 'self.layer_results\[' momentum/FeatureEngineering/feature_factory.py` → 印出 `:574`、`:625` 以 layer 名為鍵賦值，唯一重設點 `:298`（主委 實跑 2026-09-23）⇒ MultiTF 逐週期執行時 `factory.layer_results` 被最後處理之週期覆寫。
  - FACT-RECEIPT: `grep -n 'skipped_tfs\|failed_layers.extend' momentum/FeatureEngineering/timeframe/multi_tf_generator.py` → 三條路徑皆於 L7 persist 前已收齊 `skipped_tfs` 與 `"L<n>:<tf>"` 之失敗層（主委 實跑 2026-09-23）；但收集器 `_collect_failed_layer_ids` 只收 `LayerStatus.layer_failed`（r1 codex／grok）。
  - FACT-RECEIPT: `sed -n 504,519p momentum/FeatureEngineering/feature_storage.py` → `LAYER_NAME_TO_ID` 只含 L1–L6；`FAILOPEN_LAYER_FAILURE_STATUSES＝{layer_failed, all_engines_failed, dependency_failed}`（主委 實跑 2026-09-24）
  - FACT-RECEIPT: `grep -n '_preprocessing_applied = ' momentum/FeatureEngineering/feature_factory.py` → 只於 `_execute_l65_with_degradation`（`:696`／`:700`）設定；該函式呼叫點 `feature_factory.py:421`（單週期 frame）與 `multi_tf_generator.py:1371`（legacy），皆在 L7 persist 之前；CGSA 兩路徑不經此函式（主委 實跑 2026-09-24）
  - FACT-RECEIPT: `grep -n 'write_raw(\|write_processed(' momentum/FeatureEngineering/feature_factory.py` 之 IC-first 段 → `:2179`（`write_raw`）與 `:2247`（`write_processed`）以 `layer_results=self.layer_results`、不帶週期資訊再寫同一 run 之 manifest（r1 grok P1-03；主委 讀檔 2026-09-24）
- **待使用者確認**：待確認：無
- **已確認結果**：2026-09-21 使用者「那命名缺陷和timeframe缺陷，應該是要修吧 你跟委員先研究是真缺陷看是要怎麼修」（定性輪判真缺陷，決策檔 B-1～B-4）；2026-08-05 使用者「面向未來不溯及既往」（只對新 run 生效、不回填）；2026-09-23 使用者離線前「有問題你跟委員討論共識決定」。

## §C 約束
- 解耦 7 條：`momentum/` 不 import `api/`；`api/services/feature_factory_service.py` **不改**（`_persist_task_record` 以 `summary.get("metadata")` 整包寫入，修 producer 即自動正確）。
- **特徵資料檔、欄名、欄數、列數、檔案集合不變**；metadata JSON（manifest、`meta.json`、task record）因既有欄位值改變、task metadata 補齊 `expected_timeframes`／`failed_timeframes`、降級 run 之 manifest 品質欄改為與 task record 同值而大小可變；**不新增 manifest 鍵**（`quality_thresholds` 等降級細節仍只在 task record）——允許變動之 JSON 路徑見 §G，實測大小差寫入收據（r1 codex P2-07）。
- 權威來源（決策檔 B-4）：週期集合之 canonical＝ordered training config（`MultiTFGenerator._training_tfs`）＋ skip／failure 集合；registry 群組之週期只作 diagnostic cross-check。
- 決策檔禁令：不得在 storage 端由 primary tf 猜多週期集合；不得在 manifest 寫完後只 patch metadata；persist 之後不得再改寫 `COMPLETENESS_FIELD_NAMES`、`quality_status`、`run_status`（r1 composer P2-01）。
- 欄位名集合沿用既有單一真相源 `feature_storage.COMPLETENESS_FIELD_NAMES`，**不新增 manifest 欄位**；registry 工作 manifest（中間產物）新增逐週期層狀態見 Task 1.3。
- 層失敗之判定一律用 `FAILOPEN_LAYER_FAILURE_STATUSES`（單週期與 MultiTF 同一謂詞）。
- 單週期 run（`generate` 直走）且**未降級**者，manifest 值不得改變（`[timeframe]`）；降級之單週期 run 其 manifest `quality_status`／`failure_reasons` 依 Task 2.3 與 task record 對齊，屬預期變更。

## §G Golden / Baseline
- **feature/kline 條件**：適用。以真實 `data_cache/feature_klines/kline_cache.h5`、沿用 `tests/feature_engineering/ff_truncation_mr_helpers.py` 之 `_run_generation`（`:320-365`）建多週期（primary `1h`、training `["1h","12h"]`）CGSA 小窗 run；禁合成 fixture。
- **凍結時機 / reference**：動工前以當下 HEAD 跑一次，存 `tests/_golden/fftfmeta/baseline.json`：run 參數；群組檔名集合 sha256；每群組以 pyarrow 讀出之每欄 `dtype`、`shape`、NaN mask sha256、以 little-endian 原生 dtype 序列化之值 sha256；manifest 與 task record 之 canonical JSON（`sort_keys=True`、`ensure_ascii=False`、`separators=(",", ":")`）去除下列**允許變動路徑**後之 sha256。
- **允許變動路徑（封閉集）**：manifest 根與 `artifacts.raw`（及 `artifacts.processed`，若存在）之 `expected_timeframes`、`present_timeframes`、`failed_timeframes`、`expected_layers`、`present_layers`、`failed_layers`、`failure_reasons`、`quality_status`、`run_status`，以及 `created_at`、`updated_at`、`generation_metadata.generation_time`；task record 之 `metadata` 下同名鍵、`generation_time`、`persisted_at`。
- **通過條件（可證偽）**：改後同參數重跑 ⇒ 群組檔名集合、每群組每欄四個 hash、去除允許路徑後之兩份 canonical JSON sha256 **全等**；允許路徑之改後值**恰為** Task 3.1 所定（健康 run：週期三欄＝`["1h","12h"]`／`["1h","12h"]`／`[]`，`quality_status`＝`complete`）。任一不等即列出路徑與 diff＝FAIL。
- **降級單週期 reference（r2 codex P2-03）**：同一小窗、單週期 `1h`（不經 MultiTF），以設定 `max_nan_ratio=0.0` 觸發 NaN 門檻降級（真實資料必含 warmup NaN），改前改後各跑一次：特徵資料四 hash 與去除允許路徑後之 canonical JSON 全等；允許路徑逐鍵預期＝manifest 根與 `artifacts.raw` 之 `quality_status`／`run_status` 由 `complete` 變 `partial`、`failure_reasons` 等於 task record 之 `failure_reasons`（含 `nan_ratio=…>max_nan_ratio=…`），task record 之 `quality_status`、`failure_reasons`、`quality_thresholds` 改前改後相等；manifest、task record 之 JSON 位元組大小差寫入收據。

## §P Phase 與依賴

### Phase 1 — 純函式與 resume 狀態（依賴：無）
**Task 1.1 — 週期完整性建構**
- 目標：由 ordered training tfs 與失敗週期集合形成週期三欄。　檔案：`momentum/FeatureEngineering/feature_storage.py` 新增 `build_timeframe_completeness(expected_tfs: Sequence[str], failed_tfs: Sequence[str]) -> Dict[str, List[str]]`　既有 caller／影響面：新建無 caller。
- 改法：`expected`＝`expected_tfs` 依首次出現序去重；`failed`＝`failed_tfs` 依 expected 之序、去重；`failed ⊄ expected` ⇒ `ValueError`；`expected` 為空 ⇒ `ValueError`；`present`＝expected 中不在 failed 者（保序）。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k timeframe_completeness` 全綠；五條等式各一支具名測試：expected＝ordered training tfs、present＝expected − failed、failed ⊆ expected、expected＝present ∪ failed（集合相等且 present 保序）、failed 為空時 present＝expected。
- **邊界**：①`failed_tfs` 含不在 expected 之週期 ⇒ `ValueError`；②`["1h","12h","1h"]` ⇒ expected＝`["1h","12h"]`；③全部週期失敗 ⇒ present＝`[]`（呼叫端既有「All training timeframes skipped」先拋錯）；④`failed_tfs` 逆序 ⇒ 輸出依 expected 序。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得解析 group id；不得讀 config 物件。

**Task 1.2 — 合併層完整性與週期完整性**
- 目標：把週期三欄與跨週期層失敗併入 layer completeness，得單一 canonical 物件。　檔案：`feature_storage.py` 之 `resolve_completeness_meta`（加 keyword-only 參數 `timeframe_completeness: Optional[Dict[str, List[str]]] = None`、`cross_tf_layer_failures: Sequence[str] = ()`）　既有 caller：`feature_storage.py:1171`、`:1298`。
- 改法：參數皆為預設值時行為逐位元組不變。有 `timeframe_completeness` 時（MultiTF 路徑）：週期欄取其三欄；`failed_timeframes` 非空 ⇒ `failure_reasons` 追加 `timeframe:<tf>`、`quality_status` 由 `complete` 降為 `partial`；L1–L6 之層失敗以 `cross_tf_layer_failures`（條目形 `L<n>:<tf>:<reason 或 status 值>`，涵蓋 primary 與 resume 讀回者）為權威——`failed_layers`＝其 `L<n>:<tf>` 前綴（去重保序；`qualify_failed_layer_ids` 對已限定形不改寫）、`present_layers` 移除任一週期失敗之 `L<n>`、`failure_reasons` 追加各條目，非空 ⇒ `complete` 降為 `partial`。`expected_layers` 取任一週期之啟用層聯集（Task 1.3 保存）。`LAYER_NAME_TO_ID` 只含 L1–L6，本 Task 不涉 L6.5／L7。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k resolve_completeness` 全綠——單週期：`resolve_completeness_meta(lr, "1h")` 對既有測試之輸入與改前 `==`；四情況（健康多週期／skip／failed／單週期）與三種失敗狀態（`layer_failed`／`all_engines_failed`／`dependency_failed` 各於非 primary 週期）各一支具名測試斷言完整物件相等。
- **邊界**：①`override_quality_status="empty_selection"` 與 failed 週期並存 ⇒ 仍 `empty_selection`；②從未執行任何層且 registry 無該週期群組（`layer_results` 為空、無 Task 1.3 狀態）⇒ 週期欄取 canonical、`quality_status` 維持 `unknown`；③同一 `L<n>` 於兩週期失敗 ⇒ `failed_layers` 各列一條限定形、`present_layers` 移除一次。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得改 `build_completeness_meta_from_layer_results` 之簽名與單週期輸出；不得新增 manifest 欄位名；不得把原因改寫成固定字面。

**Task 1.3 — resume 保存逐週期層狀態（r1 codex P1-03）**
- 目標：CGSA resume 跳過之週期仍能提供其 L1–L6 狀態與失敗原因。　檔案：`momentum/FeatureEngineering/core/column_group_registry.py`（registry 工作 manifest，即既有 resume checkpoint）、`multi_tf_generator.py` 之兩條 CGSA 路徑與 `_tf_worker_entry`　既有 caller：`_has_resume_checkpoint_for_timeframe`（`multi_tf_generator.py:148`、`:407`、`:477`）。
- 改法：①registry 新增記憶體欄 `layer_status_by_tf: Dict[str, Dict[str, Tuple[str, str]]]`（週期 → L1–L6 → (status, reason)），`record_layer_status(tf, statuses)` 以整組取代該週期舊條目；`write_manifest()` 之 payload 帶此欄，`resume_from_manifest()` 讀回同一記憶體欄（r2 grok P1-02：只讀進區域變數會於下一次 flush 被整檔重寫抹除）。②循序路徑：每週期 L1–L6 執行後、`write_manifest()` 前記錄六層（含非失敗狀態）。③parallel 路徑：`_tf_worker_entry` 回傳增加六層 `(status, reason)`；parent 於該週期群組註冊成功後、`:586` 之 `write_manifest()` 前記錄；註冊失敗 rollback 時清掉該週期條目；primary 於 `:466` flush 前記錄（r2 codex P1-02、composer P2-01）。④stale alignment 拆除群組後重跑之週期，以新六層記錄取代舊條目。⑤resume 跳過之週期自此欄讀回，併入 `cross_tf_layer_failures` 與 `expected_layers`；該週期無條目、或條目未涵蓋其已啟用之 L1–L6 ⇒ 缺證據 ⇒ `quality_status`＝`unknown`（不得解為無失敗）。⑥**resume 閘不改**：`_prepare_cgsa_registry`（`feature_factory.py:1034`）於有 config hash 時，L7 manifest 缺席或不可快取即不 resume、層全數重算，無層狀態流失；本 Task 只保證「確實 resume 時」層狀態不流失（r2 codex／grok P1-01 指出之不可達，改以可 resume 之組態驗收，見驗證）。
- **驗證**：`pytest tests/test_cgsa_resume.py -k layer_status` 全綠——以可 resume 之組態（`FFACT_CGSA_WORK_DIR` 指定工作目錄，gate 只驗工作 manifest 存在）：第一次 run 令 12h 之 L2 `dependency_failed`（`allow_partial_layers=True`）並於 persist 前中止；resume 後斷言確實命中跳過分支（log 或 spy），manifest `failed_layers` 含 `L2:12h:<原因>` 之前綴、`quality_status == "partial"`；循序與 parallel 各一；中途再 flush 一次（第三個週期寫入）後條目仍在；以無 `layer_status_by_tf` 之舊 checkpoint resume ⇒ `quality_status == "unknown"`；parallel 註冊失敗 rollback ⇒ 該週期無條目。
- **邊界**：①全部週期皆由 checkpoint 跳過 ⇒ 層狀態全數讀回，健康者 `quality_status == "complete"`；②checkpoint 之 `layer_status_by_tf` 含 training 以外之週期 ⇒ 忽略並記 warning；③條目只涵蓋部分層 ⇒ `unknown`。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得另建 sidecar 檔；不得以 registry 群組之 `group.layer` 回推層狀態。

### Phase 2 — persist 鏈傳遞與品質降級同步（依賴：Phase 1）
**Task 2.1 — storage writer 傳遞與 IC-first 保留**
- 目標：writer 接收並使用 canonical 輸入；後續不帶週期資訊之寫入不得覆蓋既有週期欄。　檔案：`feature_storage.py` 之 `write_raw_from_registry_stream`（`:733`）、`write_raw`（`:705`）、`write_processed`、`_write_l7_v2_artifact`（`:1274`）、`_build_feature_manifest_v2`（`:1773`）　既有 caller：`feature_factory.py` 之 CGSA、frame 與 IC-first（`:2179`、`:2247`）。
- 改法：各 writer 加同名 keyword-only 參數並原樣傳入 `resolve_completeness_meta`；未傳 `timeframe_completeness` 與 `cross_tf_layer_failures` 且既有 manifest 根已有週期三欄時，`_build_feature_manifest_v2` 保留既有根之六個 `COMPLETENESS_FIELD_NAMES` 欄、`failure_reasons`、`quality_status`、`run_status`，不執行根賦值（`:1839-1847`）；新 artifact 仍寫入 `artifacts.<kind>`（r1 grok P1-03、r2 grok P1-03）；全新 run 無既有 manifest ⇒ 單週期預設不變。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k writer_timeframe_completeness` 全綠：以 `tmp_path` 寫 artifact，`manifest["present_timeframes"] == canonical["present_timeframes"]`（三欄與 `quality_status` 同）；先寫多週期（含 12h 層失敗與 Task 2.3 降級）再以 IC-first 形（不帶參數）各寫一次 raw 與 processed ⇒ 根之六欄、`failure_reasons`、`quality_status`、`run_status` 皆 `==` 寫入前值；全新單週期未傳參數 ⇒ 與改前 `==`。
- **邊界**：①registry-stream 路徑既有 artifact 已存在（`.previous-raw-*`）⇒ 合併取新值；②`allow_empty` 導致 `empty_selection` ⇒ 週期欄仍為 canonical。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得在 writer 內由 `tf` 推導多週期。

**Task 2.2 — factory persist 傳遞，manifest 與 result.metadata 同源**
- 目標：factory 之 persist 入口接收 canonical 輸入，manifest 與 `result.metadata` 之 completeness 由同一個物件產生。　檔案：`feature_factory.py` 之 `_layer7_raw_from_cgsa_pipeline`（`:3144`；`:3271`）、`_layer7_validate_and_persist`（`:3516`；`:3573`）及其委派之 `_layer7_validate_and_persist_cgsa`（`:3388`）　既有 caller：`feature_factory.py:400`、`:427`、`multi_tf_generator.py:324`、`:617`、`:1384`。
- 改法：加同名 keyword-only 參數；writer 回傳最終 completeness（含 Task 2.3 降級），factory 以該回傳值寫 `result.metadata`，不再自行由 `self.layer_results` 另建；非 CGSA 路徑（無 manifest writer）以同一函式產生之物件寫 `result.metadata`，再由既有 `save_factory_output` 寫 `meta.json`。
- **驗證**：`pytest tests/feature_engineering/test_failopen_producer.py -k persist_completeness_same_source` 全綠：打樁 storage 捕捉寫入之 completeness，對 `COMPLETENESS_FIELD_NAMES` 每鍵與 `quality_status` 斷言 `captured[k] == result.metadata[k]`。
- **邊界**：①單週期 `generate`（`:400`／`:427`）不傳參數 ⇒ `result.metadata` 與 manifest 皆為 `[timeframe]`；②persist=False ⇒ `result.metadata` 仍含 canonical 週期欄。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得在 persist 之後另行覆寫 manifest 或 completeness 鍵。

**Task 2.3 — 品質降級於 manifest 合併前定案（r1 三家；範圍由委員證據定）**
- 目標：`result.metadata.quality_status` 與 manifest `quality_status` 一致（決策檔 B-4）。　現況：`_apply_runtime_quality_gate`（`feature_factory.py:3037`；呼叫 `:3319`、`:3475`、`:3623`）與 `_apply_preprocessing_degradation_metadata`（`:3072`；呼叫 `:3317`、`:3474`、`:3622`）於 writer 返回後只改 `result.metadata`。
- 改法：①把兩者之判定抽成 `feature_storage.py` 內純函式 `apply_quality_degradation(meta, *, inf_ratio, nan_ratio, max_inf_ratio, max_nan_ratio, preprocessing_applied) -> Dict`（不 import factory）；②門檻之 `None` 於 factory 既有政策層先解析為實值（`_default_max_nan_ratio`；inf 預設 `0.0`）再傳入，writer 只收實值；③CGSA stream writer 以其於 merge 前已算之 validation 比率（`feature_storage.py:1137-1171`）呼叫該函式，把結果併入 completeness 後才 `_atomic_merge_feature_manifest_v2`；④frame 路徑（單週期與 legacy）：L6.5 旗標與比率皆於 persist 前已知，factory 以同一函式先判再存；⑤factory 刪除 writer 返回後之事後降級呼叫，改讀 writer 回傳之最終物件；`quality_thresholds` 與既有 `failure_reasons` 語意不變。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k degradation_in_manifest` 全綠：打樁 NaN 比例超門檻 ⇒ `manifest["quality_status"] == result.metadata["quality_status"] == "partial"` 且 `failure_reasons` 相等；frame 路徑 L6.5 失敗 ⇒ `meta.json` 與 `result.metadata` 皆含 `L6.5:preprocessing_failed`。
- **邊界**：①門檻由 `None` 解析 ⇒ 判定結果與改前 factory 事後判定相同（同輸入比對）；②L6.5 降級與週期失敗並存 ⇒ `failure_reasons` 兩者皆有、順序固定（週期→層→品質）。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得於 manifest 寫完後再改 manifest；CGSA 路徑不得臆造 L6.5 旗標（見 §N 殘留）。

### Phase 3 — MultiTF producer（依賴：Phase 2）
**Task 3.1 — 三條 MultiTF 路徑於 persist 前形成 canonical 物件**
- 目標：`_generate_multi_tf_cgsa`、`_generate_multi_tf_cgsa_parallel`、`_generate_multi_tf_legacy` 於 persist 前以 `build_timeframe_completeness(self._training_tfs, skipped_tfs)` 形成週期物件，連同跨週期層失敗傳入 factory persist。　檔案：`multi_tf_generator.py`（`:324`、`:617`、`:1384` 之呼叫；`:344-346`、`:638-640`、`:1396-1398` 之事後寫入；`_collect_failed_layer_ids`）　既有 caller：`generate_multi_tf`（`:51`）。
- 改法：`_collect_failed_layer_ids` 改用 `FAILOPEN_LAYER_FAILURE_STATUSES` 並保留原因，產出 `L<n>:<tf>:<reason 或 status 值>`（parallel worker 回傳同形）；persist 成功後**刪除**三處 `_present_timeframes` 賦值與 `_apply_failed_timeframe_metadata`／`_apply_failed_layer_metadata` 呼叫，不再寫 `COMPLETENESS_FIELD_NAMES`、`quality_status`、`run_status`（r1 composer P2-01）；`skipped_timeframes` 保留為 diagnostic 鍵，值＝`failed_timeframes`；`run_status` 於 canonical 物件中與 `quality_status` 同值。
- **legacy 路徑契約（r1 codex P1-04）**：legacy 經 `save_factory_output` 只寫 `features.h5` 與 `meta.json`、不產 manifest；本 Task 對 legacy 之驗收為 `meta.json` 之同名鍵 `==` `result.metadata`（同一 canonical 物件），不新增 manifest。
- **驗證**：`pytest tests/test_multi_tf_generator.py -k canonical_completeness` 全綠——打樁 factory，四情況（健康 `["1h","12h"]`／12h skip（`allow_partial_timeframes=True`）／12h 失敗／單週期 `["1h"]`）：CGSA 兩路徑之 manifest 與 `result.metadata`、legacy 之 `meta.json` 與 `result.metadata`，三欄與 `quality_status` 皆等於預期且兩兩相等；§G 真實 run 改後 manifest `present_timeframes == expected_timeframes == ["1h","12h"]`、`failed_timeframes == []`。
- **邊界**：①primary 週期失敗 ⇒ 既有 `ValueError("Primary timeframe data missing…")` 不變；②training 序 `["12h","1h"]`（primary `12h`）⇒ expected 依 training 序；③parallel worker 回報 error 且 `allow_partial_timeframes=False` ⇒ 既有拋錯不變。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得以 `_present_timeframes()` 或 group id 當週期權威；不得保留 persist 後之 completeness 覆寫。

**Task 3.2 — 週期集合之 diagnostic cross-check**
- 目標：CGSA 兩路徑於 persist 前比對 registry 中實際出現之週期集合與 canonical `present_timeframes`。　檔案：`multi_tf_generator.py` 新增私有 `_crosscheck_present_timeframes(registry, present)`。
- 改法：週期取自結構化欄位 `ColumnGroup.timeframe`（`core/column_group.py:78`）；`registry.iter_all()` 產出 `(group_id, group)` 二元組（同檔 `:1201`、`:1537` 既有拆包），集合＝`{group.timeframe for _, group in registry.iter_all()}`（r1 codex P1-01）；與 `present_timeframes` 之集合不等 ⇒ `RuntimeError`（fail-closed，L7 persist 前）。
- FACT-RECEIPT: `sed -n 76,86p momentum/FeatureEngineering/core/column_group.py` → 印出 `group_id: str`、`layer: LayerSource`、`timeframe: str` 等欄（主委 實跑 2026-09-23）
- **驗證**：`pytest tests/test_multi_tf_generator.py -k crosscheck_present_timeframes` 全綠：以真實 `ColumnGroupRegistry` 註冊群組（不以只回傳 group 之假 stub），使 `12h` 無群組（`present == ["1h","12h"]`）⇒ `RuntimeError`；健康 ⇒ 不拋。
- **邊界**：①dead-drop 於 L7 寫入時才發生，cross-check 在其前 ⇒ 不影響；②resume 讀回之週期群組亦計入。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得把 cross-check 結果寫入 manifest；不得以其結果修正 canonical 物件。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用（RISK-HIT 含 a）。至少五個 mutant 必使具名測試紅：①恢復 `if not failed_timeframes: return`；②storage 改回 `[timeframe]`；③`resolve_completeness_meta` 忽略 `cross_tf_layer_failures`；④`_collect_failed_layer_ids` 改回只收 `layer_failed`（`dependency_failed` 於 12h 時 manifest 仍 `complete`）；⑤恢復 writer 返回後之事後降級（manifest `complete`、metadata `partial`）。
- 測試層級：單元（Phase 1）、打樁整合（Phase 2、3）、resume 整合（Task 1.3）、§G 真實小窗 run 對照。可獨立 `pytest tests/feature_engineering/…`、`tests/test_multi_tf_generator.py`、`tests/test_cgsa_resume.py` 跑。
- **防假綠**：`tests/feature_engineering/test_failopen_manifest.py::test_completeness_fields` 等既有斷言不得放寬；其單週期期望值不變。
- **邊界目錄**：重複 timeframe（1.1②）、空集合（1.1③）、亂序（1.1④）、既有 artifact 覆寫（2.1①）、resume 全跳過（1.3①）、舊 checkpoint（1.3 驗證）。

## §R 回退
- 三 Phase 各自獨立 commit，可單獨 revert；只對新 run 生效，無資料遷移；registry 工作 manifest 新鍵為中間產物，舊版讀取時忽略；§G 不等 ⇒ 不 merge。不設 feature flag（行為修正非實驗，依「驗過就別預設關閉」）。

## §N N/A 登記
- (c)(d) 不命中：見 §RISK。
- 不適用：Task 3.2 於 legacy 路徑——legacy 不建立 CGSA registry，其週期只在欄名字串內（解析欄名違反 §C 權威規則）；legacy 之 canonical 物件仍由 Task 3.1 形成並寫入 `meta.json`（r1 grok P2-05）。
- 殘留：既有 18 個 run 之 manifest 不回填 — `為何現在不做: user-ruling:2026-08-05 面向未來不溯及既往`；觸發：無（舊 run 依 task-record authority 使用）；登記處：`docs/FFDEFECT_DECISION.md` B-4 相容性。
- 殘留：CGSA 路徑之 L6.5 預處理失敗未進 completeness — `為何現在不做: needs-research:CGSA 串流於 manifest 合併前，哪一個已產生之 run 級信號代表 preprocessing 失敗（_preprocessing_applied 只於 frame 路徑設定，CGSA 兩路徑不經 _execute_l65_with_degradation）`；觸發：研究得出信號後另立票；登記處：`docs/FFDEFECT_DECISION.md`（本票收案時補列）。
