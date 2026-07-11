# IC1EB-B5-IMPL-RESULT — Task 5.1 Golden 三腿+選型 diff+1a 重生

**Agent**: Grok 4.5 | **Date**: 2026-07-11 | **Status**: **BLOCKED-1A**  
**SPEC**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §G v2 | **TODO**: Phase 5 Task 5.1  
**Prompt**: `handoffs/IC1EB-B5-IMPL-PROMPT.md` | **基底**: main `49ef0ac`

## 白話摘要

B5 要證明兩件事：(1) 換上 HAC+FDR 顯著性後，**IC 點估計等非顯著性欄位沒漂**（G-1）；(2) **誰被篩掉、為什麼**可審計（G-2 對照表）；再加 fail-closed 契約（G-3）。  
G-1/G-2/G-3 已用 `handoffs/ic1eb_baseline/` 預物化輸入重放新路徑完成，行為方向符合「高自相關假顯著轉紅」。  
**1a cut1 golden 重生**：在 pre-B2 commit `c0b29ac` worktree 重跑凍結後，**與 `baseline_meta.json` / `baseline_new_meta.json` 宣告雜湊不一致** → 依派工鐵律 **BLOCKED-1A 停手**（禁湊合放回）。1a 兩測試維持 skip-if-absent。

### 名詞對照
| 中文 | English / 縮寫 |
|------|----------------|
| 五雜湊 | five_hash（index/columns/dtypes/nanmask/values） |
| 新路徑凍結 | newpath freeze（`ic1eb_newpath_freeze/`） |
| 錯誤發現率 | FDR（False Discovery Rate） |
| 異方差自相關穩健 | HAC（Heteroskedasticity and Autocorrelation Consistent） |
| 舊路徑 i.i.d. p 值 | p_iid_old |

---

## G-1 不變腿

**實作**：
- `scripts/ic1eb_b5_replay.py` — 重用 `scripts.capture_ic1eb_baseline` 的 `five_hash` / `summary_to_g1_frame` / `patch_persist_outputs`
- `tests/momentum/Analysis/test_ic_1eb_b5_golden.py`
  - `test_g1_fast_btc_12h_f754_invariant`（**不掛** `slow_stat`）
  - `test_g1_slow_runs_invariant` ×12（掛 `slow_stat`）
  - 斷言：`g1_five_hash` 五欄 + `summary_feature_order_sha256` + `series_sha256`（rolling/decay/grouped）

**Receipt** VERIFY:IC1EB-B5-G1G3  
```text
venv/bin/python scripts/run_with_receipt.py --claim-id IC1EB-B5-G1G3 -- \
  venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1eb_b5_golden.py -q --tb=line
→ 18 passed, 9190 warnings in 349.77s
→ handoffs/run_receipts/20260710T221600Z-IC1EB-B5-G1G3.json
```

baseline 唯讀：重放前 `verify_inputs_integrity`；抽樣 inputs sha 仍與 manifest 一致。

---

## G-2 變更腿

**實作**：
- `scripts/ic1eb_g2_golden_diff.py`（全程式生成，禁手填）
- 產出：
  - `handoffs/IC1EB-GOLDEN-DIFF.md`（13 顆 per-feature 表 + 方向摘要 + fraction_nan_p）
  - `handoffs/ic1eb_newpath_freeze/`（manifest + 13 report + per_feature_diff.json；已 gitignore）

**方向摘要（可審）**：

| metric | value |
|--------|------:|
| n_feature_rows | 6488 |
| pass_both | 506 |
| pass_old_only（假顯著→轉紅） | **273** |
| pass_new_only | **0** |
| pass_neither | 5709 |
| fraction_p_inflated (p_hac>p_iid) | **0.941** |

解讀：HAC 相對 i.i.d. 幾乎全面抬 p；FDR 後通過集合只縮不擴（new_only=0），符合「高自相關假顯著轉紅」。

**fraction_nan_p（12h 短窗）**：大多 ~0.002（約 1/499 特徵 fail-closed NaN p）；event/full/xsec 為 0.0；非爆炸性短窗失效。

**Receipt** VERIFY:IC1EB-B5-G2  
```text
venv/bin/python scripts/ic1eb_g2_golden_diff.py
→ G2_EXIT=0；wrote IC1EB-GOLDEN-DIFF.md；freeze→ic1eb_newpath_freeze
→ newpath_freeze_manifest_sha256=0aa54b2d0065e41f27ff825d208b71c38978eae8ee0e166dfd0bf150edf39ab2
```

