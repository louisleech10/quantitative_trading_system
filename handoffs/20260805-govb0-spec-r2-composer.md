# GOVB0-SPEC-R2 — Composer Adversarial Review (R2)

**審查標的**：`docs/GOVB0_FRICTION_SPEC.md`（R2 版）  
**家族**：COMPOSER | **輪次**：R2 | **task-id**：GOVB0-SPEC-R2  
**日期**：2026-08-05

---

## 被當成事實的未驗證假設（§0）

| 標籤 | brief／SPEC 陳述 | 裁定 |
|---|---|---|
| **assumed→部分成立** | 13 項 D 群裁決全部已在 R2 落實且無新矛盾 | **文本層大多成立**；D-1／D-4／D-11／D-12 有明確條目。但 **Task 2.0 詞法契約 5 項未涵蓋 eval／命令替換等向量**（見 P0-01），且主委原型②對契約第 3–5 項多數未實作（見 P1-01）。 |
| **assumed→可接受但有殘留** | D-6 SPLIT 刪 Phase 4 不讓 B-24 掉項 | **紀律面 §V 有逐 Task 狀態斷言**；**機械強制面確實移出**且 grandfather 三要件在 backlog 有記（`票 B-24` 拆分節）。與使用者「工具強制」仍有差距，但 SPLIT 裁決可接受（見 Q3）。 |
| **assumed→未成立** | Task 2.0 五項涵蓋所有影響判定的詞法情境 | **未成立**——隔離探針 12 條中 8 條契約未列或原型未覆蓋（見 P0-01／P1-01／P1-02）。 |
| **fact-verified** | R2 = 4 Phase／10 Task；`template_check.sh spec` rc=0 | **複核通過**：`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS`；grep 無 `Task 4`／`Phase 4` 實作段（僅 §N 移出說明）。 |
| **fact-verified** | 原型② 9/9 全對 | **複核通過**：`bash .claude/tmp/b15probe3.sh` → `bash -c`／`sh -c` 兩條 proto1=ALLOW、proto2=BLOCK。 |

---

## §1 必查摘要

| # | 類別 | 結果 |
|---|---|---|
| 1 | 矛盾/互斥 | **有（輕）** — Task 3.3「已 publish 則依格式檢查」與 Task 3.2「先格式檢查再 publish」語序易誤讀；實際區間為 CLI timeout vs wrapper publish，**可化解**但 TODO 須寫清時序（見 Q2）。 |
| 2 | 漏項/端到端 | **有** — Task 2.0 缺 eval／`$()`／反引號／子 shell；Task 3.1 缺 duration 樣本門檻（P0-01、P1-04）。 |
| 3 | 不可測驗收 | **有（輕）** — Task 3.1→3.3 定稿條件缺可執行 n（P1-04）。 |
| 4 | 可疑 quant 假設 | **無** |
| 5 | 過度工程 | **無** — Phase 4 已移出。 |
| 6–8 | OOM／Cache／API | **無** |
| 9 | 測試品質 | **有** — 契約第 3–5 項與邊界語料尚無可執行 receipt（P1-01）。 |
| 10 | Agent 可執行性 | **有** — 見 P0-01（詞法契約不完整）。 |
| 11 | 必要性/短命工 | **無** — Task 2.5「B-29 取代」標註正確。 |

## §2 範本錨點 + 獵空殼

- §RISK／§A／§C／§P／§V／§R／§N：**齊**；§G N/A 合理。
- §A FACT-RECEIPT：**9 條皆有**；OPEN-1 標暫定、OPEN-2→B-33、OPEN-3 補查條件已寫。
- §P 依賴圖：**已補** registry enum／snapshot／corpus／prompt identity（D-13）。
- 獵空殼：**未發現表頭-only**；各 Task 驗證欄有 ASSERT／狀態斷言 token。

---

## Q1 — R1 P0／P1 逐條關閉判定

