# 委員會根因調查:B2 後 cut1 golden 漂移(task-id: ic1a-align-b2-golden-rca)

## 已知事實(Claude 實跑 receipt,2026-07-09)
1. B2(Task 2.1-2.4,working tree 未 commit)後,cut1 golden(`tests/momentum/Analysis/test_ic_1a_cut1_golden.py`,真 BTCUSDT 1h top50)與凍結 baseline 深比對 11,697 個 diff path。
2. **已排除「舊 positional 錯位」**:golden 的 kline 軸與 feature 軸完全相同(各 20352 列、首尾 ts 1704067200/1777330800 相等、offset=0)→ 舊對齊在此路徑本來正確,label 值不應變。
3. Diff 兩類:
   - **A 類(量大)**:grouped_ic/turnover_analysis 全面 ~1e-4 相對微擾(例 `0.007399221491284419→0.007399095218296034`)——像「有效樣本差 1 列」或「浮點 dtype/計算路徑改變」。
   - **B 類(行為)**:`filter_log/stage5_thresholds/removed_features`:`ic_mean` 50→43、`icir` 0→7(7 特徵翻類)——可能是 A 類微擾把值推過門檻,也可能獨立機制。
4. B2 改動面:`git diff momentum/Analysis/ic_filter_orchestrator.py`(helpers L95/L103+slice L564+stage0 L1740+stage2 L1821+event_filter L1886)。B1(已 commit fd5866f)在 golden 跑過時未觸發漂移(B1 驗收時 386 綠含 golden?→自行驗證此假設)。

## 任務(各自全面獨立查,附 bisect 級 receipt)
1. **定位機制**:哪一個 B2 改動造成 A 類微擾?建議逐一還原(stash/patch 局部)或在關鍵點 dump 中間值(label 值/有效列數/dtype/rolling 窗邊界)比對新舊。明確回答:是「樣本列數變了」「label 值變了」「dtype/精度路徑變了」還是「rolling/purge 邊界變了」?
2. **B 類歸因**:7 特徵翻類是 A 類微擾推過門檻,或獨立 bug?列出 7 特徵的新舊 ic_mean/icir 值與門檻。
3. **裁定建議**:機制屬(a)修正已知錯(如 WHOLEMAP §C「秒被當毫秒」grouped 軸錯、或其他既有錯誤行為)→ 重凍 baseline 合理;(b)引入新錯(非蓄意語義改變)→ 修 code。附證據,不猜。
4. **data_cache 寫入面**:golden 跑一次會寫 `data_cache/reports/ic_report_*` 與改 `data_cache/features/BTCUSDT_1h_filtered.h5`——確認這是 pre-existing 設計(B2 之前就會寫)還是 B2 新增,列出寫入點(檔:行)。

## 產出
`handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-<codex|composer>.md`:機制結論/receipt/裁定建議((a) or (b))/data_cache 寫入歸屬。結尾 `Verdict: REBASELINE|FIX-CODE|MIXED`。
只讀+跑診斷腳本(輸出重導 /tmp 或 scratchpad);不改生產 code/測試;不 commit;不動 working tree 的 B2 diff。
