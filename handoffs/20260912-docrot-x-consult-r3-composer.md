# DOCROT consult R3 — COMPOSER（可驗收 TODO）

task-id: 20260912-DOCROT-X-CONSULT-R3  
family: COMPOSER  
brief: `handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md`  
findings-round: R3

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 | 否證／碼證 |
|---|---|---|
| 「D1／D2 機械化後輪數就會降」 | **未驗證，不得宣稱已解** | D-002 R1–R12 heading 計數 15/11/15/8/11/16/15/14/21/13/12/13，均值 **13.25**，末三輪 R10–R12 仍 **13/12/13**，無下降趨勢；主委五項落地後 `--dupes` 仍 `|| true` ⇒ D1 硬擋覆蓋率 **0%**（見 COMPOSER-R3-P1-01） |
| 「限制審查輸入（current block＋diff）即可讓 finding 指向碼與架構」 | **部分成立，不足** | 輸入隔離可砍掉 D2 考古再審，但 `COMMITTEE_FINDING_TEMPLATE.md` 仍允許 **碼證** 只寫「章節／原文短句」；R8–R12 群集表關鍵字 grep 僅 **17/73**，低計數是因表頭未強制 `path:line`，非代表已聚焦碼（見 COMPOSER-R3-P1-02） |

fact-verified: review-r1 十群 22/22 歸戶 → `handoffs/reconcile/20260912-docrot-x-review-r1/synth.md`  
fact-verified: `gov_check.sh` 段 1b、`spec_xref_hook.sh` ③ 之 `--dupes` 皆 `|| true` → 實讀兩檔  
fact-verified: `verification_claim_check.py` 對「三家共同結論」commit subject → **rc=0**（未擋）

---

## 必答 1 — 主委五項裁定

| # | 裁定 | 理由（一句） |
|---|---|---|
| 1 `brief_conformance_check.sh` 佔位拒派 | **改寫** | 保留封閉字面集，但宣稱改為「只擋 `new_brief.sh` 骨架原樣派出；**不**涵蓋手寫 brief、不替代 E8 Phase A」；**另列 Task 3.1** 補 completeness HISTORY-anchor 拒收（E3／E8 後半） |
| 2 `spec_count_audit.py --dupes` 三 regex | **改寫** | `dupes()` 僅掃 `_RE_TOTAL_ITEMS`（窄 F2）；三 regex 對 `GAP3_EVENT_UX_SPEC.md` 誤報「五維度」等 **19+** 行（實跑 `--dupes`） |
| 3 `dupes()` 在 `HISTORY-BEGIN` **break** | **撤回** | 檔內若 `HISTORY` 非尾段，`break` 漏掃 `HISTORY-END` 之後活文；改 **區間 skip**（`in_hist` 旗標），禁 `break` |
| 4 警告併入 `spec_xref_hook.sh` | **採納** | E2 三層之產出端 warn 層；fail-closed 只放在 `gov_check` 段 1b（Task 3.2），不增 `settings.json` 條目 |
| 5 F1 只做 `D-002` 一份 | **採納（試點標籤）** | 三家未限單檔；標「D-002 pilot」，不得宣稱 F1 收斂；成效在 **b9 下一輪 review** 量（必答 3） |

---

## 必答 2 — TODO 表（≤8；每條過三問）

