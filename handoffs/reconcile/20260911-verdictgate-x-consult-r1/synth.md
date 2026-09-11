# Reconcile — 20260911-verdictgate-x-consult-r1

**來源** 20260911-verdictgate-x-consult-r1-codex.md, 20260911-verdictgate-x-consult-r1-composer.md, 20260911-verdictgate-x-consult-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**Verdict**：需修補後合併——偵察結論可收斂；主委版 G-1～G-6 **三處被推翻或改落點**（見 V1／V2／V4），依修正後版本起草 SPEC。

主委版被打掉的三件事（先講，因為它們改變 SPEC 骨架）：
①**F5 講過頭**：我用 14 份 SPLITUNIFY 檔宣稱「範本三值沒有任何一份照用」；全庫 628 份中 490 份有 Verdict 行、152 份用三值前綴（grok／composer 各自實跑）。真病灶＝**開放詞彙＋從未入 audit**，不是「結構上無法解析」。
②**G-3 落點按字面不可行**：pre-commit **拿不到 commit 訊息**，只有 commit-msg 拿得到；而 commit-msg 的 G-7 依使用者 2026-09-05 裁定是 warn-only（`|| true`）——照我原案做，「無 trailer 拒 commit」在預設路徑上一個 commit 都擋不住。
③**跨批漏洞不是 SPLITUNIFY 偶發**：GAP-3（`GAP3D2-B3` codex 不可進 B-D4 → `debt_clear` → B4 開輪）與 EVTLABEL（B1 codex、B3 grok）**同型**——第三條主路＝`debt_clear` → 下一批 `committee_round_open`，我原案沒列。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **V1 G-1 Verdict 契約是一切前置，且 `closed` 須逐 finding 綁原提出方** | P0 | COMPOSER-R1-P0-01、GROK-R1-P1-01、COMPOSER-R1-P1-02、CODEX-R1-P1-02（四條獨立） | **採納，並修正 F5 敘述**。無 G-1 則 G-2 沒有穩定輸入（全庫僅 8 份含 `VERDICT:` 行）。契約改為**兩層**：整份輸出級 `VERDICT: proceed｜blocked`；逐 finding 級 `BLOCKED-BY: <ID,…>`（blocked 時必填）與閉合輪之 `CLOSED: <ID,…>`——**每個 CLOSED 的 ID 必須是同一家自己提出的**（前綴家族相符），否則 register-output 拒收。值集住 `scripts/governance_verdicts.json`；`register-output` 解析並寫入 audit `committee_output.verdict`／`blocked_by`／`closed`；解析失敗 ⇒ fail-closed 拒收。範本同步改為此格式。 |
| **V2 G-3 落點改到 commit-msg，且必須與 warn-only 的 G-7 分離** | P0 | CODEX-R1-P0-01、GROK-R1-P0-01 | **採納，落點改**。`Ticket-Batch` 檢查掛 **commit-msg**、放在 `exec` 之前、**fail-closed**（依使用者 2026-09-11「不論哪家執行都要觸發」）；與 G-7 的 `|| true` 是兩條獨立呼叫，**不共用**回傳。GROK-R1-P2-02 已實證 `Ticket-Batch` 與 `Governance-Scope` 同段共存可被 `git interpret-trailers` 原生解析；cx_run 委員路徑不 commit ⇒ 對委員交件無相容性風險。CODEX-R1-P0-01 之「cx_run 無委員 commit 可驗相容」與此一致。 |
| **V3 G-2 觸發點加第三處：`debt_clear`→下一批開輪；且只計「無後續 closed 的 blocked」** | P1 | COMPOSER-R1-P1-01、GROK-R1-P1-02、GROK-R1-P1-03、GROK-R1-P2-01（四條獨立） | **採納**。G-2 判定改為在 **`committee_run.sh` 開任何新輪**時執行（同 root、批次號更大 ⇒ 讀前一批最新輪之 audit verdict）；`gate.sh dispatch` 派 review 同判。判定只計「某家 `blocked` 且該家對同一 ID **無後續** `CLOSED`」——否則 GAP-3 那種 R2 不可進→R3 CLOSED→進 B3 的合法序列會被誤打（GROK-R1-P2-01）。上線前先跑一次**全庫回溯**產出既有跨批清單當基準（只准變短）。 |
| **V4 `--no-verify`／`GOVERNANCE_SKIP_PREPUSH` 無第二層；CI 已由使用者刪除** | P1 | CODEX-R1-P1-03、COMPOSER-R1-P2-01、GROK-R1-P1-03（三條獨立） | **部分採納＋一條具名殘留（使用者裁定類）**。做得到的：①`GOVERNANCE_SKIP_PREPUSH=1` 與 commit-msg 之逃生口一律**寫 audit 留痕**（現在是靜默）；②`gov_check --fast` 加一段：偵測 HEAD 之 commit 訊息**無** `Ticket-Batch` 卻含生產碼 ⇒ 拒 push（補 `git commit --no-verify` 這條）。做不到的：`git push --no-verify` 在**客戶端不可能擋**（git 設計），唯一兜底是伺服端／CI——**CI 於 2026-08-13 由使用者裁定全數刪除**（pre-push 檔頭逐字），屬「使用者裁定」類殘留，SPEC §N 具名。 |
| **V5 G-4 之逐字引用可被「抄對字、答錯題」繞過；語意閉合不可能** | P2 | CODEX-R1-P2-04、COMPOSER-R1-P2-02、GROK-R1-P1-04（三條獨立） | **採納三家一致的上限**：群集表**必列**每個 ID（不在表列＝紅）＋斷言前 20 個 Unicode 字元逐字引用（比 20 bytes；解決中文截斷）＋**處置 token 封閉集合** `採納｜部分採納｜駁回｜延後→<TODO §E ID 或 Task N.N>`（`延後→` 之目標必須存在，即 G-5 併入此）＋`attribution_check` 從報表改成閘（rc≠0 擋 `debt_clear`）。**「決議是否真的處理了 finding」之語意驗證：現階段完全不可能**（三家一致）⇒ SPEC §N 具名，理由＝需自然語言蘊涵判定，無機械判準。 |
| **V6 主委「沒查的」兩條已由委員實查關閉** | — | GROK-R1-P2-02 | trailer 同段共存 OK；cx_run 不 commit。記錄。 |

