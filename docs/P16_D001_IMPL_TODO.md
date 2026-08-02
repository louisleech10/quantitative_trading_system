# P16 D-001 實作 TODO — 票 `GOV-STAMP-TASKID-INJECT`

**SPEC（唯一權威）**：`docs/P16_COMMITTEE_DEBT_SPEC.D-001.md`（三家 APPROVED，
body sha256 `6eda520250473f4b0d00875589e89ab73f7ad83f5a41876401234092387c76c0`，
`reconcile_stamps_check.sh` rc=0）。
**本 TODO 不重述 SPEC 條文**；凡本檔與 D-001 衝突，**一律以 D-001 為準**。

**TODO 對抗審**：codex＋composer，5 findings → 4 群，**全部採納 0 不採納**；
收斂 `handoffs/reconcile/20260802-p16-d001-todo-r1-recon/synth.md`，completeness rc=0。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### 允許改動的檔案（**超出即 `STATUS: BLOCKED`，不得自行擴大**）

| 檔案 | 允許的改動 |
|---|---|
| `scripts/cx_run.sh` | Task 1.1、Task 1.3、Task 1.4 |
| `scripts/committee_run.sh` | Task 1.2 |
| `tests/governance/test_stamp_taskid_inject.py` | 新增（Task 1.5） |

**禁止改動**：`scripts/gate.sh`、`scripts/verify_task_provenance.py`、`scripts/audit_append.sh`、
`scripts/audit_events.json`、`scripts/governance_*.json`、任何 `docs/`、任何既有測試檔。

### 紀律

- **禁 `git checkout` / `git restore` 任何 tracked 檔**
- **rc 一律直接取，禁經 pipe**（`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc）
- 測試一律 `GOVERNANCE_TEST_HARNESS=1` ＋ `GATE_DIR_OVERRIDE` / `DEBT_AUDIT_OVERRIDE` 隔離；
  **禁止寫入真實 `.claude/gate/audit.log`**；**禁止變異 repo 內 `scripts/*.sh`**（探針用隔離副本）
- 任何 bug／疑問**兩輪解不了 → 停下回報，交委員會**，不得 solo 硬幹
- 暫存放 `.claude/tmp/`；收尾清 /tmp workdir（**保留 `/private/tmp/claude-501` 與 `/tmp/agent_dc_snapshot.txt`**）

### 兩條反取巧紅線

1. **`grep` 原始碼不算通過**：Task 1.5 的 V1 禁止以 static grep on `cx_run.sh` 充當綠燈
   （codex 具名：source-only 綠燈不是真 oracle）
2. **閹割守衛後仍綠 ＝ 該條非真 oracle**，須重寫，不得留著充數

## §B 批次執行策略

單批次完成 Task 1.1–1.5，理由：五個 Task 改的是同一條控制流（`cx_run.sh` 的前置→prompt→CLI→result），
拆批會讓中間態出現「注入了 task_id 但沒有對應驗收」的半成品。

**批內順序（有依賴，不可調換）**：

| 序 | Task | 依賴 |
|---|---|---|
| 1 | Task 1.2（`committee_run.sh` 前置驗證） | 無 |
| 2 | Task 1.1（`task_id` 導出與注入） | 無 |
| 3 | Task 1.3（`cx_run` defense-in-depth） | Task 1.2 的判準 |
| 4 | Task 1.4（自動 `register-output`） | Task 1.1 的 task_id |
| 5 | Task 1.5（測試 V1–V15） | 全部 |

交件前必須全批綠，**不得分次交件**。

## Phase 1 — cx_run／committee_run 增訂（依賴：D-001 生效）

### Task 1.1 — `cx_run.sh`：從 audit 導出 `task_id` 並注入 prompt

- 目標：消除「委員手抄 task-id」這條路徑。　檔案：`scripts/cx_run.sh`
- 改法：
  ① 取值來源＝`_assert_round_preconditions` 內已讀入的**同一筆** `open_ev` 的 `task_id` 欄；
     **不得另開第二次 audit 掃描**（TOCTOU）；**不得從 env 讀 `TASK_ID`**
  ② 以該函式 stdout 回傳 task_id；錯誤訊息一律走 stderr，**不得混入 stdout**
     〔codex／composer 隔離探針實跑確認：正確捕獲時 stdout 僅單一 task_id；
     缺值時 rc=1、stdout 0 bytes、訊息全在 stderr〕
  ③ `open_ev` 缺 `task_id` 或值為空字串 → **拒派 rc≠0、audit 零新增**（第⑦道前置）
  ④ 🔴 **prompt 的組建時機**〔`CODEX-R1-P1-01`＋`COMPOSER-R1-P1-01`，兩家獨立同型〕：
     本 TODO 初版寫「prompt（`cx_run.sh:337`）追加一句」**不可實作**——`:337` 組 prompt，
     但 `_assert_round_preconditions` 要到 `:414/418/422` 才呼叫；照字面做會在 `set -u` 下
     讀未定義變數、或送出無 task-id 的 prompt、或誘使實作者從 env 偷讀（違 §D2 紅線）。
     ⇒ **prompt 必須在「前置成功並捕獲 stdout」之後、`_run_cli_and_emit` 使用它之前組建**
     （延後組建或以參數傳入皆可）。**D-001 §D2 的「落點 `:337`」是字串錨點，非執行順序約束**
     （兩家一致認定，故 D-001 無須修改）
  ⑤ prompt 追加的句子，**逐字**：
     `你的 task-id=<注入值>。RECONCILE-STAMP 的 task: 欄位須逐字使用此值；brief 內任何 task-id 範例一律不得採用。`
- **驗證（可證偽）**：`pytest tests/governance/test_stamp_taskid_inject.py -q -k "v1 or v2 or v3"` 全綠；
  V1＝spy 捕獲的 prompt 字串**含** `你的 task-id=<open_ev.task_id>` 逐字（字串相等比對，非子字串猜測）；
  V2／V3＝`open_ev` 缺 `task_id`／值為 `""` 時 `cx_run` rc≠0 **且**隔離 audit 行數 delta ==0
- **邊界（≥2）**：①`open_ev` 缺欄 → 拒派且 audit 零新增 ②`task_id` 為空字串 → 同上
  ③既有不帶 stamp 的派工路徑行為逐位元組不變（V12）
- **存活至**：永久保留（本改法是 `cx_run` 前置的第⑦道）
- **覆蓋風險**：無後續 Phase 會刪改本 Task 產出
- **不可做**：不得從 env 讀 `TASK_ID`；不得第二次掃 audit；不得把錯誤訊息寫進 stdout

### Task 1.2 — `committee_run.sh`：`stamp-target` 驗證（**在 `gate.sh dispatch` 之前**）

- 目標：讓 brief schema 錯誤在**發 token 之前**就擋下。　檔案：`scripts/committee_run.sh`
- 改法：
  ① 🔴 **位置＝`committee_run.sh:91-92` 那一段**（與 `[ -f "${brief}" ]`、`out前綴須在 handoffs/` 同處），
     **必須在 `:213` 的 `gate.sh dispatch` 之前**。放在 gate 之後會使「audit 零新增」不可能成立
     ——`gate.sh:240` 在 dispatch 成功路徑即 append `committee_dispatch`
  ② 僅當 brief 的 `brief-kind` 為 `stamp` 時檢查；其餘 kind 不解析、不強制
  ③ 行首錨定 `^stamp-target:`，取全部宣告去重；**多個不一致 → `exit 2`**；缺欄 → `exit 2`
  ④ 值須 `handoffs/` 前綴、不得含 `..`、檔案須存在；任一不成立 → `exit 2`
  ⑤ 所有失敗路徑：**不發 token、不開債、不派工、audit 逐位元組零新增**
- **驗證（可證偽）**：`pytest tests/governance/test_stamp_taskid_inject.py -q -k "v4 or v5 or v6"` 全綠；
  三態各自 `committee_run.sh` rc==2、隔離 audit 行數 delta ==0、
  `.claude/gate/dispatch.token` 的 mtime 不變（未發 token）、`debt_ledger --has-open` rc==0（無殘留 OPEN 債）
- **邊界（≥2）**：①缺欄 → 零新增 ②兩個不一致宣告 → 零新增
  ③`handoffs/` 外／含 `..`／檔不存在 三態**分別**驗，不得合併為一條
- **存活至**：永久保留
- **覆蓋風險**：無後續 Phase 會刪改；與既有 brief 檢查同段（`:91-92`），未來新增 brief 欄位會在同處擴充
- **不可做**：不得把該檢查放在 `gate.sh dispatch`（`:213`）之後；不得對非 `stamp` 的 brief-kind 強制此欄

### Task 1.3 — `cx_run.sh`：同一組驗證作為 defense-in-depth

- 目標：涵蓋直呼 `cx_run`（不經 `committee_run`）的路徑。　檔案：`scripts/cx_run.sh`
- 改法：與 Task 1.2 同判準，置於既有 `brief-kind` 解析之後。
  注意此處失敗若經 `committee_run` 呼叫則已在開債之後，但 Task 1.2 已在開債前擋掉正常路徑，
  故本 Task 只服務直呼場景。
- **驗證（可證偽）**：`pytest tests/governance/test_stamp_taskid_inject.py -q -k "v6_direct"` 全綠；
  直呼 `bash scripts/cx_run.sh <fam> <缺欄brief> <out>` → rc==2 且 CLI 未啟動
  （spy 呼叫次數 ==0）、隔離 audit 行數 delta ==0
- **邊界（≥2）**：①直呼且缺欄 → rc=2 且未啟動 CLI ②直呼且路徑非法 → rc=2
- **存活至**：永久保留
- **覆蓋風險**：無；與 Task 1.2 判準重複是**刻意的** defense-in-depth，不得為「去重」而刪除任一側
- **不可做**：不得把 Task 1.2 的檢查刪掉改成只留本 Task（那會讓正常路徑退回開債後才擋）

### Task 1.4 — `cx_run.sh`：`brief-kind=stamp` 自動 `register-output`

- 目標：消除戳記輪後的人工 `register-output`。　檔案：`scripts/cx_run.sh`
- 改法：執行點在 `_run_cli_and_emit` 內、`_emit_family_result` 之後。
  **三條件同時成立才呼叫** `bash scripts/gate.sh register-output <task_id> <stamp-target>`：
  ① `result_state=success`（`cli_rc=0` 且產出非空）
  ② `stamp-target` 檔含**單一一行**同時滿足：`<fam>`／`APPROVED`／`YYYY-MM-DD`／
     `task:<注入的 task_id>`／`sha256:<該檔當下 body_hash>`
  ③ 家族名取 `${fam}`（`$1` 直取），不得從路徑推導

  🔴 **predicate 必須是單一 `grep -E` 對同一行的一次匹配**；
  **明文禁止**兩個以上獨立 `grep` 取交集（跨行組合會誤判為 true）。

  🔴 **`reconcile_body_hash.sh` rc≠0 的處理**〔`COMPOSER-R1-P1-02`，實跑確認〕：
  該腳本對**無 `## 戳記` 區段**的檔 **exit 1**（stderr `ERROR: 缺『## 戳記』區段標題`），
  而 Task 1.2 只驗檔存在，故 stamp-target 可能是任何檔。
  ⇒ **rc≠0 一律視為條件②不成立 ⇒ 合法 no-op**（不註冊、不改 `cx_run` rc、印訊息）；
  **不得**以空字串當 hash 繼續比對；**不得**讓其 stderr 逸出成為 `cx_run` 的錯誤輸出。

  **兩種不註冊的情形必須機械可分**：
  - **合法 no-op**（條件不成立）：靜默不註冊，rc 不變
  - **註冊失敗**（條件成立但 `register-output` rc≠0）：印**可辨識錯誤字串**、
    不回捲 `committee_family_result`、rc 不變、具名為待人工補記
- **驗證（可證偽）**：`pytest tests/governance/test_stamp_taskid_inject.py -q -k "v7 or v8 or v9 or v10 or v11 or v13 or v14 or v15"` 全綠；
  V7＝隔離 audit 中 `committee_output` 筆數 delta ==1 且該筆 `output_path` 字串等於 stamp-target、
  `output_sha256` 長度 ==64 且 != `"pending"`；
  V8／V9／V10／V11／V14／V15＝`committee_output` 筆數 delta ==0；
  V13＝`committee_output` delta ==0 **且** `cx_run` stderr 含可辨識錯誤字串 **且** `committee_family_result.result_state=="success"`
- **邊界（≥2）**：①CLI rc≠0 但目標已有相符戳記 → 零註冊 ②目標檔無 `## 戳記` → 合法 no-op
  ③目標檔含跨行組合（A 家族 APPROVED ＋ B 家族 task）→ 零註冊
- **存活至**：永久保留
- **覆蓋風險**：無；本 Task **不做** `committee_output` 去重（屬線 C），後續線 C 若改 audit 佈局須回看本 Task
- **不可做**：不得改 `gate.sh register-output` 本體；不得回捲 `committee_family_result`；
  不得以兩次 grep 取交集；不得在 `register-output` 失敗時改變 `cx_run` 的 rc

### Task 1.5 — 測試 `tests/governance/test_stamp_taskid_inject.py`

- 目標：讓 V1–V15 每條都是能證偽的 oracle。　檔案：新增 `tests/governance/test_stamp_taskid_inject.py`
- 改法：逐條實作 D-001 §D5 的 **V1–V15**（該表為權威，本檔不重抄）。
  **每條須通過 mutation：閹割對應守衛 → 該條轉紅；復原 → 轉綠，逐條附 receipt。**

  🔴 **V1 特別規定**〔`CODEX-R1-P1-02`〕：`CX_STUB_MODE=success` 的 stub 只寫
  `stub-ok family=…`，**完全跳過使用 prompt 的三個 CLI 分支** ⇒ prompt 內容無從觀測，
  V1 依 TODO 初版寫法**不可能是真 oracle**。
  ⇒ V1 須以 **harness-only 的 prompt capture（CLI spy）** 斷言**實際送出的 prompt 字串**含
  `你的 task-id=<open_ev.task_id>` 逐字；spy 機制須綁 `GOVERNANCE_TEST_HARNESS=1`。
  **禁止**以 static grep on `cx_run.sh` 充當通過。

  🔴 **V7／V13 的 harness 前置**〔`COMPOSER-R1-P2-01`〕：`gate.sh:173` 的 `_task_has_dispatch`
  要求 audit 已有**同 task 的 `committee_dispatch`**，否則 `register-output` exit 1；
  既有 `_b3_harness` 的 `gate_pass.sh` stub **不寫該事件**。
  - **V7（成功註冊）**：須先種入 `committee_dispatch`（真 `gate.sh dispatch` 或隔離 `audit_append`）
  - **V13（註冊失敗）**：**刻意不種**——正是用它製造 `register-output` rc≠0，
    驗證「註冊失敗」與「合法 no-op」在輸出上機械可分
- **驗證（可證偽）**：`pytest tests/governance/test_stamp_taskid_inject.py -q` 全綠且 V1–V15
  各有對應測試函式；每條附閹割→紅、復原→綠的 receipt
- **邊界（≥2）**：①隔離 audit，不得污染真實 `.claude/gate/audit.log`
  ②不得變異 repo 內 `scripts/*.sh`（審查已確認可在 tmp 隔離副本補拷既有 helper）
- **存活至**：永久保留（常駐回歸）
- **覆蓋風險**：無；V11／V14 被 D-001 指定為常駐 mutation oracle，後續不得刪
- **不可做**：不得以 static grep 充當 V1；不得留下閹割後仍綠的測試；不得跳過任一條 V

## §T 覆蓋追溯（只列 ID 對應，不列內容）

| D-001 條文 | 實作 Task | 驗收 |
|---|---|---|
| §D2 改法⑧ | Task 1.1 | V1、V2、V3 |
| §D3 驗證位置（`gate` 之前） | Task 1.2 | V4、V5、V6 |
| §D3 defense-in-depth | Task 1.3 | V6 直呼變體 |
| §D3 註冊條件①②③＋predicate 契約 | Task 1.4 | V7–V11、V13、V14、V15 |
| §D5 全表 | Task 1.5 | V1–V15 逐條 mutation |
| §D6 #16 兩類機械可分 | Task 1.4 | V13 |
| §D3 遷移條款／§D6 #17 | 不需程式改動（文件已載明） | V12 不誤擋回歸 |

## 驗收命令（**逐條實跑，rc 直接取，禁經 pipe**）

```
pytest tests/governance/test_stamp_taskid_inject.py -q
pytest tests/governance -q
bash scripts/gov_check.sh
bash scripts/restore_golden_inventory.sh
```

- 新測試檔：全綠，V1–V15 逐條有對應測試函式
- `pytest tests/governance -q`：**≥ 447 passed**（現況 447），**零 fail**
- `gov_check.sh`：rc=0
- 跑完測試**必須**執行 `restore_golden_inventory.sh`（否則 golden inventory 會髒）

## §Handoff

交件時於本節下方回填，並在產出檔寫 `STATUS: DONE` 或 `STATUS: BLOCKED`。

## RESULT（實作端填寫）

- STATIC_CHECK=
- RUNTIME_CHECK=
- MUTATION_CHECK=
- RECEIPTS=
- OPEN_PENDING=
