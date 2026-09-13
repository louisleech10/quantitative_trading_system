# CXSTAMP X-REVIEW R1 — grok

task-id: 20260913-CXSTAMP-X-REVIEW-R1  
family: GROK  
findings-round: R1  
brief: `handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md`  
scope: current block＝`cx_run` stamp 格式閘／stub `stamp)` 臂；`debt_clear` `round_brief_kind`＋sha 不符解鎖；本輪 diff `1481604e..HEAD` 六檔。禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 碼證 |
|---|---|---|---|
| 新測 4+5 條綠；`test_debt_clear` 30 passed 等 | fact-verified | **本輪重跑新測成立** | `venv/bin/python -m pytest tests/governance/test_cxrun_stamp_format_gate.py tests/governance/test_debt_clear_stamp_unlock.py -q` → **9 passed** rc=0 |
| `cx_run.sh` 在 `_B4_ALLOWED_COVARIANT`，改動在凍結 case 外側 ⇒ contract_matrix 不因本改轉紅 | assumed | **成立** | `venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q -k "waiver and not worktree"` → **7 passed**, 77 deselected, rc=0；stamp 閘在 `esac` 之後（L733–741），未改 case 內字面 |
| 解鎖 B 不會被濫用為「任何 stamp 交件都可事後改字面」——每次須主委顯式 register-output | assumed | **不成立（P1）** | 解鎖不要求 `committee_output.output_path == family_result.output_path`；`_maybe_register_stamp_output` 自動寫入 stamp-target 之 `committee_output`（`--kind stamp`、跳過 expected 對證）即可在家族交件被改後仍銷帳。構造見 GROK-R1-P1-01 |
| `_maybe_register_stamp_output` 與新 stamp 格式檢查無互動 | assumed | **與格式閘本身無直接互動；與解鎖 B 有互動** | `_maybe_register_stamp_output` 只看 `cli_rc`／非空，不讀 `_fmt_rc`；格式失敗走 `format-failed` 後仍可能嘗試 stamp 登記（需 APPROVED 行）。真正危險面＝該登記被 B 當解鎖憑據（併入 P1） |

## 被當成事實的未驗證假設（§0）

- 「B 每次都須主委對**交件檔**顯式 register-output」→ brief 寫成 assumed，實測為**假**：自動 stamp-target 登記即可解鎖家族交件 sha 漂移。見 P1。
- 「註解所稱『本身經 verdict 解析』」→ stamp-kind `committee_output` 之 `verdict=null`、不跑 parser（`gate.sh` L209–211）；註解超賣。

---

## 必答 1 — A／B 是否最窄能過三問

| 修法 | 擋哪個根因 | 不做再燒幾輪 | 怎麼機械量 | 最窄？ |
|---|---|---|---|---|
| **A** `cx_run` stamp 亦跑 `--single`＋stub sentinel | 根因 1（stamp 跳過格式閘仍記 success） | 不做 ⇒ 空殼 stamp 交件繼續 success，reconcile／debt_clear 再紅、四路死鎖重演 | `test_cxrun_stamp_format_gate` 空殼→format-failed／合法→success／缺 checker→非 success | **是**（凍結 case 不可內改，外側 `if stamp` 為必要形狀；stub 臂為 harness 共變） |
| **B** stamp＋其後 register 解鎖 sha 不符 | 根因 3 之歷史死鎖出口（已 success 空殼無法重派／abandon） | 不做 ⇒ 舊債無出路（本事故已先銷）；但**現行 B 過寬** | 五條 `test_debt_clear_stamp_unlock`；缺「path 必須＝交件路徑」反例 | **方向對、收窄不足** — 更窄替代＝解鎖時強制 `rr.output_path` 正規化等於 `op`（或 `expected_outputs[fam]`），且／或拒絕 `verdict is null` 的 stamp-kind 登記當解鎖憑據。不需新腳本 |

**結論**：A 可留；B 須收窄後才能宣稱「不會被濫用」。僅 A、不修 B 之過寬，則**新** stamp 輪在 APPROVED 自動登記後，家族交件檔可被事後改字面仍 `debt_clear` 過關。

---

## 必答 2 — 三條 assumed 攻擊結果

