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

## ★進行中:FF 深稽 P0-FF-1/2/4 + BUG-1/2(大,完整管線,實作階段)
- **設計全程戳記齊**:Claude 腿→R1 雙家族 adversarial(揪 2 真 bug)→reconcile→R2/R2b 戳記(`...-RECONCILE.md` sha256:fa597372);SPEC+TODO(`docs/FF_DEEPAUDIT_P0_SPEC.md`/`_TODO.md`)→SPEC 層雙家族 adversarial→`...-SPECADV-RECONCILE.md`(sha256:6b75220)雙戳記。皆 reconcile_stamps_check PASS。
- **2 真 bug**:BUG-1 BETA/CORREL 餵 (close,volume) 非 canonical (high,low);BUG-2 手刻 Klinger 非標準(corr 0.59)。**BUG-1 修法=使用者定『兩者都要』**(標準 high/low + 改名 Beta_CloseVolume 價量版+標非標準);改特徵集→須三方數據簽核。
- **環境已修**:brew hdf5 升 320 斷 pytables → numpy 還原 1.26.4(pin)+ tables 重編連 hdf5 320 + packaging 25.0。kline 實測:`data_cache/feature_klines/kline_cache.h5`=10 symbols×3TF;storage manager 讀(非 pd.HDFStore);index=RangeIndex、timestamp 是欄位。
- **B0 完成 commit+push `2d13f2d`**:requires_kline marker(缺資料 FAIL 非 skip)+ DATA_MANIFEST(30 entries,3 mutation 可證偽)。Codex review 抓 2 P0 已修+Claude 雙驗。
- **B1 實作派工中**(Composer 2.5,bg b2pyohqda,45分):Task 1.0 correctness mode+1.1 prepare_inputs 等價+1.2 atomic differential+1.3 修 BUG-1(先產 Consumer Sync Checklist+新舊差異表)+1.4 修 BUG-2。`...-B1-DISPATCH/RESULT.md`。
- **B1 第一輪回+驗收**:Composer 實作 176 pass;Claude 驗 BUG-1 真實路徑正確(hl BETA==talib(high,low));Codex code review 抓 C1-2 假綠(oracle 自指)+BUG-2 HOLD(Klinger corr 0.18)。
- **C1-2 假綠已修並驗**:TALIB_INPUT_SEMANTICS 改獨立硬編表;Claude 親跑真 mutation(改map+clear registry+reinit)確認 ATR 真 FAIL。
- **章程+閘強化 commit `0d377e6`**:§B1.1-1.3(可執行自證探針/oracle獨立/注入重置快取)+ `scripts/mutation_probe_check.sh`;驗收紀律=親跑探針看真紅,禁只看全綠grep。dogfood 即抓 test_correctness_mode/test_bug1 缺探針。
- **BUG-2 使用者定:換 canonical**(正確性優先,不留簡化版);EOM corr 0.9999 可不動。
- **B1 完成批派工中**(Composer,bg bonaeq3fh):BUG-2 換 canonical Klinger/ForceIndex+獨立 oracle、correctness-mode 補全8engine、補缺探針;須過 mutation_probe_check。
- **B1 進度**:BUG-1 兩家 PASS(hl BETA==talib);C1-2 假綠已修驗;ForceIndex canonical 兩家 PASS;correctness-mode 接線(entropy 漏接修中)。
- **mutation 機制硬化 commit d6de3ba**:兩家 review 攻破原閘(空探針/偽raises/N-A濫用/async/路徑)→ 補 AST 靜態檢查器+腳本,委員反例重跑全擋,不誤擋。B0 重審 PASS。
- **BUG-2 三輪**:round1 simplified(corr0.18)→round2「canonical」但**缺abs+自指oracle**(兩家獨立查 Stock.Indicators,impl vs真canonical corr-0.82,反相關)→**round3 派工中**(bg badnof09c):Klinger 修 `vf=volume*abs(2*((dm/cm)-1))*trend*100`、entropy 真接 guard、**手推 worked-example 獨立 oracle**(禁拷貝)。
- **B2 序列待派**(B1 回收後;不並行避免同工作樹污染)。**下一步**:B1 回→postflight+diff 防假綠+Codex review+**BUG-1/2 三方數據簽核**(用差異表)→B2(全鏈截斷 MR)→B3 分級。
- **golden 副作用鐵律**:跑 test_l65_golden/tier2 會寫 tests/golden/l65/ artifacts,驗收後須 `git checkout --` 還原勿入 commit。pre-existing v8 失敗=test_ic_engine(非本批)。
- **執行者新規(使用者 2026-06-27)**:中大一律 Composer 實作+Codex review(覆蓋原『大=Codex實作』),記憶 feedback_executor_override_composer_impl。

## 維運
- 大 baseline gitignore(skip-if-absent,本地 freeze 再生)。記憶索引見 MEMORY.md(測試章程/戳記/§B8 閉合再驗證/驗過別預設關閉/完工附測試說明…)。
- 其他待辦:IC P0 測試缺口(rolling IC vs scipy 等,handoffs/20260627-CHARTER-VERIFY-*)、1a 第二刀(cross_sectional 防洩漏)、FF/IC 既有 follow-up(§N)。
