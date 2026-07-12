# P2DEBT-T2 P-1 polarity — Grok — 2026-07-11

- task-id: `p2debt-t2-p1-polarity`
- 角色：代跑（修=codex / 跑=grok）；除基線暫刪行並還原外，未改任何檔。
- 基線：`tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt`（23 nodeid）
- 反向手法：`cp` → 刪 `tests/api/test_ic_deep_analysis.py::test_full_analysis` → 跑 → `cp /tmp/baseline.bak` 還原
- 還原核對：`diff -u /tmp/baseline.bak tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt` → identical；nodeid count=23
- `tests/fixtures/` 其他 diff/?? 為票 2 既有 WIP（非本任務）；本任務對基線檔無殘留改動

## 1) 正向 `/tmp/t2-p1-v6-pos.log`

命令：`bash scripts/run_ic_persist_hermetic.sh --set V6 > /tmp/t2-p1-v6-pos.log 2>&1; echo RC=$? >> log`

關鍵行原文：
```
DIGEST_DIFF_EMPTY[V6]=1
NEW_RED[V6]:
(none)
V6_NO_NEW_RED=1
RC=0
```

判定：**PASS** — 期望 `V6_NO_NEW_RED=1` + `DIGEST_DIFF_EMPTY[V6]=1` + `RC=0` 全滿足。

## 2) 反向可證偽 `/tmp/t2-p1-v6-neg.log`

命令：同上 V6，暫缺基線一行 `tests/api/test_ic_deep_analysis.py::test_full_analysis`

關鍵行原文：
```
DIGEST_DIFF_EMPTY[V6]=1
NEW_RED[V6]:
tests/api/test_ic_deep_analysis.py::test_full_analysis
V6_NO_NEW_RED=0
RC=1
```

判定：**PASS** — 被刪 nodeid 出現在 `NEW_RED` 且 `RC=1`（可證偽）。

## 總判定

| 極性 | 期望 | 實測 | 結果 |
|------|------|------|------|
| 正 | NO_NEW_RED=1, DIGEST=1, RC=0 | 同左 | PASS |
| 反 | NEW_RED 含 test_full_analysis, RC=1 | 同左 | PASS |

**POLARITY: BOTH_PASS** — P-1 V6 gate 機械化可接 final5 / 雙審。

ASSUMPTIONS_VERIFIED: 正/反各完整 V6 一輪；刪 exact nodeid 行觸發 NEW_RED；還原後 bak 與 fixture 位元一致
TESTS_RUN: pos V6 ~78s RC=0 gate PASS；neg V6 ~78s RC=1 NEW_RED=test_full_analysis；diff bak==fixture
FAILURES_SEEN: none（兩極性皆符合期望）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
