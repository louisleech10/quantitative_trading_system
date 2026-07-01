# VERIFY_GATE 全硬化合理性審議 — Composer 2.5（治理設計委員）

**角色**：治理設計委員（獨立挑戰 Claude 自產版，非附和）  
**輸入**：`handoffs/20260701-VERIFYGATE-BALANCE-AND-WORKFLOW-CLAUDE.md`、`handoffs/20260701-VERIFYGATE-SPEC-ADV-RECONCILE.md`、`docs/VERIFY_GATE_SPEC.md`、`scripts/gate.sh`、`scripts/gate_check.sh`、`scripts/reconcile_stamps_check.sh`  
**使用者決策**：全硬化（careless-proof 取向，非密碼學 forgery-proof）  
**立場**：全硬化**值得做**，但 Claude 版對三個高撞牆點的緩解過於樂觀；若干項標「合理」卻未給可實作判準，實作後仍會撞牆或變相繞過。

---

## 對 Claude 自產版的逐條挑戰

| Claude 斷言 | 挑戰 |
|---|---|
| B-FORGE「合理、撞牆低」 | **部分同意，但 Claude 的 `READONLY_SIGNOFF` 逃生口過寬**。讀碼結論若無 runnable test，仍須另一種 provenance（委員戳記 + task-id + 審閱範圍引用），不能變成「不用 receipt 也能寫已驗」。否則 causality signoff 類事故原路重現，只是換標籤。 |
| B-HOOK「合理」+「最大撞牆源」卻仍標合理 | **內部矛盾**。合理的是「攔 Edit HANDOFF 主路徑」；不合理的是 SPEC 現狀把 claim 偵測做成詞表+同段，卻要上 PreToolUse——這組合**必**高誤報。應改判：**機制合理、偵測器 v1 規格不合理**。 |
| 「快逃生口」否則人人 EXEMPT | **方向對、手段錯**。逃生口若是「任意引用舊 run」或「一行 SUPERSEDES 免 receipt」，等於把牆鑿洞。逃生應是**結構化引用**（`REF:<receipt_id>` 綁既有審計事件 + 極性一致），不是語意模糊的「上一步已驗」。 |
| B-EXEMPT「反諷：forensic 檔會擋自己」 | **這是設計失敗的徵兆，不是豁免理由**。若事故分析檔不能寫引號內「已驗」，代表偵測器把「引用」當「宣稱」——應修偵測器，不是擴豁免。檔名白名單（`handoffs/*FORENSICS*`、`*-ADV-*`、`*-DELIB-*`）+ 段內必須是 fenced quote 或 `>` 引用塊，**不可**靠 HTML comment 蓋整段 operational 文字。 |
| B-SCOPE #6「v1 輕量、完整索引 phase 2」 | **半對半錯**。完整 render 索引可 phase 2；但「紅燈後舊綠 claim 仍留 HANDOFF」是**本次事故直接向量**，v1 必做衝突檢查，不能列 N/A。Claude 說「最可能過頭」——我認為過頭的是**自動重寫 HANDOFF**，不是**偵測衝突**。 |
| W7「靠人即可、不必全機器化」 | **同意殘餘風險可靠人，但不同意 W7 與 W2 脫鉈**。`reconcile_stamps_check` 已要求 `task:<id>`，卻仍寫「Claude 可自算雜湊自寫戳記」——全硬化下 W2 修補應是：**stamp 無對應 harness 輸出 → gate 拒發**，不是只留「使用者可稽核」文案。W7 是人類最後關卡，不是機器放棄 W2。 |
| 「過嚴→大家學會繞」 | **真風險，但 Claude 沒量化**。繞過成本曲線：誤擋日常編輯 > 寫 `# VERIFY-EXEMPT: wip` > `--no-verify` > 改寫同義詞。全硬化必須讓前兩步比「真跑 receipt」更麻煩，否則失效。 |
| 未列 W10 | **遺漏**：`gate_check.sh` 無 `jq` → fail-open（L18）；`reconcile_stamps_check` 只 grep 行首戳記。兩者都是「守門員缺席仍綠燈」，應併入 W5/W2 優先修。 |

