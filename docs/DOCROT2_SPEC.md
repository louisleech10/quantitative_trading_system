# DOCROT2 — 活文件狀態單一來源與新舊並存之產出端擋（修正 DOCROT）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260915-docrot2-x-consult-r1/synth.md`、`.../20260915-docrot2-x-consult-r2/synth.md`、`.../20260915-docrot2-x-review-r1/synth.md`、`.../20260915-docrot2-x-review-r2/synth.md`　|　日期：2026-09-15　|　對應 TODO：`docs/DOCROT2_TODO.md`　|　版本：v3

## §RISK 風險分級
- **大小**：大（全專案活文件、共用產出端 hook、多 Phase）。
- **命中高風險原則**：(b) 跨模組／共用路徑——`.claude/settings.json` hook 鏈、`scripts/fact_keys.json` 與其生成器、`scripts/completeness_check.sh`、`scripts/debt_clear.sh` 為所有票共用；(c) 多 Phase——登記、擋、量測、遷移四段，後段依賴前段。
- RISK-HIT: b,c
- 未命中 (a)(d)：不碰數值、特徵、ML、回測路徑 ⇒ §G 移 §N。

## §A 假設與待使用者確認
**已驗證事實**（2026-09-15 實跑）：
- FACT-RECEIPT: `jq -c '._schema | {status_enum, status_keys}' scripts/fact_keys.json` → 印出 `status_keys` 僅四個 `governance-*` key；`status_enum` 含 `已完成`、`部分完成`、`進行中`，不含 `完成`、`已關閉`、`部分關閉`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `jq -c '._schema.enforcement_completed_statuses' scripts/fact_keys.json` → 印出 `["收案","已落地","已完成"]`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `awk -F'|' 'NR>=58 && NR<=86 && $2 ~ /B[0-9]/ {print $4}' docs/SPLITUNIFY_TODO.md | sort | uniq -c` → 印出 §B 狀態欄 12 列全為「✅ 完成」或「✅ **完成**（附註）」兩形（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `awk -F'|' 'NR>=1082 && /^\| /{print $2" || "$4}' docs/SPLITUNIFY_TODO.md` → 印出 §E 識別碼欄以刪除線＋「已關閉」表示關閉、`SU-RESID-1` 以「可機械化之半已關閉」表示部分關閉、理由類別欄為 `blocked-by`／`user-ruling`／`needs-research`／`—`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 438,560p scripts/gen_fact_key_blocks.sh` → 印出 `_fk_reject_handwritten_status`：範圍檔內、合法生成區塊外，同一行同時含登記識別碼（token 邊界）與 `status_enum` 字面即報（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `jq -c '._schema.status_scope' scripts/fact_keys.json` → 印出 `["HANDOFF.md","docs/GOVERNANCE_EXECUTION_ORDER.md","白話說明/"]`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `nl -ba scripts/verify_pretooluse.sh | sed -n '69,90p'` → Edit 只取 `new_string`、Write 以磁碟舊檔 diff（codex 實跑 2026-09-15，review-r1 `CODEX-R1-P1-04`）⇒ 本票須另以 `old_string` 重建寫入後全文。
- FACT-RECEIPT: `jq -r '.debt_events | keys[]' scripts/audit_events.json` → 印出含 `committee_round_open`、`committee_debt_clear`；`grep -o '"sequence": *[0-9]*' .claude/gate/audit.log | tail -1` → 印出 `"sequence": 4497`（主委 實跑 2026-09-15）⇒ audit 序號可作「本規則上線後之輪次」判定依據。
- FACT-RECEIPT: `git show efcafc63:HANDOFF.md | sed -n '258,270p'` → 印出現況「＝v31 待重簽」、下一步「`review-r39`」、「現行＝三家全員」（composer 實跑 2026-09-15）。
- FACT-RECEIPT: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=1、364 行（composer 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 118,123p scripts/plain_docs_sync_check.sh` → 印出 catch-all `*) echo ""`（codex 實跑 2026-09-15）。
- FACT-RECEIPT: `grep -n '30 行' CLAUDE.md` → 印出 `16:`（主委 實跑 2026-09-15）。

**待使用者確認**：待確認：無

**已確認結果**：
- 2026-09-15 使用者：「持續不接受用紀律或記憶當解法，但允許擴建治理工具，就是要修正DOCROT沒做好之處，真正減少文檔問題和降低不必要的輪數，而且要全專案涵蓋，不是只有SPEC」
- 2026-09-15 使用者：「交接文件能交接清楚明確是最重要，所以不一定要限制行數，怕的只是把舊案或已完成或不必要的殘留在裡面」
- 2026-09-15 使用者：「針對修正優化DOCROT的方法，你跟委員討論共識決定，先做好DOCROT這部分」
- 2026-09-15 使用者：「現在就是Codex+Cursor(Grok)兩家委員，等Grok回來後我會再將Cursor切成Composer回到三家委員」

