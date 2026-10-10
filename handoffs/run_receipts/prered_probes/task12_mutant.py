"""PRE-RED Task 1.2 mutant：取版規則改為「最新 commit」⇒ 樣本斷言 10 項須紅。用法：venv/bin/python <本檔>"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import tests.governance.test_todofmt_sample_fftfmeta as t  # noqa: E402

latest = subprocess.run(["git", "log", "-1", "--format=%H", "--", t._MANIFEST_REL], cwd=REPO,
                        capture_output=True, text=True, check=True).stdout.strip()
t._sample_commit = lambda: latest
cases = [("boundary_03", t.test_boundary_03_callers_now_empty_callers_later_nonempty, None)]
cases += [(f"boundary_06[{c}]", t.test_boundary_06_each_case_has_named_test, c) for c in t.FOUR_CASES]
cases += [(f"equation[{e}]", t.test_coverage_risk_lists_each_equation_with_named_test, e) for e in t.FIVE_EQUATIONS]
red = 0
for name, fn, arg in cases:
    try:
        fn() if arg is None else fn(arg)
        print(f"{name}: 存活")
    except AssertionError:
        red += 1
print(f"mutant 取最新 commit：{red}/{len(cases)} 紅")
