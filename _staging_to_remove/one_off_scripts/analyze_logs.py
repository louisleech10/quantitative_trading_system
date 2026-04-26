import sys
import re
from datetime import datetime

def analyze(filename):
    print(f"\n--- Analyzing {filename} ---")
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return

    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?)')
    
    entries = []
    for line in lines:
        match = pattern.match(line)
        if match:
            ts_str = match.group(1).replace(',', '.')
            try:
                ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            entries.append((ts, line.strip()))

    if not entries:
        print("No timestamped entries found.")
        return

    gaps = []
    for i in range(1, len(entries)):
        gap = (entries[i][0] - entries[i-1][0]).total_seconds()
        gaps.append((gap, entries[i-1], entries[i]))

    gaps.sort(key=lambda x: x[0], reverse=True)

    print(f"Total entries: {len(entries)}")
    print(f"Top 10 gaps:")
    for gap, prev, curr in gaps[:10]:
        print(f"Gap: {gap}s | {prev[0]} -> {curr[0]}")
        print(f"  Prev: {prev[1]}")
        print(f"  Next: {curr[1]}")

    gt_30m = [g for g in gaps if g[0] >= 1800]
    print(f"Gaps >= 30 mins: {len(gt_30m)}")
    for gap, prev, curr in gt_30m:
        print(f"  {gap}s: {prev[0]} to {curr[0]}")

analyze('logs/case_search_api_20260412.log')
analyze('logs/errors_20260412.log')
