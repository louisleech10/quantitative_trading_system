"""FRAMEPATH 受影響測試閘（SPEC v20 D6、審查 r46／r47）：A 組全綠＋B／C 組逐 nodeid 照跑、完整性機械比對、
失敗逐項與錨點碼態比對歸屬。

流程（單組串行）：
1. A 組＝本票具名驗收（`A_GROUP_BY_PHASE`），須全部 passed（不適用既有紅豁免）。
2. B／C 組應跑集合 E：manifest `affected_tests phase=<P>` 所列檔扣 A 組，逐檔 `pytest --collect-only -q`（rc 須 0，
   否則拒跑）；C 組（`affected_groups phase=<P> C=…`）排在 B 組之後，只影響順序。
3. 逐檔執行寫 junit xml；結果檔附狀態指紋（repo HEAD、工作樹相對 HEAD 之完整 diff、未追蹤檔清單、該測試檔內容、
   pytest 參數、phase），指紋相同且結果完整才沿用（中斷後接續），否則重跑；pytest rc 非 0／1 ⇒ 該檔視為未完成。
4. 非綠 nodeid 於錨點工作樹重跑同 nodeid；錨點＝本票最晚一筆實作許可之 round_start_head（`.claude/gate/audit.log`，
   與處置驗證器 ⓪ 同一函式），工作樹由本腳本自建（或 `--anchor-worktree` 指定）並驗：HEAD＝錨點、工作樹乾淨、
   生產碼（momentum／api／config）與碼態錨點 6e07e0ad 相同。結果類別＋例外型別＋訊息首行（只遮暫存路徑與位址、
   數字不遮）皆同者歸「HEAD 既有紅」，其餘一律「本批造成」。
5. 通過＝A 組全綠、E 完整、無多出之 nodeid、本批造成＝0。收據寫 `--receipt`。

用法（每批一行；`--anchor-worktree` 省略則自建於系統暫存）：
  PYTHONPATH=. venv/bin/python scripts/framepath_affected_gate.py --phase 1 \
      --receipt handoffs/run_receipts/framepath-b1-affected.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
MANIFEST_REL = "docs/manifests/FRAMEPATH.json"
CODE_ANCHOR = "6e07e0ad"
PRODUCTION_ROOTS = ("momentum", "api", "config")
A_FILES = (
    "tests/feature_engineering/test_framepath_disposition.py",
    "tests/feature_engineering/test_framepath_cgsa_only.py",
    "tests/feature_engineering/test_framepath_invariance.py",
    "tests/api/test_framepath_api_h5.py",
)
A_GROUP = A_FILES  # 自 B／C 扣除之集合（不分 phase）
A_GROUP_BY_PHASE = {1: A_FILES[:3], 2: A_FILES, 3: A_FILES}
PYTEST_FLAGS = ("-q", "-p", "no:cacheprovider", "-o", "log_cli=false", "--log-level=WARNING", "--tb=short")
RUN_RC_OK = (0, 1)  # pytest：0 全過、1 有測試失敗；其餘（中斷、內部錯誤、用法、無測試）＝未完成


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
    """完整性與歸屬（純函式）。回傳 {"missing", "unexpected", "caused", "head_red", "passed"}；通過條件見 `verdict`。"""
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


def verdict(result: Mapping[str, Sequence[str]], a_failures: Sequence[str], incomplete_files: Sequence[str]) -> bool:
    """通過＝A 組全綠、無未完成檔、無缺、無多出、本批造成＝0（純函式）。"""
    return not (a_failures or incomplete_files or result["missing"] or result["unexpected"] or result["caused"])


def state_key(repo: Path, test_file: str, phase: int) -> str:
    """結果檔沿用之狀態指紋：HEAD、相對 HEAD 之完整 diff、未追蹤檔清單、測試檔內容、pytest 參數、phase。"""
    h = hashlib.sha256()
    for part in (
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "diff", "--binary", "HEAD"),
        _git(repo, "ls-files", "--others", "--exclude-standard"),
        (repo / test_file).read_bytes().decode("utf-8", "replace") if (repo / test_file).is_file() else "",
        json.dumps(PYTEST_FLAGS), str(phase),
    ):
        h.update(part.encode("utf-8", "replace"))
        h.update(b"\0")
    return h.hexdigest()


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} rc={proc.returncode}：{proc.stderr[-300:]}")
    return proc.stdout


def _pytest(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pytest", *args], cwd=cwd, env=dict(env), capture_output=True,
                          text=True)


def collect(test_file: str, cwd: Path, env: Mapping[str, str]) -> List[str]:
    proc = _pytest(["--collect-only", "-q", "-p", "no:cacheprovider", test_file], cwd, env)
    ids = [ln.strip() for ln in proc.stdout.splitlines() if ln.startswith(test_file + "::")]
    if proc.returncode != 0 or not ids:
        raise GateError(f"{test_file} 收集失敗或為空 rc={proc.returncode}：{proc.stdout[-500:]}{proc.stderr[-500:]}")
    return ids


def run_file(test_file: str, xml_path: Path, cwd: Path, env: Mapping[str, str],
             nodeids: Optional[Sequence[str]] = None) -> Tuple[int, Dict[str, Dict[str, str]]]:
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    if xml_path.exists():
        xml_path.unlink()
    proc = _pytest([*PYTEST_FLAGS, f"--junitxml={xml_path}", *(nodeids or [test_file])], cwd, env)
    res = junit_results(xml_path.read_text(encoding="utf-8"), test_file) if xml_path.is_file() else {}
    return proc.returncode, res


def resolve_anchor() -> str:
    """本票最晚一筆實作許可之 round_start_head（與處置驗證器 ⓪ 同一函式）。"""
    from tests.feature_engineering.test_framepath_disposition import AUDIT_REL, approval_anchor

    anchor = approval_anchor((REPO / AUDIT_REL).read_text(encoding="utf-8", errors="replace").splitlines())
    if not anchor:
        raise GateError("審計紀錄無本票實作許可（impl_token_issued）")
    return anchor


def _benign_status(line: str) -> bool:
    """錨點工作樹乾淨判定之封閉豁免：本腳本建立之 `data_cache` symlink（未追蹤），與已追蹤之 `__pycache__/` 位元組碼／
    numba 快取（任一測試執行即改寫；同處置驗證器⑤⑦之過濾）。其餘任何改動或未追蹤檔皆不乾淨。"""
    path = line[3:]
    return line == "?? data_cache" or "/__pycache__/" in path


def verify_anchor_worktree(wt: Path, anchor: str) -> None:
    """錨點工作樹：HEAD＝錨點、工作樹乾淨（無追蹤檔改動、無未追蹤檔）、生產碼與碼態錨點相同。"""
    head = _git(wt, "rev-parse", "HEAD").strip()
    if head != anchor:
        raise GateError(f"錨點工作樹 HEAD {head[:8]} ≠ 本票實作許可錨點 {anchor[:8]}")
    dirty = [ln for ln in _git(wt, "status", "--porcelain").splitlines() if ln.strip() and not _benign_status(ln)]
    if dirty:
        raise GateError(f"錨點工作樹不乾淨：{dirty[:10]}")
    prod = [p for p in _git(wt, "diff", "--name-only", CODE_ANCHOR, "HEAD", "--", *PRODUCTION_ROOTS).splitlines()
            if p and "/__pycache__/" not in p]
    if prod:
        raise GateError(f"錨點之生產碼與碼態錨點 {CODE_ANCHOR} 不同：{prod[:10]}")


def make_anchor_worktree(anchor: str) -> Path:
    wt = Path(tempfile.mkdtemp(prefix="framepath_anchor_")) / "wt"
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", str(wt), anchor], check=True,
                   capture_output=True)
    return wt


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phase", type=int, required=True, choices=sorted(A_GROUP_BY_PHASE))
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--out", default=None, help="junit 暫存目錄（預設系統暫存下固定名，供接續）")
    ap.add_argument("--anchor-worktree", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out or Path(tempfile.gettempdir()) / f"framepath_affected_b{args.phase}").resolve()
    anchor = resolve_anchor()
    anchor_wt = Path(args.anchor_worktree).resolve() if args.anchor_worktree else make_anchor_worktree(anchor)
    verify_anchor_worktree(anchor_wt, anchor)
    if not (anchor_wt / "data_cache").exists():
        (anchor_wt / "data_cache").symlink_to(REPO / "data_cache")
    env = dict(os.environ, FRAMEPATH_PHASE=str(args.phase), PYTHONPATH=str(REPO))
    anchor_env = dict(os.environ, PYTHONPATH=str(anchor_wt))
    manifest = json.loads((REPO / MANIFEST_REL).read_text(encoding="utf-8"))
    b_group, c_group = manifest_groups(manifest, args.phase)

    a_failures: List[str] = []
    a_results: Dict[str, Dict[str, str]] = {}
    for f in A_GROUP_BY_PHASE[args.phase]:
        ids = collect(f, REPO, env)
        rc, res = run_file(f, out / "a_junit" / (f.replace("/", "_") + ".xml"), REPO, env)
        a_results.update(res)
        a_failures += [n for n in ids if res.get(n, {}).get("outcome") != "passed"]
        if rc not in RUN_RC_OK:
            a_failures.append(f"{f}（pytest rc={rc}）")

    expected: List[str] = []
    batch: Dict[str, Dict[str, str]] = {}
    per_file: Dict[str, Dict[str, object]] = {}
    incomplete: List[str] = []
    for f in b_group + c_group:
        ids = collect(f, REPO, env)
        expected += ids
        xml = out / "junit" / (f.replace("/", "_") + ".xml")
        meta = xml.with_suffix(".meta.json")
        key = state_key(REPO, f, args.phase)
        res: Dict[str, Dict[str, str]] = {}
        rc: Optional[int] = None
        if xml.is_file() and meta.is_file():
            m = json.loads(meta.read_text(encoding="utf-8"))
            if m.get("state_key") == key and m.get("rc") in RUN_RC_OK:
                res, rc = junit_results(xml.read_text(encoding="utf-8"), f), m["rc"]
        if rc is None or set(ids) - set(res):
            rc, res = run_file(f, xml, REPO, env)
            meta.write_text(json.dumps({"state_key": key, "rc": rc, "file": f}), encoding="utf-8")
        if rc not in RUN_RC_OK or set(ids) - set(res):
            incomplete.append(f)
        batch.update(res)
        per_file[f] = {"expected": len(ids), "results": len(set(ids) & set(res)), "rc": rc}

    not_passed = [n for n in expected if n in batch and batch[n]["outcome"] != "passed"]
    anchor_res: Dict[str, Dict[str, str]] = {}
    for f in dict.fromkeys(n.split("::", 1)[0] for n in not_passed):
        ids = [n for n in not_passed if n.startswith(f + "::")]
        if (anchor_wt / f).is_file():
            _, res = run_file(f, out / "anchor_junit" / (f.replace("/", "_") + ".xml"), anchor_wt, anchor_env, ids)
            anchor_res.update(res)
    result = classify(expected, batch, anchor_res)
    passed = verdict(result, a_failures, incomplete)
    receipt = {
        "spec": "docs/FRAMEPATH_SPEC.md v20 D6", "phase": args.phase, "repo_head": _git(REPO, "rev-parse", "HEAD").strip(),
        "anchor": anchor, "anchor_worktree": str(anchor_wt), "groups": {"A": list(A_GROUP_BY_PHASE[args.phase]),
                                                                        "B": b_group, "C": c_group},
        "a_failures": a_failures, "incomplete_files": incomplete, "per_file": per_file,
        "expected_count": len(expected), "result_count": len(set(expected) & set(batch)),
        **result,
        "head_red_identity": {n: list(failure_identity(batch[n])) for n in result["head_red"]},
        "caused_detail": {n: {"batch": list(failure_identity(batch[n])),
                              "anchor": list(failure_identity(anchor_res[n])) if n in anchor_res else None}
                          for n in result["caused"]},
        "pass": passed,
    }
    Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"FRAMEPATH affected gate：A_fail={len(a_failures)} expected={len(expected)} incomplete={len(incomplete)} "
          f"missing={len(result['missing'])} unexpected={len(result['unexpected'])} caused={len(result['caused'])} "
          f"head_red={len(result['head_red'])} pass={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
