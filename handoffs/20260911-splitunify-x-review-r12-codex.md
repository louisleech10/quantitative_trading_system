# SPLITUNIFY D-001 閉合確認 R12（codex）
task-id: 20260911-SPLITUNIFY-X-REVIEW-R12 | family: codex | findings-round: R12
SCOPE: 只讀 closure；未改 code、SPEC、tracked 檔，未 commit/push，未跑 tests/governance 全套。

## CODEX-R12-P1-01
**斷言**: D-001 仍把全框 `row_index` 與 symbol-local `row_index_local` 混在同一契約：C1.4 的「以 feature_index 解釋 row_index」、oracle 的 `row_index`、per-symbol ASSERT 的 B `row_index` 與 local-only 規則互斥；`symbol_positions` 也未定義為時間序列。
**碼證**: `docs/SPLITUNIFY_SPEC.D-001.md:44,52,65-73,81,85,99-100` 對讀；D-001:20 宣稱 BASE C-4 其餘段落仍有效，而 `docs/SPLITUNIFY_SPEC.md:165,224-225,307` 仍寫 `feature_index[row_index]`；`momentum/core/contracts.py:504-519` 的 `symbol_positions` 實際是 frame 序。這使 b8 可同時被導向全框索引與 local 索引，交錯 symbol 的投影／oracle 會失去單一座標契約。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3f8c2c4590ff

## CODEX-R12-P2-02
**斷言**: D-001 所稱前置閘「`row_index_local` 為整數」若包含 dtype fail-closed，指定複用的 helper 並未實現該強度；且「逐位對應」未明定長度閘。
**碼證**: `momentum/core/split_preview.py:131-166`；`venv/bin/python -c` dtype/uint/length probe 觀測：integral float、bool、object 數字與數字字串皆 PASS 並轉成 `[0,1]`，fractional float、`uint64(2**63)`、object `2**100` REJECT；`np.array_equal` 對四種長度不等組合皆為 `False`。因此未見改變投影歸屬的長度繞過，但 dtype 語意仍未釘死。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3f8c2c4590ff

必答1: R11 W1/W2/W3 均閉合；`rg` 精確掃描 `_local_ordinals_for_symbol.*==|==.*_local_ordinals_for_symbol` → `NO_POSITIVE_HELPER_EQUALITY`，目前只剩「不採 helper」敘述與 M-SU-D1-15 反向 mutation；:69-71 已是時間序往返、前置閘、指紋與遞增合取。
必答2: 空 train 陣列由 helper 返回空 int 陣列，與 :83/:122 的合法 `sha256("[]")` 一致；空 test 在現行 derive :460-462 fail-closed。非整數值 float 會拒絕，但 integral float/bool/object 會靜默轉型；超大 unsigned/object 觀測均拒絕；長度不等以 `array_equal` 不相等，未找到成功放行。
必答3: fingerprint probe：原集合 `[0,2,4]`；重排 `[4,2,0]` 同 hash 但 strict guard=False；改集合 `[0,2,3]`、位移 `[1,3,4]` hash 均不同且 guard=True；五元素排列交集只剩原集合。故只改 local 不可能同時過兩閘；`object.__setattr__` 同時重綁 local 與 digest 是 R11 已接受的 Python frozen 逃生口，不列新 finding。
必答4: 全文掃描後唯一 P1 互斥是 P1-01 所列 :20/:44/:52/:65-73/:81/:85/:99-100 及 base C-4 舊索引語彙；P2-02 是 helper predicate 落差。其餘 R11 修法、空陣列語意、不可變性之序列化誠實邊界、SU-RESID-5 延後彼此一致；SU-RESID-5 不使本批投影 ASSERT 產生可證偽假綠。
必答5: 不可進實作；P1-01 未釐清時，b8 可能讓 producer 寫 local、oracle／projection 讀 global，交錯 symbol 造成錯分或錯誤 IndexError。
ASSUMPTIONS_VERIFIED: `HANDOFF.md`、`CLAUDE.md`、R12 brief、D-001、R11 synth、template 已讀；helper reference scan、時間序往返、dtype/unsigned/length 邊界、fingerprint∩strict-increasing 探針與全文逐句對讀均完成。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/core/test_split_contract.py` → 83 passed；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `3f8c2c4590ffcb4cf3bace21da25f9282c67276efb2b223c5a1efef59fbb48d3`；指定 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r12-codex.md --family codex` → PASS、rc=0；`bash scripts/restore_golden_inventory.sh` rc=128（`.git/index.lock` 不可建立，既有 inventory dirty 未改寫）。
FAILURES_SEEN: completeness 首次被 PreToolUse 的 OPEN debt dispatch gate 擋下，重跑指定原命令 PASS rc=0；restore golden inventory 受 sandbox 的 `.git` 寫入限制而失敗；未修改 tracked 檔，未跑 governance 全套。
SCOPE_CHANGES: 僅新增本交件檔；無越界、無 code/SPEC/TODO/data 變更、無 commit/push。 NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r12-codex.md；TMP_CLEANUP: `/tmp` 無 `*workdir*` 候選，保留 `/tmp/claude-501`。
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:3f8c2c4590ffcb4cf3bace21da25f9282c67276efb2b223c5a1efef59fbb48d3 task:20260911-SPLITUNIFY-X-REVIEW-R12
VERDICT: blocked
BLOCKED-BY: CODEX-R12-P1-01
CLOSED:
STATUS: DONE
