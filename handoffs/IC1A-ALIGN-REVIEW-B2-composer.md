# IC1A-ALIGN-REVIEW-B2 — Composer 總 Code Review

**task-id**: `ic1a-align-review-b2`  
**agent**: Composer | **date**: 2026-07-09  
**scope**: 只讀審查 + 本檔；基準 `docs/IC_PHASE1_1A_ALIGN_SPEC.md` v3 Frozen Task 2.1–2.4 + MIXED 裁定（`handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-{codex,composer}.md`）  
**diff 範圍**: `git diff momentum/ tests/`（4 檔）+ golden baseline 兩檔（`baseline_old_*` / `baseline_new_*`，已入庫）

---

## Executive Summary

B2 核心接線（stage0/2 D-4 寫回、stage2 kline 軸正規化、slice 消滅長度巧合、event_filter 同型交集）**實作品質達 SPEC 意圖**；dtype 修復後 **turnover/grouped 數值 payload 與重凍 `baseline_old` 完全相等**；golden 深相等測試全綠。  
**未過 B2 Gate 項**：TODO/SPEC 要求的 **M5 雙腿 mutation 缺失**、**Task 2.2 M4 stage0 整合測缺失**；stage0 Tier-2 `close` 仍強制 float64 而 stage2 已保留 float32，邊界未統一。  
**ISO timestamp 全棧**：D-4 後 turnover `time_series.timestamps` 為 ISO 字串；前端型別與元件已相容，不斷線。

**Verdict: REJECT**（Gate 缺口可補；核心修正方向正確，重凍 baseline 合理）

---

## 1) RCA 探針重跑 — dtype 修後 turnover/grouped exact_equal

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-RCA-01** | ✅ PASS | `source venv/bin/activate && python` 診斷腳本 replay cut1 golden（`split_on=False`, 50 feat）；輸出：`TURNOVER_NUMERIC_EXACT_EQUAL=True`，`GROUPED_IC_EXACT_EQUAL=True`，`GROUPED_FIRST_DIFF=None`。stage2 close 已改 `raw_data["close"].to_numpy(copy=False)`（保留 float32）。 | 無需再修 dtype；維持 stage2 不強制 float64。 |
| **B2-RCA-02** | ✅ PASS | `pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py::test_flag_off_deep_equal_baseline -q` → **PASSED**（33.9s）；全報告深相等（僅豁免 `generated_at`）。 | 重凍 `baseline_old` 與現行碼一致，裁定 **REBASELINE 合理**（推翻 Codex FIX-CODE-only）。 |

**MIXED 裁定結論**：實作採 Composer REBASELINE + stage2 dtype 保留；Codex 指出的 float64 微擾已在 working tree 修復，探針證實 turnover/grouped 與舊 baseline 數值 payload 完全相等。

---

## 2) 重凍 baseline 抽驗 — rolling_ic / summary 七特徵

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-BASE-01** | NON-BLOCKING | `baseline_old` `summary_table`：`ic_mean=None` 計數 **0/50**（已重凍，非 RCA 撰寫時的全 None 狀態）。`rolling_ic_series`：**50/50** 特徵非空窗。 | 無；RCA 描述的是修復前狀態，重凍後為預期。 |
| **B2-BASE-02** | ✅ PASS | `stage5_thresholds.removed_features`：`ic_mean` 43 筆、`icir` **7 筆**，與 RCA 表一致。七特徵 actual 值與 RCA 逐項吻合（例 `None_12h_tail_risk_max_drawdown_21_100_Cross` ic_mean=0.059927… icir=0.2180…；最低 ic_mean=0.04454，最高 icir=0.4075，均過 ic_mean≥0.02、未過 icir<0.5）。 | 無；B 類翻閘為修復後首次有效 icir 分類，合理。 |
| **B2-BASE-03** | ✅ PASS | `pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py::test_flag_on_matches_new_golden -q` → **PASSED**；`metadata.scope=="test"` OOS 路徑與 `baseline_new` 一致。 | 無。 |

---

## 3) Task 2.1–2.4 SPEC/TODO 忠實度

### Task 2.1 — Stage2 kline label + D-4 寫回

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-2.1-01** | ✅ PASS | `_stage2_label_generation`（`ic_filter_orchestrator.py:1821-1884`）：`_normalize_frame_time_index`、reindex、`validate_alignment`、`_assign_datetime_index_preserving_values` 值守恆寫回。 | — |
| **B2-2.1-02** | ✅ PASS | `test_alignment_gate_stage2_normalizes_kline_axis_and_preserves_values`：`features_df.to_numpy().tobytes()` 寫回前後相等；index 為 `DatetimeIndex`。 | — |
| **B2-2.1-03** | NON-BLOCKING | `analyze()` 已傳 `features_df` 入 stage2（diff L746-748）；horizon fallback warning 仍出現（golden 無 labels_path）— 符合 Task 1.2 行為，非 B2 回歸。 | 可選：metadata 標 `horizon_source`。 |

