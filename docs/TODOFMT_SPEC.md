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
- **C-3 禁止擴成全量掃描**：mutation 靜態檢查維持 **opt-in**（僅選中已宣告 `def test_mutation_` 之檔）。**不得**在本票內改為「每個測試檔都必須有探針或 N/A」。
- **C-4 不得動 `pre-push`**：`pre-push` 維持 `gov_check.sh --fast`。本票**不得**新增任何項目進 `pre-push`。
- **C-5 不得引入 pytest 執行段**：本票所加之寫檔當下檢查**只准做靜態分析**（AST／grep／jq），**不得**在該路徑上執行 `pytest`。依 §A receipt：對**該批 26 檔**，靜態器 rc=1 並列出 12 支 fatal，pytest 段**額外**列出 **0** 支。🔴 此成立範圍限該批 26 檔，**不得外推**為「pytest 段普遍無價值」（見 RESID-4）。

### C-6～C-9：範圍與相容

- **C-6 不溯及既往**：設計定案 commit 之 git 樹中符合 Task 1.2 步驟 2 樣式之既有散文 TODO（樣式定義以該步驟為唯一權威，含任一層子目錄與延伸檔；r5／r6 grok 指出不得以 glob 舉例等同之）（`GAP1`／`GAP2`／`GAP3_EVENT`／`SPLITUNIFY`／`EVTLABEL`／`DOCROT2`／`REDISPATCH`／`VERDICTGATE` 等）**不遷移、不改寫**。**legacy 之界線＝設計定案 commit**（與 Task 1.2／1.4 字面陣列之來源一致）；新格式之**強制**自收案起生效。🔴 **設計定案至收案之間不得新開任何票**（使用者 2026-09-22 已裁定「TODO優化完成後再討論下一步」，其餘票暫停）；若仍有，其散文 TODO 不在字面陣列內，收案後即被擋，須轉為新格式。
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
| **收案** | §P 收案判定表之全部測試皆通過（聚合入口 rc=0） | 新格式之**強制**自此生效（hook 掛載、gate 分支加入）；legacy 之**界線**則為設計定案 commit（見 C-6） |
| **生效時點** | ＝收案 commit | 既有散文 TODO 清單與既有 SPEC 清單以**字面陣列**寫入 hook／gate 腳本，且 hook 掛載於 `.claude/settings.json`——**三者於同一個 commit 完成** |

⇒ 原文之「凍結前置」「凍結條件」「凍結判定表」語意皆為**收案**，已全數改稱。聚合入口檔名沿用 r3 收斂檔之 `scripts/todofmt_freeze_check.sh`，其語意為收案判定。
⇒ 基準檔（見收案判定表）於**設計定案之後、任何實作改動之前**擷取。

### 🔴 生效之判定——結構性簡化（r5 主委提案 S1；r6 三家攻擊後修正）

**r2–r5 之經過**：r2 為「白名單只減不增」加 sha256 自保護 → r3 發現其與刪行衝突而改四句規則 →
r3 為避開實作期誤擋而把清單延至收案才寫 → r4 發現啟用空窗而加生效標記三態機與 `TODOFMT_LIST_DIR` 注入 →
r5 三家打穿三態機之組合判定與環境變數殘留。**每一輪之修補新增一層機制，該機制於下一輪生出新邊界。**
⇒ r5 以結構性簡化 S1 取代整層；r6 三家攻擊 S1，**抓出其兩處前提錯誤**（見下），已依三家修法修正，**皆未新增機制層**。

**現行設計**：
- 🔴 **既有清單＝腳本內之字面陣列**：兩份清單（既有散文 TODO、既有 SPEC），以字面陣列寫入 `scripts/` 下之 Task 1.2 hook 腳本，與 Task 1.4 之 `gate.sh` 分支（判 `--spec`／`--todo`）。**無獨立清單檔、無 sha256 自保護、無生效標記、無三態機、無環境變數。**
  （r2–r4 曾規劃之 `scripts/legacy_prose_todo.txt`／`scripts/legacy_spec_snapshot.txt`／`scripts/todofmt_active.marker` 三檔**於 S1 下全數不建立**。）
- 🔴 **陣列之輸入＝設計定案 commit 之 git 樹，不是收案時之工作樹**（r6 三家獨立同判 S1 之前提「不存在意外加行」不成立：
  設計定案至收案之間 hook 未掛，其間新建之散文 TODO 若以收案時工作樹掃描生成，會被**意外**收進 legacy 陣列）：
  陣列內容＝`git ls-tree -r --name-only <設計定案 sha>` 之輸出，再套 Task 1.2 步驟 2 樣式（既有 SPEC 陣列比照，套 `*_SPEC*.md`）。
  **設計定案 sha 以字面寫於陣列旁**。未追蹤殘檔與設計定案後才 commit 之新檔**不會進集合**。
  `git ls-tree <固定 sha>` 為**一次性生成時**讀取不可變內容，非執行期之 git 狀態判定——hook 與 gate 執行時**只比對字面陣列**（r1 之「不得以 git 狀態判定」維持）。
- 🔴 **陣列之機械對照**（r6 grok 指出「改腳本即三家 code review」**不成立**——現有機器只在下一次派 impl 時數前批家族數，**不讀陣列之 diff**，實為「記得去看那一行」＝紀律，違反使用者 2026-09-13「不接受紀律或記憶當解法」）：
  **測試斷言「字面陣列＝設計定案樹之符合路徑集合」**。往陣列**多加一行即使該測試失敗**——防線是這條測試，**不是 code review**。
  欲蓄意繞過須同時改掉該測試之預期集合（見 RESID-12）。
- 🔴 **生效＝掛載**：hook 掛於 `.claude/settings.json` 且 `gate.sh` 分支存在，即生效。**掛載前行為同現行**（hook 不存在即不執行）。
  字面陣列寫入、hook 掛載、gate 分支三者**於同一個收案 commit 完成**，故無啟用空窗。
- **測試**：直接呼叫判定函式並**以參數傳入清單**（測試用清單可置於 `tests/governance/fixtures/`）；生產呼叫**不傳參數**即用腳本字面。兩者為同一函式之不同呼叫，無「測試讀 A、生產讀 B」之分岔。
- **設計定案 sha 之記錄時點**：commit 無法包含自身 sha ⇒ 由**實作之第一個 commit** 將設計定案 commit 之全長 sha 寫入本節與 Task 2.2 擷取句旁。

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
  - **其餘判定規則為 checker 程式碼**：值域（enum／格式）、跨欄規則（例：`forbidden[].observable=false` ⇒ 須於 `not_executable` 有對應項）、`expiry` 日期比較等。**不以資料表達，不設計規則語言。**
  - **兩者皆由 `contract_digest` 涵蓋**（見上表）⇒ 不論改在哪，樣本皆失效。
  本表之「值域」「承載」兩欄為**說明**；與契約 JSON 或 checker 程式碼不一致時，以後二者為準。
- **不可做**：不得新增第六類落點；不得讓任一欄位值為自由散文（除 `not_executable.item` 與 `risk_mitigation`／`coverage_risk` 之描述文字，該三者允許自然語言但**不承載判定**）；**不得為表達判定規則而設計規則語言或 DSL**。
- **邊界**：① 五類皆空 ② 只有 `batch_card` ③ `not_executable.reason` 非三值之一 ④ `expiry` 已過期 ⑤ **`exists_check=true` 之欄位路徑不存在（須 fail）** ⑥ `gate_cmd` 為空字串 ⑦ `contract_digest` 與 loader 計算值不等 ⑧ `spec_path` 缺漏或為空 ⑨ `run_receipts` 之 receipt 檔內容缺三鍵之一（須 fail；receipt 為資訊性，只驗形狀） ⑩ **`exists_check=false` 之欄位指向不存在路徑（須放行）** ⑪ **`callers_now` 非空（須接受並驗其路徑存在）**（r4：原樣本只驗空值情形） ⑫ **只改 checker 腳本（不動契約 JSON）而 `contract_digest` 隨之改變**（證 digest 涵蓋程式碼中之規則） ⑬ **只改契約 JSON 之 `exists_check` 值而 `contract_digest` 隨之改變**（證 digest 涵蓋資料中之規則）。
- **驗證**：`tests/governance/test_todofmt_contract.py`：**對本 Task 全部邊界各一具名測試**；契約鍵集與 loader 回傳鍵集相等；`contract_digest` 由 loader 計算之值與樣本記錄值之比較；`test_mutation_*` 探針一支（改壞值域即轉紅）。合法 manifest 之 `template_check.sh todofmt` 須 rc=0；缺 `batch_card` 之 manifest 須 rc 非 0（於測試內以 `subprocess` 斷言 rc，不在本 SPEC 內放可執行斷言行）。
- **存活至**：全票完工後保留（為新票之權威契約）。
- **覆蓋風險**：無（新增檔，無既有 caller）。

#### Task 0.2 — `template_check.sh todofmt` 子命令（`票 TODOFMT/P0`）

- **目標**：機械驗「一張票之 TODO 五類落點齊備且合法」，秒級。
- **實作要點**：檢查邏輯置於**獨立檔 `scripts/todofmt_check.sh`**，`template_check.sh todofmt` 子命令只轉呼叫之（r6：使 `contract_digest` 之 checker 部分只涵蓋此檔，`template_check.sh` 其他子命令之修改不使樣本失效）；純 `jq` ＋ 路徑存在性檢查；**禁止執行 pytest**（C-5）。
- **不可做**：不得讀取測試內容做語義判斷；不得掃全 repo。
- **邊界**：① manifest 不存在 ② JSON 不合法 ③ 缺任一類 ④ **`exists_check=true` 之欄位**路徑不存在（依契約 JSON 之 `exists_check` 判定，r4 指出原文未指向例外即會對全部路徑欄套存在性檢查而誤殺） ⑤ `not_executable` 缺 owner ⑥ `expiry` 格式非 `YYYY-MM-DD` ⑦ `exists_check=false` 之欄位指向不存在路徑（須放行）。
- **驗證**：`tests/governance/test_template_check_todofmt.py`：對本 Task 全部邊界各一具名測試；耗時以 `date +%s%N` 前後差量測並**記錄**至 §V（**不與任何門檻比對**，依 C-1）；`test_mutation_*` 一支。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`template_check.sh` 既有 `spec` 子命令行為不得改變——須有回歸測試斷言 `spec` 子命令輸出逐字不變。

### Phase 1 — 產出端 hook 與 mutation 靜態擴覆蓋（依賴：Phase 0）

#### Task 1.1 — mutation 靜態檢查擴至量化三層（`票 TODOFMT/P1`）

- **目標**：**新增一個獨立的靜態入口**，選檔範圍為 `tests/{governance,momentum,api,feature_engineering}`，**維持 opt-in**，**僅跑靜態器**。
- 🔴 **不改 `gov_check.sh` 既有第 6 段**（r1 三家同判：該段呼叫的是含 pytest 段之 `mutation_probe_check.sh`，「擴覆蓋」若改動它即同時改變既有治理行為）。新入口與既有第 6 段**並存且各自具名**。
- **實作要點**：新入口只呼叫 `scripts/mutation_probe_static.py`；不呼叫 `mutation_probe_check.sh`。
- **不可做**：不得改為強制（C-3）；不得在此路徑執行 pytest（C-5）；不得修 §A 具名之 12 支（C-7）；不得改分類器；**不得新增 `LEGACY_PROBE_DEBT` 排除項**（新增排除會使治理層之 27 支消失，改變既有態）。
- **邊界**：① 量化層零檔有探針 ② 只有 `tests/api` 有 ③ 既有第 6 段輸出逐字不變 ④ fatal 名單被正確列出 ⑤ 非 fatal 之探針不誤列 ⑥ 檔案不存在。
- **驗證**：`tests/governance/test_mutation_scope_extension.py`，**真陽性斷言分兩段、皆只跑靜態器**：
  - (i) 量化 26 檔之 fatal 名字集合**等於** §A 具名之 12 支（具名比對，不多不少）；
  - (ii) `tests/governance` 扣除既有三檔後之 fatal 集合**維持 27 支**（具名寫進測試，**不新增排除**）。
  另對本 Task 全部邊界各一具名測試；耗時以 `date +%s%N` 記錄並寫入 §V（**不與門檻比對**，依 C-1）；`test_mutation_*` 一支（改壞選檔 glob 即轉紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：🔴 新入口之 rc 會因 12＋27＝39 支而非 0。⇒ **新入口之 rc 不接進任何既有 fail-stop 鏈**，僅輸出名單供人看；其「該不該紅」之裁決屬分類器另票。既有第 6 段行為須有回歸測試斷言逐字不變。

#### Task 1.3 — `gate.sh --todo` 機械判型路由（`票 TODOFMT/P1`）

- 🔴 **起因**（r1 三家同判）：`--todo` 有值時 `gate.sh` **無條件**呼叫 legacy `template_check.sh todo`，該子命令要求 markdown 錨點（`## §0` 等）⇒ **新格式 manifest 必被擋**，C-6 之並存在命令路由上未落地。
- **目標**：`gate.sh` 依 `--todo` 之**機械判型**路由，判型規則須可機械導出、不得靠散文說明。
- **判型規則（封閉）**：副檔名**經 `casefold` 後**為 `.md` ⇒ legacy 路徑（`template_check.sh todo`）；`casefold` 後為 `.json` 且頂層含 `stub_modules` 鍵 ⇒ 新路徑（`template_check.sh todofmt`）；其餘 ⇒ fail-closed 並印兩種合法形式。
  🔴 **`casefold` 為必要**（r2 指出：本機大小寫不敏感卷上 `X_TODO.MD` 會判不出 legacy）。
- 🔴 **`--manifest` 等既有旗標不受影響**（r2 指出原文未定義）：本 Task **只改 `--todo` 之分派**，其餘旗標之路徑解析與 rc 語義逐字不變，並以回歸測試斷言。
- **不可做**：不得以內容啟發式猜測；不得讓同一輸入同時進兩條路徑；不得改動 legacy 路徑之 rc 語義。
- **邊界**：① `.md` 走 legacy 且 rc 語義不變 ② 合法 manifest 走新路徑 ③ `.json` 但缺 `stub_modules` ④ 副檔名為 `.yaml` ⑤ 檔不存在 ⑥ **同一次呼叫重複給 `--todo`**（如同時給 `--todo X.md` 與 `--todo Y.json`）⇒ fail-closed（r3 指出原「兩種皆給」未給與「不做內容嗅探」相容之具體輸入；判型只看副檔名與 JSON 頂層鍵） ⑦ 副檔名大小寫變體 `X_TODO.MD`（`casefold` 後走 legacy）。
- **驗證**：`tests/governance/test_gate_todo_routing.py`：對本 Task 全部邊界各一具名測試；legacy 路徑之輸出逐字不變之回歸斷言；`test_mutation_*` 一支（改壞判型即轉紅）。
- **存活至**：`lifecycle: keep`。
- **覆蓋風險**：`gate.sh` 為全專案共用控制流——改動須有回歸測試斷言 `dispatch`／`artifact`／`register-output` 三條既有路徑行為不變。

#### Task 1.4 — `gate.sh` 於 impl 派工強制要求 manifest（`票 TODOFMT/P1`）

- 🔴 **起因（r2 最重之單條）**：`scripts/gate.sh:1004-1006` 僅在 `--todo` **非空**時呼叫檢查；
  `:927` 對高風險派工只要求 `--spec`，**不要求** `--todo`。
  ⇒ 新票只交 `--spec`、省略 `--todo`，則 Task 1.2 之 hook 無路徑可擋、檢查條件為假，
  **整套五類落點檢查被完全繞過而 token 照發**。現成案例＝`docs/EVENTSCAN_SPEC.md`（有 SPEC、無 TODO 檔）。
- **目標**：`--spec` 有值時**強制要求** `--todo`，且其須為新格式 manifest。
- **實作要點**（插在 `scripts/gate.sh` 發 token 之前、與 Task 1.3 同一段；**`--impl-self` 走同一段**；`scripts/dispatch.sh` 以 `exec gate.sh` 單點收口，無須另做）：
  1. `--spec` 經正規化後命中 **`gate.sh` 內之既有 SPEC 字面陣列**（收案 commit 一次生成；見 §P「生效之判定」S1）⇒ 放行（C-6）。
  2. 否則 `--todo` 缺值 ⇒ **fail-closed**，訊息印出五類落點與 manifest 樣板路徑。
  3. `--todo` 有值但判型為 legacy `.md` 且 `--spec` 不在既有清單 ⇒ fail-closed。
  4. 🔴 **manifest 與 SPEC 之對應**（r3 grok 指出可拿任一合法 manifest 為新 SPEC 領 token）：manifest 之 `spec_path` 經與 Task 1.2 步驟 1 相同之正規化（剝根、剝 `./`、`casefold`）後，**必須等於**同樣正規化後之 `--spec`；不等 ⇒ fail-closed。一次 `jq` 字串比較。
  5. 🔴 **`--manifest` 不得替代 `--todo`**（r3 codex／composer 同判）：`--manifest` 維持既有 coverage 參數之語義，**不計入**本 Task 之「已提供 manifest」判定。
- **生效**：本 Task 之 `gate.sh` 分支於收案 commit 加入即生效；**加入前行為同現行**（見 §P「生效之判定」S1）。無生效標記、無三態判定。
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
- **邊界**：① 新 SPEC ＋ 無 `--todo`（擋） ② 新 SPEC ＋ manifest 且 `spec_path` 相等（放行） ③ 既有 SPEC ＋ 無 `--todo`（放行） ④ 既有 SPEC ＋ 散文 TODO（放行） ⑤ 新 SPEC ＋ 散文 TODO（擋） ⑥ `--spec` 之大小寫變體或 `./` 前綴命中既有 SPEC 字面陣列（放行，須正規化後判定） ⑦ 新 SPEC ＋ manifest 但 `spec_path` 不等（擋） ⑧ 新 SPEC ＋ 只給 `--manifest` 未給 `--todo`（擋） ⑨ `--impl-self` ＋ 新 SPEC ＋ 無 `--todo`（擋） ⑩ **`--impl-self` ＋ 無 `--spec`**（擋） ⑪ 生產呼叫所用之既有 SPEC 陣列＝`gate.sh` 腳本字面（斷言不讀任何外部清單檔） ⑫ **既有 SPEC 字面陣列＝設計定案樹之 `docs/` 下全部 `*_SPEC*.md`**（不等即 fail）。
- **驗證**：`tests/governance/test_gate_impl_requires_manifest.py`：對本 Task 全部邊界各一具名測試；
  `dispatch` 之非 impl 路徑（無 `--spec` **且**無 `--impl-self`）行為逐字不變之回歸斷言；`test_mutation_*` 一支。
- **存活至**：`lifecycle: keep`。
- **覆蓋風險**：`gate.sh` 為全專案共用控制流；本 Task 與 Task 1.3 同檔改動，須合併為單一 diff 並同批回歸。

#### Task 1.2 — 產出端 hook：新票寫散文 TODO 即擋（`票 TODOFMT/P1`）

- **目標**：`PreToolUse` hook，於 Write／Edit 建立**新的**散文 TODO（`docs/` 下任一層、檔名符合下述樣式者，含延伸檔）時 fail-closed，並印出五類落點指引。
- 🔴 **判定不得依賴 git 狀態**（r1 三家各自獨立打穿 `git ls-files` 版：已 `git add` 之佔位檔會被當成既有檔；hook 收到之**絕對路徑**與 `./` 前綴皆不在 `git ls-files` 輸出中）。
- **生效**：本 hook 掛載於 `.claude/settings.json` 即生效；**掛載前不存在即不執行**（見 §P「生效之判定」S1）。無生效標記、無三態判定。
- **實作要點**（**順序即判定順序**，不得調換）：
  1. **字串層正規化**：剝 repo root 前綴、剝 `./`，得 repo 相對路徑；整串 `casefold`（本機為大小寫不敏感卷；例：`Docs/X_Todo.md` 正規化後即 `docs/x_todo.md`，不得繞過）。
  2. 🔴 **先比樣式、後解 symlink**（r3 指出先 `realpath` 會使指向白名單之 symlink 改變判定）：
     路徑首段為 `docs`（**任一層子目錄皆算**，例：`docs/sub/X_TODO.md`）且**檔名**符合 `^[a-z0-9_]+_todo(\.[a-z0-9-]+)?\.md$`
     （涵蓋 `X_TODO.md` 與延伸檔 `X_TODO.D-001.md`，比對前已 casefold；r3 指出原樣式放行 `docs/NEWEPIC_TODO.D-001.md`）
     ⇒ 進入白名單比對；否則放行（非本 hook 管轄）。
  3. **既有清單比對**：以步驟 1 之字串比對 hook 腳本內之字面陣列；另以 `realpath` 解析後之路徑**再比一次**，兩者任一命中即視為命中（涵蓋 symlink／硬連結指向既有清單內檔案之情形）。
  4. 命中既有清單 ⇒ 放行（C-6）；未命中 ⇒ fail-closed 並印五類落點指引。
- 🔴 **既有清單（字面陣列）之內容**（r4 grok 實查：若以 `docs/*_TODO.md` glob 定義，現存 69 個命中樣式之檔中有 **12 個**——延伸檔 7（`docs/GAP3_EVENT_TODO.D-001.md`、`docs/GAP3_EVENT_UX_TODO.D-001.md` 至 `D-006.md`）、`docs/Archived/` 下 5 個——不在該 glob 內，生效後其合法編輯會被誤擋）：
  **內容＝設計定案 commit 之 git 樹中，符合本 Task 步驟 2 樣式之全部路徑**（`git ls-tree -r --name-only <設計定案 sha>` 再套樣式；含延伸檔與任一層子目錄），正規化並排序後寫為 hook 腳本內之字面陣列。**不以 `docs/*_TODO.md` glob 當全集；不取收案時之工作樹**（r6 三家同判：設計定案至收案之間新建之散文 TODO 會被意外收進）。
  新延伸檔因不在該陣列內仍被擋（r3 之原反例不會回來）。Task 1.4 `gate.sh` 內之既有 SPEC 字面陣列比照：設計定案 commit 之 git 樹中 `docs/` 下全部 `*_SPEC*.md`。
- 🔴 **陣列之機械對照**（r2–r4 之 sha256 自保護四句與首次寫入例外**全數移除**；r6 grok 指出「改腳本即三家 code review」實為紀律，**已刪除該等同**）：
  **測試斷言「hook 腳本之字面陣列＝設計定案樹之符合路徑集合」**（見 §P「生效之判定」）——往陣列多加一行即使該測試失敗。欲蓄意繞過須同時改掉該測試之預期集合，列 RESID-12 蓄意等價。
- **不可做**：不得擋既有清單內檔案之編輯；不得掃全 repo；不得執行 pytest；**不得以 git 狀態（`ls-files`／`status`／`diff`）作為判定依據**；**不得另建獨立清單檔**。
- **邊界**：① 新建 `docs/X_TODO.md`（擋） ② 編輯既有清單內之 `docs/GAP2_MARGINAL_IC_TODO.md`（放行） ③ 新建 `docs/X_TODO.yaml`（放行） ④ 路徑含空白 ⑤ 傳入**絕對路徑**或 `./docs/X_TODO.md`（須正規化後正確判定） ⑥ 已 `git add` 但未 commit 之新散文 TODO（**須擋**） ⑦ symlink 指向既有清單內檔案（放行） ⑧ **大小寫變體** `Docs/X_Todo.md`（須擋） ⑨ **子目錄** `docs/sub/X_TODO.md`（須擋） ⑩ 硬連結指向既有清單內檔案（放行） ⑪ **延伸檔** `docs/NEWEPIC_TODO.D-001.md`（須擋） ⑫ 編輯**既有延伸檔** `docs/GAP3_EVENT_TODO.D-001.md`（放行，因在字面陣列內） ⑬ 編輯 `docs/Archived/` 下既有之 `*_TODO.md`（放行） ⑭ **生產呼叫（不傳清單參數）使用之陣列＝腳本字面**，與測試傳入之陣列為同一函式之不同呼叫（斷言生產路徑不讀任何外部檔） ⑮ **字面陣列＝設計定案樹之符合路徑集合**（不等即 fail；往陣列多加一行、或設計定案後才建立之散文 TODO 被收進陣列，皆使本測試失敗） ⑯ 設計定案後新建之 `docs/LATE_TODO.md`（不在陣列內，生效後須擋）。
- **驗證**：`tests/governance/test_todofmt_write_guard.py`：對本 Task 全部邊界各一具名測試；hook 掛載點與 `.claude/settings.json` **機械對證**（比照既有 `factkey_write_guard` 之對證作法）；耗時以 `date +%s%N` 記錄寫入 §V（依 C-1 不比門檻）；`test_mutation_*` 一支。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`.claude/settings.json` 為共用掛載點，新增條目不得影響既有 hook 之觸發順序——須有回歸測試斷言既有 hook 清單為新清單之子集。

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
- **邊界**：① 只改 `CLAUDE.md` 未改 ORCH（產生第二權威） ② 改動誤及「不得跳步」之審查強度語義 ③ 家數字面被寫入 `CLAUDE.md` ④ 既有 `--spec/--todo` 旗標說明失效 ⑤ 觸發句表失同步 ⑥ 交叉引用殘留 ⑦ **fixture 之引入 commit 同時修改任一憲法檔**（`git diff-tree` 之檔名清單含憲法檔即 fail） ⑧ **fixture 之引入 commit 之父樹中憲法檔 blob 不等於設計定案 commit 之 blob**（即 fail；防擷取已弱化之文本）。
- **驗證**：`tests/governance/test_todofmt_constitution_sync.py`：
  1. 🔴 **審查強度四項不變式之逐字快照比對**（r1 三家同判：只比對 TODO 定義一致性，抓不到「兩份文件一起被改弱」；r2 加入第四項；r3 指出原標題仍寫「三段」且無 exact literal）。
     **四項之逐字字面只存於一處**：`tests/governance/fixtures/constitution_invariants.txt`——**實作開始時**由主委自現行檔擷取寫入，本 SPEC **不複寫其字面**。
     🔴 **fixture 之擷取 commit 只得含 fixture 檔**（r4 codex 指出從現行樹自取之風險；r5 codex 指出「同一 commit 既建 fixture 又改憲法」仍可擷取已弱化之字面；r5 主委提案 S5）：
     擷取 commit **不得**同時修改 `CLAUDE.md`／`docs/MULTI_AGENT_ORCHESTRATION.md`／`AGENTS.md`／`.cursorrules` 任一檔。
     🔴 **機械驗證之兩句**（r6 三家同判：無版本引數之 `git diff --name-only` 看的是工作樹不是擷取 commit；原未定義由誰、何時驗）：
     (a) 本 Task 之編號測試以 `git diff-tree --no-commit-id --name-only -r <引入 fixture 之 commit>` 取該 commit 之檔名清單，**只得含 fixture 檔**（`constitution_invariants.txt`、`constitution_exception_allowlist.txt`）；**禁用**無版本引數之 `git diff --name-only`。
     (b) 該 commit 之**父樹**中四份憲法檔之 blob sha，**必須等於設計定案 commit 中同檔之 blob sha**（`git rev-parse <commit>^:<path>` 對 `git rev-parse <設計定案 sha>:<path>`）。設計定案 sha 依 §P「生效之判定」之記錄時點寫入。
     ⇒ fixture 擷取之文本即**設計定案時**之文本；本票其後之憲法改動（本 Task 2.2 本身）**受該 fixture 約束**。
     fixture 檔頭另記擷取來源之檔路徑與擷取當下之 sha256，作為輔助稽核（非主要防線）。四項為：
     (i) 對抗式審查之要求 (ii) 實作者不自審之要求 (iii) 家數與家族指向 ORCH §1 現行分工行 (iv) 「不得跳步」。
     **比對標的四份檔**：`CLAUDE.md`／`docs/MULTI_AGENT_ORCHESTRATION.md`／`AGENTS.md`／`.cursorrules`；測試斷言 fixture 內每一項在其**所屬**之檔中逐字存在（fixture 每行標明所屬檔），任一缺失即 fail。
  1b. 🔴 **例外條款偵測**（r2 指出：字面逐字保留但可在他處新增例外抵銷）：對上列四份檔之**新增行**掃描，凡新增行同時命中「審查／對抗／自審／家數」任一關鍵詞**且**命中「例外／不適用／可略／免」任一者 ⇒ fail。
     🔴 **放行方式改為已提交之清單檔**（r3 指出原「人工裁決後具名放行」不可機械判定）：`tests/governance/fixtures/constitution_exception_allowlist.txt`，每行為被放行行之 sha256；測試**只對清單外之命中** fail。grok r3 實測歷史 1343 行僅 6 行命中 ⇒ 該 6 行於實作開始時列入清單。
     **誠實邊界**：此為關鍵詞啟發式，非封閉集合，可被改寫繞過；其角色是提醒不是保證，已具名為 RESID-8。
  2. `CLAUDE.md` 與 ORCH 之 TODO 定義字面一致性機械斷言。
  3. `grep -c` 確認家數數字未被寫入 `CLAUDE.md`。
  4. 全 repo 殘留掃描：`templates/` ＋ `scripts/` 內佔位符字面 `docs/X_TODO.md` 之命中數應為 0（r3 指出原「舊散文 TODO 路徑樣式」未定義；既有 `docs/<EPIC>_TODO.md` 之引用依 C-6 保留，**不計入**）。
  5. `test_mutation_*` 一支（改壞快照比對即轉紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`AGENTS.md`／`.cursorrules` 為執行端合約，若引用 TODO 格式須同批更新——須先 grep 確認。

