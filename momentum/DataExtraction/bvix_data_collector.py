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

class BVIXDataCollector:
    """幣安VIX指數(BVIX)數據採集器"""
    
    def __init__(self, output_dir="market_data"):
        """初始化採集器"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.bvix_data = None
        
        # 市場階段定義
        self.market_phases = {
            'EXTREME_FEAR': (0, 25),
            'FEAR': (26, 45),
            'NEUTRAL': (46, 55),
            'GREED': (56, 75),
            'EXTREME_GREED': (76, 100)
        }
        
    def fetch_bvix_data(self, start_date, end_date, interval='1w'):
        """
        抓取指定時間範圍的BVIX數據
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            interval: 時間間隔 ('1d', '1w', '1M')
            
        Returns:
            pd.DataFrame: BVIX數據
        """
        try:
            # 轉換日期為毫秒時間戳
            start_ms = int(pd.Timestamp(start_date).timestamp() * 1000)
            end_ms = int(pd.Timestamp(end_date).timestamp() * 1000)
            
            # 幣安BVIX指數的API端點
            # 使用BVIX標誌，也可嘗試BVX（根據幣安API檔案）
            url = "https://fapi.binance.com/futures/data/globalLongShortRatio"
            
            # 參數
            params = {
                'symbol': 'BTCUSDT',  # 使用BTC數據作為市場情緒代表
                'period': interval,
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': 500  # 最大限制
            }
            
            # 請求數據
            logger.info(f"正在請求BVIX數據：{start_date}至{end_date}")
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"API請求失敗: {response.status_code} - {response.text}")
                return pd.DataFrame()
                
            # 解析數據
            data = response.json()
            if not data:
                logger.warning("API返回空數據")
                return pd.DataFrame()
                
            # 轉換為DataFrame
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 計算BVIX等效值（這裡使用longShortRatio作為替代）
            # 注意：真正的BVIX可能需要其他計算方法，這裡僅作示例
            df['bvix_value'] = 100 - (df['longShortRatio'] * 10)  # 示例轉換
            df['bvix_value'] = df['bvix_value'].clip(0, 100)  # 確保在0-100範圍
            
            logger.info(f"成功獲取{len(df)}筆BVIX數據")
            self.bvix_data = df
            return df
            
        except Exception as e:
            logger.error(f"抓取BVIX數據時出錯: {str(e)}")
            return pd.DataFrame()
    
    def classify_market_phases(self):
        """根據BVIX值分類市場階段"""
        if self.bvix_data is None or self.bvix_data.empty:
            logger.error("沒有可用的BVIX數據進行分類")
            return pd.DataFrame()
            
        df = self.bvix_data.copy()
        
        # 創建市場階段列
        df['market_phase'] = None
        
        # 分類
        for phase, (lower, upper) in self.market_phases.items():
            mask = (df['bvix_value'] >= lower) & (df['bvix_value'] <= upper)
            df.loc[mask, 'market_phase'] = phase
            
        # 檢查是否有未分類的資料
        missing = df['market_phase'].isna().sum()
        if missing > 0:
            logger.warning(f"有{missing}個資料點未被分類")
            
        # 創建時間範圍數據
        phases_data = []
        
        current_phase = None
        start_date = None
        
        for date, row in df.iterrows():
            phase = row['market_phase']
            
            # 如果是新階段或第一個資料點
            if phase != current_phase or (current_phase is None and phase is not None):
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
            phases_data.append({
                'phase': current_phase,
                'start_date': start_date,
                'end_date': df.index[-1]
            })
            
        # 轉換為DataFrame
        phases_df = pd.DataFrame(phases_data)
        
        return phases_df
            
    def save_market_phases(self, filename=None):
        """保存市場階段數據"""
        if filename is None:
            # 使用當前日期作為文件名
            filename = f"market_phases_{datetime.now().strftime('%Y%m%d')}.json"
            
        filepath = self.output_dir / filename
        
        if self.bvix_data is None or self.bvix_data.empty:
            logger.error("沒有數據可保存")
            return False
            
        # 獲取市場階段分類
        phases_df = self.classify_market_phases()
        
        if phases_df.empty:
            logger.error("市場階段分類結果為空")
            return False
            
        # 轉換為字典格式
        market_phases = {}
        for _, row in phases_df.iterrows():
            phase = row['phase']
            start = row['start_date'].strftime('%Y-%m-%d')
            end = row['end_date'].strftime('%Y-%m-%d')
            
            market_phases[phase + "_" + start.replace('-', '')] = {
                'start_date': start,
                'end_date': end,
                'description': self._get_phase_description(phase)
            }
            
        # 保存為JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(market_phases, f, indent=2, ensure_ascii=False)
            
        # 同時保存原始BVIX數據
        csv_path = self.output_dir / f"bvix_data_{datetime.now().strftime('%Y%m%d')}.csv"
        self.bvix_data.to_csv(csv_path)
            
        logger.info(f"市場階段數據已保存至 {filepath}")
        logger.info(f"原始BVIX數據已保存至 {csv_path}")
        
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
        if self.bvix_data is None or self.bvix_data.empty:
            logger.error("沒有數據可用於生成代碼")
            return
            
        phases_df = self.classify_market_phases()
        
        if phases_df.empty:
            logger.error("市場階段分類結果為空")
            return
            
        # 生成代碼
        code = "# 自動生成的市場階段定義，基於BVIX數據\n"
        code += "# 生成時間: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n"
        code += "MARKET_PHASES: Dict[str, MarketPhase] = {\n"
        
        for _, row in phases_df.iterrows():
            phase = row['phase']
            start = row['start_date'].strftime('%Y-%m')
            end = row['end_date'].strftime('%Y-%m')
            description = self._get_phase_description(phase)
            
            code += f"    '{phase}_{start.replace('-', '')}': MarketPhase('{start}', '{end}', '{description}'),\n"
            
        code += "}\n"
        
        # 保存或顯示代碼
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code)
            logger.info(f"市場階段代碼已保存至 {output_file}")
        else:
            print(code)
            
        return code

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BVIX數據採集器')
    parser.add_argument('--start', type=str, required=True, help='開始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='結束日期 (YYYY-MM-DD)')
    parser.add_argument('--interval', type=str, default='1w', help='時間間隔 (1d/1w/1M)')
    parser.add_argument('--output', type=str, default='market_data', help='輸出目錄')
    
    args = parser.parse_args()
    
    collector = BVIXDataCollector(output_dir=args.output)
    collector.fetch_bvix_data(args.start, args.end, args.interval)
    collector.save_market_phases()
    collector.generate_market_phases_code("market_phases_code.py")

if __name__ == "__main__":
    main()