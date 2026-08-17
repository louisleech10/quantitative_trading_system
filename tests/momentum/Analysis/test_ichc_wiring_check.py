"""ICHC Task 5.1 — wiring check 常駐強制（pytest 包裝）＋M5 mutation＋fail-closed。"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts/ic_wiring_check.py"
STORE = REPO / "frontend/src/store/icAnalysisStore.ts"
ALLOWLIST = REPO / "scripts/ic_wiring_allowlist.json"


def _run(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *extra],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )


class TestWiringCheck:
    def test_current_tree_green(self):
        proc = _run()
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_m5_injected_ghost_key_turns_red(self, tmp_path):
        """M5：PRESET_TOGGLES 注入新幽靈 key → rc!=0。"""
        mutated = tmp_path / "store.ts"
        src = STORE.read_text(encoding="utf-8")
        mutated.write_text(
            src.replace(
                "    ic_calculation: true,",
                "    ic_calculation: true,\n    ichc_m5_ghost_key: true,",
                1,
            ),
            encoding="utf-8",
        )
        proc = _run("--store", str(mutated))
        assert proc.returncode == 1
        assert "ichc_m5_ghost_key" in proc.stdout

    def test_allowlist_absent_fails_closed(self, tmp_path):
        proc = _run("--allowlist", str(tmp_path / "nope.json"))
        assert proc.returncode == 1
        assert "allowlist 缺席" in proc.stdout

    def test_stale_allowlist_entry_turns_red(self, tmp_path):
        """R2 lifecycle：條目 key 已不存在於宣告檔 → rc!=0。"""
        data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
        data["entries"].append(
            {
                "key": "ichc_stale_entry_zzz",
                "file": "frontend/src/store/icAnalysisStore.ts",
                "kind": "ghost_toggle",
                "finding": "TEST",
                "status": "test",
            }
        )
        mutated = tmp_path / "allow.json"
        mutated.write_text(json.dumps(data), encoding="utf-8")
        proc = _run("--allowlist", str(mutated))
        assert proc.returncode == 1
        assert "過期" in proc.stdout

    def test_scan_target_missing_is_env_error(self, tmp_path):
        proc = _run("--orch", str(tmp_path / "nope.py"))
        assert proc.returncode == 2
