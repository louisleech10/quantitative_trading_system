# Batch1 Follow-up SPEC/TODO Adversarial Review (Codex, V13)

日期：2026-06-12  
範圍：`docs/BATCH1_FOLLOWUP_SPEC.md`、`docs/BATCH1_FOLLOWUP_TODO.md`；背景 `docs/DSTAR_FRACDIFF_NONCGSA_FINDING.md`  
嚴格度：MAXIMUM；文件作者：Claude；reviewer：Codex（獨立重判）

## Verdict：有根本缺陷需重作

目前不可派工。核心缺陷不是文字潤飾，而是風險分級、N6/N3 的依賴設計、Golden oracle、schema 相容與驗收基線均未收斂。修補後應重新做至少一輪不同模型 adversarial review。

## §0 前提重判與 §A 逐條核實

| SPEC §A 陳述 | 判定 | 獨立證據 / 缺口 |
|---|---|---|
| N4：`_default_max_nan_ratio` 讀 `tests/_golden/failopen/max_nan_ratio.json`，檔案 296 bytes，讀取失敗會 raise | **fact-verified** | `momentum/FeatureEngineering/feature_factory.py:2790-2810`；`stat` 實測 296 bytes，SHA256=`dadc1da8...0189ee0b`。 |
| N4：production 部署沒有 `tests/` | **assumed** | SPEC 未附部署映像、package manifest 或 production filesystem 實測。repo 內也未找到 packaging 設定可證明 `_resources/*.json` 一定被發佈。 |
| N6：stream summary 的 validation 可能缺 `nan_ratio` | **fact-verified（實際為固定缺）** | `feature_storage.py:1127-1135` 建立 validation dict，沒有 `nan_ratio`；`feature_factory.py:3022,3079` 因而固定走 `1-coverage` fallback。 |
| N6：fallback 會把合法 warmup 誤標 partial | **assumed as observed behavior / code-supported hypothesis** | `feature_factory.py:3079` 與 artifact 門檻支持此因果，但 SPEC 沒附所稱「真實 run」的命令與輸出；依專案驗證保真度規則，不能標成已實測事實。 |
| N6：scan 路徑已有 warmup-aware ratio | **fact-verified** | `_scan_cgsa_registry_validation` 在 `feature_factory.py:2632-2768`，於 `:2692` 累加 `_abnormal_nan_count`，`:2733` 算 ratio，`:2767` 回傳。 |
| N7：multi-TF 產 `L{n}:{tf}`，manifest 產裸 `L{n}` | **fact-verified** | `multi_tf_generator.py:1464-1473`；`feature_storage.py:571-601`。 |
| N3：validator 寫死 252/63，L6.5 已 winsor 時跳過 | **fact-verified** | `feature_validator.py:179-209`。 |
| T5：production 中 `actual_timeframes` 僅三個 producer、無 momentum/api/frontend consumer | **fact-verified（限所述目錄）** | producer 在 `multi_tf_generator.py:327,619,1376`；獨立 `rg` 未見 production consumer。tests 有至少四個舊鍵引用，故不是全 repo 無 consumer。 |
| winsor 252 是 L6.5 預設，改 config 且預設不變可 byte-identical | **部分 fact / 部分 assumed** | `WinsorConfig.window=252`（`feature_config.py:165-171`）已核實；L6.5 `min_periods` 不是獨立 config，而由 `feature_preprocessor.py:151-158` 動態算 `min(window,max(20,window//4))`。validator 如何取得同一 config 尚未設計，故 byte-identical 結論未完整驗證。 |
| HANDOFF backlog 已由使用者拍板 | **not independently verifiable from code** | `HANDOFF.md:10-17` 只證明文件如此記載；review 不把 inter-agent artifact 自述升格為外部事實。此點不阻塞技術審查。 |

## Findings

### BLOCKING

