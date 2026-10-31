#!/usr/bin/env python3
"""估時收據之 identity.match 計算（只印，不寫檔）：與 `scripts/heavy_run_guard.py` 同一規則（`scripts/heavy_commands.json` 之
規則 id 與 code／data／config 路徑），供寫 `handoffs/run_receipts/*-estimate.json` 時填 `identity.match`。

用法：venv/bin/python scripts/estimate_identity.py <規則 id> <命令檔>（命令檔內容＝將要執行之完整命令列；以檔傳入，
避免命令列含重型樣式而被 heavy_run_guard 誤攔）。
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import heavy_run_guard as g  # noqa: E402


def main(argv: list) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    rule_id, cmd = argv[0], Path(argv[1]).read_text(encoding="utf-8").strip()
    rules = json.loads((SCRIPTS / "heavy_commands.json").read_text(encoding="utf-8"))
    rule = next((r for k in ("wrapped", "self_watched", "background_only") for r in rules.get(k, [])
                 if isinstance(r, dict) and r.get("id") == rule_id), None)
    if rule is None:
        print(f"heavy_commands.json 無規則 {rule_id}", file=sys.stderr)
        return 2
    args = shlex.split(cmd)
    match = g._rid().compute_match(g._entrypoint(rule, args), args, rule.get("code_paths") or [],
                                   rule.get("data_paths") or [], rule.get("config_paths") or [])
    print(json.dumps(match, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
