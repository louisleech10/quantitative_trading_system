"""FF-STAT：FF-TFMETA golden 基準之有證據遷移（平穩化設定 schema 變更 ⇒ config_hash 改變）。

schema 變更（累計）：b1 刪 `preprocessing.adf_safe_skip`；b3a 刪 `preprocessing.adf_differencing.sample_size`、
新增 `preprocessing.calibration_bars_by_timeframe`（預設 {}）。

逐情境：①以改前程式樹（FF-STAT 動工前）重跑，證其去除允許路徑之 manifest／task sha 等於 FF-STAT 動工前之凍結基準
（取自 git `ORIGINAL_REV:tests/_golden/fftfmeta/baseline.json`）；②以本樹重跑；③證「改前輸出套上述 schema 變更、
把改前 config_hash 字串換成改後值」後與本樹輸出逐位元組相等，且群組逐欄 hash 與群組檔名集合三方相同（特徵值零變動）；
④皆成立才把基準之兩個 sha 欄改為本樹值，其餘基準內容一律不動。任一不成立即非 0 退出、不寫基準。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/migrate_fftfmeta_baseline.py <改前程式樹> [--write] [--receipt <路徑>]
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BASELINE = REPO / "tests" / "_golden" / "fftfmeta" / "baseline.json"
DUMP = Path(__file__).resolve().parent / "fftfmeta_dump.py"
PY = REPO / "venv" / "bin" / "python"
ORIGINAL_REV = "02350721^"  # FF-STAT 實作動工前（b1 之前）


def _dump(tree: Path, ref: str, out: Path) -> dict:
    subprocess.run([str(PY), str(DUMP), str(tree), ref, str(out)], check=True, capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))


def _apply_schema_changes(obj):
    """FF-STAT 累計之平穩化設定 schema 變更（只作用於前處理設定 dict：同時含 calibration_bars 與 adf_differencing 者）。"""
    if isinstance(obj, list):
        return [_apply_schema_changes(v) for v in obj]
    if not isinstance(obj, dict):
        return obj
    out = {k: _apply_schema_changes(v) for k, v in obj.items() if k != "adf_safe_skip"}
    if "calibration_bars" in out and isinstance(out.get("adf_differencing"), dict):
        out["adf_differencing"] = {k: v for k, v in out["adf_differencing"].items() if k != "sample_size"}
        out.setdefault("calibration_bars_by_timeframe", {})
    return out


def main() -> int:
    old_tree, write = Path(sys.argv[1]).resolve(), "--write" in sys.argv
    receipt_path = (Path(sys.argv[sys.argv.index("--receipt") + 1]) if "--receipt" in sys.argv
                    else REPO / "handoffs" / "run_receipts" / "20260925-ffstat-fftfmeta-baseline-migration.json")
    sys.path.insert(0, str(REPO))
    from tests.feature_engineering import fftfmeta_golden_helpers as g

    original = json.loads(subprocess.run(["git", "show", f"{ORIGINAL_REV}:tests/_golden/fftfmeta/baseline.json"],
                                         cwd=REPO, check=True, capture_output=True, text=True).stdout)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    receipt = {"old_tree": str(old_tree), "original_rev": ORIGINAL_REV,
               "schema_changes": ["drop preprocessing.adf_safe_skip", "drop preprocessing.adf_differencing.sample_size",
                                  "add preprocessing.calibration_bars_by_timeframe={}"],
               "references": {}}
    for ref, frozen in original["references"].items():
        old = _dump(old_tree, ref, Path(f"/tmp/fftfmeta_old_{ref}.json"))
        new = _dump(REPO, ref, Path(f"/tmp/fftfmeta_new_{ref}.json"))
        checks = {
            "old_reproduces_original_frozen": old["manifest_sha"] == frozen["manifest_stripped_sha256"]
            and old["task_sha"] == frozen["task_stripped_sha256"],
            "features_unchanged": old["groups"] == new["groups"] == frozen["groups"]
            and old["group_files_sha256"] == new["group_files_sha256"] == frozen["group_files_sha256"],
        }
        for part in ("manifest", "task"):
            transformed = json.loads(json.dumps(_apply_schema_changes(old[part])).replace(
                old["config_hash"], new["config_hash"]))
            checks[f"{part}_only_schema_diff"] = g.canonical_json(transformed) == g.canonical_json(new[part])
        receipt["references"][ref] = {
            "checks": checks, "old_config_hash": old["config_hash"], "new_config_hash": new["config_hash"],
            "manifest_sha": [frozen["manifest_stripped_sha256"], new["manifest_sha"]],
            "task_sha": [frozen["task_stripped_sha256"], new["task_sha"]],
        }
        if not all(checks.values()):
            print(json.dumps(receipt, indent=1, ensure_ascii=False))
            return 1
        baseline["references"][ref]["manifest_stripped_sha256"] = new["manifest_sha"]
        baseline["references"][ref]["task_stripped_sha256"] = new["task_sha"]
    print(json.dumps(receipt, indent=1, ensure_ascii=False))
    if write:
        BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("written", receipt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
