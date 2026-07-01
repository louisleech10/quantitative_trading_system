<!-- claim-context: discussion -->
# VERIFY_GATE 全硬化治理審議 — Codex(GPT-5.5)

VERDICT: PROCEED-WITH-CONSTRAINED-HARDENING — 全硬化方向成立，但不得把文字 claim 偵測器設計成總閘；v1 先補 provenance 事件、runtime receipt、reconcile/task-id 佐證、pending ledger、RESULT 欄位，#6 根 HANDOFF 自動索引降為 phase 2，v1 僅做 supersede/衝突檢查。

## 讀碼依據
- 已讀：`handoffs/20260701-VERIFYGATE-BALANCE-AND-WORKFLOW-CLAUDE.md`、`handoffs/20260701-VERIFYGATE-SPEC-ADV-RECONCILE.md`、`docs/VERIFY_GATE_SPEC.md`。
- 已讀：`scripts/gate.sh`、`scripts/gate_check.sh`、`scripts/reconcile_stamps_check.sh`。
- 關鍵觀察：現有 gate 明確只守「有無走通道/檔案存在/模板形狀」，不驗證內容為真；reconcile stamp 腳本明確承認戳記只是 tamper-evident，仍可被有寫權的編排者偽造。

## ① 全硬化逐項評估

| 項目 | 判斷 | 挑戰 Claude 版 | 建議設計 |
|---|---|---|---|
| B-FORGE receipt 綁 append-only audit event | 必做 | Claude 說風險低，但低估了「誰能寫 audit.log」問題；若 receipt 與 audit 都由同一可寫主體產生，只是提高偽造成本，不是消除偽造。 | v1 足夠採用 `run_with_receipt.py` 產 receipt + audit event + log hash + git head；checker 要求三者互相吻合。不要承諾不可偽造，只承諾 careless-proof + tamper-evident。 |
| B-HOOK PreToolUse 攔 Edit/Write HANDOFF/handoffs | 必做但限縮 | Claude 正確指出這是最大撞牆點；但「只擋新 claim」如果做成純 regex，一定誤擋 forensics 與設計文。 | PreToolUse 只做快速 coarse guard：新增/修改 operational 檔案中的 operational result blocks 才 fail-closed；複雜語意交給 pre-commit/CI checker。Edit hook 不應解析整份 markdown 的所有歷史文字。 |
| git hook + CI + health | 必做 | Claude 版把它列在 B-HOOK 內，但要分層：local hook 是體驗，CI 是底線，health 是告警。 | repo-tracked `scripts/git_hooks` + install script + CI over changed files。`--no-verify` 可繞 local hook，因此 CI 才是正式 enforcement。 |
| B-CLASS runtime_class 推導 | 必做 | 無異議，但推導規則要避免過度耦合 pytest 文字格式。 | authoritative class 由 argv/node id/markers/exit code 推導；pytest summary parse 失敗時，對需要 node 範圍的 claim fail-closed，對一般 command receipt 允許 unknown 但不得支撐慢測/真 run claim。 |
| B-EXEMPT 窄豁免 | 必做但要少用 | Claude 對 discussion 豁免的擔心合理；但「forensic 白名單檔名」太容易成為新逃生口。 | 豁免分兩種：`claim-context: discussion` 只讓 fenced evidence/quoted blocks 不觸發；`VERIFY-EXEMPT:<category>:<issue-id>` 只允許 typo/doc-example/migration-note，不允許 RESULT/HANDOFF operational status。 |
| B-LEDGER 狀態機 | 必做 | Claude 說低風險，低估 race/陳舊 pending 的治理負擔。 | append-only JSONL reducer；pending 需 fingerprint + source line + required runtime class + task id；close 必須 exact pending_id。提供 `list-open` 指令，否則日常會被不明 pending 卡死。 |
| B-SCOPE #7 RESULT 硬欄位 | 必做 | 同意，但欄位名稱不能靠自然語言。 | RESULT template 用枚舉：`STATIC_CHECK=NOT_RUN|PASS|FAIL|N/A:reason`、`RUNTIME_CHECK=...`、`MUTATION_CHECK=...`、`RECEIPTS=[...]`、`OPEN_PENDING=[...]`。checker 讀結構欄，不猜段落。 |
| B-SCOPE #6 根 HANDOFF 生成索引 | v1 不做完整自動生成 | Claude 說「最可能過頭」正確，但仍偏保守地想做索引。完整 render 會改變所有 agent 的習慣，churn 太高。 | v1 只做：舊 green claim 被 later red/superseded 後，不得在根 HANDOFF 同 scope 保持未標 superseded。完整生成索引 phase 2，先用 linter report 不阻擋。 |

