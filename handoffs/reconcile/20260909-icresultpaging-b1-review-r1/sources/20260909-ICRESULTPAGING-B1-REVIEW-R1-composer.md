brief-kind: review
task-id: 20260909-ICRESULTPAGING-B1-REVIEW-R1
family: composer
findings-round: R1
標的 commit: `3df3ee20`（B0）→ `0154587e`（B1）→ `06e550e2`（mutation 錨點）→ `ed7563f4`（la1 測試修正）
審查範圍: `git diff a1ec256e..HEAD` — `api/services/ic_result_projection.py`、`ic_analysis_service.py`、`ic/routes`、`ic_models.py`、contract、golden、gate、探針、mutation、`test_icresult_paging.py`、`test_ic_la1_degraded_gate.py`

## Verdict：可合併、可開 B2

B0＋B1 實作與 SPEC R6（§C-6～10／§G G-1～G-9）逐條對齊；本輪驗收命令全 PASS；mutation P1–P16 紅＋C0 綠（brief 已 fact-verify）。**無新 P0／P1**。`test_ic_la1_degraded_gate` 之 `reference_tf=1h` 為測試面補齊（測 status 鏈非視窗），非改測試換綠。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| `pytest tests/api/test_icresult_paging.py` 36 passed 0 skip | **fact-verified** | 本輪 `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` → 36 passed，rc=0 |
| golden `--check`／SIZE／LATENCY gate | **fact-verified** | `probe-icresult-golden.py --check` → `CHECK PASS`；`probe-icresult-size.py` → `SIZE_GATE=PASS`（light 28681／summary50 18184／feature ≤2567）；`--latency` → `LATENCY_GATE=PASS`（light p50/p95 4.07/4.18 ms） |
| `test_export_api` 單跑 | **fact-verified** | `venv/bin/python -m pytest tests/api/test_export_api.py -q` → 8 passed，rc=0 |
| G-1 預設 `/result` raw bytes | **fact-verified（fixture）** | golden `--check`：`raw_body_sha golden=85ec16e8be1d live=85ec16e8be1d` |
| `_to_json_compatible` 對已 normalized 樹冪等 | **fact-verified** | `test_to_json_compatible_is_idempotent_on_normalized_tree` PASS；`get_result` 無 view 仍走 `:1880-1885` `_to_json_compatible`＋`deny` |
| 39k 實機預設 `/result` 位元組改前==改後 | **assumed（未跑）** | brief「我沒查的」第一行；G-1 僅鎖 14 特徵 fixture；風險：若冪等對 39k 不成立才會漂移——無反例 |
| 事件 run `metadata_keep_keys` 完整 | **assumed（未跑）** | golden 為全域 12h fixture；contract 已列 `event_filter`／`oos_downgrade`／`isolation`；無事件 run 實跑比對 |
| 5×39k RSS receipt | **unverified** | `icresult_memory.log` 尚未產；IP-RESID-5 殘留登記 |
| baseline sha 全 OK | **部分** | `shasum -c handoffs/20260909-icresult-b1-baseline.sha`：後端／測試／golden 全 OK；**3 個前端檔**（`useICAnalysis.ts`／`types.ts`／`icAnalysisStore.ts`）FAILED——本批未動前端，與 B1 scope 無關 |

---

## 必答（成對）

### 1a／1b 預設 `/result` 位元組級不變

- **1a（反例輸入）**：在 **14 特徵 fixture** 上未找到使「單樹＋讀取時 `_to_json_compatible`」與改前位元組不同的輸入。理論風險型別（NaN／inf／datetime／numpy 殘留／dict 鍵序）於寫入時已在 `_set_result` `:1797-1799` 一次正規化；讀取路徑 `:1880-1885` 對已 normalized 樹為早退冪等。若 39k 實機存在未正規化殘留型別，才可能二次轉換改序列化——**本輪未實跑 39k 對照**（brief NOT_RUN）。
- **1b**：**能**——G-1 `raw_body_sha256` golden 與 live 一致；mutation P6（預設誤套 light）會紅。

