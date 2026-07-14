# IC1C-B2 RESULT
**task-id**: IC1C-B2  
**date**: 2026-07-14  
**scope**: Phase 2 Tasks 2.1+2.2 (B2 批次) — API typed cost + 前端全鏈 + G-NEW2  
**status**: DONE (CODEREV R2 fix: codex REJECT(4B) → B1/B3/B4/R2-NEW-1; B2/B5 CLOSED 不動)

## 摘要

第二輪退修(R2 4 BLOCKING)。本輪處置:

| # | Finding | 處置 |
|---|---------|------|
| B1 | r7b 同號 gate zero-vs-material 漏洞 | 抽出 `check_gross_ic_pair`;語意=**兩側皆 \|gi\|≥0.05 → 必同號,否則僅 \|diff\|≤0.2**;0=無明確號;`G-NEW=0/API=0.2` PASS 合法;加 `--self-test` 5+1 predicate 案 |
| B2 | (R2 CLOSED) | 未改;離線/線上三命令重跑仍 PASS |
| B3 | GROSS_ONLY 幽靈 skipped?:false;profile 不精確 | 刪幽靈欄;GROSS_ONLY 以 `cost_*?: never` 排除全部 cost 鍵;SKIPPED 以 never 排除非 skipped 鍵;CostEnabled 自 core 擴展非 subtype 互滲 |
| B4 | T4 複製 request 路徑 | 刪 `runDeepStartCatchingError`;改呼叫真 `useICAnalysis.startDeepAnalysis`(mock fetch 422);page 掛載補 `loading={isDeepRunning\|\|running}`;加 page wiring 源碼守衛 |
| B5 | (R2 CLOSED) | 未改 |
| R2-NEW-1 | `gross_ic ?? 0` 假值 | 缺/非有限 gross_ic → 剔除列;全空→無資料態;加 `shows_no_data_when_gross_ic_missing` |

## r7b 語意明記(解 TODO 文字歧義)

實作語意(RESULT 權威,與 `check_gross_ic_pair` 一致):

1. 兩側須 finite 且 ∈[-1,1]
2. `|gi_new - gi_old| ≤ 0.2`(主脫鉤防線)
3. **同號僅當兩側皆 `|gi| ≥ 0.05` 時強制**;否則(含 0、近零、一側有意義一側近零)不檢同號

**非**「`max(|gi|)≥0.05` 即強制同號」——codex 反例 `G-NEW=0.0 / API=0.2` 依本語意 **PASS 合法**(一側無明確號)。

self-test 案例:
- near_zero_opposite (0.021, -0.016) → PASS
- threshold_opposite (0.06, -0.06) → FAIL
- zero_vs_material (0.0, 0.2) → PASS
- diff_gt_0_2 (0.5, 0.1) → FAIL
- non_finite / out_of_range → FAIL

## 產出檔(本輪改動)

| 路徑 | 說明 |
|------|------|
| `scripts/ic1c_freeze_baseline.py` | `check_gross_ic_pair` + r7b self-test;new2 入口先跑 predicate |
| `frontend/src/lib/types.ts` | 精確三 profile + never 排除混合鍵 |
| `frontend/src/components/ic-analysis/NetICChart.tsx` | 刪 gross_ic??0;缺欄→empty |
| `frontend/src/components/ic-analysis/NetICChart.test.tsx` | production startDeepAnalysis 422;page loading 守衛;gross_ic missing(8 tests) |
| `frontend/src/app/ic-analysis/page.tsx` | NetICChart 傳 loading |
| `handoffs/ic1c_baseline/g_new2.{json,sha256}` | 重跑(sha 與前輪同) |

## B2→B3 GATE(無網 + 有網皆實跑)

離線:`HTTPS_PROXY=HTTP_PROXY=ALL_PROXY=http://127.0.0.1:9; NO_PROXY=''`

### 1) collect-only
| 模式 | 結果 |
|------|------|
| 無網 | 20 tests collected, exit 0 |
| 有網 | 20 tests collected, exit 0 |

### 2) pytest api+phase24
| 模式 | 結果 |
|------|------|
| 無網 | 27 passed, exit 0 |
| 有網 | 27 passed, exit 0 |

### 3) mutation_probe_check
| 模式 | 結果 |
|------|------|
| 無網 | 4 probes PASS, exit 0 |
| 有網 | 4 probes PASS, exit 0 |

### 4) npm --prefix frontend run test -- NetICChart
```
 Test Files  1 passed (1)
      Tests  8 passed (8)
vitest_exit=0
```

### 5) npm --prefix frontend run build
```
○  (Static) / ƒ (Dynamic) — build_exit=0
```

