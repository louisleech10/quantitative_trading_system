# SPLITUNIFY b9 — review-r22（r21 E1／E2 閉合再驗證）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R22`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R22-BRIEF.md`  
**findings-round**: R22  
**brief-kind**: review  
**審查標的**: commit `2f66cf77`；current block＝`test_multi_feature_tf_opposite_sides_must_fail_closed`；`docs/SPLITUNIFY_TODO.md` Task 2.2 三處＋§E `SU-RESID-2`  
**禁改碼／禁改 SPEC／禁改 TODO**（本檔只產 findings）。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: xfail 收緊後仍 `1 xfailed` | **fact-verified** | 逐字命令 → `1 xfailed`（非 passed／非 no tests ran） |
| brief fact-verified: `AlignmentViolationError` 在 `contracts.py:933` | **fact-verified** | `grep -n 'class AlignmentViolationError'` → `933`；為 `ValueError` 子類 |
| brief fact-verified: TODO Task 2.2 三處已 SUPERSEDED | **fact-verified** | `grep -n SUPERSEDED docs/SPLITUNIFY_TODO.md` 於 Task 2.2 段三處命中；原字面刪節線／「保留供追溯」 |
| brief assumed: Task 2.2 SUPERSEDED 已涵蓋該段全部與新契約互斥處；**其他舊 Task 段**是否也有 | **攻過** | 見必答 2；Task 2.1／2.3／3.1–3.3／4.1 **無**未標示之 B9B 互斥施工指示 |
| brief assumed: `SU-RESID-2` 標「已關閉」正確（下游 9.3 未做是否只關一半） | **攻過** | 見必答 3；依 D-002 範圍判 **已關閉** 正確；Task 9.3 為另列延續、非本殘留未閉半截 |

---

## 必答 1 — 本家 R21 反例／對照驗收 E1／E2

### (1a)

本家 review-r21 **無實質 finding**（僅 sentinel `GROK-R21-P3-00`）⇒ 無本家可標 `CLOSED` 之反例 ID。  
對照驗收標的（他家 `CODEX-R21-P1-01`／`P1-02` 之修補）本家仍實跑核對：

| 修補 | 本家觀測 |
|------|----------|
| E1 xfail 例外收緊 | **修補成立**（見 1b） |
| E2 Task 2.2 SUPERSEDED＋`SU-RESID-2` 已關閉 | **修補成立**（見必答 2／3） |

### (1b)

