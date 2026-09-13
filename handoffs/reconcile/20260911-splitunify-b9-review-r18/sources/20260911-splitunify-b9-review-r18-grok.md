# SPLITUNIFY b9 — review-r18（Task 9.1 實作審碼）— grok

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R18`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R18-BRIEF.md`  
**findings-round**: R18  
**brief-kind**: review  
**審查標的**: commit `0bd91069` 之 `split_projection.py`／`pipeline.py`／`test_splitunify_derive.py` ＋ current block（`build_event_keys`、`_derive_single_symbol`、Mapping 多 symbol 分支、`_build_summary`、`pipeline` 投影 caller、`docs/SPLITUNIFY_TODO.md` §C-9 Task 9.1）  
**禁改碼／禁改 SPEC／禁改 TODO**（本檔只產 findings）。

---

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: `build_event_keys` 全 repo 生產呼叫點僅 `pipeline.py:747`（unpack 兩值並傳 `discarded_rows_by_feature_tf`）；測試呼叫皆在 `test_splitunify_derive.py`；`handoffs/20260911-splitunify-b9-probe-multitf.py:47` 仍單值承接。

fact-verified: Mapping 多 symbol 分支之最終 `_build_summary` **有**帶入 `discarded_rows_by_feature_tf`（`split_projection.py:688`）；迴圈內 `_derive_single_symbol` 不傳該參數（其 `summary` 被丟棄，只取 assignments／purged／test_n）——與「批次級原樣傳遞」一致。

fact-verified: `M-SU-D2-01`（刪 `_build_summary` 之 discarded 寫入）⇒ **3 failed**（`thirteen_keys`／`summary_carries_...`／`independently_revertible`）；`M-SU-D2-02`（`_derive_single_symbol` 改傳 `{}`）⇒ **1 failed**（`summary_carries_...` 值相等）。兩者皆已還原，`git diff` 兩生產檔空白。

fact-verified: 第三種破壞——刪 `pipeline.py:754` 之 `discarded_rows_by_feature_tf=discarded_rows` ⇒ `test_splitunify_derive.py -k 'discarded or thirteen_keys'` **全綠**；`test_splitunify_wiring.py` **9 passed**（單 TF fixture 下 `{}` 與省略 kwarg→`None`→`{}` 不可分）。

assumed（brief）：「逐 symbol 相加」vs 批次級原樣 → **本輪裁定實作對**（見必答 1）；TODO 字面應改，否則 Agent 會照字面做重複計數。

assumed（brief）：`value_counts` 對 Categorical／NaN → **Categorical 已被 `.astype(str)` 擋掉零計數偽項**；NaN／None 經 `astype(str)` 會變成鍵 `"nan"`／`"None"`，但生產 `alignment.py` 之 `timeframe` 來自 `config.timeframes` 字面，非 Categorical／NaN 路徑（見必答 3）。

---

## 必答

### (1a)(1b) 逐 symbol 相加 vs 批次級原樣傳遞

**(1a) 裁定：實作對（批次級原樣傳遞）。**  
呼叫圖：`pipeline.py:747` 對整批 `receipts` **只呼一次** `build_event_keys`；Mapping 分支只切 `event_keys`／manifest，**不**重呼 producer。不存在「逐 symbol 的 discarded 分量」可相加；若對同一份 `discarded` 按 symbol 數相加會**重複計數**。碼中 `split_projection.py:685-688` 已具名此理由。

**(1b)** TODO `Task 9.1` 實作要點 2 末句應改為（建議字面）：  
「多 symbol 分派器對 producer 之 `discarded` **原樣傳遞**（批次級；**不得**逐 symbol 相加——producer 只算一次，相加會重複計數）。」  
（本輪禁改 TODO，只報 finding `GROK-R18-P2-01`。）

### (2a)(2b) 多 symbol Mapping 分支是否帶到 summary

**(2a) 有帶到。** 反例實跑（`n_symbols=2`，手注 `{"4h":7,"12h":2}` 與 producer→Mapping e2e）：  
`plan.summary["discarded_rows_by_feature_tf"]` **值相等**於傳入／producer；值型別為 Python `int`。

**(2b) 應補具名測試**（行為已正確，但現無 Mapping＋discarded 具名用例；見 `GROK-R18-P2-02`）。最小修法：在 `test_splitunify_derive.py` 用既有 `_interleaved_case()` 加一條 `discarded_rows_by_feature_tf=...` 之值相等斷言。

### (3a)(3b) `value_counts` × Categorical／NaN

