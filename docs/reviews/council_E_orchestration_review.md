# Council Test E — multi-agent 設計對抗式審查（transcript）

> **日期**: 2026-05-31 | **委員會成員**: Claude (Opus, 綜合者) + Codex (GPT-5.5, 對抗式審查者)
> **審查對象**: `docs/MULTI_AGENT_ORCHESTRATION.md` + `AGENTS.md`「執行任務時」合約
> **目的**: 固化成 bootstrap 前，讓對方模型挑設計的洞。本檔保留**原始輸出 + Claude 評估**，供使用者稽核我有無曲解。

---

## 第一部分：Codex 原始批評（逐字，未經 Claude 編輯）

> 完整原文亦存於 `/tmp/council_E_codex.txt`。

1. [高] Claude 同時當 SPEC 作者與驗收者 → 錯誤假設會被制度化；跨模型 review 只在 SPEC freeze 前，沒覆蓋實作後 diff。修法：高風險任務加「實作後 adversarial diff review」，審 `git diff + SPEC + 測試結果`。
2. [高] `HANDOFF.md` 是共享可變單點 → 最後寫入者覆蓋前者、丟決策、stale。修法：append-only `handoffs/YYYYMMDD-task-id.md` 或 `logs/agent_events.jsonl`；根 HANDOFF 只當索引。
3. [高] scope 合約太死 → 真 bug（根因在 caller/fixture/config）被逼成 BLOCKED 或局部假修。修法：SPEC 定義「允許探索範圍」vs「需升級範圍」，允許 proposed scope expansion（附證據），不直接改超界檔。
4. [高] 驗收偏結果快照、缺決策可審計 → 漏掉過程中採用過但沒進 diff 的假設、被跳過的失敗、被替換的測試。修法：執行端輸出結構化 `ASSUMPTIONS_VERIFIED / TESTS_RUN / FAILURES_SEEN / SCOPE_CHANGES / NUMERIC_OR_SCHEMA_IMPACT`。
5. [高] `--force` / `--dangerously-skip-permissions` 當常規，安全靠 prompt → data_cache 不可刪/commit 卻無實體防線。修法：每個執行端包 runner，禁 `rm -rf data_cache`/git history rewrite/force push/改 .git，dispatch 前後記錄 `git status --porcelain`。
6. [中] 「小任務可無 SPEC」與 AGENTS「必讀指定 SPEC」打架。修法：定義 `INLINE_TASK_CONTRACT`（scope/驗收命令/允許檔/禁止事項），AGENTS 加「若標記 SMALL_INLINE 則 SPEC 可省」。
7. [中] debug ≤3 輪無可操作定義（什麼算一輪/同一失敗）。修法：iteration =「一次假設 + 一組改動 + 一次驗證」；BLOCKED 須列三輪 hypothesis/changed files/test output。
8. [中] gate 靠弱 grep → 抓不到 `import api.x`、動態 import、schema drift、cache 污染。修法：腳本化 gate（AST import checker、forbidden path、schema snapshot、numeric regression、data_cache dirty check）。
9. [中] 多 agent 並行無 worktree 隔離 → diff 混在一起、HANDOFF 互蓋。修法：每派工獨立 branch/worktree，task id 對應 branch，只讀該 branch 相對 base 的 diff。
10. [中] resume 脆弱：`--last` 並行時接錯 session；Cursor 重發失去狀態。修法：resume 指定 session id/task id/base commit/diff hash；不支援則寫 task-local `STATE.md`。
11. [中] 成本優化進核心流程但品質降級條件不夠硬；cursor/agy T-D 未驗卻已列為可用溢出。修法：每 agent 能力矩陣 + 允許任務類型；未過 T-D 只能 read-only review。
12. [低] 「最後更新 HANDOFF」與唯讀/審查任務衝突。修法：AGENTS 加例外，read-only 時輸出 `HANDOFF_NOT_UPDATED: <原因>`。

---

## 第二部分：Claude 的逐條評估（綜合者）

標記：✅採納　🔶保留/降級　❌不同意　🔬本次 session 已實證

