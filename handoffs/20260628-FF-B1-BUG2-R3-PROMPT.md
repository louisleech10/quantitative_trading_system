# 派工:BUG-2 round-3(Composer)— Klinger 真 canonical + 獨立 oracle + entropy guard

兩家(Claude+Codex)收斂簽核 HOLD,理由+修法明確。讀 `handoffs/20260628-FF-B1-BUG2-SIGNOFF-codex.md`。

## 1. Klinger VF 修為權威 canonical(Stock.Indicators / Stephen Klinger)
- 現 impl(`momentum/FeatureEngineering/atomic/volume_indicators.py::_compute_klinger`):`vf = volume*(2*(dm/cm)-1)*trend*100` — **錯**(缺 abs + 形狀)。
- **改為**:`vf = volume * abs(2*((dm/cm) - 1)) * trend * 100`(= Stock.Indicators `Volume * Math.Abs(2*((dm/cm)-1)) * trend*100`)。trend=(H+L+C) 比較、dm=H-L、cm 重置邏輯維持(那兩段已對)。KVO=EMA34(vf)-EMA55(vf) 用 talib.EMA。
- 影響:73% bar 受影響、vs 舊值反相關(corr-0.82)→ Affected Column Closure + §G v1 差異表更新(舊「canonical」其實錯,差異表須註明 round2→round3 修正)。

## 2. 獨立 oracle(禁再拷貝 impl)— 章程 §B1.2
- **刪除** `tests/references/volume_indicators_ref.py::klinger_canonical`(它是 impl 拷貝=自指)。
- 改用**手推 worked-example golden**:造 ~6-8 根合成 bar,**手算**(寫出推導註解)每根的 dm/trend/cm/vf 期望值,硬編為 literal 在測試中;assert impl 的 vf == 手算值(VF 是逐根、不需 EMA,可手推)。EMA34/55 部分另用 talib 驗。
- 這樣 oracle 來自獨立手算非 impl 拷貝;Codex 下輪會逐根核你的手算值對不對。

## 3. correctness-mode 真補全(Codex 指 entropy 沒接)
- `momentum/FeatureEngineering/atomic/entropy_indicators.py`:**實際用 `guard_indicator_compute` 包 compute**(現只存 `_fail_open` 沒用)。`tail_risk_indicators.py` 同樣確認真接。
- `test_correctness_mode.py`:加 entropy + tail_risk 的 fault-injection 探針(off→不raise基線、on→raise變異)。

## 4. mutation 探針(章程 §B1.1,過 mutation_probe_check)
- Klinger:把 abs 拿掉(還原 bug)→ VF worked-example 測試必紅。
- 收尾前**自跑 `bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/` 須 PASS**(含新探針);附輸出。

收尾:更新 `handoffs/20260627-FF-DEEPAUDIT-B1-RESULT.md`。跑 tests/golden 後 git checkout 還原。完成 STATUS: DONE/BLOCKED。
