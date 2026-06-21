# B6 warmup-then-trim — Adversarial Review (Composer 2.5)
SPEC=`docs/B6_WARMUP_TRIM_SPEC.md` TODO=`docs/B6_WARMUP_TRIM_TODO.md` | 2026-06-22 | read-only

## Verdict：需修補後派工
核心 Option 1 可行，但 §A 把未驗證假設當事實、parity 例外表不完整、multi-TF/CGSA trim 與 max_warmup 來源未閉環；不修補派工高機率假綠或靜默降級。

## Findings
1. **[BLOCKING|High]** §A「無真正 expanding；唯一位置相依是 fracdiff d*」與 `warmup_table.yaml:367-386` cumulative_special_cases(OBV/AD/ADOSC/VWAP `burn_in_from_dataset_start`)矛盾；`get_max_warmup_bars` 不讀 cumulative。→ date-windowed 即使 warmup 足，累積量級仍≠全範圍同日期。修法：列 parity 例外或排除欄；Task1.1 納 cumulative burn-in。
2. **[BLOCKING|High]** §C/TODO 僅 fracdiff d* 例外；`feature_preprocessor.py:3334` ADF differencing 亦用 `_calibration_series`+`head(sample_size)` 決策。→ 與 fracdiff 同類非 PIT parity 風險。修法：ADF 併入 FRACEXC 或獨立例外+測試跳過。
3. **[BLOCKING|High]** Task1.1 列 L1/L3/L6.5/fracdiff/native-tf，漏 **L4 max(lag)**(`lag_processor.py:158-163`)、**L2 衍生窗**(worldquant/momentum lags `feature_factory.py:1278-1298`)、**rank/zscore 窗**(post_ic 輸出)、**zscore max(windows)**。→ 低估 max_warmup→邊界 winsor/zscore/lag 非 byte 一致。修法：Task1.1 明列公式+單測每源。
4. **[MAJOR|High]** Multi-TF：`multi_tf_generator.py:162-165` 每 TF 獨立 `_layer0`；Task2.1 只寫 primary bar×週期，未規定次 TF 用 timestamp span 或 `scale_window_for_native` 換算；Task2.2「對齊後 trim」未覆蓋 **compact native 組**(1696 vs 20352 列 `_native_tf_helpers.py:5-16`)。→ 誤砍/漏 trim 或 native L6.5 parity 失敗。修法：per-TF ingest 規則+primary index mask 傳播 idx_map。
5. **[MAJOR|High]** CGSA L3 streaming persist(`feature_factory.py:1606-1629`) 中間寫盤；Task2.2 僅「L7 前 trim」無 resume/checkpoint 列裁剪。→ 磁碟含 warmup 列或 resume 污染。修法：trim mask 貫穿 stream persist 或 flag 開禁用未 trim checkpoint。
6. **[MAJOR|High]** §V parity 用 `allclose≤1e-6` 但未定：**比對層級**(L1-L6 vs pre_ic vs post_ic)、**欄集合**(排除 fracdiff/ADF/cumulative)、**NaN mask 一致**、float32 CGSA 容差。→ aggregate allclose 可假綠。修法：§G 補 column manifest+`assert_array_equal` on NaN+分層 rtol。
7. **[MAJOR|Medium]** IC-First：pre_ic winsor 邊界影響 IC 選特(`feature_factory.py:2077-2115`)；parity 只比 values 不比 selection→最終輸出結構可完全不同。修法：parity 測試固定 mock IC 或分開驗 L1-L6/pre_ic。
8. **[MAJOR|Medium]** Task2.3 邊界「完全無前史→needed/available=0」與 needed=max_warmup 矛盾。修法：available=0, needed=max_warmup, 強制警示。
9. **[MINOR|High]** flag 名/env、Pydantic metadata 欄位名、受影響前段計算式未寫死→Agent 腦補。修法：SPEC 補 env key+contract 欄位。
10. **[MINOR|Medium]** PIT 只 assert `max(warmup_index)<start`；未驗證 fracdiff/ADF 校準僅用 warmup 段。修法：加 calibration slice 上界 assert。

## 被當成事實的未驗證假設
- §A「無 expanding/僅 fracdiff 位置相依」→ **假設**；cumulative YAML 已否定(MAJOR+)。
- §A「warmup_lookup 可覆蓋 L1」→ **部分**；cumulative/CDL pattern bars 未接入 get_max_warmup_bars。
- §C「非 fracdiff 全 byte 一致」→ **未驗證**；缺 winsor min_periods 邊界實測+欄級排除表。
- §V「真實 kline parity」→ **未設計**；無 symbol/TF/日期窗/fixture 命令。

## §1 十類速查
矛盾:無｜漏項:#3-5｜不可測:#6-7｜quant:#1-2,7｜過度工程:無｜OOM:無｜Cache:#5｜相容:#9｜測試:#6-7｜Agent:#9

STATUS: DONE
