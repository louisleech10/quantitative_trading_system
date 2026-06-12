# Batch1 Follow-up — Adversarial Reconcile R2（Composer 2.5 獨立版）

> 審查對象：`docs/BATCH1_FOLLOWUP_SPEC.md`（V3）/ `docs/BATCH1_FOLLOWUP_TODO.md`（V3）/ `docs/BATCH1_FOLLOWUP_MANIFEST.md`（V3）  
> 對照基線：`handoffs/20260612-batch1-followup-adversarial-composer.md`（r1，P1–P8）  
> 審查者：Composer 2.5（獨立 r2，未讀 Codex r2 全文）  
> 焦點：P1–P8 在 V3 是否收斂；P7 決策評估；新引入 BLOCKING  
> 日期：2026-06-12  
> 方法：逐條對照 r1 finding ↔ V3 三檔原文 + 關鍵錨點 spot-check（rg/Read）

---

## Verdict：V3 已收斂 r1 全部 finding；可派工

r1 的 1 BLOCKING + 3 MAJOR + 2 MINOR + 1 Suggestion 均在 V3 SPEC/TODO/MANIFEST 有明確對應修補與可追溯引用。獨立 spot-check 確認 `:3070`/`:3325`、`:917-918`、`scripts/` 兩消費者錨點與 HEAD 程式一致。未發現 V3 新引入之 BLOCKING。

---

## P1–P8 逐條核對

| ID | r1 嚴重度 | V3 狀態 | V3 原文證據（摘錄） | 備註 |
|----|-----------|---------|---------------------|------|
| **P1** | BLOCKING | **RESOLVED** | SPEC §A L16：「單 TF metadata 組裝有**兩處**：`feature_factory.py:3070-3071`（stream CGSA）與 **`:3325-3326`（legacy L7 `_layer7_validate_and_persist`…）**」；Task 4.1 L95–99 套用兩點 +「stream/legacy/multi-TF 三路徑」驗收；MANIFEST [B1-4] L9 同文；TODO Task 4.1 L128–129 刪 `:3219`、改 `:3325-3326` | spot-check：`failed_layers` 確在 `:3070`、`:3325` |
| **P2** | MAJOR | **RESOLVED** | SPEC §A L15：「`nan_mask`…在 **`feature_storage.py:917-918`**（V2 寫 938-943 錯誤）」；§C L30、Task 2.2 L69；MANIFEST [B1-2] L8；TODO §0 L9 | spot-check：`:917` `nan_mask = np.isnan(array)` |
| **P3** | MAJOR | **RESOLVED** | SPEC §A L16：「V2 的 `:3219` 錨點錯誤…**刪除**」；TODO Task 4.1 僅列 `:3070-3071` + `:3325-3326`，無 `:3219` | — |
| **P4** | MAJOR | **RESOLVED** | SPEC §A L18：「**`scripts/` 有 2 個消費者**（`profile_multi_tf_baseline.py:414`、`profile_v6v7_comparison.py:466`）」；Task 4.2 L103–105 列入 scope + grep 含 `scripts/`；MANIFEST [B1-6] L11；TODO §B L24、Task 4.2 L140–145 | spot-check：兩檔仍讀 `actual_timeframes`（待實作改） |
| **P5** | MAJOR | **RESOLVED** | SPEC §G L40：「mid-hole（**abnormal/total>0.17>門檻 0.16346**）→partial」；Task 2.2 L70；TODO Task 2.2 L87「72/400→0.18>0.17>0.16346，手算入註解」；MANIFEST [B1-3] L9 | 雙向斷言可證偽性已綁定 |
| **P6** | MINOR | **RESOLVED** | SPEC Task 2.3 L74–78：P0 凍結 perf 基準、**warmup 1 丟棄、median-of-3**、×1.15/×1.10；§G L38；MANIFEST [B1-9] L14；TODO Task 2.3 L90–97 | 由「相對門檻無基準」改為 baseline 比對 |
| **P7** | MINOR | **RESOLVED**（決策見下） | SPEC Task 3.1 L88：「**拒 setter——無共享 mutable state**」；`validate_factory_output(..., winsor_window=None)` per-call；TODO L114「**禁 constructor kwarg/setter**」；DECISION §V3 #9 | 評估：**可接受**（見 §P7） |
| **P8** | Suggestion | **RESOLVED** | SPEC Task 4.1 L101、§N L121：「scan-CGSA（`:3142-3226` 無 completeness）**out-of-scope**」；TODO Task 4.1 L133；MANIFEST [B1-10] L15 | 主路徑=stream 已登記 |

