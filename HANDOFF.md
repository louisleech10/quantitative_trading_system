# Handoff

REF:handoffs/reconcile/20260810-govb1-x-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b10-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b9-review-r1/synth.md
REF:handoffs/reconcile/20260810-govb1-b8-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 施工順序、各站狀態 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 的 **generated block**（敘述段是第二份副本，**已咬過一次**） |
| 票的內容與狀態 | `handoffs/20260801-GOV-AMEND-BACKLOG.md`（53 張） |
| 給使用者的現況 | `白話說明/接下來要做什麼.md` |

🔴 **不得在本檔或白話說明寫「第 N 批全數收案」這類狀態**——該句 2026-08-10 在四份檔各有一份副本，
逐份手改連漏三次，最後以 `grep -rn` 才找齊。**這正是 `站 2.5` 要治的病。**

## 🔴 接手第一件事：**站 2.5**（`票 B-25` scope 擴充：批次/票狀態入 fact-key）

`scripts/fact_keys.json` 現況**恰有一個 key**（執行順序），狀態事實**零涵蓋**。
生成器（`scripts/gen_fact_key_blocks.sh`）**已存在**，只需擴充 key 與宿主檔邊界標記。
逐條證據與閉合條件見 backlog 的 `B-25` 節「2026-08-10 scope 缺口」。

之後：`站 2.6`（`票 B-37` 唯讀最小版）→ `站 2.7`（`b1` 補戳記、`b4` 階段 2）→ 順序表其餘各站。

🔴 **`站 2.6` 動工前必先處理**：`gate_deny` 的 JSON 間距與其他事件不同
（`"event":"gate_deny"` 無空格）⇒ 以 `"event": "` 掃描會漏掉該類事件。細節與 receipt 見 `B-37` 票。

## 🔴 未修的活缺口

- `gate_check` 對真派工放行：process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c` ⇒ GOVB0 `B4`
- `票 B-15` 誤擋在 `B7` 之後仍存在（`printf`／`find`／`ls`／`gate.sh` 自身）⇒ GOVB0 `B4` Task 2.3/2.4
- `B3R` 的 **O(n) scanner 未交付**（`CODEX-R8-P1-03`）⇒ 不得宣稱達標
- `票 B-50` 流程面**永久標記為跳步**；形態①④ 未做
- `票 B-31` 對外**不得說「強制」**，只能說「產出端已有檢查點」（`票 B-53` 落地前）
- `plain_docs_sync_check.sh` 的 catch-all 回空字串 ⇒ **新增說明檔預設不受監看**（已具名於該檔）
- `R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit
- `docs/ROADMAP.md` 不在 manifest ⇒ 更新須走 OOE；本 session 未更新

## ⚠ 操作紀律（踩過的坑，一律照做）

- 🔴 **改一個事實前先 `grep -rn` 掃全部副本**，不要一份一份修。
- 🔴 **背景任務的 exit code ＝ 指令鏈最後一個指令的 rc**。推完一律用
  `git rev-list --count origin/main..HEAD` **實查**。同型：`cmd | tail; echo rc=$?`。
- 🔴 **改 `scripts/fact_keys.json` 須同步三份 generated block**：正式文件 ＋
  `tests/governance/fixtures/govb1/factkey_{clean,drifted}/`；drifted 須保留單列竄改。
- 🔴 **可構造出可重現反例者＝缺陷，不得寫成「上界」**（stamp-r2 兩家核可之判準）。
- 🔴 **自陳未測的攻擊面時不得附帶自己的嚴重度判定。**
- 🔴 **兩家分歧看碼證不數人頭**；不決則採較嚴版＋具名殘留。
- 🔴 **`cx_run.sh` 被 `_B45_HARNESS` 逐字錨定** ⇒ 新增加**錨點外側**，傳值走 bash **動態作用域**。
- 🔴 **OOE 改動易漏 `Governance-Scope:` trailer** ⇒ 收尾必跑 `--only g7`。
- 🔴 **`$( )` 內禁用 `case`**（macOS bash 3.2 對模式尾 `)` 的解析）⇒ 改 `grep -E` 前置過濾。
- 🔴 **`git status --porcelain -z` 解析**：先 `tr '\n' '\001'` 再 `tr '\0' '\n'`；
  rename 第二筆是裸路徑，須依**位置語意**判定，禁用正則猜形狀。
- 銷帳前確認 `sources.lock` 是 **review 模式**；session 命名 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，未分批用 `x`。
- stamp 輪**交件不驗格式、收集才驗** ⇒ 有 findings 的 stamp 輪會在收集節點被擋（`票 B-52`）。
- `grok` 額度封鎖 ⇒ `active_stampers=["codex","composer"]`。
