"""IC API model tests."""

from api.models.ic_models import CrossRunRef, ICAnalyzeRequest


def test_ic_analyze_request_config_hash_optional() -> None:
  request = ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h")
  assert request.config_hash is None

  with_hash = ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h", config_hash="abc123")
  assert with_hash.config_hash == "abc123"


def test_ic_analyze_request_cross_sectional_runs() -> None:
  request = ICAnalyzeRequest(
    mode="cross_sectional",
    timeframe="12h",
    cross_sectional_runs=[
      CrossRunRef(symbol="BTCUSDT", config_hash="hash_a"),
      CrossRunRef(symbol="ETHUSDT", config_hash="hash_b"),
    ],
  )
  assert request.cross_sectional_runs is not None
  assert len(request.cross_sectional_runs) == 2
  assert request.cross_sectional_runs[0].symbol == "BTCUSDT"
  assert request.cross_sectional_runs[0].config_hash == "hash_a"


# ══════════════════════════════════════════════════════════════════════════
# EVTLABEL Task 3.2 — event_label_mode 之請求欄與兩條 transport 不變式
#
# 這批測試在防什麼：`event_label_mode` 是**請求**不是結論。放行「沒有事件批卻指定模式」
# 或「掃描網格＋匯入標籤模式」都會產生看起來成功、實際上沒做到使用者想要的事的 run。
# ══════════════════════════════════════════════════════════════════════════


def test_event_label_mode_defaults_to_auto() -> None:
  """預設 auto：有可用的 0/1 就用，否則後端退回報酬版並寫明原因。"""
  request = ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h")
  assert request.event_label_mode == "auto"


def test_event_label_mode_accepts_the_three_contract_values() -> None:
  """值集必須與契約檔 `label_modes` 相等——兩端各自手打就會分歧。"""
  import json
  from pathlib import Path

  contract = json.loads(
    (Path(__file__).resolve().parents[2] / "momentum/Analysis/contracts/event_label_mode.json")
    .read_text(encoding="utf-8")
  )
  for mode in contract["label_modes"]:
    kwargs = {"symbol": "BTCUSDT", "timeframe": "1h", "event_label_mode": mode}
    if mode != "auto":
      kwargs["event_import_id"] = "imp-1"   # 不變式①：非 auto 必須帶批
    assert ICAnalyzeRequest(**kwargs).event_label_mode == mode


def test_event_label_mode_unknown_value_rejected() -> None:
  """邊界②：大小寫錯／未知值 ⇒ pydantic 422（不 silent coerce）。"""
  import pytest

  for bad in ("Imported_Binary", "binary", "IMPORTED_BINARY", ""):
    with pytest.raises(Exception):
      ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h", event_import_id="imp-1", event_label_mode=bad)


def test_non_auto_mode_without_import_id_rejected() -> None:
  """不變式①：0/1 標籤住在事件批裡，沒有批就沒有標籤可用 ⇒ 400。"""
  import pytest

  for mode in ("imported_binary", "return_rule"):
    with pytest.raises(ValueError, match="event_import_id"):
      ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h", event_label_mode=mode)


def test_legacy_event_timestamps_path_rejects_the_field() -> None:
  """邊界①：legacy（只帶 event_timestamps）帶模式欄 ⇒ 400（該路徑沒有事件批可讀標籤）。"""
  import pytest

  with pytest.raises(ValueError, match="event_import_id"):
    ICAnalyzeRequest(
      symbol="BTCUSDT", timeframe="1h",
      event_timestamps=[1, 2, 3], event_label_mode="imported_binary",
    )


def test_scan_grid_with_imported_binary_rejected() -> None:
  """不變式②：掃描是對 k×h 逐格重算**報酬**，匯入標籤模式不用 h 算 label。

  放行的話每一格會得到同一份 0/1、同一組統計 ⇒ 整張網格是假的變化。
  """
  import pytest

  with pytest.raises(ValueError, match="scan_not_applicable_in_imported_binary_mode"):
    ICAnalyzeRequest(
      symbol="BTCUSDT", timeframe="1h",
      event_import_id="imp-1",
      event_label_scan={"decision_offset_bars_max": 2, "horizon_bars_max": 3},
      event_label_mode="imported_binary",
    )


def test_scan_grid_with_return_rule_still_allowed() -> None:
  """反向：報酬版＋掃描是合法組合（不得把不變式②寫成「有掃描就擋」）。"""
  request = ICAnalyzeRequest(
    symbol="BTCUSDT", timeframe="1h",
    event_import_id="imp-1",
    event_label_scan={"decision_offset_bars_max": 2, "horizon_bars_max": 3},
    event_label_mode="return_rule",
  )
  assert request.event_label_mode == "return_rule" and request.event_label_scan is not None
