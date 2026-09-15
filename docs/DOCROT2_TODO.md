# DOCROT2 TODO（DRAFT v5｜基於 `docs/DOCROT2_SPEC.md` v5｜2026-09-15）

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 產出端覆蓋鐵律：新檢查掛寫檔當下；掛不上者登記 `governance-enforcement` 並寫理由（SPEC §C）。
- 不接受紀律／記憶當解法：「須記得做」一律改機械閘或具名殘留。
- 面向未來：既有行不回洗；「上線後」以 audit 序號或 commit 判定，禁日期、mtime。
- 單一真相源：本 TODO 所列初始值只作寫入 JSON 之來源；寫入後以 JSON 為準，本 TODO 不再同步維護。
- 不弱化既有檢查：SPEC §C 六個既有測試檔斷言零刪減；DOCROT Task 1.1–1.6、1.8 保留。
- 測試逐檔明列路徑，禁 glob、禁無路徑 `pytest`；治理全套為小時級，只在收票前丟背景跑一次。
- 實作者＝主委；每批完成後兩家審碼（`scripts/governance_families.json` 之 `active_stampers`），blocked 項由原提出方 CLOSED 後才進下一批。
- 防假綠：每道新判定附 SPEC §V mutation 並實跑改壞轉紅後還原。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| D2A | Task 1.1、1.2、1.3 | 無 | 登記層與狀態切換同屬 `scripts/fact_keys.json`／新登記檔，拆開即出現雙權威中間態 | 中 |
| D2B | Task 2.1、2.2、2.3、2.4、2.5 | D2A | 同一入口 `scripts/live_doc_write_guard.sh` 與同一次 `.claude/settings.json` 掛載；交接檔遷移須與掛載同 commit | 大 |
| D2C | Task 3.1、3.2 | D2B | 擋下事件由 D2B 之守衛產出，同批一次完成 | 中 |
| D2D | Task 4.1 | D2A、D2B、D2C | 遷移須在規則全部上線後一次完成 | 中 |

- 批次狀態：Task 1.2 落地後由 `scripts/fact_keys.json` 生成至本節，本表不手寫狀態。

<!-- BEGIN GENERATED: docrot2-batch-status -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 010 | D2A | 已完成 | docs/DOCROT2_TODO.md §B | — |
| 020 | D2B | 進行中 | docs/DOCROT2_TODO.md §B | 寫入別名三判準並集已修補（第四輪一條）→ 兩家第五輪閉合 → 收批進 D2C |
| 030 | D2C | 未開工 | docs/DOCROT2_TODO.md §B | D2B 審碼閉合後開工 Task 3.1–3.2 |
| 040 | D2D | 未開工 | docs/DOCROT2_TODO.md §B | D2C 審碼閉合後開工 Task 4.1 |
<!-- END GENERATED: docrot2-batch-status -->
- 批次間 Gate：前批審碼輪兩家 `VERDICT: proceed` 或 blocked 項已由原提出方 CLOSED；`bash scripts/gen_fact_key_blocks.sh --check` rc=0；該批測試檔逐檔 `venv/bin/python -m pytest <檔> -q` 0 failed。

## Phase 1 — 登記與狀態切換（完成後：活文件類別封閉；SPLITUNIFY 與本票狀態只存於 JSON 並已投影）

