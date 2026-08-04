# GOVB0-RECON R1 — grok 偵察報告（B-24／B-15／B-14）

family: grok | task-id: `GOVB0-RECON-R1` | brief: `handoffs/20260804-GOVB0-RECON-BRIEF.md`  
scope: 事實查證與修法方案實測；**禁改碼**（僅隔離副本探針）

---

## Verdict：可派工（主委可起草 SPEC；下列 P0/P1 須寫進 SPEC 前提，不得沿用 backlog 舊根因）

- **B-15**：backlog 根因句與「三 FP 同源」assumed **已證偽一部分**；修法不可只做 option②。
- **B-14**：`completeness_check --single` **不充分**作「寫完即成功」；timeout 有數據建議。
- **B-24**：「不建檢查器」與使用者定死「工具自帶強制」**衝突**；SPEC 須二選一或降級為過渡。
- 無必須先另開 hotfix 才能寫 SPEC 的 blocker；但 SPEC 若照抄 backlog 錯誤根因 → 本輪 findings 應 BLOCK 該 SPEC。

---

## Q1（B-15）三個 FP 逐例重現

**方法**：`REGEX`＝`gate_check.sh:87` 原文；並以隔離副本  
`/private/tmp/govb0-recon-grok/gate_check.sh` + `GATE_DIR=/private/tmp/govb0-recon-grok/gate_empty`  
餵 PreToolUse JSON `{"tool_name":"Bash","tool_input":{"command":...}}`。  
live 模型與 regex 模型 **mismatches=0**。

| FP | 完整指令字串 | 是否命中 | 命中的 alternation | 命中處字元位置與上下文 |
|---|---|---|---|---|
| FP1 `pgrep` | `pgrep -fl 'codex exec\|cursor-agent\|grok '` | **YES**（live rc≠0 → GATE BLOCKED） | `grok` at command-position via **`\|` 當分隔符** | span `(34,40)` 匹配 `\|grok `；context `ex exec\|cursor-agent\|grok '` |
| FP2 `for` 讀產出 | `for f in codex composer grok; do cat handoffs/x-$f.md; done` | **NO**（live rc=0） | — | 家族名在 `in` 列表／檔名位置，**不在** `(^|[;&|]\s*)` 命令位 |
| FP3 `completeness --lock` | `bash scripts/completeness_check.sh --lock handoffs/reconcile/foo.lock` | **NO**（live rc=0） | — | 無家族 CLI 命令位；腳本名亦不命中 |
| （對照）引號內 `; codex` | `bash scripts/reconcile_build.sh s1 --reason "no review file; codex closure review"` | **YES** | `codex` | span `(59,67)` 匹配 `; codex `；引號**不**保護 |
| （對照）檔名子字串 | `cat handoffs/sp_codex.txt` | **NO** | — | 與 `gate_check.sh:82` 註解一致 |

**FP1 機制（非「字串含家族名」）**：  
正則把 **`|`** 當命令分隔符；pattern 內 `|grok `（pipe + `grok` + **空白**）被當成「新命令 `grok`」。  
對照：`pgrep -fl 'cursor-agent '` → **NO**；`pgrep -fl '…|grok'`（無尾空白）→ **NO**。

**FP2／FP3：重現不出來**（重要結論，非湊例）。  
backlog `## B-15` 列的後兩例在**當前** `gate_check.sh` Bash 通道**不會**被 :87 命中。可能解釋（未在本輪找到字串級事故留檔，標 assumed）：
1. 事故指令與 backlog 摘要不等價（例如複合命令後接真 CLI）；
2. 經 **Task** 工具（`kind=dispatch` 無條件，與字串無關）；
3. 舊版正則／不同 gate 路徑（本輪只證 current）。

**backlog 根因句已錯**（與 brief fact-verified 一致）：  
「判定僅比對指令字串是否含家族名，不區分讀寫」——實碼是**命令位置**比對（:82–87 註解＋實測 `cat sp_codex.txt` 放行）。

**audit.log 無法還原誤擋語料**（fact）：`gate_deny` 欄位僅 `event/ts/tool/kind/reason`；reason 只有 `token_expired`／`open_debt`（本輪計 493+110；brief 記 493+106，量級一致、筆數隨時間漂移）。

---

## Q2（B-15）語料與兩案（+疊加）實測

