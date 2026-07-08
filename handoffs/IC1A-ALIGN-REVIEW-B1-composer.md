# IC 1-align B1 Adversarial Code Review (Composer)

**task-id**: `ic1a-align-review-b1`  
**baseline**: `docs/IC_PHASE1_1A_ALIGN_SPEC.md` v3 Frozen (D-1~D-4, §V mutation) + `docs/IC_PHASE1_1A_ALIGN_TODO.md` Task 1.1/1.2  
**scope reviewed**: uncommitted diff — `momentum/core/contracts.py`, `momentum/Analysis/ic_filter_orchestrator.py`, `tests/momentum/core/test_alignment_contract.py`, `tests/momentum/Analysis/test_ic_1a_cut1_split.py`  
**reviewer**: Composer | **date**: 2026-07-09

## VERIFY receipt (pre-review)

```bash
pytest tests/momentum/core/test_alignment_contract.py \
  tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_horizon_resolver_uses_return_column_before_default_m7 \
  tests/momentum/Analysis/test_ic_1a_cut1_split.py::test_effective_horizon_resolution -q
# 13 passed in 0.39s
```

## Summary

Kernel 骨架（D-1 int64 秒轉型、D-2 bar-ordinal `close[i+lag]/close[i]`、D-3 眾數 cadence + gap 計數）與 Task 1.2 horizon resolver / `purge_gap` 同源接線方向正確；既有 `test_effective_horizon_resolution` 保留未弱化。  
但 Tier-1 **覆蓋率門檻未實作**、Tier-2 **抽樣對單點錯位有系統性漏網**、**「feature ts ∉ close 軸」硬 raise** 與 SPEC 邊界②衝突——B2 接線前須修。M1/M3/M4/M7 對「整段 kernel 失效」可證偽；M1 對「單 bar 錯位」不可證偽（與抽樣洞同源）。

---

## Findings

### ADV-B1-01 — Tier-1 覆蓋率門檻缺失

| | |
|---|---|
| **Severity** | **BLOCKING** |
| **receipt** | SPEC TODO Task 1.1 §「覆蓋率<(len−lag)/len×(1−tol)→raise」；`contracts.py:883-913` 僅檢查 `tail_nans==lag`、cadence、全 NaN，無覆蓋率計算 |
| **實跑** | `python3` probe：100 列僅 10 個有效 label（中間 80 孔）+ lag=5 → `validate_alignment` **PASS**，`checked_samples=15`（應被覆蓋率門檻拒絕） |
| **修法** | 在 Tier-1 加入 `valid_ratio = target_values.notna().sum() / len` 與 `(len-lag)/len * (1-tol)` 比較（`tol` 需對齊既有 config 或 `AlignmentSpec` 擴欄）；不足 → `AlignmentViolationError` |

### ADV-B1-02 — `rng(0)` 固定種子造成 Tier-2 系統性漏抽樣

| | |
|---|---|
| **Severity** | **BLOCKING** |
| **receipt** | `contracts.py:876-877` `np.random.default_rng(0)`；`_sample_alignment_positions` 僅頭 2 + 尾 2 + 中間隨機 |
| **實跑** | 200 列 lag=1、`sample_size=64`：`row 100 ∉ sampled`；掃描 middle rows 2..197 單點腐化 → **135/196 列腐化後仍 PASS**；`row 50` 單點腐化 **MISSED** |
| **修法** | 除頭尾外強制納入 SPEC 要求的「變異敏感區」（gap 鄰近、label 跳變點）；或改為確定性分層抽樣（等距 + 突變點）並附漏網率上界測試；勿僅依賴 `rng(0)` |

### ADV-B1-03 — 缺少「變異敏感區」強制抽樣（§V / CODEX-6 / COMPOSER-8）

