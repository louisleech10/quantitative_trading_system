# DOCROT X-CONSULT R2 — grok

task-id: 20260912-DOCROT-X-CONSULT-R2  
family: grok  
findings-round: R2  
brief: handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md  
note: 唯讀審查主委第二版裁定；禁改碼／禁改文檔。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 證據 |
|---|---|---|---|
| R1 三家路線如上 | fact-verified | **成立** | 對讀 `handoffs/20260912-docrot-x-consult-r1-{grok,composer,codex}.md` |
| 第二版裁定＝判定採 grok F1–F3、強制掛既有 PostToolUse | fact-verified | **成立（文字）** | synth.md L29；HANDOFF.md L32 |
| 現行 PostToolUse Edit\|Write 八支 | fact-verified | **成立** | `.claude/settings.json` L189–223 恰 8 個 command |
| 「掛進既有鏈」制度上不算擴建治理工具 | assumed | **不成立** | 見 P1-02：新增第 9 支腳本＝實質擴建；只是不開 epic |
| grok 三條判定在無 registry 下仍可實作 | assumed | **部分不成立** | F1／窄 F2／Task-auto F3 可；「單一決定」廣義 F3 不可（P0-01） |
| 主委有能力正確裁定三家分歧 | assumed | **本輪否證傾向** | 第二版折衷無人提過；F3 與「零 registry」互斥；完全忽略 codex② |

## 被當成事實的未驗證假設（§0）

- 「F1–F3 皆為可數量之 grep、不需 YAML」被寫成裁定事實 → **assumption**；本輪實跑證明廣義 F3 缺 token 清單則閘無輸入（P0-01）。
- 「掛 PostToolUse＝已有強制」→ **部分事實**：Edit\|Write 有早期警告；Bash／生成器路徑本鏈不觸發（既有腳本檔頭自白＋codex R1），第二版未交代如何補（P0-02）。
- 「≤3」為合理閾值 → **assumption**；本輪無驗證、現行 SPEC 七個 Task token 全 >3（P2-01）。

---

## 必答總覽（1–6）

### 1. 第二版裁定可不可行？F3 無 registry 能否實作？

**結論：第二版就字面不可行。** 可拆成三層：

| 判定 | 無 registry？ | 具體實作 | 現行 SPEC 實跑 |
|---|---|---|---|
| F1 活文 `vN`→0 | **可** | 切沿革後 `re.findall(r'\bv\d+\b', live)` | `live_vN=109`（會紅，屬預期） |
| F2「數字字面恰一處」 | **僅窄義可** | 只數 `共\s*\d+\s*條` → 恰 1 | 現行 **2** 命中；若「所有數字」則不可行（無清單必誤擋） |
| F3「單一決定 ≤3」 | **廣義不可** | 閘必須先知道要數哪些字串 | 見下 |

**F3 廣義失敗的具體一步（照第二版做會卡在這裡）：**

1. 實作者寫 `live_doc_density_check.sh`，F1／窄 F2 可交。
2. 寫到 F3 時問：「要數 `Task 9.2b`？還是 `metadata.split_unify`？還是 `validate_split_pair_integrity`？」——R12 真病灶含後兩者（11／8 次）。
3. 第二版禁止 YAML registry，又沒給替代 token 來源 → 實作者只能 (a) 只數 Task ID（漏掉 R12 非 Task 決定）、(b) 把 pattern 寫死進腳本（＝沉默 registry，否定「零維護／不需 registry」）、(c) 停工回報 BLOCKED。
4. 成效判準「改一處漏一處占比下降」若只靠 (a)，下一張票仍會在非 Task token 上重演 → **裁定自我失敗**。

**F3 可救的窄化（本家修正主張，非第二版原文）：**  
自動從活文抽取 `\bTask\s+\d+(?:\.\d+)*[a-zA-Z]?\b`，對每個 token 計數、閾值可調——**不需 YAML**。本輪實跑 `over3`＝Task 9.3×23、9.2b×19、9.1×14、9.5×12、9.4×12、9.2a×8、9.2×8。這只覆蓋「Task 掛名密度」，**不**覆蓋 `metadata.split_unify` 類決定。

