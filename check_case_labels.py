"""
檢查案例的正負例分佈

用於診斷 XGBoost 訓練失敗問題
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.utils.case_storage import get_case_storage_manager


def check_case_labels():
    """檢查各標的案例的正負例分佈"""
    storage = get_case_storage_manager()
    
    test_symbols = ["BTCUSDT", "ETHUSDT"]
    
    print("=" * 80)
    print("案例正負例分佈檢查")
    print("=" * 80)
    
    all_results = {}
    
    for symbol in test_symbols:
        cases = storage.get_cases_by_symbol(symbol)
        
        if not cases:
            print(f"\n{symbol}: ⚠️  未找到案例")
            continue
        
        # 統計正負例
        positive_cases = [c for c in cases if c.positive_case]
        negative_cases = [c for c in cases if not c.positive_case]
        
        positive_count = len(positive_cases)
        negative_count = len(negative_cases)
        total_count = len(cases)
        
        result = {
            'total': total_count,
            'positive': positive_count,
            'negative': negative_count,
            'positive_ratio': positive_count / total_count if total_count > 0 else 0
        }
        
        all_results[symbol] = result
        
        print(f"\n{symbol}:")
        print(f"  總案例數: {total_count}")
        print(f"  ✅ 正例（盈利）: {positive_count} ({result['positive_ratio']*100:.1f}%)")
        print(f"  ❌ 反例（虧損）: {negative_count} ({(1-result['positive_ratio'])*100:.1f}%)")
        
        if positive_count == 0:
            print(f"  ⚠️  WARNING: 沒有正例，無法訓練模型！")
        elif negative_count == 0:
            print(f"  ⚠️  WARNING: 沒有反例，無法訓練模型！")
        elif positive_count < 10 or negative_count < 10:
            print(f"  ⚠️  WARNING: 正例或反例數量過少，模型可能不穩定")
        else:
            print(f"  ✅ 案例分佈正常，可以訓練")
    
    # 合併統計
    if len(all_results) > 1:
        print("\n" + "=" * 80)
        print("合併統計（多標的訓練）")
        print("=" * 80)
        
        total_all = sum(r['total'] for r in all_results.values())
        positive_all = sum(r['positive'] for r in all_results.values())
        negative_all = sum(r['negative'] for r in all_results.values())
        
        print(f"\n合併後:")
        print(f"  總案例數: {total_all}")
        print(f"  ✅ 正例（盈利）: {positive_all} ({positive_all/total_all*100:.1f}%)")
        print(f"  ❌ 反例（虧損）: {negative_all} ({negative_all/total_all*100:.1f}%)")
        
        if positive_all == 0:
            print(f"  ⚠️  WARNING: 沒有正例，無法訓練模型！")
        elif negative_all == 0:
            print(f"  ⚠️  WARNING: 沒有反例，無法訓練模型！")
        elif positive_all < 10 or negative_all < 10:
            print(f"  ⚠️  WARNING: 正例或反例數量過少，模型可能不穩定")
        else:
            print(f"  ✅ 合併後案例分佈正常，可以進行跨標的訓練")
    
    print("\n" + "=" * 80)
    print("建議:")
    print("=" * 80)
    print("1. 如果單一標的全是正例或反例，請選擇多個標的合併訓練")
    print("2. 如果所有標的都只有一種標籤，請調整案例搜尋條件")
    print("3. 理想的案例分佈: 正例 30%-70%，反例 30%-70%")
    print("4. 最少需要: 正例 >= 10 且 反例 >= 10\n")


if __name__ == "__main__":
    check_case_labels()
