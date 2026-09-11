# Reconcile — 20260911-splitunify-b7-review-r1

**來源** 20260911-splitunify-b7-review-r1-codex.md, 20260911-splitunify-b7-review-r1-composer.md, 20260911-splitunify-b7-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**Verdict**：需修補後合併——唯一未閉合項（P1 群集）已於本輪修完；**本輪僅確認「過去讓委員寫不可進的意見已修好」，不代表 SPLITUNIFY 可收票**（依使用者 2026-09-11 之殘留規則，R-1／R-5／SU-RESID-1／2／3 仍須做完並各自經審與原提出方確認）。

本輪性質：**閉合確認**（原提出方重跑自己的反例），修補「本票每一個批次邊界都在至少一家寫『不可進』的情況下跨過、從未確認閉合」之流程違規（含 B2b R3 援引已廢止之「95% 就收」那次）。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **P1 事件批缺 `split_unify` 被顯示成「全域不適用」** | P2 | COMPOSER-R1-P2-02 | **採納，本輪修完**。composer 以提出者身分挑戰成功：B4 R1 之 N5 我宣稱已區分缺鍵情形，實際只分「全域 vs 舊報告」，**事件批的後端回歸會被顯示成「全域分析：不適用」**——把 bug 掩蓋成設計如此。這正是回溯稽核沒比到的形態（編號掛對、處置只做一半）。修：`splitUnifyView` 新增 `isEventRun`（判準＝`event_filter.label_source === 'event_label_value'`，與後端寫 `split_unify` 之 `is_event_label_consumed` 同條件），事件批缺揭露顯示琥珀「未揭露／後端未寫入」；vitest 新增一條；mutation `M-SU-B4-19`（退回「不適用」⇒ 紅）。 |
| **P2 codex 自身反對項全數閉合** | — | CODEX-R1-P3-00 | codex 逐條重跑自己在 B1、B2b R3、B2c、B3、B4 R2 寫「不可進」的每一條（含被主委漏掉的 `CODEX-R3-P3-04` 與 H6 附帶項），**全數閉合**。記錄在案。 |
| **P3 grok 自身反對項全數閉合** | — | GROK-R1-P3-00 | grok 逐條重跑 B2b R3、B2c、B4 R2 之反對項與 `GROK-R1-P2-02`（含主委「`time_bounds[0]` 已成等價 mutant」之判定），**全數閉合**。記錄在案。 |

### 仍開著、本輪不涵蓋的（避免把「閉合確認」誤讀成收票）

R-1（per-symbol 投影）、R-5（事件掃描端 universe）、SU-RESID-1（歸屬檢查閘）、SU-RESID-2（多 TF 複合鍵）、
SU-RESID-3（同源對證只比首尾）；以及已廢止之「95% 就收」曾被用來接受 D1 之範圍裁定，本輪未重審。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P3-00

**斷言**：本輪逐項核對後無 finding；11 項既有自有 finding 均已閉合：B1 P1-01/P1-02、B2 R3 P1-01/P1-02/P3-04、B3 P1-01/P1-02/P1-03、B4 P1-01、B6 P1-01、B2 H6 P2-04。
**碼證**：D-002 template rc=0；receipt 原始 FAILED=30、過濾 nodeid=19、baseline=19、untracked=0；derive 7 passed、wiring 1 passed；golden freeze `GOLDEN OK`、golden 4 passed；fingerprint 注入定位 index 0；移除外部副本 embargo 後 freeze rc=1 且 5 mismatches；disclosure scanner 2 passed；golden status 空。
**來源摘要**：`handoffs/20260911-SPLITUNIFY-CLOSURE-BRIEF.md#1905f4bc5af5`、`docs/SPLITUNIFY_SPEC.md#3e39458b00e4`、`docs/SPLITUNIFY_TODO.md#e44da6448b01`、`docs/GAP3_EVENT_UX_SPEC.D-002.md#9e122d83b91d`、object `539431fce93c`。