### 三個高撞牆點的具體邊界

1. PreToolUse Edit 偵測精度：只阻擋新增或修改的「操作狀態區」內出現未 backing 的驗收結論。不要掃全檔歷史，不要把設計討論、反例測試、引用區塊當 operational claim。
2. discussion 豁免：豁免不應是「整段任意文字免責」。只豁免 fenced block、blockquote、明確標註的 evidence excerpt、以及 `Forensic quote:` 下的原文引用。引用後作者自己的結論仍要按 claim 規則檢查。
3. #6 churn：先做衝突檢查，不做自動重寫。日常卡點會來自 stale root HANDOFF；解法是報告「哪一行與哪個 later supersede 衝突」，不是直接替 agent 重排索引。

## ② claim 偵測器高精度低誤報判準

我不同意 Claude 版把重點放在「高精度 regex」的語氣。高精度應來自結構化 claim object，而不是更多同義詞。

### claim object 最小欄位
- `polarity`: success / failure / supersede / pending / discussion
- `scope`: command、test file、node id、task id、feature area
- `runtime_expectation`: none / static / smoke / requires_kline / mutation / readonly_signoff
- `source_context`: operational_result / root_handoff_status / commit_msg / docs_spec / discussion_quote / fenced_evidence
- `backing`: receipt_id / task_id / stamp_id / supersedes_line / none

### 應阻擋的新無 backing 斷言
- 在 RESULT/HANDOFF/commit message 內宣稱某測試、慢測、mutation、B2/B3、signoff、code review、adversarial review 已完成，且沒有 receipt/task event/stamp 佐證。
- 將 static/smoke receipt 用來支撐 runtime、mutation、requires_kline、真實路徑語意。
- 同一段有多個 scope claim，只附一個 receipt；receipt node ids/markers 只覆蓋其中一個時，其餘仍違規。
- pending ledger 尚未 close，卻出現 DONE/complete/ready-to-ship 類結論。

### 應放行的引用、supersede、討論
- 引用舊錯誤 claim，且同段或相鄰結構標明 `superseded_by` / `contradicted_by` / `forensic quote`，極性是「此 claim 不可信」。
- 設計討論中的反例，例如「若有人寫 X，checker 應擋」，且位於 fenced code、blockquote、或 `claim-context: discussion` 區塊。
- readonly signoff：讀碼結論可用 task event + reviewer output hash 背書，不要求 runtime receipt；但不得用 readonly signoff 支撐「慢測跑過」。
- N/A 或 NOT_RUN：這不是驗收完成 claim，應保留為 pending 或 residual risk。

### Unicode / 同義詞策略
- Normalize：NFKC、移除 zero-width、統一 dash/space/case。
- 詞表分級：強 claim 詞直接掃；弱詞如 `passed`、`通過` 只有在 operational result/commit/HANDOFF status 語境觸發。
- 未知近似詞先 WARN 再收斂，不要 v1 就 fail-closed；否則日常文件會被文字遊戲卡住。

## ③ W1-W9 排序與補充

### P0：先補，與本事故同型且高收益
1. W4 驗收/測試 pass-fail 自述無 receipt：本事故核心。先做 `run_with_receipt.py`、claim checker、RESULT 欄位、mutation script 接 receipt。
2. W3 adversarial review 只查檔案存在：必須綁 task-id、agent family、output hash、gate audit event；否則 Claude 自寫 review 檔仍可過。
3. W2 reconcile stamp 可自 append：現有 hash 只防改內容，不防自寫。v1 至少要求 stamp 的 `task:<id>` 對應 audit event + output file hash；checker 可做機械對照，使用者仍可抽查。
4. W1 SPEC §A facts 可捏造：加 `FACT-RECEIPT`/`READ-RECEIPT` 欄位。資料結構/型別/命令輸出類事實必須附最便宜的實測 transcript；純設計假設不得寫成已確認。

### P1：次補，會造成持久污染或防線空洞
5. W8 MEMORY.md 持久污染：任何 PASS/signoff 記憶都要帶 provenance id；若 later supersede，記憶索引必須顯示 superseded，不可只留綠結論。
6. W9 執行端 RESULT 欄位造假：要求執行端提供 receipts/task event，Claude 接回時只信 receipt-backed 欄位。對小任務可人工抽查，不必每次重跑。
7. W5 preflight/postflight 非全 dispatch 強制：把 snapshot id 寫進 dispatch token；postflight 驗 token 是否有 paired snapshot。這是資料安全底線，但與本事故間接相關。

