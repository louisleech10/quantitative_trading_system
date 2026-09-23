# FKPERF — fact-key 生成器：外部程序數與登記規模解耦 — SPEC

> 來源：使用者 2026-09-23 逐字「這會膨脹很快，兩三分鐘很快就更久吧，這無法接受」；偵察收據 `handoffs/run_receipts/20260923-fkperf-recon.json`（探針 `handoffs/run_receipts/fkperf_probes/`）　|　日期：2026-09-23　|　對應 TODO：`docs/manifests/FKPERF.json`（五類落點 manifest，SPEC 定案後由 TODO_GENERATION_PROMPT 生成）

## §RISK 風險分級
- **大小**：大。
- **命中高風險原則**：(b) 共用路徑——`scripts/gen_fact_key_blocks.sh` 有 8 個消費端（PostToolUse 產出端 hook、PreToolUse `--status-hits`、pre-commit、`precommit_selfcheck`、`gov_check` 第 3 段、`regen_factkey_fixtures`、`govb1_final_gate` g2／g3 掃描、`settings.json` 掛載），皆以其 rc／stderr 作 fail-closed 判定；(c) 多 phase，切換（Phase 4）後之回退為整體 revert。
- **RISK-HIT 宣告**（機檢依據）：
RISK-HIT: b,c

## §A 假設與待使用者確認
- **已驗證事實**（8 條 FACT-RECEIPT）：
  - FACT-RECEIPT: `bash scripts/factkey_write_guard.sh HANDOFF.md`（計時）→ 印出 `rc=0 10.3s`；`白話說明/現在做到哪.md` 10.2s；`docs/EVENTSCAN_SPEC.md` 10.5s；`momentum/factories.py` 0.0s（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `bash scripts/gen_fact_key_blocks.sh --check`（計時兩次）→ 印出 `10.73s`、`10.55s`；無參數 emit 三次 → `2.53s`、`2.45s`、`2.45s`（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `bash handoffs/run_receipts/fkperf_probes/prof_spawn.sh guard` → 印出 `total external calls: 4322`（jq 1417／tr 882／wc 842／grep 555／sort 466／awk 99／sed 52／git 2）；`… --check` → `4317`；`… emit` → `664`（jq 438）（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `bash handoffs/run_receipts/fkperf_probes/prof_func.sh` → 印出前六 `315 _fk_reject_handwritten_status grep`／`160 _fk_targets jq`／`142 _fk_targets wc`／`142 _fk_targets tr`／`76 _fk_markers_ok grep`／`71 _fk_targets sort`（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `git show 9ce175c2:scripts/fact_keys.json | jq 'keys|length'` → 印出 `18`；`jq 'keys|length' scripts/fact_keys.json` → 印出 `36`（皆含 `_schema`；fact-key 17→35，2026-09-19→23）（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `bash --version | head -1` → 印出 `GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)`（無關聯陣列 ⇒ 逐 key 狀態只能重查 jq）（主委 實跑 2026-09-23）
  - FACT-RECEIPT: PreToolUse `live_doc_write_guard.sh` 以 Edit HANDOFF.md payload 計時 → 印出 `rc=0 0.1s`（判定核心為 Python `_live_doc_write_guard.py`）（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `grep -n '缺 jq\|without_jq\|shutil.which("jq")' tests/governance/test_govb1_factkey_*.py tests/governance/test_docrot2_*.py` → 印出空（無測試守「缺 jq」行為）（主委 實跑 2026-09-23）
- **待確認：無**
- **已確認結果**：2026-09-23 使用者逐字「這會膨脹很快，兩三分鐘很快就更久吧，這無法接受」⇒ 開票；目標＝存檔檢查之等待不隨登記規模增長。

