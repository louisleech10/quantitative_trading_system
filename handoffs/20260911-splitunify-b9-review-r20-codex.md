# SPLITUNIFY b9 — review-r20（B9B Task 9.2＋9.2a）— codex 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R20`；**審查標的**: `9e87386f`；**範圍**: brief 指定 current block＋本輪 diff；review-only。

## CODEX-R20-P1-01

**斷言**: `Task 9.2a` 要求的 `test_multi_feature_tf_opposite_sides_must_fail_closed`（`xfail(strict=True)`）未存在；因此異側／混態的機械驗收可被刪除或從未加入而不會讓測試失敗。

**碼證**: `docs/SPLITUNIFY_TODO.md:539-542` 明定逐字 node id 與 `1 xfailed`；`rg -n 'test_multi_feature_tf_opposite_sides_must_fail_closed' tests` 無命中；`venv/bin/python -m pytest -rxX 'tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed'` → collected 0 items、`no tests ran`、rc=4。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:539
MUTATION: 從 `tests/momentum/Analysis/test_splitunify_derive.py` 移除或不加入該測試函式，再執行指定 node；現況已重現 `no tests ran` rc=4。

**來源摘要**: docs/SPLITUNIFY_TODO.md#3761a7b4a8ac

[P1] 信心度=High。這是驗收閘缺失，不是把尚未實作的 `Task 9.2b` 行為誤判成 B9B 缺陷；混態本身已由 TODO 明列為 9.2b 過渡行為。**修法**：新增同名測試，以事件級 manifest、兩個 feature TF 且不同 cutoff 的 fixture，`@pytest.mark.xfail(strict=True, reason="Task 9.2b: event-level anchor + AlignmentViolationError")`，預期目前版本 xfailed，9.2b 完成後解除 xfail。**可行性證據**：mixed-cutoff probe 已實跑 `rc=0`，輸出同一 `event_id` 的 `1h` 為 `purged`、`4h` 為 `train` assignment；故反例可穩定構造，測試不是空殼。

## CODEX-R20-P2-01

**斷言**: 多 symbol Mapping 分支的 `n_events`、`n_event_tf_rows`、`n_event_tf_rows_purged` 沒有具名測試；三個 summary 值可在直接相關測試全綠時退化。

**碼證**: `momentum/Analysis/event_samples/split_projection.py:767-770` 是多 symbol 三鍵的唯一組裝點；現有 `tests/momentum/Analysis/test_splitunify_derive.py:1451-1474` 只驗 discarded 傳遞，`1573-1581` 的三鍵測試只走單 symbol；runtime mutant 將多 symbol 三鍵置零後，兩個直接相關 test files 仍 `104 passed` rc=0。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#bd27c2f92a20

[P2] 信心度=High；production 計算本輪 probe 正確，問題是覆蓋缺口。**修法**：新增 `test_multi_symbol_summary_has_n_events_and_n_event_tf_rows`，用兩 symbol、每事件兩 feature TF、至少一 symbol 的空 purge 子批，斷言 `n_events == keys.event_id.nunique()`、`n_event_tf_rows == len(keys)`、`n_event_tf_rows_purged == len(plan.purged)`，並驗 `feature_timeframe` 欄集。

### §0 被當成事實的假設核對

brief 的 mixed-cutoff「不會混態」假設已被反例推翻，但依 TODO 屬 `Task 9.2b`，不在本批重開；多 symbol 三計數與空 purge concat 已實跑確認（`5 events / 10 TF rows / 2 purged rows`）；brief 所載六路回歸 `705 passed` 本輪視為既有 receipt，未重跑，另有本輪直接相關基線 `104 passed`。

### §1 必查（11 類）

1 矛盾/互斥：無；2 漏項/端到端：P1-01、P2-01；3 不可測驗收：P1-01；4 quant 假設：無；5 過度工程：無；6 OOM/並行：無；7 cache：無；8 API/型別/相容：無；9 測試品質：P1-01、P2-01；10 Agent 可執行性：P1-01 使指定 node 不可執行；11 必要性/短命工：無。

### §2 範本錨點與空殼

