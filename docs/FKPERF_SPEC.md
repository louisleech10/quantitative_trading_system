# FKPERF — fact-key 生成器：外部程序數與登記規模解耦 — SPEC

> 來源：使用者 2026-09-23 逐字「這會膨脹很快，兩三分鐘很快就更久吧，這無法接受」；偵察收據 `handoffs/run_receipts/20260923-fkperf-recon.json`（探針 `handoffs/run_receipts/fkperf_probes/`）　|　日期：2026-09-23　|　版本：v8（實作第 2 批實測：C-1 新增具名例外⑤，jq 執行期錯誤行）；v7（r1 收斂 `handoffs/reconcile/20260923-fkperf-x-review-r1/synth.md`；r2 收斂 `handoffs/reconcile/20260923-fkperf-x-review-r2/synth.md`；v4＝主委自查修訂：比例量測端點改 4×／40×；v5＝r3 收斂 `handoffs/reconcile/20260923-fkperf-x-review-r3/synth.md`：規模改以總 fact-key 數定義、端點改列待使用者確認；v6＝寫 TODO 時主委實測更正 C-5 與 Task 1.1 邊界③之 NaN 描述：jq 接受 NaN，由型別檢查拒絕；v7＝實作前主委實跑 oracle：24 處出口僅於內部 jq／awk／mktemp／mv 子程序失敗時觸發，新實作無對應分支，Task 0.1 ③不列入並機械歸類）　|　對應 TODO：`docs/manifests/FKPERF.json`（五類落點 manifest，SPEC 定案後由 TODO_GENERATION_PROMPT 生成）

## §RISK 風險分級
- **大小**：大。
- **命中高風險原則**：(b) 共用路徑——`scripts/gen_fact_key_blocks.sh` 之消費端分呼叫型與路徑字面型兩類（逐一列舉見 C-2），呼叫型皆以其 rc／stderr 作 fail-closed 判定；(c) 多 phase，切換（Phase 4）後之回退為整體 revert。
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
  - FACT-RECEIPT: `prof_spawn.sh --check`／`guard`（三家各於隔離複本重跑）→ 印出 `4317`／`4322`～`4323`，與主委收據相同；`--check` 耗時 11.2～12.25s（codex／composer／grok 實跑 2026-09-23，見 r1 收斂檔）
  - FACT-RECEIPT: `grep -rno 'gen_fact_key_blocks\.sh:[0-9][0-9-]*' docs scripts tests` → 生產引用僅 `scripts/fact_keys.json` E-028 列之 `gen_fact_key_blocks.sh:1863`（生成至 `docs/GOV_ENFORCEMENT_REGISTRY.md`、`docs/GOV_TICKET_SOT.md` 與兩組 fixture）（主委 實跑 2026-09-23）
  - FACT-RECEIPT: `printf '{"x": NaN}' | jq -e 'type == "object"'` → rc=0（jq-1.7.1-apple）；`printf '{"x": Infinity}' | jq -c .` → `{"x":1.7976931348623157e+308}`；最小沙箱 `{"x": NaN}` 經現行生成器 → rc=1 `key x 之 rows 型別不符（須為字串陣列之陣列）`（主委 實跑 2026-09-23，寫 TODO 時推翻 v5 C-5 之「jq 不接受 NaN」，收據 `handoffs/run_receipts/20260923-fkperf-todo-exit-probes.json`）
- **待確認：無**（原待確認之量測端點，已於 2026-09-23 白話審閱獲使用者確認，見下）
- **白話審閱**：`白話說明/FKPERF規格審閱.md`；使用者 2026-09-23 逐問「量測點數字不同有什麼差異」「以後會越來越大、很多地方用到會不會拖慢」，經說明後回「ok」⇒ SPEC 定案、端點依下條：
  - 量測端點取總 fact-key 數 140 與 1400（35 之 4 倍與 40 倍，仍相差 10 倍、門檻仍 20 倍），不取使用者選項說明中之 1 倍與 10 倍——主委自查：每次呼叫之固定開銷約 0.1s（`python3` 啟動 0.022s、`ticket_universe.sh --check` 0.03s，另 git 與包裝層），1×／10× 直接相除會被稀釋，r2 反例之比例僅約 13.5 倍而漏抓；grok r3 以純內容夾具實測 4×／40× 同型反例純 CPU 52 倍、含固定開銷 31 倍，且冪次成長下不存在「1×／10× 會紅而 4×／40× 不紅」之情形（此改動為收緊，非放寬）。
  - FACT-RECEIPT: `bash scripts/ticket_universe.sh --check`（計時三次）→ 印出 `0.04s`、`0.03s`、`0.03s`；`python3 -c pass` → `0.022s`（主委 實跑 2026-09-23）
