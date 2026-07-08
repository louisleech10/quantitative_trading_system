# 委員會諮詢:IC 1a 剩餘刀施工順序(task-id: IC1A-CUTS-ORDER)

你是委員會一員。**全面獨立**完成本任務——自己偵察、自己下結論,不分角度、不依賴他人版本。

## 任務

IC Gatekeeper Phase 1 剩餘刀清單(出處 `docs/ROADMAP.md` P0 節 + `handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`):

1. **1-align**:前瞻偏誤硬閘——Feature_t vs Target_t+1 timestamp 對齊檢測
2. **1b FDR 接線**:多重比較校正接進特徵選擇主流程
3. **1c Net IC 量綱修正**:Grinold 式,非「相關係數減報酬率」
4. **1d factor_attribution**:接真實作或 UI 正名 proxy + NaN 政策
5. **1e HAC/block bootstrap**:rolling IC 自相關 + 重疊報酬的顯著性修正
6. **1f 靜默空圖**:report schema flatten 前後端接線
7. **grouped_ic 止血**(HANDOFF 列的,現況待你驗證)

**產出兩件事**:

### A. 現況偵察(必附 receipt:檔案:行號 + 你實際 grep/讀到什麼)
逐項驗證:這刀在**現行 HEAD** 是否仍需要?已被 cut1(單幣縱向)/cut2(cross_sectional)/Phase 0(commit 11507f5)順手修掉的要指出。勿盡信 ROADMAP/HANDOFF 舊結論。
重點檔:`momentum/Analysis/ic_filter_orchestrator.py`、`statistical_validator.py`、`net_ic_analyzer.py`、`factor_exposure_analyzer.py`、`momentum/core/contracts.py`、`api/services/ic_analysis_service.py`、前端 `frontend/src/components/ic-analysis/`。

### B. 施工順序提案
- 每刀:順位、任務大小(小/中/大,判準見 CLAUDE.md 決策表:命中 a-d=大)、一句理由
- 哪些刀該**合併**或**拆分**?(例:有無 p-value 生產→消費依賴?)
- 哪些已完成該從清單移除?
- 排序核心邏輯用一段話講清楚(依賴關係/風險/返工成本)

## 約束
- 只讀+寫你自己的輸出檔,**不改任何生產 code/測試**,不 git checkout tracked 檔。
- 輸出寫到:`handoffs/IC1A-CUTS-ORDER-<你的名字 codex|composer>.md`
- 結論須可證偽:每個「已修/未修」判斷附 grep/讀檔證據。
- 背景:cut2 已完成 F1-F4(cross_sectional 標籤對齊+fail-closed+全域時間邊界 OOS);SCAR 治理:未來每刀 SPEC 須 consumer-map+真路徑 red-on-break 測試。
