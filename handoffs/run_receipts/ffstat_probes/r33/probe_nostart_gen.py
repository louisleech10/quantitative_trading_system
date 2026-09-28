"""探針：無起始日全史、平穩化關閉之輕量設定生成（於主 repo 或改前 worktree 執行；輸出至指定目錄）。
用法：cd <repo 或 worktree> && python probe_nostart_gen.py <out_dir>"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.getcwd())
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
mp = pytest.MonkeyPatch()
try:
    h.prepare_stat_env(mp, out)
    root, _f, result = h.run_stat(out, h.stat_payload(fracdiff=False, adf=False), start_date=None, end_date=None,
                                  kline_dir="/Users/louis/Desktop/quantitative_trading_system/data_cache/feature_klines")
    print("ROOT", root)
finally:
    mp.undo()
