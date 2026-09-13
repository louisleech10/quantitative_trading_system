# DOCROT X-CONSULT R3 — grok

task-id: 20260912-DOCROT-X-CONSULT-R3  
family: grok  
findings-round: R3  
brief: handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md  
note: consult——寫出可驗收 TODO 與判準；禁改碼。synth／HANDOFF 為診斷輸入，非 gating。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 證據 |
|---|---|---|---|
| review-r1 十群＝三家原文處置，主委未加新機制 | fact-verified | **成立** | `handoffs/reconcile/20260912-docrot-x-review-r1/synth.md` L11–23；歸戶 22/22 |
| D1 寫入時硬擋覆蓋率＝0%（兩處 `--dupes` 皆 `\|\| true`） | fact-verified | **成立** | `scripts/gov_check.sh:271-273` 註解「刻意不進 `_docbad`」＋`\|\| true`；`scripts/spec_xref_hook.sh` ③ 段同型不改 rc |
| docs 200；觸發名 132／不命中 68；無 DOCROT SPEC/TODO | fact-verified | **成立** | `ls docs/*.md \| wc -l`＝200；名含 SPEC\|TODO\|PLAN\|RECON＝133；`grep -i docrot`＝空 |
| 「文檔多輪根因＝R1 的 D1／D2；機械化後輪數就降」 | assumed | **不充分** | 見 P0-03：review-r1 已抓第三根因「決議→實作無可核對 TODO」；主委 R2→碼即再犯 |
| 「只餵 current block＋diff ⇒ 討論聚焦碼／架構」 | assumed | **必要但不充分** | 見 P2-01：diff 內仍可爭字面；須強制碼證指向碼符號 |
| 「scripts／templates 改動可不經 SPEC 直接實作」 | assumed | **成立（限本輪）** | 見必答 6：≤8 條、既有檔、三問過關；另開 `docs/DOCROT_*` 會再製病灶 |

## 被當成事實的未驗證假設（§0）

- 「把 D1／D2 閘化後輪數下降」→ **assumption**；主委無票前後對照。本輪改寫為：閘化 D1／D2 **且** consult→TODO→實作可核對，才有資格談輪數下降（P0-03）。
- 「輸入隔離＝聚焦碼／架構」→ **assumption**；隔離只擋歷史重審，不擋 diff 內字面戰（P2-01）。
- 「warn-only 仍屬 R2 遷移序、故可維持」→ **對主委已否證**（review-r1 G5）；遷移序只保留在 hook 層，gov_check 1b 必須升 fail-closed（P0-01）。

---

## 必答總覽（1–6）

### 1. 五項逐項裁定（採納／改寫／撤回）

| # | 主委做了什麼 | 裁定 | 改寫後逐字規格（若改寫）／撤回理由 |
|---|---|---|---|
| 1 | `brief_conformance_check.sh` 拒派含 `new_brief.sh` 骨架佔位字面 | **改寫（保留輔助）** | 保留 PLACEHOLDERS 硬擋。宣稱改為：「只擋 new_brief 骨架原樣派出；不涵蓋手寫『整份檔』；合法正文引用骨架字面會誤拒——誤拒時改寫引用或 VERIFY-EXEMPT」。**另必須**完成 E8 Phase A：`completeness_check.sh` 拒收 HISTORY 區 anchor（見 Task 1.4）。不得宣稱「E3 已完成」。 |
| 2 | `spec_count_audit.py --dupes` 三 regex 多行重複 | **改寫（取最窄）** | `dupes()` **只**掃 `_RE_TOTAL_ITEMS`（`共\s*<數>\s*條`）。`_RE_NUM_UNIT`／`_RE_COUNT_ASSERT` 退出 `dupes()`（仍可留在 `--list`／`--check`）。不得宣稱「＝窄 F2 本體已含多行」而不寫清形態。 |
| 3 | `dupes()` 在首個 `HISTORY-BEGIN` `break` | **撤回** | 無任何一家提過；構造反例：HISTORY 後活文雙「共 7 條」→現行 stderr 空、interval-skip 則報 `[1,7]`。改為 BEGIN–END **區間 skip**，禁 `break`（Task 1.1）。 |
| 4 | 警告層併入 `spec_xref_hook.sh`、不新增 settings 條目 | **採納** | E2 要三層、未指定併入哪支；併入既有 hook 符合「不新增第 9 支全域 hook」。hook 層維持 warn-only；硬擋改由 gov_check 1b（Task 1.3）。 |
| 5 | F1 只做 `docs/SPLITUNIFY_SPEC.D-002.md` 即宣告收斂 | **改寫** | 改標「D-002 單檔試點」，刪「F1 已到收斂點」。下一張中大票＝SPLITUNIFY b9（仍 D-002）⇒ 試點適用；成效用必答 3 之機械句量，不達再議擴檔（不開新 epic）。 |