1. **[BLOCKING][High] §RISK 將任務錯分為中型，違反專案自己的高風險 gate。**  
   證據：SPEC `§RISK` 原文「(a)(b)(c) 不直接命中」；但 N6 直接改 NaN quality gate 的觀測量，N3 改 winsor 數值參數來源，N7/T5 改持久化/回傳 metadata contract，且修改 `feature_factory.py`、`feature_storage.py`、`feature_validator.py`、`multi_tf_generator.py` 多個共用路徑。`CLAUDE.md` 明定命中 (a) 數值/資料品質或 (b) 跨模組共用路徑即為大任務。  
   失敗方式：以中型流程派工，跳過大型任務所需雙家族 adversarial、使用者決策文件與更完整資料正確性 gate。  
   修法：重分級為大；拆分純 metadata 與數值/quality-gate 任務，或整批走大任務流程。

2. **[BLOCKING][High] N6 的 fallback 規格互斥，無唯一可實作行為。**  
   證據：SPEC Task 1.2 原文同時要求「fallback 保留」、「fallback 觸發時不得用於 partial 判定升級」及「沿用 fail-closed 現狀」；TODO `1.2.2` 則明確要求沿用 `1-coverage` 現狀。現狀 `feature_factory.py:3074-3081` 會把 fallback 傳入 gate，可能升級為 partial。  
   失敗方式：實作者無論保留或停用 fallback 升級都會違反其中一條；空 summary 的驗收期望也不明。  
   修法：明定 missing `nan_ratio` 時是 hard error、partial、unknown 或僅 warning；對應狀態與測試只能選一套。

3. **[BLOCKING][High] N6 要求「reuse `_abnormal_nan_count`」但 producer 位於另一類別，依賴與 scope 未設計。**  
   證據：stream producer 是 `FeatureStorage.write_raw_from_registry_stream`（`feature_storage.py:733-1201`）；helper 是 `FeatureFactory._abnormal_nan_count`（`feature_factory.py:2773-2787`）。TODO 只說「實作端定位」，並禁止自寫算法；沒有 callback、protocol、shared utility 或允許新增檔案。  
   失敗方式：直接 import private factory 造成反向/循環依賴；複製算法違反 TODO；擴 scope 抽共用 helper 又違反派工檔案邊界。  
   修法：SPEC 先選定共享純函式的 ownership（含允許檔案、兩個 caller、測試），或顯式 callback injection；不可交給實作者臨場決定。

4. **[BLOCKING][High] N3 所稱「既有 config 注入點」不存在，`cfg` 與欄位位置未定義。**  
   證據：`FeatureValidator.__init__` 只有 `correlation_threshold`（`feature_validator.py:49-56`）；factory 固定 `FeatureValidator()`（`feature_factory.py:186-193`）；public factory 也固定無參數（`momentum/factories.py:217-218`）。TODO 卻指定 `cfg.get("winsor_window")` 並稱新參數不改函式簽名。既有真正 config 是 `FactoryConfig.preprocessing.winsorization.window`（`feature_config.py:165-171,231-247`），沒有 `winsor_min_periods` 欄。  
   失敗方式：實作者會任選 constructor state、`result.config_used`、新 validator config 或 FactoryConfig 欄位；不同選擇影響 API standalone validator、factory reuse 及 config hash。  
   修法：先定唯一來源與傳遞路徑，列出 `FeatureFactory`、`create_feature_validator`、`FeatureTaskService` 等 caller 的相容策略；明定 min_periods 是獨立欄位還是沿用 L6.5 的動態公式。

5. **[BLOCKING][High] Golden bootstrap 是可自我認證的 oracle，且 SPEC/TODO hash 定義不一致。**  
   證據：SPEC §G 要 `sha256(values.tobytes())`；TODO Task 1.0 改成 `sha256(np.nan_to_num(..., nan=-9e9).tobytes())`。TODO 又要求 baseline 不存在時由測試生成並 `pytest.skip("frozen")`；Phase Gate 將 skipped 視為非失敗。  
   失敗方式：baseline 可在錯誤實作之後生成，第一次 gate 仍綠；兩種 hash 算法使 oracle 不唯一。  
   修法：baseline 必須在實作 commit 前由獨立 freeze script/固定舊 commit 生成並 review；測試缺 baseline 應 fail，不得生成或 skip；統一 canonical value hash + NaN-mask hash 定義。

