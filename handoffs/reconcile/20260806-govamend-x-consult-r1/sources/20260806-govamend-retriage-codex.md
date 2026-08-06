# 治理修正 epic — 全票重新裁決（codex，R21）

task-id: `20260806-GOVAMEND-X-CONSULT-R1`  |  brief-kind: consult  |  source: `handoffs/20260801-GOV-AMEND-BACKLOG.md`

## Verdict

RECOMMENDATION: 38/38 票均已裁定；9 張關閉獨立票，2 張已完成，5 張併入既有票或降級；目前最先處理的是 `###` 誤判、B-38、B-15/B-32/B-31 的現行阻塞鏈。

VALUE_RULE: 實證次數只計「可定位的 agent 失誤 episode」；同一 episode 的多次文字引用不重複計算。只有模擬探針、程式碼存在或人類可讀性改善，不能充作 agent 失誤次數。

CLOSED_STANDALONE: B-1, B-2, B-3, B-8, B-12, B-20, B-21, B-23, B-35。

FINDINGS_COUNT: 3

## §0 前提宣告

FACT-VERIFIED:

- `rg -o '^## B-[0-9]+ 票|\*\*B-[0-9]+\*\*' handoffs/20260801-GOV-AMEND-BACKLOG.md` 去重計數為 **38**；1–28 在索引表、29–38 在後續票段，並非缺票。
- `rg --count-matches -F '票 B-38' .claude/gate/audit.log` stdout 為 **9**；這是 B-38 的現行 audit episode 數。
- `rg --count-matches -F 'HEADING_LINE_RE' .claude/gate/audit.log` stdout 為 **1**；該行明確記錄 `###` 被判為 invalid finding ID。
- `rg -n -F '群集' docs/GOVERNANCE_ID_NAMESPACES.md` 只有 `E-<n>` 的非 ID 警告，沒有群集 namespace；`rg -n -F '本 session 9 次' handoffs/20260801-GOV-AMEND-BACKLOG.md` 命中群集歸錯事故。
- `rg -n -F 'mutation_probe_static.py' handoffs/20260801-GOV-AMEND-BACKLOG.md` 命中兩處：問題描述與「待開」記錄；目前沒有 B-票號。

ASSUMPTIONS_EXPLICIT:

- 「實證次數」採 incident episode，不採 raw grep 命中數；B-11、B-28、B-35 等只有設計／模擬證據者明列為 0 真實 episode。
- 「溯及既往」指是否要重寫既有票、既有收斂檔或既有產物；新產物的守衛均按 forward-only 判定。
- 未把現行未提交 B3 修補當 oracle；B3R 仍以凍結 snapshot + `phase2_expected_flips` 矩陣為差分基準。

VERIFY_RECEIPTS:

- B-7：`rg -n -F '格式範例字串' handoffs/20260801-GOV-AMEND-BACKLOG.md` → line 166，原文記錄兩家委員抄錯、兩輪補正。
- B-9/B-10：`rg -n -F '2026-08-02 codex' handoffs/20260801-GOV-AMEND-BACKLOG.md` → B-9 的一輪直接機檢停工；同段 B-10 記錄一輪 TEMPLATE FAIL，且 B-10 已有 commit `901a8d9`。
- B-13/B-36：`rg -n -F '兩輪三家對抗審' handoffs/20260801-GOV-AMEND-BACKLOG.md` → 1 個 migration episode；`rg -n -F '錯位' handoffs/run_receipts/20260805T003743Z-govb0-r4-g5-b36-residual.log` → 殘留為漏／錯位兩種不同缺口。
- B-30：`rg -n -F '43 分 26' handoffs/20260801-GOV-AMEND-BACKLOG.md` → 1 個 self-overwrite episode。
- B-31/B-32：`rg -n -F 'a50b7e6c' .claude/gate/audit.log` 與 `rg -n -F '8fedcd8b' .claude/gate/audit.log` → R5/R5B 兩個 format-failed/abandon episode；R1 的同類事件另在 backlog 票面記錄，合計 3。
- B-38：`rg --count-matches -F '票 B-38' .claude/gate/audit.log` → 9；不是把 `debt_abandon` 總數當 B-38 次數。
- `###`：`rg -n -F '927b9f79-0348-4f2a-9854-762c9f09a238' .claude/gate/audit.log` → round open/result/abandon；abandon reason 明列 `#{2,6}` 與 `##(?!#)` 分歧。

