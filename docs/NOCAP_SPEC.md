# NOCAP 全專案移除運算時間上限、卡死以進度判定並留現場 — SPEC

> 版本：v1（2026-10-27；初稿）　|　來源：使用者 2026-10-27 裁定（逐字見 §A）、盤點收據 `handoffs/run_receipts/20261027-nocap-inventory.md`　|　日期：2026-10-27　|　對應 TODO：`docs/manifests/NOCAP.json`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（跨 scripts／momentum／api／tests 與共用監看；多 phase）。
- **命中高風險原則**：(b) 跨模組共用路徑（共用監看 `handoffs/run_receipts/numview_probes/_watchdog.py` 八個呼叫端、pytest 閘門 runner、API 服務）；(c) 多 phase；(d) IC 負對照之置換次數現依時間預算縮減（`ic_filter_orchestrator.py` 依 `negative_control_budget_seconds`），結果隨機器快慢而變，屬回測／統計正確性。
- RISK-HIT: b,c,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已確認結果**：2026-10-27 使用者原話：「講幾千次不準再因為時間上限問題被停掉，一直再犯，不要給我講藉口，只准提如何解決」「我說的時間上限問題不是只有這一票，是整個專案」「判停一律重跑，不先查停止的原因，直接重跑不也會停?」「時間上限的問題要根本解決，確保軟體和量化業界怎麼做，在這專案中不準再次發生，也不準跑完或沒動靜還要等我問你才去查，這也不準在這專案中再次發生」。2026-10-26 使用者原話：「我完全沒有任何一次要求你把時間控制在多少時間以內」。
- **已驗證事實**（4 條 FACT-RECEIPT）：
  - FACT-RECEIPT: 子代理唯讀盤點（grep `wall_cap_seconds|wall_ceiling_seconds|run_watched(|TimeoutExpired|signal.alarm|mark.timeout|timeout_seconds|max_seconds|deadline|wait_for|result(timeout=` 等並逐處讀碼分類）→ 印出 A 類（依牆鐘停止／縮減運算）約 40 處、B／C／D 分組摘要（主委 實跑 2026-10-27；全文收據 `handoffs/run_receipts/20261027-nocap-inventory.md`）
  - FACT-RECEIPT: `venv/bin/python -c "import pytest_timeout"` → 印出 `ModuleNotFoundError`（盤點子代理 實跑 2026-10-27）——21 個 `pytest.mark.timeout` 標記現不生效。
  - FACT-RECEIPT: `venv/bin/py-spy dump --pid <同使用者 python>` → 印出 `This program requires root on OSX.`；`sample <pid> 1 -file f` → rc=0 且含 `__select` 堆疊；子行程 `faulthandler.register(SIGUSR1, all_threads=True)` 後送 SIGUSR1 → 印出 `Current thread … File "<string>", line 1`（主委 實跑 2026-10-27）。
  - FACT-RECEIPT: FFPROD 量測首跑改前全欄 IC（209,053 欄）→ 收據逐字 `牆鐘 5404 秒逾上限 5400 秒`、`swap_growth_max_mb` 約 1086（主委 實跑 2026-10-27，`handoffs/run_receipts/20261026-ffprod-candidates.json`）。