6. **[BLOCKING][High] 回歸 gate 的固定通過數已經錯誤。**  
   證據：SPEC `§V`/TODO `§B` 寫「維持 77 passed」；對文件列出的同一 bundle 實跑 pytest collection 得到 **78 items**（2026-06-12）。  
   失敗方式：嚴格照 gate 驗收時，健康 HEAD 也不可能符合「77 passed」；若只要求 exit 0，文件的量化條件又是假的。  
   修法：以當前 HEAD 完整跑完後凍結真實 pass/skip 數及 commit，或移除脆弱的固定數量，改以明確 node-id 清單與 exit code 驗收。

7. **[BLOCKING][High] N6 沒有真實 streaming producer 的保真驗收，違反專案明定的資料正確性規則。**  
   證據：SPEC §V 只要求「經 `_apply_runtime_quality_gate` 呼叫鏈」；該函式可用手工 summary/metadata 輕易假綠。真正缺鍵發生在 `FeatureStorage.write_raw_from_registry_stream` 的 post-transform/post-sanitize/post-dead-drop array（`feature_storage.py:915-948,1125-1135`）。既有 `test_failopen_producer.py:267-308` 也只直接呼叫 gate。  
   失敗方式：helper 測試綠，但真實 storage summary 仍缺鍵、分母錯誤或計算時點錯誤。  
   修法：至少一個測試須真跑 registry -> stream write -> returned summary -> factory metadata/gate，並斷言 leading/trailing warmup 與 mid-hole；若此處被視為 Feature Factory 資料正確性，依規範使用真實 kline 路徑而非只用 sanitized fixture。

### MAJOR

8. **[MAJOR][High] N7 是 schema 語義變更，卻無 version/migration/backward-compat 決策。**  
   證據：`failed_layers` 是 `raw_v2/processed_v2` completeness contract（`feature_storage.py:521-539`）；Task 1.3 將值由 `L3` 改為 `L3:12h`，並改 `failure_reasons` 格式，但保留同一 schema version。SPEC §N 卻稱「無 API/前端契約變更」，TODO 稱「純 ID 字串格式」。  
   失敗方式：新舊 run 在同一 schema version 下具有不同 value grammar；後續 consumer 無法可靠解析或比較。  
   修法：明定兼容策略：version bump + reader migration，或 reader 同時接受兩種格式並把 canonicalization 放在讀邊界；`expected_layers/present_layers` 是否也帶 tf 必須一併決策。

9. **[MAJOR][High] N7 round-trip gate 是同源自證，不能抓 producer/consumer contract 錯誤。**  
   證據：manifest 與 result metadata 都會經 `build_completeness_meta_from_layer_results`/同一改動來源；SPEC 只要求集合相等。  
   失敗方式：兩邊同時產出同一個錯誤格式仍通過；set 比較還會掩蓋順序與重複 ID。  
   修法：用獨立 golden grammar + 明確預期 list 驗證；加入舊 raw_v2 fixture 的讀取兼容測試與 mixed primary/secondary TF failure 測試。

10. **[MAJOR][High] N6 位於大資料 streaming hot path，文件錯稱「效能不適用」，沒有 memory/runtime gate。**  
    證據：TODO Phase Gate 原文「效能：不適用（無熱路徑變更）」；實際變更點 `_write_group` 對每個 post-transform array 執行，現有程式已建立 `nan_mask`（`feature_storage.py:938-943`）。若再直接呼叫目前 helper，會額外建立 `nan_mask`、`valid_mask`、argmax 與多個 per-column array（`feature_factory.py:2777-2787`）。  
    失敗方式：寬 group 產生額外 copy amplification，跨 8GB/16GB tier 可能 OOM 或顯著變慢。  
    修法：設計能重用現有 mask/按 shard 累計首尾有效位置的算法；加入至少 peak RSS 不回歸與代表性寬度 runtime gate。

