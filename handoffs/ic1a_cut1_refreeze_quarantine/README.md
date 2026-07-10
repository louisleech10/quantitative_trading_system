# 1a cut1 golden baseline 隔離區(2026-07-11)

- 內容物=Grok B2(2026-07-11 00:10)越界重凍的兩份 baseline json(codex B2 review FINDING #11:宣告雜湊與實際失配;自證型凍結不可信)。
- 原始凍結(2026-07-09)為 gitignored 未追蹤檔,`git restore` 無效,本地原始內容已滅失——此為「golden 產物未入版/無外部雜湊」的制度缺口實例,併入 RULE-PROPOSAL-ORCH-SELF-ARTIFACT 詰問素材。
- 現況:1a golden 測試依既有 skip-if-absent 設計轉 SKIP(誠實狀態,非假綠)。
- B5 義務:於 pre-B2 commit(c0b29ac)開 git worktree 重跑 1a 凍結程序重生 old baseline,與 `baseline_meta.json` 宣告雜湊比對一致後放回;B5 再依 §G 凍結 new。
