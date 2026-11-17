# TESTSEL I1 紅清單、隔離根確認與真紅修 — SPEC

> 來源大綱：`handoffs/20261116-testsel-route-outline.md`（I1；確認輪 `handoffs/reconcile/20261116-testsel-x-consult-r5/synth.md`）　|　日期：2026-11-17　|　對應 TODO：`docs/manifests/TESTSEL_I1.json`（本 SPEC 定稿後生成）　|　原型產出：`runs/testsel_route/i1_proto/red_classified.md`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（改 tests/conftest.py 共用隔離介面、多模組測試；涉 NUMVIEW 收據與 L2 數值量測；清理正式資料）。
- **命中高風險原則**：(a) 測試寫入正式資料根（`data_cache/kline_cache.h5` ETHUSDT/1h 整組為測試下載之不連續 K 線；`data_cache/patterns` 370 檔全為測試假型態）、L2 兩臂 4h 數值未驗；(b) tests/conftest.py 為全部測試共用；(d) 量化測試之紅含釘值／收據，處置錯誤會掩蓋數值錯。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- FACT-RECEIPT: `venv/bin/python -m pytest … $(unreg_args.txt)`（i7b-probe，d1f57180）→ 印出 `157 failed, 96 passed, 4169 warnings in 1613.37s`（主委 實跑 2026-11-17；log `runs/testsel_route/i1_proto/rerun_unreg.log`）
- FACT-RECEIPT: `bash runs/testsel_route/i1_proto/run_in_tree.sh .claude/worktrees/main-probe quant_reds.txt`（9f059c65）→ 68 條中 63 條同紅、5 條通過（主委 實跑 2026-11-17；`main_quant.log`、`c_class.txt`）
- FACT-RECEIPT: `jq -r '.[].node' tests/_golden/prered/allowed_red.json`（main-probe）與 `c_class.txt` 交集 → `0`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `run_in_tree_freshcache.sh i7b-probe f32only.txt <新快取根>` → 印出 `1 passed … in 565.26s`；命中舊快取時 `2 failed in 3.43s`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `cmp_nv_obs.py <舊 pkl> <新 pkl>` → `old compute_all_polars_calls= 8 arms_tf= ['1h', '4h']`、`new … 7 arms_tf= ['1h']`、1h `returned`／`category` 共同欄 536 不等格 0（主委 實跑 2026-11-17）
- FACT-RECEIPT: `remaining_ids.py <整合樹> i7e_deselect.txt` → `selected=2026 remaining=103 deselect_not_done=3`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `inspect_kline_h5.py data_cache/kline_cache.h5` → `ETHUSDT/1h n=1762 first=2024-05-20 20:00:00 last=2025-10-27 12:00:00 gaps=2 dup=0 max_gap_bars=5589`；其餘 4 組 12h `gaps=0`（主委 實跑 2026-11-17）
- FACT-RECEIPT: `data_cache/patterns/PAT_*.json` 規則含 `f0` 者 → `test-signature=367 total=370`；其餘 3 檔名 `a`／`b`／`c`、case `cx`、規則欄 `f`（主委 實跑 2026-11-17）
- 待確認：無
- 已確認結果：2026-11-17 使用者「data_cache你可以刪除，然後用現在專案有的程式經過幣安API再抓需要的真實資料」（Task 1.6）。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條；不弱化 NaN/inf gate；不放寬既有斷言換綠（§V 防假綠）。
- 紅之處置只有兩種終態：修後通過；或登記 `tests/_golden/prered/allowed_red.json`（owner＋`為何現在不做: blocked-by:…|user-ruling:…`，SPEC_TEMPLATE 殘留規則）。不得 skip／xfail 規避。
- 釘值、收據、golden 之改動屬資料正確性範圍 ⇒ 依 CLAUDE.md「三方數據正確性簽核」；改後值須以獨立 oracle（pandas／numpy／TA-Lib 等業界庫）於真實資料（`data_cache/feature_klines/kline_cache.h5`）比對，不得以「改後＝改前」代替。
- 全量期間不在整合樹改檔；施工在整合分支（全量收尾後）或依 I2 清單分流。
- 分類單一真相源：`runs/testsel_route/i1_reds.json`（每條紅一列；schema 見 Task 4.1），本 SPEC 不列舉 nodeid。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I1-BUDGET-1 | 全量剩餘 106 條於 i7b-probe 補跑 | 段 9 未執行之 103 條＋卡死排除 3 條 | 106 條 | ✅ 已實跑：`103 passed, 3 xfailed … in 6505.94s (1:48:25)`（`runs/testsel_route/i1_proto/i7e_remaining.log`）；跑前 ledger 估快速 386 s＋重型 5,006 s | I7e 段 1–8 結果 |
| TESTSEL-I1-BUDGET-2 | 段 4 前綴依序重放（定位順序污染） | numba_rolling 等 5 數值檔於長行程中之狀態 | 404 檔 | 已實跑一次（帶 `--testmon`、整檔）：`… in 16399.79s (4:33:19)`（`runs/testsel_route/i1_proto/bisect_numba4b.log`，未重現）；Task 2.1 重放①–③之耗時於施工時依實際選取清單另估 | 無 |
| TESTSEL-I1-BUDGET-4 | Task 2.4 現存 run 之 L3 skew／kurt 全窗精確驗值 | 正式資料中全部 L3 skew／kurt 欄之每一窗 | 現存 run 中 manifest 列有 `_Kurt-W`／`_Skew-W` 欄者：BTCUSDT/12h `0729db3a…` 28,528 欄 × 1,951 列，窗長分佈 W3 1,498／W5 3,002／W8 3,006／W13 3,006／W21 3,006／W34 3,006／W55 3,006／W89 3,004／W144 3,004／W233 2,990 欄（施工時以 registry 與 parquet 群組補查其餘 run） | 精確滑動整數冪次和法每窗 40.4／28.5／33.0 µs（窗 5／21／233，`runs/testsel_route/i1_proto/exact_sliding.py` 實測，與窗長無關；與逐窗 Fraction 抽查 176 窗不一致 0）；skew＋kurt 共用，約 14,264 組（輸入欄×窗長）× 1,951 列；以合成資料每窗耗時外推之總量為推算、未實測，不得引用——開跑前依 Task 2.4 先查以真實 run 實測後再估 | 無 |
| TESTSEL-I1-BUDGET-3 | 修後受影響測試（含重型）一次 | 本票改動之受影響集 | 依 TEST_SELECTION §5 | 施工後依 ledger 估 | 無 |
- 不降驗證之省法：BUDGET-2 先以最近鄰／涉 numba 之檔試（已試 7 組皆未重現，含段 4 完整前綴整檔重放，見 red_classified.md），重現後才二分；BUDGET-1 改在同 commit 之 probe 補跑而非重開全量。
- 小規模驗不到之理由：順序污染只在長行程前綴出現（單跑、帶 --testmon 單跑、根目錄 47 檔前綴、段 4 完整前綴整檔重放皆未重現）。

