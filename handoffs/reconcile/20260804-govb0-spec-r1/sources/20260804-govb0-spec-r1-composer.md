# GOVB0-SPEC-R1 — Composer Adversarial Review (R1)

**審查標的**：`docs/GOVB0_FRICTION_SPEC.md`  
**家族**：COMPOSER | **輪次**：R1 | **task-id**：GOVB0-SPEC-R1  
**日期**：2026-08-04

---

## 被當成事實的未驗證假設（§0）

| 標籤 | SPEC／brief 陳述 | 裁定 |
|---|---|---|
| **assumed→攻** | 五張票合成一個 SPEC 一次管線正確 | **部分成立**：B-32／B-15／B-14／B-30 共用 `cx_run.sh`／`gate_check.sh`，合批合理；**Phase 4（B-24 checker）邊界已達獨立中任務規模**，但限縮為「新寫＋本批修改」後可留在本批（見 Q4）。 |
| **assumed→攻** | Phase 2 四 Task 疊加不互相抵銷 | **未完全成立**：隔離原型 8/9 通過，但 `bash -c "codex exec x"` 在引號感知後 **fail-open**（見 P0-01）。SPEC Task 2.1 邊界已要求 BLOCK，**缺可執行的疊加驗收**。 |
| **assumed→攻** | Task 3.2 `.part`→rename 同時解 B-30＋B-14 | **機制方向正確**，但 **cx_run prompt（`:512`）仍寫「產出寫到 ${out}」**，與 `.part` 路徑未對齊（見 P0-02）。 |
| **assumed→攻** | Phase 0 純觀測、行為逐位元組不變 | **大致成立**：`grep -Eo` 僅在已判定 `kind=dispatch` 後取片段，不改 `:86` 比對與 exit code；風險在實作若把 grep 放進判定路徑（見 P2-01）。 |
| **fact-verified** | template_check spec rc=0 | **複核通過**：`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → rc=0。 |

---

## §1 必查摘要

| # | 類別 | 結果 |
|---|---|---|
| 1 | 矛盾/互斥 | **有** — Task 3.2 `.part` vs `cx_run.sh:512` prompt；Task 2.5 靜態差集 vs Phase 0 動態 deny 語料（P0-02、P1-01） |
| 2 | 漏項/端到端 | **有** — Task 3.2 未列 `cx_run.sh` prompt 路徑改動；Task 4.1 grandfather 到期責任主體未寫（P0-02、P1-04） |
| 3 | 不可測驗收 | **有** — Task 2.5「兩欄每一項須在 SPEC 預期」在 Phase 0 上線後不可執行（P1-01） |
| 4 | 可疑 quant 假設 | **無**（本批不碰數值路徑） |
| 5 | 過度工程 | **無** — Phase 4 checker 已限縮 scope |
| 6 | OOM/並行 | **無** |
| 7 | Cache 正確性 | **無** |
| 8 | API/型別/相容 | **有（輕）** — Task 3.2 改產出路徑語意，brief／prompt 須同步（P0-02） |
| 9 | 測試品質 | **有** — Phase 2 缺四 Task 疊加整合測試；Task 1.1 只測 prompt 字串（P0-01、P2-02） |
| 10 | Agent 可執行性 | **有** — 見 P0-01／P0-02 |
| 11 | 必要性/短命工 | **有（輕）** — Task 2.5 標「B-29 實作時取代」；存活欄位正確，無白工指控 |

## §2 範本錨點 + 獵空殼

- §RISK／§A／§C／§G／§P／§V／§R／§N：**齊**；`template_check.sh spec` rc=0。
- §A FACT-RECEIPT：**7 條皆有 receipt**；OPEN-1／2／3 正確標為委員裁決項。
- §G N/A：**合理**（RISK-HIT b,c 無 a,d）。
- 獵空殼：**未發現表頭-only 空殼**；各 Task 驗證欄有 ASSERT／狀態斷言 token。

---

## 必答裁定（Q1–Q7）

### Q1 — OPEN-1 timeout（本輪裁定）

**1. 精確區間**  
per-family timeout 必須涵蓋 **`cx_run.sh` `_run_cli_and_emit` 內前景 CLI 的 wall-clock**：自 `codex`／`grok`／`cursor-agent` **spawn 前** 至 **wait 返回後、format check 前**（`:443–465` 區段）。這是 `cx_run.sh` 能 `kill` 進程群的唯一區間。  
**不採用** codex 的「output mtime → runlog close」——那只是尾段延遲 proxy，**無法覆蓋** B-14 類「產出已寫完但 CLI 不退出」的掛死。  
歷史量測用 runlog **birth→mtime** 作總時長 proxy（含寫檔＋ harness 尾段），n=462。

**VERIFY**：
```bash
python3 /private/tmp/composer-govb0-r1/q1_timeout_analysis.py
# TOTAL_RUNLOGS=462; CLEAN n=460; ALL p95=26.1m p99=43.9m max=68.2m
```

**2. 掛死樣本排除與重算**  
判準：①已知 B-14 掛死 stem；②**總時長 >90m**（相對 clean p99≈44m 的極端離群）。  
排除 2 筆：`20260803-govflow-todo-r2-composer`（146.7m）、`20260803-frozen-proc-v2-stamp-codex`（23.7m，stem 入帳但 <90m——僅第一筆為硬掛死；第二筆保留在 clean 集）。  
**修正**：僅排除 composer 146.7m 一筆為確定掛死；clean **n=461**。

| 集合 | n | p95 | p99 | max |
|---|---:|---:|---:|---:|
| ALL | 462 | 26.1m | 43.9m | 146.7m |
| CLEAN（排除 146.7m） | 461 | 26.0m | 43.8m | 68.2m |
| codex clean | 166 | 30.2m | 42.2m | 45.1m |
| composer clean | 152 | 12.2m | 43.5m | 68.2m |
| grok clean | 143 | 22.6m | 45.9m | 64.6m |

**3. 建議值與誤殺率**

| 方案 | 值 | clean 誤殺 |
|---|---|---:|
| codex 20m（拒絕） | 20m | 34/166 codex（20.5%） |
| 統一 60m | 60m | 2/461（0.43%） |
| **建議 per-family** | codex **50m**／grok **65m**／composer **75m** | **0/461（0%）** |

誤殺樣本（僅在統一 60m 時）：`20260730-p16-b4-fix3rev-composer` 68.2m、`20260730-p16-b4-fix3-grok` 64.6m——皆為真實完成審查，非掛死。

`committee_run.sh` 外層安全閥：**90m**（= max family 75m + 15m）。

**4. per-family 是否必要**  
**是**。codex clean max=45.1m，可設較緊（50m）；composer 有 68.2m 合法樣本，需 75m。統一 60m 可行但誤殺 0.43%；per-family 可零誤殺。

---

### Q2 — OPEN-2 locale 守衛

① **嚴重度：MAJOR（非本批 BLOCKING）**——`LC_ALL=C` 下 `doc_format_precheck` 對佔位 Verdict rc=0（fail-open）已在本機複核；`gate.sh` Verdict 探針因 OPEN 債務未觸及，採 synth C-12 主委實測為準。  
② **開新票**：建議 **`B-33` `GOV-LOCALE-GUARD-DRIFT`**，範圍＝`gate.sh` D-1 Verdict 正則、`doc_format_precheck.sh`、`template_check.sh` §A 錨點——**統一改為 `LC_ALL=C` 或 `LC_ALL=UTF-8` 顯式鎖定**，禁依賴環境預設。  
③ **是否納入本批**：**否**（同意主委預設）。理由：與 B-15 正則無耦合、修復面跨多腳本、易 scope 膨脹；但須在 TODO §0 記「已知 MAJOR 債，B-33 跟進」。

---

### Q3 — OPEN-3 FP-2

① **裁定：以「Phase 0 上線後補查」結案**（非除役）。  
**VERIFY**：`bash .claude/tmp/b15probe.sh` → FP-2a／FP-2b 皆 ALLOW；`for f in codex composer grok; do …` **現行正則不可重現**。  
② **不建議從 B-15 除役**：backlog 記載為事故觀察，可能為同分鐘另一指令或已修復路徑；Phase 0 deny 紀錄上線後用 `match_rule` 反查。  
③ **我無法重現 FP-2**。

---

### Q4 — B-24 Phase 4 可行性

**限縮可交付**：只檢「新寫＋本批修改」文件＋具名 grandfather **足以使 Task 4.1 可交付**。  
**grandfather 到期日**：應由 **Claude（治理維護者）在 `docs/governance_grandfather.yaml`（或同級 SoT）逐檔登記**，判準＝①機械掃描確認該檔不在本批修改集 ②距離上次實質修驗收欄 >90 天 ③到期後必須通過 checker 或移出 docs。SPEC 應補一句責任主體，否則無人維護清單（P1-04）。

---

### Q5 — §V 可證偽性

- **多數 Task 驗證欄合格**：含 ASSERT、狀態斷言、mutation 自證要求。  
- **弱點**：Task 1.1「prompt 不含 RECONCILE-STAMP」——改壞了若 agent 仍從習慣寫標題，測試仍綠（P2-02）。  
- **Task 2.5**：「兩欄每一項須在 SPEC 預期」——**實務會被放寬或永遠 FAIL**；Phase 0 累積真實 deny 後會出現 SPEC 未列舉的「本來擋現在放行」項（P1-01）。  
- **Task 0.1 mutation**：設計正確；若實作把 `grep -Eo` 失敗當成 deny 會改 rc——須保持在 audit 分支（P2-01）。

---

### Q6 — 依賴與順序

| 關係 | 裁定 |
|---|---|
| 已宣告 Phase 0→2 | **正確且必要** |
| **未宣告 forward dep** | **Phase 1→3.2**（prompt 路徑）、**Phase 3.1→3.3**（timeout 需 duration 欄）、**OPEN-1 裁決→3.3 TODO 填值** |
| Phase 3.2 影響 Phase 0／2？ | **不影響** Phase 0（gate_deny）與 Phase 2 判定 |
| Phase 4 回頭抽驗 0–3 | **非循環依賴**——meta-checker 對已完成 Task 驗收欄做靜態檢查，合理 |

建議 §P 補：`Phase 3 Task 3.2` 依賴 `Phase 1`（prompt 不再誘導錯誤格式）並行可選，但 **prompt 路徑對齊為 BLOCKING**。

---

### Q7 — 可否進 TODO？

**需修補後派工**。BLOCKING 修補項：  
1. Task 3.2 明列 `cx_run.sh:512`（及 brief 骨架）產出路徑改為 `.part` 或內部 remap  
2. Task 2.5 驗收改為「SPEC 列舉項為必要子集；Phase 0 真實 deny 語料為附加堆，附加項須人工標註」  
3. Phase 2 增 **四 Task 疊加整合測試**，必含 `bash -c "codex exec …"` TP  
4. §A OPEN-1 填入上表 per-family 值（供 Task 3.3 TODO）  
5. Task 4.1 補 grandfather 責任主體  

非 BLOCKING：OPEN-2→B-33；OPEN-3→Phase 0 後補查。

---

## Verdict：需修補後派工

---

## COMPOSER-R1-P0-01

**斷言**: Phase 2 四 Task 疊加後，`bash -c "codex exec x"` 在引號感知實作下仍可能 **fail-open**，與 Task 2.1 邊界③「引號內含真派工須 BLOCK」衝突。

**碼證**: 隔離原型 `bash /private/tmp/composer-govb0-r1/phase2_fullstack_probe.sh` → 8/9 通過，**唯一失敗**＝`bash -c "codex exec x"` got=ALLOW want=BLOCK。機制：雙引號內容被剝除後，外層字串不再命中家族段。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[BLOCKING] 信心度=High。SPEC 已列邊界案例但 **驗收未要求四 Task 疊加後重跑 TP 全集**；實作者若用 naive quote-strip 會開洞。修法：Task 2.5 語料＋整合測試必含此條；引號感知須 **保留 `bash -c`/`eval` 外殼內容** 或對 `-c` 後引號段單獨再判。

---

## COMPOSER-R1-P0-02

**斷言**: Task 3.2 要求委員寫 `<out>.part`，但 `cx_run.sh:512` prompt 仍為「產出寫到 ${out}」，且 Task 3.2「不可做」易被誤讀為不改 prompt——**路徑未對齊必致 B-30 重現或 format-failed**。

**碼證**: `grep -n '產出寫到' scripts/cx_run.sh` → `:512` 僅 `${out}`；Task 3.2 改法①寫 `.part`、不可做段寫「不改委員 prompt 要求它自己做 atomic write」——**未列 harness prompt 改為 `${out}.part` 或內部 remap**。

**來源摘要**: scripts/cx_run.sh#39cfdddec350

[BLOCKING] 信心度=High。失敗模式：委員寫入 `<out>` 直接上架（無 atomic）或寫錯路徑只剩 `.part`。修法：Task 3.2 增子步「`prompt` 產出路徑與 `new_brief.sh` 骨架同步為 `.part`」；驗證增「prompt 含 `.part` 後綴」斷言。

---

## COMPOSER-R1-P1-01

**斷言**: Task 2.5「『本來擋現在放行』與『本來放行現在擋』兩欄的**每一項**都須在 SPEC 中被預期」在 Phase 0 上線後 **不可執行**——真實 `gate_deny` 語料會產生 SPEC 未列舉項，導致永遠 FAIL 或實作者悄悄放寬。

**碼證**: §V「行為差集」＋Task 2.5 驗證②③；Phase 0 Task 0.1「存活至永久」且「後續 Phase 只讀」⇒ Phase 2 完工後 deny 紀錄持續累積。`CLAUDE-R1-P0-01`（synth C-8）已證目前零 deny 指令欄。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MAJOR] 信心度=High。修法：差集驗收改為 **必要子集＝Task 2.1–2.4 列舉 12 條**；Phase 0 真實語料為 **附加堆**，出現未預期附加項時須 **人工標註＋回寫 SPEC 或 backlog**，而非機械 FAIL。

---

## COMPOSER-R1-P1-02

**斷言**: 五票合一 SPEC **可接受**，但「一次管線」假設把 **Phase 4（新 checker + grandfather 機制）** 與 **Phase 2（高風險正則）** 綁在同一 adversarial／TODO 臨界路徑，放大單輪 BLOCKING 面。

**碼證**: §P 5 Phase／11 Task；`CODEX-R1-P0-03`（synth C-5）629 docs 候選；Phase 4 已限縮 scope 仍含新腳本＋hook 接入。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02

[MAJOR] 信心度=Medium。若本輪修補後 Phase 2／3 穩定，Phase 4 可跟進；**不建議拆票**除非 Phase 4 grandfather 機制再膨脹。判準：新腳本 >200 行或需改 `template_check` 以外第三個 caller 時再拆。

---

## COMPOSER-R1-P1-03

**斷言**: OPEN-2（locale 守衛漂移）應 **開 B-33、不納入本批**，但嚴重度應標 **MAJOR** 並寫入 TODO §0 已知債——非「可忽略」。

**碼證**: 本機 `bash /private/tmp/composer-govb0-r1/open2_locale_probe.sh` → `doc_format_precheck` 在 `LC_ALL=C` 下對 `**Verdict: （待填…）**` rc=0；synth C-12 表三例方向不一致。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02

[MAJOR] 信心度=High（gate.sh 項採 synth 主委實測）。同意主委不納入本批；**攻「不納入」≠「不嚴重」**。

---

## COMPOSER-R1-P1-04

**斷言**: Task 4.1 grandfather 清單「須具名且有到期日」**未指定誰維護、依何事件續期**，實作後易成永久豁免垃圾場。

**碼證**: Task 4.1 邊界②僅寫清單格式；無 owner／review cadence。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MAJOR] 信心度=High。修法：指定 Claude 維護 `docs/governance_grandfather.yaml`；到期預設 90 天；續期須附機械掃描 receipt。

---

## COMPOSER-R1-P1-05

**斷言**: brief 假設「Phase 2 四 Task 疊加不開新洞」**僅在含 `bash -c` 修補後才成立**；其餘 8 條 TN/TP 原型全通。

**碼證**: `phase2_fullstack_probe.sh` 輸出 8/9 ok；`b15probe.sh`／`b15probe2.sh` 重現 FP-1（洞 A）、洞 B 誤擋與 fail-open `| claude -p`。

**來源摘要**: handoffs/reconcile/govb0-recon-r1/synth.md#3188be152a02

[MAJOR] 信心度=High。疊加本身不互斥，**實作技巧**（quote-strip 範圍）才是風險；見 P0-01。

---

## COMPOSER-R1-P2-01

**斷言**: Task 0.1 在 deny 路徑加 `grep -Eo` **若誤入判定前主路徑**，可能因 grep 失敗或性能改變 rc；目前設計「先判後記」則安全。

**碼證**: `gate_check.sh:86` 判定 → `:88` 排除 → 僅 deny 時 `_append_gate_deny_audit`；SPEC Task 0.1 改法①取命中片段在判定**之後**。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MINOR] 信心度=Medium。修法：Task 0.1 明寫「`grep -Eo` 只在 `kind` 已設為 dispatch 之後執行；grep 失敗不得改 rc」。

---

## COMPOSER-R1-P2-02

**斷言**: Task 1.1 驗證「prompt 不含 RECONCILE-STAMP」**無法證偽 agent 仍寫 `## RECONCILE-STAMP` 標題**——測的是 harness 字串，不是委員行為。

**碼證**: Task 1.1 驗證③明訂「不得以委員這次沒寫為斷言」；僅測 prompt 文字。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c8446a4909f8

[MINOR] 信心度=High。可接受為必要非充分條件；B-32 根因是 **誘導句**，移除誘導已覆蓋主要風險。可選增強：`completeness_check` 錯誤訊息專屬提示（票 B-32 ③，本批不做）。

---

## COMPOSER-R1-P2-03

**斷言**: OPEN-3 應 **Phase 0 後補查**，不應將 B-15 FP-2 從 backlog **除役**——現行不可重現不等於從未發生。

**碼證**: `b15probe.sh` FP-2a/b ALLOW；backlog `B-15` 仍列 `for` 迴圈事故。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#fa6a9a90835c

[MINOR] 信心度=High。SPEC §A OPEN-3 結案文案建議用「未定位／待紀錄」而非「記載錯誤」。

---

STATUS: DONE