11. **[MAJOR][High] N4 的 production resource 可用性未驗證，測試方案也沒有可注入 path。**  
    證據：SPEC 把「production 無 tests」列已驗證，但未附部署證據；TODO 又假設「本 repo 非 wheel 部署」。`_default_max_nan_ratio` 內 path 是 local variable（`feature_factory.py:2792`），所稱 monkeypatch `_resources` 不存在路徑沒有指定 injection point。  
    失敗方式：source checkout 測試綠，但容器/打包部署漏掉 JSON；或測試只能改真檔/patch `Path`，脆弱且可能污染並行測試。  
    修法：定義 module constant/resource loader（如 package resource API）並在 deployment artifact/最小安裝環境驗證；缺檔測試 patch loader/constant，不改真實 resource。

12. **[MAJOR][High] min_periods 語義與現有 L6.5 不一致，會造成兩條路徑 config 同名不同義。**  
    證據：TODO 固定預設 `winsor_min_periods=63`，但 L6.5 對 window=100 會由 `feature_preprocessor.py:155-158` 得到 25。`WinsorConfig` 只有 window，沒有 min_periods。  
    失敗方式：同一 `winsorization.window=100` 在 L6.5 與 validator 路徑裁剪起點不同，破壞 CGSA/non-CGSA 可比性。  
    修法：共用同一 resolver/公式，或新增同一 schema 欄位並讓兩條路徑都使用；Golden 必測至少 100 與小於 80 的 window。

13. **[MAJOR][Medium] T5 硬改鍵名雖無 production code consumer，仍缺 persisted task/result compatibility 檢查。**  
    證據：tests 至少在 `tests/test_multi_tf_generator.py:194`、`tests/feature_engineering/test_failopen_producer.py:263`、`tests/test_multi_tf_golden_equivalence.py:110`、`tests/test_primary_self_align_skip.py:127` 使用舊鍵；API 有 task record persistence/restore（`feature_factory_service.py:251-253,3878-3895`）。  
    失敗方式：舊 task record 仍只含 `actual_timeframes`，新 consumer/診斷若只看新鍵會失去資料。  
    修法：明確宣告舊 persisted result 是否需 read-time alias/migration；若確定無 consumer，增加兼容性不需要的證據與契約版本說明。

14. **[MAJOR][High] TODO 沒有可機檢的需求 ID 追溯，coverage gate 目前無法工作。**  
    證據：`coverage_check.sh` 對指定文件回報「manifest 內找不到任何 [X-N] 格式 ID」；TODO 首行的「6 Task 全覆蓋」是作者自述，非機械追溯。  
    失敗方式：後續修補或拆 Task 時容易掉 requirement，gate 無法偵測。  
    修法：建立扁平 requirement IDs，SPEC/TODO 每項雙向引用；重新跑 coverage check。

### MINOR

15. **[MINOR][High] N4「搬移而非複製」與實際要求保留兩份 byte-identical JSON 用語矛盾。**  
    證據：SPEC Task 1.1 同段寫「搬移而非複製語義」及「tests 原檔保留，新增 production 副本」。  
    後果：不影響核心設計，但可能讓實作者誤刪 golden。  
    修法：改稱「建立 production-owned canonical copy，test golden 保留為 oracle」。

16. **[MINOR][High] T5 的 grep-in-test 驗收耦合 repo layout，價值低於直接 contract tests。**  
    證據：TODO Task 1.5 要 subprocess `grep`。  
    後果：Windows/工具缺失或註解文字會造成假紅；不能證明 persisted compatibility。  
    修法：grep 留在 shell gate，pytest 只測三條真實 producer path 的 metadata contract。

### Suggestions

17. **[Suggestion][Medium]** 將此批拆為：N4 resource ownership、N6 quality metric、N3 winsor config、N7/T5 metadata schema四個可獨立回退批次。現在「同一測試檔所以合併」是排程便利，不是技術內聚。

