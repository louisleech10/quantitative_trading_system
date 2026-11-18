"""tests/conftest.py TESTSEL-SEED 段（每測試固定隨機種子、非 function 範圍 fixture 之 `pytest_fixture_setup` hook）之驗收。

自 testsel 整合分支之 tests/registry/test_testsel_plugin.py 抽出（該檔其餘為自製選取外掛之驗收，不合回 main）：
同一測試及其 module 範圍 fixture 之亂數輸入不依前序測試與觸發 fixture 之測試。
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Dict, Optional

import pytest

from tests._nocap_subprocess import run_watched_subprocess

ROOT_REPO = Path(__file__).resolve().parents[2]

_SEED_TESTS = """\
    import json
    import os
    import random
    from pathlib import Path

    import numpy as np
    import pytest

    RNG = np.random.default_rng(7)  # 模組層、各測試共用之產生器
    OUT = Path(os.environ["SEED_OUT"])


    def _rec(name):
        vals = [random.random(), float(np.random.random()), float(RNG.random())]
        d = json.loads(OUT.read_text()) if OUT.exists() else {}
        d[name] = vals
        OUT.write_text(json.dumps(d))


    @pytest.fixture(scope="module")
    def mf():
        _rec("mf")  # module 範圍 fixture 內之亂數（只在第一個用到它之測試建立）


    def test_first(mf):
        _rec("first")


    def test_second(mf):
        _rec("second")
    """


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")


def _clean_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("COVERAGE_", "PYTEST_", "TESTREG_")) and k != "PYTHONPATH"}
    env["NUMBA_CACHE_DIR"] = str(Path(os.environ.get("TMPDIR", "/tmp")) / "conftest_seed_numba_cache")
    env.update(extra or {})
    return env


@pytest.mark.parametrize("variant", ["enabled", "no_fixture_hook", "control"])
def test_fixed_seed_order_independent(tmp_path: Path, variant: str) -> None:
    """同一測試及其 module 範圍 fixture 之亂數輸入（全域 random、numpy.random、模組層 Generator）不依前序測試與觸發
    fixture 之測試：全檔跑與只跑後段子集（-k test_second）所得相同。改壞對照：拿掉 `pytest_fixture_setup` hook ⇒
    module fixture 之值不同；全拿掉 ⇒ 測試之值不同。hook 原始碼取自本 repo tests/conftest.py 之 TESTSEL-SEED 段。"""
    text = (ROOT_REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
    b, e = text.index("# TESTSEL-SEED BEGIN"), text.index("# TESTSEL-SEED END")
    seg = text[b:e] if variant != "control" else ""
    if variant == "no_fixture_hook":
        fb, fe = seg.index("# TESTSEL-SEED-FIXTURE BEGIN"), seg.index("# TESTSEL-SEED-FIXTURE END")
        seg = seg[:fb] + seg[fe:]
    r = tmp_path / "seed"
    _write(r, "pytest.ini", "[pytest]\ntestpaths = tests\n")
    (r / "tests").mkdir(parents=True, exist_ok=True)
    (r / "tests" / "conftest.py").write_text("from typing import Any, Dict\n\nimport pytest\n\n" + seg,
                                             encoding="utf-8")
    _write(r, "tests/test_seed.py", _SEED_TESTS)
    got = []
    for i, extra in enumerate(([], ["-k", "test_second"])):
        out = tmp_path / f"seed{i}.json"
        proc = run_watched_subprocess([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *extra],
                                      cwd=str(r), env=_clean_env({"SEED_OUT": str(out)}))
        assert proc.returncode == 0, proc.stdout[-3000:]
        d = json.loads(out.read_text())
        got.append((d["mf"], d["second"]))
    (mf_full, sec_full), (mf_sub, sec_sub) = got
    assert (mf_full == mf_sub) == (variant == "enabled"), got
    assert (sec_full == sec_sub) == (variant == "enabled"), got
