# Multi-Agent Orchestration — Claude 編排手冊

> **角色分工**：Claude (Opus, $20) 規劃 / 寫 SPEC / 驗收 → Codex CLI / Cursor CLI 執行 + debug。
> **目的**：把長時間實作與 debug 迴圈移出 Opus，分散 hour / weekly limit。
> **本文件給誰看**：Claude（編排者）。執行端的規則在 `AGENTS.md`（Codex）/ `.cursorrules`（Cursor）的「執行任務時」一節。

---

## 0. 一次性設定（使用者本人做一次）

```bash
# Codex CLI（已用 brew 裝；登入用 ChatGPT $20 帳號）
codex login            # 互動式，必須使用者本人在終端機完成

# Cursor CLI（已裝於 ~/.local/bin/cursor-agent）
cursor-agent login     # 互動式，用 Cursor $20 帳號登入

# Antigravity CLI（已用 brew 裝，binary 名 `agy` v1.0.3；用 Gemini AI Pro/Ultra 訂閱）
agy                    # ⚠️ 無 login 子命令！首次直接跑 agy（互動 TUI）會觸發授權，
                       #    印出授權 URL + 一次性碼，用 Google 帳號登入。Gemini CLI 2026-06-18 退役，agy 接棒
```

登入是互動式驗證，Claude 無法代勞。裝好登入後，Claude 即可用 Bash 工具驅動三者。
- ✅ 已驗證（2026-05-31）`agy --help`：`-p/--print`（非互動單 prompt）、`--dangerously-skip-permissions`（自動核准）、`--sandbox`、`--print-timeout`。可被 Claude 驅動，等同 codex/cursor。

---

## 1. 執行池與選層（Claude 決定，使用者不用管）

| 層 | 角色 | 工具 | 何時用 |
|----|------|------|--------|
| 1 | 規劃 / SPEC / 驗收 | **Claude (Opus)** | 高價值思考，額度集中於此 |
| 2 | 主力執行 | **`codex exec`**（GPT-5.5） | terminal-heavy、長自主任務、需嚴謹 root-cause |
| 3 | 溢出 / 廉價執行 | **`cursor-agent -p`**（Composer 2.5） | Codex 額度吃緊、或大量 routine 實作（便宜 10–60×） |
| 3 | 溢出執行（Gemini 家族） | **`agy -p`**（Gemini） | Gemini 訂閱額度可用時的另一個執行端 |

**選層原則**：預設 Codex 主力；Codex 額度告警或任務偏 routine/多檔編輯 → 切 Cursor 或 agy。切哪個對使用者透明，使用者只跟 Claude 講需求。

### 規劃委員會（高風險不可逆決策才開全員）
研究 / SPEC 階段可 fan-out 多模型家族「諮詢」（read-only，不 exec）以防單一盲點：

| 成員 | 工具 | 家族 |
|------|------|------|
| Claude (Opus) | 本體 | Anthropic |
| Codex | `codex exec`（或 `codex consult`） | OpenAI GPT |
| Antigravity | `agy -p` | Google Gemini |

Claude 當綜合者：提煉「共識 / 分歧 / 我的判斷」給使用者，只凸顯打架的點，不丟原始 4 份輸出。日常規劃 2 個聲音即可；架構 / pipeline 本身設計才開全員。`/benchmark-models` 也可做 Claude/Codex/Gemini 三方比較（不含 Cursor）。

---

## 2. 派工（dispatch）

### 派工前 Claude 必做
1. 依 CLAUDE.md「任務分派規則」判定 小 / 中 / 大，並向使用者宣告。
2. 中 / 大任務：先寫好 SPEC（+ TODO）落地成檔，路徑明確。
3. 確認 `HANDOFF.md` 反映當前狀態（執行端會先讀它）。

