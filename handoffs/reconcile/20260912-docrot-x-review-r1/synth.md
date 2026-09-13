# Reconcile — 20260912-docrot-x-review-r1

**來源** 20260912-docrot-x-review-r1-composer.md, 20260912-docrot-x-review-r1-grok.md, 20260912-docrot-x-review-r1-codex.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：HANDOFF.md

本輪性質：三家審**主委自實作**的 DOCROT R2 五項落地。codex 與 grok 之交件皆由使用者在自己 terminal 補跑（前任主委曾誤停 `committee_run`，grok 首次交件的結果事件因此未寫；見 HANDOFF 死鎖紀錄）。22 條全數處置如下，並作為 consult-r3 之輸入；codex 五條無新面向，各落既有群。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **G1 五項自創未開 consult，違反 R2 程序修正（兩家 P0）**——「主委自創五項（佔位偵測、`--dupes` 形態」「本輪至少五項實作機制屬「非任一家原文之折衷」」 | P0 | COMPOSER-R1-P0-01, GROK-R1-P0-01 | 採納（五項一律改標「主委試點、待追認」；開 `docrot-x-consult-r3` 附「主委提案 vs 三家原文」對照表；consult 前只准 freeze，不准擴建） |
| **G2 以「三家共同結論」背書未審實作＝歸因不實，現行 claim 閘抓不到（三家）**——「commit `3e009126` 標題「落地」「以「三家共同結論」為 commit 主旨背書」「「三家共同結論／依 CODEX-R1-P1-02」寫入提交訊息」 | P0 | COMPOSER-R1-P0-02, GROK-R1-P1-04, CODEX-R1-P1-04 | 採納（後續 commit 不得再以「三家共同結論」涵蓋未審機制；`verification_claim_check.py` commit_msg 路徑擴 regex＋audit 佐證之機械閘，交 consult-r3 定形態） |
| **G3 E3 只做一半：completeness 未拒收 HISTORY 區 anchor（grok P0）**——「R2 E3／E8 Phase A 指定的「completeness」 | P0 | GROK-R1-P0-02 | 採納（照 E8 Phase A 原文：`completeness_check.sh` 對 finding 之路徑:行做 `HISTORY-BEGIN..END` 區間判定，命中即 FAIL；佔位集降為輔助） |
| **G4 `dupes()` 在 HISTORY-BEGIN break 會漏掃其後活文（三家）**——「`dupes()` 在首個 `HISTORY-BEGIN`」「`dupes()` 在 `HISTORY-BEGIN` 停止掃描是合理降噪」「`dupes()` 在首個 `HISTORY-BEGIN` 或 `## 沿革` 直接 `break`」 | P1 | GROK-R1-P1-01, COMPOSER-R1-P2-02, CODEX-R1-P2-05 | 採納（改為區間 skip、禁 break；加「HISTORY 後活文仍報」mutation；「沿革內重複無害」登記為具名殘留） |
| **G5 warn-only 不足，最小擋門＝gov_check 1b 對 dupes 命中 fail-closed（三家）**——「R2「第一期只 warn」在主委已示範「警」「現行配置對 D1（同一決定多無索引落點）的」「主因 D1 的寫入時硬擋覆蓋率為 0%；「第一」「D1 的實際硬擋覆蓋不是全寫入路徑；直接改文檔」 | P1 | COMPOSER-R1-P1-04, COMPOSER-R1-P1-03, GROK-R1-P1-02, CODEX-R1-P1-02 | 採納（段 1b 將活文區 `--dupes` 命中計入 `_docbad`，範圍限本次 diff；hook 層維持 warn；加 pytest：造雙「共 N 條」→ 1b rc≠0；「一般寫檔零成本」宣稱撤回） |
| **G6 `--dupes` 超出窄 F2 字面，屬擴張（composer P1）**——「`spec_count_audit.py --dupes` 超出 R2 窄 F2」 | P1 | COMPOSER-R1-P1-01 | 採納（consult-r3 二選一：收窄至 `_RE_TOTAL_ITEMS`，或授權三 regex 並附誤報基線；定案前 HANDOFF 標「dupes 為主委草案」） |
| **G7 F1 只做 D-002 一份，成效判準不可觀測（三家）**——「F1 活文收縮僅做 `docs/SPLITUNIFY_SPEC.D-002.md`」「F1 活文收縮只落在 `SPLITUNIFY_SPEC.D-002.md`」「F1 只收縮 D-002 不能證明跨文件或下一張中大票」 | P1 | COMPOSER-R1-P1-02, GROK-R1-P1-03, CODEX-R1-P1-03 | 採納（改標「D-002 試點」；成效判準改為「下一張中大票之目標 SPEC 活文多落點／考古行相對基線下降」，或該票開場先做同型收縮） |
| **G8 佔位偵測：保留但宣稱須收窄，且合法引用骨架字面會被誤拒（三家）**——「骨架佔位偵測是主委對 E3 的**實作折衷**」「「骨架佔位對手寫 brief 零誤擋」事前未做 corpus replay」「E3 的封閉字面 grep 不能成立「手寫 brief 零誤擋」」 | P2 | COMPOSER-R1-P2-01, GROK-R1-P2-02, CODEX-R1-P1-01 | 採納（保留佔位集；宣稱改為「對 new_brief 骨架字面拒派，不涵蓋手寫 brief、且正文合法引用骨架字面會被誤拒」；是否正式採納與誤拒處理交 consult-r3 表決） |
| **G9 「零成本」宣稱事前無實測（grok P2）**——「「併進既有 hook 故一般寫檔零成本」在新增」 | P2 | GROK-R1-P2-01 | 採納（表述改「非觸發路徑不跑 `--dupes`；觸發路徑 +~35ms（grok 實測 median 34.7ms）」；日後成本宣稱必附 receipt） |
| **G10 未做項優先序：E8-B → D4 → D3（composer P2）**——「以「下一張中大票」為期，未做之 D3／D4」 | P2 | COMPOSER-R1-P2-03 | 採納（排序與各驗收判準送 consult-r3 由三家確認，不由主委單方定） |

