# 治理批次 O3-extension + R7-emitter TODO　（DRAFT／基於 docs/GOV_O3EXT_R7_SPEC.md／2026-07-03）

**SPEC 索引追溯（100% 覆蓋）**：Task 合計 5——1.1「gate.sh emitter 擴觸發」、1.2「stamps_check 消費新事件」、2.1「checker 檔案類豁免」、2.2「legacy 8 檔註冊+補 commit」、3.1「回歸與文件」。§G=N/A（§N 登記）。§RISK=中、比照 (b) 嚴管。環境 flag 合計 1：`VERIFY_GATE_O3_FILECLASS`（預設 on）。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 反 R2 紅線：豁免必綁 audit 事件+sha256，**禁**純路徑 glob；HANDOFF.md/commit-msg/docs/* claim 檢查強度不變。
- audit.log append-only：只 append 事件，不刪不改既有行；不得為過閘改 8 檔原文。
- 防假綠：不放寬 tests/governance/ 既有斷言（尤其 test_verify_gate_redteam.py R1-R7 反例）；驗收 diff 斷言。
- Logging/錯誤：shell 腳本 fail-closed（讀不到 audit → exit 1 非跳過）；Python 檢查器沿既有 print-to-stderr 慣例。
- 測試隔離：沿 `VERIFY_GATE_RECEIPTS_DIR`/`VERIFY_GATE_AUDIT_LOG`/`GATE_DIR_OVERRIDE` 環境覆蓋模式，禁寫真實 `.claude/gate/`。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1+1.2 | 無 | 同為 emitter/consumer 事件鏈,一起測 | 中 |
| B2 | 2.1 | B1(事件 schema 定案) | checker 獨立模組 | 中 |
| B3 | 2.2+3.1 | B1+B2 | 註冊操作+全回歸+文件,收尾一批 | 小 |
- 批次 Gate：B1→`pytest tests/governance/test_verify_gate_r7ext.py -q` 全綠**且 collected>0**；B2→`pytest tests/governance/test_verify_gate_o3ext.py tests/governance/test_verify_gate_redteam.py -q` 全綠**且 o3ext collected>0**；B3→`pytest tests/governance/ -q` 全綠(基線 106 只增不減)。**兩個新測試檔目前不存在=B1/B2 各自的第一個子任務，不得空檔（防 0 collected 假綠）。**
- 派工 prompt：見各 Phase（執行端讀本檔+SPEC 即可，兩檔皆在 repo）。

## Phase 1 — R7-emitter（目標：任何帶 --task-id 的派工皆有 provenance；完成後 stamp-review 不再 waived）

### Task 1.1 — gate.sh emitter 擴觸發
- SPEC ref：Task 1.1　目標：`--task-id` 存在即 emit committee_dispatch；新增 `register-output` 子命令。
- 輸入/輸出：argv（`--task-id`、可選 `--output <path>`）→ audit log JSON 行（dispatch_ts/task_id/output_path/family/output_sha256，檔案不存在記 `pending`）。
- 實作要點（≥3）：
  1. `scripts/gate.sh` dispatch 分支尾端：`[ -n "${task_id}" ] && _append_committee_dispatch_any "${output_path:-}" "${task_id}"`——新函式泛化自 `_append_committee_dispatch`（gate.sh:52），path 可空/pending。事件欄位名用 **`output_path`**（與 gate.sh:84/verify_task_provenance.py:109 現碼一致，禁 `out_rel` 新名）；事件行經 `"${VENV_PY}" -c 'import json; print(json.dumps({...}))'` 產生，禁 printf 裸拼（防 task_id/path 含引號換行的 JSON 注入）。
  2. 新子命令 `gate.sh register-output <task-id> <path>`：**先驗同 task_id 的 committee_dispatch 事件已存在，否則 exit 1**（防無派工自造豁免鏈=R2 復辟）；**拒絕 `legacy-*` task-id**；驗 path 存在且以 `handoffs/` 開頭（拒 docs/、拒絕不存在檔、拒 `..` 正規化逃逸——沿 R4 路徑正規化函式）；emit `committee_output` 事件記 **raw file bytes 的 sha256**（與 gate.sh:79-81 一致；**禁用 reconcile_body_hash.sh**——委員會檔無戳記節會 ERROR，兩 hash 語義不可混用）。
  3. 既有高風險+adversarial 分支的 `_append_committee_dispatch` 呼叫保留不動（W3 語義不變）。stamp-review 派工今後**必帶 `--output <reconcile路徑>`**（Task 1.2 閉合鏈前提）。
- 修改檔案：`scripts/gate.sh`（dispatch 分支、新函式 `_append_committee_dispatch_any`、新 case `register-output`）。既有 caller：settings.json hook `gate_check.sh` 不需改（只讀 token）。
- 不可做：不改 W3 fail-closed case 分支；不動 token TTL/檢查邏輯；不 emit 無 task-id 的事件。
- 邊界（≥2）：①`--output` 檔不存在→事件 output_sha256=`pending`、exit 0；②同 task-id 重複 register-output→append 第二筆事件，舊事件保留；③register-output 對 `docs/x.md` 或 `../etc`→exit 1；④register-output 無先行 dispatch→exit 1；⑤task_id 含 `"`/`\n`/unicode fuzz→事件仍單行合法 JSON。
- 風險緩解：R2 走私（prior-dispatch 強制+路徑域限+正規化）、F4 注入（json.dumps）。
- 驗證：`pytest tests/governance/test_verify_gate_r7ext.py -q` 全綠——risk low 無 adversarial 帶 `--task-id` 派工後 `grep -c committee_dispatch $AUDIT`==1 且欄位齊；無 `--task-id` 派工後 grep 計數==0。

### Task 1.2 — reconcile_stamps_check 消費新事件
- SPEC ref：Task 1.2　目標：戳記 task:<id> 可經 Task 1.1 事件通過 W2 provenance。
- 輸入/輸出：戳記行（family/APPROVED/sha256/task:<id>）+ audit log → PASS/FAIL。
- 實作要點（≥3）：
  1. `scripts/reconcile_stamps_check.sh` W2 段（:59 起）：現查 committee_dispatch 之處，擴為「committee_dispatch **或** committee_output 事件，task_id 相符且（output_path==被戳記檔 或 事件 sha256==戳記 sha256）」；pending sha 且無 register-output → 不通過。
  2. audit log 缺失/不可讀→維持既有 fail-closed（exit 1）。
  3. grandfather 日期判斷（2026-07-01 前）原邏輯不動。
- 修改檔案：`scripts/reconcile_stamps_check.sh`（W2 檢查段）。既有 caller：`gate.sh` dispatch `--spec` 分支（不需改）。
- 不可做：不移除 body_hash 相符檢查；不放寬 family 全數 APPROVED 要求。
- 邊界（≥2）：①偽 task-id（audit 無事件）→exit 1 並列缺失 family；②事件存在但 sha256 與戳記不符且 output_path 也不符→exit 1。
- 風險緩解：⊘（消費端，無新攻擊面）。
- 驗證：`pytest tests/governance/test_verify_gate_r7ext.py -q`——走 Task 1.1 派工+register-output+戳記→`reconcile_stamps_check.sh` exit 0 輸出含 `PASS`；偽 task-id→exit 1。

### Phase 1 測試
單元：emitter 欄位/邊界；整合：dispatch→register→stamps_check 全鏈；Gate：`pytest tests/governance/test_verify_gate_r7ext.py -q` 全綠。

## Phase 2 — O3-extension 檔案類豁免（目標：已註冊+hash 相符的委員會過程檔可過 checker；完成後 8 檔可補 commit）

### Task 2.1 — checker 檔案類豁免（provenance 綁定）
- SPEC ref：Task 2.1　目標：handoffs/ 下有事件且內容 sha256 相符的檔，prose claim 免 backing。
- 輸入/輸出：unit（source_file+text）+ audit log → 豁免判定 bool。
- 實作要點（≥3）：
  1. `scripts/verification_claim_check.py` 新函式 `_committee_registered_files() -> dict[str, set[str]]`：讀**委員會審計 log** `.claude/gate/audit.log`（新 `_committee_audit_path()`，環境覆蓋 `VERIFY_GATE_COMMITTEE_AUDIT_LOG`，沿 verify_task_provenance.py:19 慣例；**禁用 `_audit_log_path()`——那是 verify_audit.log receipt 審計，不同 log，混讀=豁免必失效**）每行 JSON，收 committee_dispatch/committee_output 的 `{output_path: {sha256,...}}`；log 缺失/壞行回空/跳過（=無豁免，fail-closed）。
  2. 新函式 `_is_committee_process_exempt(unit) -> bool`：`unit.source_file` 正規化後以 `handoffs/` 開頭、命中 registered map、且 `sha256(當前檔 raw bytes)`∈集合（與 register-output 同演算法，無額外正規化）→ True。`HANDOFF.md`/commit-msg/docs 路徑直接 False。
  3. 主判定鏈：在 operational claim 判 FAIL 前插入 `if _is_committee_process_exempt(unit) and os.environ.get("VERIFY_GATE_O3_FILECLASS","1")!="0": continue`。
- 修改檔案：`scripts/verification_claim_check.py`（兩新函式+主鏈一處）。既有 caller：pre-commit hook/`verify_pretooluse.sh`/CI workflow 三消費端不需改（介面不變）。
- 不可做：不豁免 docs/*；不加路徑 glob 白名單；不動既有內容級 O3（:369-370）；不快取跨呼叫狀態。
- 邊界（≥2）：①audit log 空檔→8 檔照常 FAIL；②檔案改一字→sha 不符→FAIL；③CRLF 檔→hash 正規化後仍相符；④`VERIFY_GATE_O3_FILECLASS=0`→全部豁免失效。
- 風險緩解：R2（hash 綁定+域限 handoffs/）、R3（豁免不及 HANDOFF/commit）。
- 驗證：`pytest tests/governance/test_verify_gate_o3ext.py -q` 全綠——已註冊+相符→checker exit 0；改一字→exit 1；同 prose 放 HANDOFF.md→exit 1；`pytest tests/governance/test_verify_gate_redteam.py -q` R2 反例回歸全綠。

### Task 2.2 — legacy 8 檔一次性註冊 + 補 commit
- SPEC ref：Task 2.2　目標：§A.4 清單 8 檔經 register-output 註冊後補 commit。
- 輸入/輸出：8 檔路徑 → 8 筆 committee_output 事件 + 1 個 commit。
- 實作要點（≥3）：①task-id 可稽者用原 id 走 `register-output`；不可稽者走一次性 `scripts/register_legacy_committee_files.sh`（8 檔白名單+當下 sha256 寫死於腳本、白名單耗盡即拒絕；主命令拒 `legacy-*`）；②註冊後 `python scripts/verification_claim_check.py --files <8檔>` 驗 exit 0；③commit 訊息引用本 SPEC/TODO 並明標 legacy 通道使用（R6 反假歸屬）。**此 Task 由編排端（Claude）執行，不派執行端**（涉 commit 權限與人工判斷 task-id 對應）。
- 修改檔案：無程式碼。既有 caller：⊘。
- 不可做：不改 8 檔原文；不用未經 register 的路徑直接繞 checker。
- 邊界（≥2）：①register-output 對不存在檔→exit 1；②註冊後又改檔→commit 時 checker FAIL（預期，需重新 register）。
- 風險緩解：R6 假歸屬（legacy id 明標非原 task）。
- 驗證：`python scripts/verification_claim_check.py --files <8檔>` exit 0；改任一檔一字重跑→exit 1 且報該檔名。

### Phase 2 測試
單元：豁免判定矩陣（註冊×hash×路徑域）；整合：register→checker→commit 鏈；Gate：`pytest tests/governance/test_verify_gate_o3ext.py tests/governance/test_verify_gate_redteam.py -q` 全綠。

## Phase 3 — 回歸與文件（目標：全套護網不回退；完成後本 epic 關閉）

### Task 3.1 — governance 全回歸 + 文件增補
- SPEC ref：Task 3.1　目標：全套回歸+兩文件增補。
- 輸入/輸出：Phase 1+2 產物 → 綠燈回歸 + `docs/MULTI_AGENT_ORCHESTRATION.md` Gate 節、`docs/VERIFY_GATE_SPEC.md` 增補段。
- 實作要點（≥3）：①`pytest tests/governance/ -q` 全綠且數量≥106+新增；②`git diff tests/governance/` 人工檢視零放寬；③文件增補：register-output 用法、檔案類豁免語義、`VERIFY_GATE_O3_FILECLASS` 逃生口。
- 修改檔案：兩 docs 檔對應節。既有 caller：⊘。
- 不可做：不改紅隊反例測試預期方向；文件不寫「已驗/真紅」裸聲稱（沿引用格式）。
- 邊界（≥2）：①`VERIFY_GATE_O3_FILECLASS=0` 全豁免失效、行為==現狀；②audit log 空檔時 checker 對 8 檔照常 FAIL。
- 風險緩解：⊘。
- 驗證：`pytest tests/governance/ -q` 全綠（≥106+新增數）；`git diff tests/governance/ | grep -c "^-.*assert"`==0（無刪斷言）。

### Phase 3 測試
Gate：`pytest tests/governance/ -q` 全綠。

---
**自檢（階段 3）**：追溯 5/5 Task 全對應（1.1/1.2/2.1/2.2/3.1）；每 Task 含實作要點≥3/修改檔案到函式/邊界≥2/驗證可證偽/不可做；單層（governance scripts）無全棧鏈 ⋅跳過；錨點 §0/§B/驗證/邊界/不可做齊。
**Frozen 前 handoff**：`SPEC=docs/GOV_O3EXT_R7_SPEC.md TODO=docs/GOV_O3EXT_R7_TODO.md FOCUS=R2走私復辟/hash繞過/audit汙染`——用 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 獨立審查（Composer），Blocking 修補後才 Frozen。現狀=`Internal Frozen`。