## 逐項核對表

| 票號 | 擋哪類 agent 失誤 | 實證次數（可重跑查法） | 新增摩擦 | 是否溯及既往 | 裁定 |
|---|---|---:|---|---|---|
| B-1 `spec_binding_check.sh` | 依過時 v0.5 正文對不存在腳本施工 | 0；`rg -n -F 'spec_binding_check.sh' .claude/gate/audit.log handoffs/run_receipts` 無 agent 事故 episode | 建舊 checker、三態測試、遷移舊正文 | 是 | 關閉；v2.0 已取代 |
| B-2 `manifest_parse.py` | 把不存在的 manifest parser 當現行機制 | 0；`rg -n -F 'manifest_parse.py' .claude/gate/audit.log handoffs/run_receipts` 無 agent 事故 episode | 新 parser、yaml contract、遷移 | 是 | 關閉 |
| B-3 `rejections.yaml validator` | 把拒絕登錄檢核錯掛到 manifest parser | 0；`rg -n -F 'rejections.yaml' .claude/gate/audit.log handoffs/run_receipts` 無執行事故 | 新 validator 與分工維護 | 是 | 關閉 |
| B-4 stamp 區白名單 | 把 stamp/waived 分支誤當可跳過的檢查 | 0；`rg -n -F '戳記區白名單' .claude/gate/audit.log handoffs/run_receipts` 無 agent episode | 每輪 stamp/遷移都增加白名單檢查 | 否 | 降級；與 B-5 合併為 forward-only guard |
| B-5 `gate.sh` 落地缺口 | 依賴缺席或 waived 狀態仍被當作通過 | 0 個實際誤放行 episode；`rg -n -F 'waived:*' scripts/gate.sh` 只證明程式缺口 | gate dispatch 每次多一個分支驗證 | 否 | 做（P2，先補實證再改判定） |
| B-6 token worktree bind | 跨 session token 授權錯 task/intent | 0；`rg -n -F 'GATE-TOKEN-BINDING' .claude/gate/audit.log handoffs/run_receipts` 無 wrong-task episode | token payload/lock 綁定與每次驗證 | 否 | 降級（P2，待 B-11 後） |
| B-7 task-id inject | 手抄 task-id 抄到 brief 範例值 | 2 家族；`rg -n -F '格式範例字串' handoffs/20260801-GOV-AMEND-BACKLOG.md` line 166 | 已由 prompt 注入；日後每輪少手抄 | 否 | 做（已完成） |
| B-8 rejected-list ACK | append 未經他方確認，agent 以未核實清單繼續 | 0；`rg -n -F 'gov_rejected_mechanisms.tsv' .claude/gate/audit.log handoffs/run_receipts` 無誤用 episode | 每次 append 需 ACK/audit，摩擦固定 | 否 | 關閉 |
| B-9 docs stamp provenance | 照文件把 D 產物送機檢後被錯誤拒派 | 1；`rg -n -F '2026-08-02 codex' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 路徑規則、provenance、三家收斂 | 否 | 做（P1；B28 併入前置） |
| B-10 dext template kind | D extension 被誤送 SPEC template 而拒派 | 1；同上 query line 169 記錄 TEMPLATE FAIL；`git log -1 --oneline -- scripts/template_check.sh` 可見已落地 | 修正後無新增每輪成本 | 否 | 做（已完成） |
| B-11 fail-closed dependency guard | 依賴缺席被當成「不適用」而靜默放行 | 1 個靜態探針誤判實驗；`rg -n -F '誤判率 100%' handoffs/20260801-GOV-AMEND-BACKLOG.md` | runtime mutation hard gate + 靜態 tripwire | 否 | 降級；併 `GOV-FAILOPEN-GUARD`，不採原本 static hard gate |
| B-12 harness script-list SSOT | harness 漏列／錯列腳本造成測試假綠 | 0；`rg -n -F 'GOV-TESTHARNESS-SCRIPTLIST-SSOT' .claude/gate/audit.log handoffs/run_receipts` 無直接 episode | SSOT 建立與持續同步 | 否 | 關閉；必要部分併 B-17 |
| B-13 merge completeness | 搬文檔漏段、漏 ID、改號只改標題 | 2 migration episodes；`rg -n -F '兩輪三家對抗審' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 生成 source→target 骨架、反向差集、撞號檢查 | 否 | 做（P1；吸收 B-18、B-36） |
| B-14 postwrite hang | agent 已交件但 CLI 不退出，主流程長時間空等 | 1 round / 3 family outputs；`rg -n -F '三家 18 分鐘' handoffs/20260801-GOV-AMEND-BACKLOG.md` | timeout、terminal state、完成度判定 | 否 | 做（P1；與 B-30 同批） |
| B-15 readonly gate FP | 唯讀查詢誤擋，或真派工從詞法缺口漏網 | 5（3 個明名 FP + 2 個 fail-open）；`rg -n -e 'pgrep' -e 'completeness --lock' -e '家族 CLI' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 先補 deny receipt，再做 lexer/delta/mutation | 否 | 做（P0） |
| B-16 prose contract detector | 機器依賴契約在散文，regex 漏掉可執行契約 | 1；`rg -n -F '實際 15' handoffs/20260801-GOV-AMEND-BACKLOG.md` | generated-source marker、遷移既有表 | 是；新規則 forward-only | 做（P1） |
| B-17 contract tables→data | 手寫表改一處、其他表漂移 | 4 documented drift episodes；`rg -n -F '四格錯三格' docs/GOVB0_FRICTION_TODO.md` | 結構化資料、生成 view、初始遷移 | 是；舊檔不重寫，新增一律生成 | 做（P1） |
| B-18 reconcile skeleton | 自由書寫收斂漏處置或漏引用 | 同 B-13 的 2 episodes；`rg -n -F '漏處置' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 每次生成預填欄位 | 否 | 降級；併 B-13，不獨立施工 |
| B-19 brief precheck | brief kind、ID、reconcile 授權寫錯導致派工燒輪 | 3；`rg -n -e 'B0R' -e '無法戳記' -e '排除 grok' docs/GOV_DISPATCH_FLOW_FIX_TODO.md handoffs/20260801-GOV-AMEND-BACKLOG.md` | 每次 dispatch 多跑格式/授權/ID precheck | 否 | 做（P0；與 B-29 同批） |
| B-20 closure requires gate | agent 結案只報「跑過」不確認實際 gate 覆蓋 | 0；`rg -n -F 'GOV-TICKET-CLOSURE-REQUIRES-GATE' .claude/gate/audit.log handoffs/run_receipts` 無直接 episode | 每張票增加機械掛點/例外說明 | 否 | 關閉；不以泛化紀律票增加摩擦 |
| B-21 artifact checker registry | agent 漏掛 artifact 驗證器或掛錯 checker | 0；`rg -n -F 'artifact → 驗證檢查器' .claude/gate/audit.log handoffs/run_receipts` 無直接 episode | 維護 registry、每次新增 artifact 登記 | 否 | 關閉；需求併 B-19/B-27 的具名 gate |
| B-22 dispatch watcher | agent/主委把 stale output 當仍在寫，或反之 | 1，與 B-14 同一 2h20m episode；`rg -n -F '2 小時 20 分' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 每 2 分鐘監看進程與檔案 | 否 | 降級；併 B-14/UNTRACKED-PRODUCT-GUARD，不另造 watcher |
| B-23 markup whitelist | 以可讀性/符號形式規則打地鼠，漏掉或誤擋文件 | 0 真實 agent episode；`rg -n -F '20 種' handoffs/20260801-GOV-AMEND-BACKLOG.md` 是變體數，不是事故數 | 全量掃描、allowlist、誤擋 receipt；高摩擦 | 是 | 關閉；不得以美觀或可讀性單獨立票 |
| B-24 acceptance state | 只看命令 rc，不看產出後狀態 | 3；`rg -n -e '已開票' -e '完整併回' -e 'golden 已還原' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 每個驗收欄加狀態斷言 | 否 | 降級；只保留 forward-only 紀律面，機械面另議 |
| B-25 fact-key single source | agent 改一份事實、忘記同步散文副本 | 5；`rg -n -F '同日五次' handoffs/20260801-GOV-AMEND-BACKLOG.md` | fact-key registry/同步機檢；既有資料遷移成本高 | 是；新 key forward-only | 降級；併 `GOV-XREF-SYNC`，不重做兩票 |
| B-26 ID-space allocation | 新增 ID 歸錯群、撞既有 namespace | 8；`rg -n -F '同日 8 次撞號' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 每次新 ID 查登記、查重、寫唯一 owner | 否 | 做（P1） |
| B-27 doc taxonomy | 新文件放錯目錄、票開錯 SoT、事實多副本 | 4 個明名根因 episode；`rg -n -F '這是同日多起事故的直接根因' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 新文件/票多一層分類與 owner 檢查 | 否 | 做（P1；先規則後機械強制） |
| B-28 v2 stage1 tooling | agent 依 v2.0 operative 語氣尋找不存在工具 | 0 真實 agent episode；`test -e` 三工具只證明缺檔，不證明曾誤派 | 建 3 工具、接 3 掛點，成本大 | 否 | 降級；作 B-9 的 forward-only acceptance，不獨立批 |
| B-29 behavior delta | 測試全綠但真實標的沒變，或放行集合擴大未被察覺 | 3/6 GOVFLOW B4 rounds；`rg -n -F 'GOVFLOW `批次 B4` 走 6 輪' handoffs/20260801-GOV-AMEND-BACKLOG.md` | brief 宣告、產出差集、commit 保險；每個判定改動都多一份 delta | 否 | 做（P0/P1；B-19 先或同批） |
| B-30 self-overwrite | agent 用自己的 handoff 路徑覆蓋既有產出 | 1；`rg -n -F '43 分 26' handoffs/20260801-GOV-AMEND-BACKLOG.md` | `.part`/atomic publish/attempt lock | 否 | 做（P1；併 B-14） |
| B-31 format-fail no cheap fix | 完整內容只因格式小錯被迫整份重跑/棄輪 | 3 episodes；`rg -n -F 'a50b7e6c' .claude/gate/audit.log`、`rg -n -F '8fedcd8b' .claude/gate/audit.log` 加 R1 票面 | fixup kind、附掛 brief、狀態化重派；需守 fail-closed | 否 | 做（P0） |
| B-32 unconditional stamp prompt | 系統 prompt 反覆誘導 consult/review 寫錯 stamp heading | 2 direct composer episodes；`rg -n -F '同一個 ## RECONCILE-STAMP' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 依 brief-kind 分支；少量 prompt 邏輯 | 否 | 做（P0） |
| B-33 locale guard drift | agent 在不同 locale 得到不同 gate verdict | 3 observed outcomes（2 fail-open + 1 false-positive）；`rg -n -F 'LC_ALL=C' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 雙 locale 執行與 ASCII/byte-safe guard | 否 | 做（P1） |
| B-34 roster vs rolegate | agent 被角色閘排除後仍被要求補不具語意的第三方 stamp | 1 review round；`rg -n -F 'grok 必須為一份' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 以實際 participants 取 roster 或區分 spec/code review | 否 | 做（P1） |
| B-35 truncation oracle | 截斷產出被誤當完整交件 | 0 真實；1 synthetic probe；`rg -n -F '截成 6 行' handoffs/20260801-GOV-AMEND-BACKLOG.md` | producer manifest/sidecar，跨越現行 scope | 否 | 關閉至有真實受害 episode；保留 B-14 殘留註記 |
| B-36 cluster blindspot | finding 漏進群集、ID 歸錯群或兩列對調仍全綠 | 3 episodes；`rg -n -e '漏掉.*COMPOSER-R2-P1-01' -e '引錯三個 ID' -e '兩個群集列' handoffs/20260801-GOV-AMEND-BACKLOG.md` | 產出端預填、assertion 摘句、來源比對 | 否 | 降級；併 B-13，錯位守衛須另列殘留 |
| B-37 friction tally | agent/主委用漂移的人工次數排序工作 | 8 次計數漂移；`rg -n -F '計數已漂 8 次' handoffs/20260801-GOV-AMEND-BACKLOG.md` | B1 telemetry 後導出每票次數；不可手寫 | 否 | 做（P2；B1 後） |
| B-38 zero-findings closure | 合法 0 findings 被判 WARN/FAIL，只能 abandon | 9 audit episodes；`rg --count-matches -F '票 B-38' .claude/gate/audit.log` → 9 | 0 findings 需明示 count/sentinel；低摩擦且可驗 | 否 | 做（P0） |

ADDITIONAL_ANSWERS:

1. 應關閉的 9 張獨立票：B-1、B-2、B-3（v2.0 取代的舊票）；B-8、B-12、B-20、B-21、B-23（沒有可定位 agent 失誤且新增摩擦高）；B-35（只有 synthetic truncation，尚無真實受害）。關閉不等於刪除風險記錄；B-35 風險留在 B-14 殘留。

2. 第 0 批批次計畫的建議順序：`B0 → (B1 ∥ B2) → B3R → B4 → B5 → B6 → B7`。B0 的 pre-Phase2 snapshot 仍是 B3R/B5 的硬前置；B1 是 B5/B37 的資料前置，但不應阻塞 B3R；B2 是 B32 且是 B6 prompt 路徑的前置。原 B3 不再獨立驗收，B3R 吸收其 11 契約／parity／mutation／時限，舊 B3 已達成部分以 ledger 保留，不重做。B4 必須等 B3R；B5 只能在 B3R+B4 後產生差集；B6 保留並吸收 B14/B30；B7 延後到 B6 的 terminal/duration receipt 足夠，timeout 仍標 `PROVISIONAL`，不砍。

3. `###` 誤判依公式為 **P0、當前佇列優先序 #1**：raw evidence 僅 1 episode，但單次成本是整個 review round 被 `format-failed`/abandon，且修正邊界小於另造一個全流程；它不是可讀性問題，而是 checker 的兩個標題定義造成合法 agent 產出不可達。應開獨立機制票（例如 `GOV-COMPLETENESS-HEADING-LEVEL-MISMATCH`），B-31/B-32 分別只是放大器與誘因，不能吞掉根因。

