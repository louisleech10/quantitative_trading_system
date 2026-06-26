# 1a cut1 — default-ON 語義 委員會回覆（Composer 2.5 獨立）

**角色**：執行端 code review / correctness·洩漏評估（非實作派工）  
**依據**：`handoffs/20260626-1a-cut1-DEFAULTON-COMMITTEE.md` + 實碼閱讀（2026-06-27）

---

## 1. 三選一 + correctness / 洩漏理由

**裁決：改良版 (A) —「分因回退」，非一刀切 Skipped，亦非 (C) 只改測試**

| 不可行原因 | 建議行為 | 理由 |
|---|---|---|
| **`min_test_rows` 不足**（含 rolling warmup 二段 skip） | **回退 full-sample + `applied:false`** | OOS 在數學上無法成立；legacy full-sample 與 flag-off 同語義，**不新增** train/test 洩漏，只是無法宣稱 OOS。透明標記即可。 |
| **`TimestampDiscontinuityError`（不規律 ts / gap）** | **維持 fail-closed（raise 或整體 skip）— 不回退 full-sample** | 1-contract C-3 鐵律：rows-purge 遇 gap 必 raise。回退 full-sample 仍會在**未通過時間連續性契約**的資料上產 IC，等於繞過紅線、產出**語義錯誤**數字（非單純「沒 OOS」）。 |
| **合成/plumbing 測試** | 可 `config_override.ic_train_test_split=false`（輔助） | 屬 (C) 範圍，**不能**當主策略；治標。 |

**不選純 (B)**：對 `insufficient_data` 整體 Skipped 在 correctness 上過嚴——小樣本本來就無法 OOS，skip 整條分析不比標記清楚的 legacy IC 更安全，只更難用。  
**不選純 (C)**：default-ON 對真實小 run / legacy caller 仍壞，與使用者「驗證 PASS 後預設開啟」衝突。

**核心 correctness 論點**：
- default-ON 的洩漏保證應表述為：**「當 `applied:true` 時，train-only fit + OOS 報告口徑成立」**；不可行時不應假裝 OOS。
- `insufficient_data` 回退 **不引入** 新的 train→test 資訊流（因為根本沒切分）；風險在**消費端誤讀**，靠 schema 擋。
- `irregular_timestamps` 若回退 full-sample，會**削弱** Phase 1 契約已凍結的 fail-closed，且 IC 在錯誤時間語義上仍不可信——比「沒 OOS」更糟。

---

## 2. (A) 回退標記設計 + 防誤用

### 建議 metadata（與現有 flag-on 成功路徑並存）

**OOS 成功（現狀，微調）**：
```json
"ic_train_test_split": {
  "requested": true,
  "applied": true,
  "scope": "train_test_holdout",
  "oos_guarantees": true,
  "effective_horizon": 5,
  "purge_gap": 5,
  "train_rows": 16281,
  "test_rows": 4071,
  "index_kind": "positional"
}
```

**回退 full-sample（新增）**：
```json
"ic_train_test_split": {
  "requested": true,
  "applied": false,
  "scope": "full_sample_legacy",
  "oos_guarantees": false,
  "reason": "insufficient_data",
  "reason_detail": "train/test rows below min_test_rows",
  "details": {
    "train_rows": 96,
    "test_rows": 19,
    "min_test_rows": 131
  }
}
```

`reason` 枚舉建議：`insufficient_data` | `rolling_warmup_insufficient`（stage4 二段 gate）| `irregular_timestamps`（若改為 skip 而非 raise，仍 **不可** `applied:false` 回退）。

### 防「full-sample 被誤當 OOS」

1. **單一判斷鍵**：下游（threshold、summary、deep analysis、前端 badge）只看 `applied === true`；**禁止**用 `requested` / `enabled` 推斷 OOS。
2. **報告頂層**：`metadata.evaluation_scope: "oos" | "full_sample_legacy"`（或沿用 Phase 1 `eval_status`，full-sample 回退 → `UNKNOWN_LEGACY` / 新值 `FULL_SAMPLE_FALLBACK`）。
3. **契約測試**：G-NEW golden 僅凍 `applied:true` 路徑；新增 `test_fallback_insufficient_data_marks_applied_false`（小 n + default ON → 有 `summary_table` 且 `applied:false`）。
4. **API**：task/result 對 `applied:false` 回傳明確 `evaluation_scope`；禁止 v2 artifact 標「OOS validated」。
5. **文件**：SPEC §E 寫死——`applied:false` 的 IC **不得**進入 feature selection / FDR / 簽核 checklist。

---

## 3. API timeout 是否 task-status propagation bug？

**結論：有 propagation gap，但委員會描述的「timeout」與程式路徑需拆開看。**

### 碼證

**引擎 early skip**（`ic_filter_orchestrator.py:323-330`）：`SkippedResult` → 回 `{"status":"skipped", ...}`，**不 raise**。

**API service**（`ic_analysis_service.py:231-236`）：`analyze()` 正常返回後 **一律** `task_info["status"] = "completed"`，**未**檢查 `report.get("status") == "skipped"`。

對照：`model_enhancement_service.py:196-199` 對 `SkippedResult` 明確設 `status = "skipped"`。

**`TimestampDiscontinuityError`**：在 `_build_holdout_split_plan` → `validate_split_pair_integrity` 內 raise（`test_analyze_split_gap_blocked` 可證），`analyze()` 未 catch → `_run_analysis` except → `status = "failed"`（`:248-257`）。應 **fast-fail**，非 hang。

### 對 API 測試 fixture 的推論（`test_ic_analysis_api.py`）

- `n_samples=120`，`min_test_rows=131`（`ic_config_schema.py:338`）→ **early skip**，應在秒內結束。
- `_wait_for_task` 只等 `completed`/`failed`（`:58-61`）→ early skip 會變 **`completed`**，**不應 15s timeout**。
- 更可能失敗模式：**fixture 通過 wait，子測試 assert `metadata`/`summary_table` 缺失**（skip payload 無完整 report）——委員會或把此歸為「壞掉」，部分 case 才可能真 timeout（例如 split 成立後 stage4+ 重計算、或 kline 路徑阻塞）。

### 建議修復（值得做，獨立小任務）

1. `_run_analysis`：若 `isinstance(report, dict) and report.get("status") == "skipped"` → `task_info["status"] = "skipped"`，`error`/`skip_reason` 填 `reason`。
2. `ICTaskStatusResponse` 允許 `status in {running, completed, failed, skipped}`（與 model enhancement 對齊）。
3. 測試：mock analyzer 回 skip dict → assert task status `skipped` 且 <1s。

**不建議**把 engine skip 當 `completed` 留給消費端猜——這是確定的 UX/契約 bug，即使不是 timeout 根因。

---

## 4. 對 leakage 契約鐵律的影響評估

| 鐵律 | default-ON | 純 (B) Skipped | 改良 (A) |
|---|---|---|---|
| **OOS 可行時 train-only fit + test 報告** | ✅ 維持（已簽核路徑） | ✅ | ✅ |
| **C-3 gap → fail-closed** | ✅ 若 irregular 仍 raise | ✅ | ✅ 僅當 irregular **不回退** |
| **purge ≥ horizon** | ✅ `_build_holdout_split_plan` | N/A（無分析） | ✅ 回退路徑不走 split |
| **消費端不混淆 OOS / legacy** | ⚠️ 需 `applied` gate | ✅ 無數字 | ⚠️ 靠 schema + 測試 |
| **G-OLD byte 守恆（flag off）** | ✅ 不受影響 | ✅ | ✅ |
| **G-NEW（OOS applied:true）** | ✅ | N/A | ✅ 與回退分離 |

**總評**：
- default-ON **本身不削弱**鐵律；削弱點在「不可行時怎麼辦」。
- **改良 (A)**：只對 `insufficient_data` 回退，**不動** C-3；鐵律在「`applied:true` 子集」上完整成立。
- **純 (B)**：最安全但過度；對小樣本拒絕服務不增加洩漏防護（本來就無 OOS）。
- **純 (C)**：不觸鐵律，不解產品問題。
- **錯誤版 (A)**（irregular 也回退 full-sample）：**會違反** C-3 精神，**拒絕**。

### 實作落點提示（供後續派工，本檔不實作）

- `analyze()`：`ic_train_test_split` 為 True 時，`_build_holdout_split_plan` 回 `SkippedResult` 且 `error_type == INSUFFICIENT_DATA` → 清 `split_context`，設 `metadata.ic_train_test_split.applied=false`，**走 flag-off 管線**。
- `TimestampDiscontinuityError`：**不 catch 回退**（或 catch 後 re-raise / 回整體 skip，無 IC 數字）。
- stage4 `rolling_warmup_insufficient`：與 early `min_test_rows` 同級，可回退或 skip；若回退，reason 分開枚舉。

---

## 碼證索引

| 議題 | 位置 |
|---|---|
| default ON + min_test_rows=131 | `ic_config_schema.py:335-338` |
| early skip 整條 analyze | `ic_filter_orchestrator.py:323-330` |
| stage4 二段 skip | `ic_filter_orchestrator.py:1507-1517` |
| gap fail-closed | `test_ic_1a_cut1_split.py:186-197` |
| API 一律 completed | `ic_analysis_service.py:231-236` |
| API fixture n=120, ts=arange(1) | `test_ic_analysis_api.py:74-78` |

---

```
ASSUMPTIONS_VERIFIED:
- ic_train_test_split 預設 True（ic_config_schema.py:335）
- min_test_rows 預設 131；API fixture n=120 → early INSUFFICIENT_DATA skip（ic_filter_orchestrator.py:161-172）
- API service 不區分 engine skipped vs completed（ic_analysis_service.py:231-236）
- TimestampDiscontinuityError 在 _build_holdout_split_plan 內 raise，analyze 未 catch（test_analyze_split_gap_blocked）

TESTS_RUN: none（諮詢任務，唯讀碼審）

FAILURES_SEEN: none

SCOPE_CHANGES: none

NUMERIC_OR_SCHEMA_IMPACT: 建議新增 metadata.applied/reason/scope（諮詢層）；未改碼
```

STATUS: DONE
