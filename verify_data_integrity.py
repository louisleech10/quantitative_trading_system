"""
數據完整性驗證腳本

檢查 HDF5 數據檔案的連續性，並生成詳細報告
"""

import pandas as pd
import h5py
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class DataIntegrityChecker:
    """數據完整性檢查器"""
    
    def __init__(self, data_cache_path: Path = None):
        self.data_cache_path = data_cache_path or Path(__file__).parent / "data_cache"
        
    def check_file_continuity(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Dict:
        """
        檢查單一檔案的數據連續性
        
        Returns:
            {
                'symbol': str,
                'timeframe': str,
                'total_rows': int,
                'time_range': (start, end),
                'expected_rows': int,
                'missing_rows': int,
                'gaps': List[Dict],  # 缺口詳情
                'is_continuous': bool
            }
        """
        file_path = self.data_cache_path / f"{symbol}_{timeframe}.h5"
        
        if not file_path.exists():
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'error': 'File not found',
                'file_path': str(file_path)
            }
        
        try:
            # 讀取數據（這些檔案使用 pandas HDFStore 格式）
            df = pd.read_hdf(file_path, key='data')
            
            if df.empty:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'error': 'Empty dataframe'
                }
            
            #確保索引是 datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                # 嘗試轉換
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception as e:
                    return {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'error': f'Cannot convert index to datetime: {str(e)}',
                        'index_type': str(type(df.index))
                    }
            
            # 轉換索引為每秒時間戳（用於計算）
            df = df.sort_index()
            timestamps = df.index.astype('int64') // 10**9  # 轉換為秒級時間戳
            
            # 計算時間間隔（秒）
            interval_seconds = self._timeframe_to_seconds(timeframe)
            
            # 檢查連續性
            start_time = df.index[0]
            end_time = df.index[-1]
            total_rows = len(df)
            
            # 預期的 K 線數量
            time_diff_seconds = int((end_time - start_time).total_seconds())
            expected_rows = time_diff_seconds // interval_seconds + 1
            missing_rows = expected_rows - total_rows
            
            # 找出所有缺口
            gaps = []
            for i in range(len(timestamps) - 1):
                current_ts = timestamps[i]
                next_ts = timestamps[i + 1]
                expected_next_ts = current_ts + interval_seconds
                
                if next_ts != expected_next_ts:
                    gap_seconds = next_ts - expected_next_ts
                    missing_count = gap_seconds // interval_seconds
                    
                    gaps.append({
                        'position': i,
                        'gap_start': df.index[i].isoformat(),
                        'gap_end': df.index[i + 1].isoformat(),
                        'missing_count': int(missing_count),
                        'duration_hours': gap_seconds / 3600
                    })
            
            is_continuous = len(gaps) == 0
            
            result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'file_path': str(file_path),
                'total_rows': total_rows,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'expected_rows': expected_rows,
                'missing_rows': missing_rows,
                'missing_percentage': (missing_rows / expected_rows * 100) if expected_rows > 0 else 0,
                'gaps_count': len(gaps),
                'gaps': gaps,
                'is_continuous': is_continuous
            }
            
            if not is_continuous:
                logger.warning(
                    f"{symbol}/{timeframe}: 發現 {len(gaps)} 處缺口，"
                    f"缺少 {missing_rows} 根K線 ({result['missing_percentage']:.2f}%)"
                )
            else:
                logger.info(f"{symbol}/{timeframe}: ✅ 數據連續")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check {symbol}/{timeframe}: {str(e)}", exc_info=True)
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'error': str(e)
            }
    
    def _timeframe_to_ms(self, timeframe: str) -> int:
        """將時間框架轉換為毫秒"""
        return self._timeframe_to_seconds(timeframe) * 1000
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """將時間框架轉換為秒"""
        if timeframe.endswith('m'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60 * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 24 * 60 * 60
        else:
            raise ValueError(f"Unknown timeframe: {timeframe}")
    
    def batch_check(self, symbols: List[str], timeframe: str) -> Dict:
        """
        批量檢查多個幣種
        
        Returns:
            {
                'total_checked': int,
                'continuous_count': int,
                'discontinuous_count': int,
                'error_count': int,
                'details': List[Dict],
                'summary': Dict
            }
        """
        results = []
        continuous_count = 0
        discontinuous_count = 0
        error_count = 0
        
        logger.info(f"開始批量檢查 {len(symbols)} 個幣種的 {timeframe} 數據...")
        
        for symbol in symbols:
            result = self.check_file_continuity(symbol, timeframe)
            results.append(result)
            
            if 'error' in result:
                error_count += 1
            elif result.get('is_continuous'):
                continuous_count += 1
            else:
                discontinuous_count += 1
        
        # 生成摘要
        summary = {
            'total_checked': len(symbols),
            'continuous_count': continuous_count,
            'discontinuous_count': discontinuous_count,
            'error_count': error_count,
            'continuous_percentage': (continuous_count / len(symbols) * 100) if symbols else 0
        }
        
        # 找出最嚴重的問題
        worst_cases = sorted(
            [r for r in results if not r.get('error') and not r.get('is_continuous')],
            key=lambda x: x.get('missing_rows', 0),
            reverse=True
        )[:10]
        
        return {
            'summary': summary,
            'worst_cases': worst_cases,
            'details': results
        }
    
    def generate_report(self, batch_result: Dict, output_path: Path = None):
        """生成可讀的報告"""
        output_path = output_path or Path("data_integrity_report.md")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 數據完整性檢查報告\n\n")
            f.write(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 摘要
            summary = batch_result['summary']
            f.write("## 📊 摘要統計\n\n")
            f.write(f"- **總檢查數**: {summary['total_checked']}\n")
            f.write(f"- **✅ 連續數據**: {summary['continuous_count']} ({summary['continuous_percentage']:.1f}%)\n")
            f.write(f"- **⚠️ 不連續數據**: {summary['discontinuous_count']}\n")
            f.write(f"- **❌ 錯誤**: {summary['error_count']}\n\n")
            
            # 最嚴重問題
            f.write("## 🚨 最嚴重的數據缺口（Top 10）\n\n")
            for i, case in enumerate(batch_result['worst_cases'], 1):
                f.write(f"### {i}. {case['symbol']}/{case['timeframe']}\n\n")
                f.write(f"- **總行數**: {case['total_rows']:,}\n")
                f.write(f"- **預期行數**: {case['expected_rows']:,}\n")
                f.write(f"- **缺少行數**: {case['missing_rows']:,} ({case['missing_percentage']:.2f}%)\n")
                f.write(f"- **缺口數量**: {case['gaps_count']}\n")
                f.write(f"- **時間範圍**: {case['time_range']['start']} ~ {case['time_range']['end']}\n\n")
                
                if case['gaps']:
                    f.write("**缺口詳情**:\n\n")
                    for gap in case['gaps'][:5]:  # 只顯示前 5 個
                        f.write(f"- 位置 {gap['position']}: {gap['gap_start']} ~ {gap['gap_end']} "
                               f"(缺少 {gap['missing_count']} 根, {gap['duration_hours']:.1f} 小時)\n")
                    if len(case['gaps']) > 5:
                        f.write(f"- ... 還有 {len(case['gaps']) - 5} 個缺口\n")
                    f.write("\n")
            
            # 詳細列表
            f.write("## 📋 完整檢查結果\n\n")
            f.write("| 幣種 | 時間框架 | 狀態 | 總行數 | 缺口數 | 缺少行數 | 缺失% |\n")
            f.write("|------|---------|------|--------|--------|----------|-------|\n")
            
            for result in batch_result['details']:
                if 'error' in result:
                    status = f"❌ {result['error'][:20]}"
                    f.write(f"| {result['symbol']} | {result['timeframe']} | {status} | - | - | - | - |\n")
                elif result['is_continuous']:
                    f.write(f"| {result['symbol']} | {result['timeframe']} | ✅ 連續 | "
                           f"{result['total_rows']:,} | 0 | 0 | 0% |\n")
                else:
                    f.write(f"| {result['symbol']} | {result['timeframe']} | ⚠️ 不連續 | "
                           f"{result['total_rows']:,} | {result['gaps_count']} | "
                           f"{result['missing_rows']:,} | {result['missing_percentage']:.2f}% |\n")
        
        logger.info(f"報告已生成: {output_path}")
        return output_path


def main():
    """主函式"""
    import sys
    
    # 解析命令列參數
    timeframe = "12h"  # 預設檢查生產環境的 12h 數據
    if len(sys.argv) > 1:
        timeframe = sys.argv[1]
    
    # 初始化檢查器
    checker = DataIntegrityChecker()
    
    # 從 data_cache 獲取所有幣種
    data_cache_path = Path(__file__).parent / "data_cache"
    h5_files = list(data_cache_path.glob(f"*_{timeframe}.h5"))
    
    if len(h5_files) == 0:
        logger.error(f"未找到任何 {timeframe} 數據檔案在 {data_cache_path}")
        print(f"❌ 錯誤: 未找到任何 {timeframe} 數據檔案")
        print(f"   路徑: {data_cache_path}")
        print(f"   請確認數據已下載")
        return 1
    
    # 提取幣種
    symbols = [f.stem.replace(f"_{timeframe}", "") for f in h5_files]
    
    logger.info(f"找到 {len(symbols)} 個 {timeframe} 數據檔案")
    
    # 批量檢查
    result = checker.batch_check(symbols, timeframe)
    
    # 生成報告
    report_path = Path("test_results") / f"data_integrity_report_{timeframe}.md"
    report_path.parent.mkdir(exist_ok=True)
    checker.generate_report(result, report_path)
    
    # 同時生成 JSON（供程式讀取）
    json_path = Path("test_results") / f"data_integrity_report_{timeframe}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"JSON 報告已生成: {json_path}")
    
    # 打印關鍵訊息
    summary = result['summary']
    print("\n" + "="*60)
    print(f"數據完整性檢查完成 ({timeframe})")
    print("="*60)
    print(f"✅ 連續數據: {summary['continuous_count']}/{summary['total_checked']} ({summary['continuous_percentage']:.1f}%)")
    print(f"⚠️ 不連續數據: {summary['discontinuous_count']}")
    print(f"❌ 錯誤: {summary['error_count']}")
    print(f"\n📄 詳細報告: {report_path}")
    print(f"📄 JSON 報告: {json_path}")
    print("="*60 + "\n")
    
    # 如果有嚴重問題，返回非零退出碼
    if summary['discontinuous_count'] > 0:
        print("⚠️ 警告: 發現數據不連續問題")
        print("\n建議處理方式：")
        print("1. 檢視詳細報告確認缺口位置")
        print("2. 使用 fill_data_gaps.py 修復缺口（重新下載）")
        print("3. 或在 ML 訓練時使用 validate_continuity=False（風險較高）")
        print("\n⚠️ 強烈建議修復後再進行 ML 訓練！")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