### Task 1.1 — 活文件類別登記（`票 B-63`）
- SPEC ref：§P Task 1.1　目標：封閉登記活文件、類別與規則，清冊可由命令重建。
- 輸入 / 輸出：輸入全樹 `.md` 清冊；輸出 `scripts/live_doc_registry.json`、`scripts/live_doc_registry_check.sh`。
- 實作要點：
  1. 類別集合（寫入 JSON，封閉）：`LIVE-HANDOFF`、`LIVE-CONTRACT`、`LIVE-SPEC`、`LIVE-PLAIN`、`LIVE-GUIDE`、`LOG`、`HIST`、`OTHER-DORMANT`。
  2. 路徑對照初始值（exact 或 `/` 結尾 prefix）：`LIVE-HANDOFF`＝`HANDOFF.md`；`LIVE-CONTRACT`＝`CLAUDE.md`、`AGENTS.md`、`docs/MULTI_AGENT_ORCHESTRATION.md`、`docs/SCAR_LEDGER.md`、`docs/ROADMAP.md`、`docs/GOV_ENFORCEMENT_REGISTRY.md`、`docs/GOV_TICKET_SOT.md`、`docs/GOVERNANCE_EXECUTION_ORDER.md`、`templates/`；`LIVE-SPEC`＝要點 7 探索函式所得、`docs/` 頂層（路徑恰兩段）且檔名含 `SPEC`、`TODO` 或 `PLAN` 之每一路徑（逐條 exact；HIST prefix 先套，故 `docs/Archived/` 不入）；`LIVE-PLAIN`＝`白話說明/`；`LOG`＝`白話說明/治理進度日誌.md`、`白話說明/流程摩擦記錄.md`、`docs/HANDOFF_ARCHIVE.md`；`LIVE-GUIDE`＝`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT_GUIDE.md`、`docs/API_SPECIFICATION.md`、`docs/PRODUCT_VISION.md`；`HIST`＝`docs/Archived/`、`白話說明/Archived/`、`docs/site/`；`OTHER-DORMANT`＝要點 7 探索函式所得範圍內（`docs/`、`白話說明/`、`templates/` 全部層級與 repo 根目錄 `.md`）未落入上列任一類之每一路徑（逐條 exact，含巢狀路徑如 `docs/reviews/` 下各檔）。exact 優先於 prefix（`LOG` 之 exact 覆蓋 `LIVE-PLAIN` 之 prefix）；同優先級命中兩類即錯。
  3. 各類規則旗標：`new_line_status_check`＝LIVE-*、OTHER-DORMANT 為 true，LOG、HIST 為 false；`archaeology_check`＝LIVE-*、OTHER-DORMANT 為 true，LOG、HIST 為 false；`concept_removal_xref`＝僅 LIVE-SPEC 為 true；`handoff_grammar`＝僅 LIVE-HANDOFF 為 true。
  4. 考古字面集合初始值：`保留供追溯`、`原寫`、`SUPERSEDED`、`作廢`、`以下為關閉前之敘述`（`~~` 另判，不入集合）。歷史專區指標文法初始值（正則）：`^- [0-9]{4}-[0-9]{2}-[0-9]{2}：(v[0-9]+|[A-Za-z0-9._-]+) → (\`[^\`]+\`|commit \`[0-9a-f]{7,40}\`)$`。
  5. 交接檔：H1 限一行、H2 區段封閉集合＝`## 現況`、`## 待辦`、`## 坑`、`## 進行中紀錄`；`## 現況`、`## 待辦` 只准生成區塊；`## 進行中紀錄` 內為 `HISTORY-BEGIN..END`，條目標記文法＝`<!-- ENTRY: <ID>(,<ID>)* -->`；完成條目移出目的地＝`docs/HANDOFF_ARCHIVE.md`；交接投影：來源 key＝`docrot2-batch-status`、`splitunify-batch-status`、`splitunify-residual-status`、`handoff-pending`；投影欄位＝`識別碼`、`狀態`、`權威路徑`、`下一步`；`## 現況`＝狀態 ∈ {`進行中`、`部分完成`} 之列；`## 待辦`＝狀態 ∈ {`未開工`、`進行中`、`部分完成`、`待審`、`停手`、`狀態未確認`} 之列（寫入 JSON 時逐值列出）；投影列「下一步」為空 ⇒ 生成與 `--check` rc!=0。
  6. `live_doc_registry_check.sh`：`--path <p>`、`--all`、`--staged` 三模式皆呼叫要點 7 之探索函式；未命中、同優先級命中兩類、`_schema.status_scope` 項不在登記 ⇒ rc=1；symlink、非 regular file ⇒ rc=1。
  7. 單一探索函式 `discover_live_docs`：`git ls-files --cached --others --exclude-standard -z`、`LC_ALL=C` 排序、NUL-safe；範圍＝`docs/`、`白話說明/`、`templates/` 全部層級與 repo 根目錄之 `.md`（此四個範圍根以外之 `.md` 一律不登記亦不擋）；先套 HIST prefix，其餘依要點 2 分類。
  8. `scripts/live_doc_registry_update.sh --add <path> [--class <類別>]`：未給類別時以要點 2 之分類述詞判定；寫入後依類別、路徑排序輸出 JSON；同路徑已登記 ⇒ rc=1；新增規格或施工清單檔之唯一登記入口。
- 修改檔案：新建 `scripts/live_doc_registry.json`、`scripts/live_doc_registry_check.sh::main`、`::discover_live_docs`、`scripts/live_doc_registry_update.sh::main`　既有 caller：新建無。
- 路徑：
  - scripts/live_doc_registry.json
  - scripts/live_doc_registry_check.sh
  - scripts/live_doc_registry_update.sh
  - docs/HANDOFF_ARCHIVE.md
  - tests/governance/test_docrot2_registry.py
  - tests/governance/fixtures/docrot2/
