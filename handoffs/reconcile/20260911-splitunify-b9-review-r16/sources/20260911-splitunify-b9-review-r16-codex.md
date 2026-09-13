# SPLITUNIFY b9 review-r16 — codex；輸入邊界：current block＋79b66dd1 diff；未改碼、SPEC 正文或 TODO。
## CODEX-R16-P1-01
**斷言**: Task 9.3 的 keyed receipt 對證不可執行：D-002-C5 多數列沒有可解析的 repo-relative `path:line`，C5-25 更只有「ic_feed survivor 餵入端」，因此不能決定 receipt 的路徑是否與同列 register 相同。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:652
MUTATION: 構造合法 TASK/COMMIT 與 C5-01..29 receipt，將 C5-25（或任一無 target 的列）碼證替換成任意真實 `path:line`，執行 TODO:652-656 keyed 對證；該列沒有可比對的 register RHS。
**來源摘要**: docs/SPLITUNIFY_TODO.md#33911fd6b944
[MAJOR] 信心度=High；無完整 file:line 的列為 C5-01/02/03/04/05/06/07/08/10/11/12/15/16/17/18/20/22/24/25；只有 basename/module token 的列為 C5-09/13/14/19/21/23/26/27/29；C5-13/27 雖有多個範圍但仍是同一未限定 basename 檔，沒有明列多檔集合。最小修補：在每列消費面末尾補 `TARGETS: <repo-relative-path>:<start>-<end>[; <repo-relative-path>:<start>-<end>...]`，receipt 僅在 path 精確命中同列 TARGETS 且行號落在範圍內通過；C5-25 至少錨 `momentum/Analysis/event_samples/ic_feed.py:56-65`。不要放寬成任意檔案存在即可。
### 必答
(1a) `CODEX-R15-P1-01` STILL-OPEN；`CODEX-R15-P1-02`、`CODEX-R15-P1-03`、`CODEX-R15-P1-04` CLOSED；同型 `COMPOSER-R15-P2-01` 亦仍受同一 register 落點缺口影響。
(1b) `rg -n 'M-SU-D2-(38|39|40)' docs/SPLITUNIFY_SPEC.D-002.md` 取得 v16 三條修補；hash probe `event_context_from_windows([w])` 對 `[w,w]` 輸出 `same=False` rc=0；pandas probe 輸出 `ValueError: cannot reindex on an axis with duplicate labels`；`pytest -q` 三檔輸出 `93 passed`。
(2a) 逐列 scan 明確列出上述 19 個無完整 target、9 個 basename/module-only；沒有一列明確寫出多檔集合，C5-13/27 是同檔多範圍而非多檔。
(2b) 最小字面為：`每列消費面末尾必有 TARGETS: <repo-relative-path>:<start>-<end>[; ...]；receipt path 必須精確命中同列 TARGETS 且 line 落範圍；禁止 module-only 或裸 :line`；多落點才用明列集合，不採任意檔集合放寬。
(3a) 不是同一個可驗證落點：C5-25 未寫行；現有 caller 是 `momentum/Analysis/event_samples/pipeline.py:406-408`，hash rows/seam 是 `momentum/Analysis/event_samples/ic_feed.py:56-65`。
(3b) 既然 v16 測試直接呼叫函式，正確 seam 應固定為 `ic_feed.py:56-65`，並把 C5-25 改成該 TARGET；若要 caller 去重則改寫 M38 與測試一併固定 `pipeline.py:406-408`，不可兩者混用。
(4a) 有三個既有相關測試不會因新破壞而紅：`test_conditional_ic_feed_emits_event_context`（只驗 hash 形狀）、`test_insufficient_events_in_test_is_per_symbol_not_batch`（無 1 event×2 TF fixture）、`test_discrimination_oos_only_and_kind_strata`（assignments index 唯一）；這不否定 v16 要新增的具名 mutation tests。
(4b) `nl -ba tests/momentum/event_samples/test_gap3_conditional_ic.py | sed -n '104,109p'`、`.../test_splitunify_derive.py | sed -n '1153,1162p'`、`.../test_tables.py | sed -n '106,121p'`；三段皆無重複 TF/duplicate symbol fixture；named test sweep 對 M38/M39/M40 新測試輸出 `missing`。
(5a) 本輪 finding 明確屬「register 錯配／落點不足」，不是 P2 級字面問題；mutation 條數實查為 40、C5 register 為 29。
(5b) 依 r15 停輪判準，本票停輪並回報使用者；不可進 `Task 9.1`。
(6a) body sha256 `8607f2b770fb39f967c7c75686a90f4c1bc39a7d1536cc70bca1909e838021a0` 判 `REJECTED`。
(6b) 唯一阻擋項 `CODEX-R16-P1-01`：一次修訂補齊每列 repo-relative TARGETS、C5-25 的 ic_feed seam，並讓 keyed checker 對 path＋line range；修補後可關閉。
ASSUMPTIONS_VERIFIED: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`→8607…021a rc=0；兩份 doc_format_precheck rc=0；mutation=40、register=29；direct probes 與 93-test targeted run 如上。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/event_samples/test_tables.py tests/momentum/Analysis/test_splitunify_derive.py`→93 passed rc=0；`pytest --collect-only`→93 collected rc=0；hash probe rc=0；pandas probe預期 rc=1。
FAILURES_SEEN: pandas probe 的 rc=1 是預期 duplicate-index `ValueError`，非未解決測試失敗；無其他未解決失敗。
SCOPE_CHANGES: 新增本交件；僅在 SPEC `## 戳記` append codex REJECTED stamp；未改碼、SPEC 正文、TODO、HANDOFF.md、data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 無 runtime/schema/output-size 變更；僅拒絕 v16 文件簽核。
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r16-codex.md`。
VERDICT: blocked
BLOCKED-BY: CODEX-R16-P1-01
CLOSED: CODEX-R15-P1-02,CODEX-R15-P1-03,CODEX-R15-P1-04
STATUS: DONE
