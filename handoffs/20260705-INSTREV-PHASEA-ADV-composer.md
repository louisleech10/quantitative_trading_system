# INSTREV Phase A — SPEC/TODO Adversarial Review (Composer)

> Reviewer: Composer 2.5 (獨立) | Date: 2026-07-05 | task-id: instrev-phasea-adv-composer  
> Inputs: `docs/INSTREV_PHASEA_SPEC.md`, `docs/INSTREV_PHASEA_TODO.md`, `handoffs/20260705-INSTREV-PHASEA-BRIEF-MANIFEST.md`  
> Focus: 規則零刪減風險 + token 保留 + 單一來源一致性 + 挑戰前提（reconcile §E 漏 U-3、§A receipt）

---

## Verdict：需修補後派工

SPEC/TODO 整體可執行、manifest 覆蓋完整、§A 多數 receipt 已獨立重驗；但 **零刪減驗收設計有假綠洞**、**D-4 選層 grep 可繞過**、**§B Gate 未收斂 [A-4]**，以及 **U-3 納入僅靠敘事未回寫 reconcile**。建議修補 ADV-COMPOSER-3/4/5/6 後再派 B1；其餘 MAJOR 可並行實作時防護。

---

## Findings

### 挑戰前提（§0，置頂）

**ID: ADV-COMPOSER-1** | **[MAJOR]** | 信心度: **High**  
**證據**: SPEC §A FACT-RECEIPT 末句「憲法檔的機檢依賴面=sync check 一支」；實際 `scripts/gate_check.sh`、`scripts/gate.sh`、`scripts/reconcile_stamps_check.sh`、`scripts/template_check.sh` 皆讀/依賴治理檔內容與 token（ORCH Gate 節亦描述 `register-output`/`RECONCILE-STAMP` 流程）。  
**VERIFY:** `grep -l "CLAUDE.md\|AGENTS.md\|gate.sh\|register-output" scripts/*.sh` → 至少 `gate.sh`、`check_agent_contract_sync.sh`、`reconcile_stamps_check.sh` 等。  
**RECHECK:** 同上 grep；對照 ORCH L67–88 Gate 節。  
**會怎麼失敗**: 執行端以為「sync check 綠就好」，忽略 copilot 殘留引用（如 `docs/ARCHITECTURE.md` L485）或 gate 路徑仍假設舊憲法結構。  
**修法**: §A 改為「presence 機檢=sync check；語意/派工閘=gate 族；本批不改腳本故 U-9 殘量仍 Phase B」；Task 1.2 邊界補「檔名級引用清單（ARCHITECTURE L485 等）→ 收尾 SCOPE_CHANGES 註記，不擴 scope 改正文」。

**ID: ADV-COMPOSER-2** | **[MAJOR]** | 信心度: **High**  
**證據**: `handoffs/20260705-INSTREV-RECONCILE.md` §E L53「Phase A: U-1/2/4/5/6/7/8/10/11/19」**未列 U-3**；U-3 L15 為「一次補齊 5 項（含 register-output/VERIFY/STAMP）」3/3 收斂。SPEC §A L20–21 以「列表筆誤」納入 [A-12]；manifest L17–18、L37 有白話說明。  
**RECHECK:** `grep -n "U-3\|Phase A" handoffs/20260705-INSTREV-RECONCILE.md`；比對 manifest [A-12] 與 reconcile §E。  
**會怎麼失敗**: 日後稽核以 reconcile §E 為準認定 U-3 屬 Phase B，[A-12] 被質疑 scope creep；或 stamp-review 以「未在核准分期」拒派。  
**修法**: 處置方向可接受（Phase A 標題=合約補齊、U-8 只覆蓋五項中之 debug），但應在 manifest/SPEC §A 加一句「reconcile §E 未改檔；以雙戳記 reconcile + 本 manifest [A-12] + 使用者 D-1~D-6 為準」；可選：Claude 事後 append reconcile §E errata（非本批 executor scope）。

