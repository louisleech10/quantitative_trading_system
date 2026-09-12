# DOCROT R1 — COMPOSER（委員獨立偵察）

task-id: 20260912-DOCROT-X-CONSULT-R1  
family: COMPOSER  
brief: `handoffs/20260912-DOCROT-CONSULT-R1-BRIEF.md`  
findings-round: R1

## 被當成事實的未驗證假設（§0）

| 假設 | 判定 | 否證／碼證 |
|---|---|---|
| 使用者「7 成時間浪費在修文檔」之分母＝**輪數**而非 commit | **部分成立** | b9 十二輪審查＋十三次 SPEC 修訂、Task 9.1 **尚未開工**；2026-09-01 起 doc-only commit 205 vs code-only 72（見必答 1） |
| 此問題**有解**（非協作固有成本） | **部分成立** | 十二輪後面向已收斂（R12 七群全打 v12 自修），剩餘為資訊結構＋閘缺口；全換文檔體系**不值得**（必答 6） |
| 不看主委版本仍可獨立界定問題 | **成立** | 本輪僅用 git／synth／SPEC／閘腳本實跑，未讀 `handoffs/20260912-docrot-x-consult-r1-claude.md` |
| `RECONCILE-STAMP APPROVED`＝0 代表「沒收斂」 | **需修正** | 0 代表**未走正式 stamp 流程**，不等於內容未閉；但與「十二輪全綠」敘述並存會製造假安全感 |

fact-verified: 使用者原話逐字見 brief L29–34  
fact-verified: `git log -- docs/SPLITUNIFY_SPEC.D-002.md` → 14 commits（含初稿）  
fact-verified: `grep -c 'RECONCILE-STAMP.*APPROVED' handoffs/reconcile/20260911-splitunify-b9-review-r*/synth.md` → **0**

---

## 必答 1 — 我自己量到什麼

| 量測 | 指令 | 結果 |
|---|---|---|
| SPEC 修訂次數 | `git log --oneline -- docs/SPLITUNIFY_SPEC.D-002.md \| wc -l` | **14**（十三次修訂＋初稿） |
| 十二輪 synth finding 總數 | `for r in $(seq 1 12); do rg -c '## (CODEX\|COMPOSER\|GROK)-R'"$r"'-P' handoffs/reconcile/...-r"$r"/synth.md; done` | **164**（15/11/15/8/11/16/15/14/21/13/12/13） |
| finding 趨勢 | 同上序列 | **無下降**；R9 峰值 21，R12 仍 13 |
| R11+R12 群集主題 | `awk` 掃 synth 群集表（見碼證） | **11/13** 群集含「上一版／字面／同步／條數／v11/v12」字樣；**0** 群集為全新設計面向 |
| 2026-09 以降 commit 類型 | `git log --since=2026-09-01` 分類 doc／code／mixed | doc-only **205**、code-only **72**、mixed **107**；純文檔佔非 mixed 的 **74%**（205/(205+72)） |
| 狀態敘事散落 | `rg -l 'v13\|十二輪\|164 條\|29 條' docs/ HANDOFF.md 白話說明/` | **30** 檔（不含 handoffs/） |
| 單一決定多落點 | `rg -c 'validate_split_pair_integrity' docs/SPLITUNIFY_SPEC.D-002.md` 等 | validator **5** 處、`metadata.split_unify` **11** 處、`[0-9]+ 條` 字面 **27** 處 |
| 閘在矛盾檔上仍綠 | 見 COMPOSER-R1-P1-02 碼證 | obligation／format／xref **rc=0**（修訂後 v13） |
| RECONCILE-STAMP | `grep -c 'RECONCILE-STAMP.*APPROVED' handoffs/reconcile/.../synth.md` | **0**／12 synth |

**量測取捨**：未量「agent token 分鐘」——無可重跑 receipt；commit 分母**低估**輪內反覆（一輪可多次 amend 不 commit）。

---

## 必答 2 — 問題是什麼（我自己的話）

