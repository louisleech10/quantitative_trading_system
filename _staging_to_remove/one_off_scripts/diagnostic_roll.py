import os
import time
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append(os.getcwd())

# Import from the actual locations
try:
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
    from api.services.kline_data_service import KlineDataService
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def run_diagnostic():
    # 1. Load data
    print("Loading data...")
    ks = KlineDataService()
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=365) # 1 year of data
    
    # Check if get_kline_data is async or sync
    import inspect
    is_async = inspect.iscoroutinefunction(ks.get_kline_data)
    
    if is_async:
        import asyncio
        df_raw = asyncio.run(ks.get_kline_data("ETHUSDT", "12h", start_time, end_time))
    else:
        df_raw = ks.get_kline_data("ETHUSDT", "12h", start_time, end_time)
        
    # 2. Get Layer 1 subset (64 columns)
    # Using RollingAggregator directly on OHLCV to avoid FeatureFactory complexity
    print("Preparing input columns...")
    l1_subset = df_raw[['open', 'high', 'low', 'close', 'volume']].copy()
    # Duplicate to get 60+ columns for meaningful test
    for i in range(12):
        for col in ['open', 'high', 'low', 'close', 'volume']:
            l1_subset[f"{col}_{i}"] = l1_subset[col]
    
    l1_subset = l1_subset.iloc[:, :64]
    print(f"Input subset shape: {l1_subset.shape}")

    windows = [3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
    aggregators = ['mean', 'std', 'rank', 'zscore', 'skew', 'kurt', 'slope', 'min', 'max', 'range']
    
    # 3. Force Pandas path
    print("Running Pandas path...")
    os.environ['FFACT_USE_NUMBA_ROLLING'] = '0'
    ra_pd = RollingAggregator(windows=windows, aggregators=aggregators)
    start_pd = time.time()
    res_pd = ra_pd.apply(l1_subset)
    elapsed_pd = time.time() - start_pd
    print(f"Pandas path elapsed: {elapsed_pd:.4f}s")

    # 4. Force Numba path
    print("Running Numba path...")
    os.environ['FFACT_USE_NUMBA_ROLLING'] = '1'
    ra_nb = RollingAggregator(windows=windows, aggregators=aggregators)
    start_nb = time.time()
    res_nb = ra_nb.apply(l1_subset)
    elapsed_nb = time.time() - start_nb
    print(f"Numba path elapsed: {elapsed_nb:.4f}s")

    # 5. Align and compare
    common_cols = res_pd.columns.intersection(res_nb.columns)
    res_pd = res_pd[common_cols]
    res_nb = res_nb[common_cols]
    
    # Convert to float to avoid issues
    res_pd = res_pd.astype(float)
    res_nb = res_nb.astype(float)
    
    diffs = (res_pd - res_nb).abs()
    # Handle NaNs (they should be in the same places)
    mask = res_pd.notna() & res_nb.notna()
    diffs = diffs.where(mask, 0)
    
    max_diffs = diffs.max()

    # 6. Grouped Summary
    summary = []
    agg_suffixes = [f'_{a}' for a in aggregators]
    
    for suffix in agg_suffixes:
        cols_with_suffix = [c for c in common_cols if c.endswith(suffix)]
        if not cols_with_suffix:
            continue
        agg_diffs = max_diffs[cols_with_suffix]
        worst_col = agg_diffs.idxmax()
        summary.append({
            'aggregator': suffix[1:],
            'count': len(cols_with_suffix),
            'max_diff': agg_diffs.max(),
            'worst_col': worst_col
        })
    
    print("\nSummary by Aggregator:")
    print(pd.DataFrame(summary).sort_values('max_diff', ascending=False).to_string(index=False))

    print("\nTop 20 Worst Columns (Global):")
    print(max_diffs.sort_values(ascending=False).head(20))

if __name__ == "__main__":
    run_diagnostic()
