# Reconcile — 20260911-verdictgate-b4-review-r2

**來源** 20260911-verdictgate-b4-review-r2-codex.md, 20260911-verdictgate-b4-review-r2-grok.md　|　**roster** codex,grok

## 群集 / 處置

**修訂標的**：scripts/_synth_attr.py

**Verdict**：需修補後合併——grok `proceed`（R1 兩條 CLOSED）；codex R1 三條 CLOSED、新開 1 P1。採納已修；派 codex 閉合 R3。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **O1 說明括號未驗閉合、括號後可藏第二箭號**——「N2 修後 parser 仍接受未閉合括號說明，且可把第二個」延後箭號藏在已開括號說明後 | P1 | CODEX-R2-P1-01 | 採納（說明須為完整成對（）可多組，且 tail 不得含延後箭號；新測試 `test_41_defer_explanation_must_be_closed_paren_without_second_arrow`＋mutation M27；M23 錨點同步） |
| **O2 grok sentinel**——「本輪逐項核對後無 finding；`GROK-R1-P1-01` 與 `GROK-R1-P2-01` 於修法 `bfb9a14d` 後皆閉合」 | P3 | GROK-R2-P3-00 | 採納（紀錄） |

### 本輪程序記錄
- 修後實跑（主委 2026-09-11）：`test_verdictgate_p4.py` 29 passed；hook 7；debt_clear 30；mutation UNCOVERED=0（16 條）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；`GROK-R1-P1-01` 與 `GROK-R1-P2-01` 於修法 `bfb9a14d` 後皆閉合。

**碼證**: 隔離 probe `/tmp/vg-b4-cl-r2/probe/run.sh`：R1 原 fail-open 五案（`延後→Task`／`延後→Task、9.9`／`延後→E`／`延後→4.1`／`延後→Task 4`）對含 `Task 4.1`＋`E-4` 之 TODO 皆 gate_rc=1；brief N2 清單 `不採納`／`延後→備忘`／`延後→Task`／`延後→Task、9.9`／`延後→E-4、E-9` 皆 rc=1，`延後→E-4（理由）` rc=0；好對照 `延後→Task 4.1`／`延後→E-4` rc=0。殘留縫三問皆擋：多箭號 `延後→E-4；延後→E-9` rc=1、`延後→Task 4.1.` rc=1、`延後→e-4` rc=1。N3：`venv/bin/python -m pytest` 六節點（wrappers_agree／wrappers_differ／shape_closed／single_target／token_whole／existence_whole）→ 6 passed rc=0；源碼已無 `check_ids(doc)==check_ids(doc)` 恆真；M26 錨點仍在 mutate-b4。`bash scripts/debt_ledger.sh --has-open` → rc=1。

**來源摘要**: handoffs/20260911-VERDICTGATE-B4-CLOSURE-R2-BRIEF.md#b572123c41cb; handoffs/reconcile/20260911-verdictgate-b4-review-r1/synth.md#2c462cbd155e; scripts/_synth_attr.py#04eb48088717; tests/governance/test_verdictgate_p4.py#3cb5e44b0f24; handoffs/20260911-verdictgate-mutate-b4.py#36b7855c3a70

### 必答 1：各條修後是否閉合

| 原 ID | 重跑 | 結果 |
|---|---|---|
| `GROK-R1-P1-01` | bare gate：`延後→Task`／`延後→Task、9.9`／`延後→E`／`延後→4.1`／`延後→Task 4` 皆 rc=1（④ 不合形狀）；`延後→Task 4.1`／`延後→E-4` rc=0 | **CLOSED** |
| `GROK-R1-P2-01` | 恆真自比已刪；`test_41_hook_and_gate_wrappers_agree_on_complete_fixture`＋`…_differ_only_on_draft_rows` 真呼叫兩支 bash、比 ①②⑤／草稿 ② 差；M26 把 hook 改跑 gate 模式；六節點 6 passed | **CLOSED** |

### 必答 2：N2 封閉文法是否還有縫

**brief 點名三縫皆已擋（非 fail-open）**：

| 構造 | gate_rc | 觀測 |
|---|---|---|
| 多個延後箭號 `延後→E-4；延後→E-9` | 1 | 第一箭號 rest 吞入後段 ⇒「只准單一目標」 |
| `Task N.N` 後接 `.`（`延後→Task 4.1.`） | 1 | tail=`.` 非 `（`/`(` 起 |
| 殘留 ID 含小寫（`延後→e-4`） | 1 | `DEFER_TARGET_RE` 要求 `[A-Z]…` |

**殘留觀察（不升 finding）**：brief 清單寫 `延後→E-4（理由`（未閉合括號）「須 rc=1」，實測 gate_rc=0——現行文法只要求說明**以** `（`/`(` **起**，不驗成對閉合；目標仍正確擷取為 `E-4` 並整詞存在性通過，**非** R1 子字串 fail-open 復發。另：處置欄若夾敘事字面 `延後→…`，會被當延後處置解析（主委寫 synth 曾擋一次）——接受主委立場：處置欄只放處置 token，描述放群集欄。

### 必答 3：可否收 B4？

**可（就本家兩條而言）。** P1 延後目標存在性 fail-open 已閉；P2 hook／閘一致性測試已改為可證偽雙包裝＋M26。本輪無新 P0／P1。未閉合括號說明與處置欄字面箭號屬契約語意／寫作紀律，不擋本家閉合確認。

ASSUMPTIONS_VERIFIED: R1 五案 fail-open 修後皆紅；N2 brief 反例（除未閉合括號一項與 brief 預期不符見上）符合；三殘留縫皆擋；N3 六節點綠且恆真已刪；synth sha256=2c462cbd…；debt `--has-open` rc=1。
TESTS_RUN: `/tmp/vg-b4-cl-r2/probe/run.sh`（gate 反例表）→ 見上；`venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py::test_41_hook_and_gate_wrappers_agree_on_complete_fixture ::test_41_hook_and_gate_wrappers_differ_only_on_draft_rows ::test_41_defer_target_shape_closed ::test_41_defer_single_target_only ::test_41_disposition_token_must_be_whole_word ::test_41_defer_existence_is_whole_word -q` → 6 passed rc=0；`bash scripts/debt_ledger.sh --has-open` → rc=1；completeness 見下。
FAILURES_SEEN: none
SCOPE_CHANGES: none（closure；未改碼）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b4-review-r2-grok.md
TMP_CLEANUP: 收尾清 `/tmp/vg-b4-cl-r2`；保留 `claude-501`
STATUS: DONE

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R1-P1-01,GROK-R1-P2-01