```bash
# RECHECK F3 邊界（可重跑）
python3 - <<'PY'
from pathlib import Path
import re
from collections import Counter
live=re.split(r'^#+ .*沿革', Path('docs/SPLITUNIFY_SPEC.D-002.md').read_text(), maxsplit=1, flags=re.M)[0]
print('Task', Counter(re.findall(r'\bTask\s+\d+(?:\.\d+)*[a-zA-Z]?\b', live)))
for t in ['metadata.split_unify','validate_split_pair_integrity']:
    print(t, len(re.findall(re.escape(t), live)))
PY
```

### 2. 我自己 R1 主張是否修正？

| R1 grok | 看過另兩家＋使用者否決後 | 理由 |
|---|---|---|
| 反對新建任何工具；F1–F3 靠結構改寫＋一次性命令 | **修正**：接受「必須有產出端強制」，否則＝自證七條同型失敗 | 使用者「靠紀律你絕對失敗」成立；我 R1 低估強制 |
| 不採 composer YAML epic | **大致堅持，但限縮**：廣義 F3／跨檔 fact equality 若要做，composer／codex① 的「有名單」才誠實；Task-auto F3 不需 YAML | composer 反對「零 list」在廣義 F3 上成立；YAML 檔＋新 epic 仍過重 |
| 未把 codex②（審查只餵當前＋diff）當一等修法 | **修正為首選**：成本最低、直接對「又審已修過的字」 | 三家唯 codex 提；不改文件結構；主委一字未提＝裁定缺陷（P0-03） |
| F4 停輪寫死 | **堅持** | 與本輪無關，仍要 |

### 3. 掛進既有 PostToolUse 鏈的成本

**實測（SPEC 路徑、hook JSON stdin、每支 3 次取中位）：**

| 既有支 | median wall |
|---|---|
| doc_format_precheck | 0.091s |
| plain_docs_order_check | 0.141s |
| **obligation_block_check** | **4.259s** |
| factkey_write_guard | 0.047s |
| list_active_mechanisms --hook | 0.039s |
| narrow_check_router | 0.036s |
| spec_xref_hook | 0.312s |
| synth_attribution_hook | 0.041s |
| **SUM Edit\|Write 鏈** | **≈4.965s／次寫入** |

假設 F1＋窄 F2＋Task-auto F3 的純 Python 計數：20 次合計 0.0419s ⇒ **≈2.1ms／次**。相對既有鏈可忽略；**延遲主因已是 obligation_block_check，不是新判定**。

**誤擋：**

- 既有 hook 以路徑 kind 過濾；`handoffs/` 多數放行或走別 kind。若新閘未複製同一 path filter，對 `HANDOFF.md`／白話／reconcile 會誤擋（裁定複述本身就在 HANDOFF）。
- 現行 SPEC 在 F1／F3-auto 下會**立刻全紅**（109 個 vN、7 個 Task >3）——在活文未先收縮前掛上＝寫檔即炸，屬「強制有效」但需遷移序：先改結構再掛閘，或閘先 warn。

**維護：** 第 9 支腳本＋settings 多一行＝維護面增加；與「不擴建」話術衝突（P1-02），但遠小於 YAML registry epic。

```bash
# RECHECK 成本（可重跑；勿在前景對全鏈做過多次）
python3 - <<'PY'
# 同本檔必答 3 之計時腳本；對 docs/SPLITUNIFY_SPEC.D-002.md 餵 Edit JSON
import json, subprocess, time
from pathlib import Path
root=Path('.').resolve(); spec=root/'docs/SPLITUNIFY_SPEC.D-002.md'
payload=json.dumps({"tool_name":"Edit","tool_input":{"file_path":str(spec)},"cwd":str(root)})
cmd=['bash','scripts/obligation_block_check.sh']
ts=sorted((time.perf_counter(), subprocess.run(cmd,input=payload,text=True,capture_output=True), time.perf_counter())[0] or 0 for _ in range(1))
# 簡版：單次
t0=time.perf_counter(); subprocess.run(cmd,input=payload,text=True,capture_output=True); print('obligation_once', round(time.perf_counter()-t0,3))
PY
```