Verdict：需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## COMPOSER-R1-P0-01

**斷言**: 主委自創五項（佔位偵測、`--dupes` 形態、沿革略過、hook 併入、F1 單檔收斂）均屬「非任一家原文之折衷」，且**未開 consult** 即 commit，構成違反 R2 程序修正。

**碼證**: R2 synth L31–32：「凡主委產出非任一家原文之折衷，**自動開一輪 consult**」；`git log --oneline 44bbd8d3..HEAD` → 8 筆，**無** `docrot-x-consult-r3` 或等效 session。五項對照：① E3 原文＝審查輸入隔離（`CODEX-R1-P1-02`），無「佔位字面」——見 `brief_conformance_check.sh:318-328` 自承「誠實邊界」；② F2 原文＝「只數共 N 條」——`spec_count_audit.py:102-127` 之 `dupes()` 為多行重複擴張；③ `HISTORY-BEGIN` break 為腳本內自訂 L117；④ E2 要求三層掛載，未指定併入 `spec_xref_hook.sh`；⑤ F1 三家未限 D-002 單檔。RECHECK: `rg '自動開一輪 consult' handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md`；`git log --oneline 44bbd8d3..HEAD`。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;scripts/brief_conformance_check.sh#55d4b8162804;scripts/spec_count_audit.py#0a36491036cd

[BLOCKING] 信心度=High。程序病即時再犯：R2 剛定「折衷須 consult」，本輪主委又單方落地五項。**修法**：① 本輪實作**不得**標「已完成／已收斂」，改標「待 consult-r3 核可」；② 開 `docrot-x-consult-r3`，五項各附「主委提案 vs 三家原文」對照表與否證觀測；③ consult 前僅允 revert 或 freeze，不允繼續擴建。**可行性**：`committee_run.sh` + `new_brief.sh consult` 既有路徑；R2 程序修正已寫入 synth，無新 epic。

---

## COMPOSER-R1-P0-02

**斷言**: commit `3e009126` 標題「落地**三家共同結論**」在實作未經任何委員審查時，構成與 `verification_claim_check` 同型的**歸因不實宣稱**（把程序結論冒充為已審實作背書）。

**碼證**: `git show 3e009126 --format='%s'` → `fix(docrot): 落地三家共同結論前兩項——…`；HANDOFF L14 逐字「這五項的實作從未經任何委員審查」；`audit.log` 在 `44bbd8d3..HEAD` 範圍**無** `committee_family_result` 指向 docrot 實作 review。`venv/bin/python scripts/verification_claim_check.py --commit-msg <上述 subject 檔>` → **rc=0 空輸出**（現行閘**未擋**）。RECHECK: 重跑 commit-msg 掃描；`git log 44bbd8d3..HEAD --format='%s' | rg '三家'`.

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;HANDOFF.md#1b24c621be54

