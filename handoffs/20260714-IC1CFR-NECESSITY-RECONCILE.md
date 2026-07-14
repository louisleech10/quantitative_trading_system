# 1c-FR 必要性委員會 RECONCILE — Claude 主編(2026-07-14)

輸入:handoffs/20260714-IC1CFR-NECESSITY-{claude,codex,composer,grok}.md

## 三家+Claude 裁決對照

| 委員 | 裁決 | 關鍵論點 |
|------|------|----------|
| Claude | PARKED+觸發器 | 風險自評:T1(ML cost-aware)是最不確定點 |
| composer | PARKED 至 1d/1f/實測後 | 觸發器=IC 淨閘/組合序列/錯位修復/實測算力證據 |
| grok | PARKED | cost-aware ML≠1c-FR 前置(物件混淆:監督標籤≠因子組合序列);**另記隱憂:deep FR 錯位有限值仍在輸出** |
| codex | **P1 高必要,不應無限 parked** | **事實核查推翻「無消費者」**:FactorReturnConfig.enabled=True 預設跑,ic_reporter:581-588 抽 LS mean/Sharpe,前端 page.tsx:800 展示=錯位數字活在 UI;立即 gate=先 fail-close 錯配輸出 |

## 收斂與分歧

**四方一致**:①成本盈利最終權威=回測;②單因子淨報酬會高估成本(無組合軋單),不可當淘汰依據;③cost-aware ML 不硬依賴 1c-FR(Claude T1 疑慮被 grok/codex 雙雙以「物件混淆」駁回——ML 淨效用須由 OOF predictions→positions→turnover 算,非單因子序列);④現有 ls_returns 錯位輸出是隱憂(grok 記隱憂/codex 升級為立即 gate/composer 觸發器含之)。

**唯一實質分歧**=排序:composer/grok 判 PARKED,codex 判 P1 近期——但根因是兩家對「消費者是否存在」認知不同,codex 的 repo 實證(預設 enabled+UI 展示)成立,故分歧可分解:

## Claude 裁決(拆兩票)

1. **IC1C-FR-STOPGAP(止血,小-中,立即)**:現有 factor_return 模組錯位產出(LS mean/Sharpe 等)在 reporter+前端=活的錯誤數字面——比照 B-strict 慣例 fail-close:預設停用或全欄標 `unavailable/unverified`+UI 註記,禁再以有限值示人。四方在此實質一致(codex 明令/grok 隱憂/composer 觸發器/Claude 同意)。
2. **IC1C-FR-FULL(完整重建,大)**:canonical timestamp-aligned series;止血後其緊迫性回落(錯誤數字已下架,新增資訊屬研究參考層)——排序=1d 之前或之後,**交使用者最終定**(codex 傾向近期,composer/grok 傾向 parked+觸發器;止血完成後兩派的實質差距只剩「中間研究視角要多早要回來」)。

重開觸發器(合併四方):①breakeven/profitable 要重新啟用;②因子組合優化需逐期序列;③實測證實回測算力浪費;④FR-as-target 學習需求。

## Provenance
三家產出已 register-output(sha256 見 .claude/gate/audit.log task:IC1CFR-NECESSITY);各檔末行 RULING: 為裁決原文。SIGNOFF:committee:IC1CFR-NECESSITY

## 戳記
(使用者最終裁決 2026-07-14:①止血票立即做;②完整 1c-FR=1d 之後近期排入〔採 codex 排序〕,非無限 parked。)
