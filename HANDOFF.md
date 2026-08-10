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

## 🔴 接手第一件事：**站 4 — `B3R` 的 O(n) scanner**（序 `050`）

出處：`handoffs/reconcile/20260809-govb1-b3-review-r8/synth.md:44-50`（`CODEX-R8-P1-03`）。

- **病**：`scripts/_gate_lex.sh` 之 `_gate_lex_preprocess` 兩個 pass 皆逐字元累加字串
  （`out = out c`、`src = src "\n" line`、`line = line substr(...)`）⇒ **O(n²)**。
- **SPEC C-5 驗收**：quoted 100K **<2s**、500K **<5s**（`docs/GOVB0_B3R_LEXER_SPEC.md:142-143,209`）。

### 🔴 主委 2026-08-11 已做完 Phase 2 原型與差分，**但 C-5 未達標 ⇒ 依 SPEC 不得進 repo**

原型與量測全在 `.claude/tmp/probe-r11r12/`（git worktree，**主樹 `scripts/_gate_lex.sh` 一字未動**）。

| 項 | 舊版 | 原型 |
|---|---|---|
| quoted 100K | **1s** | **0s** |
| quoted 500K | **29s** | **11s** |
| 差分（95 條語料：`gate_decision_corpus` ＋ `gate_invariance_corpus`） | — | `pre_diff=0 rc_diff=0`（前處理輸出**逐位元組相同**、判定 rc 全同） |

🔴 **29s 這個數字與 SPEC `E-2` 記載的 `500K→29.92s` 吻合** ⇒ 量測可信、可重跑。

**原型改了什麼**：`ACC_RESET/ACC_ADD/ACC_GET` 三個 awk 函式取代所有 `out = out c`／`src = src line`／
`line = line substr(...)`（共 20 處，以斷言命中次數的腳本機械替換，漏一處即拒寫檔）；
`ACC_GET` 用**兩兩合併**（log 深度）而非線性串接。

🔴 **為什麼 2.6× 之後就卡住（profiling 結論，別再重試同一路）**：
`prof_lex.sh` 把 `_gate_cmd_is_dispatch` 拆三段量測 ⇒ 500K 時 `grep_pre=0 preprocess=11 match_scan=0 grep_post=0`
——**全部時間都在 awk 前處理內**，且把 chunk 由 8192 改 128＋log 合併**完全沒有改善**（仍 11s）
⇒ 瓶頸**不是字串累加**，是**每字元一次 awk 函式呼叫／迴圈迭代**本身（1M 次）。
⇒ 真正的解＝**批次掃描**（一次跳到下一個特殊字元，整段 `substr` 搬移），
  而 POSIX awk 沒有「從偏移量開始 match」的原語 ⇒ 這是**演算法重寫**，不是微調。
  這正是 SPEC 把它放進 Phase 2「原型與差分」而非直接實作的理由。

**接手時**：原型與三支量測腳本在 `.claude/tmp/`（`bench_lex.sh`／`diff_lex.sh`／`prof_lex.sh`），
worktree 若已被清掉，用 `git worktree add` 重建再套同一組替換即可。
🔴 **`bench` 的 payload 生成必須是 O(n)**（`sprintf("%*s")`＋`gsub`）——初版用逐字元累加造字串，
量到的是測具自己，主委已踩過一次。

- 🔴 **`scripts/_gate_lex.sh` 不在 `govb1_scope.manifest` allow** ⇒ commit 須帶 OOE trailer；
  它是**共用控制流**（`gate_check.sh` 的 PreToolUse hook 每次工具呼叫都走它；命中高風險 (b)）
  ⇒ 走完整管線，規格已存在：`docs/GOVB0_B3R_LEXER_SPEC.md`（**唯讀**）。
- 🔴 **不得只因「比較快」就把原型落地**：SPEC Task 2.1 的出口是 C-1～C-5 **全數通過**，
  C-5 未過 ⇒ Phase 3 不得開始。落一個「快 2.6 倍但仍不達標」的版本，
  只會讓下一手誤以為這件事做完了——那是本 epic 一路在治的病。

## ✅ 本 session 已交付（2026-08-10～11，皆兩家 `RECONCILE-STAMP APPROVED`）

| 站 | 收斂檔（`reconcile_stamps_check` 皆 rc=0） | 輪數 | 🔴 未閉合 |
|---|---|---|---|
| 2.5 `B-25` | `…/20260810-govb25-x-review-r6/synth.md` | 7 輪 33 條 | 八條殘留，含「判準資料化」整項未做 |
| 2.6 `B-37` | `…/20260810-govb37-x-review-r5/synth.md` | 5 輪 18 條 | 六條殘留，含票級統計與強制機制兩項未交付 |
| 2.7 前半 | `…/20260807-govb1-b1-review-r6/`、`…/20260809-govb1-b4-review-r4/` | 1 輪 | — |
| 2.7 後半 | `…/20260810-govb1-b4-consult-r1/`、`…/20260810-govb1-b4-review-r3/` | 1 consult＋3 review＋2 stamp | 五條殘留（見下） |

**三票皆不得宣稱閉合。** 站 2.7 後半交付的**只有階段 2**，該批之整體狀態一律看
`docs/GOVERNANCE_EXECUTION_ORDER.md` 的 `governance-batch-status` block，**本檔不重述**。

> 🔴 本節刻意不把批次識別碼與狀態值寫在同一行——主委 2026-08-11 在此處**又被自己建的偵測器擋下一次**
> （`HANDOFF.md:44` 與 `白話說明/治理待辦總覽.md:32`，這是第二次）。機制正常運作。

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