### Task 2.2 — Stage0 外部 labels gate + D-4 寫回

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-2.2-01** | ✅ PASS | `_stage0_ingestion`（`:1754-1791`）：D-1 正規化、reindex、resolver horizon、`validate_alignment`、D-4 寫回；`analyze` 傳入 `kline_reader`（`:681-682`）。 | — |
| **B2-2.2-02** | ✅ PASS | `test_alignment_gate_stage0_external_labels_reject_rangeindex` → `AlignmentViolationError` match `RangeIndex`。 | — |
| **B2-2.2-03** | **BLOCKING** | TODO §2.2 驗證要求 **M4 轉紅 receipt**（1h labels + 12h features → cadence raise）。kernel 有 `test_alignment_contract.py::test_validate_alignment_cadence_mismatch`；**stage0 整合路徑無 M4 測試**。 | 新增 `test_alignment_gate_stage0_wrong_tf_raises`（12h features + 1h labels index，期望 `AlignmentViolationError`）。 |
| **B2-2.2-04** | NON-BLOCKING | `test_stage0_ingestion_uses_meta_and_reindexes_labels` 未傳 `kline_reader` → Tier-2 未覆蓋；僅測 reindex + nan 剔除。 | 補 stage0 + kline_reader Tier-2 pass 測試（可併 B3 前）。 |

### Task 2.3 — `_slice_by_mask` / `_slice_raw_data_by_mask`

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-2.3-01** | ✅ PASS | 兩函式同規則（`:564-621`）：同長須 `_normalize_ic_time_index` 後 `.equals` 才 iloc；否則 reindex。 | — |
| **B2-2.3-02** | ✅ PASS | caller 全列（`grep`）：`:2056` stage4 IC、`:2090` rolling、`:2125` raw_data、`:2177` stats — **4/4 已接**。 | — |
| **B2-2.3-03** | ✅ PASS | **M2** 可證偽：`test_slice_alignment_same_length_misaligned_label_raises`、`test_slice_alignment_raw_data_misaligned_same_length_raises` → PASSED。 | — |

### Task 2.4 — `_stage3_event_filter` 同型交集

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-2.4-01** | ✅ PASS | `:1901-1935`：feature/label 先 D-1 正規化；kline `filter_base` 同型化；`feature_index.intersection(filtered_index)`；空交集 → `AlignmentViolationError`。 | — |
| **B2-2.4-02** | ✅ PASS | fixture 遷移：`test_stage3_event_filter_uses_raw_data` 改 `DatetimeIndex` features + int64 秒 kline；斷言由 `list(range(11,50))` 升級為 `index[11:].equals` — **未弱化**。 | — |
| **B2-2.4-03** | NON-BLOCKING | event_filter off 時 early return `{"mode":"none"}`（`:1895-1896`）— 符合 SPEC 邊界①。 | — |

### Mutation Gate（M2/M4/M5/M6）

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-M2** | ✅ PASS | 見 B2-2.3-03。 | — |
| **B2-M4** | **BLOCKING** | 見 B2-2.2-03。 | 見上。 |
| **B2-M5** | **BLOCKING** | SPEC §V + TODO §B B2 Gate 要求 **雙腿**：腿A gate ON+錯位→raises；腿B no-op+同資料→**同測試必 FAIL**。**diff 內無任何 `alignment_gate_m5` / M5 測試**（`grep` 0 命中）。 | 新增 `test_alignment_gate_m5_dual_leg`：M1 平移 label ±1 bar；腿A `pytest.raises`；腿B `monkeypatch validate_alignment→no-op` 後 `pytest.raises(AssertionError)` 或自訂 fail。 |
| **B2-M6** | ✅ PASS | `test_alignment_gate_m6_noop_validate_keeps_ic_output_sha`：gate on/off `summary_table` sha256 相等 → PASSED。 | — |

---

## 4) ISO timestamp 序列化 — 全棧三欄

| 層 | 行為 | 斷線風險 |
|----|------|----------|
| **後端** | D-4 寫回 `DatetimeIndex` 後，`turnover_analyzer.py:119-121` 對 index 元素：`ts.isoformat()` if hasattr else `int(ts)`。實跑 receipt：`turnover_analysis.*.time_series.timestamps[0]="2024-01-01T13:00:00"`（`type=str`，n=20339）。`rolling_ic_series` 結構為 `{window_key: [ic_values...]}` **不含 timestamp 軸**（`ic_reporter._sample_rolling_series` 僅降採樣值列表）。 | 序列化變更是 D-4 自然結果，非 ic_reporter 新邏輯。 |
| **前端** | `types.ts:2021` `timestamps: Array<number \| string>` 已聯合型別。`TurnoverTimeSeriesChart.tsx:53-70` 讀 `series.timestamps` 作 tooltip 標籤，**不做數值比較/epoch 假設**。`RollingICChart.tsx` 僅用陣列 index 繪圖，**不讀 timestamps**。 | **不斷** |
| **wiring** | `ic-analysis/page.tsx:768-769` `report?.turnover_analysis?.[activeFeature]` → `TurnoverTimeSeriesChart`；`page.tsx:735` `rolling_ic_series` → `RollingICChart`（無 ts 欄位）。`ICAnalysisService.get_result` 原樣轉發 report dict。 | **不斷** |

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-ISO-01** | NON-BLOCKING | 上表 + 實跑 `ts0=2024-01-01T13:00:00 type=str`。 | 可選：在 `docs/` 或 types 註記「post D-4 turnover ts 為 ISO」；非 merge 阻擋。 |
| **B2-ISO-02** | NON-BLOCKING | 若未來要在 turnover 圖表 X 軸顯示真實時間，需 `new Date(ts)` — 目前 X 軸用 `index` 整數，ISO 變更無影響。 | 產品需求時再改 chart。 |