## §C 約束
- **產出端覆蓋鐵律**（`CLAUDE.md`）：每道新檢查掛寫檔當下；掛不上者登記於 `scripts/fact_keys.json` 之 `governance-enforcement` 並寫明理由。
- **不接受紀律／記憶當解法**：任何「須記得做」之步驟一律改為機械閘或具名殘留。
- **面向未來**：既有行不回洗；新增行、新檔、本票遷移之檔才受新規則全量約束。「本規則上線後」一律以 audit 序號或 commit 判定，不以日期或 mtime。
- **單一真相源**：本票新增之封閉集合一律定義於 JSON（`scripts/live_doc_registry.json`、`scripts/governance_verdicts.json`、`scripts/fact_keys.json`、`scripts/docrot2_metric_contract.json`）；SPEC 只 pointer，初始值由 TODO 逐項給出供實作者寫入，寫入後以 JSON 為準。
- **設計依據（外部做法，2026-09-12 研究）**：架構決策紀錄（ADR）一經接受即不可變、決策改變則寫新紀錄取代，規格只描述現行態；立法之 consolidated text 以機械合併修正案、不重新審議文字。對應本專案：`handoffs/reconcile/*/synth.md` 與 git 為不可變修訂紀錄，活文件只承載現行態。來源：IcePanel〈Architecture decision records (ADRs)〉、ASDLC.io〈The ADR〉、Wikipedia〈Consolidation (law)〉、U.S. House Office of the Legislative Counsel〈HOLC Guide to Legislative Drafting〉。
- **不弱化既有檢查**：DOCROT Task 1.1–1.6、1.8 保留；`tests/governance/test_govb1_factkey_gen.py`、`test_factkey_write_guard.py`、`test_govb1_factkey_hook.py`、`test_docrot_f2_total_items_count.py`、`test_docrot_e3_brief_placeholder.py`、`test_docrot_claim_committee_backing.py` 之既有斷言零刪減。
- **hook 成本**：未命中登記活文件之寫入不得 fork 重檢查；寫入前檢查只對登記活文件執行。
- **自身故障**：寫入前檢查對登記活文件路徑之自身故障 exit 2；非登記路徑放行。
- 解耦 7 條：不涉 `momentum/`、`api/`、`frontend/`。

## §P Phase 與依賴

### Phase 1 — 登記與狀態切換（依賴：無）

**Task 1.1 — 活文件類別登記**
- 目標：封閉登記活文件、類別與各類規則，並提供單一登記交易。　檔案：新建 `scripts/live_doc_registry.json`、`scripts/live_doc_registry_check.sh`、`scripts/live_doc_registry_update.sh`。既有 caller：無。
- 改法：JSON 含類別集合、路徑對照（exact 與 `/` 結尾 prefix，禁 wildcard）、排除路徑、各類規則旗標、考古字面集合、歷史專區指標文法、交接檔區段集合與條目標記文法、交接投影（現況與待辦各自之來源 key、狀態篩選、欄位）、日誌類移出路徑；初始值由 TODO Task 1.1 給出。清冊由單一探索函式產生：`git ls-files --cached --others --exclude-standard -z`（NUL-safe、`LC_ALL=C` 排序）→ 範圍＝`docs/` 與 `白話說明/` 下全部層級、repo 根目錄之 `.md` → 先套 HIST prefix → 其餘逐條 exact 分類（`docs/` 頂層且檔名含 SPEC、TODO、PLAN 者為 LIVE-SPEC；未落入任何類者為 OTHER-DORMANT，含巢狀路徑）。`live_doc_registry_check.sh` 之 `--path`／`--all`／`--staged` 皆用同一探索函式；未命中、同優先級命中兩類 ⇒ rc=1；`_schema.status_scope` 每項須落在登記內。新增活文件一律經 `live_doc_registry_update.sh --add <path> [--class <類別>]` 登記（未給類別時以同一分類述詞判定），寫入決定性排序之 JSON；手改登記檔之結果仍受 `--all` 判定。
- **驗證**：`ASSERT bash scripts/live_doc_registry_check.sh --path docs/NEW_THING.md WHEN fixture=unregistered THEN rc=1`；`ASSERT bash scripts/live_doc_registry_check.sh --all WHEN fixture=path_in_two_classes THEN rc=1`；`ASSERT bash scripts/live_doc_registry_check.sh --all WHEN fixture=archived_spec_listed_as_live_spec THEN rc=1`；`ASSERT bash scripts/live_doc_registry_check.sh --all WHEN fixture=nested_doc_unclassified THEN rc=1`；`ASSERT bash scripts/live_doc_registry_update.sh --add docs/NEW_SPEC.md WHEN fixture=new_top_level_spec THEN rc=0`；`ASSERT bash scripts/live_doc_registry_check.sh --all WHEN fixture=excluded_site_listed_as_live THEN rc=1`；`ASSERT bash scripts/live_doc_registry_check.sh --all WHEN fixture=one_registered_path_removed THEN rc=1`；`ASSERT bash scripts/live_doc_registry_check.sh --all WHEN fixture=current_tree THEN rc=0`。
- **邊界**：①symlink、非 regular file、含換行之路徑 ⇒ 依 `_fk_scope_files` 同規則；②登記檔非 JSON ⇒ rc=1；③`handoffs/` 下 `.md` ⇒ 不在清冊範圍、rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無（Task 2.x、4.1 只消費）。
- 不可做：不得 glob；不得登記 `handoffs/` 為活文件；不得改 hook 掛載。

