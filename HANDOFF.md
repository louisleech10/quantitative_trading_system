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
本檔**不得手寫**票／批次的狀態字面值（偵測器 fail-closed；已實際擋過多次，**每個 session 都會再擋**）。

# 🔴🔴🔴 待辦清單（唯一來源，機器投影——**本節不得手寫**）

> 改法：編輯 `scripts/fact_keys.json` 之 `governance-worklist` → 跑
> `bash scripts/gen_fact_key_blocks.sh --write`。**完成就把該列狀態改成 `收案`。**
> 欄名見表頭（亦為機械產物）。手寫狀態字面值會被 fail-closed 擋下。

<!-- BEGIN GENERATED: governance-worklist -->
| 序 | 項目 | 狀態 | 內容 |
|---|---|---|---|
| 010 | WL-01 | 收案 | P0 前置：fact_keys schema 由平面列擴為具名欄＋表格投影（columns／render）。三家 review＋閉合複驗＋戳記核可；票 B-25 殘留⑥之 schema 阻塞已解除 |
| 020 | WL-02 | 收案 | P1-a 判準資料化：判準入註冊表＋三道機械檢查（狀態列舉封閉／同適用範圍同條件不得相異期望／判準宿主區塊外不得陳述期望結束狀態）。字面設計經實測為零訊號已由三家 consult 改寫；三輪委員（consult→review→closure）、三家戳記核可。🔴 語意互斥不被攔截，見 docs/GOV_CRITERIA_REGISTRY.md 殘留 1 |
| 030 | WL-03 | 收案 | P1-b 機制證據登記：平台機制入專用登記表（receipt:／assumed: 封閉格式，receipt 須指向被驗樹內之真檔且非 symlink）＋顯式 opt-in 宿主之 `- 改法` 子樹掃描。三輪委員（consult→review→stamp×2）、兩份收斂檔各三枚戳記。🔴 誠實邊界：現樹訊號近零（opt-in 五宿主子樹 195 行、平台機制命中 0），價值在面向未來；子樹旁路四度被委員實構（發現曲線未收斂，改 parser 須重跑候選組）；偶發紅之 fail-open 已封但原始觸發未獨立重現。具名殘留 1-11 見 docs/GOV_MECHANISM_REGISTRY.md |
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
🔴 **不要在本檔任何地方手寫項目編號＋狀態值**——偵測器會擋（歷次前置皆實際擋下過）。

使用者 2026-08-12 夜間指示（逐字）：治理 epic **不寫 SPEC/TODO**，由 Opus 依本表直接實作，
三家委員 review＋adversarial＋討論，分歧由主委與委員共識決、不上呈；中途只 commit 不 push。

🔴 **不要再提「等使用者回答兩個問題」**——已作廢。問題 (b)（凍結檔授權）建立在
**錯誤量測**上：可執行 ASSERT 僅 2 行、兩份凍結檔 0 行，授權問題不存在。
量法錯在何處見 `docs/GOV_ASSERT_PATHA_NOTE.md` §2。

## 🔴 推送狀態：多筆待推（使用者指示先不 push）

**筆數與最新 hash 本檔刻意不寫**（一個 session 內就漂過一次）——直接跑
`git log --oneline origin/main..HEAD` 與 `bash scripts/gov_check.sh --no-probe`（丟背景）。
髒檔應為 4 個且**全為規則禁止提交項**：`.claude/gate/*.log`×2、
`governance_families.json`（`R-15`）、`docs/GOVB0_FRICTION_AMENDMENTS.md`。

🔴 **本 session 兩次被目錄萬用字元 `git add` 咬到**：`git add docs/` 掃進
`GOVB0_FRICTION_AMENDMENTS.md`、`git add scripts/` 掃進 `governance_families.json`，
兩者皆為明令不得提交項。**逐檔列出，不要用目錄形式 add。**
第二次還連帶要重寫三個本地 commit——因為 G-7 的豁免是
「該路徑在範圍內**只**被 out-of-epic commit 觸及」，補後續 commit 解不掉。