- 正常：`venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **`1 xfailed`**（rc=0）。
- `--runxfail`：同 node → **`FAILED: DID NOT RAISE <class 'momentum.core.contracts.AlignmentViolationError'>`**（非 KeyError／fixture／複合鍵／match 失敗）。失敗點 `test_splitunify_derive.py:1642`；`raises(AlignmentViolationError, match="e_x")` 已就位；import 含 `AlignmentViolationError`。

---

## 必答 2 — 其他舊 Task 段 vs B9B

### (2a)

逐段掃 `Task 2.1`／`2.3`／`3.1`–`3.3`／`4.1`（模式：`每事件恰`／`恰一列`／`12 鍵`／`13 鍵`／`selected_timeframe…必`／`單選`／欄集／`feature_timeframe`）：

| Task | 與 B9B 互斥？ | 說明 |
|------|---------------|------|
| 2.1 | **無** | 邊界算術；不涉 producer／schema |
| 2.2 | 已標 SUPERSEDED | 三處（單選／複合鍵／12→16 鍵）本輪已蓋 |
| 2.3 | **無** | golden／oracle 仍以 event_id 集合語意；擴維屬 `Task 9.5`，非「回退全量」指示 |
| 3.1 | **無（不開 finding）** | 「成員消費者，型別不變」為 **B3 當輪**歷史敘述；消費面改法權威＝`Task 9.3`，非本段施工令 |
| 3.2 | **無** | 多 symbol fail-closed |
| 3.3 | **無** | event-study-only／capability |
| 4.1 | **無** | metadata 揭露；計數拆鍵屬 `Task 9.4` |

**結論**：assumed 1 之「其他舊 Task 段仍藏互斥施工指示」**不成立**（在本輪攻擊面內）。

### (2b)

**N/A**（無須新增 SUPERSEDED 字面）。

---

## 必答 3 — `SU-RESID-2` 已關閉 vs 部分關閉

### (3a)

**應維持「已關閉」。**  
D-002 把 `SU-RESID-2` 定為本延伸落實之 **producer＋`EventSplitPlan` 表層複合鍵**（`Task 9.2`／`9.2a`：全量 keyed、`feature_timeframe` 欄、複合鍵 guard）。該批已交付（碼證：`build_event_keys` 預設 `None`＝全量；`assignments`／`purged` 含欄；guard 用複合鍵）。  
原文「連 `EventSplitPlan` 之下游一起改」在 D-002 分工下＝**表層**（兩表＋guard）屬 B9B；九處**消費面**另列 `Task 9.3`（未開工，`pattern_bridge.py:125` 仍 `assign.set_index("event_id")`）——那是**延續 Task**，不是本殘留未關的一半。SPEC §N 亦寫「本延伸落實」。

### (3b)

現行「已關閉」狀態可保留。若主委要消歧「下游」措辭（非必須、不阻），可把說明句收成：

> ~~`SU-RESID-2`~~ **已關閉（2026-09-14，批次 B9B）**｜多 TF 之 `(event_id, feature_timeframe)` 複合鍵｜—｜**已關閉範圍＝producer＋`EventSplitPlan` 表層**（`Task 9.2`／`9.2a`）。消費面九處見 **`Task 9.3`（尚未開工，不構成本殘留未閉）**。

---

## 必答 4 — SPEC 是否第四次同形（舊段 vs B9B）

### (4a)

**有過期字面，但是「已完成 Task 之施工前『現行』快照＋§N 同步指示未回寫」，不是會讓 `Task 9.2b` 實作者回退 B9B 的現行契約。**

實核（對照碼）：

1. **§P `Task 9.2`** 仍以「現行」描述四參數閘／`str(selected_timeframe)`／`validate="1:1"` merge——但 `pipeline.py:724-733` 已三者閘、`build_event_keys` 已全量＋`feature_timeframe`。屬**已完工段**之改前快照未標「已落地」。
2. **§N `SU-RESID-2`** 仍寫 TODO §E「現仍為 `needs-research`…須於…`Task 9.1` 動工前同步」——TODO 已「已關閉」、`Task 9.1` 已完工 ⇒ **同步指示本身過期**。

`Task 9.2b`／§V／register 之現行契約段與 B9B **無互斥**。

### (4b)

**不阻擋**進 `Task 9.2b`。最小後續（非本輪閉合集合）：§N 刪／改寫過期同步句；§P Task 9.2「現行」改「改前（已由 B9B 落地）」——屬文件回寫，可併下一次動 SPEC 的輪次；**本輪禁改 SPEC**。

---

## 必答 5 — 可否進 Task 9.2b（B9C）

### (5a)

**可以進 `Task 9.2b`（批次 `B9C`）。** 無本家 P0／P1；E1／E2 修補實跑成立；assumed 兩條攻擊後不構成 BLOCKING。

### (5b)

已檢查：`git show 2f66cf77`；xfail 正常／`--runxfail`→`DID NOT RAISE AlignmentViolationError`；`AlignmentViolationError`@933；Task 2.2 三處 SUPERSEDED；舊 Task 2.1–4.1 掃無未標互斥；`SU-RESID-2` 範圍 vs `Task 9.3`；SPEC §P／§N 過期字面（非阻）；scoped 四節點 → **3 passed, 1 xfailed**。

誠實邊界（不開 finding、不阻 B9C）：SPEC §P／§N 過期字面仍在（見必答 4）；`SU-RESID-2` 說明句「下游確實一起改了」易被誤讀為 9.3 已做——狀態「已關閉」仍正確。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：E1／E2 與碼／TODO 一致；舊 Task 段無未標 B9B 互斥。  
2. 漏項：無（閉合輪）。  
3. 不可測：xfail 可 `--runxfail` 證 DID NOT RAISE。  
4. 可疑 quant：異側混態仍在——屬 9.2b，錨點仍 xfail。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：本輪未改生產簽章。  
9. 測試品質：E1 收緊後失敗原因正確。  
10. Agent 可執行：可進 9.2b。  
11. 必要性／短命工：xfail 殼存活至 9.2b 解除——符合設計。

---

## GROK-R22-P3-00

**斷言**: 本輪逐項核對後無 finding；E1／E2 修補成立，本家 R21 無實質反例可 CLOSED，可進 Task 9.2b（B9C）。

**碼證**: `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed**；同命令加 `--runxfail` → **FAILED DID NOT RAISE AlignmentViolationError**（非他錯）；`contracts.py:933` 類存在；Task 2.2 三處 SUPERSEDED；舊 Task 2.1／2.3／3.1–3.3／4.1 掃無未標 B9B 互斥；`SU-RESID-2` 依 D-002 範圍維持已關閉；SPEC §P／§N 過期字面具名但不阻；scoped 四節點 → **3 passed, 1 xfailed**。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R22-BRIEF.md#fc626dbb3031

[P3] 信心度=High。閉合輪 sentinel；E1／E2 由實跑＋全文掃核對。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: E1 xfail 仍 1 xfailed 且 --runxfail=DID NOT RAISE AlignmentViolationError；E2 Task 2.2 SUPERSEDED 三處；舊 Task 2.1–4.1 無未標 B9B 互斥；SU-RESID-2 已關閉範圍正確（9.3 另列）；SPEC 過期字面非阻；可進 B9C
TESTS_RUN: `pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 xfailed；`--runxfail` → DID NOT RAISE AlignmentViolationError；scoped 四節點 → 3 passed, 1 xfailed
FAILURES_SEEN: none（--runxfail 預期失敗）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r22-grok.md

STATUS: DONE