**Task 1.2 — 產品 epic 狀態遷入 `scripts/fact_keys.json` 並即時切換**
- 目標：SPLITUNIFY 之批次、Task、殘留狀態與本票（`B-63`）狀態只存於 `scripts/fact_keys.json` rows，施工清單之狀態改為生成區塊；同一 commit 完成，不設過渡雙權威（review-r1 K1、K2）。　檔案：`scripts/fact_keys.json`、`docs/SPLITUNIFY_TODO.md`（§B、§C Task 標題、§E）、`docs/GOV_TICKET_SOT.md`（經 `--write`）、`handoffs/20260801-GOV-AMEND-BACKLOG.md`、`docs/DOCROT2_TODO.md`（§B）。既有 caller：`scripts/gen_fact_key_blocks.sh`、`scripts/ticket_universe.sh`、`scripts/factkey_write_guard.sh`（不改）。
- 改法：新 status key 各宣告 `columns`（識別碼第 2 欄）與 `target`；狀態值一律取既有 `status_enum`，由 TODO Task 1.2 之一次性遷移對照換算，理由類別留在 §E 散文欄、不進狀態值。施工清單原手寫狀態欄與 Task 標題中之狀態字面刪除，改插合法生成區塊並 `--write`。完成語意之值須 ∈ `_schema.enforcement_completed_statuses`。
- **驗證**：`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=splitunify_status_cutover THEN rc=0`；遷移前後逐識別碼對讀：遷移前字面經對照換算之值＝rows 值（fixture 以 JSON 逐 ID 比對，不寫聚合數）；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=completed_batch_row_value_outside_completed_set THEN rc!=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=same_id_in_two_status_keys THEN rc!=0`；`bash scripts/ticket_universe.sh --check` rc=0。
- **邊界**：①`B9` 與 `B9A` token 邊界；②§E 同一識別碼有劃除之原文列與現行列 ⇒ 只登現行列，原文列移入歷史專區（受 Task 2.2 指標文法約束之前之一次性搬遷）；③遷移對照未涵蓋之字面 ⇒ 遷移 fixture rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得擴充 `status_enum`；不得保留手寫狀態欄；不得動 `docs/SPLITUNIFY_SPEC.D-002.md`。

**Task 1.3 — 委員組成投影讀機器權威**
- 目標：委員組成之投影讀 `scripts/governance_families.json`，不複製值；投影可依狀態篩選列（供交接現況與待辦）。規格版本不作狀態種類——其唯一來源為該規格歷史專區最新之 `v<N>` 指標行（Task 2.2 文法）。　檔案：`scripts/gen_fact_key_blocks.sh`、`scripts/fact_keys.json` `_schema.fields`。既有 caller：同 Task 1.2。
- 改法：rows 來源欄位之封閉形式＝`{file: repo 相對 JSON 路徑, path: 字串陣列（逐層物件鍵）}`；該路徑之值須為字串陣列，每元素產出一列 `[三位零補序號, 元素]`；不接受任意查詢式。同 key 同時有靜態 rows 與來源欄位、路徑不存在、值非字串陣列、路徑含 `..` 或為絕對路徑 ⇒ rc!=0。另新增投影篩選之封閉形式＝`{source_keys: key 陣列, status_column: 欄名, allow: 狀態值陣列}`：自各來源 key 取狀態欄 ∈ `allow` 之列，依 `source_keys` 順序與 rows 原順序串接；來源 key 不存在、欄名不存在、`allow` 含 `status_enum` 以外之值 ⇒ rc!=0。
- **驗證**：`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_source_string_array THEN rc=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_source_changed_without_write THEN rc!=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_source_value_is_object THEN rc!=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_source_absolute_path THEN rc!=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_filter_selects_open_rows THEN rc=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=rows_filter_unknown_status_value THEN rc!=0`；`venv/bin/python -m pytest tests/governance/test_govb1_factkey_gen.py -q` 0 failed。
- **邊界**：①空陣列 ⇒ 產出零列、rc=0；②陣列含非字串 ⇒ rc!=0；③靜態 rows 與來源並存 ⇒ rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得執行 shell；不得讀 repo 外檔；輸出須符合既有決定性契約。

### Phase 2 — 產出端擋（依賴：Phase 1 全部 Task）

**Task 2.1 — 寫入前手寫狀態偵測（新增行模式）**
- 目標：非權威活文件之新增行含「識別碼＋狀態值」即寫入前擋。　檔案：新建 `scripts/live_doc_write_guard.sh`；`scripts/gen_fact_key_blocks.sh`（抽出共用判定入口，既有全檔模式行為不變）。
- 改法：寫入後全文之重建——Edit：`replace_all` 為 true ⇒ 磁碟舊檔之全部 `old_string` 取代為 `new_string`；否則 `old_string` 於磁碟舊檔須恰出現一次再取代，出現 0 次或 2 次以上 ⇒ exit 2。Write：`content` 即寫入後全文。新增行＝舊檔與寫入後全文之 diff `+` 行，位置以寫入後全文之行號計。判定沿用「識別碼 token ∩ `status_enum` 字面」；豁免＝寫入後全文中位於合法生成區塊內、`HISTORY-BEGIN..END` 內、fenced code block 內之行。**相對 consult-r2 裁定 2 之具名偏離**：不採引號豁免，亦不設樣本句豁免（同行樣本豁免可在樣本後附加狀態字面繞過）；需引用過時樣本者置於 fenced code block。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_edit_adds_id_with_status THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=same_new_string_old_string_inside_history THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=same_new_string_old_string_outside_history THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=replace_all_true_two_occurrences THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=quoted_id_with_status THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=git_show_decoy_status_suffix THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=stale_sample_in_fence THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=edit_old_string_absent THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=edit_old_string_nonunique THEN rc=2`。
- **邊界**：①Write 新建檔 ⇒ 全文為新增行；②寫入後全文與舊檔相同 ⇒ rc=0；③payload 不可解析且目標為登記活文件 ⇒ rc=2；④既有行含狀態、本次新增行無 ⇒ rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得掃整檔既有行；不得以寫檔後鉤子宣稱已擋。

**Task 2.2 — 新增行禁舊版字面；歷史專區只准指標**
- 目標：活文件只承載現行態，修訂史只以指標指向不可變紀錄（§C 設計依據）。　檔案：`scripts/live_doc_write_guard.sh`（第二道）；字面集合、指標文法、適用類別定義於 `scripts/live_doc_registry.json`。
- 改法：適用類別之新增行位於歷史專區外且含 `~~`、考古字面集合任一、或 canonical finding ID（形狀同 `scripts/_synth_attr.py` 之 `ID_RE`）⇒ exit 2。適用類別之新增行位於歷史專區內，須全行符合指標文法 `- <YYYY-MM-DD>：<主詞> → <目標>`：主詞為單一 token，只准 `v<N>` 或登記之狀態識別碼；目標只准以反引號包住、工作樹中實際存在之 repo 相對路徑（含 `.git/info/exclude` 排除之 `handoffs/`——不可變收斂檔之權威位置在此，故以工作樹存在性而非 git 物件驗證），或 `commit` 加反引號包住之 7–40 位十六進位且 `git cat-file -e` 成立者；主詞或目標不合、目標不存在 ⇒ exit 2。整段自正文移出（正文為刪除）不受限。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=spec_adds_strikethrough_outside_history THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=spec_adds_finding_id_outside_history THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=spec_history_adds_pointer_line THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=spec_history_adds_copied_old_text THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=history_pointer_free_text_subject THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=history_pointer_target_missing THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=todo_unrelated_edit_legacy_strikethrough_elsewhere THEN rc=0`。
- **邊界**：①日誌類 ⇒ 不適用、rc=0；②刪除正文段落 ⇒ rc=0；③`templates/` 依類別旗標，fixture 各一。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得要求既有刪除線清零；不得擴及 `handoffs/`。

**Task 2.3 — pre-commit 兜底、未登記路徑、樹狀態重放**
- 目標：Bash、生成器、委員 CLI 寫入在 commit 時以同一判定擋下；可對指定 commit 重放。　檔案：`scripts/git_hooks/pre-commit`、`scripts/live_doc_write_guard.sh`（`--staged`、`--tree <commit> --path <p>`）、`scripts/live_doc_registry_check.sh`（`--staged`）。
- 改法：`--staged`：對每個暫存之登記活文件，以 `HEAD` 版為舊檔、index 版為寫入後全文，套 Task 2.1、2.2 判定與 Task 2.4 之全文判定；刪除檔不判；重新命名以新路徑判類別；二進位檔略過。`--tree <commit> --path <p>`：以該 commit 之檔為寫入後全文，執行 Task 2.4 之全文判定（供 §V 成效判準重放）。pre-commit 呼叫兩支之 `--staged`，任一非零即中止，無略過旗標。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=bash_redirect_added_status_line_staged THEN rc!=0`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=clean_staged_diff THEN rc=0`；`ASSERT bash scripts/live_doc_registry_check.sh --staged WHEN fixture=new_unregistered_md_staged THEN rc!=0`；`ASSERT bash scripts/live_doc_write_guard.sh --tree HEAD --path HANDOFF.md WHEN fixture=handoff_tree_with_completed_entry THEN rc!=0`。
- **邊界**：①暫存為刪除 ⇒ 不判；②index 與工作樹不同 ⇒ 以 index 為準。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得提供略過旗標；不得在 pre-push 重複執行。

**Task 2.4 — 交接檔封閉文法與流水帳生命週期**
- 目標：交接檔只含生成之現況與待辦、手寫教訓、以及進行中工作之紀錄；現行交接檔之遷移屬本 Task。　檔案：`scripts/live_doc_write_guard.sh`（交接類全文判定）、`HANDOFF.md`、`docs/HANDOFF_ARCHIVE.md`、`scripts/fact_keys.json`（交接投影兩個 key）；文法定義於 `scripts/live_doc_registry.json`。既有 caller：`scripts/inject_handoff.sh`（不改）。
- 改法：交接檔之 H2 區段須屬登記之封閉集合；「現況」「待辦」兩區除合法生成區塊外不得有任何非空行，且各須恰含 `scripts/live_doc_registry.json` 交接投影所指之生成區塊（內容型，寫入前以寫入後全文判定）；投影每列欄位為識別碼、狀態、權威相對路徑、下一步，「下一步」為空 ⇒ 違規；現況＝投影來源 key 中狀態 ∈ {`進行中`、`部分完成`} 之列，待辦＝狀態 ∉ `enforcement_completed_statuses` 之列（由 Task 1.3 投影篩選產生，`--check` 對讀）；「坑」為手寫、受 Task 2.1；進行中紀錄區為 `HISTORY-BEGIN..END`，區內首個非空行起每則以條目標記開始（標記文法含一或多個登記識別碼），一則延伸至下一標記或區塊結束；區內首個標記前有非空行、標記含未登記識別碼 ⇒ 違規（內容型）；任一則所含識別碼之狀態 ∈ `enforcement_completed_statuses` ⇒ 違規（一致性型，只在 `--staged`／`--tree` 判定，理由登記於 `governance-enforcement`）。
- **驗證**：`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_current_section_handwritten_line THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_unknown_h2_section THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_todo_row_missing_next_action THEN rc=2`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=handoff_todo_contains_completed_row THEN rc!=0`；`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN fixture=handoff_current_missing_open_batch THEN rc!=0`；`ASSERT bash scripts/live_doc_write_guard.sh WHEN fixture=handoff_history_line_before_first_marker THEN rc=2`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=handoff_entry_any_id_completed THEN rc!=0`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=handoff_entry_all_ids_open THEN rc=0`；`ASSERT bash scripts/live_doc_write_guard.sh --staged WHEN fixture=efcafc63_handoff_status_lines_in_current_section THEN rc!=0`。
- **邊界**：①同一 commit 內狀態轉完成且條目已移出 ⇒ rc=0；②多識別碼中一個完成 ⇒ 整則違規；③跨票教訓寫於「坑」⇒ 不受生命週期判定；④遷移後 `scripts/inject_handoff.sh` 注入內容含生成區塊（對讀）；⑤本 Task 之交接檔遷移與 Task 2.5 之 PreToolUse 掛載須同一 commit——掛載先於遷移則交接檔任何編輯皆因文法不合被擋。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無（交接檔遷移在本 Task 內完成，Task 4.1 不再改交接檔結構）。
- 不可做：不得以行數判定；不得刪除進行中紀錄而不移至登記之日誌類檔。

