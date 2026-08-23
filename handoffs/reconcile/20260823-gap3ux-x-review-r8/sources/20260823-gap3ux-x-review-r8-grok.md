# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R8（GROK）

TASK_ID: 20260823-GAP3UX-X-REVIEW-R8  
FAMILY: GROK  
brief-kind: review  
brief: `handoffs/20260823-gap3ux-x-review-r8-brief.md`  
標的: `docs/GAP3_EVENT_UX_SPEC.md`  
sha256（開工第一件事重跑）: `01cf2468573ff50f9d3933698d2b110824bccc259bb519a1e2f523ca5b151bd0`（與 brief 鎖定值相符；1580 行、42 Task）  
SCOPE: review-only；禁改碼、禁改 SPEC。補丁包＝可套用文字，實際套用由主委做。

## Verdict：需修訂後定版

**議題一成立**（不以主委表態為準；碼證獨立支持）：條件 IC 之答案窗／連續 `label_value` 屬**分析參數**，事件批次屬**事實**；現行 SPEC 把「主答案窗→烤入匯出 `label_value`」當條件 IC SoT（D-3(a)／A-6／Task 4.1／7.0b）＝錯層。A-6 舊框**作廢**，改 A-6′ 並仍須白話閘。R7 群集 E（7.0b 匯出 API）在新架構下須**整段重寫**，不得當 CLOSED 凍結。

另抓兩條主委單方產出／harness 假綠（同型「清單與計數不同步」病）：F-14 用 `; echo $?` 使 `count_audit=2` 時 `facts.sh` 仍 `rc_all=0`；`gap3ux_pre_review.sh` 仍硬編碼 r7-facts，R8 facts 未進唯一閘入口。

**不可 FROZEN**：OPEN 含 P0；A-6′ 未確認；硬輪上限內本輪為 consult 後第 1 輪。

補丁包：
- `handoffs/patches/20260823-gap3ux-r8-arch-analyze-time-label.md`
- `handoffs/patches/20260823-gap3ux-r8-harness-f14-prereview.md`

---

## 0. 標的指紋與 fact 重跑

| 項 | 結果 |
|---|---|
| `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md` | `01cf2468573f…b151bd0`＝brief 鎖定值 |
| `wc -l` | 1580 |
| `bash handoffs/20260823-gap3ux-x-review-r8-facts.sh` | 宣稱 `rc_all=0`；但 F-14 內 `count_audit=2`（見 P1-02）——**總碼不可信** |
| `python3 handoffs/20260823-gap3ux-x-review-r8-dims.py` | rc=0 |
| `bash scripts/gap3ux_pre_review.sh` | rc=0（FACTS＝**r7**-facts；未覆蓋 r8） |
| `patch_locus_check` 空 SYNC-LOCI | rc=2（反測成立） |
| F-14 compound | `count_audit=2` 且 compound `rc=0`（假綠成立） |

---

## 1. 議題一裁定（必答）

### 1.1 架構調整是否成立？→ **成立**

使用者論點與碼證對齊，**主委「你的判斷正確」未被推翻**：

| 層 | 現況碼證 | 推論 |
|---|---|---|
| 事件事實 | `eventExport.ts:75-85`：`label` ← `positive_case`，**不看**答案窗 | t0 條件標記 0/1 可獨立固化 |
| 分析參數 | 同段：`label_value` ← `future_{horizon}bar_return` | 連續報酬＝條件 IC 輸入，隨 h 變 |
| 「不重算」 | `ic_feed.py:5`「v1 不重算」 | **版本限制**，非能力上限 |
| bars 能力 | `pipeline.py:76-82` `bars_from_kline_cache`＝唯一入口；B8 表已用 | 分析時可算，不必烤進匯出 |
| 錯層代價 | 比較 h=3 vs h=7 須重匯出未變事件批 | 與「事實／參數分離」相反 |

**不成立之反證（本輪未找到）**：無碼證顯示條件 IC 必須在 `/search` 選定答案窗；契約 `window.horizon_bars` 為單一 int 只約束**一次分析**之窗，不強制窗必須在匯出時凍結。

### 1.2 PIT 如何保證？（推翻 brief assumed「既有 decision_time_rule 即可」）

