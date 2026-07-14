# IC1CFR-B2 RESULT — Phase 2 Tasks 2.1+2.2 (+ codex REJECT 退修)

**task-id**: IC1CFR-B2  
**agent**: Grok (impl / B2 rework)  
**date**: 2026-07-15  
**status**: DONE

## 摘要

Phase 2 前端兩圖下架 + types §U + B2 Gate 全綠。VERIFY:handoffs/IC1CFR-B2-RECEIPT.md  
**codex code review REJECT 1 BLOCKING 已修**：`FactorReturnChart` 缺鍵/`data==null` 改顯示下架警示（同 Equity），測試改具名斷言並不再固化「暫無」通用空態。

| Task | 內容 |
|------|------|
| 2.1 | `FactorReturnChart`：union / legacy 有限 / **缺鍵 null** 三態皆「錯位序列已下架,待 1c-FR 重建」；`types.ts` §U；vitest + M3 |
| 2.2 | `FactorEquityCurveChart` 整圖下架（同文案）；producer 不動；vitest + M4 |
| Gate 附帶 | phase26 §V；export session redirect；nodeid parser log 偽陽性 |
| 退修 | 僅動 `FactorReturnChart.tsx` + `FactorReturnChart.test.tsx`（本輪） |

## 產出檔

| 路徑 | 說明 |
|------|------|
| `frontend/src/lib/types.ts` | `FactorReturnData` = Ok \| Unavailable §U |
| `frontend/src/components/ic-analysis/FactorReturnChart.tsx` | 下架警示；**null/缺鍵亦 unavailable**（非 factor-return-empty） |
| `frontend/src/components/ic-analysis/FactorReturnChart.test.tsx` | shows_unavailable_notice / legacy_finite_payload_not_rendered / **missing_key_shows_unavailable_notice** / M3 |
| `frontend/src/components/ic-analysis/FactorEquityCurveChart.tsx` | 整圖下架 |
| `frontend/src/components/ic-analysis/FactorEquityCurveChart.test.tsx` | equity_* / M4 |
| `frontend/src/app/ic-analysis/page.tsx` | 兩圖 loading/error 接線 |
| `tests/phase26/...` / `tests/api/...` / `scripts/ic1cfr_stopgap_freeze.py` | 既有 Gate enabler（本退修未再動） |

## 退修變更（codex BLOCKING #1）

- **根因**：`FactorReturnChart` `data==null` 分支渲染 `factor-return-empty`「暫無 Factor Return 資料」；測試 `loading / error / empty 三態齊` 固化此錯。
- **修法**：null 分支改 `factor-return-unavailable` + `FACTOR_RETURN_UNAVAILABLE_NOTICE`（對齊 Equity 缺鍵）。
- **測試**：新增具名 `missing_key_shows_unavailable_notice`；拆 loading/error；禁 `factor-return-empty` 回落。

## §B B2 Gate stdout（退修後重跑）

### G1 vitest
```
$ npm --prefix frontend run test -- src/components/ic-analysis/FactorReturnChart.test.tsx src/components/ic-analysis/FactorEquityCurveChart.test.tsx src/components/ic-analysis/NetICChart.test.tsx

 Test Files  3 passed (3)
      Tests  21 passed (21)
   Duration  1.64s
```
exit 0（+1 具名 missing_key 用例）

### G2 build
```
$ npm --prefix frontend run build
✓ Compiled successfully in 2000ms
✓ Generating static pages (20/20)
```
exit 0

## 標準收尾

```
ASSUMPTIONS_VERIFIED: FactorReturn 三態(union/legacy/null 缺鍵)皆渲染 factor-return-unavailable 與文案「錯位序列已下架,待 1c-FR 重建」；Equity 缺鍵分支為參照；vitest 21/21；build exit0
TESTS_RUN: npm --prefix frontend run test -- FactorReturnChart/FactorEquityCurveChart/NetICChart → 3 files 21 passed exit0; npm --prefix frontend run build → exit0
FAILURES_SEEN: codex review 1 BLOCKING null→empty(fixed this rework); prior build unused-vars / check-nodeids enablers 已在初版 RESULT
SCOPE_CHANGES: 本退修僅 FactorReturnChart.tsx + FactorReturnChart.test.tsx + 本 RESULT；none 超界
NUMERIC_OR_SCHEMA_IMPACT: none（僅空態 UI 文案/testid 對齊；無數值路徑）
```

STATUS: DONE
