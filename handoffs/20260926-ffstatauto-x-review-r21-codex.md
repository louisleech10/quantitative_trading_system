# FF-STAT SPEC v40 審查 r21 — CODEX

審查標的為 `git diff 3ff787e1f08326631ad9e7a2d89a4beb78525df2 38ca213780dd5ec9718e06f2daa3650877deceb3 -- docs/FFSTAT_SPEC.md`；本輪未改 source、SPEC、manifest、template、CLAUDE.md、git history 或 `data_cache/`。

## CODEX-R21-P1-01

**斷言**: v40 同時要求 §G⑦ 依 `M_tf + F_max_tf + 500` 與每欄 500 列重疊資格判定，又要求 BTC/12h 6,656 根的長歷史「不得以 blocked 收場」；以目前已存在且納入 1h 測量的 ADXR 233 週期下限計算，6,656 根不可能滿足該資格。

**碼證**: `docs/FFSTAT_SPEC.md:90` 定義 `M_tf=K_max_tf+F_max_tf`、列數與欄重疊不足即 blocked，且同一行對 12h 寫「不得以 blocked 收場」。`config/scan_config.yaml:135-136` 啟用 ADXR 並含 period 233；`momentum/FeatureEngineering/atomic/warmup_table.yaml:25-28` 之 1h 表值為 factor 8.8、`max_K_observed=2049`，故按表公式 `ceil(233*8.8)=2,051`。`docs/FFSTAT_SPEC.md:59` 的 L6.5 完整 252 窗使 `F_max >= 2,051+251=2,302`；`handoffs/run_receipts/20260927-ffstat-longhist-download.log:191-193` 實際記錄 BTC/ETH 12h 各 6,656 根。唯讀算式命令 `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -c 'k=2051; f=k+251; required=k+2*f+500; overlap=6656-(k+2*f); print(f"K_max={k} F_lower_bound={f} required_rows={required} overlap_for_Fmax={overlap}")'` 輸出 `K_max=2051 F_lower_bound=2302 required_rows=7155 overlap_for_Fmax=1`。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:90
MUTATION: 將 §G⑦ 的輸入固定為真實 BTCUSDT/12h 6,656 列，並以慢欄 `F=2,302` 執行資格判定；預期列數不足與單欄重疊 1 列分支被觸發，若同時套用「不得以 blocked 收場」則該 v40 驗收序列無法產生 pass。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#9060a56e2903; config/scan_config.yaml#0dc95e4f0a10; momentum/FeatureEngineering/atomic/warmup_table.yaml#d1fbdeae67c8; handoffs/run_receipts/20260927-ffstat-longhist-download.log#960155b7fe59; handoffs/20260927-ffstat-b4-redesign-rulings.md#3c6909ea0b9a

這是 v40 新增長歷史驗收路徑的 blocking contract defect，不是把資料不足誤報成既有實作缺陷。`§G⑦` 的一般規則明定不合資格要輸出 blocked，而 R8 又排除以資料不足 blocked 收場；目前可用真實資料與已知 L1 下限的算式已把兩者分開證成互斥。長歷史收據另記錄 BTC/ETH 12h 各有一處缺口及 post-write verification failed（`:63-66`、`:129-132`），因此 6,656 的 row count 也沒有提供 7,155 根合資格重疊的證據。

修法選項是先完成一個使用者核可的可行性決策：要嘛提供真實且至少達到該資格下限的 12h 輸入，要嘛修訂資格公式／「不得以 blocked」規則；現有 Binance 全史自 2017-08-17 僅收得 6,656 根，不能以補值、刪欄、放寬 gate 或 fake data 關閉。可行性證據是所需數字可由現有 SPEC、實際 warmup table、預設 config 與長歷史收據重算，且失敗分支已由 §G⑦ 明確定義；這代表修法邊界可被機械驗證，而非需要再加一層機制。

## CODEX-R21-P2-02

**斷言**: v40 版本註記宣稱已刪除 §N 的 12h blocked 殘留，但現行 `docs/FFSTAT_SPEC.md:180` 仍保留「1,696 根、blocked-by、需更長真實 12h 歷史」的 v39 文案，與 v40 §G⑦ 的長歷史路徑及「不得以 blocked 收場」直接矛盾。

