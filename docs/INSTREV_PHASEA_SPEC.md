# 制度層總審查 Phase A(憲法重構+合約補齊)— SPEC

> 來源 PLAN/診斷:`handoffs/20260705-INSTREV-RECONCILE.md`(雙戳記 APPROVED)+ `handoffs/20260705-INSTREV-PHASEA-BRIEF-MANIFEST.md`　|　日期:2026-07-05　|　對應 TODO:`docs/INSTREV_PHASEA_TODO.md`

## §RISK 風險分級(gate 讀此決定要求強度)
- **大小**:大(制度層文件,全 agent 下游消費;使用者 2026-07-05 裁定「屬大、走完整管線」)。
- **命中高風險原則**:(b) 跨模組共用路徑——CLAUDE.md/AGENTS.md/.cursorrules 是所有 agent 每次載入的合約;(c) 多檔一批、改壞憲法會影響後續所有派工(git 可 revert,但錯誤版本存續期間的派工都受污染)。不命中 (a)(d):零程式/數值/ML 改動。
- RISK-HIT: b,c
- 不命中 (a)/(d) → §G Golden 於 §N 登記 N/A;adversarial review 仍必跑(大型雙家族鐵律 2026-06-09)。

## §A 假設與待使用者確認(事故:拿推論代替問人)
- **已驗證事實**(附 receipt;皆 Claude 實跑 2026-07-05):
  - FACT-RECEIPT: `wc -l CLAUDE.md .github/copilot-instructions.md docs/MULTI_AGENT_ORCHESTRATION.md AGENTS.md .cursorrules` → 印出 216 / 739 / 334 / 178 / 180(Claude 實跑 2026-07-05)
  - FACT-RECEIPT: `git log -1 --format="%ai %h" -- .github/copilot-instructions.md` → 印出 `2026-04-26 23:58:04 +0800 04d7691`,copilot 檔停更逾兩月(Claude 實跑 2026-07-05)
  - FACT-RECEIPT: `grep -rn "5 分鐘" CLAUDE.md AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md` → 唯一命中 CLAUDE.md:34(鐵律⑤);`grep -n "3 輪\|≤3 輪" AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md` → 印出 AGENTS.md:26、.cursorrules:19、ORCH:227、ORCH:241 四處(Claude 實跑 2026-07-05)
  - FACT-RECEIPT: `bash scripts/check_agent_contract_sync.sh` → 印出 `✅ 四源關鍵不變式一致(presence check)` exit 0,為改動前 baseline(Claude 實跑 2026-07-05)
  - FACT-RECEIPT: `grep -rln "CLAUDE.md\|AGENTS.md\|cursorrules\|copilot-instructions" scripts/*.sh scripts/*.py` → 印出僅 `scripts/check_agent_contract_sync.sh`、`scripts/register_legacy_committee_files.sh`(後者為 sha 白名單不 grep 內容)(Claude 實跑 2026-07-05)