## 本 session（2026-08-13 凌晨）之待辦項目

**做法**（使用者 08-12 夜間定）：不寫 SPEC/TODO，依待辦清單直接實作＋三家 review。
每項鏈路：實作 → 三家 review → 採納修補 → **原提出方複驗**（章程 §B8）→ 三家戳記 → 清債。
狀態值見本檔最上方生成區塊，此處不重述。

| 項 | 交付 | 委員輪次 | 收斂檔（含量測與逐條處置） |
|---|---|---|---|
| 第一項 | `fact_keys` schema 擴為具名欄＋表格投影 | review → closure | `handoffs/reconcile/20260813-govwl01-x-review-r1/synth.md` |
| 第二項 | 判準入註冊表＋三道機械檢查 | consult → review → closure | `handoffs/reconcile/20260813-govwl02-x-consult-r1/synth.md` |

### 🔴 接手前必讀的兩條經驗（細節與量測一律看上表收斂檔，本檔不重述）

1. **清單上的字面設計不等於既成事實。** 第二項的字面寫法經三家 consult 後**整個改寫**；
   理由、量測方法與逐條裁定都在上表第二列的收斂檔。
   **看到類似的字面設計，先量一次再動手，不要照抄開工。**
2. **注意「檢查只掛在其中一條路徑上」這個形態。** 本 session 反覆出現，
   逐次列舉見 `白話說明/流程摩擦記錄.md` 8/13 第十五條。
   **審查時應主動問「同一種輸入有沒有第二條處理路徑」。**

## 已完成並 push（`origin/main`）

- `票 B-49`：凍結出口補上、幽靈路徑 11→0、關票條件機械可驗（**狀態值見生成區塊**）
- **ASSERT 自鎖 T0 止血**（`53966e90`）：寫檔路徑零執行 ＋ 逐行 timeout ＋ `proc_guard.sh`
- 檢查鏈段序改「便宜先」＋早退＋失敗摘要（`2c34027a`）

## 📜 前一 session（2026-08-12）之批次——**歷史紀錄，非現況**

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

- 🔴 `票 B-25`：schema 阻塞與互斥判準偵測已交付（待辦清單前兩列），
  **機制證據登記（第三列）設計已定、尚未實作**。
  🔴 **能力邊界（三家一致，永遠不會由本機制關閉）**：語意互斥——兩段話用**不同條件字串**
  描述同一物理事件時鍵不相等，機械上偵測不到；出生事故那型即屬此類。
  完整殘留清單見 `docs/GOV_CRITERIA_REGISTRY.md`。
  該票於票狀態表之列為 ord `005`（**狀態值見生成區塊，本檔不重述**）；
  票本身另有具名殘留，見 backlog `B-25` 節。
- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；OOE 通道救不了
- `R-13` Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`
- `票 B-49`：四條具名殘留見 `docs/GOV_B49_ASBUILT_DELTA.md` §3
- `票 B-54`：戳記 64 位 hex 仍由委員手抄，曾掉字一次。**已部分緩解但未機械化**——
  現行做法是在 stamp brief 內要求委員**自行以 `reconcile_body_hash.sh` 重算核對、不得抄**，
  並聲明「算出不同就以你算的為準並開 finding」。屬紀律非強制；根治＝待辦清單之 `WL-04`
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
  曾兩次只 `tail -3` 就重跑，白花 22 分鐘——摘要末尾化就是為此而做。
- 🔴 **G-7／F5 用 endpoint 淨差**：commit **前**是綠的（檔還沒進範圍），一 commit 才現形
  ⇒ **commit 之後必須重驗**。歷次 session 皆踩過。
- 🔴 **G-7 的 out-of-epic 豁免是「該路徑在範圍內*只*被帶 trailer 的 commit 觸及」**
  ⇒ 同一檔若被任一無 trailer 的 commit 碰過，**補後續 commit 解不掉**，只能重寫歷史。
  凡動到 scope 外的檔（如新建 `docs/GOV*`），**該檔涉及的每一筆 commit 都要帶 trailer**。
- 🔴 **反向驗證才算數**（移除判定 ⇒ 對應斷言須轉紅）；**前必先 commit**——
  `git clone --local` 只取已提交內容（曾因此白驗一輪）。
- 🔴 **實測 > 假設**（本專案最貴的一條，已連續多輪咬人）：
  ・寫進文件的機制**必須先實跑**（`setsid`／`ulimit` 那次燒掉三輪審查）
  ・**量測時 pattern 須一致**，且**引用命中數必須同時給比對式**——
  　同一件事三家量出三個不同數字，只是寬嚴不同，不附 pattern 的數字等於沒有數字
  ・**斷言「這條規則抓得到那個已知案例」時，要拿那個案例去跑**——
  　曾斷言新規則會攔到 `setsid`，實測發現 `setsid` 不在 PATH ⇒ 規則反而漏掉它本身
- 🔴 **待辦清單上的字面設計不等於既成事實**：連續兩項（判準偵測、機制證據）
  的字面寫法都在開工前量測時被推翻（一項零訊號、一項誤擋率八九成）。
  **每項開工前先量一次「這條規則在現有語料抓得到東西嗎」**，這已兩次擋下無效施工。
- 🔴 **注意「檢查只掛在其中一條路徑上」這個形態**：一天內出現四個位置
  （表頭 vs 儲存格／schema 單欄刪除／狀態靠列舉位置／驗證只掛 `--check`）。
  審查時主動問「同一種輸入有沒有第二條處理路徑」。
- 🔴 **不以家數表決，以碼證定**（本 epic 三次「兩家一種說法、一家附碼證」，皆採後者）。
- 🔴 **同一支腳本不得並行跑多份**——曾三份 `template_check` 併發導致 fork 耗盡（上限 1333）。
- 🔴 fact-key 註記**不得含日期**；改 `fact_keys.json` 後 `factkey_clean`／`factkey_drifted`
  兩 fixture 皆須用 `GOVB1_FACTKEY_ROOT=<目錄>` 重生成，drifted 須維持「恰一列不同」。
- 🔴 `handoffs/run_receipts/` 進 commit 須帶 `Governance-Scope: out-of-epic` trailer，
  且 **trailer 必須在最後一段**（git 只解析最末段）。
- 🔴 閘會把含家族名的**讀取指令與 commit 訊息**當成派工 ⇒ 訊息一律用 Write 工具寫檔再 `-F`。
- 🔴 禁 `cd <專案路徑>` 前綴、禁 `sed -i`、禁 `rm`（用 `mv` 到 `.claude/tmp/`）、
  禁 `python3 - <<'PY'` heredoc；改檔一律用 Edit／Write。
  **`printf ... >> 檔` 也算違反**——內容裡的 `%` 會被當格式指令，
  曾一次把三份說明檔截斷在句子中間。Edit 找不到目標會失敗，shell 拼字串會**靜默產出半截**。
- 🔴 **`git add` 一律逐檔列出，禁目錄形式**——`git add docs/`／`git add scripts/`
  曾各掃進一個明令不得提交的檔（`GOVB0_FRICTION_AMENDMENTS.md`、`governance_families.json`），
  其中一次還連帶要重寫三個本地 commit。
- 🔴 **說明檔同步是「每個工作項目的最後一個 commit」**，不是每次存檔都補——
  時序判準比的是「說明檔最後改動不早於程式最後改動」，只要又動程式全部說明檔就再度過期。
  曾照「每次存檔都補」做而連撞三次。
- 🔴 **委員戳記的 body hash 一律要求委員自算**（brief 內明寫「不得抄、算出不同以你的為準」）——
  `票 B-54` 是委員手抄掉字造成的。
