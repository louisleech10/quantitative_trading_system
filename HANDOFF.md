# Handoff

REF:handoffs/reconcile/20260809-govb1-b5-review-r2/synth.md
REF:handoffs/reconcile/20260809-govb1-x-review-r3/synth.md
REF:handoffs/reconcile/20260809-govb1-x-consult-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b4-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-09 | **Branch**: main | **閘**: `govb1_final_gate` **12/12 PASS**

## 🔴 接手第一件事：**B6**（B5 已收案）

`docs/GOVB1_INPUT_QUALITY_TODO.md` 之 Task 1.6；先照 CLAUDE.md 開工前稽核。
🔴 **實作端＝主委（Opus）自任**（使用者 2026-08-09 授權）；review＝codex+composer 兩家。
`roles.json` 仍寫 `implementer: grok`（**結構上表達不了編排端自任**，見 `票 B-49`）。
🔴 **換實作端前必讀**：`set_roles.sh` 會先算 quorum，grok 403 期間切 codex／composer **都會被拒**。

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
| — | **B6–B10** 未開工；**B4 階段 2** scope 錯配須另立票 | 依序 |
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
