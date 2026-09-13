# SPLITUNIFY b9 — review-r18 A1–A6 閉合再驗證 — grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R19`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R19-BRIEF.md`  
**findings-round**: R19  
**brief-kind**: review  
**審查標的**: commit `7943abe3`；current block＝`split_projection.py`／`test_splitunify_wiring.py`／`test_splitunify_derive.py`／`probe-multitf.py`／`docs/SPLITUNIFY_TODO.md` §C-9 Task 9.1  
**禁改碼／禁改 SPEC／禁改 TODO**（本檔只產 findings）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六群修補已落地於 `7943abe3` | **fact-verified** | `git show 7943abe3 --stat` 含 `split_projection.py`／`test_splitunify_wiring.py`／`test_splitunify_derive.py`／`probe-multitf.py`／`docs/SPLITUNIFY_TODO.md` |
| brief assumed: Categorical 未使用類別會讓 `discarded` 混入計數 0 偽項 | **fact-verified（不成立）** | `/tmp/r19-grok-workdir/probe_categorical.py`：`categories=["1h","4h","12h","1d"]` 實際只含 `1h`/`4h` ⇒ `discarded={'4h':1}`；對照 raw `Categorical.value_counts` 會列出 `1h:0`/`12h:0`/`1d:0`，但碼路徑先 `astype(str)` 再計數故無零值鍵 |
| brief assumed: `bars_multi_tf` 真讓兩 feature TF 進 `per_tf`；`timeframes` 順序可能影響 `selected_timeframe` 過濾 | **fact-verified（順序不影響）** | 同 fixture 下 `ORDER=('4h','12h')` 與 `('12h','4h')` 皆得 `discarded={'4h': 4}`；`selected_timeframe=TF`（`12h`）由呼叫端明示 |
| brief assumed: NaN fail-closed 只擋壞資料、不誤殺合法批 | **fact-verified** | `isna` 只對 `dropped` 側；NaN／`pd.NA`／Categorical+NaN 皆 raise；既有合法批 94 passed |

---

## 必答 1 — 本家 R18 反例重跑（§B8）

### (1a)

| finding | 判定 |
|---------|------|
| `GROK-R18-P1-01`（pipeline 省略 `discarded_rows_by_feature_tf=` 時 derive／舊 wiring 仍綠） | **CLOSED** |
| `GROK-R18-P2-01`（TODO「逐 symbol 相加」與批次級原樣傳遞互斥） | **CLOSED** |
| `GROK-R18-P2-02`（Mapping 多 symbol 缺 discarded 具名測試） | **CLOSED** |
| `GROK-R18-P3-01`（探針仍單值承接 tuple） | **CLOSED** |
| `GROK-R18-P3-02`（`_build_summary` docstring 仍寫 12 鍵） | **CLOSED** |

### (1b)

