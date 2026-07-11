# IC1EB-B5 Code Review — Composer（委員，非實作者）

**Task**: IC 1e+1b B5（Task 5.1 Golden 三腿 + 選型 diff + 1a 解鎖）  
**實作者**: Grok 4.5（G-1/G-2/G-3）；Claude 編排端（1a 解鎖 / 新凍結）  
**自報**: `handoffs/IC1EB-B5-IMPL-RESULT.md`（未採信，獨立驗證）  
**規格**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §G v2 + TODO Task 5.1 + `handoffs/IC1EB-B5-IMPL-PROMPT.md`  
**審查時間**: 2026-07-11

---

## 獨立驗證命令（實跑）

| 命令 | 結果 |
|------|------|
| `source venv/bin/activate && venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1eb_b5_golden.py::test_g1_fast_btc_12h_f754_invariant -q --tb=short` | **1 passed** in 16.17s |
| `source venv/bin/activate && venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1eb_b5_golden.py -k g3 -q --tb=short` | **4 passed** in 11.21s |
| `source venv/bin/activate && venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q --tb=short` | **2 passed** in 42.20s |
| `git status --short tests/golden/l65/test_inventory.txt` | 空（**未**覆寫，無需 restore） |
| ad-hoc：`ic_mean` +1e-6 mutation → `assert_g1_invariant` | **轉紅**（`values_sha256 mismatch`） |
| ad-hoc：3 列 per-feature 復算 + direction 聚合 | 與 `IC1EB-GOLDEN-DIFF.md` / `per_feature_diff.json` 一致 |
| ad-hoc：1a / freeze manifest / report sha256 鏈 | 見各節 |

〔編排端 receipt：`handoffs/run_receipts/20260710T234345Z-ic1eb-b5-full-gate.log` 1057 passed；本輪未重跑全套 13 顆 slow_stat G-1〕

---

## (1) G-1 不變腿測試 — **PASS**

| 檢查項 | 證據 |
|--------|------|
| 唯讀消費 baseline | `baseline_manifest` fixture 僅 `load_manifest()` + `verify_inputs_integrity()`；無寫入 `handoffs/ic1eb_baseline/` |
| 五 hash 程序同源 | `scripts/ic1eb_b5_replay.py` 自 `scripts.capture_ic1eb_baseline` import `five_hash` / `summary_to_g1_frame` / `patch_persist_outputs`（與 capture F6/F8 同構） |
| 重放同 patch | module fixture 與 `replay_run` 前均 `patch_persist_outputs()` |
| 斷言範圍 | `assert_g1_invariant`：`g1_five_hash` 五欄 + `summary_feature_order_sha256` + `series_sha256`（rolling/decay/grouped） |
| 13 顆覆蓋 | `test_g1_manifest_covers_13_runs`；快顆 `long_BTCUSDT_12h_f754aad4` 無 `slow_stat`；其餘 12 顆 parametrize + `slow_stat` |
| mutation 轉紅 | 對快顆 replay 結果將首列 `ic_mean` +1e-6 → `AssertionError: G-1 five_hash.values_sha256 mismatch` |

**可證偽反例**: 在 `summary_to_g1_frame` 將 `G1_COLUMNS` 順序改動或省略 `patch_persist_outputs` → 快顆或 slow 顆 `five_hash.*` 轉紅。

**FINDING（低，非 BLOCK）**: 無像 B2/B3 的 `scripts/ic1eb_b5_mutation_probe.py` 入庫 receipt；mutation 僅 ad-hoc 驗過。建議後續補一條輕量 probe 或 pytest marker 供 CI 抽驗。

---

## (2) G-2 變更腿 / `IC1EB-GOLDEN-DIFF.md` — **PASS**

| 檢查項 | 證據 |
|--------|------|
| 程式生成 | 生成器 `scripts/ic1eb_g2_golden_diff.py`；diff 檔頭 `generator:` 欄一致 |
| 抽樣復算 | `long_BTCUSDT_12h_f754aad4` 三列 `pass_old=True`：`p_iid_old` / `p_hac` / `q` / `pass_*` / `reason` 與 `per_feature_diff.json` 逐欄一致 |
| 方向摘要 | `pass_old_only=273`；273/273 列滿足 `p_hac > p_iid_old`；`fraction_p_inflated=5160/5482=0.941262` 與 MD 表一致 |
| `fraction_nan_p` 合理性 | 12h 縱向多為 **~0.002**（≈1/499 或 1/498 列 NaN p，符合 fail-closed 低比例預期）；event/full/xsec=0.0；非爆炸性短窗失效 |
| 高自相關假顯著轉紅 | **有數據支撐**：273 列 old-only 全數 p 膨脹；`pass_new_only=0`（FDR 後無新增通過） |

**可證偽反例**: 手改 `IC1EB-GOLDEN-DIFF.md` 任一 `p_hac` 或 `pass_old_only` → 重跑 `ic1eb_g2_golden_diff.py` 或對 `per_feature_diff.json` 復算轉紅。

---

## (3) G-3 fail-closed 腿 — **PASS**

