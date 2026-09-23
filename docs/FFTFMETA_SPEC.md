# FF-TFMETA：多週期 run 之 completeness 由 MultiTF producer 一次形成 — SPEC

> 來源 PLAN/診斷：`docs/FFDEFECT_DECISION.md` 第二節（缺陷 B；定性輪 `handoffs/reconcile/20260921-ffdefect-x-consult-r1/synth.md`）　|　日期：2026-09-23　|　對應 TODO：`docs/manifests/FFTFMETA.json`（五類落點 manifest；本 SPEC 定案後依 TODO_GENERATION_PROMPT 覆寫既有樣本）
> 版本：v1（主委起草，待三家對抗審）

## §RISK 風險分級
- **大小**：大（CLAUDE.md 任務分派規則：命中 a、b）。
- **命中高風險原則**：(a) 資料品質 metadata——`feature_manifest.json` 之 completeness 欄為下游判定 run 是否完整之依據；(b) 跨模組共用路徑——`feature_storage.py`／`feature_factory.py`／`multi_tf_generator.py` 三檔之 L7 persist 鏈，另經 `result.metadata` 流入 `api/services/feature_factory_service.py` 之 `task_record.json`。
- 不命中 (c)：只對新 run 生效，每 Phase 可單獨 revert，無資料遷移。不命中 (d)：不改任何特徵值、欄名、列數。
- RISK-HIT: a,b

## §A 假設與待使用者確認
- **已驗證事實**（4 條 FACT-RECEIPT，皆附 `.py` 路徑與行號）：
  - FACT-RECEIPT: `jq -c '{present_timeframes,expected_timeframes,failed_timeframes,quality_status}' data_cache/features/ETHUSDT/1h/d9935491cea49e8cada481a8bf9487d6/feature_manifest.json` → 印出 `{"present_timeframes":["1h"],"expected_timeframes":["1h"],"failed_timeframes":[],"quality_status":"complete"}`（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `jq -c '.metadata | {present_timeframes,skipped_timeframes,expected_timeframes,failed_timeframes,tr:.config_used.timeframes.training}' <同 run>/task_record.json` → 印出 `{"present_timeframes":["1h","12h"],"skipped_timeframes":[],"expected_timeframes":null,"failed_timeframes":null,"tr":["1h","12h"]}`（主委 實跑 2026-09-23）——健康多週期 run 之 task record **缺** `expected_timeframes`／`failed_timeframes`（`_apply_failed_timeframe_metadata` 無失敗即 return）。
  - FACT-RECEIPT: `grep -n 'self.layer_results\[' momentum/FeatureEngineering/feature_factory.py` → 印出 `:574` 與 `:625` 兩處以 layer 名為鍵賦值，全檔唯一重設點為 `:298`（`generate` 入口）（主委 實跑 2026-09-23）⇒ MultiTF 逐週期呼叫 `_execute_layer1_6_preserve_dtype` 時，`factory.layer_results` 被最後處理之週期覆寫；manifest 之 layer completeness 反映「最後一個週期」而非全部週期。
  - FACT-RECEIPT: `grep -n 'skipped_tfs\|failed_layers.extend' momentum/FeatureEngineering/timeframe/multi_tf_generator.py` → 三條路徑（`_generate_multi_tf_cgsa`、`_generate_multi_tf_cgsa_parallel`、`_generate_multi_tf_legacy`）皆於呼叫 L7 persist **之前**已收齊 `skipped_tfs` 與以 `"L<n>:<tf>"` 限定之 `failed_layers`（主委 實跑 2026-09-23）⇒ canonical 物件可在 persist 前形成，不需寫後 patch。
- **待使用者確認**：待確認：無
- **已確認結果**：2026-09-21 使用者「那命名缺陷和timeframe缺陷，應該是要修吧 你跟委員先研究是真缺陷看是要怎麼修」（定性輪判真缺陷，決策檔 B-1～B-4）；2026-08-05 使用者「面向未來不溯及既往」（只對新 run 生效、不回填）；2026-09-23 使用者離線前「有問題你跟委員討論共識決定」。

