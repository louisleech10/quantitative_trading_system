# 第 0 批開工偵察 — 主委（Claude）獨立版

輪次 R1。與 codex／composer／grok 三家平行、互不參照產出。
全部 receipt 為 2026-08-04 本機實跑，探針一律隔離副本（`.claude/tmp/`），未變異 repo 內任何 tracked 檔。

---

## CLAUDE-R1-P0-01

**斷言**: 被 `gate_check.sh` 擋下的指令**在整個系統中沒有任何紀錄** —— `audit.log` 的 `gate_deny` 事件不含指令欄位，`ts_stamp.log` 因 hook 排序在 gate 之後而不會執行。因此 `B-15` 的誤擋率**無法事後量測**，改完也**無法驗證改對了**。

**碼證**:
- `scripts/gate_check.sh:28` 的 `_append_gate_deny_audit` 只寫 `{"event","ts","tool","kind","reason"}` 五欄，**無 command**。
- `.claude/settings.json:99-135`：`PreToolUse` 依序為 ①`gate_check.sh`（matcher `Task|Bash|Write`）②`block_busywait.sh` ③`verify_pretooluse.sh` ④`ts_stamp.sh IN`（matcher `Bash|Edit|Write`）。gate 為**第 1 個**。
- 決定性實測（今日已知被擋的指令）：`LC_ALL=C grep -ac 'closure review' .claude/gate/ts_stamp.log` → **0**；
  改用訊息檔的成功重試 `LC_ALL=C grep -ac 'hmsg.txt' .claude/gate/ts_stamp.log` → **2**。
  ⇒ 被擋者零紀錄、成功者有紀錄，機制確認。
- `LC_ALL=C grep -o '"reason":"[^"]*"' .claude/gate/audit.log | sort | uniq -c` → 全檔 599 筆僅兩值：`token_expired` 493、`open_debt` 106。**無任何 reason 指出「正則命中了什麼」**。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：這是 `B-15` 的**前置阻塞**，不是附帶改善。沒有 deny 紀錄則：①誤擋率是憑印象的 ②`票 B-29`（行為差集宣告）對 gate 這條線**做不出差集**，因為「舊版擋了誰」根本沒被記下來。
建議修法順序改為：**先讓 `gate_deny` 記下（a）完整指令（b）命中的 alternation，再談改判準**。落點＝`gate_check.sh:21-30`（`_append_gate_deny_audit` 加欄）＋ `:86` 命中時保留 `grep -Eo` 結果。
🔴 隱私/體積考量須在 SPEC 處理：指令可能含長 prompt；建議存 sha256＋前 N 字元，或另檔 `gate_deny_cmds.log` 並納入既有 rotate 機制。

---

## CLAUDE-R1-P1-02

**斷言**: backlog `## B-15` 節記載的三個 FP，**只有一例可重現**；另外兩例（`for` 迴圈讀產出、`completeness_check.sh --lock`）用票上記載的形態**跑不出 BLOCK**，且因 `CLAUDE-R1-P0-01` 無紀錄可查證。⇒ 票的事故描述是憑記憶寫的，**不可直接作為 SPEC 輸入**。

**碼證**: `.claude/tmp/b15probe.sh`（正則字面複製自 `gate_check.sh:86`，含 `:81-84` 的 env 前綴剝除與 `:88` 的 `gate.sh` 排除），實跑輸出：

| 案例 | 判定 | 命中片段 |
|---|---|---|
| `pgrep -fl 'codex exec\|cursor-agent\|grok '` | **BLOCK**（重現 ✓） | `\|grok ` |
| `for f in codex composer grok; do cat handoffs/…-$f.md; done` | ALLOW（**重現不出**） | — |
| `for f in codex composer grok ; do echo $f ; done` | ALLOW（**重現不出**） | — |
| `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260804-govb0-recon` | ALLOW（**重現不出**） | — |
| `bash …completeness_check.sh --lock handoffs/reconcile/…/sources/grok.md` | ALLOW（**重現不出**） | — |
| `git commit -m "fix: no review file; codex closure review done"` | **BLOCK**（今日實際踩到 ✓） | `; codex ` |

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：可重現的兩例**同一機制**——正則的 `[;&|]` 吃到**引號內**的 `|` 或 `;`。
不可重現的兩例有三種可能：①票記載的指令形態不精確 ②當時被擋的是同一分鐘內的**另一條**指令（我把兩者記混）③觸發源是 `claude[^|]*(-p|--print)` 那段而非家族名段。
🔴 **SPEC 不得宣稱「三例同因」**。可交付的結論只有：**引號不感知是已證實的一個真洞**；其餘待 `CLAUDE-R1-P0-01` 的紀錄機制上線後才有辦法查。

