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
- **C-5 不得引入 pytest 執行段**：本票所加之寫檔當下檢查**只准做靜態分析**（AST／grep／jq），**不得**在該路徑上執行 `pytest`。依 §A receipt：靜態段 0 秒抓到 12／12 空心探針，pytest 段額外抓到 **0** 支。

### C-6～C-9：範圍與相容

- **C-6 不溯及既往**：既有 `docs/*_TODO.md`（`GAP1`／`GAP2`／`GAP3_EVENT`／`SPLITUNIFY`／`EVTLABEL`／`DOCROT2`／`REDISPATCH`／`VERDICTGATE` 等）**不遷移、不改寫**。新格式**只對本 SPEC 凍結後新開之票**生效。
- **C-7 不修空心探針**：§A 具名之 12 支空心探針，本票**只讓它們被檢查看見**，**不修**。修理另開票。
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
| `scripts/gov_check.sh:500` | mutation 掃描範圍寫死 `tests/governance/test_*.py` | 擴至量化三層（**僅靜態段**，見 C-5） |
| `.claude/settings.json` | hook 掛載點 | 新增產出端 hook 掛載 |

---

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

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
  | `run_receipts` | 路徑陣列 | 真實命令、輸入 identity、rc、誠實邊界 |
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
- **不可做**：不得新增第六類落點；不得讓任一欄位值為自由散文（除 `not_executable.item` 與 `risk_mitigation`／`coverage_risk` 之描述文字，該三者允許自然語言但**不承載判定**）。
- **邊界**：① 五類皆空 ② 只有 `batch_card` ③ `not_executable.reason` 非三值之一 ④ `expiry` 已過期 ⑤ 路徑指向不存在之檔 ⑥ `gate_cmd` 為空字串。
- **驗證**：`tests/governance/test_todofmt_contract.py`：對 ①–⑥ 各一具名測試；契約鍵集與 loader 回傳鍵集相等；`test_mutation_*` 探針一支（改壞值域即轉紅）。合法 manifest 之 `template_check.sh todofmt` 須 rc=0；缺 `batch_card` 之 manifest 須 rc 非 0（六條邊界各對應一測試，於測試內以 `subprocess` 斷言 rc，不在本 SPEC 內放可執行斷言行）。
- **存活至**：全票完工後保留（為新票之權威契約）。
- **覆蓋風險**：無（新增檔，無既有 caller）。

#### Task 0.2 — `template_check.sh todofmt` 子命令（`票 TODOFMT/P0`）

- **目標**：機械驗「一張票之 TODO 五類落點齊備且合法」，秒級。
- **實作要點**：純 `jq` ＋ 路徑存在性檢查；**禁止執行 pytest**（C-5）。
- **不可做**：不得讀取測試內容做語義判斷；不得掃全 repo。
- **邊界**：① manifest 不存在 ② JSON 不合法 ③ 缺任一類 ④ 路徑不存在 ⑤ `not_executable` 缺 owner ⑥ `expiry` 格式非 `YYYY-MM-DD`。
- **驗證**：`tests/governance/test_template_check_todofmt.py`：六條邊界各一測試；耗時以 `date` 前後差量測並斷言 ≤ 2 秒（實測值回填 §V）；`test_mutation_*` 一支。
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
  另對 ①–⑥ 各一測試；耗時以 `date +%s%N` 記錄並寫入 §V（**不與門檻比對**，依 C-1）；`test_mutation_*` 一支（改壞選檔 glob 即轉紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：🔴 新入口之 rc 會因 12＋27＝39 支而非 0。⇒ **新入口之 rc 不接進任何既有 fail-stop 鏈**，僅輸出名單供人看；其「該不該紅」之裁決屬分類器另票。既有第 6 段行為須有回歸測試斷言逐字不變。

#### Task 1.3 — `gate.sh --todo` 機械判型路由（`票 TODOFMT/P1`）

