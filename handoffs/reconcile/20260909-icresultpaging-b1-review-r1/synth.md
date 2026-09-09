# Reconcile — 20260909-icresultpaging-b1-review-r1

**來源** 20260909-ICRESULTPAGING-B1-REVIEW-R1-codex.md, 20260909-ICRESULTPAGING-B1-REVIEW-R1-composer.md, 20260909-ICRESULTPAGING-B1-REVIEW-R1-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

composer「可合併、可開 B2」（sentinel `COMPOSER-R1-P3-00`）；grok 1 P1＋1 P2；codex 2 P1。四條皆實作缺陷、皆附實跑反例、皆已修（commit `ddbcca84`、本輪 commit）。

### Q1 — P1 `_set_result` 在 lock 內做全樹 normalize＋守衛（39k ≈4 s）擋住所有讀取（`GROK-R1-P1-01`）
**處置**：normalize＋守衛移到 lock 外，lock 內只賦值／遞增 revision／快取失效；三寫點與 refilter 改在 lock 外呼叫（完成路徑先寫 result 再標 completed，守衛 raise 仍由背景 except 標 failed）；測試 `test_set_result_does_not_hold_lock_during_normalize`。

### Q2 — P2 字串欄 desc 用字元碼取負 ⇒ 前綴名錯序（`GROK-R1-P2-01`）
**處置**：`build_sort_index` 對字串欄改 `sorted(..., reverse=desc)`；golden 加 `feature_name_desc_top5`／`prefix_desc`；測試含 `close/close_sma/close_sma_20`。

### Q3 — P1 快取 key `pass_class or ""` 合併 None 與空字串（`CODEX-R1-P1-01`）
**處置**：key 以 sentinel 區分 None／""；測試 None ⇒ 2 列、"" ⇒ 1 列；mutation P14 錨點同步。

### Q4 — P1 探針在 app import／Binance ping 失敗時無 token、rc=1（`CODEX-R1-P1-02`）
**處置**：探針主體包 try ⇒ 任何 setup 失敗轉恰一行 `*_GATE=BLOCKED`＋`*_REASON=setup failed(...)`、rc=2；測試以 `ICRESULT_PROBE_FORCE_SETUP_FAIL` 注入。

Verdict: 可合併（修補後）——Q1–Q4 已修並加測試；gate 1（17 mutation 紅、UNCOVERED=0）與 gate 3（SIZE／LATENCY PASS）重跑 PASS；B2 已實作（`bf3afad1`），另派前端 review。

---
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: `pass_class=None`（不篩選）與 `pass_class=""`（精確空字串）共用同一排序 cache key，會回傳錯誤列集。
**碼證**: `api/services/ic_result_projection.py:118-123,146-148`；VERIFY：反例輸出 `cache_none_total 2 cache_empty_total 2 cache_empty_rows ['empty', 'keep']`，後者應為 1 列。
**來源摘要**: api/services/ic_result_projection.py#4453b9d477f4；docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；`pass_class or ""` 把兩個語意合併，HTTP `?pass_class=` 可觸發 stale rows。修法是保留 None 與空字串的區分；RECHECK：同一 task/revision 先呼叫 None 再呼叫空字串，斷言 total/rows 分別為 2/1。
## CODEX-R1-P1-02
**斷言**: G-5/G-9 size probe 在離線環境未輸出規定的單一 `SIZE_GATE`/`LATENCY_GATE` token，phase gate 因未處理的 app import 例外而不可執行。
**碼證**: `handoffs/20260909-probe-icresult-size.py:43-46`；VERIFY：`probe --size`、`--latency` 均 rc=1，stderr traceback 為 `ConnectionError ... api.binance.com`，stdout 無 token；`test_size_probe_emits_single_token_line` 為 0 lines。
**來源摘要**: handoffs/20260909-probe-icresult-size.py#58a2c469b953；docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；probe 只捕捉 projection import，未捕捉 `api.main`／Binance ping 的 setup failure，違反三態 gate 的可解析輸出並阻斷離線驗收。修法是隔離 IC app 或將 setup failure 轉為明確 BLOCKED；RECHECK：無 Binance 網路時仍恰一行 token 且 rc 與三態一致。
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