## §C 約束
- 解耦 7 條：`momentum/` 不 import `api/`；本票 `api/services/feature_factory_service.py` **不改**（它整包寫 `result.metadata`，修 producer 即自動正確）。
- 不改任何特徵值、欄名、欄數、列數、檔案集合、輸出大小；只改 completeness 欄之值與 `result.metadata` 同名鍵。
- 權威來源（決策檔 B-4，codex 修正）：canonical＝**ordered training config（`MultiTFGenerator._training_tfs`）＋ skip／failure 集合**；registry group id 之週期前綴**只作 diagnostic cross-check**，不得成為權威。
- 決策檔禁令：不得在 storage 端由 primary tf 猜多週期集合；不得在 manifest 寫完後只 patch metadata。
- 欄位名集合沿用既有單一真相源 `feature_storage.COMPLETENESS_FIELD_NAMES`，**不新增欄位**。
- 單週期 run（`generate` 直走、不經 MultiTF）之 manifest 值不得改變（`[timeframe]`）。

## §G Golden / Baseline
- **feature/kline 條件**：適用（改 FF persist 鏈）。以真實 `data_cache/feature_klines/kline_cache.h5`、沿用 `tests/feature_engineering/ff_truncation_mr_helpers.py` 之 `_run_generation` 建多週期（primary `1h`、training `["1h","12h"]`）小窗 run；禁合成 fixture。
- **凍結時機 / reference**：動工前以當下 HEAD 跑一次，存 `tests/_golden/fftfmeta/baseline.json`（run 參數、群組檔名集合 sha256、每群組 parquet 之資料位元組 sha256、manifest 全文去除 completeness 欄與時間戳後之 sha256）。
- **通過條件（可證偽）**：改後同參數重跑 ⇒ 群組檔名集合、每群組資料 sha256、去除 completeness 欄後之 manifest sha256 **全等**；completeness 欄之差異**恰為** §P Task 3.1 所定之值。任一不等即列出該檔與 diff＝FAIL。

## §P Phase 與依賴

### Phase 1 — 純函式：canonical completeness 物件（依賴：無）
**Task 1.1 — 週期完整性建構**
- 目標：由 ordered training tfs 與失敗週期集合形成週期三欄。　檔案：`momentum/FeatureEngineering/feature_storage.py` 新增 `build_timeframe_completeness(expected_tfs: Sequence[str], failed_tfs: Sequence[str]) -> Dict[str, List[str]]`　既有 caller／影響面：新建無 caller。
- 改法：`expected`＝`expected_tfs` 依首次出現序去重；`failed`＝`failed_tfs` 依 expected 之序排列、去重；`failed ⊄ expected` ⇒ `ValueError`；`expected` 為空 ⇒ `ValueError`；`present`＝expected 中不在 failed 者（保序）。回傳 `{"expected_timeframes","present_timeframes","failed_timeframes"}`。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k timeframe_completeness` 全綠；五條等式各一支具名測試：expected＝ordered training tfs、present＝expected − failed、failed ⊆ expected、expected＝present ∪ failed（集合相等且 present 保序）、failed 為空時 present＝expected。
- **邊界**：①`failed_tfs` 含不在 expected 之週期 ⇒ `ValueError`；②`expected_tfs` 含重複（`["1h","12h","1h"]`）⇒ expected＝`["1h","12h"]`；③全部週期失敗 ⇒ present＝`[]`（由呼叫端既有「All training timeframes skipped」先行拋錯，本函式不另擋）；④`failed_tfs` 順序與 expected 相反 ⇒ 輸出依 expected 序。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得解析 group id；不得讀 config 物件（只收兩個序列）。

**Task 1.2 — 合併層完整性與週期完整性**
- 目標：把週期三欄與跨週期之層失敗併入既有 layer completeness，得單一 canonical 物件。　檔案：`feature_storage.py` 之 `resolve_completeness_meta`（加 keyword-only 參數 `timeframe_completeness: Optional[Dict[str, List[str]]] = None`、`cross_tf_failed_layers: Sequence[str] = ()`）　既有 caller：`feature_storage.py:1171`、`:1298`。
- 改法：參數皆為預設值時行為逐位元組不變（單週期路徑）。有 `timeframe_completeness` 時以其三欄覆寫週期欄；`failed_timeframes` 非空 ⇒ `failure_reasons` 依序追加 `timeframe:<tf>`，且 `quality_status` 由 `complete` 降為 `partial`（`unknown`／`empty_selection` 不動）。有 `timeframe_completeness` 時（即 MultiTF 路徑），L1–L6 之層失敗改以 `cross_tf_failed_layers`（MultiTF 逐週期收集之 `"L<n>:<tf>"`，涵蓋 primary）為權威：`failed_layers` 中 L1–L6 之條目＝該清單（已限定形，去重保序；`qualify_failed_layer_ids` 對已限定條目不變），`present_layers` 移除任一週期失敗之 `L<n>`，`failure_reasons` 中 L1–L6 之條目＝`L<n>:<tf>:layer_failed`；L6.5／L7 之條目仍取自 `layer_results`（其於 primary 週期執行，歸屬正確）。清單非空 ⇒ `quality_status` 由 `complete` 降為 `partial`。
- FACT-RECEIPT: `sed -n 14,26p momentum/FeatureEngineering/utils/layer_ids.py` → 印出 `_QUALIFIED_LAYER_ID = re.compile(r"^L\d+:\d+[hdm](?:$|:)")` 與「已限定條目保持不變」之分支（主委 實跑 2026-09-23）⇒ 限定形條目經 `feature_factory.py:3309-3314` 之 qualify 不被改寫。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k resolve_completeness` 全綠——單週期 golden：`resolve_completeness_meta(lr, "1h")` 對既有測試之輸入與改前 `==`；四情況（健康多週期／skip／failed／單週期）各一支具名測試斷言完整物件相等。
- **邊界**：①`override_quality_status="empty_selection"` 與 failed 週期並存 ⇒ 仍為 `empty_selection`；②`layer_results` 為空（`default_completeness_meta`）而有 `timeframe_completeness` ⇒ 週期欄取 canonical、`quality_status` 維持 `unknown`；③`cross_tf_failed_layers` 含 primary 已失敗之層 ⇒ 不重複。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得改 `build_completeness_meta_from_layer_results` 之簽名與單週期輸出；不得新增 completeness 欄位名。