| Task | 改哪個既有檔 | 擋哪個根因 | 不做再燒幾輪 | 驗收（rc）＋ mutation |
|---|---|---|---|---|
| **3.1** | `scripts/completeness_check.sh` | **D2** | R11 **12/12**、R12 **13/13** 全打上一版修法（review-r1 G3） | `pytest tests/governance/test_docrot_e3_history_anchor.py -q` → **0**；mutation：finding `碼證` 含 `docs/X.md:400` 且該行在 `HISTORY-BEGIN..END` → completeness **≠0** |
| **3.2** | `scripts/gov_check.sh`（段 1b）＋`scripts/spec_count_audit.py`（`--dupes` rc） | **D1** | D1 寫入硬擋 **0%**；主委可不派工直改 `docs/`（review-r1 G5） | `pytest tests/governance/test_docrot_f2_total_items_count.py -q` → **0**；mutation：活文雙「共 29 條」→ `gov_check` 段 1b **≠0** |
| **3.3** | `scripts/spec_count_audit.py` `dupes()` | **D2** | G4：`break` 漏掃 HISTORY 後活文 ⇒ 假綠 | `pytest tests/governance/test_docrot_dupes_history_skip.py -q` → **0**；mutation：fixture 在 `HISTORY-END` 後再放雙「共 2 條」→ `--dupes` 必報 |
| **3.4** | `scripts/spec_count_audit.py` `dupes()` regex 表 | **D1** | G6 三 regex 誤報削弱閘可信度，主委繼續繞過 warn | `python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md` → stderr **無**「五維度」；**有**「共 8 條」@117,3591 |
| **3.5** | `scripts/verification_claim_check.py` | **第三根因**（決議→實作無可核對 TODO） | commit 以「三家共同結論」背書未審實作（review-r1 G2，已實證 rc=0） | `pytest tests/governance/test_docrot_claim_committee_backing.py -q` → **0**；mutation：subject 含「三家共同結論」且無 `committee_family_result` audit → **≠0** |
| **3.6** | `scripts/brief_conformance_check.sh`（註解＋錯誤文案） | **D2**（輔助） | 空殼 brief 仍可能派出（assumed 行數閘只數不擋骨架） | `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` → **0**；文案須含「不替代 completeness HISTORY 檢查」 |
| **3.7** | `templates/COMMITTEE_FINDING_TEMPLATE.md`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` | **D2**＋聚焦碼 | finding 可只引散文，diff 內仍爭字面 | 見必答 4 逐字改法；`bash scripts/template_check.sh template` → **0** |
| **3.8** | `tests/governance/test_docrot_r3_bundle.py`（合併 3.1–3.5 探針） | 回歸 | 單測散落再犯 warn-only 假綠 | `pytest tests/governance/test_docrot_r3_bundle.py -q` → **0**；任一 Task 改壞對應子測試必紅 |

**D3／D4／D5（只答做不做）**  
- **D3**（語意互斥閘）：**不做**——需 NLP／全庫 registry，違反 brief 禁語意閘；登記具名殘留。  
- **D4**（停輪機械化）：**做（最小）**——僅在 `docs/ROADMAP.md` 增一句可 `rg` 的停輪條（連兩輪群集表「上一版修法」占比 ≥80% ⇒ 停審），**不**新腳本；不佔 TODO 名額。  
- **D5**（狀態跨檔複寫）：**不做（本輪）**——使用者看板偏好；非 D1/D2 根因，擴到 `白話說明/` 會違反「不窮舉」。

**不需 SPEC**：改動全在 `scripts/`／`templates/`／`tests/governance/`；consult-r3 本檔即派工契約。

---

## 必答 3 — 成效判準（一句可機械計算）

**句**：下一張中大票（**SPLITUNIFY b9**，目標 `docs/SPLITUNIFY_SPEC.D-002.md`）之 **review-r1** synth，群集表第 1 欄（斷言前 20 字）命中 `落點|考古|条数|條數|上一版|前版|同步|複述|漂移` 的 finding 數 ÷ 該輪 `## *-R1-P*` heading 總數 ≤ **56%**。

| 欄位 | 值 |
|---|---|
| 分子 | 上列關鍵字命中之群集行數（`scripts/_synth_attr.py` 群集表第 1 欄；`rg` 可重跑） |
| 分母 | `rg -c '## (CODEX|COMPOSER|GROK)-R1-P' handoffs/reconcile/<ticket>-review-r1/synth.md` |
| 資料來源 | 該票 review-r1 之 `synth.md` 群集表＋附錄 heading |
| 基線 | D-002 R10–R12 三輪：R11 **12/12=100%**、R12 **13/13=100%** 自述全為上一版修法；取基線 **80%** |
| 及格線 | ≤ **56%**（降 30%） |

---

## 必答 4 — 結構病灶與逐字改法

| 結構 | 為何導向字面 finding | 改哪裡 |
|---|---|---|
| finding **碼證** 允許「章節／原文短句」 | 委員可只複述 SPEC 散文，不必指向本輪 diff 行 | `templates/COMMITTEE_FINDING_TEMPLATE.md` 規則 2 |
| adversarial prompt 未要求 **碼證** 落在 diff | 與 E3 輸入隔離不同步 | `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §輸出格式 |
| brief 無機械檢查 HISTORY anchor | E8 Phase A 半程 | `scripts/completeness_check.sh`（Task 3.1） |
| synth 群集表以斷言敘事為主 | 收斂時比對字面非比對碼 | 不改 synth 格式（D6）；靠 3.1＋3.7 在產出端擋 |

**逐字改法（COMMITTEE_FINDING_TEMPLATE.md 規則 2）**——將  
`- \`**碼證**\`：檔案路徑 / 行號 / 命令 / 觀測輸出摘要`  
改為  
`- \`**碼證**\`：必含可重跑之 \`path:line\`（實作類 finding 優先 \`scripts/\` 或 \`momentum/\`）；若引 SPEC，該 \`docs/…:line\` 須出現在本 brief「本輪 diff」輸出內，且不得落在 \`HISTORY-BEGIN\`～\`HISTORY-END\`。`

**逐字改法（SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md §輸出格式四欄第 2 點）**——在「章節 / 路徑:行」後追加：  
`；BLOCKING 者 path:line 須落在 brief 所列 diff 範圍內（completeness 機械拒收越界 anchor）。`

---

## 必答 5 — F1 範圍