- **機檢依賴面界定(adversarial 收窄,ADV-COMPOSER-1/CODEX-3)**:憲法檔的 **presence 機檢 = `check_agent_contract_sync.sh` 一支**(grep token 是否在);**語意/派工閘 = gate 族**(`gate.sh`/`gate_check.sh`/`template_check.sh`/`reconcile_stamps_check.sh`,依賴治理流程而非四檔逐行內容)。本批不改任何腳本(U-9 屬 Phase B),故不觸動 gate 族。
- **copilot 依賴收窄(adversarial,ADV-COMPOSER-9/CODEX-3)**:`.github/copilot-instructions.md` **無現役 scripts/gate 依賴**(見上 receipt);repo 內 `docs/ARCHITECTURE.md:485` 等歷史/低頻文件仍以**檔名**引用該檔——因本批把它改成 pointer 檔(不刪),連結不破、語意不誤導(指向的本就是指路檔)。
- **執行端現行分工(使用者 2026-07-05 額度切換)**:中/大 = **Composer 2.5(`cursor-agent`)實作 + Codex(`codex`)code review**(因 Codex 額度 limit,由 07-02 的 Codex 實作對調)。選層動態,以使用者當下指示為準;此即 [A-7] ORCH §1「現行分工行」要寫入的內容。本 Phase A 實作依此派 Composer。
- **待使用者確認**(未確認前不得實作):待確認:無(D-1~D-6 已全數裁決)。
- **已確認結果**:2026-07-05 使用者裁決(出處:memory project_instrev_rulings + HANDOFF.md):D-1 中型不跳步同意、D-2 copilot 刪換 pointer 同意、D-3 敘事移 SCAR_LEDGER 同意、D-4 否決固定選層改動態(單一「現行分工」行;現行=2026-07-05 中大 Composer 實作+Codex review,因 Codex 額度 limit 由 07-02 的 Codex 實作對調)、D-5 輪詢 10 分鐘同意、D-6 debug 統一 2 輪同意;附帶原則=憲法給 AI 用、簡潔明確、品質優先但避免 token 冗餘。
- **reconcile §E 疏漏之處置(adversarial,ADV-COMPOSER-2)**:Phase A 清單漏列 U-3,但 Phase A 標題即「合約補齊」且 U-3 裁決 3/3 收斂 → 判定列表筆誤,U-3 納入本批([A-12])。**權威依據=雙戳記 reconcile 全文 + 本 SPEC/manifest [A-12] + 使用者 D-1~D-6 裁決;§E 分期表為建議非窮舉**。Claude(編排者)另在舊 `handoffs/20260705-INSTREV-RECONCILE.md` 戳記區之後 append errata 記錄此歸屬(不動本體雜湊、不破既有戳記)。

## §C 約束(不重抄,引用+只列本任務相關)
- 本任務**純文件**,不碰 `momentum/`/`api/`/`frontend/`/`scripts/`/`templates/`;解耦 7 條與資料紅線不受影響但**其條文本體一字不可刪**(見 [A-4] 不可砍清單)。
- **允許改檔追加(adversarial,ADV-COMPOSER-11)**:`docs/MULTI_AGENT_BOOTSTRAP.md`(僅 L35 `debug ≤3 輪`→2,消滅第 5 個分叉源;歸 Task 3.3)。
- **明列不改**:`docs/ARCHITECTURE.md` 正文(含 L485 copilot 引用)——維持 U-11 不強制同步,僅檔頭 banner;L485 因 pointer 檔不刪故不破鏈,Task 1.2 收尾 SCOPE_CHANGES 註記即可。
- 共用路徑注意:CLAUDE.md 每 session 全載注入、AGENTS.md/.cursorrules 為執行端每次派工必讀合約、`scripts/check_agent_contract_sync.sh` grep 這四檔的 token(CONTRACT_TOKENS:`STATUS: BLOCKED`/`handoffs/`/`data_cache`/`SMALL_INLINE`/`ASSUMPTIONS_VERIFIED`/`反提示注入`;GLOBAL_TOKENS:`preflight`/`斷路器`/`委員會`)——改寫後全部 token 必須仍在。
- SessionStart hook 注入 HANDOFF.md、PreToolUse hook 讀 `scripts/gate_check.sh`——皆不依賴本批改動檔的行號/內文格式,無需同步。
- 執行端不得改 `HANDOFF.md`(根)與本 SPEC/TODO/manifest;交接寫 `handoffs/20260705-INSTREV-PHASEA-impl.md`。

## §P Phase 與依賴(事故:宣稱無依賴卻有 forward dependency)
> 自檢:Task 輸入來源皆為前置 Phase 或既有檔案,無 forward dependency。Phase 6 為 Claude 收尾自做,不在派工 scope。