- **業界依據（本 SPEC 之判準來源）**：批次運算之卡死判定以進度（心跳／log／CPU）為準、不以固定牆鐘時間終止；判卡死時先取執行緒堆疊再終止（JVM thread dump、Python faulthandler、py-spy 同類做法）；只有可重試之暫時性失敗（網路、外部服務）才自動重試且有退避；互動請求之逾時屬服務契約（HTTP 504），長運算改背景工作＋進度，不在請求內殺運算；統計檢定（置換、自助法）之次數固定、與機器快慢無關（可重現性）。
- 待確認：無

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條、不弱化 NaN／inf gate、不擅改輸出大小（CLAUDE.md）。NUMVIEW 判準檔 `tests/_golden/numview/preregistered_criteria_v9.json` 之鍵集合不改（`WATCHDOG_KEYS` 封閉；牆鐘兩鍵改為只記錄之語意，於共用監看實作與本 SPEC 定義）。
- 分類登記之單一真相源＝`scripts/timeout_registry.json`（新建，Task 0.2）；SPEC 不列舉清單。
- 本任務特別注意：共用監看八個呼叫端（`scripts/numview_freeze_baseline.py`、`scripts/ffprod_freeze_baseline.py`、`scripts/ffprod_measure.py`、`handoffs/run_receipts/numview_probes/{estimate,l2_arm_matrix,postic_branchdiff,postic_core_select,precision_chain}.py`）；pytest 閘門 `scripts/framepath_affected_gate.py`、`scripts/testreg.py`；API `api/services/model_enhancement_service.py`、`api/services/ic_analysis_service.py`、`api/routes/feature_browser.py`；`momentum/Optimization/optuna_optimizer.py`、`momentum/Analysis/feature_quality_diagnostics.py`、`momentum/Analysis/ic_filter_orchestrator.py`。

## §G Golden / Baseline
- 適用：Task 5.1（負對照置換次數，RISK-HIT d）。其餘 Task 不改數值。
- 凍結時機／reference：動工前以現行碼於 `tests/` 既有負對照測試所用之真實資料輸入（Task 5.1 實作前以 FACT-RECEIPT 寫明檔名與設定），在「時間預算足夠、未觸發縮減」之條件下跑一次，存 `tests/_golden/nocap/negative_control_baseline.json`（逐特徵置換統計量與 p 值、置換次數、輸入 sha256）。
- 通過條件：改後於同輸入之逐特徵統計量與 p 值 `==`（逐位元）基準；置換次數 `==` 基準；另注入兩種耗時（快／慢）之兩次改後執行彼此逐位元相同。

## §P Phase 與依賴

### Phase 0 — 登記與機械閘（依賴：無）
**Task 0.1 — 共用監看：不因時間終止、進度判卡死、留現場判原因**（已實作於 `07e8887c`，本 Task 為審查與驗收）
- 目標：`_watchdog.run_watched` 牆鐘只記錄 `over_expected`；卡死＝log 未增長且行程樹 CPU < `CPU_PROGRESS_FRACTION` 核持續 `log_stall_seconds`；終止前 `diagnose`（注入 sitecustomize 以 faulthandler 經 SIGUSR1 寫全執行緒 Python 堆疊至 `<log>.stacks.txt`、串接呼叫端原 sitecustomize；macOS `sample`；各行程狀態／CPU／RSS、swap、log 尾段），`cause`∈{`memory`,`hang`}。
- **驗證**：`tests/feature_engineering/test_numview_criteria.py -k watchdog` 全綠，含 `test_watchdog_busy_silent_child_not_stalled`、`test_watchdog_wall_cap_only_records`、`test_watchdog_silent_child_stalled`（堆疊檔含卡住行）、`test_watchdog_stack_dump_chains_existing_sitecustomize`、`test_watchdog_memory_cause_from_swap_evidence`。
- **邊界**：psutil 讀不到 CPU ⇒ 退回只看 log（理由寫明 CPU 讀不到）；子行程於留現場期間自行結束 ⇒ 留現場盡力而為、照判 STALLED。
- **存活至**：本票完工後保留。　**覆蓋風險**：無。
- 不可做：不改判準檔鍵集合；不加入任何依牆鐘終止之條件。