**Task 2.5 — 既有檢查依類別適用、宣稱與規則同步、掛載**
- 目標：消除已知摩擦、過期宣稱與互斥規則，掛上 Task 2.1–2.4。　檔案：`scripts/spec_xref_hook.sh`、`scripts/plain_docs_sync_check.sh`、`CLAUDE.md`、`.claude/settings.json`（PreToolUse、PreCompact）、`scripts/fact_keys.json` `governance-enforcement`。
- 改法：`spec_xref_hook.sh` 之「概念被拿掉須補版本標記」只對 LIVE-SPEC 類執行；`plain_docs_sync_check.sh` 之 catch-all 改查登記、未登記 rc!=0；`CLAUDE.md:16` 與 PreCompact 訊息刪除 HANDOFF 行數上限；`governance-enforcement` 追加 DOCROT Task 1.1–1.8 與本票各閘之掛載點（由 `_fk_validate_enforcement` 對證存在），DOCROT Task 1.3 宣稱改為只擋「共 N 條」雙落點、不涵蓋交接檔；`.claude/settings.json` 新增 PreToolUse Edit|Write 掛 `scripts/live_doc_write_guard.sh`，與本 Task 同一 commit。
- **驗證**：`ASSERT bash scripts/spec_xref_hook.sh WHEN fixture=handoff_remove_current_lines_history_keeps_concept THEN rc=0`；`ASSERT bash scripts/spec_xref_hook.sh WHEN fixture=spec_remove_concept_live_reference_remains THEN rc=2`；`ASSERT bash scripts/plain_docs_sync_check.sh WHEN fixture=new_unregistered_plain_doc THEN rc!=0`；`grep -c '30 行' CLAUDE.md` 輸出 0；`jq empty .claude/settings.json` rc=0；`bash scripts/gen_fact_key_blocks.sh --check` rc=0。
- **邊界**：①未登記路徑之 `spec_xref_hook.sh` 行為與改前相同；②`governance-enforcement` 新列掛載點不存在 ⇒ `--check` rc!=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得改變 `spec_xref_hook.sh` 對 LIVE-SPEC 之判定寬嚴；不得刪除 DOCROT Task 1.1–1.3 掃描器。