ASSUMPTIONS_VERIFIED: object HEAD=539431fce93cec46e7a8858732dd2c13322d89e4；reconcile-stamps check rc=0；外部突變只在 /tmp 副本；/tmp 工作目錄已清除且 `/tmp/claude-501` 保留。
TESTS_RUN: `bash scripts/template_check.sh dext docs/GAP3_EVENT_UX_SPEC.D-002.md` rc=0；receipt awk/comm rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'datetime_index_unsorted_is_fail_closed or duplicate_feature_index_timestamps_is_fail_closed or unsorted_row_index_is_fail_closed or manifest_summary_missing_key_is_named_not_bare_keyerror or tier_min_test_events_is_honored_not_silently_one or same_source_shifted_feature_index_is_fail_closed or same_source_plans_from_shorter_grid_is_fail_closed'` 7 passed/48 deselected；wiring 1 passed/8 deselected；golden freeze rc=0 `GOLDEN OK`；golden selectors 4 passed/5 deselected；disclosure selectors 2 passed/26 deselected；外部 boundary mutant freeze rc=1（預期，5 mismatches）。
FAILURES_SEEN: restore script rc=128（sandbox 禁止建立 `.git/index.lock`；後續 `git status --short -- tests/golden/` 為空）；外部突變反例按預期被擋下；無未解決測試失敗。
SCOPE_CHANGES: none；只新增本交接檔，未改 source、golden 或 root HANDOFF.md；既有 unrelated dirty files 保留。
NUMERIC_OR_SCHEMA_IMPACT: none；review-only，未改數值、schema、輸出大小或測試斷言。
OUTPUT_ARTIFACT: `handoffs/20260911-splitunify-b7-review-r1-codex.md`
STATUS: DONE
## COMPOSER-R1-P2-02

**斷言**: B5 必答 5 建議「事件路徑且 `ic_train_test_split.applied=true` 時缺 `split_unify` 應顯示琥珀警示」；B6 N5 決議宣稱已閉合，但 `splitUnifyView(undefined, { hasSplitMetadata: true })` 對**事件批後端漏寫**與**全域 run** 回傳同一 `notApplicable` 視圖，使用者會看到「全域分析：本次不是事件批」之錯誤解釋。

**碼證**: `frontend/src/lib/splitAuthority.ts:62-71` 僅二分（有無 `ic_train_test_split`）；`SplitUnifyBadge.tsx:23-24` 以 `ic_train_test_split !== undefined` 設 `hasSplitMetadata`；`splitAuthority.test.ts:75-81` 只測全域 case，**無**事件漏寫 case。RECHECK: `splitUnifyView(undefined, { hasSplitMetadata: true })` 與事件 bug payload 無法區分 ⇒ 兩者 JSON 相同（`notApplicable: true`, `countText: '不適用'`）。

**來源摘要**: frontend/src/lib/splitAuthority.ts#75126e925a7e

P2，信心度=High（邏輯）；Medium（生產路徑應永遠寫 `split_unify`）。不改不會復發 31 vs 33，但後端 regression 會被「不適用」掩蓋成使用者以為設計如此。修法：`SplitUnifyBadge` 再讀 `metadata.event_filter.enabled` 或 `execution_mode`，事件批缺 `split_unify` 時 `countText` 改琥珀「後端未揭露 canonical 驗證段數字」。

---

## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding——brief 列給 grok 的四條原反例於 `539431fc` 皆已閉合，且 `time_bounds[0]` 等價 mutant 判定成立。

**碼證**: 上表四列實跑；stdout 存 `/tmp/grok-b7-review-r1/{r3,g5,rename,p202}_out.txt`、`pytest_targeted.txt`（4 passed）、`msu30_mutant.txt`（rc=1）、`equiv_mutant.txt`（10 passed）；`git rev-parse HEAD`=`539431fc`。

**來源摘要**: handoffs/20260911-SPLITUNIFY-CLOSURE-BRIEF.md#1905f4bc5af5;handoffs/20260911-splitunify-b2-review-r3-grok.md#c3d36c2f8df7;handoffs/20260911-splitunify-b3-review-r1-grok.md#89c80e9d9cfb;handoffs/20260911-splitunify-b6-review-r1-grok.md#a418fa602b3c;handoffs/20260911-splitunify-b2-review-r1-grok.md#43ffe4bb5c8d

[MINOR] 信心度=High。sentinel only；非實質缺陷。

---