4. 群集 ID 不應用 `C-`、`D-`、`E-`、`F-` 再開一個全域 namespace；這些字首已撞既有空間或被用作語意標籤。新收斂檔應使用機械生成的 session-scoped cluster key，並同列來源 finding ID、斷言摘句與唯一 owning synth；群集 key 不得作 `##` finding heading。舊群集不回寫，B-13/B-26/B-36 只對新產出強制。原因與收益：本 session 已記錄 9 次歸錯群，新增一行摘句比對的摩擦小於再次重跑一輪。

5. 該開而未開：

- 應新增根因票：`###`/`######` 抽取正則與 `##` body-hash 正則不一致；目前只有 B-31/B-32 的結果票，沒有 checker 根因票。
- 應新增或正式編號：`mutation_probe_static.py` 對 subprocess 探針 false-negative；backlog 已明載「待開」，且現行以 helper/monkeypatch 繞過。
- 已有名稱但未納入 B-1～B-38 的 open 項，應補 owner/票號而非再發明名字：`GOV-CLAIMCHECK-VS-VERBATIM`、`GOV-COMPLETENESS-FAMILYPREFIX-FP`、`GOV-GATECHECK-DEBTCLEAR-DEADLOCK`、`GOV-MANIFEST-INFLATION-RESIDUAL`、`GOV-SPEC-REV6-STALE-COUNTS`。`GOV-RECONCILE-LOCK-IMMUTABLE-DEADLOCK` 已標 DONE，不列為未開。