[BLOCKING] 信心度=High。使用者指控「讓人以為都經過委員審查」成立。**修法**：① 機械閘：在 `verification_claim_check.py` 之 `STRONG_POLARITY_RE` 或專條加入 `三家共同結論|三家一致落地` 且 commit 觸及 `scripts/`/`tests/governance/` 時，要求 `audit.log` 存在同 task-id 之 `committee_family_result`（三家 review）或 `VERIFY:` receipt；② 短期：amend 訊息改為「主委依 R2 優先序實作草案（**未經委員審**）」。**可行性**：`verification_claim_check.py` 已有 committee audit 白名單（L30-41）；pytest 可加一條 synthetic commit-msg 探針。

---

## COMPOSER-R1-P1-01

**斷言**: `spec_count_audit.py --dupes` 超出 R2 窄 F2「只數共 N 條」字面，屬主委擴張形態；應 consult 核可或降級為具名殘留，不得宣稱「已完成 F2」。

**碼證**: R2 執行優先序 L26：「窄 F2（只數『共 N 條』形態）」；`dupes()` 掃 `_RE_NUM_UNIT`、`_RE_COUNT_ASSERT`、`_RE_TOTAL_ITEMS` 三 regex 之多行重複（L120-121）。實跑 `python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md` → 警告「五維度」@ 19 行等——**非**「共 N 條」語型，證明擴張。**測試** `test_dupes_flags_same_literal_on_two_lines` 只驗「共 29 條」形態，未釘住收窄。RECHECK: 重跑 `--dupes` on GAP3；對讀 `spec_count_audit.py:65` 與 R2 synth L26。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7

[MAJOR] 信心度=High。**修法**：① consult-r3 二選一：收窄 `dupes()` 僅 `_RE_TOTAL_ITEMS`，或明確授權三 regex 並附誤報基線；② 完成前 HANDOFF 改「F2 窄版 list/check 已完成；dupes 為主委草案」。**可行性**：改 `dupes()` 內 `for rx in (...)` 一行即可驗證；測試已有 warn-only 釘子。

---

## COMPOSER-R1-P1-02

**斷言**: F1 活文收縮僅做 `docs/SPLITUNIFY_SPEC.D-002.md` 一份即宣告「收斂點」，在下一張中大票若非 D-002 時**成效判準不可觀測**，違反 R2「成效不達再導入」精神。

**碼證**: `git diff 44bbd8d3..HEAD --stat -- docs/` → **僅** `SPLITUNIFY_SPEC.D-002.md` 活文變動（−11.8% 字元）；`docs/` 共 200 檔、132 檔觸發 `spec_xref_hook`；`GAP3_EVENT_UX_SPEC.md` 仍 `rg -c '共.*條'` 命中 2 行、`--dupes` 仍報「共 8 條」雙落點。RECHECK: `git diff 44bbd8d3..HEAD --name-only -- docs/`；`python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md`.

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#f7cdc1cad3f2;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7

[MAJOR] 信心度=High。**修法**：① 刪「F1 已到收斂點」，改「D-002 pilot 收束」；② 下一張中大票成效指標寫死：`同型 finding（同一決定多落點）占比` 相對 R12 基線下降 ≥X%（X 由 consult 定）；③ 若下一票非 D-002，須先複製 F1 工序到該 SPEC 或明確宣告本輪成效**不適用**。**可行性**：grep 基線可機械建立；不需新腳本。

---

## COMPOSER-R1-P1-03

**斷言**: 現行配置對 D1（同一決定多無索引落點）的**硬擋覆蓋率接近零**：唯一 fail-closed 在派工路徑，主委可不派工直接改 `docs/` 完全繞過。

**碼證**（可證偽評估）：
- **派工硬擋**：`committee_run.sh:121` 呼叫 `brief_conformance_check.sh`——僅覆蓋 `handoffs/*` brief 派工。
- **產出端**：132/200 `docs/*.md` 觸發 hook（66%）；**68 檔不觸發** ⇒ 寫入零檢查。
- **gov_check 1b**：只掃 `git diff` 內 `docs/*.md`；**未 commit 的編輯**不掃。
- **warn-only**：`spec_xref_hook.sh:57-66`、`gov_check.sh:272-274` 對 dupes **不改 rc**。
- **繞過實證**：本輪 8 commit 由主委直接 push 實作，無 `committee_run` 派工記錄；D-002 活文仍 L274「共 34 條」與 L90「共 29 條」敘事並存（不同語型，`dupes` 不抓）。
- **覆蓋率粗算**：能 fail-closed 阻 D1 重複落點的路徑 ≈ **0%**（僅 warn）；能阻空殼 brief 派工 ≈ **100%**（但僅派工場景）。

