# SPLITUNIFY b9 — review-r20（Task 9.2＋9.2a／B9B 審碼）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R20`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R20-BRIEF.md`  
**findings-round**: R20  
**brief-kind**: review  
**審查標的**: commit `9e87386f`；current block＝`split_projection.py`（`build_event_keys`／`EVENT_KEY_COLUMNS`／`_derive_single_symbol` guard＋兩表／多 symbol／`_build_summary`）／`pipeline.py` 投影三參數閘／`scripts/freeze_splitunify_golden.py` `_event_keys`／`docs/SPLITUNIFY_TODO.md` §C-9 Task 9.2＋9.2a  
**禁改碼／禁改 SPEC／禁改 TODO**（本檔只產 findings）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 回歸 705 passed | **fact-verified（本家抽樣）** | 本家實跑 scoped：`test_splitunify_derive.py`＋`test_splitunify_wiring.py` → **104 passed**；全量 705 以 receipt `20260913T165740Z-splitunify-b9b-task92-92a` 為權威，本家未重跑全套 |
| brief fact-verified: 五種破壞各自轉紅 | **未本家重跑** | 標「未經覆核」；不另開 finding（brief 已附） |
| brief fact-verified: golden 值未動／三條全綠 | **fact-verified** | `git rev-parse 9e87386f^:tests/golden/splitunify/splitunify_golden.json`＝`HEAD:` 同 blob `2cb1b974…`；JSON 11 頂層鍵逐值 `IDENTICAL` |
| brief fact-verified: summary 16 鍵 exact-set | **fact-verified** | `test_summary_has_all_sixteen_keys` 在 scoped 回歸內 PASSED |
| brief assumed: 多 TF 不同 cutoff **不會**混態 | **fact-verified（不成立＝會混態）** | `/tmp/r20-grok-workdir/probe_r20.py` 三變體皆混態；判屬 `Task 9.2b` |
| brief assumed: 多 symbol 三計數正確 | **fact-verified（值正確）** | 同探針：`n_events=3`／`n_event_tf_rows=6`／`n_event_tf_rows_purged=2` 與真值相符；**但缺具名測試**（見 P2） |

---

## 必答 1 — cutoff 不同之多 TF 混態

### (1a)

**會。** 現行判側逐列讀 `feature_cutoff_ms`（`split_projection.py:608-640`），同事件兩 feature TF 之 cutoff 不同時可落入不同側。實跑三變體（`/tmp/r20-grok-workdir/probe_r20.py` → `probe_r20_out.json`）：

| 變體 | 觀測 |
|------|------|
| v1 train vs test | `e_mix`：`1h→train`、`4h→test`（同表異 `split_label`） |
| v2 answer-window purge vs train | `e_mix2`：`1h→purged`、`4h→train`（跨表混態） |
| v3 train vs gap-purge | `e_mix3`：`1h→train`、`4h→purged`（跨表混態） |

### (1b)

**屬 `Task 9.2b`，現在不擋本批。** 依據：TODO `Task 9.2a` 明定判側仍 `feature_cutoff_ms`、異側 `AlignmentViolationError` 屬 9.2b；`_multi_feature_tf_case` 刻意讓兩 TF cutoff **相同**；碼註亦寫跨表互斥待 9.2b。最小修法不在本批（事件級錨定＋同側／跨表互斥）。惟 9.2a 應留下的 xfail 錨點**缺席** → 見 `GROK-R20-P1-01`。

---

## 必答 2 — 多 symbol 三計數

### (2a)

**現行值正確。** 構造 ETH×2 事件×2 TF＋BTC×1 事件×2 TF（其一 symbol 之 purged 為空）走 Mapping 分支：`n_events=3`、`n_event_tf_rows=6`、`n_event_tf_rows_purged=2=len(purged)`；`purged` 經 concat 後欄集仍含 `feature_timeframe`。單標的空批欄集亦含該欄，三計數皆 0。空 symbol 子批不會靜默發生（`event_symbols != plan_keys` 先 fail-closed）。

### (2b)

**該補具名測試。** 建議名：`test_multi_symbol_branch_summary_event_and_tf_row_counts`。斷言：`n_events == event_keys["event_id"].nunique()`、`n_event_tf_rows == len(event_keys)`、`n_event_tf_rows_purged == len(purged)`，且 fixture 須 **多 symbol＋多 feature TF**（單 TF 時 `nunique==len` 抓不到「以列數冒充事件數」）。實跑破壞：刪多 symbol 分支三 kwargs → summary 變 `0/0/0` 且 **104 條仍全綠**（見 P2）。

---

