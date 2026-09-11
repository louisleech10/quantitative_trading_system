# VERDICTGATE consult R1 — GROK

task-id: 20260911-VERDICTGATE-X-CONSULT-R1
family: grok
brief: `handoffs/20260911-VERDICTGATE-RECON-BRIEF.md`
findings-round: R1

## Verdict：需修補後派工

主委 F1–F4／F6–F10 核心成立；F5「無法機械解析／0 份三值」須收窄。G-1→G-2→G-6 為前置鏈；G-3 若做成 G-7 式 warn-only 會空轉。必答 1–7 皆有立場與碼證。

## 被當成事實的未驗證假設（§0）

| 假設 | 標記 | 判定 | 理由 |
|---|---|---|---|
| 範本三值 Verdict 可由範本強制 ⇒ 實際 0 份照用 | brief assumed | **半成立** | SPLITUNIFY **批次** code-review 27 份三值前綴＝0；但全庫 628 份 review 有 152 份三值前綴；空 `## Verdict`+次行結論仍可兩行解析 |
| Verdict「不是機械可解析」＝結構上抓不到 | F5 措辭 | **推翻（措辭）** | 問題是開放詞彙＋未入 audit，不是「沒有 Verdict 行」 |
| G-3 trailer 會擋 cx_run 委員交件 | 主委未查 | **不成立** | `cx_run.sh` 無 `git commit`；只寫 `handoffs/` |
| Ticket-Batch 與 Governance-Scope 互斥 | 主委未查 | **不成立** | 同 trailer 段多 key，`git interpret-trailers --parse` 兩行皆出 |

---

## 必答 1：F1–F10

| # | 立場 | 碼證 |
|---|---|---|
| **F1** | **同意** | `scripts/gate.sh:784-805`：`case "${task_id}" in *-impl-b[0-9]*-*)` 內才呼叫 `review_quorum_check.sh` |
| **F2** | **同意** | audit 之 SPLITUNIFY `committee_dispatch` task_id 僅 CONSULT／REVIEW／STAMP／CONFIRM，**無** `impl-b`；`git log --grep=splitunify` 作者皆主委直寫 |
| **F3** | **同意** | `review_quorum_check.sh:27-57` 只掃 `committee_dispatch`＋task_id 尾碼家族去重，不開產出檔、不讀 Verdict |
| **F4** | **同意** | 例：`handoffs/20260911-splitunify-b3-review-r1-codex.md` `Verdict：不可進 B3：CODEX-R1-P1-01…`；同票仍有 B4 review；receipt `handoffs/run_receipts/splitunify-attribution-audit-20260911.txt` |
| **F5** | **同意核心、推翻過寬措辭** | 見 GROK-R1-P1-01：批次三值＝0／空標題 13／14 屬實；「無法解析」與「全專案 0 份三值」不成立 |
| **F6** | **同意** | `grep -c '"verdict":' .claude/gate/audit.log` → **0**（鬆散 `verdict` 字樣只出現在 `cmd_head` 散文，非欄位） |
| **F7** | **同意** | `completeness_check.sh:1-7` 設計＝來源 heading ID ⊆ 綜合檔；附錄逐字保留 ⇒ ID 恆在 |
| **F8** | **同意** | `reconcile_cluster_attribution_check.sh:5-12` 明寫恆 rc=0；`:24` `cut -c1-70`；實跑 stamp 檔多行「附錄斷言: （找不到）」仍 rc=0 |
| **F9** | **同意（依主委＋commit，本輪未重跑投影）** | `539431fc` 訊息載明投影把使用者設定靜默換成 1；本輪未獨立重跑用例 |
| **F10** | **同意** | 閉合確認至 B7 才出現；`scripts/` 無強制 `brief-kind: closure` 與 G-2 連動 |

---

## 必答 2：「我沒查」三條

### ① GAP-3／EVTLABEL 是否也有「不可進卻跨批」

**有。** 且比「同批內多輪修到 CLOSED 再進」更乾淨的跨批例在 EVTLABEL／GAP3D2。

