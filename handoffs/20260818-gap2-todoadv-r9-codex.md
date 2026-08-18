# GAP-2a／2b TODO adversarial 審查 R9（codex）
審查標的：`docs/GAP2_MARGINAL_IC_TODO.md` DRAFT R3；只讀審查，未修改 SPEC／TODO／程式／測試；task-id=`20260818-GAP2-X-REVIEW-R9`。
前置：R8 synth 三家 RECONCILE-STAMP 均 APPROVED；`template_check` rc=0、`todo_spec_crosscheck` rc=0、現況 `ic_wiring_check` rc=0。
## Verdict：需修補後派工（不可 Frozen）
## CODEX-R9-P1-01
**斷言**: B1 Phase Gate 仍含無參數 `bash scripts/mutation_probe_check.sh`，按正式用法必然失敗。 **碼證**: `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:109-110`；`bash scripts/mutation_probe_check.sh` 輸出 `用法: ... <test_path>...`、rc=1；同檔 B1→B2 已明列兩個 test path。 **來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358; scripts/mutation_probe_check.sh#03309f359005。 [MAJOR] 信心度=High；B1 收尾先被硬 gate 擋住。修法：Phase B1 Gate 也明列 `tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py`，並重跑該 gate。
## CODEX-R9-P1-02
**斷言**: B5「IC 頁面可見」無法在現行 scope 完成：`MarginalICTable` 沒有被現有 IC 結果頁匯入或渲染。 **碼證**: TODO:251-262 要求新增 table 並接入 deep 區塊；`frontend/src/app/ic-analysis/page.tsx:814-916` 的 deep JSX 無該元件；`rg -n 'MarginalICTable' frontend/src` 無命中；TODO:258 的既有檔清單只有 `types.ts`／store／panel 加新元件，未列 page 容器。 **來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358; frontend/src/app/ic-analysis/page.tsx#77341721b6f0。 [MAJOR][SPEC 義務側] 信心度=High；新檔會成孤兒，頁面義務不成立。修法：A1-4／Task 5.1 明列 `frontend/src/app/ic-analysis/page.tsx`、精確插入點與資料來源（base `report?.marginal_ic`），並納入相應 gate。
## CODEX-R9-P1-03
**斷言**: `write_failed:<ExceptionClass>` 與 survivor contract 的 reason SoT `write_failed` 不一致，且違反「orchestrator 一律由契約取 reason」的同段要求。 **碼證**: TODO:44-47 將 `survivor_output` reasons 唯一列為 `identity_missing, write_failed`；TODO:206 要求由 `load_survivor_contract()["reasons"]` 取值；TODO:220 卻要求 `f"write_failed:{type(exc).__name__}"`。 **來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358; docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d。 [MAJOR] 信心度=High；嚴格 validator／reason-membership 檢查會拒絕寫檔失敗形狀，放寬則 SoT 不再封閉。修法：二選一並寫入契約／測試：固定輸出 `write_failed` 並將例外類別只寫 log，或正式定義可驗證的結構化錯誤欄／pattern；不可由實作端自行猜。
§1 必查：1 矛盾／互斥＝有（P1-01～03）；2 端到端漏項＝有（B5 page 接線）；3 不可測＝有（B1 gate、write_failed enum）；4 quant 假設＝無新的方向漂移（root OOS、fit spy、預算 gate 已寫回）；5 過度工程＝無；6 OOM／並行＝既有計數 spy／原子寫要求已覆蓋；7 cache＝顯式 persist kwargs／cache 時序已對齊；8 API／型別＝B5 page scope 未閉合；9 測試＝P1-01，U6 grep 已關閉；10 Agent 可執行性＝P1-01～03；11 短命工＝無。
必答1 Agent 可執行性：B1 gate、B5 page 接線、write_failed reason 決策會卡；其餘 Task 的檔案／函式／驗證大致足夠。
必答2 義務覆蓋：D1–D7／D3′／D3″、§G、§V、§N 多數有落點；B5「可見」義務缺 page scope，survivor write-failure reason 有語意漂移。
必答3 批次獨立性：4.0→4.1 順序、U2/U3/U4/U5/U7/U8/U10 已對齊；B2/B3/B4 新測試檔路徑明列；B1 Phase Gate 殘留無 path，B5 依賴缺 page。
必答4 取巧面：若接受 dynamic `write_failed:*` 可繞過 reason SoT；table orphan 可讓 build／component test 綠但產品頁永遠不顯示；budget spy／root oracle 取巧面已補。
必答5 測試設計：U6 同一 grep 無命中（rc=1）；`fit_projection` spy 的 module-level patch 在實作缺席下未能 runtime 驗證；xsec exact、root oracle、persist cold-call、case_id/report_ref、四形狀與各 `test_mutation_*` 名已明列；B1 command 仍錯。
必答6 可以 Frozen？不可以。BLOCKING／MAJOR 清單：`CODEX-R9-P1-01`、`CODEX-R9-P1-02`（SPEC 義務側）、`CODEX-R9-P1-03`；修補後需重跑 template/crosscheck、相關 gates 與三家 review/stamp。
ASSUMPTIONS_VERIFIED: R8 三家 stamp APPROVED；U6 grep 無命中且 rc=1；root annotate 呼叫點／stage7 呼叫點已由 rg 核對；現行 IC deep page 無 MarginalICTable；B1 mutation checker 無參數 rc=1；fit spy 尚未因實作不存在而 runtime 驗證。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`bash scripts/ic_wiring_check.sh` PASS rc=0；`grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` no match rc=1；`bash scripts/mutation_probe_check.sh` usage rc=1；指定 `bash scripts/completeness_check.sh --single handoffs/20260818-gap2-todoadv-r9-codex.md --family codex` 被 PreToolUse gate 擋在腳本前，未取得 checker rc；其餘為 `nl`／`rg`／`shasum` read-only probes。
FAILURES_SEEN: `bash scripts/mutation_probe_check.sh` 無參數 rc=1（TODO 殘留）；U6 指定 grep rc=1 是預期「無命中」證據，非 review 失敗；completeness 命令因本輪 OPEN debt 被 gate 擋下，非格式驗證結果。
SCOPE_CHANGES: 只新增本交件檔；未修改 SPEC／TODO／程式／測試／data_cache；提出 page whitelist 與 reason schema 修補建議，未自行越界修改。
NUMERIC_OR_SCHEMA_IMPACT: 未改產品數值／輸出；finding 指出 B5 page scope 與 survivor `write_failed` reason schema 需裁決。
HANDOFF_OUTPUT: `handoffs/20260818-gap2-todoadv-r9-codex.md`; family=codex; task-id=`20260818-GAP2-X-REVIEW-R9`。
STATUS: BLOCKED — completeness_check 被本輪 OPEN debt 的 PreToolUse gate 擋下；需治理 owner 銷帳後以同一參數重跑。