## §C 約束
- **C-1 行為逐位元組不變**：六種呼叫形態（emit、`--check`、`--write`、`--status-hits <行檔>`、`-h|--help`、錯誤參數），其 stdout、stderr、rc 以及寫檔後的宿主檔位元組，在 §V 差分語料上須與 oracle（Phase 4 切換前之 bash 實作，commit 寫死於 Task 0.1）逐位元組相同。**唯一具名例外**＝C-5 之前置條件字面（`缺 jq` → `缺 python3`）。其餘任何差異＝FAIL，新增例外須改本條並經審。
- **C-2 入口與 env 語意不變**：`bash scripts/gen_fact_key_blocks.sh [mode]` 仍為唯一入口，8 個消費端呼叫方式不改。`GOVB1_FACTKEY_ROOT` 只影響宿主查找；`rows_source` 相對註冊表所在 repo，不隨 ROOT 改變；receipt 相對 ROOT。三者語意照舊。
- **C-3 決定性契約不變**：唯一排序點＝整列 @tsv 後以位元組序排序（現行 `LC_ALL=C sort`）；jq `@tsv` 之跳脫（`\t` `\n` `\r` `\\`）逐位元組重現；全程 LF、無 BOM、無時間戳。`keys[]` 之序照 jq（碼點序），不得沿用 Python dict 插入序。
- **C-4 fail-closed 不減**：檔頭列舉之 fail-closed 點與各 validator 之拒絕集合全數保留，不得新增 fail-open 路徑。`factkey_write_guard.sh` 既有之刻意 fail-open（其檔頭誠實邊界第 4 條）照舊。
- **C-5 執行環境**：只用標準庫；以系統 `python3`（3.9）執行，不依賴 venv。缺 `python3` ⇒ fail-closed，訊息 `gen_fact_key_blocks: 缺 python3 → fail-closed`，rc 同現行缺 jq（1）。JSON 解析須拒 `NaN`／`Infinity` 等 jq 不接受之字面，與現行「非合法 JSON 物件 → fail-closed」同判。
- **C-6 效能驗收不設秒數門檻**：遵使用者定死之「新閘禁固定秒數門檻」，本票效能驗收以**外部程序數之規模不變性**判定（決定性）；實測耗時只作收據。
- **C-7 不加快取**：不得引入 sidecar、增量索引或跨呼叫快取（快取失效即新漂移來源；同債務帳本「無 sidecar 快取」原則）。
- **C-8 判定寬嚴不變**：由 C-1 語料與既有測試共同守住；既有測試之斷言不得放寬或刪除。
- **C-9 GOVB1 硬保護集不動**：`scripts/govb1_scope.manifest`、`scripts/govb1_frozen_hashes.txt`、`docs/GOVB1_*` 皆不改。g2（consumer 字面分母）與 g3（停用開關）按路徑掃描 `gen_fact_key_blocks.sh`；核心移入新檔後，這兩道對核心失效，須由 Task 4.3 對新核心施加同等檢查。
- **C-10 mutation 不失效**：耦合 bash 原始碼的 mutation 測試（收據初估：`test_govb1_factkey_gen.py` 中讀取或改寫 bash 原始碼之行 14 處，其中 `_mutate(sdir` 形式 4 處；確切清單由 Task 4.2 以 grep 列舉），改為對新核心施加**同一破壞語意**的 mutation，逐條證明改壞會紅；錨點唯一性要求（例：`test_wl01_sort_anchor_stays_unique_in_generator`）對新核心照樣成立。
- **C-11 單一判定實作**：`--status-hits` 是 `_live_doc_write_guard.py` 與全檔模式共用的唯一判定碼；移植後仍只能有一份實作，不得在 Python 核心與 `_live_doc_write_guard.py` 各留一份。
- **C-12 解耦 7 條不涉**：只動治理腳本與治理測試，不碰 `momentum/`、`api/`。

## 方案比較（主委建議；委員裁）
| 方案 | 外部程序數對 key 數 | 結論 |
|---|---|---|
| **A 核心移入單一 Python 程序**，bash 檔改薄包裝 | O(1)：`python3` 一次；`--check` 另 `git ls-files` 一次 | **採** |
| B bash 內批次化 jq | 仍 O(key)：bash 3.2 無關聯陣列，逐 key 狀態須重查 | 否 |
| C hook 只查被編輯檔 | 仍隨該檔 key 數成長（`EVENTSCAN_SPEC.md` 一檔 15 key）；改 `fact_keys.json` 本身仍須全量 | 否 |
| D 快取／增量 | — | 否（C-7） |

## §P Phase 與依賴