1. **contract_matrix waiver**：命令見上表 → **rc=0，7 passed**。assumed **成立**。
2. **B 濫用構造（放過了不該放）**：  
   - 構造①：stamp 輪 success → 寫入**異路徑** `committee_output`（sha 自洽）→ 篡改家族交件 → `debt_clear` **rc=0**（路徑替換）。  
   - 構造②（生產路徑）：success → `_maybe_register_stamp_output` 風格之 stamp-target `committee_output` → 再篡改家族交件 → **rc=0 unlocked=True**（本家實跑）。  
   - 對照：無其後 `committee_output` → **rc≠0**（`test_stamp_round_edited_without_reregister_blocked`）。  
   assumed **不成立** → GROK-R1-P1-01。
3. **stamp register × 格式閘**：無直接讀寫 `_fmt_rc`；**與 B 解鎖有互動**（上）。assumed 字面「與格式檢查無互動」窄義可過；完整風險面併入 P1。

---

## 必答 3 — 可以結票嗎？

**不可結票（blocked）**。A 與新測對根因 1 成立；B 之 path-agnostic 解鎖推翻 brief 安全假設，屬本輪 diff 引入之可證偽缺口。主委應收窄 B（path 綁定）並補反例測試後再審／戳記；審不過則依 brief 回退重議。

---

## §1 必查摘要

1. 矛盾：B 註解稱「verdict 解析＋主委顯式」vs 實碼接受 stamp-kind／異路徑 → P1  
2. 漏項：解鎖缺 `output_path == op` 守衛；測試五條未覆蓋異路徑／stamp-target 自動登記  
3. 不可測：無（構造可重跑）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：9 新測綠；缺濫用反例  
10. Agent 可執行：修法可具名到 `debt_clear.sh` L496–508  
11. 短命工：無（B 為常駐路徑，非一次性）  

具名殘留（不另開 finding）：`cx_run.sh` L634／L865–875 註解仍寫「stamp 維持 stub-ok／stamp 不跑格式檢查」— 與本輪行為漂移，屬 doc-literal，不阻收窄 B。

---

## GROK-R1-P1-01

**斷言**: `debt_clear` 之 stamp 解鎖在 `actual != expect` 時，只要其後同 round 同家任一 `committee_output` 之檔案當前 sha 等於該事件登記 sha 即 `continue` 放行，不要求 `output_path` 等於該家 success 交件路徑；因此 `_maybe_register_stamp_output` 自動登記之 stamp-target（或任意異路徑）會讓家族交件被事後改字面後仍銷帳成功——推翻 brief assumed「每次須主委對交件顯式 register、不會被濫用為事後改字面」。

**碼證**: CODE-ANCHOR: scripts/debt_clear.sh:496 ；MUTATION: 解鎖分支加正規化 path 等式 `rr.output_path==op` 後，異路徑／stamp-target 構造應轉紅（rc≠0），同路徑重登仍綠；拿掉該等式 ⇒ 異路徑構造回 rc=0。RECHECK：L496–508 無 path 等式；`cx_run.sh:587` 以 `--kind stamp` 登記 stamp-target（`gate.sh` L209–211 跳過 expected、verdict=null）；本家實跑 stamp success→committee_output(STAMP_TARGET.md)→tamper 家族交件→debt_clear rc=0「視為已交件」，無登記對照 rc≠0；`pytest tests/governance/test_debt_clear_stamp_unlock.py -q` → 5 passed 未擋異路徑。

**來源摘要**: scripts/debt_clear.sh#220b4a6993ce;scripts/cx_run.sh#25ff92c32893;scripts/gate.sh#1779022ef126;handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md#cdecc8b5b8d3;tests/governance/test_debt_clear_stamp_unlock.py#ac7058156d8e

[BLOCKING] 信心度=High。  
會怎麼失敗：合法 stamp 輪三家 APPROVED 後，audit 已有 stamp-target 之 `committee_output`；任何人改 `handoffs/<session>-<fam>.md` 字面（削弱／竄改交件），`debt_clear` 仍過——「success 檔不得改」對 stamp 輪在自動登記後形同虛設。  
修法：解鎖分支增加 path 綁定（`rr.output_path` 正規化＝`op`）；可選拒絕 `verdict is null`。補兩條反例測試（異路徑擋／同路徑放）。可行性：既有 `test_debt_clear_stamp_unlock` harness 已能構造；本家異路徑探針已證當前為 rc=0、加 path 等式後預期 rc≠0。不新腳本。

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P1-01
CLOSED:
STATUS: DONE
