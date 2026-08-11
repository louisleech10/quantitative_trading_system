# Handoff

REF:handoffs/reconcile/20260810-govb1-b4-review-r3/synth.md
REF:handoffs/reconcile/20260810-govb1-b4-consult-r1/synth.md
<!-- 2026-08-11 之全部收斂檔（站 4 govb3r、站 5 govb0-b4、B-49 之 consult r1–r4 與 review r1–r3）
     **皆尚未取得委員戳記**，依下方規則一律不得列入 REF:。取得 RECONCILE-STAMP APPROVED 後再補。 -->

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Branch**: main | 實作＝主委自任（`implementer=claude`）；
討論／review／adversarial＝**codex+composer+grok 三家全員**（使用者 2026-08-11 定；
出處 `docs/GOV_ROLES_ORCHESTRATOR_AMENDMENT.md`）

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 施工順序／批次狀態／票收案狀態 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 之三個 generated block |
| 票的內容 | `handoffs/20260801-GOV-AMEND-BACKLOG.md` |
| 給使用者的現況 | `白話說明/接下來要做什麼.md`／`治理待辦總覽.md` |
| 摩擦統計現值 | `bash scripts/friction_tally.sh --by-event`／`--field-presence`（**數字不寫死**） |
| 委員名冊與角色 | `scripts/governance_roles.json`＋`scripts/governance_families.json`（**機器版為準**，散文版 ORCH §1） |
| `b4` 階段 2 之交付與殘留 | `docs/GOV_B4_STAGE2_AMENDMENT.md` |

🔴 **generated block 一律不得手改**：改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`。

---

# 🔴🔴🔴 使用者授權（2026-08-12，逐字，**接手第一件事**）

> 「我授權你跟委員看要解凍或如何做，把 B-49 做完，然後不要有殘留什麼卡到以後流程，
> 你們看要做什麼就一次做完，然後再繼續做完其餘任務，加速完成」

**授權範圍（明確擴權，不得縮讀）**：

1. **解凍方式由主委＋委員共識決定**——包含修改 `docs/GOVB1_INPUT_QUALITY_TODO.md` 的宣告集。
   先前「全程唯讀、禁改」之約束**就此解除**。
2. **一次做完，不留卡點**——須連同會卡到後續流程的殘留一起處理
   （至少：幽靈路徑之處置、`R-12`、G-7 長期紅）。
3. **做完 B-49 後直接續做其餘任務**，不必回頭問。

**授權**不**涵蓋（仍受既有鐵律約束）**：

- ❌ 不得跳過兩家非實作者 code review
- ❌ 不得用 `meta` 動詞之類**取巧手法**充當達標（使用者 2026-08-01 定死，與凍結無關）
- ❌ 不得改 F5／B5／G-7 之**判準本身**去讓自己過關
- ❌ 推送之前，測試與 code review 兩關都不得省略

**使用者在授權前提出、主委已更正的三點認知（勿沿用舊敘述）**：

| 主委原說法 | 更正後 |
|---|---|
| 「不可回退」是重大負債 | 只有「撤銷授權」不可回退，而那是永遠不會想做的事；實際成本＝改那三個檔時同批更新一個常數 |
| 「開先例」是主要風險 | **框架錯了**。F5 驗的是「兩份清單一致」不是「不可變」，而清單 A 本來就能經授權集合修改 ⇒ 照程序改**不削弱** F5。真正的風險是「沒程序地隨手改」 |
| 凍結不能改是規則 | **是設計缺陷**：凍結是 epic 期間的暫時裝置，卻**沒人寫到期日與出口** ⇒ 暫時變永久。B-49 的真正價值是**逼這個 repo 補上缺掉的出口** |

🔴 **殘留的真實顧慮（不因授權而消失）**：`_B5_FORBIDDEN_PREFIXES` 擋 `docs/GOVB1_` 的目的是
「epic 施工期間規格不得在腳下移動」，而該 epic **尚未整批收案**
（各批現況一律看 `docs/GOVERNANCE_EXECUTION_ORDER.md` 的批次狀態區塊，本檔不重述）。
⇒ **施工時必做的減輕辦法**：範圍鎖死在宣告清單，**技術內容 diff 必須為空**，機械驗證後給使用者看。

## 接手後的執行順序

**① 先隔離乾跑，再碰 repo。** 主委已**三次**「以為找到正解」後撞上結構性死結
（r3 range bootstrap → r6 兩段提交 → TODO 的 Task 0.2）。
⇒ 先在隔離副本把 `Task 0.2 → 1.1 → 1.2` 整條鏈走完並逐項核對結果，才動 repo 一個字。
隔離副本仍在 `<scratchpad>/b49iso`；其 `scripts/` 是 symlink，**擴大範圍前須改實體 copy**。

**② B-49 施工**：照 `docs/GOV_B49_PATH_GRANT_TODO.md`。`Task 0.2` 現在可以做了。
TODO 內已寫明**三條已證偽路徑**（不得重試）與**唯一自洽的機械解**：
把 `docs/GOVB1_INPUT_QUALITY_TODO.md` 納入 grant 第四條路徑 ＋ manifest allow ＋
**其自身宣告集**（自我宣告 ⇒ F5 兩側相等）。
🔴 `decl` 數字（40 或 41）**待實測，不得預先寫死**（`GROK-R1-P1-02`）。

**③ 不留卡點**：幽靈路徑用 `bash scripts/govb1_ghostpath_check.sh` 盤點
（三家原裁「逐案」，但**授權已改前提** ⇒ 須重新評估是否一次處理完）；
G-7 現行紅的唯一來源＝`tests/governance/test_cxrun_selfcheck_prompt.py`，B-49 落地時一併處理；
`R-12` 需 B-49 先落地。

**④ 續做其餘任務**：站 5 `B4` 剩餘（§B8 閉合複驗由**原提出方 codex** 重跑反例）
→ `B5`／`B6`／`B7` → 站 6 `B-26` → 站 7 治理殘留票。

---

## 🔴 現況（2026-08-11 深夜；**背景有一輪 review 在跑**）

## 🔴🔴 最新：commit 後全套由 4 紅變 **7 紅**——是我 commit 造成的，已定位

**背景任務 `bcwu7w2mb`** ＝ `20260812-govg7-x-consult-r1`，決這件事，**未回**。
（前一次 `b1wx84rak` 被命名規約 fail-closed 擋下：**task-id 須為 session 的大寫形式**，
我卻用了 brief 的名字。閘的行為正確——未發 token、未開債、未派工。）

`bash scripts/govb1_final_gate.sh --only g7` →
`G-7 FAIL: 未宣告即修改: tests/governance/test_cxrun_selfcheck_prompt.py`

🔴 **根因是 endpoint net-diff，而且它剛好活生生印證了我今晚寫進 §C-2 的那條**：

```
git diff --name-only <base_commit> e029514d -- tests/governance/test_cxrun_selfcheck_prompt.py  → 空
git diff --name-only <base_commit> HEAD     -- 同檔                                              → 有
```

該檔在 range 內被兩個 **in-epic** commit 動過（`f5834c40`／`00f52b99`，**皆無** trailer），
但到 `e029514d` 為止**淨差回到零** ⇒ G-7 的 endpoint diff 看不到它 ⇒ 一直綠。
我的 commit 使淨差非零 ⇒ 路徑現形 ⇒ 既不在 manifest allow、又非 path-only-OOE ⇒ 紅。

🔴 **我原本寫「這是既有 manifest 缺口被掀開」——那句話被 grok 推翻，是錯的。**
`00f52b99` 標題逐字含 `restore G-7 scope`：epic 當時是**刻意**把該檔留在 scope 外
並主動還原自身改動以維持 G-7 綠。**不是漏登記。**
⇒ 正確表述：我打破了 epic **刻意維持**的狀態，不是揭開疏漏。
⇒ 紅的充分條件三者同時成立：① endpoint 淨差非零 ② `path-only-OOE` 被 in-epic 歷史毒化 ③ 不在 allow。

## 🔴🔴 三家一致選的 A **實作後證明做不到**，已完整還原

三家 consult 一致選 A（加 manifest allow）。主委依 codex 指定順序實作：
① `_B5_MANIFEST_AUTHORIZED_ADDITIONS` 改兩元素 ② 加 manifest 一行
③ 重算 `scope_manifest:` 雜湊 ④ 連帶更新四處 `decl == 36` → `37`。
**`--only g7` 確實轉 PASS，7 紅降到 3 紅。**

🔴 **但撞上一道沒有人提到的牆**：

```
test_t01_f5_manifest_matches_task_decl
→ manifest 的 allow 集合必須**逐條等於** docs/GOVB1_INPUT_QUALITY_TODO.md
  「修改檔案」節所列的路徑集合
