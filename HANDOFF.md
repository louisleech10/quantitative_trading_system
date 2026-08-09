# Handoff

REF:handoffs/reconcile/20260809-govb1-b5-review-r2/synth.md
REF:handoffs/reconcile/20260809-govb1-x-review-r3/synth.md
REF:handoffs/reconcile/20260809-govb1-x-consult-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b4-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-09 | **Branch**: main | **閘**: `govb1_final_gate` **12/12 PASS**

## 🔴 接手第一件事：**B6 實作**（開工前稽核**已做完**，見下）

**B6 ＝ Task 2.1 ＋ Task 2.2**（票 `B-25` 事實單一來源）。
歸屬出處＝`scripts/govb1_task_tickets.tsv`（W′ 機械權威）第 `6` 批兩列。
規格＝`docs/GOVB1_INPUT_QUALITY_TODO.md:884-966`（**唯讀，禁改**）。

🔴 **實作端＝主委（Opus）自任**（使用者 2026-08-09 授權）；review＝codex+composer 兩家。
`roles.json` 仍寫 `implementer: grok`（**結構上表達不了編排端自任**，見 `票 B-49`）。
🔴 **換實作端前必讀**：`set_roles.sh` 會先算 quorum，grok 403 期間切 codex／composer **都會被拒**。

### 已完成之開工前稽核（實測，勿重查）

| 標的 | 現況 |
|---|---|
| `scripts/fact_keys.json` | **不存在** → Task 2.1 新建 |
| `scripts/gen_fact_key_blocks.sh` | **不存在** → Task 2.1 新建 |
| `tests/governance/test_govb1_factkey_{gen,hook}.py` | **皆不存在** → 各由 2.1／2.2 新建 |
| `docs/GOVERNANCE_EXECUTION_ORDER.md` | 存在（**只讀**；生成 block 之標的） |
| `tests/.../govb1/factkey_{clean,drifted}/` | 存在但**只有 `README.md`** |

🔴 **fixture 只有 README 不是前批漏做**——已讀其 README 確認：
「本目錄於 Task 0.1 建立為**存在性錨點**（T-0.1-F1）；**內容由 2.1 生成器契約定義**」。
⇒ **內容該由 B6 填**。此問題已查結，接手者不必再猜。

上列六項**全在 `govb1_scope.manifest` allow 內** ⇒ 一般 commit，不需 out-of-epic trailer。

### 🔴 Task 2.2 的地雷（TODO 已預告，主委實測確認）

現行 `gov_check.sh` 段號**分母不一致**（`grep -n 'gov_check\] [0-9]' scripts/gov_check.sh`）：

```
1/3  shell 語法        1b/3 治理文件格式（帶字母後綴）
2/3  守衛測試          3/3  mutation 探針      4/4  白話說明過期  ← 分母不同
```

TODO 定的規則：**分母＝該檔實際段數（現算）**、帶字母後綴者併入前一段、
🔴 **禁在字串中寫死分母**——目前這 10 處**全是寫死的**，那正是它會漂的原因。
**加 fact-key 段之前要先修這個**，否則只是多一個寫死的數字。

### 施工順序（建議）

1. **Task 2.1**：`fact_keys.json`（初始**只收 `governance-execution-order` 一項**）
   ＋ `gen_fact_key_blocks.sh`。決定性契約：`LC_ALL=C` 固定 collation、全程 LF、
   **無 BOM、無時間戳**；`--check` 逐 key 重生成並 diff。
   🔴 目標檔**缺邊界標記 ⇒ `cur` 空 ⇒ 必 rc≠0**（fail-closed，非靜默放行）。
   🔴 **不得實作「權威宣稱詞黑名單」**——已被使用者推翻（靠記憶＋禁止清單列不完）。
   填兩個 fixture 目錄；`T-2.1-D1` 連跑 3 次 sha 相同；`T-2.1-M1` 拿掉 `LC_ALL=C` ⇒ 決定性測試須轉紅。
2. **Task 2.2**：先統一段號（`n/5`，禁寫死），再加 `_gov_check_factkey()`；
   生成器不存在 ⇒ **fail-closed**。**禁改 `scripts/git_hooks/pre-push`**。
3. 全套 `bash scripts/govb1_final_gate.sh`（**約 340s，必丟背景**）→ commit
4. 兩家對抗審 → 收斂 → 兩家戳記 → 清帳 → push