### Phase 1 — 新建傷疤帳本 + 淘汰死文件(依賴:無)
**Task 1.1 — [A-2] 新建 `docs/SCAR_LEDGER.md`**
- 目標:建立「規則傷疤帳本」,收納各規則的出生事故敘事。檔案:`docs/SCAR_LEDGER.md`(新建,無既有 caller)。
- 改法:表格式,欄=規則名 / 出生事故一行(日期+發生什麼+後果) / 現行 enforcement(gate 機檢/合約條文/prose) / 出處(commit、handoffs 檔名或「記憶(原始 commit 未尋獲)」)。首批條目=從 CLAUDE.md 將移出的敘事(Task 2.1 清單):實測>假設兩事故(underscore/warmup)、驗證保真度三事故(V2 timestamp a/b/c)、C3 委員會相關性錯誤、gate 兩次事故(漏 §G 範本/相同框架)、06-05 中大鐵律出生(06-04 feature-browser 自行跳步,出處標「記憶(原始 commit 未尋獲)」)、06-10 solo 硬幹整夜(斷路器出生)、06-02 stdin 卡死(timeout+/dev/null 鐵律)、07-01 FF 驗收捏造(verify receipt 出生)、選層三處分叉(07-05 總審查發現,D-4 動態制出生)。
- **驗證(可證偽)**:檔案存在且 `grep -c "^|" docs/SCAR_LEDGER.md` ≥ 12(表頭+≥10 條目);`grep -q "記憶(原始 commit 未尋獲)" docs/SCAR_LEDGER.md` exit 0。
- **邊界(≥2)**:①敘事在 CLAUDE.md 與手冊重複出現 → 帳本只收一條,兩處各留 pointer;②事故出處找不到原始 commit → 不捏造 hash,標「出處=記憶」。
- 不可做:不改寫事故內容/日期(忠實搬運);不在帳本裡新增規則;不收錄本 SPEC 未列且 CLAUDE.md 未移出的敘事。

**Task 1.2 — [A-1] copilot-instructions.md 淘汰**
- 目標:739 行 → ≤15 行 pointer。檔案:`.github/copilot-instructions.md`(整檔重寫;無 agent 依賴,見 §A receipt)。
- 改法:保留檔名,內容=標題+一句「本檔已淘汰(2026-07-05 制度層總審查 U-1,使用者核准 D-2)」+指向 `CLAUDE.md`(專案規範)/`AGENTS.md`(執行端合約)/`docs/MULTI_AGENT_ORCHESTRATION.md`(編排)。
- **驗證(可證偽)**:`wc -l .github/copilot-instructions.md` ≤ 15;`grep -q "CLAUDE.md" .github/copilot-instructions.md` exit 0。
- **邊界(≥2;adversarial 收窄 ADV-COMPOSER-9)**:①**檔名級**引用(如 `docs/ARCHITECTURE.md:485`)→ 因 pointer 檔不刪、連結不破,**不 BLOCKED**,收尾 SCOPE_CHANGES 註記即可,不改該正文;若發現引用 copilot **內文具體段落/數值** → 才 BLOCKED 回報;②pointer 不得引用將被移動的段落名(只指檔案)。
- 不可做:不刪檔(留 pointer 檔);不把 739 行內容搬到別處(內容已 stale,CLAUDE.md 為準)。

