import gc
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import h5py
from pathlib import Path
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from momentum.Indicator.Advanced_MA import AdvancedMA, MAParams
from momentum.Indicator.Base_Indicator import BaseIndicator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignalAnalyzer:
    """通用信號分析器"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.logger = logging.getLogger(__name__)
        # 添加有效K線指標配置參數，設置默認值
        self.density_config = {
            'overall_density_min': 0.2,  # 整體密度最小值 20%
            'overall_density_max': 0.4,  # 整體密度最大值 40%
            'key_area_density_min': 0.1  # 關鍵區密度最小值 50%
        }

    def _print_h5_structure(self, h5file: h5py.File) -> None:
        """打印H5文件結構"""
        def print_group(name: str, obj: Any) -> None:
            self.logger.info(f"找到: {name}, 類型: {type(obj).__name__}")
            if isinstance(obj, h5py.Dataset):
                self.logger.info(f"  形狀: {obj.shape}")
                self.logger.info(f"  數據類型: {obj.dtype}")
        
        h5file.visititems(print_group)

    def _read_and_validate_data(self, group, case_key: str) -> pd.DataFrame:
        """讀取並驗證HDF5數據"""
        try:
            # 檢查是否為Dataset而不是Group
            if isinstance(group, h5py.Dataset):
                self.logger.info(f"檢測到Dataset，嘗試直接讀取")
                # 嘗試直接讀取為pandas DataFrame
                df = pd.read_hdf(self.data_file, key=group.name)
                return df
            
            # 原始的Group處理邏輯
            # 讀取數據
            case_data = {}
            raw_timestamps = None
            
            # 首先讀取所有數據
            for column in group.keys():
                data = group[column][:]
                
                if column == 'timestamp':
                    raw_timestamps = data
                elif column in ['open', 'high', 'low', 'close', 'volume',
                            'quote_asset_volume', 'number_of_trades',
                            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']:
                    if data.dtype == object:
                        data = np.array([float(x) if isinstance(x, bytes) else x for x in data])
                    case_data[column] = data
            
            # 驗證時間戳是否存在
            if raw_timestamps is None:
                raise ValueError("無法在HDF5文件中找到時間戳數據")
                
            # 轉換時間戳
            try:
                timestamps = pd.to_datetime(raw_timestamps, unit='s')
            except Exception as e:
                self.logger.error(f"時間戳轉換錯誤: {str(e)}")
                self.logger.info("嘗試其他時間單位轉換...")
                try:
                    # 嘗試毫秒轉換
                    timestamps = pd.to_datetime(raw_timestamps, unit='ms')
                    self.logger.info(f"使用毫秒轉換的時間戳 (first 5): {timestamps[:5]}")
                except Exception as e2:
                    self.logger.error(f"毫秒轉換也失敗: {str(e2)}")
                    raise
            
            # 創建DataFrame
            df = pd.DataFrame(case_data, index=timestamps)
            
            # 驗證數據完整性
            required_columns = {'open', 'high', 'low', 'close', 'volume'}
            missing_columns = required_columns - set(df.columns)
            if missing_columns:
                raise ValueError(f"數據缺少必要列: {missing_columns}")
                
            # 驗證數據類型
            for col in required_columns:
                if not np.issubdtype(df[col].dtype, np.number):
                    raise ValueError(f"列 {col} 必須是數值型")
            
            # 驗證數據合理性
            if df['high'].min() < df['low'].min():
                raise ValueError("最高價不能低於最低價")
            if (df['volume'] < 0).any():
                raise ValueError("成交量不能為負")
            
            # 輸出基本統計信息
            self.logger.info(f"數據範圍: {df.index[0]} 到 {df.index[-1]}")
            self.logger.info(f"數據點數: {len(df)}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"讀取與驗證數據時出錯: {str(e)}")
            self.logger.exception("完整錯誤追蹤:")
            raise

    def analyze_cases(self, indicator) -> Dict[str, Any]:
        """分析所有案例的信號分布"""
        try:
            signal_locations = {
                signal_name: [] for signal_name in indicator.get_signal_names()
            }
            
            indicator_stats = {
                'signals': {},
                'patterns': {},
                'correlations': {},
                'timing': {},
                'combinations': {}
            }
            
            analysis_summary = {
                'total_cases': 0,
                'cases_with_signals': 0,
                'signal_counts': {},
                'time_ranges': {},
                'data_statistics': {},
                'valid_cases': {}  # 新增: 記錄有效案例數
            }

            raw_data = {}
            indicator_results = {}
            case_signals = {}

            self.logger.info("開始分析案例...")
            
            with h5py.File(self.data_file, 'r') as f:
                for symbol in f.keys():
                    for timestamp in f[symbol].keys():
                        case_key = f"{symbol}_{timestamp}"
                        self.logger.info(f"\n處理案例: {case_key}")
                        analysis_summary['total_cases'] += 1
                        
                        try:
                            # 讀取數據
                            df = self._read_and_validate_data(f[symbol][timestamp], case_key)
                            if df.empty:
                                self.logger.warning(f"案例 {case_key} 數據為空，跳過")
                                continue
                                
                            # 計算指標
                            self.logger.info(f"計算 {case_key} 的指標...")
                            #indicator_values = indicator.calculate(df)
                            indicator_values = indicator.safe_calculate(df)
                            
                            # 分析模式和信號
                            self.logger.info(f"分析 {case_key} 的模式...")
                            patterns = indicator.analyze_pattern(df, indicator_values)
                            #self.logger.info(f"Pattern result for {case_key}: {patterns}") #Debug using
                            
                            # 保存信號
                            if patterns.get('signals'):
                                #self.logger.info(f"Found signals for {case_key}: {patterns['signals']}") #Debug Using
                                case_signals[case_key] = patterns['signals']
                                #self.logger.info(f"Current case_signals size: {len(case_signals)}")#Debug Using
                                analysis_summary['cases_with_signals'] += 1
                                
                                # 新增: 計算每個信號的密度 20250115新增
                                case_densities = {}
                                for signal_name in indicator.get_signal_names():
                                    density_info = self._calculate_case_density(
                                        df, patterns['signals'], indicator, signal_name)
                                    case_densities[signal_name] = density_info
                                    
                                    # 判斷是否為有效案例
                                    if self._is_valid_case(density_info):
                                        analysis_summary['valid_cases'].setdefault(
                                            signal_name, 0)
                                        analysis_summary['valid_cases'][signal_name] += 1
                                #20250115新增

                                self._update_signal_stats(patterns['signals'], 
                                                        signal_locations, 
                                                        indicator_stats, 
                                                        analysis_summary,
                                                        case_densities  # 20250115新增密度信息
                                                        )
                            else:
                                self.logger.info(f"No signals found for {case_key}")
                            
                            # 保存原始數據
                            raw_data[case_key] = {
                                'open': df['open'].tolist(),
                                'high': df['high'].tolist(),
                                'low': df['low'].tolist(),
                                'close': df['close'].tolist(),
                                'volume': df['volume'].tolist()
                            }
                            if 'taker_buy_base_asset_volume' in df.columns:
                                raw_data[case_key]['taker_buy_base_asset_volume'] = \
                                    df['taker_buy_base_asset_volume'].tolist()
                            
                            # 保存指標結果
                            indicator_results[case_key] = {
                                k: v.tolist() if isinstance(v, (pd.Series, np.ndarray)) else v 
                                for k, v in indicator_values.items()
                            }
                            
                            # 保存時間範圍和統計數據
                            analysis_summary['time_ranges'][case_key] = self._get_time_range(df)
                            analysis_summary['data_statistics'][case_key] = self._calculate_data_statistics(df)
                                
                        except Exception as e:
                            self.logger.error(f"處理案例 {case_key} 時出錯: {str(e)}")
                            self.logger.exception("完整錯誤追蹤:")
                            continue

                # 記錄總結資訊
                self.logger.info(f"\n分析完成:")
                self.logger.info(f"總案例數: {analysis_summary['total_cases']}")
                self.logger.info(f"有信號案例數: {analysis_summary['cases_with_signals']}")
                self.logger.info(f"找到的信號總數: {len(signal_locations)}")

                case_counts = {}
                for signal_name in indicator.get_signal_names():
                    case_count = sum(
                        1 for case_data in case_signals.values()
                        if any(
                            signal_name in str(k_line_info['signals'])
                            for k_line_info in case_data.values()
                        )
                    )
                    case_counts[signal_name] = case_count
                    #self.logger.info(f"信號 {signal_name} 在 {case_count} 個案例中出現") #Debug Using

                # 修改 return 語句，將 case_counts 加入到 analysis_summary 中
                analysis_summary['case_counts'] = case_counts
                
                return {
                    'raw_data': raw_data,
                    'indicator_results': indicator_results,
                    'signal_locations': signal_locations,
                    'case_signals': case_signals,
                    'distribution_analysis': self._analyze_signal_distribution(signal_locations),
                    'analysis_summary': analysis_summary,
                    'indicator_stats': indicator_stats
                }
                
        except Exception as e:
            self.logger.error(f"分析過程發生錯誤: {str(e)}")
            self.logger.exception("完整錯誤追蹤:")
            raise

        finally:
            # 清理內存
            gc.collect()

    def _get_time_range(self, df: pd.DataFrame) -> Dict:
        """獲取數據時間範圍信息"""
        return {
            'start': df.index[0].strftime('%Y-%m-%d %H:%M:%S'),
            'end': df.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            'total_periods': len(df)
        }

    def _calculate_data_statistics(self, df: pd.DataFrame) -> Dict:
        """計算數據統計信息"""
        try:
            return {
                'price_range': {
                    'min': float(df['low'].min()),
                    'max': float(df['high'].max()),
                    'avg': float(df['close'].mean())
                },
                'volume_stats': {
                    'avg': float(df['volume'].mean()),
                    'median': float(df['volume'].median()),
                    'std': float(df['volume'].std())
                },
                'taker_ratio_stats': {
                    'avg': float(df['taker_ratio'].mean()),
                    'median': float(df['taker_ratio'].median()),
                    'std': float(df['taker_ratio'].std())
                }
            }
        except Exception as e:
            self.logger.error(f"計算統計數據時出錯: {str(e)}")
            # 返回空的統計結構
            return {
                'price_range': {'min': 0, 'max': 0, 'avg': 0},
                'volume_stats': {'avg': 0, 'median': 0, 'std': 0},
                'taker_ratio_stats': {'avg': 0, 'median': 0, 'std': 0}
            }

    def _analyze_signal_distribution(self, locations: Dict[str, List[int]]) -> Dict:
        """分析信號分布特徵"""
        analysis = {}
        
        for signal_name, positions in locations.items():
            if not positions:
                continue

            #self.logger.info(f"分析信號 {signal_name}, 位置數量: {len(positions)}") #Debug Using

            positions_array = np.array(positions)
        

            # 計算4天內的信號數量(K76到K99)
            four_days_signals = len([p for p in positions if 76 <= p <= 99])
            four_days_ratio = (four_days_signals / len(positions) * 100) if positions else 0

                
            analysis[signal_name] = {
                'count': len(positions),
                'mean_position': float(np.mean(positions)),
                'std_position': float(np.std(positions)) if len(positions) > 1 else 0,
                'most_common_range': self._find_most_common_range(positions),
                'is_clustered': self._check_clustering(positions),
                'four_days_ratio': four_days_ratio,
                'positions': positions  # 20250113添加這行，保存原始位置數據
            }

        return analysis

    def _find_most_common_range(self, positions: List[int], window: int = 5) -> Dict:
        """找出信號最集中的區間"""
        if not positions:
            return {}
            
        max_count = 0
        best_range = None
        total_length = max(positions) + 1
        
        for start in range(1, total_length - window + 1):
            end = start + window
            count = sum(1 for x in positions if start <= x < end)
            
            if count > max_count:
                max_count = count
                best_range = (start, end-1)
                
        return {
            'range': best_range,
            'count': int(max_count),
            'percentage': float(max_count / len(positions) * 100)
        }

    def _check_clustering(self, positions: List[int], threshold: float = 0.6) -> bool:
        """檢查信號是否集中分布"""
        if not positions:
            return False
        
        most_common = self._find_most_common_range(positions)
        return most_common['percentage'] >= threshold * 100

    def create_distribution_plots(self, 
                                signal_locations: Dict[str, List[int]], 
                                distribution_analysis: Dict) -> None:
        """創建分布視覺化圖表"""
        output_dir = Path('analysis_results')
        output_dir.mkdir(exist_ok=True)
        
        # 信號分布圖
        fig = make_subplots(rows=len(signal_locations), cols=1,
                           subplot_titles=list(signal_locations.keys()))
        
        for i, (signal_name, positions) in enumerate(signal_locations.items(), 1):
            if positions:
                max_position = max(positions)
                num_bins = min(50, max_position // 2)
                
                fig.add_trace(
                    go.Histogram(x=positions, nbinsx=num_bins,
                               name=signal_name),
                    row=i, col=1
                )
                
                if distribution_analysis.get(signal_name, {}).get('is_clustered'):
                    range_info = distribution_analysis[signal_name]['most_common_range']
                    start, end = range_info['range']
                    fig.add_vrect(
                        x0=start, x1=end,
                        fillcolor="red", opacity=0.3,
                        layer="below", line_width=0,
                        row=i, col=1
                    )
        
        fig.update_layout(height=200*len(signal_locations),
                         showlegend=False)
        fig.write_html(output_dir / 'signal_distributions.html')
        
        # 時間分布圖
        fig_time = go.Figure()
        fig_time.write_html(output_dir / 'time_distribution.html')

    def _save_results(self, 
                     signal_locations: Dict,
                     distribution_analysis: Dict,
                     analysis_summary: Dict,
                     indicator_stats: Dict) -> None:
        """保存分析結果"""
        output_dir = Path('analysis_results')
        output_dir.mkdir(exist_ok=True)
        
        # 保存分布分析
        pd.DataFrame.from_dict(distribution_analysis, orient='index').to_csv(
            output_dir / 'distribution_analysis.csv'
        )
        
        # 保存性能分析
        pd.DataFrame.from_dict(
            analysis_summary['indicator_performance'],
            orient='index'
        ).to_csv(output_dir / 'performance_analysis.csv')
        
        # 保存總結報告
        with open(output_dir / 'analysis_summary.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_summary, f, ensure_ascii=False, indent=2)
        
        # 生成詳細報告
        self._generate_analysis_report(
            output_dir, 
            analysis_summary,
            distribution_analysis,
            indicator_stats
        )

    def _generate_analysis_report(self,
                                output_dir: Path,
                                analysis_summary: Dict,
                                distribution_analysis: Dict,
                                indicator_stats: Dict) -> None:
        """生成詳細分析報告"""
        report_lines = [
            "技術指標分析報告",
            "=" * 50,
            f"\n分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n基本統計:",
            f"總案例數: {analysis_summary['total_cases']}",
            f"有信號案例數: {analysis_summary['cases_with_signals']}",
            f"信號檢出率: {analysis_summary['cases_with_signals']/max(1, analysis_summary['total_cases'])*100:.2f}%",
        ]
        
        # 信號統計
        report_lines.append("\n信號統計:")
        for signal, stats in indicator_stats['signals'].items():
            report_lines.extend([
                f"\n{signal}:",
                f"出現次數: {stats['count']}次"
            ])
            if signal in distribution_analysis:
                dist_info = distribution_analysis[signal]
                report_lines.append(
                    f"最集中區間: K{dist_info['most_common_range']['range'][0]}-"
                    f"K{dist_info['most_common_range']['range'][1]}"
                )
                report_lines.append(
                    f"集中度: {dist_info['most_common_range']['percentage']:.2f}%"
                )
        
        # 信號組合分析
        if indicator_stats['combinations']:
            report_lines.append("\n信號組合分析:")
            sorted_combinations = sorted(
                indicator_stats['combinations'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for combo, count in sorted_combinations:
                report_lines.append(f"{combo}: {count}次")
        
        # 保存報告
        with open(output_dir / 'detailed_analysis_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

    def _update_signal_stats(self, 
                               signals: Dict, 
                               signal_locations: Dict,
                               indicator_stats: Dict,
                               analysis_summary: Dict,
                               case_densities: Dict = None):
        """更新信號統計信息"""
        for k_line_info in signals.values():
            k_line = k_line_info['k_line_number']
            current_signals = k_line_info['signals']
            #self.logger.info(f"更新信號統計: {len(current_signals)} 個信號") #Debug using
            
            # 更新信號位置和計數
            for signal in current_signals:
                # 更新信號位置
                if signal in signal_locations:
                    signal_locations[signal].append(k_line)
                    
                # 更新信號統計
                if signal not in indicator_stats['signals']:
                    indicator_stats['signals'][signal] = {
                        'count': 0,
                        'positions': [],
                        'timestamps': [],
                        'sequence_data': [],  # 新增：記錄信號出現的序列數據
                        'densities': []  # 新增: 收集密度信息
                    }
                    
                stats = indicator_stats['signals'][signal]
                stats['count'] += 1
                stats['positions'].append(k_line)
                stats['timestamps'].append(k_line_info['timestamp'])

                # 新增: 如果有密度信息，添加到統計中 #0115新增
                if case_densities and signal in case_densities:
                    stats['densities'].append({
                        'overall': case_densities[signal]['overall_density'],
                        'key_area': case_densities[signal]['key_area_density']
                    })
                #0115新增
                
                # 更新總計數
                analysis_summary['signal_counts'][signal] = \
                    analysis_summary['signal_counts'].get(signal, 0) + 1
            
            # 分析信號組合
            if len(current_signals) > 1:
                signal_combination = tuple(sorted(current_signals))
                indicator_stats['combinations'][signal_combination] = \
                    indicator_stats['combinations'].get(signal_combination, 0) + 1
                
            # 更新時序關係
            if len(current_signals) > 1:
                self._analyze_signal_timing(
                    current_signals,
                    k_line_info,
                    indicator_stats['timing']
                )

    def _analyze_signal_timing(self,
                             signals: List[str],
                             k_line_info: Dict,
                             timing_stats: Dict) -> None:
        """分析信號之間的時序關係"""
        for i, signal1 in enumerate(signals):
            for signal2 in signals[i+1:]:
                pair = (signal1, signal2)
                if pair not in timing_stats:
                    timing_stats[pair] = {
                        'count': 0,
                        'intervals': [],
                        'patterns': []
                    }
                    
                timing_stats[pair]['count'] += 1
                timing_stats[pair]['patterns'].append({
                    'timestamp': k_line_info['timestamp'],
                    'k_line': k_line_info['k_line_number']
                })

    def _analyze_indicator_performance(self, indicator_stats: Dict) -> Dict:
        """分析指標整體表現"""
        performance = {
            'signal_frequency': {},     # 信號出現頻率
            'signal_reliability': {},   # 信號可靠性
            'signal_combinations': {},  # 信號組合分析
            'timing_analysis': {},      # 時序分析
            'pattern_recognition': {}   # 形態識別結果
        }
        
        # 計算信號頻率
        total_signals = sum(
            stats['count'] for stats in indicator_stats['signals'].values()
        )
        
        for signal, stats in indicator_stats['signals'].items():
            frequency = stats['count'] / max(1, total_signals)
            performance['signal_frequency'][signal] = frequency
            
            # 分析信號序列特徵
            if stats['sequence_data']:
                performance['pattern_recognition'][signal] = \
                    self._analyze_signal_sequence(stats['sequence_data'])
        
        # 分析信號組合
        if indicator_stats['combinations']:
            total_combinations = sum(indicator_stats['combinations'].values())
            for combo, count in indicator_stats['combinations'].items():
                combo_str = '+'.join(combo)
                performance['signal_combinations'][combo_str] = \
                    count / max(1, total_combinations)
        
        # 分析時序關係
        if indicator_stats['timing']:
            performance['timing_analysis'] = \
                self._analyze_timing_patterns(indicator_stats['timing'])
        
        return performance

    def _analyze_signal_sequence(self, sequence_data: List) -> Dict:
        """分析信號序列特徵"""
        return {
            'avg_interval': np.mean([s['interval'] for s in sequence_data]),
            'std_interval': np.std([s['interval'] for s in sequence_data]),
            'pattern_types': self._identify_sequence_patterns(sequence_data)
        }

    def _analyze_timing_patterns(self, timing_stats: Dict) -> Dict:
        """分析時序模式"""
        patterns = {}
        for pair, stats in timing_stats.items():
            signal1, signal2 = pair
            patterns[f"{signal1}->{signal2}"] = {
                'frequency': stats['count'],
                'avg_interval': np.mean(stats['intervals']) \
                    if stats['intervals'] else 0,
                'reliability': self._calculate_pattern_reliability(stats)
            }
        return patterns

    def _calculate_pattern_reliability(self, stats: Dict) -> float:
        """計算模式可靠性"""
        if not stats['patterns']:
            return 0.0
            
        # 這裡可以根據具體需求實現可靠性計算邏輯
        # 當前返回一個基於出現次數的簡單度量
        return min(1.0, stats['count'] / 10.0)
    
    def set_density_thresholds(self, 
                         overall_min: float = 0.2,
                         overall_max: float = 0.4,
                         key_area_min: float = 0.5):
        """設置密度閾值"""
        self.density_config.update({
            'overall_density_min': overall_min,
            'overall_density_max': overall_max,
            'key_area_density_min': key_area_min
        })
    
    def _calculate_case_density(self, 
                          case_data: pd.DataFrame,
                          signals: Dict,
                          indicator,
                          signal_name: str) -> Dict[str, float]:
        """計算單一案例的信號密度
        
        Returns:
            Dict包含:
            - overall_density: 整體密度
            - key_area_density: 關鍵區域密度
        """
        self.logger.info(f"開始計算信號 {signal_name} 的密度")
        self.logger.info(f"indicator type: {type(indicator)}")
        # 獲取有效K線起始位置
        valid_start = indicator.get_signal_valid_range(signal_name)
        self.logger.info(f"get_signal_valid_range 返回值: {valid_start}")
    
        # 查看 _valid_starts 的內容
        if hasattr(indicator, '_valid_starts'):
            self.logger.info(f"_valid_starts 內容: {indicator._valid_starts}")

        self.logger.info(f"\n信號 {signal_name} 密度計算:")
        self.logger.info(f"有效起始K線: {valid_start}")
        
        # 計算實際可用的K線範圍
        total_k_lines = len(case_data) - valid_start
        self.logger.info(f"總有效K線數: {total_k_lines}")
        if total_k_lines <= 0:
            return {'overall_density': 0, 'key_area_density': 0}
            
        # 統計信號出現次數
        signal_positions = [
            k for k, v in signals.items()
            if signal_name in str(v.get('signals', []))
            and int(k) >= valid_start  # 只計算有效K線範圍內的信號
        ]
        
        # 計算整體密度
        total_signals = len(signal_positions)
        self.logger.info(f"信號總出現次數: {total_signals}")

        overall_density = total_signals / total_k_lines if total_k_lines > 0 else 0
        self.logger.info(f"整體密度: {overall_density:.2%}")
        
        # 計算關鍵區域密度 (K80-K99)
        key_area_start = max(80, valid_start)  # 確保不會在有效K線之前
        key_area_signals = len([
            p for p in signal_positions 
            if key_area_start <= int(p) <= 99
        ])

        key_area_length = len([
            i for i in range(80, 100)
            if i >= valid_start
        ])
        self.logger.info(f"關鍵區間K線數: {key_area_length}")
        self.logger.info(f"關鍵區間信號數: {key_area_signals}")

        key_area_density = (key_area_signals / key_area_length 
                        if key_area_length > 0 else 0)
        self.logger.info(f"關鍵區間密度: {key_area_density:.2%}\n")
        
        return {
            'overall_density': overall_density,
            'key_area_density': key_area_density
        }
    
    def _is_valid_case(self, density_info: Dict[str, float]) -> bool:
        """判斷是否為有效案例"""
        return (self.density_config['overall_density_min'] <= 
                density_info['overall_density'] <= 
                self.density_config['overall_density_max']
                and
                density_info['key_area_density'] >= 
                self.density_config['key_area_density_min'])