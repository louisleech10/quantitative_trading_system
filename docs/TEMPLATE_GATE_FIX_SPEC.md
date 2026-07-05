# TEMPLATE_GATE_FIX — 派工品質防線修補 SPEC

> 來源 PLAN/診斷：handoffs/2026-07-04-template-review-RECONCILE.md（四方委員會定案）＋ docs/TEMPLATE_GATE_FIX_MANIFEST.md　|　日期：2026-07-04　|　對應 TODO：docs/TEMPLATE_GATE_FIX_TODO.md（已生成）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（使用者 2026-07-04 核准為 epic）。
- **命中高風險原則**：(b) 跨模組/共用路徑——`template_check.sh`/`gate.sh` 是**所有派工與治理文件**的守門；(c) 多 phase（6 個）。不命中 (a)/(d)：不碰數值計算、特徵、ML、回測路徑。
- RISK-HIT: b,c
- 雖不命中 (a)/(d)，本 SPEC 自願填 §G（行為 golden＝fixture exit-code 矩陣），且 adversarial review 依大任務鐵律雙家族必跑。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（附驗證方式，共 4 條，每條有 FACT-RECEIPT）：
  - 治理文件殘留舊錨點共 7 處（gate.sh 2 處皆 §1.4、CLAUDE.md 1 處 §1.0、MULTI_AGENT_ORCHESTRATION.md 4 處＝§1.4×2＋§1.0×2；合計 §1.4×4、§1.0×3）。〔初版誤計 6 處，經 Composer adversarial ADV-P1 重跑同一命令抓出，2026-07-04 更正〕
    FACT-RECEIPT: `grep -n "§1.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md` → 印出 gate.sh:9,254；CLAUDE.md:41；MULTI_AGENT_ORCHESTRATION.md:69,101,212,308（Claude 實跑 2026-07-04）
  - 「待使用者確認：本任務無」不匹配現行 facts-resolved regex，會被誤擋。
    FACT-RECEIPT: `printf -- "- **待使用者確認**：本任務無\n" > /tmp/sec_a_test.txt; grep -qE "待[^：:]*確認[：:][[:space:]]*無|無[^。]*待[^：:]*確認|無待確認" /tmp/sec_a_test.txt` → 印出「regex NO MATCH(會被誤擋)」（Claude 實跑 2026-07-04）
  - Composer 委員會輪實跑之繞過探針（已驗證事實繞 FACT-RECEIPT／高風險 §G:N/A／TODO 末 Task 缺三欄）對現行 template_check.sh 均 exit 0＝PASS（不應）；facts-unresolved 探針正確 exit 1＝FAIL。〔探針全集以 [F-1]＝7 支繞過為準；委員會輪未跑的其餘支現狀 exit code 由 Phase 1 baseline 實測取得，不在此預斷〕
    FACT-RECEIPT: Composer 實跑 `template_check.sh` 對 /tmp/spec_verified_bypass.md、/tmp/spec_highrisk_no_g.md、/tmp/todo_bad.md、/tmp/spec_pending_unresolved.md → 印出 PASS/PASS/PASS/FAIL（檔載於 handoffs/2026-07-04-template-review-composer.md「機檢實跑摘要」表；Phase 1 將在 repo 內重建為 fixture 並重跑取得本地 receipt）。另現役 `docs/IC_PHASE0_SPEC.md`（`### 已驗證事實` 標題下 bullet 含 DatetimeIndex/int64 而行內無「已驗證」字面）同樣 exit 0＝繞過（Composer ADV-P2 實跑 2026-07-04）；Codex 亦造標題行變體探針證實行級關鍵詞修法不足（ADV-C1 實跑 2026-07-04）
  - 執行端（Codex/Cursor）憲法合約檔為 AGENTS.md/.cursorrules，非 .github/copilot-instructions.md；TODO 生成 prompt 現要求讀後者，存在分叉。
    FACT-RECEIPT: `ls .github/copilot-instructions.md docs/TEST_DESIGN_CHARTER.md docs/ARCHITECTURE.md docs/DEVELOPMENT_GUIDE.md` → 4 檔皆存在（Claude 實跑 2026-07-04）；合約來源見 CLAUDE.md「其他 agent：Codex 讀 AGENTS.md，Cursor 讀 .cursorrules」
