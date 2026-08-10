# Handoff

REF:handoffs/reconcile/20260810-govb1-b4-review-r3/synth.md
REF:handoffs/reconcile/20260810-govb1-b4-consult-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-11 | **Branch**: main | 實作＝主委自任；review＝codex+composer

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 施工順序／批次狀態／票收案狀態 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 之三個 generated block |
| 票的內容 | `handoffs/20260801-GOV-AMEND-BACKLOG.md`（55 張） |
| 給使用者的現況 | `白話說明/接下來要做什麼.md`／`治理待辦總覽.md` |
| 摩擦統計現值 | `bash scripts/friction_tally.sh --by-event`／`--field-presence`（**數字不寫死**） |
| `b4` 階段 2 之交付與殘留 | `docs/GOV_B4_STAGE2_AMENDMENT.md` |

🔴 **generated block 一律不得手改**：改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`。

## 🔴 使用者 2026-08-11 裁定：**照順序表走，不插隊**

明確答覆「就照你的順序」⇒ **站 4 → 站 5 → 站 6 → 站 7**，不為了 `R-12` 把站 7 的解凍提前。
🔴 **不要再去問使用者要不要解凍**——已問過，答案是照順序。等真的走到站 7 再整包提出。

## 🔴 地雷：`scripts/governance_roles.json` 的 `implementer: grok` **是刻意的，不是漏改**

看起來「名冊與事實不符」（grok 額度封鎖、實際實作端是主委），但 `set_roles.sh:54-57`
逐字記載了兩家 APPROVED 的裁決：

```
implementer=grok      → 非實作者池 {codex, composer} → 2 家可用 ✅
implementer=codex     → {composer, grok} → 僅 1 家可用 ❌ quorum 當場破
implementer=composer  → {codex, grok}    → 僅 1 家可用 ❌ quorum 當場破
```

⇒ **把實作者掛在一個不會真的被派工的家族上，是目前唯一能湊出「兩家 review」的辦法。**
改成 codex 或 composer ⇒ 下一次 code review 只剩一家 ⇒ **全部派工當場被擋死**。

🔴 **票 `B-49` 的第 4 條（使用者改名冊）是最後一步，不是第一步**：
條文逐字為「**之後才**由使用者更新」，前三條（`:769` 改 fail-closed、mutation 證據、
`eligible` 與測試家族集合機械連動）都要先做，而它們全在凍結的五檔內。
⇒ **現在單獨改名冊只會把洞開著**。主委 2026-08-11 曾把這條講成「卡在使用者身上」，**措辭不準，已更正**。

## 🔴 接手第一件事：**站 4 — `B3R` 的 O(n) scanner**（序 `050`）

出處：`handoffs/reconcile/20260809-govb1-b3-review-r8/synth.md:44-50`（`CODEX-R8-P1-03`）。

- **病**：`scripts/_gate_lex.sh` 之 `_gate_lex_preprocess` 兩個 pass 皆逐字元累加字串
  （`out = out c`、`src = src "\n" line`、`line = line substr(...)`）⇒ **O(n²)**。
- **SPEC C-5 驗收**：quoted 100K **<2s**、500K **<5s**（`docs/GOVB0_B3R_LEXER_SPEC.md:142-143,209`）。

### 🔴 Phase 2 原型與差分**已於 2026-08-11 做完，但 C-5 未達標 ⇒ 依 SPEC 不得進 repo**

**完整收據（量測、差分、profiling 結論、四支工具位置）＝`docs/GOV_B3R_PHASE2_RECEIPT.md`。**
一句話版：`500K 29s → 11s`、95 條語料**輸出逐位元組相同**、但 C-5 要 `<5s` ⇒ **不落地**；
profiling 已證明瓶頸是**每字元一次 awk 函式呼叫**（改 chunk 大小完全無效），真解是**批次掃描演算法重寫**。
🔴 **主樹 `scripts/_gate_lex.sh` 一字未動**；原型在 worktree `.claude/tmp/probe-r11r12`。

<!-- 本節原有 46 行明細，已**逐字**搬至上述 docs 收據檔（HANDOFF 須 ≤30 行）。
     🔴 用搬不用刪：上次精簡 HANDOFF 是直接刪，弄丟「B-53 提及」與「fixture 同步」兩條，
     兩條都在同一天咬回來（前者害 push 被拒、後者害兩條測試轉紅）。 -->


## ✅ 本 session 已交付（2026-08-10～11，皆兩家 `RECONCILE-STAMP APPROVED`）

| 站 | 收斂檔（`reconcile_stamps_check` 皆 rc=0） | 輪數 | 🔴 未閉合 |
|---|---|---|---|
| 2.5 `B-25` | `…/20260810-govb25-x-review-r6/synth.md` | 7 輪 33 條 | 八條殘留，含「判準資料化」整項未做 |
| 2.6 `B-37` | `…/20260810-govb37-x-review-r5/synth.md` | 5 輪 18 條 | 六條殘留，含票級統計與強制機制兩項未交付 |
| 2.7 前半 | `…/20260807-govb1-b1-review-r6/`、`…/20260809-govb1-b4-review-r4/` | 1 輪 | — |
| 2.7 後半 | `…/20260810-govb1-b4-consult-r1/`、`…/20260810-govb1-b4-review-r3/` | 1 consult＋3 review＋2 stamp | 五條殘留（見下） |

**三票皆不得宣稱閉合。** 站 2.7 後半交付的**只有階段 2**，該批之整體狀態一律看
`docs/GOVERNANCE_EXECUTION_ORDER.md` 的 `governance-batch-status` block，**本檔不重述**。

> 🔴 本節刻意不把批次識別碼與狀態值寫在同一行——主委 2026-08-11 在本檔與
> `白話說明/治理待辦總覽.md` 各被自己建的偵測器擋下一次（全 session 共三次）。機制正常運作。
> **不寫行號**：行號會隨每次編輯漂掉，寫了就是下一個要對帳的假事實。

## 🔴 未修的活缺口

- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；`TODO:822` 第 1 條 ASSERT 字面不成立。
  修它須動 `_B45_HARNESS` ⇒ 觸窗守衛 ⇒ 需解凍 ⇒ `票 B-49` 須 CLOSED，而其閉合條件第 4 項**須使用者改 `governance_roles.json`**。
  🔴 **OOE 通道救不了**：`_MSG_PARSE_MARKERS` 含 `"Governance-Scope"`，窗守衛結構上禁解析 commit 訊息。
- `R-13` 未列舉之 Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`（同型旗標空值不一致）
- `票 B-54`（新開）：戳記行之 64 位 hex 由委員手抄 ⇒ 本 session 實際掉字一次
- `B3R` O(n) scanner 未交付（`CODEX-R8-P1-03`）⇒ 不得宣稱達標
- `票 B-15` 誤擋在 `B7` 之後仍存在（`printf`／`find`／`ls`／`gate.sh` 自身）⇒ GOVB0 `B4` Task 2.3/2.4
- `gate_check` 對真派工放行：process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c` ⇒ GOVB0 `B4`
- `票 B-50` 流程面永久標記為跳步；`票 B-31` 對外只能說「產出端已有檢查點」（`票 B-53` 落地前）
- `plain_docs_sync_check.sh` catch-all 回空字串 ⇒ 新增說明檔預設不受監看
- `R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit

## ⚠ 操作紀律（踩過的坑，一律照做）

- 🔴 **補洞前先問「舊行為在這個輸入上是什麼」**。本 session 為修一條 P2 而開了一個 P1
  （三版本對照 `擋 → 放行 → 擋`）。**補洞比洞更危險**。
- 🔴 **凍結測試檔會以原始碼字面錨定生產腳本的行**（`_CR_BK_FULL_EXTRACT` 等）⇒ 那些行等於被連帶凍結，
  **改對了也會紅**。解法＝保留該行逐字、只換它的輸入。
- 🔴 **委員戳記主委不得代寫**——sha 掉字要重派，不得自己補。
- 🔴 **改 `scripts/fact_keys.json` 的連鎖三件事**（本 session 因精簡 HANDOFF 砍掉此條，當場踩回去）：
  ① 跑 `--write` 重生成所有宿主檔　② **同步兩份 fixture**（`factkey_clean`／`factkey_drifted`，
  drifted 須保留其單列竄改）　③ 生成內容**不得含任何 `20\d{2}-\d{2}-\d{2}` 形狀的字串**（防時間戳的決定性守衛）。
- 🔴 **新開票會改變 `governance-ticket-closure` 的機械導出集合**：union＝`HANDOFF.md` 之
  「未修的活缺口」節 ∪ backlog 之「2026-08-10 scope 缺口」節所提及的票號。
  ⇒ 在 HANDOFF 增刪票號提及**就會**讓 `test_e3_ticket_union_matches_key_rows` 轉紅，須同步 `fact_keys.json`。
- 🔴 **兩家 Verdict 分歧看碼證不數人頭**；附可重現反例者勝過 sentinel；不決採較嚴版。
- 🔴 **`docs/` 與新增 `scripts/` 檔不在 manifest** ⇒ commit 須帶 `Governance-Scope: out-of-epic` trailer，
  且**trailer 必須在最後一段**（git 只解析最末段；本 session 因寫在中段而 g7 紅過一次）。收尾跑 `--only g7`。
- 🔴 **`docs/GOVB1_` 前綴 OOE 亦禁**（硬保護集）⇒ 延伸檔須另取名（本次用 `docs/GOV_B4_STAGE2_AMENDMENT.md`）。
- 🔴 **背景任務 exit code ＝ 指令鏈最後一個的 rc**；推完用 `git rev-list --count origin/main..HEAD` 實查。
- 🔴 **`git push` 用 harness `run_in_background`，不得用 shell `&`**。
- 🔴 **改一個事實前先 `grep -rn` 掃全部副本**；改檔一律 Edit/Write，禁 `sed -i`／heredoc。
- 🔴 **BSD awk `-v` 值不接受換行**；**awk 無 regex 型別**（`f($0,/re/)` 會先求值成 0/1）；`$( )` 內禁 `case`；rc 禁經 pipe。
- 🔴 **mutation 錨點須唯一且與實作同步**；錨點失配時測試須 fail-closed 轉紅。
- 全套 `pytest tests/governance -q` **≈470 秒 / 1393 passed**（2026-08-11 實測）⇒ 丟背景，跑完 `bash scripts/restore_golden_inventory.sh`。
- 委員跑驗收時**主控端不得動檔**；`cx_run.sh` 可能在委員 `.md` 寫出後仍未記 `committee_family_result`，
  銷帳前先等 `ps aux | grep cx_run.sh` 歸零。
- stamp 輪產出為散文無 canonical ID ⇒ 收集節點必失敗，走 `no-findings-expected` 銷帳（`票 B-52`，已發作九次）。
- `grok` 額度封鎖 ⇒ 委員＝codex＋composer（使用者 2026-08-10 確認）。