下一張中大票＝**SPLITUNIFY b9 實作**（`D-002` v13，HANDOFF 現行 topic 暫停待 DOCROT 收斂）。**F1 不先擴**到其他 SPEC；`D-002` pilot 足夠，成效在 b9 的 **review-r1** 用必答 3 公式量。若 b9 impl 觸及其他 SPEC（如 `SPLITUNIFY_TODO.md`），只改 **指標**不複述決定正文。

---

## 必答 6 — 可否進實作

**可進實作**，條件：① 僅做上表 Task 3.1–3.8；② 主委五項 #3 **撤回**、#2 **收窄**、#1 **補** Task 3.1；③ commit 訊息禁「三家共同結論」直至 Task 3.5 上線；④ consult-r3 三家 reconcile ＋ `debt_clear` 後再動碼。  
**BLOCKING（實作前）**：review-r1 G3/G4/G5 尚未落地（現 completeness 無 HISTORY 檢查、`dupes` 仍 warn-only、break 未改）——由 Task 3.1–3.4 解除，非新 epic。

---

## COMPOSER-R3-P1-01

**斷言**: brief 假設「D1／D2 機械化後輪數會降」**無前後對照數據**，在 `--dupes` 仍 warn-only（硬擋 0%）時不得當作已驗事實。

**碼證**: `for r in $(seq 1 12); do rg -c '## (CODEX|COMPOSER|GROK)-R'"$r"'-P' handoffs/reconcile/20260911-splitunify-b9-review-r"$r"/synth.md; done` → 15,11,15,8,11,16,15,14,21,13,12,13；`scripts/gov_check.sh:271-274` `|| true`；`scripts/spec_xref_hook.sh:65` `|| true`。RECHECK: 重跑迴圈；`rg '\|\| true' scripts/gov_check.sh scripts/spec_xref_hook.sh`。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#70660a69b76f;scripts/gov_check.sh#4b333ce050ff

[MAJOR] 信心度=High。宣稱已解會在 b9 再燒 3+ 輪 doc-sync。**修法**：必答 3 成效公式＋Task 3.2 fail-closed；無數據前 HANDOFF 只寫「試點待量」。

---

## COMPOSER-R3-P1-02

**斷言**: 「current block＋diff」**單獨**不能保證 finding 指向碼與架構——範本仍允許 **碼證** 僅引 SPEC 散文。

**碼證**: `templates/COMMITTEE_FINDING_TEMPLATE.md:17` 仍寫「檔案路徑 / 行號 / 命令 / 觀測輸出摘要」無 diff 邊界；R8–R12 群集關鍵字 grep 17/73 低估因表頭非機械碼證。RECHECK: `sed -n '15,20p' templates/COMMITTEE_FINDING_TEMPLATE.md`。

**來源摘要**: templates/COMMITTEE_FINDING_TEMPLATE.md#0c1fbb8d3f0b;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：必答 4 逐字改法＋Task 3.7；與 Task 3.1 同鏈拒收越界 anchor。

---

## COMPOSER-R3-P2-01

**斷言**: 主委五項 #3（`dupes()` `break`）必須**撤回**；#2 必須**收窄**至 `_RE_TOTAL_ITEMS`，否則 G4/G6 在 b9 首輪即復發。

**碼證**: `scripts/spec_count_audit.py:117-118` `break`；`python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md` → 「五維度」誤報；D-002 `--dupes` 活文區 rc=0（無雙「共 N 條」時）。RECHECK: 重跑 GAP3 `--dupes`；讀 `dupes()` L117。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 3.3–3.4；#3 主委 revert `break` 引入 commit 之邏輯，改 interval skip。

---

## COMPOSER-R3-P2-02

**斷言**: `verification_claim_check.py` 未擋「三家共同結論」類 commit 背書，第三根因「決議→實作無可核對」仍開。

**碼證**: `git show 3e009126 --format='%s'` → 含「三家共同結論」；`venv/bin/python scripts/verification_claim_check.py --commit-msg` 同上 subject → **rc=0**；`STRONG_POLARITY_RE`（L46-52）無「三家」模式。RECHECK: 重跑 verification_claim_check。

**來源摘要**: scripts/verification_claim_check.py#2fc6b3a0e20c;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#abb5efcdc63d

[MAJOR] 信心度=High。**修法**：Task 3.5 加 regex＋`audit.log` `committee_family_result` 同 task-id 佐證。

---

ASSUMPTIONS_VERIFIED: D-002 R1–R12 計數、GAP3 `--dupes` 誤報、`verification_claim_check` rc=0、`gov_check`/`hook` `|| true` 均已實跑  
TESTS_RUN: （交件前）`bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r3-composer.md --family composer`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（consult 禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none

VERDICT: proceed  
BLOCKED-BY:  
CLOSED: COMPOSER-R2-P3-01  
STATUS: DONE