- **待使用者確認**：無（修法方向與優先序四方 reconcile 已定案；使用者本日核准 epic 並要求嚴謹審慎）。待確認：無
- **已確認結果**：2026-07-04 使用者回覆「同意先做這個EPIC，這攸關每次任務的品質，所以你跟委員會要嚴謹審慎」→ 核准動工、走完整大任務管線。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條不受影響（本任務不碰 momentum/／api/ 程式碼）；不可違反原則之「不弱化防線」直接適用：**所有改動只加強機檢，不得放寬任何既有檢查**。
- 本任務特別注意的共用路徑：`scripts/template_check.sh`（gate.sh 與所有 SPEC/TODO freeze 呼叫）、`scripts/gate.sh`（PreToolUse hook 依賴其 token 流程）、`scripts/coverage_check.sh`、4 份 templates/、CLAUDE.md 與 MULTI_AGENT_ORCHESTRATION.md（多 agent 共讀）。**gate.sh 改動不得破壞現行 token 簽發流程，否則所有派工被鎖死**——每次改後must立即以本 SPEC 自身跑一次 gate 驗證可用。
- 下游消費者：Claude（開 gate）、Codex/Composer（讀範本寫 SPEC/TODO、adversarial）、使用者（稽核 audit.log）。

## §G Golden / Baseline（本任務為行為 golden：fixture exit-code 矩陣）
- **凍結時機 / reference 設定**：Phase 1 動工前，在 `tests/gate_fixtures/` 重建 Task 1.1 所列全部 14 fixture（7 繞過＋1 維持 FAIL＋5 正樣本＋R1 修正輪新增 1；見 result_done_after_discussion.md）＋收集 ≥3 份現役已 PASS 文件（docs/IC_PHASE1_1a_CUT1_SPEC.md 等）入 POSITIVE_SAMPLES.txt；以**現行** template_check.sh 跑全矩陣，輸出存 `tests/gate_fixtures/BASELINE_BEFORE.txt`（路徑寫死）。
- **baseline 內容**：每 fixture 一行 `<fixture>,<kind>,<exit_code_before>`；修後產 `AFTER` 同格式。
- **通過條件（可證偽）**：修後矩陣必須逐行等於預期：**[F-1] 所列全部 7 個繞過探針** exit 0→**1**（不得漏列任一——EXPECTED.txt 行數須等於 Task 1.1 的 14 fixture 數，含 R1 修正輪新增）；facts-unresolved 探針維持 1；誤擋反例 exit 1→**0**；全部正樣本維持 0（任何正樣本翻 1 = 誤擋回歸 = FAIL，需修 A 組觸發條件而非放行）。比對命令：`diff tests/gate_fixtures/EXPECTED.txt tests/gate_fixtures/AFTER.txt` → exit 0。

## §P Phase 與依賴（自檢：無 forward dependency；Phase 2-6 依賴 Phase 1 fixture；Phase 3 依賴 Phase 2 定稿的觸發規則；Phase 4 為 adversarial prompt 檔唯一改動點，Phase 5 僅改 TODO_GENERATION_PROMPT.md——同檔衝突已消解）

