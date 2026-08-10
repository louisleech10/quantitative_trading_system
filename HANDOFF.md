# Handoff

REF:handoffs/reconcile/20260810-govb1-b10-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b9-review-r1/synth.md
REF:handoffs/reconcile/20260810-govb1-b8-review-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b7-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## GOVB1 第 1 批（B1–B10）｜最終閘 12/12 PASS｜測試 1129 → **1283**

🔴 **不得寫「全數收案」**（2026-08-10 三處誇大已更正）：`b1-review-r6` 內容寫「批 1 收案」
但**無 `RECONCILE-STAMP`**；`b4-review-r4` 明寫「**階段 1 收案**」、階段 2 未開工。
各批次狀態**唯一來源**＝`docs/GOVERNANCE_EXECUTION_ORDER.md`，本檔與白話說明**只得 pointer**。

`bash scripts/govb1_final_gate.sh` → `g0_tests g0_syntax g1..g8 gate_b3 lifecycle_embed` 全 PASS。
本 session 收案：B7 `a5ddf05`／B8 `52c4a1a`+`b6a9da2`／B9 `39037f5`+`be9fda0`／
B10 `f674cb73`+`53d83dbf`(OOE)+`9e35f159`。四票皆兩家 `RECONCILE-STAMP APPROVED`。

## ✅ `票 B-50` **實作面收案**（四輪 9→3→1→0，兩家 APPROVED）｜🔴 **票仍 OPEN**

`reconcile_stamps_check.sh handoffs/reconcile/20260810-govb1-x-review-r2/synth.md` rc=0
（sha `8b285aee…9eec`）。偵測層 22 tests。

| 面向 | 狀態 |
|---|---|
| 形態②③／checker receipt／訊噪比 | ✅ 閉合（含含空白·中文·**含換行**路徑、**rename 裸路徑**不誤報） |
| **流程面** | 🔴 **永久標記為跳步**——**任何文件不得宣稱流程閉合**（`CODEX-R2-P1-01` 裁 (C)） |
| 形態① 逸出允許清單 | 🔴 未做（需 `票 B-51` 的 brief 允許清單欄位） |
| 形態④ 執行端 commit | 🔴 已入票、閉合條件已寫、**未實作** |
| porcelain v2 | 🔴 非本實作輸入；改用 v2 須重驗裸路徑判定 |

🔴 **戳記行由主委逐字轉錄**（兩家寫在自己產出檔未 append），`diff` 比對 IDENTICAL，
留痕在標的檔 `## 戳記` 區註解；provenance 以 `gate.sh register-output` 補記。

🔴 **本票換來的可援引判準**（stamp-r2 兩家核可）：
> **只有在固定 producer contract 與輸入字母表下機械不可達，才可稱「上界」；
> 任何可跑 harness 反例均屬缺陷。**

主委在本票內**兩次**把可重現的真缺陷寫成「宣告上界」，第二次被 hex 收據打回。

🔴 **接手前必讀** `20260810-govb1-x-review-r2/synth.md` C0–C4
（C0＝兩家分歧看碼證不數人頭的實例；C4＝自陳疑慮不得附帶自己的嚴重度判定）
與 `20260810-govb1-x-stamp-r2/synth.md` C2（裸路徑位置語意的窮盡性實跑）。

## 🔴 2026-08-10 事故：**執行端 commit 進版控**（形態④，本票原本沒有這一類）

r2 審查期間執行端對真實 repo 做三個 commit（`d63773a4`／`b8f5c4c2`／`7be8a11c`），
把探針 fixture 提交進版控 ⇒ `g7` 紅、4 條測試紅。已 `git reset --mixed`（未推、不動工作區），
污染檔 `mv` 至 `.claude/tmp/executor-pollution-20260810/`（**未刪，留供稽核**）。清理後 1281 passed。

🔴 **偵測器有作動、但主委沒讀到**——輸出在 `committee_run` 日誌尾端，是測試轉紅才回頭查。
⇒ **偵測到 ≠ 被讀到**。閉合條件已補（形態④ 比對 `HEAD`；②③④ 須進**最終摘要行**）。

## 🔴 六張殘留票**無批次歸屬 ⇒ 需要一次裁定**

`B-48`／`B-49`／`B-50`／`B-51`／`B-52`／`B-53` 全文在
`handoffs/20260801-GOV-AMEND-BACKLOG.md`（**本檔只放 pointer**）。
六張在 `docs/GOVERNANCE_EXECUTION_ORDER.md` 的 generated block **零命中 ⇒ 不會被排到**。
🔴 主委**停碼未自行排入**：排序＝改 `scripts/fact_keys.json` 並重生成，而使用者 2026-08-09
定案「**不得再開執行順序討論**」、該檔 `LAST-RULED` 亦為使用者 ⇒ 依 `票 B-51` 須先取得裁決。

**順序唯一來源**＝該檔；下一站 **站 3 `B-26`**（編號登記，仍 ⬜）→ 站 4 `B3R` → 站 5 第 0 批 `B4`–`B7`。

## 🔴 未修的活缺口

`gate_check` 對下列**真派工**放行：process substitution／`xargs -n 1`／`env FOO=bar`／
動態賦值／絕對路徑 `bash -c` ⇒ 歸 **GOVB0 B4**。`CODEX-R8-P1-03`：B3R 的 O(n) scanner 未交付。
`R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M。
`.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit。
`docs/ROADMAP.md` 不在 manifest ⇒ 更新須走 OOE；本 session 未更新。

## ⚠ 踩過就別再踩

- 🔴 **修一條 finding ≠ 修一個類別**；**「委員當場驗過」≠「以後改壞會被抓」**（臨時探針須落成常駐測試）。
- 🔴 **自陳未測的攻擊面時，不得附帶自己的嚴重度判定**——會誘導審查者放鬆（rename 那條實為假紅燈）。
- 🔴 **兩家分歧看碼證不數人頭**；不決則採較嚴版＋具名殘留。
- 🔴 **`cx_run.sh` 被 `_B45_HARNESS` 逐字錨定** ⇒ 新增加**錨點外側**，傳值走 bash **動態作用域**。
- 🔴 **同一檔第二次 OOE 改動極易漏 `Governance-Scope:` trailer** ⇒ 收尾必跑 `--only g7`。
- 🔴 **`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc**——本 session 又犯一次。
- 🔴 **`case` 的模式尾 `)` 在 `$( )` 內會被 macOS bash 3.2 當成收尾** ⇒ 整段語法錯、功能全死，
  而讀原始碼的斷言會是綠的。**只有真的跑一次才抓得到。**
- 🔴 `git status --porcelain -z` 解析：**先** `tr '\n' '\001'` **再** `tr '\0' '\n'`；
  rename 第二筆是**裸路徑**，不可一律砍 3 字元。
- 🔴 銷帳前確認 `sources.lock` 是 **review 模式**（`--mode review --rebuild` 就地升級，
  該路徑在 `reconcile_build.sh:238` 即 exit，**不動 synth**）。
- 🔴 session 命名須 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`；未分批用 `x`。
- 🔴 **stamp／review brief 必須硬性要求 canonical heading ＋ sentinel body 非空**，否則銷帳鎖死。
- 收斂檔**被 REJECTED 者須修訂本體並重蓋新 hash**；`grok` 額度封鎖 ⇒ `active_stampers=["codex","composer"]`。