**ID: ADV-COMPOSER-3** | **[BLOCKING]** | 信心度: **High**  
**證據**: TODO Task 2.3 L78 要求 `grep -q "繁體" CLAUDE.md`、`grep -q "VERIFY" CLAUDE.md`、`grep -q "FACT-RECEIPT\|先問" CLAUDE.md`；**現況 CLAUDE.md 三者皆 0 命中**（`繁體`/`白話` 全檔無；`VERIFY` 無；`先問` 無——僅「否決」L34）。manifest [A-4] L27 宣稱「8 類…改後 **CLAUDE.md+合約** 仍可 grep」；Task 2.1/2.2 **未要求**補 pointer 保留這些 token。  
**VERIFY:** `grep -c "繁體\|VERIFY\|FACT-RECEIPT\|先問" CLAUDE.md` → 0（2026-07-05 實跑）。  
**RECHECK:** 同上；對照 SPEC §V L130 與 TODO Task 2.3 L78。  
**會怎麼失敗**: B1 收尾 Task 2.3 必 FAIL，或執行端為過 grep 塞無語義 token（Task 2.3 禁止但無替代指引）→ **假綠或阻塞**。  
**修法**: (a) Task 2.1/2.2 明列「零刪減類若 CLAUDE 無字面，須加一行 pointer（繁中/白話簡述/VERIFY receipt/先問使用者）」；或 (b) Task 2.3 改為「CLAUDE **或** AGENTS+.cursorrules 聯合命中」並與 manifest [A-4] 對齊；§B Gate 同步納入。

**ID: ADV-COMPOSER-4** | **[BLOCKING]** | 信心度: **High**  
**證據**: Task 2.2 驗證 `grep -n "Codex(GPT-5.5)實作" CLAUDE.md` =0（半形括號）；現檔 L28 為 `Codex（GPT-5.5）實作`（**全形括號**），L37 為半形。刪 L37「執行端選層」bullet 後，L28「大」列仍寫死 Codex+Composer，**grep 可過但違反 D-4 單一來源 + Task 2.2 不可做**。  
**VERIFY:** `grep -n "Codex.*GPT-5.5.*實作" CLAUDE.md` → L28、L37（2026-07-05 實跑）。  
**RECHECK:** 實作後跑 `grep -nE "Codex.*GPT-5.5|Composer 2.5.*實作|cursor-agent --model composer" CLAUDE.md`（應僅 pointer 語境或 0）。  
**會怎麼失敗**: D-4 動態選層表面完成（ORCH 有現行分工行），CLAUDE 仍每次 session 注入寫死分工 → token 與分叉未消除。  
**修法**: 驗證改 `grep -nE "Codex.*實作|Composer.*實作"` 於「任務分派」節 =0；「大」列執行端欄改「見 ORCH §1 現行分工行」與「中」列一致。

---

**ID: ADV-COMPOSER-5** | **[MAJOR]** | 信心度: **High**  
**證據**: SPEC §V L130「[A-4]…改後 CLAUDE.md**+合約**」；TODO Task 2.3 L78 僅 grep `CLAUDE.md`（14 組全單檔）。  
**RECHECK:** 比對 §V ③ 與 Task 2.3 實作要點。  
**會怎麼失敗**: VERIFY/兩輪斷路器等只留在 AGENTS，CLAUDE 瘦身後規劃端讀不到 → 規則零刪減對「全 agent 消費」不成立。  
**修法**: Task 2.3 拆成「CLAUDE 必留 / 或合約必留」表，與 manifest [A-4] 八類一一對應。

**ID: ADV-COMPOSER-6** | **[MAJOR]** | 信心度: **High**  
**證據**: TODO §B Gate L19–28 無 Task 2.3 的 14 組 grep；Phase Gate L182 只要求 §B Gate。  
**RECHECK:** 讀 TODO §B vs Task 2.3 vs Phase 1-5 Gate 總表。  
**會怎麼失敗**: 執行端只跑 §B Gate 即標 DONE，[A-4] 零刪減未驗 → **核心驗收目標假綠**。  
**修法**: 將 Task 2.3 全部斷言併入 §B Gate 或 Phase Gate 必填清單。

**ID: ADV-COMPOSER-7** | **[MAJOR]** | 信心度: **High**  
**證據**: Task 4.3 新增 `register-output`/`RECONCILE-STAMP`/`VERIFY`；`scripts/check_agent_contract_sync.sh` CONTRACT_TOKENS **不含**這些（U-9 屬 Phase B）。Task 4.4 僅跑現行 sync。  
**VERIFY:** `grep CONTRACT_TOKENS scripts/check_agent_contract_sync.sh` → 僅 6+3 舊 token。  
**RECHECK:** 實作後 `grep -q register-output AGENTS.md .cursorrules`（Task 4.3 有）但 sync 不驗。  
**會怎麼失敗**: 合約漏寫新條目仍 sync 綠；與 U-9「假綠」問題延後但未在 SPEC 標殘量風險。  
**修法**: SPEC §V 或 Task 4.4 加「U-9 前以 Task 4.3 grep 為準；sync 綠 ≠ 新制度齊」；Phase B 依賴寫清。