- 不可做：不得 glob 登記；不得登記 `handoffs/`；不得改 hook 掛載。
- 邊界：①含換行之路徑正確判定不切碎；②`docs/Archived/x.md` ⇒ HIST、rc=0；③`白話說明/治理進度日誌.md` ⇒ LOG（exact 優先）。
- 風險緩解：⊘
- 驗證：fixture `unregistered`、`path_in_two_classes`、`excluded_site_listed_as_live`、`one_registered_path_removed`、`archived_spec_listed_as_live_spec`、`nested_doc_unclassified`、`templates_live_doc_unregistered` 各 rc=1，`current_tree`、`new_top_level_spec`（`live_doc_registry_update.sh --add`）rc=0；`venv/bin/python -m pytest tests/governance/test_docrot2_registry.py -q` 0 failed。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 1.2 — 狀態遷入 `scripts/fact_keys.json` 並即時切換（`票 B-63`）
- SPEC ref：§P Task 1.2　目標：SPLITUNIFY 批次／Task／殘留與本票狀態只存於 JSON，施工清單同 commit 改為生成區塊。
- 輸入 / 輸出：輸入 `docs/SPLITUNIFY_TODO.md` §B、§C-9 Task 標題、§E 現行字面；輸出新 status key、切換後之施工清單、`B-63` 票列、`白話說明/DOCROT2施工進度.md`。
- 實作要點：
  1. 一次性遷移對照（只用於本次換算）：§B 狀態欄「✅ 完成」或「✅ **完成**（附註）」→ `已完成`（附註移入同列「合併理由」欄後段或刪除，由 git 保留）；§C-9 Task 標題含「✅ **已完成」→ `已完成`；§E 識別碼欄含刪除線且含「已關閉」→ `已完成`；§E 理由類別欄含「已關閉」且含「剩餘之半」→ `部分完成`；§E 識別碼欄無刪除線且理由類別欄 ∈ {`blocked-by`、`user-ruling`、`needs-research`} → `未開工`；§E「（原文，保留供對照）」列不登記，整列刪除並於 §E 下方歷史專區加一行指標（`- 2026-09-15：SU-RESID-3 → commit \`<切換前 HEAD 之 sha 前 8 碼>\``；主詞為單一識別碼，符合 Task 2.2 文法）。對照未涵蓋之字面 ⇒ 換算 fixture rc!=0。
  2. 新 key：`splitunify-batch-status`（B1…B9F）、`splitunify-task-status`（§C-9 之 Task 9.1、9.2、9.2a、9.2b、9.3、9.4、9.5）、`splitunify-residual-status`（§E 各識別碼）、`docrot2-batch-status`（D2A–D2D，初值 `未開工`）、`handoff-pending`（使用者待決事項，初值一列：白話說明整理）；各 key `columns` 第 2 欄為識別碼，並含 `權威路徑`、`下一步` 兩欄（未完成列之「下一步」不得為空）；`_schema.status_keys` 追加五個 key。
  3. `governance-ticket-sot` rows 追加 `B-63`（狀態 `部分完成`，狀態依據以「還缺：」起頭）；backlog 追加 `## B-63`。
  4. 施工清單刪除 §B 狀態欄、§C-9 Task 標題中之狀態字面、§E 識別碼欄與理由類別欄之狀態字面，改插合法生成區塊；`bash scripts/gen_fact_key_blocks.sh --write`。
  5. 新建 `白話說明/DOCROT2施工進度.md`，狀態只以生成區塊呈現。
- 修改檔案：`scripts/fact_keys.json`（新 key、`_schema.status_keys`、`governance-ticket-sot`）；`docs/SPLITUNIFY_TODO.md`（§B 表、§C-9 標題、§E 表）；`docs/DOCROT2_TODO.md`（§B 生成區塊）；`handoffs/20260801-GOV-AMEND-BACKLOG.md`　既有 caller：`scripts/gen_fact_key_blocks.sh`、`scripts/ticket_universe.sh`、`scripts/factkey_write_guard.sh`（不改）。
- 路徑：
  - scripts/fact_keys.json
  - docs/SPLITUNIFY_TODO.md
  - docs/DOCROT2_TODO.md
  - docs/GOV_TICKET_SOT.md
  - handoffs/20260801-GOV-AMEND-BACKLOG.md
  - 白話說明/DOCROT2施工進度.md
  - tests/governance/test_docrot2_registry.py
- 不可做：不得擴充 `status_enum`；不得保留手寫狀態欄；不得動 `docs/SPLITUNIFY_SPEC.D-002.md`；不得改 `scripts/plain_docs_sync_check.sh::_watched`（catch-all 改動屬 Task 2.5）。
- 邊界：①`B9` 與 `B9A` token 邊界各一 fixture；②同一識別碼出現於兩個 key ⇒ `--check` rc!=0；③完成批次之值不屬 `enforcement_completed_statuses` ⇒ `--check` rc!=0。
- 風險緩解：遷移前以 `awk` 輸出 §B、§E 原字面清單存 receipt，遷移後逐 ID 與 rows 對讀。
- 驗證：fixture `splitunify_status_cutover` rc=0、`completed_batch_row_value_outside_completed_set` rc!=0、`same_id_in_two_status_keys` rc!=0；`bash scripts/ticket_universe.sh --check` rc=0；`bash scripts/gen_fact_key_blocks.sh --check` rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 1.3 — 委員組成投影讀機器權威（`票 B-63`）
- SPEC ref：§P Task 1.3　目標：委員組成投影不複製值。
- 輸入 / 輸出：輸入 `scripts/governance_families.json`；輸出來源欄位支援與 `committee-roster` key。
- 實作要點：
  1. `_schema.fields` 新增 `rows_source`：物件，鍵 `file`（repo 相對 JSON 路徑）、`path`（字串陣列，逐層物件鍵）。
  2. 讀取：值須為字串陣列；每元素產出 `[三位零補序號, 元素]`；`LC_ALL=C`；同 key 同時有 `rows` 與 `rows_source`、`file` 含 `..` 或為絕對路徑、路徑不存在、值非字串陣列 ⇒ rc!=0。
  3. 新增 `committee-roster` key：`rows_source`＝`{file: "scripts/governance_families.json", path: ["active_stampers"]}`。
  4. `_schema.fields` 新增 `rows_filter`：`{source_keys: key 陣列, status_column: 欄名, allow: 狀態值陣列}`；取各來源 key 狀態欄 ∈ `allow` 之列，依 `source_keys` 順序與 rows 原順序串接；來源 key 或欄名不存在、`allow` 含 `status_enum` 以外之值、與 `rows`／`rows_source` 並存 ⇒ rc!=0。
  5. 交接投影之 `handoff-current`、`handoff-todo` 兩個 key 於 Task 2.4 建立（target＝`HANDOFF.md`）；本 Task 只以 fixture 驗 `rows_filter`。
