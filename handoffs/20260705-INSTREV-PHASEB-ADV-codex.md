ID: ADV-CODEX-1
Verdict: BLOCKING
會怎麼失敗: U-14 要求 pre-commit 對 staged md 移尾隨空白後 `git add` 回 index；具體反例：`HANDOFF.md` 先 staged `- align 已驗真紅  `，working tree 再改成 `- clean note`，pre-commit 若對工作樹 `sed -i` 後 `git add HANDOFF.md`，會把未 staged 的 `clean note` 一起納入 commit，既有基線 `tests/governance/test_verify_gate_b3.py::test_git_hook_rejects_partial_stage_fake_claim` 代表的 partial-stage 防線被污染，假 claim 可被工作樹覆蓋而放行。
建議修法: U-14 SPEC/TODO 改成只操作 index blob（temp checkout staged blob + `git update-index --cacheinfo` 或等價 index-only 流程），並新增「staged 假 claim + working tree clean + 尾隨空白」回歸測試。

ID: ADV-CODEX-2
Verdict: MAJOR
會怎麼失敗: U-14 宣稱 fenced code block 內尾隨空白「無語義」不成立；具體反例：Markdown 行尾兩個空白表示 hard line break，docs 範例、表格、code fence 內的逐字內容也可能需要保留尾端空白。實作若全域移除 `[ \t]+$`，commit 會靜默改變文件渲染或範例 byte 內容，而 TODO 的驗證只要求「除尾隨空白外位元組不變」，等於把有語義的尾隨空白先定義成無語義，測試無法證偽。
建議修法: 將 auto-fix 限縮為明確安全的治理交接 prose 行，或改為提示/拒絕而非自動改；若仍 auto-fix，至少排除 fenced code、表格與 Markdown hard-break 兩空白行並加測。

ID: ADV-CODEX-3
Verdict: BLOCKING
會怎麼失敗: U-15 說 dispatch wrapper 不得自動生成會覆蓋既有檔的 output，但驗證只檢查有產生 `handoffs/*-RESULT.md`，沒有預先建立同名檔再跑第二次；具體反例：同日兩次 `scripts/dispatch.sh --intent "phase b impl" ...` 都生成 `20260705-phase-b-impl` 與 `handoffs/20260705-phase-b-impl-RESULT.md`，後續執行端按 output 路徑寫檔時覆寫前一份 handoff，gate.sh 目前只記 pending output，不會替 wrapper 擋碰撞。
建議修法: SPEC/TODO 要求 wrapper 在 output 已存在或 task-id 已出現在 audit 時 fail closed 或加唯一 suffix，並新增「同 intent 連跑兩次/預建 output 檔」測試。

ID: ADV-CODEX-4
Verdict: MAJOR
會怎麼失敗: U-12 明列「TTL 過期 token 走同 DENY 路徑亦記錄」，但驗證只餵無 token 的 `{"tool_name":"Task"}` 與放行案例；具體反例：實作者只在 token 不存在分支 append audit，過期 token 分支仍 exit 2 但不寫 `gate_deny`，所有指定測試仍可能綠，稽核漏掉最常見的 stale-token DENY。
建議修法: 在 `test_gate_deny_audit.py` 明確建立過期 `dispatch.token`（mtime > TTL）後觸發 Task，斷言 exit 2 且 audit 尾行 reason/kind/tool 正確。

ID: ADV-CODEX-5
Verdict: MAJOR
會怎麼失敗: U-12 要求 audit append best-effort 且寫失敗不影響 exit 2，但 TODO 沒規定如何屏蔽 shell redirection/mkdir 錯誤；具體反例：`GATE_DIR_OVERRIDE=/dev/null/x` 時 `mkdir -p` 或 `>> "${GATE_DIR}/audit.log"` 失敗，若實作在 `set -e`、subshell、或未包 `|| true` 的 helper 中追加，可能提前 exit 1 或噴非預期錯誤，PreToolUse 看到的不是既有 fail-closed exit 2 語義。已嘗試找「audit 寫失敗導致 fail-open(0)」反例，按現腳本無 `set -e` 不會自然變 0，但 SPEC 未把 exit 2 包裝成測試保證。
建議修法: 明寫 append helper 必須 `mkdir -p ... 2>/dev/null || true`、append redirection 整體 `|| true`，並新增不可寫/非法 GATE_DIR_OVERRIDE 仍 exit 2 的測試。

ID: ADV-CODEX-6
Verdict: MAJOR
會怎麼失敗: U-15 wrapper 驗證沒有釘住「所有既有參數透傳」與「gate.sh 仍是唯一裁決者」；具體反例：wrapper 自己過濾未知參數或重排參數後吞掉 `--spec/--todo/--manifest/--reconcile`，`bash scripts/dispatch.sh --intent x --risk high --unknown y ...` 可能不再由 gate.sh 報 `ERROR: 未預期參數`，也可能讓高風險 SPEC 派工少跑 template/reconcile 檢查；現有驗證只看自動 task-id/output 是否出現，無法抓這種 wrapper 越權。
建議修法: 新增 wrapper 測試：未知參數必須得到 gate.sh 的未預期參數錯誤；高風險帶 `--spec/--todo` 時仍觸發 gate.sh template/reconcile 檢查。

ID: ADV-CODEX-7
Verdict: MINOR
會怎麼失敗: U-9 邊界文字說「錨點行大小寫/全半形括號變體」但實際 regex 只含 `現行分工\(`，且現檔是 ASCII `(`；若未來人工改成全形 `現行分工（...）`，SPEC 文字暗示應支援但機檢會假紅。這不是當前立即失敗，因 `grep` 實檔目前只有 L37 被錨點命中。
建議修法: 要嘛刪掉「全半形括號變體」承諾，要嘛 regex 改為 `現行分工[（(]` 並加一個 fixture 測試。

ID: ADV-CODEX-8
Verdict: MINOR
會怎麼失敗: U-14 checker 提示驗證只 grep `VERIFY-EXEMPT`，未要求 violation 數量、exit code 與原本 stderr 結構完全不變；具體反例：實作把所有 violation 都附同一段提示、或把原 `file:line: message` 順序改掉，既有 parser/人讀流程可能退化，但新測仍因含 `VERIFY-EXEMPT` 而綠。
建議修法: 測試應斷言缺 backing violation 仍為 exit 1、原 `file:line: operational claim 缺少...` 行仍存在且 violation 數量不變，提示只追加於該類 message 後。

Verdict: REJECT
