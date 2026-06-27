# FF 正確性 scoping 稽核 — 三腿 reconcile

> 三獨立腿:Claude(自讀碼) + Codex + Composer。**注意:本 reconcile + Claude 自身腿須回送委員戳記後才可據以派實作(見下「待戳記」)。**

## 地基判斷(三腿收斂):**有疑(partial confidence),非不穩**
FF 對齊/L6.5 因果/整合視窗有真 kline P0 硬測(強);但**特徵公式本身**與**全鏈 bar 級未來截斷 MR**未達 P0。IC 把 FF 當完整可信 oracle = 目前只能 partial confidence。

## 三腿一致的關鍵(含對 Claude 草稿的修正)
- **Claude 草稿被 Composer 抓錯**:把 `test_cross_symbol_features` 當軸6隔離證據=誤導(那是 legacy extractor,非 FF/CGSA 生成隔離;真隔離在 failopen V-7 + cgsa isolation)。← 證明 Claude 自身腿需委員審。
- **Claude 獨立觀察(非委員認可,Codex 戳記更正)**:atomic L1 `import talib`(RSI/ATR/EMA/volume)。**但委員立場(Codex)**:atomic/operator correctness 覆蓋**不完整**、仍須 TA-Lib/scipy/pandas/manual differential,**且未認可 wrapper/source/param 正確性**。→ **L1 風險不因「騎 talib」而降**:即使底層公式是 talib,wrapper 傳錯 source/price 欄或參數一樣全錯,differential 仍 **P0 必補**。(Claude 原稿把此歸因講太輕,已更正)
- **Composer 更精確分級(採)**:L3 `test_numba_rolling` 是**真 P0 differential**(vs pandas);L6.5 `test_causal_winsor`/`test_ff_causal_golden`/failopen **V-5(截短 end→prefix byte 相等)/V-6(as-of oracle byte)** 是**真 P0 因果/對齊**。**最弱=L1 atomic 幾乎 smoke**(數百生產指標僅「能算出來」)。

## 高風險缺口優先序(三腿收斂)
1. **P0-FF-1 L1 atomic differential(最大 GIGO 單點)**:~13 atomic 模組對 TA-Lib/scipy 抽樣 differential(現僅 smoke;公式/source 欄錯則下游全錯)。
2. **P0-FF-2 全鏈 bar 級未來截斷 MR**:真 kline 跑 `generate_features()`,截斷/擾動尾端未來 bars→截斷點前 feature matrix+NaN mask+columns 不變;覆蓋 L1-L6.5+CGSA+multi-TF。(章程 §E1 點名;V-5 測「縮短 end」非 bar 級)
3. **P0-FF-3 MultiTF 高頻未來截斷 MR + production preset 全欄矩陣**(現多 minimal/fast config)。
4. **P0-FF-4 golden/真實資料 job 治理(Composer P0-3,Codex 戳記補回——原稿漏併)**:`requires_kline` 缺檔**不可 skip**(correctness job 缺 kline/golden = **FAIL** 非 silent skip)+ 建 `tests/fixtures/DATA_MANIFEST.json`、golden 漂移→明確 FAIL。
5. **P1-FF-5 跨 symbol 真 run 計算值隔離 MR**:A+B vs B+A vs only A→A 的 feature/metadata/d-star 語義不受 B 影響(現多 path/shard 隔離,非值隔離)。
6. **P1-FF-6 d-star/fracdiff mutation probe**:人工移除 symbol/TF/fingerprint 欄→隔離測試必紅(章程 B1)。
7. **P1-FF-7 TA-Lib wrapper source/price 欄與參數正確性**;Polars/Numba/Pandas 多路徑全覆蓋;float16 lossy 明示。

## 結論/建議
FF 可續用於 IC,但 IC 不得宣稱「建在已完整驗證的 FF 上」,只能 partial confidence。**建議深稽聚焦 P0-FF-1/2/3**(最致命、收斂明確),分批補;P1 隨後。**不全重測**(對齊/L6.5/視窗因果已 P0)。

## 戳記(委員 append 真戳記於下方;格式 `^RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD>`,須帶日期)
（CLAUDE-LEG 已交委員審——本次新增對稱機制）

RECONCILE-STAMP-RESOLVED(R1): codex was-REJECTED — ① 漏併 Composer P0-3(requires_kline 缺檔不可 skip/DATA_MANIFEST/缺檔 FAIL) ② atomic TA-Lib 過度歸因「被 Codex 認同」。**兩點已修**:① 補為 P0-FF-4;② 改為 Claude 獨立觀察+明示委員未認可+L1 風險不降 differential 仍 P0。待 R2 重審。

RECONCILE-STAMP: codex APPROVED 2026-06-27
RECONCILE-STAMP: composer APPROVED 2026-06-27