### Phase 2 — CLAUDE.md 重構(依賴:Phase 1 之 SCAR_LEDGER 存在)
**Task 2.1 — [A-3][A-5] 敘事移出+觸發句**
- 目標:規則全留、敘事出走,216 行 → ≤140 行。檔案:`CLAUDE.md`。
- 改法:移出候選(僅此清單):①「Validate Assumptions」節兩事故敘事段(規則 4 步驟留);②「驗證保真度鐵律」的第三次事故敘事段(三條強制規則全留);③「Fail-closed Gate」節內「設計理由見兩次事故…」重複敘事(規則+開門指令留,細節已在 ORCH「Gate」節);④任務分派節內日期考據 prose(「2026-06-0X 使用者定」的敘事脈絡,規則本體與「定死」效力標記留)。每個移出處留一行:「出處與事故敘事見 `docs/SCAR_LEDGER.md`」。並保留/補「何時必須去讀哪檔」觸發句:規則出處→`docs/SCAR_LEDGER.md`、派工/委員會→`docs/MULTI_AGENT_ORCHESTRATION.md`、SPEC/TODO→`templates/`;引用一律 repo 固定路徑。
- **驗證(可證偽)**:`wc -l CLAUDE.md` ≤ 140;`grep -c "SCAR_LEDGER" CLAUDE.md` ≥ 3;移出的每段敘事可在 SCAR_LEDGER 以關鍵詞(underscore、1970-01-21、C3、feature-browser)grep 到。
- **邊界(≥2)**:①同一段落規則與敘事交織 → 逐句拆,規則句留原位,敘事句搬走,不整段刪;②拿不準是規則還是敘事 → 當規則留下(寧多留不誤刪)。
- 不可做:不刪 [A-4] 不可砍清單任何條文;不改規則語義;不動「Key Directories/Dev Commands/Code Standards/Pre-Commit Checklist」等非治理節(除非僅為對齊 pointer)。

**Task 2.2 — [A-6][A-7][A-9] 任務分派決策表+選層 pointer+輪詢 10 分鐘**
- 目標:「任務分派規則」約 40 行 prose → 一張決策表+少量固定條款。檔案:`CLAUDE.md`「Multi-Agent 協作協議→任務分派規則」節。
- 改法:表欄=小/中/大;表列=①判準(小:1 函式/test/局部 bug 且不命中 a-d 且可本地驗;中:單一 module 動既有 caller 不命中 a-d;大:命中任一 a-d,不看檔案數)、②管線(小:直接做+自測;中/大:SPEC+TODO+adversarial 完整管線不得跳步[D-1],大另附白話簡述+manifest+雙家族 adversarial)、③執行端(=pointer:「見 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行,動態、以使用者當下指示為準」,不寫死名字)、④code review 方(中/大必派另一方,實作者不自審)、⑤SMALL_INLINE 條件(免 SPEC 需含 scope/驗收命令/允許檔/禁止事項)、⑥膨脹升級 5 訊號(檔案數超預期/碰 factories·protocols·config 共用路徑/新既有 caller/測試面擴大/觸及 a-d)、⑦判不出→明講不確定+先當中辦,絕不靜默假設。表下保留固定條款:a-d 原則定義、中大鐵律①~④(第⑤條輪詢改「**派工進度每 10 分鐘回報一次**」[D-5])、「別問鐵律」。日期考據移 SCAR_LEDGER(Task 2.1 已含)。
- **驗證(可證偽;adversarial 修牙 ADV-COMPOSER-4)**:`grep -q "每 10 分鐘" CLAUDE.md` exit 0 且 `grep -rn "每 5 分鐘" CLAUDE.md AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md` 0 命中;`grep -q "現行分工" CLAUDE.md` exit 0(pointer 句);CLAUDE.md 不再寫死任何執行端分工——`grep -nE "Codex.*實作|Composer.*實作|GPT-5.5.*實作" CLAUDE.md` 0 命中(全/半形括號皆涵蓋,取代舊半形無牙 grep)。
- **邊界(≥2)**:①既有條款與表內容重複 → 刪 prose 留表,語義不變;②表格塞不下的長條款(如 a-d 定義)留表外條列,表內放引用。
- 不可做:不改小/中/大判準實質;不砍「判不出→問」與膨脹偵測;不在 CLAUDE.md 重複 ORCH §1 選層內容(只 pointer)。