既有 `feature_cutoff_rule=max_close_ms_le_decision_at`／`decision_time_rule=t0_open_minus_k_bars` **只護特徵截止**，**不自動護**：

1. **分析時 `label_value` 公式**須與 `future_{h}bar_return` 同源（`bars_from_kline_cache`＋close→close／F-1 三元組），逐 (event,h) golden、`atol=0`；尾端不足 ⇒ None／loud，禁填 0。  
2. **D-7／purge**：`event_split.py:58-61` 之 embargo 取 `label_end_ms−label_start_ms`。若 IC 頁改 h 而仍用匯出烤入之舊窗 ⇒ **embargo 偏小＝洩漏**（§C0）。分析時必須重算 window／label_*_ms 並綁同次 split。  
3. **禁混用**：舊批烤入之 `label_value` 不得在 h 變更後靜默沿用。  
4. mutation：改 h 不重算 embargo；或用舊 `label_value` 覆蓋新 h ⇒ 紅。

⇒ brief assumed「不需新機制」**不成立**——不是新 PIT 哲學，但是**分析時 producer＋窗寬與 split 同步**之顯式 Task／golden（見補丁包）。

### 1.3 A-6？→ **舊 A-6 作廢**；改 **A-6′** 仍待白話閘

舊 A-6 問「多選附帶欄是否不動主答案窗／label 算法」——前提是「主答案窗住在匯出層餵條件 IC」。議題一成立後該前提為假 ⇒ **整問作廢**。  
殘留須使用者確認者＝**A-6′**：條件 IC 之 h／`label_value` 在 IC 頁分析時計算；`/search` 不烤條件 IC 用之 `label_value`。Excel 附帶 `future_*` 可保留（D-3 縮層）。**確認前不得 FROZEN**（FROZEN 條件③）。

### 1.4 同步集合（完整）

見補丁包 `SYNC-LOCI`：§A／A-6／D-3／D-7／Task 4.1／4.1b／4.1c／7.0b／F-1／F-4／7.4／V-6／檔頭 FROZEN 句／`ic_feed.py` 檔頭／白話勾選表 Phase 4。  
**群集 E（7.0b 匯出 API）整段納入重寫**，不得只加句「亦可於 IC 頁呼叫」。

---

## 2. R7 十二條 CLOSED／OPEN（反例，非「有寫」）

| 群集 | R7 病灶 | 本輪 | 反例／碼證 |
|---|---|---|---|
| A | F-14 閘數四→五 | **字面 CLOSED；harness OPEN** | 標題已「五支」且串 count-audit；但 `; echo $?` 假綠⇒P1-02；pre_review 仍指 r7⇒P1-03 |
| B | F-2「15→16」vs 1.1 `==20` | **CLOSED** | F-2 改「權威在 Task 1.1、不重述計數」（L1088-1091）；`grep 增為 16` 於 SPEC 無命中 |
| C | 7.7① ISO vs ④ epoch | **CLOSED** | ① 改指向 ④／epoch 秒字串（L1429-1431） |
| D | 7.3 漏 `control_kind` | **CLOSED** | 7.3 清單含 control_kind；4.1b 加「逐項對照」（L861-867、L1303-1310） |
| E | 7.0b 無 API／wiring | **原單位 CLOSED；架構下 REOPEN** | API 已寫入（L1164-1194）；議題一成立⇒匯出時 `label_value` API **錯層**⇒P0-01／P1-01 |
| F | 1.10 registry 內容 | **CLOSED** | `lookahead_unknown`＋mutation（L613-629） |
| G | canonicalSourceText↔S-9 浮點 | **CLOSED** | 明引 S-9 浮點 lexeme＋跨環境 digest（L494-508） |

---

## 3. 主委單方產出（brief 必查第 4）

| 項 | 判定 |
|---|---|
| `scripts/patch_locus_check.py` | 空 SYNC-LOCI⇒rc=2；`changed_files` 用 `git status -uall`（檔頭自陳曾 fail-open）——**反測成立**；誠實邊界「漏列看不見」仍成立 |
| `scripts/gap3ux_pre_review.sh` | 五常駐閘串好；**FACTS 鎖 r7** 而本輪 brief／facts 已是 r8⇒P1-03 |
| `docs/GAP3_EVENT_UX_ROLE_CARD.md` | 流程對；「五閘（含 locus）」與 brief「六閘」互斥⇒P2-01 |
| R7 驗收補寫 | B/C/D/F/G 對症；E 在舊架構對症、在議題一下須重寫 |