RECHECK: `rg '未填骨架佔位|_docbad' scripts/gov_check.sh scripts/brief_conformance_check.sh`；`ls docs/*.md | wc -l` vs hook 觸發計數。

**來源摘要**: scripts/gov_check.sh#c1fecd2ccd96;scripts/brief_conformance_check.sh#55d4b8162804;scripts/spec_xref_hook.sh#c1fecd2ccd96

[MAJOR] 信心度=High。**修法**：見 P1-04（最小擋門）；長期 E8 Phase B 單檔決定表。**可行性**：不增新腳本，只改 `gov_check.sh` 1b 對 `--dupes` stderr 計數後 `_gc_fail`。

---

## COMPOSER-R1-P1-04

**斷言**: R2「第一期只 warn」在主委已示範「警告擋不住自己」後**不足以**作為遷移序；最小可行擋門應升級 **gov_check 1b 改動掃描**（非 hook）對 dupes 命中 fail-closed。

**碼證**: R2 synth L28：「遷移序…第一期只 warn」；主委本輪 8 commit 未因任何 warn 停下。`gov_check.sh:270-274` 明寫「刻意不進 _docbad」。`test_dupes_is_warn_only_never_blocks` 釘住 `--dupes` rc=0，**未**釘 gov_check。**限制內最小擋門**：在 1b 迴圈內若 `spec_count_audit.py --dupes` stderr 非空 ⇒ `_docbad++`（沿用既有腳本與段號，**不新增腳本檔、不新 epic**）；hook 層保持 warn-only 以免 4s 鏈誤擋。RECHECK: `sed -n '268,284p' scripts/gov_check.sh`；`pytest tests/governance/test_docrot_f2_total_items_count.py -q` → 15 passed。

**來源摘要**: scripts/gov_check.sh#c1fecd2ccd96;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7

[MAJOR] 信心度=High。**修法**：① 1b 升級為 fail-closed on dupes（僅本次 git diff 範圍）；② 新增 pytest：改 D-002 製造雙「共 N 條」→ `gov_check` 1b rc≠0；③ 遷移序改寫為「hook warn + gov_check 擋 commit 範圍」。**可行性**：`gov_check.sh` 已有 1b 框架與 `spec_count_audit.py` 呼叫；實測 dupes 0.02s/檔。

---

## COMPOSER-R1-P2-01

**斷言**: 骨架佔位偵測是主委對 E3 的**實作折衷**（非三家原文），但對 `new_brief.sh` 產出有效且全庫 replay 零佔位誤擋；**不應推翻**，應 consult 核可並保留腳本 L328 誠實邊界。

**碼證**: `brief_conformance_check.sh:328`「擋不住手寫 brief 把審查標的寫成整份檔」；`rg -l '（我的假設，可能是錯的）' handoffs` → **1** 檔；抽樣 200 份 `brief-kind:` → **0** 次佔位拒絕。`tests/governance/test_docrot_e3_brief_placeholder.py` → 6 passed。RECHECK: 重跑 pytest；`rg` 佔位字面。

**來源摘要**: scripts/brief_conformance_check.sh#55d4b8162804;tests/governance/test_docrot_e3_brief_placeholder.py#2c350f092373

[MINOR] 信心度=High。**修法**：consult-r3 表決「佔位字面集」是否採納；另增一條拒絕「整份檔」關鍵字的軟檢查（可放 brief 範本，非新腳本）。**可行性**：`grep -qF '整份檔' "${brief}"` 一行可試。

---

## COMPOSER-R1-P2-02

**斷言**: `dupes()` 在 `HISTORY-BEGIN` 停止掃描是合理降噪，但「沿革內重複字面一定無害」**未證明**；應登記具名殘留而非宣稱完備。

**碼證**: `spec_count_audit.py:114-118`；`test_dupes_ignores_history_section` 只驗單一 fixture。D-002 沿革 L365 逐字保存「共 29 條」引文——設計使然。反例風險：活文在 `HISTORY-BEGIN` **之前**仍可有未收斂重複（L274「共 34 條」vs L90）。RECHECK: `rg -n 'HISTORY-BEGIN|共.*條' docs/SPLITUNIFY_SPEC.D-002.md | head -20`.

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;docs/SPLITUNIFY_SPEC.D-002.md#f7cdc1cad3f2

