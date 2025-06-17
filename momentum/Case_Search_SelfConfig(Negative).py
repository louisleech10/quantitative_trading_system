import sys
import os
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from momentum.DataExtraction.Momentum_Strategy_Data_Loader import MomentumDataLoader
from momentum.signal_analyzer import SignalAnalyzer
from momentum.Indicator.Advanced_MA import AdvancedMA, MAParams
# 引入搜索配置和篩選條件類
from momentum.DataExtraction.case_search_engine import SearchConfiguration, FilterCondition
import logging
from datetime import datetime
import asyncio
from pathlib import Path

# 設置日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # 創建結果目錄
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        # 初始化加載器
        scanner = MomentumDataLoader()
        
        # 生成時間戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = results_dir / f'momentum_signals_{timestamp}.h5'
        csv_file = results_dir / f'momentum_signals_{timestamp}.csv'

        logger.info("開始掃描市場動能信號...")
        
        # 設置搜索參數
        start_date = '2022-03-01'
        end_date = '2022-04-30'
        timeframe = '12h'
        batch_size = 200  # 每批處理的交易對數量
        
        # 創建自定義搜索配置
        config = SearchConfiguration(
            name="Custom Momentum Strategy",
            description="自定義動能策略搜索條件",
            timeframe=timeframe,  # 使用之前定義的時間週期
            lookback_periods=100,  # 回溯100根K線
            forward_periods=6,     # 向前看6根K線（對於12h時間週期，相當於3天）
            time_range=(start_date, end_date),  # 使用之前定義的時間範圍
            sample_limit=1000,     # 最多獲取1000個案例
            min_volume=500000,     # 最小成交量要求（USDT）
            exclude_new_listing_days=7  # 排除新上市後7天的數據
        )
        
        # 添加初始篩選條件
        
        # 創建負例搜索配置
        negative_config = SearchConfiguration(
            name="Negative Cases",
            description="搜索不會上漲的案例",
            timeframe=timeframe,
            lookback_periods=100,
            forward_periods=6,
            time_range=(start_date, end_date),
            sample_limit=1000
        )

        # 添加條件：價格變化小
        negative_config.add_initial_condition(
            FilterCondition(
                condition_type="price",
                parameter="price_change",
                operator="between",
                value=(-0.02, 0.02),  # 價格變化在 -2% 到 2% 之間
                description="K線漲跌幅在 -2% 到 2% 之間"
            )
        )

        # 添加條件：未來價格變化小
        negative_config.add_advanced_condition(
            FilterCondition(
                condition_type="price",
                parameter="future24_close_return",
                operator="between",
                value=(-0.03, 0.03),  # 未來24小時價格變化在 -3% 到 3% 之間
                description="未來24小時價格變化在 -3% 到 3% 之間"
            )
        )
        
        # 執行自定義配置搜索
        logger.info(f"使用自定義配置搜索動能信號...")
        signals = await scanner.search_engine.search_cases(
            config=config,
            batch_size=batch_size,
            save_results=True
        )
        
        # 轉換搜索結果為動能信號格式
        if signals:
            logger.info(f"找到 {len(signals)} 個潛在案例，轉換為動能信號格式...")
            signals = scanner._convert_to_momentum_signals(signals, timeframe)
        
        # 原來的代碼保持不變
        if signals:
            # 保存結果
            scanner.save_results(signals, str(output_file))
            logger.info(f"找到 {len(signals)} 個動能信號")

            # 保存為CSV格式
            signals_df = pd.DataFrame(signals)
            signals_df.to_csv(csv_file, index=False)
            logger.info(f"信號數據已保存至CSV: {csv_file}")
            
            # 分析信號
            report_file = results_dir / f'momentum_analysis_{timestamp}.txt'
            
            # 創建指標實例進行分析
            indicator = AdvancedMA(MAParams())
            
            # 生成分析報告
            generate_analysis_report(signals, {}, str(report_file))
            
            # 打印摘要
            print("\n=== 基本統計 ===")
            print(f"掃描幣種數: {len(set(signal['symbol'] for signal in signals))}")
            print(f"信號總數: {len(signals)}")
            print(f"\n詳細報告已保存至: {report_file}")
            
            # 信號類型分布
            signal_types = {}
            for signal in signals:
                signal_type = signal.get('signal_type', 'unknown')
                signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
                
            print("\n信號類型分布:")
            for signal_type, count in signal_types.items():
                percentage = (count / len(signals)) * 100
                print(f"  {signal_type}: {count} ({percentage:.1f}%)")
            
        else:
            logger.warning("未找到符合條件的信號")
            
    except Exception as e:
        logger.error(f"執行過程中發生錯誤: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# 這個函數需要添加到文件中
def generate_analysis_report(signals, analysis_results, report_file):
    """生成分析報告"""
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== 動能信號分析報告 ===\n")
            f.write(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 基本統計
            f.write("=== 基本統計 ===\n")
            f.write(f"總信號數: {len(signals)}\n")
            f.write(f"幣種數: {len(set(signal['symbol'] for signal in signals))}\n\n")
            
            # 市場階段分布
            market_phases = {}
            for signal in signals:
                phase = signal.get('market_phase', 'UNKNOWN')
                market_phases[phase] = market_phases.get(phase, 0) + 1
            
            f.write("市場階段分布:\n")
            for phase, count in sorted(market_phases.items()):
                percentage = (count / len(signals)) * 100
                f.write(f"  {phase}: {count} ({percentage:.1f}%)\n")
            f.write("\n")
            
            # 信號類型分布
            signal_types = {}
            for signal in signals:
                signal_type = signal.get('signal_type', 'unknown')
                signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
            
            f.write("信號類型分布:\n")
            for signal_type, count in sorted(signal_types.items()):
                percentage = (count / len(signals)) * 100
                f.write(f"  {signal_type}: {count} ({percentage:.1f}%)\n")
            f.write("\n")
            
            # 處理分析結果
            if analysis_results:
                # 分析摘要
                if 'analysis_summary' in analysis_results:
                    summary = analysis_results['analysis_summary']
                    f.write("=== 分析摘要 ===\n")
                    f.write(f"總案例數: {summary.get('total_cases', 0)}\n")
                    f.write(f"有信號案例數: {summary.get('cases_with_signals', 0)}\n")
                    
                    if 'total_cases' in summary and summary['total_cases'] > 0:
                        detection_rate = (summary.get('cases_with_signals', 0) / summary['total_cases']) * 100
                        f.write(f"信號檢出率: {detection_rate:.1f}%\n")
                    f.write("\n")
                
                # 信號分布分析
                if 'distribution_analysis' in analysis_results:
                    f.write("=== 信號分布分析 ===\n")
                    dist_analysis = analysis_results['distribution_analysis']
                    
                    for signal_name, stats in sorted(dist_analysis.items()):
                        f.write(f"{signal_name}:\n")
                        f.write(f"  出現次數: {stats.get('count', 0)}\n")
                        f.write(f"  平均位置: K{stats.get('mean_position', 0):.1f}\n")
                        f.write(f"  標準差: {stats.get('std_position', 0):.2f}\n")
                        
                        # 添加集中度信息
                        if 'most_common_range' in stats:
                            range_info = stats['most_common_range']
                            if 'range' in range_info:
                                start, end = range_info['range']
                                f.write(f"  最集中區間: K{start}-K{end}")
                                if 'percentage' in range_info:
                                    f.write(f" ({range_info['percentage']:.1f}%)\n")
                                else:
                                    f.write("\n")
                        
                        f.write(f"  4天內信號比例: {stats.get('four_days_ratio', 0):.1f}%\n")
                        f.write(f"  信號聚集: {'是' if stats.get('is_clustered', False) else '否'}\n")
                        f.write("\n")
                
                # 整合其他分析結果
                if 'indicator_stats' in analysis_results:
                    f.write("=== 指標統計 ===\n")
                    indicator_stats = analysis_results['indicator_stats']
                    
                    # 信號組合分析
                    if 'combinations' in indicator_stats and indicator_stats['combinations']:
                        f.write("常見信號組合:\n")
                        sorted_combos = sorted(indicator_stats['combinations'].items(), 
                                             key=lambda x: x[1], reverse=True)
                        for combo, count in sorted_combos[:10]:  # 顯示前10個組合
                            combo_str = '+'.join(combo)
                            f.write(f"  {combo_str}: {count}次\n")
                        f.write("\n")
            
            # 添加案例分布統計
            symbols_count = {}
            for signal in signals:
                symbol = signal['symbol']
                symbols_count[symbol] = symbols_count.get(symbol, 0) + 1
            
            f.write("=== 幣種分布 (前20名) ===\n")
            sorted_symbols = sorted(symbols_count.items(), key=lambda x: x[1], reverse=True)
            for symbol, count in sorted_symbols[:20]:
                percentage = (count / len(signals)) * 100
                f.write(f"  {symbol}: {count} ({percentage:.1f}%)\n")
                
        logger.info(f"分析報告已保存至: {report_file}")
            
    except Exception as e:
        logger.error(f"生成分析報告時出錯: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())