### 語料（每條有出處；禁憑空）

| 類 | 出處 | 指令形態 |
|---|---|---|
| TP | `scripts/cx_run.sh:443` | `$CODEX exec -s workspace-write …`（含 **絕對路徑** `/opt/homebrew/bin/codex`） |
| TP | `scripts/cx_run.sh:452` | `$GROK -m grok-4.5 …`（絕對路徑 `…/grok`） |
| TP | `scripts/cx_run.sh:461` | `cursor-agent -p --force …` |
| TP | 同上 bare 名 | `codex exec`／`grok -m`／`cursor-agent -p` |
| TP | 手搓繞過（`cx_run.sh:5` 明文禁止但技術可行） | `codex exec …`；`CODEX_HOME=… codex exec …` |
| TP | `committee_run.sh:269` | `bash scripts/cx_run.sh …`；`ROUND_ID=… bash scripts/cx_run.sh …`；`bash scripts/committee_run.sh …` |
| TP | `gate_check.sh:87` | `claude -p`／`claude --print` |
| TN | backlog FP1–3；HANDOFF 引號分號；`gate_check:82` 檔名；唯讀 grep/ls/head/cat；`gate.sh dispatch` bootstrap |

### 方案定義（隔離原型，非改 repo）

| 方案 | 規則 |
|---|---|
| CURRENT | 現況 :87 + `scripts/gate(_check)?.sh` 排除 |
| ① 引號感知 | 先剝單/雙引號span，再套 CURRENT 家族命令位 |
| ② 呼叫點 | 僅 `cx_run.sh`／`committee_run.sh` 出現則擋；`gate.sh` bootstrap 仍放行；**不**看家族 CLI |
| ③ 疊加 | ① OR（`cx_run`/`committee_run` 呼叫點）；`gate.sh` 仍排除 |

### 結果表（n=25：TP=13 TN=12）

| 方案 | TP 被擋 | TP 漏網 | FP 誤擋 | TN 正確放行 |
|---|---:|---:|---:|---:|
| CURRENT | 8 | **5** | **3** | 9 |
| ① 引號感知 | 8 | **5** | 0 | 12 |
| ② 呼叫點 | 3 | **10** | 0 | 12 |
| ③ 疊加 | 11 | **2** | 0 | 12 |

**TP 漏網明細（權重最高）**

| 方案 | 漏網 |
|---|---|
| CURRENT／① | ①絕對路徑 `…/codex`、`…/grok`（**basename 非裸名**）②外層 `bash scripts/cx_run.sh`／`committee_run.sh`（官方主路徑！） |
| ② | 全部裸名／絕對路徑家族 CLI、手搓 `codex exec`、`claude -p`——**fail-open 不可用** |
| ③ | 僅剩絕對路徑 `…/codex`、`…/grok`（`cursor-agent` 通常裸名故仍擋） |

**live 證實絕對路徑繞過**（CURRENT `gate_check` 隔離副本）：

```
rc=0 cmd='/opt/homebrew/bin/codex exec hi'
rc=0 cmd='/Users/louis/.grok/bin/grok -m x -p y'
rc≠0 cmd='cursor-agent -p hi'   # 有擋
```

**對 assumed 的 verdict**

1. 「三 FP 全源自引號不感知」→ **FALSE**（FP1 是 **quote 內的 `|` 當分隔符**／或等價 pipe 語意；FP2/FP3 現況不命中）。引號感知能修 FP1 與 `; codex` 類，**不能解釋**未命中的 FP2/FP3。
2. 「option② 比 ① 乾淨」→ **FALSE 且更危險**：TP 漏網 10／13，手搓家族 CLI 全漏；與 brief 攻擊方向一致。
3. **建議寫入 SPEC 的方向**＝③ 的強化版：**引號感知 + 命令位 basename**（`(?:\S*/)?(codex|…)`）**+** 外層 `cx_run.sh`／`committee_run.sh` 呼叫點；`gate.sh dispatch` 維持 token 發行放行。另：PreToolUse **看不見** `cx_run` 子進程內的 CLI——外層呼叫點補的是「官方 harness 也要 token」政策洞，與子進程無關。

**原型補充**：quote-strip 後 FP1 的 `|grok ` 隨引號內容消失 → ①/③ 對 FP1 放行（已列入上表 FP=0）。

---

## Q3（B-14）逾時落點與「完整即成功」