[MINOR] 信心度=Medium。**修法**：殘留登記於 HANDOFF（非 GOV_ENFORCEMENT_REGISTRY，同意主委不塞表理由）；活文收斂靠 F1 工序非 dupes。**可行性**：文檔-only。

---

## COMPOSER-R1-P2-03

**斷言**: 以「下一張中大票」為期，未做之 D3／D4／E8 Phase B 優先序應為：**① E8 Phase B（單檔決定表 + narrow_check_router 一列）→ ② D4（停輪機械化）→ ③ D3（三閘語意互斥）**。

**碼證**: R2 E8 L22：`Phase B 最小機械：單檔決定表 + narrow_check_router`——直接對 D1 根因；D4 可避免 D-002 R11/R12 十三輪無下降；D3 需 cross-gate 語意模型，成本最高。D-002 R12 已停輪 ⇒ D4 可驗「十三條無一新面向」機械化。RECHECK: `sed -n '22,23p' handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md`；`ls scripts/narrow_check_router.sh`.

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;scripts/narrow_check_router.sh#61985829c6f4

[MINOR] 信心度=Medium。各一條可驗收判準：**E8-B**＝`narrow_check_router` 對目標 SPEC 新增一列，改決定 A 漏改 B 時 pre-commit/gov_check rc≠0；**D4**＝停輪 pytest：連續 N 輪 findings 皆「歷史段 anchor」占比 >90% 則機械建議停輪；**D3**＝同一決定在 `doc_format`/`xref`/`obligation` 三閘結論互斥時至少一閘 rc≠0（需先定義互斥表）。

---

## GROK-R1-P0-01

**斷言**: 本輪至少五項實作機制屬「非任一家原文之折衷」，主委未開 consult 即落地，直接違反 R2 已接受之程序修正。

**碼證**: R2 synth L31 程序修正逐字「凡主委產出『非任一家原文』之折衷，自動開一輪 consult」。對照：(1) 佔位封閉集＝`brief_conformance_check.sh` PLACEHOLDERS 段（約 L337-346），R2 E3 原文要的是 completeness 歷史 anchor 檢查（synth L17）；(2) `--dupes`＝`spec_count_audit.py` `dupes()`（約 L102-126），超出「只數共 N 條」（synth L26）；(3) HISTORY break＝L117-118；(4) 併入 `spec_xref_hook.sh` 約 L58-66 為主委成本拍板（commit `68a70342` 自白）；(5) F1 單檔收斂＝只改 `docs/SPLITUNIFY_SPEC.D-002.md`（`git diff --stat 44bbd8d3..HEAD -- docs/*.md`）。`handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md` 已寫但**尚未**跑出對這五項的 consult synth／APPROVED。RECHECK：重讀 synth L17-31；`git log --oneline 44bbd8d3..HEAD -- scripts/ templates/ tests/governance/ docs/SPLITUNIFY_SPEC.D-002.md`；`grep -n PLACEHOLDERS\|def dupes\|HISTORY-BEGIN\|warn-only scripts/brief_conformance_check.sh scripts/spec_count_audit.py scripts/spec_xref_hook.sh`。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;scripts/brief_conformance_check.sh#55d4b8162804;scripts/spec_count_audit.py#0a36491036cd;scripts/spec_xref_hook.sh#c1fecd2ccd96

[BLOCKING] 信心度=High。會怎麼失敗：機制細節以「三家共同結論」對外流通，下輪委員／使用者以為已審；異議被「已落地」話術封口。**修法**：對五項開一輪 consult（可合併為既有 r3 brief）；未 APPROVED 前 HANDOFF／commit 不得用「三家共同結論」涵蓋這五項機制，改標「主委試點、待追認」。**可行性**：consult 管線與 brief-kind 已存在；本 brief 即補審入口；r3 brief 路徑已在 repo。

---

## GROK-R1-P0-02

**斷言**: R2 E3／E8 Phase A 指定的「completeness 拒收落在歷史區之 finding anchor」未實作；現況以骨架佔位字面硬擋替代，E3 只完成輸入契約的一半。

