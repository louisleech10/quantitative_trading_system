#!/bin/bash
# 證據：無位置參數之 pytest，記錄器之 argv_norm.args＝testpaths（["tests"]）而非 []
cd /private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/wt_v50 || exit 2
venv/bin/python - <<'PY'
import sys, json
sys.path.insert(0, ".")
from pathlib import Path
import tempfile
from tests.registry.testreg_helpers import make_repo, recorded_pytest
r = make_repo(Path(tempfile.mkdtemp()), {"momentum/__init__.py": "", "tests/test_one.py": "def test_a():\n    assert True\n"})
proc, ids = recorded_pytest(r)
rec = [x for x in r.ledger(ids[0]) if x.get("kind") == "session"]
print("argv_norm.args =", json.loads(rec[0]["argv_norm"])["args"] if rec and "argv_norm" in rec[0] else rec)
PY