| 票 | 阻擋 | 下一批仍開 | 時序證據 |
|---|---|---|---|
| **EVTLABEL B1→B2** | `handoffs/20260910-evtlabel-b1-review-r1-codex.md`：`Verdict：需修補後派工（…可進 B2 前不得帶著兩項 P1）`；**無** B1-R2 | B2-REVIEW-R1 | audit：B1 `debt_clear` `2026-09-10T08:18:26Z` → B2 `committee_round_open` `09:49:44Z`；`completeness_rc=0` |
| **EVTLABEL B3→B4** | grok：`需修補後派工（不可直接進 Task 3.4–3.7）` | B4-REVIEW-R1 | B3 `debt_clear` `13:26:59Z` → B4 open `13:28:41Z` |
| **GAP3D2 B3→B4** | codex：「目前**不可進 B-D4**」；grok：「**不可直接進 B-D4**」 | B4 存在 | 產出檔字面＋後續 B4 review 檔 |

**補強／否證觀測（勿與上表混）：** 經典 `20260821-gap3-b2` 在 R2 codex 寫「不可進三家 RECONCILE-STAMP」後，**先有 R3 寫四條 CLOSED**（12:37）再出現 B3 review（13:39）——此例是「多輪修到可進」而非「帶著不可進硬跨」。G-2 基準紅燈應用 EVTLABEL／GAP3D2／SPLITUNIFY，勿把已閉合的 gap3-b2 R2 當假陽性。

### ② pre-commit trailer 對 cx_run 執行端 commit 是否相容

**相容——因為路徑不相交。** `grep 'git commit\|git add\|git push' scripts/cx_run.sh` → 空；產出契約為 `handoffs/*`（`cx_run.sh:242`）。委員 headless 交件只觸 `completeness_check --single`，不走 `scripts/git_hooks/commit-msg`。G-3 的 `Ticket-Batch` 擋的是**實作者／主委**對 `momentum/ api/ frontend/src/` 的 commit，不擋委員交件。

### ③ Ticket-Batch 與 Governance-Scope 同段可否解析

**可。** 實跑：

```text
printf '%s\n' 'feat: demo' '' 'Governance-Scope: out-of-epic test' 'Ticket-Batch: VERDICTGATE-B1' \
  | git interpret-trailers --parse
# → Governance-Scope: out-of-epic test
# → Ticket-Batch: VERDICTGATE-B1
```

`govb1_final_gate.sh`／`gov_check.sh` 用 `%(trailers:key=Governance-Scope,...)` **按 key** 取；新 key 不佔 Scope 值空間。失敗模式＝寫進非最末 trailer 段（與既有 Scope 踩坑同形），不是「兩 key 不能共存」。另：現行 `commit-msg` 對 G-7 已是 `g7_trailer_precheck.sh || true`（warn-only，2026-09-05）——見必答 4／GROK-R1-P0-01。

---

## 必答 3：G-2 還有沒有第三條必經路？

除「派下一批 review」＋「pre-commit」外，實作者／主委仍可走、且這兩處抓不到的路：

1. **`debt_clear` 後再開下一批 review**——只驗 completeness／lock，**不讀 Verdict**（EVTLABEL B1→B2 audit：`completeness_rc=0` 後直接 B2 open）。若 G-2 只掛在「派 review」而不掛在 `debt_clear`／`committee_round_open`，主委可先清債再派。
2. **`git commit --no-verify`**——整段跳過 pre-commit（含未來 Ticket-Batch）。
3. **`git push --no-verify` 或 `GOVERNANCE_SKIP_PREPUSH=1`**——`scripts/git_hooks/pre-push:16-18` 明示逃生口。
4. **主委直寫生產碼且從不 `dispatch`（F2）**——連「派下一批 review」閘都不會被問到，除非 pre-commit／pre-push 強制 `Ticket-Batch`。

**不算第三條必經的：** 純 `git push` 不新 commit（只推舊物件）；委員隔離 worktree commit（本 repo 慣例主委統一入主線）。