**ID: ADV-COMPOSER-8** | **[MAJOR]** | 信心度: **Medium**  
**證據**: Task 3.1 改「選層原則」為單一現行分工行，但 ORCH §1 工具表 L32–35 仍「中=Composer 主力 / 大=Codex」；§6 L262+「主力決策法」仍歷史 codex/cursor 敘述。Task 3.1 邊界只要求 §6 加「以 §1 為準」一句。  
**RECHECK:** 讀 ORCH §1 表與 Task 3.1 改法。  
**會怎麼失敗**: D-4 動態選層下，讀者仍從表欄「何時用」取固定結論，與「以使用者當下指示為準」衝突。  
**修法**: 表「何時用」欄統一改「見本節現行分工行」；歷史 A/B 結論移 SCAR_LEDGER，表內不留第二結論。

**ID: ADV-COMPOSER-9** | **[MAJOR]** | 信心度: **High**  
**證據**: Task 1.2 邊界「其他檔引用 copilot 內文 → BLOCKED」；`docs/ARCHITECTURE.md` L485 仍列 copilot-instructions 為「更新 AI Agent 快速參考」。Phase A 只允許 ARCHITECTURE **檔頭** banner（Task 5.1），不改 L485。  
**VERIFY:** `grep -n copilot-instructions docs/ARCHITECTURE.md` → L485。  
**RECHECK:** 實作 copilot pointer 後全 repo `grep -r copilot-instructions --include='*.md' | grep -v Archived | grep -v handoffs`。  
**會怎麼失敗**: 執行端照邊界 BLOCKED，或靜默忽略 → 讀者仍被導向 739 行 stale 檔（與 D-2 精神衝突）。  
**修法**: SPEC §C 允許範圍加「ARCHITECTURE L485 改為 pointer 一句」或 Task 1.2 改「檔名引用→收尾列 SCOPE_CHANGES 不 BLOCKED」。

**ID: ADV-COMPOSER-10** | **[MINOR]** | 信心度: **High**  
**證據**: §B Gate 關鍵詞含 `stdin`；現 CLAUDE 無 `stdin`（有 `/dev/null` L37）；Task 1.1 清單含 stdin 事故。  
**VERIFY:** `grep stdin CLAUDE.md` → 0；`grep /dev/null CLAUDE.md` → L37。  
**RECHECK:** 實作後確認 `stdin` 在 SCAR_LEDGER、不在 CLAUDE。  
**會怎麼失敗**: 若 SCAR_LEDGER 用「/dev/null」敘事不用字面 `stdin`，§B Gate 假紅。  
**修法**: Gate 關鍵詞改 `stdin\|/dev/null` 或與 Task 1.1 表條目字面對齊。

**ID: ADV-COMPOSER-11** | **[MINOR]** | 信心度: **High**  
**證據**: `docs/MULTI_AGENT_BOOTSTRAP.md` L35 仍 `debug ≤3 輪`；Phase A scope 不含。templates/ 無 3 輪（已驗）。  
**RECHECK:** `grep -n "3 輪" docs/MULTI_AGENT_BOOTSTRAP.md`。  
**會怎麼失敗**: 新專案 bootstrap 與憲法不一致；低頻但可致誤讀。  
**修法**: Phase B/C 或本批 SCOPE_CHANGES 註記；非 BLOCKING。

**ID: ADV-COMPOSER-12** | **[MINOR]** | 信心度: **Medium**  
**證據**: manifest L11「216→~130」；SPEC/TODO `wc -l CLAUDE.md` ≤**140**。  
**會怎麼失敗**: 執行端為過 140 行限刪規則句。  
**修法**: 統一目標行數或註明「140 為硬上限、130 為期望」。

---

### §1 必查（10 類）

