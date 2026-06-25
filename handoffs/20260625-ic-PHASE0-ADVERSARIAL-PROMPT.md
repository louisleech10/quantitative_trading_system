# IC Phase 0 SPEC — Adversarial Review 派工 prompt（雙家族各一次）

你是嚴格、以失敗模式為中心的**獨立** adversarial 審查者。**先完整讀**下列檔（讀不到要明說，不得假裝讀過）：
- SPEC：`docs/IC_PHASE0_SPEC.md`
- Manifest：`handoffs/20260625-ic-PHASE0-MANIFEST.md`
- 白話 brief：`handoffs/20260625-ic-PHASE0-BRIEF.md`
- 根因底稿：`handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`
- 審查準則（必照其格式與 §0 挑戰前提）：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`
- 相關真實程式：`momentum/Analysis/ic_engine.py`、`ic_filter_orchestrator.py`、`ic_config_schema.py`、`api/services/ic_analysis_service.py`、`api/models/ic_models.py`、`momentum/DataExtraction/kline_storage.py`、`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`

## 任務
照 `SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13 完整審查（§0 反幻覺+挑戰前提、§1 十類失敗模式、§2 範本錨點落實+獵空殼、§3 不可違反原則）。重點：

1. **挑戰前提**：SPEC §A「已驗證事實」六項，哪些是真 fact-verified（附碼證/實跑）、哪些其實是 assumption？特別查 IC-TIMEAXIS 的「真實路徑必觸發 1970 bug」推論鏈是否成立（read_klines 真的回 RangeIndex+秒級 timestamp 欄嗎？grouped 路徑真會走 numeric 分支嗎？）。
2. **IC-BYVOL 修法收斂（必答）**：Task 2.3 二選一——(a) 實作波動度分組 vs (b) fail-closed 報錯。**你獨立判斷哪個對，給理由**。考量：Phase 0 定位是止血+硬閘不擴功能；波動度分組實作風險/正確性；契約一致性。
3. **feature_filter 確定性排序（F-3）**：SPEC 提「按 features_df 既有欄位順序取前 N」是否足夠？有無更正確且不引入 look-ahead 的排序？max_features 截斷會不會改 feature universe 語義（命中正確性紅線）？
4. **Golden 充分性（§G）**：grouped_ic「值守恆只是分組正確」這個 golden 設計能否真抓到 timestamp 修錯後的回歸？decay byte 級不變的 golden 是否漏掉浮點重排？
5. **回歸測試防假綠**：C-3/T-3 要求「未修時 fail、修後 pass」是否每個都可落實？fixture 秒級 byte-faithful 是否真能擋 ms 假綠？
6. **漏項/端到端**：六 epic 是否有跨 Phase 銜接矛盾、缺前端串接、缺 config migration、resume/retry？

## 輸出格式（嚴格照 V13）
```
## Verdict：{{可派工 / 需修補後派工 / 有根本缺陷需重作}}
## Findings（每條：[BLOCKING|MAJOR|MINOR] + 信心度High/Med/Low + 證據(章節/原文短句) + 會怎麼失敗 + 修法）
## IC-BYVOL 建議：(a 實作 / b fail-closed) + 理由
## 被當成事實的未驗證假設（逐一列；無則「無」）
STATUS: DONE
```
不要重新生成 SPEC，只輸出 findings。不得提出違反 §3 不可違反原則的修補。