## §B 四項平衡實測
- 適用於 Task 2.4（改 L3 pandas 臂 skew／kurt）與 Task 1.7（改 `taker_ratio` 計算）；其餘 Task 不改產品計算路徑。
- Task 2.4：代表規模＝真實 BTCUSDT/1h（20,352 列）L1 欄於產品預設窗 `[5, 13, 21]`，成長曲線 3 點＝欄數 64／256／1,024（同一資料，列數固定）；量測改前（pandas rolling）與改後（numpy 兩遍法）之耗時、峰值 RSS（同一量測器）、精度（對精確 oracle 之最大相對差）、輸出大小（L3 欄 bytes）；改後精度須達 ≤1 float32 ulp，耗時與 RSS 增幅逐點列出並與 numba 臂同規模比較，主要模組另比 `tests/_golden/balance/<模組>.json`（`scripts/balance_check.py`）。
- Task 1.7：`taker_ratio` 由 float32 相除改為 float64 相除後捨入，計算量與輸出大小不變（仍 float32）；精度改善以 Task 1.7 之 `decimal` oracle 驗。

## §G Golden / Baseline
- **feature/kline 條件**：Task 3.2 之 L2 兩臂 4h 值驗證用真實 `data_cache/feature_klines/kline_cache.h5`（格 B_BTCUSDT_1h_4h），禁合成；Task 1.6 重抓之 ETHUSDT/1h 以 Binance 實際 K 線驗。
- **凍結時機 / reference**：Task 3.2 修量測後，以全新空 `NUMVIEW_REGEN_BATCH_ROOT` 生成格 A＋B，產出逐週期兩臂；reference＝pandas 獨立重算之公開 L2 類別表。
- **baseline 內容**：每週期之 f32diff 計數、不等格之欄名集合 sha256、每欄 max abs diff、NaN mask hash。
- **通過條件（兩層，比對對象不同、不得混用）**：
  - 第一層＝契約語意（兩產品來源互比，`momentum/FeatureEngineering/contracts/numeric_view.json` 之 `l2_value_sources`）：契約未列之格，Polars 回傳臂與公開類別臂 float32 逐位元相等（f32diff＝0）；具名格（`nonzero_cells`）之每週期 f32diff 計數等於新收據釘值。1h 已實測與現收據逐格相等（536 欄不等格 0）。
  - 第二層＝各臂獨立正確（每臂對獨立 oracle）：Polars 臂與 category 臂各自對 pandas 獨立重算之同欄比對，每格 `abs(out − ref) ≤ abs(np.spacing(ref))`（兩者 float32、差以 float64 計；即 `tests/feature_engineering/test_numview_core.py:447` `_ulp_ok` 之定義），NaN 位置一致；超出即列欄名、格與差＝FAIL。
  - 新收據（含 4h）經三方資料正確簽核後才可替換舊收據。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 0 — 紅清單完整（依賴：無）
