# L65 B3b 資料正確性簽核 — Composer（三方之一）

**日期**: 2026-06-18 | **任務**: 移 legacy L6.5(IC-First 唯一) + causal 釘死 True  
**資料**: `data_cache/feature_klines/kline_cache.h5`（10 symbol × 3 TF）  
**方法**: 獨立腳本 `/tmp/composer_l65_signoff_verify.py`（非 rerun `validate_l65_data_correctness.py`）

## 檢查結果

| ID | 不變量 | 結果 | 關鍵數字 |
|---|---|---|---|
| C1 | IC-First L6.5 byte parity（獨立重算 fingerprint vs frozen JSON） | **PASS** | 12 stage 比對（3 sym×2 tf×pre/post_ic）；mismatch=0；max_stat_diff=0.0 |
| G0 | 官方 golden `--check`（佐證） | **PASS** | 6 records stable |
| C2 | causal PIT 無 look-ahead | **PASS** | `forced_true=True`；log warn 捕獲；外部 False 輸出==顯式 True；尾端竄改(n-50)前綴(n-100)不變；校準窗後(>550)竄改前綴不變 |
| C3 | 跨 symbol/TF 隔離 | **PASS** | 30 對（10×3）post_ic schema hash 唯一=1；nan_ratio 0.160–0.229；BTC→ETH 同實例 d* 無污染 |
| C4 | NaN/inf gate 未弱化 | **PASS** | 注入 inf 後 output_inf=0；全 NaN 欄輸出 nan_ratio=1.0；重跑 byte 一致 |
| C5 | multi-TF merge 前後值守恆 + PIT | **PASS** | primary=600 rows；4h/12h align 各 600；leak_check 4h/12h=True；L6.5 pre/post_ic 均 600；竄改 4h 尾端 primary 欄前 400 行不變 |

## 獨立角度說明（vs Claude/Codex）

- **C1**: 直接讀 `tests/golden/l65_hardening/*_baseline.json` 重算 live fingerprint，非僅信 `--check` 退出碼。
- **C2**: 雙切點 PIT——尾端竄改 + 校準窗(500 bar)後中段竄改；中間切點在 fracdiff 校準窗內會改 d*（預期），不當 FAIL。
- **C3**: 全 10 symbol×3 TF（非 5×1）；d* cache 跨 symbol 連續處理污染檢查。
- **C5**: `TimeframeAligner` 直接驗 row 恆等 + tz-normalized source≤primary + L6.5 後列數 + 4h 尾竄改 primary 原生欄 PIT。

## 簽核

**資料正確** — 本任務宣稱（IC-First byte 不變、causal 釘死無洩漏、跨 symbol/TF 隔離、NaN/inf gate、multi-TF 對齊）在真實 kline 上可證偽檢查全 PASS。

HANDOFF_NOT_UPDATED: read-only 簽核任務，根 HANDOFF 由 Claude 維護