**碼證**: `git diff --unified=6 3ff787e1f08326631ad9e7a2d89a4beb78525df2 38ca213780dd5ec9718e06f2daa3650877deceb3 -- docs/FFSTAT_SPEC.md` 顯示舊的 §G⑦ 1,696 blocked bullet 已被刪除，但 `nl -ba docs/FFSTAT_SPEC.md | sed -n '180p'` 仍輸出 `12h 校準長度：...1696 根...為 blocked-by：需更長之真實 12h 歷史`；同一檔 `:4`、`:90` 已改指向 `data_cache/feature_klines_longhist/` 與 6,656 根。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#9060a56e2903; handoffs/20260927-ffstat-b4-redesign-rulings.md#3c6909ea0b9a; handoffs/run_receipts/20260927-ffstat-longhist-download.log#960155b7fe59

此殘留不是純字面差異：施工者可依 §N 保留 1,696 根 blocked 路徑，或把新長歷史驗收誤判為尚未解除的 N/A。修法是移除或改寫該單行殘留，使它只描述仍適用的非加密貨幣範圍；不需要新增運算層。可行性證據是 v40 diff 已經移除相鄰的舊 §G⑦ bullet，且長歷史下載收據已記錄 BTC/ETH 12h 6,656 根與獨立快取路徑，因此此修正是局部文字同步。

**(1a) 本家 r20 findings 是否閉合**：`CODEX-R20-P3-00` 是 r20 本家零 finding sentinel；r20 synth 記載 r19 四條由原提出方確認閉合，且 r20 本輪沒有個別 finding 可重新開啟。本輪對 v40 diff、r20 synth、R8/R9 及目前 §C／§G／§P／§N 對位後，確認 r20 sentinel 可閉合。

**(1b) 原反例／條文核對**：以 `git diff --stat 3ff787e1 38ca2137 -- docs/FFSTAT_SPEC.md` 確認本輪僅為 v40 長歷史、倍數週期、收據與 §N 文字變更；逐字核對 `handoffs/reconcile/20260926-ffstatauto-x-review-r20/synth.md:22-65` 與現行 SPEC，未把 v39 以前未改動條文重報。新的 §G⑦／§N 交叉核對產生本輪 P1-01 與 P2-02。

**(2a) v40 新 defects**：有。P1-01 是新長歷史驗收的資格算式與「不得以 blocked」互斥；P2-02 是 v40 明示要刪而仍留存的 1,696 blocked 殘留。

**(2b) 可重現反例**：P1-01 的真實輸入為收據記錄的 BTCUSDT/12h 6,656 列，操作序列是按 `docs/FFSTAT_SPEC.md:90` 計算 `K=2,051`、`F>=2,302`、`M+F+500=7,155`，並以絕對時間欄重疊計算；算式輸出要求 7,155 根且 Fmax 欄只剩 1 列重疊。P2-02 的反例是同一 v40 檔案中 `:4/:90` 已寫長歷史且禁止 blocked，`:180` 仍宣稱 1,696 根 blocked-by。

**(3a) 兩條 assumed 判定**：①「預設全設定 BTC/12h 6,656 根可滿足列數資格」不成立：目前 1h 測量已給出 K 的 2,051 下限，v40 自己的 L6.5 +251 契約把要求推至 7,155。②「每個受驗慢欄可保有至少 500 列重疊」不成立於同一已知下限：F=2,302 的欄在 6,656 根資料上只剩 1 列重疊；即使不把目前表值視為最終表，v40 也尚未提供一個可使此假設成立的資料／參數證明。

**(3b) 碼證／數字**：`config/scan_config.yaml:135-136` 的 ADXR period 233；`warmup_table.yaml:25-28` 的 factor 8.8；`docs/FFSTAT_SPEC.md:58-59,90` 的 K 與 L6.5 規則；`20260927-ffstat-longhist-download.log:191-193` 的 6,656 rows；算式命令輸出 `K_max=2051 F_lower_bound=2302 required_rows=7155 overlap_for_Fmax=1`。這是 lower-bound proof，沒有把未執行的全 FF run 宣稱為已驗證。

**(4a) brief 未查三項**：①儲存層 `cache_dir` 注入命中；`create_feature_factory(cache_dir=...)` 會把路徑傳至 storage，長歷史下載腳本也以獨立 `cache_dir` 建立 storage。命名的倍數量測腳本目前仍以固定 `KLINE_PATH` 讀一般快取，但該檔案本身列在 Task 2.4 的待施工範圍，故本輪將其列為實作接線前提而非額外 SPEC finding。②5m 一年 105,260 根的記憶體／耗時未跑全量量測，沒有足夠證據列 finding。③ADA 12h 較晚起點未做跨標的最大值的全量腳本驗證；SPEC 已明定 BTC／ETH／ADA 取最大，現有收據僅證明 ADA 12h 為 6,171 根，故本項未命中可重現的新 SPEC defect。

