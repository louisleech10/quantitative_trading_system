# VERDICTGATE consult R1 — COMPOSER

task-id: 20260911-VERDICTGATE-X-CONSULT-R1  
family: COMPOSER  
brief: `handoffs/20260911-VERDICTGATE-RECON-BRIEF.md`  
findings-round: R1

## 被當成事實的未驗證假設（§0）

| 假設 | 作者標記 | 判定 | 理由 |
|---|---|---|---|
| 範本三值 Verdict 可強制委員照用 | assumed（brief L28） | **未成立** | 621 份 `*-review-*` 僅 152 份含三值字面；`VERDICT:` 機械行僅 8 份（見必答 1／F5） |
| G-3 pre-commit trailer 會擋委員 cx_run 交件 | assumed（主委「未查」） | **未成立** | `cx_run.sh` 全程不 `git commit`；委員只寫 `handoffs/*.md`（見必答 2②） |
| G-7 只解析最末段 ⇒ `Ticket-Batch` 與 `Governance-Scope` 互斥 | assumed（主委「未查」） | **部分未成立** | git trailer 可同段多 key；風險在**寫錯段**而非 key 衝突（見必答 2③） |

---

## 必答 1：F1–F10 立場

| 事實 | 立場 | 碼證摘要 |
|---|---|---|
| **F1** 閘只在 `*-impl-b<N>-<家族>` 派工觸發 | **同意** | `scripts/gate.sh:784-804` `case "${task_id}" in *-impl-b[0-9]*-*)` 內才呼叫 `review_quorum_check.sh` |
| **F2** 主委自任實作從未跑 F1 | **同意** | `rg 'splitunify.*impl-b' .claude/gate/audit.log` → 0；SPLITUNIFY 全批 commit 為主委直寫（`git log --grep=splitunify`） |
| **F3** 閘只驗派工留痕不讀裁決 | **同意** | `review_quorum_check.sh:1-57` 檔頭＋主迴圈只數 `committee_dispatch` 家族去重 |
| **F4** SPLITUNIFY 邊界「不可進」仍跨批 | **同意** | 例：`handoffs/20260911-splitunify-b2-review-r3-codex.md`「不可進 B2c」；audit `20260911-splitunify-b2c` 審派工在後 |
| **F5** Verdict 非機械可解析（封閉三值） | **同意核心、補強範圍** | 全庫 621 份 review：`canonical_three_value=152`、`empty_verdict_heading=93`、`VERDICT:` 行僅 8 份；**非**僅 SPLITUNIFY 14 份。寬鬆 regex 可抓「不可進／可進」但仍無封閉 enum |
| **F6** Verdict 未寫 audit | **同意** | `rg '"verdict' .claude/gate/audit.log` → 0 |
| **F7** completeness 只驗 ID 在檔、附錄逐字保留 ⇒ 恆過 | **同意** | `completeness_check.sh:1-7` 設計＝來源 ID 全在綜合檔；不依群集表列 |
| **F8** attribution_check 恆 rc=0＋`cut -c` 中文壞 | **同意** | `reconcile_cluster_attribution_check.sh:5-12` 明寫恆 rc=0；`:24` `cut -c1-70`；實跑 synth 多行「附錄斷言: （找不到）」 |
| **F9** 「列入 Bx」延後即消失 | **同意** | 主委版＋`539431fc`；本輪未獨立重跑投影用例 |
| **F10** 閉合確認輪無機制 | **同意** | B7 才首次 `feedback_finding_closure_reverify`；無 `brief-kind: closure` 硬閘 |

---

## 必答 2：「我沒查」三條

### ① GAP-3／EVTLABEL「不可進卻跨批」

**有，且 audit 可對時序。**

| 票 | 輪次／ID | 阻擋原文 | 下一批（仍開） | audit 時序 |
|---|---|---|---|---|
| GAP3D2 | `20260905-GAP3D2-B3-REVIEW-R1` | codex L2「目前**不可進 B-D4**」；grok「**不可直接進 B-D4**」 | `20260905-GAP3D2-B4-REVIEW-R1` | B3 `debt_clear` `2026-09-04T23:54:22Z` → B4 `committee_round_open` `2026-09-05T11:07:21Z` |
| EVTLABEL | `20260910-EVTLABEL-B3-REVIEW-R1` | grok「**不可直接進 Task 3.4–3.7**」「修完 P1 **再進 B4**」 | `20260910-EVTLABEL-B4-REVIEW-R1` | B3 收斂後 B4 `committee_round_open` `2026-09-10T13:28:41Z` |

根因同 F1–F3：跨的是 **review 批次／impl 派工**，不是「讀到 blocked 就拒 `gate.sh dispatch`」。

### ② pre-commit trailer 與 cx_run 相容性

**相容（委員路徑不 commit）。** `cx_run.sh` 無 `git commit`（`rg 'git commit' scripts/cx_run.sh` → 0）；產出由 agent 寫檔＋`completeness_check --single`。現行 `scripts/git_hooks/pre-commit` 只跑 `verification_claim_check.py` 掃 staged markdown，**尚無** `Ticket-Batch` 檢查。G-3 若上線，主要卡 **主委／實作者 commit**，不卡委員 headless 交件；風險在主委用 worktree 直接 commit 生產碼而無 trailer。

### ③ `Ticket-Batch` 與 `Governance-Scope` 同段可解析性