## CODEX-R21-P0-01

**斷言**: `completeness_check` 的 heading 抽取將合法 `###` 子標題當成 finding ID，造成合法 review round 無法銷帳。

**碼證**: `rg -n -F '927b9f79-0348-4f2a-9854-762c9f09a238' .claude/gate/audit.log` → round `GOVB35-SPEC-REVIEW2` 的 composer `format-failed` 與 `debt_abandon`；reason 明列 `HEADING_LINE_RE='#{2,6}'` 與 `H2_LINE_RE='##(?!#)'` 不一致。RECHECK：`rg -n -F 'HEADING_LINE_RE' .claude/gate/audit.log` → 1。

**來源摘要**: `.claude/gate/audit.log#d3c2053155af`

[BLOCKING] 信心度=High；這是現行委員輪的硬阻塞，且不是委員措辭錯。修正必須保留真正 malformed canonical-like heading 的拒收行為，並以合法 `###` 與錯誤 `##` 反向 mutation 驗證。

## CODEX-R21-P1-02

**斷言**: 群集段的機械完整性目前對「漏列、錯位、摘句不符」無感；全域 namespace 也沒有群集 key 的註冊。

**碼證**: `rg -n -F '本 session 9 次' handoffs/20260801-GOV-AMEND-BACKLOG.md` → 群集歸錯 9 次；`rg -n -F '群集' docs/GOVERNANCE_ID_NAMESPACES.md` → 僅命中 `E-<n>` 非 ID 警告，沒有 cluster namespace；`rg -n -F '錯位' handoffs/run_receipts/20260805T003743Z-govb0-r4-g5-b36-residual.log` → `completeness_check --lock` 與骨架均可全綠。