**Task 0.2 — 時間上限登記檔與掃描測試**
- 目標：`scripts/timeout_registry.json` 逐處登記 repo 內每個逾時／期限機制（檔:符號、類別 B／C／D、理由、上限值來源）；A 類（依牆鐘停止或縮減運算）不得出現。
- 改法：新測試 `tests/registry/test_timeout_registry.py` 以 AST＋文字掃描 `scripts/ momentum/ api/ tests/ handoffs/run_receipts/*_probes/` 之逾時樣式（`timeout=`、`wait_for(`、`result(timeout=`、`signal.alarm`、`deadline`、`max_seconds`、`wall_cap`、`time.time() - … >`、`monotonic() - … >` 之比較），每處須在登記檔且類別非 A；登記檔中已不存在之項目亦紅（防漂移）。
- **驗證**：`pytest tests/registry/test_timeout_registry.py` 全綠；mutation：於 `scripts/ffprod_measure.py` 加 `subprocess.run(cmd, timeout=60)` ⇒ 紅；刪登記檔任一列 ⇒ 紅；登記一個 repo 已不存在之檔:符號 ⇒ 紅。
- **邊界**：封存副本（`numview_freeze_seam/run{1,2}_*`、`testreg_probes/trial_impl/*`）登記為 D「封存、不執行」；字串型命中（設定說明、log 文字）登記 D。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以黑名單列舉可接受寫法（登記檔為白名單）。

**Task 0.2b — 寫碼當下擋新增時間上限（產出端，使用者 2026-10-27「你能確保在此專案每次都會用到嗎? 不然你可能自己手動加上時間限制，或根本不用做好的共用監看?」）**
- 目標：任何 Edit／Write 寫入之新內容含逾時／期限樣式而不在 `scripts/timeout_registry.json` 白名單 ⇒ 寫入當下擋下（不等測試）。
- 改法：PreToolUse hook `scripts/timeout_write_guard.sh`（掛 `.claude/settings.json` 之 Edit／Write／MultiEdit）只掃本次新增之文字（Edit 之 new_string 相對 old_string 之增量、Write 之新檔對既有檔之增量），樣式與 Task 0.2 掃描測試共用同一份樣式定義（`scripts/timeout_patterns.json`，單一真相源）；命中且非白名單 ⇒ rc=2 並印登記方法與「長運算不得登記」規則。白名單只收 B／C／D 類且每列附理由；A 類（依牆鐘停止或縮減運算）不可登記（登記檔 schema 拒收）。
- **驗證**：`tests/governance/test_timeout_write_guard.py`：Edit 新增 `subprocess.run(cmd, timeout=600)` 於 `scripts/` ⇒ rc=2；新增 `asyncio.wait_for(x, timeout=30)` ⇒ rc=2；改動既有已登記行之其他字 ⇒ rc=0；新增白名單已登記之 B 類（如 Binance HTTP 逾時）⇒ rc=0；登記檔加 A 類列 ⇒ schema 拒收 rc=1；hook 單次耗時 < 1 秒。
- **邊界**：hook stdin 讀不到 ⇒ 擋（寫入類 fail-closed，與一般命令不同）；非 Python／shell 檔（.md 說明文字）⇒ 不掃；字串中出現樣式（log 文字）⇒ 以 AST 判斷是否為實際呼叫，非呼叫者放行。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以黑名單列舉可接受寫法；不得超過秒級。

**Task 0.3 — 重型跑必經監看且背景執行之產出端閘**
- 目標：重型命令（特徵生成腳本、凍結腳本、量測 `run|ic`、IC 分析、重型 pytest 檔、委員派工）未經共用監看或未以背景執行時於下指令當下擋下——保證卡死必被終止並留現場、行程結束必有完成通知，不需使用者詢問。
- 改法：PreToolUse hook `scripts/heavy_run_guard.sh`（掛 `.claude/settings.json` 之 Bash）比對命令與 `scripts/heavy_commands.json`（封閉清單）；命中而（未經 `scripts/run_watched.sh` 或 `tool_input.run_in_background` 非 true）⇒ 擋並提示改法。`scripts/run_watched.sh`（新建）以共用監看包任意命令、印 `[run-watched] start|progress|stalled|exit` 行。
- **驗證**：`tests/governance/test_heavy_run_guard.py`：重型命令直跑 ⇒ rc=2；經 `scripts/run_watched.sh` 但前景 ⇒ rc=2；經包裝且背景 ⇒ rc=0；非重型命令 ⇒ rc=0；hook 單次耗時 < 1 秒。
- **邊界**：命令經 `bash handoffs/run_receipts/.<票>-*.sh` 間接呼叫 ⇒ 讀腳本內容比對（遞迴一層）；hook stdin 讀不到 ⇒ 重型樣式無從判定 ⇒ 擋（fail-closed）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：hook 不得超過秒級。

**Task 0.3b — 全規模重型跑前須有成長曲線收據（使用者 2026-10-27「軟體和量化業界會這樣直接測大規模到崩潰？你不是保證用業界做法？」）**
- 目標：業界逐步放大——全規模之前先於小、中規模實測耗時與峰值記憶體、得成長曲線與全規模推算，確認可行才跑全規模。`scripts/heavy_commands.json` 之重型項目增欄 `scale_receipt`（收據路徑樣式）；`heavy_run_guard` 於下指令時查：對應收據存在、含 ≥ 3 個規模點（每點之欄數或列數、秒數、峰值 RSS）、全規模推算值、且其程式碼態雜湊等於現行碼；缺或過期 ⇒ 擋。
- 改法：新增 `scripts/scale_probe.py`（以同一入口、同一真實資料取子集跑 3 個規模點並擬合，寫收據 `handoffs/run_receipts/<日期>-<目標>-scale.json`）；探針本身經共用監看、背景執行。
- **驗證**：`tests/governance/test_heavy_run_guard.py` 增案：無收據 ⇒ rc=2；收據只 2 點 ⇒ rc=2；收據碼態雜湊不符 ⇒ rc=2；3 點且推算存在 ⇒ rc=0；`scripts/scale_probe.py` 對 3 點寫出之推算與注入之線性耗時誤差 < 5%。
- **邊界**：目標本身無法縮小規模（例：單一固定格之凍結）⇒ 清單標 `scale_exempt` 並寫理由（審碼必查）；推算為超線性 ⇒ 收據標記並印出，由主委報使用者後再跑。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以小規模之結果代替全規模結論（只用於推算與可行性判斷）。

**Task 0.4 — 記憶體／精確度／計算時間／檔案大小四項平衡之實測機制（全專案任何計算與使用者體驗；使用者 2026-10-27「我所謂「記憶體、精確度、計算時間、檔案大小四項要平衡」的最優化是此專案的任何計算和使用者體驗都算。」）**
- 目標：任何改到計算路徑或使用者操作（頁面等待、API 回應）之 SPEC，必附實際規模下四項實測與成長曲線；主要模組（特徵生成、IC 分析、IC 頁操作、回測、最佳化）各存一份四項基準，改動後重量、任一項明顯變差即擋。
- 改法：①`templates/SPEC_TEMPLATE.md` 增必填錨點 `## §B 四項平衡實測`（耗時、峰值 RSS、精度差、檔案大小；代表規模＋≥3 點成長曲線；不涉計算者於 §N 標 N/A 附理由），`scripts/template_check.sh spec` 缺錨點即 FAIL；②基準檔 `tests/_golden/balance/<模組>.json`（四項數值、規模、碼態）＋比較腳本 `scripts/balance_check.py`（重量後與基準比，耗時或 RSS 增逾 20%、精度差非零、檔案大小增逾 10% ⇒ rc≠0；門檻寫於基準檔可審）；③`templates/COMMITTEE_FINDING_TEMPLATE.md` 首節增必查項「本次改動於實際規模之四項有無變差、有無實測依據」。
- **驗證**：`bash scripts/template_check.sh spec` 對缺 §B 之 SPEC ⇒ rc=1、對有 §B 者 ⇒ rc=0；`tests/governance/test_balance_check.py`：注入耗時增 25% ⇒ rc≠0、增 10% ⇒ rc=0、精度差 1e-12 ⇒ rc≠0。
- **邊界**：既有已凍結 SPEC 不溯及（只對新 SPEC 與新版次）；無法於本機量之規模（記憶體不足）⇒ 記 blocked_by hardware，計算效率仍須以三點曲線評估、不得以換機為由延後（使用者 2026-10-27「換大機器跟整個計算要最優化是不同事吧」）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以單一規模之數字代替成長曲線；門檻不得放寬既有驗收。

### Phase 1 — 共用監看之呼叫端（依賴：Task 0.1）
**Task 1.1 — 八呼叫端改依原因處理**
- 目標：`cause=hang` ⇒ 寫 `stall_diagnosis.json` 並停止（不自動重跑）；`cause=memory` ⇒ 依各腳本既有之硬體受阻語意記錄；`over_expected` 寫入各收據。`scripts/ffprod_measure.py` 已於 `07e8887c` 完成。
- **驗證**：`tests/feature_engineering/test_numview_criteria.py`（估時器、凍結腳本）與各探針之卡死測試注入 `cause=hang`／`cause=memory` 並斷言：hang ⇒ `stall_diagnosis.json` 存在且 rc≠0、無重跑；memory ⇒ 照硬體受阻記錄；`grep -c "watched.cause"` 於 8 個呼叫端檔皆 ≥ 1。
- **邊界**：舊收據中依牆鐘終止之結果 ⇒ 不算完成、重算。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不新增任何自動重跑。

### Phase 2 — pytest 閘門與測試內部等候（依賴：Task 0.1）
**Task 2.1 — 閘門 runner**：`scripts/framepath_affected_gate.py` 之 `COLLECT_TIMEOUT_SECONDS`、Runner `max_seconds`（預設 3600）、`ADMISSION_BUDGET_SECONDS`（7200）與 `scripts/testreg.py` 同類：pytest 子行程改經共用監看（進度判卡死＋留現場）；`max_seconds` 預設 None（只在明示時分段）；預算閘改為只印估時、不拒跑。探針腳本（`testreg_probes/v6_profile.py`、`framepath_probes/admit_*.sh`、`probewinsor_probes/affected_chunk.sh`、`testreg_probes/b3/light_sweep.sh`）同改或登記 D（封存不執行者）。
- **驗證**：`tests/registry/test_gate_runner_nocap.py`：無 `--max-seconds` 而累計 4000 秒等效（注入時鐘）⇒ 不暫停（Paused 次數＝0）；pytest 子行程卡死（注入 `time.sleep(600)` 之測試、門檻 1 秒）⇒ STALLED＋`.stacks.txt` 存在；忙迴圈 3 秒無輸出 ⇒ rc＝0；估時 8000 秒逾舊預算 ⇒ 照跑（rc＝0）並印估時。
- **邊界**：使用者明示 `--max-seconds` ⇒ 照分段（使用者自設之預算，登記 B「使用者明示」）。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不刪 progress.json 既有欄位。

**Task 2.2 — 測試內部之子行程等候**：`tests/` 內對重型子行程之 `timeout=`（盤點收據 A 類測試表）改經共用監看；`pytest.mark.timeout` 標記全刪（未安裝、無效且誤導）。
- **驗證**：`pytest tests/registry/test_timeout_registry.py` 全綠（測試內部 A 類計數＝0）；`grep -rn "pytest.mark.timeout" tests` 計數＝0；受影響測試照 `docs/TEST_SELECTION.md` 跑且結果與改前相同。
- **邊界**：等候外部（委員 CLI、網路）者登記 B。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改測試斷言之語意（只換等候機制）；刪改測試照測試刪改清單送審。

