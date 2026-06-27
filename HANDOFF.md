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

## ★下一個任務:FF 深稽(使用者選地基優先) — 先 P0-FF-1/2/4
- **級別=大**(碰 (a)數值正確 (d)防洩漏正確性、跨模組地基)→走完整管線。
- **測法不爆炸**(幾十指標×多層):①整批不變量一個測試蓋全部(P0-FF-2 砍未來→過去不變);②測有限「算子」非無限「特徵";③基礎指標抽樣+property-based。
- **必照新制度**:SPEC 附測試章程(§G)+ Oracle 分級;雙家族 adversarial 專審測試套件本身;mutation 硬門檻(改壞必 FAIL);reconcile 走戳記;**§B8 每 Block/Bug 修後由原提出方重跑同反例確認真關閉**;三方數據簽核用真實 kline。
- Claude 先自產獨立腿(讀碼,非只編排)→雙家族→reconcile→戳記。深稽可能揪出 FF 真 bug(非只缺測)→修。

## 維運
- 大 baseline gitignore(skip-if-absent,本地 freeze 再生)。記憶索引見 MEMORY.md(測試章程/戳記/§B8 閉合再驗證/驗過別預設關閉/完工附測試說明…)。
- 其他待辦:IC P0 測試缺口(rolling IC vs scipy 等,handoffs/20260627-CHARTER-VERIFY-*)、1a 第二刀(cross_sectional 防洩漏)、FF/IC 既有 follow-up(§N)。
