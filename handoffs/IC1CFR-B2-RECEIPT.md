# IC1CFR-STOPGAP B2 驗收 receipt(2026-07-14)

Claude 獨立實跑:
```
npm --prefix frontend run test -- FactorReturnChart.test.tsx FactorEquityCurveChart.test.tsx NetICChart.test.tsx → 3 files / 21 passed
npm --prefix frontend run build → exit 0(tsc 過=types 真改 §U union)
```
codex 代驗(本機全套件逾時):`python scripts/ic1cfr_stopgap_freeze.py --check-nodeids` → exit 0,baseline=77/current=44/**new_failures=0**/resolved=33;33 條 resolved 送 `pytest --collect-only` → 33 collected rc=0,**證非刪測/改名/放寬斷言**(真修復 suite redirect 污染)。

Code review:composer APPROVED 0 BLOCKING(scope 三項裁為必要 enabler);codex 首輪 REJECT(1 BLOCKING:FactorReturnChart 缺鍵三態顯示通用空態而非下架警示,且測試固化該錯誤)→退修→codex R2 **APPROVED**(三態實渲染皆下架警示;舊行為 mutation 轉紅)。

測試意義:21 前端測試=兩圖三態(union 佔位/legacy 有限值/缺鍵)皆警示空態、零 fallback 數值;M3/M4 probe=恢復畫 legacy 即紅;types.ts 真改 discriminated union(tsc 強制)。