**核心病**：規格與周邊文檔把**同一決定**複製到 Task、§V、mutation 表、register、(5.x)、§R、沿革、HANDOFF、白話進度表等多個**無索引**位置；修一處時靠記憶同步，漏改產生**同檔矛盾**（R12 O1/O3：Task 寫「不在 derive 呼叫」、§V 仍寫「derive 必呼叫」）。審查輪次因此變成**字面一致性稽核**，而非架構探索——十二輪 164 條 finding 後 R12 仍 13 條且**全打 v12 自修**，實作尚未開始。

**使用者體感「7 成」**：以 b9 **輪數**分母大致成立（12 審查輪 vs 0 impl 輪）；以 **commit** 分母約 74% 觸文檔。體感偏高因一輪內含主委修訂＋三家審＋收斂＋閘，牆鐘遠大於 commit 數。

---

## 必答 3 — 根因（排序）

1. **資訊結構（主因）**：一決定五處以上複述、無機械「決定→落點」索引（碼證：`validate_split_pair_integrity` 5 處、`metadata.split_unify` 11 處）。
2. **編輯模式（次因）**：「插入新說法、不刪舊說法」——R12 O1 同段 metadata 既併入殘留又留 §V 斷言；沿革段保留 v11/v12 舊數字敘述。
3. **閘取向（次因）**：`spec_xref_check` 驗 synth 處置字面與 SPEC **token 對齊**，不驗 Task↔§V↔mutation **語意一致**；三閘全綠時仍可互斥（見 P1-02）。
4. **流程（三因）**：flat finding 曲線未觸發早停直到 R12 人工判「全打自修」；`RECONCILE-STAMP APPROVED=0` 使「收斂」無機械背書。

---

## 必答 4 — 修法（可機械驗證）

| 優先 | 機制 | 判定指令 | 成效指標 |
|---|---|---|---|
| P0 | **決定落點清單** `docs/decisions/SPLITUNIFY-D002.yaml`：每決定 `id`＋`grep_patterns[]`＋`canonical_file:line`；其他處只許 `見 DEC-xxx` | `bash scripts/decision_coverage_check.sh docs/SPLITUNIFY_SPEC.D-002.md`（新腳本：YAML 內每 pattern 在 SPEC 命中數＝1，且 Task/§V/mutation 三者 pattern 集合相等） | 下一輪「Task 改了 §V 沒改」類 finding **下降 ≥50%** |
| P1 | **條數字面禁複述**：允許 `[0-9]+ 條` 僅出現在 register 表標題行號集合 | `rg '[0-9]+ 條' docs/SPLITUNIFY_SPEC.D-002.md \| awk -F: '$1 !~ /L90\|L92/' \| wc -l` → **必為 0**（行號寫入 allowlist） | 「條數與表不符」finding **→0** |
| P1 | **同 commit 耦合**：改 `docs/SPLITUNIFY_SPEC.D-002.md` 中 `Task 9.` 或 `§V` 時，同 commit diff 必觸 `M-SU-D2-` 或反之 | `scripts/spec_section_coupling_check.sh` 比對 staged diff 路徑集合 | 互斥句（O3 型）**首輪即紅** |
| P2 | **狀態 SoT**：`HANDOFF.md` 唯一寫 vN／輪次／條數；`白話說明/*` 只許 `見 HANDOFF.md#<anchor>` | `rg 'v1[0-9]|十二輪|164 條' 白話說明/*.md` 命中須含 `見 HANDOFF` 或為歷史引用塊 | 白話數字漂移 **→0** |
| 紀律型 | 改決定前 `rg` 全檔（**禁 grep -v 排除**） | 人工；HANDOFF 已寫但無機械 enforcement | 自證④型漏抓不降為 0 |

**不修**：再擴第四套治理閘（HANDOFF 已定）；全庫單一 Markdown（成本＞收益）。

---

## 必答 5 — 範圍判定

