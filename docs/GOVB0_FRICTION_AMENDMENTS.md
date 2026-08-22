# GOVB0_FRICTION_TODO — Amendments（延伸決策檔）

> Internal Frozen TODO（`docs/GOVB0_FRICTION_TODO.md`）**不得就地改寫**決策註記。
> 本檔為延伸層：記錄凍結後的實作決策與錨點，不改變 TODO 正文義務。

## C5 — 絕對態（「皆／須 BLOCK」）抽取為 maintain

- **日期**：2026-08-05
- **決策**：選 **(a)**
- **理由**：`extract_phase2_expected_flips.py` 辨識 TODO 絕對態措辭「皆／須 BLOCK」→ 寫入 phase2 flips 為 `maintain`（from=BLOCK, to=BLOCK）；**勿**改為僅接受「由 X 轉 Y」之 flip 形，否則 `TEST-2.1-RECURSE` 六條與 `TEST-2.2-REGRESS` 會自排除清單消失，削弱 invariance 前提。
- **TODO 錨點**：`docs/GOVB0_FRICTION_TODO.md` Task 2.1 驗證條 `TEST-2.1-RECURSE`（「六條皆 BLOCK」）。
- **實作錨點**：`scripts/extract_phase2_expected_flips.py` 之 `_DIR_RE` 絕對態枝（`abs_all`／`abs_must`）。
- **驗收**：`python3 scripts/extract_phase2_expected_flips.py --check` rc=0；`test_01_c5_absolute_state_recurse_in_flips` 綠。
