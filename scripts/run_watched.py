"""NOCAP Task 0.3：以共用監看（`handoffs/run_receipts/numview_probes/_watchdog.py`）包任意重型命令。

不因時間終止；卡死＝log 未增長且子行程樹 CPU 無進度（門檻取 NUMVIEW 判準 `cell_rules.watchdog`）；卡死前留現場並判
原因（memory／hang）。印 `[run-watched] start|stalled|exit` 行；rc：子行程 rc、卡死 4（hang）／5（memory）。

用法：`python scripts/run_watched.py --log <路徑> -- <命令> [參數...]`
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
WATCHDOG = REPO / "handoffs" / "run_receipts" / "numview_probes" / "_watchdog.py"


def _watchdog():  # type: ignore[no-untyped-def]
    name = "nocap_shared_watchdog"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, WATCHDOG)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass 需模組已登記
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _criteria() -> dict:
    sys.path.insert(0, str(REPO))
    from tests.feature_engineering import numview_helpers as nh

    return json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    cmd: List[str] = [c for c in args.cmd if c != "--"] if args.cmd[:1] == ["--"] else list(args.cmd)
    if not cmd:
        parser.error("缺命令")
    wd = _watchdog()
    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"[run-watched] start {' '.join(cmd)}（log {log}）", flush=True)
    result = wd.run_watched(cmd, log_path=log, config=wd.load_config(_criteria()), cwd=str(REPO))
    if result.status == wd.STALLED:
        diag = log.with_name(log.name + ".stall_diagnosis.json")
        diag.write_text(json.dumps({"reason": result.reason, "cause": result.cause, **(result.diagnosis or {})},
                                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"[run-watched] stalled 原因 {result.cause}：{result.reason}；現場 {diag}；"
              f"{'程式卡住——依堆疊查因修好再跑，不得直接重跑' if result.cause == wd.CAUSE_HANG else '記憶體不足'}",
              flush=True)
        return 4 if result.cause == wd.CAUSE_HANG else 5
    print(f"[run-watched] exit rc={result.returncode}（{result.wall_seconds:.0f} 秒"
          f"{'，逾預期（只記錄）' if result.over_expected else ''}）", flush=True)
    return int(result.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