- 修改檔案：`scripts/gen_fact_key_blocks.sh`（rows 讀取函式）、`scripts/fact_keys.json::_schema.fields`、`scripts/fact_keys.json::committee-roster`　既有 caller：`--check`／`--write` 全路徑。
- 路徑：
  - scripts/gen_fact_key_blocks.sh
  - scripts/fact_keys.json
  - tests/governance/test_docrot2_registry.py
  - tests/governance/test_govb1_factkey_gen.py
- 不可做：不得執行 shell 或任意查詢式；不得讀 repo 外檔。
- 邊界：①空陣列 ⇒ 零列、rc=0；②陣列含數字 ⇒ rc!=0。
- 風險緩解：`tests/governance/test_govb1_factkey_gen.py` 全檔 0 failed。
- 驗證：fixture `rows_source_string_array` rc=0、`rows_source_changed_without_write` rc!=0、`rows_source_value_is_object` rc!=0、`rows_source_absolute_path` rc!=0、`rows_filter_selects_open_rows` rc=0、`rows_filter_unknown_status_value` rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 1 測試 + Phase Gate
- `tests/governance/test_docrot2_registry.py`；回歸 `tests/governance/test_govb1_factkey_gen.py`、`test_factkey_write_guard.py`、`test_govb1_factkey_hook.py`。
- Gate：四檔逐檔 0 failed；mutation ③ 實跑轉紅後還原；D2A 審碼輪兩家閉合。

## Phase 2 — 產出端擋（完成後：寫入前擋手寫狀態與舊版字面、交接檔封閉文法、pre-commit 兜底）

### Task 2.1 — 寫入前手寫狀態偵測（`票 B-63`）
- SPEC ref：§P Task 2.1　目標：非權威活文件新增行之「識別碼＋狀態值」寫入前擋。
- 輸入 / 輸出：輸入 PreToolUse payload；輸出 exit 0／2。
- 實作要點：
  1. 新建 `scripts/live_doc_write_guard.sh`；目標非登記活文件或類別旗標 `new_line_status_check`＝false ⇒ exit 0。
  2. 重建寫入後全文：Edit＝`replace_all` 為 true 時磁碟舊檔之全部 `old_string` 取代為 `new_string`；否則 `old_string` 須恰出現一次再取代為 `new_string`，出現 0 次或 2 次以上 ⇒ exit 2。Write＝`content`。
  3. 新增行＝`diff` 舊檔與寫入後全文之 `+` 行，行號以寫入後全文計；以寫入後全文掃描合法生成區塊、`HISTORY-BEGIN..END`、fenced code block 範圍，範圍內新增行豁免。
  4. 判定：自 `scripts/gen_fact_key_blocks.sh` 抽出共用入口（例 `_fk_status_hits_in_lines <rel> <lines-file>`），既有 `_fk_reject_handwritten_status` 改呼叫同一入口；不設引號豁免、不設樣本句豁免（具名偏離 consult-r2 裁定 2）；過時樣本須置於 fenced code block。
- 修改檔案：新建 `scripts/live_doc_write_guard.sh::main`、`::rebuild_after_state`、`::added_lines`；`scripts/gen_fact_key_blocks.sh::_fk_status_hits_in_lines`（新增）、`::_fk_reject_handwritten_status`（改呼叫共用入口，行為不變）　既有 caller：`scripts/factkey_write_guard.sh`、`scripts/gov_check.sh` 段 3。
- 路徑：
  - scripts/live_doc_write_guard.sh
  - scripts/gen_fact_key_blocks.sh
  - tests/governance/test_docrot2_write_guard.py
  - tests/governance/fixtures/docrot2/
- 不可做：不得掃整檔既有行；不得以寫檔後鉤子宣稱已擋。
- 邊界：①同一 `new_string`、`old_string` 位於歷史專區內外各一；②`replace_all` true 兩處；③Write 內容與磁碟相同 ⇒ exit 0。
- 風險緩解：`tests/governance/test_govb1_factkey_gen.py` 全檔 0 failed（共用入口抽出之回歸）。
- 驗證：fixture `handoff_edit_adds_id_with_status` exit 2、`same_new_string_old_string_inside_history` exit 0、`same_new_string_old_string_outside_history` exit 2、`replace_all_true_two_occurrences` exit 2、`quoted_id_with_status` exit 2、`git_show_decoy_status_suffix` exit 2、`stale_sample_in_fence` exit 0、`edit_old_string_absent` exit 2、`edit_old_string_nonunique` exit 2。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 2.2 — 新增行禁舊版字面；歷史專區只准指標（`票 B-63`）
- SPEC ref：§P Task 2.2　目標：活文件只承載現行態。
- 輸入 / 輸出：同 Task 2.1 入口之第二道判定。
- 實作要點：
  1. 類別旗標 `archaeology_check`＝true 者：歷史專區外新增行含 `~~`、考古字面集合任一、或 canonical finding ID（形狀同 `scripts/_synth_attr.py` 之 `ID_RE`，去除行首 `## ` 之錨定）⇒ exit 2。
  2. 歷史專區內新增行須全行符合登記之指標文法：主詞為單一 token 且為 `v[0-9]+` 形式或登記之狀態識別碼；目標為反引號包住且工作樹存在之 repo 相對路徑（含 git 排除之 `handoffs/`），或 `commit` 加反引號包住之 7–40 位十六進位且 `git cat-file -e <sha>^{commit}` 成立；任一不合 ⇒ exit 2。目標存在性只判本次新增行，既有歷史行不重驗。
  3. 刪除行不判。