| # | Codex 嚴重度 | Claude 評估 | 理由 |
|---|---|---|---|
| 1 | 高 | ✅ 採納（限高風險） | 真缺口：我同時作者+驗收。但「每個任務都加 post-diff review」對中任務太貴 → 只對高風險 / 數值 / schema 任務做 |
| 2 | 高 | ✅✅ 採納 🔬 | **本 session 已實證**：codex 三次覆蓋 HANDOFF，我每次 `git checkout` 還原。append-only + 根索引是對的 |
| 3 | 高 | ✅ 採納（守住人為關卡） | 同意 scope 太死。但「允許探索」不可變成執行端自我擴權 → 改動超界仍須 Claude/使用者核准，執行端只能「提案 + 證據」 |
| 4 | 高 | ✅ 採納（便宜高值） | 結構化收尾報告補上「讀摘要不讀全文」的盲點，且機器可掃，成本低 |
| 5 | 高 | ✅✅ 最優先 🔬 | **對量化專案最危險**：data_cache 不可刪/commit 卻靠 prompt 自律。最低限度先做 git preflight/postflight + denylist，完整 sandbox 後續 |
| 6 | 中 | ✅ 採納（易修） | 確實自相矛盾，加 SMALL_INLINE 標記即可 |
| 7 | 中 | ✅ 採納（易修） | iteration 定義要可操作，否則 ≤3 輪沒意義 |
| 8 | 中 | 🔶 原則採納、實作分期 | `grep "from api\."` 確實漏 `import api`；先把 gate 腳本化（含修正 grep），完整 AST checker 屬 V2/團隊規模再做 |
| 9 | 中 | 🔶 降級到「並行時才需要」 | 目前單執行端序列跑，worktree 隔離是 cursor/agy 上線並行後的必需，非當下 |
| 10 | 中 | ✅ 採納（並行前提下） | `--last` 並行會接錯，確實。序列單任務目前可用，但要寫進「並行須 pin session id」 |
| 11 | 中 | ✅✅ 採納 🔬 | **正中使用者疑慮**：cursor/agy 未過 T-D 就被列為可用。改成「未過 T-D 只能 read-only」 |
| 12 | 低 | ✅ 採納（易修） 🔬 | **本 session 已實證**：codex 在唯讀任務正確地沒更新 HANDOFF，但合約字面要求更新 → 加例外 + `HANDOFF_NOT_UPDATED` |

### Claude 與 Codex 的分歧 / 補充
- **分歧（強度）**：Codex 傾向一次到位（runner sandbox、AST checker、worktree 自動化）。我認為這是**團隊 / V2-V3 規模**的正解，**solo-dev V1 現在**應分期：先做便宜高值的 #2/#4/#5(最低限)/#6/#7/#11/#12，重工程的 #8/#9 等並行執行真的發生再做。否則為還沒出現的問題過度建設。
- **我最在意的兩條**：#5（data_cache 實體防線，量化資料安全）與 #2（HANDOFF 競態，已實證）。
- **委員會機制本身的驗證**：codex 找到的 #2/#5/#10/#12 都是**我們這次 session 真實踩到或觀察到**的，不是泛泛而談 → 證明跨模型思辨確實補了我的盲點，不是橡皮圖章。

---

## 第三部分：行動（固化 bootstrap 前先補）
**現在就改（便宜高值）**：#2 HANDOFF append-only+索引、#4 結構化收尾報告、#5 最低限 git preflight/postflight+denylist、#6 SMALL_INLINE、#7 iteration 定義、#11 未過 T-D 只能 read-only、#12 HANDOFF 例外。
**分期延後（並行/團隊規模再做）**：#1 post-diff review（先限高風險）、#8 完整 AST gate、#9 worktree 隔離、#10 精準 resume（先記文件提醒）。

### ✅ 已完成（2026-05-31）
- #2：建 `handoffs/`（append-only per-task）+ README；合約改「不得覆蓋根 HANDOFF」。
- #4：執行合約加結構化收尾報告（ASSUMPTIONS_VERIFIED/TESTS_RUN/FAILURES_SEEN/SCOPE_CHANGES/NUMERIC_OR_SCHEMA_IMPACT）。
- #5：建 `scripts/agent_preflight.sh` + `agent_postflight.sh`（**檔案系統快照**比對，因 data_cache 被 gitignore，git 偵測不到——實測抓到的假設錯誤）；合約標明 yolo 非安全模式。
- #6 SMALL_INLINE、#7 iteration 定義、#11 未過 T-D 只能 read-only、#12 HANDOFF 例外 + `HANDOFF_NOT_UPDATED`：均寫入 AGENTS.md / .cursorrules / CLAUDE.md / 手冊。
- **踩坑實證**：postflight 初版用 `git status` 抓 data_cache → 因 gitignore 失效；改檔案系統快照後，模擬縮減測試正確 FAIL。
