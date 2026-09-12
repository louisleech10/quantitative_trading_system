# SPLITUNIFY_SPEC.md 延伸 D-002

BASE: docs/SPLITUNIFY_SPEC.md @ 1be5be3f
PREDECESSOR: docs/SPLITUNIFY_SPEC.D-001.md
改什麼: 落實 `docs/SPLITUNIFY_TODO.md` §E 之殘留 `SU-RESID-2`（多 TF 之 `(event_id, timeframe)` 複合鍵），並**更正 D-001 兩處與實況不符的陳述**（見下方「對 D-001 的更正」）。
為什麼: `handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md`（四家偵察 18 條，收斂為六群；主委自產另見 `handoffs/20260911-splitunify-b9-consult-r1-claude.md`）。

**類別判定＝D 延伸**（依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1）。
理由：`SU-RESID-2` 於 BASE 與 D-001 皆已具名登記為殘留、並預告「排於下一批」；本延伸即該預告之落地，**不推翻** BASE 之任何設計意圖。D-001 第 11 行之「排於下一批」即本檔。

## 🔴 對 D-001 的更正（本延伸之首要義務）

<!-- OBLIGATIONS-BEGIN id=D-002-CORRECT -->

**(1.1)** D-001 第 11 行與第 189 行之句「未完成前多 TF 同批維持 fail-closed」**與實況不符**，須以本延伸之 (1.2) 取代。

**(1.2)** 現行 `build_event_keys`（`momentum/Analysis/event_samples/split_projection.py`）擋下的是**兩種**情形：①選定 TF 下同一事件有多列 `per_tf`；②選定 TF 下事件缺 `feature_cutoff_ms`。它**不擋**「同一批含多個 timeframe」——未被 `selected_timeframe` 選中的列被**靜默丟棄**，無例外、無警告、report 亦不記。

**(1.3)** D-001 第 189 行所列之「下游單鍵面六處」**不是完整清單**，不得作為本延伸之觸及面依據；觸及面以本檔「觸及面宣告」為準。

**(1.4)** (1.1)–(1.3) 之更正**不改變** D-001 其餘任何義務；D-001 之 (4.1)–(4.18) 與 `M-SU-D1-01`～`23` 全部繼續有效。

<!-- OBLIGATIONS-END -->

## 🔴 明確不在本延伸範圍

`D1`（事件掃描端「恆走」event-study-only）之條件化仍須走 **R 重開**；`R-5` 待其完成後另行處理。本延伸**不動** `row_index`／`row_index_local` 之座標語意（D-001-C2 第 4 點全文繼續有效）。

## 觸及面宣告

本清單取代 D-001 第 189 行之六處。來源＝四家偵察合併盤點（三家委員各自 `rg` ＋ 主委自產），逐處附碼證。

新增: `D-002-C1`（複合鍵語意）、`D-002-C2`（揭露義務）、`Task 9.1`～`Task 9.4`
覆寫: D-001 第 11 行與第 189 行之 `SU-RESID-2` 相關句（見上方更正區塊）
依賴: `## §V 驗證策略與邊界測試目錄`；`## §G Golden / Baseline`
不觸: D-001 之 `D-001-C1`／`D-001-C2`／`Task 8.1`～`8.3`

### 單鍵消費面（15 處，分三層）

**第一層 — producer／投影本體**
| # | 位置 | 依賴形態 |
|---|---|---|
| 1 | `split_projection.build_event_keys` | 選定 TF 後要求 `event_id` 唯一；`merge(..., validate="1:1")` |
| 2 | `split_projection` assignments／purged 組裝 | 兩表僅以 `event_id` 標識，無 `timeframe` 欄 |
| 3 | `event_split.build_time_clusters` | 一 manifest 列對一 `event_id` 列 |

**第二層 — 表格鏈（D-001 原列六處）**
| # | 位置 | 依賴形態 |
|---|---|---|
| 4 | `feature_materialization` merge `validate="many_to_one"` | 事件表被當成 `event_id` 唯一（**會報錯**） |
| 5 | `feature_materialization` 輸出 `set_index("event_id")` | 重複 index **只留最後一列，不 raise**（**靜默**） |
| 6 | `baseline` | 繼承第 5 項之唯一索引 |
| 7 | `pattern_bridge` `assign.set_index("event_id")["split_label"]` | 非唯一時取到 Series 而非純量（**靜默**） |
| 8 | `tables` 兩處 `set_index("event_id")` | 簇 lookup 非唯一時回 Series，轉 int 行為未定（**靜默**） |
| 9 | `ic_feed` 兩處 `set_index` ＋ `.loc[keep["event_id"]]` | 非唯一時取回多列（**靜默**） |
| 10 | `dedupe` merge `validate="one_to_one"` ＋ `cluster_first` 保留集 | 前者**會報錯**；後者同簇只留一列，**靜默折掉 TF** |