| 文檔類 | 同病？ | 碼證 |
|---|---|---|
| `docs/SPLITUNIFY_SPEC.D-002.md` | **是（最重）** | 5/11/27 多落點；R12 七群全源於此 |
| `HANDOFF.md` | **是（狀態複述）** | 與白話／ROADMAP 同寫 v13、十二輪、29 條；47 行仍密碼 |
| `docs/SPLITUNIFY_TODO.md` | **是（延後同步）** | R12 codex 註「TODO §E xref FAIL 為既有延後」；Task 與 SPEC 雙寫 |
| `handoffs/reconcile/*/synth.md` | **是（敘事再複述）** | 群集表重抄 SPEC 段落＋處置；byte-faithful 附錄再翻倍 |
| `白話說明/*.md` | **是（看板平行副本）** | 22 檔、GAP-3 相關 **8** 檔；`SPLITUNIFY施工進度.md` 自寫 164/29 |
| `docs/VERDICTGATE_SPEC.md` | **輕（範本型）** | 機械 ID／VERDICT 塊；矛盾少，但與 `governance_verdicts.json` 雙源 |
| `docs/ROADMAP.md` | **是（戰術摘要漂移）** | `rg` 命中 v13／十二輪；與 HANDOFF 並行維護 |

---

## 必答 6 — 是否不值得解

**不值得全解**：多 agent 審查＋ reconcile synth 對高風險 quant 規格有價值；**不值得**為 b9 再派第 13 規格審查輪（R12 已觸停輪：全打自修、無新面向）。

**值得局部解**：①決定落點索引＋②條數單源＋③Task/§V/mutation 同 commit 耦合——三者 ROI 高、可機械驗證，且 DIRECTLY 對應 R11–R12 十一條 doc-sync 群集。

**判準（何時停修文檔、開工）**：連續兩輪 synth 群集 **≥80%** 標為「上一版修法／字面同步」且 **P0 新設計面向＝0** → 停審查、impl 用 pytest 抓殘（R12 已符合）。

---

## COMPOSER-R1-P0-01

**斷言**: `docs/SPLITUNIFY_SPEC.D-002.md` 將單一決定複製到 ≥5 個無交叉引用索引的區段，是十二輪「修了 A 漏 B」的**結構主因**，非單純紀律問題。

**碼證**: `rg -n 'validate_split_pair_integrity' docs/SPLITUNIFY_SPEC.D-002.md` → **5** 命中（Task 9.2b、§V、mutation 等）；`rg -n 'metadata\.split_unify' docs/SPLITUNIFY_SPEC.D-002.md` → **11** 命中；R12 synth O3 逐字：Task「**不在 derive 內呼叫**」vs §V「**derive 路徑確實呼叫**」。RECHECK: 對讀 `handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md` 群集 O1/O3。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#9de6da3ca5b8;handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md

[BLOCKING] 信心度=High。每次修訂必漏一處 ⇒ 輪數膨脹、實作延後。**修法**：必答 4 之決定落點 YAML＋`decision_coverage_check.sh`；SPEC 內非 canonical 處改為 `見 DEC-<id>`。**可行性**：YAML＋rg 計數為現有工具可實作；試跑邏輯＝對 `validate_split_pair_integrity` 五處抽取動詞片語，不一致即 exit 1。

---

## COMPOSER-R1-P1-01

**斷言**: b9 十二輪審查 finding 總數 **164**、末輪 **13**，曲線**無下降**，邊際主要消耗在修文檔一致性而非新架構缺陷。

**碼證**: 各輪 synth 計數 15/11/15/8/11/16/15/14/21/13/12/13；R11 synth L20「本輪 12 條**首度全為我上一版修法本身的缺陷**」；R12 synth L19「**無一為新面向**」。`git log --oneline -- docs/SPLITUNIFY_SPEC.D-002.md` 最近三條 commit message 含「打我上一版」「兩個條數同時活在文件裡」。RECHECK: `for r in $(seq 1 12); do rg -c '## (CODEX|COMPOSER|GROK)-R'"$r"'-P' handoffs/reconcile/20260911-splitunify-b9-review-r"$r"/synth.md; done`

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md;docs/SPLITUNIFY_SPEC.D-002.md#9de6da3ca5b8