---

## CLAUDE-R1-P1-03

**斷言**: 現行正則的 **TP 面（真派工必須被擋）完好無缺**，7/7 全過；`B-15` 的問題**純在 TN 面**。任何修法若動到 TP 面就是淨損失。

**碼證**: 同 `.claude/tmp/b15probe.sh`，TP 段實跑全數 BLOCK：
`codex exec -s workspace-write`／`cursor-agent -p --force --model composer-2.5`／`grok -m grok-4.5 … -p`／
`GATE_DIR_OVERRIDE=/tmp codex exec …`（env 前綴繞過）／`cat brief.md | codex exec …`（管線後）／
`echo start; grok -m grok-4.5 -p …`（分號後）／`claude -p "…"`。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：⇒ 修法應為**收窄 TN 誤擋**，而非重寫判準。這條直接影響對方案②的評價（見下）。

---

## CLAUDE-R1-P0-04

**斷言**: `B-15` 修法選項②（改判準為「是否呼叫 `cx_run.sh`／`committee_run.sh`／`gate.sh dispatch`」）**單獨採用會造成 fail-open**：手搓 `codex exec`／`cursor-agent -p`／`grok -m` 三條真派工全部漏網，而現行正則擋得住它們。

**碼證**: `CLAUDE-R1-P1-03` 的 TP-1／TP-2／TP-3 三條命令列均**不含** `cx_run.sh`／`committee_run.sh`／`gate.sh`，在選項②判準下必然放行。手搓派工是 `AGENTS.md`／`.cursorrules` 明文禁止但**技術上完全可行**的路徑，且歷史上確實發生過（`gate_check.sh:78-80` 註解記載 2026-07-23「寫死漏 grok，主力實作 CLI 不被 PreToolUse 攔」的事故，正是同一類漏網）。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：**建議採方案③（疊加）**——保留現行家族名主判準（TP 面不動），只加**引號感知**的前處理（把引號內的 `;&|` 視為一般字元），呼叫點判準最多當**補強**、不得當替代。
⚠️ 我在 brief 裡把選項②標為 `assumed:「更乾淨」`，本條即自我推翻。

---

## CLAUDE-R1-P1-05

**斷言**: `scripts/cx_run.sh` **完全不記錄每家委員的起訖時間或耗時**，因此 `B-14` 的 timeout 值**在現有資料下無法用一手數據決定**，只能靠 runlog mtime 反推（誤差含寫檔延遲與 harness 排程）。

**碼證**: `LC_ALL=C grep -n "date\|SECONDS\|start_ts\|elapsed\|duration" scripts/cx_run.sh` → **零命中**。
`handoffs/*.runlog` 現有 460 份，內容為 CLI 原始 stdout，**無時間欄位**（樣本：`handoffs/20260804-govb0-recon-codex.runlog` 首行 `Reading additional input from stdin...`）。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：`B-14` 修法應**一併補 per-family 起訖時間戳**（寫入 runlog 檔頭或 audit 的 `committee_family_result` 事件），否則：①這次的 timeout 值是猜的 ②未來調整仍然沒有資料 ③無法偵測「某家族逐漸變慢」這種前兆。
這與 `CLAUDE-R1-P0-01` 是同一個病的兩個部位：**治理鏈在關鍵決策點不留可量測的紀錄**。

---

## CLAUDE-R1-P2-06

**斷言**: `.claude/gate/ts_stamp.log` 是 `Non-ISO extended-ASCII text, with LF, NEL line terminators`，**在預設 locale 下 BSD `grep` 對它靜默返回空**（連 `-c` 的計數都不輸出），使「查無此指令」與「量測壞掉」外觀完全相同。

**碼證**:
- `file .claude/gate/ts_stamp.log` → `Non-ISO extended-ASCII text, with LF, NEL line terminators`
- 預設 locale：`grep -c 'IN ' .claude/gate/ts_stamp.log` → **無任何輸出**，rc=1
- `LC_ALL=C grep -ac 'IN ' …` → **8702**；`git commit` 63、`pgrep` 26、`completeness_check.sh --lock` 175、`for f in` 218

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：主委本輪**已經據此做出一次錯誤結論**（誤判「被擋指令連 ts_stamp 都沒記」，理由是 grep 查不到；實際原因是 grep 壞掉，正確結論要靠另一條 hook 排序證據才成立）。
與 HANDOFF 已記的 zsh 斷詞事故同型：**壞掉的量測與「一切正常」外觀相同**。
建議：①任何對 `ts_stamp.log` 的分析一律 `LC_ALL=C grep -a` ②列入 `CLAUDE.md` Gotchas ③追根因＝`ts_stamp.sh` 寫入時未正規化控制字元（NEL 來自 CLI 輸出）。

