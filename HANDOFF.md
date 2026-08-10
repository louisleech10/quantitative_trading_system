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
- **實測**（codex，B3R SPEC C-5 要求 quoted 100K<2s／500K<5s）：100K `real=1.26s`；**500K `timeout 20 → rc=124`**。
- **修法方向（主委已讀碼，未實作）**：兩個 pass 皆為串流轉換 ⇒ 改 `printf` 逐段輸出取代 `out = out c`；
  兩 pass 拆成兩個 awk 以管線相接（現行 pass2 吃 pass1 的 `out` 變數）；
  heredoc 行掃描改 `substr(src, line_start, j-line_start)` 批次取代逐字元。
- 🔴 **`scripts/_gate_lex.sh` 不在 `govb1_scope.manifest` allow** ⇒ commit 須帶 OOE trailer；
  它是**共用控制流**（命中高風險 (b)）⇒ 走完整管線，規格已存在：`docs/GOVB0_B3R_LEXER_SPEC.md`（**唯讀**）。

## ✅ 本 session 已交付（2026-08-10～11，皆兩家 `RECONCILE-STAMP APPROVED`）

| 站 | 收斂檔（`reconcile_stamps_check` 皆 rc=0） | 輪數 | 🔴 未閉合 |
|---|---|---|---|
| 2.5 `B-25` | `…/20260810-govb25-x-review-r6/synth.md` | 7 輪 33 條 | 八條殘留，含「判準資料化」整項未做 |
| 2.6 `B-37` | `…/20260810-govb37-x-review-r5/synth.md` | 5 輪 18 條 | 六條殘留，含票級統計與強制機制兩項未交付 |
| 2.7 前半 | `…/20260807-govb1-b1-review-r6/`、`…/20260809-govb1-b4-review-r4/` | 1 輪 | — |
| 2.7 後半 | `…/20260810-govb1-b4-consult-r1/`、`…/20260810-govb1-b4-review-r3/` | 1 consult＋3 review＋2 stamp | 五條殘留（見下） |

**三票皆不得宣稱閉合。** `b4` **僅階段 2 收案，不得宣稱整批完成**。

## 🔴 未修的活缺口

- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；`TODO:822` 第 1 條 ASSERT 字面不成立。
  修它須動 `_B45_HARNESS` ⇒ 觸窗守衛 ⇒ 需解凍 ⇒ `票 B-49` 須 CLOSED，而其閉合條件第 4 項**須使用者改 `governance_roles.json`**。
  🔴 **OOE 通道救不了**：`_MSG_PARSE_MARKERS` 含 `"Governance-Scope"`，窗守衛結構上禁解析 commit 訊息。
- `R-13` 未列舉之 Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`（同型旗標空值不一致）
- `票 B-54`（新開）：戳記行之 64 位 hex 由委員手抄 ⇒ 本 session 實際掉字一次
- `B3R` O(n) scanner 未交付（`CODEX-R8-P1-03`）⇒ 不得宣稱達標
- `票 B-15` 誤擋在 `B7` 之後仍存在（`printf`／`find`／`ls`／`gate.sh` 自身）⇒ GOVB0 `B4` Task 2.3/2.4
- `gate_check` 對真派工放行：process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c` ⇒ GOVB0 `B4`
- `票 B-50` 流程面永久標記為跳步；`票 B-31` 對外只能說「產出端已有檢查點」
- `plain_docs_sync_check.sh` catch-all 回空字串 ⇒ 新增說明檔預設不受監看
- `R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit

## ⚠ 操作紀律（踩過的坑，一律照做）

- 🔴 **補洞前先問「舊行為在這個輸入上是什麼」**。本 session 為修一條 P2 而開了一個 P1
  （三版本對照 `擋 → 放行 → 擋`）。**補洞比洞更危險**。
- 🔴 **凍結測試檔會以原始碼字面錨定生產腳本的行**（`_CR_BK_FULL_EXTRACT` 等）⇒ 那些行等於被連帶凍結，
  **改對了也會紅**。解法＝保留該行逐字、只換它的輸入。
- 🔴 **委員戳記主委不得代寫**——sha 掉字要重派，不得自己補。
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