---

## 一、全硬化收斂項逐項評（回答提問 ①）

### 評分圖例
- **合理且 v1 必做**
- **合理但須收窄設計**（否則撞牆）
- **過頭 / 應延後**

| 收斂項 | 判定 | 撞牆風險 | Composer 評（挑戰 Claude） |
|---|---|---|---|
| **B-FORGE** receipt 綁 append-only 審計事件 | 合理且 v1 必做 | 低 | 同意。追加：**審計事件須含 `emitter=run_with_receipt.py` 且 command_sha 與 receipt 一致**；手寫 JSON 無事件一律拒。`READONLY_SIGNOFF` 改為 `SIGNOFF:<family>:<task-id>:<scope-hash>`，禁裸寫「已驗」。 |
| **B-HOOK** PreToolUse + git hook + CI + health | 合理但須收窄設計 | **高→中**（若偵測器對） | Claude 把風險歸「精度」卻仍標整包合理——我拆開：**攔 Edit/Write `HANDOFF.md`+`handoffs/*` 必做**；**攔 `docs/*.md` 全量 v1 過頭**（架構文檔充滿 `passed through` 英文）。v1 限：`HANDOFF.md`、`handoffs/*.md`、commit-msg；`docs/*SPEC*.md` 用 discussion 規則即可。 |
| **B-CLASS** runtime_class 推導 | 合理且 v1 必做 | 低 | 同意 reconcile。挑戰 Claude 未強調：**推導結果覆蓋 CLI 傳入值**，傳入僅記 `requested_class` 供稽核。 |
| **B-EXEMPT** 窄類別豁免 | 合理但須收窄設計 | **中高** | Claude 的 forensic 反諷證明現 SPEC 豁免語意太寬。v1：**HANDOFF.md / commit-msg / `## RESULT` / `STATUS:` 行 → 零豁免**；`VERIFY-EXEMPT` 僅 `template-drift|tooling-blocked|spec-ambiguity` 三類 + 必帶 `issue:<id>`；同檔每個 issue 最多 1 次 exempt（防洗版）。 |
| **B-LEDGER** pending 狀態機 | 合理且 v1 必做 | 中（規格不足則高） | 同意。Claude 說「低若自動管理」過輕——**開/關事件若可由任意 append 寫入，ledger 仍是偽造面**；關閉事件應只接受 `run_with_receipt.py` 或 parser 認可的 RESULT 模板產生。 |
| **B-SCOPE #7** RESULT 硬欄位 | 合理且 v1 必做 | 低 | 同意。這是 pending 的可靠輸入，摩擦可接受。 |
| **B-SCOPE #6** 根 HANDOFF 索引 / 衝突檢查 | 合理但須收窄設計 | 中 | **不同意 Claude「完整索引 phase 2」而衝突檢查也可緩**。v1 最小：**同一 `claim_fingerprint` 出現 RED/FAIL 後，舊 VERIFY 綠 claim 須標 `SUPERSEDED` 或刪除，否則 checker 擋**。自動 render 全文索引 → phase 2。 |

### 三個高撞牆點的具體設計（不卡日常）

#### 1) PreToolUse Edit 偵測精度

**Claude 問題**：攔「含已驗/通過字樣」會誤殺引用與 supersede。  
**Composer 方案**：不要「字樣驅動」，改 **claim-object 驅動**：

```
段落 → 正規化(NFKC, strip ZWSP) → 切 claim-object
每個 object: {polarity, scope_terms, runtime_terms, receipt_refs[], mode}
mode ∈ operational | citation | supersede | discussion
```

