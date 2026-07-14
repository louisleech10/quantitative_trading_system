# IC1CFR-B2 — Code Review (Composer)

**task-id**: IC1CFR-B2 | **審查者**: Composer | **日期**: 2026-07-15  
**對照**: Frozen `docs/IC1CFR_STOPGAP_TODO.md` Phase 2 + `git diff HEAD` + `handoffs/IC1CFR-B2-RESULT.md` + 未追蹤 `FactorReturnChart.test.tsx` / `FactorEquityCurveChart.test.tsx`

## ① 兩圖三態下架（union / legacy 有限 / 缺鍵 → 警示空態；禁 fallback 數值）

| 元件 | union 佔位 | legacy 有限 | 缺鍵 | loading/error | 禁數值 |
|------|-----------|------------|------|---------------|--------|
| **FactorReturnChart** | `isFactorReturnUnavailableUnion` → `factor-return-unavailable` + 文案 | `isFactorReturnLegacyFinitePayload` → 同警示；`extractFactorReturnChartPoints` 恒 `[]` | `data==null` → `factor-return-empty`「暫無…」（Task 2.1 邊界③） | 三態齊；`page.tsx` 已接 `loading`/`error` | recharts 已移除；DOM 測禁 `0.042`/`0.05` |
| **FactorEquityCurveChart** | 有 data → unavailable | `legacyFiniteQuantile` → unavailable；`extract` 恒 `[]` | `null` → 仍 unavailable（Task 2.2「主流程皆下架」） | 三態齊；page 已接線 | 舊 ComposedChart/html2canvas/metrics 全刪 |

`status==='ok'` 亦經 `extract` 恒空 → 走 unavailable 分支，不繪有限點。**PASS**。

## ② `types.ts` — `ICReport.factor_returns` 真改 §U union

- `FactorReturnData = FactorReturnDataOk | FactorReturnDataUnavailable`（非旁路 `Record<feature,…>`）。
- `ICReport.factor_returns?: FactorReturnData`（`:2120`）已掛 union。
- 元件 props 保留 `Record<string, unknown>` 僅收 runtime legacy，型別本體未再收納 legacy map — 符合 T-S4 意圖。
- vitest 源碼守衛 + `npm run test` 12 passed。**PASS**。

## ③ M3 / M4 probe 真自證

| Probe | 現況 | vs M1/M2 標竿 |
|-------|------|---------------|
| **M3** `test_mutation_m3_render_legacy` | 內嵌 `legacyExtract` 證「舊邏輯會出點」；**production** `extractFactorReturnChartPoints(legacy)==[]` 為真牙；`toThrow` 比對 `[]` vs mutated **儀式性**（production 正確時必綠） | 未 monkeypatch production `extract` 再跑 `legacy_finite_payload_not_rendered` 期待紅 |
| **M4** `test_mutation_m4_render_legacy_equity` | 同型：`extractFactorEquityCurvePoints` 恒空 + 內嵌位置相減 + 儀式 `toThrow` | 同上 |

**實效**：若有人恢復 `extract*` 舊邏輯 → 行 123/125 `toEqual([])` **會紅**；若直接恢復 recharts 繪圖 → `legacy_finite_*_not_rendered` DOM 斷言 **會紅**。  
**缺口**：probe 函式本身不像 M1 `monkeypatch + pytest.raises(AssertionError)` 那樣**實跑突變後自證轉紅**；`toThrow` 區塊不增覆蓋。**NB1**（stopgap 可接受；建議日後改 `vi.spyOn(extract*, legacyImpl)` 再斷言具名測轉紅）。

## ④ scope 擴張三項裁決

| 擴張 | 動機 | 假綠？ | 裁決 |
|------|------|--------|------|
| **phase26 §V 漏改** | B1 sanitizer 後 FR 恒 `unavailable` 非 `skipped`；`skipped_count` 10→9 + 新增 unavailable 斷言；skip/timeout/error oracle 改 `_run_factor_centrality` | 否 — 分類語意改測**非 FR** 模組，斷言強度不減 | **必要 enabler**（B1 殘留；非 analyzer 計算） |
| **export session fixture redirect** | `export_task` yield 期間持有 `_ACTIVE` → 後續 suite 15 ERROR；改 setup-only activate + `finally deactivate` | 否 — 僅釋放 redirect；`test_export_csv_*` 內容斷言未刪 | **必要 enabler**（測試衛生） |
| **freeze parser 偽陽性** | log `pkg.mod:file.py` 被當 collection ERROR nodeid；加 path 形狀過濾 | 否 — 修 gate 假陽性，不掩蓋真 fail | **必要 enabler** |

## ⑤ 前端文案（繁中 + 下架句）

- `FACTOR_RETURN_UNAVAILABLE_NOTICE` / `FACTOR_EQUITY_UNAVAILABLE_NOTICE` = **`錯位序列已下架,待 1c-FR 重建`**（繁中、含 `1c-FR`）。
- vitest 斷言 `錯位序列已下架` + `/1c-FR/`。**PASS**。

## ⑥ `monotonicity_tester` 未動

`git diff HEAD -- momentum/Analysis/monotonicity_tester.py` → **0 行**；元件註解明示 producer 不動。**PASS**。

## 獨立驗證（本輪實跑）

```
npm --prefix frontend run test -- FactorReturnChart.test.tsx FactorEquityCurveChart.test.tsx → 2 files, 12 passed
grep -n "1c-FR" FactorReturnChart.tsx FactorEquityCurveChart.tsx → 各 ≥1
grep "recharts" FactorReturnChart.tsx FactorEquityCurveChart.tsx → 僅註解提及 LineChart（無 import）
```

## 其他 NB

- **NB2**: `FactorEquityCurveChart.tsx:39` 註解寫「缺鍵走 empty」，實作 `null` 走 `factor-equity-unavailable` — 與 Task 2.2 行為一致，註解略舊。
- **NB3**: 兩 vitest 檔仍 `??` 未 commit；合併前須入版。

## 結論

Phase 2 Tasks 2.1/2.2 對照 Frozen TODO 已落地：兩圖下架、§U 型別真改、三態齊、文案合規、producer 未動；scope 三項為過 B2 Gate 之必要 enabler、非藉 fixture 放寬斷言之假綠。M3/M4 probe 弱於 M1 自證模型但行為守衛足夠。**0 BLOCKING**。

CODE-REVIEW: APPROVE (0 BLOCKING)