**來源摘要**: `handoffs/20260801-GOV-AMEND-BACKLOG.md#76df864efbc5`

[MAJOR] 信心度=High；B-13/B-36 的 forward-only 產出端守衛須帶 assertion excerpt 與來源 finding 綁定；不需重寫舊收斂檔。

## CODEX-R21-P1-03

**斷言**: `mutation_probe_static.py` 的 subprocess false-negative 有明確 repo 證據但沒有 B-票 owner，會使探針「未碰到待測系統」被誤當通過。

**碼證**: `rg -n -F 'mutation_probe_static.py' handoffs/20260801-GOV-AMEND-BACKLOG.md` → line 106 的掉項清單與 line 578 的「待開」記錄；同一段記錄目前以 helper module-level 常數 + monkeypatch 繞過。

**來源摘要**: `handoffs/20260801-GOV-AMEND-BACKLOG.md#76df864efbc5`

[MAJOR] 信心度=High；應先登記 owner 與 subprocess call-graph probe，再讓任何後續 mutation receipt 宣稱通過；不改既有測試斷言以取得假綠。

## 出場判準核算

CHECK-1: 38/38 票有表格列與裁定；驗證命令 `rg -o '^## B-[0-9]+ 票|\*\*B-[0-9]+\*\*' handoffs/20260801-GOV-AMEND-BACKLOG.md | sed -E 's/.*B-([0-9]+).*/B-\1/' | sort -n -t- -k2,2 | uniq | wc -l` → `38`。

