# SPLITUNIFY 收尾 consult R2 — COMPOSER

task-id: 20260911-SPLITUNIFY-X-CONSULT-R2  
family: COMPOSER  
brief: `handoffs/20260912-SPLITUNIFY-CLOSEOUT-CONSULT-R1-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 | 理由 |
|---|---|---|
| R-1 之阻塞是 `base_universe_hash`「語意未定」 | **未成立** | `_base_universe_hash(index,symbol)` 已把 symbol 納入 hash 輸入；未定的是**多對 plan 傳遞／投影 API** |
| R-5 必動「請求模型／前端／契約／UAT 全動」 | **未成立** | 選填 `features_ref` + `None⇒現行` 可只動 API model + service；前端在 `None` 路徑已正確 |
| SU-RESID-2 會迫使五組 golden **全部**重算 | **未成立** | 現 fixture 單一 selected TF；g5 指紋與 row_index 無關 event_id 鍵 |
| D1「恆走」改條件式＝推翻 C-1 權威 | **未成立** | C-1 權威仍是時間切分；變的是**事件掃描端何時能接到 universe** |
| `frontend/src/lib/api.ts:1123` 是唯一 analyze 呼叫點 | **fact-verified** | `grep -rn events/.*analyze frontend/src` 僅此一處非測試 fetch |

---

## 必答 1–7（立場＋碼證；正反各一句）

### 1. R-1 研究問題是否已被回答？

**立場**：**是——唯一性已有定義；R-1 應改寫為「per-symbol plan 傳遞 + 投影縱向合併」。**

**支持碼證**：`_base_universe_hash` 輸入含 `symbol`（`ic_filter_orchestrator.py:517-530`）；實跑 `ETHUSDT` vs `BTCUSDT` 同 index ⇒ `False`；`split_per_symbol` 對每對 plan 帶 `symbol` 但共用同一 `base_universe_hash` 參數（`contracts.py:671-684`）；投影端仍只收單一 `(train_plan,test_plan)` 且多 symbol 事件批 fail-closed（`split_projection.py:388-428`）。

**反面**：cross-sectional 路徑刻意用 `ICSplitAdapter._base_universe_hash` 對**整框**算一份 hash（`ic_filter_orchestrator.py:905-932`）——這不是「兩 symbol 碰撞」，而是**第二套 hash 語意**；若 R-1 修法未區分單幣 IC vs cross-sectional，會把兩條生產路徑混為一談。

### 2. R-5 收窄案能否避開全棧大改？

**立場**：**能——`EventAnalyzeRequest` 加選填 `features_ref{features_path,config_hash}`，`None` 維持 event-study-only；不必先動前端。**

**支持碼證**：`case_import_service.py:1609-1623` 現況恆 `run_event_study_only_with_params` 且 `capability.split=unavailable`；`test_fraction` 等三欄已註解未使用（`:1606-1608`）；`EventTablesPanel.tsx:357-378` 在 `unavailable` 時禁顯切分計數並渲染 reason；`splitCapability.ts:57-74` 對未知 reason 仍 fail-closed 顯示字面。

**反面**：當 `features_ref` 非 `None` 且投影成功時，後端必新增 `capability.split=ok` 分支——否則畫面永遠像「沒切分」；那條路徑需要前端小改（非 `None` 路徑），但**不影響**現行全 `None` 部署。

### 3. SU-RESID-3：加欄 vs 維持首尾？

**立場**：**維持首尾對證 + 把「中間間距不同」列為永久誠實邊界（不在 b9 加 `row_time_fingerprint`）。**

**支持碼證**：B3 已用首尾對證關掉兩條實跑攻擊（`split_projection.py:464-484`；SPEC TODO §E SU-RESID-3 原文）；加 producer 欄會動 `SplitPlan` + IC golden digest（`contracts._coerce_timestamp_array` 秒語意 vs 事件 ms，SPEC §N 自承）。

**反面（未選方案之最強理由）**：首尾相同、中間間距不同的兩份網格仍可通過——若 R-5 讓呼叫端可指錯 universe，只靠首尾不足以證明 post-trim index 一致；長期應在 R-5 驗收加「投影端對 plan 全部 `row_index` 取 timestamp 指紋」的**消費端**檢查（不動 plan schema），而非永久假裝已關洞。

### 4. SU-RESID-2 是否迫使五組 golden 全重算？

**立場**：**否——現五組在單一 selected TF fixture 下可保留；須**新增**多 TF golden 組，而非重寫全部。**

**支持碼證**：`freeze_splitunify_golden.py:158-161` 的 g1 取自 `assignments.event_id`；現 fixture 每事件恰一列 per_tf（`build_event_keys:283-288`）；g5 凍的是 test 段 **row positions**（`splitunify_golden.json:48-107`），與 event_id 鍵無關；複合鍵主要影響**多 TF 同 event_id** 場景——現 golden 未覆蓋。

**反面**：若只改程式、不新增多 TF golden，舊五組在單 TF 下仍綠，但**對多 TF 回歸是假綠**——收 b9 前必跑 `freeze --write` 增 `g6_multi_tf_membership`（或等價）並寫進 SPEC §G。

### 5. D1 改條件式：D 延伸還是 R 重開？

**立場**：**D 延伸**（`docs/SPLITUNIFY_SPEC.D-00X.md` 覆寫 §C-0 決議③「恆走」字面為「無 universe 時走 event-study-only；有 `features_ref` 時走對照路徑」），**不**動 C-1「時間切分為唯一權威」。**

**支持碼證**：`FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md §2.1` D＝不推翻設計；核心禁令「沒有 canonical universe 不得宣稱 OOS」（SPEC §C-0③）仍成立——只是 R-5 補供給路徑；`b7-review-r1/synth.md:20` 自承 D1 範圍未重審，屬**範圍補登**非證偽 C-1。

**反面**：§C-0 原文「事件掃描端**恆走**」與條件式**字面互斥**——依 v2 §2.2「與原檔互斥⇒不是 D」可爭議升 **R**；若主委選 D，延伸檔 `覆寫` 欄必逐字列出 §C-0 決議③，並在 reconcile 明示「恆」字被條件式取代、C-1 不變。

### 6. 批次切法與依賴

**立場**：**同意 R-5 依賴 R-1 與 SU-RESID-3（驗證邊界）**；建議 **b8＝R-1＋SU-RESID-2**、**b9＝SU-RESID-3 誠實邊界文件化 + 投影端 row 指紋（不動 plan）**、**b10＝R-5＋D1 延伸**——比主委初擬把 SU-RESID-2 與 SU-RESID-3 捆 b9 更貼依賴。**

**支持碼證**：R-5 錯 universe 要靠 per-symbol 投影（R-1）與 index 對證（SU-RESID-3 現行首尾 + 建議 row 指紋）擋（`split_projection.py:413-484`）；`build_event_keys` 與 per-symbol 投影無硬依賴，可與 R-1 同批。

**反面**：三批拆法多一輪 gate 摩擦；若合併 **b8＝R-1＋SU-RESID-2＋SU-RESID-3（文件）**、**b9＝R-5＋D1** 仍 fail-closed，且 SU-RESID-3 不加欄，可省一輪——代價是單批 diff 面大、review 負擔高。

### 7. 主委漏掉的殘留／風險

**立場**：**有 3 項**（已查：投影／IC hash 雙路徑、`dedupe` 鍵、`lgb/xgb` 假 hash 是否入投影）。

1. **IC 單幣 `_base_universe_hash(index,symbol)` vs cross-sectional `ICSplitAdapter` 整框 hash**——R-1 修法須寫清哪條路徑投影事件（`ic_split_adapter.py:189-199` vs `ic_filter_orchestrator.py:517-530`）。
2. **`dedupe.py` 以 `(label_start_ms,event_id)` 重排**（`split_projection.py:263-264`）——SU-RESID-2 複合鍵後，同一 `event_id` 多 TF 是否與 dedupe 假設衝突，**未讀碼驗收**。
3. **`lgb_cv_universe`／`xgb_cv_universe` 字面 hash**（`lightgbm_analyzer.py:377`、`xgboost_analyzer.py:1162`）——`grep` 未進 `derive_event_split_from_plans` 鏈，但若日後 CV plan 接入投影需另列殘留。

---

## COMPOSER-R2-P1-01

**斷言**: R-1 的 needs-research 理由應收回——`base_universe_hash` 在多標的下之唯一性已由 `_base_universe_hash(...,symbol)` 定義；未做的是 per-symbol `(train,test)` 對的投影 API 與 `split_per_symbol` 逐 symbol 傳 hash。

**碼證**: `ic_filter_orchestrator.py:517-530`；`contracts.py:662-684`（共用字面 hash）；`split_projection.py:400-428`（單 plan 對 + 多 symbol 事件 fail-closed）。VERIFY: `python -c "…ETH vs BTC…"` ⇒ `False`。RECHECK: 同上命令 + 讀三處行號。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a

[MAJOR] 信心度=High。若 b8 仍把 R-1 當「hash 語意研究」會再空轉一輪；**不改**則多 symbol 批永遠 `multi_symbol_projection_unsupported`，IC 與事件掃描無法對齊 per-symbol 邊界。修法：投影改收 `Mapping[symbol,(train,test)]` + `feature_index_by_symbol`，每 symbol 各自 hash（`split_per_symbol` 改為逐 symbol 呼叫 `_base_universe_hash` 或傳 `dict[symbol,str]`）。

---

## COMPOSER-R2-P1-02

**斷言**: R-5 收窄為選填 `features_ref` 時，`None` 路徑不必動前端；但 b10 驗收必含 `capability.split=ok` 新分支，否則有 universe 仍顯示「沒切分」。

**碼證**: `case_import_service.py:1620-1623`（恆 unavailable）；`EventTablesPanel.tsx:360-362`（`hasSplit` 才顯計數）；`splitCapability.ts:57`（僅 `split==='ok'` 為 hasSplit）。RECHECK: `grep capability.split case_import_service.py`；讀 `splitCapability.ts:54-74`。

**來源摘要**: api/services/case_import_service.py#d2571793953f

[MAJOR] 信心度=High。若只做後端接線、不改 capability 枚舉與前端 `ok` 分支，R-5 **靜默失敗**——表算了但 UI 永遠 event-study-only 文案。修法：契約 JSON 增 `split=ok` + reason 封閉集；前端僅在 `ok` 時恢復計數列（與現 `unavailable` 對稱）。

---

## COMPOSER-R2-P1-03

**斷言**: SU-RESID-3 在 b9 應採「首尾對證 + 明文誠實邊界」，不在 `SplitPlan` 加 `row_time_fingerprint`；R-5 驗收改加投影端對 plan 全部 `row_index` 的 timestamp 指紋（不動 IC digest）。

**碼證**: `split_projection.py:474-484`（現行首尾）；SPEC TODO §E SU-RESID-3「中間間距」殘留原文；`contracts.py:425-426`（秒語意 hash 動 golden）。RECHECK: 讀 `split_projection.py:464-484` 與 TODO §E 行。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#98ee62905643

[MAJOR] 信心度=Medium。**不改**則中間間距攻擊面仍存在，但 B3 已擋住更高危兩條；若 b10 不做 row 指紋，R-5 錯指 universe 仍可能首尾巧合通過。修法：投影內對 `index_ms[rows]` 全列 sha256 與 plan 建檔時快取比對（快取可只活在 derive 呼叫鏈，不寫回 SplitPlan）。

---

## COMPOSER-R2-P2-01

**斷言**: D1 條件式重寫應走 **D 延伸**（`SPLITUNIFY_SPEC.D-00X`），在延伸檔 `覆寫` 明示取代 §C-0 決議③「恆走」字面；爭議時預設 R 但本案核心設計（C-1 時間切分權威）未被證偽。

**碼證**: `docs/SPLITUNIFY_SPEC.md:89-93`（恆走原文）；`FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md §2.1-2.2`；`b7-review-r1/synth.md:20`（未重審）。RECHECK: 讀 SPEC §C-0 與 v2 §2.2 延伸檔模板。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[MAJOR] 信心度=Medium。若跳過延伸檔直接改 SPEC 正文會 violate 戳記；若誤判為不需程序會在 `reconcile_stamps_check` 被擋。**不改**則 b10 無法合法寫入「有 features_ref 時走對照路徑」。

---

## COMPOSER-R2-P2-02

**斷言**: 批次依賴應為 **b8（R-1＋SU-RESID-2）→ b9（SU-RESID-3 誠實邊界＋row 指紋）→ b10（R-5＋D1 延伸）**；R-5 不得早於 R-1。

**碼證**: `split_projection.py:413-428`（per-symbol 前置）；`case_import_service.py:1592-1602`（R-5 須接 derive）；主委 brief §4 自陳 R-5 依賴 R-1 與 SU-RESID-3。RECHECK: 對照 TODO §E 殘留表與 SPEC Task 3.3。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[MINOR] 信心度=High。若 b10 搶跑，事件掃描端可帶 `features_ref` 但投影仍單 plan ⇒ **跨 symbol 靜默錯分**或 fail-closed 假完成。

---

## COMPOSER-R2-P2-03

**斷言**: SU-RESID-2 收案時若只改鍵、不新增多 TF golden，現有五組不必全重算，但**必**增 §G 多 TF 組，否則複合鍵路徑無回歸。

**碼證**: `tests/golden/splitunify/splitunify_golden.json`（單 TF event_id）；`test_splitunify_golden.py:134-137`（手推锚點）；`freeze_splitunify_golden.py:158-161`。RECHECK: `pytest tests/momentum/Analysis/test_splitunify_golden.py -q`（9 passed 基線）。

**來源摘要**: tests/golden/splitunify/splitunify_golden.json#f270e007ca98

[MINOR] 信心度=High。若誤以「g1 仍綠」當 SU-RESID-2 完成，多 TF 同 event_id 會在生產路徑 raise 或靜默錯分且測試不紅。

---

## 收束建議（供 synth）

| 殘留 | 建議批次 | 程序 |
|---|---|---|
| R-1 | b8 | impl + review；改 §N 理由為「實作 per-symbol 投影」 |
| SU-RESID-2 | b8 | 加多 TF golden；舊五組保留 |
| SU-RESID-3 | b9 | 文件化誠實邊界 + 投影 row 指紋（不動 plan） |
| R-5 | b10 | 選填 `features_ref` + `capability.split=ok` |
| D1 重審 | b10 | `SPLITUNIFY_SPEC.D-00X` 條件式覆寫 §C-0③ |

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:  
STATUS: DONE
