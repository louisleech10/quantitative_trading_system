"""PRE-RED Task 2.4 §G③：兩次獨立凍結之確定性投影逐位元組比對＋重凍收據（舊→新）。

用法：python refreeze_compare.py <A baseline.json> <B baseline.json> <舊 baseline.json> <out.json> <unit,...>
投影（每單元）：layers.L1..L6 與 final_L7 之 canonical_sha256、五分量 sha256、rows、columns、groups、nan_count、cell_count、
index_metadata；group_set_sha256；feature_count；config_hash；artifacts 之資料檔 sha256；l1_direct 之同上表格欄位。
排除：perf 全部欄位、絕對路徑字串。
"""

from __future__ import annotations

import json
import sys

TABLE_KEYS = ("canonical_sha256", "column_order_sha256", "dtypes_sha256", "index_sha256", "values_sha256",
              "nan_mask_sha256", "rows", "columns", "groups", "nan_count", "cell_count", "index_metadata")


def _table(t: dict) -> dict:
    return {k: t.get(k) for k in TABLE_KEYS}


def _artifacts(a) -> object:
    """資料檔 path→sha256（與 tests/feature_engineering/test_failopen_correctness.py 之 `_artifact_data_file_map`
    同一排除規則：manifest metadata 與 .lock 不比；aggregate_sha256 含 metadata 故不比）。"""
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("_fo_corr", root / "tests/feature_engineering/test_failopen_correctness.py")
    sys.path.insert(0, str(root))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._artifact_data_file_map(a or {})


def projection(rec: dict) -> dict:
    return {
        "layers": {k: _table(v) for k, v in sorted((rec.get("layers") or {}).items())},
        "final_L7": _table(rec.get("final_L7") or {}),
        "l1_direct": _table(rec.get("l1_direct") or {}),
        "group_set_sha256": rec.get("group_set_sha256"),
        "feature_count": rec.get("feature_count"),
        "config_hash": rec.get("config_hash"),
        "artifacts": _artifacts(rec.get("artifacts")),
    }


def main(a_p, b_p, old_p, out_p, units) -> int:
    a, b, old = json.load(open(a_p)), json.load(open(b_p)), json.load(open(old_p))
    report = {"units": {}, "deterministic": True}
    for unit in units.split(","):
        sym, tf = unit.split("/")
        pa, pb = projection(a["single_tf"][sym][tf]), projection(b["single_tf"][sym][tf])
        same = json.dumps(pa, sort_keys=True) == json.dumps(pb, sort_keys=True)
        report["deterministic"] &= same
        po = old["single_tf"].get(sym, {}).get(tf, {})
        changes = {}
        for layer in [*sorted(pa["layers"]), "final_L7"]:
            new_t = pa["layers"].get(layer) if layer != "final_L7" else pa["final_L7"]
            old_t = (po.get("layers") or {}).get(layer) if layer != "final_L7" else po.get("final_L7")
            if old_t is None:
                continue
            diff = {k: [old_t.get(k), new_t.get(k)] for k in TABLE_KEYS if old_t.get(k) != new_t.get(k)}
            changes[layer] = {k: ([str(v[0])[:12], str(v[1])[:12]] if isinstance(v[0], str) else v)
                              for k, v in diff.items()}
        report["units"][unit] = {"A_equals_B": same, "changes_old_to_new": changes,
                                 "l1_direct_new": pa["l1_direct"].get("canonical_sha256"),
                                 "feature_count": [po.get("feature_count"), pa["feature_count"]],
                                 "config_hash": [po.get("config_hash"), pa["config_hash"]]}
    preserved = {k: json.dumps(old["single_tf"].get(k.split("/")[0], {}).get(k.split("/")[1]), sort_keys=True)
                 == json.dumps(a["single_tf"].get(k.split("/")[0], {}).get(k.split("/")[1]), sort_keys=True)
                 for k in ("BTCUSDT/1h",)}
    preserved["multi_tf"] = json.dumps(old["multi_tf"], sort_keys=True) == json.dumps(a["multi_tf"], sort_keys=True)
    report["unlisted_units_preserved"] = preserved
    json.dump(report, open(out_p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"deterministic": report["deterministic"], "unlisted_units_preserved": preserved,
                      **{u: {"A_equals_B": r["A_equals_B"], "changed_layers": sorted(r["changes_old_to_new"])}
                         for u, r in report["units"].items()}}, ensure_ascii=False, indent=1))
    return 0 if report["deterministic"] and all(preserved.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