CHECK-2: 每票的實證欄都附查法；0 次的票明確標為「無 agent episode」，沒有把 code-path presence 當事故。

CHECK-3: B-38 的現行 audit receipt → `rg --count-matches -F '票 B-38' .claude/gate/audit.log` → `9`；`###` 根因 receipt → `rg --count-matches -F 'HEADING_LINE_RE' .claude/gate/audit.log` → `1`。

ORDER: 先修當前 `###` checker 根因（P0）與 B-38/B-32/B-31/B-15 的阻塞鏈；並行完成 B0 snapshot、B1 telemetry、B2 prompt；再進 B3R；B4/B5；B6/B7；最後才處理低證據或需要歷史遷移的票。所有新守衛只約束新產物，既有 38 票號與舊產物不回寫。

ASSUMPTIONS_VERIFIED: 38 票盤點、B-38=9、`###`=1、群集 namespace 缺失、mutation subprocess 掉項、B3R frozen-matrix 依賴均已以 repo 命令或現存文件驗證。
TESTS_RUN: read-only grep/rg/sed/git log/hash checks only；未跑 pytest，因本任務明定禁改碼且不需全套回歸。
FAILURES_SEEN: `/tmp` 初次盤點命令曾被既有 gate 以 open debt / kind=dispatch 擋下；後續 `ls -ld /tmp/workdir` rc=2（目標不存在），未繞過、未改檔。
SCOPE_CHANGES: none；未改 code、ticket、backlog、HANDOFF.md、data_cache；只新增本報告。
NUMERIC_OR_SCHEMA_IMPACT: none to product/code schema；本報告只新增裁決文字與 evidence counts。
OUTPUT: `handoffs/20260806-govamend-retriage-codex.md`
HANDOFF_NOT_UPDATED: root `HANDOFF.md` preserved because it is Claude-maintained and user scope指定本檔。
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 存在並保留；未刪除其他系統暫存目錄。
STATUS: DONE
