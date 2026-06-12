# Batch6 三方簽核 — Claude 獨立驗證清單(自產版,先於 Composer 實作完成前寫定)

> 目的:V-9 三方簽核時,我不只看執行端測試綠,而是對照本清單逐項親驗。
> 本清單獨立於執行端實作寫成,不餵給 Composer(保持獨立性)。

## A. 生成正確性(V-3)
- [ ] 健康全量 run(BTCUSDT/12h baseline 視窗,CGSA,flag 全預設)L1-L6 per-layer canonical hash == tests/_golden/failopen/baseline.json(Gate-A,既有)。
- [ ] L7_raw artifact 內容 hash 與 Batch1 前(eccca5f^)同輸入重跑一致——若 baseline 涵蓋不到 L7,以 d* cache 命中序列+輸出 parquet 大小+欄數三證據替代。
- [ ] 五情境故障矩陣 quality_status:整層失敗→partial(allow)或 raise(預設)/NaN 超標→partial/部分 TF 失敗→failed_timeframes 記錄/CGSA TF 失敗→rollback 後 raise/L6.5 失敗→complete 但 preprocessing_applied=False。各 == 斷言,真實 generate 非合成。

## B. PIT/無洩漏(V-5)
- [ ] prefix 不變量:full 視窗 run 與「截去尾端 N 根」run,共同前綴(扣 warmup)逐 byte 一致(因果化後必須成立;winsor sliding/fracdiff/ADF 都已因果)。
- [ ] 注意陷阱:比對須同 dtype 同欄序;NaN mask 單獨比;不得用 atol(byte-identical 鐵律)。

## C. 多 TF 對齊(V-6)
- [ ] 獨立 as-of oracle:手寫「對每個 primary timestamp 取 training TF 中 ts<=t 的最後一根」,不呼叫 TimeframeAligner;抽 ≥3 欄全行比對 oracle vs 實際輸出。
- [ ] searchsorted 與 merge 兩 backend(FFACT_USE_SEARCHSORTED 0/1)輸出 byte 一致。
- [ ] 邊界:TF 邊界整除點(12h 收盤恰逢 1h 收盤)不得取到 t 當根未收盤資料(嚴格 <=t 收盤)。

## D. 隔離/重現(V-7)
- [ ] 跨 symbol:擾動 ETHUSDT 輸入(或只跑單 symbol)不改 BTCUSDT 輸出 hash。
- [ ] 順序置換:[BTC,ETH] vs [ETH,BTC] 各 symbol 輸出 hash 不變。
- [ ] cache 冷熱:force_regenerate=True vs cache 命中,讀回值一致。
- [ ] resume == fresh:中斷後 resume 的最終 artifact hash == 一次跑完。

## E. 簽核程序(V-9)
- [ ] Composer(實作者)出測試+自驗報告。
- [ ] Codex 獨立 review 測試設計可證偽性+親跑(或 read-only 核對實跑 log)。
- [ ] Claude 親跑全部新測試+本清單抽驗+diff 既有斷言。
- [ ] 三方皆「資料正確」才結案;任一方疑→不過(不催收斂)。
- [ ] FROZEN_TESTS 與全部 diff 100% 對照。