---

## 必答 4：誰擋主委不領 `--impl-self`？`--no-verify` 有無第二層？

**現況：沒有人擋。** `grep -n 'impl-self' scripts/*.sh` → 空（G-3 提案尚未落地）。不領 token ⇒ F1 路徑不觸發（F2）。現行 pre-commit 無 batch trailer；commit-msg 的 G-7 為 **`|| true` warn-only**。

`--no-verify` 之後：

| 層 | 現況 | 對 G-3 的含義 |
|---|---|---|
| commit-msg / pre-commit | 可 `--no-verify` 全跳 | 僅 pre-commit 不足 |
| pre-push → `gov_check --fast` | 可 `--no-verify` 或 `GOVERNANCE_SKIP_PREPUSH=1` | 若 pre-push **不**複驗 Ticket-Batch／batch token，第二層也不存在 |
| 遠端 | 本專案已無 CI；私有＋免費 branch protection 不強制 | **無法**防蓄意繞過 |

結論：G-3 要「不論哪家」成立，至少 **pre-commit 硬擋 + pre-push 同判準複驗**；且不得抄 G-7 的 `|| true`。蓄意雙 `--no-verify` 在現架構下**擋不住**（見必答 7）。

---

## 必答 5：G-4「斷言首 20 字」可被怎樣繞過？最強可落地判準？

主委原文：「決議列必須含該 finding **斷言首 20 字之逐字引用**」。

| 繞過 | 強度 |
|---|---|
| 引用前 20 字，決議寫無關處置（「已知／不修／另議」） | **高** |
| 只引用附錄斷言的無害前綴，避開真正缺陷子句 | **高** |
| ID 只在附錄、不進群集表（F7 現況仍 PASS） | **高** |
| `cut -c` 位元組切斷中文（F8）造成比對假「找不到」或假匹配 | **中**（改 Python UTF-8 字元可修） |

**最強可落地（仍承認語意上限）：**

1. 每個來源 ID **必須**出現在群集表 `| … | <ID> |` 列（非附錄任意處）；
2. 該列含附錄 `**斷言**` 經 NFKC 後首 20 **Unicode 字元**逐字引用；
3. 同列必有 disposition token 封閉集：`CLOSED|OPEN|DEFERRED|OUT-OF-SCOPE`（或與 G-5 殘留表鍵交叉）；
4. `attribution_check` **rc≠0** 才准 `debt_clear`。

**做不到：** 判斷「決議是否真的修掉該缺陷」（主委已列範圍外）——20 字引用＋enum 只能防「沒對到句／沒標處置」，不能防「對到句但假修」。

---

## 必答 6：G-1–G-6 切批

| 批 | 內容 | 前置理由 |
|---|---|---|
| **B1** | **G-1** `VERDICT:` 封閉集＋`register-output` 寫 audit | 無此則 G-2／G-6 無讀點 |
| **B2** | **G-2** 觸發改為「下一批 review／round_open／debt_clear 前」讀 `blocked:` | 依 B1 |
| **B3** | **G-6** `brief-kind: closure` 與 `closed` 解擋連動 | 依 B1+B2 |
| **B4** | **G-3** `--impl-self`＋`Ticket-Batch` **硬擋**（commit-msg＋pre-push 複驗；禁 `|| true`） | 依 B2（token／批號語意） |
| **B5** | **G-4** 群集表列 ID＋20 字元引用＋attribution rc≠0；**G-5** 延後→§E／Task | 可與 B4 平行，但不依賴 G-3 |

前置：**G-1**。無 G-1，G-2 只能繼續猜開放中文 Verdict。

---

## 必答 7：哪一條「現階段完全不可能」？

**（A）語意層「決議是否真處理了 finding」**——主委已寫；同意。理由：無獨立可執行 oracle 對每個 finding 自動重放缺陷；不是不方便，是判定函數不存在。