---

## G-3 fail-closed 腿

| 斷言 | 結果 |
|------|------|
| n_valid < max(8,2L) → p=NaN | PASS |
| 全 NaN / std=0 → p=NaN | PASS |
| SelectionScope 違約 → raise | PASS |
| xsec labels_path 單軸 → 仍 raise，type=`InvalidInputError`（對齊 baseline receipt） | PASS |

---

## 1a baseline 重生 → **BLOCKED-1A**

**程序**：
1. `git worktree add /tmp/ic1eb-b5-1a-c0b29ac c0b29ac`（主工作樹未 checkout/stash）
2. symlink `data_cache` + `venv`；複製既有 `tests/golden/ic_phase1_1a_cut1/inputs/`
3. freeze 腳本 rematerialize 失敗（`data_cache/features/BTCUSDT/a384e6d2.../manifest.json`  absent）→ 改以 **既有 inputs** + `ICAnalysisService` 重放（對齊 golden test `_run_baseline`）
4. 雜湊比對 meta 宣告：

| 檔 | declared (meta) | actual (c0b29ac 重生) | match |
|----|-----------------|------------------------|-------|
| baseline_old | `963ba4f2…` | `2b5e4ca6…` | **False** |
| baseline_new | `946591ad…` | `6ec10209…` | **False** |

比對機讀：`handoffs/IC1EB-B5-1A-HASH-COMPARE.json`  
OLD 位元組數=99095197（與 2026-07-09 重凍紀錄 size 相同），但 **full-file sha256 仍不等於 meta 宣告**（含 `generated_at` 與可能的殘餘非決定性）；依派工 **禁湊合放回**。

5. worktree 已刪除：`git worktree remove --force /tmp/ic1eb-b5-1a-c0b29ac`

**1a golden 現況**：
```text
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q
→ 2 skipped（baseline 檔 absent；誠實 skip，非假綠）
```

---

## 全套 momentum

```text
venv/bin/python scripts/run_with_receipt.py --claim-id IC1EB-B5-momentum-full -- \
  venv/bin/python -m pytest tests/momentum/ -q --tb=line
→ 1055 passed, 5 skipped in 549.50s (0:09:09)
→ handoffs/run_receipts/20260710T220956Z-IC1EB-B5-momentum-full.json
```
（5 skip 含 1a golden×2 + 既有 skip；B5 G-1/G-3 含於 passed）

---

## 產出檔清單

| 路徑 | 說明 |
|------|------|
| `scripts/ic1eb_b5_replay.py` | G-1/G-2 共用重放 |
| `scripts/ic1eb_g2_golden_diff.py` | G-2 生成器 |
| `tests/momentum/Analysis/test_ic_1eb_b5_golden.py` | G-1 + G-3 |
| `handoffs/IC1EB-GOLDEN-DIFF.md` | G-2 對照表（可審） |
| `handoffs/ic1eb_newpath_freeze/` | 新路徑凍結（gitignore） |
| `handoffs/IC1EB-B5-1A-HASH-COMPARE.json` | 1a 雜湊比對 |
| `.gitignore` | 加入 `ic1eb_newpath_freeze/` |

**未改**：`handoffs/ic1eb_baseline/`（唯讀）、`data_cache/` 業務資料、主樹 git history。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: five_hash/summary_to_g1_frame 與 capture 同源; patch_persist 重放; baseline inputs integrity; G-1 13 顆全過; G-2 13 顆程式生成; 1a c0b29ac 重生 full-file sha ≠ meta
TESTS_RUN: pytest test_ic_1eb_b5_golden.py → 18 passed (348s); scripts/ic1eb_g2_golden_diff.py → exit 0; pytest tests/momentum/ → 1055 passed + 5 skipped; test_ic_1a_cut1_golden.py → 2 skipped
FAILURES_SEEN: G-3 sample n=10 未觸發 fail-closed → 改 n=5 一輪修過; 1a freeze rematerialize FileNotFoundError → 改 inputs 重放後仍 hash mismatch → BLOCKED-1A
SCOPE_CHANGES: none（.gitignore 僅 B5 freeze 產物）
NUMERIC_OR_SCHEMA_IMPACT: 無 production schema 變更; G-2 記錄 passed 集合收縮（273 old_only→red）; 1a golden 未放回
```

STATUS: BLOCKED-1A — 1a baseline 於 c0b29ac 重生雜湊與 meta 宣告不一致，禁湊合放回；G-1/G-2/G-3 已完成且 momentum 1055 passed