---

## 4. 全棧三欄稽核（事件＋IC＋FL＋`/search`）

| 能力 | 後端 | 前端 UI | wiring | 判定 |
|---|---|---|---|---|
| `/search` 二元 label | 契約／匯出 | search 匯出 | `positive_case`→label | 事實層 OK |
| 條件 IC `label_value` | ic_feed 讀事件表欄；「v1 不重算」 | IC 頁有 horizons（特徵 IC），**無**事件答案窗給定＋重算入口 | 7.0b 規劃在匯出呼叫 | **錯層**⇒P0-01 |
| 附帶 `future_*` | case_search 已算 | Task 4.1 規劃 | Excel 用 | 可保留；勿再綁 IC |
| purge／D-7 | split 綁 label 窗寬 | 4.1b／7.3 揭露 | 窗若烤死在匯出 | 分析改 h 必重算窗⇒P0-02 |
| FL／time_range | 7.7④ epoch | 對證 | R7 C 已閉 | OK |
| Feature IC horizons | 既有 | `ICConfigPanel` | 與事件條件 IC 不同通路 | 勿混為已交付「事件答案窗在 IC 頁」 |

---

## 5. §C0／計數／禁令

- §C0：議題一若半套用（IC 頁可改 h、split 仍用舊窗）⇒ **洩漏**，比維持舊錯層更糟——補丁包強制窗與 h 同次綁定。  
- 閘數五／六用語漂移＝計數字面病之文件版（P2-01）。  
- 短命工：4.1b→7.3 已標；架構調整後 7.0b 匯出 API 若先實作再拆＝**白工**——應直接落 7.0b′。

---

## §1 十一類摘要

1. 矛盾／互斥：有——舊 A-6／D-3(a)／4.1 vs 議題一；閘數五／六  
2. 端到端漏項：有——IC 頁無分析時 label 窗＋producer wiring  
3. 不可測驗收：有——F-14 假綠使「五閘 rc=0」不可依 facts 總碼  
4. Quant：有——P0-02 purge／label 重算  
5. 過度工程：無（分析時重算是能力釋放，非新框架）  
6. OOM：無（#9b 不受理）  
7. Cache：無新面  
8. API：7.0b 匯出 API 錯層  
9. 測試：須新增分析時 golden／mutation（補丁）  
10. Agent 可執行性：現 SPEC 依 4.1／7.0b 會實作錯層  
11. 短命工：先做匯出 7.0b 再搬 IC＝白工  

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 |
|---|---|
| assumed：議題一成立 | **成立**（碼證支持；無反證） |
| assumed：既有 PIT 規則即可護分析時 label_value | **不成立**⇒P0-02 |
| assumed：R7 十二條未引入新矛盾 | **B–D/F/G 成立**；E 在新架構下矛盾⇒P1-01；A harness 假綠 |
| assumed：補丁包流程壓自傷至 0 | **本輪首次實測前無法證**；harness 兩洞顯示清單同步病仍在 |
| assumed：locus 閘涵蓋足夠 | **誠實邊界成立**（漏列看不見）——非本輪升 finding |
| fact：六支閘皆 rc=0 | **部分不成立**——pre_review 常駐五支綠；F-14 對 count-audit 假綠；locus 僅有補丁時跑 |

---

## GROK-R8-P0-01

**斷言**: 條件 IC 之答案窗／`label_value` 應於 IC 分析頁分析時給定與計算；現行 SPEC 以 D-3(a)／A-6／Task 4.1／7.0b 把「主答案窗烤進 `/search` 匯出」定為條件 IC 權威 ⇒ 錯層，且強迫為換 h 而重匯出未變事件事實批。