| Finding ID | Verdict | 重跑反例與結果 |
|---|---|---|
| `COMPOSER-R1-P0-01` | **CLOSED** | `bash .claude/tmp/b15probe3.sh` → `bash -c "codex exec x"` proto2=BLOCK（want=BLOCK）。R2：Task 2.0 契約②＋Task 2.1 依契約實作＋mutation「移除 -c 遞迴→ALLOW」守護測試。 |
| `COMPOSER-R1-P0-02` | **CLOSED** | `sed -n '512p' scripts/cx_run.sh` 仍為 `產出寫到 ${out}`（**現碼未改，屬預期**）。R2 Task 3.2 改法②明文「prompt 與 wrapper **必須同時改**」＋驗證「prompt 路徑 == wrapper attempt 路徑」。SPEC 層已關閉。 |
| `COMPOSER-R1-P1-01` | **CLOSED** | Task 2.5 驗證改為「列舉項必要子集＋附加項人工標註；非預期⇒FAIL」（`:230-233`）。 |
| `COMPOSER-R1-P1-02` | **CLOSED** | Phase 4 已刪；4 Phase／10 Task；SPLIT 裁決已寫入 §N 與 backlog。 |
| `COMPOSER-R1-P1-03` | **CLOSED** | §A OPEN-2 → `票 B-33`；TODO §0 已知債要求已寫。 |
| `COMPOSER-R1-P1-04` | **CLOSED（移出本批）** | Task 4.1 隨 Phase 4 刪除；grandfather owner／UTC 到期／到期後 fail-closed 記於 backlog `票 B-24` 拆分節（`:1222-1237`）。 |
| `COMPOSER-R1-P1-05` | **CLOSED** | 疊加風險收斂至 Task 2.0 契約＋2.1 實作；b15probe3 proto2 9/9。 |

**R1 P2（參考）**：`P2-01`/`P2-02`/`P2-03` 均在 R2 有明文化（Task 0.1 不可做、Task 1.1 誠實邊界、OPEN-3 補查條件）→ **CLOSED**。

---

## Q2 — R2 新矛盾／漏洞

**1. Task 2.0 契約 vs Task 2.1–2.4**  
契約列 5 項，但 **eval／`$()`／反引號／子 shell 未列**且原型②全 ALLOW（P0-01）。契約第 3–5 項（引號路徑、路徑正規化、未閉合引號）**在原型②上多數未通過**（P1-01）⇒ 實作若只抄原型②會與契約驗收衝突。

**2. Task 3.2 publish vs Task 3.3 timeout**  
**無硬矛盾**：Task 3.3 timeout 區間＝CLI process-group（`:289`）；publish 在 CLI 返回後由 wrapper 執行（Task 3.2 改法④）。逾時路徑＝CLI 未返回⇒未 publish⇒`failed`（`:291`）。建議 TODO 加一句「format check 與 publish 均在 CLI wait 返回之後；timeout 不涵蓋 publish 階段」以免實作者誤讀 `:291`「已 publish 則依格式檢查」。

**3. Phase 0 判定不變 vs Phase 2 判定改變**  
**不互斥**：Phase 0 不變式僅涵蓋 **Phase 0 自身 diff**（audit 欄位排除在外，`:100-101`）；Phase 2 差集由 Task 2.5 舊版 snapshot 對照，語料可重疊但 **比較基準不同**。

---

## Q3 — D-6 SPLIT 是否可接受

**可接受**，理由：①使用者「95% 解法」＋本批已 5 票／10 Task；②紀律面 §V 逐 Task 狀態斷言已寫；③機械強制＋grandfather 三要件 **未遺失**（backlog 拆分節）；④獨立批次可交付 checker。

**殘留風險（NOTED）**：仍不等於滿足使用者「工具必須自帶強制」對 B-24 的全票面——TODO §0 須寫「B-24 部分完成」，code review 不得宣稱 B-24 全綠。

**替代方案（若不接受）**：把 Phase 4 機械強制併回 ⇒ 新增 `acceptance_state_check.sh`＋hook 接入＋grandfather SoT，估 **+1 Phase／+3–5 日／+1 adversarial 輪**；與「摩擦止血」批次目標衝突。

---

## Q4 — Task 3.3 定稿條件可執行樣本門檻

SPEC 未給 n。建議 **可執行門檻**（寫入 TODO／Task 3.1）：

1. **Task 3.1 上線後**，每家族累積 **≥20 筆** `committee_family_result` 且 `result_state=success`、含新 duration 三欄；
2. 取各家族 **max(duration)** 與 **P99(duration)**（單調時鐘欄位，非 runlog proxy）；
3. **定稿規則**：`timeout_family = ceil(max(max, P99×1.25))`，外層 `= max(family_timeouts)+15m`；
4. **下限**：任一家族 <10 筆 ⇒ TODO 只能用 §A 暫定值並標 `PROVISIONAL`；
5. **參考**：歷史 runlog proxy n=166/143/152 僅作 sanity check，**不可替代** Task 3.1 欄位。

