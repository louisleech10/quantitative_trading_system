# P2DEBT-T2-C5-V7RUN (grok 純代跑,主委迴避)

**Time**: 2026-07-12 | **Agent**: grok | **Task**: p2debt-t2-c5-v7run

## 1) data_cache 洩漏基線 (pre-run)

```
$ find data_cache -newer /tmp/dc-digest-pre.txt -type f 2>/dev/null
(empty)
BASELINE_COUNT=0
```

不含 lightgbm_bad_payload / ic_gatekeeper 報告。

## 2) 命令

```
bash scripts/run_ic_persist_hermetic.sh --set V7 > /tmp/t2-c5-v7.log 2>&1; echo RC=$? >> /tmp/t2-c5-v7.log
```

log: `/tmp/t2-c5-v7.log` (~80s wall, pytest 本體 ~20.48s)

## 3) 關鍵行原文 (from log)

```
================ 133 passed, 8 skipped, 281 warnings in 20.48s =================
DIGEST_DIFF_EMPTY[V7]=1
RC=0
```

## 4) 洩漏檢查 (post-run)

```
$ find data_cache -newer /tmp/dc-digest-pre.txt -type f 2>/dev/null
(empty)
LEAK_COUNT=0
```

特殊目標:
- `data_cache/models/lightgbm_bad_payload.pkl` — 不存在
- `data_cache/reports/*ic_gatekeeper*` — 不存在

無需 rm。**LEAK_STILL_PRESENT: no**

## 5) 判定

| 條件 | 實際 | OK? |
|------|------|-----|
| 133 passed | 133 passed, 8 skipped | yes |
| DIGEST_DIFF_EMPTY[V7]=1 | =1 | yes |
| RC=0 | 0 | yes |
| 無洩漏 | LEAK_COUNT=0 | yes |

**VERDICT: PASS**

## 6) 範圍

除本 handoff 外未改任何檔;未清洩漏(無洩漏)。

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: C-5 接縫修好後 V7 hermetic 全綠; redirect 守衛 DIGEST_DIFF_EMPTY[V7]=1; data_cache 無測試產物洩漏
TESTS_RUN: bash scripts/run_ic_persist_hermetic.sh --set V7 → 133 passed, 8 skipped, DIGEST_DIFF_EMPTY[V7]=1, RC=0
FAILURES_SEEN: none
SCOPE_CHANGES: none (純代跑;僅寫本 handoff)
NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE
