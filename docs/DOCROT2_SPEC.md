# DOCROT2 — 活文件狀態單一來源與新舊並存之產出端擋（修正 DOCROT）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260915-docrot2-x-consult-r1/synth.md`、`handoffs/reconcile/20260915-docrot2-x-consult-r2/synth.md`（兩輪兩家 consult＋主委獨立版）　|　日期：2026-09-15　|　對應 TODO：`docs/DOCROT2_TODO.md`

## §RISK 風險分級
- **大小**：大（全專案活文件、共用產出端 hook、多 Phase）。
- **命中高風險原則**：(b) 跨模組／共用路徑——`.claude/settings.json` hook 鏈、`scripts/fact_keys.json` 與其生成器、`scripts/completeness_check.sh`、`scripts/debt_clear.sh` 為所有票共用；(c) 多 Phase——登記、擋、量測、遷移四段，後段依賴前段。
- RISK-HIT: b,c
- 未命中 (a)(d)：不碰數值、特徵、ML、回測路徑 ⇒ §G 移 §N。

## §A 假設與待使用者確認
**已驗證事實**（2026-09-15 實跑）：
- FACT-RECEIPT: `jq -c '._schema | {status_enum, status_keys}' scripts/fact_keys.json` → 印出 `status_keys` 僅四個 `governance-*` key（主委 實跑 2026-09-15）⇒ 產品 epic 之批次／殘留／版本不在手寫狀態偵測範圍，此即 `git show efcafc63:HANDOFF.md` 之「b9 SPEC＝v31 待重簽」未被擋之原因。
- FACT-RECEIPT: `jq -c '._schema.status_scope' scripts/fact_keys.json` → 印出 `["HANDOFF.md","docs/GOVERNANCE_EXECUTION_ORDER.md","白話說明/"]`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 438,560p scripts/gen_fact_key_blocks.sh` → 印出 `_fk_reject_handwritten_status`：範圍檔內、合法生成區塊外，同一行同時含登記識別碼（token 邊界）與 `status_enum` 字面 ⇒ `FACTKEY HANDWRITTEN STATUS`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `grep -n factkey_write_guard .claude/settings.json` → 印出 `205:`（PostToolUse 鏈）（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 73,84p scripts/verify_pretooluse.sh` → 印出 Write 以磁碟舊檔對 `tool_input.content` 做 `diff -u` 取 `+` 行、Edit 取 `new_string`（主委 實跑 2026-09-15）⇒ 寫入前可取得新增行。
- FACT-RECEIPT: `git show efcafc63:HANDOFF.md | sed -n '258,270p'` → 印出現況「＝v31 待重簽」、下一步「`review-r39`」、「現行＝三家全員」（composer 實跑 2026-09-15，consult-r2 交件 TESTS_RUN）。
- FACT-RECEIPT: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=1、364 行（composer 實跑 2026-09-15，consult-r1）。
- FACT-RECEIPT: `grep -r doc_friction_ratio scripts/` → 無輸出（codex、composer 實跑 2026-09-15，consult-r1）⇒ DOCROT Task 1.7 無執行路徑。
- FACT-RECEIPT: `sed -n 118,123p scripts/plain_docs_sync_check.sh` → 印出 catch-all `*) echo ""`（codex 實跑 2026-09-15，consult-r2）⇒ 新增白話檔預設不受監看。
- FACT-RECEIPT: `grep -n '30 行' CLAUDE.md` → 印出 `16:`（主委 實跑 2026-09-15）；`.claude/settings.json` PreCompact 訊息含「保持 30 行以內」（主委 實跑 2026-09-15）。

**待使用者確認**：待確認：無

**已確認結果**：
- 2026-09-15 使用者：「持續不接受用紀律或記憶當解法，但允許擴建治理工具，就是要修正DOCROT沒做好之處，真正減少文檔問題和降低不必要的輪數，而且要全專案涵蓋，不是只有SPEC」
- 2026-09-15 使用者：「交接文件能交接清楚明確是最重要，所以不一定要限制行數，怕的只是把舊案或已完成或不必要的殘留在裡面」
- 2026-09-15 使用者：「針對修正優化DOCROT的方法，你跟委員討論共識決定，先做好DOCROT這部分」
- 2026-09-15 使用者：「現在就是Codex+Cursor(Grok)兩家委員，等Grok回來後我會再將Cursor切成Composer回到三家委員」

## §C 約束
- **產出端覆蓋鐵律**（`CLAUDE.md`）：每道新檢查掛寫檔當下；掛不上者登記於 `docs/GOV_ENFORCEMENT_REGISTRY.md`（經 `scripts/fact_keys.json` 之 `governance-enforcement` 生成），並寫明理由。
- **不接受紀律／記憶當解法**：任何「須記得做」之步驟一律改為機械閘或具名殘留。
- **面向未來**：既有行不回洗；新增行、新檔案、本票遷移之檔案才受新規則全量約束。`status_scope_grandfathered` 只准縮小。
- **單一真相源**：本票新增之封閉集合（文件類別、考古字面、finding 類別）一律定義於 JSON；本 SPEC 與 TODO 只 pointer，不在散文列舉值。狀態值之唯一來源沿用 `scripts/fact_keys.json`，不另立第二份值檔（consult-r2 `CODEX-R2-P1-01`）。
- **不弱化既有檢查**：DOCROT Task 1.1–1.6、1.8 保留；既有測試檔 `tests/governance/test_govb1_factkey_gen.py`、`test_factkey_write_guard.py`、`test_govb1_factkey_hook.py`、`test_docrot_f2_total_items_count.py`、`test_docrot_e3_brief_placeholder.py`、`test_docrot_claim_committee_backing.py` 之既有斷言不得放寬或刪除。
- **hook 成本**：沿用 `scripts/narrow_check_router.sh` 之成本模型——未命中路徑不得 fork 重檢查；寫入前檢查只對登記之活文件路徑執行。
- **自身故障**：寫入前檢查對「登記之活文件路徑」自身故障 fail-closed（exit 2）；非登記路徑一律放行。寫檔後回灌維持既有 fail-open 慣例，由 pre-commit 承接。
- 解耦 7 條：不涉 `momentum/`、`api/`、`frontend/`。

## §P Phase 與依賴

### Phase 1 — 登記（依賴：無）

**Task 1.1 — 活文件類別登記**
- 目標：封閉登記「哪些 `.md` 是活文件、屬哪一類、各類套哪些規則」。　檔案：新建 `scripts/live_doc_registry.json`（類別集合、路徑編碼、各類規則旗標、考古字面集合、排除路徑）；新建 `scripts/live_doc_registry_check.sh`（`--path <p>`／`--all`）。既有 caller：無（新建）。
- 改法：類別集合初值取 consult-r1 composer A1（LIVE-CONTRACT／LIVE-SPEC／LIVE-PLAIN／LIVE-GUIDE／HIST／OTHER-DORMANT），另加日誌類；路徑編碼沿用 `status_scope` 之兩種（exact、以 `/` 結尾之 directory prefix），禁 wildcard；`docs/`、`白話說明/`、repo 根目錄下之 `.md` 未命中任何登記且未命中排除路徑 ⇒ rc=1。`status_scope` 每一項須落在登記之類別內（一致性檢查，不重複定義）。
- **驗證**：`ASSERT bash scripts/live_doc_registry_check.sh --path docs/NEW_THING.md WHEN fixture=unregistered THEN rc=1`；`ASSERT bash scripts/live_doc_registry_check.sh --path HANDOFF.md WHEN fixture=registered THEN rc=0`；`ASSERT bash scripts/live_doc_registry_check.sh --all WHEN fixture=status_scope_outside_registry THEN rc=1`。
- **邊界**：①路徑含換行或為 symlink ⇒ rc=1（同 `_fk_scope_files` 之 NUL-safe 與 symlink 規則）；②排除路徑下之 `.md`（`docs/site/`、`Archived/`、`tests/`、`.claude/`）⇒ rc=0；③登記檔缺失或非 JSON ⇒ rc=1。
- **存活至**：全票完工後常設。
- **覆蓋風險**：Task 2.3 會把本檢查接進 pre-commit、Task 2.5 會把 `plain_docs_sync_check.sh` 之 catch-all 改讀本登記——兩者只消費、不改本檔 schema。
- 不可做：不得以 glob；不得把 `handoffs/` 登記為活文件；不得在本 Task 改動任何 hook 掛載。

**Task 1.2 — 狀態種類擴充，權威遷入 `scripts/fact_keys.json`**
- 目標：把產品 epic 之批次狀態、Task 狀態、殘留狀態納入既有手寫狀態偵測之識別碼集合，權威值只存於 `scripts/fact_keys.json` rows。　檔案：`scripts/fact_keys.json`（新增 status key 與 rows；`_schema.status_keys` 追加）。既有 caller：`scripts/gen_fact_key_blocks.sh`、`scripts/factkey_write_guard.sh`、`scripts/ticket_universe.sh`。
- 改法：每個新 key 以 `columns` 宣告欄名、`target` 指向投影宿主；識別碼仍取 rows 第 2 欄（沿用 `_fk_status_ids`）。種類＝consult-r2 裁定 D1：批次、Task、殘留、票（既有）；委員組成與規格版本之讀取見 Task 1.3。本 Task 只建立 SPLITUNIFY 之 rows（現行唯一進行中之產品 epic）；其餘 epic 於其下次改動時依 Task 2.1 之新增行規則自然受約束。
- **驗證**：`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=new_status_keys_registered THEN rc=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=status_key_row_without_target_block THEN rc!=0`；新增 key 之識別碼出現在 `_fk_status_ids` 輸出（逐 ID 對讀，不寫聚合數）。
- **邊界**：①同一識別碼出現在兩個 status key ⇒ rc!=0（重複權威）；②識別碼與既有 governance 識別碼 token 邊界碰撞（例如 `B9` 與 `B9A`）⇒ 以既有 `has_token` 邊界判定，fixture 各一；③`status_enum` 不新增同義字面，新 key 之狀態值須 ∈ 既有 `status_enum`，否則 rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：Task 4.1 會把 `docs/SPLITUNIFY_TODO.md` §B／§E 之狀態欄改為本 Task 之投影區塊——那是消費本 Task，不覆蓋。
- 不可做：不得在 `docs/SPLITUNIFY_TODO.md` 或任何 md 保留第二份手寫狀態值作權威；不得擴充 `status_enum` 以容納新同義詞。

**Task 1.3 — 生成器讀取機器權威（委員組成、規格版本）**
- 目標：投影之值可來自其他機器檔，不在 `scripts/fact_keys.json` 複製一份。　檔案：`scripts/gen_fact_key_blocks.sh`（新增 rows 來源欄位與決定性讀取）、`scripts/fact_keys.json` `_schema.fields`（該欄位定義唯一處）。既有 caller：同 Task 1.2。
- 改法：rows 來源欄位只接受 repo 相對 JSON 路徑＋`jq` 表達式之封閉形式；輸出須符合既有決定性契約（`LC_ALL=C`、LF、無時間戳）。委員組成讀 `scripts/governance_families.json` 之 `active_stampers`；規格版本讀各 SPEC 檔頭之機器行（格式由本 Task 定義於 `_schema.fields`），`HISTORY` 區內之版本字面不作權威。委員型號不納入（consult-r2 裁定 D1；權威不存在，見 §N）。
- **驗證**：`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_from_json_unchanged THEN rc=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_from_json_source_changed_without_write THEN rc!=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh WHEN fixture=rows_from_absolute_path THEN rc!=0`。
- **邊界**：①來源檔缺失或 `jq` 失敗 ⇒ rc!=0；②來源路徑含 `..` 或為絕對路徑 ⇒ rc!=0；③同一 key 同時宣告靜態 rows 與來源欄位 ⇒ rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得執行任意 shell；不得讀 repo 外檔案；不得讓生成結果隨執行環境改變。

### Phase 2 — 產出端擋（依賴：Phase 1 全部 Task）