### Phase 3 — 量測（依賴：Phase 2 全部 Task）

**Task 3.1 — finding 類別欄雙填與適用門檻**
- 目標：每條 finding 有可機械計算之類別；只對本規則上線後開債之輪次生效。　檔案：`scripts/governance_verdicts.json`（類別封閉集合、適用門檻序號）、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`、`scripts/completeness_check.sh`、`scripts/_synth_attr.py`、`scripts/cx_run.sh`（傳 round id 給 `--single`）。
- 改法：類別值初值由 TODO Task 3.1 給出。適用門檻＝本 Task 落地 commit 寫入之 audit 序號；某輪之 `committee_round_open` 事件序號大於門檻 ⇒ 該輪委員交件須有類別欄且值 ∈ 集合、收斂檔群集表須有主委類別欄；兩欄不一致之 finding 須列於「類別不一致」段並附處置 token，否則收案 rc!=0；量測分子取委員欄。`--single` 未給 round id ⇒ 視為須有類別（fail-closed）。`scripts/cx_run.sh` 之四個 `--single` 呼叫面（selfcheck、review／consult／closure 收件、stamp 收件、格式失敗重跑）皆傳同一 round id；selfcheck 未給 round id 時照上述 fail-closed。
- **驗證**：`ASSERT bash scripts/completeness_check.sh --single <fixture> --family codex --round-id <rid> WHEN fixture=round_after_threshold_p1_without_category THEN rc=1`；`ASSERT bash scripts/completeness_check.sh --single <fixture> --family codex --round-id <rid> WHEN fixture=round_before_threshold_p1_without_category THEN rc=0`；`ASSERT bash scripts/completeness_check.sh --single <fixture> --family codex WHEN fixture=no_round_id_p1_without_category THEN rc=1`；`ASSERT bash scripts/completeness_check.sh --single <fixture> --family codex --round-id <rid> WHEN fixture=category_outside_set THEN rc=1`；`scripts/cx_run.sh` 四個 `--single` 呼叫面逐一以門檻前 round 之無類別交件驗 rc=0、門檻後驗 rc=1；`ASSERT python3 scripts/_synth_attr.py <fixture> --mode gate WHEN fixture=category_mismatch_unlisted THEN rc=1`；`ASSERT python3 scripts/_synth_attr.py <fixture> --mode gate WHEN fixture=category_mismatch_listed_with_disposition THEN rc=0`。
- **邊界**：①零 findings sentinel ⇒ 類別欄仍須有；②同一交件 bytes 以不同 round id 送入 ⇒ 依該 round 之開債序號判定。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得以日期、mtime 判定適用；不得讓主委欄作分子。

**Task 3.2 — 量測契約、收案事件、擋下事件**
- 目標：成效由機器逐輪記錄與計算。　檔案：新建 `scripts/docrot2_metric_contract.json`、`scripts/docrot2_metrics.sh`；`scripts/audit_events.json`、`scripts/debt_clear.sh`、`scripts/live_doc_write_guard.sh`、`scripts/live_doc_registry_check.sh`。
- 改法：契約檔定義：票鍵＝task-id 前兩段（`<YYYYMMDD>-<EPIC>`）；cohort＝首個「其第一個 `brief_kind=review` 之 `committee_round_open` 序號大於 `closure_sequence`」之票，取該票 `brief_kind=review` 之前兩輪（依 `committee_round_open` 序號，序號唯一故無並列）；finding 範圍（canonical，排除 `-P3-00` 零 findings sentinel）；分子（委員類別＝文件同步類）；分母（範圍內 canonical finding 數）；零分母（占比記 0）；比較（第二輪 ≤ 第一輪）；每輪 canonical ≤20；交接重放（各輪收案事件所記 commit 上跑 `bash scripts/live_doc_write_guard.sh --tree <commit> --path HANDOFF.md` 須 rc=0）；只動歷史區之重蓋章（cohort 票內每個 stamp 輪，以 `scripts/reconcile_body_hash.sh` 之本體區間——`## 戳記` 之前——比對被戳記檔前後兩次戳記之本體，差異行全落在 `HISTORY-BEGIN..END` 內者計 1，須為 0）。`scripts/audit_events.json` 之 `committee_round_open` 將 `brief_kind` 列入必填（只約束門檻後之新事件）。`debt_clear.sh` 收案前寫入收案量測事件，fields 與必填同步登記：`round_id`、`task_id`、`session_name`、`round_open_sequence`、`brief_kind`、`canonical_count`、各類別計數、`mismatch_count`、`handoff_tree_commit`（收案當下 HEAD）、各家 `model` 與 `reasoning_effort`（取不到記 `unavailable`）；stamp 輪另記 `stamp_target`、`body_sha_before`、`body_sha_after`、`history_only`；缺欄或寫入失敗 rc!=0；兩支守衛擋下時寫擋下事件，寫入失敗仍擋。`docrot2_metrics.sh` 只讀事件與契約，缺事件、重複事件、未知選取 ⇒ rc=1。
- **驗證**：`ASSERT bash scripts/debt_clear.sh <fixture args> WHEN fixture=synth_without_category_counts THEN rc!=0`；`ASSERT bash scripts/debt_clear.sh <fixture args> WHEN fixture=valid_round THEN rc=0`；`ASSERT bash scripts/docrot2_metrics.sh WHEN fixture=cohort_missing_second_round_event THEN rc=1`；`ASSERT bash scripts/docrot2_metrics.sh WHEN fixture=both_rounds_zero_doc_sync THEN rc=0`；`ASSERT bash scripts/docrot2_metrics.sh WHEN fixture=history_only_restamp_in_cohort THEN rc=1`；`ASSERT bash scripts/docrot2_metrics.sh WHEN fixture=history_only_restamp_hidden_by_stamp_lines THEN rc=1`；`ASSERT bash scripts/docrot2_metrics.sh WHEN fixture=cohort_round_open_missing_brief_kind THEN rc=1`；`ASSERT bash scripts/docrot2_metrics.sh WHEN fixture=duplicate_round_metric_event THEN rc=1`；擋下 fixture 後 audit 含對應擋下事件 1 筆（`jq` 對讀）。
- **邊界**：①audit 寫入失敗 ⇒ 收案 rc!=0；②擋下事件寫入失敗 ⇒ 仍 exit 2。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得以 `doc_friction_ratio` 字面作分子；不得寫入推定之委員型號；報表不得解析主委散文。

