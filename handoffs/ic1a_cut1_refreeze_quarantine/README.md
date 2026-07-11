# 1a cut1 golden baseline 隔離區(2026-07-11;R2 更新)

- 內容物=Grok B2(2026-07-11 00:10)越界重凍的兩份 baseline json(codex B2 review FINDING #11:宣告雜湊與實際失配;自證型凍結不可信)。
- 原始凍結(2026-07-09)為 gitignored 未追蹤檔,git restore 無效,本地原始內容已滅失——「golden 產物未入版/無外部雜湊」制度缺口實例,已併入 RULE-PROPOSAL-ORCH-SELF-ARTIFACT。
- **後續處置(已完成,2026-07-11)**:歷史證據由編排端 worktree 雙 commit 重生歸檔於 handoffs/ic1a_cut1_original_regen/(含 provenance);現行 tests/golden/ic_phase1_1a_cut1/ 已依 1e+1b 以修正後 canonical 腳本重凍兩態,golden 測試回綠(2 passed)。本目錄僅存審計痕跡。
