# RULEIMPL R2 複驗 — Grok 委員（對照 R1 22 條）

**標的**：`handoffs/RULEIMPL-SPEC-DRAFT-R2.md`（Composer 修訂）  
**R1**：`handoffs/RULEIMPL-REVIEW-grok.md`（22 條 CHALLENGE；VERDICT: BLOCK）  
**複驗日**：2026-07-11  
**範圍**：只產出本檔；未改其他檔。

---

## 要害兩條 — 親自實跑

### 要害 A — 消費端拒收不得可架空

| 檢查 | R1 缺陷 | R2 落點 | 實跑/靜態證據 | 判定 |
|------|---------|---------|---------------|------|
| 預設 enforce | 可 D3=A + 無鍵 skip | §C `VALIDATION_CONSUMER_ENFORCE=1`；V-C4→**FAIL**（非 skip） | 修訂稿 L71–83、L317 | 文面 **CLOSED** |
| Task 4.2 / D3 | 可整項 waive | Task 4.2 **必做**；`ic1eb_b5_replay` 接 `require_validation_receipt`；TODO 白名單含該檔、禁止 4.2 waive | 修訂稿 L248–255、L354–355、L378–384 | 文面 **CLOSED** |
| 窄 waive | —（R1 無合法旁路設計） | 僅 `category: pre-ruleimpl-baseline` + approver + expires_at + reason；過期/非白名單 FAIL（V-C6/C7） | 修訂稿 L74–82、L319–320 | 可接受過渡；**非** R1 式整票架空 |
| 現碼裸讀 | `load_manifest` 僅 `json.loads` | 仍為現況；閉合靠 Task 4.2 實作後 | 實讀 `scripts/ic1eb_b5_replay.py:56-59` 仍裸讀 | 規格已鎖必接；**實作前**仍裸讀（預期） |

**殘餘（不重開 R1 架空主因，但須知）**：
1. 「開放決策」表仍列 D3 A/B，與正文「預設 D3=B / 4.2 不可 waive」張力；若後續 artifact 把 D3 改回 A 會重開 #4/#11。
2. `validation_waive.category` 為自填白名單字串，無「確為 pre-ruleimpl」機證；靠 approver+期限（誠實 PARTIAL）。
3. 僅強制 ≥1 harness；其餘 Bash 直跑 capture 仍 PARTIAL（§R 已寫，與 v2 一致）。

**要害 A 結論**：**CLOSED**（R1「整票可不接消費端」路徑已刪；預設嚴格 + 4.2 必做 + V-C4 FAIL）。

---

### 要害 B — 驗收句須實跑為真

| 驗收句（R2 宣稱） | 本機命令 | 結果 | 真/假 |
|-------------------|----------|------|-------|
| V-T5 反錨：`VERIFY_GATE_SPEC` exit 1 | `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` | exit=**1**；缺 RISK-HIT / FACT-RECEIPT | **真** |
| V-T5 錨 A：`TEMPLATE_GATE_FIX_SPEC` exit 0 | `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md` | exit=**0**；`TEMPLATE PASS (spec): docs/TEMPLATE_GATE_FIX_SPEC.md` | **真** |
| V-T5 錨 B：`INSTREV_PHASEB_SPEC` exit 0 | `bash scripts/template_check.sh spec docs/INSTREV_PHASEB_SPEC.md` | exit=**0**；`TEMPLATE PASS (spec): docs/INSTREV_PHASEB_SPEC.md` | **真** |
| §A：`VALIDATION-ARTIFACT` in template → 0 | `grep -c 'VALIDATION-ARTIFACT' templates/SPEC_TEMPLATE.md` | **0** | **真** |
| §A：`validation-run` in gate.sh → 0 | `grep -c 'validation-run' scripts/gate.sh` | **0** | **真** |
| §A：`run_with_receipt.py` shebang | `head -1 scripts/run_with_receipt.py` | `#!/usr/bin/env python3` | **真** |
| §A：手寫 receipt 測試名 L450 | `rg 'def test_v6_handwritten...' tests/governance/test_verify_gate.py` | **L450** 存在；`test_manual_receipt_without_audit_fails` **不存在** | **真**（R2 引用正確） |
| §A：兩檔 pytest → 35 passed | `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` | **35 passed** | **真** |
| §V 回歸三檔 + 標「35 passed」 | `pytest ...test_dispatch_wrapper.py ...test_verify_gate.py ...test_verify_gate_b5.py -q` | **5 failed, 47 passed**（b5 含 `test_b5_existing_verify_gate_spec_still_passes` 仍要 VERIFY_GATE exit 0） | **假** |
| 歷史 a/d 無 VA 仍 template PASS | python 掃描 `docs/*SPEC*.md` | **8** 份（≥ 稿稱「至少 6」） | **真**（下界） |
| F6 / 4.4 暗示今日 governance 可全綠 | `pytest tests/governance/ -q --tb=no` | **9 failed, 140 passed** | **假**（作 F6 基線） |

