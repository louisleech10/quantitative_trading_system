# P1-6 委員未結案債狀態機 — SPEC 延伸 D-001

BASE: docs/P16_COMMITTEE_DEBT_SPEC.md @ 416f196212cdcde5acb99b536741a834f6d7a3cb
PREDECESSOR: none
改什麼: Task 1.3 增訂 `cx_run.sh` 兩項行為——⑧ `task_id` 由 audit 導出並注入 prompt；⑨ `brief-kind=stamp` 於戳記落地後自動 `register-output`
為什麼: 票 `GOV-STAMP-TASKID-INJECT`（`handoffs/20260801-GOV-AMEND-BACKLOG.md` B-7）；事故見 §D1

**類別判定＝D 延伸**（依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` §1）。
理由：不推翻 v2.9 任一既有條文；Task 1.3 既有改法①–⑦與六道前置**逐條保持不變**，本延伸只增列⑧⑨。
**與 v2.9「範圍凍結」（SPEC:82）的關係**：範圍凍結禁止的是「往後輪次在**本版內**新增機制」。
D 延伸依定義不進入 v2.9 本體，屬獨立版本化延伸，故不牴觸。**任一委員可推翻此判定；爭議一律預設 R。**

## 觸及面宣告

新增: none
覆寫: `### Phase 1 — 留痕（依賴：Phase 0）`
依賴: `## §A 假設與待使用者確認`, `## §V 驗證策略與邊界測試目錄`, `### Phase 3 — 擋門與回歸（依賴：Phase 2）`

**檔案級觸及面**（非 heading，另列以免讀者誤判）：`scripts/cx_run.sh`（Task 1.3）
＋ `scripts/committee_run.sh`（Task 1.2，因 `CODEX-R1-P1-03` 的修法上移而納入）
＋ 新增 `tests/governance/test_stamp_taskid_inject.py`。
**兩個 Task 同屬 `### Phase 1 — 留痕（依賴：Phase 0）`，故覆寫面未擴大。**

**審查紀錄**

| 輪 | 家族 | 結果 |
|---|---|---|
| **R1 對抗審** | codex＋composer（現行 reviewers；grok 為現行 implementer，由 `governance_roles.json` 角色閘拒絕，**非遺漏**） | 9 findings → 6 群集，**全部採納、0 條不採納**。兩家在**類別 D 成立**與**否決 env 注入**兩題獨立一致 |
| **R2 戳記輪** | codex／composer／grok（`brief-kind=stamp` 不受 implementer 限制） | composer ✅ grok ✅ **codex ❌ REJECTED** — 具名 γ 的驗證位置使 V4–V6「audit 零新增」不可成立。主委獨立實跑複驗**成立**，已修（見 §D3 精確位置段）；三枚戳記依約清除 |
| **R3 戳記輪** | 三家重簽 | 進行中；codex 須重跑自身反例確認真關閉（章程 §B8） |

收斂檔 `handoffs/reconcile/20260802-p16-d001-r1-recon/synth.md`，`completeness_check --lock` rc=0。

## 內容

### §D1 事故事實（**已發生，非推測**）

| # | 事故 | 觀測 |
|---|---|---|
| A1 | R4 戳記輪：兩家委員把 brief 中的**格式範例字串**當成自己的 task-id 寫進戳記 | `verify_task_provenance.py check-stamp` rc≠0 → 補正花兩輪 |
| A2 | R5／R7 戳記輪：三家戳記全數 provenance pending | 須逐家人工 `gate.sh register-output <task> <reconcile檔>` 補記 |

**根因（兩者同源）**：`cx_run.sh:337` 的固定 prompt **不含 task-id**，委員唯一取得管道是 brief 散文；
而戳記落地後的 `committee_output` 事件**無任何自動路徑**產生。
⇒ 兩者皆屬 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` §0「漏記、抄錯」類，**在受理範圍內**。

### §D2 Task 1.3 改法⑧ — `task_id` 注入（取代手抄）

- **來源＝`committee_round_open.task_id`**（v2.9 Task 1.2 改法⑥已列為必記欄位）。
  **不新增 env 通道**：明文否決 B-7 原提案的「`committee_run.sh` 以 `TASK_ID` env 傳給 `cx_run.sh`」。
  理由：audit 事件已是 SSOT；env 會製造第二真相源，且直呼 `cx_run` 時 env 可由呼叫端任填，與改法③
  「前置一律對 audit 驗證」的紅線相衝。**此為對 backlog 原提案的修正，須委員裁決。**
- **取值時機**：`_assert_round_preconditions` 內（該函式已讀入同一筆 `open_ev`），
  以其 stdout 回傳 `task_id`，**不得另開第二次 audit 掃描**（避免 TOCTOU 讀到不同事件）。
- **落點**：`cx_run.sh:337` 固定 prompt 追加一句，逐字為：
  `你的 task-id=<注入值>。RECONCILE-STAMP 的 task: 欄位須逐字使用此值；brief 內任何 task-id 範例一律不得採用。`
- **fail-closed（第⑦道前置）**：`open_ev` 缺 `task_id` 欄或其值為空字串 → **拒派，rc≠0，audit 零新增**。
  語意與既有六道一致（不 fallback、不 degrade）。

### §D3 Task 1.3 改法⑨ — `brief-kind=stamp` 自動 `register-output`

- **brief 新增必填欄 `stamp-target:`**，值為戳記標的檔路徑。
  解析方式**沿用 `brief-kind:` 既有配方**（`cx_run.sh:45-49`）：行首錨定 `^stamp-target:`、
  取全部宣告去重、**多個不一致宣告 → fail-closed rc=2**。
  `brief-kind=stamp` 而缺此欄 → 拒派 rc=2。**其餘 brief-kind 不強制、不解析**（不誤擋）。
🔴 **驗證位置＝`committee_run.sh`，且必須在開債之前**〔`CODEX-R1-P1-03`〕：
`committee_run.sh:211-223` 先寫 `committee_round_open`，`:225-236` 才啟動 `cx_run`。
若把 `stamp-target` 驗證放在 `cx_run`，一個 brief 打字錯誤會留下**無 family result 的 OPEN 債**
→ `debt_ledger --has-open` 回 1 → `gate.sh` 拒發 token → **全域治理阻塞**，且無機械清理路徑。
🔴 **精確位置＝`gate.sh dispatch` 之前**〔R2 `codex` REJECTED 具名更正〕：
本節初版寫「`gate.sh dispatch` 之後、`_open_debt` 之前」，**該位置使 V4–V6 的「audit 零新增」不可能成立**——
`gate.sh:240` 在 dispatch 成功路徑即 append `committee_dispatch`，而 `committee_run.sh:213` 呼叫 gate
在 `_open_debt`(:219) 之前。⇒ 驗證放在 gate 之後，audit 已多出 `committee_dispatch` ＋ 15 行散文區塊。

⇒ `stamp-target` 的**存在性、多值一致性、路徑合法性**一律由 `committee_run.sh` 在
**`gate.sh dispatch` 之前**驗證，位置＝既有 brief 驗證處（`committee_run.sh:91-92`，
與 `[ -f "${brief}" ]`／`out前綴須在 handoffs/` 同一段）；不通過 → `exit 2`，
**不發 token、不開債、不派工**，且 **audit 真正零新增**。
`cx_run.sh` 仍保留同一組驗證作為 defense-in-depth（涵蓋直呼路徑）。
⚠️ **此修法使本延伸的觸及面擴及 Task 1.2 的 `committee_run.sh`**——仍在同一 heading
`### Phase 1 — 留痕（依賴：Phase 0）` 之下，**不新增觸及 heading**。
附帶效益：既有六道前置本就有同一陷阱，本修法一併收斂。

- **路徑驗證**：須 `handoffs/` 前綴、不得含 `..`、檔案須存在。任一不成立 → rc=2。
- **執行時機**：CLI 結束、`_emit_family_result` 寫入**之後**。

🔴 **註冊條件（三者同時成立才呼叫 `register-output`）**：

1. **`_emit_family_result` 判定 `result_state=success`**（即 `cli_rc=0` 且產出非空）
   〔`CODEX-R1-P1-02`：原文未限定 CLI rc，與 §D5 V11「rc≠0 時零 `committee_output`」**直接互斥**〕
2. `stamp-target` 檔含**單一一行**同時滿足：家族 `<fam>`、`APPROVED`、`YYYY-MM-DD`、
   `task:<注入的 task_id>`、**`sha256:<該檔當下的 body_hash>`**
   〔`CODEX-R1-P1-01`＋`COMPOSER-R1-P2-01`：原文不含 body hash，錯 hash 仍會註冊，
   使 audit 狀態與 `reconcile_stamps_check` 狀態分叉〕
3. 家族名取 `${fam}`（`$1` 直取），**不得從路徑推導**（沿用 v2.9 紅線）

🔴 **predicate 實作契約**〔`CODEX-R1-P2-05`＋`COMPOSER-R1-P2-02`，兩家各自 probe 實證〕：
**必須以單一 regex 對同一行做一次匹配**；**明文禁止**以兩個以上獨立 `grep` 的交集代替——
兩家實跑證明「A 家族的 `APPROVED` 行」與「B 家族那行的 `task:`」會被 naive 兩次 grep 誤組成 true。

- **不符時的行為（合法 no-op）**：**不註冊**、印明確訊息、**不改變 `cx_run` 的 exit code**。
  理由：`REJECTED`／拒簽／未簽是**合法結果**，不得誤判為執行失敗。
- **註冊失敗的行為（與上者機械可分）**〔`CODEX-R1-P1-04`＋`COMPOSER-R1-P2-03`〕：
  三條件皆成立、已呼叫 `register-output` 但其 rc≠0 → **印可辨識的錯誤字串**、
  **不回捲**已寫入的 `committee_family_result`（append-only）、rc 不變，並具名為**待人工補記**。
  **這兩類不得共用同一條「rc 不變」規則帶過**（見 §D6#16）。
- **既有 brief 遷移**〔`CODEX-R1-P2-06`，實跑 18/18 缺欄〕：
  新欄**僅對本延伸生效後的新派工強制**。既有 18 份 `brief-kind: stamp` 歷史 brief
  **明示不再重跑**；確需重跑者，須先補 `stamp-target:` 欄。
  ⇒ 主委 brief §0 的 `assumed: stamp-target 不與既有 brief 解析衝突` **已被實測證偽**，改列為已知遷移成本。
- **冪等**：同一 `(task_id, path)` 重複執行會多寫一筆 `committee_output`。
  append-only 語意下無害（provenance 只需存在一筆 non-pending 事件）。
  **明文不做去重**——去重須掃全 audit，屬**線 C** 範圍。

### §D4 攻擊面盤點（依 `feedback_gate_script_full_attack_surface`）

| # | 面 | 判定 |
|---|---|---|
| S1 | `cx_run` 取得寫 `committee_output` 的權限＝**新增權限面** | 受限於「brief 宣告的單一 `stamp-target`」＋「該家族戳記已落地且 task 相符」。**嚴於現行人工路徑**（人工 `register-output` 完全不檢查戳記是否存在） |
| S2 | `stamp-target` 由主委寫的 brief 決定，可指向任意 `handoffs/` 檔 | **未擴大既有能力**：主委本來就能直接跑 `gate.sh register-output` 指任意 handoffs 檔 |
| S3 | prompt 注入值來自 audit，委員仍可自行改寫戳記內容 | 屬「蓄意繞過」，依 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` §0 **不在受理範圍**；記入 §D6 |
| S4 | `stamp-target` 多值宣告歧義 | 沿用 `brief-kind` 同型 fail-closed（該病根已於 `cx_run.sh:43-49` 具名處理） |
| S5 | 改法⑨在 `_emit_family_result` 之後執行，若 `register-output` 失敗 | **不得回捲**已寫入的 `committee_family_result`（append-only）；印**可辨識錯誤字串**、rc 不變，具名為待人工補記（V13 驗） |
| **S6** | **實作漂移**：實作者若以兩次檔案級 `grep` 的交集代替單行匹配，跨戳記行可誤組成 true〔`CODEX-R1-P2-05`＋`COMPOSER-R1-P2-02`〕 | **非蓄意面**（抄既有 `brief-kind` 解析寫法即會踩到）。§D3 predicate 契約明文禁止；V14 為常駐 mutation oracle |
| **S7** | **開債後拒派**留下無 family result 的 OPEN 債 → 全域治理阻塞〔`CODEX-R1-P1-03`〕 | 驗證上移至 `committee_run.sh` 開債前；V4–V6 增驗「audit 零新增、無殘留 OPEN 債」 |

### §D5 驗證（可證偽）

測試檔：`tests/governance/test_stamp_taskid_inject.py`（新增）。
**每條斷言須通過 mutation 檢查：閹割對應守衛 → 該條轉紅；復原 → 轉綠，逐條附 receipt**
（v2.9 B1 三家裁決要求，見 SPEC 檔頭 P1②）。

| # | 斷言 | 通過條件 |
|---|---|---|
| V1 | 合法輪次、`CX_STUB_MODE=success` | prompt 含 `你的 task-id=<open_ev.task_id>` 逐字 |
| V2 | `open_ev` 缺 `task_id` | rc≠0 且 audit **零新增** |
| V3 | `open_ev` 的 `task_id` 為空字串 | rc≠0 且 audit 零新增 |
| V4 | `brief-kind=stamp` 缺 `stamp-target:` | rc=2，未啟動 CLI，**且 audit 逐位元組零新增**（含**無** `committee_dispatch`、**無**散文區塊、**無** `committee_round_open`）、**未發 token**〔`CODEX-R1-P1-03`；位置由 R2 codex 更正為 gate 之前〕 |
| V5 | `stamp-target` 兩個不一致宣告 | 同 V4 全部條件 |
| V6 | `stamp-target` 指 `handoffs/` 外／含 `..`／檔不存在 | 同 V4 全部條件（三態分別驗，不得合併為一條） |
| V7 | stub 成功且目標檔含**相符**戳記行 | 產生恰一筆 `committee_output`，`output_path`＝`stamp-target`，`output_sha256`≠`pending` |
| V8 | stub 成功但目標檔**無**該家族戳記 | **零** `committee_output`；cx_run rc 與無此改法時相同 |
| V9 | 目標檔有該家族 `APPROVED` 但 `task:` 是**別的 id** | 零 `committee_output`（本改法的核心防線） |
| V10 | 目標檔為該家族 `REJECTED` | 零 `committee_output`；rc 不變 |
| V11 | CLI rc≠0 | 零 `committee_output`；`committee_family_result` 仍寫且 `result_state=failed` |
| V12 | `brief-kind` ∈ {review, consult, closure, impl} 且 brief 無 `stamp-target:` | 行為與本延伸前**逐位元組相同**（不誤擋回歸） |
| **V13** | 三條件皆成立、但 `register-output` 本身 rc≠0（例：該 task 無先行 `committee_dispatch`） | 印**可辨識錯誤字串**；`committee_family_result` 仍為 `success`；零 `committee_output`；**且此態與 V8/V10 的合法 no-op 在輸出上機械可分**〔`CODEX-R1-P1-04`＋`COMPOSER-R1-P2-03`〕 |
| **V14** | 目標檔含**兩行**戳記：A 家族 `APPROVED`＋錯 task／B 家族正確 task | **零** `committee_output`。**本條為 S6 的常駐 mutation oracle**：把 predicate 改成兩次獨立 grep 取交集 → 本條必須轉紅〔`CODEX-R1-P2-05`＋`COMPOSER-R1-P2-02`〕 |
| **V15** | 家族／`APPROVED`／日期／`task:` 全相符，但 `sha256:` 非該檔當下 body hash | **零** `committee_output`〔`CODEX-R1-P1-01`＋`COMPOSER-R1-P2-01`〕 |

**回歸**：`pytest tests/governance -q` 全綠（現況 447 passed），跑後執行 `bash scripts/restore_golden_inventory.sh`。

### §D6 誠實邊界（**只准增列，不准刪減**；接續 v2.9 §A 編號後）

12. **委員仍可寫錯戳記內容**：改法⑧只保證 task-id **被送到委員眼前**，不保證委員採用。
    採用與否由改法⑨的註冊條件**事後**擋，**不會自動修正戳記文字**。
    ⚠️ **「不相符則不註冊」的涵蓋範圍須逐項讀，不得整句外推**〔`CODEX-R1-P1-01` 指出原文過強〕：
    擋得住的＝家族不符／`REJECTED`／`task:` 不符／`sha256:` 不符／跨行組合／CLI 失敗（V8–V11、V14、V15）。
    **擋不住的**＝戳記格式與 hash 全對但語意造假（見第 14 條）、戳記寫在 `stamp-target` 以外的檔（見第 13 條）。
13. **改法⑨只覆蓋 `stamp-target` 單一檔**：委員若把戳記寫進其他檔，機器不知情，退回人工。
14. **不防蓄意**：委員可寫出格式相符但語意造假的戳記行。依 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` §0
    列為記錄，不在本延伸解決。
15. **直呼 `cx_run` 且該輪 `committee_round_open` 缺 `task_id`** → 一律拒派。
    現行 `committee_run.sh:198` 無條件寫入該欄，故正常路徑不受影響；受影響者僅手工偽造的 round。
16. **「合法 no-op」與「註冊失敗」是兩類，不得共用一條規則**〔`CODEX-R1-P1-04`〕：
    前者（未簽／`REJECTED`／不相符）＝**預期結果**，靜默不註冊即可；
    後者（三條件已成立但 `register-output` rc≠0）＝**系統故障**，須印可辨識錯誤字串並具名為
    **待人工補記**。兩者皆不改 `cx_run` rc，但**輸出必須機械可分**（V13 驗）。
    ⇒ 誠實邊界：本延伸**不保證** provenance 一定登記成功，只保證**失敗時不會偽裝成成功**。
17. **既有 18 份 `brief-kind: stamp` 歷史 brief 全數缺 `stamp-target:`**〔`CODEX-R1-P2-06` 實跑 18/18〕，
    生效後**不可原樣重跑**。這是本延伸的已知遷移成本，非缺陷。
18. **V2／V3 的兩個分支沒有各自獨立的 mutation oracle**〔`CODEX-R3-P1-01`，實作階段實測〕：
    「`open_ev` 缺 `task_id`」與「`task_id` 為空字串」由**同一個 guard block** 保護；
    單獨閹割其中一支時，下游的型別檢查與白名單 regex **仍會拒派**，故該分支**無法被單獨證偽**。
    現行測試以**整段 neuter** 同時覆蓋兩情境。
    ⇒ **本延伸不宣稱**「兩分支各自可證偽」。兩家一致認定單支閹割在現行 defense-in-depth 下
    機械上不可行（`COMPOSER-R3-P3-00` 第 3 點；`CODEX-R3-P1-01` 自陳「後續型別／regex gate
    會掩蓋單支 guard mutation」）。**不為了製造可證偽性而弱化 defense-in-depth。**
19. **`brief-kind` 值的兩項刻意行為**〔`COMPOSER-R3-P3-00`〕，記錄以免日後誤判為缺陷：
    ①尾隨空白經 trim 後視為合法（`brief-kind: stamp ` ＝ `stamp`）
    ②多行**完全相同**的宣告經 `sort -u` 去重後接受；只有**不一致**的多值才 `exit 2`
20. **E 類邊界的永久回歸矩陣**〔`CODEX-R3-P2-02`〕：`stampx`／尾空白／大寫／空值
    以及 `committee_run` 與直呼 `cx_run` 的 parity，**行為已實測正確**（rc=2、audit 零新增），
    但在補上矩陣測試前**無永久回歸保護**。
21. **#20 已閉合**〔閉合輪 `CODEX-R1-P3-00`，三家確認〕：群 H 已補上 **9 列 × 兩入口**
    的永久邊界矩陣（`test_group_h_e_boundary_matrix_committee` 與直呼 parity 各 9/9 PASSED）。
    主委獨立證偽：把 `committee_run.sh:102` 改回前綴擷取 → **5 failed**，復原 → 65 passed。
    ⇒ **#20 保留為歷史敘述**（記錄該缺口曾存在），現況已有回歸保護。

### §D7 明文不做（防 scope accretion）

- 不改 `gate.sh register-output` 本身的任何驗證
- 不改 `verify_task_provenance.py`
- 不做 `committee_output` 去重或 provenance 快取（屬**線 C**）
- **不對 brief 內的 task-id 文字做任何字面檢查**——無界字串空間，線 B 已實證此路不可行
- 不新增任何檢查器腳本（沿用 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` §6 原則）

## 戳記

🔴 **本檔的三家戳記不在本檔內，在收斂檔上。** 機檢請對**收斂檔**執行：

```
bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260802-p16-d001-r1-recon/synth.md
```
→ **rc=0**，`codex,composer,grok` 全數 APPROVED，
body sha256 `6eda520250473f4b0d00875589e89ab73f7ad83f5a41876401234092387c76c0`。

**⚠️ 對本檔（`docs/…D-001.md`）直接跑 `reconcile_stamps_check.sh` 會 rc=1，那是預期的，不是未核可。**

### 為什麼不能把戳記放在本檔內（**已知殘留，具名記錄**）

`docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` §3.2 字面要求「延伸檔須取得三家 RECONCILE-STAMP，
機檢 `reconcile_stamps_check.sh <檔>` rc=0」。**該條在現有工具下不可執行**：

1. `reconcile_stamps_check.sh:67` 對每枚戳記跑 `verify_task_provenance.py check-stamp`
2. provenance 通過需要一筆 `output_path` 指向該檔且 `output_sha256` 非 `pending` 的事件
3. 產生該事件的唯一入口是 `gate.sh register-output`，而它在 `:166-169`
   **明文只接受 `handoffs/` 內的檔案**，`docs/` 一律拒絕
4. ⇒ **任何放在 `docs/` 的延伸檔都無法取得可通過機檢的戳記**

同時 §3.1 要求來源與 lock 放在 `handoffs/reconcile/<session>/`，與 §2 模板把 `## 戳記` 放在延伸檔內
**互相矛盾**；唯一可執行的讀法即本檔採用的「戳記放收斂檔」。
**該程序 v1.0 自身即以此方式定案**（其檔頭「定案依據」指向 `handoffs/reconcile/20260801-gov-amend-r7/synth.md`）。

**新開票 `GOV-DOCS-STAMP-PROVENANCE`**：§3.2 與 §3.1／§2 的矛盾須修（走 §5 的 R）。
本輪依使用者定死的「沒有 100% 解 → 交付 95% 版、殘留具名記錄」**不在此處解決**。

**出生事故**：2026-08-02 TODO 戳記輪，`codex` 依 `AGENTS.md` 第 12 條 STAMP-BLOCKED
對本檔直接跑機檢得 rc=1 而正確停工。**是本檔未寫明戳記位置，非 codex 誤判。**

### 給執行端的判定規則（**動工前照這條檢查，不要對本檔跑機檢**）

| 要檢查的東西 | 指令 |
|---|---|
| 本 SPEC 是否已核可 | `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260802-p16-d001-r1-recon/synth.md` |
| 實作 TODO 是否已核可 | `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260802-p16-d001-todo-r1-recon/synth.md` |

兩者皆 rc=0 才可動工。
