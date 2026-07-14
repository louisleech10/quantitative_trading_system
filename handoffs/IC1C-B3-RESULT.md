# IC1C-B3 RESULT
**task-id**: IC1C-B3  
**date**: 2026-07-14  
**scope**: Phase 3 Task 3.1（B3 收尾）— UI 成本語意註記 + API 文件契約同步；**零 schema/payload 變更**  
**status**: DONE

## 摘要

| # | 交付 | 處置 |
|---|------|------|
| ① | NetICChart 繁中說明/tooltip | 常數 `NET_IC_COST_SEMANTICS_NOTE`；loading/error/empty/chart 四態皆顯示；chart Tooltip 內嵌同文；gross-only 亦正確 |
| ② | `docs/API_SPECIFICATION.md` Net IC | 新增 **§14.11 / §14.11.1**（typed `net_ic`、§U 三 profile、union、422、雙入口 reject、cost 語意）；版本 6.1 |
| ③ | 零 schema/payload | 未改 `momentum/`、`api/`、`types.ts`；G-NEW2 特徵 dict 與前版 byte 等值（僅 `git_head` 欄變） |

## 產出檔

| 路徑 | 說明 |
|------|------|
| `frontend/src/components/ic-analysis/NetICChart.tsx` | 說明文字 + tooltip；`NET_IC_COST_SEMANTICS` / `NET_IC_COST_SEMANTICS_NOTE` |
| `docs/API_SPECIFICATION.md` | §14.11 Deep Analysis + §14.11.1 Net IC 契約；changelog v6.1 |
| `handoffs/ic1c_baseline/g_new2.{json,sha256}` | new2 重跑（特徵等值；sha 因 `git_head` 變） |
| `handoffs/20260714-IC1C-B3.md` | 交接 |
| `handoffs/IC1C-B3-RESULT.md` | 本檔 |

## Phase 3 驗證（VERIFY）

### VERIFY: grep per_rebalance ≥1
```
$ grep -n "per_rebalance" frontend/src/components/ic-analysis/NetICChart.tsx
15: * ... cost_semantics=`per_rebalance_not_annualized`(含 per_rebalance ...
17:/** ... per_rebalance)。 */
18:export const NET_IC_COST_SEMANTICS = 'per_rebalance_not_annualized' as const;
count=3  (≥1 PASS)
```

### VERIFY: npm --prefix frontend run build
```
Next.js 15.3.4 build_exit=0
Compiled successfully; typecheck+lint OK（既有 hooks warning 非本票）
Route /ic-analysis 37.2 kB
```

### VERIFY: npm --prefix frontend run test -- NetICChart
```
Test Files  1 passed (1)
Tests  8 passed (8)
vitest_exit=0
```

### VERIFY: G-NEW2 byte 等值（零 schema）
```
$ python scripts/ic1c_freeze_baseline.py --baseline new2
wrote handoffs/ic1c_baseline/g_new2.json
sha256=6db9b13ee5028379b8f9d2ee5beb8894af6eec40164acdc1ac06d2a27674c418
compared_features=4 exclude=['hl_range', 'oc_return', 'zscore_20']
exit=0
```
- 與 B2 產物 diff：**僅** metadata `git_head`（`2133c77…`→`04ac6fb…`）；`result.features` / cost / union / summary **字節級不變**。
- `features_only_sha256=4f7fbcbc98bfe22f7bf51d1ab99d05b5b849cafae81bd9ef2bebb7a280df1ac8`（本輪重算）。
- 檔案 sha 變因 git_head 屬預期，**非** schema/payload 變更。

## §B「B3 完」Gate

### VERIFY: pytest IC1C 相關檔（權威綠）
```
$ venv/bin/pytest \
  tests/momentum/Analysis/test_net_ic_analyzer.py \
  tests/momentum/Analysis/test_net_ic_schema_profiles.py \
  tests/momentum/test_turnover_analyzer.py \
  tests/momentum/test_export_formats.py \
  tests/api/test_ic_deep_analysis.py \
  tests/phase24/test_deep_analysis_config.py -q
86 passed, 1 warning in 10.79s
RELATED_EXIT=0
```

### VERIFY: 全套 `tests/momentum/ tests/api/ tests/phase26/`
```
$ venv/bin/pytest tests/momentum/ tests/api/ tests/phase26/ -q --tb=no
= 44 failed, 1497 passed, 18 skipped, 5166 warnings, 32 errors in 770.91s (0:12:50) =
```
- **非本票**：repo 已知紅（HANDOFF 記 ~50 failed/171 errors）；本輪 44 failed / 32 errors。
- 全套中 `test_ic_deep_analysis.py` 20 ERROR 皆為 `RuntimeError: redirect already active; pytest must remain serial`（fixture 序競態/污染），**單獨重跑同檔 20/20 PASS**（見上 RELATED）。
- 其餘 failed 以 feature_factory batch/event-loop、worker_logging PermissionError 為主，與 Net IC UI/docs 無關。

### VERIFY: decoupling scanners
```
$ bash scripts/check_decoupling.sh
ALL RULES PASS — Ready to freeze
DECOUP_EXIT=0

$ ./scripts/check_decoupling_phase4.sh
[Phase4.6.2] PASSED（含 tests/momentum/Strategy 子集 135 passed）
DECOUP4_EXIT=0
```

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: Task 3.1 僅 UI 註記+docs；B2 Gate 已過；RECONCILE-STAMP 三家 APPROVED(body 936daabc)；G-NEW2 比對對象=G-NEW feature 鍵等值
TESTS_RUN: npm build exit0; vitest NetICChart 8/8; grep per_rebalance count=3; freeze --baseline new2 exit0; related pytest 86 passed; full suite 44f/32e(已知紅+serial redirect); check_decoupling.sh PASS; check_decoupling_phase4.sh PASS
FAILURES_SEEN: full-suite test_ic_deep_analysis redirect-already-active ERROR（單獨重跑全綠，非本票回歸）; g_new2 檔案 sha 因 git_head 變（特徵 payload 等值）
SCOPE_CHANGES: tests/conftest.py 全域 stub Binance ping=r7 離線鐵則 Gate enabler(字面越界,composer 裁核可+codex APPROVE;原「none」聲明依 composer NB-3 更正)
NUMERIC_OR_SCHEMA_IMPACT: none（零 schema/payload；G-NEW2 result.features byte 等值）
```

STATUS: DONE