### Phase 0 — 基準與 oracle（依賴：無）
**Task 0.1 — 差分 harness 與語料**
- 目標：把切換前的 bash 實作凍結為 oracle，建立新舊實作逐位元組比對的 harness 與語料。
- 檔案：新建 `tests/governance/_fkperf_oracle.py`（helper：`git show <ORACLE_COMMIT>:scripts/gen_fact_key_blocks.sh` 取至 tmp；兩實作於相同 env、cwd、參數、stdin 下各跑一次，比對 stdout、stderr、rc 與宿主檔寫前寫後位元組）；新建 `tests/governance/test_fkperf_differential.py`。`ORACLE_COMMIT` 寫死於 helper，值＝實作起點 commit。
  - 🔴 oracle 之 stderr 內含其所在路徑者（例：`宿主檔與 <REG 路徑> 不一致`），比對前只准正規化「oracle 暫存路徑 ↔ 真實路徑」這一種替換，替換規則寫死於 helper；其他正規化一律禁止。
- 既有 caller／影響面：新建，無 caller。
- 改法：語料三類。①真實 repo，六種呼叫形態各一。②既有測試建立的沙箱情境：以 `test_govb1_factkey_gen.py` 的 `_sandbox`／`_mkroot`、docrot2 測試的 `_fk_sandbox` 等 helper 建樹，逐一列入。③系統化單點破壞：檔頭 fail-closed 清單每一條、各 validator 每一個拒絕分支，各至少一例；分支清單由 Task 0.1 列舉並附對應 oracle 之 stderr 首行。
- **驗證**（`pytest tests/governance/test_fkperf_differential.py` 全綠，含下列三項）：
  - `pytest tests/governance/test_fkperf_differential.py -k oracle_self` ⇒ oracle 對 oracle，差異 0；
  - mutation：新實作 stub 輸出多一個位元組 ⇒ 該語料項報差異、測試紅；
  - 語料清單數 ≥ 分支清單數，且每一分支都有對應語料（集合相等斷言）。
- **邊界**：①沙箱缺 rows_source 來源、receipt 或 settings.json ⇒ 兩實作同樣 fail-closed，比對照常成立。②`--status-hits` 以行檔輸入，行內含 TAB 或 `\001` 編碼換行 ⇒ 照樣比對。③非 git 的 ROOT ⇒ 兩實作同樣 fail-closed。
- **存活至**：本票完工後保留，作為回歸防線。
- **覆蓋風險**：Phase 4 刪除 bash 實作後，oracle 改以 git blob 取得，不受影響。
- 不可做：不得把 oracle 輸出存成預期檔來取代實跑 oracle（等於另立一份會過期的副本）；不得為了讓比對通過而擴大正規化範圍。

**Task 0.2 — 規模探針**
- 目標：可重用的外部程序計數 helper，加上合成規模註冊表。
- 檔案：新建 `tests/governance/_fkperf_spawn.py`（PATH shim 計數，工具集合同收據）；新建 `tests/governance/test_fkperf_scale.py`。
- 既有 caller／影響面：新建，無 caller。
- 改法：以真實註冊表為底，將純內容 key（`FACTKEY-CONTENT` 宣告者）複製為 1×、4×、10× 並改名（改名規則寫死），其宿主區塊以 `--write` 物化；於三種規模量測 emit、`--check`、`--write` 的外部程序數。規模不變性斷言在 Phase 4 之前以 `xfail(strict=True)` 標記。
- **驗證**：①helper 自測：shim 計數等於實際呼叫次數（以已知呼叫數之小腳本驗證）；②基準記錄：現行實作下 1× 的 `--check` 程序數與收據 4317 同量級，且 4× 大於 1×（證明探針有鑑別力）。
- **邊界**：①10× 規模 key 名稱須合 `_schema.key_pattern`；②合成 key 不得與既有 key 或狀態識別碼撞名。
- **存活至**：本票完工後保留。
- **覆蓋風險**：Task 4.4 移除 xfail 標記，不刪檔。
- 不可做：不以實測秒數作斷言（C-6）。

