# FF 因果性三方簽核 + B2 測試設計 — Claude 腿

> 使用者無法自判「FF 是否可用於量化」與「B2 測試怎麼收」,全權委派委員會(三方數據簽核鐵律)。
> 本文=Claude 獨立腿(判斷+設計),待 Codex/Composer 各獨立腿 → 三方 reconcile。
> **委員從已蒐證據+讀碼判斷,勿重跑全鏈(generate_features 全開 ~14分/次,反覆 timeout)**;必要時只做小範圍 targeted 實驗。

## 一、證據摘要(B2 全鏈截斷 MR 實測,真 kline BTCUSDT/1h)
全開 config(全 10 原子+全前處理,排 fracdiff),窗 2081(warmup 2051),截尾 K=10:
- **暖機後前綴的特徵「值」在截斷前後相同**(差異僅來自儲存):
  - 實證 1:`LINEARREG-ANGLE_144` full=2.6132964e-05(float32)vs trunc=2.61e-05(float16)= **同一值的 float16 捨入**,rel_err 9.999e-4(< float16 容差 1e-3)。
  - 即:**砍掉未來 bar,過去的特徵值不變**(除儲存精度)。
- **差異全部來自兩類良性、非因果的機制**:
  1. **roundtrip-safe float16 降精度**(`feature_storage.py:2555`,誤差 ≤ FLOAT16_MAX_REL_ERROR=1e-3 才降):borderline 欄在 full(2081列)vs trunc(2071列)會 float16↔float32 翻面。值差 ≤0.1%。
  2. **列數依賴的 NaN/dead-feature 處理**(NaN blacklist 按 NaN 比例、L7 dead_drop 按 min_valid/總列數):near-empty 衍生欄(如 `MACDEXT-Hist_13-55-13_Momentum_L144`)在不同總列數下被丟/留/處置略不同 → NaN mask 差。
- **mutation 探針反證**:注入 look-ahead(rolling center=True / lag shift(-1) / 全量 fit)→ 差異遠超 0.1%(數量級)→ 測試抓得到。真實 pipeline 無此級差異 = 無 look-ahead。

## 二、Claude 判斷:FF 是否可用於量化?
**可用於量化研究(no look-ahead);有兩個 productionization caveat,皆已知非新危機。**
- **量化最致命的 look-ahead:FF 乾淨**。截斷未來→過去值不變(僅儲存精度差),這是回測真實性的紅線,過。**不會因偷看未來而回測虛高、上線破功。**
- **Caveat 1(可重現性,輕)**:float16 儲存使 borderline 欄跨窗值差 ≤0.1% → 非 bit-reproducible。對 ML 是噪音級,無害;是刻意記憶體優化(15萬特徵)。
- **Caveat 2(特徵集穩定,中,已有 epic)**:列數依賴的 NaN/dead 處理使「哪些 near-empty 欄存在」跨窗略不同 → train/serve 特徵集一致性需留存特徵清單。**這正是 [[project-stateful-param-audit]] epic(三方已盤點)**,非新發現。
- **結論**:研究階段可用;上線(productionization)須持久化特徵清單 + 考慮讓 downcast/drop 對固定特徵集確定性。**「資料品質差不能用」= 否**;真正的紅線(look-ahead)是過的。

## 三、Claude 設計:B2 因果 MR 怎麼收(對準它該測的)
測試該驗「**過去不依賴未來**」,不該管儲存/空欄後處理:
- **columns gate**:比交集;只在一邊的欄(列數依賴 drop)= 記錄 informational,不 fail(但列出供稽核,防大量掉欄掩蓋問題——設上限,如 drop 差異 > X% 才 fail)。
- **values gate**:對共同欄、**兩邊都非 NaN** 的位置,值在容差(2× float16 = rtol 2e-3)內一致。這直接測 look-ahead(真偷看→值大幅變)。
- **NaN mask**:不要求暖機區 exact(列數依賴 NaN 處理良性);改為「**非列數依賴處理的欄** NaN mask 一致」,或退一步:NaN-mask 差異記錄,值比對在 both-non-NaN 上做(look-ahead 會在值上現形)。委員定哪個夠嚴。
- **mutation 探針保留**(center/shift/全量fit 必紅;rtol 2e-3 下仍遠超)。
- **fracdiff 專屬 MR 保留**(Codex 前設計:窗>校準+d-star穩定+容差+negative control)。

## 四、待委員(Codex/Composer)各獨立腿
1. 同意/反對「FF 因果健全可用於量化(+2 caveat)」?有無讀碼發現某層真用未來資料(我可能漏看)?
2. B2 測試設計:common-valid-region + 容差 + NaN/drop 良性化 是否夠嚴(不放走真 look-ahead)?columns drop 差異要不要設上限門檻防掩蓋?NaN mask 退讓到什麼程度仍可證偽?
3. 三方簽核結論:`SIGN-OFF: FF-CAUSAL PASS/HOLD` + `B2-DESIGN 同意/修正`。