🔴 **不得宣稱「single-source 已完成」**（TODO 明列）。具名殘留：
生成器不知道的新文件第三份副本擋不到；`git push --no-verify` 可繞。

## ✅ 本輪已收案（勿重做）

- **R-18/19/20** ＋ review-r2 之 4 項 ＋ consult-r1 裁決之 4 項落地 ＋ review-r3 之 6 項，
  **全數修完並取得兩家戳記**。commit：`4cf27ca` `f3753ef` `f3bf4c3` `c54d27b`
  `8300b70` `1bc47da` `56d7c2a` `bc2c191`。
- **裁決**（`consult-r1` 兩家 APPROVED）：窗守衛**不承認** out-of-epic ⇒
  `_B45_HARNESS` 五檔 epic 期間動不了。G-7 排除五檔≠可改（見 `govb1_final_gate.sh` 三道機制註解）。
- **B4 階段 1** 收案；**B5 全案收案**（`39f4812`→`87cee02`→`11ed06b`→`70bb18f`，
  兩家戳記 APPROVED、測試 28→52、閘 12/12）。
  🔴 B5 過程中 **codex 連退兩次**（`eval`→字元集合→白名單/PATH 三層才封閉）；
  主委已於收斂檔具名「連續兩次把未封閉修法標成 ACCEPT」＋斷路器聲明。

## ▶ 兩個低摩擦機制（每週會用）

| 你要做的 | 怎麼做 |
|---|---|
| 暫停／調換委員 | 改 `scripts/governance_families.json` 的 `active_stampers` **一行**。空 list／打錯字／未進 `review_families` ⇒ **fail-closed 拒**（非靜默回退）。`gov_check` 每次 push 印暫停名單 |
| 換**實作端** | `bash scripts/set_roles.sh <家族>`。🔴 切換前機器先算 `\|active_stampers − 新端\| ≥ 2`，**不足即拒**（grok 403 期間切 codex／composer 都會破雙家族審查）。逃生口須帶 `SET_ROLES_QUORUM_BREAK_REASON`，理由寫入 history |
| epic 中穿插修別的事 | commit 訊息加 `Governance-Scope: out-of-epic <理由>`。🔴 **須與 `Co-Authored-By:` 同一段、中間不得空行**（git 原生 trailer 只認最後一段）。硬保護仍禁：`docs/GOVB1_`／`govb1_scope.manifest`／`govb1_frozen_hashes.txt` |

## 🔴 待辦與具名殘留

| 代號 | 內容 | 何時解 |
|---|---|---|
| — | **B6 已稽核未實作**；**B7–B10** 未開工；**B4 階段 2** scope 錯配須另立票 | 依序 |
| `B-50` | 執行端**兩次**把工作區留在壞狀態（mutation 未還原／誤 checkout tracked 檔），**皆無機制通知** | 見 backlog |
| `R-15` | `scripts/governance_families.json` **不可 commit**（不在 manifest；它是設定非修復）⇒ 走 ambient M | epic 結束後 |
| `B-48` | `debt_clear --abandon --kind` **不查核事實**（曾以「零 findings」清掉有 5 findings 的輪） | 見 backlog |
| `B-49` | roles SoT 表達不了「編排端自任實作」＋ `test_stamp_taskid_inject.py:769` 靜默 skip（fail-open）。**修它須動 `_B45_HARNESS` ⇒ 凍結期間做不到** | 🔴 **有定時炸彈**：凍結一解除，`test_b45_unfreeze_requires_roles_sot_closure` 即紅 |
| — | 「pre-push pytest 非來源不可變保證」**無行為 oracle**（要證明須比對凍結基準＝B-49 解凍後） | 併 `B-49` |
| — | `review_quorum_check.sh:35` 硬編家族名單（既有漂移，非本批引入） | 併入名冊統一票 |
| — | B3 十檔 ambient M、`.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 皆**不得 commit** | — |

## ⚠ 踩過就別再踩

`grok` 額度用罄（403）⇒ `active_stampers=["codex","composer"]`，2/2 即滿足，**不是缺額殘留**。
session 名須 `<日期>-<epic>-<batch>-<kind>-r<N>`（batch＝`b<數字>` 或 `x`；四段就會被拒）。
上一輪債沒清 ⇒ 擋所有新派工；清帳走 `debt_clear --round-id --session`（附 reconcile），**逃生口 `--abandon` 只用於本質零 findings 的輪次**。
