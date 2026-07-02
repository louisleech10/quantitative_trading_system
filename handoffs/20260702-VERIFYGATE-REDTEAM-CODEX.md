# VERIFY_GATE 全系統紅隊 — Codex 實測版

SCOPE: commit `abeb9ff`; read `HANDOFF.md`, `CLAUDE.md`, `handoffs/20260702-VERIFYGATE-REDTEAM-CLAUDE.md`.
ISOLATION: `/tmp/verifygate-redteam.0mhhcd/{mini,mini2}` temp git repos; receipt/audit/ledger used `VERIFY_GATE_*` tmp paths except B2 default-path test inside temp repo. Real `.claude/gate/*`, `handoffs/run_receipts/`, `data_cache/` unchanged.
NOTE: B5 range debugging hit temp-fixture anomalies; conclusion below uses successful direct checker/hook runs plus workflow/source behavior, not the bad fixture output.

## A. 繞過面

| ID | 判定 | 實跑證據 | 結論 |
|---|---|---|---|
| A1 receipt 洗白 | BROKEN | `A1_strict rc=1 runtime_class 不足: helper_smoke vs mutation`; `A1_slow_word rc=1 helper_smoke vs requires_kline`; but `A1_vague rc=0` for `P0-FF-3 已驗綠燈 VERIFY:<fast-ok>` | 明確 mutation/慢測/node-id 會擋；模糊「已驗綠燈」因 scope/runtime 空洞可用無關快測洗白。 |
| A2 SUPERSEDED 洗白 | BOUNDARY | `A2_no_superseded rc=1 claim_fingerprint 衝突`; `A2_fake_superseded rc=0` with `SUPERSEDED:fake-id` | 衝突檢查有效；`SUPERSEDED` id 本身不驗真，適合作為「舊 claim 失效」標記，不可當新綠 provenance。 |
| A3 fenced/quote/偽 citation | BROKEN | `A3_fenced rc=0`; `A3_quote rc=0`; `A3_fake_attribution rc=0` for `Codex 檔案寫道「...已驗真紅」` | 引用豁免能走私「假的歸屬」。若 HANDOFF 用引用語氣承載驗收狀態，gate 不查出處檔是否真含該句。 |
| A4 非攔截 docs/include | BROKEN | `A4_docs_operational rc=0` for `docs/reviews/x.md: STATUS: DONE ... 已驗真紅`; B4 also `docs/roadmap_status rc=0` | pre-commit/CI 掃 docs，但 checker 對 `docs/*` 一律 `docs_spec -> discussion`，所以 docs 是 operational claim 走私通道。 |
| A5 audit+receipt 同步竄改 | BOUNDARY | After editing receipt runtime/node and updating audit hash: `A5_tamper_receipt_audit checker_rc=0`; `verify_audit_chain Summary: OK=2 TAMPER/MISSING=0` | 與文件誠實邊界一致：tamper-evident 非防惡意。同步改 receipt+audit 可完全通過。 |
| A6 env override | HOLDS + BROKEN(extra) | `GATE_DIR_OVERRIDE=tmp gate.sh` minted only tmp token; `.claude/gate/dispatch.token` absent; Task through `gate_check` `rc=2`. Extra: `Bash command="GATE_DIR_OVERRIDE=/tmp codex exec hello"` `rc=0`, while plain `codex exec hello` `rc=2` | `GATE_DIR_OVERRIDE` 不會讓 Task hook 接受 tmp token；但 Bash executor regex 漏掉 env-prefix `VAR=x codex ...`，是真 dispatch gate 繞過。 |
| A7 pending ledger fake close | HOLDS | Ledger open + hand-written close `receipt_id=fake-no-audit`; `A7_fake_close_open_pending rc=1 task P0-FF-3 有未結 pending p1`; `list-open` still prints p1 | B2 reducer 對 fake close 有效；若結合 A5 同步偽造 receipt/audit，仍回到 tamper 邊界。 |
| A8 `--no-verify` | BOUNDARY | Normal commit bad HANDOFF: `rc=1 operational claim 缺少 backing`; `git commit --no-verify` same staged bad HANDOFF: `rc=0` committed. Workflow file exists for push/PR `Verify Claim` | 本地 hook 可被 `--no-verify` 繞；CI 是設計後盾，但本次不能證明 GitHub 已真跑過。 |

## B. 過嚴/卡死面