**Task 0.1 — 全量剩餘補跑**
- 目標：I7e 未執行之 106 條於 i7b-probe 補跑，紅併入清單。　檔案：`runs/testsel_route/i1_proto/i7e_remaining.txt`（既有）　既有 caller：無
- **驗證（可證偽）**：補跑 log 末行 summary 之各結果合計＝106；data_cache 標記檔後 `find data_cache -newer` 無新寫入（有則列為 Task 1.2 寫入者）。
- **邊界**：①g7 類單條數百秒無輸出 ⇒ run_watched 判卡死時記為「卡死未判」列入清單，不視為通過；②已知寫正式資料之三條照排除。
- **存活至**：Task 4.1 清單建立後即被吸收。　**覆蓋風險**：無。
- 不可做：不重開整合樹全量；不還原整合樹 golden。

### Phase 1 — 隔離根與狀態外洩（依賴：Phase 0）
**Task 1.1 — 正式資料根寫入偵測擴至整個 data_cache**
- 目標：測試 session 前後對 `data_cache` 遞迴（檔 mtime_ns＋size、目錄項集合）快照比對，任何新增／修改／刪除 ⇒ session 結束狀態非零並具名列出路徑。　檔案：`tests/conftest.py`（`_PROD_WRITE_DIRS`、`prod_write_snapshot`、`pytest_sessionfinish`）　既有 caller：全部測試 session。
- 定位：「測試不寫正式資料」之主路徑＝Task 1.2 之明給暫存根（業界之依賴注入／tmp 根）；本 Task 為其後之安全網，抓漏網者。
- 改法：範圍由兩個頂層目錄改為 `data_cache` 全樹（解析符號連結至實體）；結果由只報改為設 `session.exitstatus` 非零；列出之每個路徑附其 mtime，以對照 TESTREG ledger 各測試起訖時間歸因至單一測試（不做逐測試快照）。
- 執行前提（寫入 `docs/TEST_SELECTION.md` 全量／收案層之執行條件）：全量與受影響集跑時，不得有並行之正式服務寫入 `data_cache`（API／前端／下載排程停止）；session 開始與結束時各查一次正式服務行程（`pgrep -if 'run_api.py|uvicorn|next dev|next start'`）皆為空，任一非空即該次結果不採計、前提滿足後重跑（`lsof` 只反映當下開檔，不作判定依據）；期間之間歇寫入另由列出路徑之 mtime 對 ledger 測試時段歸因（見邊界②）。
- **驗證（可證偽）**：新測試以 pytester 建暫存 repo 根：①測試寫 `data_cache/patterns/x.json` ⇒ rc≠0 且輸出含該路徑；②就地改寫既有 `data_cache/kline_cache.h5`（同大小、mtime 變）⇒ rc≠0；③只讀 ⇒ rc=0。mutation：把範圍改回兩頂層目錄 ⇒ ① 漏抓轉綠。
- **邊界**：①`data_cache` 為符號連結（worktree）⇒ 解析至實體再掃；②執行前提被違反（有並行正式寫入）⇒ 列出之路徑以 mtime 對 ledger 歸因，落在無測試執行之時段者標「非測試寫入」，不計為測試紅，但該次結果須於前提滿足時重跑確認。
- **存活至**：I3 移植至 main 後保留。　**覆蓋風險**：I3 移植 conftest 時須原樣帶入（I2 清單 keep-owner 列）。
- 不可做：不做逐測試快照；不 chmod 正式目錄。

**Task 1.2 — 寫正式資料之測試改暫存根**
- 目標：已知寫入者及 Task 0.1／1.1 新抓到者，全部改寫暫存根。已知：`tests/momentum/test_la2_lookahead.py::test_pattern_promotion_guard`、`tests/test_append_fix.py::test_multi_range_append`、`tests/api/test_scan_cube.py::test_cube_failure_does_not_kill_scan_results`；型態假資料之名稱（`n`、`nl`、`np`、`f`、`good`、`a`／`b`／`c`）對應之全部測試以 grep 一次找齊。　既有 caller：無（測試本身）。
- 改法：以明給根（`tmp_path`）建構服務／存放；`test_multi_range_append` 直連 Binance 且檔內已有密封姊妹 `test_multi_range_append_isolated_cache_sum_and_revision` ⇒ 原測試改用暫存 `cache_dir`（保留網路路徑覆蓋）。
- **驗證（可證偽）**：各測試於 Task 1.1 偵測下 rc=0 且通過；mutation：把任一條改回預設根 ⇒ Task 1.1 偵測 rc≠0。
- **邊界**：①測試需讀真實 kline（feature_klines）⇒ 唯讀不受影響；②網路不可用 ⇒ 原有行為（不得改為 skip 掩蓋）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改產品預設路徑（Rule 5 之字面路徑屬另案，§N 登記）。