### Phase 3 — ORCHESTRATION 手冊(依賴:無,可與 Phase 2 並行;同批派工序列做)
**Task 3.1 — [A-7] §1 選層改單一「現行分工」行**
- 目標:選層單一來源。檔案:`docs/MULTI_AGENT_ORCHESTRATION.md` §1。
- 改法:刪固定選層表中「何時用」欄的寫死分工敘述與「選層原則(2026-06-03 A/B 實證後定)」的固定結論,改為:**單一現行分工行**——「**現行分工(2026-07-05 使用者指示,因 Codex 額度 limit 切換):中/大=Composer 2.5(`cursor-agent`)實作+Codex(`codex`)code review;小=Claude 自做**。選層為**動態**:一律以使用者最新口頭指示為準(使用者依各 agent usage 切換,未來可能加新執行端;新執行端須先過 §8 T-D 對等性測試才可寫入)。」工具表「何時用」欄改中性 pointer(不含精確「現行分工」四字);保留:工具表(CLI 與能力閘門)、agy read-only 限制、A/B 實證誠實邊界、preflight/postflight 要求。
- **驗證(可證偽)**:`grep -c "現行分工" docs/MULTI_AGENT_ORCHESTRATION.md` = 1(單一來源);`grep -q "T-D" docs/MULTI_AGENT_ORCHESTRATION.md` exit 0。
- **邊界(≥2)**:①§6「主力決策法」含歷史選層敘述 → 保留(那是決策方法非現行結論),但若與「動態以使用者為準」矛盾處加一句「最終以 §1 現行分工行為準」;②快取的舊日期敘事(06-03 定層)→ 移 SCAR_LEDGER 或刪,不留第二個結論。
- 不可做:不刪能力閘門(T-D)與 agy 禁寫入;不改 §8 測試集。

**Task 3.2 — [A-8] 中型管線矛盾修復**
- 目標:刪「中型跳步」敘述,單一來源=CLAUDE.md 決策表。檔案:`docs/MULTI_AGENT_ORCHESTRATION.md`「SPEC/TODO 作者流程」分層表。
- 改法:分層表「中」列由「寫 SPEC→直接從 SPEC 派工,跳獨立 TODO+跳一次 adversarial」改為「完整管線同大型(SPEC+TODO+至少一家不同模型 adversarial;2026-06-05 使用者定死不得跳步,D-1 維持)——分級判準與步驟見 CLAUDE.md 任務分派決策表」。
- **驗證(可證偽)**:`grep -n "跳獨立 TODO" docs/MULTI_AGENT_ORCHESTRATION.md` 0 命中;`grep -q "任務分派決策表" docs/MULTI_AGENT_ORCHESTRATION.md` exit 0。
- **邊界(≥2)**:①「小」列(不寫 SPEC)不受 D-1 影響 → 保留;②大任務管線 6 步驟敘述與 CLAUDE.md 表重複 → 手冊留操作細節(它是操作手冊),但分級歸屬句指向 CLAUDE.md 表。
- 不可做:不砍大任務管線 6 步驟操作說明;不改信任分工表。

**Task 3.3 — [A-11 之 ORCH 部分] debug 輪數 3→2**
- 目標:ORCH 兩處「≤3 輪」與兩輪斷路器一致。檔案:`docs/MULTI_AGENT_ORCHESTRATION.md` L227、L241 附近。
- 改法:§5 兩處「debug ≤ 3 輪」→「debug ≤ 2 輪」,並補一句依據「(2026-06-10/06-25 使用者兩輪斷路器指示,詳 SCAR_LEDGER)」。
- **驗證(可證偽)**:`grep -n "3 輪\|≤3 輪" docs/MULTI_AGENT_ORCHESTRATION.md AGENTS.md .cursorrules` 0 命中(Phase 4 完成後合併驗)。
- **邊界(≥2)**:①「重派 ≤ 2 輪」宏觀斷路器既有敘述 → 不動;②若發現其他檔還有 3 輪殘留(templates 外)→ 回報列入 diff,不擅自擴 scope 改 templates。
- 不可做:不改宏觀斷路器(重派 ≤2 輪升級使用者)語義。

