# 驗收防偽閘 全硬化議事 — 最終 reconcile(餵 SPEC 大改)

**四方**:Claude(自產版)、Codex(PROCEED-WITH-CONSTRAINED-HARDENING)、Composer(APPROVED-WITH-CONDITIONS)、Gemini(read-only;見末節)。
**使用者決策**:全硬化。**委員共識**:全硬化**可執行**,但須「約束式硬化」——否則必撞牆變相繞過。

## 定案核心原則(Codex+Composer 一致)
> **語意分類器只當 router,不當法官。機器只判「宣稱的流程有沒有對應的 provenance 事件」;人判詮釋/邏輯品質。**
> **在 commit/交接邊界對『可機械驗證且低成本的 provenance』fail-closed;在 討論/引用/否定舊claim fail-open。**

## 定案設計(逐項,餵 SPEC v2)

1. **claim-object 偵測**(取代詞表+同段,兩家一致):normalize(NFKC+strip ZWSP+統一 dash/space/case)→段切分(markdown block/列表/表格格/commit subject 各自獨立)→每 claim-object `{polarity, scope(command/test/node/task/area), runtime_expectation(none|static|smoke|requires_kline|mutation|readonly_signoff), source_context(operational_result|root_handoff_status|commit_msg|docs_spec|discussion_quote|fenced_evidence), backing(receipt_id|task_id|stamp_id|supersedes|none)}`。**只擋** `operational` 新斷言且無有效 backing。**放行** citation(`REF:<id>` 指既存審計事件)/supersede(`SUPERSEDED:<id>`)/discussion。

2. **B-FORGE receipt 綁 append-only 審計事件**:`run_with_receipt.py` 產 receipt + audit event(emitter=run_with_receipt.py, command_sha, log_sha, git_head, started/ended);checker 要求三者互相吻合,手寫無事件→拒。**誠實邊界(Codex 糾正 Claude 太樂觀)**:receipt 與 audit 同一可寫主體 → 只能 **careless-proof + tamper-evident,非防惡意密碼學偽造**;文件須明標,不承諾不可偽造。

3. **B-HOOK 三層**:①**PreToolUse coarse-guard** 攔 Edit/Write `HANDOFF.md`+`handoffs/*` 中**新增/修改的 operational result 區塊**(不解析全檔歷史文字);②repo-tracked `core.hooksPath=scripts/git_hooks` 的 pre-commit+commit-msg(本地體驗);③**CI over changed files = 正式 enforcement**(`--no-verify` 繞不掉)。+ `verify_hooks_health.sh`(檢 jq/venv/python/checker 可用)入 preflight/CI;**CI 不可 fail-open**。

4. **B-CLASS runtime_class 推導**:由 argv/node-ids/markers/exit **推導**為 authoritative;CLI 傳入僅記 `requested_class`。pytest summary 解析失敗 → 對「需 node 範圍」的 claim **fail-closed**;一般 command 允許 unknown 但不得支撐 runtime/mutation/慢測/真跑 claim。

5. **B-EXEMPT 窄豁免**:兩種——`claim-context: discussion` **僅**作用於 fenced evidence/quoted block(不蓋整段任意文字);`VERIFY-EXEMPT:<category>:<issue-id>` 僅 `typo|doc-example|migration-note`(或 Composer 版 `template-drift|tooling-blocked|spec-ambiguity`,reconcile 取聯集後由實作收斂)。**HANDOFF.md operational status / commit / RESULT 段零豁免**。**分歧裁決**:討論豁免**以局部結構+極性為主判**(Codex),**檔名至多當弱訊號不可單獨免責**(否決 Composer 純檔名白名單——檔名會變新逃生口)。回歸測試須含「白名單檔內寫 operational 新 claim 仍應擋」。

6. **B-LEDGER 狀態機**:append-only JSONL + reducer;pending 需 `pending_id+claim_fingerprint+source_file/line+required_runtime_class+required_node_ids/markers+task_id`;close 必對 exact pending_id;提供 `list-open` 指令(否則被不明 pending 卡死);open/close 事件只接受 run_with_receipt.py 或認可的 RESULT parser 產生。

7. **B-SCOPE #7 RESULT 硬欄位(枚舉,非自然語言)**:`STATIC_CHECK|RUNTIME_CHECK|MUTATION_CHECK = NOT_RUN|PASS|FAIL|N/A:reason`、`RECEIPTS=[...]`、`OPEN_PENDING=[...]`。checker 讀結構欄不猜段落。

8. **B-SCOPE #6 v1 僅衝突檢查**:同 `claim_fingerprint` 出現 RED/FAIL 後,舊 VERIFY 綠 claim 未標 `SUPERSEDED` → checker 擋。**完整自動 render 索引 = phase 2**(先 linter report 不阻擋,避免改全員習慣 churn)。