### Phase 2 — persist 鏈傳遞（依賴：Phase 1）
**Task 2.1 — storage writer 傳遞**
- 目標：兩個 writer 接收並使用 canonical 輸入。　檔案：`feature_storage.py` 之 `write_raw_from_registry_stream`（`:733`）、`write_raw`（`:705`）→ `_write_l7_v2_artifact`（`:1274`）　既有 caller：`feature_factory.py` 之 CGSA 與 frame persist。
- 改法：三者加同名 keyword-only 參數並原樣傳入 `resolve_completeness_meta`；預設值時行為不變。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k writer_timeframe_completeness` 全綠：以 `tmp_path` 寫 artifact，`manifest["present_timeframes"] == canonical["present_timeframes"]`（三欄與 `quality_status` 同）；未傳參數時 manifest 與改前逐位元組 `==`。
- **邊界**：①registry-stream 路徑既有 artifact 已存在（`.previous-raw-*` 備份）時 manifest 合併仍取新值；②`allow_empty` 導致 `empty_selection` 時週期欄仍為 canonical。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得在 writer 內由 `tf` 推導多週期。

**Task 2.2 — factory persist 傳遞，且 result.metadata 與 manifest 同源**
- 目標：factory 之三個 persist 入口接收 canonical 輸入，manifest 與 `result.metadata` 之 completeness 由**同一次** `resolve_completeness_meta` 呼叫產生。　檔案：`feature_factory.py` 之 `_layer7_raw_from_cgsa_pipeline`（`:3144`；`:3271` 建 metadata）、`_layer7_validate_and_persist`（`:3516`；`:3573`）及其委派之 `_layer7_validate_and_persist_cgsa`（`:3388`）　既有 caller：`feature_factory.py:400`、`:427`、`multi_tf_generator.py:324`、`:617`、`:1384`。
- 改法：加同名 keyword-only 參數；`:3271`／`:3573` 改呼叫 `resolve_completeness_meta(self.layer_results, timeframe, timeframe_completeness=…, cross_tf_failed_layers=…)`，把同一 dict 傳入 storage writer 並寫入 `result.metadata`。
- **驗證**：`pytest tests/feature_engineering/test_failopen_producer.py -k persist_completeness_same_source` 全綠：打樁 storage 捕捉傳入之 completeness，對 `COMPLETENESS_FIELD_NAMES` 每鍵 `captured[k] == result.metadata[k]`。
- **邊界**：①單週期 `generate`（`:400`／`:427`）不傳參數 ⇒ `result.metadata` 與 manifest 皆為 `[timeframe]`；②persist=False 時 `result.metadata` 仍含 canonical 週期欄。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得在 persist 之後另行覆寫 manifest。

**Task 2.3 — 品質降級之 manifest 同步（🔴 範圍待 r1 委員裁定）**
- 目標：`result.metadata.quality_status` 與 manifest `quality_status` 一致（決策檔 B-4「task_record 同名欄在有該檔時亦須相等」）。　現況：`feature_factory.py` 之 NaN／inf 門檻降級（`:3062` 附近）與 L6.5 失敗降級（`_apply_preprocessing_degradation_metadata`，`:3072`；呼叫點 `:3317`、`:3474`、`:3622`）於 storage 寫完 manifest **之後**只改 `result.metadata` ⇒ 同一 run manifest `complete`、task record `partial`。
- FACT-RECEIPT: `grep -n '_apply_preprocessing_degradation_metadata(\|metadata\["quality_status"\] = "partial"' momentum/FeatureEngineering/feature_factory.py` → 印出 `:3062`、`:3080` 兩處降級賦值與 `:3317`、`:3474`、`:3622` 三處呼叫，皆在 storage writer 返回之後（主委 實跑 2026-09-23）
- 主委提案：併入本票——storage writer 另收門檻（`max_inf_ratio`／`max_nan_ratio`）於串流統計完成、manifest 合併前判定；L6.5 失敗旗標於串流中已知者一併納入；factory 端改讀 writer 回傳之最終 completeness，不再事後改寫。若委員判定無乾淨落點，改列 §N 殘留（`needs-research`）並另立票。
- **驗證**：`pytest tests/feature_engineering/test_failopen_manifest.py -k degradation_in_manifest` 全綠：打樁 NaN 比例超門檻之群組 ⇒ `manifest["quality_status"] == result.metadata["quality_status"] == "partial"` 且 `failure_reasons` 相等。
- **邊界**：①門檻未設（`None`）⇒ 行為不變；②L6.5 降級與週期失敗並存 ⇒ `failure_reasons` 兩者皆有、順序固定。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得於 manifest 寫完後再改 manifest。

### Phase 3 — MultiTF producer（依賴：Phase 2）
**Task 3.1 — 三條 MultiTF 路徑於 persist 前形成 canonical 物件**
- 目標：`_generate_multi_tf_cgsa`、`_generate_multi_tf_cgsa_parallel`、`_generate_multi_tf_legacy` 於呼叫 L7 persist 前以 `build_timeframe_completeness(self._training_tfs, skipped_tfs)` 形成週期物件，連同 `failed_layers` 傳入 factory persist。　檔案：`momentum/FeatureEngineering/timeframe/multi_tf_generator.py`（`:324`、`:617`、`:1384` 之呼叫與其後 `:344-346`、`:638-640`、`:1396-1398` 之事後寫入）　既有 caller：`generate_multi_tf`（`:51`）。
- 改法：persist 後之 `result.metadata` 週期鍵一律取自 persist 回傳之 canonical 值（`skipped_timeframes` 保留，值＝`failed_timeframes`）；刪除 `_apply_failed_timeframe_metadata` 開頭之 `if not failed_timeframes: return` 不對稱（健康 run 亦寫齊三欄）；`run_status`／`quality_status` 為 `partial` 之既有語意保留。`_present_timeframes` 由 `build_timeframe_completeness` 取代。
- **驗證**：`pytest tests/test_multi_tf_generator.py -k canonical_completeness` 全綠——打樁 factory 之 MultiTF 測試，四情況（健康 `["1h","12h"]`／12h skip（`allow_partial_timeframes=True`）／12h 失敗／單週期 `["1h"]`）manifest 與 `result.metadata` 之三欄與 `quality_status` 皆等於預期且兩者相等；§G 真實 run 改後 manifest `present_timeframes==expected_timeframes==["1h","12h"]`、`failed_timeframes==[]`。
- **邊界**：①primary 週期失敗 ⇒ 既有 `ValueError("Primary timeframe data missing…")` 行為不變；②training 序為 `["12h","1h"]`（primary `12h`）⇒ expected 依 training 序；③parallel 路徑 worker 回報 error 且 `allow_partial_timeframes=False` ⇒ 既有拋錯不變。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得以 `_present_timeframes()` 或 group id 當週期權威；不得保留 persist 後之週期覆寫。

**Task 3.2 — 週期集合之 diagnostic cross-check**
- 目標：CGSA 兩路徑於 persist 前比對 registry 中實際出現之週期集合與 canonical `present_timeframes`。　檔案：`multi_tf_generator.py` 新增私有 `_crosscheck_present_timeframes(registry, present)`。
- 改法：registry 各 group 之來源週期取自結構化欄位 `ColumnGroup.timeframe`（`momentum/FeatureEngineering/core/column_group.py:78`；不解析 group id 字串）；`{g.timeframe for g in registry.iter_all()}` 與 canonical `present_timeframes` 之集合不等 ⇒ `RuntimeError`（fail-closed，於 L7 persist 之前）。
- FACT-RECEIPT: `sed -n 76,86p momentum/FeatureEngineering/core/column_group.py` → 印出 `group_id: str`、`layer: LayerSource`、`timeframe: str`、`data_source: str` 等欄（主委 實跑 2026-09-23）
- **驗證**：`pytest tests/test_multi_tf_generator.py -k crosscheck_present_timeframes` 全綠：打樁 registry 使 `12h` 無任何 group（`present == ["1h","12h"]`）⇒ `RuntimeError`；健康 ⇒ 不拋。
- **邊界**：①某週期全部 group 被 dead-drop（dead-drop 於 L7 寫入時才發生，cross-check 在其前）⇒ 不影響；②legacy 路徑無 registry ⇒ 不適用（見 §N）。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得把 cross-check 結果寫入 manifest 新欄位；不得以其結果修正 canonical 物件。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用（RISK-HIT 含 a）。至少三個 mutant 必使具名測試紅：①恢復 `if not failed_timeframes: return`（健康 run 缺 expected／failed）；②storage 改回 `[timeframe]`（多週期 manifest 只剩 primary）；③`resolve_completeness_meta` 忽略 `cross_tf_failed_layers`（非 primary 週期之層失敗時 manifest 仍 `complete`）。
- 測試層級：單元（Phase 1）、打樁整合（Phase 2、3.1、3.2）、§G 真實小窗 run 對照。可獨立 `pytest tests/feature_engineering/…` 跑。
- **防假綠**：`tests/feature_engineering/test_failopen_manifest.py::test_completeness_fields` 等既有斷言不得放寬；其單週期期望值不變。
- **邊界目錄**：重複 timeframe（Task 1.1②）、空集合（1.1③）、亂序（1.1④）、既有 artifact 覆寫（2.1①）。

## §R 回退
- 三 Phase 各自獨立 commit，可單獨 revert；只對新 run 生效，無資料遷移；§G 不等 ⇒ 不 merge。不設 feature flag（行為修正非實驗，依「驗過就別預設關閉」）。

## §N N/A 登記
- (c)(d) 不命中：見 §RISK。
- 殘留：既有 18 個 run 之 manifest 不回填 — `為何現在不做: user-ruling:2026-08-05 面向未來不溯及既往`；觸發：無（舊 run 依 task-record authority 使用）；登記處：`docs/FFDEFECT_DECISION.md` B-4 相容性。
- Task 3.2 於 legacy 路徑不適用：legacy 無 CGSA registry，其合併框之週期資訊只在欄名字串內，解析欄名即違反 §C 權威規則；legacy 之 canonical 物件仍由 Task 3.1 形成，僅無 cross-check。
