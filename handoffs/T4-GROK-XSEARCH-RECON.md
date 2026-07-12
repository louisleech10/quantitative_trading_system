# T4 Grok X/Web Recon — Codex CLI sandbox hang (#7852 class)

**Task**: t4-grok-xsearch（純 recon）  
**Agent**: Grok 4.5 | **Date**: 2026-07-12  
**Scope**: X + web/GitHub API — 是否有比 #7852 OPEN 更新的修補/繞法/版本區間  
**Method**: GitHub REST API (`api.github.com/repos/openai/codex/...`)、web search、X keyword/semantic search  
**Baseline known**: [openai/codex#7852](https://github.com/openai/codex/issues/7852)（2025-12 開；根因敘述=孫進程 orphan keep pipe open → codex 等 EOF）

---

## 結論（一句）

**沒有**比 #7852 仍 OPEN 更明確的「已修 / 已 merge 專修 PR / 已標安全版本」進展；相關 process-group / pipe 修補是**更早或旁支**，asyncio seccomp 與後續 orphan 議題**仍開**。

---

## (1) 修在路上 / 已 merge PR / 已釋出版本？

### #7852 本身（權威狀態，2026-07-12 查）

| 欄位 | 值 | 來源 |
|------|-----|------|
| State | **open**（`closed_at: null`） | GitHub API issue #7852 |
| Created | 2025-12-11 | 同上 |
| Updated | **2026-04-05**（最後事件：etraut-openai unlabeled） | API + timeline |
| Comments | 4 | API |
| Assignees / milestone | 無 | API |
| Linked PR with "7852" | **0**（search `repo:openai/codex is:pr 7852` → total 0） | GitHub search API |

**公開對話時間線：**
1. 2025-12-11 bot：疑似 duplicate of #7846 — [comment](https://github.com/openai/codex/issues/7852#issuecomment-3639660730)
2. 2025-12-11 **sayan-oai**（OpenAI collaborator）：Ubuntu 22 + Codex **v0.66 無法 repro**；並指出 `--dangerously-bypass-approvals-and-sandbox` 與 `--full-auto` 同時用應 error — [comment](https://github.com/openai/codex/issues/7852#issuecomment-3639964689)
3. 2025-12-11 **ghul0** 收斂 repro：`codex exec --full-auto` + `asyncio.to_thread` 卡死；**interactive** `--full-auto` 正常；純 `codex exec` 無 full-auto 正常 — [comment](https://github.com/openai/codex/issues/7852#issuecomment-3640857873)
4. 2026-01-19 **etraut-openai**：仍能 repro 嗎？請 `/feedback` 上傳 thread-id — [comment](https://github.com/openai/codex/issues/7852#issuecomment-3766867198)  
   → **之後無公開 reporter 回覆、無 maintainer「fixed」聲明、無 close。**

### 姊妹 issue #7846（同作者、process substitution / orphan grandchild）

| 欄位 | 值 | 來源 |
|------|-----|------|
| State | **closed** | API issue #7846 |
| Closed | 2025-12-11 | API |
| Close reason（非官方 fix） | Reporter 自關：*「I cannot reproduce it as well on codex **0.69**. It may be already fixed」* | [comment](https://github.com/openai/codex/issues/7846#issuecomment-3641143348) |

→ **不是** maintainer 標 FIXED；**不是** merge PR 關單。

### 相關已 merge（**早於或旁支 #7852，未在 #7852 上 close 連結**）

| PR | Merged | 內容摘要 | 與 #7852 關係 | URL |
|----|--------|----------|---------------|-----|
| **#5258** | **2025-11-08** | shell tool 自建 process group；timeout/ctrl-c 時 killpg | 修「timeout 只殺直接子進程、孫進程 keep PTY」類 hang；**早於 #7852 開立** | https://github.com/openai/codex/pull/5258 |
| **#6575** | **2025-11-13** | 孫進程共用 stdout/stderr 時 `consume_truncated_output` 等 pipe 關死 | **最接近** issue body 的 pipe-EOF / grandchild 敘事；etraut 在 #5229 指向此 PR | https://github.com/openai/codex/pull/6575 |
| **#12688** | **2026-02-24** | PTY 用 process group kill | 強化 kill 路徑，**未標 7852** | https://github.com/openai/codex/pull/12688 |
| **#8691** | **2026-01-08** | macOS inherited stdio **避免 setpgid**（防 SIGTTIN 假 hang） | 方向甚至與 #7852 假設「缺 setpgid」**部分相反**（stdio inherit 場景） | https://github.com/openai/codex/pull/8691 |
| **#22729** | **2026-05-27** | Linux sandbox 中斷：SIGTERM → wait → hard-kill process group | 清理 interrupt race；**非標 7852** | https://github.com/openai/codex/pull/22729 |
| **#25116** | **2026-05-29** | exec-server fs helper `kill_on_drop` | orphan helper 清理；窄 scope | https://github.com/openai/codex/pull/25116 |
| **#26734** | **2026-06-09** | non-TTY unified exec Ctrl-C → SIGINT process group | interrupt 路徑 | https://github.com/openai/codex/pull/26734 |

### 相關 **未 merge / 仍開**（比 #7852 更新或同族）

| ID | State | 日期 | 說明 | URL |
|----|-------|------|------|-----|
| **PR #6553** | closed **未 merge** | 2025-11 | killpg 殺 PTY 子樹；作者稱 #5258 未蓋 unified_exec | https://github.com/openai/codex/pull/6553 |
| **PR #10109** | closed **未 merge**（stale bot 2026-02-19 / 2026-04-26） | 2026-01 | landlock 允許 `sendto(NULL,0)` 解 asyncio self-pipe；**對齊 #7852 後續 asyncio.to_thread repro** | https://github.com/openai/codex/pull/10109 |
| **#9906** | **open** | 2026-01 | Async SQLite / asyncio hang under **no-network sandbox**（seccomp `sendto`） | https://github.com/openai/codex/issues/9906 |
| **#13821** | **open** | 2026-03 | app-server 達 `outputBytesCap` 後 stop drain → pipe back-pressure hang；作者寫 *distinct from but possibly related to #7852* | https://github.com/openai/codex/issues/13821 |
| **#15379** | **open** | 2026-03 | parent 退出後 child orphan（0.116.0）；etraut 問是否 regression | https://github.com/openai/codex/issues/15379 |
| **#18243** | **open** | 2026-04 | macOS workspace-write/read-only shell 失敗；danger-full-access 才行 | https://github.com/openai/codex/issues/18243 |
| **#19020** | **open** | 2026-04 | macOS 0.122.0 `apply_patch` 在 workspace-write hang、danger-full-access 5/5 OK | https://github.com/openai/codex/issues/19020 |
| **#21994** | **open** | 2026-05 | parent-kill 未清 process tree（Win Job Object / POSIX setpgid）；CLI **0.128.0** | https://github.com/openai/codex/issues/21994 |

### 已釋出「修掉 #7852」的版本？

**查不到。**  
- npm `@openai/codex` **latest = 0.144.1**（查於 2026-07-12 registry）；GitHub release 另有 `rust-v0.144.1`（2026-07-09）、`0.145.0-alpha.4`（2026-07-11）。  
- 無 release notes / changelog 條目稱 closes #7852（repo root CHANGELOG 幾乎空；無 7852 字樣）。  
- **不能**從「0.144 仍開 #7852」推論「0.66 起全壞」——只能說 **issue 未關閉、無官方 safe-range**。

---

## (2) X 上開發者更好的繞法？

### OpenAI 官方帳（@OpenAIDevs / @OpenAI / codex 員工）

**查不到**針對 #7852 / pipe deadlock / setpgid / workspace-write 命令卡死的官方 workaround 貼文。  
抽樣：sandbox 產品文（Windows sandbox 2026-05）、產品功能，**無**此 bug 的修補/版本公告。

### 使用者/開發者 X（相關但**不等於 #7852 官方繞法**）

| 日期 | 帳號 | 內容摘要 | 是否優於「避開多進程管線」 | URL |
|------|------|----------|---------------------------|-----|
| 2026-05-31 | @madmaxbr5 | sandbox 下 agent 以為殺不掉 stuck process；沒有 inspect/kill bash 的便利 | 抱怨，**無具體繞法** | https://x.com/madmaxbr5/status/2061049520046088676 |
| 2026-04-23 | @MrOcelot1976 | 0.124-alpha2 bwrap loopback 權限 → **退回 0.123** | 不同 bug；downgrade 僅限該版 | https://x.com/MrOcelot1976/status/2047417165566124474 |
| 2025-11-09 | @LeeLeepenkman | fork `--yolo3` 真正破 sandbox、不 timeout | 降安全面，非官方 | https://x.com/LeeLeepenkman/status/1987388584316584421 |
| 2025-11-24 | @mattshumer_ | alias：`--sandbox=danger-full-access --ask-for-approval=never` + network | 換 sandbox 等級，非修 pipe | https://x.com/mattshumer_/status/1992988943319445544 |
| 2026-06-30 | @puravidamoss | 關 terminal 留下 **16 個 orphaned Codex CLI** 高 CPU | 確認 orphan 類現象仍存在於 2026 中；**無繞法** | https://x.com/puravidamoss/status/2071982723603075361 |

### GitHub 上比「避開多進程管線」更具體、且可引用的繞法

| 繞法 | 來源 / 日期 | 備註 |
|------|-------------|------|
| 拿掉 `--full-auto`；只要 JSON 用 `--json` | #7852 issue body 2025-12 | 官方 issue 自帶；sayan 也質疑 full-auto+bypass 旗標組合 |
| **interactive** `codex --full-auto` 正常；卡死在 **`codex exec --full-auto`** | ghul0 comment 2025-12-11 | 若派工能改 interactive 路徑可試（我方 headless 可能不適用） |
| asyncio/no-network hang：**開 sandbox network**（`has_full_network_access` 時不裝 seccomp sendto 擋） | #9906 分析 2026-01 | 解 **asyncio.to_thread / aiosqlite** 類；**不保證** coreutils 管線 orphan-pipe |
| 走 **danger-full-access / `--dangerously-bypass-approvals-and-sandbox`** | #19020 5/5 vs workspace-write 0/5（2026-04）；#18243 | 安全降級；與 pipe-orphan 不同觸發也常被當 A/B |
| Parent 被 kill 後：自寫 **process-tree reaper**（Win PowerShell 遞迴 ParentProcessId） | #21994 2026-05 | 清 orphan，**不防** 執行中 pipe deadlock |
| PR 作者分支：cap 後繼續 drain stdout（#13821） | fitchmultz branch 2026-03 | **未確認 merge 進 openai/codex** |

**X 上沒有** OpenAI 工程師給出比我方 A′（拆多進程管線 / 單命令寫檔再讀）更精準、且針對 #7852 的繞法可引用。

---

## (3) 版本區間：安全 / 受影響？

| 版本 | 情報 | 來源 | 能否當「安全區間」 |
|------|------|------|-------------------|
| **0.66.0** | #7852 / #7846 回報版 | issue body | 受影響（reporter） |
| **0.69** | #7846 reporter **自己**說 process-sub 不再 repro | #7846 close comment | **僅**該觸發；**非** maintainer 認證 safe |
| **0.91.0** | #9906 asyncio/no-network hang 仍在 | #9906 | sandbox 下 async 仍可卡 |
| **0.116.0** | #15379 orphan after parent exit | #15379 | orphan 生命週期問題仍報 |
| **0.122.0** | #19020 workspace-write apply_patch hang | #19020 | workspace-write 路徑仍報 hang |
| **0.128.0** | #21994 parent-kill 不清樹 | #21994 | process tree 清理仍缺 |
| **0.144.1**（npm latest 查詢日） | 我方 session 仍見 shell 管線卡死（內部 evidence） | handoffs/P2DEBT-T4-…；非 OpenAI 關閉 #7852 | **無**「已修 7852」官方聲明 |
| **0.145.0-alpha.\*** | 存在 alpha release | GitHub releases 2026-07 | **查無** 7852 fix 說明 |

**結論：**  
- **官方未公布**「≥X 已修 #7852」或「Y–Z 受影響」。  
- 旁支 pipe/process-group 修補（#5258/#6575，2025-11）**早於** #7852 開立，卻**未能**讓 #7852 被 close → 要嘛 repro 不同、要嘛未完全覆蓋 sandbox/`exec --full-auto`/asyncio 路徑。  
- 2026 年仍有多開 issue 指向 sandbox hang / orphan / pipe，**不能**假設 0.144+ 安全。

---

## 情報可信度分層

| 等級 | 內容 |
|------|------|
| **硬證據** | #7852 API `state=open`；0 linked PR；PR 10109 未 merge；#9906/#15379/#21994 open |
| **強相關但非同 bug close** | #6575/#5258 已 merge（pipe/grandchild/process group） |
| **弱 / 旁證** | X 使用者 stuck/orphan 貼文；downgrade 0.124→0.123（bwrap，**另一 bug**） |
| **查無** | OpenAI 官方 X 繞法；changelog「fixed 7852」；safe version range |

---

## 對我方票 4 的含義（事實陳述，非指令）

- Upstream **未**把 #7852 標 FIXED；2026-04 後 issue 靜默。  
- 與我方 A′（避開多進程 shell 管線）同族的 mitigation 仍是公開 issue 上**最穩、零權限降級**的做法之一。  
- 若需「更好繞法」：**開 network** 只對 asyncio/seccomp 族；**danger-full-access** 可繞多種 sandbox hang 但放棄隔離；**interactive vs exec** 差異僅有 reporter 一筆。  
- 可選：在 #7852 補 macOS + `comm`/`sort` 管線 repro + `/feedback` thread-id（需使用者核可對外發言）——**目前查無 2026 新 maintainer 進度可等**。

---

## 查詢回執（可重跑）

```text
# 2026-07-12
curl -sL https://api.github.com/repos/openai/codex/issues/7852
# → "state":"open","closed_at":null,"updated_at":"2026-04-05T06:45:52Z"

curl -sL 'https://api.github.com/search/issues?q=repo:openai/codex+is:pr+7852'
# → total_count: 0

# X: keyword (sandbox|workspace-write|full-auto)+(deadlock|hang|orphan|pipe|setpgid)
#     + OpenAIDevs/codex staff — no official #7852 fix thread found
```

---

**ASSUMPTIONS_VERIFIED**: #7852 仍 open；無 PR 連結 7852；#10109/#9906 未落地；npm latest 0.144.1  
**TESTS_RUN**: N/A（純 recon，無本機 pytest）  
**FAILURES_SEEN**: GitHub search API 一度 403 rate limit（後改分批查詢成功）  
**SCOPE_CHANGES**: none  
**NUMERIC_OR_SCHEMA_IMPACT**: none  

STATUS: DONE