### 現況（fact）

- `scripts/cx_run.sh`：**`timeout` 字面零命中**（`grep -c timeout` → 0，rc=1）；`:443/:452/:461` 前景直呼 CLI。
- `scripts/committee_run.sh:280`：裸 `wait "${pid}"`，**無上限**。
- 事故敘事（backlog）：composer 已寫完產出，sandbox 卡 `cat <&3`，空等 **2h20m**；最長 runlog birth→mtime **146.7m**＝`handoffs/20260803-govflow-todo-r2-composer.runlog`。

### 落點比較

| 層 | 作法 | 代價 |
|---|---|---|
| **A. `cx_run.sh` CLI 呼叫**（:443/:452/:461） | `timeout ${SEC} <cli…>` 或等價 | 訊號進 CLI 進程組；`cli_rc` 可區分 124；**runlog 仍由外層重導**；format check／`_emit_family_result` 仍跑得成。孤兒：timeout 殺主進程後子 sandbox 或殘留（composer 事故本就有殘殼）→ 需 `pkill` 或 process group。 |
| **B. `committee_run.sh:280` wait** | `wait` 輪詢 + 截止 | 只控「等多久」；**殺不了**已掛的 `cx_run`/CLI 除非另 `kill $pid`；多家族並行時 per-pid 截止自然。runlog 完整性：kill 後可能無最終 `[cx_run] done` 行。 |

**建議**：**A 為主（per-family timeout 包 CLI）+ B 為保險（committee 對 pid 硬上限略大於 A）**。只做 B 會留下掛死 CLI；只做 A 在 `cx_run` 卡在 CLI 前／後少見路徑仍可能拖 wait——雙層成本低。

### `completeness_check --single` 是否充分？

**不充分**（實跑）：

| 檔 | 意涵 | rc |
|---|---|---|
| 缺 `**碼證**` 的 finding | 格式爛 | **1** |
| 兩條 finding 欄位齊、**無** `STATUS: DONE` | 中途停寫但格式齊 | **0** |
| 僅一條完整 finding + Verdict、無更多內容 | 同左 | **0** |

`--single`（:1459–1472）只做：canonical ID、同檔重複、body 斷言/碼證、P0/P1 digest。  
**不檢查**：寫作是否結束、`STATUS: DONE`、Verdict 是否為審查結論、是否還有未寫完章節。

⇒ 「逾時 + single rc=0 ⇒ success」會把**提早停寫但格式碰巧完整**的產出當成功。

**補救判準（建議寫進 SPEC，可組合）**：

1. single rc=0；**且**
2. 檔案 mtime 在逾時前已穩定 ≥ N 秒（無繼續寫入）；**且**
3. 契約結尾標記：`STATUS: DONE` 或 brief 規定的 Verdict 行（consult/review 分流）；**且**
4. 可選：runlog 出現 CLI 正常結束痕跡 vs 僅 timeout——若 CLI 仍活且 mtime 持續變，不得 success。

### 逾時值（runlog birth→mtime，handoffs 440 個可算樣本）

| 家族 | n | p50 | p90 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 440 | 5.3m | 20.7m | 26.3m | 48.5m | 146.7m |
| codex | 160 | 11.8m | 25.4m | 29.8m | 34.9m | 43.1m |
| composer | 144 | 3.0m | 9.8m | 14.6m | 68.2m | **146.7m** |
| grok | 136 | 4.9m | 14.5m | 22.7m | 49.0m | 64.6m |
| composer 排除 >90m | 143 | — | — | 12.9m | — | 68.2m |

**建議（數據，非感覺 30m）**：

- 預設硬頂：**60m／家族**（> ALL p99 48.5m，遠低於 146m 掛死；允許 grok/codex 長尾）。
- composer 可 **45m** 起（健康 p95≈13m；68m 樣本可能已含半掛）；若怕誤殺長審查 → 與 60m 對齊。
- **勿**用 30m 一刀切：codex p95≈30m，誤殺風險高。
- 可配置 env（如 `CX_FAMILY_TIMEOUT_SEC`），預設按上表；測試 harness 可縮短。

### `result_state` 三值

寫入點 `_emit_family_result`（`cx_run.sh:250–288`）：