| 斷言 | 結果 |
|------|------|
| `n_valid < max(8,2L)` → p=NaN | PASS（n=5） |
| 全 NaN / std=0 → p=NaN | PASS |
| SelectionScope 違約 → ValueError | PASS |
| xsec `labels_path` 單軸 → raise | PASS；`exception_type == InvalidInputError`（對齊 `expected_raise_runs.xsec_labels_return5_12h`） |

ad-hoc 補驗：`run_xsec_labels_raise` 之 `str(exc)` 與 baseline receipt `exception_message` **位元組級一致**（測試僅斷言 type）。

**可證偽反例**: 在 orchestrator 放行單軸 `labels_path` → `test_g3_xsec_labels_path_still_raises` 轉綠（假綠）。

**FINDING（低，非 BLOCK）**: `test_g3_xsec_labels_path_still_raises` 未斷言 `exception_message`；建議補 `match=` 或顯式字串比對以鎖死 F14 receipt。

---

## (4) newpath freeze — **PASS**

| 檢查項 | 證據 |
|--------|------|
| 目錄 | `handoffs/ic1eb_newpath_freeze/`：manifest + 13 `*.report.json` + `per_feature_diff.json` |
| manifest 格式 | 仿 baseline：`runs` 每項含 `report_sha256`、`feature_name_set_sha256`、`feature_pq_values_sha256`、`g1_five_hash`、`passed_set_sha256`、`fraction_nan_p` 等 |
| 雜湊自洽 | `baseline_manifest.json` sha = MD 宣告 `0aa54b2d…`；`long_BTCUSDT_12h_f754aad4.report.json` sha 與 manifest 項一致；`per_feature_diff_sha256` 與檔案一致 |
| 全域 | `name_set_sha256`、`direction_summary`、`fraction_nan_p_12h` 入 manifest |

**可證偽反例**: 改任一 report JSON 一字節不更新 manifest → sha 鏈斷裂。

---

## (5) 1a 解鎖（Claude 編排端）— **PASS**（附 provenance FINDING）

### 根因論證（Grok BLOCKED-1A）

| 主張 | 獨立驗證 |
|------|----------|
| 原件滅失 | `git cat-file -e c0b29ac:tests/golden/.../baseline_old_*.json` 歷史上不存在（B2 R2 codex 已記）；quarantine README 如實 |
| c0b29ac 重生 ≠ 舊 meta 宣告 | `handoffs/IC1EB-B5-1A-HASH-COMPARE.json`：`old_match=false`、`new_match=false`（declared `963ba4f2…` vs actual `2b5e4ca6…`） |
| flag-off 腳本無顯式 override | `freeze_baseline.py` **未**傳 `config_override`；`freeze_baseline_new.py` **有** `ic_train_test_split: True`；golden test **有** `split_on=False` 顯式 override |
| 預設漂移假說 |  plausible 但非本次 hash 失配唯一根因；更直接根因=gitignored 原件滅失 + B2 越界重凍自指 sha 失配 |

Grok 依派工 **BLOCKED-1A 停手、禁湊合** → **正確**。

### 編排端解鎖（現況）

| 檢查項 | 證據 |
|--------|------|
| 新凍結兩態 | `baseline_meta.json` / `baseline_new_meta.json` 宣告 sha 與實檔 **match=True**（`91941b67…` / `e2e0b2e5…`） |
| 原程序 | `reproduction_command` 仍指向 `freeze_baseline.py` / `freeze_baseline_new.py`；inputs 路徑未變 |
| 測試回歸 | `test_ic_1a_cut1_golden.py` **2 passed**（非 skip） |
| quarantine README | 如實記 B2 越界、原件滅失、skip 義務 |

**FINDING（中，非 BLOCK）**: `handoffs/ic1a_cut1_original_regen/README.md` 稱 c0b29ac 與 854d444 重生「內容相等」，但歸檔檔 sha=`f4046d33…` **≠** Grok 記錄的 c0b29ac actual=`2b5e4ca6…`（同 size 99095197 vs 現行 golden 99104780 亦不同）。歸檔為**歷史證據**，與現行 `tests/golden/` 新凍結（編排端解鎖後更新 meta）為不同世代；README 宜標註「歸檔 ≠ 現行 golden」以免誤讀。

**FINDING（低）**: 解鎖路徑=更新 meta 宣告 sha 以匹配新路徑重凍結果，而非 B5 字面「與舊宣告一致才放回」；屬編排端核准的程序例外，功能上已由 2 passed 背書。

**可證偽反例**: 刪 `tests/golden/ic_phase1_1a_cut1/baseline_old_*.json` → 兩測試 skip（誠實 absent），非假綠。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: capture 同源 five_hash+patch; baseline inputs integrity; G-2 腳本生成+抽樣復算; G-3 xsec type+message; freeze sha 鏈; 1a meta↔檔一致+2 passed; l65 inventory 未動
TESTS_RUN: G-1 fast 1p; G-3 4p; 1a golden 2p; ad-hoc mutation+G-2 recalc+hash chain（見上表）
FAILURES_SEEN: none
SCOPE_CHANGES: 僅新增 handoffs/IC1EB-B5-REVIEW-composer.md
NUMERIC_OR_SCHEMA_IMPACT: 無（審查唯讀）；G-2 已記錄 273 old-only 轉紅（實作產物，非本輪改動）
```

VERDICT: PASS