### 4. 有沒有第四條路？

**有。** 三家與主委都沒完整寫出的組合：

1. **立刻採 codex②（流程，零腳本）**：派工 brief 只附「現行契約段＋本輪 diff」；finding 之 source anchor 落在沿革／HISTORY → completeness／主委拒收。這直接打「新一輪又看到前幾輪修完的字」。
2. **機械層只做 F1＋窄 F2＋Task-auto F3**，掛 PostToolUse **且**掛進 `gov_check.sh` 1b（複製既有 doc_format 的三層：Edit\|Write 早期警告＋改動掃描補 Bash＋派工硬擋）——不要只掛有洞的 matcher。
3. **廣義「決定」密度**降級為具名殘留：若下一張中大票成效判準失敗，再導入 **最小** token 清單（可內嵌於腳本或單檔；不必先上 composer 全套 YAML epic）。
4. **遷移序強制**：先把活文收縮到閘會綠，再 enable fail；否則「強制」＝無法改 SPEC。

此路保留 grok「少維護」與 composer「要強制」、並補上被忽略的 codex② 與 Bash 洞。

### 5. 裁定程序本身該怎麼改？

現行：主委對三家互斥路線自行折衷 → 寫進 synth／HANDOFF → 使用者質問才有 R2。  
**缺陷**：第二版是「無人提過的折衷」，卻當已決執行；與「實作者不自審」對稱原則衝突——**主委也不該自裁自過**。

**改法（可執行）：**

1. 凡主委產出「非任一家原文」的折衷路線 ⇒ **自動開一輪 consult**（本 R2 應成為常設，而非使用者催才做）。
2. 折衷文只准寫在 **一個**權威位置（reconcile synth 的「路線裁定」段）；HANDOFF 只寫 `見 synth#錨`——本輪裁定本身已複寫兩處（P1-01）。
3. 折衷必須附「否證觀測」表（本 brief 已有）且 **每格「我跑了」非空** 才能標 APPROVED；本裁定 assumed 兩格仍「沒跑」就被寫進 HANDOFF 當現行。

### 6. 是否不值得做？

**值得做窄核，不值得做第二版全文。**

| 做 | 不做／延後 |
|---|---|
| codex② 派工輸入隔離 | 全庫 fact-key equality NLP／跨所有白話檔 |
| F1＋窄 F2＋Task-auto F3＋三層掛載 | 「單一決定」無名單的廣義 F3 |
| 活文先收縮再 enable | 未收縮就對全 SPEC 硬紅擋寫 |

**可接受殘餘：** 收斂檔歷史敘事；非 Task 決定的偶發複述——用「下一張中大票同型 finding 占比」當失敗開關（主委已寫的成效判準保留）。  
**若只做第二版原文：** 會在 F3 實作步失敗或沉默變成 registry，同時留下 Bash 洞與忽略輸入隔離 → **不值得照原文做**。

---

## GROK-R2-P0-01

**斷言**: 第二版裁定同時主張「F3 單一決定活文計數 ≤3」與「不需任何 registry／token 清單」——二者互斥；照原文實作會在「閘要數哪個字串」這一步失敗或淪為腳本內沉默名單。

**碼證**: 裁定原文「單一決定活文計數降至三以下…**不需** composer 之 YAML registry」（`handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md:29`）。實跑活文：`Task 9.2b`×19 可自動抽，但 R12 病灶 token `metadata.split_unify`×11、`validate_split_pair_integrity`×8 **不是** Task 文法，無名單則閘不知數它們。RECHECK：必答 1 之 Python 區塊。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7