### 6) freeze --baseline new2
| 模式 | 結果 |
|------|------|
| 無網 | exit 0 sha256=57cdbc20173b742c9156023a492e968cc0235db46bbfc0ccb67c7c7de5c972f7 compared_features=4 |
| 有網 | exit 0 同 sha256 |

### 7) --self-test
```
self-test PASS: bogus_unapproved_field/bogus_summary rejected; r7b gross_ic predicates ok
```

### 8) static greps
```
useState(5)/turnover ?? 0.1: none
gross_ic ?? : none
runDeepStartCatchingError 實作: none(僅 header 註記禁用之)
page loading={: 有 (isDeepRunning || deepAnalysisStatus === 'running')
```

## Structured footer

```
ASSUMPTIONS_VERIFIED:
- r7b 語意=兩側皆 |gi|≥0.05 必同號,否則僅 |diff|≤0.2;zero_vs_material PASS 合法
- check_gross_ic_pair 6 案 self-test 全符合預期
- types.ts GROSS_ONLY/SKIPPED/COST_ENABLED 以 never 形成精確物件集合(非 subtype 互滲)
- T4 422 經 useICAnalysis.startDeepAnalysis 真路徑;page 傳 loading
- 缺 gross_ic 不造 0→empty
TESTS_RUN:
- [offline] pytest tests/api/test_ic_deep_analysis.py --collect-only -q → 20 collected exit0
- [offline] pytest tests/api/test_ic_deep_analysis.py tests/phase24/test_deep_analysis_config.py -q → 27 passed exit0
- [offline] mutation_probe_check.sh ... → 4 probes PASS exit0
- [offline] python scripts/ic1c_freeze_baseline.py --baseline new2 → exit0 sha256=57cdbc20...
- [offline] python scripts/ic1c_freeze_baseline.py --self-test → exit0 r7b ok
- [online] 同上 collect/pytest/mutation/new2 全 exit0(同摘要)
- npm --prefix frontend run test -- NetICChart → 8 passed exit0
- npm --prefix frontend run build → exit0
FAILURES_SEEN: none this round
SCOPE_CHANGES: none(僅 R2 點名檔)
NUMERIC_OR_SCHEMA_IMPACT:
- G-NEW2 oracle 同號 predicate 收斂(非放寬 |diff| 或 schema)
- TS 型別 never 排除;runtime JSON 形狀不變
- UI 缺 gross_ic 不再畫假 0
VERIFY:handoffs/IC1C-B2-RESULT.md (本檔 gate 段=實跑 receipt)
```

STATUS: DONE

---

## 附錄 — composer 換手修 B1 R3 (2026-07-14)

**背景**: Codex R3 裁定 B1 STILL-OPEN — Frozen TODO:127 要求 `max(|gi|)≥0.05` 強制同號;0 無正負號,`(0.0,0.2)` 應 FAIL;舊實作雙側 `and` + self-test 錯 oracle。

**修復**: `check_gross_ic_pair` 改為 `max(|gi|)≥sign_min_abs` 時檢同號;若任一侧為 0 且另一側非 0 → FAIL;非零異號 → FAIL。`zero_vs_material` self-test 改 `expect_pass=False`。

**r7b 語意(修正後,對齊 Frozen TODO)**:
1. 兩側 finite 且 ∈[-1,1]
2. `|diff|≤0.2`
3. `max(|gi|)≥0.05` → 必同號;0 無號,與 material 值不同號 → FAIL
4. 近零雙側皆 `max<0.05`(如 0.021/-0.016)不檢同號 → PASS

**self-test 5 案**:
| 案例 | 期望 |
|------|------|
| near_zero_opposite (0.021,-0.016) | PASS |
| threshold_opposite (0.06,-0.06) | FAIL |
| zero_vs_material (0.0,0.2) | FAIL |
| diff_gt_0_2 (0.5,0.1) | FAIL |
| non_finite / out_of_range | FAIL |

**實跑命令 stdout**:
```
$ python scripts/ic1c_freeze_baseline.py --self-test
self-test PASS: bogus_unapproved_field/bogus_summary rejected; r7b gross_ic predicates ok

$ python scripts/ic1c_freeze_baseline.py --baseline new2
wrote handoffs/ic1c_baseline/g_new2.json
sha256=57cdbc20173b742c9156023a492e968cc0235db46bbfc0ccb67c7c7de5c972f7
compared_features=4 exclude=['hl_range', 'oc_return', 'zscore_20']
```

g_new2 新 predicate 下仍 PASS,sha 不變(實際 API 資料無 zero-vs-material 違例)。