18. **[Suggestion][Medium]** N6 可把 warmup-aware 統計抽成 storage/quality 共用純函式，輸入 ndarray、輸出結構化 counts（total/nan/abnormal/inf），讓 scan 與 stream 共用；但 ownership 與 memory budget 必須先寫進 SPEC，不能由 agent 自行發明。

## V13 §1 十類必查摘要

1. **矛盾/互斥**：有。N6 fallback；Golden hash；N4 搬移/複製。
2. **漏項/端到端**：有。N6 shared helper ownership；N3 config propagation/callers；N7 schema migration；T5 persisted records。
3. **不可測驗收**：有。77 passed 已失真；Golden 首跑 skip；N6 gate 可繞過真 storage path。
4. **可疑 quant 假設**：有。warmup 誤標未附真實 run；N3 min_periods 與 L6.5 分歧，會改特徵裁剪起點。
5. **過度工程**：無明顯 distributed/queue 類過度工程；但六項合包增加驗收耦合。
6. **OOM/並行**：有。N6 對寬 streaming array 增加 mask/argmax allocations，無 tier gate。
7. **Cache 正確性**：本批 d* cache 已抽出；N4 resource duplicate 有 drift gate但缺 packaging gate。無 cross-symbol cache 新問題。
8. **API/型別/相容**：有。N7/T5 metadata contract 改名/改 grammar，無 version/migration；N3 public factory caller 未盤點。
9. **測試品質**：有。Golden 自生成、N6 非真 producer、N7 同源 round-trip、固定 pass count 錯誤。
10. **Agent 可執行性**：有。N6/N3 都含「實作端定位/確認」且缺唯一設計，會逼 agent 越界猜測。

## V13 §2 範本錨點與空殼

- SPEC 有 §RISK/§A/§C/§G/§P/§V/§R/§N，形式錨點齊。
- §G 不是空表，但 Golden bootstrap 邏輯不可信，且只覆蓋預設 winsor 小 fixture與 N4 scalar；未保護 N6 真 stream、N7 schema、T5舊資料兼容。
- Task 1.2/1.4 的「實作端定位/確認」屬邏輯空殼：關鍵 ownership/config source 未決，不是可執行偽碼。
- 文件沒有 `[X-N]` requirement IDs，coverage 機檢無法建立追溯。

## 被當成事實的未驗證假設（§0）

1. production 一定沒有 `tests/`，但一定會攜帶 `_resources/max_nan_ratio.json`。
2. N6 warmup 誤標已由真實 run 驗證；文件沒有命令/輸出。
3. `FeatureValidator` 有既有 config 注入點。
4. validator 與 L6.5 的 winsor 預設/可配置語義可直接對齊並保持 byte-identical。
5. N7/T5 只是內部字串改名，不構成 schema/compatibility 變更。
6. 回歸 bundle 是 77 tests；實際 collection 為 78。
7. N6 不算 hot-path/performance 變更。

ASSUMPTIONS_VERIFIED: 已以 nl/sed/rg 對照 §A 所列程式碼；實測 max_nan_ratio artifact size/SHA；實際 pytest collection=78；確認 FeatureValidator 無 config 注入、stream validation 固定缺 nan_ratio。
TESTS_RUN: `pytest tests/feature_engineering/test_failopen_producer.py tests/feature_engineering/test_failopen_winsor.py tests/feature_engineering/test_failopen_manifest.py tests/feature_engineering/test_failopen_layers.py tests/feature_engineering/test_failopen_golden.py tests/feature_engineering/test_failopen_contract.py tests/test_multi_tf_generator.py -q` => 78 passed in 199.09s；coverage_check 明確因無 [X-N] IDs 失敗。
FAILURES_SEEN: coverage_check 無 requirement IDs；文件 gate 寫 77 passed 與實際 78 collected 不符。
SCOPE_CHANGES: none；只新增本 handoff review，未修改 docs/ 或 momentum/。
NUMERIC_OR_SCHEMA_IMPACT: review 本身 none；被審計畫會改 NaN quality metric、winsor config semantics、failed_layers grammar、timeframes metadata key，必須標為 numeric/schema impact。
STATUS: DONE
