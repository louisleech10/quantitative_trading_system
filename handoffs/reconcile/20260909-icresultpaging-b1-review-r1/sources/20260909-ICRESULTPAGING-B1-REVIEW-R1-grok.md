# ICRESULT_PAGING B0＋B1 實作 code review R1（grok）

brief-kind: review  
task-id: 20260909-ICRESULTPAGING-B1-REVIEW-R1  
family: grok  
findings-round: R1  
標的 commit: `3df3ee20`（B0）→ `0154587e`（B1）→ `06e550e2` → `ed7563f4`（HEAD）  
SCOPE: review-only；禁改 production／test／docs／frontend  
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#c0780c361456  
CONTRACT-DIGEST: momentum/Analysis/contracts/ic_result_paging_contract.json#3d72cac820f6  

---

## Verdict：需修補後派工

本輪 **無 P0**；**1 P1＋1 P2**。B1 投影／revision／快取／G-1～G-9 fixture 路徑與 mutation 紅集合與 oracle 對得上，驗收命令全綠。阻擋開 B2 前應修：①寫入路徑在持有 process-wide `self._lock` 時跑全樹 `_to_json_compatible`＋`deny_factor_in_ok_oos`（39k 量級秒級鎖死）；②`sort_by=feature_name&sort_order=desc` 的 `_rev` 序 ≠ 純字串反序（前綴特徵名錯序）。`test_ic_la1_degraded_gate` 之 `reference_tf=1h` **不是**改測試換綠（測的是 status 鏈）。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` | **36 passed／0 skip**；rc=0 |
| `venv/bin/python handoffs/20260909-probe-icresult-golden.py --check` | `CHECK PASS`；raw sha `85ec16e8be1d` 對齊；rc=0 |
| `venv/bin/python handoffs/20260909-probe-icresult-size.py` | 恰一行 `SIZE_GATE=PASS`；light=28681／summary50=18184／feature≤2567；rc=0 |
| `venv/bin/python handoffs/20260909-probe-icresult-size.py --latency` | 恰一行 `LATENCY_GATE=PASS`；light p50/p95 4.56/5.26；cache hit 2.09；rc=0 |
| `venv/bin/python -m pytest tests/api/test_export_api.py -q` | **8 passed**；rc=0（單跑） |
| `shasum -a 256 -c handoffs/20260909-icresult-b1-baseline.sha` | 全 OK；rc=0 |
| mutation oracle（主委 receipt，本輪未在共用樹重跑） | `icresult_mutate_phase1b.log`：P1–P16 紅＋C0 綠；UNCOVERED=0 |

HEAD=`ed7563f4`

### brief「我沒查的」覆核

| claim | 結果 |
|---|---|
| 39k 預設 `/result` 改前==改後位元組 | **未跑** a1ec256e worktree 對照（cost）；fixture G-1＋冪等測試綠；見必答 1 |
| deep-analysis `:2339` 是否進 revision | **fact-verified**：獨立 deep 寫 `deep_analysis_result` 不經 `_set_result`；full-analysis 把 deep 併入 `report` 後一次 `_set_result`（`:2436`）⇒ 主 result 世代一次遞增。語意合理 |
| `invalidate_task(task_info["task_id"])` vs `_tasks` key | **fact-verified**：建立點皆 `"task_id": task_id` 且 `_tasks[task_id]=task_info`（`:1367`／`:2343` 附近）；key 恆等 |
| light `metadata_keep_keys` 對事件 run | **部分驗證**：contract 含 `event_filter`／`oos_downgrade`／`isolation`／`ic_window_disclosure`／`period_alignment`；`CONSUMED_META_KEYS` ⊆ keep；39k 全域報告 `eventish_not_kept=0`；**未**另跑事件 fixture light |
| 多 task RSS | **未跑**（receipt 尚未產） |

---

## 必答（成對）

### 1a. 預設 `/result` 位元組級不變：一種使「單樹＋再 normalize」與改前不同的輸入
**理論反例**：報告內含 `set`（或依賴雜湊迭代序的容器）。`_to_json_compatible` 對 `set` 做 `for item in value` → list，迭代序不穩定；寫入時一次正規化鎖定某一序，讀取再 normalize 保持該 list；改前「每次讀取才轉 set→list」可能得到不同序 ⇒ JSON 位元組不同。IC 報告實務幾乎無 set；NaN／inf／numpy 標量／datetime 路徑在 fixture 上已證冪等（`test_to_json_compatible_is_idempotent_on_normalized_tree`；golden `idempotent` 敘述）。

### 1b. G-1 golden（14 特徵）抓不抓得到
**能抓結構回歸**（誤套 light、丟段、normalize 字面變）⇒ raw body sha 紅；mutation P6 紅錨。**抓不到** 39k 實機獨有型別殘留／set 序（fixture 無）；brief 之 39k 改前 vs 改後對照 **NOT_RUN**。

### 2a. snapshot 被投影改寫的請求序列
現行 `project_light_view`／`apply_count_paths`／`paginate_summary`／`project_feature` **函式本身**不就地改 source（計數走私有副本；頂層新建 dict）。**可構造的污染路徑**：`paginate_summary`／`project_feature` 回傳的 `rows`／`summary_row` **別名** snapshot 列物件——若呼叫端 `page["rows"][0]["icir"]=999`（in-process，非經 JSON 反序列化）⇒ `task_info["result"]["summary_table"]` 被改。HTTP TestClient `.json()` 路徑會新建結構，實害限於同 process 持有回傳物件的呼叫端。

### 2b. `test_light_view_snapshot_immutable` 是否真能抓
**能抓就地改寫**：`before=deepcopy(result)` 後 light×2＋summary＋feature，再 `info["result"]==before`（含 `filter_log` 巢狀）。**抓不到** 回傳別名被呼叫端事後改寫（測試未持有 page 列再 mutate）。迴圈內 `assert … or True` 為空操作，真正守衛是 deep-equal。

### 3a. 寫 result 卻不經 `_set_result` 的路徑（AST 洞）
AST 守衛只認 `task_info["result"] =`（`Name.id=="task_info"` 的 Assign／Subscript）。**可繞過文法**（現碼未用）：`ti=task_info; ti["result"]=…`、`task_info.update({"result":…})`、`task_info.setdefault("result",…)`、`setattr` 等。現行三寫點（`:1638`／`:2436`／`:2730`）皆經 helper；獨立 deep 寫的是 `deep_analysis_result`。

### 3b. refilter 守衛 raise 後 vs SPEC §C-7(b)
**一致**：`refilter` try `_set_result`，`ValueError`→`ResultValidationError`→route 422；寫入在 deny 之後故舊 `result`／`result_revision` 不變；`status` 維持 `completed`（`test_refilter_guard_fail_422_keeps_old_result`）。`_tasks` 其他欄位不被該失敗路徑改寫。

### 4a. 快取並發／LRU／`cache_bytes`
`get_or_build`：**鎖外**呼叫 `builder()` ⇒ 兩執行緒同 key 可重複 build（實測 `concurrent_builds=2`）；再鎖內寫入，後寫覆蓋——同 snapshot 列 ⇒ 索引內容應相同，非錯配。LRU：`OrderedDict`＋module 單例 `_CACHE`，process-wide 32 task／每 task 8 key。`cache_bytes()`＝Σ`arr.nbytes`；**無獨立位元組上限**，上限由 32×8×(n·4) 推得（容量測試有斷言）。

### 4b. 舊 revision 索引殘留
key 含 `revision`；`_set_result` 呼叫 `invalidate_task` 整 task 清除。即使未 invalidate，舊 revision 鍵不會被新請求命中。索引持有的是 **int 位置**，rows 來自當次 snapshot 列表；refilter 後新 snapshot＋新 revision 重建。殘留風險低（記憶體至下次 task LRU 淘汰）。

### 5a. light 投影：事件 metadata／39k filter_log
`metadata_keep_keys` 含前端 DegradedBanner／IsolationNote／PeriodAlignment／window 所需鍵；`CONSUMED_META_KEYS` 測試鎖 ⊆。39k 實機：`project_light_view` 後 `dropped_present_in_light=[]`；`filter_log` 六 stage 皆在；`funnel_matches_light=True`；stage5 funnel `{input:39346,output:0}` 與計數後 `output_features_count=2` 語意分離（與 G-8／P12 一致）。事件 run 專用 light **未**另跑 fixture。

### 5b. funnel 先於計數；P12 是否真因順序
**是**：`project_light_view` 先 `funnel_from_filter_log(report.get("filter_log"),…)` 再 `apply_count_paths`。P12 突變改為對 `apply_count_paths(report,contract).get("filter_log")` 算 funnel ⇒ stage5 的 list／dict 已變 `_count` 標量，adapter 取不到 ⇒ stage5 變 null；receipt `P12-funnel-after-counts rc=1`。

### 6. ≥10× 不必要複雜？
**無**。contract SoT、單一寫點、snapshot、int32 LRU、mutation P1–P16 對 §G／§V 比例合理。

### 7. 可合併開 B2？la1 `reference_tf=1h` 是否假綠？
- **修 P1／P2 後可開 B2**（前端 cutover 不依賴這兩點的修法形狀）。未修 P1 時 refilter／完成會秒級鎖死全 service，B2 實機體驗差。
- **la1 修法不是假綠**：`ed7563f4` 只為 1h fixture 加 `ic_calculation.icir.reference_tf=1h`，註解寫明測的是 status 鏈非視窗；A/B 證 TFWINDOW×12 測試面遺漏（`7a1dd8f0` 綠→`a17b57e7` 紅），非放寬 ICRESULT 斷言。

---

## Findings

## GROK-R1-P1-01

**斷言**: `_set_result` 的全樹 `_to_json_compatible`＋`deny_factor_in_ok_oos` 在呼叫端已持有的 process-wide `self._lock` 內執行，39k 報告寫入期間會阻塞所有 task／result／summary／feature 讀取。

**碼證**: `api/services/ic_analysis_service.py:1632-1638`（完成）、`:2428-2436`（full-analysis）、`:2725-2732`（refilter）皆 `with self._lock:` 內呼叫 `_set_result`；`:1789-1806` 內先 normalize 再 deny 再賦值。SPEC §C-7 自證 39k normalize ≈2586 ms、deny ≈1461 ms。對照改前寫入為參考賦值（O(1)）。`self._lock = threading.Lock()`（`:450`）。修法：lock 外 normalize＋deny，lock 內只賦值／遞增 revision／invalidate；守衛失敗則不進 lock 寫入（完成路徑再標 failed）。

**來源摘要**: api/services/ic_analysis_service.py#d61aa89ca9ac

[MAJOR] 信心度=高；單使用者完成當下也可接受，但 refilter／多 task 時全 API 停滯與 §C-9 讀取預算衝突；B2 實機翻頁會踩到。

## GROK-R1-P2-01

**斷言**: `sort_by=feature_name&sort_order=desc` 使用 `_rev`（字元碼取負的 tuple）排序，與 SPEC §C-8「純字串比較」／Python `sorted(..., reverse=True)` 不一致；前綴特徵名（`close`／`close_sma`／`close_sma_20`）會錯序。

**碼證**: `api/services/ic_result_projection.py:31-39`（`_rev`＋string_fields 分支）。實跑：`paginate_summary` desc → `['close','close_sma','close_sma_20','a','ab']`；`sorted(names, reverse=True)` → `['close_sma_20','close_sma','close','ab','a']`。G-6／latency 只鎖 `feature_name` **asc**，desc 無 golden。修法：字串欄改 `(0, name)` 並在 desc 時用反向比較，或 `sorted(..., reverse=(sort_order=="desc"))` 等價策略；補 G-6／單元反例（含前綴名）。

**來源摘要**: api/services/ic_result_projection.py#5368cd305826

[MAJOR] 信心度=高；預設排序為 icir，故非 P0；B2 表格若提供按名降冪會顯示錯序。

---

## §1 必查摘要（碼 vs SPEC）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | **P1-01** lock 範圍 vs 寫入時昂貴正規化；**P2-01** 字串 desc vs §C-8 |
| 2 | 漏項 | G-6 缺 `feature_name` desc／前綴反例（與 P2-01 同源） |
| 3 | 不可測 | 39k 改前 vs 改後預設 body 未跑；其餘 G-1～G-9 fixture／探針可測 |
| 4 | quant | deny 守衛仍在寫入路徑；無弱化 NaN／inf |
| 5 | 過度工程 | 無（必答 6） |
| 6 | OOM | 單樹＋32×8 int32；`_tasks`→IP-RESID-5 |
| 7 | cache | key 含 revision；invalidate 在寫入後；並發重複 build 無害 |
| 8 | API | light×v2⇒400；refilter 422／revision 409 測過 |
| 9 | 測試 | 36 綠；immutable 測靠 deep-equal；字串 desc 缺口 |
| 10 | Agent | AST 只鎖 `task_info` 名；文件已寫呼叫端持 lock |
| 11 | 短命工 | 無 |

## 被當成事實的未驗證假設（§0）
- 39k 預設 `/result` 位元組改前==改後（NOT_RUN）
- 事件 run light 的 metadata 鍵集完整（僅 contract／CONSUMED 靜態＋39k 全域抽樣）
- 多 task RSS 增量（receipt 未產）

STATUS: DONE
