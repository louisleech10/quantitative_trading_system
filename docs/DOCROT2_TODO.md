# DOCROT2 TODO（DRAFT｜基於 `docs/DOCROT2_SPEC.md`｜2026-09-15）

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 產出端覆蓋鐵律：每道新檢查掛寫檔當下；掛不上者登記 `governance-enforcement`（SPEC §C）。
- 不接受紀律／記憶當解法：任何「須記得做」之步驟一律改為機械閘或具名殘留（SPEC §C）。
- 面向未來：既有行不回洗；新增行、新檔、Task 4.1 遷移之檔才受新規則全量約束；`status_scope_grandfathered` 只准縮小。
- 單一真相源：新封閉集合只定義於 JSON（`scripts/live_doc_registry.json`、`scripts/governance_verdicts.json`、`scripts/fact_keys.json`）；本 TODO 不列舉值。
- 不弱化既有檢查：SPEC §C 所列六個既有測試檔之斷言零刪減；DOCROT Task 1.1–1.6、1.8 保留。
- 測試一律逐檔明列路徑執行，禁 glob、禁無路徑 `pytest`；治理全套為小時級，只在收票前丟背景跑一次。
- 實作者＝主委；每批完成後兩家審碼（`scripts/governance_families.json` 之 `active_stampers`），原提出方閉合後才進下一批。
- 防假綠：新斷言對應新行為；每道新判定附 mutation（SPEC §V 七條）且實跑改壞轉紅後還原。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| D2A | Task 0.1、1.1、1.2、1.3 | 無 | 登記層：票、活文件類別、狀態種類、生成器來源欄位同屬 `scripts/fact_keys.json`／新登記檔，拆開會使中間態不一致 | 中 |
| D2B | Task 2.1、2.2、2.3、2.4、2.5 | D2A | 同一入口 `scripts/live_doc_write_guard.sh` 與同一次 `.claude/settings.json` 掛載 | 大 |
| D2C | Task 3.1、3.2 | 無（可早於 D2B） | 量測層獨立於擋層；3.2 之擋下事件於 D2B 落地後補接 | 中 |
| D2D | Task 4.1 | D2A、D2B、D2C | 遷移須在規則全部上線後一次完成 | 中 |

- 批次狀態：Task 0.1 落地後由 `scripts/fact_keys.json` 生成至本節（本表不手寫狀態）。
- 批次間 Gate：前批審碼輪兩家 `VERDICT: proceed` 或 blocked 項已由原提出方 CLOSED；`bash scripts/gen_fact_key_blocks.sh --check` rc=0；該批測試檔逐檔 `venv/bin/python -m pytest <檔> -q` 0 failed。

## Phase 0 — 開票登記（完成後：B-63 在票表、看板受監看）

### Task 0.1 — 登記票與批次狀態 key（`票 B-63`）
- SPEC ref：§C「產出端覆蓋鐵律」、§P Phase 1 前置　目標：本票自身之狀態從第一天起即走單一來源。
- 輸入 / 輸出：輸入 `scripts/fact_keys.json`、`handoffs/20260801-GOV-AMEND-BACKLOG.md`；輸出票列 `B-63`、批次狀態 key（`D2A`–`D2D`）、本 TODO §B 生成區塊、白話看板監看登記。
- 實作要點：
  1. `scripts/fact_keys.json` 之 `governance-ticket-sot` rows 追加 `B-63`（狀態值取既有 `status_enum`，狀態依據以「還缺：」起頭）。
  2. backlog 追加 `## B-63` 標題，使 `bash scripts/ticket_universe.sh --check` 對帳一致。
  3. 新增批次狀態 key，`target` 含 `docs/DOCROT2_TODO.md`，`_schema.status_keys` 追加該 key；本 TODO §B 插入邊界標記後跑 `bash scripts/gen_fact_key_blocks.sh --write`。
  4. `scripts/plain_docs_sync_check.sh` 追加 `DOCROT2施工進度.md` 之監看列（Task 2.5 改 catch-all 前之過渡登記）。
- 修改檔案：`scripts/fact_keys.json`（`governance-ticket-sot`、新 key、`_schema.status_keys`）；`scripts/plain_docs_sync_check.sh::_watched`（case 列）　既有 caller：`scripts/gen_fact_key_blocks.sh`、`scripts/ticket_universe.sh`、`scripts/factkey_write_guard.sh`（皆不改）。
- 路徑：
  - scripts/fact_keys.json
  - handoffs/20260801-GOV-AMEND-BACKLOG.md
  - docs/DOCROT2_TODO.md
  - scripts/plain_docs_sync_check.sh
  - 白話說明/DOCROT2施工進度.md
- 不可做：不得擴充 `status_enum`；不得在白話看板手寫批次或票狀態值。
- 邊界：①backlog 有 `## B-63` 而票表無 ⇒ `ticket_universe.sh --check` rc=1；②批次 key 之 target 缺邊界標記 ⇒ `gen_fact_key_blocks.sh --check` rc!=0。
- 風險緩解：⊘
- 驗證：`bash scripts/ticket_universe.sh --check` rc=0；`bash scripts/gen_fact_key_blocks.sh --check` rc=0；`bash scripts/factkey_write_guard.sh 白話說明/DOCROT2施工進度.md` rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：Task 4.1 不改本 Task 產出。

## Phase 1 — 登記（完成後：活文件類別封閉、產品 epic 狀態進入單一來源、投影可讀其他機器檔）

### Task 1.1 — 活文件類別登記（`票 B-63`）
- SPEC ref：§P Task 1.1　目標：封閉登記活文件與類別規則。
- 輸入 / 輸出：輸入 consult-r1 composer A1 分類；輸出 `scripts/live_doc_registry.json`、`scripts/live_doc_registry_check.sh`。
- 實作要點：
  1. JSON 定義類別集合、每類規則旗標（是否狀態權威、是否套新增行禁舊版字面、是否套概念移除檢查）、考古字面集合、流水帳標記格式、日誌類移出路徑、排除路徑；路徑編碼只允 exact 與 `/` 結尾 prefix。
  2. `live_doc_registry_check.sh --path <p>`：`docs/`、`白話說明/`、repo 根目錄 `.md` 未命中登記且未命中排除 ⇒ rc=1；`--all`：列舉全樹（`git ls-files --cached --others --exclude-standard -z`，NUL-safe，同 `_fk_scope_files`）逐檔判定。
  3. 一致性：`scripts/fact_keys.json` `_schema.status_scope` 每項須落在登記類別內，否則 `--all` rc=1。
  4. symlink、非 regular file、登記檔非 JSON ⇒ rc=1。
- 修改檔案：新建 `scripts/live_doc_registry.json`、`scripts/live_doc_registry_check.sh::main`　既有 caller：新建無。
- 路徑：
  - scripts/live_doc_registry.json
  - scripts/live_doc_registry_check.sh
  - tests/governance/test_docrot2_registry.py
  - tests/governance/fixtures/docrot2/
- 不可做：不得使用 glob；不得登記 `handoffs/` 為活文件；不得改任何 hook 掛載。
- 邊界：①`docs/site/x.md` ⇒ rc=0（排除）；②含換行之檔名 ⇒ 正確判定不切碎；③`status_scope` 含未登記路徑 ⇒ `--all` rc=1。
- 風險緩解：⊘
- 驗證：`tests/governance/test_docrot2_registry.py` 之 fixture `unregistered`／`registered`／`status_scope_outside_registry` 對應 rc=1／rc=0／rc=1；`venv/bin/python -m pytest tests/governance/test_docrot2_registry.py -q` 0 failed。
- **存活至**：全票完工後常設。
- **覆蓋風險**：Task 2.3、2.5 只消費本檔，不改 schema。

### Task 1.2 — 狀態種類擴充（`票 B-63`）
- SPEC ref：§P Task 1.2　目標：SPLITUNIFY 批次、Task、殘留狀態進入 `scripts/fact_keys.json`。
- 輸入 / 輸出：輸入 `docs/SPLITUNIFY_TODO.md` §B／§E 現行狀態；輸出新 status key 與 rows、`_schema.status_keys` 追加。
- 實作要點：
  1. 每個新 key 宣告 `columns`（識別碼必在第 2 欄）、`target`（投影宿主，Task 4.1 插標記前先指向 fixture 以通過 `--check`，或與 Task 4.1 同批——本批選前者並於 D2D 改指現行檔）。
  2. rows 狀態值 ∈ 既有 `status_enum`；同一識別碼不得出現在兩個 status key。
  3. `_fk_status_ids` 不改碼；以 fixture 證明新識別碼進入其輸出。
- 修改檔案：`scripts/fact_keys.json`（新 key、`_schema.status_keys`）　既有 caller：`scripts/gen_fact_key_blocks.sh::_fk_status_ids`、`_fk_reject_handwritten_status`（不改）。
- 路徑：
  - scripts/fact_keys.json
  - tests/governance/test_docrot2_registry.py
  - tests/governance/fixtures/docrot2/
- 不可做：不得擴充 `status_enum`；不得在任何 md 保留權威狀態值。
- 邊界：①識別碼跨 key 重複 ⇒ `--check` rc!=0；②`B9` 與 `B9A` token 邊界各一 fixture。
- 風險緩解：⊘
- 驗證：fixture `new_status_keys_registered` rc=0、`status_key_row_without_target_block` rc!=0；`bash scripts/gen_fact_key_blocks.sh --check` rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：Task 4.1 把 target 改指現行檔，rows 不變。

### Task 1.3 — 生成器讀取機器權威（`票 B-63`）
- SPEC ref：§P Task 1.3　目標：委員組成與規格版本投影不複製值。
- 輸入 / 輸出：輸入 `scripts/governance_families.json`、SPEC 檔頭機器行；輸出 `scripts/gen_fact_key_blocks.sh` rows 來源欄位支援、`_schema.fields` 定義。
- 實作要點：
  1. `_schema.fields` 新增 rows 來源欄位定義（repo 相對 JSON 路徑＋`jq` 表達式）與 SPEC 檔頭版本機器行格式。
  2. `gen_fact_key_blocks.sh` 讀取時 `LC_ALL=C`、禁絕對路徑與 `..`、`jq` 失敗 ⇒ rc!=0；同 key 同時有靜態 rows 與來源欄位 ⇒ rc!=0。
  3. 新增委員組成 key 與規格版本 key（不含委員型號）。
- 修改檔案：`scripts/gen_fact_key_blocks.sh::_fk_rows`（或現行 rows 讀取函式）、`scripts/fact_keys.json::_schema.fields`　既有 caller：`--check`／`--write` 全路徑。
- 路徑：
  - scripts/gen_fact_key_blocks.sh
  - scripts/fact_keys.json
  - tests/governance/test_docrot2_registry.py
  - tests/governance/test_govb1_factkey_gen.py
- 不可做：不得執行任意 shell；不得讀 repo 外檔；不得讓輸出隨環境變。
- 邊界：①來源檔缺失 ⇒ rc!=0；②絕對路徑 ⇒ rc!=0；③靜態 rows＋來源欄位並存 ⇒ rc!=0。
- 風險緩解：既有 `tests/governance/test_govb1_factkey_gen.py` 全檔須 0 failed（決定性契約回歸）。
- 驗證：fixture `rows_from_json_unchanged` rc=0、`rows_from_json_source_changed_without_write` rc!=0、`rows_from_absolute_path` rc!=0；`venv/bin/python -m pytest tests/governance/test_govb1_factkey_gen.py -q` 0 failed。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 1 測試 + Phase Gate
- 單元／邊界：`tests/governance/test_docrot2_registry.py`；回歸：`tests/governance/test_govb1_factkey_gen.py`、`tests/governance/test_factkey_write_guard.py`、`tests/governance/test_govb1_factkey_hook.py`。
- Gate：上列四檔逐檔 0 failed；mutation ③（SPEC §V）實跑轉紅後還原；D2A 審碼輪兩家閉合。

## Phase 2 — 產出端擋（完成後：活文件寫入前擋手寫狀態與新舊並存、pre-commit 兜底、交接檔流水帳有生命週期）

### Task 2.1 — 手寫狀態偵測之新增行模式（`票 B-63`）
- SPEC ref：§P Task 2.1　目標：非權威活文件之新增行含「識別碼＋狀態值」即寫入前擋。
- 輸入 / 輸出：輸入 PreToolUse payload；輸出 exit 2＋stderr 訊息。
- 實作要點：
  1. 新建 `scripts/live_doc_write_guard.sh`：解析 `tool_name`、`file_path`；非登記活文件 ⇒ exit 0。
  2. 新增行：Edit 取 `tool_input.new_string`；Write 以磁碟舊檔 `diff -u` 取 `+` 行（新檔＝全文）。
  3. 判定沿用 `gen_fact_key_blocks.sh` 之識別碼集合與 `status_enum`、`has_token` 邊界；以新增入口函式（例 `_fk_reject_handwritten_status_lines <rel> <lines-file>`）共用同一 awk 判定，禁複製第二份判定。
  4. 豁免：合法生成區塊內、`HISTORY-BEGIN..END` 內、fenced code block 內；「」引號不豁免。區塊與 fence 狀態須以舊檔上下文判定新增行所在位置。
  5. payload 不可解析且目標為登記活文件 ⇒ exit 2。
- 修改檔案：新建 `scripts/live_doc_write_guard.sh::main`；`scripts/gen_fact_key_blocks.sh`（新增共用入口，既有 `_fk_reject_handwritten_status` 行為不變）　既有 caller：`scripts/factkey_write_guard.sh`、`scripts/gov_check.sh` 段 3（皆不改）。
- 路徑：
  - scripts/live_doc_write_guard.sh
  - scripts/gen_fact_key_blocks.sh
  - tests/governance/test_docrot2_write_guard.py
  - tests/governance/fixtures/docrot2/
- 不可做：不得掃整檔既有行；不得以寫檔後鉤子宣稱已擋。
- 邊界：①Write 內容與磁碟相同 ⇒ exit 0；②新增行在 fence 內 ⇒ exit 0；③新檔含狀態行 ⇒ exit 2。
- 風險緩解：⊘
- 驗證：fixture `handoff_edit_adds_B9F_with_status` exit 2、`handoff_edit_adds_B9F_pointer_only` exit 0、`roadmap_edit_unrelated_line_with_legacy_status_elsewhere` exit 0、`efcafc63_handoff_status_lines_re_added` exit 2；`venv/bin/python -m pytest tests/governance/test_docrot2_write_guard.py -q` 0 failed。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 2.2 — 新增行禁舊版字面（`票 B-63`）
- SPEC ref：§P Task 2.2　目標：舊文只准進歷史專區。
- 輸入 / 輸出：同 Task 2.1 入口之第二道判定。
- 實作要點：
  1. 適用類別由 `scripts/live_doc_registry.json` 旗標決定；考古字面集合讀同檔。
  2. 新增行位於歷史專區外且含 `~~` 或考古字面 ⇒ exit 2。
  3. 新增行含 canonical finding ID（沿用 `scripts/_synth_attr.py` 之 `ID_RE` 形狀）且位於歷史專區外 ⇒ exit 2。
  4. 歷史專區內之新增行豁免；整段移入專區（正文刪、專區增）⇒ exit 0。
- 修改檔案：`scripts/live_doc_write_guard.sh::check_archaeology`　既有 caller：無。
- 路徑：
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry.json
  - tests/governance/test_docrot2_write_guard.py
- 不可做：不得要求既有刪除線清零；不得擴及 `handoffs/`。
- 邊界：①日誌類檔 ⇒ exit 0；②`templates/` 範例字面依類別旗標，fixture 各一。
- 風險緩解：⊘
- 驗證：fixture `spec_edit_adds_strikethrough_outside_history` exit 2、`spec_edit_adds_strikethrough_inside_history` exit 0、`todo_edit_unrelated_line_with_legacy_strikethrough_elsewhere` exit 0、`spec_edit_adds_finding_id_outside_history` exit 2。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 2.3 — pre-commit 兜底與未登記路徑（`票 B-63`）
- SPEC ref：§P Task 2.3　目標：Bash／生成器／委員 CLI 寫入在 commit 時被擋。
- 輸入 / 輸出：輸入暫存差異；輸出 commit rc!=0。
- 實作要點：
  1. `live_doc_write_guard.sh --staged`：`git diff --cached -U0` 取各登記活文件之新增行，套 Task 2.1、2.2 判定。
  2. `live_doc_registry_check.sh --staged`：暫存之新增 `.md` 未登記 ⇒ rc=1。
  3. `scripts/git_hooks/pre-commit` 呼叫兩者，任一非零即中止；無略過旗標。
- 修改檔案：`scripts/git_hooks/pre-commit`（新增段）、`scripts/live_doc_write_guard.sh::staged_mode`、`scripts/live_doc_registry_check.sh::staged_mode`　既有 caller：pre-commit 既有段（不改順序以外之行為）。
- 路徑：
  - scripts/git_hooks/pre-commit
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry_check.sh
  - tests/governance/test_docrot2_write_guard.py
- 不可做：不得提供略過旗標；不得在 pre-push 重複。
- 邊界：①暫存刪除檔 ⇒ 不檢查；②重新命名 ⇒ 以新路徑判類別。
- 風險緩解：⊘
- 驗證：fixture `bash_redirect_added_status_line_staged` rc!=0、`clean_staged_diff` rc=0、`new_unregistered_md_staged` rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 2.4 — 交接檔流水帳生命週期（`票 B-63`）
- SPEC ref：§P Task 2.4　目標：已結束工作之流水帳不得留在交接檔。
- 輸入 / 輸出：輸入暫存之 `HANDOFF.md`、`scripts/fact_keys.json` 狀態、`bash scripts/debt_ledger.sh --list`；輸出 rc。
- 實作要點：
  1. 解析 `HISTORY-BEGIN..END` 內每則之識別碼標記（格式讀 `scripts/live_doc_registry.json`）；無標記 ⇒ rc=1。
  2. 識別碼狀態 ∈ `_schema.enforcement_completed_statuses` ⇒ rc=1，訊息指明移至日誌類檔案路徑。
  3. 「待辦」區段引用之 session 名於 debt ledger 為 `CLOSED` ⇒ rc=1。
  4. 登記為一致性型（跨檔讀狀態），掛 pre-commit；登記理由寫入 `governance-enforcement`。
- 修改檔案：`scripts/live_doc_write_guard.sh::check_handoff_lifecycle`　既有 caller：`scripts/inject_handoff.sh`（不改）。
- 路徑：
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry.json
  - tests/governance/test_docrot2_write_guard.py
- 不可做：不得以行數判定；不得刪除流水帳而不移至登記之日誌類檔。
- 邊界：①同一 commit 內狀態轉完成且已移出 ⇒ rc=0；②標記引用未登記識別碼 ⇒ rc=1；③`## 坑` 引用已結束工作 ⇒ 不受本判定。
- 風險緩解：⊘
- 驗證：fixture `handoff_history_entry_for_completed_batch` rc!=0、`handoff_history_entry_for_open_batch` rc=0、`handoff_todo_cites_closed_session` rc!=0、`handoff_history_entry_without_marker` rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：Task 4.1 首次把現行交接檔改為本結構。

### Task 2.5 — 既有檢查依類別適用、宣稱與規則同步、掛載（`票 B-63`）
- SPEC ref：§P Task 2.5　目標：消除已知摩擦、過期宣稱與互斥規則，並掛上 Task 2.1–2.4。
- 輸入 / 輸出：輸入各既有檔；輸出最小改動＋`.claude/settings.json` PreToolUse Edit|Write 掛 `scripts/live_doc_write_guard.sh`。
- 實作要點：
  1. `scripts/spec_xref_hook.sh`：「概念被拿掉」只對登記為 LIVE-SPEC 類之檔執行；未登記路徑行為不變。
  2. `scripts/plain_docs_sync_check.sh`：catch-all 改為查 `scripts/live_doc_registry.json`，未登記 ⇒ rc!=0（取代 Task 0.1 過渡列之必要性）。
  3. `CLAUDE.md:16` 與 `.claude/settings.json` PreCompact 訊息刪除 HANDOFF 行數上限，改寫為「現況／待辦須與權威一致，已結束工作不得留存」之指標句。
  4. `scripts/fact_keys.json` `governance-enforcement` 追加 DOCROT Task 1.1–1.8 與本票各閘列（掛載點須實際存在，由 `_fk_validate_enforcement` 對證）；DOCROT Task 1.3 之宣稱文字改為只擋「共 N 條」雙落點、不涵蓋交接檔。
  5. `.claude/settings.json` 新增 PreToolUse 掛載與本 Task 同一 commit。
- 修改檔案：`scripts/spec_xref_hook.sh::main`、`scripts/plain_docs_sync_check.sh::_watched`、`CLAUDE.md`、`.claude/settings.json`（hooks.PreToolUse、hooks.PreCompact）、`scripts/fact_keys.json::governance-enforcement`　既有 caller：各檔既有測試。
- 路徑：
  - scripts/spec_xref_hook.sh
  - scripts/plain_docs_sync_check.sh
  - CLAUDE.md
  - .claude/settings.json
  - scripts/fact_keys.json
  - tests/governance/test_docrot2_class_routing.py
- 不可做：不得改變 `spec_xref_hook.sh` 對 LIVE-SPEC 類之判定寬嚴；不得刪除 DOCROT Task 1.1–1.3 掃描器。
- 邊界：①未登記路徑之 `spec_xref_hook.sh` 行為與改前相同（fixture 對照）；②`governance-enforcement` 新列掛載點不存在 ⇒ `gen_fact_key_blocks.sh --check` rc!=0。
- 風險緩解：`.claude/settings.json` 改動後以 `jq empty .claude/settings.json` rc=0 驗 JSON 合法，避免 hook 全面失效。
- 驗證：fixture `handoff_remove_current_lines_history_keeps_concept` rc=0、`spec_remove_concept_live_reference_remains` rc=2、`new_unregistered_plain_doc` rc!=0；`grep -c '30 行' CLAUDE.md` 輸出 0；`bash scripts/gen_fact_key_blocks.sh --check` rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 2 測試 + Phase Gate
- `tests/governance/test_docrot2_write_guard.py`、`tests/governance/test_docrot2_class_routing.py`；回歸 SPEC §C 六檔＋`tests/governance/` 內 `spec_xref`、`plain_docs_sync` 既有測試檔（逐檔明列於審碼 brief）。
- Gate：mutation ①②⑥⑦ 實跑轉紅後還原；D2B 審碼輪兩家閉合。

## Phase 3 — 量測（完成後：每輪類別雙填、收案寫量測事件、擋下寫事件、報表可跑）

### Task 3.1 — finding 類別欄雙填（`票 B-63`）
- SPEC ref：§P Task 3.1　目標：每條 finding 有機械可算之類別。
- 輸入 / 輸出：輸入委員交件、收斂檔；輸出 `completeness_check.sh --single` 與 `_synth_attr.py --mode gate` 之 rc（0／1）。
- 實作要點：
  1. `scripts/governance_verdicts.json` 新增類別封閉集合（初值取 consult-r1 composer F3）。
  2. 兩份範本新增 `**類別**:` 行；`scripts/completeness_check.sh::_validate_finding_body`（或 `--single` 路徑新函式）驗委員欄 ∈ 集合。
  3. `scripts/_synth_attr.py` 新增 `check_category`：群集表須有主委類別欄；委員欄與主委欄不一致之 finding 須列於「類別不一致」段且附處置 token，否則錯。
  4. forward-only：以本 Task commit 之後建立之交件／收斂檔為適用範圍（判定依據寫入 JSON，不靠日期記憶）。
- 修改檔案：`scripts/governance_verdicts.json`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`、`scripts/completeness_check.sh::_validate_finding_body`、`scripts/_synth_attr.py::check_category`　既有 caller：`scripts/cx_run.sh`、`scripts/synth_attribution_hook.sh`、`scripts/reconcile_cluster_attribution_check.sh`、`scripts/debt_clear.sh`。
- 路徑：
  - scripts/governance_verdicts.json
  - templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
  - templates/COMMITTEE_FINDING_TEMPLATE.md
  - scripts/completeness_check.sh
  - scripts/_synth_attr.py
  - tests/governance/test_docrot2_metrics.py
- 不可做：不得讓主委欄作分子；不得對舊交件回溯。
- 邊界：①零 findings sentinel 仍須類別欄；②上線前舊交件重跑 ⇒ 豁免。
- 風險緩解：`tests/governance/test_docrot_e3_brief_placeholder.py` 與既有 completeness 測試逐檔 0 failed。
- 驗證：fixture `p1_without_category` rc=1、`p1_category_outside_set` rc=1、`category_mismatch_unlisted` rc=1、`category_mismatch_listed_with_disposition` rc=0；`venv/bin/python -m pytest tests/governance/test_docrot2_metrics.py -q` 0 failed。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 3.2 — 收案量測事件與擋下事件（`票 B-63`）
- SPEC ref：§P Task 3.2　目標：成效逐輪機械記錄。
- 輸入 / 輸出：輸入收斂檔、交件、各閘擋下；輸出 audit 事件與 `scripts/docrot2_metrics.sh` 報表。
- 實作要點：
  1. `scripts/audit_events.json` 登記收案量測事件與擋下事件之名稱、必填欄與允許之 origin script。
  2. `scripts/debt_clear.sh` 收案前計算各類別計數、類別不一致數，寫事件；缺值或寫入失敗 ⇒ rc!=0。
  3. `live_doc_write_guard.sh`、`live_doc_registry_check.sh` 擋下時寫擋下事件；寫入失敗仍擋。
  4. `scripts/docrot2_metrics.sh` 以 `jq` 讀事件，依票與輪次輸出計數與占比。
- 修改檔案：`scripts/audit_events.json`、`scripts/debt_clear.sh::main`（收案前段）、`scripts/live_doc_write_guard.sh::emit_block_event`、`scripts/live_doc_registry_check.sh::emit_block_event`、新建 `scripts/docrot2_metrics.sh::main`　既有 caller：`scripts/audit_append.sh`（不改）。
- 路徑：
  - scripts/audit_events.json
  - scripts/debt_clear.sh
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry_check.sh
  - scripts/docrot2_metrics.sh
  - tests/governance/test_docrot2_metrics.py
- 不可做：不得以 `doc_friction_ratio` 字面作分子；不得寫入推定之委員型號。
- 邊界：①audit 寫入失敗 ⇒ 收案 rc!=0；②擋下事件寫入失敗 ⇒ 仍 exit 2。
- 風險緩解：`tests/governance/test_debt_emit.py` 既有紅基準（隔離 repo 缺依賴）不得增加，逐條對讀。
- 驗證：fixture `synth_without_category_counts` rc!=0、`valid_round` rc=0 且 audit 事件逐欄以 `jq` 對讀；擋下 fixture 後 audit 含對應事件 1 筆。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 3 測試 + Phase Gate
- `tests/governance/test_docrot2_metrics.py`；回歸：completeness 與 synth_attr 既有測試檔（逐檔明列於審碼 brief）。
- Gate：mutation ④⑤ 實跑轉紅後還原；D2C 審碼輪兩家閉合。

## Phase 4 — 遷移（完成後：現行活文件狀態全為投影、交接檔只留進行中工作）

### Task 4.1 — 現行活文件改為投影結構（`票 B-63`）
- SPEC ref：§P Task 4.1　目標：交接檔、ROADMAP、白話進度表、SPLITUNIFY 施工清單之狀態改由生成區塊提供。
- 輸入 / 輸出：輸入 Phase 1–3 產出；輸出遷移後之活文件與日誌類檔。
- 實作要點：
  1. Task 1.2／1.3 之 key `target` 改指現行檔並插入邊界標記，`bash scripts/gen_fact_key_blocks.sh --write`。
  2. 刪除區塊外之手寫狀態值；`HANDOFF.md` 改為「現況（生成）／待辦／坑／歷史區（帶識別碼標記）」結構，已結束工作之流水帳移至登記之日誌類檔。
  3. 白話進度表生成區塊每列含識別碼、狀態值與權威相對路徑。
  4. 以 `bash scripts/live_doc_write_guard.sh --staged` 驗本 commit 全部新增行。
- 修改檔案：`HANDOFF.md`、`docs/ROADMAP.md`、`白話說明/SPLITUNIFY施工進度.md`、`白話說明/接下來要做什麼.md`、`docs/SPLITUNIFY_TODO.md`（§B、§E）、`scripts/fact_keys.json`（target）　既有 caller：`scripts/inject_handoff.sh`、`scripts/plain_docs_render.sh`（不改）。
- 路徑：
  - HANDOFF.md
  - docs/ROADMAP.md
  - 白話說明/SPLITUNIFY施工進度.md
  - 白話說明/接下來要做什麼.md
  - docs/SPLITUNIFY_TODO.md
  - scripts/fact_keys.json
- 不可做：不得改已結案 epic 文件；不得改 `docs/SPLITUNIFY_SPEC.D-002.md`（SPEC §N 殘留）；不得修改任何檢查判定。
- 邊界：①`scripts/inject_handoff.sh` 注入內容含生成區塊（對讀）；②遷移前後 SPLITUNIFY 殘留識別碼集合相同（逐 ID 對讀）。
- 風險緩解：遷移前後各跑 `bash scripts/gen_fact_key_blocks.sh --check` 與 `bash scripts/plain_docs_render.sh --check`。
- 驗證：`bash scripts/gen_fact_key_blocks.sh --check` rc=0；`bash scripts/live_doc_write_guard.sh --staged` rc=0；`bash scripts/plain_docs_render.sh --check` rc=0；`bash scripts/live_doc_registry_check.sh --all` rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 4 測試 + Phase Gate
- 上列四命令；收票前丟背景跑一次 `bash scripts/gov_check.sh --no-probe` 並讀 pytest 自身 passed／failed 行。
- Gate：D2D 審碼輪兩家閉合；SPEC §V 成效判準之量測起點記錄於第一張後續中大票。
