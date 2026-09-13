# Reconcile — 20260911-splitunify-b9-review-r21

**來源** 20260911-splitunify-b9-review-r21-codex.md, 20260911-splitunify-b9-review-r21-composer.md, 20260911-splitunify-b9-review-r21-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **E1 xfail 錨點測試之例外斷言太寬，`Task 9.2b` 落地時仍可誤收**——「異側fixture確實把同一事件分到tr」 | P1 | CODEX-R21-P1-01 | 採納（🔴 **這正是主委在 brief assumed 第 1 條自問「match 是否該收緊成僅 `AlignmentViolation`」的答案，該家判「是」並補出第二個理由**：原寫 `pytest.raises(Exception, match="同一事件\|異側\|同側\|AlignmentViolation")` ⇒ ①`Exception` 太寬，連「fixture 自己壞掉」都算 xfail 通過；②寬 regex 使 9.2b 落地時**錯誤型別仍可被誤收**。改法：釘死 `AlignmentViolationError`（`momentum/core/contracts.py:933`，`ValueError` 子類，**已存在**）＋訊息須含該 `event_id`（`D-002-C3` (3.2) 明定）。⇒ 9.2b 若用別的型別或不帶 `event_id`，本測試**不會**變 XPASS 而是繼續紅——那是對的） |
| **E2 TODO 舊段 `Task 2.2` 與 B9B 契約互斥且未標 superseded**——「TODO現行`Task2.2`仍要求`s」 | P1 | CODEX-R21-P1-02 | 採納（🔴 **這是「文件舊段落落後於新實作」的第三次發作**——前兩次是 SPEC `§P` 落後於 `§V`（R19）與 §P 之 Task 9.1 兩處字面（R19 同輪）。本次在 TODO：`Task 2.2` 仍寫 `selected_timeframe` 單選、每事件恰一列、12 鍵 summary，後續實作者依較早段落會**回退已完成行為**。改法：三處各加 SUPERSEDED 標記並指向 `Task 9.2`／`Task 9.2a`，原字面保留供追溯。🔴 **主委同型自查另補一處該家沒點名的**：§E 殘留表之 `SU-RESID-2` 描述的正是 B9B 剛解掉的東西，本身就該關 ⇒ 已標**已關閉（2026-09-14，批次 B9B）**並註明 `Task 9.3` 為其下游延續） |
| **E3 composer 零 findings、判可收斂**——「本輪逐項核對後無需阻擋收斂之findin」 | P3 | COMPOSER-R21-P3-00 | 採納（該家 CLOSED 自提之 `COMPOSER-R20-P1-01`／`P2-01`，判 proceed） |
| **E4 grok 零 findings、兩條自提全 CLOSED**——「本輪逐項核對後無finding；本家R2」 | P3 | GROK-R21-P3-00 | 採納（該家 CLOSED 自提之 `GROK-R20-P1-01`／`P2-01`，判 proceed） |

### 本輪裁定
1. **review-r20 之六條 finding 全數由原提出方 CLOSED**（codex 二、composer 二、grok 二）。
2. **E1／E2 已修**；回歸 **706 passed、1 xfailed**（xfail 收緊為 `AlignmentViolationError` 後仍正確為 xfail，非 XPASS）。
3. 🔴 **本輪最值得記的一件事**：E2 是「文件舊段落落後於新實作」的**第三次**發作（R19 兩次在 SPEC、本次在 TODO）。三次的形狀完全相同——**改了新段落、沒回頭標舊段落**。⇒ 日後凡改動契約面（簽章、預設值、鍵集、唯一性判準），須**全檔掃該契約的舊描述**並逐處標 superseded，不能只改當前 Task 段。
4. **下一步**：派 `review-r22` 做 E1／E2 閉合再驗證；三家確認後進 `Task 9.2b`（批次 **B9C**）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R21-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；本家 R20 兩條反例均已 CLOSED，brief 兩條 assumed（9.2b 自然 pass、xfail 最佳）經探針與條文對讀確認可接受。

**碼證**: `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed** rc=0；六路回歸 `-rxX` → **706 passed, 1 xfailed** rc=0；`/tmp/r21-composer-probe-opposite.py` → `NO_EXCEPTION`＋異側 assignments；`/tmp/r21-composer-mutation2.py`（省略多 symbol 三 kwargs）→ **1 failed** `assert 0 == 6`（已還原）；`rg build_event_keys|def _event_keys|def _keys` 全 repo 無第四處缺 `feature_timeframe`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#6dd7a70a9b0d

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R20-P1-01,COMPOSER-R20-P2-01

ASSUMPTIONS_VERIFIED: xfail 1 xfailed；706+1xfail 回歸；異側探針 NO_EXCEPTION；多 symbol mutation 轉紅；event_keys 全掃無第四處；match／xfail 交接分析
TESTS_RUN: `pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 xfailed；六路 `pytest -q … -rxX` → 706 passed 1 xfailed；`pytest -q …::test_multi_symbol_branch_summary_counts_are_named` → 1 passed；`/tmp/r21-composer-probe-opposite.py`；`/tmp/r21-composer-mutation2.py` → MUTATION_RC=1 後還原
FAILURES_SEEN: none（review-only；mutation 預期失敗已還原）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r21-composer.md

STATUS: DONE
## GROK-R21-P3-00

**斷言**: 本輪逐項核對後無 finding；本家 R20 兩條反例均 CLOSED，xfail 確因異側靜默而未 raise，可進 Task 9.2b（B9C）。

**碼證**: `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed**；剝 xfail 後同 node → **FAILED DID NOT RAISE**；直呼 derive → `e_x` 之 `1h→train`／`4h→test`（`nunique_split_label=2`）；`pytest …::test_multi_symbol_branch_summary_counts_are_named` → **1 passed**；omit Mapping 三 kwargs → 該測 **FAILED assert 0==6**（已還原）；scoped 四節點 → **3 passed, 1 xfailed**；`negative-injection._keys` 含 `feature_timeframe`；builder 掃描無第四缺欄處。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R21-BRIEF.md#8905ce34a88f

[P3] 信心度=High。閉合輪 sentinel；D1／D2 由本家原反例重跑驗證。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R20-P1-01,GROK-R20-P2-01

ASSUMPTIONS_VERIFIED: TODO 第 6 條 1 xfailed；異側 fixture 靜默雙側＋DID NOT RAISE；P2 omit-kwargs 轉紅後還原；match 不宜收緊為僅 AlignmentViolation（str(exc) 不含類名）；xfail(strict=True) 在 TODO 契約下最佳；無第四 event_keys 缺欄處；可進 B9C
TESTS_RUN: `pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 xfailed；剝 xfail → DID NOT RAISE；`pytest …::test_multi_symbol_branch_summary_counts_are_named` → 1 passed／mutation 下 1 failed 後還原；scoped 四節點 → 3 passed, 1 xfailed
FAILURES_SEEN: none（mutation／剝 xfail 預期失敗已還原；生產檔 `git diff` 空白）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r21-grok.md

STATUS: DONE