---

## 5) Fixture 遷移 — 斷言弱化檢查

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-FIX-01** | ✅ PASS | `test_ic_filter_orchestrator_analyze`：RangeIndex → int64 秒 + `return_1` 尾端 NaN（對齊 lag 結構）；**更嚴**。 | — |
| **B2-FIX-02** | ✅ PASS | `test_ic_1a_cut1_split._labels_from_close`：移除 `.fillna(0.0)`，保留 tail NaN — **更嚴**（避免假覆蓋）。 | — |
| **B2-FIX-03** | NON-BLOCKING | `test_irregular_timestamps_still_fail_closed`：接受 `(TimestampDiscontinuityError, AlignmentViolationError)` 聯合 — 仍 fail-closed，範圍略擴（gate 可能先觸發）。 | 可拆成兩個獨立 case 提高可證偽性。 |
| **B2-FIX-04** | ✅ PASS | `pytest tests/momentum/test_ic_filter_orchestrator.py -q` → **39 passed**。 | — |

---

## 6) stage0 validation float64 vs stage2 production float32 邊界

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-DTYPE-01** | **BLOCKING** | **stage2**（`:1843-1845`）：`to_numpy(copy=False)` → 保留 kline `float32`（Codex RCA 建議已落實）。**stage0 Tier-2 close**（`:1776-1778`）：`to_numpy(dtype="float64", copy=False)` → **仍強制 float64**。同一 `raw_data["close"]` 兩路徑 dtype 不一致；stage0 外部 labels + kline Tier-2 oracle 可能與 label 生成路徑數值基準不同。 | stage0 close 改與 stage2 相同：`raw_data["close"].to_numpy(copy=False)`；補 stage0 Tier-2 與 stage2 同 close dtype 的 hermetic 對照測試。 |
| **B2-DTYPE-02** | NON-BLOCKING | `_numeric_payload_sha256` / `_assign_datetime_index_preserving_values` 只驗 index 寫回值守恆，**不涵蓋** close dtype 選擇 — 需在 Task 2.2 文件或測試明示。 | TODO 或 SPEC 補一句「Tier-2 close 須與 label 生成 dtype 一致」。 |

---

## 7) 其他觀察

| ID | 嚴重度 | Receipt | 修法 |
|----|--------|---------|------|
| **B2-MISC-01** | NON-BLOCKING | `_persist_outputs` 仍寫 `data_cache/reports/`（B2 前既有）；多數新測試已 `monkeypatch _persist_outputs` — 良好。 | — |
| **B2-MISC-02** | NON-BLOCKING | `test_stage2_label_generation_with_kline_reader` 未傳 `features_df` — 未覆蓋 D-4 寫回分支（由專項 `test_alignment_gate_stage2_*` 覆蓋）。 | — |

---

## VERIFY 摘要（本 review 實跑）

```bash
# B2 對齊子集
pytest tests/momentum/test_ic_filter_orchestrator.py -k "alignment_gate or slice_alignment or stage3_event_filter" -q
# → 6 passed

# Golden 深相等
pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q
# → 2 passed

# Orchestrator 全檔
pytest tests/momentum/test_ic_filter_orchestrator.py -q
# → 39 passed

# RCA 探針（turnover/grouped numeric vs baseline_old）
# → TURNOVER_NUMERIC_EXACT_EQUAL=True, GROUPED_IC_EXACT_EQUAL=True
```

---

## 機讀收尾

```
ASSUMPTIONS_VERIFIED: stage2 close 已 copy=False；baseline_old/new 已重凍且 golden 深相等；turnover ts 實跑為 ISO str
TESTS_RUN: alignment_gate 6/6 pass; golden 2/2 pass; orchestrator 39/39 pass; RCA probe turnover+grouped exact_equal=True
FAILURES_SEEN: none in executed suites
SCOPE_CHANGES: none (review-only)
NUMERIC_OR_SCHEMA_IMPACT: D-4 DatetimeIndex 寫回；turnover timestamps int→ISO；rolling_ic/summary 語義修復（重凍 baseline）；stage0 close 仍 float64（未統一）
BLOCKING_FINDINGS: B2-2.2-03(M4 stage0), B2-M5, B2-DTYPE-01
NON_BLOCKING_FINDINGS: B2-ISO-01/02, B2-2.2-04, B2-FIX-03, B2-MISC-01/02
RECOMMENDATION: 補 M5+M4 stage0 測試並統一 stage0/stage2 close dtype 後可 APPROVE；重凍 baseline 路徑正確，勿回退 index 修正
```

**Verdict: REJECT**

Verdict: REJECT
