# Handoff
**Agent**: Claude | **Time**: 2026-06-27 | **Branch**: main

## ✅ 已完成(2026-06-26~27,皆 commit+push)
1. **IC Phase 1 1a 第一刀(單幣縱向切分接線)** `d3b2dff`:防洩漏紅線生效於 `analyze()`——holdout+purge≥horizon+train-only fit+OOS 報告;兩輪雙家族 adversarial(9 BLOCKING)+三方數據簽核(R1 抓 2 LEAK→修→R2)+G-NEW 真run 抓 2 整合 bug→修;default ON,OOS 不可行分因回退。
2. **測試設計章程** `edfbfc6`/`152443d`:docs/TEST_DESIGN_CHARTER.md v2(三方+雙家族驗證)。§0 Oracle 分級(SMOKE 不計正確性)、§A 22 類、§B mutation 硬門檻、§E 模組對照、§F 統計檢定、§G SPEC 章程模板。**每 SPEC 須附測試章程**。
3. **reconcile 戳記機制** `4603d81`/`7f45c14`:reconcile/Claude 自身腿/SPEC/章程**須委員 RECONCILE-STAMP APPROVED**,gate fail-closed 拒發實作 token(無戳記)。`scripts/reconcile_stamps_check.sh`。**Claude 不享特權**(自身產物也審)。機制實證抓到 Claude 4 處錯。

## ★FF 正確性稽核結論(commit 7f45c14,兩家戳記 APPROVED)
**FF 地基「有疑(partial confidence),非不穩」**。IC 蓋在 FF 上,但 IC 不得宣稱建在已完整驗證的 FF。
- **強(已 P0)**:多TF對齊(V-6 as-of byte)、L6.5 因果(causal_winsor/V-5 截短 prefix byte)、L3 numba_rolling vs pandas differential。
- **高風險缺口(待補)**:P0-FF-1 L1 atomic 指標僅 smoke(騎 talib 但 wrapper/source/param 未驗,須抽樣 differential);P0-FF-2 全鏈 bar 級未來截斷 MR;P0-FF-3 MultiTF 高頻截斷 MR;P0-FF-4 requires_kline 缺檔 FAIL+DATA_MANIFEST。詳 handoffs/20260627-FF-AUDIT-RECONCILE.md。

## ★下一步(三選一,待使用者定優先序)
- **A. FF 深稽補 P0-FF-1/2/4**(地基,最致命;使用者已選地基優先) ← 建議
- **B. 補 IC 的 P0 測試缺口**(rolling IC vs scipy/MR-L2-L3/顛倒 probe/golden 缺檔 FAIL/stage5 統計;見 handoffs/20260627-CHARTER-VERIFY-*)
- **C. 1a 第二刀(cross_sectional 防洩漏)**
- 不論做哪個:依新章程附測試章程 + 走 reconcile 戳記機制。

## 維運
- 大 baseline gitignore(skip-if-absent,本地 freeze 再生)。記憶新增:測試章程/戳記機制/驗過就別預設關閉/完工附測試說明等。