**Task 2.1 — 手寫狀態偵測擴至全部活文件（新增行模式）**
- 目標：非權威活文件之手寫狀態在寫入前被擋，既有行不回洗。　檔案：`scripts/gen_fact_key_blocks.sh`（偵測器新增「只判新增行」入口）、新建 `scripts/live_doc_write_guard.sh`（PreToolUse Edit|Write 入口）。既有 caller：`_fk_reject_handwritten_status`（全檔模式維持不變）。
- 改法：新增行取法同 `scripts/verify_pretooluse.sh`（Edit＝`new_string`；Write＝磁碟舊檔 diff）；範圍＝Task 1.1 登記之活文件中非狀態權威者；判定沿用既有「識別碼 token ∩ `status_enum` 字面」；豁免＝合法生成區塊內、`HISTORY-BEGIN..END` 內、fenced code block 內。「」引號**不**豁免（引號為零成本繞法）。既有 `status_scope` 檔之全檔模式保留。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_edit_adds_B9F_with_status THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_edit_adds_B9F_pointer_only THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=roadmap_edit_unrelated_line_with_legacy_status_elsewhere THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=efcafc63_handoff_status_lines_re_added THEN rc=2`。
- **邊界**：①Write 新建檔 ⇒ 全文視為新增行；②Write 內容與磁碟相同 ⇒ 無新增行、rc=0；③新增行位於 fenced code block 內 ⇒ rc=0；④payload 無法解析且目標為登記活文件 ⇒ rc=2。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得掃描整檔既有行（會使既有活文件無法再改）；不得以寫檔後鉤子宣稱已擋。

**Task 2.2 — 新增行禁舊版字面（新舊並存）**
- 目標：修正舊句時，舊文只准進歷史專區，不再以刪除線或「保留供追溯」類字面留在正文。　檔案：`scripts/live_doc_write_guard.sh`（同一入口第二道判定）；考古字面集合與適用類別定義於 `scripts/live_doc_registry.json`。既有 caller：無。
- 改法：適用類別之新增行位於歷史專區外，含 `~~` 或考古字面集合任一 ⇒ exit 2；適用類別之活文件若無歷史專區而需寫入歷史，須先新增 `HISTORY-BEGIN..END` 區塊（區塊內新增行豁免）。新增行含 canonical finding ID 且位於歷史專區外 ⇒ exit 2（同 `obligation_block_check.sh` R5 語意之新增行版）。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=spec_edit_adds_strikethrough_outside_history THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=spec_edit_adds_strikethrough_inside_history THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=todo_edit_unrelated_line_with_legacy_strikethrough_elsewhere THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=spec_edit_adds_finding_id_outside_history THEN rc=2`。
- **邊界**：①把既有刪除線段落整段移入歷史專區（正文為刪除、專區為新增）⇒ rc=0；②日誌類檔案 ⇒ 不適用、rc=0；③`templates/` 內之範例字面 ⇒ 依登記類別決定，fixture 各一。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得要求既有刪除線清零；不得擴及 `handoffs/`。

**Task 2.3 — pre-commit 兜底與未登記路徑**
- 目標：Bash、生成器、委員 CLI 寫入之活文件在 commit 時被同一判定擋下。　檔案：`scripts/git_hooks/pre-commit`（呼叫 `scripts/live_doc_write_guard.sh` 之暫存差異模式與 `scripts/live_doc_registry_check.sh`）。既有 caller：`scripts/git_hooks/pre-commit` 既有段。
- 改法：暫存差異之新增行套 Task 2.1、2.2 判定；暫存之新增 `.md` 套 Task 1.1 未登記判定；任一命中 ⇒ commit rc!=0。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=bash_redirect_added_status_line_staged THEN rc!=0`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=clean_staged_diff THEN rc=0`；`ASSERT bash scripts/live_doc_registry_check.sh --staged WHEN fixture=new_unregistered_md_staged THEN rc!=0`。
- **邊界**：①暫存為刪除檔 ⇒ 不檢查；②暫存為重新命名 ⇒ 以新路徑判定類別。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得提供略過旗標；不得在 pre-push 重複執行同一判定。

**Task 2.4 — 交接檔流水帳生命週期**
- 目標：交接檔只留進行中工作之紀錄；所屬工作已結束之流水帳不得留在交接檔。　檔案：`scripts/live_doc_write_guard.sh`（交接類判定）、`HANDOFF.md` 結構。既有 caller：`scripts/inject_handoff.sh`（整份注入，不改）。
- 改法：交接檔之流水帳置於 `HISTORY-BEGIN..END`，每則以機器標記宣告所屬識別碼（格式定義於 `scripts/live_doc_registry.json`）；所屬識別碼於 `scripts/fact_keys.json` 之狀態 ∈ `_schema.enforcement_completed_statuses` ⇒ pre-commit rc!=0（一致性型，登記理由：須跨檔讀狀態）；無標記之流水帳則 ⇒ rc!=0。交接檔「待辦」區段引用之 session 名於 `scripts/debt_ledger.sh --list` 為 `CLOSED` ⇒ rc!=0。依據＝使用者 2026-09-15 逐字（§A）；進行中工作之流水帳保留（回應 consult-r2 composer 之注入脈絡論證）。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=handoff_history_entry_for_completed_batch THEN rc!=0`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=handoff_history_entry_for_open_batch THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=handoff_todo_cites_closed_session THEN rc!=0`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=handoff_history_entry_without_marker THEN rc!=0`。
- **邊界**：①識別碼剛轉完成、同一 commit 內移出流水帳 ⇒ rc=0；②標記引用未登記識別碼 ⇒ rc!=0；③`## 坑` 區段引用已結束工作作教訓 ⇒ 不受本判定（受 Task 2.1 約束）。
- **存活至**：全票完工後常設。
- **覆蓋風險**：Task 4.1 首次把現行交接檔改成本結構。
- 不可做：不得以行數判定；不得刪除流水帳內容而不移至日誌類檔案（移出檔路徑由 `scripts/live_doc_registry.json` 登記）。

