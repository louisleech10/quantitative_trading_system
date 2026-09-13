# SPLITUNIFY b9 — review-r21（B9B D1／D2 閉合再驗證）— codex 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R21`；**範圍**: brief 指定 current block＋`git show ef4d0664`；review-only。

## CODEX-R21-P1-01

**斷言**: 異側 fixture 確實把同一事件分到 train/test，但 anchor 測試以 `Exception`＋寬 regex 驗收，且 `xfail(strict=True)` 在 9.2b 正確落地時不會自然變 pass；若只拿掉 decorator，錯誤型別仍可被誤收。

**碼證**: `--runxfail` 實跑為 `1 failed`、`Failed: DID NOT RAISE <class 'Exception'>`；同一 fixture 直接探針為 `TRAIN_CUTOFF_IN_TRAIN True`、`TEST_CUTOFF_IN_TEST True`、assignments 同時含 `train`／`test`，purged 為空。`pytest` 的 `match` 比對例外訊息，不會自動把類名 `AlignmentViolationError` 放入訊息。
CODE-ANCHOR: tests/momentum/Analysis/test_splitunify_derive.py:1635
MUTATION: 在 9.2b 完成後只移除 `xfail(strict=True)`、保留 `pytest.raises(Exception, match=...)`，再以非 `AlignmentViolationError` 但含「異側」訊息的例外替換實作 raise。

**來源摘要**: tests/momentum/Analysis/test_splitunify_derive.py#d7e295e56d42

[MAJOR] 信心度=High；這不是把 9.2b 尚未實作誤報成 B9B 缺陷：目前 xfail 的 `DID NOT RAISE` 是預期過渡狀態，但「自然變 pass」前提為假，且寬例外會讓未來錯誤實作過閘。修法：9.2b 同批移除 strict xfail，改用 `pytest.raises(AlignmentViolationError, match=re.escape("e_x"))`（或等價地驗證規格要求的 event id）；不要把 regex 收成字面 `AlignmentViolation`，因為那不是例外訊息契約。可行性證據：`momentum/core/contracts.py:933` 已有該類別，TODO 9.2b:592-595 明定類別與 event id；上述 fixture 探針已實測為異側。

## CODEX-R21-P1-02

**斷言**: TODO 現行 `Task 2.2` 仍要求 `selected_timeframe` 單選、每事件恰一列、以及 12-key summary，未標示 superseded；它與現行 B9B producer tuple/full-scan contract 及 16-key summary 互斥，後續實作者依較早段落會回退已完成行為。

**碼證**: `docs/SPLITUNIFY_TODO.md:221-237` 仍寫舊契約；現行 `build_event_keys` 為 `selected_timeframe: Optional[str] = None` 並回 `(keyed, discarded)`，`_build_summary` 實作 16 keys。scoped 回歸中的 `test_build_event_keys_full_scan_is_default`、`test_summary_has_all_sixteen_keys` 均 pass。
CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:259
MUTATION: 依 `docs/SPLITUNIFY_TODO.md:221-237` 把 `selected_timeframe` 改回必填/單值回傳並保留 12-key summary，再跑 B9B named tests；全量與 exact-set 測試即轉紅。

**來源摘要**: docs/SPLITUNIFY_TODO.md#6dd7a70a9b0d

[MAJOR] 信心度=High；這是 live TODO 的可執行契約矛盾，不是 HISTORY 殘留。修法：將 Task 2.2 的 producer、summary 段改成明確指向 Phase 9 `Task 9.2`／`9.2a` 的現行契約，或逐字標為 superseded，避免同一份 TODO 同時存在兩個接口真相。可行性證據：現行實作與 named tests 已完成 Optional/full-scan、tuple 與 16-key exact-set；只需文件同步，不需改數值或 schema。

### §0 被當成事實的未驗證假設

`xfail` 會在 9.2b 完成後自然 pass：**否證**，strict xfail 會把 XPASS 判失敗；match 只收 `AlignmentViolation`：**否證**，應驗證類別＋event id。其餘 brief fact claims 以本檔命令複驗。

### §1／§2／§3 必查摘要

1 矛盾/互斥：P1-02；2 漏項/端到端：無第四個 producer/caller；3 不可測驗收：P1-01；4 quant：無；5 過度工程：無；6 OOM/並行：無；7 cache：無；8 API/型別：無；9 測試品質：P1-01；10 Agent 可執行性：P1-02；11 必要性/短命工：無。§2 錨點與內容非空；§3 不可違反原則無新違反。

### 必答

1a. `CODEX-R20-P1-01=CLOSED`、`CODEX-R20-P2-01=CLOSED`。1b. exact node 命令得 `1 xfailed`；D2 named test 得 `1 passed`；完整兩檔得 `105 passed, 1 xfailed`。
2a. 是異側 fixture，但目前沒有 raise；`--runxfail` 觀測為 `DID NOT RAISE`，非某個例外訊息。2b. 不應只 match 字面 `AlignmentViolation`；應收緊為 `AlignmentViolationError` 類別並 match `e_x`。
3a. strict xfail 的摩擦是預期且明確：9.2b 完成時必須同批移除 decorator；skip 會藏掉機械 gate，不較好。3b. 可直接替換為 `with pytest.raises(AlignmentViolationError, match=re.escape("e_x")):` 並移除 xfail。
4a. 無第四處：生產 `build_event_keys(` 只有 `pipeline.py:756`；golden `_event_keys` 與 negative-injection `_keys` 已有 `feature_timeframe`，multi-TF probe 只建合法的 `per_tf` 輸入且已改兩值 unpack。4b. 不阻擋。
5a. 目前不能標 `proceed`：P1-01 須納入 9.2b 閉合集合，P1-02 須先消除 TODO 雙真相。5b. 最小閉合集合即上述兩條修法；D2 計數本身不需再改。

ASSUMPTIONS_VERIFIED: stamp check rc=0；異側 fixture side membership；xfail `1 xfailed` 與 `--runxfail` 的 `DID NOT RAISE`；D2 `1 passed`；全 scoped 回歸 `105 passed, 1 xfailed`；全 repo producer caller 掃描無第四處。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`venv/bin/python -m pytest -rxX -vv --runxfail tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 failed, DID NOT RAISE；`venv/bin/python -m pytest -q -rxX tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 105 passed, 1 xfailed。
FAILURES_SEEN: 第一次 inline fixture probe 將 `_plans()` 三值誤解為四值而退出；未改檔，修正 unpack 後取得上述 side/assignment 輸出。
SCOPE_CHANGES: 僅新增本交件檔；未改程式、SPEC、TODO、data_cache、根 HANDOFF。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值、schema、golden 或輸出；P1-02 僅指出文件契約漂移。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r21-codex.md

VERDICT: blocked
BLOCKED-BY: CODEX-R21-P1-01,CODEX-R21-P1-02
CLOSED: CODEX-R20-P1-01,CODEX-R20-P2-01
STATUS: DONE