---

## CLAUDE-R1-P0-07

**斷言**: backlog `## B-15` 第三例 FP（`completeness_check --lock`）的真正機制**已於 2026-08-04 22:5x 現場重現並定位**：不是家族名段，而是第二段 `claude[^|]*(-p|--print)`。觸發條件為「指令含字串 `claude`（`.claude/` 治理目錄或 `/private/tmp/claude-501/` scratchpad 皆命中）＋ 之後任一處出現 `-p` 子字串（`rev-parse`／`--porcelain`／`-print`，**不必是旗標**）＋ 兩者間無 `|`」。

**碼證**: 主委執行唯讀指令
`head -3 "/private/tmp/claude-501/…/tasks/bfzappo85.output"; git rev-parse --short origin/main`
遭 `[GATE BLOCKED] 偵測到 kind=dispatch` 擋下（**現場事故，非構造**）。
隔離重現 `.claude/tmp/b15probe2.sh`（正則字面複製自 `gate_check.sh:86`）：

| 案例 | 判定 |
|---|---|
| 只有 scratchpad 路徑（無 `-p`） | ALLOW |
| 只有 `git rev-parse`（無 `claude`） | ALLOW |
| **兩者併用** | **BLOCK ← 誤擋** |
| `ls /private/tmp/claude-501/; git status --porcelain` | **BLOCK** |
| `cat .claude/tmp/x.txt; git rev-parse HEAD` | **BLOCK** |
| `find .claude/tmp -name "*.md" -print` | **BLOCK** |
| `bash scripts/completeness_check.sh --lock /private/tmp/claude-501/sess; git rev-parse HEAD` | **BLOCK**（＝backlog FP-3 原形） |
| 同一條但中間加管線 | ALLOW（`[^|]` 不跨管線） |
| `claude -p "…"`／`claude --print "…"`（真 TP） | BLOCK（正確） |

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：本條**推翻 `CLAUDE-R1-P1-02` 的「重現不出來」結論**，也推翻三家一致的
「FP-2／FP-3 不可重現」——**不可重現的原因是重建的指令缺了 `claude` 或缺了 `-p`**，
而非該 FP 不存在。
🔴 **嚴重性高於引號那條**：`.claude/` 是治理目錄、`/private/tmp/claude-501/` 是憲法規定的 scratchpad，
`-p` 又是極常見子字串 ⇒ **凡碰治理檔的唯讀指令都在擲骰子**；且「加管線就過」使它看起來時靈時不靈，
主委長期誤以為是隨機環境問題。
🔴 **也是一條 fail-open 線索**：`[^|]` 不跨管線 ⇒ `cat brief.md | claude -p "…"` **不會被擋**。
須併入 `B-15` 的 TP 語料驗證。
**修法**：`claude` 須比照家族名段限定在**命令位置**（`(^|[;&|][[:space:]]*)(\S*/)?claude[[:space:]]`），
且 `-p`／`--print` 須是**獨立引數**（前後為詞界），不得比對子字串。

---

## Verdict

**可以進下一步，但 `B-15` 的施工內容須依 `CLAUDE-R1-P0-01` 重排**：

1. `B-15` 拆兩段：**(a) 先補 deny 紀錄**（指令＋命中 alternation）→ **(b) 再改判準**。無 (a) 則 (b) 不可驗收，且 `票 B-29` 對本票失效。
2. `B-15` 判準採**方案③疊加**（現行家族名主判準不動 ＋ 引號感知前處理），**明文否決單獨採方案②**（`CLAUDE-R1-P0-04`）。
3. `B-14` 須**一併補 per-family 起訖時間**（`CLAUDE-R1-P1-05`），否則 timeout 值無據。
4. backlog `## B-15` 節的事故描述**須先更正**（「判定僅比對指令字串是否含家族名」為錯；三例同因為未證實），再進 SPEC。
5. `CLAUDE-R1-P2-06` 的 locale 坑須進 `CLAUDE.md` Gotchas —— 本輪已致主委誤判一次。

**待三家回報後**，本檔與三家產出走 `reconcile_build.sh` 收斂，再起草 SPEC。
