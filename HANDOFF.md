# Handoff
**Agent**: Claude | **Time**: 2026-06-27 | **Branch**: main

## ✅ 已完成(2026-06-26~27,皆 commit+push)
1. **IC Phase 1 1a 第一刀(單幣縱向切分接線)** `d3b2dff`:防洩漏紅線生效於 `analyze()`(holdout+purge≥horizon+train-only fit+OOS+分因回退);兩輪雙家族 adversarial+三方數據簽核(R1 抓 2 LEAK→修→R2)+G-NEW 真run 抓 2 整合 bug→修;default ON。
2. **測試設計章程** docs/TEST_DESIGN_CHARTER.md(v2,三方+雙家族驗證):§0 Oracle 分級(SMOKE 不計正確性)、§A 22 類、§B mutation 硬門檻、**§B8 Finding 閉合再驗證**、§E 模組對照、§F 統計檢定、§G SPEC 章程模板。**每 SPEC 須附測試章程**。
3. **治理機制(機器強制 fail-closed)**:reconcile/Claude 自身腿/SPEC/章程 須委員 `RECONCILE-STAMP APPROVED`(含 sha256 內容綁定+task)才可派實作(`scripts/reconcile_stamps_check.sh` + gate hook);**Claude 不享特權**。

## ★FF 正確性 scoping 稽核結論(兩家戳記 APPROVED;handoffs/20260627-FF-AUDIT-RECONCILE.md)
**FF 地基「有疑(partial confidence),非不穩」**。IC 不得宣稱建在已完整驗證的 FF 上。
- 強(已 P0):多TF對齊(V-6)、L6.5因果(causal_winsor/V-5)、L3 numba_rolling differential。
- **深稽藍圖(起手,非封閉全集)**:P0-FF-1 atomic 指標逐筆對 reference 差分(僅 smoke;騎 talib 但 wrapper/source/param 未驗);P0-FF-2 全鏈「砍未來→過去不變」因果 MR;P0-FF-3 MultiTF 高頻截斷 MR+production 全欄;P0-FF-4 requires_kline 缺檔 FAIL+DATA_MANIFEST;P1-FF-5 跨幣真run值隔離;P1-FF-6 d-star/fracdiff mutation probe;P1-FF-7 wrapper/polars-numba多路徑/float16。

## ★進行中:FF 深稽 — B0/B1 完成,B2 三方簽核 PASS 收尾中
- **B0 `2d13f2d`**(marker+DATA_MANIFEST)、**B1 `2247c39`**(修 BUG-1/2 真bug+atomic差分套件+三方簽核)、**mutation機制 `d6de3ba`/`0d377e6`**(防假綠閘,兩家審+硬化)。
- **★FF 因果性三方數據簽核 PASS(2026-06-29)**:Claude+Codex+Composer **各獨立讀碼**確認**無任一層偷看未來**(L2 shift正向/L3 numba單向無center/L4 lag≥1/L6.5強制causal/fracdiff只用校準前綴;shift(-n)只在IC標籤非持久特徵)。**FF 可用於量化研究**。reconcile=`handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md`。2 caveat(float16可重現性、特徵集列數依賴→stateful-param-audit epic)。
- **B2 真相**:全鏈截斷MR『失敗』非look-ahead,是測試逐byte太嚴撞良性邊界(float16翻面+列數依賴NaN/dead)。值在容差內穩定=無偷看未來。
- **B2 收斂設計實作中**(Composer b1748tr6v):columns gate交集+不對稱掉欄門檻max(100,0.1%union)、values both-non-NaN rtol2e-3、NaN mask分層(高fill≥95%欄exact防mask-only洩漏/near-empty informational)、覆蓋率守衛、5 mutation必紅、fracdiff專屬嚴格MR。
- **B2 比對效能三方定案+實作中**(Composer baux0audn):瓶頸=逐欄read_parquet(22萬次);修=批次讀parquet(每檔一次)+分層抽樣比對(每layer/operator抽K欄,mutation注入層必含,fracdiff專屬不抽樣)+覆蓋守衛。generate全鏈不變,比對<2min。
- **下一步**:B2實作回→Claude長timeout驗收(test_c2_1 PASS+mutation真紅)→Codex review→commit B2→B3
- **教訓**:慢測試(generate_features全開~14分/次,warmup2051需窗>暖機)驗證別巢狀&孤兒/別給太短timeout/優先讀碼判完成度;資料正確性交三方簽核非solo。preset盤點另epic。

## 維運
- 大 baseline gitignore(skip-if-absent,本地 freeze 再生)。記憶索引見 MEMORY.md(測試章程/戳記/§B8 閉合再驗證/驗過別預設關閉/完工附測試說明…)。
- 其他待辦:IC P0 測試缺口(rolling IC vs scipy 等,handoffs/20260627-CHARTER-VERIFY-*)、1a 第二刀(cross_sectional 防洩漏)、FF/IC 既有 follow-up(§N)。