### Phase 1 — Python 核心：資料路徑（依賴：Phase 0）
**Task 1.1 — 核心骨架、載入與基本驗證**
- 目標：新建 `scripts/_gen_fact_key_blocks.py`（下稱核心），涵蓋 preflight、keys、shape、rows、schema sets、rows_source／rows_filter 物化，與對應之 fail-closed 訊息。
- 既有 caller／影響面：新建。本 Phase 不接入入口，只由差分測試直呼。
- 改法：以 bash 各函式（`_fk_preflight`、`_fk_validate_keys`、`_fk_validate_shape`、`_fk_validate_rows`、`_fk_validate_schema_sets`、`_fk_materialize`、`_fk_rows_source_rows`、`_fk_rows_filter_rows`）為規格逐條移植；訊息字串逐字照抄。
- **驗證**：差分語料中屬本 Task 分支者全等；`pytest tests/governance/test_fkperf_differential.py -k phase1` 全綠。
- **邊界**：①空註冊表 ⇒ rc=0 契約不變（`test_empty_registry_is_rc_zero_not_failure`）；②rows_filter 序號位數溢位 ⇒ 同訊息 fail-closed。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改任何 validator 的接受集合；不合併或改寫訊息字串。

**Task 1.2 — 生成與寫入**
- 目標：emit（tsv／table render、唯一排序點）與 `--write`（標記檢查、區塊替換）。
- 既有 caller／影響面：同 Task 1.1。
- 改法：唯一排序點以 `bytes` 排序整列 @tsv 字串（C-3），且在核心中只能有一處。`--write` 之寫檔語意照 oracle（`_fk_write`）：於宿主檔同目錄寫暫存檔 `<宿主>.factkey.<pid>`（區塊暫存 `<宿主>.factkey-blk.<pid>`），完成後 rename 覆蓋宿主；寫後權限位隨 umask，與 oracle 相同。
- **驗證**：差分語料 emit／`--write` 全等（含寫後宿主檔位元組與權限位、同目錄無殘留暫存檔）；`test_t21_d1_deterministic_three_runs_identical`、`test_output_has_no_bom_no_crlf_no_timestamp` 之判準對核心直呼亦成立。
- **邊界**：①儲存格含控制字元或 `|` ⇒ 同訊息 fail-closed；②兩列只差大小寫 ⇒ 排序與 oracle 相同（C collation）。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不引入 locale 相依排序（`sorted()` 以 str 直接比較亦須證明與 bytes 序相同，否則一律用 bytes）。

### Phase 2 — `--check` 宿主檢查（依賴：Phase 1）
**Task 2.1 — 範圍列舉與宿主檢查**
- 目標：`_fk_scope_files`（`git ls-files --cached --others --exclude-standard -z` 單次、`\001` 換行編碼語意）、`_fk_markers_ok`、`_fk_reject_unregistered_blocks`、區塊漂移比對與訊息、`_fk_reject_rc_claims_outside_blocks`、`_fk_reject_handwritten_status`（`_FK_HIT_AWK` 語意）、`--status-hits`。
- 既有 caller／影響面：`--status-hits` 為 `_live_doc_write_guard.py` 所用（C-11）。
- 改法：判定碼移入核心，是唯一實作；`--status-hits` 由核心提供；`_live_doc_write_guard.py` 呼叫路徑不改（C-2）。
- **驗證**：差分語料全等；`tests/governance/test_docrot2_write_guard.py`、`test_docrot2_metrics.py` 以直呼核心方式照跑全綠。
- **邊界**：①檔名含換行 ⇒ 與 oracle 同判；②非 git 的 ROOT ⇒ 同訊息 fail-closed；③識別碼邊界（如 `B3RB3R`）⇒ 同判。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不擴大或縮小掃描範圍（status_scope、豁免清單之字首語義照舊）。

### Phase 3 — 語意驗證器（依賴：Phase 1）
**Task 3.1 — 判準與機制**
- 目標：移植 `_fk_validate_criteria`、`_fk_validate_mechanism`（含 receipt 存在性，receipt 相對 ROOT）、`_fk_reject_unregistered_mechanisms`、`_fk_registered_tokens`。
- 既有 caller／影響面：同 Phase 1。
- 改法：逐函式移植，訊息逐字照抄。
- **驗證**：差分語料中屬本 Task 分支者全等；`test_govb1_factkey_gen.py` 判準與機制相關測試對核心直呼全綠。
- **邊界**：①receipt 路徑不存在 ⇒ 同訊息 fail-closed；②同範圍同條件相異期望 ⇒ 同判拒絕。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `_schema` 任何欄位語意。

