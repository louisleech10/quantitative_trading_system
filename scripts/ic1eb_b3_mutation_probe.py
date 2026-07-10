"""IC1EB B3 mutation 探針：兩種真紅。

1) iid-swap: 把 xsec HAC t 換成 i.i.d. t → T-3.1a 分離斷言紅
2) label-rename: 把 horizon 解析改成永遠對 `_label` → T-3.1b maxlags floor 紅

整體 exit 0 = 兩 mutation 皆能轉紅且還原乾淨；否則 exit 1。
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TARGET = REPO / "momentum/Analysis/ic_filter_orchestrator.py"

# Mutation A: HAC path → i.i.d. t (p 用 2*t.sf 但 t 已錯；分離斷言必紅)
ORIG_HAC_BLOCK = """            else:
                hac = _compute_hac_on_ic_series(values, sig_horizon)
                t_stat = float(hac["t_stat"]) if hac.get("t_stat") is not None else float("nan")
                p_value = float(hac["p_value"]) if hac.get("p_value") is not None else float("nan")
                maxlags_by_feature[feature_name] = hac.get("maxlags", np.nan)"""

MUT_IID_BLOCK = """            else:
                # TEMP-MUTANT: i.i.d. t (B3 mutation A)
                finite = values[np.isfinite(values)]
                if finite.size > 1 and float(np.nanstd(finite)) > 0:
                    t_stat = float(
                        np.nanmean(finite) / (np.nanstd(finite) / np.sqrt(finite.size))
                    )
                else:
                    t_stat = float("nan")
                p_value = float("nan") if not np.isfinite(t_stat) else float(
                    2.0 * __import__("scipy").stats.t.sf(abs(t_stat), df=max(finite.size - 1, 1))
                )
                maxlags_by_feature[feature_name] = 0"""

# Mutation B: resolve horizon from working label_col after rename (loses return_5)
ORIG_LABELS_RESOLVE = """            sig_horizon = _resolve_cross_sectional_label_horizon(horizon_source_name)
            working_df = features.copy()
            working_df["_label"] = label_series.reindex(features.index).to_numpy()
            label_col = "_label\""""

MUT_LABELS_RESOLVE = """            working_df = features.copy()
            working_df["_label"] = label_series.reindex(features.index).to_numpy()
            label_col = "_label"
            # TEMP-MUTANT: resolve AFTER rename (CODEX-3 regression)
            horizon_source_name = "_label"
            sig_horizon = _resolve_cross_sectional_label_horizon("_label")"""

TEST_A = "tests/momentum/test_ic_1eb_b3_xsec.py::test_t31a_xsec_p_not_none_matches_kernel_and_separates_iid"
TEST_B = "tests/momentum/test_ic_1eb_b3_xsec.py::test_t31b_labels_path_return_5_maxlags_floor"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_pytest(node: str) -> int:
    return subprocess.run(
        [sys.executable, "-m", "pytest", node, "-q", "--tb=line"],
        cwd=REPO,
    ).returncode


def probe_one(name: str, orig: str, mut: str, test_node: str) -> int:
    src = TARGET.read_text()
    if src.count(orig) != 1:
        print(f"PROBE FAIL [{name}]: expected exactly 1 occurrence of ORIG block")
        print(f"  count={src.count(orig)}")
        return 1
    pre = sha(TARGET)
    if run_pytest(test_node) != 0:
        print(f"PROBE FAIL [{name}]: baseline not green")
        return 1
    TARGET.write_text(src.replace(orig, mut))
    try:
        red = run_pytest(test_node)
    finally:
        TARGET.write_text(src)
    if sha(TARGET) != pre:
        print(f"PROBE FAIL [{name}]: restore sha mismatch")
        return 1
    if red == 0:
        print(f"PROBE FAIL [{name}]: mutation did NOT turn red (fake-green risk)")
        return 1
    if run_pytest(test_node) != 0:
        print(f"PROBE FAIL [{name}]: not green after restore")
        return 1
    print(f"MUTATION PROBE PASS [{name}]: red exit={red}, restore ok")
    return 0


def main() -> int:
    rc_a = probe_one("iid-swap", ORIG_HAC_BLOCK, MUT_IID_BLOCK, TEST_A)
    rc_b = probe_one(
        "label-rename", ORIG_LABELS_RESOLVE, MUT_LABELS_RESOLVE, TEST_B
    )
    if rc_a == 0 and rc_b == 0:
        print("MUTATION PROBE PASS: both A(iid) and B(label-rename)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