### Phase 4 — 執行端合約補齊(依賴:無;與 Phase 3 同批序列做)
**Task 4.1 — [A-10] HANDOFF 所有權矛盾修復**
- 目標:同檔內「更新 HANDOFF.md」vs 第 7 條「絕不重寫根 HANDOFF」矛盾消除。檔案:`AGENTS.md` L8-10「最後一步」節、`.cursorrules` L5-6「協作協議」節。
- 改法:兩處改為「**結束前(必執行)**:寫交接到 `handoffs/<YYYYMMDD>-<task-id>.md`(append-only,≤30 行:正在做/待辦/阻塞/決策/踩坑);根 `HANDOFF.md` 由 Claude 維護,執行端不得改寫」。
- **驗證(可證偽)**:`grep -n "更新 \`HANDOFF.md\`\|更新 HANDOFF.md" AGENTS.md .cursorrules` 0 命中於頂部節(第 7 條的「不可覆蓋」敘述保留);兩檔皆 `grep -q "由 Claude 維護"` exit 0。
- **邊界(≥2)**:①第 7 條與頂部改後語義重複 → 兩處都留(頂部=指令,第 7 條=紅線),用詞一致;②互動模式(使用者直接開 Codex/Cursor 對話)同樣適用此規則,不分派工/互動。
- 不可做:不刪「≤30 行」交接格式要求。

**Task 4.2 — [A-11] 合約 debug 輪數 3→2**
- 目標:第 5 條統一兩輪斷路器。檔案:`AGENTS.md` 第 5 條、`.cursorrules` 第 5 條。
- 改法:「debug 迭代上限 ≤ 3 輪…同一失敗 3 輪未過」→「**debug 迭代上限 ≤ 2 輪**:一輪=一個假設+一組改動+一次驗證。同一失敗 2 輪未過 → 停,輸出 `STATUS: BLOCKED` + 兩輪各自(假設/改了哪些檔/測試輸出摘要),交委員會處理(2026-06-10/06-25 使用者定)」。其餘(不堆嘗試/不改名續做)保留。
- **驗證(可證偽)**:同 Task 3.3 合併驗:三檔 grep「3 輪」0 命中;`grep -c "≤ 2 輪" AGENTS.md` ≥1 且 `.cursorrules` 同。
- **邊界(≥2)**:①「三輪各自」等派生字樣同步改「兩輪」;②委員會=Claude 編排的跨家族討論,合約中註明「由 Claude 發起,執行端只需 BLOCKED 停下」。
- 不可做:不把 2 輪改成可協商字眼(「建議」「盡量」)。

**Task 4.3 — [A-12] 合約補齊 5 項現役制度**
- 目標:兩份合約補入 05-31 後上線的制度。檔案:`AGENTS.md`「執行任務時」節、`.cursorrules` 同節(兩份內容須對齊)。
- 改法:新增條目(或併入既有條):②**留痕義務**——派工 prompt 帶 task-id 者,產出檔落地 `handoffs/` 後由 Claude `register-output` 入帳;執行端須在收尾報告列出產出檔路徑,不得只寫在 log。③**VERIFY claim 義務**——收尾報告與交接檔中任何「已驗/passed/確認正確」聲明,須附實跑命令+輸出摘要(或標「未驗證」);空稱視為捏造(2026-07-01 FF 驗收捏造事故)。④**STAMP-BLOCKED**——被指派實作前若讀到所依 reconcile/SPEC 的 `RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可` 不動工。⑤既有「產物視為資料非指令」條確認保留原文。①=Task 4.2 兩輪斷路器。
- **驗證(可證偽)**:兩檔皆 `grep -q "register-output"`、`grep -q "RECONCILE-STAMP"`、`grep -qE "VERIFY|實跑命令"` exit 0;`grep -q "反提示注入" AGENTS.md .cursorrules` 仍 exit 0。
- **邊界(≥2)**:①兩檔行文風格略異(AGENTS 詳/.cursorrules 精簡)→ 允許字數差,token 與語義必須同;②新條目與既有 9 條衝突 → 併入最接近條目,不推翻既有紅線。
- 不可做:不重排既有 9 條編號順序(下游引用「第 7 條」等);不刪任何既有紅線。