### 2a／2b snapshot 不可變

- **2a（改寫 `task_info["result"]` 序列）**：投影函式均只讀 snapshot、不回寫 `_tasks`。`project_light_view` `:230-248` 先 `funnel_from_filter_log`（計數前原始 `filter_log`），再頂層 shallow copy＋`apply_count_paths` 私有副本；`paginate_summary`／`project_feature` 不 assign `task_info["result"]`。無請求序列能透過投影改寫 live 樹。
- **2b**：`test_light_view_snapshot_immutable` 僅頂層 `==` deep-equal，**抓不到**子物件就地 mutation。但實作已用 `collections_to_counts`／`apply_count_paths` 建私有副本（`:163-191`），`filter_log` 原始 list/dict 鍵保留（測試 `:381-382` 佐證）；G-7b monkeypatch 中間 refilter 亦斷言舊世代。測試深度為 residual 風險，非已觀測缺陷。

### 3a／3b revision／409／422

- **3a（繞過 `_set_result`）**：`grep 'task_info\["result"\]' api/services/ic_analysis_service.py` → 僅 `:1800`（`_set_result` 內）；`test_ast_guard_single_result_write_site` AST 斷言 helper 內 ==1、外 ==0。未覆蓋 `task_info.update`／`setdefault`——全檔無其他 result 賦值。
- **3b（refilter 守衛後狀態）**：`refilter` `:2728-2732` 先驗後寫，`ValueError` → `ResultValidationError`；route `:677-678` → 422。`test_refilter_guard_fail_422_keeps_old_result`：`status==completed`、`result_revision==1`、task 端一致——與 SPEC §C-7(b) 吻合。

### 4a／4b 快取

- **4a（並發）**：`get_or_build` `:64-85` 鎖外呼叫 `builder()`，兩執行緒同 key 可能重複 build——**效能冗余、索引值相同**，非錯配。LRU：`test_cache_capacity_process_wide` 33 task×8 key 後 `cap-task-0` 被淘汰、process-wide 32 task；`cache_bytes()` 有上界斷言。
- **4b（revision 殘留）**：快取 key 含 `(task_id, revision, …)`（`:147`）；`test_cache_key_includes_revision` revision 變更必重排；`_set_result` `:1803` `invalidate_task`。舊 revision 索引不會被新 revision 命中。

### 5a／5b light 投影

- **5a（metadata 事件／降級 run）**：contract `metadata_keep_keys` 含 `event_filter`／`oos_downgrade`／`isolation` 等 33 鍵；`project_light_view` `:236-238` 白名單投影。事件 run 實機未跑（brief NOT_RUN）——設計對齊，覆蓋缺口非碼缺陷。
- **5b（funnel 先於計數）**：`project_light_view` `:230` funnel 在 `:239` `apply_count_paths` **之前**；`test_funnel_g8_shape_fixture_via_light` stage5 `output_features_count==2`（len）vs funnel `output==0`（dict.count）語意分離；mutation P12 改順序會紅——**順序 bug 可被 mutation 抓到**。

### 6 ≥10× 不必要複雜

**無**。contract SoT、純函式投影、LRU 有上限、mutation P1–P16 對應 §G／§V，複雜度與 SPEC 風險分級 (a)(d) 相称。

### 7 可合併 B2／la1 修法