| 值 | 條件（:262–272） |
|---|---|
| `success` | `cli_rc==0` 且產出非空 且 `fmt_rc==0` |
| `format-failed` | `cli_rc==0` 且產出非空 且 `fmt_rc!=0` |
| `failed` | 其餘（含 CLI 非 0、產出空） |

audit 欄位：`:286 --field result_state=…`。

**逾時應寫**：

- 產出通過「充分完整」判準 → 視同正常結束：`cli_rc=0` 路徑 → `success` 或（格式爛）`format-failed`；
- 產出不完整／空 → **`failed`**（不得 success）；
- **不要**新造第四值（除非另開 schema 票）；timeout 可另記 runlog／optional 欄，但三值契約內歸 `failed` 或完整則 `success`。

---

## Q4（B-24）驗收欄盤點與強制機制

### templates/（全 md）

| 檔 | 「rc／腳本通過」取向 | 「狀態斷言」取向 |
|---|---|---|
| `SPEC_TEMPLATE.md` | :28 `ASSERT … THEN rc=` 固定文法；:33 非條件式可散文 `pytest 全綠` | :51 FACT-RECEIPT 要求 stdout 摘要（近狀態） |
| `COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md` | :12/:27/:28/:39 多處 `completeness_check` **rc=0** | 無 git status／差集類 |
| `SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` | 不可測驗收檢查（:30） | :25 VERIFY+stdout |
| `COMMITTEE_FINDING_TEMPLATE.md` | — | :32 碼證含 stdout |
| `TODO_GENERATION_PROMPT.md` | 驗證要可證偽（:70） | 無 B-24 意義的狀態斷言範本句 |
| 其餘 json/html 範本 | N/A 治理驗收 | N/A |

**缺口**：templates **沒有**「跑 `restore_*.sh` 後必須 `git status --short …` 為空」這類 **B-24 範型** 的必填錨點；語義審查範本甚至**強化 rc=0 口吻**。

### docs/*SPEC*/*TODO*（83 路徑，426 條含驗收/驗證關鍵字的行——啟發式）

| 桶 | 約略條數 | 含義 |
|---|---:|---|
| 僅 rc／腳本信號 | 58 | 易犯 B-24 |
| 僅狀態信號 | 7 | 少 |
| 兩者都有 | 5 | 接近正確（如 P2DEBT pre-dirty delta） |
| 兩者皆無（空泛「驗證」） | 356 | 多數不可機檢是否 B-24 |

（啟發式會有誤判；方向穩：`狀態斷言` 遠少於 `rc=0`／跑腳本。）

### 可機檢形態？

可行 tripwire（非完美）：

- 驗收／驗證行匹配 `rc\s*=\s*0` 或 `restore_.*\.sh`／`bash scripts/\S+` **且同條（或後 N 行）無** `git status|差集|為空|stdout|FACT-RECEIPT|實際輸出` → 警告/FAIL。
- **誤報預估**：中高（30–50%+）。反例：`ASSERT … THEN rc=0` 行為契約（SPEC_TEMPLATE 合法）、純單元測試「exit 0」、語義模板「機械層 rc=0」。需白名單文法（`ASSERT` 行、`completeness_check` 機械層）。
- 低誤報做法：只掃 **TODO/brief 完工驗收清單** 中含 `restore_`／`gate.sh`／`agent_postflight` 的列，強制鄰近狀態命令——範圍窄、對 B-24 事故形態準。

### 「不建檢查器」能否成立？

**對 assumed「不建檢查器即可」→ 否決（MAJOR）**。  
使用者定死：「工具必須自帶強制機制——不准靠紀律和記憶」。  
backlog `## B-24`「併入各票驗收欄，不另建檢查器」＝又一條靠主委／委員記得寫狀態句的 prose 規則；與定死條款直接衝突。  
**最低可接受強制**（擇一寫進 SPEC）：

1. 窄域機檢（上節 restore/postflight 鄰近狀態命令）；或  
2. `template_check`／brief 範本新增必填 token（`STATE-ASSERT:` 行）；或  
3. 驗收 runner（`GOV-VERIFY-RECEIPT-RUNNER` 已 OPEN）執行狀態命令並比對期望 stdout。

若本批堅持「只改 prose」→ 必須在 SPEC 標 **殘留風險＝無機械強制**，不得宣稱 B-24 已「根治」。

---

## Q5 合成一批：順序與耦合

