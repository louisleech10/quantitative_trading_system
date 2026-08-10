# Handoff

REF:handoffs/reconcile/20260810-govb1-b10-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b9-review-r1/synth.md
REF:handoffs/reconcile/20260810-govb1-b8-review-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b7-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## ✅ GOVB1 第 1 批（B1–B10）**全數收案**；最終閘 12/12 PASS

`bash scripts/govb1_final_gate.sh` → `g0_tests g0_syntax g1..g8 gate_b3 lifecycle_embed` 全 PASS。
測試 1129 → **1261**。本 session 收案：B7 `a5ddf05`／B8 `52c4a1a`+`b6a9da2`／B9 `39037f5`+`be9fda0`／
B10 `f674cb73`+`53d83dbf`(OOE)+`9e35f159`。四票皆兩家 `RECONCILE-STAMP APPROVED`。

## 🔴 接手第一件事：**六張殘留票沒有批次歸屬 ⇒ 需要一次裁定**

`B-48`／`B-49`／`B-50`／`B-51`／`B-52`／`B-53` 全文已登記在
`handoffs/20260801-GOV-AMEND-BACKLOG.md`（**本檔只放 pointer，內容不得複製**）。
但六張在 `docs/GOVERNANCE_EXECUTION_ORDER.md` 的 generated block **零命中 ⇒ 沒有批次＝不會被排到**，
正是該檔「出生事故」記載的失效模式。

🔴 **主委已停碼未自行排入**：排序＝改 `scripts/fact_keys.json` 並重生成該 block，
而使用者 2026-08-09 定案「**不得再開執行順序討論**」、該檔 `LAST-RULED` 亦為使用者
⇒ 依 `票 B-51` 判準須先取得裁決。主委建議見 backlog 末節。

**順序唯一來源**＝`docs/GOVERNANCE_EXECUTION_ORDER.md`；下一站是 **站 3 `B-26`**（編號登記，
狀態仍 ⬜「登記表本體已建」）→ 站 4 `B3R` → 站 5 第 0 批 `B4`–`B7`。

## 🔴 未修的活缺口（不是待辦，是現在就成立的洞）

`gate_check` 對下列**真派工**放行（三版對照確認非本次引入）：
process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c`
⇒ 歸 **GOVB0 B4**（`Task 2.3`／`2.4`）。`CODEX-R8-P1-03`：B3R 的 **O(n) scanner 未交付**。
`R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M。
`.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit。
`docs/ROADMAP.md` 不在 manifest ⇒ 更新須走 OOE；本 session 未更新。

## ⚠ 踩過就別再踩

- 🔴 **修一條 finding ≠ 修一個類別**。r1 判我「源碼斷言冒充端到端」，我修好那一格，
  同一批新增裡又放兩條同型的（兩家都沒抓到，我自己發現）。收窄型修補**必回頭掃同型**。
- 🔴 **「委員當場驗過」≠「以後改壞會被抓」**：臨時探針必須落成常駐測試。
- 🔴 **`cx_run.sh` 被 `_B45_HARNESS` 逐字錨定**（函式本體、`bash "${_cc}" --single …`、呼叫點
  `_fmt_rc="$(...)"`）⇒ 新增一律加**錨點外側**，傳值走 bash **動態作用域**。
- 🔴 **同一檔第二次 OOE 改動極易漏 `Governance-Scope:` trailer** ⇒ 收尾必跑 `--only g7`。
- 🔴 **`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc**——本 session 又犯一次。
- 🔴 銷帳前確認 `sources.lock` 是 **review 模式**（`--mode review --rebuild` 就地升級；
  該路徑在 `reconcile_build.sh:238` 即 exit，**不動 synth**——先讀過再跑，且先備份）。
- 🔴 **stamp／review brief 必須硬性要求 canonical heading ＋ sentinel body 非空**，否則銷帳鎖死。
- 🔴 **「現跑導出」的量測必須附輸入集合指紋**；`jq` 的 `//` 把 `false` 當空值；
  `grep` 互動 shell 是 ugrep、腳本是 BSD；**改檔一律用 Edit/Write**。
- 收斂檔**被 REJECTED 者須修訂本體並重蓋新 hash**；`grok` 額度封鎖 ⇒ `active_stampers=["codex","composer"]`。
