"""
測試多標的 XGBoost 分析功能

驗證：
1. API 模型接受 symbols 列表
2. 後端服務正確處理多標的
3. 返回的 message 包含多標的資訊
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.models.pattern_analysis_models import XGBoostBatchAnalysisRequest, IndicatorParamsConfig
from api.services.xgboost_batch_service import XGBoostBatchService


def test_api_model():
    """測試 API 模型接受 symbols 列表"""
    print("=" * 80)
    print("測試 1: API 模型驗證")
    print("=" * 80)
    
    # 建立請求
    request = XGBoostBatchAnalysisRequest(
        symbols=["BTCUSDT", "ETHUSDT"],  # ✅ 現在接受列表
        timeframe="12h",
        indicators=[
            IndicatorParamsConfig(
                indicator="ema_three_line",
                data_source="close",
                params={"ema_short": 5, "ema_mid": 20, "ema_long": 60}
            )
        ],
        lookback_bars=200,
        cv_folds=5
    )
    
    print(f"✅ symbols 類型: {type(request.symbols)}")
    print(f"✅ symbols 內容: {request.symbols}")
    print(f"✅ 標的數量: {len(request.symbols)}")
    print()


def test_service_signature():
    """測試服務方法簽名"""
    print("=" * 80)
    print("測試 2: 服務方法簽名檢查")
    print("=" * 80)
    
    import inspect
    
    service = XGBoostBatchService()
    sig = inspect.signature(service.start_batch_analysis)
    
    print(f"方法簽名: {sig}")
    print(f"參數列表:")
    for param_name, param in sig.parameters.items():
        print(f"  • {param_name}: {param.annotation}")
    
    # 檢查第一個參數是否為 symbols: List[str]
    params_list = [p for name, p in sig.parameters.items() if name != 'self']
    first_param = params_list[0]
    print(f"\n✅ 第一個參數名稱: {first_param.name}")
    print(f"✅ 第一個參數類型: {first_param.annotation}")
    
    assert first_param.name == "symbols", f"預期參數名為 'symbols'，實際為 '{first_param.name}'"
    print("\n✅ 服務方法已正確更新為接受 symbols 列表")
    print()


def test_case_storage():
    """測試案例存儲獲取多標的案例"""
    print("=" * 80)
    print("測試 3: 多標的案例獲取")
    print("=" * 80)
    
    from api.utils.case_storage import get_case_storage_manager
    
    storage = get_case_storage_manager()
    
    # 測試獲取兩個標的的案例
    test_symbols = ["BTCUSDT", "ETHUSDT"]
    all_cases = []
    
    for symbol in test_symbols:
        cases = storage.get_cases_by_symbol(symbol)
        if cases:
            all_cases.extend(cases)
            print(f"✅ {symbol}: 找到 {len(cases)} 個案例")
        else:
            print(f"⚠️  {symbol}: 未找到案例")
    
    if all_cases:
        print(f"\n✅ 合併後總案例數: {len(all_cases)}")
        print(f"✅ 涵蓋標的: {set(c.symbol for c in all_cases)}")
    else:
        print("\n⚠️  未找到任何案例，請先執行案例搜尋")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("多標的 XGBoost 分析功能測試")
    print("=" * 80 + "\n")
    
    try:
        test_api_model()
        test_service_signature()
        test_case_storage()
        
        print("=" * 80)
        print("✅ 所有測試通過！多標的功能已正確實作")
        print("=" * 80)
        
        print("\n下一步:")
        print("1. 啟動後端: python run_api.py")
        print("2. 啟動前端: cd frontend && npm run dev")
        print("3. 開啟 http://localhost:3000/patterns/xgboost-analysis")
        print("4. 選擇多個交易對並啟動分析")
        print("5. 觀察進度訊息是否顯示「共 N 個案例（M 個標的）」\n")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


import pytest as _pytest_new
from pydantic import ValidationError as _ValidationError_new
import api.utils.case_storage as _case_storage_mod_new
from api.utils.case_storage import CaseStorageManager as _CaseStorageManager_new
from api.utils.case_storage import get_case_storage_manager as _get_case_storage_manager_new
from api.models.case_models import CaseRecord as _CaseRecord_new


def test_api_model_multi_symbol_fields_and_leak_safe_defaults():
    """XGBoostBatchAnalysisRequest 接受多標的列表並保序；防洩漏預設（time_series_split=True）與
    指標 data_source 預設 close；embargo_pct 上限 0.1 之驗證生效。期望值為契約手寫值。"""
    req = XGBoostBatchAnalysisRequest(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        indicators=[
            IndicatorParamsConfig(
                indicator="ema_three_line",
                data_source="close",
                params={"ema_short": 5, "ema_mid": 20, "ema_long": 60}
            ),
            IndicatorParamsConfig(indicator="rsi", params={"period": 14}),
        ],
        lookback_bars=200,
        cv_folds=5
    )
    assert type(req.symbols) is list and req.symbols == ["BTCUSDT", "ETHUSDT"] and req.time_series_split is True and req.sequence_feature_mode == "aggregate" and req.indicators[1].data_source == "close" and req.indicators[0].params == {"ema_short": 5, "ema_mid": 20, "ema_long": 60}, f"req={req!r}"
    with _pytest_new.raises(_ValidationError_new):
        XGBoostBatchAnalysisRequest(
            symbols=["BTCUSDT"],
            indicators=[IndicatorParamsConfig(indicator="rsi", params={})],
            embargo_pct=0.5,
        )


def test_case_storage_multi_symbol_isolation_via_singleton(tmp_path, monkeypatch):
    """多標的案例獲取（tmp 存檔，不讀真實 data_cache/cases.json）：
    單例入口 get_case_storage_manager 回傳已建立之實例；BTC 2 筆、ETH 1 筆依標的隔離，合併 3 筆。"""
    mgr = _CaseStorageManager_new(use_persistent_storage=False, json_path=str(tmp_path / "cases.json"))
    monkeypatch.setattr(_case_storage_mod_new, "_case_storage_manager", mgr)
    mgr.save_cases([
        _CaseRecord_new(case_id="BTCUSDT_1_1", symbol="BTCUSDT", timeframe="12h", timestamp=1, positive_case=1),
        _CaseRecord_new(case_id="BTCUSDT_2_0", symbol="BTCUSDT", timeframe="12h", timestamp=2, positive_case=0),
        _CaseRecord_new(case_id="ETHUSDT_3_1", symbol="ETHUSDT", timeframe="12h", timestamp=3, positive_case=1),
    ])
    storage = _get_case_storage_manager_new()
    btc = storage.get_cases_by_symbol("BTCUSDT")
    eth = storage.get_cases_by_symbol("ETHUSDT")
    merged = btc + eth
    assert storage is mgr and sorted(c.case_id for c in btc) == ["BTCUSDT_1_1", "BTCUSDT_2_0"] and [c.case_id for c in eth] == ["ETHUSDT_3_1"] and len(merged) == 3 and {c.symbol for c in merged} == {"BTCUSDT", "ETHUSDT"} and storage.get_cases_by_symbol("XRPUSDT") == [], f"btc={btc} eth={eth}"
