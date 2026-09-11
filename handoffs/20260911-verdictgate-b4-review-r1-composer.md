# VERDICTGATE B4（Task 4.1）code review R1 — COMPOSER

task-id: `20260911-VERDICTGATE-B4-REVIEW-R1`  
family: `composer`  
findings-round: `R1`  
審查對象: `scripts/_synth_attr.py`；`reconcile_cluster_attribution_check.sh`；`synth_attribution_hook.sh`；`debt_clear.sh::_run_attribution`；`reconcile_build.sh`；`tests/governance/test_verdictgate_p4.py`（21）；`test_synth_attribution_hook.py`（7）；`test_debt_clear.py`（+2）；`handoffs/20260911-verdictgate-mutate-b4.py`（9）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| `pytest test_verdictgate_p4.py` 21 passed | brief fact-verified | **本輪複驗 21 passed** |
| `test_synth_attribution_hook.py` 7 passed | brief fact-verified | **本輪複驗 7 passed**（另抽跑 debt_clear attribution 2 條） |
| mutation 9/9 UNCOVERED=0 | brief fact-verified | **本輪複驗 UNCOVERED=0** |
| 歷史 24 份 synth 逐份 rc=1 | brief fact-verified | **本輪複驗 24/24 rc=1**（11 VERDICTGATE＋13 SPLITUNIFY） |
| 修後 `延後→` 擷取無其他縫 | brief `assumed:` | **部分否證**：`延後→E-4、E-5` 只驗 `E-4`（見必答 5）；不升格 P0/P1 |
| `debt_ledger --has-open` rc=0 | brief fact-verified | **未重跑**（與 B4 審碼無直接關聯） |

---

## 必答 1：SPEC ASSERT ↔ test 對應

### Task 4.1（五條 ASSERT）

| SPEC ASSERT（摘要） | test |
|---|---|
| `id_in_table=absent` ⇒ rc≠0 | `test_41_id_in_table_absent_rc_nonzero` |
| `quote20=mismatch` ⇒ rc≠0 | `test_41_quote20_mismatch_rc_nonzero` |
| `disposition=absent` ⇒ rc≠0 | `test_41_disposition_absent_rc_nonzero` |
| `disposition=延後` 且 target 不在 TODO ⇒ rc≠0 | `test_41_defer_target_missing_in_todo_rc_nonzero` |
| 全合規 ⇒ rc=0 | `test_41_all_good_rc_zero` |

**缺者**：無（五條一一對應）。

### 邊界 ①②③

| 邊界 | test |
|---|---|
| ① 斷言 <20 字 ⇒ 引用全文 | `test_41_short_assertion_quotes_full_text` |
| ② 同一 finding 兩列引用 ⇒ 任一合規即可；空白容忍／標點不容忍 | `test_41_two_rows_any_one_compliant_ok`；`test_41_nfc_and_whitespace_tolerant_but_not_punctuation` |
| ③ `延後→Task 9.9` 而 TODO 無此字串 ⇒ rc=1 | `test_41_defer_target_with_space_is_whole_token`（含 M15c mutation 錨） |

### 票內延伸（非 SPEC 五條 ASSERT，已覆蓋實作要點）

| 要點 | test |
|---|---|
| hook 子集 vs gate 全量（草稿列／strict_defer） | `test_41_hook_draft_row_without_token_not_quote_checked_but_gate_is`；`test_41_check_disposition_two_modes`；`test_41_hook_defer_target_not_checked_gate_is` |
| `-x-` 層修訂標的 | `test_41_x_layer_target_required_b_layer_not` |
| 佔位列不算已完成 | `test_41_placeholder_row_ignored_for_quote_but_id_counts` |
| debt_clear 串接 | `test_clear_attribution_gate_blocks_bad_synth`；`test_clear_attribution_gate_defer_target_uses_epic_todo` |
| hook 模組缺失 fail-open | `test_41_hook_module_missing_fails_open_gate_does_not` |
| mutation M14–M20 | `handoffs/20260911-verdictgate-mutate-b4.py`（9/9 COVERED） |