現行 `Task 9.2`／`9.2a` 的欄位、驗證命令、golden 與存活／覆蓋風險均有實質內容；P1 finding 的 anchor 位於現行 TODO 段，不在 HISTORY 區；無新增 quant、cache、OOM 或 schema 數值變更。

### 必答

1a. **會混態**：不同 cutoff 的多 TF probe → `mixed_cutoff_rc=0`、同一事件 `1h=purged`、`4h=train assignment`。1b. **屬 `Task 9.2b`**：TODO 9.2b 明定事件級 `decision_at_ms` 錨定與異側 fail-closed；本批不加第二份判側邏輯，但必須先補 P1-01 的 xfail 機械閘。

2a. **正確**：多 symbol probe → `summary_counts={'n_events': 5, 'n_event_tf_rows': 10, 'n_event_tf_rows_purged': 2}`；purged 欄為 `event_id/reason/feature_timeframe`，其中一個 symbol 子批為空仍正確 concat。2b. **該補**：`test_multi_symbol_summary_has_n_events_and_n_event_tf_rows`，斷言上述三鍵分別等於 `event_id.nunique()`、`len(event_keys)`、`len(purged)`。

3a. production 只有 `split_projection.py:259-360` producer（輸出 `feature_timeframe`）、`pipeline.py:756-759` caller（不自行建表）；golden `scripts/freeze_splitunify_golden.py:108-111` 與測試 helper `tests/momentum/Analysis/test_splitunify_derive.py:116-140` 已含欄。另掃到歷史 negative-injection helper `handoffs/20260911-probe-splitunify-negative-injection.py:48-53` 未含欄；它未被 production/API 引用，`handoffs/20260911-splitunify-b9-probe-multitf.py` 只建 `per_tf` 並呼叫 producer。3b. **不阻擋**：歷史探針若要重用需另行更新，非本輪 current production constructor。

4a. **逐值未變**：`git show 9e87386f^:tests/golden/splitunify/splitunify_golden.json | cmp -s - tests/golden/splitunify/splitunify_golden.json` → rc=0；`jq -S` sorted JSON compare → rc=0；頂層 11 鍵為 `_doc g1_membership g3b_oracle g4_per_symbol_n g5_answer_window g5_row_fingerprint_first_ms g5_row_fingerprint_last_ms g5_row_fingerprint_n g5_row_fingerprint_positions g5_row_fingerprint_sha256 purge_reasons`。4b. **無變動鍵**。

5a. **會 raise**：selected `1h`、未選中 `4h` 的 `timeframe=NaN` probe → rc=1，錯誤為 `build_event_keys: per_tf 之 timeframe 欄有缺值 ... fail-closed`。5b. **預期**：`split_projection.py:298-304` 明定提前到全欄，避免全量模式或 discarded summary 產生假 TF；不修。

6a. **有第六種**：缺失的 strict-xfail node 是可讓異側驗收失效而現有 suite 綠的獨立破壞；直接相關兩檔 runtime mutant 亦以多 symbol 三鍵全置零後 `104 passed` rc=0（P2-01）。6b. **先修 P1-01 再進 `Task 9.2b`**；混態行為本身留給 9.2b，測試錨點不可缺席。

ASSUMPTIONS_VERIFIED: mixed cutoff、multi-symbol 三計數／空子批、NaN 全欄 fail-closed、golden 11 鍵逐值、constructors 掃描、strict-xfail node 缺失均附本檔命令或輸出摘要；705 passed 僅引用 brief receipt。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 104 passed rc=0；缺失 xfail node → no tests ran rc=4；mixed/multi-symbol/NaN runtime probes；golden `cmp` 與 sorted JSON compare 均 rc=0。
FAILURES_SEEN: 初次 probe 誤讀測試 helper 名稱而 ImportError（未改檔），改用 inline receipts 後完成；`scripts/restore_golden_inventory.sh` 因受限環境無法建立 `.git/index.lock`，rc=128，未改 production code。
SCOPE_CHANGES: 僅新增本交件檔；未改程式、SPEC、TODO、data_cache；歷史 handoff constructor 僅列為非阻擋觀察。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值、schema、golden 或輸出檔；review 僅指出缺失測試與必要測試覆蓋。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r20-codex.md

VERDICT: blocked
BLOCKED-BY: CODEX-R20-P1-01
CLOSED:
