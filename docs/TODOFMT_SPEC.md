# TODOFMT — 工作文件（TODO）改為可執行落點 — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260922-todofmt-x-consult-r1/synth.md`（三家 17 條，零駁回）＋`docs/PROCOPT_DECISION.md`　|　日期：2026-09-22　|　對應 TODO：本票之 TODO 依本 SPEC 定義之新格式產出（見 §P Phase 3）

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：**大**（改 `templates/`、`CLAUDE.md`、`docs/MULTI_AGENT_ORCHESTRATION.md` 與閘門腳本，影響其後每一張票）。
- **命中高風險原則**：
  - **(b) 跨模組／共用路徑**：`templates/TODO_GENERATION_PROMPT.md`、`scripts/template_check.sh`、`scripts/gate.sh`、`CLAUDE.md` 皆為全專案共用控制流。
  - **(c) 多 phase／難回退**：格式改變後，既有 `docs/*_TODO.md` 與新格式並存期間須有明確判定規則。
  - **不命中 (a)**：本票**不改任何數值計算**。**不命中 (d)**：不碰 ML／回測正確性。
- **RISK-HIT 宣告**（機檢依據）：
RISK-HIT: b,c
- 未命中 (a)／(d) ⇒ §G Golden 於 §N 標 N/A＋理由。

---

## §A 假設與待使用者確認（事故：拿推論代替問人）

### 已驗證事實（FACT-RECEIPT）

