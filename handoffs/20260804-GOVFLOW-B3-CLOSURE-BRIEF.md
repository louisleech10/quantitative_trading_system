# B3 finding 閉合確認 — `CODEX-R10-P1-01`／`P1-02`／`P1-04`

brief-kind: review

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 執行，但**本輪極窄**：
只確認你 R10 的三條阻塞 finding 是否關閉。
🔴 **findings ID 用 `## CODEX-R12-P<0-3>-<NN>`**（`R1`–`R11` 已用於本 epic 前十一輪）。
🔴 **零 finding 時須產恰一條 `P3-00` sentinel，不得空手。**
⚠️ **已知限制**：`GOV-NOFINDINGS-SENTINEL` 指出現行 `completeness` **接受空殼 P3-00**
⇒ **請自律產出有實質內容的 sentinel。**
自驗：`bash scripts/completeness_check.sh --single <你的檔> --family codex`。

## 授權鏈

🔴 **授權 reconcile ＝ `handoffs/reconcile/20260803-govflow-todo-r2/synth.md`**
（三家 APPROVED，`reconcile_stamps_check` **rc=0**，body sha256 `37337418…`）。

⚠️ **切勿**查 `handoffs/reconcile/20260803-govflow-fix-r6/synth.md`——**永久無法戳記**，非授權來源。

## 為何只找你

B3 雙家族 review：**composer GO**；**你 NO-GO**，三條阻塞。
依「Finding 閉合再驗證」章程，**須由原提出方確認關閉**，故本輪只派你。

## 三條的處置

| 你的 finding | 處置 |
|---|---|
| `CODEX-R10-P1-01`（＋`COMPOSER-R10-P1-01` 同軸）：白名單雖只有 `_role_gate.sh` 一處定義，但**沒有測試證明兩端規則漂移時會轉紅** | 新增**行為層**測試：`test_t3_t3_task_id_inline_divergence_turns_red`（在 `committee_run.sh` 內嵌不同 regex ⇒ 轉紅）＋ `test_t3_t4_task_id_ssot_widen_both_ends_sync`（放寬 SSOT ⇒ 兩端同步變）＋ `test_mutation_task_id_inline_committee_turns_red` |
| `CODEX-R10-P1-02`：13 個 T3 節點**不足以證明**未知 family／完整 incompatibility list／canonical mutation 轉紅 | 補三項：`test_t3_u7_unknown_family_rejected_nonzero`／`test_t3_b3_two_incompatible_full_list`／`test_mutation_incompat_list_first_only_turns_red`／`test_mutation_canonical_role_gate_skip_turns_red` |
| `CODEX-R10-P1-04`：golden inventory 仍是 blocker sentinel，且該檔不在 B3 允許標的清單 | **主委驗收方法錯誤**：只看 `restore_golden_inventory.sh` 的 rc=0 就報「已還原」。**rc 只證明腳本跑過**，後續任何測試都會再弄髒。已改為以 `git status --short tests/golden/` 的**輸出**為準 |

## 主委實跑（請自行複驗，勿信宣稱）

```
pytest tests/governance/test_rolegate_predispatch.py -q     20 passed（修補前 13）
mutation_probe_check.sh                                     rc=0
collected 20 == Phase 3 測試表 20 列                         ✓
pytest tests/governance（全套）                              675 passed（B3 修補前 668）
git status --short tests/golden/                            空（改用狀態斷言，不看 restore 的 rc）
cx_run.sh 內 role_gate 引用 6 處                            角色閘未被搬走
task_id 白名單 regex 定義處                                 僅 scripts/_role_gate.sh（SSOT）
```

🔴 **主委獨立變異（隔離副本 `.claude/tmp/mutp8`，基準 20 passed）**：
在 `committee_run.sh` 內嵌一條**不同**的 regex（多允許 `#`）取代對 `_role_gate.sh` 的委派
⇒ **3 failed**，其中 `test_t3_t3_task_id_inline_divergence_turns_red`
與 `test_mutation_task_id_inline_committee_turns_red` **正是專門驗委派的兩條**。
⚠️ **修補前此變異完全不會被抓到**（舊測試只掃 regex 字面量，而字面量確實仍單一）。

## 必答（四項）

1. **`CODEX-R10-P1-01` 是否關閉**？請自行做**你設計的**漂移變異，確認轉紅。
   🔴 特別驗：**放寬 `_role_gate.sh` 白名單 ⇒ 兩端行為是否同步改變**
   （這才證明兩端讀同一份，而非各自實作後碰巧一致）。
2. **`CODEX-R10-P1-02` 是否關閉**？三項（未知 family／完整清單／canonical mutation）
   請各自變異驗證。
3. **`CODEX-R10-P1-04` 是否關閉**？請自行跑 `git status --short tests/golden/` 確認為空。
4. **B3 go/no-go**：可否標 DONE 並進 B4？

## 🔴 不受理範圍（硬邊界）

- **蓄意繞過軸不受理**（依使用者定死「95% 解法就收、殘留具名記錄不當阻塞」）。
- **本輪不受理新開戰線**：只審上述三條是否關閉。其餘觀察標 `P3-*` 或具名為新票交 B4。
- 重開 Task 3.1 設計（已定版並三家戳記）；B0／B1／B2 已 commit 範圍；B4 範圍
- 既有檔改動的合法性（`PHASE_MAP` 加 `,3`、`T0-B1` 探針改鎖）——composer 已於 R10 覆核
- 效能

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: composer 於 B3 review 判 GO → `handoffs/20260804-govflow-b3-review-composer.md`
fact-verified: 20 passed、collected 20 == 表 20、全套 675 passed → 主委實跑
fact-verified: `mutation_probe_check.sh` rc=0 → 主委實跑
fact-verified: 內嵌不同 regex ⇒ 3 failed 含兩條委派專屬測試 → 主委實跑（隔離副本）
fact-verified: `git status --short tests/golden/` 為空 → 主委實跑

assumed: **三條阻塞全部關閉。** ← **請各自變異複驗，勿信主委宣稱**
assumed: **新增的 7 條測試本身可證偽。** ← 請抽驗至少兩條
assumed: **B3 可標 DONE 並進 B4。** ← 本輪請給明確 go/no-go

## 產出

canonical 四欄 findings（若有）＋ **Verdict**（四項必答逐條回），
寫 `handoffs/20260804-govflow-b3-closure-codex.md`。
**禁改碼、禁改 SPEC／TODO。** 收尾清 /tmp workdir（保留 claude-501）。