---

## §P7 決策評估（不重開）

| 項目 | r1 建議 | V3 採用 | 評估 |
|------|---------|---------|------|
| N3 winsor 注入時序 | (b) validate 前 **setter** | **per-call** `winsor_window: Optional[int]=None`；factory `:3340` 顯式傳 `config…window`；API `feature_task_service.py:185` 不傳=252 | **可接受** |

理由（簡述）：
1. r1 核心風險是「init 無 config + 雙重注入」——V3 用 per-call 顯式參數 + 「禁 setter/constructor kwarg」閉合，無共享 mutable state。
2. `window is None → 252` 用顯式 None 判斷（禁 `or 252`），`window<=0 → ValueError`，覆蓋 r1 擔心的靜默回退。
3. factory/API 兩 caller 路徑在 Task 3.1 與 DECISION #9 已盤點，執行端可 grep 驗收。

per-call 相對 setter 在 thread-safety 與可測性上更嚴，不劣於 r1 建議。

---

## 新引入缺陷掃描（僅列需擋派工項）

| 檢查項 | 結果 |
|--------|------|
| r1 錨點回歸（錯行號復發） | 未見；`:917-918`、`:3325-3326` spot-check 通過 |
| N7 scope 仍漏 legacy | 已列雙路徑 + 三路徑驗收 |
| T5 scripts 仍 out-of-scope | 已列入 Task 4.2 + grep gate |
| N6 門檻未綁定 | 已寫 0.17 / 0.16346 / 手算註解 |
| 內部矛盾（setter 與 per-call 並存） | 無；「不可做」明禁 setter |
| 弱化 NaN/inf gate | 無；all-NaN=total_nan 與 reference oracle 強化 |
| **新 BLOCKING** | **無** |

非 BLOCKING 備註（不擋派工）：
- `multi_tf_generator.py` 未寫完整路徑 `timeframe/`（與 r1 相同慣例）；`:546` spot-check 為 worker `failed_layers.extend` 聚合點，與 Task 4.1 敘述一致。
- MANIFEST [B1-10] 寫「P1–P7 收斂」；P8 亦在 §N/out-of-scope 登記——索引用語小缺，不影響執行。

---

## V3 相對 r1 的增量（非 finding，供派工 awareness）

- Task **2.4** 真實 kline gate（Codex r2 B4 + 驗證保真度鐵律）：強化 [B1-3]，非 r1 要求但方向正確。
- P0 baseline 增 **nan_stats 6 案例** + **perf 凍結**（呼應 P5/P6 根因）。
- N7 增 **worker 聚合 `:546`**（冪等 canonicalizer）——在 P1 兩處之上擴 scope，有冪等規則與測試，可接受。

---

## ASSUMPTIONS_VERIFIED

- r1 P1–P8 均在 V3 三檔有明確 reconcile 引用（Composer P1–P8 字樣或等價條文）。
- `feature_factory.py:3070,3325`、`feature_storage.py:917-918`、`scripts/*:414,466` 與 V3 錨點一致。
- `feature_factory.py:3340` 為 `validate_factory_output` 呼叫點（N3 接線錨點有效）。

## TESTS_RUN

- `rg failed_layers feature_factory.py` → :3070, :3325
- `rg nan_mask feature_storage.py` → :917-918
- `rg actual_timeframes scripts/` → 2 hits（待 Task 4.2 實作）
- Read `timeframe/multi_tf_generator.py:546`、`feature_storage.py:582`

## FAILURES_SEEN

- none（reconcile-only，未改碼）

## SCOPE_CHANGES

- none（審查-only）

## NUMERIC_OR_SCHEMA_IMPACT

- none（審查-only）；V3 設計意圖與 r1 一致，無新增 schema 變更

---

HANDOFF_NOT_UPDATED: 根 HANDOFF 由 Claude 維護；本輪僅寫 reconcile r2 交接檔。

STATUS: PASS — 可派工