| mode | 判定信號 | 是否需 VERIFY |
|---|---|---|
| `operational` | 無引號/無 `>`/無 fenced quote；含驗收極性詞；非 `STATUS: BLOCKED` 討論 | **是**（新 claim） |
| `citation` | 行內有 `REF:<receipt_id>` 或 `VERIFY:<id>`（指向**已存在**審計事件） | 否（引用） |
| `supersede` | 含 `SUPERSEDED:`/`取代`/`作廢` + 舊 receipt id | 否（否定舊 claim） |
| `discussion` | 檔名白名單 **或** 父段為 fenced ` ``` ` / `>` quote；或段首 `<!-- claim-context: discussion -->` **且** 段內無新 task-id | 否 |

**PreToolUse 只擋**：`mode=operational` 且無有效 backing。  
**日常可寫**：「見 `REF:20260701-abc` 的 mutation 結果」；「`SUPERSEDED:20260701-old` 先前誤報」；forensic 檔 fenced 引號事故原文。

**挑戰 Claude**：「快逃生口」若不用上表結構化，等於回到 EXEMPT 氾濫。

#### 2) discussion / forensic 豁免

- **檔名白名單**（suffix）：`*FORENSICS*`、`*-ADV-*`、`*-RECONCILE*`、`*-DELIB-*`、`*VERIFY_GATE_SPEC*`。  
- **段內白名單**：fenced code block、`>` blockquote、表格內「事故原文」列。  
- **禁止**：HTML comment 包整段；在 `HANDOFF.md` 用 discussion 標記寫當前任務驗收。  
- **回歸測試必含**：本檔、forensic reconcile、**以及**「在白名單檔寫 operational 新 claim」→ 仍應擋。

#### 3) #6 churn（HANDOFF 生成索引）

| 層級 | v1 | phase 2 |
|---|---|---|
| 衝突檢查 | 同 fingerprint 紅後舊綠仍在 → FAIL | — |
| 過期標記 | 要求手動 `SUPERSEDED:<receipt_id>`（機器可驗 receipt 存在） | 自動掃描 |
| 全文索引 render | **不做**（避免改寫習慣衝擊） | 可選自動附錄 |

**日常摩擦**：編輯 HANDOFF 時多寫一行 supersede，比「每次改狀態都跑 pytest」低得多；真正痛點是誤擋，不是多一行標記。

---

## 二、claim 偵測器「高精度低誤報」判準（回答提問 ②）

### 核心原則
**擋「新的 operational 驗收斷言」，不擋「語言裡出現驗收詞」。**

### 分類決策樹（實作可測）

1. **正規化**：NFKC → 去 ZWSP/ZWNJ → 統一 hyphen/空格 → 小寫（英文段）。  
2. **段切分**：Markdown 以空行分段；列表項獨立；表格格獨立；commit subject 獨立。  
3. **極性詞偵測**（非閉集字串匹配）：  
   - PASS 類：`已驗|驗收.*通過|全綠|綠燈|STATUS:\s*DONE|真紅|真跑|無\s*look[- ]?ahead|runtime\s+PASS` + 事故 regression 原文片斷。  
   - FAIL 類：`真紅|紅燈|FAIL|未通過`（搭配 mutation/runtime 語境）。  
   - **排除**：`` `42 passed` ``（反引號內 pytest 輸出）、`passed through`（架構敘述）、`通過層 6.5`（層級名詞）。  
4. **模式判定**（按優先序）：  
   - 有 `VERIFY:<id>` 或 `REF:<id>` → 驗證 id 存在 + 審計事件 + 極性匹配 → `citation`（通過）或 FAIL。  
   - 有 `SUPERSEDED:<id>` / `取代.*VERIFY:` → `supersede`（通過）。  
   - 段在 fenced/quote **或** 檔名白名單 **或** `claim-context: discussion` 且無 `task:`/無新 `P0-` → `discussion`（通過）。  
   - 否則含極性詞 → `operational` → **必須** VERIFY 或 FAIL。  
5. **同段多 claim**（Codex MAJOR-2）：一個 receipt 只滿足 scope 交集的 claim；同段其他 claim 仍 FAIL。  

### 誤報/漏報驗收標準（寫進 §V）

| 指標 | v1 門檻 |
|---|---|
| 事故 regression fixture（`7e71fd1` HANDOFF 片段、`METAFIX` L6） | 漏報 = 0（必擋） |
| forensic/deliberation 檔引號原文 | 誤報 = 0 |
| `docs/ARCHITECTURE.md` 隨機 20 段採樣 | 誤報 = 0（若全量掃 docs 則很難，故 v1 不掃） |
| 「`pytest: 42 passed`」在 RESULT 模板 | 誤報 = 0 |
| 未知同義詞 `驗完/實測通過` | 可先 WARN 再升級 FAIL（避免一次封死） |

**挑戰 Claude**：「高精度低誤報」不是口號；上表門檻可寫進 `tests/governance/test_verify_gate.py`，未達標不上 PreToolUse。

---

## 三、全流程漏洞 W1–W9：同意 / 補充 / 排序（回答提問 ③）

### 同意與補充

| ID | 同意？ | 補充 |
|---|---|---|
| **W1** SPEC §A「已確認」可捏造 | ✓ | 全硬化下 §A 每條「已確認」須 `FACT:<source>`（`git grep` 輸出 hash / 檔:行 / receipt id）。純推論改回「待確認」。**不必**機器驗證推論真偽，但要驗證**有來源指標**。 |
| **W2** reconcile 戳記自寫 | ✓ | `task:<id>` 須在 harness 存在且輸出檔含 `APPROVED` 字樣匹配；僅 grep 戳記行不夠。 |
| **W3** adversarial 只驗存在 | ✓ | 高風險 `--adversarial` 除 reconcile stamp 外，路徑須匹配 `handoffs/*-ADV-{CODEX,COMPOSER}.md` 命名；waived 須使用者顯式理由。 |
| **W4** 驗收靠 Claude 自述 | ✓ | 編排者寫「diff 測試已驗」進 HANDOFF → 同 claim gate。驗收命令須 receipt。 |
| **W5** preflight/postflight 非強制 | ✓（部分） | 全硬化：**對執行端派工** preflight/postflight 應由 `gate.sh dispatch` 記錄是否執行（審計欄位），但不必擋每次 Bash。真正要擋的是 **data_cache 紅線**已有 postflight。 |
| **W6** template 只抓空殼 | ✓ | 已知邊界；靠 adversarial + 執行端合約。列殘餘風險，不無限擴機檢。 |
| **W7** audit.log 靠使用者稽核 | ✓ | 人類最後關卡合理；但 W2/W3 須減少「只能靠人」的比例。 |
| **W8** MEMORY 污染 | ✓（Claude 未展開） | MEMORY 寫 PASS/簽核須帶 `REF:<receipt\|stamp>`，否則視為軟性建議不進 fail-closed 路徑。v1 列殘餘風險即可。 |
| **W9** 執行端 RESULT 造假 | ✓ | ledger + receipt 關閉鏈可部分接住；Claude 未強調 **RESULT 欄位須與 receipt pytest_summary 交叉**，不一致 → pending 不得關閉。 |

**W10（補充）**：`gate_check.sh` jq 缺失 fail-open → 改 health check FAIL；與 B-HOOK 同批。

### 優先排序（全硬化 v1）

| 優先 | 項目 | 理由 |
|---|---|---|
| **P0** | W2 + W3 + B-FORGE | 與本次事故同型：自寫戳記 / 自寫 adversarial / 自寫 receipt |
| **P0** | W4 + B-HOOK + claim checker | 事故主路徑：不 commit 污染 HANDOFF + 假驗收 |
| **P1** | B-CLASS + B-LEDGER + #7 RESULT | 快測冒充慢測、pending 半開 |
| **P1** | #6 衝突檢查（非全文索引） | 紅燈後舊綠復活 |
| **P2** | W1 FACT 來源標記 | 接第 2/3 次事故，但實作成本低 |
| **P2** | W10 hook health + CI diff scan | 防 `--no-verify` / hook 未裝 |
| **P3（殘餘風險靠人）** | W6、W7、W8 | 邏輯空殼、人工稽核、記憶污染 |
| **P3** | W5 preflight 強制 | 已有 postflight 紅線；強制每次派工成本高 |
| **延後** | 全文 HANDOFF 自動索引 render | churn 高，衝突檢查已覆蓋核心風險 |

---

## 四、「治理加太多反而被繞」的真風險與平衡點（回答提問 ④）

### 真風險（按嚴重度）

1. **誤報驅動 EXEMPT 洗版**（最高）：作者學會 `# VERIFY-EXEMPT: spec-ambiguity:xxx` 貼在每段。→ 對策：窄白名單 + 每 issue 一次 + CI 統計 exempt 率 WARN。  
2. **`--no-verify` 常態化** → 對策：CI 必跑 `verification_claim_check.py --range ${base}...HEAD`；PR 不綠不能 merge。  
3. **同義詞軍備競賽** → 對策：WARN 模式收集未知詞 + 週期性補詞表；而非一次無限詞表。  
4. **receipt 疲勞**（每次改 HANDOFF 都要跑測試）→ 對策：只有 **operational mode 新 claim** 要 receipt；改待辦/阻塞/決策文字不觸發。  
5. **雙閘混淆**（`gate_check` token vs `verify_claim`）→ 對策：錯誤訊息明確分「派工門」與「驗收門」；文件一頁圖。  
6. **過度掃描 `docs/`** → 對策：v1 不掃一般 docs；只掃 HANDOFF/handoffs/commit。  

### 平衡點（Composer 立場）

> **在「commit / 交接邊界」fail-closed，在「討論 / 引用 / 否定舊 claim」fail-open。**

- **必須機器擋**：新的 operational 驗收斷言、偽 receipt、偽戳記、hook 缺席仍 merge。  
- **可以靠人**：§A 事實是否正確、adversarial 論點品質、MEMORY 軟性記憶。  
- **不做的**：企圖用 regex 證明「人對結果的詮釋正確」（SPEC §C 已誠實邊界，應保留）。  

**挑戰 Claude 結論**：Claude 說「全硬化值得」但用過多逃生口稀釋；我認為全硬化 **v1 範圍若鎖定 P0+P1**，日常可執行；若堅持「所有 docs + 全文索引 + 任意 READONLY_SIGNOFF」，**必**撞牆。

---

## 五、對實作派的硬性條件（全硬化可執行前提）

1. **先寫 claim-object 測試套件，再接 PreToolUse**（順序錯則必撞牆）。  
2. **審計事件為 receipt 必要條件**（B-FORGE）。  
3. **CI 為 hook 後盾**（B-HOOK 第三層不可省）。  
4. **豁免不得出現在 HANDOFF.md / commit / RESULT**（無例外）。  
5. **#6 v1 只做衝突檢查，不做自動 render**。  

---

## VERDICT

**VERDICT: APPROVED-WITH-CONDITIONS** — 使用者「全硬化」決策可執行，但須採納：(1) claim-object 偵測取代純詞表同段規則後才上 PreToolUse；(2) B-EXEMPT 限三類+禁 HANDOFF/commit/RESULT；(3) #6 v1 僅衝突檢查、全文索引延後；(4) `READONLY_SIGNOFF` 改為帶 task-id 的結構化 SIGNOFF，禁裸「已驗」；(5) W2/W3/W4 列 P0 與 B-FORGE 同批落地。未滿足 (1) 則判定 **全硬化過嚴且必撞牆**，應降級為「僅 commit-hook + receipt」而非 PreToolUse 全面攔截。

---

## 戳記(委員審議後 append;須 sha256 綁定本體)

RECONCILE-STAMP: composer APPROVED 2026-07-01 sha256:e798e006cf434487784d4ef99bfca834e591b406827b20766dc7ddc97181a934 task:VERIFYGATE-DELIB-COMPOSER