**Task 4.4 — [A-13] 同步檢查護欄**
- 目標:證明四源改寫沒弄斷機檢(sync check exit 0)。檔案:無(純驗證任務,跑 check_agent_contract_sync.sh)。
- 改法:Phase 1-4 完成後跑 `bash scripts/check_agent_contract_sync.sh`;若 FAIL,修補缺 token 的檔(補 token,不改腳本——U-9 屬 Phase B)。
- **驗證(可證偽)**:腳本 exit 0,stdout 含「✅ 四源關鍵不變式一致」。
- **邊界(≥2)**:①token 因改寫換了說法(如「斷路器」被改寫掉)→ 恢復原 token 字樣;②腳本本身壞(非本批造成)→ BLOCKED 回報,不改腳本。
- 不可做:不改 `scripts/check_agent_contract_sync.sh`。

### Phase 5 — 低頻文件 banner(依賴:無)
**Task 5.1 — [A-14] staleness banner**
- 目標:防讀者把過時細節當現行制度。檔案:`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT_GUIDE.md`(僅檔頭插入,各 ≤4 行)。
- 改法:標題下插入 blockquote:「> ⚠️ 治理制度(協作/派工/gate)以 `CLAUDE.md` 與 `docs/MULTI_AGENT_ORCHESTRATION.md` 為準;本檔最後驗證 2026-07-05,其後細節可能過時。」
- **驗證(可證偽)**:兩檔 `grep -q "最後驗證 2026-07-05"` exit 0;`git diff --stat` 顯示兩檔各改動 ≤6 行。
- **邊界(≥2)**:①檔頭已有其他 banner → 併列不覆蓋;②不動兩檔正文任何一行。
- 不可做:不「順手」修兩檔內文的過時敘述(那是明確的不強制同步裁決 U-11)。

### Phase 6 — 記憶層同步(依賴:Phase 2-4 完成;**Claude 自做,不在派工 scope**)
**Task 6.1 — [A-15][A-16] 記憶 pointer 化**
- 目標:多 agent 規則以 repo 憲法為單一來源,記憶留使用者偏好。檔案:`~/.claude/projects/.../memory/`(repo 外,executor sandbox 不可達,故 Claude 自做)。
- 改法:feedback_task_routing 頂部加 SUPERSEDED 標記指向 CLAUDE.md 決策表(保留歷史軌跡供考據);feedback_dispatch_polling 內文改 pointer(CLAUDE.md 已載 10 分鐘);盤點與憲法重疊條目(兩輪斷路器/adversarial 紀律/reconcile 戳記等)逐條標「規則本體見 repo 憲法」;偏好類(繁中/push 不問/brief 白話/veto 彈窗/gemini 只研究)保留;MEMORY.md 索引行同步。
- **驗證(可證偽)**:`grep -q "SUPERSEDED" feedback_task_routing.md` exit 0;MEMORY.md 對應行含新語義。
- **邊界(≥2)**:①記憶條目含 repo 沒有的細節(quota role-swap 操作紀律)→ 保留該 delta 段;②刪錯記憶不可逆 → 只改標記/內文,不刪檔。
- 不可做:不刪任何記憶檔;不把使用者偏好搬進 repo。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**:RISK-HIT: b,c(不含 a/d)且無「聲稱驗數值正確性」的測試 → mutation N/A(§N 登記)。本批驗收全走可證偽 grep/wc/exit-code。
- **行數目標(adversarial,ADV-COMPOSER-12)**:`wc -l CLAUDE.md` **≤140 為硬上限、~130 為期望**;驗收以 140 為準,不得為壓 130 誤刪規則句。
- 測試層級:①每 Task 驗證命令(上列,全部可獨立 bash 跑,不需 run_api.py);②整批驗收=TODO §B Gate 全套(含下列③④),依序跑:`bash scripts/check_agent_contract_sync.sh`(exit 0)、`wc -l CLAUDE.md`(≤140)、`wc -l .github/copilot-instructions.md`(≤15)、**四檔 grep「3 輪」=0(含 `docs/MULTI_AGENT_BOOTSTRAP.md`)**、四檔 grep「每 5 分鐘」=0、`grep -c "現行分工" docs/MULTI_AGENT_ORCHESTRATION.md`=1、`ls docs/SCAR_LEDGER.md`。
- ③**[A-4] 規則零刪減核對(adversarial 重寫,ADV-COMPOSER-3/5)**:分**兩張表按條文實際所在檔** grep(用真實 baseline token,非臆想 token):
  - **CLAUDE.md 必留 12 token**(2026-07-05 實測皆存在,改後須仍在):`data_cache`、`momentum/`(解耦表)、`Validate Assumptions`、`驗證保真度`、`三方數據`、`雙家族`、`adversarial`、`gate_check.sh`、`斷路器`、`否決`、`不跳`(或「不得」+「跳」中大不跳步)、`preflight`。
  - **合約(AGENTS.md+.cursorrules)必留**:既存 `反提示注入`;A-12 **新增後**須有 `register-output`、`RECONCILE-STAMP`、`VERIFY`(此三者改前=0,屬 Task 4.3 新增產物,故在 Task 4.3 post-add 驗,不列改前 baseline)。
  - **不列 CLAUDE.md**:`繁中`/`白話`/`push`=記憶專屬 user pref(U-10 定留記憶不入 repo),於 Phase 6 記憶層驗。
  - 任一「改前存在」token 改後落空=驗收 FAIL 退回。
