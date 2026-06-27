# FF 深稽 P0-FF-1/2/4 — 三腿 reconcile(Claude 腿 + Codex + Composer adversarial)

> 被審:`20260627-FF-DEEPAUDIT-CLAUDE-LEG.md`;審查腿:`...-ADV-codex.md`、`...-ADV-composer.md`(皆真 run)。
> 兩家結論均「須修後再審」。本 reconcile 逐條採納收斂 BLOCK,修正後設計即正式 SPEC 種子。**須委員 R2 戳記後才可據以派實作。**

## 一、深稽揪出的真 FF BUG(非只缺測 — 兩家真 run 坐實)

**BUG-1(BLOCK,採)BETA/CORREL source 語義錯配**
- 事實:`talib_wrapper.py:206` 把 BETA/CORREL 放 `_INPUT_TYPE_MAP["close_volume"]` → 餵 `(close, volume)`。TA-Lib `abstract.Function("BETA").input_names = {price0:high, price1:low}`。兩家真 run:`wrapper == talib.BETA(close,volume)` True;`== talib.BETA(high,low)` False(maxdiff 7.33 / CORREL 1.95)。
- 欄名 `*_statistics_BETA_*` 暗示 TA-Lib β,實為 close–volume 相關 = **錯特徵/誤導命名**。
- **修法(SPEC 決策點,須三方數據簽核)**:預設對齊 TA-Lib canonical → 改 `hl`(high,low)+ 改欄名/metadata/golden;**若**產品確要 close-volume 語義 → 改名 `Beta_CloseVolume` 等 + metadata 標非標準 + 獨立 oracle。在決策定案前,C1-1 對此族用**雙 oracle** 測試,預設 fail。

**BUG-2(BLOCK,採)手刻 Klinger 非 canonical;ForceIndex/EOM 未標變體**
- Klinger VF vs trend-aware canonical:corr=0.59、同號率 69.8% = **公式實質不同**。ForceIndex=`diff(close)*volume` raw(非 EMA13 平滑,maxdiff 997)。EOM 缺常見 1e8 scale。三者 metadata 皆未標「簡化變體」。
- **修法**:每個手刻指標建**獨立 reference**(不得 import 被測模組);定 oracle 分級(見 C1-3)。簡化變體 → 三方簽 off 後 golden-lock + metadata `variant=simplified`,欄名/描述明示;不得讓下游誤認標準 Klinger/EOM/FI。

## 二、Claude 腿須更正(兩家抓出)

- **B1 降為 RISK**:漏登錄指標非「靜默餵 close」,而是 `talib.FUNC(close)` 拋 TypeError → 被 `compute_all` 的 `except Exception` 吞成 warning → **fail-open 掉特徵**。現 132 指標全在 map,**無 live misroute**;風險在新增指標。修法:registry 完整性 CI gate + **correctness mode 對已登錄指標計算失敗須 FAIL 非 warning**。
- **A5 更正**:`test_failopen_correctness.py::test_v5_prefix_no_leakage_after_warmup` **已存在**(end-date 截短 + warmup 後 prefix byte 相等,但 **fast config / 單 TF / preprocessing off**)。正確表述 = 「**end-date 截短 MR 有(窄 config);bar 級尾端擾動 MR + production 全欄全鏈 缺**」。
- **B4 = OK**(非 bug,撤回)。`compute_batch` 對非 single 用 close 進 `_prepare_inputs` 後由 input_type 覆蓋 source_label,metadata 對齊。
- **覆蓋漏洞**:`test_atomic_indicators.py` 只覆 trend/momentum/volatility/volume/pattern 五類;**cycle/statistics/custom atomic 零專測**。P0-FF-1 抽樣須明含這三模組 + price_transform adapter policy。

## 三、測試設計修正(採兩家補強;mutation 須 TDD-first + §B8 閉合再驗證)

