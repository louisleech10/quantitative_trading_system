import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import os
import logging
import json
from pathlib import Path

# 設置日誌
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FearGreedIndexCollector:
    """加密貨幣恐懼與貪婪指數數據採集器"""
    
    def __init__(self, output_dir="market_data"):
        """初始化採集器"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.market_data = None
        
        # 市場階段定義
        self.market_phases = {
            'EXTREME_FEAR': (0, 25),
            'FEAR': (26, 45),
            'NEUTRAL': (46, 55),
            'GREED': (56, 75),
            'EXTREME_GREED': (76, 100)
        }
        
    def fetch_fear_greed_index(self, limit=365):
        """
        抓取加密貨幣恐懼與貪婪指數
        
        Args:
            limit: 要獲取的數據點數量
            
        Returns:
            pd.DataFrame: 恐懼與貪婪指數數據
        """
        try:
            # Alternative.me API的新端點
            url = f"https://api.alternative.me/fng/?limit={limit}"
            
            # 請求數據
            logger.info(f"正在請求最近{limit}天的恐懼與貪婪指數數據")
            response = requests.get(url)
            
            if response.status_code != 200:
                logger.error(f"API請求失敗: {response.status_code} - {response.text}")
                return pd.DataFrame()
                
            # 解析數據
            data = response.json()
            if not data or 'data' not in data:
                logger.warning("API返回無效數據")
                logger.warning(f"回應內容: {data}")
                return pd.DataFrame()
            
            # 檢查API回應的結構
            if len(data['data']) > 0:
                logger.info(f"API回應的數據結構: {data['data'][0].keys()}")
            
            # 轉換為DataFrame
            records = []
            for item in data['data']:
                # 根據API返回的實際格式調整欄位
                record = {
                    'timestamp': int(item['timestamp']),
                    'value': int(item['value']),
                    'classification': item['value_classification'],
                }
                records.append(record)
                
            df = pd.DataFrame(records)
            
            # 添加日期列
            df['date'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.sort_values('date')  # 確保按日期排序
            df.set_index('date', inplace=True)
            
            # 添加周別數據
            df['week_start'] = df.index.to_period('W').start_time
            
            logger.info(f"成功獲取{len(df)}筆恐懼與貪婪指數數據")
            self.market_data = df
            return df
            
        except Exception as e:
            logger.error(f"抓取恐懼與貪婪指數數據時出錯: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def aggregate_to_weekly(self):
        """將數據聚合為週級別"""
        if self.market_data is None or self.market_data.empty:
            logger.error("沒有可用的數據進行聚合")
            return pd.DataFrame()
            
        # 按週聚合
        weekly_data = self.market_data.groupby('week_start').agg({
            'value': 'mean',  # 週平均值
        })
        
        # 四捨五入為整數
        weekly_data['value'] = weekly_data['value'].round().astype(int)
        
        # 添加分類
        weekly_data['market_phase'] = None
        for phase, (lower, upper) in self.market_phases.items():
            mask = (weekly_data['value'] >= lower) & (weekly_data['value'] <= upper)
            weekly_data.loc[mask, 'market_phase'] = phase
            
        logger.info(f"將{len(self.market_data)}筆數據聚合為{len(weekly_data)}筆週級別數據")
        return weekly_data
    
    def identify_market_phases(self, weekly_data=None):
        """識別連續的市場階段"""
        if weekly_data is None:
            if self.market_data is None or self.market_data.empty:
                logger.error("沒有可用的數據進行市場階段識別")
                return pd.DataFrame()
            weekly_data = self.aggregate_to_weekly()
            
        if weekly_data.empty:
            return pd.DataFrame()
        
        # 識別連續的市場階段
        phases_data = []
        
        current_phase = None
        start_date = None
        
        # 遍歷每週數據
        for date, row in weekly_data.iterrows():
            phase = row['market_phase']
            
            # 如果是新階段或第一個數據點
            if phase != current_phase:
                # 保存前一個階段
                if current_phase is not None and start_date is not None:
                    phases_data.append({
                        'phase': current_phase,
                        'start_date': start_date,
                        'end_date': date - timedelta(days=1)
                    })
                
                # 開始新階段
                current_phase = phase
                start_date = date
        
        # 添加最後一個階段
        if current_phase is not None and start_date is not None:
            # 週數據最後一個點的日期加6天（代表週末）
            last_end_date = weekly_data.index[-1] + timedelta(days=6)
            phases_data.append({
                'phase': current_phase,
                'start_date': start_date,
                'end_date': last_end_date
            })
            
        # 轉換為DataFrame
        phases_df = pd.DataFrame(phases_data)
        
        logger.info(f"識別出{len(phases_df)}個連續市場階段")
        return phases_df
            
    def save_market_phases(self, filename=None):
        """保存市場階段數據"""
        if filename is None:
            # 使用當前日期作為文件名
            filename = f"market_phases_{datetime.now().strftime('%Y%m%d')}.json"
            
        filepath = self.output_dir / filename
        
        if self.market_data is None or self.market_data.empty:
            logger.error("沒有數據可保存")
            return False
            
        # 獲取週級別數據
        weekly_data = self.aggregate_to_weekly()
        
        # 獲取市場階段分類
        phases_df = self.identify_market_phases(weekly_data)
        
        if phases_df.empty:
            logger.error("市場階段分類結果為空")
            return False
            
        # 轉換為字典格式
        market_phases = {}
        for _, row in phases_df.iterrows():
            phase = row['phase']
            start = row['start_date'].strftime('%Y-%m-%d')
            end = row['end_date'].strftime('%Y-%m-%d')
            
            phase_key = f"{phase}_{start.replace('-', '')}"
            market_phases[phase_key] = {
                'start_date': start,
                'end_date': end,
                'description': self._get_phase_description(phase)
            }
            
        # 保存為JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(market_phases, f, indent=2, ensure_ascii=False)
            
        # 同時保存原始數據和週級別數據
        csv_path = self.output_dir / f"fear_greed_daily_{datetime.now().strftime('%Y%m%d')}.csv"
        self.market_data.to_csv(csv_path)
        
        weekly_csv_path = self.output_dir / f"fear_greed_weekly_{datetime.now().strftime('%Y%m%d')}.csv"
        weekly_data.to_csv(weekly_csv_path)
            
        logger.info(f"市場階段數據已保存至 {filepath}")
        logger.info(f"原始數據已保存至 {csv_path}")
        logger.info(f"週級別數據已保存至 {weekly_csv_path}")
        
        return True
    
    def _get_phase_description(self, phase):
        """獲取市場階段描述"""
        descriptions = {
            'EXTREME_FEAR': 'EXTREME_FEAR',
            'FEAR': 'FEAR',
            'NEUTRAL': 'NEUTRAL',
            'GREED': 'GREED',
            'EXTREME_GREED': 'EXTREME_GREED'
        }
        return descriptions.get(phase, f'未知市場階段: {phase}')
    
    def generate_market_phases_code(self, output_file=None):
        """生成可直接使用的Market_Screener_Configuration.py代碼"""
        if self.market_data is None or self.market_data.empty:
            logger.error("沒有數據可用於生成代碼")
            return
            
        # 獲取週級別數據
        weekly_data = self.aggregate_to_weekly()
        
        # 獲取市場階段分類
        phases_df = self.identify_market_phases(weekly_data)
        
        if phases_df.empty:
            logger.error("市場階段分類結果為空")
            return
            
        # 生成代碼
        code = "# 自動生成的市場階段定義，基於加密貨幣恐懼與貪婪指數\n"
        code += "# 生成時間: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n"
        code += "MARKET_PHASES: Dict[str, MarketPhase] = {\n"
        
        for _, row in phases_df.iterrows():
            phase = row['phase']
            # 保留完整的日期格式，包括日
            start = row['start_date'].strftime('%Y-%m-%d')
            end = row['end_date'].strftime('%Y-%m-%d')
            description = self._get_phase_description(phase)
            
            # 生成唯一的鍵名，使用日期
            key = f"{phase}_{start.replace('-', '')}"
            code += f"    '{key}': MarketPhase('{start}', '{end}', '{description}'),\n"
            
        code += "}\n"
        
        # 保存或顯示代碼
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code)
            logger.info(f"市場階段代碼已保存至 {output_file}")
        else:
            print(code)
            
        return code
        
    def visualize_market_phases(self):
        """視覺化市場階段"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            if self.market_data is None or self.market_data.empty:
                logger.error("沒有數據可視覺化")
                return
                
            # 獲取週級別數據
            weekly_data = self.aggregate_to_weekly()
            
            # 獲取市場階段分類
            phases_df = self.identify_market_phases(weekly_data)
            
            if phases_df.empty:
                logger.error("市場階段分類結果為空")
                return
                
            # 設置圖表
            plt.figure(figsize=(15, 10))
            
            # 繪製恐懼與貪婪指數
            ax = plt.subplot(2, 1, 1)
            plt.plot(self.market_data.index, self.market_data['value'], 'b-', alpha=0.7)
            plt.fill_between(self.market_data.index, self.market_data['value'], alpha=0.2)
            plt.title('加密貨幣恐懼與貪婪指數 (每日)')
            plt.ylabel('指數值')
            plt.ylim(0, 100)
            plt.grid(True, alpha=0.3)
            
            # 添加水平線和區域標識
            plt.axhline(y=25, color='r', linestyle='--', alpha=0.5)
            plt.axhline(y=45, color='orange', linestyle='--', alpha=0.5)
            plt.axhline(y=55, color='g', linestyle='--', alpha=0.5)
            plt.axhline(y=75, color='darkgreen', linestyle='--', alpha=0.5)
            
            plt.text(self.market_data.index[0], 12.5, 'Extreme Fear', verticalalignment='center')
            plt.text(self.market_data.index[0], 35, 'Fear', verticalalignment='center')
            plt.text(self.market_data.index[0], 50, 'Neutral', verticalalignment='center')
            plt.text(self.market_data.index[0], 65, 'Greed', verticalalignment='center')
            plt.text(self.market_data.index[0], 87.5, 'Extreme Greed', verticalalignment='center')
            
            # 格式化x軸日期
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.xticks(rotation=45)
            
            # 繪製週級別指數
            ax2 = plt.subplot(2, 1, 2)
            plt.plot(weekly_data.index, weekly_data['value'], 'b-', linewidth=2)
            plt.scatter(weekly_data.index, weekly_data['value'], c=weekly_data['value'], 
                      cmap='RdYlGn', vmin=0, vmax=100, s=50)
            plt.title('加密貨幣恐懼與貪婪指數 (週平均)')
            plt.ylabel('指數值')
            plt.ylim(0, 100)
            plt.grid(True, alpha=0.3)
            
            # 添加水平線和區域標識
            plt.axhline(y=25, color='r', linestyle='--', alpha=0.5)
            plt.axhline(y=45, color='orange', linestyle='--', alpha=0.5)
            plt.axhline(y=55, color='g', linestyle='--', alpha=0.5)
            plt.axhline(y=75, color='darkgreen', linestyle='--', alpha=0.5)
            
            # 標記市場階段
            for _, row in phases_df.iterrows():
                phase = row['phase']
                start = row['start_date']
                end = row['end_date']
                
                color_map = {
                    'EXTREME_FEAR': 'darkred',
                    'FEAR': 'red',
                    'NEUTRAL': 'yellow',
                    'GREED': 'lightgreen',
                    'EXTREME_GREED': 'darkgreen'
                }
                
                color = color_map.get(phase, 'gray')
                plt.axvspan(start, end, alpha=0.2, color=color)
                
                # 添加標籤
                mid_point = start + (end - start) / 2
                plt.text(mid_point, 90, phase, horizontalalignment='center', 
                       bbox=dict(facecolor='white', alpha=0.7))
            
            # 格式化x軸日期
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # 保存圖表
            plt_path = self.output_dir / f"market_phases_chart_{datetime.now().strftime('%Y%m%d')}.png"
            plt.savefig(plt_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"市場階段視覺化圖表已保存至 {plt_path}")
            
        except ImportError:
            logger.warning("無法創建視覺化，請安裝matplotlib: pip install matplotlib")
        except Exception as e:
            logger.error(f"創建視覺化時出錯: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='加密貨幣恐懼與貪婪指數數據採集器')
    parser.add_argument('--limit', type=int, default=2000, help='數據點限制')
    parser.add_argument('--output', type=str, default='market_data', help='輸出目錄')
    
    args = parser.parse_args()
    
    collector = FearGreedIndexCollector(output_dir=args.output)
    collector.fetch_fear_greed_index(args.limit)
    collector.save_market_phases()
    collector.generate_market_phases_code("market_phases_code.py")
    collector.visualize_market_phases()

if __name__ == "__main__":
    main()