**Task 3.2 — 產出端覆蓋**
- 目標：移植 `_fk_validate_enforcement`（含 settings.json 掛載機械對證 `_fk_mount_exists`、`enforcement_ticket_allowlist`、`_fk_has_closed_ticket`）與 `_fk_validate_ticket_universe`。
- 既有 caller／影響面：同 Phase 1。
- 改法：逐函式移植，訊息逐字照抄；掛載對證讀 `_schema.enforcement_settings_path` 所指之檔。
- **驗證**：差分語料中屬本 Task 分支者全等；`test_govb1_factkey_gen.py` 的 s1x／s2x／s6x 系列（收案綁定、掛載對證、引用行驗證）對核心直呼全綠。
- **邊界**：①settings.json 缺失而目錄存在 ⇒ 同訊息 fail-closed；②引用指向註解行 ⇒ 同判拒絕。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改掛載對證之比對方式；不擴大 `enforcement_ticket_allowlist`。

**Task 3.3 — DOCROT2 狀態與交接投影**
- 目標：移植 `_fk_validate_docrot2_status`、`_fk_validate_handoff_projection`。
- 既有 caller／影響面：同 Phase 1。
- 改法：逐函式移植，訊息逐字照抄。
- **驗證**：差分語料中屬本 Task 分支者全等；`tests/governance/test_docrot2_registry.py`、`test_docrot2_migration.py` 以直呼核心方式全綠。
- **邊界**：①同一識別碼出現在兩個狀態鍵 ⇒ 同訊息 fail-closed；②B9 與 B9A 之識別碼邊界 ⇒ 同判。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `docrot2_status_values` 之集合。

### Phase 4 — 切換與收尾（依賴：Phase 2、Phase 3）
**Task 4.1 — 入口切換**
- 目標：`scripts/gen_fact_key_blocks.sh` 改為薄包裝：檢查 `python3` 存在（缺 ⇒ C-5 訊息，rc=1），隨後 `exec python3 <核心> "$@"`。
- 既有 caller／影響面：8 個消費端（C-2），呼叫方式不變。
- 改法：以單一 commit 切換（§R）；bash 中已移入核心的函式在本 Task 刪除；檔頭改為指向核心。
- **驗證**：差分語料對入口全等（只允許 C-1 那一條例外）；8 個消費端各自的既有測試全綠。
- **邊界**：①`PATH` 中無 `python3` ⇒ rc=1 與 C-5 訊息；②以 `bash -n` 檢查包裝器語法。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不保留 bash 實作作為常駐備援或切換旗標（雙實作即雙倍漂移面；回退走 git revert，見 §R）。

**Task 4.2 — mutation 重定向**
- 目標：C-10 所列耦合 bash 原始碼的 mutation，改為對核心施加同一破壞語意。
- 既有 caller／影響面：`tests/governance/test_govb1_factkey_gen.py` 等引用 `gen_fact_key_blocks` 的 10 個測試檔，其中耦合原始碼者逐一列舉。
- 改法：每一處 mutation 列出「原破壞語意 → 核心中之對應錨點」對照表，放在測試檔內；錨點唯一性測試改掃核心。
- **驗證**：對照表每一列之 mutation 對核心實跑 pytest 必紅（rc≠0），還原後 rc=0；逐列收據寫入 `handoffs/run_receipts/<日期>-fkperf-mutation.json`；對照表之耦合處集合＝Task 4.2 以 `grep -n` 對 `tests/governance/*.py` 列舉之讀寫 bash 原始碼行之集合（集合相等，少一處即 FAIL）。
- **邊界**：①錨點在核心中出現兩次 ⇒ 唯一性測試紅；②mutation 使核心語法錯誤 ⇒ 不算有效 mutation，須先過 `python3 -m py_compile`。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得刪除任何 mutation 測試；對應不到的，改寫破壞語意而非刪除，且須在對照表說明。

