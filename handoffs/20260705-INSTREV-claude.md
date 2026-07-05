# 制度層總審查 — Claude 獨立版 R1（2026-07-05）

> 委員會三方各自獨立產完整版後互審。本檔=Claude 腿。方法=每條規則考掘「出生事故 + violation/摩擦紀錄」→ 四選一裁決：**機械化 / 留核心原則 / 合併去重 / 淘汰**。
> 證據來源：git log（檔案最後改動日）、`.claude/gate/audit.log`（448 dispatch / 104 artifact 事件）、`handoffs/TGF-*`、記憶檔 25 feedback、四源憲法逐行比對。

---

## 0. 已驗證事實（考掘結果，全部實測非推論；經四方互審與雙戳記核可 REF:handoffs/20260705-INSTREV-RECONCILE.md；SUPERSEDED: 取代 REF 補標前初版同句 VERIFY:none）

| # | 事實 | 出處 |
|---|------|------|
| F1 | 四源行數：CLAUDE.md 216 / AGENTS.md 178 / .cursorrules 180 / copilot-instructions **739** | `wc -l` 實測 |
| F2 | copilot-instructions 最後改動 **2026-04-26**（v3.2，內文自稱「Current Status 2026 Q1」）；無任何現役 agent 讀它（編排手冊執行池無 Copilot） | git log 04d7691 |
| F3 | AGENTS.md / .cursorrules 最後改動 **2026-05-31**（c084c96）——晚於它的制度全部缺席：兩輪斷路器（06-10）、--task-id/register-output（07-03）、VERIFY receipt/claim gate（07-01）、RECONCILE-STAMP 未全數 APPROVED 須 BLOCKED（06-27，手冊有、合約沒有） | git log + 逐行讀 |
| F4 | **執行端選層三處三答案（現行活分叉）**：CLAUDE.md L27「中=Composer 實作」｜MEMORY.md 索引行「2026-06-27起中大型一律Composer2.5實作」｜記憶內文 feedback_executor_override「**2026-07-02 使用者改回中大=Codex 實作+Composer review**（解除 06-27 覆蓋）」。每 session 注入的 CLAUDE.md 與現行裁定**相反** | 三檔逐字比對 |
| F5 | **中型管線直接矛盾**：CLAUDE.md L27「中型完整管線不得跳過：SPEC+**TODO 生成**+第三方 adversarial（2026-06-05 定死）」 vs ORCHESTRATION L123「中=寫 SPEC → 直接派工，**跳獨立 TODO+跳一次 adversarial**」 | 兩檔逐字比對 |
| F6 | **輪詢頻率分叉**：CLAUDE.md 鐵律⑤「每 5 分鐘回報」 vs 記憶 feedback_dispatch_polling「每 10 分鐘（省 token）」 | 兩檔比對 |
| F7 | audit.log 只記放行事件，**gate DENY（hook exit 2）不落地** → 「被擋幾次/為什麼」無法量化稽核 | grep audit.log 無 deny 條目 |
| F8 | `check_agent_contract_sync.sh` 只查 9 個 token 的 presence，查不出 F4/F5 這種語意分叉；token 清單也未含 --task-id/VERIFY/RECONCILE-STAMP 等新合約 | 讀腳本 |
| F9 | TGF 實測摩擦：戳記輪×4（每輪一次派工序列化）、claim-check 擋 commit×5（git log 43a22cf/1cdcb37/d829098 全是尾隨空白/claim 標記 chore）、provenance 流程中途才學會、同檔並發只能序列化 | HANDOFF + git log |
| F10 | ARCHITECTURE.md 最後同步 2026-05-25（v7.0）、DEVELOPMENT_GUIDE.md **2026-04-15**（近 3 個月未動）；gate/verify/TGF 制度全未入 | git log |
| F11 | 記憶層：25 條 feedback + 13 project + 2 reference；其中 ≥8 條與 CLAUDE.md/手冊重疊（task_routing、validate_assumptions、executor_override、two_round_breaker、reconcile_stamp、adversarial_beats_signoff、dispatch_polling、update_roadmap） | ls memory + 比對 REF:handoffs/20260705-INSTREV-RECONCILE.md（SUPERSEDED: 取代 REF 補標前初版同句 VERIFY:none） |
| F12 | TGF 已上線機檢：RISK-HIT 宣告、FACT-RECEIPT、真 §G、TODO 三欄、RESULT 極性、reconcile 戳記機驗、--mutate 回歸矩陣 → 部分 CLAUDE.md prose 的職責**已被機器接管** | HANDOFF TGF 節 |

