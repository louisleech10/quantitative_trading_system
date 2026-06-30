# 派工:targeted 修 B2 values gate(Composer)— float16 容差非嚴格 dtype

## 根因(Claude 真測試診斷確認)
`test_c2_1` 失敗 assertion = `taker-ratio_1h_statistics_LINEARREG-ANGLE_144 dtype mismatch: float32 vs float16`。值幾乎一樣(0.00414397 vs 0.004143),只是**儲存精度因窗不同**:`feature_storage.py:2555 _array_for_parquet` 對每欄做 **roundtrip-safe float16 降精度**(誤差 ≤ FLOAT16_MAX_REL_ERROR=1e-3 才降),borderline 欄在 full(2561根) vs trunc(2551根)會翻 float16↔float32。**這是合法、必要、有界(0.1%)的優化,非 look-ahead,非 bug**。

## 修法(只改測試比對,不改 storage)
- `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 的 `_assert_arrays_byte_equal`/values gate:
  - **丟掉嚴格 `left.dtype == right.dtype` 檢查**(dtype 是合法降精度結果)。
  - 改成:兩邊 **cast np.float32** 後比 `np.allclose(rtol=1e-3, atol=1e-12)`(= 系統 float16 容差 FLOAT16_MAX_REL_ERROR/ABS);**NaN mask 仍 exact**;**columns 仍 exact**。
  - 命名:這條是「值因果穩定(容差內)」非「byte 級」——更新 docstring/函式名避免誤導(原叫 byte_equal,改成 values gate 容差版)。
- **保留 fracdiff 專屬 MR 的容差(已 atol=1e-8)**;主 MR 用 float16 容差(1e-3 rel)因為主 MR 含被降精度的欄。
- **mutation 探針要仍能紅**:center=True/shift(-1)/全量fit 造成的差遠超 0.1% 容差 → 探針仍 FAIL(確認跑 mutation_probe_check 仍 PASS,即探針真紅)。

## 注意 / 加 note
- 在測試檔頂註解記:borderline 欄會因窗 float16↔float32 翻面=良性(roundtrip-safe ≤0.1%),故主 MR 用容差非 byte。
- WINDOW:確認主 MR 窗 > warmup(~2051)有足夠暖機後可比列(現 _required_window_bars 已含 warmup)。

## 收尾
- 自跑 `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -q`(慢,給夠時間)全綠 + `bash scripts/mutation_probe_check.sh tests/feature_engineering/test_ff_fullchain_truncation_mr.py` PASS(探針真紅)。附耗時。
- 寫 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`。跑後 git checkout 還原 golden。完成 STATUS: DONE/BLOCKED。兩輪卡住→BLOCKED 不 solo。