**Task 2.5 — 既有檢查依類別適用、宣稱與規則同步**
- 目標：消除已知摩擦與過期宣稱。　檔案：`scripts/spec_xref_hook.sh`（「概念被拿掉須補版本標記」只套 LIVE-SPEC 類）、`scripts/plain_docs_sync_check.sh`（catch-all 改為對 Task 1.1 登記 fail-closed）、`CLAUDE.md:16` 與 `.claude/settings.json` PreCompact 訊息（刪除 HANDOFF 行數上限）、`scripts/fact_keys.json` `governance-enforcement`（登記 DOCROT Task 1.1–1.8 與本票各閘之掛載點）、DOCROT Task 1.3 之宣稱文字（改為只擋「共 N 條」雙落點、不涵蓋交接檔）。既有 caller：各檔既有測試。
- 改法：逐檔最小改動；`.claude/settings.json` 新增之 PreToolUse 掛載與本 Task 同一 commit。
- **驗證**：`ASSERT bash scripts/spec_xref_hook.sh WHEN fixture=handoff_remove_current_lines_history_keeps_concept THEN rc=0`；`ASSERT bash scripts/spec_xref_hook.sh WHEN fixture=spec_remove_concept_live_reference_remains THEN rc=2`；`ASSERT bash scripts/plain_docs_sync_check.sh WHEN fixture=new_unregistered_plain_doc THEN rc!=0`；`grep -c '30 行' CLAUDE.md` 輸出為 0；`bash scripts/gen_fact_key_blocks.sh --check` rc=0。
- **邊界**：①`spec_xref_hook.sh` 對未登記路徑之行為與改前相同（fixture 對照）；②`governance-enforcement` 新列之掛載點須實際存在於 `.claude/settings.json`（既有 `_fk_validate_enforcement` 機械對證）。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得改動 `spec_xref_hook.sh` 對 LIVE-SPEC 類之判定寬嚴；不得刪除 DOCROT Task 1.1–1.3 之掃描器。

### Phase 3 — 量測（依賴：無；可與 Phase 2 並行）

**Task 3.1 — finding 類別欄雙填**
- 目標：每條 finding 有可機械計算之類別。　檔案：`scripts/governance_verdicts.json`（類別封閉集合唯一定義處，初值取 consult-r1 composer F3）、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 與 `templates/COMMITTEE_FINDING_TEMPLATE.md`（新增類別行）、`scripts/completeness_check.sh`（`--single` 驗委員欄）、`scripts/_synth_attr.py`（群集表驗主委欄）。既有 caller：`scripts/cx_run.sh`（交件後呼叫 `--single`）、`scripts/debt_clear.sh`。
- 改法：委員欄與主委欄皆必填、值 ∈ 封閉集合；兩欄不一致之 finding 須列於收斂檔「類別不一致」段並附處置 token，否則收案 rc!=0；量測分子取委員欄（consult-r2 裁定 D5）。只對本 Task 上線後之新交件與新收斂檔生效。
- **驗證**：`ASSERT bash scripts/completeness_check.sh --single <fixture> --family codex WHEN fixture=p1_without_category THEN rc=1`；`ASSERT bash scripts/completeness_check.sh --single <fixture> --family codex WHEN fixture=p1_category_outside_set THEN rc=1`；`ASSERT python3 scripts/_synth_attr.py <fixture> --mode gate WHEN fixture=category_mismatch_unlisted THEN rc=1`；`ASSERT python3 scripts/_synth_attr.py <fixture> --mode gate WHEN fixture=category_mismatch_listed_with_disposition THEN rc=0`。
- **邊界**：①零 findings sentinel ⇒ 類別欄仍必填；②上線前之舊交件重跑 ⇒ 依既有 forward-only 慣例豁免，fixture 一件。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得讓主委欄作為分子；不得對舊交件回溯要求。