**第三層 — D-001 未列（本延伸新增）**
| # | 位置 | 依賴形態 | 誰找到 |
|---|---|---|---|
| 11 | `counterexample_classifier` `.loc[eid]` | 非唯一時分類結果綁錯 receipt 列（**靜默**） | composer／grok |
| 12 | `candidate_ledger` 雙 `set_index` ＋ `.loc[eid]` | 同上 | composer／grok |
| 13 | `ic_feed.event_context_from_windows` survivor 六鍵 | 以排序後 `event_id` 列雜湊，多 TF 後語意改變 | composer |
| 14 | `frontend/src/lib/types.ts` batch_facts ／ `frontend/src/app/search/page.tsx` 之 `byEventId` Map | 前者隱含唯一；後者同鍵**後者覆蓋前者**，畫面靜默顯示錯列 | composer（前）／主委自產（後） |
| 15 | `tests/golden/splitunify/splitunify_golden.json` ／ `clusters_oracle.json` | 以 `event_id` 清單比對，多 TF 因 set 去重而看不出差異 | composer・grok（前）／主委自產（後） |

## 內容

### §RISK 風險分級

- **大小**：大（命中 (a)(b)(d)）。
- **命中高風險原則**：(a) 多 TF 記帳影響 IC 樣本數與統計量；(b) 觸及 15 處共用消費面含前端與 golden；(d) 錯誤折疊會直接改變 ML／回測輸入的樣本構成。
- **RISK-HIT: a,b,d**
- 命中 (a)(d) ⇒ §G Golden 必填、adversarial review 必跑。

### §A 假設與待使用者確認

- FACT-RECEIPT: `venv/bin/python probe_b9_multitf.py` → 印出 `A NO_RAISE 產出 2 列` / `B RAISED …多列 per_tf` / `C NO_RAISE 產出 2 列` / `D RAISED …缺 cutoff`（主委 實跑 2026-09-12）
- FACT-RECEIPT: codex 獨立 Probe A → 印出 `input_per_tf_rows 4 output_rows 2 output_timeframes ['1h'] UNSELECTED_ROWS_DROPPED 2`（codex 實跑 2026-09-12）
- FACT-RECEIPT: `git hash-object docs/SPLITUNIFY_SPEC.md` → 印出 `0e51d3f6d5e8c00d605767f990a4cf5288c0c36d`（主委 實跑 2026-09-12）
- **待確認：無**
- **已確認結果**：`2026-09-12 使用者裁定——主委自產不進委員收斂之 roster 與 sources，僅以敘述引用`

### §C 約束

- 解耦 7 條不變；本延伸**不得**讓 `momentum/` 反向依賴 `api/`。
- 本任務特別注意：15 處消費面中，第 5／7／8／9／10／11／12／14 為**靜默**失效面——驗收不得只看「有沒有報錯」。
- 🔴 **事件數與列數是兩個量**：`(event_id, timeframe)` 複合鍵落地後，`n_events` 與「(事件,TF) 列數」不得混用；報告、API、前端任一處把列數當事件數即為缺陷（codex 偵察指出）。

### §G Golden / Baseline

- **必填理由**：命中 (a)(d)。
- **凍結時機**：Task 9.1 動工前，以現行單 TF fixture 重跑 `scripts/freeze_splitunify_golden.py` 取得 baseline（`GOLDEN OK` 為前置條件）。
- **baseline 內容**：`g1_membership`／`g3b_oracle`／`g5_row_fingerprint_*`／`g4_per_symbol_n` 現值；另存 `clusters_oracle.json` 現值。
- **本延伸之預期位移**：`g1_membership`／`g3b_oracle` **必須擴維或新增 multi-TF 平行組**（三家一致）；`g5` 指紋 payload 不含 `timeframe`，**不受影響**；`clusters_oracle.json` 須擴充。單 TF 舊值**保留為回歸錨**，不得刪除。
- **通過條件**：單 TF 路徑逐值不變（exact）；多 TF 路徑以新增之平行組比對。任一單 TF 舊值位移即 FAIL。
- 🔴 **順道處置 `M-SU-D1-23`**：D-001 該條 mutation 在單標的 golden 下不可觸發，三家 R1 一致建議「日後 digest 本就要動時再改」。本延伸既必然動 golden，**即為該時機**——fixture 改為兩標的交錯，使該 mutation 可觸發。

### §P Phase 與依賴

### Phase 9A — 揭露先行（依賴：無）