## 必答 3 — 全 repo 建構 `event_keys` 而未加 `feature_timeframe`

### (3a)

逐處：

| 處 | 有無 `feature_timeframe` | 角色 |
|----|--------------------------|------|
| `split_projection.build_event_keys` | **有**（rename自 `per_tf.timeframe`） | 唯一生產 producer |
| `pipeline.py:756` | 經 producer | 唯一生產 caller |
| `scripts/freeze_splitunify_golden.py:_event_keys` | **有**（`"1h"`） | golden 工具 |
| `tests/.../test_splitunify_derive.py:_event_keys` | **有** | 測試 helper |
| `handoffs/20260911-probe-splitunify-negative-injection.py:_keys` | **無** | 舊探針（非生產） |
| `handoffs/` 其他 backup／研究探針 | 多為 `per_tf` 形或舊 schema | 非生產 |

生產／golden／現行測試 helper：**無**缺欄建構者。`api/` 無 `build_event_keys`／`EVENT_KEY_COLUMNS` 組裝點。

### (3b)

**不阻擋。** 舊 handoffs 探針缺欄會被 `EVENT_KEY_COLUMNS` 入口檢查擋下，不進生產鏈。

---

## 必答 4 — golden 11 頂層鍵逐值

### (4a)

**逐值未變。** `9e87386f` 未改 `tests/golden/splitunify/splitunify_golden.json`；parent／HEAD／該 commit 之 blob 皆 `2cb1b974835f49929ea439ebe4f91c8b3728c74c`；載入前後 JSON `changed_count=0`／`IDENTICAL`。11 鍵：`_doc`、`g1_membership`、`g3b_oracle`、`g4_per_symbol_n`、`g5_answer_window`、`g5_row_fingerprint_*`（5）、`purge_reasons`。

### (4b)

**N/A**（無變動）。

---

## 必答 5 — NaN fail-closed 提前到全欄是否誤殺

### (5a)

**單選模式在「缺值只在未選中側」時會 raise。** 實跑：`selected_timeframe="1h"`＋未選側 `timeframe=None`／`pd.NA` ⇒ `ValueError: …缺值（NaN／NA）…`；全量模式同樣 raise；乾淨雙 TF 單選 ⇒ `OK n=1 discarded={'4h':1}`。

### (5b)

**屬預期，非本批回歸誤殺。** 對照 R18 舊邏輯只查 `dropped.isna()`：同一「NaN 在未選側」案例下 `dropped.isna().any()` 亦為 True ⇒ R18 單選**已會** raise。`Task 9.2` 把檢查提前到全欄，是為全量模式（無 dropped 側）補同一 fail-closed；單選行為相對 R18 不變。壞資料不得產出假 TF 名 `'nan'`。

---

## 必答 6 — 第六種破壞／可否進 9.2b

### (6a)

**針對「全量輸出」四層：本家未另找到第六種使全量失效且測試仍綠的破壞**（五種 brief 已列者本家未重跑）。  
**相關第六種（計數層／驗收層，非全量本身）已抓到兩條：**

1. 多 symbol 分支省略三計數 kwargs → summary 變 0 且 scoped **104 passed**（P2）。  
2. TODO `Task 9.2a` 第 6 條 xfail node **整段缺席** → 驗收命令 `ERROR: not found`／`collected 0`（P1；刪測換綠的極致形態）。

另：多 symbol 空批 fallback 欄集拿掉 `feature_timeframe` 亦 104 全綠（該分支僅在 `plans={}` 空 Mapping 才走到，實務難達）——記為誠實邊界，不另開 finding。

### (6b)

**不可直接進 `Task 9.2b`。** 最小閉合：`GROK-R20-P1-01`（補回 `xfail(strict=True)` 錨點並通過 TODO 第 6 條機械驗收）。P2 建議同批補，不構成第二個閉合門檻。混態本身屬 9.2b，不阻本裁決。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：TODO 第 6 條要求之 xfail node 與測試樹互斥（缺席）→ P1。  
2. 漏項：多 symbol 三計數無具名測 → P2；xfail 錨點未落地 → P1。  
3. 不可測驗收：第 6 條命令現況不可得 `1 xfailed`。  
4. 可疑 quant：混態在不同 cutoff 下可達，已標屬 9.2b。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：`selected_timeframe` Optional＋三參數閘＋去 `str(None)` 與 TODO 一致。  
9. 測試品質：P1／P2。  
10. Agent 可執行性：TODO 第 6 條可執行但現況 fail-closed 於缺測。  
11. 必要性／短命工：xfail 錨點存活至 9.2b 解除——缺它則 9.2b「解除 xfail」無標的。