- **已確認結果**：2026-09-23 使用者逐字（見下列兩則）
  - 2026-09-23 使用者逐字「這會膨脹很快，兩三分鐘很快就更久吧，這無法接受」⇒ 開票；目標＝存檔檢查之等待不隨登記規模增長。
  - 2026-09-23 使用者於 AskUserQuestion 選「比例型：規模放大 10 倍最多慢 20 倍」（兩端各量三次取最小值）⇒ C-6 ②、Task 4.4 之比例型耗時斷言，涵蓋 `--check`、`factkey_write_guard.sh`、`--status-hits`（r2 codex／composer 以「每 key 對整份註冊表做 JSON 往返」反例證明程序數與開檔數之不變性抓不到純 CPU 退化：35 key 0.024s → 350 key 2.476s）。

## §C 約束
- **C-1 行為逐位元組不變**：六種呼叫形態（emit、`--check`、`--write`、`--status-hits <行檔>`、`-h|--help`、錯誤參數），其 stdout、stderr、rc 以及寫檔後的宿主檔位元組，在 §V 差分語料上須與 oracle（Phase 4 切換前之 bash 實作，commit 寫死於 Task 0.1）逐位元組相同。**具名例外（封閉集，v8 起五項）**：①C-5 之前置條件字面（`缺 jq` → `缺 python3`）；②`TMPDIR` 不存在或不可用：oracle 因 mktemp／暫存重導向失敗而拒絕，新實作不使用暫存目錄，須照常執行且 stdout、rc、寫檔結果等於 oracle 於可用 `TMPDIR` 下之結果；③宿主寫入失敗：stderr 不比對，新實作須 rc=1 且宿主檔位元組不變；④`--status-hits` 行檔存在但不可讀：stderr 不比對，新實作須 rc=2、stdout 無命中、不改行檔；⑤（v8，實作第 2 批實測）oracle 之 jq 程式於前一驗證已失敗之資料上發生執行期錯誤時，jq 自身印出之整行 `jq: error (at <輸入檔>:<行>): <jq 內部措辭>`——輸入檔常為 `mktemp` 物化暫存檔（隨機檔名）、措辭與截斷為 jq 內部實作——比對前自 oracle stderr 刪除**恰符合** `^jq: error \(at [^\n]*\): [^\n]*$` 之整行，新實作不得印出任何此形之行，其餘各行、stdout、rc、寫檔結果照常全等（2026-09-24 主委實跑：409 筆語料中 4 筆含此行，餘 405 筆逐位元組全等）。②③④⑤各有具名測試（Task 0.1 ③）。其餘 oracle 內部子程序失敗出口依 Task 0.1 ③歸類 tool_failure、不建語料。其餘任何差異＝FAIL，新增例外須改本條並經審。
- **C-2 入口之 CLI、env、rc 語意不變**：`bash scripts/gen_fact_key_blocks.sh [mode]` 仍為唯一入口。`GOVB1_FACTKEY_ROOT` 只影響宿主查找；`rows_source` 相對註冊表所在 repo，不隨 ROOT 改變；receipt 相對 ROOT。三者語意照舊。消費端逐一列舉（分兩型）：
  - **呼叫型**（經入口，呼叫方式不改）：`scripts/factkey_write_guard.sh`（`--check`，由 `.claude/settings.json` PostToolUse 掛載）；`scripts/_live_doc_write_guard.py`（`--status-hits`，其上游為 PreToolUse `scripts/live_doc_write_guard.sh` 與 `scripts/git_hooks/pre-commit` 之 `live_doc_write_guard.sh --staged`）；`scripts/gov_check.sh` 第 3 段（`--check`）；`scripts/precommit_selfcheck.sh`（`--check`）；`scripts/regen_factkey_fixtures.sh`（`--write`）。
  - **路徑字面型**（以檔名判定，須把核心列入）：`scripts/factkey_write_guard.sh` 之 `_managed()` 受管集合；`scripts/git_hooks/pre-commit` 之遷移判定觸發式；`scripts/fact_keys.json` E-028 列之實作位置引用（行號）；`scripts/govb1_final_gate.sh` g2／g3（屬硬保護集，不改，走 Task 4.3）。前三者於 Task 4.1 加入或改指核心。