| 題 | 結論 |
|---|---|
| B-24→B-15→B-14 順序？ | **合理非唯一**。B-24 橫向、檔案面是 templates/docs 驗收句；B-15 只動 `gate_check.sh`（+測試）；B-14 動 `cx_run.sh`／`committee_run.sh`。 |
| 必須拆開？ | **無強技術必須**。風險：(1) B-15 改「誰被擋」需 **手動前後對照表**（B-29 未落地）；(2) B-14 行為／audit 契約敏感。可同一管線分 Phase，Phase gate 分開驗。 |
| 必須調換？ | 無。B-14 不依賴 B-15；B-15 不依賴 B-14。B-24 若做機檢可最後或最先（模板）。 |
| 共用檔衝突？ | **三票主改檔不相交**。測試檔可能同碰 `tests/governance/`——TODO 劃分測試模組即可。 |

---

## Q6 可否進 SPEC？

**可以起草 SPEC**。須吸收：

1. 重寫 B-15 根因（命令位 + 引號/pipe；非「含家族名」）。  
2. FP2/FP3 標 **未重現**——修法 acceptance 不得假裝已修這兩條 unless 另找到真指令。  
3. 修法以 **③+basename** 為默認候選；② 單獨 = 不可用。  
4. B-14：timeout 60m 級 + 完整判準 **> single rc=0**。  
5. B-24：正視強制機制；禁「只改驗收散文」當 Done。  

---

## 被當成事實的未驗證假設（§0）

| 假設 | 本輪 verdict |
|---|---|
| 三 FP 全因引號不感知 | **證偽**（僅 FP1／`;codex` 類可重現；FP2/FP3 無命中） |
| option② 更乾淨 | **證偽**（TP 漏網不可接受） |
| B-24 不建檢查器即可 | **與使用者定死衝突**；不可當已驗證策略 |
| brief 內 gate 正則／audit 欄位／cx 無 timeout | **fact-verified 複核通過**（receipt 見上） |

---

## GROK-R1-P0-01

**斷言**: backlog 所稱 FP2（`for f in codex…`）與 FP3（`completeness_check --lock`）在現版 `gate_check.sh:87` **無法重現為 dispatch 誤擋**；不得寫進 SPEC 當已證根因。

**碼證**: 隔離 `gate_check`：`FP2 rc=0`、`FP3 rc=0`；regex 無 match。對照 FP1 `rc≠0` 且 span `(34,40)=|grok `。`VERIFY: printf '%s' "for f in codex composer grok; do cat x; done" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]' ; echo $?` → 預期 1。

**來源摘要**: scripts/gate_check.sh#871258c9ea2e

BLOCKING（對錯誤 SPEC 前提）信心度=High。修法：acceptance 只承諾已重現形態（FP1、引號分號、絕對路徑洞、外層 cx_run 洞）。

---

## GROK-R1-P0-02

**斷言**: B-15 修法選項②（只認 `cx_run`／`committee_run`／`gate dispatch`）對語料 TP **漏網 10/13**，含全部手搓 `codex exec`／`cursor-agent`／`grok`／`claude -p`，屬 fail-open，**不可採用為唯一判準**。

**碼證**: 隔離原型計分表（Q2）；`codex exec` CURRENT=BLOCK、OPT2=ALLOW。出處手搓風險：`scripts/cx_run.sh:5` 註解「勿再手搓」。

**來源摘要**: scripts/cx_run.sh#39cfdddec350

BLOCKING 信心度=High。修法：①+basename+呼叫點疊加；mutation 必含手搓 CLI 仍擋。

---

## GROK-R1-P0-03

**斷言**: 現版 gate 對 **絕對路徑家族 CLI**（`cx_run` 真實呼叫形態 `$CODEX`／`$GROK`）**不擋**，是已存在 fail-open，SPEC 必須修。

**碼證**: live 隔離 gate：`/opt/homebrew/bin/codex exec hi` → rc=0；`/Users/louis/.grok/bin/grok -m x -p y` → rc=0；對照 `cursor-agent -p hi` 有擋。源碼：`cx_run.sh:443,452` 使用絕對路徑變數。

**來源摘要**: scripts/cx_run.sh#39cfdddec350

BLOCKING 信心度=High。修法：命令位改 `(?:\S*/)?(codex|cursor-agent|grok|agy)[[:space:]]`。

---