### Codex 派工模板
```bash
codex exec -m <GPT-5.5 model id> -s workspace-write \
  -o /tmp/codex_last.txt \
  "讀 HANDOFF.md、CLAUDE.md、AGENTS.md。\
依 specs/<NAME>_SPEC.md 與其 TODO 實作 <Phase/Task 範圍>。\
嚴守 AGENTS.md「執行任務時」合約：只改範圍內檔案、不弱化品質 gate、不腦補數值。\
完成後跑 <pytest 指令>。結束時更新 HANDOFF.md，最後輸出一行 STATUS: DONE 或 STATUS: BLOCKED — <原因>。"
```
- `-m` 顯式釘模型（見 §8 模型釘選）；`-s workspace-write` = sandbox 只能寫工作目錄（安全，命令自動執行不互動提問）。
- `-o <FILE>` 把 agent 最後一則訊息寫檔，Claude 讀它取 STATUS，不必撈整段 log。`--json` 可取 JSONL 事件流。
- 長任務用 `run_in_background: true`（Claude 的 Bash 工具），跑完通知 Claude。
- 一次性小任務可不寫 SPEC，prompt 內直接給明確指令 + 範圍 + 驗收命令。

### Cursor 派工模板（非互動 print 模式）
```bash
cursor-agent -p --force --output-format text --model <Composer 2.5 model id> \
  "讀 HANDOFF.md、CLAUDE.md、.cursorrules。<同上任務描述與合約要求>。\
完成輸出 STATUS: DONE 或 STATUS: BLOCKED — <原因>。"
```
- `--force`（= `--yolo`）自動允許命令，不互動提問；`--output-format text|stream-json`。
> ✅ **已驗證**（2026-05-31）：codex `-m/-s/-o/--json/resume`、cursor `-p/--force/--model/--output-format/--list-models` 旗標均存在。

### Adversarial review = 跨模型（大任務必做）
SPEC freeze 前，Claude 寫的 SPEC 由**對方模型**審：
```bash
codex exec review   # 或在 prompt 帶 SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 要求 challenge
```
讓沒有 Claude 盲點的模型挑 blocking findings，比自審有效。修補後才 freeze。

---

## 3. 查進度

執行端在自身 context 跑 implement→test→debug 迴圈，**不回灌 Claude context**。Claude 只觀測產出：

```bash
git status            # 動了哪些檔
git diff --stat       # 改動規模
git diff <file>       # 看具體改動（按需，控制讀取量）
git log --oneline -5  # 執行端的 commit
```
- 背景任務：讀 task output log 看 streaming 進度。
- **不要把執行端的完整 debug log 拉進 context** — 那正是會爆 context 的東西。

---

## 4. 驗收（accept）

靠 SPEC §1.0 可測性準則，**只驗 pass 條件，不重演過程**：

1. **跑驗收測試**（Claude 自己跑，便宜且客觀）：`pytest <對應測試>`。
2. **讀 diff**：是否符合 TODO、是否越界改了範圍外檔案。
3. **品質 gate 抽查**：`grep -r "from api\." momentum/` → 0；無 fake data；NaN/inf gate 未被弱化。
4. **讀 STATUS 行 + HANDOFF.md** 的一段摘要。

通過 → 收。失敗 → 帶著具體失敗點再派一輪。

---

## 5. 卡關 / 需決策（escalation & resume）

headless 模式**不會互動提問**（codex sandbox 內自動執行 / cursor `--force`）。執行端遇到「需要使用者決策」或「debug ≤ 3 輪未過」→ **停下並輸出 `STATUS: BLOCKED — <問題>`**，不卡在那等輸入。

**決策回填迴圈（使用者只跟 Claude 對話，不直接面對執行端）：**
```
執行端 BLOCKED → Claude 讀 -o 輸出檔取問題 → 轉述使用者 → 使用者回答
  → Claude 用 codex exec resume --last "答案：<YES/NO/comment>，理由…" 接回原 session
```
`codex exec resume --last` 續接最近 session，不必從頭重跑（cursor 則重發 prompt 帶上答案）。

**debug 卡關時**：
- Claude 用 `/investigate`（gstack skill）做 root-cause，只吃摘要 + 關鍵幾檔，不吃全 trace。
- 難 bug 的 debug 優先用便宜模型（Codex/Cursor），**不要動用 Opus 硬啃**。

---

## 6. 成本與額度

| | Codex (GPT-5.5) | Cursor (Composer 2.5) |
|---|---|---|
| 每任務概估 | ~$4.8 等級 | Fast ~$0.44 / 標準 ~$0.07（便宜 10–60×） |
| 強項 | terminal-bench、長自主、root-cause | 多檔編輯、routine、速度快 |

額度策略：Codex 主力，告警時切 Cursor 當溢出；或反轉用 Cursor 當日常主力、Codex 留給硬任務。實測手感後再定。