### Phase 3 — 本票自身以新格式落地（依賴：Phase 2）

#### Task 3.1 — 以新格式產出本票之 TODO（`票 TODOFMT/P3`）

- **目標**：**本票自己吃自己的狗糧**——本票之 TODO 以 Phase 0 定義之五類落點產出，不產生散文 TODO 檔。
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
- **目標**：在本票收案**之前**，為下一張真實實作票 **FF-TFMETA** 產出一份 manifest 並通過 `template_check.sh todofmt`。
- **驗收之 identity 與資料流**：四情況依 `docs/FFDEFECT_DECISION.md` 缺陷 B 修法節原文「驗收須覆蓋**健康多 TF／skip／failed／單 TF** 四種情況」，每一情況對應 `test_files` 中之一個具名測試。
  🔴 **r3 更正**：主委 r2 寫成「單週期／多週期／兩值一致／兩值不一致」並宣稱逐字對齊，**為誤**。以決策檔原文為準。
  🔴 **本 SPEC 不自行陳述 FF-TFMETA 之 golden 狀態**——以決策檔為準。
- 🔴 **樣本之 `batch_card.coverage_risk` 須逐條列出決策檔缺陷 B 修法節之五條等式**，並標明各由哪一個具名測試斷言（r4 codex 指出：測試依四情況命名不等於斷言了 canonical completeness object）：
  (a) `expected = ordered(training_tfs)` (b) `present = expected − skipped/failed` (c) `failed ⊆ expected` (d) `expected = present ∪ failed` (e) complete 時 `failed = []` 且 `present == expected`。
  **測試之斷言內容屬 FF-TFMETA 之實作，不屬本票**（本 Task 不可做：不得實作 FF-TFMETA）；其正確性由 FF-TFMETA 之三家 code review 驗。本樣本只驗 manifest 已**宣告**此對應。

🔴 **本樣本之涵蓋邊界——逐欄對照契約表**（r3 指出原以票型描述代替、未窮舉 `batch_card` 各欄）。欄值：「有值」＝本樣本該欄非空且被驗；「驗空」＝本樣本驗該欄為空之情形；「不驗」＝本樣本不驗此欄非空之情形；「不涵蓋」＝列入 RESID-9a／9b。

| 契約欄位 | 本樣本之值 | 涵蓋 |
|---|---|---|
| `stub_modules` | 非空（FF completeness producer） | 有值 |
| `test_files` | 非空（決策檔四情況＋mutation） | 有值 |
| `script_acceptance` | 空 | 不驗 |
| `contract_jsons` | 指向既有 FF 契約 | 有值 |
| `spec_path` | FF-TFMETA 之 SPEC 路徑 | 有值 |
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
| `batch_card.not_executable` | 空 | 不驗 |
| （契約外）測試之斷言內容 | 由 `coverage_risk` 宣告對應 | **不驗**（屬 FF-TFMETA 之實作與 code review） |
| （契約外）golden 重簽 | — | **不涵蓋**（阻擋項 `RM-FFNAME`） |
| （契約外）前端落點（`frontend/`） | — | **不涵蓋** |
- **不可做**：不得實作 FF-TFMETA（本票只產其 manifest）；不得為了讓 manifest 通過而放寬契約值域。
- **邊界**：① `stub_modules` 非空（FF-TFMETA 有生產模組） ② `contract_jsons` 指向既有 FF 契約 ③ `batch_card.callers_now` 為空而 `callers_later` 非空（EVENTSCAN 為後續消費者） ④ `coverage_risk` 含「既有 18 個 run 之 metadata 不得改寫」 ⑤ `lifecycle` 值合法 ⑥ 四情況各有具名測試。
- **驗證**：`tests/governance/test_todofmt_sample_fftfmeta.py`：對本 Task 全部邊界各一具名測試；該 manifest 通過 `template_check.sh todofmt`（rc=0）；`test_mutation_*` 一支。
- **存活至**：`lifecycle: keep`（FF-TFMETA 開工時直接沿用）。
- **覆蓋風險**：若 FF-TFMETA 之真實需求與本樣本不符，該票開工時須先更新樣本並重跑 Task 0.1 之 `contract_digest` 比較。