**碼證**: synth L17「只改派工契約與 completeness 之 anchor 檢查」；L22 E8A「completeness 拒收 anchor 落在歷史區之 finding」。本輪：`grep -cE 'HISTORY|歷史段|沿革' scripts/completeness_check.sh` → **0**（本輪重跑確認無命中）。已做：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 輸入邊界、`new_brief.sh` current block／diff、`brief_conformance_check.sh` 佔位集。佔位測 6 passed；completeness 歷史 anchor 測不存在。RECHECK：重跑上列 grep；讀 synth L17／L22；確認無新 completeness 測試指向 HISTORY。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;scripts/brief_conformance_check.sh#55d4b8162804;templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#976f11c084b2;scripts/completeness_check.sh#c76692e041da

[BLOCKING] 信心度=High。會怎麼失敗：手寫 brief 寫「整份檔」或委員仍把 source anchor 指進 HISTORY ⇒ 考古再審复發；佔位閘自以為已做完 E3。**修法**：在既有 `completeness_check.sh` 對 finding 的路徑:行／章節做 HISTORY-BEGIN..END 區間判定，命中 ⇒ FAIL；佔位集降為輔助。**可行性**：E8A 自述零新腳本；區間標記在 D-002 已存在（`HISTORY-BEGIN`@L329、`HISTORY-END`@L367）。

---

## GROK-R1-P1-01

**斷言**: `dupes()` 在首個 `HISTORY-BEGIN`（或 `## 沿革`）處 `break`，會漏掉標記之後的活文多落點；「沿革略過無害」已被構造反例否證。

**碼證**: `spec_count_audit.py` L117-118。本輪構造 Case A（行1 `共 5 條` → HISTORY → 行後再 `共 5 條`）→ `--dupes` stderr **空**、rc=0；Case B（HISTORY 前兩處）→ 報 `@ 行 2,3`。D-002 現把 HISTORY 放檔末（L329）故倖免；規則卻是「此後永遠不掃」。RECHECK：重跑 `/tmp` Case A／B 等價 fixture。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/20260912-DOCROT-X-REVIEW-R1-BRIEF.md#554fd32867f1

[MAJOR] 信心度=High。會怎麼失敗：誤植／提早寫入的 HISTORY 標記讓其後活文雙真相源永久靜默。**修法**：改為區間 skip（見 BEGIN 則跳過直到 END），禁止 break 出迴圈。**可行性**：同函式內狀態機兩行級；既有 `test_dupes_*` 可加「HISTORY 後活文仍報」mutation。

---

## GROK-R1-P1-02

**斷言**: 主因 D1 的寫入時硬擋覆蓋率為 0%；「第一期只 warn」對主委自身已否證，不能再當 D1 防線。

**碼證**: `gov_check.sh` L269-273／`spec_xref_hook.sh` L65-66 皆 `|| true` 且不改 rc、不進 `_docbad`。`python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md` → 警告含 `共 8 條 @ 117,3591` 等，**rc=0**。佔位硬擋只掛 `cx_run` 派工路徑，與「多落點寫入」正交。RECHECK：對 GAP3 重跑 `--dupes`；對一段含雙「共 N 條」的 docs 改動跑 `gov_check` 看 `_docbad` 是否仍 0。

**來源摘要**: scripts/gov_check.sh#4b333ce050ff;scripts/spec_xref_hook.sh#c1fecd2ccd96;docs/GAP3_EVENT_UX_SPEC.md#30bb5ab0aa28

[MAJOR] 信心度=High。會怎麼失敗：下張票主委繼續改一處漏一處，stderr 有字、流程不停。**修法**：見必答 3——段 1b 將活文區 `--dupes` 命中計入 `_docbad`（不新檔）。**可行性**：迴圈與腳本皆在；測試會刻意轉紅逼遷移。

---

## GROK-R1-P1-03

**斷言**: F1 活文收縮只落在 `SPLITUNIFY_SPEC.D-002.md` 卻被寫成 DOCROT 收斂點；若下一張中大票非 D-002 系列，本輪 F1 成效判準測不到。

**碼證**: `git diff --stat 44bbd8d3..HEAD -- docs/*.md` → 實質收縮僅 D-002。D-002 活文區 `共 29 條` 現僅表標題一處（L90）；但 `GAP3_EVENT_UX_SPEC.md` 仍雙落點；70 份 `docs/*SPEC*.md` 中 **13** 份本輪 `--dupes` 有警告。HANDOFF 表述「F1 活文收縮已到收斂點」。RECHECK：重跑 diff --stat；對非 D-002 SPEC 跑 `--dupes`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#30bb5ab0aa28;docs/SPLITUNIFY_SPEC.D-002.md#bd2cbf221f9f;handoffs/20260912-DOCROT-X-REVIEW-R1-BRIEF.md#554fd32867f1

