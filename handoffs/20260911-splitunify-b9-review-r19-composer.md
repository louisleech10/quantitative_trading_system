# SPLITUNIFY b9 — review-r18 A1–A6 閉合再驗證 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R19`  
**family**: composer  
**findings-round**: R19  
**審查標的**: commit `7943abe3`；current block＝brief 指定之 `split_projection.py`／`test_splitunify_wiring.py`／`test_splitunify_derive.py`／`probe-multitf.py`／`docs/SPLITUNIFY_TODO.md` §C-9 Task 9.1  
**禁改碼**：review-only。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六群修補已落地 | **fact-verified** | `git show 7943abe3 --stat` 含五檔生產／測試／探針／TODO |
| brief assumed: Categorical 未使用類別會產生計數 0 偽項 | **fact-verified（不成立）** | `/tmp/r19-composer-verify.py`：`categories=["1h","4h","12h","1d"]` 且實際含 4h／12h ⇒ `discarded={'4h':1,'12h':1}`、`zero_keys={}` |
| brief assumed: `bars_multi_tf` 兩 TF 都進 `per_tf` | **fact-verified** | wiring 測試 `set(discarded)=={"4h"}` 且值為正整數；`selected_timeframe=TF`（`12h`）由呼叫端明示，不依 `timeframes` tuple 順序 |
| brief assumed: NaN fail-closed 不誤殺合法批 | **fact-verified** | 只對 `dropped` 側 `isna()`；`test_build_event_keys_rejects_nan_timeframe_in_dropped_rows` pass；Categorical／object／str 三 dtype 基線計數不變 |

---

## 必答 1 — 本家 R18 反例重跑（§B8）

### (1a)

| finding | 判定 |
|---------|------|
| `COMPOSER-R18-P2-01`（多 symbol 無具名測試） | **CLOSED** |
| `COMPOSER-R18-P2-02`（探針單值接收 TypeError） | **CLOSED** |
| `COMPOSER-R18-P3-01`（NaN timeframe → 鍵 `'nan'`） | **CLOSED**（R18 修補改為 fail-closed，與本家原 P3 建議一致） |

### (1b)

- **P2-01**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py::test_multi_symbol_branch_carries_discarded_rows_verbatim` → **1 passed** rc=0。第三 mutation（`split_projection.py:696` 改 `discarded_rows_by_feature_tf={}`）→ **1 failed**（已還原）。
- **P2-02**：`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → 四案：`A NO_RAISE … discarded={}`／`B RAISED …多列 per_tf`／`C NO_RAISE … discarded={'4h': 2}`／`D RAISED …缺 cutoff`；**rc=0**，無 TypeError。
- **P3-01**：`pytest …::test_build_event_keys_rejects_nan_timeframe_in_dropped_rows` → **1 passed**；`/tmp/r19-composer-verify.py` 插入 `timeframe=None` dropped 列 → `ValueError: …缺值（NaN／NA）…`。

---

## 必答 2 — 第二條生產路徑

### (2a)

**無。** 全 repo `derive_event_split_from_plans` 之**生產**呼叫點僅 `momentum/Analysis/event_samples/pipeline.py:750`（canonical 投影分支，與 wiring 測試同入口）。`scripts/freeze_splitunify_golden.py` 為 golden 腳本、非 `EventSamplePipeline.run` 路徑；`handoffs/*probe*` 非生產。

### (2b)

**N/A**（無第二路徑可列）。

---

## 必答 3 — Categorical dtype

### (3a)

**不會**混入值為 0 的偽項。實跑三種 dtype（`/tmp/r19-composer-verify.py`）：

| dtype | discarded | 零值鍵 |
|-------|-----------|--------|
| `Categorical`（含未出現類別 `1d`） | `{'4h': 1, '12h': 1}` | `{}` |
| `object` | `{'4h': 1, '12h': 1}` | `{}` |
| `str` | `{'4h': 1, '12h': 1}` | `{}` |

機制：`split_projection.py:294-304` 先對 `dropped` 做 `isna()` fail-closed，再 `astype(str).value_counts()`——計數前已字串化，未出現的 Categorical 類別不進 `dropped` 子集，故無幽靈鍵。

### (3b)

**N/A**（問題不成立，無需修法）。

---

## 必答 4 — 可否進 Task 9.2（B9B）

### (4a)

**可以進 `Task 9.2`＋`9.2a`（B9B，不得拆批）。** 本家 R18 三條全 CLOSED；brief 六群修補皆有對應測試且 mutation 鑑別力已重跑確認；無新 P0/P1。

### (4b)

已檢查：`7943abe3` current block 三條新測試 pass；derive＋wiring 合計 **94 passed** rc=0；wiring mutation（省略 `pipeline.py:754` 之 `discarded_rows_by_feature_tf=`）→ wiring 測試 **1 failed**；多 symbol mutation → **1 failed**；探針四案與 SPEC §A FACT-RECEIPT 字面一致（C 案新增 `discarded=` 為 Task 9.1 延伸、不衝突）；防放大斷言雖只具名檢查 `4h`，但同測試另有全 dict `== producer_discarded`，部分鍵被改仍會紅。

**誠實邊界（不阻 9.2）**：`docs/SPLITUNIFY_SPEC.D-002.md` §P `Task 9.1` 仍寫「多 symbol 時逐 symbol 相加」（L181），與已修正之 TODO §C-9 及實作「原樣傳遞」字面衝突——brief 明示 SPEC 正文本輪未動、不在審查範圍；施工權威＝TODO＋碼，非本輪 BLOCKING。

---

## §1 必查（摘要）

1. 矛盾/互斥：無（TODO 與碼一致；SPEC 舊「相加」字面見上，本輪不修）
2. 漏項/端到端：無
3. 不可測驗收：無
4. 可疑 quant 假設：無
5–11：無

---

## COMPOSER-R19-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；本家 R18 三條反例均已 CLOSED，brief 兩條 assumed（Categorical 零值偽項、雙 TF wiring）經實跑不成立。

**碼證**: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → **94 passed** rc=0；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → 四案 A/B/C/D 如 FACT-RECEIPT；`/tmp/r19-composer-verify.py` → Categorical／object／str 無 `zero_keys`、NaN fail-closed；`rg -n 'derive_event_split_from_plans' momentum/ --glob '*.py'` → 生產僅 `pipeline.py:750`。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R19-BRIEF.md#7943abe3b5a7

[P3] 信心度=High。閉合輪 sentinel；六群修補已由本家原反例重跑驗證。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R18-P2-01,COMPOSER-R18-P2-02,COMPOSER-R18-P3-01

ASSUMPTIONS_VERIFIED: 94 passed；探針四案；Categorical/object/str 三 dtype；NaN fail-closed；雙 mutation 轉紅；derive 生產單呼叫點；SPEC「相加」字面漂移已具名
TESTS_RUN: `pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 94 passed；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0；`/tmp/r19-composer-verify.py` rc=0；multi-symbol／pipeline wiring mutation 各 1 failed（已還原）
FAILURES_SEEN: none（mutation 預期失敗已還原）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r19-composer.md

STATUS: DONE