### 切批（依三家必答 6 之共識）
B1＝V1（契約＋register-output＋範本）→ B2＝V3（開輪閘＋全庫回溯基準）→ B3＝V2＋V4 做得到的部分（commit-msg 閘＋逃生口留痕＋gov_check 段）→ B4＝V5（收斂閘）。V1 是前置，其餘不得先做。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01
**斷言**：G3 將 commit-message trailer 驗證放在 pre-commit 按字面不可行；cx_run 也沒有委員執行端 commit 可被該檢查相容性驗證。 **碼證**：pre-commit 無 message 參數；commit-msg:18-29 才取得 msg 且 g7 以 || true warn-only；cx_run.sh:154-161、513-524 僅 selfcheck/audit emit，沒有 git commit。 **來源摘要**：scripts/git_hooks/pre-commit#eae29414b4f9；scripts/git_hooks/commit-msg#828326ffb754；scripts/cx_run.sh#d7aa1dc7bf09。正文：改為 commit-msg 解析 Ticket-Batch，pre-commit 驗 staged token；否則 G3 無法 fail-closed。
## CODEX-R1-P1-02
**斷言**：G1/G6 的 VERDICT: closed 是整份輸出級狀態，未綁定逐 finding ID、closure 證據與原提出方重跑結果；可能以一個 closed 釋放多個 blocked。 **碼證**：主委版 G1 僅列 closed/blocked:<ID,ID>，G6 只以 closed 解除 G2；現 audit 無 verdict 欄。 **來源摘要**：handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574；scripts/review_quorum_check.sh#a1c6ced819a。正文：改成每一 finding 的 closed:<ID>、proposer、closure round、evidence digest 四元組，G2 只消費逐項 closed。
## CODEX-R1-P1-03
**斷言**：G2/G3 只加 local dispatch/pre-commit 不能涵蓋 push acceptance；現行 pre-push 明示 --no-verify 與環境逃生口，且無 remote/CI fail-closed 兜底。 **碼證**：pre-push:7-18、46-53；git config --get core.hooksPath→scripts/git_hooks；.github 無 workflow 檔。 **來源摘要**：scripts/git_hooks/pre-push#5c9ec7a78e59；handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574。正文：在 G2 驗收中加入 commit-msg、pre-push、remote/CI 三邊界；若只允許 local 威脅模型，必須把「蓄意 bypass 不防」標為非 fail-closed。
## CODEX-R1-P2-04
**斷言**：G4 的首 20 字引用會碰撞、可引用附錄複製文字或不相關決議，不能單獨證明 finding 已處置。 **碼證**：主委版 G4:46-49 的機械條件只有 ID 所在列與首 20 字 quote；completeness single:1556-1579 仍未驗決議對應。 **來源摘要**：handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574；scripts/completeness_check.sh#c76692e041da。正文：quote 僅保留為人讀索引，機檢再綁 canonical claim digest；語意 closure 維持原提出方人工驗證。
ASSUMPTIONS_VERIFIED: GAP3D2/EVTLABEL review 檔、F1-F10 腳本證據、trailer 共存 parser 均已讀／實跑；未改 code、SPEC、TODO 或 data_cache。
TESTS_RUN: rg 全 review glob blank Verdict=111、verdict-like=681；rg verdict .claude/gate/audit.log→0；git interpret-trailers --parse 同段雙 trailer→各輸出一行；無 full governance/momentum Analysis。
FAILURES_SEEN: none；未宣稱已修 production。
SCOPE_CHANGES: 僅新增本交接檔；未越界，保留既有 dirty worktree。
NUMERIC_OR_SCHEMA_IMPACT: 未改輸出；提案需新增 per-finding verdict/closure 與 Ticket-Batch 欄位，屬後續 schema 變更。
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-x-consult-r1-codex.md
STATUS: DONE
## COMPOSER-R1-P0-01