[MAJOR] 信心度=High。會怎麼失敗：下一票審 GAP／GOV SPEC 時考古再審與雙計數依舊，卻以為 F1 已驗收。**修法**：對外改標「D-002 試點」；成效判準改為「下一張中大票目標 SPEC 的活文多落點／考古行相對基線下降」，或在該票開場先做同型收縮。**可行性**：只改表述／驗收句，不需新工具。

---

## GROK-R1-P1-04

**斷言**: 以「三家共同結論」為 commit 主旨背書未經委員審之實作細節，屬 verification_claim 同型的不實歸屬；現行 `--commit-msg` 路徑抓不到。

**碼證**: `git log -1 --format=%B 3e009126` 首行「落地三家共同結論前兩項」，內文含「brief_conformance_check.sh 新增骨架佔位偵測」等自創機制。`venv/bin/python scripts/verification_claim_check.py --commit-msg <該 body 檔>` → **rc=0**（本輪重跑確認）。本輪實作四筆 commit 無委員 stamp／review 產出覆蓋其 scripts／templates diff。RECHECK：重跑上列 claim-check；查 audit 有無對應 committee_output。

**來源摘要**: handoffs/20260912-DOCROT-X-REVIEW-R1-BRIEF.md#554fd32867f1;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7

[MAJOR] 信心度=High。會怎麼失敗：git 史上留下「委員已審」假 provenance，後人／閘都當真。**修法**：改既有 `verification_claim_check.py` commit_msg 路徑——背書語需 audit 佐證或 EXEMPT；並回寫後續 commit 訊息勿再籠統掛「三家共同結論」於未審機制。**可行性**：檔案已有 `commit_msg` source_context 與 committee audit 白名單；擴 regex＋audit 查詢即可，不新腳本。

---

## GROK-R1-P2-01

**斷言**: 「併進既有 hook 故一般寫檔零成本」在新增 `--dupes` 路徑上事前未實測；本輪測得觸發路徑仍付可見延遲。

**碼證**: brief assumed 自白只有 codex R2 對既有八支 4.39–4.97s。本輪：`python3 scripts/spec_count_audit.py --dupes docs/SPLITUNIFY_SPEC.D-002.md`×10 → real 皆 **0.03s**；`GOVERNANCE_TEST_HARNESS=1 SPEC_XREF_HOOK_TARGET=docs/SPLITUNIFY_SPEC.D-002.md bash scripts/spec_xref_hook.sh`×5 → real **0.49/0.30/0.31/0.35/0.31**（median≈**0.31s**）。非觸發名之檔案不跑 `--dupes`（case 過濾後）。RECHECK：重跑上列 timing。

**來源摘要**: scripts/spec_xref_hook.sh#c1fecd2ccd96;scripts/spec_count_audit.py#0a36491036cd

[MINOR] 信心度=High。相對既有 ~5s 鏈，+30ms 量級不大，但「零成本」事前無數據＝過程病。**修法**：宣稱成本必附新增路徑 receipt；表述改「非觸發路徑不加 `--dupes`；觸發路徑 hook e2e median≈0.31s（含既有 xref），其中 `--dupes`≈0.03s」。

---

## GROK-R1-P2-02

**斷言**: 「骨架佔位對手寫 brief 零誤擋」事前未做 corpus replay；事後 replay 顯示歷史 BRIEF 字面 FP＝0，但手寫「整份檔」繞過仍在，不能代替 E3 的 completeness 半邊。

**碼證**: `find handoffs -name '*BRIEF*.md'` → **653**；對封閉八字面 `grep -qF` → **hit_any_placeholder=0**。腳本約 L328 自白「擋不住手寫 brief 把審查標的寫成整份檔」。RECHECK：重跑字面掃描；抽一手寫「整份檔」brief 確認佔位閘 rc=0。

**來源摘要**: scripts/brief_conformance_check.sh#55d4b8162804;tests/governance/test_docrot_e3_brief_placeholder.py#2c350f092373

[MINOR] 信心度=High。語料 FP 攻擊未成立；過程攻擊成立；覆蓋洞指向 P0-02。**修法**：保留佔位集；補 completeness；宣稱改為「對 new_brief 骨架字面拒派；不宣稱涵蓋所有手寫 brief」。

---

