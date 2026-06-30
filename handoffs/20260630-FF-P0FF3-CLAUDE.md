# P0-FF-3 多 TF 全鏈截斷 MR — Claude 設計腿(委員會用)

> 整套 P0-FF-3(使用者選項①完整版)。複用 B2 基建。委員從**讀碼推理**設計,勿跑慢全鏈;設計定案後實作+長 timeout 驗。

## 範圍(深稽藍圖 P0-FF-3)
**MultiTF 高頻截斷 MR + production multi-TF 全欄矩陣**:B2 的全鏈截斷不變量,但 config 開**多 TF**(primary + training,如 1h primary + [1h,4h,12h] training),驗截斷 primary(細)TF 未來 → 暖機後前綴**所有特徵(含粗 TF as-of 對齊欄)**不變。

## 已有護網(避免重複)
- **V-6 golden**(`test_mtf_align_golden.py`)已測**對齊因果**:`merge_asof` backward(用最後已收盤粗 bar)、`test_before_baseline_shows_lookahead`、real generate down/up 不變量、路徑矩陣。**對齊算法本身已 P0**。
- B2 已測單 TF 全鏈截斷 + 建立基建(批次讀/抽樣/收斂 gate/mutation 模式)。

## P0-FF-3 真正增量
截斷 MR **穿過多 TF 對齊層**:截斷細 TF 未來 bar 時,前綴中**依賴粗 TF 對齊的衍生欄**是否仍不變?(粗 TF as-of join 若洩漏未來粗 bar → 前綴變)。V-6 測對齊值,P0-FF-3 測「對齊在全鏈 + 截斷不變量下」。

## Claude 提案(複用 B2)
1. **複用 B2 測試基建**:`test_ff_fullchain_truncation_mr.py` 的截斷 pair 建構、批次讀、分層抽樣、收斂 gate（columns交集/both-non-NaN值/NaN分層/覆蓋守衛）、mutation 模式。新檔 `test_ff_multitf_truncation_mr.py` 或擴 B2。
2. **多 TF config**:`timeframes.training = [primary, 中, 粗]`(委員定實際組合,如 1h+[1h,4h,12h] 或 12h primary)。production 全特徵。
3. **截斷**:截 primary TF 尾 k bars → 全欄(含對齊衍生)前綴不變(B2 同收斂設計)。
4. **多 TF mutation 探針(新,關鍵)**:注入對齊 look-ahead——monkeypatch `TimeframeAligner.build_asof_index_map` 改成 forward/未來粗 bar(V-6 的 before baseline 即此類)→ 截斷 MR 必紅。+ 沿用 B2 的 center/shift/winsor。
5. **window**:多 TF 暖機更大(粗 TF W233 需 233 粗 bar = 對細 TF 更多列)。委員定窗(估 primary warmup + 粗 TF warmup 換算 + 餘量),用足夠長窗。
6. **mutation 層覆蓋守衛**:加「對齊層」必在 sampled set(粗 TF 對齊衍生欄)。

## 待委員(Codex/Composer)
- 多 TF config 實際組合(讀碼定 primary/training + production preset 多 TF 怎麼設)。
- 對齊 look-ahead mutation 注入點(`build_asof_index_map` forward?或 V-6 既有 before 機制)+ 確認截斷 MR 抓得到(對齊洩漏在前綴哪現形:值 or NaN?)。
- window 估算(多 TF 暖機)。
- 是否新檔 vs 擴 B2(共用 helper)。
- 結論:P0-FF-3 設計定案。