---

## Q5 — §V `票 B-24` 紀律面

§V `:310` 稱「每個 Task 驗證欄皆狀態斷言、而非某腳本 rc=0」——**部分過度宣稱**。

仍含 **rc 斷言**（作為被測 harness 的 outcome，可接受）：

| Task | rc 斷言行 | 是否另有狀態斷言 |
|---|---|---|
| 0.1 | `ASSERT gate_check blocked/allowed THEN rc` | 有（JSON diff、`jq` 欄位） |
| 1.1 | `ASSERT cx_run brief_kind THEN rc` | 有（prompt 字串） |
| 3.3 | `ASSERT cx_run hang THEN rc!=0` | 有（`result_state`、孤兒進程） |
| 2.5 | 非預期附加項⇒`rc≠0`；空語料⇒`rc≠0` | 有（子集、sha256） |

**純 rc 無狀態**：**無**（各 Task 均有並列狀態斷言）。§V 對 `restore_golden_inventory.sh` 的「不得以腳本 rc 為證」（`:316`）正確且重要。

---

## Q6 — `票 B-34 GOV-STAMP-ROSTER-VS-ROLEGATE`

① **嚴重度：MAJOR**（非本批 BLOCKING）——硬防線語意空洞：非參與者被迫蓋章。  
② **修法**：**①優先**——`reconcile_stamps_check.sh` 必要 roster 改為該輪 `committee_round_open.participants`（或 synth 檔頭 roster），而非 `review_families` 全集。②③需新 kind 或放寬角色語意，成本高。  
③ **納入第 0 批**：**否**（同意主委，同 B-33 避免膨脹）；TODO §0 記已知債。

**VERIFY**：
- `bash scripts/_role_gate.sh check-families handoffs/20260804-GOVB0-SPEC-R2-BRIEF.md codex,composer,grok` → rc=2（grok=implementer 拒派）
- `governance_roles.json`：`implementer=grok`；`review_families` 含 grok
- `reconcile_stamps_check.sh` 預設要求 `review_families` 全員

---

## Q7 — 可否進 TODO？

**需修補後派工**。

**BLOCKING 清單**：

| # | 修法方向 |
|---|---|
| B1 | Task 2.0 契約增第 6–9 項或統一規則：`eval`／`$()`／反引號／子 shell 內容 **遞迴套用同一判定**；各至少 1 TP＋納入 immutable corpus |
| B2 | Task 2.0 驗收增 **契約第 3–5 項** 具名 TP/TN（引號路徑、路徑正規化、未閉合引號、巢狀 `-c`、無引號 `-c`）；不得僅引用 b15probe3 9 條 |
| B3 | Task 3.1 增 **duration manifest 樣本門檻**（見 Q4 五條）；Task 3.3 定稿條件引用該門檻 |
| B4 | TODO §0 記 `B-34` MAJOR 已知債；`B-24` 標「部分完成」 |

**NON-BLOCKING**：Task 3.3 補 publish／timeout 時序一句；heredoc TN 可併入 B1 或標為低優先 TN。

---

## Verdict：需修補後派工

---

## COMPOSER-R2-P0-01

**斷言**: Task 2.0 詞法契約 5 項未涵蓋 `eval`／命令替換／反引號／子 shell，且這些向量在參考原型②上 **全部 fail-open**。

**碼證**: 隔離探針 `/tmp/govb0-r2-composer/lexical_gap_probe.sh` → `eval "codex exec x"`、`$(codex exec x)`、`` `codex exec x` ``、`(codex exec x)` 皆 `ALLOW want=BLOCK`；契約 5 項未列上述機制。SPEC Task 2.0 `:146-151` 僅列引號／`-c`／路徑／未閉合引號。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[BLOCKING] 信心度=High。攻擊路徑：`eval "codex exec …"` 繞過引號感知與 `-c` 遞迴。修法：契約增「命令替換／eval／子 shell 內容遞迴判定」或對未知包裝 **fail-closed**；每項至少 1 TP 進 corpus。

---

## COMPOSER-R2-P1-01

**斷言**: R2 要求契約第 3–5 項（引號路徑、路徑正規化、未閉合引號）有測試，但主委原型② **未實作多數項**，實作者若照抄原型會與 Task 2.0 驗收衝突。