**Task 9.1 — 丟棄列數必須揭露**
- 目標：在複合鍵落地**之前**，先消除「靜默丟棄」這個誠實性缺陷。
- 檔案：`momentum/Analysis/event_samples/split_projection.py::build_event_keys`；`EventSplitPlan.summary`。
- 改法：`build_event_keys` 於 selected-TF 過濾處計算被丟棄之列數（按 timeframe 分組），寫入 summary 之 `discarded_per_tf_rows_by_timeframe`；為空時寫 `{}` 而非省略欄。
- 不可做：不得以此取代複合鍵（揭露不是修復）；不得在丟棄時 raise（那會擋掉目前合法的單 TF 用法）。

### Phase 9B — 複合鍵主體（依賴：Phase 9A）

**Task 9.2 — schema 加 `timeframe`**
- 檔案：`split_projection` 之 `assignments`／`purged`；`event_split.build_time_clusters` 之 `clusters`。
- 改法：三表各加 `timeframe` 欄；`receipts.per_tf` **不改形狀**（本就是該粒度）。
- 🔴 `n_events` 與列數分離：summary 須同時提供 `n_events`（去重後事件數）與 `n_event_tf_rows`。

**Task 9.3 — 15 處消費面逐處改**
- 檔案：見「觸及面宣告」之三層表。
- 改法：凡 `set_index("event_id")` 改為 `(event_id, timeframe)` 或 MultiIndex，並**斷言索引唯一**；`dedupe` 之 `cluster_first` 保留集改 `(event_id, timeframe)` 粒度。
- 🔴 **cluster 語意**（四家一致）：時間簇仍按**事件級 interval** 合併，同一事件之不同 TF **同簇**；不得因複合鍵而把同一事件當成多個獨立觀測（那會稀釋 `n_events_effective`）。

**Task 9.4 — golden 與前端**
- 檔案：`tests/golden/splitunify/*`；`frontend/src/lib/types.ts`；`frontend/src/app/search/page.tsx`。
- 改法：golden 依 §G 擴維；前端 `byEventId` Map 之鍵改為複合鍵，消除「後者覆蓋前者」。

### §V 驗證策略與邊界測試目錄

- `Task 9.1`：`ASSERT build_event_keys WHEN per_tf 含 1h 與 4h 而 selected=1h THEN summary["discarded_per_tf_rows_by_timeframe"] == {"4h": 2}`；`ASSERT WHEN 單一 TF THEN 該欄 == {}`。
- `Task 9.2`：`ASSERT assignments WHEN 複合鍵 THEN 欄含 timeframe 且 (event_id, timeframe) 唯一`；`ASSERT summary THEN n_events != n_event_tf_rows 時兩者皆存在且不相等`。
- `Task 9.3`：每一處消費面各需一條「**改壞就要變紅**」測試；🔴 **靜默面（第 5／7／8／9／10／11／12／14 項）之測試不得只斷言「不報錯」**，須斷言取到的**值**正確。
- `Task 9.4`：`ASSERT golden WHEN 單 TF fixture THEN 舊值逐值不變`；`ASSERT WHEN 多 TF fixture THEN 新增平行組可區分不同 TF`。
- **mutation**（接續 `M-SU-D1-*`，前綴 `M-SU-D2-`）：`01` 丟棄列數改為不寫入 summary、`02` `set_index` 保留單鍵、`03` `cluster_first` 保留集退回 `dedupe_cluster_id` 粒度、`04` 前端 Map 鍵退回 `event_id`、`05` `n_events` 直接取列數、`06` golden 仍以 event_id 清單比對。各須指名應紅之測試。

### §R 回退

單 TF 舊值保留為回歸錨；Phase 9A 可獨立回退（只移除 summary 欄）。Phase 9B 回退需連同 15 處消費面一併還原，故 9B 須在單一批次內完成，不得部分上線。

### §N N/A 登記與殘留

- `SU-RESID-2` — **本延伸落實**，理由類別由 `needs-research` 解除。
- `M-SU-D1-23` — 由本延伸 §G 順道處置（fixture 改兩標的交錯），`needs-research` 解除。
- `D1`／`R-5` — 不在本延伸；`D1` 須走 R 重開。
- `SU-RESID-4`／`SU-RESID-5` — 不動（觸發條件未到）。
- `R-3`（UAT 最後，user-ruling）、`R-4`（屬 GAP-3，blocked-by）— 不動。
- 🔴 **誠實邊界**：IC 端到端真實 run **未跑**（四家偵察皆同此限縮）；`api/services/` 未逐檔讀、僅型樣 grep，故第三層清單可能仍不完整——`Task 9.3` 動工前須再掃一次並更新本表。

## 沿革與追溯索引

<!-- HISTORY-BEGIN -->
- 2026-09-12：依 `handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md`（四家偵察 18 條／六群）建立本延伸。
<!-- HISTORY-END -->

## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。