🔴 **收案條件**（r2 加嚴；r3 改為可機械判定）：下表全部列之測試**皆通過**方得收案。

#### §P 收案判定表（r3 新增；聚合入口 `scripts/todofmt_freeze_check.sh`）

| Task | 測試檔（逐檔明列，禁 glob） | 預期 | 基準檔（「逐字不變」類之比較對象） |
|---|---|---|---|
| 0.1 | `tests/governance/test_todofmt_contract.py` | 全 pass | — |
| 0.2 | `tests/governance/test_template_check_todofmt.py` | 全 pass | `tests/governance/fixtures/template_check_spec_baseline.txt`（`template_check.sh spec` 對既有 SPEC 之 stdout） |
| 1.1 | `tests/governance/test_mutation_scope_extension.py` | 全 pass | `tests/governance/fixtures/gov_check_seg6_baseline.txt`（第 6 段通過句之**來源模板字面**，**不為取基準而跑第 6 段**） |
| 1.2 | `tests/governance/test_todofmt_write_guard.py` | 全 pass | `tests/governance/fixtures/settings_hooks_baseline.json`（既有 hook 清單） |
| 1.3 | `tests/governance/test_gate_todo_routing.py` | 全 pass | `tests/governance/fixtures/gate_legacy_todo_baseline.txt` |
| 1.4 | `tests/governance/test_gate_impl_requires_manifest.py` | 全 pass | `tests/governance/fixtures/gate_nonimpl_baseline.txt` |
| 2.1 | `tests/governance/test_todofmt_template.py` | 全 pass | — |
| 2.2 | `tests/governance/test_todofmt_constitution_sync.py` | 全 pass | `tests/governance/fixtures/constitution_invariants.txt`、`constitution_exception_allowlist.txt` |
| 3.1 | `tests/governance/test_todofmt_sample_self.py` ＋ 以本票 manifest 跑 `template_check.sh todofmt` | 全 pass ＋ rc=0 | — |
| 3.2 | `tests/governance/test_todofmt_sample_fftfmeta.py` ＋ 以 FF-TFMETA manifest 經 `gate.sh --todo` 新路由 | 全 pass ＋ rc=0 | — |

- **基準檔之取得時點**：**實作開始時**（任何改動之前）以對應命令之 stdout 寫入；基準檔一經寫入，其後只准以「使用者或委員共識決」更新。
- 🔴 **本表之權威來源＝`scripts/todofmt_freeze_check.sh` 內之字面陣列，本表為其說明**（r6 三家同判：若聚合器之期望集合取自本 SPEC 之 markdown 表，即依賴散文格式，漏解析一列即假綠）。**聚合器不讀本 SPEC。**
- **聚合入口規則**（r6 grok 三句修法）：
  1. **執行清單與期望集合只准是聚合器腳本內之同一個字面陣列**；上表之兩條非 `.py` 命令（Task 3.1、3.2 之 `template_check.sh todofmt`／`gate.sh --todo`）亦寫入同一陣列。逐項執行（**禁 glob**，依既有「pytest 逐檔明列」規則）。
  2. **每一項只在其行程結束並取得 rc 之後才追加進執行紀錄**；返回前比對「執行紀錄」與「字面陣列」，**不等即 rc 非 0**（漏跑一項即不等）。
  3. **skip／xfail 一律計為未通過**；回傳聚合 rc（任一未通過即非 0）。**不設入表之自測檔。**
- **聚合器之單元測試置於本表之外**：`tests/governance/test_todofmt_freeze_check.py` 餵入兩支 stub、令第二支不啟動，斷言聚合器 rc 非 0；兩支皆正常，斷言 rc=0。**此測試不經聚合器執行**，故無自我參照。
- **誠實邊界**：聚合器之字面陣列與本表散文之後仍可能各寫各的。**不為對齊二者而做 markdown 解析器**（r6 grok 明言）；列 RESID-13。
- **耗時**：依 C-1 記錄於 §V，不設門檻。此入口**僅於收案前執行一次**，非每次寫檔之檢查，不受 C-5 之禁 pytest 約束（C-5 管轄寫檔當下之檢查）。
單靠 Task 3.1（自我 dogfooding）不足；單靠 3.1＋3.2 亦不足——新增之 Task 1.3／1.4 之回歸斷言亦為收案前置。

---

## §V 驗證策略與邊界測試目錄