**Task 3.2 — 收案量測事件與閘擋下事件**
- 目標：成效由機器逐輪記錄，不再由主委自判。　檔案：`scripts/audit_events.json`（新事件與欄位登記）、`scripts/debt_clear.sh`（收案時計算並寫事件，缺值 rc!=0）、`scripts/live_doc_write_guard.sh` 與 `scripts/live_doc_registry_check.sh`（擋下即寫事件）、新建 `scripts/docrot2_metrics.sh`（讀事件輸出報表）。既有 caller：`scripts/audit_append.sh`。
- 改法：收案事件欄位含 round、task、session、family 名冊、各類別計數、類別不一致數、委員型號與 effort（取不到者記 `unavailable`）；擋下事件欄位含規則識別碼、路徑、類別。
- **驗證**：`ASSERT bash scripts/debt_clear.sh <fixture args> WHEN fixture=synth_without_category_counts THEN rc!=0`；`ASSERT bash scripts/debt_clear.sh <fixture args> WHEN fixture=valid_round THEN rc=0`；對 valid_round fixture 之 audit 輸出以 `jq` 逐欄對讀（不寫聚合數）；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_edit_adds_B9F_with_status THEN rc=2` 之後 audit 含對應擋下事件一筆。
- **邊界**：①audit 寫入失敗 ⇒ 收案 rc!=0；②擋下事件寫入失敗 ⇒ 仍擋（rc=2），不因寫事件失敗而放行。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得以 DOCROT 之 `doc_friction_ratio` 字面作任何分子；不得在事件中寫入推定之委員型號。

### Phase 4 — 遷移現行活文件（依賴：Phase 1–3 全部 Task）

**Task 4.1 — 現行活文件改為投影結構**
- 目標：現行交接檔、ROADMAP、白話進度表、SPLITUNIFY 施工清單之狀態改由 Task 1.2／1.3 生成。　檔案：`HANDOFF.md`、`docs/ROADMAP.md`、`白話說明/` 內現行進度表、`docs/SPLITUNIFY_TODO.md` §B／§E。既有 caller：`scripts/inject_handoff.sh`、`scripts/plain_docs_render.sh`。
- 改法：插入合法生成區塊；刪除區塊外之手寫狀態值；交接檔改為 Task 2.4 結構，所屬工作已結束之流水帳移至登記之日誌類檔案。`docs/SPLITUNIFY_SPEC.D-002.md` 不在本 Task（見 §N）。
- **驗證**：`bash scripts/gen_fact_key_blocks.sh --check` rc=0；`bash scripts/live_doc_write_guard.sh --staged` 對本 Task commit rc=0；`bash scripts/plain_docs_render.sh --check` rc=0；`bash scripts/live_doc_registry_check.sh --all` rc=0。
- **邊界**：①遷移後 `scripts/inject_handoff.sh` 注入內容仍含生成區塊（fixture 對讀）；②白話進度表之生成區塊每列含識別碼、狀態值與權威相對路徑（consult-r2 composer M2 改寫）。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得改動已結案 epic 之文件；不得在本 Task 修改任何檢查之判定。

## §V 驗證策略與邊界測試目錄
- **測試落點**：新建 `tests/governance/test_docrot2_registry.py`（Task 1.1–1.3）、`test_docrot2_write_guard.py`（Task 2.1–2.4）、`test_docrot2_class_routing.py`（Task 2.5）、`test_docrot2_metrics.py`（Task 3.1–3.2）；fixture 置 `tests/governance/fixtures/docrot2/`。逐檔明列執行，禁 glob。
- **mutation（每道新判定至少一條，改壞須紅）**：①移除新增行模式之 Write diff、改為全文 ⇒ `roadmap_edit_unrelated_line_with_legacy_status_elsewhere` 應紅；②加入「」引號豁免 ⇒ 引號包狀態之 fixture 應紅；③`live_doc_registry_check.sh` 對未登記改 rc=0 ⇒ `new_unregistered_md_staged` 應紅；④類別欄驗證移除 ⇒ `p1_without_category` 應紅；⑤收案量測缺值改放行 ⇒ `synth_without_category_counts` 應紅；⑥流水帳完成判定改讀錯欄 ⇒ `handoff_history_entry_for_completed_batch` 應紅；⑦`spec_xref_hook.sh` 類別路由移除 ⇒ `handoff_remove_current_lines_history_keeps_concept` 應紅。
- **防假綠**：§C 所列既有測試檔之斷言 diff 須為零刪減；新斷言對應新行為。
- **成效判準（及格線）**：本票完工後第一張中大票之前兩輪 review：①每輪 canonical finding ≤20；②`scripts/docrot2_metrics.sh` 報告之文件同步類占比，第二輪低於第一輪；③該兩輪期間 Task 2.4 之交接過時判定於 pre-commit 無擋下以外之漏網（以 `git log` 之交接檔 diff 對讀）；④只因狀態改字而重蓋章之戳記輪為 0（狀態值已不在規格內）。不達標 ⇒ 回到 consult 討論「哪一類事實或哪一條寫入路徑仍漏」，不得同時開新治理 epic。
- **邊界目錄**：空檔、只含生成區塊之檔、含換行之路徑、symlink、重新命名、刪除檔、fenced code block、HISTORY 區塊跨越 Edit 邊界、payload 不可解析。

## §R 回退
- 每個 Task 獨立 commit，可單獨 revert；回退順序與 Phase 相反。
- `.claude/settings.json` 之新掛載與 Task 2.5 同一 commit，revert 該 commit 即卸載。
- Task 4.1 回退＝revert 遷移 commit，交接檔流水帳由日誌類檔案還原。

## §N N/A 登記
- §G：N/A — 本票為治理文件閘，不碰數值、特徵、ML、回測路徑。

**殘留**：
- `DOCROT2-RESID-MEMORY-OFFREPO` 主委記憶檔不受本票閘約束 — `為何現在不做: blocked-by:hook 以 git 根目錄相對路徑運作，記憶目錄位於 repo 外`；觸發：記憶目錄移入 repo 或 hook 支援 repo 外絕對路徑白名單；登記處：本 SPEC §N。
- `DOCROT2-RESID-D002-STRUCTURAL-RED` `docs/SPLITUNIFY_SPEC.D-002.md` 之 `obligation_block_check.sh` 結構性紅與既有正文狀態字面 — `為何現在不做: blocked-by:SPLITUNIFY 規格 R 重開（將改寫 D-002 正文，屆時受 Task 2.1／2.2 新增行規則約束）`；觸發：SPLITUNIFY R 重開之第一個 commit；登記處：本 SPEC §N。
- `DOCROT2-RESID-SEMANTIC` 同一段現行文字內部之語意矛盾 — `為何現在不做: needs-research:兩段散文互斥之可證偽機械判準`；觸發：出現可機械判定之封閉句型；登記處：本 SPEC §N。
- `DOCROT2-RESID-PARAPHRASE` 以 `status_enum` 以外之措辭寫狀態可繞過 — `為何現在不做: needs-research:開放語言無法封閉列舉`；觸發：`scripts/docrot2_metrics.sh` 報告之交接過時漏網出現改寫措辭樣本；登記處：本 SPEC §N。
- `DOCROT2-RESID-EXECUTOR-WRITE` 委員 CLI 與 Bash 重導寫入不經寫入前檢查 — `為何現在不做: blocked-by:寫入前 hook 無法取得執行端 CLI 與任意 shell 重導之寫入事件`；部分閘＝Task 2.3 pre-commit 與既有 `scripts/cx_run.sh` 交件檢查；觸發：hook 事件模型支援 Bash 寫檔目標；登記處：`docs/GOV_ENFORCEMENT_REGISTRY.md`。
- `DOCROT2-RESID-CATEGORY-SELF-REPORT` 委員自填類別可能錯填 — `為何現在不做: needs-research:類別判定之獨立機械信任根`；部分閘＝Task 3.1 主委欄對照與不一致列處置；觸發：類別不一致數連續兩輪 >0；登記處：本 SPEC §N。
- `DOCROT2-RESID-COMMITTEE-MODEL` 委員實際型號不作狀態種類 — `為何現在不做: blocked-by:SU-RESID-COMMITTEE-MODEL-EVIDENCE（實際型號無機械權威）`；觸發：該殘留關閉；登記處：本 SPEC §N。