### Phase 4 — 遷移（依賴：Phase 1–3 全部 Task）

**Task 4.1 — 由登記導出之全專案遷移**
- 目標：現存活文件（交接檔除外，已於 Task 2.4 遷移）中之手寫狀態，要麼遷移為生成區塊、要麼具名留存。　檔案：`docs/ROADMAP.md`、`白話說明/` 內進度表、登記導出之其他命中檔；新建 `scripts/docrot2_migration_residuals.json`；`scripts/live_doc_registry_check.sh`（`--migration`）。
- 改法：`--migration` 對登記之非日誌、非歷史類活文件執行全檔模式偵測（新 status key 生效後），命中之每個檔須 ∈（本 Task 遷移後無命中）∪（`docrot2_migration_residuals.json` 所列，每列含路徑、理由類別、owner、觸發條件）；兩者皆否 ⇒ rc=1。交接檔不在本 Task 改結構，僅以 `bash scripts/live_doc_write_guard.sh --tree HEAD --path HANDOFF.md` 確認 rc=0。
- **驗證**：`ASSERT bash scripts/live_doc_registry_check.sh --migration WHEN fixture=hit_file_neither_migrated_nor_listed THEN rc=1`；`ASSERT bash scripts/live_doc_registry_check.sh --migration WHEN fixture=current_tree_after_migration THEN rc=0`；`bash scripts/gen_fact_key_blocks.sh --check` rc=0；`bash scripts/live_doc_write_guard.sh --staged` rc=0；`bash scripts/plain_docs_render.sh --check` rc=0。
- **邊界**：①殘留清單列之檔已無命中 ⇒ rc=1（清單過期須刪列）；②`docs/ROADMAP.md` 生成區塊與 `scripts/fact_keys.json` rows 逐識別碼對讀。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得改 `docs/SPLITUNIFY_SPEC.D-002.md`；不得修改任何檢查判定。