- 修改檔案：`scripts/live_doc_write_guard.sh::check_archaeology`、`::check_history_pointer`　既有 caller：無。
- 路徑：
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry.json
  - tests/governance/test_docrot2_write_guard.py
- 不可做：不得要求既有刪除線清零；不得擴及 `handoffs/`。
- 邊界：①LOG 類 ⇒ exit 0；②正文整段刪除 ⇒ exit 0。
- 風險緩解：⊘
- 驗證：fixture `spec_adds_strikethrough_outside_history` exit 2、`spec_adds_finding_id_outside_history` exit 2、`spec_history_adds_pointer_line` exit 0、`spec_history_adds_copied_old_text` exit 2、`history_pointer_free_text_subject` exit 2、`history_pointer_target_missing` exit 2、`existing_history_pointer_target_absent_unrelated_edit`（`--staged`）rc=0、`todo_unrelated_edit_legacy_strikethrough_elsewhere` exit 0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 2.3 — pre-commit 兜底、未登記路徑、樹狀態重放（`票 B-63`）
- SPEC ref：§P Task 2.3　目標：非 Edit／Write 寫入於 commit 時擋；可對 commit 重放交接檔判定。
- 輸入 / 輸出：輸入 index 與 `HEAD`；輸出 rc。
- 實作要點：
  1. `live_doc_write_guard.sh --staged`：`git diff --cached --name-status -z` 取暫存登記活文件；舊檔＝`git show HEAD:<p>`（新檔為空）、寫入後全文＝`git show :<p>`；套 Task 2.1、2.2 與 Task 2.4 全文判定；`D` 不判、`R` 以新路徑、二進位略過。
  2. `live_doc_write_guard.sh --tree <commit> --path <p>`：寫入後全文＝`git show <commit>:<p>`，只執行 Task 2.4 全文判定。
  3. `live_doc_registry_check.sh --staged`：暫存之新增 `.md` 未登記 ⇒ rc=1。
  4. `scripts/git_hooks/pre-commit` 呼叫兩支 `--staged`，任一非零中止。
- 修改檔案：`scripts/git_hooks/pre-commit`、`scripts/live_doc_write_guard.sh::staged_mode`、`::tree_mode`、`scripts/live_doc_registry_check.sh::staged_mode`　既有 caller：pre-commit 既有段。
- 路徑：
  - scripts/git_hooks/pre-commit
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry_check.sh
  - tests/governance/test_docrot2_write_guard.py
- 不可做：不得提供略過旗標；不得在 pre-push 重複。
- 邊界：①index 與工作樹不同 ⇒ 以 index 判；②重新命名至未登記路徑 ⇒ rc=1。
- 風險緩解：⊘
- 驗證：fixture `bash_redirect_added_status_line_staged` rc!=0、`clean_staged_diff` rc=0、`new_unregistered_md_staged` rc!=0、`handoff_tree_with_completed_entry`（`--tree HEAD --path HANDOFF.md`）rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 2.4 — 交接檔封閉文法與流水帳生命週期（`票 B-63`）
- SPEC ref：§P Task 2.4　目標：交接檔只含生成之現況與待辦、手寫教訓、進行中工作之紀錄。
- 輸入 / 輸出：輸入交接檔寫入後全文（寫入前）或 index／commit 版（`--staged`／`--tree`）；輸出 rc。
- 實作要點：
  1. 內容型（寫入前與 `--staged` 皆判）：H2 不屬封閉集合、`## 現況`／`## 待辦` 有生成區塊外之非空行或未恰含對應投影 key（`handoff-current`／`handoff-todo`）之生成區塊、生成區塊內任一列「下一步」為空、進行中紀錄區首個條目標記前有非空行、標記不合文法或含未登記識別碼 ⇒ 違規。
  2. 一致性型（僅 `--staged`／`--tree`）：任一條目所含識別碼之狀態（讀 `scripts/fact_keys.json` rows）∈ `enforcement_completed_statuses` ⇒ 違規。
  3. 一則＝自標記行至下一標記或 `HISTORY-END` 前一行。
  4. `governance-enforcement` 登記第 2 點為一致性型並寫理由（須跨檔讀狀態）。
  5. 遷移（與 Task 2.5 掛載同一 commit）：建立 `handoff-current`、`handoff-todo` 兩個投影 key（`target`＝`HANDOFF.md`，`rows_filter` 依 Task 1.1 要點 5）；`HANDOFF.md` 改為本文法：現況與待辦插生成區塊；現行主線之紀錄以 `<!-- ENTRY: B-63 -->` 等標記置於進行中紀錄區；已完成工作之紀錄整段移至 `docs/HANDOFF_ARCHIVE.md`。
  6. 掛載先於遷移會使交接檔任何編輯皆因文法不合被擋，故兩者不得分 commit。
- 修改檔案：`scripts/live_doc_write_guard.sh::check_handoff_grammar`、`::check_handoff_lifecycle`、`HANDOFF.md`、`docs/HANDOFF_ARCHIVE.md`、`scripts/fact_keys.json`（`handoff-current`、`handoff-todo`）　既有 caller：`scripts/inject_handoff.sh`（不改）。
- 路徑：
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry.json
  - tests/governance/test_docrot2_write_guard.py
  - HANDOFF.md
  - docs/HANDOFF_ARCHIVE.md
  - scripts/fact_keys.json
- 不可做：不得以行數判定；不得刪除進行中紀錄而不移至 `docs/HANDOFF_ARCHIVE.md`。
- 邊界：①同一 commit 狀態轉完成且條目已移出 ⇒ rc=0；②一則兩識別碼一完成 ⇒ 違規；③「坑」引用已結束工作 ⇒ 不判生命週期；④遷移後 `scripts/inject_handoff.sh` 注入內容含生成區塊（對讀）。
- 風險緩解：⊘
- 驗證：fixture `handoff_current_section_handwritten_line` exit 2、`handoff_unknown_h2_section` exit 2、`handoff_todo_row_missing_next_action` exit 2、`handoff_todo_contains_completed_row`（`gen_fact_key_blocks.sh --check`）rc!=0、`handoff_current_missing_open_batch`（`gen_fact_key_blocks.sh --check`）rc!=0、`handoff_history_line_before_first_marker` exit 2、`handoff_entry_any_id_completed`（`--staged`）rc!=0、`handoff_entry_all_ids_open`（`--staged`）rc=0、`efcafc63_handoff_status_lines_in_current_section`（`--staged`）rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無（交接檔遷移在本 Task 內完成）。

### Task 2.5 — 既有檢查依類別適用、宣稱與規則同步、掛載（`票 B-63`）
- SPEC ref：§P Task 2.5　目標：消除已知摩擦與互斥規則，掛上 Task 2.1–2.4。
- 輸入 / 輸出：輸入各既有檔；輸出最小改動與 PreToolUse 掛載。
- 實作要點：
  1. `scripts/spec_xref_hook.sh`：「概念被拿掉」只對 `concept_removal_xref`＝true 之類別執行；未登記路徑行為不變。
  2. `scripts/plain_docs_sync_check.sh`：catch-all 改查登記，未登記 rc!=0。
  3. `CLAUDE.md:16` 與 `.claude/settings.json` PreCompact 之 auto、manual 兩則訊息刪除 HANDOFF 行數上限，改為指向 Task 2.4 文法之指標句。
  4. `governance-enforcement` 追加 DOCROT Task 1.1–1.8 與本票各閘之掛載點；DOCROT Task 1.3 宣稱改為只擋「共 N 條」雙落點、不涵蓋交接檔。
  5. `.claude/settings.json` PreToolUse `Edit|Write` 掛 `bash scripts/live_doc_write_guard.sh`，與本 Task 同一 commit。
- 修改檔案：`scripts/spec_xref_hook.sh::main`、`scripts/plain_docs_sync_check.sh::_watched`、`CLAUDE.md`、`.claude/settings.json`（hooks.PreToolUse、hooks.PreCompact）、`scripts/fact_keys.json::governance-enforcement`　既有 caller：各檔既有測試。
- 路徑：
  - scripts/spec_xref_hook.sh
  - scripts/plain_docs_sync_check.sh
  - CLAUDE.md
  - .claude/settings.json
  - scripts/fact_keys.json
  - tests/governance/test_docrot2_class_routing.py
- 不可做：不得改變 LIVE-SPEC 之 xref 判定寬嚴；不得刪除 DOCROT Task 1.1–1.3 掃描器。
- 邊界：①未登記路徑之 `spec_xref_hook.sh` 行為不變；②新列掛載點不存在 ⇒ `--check` rc!=0。
- 風險緩解：改動後 `jq empty .claude/settings.json` rc=0。
- 驗證：fixture `handoff_remove_current_lines_history_keeps_concept` rc=0、`spec_remove_concept_live_reference_remains` rc=2、`new_unregistered_plain_doc` rc!=0；`test "$(grep -c '30 行' CLAUDE.md)" -eq 0 && test "$(grep -c '30 行' .claude/settings.json)" -eq 0` rc=0（`grep -c` 零命中時自身 rc=1，故以輸出值判定）；`bash scripts/gen_fact_key_blocks.sh --check` rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 2 測試 + Phase Gate
- `tests/governance/test_docrot2_write_guard.py`、`tests/governance/test_docrot2_class_routing.py`；回歸 SPEC §C 六檔與 `spec_xref`、`plain_docs_sync` 既有測試檔（逐檔明列於審碼 brief）。
- Gate：mutation ①②⑥⑦⑧ 實跑轉紅後還原；D2B 審碼輪兩家閉合。

## Phase 3 — 量測（完成後：類別雙填、收案量測事件、擋下事件、報表可跑）

