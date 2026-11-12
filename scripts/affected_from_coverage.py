"""依逐測試覆蓋資料（pytest-cov `--cov-context=test`）算執行到改動之 Python 程式的 nodeid（TEST_SELECTION §5 過渡工具）。

補讀檔追蹤（`scripts/readtrace_plugin.py`）之盲區：測試以 import 執行改動之 .py，不會「讀檔」。
判定（業界同類 pytest-testmon 之方法級指紋、Ekstazi）：
- 改動行＝`git diff -U0 HEAD` 新側行（純刪除 hunk 取其前後各一行；未追蹤新檔＝全部行），多行敘述之續行映射至首行；
- 改動行在函式內（含簽名、預設值）⇒ 依賴單位＝整個最內層函式：執行到該函式任一行之 nodeid 受影響；
- 函式外（模組／類別層級）之改動：執行到該行之 nodeid 受影響；只在 import／收集期執行（context 空字串）者另列
  `<前綴>_import_lines.txt`，須逐行判其使用者（如類別欄位、設定欄位之讀取端）；
- context `<nodeid>|setup` 命中 ⇒ 同檔全部 nodeid 列入 `<前綴>_setup_files.tsv`（module／session fixture 只於第一條
  測試 setup 執行，同檔他測試共用其結果）。
不涵蓋：子行程內執行（由讀檔追蹤之子行程命令列判）；未納入覆蓋跑之測試。

用法：`venv/bin/python -m pytest --cov --cov-config=<rc：include 限改動 .py> --cov-context=test --cov-report= <測試>`，
再 `venv/bin/python scripts/affected_from_coverage.py <coverage 資料檔> <改動 .py 清單> <輸出前綴> [<readtrace.jsonl>...]`
（同跑加 `-p scripts.readtrace_plugin` 則可附其紀錄，setup 命中者依 `shared` 擴散給共用同一 fixture 之他檔測試）
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from coverage import CoverageData
from coverage.parser import PythonParser

REPO = Path(__file__).resolve().parents[1]


def changed_lines(root: Path, path: str) -> Set[int]:
    """改動行（新側行號）；未追蹤新檔 ⇒ 全部行。"""
    tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", path],
                             capture_output=True).returncode == 0
    if not tracked:
        return set(range(1, len((root / path).read_text(encoding="utf-8").splitlines()) + 1))
    diff = subprocess.run(["git", "-C", str(root), "diff", "-U0", "HEAD", "--", path],
                          capture_output=True, text=True, check=True).stdout
    out: Set[int] = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, count = int(m.group(1)), int(m.group(2) or "1")
        out.update({start, start + 1} if count == 0 else range(start, start + count))
    return out


def first_lines(source_path: Path, lines: Iterable[int]) -> Set[int]:
    """改動行 → 其所屬敘述之首行（覆蓋紀錄之行號）。"""
    parser = PythonParser(filename=str(source_path))
    parser.parse_source()
    return {parser.first_line(x) for x in lines}


def dependency_lines(source_path: Path, lines: Iterable[int]) -> Set[int]:
    """改動行 → 依賴行集合：續行映射至敘述首行；在函式內者擴為整個最內層函式之行。"""
    funcs: List[Tuple[int, int]] = [
        (n.lineno, n.end_lineno) for n in ast.walk(ast.parse(source_path.read_text(encoding="utf-8")))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    out: Set[int] = set()
    for ln in first_lines(source_path, lines):
        inner = [f for f in funcs if f[0] <= ln <= f[1]]
        if inner:
            a, b = min(inner, key=lambda f: f[1] - f[0])
            out.update(range(a, b + 1))
        else:
            out.add(ln)
    return out


def affected(data_file: str, changed: List[str], root: Path = REPO,
             shared: Dict[str, Set[str]] = None) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]],
                                                          Dict[str, Set[int]], List[str]]:
    """回 (nodeid→理由集, 測試檔→setup 命中理由, 改動檔→只在 import 期執行之改動行〔敘述首行〕, 未量測之改動檔)。
    `shared`（nodeid→非 function 範圍 fixture 集，取自 readtrace 紀錄）給定時，setup 命中者之依賴擴散給共用同一
    fixture 之全部 nodeid（理由 `shared-fixture:<命中者>`；跨檔 session fixture 亦涵蓋）。"""
    cd = CoverageData(basename=data_file)
    cd.read()
    measured = {}
    for f in cd.measured_files():
        try:
            measured[str(Path(f).resolve().relative_to(root.resolve()))] = f
        except ValueError:
            continue
    hits: Dict[str, Set[str]] = defaultdict(set)
    setup_files: Dict[str, Set[str]] = defaultdict(set)
    import_lines: Dict[str, Set[int]] = defaultdict(set)
    missing: List[str] = []
    for rel in changed:
        if rel not in measured:
            missing.append(rel)
            continue
        raw = changed_lines(root, rel)
        raw_first = first_lines(root / rel, raw)  # 與覆蓋行號同一正規化（續行改動 ⇒ 敘述首行）
        deps = dependency_lines(root / rel, raw)
        by_line = cd.contexts_by_lineno(measured[rel])
        for ln in sorted(deps):
            for ctx in by_line.get(ln, []):
                if not ctx:
                    if ln in raw_first:
                        import_lines[rel].add(ln)
                    continue
                node, _, phase = ctx.rpartition("|")
                hits[node].add(f"{rel}:{ln}|{phase}")
                if phase == "setup":
                    setup_files[node.split("::", 1)[0]].add(f"{rel}:{ln}")
    if shared:
        for node in [n for n, r in hits.items() if any(x.endswith("|setup") for x in r)]:
            mine = shared.get(node) or set()
            for other, fx in shared.items():
                if other not in hits and mine & fx:
                    hits[other].add(f"shared-fixture:{node}")
    return hits, setup_files, import_lines, missing


def main(argv: List[str] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 3:
        print(__doc__)
        return 2
    data_file, changed_list, prefix = argv[:3]
    changed = [ln.strip() for ln in Path(changed_list).read_text(encoding="utf-8").splitlines()
               if ln.strip().endswith(".py")]
    shared: Dict[str, Set[str]] = {}
    for trace in argv[3:]:  # 選填：readtrace JSONL（取 shared 欄做共用 fixture 擴散）
        for line in Path(trace).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and isinstance(rec.get("nodeid"), str) and "shared" in rec:
                shared[rec["nodeid"]] = set(rec["shared"])
    hits, setup_files, import_lines, missing = affected(data_file, changed, shared=shared or None)
    Path(f"{prefix}_hits.tsv").write_text(
        "".join(f"{n}\t{sorted(r)[0]}\t{len(r)}\n" for n, r in sorted(hits.items())), encoding="utf-8")
    Path(f"{prefix}_setup_files.tsv").write_text(
        "".join(f"{f}\t{sorted(r)[0]}\n" for f, r in sorted(setup_files.items())), encoding="utf-8")
    Path(f"{prefix}_import_lines.txt").write_text(
        "".join(f"{f}:{','.join(map(str, sorted(ls)))}\n" for f, ls in sorted(import_lines.items())), encoding="utf-8")
    print(f"nodeids={len(hits)} setup_files={len(setup_files)} import_only_files={len(import_lines)} "
          f"unmeasured={','.join(missing) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
