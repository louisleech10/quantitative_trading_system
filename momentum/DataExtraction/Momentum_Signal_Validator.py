from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd
import logging

class MomentumValidator:
    """
    Validates price surge signals based on simple criteria
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate_signal(self, 
                       data: pd.DataFrame, 
                       signal_idx: int,
                       timeframe: str) -> Optional[Dict]:
        """
        Validate a potential price surge signal
        
        Args:
            data: OHLCV data
            signal_idx: Index of the K-line meeting surge criteria
            timeframe: Time period ('12h' or '24h')
            
        Returns:
            Dict containing signal details if valid, None otherwise
        """
        try:
            if signal_idx < 1:  # Need at least one previous K-line
                return None
                
            # Get current and previous data
            current = data.iloc[signal_idx]
            prev = data.iloc[signal_idx - 1]
            
            # Calculate price change
            price_change = (current['close'] - prev['close']) / prev['close']
            
            # Check minimum price change criteria
            min_change = 0.10 if timeframe == '12h' else 0.15
            if price_change < min_change:
                return None
            
            # Create signal record
            signal = {
                'timestamp': current.name,  # K-line timestamp
                'symbol': data.get('symbol', 'Unknown'),
                'timeframe': timeframe,
                'price_change': price_change,
                'close_price': current['close'],
                'volume': current['volume']
            }
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error validating signal: {str(e)}")
            return None