# IC Phase 0 TODO — Adversarial Review 派工 prompt（雙家族各一次，聚焦 TODO）

你是嚴格、獨立的 adversarial 審查者。**先完整讀**：
- TODO（審查主體）：`docs/IC_PHASE0_TODO.md`
- SPEC（已過雙家族 reconcile）：`docs/IC_PHASE0_SPEC.md`
- reconcile 結論：`handoffs/20260625-ic-PHASE0-ADVERSARIAL-RECONCILE.md`
- manifest：`handoffs/20260625-ic-PHASE0-MANIFEST.md`
- 審查準則：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（§0 挑戰前提、§1 十類、§2 空殼、§3 不可違反）
- 真實程式（驗證 TODO 引用的檔案/函式/行號是否存在）：`momentum/Analysis/ic_engine.py`、`ic_filter_orchestrator.py`、`ic_config_schema.py`、`api/services/ic_analysis_service.py`、`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`

## 聚焦（SPEC 已雙家審過，本輪查 TODO 特有風險）
1. **忠實落實**：TODO 是否忠實實現 reconcile 後的 SPEC？特別查 12 項 reconcile 決策（R-1~R-12）有無在 TODO 中走樣或遺漏（如 by_volatility 預設改 False、feature_filter 預設不截斷、_get_time_index 回 DatetimeIndex、decay 結構化 float 非 byte）。
2. **執行端可寫碼性**（§1.10）：每 Task 是否「冷啟動 agent 拿了就能寫」？實作要點 ≥3 含偽碼、修改檔案到函式名、邊界 ≥2、驗證有可證偽通過條件？哪些 Task 仍會讓 agent 猜？
3. **引用真實性**：TODO 寫的檔案/函式/行號（如 icAnalysisStore.ts:187、service:154-159/209-216、ic_engine:944）是否真的存在且語義相符？（實際開檔比對）
4. **掉項/churn**：manifest 30 ID 是否都有實質 Task（非只掛 ID 空殼）？批次依賴拓撲 B1-B4 是否正確（有無隱藏 forward dependency）？
5. **防假綠落實**：TDD 兩 commit、Golden 結構化比對、不放寬既有斷言——TODO 是否寫成可執行而非口號？

## 輸出格式（嚴格照 V13）
```
## Verdict：{{可派工 / 需修補後派工 / 有根本缺陷需重作}}
## Findings（每條：[BLOCKING|MAJOR|MINOR] + 信心度 + 證據(Task/原文短句) + 會怎麼失敗 + 修法）
## 被當成事實的未驗證假設（逐一；無則「無」）
STATUS: DONE
```
不重新生成 TODO，只輸出 findings。不得提違反 §3 的修補。