**Task 1.3 — HERMETIC 重導只作用於寫入預設**
- 目標：讀真實 run 之測試不被導向空暫存根。　檔案：`tests/conftest.py`（HERMETIC 段）、`tests/momentum/test_feature_library_row_index.py`、`tests/momentum/Analysis/test_ic_persist_redirect_isolation.py`　既有 caller：全部測試。
- 改法：讀真實 run 之測試明給根；S11 探針之期望根與 HERMETIC 根之關係依該測試原意（探針須落在測試給定根下）修。
- **驗證（可證偽）**：`test_load_real_run_attaches_persisted_axis`、`test_load_real_run_value_conservation`、`test_all_seam_probes_stay_under_root[S11]` 於整合分支通過；main 基準已通過（9f059c65）。
- **邊界**：①未給根之寫入仍落 HERMETIC 根（Task 1.1 偵測 rc=0）；②給根之讀取讀實際 run。
- **存活至**：I3 移植後保留。　**覆蓋風險**：無。
- 不可做：不移除 HERMETIC 重導。

**Task 1.4 — root logger handler 外洩**
- 目標：任一測試新增至 root logger 之 handler 於該測試結束後關閉並移除。　檔案：`tests/conftest.py`（新 autouse fixture，function 範圍）；`tests/momentum/DataExtraction/test_search_download_pagination.py:599,613` 兩測試加 finally 清理。　既有 caller：全部測試。
- **驗證（可證偽）**：依段 5 順序跑 pagination 檔 44 條 ⇒ 全過（現況 11 failed，見 TESTSEL_REMAINING 11-16 20:02 列）；新增兩條單元測試分別驗兩邊界：(i) 測試 A 掛 root handler 且不清理、測試 B 斷言 root handlers 不含之 ⇒ 1 passed；(ii) 使用 `caplog` 之測試於 fixture 清理後 `caplog.records` 仍收到紀錄 ⇒ 1 passed。mutation 分開做：M1 移除 fixture（兩測試 finally 保留）⇒ (i) 1 failed；M2 fixture 改為清除全部 root handlers（含 pytest 自身）⇒ (ii) 1 failed；M3 兩測試 finally 移除而 fixture 保留 ⇒ pagination 44 條仍全過（證 fixture 單獨足夠）。
- **邊界**：①測試刻意測 handler 掛載 ⇒ 於測試內斷言後由 fixture 清理；②pytest 自身 handler（caplog／logging plugin）不得被移除（只移除測試期間新增者）。
- **存活至**：I3 移植後保留。　**覆蓋風險**：無。
- 不可做：不改產品 `_init_worker_file_logging` 語意（子行程用法正確）。

**Task 1.5 — golden 輸入檔不被測試改寫**
- 目標：跑完 la1／la0 相關測試後 `git status --porcelain tests/golden` 為空。　檔案：`tests/golden/la1/gen_baseline.py`（`INPUTS_DIR`／`OUTPUT_DIR` 由呼叫端可給）、呼叫之測試　既有 caller：`tests/momentum/test_la1_lookahead.py`、`tests/api/test_ic_la1_degraded_gate.py`、`tests/momentum/test_ic_golden_inputs_names_opaque.py`。
- 閘門 1.5a（定位，先於任何改碼）：對 `grep -rln 'golden/la1\|golden/la0\|gen_baseline' tests` 之每個測試檔逐檔單跑，前後比對 `tests/golden/**` 全部檔之 sha256，產出 `runs/testsel_route/i1_golden_writers.json`（{測試 nodeid: [被改檔]}）。通過條件＝每個被改檔都有歸因之測試、候選檔全數跑過；未過不得進 1.5b。（ETHUSDT_12h `_fallback_tail100.h5` 之寫入者目前推測為 la1 相關，未查證——即由本閘門查。）
- 1.5b（修）：僅修 1.5a 列出之寫入者，令其寫暫存複本；改法依 1.5a 結果定（`gen_baseline.py` 可給輸出根為候選之一）。
- **驗證（可證偽）**：1.5a 清單中每條測試跑後 `tests/golden/**` 之 sha256 與跑前相同；mutation：任一寫入者改回寫 repo 路徑 ⇒ sha256 不同。
- **邊界**：①重生 golden 之正式命令（人工執行 gen_baseline）仍寫 repo；②測試讀 golden 仍讀 repo。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以「跑完再 git checkout」作修法。

