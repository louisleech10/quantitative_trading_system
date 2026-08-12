# Handoff

**Agent**: Claude(Opus 5) | **Branch**: main | 實作＝主委自任（`implementer=claude`）；
討論／review／adversarial＝**codex+composer+grok 三家全員**

> 🔴 本檔超過 CLAUDE.md 之 ≤30 行規約，**結構上不可能達成**：下方「未修的活缺口」節是
> **機器輸入**（`governance-ticket-closure` 之導出來源），長度由未收案票數決定。
> 刪它會使 `test_e3_ticket_union_matches_key_rows` 轉紅（實測過）。修訂案待使用者裁定。

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 施工順序／批次狀態／票收案狀態 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 之三個 generated block |
| 票的內容 | `handoffs/20260801-GOV-AMEND-BACKLOG.md` |
| 給使用者的現況 | `白話說明/接下來要做什麼.md` |
| 委員名冊 | `scripts/governance_roles.json`＋`governance_families.json` |
| `B-49` as-built 落差與殘留 | `docs/GOV_B49_ASBUILT_DELTA.md` |

🔴 改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`；
本檔**不得手寫**票／批次的狀態字面值（偵測器 fail-closed，本 session 踩三次）。

# 🔴🔴🔴 待辦清單（唯一來源，機器投影——**本節不得手寫**）

> 改法：編輯 `scripts/fact_keys.json` 之 `governance-worklist` → 跑
> `bash scripts/gen_fact_key_blocks.sh --write`。**完成就把該列狀態改成 `收案`。**
> 欄名見表頭（亦為機械產物）。手寫狀態字面值會被 fail-closed 擋下。

<!-- BEGIN GENERATED: governance-worklist -->
| 序 | 項目 | 狀態 | 內容 |
|---|---|---|---|
| 010 | WL-01 | 收案 | P0 前置：fact_keys schema 由平面列擴為具名欄＋表格投影（columns／render）。三家 review＋閉合複驗＋戳記核可；票 B-25 殘留⑥之 schema 阻塞已解除 |
| 020 | WL-02 | 未開工 | P1-a 判準資料化：同 Task 內互斥判準偵測（抽 條件→期望rc 配對，同條件不同期望即 FAIL）。前置 WL-01；票 B-25 |
| 030 | WL-03 | 未開工 | P1-b 改法段之機制須有 FACT-RECEIPT 或標 assumed，否則 FAIL（撰寫當下攔先斷言後驗證）。前置 WL-01；票 B-25 |
| 040 | WL-04 | 未開工 | P1-c 戳記整行由 harness 自動生成，消滅 64 位 hex 手抄。票 B-54（其樣本數1門檻已過期，須先更新）。無前置 |
| 050 | WL-05 | 未開工 | P2 指令 tokenize 化：逐命令位置解 argv[0] 比對封閉 executor_clis。票 B-59（併 B-61 同型）。屬大重寫，須另立 epic |
| 060 | WL-06 | 未開工 | P3 測試空心／假綠之機械判準。併入票 B-25，不新開票（既有：PATH劫持1條已修、test_verify_gate系列3條、未列入排除清單2條） |
| 070 | WL-07 | 未開工 | 管線豁免提案交三家（免SPEC/TODO之三條件；延伸檔，範圍由 govb1_scope.manifest 導出以免凍結變永久） |
| 080 | WL-08 | 收案 | CLAUDE.md 去除會漂的值：code review 家數改指向 ORCH §1；pytest 秒數/測試數改為不漂的定性判準 |
| 090 | WL-09 | 未開工 | 六張無批次歸屬之票排入執行序：B-48／B-50／B-51／B-52／B-53（排序凍結已解除，見 GOVERNANCE_EXECUTION_ORDER 之 RULED-BY；backlog:3129 之舊句已作廢） |
| 100 | WL-10 | 未開工 | 站級施工順序不在本表重述，見 docs/GOVERNANCE_EXECUTION_ORDER.md 之 governance-execution-order 區塊 |
<!-- END GENERATED: governance-worklist -->

# 接手第一件事：做上表**由上而下第一個尚未完成的項目**

**做完後只改 `scripts/fact_keys.json` 該列的狀態欄，再跑
`bash scripts/gen_fact_key_blocks.sh --write`**，兩份文件同時更新。
本節刻意**不重述任何一列的內容**——重述就是副本，副本就會過期。
🔴 **不要在本檔任何地方手寫項目編號＋狀態值**——偵測器會擋（本次前置已擋下兩處）。

使用者 2026-08-12 夜間指示（逐字）：治理 epic **不寫 SPEC/TODO**，由 Opus 依本表直接實作，
三家委員 review＋adversarial＋討論，分歧由主委與委員共識決、不上呈；中途只 commit 不 push。

🔴 **不要再提「等使用者回答兩個問題」**——已作廢。問題 (b)（凍結檔授權）建立在
**錯誤量測**上：可執行 ASSERT 僅 2 行、兩份凍結檔 0 行，授權問題不存在。
量法錯在何處見 `docs/GOV_ASSERT_PATHA_NOTE.md` §2。

## 🔴 推送狀態：**2 筆待推**（使用者指示先不 push）

`eddd78e3`（待辦清單機械化＋CLAUDE.md 去漂）、`dd384910`（ASSERT 執行閘反轉 opt-in）。
四道閘已於 commit 後重驗：`g7=0 factkey=0 plaindocs=0`；全套 1534 passed（收據見下）。

## 已完成並 push（`origin/main`）

- `票 B-49`：凍結出口補上、幽靈路徑 11→0、關票條件機械可驗（**狀態值見生成區塊**）
- **ASSERT 自鎖 T0 止血**（`53966e90`）：寫檔路徑零執行 ＋ 逐行 timeout ＋ `proc_guard.sh`
- 檢查鏈段序改「便宜先」＋早退＋失敗摘要（`2c34027a`）

## 本批（2026-08-12；使用者裁定「不要再搞 SPEC/TODO」，直接實作＋三家 review）

**PUSH 11 分鐘 ＋ ASSERT 自鎖，兩題皆已改碼**（前版交接記為「一行程式碼都沒改」）：

| 改動 | 檔 |
|---|---|
| 段序改便宜先＋便宜段早退＋失敗摘要末尾化＋backlog 移至最末 | `scripts/gov_check.sh` |
| 路 A：呼叫端不執行文件內 ASSERT（**三處**） | `gate.sh`×2、`spec_fourway_check.sh`×1 |
| NO_EXEC 下印出「ASSERT 未驗證」（不得靜默） | `scripts/template_check.sh` |
| 新增守衛測試 13 格（含 5 條 mutation 反面） | `tests/governance/test_gov_check_cheap_first.py` |
| 處置與具名殘留 | `docs/GOV_ASSERT_PATHA_NOTE.md` |

**三家 review**（`handoffs/20260812-govcheap-x-review-r1/`）：Composer／Grok 判可派工；
**Codex 判需修補**（2 條 P1，附行號碼證）。依「不數人頭以碼證定」採 Codex，兩條均已修：
① G-7 缺檔原寫成「略過」＝fail-open ⇒ 改以 `scripts/govb1_scope.manifest` 判適用性、
　 缺腳本判紅，並補 `test_mutation_removing_g7_script_turns_red`
② NO_EXEC 靜默放行「文法對但結果會錯」之 ASSERT ⇒ 改為大聲印出，
　 並把可執行 ASSERT 之**檔案集合凍成具名清單**（新增即轉紅）
另 Grok＋Codex 抓到主委自造回歸：以 `awk` 批次改註解時**掉了 `gov_check.sh` 的可執行位**，已還原。

### 續作（同日第二輪，session `20260812-govassert-x-review-r1`）

`CODEX-R1-P2-04` 指出「掃呼叫端」判準**不封閉**（`scripts/test_template_check.sh:64`
以 `bash "${TEMPLATE_CHECK}"` 呼叫，正則看不見）⇒ **反轉預設**：
`template_check.sh` 改為預設不執行、須明示 `TEMPLATE_CHECK_EXEC=1`；
四處呼叫端的死旗標移除；列舉式掃描測試刪除，改為形態面＋行為面兩條判準。

三家再審 6 條**全數採納並修**。其中 `GROK-R1-P1-01` 為 BLOCKING：
反轉後 `test_t15_a1_path_hijack_blocked`（唯一不走 `_run_fn` 的承重測）變成空心格，
已修並經反面實證（拆掉 PATH 固定 ⇒ marker 出現）。

🔴 **本輪品質觀察（重要）**：必答「是否出現空心格」一題，**Codex 與 Composer 皆答錯**
（兩家都聲稱 PATH 劫持測經由 `_run_fn`，實為自建 probe），只有 grok 實跑隔離。
⇒ 該兩家之「可 commit」verdict 建立在錯誤事實上。
**review 品質的分水嶺是「有沒有真的跑」，不是家數**——派工時應要求附實跑隔離結果。

### 第三批（`eddd78e3`；使用者指示「寫在一定會看到、不會漏也不會讀錯的地方」）

- **待辦清單改為機械投影**：新 fact-key `governance-worklist`，宿主＝本檔＋
  `白話說明/接下來要做什麼.md`。**狀態只改 `scripts/fact_keys.json` 一處**，手寫即 fail-closed。
- **`CLAUDE.md` 去除會漂的值**：① code review 家數改為指向 `ORCH §1`
  （原寫「2 個」而 ORCH 為三家，當日害主委做錯一次）② pytest 秒數／測試數改為
  「十分鐘級、前景必 timeout」之不變判準（該數字已過期四次）。
- 延伸檔 `docs/GOV_B25_SCOPE_AMENDMENT.md` 補列 `FACTKEY-ADDED: governance-worklist`，
  並把該檔寫死的「兩個狀態 key」改為指標。
- 🔴 **本批未經三家 review**（改動為資料註冊與文件去漂，無行為邏輯）。
  若下個 session 認為需要，補派一輪即可；**不得宣稱已審**。

## 實測數字：本檔不重述，看唯一來源

| 量到什麼 | 唯一來源 |
|---|---|
| `--fast`／全套 push 路徑之前後對照、backlog 75 秒之根因 | `白話說明/接下來要做什麼.md` 之「8/12 深夜」節 |
| 可稽核收據（含 exit_code／sha256／git_head） | `handoffs/run_receipts/20260812T121019Z-govcheap-fast-1s.*`<br>`handoffs/run_receipts/20260812T122358Z-govcheap-fullgate-703s.*` |
| ASSERT 執行面之正確量法與數字 | `docs/GOV_ASSERT_PATHA_NOTE.md` §2 |

🔴 **舊記「89 行／9 檔／凍結檔 45 行」係量法錯誤（未錨定行首），已作廢——勿再引用。**

## 平台事實（勿重測，直接用）

- `ulimit -H -u` 本機**不能降**（`Invalid argument`）；只降 soft 必被子程序抬回
- **無 `setsid` 指令**；`set -m` 可使背景 job 自成 pgid，`kill -TERM -<pgid>` 實測連孫程序一併終止
- per-user process 上限 `ulimit -u`＝**1333**

## 🔴 未修的活缺口

> 🔴 **本節是機器輸入**：`governance-ticket-closure` 之導出集合＝本節 ∪
> backlog「2026-08-10 scope 缺口」節所提及之票號。增刪票號提及須同步 `scripts/fact_keys.json`。

- 🔴 `票 B-25`：**判準資料化整項未做**，卡在 `fact_keys` 之 `.rows[]|@tsv` 只支援平面列
  （＝待辦清單之 `WL-01`）。三項殘留：①正向斷言擋不住「有 pointer 但旁邊另寫互斥判準」
  ②引用已廢判準無機械偵測 ③完整解未做。併入兩條機械檢查提案：**同 Task 內互斥判準偵測**、
  **改法段之機制須有 FACT-RECEIPT**（對應待辦清單第二、三列）。
  該票於票狀態表之列為 ord `005`（**狀態值見生成區塊，本檔不重述**）；
  票本身另有 **8 條**具名殘留，見 backlog `B-25` 節。
- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；OOE 通道救不了
- `R-13` Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`
- `票 B-49`：四條具名殘留見 `docs/GOV_B49_ASBUILT_DELTA.md` §3
- `票 B-54`：戳記 64 位 hex 由委員手抄，曾掉字一次
- `B3R` 已進主樹但三家 review 未戳記 ⇒ 只能說「已交付、待戳記」
- `票 B-56`／`票 B-57`（優先序低）／`票 B-58`（前導空行是否為缺陷未判定）
- `票 B-59`（優先序高）：dispatch gate 判定式為黑名單列舉，**不得宣稱閘已完備**
- `票 B-60`：`review_quorum_check.sh:35` 家族清單硬編未讀 SoT
- `票 B-61`：`_role_gate.sh` 之 `known_only` 對未知家族靜默放行
- `票 B-15` 誤擋仍在（含 `for f in codex composer grok` 這類唯讀迴圈被家族名偵測誤擋）
- `票 B-50` 流程面永久標記為跳步；`票 B-31` 只能說「產出端已有檢查點」（`票 B-53` 落地前）
- 站 5 未修殘留：`CODEX-R3-P0-03`／`CODEX-R3-P1-04`／`gate_check.sh` audit 分類器未同步
- 另有兩條空心探針不在 `LEGACY_PROBE_DEBT` 內（`test_mutation_g5_g6_empty_extract_fails`／
  `test_mutation_removing_selfcheck_case_turns_red`）⇒ `gov_check` 全跑必紅（pre-push 用
  `--no-probe` 跳過故不擋推送）。**既有債**，pre-B49 基準實測同樣紅。刻意不加進具名排除清單。