## §V 驗證策略與邊界測試目錄
- **測試落點**：`tests/governance/test_docrot2_registry.py`（Task 1.1–1.3）、`test_docrot2_write_guard.py`（Task 2.1–2.4）、`test_docrot2_class_routing.py`（Task 2.5）、`test_docrot2_metrics.py`（Task 3.1–3.2）、`test_docrot2_migration.py`（Task 4.1）；fixture 置 `tests/governance/fixtures/docrot2/`。逐檔明列執行。
- **mutation（改壞須紅）**：①Edit 重建改為只取 `new_string` ⇒ `same_new_string_old_string_inside_history` 應紅；②加入引號或同行樣本豁免 ⇒ `quoted_id_with_status`、`git_show_decoy_status_suffix` 應紅；③未登記改 rc=0 ⇒ `new_unregistered_md_staged` 應紅；④類別門檻比較改為恆真 ⇒ `round_before_threshold_p1_without_category` 應紅；⑤收案缺值改放行 ⇒ `synth_without_category_counts` 應紅；⑥條目完成判定改為「全部識別碼完成才擋」⇒ `handoff_entry_any_id_completed` 應紅；⑦類別路由移除 ⇒ `handoff_remove_current_lines_history_keeps_concept` 應紅；⑧歷史專區指標文法移除 ⇒ `spec_history_adds_copied_old_text` 應紅；⑨遷移判定不讀殘留清單 ⇒ `current_tree_after_migration` 應紅；⑩`replace_all` 為 false 時改取第一處 ⇒ `edit_old_string_nonunique` 應紅；⑪重蓋章判定改用整檔差異 ⇒ `history_only_restamp_hidden_by_stamp_lines` 應紅；⑫投影「下一步」欄檢查移除 ⇒ `handoff_todo_row_missing_next_action` 應紅。
- **防假綠**：§C 所列既有測試檔之斷言零刪減。
- **成效判準**：由 `scripts/docrot2_metric_contract.json` 定義、`bash scripts/docrot2_metrics.sh` 計算；及格＝契約四條全過（每輪 canonical finding ≤20；文件同步類占比第二輪 ≤ 第一輪；兩輪收案 commit 之交接檔重放 rc=0；範圍票之只動歷史區重蓋章輪為 0）。不達標 ⇒ 回到 consult 討論「哪一類事實或哪一條寫入路徑仍漏」，不得同時開新治理 epic。
- **邊界目錄**：空檔、只含生成區塊之檔、含換行之路徑、symlink、重新命名、刪除檔、fenced code block、HISTORY 區塊跨越 Edit 邊界、`replace_all`、payload 不可解析、index 與工作樹不同。

## §R 回退
- 每個 Task 獨立 commit，可單獨 revert；回退順序與 Phase 相反。
- `.claude/settings.json` 新掛載與 Task 2.5 同一 commit。
- Task 1.2 回退＝revert 該 commit（施工清單手寫狀態欄隨之還原）；Task 4.1 回退＝revert 遷移 commit。

## §N N/A 登記
- §G：N/A — 本票為治理文件閘，不碰數值、特徵、ML、回測路徑。

**殘留**：
- `DOCROT2-RESID-MEMORY-OFFREPO` 主委記憶檔不受本票閘約束 — `為何現在不做: blocked-by:hook 以 git 根目錄相對路徑運作，記憶目錄位於 repo 外`；觸發：記憶目錄移入 repo 或 hook 支援 repo 外絕對路徑白名單；登記處：本 SPEC §N。
- `DOCROT2-RESID-D002-STRUCTURAL-RED` `docs/SPLITUNIFY_SPEC.D-002.md` 之結構性紅與既有正文狀態字面 — `為何現在不做: blocked-by:SPLITUNIFY 規格 R 重開`；觸發：SPLITUNIFY R 重開之第一個 commit；登記處：`scripts/docrot2_migration_residuals.json`。
- `DOCROT2-RESID-SEMANTIC` 同一段現行文字內部之語意矛盾 — `為何現在不做: needs-research:兩段散文互斥之可證偽機械判準`；觸發：出現可機械判定之封閉句型；登記處：本 SPEC §N。
- `DOCROT2-RESID-PARAPHRASE` 交接檔「坑」與其他手寫區以 `status_enum` 以外措辭寫狀態可繞過 — `為何現在不做: needs-research:開放語言無法封閉列舉`；部分閘＝交接檔現況與待辦只准生成區塊；觸發：`scripts/docrot2_metrics.sh` 之交接重放出現改寫措辭樣本；登記處：本 SPEC §N。
- `DOCROT2-RESID-EXECUTOR-WRITE` 委員 CLI 與 Bash 重導寫入不經寫入前檢查 — `為何現在不做: blocked-by:寫入前 hook 取不到執行端 CLI 與任意 shell 重導之寫入事件`；部分閘＝Task 2.3 pre-commit；觸發：hook 事件模型支援 Bash 寫檔目標；登記處：`governance-enforcement`。
- `DOCROT2-RESID-CATEGORY-SELF-REPORT` 委員自填類別可能錯填 — `為何現在不做: needs-research:類別判定之獨立機械信任根`；部分閘＝Task 3.1 主委欄對照；觸發：類別不一致數連續兩輪 >0；登記處：本 SPEC §N。
- `DOCROT2-RESID-COMMITTEE-MODEL` 委員實際型號不作狀態種類 — `為何現在不做: blocked-by:SU-RESID-COMMITTEE-MODEL-EVIDENCE`；觸發：該殘留關閉；登記處：本 SPEC §N。

## 沿革與追溯索引
<!-- HISTORY-BEGIN -->
- 2026-09-15：v3 → `handoffs/reconcile/20260915-docrot2-x-review-r2/synth.md`
- 2026-09-15：v2 → `handoffs/reconcile/20260915-docrot2-x-review-r1/synth.md`
- 2026-09-15：v1 → commit `3dbc702c`
<!-- HISTORY-END -->