**碼證**: `sed -n '75,85p' frontend/src/lib/eventExport.ts` → `label`←`positive_case`，`label_value`←`future_${horizon}bar_return`。`sed -n '1,6p' momentum/Analysis/event_samples/ic_feed.py` →「v1 不重算」。`sed -n '76,82p' momentum/Analysis/event_samples/pipeline.py` → `bars_from_kline_cache` 唯一入口。SPEC：`sed -n '113,119p;241,258p;841,850p;1150,1178p' docs/GAP3_EVENT_UX_SPEC.md`（D-3(a)／A-6／4.1／7.0b 匯出 API）。RECHECK：重跑上列；確認無「條件 IC 必須在 search 選窗」之碼證反例。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f；frontend/src/lib/eventExport.ts；momentum/Analysis/event_samples/ic_feed.py

[BLOCKING] 信心度=High。修法＝套用 `handoffs/patches/20260823-gap3ux-r8-arch-analyze-time-label.md`；A-6→A-6′ 白話閘。

---

## GROK-R8-P0-02

**斷言**: 若採分析時 `label_value`／h，卻假設「既有 `decision_time_rule`／`feature_cutoff_rule` 已足夠、不需新機制」，則 `event_split` 仍可能用匯出烤入之舊 `label_end_ms−label_start_ms` 當 embargo ⇒ 分析改大 h 時 purge 偏小，構成 train/test 洩漏（§C0）。

**碼證**: `sed -n '58,61p' momentum/Analysis/event_samples/event_split.py` → `embargo = … int(window.max())` 且 `embargo < window.max()` raise；window 來自事件列之 label 窗。`ic_feed.py:75-77` 特徵截止與 `label_window_rule` 分開。brief assumed L169-170。RECHECK：設想同批匯出 `horizon_bars=3`、IC 頁選 h=7 且不重算 label_*_ms——對照 split 公式。

**來源摘要**: momentum/Analysis/event_samples/event_split.py；handoffs/20260823-gap3ux-x-review-r8-brief.md；docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f

[BLOCKING] 信心度=High。修法＝同架構補丁之 D-7「分析時窗」＋ golden／mutation（改 h 不重算 embargo ⇒ 紅）。

---

## GROK-R8-P1-01

**斷言**: R7 群集 E 已把 Task 7.0b 補成「`POST /api/v1/case/label-values`＋匯出 `buildEventContractRecords` 只得經此取 `label_value`」；在議題一成立後，該 API／呼叫點落在**錯誤生命週期（匯出）**——原單位可稱 CLOSED，架構上必須 REOPEN 並重寫為分析時路徑，否則 Agent 會把錯層實作到 Frozen。

**碼證**: `sed -n '1164,1194p' docs/GAP3_EVENT_UX_SPEC.md`（端點＋前端呼叫點）。對照 P0-01 碼證。RECHECK：grep Task 7.0b 是否仍要求 search 匯出呼叫 label-values。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573f

[MAJOR] 信心度=High。修法＝架構補丁 §5（7.0b′）；禁止先實作匯出 API 再搬（白工）。

---

## GROK-R8-P1-02

**斷言**: `handoffs/20260823-gap3ux-x-review-r8-facts.sh` F-14 以 `cmd; echo count_audit=$?` 結尾，使 `spec_count_audit` 回傳 2 時 emit 仍見 **rc=0**，進而 `rc_all=0`——「五閘皆 rc=0」之 fact 總碼假綠（與 CLAUDE.md「`$?` 經 pipe／尾命令」同型）。

**碼證**: `sed -n '75,79p' handoffs/20260823-gap3ux-x-review-r8-facts.sh`。實跑：`python3 scripts/spec_count_audit.py --check docs/GAP3_EVENT_UX_SPEC.md --baseline handoffs/run_receipts/gap3ux-spec-count-baseline.txt` ⇒ rc=2（消失 r7-facts「五支機械閘」）；同命令經 `; echo count_audit=$?` 之 compound ⇒ **rc=0**。本輪 `facts.sh` 輸出含 `count_audit=2` 且 `rc_all=0`。RECHECK：重跑上列兩命令。

**來源摘要**: handoffs/20260823-gap3ux-x-review-r8-facts.sh#a3d9fdfb26af；handoffs/run_receipts/gap3ux-spec-count-baseline.txt

[MAJOR] 信心度=High。修法＝`handoffs/patches/20260823-gap3ux-r8-harness-f14-prereview.md` §1。

---

## GROK-R8-P1-03

