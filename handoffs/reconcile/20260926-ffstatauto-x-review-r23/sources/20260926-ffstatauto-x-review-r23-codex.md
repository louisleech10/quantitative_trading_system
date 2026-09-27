## CODEX-R23-P2-01

**斷言**: v42 §G⑦ 已指定以長歷史快取的 `cache_dir` 做 12h 實測，但沒有把已知 BTC/ETH 12h 缺口的連續性處理寫成可重現操作。對長歷史快取採預設連續性驗證會在 Fmax／資格收據前失敗；明確使用既有的 `validate_continuity=False` 才能讀取資料。這是非阻塞的 code-contract 操作缺口，不是資料不足本身的 finding。

**碼證**: `docs/FFSTAT_SPEC.md:92` 只寫「以儲存層之 `cache_dir` 指向」；`momentum/DataExtraction/kline_storage.py:1052` 的 `read_klines` 預設 `validate_continuity=True`，`:1111-1113` 對缺口拋出 `ValueError`。在隔離複本執行 `env PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe_default_continuity.py`，真實 `BTCUSDT/12h` 輸出 `DEFAULT_CONTINUITY_REJECTED ValueError`，缺口為 `2018-02-08 12:00:00 UTC`；同一複本以 `create_kline_storage_manager(cache_dir="data_cache/feature_klines_longhist").read_klines("BTCUSDT", "12h", validate_continuity=False)` 讀得 `6656` 列。`momentum/factories.py:238-249` 已提供 `create_feature_factory(..., validate_continuity=False)`，故反例可由現有 API 重現及修正。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#4f10344303eb; momentum/DataExtraction/kline_storage.py#0e1fca9defc4; momentum/factories.py#73c06e7604e2; handoffs/run_receipts/20260927-ffstat-longhist-download.log#960155b7fe59; handoffs/20260926-FFSTATAUTO-X-REVIEW-R23-BRIEF.md#1a88446b1f75

修法：將 §G⑦ 的 12h 操作補成封閉序列，明寫長歷史快取讀取使用 `validate_continuity=False`，並在收據記錄缺口數與時間點；若未來選擇修復資料，則須以真實下載後的 gap-free 收據取代此路徑。較小修法已有可行性證據：同一真實 HDF5 以現有 factory/storage API、只切換該既有參數即可讀取 6,656 列，沒有新增生成期機制，也不改預設快取或資料。

(1a)/(1b) 本家 r22 的 `CODEX-R22-P1-01` 已閉合：v42 逐字加入實測 `F_max_12h`、各欄首有限值、`6,656−(M_tf＋F_max_tf＋500)` 與資格結果，且不合資格時改交使用者三擇一；本輪沒有把尚待實作後取得的 Fmax 當成 finding。`CODEX-R22-P1-02` 也已閉合：v42 封閉為 ADXR、`period_keys=timeperiod`、period 233，並要求收據列 mutant 前後 K、首有限值、重疊列數與 normalized error，同時明記 EMA5 不紅的界線。前者採條文閉合核對、後者兼有下列真實 1h TA-Lib 小探針；兩條沒有遺留 P1。

(2a)/(2b) v42 有一項新的非阻塞 P2，即本 finding。可重現反例是：把真實 `data_cache/feature_klines_longhist/kline_cache.h5` 複製到隔離工作目錄，建立 `cache_dir` storage，對 `BTCUSDT/12h` 呼叫預設 `read_klines`；既有收據同樣記錄該時間點缺口，預設路徑在產生 Fmax 前拒讀。顯式 continuity 參數的成功路徑已實跑，因此不升級為 P1。

(3a)/(3b) 第一條 assumed（刪 L1 遮罩、縮尾不遮、第④類不遮三個 mutant 各至少一欄紅）本輪判為「未成立為已證實 invariant」：brief 明載尚未跑，且本輪遵守不跑全設定 FF；沒有把未跑本身列成 finding。第二條 assumed（固定 ADXR 233 的係數 mutant 會紅）判成立：真實 BTCUSDT/1h 小探針以 period=233、K=233 的係數 1.0，eval 500 輸出 `NORMALIZED_ERROR=0.5683817772164229 RED=True`；對照 EMA5、係數 1.0、K=5 輸出 `0.0007597101797533 RED=False`。eval 1000 的 ADXR 仍為 `0.0611462765144765 RED=True`，EMA5 為 `0.0008152637276039 RED=False`。這也與 r22 已記錄的 ADXR 紅／EMA5 不紅邊界一致。