---

## 必答 2：hook 與閘同一實作

**立場**：**是同一模組**（`scripts/_synth_attr.py`）；`test_41_hook_and_gate_agree_on_ids_target_quote` **部分恆真、部分有意義**。

| check | 測試行為 | 評價 |
|---|---|---|
| `check_ids` | `sa.check_ids(doc) == sa.check_ids(doc)` | **恆真**（同函式同參數兩次） |
| `check_target` | 同上 | **恆真** |
| `check_quote20` | `completed_only=True` vs `False`，斷言兩者相等 | 只在 fixture **全部列皆已完成**（`row4` 含 disposition token）時有意義；與「hook／gate 共用模組、差別在 `completed_only`」一致 |
| `check_disposition` | **未在此測** | 由 `test_41_check_disposition_two_modes`／`test_41_hook_defer_target_not_checked_gate_is` 分測 |

**殼層**：`synth_attribution_hook.sh` 呼叫 `--mode hook`；`reconcile_cluster_attribution_check.sh` 呼叫 `--mode gate`（`run()` 分支 `scripts/_synth_attr.py:186-195`）。`test_41_hook_blocks_missing_id_and_passes_good`／`test_41_hook_completed_row_bad_quote_blocks` 驗 shell 端 rc。

**可證偽改法**（尚未寫成單測、但 M18 已 mutation 覆蓋 completed_only）：

1. fixture：一列 `row4=""`（草稿）＋一列 `row4="採納"` 但 quote 錯 ⇒ 斷言 `hook_q==[]` 且 `gate_q!=[]`（`test_41_hook_draft_row_without_token` 已覆蓋單列草稿；缺「混合列」單測）。
2. 對 `SYNTH_ATTR_MODULE` 指向 stub，分別跑 hook bash 與 gate bash，比對 stderr 逐字（integration 級）。

**收票影響**：不改不會讓 hook／gate 分叉——兩端皆 `exec python3 … _synth_attr.py`；風險是**未來改 hook 包裝漏傳旗標**，現有測試對 `check_ids` 恆真段防護弱。屬 **P2 測試債**，不阻 B4。

---

## 必答 3：「已完成列」判準與繞過縫

**立場**：**無實用繞過縫**；主委 CODEX-R10 Q4 立場（第 4 欄含 disposition token＝已完成）與實作一致。

| 階段 | 行為 |
|---|---|
| 寫入中（hook） | 第 4 欄空／無 token ⇒ `placeholder` 或 `_row_done=False` ⇒ **不驗 quote20**（`check_quote20` `completed_only=True` 跳過） |
| 清債（gate／debt_clear） | **全量** `check_disposition`＋`check_quote20(completed_only=False)`；無 token ⇒ ③ 錯，拒銷 |

**「永遠不填 token、靠 debt_clear 前手動繞」**：**不可行**。唯一銷帳路徑 `debt_clear.sh` 在 `_run_completeness` 之後必跑 `_run_attribution`（`:584`）；無 disposition token 必 rc≠0（`test_clear_attribution_gate_blocks_bad_synth`）。中途存檔可不填 token，但**不能清債**。

**碼證**：`scripts/_synth_attr.py:114-117` `_row_done`；`debt_clear.sh:256-269` `_run_attribution`。

---

## 必答 4：ID 比對邊界（實跑）

**VERIFY**（`venv/bin/python`，`sys.modules['_synth_attr']` 預註冊後 `exec_module`）：

| 情境 | 結果 |
|---|---|
| `CODEX-R1-P1-01` in `CODEX-R1-P1-01` | **True**（預期 True） |
| `CODEX-R1-P1-01` in `CODEX-R1-P1-010` | **False**（預期 False）✓ |
| `CODEX-R1-P1-01` in `XCODEX-R1-P1-01` | **False**（預期 False）✓ |
| `CODEX-R1-P1-01` in `CODEX-R1-P1-01X` | **True**（預期 False）— `(?![0-9])` 不擋尾隨字母 |

