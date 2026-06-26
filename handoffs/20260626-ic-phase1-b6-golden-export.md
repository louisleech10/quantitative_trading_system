# IC Phase 1 B6 Golden + Export Route

## 正在做
- B6 G3 split/leakage golden 與 B5 export route bounded residual 已完成。

## 待辦
- Claude 驗收既有 B0-B5 大量未追蹤檔與本次 diff 範圍。

## 阻塞
- none

## 本次決策
- 新增 `tests/golden/ic_phase1_contract/test_split_leakage_golden.py`，使用真實 `data_cache/feature_klines/kline_cache.h5` BTC+ETH 1h。
- G3 覆蓋 gap、unsorted、duplicate timestamp、sorted-but-multi-symbol 反例，皆 `pytest.raises`。
- 補 `split_per_symbol` golden：每 plan symbol purity==1.0、train rows 等於 expected global rows、purge 不跨 symbol 邊界。
- 補 `tests/api/test_ic_response_v2.py::test_export_route_streaming`，用 `TestClient.stream()` bounded read 驗 200、Content-Disposition、body 非空。
- 修 `api/routes/ic_analysis.py`：`export_result["type"]=="bytes"` 回普通 `Response`，避免 `BytesIO` 被 `StreamingResponse` 包裝後在 TestClient 下 hang。

## 踩坑提醒
- 初版 route streaming test 直接卡住；根因是 bytes payload 已 materialized，不能再依賴 StreamingResponse generator 行為。
- 驗證命令 `pytest tests/momentum/core/ tests/momentum/Analysis/ tests/api/test_ic_response_v2.py tests/golden/ic_phase1_contract/ -q` 通過 355 passed。
- `grep -rE "from api\\." momentum/` 與 `grep -r "from api" momentum/core momentum/Analysis/ic_split_adapter.py momentum/Analysis/ic_artifact_writer.py` 皆 0 輸出。
- `./scripts/check_decoupling_phase4.sh` 通過，內含 Strategy 135 passed。