**Task 1.6 — 正式資料之測試污染清除與真實資料重抓**
- 目標：清除測試寫入正式資料之全部假資料，並以專案既有下載程式經 Binance API 重抓被測試污染之真實 K 線。　檔案：`data_cache/patterns/`（370 檔全為測試假型態＋`_index.json`）、`data_cache/ic_scan_cubes/t1/`、`data_cache/kline_cache.h5` 之 ETHUSDT/1h　既有 caller：PatternManagementService、IC scan cube、`momentum/Indicators/data_source_manager.py:60`（預設 K 線庫）。
- 改法：①備份至 `runs/testsel_route/datacache_backup/`（已做，h5 sha256 前綴 950f3dca 一致）；②以產品 `delete_pattern`／`delete_all_patterns`（`api/services/pattern_management_service.py:545,555`）刪除測試簽章之型態並同步索引；③刪 `ic_scan_cubes/t1/`；④ETHUSDT/1h 以 `KlineDownloadService`＋`BinanceProvider` 下載同時段（2024-05-20 20:00～2025-10-27 12:00）連續 K 線，`KlineStorageManager.write_klines`（覆寫模式，`momentum/DataExtraction/kline_storage.py:742`）取代整組。
- **驗證（可證偽）**：`data_cache/patterns` 無規則含 `f0`／`f` 之測試簽章檔、`_index.json` 合法且不含已刪 id；`ic_scan_cubes/t1`、`task-scan` 不存在；ETHUSDT/1h `inspect_kline_h5.py` 得 `gaps=0 dup=0`、筆數＝(末−首)/1h＋1（實測 12,593）；`cmp_kline_groups.py <備份> data_cache/kline_cache.h5` 其餘 4 組「逐位元相同」、ETHUSDT/1h 與備份重疊 1,762 筆 OHLCV 不等欄＝無。
- `taker_ratio` 1 ulp 差（重疊 1,762 筆中 534 筆，max_abs 5.96e-08，NaN 不一致 0）之處置：同源 Binance 資料經 append 路徑與一次下載路徑之 float32 結果應逐位元相同 ⇒ 列 I1 子項 Task 1.7 定因，不在本 Task 放行或忽略。
- **邊界**：①`_index.json` 其他條目不變；②重抓期間網路失敗 ⇒ 保留原組（write_klines 原子 swap）、不留半寫入狀態。
- **存活至**：永久。　**覆蓋風險**：Task 1.2 未完成前再跑相關測試會再污染 ⇒ Task 1.2 完成後以 Task 1.1 偵測確認。
- 不可做：不動 `data_cache/feature_klines/kline_cache.h5`（量化主線之真實 K 線來源）；不刪測試簽章以外之檔。

**Task 1.7 — K 線寫入路徑之 taker_ratio 決定性**
- 目標：產品內 `taker_ratio` 有兩個計算點且算法不同——`momentum/DataExtraction/providers/binance_provider.py:472–482`（volume、taker_buy_volume 先轉 float32 再相除，結果 float32）與 `momentum/DataExtraction/kline_storage.py:491–495`（舊快取匯入：float64 相除後轉 float32）；兩者對同一原始值可差 1 float32 ulp（實測 1,762 筆中 534 筆）。先以備份 h5 之 ETHUSDT/1h metadata／寫入紀錄定位舊組由哪一路徑產生（定位結果寫入 `runs/testsel_route/i1_reds.json` 該項 evidence），再統一兩計算點為單一函式。　既有 caller：KlineDownloadService、`_import_from_legacy_cache`、data_source_manager。
- 定義（單一正解）：`taker_ratio`＝Binance 原始字串欄 `taker_buy_base_asset_volume` 與 `volume` 以 float64 解析後相除，一次捨入為 float32，再 clip 至 [0,1]；volume＝0 ⇒ 0.5（現行兩計算點之既有約定，`_validate_kline_dataframe` 要求 [0,1] 且拒 NaN）。此定義較現行 provider 之 float32 先除精確（只捨入一次）；改後 provider 輸出可能有 1 ulp 變動，屬產品值改動 ⇒ §G 三方簽核範圍。
- 錄製物：Binance `GET /api/v3/klines` 之原始 JSON 回應（數值欄為字串，於 provider `_convert_to_dataframe` 之 `astype('float32')`（`binance_provider.py:472–473`）之前擷取），存 `tests/fixtures/` 下；不得存經 provider 轉型後之 DataFrame。
- **驗證（可證偽）**：新測試以上述錄製之原始 JSON（非合成）分別走 provider 路徑與舊快取匯入路徑，`taker_ratio` 逐位元相同（`tobytes()` 相等）且等於上列定義之獨立計算（Python `decimal` 自原始字串計算後轉 float32）；mutation：provider 改回 float32 先除 ⇒ 1 failed。
- **邊界**：①volume＝0 ⇒ 兩路徑皆 0.5；②taker_buy_volume > volume（資料異常）⇒ clip 為 1.0，兩路徑相同；③既有庫內資料不重寫（只修路徑；`data_cache/feature_klines/kline_cache.h5` 之既有值是否重抓另依 §G 簽核決定）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以容差斷言掩蓋。