**(4b) code evidence**：①`momentum/factories.py:236-249`、`momentum/DataExtraction/kline_storage.py:230-238`、`handoffs/run_receipts/20260927-ffstat-longhist-download.py:17-36` 顯示 cache_dir 從 factory 到 HDF5 path 的接線；`20260927-ffstat-longhist-download.log:191-193` 與 `20260927-ffstat-longhist-download-5m-1d.log:1757-1762` 顯示真實長歷史列數。量測 verifier 的目前接線證據為 `scripts/verify_l1_warmup_requirements.py:49-70` 固定 `data_cache/feature_klines/kline_cache.h5`，`:369-388` 沒有 `--cache-dir`；這是 Task 2.4 實作時需留下 resolved cache path 收據的風險，沒有被誤報為已完成的 v40 implementation。②腳本 CLI 明示 `eval-window=1000`、`max-K-cap=4000`（`:369-389`），5m 105,260 根只做資料收據核對，未執行全量指標量測。③ADA 收據行 `1761`（1d/5m）與 12h 收據行 `193` 證實較晚起點／較少列數；沒有執行會把它誤外推成最大值的腳本。

**(5a) 是否可定案 `VERDICT: proceed`**：不可以。P1-01 使 v40 12h 核心驗收在目前真實輸入與自身公式下無法同時得到合資格 pass；P2-02 另需同步修正文案。

**(5b) blocking IDs**：`CODEX-R21-P1-01`。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、本輪 brief、v40 target diff、r20 synth、R8/R9 ruling、finding template 與 governance category allowlist；已核對 r20 closure、v40 新 diff、兩條 assumed 與三項 not-checked；長歷史數字、ADXR lower bound、L6.5 +251、cache_dir 接線與殘留行號均有實際檔案／命令證據。
TESTS_RUN: `git diff --stat 3ff787e1 38ca2137 -- docs/FFSTAT_SPEC.md` → `docs/FFSTAT_SPEC.md | 19 ++++++++++---------`; `nl -ba`／`rg -n` 核對 SPEC、config、warmup table、verifier、factory、storage 與 receipts；`env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -c 'k=2051; f=k+251; required=k+2*f+500; overlap=6656-(k+2*f); print(...)'` → `K_max=2051 F_lower_bound=2302 required_rows=7155 overlap_for_Fmax=1`; `git status --short -- momentum api scripts tests docs templates config` 開跑前後均未新增本輪 source 變更；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r21-codex.md --family codex --round-id aeb6cbcb-1723-43ed-98e7-72cdf8048e49` → `COMPLETENESS PASS(single)`, rc=0。
FAILURES_SEEN: 建立 `/tmp` 複本的複合命令因 PreToolUse hook 拒絕 `rm -f` 而未執行；收尾精確刪除三個本輪複本的 `rm -rf -- /private/tmp/ffstat-r21-work /private/tmp/ffstat-r21-z5DqdN /private/tmp/ffstat-r21-copy-1aMiPK` 亦被同一安全閘拒絕。兩次均依 brief 停止，未改寫形式。隔離 probe 初次以 `inspect.py` 命名造成 stdlib shadowing；改名後 probe 讀取真實 longhist rows（BTC/ETH 12h 6,656、1d 3,329、5m 105,260；ADA 12h 6,171、1d 3,086、5m 105,260）並在最後的 table pretty-print 遇 `AttributeError: 'float' object has no attribute 'get'`；未以第三輪繞過或執行全 FF。長歷史 BTC/ETH 12h 的既有收據 continuity verification failure 已如實列於 P1 evidence。
SCOPE_CHANGES: none；只新增本輪指定 committee 交件檔與 append-only 狀態交接檔，未修改 source、SPEC、manifest、templates、CLAUDE.md、git history 或 `data_cache/`。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪唯讀審查，未改數值、schema、輸出大小或測試斷言；算式與 probe 只讀真實資料／其複本。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r21-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R21.md
TMP_CLEANUP: 依序嘗試刪除 `/private/tmp/ffstat-r21-work`（8.0K）、`/private/tmp/ffstat-r21-z5DqdN`（11M）、`/private/tmp/ffstat-r21-copy-1aMiPK`（869M）；`rm -rf --` 被環境安全閘拒絕，三者仍在。`/tmp/claude-501`（145M）已確認存在且保留。
STATUS: DONE

VERDICT: blocked
BLOCKED-BY: CODEX-R21-P1-01
CLOSED: CODEX-R20-P3-00