- **可合併、可開 B2**：後端 Phase 1 驗收全 PASS；前端為獨立 Phase 2 cutover。
- **`test_ic_la1_degraded_gate` `reference_tf=1h`**：註解 `:717-718`／`:798-799` 明示「測 status 鏈非視窗」；TFWINDOW ×12 改的是 IC 視窗門檻，與 LA-1 OOS-gate oracle 無關——**測試面補齊，非降標換綠**。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無（碼與 SPEC R6 一致） |
| 2 | 漏項 | 無 blocking（39k G-1／事件 metadata 為 receipt 缺口，已登記 §0） |
| 3 | 不可測 | G-1～G-9／mutation 可機械驗 |
| 4 | quant | 無 leakage；deny 守衛寫入時一次、失敗不寫入 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 單樹 normalized；快取 32 task×8 key×int32；`_tasks` 無界＝IP-RESID-5 |
| 7 | cache | revision 在 key；寫入 invalidate；測試覆蓋 |
| 8 | API | 無 view＝G-1；v2×light⇒400；sort 白名單⇒400；revision 不符⇒409 |
| 9 | 測試 | 36 條＋golden＋gate parser＋G-7a/b/c |
| 10 | Agent | Task 落到檔案／函式，gate 可執行 |
| 11 | 短命工 | 無 |

---

## COMPOSER-R1-P3-00

**斷言**: 本輪對 B0＋B1 實作、必答 1–7、§1 十一類與 brief 必驗命令逐項核對後無需阻擋合併的 finding；可開 B2。

**碼證**: `pytest tests/api/test_icresult_paging.py -q -rs` → 36 passed rc=0；`probe-icresult-golden.py --check` → `CHECK PASS`（`raw_body_sha` 一致）；`probe-icresult-size.py` → `SIZE_GATE=PASS`；`--latency` → `LATENCY_GATE=PASS`；`pytest tests/api/test_export_api.py -q` → 8 passed rc=0；`_set_result` 三寫點 `:1638`／`:2436`／`:2730`；AST 守衛 `inside==1 outside==0`；`project_light_view` funnel 先於 `apply_count_paths`（`:230` vs `:239`）；`test_revision_g7a_and_g7c_refilter_handshake`／`test_revision_mid_projection_uses_old_snapshot_g7b`／`test_refilter_guard_fail_422_keeps_old_result` 全 PASS；brief mutation P1–P16 紅＋C0 綠（`icresult_mutate_phase1b.log`）。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c0780c361456; api/services/ic_result_projection.py#5368cd305826; api/services/ic_analysis_service.py#d61aa89ca9ac; tests/api/test_icresult_paging.py#b1review

[NON-BLOCKING] 信心度=High。Residual：39k 預設 `/result` 位元組未實跑對照、事件 run metadata golden、5×39k RSS receipt——皆 brief「我沒查的」或 IP-RESID-5，不阻擋 B2。

---

ASSUMPTIONS_VERIFIED: pytest 36/36；golden CHECK PASS；SIZE_GATE=PASS；LATENCY_GATE=PASS；export 8/8；AST guard 1/0；三 `_set_result` 寫點；funnel 順序碼證；refilter 422 測試；baseline sha 後端全 OK（前端 3 檔 drift 非本批）
TESTS_RUN: `venv/bin/python -m pytest tests/api/test_icresult_paging.py -q -rs` rc=0；`venv/bin/python handoffs/20260909-probe-icresult-golden.py --check` rc=0；`venv/bin/python handoffs/20260909-probe-icresult-size.py` → SIZE_GATE=PASS；`venv/bin/python handoffs/20260909-probe-icresult-size.py --latency` → LATENCY_GATE=PASS；`venv/bin/python -m pytest tests/api/test_export_api.py -q` rc=0；`shasum -a 256 -c handoffs/20260909-icresult-b1-baseline.sha`（3 frontend FAILED，餘 OK）
FAILURES_SEEN: baseline sha 3 前端檔不匹配（本批未動前端，非 B1 缺陷）
SCOPE_CHANGES: none（唯讀 review）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）

產出: `handoffs/20260909-ICRESULTPAGING-B1-REVIEW-R1-composer.md`

TMP_CLEANUP: 嘗試清 `/private/tmp/{icresult_*.log,sessions}` → Permission denied（sandbox）；保留 `claude-501`＋系統目錄

STATUS: DONE