**（B）在無遠端強制的前提下，防蓄意 `commit --no-verify` + `push --no-verify`／`GOVERNANCE_SKIP_PREPUSH=1`**——本專案已刪 CI、私有免費無生效 branch protection；本地 hook **定義上**可被跳過。G-3 能做的上限＝擋粗心／擋預設路徑，不是擋蓄意。把「防蓄意」寫進本票 ACCEPT 會永遠無法收案。

其餘 G-1–G-6 **都可能**（機械契約＋閘），不是不可能。

---

## GROK-R1-P0-01

**斷言**: 若 G-3 的 `Ticket-Batch` 檢查做成與現行 G-7 相同的 `g7_trailer_precheck.sh || true`（warn-only），則「主委也須領權限／無 trailer 拒 commit」在預設路徑上不會擋任何 commit。

**碼證**: `scripts/git_hooks/commit-msg:19-27`（2026-09-05 使用者裁定 G-7 不擋；`|| true`）；`grep -n 'impl-self' scripts/*.sh` → 空。RECHECK: `sed -n '19,28p' scripts/git_hooks/commit-msg`。

**來源摘要**: scripts/git_hooks/commit-msg#828326ffb754

[BLOCKING] 信心度=High。修法：Ticket-Batch／batch-token 檢查必須硬失敗；並在 `pre-push` 用同一判準複驗。不可複製 G-7 warn-only 先例。

## GROK-R1-P1-01

**斷言**: F5「Verdict 不是機械可解析／範本三值沒有任何一份照用」對 SPLITUNIFY **批次** code-review 的「三值＝0」成立，但把病灶說成「結構上無法解析」或暗示全語料 0 份三值則過寬——全庫 628 份 `*-review-*-{codex,composer,grok}.md` 中 490 份有同名 Verdict 行、152 份值以三值前綴開頭；批次 SPLITUNIFY 27 份三值＝0、空標題 13。

**碼證**: awk 掃描（本輪）：`files=628 structured=490 three_value_prefix=152`；`batch_only n=27 empty=13 three=0`。空標題例與次行結論：`handoffs/20260821-gap3-b2-review-r3-codex.md`（`## Verdict` 後次行「四條 CLOSED…」）。真病灶＝開放詞彙＋F6 未入 audit。RECHECK: 重跑同 awk。

**來源摘要**: handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574

[MAJOR] 信心度=High。修法：G-1 仍必要；SPEC／偵察措辭改為「無封閉 enum／未入 audit」，勿寫「無法解析」。兩行 `## Verdict`+本文可作過渡 parser，但不得代替封閉 `VERDICT:` 契約。

## GROK-R1-P1-02

**斷言**: EVTLABEL 在至少一家寫「需修補後派工／不可直接進」且無閉合輪的情況下，`debt_clear`（completeness_rc=0）後仍開啟下一批 review——證實跨批漏洞不限 SPLITUNIFY。

**碼證**: B1 codex Verdict「可進 B2 前不得帶著兩項 P1」且僅 r1；audit B1 `debt_clear` `08:18:26Z` → B2 `round_open` `09:49:44Z`。B3 grok「不可直接進 Task 3.4–3.7」→ B4 open `13:28:41Z`（B3 clear `13:26:59Z`）。RECHECK: `grep EVTLABEL-B[1234] .claude/gate/audit.log`。

**來源摘要**: handoffs/20260910-evtlabel-b1-review-r1-codex.md#b9ed8b3c1419

[MAJOR] 信心度=High。修法：G-2 觸發點須含 `committee_round_open`／`debt_clear` 前讀前批最新 `blocked:`；上線前對 EVTLABEL／GAP3D2／SPLITUNIFY 建基準（哪些歷史 round 會變紅）。

## GROK-R1-P1-03

**斷言**: G-2 若只掛「派下一批 review」＋「pre-commit」，仍可被 `debt_clear`→再開 review、以及雙 `--no-verify`／`GOVERNANCE_SKIP_PREPUSH` 繞過。

