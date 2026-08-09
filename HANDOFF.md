# Handoff

REF:handoffs/reconcile/20260809-govb1-x-review-r2/synth.md
REF:handoffs/reconcile/20260808-govb1-b4-review-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b4-consult-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-09 | **Branch**: main | **測試**: `pytest tests/governance` = **986 passed / 298s**

## 🔴 接手第一件事：**B5 impl**（brief 已備妥，可直接派）

`handoffs/20260809-govb1-b5-impl-r1-brief.md`（`brief_conformance_check` rc=0）。
派工前跑 `bash scripts/agent_preflight.sh`；實作端＝現行分工行（`docs/MULTI_AGENT_ORCHESTRATION.md` §1）。

## ✅ 本輪已收案（勿重做）

- **R-18/19/20** 全修完 ＋ review-r2（codex+composer）再抓 4 項亦全修完，**兩家戳記 APPROVED**。
  收斂檔＝上方第一條 `REF`。commit：`4cf27ca` `f3753ef` `f3bf4c3` `c54d27b`。
- **B4 階段 1** 收案（四輪 `4→5→3→0`）；**B5 偵察**完成並戳記。

## ▶ 兩個低摩擦機制（每週會用）

| 你要做的 | 怎麼做 |
|---|---|
| 暫停／調換委員 | 改 `scripts/governance_families.json` 的 `active_stampers` **一行**。空 list／打錯字／未進 `review_families` ⇒ **fail-closed 拒**（非靜默回退）。`gov_check` 每次 push 印暫停名單 |
| epic 中穿插修別的事 | commit 訊息加 `Governance-Scope: out-of-epic <理由>`。🔴 **須與 `Co-Authored-By:` 同一段、中間不得空行**（git 原生 trailer 只認最後一段）。硬保護仍禁：`docs/GOVB1_`／`govb1_scope.manifest`／`govb1_frozen_hashes.txt` |

## 🔴 待辦與具名殘留

| 代號 | 內容 | 何時解 |
|---|---|---|
| — | **B6–B10** 未開工；**B4 階段 2** scope 錯配須另立票 | 依序 |
| `R-15` | `scripts/governance_families.json` **不可 commit**（不在 manifest；它是設定非修復）⇒ 走 ambient M | epic 結束後 |
| `B-48` | `debt_clear --abandon --kind` **不查核事實**（曾以「零 findings」清掉有 5 findings 的輪） | 見 backlog |
| — | `review_quorum_check.sh:35` 硬編家族名單（既有漂移，非本批引入） | 併入名冊統一票 |
| — | B3 十檔 ambient M、`.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 皆**不得 commit** | — |

## ⚠ 踩過就別再踩

`grok` 額度用罄（403）⇒ `active_stampers=["codex","composer"]`，2/2 即滿足，**不是缺額殘留**。
session 名須 `<日期>-<epic>-<batch>-<kind>-r<N>`（batch＝`b<數字>` 或 `x`；四段就會被拒）。
上一輪債沒清 ⇒ 擋所有新派工；清帳走 `debt_clear --round-id --session`（附 reconcile），**逃生口 `--abandon` 只用於本質零 findings 的輪次**。
