# 章程驗證 + 過往工作測試差距稽核（雙家族各獨立）

兩件事一起做:

## 任務 1:驗證最終章程(抓 Claude reconcile 的錯/漏/誤併)
讀 `docs/TEST_DESIGN_CHARTER.md`(Claude 把兩家版本 reconcile 的最終稿) vs 你自己原版(`handoffs/20260627-TEST-DESIGN-CHARTER-{CODEX 或 COMPOSER}.md`)。
- **你原版有、最終稿漏掉**的重要項?(逐一列)
- 最終稿**寫錯/誤併/語義走樣**處?
- 仍有的**遺漏類別/門檻不專業**?(對照另一家若你看得到)
- 章程**自相矛盾或不可執行**處?

## 任務 2:過往工作測試差距稽核(用章程當尺)
對下列已完成工作,**按 §0 Oracle 等級分類現有測試**,標出高風險缺口(聲稱正確性卻無 mutation 驗 / 廉價 SMOKE 混充正確性 / 該有統計或差分卻缺):
- **1a 第一刀**:`tests/momentum/Analysis/test_ic_1a_cut1_*.py`(讀實際測試)。哪些是 P0 可證偽、哪些只是 SMOKE?ic_engine rolling IC 有無對 scipy 差分?
- **1-contract**:`tests/golden/ic_phase1_contract/`、契約層測試。
- **Phase 0(P0 止血)**:GroupedConfig/feature_filter/timestamp/by_volatility fail-closed 相關測試(grep 找)。
**輸出優先序清單**:哪幾個缺口是「正確性高風險、必補」vs「可延後」。不要全部重測,只標真正該補的。

## 輸出格式
```
## 任務1:章程驗證
### 漏項(原版有最終稿無):...
### 錯誤/誤併:...
### 仍遺漏/門檻問題:...
## 任務2:差距稽核(優先序)
### 必補(正確性高風險,附模組+為何+建議測試類別):...
### 可延後:...
STATUS: DONE
```