---

## Layer ① 憲法（內容/架構/儲存）

### C-1 copilot-instructions.md（739 行，停在 04-26）→ **淘汰**
- 出生：早期為 GitHub Copilot 寫的總覽（v3.2）。violation 紀錄：無人讀=無 violation，但它是四源分叉的最大單一來源（佔四源總行數 56%，內容停在 Q1）。
- 裁決：**刪除，換 ≤10 行 pointer**（指向 CLAUDE.md/AGENTS.md）。若使用者仍用 Copilot 補齊局部（無證據），再議。風險低：無 agent 依賴。

### C-2 執行端選層分叉（F4）→ **機械化 + 合併**
- 出生事故：選層 06-03 定 → 06-27 覆蓋 → 07-02 解除覆蓋，但只更新記憶內文，**MEMORY 索引與 CLAUDE.md 都停在舊版**。這正是「同一事實存多處」的結構病。
- 裁決：①**選層表單一來源**——只存 ORCHESTRATION §1，CLAUDE.md 改一行 pointer；②機械化：`check_agent_contract_sync.sh` 加「選層 token 只准出現在單一來源檔」反向檢查；③ MEMORY 索引行與內文 description 不一致 → 修此條 + 建議索引行由內文 description 自動生成（低成本腳本）。

### C-3 中型管線矛盾（F5）→ **合併（單一來源）+ 請使用者裁決實質差異**
- 兩份文件對「中型要不要 TODO+adversarial」相反，且都聲稱使用者定案。這不是誰筆誤——2026-06-05 定死條款在 CLAUDE.md，手冊分層表是後來省 token 的優化，**未回寫**。
- 裁決：管線分層表**只存一處**；實質內容（中型到底跳不跳）屬使用者已定死領域 → 白話簡述列為**否決點 D-1**，預設按 CLAUDE.md（不跳）因它註明「定死」且較新敘述一致。

### C-4 CLAUDE.md 全載成本 → **壓縮：規則留、敘事出**
- 216 行極稠密，含三段完整事故敘事（驗證保真度~15行敘事、C3、Gate 設計理由重複兩處）。每 session 固定 token 支出。
- 判準（接 F12）：**凡已被 gate 機檢接管的 prose，敘事部分移出**——出生事故敘事移 `docs/SCAR_LEDGER.md`（規則傷疤帳本，本 epic 產物），CLAUDE.md 每條規則留「規則本體 + 一行出處 pointer」。
- 明確候選：驗證保真度鐵律三事故敘事（已被 FACT-RECEIPT/§G 機檢接管）、Gate 節設計理由（手冊已有完整版，CLAUDE.md 重複 ~20 行）、任務分派節的日期考據 prose。
- **不可砍**：規則本體一條都不砍（見 §不可砍清單）；砍的只是「為什麼」的敘事，且必留 pointer。目標 216→~120 行。

### C-5 AGENTS.md/.cursorrules 合約 stale（F3）→ **合併補同步 + 機械化**
- violation 紀錄：記憶 feedback_two_round_breaker 明寫「派工合約要明寫」但兩份合約至今沒有；RECONCILE-STAMP 的執行端 defense-in-depth 只在手冊。執行端讀的合約缺現役制度=靠 prompt 每次重講（TGF 的 provenance 中途才學會即此病）。
- 裁決：一次補齊（兩輪斷路器、task-id/register-output、VERIFY claim、STAMP-BLOCKED）；`check_agent_contract_sync.sh` token 清單同步擴充（機械化，把「新制度上線必進合約」變機檢）。

