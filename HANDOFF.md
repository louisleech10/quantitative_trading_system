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

## 🔴 接手第一件事：**站 2.7**（序 `036`；批次狀態一律見 `governance-batch-status` 生成區塊）

**不需新規格。** 兩件事：①第 1 批第一個批次之收斂檔缺 `RECONCILE-STAMP`（機檢對它是紅的）
②第 1 批第四個批次之 TODO 明列兩階段，其第二階段尚未動工。
先查該收斂檔位置與該 TODO 之階段欄位。

> 🔴 本節刻意不寫批次識別碼＋狀態值於同一行——**主委 2026-08-10 在此處被自己的偵測器擋下一次**
> （`HANDOFF.md:26` 與 `:29`），該檔在 `status_scope` 內。這是機制正常運作。

### ✅ 站 2.5／2.6 皆已交付並取得兩家戳記（2026-08-10）

| 站 | 票 | 收斂檔 | 審查量 | 🔴 未閉合 |
|---|---|---|---|---|
| 2.5 | `B-25` | `…/20260810-govb25-x-review-r6/synth.md` | 7 輪 33 條 | 八條殘留，含「判準資料化」整項未做 |
| 2.6 | `B-37` | `…/20260810-govb37-x-review-r5/synth.md` | 5 輪 18 條 | 六條殘留，含**票級統計**與**強制機制**兩項未交付 |

兩票**皆不得宣稱閉合**。殘留逐條見 backlog 對應節。

### ~~接手第一件事~~：站 2.6 的實作（**已完成，本節留作紀錄**）

SPEC **r3 定案**（`docs/GOVB37_FRICTION_TALLY_SPEC.md`）＋ TODO 已生成
（`docs/GOVB37_FRICTION_TALLY_TODO.md`，過範本閘）。審查 2 輪 9 條全數處置
（收斂檔 `handoffs/reconcile/20260810-govb37-x-review-r{1,2}/synth.md`）。
**批 D1 ＝ Task 1.1–1.3 單一 commit**；Gate 六項見 TODO §B。

🔴 **兩項未閉合**：
1. `CODEX-R2-P0-01`（quote-aware 配平）之關閉**待原提出方複驗** ⇒ 併入 TODO 審查輪必答第 1 條。
2. `票 B-37` 修法③「強制機制」**未交付**——原 Phase 2 已於 r1 被兩家實測判死
   （非豁免命中 10 行全為 FP；反引號豁免使最主要違規行不觸發 ⇒ **判準與目標互斥**）。
   **已證偽方向記於 SPEC §N 殘留 3，不得重試關鍵字黑名單。**

🔴 **地雷（實測）**：`gate_deny` **1385 筆全部無空格**，其餘 **3955 筆全部有空格**
⇒ 以 `"event": "` 掃描會漏掉整類攔截紀錄（約 26%）。`audit.log` 為 append-only，
三次重跑得 3950／3953／3955 ⇒ **任何計數必附快照座標**（`lines` ＋ `sha256[0:12]`）。

### ✅ 站 2.5 已收案（2026-08-10，兩家 `RECONCILE-STAMP APPROVED`）

收斂檔 `handoffs/reconcile/20260810-govb25-x-review-r6/synth.md`（body sha `d85d8ff9…5b49`，
`reconcile_stamps_check` rc=0）。7 輪 33 條全數處置。**八條具名殘留見 backlog `B-25` 節**——
其中「判準資料化」未做，故**不得宣稱 `票 B-25` 已完全閉合**。

## ~~接手第一件事~~：站 2.5 的 C2 批（**已完成，本節留作紀錄**）

規格＝`docs/GOVB25_STATUS_FACTKEY_SPEC.md`（r5 定案）＋`docs/GOVB25_STATUS_FACTKEY_TODO.md`。
五輪審查之處置見 `handoffs/reconcile/20260810-govb25-x-review-r{1..5}/synth.md`（12＋7＋4＋1＋3 條）。

C1（Task 1.1–1.4）**已交付**：多宿主＋projection oracle／`_schema` 四項封閉集合／兩個狀態 key／延伸檔＋三條集合相等斷言。
C2 ＝ **Task 2.1 偵測器 ＋ Task 2.2 拆除 37 行字面狀態**。
🔴 **兩者必須同一 commit**；只交 C1 判 **BLOCKED 非完成**（SPEC §R 末列）。
🔴 Task 2.1 未附誤擋率 receipt（Wilson ≤5% ＋非實作者複核）⇒ 判 BLOCKED。

### 🔴 C2 動工前必讀：偵測器與既有測試 sandbox 的衝突（主委 2026-08-10 推導，尚未實作）

SPEC Task 2.1 邊界 ⑥ 要求「`git ls-files` 不可用（非 git 樹）⇒ fail-closed」。
但既有測試（`test_govb1_factkey_gen.py` 的 `_sandbox` 系列，約 15 條）建立的 `tmp_path` root
**不是 git 樹** ⇒ 偵測器一掛上去，那些測試會**全部因非 git 樹而轉紅**，
且紅的原因與它們各自的標的（sort／locale／marker／target）**無關**。

**三個解，主委評估如下（未定案，C2 動工時先裁）**：
- (a) **在 root-creating helper 內 `git init -q`** ——保留 fail-closed 契約，最誠實；代價＝改多處 helper。**主委傾向此案。**
- (b) 讓 `status_scope` 可為空並跳過偵測 —— ❌ 與 Task 1.2「空陣列 fail-closed」直接衝突。
- (c) 只在 `GOVB1_FACTKEY_ROOT` 未設時啟用偵測 —— ❌ 靜默旁路，SPEC 明文禁止。

另須注意：`factkey_{clean,drifted}` 位於 repo 內，`git -C <root> ls-files` 可用，
其內容僅生成區塊 ⇒ 不會命中；drifted 的竄改在**區塊內**，亦不觸發偵測器。
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