| | |
|---|---|
| **Severity** | **BLOCKING** |
| **receipt** | SPEC §V M1「抽樣含變異區」；TODO Task 1.1-2「頭 2+尾 2+變異敏感區+隨機」；`contracts.py:863-880` 無變異區邏輯 |
| **實跑** | 同 ADV-B1-02；gap 測試 `test_validate_alignment_gap_counts_but_passes_cadence` 僅驗 `gap_count==1`，未驗 gap 鄰近列必被 oracle 抽到 |
| **修法** | 在 `_sample_alignment_positions` 對 `abs(diff(label))` 或 gap 邊界索引強制 union；新增 hermetic 測試：僅變異區單點 ±1 bar 錯位必 raise |

### ADV-B1-04 — Tier-2「feature ts missing from close axis」過嚴，違反邊界②

| | |
|---|---|
| **Severity** | **BLOCKING**（B2 Task 2.1 接線阻斷） |
| **receipt** | `contracts.py:920-923` `positioner.reindex(feature_index)` 遇 NaN → raise；TODO Task 2.1 邊界②「feature ts 缺 kline 孔→NaN 合法交覆蓋率」；Tier-2 邊界④「NaN 孔抽樣跳過」 |
| **實跑** | feature 24 列、close 刪 1 孔（23 列）→ `AlignmentViolationError: feature timestamp missing from close axis: 2025-01-01 05:00:00`；預期行為：該列 label=NaN、跳過 oracle、由覆蓋率閘門處理 |
| **修法** | `pd.isna(positions)` 列改為 skip（對應 label 應為 NaN），僅在「有 close 對照且 label 非 NaN 但 oracle 失配」時 raise；與 ADV-B1-01 覆蓋率聯動 |

### ADV-B1-05 — M1 測試對單點錯位不可證偽（假綠風險）

| | |
|---|---|
| **Severity** | **BLOCKING** |
| **receipt** | `test_alignment_contract.py:82-92` 使用 `np.roll` 全域平移（多列同時錯），非 SPEC 意圖的 ±1 bar 單點錯位 |
| **實跑** | `patch('momentum.core.contracts.np.isclose', return_value=True)` → 測試 **FAIL**（整段 oracle 失效可抓）；但單點 row-50/100 腐化 + 現行 kernel → **PASS**（ADV-B1-02） |
| **修法** | 新增 M1 子測試：僅 `shifted.iloc[k]=...` 單列錯位（k 落在 rng(0) 漏網區）；與 ADV-B1-02/03 修法綁定驗收 |

### ADV-B1-06 — M3/M4/M7 對「整段失效」可證偽；M7 缺顯式 mutation receipt

| | |
|---|---|
| **Severity** | **NON-BLOCKING** |
| **receipt** | monkeypatch：`isclose→True` M1 測試 FAIL；`_cadence_report→(0,0)` M4 測試 FAIL；`_normalize` 放行 RangeIndex M3 測試 FAIL；模擬舊 resolver `del labels_df` → `assert ==5` **FAIL** |
| **缺口** | TODO 要求「移除解析回 default→FAIL 轉紅 receipt」；現僅靜態 assert，無獨立 mutation 步驟紀錄 |
| **修法** | 在測試 docstring 或 CI 腳本附一條「故意 revert resolver → pytest 預期 FAIL」receipt 即可 |

### ADV-B1-07 — `purge_gap` 雙重解析 + 不一致 raise：行為正確

| | |
|---|---|
| **Severity** | **NON-BLOCKING**（確認項） |
| **receipt** | `ic_filter_orchestrator.py:579-586` caller 傳 `purge_gap=effective_horizon` + `labels_df`；`:209-211` 內重算並 `purge_gap < effective_horizon` → `ValueError` |
| **實跑** | `return_5` + `default_horizon=1` + `purge_gap=1` + `labels_df` → `pytest.raises(ValueError, match="purge_gap")` **PASS** |
| **結論** | fail-closed 正確；舊 bug 路徑 `labels_df=None` 仍允許 `purge_gap=1`（無 labels 時 fallback），與 SPEC 一致 |

