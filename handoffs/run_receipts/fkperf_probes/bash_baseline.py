"""FKPERF Task 0.2 驗證②：現行 bash 實作於 1×／4×／10× 之外部程序數基準（切換前一次性，寫收據）。

用法（repo 根）：venv/bin/python handoffs/run_receipts/fkperf_probes/bash_baseline.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.governance import _fkperf_spawn as sp  # noqa: E402

C = sp.load_contract()
targets = dict(C["scale_total_keys"])
rows = []
for label in C["bash_baseline_scales"]:
    with tempfile.TemporaryDirectory() as t:
        if label == "1x":
            from tests.governance import _fkperf_oracle as fo
            root = Path(t) / "tree"
            fo.build_current_tree(root)
        else:
            root = sp.build_scaled_tree(Path(t), targets[label])
        n = sp.total_key_count(root)
        for mode in ("--check", "emit"):
            try:
                total, by = sp.count_spawns(root, mode)
            except subprocess.CalledProcessError as exc:
                print("FAIL", label, mode, exc.returncode, exc.stderr.decode("utf-8", "replace")[:2000], flush=True)
                raise
            rows.append({"scale": label, "total_keys": n, "mode": mode, "spawns": total,
                         "top": dict(sorted(by.items(), key=lambda kv: -kv[1])[:6])})
            print(rows[-1], flush=True)
print(sp.write_receipt(rows, "fkperf-bash-baseline"))
