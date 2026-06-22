# 20260622 MTF direction consultation (Composer)

Scope: read-only quant strategy; no product code changed.

## 立場（獨立評估）
① **Claude 大方向對**：決策週期對齊下，**粗→細**（1h 執行 + 4h/1d regime/filter）是 discretionary/systematic 主流。**細→粗**（12h/1d primary + 1h source）在實務存在但屬**次級架構**：日頻/週頻組合、HAR/MIDAS 波動、日內微結構壓縮進粗 bar——不是 crypto momentum 的預設主線。

② **業界 alpha 建構預設是聚合，非 native 全量滾動**：粗決策 bar 上放 realized vol/range、signed volume、taker imbalance、VWAP deviation、jump count、intra-bar path 摘要。本系統 native-tf 語境是 **L6.5 預處理正確性**（winsor/rank/fracdiff 勿在 step 序列上算），≠ 業界標準 alpha pipeline；兩者勿混。

③ **20352 列 slow path 合理作 backstop，不合理作預設**：profiling 顯示 12h pri+1h 次因 `native_rows×scaled_winsor(252→3024)` 達 ~7.6×/群、99 群 ~386s；主因算法量非缺核。應**分流**：需 path/order 的特徵走細粒度結構；其餘在粗 TF 原生算或聚合 descriptor，勿對全指標套 native winsor。

④ **真需「細原生結構」的 alpha（聚合會失真）**：HAR/實現核波動與跳躍、VPIN/持續 imbalance、bar 內 max DD/時間加權動量、first-half vs second-half、barrier 觸發、流動性乾涸持續度。一般 SMA/RSI/MACD 在 12h 上算再 winsor **不需** 1h native 滾動。

⑤ **Crypto 24/7**：無傳統 session，但有 **funding 8h、地域流動性時段、清算級聯**——更支持「週期性時間分桶聚合」而非 NYSE open/close；path-dependent 特徵仍要細粒度，但應**顯式分桶**（funding window、UTC 時段）而非盲目全史 1h rolling。

## B7
**暫緩原 scope 並行 native-tf slow path**（microbench ~1.0× 至 nogil 證明前）。優先：**小聚合特徵族 vs native-tf IC/ML A/B**（同 split）；native-tf 保留正確性與少數 kernel。若續做 B7：先 `nogil` + byte parity，再窄群 TP；ROI 低於聚合/分流設計。

ASSUMPTIONS_VERIFIED: HANDOFF、B7/L6.5 profiling handoffs、`_native_tf_helpers` window scaling、microbench。
TESTS_RUN: none。
SCOPE_CHANGES: none（僅本 handoff）。
NUMERIC_OR_SCHEMA_IMPACT: none。
STATUS: DONE