**P0-FF-1**
- C1-1(GOLDEN/EXACT)wrapper vs 直呼 talib differential。抽樣**必含**:RSI/ATR/EMA/MACD/STOCH/BOP/OBV/AD/ADOSC + **BETA/CORREL(雙 oracle 防 B2)** + cycle/statistics/custom 各≥1 + price_transform(AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE)adapter policy(computed_in_adapter=True 須有 adapter oracle 或證明不宣稱可算)。比對 input tuple/params/output names/NaN mask/index。
- **C1-2 改為「prepare_inputs equivalence」(取代不可證偽的「⊆ input_names」)**:建 `TALIB_INPUT_SEMANTICS` 表(indicator→input_type→實際 df 欄位 ordered);測 `_prepare_inputs` 產出的 ndarray 與依該表直呼 `talib.FUNC(*arrays)` **byte 相等**。mutation:從 `_INPUT_TYPE_MAP` 刪一項(如 ATR)→ 測試必紅。
- C1-3(oracle 三級)(1)talib/scipy/pandas 有一致 API → EXACT differential;(2)文獻公式 → **獨立 reference 實作**(`tests/references/*_ref.py`,不得 import 被測模組);(3)簡化變體 → 三方簽 off 後 golden-lock + metadata `variant`。每欄 metadata 標 oracle class;無外部 oracle 不得宣稱公式正確。mutation:EOM `*`→`/` 必紅。

**P0-FF-2(全鏈 MR)**
- C2-1(EXACT 不變量)真 kline 跑 `generate_features()`。**warmup = config-driven `estimate_max_warmup_bars(config, primary_tf, tfs)`,禁 data-dependent「首全填列」`_warmup_cutoff_row`**。比對:先 `assert list(full.columns)==list(trunc.columns)`(columns gate),再在 **共同 timestamp 交集** 上比 `full.iloc[warmup:-k]` vs `trunc.iloc[warmup:-k]` 的 values + NaN mask + index timestamps + metadata row_count/data_range。
- C2-2(同檔)尾 k bar OHLCV `±1e6` 擾動 → 截斷點前列不變。mutation:某層注入 `shift(-1)` / `center=True` rolling / 全量 fit → C2-1/C2-2 必紅。
- **C2 config 分級**:`test_ff_causal_mr_production`(requires_kline,nightly,production preset 全欄)vs `_fast`(smoke)。**勿用 fast 冒充 production 覆蓋**。

**P0-FF-3 範圍解(消除矛盾)**:本批 C2-1 第一版 = **單 primary-TF + production preset 全欄**,**明示不取代 P0-FF-3**(MultiTF 粗→細高頻截斷 MR 另批)。C2-1 文字移除「multi-TF 粗→細」宣稱,改為「多 TF 聚合留 FF-3」。

**P0-FF-4**
- C4-1 註冊 `pytest.ini` marker `requires_kline`(現未註冊);correctness 測試缺指定 kline → **FAIL**。雙 job:PR `-m "not requires_kline"` smoke;nightly correctness 缺 manifest/kline → FAIL。逃生口只給開發者顯式 exclude,**不給 CI 靜默綠**。
- C4-2 `tests/fixtures/DATA_MANIFEST.json`:覆三方數據簽核要求的 **10 symbol × 3 TF**(symbol,TF,最少列數,sha256);啟動校驗,漂移→FAIL。
- C4-3 mutation:改 manifest sha / 缺 symbol×TF / row_count below min 三種皆 FAIL。

**mutation 鐵律(兩家)**:每個 mutant 在 SPEC/TODO 列**具體 patch 點 + 驗收命令**;實作前先寫 failing probe(章程 §B);合併前由**原提出方**重跑同一反例確認真關閉(§B8)。驗收報告附 fail 摘要。

## 四、範圍/邊界(收斂)
- **不全重測**:V-6 as-of golden、L6.5 causal winsor、L3 numba differential 已 P0(`test_numba_rolling`/`test_causal_winsor`/`test_failopen_correctness` V-6),不重做。
- P1-FF-7(wrapper source 多路徑)與 P0-FF-1 **重疊 → SPEC 合併**避免雙重/漏項;polars/numba 多路徑列入 P0-FF-1 範圍註記。
- 本批 = P0-FF-1/2/4 + BUG-1/BUG-2 修;P0-FF-3、P1-FF-5/6 另批。

## 戳記(委員 R2 審本 reconcile + 修正設計後 append;v2 須帶 `sha256:<body-hash> task:<id>`)
（Claude 已採納兩家全部收斂 BLOCK;待 codex/composer R2 確認 BLOCK 真關閉——§B8 原提出方重跑反例。委員 append 前先 `bash scripts/reconcile_body_hash.sh <本檔>` 取雜湊。）
RECONCILE-STAMP: codex APPROVED 2026-06-27 sha256:fa597372175b491dfb14c8ade1b5c59627f85fd6efa5a07bcfdd076edeee71a3 task:ff-deepaudit-r2b
RECONCILE-STAMP: composer APPROVED 2026-06-27 sha256:fa597372175b491dfb14c8ade1b5c59627f85fd6efa5a07bcfdd076edeee71a3 task:ff-deepaudit-r2b