### 主力決策法（用數據，不靠感覺）
預設 Codex 主力。累積數個**真實任務**後，Claude 追蹤四指標決定是否翻轉：

| 指標 | 含義 |
|------|------|
| pass@1 | 驗收測試一次過的比率 |
| scope 紀律 | 是否越界改範圍外檔案 |
| 成本 / wall-clock | 每任務 $ 與耗時 |
| BLOCKED 頻率 | 多常卡住需 Claude 介入 |

工具：gstack **`/benchmark-models`**（同 prompt 跑 Claude / Codex / Cursor，比 latency·tokens·cost，可加 LLM judge 比品質）。
翻轉規則：若 Cursor 在某任務類型上**品質追平、成本低 10–60×** → Cursor 當該類日常主力，Codex 留給 terminal-heavy / 難 root-cause。

---

## 7. 模型釘選（不靠預設，顯式指定 + 定期重驗）

模型會更新，目標是「當下評分最高」而非寫死。每隔一陣子重驗：
```bash
# 列出帳號當下可用模型（需先 login）
codex doctor                 # 檢查 auth/config；model 設定見 ~/.codex/config.toml
cursor-agent --list-models   # 或 cursor-agent models
```
- 確認 GPT-5.5 / Composer 2.5（或更新的最佳模型）的實際 model id。
- 把 id 顯式釘進派工指令的 `-m` / `--model`，並記錄下表。

| 角色 | CLI | 釘選 model id | 重驗日期 |
|------|-----|--------------|----------|
| 主力執行 | codex | _(login 後填)_ | — |
| 溢出執行 | cursor-agent | _(login 後填)_ | — |

---

## 8. 鏈路驗收測試集（新 agent / 新專案 / 換執行端時必跑）

> 目的：證明「派工 → 執行端做 → Claude 驗收」這條鏈在當前環境真的成立。
> 換新 CLI、接新 agent、或把這套搬到新專案時，跑一遍下列測試確認設定有效。
> 每個測試都要 **Claude 獨立重跑驗收**（不採信執行端自報）。

| ID | 測什麼 | 通過條件 | 狀態（codex, 2026-05-31） |
|----|--------|----------|--------------------------|
| T-A | **Happy-path 寫入** | 派「新建檔 + 測試」小任務 → 執行端建檔、自跑測試、輸出 `STATUS: DONE`；Claude 重跑測試通過、diff 無越界 | ✅ PASS（3 passed） |
| T-B1 | **安全閥：反幻覺 BLOCKED** | 派一個需要「未定義且禁止發明的數值」的任務 → 執行端**不猜、不建檔**，輸出 `STATUS: BLOCKED — <問題>` | ✅ PASS（拒絕發明門檻） |
| T-B2 | **安全閥：resume 接回** | 餵答案 → 執行端**接續原 session**（非重跑）完成、`STATUS: DONE`；Claude 重跑驗收 | ✅ PASS（8 passed） |
| T-C | **中型 SPEC 流程** | 寫精簡 SPEC + TODO → 派工 → 按 §1.0 驗收 | ✅ PASS（drawdown 迷你模組，3 Task + 邊界 + golden 數值，Claude 獨立驗） |
| T-D | **執行端對等性** | 同一任務分別跑 codex / cursor / agy，結果可比 | ⬜ 待 cursor/agy 登入 |

### 派工管線踩坑（onboarding 必知）
- **stdin 卡住**：背景/管線環境下 `codex exec` 會等 stdin → 指令末尾加 `< /dev/null` 關閉。
- **resume 旗標**：`codex exec resume` **不吃** `-s`/`-o`（那是 `exec` 的）；sandbox 沿用原 session，prompt 直接當參數。
- **驗收讀摘要不讀全文**：`pytest -q | tail`，token 成本與 test 數量脫鉤（見 §4）。

---

## 9. 相關文件
- `CLAUDE.md` →「Multi-Agent 協作協議 / 任務分派規則」（Claude 每次自動注入）
- `AGENTS.md` / `.cursorrules` →「執行任務時」合約（執行端必守）
- `HANDOFF.md` → 跨 agent 交接狀態
- `templates/SPEC_TEMPLATE.md`、`TODO_GENERATION_PROMPT.md`、`SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`