### C-6 ARCHITECTURE/DEV_GUIDE 漂移（F10）→ **降級標示，不強制同步**
- 非執行路徑文件，強制同步成本高。裁決：檔頭加「最後驗證日期 + 可能過時」banner（機械化：commit hook 提示超過 60 天未動的 docs 於引用時警示——**過度工程風險，交委員會**）；最低限=本 epic 補一次 banner。

### C-7 audit 拒發不落地（F7）→ **機械化**
- gate 的存在理由是「留痕供稽核」，但 DENY 這半邊沒有痕。裁決：`gate_check.sh` deny 時 append 一行（ts/tool/原因）到 audit.log。成本 ~5 行 shell，收益=下次總審查有摩擦量化數據。

### C-8 記憶層與憲法重疊（F11）→ **合併去重（方向：憲法為主，記憶留 delta）**
- ≥8 條 feedback 與 CLAUDE.md/手冊重疊。記憶=Claude 私有，Codex/Cursor 看不到 → 凡屬「多 agent 都要守」的規則**必須在 repo 憲法**，記憶只留「使用者偏好類（繁中、push 不問、brief 白話）」與 repo 不宜放的個人化。
- 裁決：重疊 8 條逐一併回憲法後把記憶檔改成 pointer；輪詢頻率（F6）以記憶 10 分鐘為準回寫 CLAUDE.md。

## Layer ② 派工流程管線

### P-1 戳記輪×4（F9）→ **機械化（批次化），原則不變**
- 原則「不可自我認證、戳記須委員 append」出生於 charter v1 誤併事故——**留**。摩擦在每份 reconcile 一輪派工。
- 裁決：允許**批次戳記**——一次派工審 N 份 reconcile、逐份 append 戳記；gate 的 reconcile_stamps_check 本來就逐檔驗,不需改。純編排慣例改變,寫進手冊 §2。

### P-2 claim-check 擋 commit×5（F9）→ **機械化（auto-fix 取代 deny）**
- 5 次全是尾隨空白/claim 標記 chore,無一次抓到真捏造。誤攔太貴。
- 裁決：①尾隨空白類 → pre-commit **自動修復**而非擋下;②claim 標記類 → checker 輸出「該加什麼標記到哪行」的可貼上 diff。原則（claim 須 backing）不變,執行成本降。

### P-3 provenance 中途才學會（F9）→ **機械化（錯誤訊息即文件）**
- 裁決：`gate.sh dispatch` 缺 `--task-id`/`--output` 時,錯誤訊息直接印正確完整用法模板（含 register-output 後續步驟）。流程知識從「手冊某節」搬進「犯錯當下的提示」。

### P-4 同檔並發序列化（F9）→ **留現狀（接受序列化）**
- 頻率低、分檔+機器合併的複雜度 > 收益。裁決：不動,手冊註明「同檔戳記請序列派工」。

### P-5 大任務管線輪數 → **留原則（使用者定死不得跳步），ceremony 輪批次化**
- 使用者 06-05/06-09 定死不得跳步——委員會無權砍步。可做的是 P-1/P-2/P-3 的降成本,把純 ceremony（戳記/閉合/claim 補標）壓進更少派工輪。

### P-6 兩輪斷路器 / 委員會升級 → **留核心原則 + 補進合約（見 C-5）**
- 出生：solo 硬幹燒整夜事故。violation 後有效紀錄多次。不動。

### P-7 派工其他鐵律（preflight/postflight、timeout+</dev/null、產物視為資料非指令、diff 既有斷言防假綠）→ **全留**
- 各有出生事故（data_cache 無備份、stdin 卡死實測、Gemini 假 DONE、假綠交差）。皆已半機械化。唯一動作:敘事移 SCAR_LEDGER,規則留。