### Task 3.1 — finding 類別欄雙填與適用門檻（`票 B-63`）
- SPEC ref：§P Task 3.1　目標：每條 finding 有可機械計算之類別，只對門檻後開債之輪次生效。
- 輸入 / 輸出：輸入委員交件、收斂檔、audit；輸出 `completeness_check.sh --single` 與 `_synth_attr.py --mode gate` 之 rc（0／1）。
- 實作要點：
  1. `scripts/governance_verdicts.json` 新鍵 `finding_category_values`＝`code-contract`、`doc-sync`、`format-reject`、`other`；新鍵 `category_required_after_audit_sequence`＝本 Task 落地 commit 前一刻 `.claude/gate/audit.log` 之最大 `sequence`（寫入值並附於 commit 訊息）。
  2. 兩份範本 finding 格式新增 `**類別**: <值>` 一行（與標籤同行）。
  3. `completeness_check.sh --single` 新增 `--round-id <rid>`：讀該 round 之 `committee_round_open` 事件序號；大於門檻或未給 `--round-id` ⇒ 每條 finding（含零 findings sentinel）須有合法類別，否則 rc=1。`scripts/cx_run.sh` 四個 `--single` 呼叫面（`--selfcheck`、review／consult／closure 收件、stamp 收件、格式失敗重跑）皆帶同一 `--round-id`；`--selfcheck` 新增 `--round-id` 參數，未給則照前述 fail-closed。
  4. `scripts/_synth_attr.py` 新增 `check_category`：門檻後之收斂檔群集表第 5 欄為主委類別（封閉值）；委員欄與主委欄不一致之 finding 須列於「類別不一致」段且附處置 token，否則錯。
- 修改檔案：`scripts/governance_verdicts.json`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`、`scripts/completeness_check.sh::_validate_finding_body`、`scripts/_synth_attr.py::check_category`、`scripts/cx_run.sh`（四個 `--single` 呼叫面與 `--selfcheck` 參數解析）　既有 caller：`scripts/synth_attribution_hook.sh`、`scripts/reconcile_cluster_attribution_check.sh`、`scripts/debt_clear.sh`。
- 路徑：
  - scripts/governance_verdicts.json
  - templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
  - templates/COMMITTEE_FINDING_TEMPLATE.md
  - scripts/completeness_check.sh
  - scripts/_synth_attr.py
  - scripts/cx_run.sh
  - tests/governance/test_docrot2_metrics.py
- 不可做：不得以日期、mtime 判定適用；不得讓主委欄作分子。
- 邊界：①同一交件 bytes 以門檻前、後兩個 round id 送入 ⇒ rc 0／1；②群集表無第 5 欄之門檻前舊收斂檔 ⇒ 不判。
- 風險緩解：`tests/governance/test_docrot_e3_brief_placeholder.py` 與既有 completeness、synth_attr 測試逐檔 0 failed。
- 驗證：fixture `round_after_threshold_p1_without_category` rc=1、`round_before_threshold_p1_without_category` rc=0、`no_round_id_p1_without_category` rc=1、`category_outside_set` rc=1、`category_mismatch_unlisted` rc=1、`category_mismatch_listed_with_disposition` rc=0；`scripts/cx_run.sh` 四呼叫面逐一以門檻前 round 之無類別交件驗 rc=0、門檻後驗 rc=1。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 3.2 — 量測契約、收案事件、擋下事件（`票 B-63`）
- SPEC ref：§P Task 3.2　目標：成效由機器逐輪記錄與計算。
- 輸入 / 輸出：輸入收斂檔、交件、守衛擋下；輸出 audit 事件、`scripts/docrot2_metrics.sh` 報表 rc。
- 實作要點：
  1. 新建 `scripts/docrot2_metric_contract.json`，鍵：`ticket_key`（task-id 前兩段 `<YYYYMMDD>-<EPIC>`）、`cohort`（首個「其第一個 `brief_kind=review` 之 `committee_round_open` 序號大於 `closure_sequence`」之票，取該票 `brief_kind=review` 之前兩輪，依 `committee_round_open` 序號）、`finding_scope`（canonical finding，排除 `-P3-00`）、`numerator`（委員類別＝`doc-sync`）、`denominator`（範圍內 canonical 數）、`zero_denominator`（占比 0）、`comparator`（第二輪 ≤ 第一輪）、`max_findings_per_round`（20）、`handoff_replay`（兩輪收案 commit 各跑 `bash scripts/live_doc_write_guard.sh --tree <commit> --path HANDOFF.md` 須 rc=0）、`history_only_restamp`（範圍票內每個 stamp 輪，以 `scripts/reconcile_body_hash.sh` 之本體區間——`## 戳記` 之前——比對被戳記檔前後兩次戳記之本體，差異行全落在 `HISTORY-BEGIN..END` 內者計 1，須為 0）、`closure_sequence`（本票收票時寫入）。
  2. `scripts/audit_events.json` 之 fields 與 `required_fields_per_event` 同步登記 `docrot2_round_metric`（`round_id`、`task_id`、`session_name`、`round_open_sequence`、`brief_kind`、`canonical_count`、各類別計數、`mismatch_count`、`handoff_tree_commit`、各家 `model` 與 `reasoning_effort`〔取不到記 `unavailable`〕；stamp 輪另含 `stamp_target`、`body_sha_before`、`body_sha_after`、`history_only`）與 `docrot2_gate_block`（`rule_id`、`path`、`class`）；`committee_round_open` 之 `brief_kind` 列入必填（只約束門檻後之新事件）。
  3. `scripts/debt_clear.sh` 收案前寫 `docrot2_round_metric`（僅門檻後之輪次）；缺欄或寫入失敗 rc!=0。兩支守衛擋下時寫 `docrot2_gate_block`，寫入失敗仍擋。
  4. `scripts/docrot2_metrics.sh`：只讀 audit 與契約；缺事件、重複事件、未知 cohort ⇒ rc=1；四條及格全過 ⇒ rc=0，任一不過 ⇒ rc=1。