| # | 結果 |
|---|------|
| 1 矛盾/互斥 | **有** — ORCH 中型跳步(L123) vs CLAUDE 不得跳（Task 3.2 已覆蓋）；D-4 動態 vs CLAUDE L28/37 寫死（ADV-4）；§V vs Task 2.3 驗收範圍（ADV-5） |
| 2 漏項/端到端 | **有** — reconcile §E 未列 U-3 全五項（ADV-2）；ARCHITECTURE copilot 引用（ADV-9）；Phase 6 記憶不派工（已聲明） |
| 3 不可測驗收 | **有** — Task 2.3 部分 grep 現況不可過（ADV-3）；Codex grep 可假綠（ADV-4） |
| 4 可疑 quant 假設 | **無**（純文件，無 ML/數值路徑） |
| 5 過度工程 | **無** |
| 6 OOM/並行 | **無** |
| 7 Cache 正確性 | **無** |
| 8 API/型別/相容 | **有（制度）** — 新合約 token 未進 sync（ADV-7） |
| 9 測試品質 | **有** — §B Gate 未含 [A-4]（ADV-6）；關鍵詞雙向核對缺 `stdin` 對齊（ADV-10） |
| 10 Agent 可執行性 | **有** — Task 2.3 與遷移 Task 脫節（ADV-3）；BLOCKED 邊界與 ARCHITECTURE 衝突（ADV-9） |

### §2 範本錨點 + 獵空殼

| 檢查 | 結果 |
|------|------|
| SPEC §RISK/§A/§C/§G/§P/§V/§R/§N | **齊**（§G 合理 N/A b,c） |
| §A FACT-RECEIPT | **部分足** — wc/git/grep/sync/scripts grep **已重驗**；「機檢=sync 一支」**過度宣稱**（ADV-1） |
| RISK-HIT↔§G | **可接受** — 文件批，§N 登記 N/A + §V grep 替代 |
| TODO §0 解耦/原則 | **有** — token 清單、純文件聲明、防假綠；未逐條列解耦 7 規則全文（指向 Task 2.3，可接受） |
| 空殼 Task | **無** — 各 Task 有檔案、改法、驗證、邊界、不可做；Phase 6 驗證路徑 repo 外（已標 Claude 自做） |

### §3 不可違反原則

未發現 SPEC/TODO 要求弱化 NaN/fake/跨 symbol gate 或刪特徵換速度。**規則零刪減的驗收機制本身不足**（ADV-3/5/6）可能間接導致誤刪未被抓到。

---

## 被當成事實的未驗證假設（§0）

| 假設 | fact / assumption | 作者驗證？ | 嚴重度 |
|------|-------------------|------------|--------|
| 「憲法機檢依賴面=sync check 一支」 | **assumption 包裝成 fact** | 部分（只驗 scripts grep 兩檔） | MAJOR → ADV-1 |
| 「reconcile §E 漏 U-3 = 列表筆誤，納入合法」 | **assumption**（合理但未 amend reconcile） | 敘述+manifest，無 §E 修訂 | MAJOR → ADV-2 |
| 「D-1~D-6 已全數裁決」→ 待確認:無 | **fact**（HANDOFF L11–13、SPEC §A） | 是（HANDOFF 可追溯） | — |
| 「copilot 無 agent 依賴」 | **fact（scripts）**；**assumption（全 repo）** | scripts 已驗；ARCHITECTURE 等未驗 | MAJOR → ADV-9 |
| 「Task 2.3 可證明零刪減」 | **assumption** | 否（現況 grep 即失敗） | BLOCKING → ADV-3 |
| 「刪執行端選層 bullet = D-4 完成」 | **assumption** | 否（L28 仍寫死） | BLOCKING → ADV-4 |
| 「sync check exit 0 = 四源改寫安全」 | **assumption** | baseline 已驗；新 token 未覆蓋 | MAJOR → ADV-7 |
| §A line counts / 5分鐘唯一 / 3輪四處 | **fact** | **是（本 review 重驗）** | — |

### §A receipt 獨立重驗摘要（VERIFY）

```
wc -l → 216/739/334/178/180（與 SPEC 一致）
git log copilot → 2026-04-26 04d7691
grep 5分鐘 → 僅 CLAUDE.md:34
grep 3輪 → AGENTS:26, .cursorrules:19, ORCH:227,241
bash scripts/check_agent_contract_sync.sh → exit 0, ✅ 四源關鍵不變式一致
grep -rln ... scripts → check_agent_contract_sync.sh, register_legacy_committee_files.sh
```

---

## Suggestions（非 Blocking）

- Task 2.1 驗證「移出敘事可在 SCAR_LEDGER grep」建議加 **負向** `grep -c 關鍵詞 CLAUDE.md` 上限，與 §V 雙向核對一致。
- HANDOFF.md L17 仍列 Phase A 無 U-3 字樣；Claude 收尾索引宜與 manifest 對齊（非 executor 改根 HANDOFF）。
- 大型雙家族 adversarial 已跑本 review；派實作前收 Codex 同 prompt findings 並 reconcile 分歧。

---

STATUS: DONE
