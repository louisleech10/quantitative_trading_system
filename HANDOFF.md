# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任（Fable/Opus）；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-1 卡在「白話審閱閘」等使用者裁定

偵察已完成並收斂（四方 31 findings、attribution/lock/debt 全 rc=0）；
**收斂結論＝`handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md`**（群集 C1–C5 ＋前提修正 ＋Verdict）。
主委自產版＝`handoffs/20260817-gap1-recon-claude.md`（非鎖來源，10 條 CLAUDE-R1-*）。

**等使用者答的那一件**：交付範圍。使用者 2026-08-17 session 中途提醒
「ML／Optuna／回測都是後續才要開發，可能只是殼」，主委實測複驗成立
（`data/optuna_*.db` 不存在、`results/optimization_results/` 不存在 ⇒ 策略優化路徑從未跑過），
故 synth 已加「前提修正」節把交付改為 **純統計核心＋typed 契約＋fail-closed**，
對未成熟骨架的接線改造降級為具名待接線項。**使用者未答前不得起草 SPEC。**

使用者答「照修正後範圍走」之後的順序：
SPEC 起草（Claude）→ 三家 adversarial → 複驗＋戳記 → 白話閘 → TODO 同流程 → 實作（Claude）。
分期＝`B1` 頻率/退化語意契約 → `B2` N ledger schema+讀取API → `B3` MinBTL+DSR 純統計 → `B4` PBO 純統計。

## 現在的狀態

| 事實 | 怎麼查 |
|---|---|
| 待推筆數 | `git log --oneline origin/main..HEAD \| wc -l` |
| 三項 BLOCKING 內容 | synth 的 C1／C2／C3 節（各附四方 finding ID） |
| 既有紅（勿誤認新紅） | 產品套件 14 條（A/B 隔離證明）＋治理段5 4 條（f50f9d0f 舊契約遺留） |
| 未清雜物 | `scripts/ichc_t2_diag.py`／`ichc_t3_diff.py`／`ichc_t2_probe400.py`、`handoffs/reconcile/*.stale-*`（rm 被沙箱擋，需手清）；未 commit 的 `scripts/governance_families.json`(active_stampers)＋未追蹤 `docs/GOVB0_FRICTION_AMENDMENTS.md`（被 ROADMAP_DETAIL 引用，該補 commit） |

## ⚠ 最常咬人的操作紀律（完整清單在 CLAUDE.md Gotchas，本檔不重述）

- 🔴 `git add` 逐檔列出；rc 直取禁 pipe；commit 訊息 `-F` 寫檔（`.claude/tmp/`）＋VERIFY receipt
- 🔴 改檔用 Edit/Write；`docs/API_SPECIFICATION.md` **實務不可編輯**（檔名撞 SPEC 格式快閘）
- 🔴 凡動 `scripts/` 的 commit，四份治理白話檔同 commit 更新（sync 守衛自指循環）
- 🔴 **reconcile lock 只能鎖 round participants（三家）**：4 來源會被 roster 相等性擋（本輪與上輪各踩一次，見 `*.stale-4src`）；主委自產版走非鎖來源＋synth 註記
- 🔴 委員債未清 ⇒ 擋**所有**新派工（含格式修補）：委員產出格式不合時只能收集端機械修正（`**來源摘要**` 是機器欄）或 abandon
