"""IC 1e+1b B5 G-2：選型 diff + 新路徑 freeze（全程式生成，禁手填）。

用法:
  source venv/bin/activate
  python scripts/ic1eb_g2_golden_diff.py

產出:
  handoffs/IC1EB-GOLDEN-DIFF.md
  handoffs/ic1eb_newpath_freeze/{manifest + per-run report + feature hashes}
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ic1eb_b5_replay import (  # noqa: E402
    BASELINE_DIR,
    assert_g1_invariant,
    build_pass_set,
    g1_hashes_from_result,
    load_manifest,
    nan_p_fraction,
    patch_persist_outputs,
    removal_reason_for,
    replay_run,
    verify_inputs_integrity,
    _sha_bytes,
    _sha_json,
)

OUT_DIFF = REPO_ROOT / "handoffs" / "IC1EB-GOLDEN-DIFF.md"
FREEZE_DIR = REPO_ROOT / "handoffs" / "ic1eb_newpath_freeze"
STAGING = REPO_ROOT / "handoffs" / "ic1eb_newpath_freeze.staging"


def _load_baseline_report(report_file: str) -> dict[str, Any]:
    path = BASELINE_DIR / report_file
    return json.loads(path.read_text(encoding="utf-8"))


def _finite_or_none(v: Any) -> Any:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _feature_sig_hash(rows: list[dict[str, Any]]) -> str:
    payload = [
        {
            "feature_name": r["feature_name"],
            "p_value": r.get("p_value"),
            "p_value_adj": r.get("p_value_adj"),
            "t_stat": r.get("t_stat"),
        }
        for r in sorted(rows, key=lambda x: str(x.get("feature_name") or ""))
    ]
    return _sha_json(payload)


def _build_per_feature_rows(
    run_name: str,
    old_report: dict[str, Any],
    new_result: dict[str, Any],
    old_passed: set[str],
    new_passed: set[str],
) -> list[dict[str, Any]]:
    old_by = {
        row["feature_name"]: row for row in (old_report.get("summary_table") or [])
    }
    new_by = {
        row["feature_name"]: row for row in (new_result.get("summary_table") or [])
    }
    names = sorted(set(old_by) | set(new_by))
    new_removed = (
        ((new_result.get("filter_log") or {}).get("stage5_thresholds") or {}).get(
            "removed_features"
        )
        or {}
    )
    rows: list[dict[str, Any]] = []
    for name in names:
        o = old_by.get(name) or {}
        n = new_by.get(name) or {}
        pass_old = name in old_passed
        pass_new = name in new_passed
        rows.append(
            {
                "run": run_name,
                "feature_name": name,
                "p_iid_old": _finite_or_none(o.get("p_value")),
                "p_hac": _finite_or_none(n.get("p_value")),
                "q": _finite_or_none(n.get("p_value_adj")),
                "pass_old": pass_old,
                "pass_new": pass_new,
                "reason": removal_reason_for(
                    name, new_removed, passed=pass_new
                ),
            }
        )
    return rows


def _direction_summary(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(all_rows)
    both = sum(1 for r in all_rows if r["pass_old"] and r["pass_new"])
    old_only = sum(1 for r in all_rows if r["pass_old"] and not r["pass_new"])
    new_only = sum(1 for r in all_rows if (not r["pass_old"]) and r["pass_new"])
    neither = sum(1 for r in all_rows if (not r["pass_old"]) and (not r["pass_new"]))
    # 高自相關假顯著轉紅：old pass + new fail + p_hac > p_iid (or p_hac nan)
    false_sig_to_red = 0
    p_inflated = 0
    comparable = 0
    for r in all_rows:
        po, ph = r["p_iid_old"], r["p_hac"]
        if po is not None and ph is not None:
            comparable += 1
            if ph > po:
                p_inflated += 1
        if r["pass_old"] and not r["pass_new"]:
            false_sig_to_red += 1
    return {
        "n_feature_rows": n,
        "pass_both": both,
        "pass_old_only": old_only,
        "pass_new_only": new_only,
        "pass_neither": neither,
        "false_significant_to_red": false_sig_to_red,
        "p_hac_gt_p_iid_among_comparable": p_inflated,
        "n_comparable_p": comparable,
        "fraction_p_inflated": (p_inflated / comparable) if comparable else None,
    }


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def write_diff_md(
    *,
    head: str,
    per_run: dict[str, Any],
    all_rows: list[dict[str, Any]],
    direction: dict[str, Any],
    fraction_nan_p: dict[str, Any],
    freeze_manifest_sha: str,
) -> None:
    lines: list[str] = []
    lines.append("# IC1EB-GOLDEN-DIFF（G-2 變更腿）")
    lines.append("")
    lines.append(f"- generated_at_utc: `{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- head_sha: `{head}`")
    lines.append(f"- generator: `scripts/ic1eb_g2_golden_diff.py`")
    lines.append(f"- baseline: `handoffs/ic1eb_baseline/` (v4, 唯讀)")
    lines.append(f"- newpath_freeze_manifest_sha256: `{freeze_manifest_sha}`")
    lines.append("")
    lines.append("## 變化方向摘要（三方簽核）")
    lines.append("")
    lines.append(
        "預期：高自相關假顯著 feature 在 HAC+FDR 下轉紅（pass_old→!pass_new）。"
    )
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|--------|------:|")
    for k, v in direction.items():
        if isinstance(v, float):
            lines.append(f"| {k} | {v:.6f} |")
        else:
            lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## fraction_nan_p（12h 短窗 fail-closed 比例）")
    lines.append("")
    lines.append("| run | n_summary | fraction_nan_p (new p_value) | n_passed_old | n_passed_new |")
    lines.append("|-----|----------:|-----------------------------:|-------------:|-------------:|")
    for run_name, stats in sorted(fraction_nan_p.items()):
        lines.append(
            f"| `{run_name}` | {stats['n_summary']} | {stats['fraction_nan_p']:.6f} | "
            f"{stats['n_passed_old']} | {stats['n_passed_new']} |"
        )
    lines.append("")
    lines.append("## Per-run 通過集合")
    lines.append("")
    lines.append("| run | n_rows | pass_old | pass_new | old_only | new_only |")
    lines.append("|-----|-------:|---------:|---------:|---------:|---------:|")
    for run_name, info in sorted(per_run.items()):
        lines.append(
            f"| `{run_name}` | {info['n_rows']} | {info['n_passed_old']} | "
            f"{info['n_passed_new']} | {info['pass_old_only']} | {info['pass_new_only']} |"
        )
    lines.append("")
    lines.append("## Per-feature 對照表（13 顆全量）")
    lines.append("")
    lines.append(
        "| run | feature_name | p_iid_old | p_hac | q | pass_old | pass_new | reason |"
    )
    lines.append(
        "|-----|--------------|----------:|------:|--:|:--------:|:--------:|--------|"
    )
    # 全量可能很大：寫完整（G-2 義務）；MD 允許大檔
    for r in all_rows:
        lines.append(
            "| `{run}` | `{feat}` | {po} | {ph} | {q} | {o} | {n} | {reason} |".format(
                run=r["run"],
                feat=_md_escape(str(r["feature_name"])),
                po=("" if r["p_iid_old"] is None else f"{r['p_iid_old']:.6g}"),
                ph=("" if r["p_hac"] is None else f"{r['p_hac']:.6g}"),
                q=("" if r["q"] is None else f"{r['q']:.6g}"),
                o=str(r["pass_old"]),
                n=str(r["pass_new"]),
                reason=r["reason"],
            )
        )
    lines.append("")
    lines.append("## 機讀附件")
    lines.append("")
    lines.append("- `handoffs/ic1eb_newpath_freeze/baseline_manifest.json`")
    lines.append("- 每 run 的 `*.report.json` + `feature_sig` 已寫入 freeze 目錄")
    lines.append("")
    OUT_DIFF.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if STAGING.exists():
        raise SystemExit(f"staging residual: {STAGING}; clean first")
    if FREEZE_DIR.exists():
        # 允許覆寫 staging→rename；若 FINAL 存在先移走
        bak = FREEZE_DIR.with_suffix(".bak." + datetime.now().strftime("%Y%m%d%H%M%S"))
        FREEZE_DIR.rename(bak)
        print(f"[g2] moved existing freeze → {bak}", flush=True)

    patch_persist_outputs()
    manifest = load_manifest()
    verify_inputs_integrity(manifest)

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    ).stdout.strip()

    STAGING.mkdir(parents=True)
    freeze: dict[str, Any] = {
        "purpose": "IC 1e+1b new-path freeze (HAC p + FDR q + stage5 consumption)",
        "spec": "docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md §G G-2",
        "head_sha": head,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/ic1eb_g2_golden_diff.py",
        "baseline_manifest_head_sha": manifest.get("head_sha"),
        "baseline_dir": "handoffs/ic1eb_baseline",
        "procedure": {
            "persist_outputs": "patched no-op (same as capture_ic1eb_baseline F6)",
            "replay": "scripts/ic1eb_b5_replay.replay_run",
        },
        "runs": {},
        "name_set_sha256": None,
        "fraction_nan_p_12h": {},
    }

    all_rows: list[dict[str, Any]] = []
    per_run_summary: dict[str, Any] = {}
    fraction_nan_p: dict[str, Any] = {}
    all_new_names: list[str] = []

    for run_name, entry in sorted((manifest.get("runs") or {}).items()):
        print(f"[g2] replaying {run_name} ...", flush=True)
        t0 = time.monotonic()
        new_result = replay_run(manifest, run_name)
        elapsed = time.monotonic() - t0
        # G-1 不變量（腳本側也驗一次，失敗即停）
        assert_g1_invariant(entry, new_result)

        old_report = _load_baseline_report(entry["report_file"])
        old_passed_list = build_pass_set(old_report)
        # baseline report 走舊 filter_log；若 reconstruct 用 new API 仍適用
        # 優先用 manifest 的 passed_set_sha256 交叉驗證
        old_passed = set(old_passed_list)
        new_passed_list = build_pass_set(new_result)
        new_passed = set(new_passed_list)
        if _sha_json(old_passed_list) != entry["passed_set_sha256"]:
            # 舊 report 與 manifest 不一致=基線腐壞
            raise AssertionError(
                f"{run_name}: reconstructed old passed_set_sha256 mismatch vs manifest"
            )

        rows = _build_per_feature_rows(
            run_name, old_report, new_result, old_passed, new_passed
        )
        all_rows.extend(rows)

        report_path = STAGING / f"{run_name}.report.json"
        report_path.write_text(
            json.dumps(new_result, ensure_ascii=False, sort_keys=True, indent=1, default=str),
            encoding="utf-8",
        )
        g1 = g1_hashes_from_result(new_result)
        feature_names = sorted({r["feature_name"] for r in rows})
        all_new_names.extend(feature_names)
        sig_hash = _feature_sig_hash(
            [
                {
                    "feature_name": row.get("feature_name"),
                    "p_value": row.get("p_value"),
                    "p_value_adj": row.get("p_value_adj"),
                    "t_stat": row.get("t_stat"),
                }
                for row in (new_result.get("summary_table") or [])
            ]
        )

        freeze_entry = {
            "request": entry["request"],
            "elapsed_seconds": round(elapsed, 1),
            "report_file": report_path.name,
            "report_sha256": _sha_bytes(report_path.read_bytes()),
            "n_summary_rows": len(new_result.get("summary_table") or []),
            "n_passed_features": len(new_passed_list),
            "passed_set_sha256": _sha_json(new_passed_list),
            "feature_name_set_sha256": _sha_json(feature_names),
            "feature_pq_values_sha256": sig_hash,
            "g1_five_hash": g1["g1_five_hash"],
            "summary_feature_order_sha256": g1["summary_feature_order_sha256"],
            "series_sha256": g1["series_sha256"],
            "fraction_nan_p": nan_p_fraction(new_result.get("summary_table") or []),
            "pass_old_only": sum(1 for r in rows if r["pass_old"] and not r["pass_new"]),
            "pass_new_only": sum(1 for r in rows if (not r["pass_old"]) and r["pass_new"]),
            "n_passed_old": len(old_passed),
            "n_passed_new": len(new_passed),
        }
        freeze["runs"][run_name] = freeze_entry
        per_run_summary[run_name] = {
            "n_rows": len(rows),
            "n_passed_old": len(old_passed),
            "n_passed_new": len(new_passed),
            "pass_old_only": freeze_entry["pass_old_only"],
            "pass_new_only": freeze_entry["pass_new_only"],
        }

        # 12h 短窗統計
        req = entry["request"]
        tf = req.get("timeframe")
        if tf == "12h" or (
            isinstance(req.get("symbols"), list) and req.get("timeframe") == "12h"
        ):
            fraction_nan_p[run_name] = {
                "n_summary": freeze_entry["n_summary_rows"],
                "fraction_nan_p": freeze_entry["fraction_nan_p"],
                "n_passed_old": freeze_entry["n_passed_old"],
                "n_passed_new": freeze_entry["n_passed_new"],
            }
        print(
            f"[g2] {run_name} done {elapsed:.1f}s "
            f"passed {len(old_passed)}→{len(new_passed)} "
            f"nan_p={freeze_entry['fraction_nan_p']:.3f}",
            flush=True,
        )

    freeze["name_set_sha256"] = _sha_json(sorted(set(all_new_names)))
    freeze["fraction_nan_p_12h"] = fraction_nan_p
    freeze["direction_summary"] = _direction_summary(all_rows)

    # machine-readable full table
    table_path = STAGING / "per_feature_diff.json"
    table_path.write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    freeze["per_feature_diff_file"] = table_path.name
    freeze["per_feature_diff_sha256"] = _sha_bytes(table_path.read_bytes())

    man_path = STAGING / "baseline_manifest.json"
    man_path.write_text(
        json.dumps(freeze, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    man_sha = _sha_bytes(man_path.read_bytes())
    os.rename(STAGING, FREEZE_DIR)

    write_diff_md(
        head=head,
        per_run=per_run_summary,
        all_rows=all_rows,
        direction=freeze["direction_summary"],
        fraction_nan_p=fraction_nan_p,
        freeze_manifest_sha=man_sha,
    )
    print(f"[g2] wrote {OUT_DIFF}", flush=True)
    print(f"[g2] freeze → {FREEZE_DIR}", flush=True)
    print(json.dumps(freeze["direction_summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