- 修改檔案：新建 `scripts/docrot2_metric_contract.json`、`scripts/docrot2_metrics.sh::main`；`scripts/audit_events.json`；`scripts/debt_clear.sh::main`（收案前段）；`scripts/live_doc_write_guard.sh::emit_block_event`；`scripts/live_doc_registry_check.sh::emit_block_event`　既有 caller：`scripts/audit_append.sh`（不改）。
- 路徑：
  - scripts/docrot2_metric_contract.json
  - scripts/docrot2_metrics.sh
  - scripts/audit_events.json
  - scripts/debt_clear.sh
  - scripts/live_doc_write_guard.sh
  - scripts/live_doc_registry_check.sh
  - tests/governance/test_docrot2_metrics.py
- 不可做：不得以 `doc_friction_ratio` 字面作分子；不得寫入推定之委員型號；報表不得解析散文。
- 邊界：①兩輪文件同步類皆 0 ⇒ comparator 過；②只剩一輪事件 ⇒ rc=1。
- 風險緩解：`tests/governance/test_debt_emit.py` 既有紅基準不得增加，逐條對讀。
- 驗證：fixture `synth_without_category_counts` rc!=0、`valid_round` rc=0（audit 事件 `jq` 逐欄對讀）、`cohort_missing_second_round_event` rc=1、`both_rounds_zero_doc_sync` rc=0、`history_only_restamp_in_cohort` rc=1、`history_only_restamp_hidden_by_stamp_lines` rc=1、`cohort_round_open_missing_brief_kind` rc=1、`duplicate_round_metric_event` rc=1；擋下 fixture 後 audit 含 `docrot2_gate_block` 1 筆。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 3 測試 + Phase Gate
- `tests/governance/test_docrot2_metrics.py`；回歸 completeness、synth_attr、`test_debt_emit.py` 既有測試（逐檔明列於審碼 brief）。
- Gate：mutation ④⑤ 實跑轉紅後還原；D2C 審碼輪兩家閉合。

## Phase 4 — 遷移（完成後：現存活文件之手寫狀態全部遷移或具名留存；交接檔符合封閉文法）

### Task 4.1 — 由登記導出之全專案遷移（`票 B-63`）
- SPEC ref：§P Task 4.1　目標：命中之活文件要麼遷移、要麼具名留存。
- 輸入 / 輸出：輸入 Phase 1–3 產出與 `--migration` 命中清單；輸出遷移後之活文件、`scripts/docrot2_migration_residuals.json`。
- 實作要點：
  1. `live_doc_registry_check.sh --migration`：對 `new_line_status_check`＝true 之類別全檔執行共用判定入口；命中檔 ∉ 殘留清單 ⇒ rc=1；殘留清單列之檔已無命中 ⇒ rc=1（清單過期）。
  2. 殘留清單每列：`path`、`reason_class`（`blocked-by`／`user-ruling`／`needs-research`）、`owner`、`trigger`；初始列至少含 `docs/SPLITUNIFY_SPEC.D-002.md`（`DOCROT2-RESID-D002-STRUCTURAL-RED`）。
  3. 交接檔已於 Task 2.4 遷移，本 Task 不改其結構；以 `bash scripts/live_doc_write_guard.sh --tree HEAD --path HANDOFF.md` 確認 rc=0。
  4. `docs/ROADMAP.md` 與白話進度表之狀態格改生成區塊；其他命中檔逐檔遷移或列入殘留清單。
- 修改檔案：`docs/ROADMAP.md`、`白話說明/SPLITUNIFY施工進度.md`、`白話說明/接下來要做什麼.md`、`--migration` 命中之其他檔、`scripts/docrot2_migration_residuals.json`、`scripts/live_doc_registry_check.sh::migration_mode`　既有 caller：`scripts/inject_handoff.sh`、`scripts/plain_docs_render.sh`（不改）。
- 路徑：
  - docs/ROADMAP.md
  - 白話說明/SPLITUNIFY施工進度.md
  - 白話說明/接下來要做什麼.md
  - scripts/docrot2_migration_residuals.json
  - scripts/live_doc_registry_check.sh
  - tests/governance/test_docrot2_migration.py
- 不可做：不得改 `docs/SPLITUNIFY_SPEC.D-002.md`；不得修改任何檢查判定。
- 邊界：①殘留清單列之檔已無命中 ⇒ `--migration` rc=1；②遷移前後 SPLITUNIFY 殘留識別碼集合相同（逐 ID 對讀）。
- 風險緩解：遷移前後各跑 `bash scripts/gen_fact_key_blocks.sh --check` 與 `bash scripts/plain_docs_render.sh --check`。
- 驗證：fixture `hit_file_neither_migrated_nor_listed` rc=1、`current_tree_after_migration` rc=0；`bash scripts/live_doc_write_guard.sh --staged` rc=0；`bash scripts/plain_docs_render.sh --check` rc=0；`bash scripts/live_doc_registry_check.sh --all` rc=0；`venv/bin/python -m pytest tests/governance/test_docrot2_migration.py -q` 0 failed。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 4 測試 + Phase Gate
- 上列命令；收票前丟背景跑一次 `bash scripts/gov_check.sh --no-probe`，讀 pytest 自身 passed／failed 行。
- Gate：mutation ⑨ 實跑轉紅後還原；D2D 審碼輪兩家閉合；`scripts/docrot2_metric_contract.json` 之 `closure_sequence` 寫入收票當下序號。
