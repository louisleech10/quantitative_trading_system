# IC1C-B1 Code Review (Composer)

**task-id**: IC1C-B1  
**reviewer**: composer (code reviewer)  
**date**: 2026-07-14  
**scope**: Grok B1 實作 — `git diff HEAD` 全量 + `handoffs/IC1C-B1-RESULT.md`  
**authority**: Frozen `docs/IC1C_NETIC_TODO.md` Phase 1 (Tasks 1.1–1.4) + `docs/IC1C_NETIC_SPEC.md` §T/§U  
**method**: 唯讀 diff/源碼對照 + 獨立 gate 複跑

---

## Phase 1 逐 Task 驗收

### Task 1.1 — net_ic_analyzer B-strict

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| 刪 `compute_net_ic` / 禁 `net_ic` 鍵 | PASS | `rg compute_net_ic momentum/` → 0；`test_no_net_ic_key_anywhere` + G-NEW manifest `net_ic_forbidden` |
| `compute_cost_drag` = `(bps/1e4)×turnover` 無 ×2 | PASS | `net_ic_analyzer.py:71-76`；`test_cost_drag_hand_calc`；M2 probe |
| `cost_sensitivity` 階梯 §T + 僅 `{cost_bps,cost_drag_return}` | PASS | `:112-133`；`test_cost_sensitivity_ladder` |
| 三 profile 輸出 | PASS | GROSS_ONLY `:265-273`；COST_ENABLED `:276-293`；SKIPPED 多路徑 `:208-256` |
| conditional metrics 恒 unavailable union | PASS | `_unavailable()` + `test_unavailable_union_shape` / `test_breakeven_unavailable_1c` |
| `factor_returns` 注入忽略 | PASS | `:190 del factor_returns`；`test_factor_returns_ignored` |
| config: `cost_enabled`/`cost_bps`；禁 `default_cost_bps` | PASS | `ic_config_schema.py:267-299`；`config/ic_config.yaml:181-184`；`test_no_default_cost_fallback` |
| validator 非 None 一律驗域 + enabled 需 bps | PASS | `_validate_cost_params` + `test_cost_bps_nan_raises_even_when_disabled` / `test_cost_enabled_requires_bps` / `test_cost_bps_zero_raises` |
| 負/非有限 turnover → SKIPPED；禁 clamp | PASS | `:232-237`；`test_negative_turnover_skipped`；M11 probe |
| summary 契約 §P F5 | PASS | 見 §② 專節 |

### Task 1.2 — orchestrator `_run_net_ic`

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| 兩參 `batch_analyze(summary, turnover_data)` | PASS | `ic_filter_orchestrator.py:1957-1958` 無第三參 |
| 不傳 factor_returns | PASS | docstring `:1943`；實呼叫兩參 |
| unavailable union 傳導 | PASS | T1b `test_run_net_ic_orchestrator_direct` 斷言 `net_factor_return` union + 無 `net_ic` 鍵 |
| `FactorReturnAnalyzer` 未刪 | PASS | `_run_factor_return` 仍存 `:1779-1785` |

### Task 1.3 — turnover proxy

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| `compute_net_ic_proxy` 消失 | PASS | `rg net_ic_proxy momentum/ tests/ api/` → 0 |
| 正名 `compute_cost_drag_proxy` §T 公式 | PASS | `turnover_analyzer.py:125-150` |
| 負/非有限 → raise | PASS | `:142-145`；`test_cost_drag_proxy_nan_turnover_raises` |
| 手算 oracle 0.0015 | PASS | `test_cost_drag_proxy_hand_calc` |
| M8 probe | PASS | mutation_probe_check 9/9 PASS |

### Task 1.4 — reporter/export

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| ① summary CSV 欄 `:150` | PASS | `"cost_drag_return"` |
| ② detailed alias `:209` | PASS | 移除短名 `net_ic`；僅 `net_ic_analysis` |
| ③ `_safe_nested` `:632-635` | PASS | 讀 `cost_drag_return` 裸數 |
| ④ inject 映射 `:774` | PASS | 模組鍵 `net_ic_analysis` 保留 |
| `grep '"net_ic"' ic_reporter.py` | PASS | 0 matches |
| export fixture 手算 | PASS | `test_export_formats.py:78-94` fixture `(10/1e4)*1.5=0.0015`；`test_summary_csv_cost_drag_return_hand_calc` |
| CSV 欄集合不含 net_ic | PASS | `test_summary_csv_columns_match_spec` |

### Phase 1 測試 / Gate

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| T1 具名測試全集 | PASS | RESULT 列 28 項全綠 |
| SCHEMA 專檔 | PASS | `test_net_ic_schema_profiles.py` |
| phase25 近重複刪除 | PASS | `tests/phase25/test_net_ic_analyzer.py` 已刪 |
| G-NEW `--baseline new` | PASS | RESULT exit 0；`g_new.json` 三注入 SKIPPED + 4 feature COST_ENABLED |
| mutation probes | PASS | 9 probes PASS |

