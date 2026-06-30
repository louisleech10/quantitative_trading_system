# FF 因果性三方數據簽核 + B2 設計 — reconcile(定案)

> 使用者無法自判,全權委派委員會(三方數據簽核鐵律)。三腿:Claude / Codex / Composer,皆**獨立讀碼複核**(未重跑全鏈,避 timeout)。

## 一、FF 因果性簽核:**三方一致 PASS — 可用於量化研究**
**Claude PASS + Codex PASS + Composer PASS**(任一 HOLD 即不過 → 無 HOLD)。

三方各自**獨立讀碼**確認**沒有任何一層在算 row t 時用到 t+1.. 的資料**:
- **L2 衍生**(`derived_operators.py`):momentum `shift(lag)` 正向;ts_*/decay rolling `center=False`(Codex+Composer)。
- **L3 numba rolling**(`numba_rolling.py`):單向掃描、ring buffer 在 row_idx 移除 row_idx-window、只在 trailing 窗完成後輸出;無 `center=True`(三方)。
- **L4 lag**(`lag_processor.py`):僅 lag≥1 的 `shift(lag)`;`shift(-n)` 只在 IC 標籤/label_generator(非持久特徵)(Codex+Composer grep)。
- **L6.5 preprocess**:`causal_preprocessing` 強制 True;winsor/zscore/rank/gaussian trailing 窗;fracdiff d-star 只用校準前綴 `iloc[:bars]`(三方)。
- **實證**:截尾 K bar → 暖機後前綴值僅差 float16 儲存(≤0.1%);mutation 注入 look-ahead 差數量級(測試抓得到)。

**結論**:量化最致命的 look-ahead = FF 乾淨,回測真實性紅線過。**FF 可用於量化研究。**

**兩個 productionization caveat(三方同意,非新危機,非 look-ahead)**:
1. **float16 可重現性(輕)**:borderline 欄跨窗值差 ≤0.1%、dtype 翻面;ML 噪音級,研究可用,不可宣稱 bit-repro。
2. **特徵集列數依賴(中,已有 epic)**:NaN blacklist / L7 dead_drop 使 near-empty 欄跨窗不對稱 → train/serve 特徵集一致性,屬 **[[project-stateful-param-audit]]** epic(三方已盤點),上線前處理。

## 二、B2 測試設計:三方收斂定案
測**因果(過去不依賴未來)**,非測儲存/bit 確定性。主 MR + fracdiff 專屬 MR 兩層。
1. **columns gate**:比交集;**不對稱掉欄 > `max(100, 0.1%×|union|)` 則 fail**(防整層消失被掩蓋),assertion 列 sample 欄名。(Composer 0.1% 較嚴,採;Codex 1% 為上界)
2. **values gate**:交集欄 × `[warmup:n_trunc)` × **both-non-NaN** 位置,`allclose(rtol=2e-3, atol=1e-12)`。
3. **NaN mask 分層(防 mask-only 洩漏)**:
   - **高 fill_rate(≥95%)共同欄 → NaN mask exact**(違反 fail);
   - 低 fill_rate / near-empty / 僅一側欄 → informational 記錄不 fail(列數依賴良性)。
   - + **覆蓋率守衛**(Codex):≥95% 共同欄有可比 post-warmup cell、≥99% overlap cell 被比 → 否則 fail(防全被歸 informational 空轉)。
4. **mutation 探針必紅**(P0 硬門檻):rolling center=True / L4 shift(-1) / 全量 winsor fit / fracdiff 校準擾動 / fracdiff 全量 d-star。+ **test_c2_2 尾端 OHLCV 擾動**前綴不變。
5. **fracdiff 專屬 MR 維持嚴格**:窗≥校準、d-star equality、fracdiff 值 atol=1e-8、exact NaN mask(校準設計是被測物)。

**待改(三方讀碼指出,現測試與收斂設計不一致)**:
- `_assert_columns_gate` 現 strict equality → 改 #1 交集+門檻。
- `_assert_arrays_values_close` 現全段 NaN mask exact → 改 #3 分層。
- 已對:FLOAT16_RTOL=2e-3、L7 dead_drop 關、fracdiff 分層、mutation 結構。

## 三、範圍註
- B2 主 MR = 單 TF。**cross_sectional / multi-TF 全鏈因果留 B3**(Composer);multi-TF 對齊已有 V-6 golden、L6.5 因果已有 V-5(HANDOFF 強項)。

## 戳記(委員 append `^SIGN-OFF-STAMP: <family> APPROVED <date>`)
（三腿 leg 檔均已書 SIGN-OFF: FF-CAUSAL PASS + B2-DESIGN 同意;本 reconcile 彙整。)
