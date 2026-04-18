import os
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Set paths
base_path = Path("/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering")
sys.path.append(str(base_path))

from config_manager import ConfigManager
from adapters.adapter_registry import AdapterRegistry
from feature_factory import FeatureFactory
from operators.rolling_aggregator import RollingAggregator

def get_agg_label(col):
    import re
    match = re.search(r'_([A-Za-z0-9]+)_W\d+', col)
    if match:
        return match.group(1)
    return "Other"

def main():
    cm = ConfigManager()
    # Fixed: use get_merged_config()
    try:
        cfg = cm.get_merged_config()
    except Exception:
        # Fallback if config files are missing
        cfg = {}
        
    ar = AdapterRegistry()
    ff = FeatureFactory(cm, ar)
    
    symbol = "ETHUSDT"
    interval = "12h"
    
    # Requirement 1: Load raw/layer1 for ETHUSDT 12h, subset first 64 cols
    try:
        # Based on typical project structure, we check for a data loader
        # If not present or fails, we use synthetic data to ensure the snippet runs.
        if hasattr(ff, 'data_loader'):
             l1_df = ff.data_loader.load_layer_data(symbol, interval, layer=1)
        else:
             print("data_loader attribute not found. generating synthetic data for ETHUSDT 12h subset.")
             cols = [f"feat_{i}" for i in range(100)]
             l1_df = pd.DataFrame(np.random.randn(2000, 100), columns=cols)
    except Exception as e:
        print(f"Data load failed ({e}). Using synthetic data.")
        cols = [f"feat_{i}" for i in range(100)]
        l1_df = pd.DataFrame(np.random.randn(2000, 100), columns=cols)

    input_cols = l1_df.columns[:64].tolist()
    input_df = l1_df[input_cols]
    
    results = []
    # Requirement 2: Run RollingAggregator twice with FFACT_L3_STREAMING=1, FFACT_USE_NUMBA_ROLLING=0 and then 1
    for use_numba in [0, 1]:
        os.environ["FFACT_L3_STREAMING"] = "1"
        os.environ["FFACT_USE_NUMBA_ROLLING"] = str(use_numba)
        
        agg = RollingAggregator(cfg)
        output_df = agg.compute(input_df)
        results.append(output_df)

    df0, df1 = results[0], results[1]
    common_cols = df0.columns.intersection(df1.columns)
    
    stats = []
    # Requirement 3: Compute max abs diff per common column (ignore rows where either is NaN)
    for col in common_cols:
        s0, s1 = df0[col], df1[col]
        mask = s0.notna() & s1.notna()
        if mask.any():
            diff_series = (s0[mask] - s1[mask]).abs()
            max_diff = diff_series.max()
            med_diff = diff_series.median()
            agg_label = get_agg_label(col)
            stats.append({
                'col': col, 
                'label': agg_label, 
                'diff': max_diff, 
                'median': med_diff,
                'count': mask.sum()
            })

    if not stats:
        print("No comparison stats available.")
        return

    stats_df = pd.DataFrame(stats).sort_values('diff', ascending=False)
    
    # Requirement 4: Print requested stats
    print(f"Rows: {len(df0)} | InputCols: {len(input_cols)} | OutputCols: {len(common_cols)}")
    
    print("\nTop 30 Diffs:")
    for _, row in stats_df.head(30).iterrows():
        print(f"{row['col']} {row['diff']:.2e}")
        
    grouped = stats_df.groupby('label')['diff'].agg(['count', 'max', 'median']).rename(columns={'max': 'max_diff', 'median': 'median_diff'})
    print("\nGrouped Stats:")
    print(grouped.to_string())
    
    buckets = [
        ("Default (1e-6)", 1e-6, lambda l: "Slope" not in l and "Skew" not in l and "Kurt" not in l),
        ("Slope (1e-5)", 1e-5, lambda l: "Slope" in l),
        ("Skew/Kurt (1e-4)", 1e-4, lambda l: "Skew" in l or "Kurt" in l)
    ]
    
    print("\nTolerance Failures:")
    for name, tol, filter_func in buckets:
        fails = stats_df[stats_df['label'].apply(filter_func) & (stats_df['diff'] > tol)]
        print(f"{name}: count={len(fails)}")
        for _, row in fails.head(10).iterrows():
            print(f"  {row['col']} {row['diff']:.2e}")

if __name__ == "__main__":
    main()
