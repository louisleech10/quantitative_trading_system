# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任（Fable/Opus）；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-1 TODO 已生成（DRAFT），派三家 adversarial

**SPEC 定版**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（R8；七輪 adversarial 收斂＋使用者白話閘裁決收回三項殘留為 Task）。
**TODO DRAFT**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（`template_check todo` PASS；15 Task 四批；**尚未經三家 adversarial**）。

**接手順序**：
1. 派 TODO adversarial（brief 用 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`；review 派工模板見記憶
   `reference_committee_review_dispatch`：`--risk low --template "n/a: 用 brief"`，**勿**帶 `--spec/--adversarial waived`）。
   審查範圍**必須含**：① SPEC R8 三項收回之 delta（Task 2.4／3.4／4.3 欄位，未經委員審）② §N 殘留逐條攻「為何現在不做」（範本已加常設必答）。
2. 收斂（`reconcile_build.sh` 三來源）→ 修 TODO → 戳記 → Frozen → 開工 B1（Claude 自作，每批完成交三家 code review）。
3. 補 `review-r7` 戳記（body sha256 `ad4c5c535461`；一份一輪，brief 仿 `handoffs/20260817-gap1-stamp-v6-BRIEF.md`）。

## 現在的狀態

| 事實 | 怎麼查 |
|---|---|
| 待推筆數 | `git log --oneline origin/main..HEAD \| wc -l`（目前 4：R8／TODO／HANDOFF／白話同步；push 需使用者明示） |
| 戳記狀態 | 已 PASS：consult-r1／review-r1／r2／r4／r5／r6。**待補**：r7 |
| 待補完（不遺忘） | `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-1 待補完登記」G1-R1..R8（各附為何現在不做／觸發條件） |
| 殘留規則（範本層） | `templates/SPEC_TEMPLATE.md` §N ＋ `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §2 常設必答 |
| 既有紅（勿誤認新紅） | 產品套件 14 條（A/B 隔離證明）＋治理段5 4 條（f50f9d0f 舊契約遺留） |

## ⚠ 本 session 學到的操作紀律（完整清單在 CLAUDE.md Gotchas，本檔不重述）

- 🔴 **reconcile 須先三家 RECONCILE-STAMP 才能派下一輪**（漏跑會被 codex 依 `AGENTS.md` 12 條停工）；stamp brief 需 `stamp-target:` 且**單一目標**⇒ 一份一輪；戳記輪銷帳用 `debt_clear.sh --abandon --kind no-findings-expected`。
- 🔴 **委員債未清擋所有新派工**（含同 round 重試）：格式不合只能收集端機械修正（`**來源摘要**` `#` 後純 hex）或 abandon。
- 🔴 **gate 被擋時整個複合 Bash 都不執行**（含前段 `cat > brief`）⇒ 寫檔與派工分兩次呼叫；Write 工具也受 artifact gate＋債務重查擋。
- 🔴 reconcile lock 只鎖三家；主委自產版走非鎖來源。committee 三家 Verdict 分歧時**看碼證不數人頭、取較嚴版**（本 epic codex 六度比另兩家嚴且皆為真）。
- 🔴 `git add -f` 才能把新 handoffs 檔入版控；commit 觸及 docs/handoffs 須末段 `Governance-Scope: out-of-epic <理由>`。
- 🔴 委員 CLI 會 `resource_exhausted`（composer 實發生）⇒ 該輪 abandon（`collection-failed`）後重派。
