# VERDICTGATE-X R11 收票審（family=codex，task-id=20260912-VERDICTGATE-X-REVIEW-R11）
範圍：依 closeout brief 審 C-4、E-022–E-025、E-1–E-7 與 B1–B4 close verdict；未改 code、tracked 檔或 data_cache。
## CODEX-R11-P1-01
**斷言**: C-4 的「本批已有任一 round_open 即不重驗」讓 closure round 可成為該批第一輪；其後 `--impl-self` 會在前批仍有 blocked ID 時沿同一豁免拿 token。
**碼證**: `committee_run.sh:433-438` 與 `gate.sh:945-960` 對 `brief-kind=closure` 都跳過 `verdictgate_check`；`verdictgate_check.sh:35-53` 對同批任一 `committee_round_open` 直接 rc=0，且 `gate.sh:1019-1042` 隨後寫 token。實跑隔離 probe：先置 `ROOT-B1-REVIEW-R1` codex blocked 且缺 roster/output，`bash scripts/verdictgate_check.sh ROOT 2 ROOT-B1-REVIEW` → rc=1；只追加 `ROOT-B2-CLOSURE-R1` round_open 後同命令 → rc=0，輸出「本批已有審查輪」。
**來源摘要**: scripts/verdictgate_check.sh#e2bd25b73715; scripts/committee_run.sh#34a7ad787de0; scripts/gate.sh#ebc27429b84f; tests/governance/test_verdictgate_p2.py#a6d7a405aec6
[MAJOR] 信心度=High；修法需把 closure 例外限定為同批已有通過非-closure review 的 entered marker，並補 closure-first→`--impl-self` 不發 token 的 regression test。
## CODEX-R11-P2-02
**斷言**: E-022、E-023、E-024 的 registry reason 含可執行但語義不指向所稱 enforcement 的行號；E-025 的分類與兩個行號均正確。
**碼證**: E-022 `verdictgate_check.sh:28` 是 usage guard，實際 checker body 是 `:35-53`、caller 是 `gate.sh:959`；E-023 `gate.sh:951` 是 task-id regex parser，實際 `verdictgate_check` call 是 `:959`；E-024 `ticket_batch_check.sh:49` 是 `--msg)` case，`--push-range)` 在 `:88`、`gov_check.sh` caller 在 `:309`。E-022/E-024 的 exemption 三段與 E-023/E-025 的 producer 形態分類皆成立。`bash scripts/gen_fact_key_blocks.sh --check` → rc=0，只證明格式/行可定位，未證明語義對位。
**來源摘要**: docs/GOV_ENFORCEMENT_REGISTRY.md#8124ffba100b; scripts/fact_keys.json#4e39cb2df19a; scripts/gate.sh#ebc27429b84f; scripts/ticket_batch_check.sh#7e3422da39eb; scripts/gov_check.sh#07fa2b2ceb64
[MINOR] 信心度=High；更正 E-022/E-023/E-024 的 cited line，並讓 registry check 覆蓋 claimed enforcement line 的語義對位。
必答回覆：
1. loophole：反例已實跑；closure-first 使 checker rc=0，且 gate 的 closure 分支位於 token write 前，因此「先經 gate.sh verdictgate」不成立。
2. C-4 literal mismatch：要求走 FROZEN SPEC 修訂程序；closeout/HANDOFF 可記錄內修，但不能在未補 entered precondition 前宣稱語義已收斂。
3. E-022 豁免（:612 正確、:28 錯）；E-023 產出端（分類正確、:951 錯）；E-024 豁免（:41 正確、:49 錯）；E-025 產出端（:40、debt_clear:584 正確）。
4. E-5 重跑 `bash handoffs/20260911-verdictgate-e5-probe.sh` → rc=0、`ORDER-ALWAYS-HOLDS`；amend -m、amend --no-edit、rebase 均使 ticket_commit append 在 token 後，4/5 列 token_fresh=false（mtime 回撥模擬過期）。立場：append 序第二層無增量，mtime 保留。E-1/E-2/E-7 的 user-ruling 仍有效；E-3/E-6 仍為 needs-research；E-4 依前一輪 SPLITUNIFY 補裁決處置，理由有效。
5. 不能 close：B1–B4 tri-party review／原提出方 close 已具備，但 P1 bypass 尚未解決；P2 registry citation 亦須修正。
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF、CLAUDE、closeout brief、SPEC v9、TODO v3、template、R10 synth；C-4 closure-first 反例、E-5 三序列 probe、E-022–E-025 行號與 registry check 均有實跑證據。
TESTS_RUN: `bash handoffs/20260911-verdictgate-e5-probe.sh` rc=0；closure-first checker probe rc=0（before=1/after=0）；`venv/bin/python -m pytest -q tests/governance/test_verdictgate_p2.py::test_check_batch_already_entered_skips_prev_verdicts` 1 passed；`...test_verdictgate_p1.py::test_12_closed_id_in_legacy_round_expected_output_accepted` 1 passed；`bash scripts/gen_fact_key_blocks.sh --check` rc=0；未跑 governance 全套。
FAILURES_SEEN: 一次隔離 gate probe 因 fixture 缺 `brief_conformance_check.sh`、修補後又因 probe brief 寫入 literal `\\n` 失敗；均為 probe harness 輸入/依賴問題，未作產品結論。產品 checker 反例獨立成功。
SCOPE_CHANGES: none（唯讀審查；只新增本 handoff）。
NUMERIC_OR_SCHEMA_IMPACT: none；未改產品數值、schema 或輸出大小。
OUTPUT_ARTIFACT: handoffs/20260912-verdictgate-x-review-r11-codex.md
TMP_CLEANUP: 已將精確核對的 verdictgate-cleanup.N5HOzJ、vg-r11-probe.7tWwNE、vg-r11-impl.RIRmOQ 移至 /private/tmp/.Trash/（可恢復）；原 workdir 已清空，/private/tmp/claude-501 保留。
VERDICT: blocked
BLOCKED-BY: CODEX-R11-P1-01,CODEX-R11-P2-02
CLOSED:
STATUS: DONE

<!-- 主委正規化（2026-09-12）：原 CLOSED 列 R10 三條 ID；register-output 拒收——主委 brief 之 task-id 用了 20260912 日期前綴 ⇒ root 由 `20260911-verdictgate` 變成 `20260912-verdictgate`，語料不含 R10 產出（同家同 ID 確實存在於 handoffs/20260911-verdictgate-x-review-r10-codex.md）。該三條於 TODO v3 凍結（R11–R13 戳記 APPROVED）時已處置，且 X 層不進 verdictgate；移除後重註冊，語意不變。教訓登記 HANDOFF：task-id 日期前綴屬 root，同票跨日須沿用首日前綴。 -->