[BLOCKING] 信心度=High。會怎麼失敗：實作者卡死／只數 Task 而漏真病灶／把 pattern 寫進腳本卻仍宣稱零 registry。**修法**：把 F3 正式窄化為「自動 Task-token 密度」；非 Task 決定列為具名殘留或接受最小名單（誠實承認那是 registry）。可行性＝本輪已跑出 Task Counter 與非 Task 計數對照。

---

## GROK-R2-P0-02

**斷言**: 第二版把「強制」掛在既有 `PostToolUse: Edit|Write`，等於選用已被文件化、且 R1 codex 已揭的洞當唯一強制點——Bash／生成器寫檔不觸發該 matcher。

**碼證**: `.claude/settings.json:189` matcher=`Edit|Write`（八支文件檢查）；`scripts/doc_format_precheck.sh` 檔頭 L17–18 自白「經 Bash 重導寫出的檔…都不會觸發 hook」；`scripts/gov_check.sh` L226–229 亦承認須靠 1b 補洞。第二版原文只寫掛 PostToolUse，**未**要求同步掛 1b／派工邊界。RECHECK：`python3 -c` 印 settings PostToolUse matchers；`sed -n '14,22p;226,229p' scripts/doc_format_precheck.sh scripts/gov_check.sh`。

**來源摘要**: .claude/settings.json#77cb54336328;scripts/doc_format_precheck.sh#e39ce0d21db0;handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a

[BLOCKING] 信心度=High。會怎麼失敗：主委用 Bash／`cx_run`／生成器改 SPEC → 新密度閘沉默放行，與「違反即寫檔當下報」文案不符。**修法**：沿用既有三層（PostToolUse 警告＋`gov_check` 1b 改動掃描＋派工硬擋），新判定三處同掛；或具名登記「Bash 洞殘留」且不得宣稱已強制。可行性＝doc_format 已是該樣板，複製掛載點即可。

---

## GROK-R2-P0-03

**斷言**: 主委第二版裁定完全忽略 codex R1 第②條（審查輸入只餵當前段落＋本輪 diff），而該條可能是三家中對「重審已修文字」最直接、且零新工具的一等修法。

**碼證**: brief 必攻點 6 與 R1 codex `CODEX-R1-P1-02` 修法段；synth 路線裁定段（L22–31）只字未提「輸入範圍／diff-only／anchor 不得落歷史」。RECHECK：`grep -n 'diff\|當前段落\|輸入範圍\|HISTORY\|審查輸入' handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → 路線段無採納句（D2 群曾寫「一併採納」卻未進入「新裁定」操作句）。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-codex.md#f92298ca9f5a;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7

[BLOCKING] 信心度=High。會怎麼失敗：即使 F1 之後活文較乾淨，派工仍餵全文 → 委員繼續打沿革／前輪敘事；工具閘無法替代輸入隔離。**修法**：新裁定操作句必須顯式採納 codex②（brief 範本＋拒收歷史 anchor）；可與密度閘並行，且應**先**做。可行性＝只改派工契約，不需新腳本。

---

## GROK-R2-P1-01

**斷言**: 主委把第二版裁定完整複寫進 `synth.md` 與 `HANDOFF.md` 兩處，正是 R1 判定的主因（一決定多落點）在治理敘事上的即時再犯。

**碼證**: `grep -n '判定採 grok\|新裁定' HANDOFF.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → HANDOFF:32 與 synth:29 兩段並列全文（非指標）。RECHECK：重跑該 grep；對讀兩段是否需同步改一字。

**來源摘要**: HANDOFF.md#1b24c621be54;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb

[MAJOR] 信心度=High。會怎麼失敗：R2 若修裁定，必漏一處 → 下輪又打「裁定文檔互斥」。**修法**：權威只留 synth 路線段；HANDOFF 改 `見 handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#路線裁定`。可行性＝刪複述、留指標。

