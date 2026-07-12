"""非 opt-in subprocess 與 S1–S11 隔離驗證。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.ic_persist_redirect import REQUIRED_SEAM_IDS, RedirectPatchSet


FIXED_NODEIDS = (
    "tests/api/test_ic_run_selector.py::test_disambig_same_tf_different_hash",
    "tests/momentum/test_ic_filter_orchestrator.py::test_refilter_without_cache_raises",
    "tests/momentum/Analysis/test_long_short_analyzer.py::test_insufficient_ls_samples",
)


def test_non_opt_in_subprocesses_never_activate(tmp_path: Path) -> None:
    for index, nodeid in enumerate(FIXED_NODEIDS):
        probe = tmp_path / f"probe-{index}.json"
        env = os.environ.copy()
        env["IC_PERSIST_ASSERT_NO_ACTIVATION"] = "1"
        env["IC_PERSIST_PROBE_JSON"] = str(probe)
        completed = subprocess.run(
            ["venv/bin/python", "-m", "pytest", nodeid, "-q"],
            text=True,
            capture_output=True,
            env=env,
            timeout=60,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        payload = json.loads(probe.read_text(encoding="utf-8"))
        assert payload == {"activation_count": 0, "violations": []}


@pytest.mark.parametrize("seam_id", sorted(REQUIRED_SEAM_IDS, key=lambda item: int(item[1:])))
def test_all_seam_probes_stay_under_root(
    seam_id: str, redirect_patch_set: RedirectPatchSet, tmp_path: Path
) -> None:
    ctx = redirect_patch_set.activate(tmp_path / seam_id, owner=f"isolation-{seam_id}")
    try:
        outputs = redirect_patch_set.resolve_all()[seam_id].probe(ctx.redirect_root)
        assert all(path.resolve().is_relative_to(ctx.redirect_root) for path in outputs)
        assert not ctx.spy.violations
    finally:
        redirect_patch_set.deactivate(ctx)

