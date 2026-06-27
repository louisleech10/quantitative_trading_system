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

## ★進行中:FF 深稽 P0-FF-1/2/4(大任務,完整管線)
- **Claude 獨立腿已產**:`handoffs/20260627-FF-DEEPAUDIT-CLAUDE-LEG.md`。§A 實 grep 驗證:TA-Lib 系 atomic 測試=純 smoke(只驗欄名);手刻模組(entropy/tail/micro)有 property 不變量但無 reference 差分;衍生(VWAP/Klinger/ForceIndex/EOM)幾無專測;**`requires_kline` 機制不存在**(P0-FF-4 待新建,現缺資料一律 pytest.skip=靜默綠)。§B 讀碼揪 4 可疑點(待真run驗):B1 input_type 預設 single 陷阱、B2 BETA/CORREL 餵 close_volume、B3 手刻 Klinger 非 canonical、B4 metadata 對位。§C 測試設計(P0-FF-1 differential / P0-FF-2 全鏈 bar 級截斷 MR 一不變量蓋全 / P0-FF-4 requires_kline FAIL+DATA_MANIFEST)+ mutation 硬門檻。
- **R1 雙家族 adversarial 完成**(`...-ADV-codex.md`/`...-ADV-composer.md`,皆真run):兩家收斂揪出 **2 真 BUG**——BUG-1 BETA/CORREL 餵 (close,volume) 但 talib canonical 是 (high,low)(錯特徵/誤導命名);BUG-2 手刻 Klinger 非 canonical(corr 0.59)、ForceIndex/EOM 未標變體。另兩家共同 BLOCK:C1-2「⊆input_names」不可實作、C2-1 warmup 掩蓋假綠、C1-3 自指 oracle、mutation 須 TDD-first。我誤判更正:B1 降 RISK(fail-open 非錯值)、A5 過度宣稱(V-5 已有 end-date 截短 MR)、B4 撤回。
- **Reconcile 已採納全部**:`handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md`(修正設計=SPEC 種子)。
- **R2/R2b 戳記齊全(過機檢)**:`reconcile_stamps_check.sh` PASS,codex+composer 皆 `APPROVED ... sha256:fa597372... task:ff-deepaudit-r2b`(R2b 為補 v2 雜湊綁定格式;R2 真核可 task=b147mxx9h/b7lzyi2vl)。reconcile gate-ready 可派實作。
- **下一步**:寫正式 SPEC(P0-FF-1/2/4 + BUG-1/BUG-2 修;附測試章程§G+Oracle 分級;mutation TDD-first)+TODO → 過 gate(--spec 指向已戳記 reconcile)派實作(Codex)+另一方 code review。
- **BUG-1 決策(使用者定)= 兩者都要**:補真正標準 BETA/CORREL(high,low)+ 保留改名(BetaCloseVolume 等)的價量相關版+metadata 標非標準。改特徵集→須三方數據簽核。已存記憶 project_ff_deepaudit_bugs。

## 維運
- 大 baseline gitignore(skip-if-absent,本地 freeze 再生)。記憶索引見 MEMORY.md(測試章程/戳記/§B8 閉合再驗證/驗過別預設關閉/完工附測試說明…)。
- 其他待辦:IC P0 測試缺口(rolling IC vs scipy 等,handoffs/20260627-CHARTER-VERIFY-*)、1a 第二刀(cross_sectional 防洩漏)、FF/IC 既有 follow-up(§N)。