**(3a)**  
- **Categorical（含未出現類別）**：現行碼先 `.astype(str)` 再 `value_counts` ⇒ **不會**出現計數 0 的偽項（對照：對 Categorical 直接 `value_counts` 會列出 `12h:0`／`1d:0`）。  
- **NaN／None**：`astype(str)` 後鍵為 `"nan"`／`"None"` ⇒ **會**產生偽項（若該 dtype 真的進到 `per_tf`）。

**(3b)** 本 Task **不強制加 dtype 閘**。理由：生產 `alignment.py` 寫入之 `timeframe` 為 `config.timeframes`／trigger TF **字面 str**，非 Categorical、亦非 NaN。`int(n)` 轉換覆蓋 producer 與 `_build_summary` 兩路徑。若未來允許外部手組 receipts，再於 `build_event_keys` 入口對 `timeframe` 做 `isna` fail-closed 即可（非 9.1 閉合前置）。

### (4a)(4b) 未改之 `build_event_keys` 呼叫端

**(4a)** 生產＋測試呼叫端已改；殘留：`handoffs/20260911-splitunify-b9-probe-multitf.py:47` 仍 `out = build_event_keys(...)` 並當 DataFrame 用（tuple 下 `len(out)==2`，會誤報）。

**(4b)** **不阻擋**進 `Task 9.2`（探針非生產路徑；FACT-RECEIPT 可重跑性降級，見 `GROK-R18-P3-01`）。最小修法：改 unpack 並印 `discarded`。

### (5a)(5b) mutation 鑑別力＋第三種破壞

**(5a) 兩條皆有鑑別力（本輪重跑）。**  
- `M-SU-D2-01` → 3 failed（與 brief 一致）。  
- `M-SU-D2-02` → 1 failed，且由**值相等**抓到（只驗鍵存在會漏）。

**(5b) 有第三種：pipeline 邊界丟掉 `discarded_rows_by_feature_tf=`。**  
刪 `pipeline.py:754` 該行後：Task 9.1 四條具名＋`thirteen_keys` 全綠；wiring 9 條全綠。單 TF 下 summary 恆為 `{}`，與「沒傳」不可分——與當年 H6（`tier_min_test_events` 沒傳被靜默換成 1）同型。見 `GROK-R18-P1-01`。

### (6a)(6b) 可否進 Task 9.2

**(6a) 不可以（有 BLOCKING）。**  
**(6b) 最小閉合集合：`GROK-R18-P1-01` 一條**——補一條接線／spy 測試，使「pipeline 省略 discarded 傳遞」必紅。P2／P3 可同批或隨 doc sync，不構成另開閉合集合。檢查過：單選行為未動、`selected_timeframe: str` 仍必填、692 路徑之具名測試與兩 mutation 自證成立、多 symbol 傳遞行為正確但缺測、TODO「相加」字面誤導。

---

## GROK-R18-P1-01

**斷言**: 生產接線 `pipeline.py` 若省略 `discarded_rows_by_feature_tf=discarded_rows`，Task 9.1 全部具名測試與既有 wiring 測試仍全綠——記帳在唯一生產呼叫點可靜默失效。

**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:754  
MUTATION: 刪除 `discarded_rows_by_feature_tf=discarded_rows,` 一行後執行 `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'discarded or thirteen_keys'` → 全綠；`venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py` → 9 passed。對照：同檔 `tier_min_test_events` 已有 `test_splitunify_wiring_tier_min_test_events_reaches_projection`（:146）防 H6 回歸，discarded 無對等探針。單 TF fixture 下 `discarded=={}`，summary 鍵存在／等於 `{}` **無法**區分「有傳空 dict」與「沒傳（None→{}）」。

**來源摘要**: momentum/Analysis/event_samples/pipeline.py#db6753fd6161

[P1] 信心度=High。會怎麼失敗：實作正確時看似完工；之後任一重構若漏傳 kwarg，summary 永遠 `{}`，靜默丟棄再次對呼叫端不可見，且 CI 不紅。  
**修法**：在 `tests/momentum/event_samples/test_splitunify_wiring.py` 新增一條（對齊既有執行期探針風格）——`monkeypatch` `build_event_keys` 令其回傳具名非空 `discarded`（例如 `{"4h": 3}`），跑投影路徑 `EventSamplePipeline().run(...)`，斷言 `res.split_plan.summary["discarded_rows_by_feature_tf"] == {"4h": 3}`。  
**可行性證據**：同檔已用 runtime probe（非原始碼形狀）抓 H6；`build_event_keys` 已從 `pipeline` 模組 import，monkeypatch 點與 `spy_split` 同型；不需多 TF bars 即可令「漏傳」轉紅。

---

## GROK-R18-P2-01