**斷言**: 在無 G-1 前，任何 G-2「讀 blocked:」實作都無穩定輸入——全庫 621 份 review 僅 8 份含 `VERDICT:` 行，範本三值字面僅 152 份，其餘為「可進 B2c／不可收票」等開放語法。

**碼證**: `rg -l 'review' handoffs/*-review-*-{codex,composer,grok}.md | wc -l` → 621；`rg -c 'VERDICT:' …` 非零檔 → 8；`rg -l '可派工|需修補後派工|有根本缺陷需重作' …` → 152。RECHECK: 重跑上述三條 `rg`／`wc`。

**來源摘要**: templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#a8f3c2d1e9b0

[BLOCKING] 信心度=High。G-2 必須排在 G-1 之後；否則閘要麼永遠解析失敗，要麼退回人工讀 `## Verdict` 散文（重現 F4）。

---

## COMPOSER-R1-P1-01

**斷言**: `debt_clear`／`committee_run` 開下一批 review 時不讀裁決，是 GAP-3／EVTLABEL 與 SPLITUNIFY 同型的第三條主路——不是歷史偶發。

**碼證**: GAP3 `20260905-GAP3D2-B3-REVIEW-R1` codex「不可進 B-D4」→ audit seq 3121 `debt_clear` → seq 3167 B4 `committee_round_open`。EVTLABEL B3 grok「不可直接進 Task 3.4–3.7」→ B4 review `2026-09-10T13:28:41Z`。RECHECK: `rg 'GAP3D2-B4-REVIEW-R1' .claude/gate/audit.log`；讀 `handoffs/20260910-evtlabel-b3-review-r1-grok.md:23-27`。

**來源摘要**: handoffs/20260905-gap3d2-b3-review-r1-codex.md#f611d85c1526

[MAJOR] 信心度=High。G-2 觸發點必含 **`committee_run`／`gate.sh dispatch` 派 review 前**讀前批 `VERDICT:`，不能只改 impl-b。

---

## COMPOSER-R1-P1-02

**斷言**: 主委版 F5 樣本量偏小——「14 份 SPLITUNIFY」不足以支撐「範本自 2026-08 起規定三值 ⇒ 可強制」；全庫 93 份仍為空 `## Verdict` 標題。

**碼證**: `rg -l '^## Verdict[：: ]*$' handoffs/*-review-*-{codex,composer,grok}.md | wc -l` → 93。主委 F5 只 grep `20260911-splitunify-*`。RECHECK: 全庫空標題計數。

**來源摘要**: handoffs/20260911-VERDICTGATE-RECON-claude.md#126e1684e574

[MAJOR] 信心度=High。反證「範本＝機械契約」假設；G-1 需 `register-output` fail-closed，不能只改範本 prose。

---

## COMPOSER-R1-P2-01

**斷言**: G-3 若只上 pre-commit、不在 push／CI 複驗，`--no-verify` 仍讓主委在「blocked」狀態推生產碼——與使用者「不論哪家」精神缺口。

**碼證**: `scripts/git_hooks/pre-push:7-8` 明寫 `--no-verify` 可繞；`gov_check.sh:316` 同邊界；現 pre-commit 無 batch 檢查。RECHECK: 讀兩檔上述行。

**來源摘要**: scripts/gov_check.sh#571db4dbe8ac

[MAJOR] 信心度=High。G-3 設計應寫明：pre-commit＋pre-push 同檢查，或接受 R-G3-NOVERIFY-1 具名殘留。

---

## COMPOSER-R1-P2-02

**斷言**: G-4「20 字逐字引用」可被「抄對字、答錯題」繞過；最強機械上限是 disposition token＋群集必列，不是語意閉合。

**碼證**: 見必答 5 表；`reconcile_cluster_attribution_check.sh` 不驗決議內容（恆 rc=0）。RECHECK: 在 synth 決議列只貼斷言 20 字寫「CLOSED」不附修補，現閘無法拒。

**來源摘要**: scripts/reconcile_cluster_attribution_check.sh#044e19643d5a

[MINOR] 信心度=High。接受 G-4 為「掉項＋歸屬」閘，勿宣稱「裁決品質」已機械保證。

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