### Phase 2 — 順序污染（依賴：Phase 1）
**Task 2.1 — 定位並修段 4 數值檔叢集**
- 目標：`test_numba_rolling`（19 條 skew／kurt 類）、`test_multi_window_rolling`、`test_polars_phase4`、`test_talib_wrapper`、`test_winsorize_partition_opt` 於段 4 長行程紅之污染源定位並修。　檔案：待定位　既有 caller：待定位。
- 重放順序（逐步，前一步重現即停、進二分）：① 以段 4 進度紀錄 header 之 `selected`（逐條選取清單）依段 4 log 實際順序、同參數（`-m "not perf"`、`--testsel-tier close`、`--testmon`、testsel 外掛啟用、`MallocSpaceEfficient=1`）於與整合樹同 commit 之樹重放；② 於整合樹本身（全量收尾後、不與他跑並行）同法重放；③ 同②並以同等記憶體壓力（並行一個占用相當 RSS 之行程）重放。三步皆未重現才可列追蹤項。
- **驗證（可證偽）**：BUDGET-2 重放（上列①–③，命令與 log 存 `runs/testsel_route/i1_proto/`）重現 `tests/test_numba_rolling.py` ≥1 failed → 二分至單一污染測試 → 修後同命令 `tests/test_numba_rolling.py` 0 failed；並以「污染測試＋受害測試」兩條最小重現作為新回歸測試（`pytest <污染>::… tests/test_numba_rolling.py` 修前 failed≥1、修後 0）。
- **邊界**：①重放①–③皆未重現 ⇒ 不得單以「重現條件」收案：另以獨立 oracle 證 `rolling_skew_kurt` 值正確後才可列追蹤項。oracle＝逐窗精確有理數計算（Python `fractions.Fraction`，樣本偏態／超額峰度，定義同 `scipy.stats.skew(bias=False)`／`scipy.stats.kurtosis(fisher=True, bias=False)`）；**不得以 pandas rolling 作 oracle**——原型實測（`runs/testsel_route/i1_proto/arbiter_kurt.py`，BTCUSDT/1h close）pandas `rolling(5).kurt()` 對精確值最大差 36.5（例 row 9401：精確 −2.37908、pandas 34.1022、產品 −2.37908），為 pandas 線上累積演算法於大均值序列之數值抵消。逐窗全部分類、無遺漏：(i) 產品與 oracle 皆有限 ⇒ `abs(out − ref) ≤ abs(np.spacing(np.float32(ref)))`（產品輸出 float32；原型實測產品對精確值於 w=5／13／21 各 2,000 抽樣窗之最大相對差 5.83e-8／5.88e-8／5.86e-8，可達）；(ii) 兩者皆 NaN（樣本數不足、常數窗，產品約定見 `tests/test_numba_rolling.py` 之 `test_numba_rolling_skew_kurt_constant_is_nan`、`test_numba_rolling_n_less_than_window_all_nan`）⇒ 相符；(iii) 其餘任何組合（一方有限一方 NaN）⇒ FAIL。路徑覆蓋（非重複資料格）：一個真實 kline 格（`data_cache/feature_klines/kline_cache.h5` BTCUSDT/1h）之 close（大均值）與 log return（小均值）兩序列 × 產品預設窗長 `[5, 13, 21]`（`momentum/FeatureEngineering/feature_config.py:451`）；第二資料格僅於結果確實隨資料而變時加（CLAUDE.md「測試／量測設計＝路徑覆蓋」）。全過才列 allowed_red（owner TESTSEL、`blocked-by:` 已試重放①–③之 log 路徑與未重現事實）並於 I5 週期全量以失敗明細追蹤；②污染源為產品模組狀態（非測試）⇒ 升級為產品修正並補產品層測試。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以 xdist／隨機順序掩蓋。