**立場**：brief 點名的 **010／X- 前綴** 邊界正確；尾隨非數字（`01X`）可誤中，但 canonical ID 格式下實務極低。若表格源 ID 欄手誤多一字元，可能假陽性「已在表」。**P2 觀察**，不阻 B4（收票後新 synth 仍受 quote20／disposition 約束）。

**碼證**：`scripts/_synth_attr.py:70-71` `_id_in`。

---

## 必答 5：`延後→` 目標擷取（實跑）

**VERIFY**（`scratchpad/b4_q5_defer.sh`；TODO 僅含 `Task 4.1`／`E-4`）：

| 處置欄 | rc | 摘要 |
|---|---|---|
| `延後→Task 9.9` | **1** | ④ 目標不存在 ✓ |
| `延後→Task 4.1` | **0** | 通過 ✓ |
| `延後→Task4.1`（無空白） | **1** | ④ 不存在 ✓ |
| `延後→E-4` | **0** | 通過 ✓ |
| `延後→E-4、E-5` | **0** | 只擷取 `E-4`（regex 遇 `、` 止）⇒ **E-5 未驗** |
| `採納、延後→Task 9.9` | **1** | 仍抓到 defer 子串 ✓ |
| `延後→Task 4.1（備註）` | **1** | 擷取含 `（備註` ⇒ 不在 TODO ✓ |

**立場**：主委修的空白截斷 bug（M15c）**已關**；`Task 9.9` 反例 **rc=1 如預期**。

**殘留（P2，不阻收 B4）**：

- 目標含 **`、`**：僅驗第一段；規格語意為單一目標 token，實務應寫 `延後→E-5` 而非 `延後→E-4、E-5`。
- **多個 `延後→`** 同格：未單測；`finditer` 理論上會逐個驗。
- 全形括號：尾 `）` 在排除集、首 `（` 不在 ⇒ `（備註）` 會拉進目標字串（上表已 fail-closed）。

**使用者裁定對齊**：屬有限窮舉邊界；不值得為 `、` 組合再開一輪。

---

## 必答 6：歷史 synth 實跑＋已清債不再跑閘

**VERIFY**（`bash scripts/reconcile_cluster_attribution_check.sh <synth> --todo docs/<EPIC>_TODO.md`）：

- VERDICTGATE 11 份：`x-review-r2..r8`（7）＋`b1-review-r{1,2}`＋`b2-review-r{1,2}` ⇒ **11/11 rc=1**
- SPLITUNIFY 13 份：`b1..b7-review-r1`（7）＋`x-review-r1..r4`（4）＋`b2-review-r2,r3`（2）⇒ **13/13 rc=1**
- **合計 24/24 rc=1**（② quote20 為主，符合 brief）

**已清債 round 不會再跑閘（碼證）**：

1. `reconcile_cluster_attribution_check.sh:10-11` 明寫歷史 synth「不回改、**不再跑**」。
2. `_run_attribution` **僅**在 `debt_clear.sh` 清債主路徑 `:584` 呼叫；已 `committee_debt_clear` 之 round 走冪等 no-op（`test_clear_idempotent_noop`），**不會重入** attribution。
3. `reconcile_build.sh` 建檔後 `--report` 為提示、**rc 丟棄**（brief／TODO 要點 4），不擋歷史。

**收票影響**：歷史紅 **不影響** 現行閘；僅影響未來新 round 之 `debt_clear`。

---

## 必答 7：`debt_clear --todo` 推導

**立場**：**可接受**；缺檔不傳 `--todo` ＋ 有 `延後→` ⇒ fail-closed，符合 SPEC。

**碼證**：`debt_clear.sh:260-265`