## GROK-R1-P1-01

**斷言**: `completeness_check.sh --single` rc=0 **不能**單獨作為 B-14「逾時且產出完整⇒success」的充分條件。

**碼證**: 構造兩 finding 齊全但無 `STATUS: DONE` 之檔 → `DIRECT_RC=0`；缺碼證檔 → `DIRECT_RC=1`。single 路徑 :1459–1472 無結尾標記檢查。

**來源摘要**: scripts/completeness_check.sh#12e981972d78

MAJOR 信心度=High。修法：success 判準疊 STATUS/Verdict/mtime 穩定。

---

## GROK-R1-P1-02

**斷言**: B-24「不另建檢查器、只改驗收散文」與使用者定死「工具自帶強制、不准靠記性」衝突；本批若照 backlog 原文結案會假閉合。

**碼證**: backlog `## B-24`「併入…不另建檢查器」；HANDOFF「工具必須自帶強制機制」。templates 無 B-24 狀態斷言必填錨；`COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md` 反多 `rc=0`。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#13cc634125da

MAJOR 信心度=High。修法：窄域機檢或範本強制 token 或 receipt runner。

---

## GROK-R1-P1-03

**斷言**: 官方外層 `bash scripts/cx_run.sh`／`committee_run.sh` 在 CURRENT 下 **不分類為 dispatch**（PreToolUse 只見外層）；與「派工必經 gate token」政策不一致，疊加呼叫點可補。

**碼證**: live：`bash scripts/cx_run.sh codex brief out` → rc=0（無 token 仍放行）。Task 工具另計（:73–75 無條件 dispatch）。

**來源摘要**: scripts/gate_check.sh#871258c9ea2e

MAJOR 信心度=High（政策洞；子進程本就不可見）。修法：納入 ③。

---

## GROK-R1-P2-01

**斷言**: B-14 per-family timeout 建議硬頂約 **60 分鐘**（數據：ALL p99=48.5m；codex max=43.1m；掛死樣本 146.7m），**不應**用 30m 全球值。

**碼證**: 440 個 `handoffs/**/*.runlog` birth→mtime 分布（Q3 表）；最長 `20260803-govflow-todo-r2-composer.runlog` 146.7m。

**來源摘要**: scripts/committee_run.sh#4c6bdeff1a15

MINOR/建議 信心度=Medium（birthtime 代理，非 audit 內建 duration 欄）。修法：env 可覆寫；composer 可另參 p95。

---

## GROK-R1-P2-02

**斷言**: 三票主改檔不相交，可同一批次分 Phase；B-15 必須附前後對照語料（因 B-29 未做）。

**碼證**: B-15→`gate_check.sh`；B-14→`cx_run.sh`+`committee_run.sh`；B-24→templates/驗收句。HANDOFF 明示 B-15 即 B-29 差集案例。

**來源摘要**: HANDOFF.md#c49bf7e9d2b0

MINOR 信心度=High。

---

## GROK-R1-P3-00

**斷言**: 本偵察對 brief fact-verified 三條（正則命令位、audit 無指令、cx/committee 無 timeout）複核一致，無推翻。

**碼證**: 讀 `gate_check.sh:82-87`；`gate_deny` fields 僅五欄；`grep -c timeout scripts/cx_run.sh`→0；`committee_run.sh:280` 裸 wait。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

NON-BLOCKING 信心度=High。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - gate :87 命令位正則；FP1=|grok 命中；FP2/FP3 不命中
  - audit gate_deny 無 command 欄
  - cx_run 無 timeout；committee wait 無上限
  - option①/②/③ 語料計分；絕對路徑 live 繞過
  - completeness --single 對「無 STATUS 但格式齊」rc=0
  - runlog 耗時分布 n=440
TESTS_RUN:
  - 隔離 gate_check 多指令（FP/TP/TN）
  - python 原型 CURRENT/①/②/③ 計分 n=25，live vs CURRENT mismatches=0
  - completeness_check --single 三探針（缺碼證 rc=1；齊全無 STATUS rc=0）
  - openssl dgst 來源摘要
FAILURES_SEEN: none（初版 pipe 取 rc 已改直接取）
SCOPE_CHANGES: none（只產 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none
```

WORKDIR 清理：刪 `/private/tmp/govb0-recon-grok`（保留系統 `claude-501`）。

STATUS: DONE