- **C-3 決定性契約不變**：唯一排序點＝整列 @tsv 後以位元組序排序（現行 `LC_ALL=C sort`）；jq `@tsv` 之跳脫（`\t` `\n` `\r` `\\`）逐位元組重現；全程 LF、無 BOM、無時間戳。fact-key 迭代序照 jq `keys[]`（碼點序），不得沿用 Python dict 插入序。手寫狀態判定（`_FK_HIT_AWK` 之 `has_token`）之 `length`／`substr` 與範圍列舉之 `\001` 換行編碼，照現行 `LC_ALL=C` awk／tr，以 UTF-8 **位元組**為單位，不得改用 Python 字元（碼點）長度。
- **C-4 fail-closed 不減**：檔頭列舉之 fail-closed 點與各 validator 之拒絕集合全數保留，不得新增 fail-open 路徑。`factkey_write_guard.sh` 既有之刻意 fail-open（其檔頭誠實邊界第 4 條）照舊。
- **C-5 執行環境**：只用標準庫；以系統 `python3`（3.9）執行，不依賴 venv。缺 `python3` ⇒ fail-closed，訊息 `gen_fact_key_blocks: 缺 python3 → fail-closed`，rc 同現行缺 jq（1）。JSON 解析須與 jq 同樣**接受** `NaN`／`Infinity`（jq 1.7.1 視為數值），不得在解析階段另行拒絕；註冊表之值須為字串，此類值由其後之型別檢查以與 oracle 相同之訊息拒絕（例：`key x 之 rows 型別不符`）。
- **C-6 效能驗收**：使用者 2026-09-22 定死「任何每次都會跑的檢查，單次必須秒級；要寫進 SPEC 的是實測秒數」。本票**新增**之驗收分三層：①決定性：emit、`--check`、`--write`、`--status-hits` 四模式之**外部程序數**與**核心開檔次數**，在 1×／4×／10×／40× 規模下相等（規模一律以**總 fact-key 數**定義：35／140／350／1400；Task 0.2／4.4）；②比例型耗時（使用者 2026-09-23 裁定，§A）：`--check`、`factkey_write_guard.sh`、`--status-hits` 於 40× 之耗時不得超過 4× 之 20 倍（兩端總 key 數恰相差 10 倍，端點選擇待使用者確認，見 §A），兩端各量三次取最小值；40× 端以「20 × 4× 端最小值」為逾時上限，逾時即判紅（Task 4.4）——擋住程序數與開檔數都不變的純 CPU 退化；③實測：四模式與 `factkey_write_guard.sh` 於四種規模之耗時寫入本 SPEC §A 與收據。既有測試 `test_generator_runs_under_two_seconds` 不屬本條新增驗收，依 C-8 不得刪除或放寬，XPASS 後移除其 strict xfail 即回復原斷言。
- **C-7 不加快取**：不得引入 sidecar、增量索引或跨呼叫快取（快取失效即新漂移來源；同債務帳本「無 sidecar 快取」原則）。
- **C-8 判定寬嚴不變**：由 C-1 語料與既有測試共同守住；既有測試之斷言不得放寬或刪除。
- **C-9 GOVB1 硬保護集不動**：`scripts/govb1_scope.manifest`、`scripts/govb1_frozen_hashes.txt`、`docs/GOVB1_*` 皆不改。g2（consumer 字面分母）與 g3（停用開關）按路徑掃描 `gen_fact_key_blocks.sh`；核心移入新檔後，這兩道對核心失效，須由 Task 4.3 對新核心施加同等檢查。
- **C-10 mutation 不失效**：耦合 bash 原始碼的 mutation 測試（收據初估：`test_govb1_factkey_gen.py` 中讀取或改寫 bash 原始碼之行 14 處，其中 `_mutate(sdir` 形式 4 處；確切清單由 Task 4.2 以 grep 列舉），改為對新核心施加**同一破壞語意**的 mutation，逐條證明改壞會紅；錨點唯一性要求（例：`test_wl01_sort_anchor_stays_unique_in_generator`）對新核心照樣成立。
- **C-11 單一判定實作**：`--status-hits` 是 `_live_doc_write_guard.py` 與全檔模式共用的唯一判定碼；移植後仍只能有一份實作，不得在 Python 核心與 `_live_doc_write_guard.py` 各留一份。
- **C-12 解耦 7 條不涉**：只動治理腳本與治理測試，不碰 `momentum/`、`api/`。