**碼證**: 同一探針 → `bash scripts/../scripts/cx_run.sh`、`"./my dir/codex" exec`、`bash -c "codex exec x'`（未閉合）、`bash -c codex exec x`、巢狀 `bash -c` 皆 `ALLOW`（契約要求 BLOCK 或 fail-closed）。b15probe3 僅 9 條，未覆蓋上述。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=High。修法：Task 2.0 驗證列出具名語料（與 Task 2.3／2.4 列舉對齊）；Task 2.1 改法不得寫「參考原型②」而不列缺口。

---

## COMPOSER-R2-P1-02

**斷言**: 詞法契約未處理 heredoc／分號在引號外組合，原型②對 `cat <<EOF; codex exec x` **誤擋（假陽性）**。

**碼證**: 探針 → `heredoc 假陽性` = `BLOCK want=ALLOW`；契約與 Task 2.4 邊界③「腳本名在字串引數中→ALLOW」未覆蓋 heredoc 形態。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=Medium。修法：契約增 heredoc 或「僅引號內家族名不判定」的 TN；納入 corpus 防回歸。

---

## COMPOSER-R2-P1-03

**斷言**: `票 B-34` 結構衝突未在 R2 處理——`brief-kind:review` 禁止 grok 參與，但 `reconcile_stamps_check.sh` 仍要求三家蓋章，非參與者戳記語意為空。

**碼證**: `bash scripts/_role_gate.sh check-families … codex,composer,grok` → rc=2；`governance_roles.json` implementer=grok；`reconcile_stamps_check.sh:33-38` 預設 `review_families`。權宜 `brief-kind:stamp` 補派可過機檢但不治本。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#fa6a9a90835c

[MAJOR] 信心度=High。修法見 Q6①；本批不併入，TODO §0 須登記。

---

## COMPOSER-R2-P1-04

**斷言**: Task 3.1 未規定「多少真實派工才足以定稿 Task 3.3 timeout」，使「與 duration manifest 一致」在 TODO 生成時 **不可執行**。

**碼證**: Task 3.1 驗證僅「一次真實派工」自洽（`:250`）；Task 3.3 要求 TODO 值與 manifest 一致（`:298`）但未給 manifest 最小 n。§A 暫定值標 proxy 非 wall-clock（`:49`）。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MAJOR] 信心度=High。修法：採 Q4 五條寫入 Task 3.1／TODO §0。

---

## COMPOSER-R2-P2-01

**斷言**: §V `:310` 宣稱「每 Task 驗證皆非腳本 rc」**過度**——Task 0.1／1.1／3.3 仍用 `ASSERT … rc` 作 harness outcome（雖並列狀態斷言）。

**碼證**: grep SPEC → Task 0.1 `:103-104`、Task 1.1 `:127-129`、Task 3.3 `:294` 含 `rc` token；§V `:316` 對 golden restore 的狀態要求正確。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#cbd44a5a71ae

[MINOR] 信心度=High。修法：§V 改為「補救腳本不得以 rc 代替狀態；harness outcome 的 rc 須與狀態斷言並列」。

---

## COMPOSER-R2-P2-02

**斷言**: D-6 SPLIT 後 B-24 僅交付紀律面，**機械強制仍缺**——與使用者「工具必須自帶強制」有已知差距；R2 未在 TODO 生成條件中強制標「B-24 部分完成」。

**碼證**: §V `:309-311` 紀律面；Phase 4／`acceptance_state_check.sh` 已移出（`:10-13`、`§N :334`）；backlog `票 B-24` 狀態仍 ⬜ 全票面。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#fa6a9a90835c

[MINOR] 信心度=High（SPLIT 已裁）。TODO §0 須寫明部分完成，避免假綠。

---

ASSUMPTIONS_VERIFIED: R2 template_check rc=0；b15probe3 proto2 9/9；role_gate grok+review rc=2；lexical_gap 12 條探針；SPEC sha256=cbd44a5a71ae942d72705e418c03b6216777f1b940eb44999ff0c2da2ee6a170
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` PASS；`bash .claude/tmp/b15probe3.sh` PASS；`bash /tmp/govb0-r2-composer/lexical_gap_probe.sh` 12 cases；`bash scripts/_role_gate.sh check-families …` rc=2
FAILURES_SEEN: none（探針預期失敗為證據）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
