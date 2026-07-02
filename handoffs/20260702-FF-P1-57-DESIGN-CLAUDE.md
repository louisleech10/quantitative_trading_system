# P1-FF-5 + P1-FF-7 測試設計 — Claude 獨立版（待 Codex/Composer 挑戰）

藍圖出處:`handoffs/20260627-FF-AUDIT-RECONCILE.md` 5/7 項。真實 kline(`data_cache/feature_klines/kline_cache.h5`),禁合成 fixture 當驗收(保真度鐵律)。慢測驗證一律排在當前 mutation run 之後(序列防 OOM)。

## A. P1-FF-5 跨 symbol 值隔離 MR(新檔 tests/feature_engineering/test_ff_cross_symbol_isolation_mr.py)

**威脅模型**:多 symbol 批次時,B 的存在/順序改變 A 的特徵值、d*、metadata(共享 rolling 狀態、cache key 撞名、全域狀態殘留)。現有隔離只驗 path/shard,未驗「值」。

**設計(MR 三跑)**:同窗真實 kline,A=BTCUSDT、B=ETHUSDT(1h,窗長比照 B2 600 bar 規格):
1. run₁ = only A;2. run₂ = batch [A,B];3. run₃ = batch [B,A](順序反轉)。

**不變量(對 A 的工件)**:
- V5.1 值:A 的每特徵 parquet 三跑逐值一致(float 容忍度沿 B2 值 gate 標準;float16 欄依既有 caveat)。
- V5.2 d*:A 的 d_star json 三跑鍵值全等(d* 只依 A 自身 prefix,B 不得影響)。
- V5.3 metadata:A 的 manifest(行數/欄集/schema)三跑一致。
- V5.4 無滲漏:A 的工件內不得出現 B 的 symbol 字串/欄。

**mutation 探針(≥1,章程 B1;shape 沿 v2 定式:正向偵測斷言在 raises 外)**:
- M5.1 注入共享狀態污染:patch 快取鍵或 rolling 狀態使 A/B 共用(如去掉 key 中 symbol 成分)→ V5.1/V5.2 必紅。

**邊界**:全域 config 相同屬合法共享;dict 順序不穩不得當隔離破壞誤報。

## B. P1-FF-7 wrapper 多路徑正確性(新檔 tests/feature_engineering/test_ff_wrapper_paths.py)

**威脅模型**:①TA-Lib wrapper 餵錯 source/price 欄或參數(B1 已抓 BETA/CORREL 真 bug,已部分 audit wrapper source→只補殘餘,不重測 B1 已蓋);②Pandas/Polars/Numba 多路徑同輸入不同輸出(靜默分歧);③float16 lossy 未明示。

**設計**:
- V7.1 source/欄殘餘 audit:對 B1 未蓋到的 wrapper(以 B1 產物清單 diff 出殘餘集)靜態+單指標實跑:輸入欄擾動(swap high/low)→輸出必變;餵錯欄組合→與 canonical 參考不符。
- V7.2 多路徑等值:同一段真實 kline(單 symbol 短窗,分鐘級可跑,不必全鏈),對每個有多引擎實作的計算:pandas vs polars vs numba 輸出逐值比(容忍度明訂;超容忍=紅)。路徑覆蓋以 config 強制切換,斷言真的走到該引擎(防靜默 fallback——斷言執行路徑證據,非只看輸出)。
- V7.3 float16 lossy 明示:對 float16 儲存欄,量測並斷言誤差上界(≤既有 caveat 0.1%),超界=紅;文件化為明示邊界。

**mutation 探針**:
- M7.1 swap 一個 wrapper 的輸入欄(如 high↔low)→ V7.1 必紅。
- M7.2 patch 引擎選擇使聲稱 polars 實走 pandas → V7.2 路徑證據斷言必紅。

**邊界**:引擎間合法的 dtype/NaN 邊緣差異須列白名單並附理由,不得靜默放寬容忍。

## C. 驗證策略(兩檔共通)
- 慢測分級:V7.2/V7.3 單 symbol 短窗(~分鐘級);P1-FF-5 三跑全鏈(~1.5h)排 mutation run 後。
- 全部經 `run_with_receipt`;探針過 `mutation_probe_static`;先單測快驗再全套(align oracle 教訓)。
- 不動 production;不放寬既有斷言;測試副作用還原(golden inventory)。

## D. 給委員的問題
1. V5.1 三跑成本(3×全鏈)可否縮為兩跑(only-A vs [B,A])仍保威脅覆蓋?
2. V7.2 的「路徑證據斷言」用什麼機制最不脆(log capture/內部 counter/monkeypatch 標記)?
3. 我漏了哪些跨 symbol 污染面(如 L5 reference、全域 registry)?