| 層 | 內容 |
|---|---|
| **契約層** | Task 0.1 之契約鍵集 vs loader 回傳鍵集相等 |
| **機械閘層** | 🔴 **各 Task 之邊界以該 Task 正文為唯一權威，本表不重述條數**（r3：重述之條數於 r2 後漂移四處——0.1、1.2 條數錯、1.4／2.1／2.2／3.1 漏列；數字只存一處即不會再漂）。每 Task 之驗證段一律為「對本 Task 全部邊界各一具名測試」；收案判定見 §P 收案判定表 |
| **效能層** | 🔴 **每個新增檢查皆須寫入實測耗時**（C-1）；**不與門檻比對**，僅要求回填且不得仍為 `PENDING-MEASURE`。量法：`date +%s%N` 前後差，或 `time` 之 real 值 |
| **真陽性層** | Task 1.1 之兩段斷言：(i) 量化 26 檔 fatal 集合 == §A 具名之 12 支；(ii) 治理扣除既有三檔後 fatal 集合 == 27 支。**皆只跑靜態器** |
| **不變式層** | `template_check.sh spec` 子命令輸出逐字不變；`gov_check.sh` 第 6 段輸出逐字不變；`gate.sh` 之 `dispatch`／`artifact`／`register-output` 三條既有路徑行為不變；`.claude/settings.json` 既有 hook 清單為新清單之子集；既有散文 TODO 零改動；**審查強度四項字面快照逐字存在**（Task 2.2；字面只存於 fixture 檔） |
| **樣本層** | 自我樣本（Task 3.1）＋ FF-TFMETA 樣本（Task 3.2）**皆須通過**方得收案 |
| **mutation** | 每個新增測試檔須有 `test_mutation_*`（依 `docs/TEST_DESIGN_CHARTER.md`） |

**實測耗時回填欄**（實作時以 receipt 覆寫下列 `PENDING-MEASURE`；收案前仍為該字面即 FAIL）：

- `template_check.sh todofmt`：`PENDING-MEASURE`
- 產出端 hook（Task 1.2）：`PENDING-MEASURE`
- mutation 靜態擴覆蓋（Task 1.1）：`PENDING-MEASURE`（參考基準：26 檔實測 0 秒）

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
- **RESID-9a — golden 重簽型票無樣本**：`為何現在不做: blocked-by:RM-FFNAME`（已登記於 ROADMAP 之具名票；其狀態見 ROADMAP 生成區塊）。該票含三檔共 146 MB 之 golden 重簽，為現存唯一此型之具名票。
  🔴 **觸發條件**：該票開工前須先補「golden 重簽」型樣本並通過 `template_check.sh todofmt`，否則該票不得依本格式派工。
- **RESID-9b — 跨批搬遷型與前端落點型票無樣本**：`為何現在不做: needs-research:現存 ROADMAP 無具名之此二型待開票`（r3 grok 指出原以 `blocked-by` 標之卻無現存阻擋項）。二型為：**跨批搬遷**（`relocates_to`／`relocates_at` 實際發生）、**前端消費者**（`frontend/` 落點）。首次出現此型之票時，須於其派工前補樣本。
- **RESID-10 — 保留既有 SPEC 清單內之路徑而整份改寫其內容以繞過 Task 1.4**：`為何現在不做: user-ruling:2026-09-11 使用者判準「繞過成本 ≥ 合規成本即收，歸 §N 蓄意等價」`。
  **為何不以內容 digest 擋**（r3 分歧之裁決，看碼證）：依 C-6 既有 SPEC 允許**持續合法修訂**——`docs/EVENTSCAN_SPEC.md` 即現行修訂中之實例；內容 digest 無法區分「合法續修」與「蓄意改寫」，會擋掉正常工作。蓄意改寫一份既有 SPEC 以冒充新票，其成本不低於照規寫一份 manifest。
- **RESID-11 — 經 Bash 重導寫入散文 TODO**：`為何現在不做: needs-research:Task 1.2 之 hook 掛於 Write／Edit；Bash 之重導與 tee 不在該掛載面上，本票不做命令解析`。
  （r4 曾列之「刪除生效標記 `scripts/todofmt_active.marker` 與清單以回到未收案態」一項，因 S1 移除生效標記與清單檔**已無對應機制**，自本殘留刪除。）
- **RESID-12 — 往既有清單（hook／gate 腳本內之字面陣列）加行以放行新散文 TODO 或新 SPEC**：`為何現在不做: user-ruling:2026-09-11 使用者判準「繞過成本 ≥ 合規成本即收，歸 §N 蓄意等價」`。
  **意外之路徑已由測試封閉**（r6 三家同判：r5 主委所稱「不存在意外加行」**不成立**——若陣列取自收案時之工作樹，設計定案後新建之散文 TODO 會被意外收進）：陣列改取自設計定案 commit 之 git 樹，且**測試斷言陣列＝該樹之符合路徑集合**，意外收進或多加一行皆使該測試失敗。
  **剩餘者為蓄意**：欲放行某新檔，須**同時改掉陣列與該測試之預期集合**——其成本與照規寫一份 manifest 並列，依本判準為蓄意等價。
  🔴 **本殘留不以 code review 為防線**（r6 grok 指出「改腳本即三家 code review」不成立——現有機器只在下一次派 impl 時數前批家族數，不讀陣列 diff，實為紀律）。
  r2–r5 曾以 sha256 自保護、生效標記、三態機、環境變數注入等機械防護此項，r5 以結構性簡化全數移除，r6 以上述測試取代。
- **RESID-13 — 聚合器字面陣列與本 SPEC 收案判定表散文之漂移**：`為何現在不做: needs-research:對齊二者須解析本 SPEC 之 markdown 表，即重新引入 r6 三家所指之散文格式依賴`。聚合器之字面陣列為權威、本表為說明；**不為對齊二者而做 markdown 解析器**（r6 grok 明言）。漂移之後果＝說明過時，不影響收案判定之正確性。