**Task 2.4 — L3 pandas 臂 skew／kurt 數值錯（產品）**
- 目標：`momentum/FeatureEngineering/operators/rolling_aggregator.py` 之 pandas 臂（`_compute_all_streaming_pandas` :313、:459；`_apply_vectorized_aggregators_with_cache` :878–883；`_compute_skew`／`_compute_kurt` :950–954）以 pandas `rolling().skew()`／`.kurt()` 計算，於大均值欄（價位類 L1 指標，如 `close_1h_trend_BBANDS-Lower_13`）之 kurt 與精確值差達 36.5（原型實測同 Task 2.1）。此臂於下列任一情形生效：`FFACT_USE_NUMBA_ROLLING=0`（`memory_budget.py:154,169`，預設 "1"）、numba 臂拋例外後備（`rolling_aggregator.py:221–232`）、`FFACT_L3_STREAMING=0`（`memory_budget.py:152,167`，預設 "1"；`rolling_aggregator.py:137` 分流至非串流之 :878–883 與 :950–954）。
- 改法：pandas 臂之 skew／kurt 改為**獨立於 numba 之** numpy 逐窗兩遍法（float64，先減窗均值再算二／三／四階中心矩；`numpy.lib.stride_tricks.sliding_window_view`），不呼叫任何 `@njit` 函式——numba 臂失敗而後備時，後備仍可用。退化約定（樣本數不足、常數窗 ⇒ NaN）與 numba 臂一致。
- 先查（施工前）：現行 provenance 只記 L6.5 預處理臂（`run_provenance.py:596` `group_arm_values`），無 L3 臂紀錄，無法由紀錄判定正式資料是否曾走 pandas 臂 ⇒ 改以**全窗直接驗值**：對 `data_cache/features` 中每個現存 run 之每個 L3 skew／kurt 欄之**全部窗**，自同 run 之 L1 輸入欄**每一窗皆以精確 oracle 計算**，依 Task 2.1 (i)–(iii) 規則判定（不使用浮點參考值初篩，無放行誤差）。精確 oracle 之實作＝整數滑動冪次和（欄內每個 float64 化為同一 2 冪分母下之整數，Python int 維護 Σx¹…Σx⁴ 之加入／移出，中心矩以 `fractions.Fraction` 由冪次和導出），其結果須與逐窗 `Fraction` 直接計算逐窗相等（原型 `runs/testsel_route/i1_proto/exact_sliding.py` 抽查不一致 0；施工之測試以此為自身正確性檢查）；同一窗之 skew 與 kurt 共用（成本見 §B TESTSEL-I1-BUDGET-4）。非有限值語意對齊產品（`momentum/FeatureEngineering/operators/numba_rolling.py:125–145` `_window_moments`：窗內任一 NaN ⇒ 整窗無效、輸出 NaN；常數窗之 m2／m3／m4 定為 0 ⇒ 輸出 NaN）：oracle 滑動層另計窗內非有限值（NaN、±inf）個數，非有限值不轉整數、不入冪次和，計數 > 0 之窗 oracle＝NaN；±inf 之窗產品實際輸出須以一條測試實查並與 oracle 之 NaN 相符（不相符即產品 inf 語意另列真紅）。成本：先查開跑前，於該 run 每個窗長各取 1 欄真實 L1 輸入實跑並記錄每窗耗時與整數最大位數，依此估全量耗時後才開跑全量（合成價位級資料之 33–40 µs 不得直接外推）。超出規則者為錯值；確認不符之 run 列入重生清單（三方簽核）。不以抽樣陰性判定 run 合格。
- **驗證（可證偽）**：新測試於真實 BTCUSDT/1h（`data_cache/feature_klines/kline_cache.h5`）之 close 欄（大均值）與 log return（小均值），窗 `[5, 13, 21]`，分別於三種情形——`FFACT_USE_NUMBA_ROLLING=0`、`FFACT_L3_STREAMING=0`、numba 臂注入例外（monkeypatch `fused_rolling_stats`／`fused_rolling_stats_multi_window` 拋例外）——產 L3 skew／kurt，逐窗對 Task 2.1 精確 oracle 依 (i)–(iii) 規則全過；且 pandas 臂與 numba 臂輸出每窗差 ≤ 1 float32 ulp（兩臂演算法不同，不要求逐位元）。mutation：M1 任一 pandas 計算點改回 `rolling().kurt()` ⇒ 1 failed（實測差 36.5）；M2 pandas 臂改呼 `numba_rolling.rolling_skew_kurt`，且注入例外範圍涵蓋 `numba_rolling` 模組全部公開 numba 入口（含 `rolling_skew_kurt`、`fused_rolling_stats`、`fused_rolling_stats_multi_window`）⇒ 1 failed（證後備不依賴任何 numba 函式）。
- **邊界**：①小均值欄（log return）兩臂同值（≤1 ulp）；②低基數欄之既有排除（`_columns_for_agg`）不變；③窗長 > 樣本數 ⇒ 全 NaN。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改 numba 臂；不改 `tail_risk_indicators.py` 之 returns 序列計算（原型實測 log return 上 pandas 對產品相對差 ≤ 1.18e-5，屬另一議題，於 Task 4.1 清單登記其 oracle 比對）。

**Task 2.2 — `test_multi_tf_generator` 順序相依**
- 目標：該檔 5 條（`test_canonical_completeness_three_paths_four_cases[cgsa_*]`、`test_boundary_19_*`）於 `bisect_numba1.txt` 順序紅、段 4 順序下通過 ⇒ 定位並修。
- **驗證（可證偽）**：`bisect_numba1.txt` 順序重跑全綠；單跑全綠。
- **邊界**：①全檔單跑；②與前置檔組合。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：同 Task 2.1。

**Task 2.3 — 其餘乾淨行程通過之紅**
- 目標：`clean_pass_funcs.txt` 其餘函式逐一歸因（污染源或不穩）。
- **驗證（可證偽）**：Phase 1 修後之全量（I5 週期全量）log 中 `clean_pass_funcs.txt` 所列 46 個函式之 FAILED／ERROR 計數＝0；仍紅者依 Task 2.1 法定位。
- **邊界**：同 Task 2.1。　**存活至**：永久。　**覆蓋風險**：無。　不可做：同 Task 2.1。

### Phase 3 — 整合分支才紅（依賴：無）
**Task 3.1 — 結構重凍收據鏈**
- 目標：`test_structural_refreeze_receipt_proves_strip_equals_frozen` 接受後續重凍鏈。　檔案：`tests/feature_engineering/test_numview_acceptance.py:1565–1579`
- 改法：NUMVIEW 收據 `sha256_after` 須等於現行檔，或存在後續重凍收據使 before／after 逐段相接至現行檔（FRAMEPATH v2：`tests/_golden/framepath/refreeze_provenance_v2_receipt.json:14–15`）。
- **驗證（可證偽）**：測試通過；mutation：竄改 v2 收據 `baseline_sha256_before` ⇒ 紅。
- **邊界**：①無後續收據且 sha 不符 ⇒ 紅；②鏈斷於中段 ⇒ 紅。
- **存活至**：永久。　**覆蓋風險**：無。　不可做：不改凍結檔、不改收據值。