### P2：承認殘餘風險，先靠 review/人
8. W6 template/coverage 只能抓空殼：不要試圖把「邏輯合理」完全機器化。保留 adversarial review + reviewer accountability。
9. W7 audit.log 需人稽核：這是刻意的人為關卡，不應完全消除。可提供 `verify_audit_chain.py` 降低抽查成本。

### 補充漏洞
- W10 hook fail-open on missing `jq`：`gate_check.sh` 目前 `jq` 缺失直接 exit 0。這對既有 gate 可理解為避免鎖死，但 verify gate health 必須把 jq/venv/python/checker 可用性納入 preflight/CI；CI 不可 fail-open。
- W11 Bash executor pattern 可漏 `env VAR=x codex` 等形式：現有註解已承認。verify hardening 不應只靠 Bash pattern；Task/CI/handoff checker 才是底線。
- W12 receipt/log 未 staged 或被後續修改：SPEC reconcile 已提到。checker 要求 receipt/log 與被提交 claim 同 staged，且 hash 對上。
- W13 commit message claim：本事故類型不只在 handoff；commit subject/body 也可寫過度驗收。commit-msg hook + CI commit range checker 必須納入。

## ④ 治理過重被繞過的真風險與平衡點

真風險存在，而且不是抽象問題。若每次寫事故分析都被攔、每次更新 HANDOFF 都要補 receipt、pending 不知道怎麼關，agent 會自然形成三種繞法：濫用 EXEMPT、改用模糊語言避免觸發、把狀態寫到未掃描檔案。這會讓治理看似更硬，實際更不可稽核。

平衡點：
- Fail-closed 只用在「可機械驗證且代價低」的 provenance：receipt、task id、hash、runtime class、pending close。
- 語意分類器只當 router，不當法官；法官是 receipt/task/stamp/ledger 是否對得上。
- 豁免要少但可用；每個豁免必須有 category + issue/review id，並進 audit report。沒有快速合法出口，就會產生非法出口。
- v1 用「阻擋新無 backing 的 operational claim」而不是「重審所有歷史文字」。歷史污染用 supersede conflict checker 漸進清理。
- 人的 review 保留在高層邏輯：SPEC 是否合理、測試是否有牙齒、資料正確性是否真的被覆蓋。機器不要假裝能判斷這些。

## 對 Claude 自產版的主要挑戰
1. 「B-FORGE 風險低」過於樂觀。若 audit event 與 receipt 都由同一可寫主體產生，它只能防疏忽與低成本偽造，不能防惡意偽造；文件要誠實標界線。
2. 「discussion/forensic 白名單」不應靠檔名。檔名白名單會變成新繞道；應靠局部結構和極性分類。
3. W2/W3 不只是「高可偽」，而是和本事故同一信任階梯：Claude 自產文字被下一步當成外部事實。優先級應高於 #6 根 HANDOFF 自動索引。
4. #6 完整自動索引 v1 過頭。先做 stale/supersede conflict checker，等 claim object 和 ledger 穩定後再 render index。
5. Claude 版漏掉 CI fail-open/health 的硬要求。local hook 可繞，PreToolUse 只管 Claude 通道；CI 才是 repo 邊界。

## 建議落地順序
1. 修 SPEC：納入 B-FORGE/B-HOOK/B-CLASS/B-EXEMPT/B-LEDGER/B-SCOPE 的收斂 BLOCK；明確 v1 不做完整 #6 render。
2. 實作 P1-P4：receipt wrapper、claim checker、ledger、hooks/CI、mutation script receipt 副作用。
3. 加反例測試：偽 receipt、helper smoke 冒充 runtime、多 claim 一 receipt、discussion quote 放行、RESULT/HANDOFF 豁免禁用、unicode 變體、missing jq/health。
4. 將 W2/W3 provenance 納入 gate：adversarial/reconcile 必須能對到 task id + output hash + audit event。
5. 先以 WARN report 掃歷史 handoffs，人工標 supersede；不要一開始要求全歷史零違規。

ASSUMPTIONS_VERIFIED: 已讀指定三份治理文件與三個腳本；本審議基於現有腳本註解與邏輯，不聲稱有執行治理測試。
TESTS_RUN: `sed`/`ls`/`git status --short` 讀碼與工作區檢查；未跑 pytest，因任務是治理設計審議且未改 production code。
FAILURES_SEEN: none
SCOPE_CHANGES: 新增 `handoffs/20260701-VERIFYGATE-DELIB-CODEX.md`；未修改既有治理腳本、docs、root HANDOFF。
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: DONE
