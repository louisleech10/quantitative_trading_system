# IC Phase1 1-align — R3 增量閉合複驗 (Composer)

**Task-id**: ic1a-align-specadv-r3  
**Agent**: Composer (R2 原提出方)  
**Date**: 2026-07-08  
**Scope**: `docs/IC_PHASE1_1A_ALIGN_SPEC.md` v3 + `docs/IC_PHASE1_1A_ALIGN_TODO.md` v3  
**Method**: 重跑 R2 兩個反例 receipt + v3 條文對照（D-4 / Task 2.4 / Task 2.3 / §ADV-RESOLUTION）+ `.index` 消費點 grep

---

## 總判

**VERDICT: APPROVE**

**原因**: R2 **STILL-OPEN** `ADV-COMPOSER-1A` 與 **NEW-ISSUE MAJOR**（index 同型化）在 v3 條文層已閉合——D-4 單點寫回 + Task 2.4 交集前雙側同型化 + Task 2.3 混型 fail-closed 直接回應 R2 最小修補建議。兩反例在「裸跨 dtype」路徑仍成立（預期，生產碼未實作）；依 v3 規定走 D-1/D-4 同型化後交集非空。D-4 grep 未發現依賴 int64 index **值本身**（非語義時間戳）的 BLOCKING caller；既有 `_coerce_timestamp_array` / `ic_reporter._extract_timestamps` DatetimeIndex 分支可承接寫回後軸。

---

## v3 增量結論（R2 未閉合項）

| ID | 判定 | 依據 |
|----|------|------|
| ADV-COMPOSER-1A | **CLOSED**（spec 層） | §ADV-RESOLUTION L26 + Task 2.4：交集前兩側 D-1/D-4 同型化；禁裸 `Index.intersection`；features 若仍 int64→上游繞過 raise；同型化後空交集才 raise。R2 TypeError 反例在現行碼仍可復現（`:1703-1704` `filtered_df.index` 裸 `.loc`），屬未實作預期；v3 修法語義正確。R2 `int64∩DatetimeIndex=0` 反例仍成立，但 v3 禁止該路徑；D-1 同型化後 `size=2`（2026-07-08 实跑）。 |
| R2 NEW-ISSUE MAJOR — index 同型化 | **CLOSED** | 新增 D-4（§A L43、Task 2.1/2.2 L76-77、TODO §0 L11）：stage0/stage2 gate PASS 後 **實體寫回** features+label 同源 DatetimeIndex；值守恆 sha256；落盤 schema 不變。消滅三路 index 分裂。 |
| §ADV-RESOLUTION typo 2.1→2.4 | **CLOSED** | grep `Task 2.1.*event_filter` → 0；L26 已標 Task 2.4。 |
| Task 2.4 修法（交集前同型化） | **CLOSED** | SPEC L79 + TODO L80-82 與 R2 建議 #1 一致；邊界⑤區分「誤殺」vs「真無交集」。 |
| Task 2.3 混型同長 | **CLOSED** | SPEC L78 + TODO L77：D-1 轉型比對；D-4 後混型=上游繞過→raise。 |
| D-4 新洞檢查 | **CLOSED**（無 BLOCKING 新洞） | 見下節。 |

---

## D-4 新洞檢查（`.index` 消費點）

| 消費點 | 檔位 | D-4 後影響 | 判定 |
|--------|------|-----------|------|
| `_base_universe_hash` / `_validate_expected_frequency` / `_time_bounds_for_rows` | `ic_filter_orchestrator.py:123-167` | 皆經 `_coerce_timestamp_array(index.to_numpy())`；int64 秒與 DatetimeIndex 語義等價 | **安全** |
| `_build_holdout_split_plan` / `validate_split_pair_integrity` | `:170-231` | split 在 D-4 **之前**（analyze `:549`），用 int64；寫回後 `:614-617` `_derive_stage_masks` 再經 coercion 重導 mask | **安全**（coerced timestamps equal 实跑 True） |
| `_derive_stage_masks` | `:425-438` | `pd.to_datetime(_coerce_timestamp_array(...))` | **安全** |
| `ic_reporter._extract_timestamps` | `ic_reporter.py:423-430` | DatetimeIndex 分支 `view("int64")`；写回后走第一分支 | **安全**（实跑 int64 5） |
| stage0 `labels_df.index.equals(features_df.index)` | `:1610-1611` | 写回前 int64×datetime `equals=False`（实跑）；Task 2.2 D-1+D-4 在 stage0 gate 覆蓋 | **spec 已覆蓋**（實作須在 gate 內處理，非條文洞） |
| `_stage3_event_filter` 現行 `.loc[idx]` | `:1703-1704` | 未實作 v3；實作後依 Task 2.4 | **實作待辦，非 spec 洞** |