## 方案比較（主委建議；委員裁）
| 方案 | 外部程序數對 key 數 | 結論 |
|---|---|---|
| **A 核心移入單一 Python 程序**，bash 檔改薄包裝 | 與 key 數無關：`python3` 一次，另保留既有子程序（`git rev-parse`、`git ls-files`、`bash scripts/ticket_universe.sh --check`）；以規模不變性判定，不以固定個數 | **採** |
| B bash 內批次化（一次 jq 物化＋一次 awk 掃檔） | 可與 key 數無關（awk 有關聯陣列；r1 codex／grok 實證） | 否：判定散在 jq 與 awk 兩種 DSL；C-10 之 mutation 錨在巨石字串；BSD awk `-v` 拒換行之既有坑延續；與 `_live_doc_write_guard.py` 不同族，C-11 單一實作更難守 |
| C hook 只查被編輯檔 | 仍隨該檔 key 數成長（`EVENTSCAN_SPEC.md` 一檔 15 key）；改 `fact_keys.json` 本身仍須全量 | 否 |
| D 快取／增量 | — | 否（C-7） |

## §P Phase 與依賴

### Phase 0 — 基準與 oracle（依賴：無）
**Task 0.1 — 差分 harness 與語料**
- 目標：把切換前的 bash 實作凍結為 oracle，建立新舊實作逐位元組比對的 harness 與語料。
- 檔案：新建 `tests/governance/_fkperf_oracle.py`（helper）與 `tests/governance/test_fkperf_differential.py`。`ORACLE_COMMIT` 寫死於 helper，值＝實作起點 commit。
- 沙箱建法（🔴 只搬腳本 blob 會因 `REG=${SCRIPT_DIR}/fact_keys.json` 在前置檢查失敗，不得如此）：每筆語料建**兩個同形完整沙箱**——同一輸入樹（`git archive <ORACLE_COMMIT>` 或該語料之沙箱樹）＋註冊表所引用而未追蹤之 receipt 檔；oracle 沙箱之 `scripts/gen_fact_key_blocks.sh` 為 `git show <ORACLE_COMMIT>:scripts/gen_fact_key_blocks.sh`，新實作沙箱放新入口與核心；兩者皆各有 `fact_keys.json`、rows_source 來源、settings.json 與宿主檔，並各自 `git init`（語料需要時）。兩邊於相同 env、參數、stdin、相對 cwd 下各跑一次，比對 stdout、stderr、rc，以及宿主檔寫後位元組與權限位。
  - 🔴 stderr 內含沙箱絕對路徑者（例：`宿主檔與 <REG 路徑> 不一致`），比對前只准正規化「兩沙箱根目錄互換」這一種替換，規則寫死於 helper；其他正規化一律禁止。