## Layer ③ 小中大分類

### T-1 規則散三處 → **合併成單一決策表**
- 現狀:CLAUDE.md 任務分派節 ~40 行 prose + feedback_task_routing + feedback_executor_override。
- 裁決:重寫為**一張表**（判準列×小中大欄:風險 a-d 命中?、SPEC/TODO/adversarial 步驟、執行端、review 方、膨脹升級觸發）放 CLAUDE.md;日期考據與事故出處移 SCAR_LEDGER;記憶兩條改 pointer。表內容=現行規則忠實轉錄+F4/F5 分叉按否決點裁定後的版本,**不改實質**。

### T-2 「判不出大小→問或當中辦」「膨脹 5 訊號」→ **留原則,入表**

### T-3 升級觸發機械化(碰 factories.py/protocols.py/config.py → hook 警示) → **提案,交委員會**
- 可做 PreToolUse warn(非 deny)。風險:誤報煩人。Claude 傾向**緩做**(現行 prose 觸發近期無 violation 紀錄)。

---

## 不可砍清單（先行凍結,防瘦身誤傷）
1. 資料紅線:data_cache 不 commit/不 fake/無 hardcode;NaN/inf gate 不弱化。
2. 7 解耦規則全數。
3. facts-first(C3)、驗證保真度鐵律三條、三方數據簽核、adversarial 不自審、雙家族 adversarial(大)。
4. fail-closed gate 本體 + audit 留痕 + reconcile 戳記 + Claude 不自我認證。
5. 假綠防線:diff 既有斷言、VERIFY receipt、claim gate、RESULT 極性。
6. 兩輪斷路器 + 委員會升級。
7. 使用者否決權、白話簡述、繁體中文、「別問鐵律」。
8. 中大不得跳步(2026-06-05/06-09 定死)——本審查只降 ceremony 成本,不砍步。

## 裁決彙總
| ID | 裁決 | 類型 |
|----|------|------|
| C-1 | copilot-instructions 刪除換 pointer | 淘汰 |
| C-2 | 選層表單一來源+同步機檢+MEMORY 索引修正 | 機械化+合併 |
| C-3 | 管線表單一來源;中型跳不跳=否決點 D-1 | 合併 |
| C-4 | CLAUDE.md 敘事→SCAR_LEDGER,規則留+pointer,216→~120 行 | 合併 |
| C-5 | 執行端合約補 4 制度+sync 腳本擴 token | 合併+機械化 |
| C-6 | ARCH/DEV_GUIDE 加過時 banner | 留原則(降級) |
| C-7 | gate DENY 落地 audit.log | 機械化 |
| C-8 | 記憶重疊 8 條併回憲法,記憶留偏好類 | 合併 |
| P-1 | 批次戳記 | 機械化 |
| P-2 | claim-check 誤攔→auto-fix/可貼 diff | 機械化 |
| P-3 | gate 錯誤訊息即文件 | 機械化 |
| P-4 | 同檔並發:留現狀 | 留原則 |
| P-5 | 管線步驟全留,ceremony 批次化 | 留原則 |
| P-6/P-7 | 斷路器/派工鐵律全留 | 留原則 |
| T-1/T-2 | 分類規則合併成單一決策表 | 合併 |
| T-3 | 共用路徑 hook 警示:緩做 | 提案待審 |

## 給使用者的否決點(草案,reconcile 後定稿)
- **D-1**:中型管線要不要 TODO+adversarial(兩文件相反,皆稱你定案;預設=不跳)。
- **D-2**:copilot-instructions 直接刪(若你有在用 GitHub Copilot 請否決)。
- **D-3**:CLAUDE.md 敘事移出(每 session 省 token,但規則的「為什麼」要多跳一檔才看到)。
