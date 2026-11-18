"""Task 2.1 邊界④之全標的一次性收據（TESTSEL I10，2026-11-12）。

測試 `test_ffstat_calibration.py::test_boundary_08_default_runs_no_column_short` 只留 BTCUSDT（1h、12h 兩格）；
ETHUSDT、BCHUSDT 與 BTCUSDT 同一生成與校準判定碼，「各標的前史有效值是否湊滿 N」屬資料性質，改由本收據對契約
`cost_measure_symbols × cost_measure_timeframes` 全格呼叫同一測試函式（同設定、同窗、同斷言）並記結果。
何時重跑：`data_cache/feature_klines`／長歷史快取（契約 `longhist_cache_dir`）更新、校準或預熱碼
（`momentum/FeatureEngineering/preprocessing/calibration.py`、`warmup_window.py`、`stable_mask.py`）或預設 N 變更時。
用法：venv/bin/python handoffs/run_receipts/ffstat_probes/boundary08_symbols_receipt.py <輸出 json> [--all]
（預設只跑測試未涵蓋之標的；`--all` 連 BTCUSDT 一併跑）
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402
from tests.feature_engineering import test_ffstat_calibration as cal_tests  # noqa: E402

out = Path(sys.argv[1])
rows = []
# 測試內已跑之標的（BOUNDARY_08_TEST_SYMBOLS）不重跑；加 `--all` 則全格
symbols = [s for s in h.CONTRACT["cost_measure_symbols"]
           if "--all" in sys.argv[2:] or s not in cal_tests.BOUNDARY_08_TEST_SYMBOLS]
for symbol in symbols:
    for timeframe in h.CONTRACT["cost_measure_timeframes"]:
        mp = pytest.MonkeyPatch()
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix=f"ffstat_b08_{symbol}_{timeframe}_") as tmp:
            try:
                cal_tests.test_boundary_08_default_runs_no_column_short(symbol, timeframe, Path(tmp), mp)
                outcome, detail = "passed", None
            except AssertionError as exc:
                outcome, detail = "failed", str(exc)[:2000]
            finally:
                mp.undo()
        rows.append({"symbol": symbol, "timeframe": timeframe, "outcome": outcome, "detail": detail,
                     "seconds": round(time.monotonic() - started, 1)})
        print(rows[-1], flush=True)
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip()
dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "momentum", "tests/feature_engineering"],
                            cwd=str(REPO), capture_output=True, text=True).stdout.strip())
receipt = {"test": "tests/feature_engineering/test_ffstat_calibration.py::test_boundary_08_default_runs_no_column_short",
           "head": head, "dirty_product_or_tests": dirty, "rows": rows,
           "all_passed": all(r["outcome"] == "passed" for r in rows),
           "command": f"venv/bin/python handoffs/run_receipts/ffstat_probes/boundary08_symbols_receipt.py {out}"}
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
sys.exit(0 if receipt["all_passed"] else 1)