| ID | 判定 | 實跑證據 | 結論 |
|---|---|---|---|
| B1 `REF:` 不吃路徑 | BROKEN | `B1_ref_path rc=1 receipt 不存在: handoffs` for `REF:handoffs/20260702-X.md` | 正則只抓到 slash 前 `handoffs`，合法引用 handoff path 會被誤解成 receipt id。需文件化或放寬 REF token。 |
| B2 receipt 須 tracked/staged | HOLDS(messaging) | Default receipt unstaged: `rc=1 receipt/log 未 tracked 或 staged`; after `git add handoffs/run_receipts .claude/gate/verify_audit.log`: `rc=0` | 行為合理；錯誤訊息可直接提示 `git add handoffs/run_receipts .claude/gate/verify_audit.log`。 |
| B3 同 receipt 重用 | HOLDS | Two compatible mutation claims using same receipt: `B3_reuse_same_receipt rc=0` | 合法重引用不會被擋。 |
| B4 docs 歷史敘述誤擋 | HOLDS but risky | `B4_docs_history rc=0`; `B4_docs_status rc=0` | 不過嚴；反而過鬆，docs operational wording 也放行，與 A4 同洞。 |
| B5 CI 舊 range 卡死 | BOUNDARY | Workflow runs checker on changed `HANDOFF.md`, `handoffs/*.md`, `docs/*.md`. Source `_git_range_files` only uses range to select file names; checker reads current checkout content. Temp range replay had fixture anomaly, not used as hard verdict. | CI 不逐 commit 掃歷史 blob；若 head 文件仍含舊假 claim 會卡，若已清掉則不會。是否卡死取決於 head 內容，不是 range 內曾出現過什麼。 |
| B6 checker/hook 壞掉死鎖 | BOUNDARY | `gate_check` bad JSON `rc=0` fail-open; `verify_pretooluse` missing checker `rc=2 [VERIFY-PRETOOLUSE] python/checker 缺失，fail-closed`; `verify_hooks_health` missing checker `rc=1` | gate_check 有避免鎖死的 fail-open；PreToolUse/checker 缺失會鎖 operational handoff edits。需要明確 emergency disable/repair procedure。 |

## Extra Findings

1. `gate_check.sh` Bash detector misses env-prefix executor commands: `VAR=x codex ...` returned `rc=0`. This is higher priority than `GATE_DIR_OVERRIDE` itself.
2. `VERIFY_GATE_RECEIPTS_DIR` / `VERIFY_GATE_AUDIT_LOG` are honored by checker, and `_is_test_isolation()` skips tracked/staged checks when set. Source-level risk: git hooks inherit env, so a user can likely run `VERIFY_GATE_RECEIPTS_DIR=/tmp/fake VERIFY_GATE_AUDIT_LOG=/tmp/fake git commit ...` unless hooks scrub these vars. I attempted a live hook repro, but temp fixture began returning silent `rc=2`; not counted as completed实測.
3. Unknown polarity words (`驗證通過`, `測試綠`, `runtime綠`) are only WARN candidates in source, not hard blockers unless captured by strong regex. Live repro was inconclusive due same temp fixture issue; source risk remains.

## Top Fixes

1. Close dispatch gate env-prefix hole: parse Bash command tokens or allow leading `env/VAR=...` before `codex|cursor-agent|agy|claude`.
2. Stop docs walkaround: either scan selected docs operational sections as operational, or require `VERIFY-EXEMPT`/discussion marker for docs claims containing `STATUS/DONE/已驗/真紅/通過`.
3. Fix A1 vague receipt wash: require scope/runtime for root HANDOFF operational success claims, or reject `已驗/綠燈` with VERIFY when claim has empty scope and non-static receipt.

ASSUMPTIONS_VERIFIED: Temp git repos isolated; fast receipt classified `helper_smoke`; mutation receipt classified `mutation_runtime`; real repo trust dirs/data_cache status unchanged before report write.
TESTS_RUN: Direct checker/hook/git commands in `/tmp/verifygate-redteam.0mhhcd`; key rc values listed per row; no project pytest suite run.
FAILURES_SEEN: A5 first tamper script missed env export then reran successfully; B5 range replay and Extra X1/X2 hit temp-fixture silent `rc=2`, excluded from hard verdicts.
SCOPE_CHANGES: none; only added this handoff report.
NUMERIC_OR_SCHEMA_IMPACT: none.
結論1: 最該修前 3 = Bash env-prefix dispatch 繞過、docs operational claim 放行、A1 模糊 scope/runtime receipt 洗白。
結論2: 淨判斷 = 不是過嚴，仍有洞需緊；少數摩擦集中在 REF path 與 receipt staging 訊息。
STATUS: DONE