- 既有 caller／影響面：新建，無 caller。
- 改法：每筆語料帶**預期分支標籤**＝oracle 應得之 rc 與 stderr 首行（成功分支則為 rc=0 與 stdout 首行），先斷言 oracle 命中該標籤，再比對新實作；共同前置失敗因此不能充數。語料五類：①真實 repo，六種呼叫形態各一（含 `--help`；`--help` 另以相對路徑與同目錄 symlink 呼叫入口各一筆；C-5 前置例外以「oracle 沙箱缺 jq」與「新實作沙箱缺 python3」配成一對，各自斷言其預期分支，不得以擴大正規化處理）。②既有測試建立的沙箱情境：以 `test_govb1_factkey_gen.py` 的 `_sandbox`／`_mkroot`、docrot2 測試的 `_fk_sandbox` 等 helper 建樹，逐一列入。③系統化單點破壞：檔頭 fail-closed 清單每一條、各 validator 每一個拒絕出口，各至少一例；出口清單以現行函式之每個 `return 1`／`_fk_die`／`exit` 逐一列舉並附對應 oracle 之 stderr 首行；唯 oracle 內部子程序（jq／awk／mktemp）自身失敗之出口（v7 補：新實作不呼叫這些子程序，無對應分支）不列入、不建語料，以測試內封閉字面集機械歸類並釘數量（2026-09-24 主委實跑 oracle：24 處；其中 L218 可由 TMPDIR 不可用、L2035 可由宿主目錄唯讀觸發，但 oracle 之 stderr 首行為子程序／bash 自身訊息且含隨機字尾或 PID，本質不可逐位元組比對）。行為例外見 C-1 ②③④，各以具名測試驗收：`test_new_impl_tmpdir_unusable_still_succeeds`、`test_new_impl_host_write_failure_is_fail_closed`、`test_new_impl_unreadable_status_hits_file_rc2`；tool_failure 之 24 行以完整行號清單釘死（r11 codex）。④鍵序：一份以非排序插入序寫成之註冊表（C-3）。⑤位元組語意：狀態識別碼含三位元組 UTF-8 字元一筆，左右鄰分別為屬與不屬 `A-Za-z0-9_-` 之字元（C-3）。
- **驗證**（`pytest tests/governance/test_fkperf_differential.py` 全綠，含下列四項）：
  - `pytest tests/governance/test_fkperf_differential.py -k oracle_self` ⇒ oracle 對 oracle 差異 0，且其中至少一筆為真實 repo 之 `--check` rc=0（證明沙箱完整）；
  - 每筆語料之 oracle 命中其預期分支標籤（斷言）；
  - mutation：新實作 stub 輸出多一個位元組 ⇒ 該語料項報差異、測試紅；
  - 出口清單與語料之分支標籤集合相等（少列一個出口或多一個無主語料即紅）。
- **邊界**：①沙箱缺 rows_source 來源、receipt 或 settings.json ⇒ 兩實作同樣 fail-closed，比對照常成立。②`--status-hits` 以行檔輸入，行內含 TAB 或 `\001` 編碼換行 ⇒ 照樣比對。③非 git 的 ROOT ⇒ 兩實作同樣 fail-closed。
- **存活至**：本票完工後保留，作為回歸防線。
- **覆蓋風險**：Phase 4 刪除 bash 實作後，oracle 改以 git blob 取得，不受影響。
- 不可做：不得把 oracle 輸出存成預期檔來取代實跑 oracle（等於另立一份會過期的副本）；不得為了讓比對通過而擴大正規化範圍。

**Task 0.2 — 規模探針**
- 目標：可重用的外部程序計數與開檔計數 helper，加上合成規模註冊表。
- 檔案：新建 `tests/governance/_fkperf_spawn.py`（PATH shim 計數，工具集合同收據另加 `bash`；shim 以真實路徑 `exec`，不得對 builtin 名稱建 shim——r1 grok 實測 `printf` shim 會使 emit 早退）；新建 `tests/governance/_fkperf_opens.py`（以子程序 `python3` 啟動，先 `sys.addaudithook` 計 `open` 事件，再以 `runpy.run_path` 執行核心；只計 ROOT 與註冊表所在 repo 之下的路徑）；新建 `tests/governance/test_fkperf_scale.py`。
- 既有 caller／影響面：新建，無 caller。
- 改法：規模一律以**總 fact-key 數**定義：1×＝真實註冊表（35）、4×＝140、10×＝350、40×＝1400。以真實註冊表為底，只複製純內容 key（`FACTKEY-CONTENT` 宣告者）並改名（改名規則寫死；非內容 key 不複製，否則 schema 清單指向改名 key，`--check` 不能 rc=0）：整份複製不足之餘數，依 `keys[]` 序取純內容 key 之前 k 個補足，使總數恰等於目標；測試先斷言各規模之總 key 數等於目標值、且 40×／4× 之總數比恰為 10。宿主區塊以 `--write` 物化。本 Task 於現行（bash）實作下只量 1×／4×／10× 之外部程序數作基準（40× 於現行實作約需數分鐘，不量）；40× 與核心開檔次數於 Task 4.4 切換後才量。規模不變性斷言在 Phase 4 之前以 `xfail(strict=True)` 標記。
- **驗證**：①helper 自測：shim 計數等於實際呼叫次數、開檔計數等於已知開檔數（各以已知次數之小腳本驗證）；②基準記錄：現行實作下 1× 的 `--check` 程序數與收據 4317 相同，且 4× 大於 1×（證明探針有鑑別力）。
- **邊界**：①10× 規模 key 名稱須合 `_schema.key_pattern`；②合成 key 不得與既有 key 或狀態識別碼撞名。
- **存活至**：本票完工後保留。
- **覆蓋風險**：Task 4.4 移除 xfail 標記，不刪檔。
- 不可做：不以實測秒數作斷言（C-6）。