### Phase 1 — 探針固化與 baseline（依賴：無）
**Task 1.1 — [F-1][F-2] fixture 重建與正負樣本庫**
- 目標：把 Composer 探針、adversarial 新增探針、誤擋反例、合規正樣本固化為 repo 內永久 fixture。檔案：`tests/gate_fixtures/` 下 14 檔（R1 修正輪新增 result_done_after_discussion.md）——負樣本 7：`spec_verified_bypass.md`、`spec_heading_verified_bypass.md`（ADV-C1：標題行含「已驗證」、事實在下層 bullet）、`spec_ic_phase0_style.md`（ADV-P2：`### 已驗證事實` 標題＋bullet 無關鍵詞字面，同構現役 IC_PHASE0 樣式）、`spec_highrisk_no_g.md`（改用 `RISK-HIT: a,d` 宣告＋§N 標 §G N/A）、`todo_bad.md`、`result_pass_empty_receipts.md`（ADV-P5：RUNTIME_CHECK=PASS＋RECEIPTS=[]）、`result_notrun_done_operational.md`（MUTATION_CHECK=NOT_RUN＋discussion 區塊外 DONE 極性）；維持 FAIL 探針 1：`spec_pending_unresolved.md`；正樣本 5：`spec_good_full.md`（含 FACT-RECEIPT 行、RISK-HIT 宣告、真 §G、全錨點）、`todo_good_full.md`、`spec_pending_none_variant.md`（「待使用者確認：本任務無」措辭）、`spec_risk_false_positive.md`（ADV-P4：§RISK 含「參見 (a) 原則」「| (a) | 否 |」等干擾句＋`RISK-HIT: none`）、`result_notrun_done_in_discussion.md`（DONE 字樣僅在 `claim-context: discussion` 區塊內）。另附現役文件引用清單 `POSITIVE_SAMPLES.txt`。新建無 caller。
- 改法：依 handoffs/2026-07-04-template-review-composer.md「機檢實跑摘要」與兩份 adversarial（TGF-SPEC-ADV-codex/composer）內嵌探針原文重建。
- **驗證**：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_verified_bypass.md; echo $?` → 現行版印 0（重現繞過）；`ls tests/gate_fixtures/*.md | wc -l` == 14（含 R1 修正輪新增）。
- **邊界**：fixture 含 CRLF 或 BOM 時 grep 行為（統一 LF）；fixture 無「## §A」段時 W1 檢查整段跳過（sec_a 空）不誤炸。
- 不可做：不得修改 template_check.sh（本 Phase 只固化現狀證據）。

**Task 1.2 — [F-4] 一鍵驗證器 + [§G] baseline 凍結**
- 目標：`scripts/test_template_check.sh` 跑全 fixture 矩陣（支援 spec/todo/result 三 kind，kind 由檔名前綴判定）、輸出三欄 CSV、與 EXPECTED 比對。檔案：新建 `scripts/test_template_check.sh`、`tests/gate_fixtures/{EXPECTED.txt,BASELINE_BEFORE.txt,MUTATION.txt}`。新建無 caller。
- 改法：迴圈跑 `template_check.sh <kind> <fixture>` 收 exit code；`--freeze` 旗標寫 BASELINE_BEFORE.txt；預設模式 diff EXPECTED；MUTATION.txt 登記每條 A-* 規則的 mutation case（見 §V）。
- **驗證**：`bash scripts/test_template_check.sh --freeze && wc -l tests/gate_fixtures/BASELINE_BEFORE.txt` == 14 行（含 R1 修正輪新增）；EXPECTED.txt 依 §G 通過條件手填後 `bash scripts/test_template_check.sh; echo $?` 在修改前印 1（因繞過探針尚未被擋）——**此 1 是 Phase 2 的可證偽起點**。
- **邊界**：fixture 目錄空 → 明確 ERROR exit 2（非靜默 PASS）；單一 fixture 檔名含空格。
- 不可做：不得把 EXPECTED 寫成「跑當下結果」（那是恆真測試）。

### Phase 2 — 機檢硬化（依賴：Phase 1）
**Task 2.1 — [A-1][A-2] §A 觸發改段級狀態機與防標籤繞過**
- 目標：堵 U1（含 ADV-C1/ADV-P2 揭示的標題行與子 bullet 變體）。檔案：`scripts/template_check.sh` spec 分支 W1 段（`need`/awk 區塊，函式級）。既有 caller：gate.sh、手動呼叫。
- 改法：W1 從「行級關鍵詞」改為 **§A 段級狀態機**——awk 進入 §A 區塊後，偵測「已驗證事實」或「已確認」子段標題（`-`/`###`/`**` 任一格式）即進入 fact-scope，直到下一同級子段標題離開；fact-scope 內**任何**含資料結構詞（沿用現行 token 清單）的行，須同/鄰行 `FACT-RECEIPT:`，缺 → FAIL 並點名該行。facts-resolved 判定：「已確認」行須同時含日期樣式（`[0-9]{4}-[0-9]{2}-[0-9]{2}`）或「使用者」字樣，且該行含「待回覆|未確認|無法確認」→ 不算。
- **驗證**：`bash scripts/test_template_check.sh` 中 spec_verified_bypass、spec_heading_verified_bypass、spec_ic_phase0_style 三者 exit 均轉 1 且輸出點名缺 receipt 的 bullet 行，spec_good_full 維持 0；mutation：把 fact-scope 進入條件故意改壞一字元 → test_template_check.sh 轉紅（exit 非 0），改回轉綠。
- **邊界**：§A 無任何資料結構詞（純設計敘述）不觸發 FACT-RECEIPT；「已確認」出現在 §A 以外章節不觸發 facts-resolved 判定；fact-scope 內引用他檔的敘述行（含 `handoffs/`、`.md` 路徑而無型別斷言）不觸發。
- 不可做：不得要求非資料結構類事實也附 FACT-RECEIPT（過嚴誤擋）；不得動 result/todo 分支。

**Task 2.2 — [A-3] §RISK↔§G 聯動（結構化宣告制，棄 NLP 式 grep）**
- 目標：堵 U2，且不產生 ADV-P4 實測的誤擋面（「參見 (a) 原則」「| (a) | 否 |」等干擾句）。檔案：`scripts/template_check.sh` spec 分支 §G 檢查段。
- 改法：**機檢只認 §RISK 段內結構化宣告行 `RISK-HIT: <值>`**（值＝逗號分隔的 a/b/c/d 子集或 `none`）：① §RISK 段內無 `RISK-HIT:` 行 → FAIL（fail-closed，訊息指引補宣告；範本同步教學見 Task 3.1）；② 宣告含 `a` 或 `d` → 要求 `## §G` 存在、§G 段含 `atol|rtol|sha256` 任一 **數值 golden token**（`exit`/`==` 不算——ADV-C2：行為型 token 不得滿足 (a)/(d) 數值 golden），並拒絕 §N 內 `§G.*N/A` 豁免；③ 宣告不含 a/d → 維持現行 need_or 行為。散文敘述（命中/不命中字句）一律不參與機檢判定，只供人讀。誠實邊界：宣告可謊填 `none`——由 adversarial §2 新增必查（Task 4.1 [C-3]）與 gate 稽核兜底，機檢不做語義測謊。
- **驗證**：spec_highrisk_no_g（`RISK-HIT: a,d`＋§G N/A）exit 轉 1；spec_risk_false_positive（干擾句＋`RISK-HIT: none`）維持 0；spec_good_full（`RISK-HIT: b,c`＋自願 §G）維持 0；本 SPEC 自身（已補 `RISK-HIT: b,c`）`bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md` 維持 exit 0；mutation：把 `a` 的判定字元改壞 → 矩陣轉紅。
- **邊界**：`RISK-HIT:` 值含空白變體（`a, d`）；宣告行重複出現（取第一行並 WARN）；舊文件無宣告行 → FAIL 屬預期（GRANDFATHER 政策涵蓋，見 Task 6.2 [F-3]）。
- 不可做：不得對 b/c 宣告強制 §G；不得用散文關鍵詞推斷風險等級（誤擋面已被 ADV-P4 實證）。

**Task 2.3 — [A-4] TODO per-Task 分段檢查**
- 目標：堵 U3。檔案：`scripts/template_check.sh` todo 分支。
- 改法：awk 按 `^### Task` 切塊，每塊獨立 grep 驗證/邊界/不可做；缺欄輸出「Task 標題＋缺欄名」逐條列出。
- **驗證**：todo_bad（末 Task 缺三欄）exit 轉 1 且輸出含該 Task 標題；todo_good_full exit 0；mutation：把切塊 regex 改壞一字元 → 矩陣轉紅。
- **邊界**：`### Task` 零個時維持既有 `need "### Task"` FAIL；最末 Task 到 EOF 的塊邊界；Task 標題含特殊字元（`/`、`[]`）。
- 不可做：不得要求三欄以外欄位（實作要點等交 adversarial 語義層）。

**Task 2.4 — [A-5] RESULT 交叉規則 + [A-6] 待確認 regex**
- 目標：RESULT 假 PASS 堵洞＋誤擋修正。檔案：`scripts/template_check.sh` result 分支＋spec 分支 facts-resolved regex。
- 改法：result 分支加 RUNTIME_CHECK=PASS 且 `RECEIPTS=[]`（含空白變體）→ FAIL；MUTATION_CHECK=NOT_RUN 且 `claim-context: discussion` 標記區塊**之外**出現 `已驗|DONE|全綠` → FAIL。spec 分支 regex 增列 `待[^：:]*確認[^：:]*[：:].*[本此]?任務?無|確認[：:][[:space:]]*本任務無` 類誠實變體（以 fixture 驗收為準）。
- **驗證**：用 Phase 1 已固化的 3 個 result fixture——result_pass_empty_receipts exit 轉 1、result_notrun_done_operational exit 轉 1、result_notrun_done_in_discussion 維持 0；spec_pending_none_variant exit 轉 0；mutation：把 RECEIPTS 空判定改壞 → 矩陣轉紅。
- **邊界**：RECEIPTS=[" "]（含空白元素的偽非空）；DONE 出現在 RECHECK 命令引用中（豁免反引號 code span）。
- 不可做：不得解析 JSON 全語法（字串級檢查＋誠實邊界註明即可）。

### Phase 3 — SPEC 範本更新（依賴：Phase 2 定稿觸發規則）
**Task 3.1 — [B-1][B-2][B-5] §A 教學、RISK-HIT 宣告與頭注**
- 目標：範本教會機檢實際要求的格式。檔案：`templates/SPEC_TEMPLATE.md` §RISK＋§A 段＋頭部註解。
- 改法：§RISK 加 `RISK-HIT: <a,b,c,d 子集或 none>` 宣告行教學（機檢依據，Task 2.2 契約）；§A 加 FACT-RECEIPT 一行格式（`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`）＋範例；教「待確認：無」精確寫法與「已確認結果：YYYY-MM-DD 使用者…」結構；頭注末加「複製為 SPEC 後刪除本 HTML 註解」。
- **驗證**：`grep -c "FACT-RECEIPT" templates/SPEC_TEMPLATE.md` ≥ 2；`grep -c "RISK-HIT" templates/SPEC_TEMPLATE.md` ≥ 1；依新範本手填一份最小 SPEC 過 `template_check.sh spec` exit 0（用 spec_good_full 同步更新驗證）。
- **邊界**：範本自身（含雙大括號占位符）跑機檢仍預期 exit 1＝FAIL（樣板殘留檢查），不得為讓範本自身 PASS 而弱化檢查。
- 不可做：不得增加新必填 `## §` 錨點（§ 集合凍結；RISK-HIT 是 §RISK 段內欄位，非新錨點）。

**Task 3.2 — [B-3][B-4] §G 三方簽核子條款與 §V 章程掛鉤**
- 目標：制度鐵律下沉。檔案：`templates/SPEC_TEMPLATE.md` §G、§V 段。
- 改法：§G 加條件行「涉 feature/kline 生成/計算/merge/split/洩漏 → 真實 `data_cache/feature_klines/kline_cache.h5`＋三方簽核計畫必填，禁合成 fixture」；§V 加條件行「§RISK 命中 (a)/(d) 或測試宣稱驗正確性 → 附可證偽/mutation 設計（引 docs/TEST_DESIGN_CHARTER.md），否則 §N 標 mutation N/A＋理由」。
- **驗證**：`grep -c "kline_cache.h5" templates/SPEC_TEMPLATE.md` = 1；`grep -c "TEST_DESIGN_CHARTER" templates/SPEC_TEMPLATE.md` = 1；範本總行數增幅 ≤ 12 行（緊湊原則）。
- **邊界**：非 feature 任務讀到 §G 子條款時有明確「不適用即略過」措辭，不造成誤解為全任務強制。
- 不可做：不得把三方簽核寫成機檢錨點（它是流程義務，機檢層在 gate --review-role 已覆蓋）。

### Phase 4 — Adversarial prompt 更新（依賴：Phase 2 規則定稿；與 Phase 3 無互依；本 Phase 為 prompt 檔唯一改動點——E-3 併入，Phase 5 不再碰同檔（ADV-P8））
**Task 4.1 — [C-1][C-2][C-3][C-4][C-5][E-3] 實核義務、閉合欄位與 output 端守門**
- 目標：把「實跑反例」與「可對號銷帳」寫進 prompt；守門從 input 移到 output 端。檔案：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0、§2、輸出格式段（單一 commit 完成全部 prompt 改動）。
- 改法：§0 末插 Composer Q1 定稿條款（≤4 行，含 VERIFY: 附輸出、未經覆核 ≥MAJOR、不得 reconcile 降級）；輸出格式每 finding 加 `ID:`（**family-scoped：`ADV-CODEX-<n>`／`ADV-COMPOSER-<n>`，防雙家族撞號 ADV-C4**）與 `RECHECK:`；§2 加查三條——FACT-RECEIPT 落實、RISK-HIT 宣告 a/d ⇒ §G 非 N/A 且含數值 golden token、**[E-3]** TODO §0 是否含解耦 7 條＋不可違反原則之本任務相關子集（純前端/文檔任務可聲明不適用；缺 → MAJOR）；刪 STRICTNESS 死變數（雙大括號宣告整行）；§2 獵空殼加「含數字仍空殼」例示（『確認有 1 個檔案』）。
- **驗證**：`grep -c "RECHECK" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` ≥ 2；`grep -c "STRICTNESS" ...` = 0；`grep -c "VERIFY:" ...` ≥ 1；`grep -c "ADV-CODEX" ...` ≥ 1；`grep -cE "解耦" ...` ≥ 1；prompt 總行數 ≤ 78（緊湊原則，現 59）。
- **邊界**：read-only 委員（無 shell）路徑——條款須含優雅降級文字，不得使 agy 類委員無法履職；「相關子集」對純前端/文檔任務可為空但須明示聲明。
- 不可做：不得刪 10 類必查任何一類；不得改輸出 Verdict 三值枚舉（D-1 依賴）。

### Phase 5 — TODO 生成 prompt 瘦身（依賴：無；與 Phase 3/4 無互依）
**Task 5.1 — [E-1][E-2][E-4] 憲法來源置換與按需讀取**
- 目標：砍每次 5,100 行固定開銷、修合約分叉。檔案：`templates/TODO_GENERATION_PROMPT.md` 階段 0＋階段 2。
- 改法：階段 0 必讀改 `AGENTS.md`＋CLAUDE.md 指定三節＋SPEC §C；加按需觸發表（FeatureEngineering→ARCHITECTURE 對應章；API→DEVELOPMENT_GUIDE API 節；跨域/factory→兩檔對應節）；階段 2 §0 生成規則加「引用 SPEC §A 之 manifest ID，不整段複製」。
- **驗證**（全機械斷言，ADV-P10）：`grep -c "copilot-instructions" templates/TODO_GENERATION_PROMPT.md` = 0；`grep -c "AGENTS.md" ...` ≥ 1；`grep -n "無條件讀" templates/TODO_GENERATION_PROMPT.md` 輸出行內不得含 `ARCHITECTURE|DEVELOPMENT_GUIDE|copilot`（`grep "無條件讀" ... | grep -cE "ARCHITECTURE|DEVELOPMENT_GUIDE|copilot"` = 0）。
- **邊界**：SPEC 未列觸及模組時的 fallback（讀 AGENTS.md＋CLAUDE.md 三節即可，不得回退全讀）；AGENTS.md 未來改名/搬移的引用脆弱性（註明同步點）。
- 不可做：不得刪階段 1 覆蓋追溯、階段 3 自檢、深度紅線（不可砍清單）。

（原 Task 5.2 [E-3] 已併入 Task 4.1——ADV-P8 同檔雙向改衝突消解；Phase 5 不碰 SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md）

### Phase 6 — gate 閉合與治理文件（依賴：Phase 2（探針矩陣綠）；**可先行部分僅限 [D-3] 舊錨點 7 處替換；[F-3] 盤點必須在 Phase 2 之後（用新機檢掃）**）
**Task 6.1 — [D-1][D-2] gate adversarial 品質輕檢與 reconcile 對映義務**
- 目標：堵「空 findings 檔過門」＋閉合對號銷帳。檔案：`scripts/gate.sh`（參數解析段＋--adversarial 檢查段）。
- 改法：**CLI 契約定死（ADV-C3/ADV-P7）：gate.sh dispatch 新增 `--reconcile <path>` 參數**——① --adversarial 檔須含 `Verdict` 行，缺 → 拒發；② --adversarial 檔含 `[BLOCKING]` 或 `ID:` 格式 finding 時，`--reconcile` 必填且該檔須含每個 `ADV-(CODEX|COMPOSER)-<n>` 的 `→` 處置行，缺任一 → 拒發 token 並列出缺號（字串級，誠實邊界註明「語義真偽交人工＋二期」）；③ 無 `ID:` 的舊格式 adversarial 檔走現行行為（grandfather，以檔內有無 `ID:` 判別）。
- **驗證**：構造 5 個 gate fixture（路徑寫死 `tests/gate_fixtures/gate_no_verdict.md`／`gate_blocking_no_reconcile.md`／`gate_id_major_no_reconcile.md`（僅 MAJOR＋ID: 無 reconcile，驗「或」語義）／`gate_reconcile_missing_id.md`＋配套 reconcile／`gate_reconcile_complete.md`＋配套 reconcile）各跑 `GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --risk high --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md --adversarial <fixture> [--reconcile <fixture>] ...` → 預期 拒/拒/拒/拒/發（exit 1/1/1/1/0）；低風險 smoke（無 --adversarial）僅作 token 流程回歸，不作主驗收；**改後立即以本 SPEC 跑一次真 gate 確認 token 流程未破壞（§C 鎖死風險）**，exit 0。
- **邊界**：adversarial 檔為多委員多檔時逐檔檢（--adversarial 可重複或逗號分隔，實作擇一並寫死於 usage）；reconcile 檔內同一 ID 多處置行取全部（不誤判缺）；--reconcile 給了但 adversarial 檔無 BLOCKING 且無 ID: finding → 僅 WARN 不拒發。
- 不可做：不得實作語義級 reconcile 機檢（明確 scope-out 至二期）；不得動 token 簽發/時效邏輯。

**Task 6.2 — [D-3][D-4][D-5][F-3] 舊錨點替換、coverage 改名、RESULT 映射、現役盤點**
- 目標：文檔一致性＋誠實命名＋雙軌映射＋grandfather 清單。檔案：`scripts/gate.sh`（2 處 §1.4）、`CLAUDE.md`（1 處 §1.0）、`docs/MULTI_AGENT_ORCHESTRATION.md`（4 處＝§1.4×2＋§1.0×2）、`scripts/coverage_check.sh` 輸出字串、`templates/RESULT_TEMPLATE.md`（映射一行）、新建 `docs/TEMPLATE_GATE_FIX_GRANDFATHER.md`。
- 改法：**全部 7 處**（含歷史紀錄語境）改寫為不含 `§1.0`/`§1.4` 字面的表述（如「V12 舊『可測性準則』章，今 §V」——ADV-P3 消解：驗收=0 與歷史語境不再互斥，歷史語意用文字保留、字面移除）；coverage 輸出 `COVERAGE PASS/FAIL` → `ID PRESENCE PASS/FAIL`（同步更新呼叫方對此字串的 grep，若有）；**[D-5]** RESULT_TEMPLATE 規則節加一行映射「執行端合約之 `TESTS_RUN` 項目應可對應 `RECEIPTS` 元素（收窄版 C-6，全域統一列二期）」；用新 template_check 掃 docs/ 現役 SPEC/TODO（**明列 docs/IC_PHASE0_SPEC.md，ADV-P9**），產出將 FAIL 清單＋政策聲明（僅新文件適用，不回頭追殺）。
- **驗證**：`grep -c "§1\.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md` 每檔輸出 0（合計 0，基準=修前 7 行）；`grep -rn "COVERAGE PASS" scripts/ --include="*.sh"` = 0 行；`grep -c "TESTS_RUN" templates/RESULT_TEMPLATE.md` ≥ 1；GRANDFATHER 檔存在且含 docs/IC_PHASE0_SPEC.md 掃描結果。
- **邊界**：歷史紀錄行（MULTI_AGENT_ORCHESTRATION.md T-C 節）改寫須保留原意（舊章節名以文字描述，不留可 grep 的舊錨點字面）；audit.log 不動。
- 不可做：不得修改 .claude/gate/audit.log（append-only 稽核檔）。

## §V 驗證策略與邊界測試目錄
- 測試層級：fixture 矩陣（`scripts/test_template_check.sh`，單元級）／gate 端到端（真跑 gate.sh 三 fixture，整合級）／§G 行為 golden 對照（BEFORE/EXPECTED/AFTER diff）。全部可獨立 shell 跑，不需 run_api.py，pytest 不涉及。
- **防假綠**：EXPECTED.txt 由 §G 通過條件先驗手填（非跑後回填）；探針「修前 PASS、修後 FAIL」雙向都驗；不得放寬既有任何 need/hollow 檢查。
- **可證偽/mutation 設計（依 docs/TEST_DESIGN_CHARTER.md；ADV-P6 全規則覆蓋）**：本 SPEC 的正確性宣稱=「機檢擋得住探針」，其 oracle=fixture 預期 exit code 先驗矩陣；**mutation 覆蓋每條 A-* 規則**（A-1 fact-scope、A-3 RISK-HIT 判定、A-4 per-Task 切塊、A-5 RECEIPTS 空判定——各規則「故意改壞一字元 → 矩陣必轉紅」，case 登記於 tests/gate_fixtures/MUTATION.txt，分別列入 Task 2.1/2.2/2.3/2.4 驗收）。
- **邊界目錄**（適用者）：空 fixture 目錄（exit 2）／§A 段缺失（W1 跳過不炸）／`### Task` 零個／否定句「不命中(a)」不誤觸發／CRLF-BOM／DONE 字樣在 code span 內豁免／多委員多 adversarial 檔。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert；Phase 2/6 各 commit 後立即真跑一次 gate 流程驗證未鎖死（破壞 → 立即 revert 該 commit）；機檢從嚴僅影響新文件（GRANDFATHER 政策檔明載），無資料/程式行為變更，無需 feature flag。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- 數值型 §G（mean/std/value hash/NaN mask）：N/A — 本任務不碰數值/特徵/ML 路徑（§RISK 不命中 (a)/(d)）；§G 以行為 golden（fixture exit-code 矩陣）替代，通過條件同樣可證偽。
- feature flag 回退：N/A — 改動對象為治理文件與 shell 檢查，逐 Phase revert 即回退，flag 反增複雜度。
