import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import h5py
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Tuple
import numpy as np
from src.data.data_loader_momentum import DataLoader
from Momentum.DataExtraction.Market_Screener_Configuration import MarketConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataPreparation:
    def __init__(self, data_dir: str = "data"):
        """Initialize data preparation pipeline"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize data loader
        self.data_loader = DataLoader()
        
        # HDF5 file structure
        self.db_path = self.data_dir / "momentum_cases.h5"
        
    def read_cases(self, file_path: str) -> List[Dict]:
        """Read cases from CSV file containing symbols and timestamps"""
        try:
            df = pd.read_csv(file_path)
            cases = []
            for _, row in df.iterrows():
                case = {
                    'symbol': row['symbol'],
                    'timestamp': pd.to_datetime(row['timestamp'])
                }
                cases.append(case)
            logger.info(f"Loaded {len(cases)} cases from {file_path}")
            return cases
        except Exception as e:
            logger.error(f"Error reading cases: {str(e)}")
            return []
            
    def get_case_data(self, symbol: str, timestamp: datetime, 
                      lookback_bars: int = 100, forward_bars: int = 1) -> pd.DataFrame:
        """Get historical data for a specific case"""
        try:
            # Calculate time range
            end_time = timestamp + timedelta(hours=4 * forward_bars)
            # Add extra bars for calculating indicators
            start_time = timestamp - timedelta(hours=4 * (lookback_bars + 0))
            
            # Get data
            df = self.data_loader.get_historical_klines(
                symbol=symbol,
                start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
                end_time=end_time.strftime('%Y-%m-%d %H:%M:%S'),
                interval='4h'
            )
            
            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()
                
            # Verify data quality
            if self._check_data_quality(df, symbol):
                return df
            else:
                logger.warning(f"Data quality check failed for {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {str(e)}")
            return pd.DataFrame()
            
    def _check_data_quality(self, df: pd.DataFrame, symbol: str) -> bool:
        """Check data quality and anomalies"""
        try:
            # Check for missing values in all columns
            if df.isnull().any().any():
                logger.warning(f"Missing values found in {symbol}")
                return False
                
            # Check for zero values in essential columns
            zero_check_columns = ['volume', 'quote_asset_volume', 'number_of_trades']
            for col in zero_check_columns:
                if (df[col] == 0).any():
                    logger.warning(f"Zero values found in {symbol} {col}")
                    return False
                
            # Check for price anomalies
            price_changes = df['close'].pct_change()
            if (price_changes.abs() > 0.5).any():  # 50% price change in 4h
                logger.warning(f"Abnormal price changes found in {symbol}")
                return False
                
            # Check data continuity
            time_diff = pd.Series(df.index).diff()
            expected_diff = pd.Timedelta(hours=4)
            if not (time_diff[1:] == expected_diff).all():
                logger.warning(f"Data gaps found in {symbol}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking data quality: {str(e)}")
            return False
            
    def save_to_hdf5(self, case: Dict, data: pd.DataFrame):
        """Save case data to HDF5 file"""
        try:
            symbol = case['symbol']
            timestamp = case['timestamp']
            
            # Convert DataFrame to dictionary of arrays
            data_dict = {
                'timestamp': data.index.astype(np.int64) // 10**9,  # Convert to Unix timestamp
                'open': data['open'].values,
                'high': data['high'].values,
                'low': data['low'].values,
                'close': data['close'].values,
                'volume': data['volume'].values,
                'close_time': data['close_time'].values,
                'quote_asset_volume': data['quote_asset_volume'].values,
                'number_of_trades': data['number_of_trades'].values,
                'taker_buy_base_asset_volume': data['taker_buy_base_asset_volume'].values,
                'taker_buy_quote_asset_volume': data['taker_buy_quote_asset_volume'].values
            }
            
            with h5py.File(self.db_path, 'a') as f:
                # Create group for symbol if not exists
                if symbol not in f:
                    f.create_group(symbol)
                    
                # Create dataset for this case
                case_id = f"{timestamp.strftime('%Y%m%d_%H%M')}"
                if case_id in f[symbol]:
                    del f[symbol][case_id]
                
                # Create case group
                case_group = f[symbol].create_group(case_id)
                
                # Save each column separately
                for key, values in data_dict.items():
                    dataset = case_group.create_dataset(
                        key,
                        data=values,
                        compression="gzip"
                    )
                    
                # Add metadata to the case group
                case_group.attrs['symbol'] = symbol
                case_group.attrs['timestamp'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                case_group.attrs['creation_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Successfully saved {symbol} data to HDF5")
            
        except Exception as e:
            logger.error(f"Error saving to HDF5: {str(e)}")
            raise  # Re-raise the exception for debugging
            
            with h5py.File(self.db_path, 'a') as f:
                # Create group for symbol if not exists
                if symbol not in f:
                    f.create_group(symbol)
                    
                # Create dataset for this case
                case_id = f"{timestamp.strftime('%Y%m%d_%H%M')}"
                if case_id in f[symbol]:
                    del f[symbol][case_id]
                
                # Create case group
                case_group = f[symbol].create_group(case_id)
                
                # Save each column separately
                for key, values in data_dict.items():
                    case_group.create_dataset(
                        key,
                        data=values,
                        compression="gzip"
                    )
                
                # Save metadata
                dataset.attrs['symbol'] = symbol
                dataset.attrs['timestamp'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                dataset.attrs['creation_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
        except Exception as e:
            logger.error(f"Error saving to HDF5: {str(e)}")
            
    def save_to_csv(self, case: Dict, data: pd.DataFrame):
        """Save case data to CSV file for inspection"""
        try:
            symbol = case['symbol']
            timestamp = case['timestamp']
            
            # Create csv directory if not exists
            csv_dir = self.data_dir / "csv"
            csv_dir.mkdir(exist_ok=True)
            
            # Save to CSV
            case_id = f"{timestamp.strftime('%Y%m%d_%H%M')}"
            csv_path = csv_dir / f"{symbol}_{case_id}.csv"
            
            # Reset index to make timestamp a column
            data.reset_index().to_csv(csv_path, index=False)
            
            logger.info(f"Saved CSV file to {csv_path}")
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            
    def process_all_cases(self, cases_file: str):
        """Process all cases and save to HDF5"""
        cases = self.read_cases(cases_file)
        
        for case in cases:
            logger.info(f"Processing {case['symbol']} at {case['timestamp']}")
            
            try:
                # Get data
                data = self.get_case_data(
                    symbol=case['symbol'],
                    timestamp=case['timestamp']
                )
                
                if not data.empty:
                    # Save to HDF5
                    self.save_to_hdf5(case, data)
                    # Save to CSV for inspection
                    self.save_to_csv(case, data)
                else:
                    logger.warning(f"Skipped {case['symbol']} due to empty data")
                    
            except Exception as e:
                logger.error(f"Failed to process {case['symbol']}: {str(e)}")
                continue
if __name__ == "__main__":
    prep = DataPreparation()
    csvpath = "/Users/louis/Desktop/quant_strategy/Momentum/symbol_timestampstest.csv"
    prep.process_all_cases(csvpath)  # 假設CSV檔名