**Task 3.2 — NUMVIEW 批次快取與 L2 量測**
- 目標：①批次共用生成快取不跨 session 沿用（根預設改 session 暫存）或鍵涵蓋測試接縫全碼；②量測 spy（`tests/feature_engineering/test_numview_core.py:617–627`）每實例每週期皆記兩臂，不依是否新持久化 L2 群組；③依 §G 重量 4h 並驗證。
- **驗證（可證偽）**：§G 通過條件；`pytest tests/feature_engineering/test_numview_core.py::test_l2_named_matrix_pinned_nonzero_named_and_layers_bitwise` 於命中快取與空快取兩種情形皆 1 passed；mutation：spy 改回依持久化與否 ⇒ 新增之「主實例每週期皆有兩臂」斷言 1 failed。
- **邊界**：①快取命中與不命中結果相同；②mutant 生成不讀寫共用快取（既有規則）。
- **存活至**：永久。　**覆蓋風險**：新收據替換舊收據須三方簽核。
- 不可做：不在簽核前改契約 `l2_value_sources.f32diff`。

### Phase 4 — main 既有紅 63 條與分類單一真相源（依賴：Phase 1）
**Task 4.1 — 紅清單 JSON 與逐條處置**
- 目標：`runs/testsel_route/i1_reds.json` 每條紅一列 {nodeid, class∈{pollution,env-untracked,main-preexisting,branch-only}, cause, disposition∈{fixed,allowed_red}, evidence, owner_ticket}；main 既有 63 條逐條修或登記。
- 初判（原型，逐條施工前須再查證）：測試過時（`test_meta_features` 3＝FF-NAME 欄名、`test_feature_factory_optimization_e2e` 6＝`ent_`／`ms_` 前綴族已由 category 段取代 `momentum/FeatureEngineering/feature_naming.py:20`、`test_preprov_acceptance` 1＝變異現被產品 `ProvenanceError` 更早擋、`test_memory_chunking` 5＝NUMVIEW windows 政策）；資料缺件（`data_cache/numview_postic_core_runs/20261024T065025Z/outputs/pandas_optimized__chunked__a` 不存在 ⇒ 依使用者「資料不足就要補齊」重生）；釘值／行號漂移（`test_probewinsor` 20、`test_ichc_p2_golden`、`test_icperf_gate`、`test_ic_persist_redirect_inventory`）——每條改前須查證漂移原因，釘值改動走 §G 與三方簽核。
- 範圍另含：整合分支 `tests/_golden/prered/allowed_red.json` 中 `owner_ticket` 為 TESTSEL 之既有登記（2026-11-17 `jq '[.[] | select(.owner_ticket=="TESTSEL")] | length'` 實查 30 條）——TESTSEL 收案後即無此 owner，每條須修後自登記移除，或改歸實際負責之產品票（owner 與 `為何現在不做: blocked-by:…|user-ruling:…`）；收案時 owner＝TESTSEL 之條目數須為 0。
- **驗證（可證偽）**：檢查腳本：清單覆蓋 Phase 0 全部紅（以 log 當場取母體）、disposition=fixed 者實跑通過、allowed_red 者在 `allowed_red.json` 且附 `為何現在不做`；`allowed_red.json` 中 `owner_ticket=="TESTSEL"` 之條目數 == 0；mutation：刪一列／把 fixed 標給仍紅者／留一條 owner TESTSEL ⇒ rc≠0。
- **邊界**：①測試過時但產品值未經獨立 oracle 比對 ⇒ 修測試同時補 oracle 斷言（如 entropy 欄值以獨立算法驗）；②資料重生改變凍結值 ⇒ 三方簽核。
- **存活至**：I1 收案。　**覆蓋風險**：無。
- 不可做：不以放寬斷言換綠；不整批改釘值。

## §V 驗證策略與邊界測試目錄
- mutation：各 Task 已列；Task 1.1／1.4／3.2 之 mutation 為必跑。
- 測試層級：單元（pytester 隔離偵測）、整合（依序重放）、Golden（§G）。
- 防假綠：diff 既有斷言；釘值改動須附漂移原因與獨立 oracle；不 skip／xfail。
- 邊界目錄：並發寫（Task 1.1）、符號連結根（Task 1.1）、空快取／命中快取（Task 3.2）、長行程狀態（Phase 2）、網路失敗（Task 1.6）。

## §R 回退
- 每 Phase 獨立提交可單獨 revert；Task 1.1 改為 session 非零若誤擋並行正式寫入，可單獨 revert 該提交回到只報；Task 1.6 以備份還原。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- 殘留：產品碼 `data_cache` 字面路徑未經 `MomentumConfig.data_cache_path`（Rule 5）— `為何現在不做: blocked-by:I1 範圍為測試隔離；改產品預設路徑屬跨模組改動（命中 b），須另開票走大任務流程`；觸發：I1 收案時開票；登記處：`docs/ROADMAP.md` pointer。
- 殘留：治理測試依賴未入版控之本機檔（約 92 條）— `為何現在不做: blocked-by:大綱 I7（治理分層）已定義`；觸發：I7 開工；登記處：大綱 I7 列。
