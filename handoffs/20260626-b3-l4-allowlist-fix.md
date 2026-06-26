# 20260626 B3 L4 allowlist fix

## 正在做
- B3 L4 sentinel 與 split symbol allowlist 防線已落地。

## 待辦
- B5/B6 接線端傳入真實 allowed_symbols universe 後可啟用權威防線。

## 阻塞
- none

## 本次決策
- `_normalize_symbol_value` 補 `<na>` sentinel，涵蓋 pandas `pd.NA` repr 字串。
- `validate_split_integrity` / `validate_split_pair_integrity` / `split_per_symbol` 增加 `allowed_symbols: Optional[set[str]] = None`。
- `ICSplitAdapter` 增加 class 與 method-level `allowed_symbols`，傳入 contract validation。
- `allowed_symbols=None` 保持既有 blocklist best-effort 行為。

## 踩坑提醒
- blocklist 不是權威防線，只能擋常見缺值 sentinel。
- allowlist 檢查會掃整個資料 symbol universe，不只掃 selected row。
- 本次未改 wf/cpcv implementation。