---

## GROK-R2-P1-02

**斷言**: 「掛進既有鏈、不新開 epic」被用來主張「不算擴建治理工具」，但新增第 9 支 PostToolUse 檢查腳本在維護／失敗面與「新建腳本」無本質差別，只是包裝不同。

**碼證**: 現鏈已 8 支（settings L193–222）；brief assumed「掛進既有檢查鏈在制度上不算擴建」標 **沒跑**。composer R1 要的也是「一個 checker 腳本」——差異在有無 YAML，不在「有沒有新腳本」。RECHECK：數 settings 內 Edit\|Write hooks；對讀 composer P0 修法與第二版「強制採 composer」實際只採掛載、不採 YAML。

**來源摘要**: .claude/settings.json#77cb54336328;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7;handoffs/20260912-docrot-x-consult-r1-composer.md#4b16eee31672

[MAJOR] 信心度=Medium。會怎麼失敗：用話術繞過「不再擴建」自傷規則，日後第 10、11 支同理擠入。**修法**：若加腳本，就承認「小擴建」並受成效判準約束；或把 F1／窄 F2 併入既有 `obligation_block_check`／HISTORY 規則，**零新檔**。可行性＝obligation 已管歷史專區，F1 與之同向。

---

## GROK-R2-P2-01

**斷言**: 閾值「≤3」來自 R1 grok 對 Task 掛名的示意（標題＋§V＋mutation），未經驗證，且對現行 D-002 活文立刻全滅（7／8 個 Task token >3），不宜未經校準就寫進強制閘。

**碼證**: R1 grok F3 原文「目標 ≤3：標題+§V 掛名+mutation 掛名」；本輪 Counter 最低超標亦為 8。RECHECK：必答 1 Python。

**來源摘要**: handoffs/20260912-docrot-x-consult-r1-grok.md#f14daa65418b;docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24

[MINOR] 信心度=High。會怎麼失敗：閘一掛上 SPEC 無法改、或被迫把閾值偷偷改大假綠。**修法**：先收縮活文；閾值改由「收縮後基線＋裕度」校準，或第一期只報 warn。可行性＝先量基線再設限。

---

## GROK-R2-P2-02

**斷言**: 既有 Edit\|Write 鏈單次中位已 ≈4.97s（obligation 獨佔 ≈4.26s）；主委「成本未評估」屬實，但**新增** F 類計數不是延遲主因——未評估的是鏈上已有巨石與誤擋面，而非毫秒級新判定。

**碼證**: 本輪計時表（必答 3）；F 類計數 ≈2.1ms。RECHECK：對 `obligation_block_check.sh` 餵 SPEC 的 Edit JSON 單次 `perf_counter`。

**來源摘要**: .claude/settings.json#77cb54336328;scripts/obligation_block_check.sh

[MINOR] 信心度=High。會怎麼失敗：討論焦點誤放在「再加一支會不會慢」，忽略寫每次 SPEC 已付 ~5s 與 Bash 洞。**修法**：成本評估改問「掛載是否含 1b／誤擋 path filter／遷移序」；延遲優化另打 obligation，不擋 F1。可行性＝本輪已分拆測量。

---

ASSUMPTIONS_VERIFIED: R1 三家原文與 synth 兩版裁定已對讀；PostToolUse 八支已數；F1／F2／Task-auto F3／非 Task token 已對 D-002 實跑；Edit\|Write 鏈八支中位耗時已測；裁定在 synth＋HANDOFF 雙寫已 grep  
TESTS_RUN: 上列 python 計數與 hook 計時（本機實跑；obligation median≈4.259s；鏈 SUM≈4.965s；F-check≈2.1ms）；交件前 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r2-grok.md --family grok`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀；僅新增本產出與交接檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: blocked
BLOCKED-BY: GROK-R2-P0-01,GROK-R2-P0-02,GROK-R2-P0-03
CLOSED:
STATUS: DONE