**要害 B 結論**：**STILL-OPEN**  
- R1 核心假句（V-T5 用 VERIFY_GATE 當 PASS 錨）**已修且本機為真**。  
- 但 §V L262–266 把「三檔命令」與「FACT-RECEIPT: 35 passed」綁在一起 → **今日實跑為假**；且 §C L100「`test_verify_gate*.py` 必須全過」與現況 b5 已紅衝突。實作者若照抄 §V 三檔命令當「既有全綠」基線會假綠或假紅。

---

## 逐條複驗（R1 22 條）

| # | R1 點 | R2 落點摘要 | CLOSED / STILL-OPEN | Receipt |
|---|-------|-------------|---------------------|---------|
| 1 | disposable 無磁碟禁搬 | §C 誠實邊界：政策禁止 + 升級=new-or-changed；無磁碟禁搬；靠消費端 | **CLOSED** | 修訂稿 L90–91；與 R1 要求「寫進誠實邊界」一致，非要求本票做 FS 禁搬 |
| 2 | TODO capture vs spec none | Task 2.2 + V-T7 **FAIL**（非 WARN） | **CLOSED** | L179–182、L278 |
| 3 | existing outputs hash 可選 | Task 2.1 `existing-approved` **必**重算 `outputs_content_sha256` | **CLOSED** | L167–170 |
| 4 | 消費端可 waive 架空 | 預設 ON；刪 V-C4 skip；4.2 必做 | **CLOSED** | 見要害 A；殘餘見上 D3 表張力（非 STILL-OPEN 主因） |
| 5 | PARTIAL-MECH 僅回退 | §R：`MECH-HELPER-DONE` / `MECH-FAILCLOSED-DONE` | **CLOSED** | L332–336 |
| 6 | V-T5 錨點假 | 改 TEMPLATE_GATE_FIX / INSTREV_PHASEB；VERIFY 作反例 | **CLOSED*** | 要害 B 三命令 exit 1/0/0 親跑；*見新縫 N1（§V 三檔 35 passed 假） |
| 7 | V-C4 無鍵 skip | V-C4→FAIL；V-C6/C7 窄 waive | **CLOSED** | L317–320 |
| 8 | F5 定義錯 | F5' sabotage 新套件 + F6 回歸正交 | **CLOSED** | L23–25、L322–325 |
| 9 | 歷史 a/d 新紅 | `VALIDATION_ENFORCE_AFTER` 選項 A | **CLOSED** | L93–99；親跑 8 份 a/d PASS 無 VA 證實炸彈存在且有 grandfather 設計 |
| 10 | 未知 VALIDATION-ARTIFACT | 顯式 FAIL + V-G9 | **CLOSED** | L92、L161、L308 |
| 11 | 未接真實 harness | D3=B；4.2 必做 | **CLOSED** | L248–255、L407；現碼仍裸讀=實作前狀態 |
| 12 | disposable cp 無機械禁 | §C PARTIAL + SCAR | **CLOSED** | L90–91（誠實，非假閉合） |
| 13 | validation-run ≠ gate_check kind | run lease；不進 PreToolUse | **CLOSED** | L193–196；親讀 `gate_check.sh` 僅 Task→dispatch / Bash executor→dispatch / Write→artifact |
| 14 | audit event 混判 | D2=B + consumer 濾 `event`+`emitter` | **CLOSED** | L208–209；親讀 `run_with_receipt.py:377-379` 固定 `event:receipt` |
| 15 | verification_claim_check 未劃界 | §C validation_run ≠ VERIFY claim | **CLOSED** | L89；`rg validation_run scripts/verification_claim_check.py` → 0 |
| 16 | ic1eb 裸讀 | Task 4.2 必接 | **CLOSED** | 同 #11；現碼 L56-59 仍 `json.loads` only |
| 17 | 測試名錯誤 | 改 `test_v6_handwritten_receipt_without_audit_blocked` L450 | **CLOSED** | 親跑 grep L450 |
| 18 | test_gate_bad_kind / F5 | Task 3.2 保持 `register-output` 子字串 | **CLOSED** | 親讀 `test_dispatch_wrapper.py:30-41` assert `"register-output" in proc.stdout` |
| 19 | 條文 3 須 §N | §N 條文 3 N/A | **CLOSED** | L342 |
| 20 | 歷史 SPEC 隱性 scope | §N 批量遷移另票 + 選項 A | **CLOSED** | L346、L98–99 |
| 21 | D3 與完工分級 | §R + 預設 D3=B | **CLOSED** | L332–336、L407；殘餘：開放決策表未從「可選 A」刪除 |
| 22 | 條文 1 程序面邊界 | §C VALIDATION-REVIEW 戳記；read-only 排除句不機檢 | **CLOSED** | L90 |