### Phase 3 — 等 IC 完成之腳本（依賴：Task 0.1）
**Task 3.1**：`scripts/ic1eb_b5_replay.py`、`scripts/capture_ic1eb_baseline.py`、`scripts/ic1c_freeze_baseline.py`、`tests/golden/ic_phase1_contract/freeze_baseline.py`、`tests/golden/ic_phase1_1a_cut1/freeze_baseline{,_new}.py`、`scripts/measure_ic_footprint.sh`：等到任務終態（completed／failed）；卡死判定改依任務進度欄或服務行程 CPU（共用監看之判定函式），不設期限。
- **驗證**：`tests/registry/test_ic_wait_nocap.py`：注入任務狀態序列「running×N 而進度不變且 CPU 不動、逾門檻 1 秒」⇒ 判卡死、留現場檔存在；「running 3600 秒等效（注入時鐘）且進度遞增後 completed」⇒ 回 completed、未逾時拋錯（TimeoutError 次數＝0）。
- **邊界**：任務狀態 API 無進度欄 ⇒ 以服務行程 CPU 判（Task 3.1 先查 `get_task_status` 是否有進度欄，FACT-RECEIPT 入本 Task）。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改 IC 數值。

### Phase 4 — 驗證腳本之期限（依賴：Task 0.1）
**Task 4.1**：`scripts/verify_l1_warmup_requirements.py` 之 `--max-task-cpu-hours`（實為牆鐘）與 `--max-stall-minutes`（以任務完成為進度）：改為 pool worker CPU 進度判卡死＋留現場；期限旗標預設 None。
- **驗證**：`tests/feature_engineering/test_warmup_verify_guards.py` 增案：單一任務忙迴圈 3 秒（舊期限注入 1 秒）⇒ rc＝0；worker `time.sleep(600)` 而門檻 1 秒 ⇒ 終止、rc＝4 且留現場檔存在。
- **邊界**：使用者明示期限 ⇒ 照辦（登記 B）。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改 `verify_l1_warmup_requirements.py` 之判準。

### Phase 5 — 產品服務與量化計算（依賴：Task 0.2）
**Task 5.1 — 統計檢定次數固定**：`ic_filter_orchestrator.py` 負對照置換次數依 `negative_control_budget_seconds` 縮減 ⇒ 改為固定次數（設定值，預設＝現行未縮減時之次數），刪時間預算欄；結果與機器快慢無關。
- **驗證**：`tests/momentum/Analysis/test_negative_control_fixed_count.py`：同輸入於注入 0.01 秒與 10 秒等效耗時之兩次執行，逐特徵統計量與 p 值 `==`；與 §G 基準 `==`；mutation：恢復時間縮減 ⇒ 紅。
- **邊界**：欄數極多致置換總耗時長 ⇒ 照跑（進度回報），不縮減。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改置換統計量定義。

**Task 5.2 — 無效之 ADF 逾時**：`feature_quality_diagnostics.py` 之 `adf_timeout_sec`（`with ThreadPoolExecutor` 離開時仍等執行緒，未省時間、卻丟棄結果）⇒ 刪逾時，直接計算。
- **驗證**：`tests/momentum/Analysis/test_feature_quality_diagnostics_nocap.py`：慢 ADF（注入 6 秒）⇒ 結果保留、`reason` 無 `adf_timeout`。
- **邊界**：ADF 拋例外 ⇒ 照既有錯誤處理記錄（不變）；單一欄全 NaN ⇒ 照既有跳過規則（不變）。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改 ADF 參數。