**碼證**: EVTLABEL B1→B2 audit 路徑（上）；`scripts/git_hooks/pre-push:16-18` `GOVERNANCE_SKIP_PREPUSH=1`；檔頭自承 `git push --no-verify` 可繞。RECHECK: 讀 pre-push 檔頭與 EVTLABEL audit 序。

**來源摘要**: scripts/git_hooks/pre-push#5c9ec7a78e59

[MAJOR] 信心度=High。修法：G-2 讀裁決掛在 round_open／debt_clear；G-3 在 pre-push 複驗；文件誠實寫「防粗心不防蓄意」。

## GROK-R1-P1-04

**斷言**: G-4「斷言首 20 字逐字引用」可被「引用正確前綴、決議內容無關」繞過；最強機械上限是「群集表必列 ID + 20 Unicode 字元引用 + disposition 封閉 token + attribution rc≠0」，仍不能驗證語意修復。

**碼證**: 主委版 G-4 原文；F7 completeness 只驗 ID 在檔；F8 attribution 恆 rc=0。RECHECK: 讀 `handoffs/20260911-VERDICTGATE-RECON-claude.md` §G-4 與 `reconcile_cluster_attribution_check.sh:5-12`。

**來源摘要**: handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574

[MAJOR] 信心度=High。修法：落地上述四件套；語意正確性維持範圍外（與必答 7）。

## GROK-R1-P2-01

**斷言**: 經典 GAP-3（20260821-b2）R2「不可進」之後存在 R3 CLOSED，再進 B3——若 G-2 基準不加「僅統計無後續 closed 的 blocked」，會把已閉合輪誤打成跨批假陽性。

**碼證**: `handoffs/20260821-gap3-b2-review-r2-codex.md`「不可進三家 RECONCILE-STAMP」；`...-r3-codex.md`「四條 CLOSED…可進三家 RECONCILE-STAMP」mtime 早於 b3-review-r1。RECHECK: `ls -lt handoffs/20260821-gap3-b2-review-r*.md handoffs/20260821-gap3-b3-review-r1-*.md`。

**來源摘要**: handoffs/20260821-gap3-b2-review-r2-codex.md#ba3c8dd08f01

[MINOR] 信心度=High。修法：G-2 判定用主委已寫的「blocked 且該家尚無後續 closed」；基準表分開「真跨批」與「多輪後閉合」。

## GROK-R1-P2-02

**斷言**: `Ticket-Batch` 與 `Governance-Scope` 可在同一 trailer 段共存並被 git 原生解析；cx_run 委員路徑不 commit，故 G-3 trailer 不威脅委員交件相容性。

**碼證**: 本輪 `git interpret-trailers --parse` 兩 key 皆出；`grep 'git commit' scripts/cx_run.sh` → 空。RECHECK: 重跑 interpret-trailers 示範。

**來源摘要**: scripts/git_hooks/commit-msg#828326ffb754

[MINOR] 信心度=High。修法：G-3 文件寫明「兩 trailer 同最末段」；驗收加「錯段⇒解析空⇒拒」反例。

---

ASSUMPTIONS_VERIFIED: F1 gate case 行；F2/F6 audit 實查；F3 quorum 腳本；F5 全庫+SPLITUNIFY 批次計數；F8 腳本頭+實跑 rc=0；EVTLABEL／GAP3D2 跨批；trailer 共存；cx_run 無 commit；G-7 warn-only；impl-self 未落地。
TESTS_RUN: awk 計數 Verdict（628/490/152；batch 27/0/13）；`grep -c '"verdict":' .claude/gate/audit.log`→0；`git interpret-trailers --parse` 雙 trailer；`bash scripts/reconcile_cluster_attribution_check.sh` 對 stamp 檔 rc=0；audit 時間序 EVTLABEL B1–B4。
FAILURES_SEEN: 初用 `python3 - <<'PY'` 掃 628 檔觸發分類器掛起～190s，改 awk 後完成；已 kill 該背景行程。
SCOPE_CHANGES: none（唯讀偵察）。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_OUTPUT: handoffs/20260911-verdictgate-x-consult-r1-grok.md
STATUS: DONE
