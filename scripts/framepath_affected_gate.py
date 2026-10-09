"""FRAMEPATH 受影響測試閘（SPEC v20 D6、審查 r46）：逐 nodeid 照跑、完整性機械比對、失敗逐項與錨點碼態比對歸屬。

流程（單組串行）：
1. 應跑集合 E：對 manifest `affected_tests phase=<P>` 所列檔（扣除 A 組本票具名驗收，A 組另由 gate_cmd 直跑）逐檔
   `pytest --collect-only -q`；C 組（manifest `affected_groups phase=<P> C=…` 所列）排在 B 組之後，只影響順序。
2. 逐檔執行，寫 junit xml 至 `<out>/junit/`；已完整（xml 之 testcase 集合＝該檔應跑集合）之檔於重跑時略過——中斷後可
   接續至完成，不設「資源中止」過閘類別。
3. 本批失敗／錯誤／略過之 nodeid，於 `--anchor-worktree`（錨點碼態乾淨工作樹）以同一 pytest 重跑該 nodeid；歸屬：
   - 「HEAD 既有紅」：錨點亦為同一結果類別，且失敗身分（例外型別＋正規化之訊息首行）完全相同；
   - 其餘一律「本批造成」（含錨點綠、錨點結果類別或身分不同、錨點無此 nodeid）。
4. 通過條件：E 中每個 nodeid 皆有結果（完整）且「本批造成」＝0。收據寫 `--receipt`。

用法：
  PYTHONPATH=. venv/bin/python scripts/framepath_affected_gate.py --phase 1 --out <dir> --receipt <json> \
      --anchor-worktree <乾淨錨點工作樹>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
MANIFEST_REL = "docs/manifests/FRAMEPATH.json"
A_GROUP = (
    "tests/feature_engineering/test_framepath_disposition.py",
    "tests/feature_engineering/test_framepath_cgsa_only.py",
    "tests/feature_engineering/test_framepath_invariance.py",
    "tests/api/test_framepath_api_h5.py",
)
PYTEST_FLAGS = ("-q", "-p", "no:cacheprovider", "-o", "log_cli=false", "--log-level=WARNING", "--tb=short")
OUTCOMES = ("passed", "failed", "error", "skipped")


class GateError(RuntimeError):
    """閘之前置不成立（具名拒跑）。"""


def manifest_groups(manifest: Mapping, phase: int) -> Tuple[List[str], List[str]]:
    """(B 組, C 組)：affected_tests phase=P 扣除 A 組；C 組＝affected_groups phase=P C=… 所列（須為 affected 之子集）。"""
    rows = manifest["batch_card"]["risk_mitigation"]
    affected = _row_paths(rows, f"affected_tests phase={phase} ")
    c_rows = [r for r in rows if r.startswith(f"affected_groups phase={phase} C=")]
    if len(c_rows) != 1:
        raise GateError(f"manifest 缺或重複 affected_groups phase={phase} C=…")
    c_group = [p for p in c_rows[0].split("C=", 1)[1].split() if p]
    stray = sorted(set(c_group) - set(affected))
    if stray:
        raise GateError(f"C 組含非 affected_tests 之檔：{stray}")
    rest = [p for p in affected if p not in A_GROUP]
    return [p for p in rest if p not in c_group], [p for p in rest if p in c_group]


def _row_paths(rows: Sequence[str], prefix: str) -> List[str]:
    hits = [r for r in rows if r.startswith(prefix)]
    if len(hits) != 1:
        raise GateError(f"manifest 缺或重複 {prefix.strip()}")
    return [p for p in hits[0][len(prefix):].split() if p]


def junit_results(xml_text: str, test_file: str) -> Dict[str, Dict[str, str]]:
    """junit xml → {nodeid: {"outcome", "type", "message"}}；nodeid 由 classname（模組點路徑＋類別）與 name 重建。"""
    module = test_file[:-3].replace("/", ".")
    out: Dict[str, Dict[str, str]] = {}
    for case in ET.fromstring(xml_text).iter("testcase"):
        cls = case.get("classname", "")
        if not (cls == module or cls.startswith(module + ".")):
            continue
        inner = cls[len(module):].lstrip(".")
        nodeid = "::".join([test_file, *[p for p in inner.split(".") if p], case.get("name", "")])
        outcome, etype, msg = "passed", "", ""
        for tag in ("failure", "error", "skipped"):
            el = case.find(tag)
            if el is not None:
                outcome = "failed" if tag == "failure" else tag
                etype = el.get("type", "") or ""
                msg = el.get("message", "") or (el.text or "")
                break
        out[nodeid] = {"outcome": outcome, "type": etype, "message": msg}
    return out


_MASKS = (
    (re.compile(r"/(?:private/)?(?:var|tmp)/[^\s'\"]+"), "<tmp>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<hex>"),
)


def failure_identity(result: Mapping[str, str]) -> Tuple[str, str, str]:
    """(結果類別, 例外型別, 正規化訊息首行)；只遮暫存路徑與記憶體位址（每次執行必不同之非語意差異）。數字不遮：
    同一既有紅測試之數值改變即視為本批造成（寧可誤報須人工判讀，不得吞掉數值回歸）。"""
    first = (result.get("message") or "").strip().splitlines()[0] if (result.get("message") or "").strip() else ""
    for pat, rep in _MASKS:
        first = pat.sub(rep, first)
    return result.get("outcome", ""), result.get("type", "") or "", first


def classify(expected: Iterable[str], batch: Mapping[str, Mapping[str, str]],
             anchor: Mapping[str, Mapping[str, str]]) -> Dict[str, object]:
    """完整性與歸屬（純函式）。回傳 {"missing", "unexpected", "caused", "head_red", "passed"}；通過＝missing、caused 皆空。"""
    exp = list(dict.fromkeys(expected))
    missing = [n for n in exp if n not in batch]
    unexpected = sorted(set(batch) - set(exp))
    caused, head_red, passed = [], [], []
    for n in exp:
        if n not in batch:
            continue
        res = batch[n]
        if res.get("outcome") == "passed":
            passed.append(n)
            continue
        ref = anchor.get(n)
        if ref is not None and failure_identity(ref) == failure_identity(res):
            head_red.append(n)
        else:
            caused.append(n)
    return {"missing": missing, "unexpected": unexpected, "caused": caused, "head_red": head_red, "passed": passed}


def _pytest(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pytest", *args], cwd=cwd, env=dict(env), capture_output=True,
                          text=True)


def collect(test_file: str, cwd: Path, env: Mapping[str, str]) -> List[str]:
    proc = _pytest(["--collect-only", "-q", "-p", "no:cacheprovider", test_file], cwd, env)
    ids = [ln.strip() for ln in proc.stdout.splitlines() if ln.startswith(test_file + "::")]
    if not ids:
        raise GateError(f"{test_file} 收集為空或失敗 rc={proc.returncode}：{proc.stdout[-500:]}{proc.stderr[-500:]}")
    return ids


def run_file(test_file: str, xml_path: Path, cwd: Path, env: Mapping[str, str],
             nodeids: Optional[Sequence[str]] = None) -> Dict[str, Dict[str, str]]:
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    _pytest([*PYTEST_FLAGS, f"--junitxml={xml_path}", *(nodeids or [test_file])], cwd, env)
    if not xml_path.is_file():
        return {}
    return junit_results(xml_path.read_text(encoding="utf-8"), test_file)


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--anchor-worktree", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out).resolve()
    anchor_wt = Path(args.anchor_worktree).resolve()
    if not (anchor_wt / ".git").exists():
        raise GateError(f"--anchor-worktree 非 git 工作樹：{anchor_wt}")
    env = dict(os.environ, FRAMEPATH_PHASE=str(args.phase), PYTHONPATH=str(REPO))
    anchor_env = dict(os.environ, PYTHONPATH=str(anchor_wt))
    manifest = json.loads((REPO / MANIFEST_REL).read_text(encoding="utf-8"))
    b_group, c_group = manifest_groups(manifest, args.phase)
    expected: List[str] = []
    batch: Dict[str, Dict[str, str]] = {}
    per_file: Dict[str, Dict[str, int]] = {}
    for f in b_group + c_group:
        ids = collect(f, REPO, env)
        expected += ids
        xml = out / "junit" / (f.replace("/", "_") + ".xml")
        res = junit_results(xml.read_text(encoding="utf-8"), f) if xml.is_file() else {}
        if set(ids) - set(res):  # 未完整 ⇒ 重跑（接續至完成）
            res = run_file(f, xml, REPO, env)
        batch.update(res)
        per_file[f] = {"expected": len(ids), "results": len(set(ids) & set(res))}
    not_passed = [n for n in expected if n in batch and batch[n]["outcome"] != "passed"]
    anchor: Dict[str, Dict[str, str]] = {}
    for f in dict.fromkeys(n.split("::", 1)[0] for n in not_passed):
        ids = [n for n in not_passed if n.startswith(f + "::")]
        if (anchor_wt / f).is_file():
            anchor.update(run_file(f, out / "anchor_junit" / (f.replace("/", "_") + ".xml"), anchor_wt, anchor_env, ids))
    result = classify(expected, batch, anchor)
    receipt = {
        "spec": "docs/FRAMEPATH_SPEC.md v20 D6", "phase": args.phase, "repo_head": _head(REPO),
        "anchor_worktree_head": _head(anchor_wt), "groups": {"B": b_group, "C": c_group}, "per_file": per_file,
        "expected_count": len(expected), "result_count": len(set(expected) & set(batch)),
        **result,
        "head_red_identity": {n: list(failure_identity(batch[n])) for n in result["head_red"]},
        "caused_detail": {n: {"batch": list(failure_identity(batch[n])),
                              "anchor": list(failure_identity(anchor[n])) if n in anchor else None}
                          for n in result["caused"]},
        "pass": not result["missing"] and not result["caused"],
    }
    Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"FRAMEPATH affected gate：expected={len(expected)} missing={len(result['missing'])} "
          f"caused={len(result['caused'])} head_red={len(result['head_red'])} pass={receipt['pass']}")
    return 0 if receipt["pass"] else 1


def _head(path: Path) -> str:
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