- FACT-RECEIPT: `grep -rl "def test_mutation_" tests/momentum tests/api tests/feature_engineering | wc -l` → 印出 `26`（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `find tests/momentum -name "test_*.py" | wc -l` → 印出 `198`；`tests/api` → `100`；`tests/feature_engineering` → `69`（合計 367）（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `find tests/governance -name "test_*.py" | wc -l` → 印出 `97`；其中 `grep -rl "def test_mutation_"` → `28`（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `tr '\n' '\0' < <26檔清單> | xargs -0 python3 scripts/mutation_probe_static.py` → rc=1、`grep -c "探針未碰到待測系統"` 印出 `12`、**耗時 0 秒**（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_marginal_ic.py` → 印出 `MUTATION-PROBE PASS`、`2 passed, 32 deselected in 0.98s`、rc=0（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `grep -n "probe_files" scripts/gov_check.sh` → 印出 `:500 for pf in $(grep -rl 'def test_mutation_' tests/governance/test_*.py ...)` ⇒ 現行掃描範圍**僅** `tests/governance/`，且**僅選中已宣告探針之檔**（opt-in）（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `grep -n "TODO_FILE" templates/TODO_GENERATION_PROMPT.md` → 印出第 21 行為一表格列，其 TODO 檔佔位符對應之值為 `docs/X_TODO.md`；`grep -n "^### Task" 同檔` → 印出 `:63`；`grep -c "" 同檔` → 印出 `111`（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `grep -c "" tests/momentum/Analysis/test_marginal_ic.py` → 印出 `617`；`grep -cE "^\s*def test_"` → 印出 `35`；`grep -c "parametrize"` → 印出 `0`（Claude 實跑 2026-09-22）
- FACT-RECEIPT: `ls docs/EVENTSCAN_TODO.md` → `No such file or directory`；`grep -n "^## §P" docs/EVENTSCAN_SPEC.md` → 印出 `:488` ⇒ **同類內容在不同票落在不同檔名**（Claude 實跑 2026-09-22）

### 現行啟發式之 fatal 名單（**不是**空心探針，見下述更正）

🔴 **2026-09-22 由 grok 實跑推翻主委原描述**：下列 12 支**確實觸及待測系統**，
之所以被標 fatal，是因 `scripts/mutation_probe_static.py:26-27,117` 之分類器**只認**
`SYSTEM_TOUCH_CALL` 與 `momentum`／`api`／`tests.references` 之 import，
**不認** `subprocess`、本地 helper、`monkeypatch.setenv`、`tests.fixtures`。
⇒ 本 SPEC 一律稱其為「**現行啟發式之 fatal 名單**」，**不得**稱空心探針或假綠。

量化層 12 支：`tests/momentum/Analysis/strategy_validation/test_wiring_check.py`（9 支，其 `_run(...)` 後斷言 `proc.returncode == 1`）、
`tests/momentum/Analysis/test_factor_return_analyzer.py::test_mutation_pos`（呼叫 `_make_test_analyzer()` 並 `np.allclose` 對 production）、
`tests/momentum/Analysis/test_ic_data_cache_hermetic.py::test_mutation_redirect_disabled_caught`、
`tests/momentum/Analysis/test_ic_persist_redirect_unit.py::test_mutation_disable_redirect_internal`（後二者用 `monkeypatch.setenv`）。

- FACT-RECEIPT: 同一靜態器對 `tests/governance/test_*.py` 扣除 `LEGACY_PROBE_DEBT` 三檔後 → rc=1、同句 fatal **27 行**（其中 `tests/governance/test_doc_format_precheck.py:382` 之探針會改 `template_check.sh` 再跑它）（grok 實跑 2026-09-22）
- FACT-RECEIPT: `scripts/gov_check.sh:498` 之排除清單僅含三個 `test_verify_gate` 檔，**不含**該 27 支（grok 實跑 2026-09-22）

⇒ **分類器本票不改**（另票處理）；**不重寫這 12 支探針**（RESID-1）；
Task 1.1 之真陽性斷言改為兩段（見該 Task）。

### 待使用者確認

**待確認：無**

### 已確認結果

- `2026-09-22 使用者「TODO 你寫成中文散文我也看不懂也不會去看，這完全是你跟委員間的產物…甚至你們自己能懂能精確了解執行的語言都可以」` ⇒ 工作文件形式之判準改為「主委與委員能否精確無歧義理解並執行」，不以使用者可讀性為約束。
- `2026-09-22 使用者「你跟委員先將TODO的優化完成，TODO相關的範本或格式或閘門等都要做相對應的更新。你跟委員把TODO優化這項目做完整做好，你不要自己亂搞」` ⇒ 本票範圍含範本與閘門之對應更新；須走完整管線。
- `2026-09-22 使用者「Governance 那個每次弄都要跑好幾小時，絕對嚴禁每次跑的什麼就等幾分鐘或時間一小時多，你跟委員不要把整個流程搞死無法前進」` ⇒ 見 §C 之 C-1～C-5（硬約束）。
- `2026-08-05 使用者「面向未來不溯及既往」` ⇒ 既有 `docs/*_TODO.md` 不遷移（見 §C C-6）。

---

## §C 約束（不重抄，引用 + 只列本任務相關）

解耦 7 條、不可違反原則（跨 tier／多 symbol／資料品質／不弱化 NaN·inf gate／不擅改輸出大小）依既有規定，本票不觸及數值路徑。

### 🔴 C-1～C-5：效能硬約束（2026-09-22 使用者定死，違反即整票退回）

- **C-1 不得引入分鐘級以上之檢查**（2026-09-22 使用者中途更正；原「≤ 2 秒」硬門檻係主委自行加碼，**已移除**）。使用者逐字：「我只有說不準碰那種跑很久，不是要你限定幾秒，怕你做不進 x 秒又在撞牆搞死自己」。
  - **可機械檢查之條件**：§V 之實測耗時欄**必須回填且不得仍為 `PENDING-MEASURE`**。
  - **偏慢時之處置**：不設死數字門檻；實測偏慢者交委員共識決——**砍範圍**或**列具名殘留**，二擇一，不得默默留著。
  - 量法：`date +%s%N` 前後差（奈秒精度）或 `time` 之 real 值；記錄實測值，不與門檻比對。
- **C-2 新增之寫檔當下檢查須擋在產出端**：本票**新增**之 per-write 檢查一律掛 `PreToolUse`／`PostToolUse` hook，於寫檔當下報。**既有批次入口（如 `gov_check.sh`）之範圍擴充不在此限**——其性質為批次而非 hook，見 Task 1.1。
  🔴 **實作期補強**（主委收案前自查，依 `CLAUDE.md` 產出端覆蓋鐵律）：manifest 之格式檢查原只在派工時（Task 1.3／1.4 之 `gate.sh`）執行，寫入當下無人報。另掛 `PostToolUse`（matcher `Edit|Write`）`scripts/todofmt_manifest_guard.sh`：所寫之檔之所在目錄即 repo 之 `docs/manifests`（`-ef` 比對；子目錄不管轄）且副檔名為 `.json` 時，以同一檢查器 `scripts/todofmt_check.sh` 判定，未過 ⇒ rc=2 並回報（`PostToolUse` 不回滾已寫入之內容）；派工時之檢查不變。具名測試於 `tests/governance/test_template_check_todofmt.py`（掛載、兩份實際 manifest 放行、合法放行、不合法擋、別名路徑、管轄外放行、`test_mutation_*` 一支）。依範本階段 2 之順序（先建空殼與測試檔、後寫 manifest），寫入當下即應可通過。
- **C-3 禁止擴成全量掃描**：mutation 靜態檢查維持 **opt-in**（僅選中已宣告 `def test_mutation_` 之檔）。**不得**在本票內改為「每個測試檔都必須有探針或 N/A」。
- **C-4 不得動 `pre-push`**：`pre-push` 維持 `gov_check.sh --fast`。本票**不得**新增任何項目進 `pre-push`。
- **C-5 不得引入 pytest 執行段**：本票所加之寫檔當下檢查**只准做靜態分析**（AST／grep／jq），**不得**在該路徑上執行 `pytest`。依 §A receipt：對**該批 26 檔**，靜態器 rc=1 並列出 12 支 fatal，pytest 段**額外**列出 **0** 支。🔴 此成立範圍限該批 26 檔，**不得外推**為「pytest 段普遍無價值」（見 RESID-4）。

### C-6～C-9：範圍與相容

- **C-6 不溯及既往**：設計定案 commit 之 git 樹中符合 Task 1.2 步驟 2 樣式之既有散文 TODO（樣式定義以該步驟為唯一權威，含任一層子目錄與延伸檔；r5／r6 grok 指出不得以 glob 舉例等同之）（`GAP1`／`GAP2`／`GAP3_EVENT`／`SPLITUNIFY`／`EVTLABEL`／`DOCROT2`／`REDISPATCH`／`VERDICTGATE` 等）**不遷移、不改寫**。**legacy 之界線＝設計定案 commit**（與 Task 1.2／1.4 字面陣列之來源一致）；新格式之**強制**自 W（首個已掛載且實作齊備之 commit）起生效。🔴 **設計定案至 W 之間不得新開任何票**（使用者 2026-09-22 已裁定「TODO優化完成後再討論下一步」，其餘票暫停）。**違反之機械後果＝§P「生效之判定」之窗口檢查 fail**：該期間任一 commit 新增之 `*_SPEC*.md` 或散文 TODO 皆使收案判定紅（含其後被刪除者；與其後是否再被寫入無關）。
- **C-7 不修 fatal 名單、不改分類器**：§A 具名之量化 12 支與治理 27 支（合計 39），本票**只讓它們被新入口列出**，**不修探針、不改分類器、不新增排除**。正確修法屬分類器認列規則之重新設計，另票處理（RESID-1）。
- **C-8 不改審查家數與家族**：依 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行，本檔不寫數字。
- **C-9 不合併 SPEC 審與 TODO 審**：依 r1 收斂檔 C7，§A（前提／FACT-RECEIPT）之審查槽必須保留且獨立。本票**不得**取消 SPEC 對抗審。

### 本任務會踩的共用路徑與既有 caller

| 路徑 | 現況 | 本票會如何動 |
|---|---|---|
| `templates/TODO_GENERATION_PROMPT.md` | 111 行，`:21` 寫死 `docs/X_TODO.md`、`:63` 寫死散文 Task 格式 | 改寫為新格式之生成指引 |
| `CLAUDE.md:30,38` | 「完整管線：SPEC + TODO + adversarial，不得跳步」 | 改寫「TODO」之定義為五類落點；**不放寬審查強度** |
| `docs/MULTI_AGENT_ORCHESTRATION.md` | 中型列同義敘述 | 同步改寫，避免第二權威 |
| `scripts/template_check.sh` | 有 `spec` 子命令 | 新增 `todofmt` 子命令（驗五類落點齊備） |
| `scripts/gate.sh` | `--todo` 旗標收 `docs/*_TODO.md` 路徑 | 接受新格式之 manifest 路徑 |
| `scripts/gov_check.sh` 第 6 段 | 呼叫含 pytest 段之 `mutation_probe_check.sh`，選檔範圍 `tests/governance/test_*.py` | 🔴 **完全不動**。改為**新增獨立靜態入口**與之並存（Task 1.1） |
| `.claude/settings.json` | hook 掛載點 | 新增產出端 hook 掛載 |

---

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### 🔴 本票之三個時點（r3 後主委自查：原文以「凍結」一詞同指兩個互斥時點）

| 時點 | 定義 | 允許之動作 |
|---|---|---|
| **設計定案** | 三家審查之 Verdict 皆無未閉合之「規格不完備」P0／P1 | 准予開始實作 Phase 0–3。**對應 `CLAUDE.md` 中／大管線之「SPEC 凍結」** |
| **生效時點** | ＝**首個已掛載且實作齊備之 commit**（下稱 W；機械定義見下「窗口檢查」）；故必於 Phase 0–3 之實作全部 commit 之後 | 既有散文 TODO 清單與既有 SPEC 清單以**字面陣列**寫入 hook／gate 腳本，且 hook 掛載於 `.claude/settings.json`——**三者於同一個 commit 完成** |
| **收案** | HEAD 為 W 或其後代時，§P 收案判定表之聚合入口 rc=0 | **先 commit W、後跑聚合器**（r7：使窗口檢查涵蓋 W 本身）；聚合器紅則以後續 commit 修正至 rc=0。W 至收案之間 hook 與 gate 分支已生效，方向為較嚴（fail-closed）；legacy 之**界線**則為設計定案 commit（見 C-6） |

⇒ 原文之「凍結前置」「凍結條件」「凍結判定表」語意皆為**收案**，已全數改稱。聚合入口檔名沿用 r3 收斂檔之 `scripts/todofmt_freeze_check.sh`，其語意為收案判定。
⇒ 「逐字不變」類之比較**一律 L 對 X、不擷取基準檔**（見收案判定表），故無擷取時點之紀律問題（r7 主委自查：原「設計定案之後、任何實作改動之前擷取」為紀律）。

### 🔴 生效之判定——結構性簡化（r5 主委提案 S1；r6 三家攻擊後修正）

**r2–r5 之經過**：r2 為「白名單只減不增」加 sha256 自保護 → r3 發現其與刪行衝突而改四句規則 →
r3 為避開實作期誤擋而把清單延至收案才寫 → r4 發現啟用空窗而加生效標記三態機與 `TODOFMT_LIST_DIR` 注入 →
r5 三家打穿三態機之組合判定與環境變數殘留。**每一輪之修補新增一層機制，該機制於下一輪生出新邊界。**
⇒ r5 以結構性簡化 S1 取代整層；r6 三家攻擊 S1，**抓出其兩處前提錯誤**（見下），已依三家修法修正，**皆未新增機制層**。

**現行設計**：
- 🔴 **既有清單＝腳本內之字面陣列**：兩份清單（既有散文 TODO、既有 SPEC），以字面陣列寫入 `scripts/` 下之 Task 1.2 hook 腳本，與 Task 1.4 之 `gate.sh` 分支（判 `--spec`／`--todo`）。**無獨立清單檔、無 sha256 自保護、無生效標記、無三態機、無環境變數。**
  （r2–r4 曾規劃之 `scripts/legacy_prose_todo.txt`／`scripts/legacy_spec_snapshot.txt`／`scripts/todofmt_active.marker` 三檔**於 S1 下全數不建立**。）
- 🔴 **陣列之輸入＝設計定案 commit（下稱 L，身分見下）之 git 樹，不是收案時之工作樹**（r6 三家獨立同判 S1 之前提「不存在意外加行」不成立：
  設計定案至收案之間 hook 未掛，其間新建之散文 TODO 若以收案時工作樹掃描生成，會被**意外**收進 legacy 陣列）：
  陣列內容＝`git ls-tree -r --name-only <L>` 之輸出，再套 Task 1.2 步驟 2 樣式（既有 SPEC 陣列比照，套 `docs/` 下任一層之 `*_SPEC*.md`）。
  未追蹤殘檔與設計定案後才 commit 之新檔**不會進集合**。
  `git ls-tree <L>` 為**一次性生成時**讀取不可變內容，非執行期之 git 狀態判定——hook 與 gate 執行時**只比對字面陣列**（r1 之「不得以 git 狀態判定」維持）。
- 🔴 **L 之身分**（r7 三家中二家同判：原「由實作之第一個 commit 寫入設計定案 sha」無法自 git 物件識別；grok 實測若 sha 誤取為 fixture commit，父樹 blob 比較恆等而弱化文本仍過）：
  **L＝本 SPEC 中首次出現「設計定案標記行」之 commit**：設計定案 commit 於本 SPEC 檔尾附加**恰一行**標記行（含設計定案收斂檔之 session 名）；標記行之**字面前綴唯一定義於 `tests/governance/_todofmt_anchor.py`**（實作時依已提交之標記行寫入），本 SPEC 之說明文字**不得含該前綴**。
  取得方式＝`git log --format=%H -S <標記前綴> -- docs/TODOFMT_SPEC.md` 須**恰印一行**，否則 fail（前綴於設計定案前已被寫出、或其後被刪除，皆使結果非一行）。本 SPEC、hook 腳本、`gate.sh` 皆**不複寫 L 之 sha**。
  🔴 **L 須先於實作**：L 之 git 樹中不得存在本票 manifest（`docs/manifests/TODOFMT.json`）之 `stub_modules`／`test_files`／`script_acceptance`／`contract_jsons` 所列之任一路徑，亦不得存在 `docs/manifests/TODOFMT.json` 本身；任一存在即 fail（防標記行晚於實作才補上）。
  🔴 **既有檔亦須先於實作**（r9 codex：上句只涵蓋新檔，先改既有之 `gate.sh`／settings 再補標記行時仍綠）：令 **A＝本 SPEC 中首次出現 `INV || ` 前綴之 commit**（`git log --reverse --format=%H -S 'INV || ' -- docs/TODOFMT_SPEC.md` 之第一行）；`git log --format=%H <A>..<L> -- <P>` 須為空，其中 P＝本票 manifest 之 `batch_card.touches` 中於 L 樹已存在之路徑、扣除本 SPEC。即自不變式行寫入起至設計定案，本票要改之既有檔一律未被改動。
  本票 manifest 之 `touches` **只列實作改動之檔**，不列交接與進度類檔（`HANDOFF.md`、`docs/ROADMAP.md`、`scripts/fact_keys.json`、`白話說明/` 下之檔）——後者每輪收斂皆會更新，列入則本句必紅（r10 前主委自查）。誤列時本句 fail，修 manifest 即可。
  ⇒ 憲法檔（屬 P）於 A 至 L 間不變，故 Task 2.2 以 L 之憲法檔計次數為有效基準；憲法不變式之原文則以 Task 2.2 寫於本 SPEC 之不變式行為準（r8 grok 實測：以 L 之憲法檔為原文時，先改弱 `CLAUDE.md` 再加標記行即過）。
  **L 之語意**（r8 codex）：L 為 **repo 狀態之錨點**，不代表本 SPEC 內容之終態；L 之後對本 SPEC 之修改（如 §V 耗時回填）不影響任何由 L 推導之集合。讀取 L 中本 SPEC 內容者**只有** Task 2.2 之不變式行，其於標記行之前即已寫入。
  所有需要 L 之測試（Task 1.2 邊界⑮⑰⑱、Task 1.4 邊界⑫⑬、Task 2.2、收案判定表「逐字不變」欄）與 W 之一次性陣列生成，皆經該模組之同一函式取得 L；A 與 W 亦由同一模組推導。本節凡稱「本票 manifest 所列」者，清單一律取自 X 版 `docs/manifests/TODOFMT.json`。
  **為何不以收斂檔錨定**：`handoffs/` 為本機排除路徑（`.git/info/exclude`），收斂檔從不入 git，「引入收斂檔之 commit」恆查無（主委 r7 修補時之前提錯誤，r8 前自查實跑 0 行）。
  **不採之兩案**：①「實作起始 commit 之 parent 即 L」——grok 實測以 F 之父樹反推 L 則比較恆等，錨點不得自後續 commit 反推；② git tag 標記——tag 為可於任何時點手動建立或移動之 ref，誤標於 fixture 之後之 HEAD 即重現同一反例；標記行之首次出現為固定之歷史事件。
- 🔴 **窗口檢查**（r7 codex／grok 同判：C-6「設計定案至收案間不得新開票」無機械後果——新 SPEC 不帶散文 TODO 時，hook 無對象、Task 1.4 邊界⑫只比對 L，可靜默通過）：
  令 **W＝首個「已掛載且實作齊備」之 commit**：依序走 `git rev-list --reverse <L>..HEAD`，取第一個同時滿足下列兩條件之 commit：
  (a) 該版 `.claude/settings.json` 之 `PreToolUse` 中存在一個 `matcher` 同時匹配 `Edit` 與 `Write` 之條目，其 `hooks` 含命令 `bash scripts/todofmt_write_guard.sh`（以 `jq` 判定；r8 codex 指出只搜字串會被放錯 matcher 或未生效之條目提前命中；此判定與 Task 1.2 之掛載對證**共用同一函式**）；
  (b) 該 commit 之樹中存在 `docs/manifests/TODOFMT.json` 及其 `stub_modules`／`test_files`／`script_acceptance`／`contract_jsons` 所列之全部路徑（與「L 須先於實作」對稱；r9 codex：只取首次掛載時，先掛 hook 再補其餘實作會使 W 過早、窗口提前結束），**且**存在 Phase 3 尾端之四個具名路徑：`scripts/todofmt_freeze_check.sh`、`tests/governance/test_todofmt_freeze_check.py`、`docs/manifests/FFTFMETA.json`、`tests/governance/test_todofmt_sample_fftfmeta.py`（r10 grok：Task 3.1 之 manifest 若只列當時已存在之路徑，該 commit 即滿足前半而成為 W，Task 3.2／3.3 落在窗口外；四路徑為本 SPEC 已寫死之交付，其存在不依賴 W）。
  **尚無該 commit 時 W＝HEAD**。先行掛載而實作未齊之 commit 不成為 W，故該期間仍在窗口內。W 之 gate 分支與兩組字面陣列另由 Task 1.4 之進入條件字面比對與 Task 1.2 邊界⑮、Task 1.4 邊界⑫ 以 X＝W 驗之。
  測試斷言：`git log --no-renames --diff-filter=A --name-only --format= <L>..<W>` 所列之**全部新增路徑**中，符合 Task 1.2 步驟 2 樣式者、與 `docs/` 下任一層 `*_SPEC*.md` 者，皆須為空；非空即 fail，訊息列出之（r8 codex：只比 W 之終點樹會漏掉窗口內新增後又刪除者）。
  W 一經存在即固定，故**收案後新開之票不使本檔測試失敗**；未 commit 之路徑不在任何 commit 上，本檢查看不見（領 token 仍經 Task 1.4）。`--no-renames` 使窗口內把既有檔移入 `docs/Archived/` 亦計為新增而 fail（方向為較嚴，且不受本機 rename 偵測設定影響）。
- 🔴 **陣列之機械對照**（r6 grok 指出「改腳本即三家 code review」**不成立**——現有機器只在下一次派 impl 時數前批家族數，**不讀陣列之 diff**，實為「記得去看那一行」＝紀律，違反使用者 2026-09-13「不接受紀律或記憶當解法」）：
  **測試斷言「字面陣列＝L 樹之符合路徑集合」**。往陣列**多加一行即使該測試失敗**——防線是這條測試，**不是 code review**。
  欲蓄意繞過須同時改掉該測試之預期集合（見 RESID-12）。
- 🔴 **生效＝掛載**：hook 掛於 `.claude/settings.json` 且 `gate.sh` 分支存在，即生效。**掛載前行為同現行**（hook 不存在即不執行）。
  字面陣列寫入、hook 掛載、gate 分支三者**於同一個 commit（W）完成**，故無啟用空窗。
- **測試**：直接呼叫判定函式並**以參數傳入清單**（測試用清單可置於 `tests/governance/fixtures/`）；生產呼叫**不傳參數**即用腳本字面。兩者為同一函式之不同呼叫，無「測試讀 A、生產讀 B」之分岔。

### Phase 0 — 落點定義與機械判定（依賴：無）

#### Task 0.1 — 定義五類落點之 manifest 契約（`票 TODOFMT/P0`）

- **目標**：產出 manifest 契約 JSON，machine-readable，定義一張票之 TODO 由哪些檔組成。
- **輸入／輸出**：契約檔之鍵集與值域（**每欄皆須標值域，非僅路徑容器**）：

  | 鍵 | 值域 | 承載 |
  |---|---|---|
  | `stub_modules` | 路徑陣列 | 生產模組空殼（簽章／dataclass） |
  | `test_files` | 路徑陣列 | 具名驗收測試、邊界測試、`test_mutation_*` |
  | `script_acceptance` | 路徑陣列 | `scripts/**` 之驗收腳本／探針（consult r1 第 2 類之另一半，與 `test_files` 分列） |
  | `contract_jsons` | 路徑陣列 | 鍵集、枚舉、reason 字面 |
  | `spec_path` | repo 相對路徑 | 🔴 本 manifest 所對應之 SPEC；Task 1.4 發 token 前須與 `--spec` 正規化後相等（防拿任一合法 manifest 領 token） |
  | `contract_digest` | 128 字元 hex | 🔴 **衍生值，不得手寫**（r5 主委提案 S2）：＝ **sha256(契約 JSON 檔之 canonical 形式) ∥ sha256(`scripts/todofmt_check.sh`)**（r6 三家同判 digest 若串接整份 `template_check.sh`（781 行、含其他子命令）範圍過寬；改為 todofmt 檢查器**獨立成檔**，digest 只涵蓋該檔），由 loader 計算。**判定規則不論改在契約 JSON 或改在 checker 程式碼，digest 皆變**、樣本皆失效。樣本記錄其產生時之值，與現行計算值不等即 fail（Task 3.1 之 invalidation 依此）；**樣本失效時只替換樣本之 `contract_digest` 欄**，不重寫 manifest 其餘內容。**取代手寫 `schema_version: vN`** |
  | `run_receipts` | 物件陣列 `{path, cmd, rc, honest_bounds}` | 🔴 **資訊性紀錄，不是收案之閘**（r5 主委提案 S4）：只驗 `path` 存在且位於 `handoffs/run_receipts/` 之下、檔內含 `schema_version`／`command`／`exit_code` 三鍵（沿用既有 receipt validator 之欄名）。**收案判定只看聚合器之新鮮執行結果**（見收案判定表），故 receipt 不需身分綁定 |
  | `batch_card.depends` | 字串陣列（Task id） | 批序 |
  | `batch_card.touches` | 路徑陣列 | 本批會動之檔 |
  | `batch_card.callers_now` | 路徑陣列（可空） | **現有**呼叫者 |
  | `batch_card.callers_later` | 路徑陣列（可空） | **後續批**才接線之呼叫者 |
  | `batch_card.relocates_to` / `relocates_at` | 路徑 / Task id | 跨批搬遷之目的地與時機 |
  | `batch_card.reexport` | 布林 | 搬遷後是否保留 re-export |
  | `batch_card.tests_stay` | 布林 | 搬遷時測試是否留原處 |
  | `batch_card.gate_cmd` | 非空字串 | 本批之驗收命令 |
  | `batch_card.forbidden` | 物件陣列 `{rule, observable}` | **負向約束**；`observable` 為布林，false 者須落 `not_executable` |
  | `batch_card.risk_mitigation` | 字串陣列 | **風險緩解**（如 oracle 產生器參數之權威落點） |
  | `batch_card.coverage_risk` | 字串陣列 | **覆蓋風險**（既有行為不得變更之處） |
  | `batch_card.lifecycle` | enum `keep`／`drop_after_ticket`／`supersede` | **生命周期**（取代散文「存活至」） |
  | `batch_card.not_executable` | 物件陣列 `{item, reason, owner, expiry}` | `reason` 值域＝封閉 enum（見下） |

- **封閉 reason enum**（`RESID_REASON_ENUM`，§N 之殘留理由值亦用同一 enum）：`blocked-by`／`user-ruling`／`needs-research`。
- 🔴 **契約 JSON 之單一落點＝`scripts/todofmt_contract.json`**（r5 composer 指出原未寫路徑）。
- 🔴 **契約 JSON 承載什麼、checker 承載什麼**（r5 主委提案 S2；r4 之「規則皆以資料承載」經 r5 三家同判過強，且 grok 之 `value_domain`＋五 op 規則語言係再加一層機制，**不採**）：
  - **契約 JSON 只承載**：鍵集、各欄型別、`required`（布林）、`exists_check`（布林）。🔴 `exists_check`：`batch_card.callers_later` 與 `batch_card.relocates_to` 為 **false**（指向尚不存在之未來落點屬合法，只驗路徑字串格式）；其餘路徑類欄位——`stub_modules`／`test_files`／`script_acceptance`／`contract_jsons`／`spec_path`／`run_receipts[].path`／`batch_card.touches`／`batch_card.callers_now`——為 **true**。
  - 🔴 **全部路徑類欄位之值域＝repo 相對路徑**（r9 codex：原只有 `spec_path` 標明 repo 相對，其餘只寫「路徑陣列」，自暫存 workdir 或 IDE 複製之絕對路徑可使 repo 外之檔通過 `exists_check`）：不得以 `/` 開頭、不得含 `..` 段；`exists_check=true` 者另以 `realpath` 解析後須位於 repo 根之下。`exists_check=false` 者（`callers_later`／`relocates_to`）同受前兩條字串規則約束。checker 先做此判定、後做存在性檢查。
  - **其餘判定規則為 checker 程式碼**：值域（enum／格式）、跨欄規則（例：`forbidden[].observable=false` ⇒ 須於 `not_executable` 有對應項）、`expiry` 日期比較等。**不以資料表達，不設計規則語言。**
  - **兩者皆由 `contract_digest` 涵蓋**（見上表）⇒ 不論改在哪，樣本皆失效。
  本表之「值域」「承載」兩欄為**說明**；與契約 JSON 或 checker 程式碼不一致時，以後二者為準。
- **不可做**：不得新增第六類落點；不得讓任一欄位值為自由散文（除 `not_executable.item` 與 `risk_mitigation`／`coverage_risk` 之描述文字，該三者允許自然語言但**不承載判定**）；**不得為表達判定規則而設計規則語言或 DSL**。
- **邊界**：① 五類皆空 ② 只有 `batch_card` ③ `not_executable.reason` 非三值之一 ④ `expiry` 已過期 ⑤ **`exists_check=true` 之欄位路徑不存在（須 fail）** ⑥ `gate_cmd` 為空字串 ⑦ `contract_digest` 與 loader 計算值不等 ⑧ `spec_path` 缺漏或為空 ⑨ `run_receipts` 之 receipt 檔內容缺三鍵之一（須 fail；receipt 為資訊性，只驗形狀） ⑩ **`exists_check=false` 之欄位指向不存在路徑（須放行）** ⑪ **`callers_now` 非空（須接受並驗其路徑存在）**（r4：原樣本只驗空值情形） ⑫ **只改 checker 腳本（不動契約 JSON）而 `contract_digest` 隨之改變**（證 digest 涵蓋程式碼中之規則） ⑬ **只改契約 JSON 之 `exists_check` 值而 `contract_digest` 隨之改變**（證 digest 涵蓋資料中之規則） ⑭ 路徑欄以 `/` 開頭（須 fail，即使該絕對路徑存在） ⑮ 路徑欄含 `..` 段（須 fail） ⑯ 路徑欄經 symlink 解析後位於 repo 根之外（須 fail）。
- **驗證**：`tests/governance/test_todofmt_contract.py`：**對本 Task 全部邊界各一具名測試**；契約鍵集與 loader 回傳鍵集相等；`contract_digest` 由 loader 計算之值與樣本記錄值之比較；`test_mutation_*` 探針一支（改壞值域即轉紅）。合法 manifest 之 `template_check.sh todofmt` 須 rc=0；缺 `batch_card` 之 manifest 須 rc 非 0（於測試內以 `subprocess` 斷言 rc，不在本 SPEC 內放可執行斷言行）。
- **存活至**：全票完工後保留（為新票之權威契約）。
- **覆蓋風險**：無（新增檔，無既有 caller）。

#### Task 0.2 — `template_check.sh todofmt` 子命令（`票 TODOFMT/P0`）

- **目標**：機械驗「一張票之 TODO 五類落點齊備且合法」，秒級。
- **實作要點**：檢查邏輯置於**獨立檔 `scripts/todofmt_check.sh`**，`template_check.sh todofmt` 子命令只轉呼叫之（r6：使 `contract_digest` 之 checker 部分只涵蓋此檔，`template_check.sh` 其他子命令之修改不使樣本失效）；純 `jq` ＋ 路徑存在性檢查；**禁止執行 pytest**（C-5）。
  🔴 **轉呼叫之唯一形式**（r7 codex／grok 同判：`template_check.sh` 之 `case` 結束後不退出，而以 `TEMPLATE PASS` rc=0 收尾——轉呼叫若不 `exec`，checker 拒絕仍得 rc=0，且 digest 不變；grok 以同結構宿主實跑重現）：
  於 `template_check.sh` 取得 `kind`／`file` 之行**之後、檔案存在性檢查之前**，恰一行 `[ "${kind}" = "todofmt" ] && exec bash "${SCRIPT_DIR}/todofmt_check.sh" "${file}"`。
  ⇒ 固定 checker 路徑、單一 manifest 參數、不改寫環境、rc 與 stdout 原樣為 checker 所出；檔不存在等情形亦由 checker 判定。digest 仍**只**涵蓋 `scripts/todofmt_check.sh`。
  **`template_check.sh` 既有之用法字串與 kind 錯誤訊息不列 `todofmt`，明確接受**（r9 codex）：`todofmt` 於用法檢查之前即已轉出，永不落到該等字串；其用法由 `scripts/todofmt_check.sh` 自身之用法訊息提供。故覆蓋風險之「差異恰為一行」維持。
- **不可做**：不得讀取測試內容做語義判斷；不得掃全 repo；轉呼叫行不得為上述以外之形式。
- **邊界**：① manifest 不存在 ② JSON 不合法 ③ 缺任一類 ④ **`exists_check=true` 之欄位**路徑不存在（依契約 JSON 之 `exists_check` 判定，r4 指出原文未指向例外即會對全部路徑欄套存在性檢查而誤殺） ⑤ `not_executable` 缺 owner ⑥ `expiry` 格式非 `YYYY-MM-DD` ⑦ `exists_check=false` 之欄位指向不存在路徑（須放行） ⑧ **對①–⑦ 每一輸入及一份合法 manifest，`template_check.sh todofmt <M>` 之 rc 與 stdout 皆等於 `todofmt_check.sh <M>` 者** ⑨ **上述轉呼叫行於 `template_check.sh` 中恰出現一次**（字面比對）。
- **驗證**：`tests/governance/test_template_check_todofmt.py`：對本 Task 全部邊界各一具名測試；耗時以 `date +%s%N` 前後差量測並**記錄**至 §V（**不與任何門檻比對**，依 C-1）；`test_mutation_*` 一支（將轉呼叫行之 `exec` 移除即轉紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`template_check.sh` 既有子命令行為不得改變——回歸測試斷言 **`scripts/template_check.sh` 相對 L 之差異恰為新增上述轉呼叫行一行**（無刪除行、無其他新增行；比較端見收案判定表之 X）。該行位於所有子命令之前且只在 `kind=todofmt` 時生效，故差異恰為此行即證其他子命令不變。

### Phase 1 — 產出端 hook 與 mutation 靜態擴覆蓋（依賴：Phase 0）

#### Task 1.1 — mutation 靜態檢查擴至量化三層（`票 TODOFMT/P1`）

- **目標**：**新增一個獨立的靜態入口**，選檔範圍為 `tests/{governance,momentum,api,feature_engineering}`，**維持 opt-in**，**僅跑靜態器**。
- 🔴 **不改 `gov_check.sh` 既有第 6 段**（r1 三家同判：該段呼叫的是含 pytest 段之 `mutation_probe_check.sh`，「擴覆蓋」若改動它即同時改變既有治理行為）。新入口與既有第 6 段**並存且各自具名**。
- **實作要點**：新入口只呼叫 `scripts/mutation_probe_static.py`；不呼叫 `mutation_probe_check.sh`。
  🔴 **入口之具名契約**（r9 codex：原未指定檔名、參數與觸發時機）：`scripts/mutation_scope_static.sh`，**無參數**；自行以 `grep -rl 'def test_mutation_'` 於上述四個目錄選檔（逐目錄明列，禁無參數之 pytest 或全 repo 掃描），逐檔以參數傳給靜態器；stdout 印 fatal 名單，rc 為靜態器之 rc。**僅手動呼叫**：不掛 hook、不入 `pre-push`、不入 `gov_check.sh`、不入聚合器之執行陣列（其測試檔入之）。
- **不可做**：不得改為強制（C-3）；不得在此路徑執行 pytest（C-5）；不得修 §A 具名之 12 支（C-7）；不得改分類器；**不得新增 `LEGACY_PROBE_DEBT` 排除項**（新增排除會使治理層之 27 支消失，改變既有態）。
- **邊界**：① 量化層零檔有探針 ② 只有 `tests/api` 有 ③ 既有第 6 段通過句之來源字面同時存在於 L 與 X（見覆蓋風險；不跑第 6 段） ④ fatal 名單被正確列出 ⑤ 非 fatal 之探針不誤列 ⑥ 檔案不存在。
- **驗證**：`tests/governance/test_mutation_scope_extension.py`，**真陽性斷言分兩段、皆只跑靜態器**：
  - (i) 量化 26 檔之 fatal 名字集合**等於** §A 具名之 12 支（具名比對，不多不少）；
  - (ii) `tests/governance` 扣除既有三檔後之 fatal 集合**維持 27 支**（具名寫進測試，**不新增排除**）。
  另對本 Task 全部邊界各一具名測試；耗時以 `date +%s%N` 記錄並寫入 §V（**不與門檻比對**，依 C-1）；`test_mutation_*` 一支（改壞選檔 glob 即轉紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：🔴 新入口之 rc 會因 12＋27＝39 支而非 0。⇒ **新入口之 rc 不接進任何既有 fail-stop 鏈**，僅輸出名單供人看；其「該不該紅」之裁決屬分類器另票。既有第 6 段之回歸：第 6 段通過句之來源字面（常數寫於本 Task 測試檔）須同時為 `git show <L>:scripts/gov_check.sh` 與 X 版 `scripts/gov_check.sh` 之子字串；**不為此而跑第 6 段**。

#### Task 1.3 — `gate.sh --todo` 機械判型路由（`票 TODOFMT/P1`）

- 🔴 **起因**（r1 三家同判）：`--todo` 有值時 `gate.sh` **無條件**呼叫 legacy `template_check.sh todo`，該子命令要求 markdown 錨點（`## §0` 等）⇒ **新格式 manifest 必被擋**，C-6 之並存在命令路由上未落地。
- **目標**：`gate.sh` 依 `--todo` 之**機械判型**路由，判型規則須可機械導出、不得靠散文說明。
- **判型規則（封閉）**：副檔名**經 `casefold` 後**為 `.md` ⇒ legacy 路徑（`template_check.sh todo`）；`casefold` 後為 `.json` 且頂層含 `stub_modules` 鍵 ⇒ 新路徑（`template_check.sh todofmt`）；其餘 ⇒ fail-closed 並印兩種合法形式。
  🔴 **`casefold` 為必要**（r2 指出：本機大小寫不敏感卷上 `X_TODO.MD` 會判不出 legacy）。
- 🔴 **`--manifest` 等既有旗標不受影響**（r2 指出原文未定義）：本 Task **只改 `--todo` 之分派**，其餘旗標之路徑解析與 rc 語義逐字不變，並以回歸測試斷言。
- **不可做**：不得以內容啟發式猜測；不得讓同一輸入同時進兩條路徑；不得改動 legacy 路徑之 rc 語義。
- **邊界**：① `.md` 走 legacy 且 rc 語義不變 ② 合法 manifest 走新路徑 ③ `.json` 但缺 `stub_modules` ④ 副檔名為 `.yaml` ⑤ 檔不存在 ⑥ **同一次呼叫重複給 `--todo`**（如同時給 `--todo X.md` 與 `--todo Y.json`）⇒ fail-closed（r3 指出原「兩種皆給」未給與「不做內容嗅探」相容之具體輸入；判型只看副檔名與 JSON 頂層鍵） ⑦ 副檔名大小寫變體 `X_TODO.MD`（`casefold` 後走 legacy）。
- **驗證**：`tests/governance/test_gate_todo_routing.py`：對本 Task 全部邊界各一具名測試；legacy 路徑之回歸＝legacy 分支之呼叫字面 `bash scripts/template_check.sh todo "${todo}"` 須同時為 `git show <L>:scripts/gate.sh` 與 X 版 `scripts/gate.sh` 之子字串，且邊界①以既有治理測試隔離實跑 `.md` 路徑之 rc（r8 grok：以 `gate.sh` 輸出為基準會被債務狀態與未列入之 callee 左右）；`test_mutation_*` 一支（改壞判型即轉紅）。
- **存活至**：`lifecycle: keep`。
- **覆蓋風險**：`gate.sh` 為全專案共用控制流——改動須有回歸測試斷言 `dispatch`／`artifact`／`register-output` 三條既有路徑行為不變。

#### Task 1.4 — `gate.sh` 於 impl 派工強制要求 manifest（`票 TODOFMT/P1`）

- 🔴 **起因（r2 最重之單條）**：`scripts/gate.sh:1004-1006` 僅在 `--todo` **非空**時呼叫檢查；
  `:927` 對高風險派工只要求 `--spec`，**不要求** `--todo`。
  ⇒ 新票只交 `--spec`、省略 `--todo`，則 Task 1.2 之 hook 無路徑可擋、檢查條件為假，
  **整套五類落點檢查被完全繞過而 token 照發**。現成案例＝`docs/EVENTSCAN_SPEC.md`（有 SPEC、無 TODO 檔）。
- **目標**：`--spec` 有值時**強制要求** `--todo`，且其須為新格式 manifest。
- **實作要點**（插在 `scripts/gate.sh` 發 token 之前、與 Task 1.3 同一段；**`--impl-self` 走同一段**；`scripts/dispatch.sh` 以 `exec gate.sh` 單點收口，無須另做）：
  1. `--spec` 經正規化後命中 **`gate.sh` 內之既有 SPEC 字面陣列**（於 W 一次生成；見 §P「生效之判定」S1）⇒ 放行（C-6）。
  2. 否則 `--todo` 缺值 ⇒ **fail-closed**，訊息印出五類落點與生成指引之路徑 `templates/TODO_GENERATION_PROMPT.md`（Task 2.1 改寫後之版本）。
  3. `--todo` 有值但判型為 legacy `.md` 且 `--spec` 不在既有清單 ⇒ fail-closed。
  4. 🔴 **manifest 與 SPEC 之對應**（r3 grok 指出可拿任一合法 manifest 為新 SPEC 領 token）：manifest 之 `spec_path` 經與 Task 1.2 步驟 1 相同之正規化（剝根、剝 `./`、`casefold`）後，**必須等於**同樣正規化後之 `--spec`；不等 ⇒ fail-closed。一次 `jq` 字串比較。
  5. 🔴 **`--manifest` 不得替代 `--todo`**（r3 codex／composer 同判）：`--manifest` 維持既有 coverage 參數之語義，**不計入**本 Task 之「已提供 manifest」判定。
- **生效**：本 Task 之 `gate.sh` 分支於 W（首個已掛載且實作齊備之 commit）加入即生效；**加入前行為同現行**（見 §P「生效之判定」S1）。無生效標記、無三態判定。
- **參數矩陣**（封閉；未列之組合一律 fail-closed）：

  | `--spec` | `--todo` | `--manifest` | `--impl-self` | 結果 |
  |---|---|---|---|---|
  | 既有清單內 | 任意或缺 | 任意 | 任意 | 放行（C-6） |
  | 新 | 缺 | 任意 | 任意 | **擋** |
  | 新 | legacy `.md` | 任意 | 任意 | **擋** |
  | 新 | manifest，`spec_path` 相等 | 任意 | 任意 | 放行 |
  | 新 | manifest，`spec_path` 不等 | 任意 | 任意 | **擋** |
  | 缺 | 任意 | 任意 | **有** | **擋**（r4：impl token 必須有 `--spec` 與合法 manifest；現行 token writer 確有此路徑） |
  | 缺 | 任意 | 任意 | 缺 | 非 impl 路徑，本 Task 不介入 |

- **不可做**：不得放行「新 SPEC ＋ legacy 散文 TODO」之組合；不得改動 `--spec`／`--manifest` 之既有語義；**不得以內容 digest 判定既有 SPEC**（見 RESID-10）。
- 🔴 **本矩陣之「放行」只就本 Task 之判定而言**：`--spec` 仍須通過既有之 `template_check.sh spec`（`scripts/gate.sh` 既有行為，本 Task 不改）。
- **邊界**：① 新 SPEC ＋ 無 `--todo`（擋） ② 新 SPEC ＋ manifest 且 `spec_path` 相等（放行；夾具之 SPEC 須通過 `template_check.sh spec`——以參數傳入不含 `docs/TODOFMT_SPEC.md` 之既有清單，令該檔充當新 SPEC；**不得**以 `docs/FFDEFECT_DECISION.md` 充當，r8 grok 實跑其 `template_check.sh spec` rc=1） ③ 既有 SPEC ＋ 無 `--todo`（放行） ④ 既有 SPEC ＋ 散文 TODO（放行） ⑤ 新 SPEC ＋ 散文 TODO（擋） ⑥ `--spec` 之大小寫變體或 `./` 前綴命中既有 SPEC 字面陣列（放行，須正規化後判定） ⑦ 新 SPEC ＋ manifest 但 `spec_path` 不等（擋） ⑧ 新 SPEC ＋ 只給 `--manifest` 未給 `--todo`（擋） ⑨ `--impl-self` ＋ 新 SPEC ＋ 無 `--todo`（擋） ⑩ **`--impl-self` ＋ 無 `--spec`**（擋） ⑪ 生產呼叫所用之既有 SPEC 陣列＝`gate.sh` 腳本字面（斷言不讀任何外部清單檔） ⑫ **X 版 `gate.sh` 之既有 SPEC 字面陣列＝L 樹之 `docs/` 下任一層全部 `*_SPEC*.md`**（不等即 fail） ⑬ **窗口檢查之 SPEC 半邊**（§P「生效之判定」）：L..W 區間新增之路徑中無 `docs/` 下任一層之 `*_SPEC*.md`（含其後被刪除者）。 ⑭ `--spec`／`--todo` 含控制字元（例：既有 SPEC 接換行再接新檔名、尾端換行）（擋；b3 審碼 codex／grok：逐行比對會命中其中一行而誤報放行） ⑮ `--spec` 經正規化後為空字串（例：`./`、repo 根加尾斜線）（擋；r2 grok 正文：逐行比對會命中字面陣列開頭之空行而誤報放行——派工路徑上雖有範本機檢先擋，判定函式之結果不得倚賴其他檢查之先後）。
- **驗證**：`tests/governance/test_gate_impl_requires_manifest.py`：對本 Task 全部邊界各一具名測試；
  `dispatch` 之非 impl 路徑（無 `--spec` **且**無 `--impl-self`）之回歸＝以既有治理測試隔離實跑該路徑，斷言 rc=0 且輸出不含本 Task 之任何拒絕訊息；另斷言本 Task 區塊之進入條件只含 `--spec` 非空或 `--impl-self`（字面比對 X 版 `scripts/gate.sh`）；`test_mutation_*` 一支。
- **存活至**：`lifecycle: keep`。
- **覆蓋風險**：`gate.sh` 為全專案共用控制流；本 Task 與 Task 1.3 同檔改動，須合併為單一 diff 並同批回歸。
  🔴 **實作期補記**（同批回歸實跑查出）：邊界⑩使主委自任實作（`--impl-self`）必帶 `--spec`，而 `--spec` 為 `gate.sh` 既有之 impl 判準——帶上即連帶要求 impl 型 `--brief`（含 EXPECTED-DELTA）、`--reconcile` 之 session 收斂檔與戳記、SPEC 範本機檢；新 SPEC 另須 `--todo` manifest。此與 VERDICTGATE SPEC C-6「主委路徑與委員路徑走同一道判定」一致。`tests/governance/test_verdictgate_p3.py` 三條以 `--impl-self` 不帶 `--spec` 而期望發 token 之測試因此轉紅，已改其派工夾具滿足上述閘（該三條所測之 verdictgate／quorum 斷言不動）。

#### Task 1.2 — 產出端 hook：新票寫散文 TODO 即擋（`票 TODOFMT/P1`）

- **目標**：`PreToolUse` hook（腳本 `scripts/todofmt_write_guard.sh`），於 Write／Edit 建立**新的**散文 TODO（`docs/` 下任一層、檔名符合下述樣式者，含延伸檔）時 fail-closed，並印出五類落點指引。
- 🔴 **判定不得依賴 git 狀態**（r1 三家各自獨立打穿 `git ls-files` 版：已 `git add` 之佔位檔會被當成既有檔；hook 收到之**絕對路徑**與 `./` 前綴皆不在 `git ls-files` 輸出中）。
- **生效**：本 hook 掛載於 `.claude/settings.json` 即生效；**掛載前不存在即不執行**（見 §P「生效之判定」S1）。無生效標記、無三態判定。
- **實作要點**（**順序即判定順序**，不得調換）：
  1. **字串層正規化**：剝 repo root 前綴、剝 `./`，得 repo 相對路徑；整串 `casefold`（本機為大小寫不敏感卷；例：`Docs/X_Todo.md` 正規化後即 `docs/x_todo.md`，不得繞過）。
  2. 🔴 **先比樣式、後解 symlink**（r3 指出先 `realpath` 會使指向白名單之 symlink 改變判定）：
     路徑首段為 `docs`（**任一層子目錄皆算**，例：`docs/sub/X_TODO.md`）且**檔名**符合 `^[a-z0-9_]+_todo(\.[a-z0-9-]+)?\.md$`
     （涵蓋 `X_TODO.md` 與延伸檔 `X_TODO.D-001.md`，比對前已 casefold；r3 指出原樣式放行 `docs/NEWEPIC_TODO.D-001.md`）
     ⇒ 進入白名單比對；否則放行（非本 hook 管轄）。
  3. **既有清單比對**：以步驟 1 之字串比對 hook 腳本內之字面陣列；另以 `realpath` 解析後之路徑**再比一次**，兩者任一命中即視為命中（涵蓋 symlink 指向既有清單內檔案之情形）。
     🔴 **硬連結別名不放行**（r8 codex 實測：硬連結與原檔共用 inode，但 `realpath` 保留別名路徑，不會化為清單內之原路徑）：以別名路徑寫入者視為新路徑而擋，經清單內之原路徑編輯者放行。不做 inode 比對——git 不追蹤硬連結，`docs/` 下之別名只能是手動建立，擋下之方向為較嚴。
  4. 命中既有清單 ⇒ 放行（C-6）；未命中 ⇒ fail-closed 並印五類落點指引。
- 🔴 **實作期補強**（b3 審碼 r1：codex P1、grok P2；主委實測 Write 工具會字面折疊 `..`，經不存在之目錄亦照寫）——皆使更多路徑落入判定，不使任何路徑少判：
  - 步驟 1 之前：路徑值含控制字元（換行、tab 等）⇒ 擋。於 JSON 字串層以 `jq` 判定（命令替換會吃掉尾端換行）。步驟 3 之逐行比對會把換行拆成多個樣式——「清單內之檔＋換行＋新檔名」曾被當成清單內之檔而放行；步驟 3 之比對函式對含控制字元之值亦一律不算命中。
  - 步驟 1 之字串層正規化另含**字面折疊** `.`／`..`／空段（與 Write 工具一致；剝 `./` 為其特例）。
  - 步驟 2 之「首段為 docs」於字串層不成立時，再以 `-ef`（同裝置同 inode）由近而遠比對祖先目錄是否即 repo 之 `docs`，命中即以其下之剩餘段為 `docs/` 下之路徑（涵蓋指向 repo 之符號連結、repo 內指向 `docs` 之目錄別名、`/System/Volumes/Data` 等 firmlink 別名）。**只比祖先目錄、不解檔案本身**，故「先比樣式、後解 symlink」對檔名仍成立。
  - Task 1.4 步驟 4 之正規化維持其括號所列三項：`gate.sh` 之兩處比對（既有 SPEC 陣列、`spec_path` 相等）遇非正規形式皆落向較嚴（視為新 SPEC、或 `spec_path` 不等而拒），無放行方向之缺口；含控制字元之 `--spec`／`--todo` 比照本節即拒（Task 1.4 邊界⑭）。
- 🔴 **既有清單（字面陣列）之內容**（r4 grok 實查：若以 `docs/*_TODO.md` glob 定義，現存 69 個命中樣式之檔中有 **12 個**——延伸檔 7（`docs/GAP3_EVENT_TODO.D-001.md`、`docs/GAP3_EVENT_UX_TODO.D-001.md` 至 `D-006.md`）、`docs/Archived/` 下 5 個——不在該 glob 內，生效後其合法編輯會被誤擋）：
  **內容＝L 之 git 樹中，符合本 Task 步驟 2 樣式之全部路徑**（`git ls-tree -r --name-only <L>` 再套樣式；含延伸檔與任一層子目錄；L 之身分見 §P「生效之判定」），正規化並排序後寫為 hook 腳本內之字面陣列。**不以 `docs/*_TODO.md` glob 當全集；不取收案時之工作樹**（r6 三家同判：設計定案至收案之間新建之散文 TODO 會被意外收進）。
  新延伸檔因不在該陣列內仍被擋（r3 之原反例不會回來）。Task 1.4 `gate.sh` 內之既有 SPEC 字面陣列比照：L 之 git 樹中 `docs/` 下任一層全部 `*_SPEC*.md`。
- 🔴 **陣列之機械對照**（r2–r4 之 sha256 自保護四句與首次寫入例外**全數移除**；r6 grok 指出「改腳本即三家 code review」實為紀律，**已刪除該等同**）：
  **測試斷言「hook 腳本之字面陣列＝L 樹之符合路徑集合」**（見 §P「生效之判定」）——往陣列多加一行即使該測試失敗。欲蓄意繞過須同時改掉該測試之預期集合，列 RESID-12 蓄意等價。
- **不可做**：不得擋既有清單內檔案之編輯；不得掃全 repo；不得執行 pytest；**不得以 git 狀態（`ls-files`／`status`／`diff`）作為判定依據**；**不得另建獨立清單檔**。
- **邊界**：① 新建 `docs/X_TODO.md`（擋） ② 編輯既有清單內之 `docs/GAP2_MARGINAL_IC_TODO.md`（放行） ③ 新建 `docs/X_TODO.yaml`（放行） ④ 路徑含空白 ⑤ 傳入**絕對路徑**或 `./docs/X_TODO.md`（須正規化後正確判定） ⑥ 已 `git add` 但未 commit 之新散文 TODO（**須擋**） ⑦ symlink 指向既有清單內檔案（放行） ⑧ **大小寫變體** `Docs/X_Todo.md`（須擋） ⑨ **子目錄** `docs/sub/X_TODO.md`（須擋） ⑩ 硬連結別名指向既有清單內檔案，以別名路徑寫入（擋） ⑪ **延伸檔** `docs/NEWEPIC_TODO.D-001.md`（須擋） ⑫ 編輯**既有延伸檔** `docs/GAP3_EVENT_TODO.D-001.md`（放行，因在字面陣列內） ⑬ 編輯 `docs/Archived/` 下既有之 `*_TODO.md`（放行） ⑭ **生產呼叫（不傳清單參數）使用之陣列＝腳本字面**，與測試傳入之陣列為同一函式之不同呼叫（斷言生產路徑不讀任何外部檔） ⑮ **X 版 hook 腳本之字面陣列＝L 樹之符合路徑集合**（不等即 fail；往陣列多加一行、或設計定案後才建立之散文 TODO 被收進陣列，皆使本測試失敗） ⑯ 設計定案後新建之 `docs/LATE_TODO.md`（不在陣列內，生效後須擋） ⑰ **窗口檢查之 TODO 半邊**（§P「生效之判定」）：L..W 區間新增之路徑中無符合樣式者 ⑱ **既有散文 TODO 內容不變**（r9 codex：只守路徑集合，不守 C-6 之「不改寫」）：L 樹中符合樣式之每一路徑，其 X 版內容須與 `git show <L>:<路徑>` **逐位元組相等**，**但生成區塊（`gen_fact_key_blocks.sh` 所維護之成對起訖註解標記行）之間之內容不比**（r10 codex 實查：`docs/DOCROT2_TODO.md`、`docs/SPLITUNIFY_TODO.md` 含生成區塊，由 `gen_fact_key_blocks.sh --write` 依 `scripts/fact_keys.json` 正常改寫，屬另一系統之狀態鏡像而非本票之改寫）；標記行本身之序列須兩版相同（生成區塊不得增刪）。比較值取原始位元組、不經換行轉換（實作期審碼 codex：以文字讀入再逐行重組會抹平末換行與 CRLF 之差異）。X＝W 時收案後之合法續修不受影響。 ⑲ 路徑值含控制字元（例：`docs/GAP2_MARGINAL_IC_TODO.md` 接換行再接新檔名、尾端換行、tab）（擋） ⑳ 含 `..` 段之路徑（含經不存在之目錄者）依字面折疊後判定 ㉑ 經指向 repo 根之符號連結、或 repo 內指向 `docs` 之目錄別名寫入新散文 TODO（擋；經別名編輯清單內之檔放行）。
- **驗證**：`tests/governance/test_todofmt_write_guard.py`：對本 Task 全部邊界各一具名測試；hook 掛載點與 `.claude/settings.json` **機械對證**（比照既有 `factkey_write_guard` 之對證作法）；耗時以 `date +%s%N` 記錄寫入 §V（依 C-1 不比門檻）；`test_mutation_*` 一支。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`.claude/settings.json` 為共用掛載點，新增條目不得影響既有 hook 之觸發順序——須有回歸測試斷言 **`git show <L>:.claude/settings.json` 之 hook 清單**為 X 版清單之子集（直接取自 L，無基準檔）。

### Phase 2 — 範本與憲法同步（依賴：Phase 1）

#### Task 2.1 — 改寫 `templates/TODO_GENERATION_PROMPT.md`（`票 TODOFMT/P2`）

- **目標**：自「生成一份 markdown 散文 TODO」改為「生成五類落點」。
- **不可做**：不得保留 `docs/X_TODO.md` 之字面（否則執行端仍會照舊生成）；不得同時保留新舊兩套格式說明。
- **邊界**：① 範本內仍殘留 `docs/X_TODO.md` ② 仍含 markdown Task 區塊 ③ 缺五類任一之說明 ④ 缺 `not_executable` 三值說明 ⑤ 新舊並存 ⑥ 佔位符未替換。
- **驗證**：`tests/governance/test_todofmt_template.py`：對本 Task 全部邊界各一機械斷言（`grep -c` 式）；`test_mutation_*` 一支。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`scripts/new_brief.sh` 若引用本範本之章節標題，改標題會斷——須先 grep 確認引用點並同批更新。

#### Task 2.2 — `CLAUDE.md` 與 ORCH 同步（`票 TODOFMT/P2`）

- **目標**：`CLAUDE.md:30,38` 與 `docs/MULTI_AGENT_ORCHESTRATION.md` 中型列，將「TODO」之定義改為五類落點。
- **不可做**：🔴 **不得放寬審查強度**——對抗式審查、實作者不自審、家數（ORCH §1）、不得跳步四項逐字不動；不得取消 SPEC 對抗審（C-9）；`CLAUDE.md` 不得自寫家數。
- **邊界**：① 只改 `CLAUDE.md` 未改 ORCH（產生第二權威） ② 改動誤及「不得跳步」之審查強度語義 ③ 家數字面被寫入 `CLAUDE.md` ④ 既有 `--spec/--todo` 旗標說明失效 ⑤ 觸發句表失同步 ⑥ 交叉引用殘留 ⑦ **L 之本 SPEC 中某一 `INV || ` 行之片段不為現行所屬檔之子字串**（即 fail；防本 Task 或其後之改弱） ⑧ 四項 (i)–(iv) 任一項於 L 之本 SPEC 中無 `INV || ` 行（即 fail） ⑨ `INV || ` 行不為四欄（即 fail） ⑩ `INV || ` 行之片段含 `TODO` 字樣（即 fail；本 Task 本身即改 TODO 之定義，含之則被自己的合法修改打紅） ⑪ 某片段於現行所屬檔之出現次數少於其於 L 之所屬檔（即 fail）。
- **驗證**：`tests/governance/test_todofmt_constitution_sync.py`：
  1. 🔴 **審查強度四項不變式之逐字比對**（r1 三家同判：只比對 TODO 定義一致性，抓不到「兩份文件一起被改弱」；r2 加入第四項；r3 指出原標題仍寫「三段」且無 exact literal）。
     🔴 **不變式之原文寫於本 SPEC、隨設計定案進入 L，由三家審 SPEC 時對讀**（r8 grok 實測：以 L 之憲法檔為準時，先改弱 `CLAUDE.md` 再加標記行即過；原文寫在 SPEC，則後到之改弱改不到它）。
     **不另建 fixture 檔**：測試以 `git show <L>:docs/TODOFMT_SPEC.md` 取行首為 `INV || ` 之行（固定前綴之逐行擷取，非散文解析），每行四欄＝`INV || <項> || <所屬檔> || <片段>`；斷言每一片段為**現行**所屬檔之子字串。
     🔴 **片段而非整行**（r8 主委自查：r7 所改之「整行相等」與本 Task 自身衝突——本 Task 正是要改 `CLAUDE.md:30,38` 與 ORCH 中型列這幾行之 TODO 定義，整行相等必被自己的合法修改打紅）：片段一律**不含 `TODO` 字樣**，只取該不變式之核心句。
     四項為：(i) 對抗式審查之要求 (ii) 實作者不自審之要求 (iii) 家數與家族指向 ORCH §1 現行分工行 (iv) 「不得跳步」。四項之原文只見於 `CLAUDE.md` 與 `docs/MULTI_AGENT_ORCHESTRATION.md`（主委 r8 實查：`AGENTS.md`／`.cursorrules` 不含此四項，二者只列於步驟 1b 之掃描範圍）。

```
INV || i || CLAUDE.md || adversarial 都要）
INV || i || CLAUDE.md || adversarial**，**不得跳步/不跳**（D-1）
INV || i || docs/MULTI_AGENT_ORCHESTRATION.md || **adversarial 稽核 = §1 現行分工行所列之全部審查家族都跑**
INV || ii || CLAUDE.md || ；實作者不自審
INV || ii || docs/MULTI_AGENT_ORCHESTRATION.md || 中/大必派，實作者不自審
INV || iii || CLAUDE.md || code review 之家數與家族＝`docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行
INV || iii || CLAUDE.md || **家數與家族＝`ORCH §1 現行分工行`（唯一來源，本檔不重述）**
INV || iv || CLAUDE.md || ① 完整管線不得跳步
INV || iv || CLAUDE.md || **不得跳步/不跳**（D-1）
INV || iv || docs/MULTI_AGENT_ORCHESTRATION.md || 使用者定死不得跳步,D-1 維持
```

     🔴 **次數不得減少**（r9 codex：`；實作者不自審` 於 `CLAUDE.md` 出現兩次，刪去其一仍綠）：每一片段於現行所屬檔之出現次數須 **≥** 其於 `git show <L>:<所屬檔>` 之出現次數。L 之憲法檔為有效基準，因 A 至 L 間本票要改之既有檔（含憲法檔）已由 §P「既有檔亦須先於實作」鎖定不變。
     **誠實邊界**：於片段所在行附加限縮條件而片段本身與次數皆不動時，本步驟不擋（由步驟 1b 之關鍵詞掃描承接，屬 RESID-8 之範圍）。
  1b. 🔴 **例外條款偵測**（r2 指出：字面逐字保留但可在他處新增例外抵銷）：對 `CLAUDE.md`／`docs/MULTI_AGENT_ORCHESTRATION.md`／`AGENTS.md`／`.cursorrules` 四份檔之**新增行**掃描，凡新增行同時命中「審查／對抗／自審／家數」任一關鍵詞**且**命中「例外／不適用／可略／免」任一者 ⇒ fail。
     **新增行之基準＝L**（r7 主委自查：原未定義相對何者為「新增」）：＝`git diff <L> -- <四份檔>` 之新增行。L 中既有之行不在掃描範圍。
     🔴 **放行方式改為已提交之清單檔**（r3 指出原「人工裁決後具名放行」不可機械判定）：`tests/governance/fixtures/constitution_exception_allowlist.txt`，每行為被放行行之 sha256；測試**只對清單外之命中** fail。清單**初始為空**——r3 實測之歷史命中行皆已存在於 L，不屬新增行。
     **誠實邊界**：此為關鍵詞啟發式，非封閉集合，可被改寫繞過；其角色是提醒不是保證，已具名為 RESID-8。
  2. `CLAUDE.md` 與 ORCH 之 TODO 定義字面一致性機械斷言。
  3. `grep -c` 確認家數數字未被寫入 `CLAUDE.md`。
  4. 全 repo 殘留掃描：`templates/` ＋ `scripts/` 內佔位符字面 `docs/X_TODO.md` 之命中數應為 0（r3 指出原「舊散文 TODO 路徑樣式」未定義；既有 `docs/<EPIC>_TODO.md` 之引用依 C-6 保留，**不計入**）。
  5. `test_mutation_*` 一支（於暫存副本中刪去任一 `INV || ` 片段所在之字句即轉紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`AGENTS.md`／`.cursorrules` 為執行端合約，若引用 TODO 格式須同批更新——須先 grep 確認。

### Phase 3 — 本票自身以新格式落地（依賴：Phase 2）

#### Task 3.1 — 以新格式產出本票之 TODO（`票 TODOFMT/P3`）

- **目標**：**本票自己吃自己的狗糧**——本票之 TODO 以 Phase 0 定義之五類落點產出，不產生散文 TODO 檔。
- **manifest 路徑**（r7 主委自查：原未定義）：新格式 manifest 一律置於 `docs/manifests/<EPIC>.json`；本票＝`docs/manifests/TODOFMT.json`。副檔名 `.json` 不命中 Task 1.2 步驟 2 樣式與窗口檢查之兩個樣式。
- 🔴 **時序（r2 指出原文自相矛盾：「收案後才產 manifest」與「manifest 通過才准收案」互斥）**：
  manifest 之產出與檢查**皆在收案之前**；`template_check.sh todofmt` rc=0 是**收案前置**，不是收案後動作。
  收案之後不再改 manifest，只依 invalidation 條件重產。
- **不可做**：不得回頭寫散文 TODO；不得因「本票是治理票、沒有生產模組」而免除測試檔落點。
- **邊界**：① 本票無生產模組（`stub_modules` 為空）⇒ 須明示為 `not_executable` 並附三值理由 ② 契約 JSON 落點 ③ 批次卡欄位齊備 ④ 收據落點 ⑤ 五類齊備檢查通過 ⑥ `template_check todofmt` rc=0。
- **驗證**：以本票 manifest 跑 `template_check.sh` 之 `todofmt` 子命令須 rc=0；並以 `tests/governance/test_todofmt_sample_self.py` 覆蓋 promotion artifact 存在性與 `contract_digest` invalidation（r4 指出此處曾重述邊界條數，為「數字只存一處」之漏網一處）。
- 🔴 **promotion 條件**（r1 三家要求，原 SPEC 只說「受控回饋邊」而無機制）：本票 manifest 通過 `template_check.sh todofmt` 且 Task 1.3 路由測試綠 ⇒ 該 manifest **promote 為樣本**，寫入 `tests/governance/fixtures/todofmt_sample_self.json`。
- 🔴 **invalidation 條件**：Phase 0 之契約（鍵集或值域）**任一變更** ⇒ 全部已 promote 之樣本**須重產**（舊樣本檔刪除，不保留），且 Task 0.1 之測試須斷言「樣本記錄之 `contract_digest` == loader 以現行契約計算之 `contract_digest`」，不等即 fail。因該值由契約內容衍生，**改鍵集或值域而不改版本號之情形不存在**。
- **存活至**：`lifecycle: keep`（作為新格式之第一個活樣本）。
- **覆蓋風險**：若 Phase 0 之契約在 Phase 3 發現不足，須回頭改 Phase 0 ⇒ 由上述 invalidation 條件機械處理，不靠紀律。

#### Task 3.2 — 第二樣本：FF-TFMETA manifest（**收案前置**）（`票 TODOFMT/P3`）

- 🔴 **起因**（r1 三家同判）：本票為**治理票**，`stub_modules` 只能為空、`test_files` 全是治理測試 ⇒ 五類對本票退化為二類，**Task 3.1 之 dogfooding 不足以驗收**「含生產 stub ＋ golden 路徑」之真實實作票。
- **目標**：在本票收案**之前**，為下一張真實實作票 **FF-TFMETA** 產出一份 manifest（`docs/manifests/FFTFMETA.json`）並通過 `template_check.sh todofmt`。
- 🔴 **`spec_path`＝`docs/FFDEFECT_DECISION.md`**（r7 主委自查：FF-TFMETA 之 SPEC **不存在**，而 `spec_path` 之 `exists_check` 為 true，指向不存在之 SPEC 則樣本必不過；產出其 SPEC 即為開啟該票，而使用者已裁定其餘票暫停至本票完工，且 W 於 Phase 0–3 之後建立，於本票內新建之亦使窗口檢查失敗）：
  🔴 **本樣本於 FF-TFMETA 之 SPEC 產出並更新 `spec_path` 之前，不能作為 `--spec` 派工之 manifest**（r8 codex／grok 同判）：以 `--spec docs/FFDEFECT_DECISION.md` 派工時，既有 `template_check.sh spec` 對該決策檔 rc=1 而拒發 token——此由既有 gate 機械擋下，本票不為此放寬任何錨點。本樣本之驗收只及 `template_check.sh todofmt` 與不帶 `--spec` 之 `--todo` 路由。
  FF-TFMETA 之需求現行唯一權威即該決策檔之缺陷 B 修法節。該票開工時產其 SPEC，並依本 Task 覆蓋風險更新樣本之 `spec_path`。
- **驗收之 identity 與資料流**：四情況依 `docs/FFDEFECT_DECISION.md` 缺陷 B 修法節原文「驗收須覆蓋**健康多 TF／skip／failed／單 TF** 四種情況」，每一情況對應 `test_files` 中之一個具名測試。
  🔴 **r3 更正**：主委 r2 寫成「單週期／多週期／兩值一致／兩值不一致」並宣稱逐字對齊，**為誤**。以決策檔原文為準。
  🔴 **本 SPEC 不自行陳述 FF-TFMETA 之 golden 狀態**——以決策檔為準。
- 🔴 **樣本之 `batch_card.coverage_risk` 須逐條列出決策檔缺陷 B 修法節之五條等式**，並標明各由哪一個具名測試斷言（r4 codex 指出：測試依四情況命名不等於斷言了 canonical completeness object）：
  (a) `expected = ordered(training_tfs)` (b) `present = expected − skipped/failed` (c) `failed ⊆ expected` (d) `expected = present ∪ failed` (e) complete 時 `failed = []` 且 `present == expected`。
  **測試之斷言內容屬 FF-TFMETA 之實作，不屬本票**（本 Task 不可做：不得實作 FF-TFMETA）；其正確性由 FF-TFMETA 之三家 code review 驗。本樣本只驗 manifest 已**宣告**此對應。

- **樣本之具體路徑**（r9 codex：本節只以語意描述 producer、契約與測試）：`stub_modules`／`contract_jsons`／`test_files` 之具體路徑屬 FF-TFMETA 自身之設計，本票不代為決定；Task 3.2 實作時依決策檔缺陷 B 修法節讀碼選定，並於樣本之 `batch_card.risk_mitigation` 逐條記錄「路徑 ← 決策檔段落 ← 定位所用之 grep 命令」。`test_files` 之四個測試須逐一對應決策檔之四情況，`coverage_risk` 之五條等式須逐一對應其中之具名測試。FF-TFMETA 開工時依其 SPEC 覆核並更新（見本 Task 覆蓋風險）。
  🔴 **本樣本不承諾其路徑由本 SPEC 唯一決定**（r10 codex：兩名實作者依同一決策檔可選出不同路徑）：本樣本之作用是以真實票之形狀驗證 manifest 格式與路由，不是替 FF-TFMETA 定稿；其路徑之唯一性屬 FF-TFMETA 自身 SPEC 之責任。

🔴 **本樣本之涵蓋邊界——逐欄對照契約表**（r3 指出原以票型描述代替、未窮舉 `batch_card` 各欄）。欄值：「有值」＝本樣本該欄非空且被驗；「驗空」＝本樣本驗該欄為空之情形；「不驗」＝本樣本不驗此欄非空之情形；「不涵蓋」＝列入 RESID-9a／9b。

| 契約欄位 | 本樣本之值 | 涵蓋 |
|---|---|---|
| `stub_modules` | 非空（FF completeness producer） | 有值 |
| `test_files` | 非空（決策檔四情況＋mutation） | 有值 |
| `script_acceptance` | 空 | 不驗 |
| `contract_jsons` | 空，以 `not_executable` 宣告（實作期實查：FF 無既有 completeness 契約 JSON，`momentum/FeatureEngineering` 下之 JSON 只有 `_resources/max_nan_ratio.json`） | 驗空類宣告 |
| `spec_path` | `docs/FFDEFECT_DECISION.md`（見上） | 有值 |
| `run_receipts` | 空（實作前無收據） | 不驗 |
| `batch_card.depends` | 空（單批） | 不驗 |
| `batch_card.touches` | 非空 | 有值 |
| `batch_card.callers_now` | 空 | 驗空 |
| `batch_card.callers_later` | 非空（EVENTSCAN） | 有值（且驗「不驗存在性」之例外） |
| `batch_card.relocates_to` / `relocates_at` | 空 | **不涵蓋**（跨批搬遷） |
| `batch_card.reexport` / `tests_stay` | 不適用 | **不涵蓋**（同上） |
| `batch_card.gate_cmd` | 非空 | 有值 |
| `batch_card.forbidden` | 非空，含 `observable=false` 一條（「不得在 storage 端由 primary tf 猜多週期集合」） | 有值，含不可觀測項 |
| `batch_card.risk_mitigation` / `coverage_risk` | 非空（`coverage_risk` 含「既有 18 個 run 之 metadata 不得改寫」） | 有值 |
| `batch_card.lifecycle` | `keep` | 有值 |
| `batch_card.not_executable` | 非空：`contract_jsons` 之空類宣告＋兩條 `observable=false` 之 `forbidden` 之宣告（b3 審碼 codex／grok：原「空」與同表 `contract_jsons` 列及 checker 之必查衝突） | 有值（checker 對空類與不可觀測項之宣告必查） |
| （契約外）測試之斷言內容 | 由 `coverage_risk` 宣告對應 | **不驗**（屬 FF-TFMETA 之實作與 code review） |
| （契約外）golden 重簽 | — | **不涵蓋**（阻擋項 `RM-FFNAME`） |
| （契約外）前端落點（`frontend/`） | — | **不涵蓋** |
- **不可做**：不得實作 FF-TFMETA（本票只產其 manifest）；不得為了讓 manifest 通過而放寬契約值域。
- **邊界**：① `stub_modules` 非空（FF-TFMETA 有生產模組） ② `contract_jsons` 指向既有 FF 契約；無既有契約時為空並以 `not_executable` 宣告此類（實作期實查為後者） ③ `batch_card.callers_now` 為空而 `callers_later` 非空（EVENTSCAN 為後續消費者） ④ `coverage_risk` 含「既有 18 個 run 之 metadata 不得改寫」 ⑤ `lifecycle` 值合法 ⑥ 四情況各有具名測試；所宣告之測試函式尚不存在者須標「（待 FF-TFMETA 新增）」、已存在者不得標（b3 審碼 composer：看似可執行之 node id 實不存在；以靜態比對該檔之 `def` 行驗其與現況一致）。
- **驗證**：`tests/governance/test_todofmt_sample_fftfmeta.py`：對本 Task 全部邊界各一具名測試；該 manifest 通過 `template_check.sh todofmt`（rc=0）；`test_mutation_*` 一支。
  🔴 **經 `gate.sh` 路由之斷言在本測試檔內，不在聚合器**（r7 codex／grok 同判：`gate.sh --todo` 非合法 top-level 命令，rc=1 於 kind 檢查；補成 `dispatch` 又在讀 manifest 前因未清債 rc=1，且 rc=0 之意義是已發 token 而非 manifest 合法）：
  以既有治理測試之隔離（`GATE_DIR_OVERRIDE` 指向 tmp、`GOVERNANCE_TEST_HARNESS=1`、conftest 之債務隔離；比照 `tests/governance/test_gate_impl_dispatch.py`）執行非 impl 之 `gate.sh dispatch --todo docs/manifests/FFTFMETA.json`（不帶 `--spec`，其餘必填旗標以固定值給足），斷言 rc=0 且 stdout 含 todofmt 路徑之通過句；token 只落於 tmp。
- **存活至**：`lifecycle: keep`（FF-TFMETA 開工時直接沿用）。
- **覆蓋風險**：若 FF-TFMETA 之真實需求與本樣本不符，該票開工時須先更新樣本並重跑 Task 0.1 之 `contract_digest` 比較。

#### Task 3.3 — 收案聚合入口 `scripts/todofmt_freeze_check.sh`（`票 TODOFMT/P3`）

- 🔴 **起因**（r9 codex）：聚合入口原只寫在下方收案判定表之說明中，無任何 Task 認領其交付、驗證與存活——實作者完成全部 Task 仍可能沒有收案入口。
- **目標**：實作下方收案判定表之聚合入口；其行為規則以下方「聚合入口規則」三句為準（本 Task 不重述）。
- **實作要點**：執行陣列為腳本內之字面陣列，每項為完整 argv（見下方規則 1）；判定函式以參數接受陣列，生產呼叫不傳參數即用腳本字面（與 Task 1.2 同一模式）。**不讀本 SPEC**。
- **不可做**：不得以 glob 選檔；不得把 `gate.sh` 列入陣列；不得把本 Task 自身之單元測試列入陣列。
- **邊界**：① 陣列第二項之行程未啟動（rc 非 0） ② 全部項目 rc=0（rc=0） ③ 某項有 skip（rc 非 0） ④ 某項有 xfail（rc 非 0） ⑤ 某項 rc 非 0（聚合 rc 非 0） ⑥ 生產呼叫之陣列＝腳本字面（斷言不讀任何外部清單檔或本 SPEC） ⑦ 生產陣列每一項皆為完整 argv：首元素為可執行者（`bash` 或 repo 之 venv python）、無 glob 字元（`*`／`?`／`[`）、不含 `gate.sh`（靜態讀腳本字面斷言） ⑧ 記錄時點：以一支先印出成功字樣、稍後以非 0 結束之 stub 驗證——該項之紀錄須為其最終 rc（非 0），聚合 rc 非 0（若於啟動時即記錄則會記成通過） ⑨ 執行紀錄少一項、多一項、或順序與陣列不同（各 rc 非 0）。
- **驗證**：`tests/governance/test_todofmt_freeze_check.py`：對本 Task 全部邊界各一具名測試（以參數傳入 stub 陣列）；**此測試不經聚合器執行**，故無自我參照；耗時記錄於 §V；`test_mutation_*` 一支（移除「執行紀錄與陣列之比對」即轉紅）。
- **存活至**：`lifecycle: keep`。
- **覆蓋風險**：無既有 caller（新增檔）。

🔴 **收案條件**（r2 加嚴；r3 改為可機械判定）：下表全部列之測試**皆通過**方得收案。

#### §P 收案判定表（r3 新增；聚合入口 `scripts/todofmt_freeze_check.sh`）

| Task | 測試檔（逐檔明列，禁 glob） | 預期 | 「逐字不變」類之比較（L 對 X；**無基準檔**） |
|---|---|---|---|
| 0.1 | `tests/governance/test_todofmt_contract.py` | 全 pass | — |
| 0.2 | `tests/governance/test_template_check_todofmt.py` | 全 pass | `scripts/template_check.sh` 相對 L 之差異恰為轉呼叫行一行 |
| 1.1 | `tests/governance/test_mutation_scope_extension.py` | 全 pass | 第 6 段通過句之來源字面同為 `git show <L>:scripts/gov_check.sh` 與 X 版之子字串（**不跑第 6 段**） |
| 1.2 | `tests/governance/test_todofmt_write_guard.py` | 全 pass | `git show <L>:.claude/settings.json` 之 hook 清單 ⊆ X 版清單；既有散文 TODO 內容 L 對 X 逐位元組相等（生成區塊除外） |
| 1.3 | `tests/governance/test_gate_todo_routing.py` | 全 pass | legacy 分支呼叫字面同為 L 與 X 版 `scripts/gate.sh` 之子字串 |
| 1.4 | `tests/governance/test_gate_impl_requires_manifest.py` | 全 pass | 非 impl 路徑實跑 rc=0 且無本 Task 訊息；進入條件字面見於 X 版 `scripts/gate.sh` |
| 2.1 | `tests/governance/test_todofmt_template.py` | 全 pass | — |
| 2.2 | `tests/governance/test_todofmt_constitution_sync.py` | 全 pass | L 之本 SPEC 之 `INV || ` 行對現行憲法檔；例外放行清單 `tests/governance/fixtures/constitution_exception_allowlist.txt` |
| 3.1 | `tests/governance/test_todofmt_sample_self.py` ＋ `bash scripts/template_check.sh todofmt docs/manifests/TODOFMT.json` | 全 pass ＋ rc=0 | — |
| 3.2 | `tests/governance/test_todofmt_sample_fftfmeta.py` ＋ `bash scripts/template_check.sh todofmt docs/manifests/FFTFMETA.json` | 全 pass ＋ rc=0 | — |

- 🔴 **「逐字不變」一律 L 對 X，不擷取基準檔**（r8 grok 實測：以命令輸出為基準時，輸出受債務狀態與未列入來源集合之 callee 左右，首行 blob 等於 L 而輸出已變；codex 另指出 hash 與輸出非同一 snapshot。主委據此**移除 r7 所加之首行 blob 記錄與四個基準檔**，改為直接讀 L 之內容）：
  **X＝W（已存在時），否則＝工作樹**。W 一經存在即固定，故收案後他票對同檔之合法修改不使本表之比較失敗。
  ⇒ 無「何時擷取」之問題，亦無擷取命令本身之正確性問題。
- 🔴 **本表之權威來源＝`scripts/todofmt_freeze_check.sh` 內之字面陣列，本表為其說明**（r6 三家同判：若聚合器之期望集合取自本 SPEC 之 markdown 表，即依賴散文格式，漏解析一列即假綠）。**聚合器不讀本 SPEC。**
- **聚合入口規則**（r6 grok 三句修法）：
  1. **執行清單與期望集合只准是聚合器腳本內之同一個字面陣列**；上表之兩條非 `.py` 命令（Task 3.1、3.2 之 `bash scripts/template_check.sh todofmt <manifest>`）亦寫入同一陣列。逐項執行（**禁 glob**，依既有「pytest 逐檔明列」規則）。
     🔴 **每一項為完整 argv 且預期 rc=0**（r7 codex）：pytest 項＝`<repo 之 venv python> -m pytest -q <單一測試檔>`；非 `.py` 項即上表所列之完整命令。**應被拒絕之組合一律留在各 Task 之測試檔內以 subprocess 斷言，不列為聚合器項**；`gate.sh` 不進陣列。
  2. **每一項只在其行程結束並取得 rc 之後才追加進執行紀錄**；返回前比對「執行紀錄」與「字面陣列」，**不等即 rc 非 0**（漏跑一項即不等）。
  3. **skip／xfail 一律計為未通過**；回傳聚合 rc（任一未通過即非 0）。**不設入表之自測檔。**
- **聚合器之單元測試置於本表之外**：見 Task 3.3（`tests/governance/test_todofmt_freeze_check.py`，不經聚合器執行，故無自我參照）。
- **誠實邊界**：聚合器之字面陣列與本表散文之後仍可能各寫各的。**不為對齊二者而做 markdown 解析器**（r6 grok 明言）；列 RESID-13。
- **耗時**：依 C-1 記錄於 §V，不設門檻。此入口**僅於收案判定時執行**（HEAD 為 W 或其後代；見 §P 三時點表），非每次寫檔之檢查，不受 C-5 之禁 pytest 約束（C-5 管轄寫檔當下之檢查）。
單靠 Task 3.1（自我 dogfooding）不足；單靠 3.1＋3.2 亦不足——新增之 Task 1.3／1.4 之回歸斷言亦為收案前置。

### Phase 4 — 收案後補遺（依賴：Phase 3；使用者 2026-09-23 追問「其他 TODO 相關的文件都有跟著更新了嗎」）

Task 2.1／2.2 只涵蓋 TODO 範本與 TODO 定義句；主委盤點 `templates/`、`docs/MULTI_AGENT_ORCHESTRATION.md`、`scripts/` 後，另查出五處仍預設散文 TODO，於第 4 批一併改正：

| 落點 | 原狀 | 改為 |
|---|---|---|
| `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` | V13：TODO 檔變數未定義新格式；§1 第 11 類之欄位、§2 之全域約束檢查、獵空殼皆指散文 TODO | V14：新舊格式並陳；全域約束改查 manifest `batch_card.forbidden`；獵空殼另須逐一打開空殼與具名測試 |
| `templates/TODO_GENERATION_PROMPT.md` | 舊版全域規則節（解耦、不可違反原則、不得放寬既有測試斷言）於新格式無落點 | 規定其落點為 `batch_card.forbidden`；必讀清單加「The 7 Decoupling Rules」「Non-Negotiable Principles」；階段 3 加第 6 項自檢 |
| `templates/SPEC_TEMPLATE.md` | 「對應 TODO」為散文路徑寫法 | 指向 `docs/manifests/<EPIC>.json` |
| `docs/MULTI_AGENT_ORCHESTRATION.md` | 範本說明、`--todo` 機檢、機器把關三處只描述散文 TODO | 補新格式之機檢路徑；註明 `--manifest`（coverage 清單）與 TODO manifest 同名不同物 |
| `scripts/debt_clear.sh`、`scripts/_synth_attr.py` | 收斂檔 `延後→X` 只到 `docs/<EPIC>_TODO.md` 找 X ⇒ 新格式之票有延後即拒銷 | 無散文 TODO 時改查 `docs/manifests/<EPIC>.json`（舊票行為不變）；manifest 只認 `batch_card.not_executable[].item` 之**完全相等**，不對整份 JSON 搜字（第 4 批審碼 codex／composer：描述欄、`gate_cmd` 偶含同字面會誤放）；具名測試 `tests/governance/test_debt_clear.py::test_clear_attribution_gate_defer_target_uses_epic_manifest_without_prose_todo`（含「只在描述欄出現 ⇒ 拒」之反例） |

- **不可做**：不得動 TODO 定義句（Task 2.2 之兩檔逐字相同）與任何 `INV || ` 片段所在語句；不得使 `docs/TODOFMT_SPEC.md` 之設計定案標記行再次出現；`scripts/debt_clear.sh` 之行數不得改變（`scripts/fact_keys.json` 以行號引用其第 544、891 行）。
- **驗證**：本票 11 個測試檔＋`tests/governance/test_debt_clear.py` 全數通過；收案聚合器 12 項 rc=0；三家審碼。

---

## §V 驗證策略與邊界測試目錄

| 層 | 內容 |
|---|---|
| **契約層** | Task 0.1 之契約鍵集 vs loader 回傳鍵集相等 |
| **機械閘層** | 🔴 **各 Task 之邊界以該 Task 正文為唯一權威，本表不重述條數**（r3：重述之條數於 r2 後漂移四處——0.1、1.2 條數錯、1.4／2.1／2.2／3.1 漏列；數字只存一處即不會再漂）。每 Task 之驗證段一律為「對本 Task 全部邊界各一具名測試」；收案判定見 §P 收案判定表 |
| **效能層** | 🔴 **每個新增檢查皆須寫入實測耗時**（C-1）；**不與門檻比對**，僅要求回填且不得仍為 `PENDING-MEASURE`。量法：`date +%s%N` 前後差，或 `time` 之 real 值 |
| **真陽性層** | Task 1.1 之兩段斷言：(i) 量化 26 檔 fatal 集合 == §A 具名之 12 支；(ii) 治理扣除既有三檔後 fatal 集合 == 27 支。**皆只跑靜態器** |
| **不變式層** | 一律 L 對 X（見收案判定表）：`template_check.sh` 相對 L 之差異恰為轉呼叫行；`gov_check.sh` 第 6 段通過句字面同存於 L 與 X；`gate.sh` legacy 分支字面同存於 L 與 X；`gate.sh` 之 `dispatch`／`artifact`／`register-output` 三條既有路徑行為不變（Task 1.3 覆蓋風險）；`git show <L>:.claude/settings.json` 之 hook 清單 ⊆ X 版清單；既有散文 TODO 之內容 L 對 X 逐位元組相等、生成區塊除外（Task 1.2 邊界⑱）；**審查強度四項之片段存於現行憲法檔**（Task 2.2；原文為 L 之本 SPEC 之 `INV || ` 行） |
| **樣本層** | 自我樣本（Task 3.1）＋ FF-TFMETA 樣本（Task 3.2）**皆須通過**方得收案 |
| **mutation** | 每個新增測試檔須有 `test_mutation_*`（依 `docs/TEST_DESIGN_CHARTER.md`） |

**實測耗時回填欄**（實作時以 receipt 覆寫下列 `PENDING-MEASURE`；收案前仍為該字面即 FAIL）：

- `template_check.sh todofmt`：**0.11 秒**（`time` real；以 `docs/manifests/TODOFMT.json`，2026-09-23 主委實跑）
- 產出端 hook（Task 1.2）：**0.02 秒**（`time` real；擋下之情形，2026-09-23 主委實跑）；實作期審碼補強（控制字元、字面折疊、祖先目錄比對）後複測 **0.03 秒**（放行與擋下皆同級）
- mutation 靜態擴覆蓋（Task 1.1）：**1.71 秒**（`bash scripts/mutation_scope_static.sh`，量化 26 檔＋治理層；2026-09-23 主委實跑）
- 收案聚合入口（Task 3.3）：**41.9 秒**（12 項；僅收案判定時執行一次；2026-09-23 主委實跑）
- 窗口檢查與 W 之判定（§P「生效之判定」）：**0.30 秒**（W 尚未存在時之 L..HEAD 全走一遍；2026-09-23 主委實跑；另參考 r9 codex 實跑 `.claude/settings.json` 之 29 個歷史版本逐一 `jq` 共 448 毫秒）
- 以上五項皆已自 `PENDING-MEASURE` 回填為實測值。

---

## §R 回退

- **Phase 0–1**：新增檔與新增子命令，回退＝刪除新增檔 ＋ 移除 `.claude/settings.json` 新增條目 ＋ 還原 `gate.sh` 之判型分支。🔴 **`gov_check.sh` 第 6 段全程未改，故無須還原**。無資料遷移，無既有檔改寫。
- **Phase 2**：`CLAUDE.md`／ORCH／範本之改動皆在 git 追蹤內，回退＝`git revert`。
- **Phase 3**：本票 manifest 為新增檔，刪除即回退。
- **回退後之一致狀態**：既有 `docs/*_TODO.md` 全程零改動（C-6），故回退不需處理任何既有票。

---

## §N N/A 登記與殘留

- **§G Golden / Baseline ＝ N/A**：本票 `RISK-HIT: b,c`，未命中 (a)／(d)，不改任何數值計算，無 golden 可對照。
> 🔴 **理由值一律用 Phase 0 定義之封閉 enum `RESID_REASON_ENUM`**（`blocked-by`／`user-ruling`／`needs-research`），與契約同一值域。

- **RESID-1 — 現行啟發式之 fatal 名單（12＋27 支）不修、分類器不改**：`為何現在不做: needs-research:該 39 支經 grok 實跑確認皆觸及待測系統，被標 fatal 係分類器不認 subprocess／本地 helper／monkeypatch.setenv／tests.fixtures；正確修法是改分類器之認列規則，而該規則之封閉集合尚未設計`。具名清單與 receipt 見 §A。
- **RESID-2 — 341 個量化測試檔無 mutation 探針**：`為何現在不做: user-ruling:2026-09-22 使用者定死嚴禁擴成全量掃描（C-3）；改為強制需 341 檔工作量，成本與本票差兩個數量級`。
- **RESID-3 — 既有散文 TODO 不遷移**：`為何現在不做: user-ruling:2026-08-05 面向未來不溯及既往`。
- **RESID-4 — `mutation_probe_check.sh` 之 pytest 段不擴至量化層**：`為何現在不做: user-ruling:2026-09-22 C-5`。🔴 **成立範圍須明記**：「pytest 段額外抓到 0 支」僅對**本批 26 檔**成立（該批靜態器 rc=1、fatal 12 行）；**不得**外推為「pytest 段普遍無價值」。
- **RESID-5 — 審 stub＋測試檔之每輪成本上升未量測**：`為何現在不做: needs-research:三家於 r1 consult 同判成本不相當，但無人給出量法；需於本票之新格式試辦後才有可量對象`。
- **RESID-6 — §A 前提詮釋之缺陷（有限 receipt → 全稱結論）不在本票範圍**：`為何現在不做: needs-research:本方向完全不碰 §A；2026-09-22 該問題之六個候選改法全數被實測或使用者推翻，尚無可行設計`。（理由值自 `blocked-by` 改為 `needs-research`——非被他方阻擋，而是無設計。）
- **RESID-7 — 靜態分析原理上偵測不到、而實跑會轉紅之類型**：`為何現在不做: user-ruling:2026-09-22 使用者定死不得引入分鐘級以上之檢查（C-1、C-5）`。🔴 **具名取捨**：C-5 以「只做靜態分析」換速度，代價是此類**本票不覆蓋**。
  **已觀測之兩種靜態行為（供日後可查，r2 要求補）**：
  (i) **偽陽性**——探針確實觸及系統，但觸及方式不在分類器認列清單（`subprocess`、本地 helper、`monkeypatch.setenv`、`tests.fixtures`），即 §A 之 39 支；
  (ii) **偽陰性之可能面**——探針 import 了 `momentum`／`api` 符號因而通過靜態認列，但其斷言與被 mutate 之行為無因果關係；靜態器只驗「有無觸及」不驗「因果」，此面**未經量測**。
  **可查之兩條靜態器行為**（r3 grok 要求補）：(a) 探針引用 `momentum`／`api` 被測符號時，靜態器 **rc=0**（即 (ii) 之入口） (b) `ORACLE-SELF-REF WARN` **只警告、不改 rc**。
  **靜態器之具名落點**（r4 codex 要求補）：認列清單於 `scripts/mutation_probe_static.py:26-27`、判定分支於 `:117`；**owner＝分類器另票**（RESID-1）；**expiry＝分類器另票開工時**；review 索引＝`handoffs/reconcile/20260922-todofmt-x-review-r5/synth.md` C8。
  **具名證偽方法**（r3 codex 要求補；本票依 C-5 不執行，但方法具名以供日後）：對任一被列 fatal 之探針，手動 mutate 其被測函式後執行該探針——若轉紅，即證該條為 (i) 偽陽性；對任一靜態 rc=0 之探針，mutate 其被測函式後若**不轉紅**，即證該條為 (ii) 偽陰性。
- **RESID-8 — Task 2.2 之例外條款偵測為關鍵詞啟發式**：`為何現在不做: needs-research:封閉可導出集合尚未設計；黑名單式關鍵詞可被改寫繞過`。其角色為提醒不為保證，已於 Task 2.2 步驟 1b 明記。
  **同一範圍另含步驟 1 之片段比對之盲點**（r8／r9 codex）：於片段所在行附加限縮條件而片段與其次數皆不動時不擋（重複出現之刪除已由次數比對擋下）。其封閉解法為「不變式之語意判定」，與關鍵詞啟發式同屬未設計之封閉集合。
- **RESID-9a — golden 重簽型票無樣本**：`為何現在不做: blocked-by:RM-FFNAME`（已登記於 ROADMAP 之具名票；其狀態見 ROADMAP 生成區塊）。該票含三檔共 146 MB 之 golden 重簽，為現存唯一此型之具名票。
  🔴 **觸發條件**：該票開工前須先補「golden 重簽」型樣本並通過 `template_check.sh todofmt`，否則該票不得依本格式派工。
- **RESID-9b — 跨批搬遷型與前端落點型票無樣本**：`為何現在不做: needs-research:現存 ROADMAP 無具名之此二型待開票`（r3 grok 指出原以 `blocked-by` 標之卻無現存阻擋項）。二型為：**跨批搬遷**（`relocates_to`／`relocates_at` 實際發生）、**前端消費者**（`frontend/` 落點）。首次出現此型之票時，須於其派工前補樣本。
- **RESID-10 — 保留既有 SPEC 清單內之路徑而整份改寫其內容以繞過 Task 1.4**：`為何現在不做: user-ruling:2026-09-11 使用者判準「繞過成本 ≥ 合規成本即收，歸 §N 蓄意等價」`。
  **為何不以內容 digest 擋**（r3 分歧之裁決，看碼證）：依 C-6 既有 SPEC 允許**持續合法修訂**——`docs/EVENTSCAN_SPEC.md` 即現行修訂中之實例；內容 digest 無法區分「合法續修」與「蓄意改寫」，會擋掉正常工作。蓄意改寫一份既有 SPEC 以冒充新票，其成本不低於照規寫一份 manifest。
- **RESID-11 — 經 Bash 重導寫入散文 TODO**：`為何現在不做: needs-research:Task 1.2 之 hook 掛於 Write／Edit；Bash 之重導與 tee 不在該掛載面上，本票不做命令解析`。
  （r4 曾列之「刪除生效標記 `scripts/todofmt_active.marker` 與清單以回到未收案態」一項，因 S1 移除生效標記與清單檔**已無對應機制**，自本殘留刪除。）
- **RESID-12 — 往既有清單（hook／gate 腳本內之字面陣列）加行以放行新散文 TODO 或新 SPEC**：`為何現在不做: user-ruling:2026-09-11 使用者判準「繞過成本 ≥ 合規成本即收，歸 §N 蓄意等價」`。
  **意外之路徑已由測試封閉**（r6 三家同判：r5 主委所稱「不存在意外加行」**不成立**——若陣列取自收案時之工作樹，設計定案後新建之散文 TODO 會被意外收進）：陣列改取自 L 之 git 樹，且**測試斷言陣列＝該樹之符合路徑集合**，意外收進或多加一行皆使該測試失敗；L 之身分由本 SPEC 設計定案標記行之首次出現推導，不靠手寫 sha。
  **剩餘者為蓄意**：欲放行某新檔，須**同時改掉陣列與該測試之預期集合**——其成本與照規寫一份 manifest 並列，依本判準為蓄意等價。
  🔴 **本殘留不以 code review 為防線**（r6 grok 指出「改腳本即三家 code review」不成立——現有機器只在下一次派 impl 時數前批家族數，不讀陣列 diff，實為紀律）。
  r2–r5 曾以 sha256 自保護、生效標記、三態機、環境變數注入等機械防護此項，r5 以結構性簡化全數移除，r6 以上述測試取代。
- **RESID-13 — 聚合器字面陣列與本 SPEC 收案判定表散文之漂移**：`為何現在不做: needs-research:對齊二者須解析本 SPEC 之 markdown 表，即重新引入 r6 三家所指之散文格式依賴`。聚合器之字面陣列為權威、本表為說明；**不為對齊二者而做 markdown 解析器**（r6 grok 明言）。漂移之後果＝說明過時，不影響收案判定之正確性。
- **RESID-14 — 改寫已推送之歷史（rebase／squash／force push）使 L 或 W 之推導改變**：`為何現在不做: user-ruling:2026-09-11 使用者判準「繞過成本 ≥ 合規成本即收，歸 §N 蓄意等價」`。
  本 repo 於 main 直推、不改寫已推送歷史；改寫須 force push，屬蓄意。推導結果變為零行或多行時 fail-closed；推導至另一 commit 而結果等價時不影響判定。
  **不涵蓋之理由**：L 與 W 之推導皆讀不可變之 commit 歷史；防歷史改寫須在 git 之外另建簽章或外部記錄，即新增一層機制。

TODOFMT-DESIGN-FREEZE: 20260922-todofmt-x-review-r11