**22 條 CLOSED 計數**：22/22 對 R1 原缺陷文面吸收。  
**但要害 B / 新縫 → 整體仍不可 PASS。**

---

## 新縫（R2 修訂引入或暴露）

| ID | 嚴重度 | 描述 | 證據 |
|----|--------|------|------|
| **N1** | **BLOCKING** | §V「回歸必跑」命令含 `test_verify_gate_b5.py`，卻標 **FACT-RECEIPT 35 passed**。親跑三檔 = **5 failed / 47 passed**，非 35 passed。§A 兩檔 35 passed 為真，但 §V 把錯誤集合與數字綁死 → 驗收句假。 | 要害 B 表；b5 失敗含 `test_b5_existing_verify_gate_spec_still_passes`（仍要 VERIFY_GATE exit 0） |
| **N2** | **BLOCKING** | §C L100 要求實作後 `test_verify_gate*.py` **全過**；今日 b5 已紅。未先修 b5 / 未把基線寫成「不得比 baseline 更差」則 4.4 / F6 不可達或誘使弱化斷言。 | `pytest …test_verify_gate_b5.py` 5 fail；`pytest tests/governance/` 9 fail |
| N3 | 非阻塞 | 正文 D1/D2「鎖 A/B」、D3「預設 B」 vs 「開放決策」表仍可選對立項 — 實作前須凍結，否則 #4/#11 可被表推翻 | 修訂稿 L165、L208、L252 vs L401–408 |
| N4 | 非阻塞 | V-T5 錨 exit 碼真；`TEMPLATE_GATE_FIX` §G 段對 Task 2.1 regex **0 hit**（未觸發語意成立）。`INSTREV_PHASEB` 全文有「Golden 對照」在 §V — 實作須嚴格「僅 §G 段」否則誤觸發 | python 探針：§G matches=[]；whole-file 有 golden 對照 |
| N5 | 非阻塞 | `VALIDATION_ENFORCE_AFTER` 日期後僅「新建或 commit 觸碰 §G」FAIL，未觸碰之歷史 a/d 可永 WARN — 與選項 A 一致，但 L96「日期後 → FAIL」措辭略寬於 L97 | L93–97 |
| N6 | 非阻塞 | `require_validation_receipt(enforce=False)` 僅當 caller∈`tests/governance/` 早退；enforce=False 且 caller 在 scripts/ 時未寫「必須忽略 enforce 並 FAIL」— 依序檢查可推得落 step 2/3，建議一句釘死 | L238–241 |

---

## 彙總

| 維度 | 判定 |
|------|------|
| R1 22 條文面吸收 | 22 CLOSED |
| 要害 A 消費端架空 | **CLOSED** |
| 要害 B 驗收句為真 | **STILL-OPEN**（V-T5 已真；§V/F6 基線句假） |
| 新縫 N1/N2 | **BLOCKING** |
| 是否建議 stamp / 派實作 | **否** — 先修 §V 回歸命令與 FACT 數字一致，並處理 b5/VERIFY_GATE 基線（從回歸集合剔除 b5 **或** 另票修 b5 fixture / 改 b5 對 VERIFY_GATE 斷言，**禁止**為 RULEIMPL 假綠而削弱 b5） |

### 建議最小修文（供下一輪，本檔不改稿）

1. §V 回歸：改回與 §A 一致的兩檔命令 + 35 passed；**或** 實跑三檔後改寫為 `5 failed (b5 pre-existing) / 47 passed` 並明列「RULEIMPL 不得使 fail 數增加」。  
2. §C L100：`test_verify_gate.py` + `test_dispatch_wrapper.py` 必全綠；`test_verify_gate_b5.py` 標 pre-existing / 另票，勿寫「*.py 全過」。  
3. 開放決策：D1/D2/D3 改「已鎖」或刪 A 選項，只留 D4 日期。

---

ASSUMPTIONS_VERIFIED: R2 修訂稿全文 vs R1 22 條；要害 A 文面閉合路徑；要害 B 親跑 V-T5 三錨 + §A FACT + 兩檔/三檔/全 governance pytest  
TESTS_RUN:  
- `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` → exit 1  
- `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md` → exit 0  
- `bash scripts/template_check.sh spec docs/INSTREV_PHASEB_SPEC.md` → exit 0  
- `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` → 35 passed  
- `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py tests/governance/test_verify_gate_b5.py -q --tb=line` → 5 failed, 47 passed  
- `pytest tests/governance/ -q --tb=no` → 9 failed, 140 passed  
- 歷史 a/d 無 VA 仍 PASS 掃描 → 8 份  
FAILURES_SEEN: none（審查過程；上列 fail 為現況基線證據）  
SCOPE_CHANGES: none（僅本審查檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: BLOCK
