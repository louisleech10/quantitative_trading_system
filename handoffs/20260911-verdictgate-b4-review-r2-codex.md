# VERDICTGATE B4 閉合確認 R2 — codex
brief-kind: closure
task-id: 20260911-VERDICTGATE-B4-REVIEW-R2
findings-round: R2
RECONCILE-STAMP: codex APPROVED 2026-09-11 sha256:33fd761ec35a0c657869817fdc1862ac0e94aea0e3db28671037e8994acd12a5 task:20260911-VERDICTGATE-B4-REVIEW-R2

## CODEX-R2-P1-01

**斷言**: N2 修後 parser 仍接受未閉合括號說明，且可把第二個 `延後→` 藏在已開括號說明後；封閉文法與單一目標仍非 fail-closed。
**碼證**: `scripts/_synth_attr.py:97-108` 用 `([^|]*)` 貪婪讀到儲存格尾端，且只驗 `tail.startswith(("（","("))`，未驗閉合或禁止 tail 內第二箭頭；實跑 brief probes：`延後→E-4（理由` → rc=0（預期 1），`延後→E-4（理由）延後→E-9`（TODO 僅含 E-4）→ rc=0。
**來源摘要**: scripts/_synth_attr.py#04eb48088717; tests/governance/test_verdictgate_p4.py#3cb5e44b0f24; scripts/reconcile_cluster_attribution_check.sh#8f1b90735e2b
影響：畸形 defer 可通過；第二目標可逃過 TODO 存在性檢查。N1 與 N3 已閉合，N2 需補文法驗證後重審。

必答 1：N1 CLOSED；`printf '%s' '{"tool_input":{"file_path":"handoffs/reconcile/zz-b4-r2-x-review/synth.md"}}' | env -u GOVERNANCE_TEST_HARNESS SYNTH_ATTR_MODULE=/private/tmp/vg_b4_r2_no_module.py bash scripts/synth_attribution_hook.sh` → rc=2。N2 部分閉合但本 finding 未閉合：`不採納`/`延後→備忘`/`延後→Task`/`延後→Task、9.9`/`延後→E-4、E-9` 各 rc=1；未閉合 `延後→E-4（理由` rc=0；合法 `延後→E-4（理由）` rc=0。
必答 1（續）：N3 CLOSED；指定 wrapper/draft 等 6 targeted tests → `6 passed`, rc=0；tautology grep 無命中。mutation 15/15 為 brief 的 fact-verified 前提，本輪未重跑（會修改 tracked 檔）。
必答 2：一般多箭頭 `延後→E-4；延後→E-9`、`Task 4.1.`、小寫 `e-4` 各 rc=1；但 `延後→E-4（理由）延後→E-9` rc=0，仍有縫。
必答 3：不可收 B4；blocked-by 本輪 `CODEX-R2-P1-01`。處置欄若混入說明文字與字面 `延後→` 而被擋，符合「第 4 欄只放處置、說明放群集欄」的 fail-closed 語意。

ASSUMPTIONS_VERIFIED: N1 固定正式模組；N2 shape/整詞/一般多箭頭/句點/小寫邊界與未閉括號、括號後第二箭頭均已實跑；N3 wrapper tests 具真呼叫路徑。
TESTS_RUN: `PYTHONDONTWRITEBYTECODE=1 NUMBA_DISABLE_CACHING=1 venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py::test_41_hook_and_gate_wrappers_agree_on_complete_fixture tests/governance/test_verdictgate_p4.py::test_41_hook_and_gate_wrappers_differ_only_on_draft_rows tests/governance/test_verdictgate_p4.py::test_41_defer_target_shape_closed tests/governance/test_verdictgate_p4.py::test_41_defer_single_target_only tests/governance/test_verdictgate_p4.py::test_41_disposition_token_must_be_whole_word tests/governance/test_verdictgate_p4.py::test_41_defer_existence_is_whole_word -q --tb=line` → 6 passed rc=0；N2 gate probes與 N1 hook probe 如上；`bash scripts/completeness_check.sh --single handoffs/20260911-verdictgate-b4-review-r2-codex.md --family codex` → PASS rc=0（由 wrapper 執行）。
FAILURES_SEEN: 一次 macOS `sed -i` 探針語法錯誤 rc=2，改用 `sed -i ''` 後完成；直接 completeness 呼叫被 OPEN-debt 外層 gate 擋，wrapper 內同一命令 rc=0；trash 權限拒絕後以明確 `unlink` 完成清理。
SCOPE_CHANGES: 僅新增本交件檔與短暫隔離 fixture；未改 code、tracked 檔、data_cache、root HANDOFF；未跑 mutation。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b4-review-r2-codex.md。
TMP_CLEANUP: 已移除本輪 `/private/tmp/vg-b4-cl-r2` 與 `vg_b4_r2_*` 暫存（清理掃描無殘留）；`/private/tmp/claude-501` 保留。
STATUS: DONE

VERDICT: blocked
BLOCKED-BY: CODEX-R2-P1-01
CLOSED: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P2-03