撤回者（#3 之 break）主委實作時即 revert 該控制流。

### 2. TODO（Task N.N；≤8；每條過三問）

| Task | 改哪個既有檔 | 擋哪個根因 | 不做再燒幾輪（引數據） | 做完怎麼機械量 | 驗收指令與預期 rc | mutation（改壞會紅） |
|---|---|---|---|---|---|---|
| **1.1** `dupes()` 區間 skip | `scripts/spec_count_audit.py` 之 `dupes()`（約 L117–118）：刪 `break`；遇 `HISTORY-BEGIN` 設 `in_hist=1`／`HISTORY-END` 清零；`in_hist` 或 `## 沿革` 行 `continue`（鏡像 `obligation_block_check.sh` L72–73） | D2 誤報＋活文漏掃（第三根因之實作缺陷） | R12 活文收縮後若 HISTORY 後仍有活文，break 會永久漏 D1；每輪可再燒 1 次「漏掃／誤報」往返 | 構造檔：活前＋HISTORY＋活後同「共 N 條」→`--dupes` stderr 含兩活文行號 | `venv/bin/python scripts/spec_count_audit.py --dupes <構造檔>` → stderr 含兩活文行號、**不含** HISTORY 內行；rc 見 1.3 | 復原 `break` ⇒「HISTORY 後活文仍報」測試紅 |
| **1.2** `dupes()` 收窄至 `_RE_TOTAL_ITEMS` | 同檔 `dupes()` 內 `for rx in (...)` 改為只 `_RE_TOTAL_ITEMS` | D1 窄化（避免三 regex 誤報拖垮 fail-closed） | 授權三 regex 無基線時，升擋門會全庫紅／被迫退回 warn → 再燒 ≥1 consult | 對 `docs/GAP3_EVENT_UX_SPEC.md`：可報「共 N 條」雙落點；「五維度」等多行非「共 N 條」**不再**由 `--dupes` 報 | `python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md` → 若有「共 N 條」雙落點則報；stderr 無「五維度」類 | 加回 `_RE_NUM_UNIT` 入 dupes ⇒ 收窄測試紅 |
| **1.3** gov_check 1b dupes fail-closed | `scripts/gov_check.sh` 段 1b（約 L271–273）：對本次 diff 之 `docs/*.md`，跑 `--dupes`；**活文區**命中（stdout/stderr 非空或改 `--dupes` 回傳命中數）⇒ `_docbad+=1`；去掉「刻意不進 `_docbad`」與盲 `\|\| true`。hook 層不變 | D1 硬擋覆蓋 0%→>0%（寫入／commit 掃描路徑） | 主委已示範 warn 無效（review-r1 G5）；維持 warn＝D1 每張中大票可再燒多輪「改一處漏一處」（D-002 R8–R12 同型未降） | `gov_check` 對含雙「共 N 條」之改動 docs → 段 1b rc≠0 | 造臨時 docs fixture 雙「共 3 條」納入 diff 掃描（或 pytest harness）→ `bash scripts/gov_check.sh --fast` 段 1b 失敗；單一真相源 → 段 1b 該檔不因 dupes 失敗 | 復原 `\|\| true` 且不進 `_docbad` ⇒ 新 pytest 紅；既有 `test_dupes_is_warn_only_never_blocks` 若斷言 CLI rc=0 則**改釘 hook 層**，勿與 1b 混為一談 |
| **1.4** completeness 拒 HISTORY anchor | `scripts/completeness_check.sh`：對每個 finding 的 `**碼證**`／`**來源摘要**` 抽取 `path:line`（及 `` `path:line` ``）；若 path 存在且 line ∈ 該檔 `HISTORY-BEGIN`‥`HISTORY-END`（或該行在 `## 沿革` 節內）⇒ FAIL。無 path:line 則本條不觸發（不新增語意閘） | D2／E3／E8 Phase A（審查輸入隔離之機械牙） | D-002 R11＝12、R12＝13 **全部**針對前版修法（R1 synth）；缺此牙則輸入隔離只靠紀律 | 構造 finding：`**碼證**: docs/X.md:L` 且 L 在 HISTORY 內 → `completeness_check.sh --single` rc≠0；L 在活文 → rc=0（其他欄合規時） | `bash scripts/completeness_check.sh --single <構造交件> --family grok` → HISTORY 行號 rc≠0 | 刪區間判定 ⇒ HISTORY-anchor 測試紅 |
| **1.5** 「三家共同結論」須 audit 佐證 | `scripts/verification_claim_check.py`：`commit_msg` 路徑若命中 `三家共同結論|三家一致落地`（封閉字面，不做語意），則要求 `.claude/gate/audit.log` 同 task-id 存在 `committee_family_result` 或 `committee_output`（≥派工 roster 家數），否則 rc≠0；允許既有 `VERIFY-EXEMPT:` | 第三根因：未審實作冒充三家背書（review-r1 G2） | 本輪已發生（`3e009126` 主旨）；每再犯一次＝整輪審碼＋consult（本 DOCROT 已多燒 review-r1＋本 r3） | `venv/bin/python scripts/verification_claim_check.py --commit-msg <含該字面且無 audit 之訊息檔>` → **rc≠0**；有齊套 audit 或 EXEMPT → rc=0 | 同上；對照：現行同訊息 **rc=0**（本輪已實跑） | 拿掉字面或跳過 audit 查 ⇒ 新測試紅 |
| **1.6** 範本：碼證須能指向碼／架構 | `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 輸出格式段：在「碼證」條下新增逐字——「主張涉及行為／架構／數值者，`**碼證**` 必須含 `path:符號` 或 `path:函式` 或可重跑命令＋stdout 摘要；僅引文檔字面差異且無行為影響者最高 P3，並標 `doc-literal-only`」。`new_brief.sh` consult/review 臂加一行同文 pointer | 使用者目標：討論聚焦碼／架構（assumed 2 之補洞） | R11/R12 全文重審字面＝每輪 +12～13 條；字面戰不降則中大票可再 >10 輪 | 下輪 brief 含該句；缺碼路徑之架構向 P0/P1 由主委／completeness 人審拒收（本條不新增腳本） | `grep -F 'doc-literal-only' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md scripts/new_brief.sh` → 命中 | 刪該句 ⇒ grep 驗收紅 |
| **1.7** F1 試點標籤＋成效句入單一權威 | 只改收斂／交接指標：下一張 reconcile synth 或本 consult 收斂檔寫必答 3 之成效句；HANDOFF 只留 pointer。**不改** `docs/SPLITUNIFY_SPEC.D-002.md` HISTORY 區 | G7：成效不可觀測 | 無基線／及格線 ⇒ 下張票結束又爭論「有沒有比較好」＝再燒 1 consult | 成效句出現在單一權威檔；HANDOFF 無複述分子分母 | `grep -n 'doc.friction.ratio\|活文多落點占比' handoffs/reconcile/*/synth.md handoffs/20260912-docrot-x-consult-r3-*.md` 在收斂後恰一權威落點 | 兩處全文複述成效句 ⇒ 違反 D1 自指 |
| **1.8** （合併入 1.3 測試）佔位宣稱收窄 | `scripts/brief_conformance_check.sh` 錯誤訊息／檔頭「誠實邊界」與 tests 註解對齊必答 1＃1 之宣稱；**不**擴佔位集 | 輔助 E3；防過度宣稱 | 宣稱過寬被審碼輪打回＝再燒 1 輪 | 檔頭／ERROR 文案含「不涵蓋手寫 brief」 | `grep -F '不涵蓋手寫' scripts/brief_conformance_check.sh` → 命中；既有 e3 測試仍綠 | 宣稱改回「手寫零誤擋」⇒ 文案測試或 review 再打回 |

**D3／D4／D5（只答做或不做）**  
- **D3**（語意互斥閘）：**不做**。需語意判斷或新對照裝置，違反本輪硬約束；既有 xref「只驗存在」自白仍成立，列具名殘留。  
- **D4**（停輪機械化）：**不做（本輪）**。不擋 D1／D2／第三根因之寫入路徑；待 TODO 1.1–1.5 落地且下一張票仍輪數不降再議。  
- **D5**（跨檔狀態複寫）：**不做**。屬看板／權威指標習慣；使用者已把白話合併列待裁定。  

**禁止項自檢**：無新 epic、無新腳本檔、無語意閘、無全庫 registry；只改既有 `scripts/*`／`templates/*`／測試。

### 3. 成效判準（可機械計算的一句）

**活文摩擦比 `doc_friction_ratio`**＝（該輪 `handoffs/reconcile/<ticket>-review-rN/synth.md` 附錄中，滿足下列任一之 canonical finding 數）／（該輪附錄 canonical finding 總數）：  
(a) `**碼證**` 或 `**來源摘要**` 之 `path:line` 落在標的 SPEC 的 `HISTORY-BEGIN`‥`HISTORY-END`；或  
(b) `**斷言**` 命中封閉字面 `多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張`。  

- **資料來源**：各輪 `synth.md` 附錄 `## <FAMILY>-R*-P*-*` 區塊之 `**斷言**`／`**碼證**`／`**來源摘要**` 欄。  
- **基線（D-002 R1–R12）**：R11＝12/12＝**1.00**、R12＝13/13＝**1.00**（R1 synth 定論：兩輪全部針對前版修法）；R8–R12 合計 finding＝73 為晚輪負載基線。  
- **及格線**：下一張中大票之 **review-r1 與 review-r2** 兩輪 `doc_friction_ratio` **均 ≤ 0.30**（且每輪 finding 總數 ≤ R12 的 13 之 1.5 倍＝20，防「比例好看但絕對量爆」）。不達 ⇒ 本 TODO 裁定失敗，只准回到「是否要最小 token 表」討論，**禁止**同時開新 epic。

### 4. 哪些結構讓 finding 落在字面？改哪段範本？

| 結構 | 為何推向字面戰 | 逐字改法 |
|---|---|---|
| 舊審查契約「先完整讀 SPEC/TODO/PLAN」 | 歷史與現行同檔 ⇒ 重審已作廢主張（R11/R12） | 已改輸入邊界；**仍缺** completeness 牙（Task 1.4） |
| finding 四欄未要求碼符號 | 委員可用「兩處用詞不同」當 P0，無需行為差 | 在 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`「輸出格式」之碼證條下插入必答 2 Task 1.6 逐字句 |
| synth 群集表以「斷言前 20 字」歸戶 | 激勵把爭議寫進斷言開頭的措辭，而非函式名 | **本輪不改歸戶腳本**（禁新機制）；改靠 Task 1.6 把架構向碼證綁到 `path:函式` |
| brief「必答」若只問文檔句是否一致 | 答題型審查 | consult/review brief 之必答須含至少一題「指出行為／呼叫點／數值閘」；`new_brief.sh` 在「## 必答」骨架加一句：`（至少一題須指向 path:函式或驗收命令，不得全為用詞差異）` |

### 5. F1 範圍與下一張中大票

下一張中大票＝**SPLITUNIFY b9 實作（`D-002`）**（HANDOFF 現況）。因此 F1 的 D-002 試點**適用**，不必先擴到別票 SPEC。若 b9 再開工前插入其他中大票，則該票開場須先做同型活文收縮，或明示本成效句不適用——二選一寫進該票 brief。

### 6. 可以進實作嗎？

- **可以進本 consult 之 Task 1.1–1.5（及 1.6–1.8）實作**——前提：本輪三家 reconcile 對「根因被 TODO 涵蓋」一致答是；主委**只照 TODO 表**改既有檔，禁止再塞表外機制。  
- **不可**進 SPLITUNIFY b9 生產碼／不可再擴 DOCROT 機制，直到 1.1–1.5 驗收綠。  
- **不需**另開 `docs/DOCROT_SPEC.md`：改動全在 `scripts/`＋`templates/`＋治理測試，本檔 TODO 表＝最小 TODO；另開 SPEC 會複製 D1。  
- **BLOCKING 必須先修（相對「宣稱 DOCROT 已落地」）**：P0-01、P0-02、P0-03 對應 Task 1.3／1.4／本 TODO 紀律。

---

## Findings（canonical 四欄）

## GROK-R3-P0-01

**斷言**: 現行 `gov_check.sh` 段 1b 對 `--dupes` 命中不進 `_docbad` 且 `|| true`，使 D1 在改動掃描路徑上的硬擋覆蓋率仍為 0%。

**碼證**: `scripts/gov_check.sh:271-273` 逐字「刻意**不進 _docbad**」＋`python3 scripts/spec_count_audit.py --dupes "${f}" >/dev/null || true`；`scripts/spec_xref_hook.sh` ③ 段同型不改 rc。RECHECK: `sed -n '268,275p' scripts/gov_check.sh`。

**來源摘要**: scripts/gov_check.sh#4b333ce050ff;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[BLOCKING] 信心度=High。review-r1 G5 三家已採納「最小擋門＝1b fail-closed」；主委試點仍停在 warn。**修法**：Task 1.3——命中計入 `_docbad`；hook 維持 warn。**可行性**：段 1b 迴圈與 `_docbad`／`_gc_fail` 已存在；只改分支。pytest：雙「共 N 條」→ 1b rc≠0。

## GROK-R3-P0-02

**斷言**: `completeness_check.sh` 仍不拒收落在 `HISTORY-BEGIN`‥`HISTORY-END` 的 finding anchor，E8 Phase A 後半未做，E3 輸入隔離無機械牙。

**碼證**: `grep -n 'HISTORY-BEGIN' scripts/completeness_check.sh` → **0 命中**（本輪實跑）；對照 `scripts/new_brief.sh:66` 與範本已寫「落在歷史段者不受理」但無執行端。RECHECK: 同上 grep；構造 `--single` 交件含 HISTORY 行號。

**來源摘要**: scripts/completeness_check.sh#c76692e041da;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[BLOCKING] 信心度=High。R2 E3／E8A 與 review-r1 G3（本家 P0）已定案。**修法**：Task 1.4——解析碼證／來源摘要之 `path:line`，落 HISTORY 區間即 FAIL。**可行性**：只讀既有欄位與檔內標記；`obligation_block_check` 已有區間 skip 可鏡像；不新腳本。

## GROK-R3-P0-03

**斷言**: 僅機械化 D1／D2 不足以降低文檔輪數——第三根因是「委員會決議 → 主委實作」之間沒有可核對 TODO，本輪主委 R2→碼即再犯。

**碼證**: review-r1 G1：五項非原文折衷且未開 consult 即 commit（`git log --oneline 44bbd8d3..HEAD` 含 `3e009126`／`ab3508c0`／`68a70342` 等）；`ls docs/ \| grep -i docrot` → 空。R2 程序修正「折衷須 consult」已被繞過。RECHECK: 對讀 review-r1 synth L13；`ls docs/ \| grep -i docrot`。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#70660a69b76f

[BLOCKING] 信心度=High。挑戰 brief assumed「D1／D2 機械化後輪數就降」：**不充分**。**修法**：本 consult 產出之 Task 1.1–1.5 為唯一實作清單；主委禁表外機制；實作後須審碼輪對表驗收。**可行性**：不新 epic；TODO 即契約。

## GROK-R3-P1-01

**斷言**: `dupes()` 在首個 `HISTORY-BEGIN` 使用 `break` 會漏掃其後活文，屬主委自創且有構造反例。

**碼證**: `scripts/spec_count_audit.py:117-118`；構造檔活前 L1「共 7 條」＋HISTORY＋活後 L7「共 7 條」→現行 `--dupes` stderr 空、rc=0；interval-skip 原型回傳 `('共 7 條',[1,7])`。RECHECK: 重跑同構造。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 1.1 區間 skip、禁 break。**可行性**：`obligation_block_check.sh` 已實作同型；加 mutation「HISTORY 後活文仍報」。

## GROK-R3-P1-02

**斷言**: `--dupes` 同時掃三 regex 超出 R2 窄 F2「只數共 N 條」；升 fail-closed 前必須收窄，否則誤報面會逼回 warn。

**碼證**: R2 synth L26「窄 F2（只數『共 N 條』形態）」；`dupes()` L120 `for rx in (_RE_NUM_UNIT, _RE_COUNT_ASSERT, _RE_TOTAL_ITEMS)`；composer 實跑 GAP3 報「五維度」等多行非「共 N 條」。RECHECK: `python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md`。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7

[MAJOR] 信心度=High。硬約束「取最窄能過三問者」。**修法**：Task 1.2 只留 `_RE_TOTAL_ITEMS`。**可行性**：改 for 迴圈一行；測試釘「五維度不報／共 N 條雙落點報」。

## GROK-R3-P1-03

**斷言**: `verification_claim_check.py` 對 commit 主旨「三家共同結論」類背書語現行不擋（rc=0），無法強制 audit 佐證。

**碼證**: `STRONG_POLARITY_RE`（L46–53）無「三家共同結論」；本輪 `printf 'fix(docrot): 落地三家共同結論前兩項…' > /tmp/msg` + `venv/bin/python scripts/verification_claim_check.py --commit-msg /tmp/msg` → **rc=0**。RECHECK: 重跑同命令。

**來源摘要**: scripts/verification_claim_check.py#2fc6b3a0e20c;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 1.5——封閉字面＋audit 家數檢查；允許 EXEMPT。**可行性**：既有 commit_msg 路徑與 committee audit 白名單（L30–41）可复用。

## GROK-R3-P2-01

**斷言**: 只限制審查輸入為 current block＋diff，不足以迫使 finding 指向碼／架構；diff 內字面差異仍可成篇。

**碼證**: 範本已有輸入邊界（`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`），但碼證欄未要求 `path:函式`；D-002 晚輪 findings 多數打修法字面（R1 D4／R12）。RECHECK: 讀範本輸出格式段；對照 R12 synth 附錄。

**來源摘要**: templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#976f11c084b2;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MINOR] 信心度=Medium。**修法**：Task 1.6 範本＋`new_brief.sh` 逐字句；doc-literal-only ≤P3。**可行性**：只改範本字面，無新腳本；執行靠主委拒收＋後續可選機檢。

## GROK-R3-P2-02

**斷言**: 骨架佔位偵測可保留為 E3 輔助，但「對手寫 brief 零誤擋／E3 已完成」宣稱過寬，且不能替代 completeness HISTORY 拒收。

**碼證**: `brief_conformance_check.sh` PLACEHOLDERS 段自承「擋不住手寫 brief 把審查標的寫成整份檔」；review-r1 G8。RECHECK: `sed -n '314,350p' scripts/brief_conformance_check.sh`。

**來源摘要**: scripts/brief_conformance_check.sh#55d4b8162804;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MINOR] 信心度=High。**修法**：必答 1＃1 改寫宣稱＋Task 1.8 文案；主牙仍是 Task 1.4。

---

## §1 必查摘要

1. 矛盾：有（主委「E3／F2 已完成」vs 三家原文缺口）→ P0-02／P1-02  
2. 漏項：有（completeness HISTORY、1b fail-closed、claim 閘）  
3. 不可測：有 → 必答 3 補機械句  
4. quant：無（本輪治理）  
5. 過度工程：無（拒新 epic／新腳本；D3/D4/D5 不做）  
6. OOM：不適用  
7. cache：不適用  
8. API：無  
9. 測試：有（各 Task mutation）  
10. Agent 可執行：有（Task 表到檔：行／函式）  
11. 短命工：無（閘為常設；F1 試點標籤非短命碼）

## 根因是否被 TODO 涵蓋？

**是（本家）**：D1→1.2+1.3；D2／E3→1.1+1.4+1.6；第三根因（決議→實作）→本 TODO 表本身＋1.5 背書閘。D3/D4/D5 明示不做。

---

ASSUMPTIONS_VERIFIED: gov_check 1b `|| true`／不進 `_docbad`；completeness 無 HISTORY-BEGIN 字面；dupes break 構造反例（interval-skip 報 [1,7]、現行空）；commit-msg「三家共同結論」rc=0；docs 200／觸發名 133／無 docrot SPEC；R11/R12 基線依 R1 synth 定論。  
TESTS_RUN: `python3 scripts/spec_count_audit.py --dupes` 構造檔；`venv/bin/python scripts/verification_claim_check.py --commit-msg` → rc=0；`grep HISTORY-BEGIN scripts/completeness_check.sh` → 0；寫檔後將跑 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r3-grok.md --family grok`。  
FAILURES_SEEN: none（本輪唯讀＋產 consult 檔）。  
SCOPE_CHANGES: none（禁改碼；僅本產出檔）。  
NUMERIC_OR_SCHEMA_IMPACT: none。

VERDICT: blocked
BLOCKED-BY: GROK-R3-P0-01,GROK-R3-P0-02,GROK-R3-P0-03
CLOSED:
STATUS: DONE