**Task 5.3 — 長運算服務改背景工作＋進度**：`model_enhancement_service.py`（`asyncio.wait_for` 逾時後執行緒仍在跑、結果丟棄）、`ic_analysis_service.py` 掃描網格之逐格／全網格期限：改為背景工作至完成、逐步回報進度、可由使用者取消；HTTP 請求不等待運算（立即回工作 ID）。`api/routes/feature_browser.py` 之請求逾時屬互動服務契約 ⇒ 運算改快取＋背景計算，請求逾時保留並登記 B（理由：互動請求延遲上限，非運算上限，逾時不中止運算）。
- **驗證**：`tests/api/test_nocap_background_jobs.py`：長運算請求（注入 5 秒）於 1 秒內回工作 ID；完成後結果可取且等於同步計算之結果（`==`）；取消後工作狀態＝cancelled；`grep -rn "scan_cell_timeout\|skipped_reason=\"timeout\"" api momentum` 計數＝0。
- **邊界**：前端輪詢中斷 ⇒ 工作照跑、結果保留。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改各分析之計算內容。

**Task 5.4 — Optuna 時間預算**：`timeout` 為使用者可設之搜尋預算（Optuna 標準參數）⇒ 保留為選填、預設 None（以 `n_trials` 界定）；`api/models/optimization_models.py` 預設 300／1800 改 None；`config/optimization_config.yaml` 之 `timeout: 300` 刪或改 null。登記 B「使用者明示之搜尋預算」。
- **驗證**：`tests/momentum/Optimization/test_optuna_no_default_timeout.py`：未指定 ⇒ 完成 trial 數＝`n_trials`（注入每 trial 0.2 秒、n_trials＝5）；指定 `timeout=0.5` ⇒ 完成數 < 5（Optuna 語意）。
- **邊界**：`n_trials` 與 `timeout` 皆未指定 ⇒ 請求驗證拒收（422，無界搜尋）；舊設定檔帶 `timeout: 300` ⇒ 讀取時忽略並記一行說明。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改搜尋演算法。

### Phase 6 — 委員 CLI 等候（依賴：Task 0.1）
**Task 6.1**：`scripts/cx_run.sh` 之 `CX_MAX_SEC`（5400）：委員 CLI 以輸出檔增長／行程 CPU 判卡死並留現場（`ps`、輸出尾段），不設牆鐘上限；`STATUS: DONE` 後之寬限保留（屬已完成後收尾，登記 C）。`scripts/wait_for_dispatch.sh --timeout` 預設 None。
- **驗證**：`tests/governance/test_cxrun_progress_watch.py`：假 CLI 持續輸出 6000 秒等效（注入時鐘）⇒ 不終止；假 CLI 無輸出且無 CPU 逾門檻 ⇒ 終止、rc＝124 且留 `ps`／輸出尾段檔。
- **邊界**：CLI 已寫 `STATUS: DONE` 而未退出 ⇒ 寬限後收尾（不變）；CLI 等網路回應（無 CPU、無輸出）⇒ 屬外部等候，門檻取登記檔之 B 類值並記錄原因。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改委員派工流程。

## §V 驗證策略與邊界測試目錄
- mutation：Task 0.2 掃描（加回任一 A 類即紅）、Task 5.1（恢復時間縮減即紅）、Task 0.1（`ENABLED=False` 即不判卡死，既有）。
- 三道防線（寫碼當下 Task 0.2b、下指令當下 Task 0.3、測試期 Task 0.2）之外，`templates/COMMITTEE_FINDING_TEMPLATE.md` 首節增一項必查：「本次變更是否新增或擴大依時間停止／縮減運算之機制，或重型執行繞過共用監看」（樣式比對抓不到之新寫法由審碼抓）。
- 測試層級：單元（監看、登記掃描、hook）／整合（閘門 runner、IC 等候、API 背景工作）。受影響測試照 `docs/TEST_SELECTION.md`。
- 防假綠：刪除之牆鐘終止測試（`test_watchdog_wall_cap_stalled`）改寫為只記錄，同提交送測試刪改清單審。
- 邊界目錄：API 重啟（背景工作）、並發（多工作）、OOM（記憶體原因）、psutil 不可用、非 macOS（無 `sample`）。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert；共用監看之 `ENABLED` 既有開關不改。

## §N N/A 登記
- 殘留：無。