---

## GROK-R20-P1-01

**斷言**: `Task 9.2a` 明文要求之機械驗收錨點 `tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`（`xfail(strict=True)`）在測試樹中**整段缺席**，TODO 第 6 條驗收命令得到 `ERROR: not found`／`collected 0`，等同「刪測換綠」且使 `Task 9.2b` 失去可解除之 xfail 標的。

**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:556  
MUTATION: 維持該 node id 缺席（現況＝已發生之破壞）後執行 `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → rc=4、`ERROR: not found`、`collected 0 items`（TODO 原文：此結果＝**不通過**；須為 `1 xfailed`）。對照：`grep -n 'opposite_sides_must_fail' tests/momentum/Analysis/test_splitunify_derive.py` → 0 命中；同檔已有 `_multi_feature_tf_case`／複合鍵測試，惟無此 xfail 殼。

**來源摘要**: docs/SPLITUNIFY_TODO.md#3761a7b4a8ac

[P1] 信心度=High。會怎麼失敗：B9B 看似 705 全綠，但 TODO 自訂之第 6 條閘永遠過不了；9.2b 寫「解除 xfail」時找不到標的，混態契約失去嚴格失敗錨。  
**修法**：在 `tests/momentum/Analysis/test_splitunify_derive.py` **新增**（非改名藏舊）`test_multi_feature_tf_opposite_sides_must_fail_closed`，`@pytest.mark.xfail(strict=True, reason="Task 9.2b: 異側 fail-closed 尚未實作")`；fixture 修 9.2a 要點①（manifest 事件級去重，不得把同 `event_id` 兩列寫進 `manifest.table`）；斷言期望現行碼在不同 cutoff 混態下**尚未** raise `AlignmentViolationError`（故 xfail 等待 9.2b）。  
**可行性證據**：本家 Q1 已實跑出跨表／異標混態，故「預期仍紅／xfail」之行為前提成立；TODO:540-542 已寫死 node id 與驗收字面；`pytest.mark.xfail(strict=True)` 為專案既有模式。驗收：同上第 6 條命令須出現 `1 xfailed`（不得 `1 passed`／`no tests ran`）。

---

## GROK-R20-P2-01

**斷言**: 多 symbol（Mapping）分支之 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 無具名測試；省略該分支三 kwargs 後 summary 靜默變 0 且 scoped 回歸仍全綠。

**碼證**: `split_projection.py:768-770`（多 symbol `_build_summary` 傳入三計數）；`_build_summary` 以 `int(n_events or 0)` 吞掉缺省（:860-862）。MUTATION 實跑：刪 :767-770 三行 kwargs → `derive` Mapping 路徑 summary `{n_events:0,n_event_tf_rows:0,n_event_tf_rows_purged:0}`（真值 6/6/0 於 interleaved）；`pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → **104 passed**。單標的 `test_summary_has_n_events_and_n_event_tf_rows` 抓不到此分支。已還原，`git diff` 生產檔空白。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#bd27c2f92a20

[P2] 信心度=High。行為現況正確（本家反例值相符），缺的是鑑別力。  
**修法**：新增 `test_multi_symbol_branch_summary_event_and_tf_row_counts`（多 symbol＋多 feature TF fixture；三鍵值相等斷言）。不阻 9.2b 邏輯，建議與 P1 同批補。

---

VERDICT: blocked
BLOCKED-BY: GROK-R20-P1-01
CLOSED:

ASSUMPTIONS_VERIFIED: 不同 cutoff 三變體皆可混態（屬 9.2b）；多 symbol 三計數值正確但缺測且 omit-kwargs 全綠；生產／golden／測試 helper 之 event_keys 皆含 feature_timeframe；golden 11 鍵逐值未變；NaN 在未選側單選 raise＝R18 同行為（預期）；TODO 第 6 條 xfail node 缺席致驗收 fail
TESTS_RUN: `venv/bin/python /tmp/r20-grok-workdir/probe_r20.py` → q1.any_mixed=true、q2.match=true；NaN 四案（含 pd.NA）→ 三缺值 RAISE／clean OK；`pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → ERROR not found rc=4；omit-counts mutation → 104 passed 後已還原；scoped `test_splitunify_derive.py`＋`test_splitunify_wiring.py` → **104 passed** rc=0；`git diff` split_projection 空白
FAILURES_SEEN: 初版探針誤傳 `AlignmentReceipts(failures=…)`（已改）；非產品缺陷
SCOPE_CHANGES: none（唯讀審碼）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r20-grok.md
