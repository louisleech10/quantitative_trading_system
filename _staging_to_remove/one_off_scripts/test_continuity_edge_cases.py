"""
測試數據連續性檢查的邊界情況

驗證三種關鍵情況：
1. 不同 symbol 的不同時間框架
2. append 新時間段的處理
3. Warmup 期的連續性
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class ContinuityEdgeCaseTester:
    """連續性邊界情況測試器"""
    
    def __init__(self):
        # 使用臨時目錄進行測試
        self.test_dir = Path(tempfile.mkdtemp(prefix="continuity_test_"))
        logger.info(f"測試目錄: {self.test_dir}")
        
    def cleanup(self):
        """清理測試目錄"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            logger.info(f"已清理測試目錄: {self.test_dir}")
    
    def generate_continuous_klines(
        self, 
        start_timestamp: int,
        count: int,
        interval_seconds: int
    ) -> pd.DataFrame:
        """生成連續的 K 線數據（符合 KlineStorageManager 的格式要求）"""
        timestamps = [start_timestamp + i * interval_seconds for i in range(count)]
        
        # 生成合法的 OHLC 數據
        open_prices = np.random.uniform(100, 200, count)
        close_prices = open_prices * np.random.uniform(0.98, 1.02, count)
        
        # high 必須是 open/close 的最大值再加一點
        high_prices = np.maximum(open_prices, close_prices) * np.random.uniform(1.0, 1.02, count)
        
        # low 必須是 open/close 的最小值再減一點
        low_prices = np.minimum(open_prices, close_prices) * np.random.uniform(0.98, 1.0, count)
        
        # 成交量數據
        volumes = np.random.uniform(1000, 10000, count)
        taker_buy_volumes = volumes * np.random.uniform(0.4, 0.6, count)  # 40-60% 是買方成交
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes,
            'taker_buy_volume': taker_buy_volumes,  # 主動買入成交量
            'taker_ratio': taker_buy_volumes / volumes  # Taker 比率
        })
    
    def test_case_1_different_symbols_timeframes(self) -> dict:
        """
        測試情況1: 不同 symbol 的不同時間框架
        
        驗證：
        - BTCUSDT/1h 和 ETHUSDT/4h 互不干擾
        - 每個獨立驗證連續性
        - 不會交叉污染
        """
        logger.info("\n" + "="*60)
        logger.info("測試情況1: 不同 symbol 的不同時間框架")
        logger.info("="*60)
        
        # 建立子目錄用於此測試
        test1_dir = self.test_dir / "case1"
        test1_dir.mkdir(exist_ok=True)
        storage = KlineStorageManager(cache_dir=str(test1_dir))
        
        results = {
            'test_name': '不同 symbol 的不同時間框架',
            'sub_tests': []
        }
        
        # 子測試1: BTCUSDT 1h（連續）
        btc_1h_data = self.generate_continuous_klines(
            start_timestamp=1640000000,  # 2021-12-20
            count=100,
            interval_seconds=3600  # 1h
        )
        
        success = storage.write_klines('BTCUSDT', '1h', btc_1h_data)
        results['sub_tests'].append({
            'name': 'BTCUSDT/1h 寫入',
            'success': success,
            'expected': True
        })
        
        # 子測試2: ETHUSDT 4h（連續）
        eth_4h_data = self.generate_continuous_klines(
            start_timestamp=1640000000,
            count=50,
            interval_seconds=14400  # 4h
        )
        
        success = storage.write_klines('ETHUSDT', '4h', eth_4h_data)
        results['sub_tests'].append({
            'name': 'ETHUSDT/4h 寫入',
            'success': success,
            'expected': True
        })
        
        # 子測試3: SOLUSDT 12h（故意製造缺口）
        sol_12h_data = self.generate_continuous_klines(
            start_timestamp=1640000000,
            count=20,
            interval_seconds=43200  # 12h
        )
        # 移除中間一根K線製造缺口
        sol_12h_data = pd.concat([
            sol_12h_data.iloc[:10],
            sol_12h_data.iloc[11:]  # 跳過第11根
        ]).reset_index(drop=True)
        
        success = storage.write_klines('SOLUSDT', '12h', sol_12h_data)
        results['sub_tests'].append({
            'name': 'SOLUSDT/12h 寫入（有缺口）',
            'success': success,
            'expected': False,  # 應該失敗
            'note': '驗證系統能偵測到缺口'
        })
        
        # 子測試4: 讀取 BTCUSDT/1h（不應受 SOLUSDT/12h 影響）
        btc_read = storage.read_klines('BTCUSDT', '1h', validate_continuity=True)
        results['sub_tests'].append({
            'name': 'BTCUSDT/1h 讀取驗證',
            'success': btc_read is not None and len(btc_read) == 100,
            'expected': True,
            'note': '不應受其他 symbol 影響'
        })
        
        results['overall_success'] = all(
            t['success'] == t['expected'] for t in results['sub_tests']
        )
        
        logger.info(f"測試情況1 結果: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        
        return results
    
    def test_case_2_append_new_timerange(self) -> dict:
        """
        測試情況2: append 新時間段的處理
        
        驗證三種 append 情境：
        a) 緊接著現有數據（無缺口）→ 應成功
        b) 有時間缺口 → 應失敗
        c) 重疊部分（去重處理）→ 應成功
        """
        logger.info("\n" + "="*60)
        logger.info("測試情況2: append 新時間段的處理")
        logger.info("="*60)
        
        test2_dir = self.test_dir / "case2"
        test2_dir.mkdir(exist_ok=True)
        storage = KlineStorageManager(cache_dir=str(test2_dir))
        
        results = {
            'test_name': 'append 新時間段的處理',
            'sub_tests': []
        }
        
        # 初始數據: 2022-01-01 00:00 開始的 50 根 1h K線
        initial_start = int(datetime(2022, 1, 1, 0, 0).timestamp())
        initial_data = self.generate_continuous_klines(
            start_timestamp=initial_start,
            count=50,
            interval_seconds=3600
        )
        
        success = storage.write_klines('TESTUSDT', '1h', initial_data)
        results['sub_tests'].append({
            'name': '初始數據寫入',
            'success': success,
            'expected': True
        })
        
        # 情境a: 緊接著的數據（無缺口）
        # 最後一根: initial_start + 49*3600
        # 新數據從: initial_start + 50*3600 開始
        seamless_start = initial_start + 50 * 3600
        seamless_data = self.generate_continuous_klines(
            start_timestamp=seamless_start,
            count=30,
            interval_seconds=3600
        )
        
        success = storage.append_klines('TESTUSDT', '1h', seamless_data)
        results['sub_tests'].append({
            'name': 'a) 無縫 append（無缺口）',
            'success': success,
            'expected': True
        })
        
        # 驗證總數
        total_data = storage.read_klines('TESTUSDT', '1h', validate_continuity=True)
        results['sub_tests'].append({
            'name': 'a) 驗證總數 (應為 80)',
            'success': len(total_data) == 80 if total_data is not None else False,
            'expected': True,
            'actual': len(total_data) if total_data is not None else 0
        })
        
        # 情境b: 有缺口的 append（重新開始測試）
        test2b_dir = self.test_dir / "case2b"
        test2b_dir.mkdir(exist_ok=True)
        storage_b = KlineStorageManager(cache_dir=str(test2b_dir))
        storage_b.write_klines('TESTUSDT', '1h', initial_data)
        
        # 跳過 10 根 K線製造缺口
        gap_start = initial_start + 60 * 3600  # 跳過 10 根
        gap_data = self.generate_continuous_klines(
            start_timestamp=gap_start,
            count=20,
            interval_seconds=3600
        )
        
        success = storage_b.append_klines('TESTUSDT', '1h', gap_data)
        results['sub_tests'].append({
            'name': 'b) 有缺口 append',
            'success': success,
            'expected': False,  # 應該失敗
            'note': '系統應偵測到 10 根 K線的缺口'
        })
        
        # 情境c: 重疊數據 append
        test2c_dir = self.test_dir / "case2c"
        test2c_dir.mkdir(exist_ok=True)
        storage_c = KlineStorageManager(cache_dir=str(test2c_dir))
        storage_c.write_klines('TESTUSDT', '1h', initial_data)
        
        # 重疊最後 5 根，然後新增 25 根
        overlap_start = initial_start + 45 * 3600  # 重疊最後 5 根
        overlap_data = self.generate_continuous_klines(
            start_timestamp=overlap_start,
            count=30,  # 5 根重疊 + 25 根新數據
            interval_seconds=3600
        )
        
        success = storage_c.append_klines('TESTUSDT', '1h', overlap_data)
        results['sub_tests'].append({
            'name': 'c) 重疊 append',
            'success': success,
            'expected': True,
            'note': '重疊部分應被去重'
        })
        
        # 驗證去重後的總數
        total_overlap = storage_c.read_klines('TESTUSDT', '1h', validate_continuity=True)
        results['sub_tests'].append({
            'name': 'c) 驗證去重總數 (應為 75)',
            'success': len(total_overlap) == 75 if total_overlap is not None else False,
            'expected': True,
            'actual': len(total_overlap) if total_overlap is not None else 0
        })
        
        results['overall_success'] = all(
            t['success'] == t['expected'] for t in results['sub_tests']
        )
        
        logger.info(f"測試情況2 結果: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        
        return results
    
    def test_case_3_warmup_continuity(self) -> dict:
        """
        測試情況3: Warmup 期的連續性
        
        驗證：
        - 從最早案例時間往前推 warmup 數量的數據必須連續
        - 使用 validate_range_continuity 檢查特定範圍
        - 確保技術指標計算有足夠的前置數據
        """
        logger.info("\n" + "="*60)
        logger.info("測試情況3: Warmup 期的連續性")
        logger.info("="*60)
        
        test3_dir = self.test_dir / "case3"
        test3_dir.mkdir(exist_ok=True)
        storage = KlineStorageManager(cache_dir=str(test3_dir))
        
        results = {
            'test_name': 'Warmup 期的連續性',
            'sub_tests': []
        }
        
        # 生成數據: 2022-01-01 開始的 500 根 1h K線
        data_start = int(datetime(2022, 1, 1, 0, 0).timestamp())
        full_data = self.generate_continuous_klines(
            start_timestamp=data_start,
            count=500,
            interval_seconds=3600
        )
        
        success = storage.write_klines('BTCUSDT', '1h', full_data)
        results['sub_tests'].append({
            'name': '寫入完整數據',
            'success': success,
            'expected': True
        })
        
        # 情境a: 案例在第 250 根，warmup = 100
        # 需要驗證 [150, 250] 範圍的連續性
        case_index = 250
        warmup = 100
        case_timestamp = data_start + case_index * 3600
        warmup_start = data_start + (case_index - warmup) * 3600
        
        is_continuous, error_msg = storage.validate_range_continuity(
            symbol='BTCUSDT',
            timeframe='1h',
            start_timestamp=warmup_start,
            end_timestamp=case_timestamp
        )
        
        results['sub_tests'].append({
            'name': 'a) 驗證 warmup 範圍 [150, 250]',
            'success': is_continuous,
            'expected': True,
            'error': error_msg
        })
        
        # 情境b: 案例在第 50 根，warmup = 100（不夠）
        # 需要驗證 [-50, 50] → 只有 [0, 50] 可用
        early_case_index = 50
        early_case_timestamp = data_start + early_case_index * 3600
        early_warmup_start = data_start - 50 * 3600  # 負數，不存在
        
        is_continuous_b, error_msg_b = storage.validate_range_continuity(
            symbol='BTCUSDT',
            timeframe='1h',
            start_timestamp=early_warmup_start,
            end_timestamp=early_case_timestamp
        )
        
        results['sub_tests'].append({
            'name': 'b) warmup 不足（案例太早）',
            'success': is_continuous_b,
            'expected': False,  # 應該失敗
            'error': error_msg_b,
            'note': 'warmup 期超出數據範圍'
        })
        
        # 情境c: 使用 read_klines_around_timestamp 讀取案例+warmup
        # 案例在第 300 根，lookback=200（warmup）
        case_ts_c = data_start + 300 * 3600
        
        klines_with_warmup = storage.read_klines_around_timestamp(
            symbol='BTCUSDT',
            timeframe='1h',
            center_timestamp=case_ts_c,
            lookback=200,
            forward=50
        )
        
        expected_count = 200 + 1 + 50  # warmup + 案例 + forward
        results['sub_tests'].append({
            'name': 'c) read_klines_around_timestamp (lookback=200)',
            'success': klines_with_warmup is not None and len(klines_with_warmup) == expected_count,
            'expected': True,
            'actual': len(klines_with_warmup) if klines_with_warmup is not None else 0,
            'expected_count': expected_count
        })
        
        # 情境d: 測試有缺口的情況（重新建立）
        test3d_dir = self.test_dir / "case3d"
        test3d_dir.mkdir(exist_ok=True)
        storage_d = KlineStorageManager(cache_dir=str(test3d_dir))
        
        # 製造缺口: 第 180-190 根 K線缺失
        gap_data = pd.concat([
            full_data.iloc[:180],
            full_data.iloc[190:]
        ]).reset_index(drop=True)
        
        storage_d.write_klines('BTCUSDT', '1h', gap_data)  # 注意: 這會失敗
        
        # 嘗試驗證包含缺口的範圍 [150, 250]
        # 這個範圍包含了 [180, 190] 的缺口
        gap_case_ts = data_start + 250 * 3600
        gap_warmup_start = data_start + 150 * 3600
        
        # 由於 write 可能已失敗，這裡用 try-except
        try:
            is_continuous_d, error_msg_d = storage_d.validate_range_continuity(
                symbol='BTCUSDT',
                timeframe='1h',
                start_timestamp=gap_warmup_start,
                end_timestamp=gap_case_ts
            )
            results['sub_tests'].append({
                'name': 'd) warmup 範圍內有缺口',
                'success': is_continuous_d,
                'expected': False,
                'error': error_msg_d,
                'note': '缺口在 [180, 190]'
            })
        except Exception as e:
            results['sub_tests'].append({
                'name': 'd) warmup 範圍內有缺口',
                'success': False,
                'expected': False,
                'error': str(e),
                'note': '寫入階段已偵測到缺口'
            })
        
        results['overall_success'] = all(
            t['success'] == t['expected'] for t in results['sub_tests']
        )
        
        logger.info(f"測試情況3 結果: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        
        return results
    
    def run_all_tests(self) -> dict:
        """執行所有測試"""
        logger.info("\n" + "="*80)
        logger.info("開始執行數據連續性邊界情況測試")
        logger.info("="*80)
        
        all_results = {
            'test_suite': '數據連續性邊界情況測試',
            'timestamp': datetime.now().isoformat(),
            'results': []
        }
        
        try:
            # 測試情況1
            result1 = self.test_case_1_different_symbols_timeframes()
            all_results['results'].append(result1)
            
            # 測試情況2
            result2 = self.test_case_2_append_new_timerange()
            all_results['results'].append(result2)
            
            # 測試情況3
            result3 = self.test_case_3_warmup_continuity()
            all_results['results'].append(result3)
            
            # 總結
            all_pass = all(r['overall_success'] for r in all_results['results'])
            all_results['all_tests_passed'] = all_pass
            
            logger.info("\n" + "="*80)
            logger.info("測試總結")
            logger.info("="*80)
            
            for result in all_results['results']:
                status = "✅ PASS" if result['overall_success'] else "❌ FAIL"
                logger.info(f"{result['test_name']}: {status}")
                
                for sub_test in result['sub_tests']:
                    sub_status = "✅" if sub_test['success'] == sub_test['expected'] else "❌"
                    logger.info(f"  {sub_status} {sub_test['name']}")
                    if 'note' in sub_test:
                        logger.info(f"     註: {sub_test['note']}")
                    if 'error' in sub_test and sub_test['error']:
                        logger.info(f"     錯誤: {sub_test['error'][:100]}")
            
            logger.info("="*80)
            logger.info(f"整體結果: {'✅ 所有測試通過' if all_pass else '❌ 部分測試失敗'}")
            logger.info("="*80)
            
        finally:
            self.cleanup()
        
        return all_results


def main():
    """主函式"""
    tester = ContinuityEdgeCaseTester()
    results = tester.run_all_tests()
    
    # 儲存結果
    import json
    output_path = Path("test_results/continuity_edge_cases.json")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n測試結果已儲存: {output_path}")
    
    # 返回退出碼
    return 0 if results['all_tests_passed'] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
