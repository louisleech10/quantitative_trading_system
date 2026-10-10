"""PRE-RED Task 1.1 mutant 實跑：W 快照 mini repo 上改壞入口或靜態器，斷言集合不再等於 QUANT_FATAL。
用法：venv/bin/python <本檔>"""

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from tests.governance.test_mutation_scope_extension import QUANT_FATAL, _run_entry, _w_snapshot_repo  # noqa: E402

MUTANTS = {
    "static_never_fatal": ("scripts/mutation_probe_static.py", None),
    "entry_skips_tests_momentum": ("scripts/mutation_scope_static.sh", ("tests/momentum tests/api", "tests/api")),
}
for name, (rel, repl) in MUTANTS.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = _w_snapshot_repo(Path(tmp))
        p = root / rel
        src = p.read_text(encoding="utf-8")
        if repl is None:
            # 靜態器之 fatal 列印行改為不印（以列印前綴為錨點）
            anchor = '"  · '
            assert anchor in src, "找不到 fatal 列印錨點"
            src = src.replace(anchor, '"  ~ ')
        else:
            assert repl[0] in src, f"找不到錨點 {repl[0]}"
            src = src.replace(repl[0], repl[1])
        p.write_text(src, encoding="utf-8")
        _, names, _ = _run_entry(root)
        quant = {n for n in names if not n.startswith("tests/governance/")}
        print(f"{name}: equals_QUANT_FATAL={quant == QUANT_FATAL} size={len(quant)}  ⇒ {'RED（mutant 被抓）' if quant != QUANT_FATAL else '存活'}")