- ④**A-12 新制度落地驗**:兩合約各 `grep -q "register-output"`、`grep -q "RECONCILE-STAMP"`、`grep -qE "VERIFY|實跑命令"` 皆 exit 0(CONV-1)。
- **sync 殘量註記(adversarial,ADV-COMPOSER-7)**:`check_agent_contract_sync.sh` 的 CONTRACT_TOKENS 尚未含 A-12 新 token(U-9=Phase B)→ **sync 綠 ≠ 新制度已齊**;U-9 前以上④的 Task 4.3 grep 為權威。
- **防假綠**:本批無 pytest 斷言可放寬;假綠風險=「敘事沒搬就刪」→ 靠 SCAR_LEDGER 關鍵詞 grep(`underscore`、`1970-01-21`、`C3`、`feature-browser`、字面 `stdin`)雙向核對:CLAUDE.md 刪掉的每個事故關鍵詞必須在 SCAR_LEDGER 出現、且在 CLAUDE.md 已 `grep -c`=0(負向核對,ADV-COMPOSER Suggestion)。
- **邊界目錄**:空DF/全NaN/Inf/並發等數值邊界不適用(純文件);適用邊界=各 Task「邊界」欄(交織段落拆句、token 改寫斷 sync check、pointer 指向被移動段落)。

## §R 回退
- 每 Phase 獨立 commit(1.1/1.2 可合一),整批可 `git revert` 區間回退;無 feature flag 需求(文件無執行路徑);sync check FAIL → 不 merge、不更新 HANDOFF 宣告完成。
- 記憶層(Phase 6)獨立於 git:改壞可由本 SPEC 的改法欄重建,且不刪檔保底。

## §N N/A 登記(被省略的必填段,逐一標理由,不可直接刪)
- §G Golden:N/A — RISK-HIT: b,c,不含 (a)/(d);零數值/特徵/ML 路徑改動,無 baseline 可凍結;行為不變性由 §V 的 grep/wc/exit-code 可證偽驗收替代。
- §V mutation:N/A — 無聲稱驗數值正確性的測試;文件改動的「改壞會 FAIL」由 sync check token 檢查與零刪減 grep 清單承擔。
- feature/kline 三方簽核:N/A — 不涉 feature/kline 生成/計算/merge/split。