```bash
epic="$(printf '%s' "${SESSION}" | awk -F- '{print toupper($2)}')"
[ -n "${epic}" ] && [ -f "docs/${epic}_TODO.md" ] && todo_arg="docs/${epic}_TODO.md"
```

| 反例 | 行為 |
|---|---|
| `20260911-verdictgate-b4-review-r1` | `VERDICTGATE` ⇒ `docs/VERDICTGATE_TODO.md` ✓ |
| session 第二段非 epic／缺檔 | 不傳 `--todo`；有延後 ⇒ ④「未提供 --todo」或目標無法驗 ⇒ **拒銷** |
| `docs/P16_COMMITTEE_DEBT_TODO.md` 命名 | 不會自動命中（非 `<EPIC>_TODO.md` 模式）⇒ fail-closed |

**誠實邊界**：依賴 session 命名慣例（`<date>-<epic>-…`）；舊票若 TODO 檔名不符則延後目標全拒——**安全側**，非 fail-open。

---

## 必答 8：可否收 B4？

**可以（composer：proceed）。**

- SPEC Task 4.1 五條 ASSERT＋邊界 ①②③ **全有 test**；mutation **9/9**。
- hook／gate **同一模組**；debt_clear 串接與 epic TODO 推導 **fail-closed**。
- 歷史 24 份 synth 全紅 **符合 SPEC「不回改」**；不阻塞收票。
- 殘留：`check_ids` 恆真段測試弱、`01X` 尾隨字母、`延後→` 遇 `、` 只驗首段 — **皆 P2**，且使用者已裁定不無限窮舉。

---

## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–8、SPEC Task 4.1×5 ASSERT／邊界 ①②③、Q4/Q5/Q6 實跑與 p4／hook／debt_clear／mutation 測試後，composer 家族無 P0/P1 finding。

**碼證**: `venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q` → 21 passed；`venv/bin/python -m pytest tests/governance/test_synth_attribution_hook.py -q` → 7 passed；`venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py` → UNCOVERED=0；`bash scratchpad/b4_q5_defer.sh` → `延後→Task 9.9` rc=1；歷史 synth 掃描 24/24 rc=1；`_id_in` 實跑 010／X- 前綴正確。RECHECK: 重跑上述命令 + 必答 1 表。

**來源摘要**: scripts/_synth_attr.py#8ef20ed5ab7c;scripts/reconcile_cluster_attribution_check.sh#8f1b90735e2b;scripts/synth_attribution_hook.sh#ad9c334c22dc;scripts/debt_clear.sh#47c5bdcc8d2d;tests/governance/test_verdictgate_p4.py#912b27393cfe;docs/VERDICTGATE_SPEC.md#d723f42d7194;docs/VERDICTGATE_TODO.md#012a38a2888f

[P3] 信心度=High。核對依據＝ASSERT↔test 表、hook/gate 讀碼、Q4 `_id_in` 實跑、Q5 defer 反例、Q6 24 份 gate 實跑 + debt_clear 呼叫點、mutation 全覆蓋；P2 殘留已列必答 4/5/8（不捏造 P0/P1）。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

---

ASSUMPTIONS_VERIFIED: p4 21/21；hook 7/7；debt_clear attribution 2/2；mutation UNCOVERED=0；Q4 `_id_in` 五案例；Q5 defer 七案例；Q6 歷史 24/24 rc=1；debt_clear 僅清債路徑呼叫 `_run_attribution`  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q` → 21 passed rc=0；`venv/bin/python -m pytest tests/governance/test_synth_attribution_hook.py -q` → 7 passed rc=0；`venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py` → UNCOVERED=0 rc=0；`bash scratchpad/b4_q5_defer.sh` → Task9.9 rc=1  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 review；新增 `scratchpad/b4_q5_defer.sh`、`scratchpad/b4_review_probe.sh` 為 VERIFY）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b4-review-r1-composer.md  
TMP_CLEANUP: 已清 `/tmp/tmp.*`；保留 `/tmp/claude-501`

STATUS: DONE