## W1-W13 排序(四方收斂)
- **P0(與本事故同型,最先補)**:**W4**(驗收/測試 pass-fail 自述無 receipt=事故核心)、**W3**(adversarial 只查檔存在→綁 task-id+family+output-hash+audit event)、**W2**(reconcile 戳記可自 append→綁 task-id+audit+output-hash 機械對照)、**B-FORGE**。
- **P1(持久污染/防線空洞)**:**W1**(SPEC §A facts→資料結構/型別/命令輸出類事實附最便宜實測 transcript `FACT-RECEIPT`;純設計假設不得寫已確認)、B-CLASS、B-LEDGER、#7 RESULT、#6 衝突檢查、**W8**(MEMORY PASS/signoff 帶 provenance id;supersede 須顯示)、**W9**(執行端 RESULT 欄位須與 receipt pytest_summary 交叉,不符不得關 pending)。
- **P2(承認殘餘風險,靠人/review)**:**W6**(template 只抓空殼,保留 adversarial+reviewer 課責)、**W7**(audit.log 人稽核=刻意人為關卡,提供 `verify_audit_chain.py` 降抽查成本)、**W5**(snapshot id 寫進 dispatch token,postflight 驗 paired)。
- **新增**:**W10**(gate_check jq 缺→fail-open;verify health 須納 jq/venv/python,CI 不可 fail-open)、**W11**(Bash executor `env VAR=x codex` 形式可漏→靠 Task/CI/handoff checker 非只 Bash pattern)、**W12**(receipt/log 須與 claim 同 staged+hash 對上)、**W13**(commit subject/body claim 納 commit-msg hook+CI range checker)。

## 撞牆平衡點(四方一致)
真風險非抽象:誤報→EXEMPT 洗版 / `--no-verify` 常態化 / 同義詞軍備 / receipt 疲勞 / 寫到未掃描檔。對策:①只有 operational 新 claim 要 receipt,改待辦/阻塞/決策文字不觸發;②未知近似詞先 WARN 再升 FAIL;③CI 統計 exempt 率 WARN;④歷史先 WARN 報告人工漸進標 supersede,不要求全歷史零違規;⑤雙閘錯誤訊息分「派工門 gate_check」vs「驗收門 verify」。

## 硬性落地順序(Composer 條件,實作前提)
1. **先寫 claim-object 測試套件達誤報=0 門檻,才接 PreToolUse**;未達標則 v1 降為「commit-hook + CI + receipt」不上 PreToolUse 全攔。
2. 審計事件為 receipt 必要條件(B-FORGE)。3. CI 為 hook 後盾不可省。4. 豁免不得現於 HANDOFF/commit/RESULT。5. #6 v1 只衝突檢查。

## Gemini(read-only 第三視角;重試成功,與 Codex+Composer 完全收斂,無新分歧)
- ①三高點中 PreToolUse+討論豁免最易撞牆(關鍵字攔截會擋死合法引用/事故檢討);要訣「只抓無背書新斷言+快逃生口」;#6 先輕量過期/衝突檢查勿一次完整重構。
- ②偵測器不能無腦 grep;須辨識標記區塊(blockquote/fenced)視為討論放行;新斷言強制附機器生成 receipt ID;引用/否定用專用語法或關聯舊 ID。
- ③**W2/W3/W4 最致命(同型),最優先機器補強(綁 provenance 事件)**;W1 逐步導入出處驗證;W7/W5/W6 屬人為最後關卡,列可接受殘餘風險靠人抽查。
- ④平衡點:「只在信任攸關斷言上硬化(要求 provenance)」+接受殘餘風險;**過度把需綜合判斷的人為稽核全機器化=破壞平衡、導致繞過的主因**。

## 核可摘要
- Claude: 整合四方,分歧已裁決。
- Codex: DELIB VERDICT PROCEED-WITH-CONSTRAINED-HARDENING;SPEC v2.1 CONFIRM VERDICT APPROVED(`...-SPEC-V2_1-CONFIRM-CODEX.md`,task b1eicjnuo)。
- Composer: DELIB APPROVED-WITH-CONDITIONS;SPEC v2.1 CONFIRM VERDICT APPROVED(`...-SPEC-V2_1-CONFIRM-COMPOSER.md`,task bwhprlh0j)。

## 戳記
RECONCILE-STAMP: composer APPROVED 2026-07-01 sha256:86fe39f51ea28fadde135b0c0fd2f75feeb09b4adffaba8bbcde4fd590140044 task:bwhprlh0j
（委員各自 run `scripts/reconcile_body_hash.sh` 後 append:`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<id>`）
RECONCILE-STAMP: codex APPROVED 2026-07-01 sha256:86fe39f51ea28fadde135b0c0fd2f75feeb09b4adffaba8bbcde4fd590140044 task:b1eicjnuo
