# 制度層總審查 Phase A TODO(版本 V1/狀態 DRAFT/基於 docs/INSTREV_PHASEA_SPEC.md/2026-07-05)

> 冷啟動說明:本 TODO 自足,執行端不需回讀 SPEC 即可逐 Task 寫改動;有疑義以 `docs/INSTREV_PHASEA_SPEC.md` 為準,矛盾 → `STATUS: BLOCKED`。

## §0 全域規則與約束(執行端讀完即可遵守)
- **本批=純文件改動**,允許改的檔案**只有**:`.github/copilot-instructions.md`、`CLAUDE.md`、`AGENTS.md`、`.cursorrules`、`docs/MULTI_AGENT_ORCHESTRATION.md`、`docs/MULTI_AGENT_BOOTSTRAP.md`(僅 L35 debug 輪數,adversarial 追加)、`docs/ARCHITECTURE.md`(僅檔頭)、`docs/DEVELOPMENT_GUIDE.md`(僅檔頭)、新建 `docs/SCAR_LEDGER.md`。**禁改**:`scripts/`、`templates/`、`momentum/`、`api/`、`frontend/`、根 `HANDOFF.md`、`docs/ARCHITECTURE.md` 正文(含 L485 copilot 引用)、本 TODO/SPEC/manifest。
- 解耦 7 條/NaN gate/資料紅線:本批不觸及程式,**但其在 CLAUDE.md/合約中的條文一字不可刪**(見 Task 2.3 零刪減清單)。
- **token 保留清單**(`scripts/check_agent_contract_sync.sh` 會 grep,改寫時原字樣必須留在對應檔):AGENTS.md 與 .cursorrules 皆須含 `STATUS: BLOCKED`、`handoffs/`、`data_cache`、`SMALL_INLINE`、`ASSUMPTIONS_VERIFIED`、`反提示注入`;四檔(加 CLAUDE.md、docs/MULTI_AGENT_ORCHESTRATION.md)合計須含 `preflight`、`斷路器`、`委員會`。
- 防假綠:驗證命令逐條真跑,輸出貼收尾報告;「敘事已搬」須可 grep 證明(關鍵詞雙向核對,見 Task 2.3),不得刪了沒搬。
- 語言:繁體中文,禁簡體字。commit 前綴 `docs(gov):`。
- 交接寫 `handoffs/20260705-INSTREV-PHASEA-impl.md`,**不改根 HANDOFF.md**(由 Claude 維護)。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 5.1 | Task 2.1 依賴 1.1(SCAR_LEDGER 先存在);其餘互獨,同批序列做 | 全屬治理文件、單執行端序列改,拆批只增派工輪 | 大(檔多但機械) |
| —(不派工) | 6.1 | B1 完成 | 記憶目錄在 repo 外,executor sandbox 不可達,Claude 自做 | 小 |
- 批次內順序:1.1 → 1.2 → 2.1 → 2.2 → 2.3(驗證)→ 3.1 → 3.2 → 3.3 → 4.1 → 4.2 → 4.3 → 4.4(驗證)→ 5.1 → 整批驗收命令(§B Gate)。
- **§B Gate(整批驗收,全部須過;adversarial reconcile CONV-1/COMPOSER-3/5/6/7/11 已補全)**:
  ```bash
  bash scripts/check_agent_contract_sync.sh                      # exit 0
  wc -l CLAUDE.md                                                # ≤140(硬上限;~130 期望)
  wc -l .github/copilot-instructions.md                          # ≤15
  grep -n "3 輪\|≤3 輪" AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md docs/MULTI_AGENT_BOOTSTRAP.md  # 0 命中(含 BOOTSTRAP)
  grep -rn "每 5 分鐘" CLAUDE.md AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md  # 0 命中
  grep -cE "^\*\*現行分工|^- \*\*現行分工|現行分工\(" docs/MULTI_AGENT_ORCHESTRATION.md   # =1(錨點式,非裸字串)
  ls docs/SCAR_LEDGER.md                                         # 存在
  # [A-4] CLAUDE.md 零刪減:12 個改前實測存在的 token 改後須仍在(缺=FAIL)
  for t in data_cache "momentum/" "Validate Assumptions" 驗證保真度 三方數據 雙家族 adversarial gate_check.sh 斷路器 否決 不跳 preflight; do grep -q "$t" CLAUDE.md || echo "DELETED_RULE:$t"; done  # 無 DELETED_RULE
  # [A-12] 合約新制度落地(改前=0,改後兩檔皆須有)
  for f in AGENTS.md .cursorrules; do for t in register-output RECONCILE-STAMP VERIFY 反提示注入; do grep -q "$t" "$f" || echo "MISSING_CONTRACT:$f:$t"; done; done  # 無 MISSING_CONTRACT
  # 敘事已搬:關鍵詞在 SCAR_LEDGER 有、在 CLAUDE.md 無(負向核對)
  for kw in underscore 1970-01-21 C3 feature-browser stdin; do grep -q "$kw" docs/SCAR_LEDGER.md || echo "SCAR_MISSING:$kw"; done   # 無 SCAR_MISSING
  for kw in 1970-01-21 feature-browser; do [ "$(grep -c "$kw" CLAUDE.md)" = 0 ] || echo "NOT_MOVED:$kw"; done  # 無 NOT_MOVED(敘事應已離開 CLAUDE)
  ```

## Phase 1 — 新建傷疤帳本+淘汰死文件(完成後:SCAR_LEDGER 可被 CLAUDE.md 引用;copilot 檔只剩 pointer)

### Task 1.1 — [A-2] 新建 docs/SCAR_LEDGER.md
- SPEC ref:Task 1.1　目標:建「規則傷疤帳本」收納規則出生事故敘事。
- 輸入/輸出:輸入=CLAUDE.md 現有敘事段+下列事故清單;輸出=新檔 `docs/SCAR_LEDGER.md`(markdown 表)。
- 實作要點:①檔頭一段說明用途(「規則=傷疤;本檔存『為什麼』,規則本體在 CLAUDE.md/合約;增規則時此處記出生事故」);②表欄=`| 規則 | 出生事故(日期+一行) | 現行 enforcement | 出處 |`;③首批 ≥10 條:實測>假設(underscore blacklist 靜默失效、warmup 誤判,2026-05 前)、驗證保真度三事故(V2 timestamp:§A 未實跑 `_layer0`→fail-closed abort;ms/秒 fixture 假綠 1970-01-21 錯軸;multi-TF 玩具 fixture 降級放走)、C3 委員會相關性錯誤(相同框架餵多模型一起錯)、gate 出生兩事故(寫 SPEC 沒開範本漏 §G;always-loaded 原則在 context 仍被漏)、06-05 中大鐵律(06-04 feature-browser 自行跳 TODO+adversarial,出處=記憶(原始 commit 未尋獲))、兩輪斷路器(06-10 solo 硬幹整夜:timeout/孤兒temp/fracdiff 誤導)、timeout+`</dev/null` 鐵律(06-02 stdin 卡死實測)、VERIFY receipt/claim gate(07-01 FF 驗收捏造:smoke 寫成已驗)、D-4 動態選層(選層三處三答案分叉,07-05 總審查)。
- 修改檔案:`docs/SCAR_LEDGER.md`(新建,無既有 caller)。
- 不可做:不改寫事故內容/日期;不在帳本新增規則;不收 SPEC 未列敘事。
- 邊界:①同敘事在 CLAUDE.md 與手冊重複 → 帳本一條,兩處各留 pointer;②找不到原始 commit → 標「出處=記憶(原始 commit 未尋獲)」,不捏造 hash。
- 風險緩解:⊘(新檔,git revert 即回退)。
- 驗證:`grep -c "^|" docs/SCAR_LEDGER.md` ≥12;`grep -q "記憶(原始 commit 未尋獲)" docs/SCAR_LEDGER.md` exit 0;§B Gate 關鍵詞迴圈無 MISSING。

### Task 1.2 — [A-1] copilot-instructions.md 淘汰
- SPEC ref:Task 1.2　目標:739 行 stale 檔換 ≤15 行 pointer。
- 輸入/輸出:輸入=現檔(內容全棄);輸出=同路徑 pointer 檔。
- 實作要點:①整檔重寫,內容=標題+「本檔已淘汰(2026-07-05 制度層總審查 U-1,使用者核准 D-2)」+三行指路:`CLAUDE.md`(專案規範)/`AGENTS.md`(執行端合約)/`docs/MULTI_AGENT_ORCHESTRATION.md`(編排);②不刪檔、不搬舊內容。
- 修改檔案:`.github/copilot-instructions.md`(整檔)。既有 caller:無(§A receipt:全 repo scripts 無引用)。
- 不可做:不刪檔;不把舊 739 行任何段落搬到其他檔。
- 邊界(adversarial 收窄,ADV-COMPOSER-9):①**檔名級**引用(如 `docs/ARCHITECTURE.md:485` 以檔名列 copilot-instructions)→ 因 pointer 檔不刪、連結不破,**不 BLOCKED**,收尾 SCOPE_CHANGES 註記即可,不改該正文;②若發現有檔引用 copilot **內文的具體段落/數值**(非僅檔名)→ 才 `STATUS: BLOCKED` 回報;③pointer 只指檔案,不指段落名。
- 風險緩解:⊘。
- 驗證:`wc -l .github/copilot-instructions.md` ≤15;`grep -q "CLAUDE.md" .github/copilot-instructions.md` exit 0。

## Phase 2 — CLAUDE.md 重構(完成後:216→≤140 行,規則全留、敘事在 SCAR_LEDGER)

### Task 2.1 — [A-3][A-5] 敘事移出+觸發句
- SPEC ref:Task 2.1　目標:CLAUDE.md 敘事出走、規則留、pointer 補。
- 輸入/輸出:輸入=CLAUDE.md 現 216 行+Task 1.1 產出;輸出=改寫後 CLAUDE.md。
- 實作要點(移出候選**僅此四類**):①「Validate Assumptions」節末兩事故敘事段(斜體 *Established after two incidents…*)→ 已在 SCAR_LEDGER,原處留「出處見 `docs/SCAR_LEDGER.md`」;規則 4 步驟全留。②「驗證保真度鐵律」的「*第三次事故:V2 timestamp…*」敘事段 → 同上;三條強制規則全留。③「Fail-closed Gate」條內「**設計理由見兩次事故**:always-loaded 原則…不靠 Claude 記得」句與重複的設計理由 prose → 縮成「設計理由與事故見 `docs/SCAR_LEDGER.md` 與 ORCH Gate 節」;開門指令、三道機檢、誠實邊界句留。④任務分派節日期考據(「2026-06-0X 使用者定死」的敘事脈絡句)→ 規則本體+「(使用者定死,出處見 SCAR_LEDGER)」效力標記留,考據移走。另:全檔確認引用皆 repo 固定路徑,補三句觸發句(規則出處→SCAR_LEDGER;派工/委員會→`docs/MULTI_AGENT_ORCHESTRATION.md`;SPEC/TODO→`templates/`)。
- 修改檔案:`CLAUDE.md`(治理節);**不動** Key Directories/Dev Commands/Code Standards/Pre-Commit Checklist 等節(pointer 對齊除外)。既有 caller:所有 agent session 注入+`check_agent_contract_sync.sh`(token 見 §0)。
- 不可做:不刪 Task 2.3 清單任何條文;不改規則語義;不砍非治理節。
- 邊界:①規則與敘事交織段 → 逐句拆,規則句留原位;②拿不準 → 當規則留下(寧多留不誤刪)。
- 風險緩解:與 Task 2.2 同 commit 可整體 revert。
- 驗證:`grep -c "SCAR_LEDGER" CLAUDE.md` ≥3;§B Gate 關鍵詞(underscore/1970-01-21/C3)已不在 CLAUDE.md 而在 SCAR_LEDGER:`grep -c "1970-01-21" CLAUDE.md` =0。

### Task 2.2 — [A-6][A-7][A-9] 任務分派決策表+選層 pointer+輪詢 10 分鐘
- SPEC ref:Task 2.2　目標:分派規則 prose → 單一決策表;選層不寫死;輪詢 5→10 分鐘。
- 輸入/輸出:輸入=CLAUDE.md「任務分派規則」節(~40 行 bullets);輸出=決策表+固定條款。
- 實作要點:①決策表欄=小/中/大,列=判準(小:改1函式/test/局部bug、不命中a-d、可本地驗;中:單一module動既有caller、不命中a-d;大:命中任一a-d——模組會變原則不變,不看檔案數)/管線(小:自己做+自測;中/大:SPEC+TODO+adversarial 完整管線**不得跳步(2026-06-05 使用者定死,D-1 維持)**,大另附白話簡述+manifest+**雙家族** adversarial(2026-06-09 定死))/執行端(**pointer**:「見 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行;動態,以使用者當下指示為準」)/code review(中/大必派另一方,實作者不自審)/SMALL_INLINE(免SPEC需含scope+驗收命令+允許檔+禁止事項)。②表外固定條款:a-d 定義(現文照留)、膨脹升級 5 訊號、判不出→明講+先當中辦、中大鐵律①~⑤(⑤改「**派工進度每 10 分鐘回報一次**」)、「唯一允許省步=動工前明列讓使用者否決」。③刪與表重複的 prose bullets(小/中/大三條長 bullet 與「執行端選層(2026-06-03…)」bullet——後者內容歸 ORCH §1)。
- 修改檔案:`CLAUDE.md`「Multi-Agent 協作協議→任務分派規則」節。既有 caller:同 Task 2.1。
- 不可做:不改判準實質;不砍膨脹偵測/判不出條款;不在 CLAUDE.md 寫死執行端名字。**「大」列與「中」列執行端欄一致=pointer「見 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行」**;現檔 L28「大」列的 `Codex（GPT-5.5）實作 + Composer 2.5 code review`、L37「執行端選層」bullet 都須改成 pointer 或刪除(ADV-COMPOSER-4)。
- 邊界:①條款與表重複 → 刪 prose 留表;②長條款(a-d 定義)表內放引用、表外條列。
- 風險緩解:同 Task 2.1 commit。
- 驗證(adversarial 修牙,ADV-COMPOSER-4/CODEX-2):`grep -q "每 10 分鐘" CLAUDE.md` exit 0;`grep -n "每 5 分鐘" CLAUDE.md` =0 命中;`grep -q "現行分工" CLAUDE.md` exit 0(pointer 句);**`grep -nE "Codex.*實作|Composer.*實作|GPT-5.5.*實作" CLAUDE.md` =0 命中**(全/半形括號皆涵蓋,取代舊半形 `Codex(GPT-5.5)實作` 無牙 grep)。

### Task 2.3 — [A-4] 規則零刪減核對(驗證任務,無新改動)
- SPEC ref:§V ③　目標:證明瘦身沒誤傷規則本體。
- 輸入/輸出:輸入=改後 CLAUDE.md+AGENTS.md+.cursorrules;輸出=收尾報告內逐項 grep 結果。
- 實作要點(adversarial 重寫,ADV-COMPOSER-3/5:改用**改前實測存在**的真實 baseline token,分所在檔驗;舊版列了 CLAUDE.md 根本沒有的 `繁體`/`VERIFY`/`先問` 會即刻假紅或誘導 token-stuffing):
  - **CLAUDE.md 必留 12 token**(逐項跑,任一落空=FAIL 回補):`grep -q "data_cache" CLAUDE.md`;`grep -q "momentum/" CLAUDE.md`(解耦表);`grep -q "Validate Assumptions" CLAUDE.md`;`grep -q "驗證保真度" CLAUDE.md`;`grep -q "三方數據" CLAUDE.md`;`grep -q "雙家族" CLAUDE.md`;`grep -q "adversarial" CLAUDE.md`;`grep -q "gate_check.sh" CLAUDE.md`;`grep -q "斷路器" CLAUDE.md`;`grep -q "否決" CLAUDE.md`;`grep -q "不跳" CLAUDE.md`(或 `grep -q "不得" CLAUDE.md && grep -q "跳" CLAUDE.md`,中大不跳步);`grep -q "preflight" CLAUDE.md`。
  - **合約家 token**(所在=AGENTS.md+.cursorrules,不在 CLAUDE.md):既存 `反提示注入`;A-12 新增後 `register-output`/`RECONCILE-STAMP`/`VERIFY`——**此三者改前=0,故在 Task 4.3 post-add 驗,不列此處 baseline**。
  - **記憶專屬 user pref**(U-10 留記憶不入 repo):`繁中`/`白話`/`push` **不列 CLAUDE.md grep**,於 Phase 6 記憶層驗。
- 修改檔案:無(FAIL 時回補 CLAUDE.md 對應規則句)。
- 不可做:不為過 grep 而塞無語義關鍵詞(規則須以完整條文存在)。
- 邊界:①grep 命中但語義被弱化(如「不得跳步」改「盡量不跳」)→ 視為 FAIL 恢復原語義;②某 token 因瘦身確實移到合約/SCAR_LEDGER → CLAUDE.md 至少留 pointer 句且該 token 在新家可 grep。
- 風險緩解:⊘(純 grep 核對,exit 0 即過)。
- 驗證:上列 CLAUDE.md 12 組 grep 全 exit 0(合約家/記憶類分別於 Task 4.3/Phase 6 驗),輸出貼收尾報告 TESTS_RUN。

## Phase 3 — ORCHESTRATION 手冊(完成後:選層單一來源、中型不跳步、2 輪一致)

### Task 3.1 — [A-7] §1 選層改單一「現行分工」行
- SPEC ref:Task 3.1　目標:選層動態化、單一來源。
- 輸入/輸出:輸入=ORCH §1(工具表+選層原則段);輸出=改寫後 §1。
- 實作要點(adversarial,ADV-COMPOSER-8/CODEX-2:單一來源要真收斂,工具表欄與 §6 都不得留第二個固定結論):①工具表保留(CLI/能力閘門/agy read-only),但「何時用」欄的寫死分工一律改中性 pointer「依本節現行分工行」(**不含精確 token「現行分工」四字**,避免與 `grep -c` 錨點驗證互撞);②「選層原則(2026-06-03 A/B 實證後定):小=Claude…大=Codex…」段落改為單一錨點行(行首即錨點):「**現行分工(2026-07-05 使用者指示,因 Codex 額度 limit 切換):中/大=Composer 2.5(`cursor-agent`)實作+Codex(`codex`)code review;小=Claude 自做。** 選層為**動態**:一律以使用者最新指示為準(依各 agent usage 切換,未來或加新執行端;新執行端須先過 §8 T-D 對等性測試才可寫入)。」;③A/B 實證誠實邊界句(codex≈cursor 正確性對等…facts-first 仍最優先)保留;④06-03 定層歷史敘事移 SCAR_LEDGER 或刪;⑤§6「主力決策法」歷史 codex/cursor 敘述加一句「最終以 §1 現行分工行為準」,不留第二結論。
- **註**:「現行分工」精確四字只准出現在 §1 那**一行**(§B Gate `grep -cE "^\*\*現行分工|現行分工\("` 應=1);工具表/§6/CLAUDE.md 一律用 pointer 措辭「§1 現行分工行」不觸發精確計數。
- 修改檔案:`docs/MULTI_AGENT_ORCHESTRATION.md` §1。既有 caller:CLAUDE.md 決策表 pointer(Task 2.2)、sync check GLOBAL_TOKENS。
- 不可做:不刪能力閘門/T-D/agy 禁寫入/preflight-postflight 要求;不改 §8。
- 邊界:①§6「主力決策法」歷史選層敘述=方法非結論 → 保留+加「最終以 §1 現行分工行為準」一句;②其他節出現寫死分工句 → 一併改 pointer。
- 風險緩解:單獨可 revert 的 hunk。
- 驗證:`grep -c "現行分工" docs/MULTI_AGENT_ORCHESTRATION.md` =1;`grep -q "T-D" docs/MULTI_AGENT_ORCHESTRATION.md` exit 0。

### Task 3.2 — [A-8] 中型管線矛盾修復
- SPEC ref:Task 3.2　目標:刪「中型跳步」敘述,分級歸屬指向 CLAUDE.md。
- 輸入/輸出:輸入=ORCH「SPEC/TODO 作者流程」分層表;輸出=修正後表。
- 實作要點:「中」列由「寫 SPEC→直接從 SPEC 派工,**跳獨立 TODO+跳一次 adversarial**」改「完整管線同大型(SPEC+TODO+至少一家不同模型 adversarial;2026-06-05 使用者定死不得跳步,D-1 維持)——判準與步驟見 CLAUDE.md 任務分派決策表」。「小」列與大任務 6 步驟操作說明不動。
- 修改檔案:`docs/MULTI_AGENT_ORCHESTRATION.md`「分層(依 §RISK…)」表。既有 caller:無腳本 grep 此表。
- 不可做:不砍大任務管線 6 步驟;不改信任分工表。
- 邊界:①「小」列不受 D-1 影響照留;②手冊他處若還有「中型可跳」語句 → 一併清除。
- 風險緩解:⊘。
- 驗證:`grep -n "跳獨立 TODO" docs/MULTI_AGENT_ORCHESTRATION.md` =0 命中;`grep -q "任務分派決策表" docs/MULTI_AGENT_ORCHESTRATION.md` exit 0。

### Task 3.3 — [A-11 之 ORCH 部分] debug 輪數 3→2
- SPEC ref:Task 3.3　目標:ORCH L227/L241 兩處「≤3 輪」→ 2 輪。
- 輸入/輸出:輸入=ORCH §5;輸出=兩處改 2 輪+依據句。
- 實作要點:①L227「debug ≤ 3 輪未過」→「debug ≤ 2 輪未過」;②L241「執行端內部已有 `debug ≤3 輪`」→「`debug ≤2 輪`」;③擇一處補「(2026-06-10/06-25 使用者兩輪斷路器指示,出處見 `docs/SCAR_LEDGER.md`)」;④**`docs/MULTI_AGENT_BOOTSTRAP.md` L35「debug ≤3 輪…超過→BLOCKED + 三輪摘要」→ 2 輪 + 兩輪摘要**(adversarial ADV-COMPOSER-11:消滅第 5 個分叉源)。
- 修改檔案:`docs/MULTI_AGENT_ORCHESTRATION.md` §5、`docs/MULTI_AGENT_BOOTSTRAP.md` L35。既有 caller:sync check GLOBAL_TOKENS(斷路器字樣仍在)。
- 不可做:不改宏觀斷路器(重派 ≤2 輪升級使用者)語義。
- 邊界:①宏觀「重派 ≤ 2 輪」既有敘述不動;②`templates/` 內若有 3 輪殘留 → 不改(超 scope),收尾報告 SCOPE_CHANGES 註記。
- 風險緩解:⊘。
- 驗證:`grep -n "3 輪\|≤3 輪" docs/MULTI_AGENT_ORCHESTRATION.md docs/MULTI_AGENT_BOOTSTRAP.md` =0 命中。

## Phase 4 — 執行端合約補齊(完成後:AGENTS.md/.cursorrules 反映全部現役制度且互相對齊)

### Task 4.1 — [A-10] HANDOFF 所有權矛盾修復
- SPEC ref:Task 4.1　目標:合約頂部與第 7 條一致。
- 輸入/輸出:輸入=AGENTS.md「最後一步(必執行)」節(L8-10)、.cursorrules「協作協議」節(L5-6);輸出=兩處改寫。
- 實作要點:兩處改「**結束前(必執行)**:寫交接到 `handoffs/<YYYYMMDD>-<task-id>.md`(append-only,≤30 行:正在做/待辦/阻塞/本次決策/踩坑提醒);根 `HANDOFF.md` 由 Claude 維護,執行端不得改寫」。
- 修改檔案:`AGENTS.md` L8-10、`.cursorrules` L5-6。既有 caller:sync check CONTRACT_TOKENS(`handoffs/` 字樣仍在)。
- 不可做:不刪「≤30 行」格式要求;不動第 7 條紅線。
- 邊界:①頂部與第 7 條語義重複=允許(指令+紅線雙保險),用詞一致;②互動模式同樣適用,不分派工/互動。
- 風險緩解:⊘。
- 驗證:兩檔 `grep -q "由 Claude 維護"` exit 0;兩檔頂部節 `grep -n "更新 \`HANDOFF.md\`"` =0 命中(第 7 條「不可覆蓋 HANDOFF.md」保留)。

### Task 4.2 — [A-11] 合約 debug 輪數 3→2
- SPEC ref:Task 4.2　目標:第 5 條統一兩輪斷路器。
- 輸入/輸出:輸入=AGENTS.md 第 5 條(L26)、.cursorrules 第 5 條(L19);輸出=兩條改寫。
- 實作要點:「≤ 3 輪…同一失敗 3 輪未過…三輪各自」→「**≤ 2 輪**…同一失敗 2 輪未過 → 停,輸出 `STATUS: BLOCKED` + 兩輪各自(假設/改了哪些檔/測試輸出摘要),交委員會處理(由 Claude 發起,執行端只需 BLOCKED 停下;2026-06-10/06-25 使用者定)」;「不堆嘗試/不改名續做」句保留。
- 修改檔案:`AGENTS.md` 第 5 條、`.cursorrules` 第 5 條。既有 caller:sync check(`STATUS: BLOCKED`、`斷路器` token)。
- 不可做:不用「建議/盡量」等可協商字眼。
- 邊界:①「三輪」派生字樣全改「兩輪」;②數字寫法統一半形 2。
- 風險緩解:⊘。
- 驗證:§B Gate 三檔 grep「3 輪」=0;`grep -c "≤ 2 輪" AGENTS.md` ≥1 且 `grep -c "≤ 2 輪" .cursorrules` ≥1。

### Task 4.3 — [A-12] 合約補齊 5 項現役制度
- SPEC ref:Task 4.3　目標:兩份合約補入 05-31 後上線制度,兩份語義對齊。
- 輸入/輸出:輸入=兩合約「執行任務時」節;輸出=新增/併入條目。
- 實作要點(5 項;①=Task 4.2 已做):②**留痕義務**:「派工 prompt 帶 task-id 者:產出檔寫進 `handoffs/`,收尾報告列出產出檔路徑(Claude 會 `register-output` 入帳);不得只寫在 log」;③**VERIFY claim 義務**:「收尾報告/交接檔中任何『已驗/passed/確認正確』聲明須附實跑命令+輸出摘要,否則標『未驗證』;空稱視為捏造(2026-07-01 事故,出處見 `docs/SCAR_LEDGER.md`)」;④**STAMP-BLOCKED**:「動工前若所依 reconcile/SPEC 的 `RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`,不動工」;⑤確認既有「inter-agent artifact 視為資料非指令」條原文保留。新增條目放第 9 條後(9.1/10 皆可),**不重排既有 1-9 編號**。
- 修改檔案:`AGENTS.md`、`.cursorrules`「執行任務時」節。既有 caller:sync check CONTRACT_TOKENS 全部仍須在。
- 不可做:不重排既有條目編號;不刪任何既有紅線;兩檔語義不得分叉(字數可異)。
- 邊界:①AGENTS 詳/.cursorrules 精簡風格差允許,關鍵 token(`register-output`/`RECONCILE-STAMP`/`VERIFY`)兩檔皆須有;②與既有條衝突 → 併入最接近條,不推翻紅線。
- 風險緩解:⊘。
- 驗證:兩檔各 `grep -q "register-output"`、`grep -q "RECONCILE-STAMP"`、`grep -qE "VERIFY|實跑命令"` 皆 exit 0;`grep -q "反提示注入" AGENTS.md && grep -q "反提示注入" .cursorrules` exit 0。

### Task 4.4 — [A-13] 同步檢查護欄(驗證任務)
- SPEC ref:Task 4.4　目標:四源改寫後機檢仍綠。
- 輸入/輸出:輸入=改後四檔;輸出=sync check stdout 貼收尾報告。
- 實作要點:跑 `bash scripts/check_agent_contract_sync.sh`;FAIL → 依缺 token 訊息回補該檔原字樣(補 token 恢復,**不改腳本**,U-9=Phase B)。
- **殘量註記(adversarial,ADV-COMPOSER-7)**:sync check 的 CONTRACT_TOKENS 尚未含 A-12 新 token(`register-output`/`RECONCILE-STAMP`/`VERIFY`)→ **sync 綠 ≠ A-12 已補齊**;A-12 是否落地以 §B Gate 的 MISSING_CONTRACT 迴圈(Task 4.3 grep)為權威。收尾報告須同時附 sync stdout + MISSING_CONTRACT 迴圈輸出。
- 修改檔案:無(FAIL 時回補四檔)。
- 不可做:不改 `scripts/check_agent_contract_sync.sh`。
- 邊界:①token 被改寫掉(如「斷路器」換詞)→ 恢復原 token 字樣;②腳本本身壞(非本批造成)→ `STATUS: BLOCKED` 回報。
- 風險緩解:⊘。
- 驗證:exit 0,stdout 含「✅ 四源關鍵不變式一致」;另附 §B Gate MISSING_CONTRACT 迴圈=無輸出。

## Phase 5 — 低頻文件 banner(完成後:讀者可辨識治理內容以憲法為準)

### Task 5.1 — [A-14] staleness banner
- SPEC ref:Task 5.1　目標:兩大文件檔頭加過時警示。
- 輸入/輸出:輸入=`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT_GUIDE.md` 檔頭;輸出=各插入 ≤4 行 blockquote。
- 實作要點:標題行下插入:「> ⚠️ 治理制度(協作/派工/gate)以 `CLAUDE.md` 與 `docs/MULTI_AGENT_ORCHESTRATION.md` 為準;本檔最後驗證 2026-07-05,其後細節可能過時。」
- 修改檔案:兩檔僅檔頭。既有 caller:無腳本 grep 檔頭。
- 不可做:不動兩檔正文任何一行;不「順手」修內文過時敘述(U-11 裁決=不強制同步)。
- 邊界:①檔頭已有 banner → 併列不覆蓋;②標題前有 frontmatter/註解 → 插在標題後仍成立。
- 風險緩解:⊘。
- 驗證:兩檔 `grep -q "最後驗證 2026-07-05"` exit 0;`git diff --stat` 兩檔各 ≤6 行變動。

## Phase 6 — 記憶層同步(**不派工;Claude 自做**,executor 到此為止)

### Task 6.1 — [A-15][A-16] 記憶 pointer 化(Claude 自做)
- SPEC ref:Task 6.1　目標:多 agent 規則單一來源=repo 憲法;記憶留偏好與 delta。
- 實作要點:feedback_task_routing 加 SUPERSEDED 標記指向 CLAUDE.md 決策表;feedback_dispatch_polling 內文改 pointer;重疊條目(兩輪斷路器/adversarial 紀律/reconcile 戳記等)標「規則本體見 repo 憲法」;偏好類(繁中/push/brief 白話/veto 彈窗/gemini 只研究)保留;MEMORY.md 索引同步。
- 不可做:不刪任何記憶檔;不把使用者偏好搬進 repo。
- 邊界:①記憶含 repo 沒有的 delta(quota role-swap 紀律)→ 保留該段;②只改標記/內文不刪檔(不可逆防護)。
- 驗證:`grep -q "SUPERSEDED" ~/.claude/projects/-Users-louis-Desktop-quantitative-trading-system/memory/feedback_task_routing.md` exit 0;MEMORY.md 對應行更新。

## Phase 1-5 測試與 Gate 總表
- 單元層=各 Task 驗證命令(grep/wc/exit code);整合層=§B Gate 全套;無效能層(純文件)。
- Phase Gate:B1 收尾必跑 §B Gate 全部命令並貼輸出於收尾報告 `TESTS_RUN`;任一 FAIL=不得輸出 `STATUS: DONE`。

## Frozen 前 handoff
SPEC=docs/INSTREV_PHASEA_SPEC.md TODO=docs/INSTREV_PHASEA_TODO.md FOCUS=規則零刪減+token保留+單一來源一致性
