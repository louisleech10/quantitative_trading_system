## Verdict：需修補後派工

## Findings

### §0 挑戰前提 / 被當成事實的未驗證假設

ID: ADV-CODEX-1 [MAJOR] 信心度 High  
證據：TODO §B Gate 只跑 `bash scripts/check_agent_contract_sync.sh`、行數、3 輪、5 分鐘、`現行分工`、`SCAR_LEDGER` 關鍵詞（`docs/INSTREV_PHASEA_TODO.md` L19-L29）；A-12 的核心新制度 token 是 `register-output` / `RECONCILE-STAMP` / `VERIFY`（L142-L147）。現行 `scripts/check_agent_contract_sync.sh` 的 token 清單只有 `STATUS: BLOCKED`、`handoffs/`、`data_cache`、`SMALL_INLINE`、`ASSUMPTIONS_VERIFIED`、`反提示注入`、`preflight`、`斷路器`、`委員會`（script L16-L19）。  
VERIFY: `bash scripts/check_agent_contract_sync.sh` → PASS；`rg -n "register-output|RECONCILE-STAMP|VERIFY|實跑命令" AGENTS.md .cursorrules` → exit 1（改前兩份合約未含）。  
RECHECK: 刻意不補 A-12 三個 token、只跑 TODO §B Gate；目前 gate 仍可能只因既有 token 通過。  
會怎麼失敗：實作者若照 §B Gate 作為「整批驗收全部須過」的唯一清單，可能漏補 U-3 的三個現役制度卻仍拿到 batch gate 綠燈；這正是本批要修的「合約 stale」風險。  
修法：不改 `scripts/`（Phase B scope），但把 A-12 三組 grep 明確加入 TODO §B Gate / SPEC §V 整批驗收清單：兩檔各 `grep -q "register-output"`、`grep -q "RECONCILE-STAMP"`、`grep -qE "VERIFY|實跑命令"`。

ID: ADV-CODEX-2 [MAJOR] 信心度 High  
證據：TODO §B Gate 要求 `grep -c "現行分工" docs/MULTI_AGENT_ORCHESTRATION.md` = 1（L26）；Task 3.1 又建議工具表「何時用」欄可寫「依 §1 現行分工行」（L90），同 Task 再新增單一「現行分工(...)」正文行（L90）。SPEC 同樣要求 ORCH 中 `現行分工` = 1（`docs/INSTREV_PHASEA_SPEC.md` L65）。  
VERIFY: `nl -ba docs/INSTREV_PHASEA_TODO.md | sed -n '87,96p'` 顯示範例與驗證同段衝突。  
RECHECK: 依 TODO L90 原樣在工具表填「依 §1 現行分工行」並新增正文行後，跑 `grep -c "現行分工" docs/MULTI_AGENT_ORCHESTRATION.md`，結果會大於 1。  
會怎麼失敗：執行端忠實照範例改工具表會讓自己的驗證 gate 失敗；若為過 gate 又刪掉正文或弱化 pointer，會破壞單一來源語義。  
修法：把工具表範例改成不含精確 token 的寫法，例如「依本節分工行」；或把驗證改成只匹配正文錨點，例如 `grep -c "^\\*\\*現行分工"`。

ID: ADV-CODEX-3 [MINOR] 信心度 Medium  
證據：SPEC §A receipt 說 `grep -rln "CLAUDE.md\|AGENTS.md\|cursorrules\|copilot-instructions" scripts/*.sh scripts/*.py` 只命中兩支 script，並推論「憲法檔的機檢依賴面=sync check 一支」（`docs/INSTREV_PHASEA_SPEC.md` L17）；Task 1.2 又說 `.github/copilot-instructions.md`「無 agent 依賴」（L40）。  
VERIFY: `rg -n "copilot-instructions|copilot" -g '!data_cache/**' .` 顯示目前仍有 `docs/ARCHITECTURE.md:485`、多個 archived docs/handoffs 提到該檔；但現役 `templates/TODO_GENERATION_PROMPT.md` 未命中。  
RECHECK: 跑上述 `rg`，再區分現役輸入、歸檔、handoff。  
會怎麼失敗：若「無 agent 依賴」被讀成「全 repo 無引用」，Task 1.2 的 pointer 化風險被低估；尤其 `docs/ARCHITECTURE.md` 正文引用不在本批允許修改範圍（只允許檔頭 banner）。  
修法：把 §A/Task 1.2 的結論收窄為「無現役 scripts/gate 依賴；repo 內歷史/低頻文件引用保留，因 pointer 檔不刪故不破鏈」。不要求本批改正文。

### §1 必查 10 類

1. 矛盾/互斥：見 ADV-CODEX-2；另 U-3 納入 Phase A 雖未列於 reconcile §E，但 manifest L17 已顯式揭露，reconcile U-3 L15 為 3/3 收斂，判定可接受但屬需使用者/Claude 知情的 assumption。
2. 漏項/端到端：見 ADV-CODEX-1；A-12 新制度的 batch-level 驗收未進 §B Gate。
3. 不可測驗收：大多可測；ADV-CODEX-1 是驗收清單不完整，不是單 Task 無驗證。
4. 可疑 quant 假設：無，純治理文件，不涉數值/ML/資料路徑。
5. 過度工程：無，未引入新機制；主要是文件重構。
6. OOM/並行：無，純文件。
7. Cache 正確性：無，未觸及 cache。
8. API/型別/相容：無，未觸及 API/DTO；文件相容性見 ADV-CODEX-3。
9. 測試品質：見 ADV-CODEX-1、ADV-CODEX-2。
10. Agent 可執行性：見 ADV-CODEX-2；其餘 Task 大多具體到檔案/驗證/不可做/邊界。

## 被當成事實的未驗證假設（§0）

- `U-3 納入 Phase A 是列表筆誤修正`：有 reconcile U-3 3/3 收斂與 manifest 對使用者揭露支撐，但 reconcile §E 原文確實漏 U-3；這是合理推論，不是 receipt-level fact。建議保留「已揭露、需 reconcile 採納」語氣，不寫成完全已驗證事實。
- `check_agent_contract_sync.sh 能保護本批合約補齊`：只對既有 token 為真；對 A-12 新 token 不為真。見 ADV-CODEX-1。
- `.github/copilot-instructions.md 無依賴`：對現役 scripts/gate 依賴可驗；對全 repo 引用不成立。見 ADV-CODEX-3。

## VERIFY Receipts

- `wc -l CLAUDE.md .github/copilot-instructions.md docs/MULTI_AGENT_ORCHESTRATION.md AGENTS.md .cursorrules` → 216 / 739 / 334 / 178 / 180，與 SPEC §A 一致。
- `bash scripts/template_check.sh spec docs/INSTREV_PHASEA_SPEC.md` → PASS。
- `bash scripts/template_check.sh todo docs/INSTREV_PHASEA_TODO.md` → PASS。
- `bash scripts/coverage_check.sh handoffs/20260705-INSTREV-PHASEA-BRIEF-MANIFEST.md docs/INSTREV_PHASEA_SPEC.md docs/INSTREV_PHASEA_TODO.md` → PASS，16 項全覆蓋。
- `bash scripts/check_agent_contract_sync.sh` → PASS，但僅 presence check；覆蓋不足見 ADV-CODEX-1。

STATUS: DONE
