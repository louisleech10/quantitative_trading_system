"""FF-STAT：FF-TFMETA golden 基準之有證據遷移（刪 `preprocessing.adf_safe_skip` 設定段 ⇒ config_hash 改變）。

逐情境：①以改前程式樹重跑，證其去除允許路徑之 manifest／task sha 等於凍結基準（改前可重現）；
②以本樹重跑；③證「改前輸出刪去 `adf_safe_skip` 鍵、把改前 config_hash 字串換成改後值」後與本樹輸出逐位元組相等，
且群組逐欄 hash 與群組檔名集合不變（特徵值零變動）；④三者皆成立才把基準之兩個 sha 欄改為本樹值，
其餘基準內容（含 FF-TFMETA 動工前之允許路徑實值）一律不動。任一不成立即非 0 退出、不寫基準。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/migrate_fftfmeta_baseline.py <改前程式樹> [--write]
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BASELINE = REPO / "tests" / "_golden" / "fftfmeta" / "baseline.json"
DUMP = Path(__file__).resolve().parent / "fftfmeta_dump.py"
PY = REPO / "venv" / "bin" / "python"


def _dump(tree: Path, ref: str, out: Path) -> dict:
    subprocess.run([str(PY), str(DUMP), str(tree), ref, str(out)], check=True, capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))


def _drop_key(obj, key):
    if isinstance(obj, dict):
        return {k: _drop_key(v, key) for k, v in obj.items() if k != key}
    if isinstance(obj, list):
        return [_drop_key(v, key) for v in obj]
    return obj


def main() -> int:
    old_tree, write = Path(sys.argv[1]).resolve(), "--write" in sys.argv
    sys.path.insert(0, str(REPO))
    from tests.feature_engineering import fftfmeta_golden_helpers as g

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    tmp = Path(sys.argv[0]).resolve().parent
    receipt = {"old_tree": str(old_tree), "references": {}}
    for ref, frozen in baseline["references"].items():
        old = _dump(old_tree, ref, Path(f"/tmp/fftfmeta_old_{ref}.json"))
        new = _dump(REPO, ref, Path(f"/tmp/fftfmeta_new_{ref}.json"))
        checks = {
            "old_reproduces_frozen": old["manifest_sha"] == frozen["manifest_stripped_sha256"]
            and old["task_sha"] == frozen["task_stripped_sha256"],
            "features_unchanged": old["groups"] == new["groups"] == frozen["groups"]
            and old["group_files_sha256"] == new["group_files_sha256"] == frozen["group_files_sha256"],
        }
        for part in ("manifest", "task"):
            transformed = json.loads(json.dumps(_drop_key(old[part], "adf_safe_skip")).replace(
                old["config_hash"], new["config_hash"]))
            checks[f"{part}_only_schema_diff"] = g.canonical_json(transformed) == g.canonical_json(new[part])
        receipt["references"][ref] = {
            "checks": checks, "old_config_hash": old["config_hash"], "new_config_hash": new["config_hash"],
            "manifest_sha": [frozen["manifest_stripped_sha256"], new["manifest_sha"]],
            "task_sha": [frozen["task_stripped_sha256"], new["task_sha"]],
        }
        if not all(checks.values()):
            print(json.dumps(receipt, indent=1))
            return 1
        frozen["manifest_stripped_sha256"], frozen["task_stripped_sha256"] = new["manifest_sha"], new["task_sha"]
    print(json.dumps(receipt, indent=1, ensure_ascii=False))
    if write:
        BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        out = REPO / "handoffs" / "run_receipts" / "20260925-ffstat-fftfmeta-baseline-migration.json"
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("written", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