**斷言**: TODO `Task 9.1` 實作要點 2 寫「多 symbol 分派器逐 symbol 相加」，與現行呼叫圖／實作（批次級原樣傳遞）互斥；照字面實作會重複計數。

**碼證**: `docs/SPLITUNIFY_TODO.md` Task 9.1 要點 2 原文「逐 symbol **相加**」；對照 `split_projection.py:685-688` 具名「不得再相加」＋ `pipeline.py:747` 單一呼叫點。doc-literal-only（行為以實作為準且正確）。RECHECK：`grep -n "build_event_keys" momentum/Analysis/event_samples/pipeline.py` 僅 import＋一呼叫。

**來源摘要**: docs/SPLITUNIFY_TODO.md#a3afd566fc1d

[P2] 信心度=High。修法：將要點 2 末句改為「原樣傳遞（批次級；不得逐 symbol 相加）」。不擋產品行為，但會誤導下一輪 Agent。

---

## GROK-R18-P2-02

**斷言**: `derive_event_split_from_plans` 之 Mapping（多 symbol）分支目前無具名測試覆蓋 `discarded_rows_by_feature_tf` 傳遞，回歸只能靠讀碼。

**碼證**: `test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer` 只走單標的 wrapper；`test_per_symbol_*` 皆未傳 discarded。本輪反例實跑確認 Mapping 路徑**行為正確**（手注與 producer e2e 值相等）。CODE 落點：`split_projection.py:688`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[P2] 信心度=High。修法：`_interleaved_case()` + `discarded_rows_by_feature_tf={"4h":7}` 值相等斷言一條即可。非 BLOCKING（行為已證）。

---

## GROK-R18-P3-01

**斷言**: `handoffs/20260911-splitunify-b9-probe-multitf.py` 仍把 `build_event_keys` 回傳值當單一 DataFrame，簽章改 tuple 後探針語意損壞。

**碼證**: `handoffs/20260911-splitunify-b9-probe-multitf.py:47` `out = build_event_keys(...)`；`len(out)` 對 tuple 為 2。doc-literal／探針維護，非生產 caller。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[P3] 信心度=High。修法：unpack `(keyed, discarded)` 並印 discarded。不阻擋 9.2。

---

## GROK-R18-P3-02

**斷言**: `_build_summary` docstring 仍寫「12 個必填鍵」，與實作 13 鍵／測試 `thirteen_keys` 漂移。

**碼證**: `split_projection.py:719` docstring「12 個必填鍵」；同函式 :762 已寫入第 13 鍵。doc-literal-only。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[P3] 信心度=High。修法：docstring 改「13 個必填鍵」。

---

## §1 必查（11 類摘要）

1. 矛盾：TODO「相加」vs 實作「原樣」→ `GROK-R18-P2-01`；其餘無。  
2. 漏項：生產接線缺 discarded 探針 → `GROK-R18-P1-01`；Mapping 缺測 → `GROK-R18-P2-02`。  
3. 不可測：既有四條具名＋兩 mutation 可測；缺的是 pipeline 邊界。  
4. quant 假設：無（本 Task 只記帳）。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：tuple 簽章生產 caller 已改；探針未改 → P3。  
9. 測試品質：`GROK-R18-P1-01`／`P2-02`。  
10. Agent 可執行性：TODO 相加字面會誤導 → P2。  
11. 必要性／短命工：無（9.1 記帳層存活至全票完工；與 9.2 不衝突）。

---

VERDICT: blocked
BLOCKED-BY: GROK-R18-P1-01
CLOSED:

ASSUMPTIONS_VERIFIED: 批次級原樣傳遞正確且相加會重複計數；Mapping 分支實跑帶到 discarded；Categorical+astype(str) 無零計數偽項；NaN→"nan" 僅手組路徑；M-SU-D2-01/02 重跑 3 failed／1 failed；pipeline 省略傳遞後 derive+wiring 全綠；build_event_keys 生產 caller 僅 pipeline 一處
TESTS_RUN: `PYTHONPATH=. venv/bin/python handoffs/20260911-splitunify-b9-review-r18-grok-probe.py`（Q2/Q3/Q5/Q5b）→ Q2 PASS；M1 rc=1（3 failed）；M2 rc=1（1 failed）；Q5b derive_tests_rc=0；另 `pytest tests/momentum/event_samples/test_splitunify_wiring.py` 於 pipeline mutation 下 9 passed 後已還原；`git diff` 兩生產檔空白
FAILURES_SEEN: 探針初版缺 `decision_at_ms`／缺 PYTHONPATH（已修探針後重跑）；非產品缺陷
SCOPE_CHANGES: none（唯讀審碼；臨時探針檔將刪除）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r18-grok.md

STATUS: DONE
