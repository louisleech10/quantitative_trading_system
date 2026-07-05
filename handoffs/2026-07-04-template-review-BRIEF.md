# 委員會任務 BRIEF — SPEC/TODO/Adversarial Template 審查（2026-07-04）

你是多模型委員會的一名獨立審查委員。本專案（量化交易系統）用一套 template/prompt 管治「SPEC 撰寫 → TODO 生成 → adversarial review → 執行端收尾回報」的多 agent 派工管線，並用 shell 機檢腳本在派工 gate 強制錨點。你的任務：**對這套管治文件本身**做全面獨立審查。

## 必讀檔案（全部都要讀完，不得分角度只看一部分）
1. `templates/SPEC_TEMPLATE.md` — SPEC 範本 V13
2. `templates/TODO_GENERATION_PROMPT.md` — TODO 生成 prompt V13
3. `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — adversarial review prompt V13
4. `templates/RESULT_TEMPLATE.md` — 執行端收尾結構化回報
5. `scripts/template_check.sh` — 錨點+反空殼機檢（gate 呼叫）
6. `scripts/coverage_check.sh` — manifest ID 覆蓋機檢
7. `CLAUDE.md` 的「Multi-Agent 協作協議」「驗證保真度鐵律」「三方數據正確性簽核鐵律」節 — 制度背景

## 回答三個問題
1. **合適性**：現在的內容合適嗎？結構、必填欄、失敗模式覆蓋是否對？
2. **冗長度**：是否太繁雜或冗長、浪費 token？哪些是真熱點、哪些不可砍？
3. **遺漏/瑕疵**：有無遺漏或缺陷會讓產出（SPEC/TODO/review findings/驗收）有品質疑慮？

## 審查要求
- **挑戰前提**：不只在文件框好的題目內找碴。質疑整套設計：錨點機檢+adversarial 分層是否真擋得住它聲稱要擋的事故？有沒有整類風險完全沒被覆蓋？
- **查 template↔機檢漂移**：範本教的寫法與 `template_check.sh` 實際 grep 的規則是否一致？照範本填會不會反而 FAIL 機檢？機檢聲稱的規則是否真的有檢查？
- **token 經濟**：指出實際運行中每次都要付的 token 成本（如生成時必讀的大檔、隨文件複製的內容），並區分「值得付」與「可省」。
- 每條 finding 格式：`[ID] [BLOCKING|MAJOR|MINOR|SUGGESTION] 標題`＋證據（檔名+可搜尋原文短句）＋會怎麼失敗＋修法。無證據的推測標 SUGGESTION。
- 另列「明確不建議改的地方」（防止為省 token 砍掉事故換來的防線）。
- **獨立性**：不得讀 `handoffs/2026-07-04-template-review-*.md` 其他委員的產出（BRIEF 除外）。
- 若卡住或需人決策：輸出 `STATUS: BLOCKED — <問題>` 停下，不要硬猜。

## 產出
把完整 findings 寫入指定給你的 handoff 檔（派工 prompt 會給路徑；read-only 委員直接輸出到 stdout）。文末必附 `STATUS: DONE`。