## CODEX-R1-P1-01
**斷言**: E3 的封閉字面 grep 不能成立「手寫 brief 零誤擋」；合法正文引用骨架字面也會被拒派。
**碼證**: `bash scripts/brief_conformance_check.sh handoffs/.tmp-codex-e3-replay.md` → rc=2，stdout 命中 `（我的假設，可能是錯的）`；兩支 DOCROT 測試雖為 15 passed，未覆蓋合法引用該字面的負例。
**來源摘要**: scripts/brief_conformance_check.sh#55d4b8162804
正文：應改為欄位/區塊語意解析，或明確排除 fenced/quoted example 後只拒實際骨架欄位；可行性證據是現有測試已能區分填妥與未填骨架，補一個 quoted-literal mutation 即可驗證。信心度=High。
## CODEX-R1-P1-02
**斷言**: D1 的實際硬擋覆蓋不是全寫入路徑；直接改文檔可繞過，現有 hook 與 `gov_check` 對重複數字均 warn-only，且「一般寫檔零成本」不成立。
**碼證**: `spec_xref_hook.sh:57-66`、`gov_check.sh:269-274` 皆 `|| true`/不增 `_docbad`；指定測試的 hook mutation 實測「有警告且 rc=0」；`--dupes` direct checker 實測約 0.02s/run，且 `main` 先 `extract` 再 `dupes` 讀檔兩次。
**來源摘要**: scripts/spec_xref_hook.sh#c1fecd2ccd96
正文：R2「第一期只 warn」可保留為遷移遙測，但不得宣稱 D1 已受保護；下一步應在既有 `gov_check` hard path 對已定義 active scope 加校準後的 duplicate gate/基線，或把狀態標為未完成。既有 `_docbad` 與 docs 改動迴圈足以承載，無需新 epic/新腳本。信心度=High。
## CODEX-R1-P1-03
**斷言**: F1 只收縮 D-002 不能證明跨文件或下一張中大票的 convergence；目前實作範圍與「已收斂」敘述不相稱。
**碼證**: `git diff --name-only 44bbd8d3..HEAD -- docs/SPLITUNIFY_SPEC.D-002.md` 僅得該一檔；`docs/SPLITUNIFY_SPEC.D-002.md:325` 的現行 §N 仍明載 API/services 未完整讀取、C5 可能不完整。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#bd2cbf221f9f
正文：應推翻「F1 已普遍收斂」改成「D-002 局部收縮」，或先定義下一票的 normative inventory、active-block 覆蓋率與可重跑判準；現有單檔 diff 與 §N 殘留已提供可驗的邊界。五項逐項皆非任一家原文，故實作前跳過 consult 的程序違反不能由測試綠化抵銷。信心度=High。
## CODEX-R1-P1-04
**斷言**: 「三家共同結論／依 CODEX-R1-P1-02」寫入提交訊息但無委員審查或 receipt，是 verification-claim 同型的未證 provenance；現行機械閘不會擋此表述。
**碼證**: `git log --format='%h %s' 44bbd8d3..HEAD` 命中 `3e009126`、`68a70342` 等 consensus 文案；`verification_claim_check.py:46-55` 的 polarity regex 不含該語意，`:2047-2065` 僅掃當下 commit message，未要求 committee registry 对應 scope/receipt。
**來源摘要**: scripts/verification_claim_check.py#2fc6b3a0e270
正文：應在既有 `commit-msg`/`verification_claim_check` 路徑對 consensus token 與外部 finding ID 要求 exact-scope committee audit/receipt，無對應即拒；可行性證據是 commit-msg 已呼叫該 checker，且 checker 已有 `source_context=commit_msg` 與 committee registry 讀取邏輯。信心度=High。
## CODEX-R1-P2-05
**斷言**: `dupes()` 在首個 `HISTORY-BEGIN` 或 `## 沿革` 直接 `break`，不是「只排除 BEGIN～END 區間」；若 marker 後仍有現行內容，會靜默漏掃。
**碼證**: `scripts/spec_count_audit.py:113-126` 在 marker 行即停止且不讀 `HISTORY-END`；現有 history 測試只驗 history 位於文件尾端的 fixture，未驗 marker 後 current block。
**來源摘要**: scripts/spec_count_audit.py#0a36491036cd
正文：修法為 BEGIN/END state machine，離開 history 後恢復掃描並拒 malformed marker；加入「current→history→current」mutation 即可驗證。此為 Medium 信心度、非單獨 blocking，但足以推翻「沿革略過不會漏真缺陷」的未驗假設。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04
CLOSED:
