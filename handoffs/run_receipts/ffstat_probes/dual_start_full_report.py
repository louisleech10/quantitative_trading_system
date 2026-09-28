"""§G⑦ 預設全設定雙起點之完整報告收據（逐欄 max_error、violations、ineligible〔含重疊列數〕、all_nan、input_explained）。
用法：venv/bin/python handoffs/run_receipts/ffstat_probes/dual_start_full_report.py <週期> <輸出 json>
每次只跑一個週期（8GB 本機記憶體；test_ffstat_golden 之 test_dual_start_convergence_default_config 同一 helper）。"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

tf, out = sys.argv[1], Path(sys.argv[2])
source = str(REPO / h.CONTRACT["dual_start"]["timeframes"][tf])
mp = pytest.MonkeyPatch()
with tempfile.TemporaryDirectory(prefix=f"ffstat_dual_{tf}_") as tmp:
    try:
        h.prepare_stat_env(mp, Path(tmp))
        report = h.dual_start_report(Path(tmp), tf, {}, source)
    finally:
        mp.undo()
report["command"] = f"venv/bin/python handoffs/run_receipts/ffstat_probes/dual_start_full_report.py {tf} {out}"
out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
print(tf, {k: report.get(k) for k in ("rows", "m", "f_max", "margin", "eligible")},
      "violations", len(report.get("violations", {})), "ineligible", len(report.get("ineligible", [])),
      "all_nan", len(report.get("all_nan", [])), "input_explained", len(report.get("input_explained", {})))
