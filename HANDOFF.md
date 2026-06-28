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
- **SPEC+TODO 已寫並過機檢**:`docs/FF_DEEPAUDIT_P0_SPEC.md`(§RISK/§A/§C/§G/§P/§V/§R/§N)+`docs/FF_DEEPAUDIT_P0_TODO.md`(§0/§B/9 Task 全覆蓋)。template_check PASS。
- **SPEC+TODO 雙家族 adversarial 完成**(`...-SPECADV-{codex,composer}.md`):兩家收斂抓 SPEC 真缺口——BUG-1 消費者清單空殼(grep 出 adf_safe_skip/golden/UI/IC 真實同步點)、§G 受影響範圍無定義、correctness mode 機制未定義、price_transform 掉項、§B4 矩陣缺、C2 metadata 自相矛盾、logging 違解耦。**已 reconcile 採納全 18 點**(`...-SPECADV-RECONCILE.md`)並**修正 SPEC+TODO**(新增 Task 1.0 correctness mode、Consumer Sync Checklist、Affected Column Closure、§B4 矩陣、C2 四段斷言、§G v0/v1...),仍過 template_check。
- **SPECADV-R2 完成,雙戳記過機檢**:codex 先 REJECTED(§B8 抓我漏改裸路徑)→ 修 → codex+composer 皆 `APPROVED sha256:6b75220 task:ff-specadv-r2(b)`,`reconcile_stamps_check` PASS。SPEC+TODO 歷兩輪雙家族 adversarial,dispatch-ready。
- **✅ 環境已修(2026-06-27)**:brew hdf5 升 320 → pytables 3.9.2 連舊 310 斷鏈。修法:numpy 還原 1.26.4(專案 pin;曾被誤升 2.0.2)+ tables 3.9.2 `--no-binary` 重編連 hdf5 320(`HDF5_DIR=/opt/homebrew/opt/hdf5`)+ packaging 還原 25.0。`tests/test_atomic_indicators.py` 5 passed。
- **kline 實測 facts(補 §A)**:`data_cache/feature_klines/kline_cache.h5` = 10 symbols(ADA/BCH/BNB/BTC/DOGE/ETH/LINK/SOL/TRX/XRP)+_metadata;storage manager(h5py)讀:BTCUSDT/12h=1696列、ETHUSDT/1h=20352列、10 欄(timestamp,open,high,low,close,volume,+taker/quote/trades);**index=RangeIndex、timestamp 是欄位非 index**(實作 §A 注意)。pd.HDFStore 不適用(非 pandas 格式)。
- **B0 實作派工中**(Composer 2.5,bg by6gk09xh;gate token 已驗戳記+preflight 快照):Task 0.1 requires_kline marker + 0.2 DATA_MANIFEST,prompt=`handoffs/...-B0-DISPATCH.md`,結果寫 `...-B0-RESULT.md`。
- **B0 完成+Claude 初驗通過**:postflight 乾淨;**無斷言放寬**(git diff grep assert=空);skip→`pytest.fail`+marker 遷移 16 檔;DATA_MANIFEST entries=30(10×3),3 mutation 真可證偽(sha256/缺項/row_count raises);requires_kline marker 註冊生效(87 collected)。`test_v8_frozen_doc` 失敗=pre-existing IC(`test_ic_engine.py`,非 B0)。`test_inventory.txt` 成長=弱 smoke 非假綠。
- **Codex B0 code review 回**(`...-B0-CODEREVIEW-codex.md`):抓 2 P0 — P0-1 manifest 測試漏 requires_kline marker(smoke 逃生口失效);P0-2 golden/parquet scope 外變動(經查=Claude 驗收跑 test_l65_golden 的副作用,已 git checkout 還原)。解耦 PASS、manifest 核心可證偽 PASS。
- **Composer B0-fix 派工中**(bg bja6edxdl):補 manifest marker + conftest KeyError 收斂。
- **下一步**:fix 回 → Claude 復驗(`-m "not requires_kline"` 排除正確)→ commit B0 → B1/B2 並行 → B3。pre-existing v8 失敗(test_ic_engine)另處理。golden 副作用提醒:跑 test_l65_golden 會寫 tests/golden/l65/ artifacts,驗收後須 git checkout 還原勿入 commit。
- **執行者新規(使用者 2026-06-27)**:中大型一律 Composer 實作 + Codex review(覆蓋原「大=Codex實作」),見記憶 feedback_executor_override_composer_impl。
- **BUG-1 決策(使用者定)= 兩者都要**:補真正標準 BETA/CORREL(high,low)+ 保留改名(BetaCloseVolume 等)的價量相關版+metadata 標非標準。改特徵集→須三方數據簽核。已存記憶 project_ff_deepaudit_bugs。

## 維運
- 大 baseline gitignore(skip-if-absent,本地 freeze 再生)。記憶索引見 MEMORY.md(測試章程/戳記/§B8 閉合再驗證/驗過別預設關閉/完工附測試說明…)。
- 其他待辦:IC P0 測試缺口(rolling IC vs scipy 等,handoffs/20260627-CHARTER-VERIFY-*)、1a 第二刀(cross_sectional 防洩漏)、FF/IC 既有 follow-up(§N)。
