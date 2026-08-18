# GAP-2a／2b TODO adversarial 審查 R10（codex）
審查標的：`docs/GAP2_MARGINAL_IC_TODO.md` DRAFT R4；SPEC R7 FROZEN＋AMENDMENTS A1-1..A1-6；task-id=`20260818-GAP2-X-REVIEW-R10`。
## Verdict：需修補後派工
## CODEX-R10-P2-01
**斷言**: Phase B4「測試＋Gate」小節仍有無參數 script 名稱殘留，未滿足 R10 V2 指定的 exact grep gate。
**碼證**: `grep -n 'mutation_probe_check.sh\`' docs/GAP2_MARGINAL_IC_TODO.md` → `247:- ... 含 \`mutation_probe_check.sh\` 三新檔路徑 ...`（rc=0）；TODO:32-35 的 §B B4→B5 列雖有三個完整 test path，但 TODO:246-247 Phase B4 只有 pointer／描述，未帶路徑。RECHECK：移除該 bare code-span 或在 Phase 小節逐字帶三個路徑後重跑同一 grep，預期 rc=1。
**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#52b446310ed8; scripts/mutation_probe_check.sh#03309f359005
[MINOR] 信心度=High；不阻 agent 追到 §B 執行，但會使 brief 指定機檢命中，且 Phase 小節不符合「含帶路徑／同文」收斂要求。
## 必答 1：Agent 可執行性
Task 1.0–5.1 均有檔案／函式、偽碼、邊界與驗證命令；唯一卡點是上列 B4 gate 文字殘留，非產品實作阻塞。
## 必答 2：義務覆蓋
逐條對照 D1–D7、D3′／D3″、§G 1–4、§V 24、§C 白名單（含 A1-4／A1-5）與 §N 四殘留：TODO:9-20、182-243、245-295 均有落點且方向一致；無漂移。
## 必答 3：批次獨立性／forward dependency
B1 無依賴；B2←B1；B3←B1/B2；B4←B1/B2/B3，且 Task 4.0 先於 4.1；B5←B4。Task 4.2 的契約增值與 orchestrator 同 commit，無未宣告 forward dependency。
## 必答 4：取巧面
未發現新的可跑綠但語意錯誤路徑；root OOS 注入、exact reason、persist 四形狀、golden sha、fit spy／預算 gate 與 24 條 mutation 已覆蓋主要取巧面。剩餘只是 B4 文字 gate。
## 必答 5：測試設計
V1：TODO:12、257、262 已明列 basic／CorrelationHeatmap 後／`section={report?.marginal_ic}`／頁面實掛載；V2：B1–B3 帶路徑且 B4 pointer 指 §B，但 TODO:247 觸發 finding；V3：TODO:220、226 exact `write_failed`、contract membership、mock `os.replace` 均齊。R8 抽核 U4、U6：persist 顯式 kwargs 與禁字串 grep 關閉均成立。
## 必答 6：可 Frozen？
目前不可 Frozen；BLOCKING 無，唯一待修 `CODEX-R10-P2-01`。移除 bare script 名稱／補 exact path 後重跑 template、crosscheck、completeness 與三家 review/stamp，即可再判可 Frozen。
## 被當成事實的未驗證假設（§0）
無新增未驗證假設；A1-6「例外類別只進 error log、不擴五鍵」與 Phase pointer 單一來源均已按文件語意核對。
ASSUMPTIONS_VERIFIED: r9 synth 三家 RECONCILE-STAMP APPROVED；V1 basic gating／props／page mount；V2 exact grep 唯一命中 TODO:247；V3 exact reason＋mock；R8 U4/U6；SPEC/TODO/A1-5/A1-6/registry 逐條對照。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`grep -n 'mutation_probe_check.sh\`' docs/GAP2_MARGINAL_IC_TODO.md` 命中 TODO:247 rc=0；`grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` no match rc=1（預期）；其餘 `nl`／`rg`／`sha256sum` 為唯讀核對。
FAILURES_SEEN: R10 V2 bare-name grep 命中 TODO:247；一次並行唯讀命令因 gate 將 roster 文字誤判 dispatch，改用等價唯讀命令後完成；無檔案變更。
SCOPE_CHANGES: 只新增本交件檔；未修改 SPEC／TODO／程式／測試／data_cache／根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none；只指出 Phase gate 文件文字／機檢殘留，未改產品數值或 schema。
HANDOFF_OUTPUT: `handoffs/20260818-gap2-todoadv-r10-codex.md`; family=codex; task-id=`20260818-GAP2-X-REVIEW-R10`。
STATUS: DONE
