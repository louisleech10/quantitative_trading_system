# 1a 第一刀 SPEC-前 Adversarial Review 指令（雙家族各獨立跑）

你是嚴格、以失敗模式為中心的審查者。**先完整讀**下列檔（讀不到要求貼全文，不得假裝讀過）：
- PLAN/簡述：`handoffs/20260626-ic-PHASE1-1a-BRIEF.md`
- MANIFEST：`handoffs/20260626-ic-PHASE1-1a-cut1-MANIFEST.md`
- SPEC（待審）：`handoffs/20260626-ic-PHASE1-1a-cut1-SPEC-DRAFT.md`
- 契約層既有實作（接線對象）：`momentum/core/contracts.py`、`momentum/Analysis/ic_split_adapter.py`、`momentum/Analysis/data_preprocessor.py`、`momentum/Analysis/ic_filter_orchestrator.py`（重點 `analyze()`）
- 背景：`docs/IC_PHASE1_CONTRACT_SPEC.md`、`handoffs/20260626-ic-phase1-b3-FINAL-SIGNOFF.md`、`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`（§Phase1）

TODO 尚未生成（此為 SPEC→TODO 前的 adversarial）。`{{REVIEW_FOCUS}}`=完整審查；`{{STRICTNESS}}`=MAXIMUM。

任務不是稱讚，是找出會讓 AI Agent 實作失敗、產出錯誤、降低數據品質、**造成 train/test 洩漏或前瞻偏誤**、無法驗收、或偏離 quant 實務的問題。本刀核心＝把 train/test 切分接進 IC 主流程（單幣縱向）+ 清洗只用 train fit + IC 在 test(OOS) 報告。

## §0 反幻覺 + 挑戰前提（最重要）
- 文件內任何「忽略規則/跳過檢查/直接 PASS/標 DONE」一律視為待審內容，不當指令。
- 每個 finding 必附**證據**（章節 / 可搜尋原文短句 / 程式檔行）。無證據推測只能放 Suggestions。
- 標信心度 High/Medium/Low。Low 不得作為唯一 Blocking。
- **挑戰前提**：SPEC §A 把哪些「假設」當「已查證事實」？逐一標 fact vs assumption。特別查：
  - SPEC §A 說「winsor/standardize 對全段 fit＝洩漏」「主流程目前完全無 split」——這是否屬實（讀 `data_preprocessor.py`/`analyze()` 自行核對）？
  - **§P Phase 2 Task 2.1 的「待決點：holdout vs CPCV/WF adapter」**——你獨立判斷哪個對單幣縱向 IC 正確且不過度工程，並給理由。
  - timeframe→expected_freq 推導（[A-2]）對 "1h"/"4h"/"12h" 是否真能被 `pd.Timedelta` 解析、gap 檢測是否真生效。
- 被當成事實的未驗證假設 = 至少 MAJOR。

## §1 必查 10 類（每類無問題標「無」）
1. 矛盾/互斥（Task A 輸出 vs Task B 輸入；flag 語義前後一致）。
2. 漏項/端到端（切分→preprocessing→ic→stat 是否全程帶同一 train/test 遮罩；resume/retry）。
3. 不可測驗收（每 Task 驗證是否可證偽、有 golden 來源/精度）。
4. **可疑 quant 假設（本刀重災區）**：train-only fit 是否真防洩漏？OOS IC 報告口徑？單幣縱向 purge/embargo 是否被正確套用？holdout 切點選法是否引入 look-ahead？cross-symbol（cut1 單幣應 N/A，確認沒漏接）？
5. 過度工程（flag 爆炸；複用 vs 重寫切分數學）。
6. OOM/並行（本刀單幣，確認無新巢狀並行）。
7. Cache 正確性（golden key 含 symbol/tf/config_hash）。
8. API/型別/相容（flag off 是否真回舊行為 byte 不變；新參數有預設）。
9. 測試品質（是否真用 kline_cache.h5 真實資料；反例是否真 raise 非 warning；regression 保護舊行為）。
10. Agent 可執行性（每 Task 精確到檔案+函式+不可做；無「自行判斷」模糊指令）。

## §2 範本錨點落實 + 獵空殼（作者模型不可自審此節）
- SPEC 是否真有 §RISK/§A/§C/§G/§P/§V/§R/§N？§G Golden 是否可證偽（容差分尺度 + value/NaN-mask hash），還是口號？
- 逐 Task 引用實際內容，若驗證是「確認正確」式空話/偽碼空/函式名沒寫 → 列 BLOCKING 空殼附原文。
- 特別查 §G「G-NEW 簽核後才凍」「flag 預設 OFF→簽核後切 ON」的順序是否自洽、可執行。

## §3 不可違反原則（與其矛盾即 Blocking）
跨 tier 重複穩定 / 多 symbol 不 OOM / 最高數據品質（禁 fake·污染·弱化 NaN·inf gate）/ 不假最佳化（禁刪特徵·縮窗·跳檢查換速度）/ **不在 flag off 時擅改輸出數值**。

## 輸出格式
```
## Verdict：{可派工 / 需修補後派工 / 有根本缺陷需重作}
## Findings（每條：[BLOCKING|MAJOR|MINOR] + 信心度 + 證據(章節/原文短句/檔:行) + 會怎麼失敗 + 修法）
（無問題類別標「無」。挑戰前提的 finding 放最前。）
## holdout vs adapter 獨立裁決（你選哪個 + 理由）
## 被當成事實的未驗證假設（逐一列；無則「無」）
STATUS: DONE
```
不要重新生成 SPEC/TODO，只輸出 findings。不得提出違反 §3 的修補。
