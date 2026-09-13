# SPLITUNIFY b9 — review-r21（r20 D1／D2 閉合再驗證）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R21`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R21-BRIEF.md`  
**findings-round**: R21  
**brief-kind**: review  
**審查標的**: commit `ef4d0664`；current block＝`tests/momentum/Analysis/test_splitunify_derive.py` 檔末兩條新測試；`docs/SPLITUNIFY_TODO.md` §C-9 Task 9.2a 驗證段  
**禁改碼／禁改 SPEC／禁改 TODO**（本檔只產 findings）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: TODO 第 6 條得 `1 xfailed` | **fact-verified** | 逐字命令 → `1 xfailed`（非 passed／非 no tests ran） |
| brief fact-verified: 多 symbol 三計數破壞驗轉紅 | **fact-verified** | 刪 Mapping 分支三 kwargs → `test_multi_symbol_branch_summary_counts_are_named` **FAILED** `assert 0 == 6`；還原後 PASSED |
| brief fact-verified: 回歸 706 passed／1 xfailed | **本家抽樣核對** | 本家跑四節點 → **3 passed, 1 xfailed**；全量 706 以 brief／synth 為權威，本家未重跑全套 |
| brief fact-verified: negative-injection 已含 `feature_timeframe` | **fact-verified** | `handoffs/20260911-probe-splitunify-negative-injection.py` `_keys()` 含該欄 |
| brief assumed: xfail 測試在 9.2b 後會自然轉 pass（match 不必再改） | **部分不成立** | 見必答 2；現行失敗＝`DID NOT RAISE`（match 未觸發）；9.2b 條文只保證訊息含 `event_id`，現況 OR match **不保證**對上未來訊息 |
| brief assumed: `xfail(strict=True)` 是此處最好表達 | **成立（在 TODO 契約下）** | 見必答 3；`skip`／`--deselect` 過不了第 6 條機械閘 |

---

## 必答 1 — 本家 R20 反例重跑（§B8）

### (1a)

| finding | 判定 |
|---------|------|
| `GROK-R20-P1-01`（xfail 錨點整段缺席） | **CLOSED** |
| `GROK-R20-P2-01`（多 symbol 三計數無具名測試） | **CLOSED** |

### (1b)

