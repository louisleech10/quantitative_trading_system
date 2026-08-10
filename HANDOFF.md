# Handoff

REF:handoffs/reconcile/20260810-govb1-x-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b10-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b9-review-r1/synth.md
REF:handoffs/reconcile/20260810-govb1-b8-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。
站 2.5 的五份收斂檔（`handoffs/reconcile/20260810-govb25-x-review-r{1..5}/synth.md`）**尚未戳記**
（SPEC/TODO 審查輪；戳記於實作 code review 輪產生）⇒ **不得列入 `REF:`**，只在下方以純文字引用。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 施工順序 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 的 `governance-execution-order` block |
| **批次狀態** | 同檔 `governance-batch-status` block（**站 2.5 新增，機械產物**） |
| **票收案狀態＋對外不得宣稱** | 同檔 `governance-ticket-closure` block（**站 2.5 新增**） |
| 票的內容 | `handoffs/20260801-GOV-AMEND-BACKLOG.md`（53 張） |
| 給使用者的現況 | `白話說明/接下來要做什麼.md`／`白話說明/治理待辦總覽.md`（兩者現含生成區塊） |

🔴 **上述 block 一律不得手改**：改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`。

## 🔴 接手第一件事：**站 2.5 的 C2 批**（Phase 2，單一 commit）

規格＝`docs/GOVB25_STATUS_FACTKEY_SPEC.md`（r5 定案）＋`docs/GOVB25_STATUS_FACTKEY_TODO.md`。
五輪審查之處置見 `handoffs/reconcile/20260810-govb25-x-review-r{1..5}/synth.md`（12＋7＋4＋1＋3 條）。

C1（Task 1.1–1.4）**已交付**：多宿主＋projection oracle／`_schema` 四項封閉集合／兩個狀態 key／延伸檔＋三條集合相等斷言。
C2 ＝ **Task 2.1 偵測器 ＋ Task 2.2 拆除 37 行字面狀態**。
🔴 **兩者必須同一 commit**；只交 C1 判 **BLOCKED 非完成**（SPEC §R 末列）。
🔴 Task 2.1 未附誤擋率 receipt（Wilson ≤5% ＋非實作者複核）⇒ 判 BLOCKED。
🔴 C2 完成後仍須 **codex＋composer 兩家 code review ＋ RECONCILE-STAMP**，本票才算收案。

## 🔴 未修的活缺口

- `gate_check` 對真派工放行：process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c` ⇒ GOVB0 `B4`
- `票 B-15` 誤擋在 `B7` 之後仍存在（`printf`／`find`／`ls`／`gate.sh` 自身）⇒ GOVB0 `B4` Task 2.3/2.4
- `B3R` 的 **O(n) scanner 未交付**（`CODEX-R8-P1-03`）⇒ 不得宣稱達標
- `票 B-50` 流程面**永久標記為跳步**；形態①④ 未做
- `票 B-31` 對外**不得說「強制」**，只能說「產出端已有檢查點」（`票 B-53` 落地前）
- `plain_docs_sync_check.sh` 的 catch-all 回空字串 ⇒ **新增說明檔預設不受監看**
- 票號抽取器**內嵌於測試檔**（新增 `scripts/` 檔不在 manifest allow 會撞 G-7）⇒ 見 `docs/GOV_B25_SCOPE_AMENDMENT.md` §4
- `R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit

## ⚠ 操作紀律（踩過的坑，一律照做）

- 🔴 **`docs/` 下所有檔皆不在 manifest** ⇒ commit 須帶 `Governance-Scope: out-of-epic` trailer，收尾跑 `--only g7`。
- 🔴 **改一個事實前先 `grep -rn` 掃全部副本**。
- 🔴 **背景任務的 exit code ＝ 指令鏈最後一個指令的 rc**；推完用 `git rev-list --count origin/main..HEAD` 實查。
- 🔴 **改 `scripts/fact_keys.json` 須同步兩份 fixture**（clean/drifted；drifted 保留單列竄改，兩份行數須相同）。
- 🔴 **awk 無 regex 型別**：`f($0, /re/)` 會先求值成 `0`／`1` 再傳入，**不報錯**。樣式一律以字串傳入 `match()`。
- 🔴 **token 邊界不得切片後重判**：`s=substr(...)` 丟失左側前文 ⇒ `B3RB3R` 誤抽（`CODEX-R4-P1-01`）。用絕對位移。
- 🔴 **mutation 錨點須唯一**：新增含同字串之函式會讓 `replace(...,1)` 打錯位置，測試轉紅但原因是錨點失準。
- 🔴 **可構造出可重現反例者＝缺陷，不得寫成「上界」**；**自陳未測攻擊面時不得附自己的嚴重度判定**。
- 🔴 **兩家分歧看碼證不數人頭**；零 findings 屬「未觀察到」，不能推翻附探針的 findings。
- 🔴 **`$( )` 內禁用 `case`**（macOS bash 3.2）；`rc` 禁經 pipe；改檔一律用 Edit/Write，禁 `sed -i`／heredoc。
- 全套 `pytest tests/governance -q` **411 秒 / 1313 passed**（2026-08-10 實測）⇒ 丟背景，跑完 `bash scripts/restore_golden_inventory.sh`。
- 銷帳前確認 `sources.lock` 是 review 模式；session 命名 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，未分批用 `x`。
- `grok` 額度封鎖 ⇒ 委員＝codex＋composer（使用者 2026-08-10 確認）。