- `R-15`：`scripts/governance_families.json` 不可 commit
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**`（`run_receipts/` 除外）不得 commit
- 卡頓偵測器錯誤歸因：`settings.json` 之 `ts_stamp.sh OUT`（`:184`）早於
  `doc_format_precheck`（`:197`）⇒ hook 執行時間被記成「Claude 生成慢」。屬使用者設定檔，需其同意

## ⚠ 操作紀律（踩過的坑，一律照做）

- ✅ **「推送前必跑 8 秒快閘」已不再是紀律**——白話同步／fact-key／G-7 已是 `gov_check.sh`
  的第 2–4 段，且**便宜段一紅即早退**（實測 10 秒內給答案，不再跑滿 12 分鐘）。
  自檢直接跑 `bash scripts/gov_check.sh --no-probe`（丟背景）即可。
- 🔴 **失敗先看最末的 `GOV-CHECK-FAILED:` 摘要**（已具名段號與修法），**禁直接重跑套件**。
  本 session 兩次只 `tail -3` 就重跑，白花 22 分鐘——摘要末尾化就是為此而做。
- 🔴 **G-7／F5 用 endpoint 淨差**：commit **前**是綠的（檔還沒進範圍），一 commit 才現形
  ⇒ **commit 之後必須重驗**。本 session 頭尾各踩一次。
- 🔴 **反向驗證才算數**（移除判定 ⇒ 對應斷言須轉紅）；**前必先 commit**——
  `git clone --local` 只取已提交內容（曾因此白驗一輪）。
- 🔴 **實測 > 假設**：本 session 三輪審查（`setsid`／`ulimit`）全因主委未實跑即寫入 SPEC。
  **量測時 pattern 須一致**（曾以 `rc=` 算檔數、`rc(=|!=)` 算行數 ⇒ 誤報 10 檔，實為 9）。
- 🔴 **不以家數表決，以碼證定**（本 epic 三次「兩家一種說法、一家附碼證」，皆採後者）。
- 🔴 **同一支腳本不得並行跑多份**——曾三份 `template_check` 併發導致 fork 耗盡（上限 1333）。
- 🔴 fact-key 註記**不得含日期**；改 `fact_keys.json` 後 `factkey_clean`／`factkey_drifted`
  兩 fixture 皆須用 `GOVB1_FACTKEY_ROOT=<目錄>` 重生成，drifted 須維持「恰一列不同」。
- 🔴 `handoffs/run_receipts/` 進 commit 須帶 `Governance-Scope: out-of-epic` trailer，
  且 **trailer 必須在最後一段**（git 只解析最末段）。
- 🔴 閘會把含家族名的**讀取指令與 commit 訊息**當成派工 ⇒ 訊息一律用 Write 工具寫檔再 `-F`。
- 🔴 禁 `cd <專案路徑>` 前綴、禁 `sed -i`、禁 `rm`（用 `mv` 到 `.claude/tmp/`）、
  禁 `python3 - <<'PY'` heredoc；改檔一律用 Edit／Write。
