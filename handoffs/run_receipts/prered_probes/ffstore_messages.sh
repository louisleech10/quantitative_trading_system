#!/bin/zsh
# PRE-RED 審碼 r1 後：逐支取 FFSTORE 列之失敗訊息（junitxml），供歸因鑑別。用法：zsh <本檔> <scratch> <out.txt>
S=${1:?scratch}; OUT=${2:?out}
venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=short --junitxml=$S/ff34.xml \
  tests/api/test_gap3_event_analysis_horizon_purge.py tests/api/test_gap3_ic_progress_fields.py tests/api/test_gap3_ic_stop_gate.py \
  tests/api/test_gap3_scan_grid.py tests/api/test_ic_analysis_service.py tests/api/test_splitunify_event_scan_projection.py \
  tests/momentum/test_feature_library_config_hash.py tests/momentum/test_ic_cross_sectional_cut2.py > $S/ff34.log 2>&1
echo "pytest_rc=$? $(tail -1 $S/ff34.log)" > $OUT
venv/bin/python - "$S/ff34.xml" >> $OUT <<'PY'
import sys, xml.etree.ElementTree as ET
for tc in ET.parse(sys.argv[1]).getroot().iter("testcase"):
    f = tc.find("failure")
    if f is None:
        f = tc.find("error")
    if f is not None:
        msg = (f.get("message") or "").replace("\n", " ")[:200]
        print(f"{tc.get('classname').split('.')[-1]}::{tc.get('name')} | {msg}")
PY
