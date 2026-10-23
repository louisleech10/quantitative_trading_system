# D-ICPAGE-ARM 前提出處證據（SPEC v30 §A、Task 1.5、設計選擇 9 引用；規格審查 r18 CODEX-R18-P1-03）

## 一、2026-10-20 主委未經實測之說法（原文逐字摘錄）

- 出處：Claude Code 對話紀錄 `~/.claude/projects/-Users-louis-Desktop-quantitative-trading-system/04fd3c82-0003-4937-8e8b-cfed1c292e22.jsonl`（repo 外），assistant 訊息 timestamp `2026-10-20T22:57:29.675Z`。
- 逐字摘錄：

> - **快**：Polars 是現有最快的一套，IC-first 也已經固定用它。
>   - 改高精度會慢一點，但這一步只處理 IC 選出的幾百欄，原本就是秒級，慢一點感覺不到。

- 使用者 2026-10-21 鎖 Polars 之裁定以此為前提；使用者 2026-10-23 逐字：「Polar是你沒查證就說最快，我完全是被你誤導，是你沒把事實證明，我才做錯誤裁定」。

## 二、實測反證（探索性證據：單次、含讀寫，非 Task 1.1 三次中位）

出處：Task 0.5 凍結錄製之子行程日誌 `data_cache/numview_freeze_runs/_results/<格>/child.log`（不入版控；日誌時間為 UTC）之 G1（IC 頁第三步，各臂依序單次、含讀檔與寫檔）起訖行，原文：

```
[freeze 23:26:35] A_BTCUSDT_1h：G1 polars 開始（選欄 3193）
[freeze 23:28:05] A_BTCUSDT_1h：G1 polars 完成（實際臂 polars）
[freeze 23:28:05] A_BTCUSDT_1h：G1 pandas_optimized 開始（選欄 3193）
[freeze 23:28:13] A_BTCUSDT_1h：G1 pandas_optimized 完成（實際臂 pandas_optimized）
[freeze 23:28:13] A_BTCUSDT_1h：G1 pandas_legacy 開始（選欄 3193）
[freeze 23:28:21] A_BTCUSDT_1h：G1 pandas_legacy 完成（實際臂 pandas_legacy）
[freeze 23:28:21] A_BTCUSDT_1h：G1 pandas_chunked 開始（選欄 3193）
[freeze 23:28:29] A_BTCUSDT_1h：G1 pandas_chunked 完成（實際臂 pandas_chunked）
[freeze 23:33:36] A_BTCUSDT_4h：G1 polars 開始（選欄 2709）
[freeze 23:34:53] A_BTCUSDT_4h：G1 polars 完成（實際臂 polars）
[freeze 23:34:53] A_BTCUSDT_4h：G1 pandas_optimized 開始（選欄 2709）
[freeze 23:35:00] A_BTCUSDT_4h：G1 pandas_optimized 完成（實際臂 pandas_optimized）
[freeze 23:35:00] A_BTCUSDT_4h：G1 pandas_legacy 開始（選欄 2709）
[freeze 23:35:07] A_BTCUSDT_4h：G1 pandas_legacy 完成（實際臂 pandas_legacy）
[freeze 23:35:07] A_BTCUSDT_4h：G1 pandas_chunked 開始（選欄 2709）
[freeze 23:35:14] A_BTCUSDT_4h：G1 pandas_chunked 完成（實際臂 pandas_chunked）
[freeze 23:38:05] A_BTCUSDT_12h：G1 polars 開始（選欄 2539）
[freeze 23:39:17] A_BTCUSDT_12h：G1 polars 完成（實際臂 polars）
[freeze 23:39:17] A_BTCUSDT_12h：G1 pandas_optimized 開始（選欄 2539）
[freeze 23:39:23] A_BTCUSDT_12h：G1 pandas_optimized 完成（實際臂 pandas_optimized）
[freeze 23:39:23] A_BTCUSDT_12h：G1 pandas_legacy 開始（選欄 2539）
[freeze 23:39:28] A_BTCUSDT_12h：G1 pandas_legacy 完成（實際臂 pandas_legacy）
[freeze 23:39:28] A_BTCUSDT_12h：G1 pandas_chunked 開始（選欄 2539）
[freeze 23:39:34] A_BTCUSDT_12h：G1 pandas_chunked 完成（實際臂 pandas_chunked）
[freeze 23:42:32] A_SOLUSDT_1h：G1 polars 開始（選欄 3029）
[freeze 23:43:57] A_SOLUSDT_1h：G1 polars 完成（實際臂 polars）
[freeze 23:43:57] A_SOLUSDT_1h：G1 pandas_optimized 開始（選欄 3029）
[freeze 23:44:08] A_SOLUSDT_1h：G1 pandas_optimized 完成（實際臂 pandas_optimized）
[freeze 23:44:08] A_SOLUSDT_1h：G1 pandas_legacy 開始（選欄 3029）
[freeze 23:44:19] A_SOLUSDT_1h：G1 pandas_legacy 完成（實際臂 pandas_legacy）
[freeze 23:44:19] A_SOLUSDT_1h：G1 pandas_chunked 開始（選欄 3029）
[freeze 23:44:30] A_SOLUSDT_1h：G1 pandas_chunked 完成（實際臂 pandas_chunked）
```

由上計得（秒）：

| 格（選欄數） | polars | pandas_optimized | pandas_legacy | pandas_chunked |
|---|---|---|---|---|
| A_BTCUSDT_1h（3193） | 90 | 8 | 8 | 8 |
| A_BTCUSDT_4h（2709） | 77 | 7 | 7 | 7 |
| A_BTCUSDT_12h（2539） | 72 | 6 | 5 | 6 |
| A_SOLUSDT_1h（3029） | 85 | 11 | 11 | 11 |

另一份單次探索性收據 `handoffs/run_receipts/numview_probes/20261022-icpage-arm-timing-adhoc.json`（未綁判準雜湊；SPEC v22 冒煙實測載明當時 chunk 預設 2000、選欄逾 2000 ⇒ optimized／legacy 實走 chunked）記 A:1h polars 89.90 秒、pandas 6.91 秒，方向一致。

## 三、證據等級

以上皆單次、含讀寫，只證「Polars 最快」前提不成立；正式各臂速度以 Task 1.1 效能基準（各臂三次中位、只計轉換、含 Polars 慢因剖析）為準，並據以重新呈報使用者（SPEC §A 重新呈報條件）。