- **P1-01**：`venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py::test_splitunify_wiring_discarded_rows_reaches_summary` → **1 passed**。重跑原反例：刪 `pipeline.py:754` 之 `discarded_rows_by_feature_tf=discarded_rows,` ⇒ 該測試 **FAILED**（`assert {}`／訊息「選 12h 卻沒記到任何被丟棄的 4h 列」）；同 mutation 下 derive 層四條 discarded／thirteen_keys **仍全綠**——鑑別力恰落在生產接線。已還原，再跑 → **1 passed**。
- **P2-01**：`sed -n '444,454p' docs/SPLITUNIFY_TODO.md` → 要點 2 已改「**原樣傳遞，不得相加**」並點名 `test_multi_symbol_branch_carries_discarded_rows_verbatim`。
- **P2-02**：`pytest …::test_multi_symbol_branch_carries_discarded_rows_verbatim` → **1 passed**；Mapping 分支改傳 `{}` ⇒ **1 failed**（`assert {} == {'4h':7,'12h':2}`）；已還原。
- **P3-01**：`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → rc=0；`A … discarded={}`／`B RAISED …多列 per_tf`／`C … discarded={'4h': 2}`／`D RAISED …缺 cutoff`。
- **P3-02**：`split_projection.py:727` docstring 現寫「**13 個必填鍵**」；`:731-732` 明寫鍵數權威＝`test_summary_has_all_thirteen_keys` exact-set；`pytest …::test_summary_has_all_thirteen_keys` → **1 passed**。

---

## 必答 2 — 第二條生產路徑

### (2a)

**無。** `build_event_keys` 之生產呼叫點僅 `momentum/Analysis/event_samples/pipeline.py:747`；`derive_event_split_from_plans` 之生產呼叫點僅同檔 `:750`（canonical 投影分支＝wiring 測試入口）。

### (2b)

**N/A**（無第二生產路徑可列）。旁注（不阻）：`scripts/freeze_splitunify_golden.py` 直接呼叫 `derive_event_split_from_plans` 且不經 `build_event_keys`／不傳 discarded——屬 golden 凍結腳本，非 `EventSamplePipeline.run` 生產鏈；`api/` 對二者呼叫點為 0。

---

## 必答 3 — Categorical dtype

### (3a)

**不會**混入值為 0 的偽項。實跑（`/tmp/r19-grok-workdir/probe_categorical.py`）：

| dtype | 觀測 |
|-------|------|
| `Categorical`＋未使用類別 `12h`/`1d` | `discarded={'4h': 1}`（無零值鍵） |
| 同上＋重複 dropped | `discarded={'4h': 2}` |
| `Categorical`＋NaN／`object`＋NaN／`string`＋`pd.NA` | 皆 `ValueError: …缺值（NaN／NA）…`（fail-closed） |
| CONTROL：raw `Categorical.value_counts` | 會列出未出現類別計數 0；`astype(str).value_counts` 後僅真實出現值 |

機制：`split_projection.py:294-305` 先對 `dropped` 做 `isna().any()` fail-closed，再 `astype(str).value_counts()`——字串化後 Categorical 未使用類別不進計數。

### (3b)

**N/A**（問題不成立，無需修法）。試過：Categorical（含未使用類別）、Categorical+NaN、object+NaN、pandas `string`+`pd.NA`。

---

## 必答 4 — 可否進 Task 9.2（B9B）

### (4a)

**可以進 `Task 9.2`＋`9.2a`（批次 `B9B`，不得拆批）。** 本家 R18 五條全 CLOSED；無新 P0/P1。

### (4b)

已檢查：`7943abe3` current block；本家五條反例重跑（含 pipeline omit／Mapping `{}` 兩 mutation 轉紅後還原）；derive＋wiring **94 passed**；探針四案；Categorical／TF 順序兩 assumed；全 repo 生產呼叫點單一路徑；防放大：雖具名斷言只查 `4h==7`，同測試另有全 dict `== producer_discarded`——只放大 `12h` 仍會紅（探針 `partial_amp` 證實）。

**誠實邊界（不阻 9.2，且本輪不開 finding）**：`docs/SPLITUNIFY_SPEC.D-002.md` §P `Task 9.1` L181 仍寫「多 symbol 時逐 symbol 相加」，與已修正之 TODO／實作「原樣傳遞」衝突。brief 明示 SPEC 正文本輪**不在審查範圍**且未動；施工權威＝TODO＋碼＋具名測試。日後若重簽 SPEC body，應順手同步該句——**非**本輪 BLOCKING，亦非重開 `Task 9.2`–`9.5` 設計。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：TODO／碼一致；SPEC 舊「相加」字面見必答 4b（範圍外、不阻）。  
2. 漏項/端到端：無（生產接線＋Mapping 均有具名測）。  
3. 不可測驗收：無。  
4. 可疑 quant 假設：無（本層只記帳）。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：探針已 unpack；生產 caller 單一。  
9. 測試品質：wiring／Mapping mutation 鑑別力已重跑。  
10. Agent 可執行性：TODO 已改「原樣傳遞」。  
11. 必要性／短命工：無。

---

## GROK-R19-P3-00

**斷言**: 本輪逐項核對後無 finding；本家 R18 五條反例均 CLOSED，brief 兩條 assumed（Categorical 零值偽項、雙 TF／順序影響 wiring）經實跑不成立，可進 B9B。

**碼證**: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → **94 passed** rc=0；省略 `pipeline.py:754` discarded kwarg ⇒ wiring **1 failed**（已還原）；Mapping 改傳 `{}` ⇒ multi-symbol **1 failed**（已還原）；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → A/B/C/D 四案且 C 之 `discarded={'4h': 2}`；`/tmp/r19-grok-workdir/probe_categorical.py` → Categorical 無零值鍵、NaN fail-closed；TF 順序兩向皆 `discarded={'4h': 4}`；`grep -rn 'build_event_keys\|derive_event_split_from_plans' momentum api --include='*.py'` → 生產僅 `pipeline.py:747`／`:750`。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R19-BRIEF.md#7943abe3b5a7

[P3] 信心度=High。閉合輪 sentinel；六群修補由本家原反例重跑驗證。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R18-P1-01,GROK-R18-P2-01,GROK-R18-P2-02,GROK-R18-P3-01,GROK-R18-P3-02

ASSUMPTIONS_VERIFIED: 94 passed；P1-01／P2-02 mutation 轉紅後還原；探針四案；Categorical／object／string+NA；TF 順序兩向；生產呼叫點單一；SPEC「相加」漂移具名但不阻
TESTS_RUN: `pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 94 passed；`pytest …::test_splitunify_wiring_discarded_rows_reaches_summary` 於 pipeline mutation 下 1 failed／還原後 1 passed；`pytest …::test_multi_symbol_branch_carries_discarded_rows_verbatim` 於 Mapping `{}` mutation 下 1 failed／還原後 1 passed；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0；categorical／TF-order 探針 rc=0
FAILURES_SEEN: none（mutation 預期失敗已還原；`git status` 生產檔乾淨）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r19-grok.md

STATUS: DONE