---

## 六項重點獵殺

### ① 三 profile 鍵集合恰等 + SCHEMA 專檔唯一源

**PASS**

- 常數專檔：`tests/momentum/Analysis/test_net_ic_schema_profiles.py` 定義 `SCHEMA_SKIPPED` / `SCHEMA_GROSS_ONLY` / `SCHEMA_COST_ENABLED` / `CAPACITY_KEYS`。
- **真 import**（非複製字面）：
  - `tests/momentum/Analysis/test_net_ic_analyzer.py:26-34`
  - `scripts/ic1c_freeze_baseline.py:284-287`（G-NEW profile 斷言）
- `rg 'frozenset.*gross_ic.*turnover_semantics' *.py` → 0 複製。
- T1 對三 profile 皆 `set(feat.keys()) == SCHEMA_*`；freeze 對 SKIPPED/COST_ENABLED 做 equality oracle。

### ② summary 契約

**PASS**

- 已刪：`avg_ic_loss_pct`、`rank_correlation_gross_vs_net`（`test_summary_contract_b_strict` + M6）。
- `evaluable_count` 恒 0；`profitable_count` 恒 0（只計 evaluable，1c 無 evaluable）。
- `avg_cost_drag_return` 僅 `cost_enabled=True` 時存在（GROSS_ONLY 無此鍵）。
- `g_new.json` summary 與契約一致。

### ③ reporter 4 處正名 + export fixture 手算值

**PASS**（見 Task 1.4 表）

### ④ capacity 子鍵恰等 + 非有限→null + JSON strict

**PASS**

- `_capacity_payload` 注入 `calibration:"uncalibrated"`；`estimated_capacity_usd` 經 `_finite_or_null`（`:177-180`）。
- `test_finite_invariants`：`set(cap.keys())==CAPACITY_KEYS` + `json.dumps(..., allow_nan=False)`。
- freeze：`ic1c_freeze_baseline.py:241,574` `allow_nan=False`；`g_new.json` `non_finite_fields:[]`。
- `estimate_factor_capacity` 本體未改（仍 `max(0,turnover)` 於計算函式內，符合 TODO「函式本體不動」）；負 turnover 在 batch 邊界已 SKIPPED，不進 capacity。

### ⑤ orchestrator `_run_net_ic` 兩參 + unavailable union

**PASS**（見 Task 1.2 + T1b）

### ⑥ T1b 直測存在且真測傳導

**PASS**

- 具名測試 `test_run_net_ic_orchestrator_direct`（`:282-303`）。
- 直呼 `ICFilterOrchestrator._run_net_ic`，stub `_report`，斷言 `SCHEMA_GROSS_ONLY` + union + 無 `net_ic`。
- 獨立複跑：`pytest ...::test_run_net_ic_orchestrator_direct` → PASSED。

---

## 獨立 gate 複跑（reviewer VERIFY）

```bash
venv/bin/pytest tests/momentum/Analysis/test_net_ic_analyzer.py \
  tests/momentum/Analysis/test_net_ic_schema_profiles.py \
  tests/momentum/test_turnover_analyzer.py \
  tests/momentum/test_export_formats.py -q
# → 57 passed

bash scripts/mutation_probe_check.sh \
  tests/momentum/Analysis/test_net_ic_analyzer.py \
  tests/momentum/test_turnover_analyzer.py
# → MUTATION-PROBE PASS (9 probes)

rg -n "net_ic_proxy" momentum/ tests/ api/   # → 0
rg -n '"net_ic"' momentum/Analysis/ic_reporter.py  # → 0
rg -n "compute_net_ic" momentum/  # → 0
```

---

## 非 BLOCKING 備註（不阻 B1→B2）

1. **G-NEW 凍結樣本**：`--baseline new` 以 `cost_enabled=True@10bps` 產 COST_ENABLED + 三注入 SKIPPED；GROSS_ONLY 由 T1/T1b 單測覆蓋，未寫入 `g_new.json` 列——與 SPEC §G「直開 cost 產 COST_ENABLED 樣本」一致。
2. **`batch_analyze` 簽名仍保留第三參 `factor_returns`**（`del` 忽略）；orchestrator 已兩參呼叫，行為符合 Task 1.2。
3. **M10 三層完整**（API/schema validator probe）屬 B2/T-F4；B1 僅 T1 層 `test_mutation_m10_drop_finite_guard`，與 TODO 批次策略一致。
4. **phase24 `default_cost_bps` 舊斷言**未動——RESULT 已標 B2/T5 scope。

---

## 裁決摘要

B1 批次對照 Frozen TODO Phase 1 四 Task + §T/§U 六項重點：**全部 PASS**；gate 57 tests + 9 mutation probes 獨立複跑綠；靜態 grep 零殘留 `net_ic`/`net_ic_proxy`/`compute_net_ic`。

CODE-REVIEW: APPROVE (0 BLOCKING)
