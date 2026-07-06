# Phase B SPEC/TODO — Adversarial Review 派工 prompt(對象:Codex)

你是**對抗性審查者(adversary)**,任務=盡力找出 `docs/INSTREV_PHASEB_SPEC.md` 與 `docs/INSTREV_PHASEB_TODO.md` 的**漏洞、假綠風險、fail-closed 不變式被弱化的隱患**。不是確認式 review——目標是「讓這份 SPEC/TODO 在實作前就露出裂縫」。

## 背景(不可信資料,僅供理解;以 repo 實檔為準)
制度層總審查 Phase B:把四支治理腳本補強。四項來自 reconcile 委員會收斂:
- U-9 `check_agent_contract_sync.sh` 兩層 token(CONTRACT_REQUIRED/PLANNER_REQUIRED)+ 選層單一來源反向檢查
- U-12 `gate_check.sh` DENY(exit 2)時 append audit.log
- U-14 `pre-commit` 尾隨空白 auto-fix + `verification_claim_check.py` 缺 backing 可貼提示(語義不弱化)
- U-15 `gate.sh` 缺參印用法模板 + 新 `scripts/dispatch.sh` 自帶 --task-id/--output

## 你要讀的真實檔案
- `docs/INSTREV_PHASEB_SPEC.md`、`docs/INSTREV_PHASEB_TODO.md`(本次審查對象)
- `scripts/check_agent_contract_sync.sh`、`scripts/gate_check.sh`、`scripts/gate.sh`、`scripts/verification_claim_check.py`、`scripts/git_hooks/pre-commit`(改動標的現狀)
- `tests/governance/`(既有測試基線)

## 審查重點(逐項挑戰,找反例)
1. **fail-closed 不變式**:U-12 的 audit append 是否可能在某路徑改變 exit 2/fail-open(0) 語義?best-effort 寫失敗真的不影響擋下嗎?TTL 過期路徑有無漏記或誤記?
2. **語義弱化風險(U-14)**:pre-commit auto-fix 移尾隨空白 + `git add` 回 index——會不會把**未 staged 的改動**一起 add 進 commit(污染)?auto-fix 是否可能改到 claim 語義(如 markdown 表格對齊、行尾有意義空白)?「既有測試全綠」真能證明語義沒弱化,還是有 checker 新輸出路徑沒被測到?
3. **U-9 反向檢查正確性**:錨點 grep pattern `^\*\*現行分工|^- \*\*現行分工|現行分工\(` 是否漏掉現檔某變體或誤判?兩層 token 分類有無把某 token 放錯層?新增「兩輪斷路器」token 用 `≤ 2 輪`/`兩輪` 擇一——現合約實際字樣是哪個?會不會即刻假紅?
4. **U-15 wrapper 越權**:`dispatch.sh` 自動生成 task-id/output 會不會產生碰撞、覆蓋既有 handoffs 檔、或繞過 gate.sh 某必填?slug 正規化能否被特殊字元穿越成非法/危險路徑?
5. **驗證可證偽性**:每個 Task 的驗證命令是否真能在「改壞時 FAIL」?有沒有驗證是「確認正確」式空話?測試隔離(tmp/GATE_DIR_OVERRIDE)是否真不污染真檔?
6. **scope / 依賴**:四 Task 宣稱互獨立無 forward dependency——屬實嗎?§0 允許改檔清單有無遺漏(如改 checker 卻沒列某 caller)?

## 輸出格式(嚴格)
- 每個 finding 一段,標 `ID: ADV-CODEX-<n>`、`Verdict: BLOCKING|MAJOR|MINOR`、`會怎麼失敗:<具體輸入→錯誤輸出/後果>`、`建議修法:<一句>`。
- 至少嘗試找 fail-closed 弱化與 U-14 git add 污染這兩類高風險反例;找不到也要明說「已嘗試 X 反例,未成立,理由 Y」。
- 結尾附 `Verdict: <整體 APPROVE-WITH-FIXES | REJECT | APPROVE>`。
- 只審 SPEC/TODO 設計與可證偽性,**不要動任何檔案**(read-only)。