### Phase 1 — Python 核心：資料路徑（依賴：Phase 0）
**Task 1.1 — 核心骨架、載入與基本驗證**
- 目標：新建 `scripts/_gen_fact_key_blocks.py`（下稱核心），涵蓋 preflight、keys、shape、rows、schema sets、rows_source／rows_filter 物化，與對應之 fail-closed 訊息。
- 既有 caller／影響面：新建。本 Phase 不接入入口，只由差分測試直呼。
- 改法：以 bash 各函式（`_fk_preflight`、`_fk_validate_keys`、`_fk_validate_shape`、`_fk_validate_rows`、`_fk_validate_schema_sets`、`_fk_materialize`、`_fk_rows_source_rows`、`_fk_rows_filter_rows`）為規格逐條移植；訊息字串逐字照抄。
- **驗證**：差分語料中屬本 Task 分支者全等；`pytest tests/governance/test_fkperf_differential.py -k phase1` 全綠；核心之 fact-key 迭代序＝`jq -r 'keys[]'` 之序，以語料④（非排序插入序之註冊表）驗證。
- **邊界**：①空註冊表 ⇒ rc=0 契約不變（`test_empty_registry_is_rc_zero_not_failure`）；②rows_filter 序號位數溢位 ⇒ 同訊息 fail-closed；③註冊表含 `NaN` 字面 ⇒ 與 oracle 同訊息 fail-closed（由 rows 型別檢查拒絕，非解析失敗；C-5）。
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
- **邊界**：①檔名含換行 ⇒ 與 oracle 同判；②非 git 的 ROOT ⇒ 同訊息 fail-closed；③識別碼邊界（如 `B3RB3R`）⇒ 同判；④識別碼含多位元組字元、鄰接字元屬或不屬 `A-Za-z0-9_-` ⇒ 與 oracle 同判（語料⑤，C-3 位元組語意）。
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
- 目標：`scripts/gen_fact_key_blocks.sh` 改為薄包裝：檢查 `python3` 存在（缺 ⇒ C-5 訊息，rc=1），隨後 `exec python3 <核心> "$@"`；C-2 路徑字面型消費端同步改指核心。
- 既有 caller／影響面：C-2 所列呼叫型消費端（呼叫方式不變）與路徑字面型消費端（本 Task 更新）。
- 改法：以單一 commit 切換（§R）：
  - 入口檔第 2–20 行（`--help` 之輸出來源）**原文保留**；指向核心之說明自第 21 行起；bash 中已移入核心之函式刪除。核心於 preflight 之後讀入口檔第 2–20 行輸出，次序同 oracle（缺註冊表時 `--help` 仍先報前置失敗）。
  - `scripts/factkey_write_guard.sh` 之 `_managed()` 加入 `scripts/_gen_fact_key_blocks.py`（與既有入口行並列）。
  - `scripts/git_hooks/pre-commit` 之遷移判定觸發式加入 `_gen_fact_key_blocks\.py`。
  - `scripts/fact_keys.json` E-028 列之實作位置由 `scripts/gen_fact_key_blocks.sh:1863` 改指核心中對應判定之行，並以 `--write` 重生成 `docs/GOV_ENFORCEMENT_REGISTRY.md`、`docs/GOV_TICKET_SOT.md`；兩組 fixture（`factkey_clean`／`factkey_drifted`）之同一引用照 `scripts/regen_factkey_fixtures.sh` 既有流程更新。