- **P1-01**：`venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **`1 xfailed`**（collected 1；非 `1 passed`、非 `no tests ran`）。node 存在於 `test_splitunify_derive.py:1616`，帶 `@pytest.mark.xfail(strict=True, …)`；manifest 用 `keys.drop_duplicates("event_id")`（事件級）。
- **P2-01**：`pytest …::test_multi_symbol_branch_summary_counts_are_named` → **1 passed**（`n_symbols==2`、三鍵逐值、`>0`）。原反例重跑：刪 Mapping 分支 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 三 kwargs → 該測 **FAILED**（`assert 0 == 6`）；`test_summary_has_all_sixteen_keys` 仍 PASSED（鑑別力落在具名測）。已還原，`git diff` 生產檔空白。

---

## 必答 2 — xfail 是否真因「異側」而紅；match 是否收緊

### (2a)

**是，真因異側靜默通過而紅，不是別的例外。** 同 fixture 直呼 `derive_event_split_from_plans`（無 xfail）：

- **NO_RAISE**；`assignments`：`e_x/1h→train`、`e_x/4h→test`；`nunique_split_label_per_event={'e_x': 2}`；`purged` 空。
- 剝掉 `@pytest.mark.xfail` 後跑同一 node → **FAILED: `DID NOT RAISE <class 'Exception'>`**（不是 KeyError／複合鍵／manifest 錯）。

亦即：fixture **確實**造出異側；現行碼靜默取兩側；測試體期望 raise → 未 raise → 紅 → 被 strict xfail 收成 `1 xfailed`。

### (2b)

**不該收緊成僅 `AlignmentViolation`。** 理由：

1. `pytest.raises(..., match=)` 對的是 **`str(exc)` 訊息**，不是類名。實測 `str(AlignmentViolationError("event_id=e_x")) == "event_id=e_x"`——字串裡**沒有** `AlignmentViolation`。
2. `Task 9.2b` 條文只保證 `AlignmentViolationError`＋訊息含 `event_id`，**不保證**含「異側／同側／AlignmentViolation」。
3. 收緊成僅 `AlignmentViolation` 會讓 9.2b 完成後更容易因訊息措辭紅（且若忘了拿掉 xfail，match 失敗會繼續顯示 XFAIL＝假「尚未完成」）。

現行寬 OR 對**此刻**足夠（失敗模式是 DID NOT RAISE，match 路徑未被行使）。**9.2b 解除 xfail 時**應改為型別斷言，例如 `pytest.raises(AlignmentViolationError, match=r"event_id")`，與 TODO 契約對齊——屬 9.2b 施工一併事項，**不阻本輪進 B9C**。

---

## 必答 3 — `xfail(strict=True)` 交接摩擦／替代寫法

### (3a)

**交接摩擦可控、且是刻意的。** 9.2b 完成當下實作者必須：(i) 實作異側 fail-closed；(ii) **拿掉**本測之 `xfail` 標記（TODO 第 6／9.2b 驗證段明文「於本 Task 解除」）。若只做 (i) 忘 (ii) → `strict=True` 下變 **XPASS → 套件紅**（正確警報）。若用 `skip`：機械驗收要的是 `1 xfailed`，會變 `1 skipped` ⇒ 第 6 條不通過；且 skip 不證明「此刻仍因異側未閉合而紅」。

### (3b)

**無更好替代可同時滿足 TODO 第 6 條。** 現行 `xfail(strict=True)` 最好：明示預期紅、禁 `--deselect`、完成時 XPASS 逼卸標記。可選強化（非必須、不阻）：解除時把 `raises(Exception, match=OR)` 改成 `raises(AlignmentViolationError, match=r"event_id")`（見 2b）。

---

## 必答 4 — 第四處未隨 Task 9.2 更新的 event_keys 建構／呼叫端

### (4a)

逐處（建構 `event_keys` 或呼叫 `build_event_keys`）：

| 處 | `feature_timeframe` | 角色 |
|----|---------------------|------|
| `split_projection.build_event_keys` | **有** | 唯一生產 producer |
| `pipeline.py` → `build_event_keys` | 經 producer | 唯一生產 caller |
| `scripts/freeze_splitunify_golden.py:_event_keys` | **有** | golden 工具 |
| `tests/.../test_splitunify_derive.py:_event_keys` | **有** | 測試 helper |
| `tests/.../test_splitunify_wiring.py` | **有**（經 builder） | wiring |
| `handoffs/.../probe-multitf.py` | 經 `build_event_keys` | 探針 |
| `handoffs/.../negative-injection.py:_keys` | **有**（本輪已補） | 探針 |
| `handoffs/_b0_mutate_backup.py` 等 backup | 舊 schema | 非生產、非本批驗收路徑 |

**無第四處**生產／golden／現行測試／本批相關探針缺欄。`api/` 無直接組裝 `EVENT_KEY_COLUMNS` 的 derive 入口。

### (4b)

**N/A（無第四處）／不阻擋。**

---

## 必答 5 — 可否進 Task 9.2b（B9C）

### (5a)

**可以進 `Task 9.2b`（批次 `B9C`）。** 無本家新 P0／P1；R20 兩條全 CLOSED。

### (5b)

已檢查：`ef4d0664` diff；TODO 第 6 條 `1 xfailed`；異側 fixture 實跑（NO_RAISE＋雙側 label）；剝 xfail → `DID NOT RAISE`；多 symbol 具名測綠＋omit-kwargs 轉紅後還原；negative-injection 含欄；全 repo builder 掃描無第四漏網；match／xfail 兩條 assumed 已答（不阻）。

**誠實邊界（不開 finding、不阻 B9C）**：

1. `_interleaved_case` 現為**單** feature TF（`n_events==n_event_tf_rows`）；omit-kwargs→0 仍被 `>0` 抓住，但抓不到「以列數冒充事件數」之置換。非本輪 D1／D2 閉合範圍。
2. 「某 symbol 子批為空」：Mapping 在 `event_symbols != plan_keys` 先 fail-closed，具名測未另造空子批——屬既有 fail-closed，非缺口。
3. xfail 之 `match` 與 9.2b 訊息契約不完全對齊——於 **9.2b 解除 xfail 時**一併改型別斷言即可。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：無（TODO 第 6 條與測試樹一致）。  
2. 漏項：R20 D1／D2 已補；無第四漏網。  
3. 不可測驗收：第 6 條可得 `1 xfailed`。  
4. 可疑 quant：異側混態仍在（屬 9.2b，已有 xfail 錨）。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：本輪未改生產簽章。  
9. 測試品質：兩反例鑑別力已重跑。  
10. Agent 可執行性：可進 9.2b。  
11. 必要性／短命工：xfail 殼存活至 9.2b 解除——符合設計。

---

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