### ADV-B1-08 — D-1/D-2/D-3 核心路徑基本忠實

| | |
|---|---|
| **Severity** | **NON-BLOCKING**（正面觀察） |
| **receipt** | D-1: `contracts.py:786-812` int64 秒 / 毫秒拒絕 / RangeIndex raise；D-2: `933-939` positional `close_pos+lag`；D-3: `838-860` median 定 gap、眾數 cadence、±5% 容差 |
| **實跑** | int64 軸 PASS；單點 gap `gap_count==1` PASS；`freq=12h` on 1h → cadence mismatch raise |
| **備註** | D-3 以 median 定 gap 閾值（非 cadence 迭代）與 TODO 偽碼一致；與 SPEC 文字「1.5×cadence」字面略有循環定義，實作選 median 可接受 |

### ADV-B1-09 — Task 1.2 `horizon_source` metadata 僅在 `labels_df is None` 時記錄

| | |
|---|---|
| **Severity** | **NON-BLOCKING** |
| **receipt** | `ic_filter_orchestrator.py:134-137` warning+`horizon_source:default_fallback`；`labels_df` 存在時無 log/metadata |
| **修法** | 解析成功時寫 `horizon_source:column_parse` + 選中欄名；多欄位時記錄解析集合 |

### ADV-B1-10 — 多欄位 `labels_df` horizon 取 `parsed[0]` 欄位順序依賴

| | |
|---|---|
| **Severity** | **NON-BLOCKING** |
| **receipt** | `ic_filter_orchestrator.py:115-127` `default_horizon in parsed` else `parsed[0]` |
| **風險** | `return_10, return_5` 且 default=1 → 取 10；B1 無選欄 API，B2 stage0 需明確選 label 欄 |
| **修法** | B2 接線時改為「實際選定 label 欄」單一入口，或全欄必須同 horizon |

### ADV-B1-11 — 既有斷言未放寬

| | |
|---|---|
| **Severity** | **NON-BLOCKING**（確認項） |
| **receipt** | `test_effective_horizon_resolution` 保留；`test_alignment_spec_rejects_*` 保留；`test_validate_alignment_signature`（NotImplementedError）合理替換為功能測試 |
| **diff 驗** | `test_ic_1a_cut1_split.py` 僅新增 M7/單位拒絕測試，無刪弱 |

---

## Focus-area verdicts

| # | 議題 | 判定 |
|---|------|------|
| 1 | D-1/D-2/D-3 kernel 忠實度 | 主路徑 OK；缺 Tier-1 覆蓋率（ADV-B1-01） |
| 2 | Tier-2 feature ts ∉ close → raise | **過嚴**，違反邊界②（ADV-B1-04） |
| 3 | `purge_gap` 雙重檢查 | **正確** fail-closed（ADV-B1-07） |
| 4 | M1/M3/M4/M7 可證偽性 | 整段失效可證偽；M1 單點不可（ADV-B1-05/02） |
| 5 | `rng(0)` 漏測 | **是**，135/196 中間列系統性漏網（ADV-B1-02） |
| 6 | 既有斷言 | 未放寬（ADV-B1-11） |

---

## Required fixes before B2

1. 實作 Tier-1 覆蓋率門檻（ADV-B1-01）  
2. Tier-2：close 軸缺孔 → skip + 覆蓋率，非 hard raise（ADV-B1-04）  
3. 抽樣加入變異敏感區 / 消除 `rng(0)` 系統性漏網（ADV-B1-02/03）  
4. M1 增單點錯位 hermetic 測試（ADV-B1-05）  

---

## VERDICT

**REJECT** — 4 項 BLOCKING（覆蓋率缺失、抽樣漏網、變異區缺失、Tier-2 過嚴 + M1 假綠風險）未閉合；B2 接線前須修 kernel。

Verdict: REJECT