- 🔴 **起因**（r1 三家同判）：`--todo` 有值時 `gate.sh` **無條件**呼叫 legacy `template_check.sh todo`，該子命令要求 markdown 錨點（`## §0` 等）⇒ **新格式 manifest 必被擋**，C-6 之並存在命令路由上未落地。
- **目標**：`gate.sh` 依 `--todo` 之**機械判型**路由，判型規則須可機械導出、不得靠散文說明。
- **判型規則（封閉）**：副檔名 `.md` ⇒ legacy 路徑（`template_check.sh todo`）；副檔名 `.json` 且頂層含 `stub_modules` 鍵 ⇒ 新路徑（`template_check.sh todofmt`）；其餘 ⇒ fail-closed 並印兩種合法形式。
- **不可做**：不得以內容啟發式猜測；不得讓同一輸入同時進兩條路徑；不得改動 legacy 路徑之 rc 語義。
- **邊界**：① `.md` 走 legacy 且 rc 語義不變 ② 合法 manifest 走新路徑 ③ `.json` 但缺 `stub_modules` ④ 副檔名為 `.yaml` ⑤ 檔不存在 ⑥ 兩種皆給（應 fail-closed）。
- **驗證**：`tests/governance/test_gate_todo_routing.py`：對 ①–⑥ 各一測試；legacy 路徑之輸出逐字不變之回歸斷言；`test_mutation_*` 一支（改壞判型即轉紅）。
- **存活至**：`lifecycle: keep`。
- **覆蓋風險**：`gate.sh` 為全專案共用控制流——改動須有回歸測試斷言 `dispatch`／`artifact`／`register-output` 三條既有路徑行為不變。

#### Task 1.2 — 產出端 hook：新票寫散文 TODO 即擋（`票 TODOFMT/P1`）

- **目標**：`PreToolUse` hook，於 Write／Edit 建立**新的** `docs/<EPIC>_TODO.md` 時 fail-closed，並印出五類落點指引。
- 🔴 **判定不得依賴 git 狀態**（r1 三家各自獨立打穿 `git ls-files` 版：已 `git add` 之佔位檔會被當成既有檔；hook 收到之**絕對路徑**與 `./` 前綴皆不在 `git ls-files` 輸出中）。
- **實作要點**：
  1. **路徑正規化**：先轉為 repo 相對路徑（剝 repo root 前綴、剝 `./`、`realpath` 解 symlink），再比對。
  2. **判定來源＝凍結時寫入之既有散文 TODO 白名單快照**（`scripts/legacy_prose_todo.txt`，內容為本 SPEC 凍結當下 `docs/*_TODO.md` 之清單）。該快照**只減不增**：檔案被刪可從清單移除，**不得新增**。
  3. 命中白名單 ⇒ 放行（C-6）；未命中且形如 `docs/<EPIC>_TODO.md` ⇒ fail-closed 並印五類落點指引。
- **不可做**：不得擋白名單內檔案之編輯；不得掃全 repo；不得執行 pytest；**不得以 git 狀態（`ls-files`／`status`／`diff`）作為判定依據**。
- **邊界**：① 新建 `docs/X_TODO.md` ② 編輯白名單內之 `docs/GAP2_MARGINAL_IC_TODO.md` ③ 新建 `docs/X_TODO.yaml`（放行） ④ 路徑含空白 ⑤ 傳入**絕對路徑**或 `./docs/X_TODO.md`（須正規化後正確判定） ⑥ 白名單檔不存在或不可讀（fail-closed 擋） ⑦ 已 `git add` 但未 commit 之新散文 TODO（**須擋**） ⑧ symlink 指向白名單內檔案。
- **驗證**：`tests/governance/test_todofmt_write_guard.py`：對 ①–⑧ 各一具名測試；hook 掛載點與 `.claude/settings.json` **機械對證**（比照既有 `factkey_write_guard` 之對證作法）；耗時以 `date +%s%N` 記錄寫入 §V（依 C-1 不比門檻）；`test_mutation_*` 一支。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`.claude/settings.json` 為共用掛載點，新增條目不得影響既有 hook 之觸發順序——須有回歸測試斷言既有 hook 清單為新清單之子集。

### Phase 2 — 範本與憲法同步（依賴：Phase 1）

#### Task 2.1 — 改寫 `templates/TODO_GENERATION_PROMPT.md`（`票 TODOFMT/P2`）

- **目標**：自「生成一份 markdown 散文 TODO」改為「生成五類落點」。
- **不可做**：不得保留 `docs/X_TODO.md` 之字面（否則執行端仍會照舊生成）；不得同時保留新舊兩套格式說明。
- **邊界**：① 範本內仍殘留 `docs/X_TODO.md` ② 仍含 markdown Task 區塊 ③ 缺五類任一之說明 ④ 缺 `not_executable` 三值說明 ⑤ 新舊並存 ⑥ 佔位符未替換。
- **驗證**：`tests/governance/test_todofmt_template.py`：對 ①–⑥ 各一機械斷言（`grep -c` 式）；`test_mutation_*` 一支。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`scripts/new_brief.sh` 若引用本範本之章節標題，改標題會斷——須先 grep 確認引用點並同批更新。

#### Task 2.2 — `CLAUDE.md` 與 ORCH 同步（`票 TODOFMT/P2`）

- **目標**：`CLAUDE.md:30,38` 與 `docs/MULTI_AGENT_ORCHESTRATION.md` 中型列，將「TODO」之定義改為五類落點。
- **不可做**：🔴 **不得放寬審查強度**——對抗式審查、實作者不自審、家數（ORCH §1）三項逐字不動；不得取消 SPEC 對抗審（C-9）；`CLAUDE.md` 不得自寫家數。
- **邊界**：① 只改 `CLAUDE.md` 未改 ORCH（產生第二權威） ② 改動誤及「不得跳步」之審查強度語義 ③ 家數字面被寫入 `CLAUDE.md` ④ 既有 `--spec/--todo` 旗標說明失效 ⑤ 觸發句表失同步 ⑥ 交叉引用殘留。
- **驗證**：`tests/governance/test_todofmt_constitution_sync.py`：
  1. 🔴 **審查強度三項不變式之逐字快照比對**（r1 三家同判：只比對 TODO 定義一致性，抓不到「兩份文件一起被改弱」）。凍結時將下列三段字面寫入快照檔 `tests/governance/fixtures/constitution_invariants.txt`，測試斷言其在 `CLAUDE.md` 與 ORCH 中**逐字存在**；任一被改即 fail：
     - 對抗式審查之要求字面
     - 實作者不自審之要求字面
     - 家數與家族指向 ORCH §1 現行分工行之字面
  2. `CLAUDE.md` 與 ORCH 之 TODO 定義字面一致性機械斷言。
  3. `grep -c` 確認家數數字未被寫入 `CLAUDE.md`。
  4. 全 repo 殘留掃描：`templates/` ＋ `scripts/` 內指向舊散文 TODO 路徑樣式之命中數應為 0。
  5. `test_mutation_*` 一支（改壞快照比對即轉紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`AGENTS.md`／`.cursorrules` 為執行端合約，若引用 TODO 格式須同批更新——須先 grep 確認。

### Phase 3 — 本票自身以新格式落地（依賴：Phase 2）

#### Task 3.1 — 以新格式產出本票之 TODO（`票 TODOFMT/P3`）

- **目標**：**本票自己吃自己的狗糧**——本 SPEC 凍結後，其 TODO 以 Phase 0 定義之五類落點產出，不產生散文 TODO 檔。
- **不可做**：不得回頭寫散文 TODO；不得因「本票是治理票、沒有生產模組」而免除測試檔落點。
- **邊界**：① 本票無生產模組（`stub_modules` 為空）⇒ 須明示為 `not_executable` 並附三值理由 ② 契約 JSON 落點 ③ 批次卡欄位齊備 ④ 收據落點 ⑤ 五類齊備檢查通過 ⑥ `template_check todofmt` rc=0。
- **驗證**：以本票 manifest 跑 `template_check.sh` 之 `todofmt` 子命令須 rc=0；並以 Phase 0 之六條邊界測試覆蓋。
- 🔴 **promotion 條件**（r1 三家要求，原 SPEC 只說「受控回饋邊」而無機制）：本票 manifest 通過 `template_check.sh todofmt` 且 Task 1.3 路由測試綠 ⇒ 該 manifest **凍結為樣本**，寫入 `tests/governance/fixtures/todofmt_sample_self.json`。
- 🔴 **invalidation 條件**：Phase 0 之契約（鍵集或值域）**任一變更** ⇒ 全部已凍結樣本**須重產**（舊樣本檔刪除，不保留），且 Task 0.1 之測試須斷言「樣本 schema 版本 == 契約 schema 版本」，版本不等即 fail。
- **存活至**：`lifecycle: keep`（作為新格式之第一個活樣本）。
- **覆蓋風險**：若 Phase 0 之契約在 Phase 3 發現不足，須回頭改 Phase 0 ⇒ 由上述 invalidation 條件機械處理，不靠紀律。

#### Task 3.2 — 第二樣本：FF-TFMETA manifest（**凍結前置**）（`票 TODOFMT/P3`）

- 🔴 **起因**（r1 三家同判）：本票為**治理票**，`stub_modules` 只能為空、`test_files` 全是治理測試 ⇒ 五類對本票退化為二類，**Task 3.1 之 dogfooding 不足以驗收**「含生產 stub ＋ golden 路徑」之真實實作票。
- **目標**：在本 SPEC 凍結**之前**，為下一張真實實作票 **FF-TFMETA** 產出一份 manifest 並通過 `template_check.sh todofmt`。
- **驗收之 identity 與資料流**：須能承載 FF-TFMETA 之四情況（單週期 run／多週期 run／`feature_manifest.json` 與 `task_record.json` 兩值一致／兩值不一致），每一情況對應 `test_files` 中之一個具名測試。
- **不可做**：不得實作 FF-TFMETA（本票只產其 manifest）；不得為了讓 manifest 通過而放寬契約值域。
- **邊界**：① `stub_modules` 非空（FF-TFMETA 有生產模組） ② `contract_jsons` 指向既有 FF 契約 ③ `batch_card.callers_now` 為空而 `callers_later` 非空（EVENTSCAN 為後續消費者） ④ `coverage_risk` 含「既有 18 個 run 之 metadata 不得改寫」 ⑤ `lifecycle` 值合法 ⑥ 四情況各有具名測試。
- **驗證**：`tests/governance/test_todofmt_sample_fftfmeta.py`：對 ①–⑥ 各一測試；該 manifest 通過 `template_check.sh todofmt`（rc=0）；`test_mutation_*` 一支。
- **存活至**：`lifecycle: keep`（FF-TFMETA 開工時直接沿用）。
- **覆蓋風險**：若 FF-TFMETA 之真實需求與本樣本不符，該票開工時須先更新樣本並重跑 Task 0.1 之 schema 版本斷言。

🔴 **凍結條件**：Task 3.1 與 **Task 3.2 皆通過**方得凍結本 SPEC。單靠 3.1（自我 dogfooding）**不足**。

---

## §V 驗證策略與邊界測試目錄

| 層 | 內容 |
|---|---|
| **契約層** | Task 0.1 之契約鍵集 vs loader 回傳鍵集相等 |
| **機械閘層** | Task 0.2／1.1／1.2 各自之六條邊界 |
| **效能層** | 🔴 **每個新增檢查皆須寫入實測耗時**（C-1）；**不與門檻比對**，僅要求回填且不得仍為 `PENDING-MEASURE`。量法：`date +%s%N` 前後差，或 `time` 之 real 值 |
| **真陽性層** | Task 1.1 之兩段斷言：(i) 量化 26 檔 fatal 集合 == §A 具名之 12 支；(ii) 治理扣除既有三檔後 fatal 集合 == 27 支。**皆只跑靜態器** |
| **不變式層** | `template_check.sh spec` 子命令輸出逐字不變；`gov_check.sh` 第 6 段輸出逐字不變；`gate.sh` 之 `dispatch`／`artifact`／`register-output` 三條既有路徑行為不變；`.claude/settings.json` 既有 hook 清單為新清單之子集；既有散文 TODO 零改動；**審查強度三項字面快照逐字存在**（Task 2.2） |
| **樣本層** | 自我樣本（Task 3.1）＋ FF-TFMETA 樣本（Task 3.2）**皆須通過**方得凍結 |
| **mutation** | 每個新增測試檔須有 `test_mutation_*`（依 `docs/TEST_DESIGN_CHARTER.md`） |

**實測耗時回填欄**（實作時以 receipt 覆寫下列 `PENDING-MEASURE`；凍結前仍為該字面即 FAIL）：

- `template_check.sh todofmt`：`PENDING-MEASURE`
- 產出端 hook（Task 1.2）：`PENDING-MEASURE`
- mutation 靜態擴覆蓋（Task 1.1）：`PENDING-MEASURE`（參考基準：26 檔實測 0 秒）

---

## §R 回退

- **Phase 0–1**：新增檔與新增子命令，回退＝刪除新增檔 ＋ 還原 `gov_check.sh:500` 之 glob ＋ 移除 `.claude/settings.json` 新增條目。無資料遷移，無既有檔改寫。
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
- **RESID-7 — 靜態 AST 原理上偵測不到、而實跑會轉紅之假綠類型**：`為何現在不做: user-ruling:2026-09-22 使用者定死不得引入分鐘級以上之檢查（C-1、C-5）`。🔴 **具名取捨**：C-5 以「只做靜態分析」換取速度，其代價是此類假綠**本票不覆蓋**；三家於 r1 同判此取捨存在，本節具名之以免日後被當成已解決。