(4a)/(4b) 「我沒查」① 命中的是操作文件缺口，storage/factory 本身可行，證據就是本 finding 的拒讀／`validate_continuity=False` 成功成對探針。② 未命中：真實 BTCUSDT/5m `105260` 列、`eval-window=1000`、`max-K-cap=4000` 的 verifier 直接執行 rc=0，搜尋輸出 `Loaded 105260 bars`、`Search finished in 0.3s`、`--no-write`；Darwin `RUSAGE_CHILDREN.ru_maxrss=139575296` bytes（約 133.0 MiB）。這是倍數量測腳本的 39 個實際測試，不宣稱是完整 FF run。③ 未命中：三標的真實 12h verifier rc=0，BTC/ETH 各 `6656` 列、ADA `6171` 列；consolidated ADXR factor `7.93`、max K `1694`，每標的 `BTC=7.92, ETH=6.61, ADA=7.27`，且其他指標由 ADA 驅動的 max 也被保留，未見跨標的 max 漏取。

(5a)/(5b) 本版可 `VERDICT: proceed`；唯一新 finding 為可在施工前補清楚的 P2，沒有 P0/P1 擋項。r22 兩條 P1 的閉合不依賴本輪尚未執行的全設定 FF 或 Fmax 生成。

ASSUMPTIONS_VERIFIED: 已讀本輪 brief、HANDOFF.md、CLAUDE.md、v42 target diff、r22 synth、R1–R9 rulings 與 canonical template；逐字核對 r22 兩條 P1 的 v42 修訂；以真實長歷史 HDF5 重現預設 continuity 拒讀與顯式參數成功；實跑 5m verifier、三標的 12h verifier、ADXR233/EMA5 mutation probe；確認 ADA 參與跨標的 max。
TESTS_RUN: `env PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe_default_continuity.py` → expected `ValueError` with `2018-02-08 12:00:00 UTC`, wrapper rc=0；`env PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python scripts/verify_l1_warmup_requirements.py --symbol BTCUSDT --tf 5m --eval-window 1000 --max-K-cap 4000 --no-write` → program rc=0, 105260 bars, 0.3s search；resource wrapper → `CHILD_RU_MAXRSS=139575296` on Darwin；same verifier with `--symbols BTCUSDT ETHUSDT ADAUSDT --tf 12h --eval-window 1000 --max-K-cap 4000 --no-write` → rc=0, rows 6656/6656/6171, consolidated ADXR max factor 7.93/K1694；`probe_adxr_mutant.py` → ADXR K233 red and EMA5 K5 non-red for eval 500/1000。
FAILURES_SEEN: 初次 `/usr/bin/time -l` wrapper 在程式成功後因 Darwin `sysctl kern.clockrate: Operation not permitted` 回 rc=1，改以直接執行確認 verifier rc=0；初次 `ps` RSS sampler 受 sandbox `Operation not permitted`，改用 `resource.getrusage(RUSAGE_CHILDREN)` 完成峰值量測；指定 completeness 命令被 PreToolUse dispatch gate 在執行前攔截，未取得 rc，依 brief 停止且未改寫／繞過命令。
SCOPE_CHANGES: none；唯讀複本探針，未改 momentum、api、scripts、tests、docs、templates、config、SPEC、manifest、git history 或 data_cache；僅寫本交件檔與 append-only 狀態交接。
NUMERIC_OR_SCHEMA_IMPACT: none；沒有修改專案數值、schema、輸出大小或測試斷言；報告中的數字均為實跑觀測。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r23-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R23.md
TMP_CLEANUP: 因 completeness 命令遭 PreToolUse gate 攔截後依 brief 停止，未執行清理；`/tmp/ffstat-r23-JFuGco` 尚存，`/tmp/claude-501` 未動。
STATUS: BLOCKED — completeness command blocked by PreToolUse dispatch gate; rc unavailable

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R22-P1-01,CODEX-R22-P1-02