**斷言**: `scripts/gap3ux_pre_review.sh` 硬編碼 `FACTS=handoffs/20260823-gap3ux-x-review-r7-facts.sh`，而本輪 brief／可重跑 receipt 已是 `…r8-facts.sh`；count-audit 對 SPEC＋r8-facts 與現行 baseline 配對 ⇒ rc=2，但 pre_review 因仍掃 r7 而顯示全綠——「唯一閘清單」與本輪 fact 腳本脫節（同型 R6/R7「加閘未進清單」）。

**碼證**: `sed -n '19,44p' scripts/gap3ux_pre_review.sh` → FACTS=r7。`python3 scripts/spec_count_audit.py --check docs/GAP3_EVENT_UX_SPEC.md handoffs/20260823-gap3ux-x-review-r8-facts.sh --baseline handoffs/run_receipts/gap3ux-spec-count-baseline.txt` ⇒ rc=2（＋r8／−r7 字面）。`bash scripts/gap3ux_pre_review.sh` ⇒ rc=0。RECHECK：同上。

**來源摘要**: scripts/gap3ux_pre_review.sh#e489b7908fdb；handoffs/20260823-gap3ux-x-review-r8-facts.sh#a3d9fdfb26af

[MAJOR] 信心度=High。修法＝harness 補丁 §2–3（改 FACTS＋重產 baseline）。

---

## GROK-R8-P2-01

**斷言**: 閘數權威用語在 ROLE_CARD「五閘（含 locus）」、brief「六閘／六支」、HANDOFF「六支」又「五支＋locus」之間互斥，Agent／主委可各取一字面更新 F-14／角色卡而再犯計數漂移。

**碼證**: `grep -n '五閘\|六閘\|五支\|六支' docs/GAP3_EVENT_UX_ROLE_CARD.md handoffs/20260823-gap3ux-x-review-r8-brief.md HANDOFF.md`。RECHECK：同一 grep。

**來源摘要**: docs/GAP3_EVENT_UX_ROLE_CARD.md；handoffs/20260823-gap3ux-x-review-r8-brief.md

[MINOR] 信心度=High。修法＝harness 補丁 §4：常駐五支＋有補丁時 locus＝最多六；禁「五閘（含 locus）」。

---

## Suggestions（非 finding）

- 既有事件 JSON 已含 `horizon_bars`／`label_value`：遷移策略在補丁已點「分析用副本覆蓋」；實作 TODO 須寫清是否保留欄位作 audit trail。  
- CSV 自帶 `label_value` vs IC 頁改 h：補丁要求二擇一寫死——建議預設「匯入鎖定、禁改 h」較不易靜默錯。  
- `patch_locus_check` 不驗「改得對不對」——本輪架構補丁之 VERIFY 條須在套用後由主委實跑，不能只靠 locus 綠。

---

ASSUMPTIONS_VERIFIED: SPEC sha256＝brief 鎖定；dims rc=0；議題一碼證（eventExport／ic_feed／bars_from_kline_cache／event_split）實讀；R7 B–D/F/G 反例 CLOSED；E 匯出 API 有字但架構 REOPEN；F-14 compound 假綠；pre_review FACTS=r7 vs r8 drift；patch_locus 空 loci rc=2。  
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`→鎖定相符；`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh`→宣稱 rc_all=0 且 F-14 印 count_audit=2；`python3 handoffs/20260823-gap3ux-x-review-r8-dims.py`→rc=0；`bash scripts/gap3ux_pre_review.sh`→rc=0；count-audit 單 SPEC→2；SPEC+r8-facts→2；SPEC+r7-facts→0；compound echo 實驗→0；空 loci patch→2；收尾 completeness 見下。未跑產品 pytest／vitest（review-only）。  
FAILURES_SEEN: facts 總碼與 F-14 內 count_audit 不一致（記為 P1-02，非工具故障）  
SCOPE_CHANGES: none（補丁包為交件，未改 SPEC／碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改產品；補丁若套用將改變 label_value 生命週期與契約欄語意——標在補丁包）  
OUTPUT: handoffs/20260823-gap3ux-x-review-r8-grok.md；handoffs/patches/20260823-gap3ux-r8-arch-analyze-time-label.md；handoffs/patches/20260823-gap3ux-r8-harness-f14-prereview.md

STATUS: DONE