**Task 4.3 — GOVB1 g2／g3 同等檢查**
- 目標：C-9 的缺口：對核心施加字面分母（量詞集合）與停用開關樣式檢查。
- 既有 caller／影響面：新增測試；不改 `govb1_final_gate.sh`、manifest 與 frozen hashes。
- 改法：新測試讀取 `scripts/govb1_final_gate.sh` 的 `_G2_UNITS` 定義行，以及 g3 樣式字面作為單一來源（不另抄一份），對核心檔施加相同判定。
- **驗證**：核心中注入 `18 份` ⇒ 紅；注入 `WARN_ONLY` ⇒ 紅；還原 ⇒ 綠。
- **邊界**：①`_G2_UNITS` 定義行格式改變 ⇒ 測試 fail-closed（找不到定義），不得靜默跳過；②註解中的字面照 g2 現行語意計入。
- **存活至**：GOVB1 epic 復工、manifest 納入核心之前。
- **覆蓋風險**：GOVB1 復工若將核心加入 manifest，本測試可退役（須該票明列）。
- 不可做：不改硬保護集（C-9）。

**Task 4.4 — 規模驗收**
- 目標：證明外部程序數與登記規模無關。
- 既有 caller／影響面：`tests/governance/test_fkperf_scale.py`（Task 0.2）。
- 改法：移除規模不變性斷言的 xfail 標記。
- **驗證**：1×／4×／10× 三種規模下，emit、`--check`、`--write` 各自的外部程序數相等；`factkey_write_guard.sh HANDOFF.md` 的程序數與規模無關。實測耗時寫入收據 `handoffs/run_receipts/<日期>-fkperf-scale.json`，不作斷言。`test_generator_runs_under_two_seconds` 的 R-GOVTEST-5 strict xfail 轉為 XPASS ⇒ 移除標記，並關閉 `docs/IC_QUANT_GAP_REGISTRY.md` 的 R-GOVTEST-5 列。
- **邊界**：①10× 規模下 `--check` rc=0；②合成 key 被 `FACTKEY-CONTENT` 宣告測試拒收 ⇒ 合成註冊表只在 tmp 沙箱內使用，不寫入真實註冊表。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不以秒數作斷言（C-6）。

**Task 4.5 — 收尾驗收**
- 目標：受影響測試與差分語料全綠；全套 `pytest tests/governance` 背景跑一次（本票動共用控制流，符合 CLAUDE.md 全套條件），與 `4bdc2d56` 之基線（0 紅）逐名比對。
- 既有 caller／影響面：無新增。
- 改法：無程式改動，只跑驗收並寫收據。
- **驗證**：新增紅＝0；收據 `handoffs/run_receipts/<日期>-fkperf-govsuite.json`。
- **邊界**：①既有 strict xfail（R-GOVTEST-1／3／4、R-G7-OFF-2）不得意外轉 XPASS；②`restore_golden_inventory.sh` 還原後，工作區除本票檔外無殘留改動。
- **存活至**：本票完工（驗收步驟，產出只有收據）。
- **覆蓋風險**：無。
- 不可做：不在全套跑的過程中動檔（CLAUDE.md 坑段）。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用。RISK-HIT 雖不含 a／d，但本票宣稱「行為不變」，須可證偽：差分 harness 自身須過 mutation（Task 0.1），既有 mutation 對核心重定向（Task 4.2）。
- **測試層級**：差分（Task 0.1，主防線）；既有單元與整合測試（直呼核心，以及切換後經入口）；規模（Task 0.2／4.4）；全套（Task 4.5）。全部可用 `pytest tests/governance/...` 獨立跑，不需 `run_api.py`。
- **防假綠**：diff 既有測試斷言，不得放寬或刪除；差分比對之正規化只准 Task 0.1 那一種。
- **邊界目錄**：空註冊表（Task 1.1）／非 git ROOT（Task 2.1）／檔名含換行（Task 2.1）／控制字元與 `|`（Task 1.2）／大規模 10×（Task 4.4）／缺 python3（Task 4.1）／`--write` 寫檔語意（Task 1.2）。

## §R 回退
- Phase 0–3 不接入入口（核心只由測試直呼），各 Phase 可單獨 revert。
- Phase 4 之切換為單一 commit，revert 該 commit 即回到 bash 實作。
- 不設 feature flag：雙實作常駐即雙倍漂移面（Task 4.1 不可做）。

## §N N/A 登記
- **§G**：N/A——RISK-HIT 不含 a／d，不碰數值與 ML；「行為不變」由差分語料（C-1）取代 golden。
- **殘留**：無。hook 改為只查被編輯檔（方案 C）不是殘留，而是否決的方案：核心達到 O(1) 程序數後，全量檢查已不隨規模增長。