**結論**: 無 caller 依賴「index 必須是 int64 秒」的數值語義；時間語義均由 `_coerce_timestamp_array` 或 DatetimeIndex 分支承接。D-4「只改 index 不改值」+ sha256 值守恆與 split 重導 mask 設計一致。

**NON-BLOCKING 備註**: v3 未明文寫「split 必須在 D-4 之後」，但現行 analyze 順序（split→preprocess→stage2 D-4→stage3 重導 mask）在 coercion 語義下可證偽安全；外部 labels 路徑實作時須在 stage0（Task 2.2）完成 gate+D-4，勿僅 stage2 early-return 繞過。

---

## R2 已 CLOSED 項 — v3 回歸檢查

v3 為增量修補，未撤回 D-1~D-3 / Task 1.2 / COMPOSER-1B~11 等 v2 裁決。抽驗：

| 類別 | 判定 | 備註 |
|------|------|------|
| ADV-COMPOSER-1B~11（v2 CLOSED） | **仍 CLOSED** | §C consumer map / §ADV-RESOLUTION 表未回退 |
| D-1~D-3 | **仍 CLOSED** | v3 追加 D-4，不衝突 |
| pytest orchestrator | **仍 2 failed / 32 passed** | 與 R2 白名單一致 |

---

## 重跑 receipt 摘要

```bash
# R2 TypeError 反例 — 現行碼（未實作 Task 2.4）
python -c "import pandas as pd; df=pd.DataFrame({'f':range(5)}, index=pd.date_range('2024-01-01',periods=5,freq='1h')); df.loc[11:49]"
# → TypeError: cannot do slice indexing on DatetimeIndex with these indexers [11] of type int

# R2 裸跨 dtype intersection（v3 禁止）
python -c "import pandas as pd; ts_int=pd.Index([1704067200,1704110400]); ts_dt=pd.to_datetime(ts_int,unit='s'); print(len(pd.DataFrame({'f':[1,2]},index=ts_int).index.intersection(ts_dt)))"
# → 0

# v3 規定路徑：D-1 同型化後 intersection
# → D-1 coerced DatetimeIndex∩DatetimeIndex size: 2

# D-4 值守恆
# → sha256 values unchanged after index write-back: True

# split/mask 跨 dtype 穩定性
# → coerced timestamps equal (int64 index vs post-D-4 DatetimeIndex): True

# stage0 裸 equals（實作前）
# → int64 vs datetime equals: False（Task 2.2 覆蓋）

pytest tests/momentum/test_ic_filter_orchestrator.py -q
# → 2 failed, 32 passed
```

---

## 凍結簽章

```
RECONCILE-STAMP APPROVED Composer 2026-07-08
```

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
- R2 TypeError receipt 現行碼仍可復現（2026-07-08 实跑）
- 裸 int64∩DatetimeIndex=0；D-1 同型化後 intersection size=2（实跑）
- D-4 写回 sha256 值守恆（实跑 True）
- split mask 重導：coerced timestamps int64 vs DatetimeIndex 相等（实跑）
- ic_reporter._extract_timestamps 承接 DatetimeIndex（实跑）
- pytest orchestrator 2 failed/32 passed（与 R2 一致）
TESTS_RUN:
- python TypeError / bare intersection / D-1 coerced intersection / D-4 sha256 / mask stability / ic_reporter / stage0 equals snippets（见上）
- pytest tests/momentum/test_ic_filter_orchestrator.py -q → 2 failed, 32 passed
FAILURES_SEEN: none（审查任务；pre-existing 2 failed 非回归）
SCOPE_CHANGES: none（只读+写本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none（未改生产 code）
產出檔: handoffs/IC1A-ALIGN-SPECADV-R3-composer.md
```

STATUS: DONE