**可共存，須同 trailer block。** `govb1_final_gate.sh:418-422`：`%(trailers:key=Governance-Scope,...)` 只讀訊息最末 trailer 段；同段可有多個 key（git 原生）。`Governance-Scope` 重複 key 以 `0x1F` 拒（`:445-451`）。`Ticket-Batch` 為**新 key**，不與 Scope 值空間衝突；失敗模式＝把 `Ticket-Batch` 寫進 body 中段（同 Scope 踩坑）⇒ 解析為空 ⇒ fail-closed。`gov_check.sh` G-7 整段已停用（`:377-382`），不影響本票新 trailer 設計。

---

## 必答 3：G-2 第三條必經路？

除「派下一批 review」＋「pre-commit（提案）」外，**實作者必經且兩處抓不到**的路：

1. **主委直寫不經 `*-impl-b*` 派工**（F2）——整條 quorum／verdict 閘跳過。  
2. **`git commit --no-verify`**——繞過 pre-commit（`gov_check.sh:316` 自承）。  
3. **`GOVERNANCE_SKIP_PREPUSH=1` 或 `git push --no-verify`**——繞過 pre-push（`pre-push:7-8,16-18`）。  
4. **`committee_run` → review 收斂 → `debt_clear`**——只跑 completeness／lock，**不讀 Verdict**（audit 可見 SPLITUNIFY／GAP3 在「不可進」後仍 `debt_clear` 再開下一批 review）。  
5. **歷史 worktree／手動 cp 產物進 repo**——若未經 `register-output`＋格式閘，audit 無 verdict 欄位可追。

**不能算「必經」的**：`git push` 不 commit 新裁決（只推舊 commit）；委員在隔離 worktree commit（若存在）——本 repo 慣例是主委統一 commit。

---

## 必答 4：G-3 `--impl-self` 誰擋主委？

**現況：幾乎沒人擋。** `--impl-self` 是提案、repo 內 `rg '--impl-self' scripts/` → 0。主委不領 impl token 時 F1 根本不觸發（F2）。pre-commit 現只驗 claim-object，**無** batch token／trailer。`--no-verify` 無第二層；pre-push `--fast` 也不驗 batch token。唯一軟性：`gate.sh` `_check_open_debt`（`:540`）擋有 OPEN 債時發 dispatch——與 verdict 無關。G-3 若只做 pre-commit、不做 push 端複驗，主委仍可用 `--no-verify` 一次繞過。

---

## 必答 5：G-4 逐字 20 字可被怎樣繞過？

**提案原文**（主委版 G-4）：「決議列必須含該 finding **斷言首 20 字之逐字引用**」。

| 繞過 | 可行性 |
|---|---|
| 引用 20 字但決議實質無關（例：只抄「Task 1.3 驗證條件」不談修補） | **高** |
| 改寫斷言用同義句、附錄仍舊 20 字 substring | **中**——若只比附錄首句 20 字，決議可抄「對的一半」 |
| 群集表根本未列 ID、只在附錄出現 | **高（現況）**——F7 仍 PASS |
| UTF-8 第 20 **字元** vs **位元組** 切斷 | **中**——F8 已示 `cut -c` 坑；須 Python 字元索引 |

**建議最強可落地判準**：群集表 `| … | <ID> |` 必列 ID ＋決議列含附錄 `**斷言**` 首 20 **Unicode 字元**（NFKC 後）＋決議須含 disposition token（`CLOSED|OPEN|延後|另票`）之一。  
**做不到**：判斷決議是否真的修掉 finding（主委 scope 外）——需 LLM／人工，非現階段機械。

---

## 必答 6：G-1–G-6 切批順序

| 批 | 內容 | 前置 |
|---|---|---|
| **B1** | **G-1** Verdict 契約＋`register-output` 解析寫 audit | 無——**一切下游依賴可解析裁決** |
| **B2** | **G-2** 改觸發點讀 `blocked:`／`closed:` | B1 |
| **B3** | **G-6** closure brief-kind 制度化 | B1＋B2（否則 closed 無意義） |
| **B4** | **G-3** `--impl-self`＋pre-commit `Ticket-Batch`（含 push 端 mirror 或接受 `--no-verify` 殘留） | B2 判定邏輯 |
| **B5** | **G-4** 群集表列＋20 字＋attribution rc≠0 | B1 ID 穩定；可與 B3 並行但收斂依賴 B1 |
| **B6** | **G-5** 延後字樣↔TODO §E | 可並行 B4–B5；`debt_clear` 前必須 |

---

## 必答 7：六條中「現階段完全不可能」者

**G-1–G-6 皆可機械化，無一條屬「完全不可能」。**  
與票相關、**確實不可能**的是主委 scope 外那層：**「決議語意是否真的處理 finding」**——需要理解修補內容與斷言的 entailment，無 ground-truth oracle，亦無法在委員產出當下用決定性演算法判定（不同於 G-4 字串匹配）。  
**不是**「不方便」：G-4 上限已明示；再往上只能人工或 LLM adjudication，與「機械閘」目標矛盾。

---

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

## Verdict：需修補後派工（偵察結論可收斂；G-1→G-2 順序與 review 觸發點須寫入 SPEC）

**停輪自評**: 必答 1–7 有立場；1–2 附證據；至少補強 F5 全庫計數、推翻「cx_run 會被 trailer 擋」、補 GAP-3／EVTLABEL 跨批實例。

---

STATUS: DONE
