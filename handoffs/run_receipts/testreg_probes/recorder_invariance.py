"""TESTREG §G 記錄器不變性基準（docs/TESTREG_SPEC.md §G、Task 1.3）：凍結與比對收據之產生器。

用法（主工作樹、repo 根；單組串行；跑完 `bash scripts/restore_golden_inventory.sh`）：
  venv/bin/python handoffs/run_receipts/testreg_probes/recorder_invariance.py freeze   # Task 1.3 動工前、記錄器未掛載之 HEAD
  venv/bin/python handoffs/run_receipts/testreg_probes/recorder_invariance.py verify   # 記錄器掛載後之同命令
收據：freeze ⇒ handoffs/run_receipts/testreg-recorder-baseline.json；verify ⇒ handoffs/run_receipts/testreg-recorder-verify.json。

收據欄（tests/registry/test_testreg_recorder.py::test_g_recorder_invariance_receipts 讀之）：
  sample（凍結清單：test_framepath_disposition.py、test_mutation_scope_extension.py、tests/api 依路徑字典序前 10 檔）、
  sample_rule（字面「tests/api 依路徑字典序前 10 檔（凍結時之 git ls-files）」）、command（argv 陣列：
  `venv/bin/python -m pytest -p no:cacheprovider -v <sample…>`）、head、recorder_loaded（本次 session 是否載入記錄器：
  以執行前後 `.testreg/ledger` 檔數差判定）、ledger_sessions_written、outcomes_sha256（排序後之「nodeid outcome」列之
  sha256）、order_sha256（-v 輸出之 nodeid 序列之 sha256）、rc、porcelain_sha256_without_testreg（`git status
  --porcelain --ignored` 去除 `.testreg/` 開頭之列後之 sha256）。執行前一律以 restore_golden_inventory.sh 還原清冊副作用。

執行位置（實作期 b1 定）：兩次執行各在一棵暫存 git worktree 內跑同一 `command`（cwd＝worktree 根；`venv`、`data_cache`
以符號連結指向主工作樹），使 ④ 之起點皆為「乾淨 checkout＋同一組連結」——主工作樹於提交前必含本批改動與他票髒檔，
字面 porcelain 不可能前後相等，且 FRAMEPATH 驗證器 ⑦ 讀工作樹改動。
  freeze：worktree＝主工作樹 HEAD（動工前、記錄器未掛載）。
  verify：worktree＝HEAD 加上記錄器掛載所需之檔（`MOUNT_PATHS`）於主工作樹之現行內容所成之暫存提交（以暫存 index＋
  `commit-tree` 建立，不入任何分支）。
  worktree 用畢以 `git worktree remove --force` 移除（本程式自建之暫存）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
BASELINE_REL = "handoffs/run_receipts/testreg-recorder-baseline.json"
VERIFY_REL = "handoffs/run_receipts/testreg-recorder-verify.json"
FIXED = ["tests/feature_engineering/test_framepath_disposition.py", "tests/governance/test_mutation_scope_extension.py"]
SAMPLE_RULE = "tests/api 依路徑字典序前 10 檔（凍結時之 git ls-files）"
LINKS = ("venv", "data_cache")
PARENT_ENV = "TESTREG_PARENT_SESSION"
_OUTCOMES = "PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS"
_LINE = re.compile(rf"^(tests/\S.*?::.*?) ({_OUTCOMES})(?:\s|$)")
_START = re.compile(r"^(tests/\S.*?::\S.*?) ?$")  # log_cli：nodeid 先單獨成列，結果字串落在 live log 之後另起一列
_CONT = re.compile(rf"^({_OUTCOMES})(?:\s|$)")
_SUMMARY = re.compile(r"^=+ (.*\d+ (?:passed|failed|error|errors|skipped|xfailed|xpassed).*) in [\d.]+s")
_SECTION = re.compile(r"^=+ (?!test session starts)[^=]+ =+$")  # 結果段後之區段標頭（FAILURES、warnings summary…）
_SUMMARY_KEYS = {"passed": "PASSED", "failed": "FAILED", "error": "ERROR", "errors": "ERROR", "skipped": "SKIPPED",
                 "xfailed": "XFAIL", "xpassed": "XPASS"}


def parse_report(stdout: str) -> Tuple[List[str], List[str], Dict[str, int]]:
    """-v 輸出 → (nodeid 序列, 「nodeid outcome」列, 摘要列計數)。同列形式與 log_cli 分列形式皆認；結果段結束（首個
    非 session-start 之 `=== … ===` 區段標頭：FAILURES、warnings summary、short test summary…）後不再配對，只讀摘要列
    ——warnings summary 之 nodeid 單列與 short summary 之 `FAILED <nodeid> - …` 不得被當成結果。"""
    seq: List[str] = []
    rows: List[str] = []
    pending: Optional[str] = None
    summary: Dict[str, int] = {}
    results_done = False
    for line in stdout.splitlines():
        if not results_done and _SECTION.match(line) and not _SUMMARY.match(line):
            results_done, pending = True, None
        if results_done:
            m = _SUMMARY.match(line)
            if m:
                for part in m.group(1).split(","):
                    n, _, word = part.strip().partition(" ")
                    key = _SUMMARY_KEYS.get(word.strip())
                    if key and n.isdigit():
                        summary[key] = summary.get(key, 0) + int(n)
            continue
        m = _LINE.match(line)
        if m:
            seq.append(m.group(1))
            rows.append(f"{m.group(1)} {m.group(2)}")
            pending = None
            continue
        m = _START.match(line)
        if m:
            pending = m.group(1)
            continue
        m = _CONT.match(line)
        if m and pending is not None:
            seq.append(pending)
            rows.append(f"{pending} {m.group(1)}")
            pending = None
            continue
        m = _SUMMARY.match(line)
        if m:
            for part in m.group(1).split(","):
                n, _, word = part.strip().partition(" ")
                key = _SUMMARY_KEYS.get(word.strip())
                if key and n.isdigit():
                    summary[key] = summary.get(key, 0) + int(n)
    return seq, rows, dict(sorted(summary.items()))


def _git(*args: str, cwd: Path = REPO, env: Optional[Dict[str, str]] = None) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} rc={proc.returncode}: {proc.stderr.strip()[:300]}")
    return proc.stdout


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sample() -> List[str]:
    """FIXED ＋ `git ls-files 'tests/api/test_*.py'` 依路徑字典序前 10 檔。"""
    api = sorted(p for p in _git("ls-files", "tests/api/test_*.py").splitlines() if p)[:10]
    return FIXED + api


def command(files: Sequence[str]) -> List[str]:
    return ["venv/bin/python", "-m", "pytest", "-p", "no:cacheprovider", "-v", *files]


def _ledger_count(root: Path) -> int:
    d = root / ".testreg" / "ledger"
    return len(list(d.glob("*.jsonl"))) if d.is_dir() else 0


def _porcelain_without_testreg(root: Path) -> List[str]:
    lines = _git("status", "--porcelain", "--ignored", cwd=root).splitlines()
    return [l for l in lines if not l[3:].lstrip('"').startswith(".testreg")]


def run_once(files: List[str], root: Path = REPO) -> Dict[str, object]:
    """於 root 執行一次並回傳收據欄（見模組說明）。"""
    subprocess.run(["bash", "scripts/restore_golden_inventory.sh"], cwd=root, check=True, capture_output=True)
    before = _ledger_count(root)
    env = {k: v for k, v in os.environ.items() if k != PARENT_ENV}
    t0 = time.time()
    proc = subprocess.run(command(files), cwd=root, capture_output=True, text=True, env=env)
    wall = round(time.time() - t0, 1)
    seq, rows, summary = parse_report(proc.stdout)
    full = Path(tempfile.mkstemp(prefix="testreg_g_full_", suffix=".txt")[1])  # 供定位差異（repo 外、不入收據比對）
    full.write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    print(f"stdout → {full}", file=sys.stderr)
    if _counts(rows) != summary:  # 解析不完整即不出收據（fail-closed）
        dump = Path(tempfile.mkstemp(prefix="testreg_g_stdout_", suffix=".txt")[1])
        dump.write_text(proc.stdout, encoding="utf-8")
        raise RuntimeError(f"-v 解析計數 {_counts(rows)} ≠ pytest 摘要 {summary}；原始輸出 {dump}")
    porcelain = _porcelain_without_testreg(root)
    written = _ledger_count(root) - before
    return {"head": _git("rev-parse", "HEAD", cwd=root).strip(), "recorder_loaded": written > 0,
            "ledger_sessions_written": written, "outcomes_sha256": _sha("\n".join(sorted(rows))),
            "order_sha256": _sha("\n".join(seq)), "rc": proc.returncode,
            "porcelain_sha256_without_testreg": _sha("\n".join(porcelain)),
            "n_report_lines": len(rows), "outcome_counts": _counts(rows),
            "non_passed": sorted(r for r in rows if not r.endswith(" PASSED")), "pytest_summary": summary, "wall_s": wall,
            "porcelain_lines": porcelain, "stdout_tail": proc.stdout.splitlines()[-3:]}


def _counts(rows: List[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        k = r.rsplit(" ", 1)[1]
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


MOUNT_PATHS = ("tests/fixtures/testreg_recorder_plugin.py", "tests/conftest.py", ".gitignore", "pytest.ini",
               "scripts/testreg.py", "tests/registry/testreg_schema.json")


def _batch_paths() -> List[str]:
    """驗證樹＝HEAD＋記錄器掛載所需之檔（記錄器本體、接入點、`.testreg/` 忽略、標記註冊、記錄器載入之 testreg.py 與
    schema）。本批其餘改動（清冊、hook 掛載、登記表與 fact_keys 等）不納入：§G 量的是記錄器之影響，混入無關改動會使
    樣本中讀這些檔之測試（如 FRAMEPATH ⑥ 讀 fact_keys）改變結果而無從歸因。"""
    return sorted(MOUNT_PATHS)


def _verify_commit() -> str:
    """HEAD ＋本批檔案於主工作樹之現行內容 ⇒ 暫存提交（暫存 index；不動主 index、不入分支）。"""
    head_paths = set(_git("ls-tree", "-r", "--name-only", "HEAD").splitlines())
    paths = [p for p in _batch_paths() if (REPO / p).exists() or p in head_paths]
    with tempfile.TemporaryDirectory(prefix="testreg_g_idx_") as d:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(d) / "index")}
        _git("read-tree", "HEAD", env=env)
        _git("update-index", "--add", "--remove", "--", *paths, env=env)
        tree = _git("write-tree", env=env).strip()
    return _git("commit-tree", tree, "-p", "HEAD", "-m", "TESTREG §G verify tree (temporary, not on any branch)").strip()


def _with_worktree(commit: str, files: List[str]) -> Dict[str, object]:
    base = Path(tempfile.mkdtemp(prefix="testreg_g_wt_"))
    wt = base / "wt"
    _git("worktree", "add", "--detach", str(wt), commit)
    try:
        for name in LINKS:
            os.symlink(REPO / name, wt / name)
        return run_once(files, wt)
    finally:
        _git("worktree", "remove", "--force", str(wt))
        try:
            base.rmdir()
        except OSError:
            pass


def main(argv: List[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("freeze", "verify"):
        print("usage: recorder_invariance.py freeze|verify", file=sys.stderr)
        return 2
    mode = argv[0]
    base_head = _git("rev-parse", "HEAD").strip()
    if mode == "freeze":
        files = sample()
        commit, tree_paths = base_head, []
    else:
        base = json.loads((REPO / BASELINE_REL).read_text(encoding="utf-8"))
        files = list(base["sample"])
        commit, tree_paths = _verify_commit(), _batch_paths()
    rec = _with_worktree(commit, files)
    out = {"schema_version": 1, "exit_code": 0, "mode": mode, "sample": files, "sample_rule": SAMPLE_RULE, "command": command(files),
           "base_head": base_head, "worktree_commit": commit, "tree_paths": tree_paths, **rec,
           "generated": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "honest_bounds": ("兩次執行各於暫存 worktree（乾淨 checkout＋venv／data_cache 連結）；porcelain 只見"
                             "被追蹤檔之狀態改變與未追蹤／被忽略路徑之出現（整個被忽略之既有目錄內新增檔不可見）；"
                             "outcome 由 -v 報告列解析（同一 nodeid 之 teardown ERROR 另成一列）")}
    dest = REPO / (BASELINE_REL if mode == "freeze" else VERIFY_REL)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{mode}: rc={rec['rc']} lines={rec['n_report_lines']} counts={rec['outcome_counts']} "
          f"recorder_loaded={rec['recorder_loaded']} wall={rec['wall_s']}s → {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
