# DOCROT R2 五項落地 — Composer 審碼（R1）

**task-id**: `20260912-DOCROT-X-REVIEW-R1`  
**家族**: COMPOSER  
**審查邊界**: brief 指定 current block ＋ `git diff 44bbd8d3..HEAD -- scripts/ templates/ tests/governance/ docs/SPLITUNIFY_SPEC.D-002.md`（D-002 沿革段除外）

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 標記 | 覆核 |
|------|------|------|
| 「併進既有 hook ⇒ 一般寫檔零成本」 | **assumed** | 主委只量測既有八支鏈 4.39–4.97s，未量測 `--dupes` 增量；實跑 `time python3 scripts/spec_count_audit.py --dupes docs/SPLITUNIFY_SPEC.D-002.md` → **0.02s**（可忽略，但「零成本」未實測 hook 全鏈） |
| 「沿革段略過不會漏真缺陷」 | **assumed** | 無反例證明；D-002 活文 L274 仍含「共 **34** 條」敘事字面，與 register「共 29 條」並存——`dupes()` 不抓跨 regex 語型衝突 |
| 「F1 只做 D-002 足以驗下一張中大票成效」 | **assumed** | 下一票若非 D-002 系列，F1/F2 成效指標**不可觀測** |
| 「骨架佔位偵測對手寫 brief 零誤擋」 | **partially verified** | `rg` 全庫僅 **1** 份含佔位字面；抽樣 200 份 `brief-kind:` 檔 **0** 次因佔位被拒——但 42% 因**其他**閘（缺範本引用等）失敗，與「零誤擋」不同義 |
| commit「落地三家共同結論」 | **false as stated** | R2 synth 授權的是**優先序與方向**，非本輪五項具體形態；且本輪實作**零委員審查** |

---

## §1 必查摘要（11 類）

1. 矛盾/互斥：**有**——commit 稱「三家共同」與 HANDOFF「從未經委員審查」互斥。  
2. 漏項/端到端：**有**——`--dupes` 掛載無端到端（HANDOFF 自承）；D3/D4/E8 Phase B 未做。  
3. 不可測驗收：**有**——F1「收斂點」無跨檔可觀測指標。  
4–10. 量化/工程/OOM 等：**無**（本輪為治理文檔範圍）。  
11. 必要性/短命工：**有**——warn-only `--dupes` 若永不升級則為永久噪音層。

---

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

## 必答逐條 Verdict（摘要）

| # | 結論 |
|---|------|
| 1 | 五項**皆**為非原文折衷；跳過 consult **構成**違反 R2 程序修正。應推翻者：**宣稱「已完成」**與 **commit 歸因**；應改寫者：`--dupes` 範圍、F1 收斂聲稱；可保留待 consult：佔位偵測、hook 併入、沿革 skip（附殘留）。 |
| 2 | D1 硬擋覆蓋率 ≈0%（warn-only）；派工硬擋僅覆蓋 brief 場景。見 P1-03 碼證。 |
| 3 | 「第一期只 warn」**單靠 warn 不成立**；最小擋門＝`gov_check` 1b fail-closed（P1-04），不增腳本。 |
| 4 | 優先序 E8-B → D4 → D3（P2-03）。 |
| 5 | 是，構成同型不實宣稱；**能**機械化（P0-02），現行未擋。 |
| 6 | **不可**進下一步實作宣告；須先 consult-r3 + 修正 commit 歸因 + 1b 擋門或 revert 五項中未核可部分。 |

---

ASSUMPTIONS_VERIFIED: `git log 44bbd8d3..HEAD` 8 筆；pytest docrot 15 passed；docs 200/132 hook 觸發；dupes D-002/GAP3 實跑；brief 佔位 replay 抽樣 200；verification_claim_check commit-msg rc=0 空輸出。  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_f2_total_items_count.py -q` → 15 passed rc=0。  
FAILURES_SEEN: none。  
SCOPE_CHANGES: none（僅 review 產出）。  
NUMERIC_OR_SCHEMA_IMPACT: none。

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R1-P0-01,COMPOSER-R1-P0-02,COMPOSER-R1-P1-04  
CLOSED:
