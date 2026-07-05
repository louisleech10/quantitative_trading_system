# SPEC/TODO/Adversarial Template 審查 — Claude 獨立版

日期：2026-07-04　審查者：Claude (Fable 5)　範圍：`templates/SPEC_TEMPLATE.md`、`templates/TODO_GENERATION_PROMPT.md`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/RESULT_TEMPLATE.md` + 機檢 `scripts/template_check.sh`、`scripts/coverage_check.sh`

三個問題的總判：
1. **合適嗎** — 骨架合適。V13「緊湊+錨點綁 gate+照事故設計」方向正確，10 類必查與獵空殼分層誠實。但有數處 template↔機檢漂移與制度斷鏈（見 findings）。
2. **太繁雜/冗長嗎** — 整體不冗（V13 已是 V12 的蒸餾版，再砍會傷錨點）。真正 token 熱點只有兩處：TODO 階段 0 全讀 ARCHITECTURE(~1900 行)、SPEC 範本頭注隨每份 SPEC 複製。
3. **有無遺漏致品質疑慮** — 有。最大缺口：adversarial prompt 仍是「純讀文件」審查，沒把「實跑廉價反例」制度化——這正是 V2-timestamp 事故三道防線全破的根因，鐵律已定但 prompt 沒落地。

## Findings

**[C-1] MAJOR｜SPEC 範本未記載 FACT-RECEIPT 要求（template↔機檢漂移）**
證據：`template_check.sh` W1 段（§A「已確認」行含資料結構詞須同/鄰行附 `FACT-RECEIPT:`）；`SPEC_TEMPLATE.md` §A 全文無「FACT-RECEIPT」字樣。
失敗方式：作者照範本誠實填「已確認：raw_data.index 是 int64 epoch 秒」→ 機檢 FAIL 且範本沒教格式；更糟的適應是作者學會避開資料結構詞繞過檢查。
修法：§A 加一行格式說明+範例（`FACT-RECEIPT: python -c "..." → 印出 <輸出>`）。

**[C-2] MAJOR｜Adversarial prompt 未要求「實跑廉價反例」，仍是純文件審**
證據：prompt §0 問「作者驗證過嗎？」但全文無任何「reviewer 應 grep/讀檔/跑一行程式驗證 §A 宣稱」指令。對照 CLAUDE.md 驗證保真度鐵律與 feedback「adversarial 至少一腿要實跑反例」（B3 事故：確認式 review 全 PASS，Codex 自己跑反例才抓 6 LEAK）。
失敗方式：§A 寫假事實，reviewer 只能標「assumption?」信心 Medium → 被 reconcile 降級放行（= V2-timestamp adversarial #7 重演）。
修法：§0 加強制條款：「§A 已驗證事實凡可低成本核實（grep 碼庫/讀真實檔案/一行 python 對真資料）者，reviewer 必須實際執行並附輸出；無法執行則該事實列『未經覆核』且相關 finding 不得低於 MAJOR」。

**[C-3] MAJOR｜Finding 無穩定 ID 與可重跑閉合命令**
證據：輸出格式僅要求 `[BLOCKING|MAJOR|MINOR]+信心度+證據+失敗方式+修法`；無 finding ID、無「re-check 命令/反例」欄。對照章程 §B8 / feedback「Block 修後須原提出方重跑同一反例確認閉合」。
失敗方式：修補後「已修」口頭閉合，原反例沒人重跑（FF 驗收捏造事故的同型土壤）。
修法：每條 finding 加 `ID:` 與 `RECHECK:`（可執行命令或可 Ctrl+F 的具體檢查步驟），reconcile 逐 ID 追蹤。

**[C-4] MAJOR｜SPEC §V / TODO 未接 TEST_DESIGN_CHARTER（mutation/可證偽斷鏈）**
證據：`docs/TEST_DESIGN_CHARTER.md` 存在、RESULT_TEMPLATE 有 `MUTATION_CHECK` 欄；但 SPEC §V 與 TODO 範本均未要求「聲稱驗正確性的測試須證明改壞會 FAIL」或引用章程。
失敗方式：上游 SPEC 不設計 mutation 驗證，下游 RESULT 只能填 `MUTATION_CHECK=NOT_RUN`，而規則「NOT_RUN 不得宣稱 DONE」變成每次都卡或被 N/A 帶過。
修法：SPEC §V 加一行「正確性測試須附 mutation/可證偽設計（引用 TEST_DESIGN_CHARTER）」；TODO per-Task 驗證欄提示同項。

**[C-5] MAJOR｜RESULT 規則「RUNTIME_CHECK=PASS ⇒ RECEIPTS 非空」未被機檢**
證據：RESULT_TEMPLATE 規則節 vs `template_check.sh` result 分支（只驗欄位存在+枚舉值）。
失敗方式：`RUNTIME_CHECK=PASS` + `RECEIPTS=[]` 可過機檢 → 假 PASS 無收據仍綠。
修法：result 分支加 3 行交叉檢查（PASS 且 RECEIPTS=[] → FAIL）。屬 verify-receipt epic 範圍但此檢查成本極低可先行。

**[C-6] 建議（token）｜TODO 階段 0 無條件全讀 ARCHITECTURE(~1900行)+DEVELOPMENT_GUIDE**
證據：TODO prompt 階段 0「無條件讀」三檔。
影響：每次 TODO 生成固定燒數萬 token，而解耦 7 條/不可違反原則已由 copilot-instructions（小檔）+ SPEC §C 覆蓋。
修法：改「必讀 copilot-instructions；ARCHITECTURE/DEVELOPMENT_GUIDE 按 SPEC 觸及模組節選讀」。需委員會確認不會重開「沒讀憲法」事故面。

**[C-7] MINOR｜SPEC 範本 11 行頭注隨每份 SPEC 複製**——usage 加「複製後刪除本註解」。
**[C-8] MINOR｜adversarial prompt `{{STRICTNESS}}` 宣告未使用**（死變數，刪或接 severity 門檻）。
**[C-9] MINOR｜CLAUDE.md 錨點清單把 §G 寫成一律必填，template/機檢實為條件必填（§N N/A 可豁免）**——措辭對齊，避免 reviewer 誤判 BLOCKING。
**[C-10] MINOR｜§G 容差無 canonical 預設**（float32 放寬但無建議 atol/rtol）→ 各 SPEC 鬆緊不一；給預設值（超出須在 SPEC 說明理由）。
**[C-11] MINOR｜adversarial 無 RECONCILE-STAMP 交代**——reviewer 不知審後要 append stamp；可在 reconcile 派工另附，或 prompt 尾加一行。

## 明確不建議的方向
- 不建議為省 token 砍 10 類必查或階段 1 索引表（防漏核心，事故換來的）。
- 不建議把中型任務的 adversarial 降為抽查（違 2026-06-05 鐵律）。
