# Handoff

REF:handoffs/reconcile/20260810-govb1-b4-review-r3/synth.md
REF:handoffs/reconcile/20260810-govb1-b4-consult-r1/synth.md
<!-- 站 4 之收斂檔 handoffs/reconcile/20260811-govb3r-x-review-r1/synth.md 尚未取得委員戳記，
     依上方規則**不得**列入 REF:。取得 RECONCILE-STAMP APPROVED 後再補。 -->

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

## 🔴 站 4 — `B3R` 詞法層超線性修法（序 `050`）

🔴 **先讀 `docs/GOV_B3R_C5_RATIONALE_AMENDMENT.md` 再談這一站**：使用者質疑後查證確認，
C-5 的秒數門檻**沒有可驗證的威脅模型**（詞法層只收 Bash 指令字串；稽核 39,861 筆平均 75 bytes；
gate 與 hook **都沒有逾時機制**）⇒ 不得宣稱本輪修掉 fail-open。
且實作是 **O(n·√n)**（此路線的下界），**不是** SPEC §B.1 寫的 O(n)。

> 批次／票的狀態值一律看 `docs/GOVERNANCE_EXECUTION_ORDER.md` 的 generated block，本節不重述。
> （本節刻意不把識別碼與狀態詞寫在同一行——主委在本檔已被自己建的偵測器擋下四次。）

**完整收據＝`docs/GOV_B3R_PHASE3_RECEIPT.md`**（根因實驗、修法、四組差分、mutation、效能矩陣、殘留）。
Phase 2 收據＝`docs/GOV_B3R_PHASE2_RECEIPT.md`，其 profiling 結論**已被 Phase 3 用受控實驗推翻**。

一句話版：真根因是 **BWK awk 的 `substr()` 成本正比於來源字串總長**
（不是字串累加、也不是函式呼叫次數）⇒ 改成「視窗存取＋批次跳躍＋分段 gsub」。
C-5 三條全過：100K 最差 0.19s（門檻 2s）、500K 最差 **1.01s**（門檻 5s，舊版 29.43s）、4MB 有界。
行為不變之證據：95 條語料＋fuzz 短 12000＋fuzz 長 run 12000＋heredoc 20 例，**皆逐位元組全同**；
mutation 8/8，其中對照組「**關掉快路徑輸出完全不變**」＝快路徑與逐字路徑等價之直接證明。

雙家 review r1 已收：收斂檔 `handoffs/reconcile/20260811-govb3r-x-review-r1/synth.md`（委員債已銷）。
兩家 Verdict 分歧（codex 要修／composer 放行）⇒ 依碼證採 codex 較嚴版，三條 findings 全數處置。
新測試 `tests/governance/test_gate_lex_b3r_c5.py`（**26 passed**）；全套 **1422 passed / 0 failed**。
🔴 fuzz 抓到 233/12000 例差異（Phase 2 的機械改寫誤改前導空行語義），**已還原**並加回歸樁。

🔴 **本輪踩到、已做成機制的三個坑**（都不是知識問題，是「沒有出口」的問題）：
① 變異版可能**無窮迴圈**（`win_at_boundary`、空字串保護）⇒ 一律硬 timeout，「卡住」＝可比對的具體回傳值。
② `subprocess` 的 timeout **只殺直接子程序**，`awk` 孫程序會變孤兒空轉（實測 5 個各吃 70% CPU，
   把全套由 8 分鐘拖成 27 分鐘、並使 C-6 canary 誤紅 201.5ms）⇒ 改 `start_new_session` ＋ `killpg`。
③ 既有兩份語料是**逐行檔**，塞不下跨行 heredoc ⇒ 視窗重置守衛在 CI 永遠測不到
   ⇒ 手寫 10 條 heredoc 案例併入 mutation 語料。


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
- `B3R` 的重寫已進主樹，但雙家 review 尚未戳記 ⇒ 對外只能說「已交付、待戳記」
- `票 B-56`：`_gate_lex_extract_inners`／`_extract_cmdsubs` 仍逐字迴圈（500K 15.3s）；
  修它須先判定 `j = i + RLENGTH` 未用 RSTART 是否為缺陷 ⇒ 屬行為變更，不得夾帶進效能批
- `票 B-57`：`parse_heredoc_delim` 的 `rest = substr(s, pos)` 全尾切 ⇒ heredoc 密集 500K **434 秒**
  （**優先序低**：查證後「慢＝危險」的前提不成立，見 `docs/GOV_B3R_C5_RATIONALE_AMENDMENT.md` §D）
- `票 B-58`：前導空行被丟棄（`"⏎⏎a"` 等同 `"a"`）；是否為缺陷**未判定**，
  回歸樁釘的是「與舊版一致」而非「這行為是對的」
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
