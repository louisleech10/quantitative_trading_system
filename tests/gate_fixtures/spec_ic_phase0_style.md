# Probe SPEC — IC_PHASE0 同款 §A 結構（ADV-P2）

## §RISK
- **大小**：大。
- **命中高風險原則**：(b) 跨模組；(d) ML 正確性敘述。
- RISK-HIT: b,d

## §A

### 已驗證事實（每項標 fact-verified）
1. **TIMEAXIS**〔fact-verified〕：`read_klines` 回 RangeIndex + `timestamp` int64 秒級欄；`_get_time_index` 對 Series 呼叫 `pd.to_datetime(values, unit="ms")` → 回傳 Series 非 DatetimeIndex。
2. **DTYPE**〔fact-verified〕：實跑 `timestamp[0]=1704067200`，`unit=s` 對齊 2024、`unit=ms` 錯軸 1970。

### 待使用者確認
- 待確認：無

### 已確認結果
- 探針用空殼標題。

## §C
- 解耦 7 條；不弱化 NaN·inf gate。

## §G
- baseline：`pytest tests/momentum/test_ic_*.py` exit == 0；sha256 對照 fixture。

## §P
### Phase 1 — 止血（依賴：無）
**Task 1.1 — 時間軸**
- 目標：修 `_get_time_index`。
- **驗證**：`pytest tests/momentum/test_ic_timeaxis.py -q` → exit 0。
- **邊界**：RangeIndex+秒級 timestamp；禁 ms 假綠。
- 不可做：不寫死單位。

## §V
- 單元 + golden；`pytest tests/...` 獨立跑。

## §R
- 每 Phase revert。

## §N
- 無。