```

而 **`docs/GOVB1_INPUT_QUALITY_TODO.md` 是全程唯讀、禁改的凍結檔**。
⇒ 要讓 manifest 合法多一行，就得改那個檔；不改，F5 永遠紅。
⇒ **A 在現行約束下不可實作。** 延伸檔繞不掉——F5 的路徑是寫死的，只讀那一個檔。

**已完整還原**（`manifest`／`frozen_hashes`／`contract_matrix` 三檔 `git diff` 皆空），
回到 commit 後的狀態：**7 紅 ＝ 3 條 B-49 凍結 ＋ 4 條 G-7 群**。

🔴 **這件事的教訓比結果重要**：三家一致同意的方案，在**實作第四步**才發現不可行。
不是委員失職——**是主委的 brief 沒有給他們 F5 這個約束**（brief 只講了 B5 oracle 攻擊面）。
⇒ 紀律：**問「這個改動合法嗎」時，必須連同「還有哪些機檢會看這個檔」一起問。**

## 🔴 裁決：採 **C**（接受 G-7 紅），本輪不改碼

consult r2：composer＋grok 選 C，codex 選 **D**。**主委裁 C——不是數人頭。**

**D 是什麼、為什麼不採**：codex 發現 **F5 只比對 `allow` 集合**，故改用 **`meta`** 動詞
即可不動凍結 TODO 而讓 G-7 轉綠，並給了完整最小修訂集。**技術上可行且會成功。**
不採的理由＝使用者 2026-08-01 定死的「**禁以技術手法充當達標**」：
`meta` 的既有語意是簿記檔（`HANDOFF.md`／`CLAUDE.md`／backlog／`白話說明/`），
把治理**測試**檔宣告成 `meta` 的唯一目的是躲開 F5 比對 ⇒ **為過檢查而改變事實分類**。
🔴 **但這條記為「封存」不是「否決」**——codex 是唯一指出「F5 只比對 allow」這個機械事實的一方，
該事實對日後正式修訂 F5／TODO 有用。

**不選 B**（兩家一致）：會讓已驗收的 `test_cxrun_selfcheck_prompt.py` 功能回歸
（VERIFY:20260811T165108Z-selfcheck-7passed），與 B-49 Task 0.1 直接衝突，
且**完全不解 F5 牆**——凍結三檔照樣撞。

### 🔴 C 的代價已具名，不得淡化（grok 打掉主委的自辯）

主委原本寫「push 已被擋 ⇒ 接受紅不增加損失」。grok 逐字更正：
**對 push 布林值成立，但對 G-7 依賴測的判讀不成立**——長期單一路徑紅會讓所有
`g7.returncode == 0` 斷言**失去區分度**（紅燈疲勞）。接受此代價，並定死判讀方式：

> **現行 G-7 紅的唯一合法來源＝`tests/governance/test_cxrun_selfcheck_prompt.py`。**
> `bash scripts/govb1_final_gate.sh --only g7` 的輸出**逐行比對**，
> 只要出現該路徑**以外**的任何路徑，即為**新違規**，不得歸入「已知紅」。

### 正解（B-49 Phase 1 一併做，不是現在）

**走凍結檔正式修訂程序改 `docs/GOVB1_INPUT_QUALITY_TODO.md` 的宣告集，再走 A 四步。**
**非** `meta` 旁路、**非**延伸檔。四個檔（selfcheck ＋ 凍結三檔）**一次解決**。

## 🔴🔴 B-49 施工前置依賴 — 凍結三檔全是「幽靈路徑」

**幽靈路徑 ＝** ① `base..HEAD` **endpoint 淨差為零**（G-7 現在看不到）
② range 內被**無 trailer 的 commit** 觸及過（`path-only-OOE` 豁免已毒化、**永久失效**）
③ 不在 manifest allow。⇒ **現在綠，一被改就立刻 G-7 紅，且 OOE trailer 救不了。**

**實跑：11 條**（與 grok 獨立給出的數字相同）。
🔴 **`_B45_HARNESS` 五檔全部在內** ⇒ B-49 動哪一檔都會撞牆。
VERIFY:20260811T162835Z-govg7-ghostpath-b49

⇒ 已做成工具，不靠紀律：**`bash scripts/govb1_ghostpath_check.sh`**（盤點用，恆 rc=0）。
⇒ **B-49 SPEC 未寫到這件事**，已列為施工前置依賴：Phase 1 一 commit 即 G-7 紅，
除非同批處理三檔之 manifest 歸屬（走與本次相同的授權集合路徑）。

⚠️ **常駐規則**：改任一幽靈路徑前，**先跑上述工具**，再決定 allow 或接受 G-7 紅。
完整裁決（含「逐案不批次」）見 `handoffs/reconcile/20260812-govg7-x-consult-r1/synth.md`
（未戳記，故不列 REF:）。

**新增四紅**（皆 `test_govb1_contract_matrix.py`，主委只逐條讀了其中兩條的訊息，
另兩條**未複驗**、屬推測，已在 brief 標 assumed）：
`test_t01_f2_frozen_hashes_self_consistent`／`test_t01_f3_g7_when_committed`／
`test_r6_u1u2u4_g7_worktree_space_quote_paths`／`test_g7_ambient_m_gate_check_not_red`

---

## 已 commit 兩筆（`1f697465`、`5ea99af1`），未推送 2 筆

工作區成果不再只存在於工作區。push 仍全擋（三條凍結紅 ＋ 上述四條）。

🔴 **commit 時踩到的兩道閘，都不是誤擋**：
① 提交守衛把否定句「該檔測試**通過**不代表它讀 SoT」讀成綠燈宣稱 ⇒ 擋 commit。
   守衛不讀語意是刻意的，**代價是寫作要避開那幾個詞**；改成「不得以其測試結果作為證據」即過。
② `plain_docs_sync` 的判準是 **commit 時序**不是 mtime ⇒ 光改檔沒用，須同 commit 提交。

## B-49 SPEC **已定案，不再開審查輪**

r6 三家：composer `APPROVED`、grok 1 條、codex 4 條 `[MUST-BEFORE-IMPL]`（union ＝ 5）。
方向 BLOCKING **連續四輪 0**。5 條已當輪修畢，**其正確性由施工後的兩家 code review 承接**。

🔴 **其中一條是刪掉我自己在 r6 發明的「兩段提交」**——那是為了修我自己寫出的矛盾
（§R row 5 說綠、mutation ⑫ 說紅，講的是同一動作）而加的新機制，結果撞回 r3 的 bootstrap 死結。
而我的 r6 brief 逐字寫著「**不收任何新增機制**」。
⇒ 教訓入 SPEC §C-11：**消解矛盾要刪掉錯的那一端，不是再加一層。**
⇒ 同批 rebind 與合法維護**機械上不可區分**，依 C-6 具名排除、交 code review，**不宣稱擋得住**。

**下一步（r6 之後）**：產 B-49 TODO → 施工 → 兩家 code review。

---

**背景任務 `b3cxm86b9`** ＝ `20260811-govb49-x-review-r6` 三家 review，**已回並銷帳**。
🔴 **r6 是 SPEC 的最後一輪**（主委依使用者「95% 解法就收」與 epic 斷路器裁定，已寫進 brief）。
r6 之後不論剩什麼一律轉**具名殘留**並進 TODO 施工，**不開 r7**。
r6 brief 已明列**不受理範圍**（措辭精確度／更好的設計／防蓄意／任何新增機制），
並要求必修條目標 `[MUST-BEFORE-IMPL]`。

回來後流程：`reconcile_build.sh <session> --mode review <三檔>` → 填群集 →
`completeness_check.sh --lock <session>/sources.lock` →
`debt_clear.sh --round-id <id> --session <name> --lock <lock>`。
🔴 `reconcile_build` 預設 `mode=discovery`，**銷帳需 review** ⇒ 建時就帶 `--mode review`
（已建成 discovery 才補救：`--mode review --rebuild`，**不得帶委員檔**）。
🔴 `completeness_check --lock` 吃的是 **`sources.lock` 路徑**，不是 synth.md。

### r4／r5 兩輪的收斂軌跡（供判斷是否該停）

| 輪 | findings | 方向 BLOCKING | 機制變更 |
|---|---|---|---|
| r3 | 14 | 0 | （commit 區間版被判不可實作） |
| r4 | 14 | **0** | 上界 commit 區間 → **digest** ⇒ r3 之 7 條 range 系列**整類消解** |
| r5 | 15 | **0** | digest → **git 物件身分**（`ls-tree` 三元組） |
| r6 | 跑中 | — | `diff --quiet` → **`cat-file blob` 逐位元組**；§R 同批矛盾解除 |

**數量沒降但嚴重度在降**：r3 是「整個方案不可實作」，r5 是「某個措辭過強」。
方向 BLOCKING 連三輪 0 ⇒ 判尚在收斂，但**只給一輪**。

### 四條紅 → 剩三條（皆凍結，仍擋 push）

`test_cxrun_selfcheck_prompt.py::test_selfcheck_absent_for_impl` **已修**（不在凍結集合，7 passed）。
另三條在 `_B45_HARNESS` 內，需 `票 B-49` 落地。

### 🔴 修法形狀已由隔離實跑定案 — `docs/GOV_B49_PINSHAPE_RECEIPT.md`

**那批紅是兩種病**：`test_result_state` 寫死家族名；另兩檔**已經在讀 SoT，仍然紅**
（`claude` 無 CLI 配方）⇒ **「改成讀 SoT」對三分之二是錯的修法**。
修法＝**釘沙箱名冊**（`tests/governance/_role_pin.py`，已落地未凍結區）。
隔離實跑：五個 `_B45_HARNESS` 檔 **141 passed / 0 skipped**（基準線 3 failed ＋ 1 靜默 skip）。

🔴 另抓到票文未列的靜默失效：`pytest.skip` 在 **for-loop 內**，一個非預期 implementer
**連帶吃掉 review/consult/closure 三種 kind 的覆蓋**，整檔仍報綠。

### SPEC 已到 r5（`docs/GOV_B49_PATH_GRANT_SPEC.md`，template_check rc=0）

- **r4**：授權上界由 commit 區間改 **digest** ⇒ 三家判定 r3 之**七條 range 系列全部消解**。
- **r5**：digest 契約定死為 **git 物件身分**（`git ls-tree HEAD` 之 `<mode> <type> <oid>`
  ＋ `git diff --quiet HEAD` rc=0）。此一步同時消掉同源／換行正規化／symlink／mode 四個爭議。
- r4 三家 verdict 皆 `NEEDS-WORK`，且**方向 BLOCKING ＝ 0**（斷路器未觸發，digest 方向獲保留）。

### 🔴 r4 打掉三條**我已落地的**程式碼缺陷（全部已修，見收據 §7b）

`reviewers` 公式錯（把無 CLI 的 `claude` 算進 review pool——**同一公式本 session 第三次咬人**）／
SoT 來源固定讀 `REPO_ROOT` 而非傳入的 `scripts_dir`（沙箱變異看不見 ⇒ mutation 假綠）／
`case` 分支 regex 只收兩空白縮排。修最後一條時揭出更深的問題：**區塊結尾錨點 `\nesac`
不匹配縮排的 `esac`**，舊版**是靠兩塊縮排剛好不同才正確的**。
承重探針 `.claude/tmp/rolepin_probe.py` **7 格全 PASS**。

### 線 A 站 5：`CODEX-R3-P1-04` **已修並通過 r5 review**

`tests/governance/test_gate_claude_narrow.py` 新增 **5 格**定向 mutation ⇒ **41 passed**。
composer／grok 判 `APPROVED`；codex 判需要第五格並**附可重現反例**
⇒ 依「看碼證不數人頭、附反例者勝、不決採較嚴版」**採 codex**，已加入 `CMDPOS_CARET`。
🔴 但 **codex 的對照組是錯的**（主委實跑推翻）：它預期 `$(printf codex) exec hi` 維持 BLOCK，
實測**兩條一起翻**——因為展開網之 `_pat` 自己也以 `${_GL_CMDPOS}` 起頭，行首命令同樣靠 `^`。
正確對照＝**命令不在行首**（走 `[;&|(`]` 分支）。
`GL_WRAPPER_DEF` 死常數已刪（`GROK-R5-P2-01`）。
⇒ 現可誠實宣稱「**五式各自承重**」，不需 codex 提的降級措辭。
🔴 查證發現比報告更糟：`GL_WRAPPER_DEF`／`GL_FAMS_DEF`／`GL_TOKEND_DEF` **從未被任何測試使用**，
且 `GL_TOKEND_DEF` 字面停在 r3 修 `$IFS` **之前**——看似有錨點，實則既不承重也不正確。已接上成承重錨點。
`CODEX-R3-P0-03` 依 r3 裁決轉 `票 B-59`，本輪不修。
**仍欠**：章程 §B8 —— 已修兩條須由**原提出方 codex** 重跑自己的反例確認閉合。

🔴 **教訓（已入紀律）**：凡宣稱「影響面就是這幾個檔」，一律以**全套實跑**為準，不得以子集掃描代替。
出處＝r2 的 Q2 只問了五個 harness 檔，三家給了那個問題的正確答案，但沒人跑全套 ⇒ 漏掉第四條紅。

---

## 🔴🔴🔴 `票 B-49` 已阻塞——需**使用者裁定**，委員無權解

TODO review（codex＋grok；composer 連兩次 `resource_exhausted`，依 `collection-failed` 銷帳）
判 `NEEDS-WORK`，**6 條 `[MUST-BEFORE-IMPL]`**。codex 五條抄寫漂移**已當輪修畢**；
grok 一條證明 **`Task 0.2` 照做不會成功**。

**三條已知路徑全部證偽**（不得重試）：

| 路徑 | 為何不通 |
|---|---|
| 直接加 manifest `allow` 行 | F5 要求 allow 集合逐條等於凍結 TODO 宣告集 ⇒ 紅 |
| 改用 `meta` 動詞 | 機械可行，但屬「以技術手法充當達標」，使用者已定死禁止 |
| 走凍結檔正式修訂程序改宣告集 | 同時撞 `_B5_FORBIDDEN_PREFIXES` 含 `docs/GOVB1_`（無例外機制）＋ G-7 未宣告 ＋ `_G7_OOE_HARD_PROTECTED` 字面含 `docs/GOVB1_`（trailer 救不了） |

**唯一自洽的機械解**：把 `docs/GOVB1_INPUT_QUALITY_TODO.md` 納入 B-49 grant 之第四條路徑
＋ manifest allow ＋ **其自身宣告集**（自我宣告）⇒ F5 兩側相等、B5 由 grant 例外承接、
G-7 由 allow 覆蓋。**機械上成立**，但要求修改一個**雙重凍結**的檔
（機械強制 ＋ 使用者常駐約束）⇒ **委員無權解除。**

### ✅ 已裁定（2026-08-12）：使用者選 (a) 並擴大授權——見本檔最上方「使用者授權」節

以下三選項保留為紀錄。**(a) 已獲授權且範圍更大**（連同殘留一次做完）。

### ~~待使用者三選一~~（已裁定）

- **(a)** 就本次施工解除該檔唯讀，**只准改其宣告集**（不動技術內容）⇒ B-49 可施工
- **(b)** 維持唯讀 ⇒ **B-49 不可實作 ⇒ push 長期全擋**
- **(c)** 另設計（三條已證偽；主委與兩家委員均未見第四條）

⚠️ **在裁定前，一律不得碰 `docs/GOVB1_INPUT_QUALITY_TODO.md`**（已依「不決採較嚴版」）。
`decl` 數字（40 或 41）亦待裁定後才鎖定。

🔴 **這是第三次同型死結**（r3 range bootstrap → r6 兩段提交 → 本次 Task 0.2）。
**已成模式**：每次為繞過一道牆而提的方案，都在下一層撞上另一道牆。
下次提「正解」前，須先窮舉**所有**會看該檔的機檢，而非只驗當前那一道。

---

# 接手第一件事（照順序讀完這三節再動任何檔）

## ① 🔴 **push 是全擋的**，而且這是已知且刻意的

`implementer=claude` 使 **3 個凍結測試檔轉紅**；`pre-push` 委派 `gov_check.sh`，
後者跑**全套** `pytest tests/governance` ⇒ **整個 repo 推不出去**，與你改了哪些檔無關。

- **commit 沒有被擋**，只有 push 被擋。目前 **未推 commit ＝ 0**，工作區 **34 髒檔**
  ⇒ 站 5 以後的所有成果**只存在於工作區**。工作區壞掉就全沒了。
- 🔴 **不要「還原 `implementer=grok` 換綠」**——三家一致否決為長期策略；
  codex 逐字判其「直接違反使用者已定的 `implementer=claude`，且會把名冊與事實重新錯置」。
- `GOVERNANCE_SKIP_PREPUSH=1` 與 `git push --no-verify` 三家一致判為**緊急留痕通道、非排程方案**，
  且**繞不過 CI**。

## ② 🔴 兩條工作線都在半空中，**都不可 commit**

**線 A：站 5（GOVB0 `B4`）**——三輪三家 review 完，r3 判「不可 commit」。
未修兩條：`CODEX-R3-P0-03`（變數化路徑呼叫派工腳本）、`CODEX-R3-P1-04`（五式未證承重）。
🔴 還欠一輪**章程 §B8**：已修的兩條須由**原提出方（codex）重跑自己的反例**確認閉合。

**線 B：`票 B-49`**——見下節。它是 push 的唯一阻塞項。

## ③ 🔴 委員名冊已切三家，四處定義同步完成

`active_stampers` 加 grok；`eligible` 加 `claude`；`implementer=claude`；`reviewers` ＝三家；
`_role_gate.sh` 補了「implementer 不在 `review_families` 時角色規則靜默失效」那個洞。
**完整裁定、代價與具名殘留在 `docs/GOV_ROLES_ORCHESTRATOR_AMENDMENT.md`，本檔不重述。**

⚠️ 舊敘述「grok 額度封鎖 ⇒ 委員＝兩家」**已作廢**，勿沿用。

---

# 🔴 線 B：`票 B-49` —— 目前的全部狀態

## 已跑完的輪次（皆已建收斂檔、債全清）

| 輪 | 收斂檔 | 結果 |
|---|---|---|
| consult r1 | `…/20260811-govb49-x-consult-r1/synth.md` | 三家 NEEDS-WORK；grok 抓到主委引入之 P0（`set_roles` reviewers 公式），已修，隔離驗證 5/5 |
| consult r2 | `…/20260811-govb49-x-consult-r2/synth.md` | 兩家 APPROVED、最小集**三檔**；codex 被 STAMP-BLOCK（主委 brief 漏寫聲明） |
| consult r3 | `…/20260811-govb49-x-consult-r3/synth.md` | codex **REJECTED** ⇒ r2 授權**撤回** |
| SPEC review r1 | `…/20260811-govb49-x-review-r1/synth.md` | 12 條、3 BLOCKING |
| SPEC review r2 | `…/20260811-govb49-x-review-r2/synth.md` | 10 條、3 BLOCKING ⇒ **斷路器命中，第一版 SPEC 依約放棄** |
| consult r4 | `…/20260811-govb49-x-consult-r4/synth.md` | 三家定方向＝**C 案**；三家一致否決「根本不該做」 |
| SPEC review r3 | `…/20260811-govb49-x-review-r3/synth.md` | 14 條、**方向 BLOCKING ＝ 0** ⇒ 不觸發斷路器 |

## 現行 SPEC 與已放棄者

- **現行**＝`docs/GOV_B49_PATH_GRANT_SPEC.md`（C 案；過 `template_check.sh spec` rc=0）
- **已放棄**＝`docs/GOV_B49_UNFREEZE_WINDOW_SPEC.md`（第一版；保留對照，**不是基礎**）

## C 案是什麼（三家共識，非主委原案）

**永久三檔 path grant ＋ 炸彈狀態機 R-A ＋ 行為式閉合證據。**
純 A（不改炸彈）與純 B（不改凍結面）皆被兩家實跑證明**結構上不可達**。

🔴 **照抄既有先例，不發明新機制**：`_B5_MANIFEST_UNLOCKED` ＋
`_B5_MANIFEST_AUTHORIZED_ADDITIONS` ＋ `test_b5_manifest_extension_is_exactly_authorized`
已是「永久、字面、被測試釘死的授權」之範本。該處註解逐字警告：
oracle 須為**字面期望集合**，寫成由同一常數導出之式子會**同義反覆恆真**。

🔴 **最小解凍集＝三檔**（三家各自逐檔實跑，rc 表逐格相同）：
`test_stamp_taskid_inject.py`／`test_rolegate_predispatch.py`／`test_result_state_format_failed.py`。
`test_cxrun_stamp_prompt.py`／`test_completeness_idlike_fp.py` **rc=0，不得順手解凍**。

## 🔴 SPEC r4 必須修的（review r3 之 14 條，全部接受）

1. **range 演算法**：兩端點 diff 的 union **不等於**歷史路徑集合；須為每個 guard 明定
   `lower`／`window_upper`／`upper` 之祖先關係 ＋ clamp ＋「僅開窗後」限定 ＋ rename／merge 語義
2. **bootstrap 死結**（兩個獨立原因）：(a) `govb1_frozen_hashes.txt` 的鍵是**封閉集合**，
   直接拒 `b49_grant_upper`；(b) 上界＝施工 commit 自身時無法自指其 hash。
   ⇒ 採 **S2＝改用 digest** 或 **S1＝兩段提交＋明確 missing-upper 語義**，二擇一寫死
3. **selector 對不上票文**：`rolegate`／`result_state` 兩條 selector **不覆蓋**票文 ②③
   （② ＝ invalid implementer mutation 轉紅＋三合法值通過＋`skipped=0`；③ ＝ `eligible` 機械連動）
   ⇒ 失敗模式是**B-49 假 CLOSED**，須逐條對應票文重寫
4. **`grant_upper` 可滑動**：未凍結「寫後不可前移」，設太早反而變長期白名單（與原意相反）
5. **selector 只釘名稱**：`test_v12…` 是 for-loop 跑四種 kind，移除 `impl` case 仍表面綠
6. **rename／隔離環境未定義**：須明寫 `--no-renames` 與隔離 subprocess 之最小變數集
7. **§R 回退條文是錯的**：已 push 後 `git revert` **不成立**（不刪 name-only 歷史）
   ⇒ 誠實版＝**一旦 push 即不可回退**，「push 前必須確定」是硬要求

## 🔴 斷路器（現行判準，勿改寬）

**只由「方向問題」BLOCKING 觸發，≥2 條即退回重議方向。**
brief 須要求每條 BLOCKING 自標「方向問題／條文問題」——review r3 已證明三家皆能區分，
且無人濫用 BLOCKING 表達不滿。
⚠️ review r3 字面計數為 2 條 BLOCKING，是靠**派工前**細化的判準才不觸發；備查用。

---

# 🔴 線 A：站 5（GOVB0 `B4`）

| 檔 | 內容 |
|---|---|
| `scripts/_gate_lex.sh` | 判定式收斂成 5 個變數 ＋ 修掉 **7 類 fail-open** |
| `tests/governance/test_gate_b4_wrapper_and_scripts.py` | 新檔，51 passed，含 5 條定向 mutation |
| `tests/governance/` 另 4 檔 | mutation 錨點由「釘整串正則」改為「釘變數定義」 |
| `tests/…/fixtures/gate_decision_corpus.txt` ＋ `.sha256` | 契約 5 之 TN 替換（**兩家裁決授權**） |

收斂檔：`handoffs/reconcile/20260811-govb0-b4-review-r{1,2,3}/synth.md`（債全清）。

🔴 **主委在 r2 收斂檔宣稱「四個消費點全引用」——那句話是假的**，
兩家獨立證明還有第五個（claude 段）。已修，勿沿用該宣稱。

### 這條線不會靠再修幾個樣式收斂

r1／r2／r3 各四條，**每輪都在同一段判定式找到新的沒被列舉到的形態**。
已開 **`票 B-59`（優先序高）**：判定式是黑名單，形態不可窮舉。
**對外宣稱限制**：可說「修掉 N 個**已知**形態」；❌ 不可說「dispatch gate 已完備」。

### 探針（皆在 `.claude/tmp/`，只餵字串不執行）

`b4_probe.sh`／`b4_r2probe.sh`／`b4_net_wrapper.sh`／`b4_r3verify.sh`（含 HEAD 對照）／
`b4_r3fix.sh`（23）／`b4_corpus.txt`＋`b4_verdicts.sh`（基準在 `b4_before.txt`）／
`setroles_probe.sh`（5 格，名冊公式）／`sync_factkey_fixtures.sh`／`vrg_probe.sh`。

🔴 **探針向量一律放檔內，不放指令列**——放指令列會被這道閘當成真派工擋下（實際發生過三次）。

---

# 🔴 委員分工：規則是「不分工」

`feedback_committee_full_scope`：**每委員都要全面看整件事、各產完整版，禁分角度。**
機制上三家收到的是**同一份 brief**。
**唯一合法的差異**＝章程 §B8「退回修改後由**原提出方**重跑自己的反例確認閉合」。

三家實績（供判斷可信度，不是貼標籤）：
grok 復出後三次抓到另兩家沒抓到的關鍵（主委引入之 P0、SPEC 狀態機死結、`active_stampers`
的 HEAD 基準線）；codex 每輪都附可重現反例，且是唯一讀到引信 return 條件那行的；
composer 在 r3 起改善，並獨立命中 selector 對不上票文。
⇒ **分歧時依「看碼證不數人頭、附可重現反例者勝過 sentinel、不決採較嚴版」。**

---

# 站 4 — `B3R`（**已 commit+push `e029514d`**）

🔴 **先讀 `docs/GOV_B3R_C5_RATIONALE_AMENDMENT.md`**：C-5 的秒數門檻**沒有可驗證的威脅模型**
⇒ 不得宣稱修掉 fail-open；且實作是 **O(n·√n)**，**不是** SPEC 寫的 O(n)。
完整收據＝`docs/GOV_B3R_PHASE3_RECEIPT.md`。
真根因＝BWK awk 的 `substr()` 成本正比於來源字串總長。
🔴 fuzz 抓到 233/12000 例差異（Phase 2 誤改前導空行語義），已還原並加回歸樁。

---

## 🔴 未修的活缺口

- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；`TODO:822` 第 1 條 ASSERT 字面不成立。
  修它須動 `_B45_HARNESS` ⇒ 觸窗守衛 ⇒ 需 `票 B-49` 先落地。
  🔴 **OOE 通道救不了**：`_MSG_PARSE_MARKERS` 含 `"Governance-Scope"`，窗守衛結構上禁解析 commit 訊息。
- `R-13` 未列舉之 Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`（同型旗標空值不一致）
- `票 B-54`：戳記行之 64 位 hex 由委員手抄 ⇒ 曾實際掉字一次
- `B3R` 的重寫已進主樹，但三家 review 尚未戳記 ⇒ 對外只能說「已交付、待戳記」
- `票 B-56`：`_gate_lex_extract_inners`／`_extract_cmdsubs` 仍逐字迴圈（500K 15.3s）；
  修它須先判定 `j = i + RLENGTH` 未用 RSTART 是否為缺陷 ⇒ 屬行為變更，不得夾帶進效能批
- `票 B-57`：`parse_heredoc_delim` 的 `rest = substr(s, pos)` 全尾切 ⇒ heredoc 密集 500K **434 秒**
  （**優先序低**：查證後「慢＝危險」的前提不成立）
- `票 B-58`：前導空行被丟棄；是否為缺陷**未判定**，回歸樁釘的是「與舊版一致」而非「這行為是對的」
- `票 B-59`（**優先序高**）：dispatch gate 的判定式是**黑名單列舉**，形態不可窮舉。**不得宣稱閘已完備。**
- `票 B-60`：`review_quorum_check.sh:35` 家族清單硬編，未讀 SoT；`_DRIFT` 已釘之，
  故**不得以該檔之測試結果作為「它讀 SoT」的證據**
  REF:handoffs/reconcile/20260811-govb49-x-consult-r1/synth.md
- `票 B-61`：`_role_gate.sh` 的 `known_only` 對未知家族靜默放行（`agy`＋consult）；
  既有行為，非本輪引入 REF:handoffs/reconcile/20260811-govb49-x-consult-r1/synth.md
- `票 B-49`：閉合條件 ④ 已執行，**①②③ 未做 ⇒ 順序是倒的**；代價＝三檔轉紅 ⇒ **push 全擋**
  REF:handoffs/reconcile/20260811-govb49-x-consult-r1/synth.md
- 站 5 未修殘留：`CODEX-R3-P0-03`、`CODEX-R3-P1-04`、
  `gate_check.sh` 之 audit 分類器未同步（新形態記為 `match_rule=unknown`）、
  `bash -n <派工腳本>` 誤擋、`$(printf echo) codex` 誤擋、`eval "$(echo cx_run.sh)"` 仍放行（既有）
- `票 B-15` 誤擋在 `B7` 之後仍存在（`printf`／`find`／`ls`／`gate.sh` 自身）⇒ GOVB0 `B4` Task 2.3/2.4
  🔴 新增一例：`for f in codex composer grok; do …` 這種**唯讀迴圈**會被家族名偵測誤擋
- `gate_check` 對真派工放行：process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c` ⇒ GOVB0 `B4`
- `票 B-50` 流程面永久標記為跳步；`票 B-31` 對外只能說「產出端已有檢查點」（`票 B-53` 落地前）
- `plain_docs_sync_check.sh` catch-all 回空字串 ⇒ 新增說明檔預設不受監看
- `R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit
- `template_check.sh` 之 `^[[:space:]]*[-*]` 會把 `**粗體**` 開頭的行誤判為 bullet
  ⇒ 範本自己的欄位標籤會觸發空殼偵測（已繞開，未修）

## ⚠ 操作紀律（踩過的坑，一律照做）

- 🔴 **補洞前先問「舊行為在這個輸入上是什麼」**。**補洞比洞更危險**——本 session 發生兩次：
  站 5 為修 P2 而開 P1；名冊改動時把 `claude` 加進 `eligible` 卻沒看誰消費它（grok 抓到）。
- 🔴 **凍結測試檔會以原始碼字面錨定生產腳本的行** ⇒ 那些行等於被連帶凍結，**改對了也會紅**。
- 🔴 **委員戳記主委不得代寫**——sha 掉字要重派。
- 🔴 **改 `scripts/fact_keys.json` 的連鎖三件事**：① 跑 `--write` 重生成所有宿主檔
  ② **同步兩份 fixture**（用 `bash .claude/tmp/sync_factkey_fixtures.sh`，drifted 須保留其單列竄改）
  ③ 生成內容**不得含任何 `20\d{2}-\d{2}-\d{2}` 形狀的字串**。
- 🔴 **新開票會改變 `governance-ticket-closure` 的機械導出集合**：union＝本檔「未修的活缺口」節
  ∪ backlog 之「2026-08-10 scope 缺口」節所提及的票號 ⇒ 增刪票號提及須同步 `fact_keys.json`。
- 🔴 **brief 的 `fact-verified` 若引用「派工會改變的 rc」，必須含字面 `派工後預期值:`**——
  那是機檢錨點，不得為了通順而改寫（本 session 踩過）。
- 🔴 **brief 須逐字寫「`handoffs/reconcile/**/synth.md` 為無戳記工作輸入，不得 STAMP-BLOCK」**——
  漏寫會讓委員依合約停工，整輪零產出（本 session 發生一次，代價是補派一輪）。
- 🔴 **session 命名規約**：`<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，`r<N>` **只收純數字**
  （`r2b` 會被拒）；task-id 必須是 session 的**大寫全形式**。
- 🔴 **`docs/` 與新增 `scripts/` 檔不在 manifest** ⇒ commit 須帶 `Governance-Scope: out-of-epic` trailer，
  且**trailer 必須在最後一段**（git 只解析最末段）。收尾跑 `--only g7`。
- 🔴 **`docs/GOVB1_` 前綴 OOE 亦禁**（硬保護集）⇒ 延伸檔須另取名。
- 🔴 **背景任務 exit code ＝ 指令鏈最後一個的 rc**；推完用 `git rev-list --count origin/main..HEAD` 實查。
- 🔴 **`git push` 用 harness `run_in_background`，不得用 shell `&`**。
- 🔴 **改一個事實前先 `grep -rn` 掃全部副本**；改檔一律 Edit/Write，禁 `sed -i`／heredoc。
- 🔴 **BSD awk `-v` 值不接受換行**；**awk 無 regex 型別**；`$( )` 內禁 `case`；**rc 禁經 pipe**。
- 🔴 **mutation 錨點須唯一且與實作同步**；錨點失配時測試須 fail-closed 轉紅。
- 🔴 **不要開輪詢迴圈等背景任務**——harness 本來就會通知。本 session 因此留下三個殭屍迴圈（最久 2h43m）。
- 全套 `pytest tests/governance -q` **≈615 秒 / 1473 passed**（2026-08-11 實測，名冊改動**前**）
  ⇒ 丟背景，跑完 `bash scripts/restore_golden_inventory.sh`。
- 委員跑驗收時**主控端不得動檔**；銷帳前先等 `ps aux | grep cx_run.sh` 歸零。
- stamp 輪產出為散文無 canonical ID ⇒ 收集節點必失敗，走 `no-findings-expected` 銷帳（`票 B-52`）。