[MAJOR] 信心度=High。使用者「7 成浪費」以輪數分母**可量化支持**。**修法**：採必答 6 停輪判準寫入 `docs/ROADMAP.md` 機械條款；連兩輪 doc-sync 占比 ≥80% 自動停審。**可行性**：`awk` 掃 synth 群集表關鍵字占比即可腳本化。

---

## COMPOSER-R1-P1-02

**斷言**: `obligation_block_check`、`doc_format_precheck`、`spec_xref_check --synth` 三閘全 **rc=0** 時，SPEC 仍可有 Task↔§V **互斥**——閘驗格式與 xref token，不驗跨區段語意。

**碼證**: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md docs/SPLITUNIFY_SPEC.D-002.md` → rc=0。但 R12 O3 證實 derive／validator 三處互斥在修訂前存在。RECHECK: 重跑三命令＋讀 R12 synth O3。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#9de6da3ca5b8;scripts/spec_xref_check.sh

[MAJOR] 信心度=High。假綠閘放大「又浪費一輪才發現」。**修法**：必答 4 之 `spec_section_coupling_check.sh`（同 commit Task+§V+mutation 聯動）。**可行性**：僅比對 git diff 路徑與行號集合，無需 NLP。

---

## COMPOSER-R1-P2-01

**斷言**: 施工狀態（v13、十二輪、164 條、29 register）同時寫在 **≥30** 份非 handoff 文檔，任一處漏改即製造「前幾輪修過又重修」體感。

**碼證**: `rg -l 'v13|十二輪|164 條|29 條' docs/ HANDOFF.md 白話說明/` → **30** 檔；`白話說明/SPLITUNIFY施工進度.md` L50/L74 自記 164／29，與 SPEC register 表標題雙源。RECHECK: 重跑 rg；改 HANDOFF 一處數字後 grep 白話是否仍舊值。

**來源摘要**: HANDOFF.md#390c9d87e933;白話說明/SPLITUNIFY施工進度.md

[MINOR] 信心度=High。**修法**：狀態只寫 HANDOFF anchor；白話只留指標。**成效**：`rg` 白話不含 `見 HANDOFF` 的數字句 → 0。

---

## COMPOSER-R1-P2-02

**斷言**: `白話說明/` 對 GAP-3 存在 **8** 份平行看板，放大同一 epic 的多處同步成本。

**碼證**: `ls 白話說明/GAP-3*.md | wc -l` → **8**；`ls 白話說明/*.md | wc -l` → **22**。HANDOFF L34 已具名六份重疊但未合併。RECHECK: `ls 白話說明/GAP-3*.md`

**來源摘要**: HANDOFF.md#390c9d87e933

[MINOR] 信心度=High。**修法**：使用者選定唯一看板檔，其餘改 stub 指標；`scripts/whitelist_single_board.sh` 拒絕向非白名單 GAP-3 檔新增行。**紀律成分**：白名單需使用者裁定（HANDOFF 已記）。

---

## COMPOSER-R1-P3-01

**斷言**: 十二份 b9 synth 的 `RECONCILE-STAMP APPROVED` 計數為 **0**，與「十二輪收斂」敘述並存，使「已修完」無機械 stamp 可稽核。

**碼證**: `grep -c 'RECONCILE-STAMP.*APPROVED' handoffs/reconcile/20260911-splitunify-b9-review-r*/synth.md` → 每檔 0、合計 0。RECHECK: 同上 grep。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md

[MINOR] 信心度=Medium。不阻實作但增加「到底收沒收斂」摩擦。**修法**：停輪後單次 `reconcile_build --mode review`＋stamp；或敘述改「功能停輪」≠「stamp APPROVED」。

---

ASSUMPTIONS_VERIFIED: brief §0 三條 fact-verified 均已重跑；commit 分類、finding 計數、synth 群集主題、閘 rc、多落點 rg 均附命令  
TESTS_RUN: `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r1-composer.md --family composer`（交件前自檢）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀偵察）  
NUMERIC_OR_SCHEMA_IMPACT: none

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R1-P0-01,COMPOSER-R1-P1-01,COMPOSER-R1-P1-02  
CLOSED:  
STATUS: DONE