- **驗證**：差分語料對入口全等（只允許 C-1 那一條例外；`--help` 逐位元組相同）；C-2 呼叫型消費端各自的既有測試全綠；「只改核心」之正反測試：①核心被改壞（例：寫入 `raise RuntimeError`）後，以核心路徑呼叫 `bash scripts/factkey_write_guard.sh scripts/_gen_fact_key_blocks.py` ⇒ rc≠0（修前 r1 反例為 rc=0）；②暫存區只含核心之 commit ⇒ pre-commit 遷移判定被觸發；③還原後兩者 rc=0；E-028 引用經 `--check` 之實作位置驗證 rc=0。
- **邊界**：①`PATH` 中無 `python3` ⇒ rc=1 與 C-5 訊息；②以 `bash -n` 檢查包裝器語法；③E-028 引用指到核心之註解行 ⇒ 既有「引用指向註解行即拒」判定照樣擋。
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
- 目標：證明外部程序數與核心開檔次數皆與登記規模無關，並把實測秒數寫進 SPEC（C-6）。
- 既有 caller／影響面：`tests/governance/test_fkperf_scale.py`（Task 0.2）。
- 改法：移除規模不變性斷言的 xfail 標記；把實測秒數回填 §A。
- **驗證**：1×／4×／10×／40× 四種規模下，emit、`--check`、`--write`、`--status-hits` 各自的外部程序數相等、核心開檔次數相等；`factkey_write_guard.sh HANDOFF.md` 的程序數與規模無關。比例型耗時斷言（C-6 ②）：`--check`、`factkey_write_guard.sh`、`--status-hits` 各自 `min(40× 三次) <= 20 * min(4× 三次)`，40× 單次逾時上限＝`20 * min(4× 三次)`，逾時即判紅。四模式與 guard 於四種規模之耗時（各取三次）寫入收據 `handoffs/run_receipts/<日期>-fkperf-scale.json`，並回填 §A 為 FACT-RECEIPT。既有 `test_generator_runs_under_two_seconds` 之 R-GOVTEST-5 strict xfail 轉為 XPASS ⇒ 移除標記、回復原斷言（C-6、C-8），並關閉 `docs/IC_QUANT_GAP_REGISTRY.md` 的 R-GOVTEST-5 列。
- **邊界**：①10× 與 40× 規模下 `--check` rc=0；②合成 key 被 `FACTKEY-CONTENT` 宣告測試拒收 ⇒ 合成註冊表只在 tmp 沙箱內使用，不寫入真實註冊表；③每 key 迴圈內新增一次讀檔之 mutation ⇒ 開檔次數之規模不變性斷言紅；④每 key 迴圈內對整份註冊表做一次 `json.loads(json.dumps(...))` 之 mutation ⇒ 比例型耗時斷言紅（r2 反例；grok r3 以純內容夾具實測 4×／40× 純 CPU 約 52 倍、含固定開銷約 31 倍，並須在逾時上限內判紅而非等其跑完）；⑤合成規則誤把非內容 key 一併複製，或總數比不等於 10 ⇒ 規模斷言先紅。
- **存活至**：本票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得另訂或放寬比例門檻（10 倍規模差、20 倍時間門檻、各取三次最小值為使用者裁定，見 §A；端點改動須經審）；不加絕對秒數斷言。

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
- **邊界目錄**：空註冊表（Task 1.1）／非 git ROOT（Task 2.1）／檔名含換行（Task 2.1）／控制字元與 `|`（Task 1.2）／大規模 10×、40×（總 fact-key 數 350、1400；Task 4.4）／缺 python3（Task 4.1）／`--write` 寫檔語意（Task 1.2）／非排序插入之鍵序（Task 1.1）／多位元組識別碼（Task 2.1）／`--help` 位元組與前置次序（Task 4.1）／只改核心之產出端與 pre-commit 觸發（Task 4.1）。

## §R 回退
- Phase 0–3 不接入入口（核心只由測試直呼），各 Phase 可單獨 revert。
- Phase 4 之切換為單一 commit，revert 該 commit 即回到 bash 實作。
- 不設 feature flag：雙實作常駐即雙倍漂移面（Task 4.1 不可做）。

## §N N/A 登記
- **§G**：N/A——RISK-HIT 不含 a／d，不碰數值與 ML；「行為不變」由差分語料（C-1）取代 golden。
- **殘留**：無。hook 改為只查被編輯檔（方案 C）不是殘留，而是否決的方案：核心達到 O(1) 程序數後，全量檢查已不隨規模增長。
