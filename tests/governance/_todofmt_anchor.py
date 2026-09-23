"""TODOFMT 之錨點推導（L／A／W／X）——docs/TODOFMT_SPEC.md §P「生效之判定」之唯一實作。

凡需要 L、A、W 或 X 版內容之測試與一次性陣列生成，一律經本模組之函式取得（SPEC：同一函式）。

- L＝本 SPEC 中首次出現設計定案標記行之 commit（`git log -S <FREEZE_PREFIX>` 須恰一行）。
- A＝本 SPEC 中首次出現不變式行前綴之 commit。
- W＝`git rev-list --reverse L..HEAD` 中第一個「已實際掛載 hook 且實作齊備」之 commit；無則 None。
- X＝W（已存在時），否則＝工作樹。

設計定案標記行之字面前綴只定義於本檔（SPEC 說明文字不得含之）。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = "docs/TODOFMT_SPEC.md"
FREEZE_PREFIX = "TODOFMT-DESIGN-FREEZE"
INV_PREFIX = "INV || "
HOOK_CMD = "bash scripts/todofmt_write_guard.sh"
SETTINGS = ".claude/settings.json"
MANIFEST = "docs/manifests/TODOFMT.json"
MANIFEST_PATH_KEYS = ("stub_modules", "test_files", "script_acceptance", "contract_jsons")
# SPEC §P 窗口檢查 (b)：Phase 3 尾端四個具名路徑
W_TAIL = (
    "scripts/todofmt_freeze_check.sh",
    "tests/governance/test_todofmt_freeze_check.py",
    "docs/manifests/FFTFMETA.json",
    "tests/governance/test_todofmt_sample_fftfmeta.py",
)
# SPEC §P：以 jq 判定 PreToolUse 中 matcher 同時匹配 Edit 與 Write 之條目含 HOOK_CMD
_JQ_MOUNTED = (
    '[.hooks.PreToolUse // [] | .[] '
    '| select((.matcher // "") as $m | ("Edit"|test("^(" + $m + ")$")) and ("Write"|test("^(" + $m + ")$"))) '
    '| .hooks // [] | .[] | select(.command == $cmd)] | length > 0'
)


class AnchorError(AssertionError):
    """錨點推導不成立（fail-closed）。"""


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise AnchorError(f"git {' '.join(args)} 失敗：{proc.stderr.strip()}")
    return proc


def show(commit: str, path: str) -> str | None:
    """`git show <commit>:<path>`；該版不存在此檔時回 None。"""
    proc = _git("show", f"{commit}:{path}", check=False)
    return proc.stdout if proc.returncode == 0 else None


def show_bytes(commit: str, path: str) -> bytes | None:
    """`git show <commit>:<path>` 之原始位元組（不做換行轉換）；該版不存在此檔時回 None。"""
    proc = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=REPO_ROOT, capture_output=True, check=False
    )
    return proc.stdout if proc.returncode == 0 else None


def exists_at(commit: str, path: str) -> bool:
    return _git("cat-file", "-e", f"{commit}:{path}", check=False).returncode == 0


@lru_cache(maxsize=1)
def design_freeze_commit() -> str:
    """L：`git log --format=%H -S <FREEZE_PREFIX> -- SPEC` 須恰一行。"""
    lines = _git("log", "--format=%H", "-S", FREEZE_PREFIX, "--", SPEC).stdout.split()
    if len(lines) != 1:
        raise AnchorError(f"設計定案標記行之推導須恰一行，實得 {len(lines)} 行：{lines}")
    return lines[0]


@lru_cache(maxsize=1)
def invariant_anchor_commit() -> str:
    """A：本 SPEC 中首次出現不變式行前綴之 commit。"""
    lines = _git("log", "--reverse", "--format=%H", "-S", INV_PREFIX, "--", SPEC).stdout.split()
    if not lines:
        raise AnchorError("本 SPEC 之歷史中找不到不變式行前綴")
    return lines[0]


def hook_mounted(settings_text: str | None) -> bool:
    """該版 settings 之 PreToolUse 是否以同時匹配 Edit 與 Write 之 matcher 掛載 HOOK_CMD（jq 判定）。"""
    if not settings_text:
        return False
    proc = subprocess.run(
        ["jq", "-e", "--arg", "cmd", HOOK_CMD, _JQ_MOUNTED],
        input=settings_text, capture_output=True, text=True, check=False,
    )
    return proc.returncode == 0


def manifest_paths(manifest_text: str) -> list[str]:
    data = json.loads(manifest_text)
    out: list[str] = []
    for key in MANIFEST_PATH_KEYS:
        out.extend(data.get(key, []))
    return out


def implementation_complete_at(commit: str) -> bool:
    """W 之條件 (b)：本票 manifest、其四欄所列全部路徑、Phase 3 尾端四路徑皆存在於該 commit 之樹。"""
    text = show(commit, MANIFEST)
    if text is None:
        return False
    try:
        listed = manifest_paths(text)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return False
    return all(exists_at(commit, p) for p in (*listed, *W_TAIL))


@lru_cache(maxsize=1)
def effective_commit() -> str | None:
    """W：`git rev-list --reverse L..HEAD` 中首個同時滿足 (a) 實際掛載 與 (b) 實作齊備 之 commit。"""
    lo = design_freeze_commit()
    for commit in _git("rev-list", "--reverse", f"{lo}..HEAD").stdout.split():
        if hook_mounted(show(commit, SETTINGS)) and implementation_complete_at(commit):
            return commit
    return None


def read_x(path: str) -> str | None:
    """X 版內容：W 已存在時取 W，否則取工作樹。"""
    w = effective_commit()
    if w is not None:
        return show(w, path)
    p = REPO_ROOT / path
    return p.read_text(encoding="utf-8") if p.is_file() else None


def read_x_bytes(path: str) -> bytes | None:
    """X 版之原始位元組（不做換行轉換）：W 已存在時取 W，否則取工作樹。"""
    w = effective_commit()
    if w is not None:
        return show_bytes(w, path)
    p = REPO_ROOT / path
    return p.read_bytes() if p.is_file() else None


def diff_lines_vs_l(path: str) -> tuple[list[str], list[str]]:
    """相對 L 之（新增行, 刪除行）；比較端為 X（W 或工作樹）。"""
    lo = design_freeze_commit()
    w = effective_commit()
    rng = [lo, w] if w is not None else [lo]
    out = _git("diff", "--no-color", "-U0", *rng, "--", path).stdout
    added, removed = [], []
    for line in out.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])
    return added, removed


_TODO_BASENAME = re.compile(r"^[a-z0-9_]+_todo(\.[a-z0-9-]+)?\.md$")


def is_legacy_todo_style(path: str) -> bool:
    """SPEC Task 1.2 步驟 2 之樣式（casefold 後）：首段 docs、檔名 ^[a-z0-9_]+_todo(\\.[a-z0-9-]+)?\\.md$。"""
    lp = path.lower()
    return lp.startswith("docs/") and bool(_TODO_BASENAME.match(lp.rsplit("/", 1)[-1]))


def is_spec_style(path: str) -> bool:
    """`docs/` 下任一層之 `*_SPEC*.md`（casefold 後）。"""
    lp = path.lower()
    base = lp.rsplit("/", 1)[-1]
    return lp.startswith("docs/") and "_spec" in base and base.endswith(".md")


def _tree_paths(commit: str) -> list[str]:
    return _git("ls-tree", "-r", "--name-only", commit).stdout.splitlines()


def legacy_todo_paths() -> list[str]:
    """L 樹中符合 Task 1.2 步驟 2 樣式之全部路徑（正規化＝casefold，排序）。"""
    return sorted({p.lower() for p in _tree_paths(design_freeze_commit()) if is_legacy_todo_style(p)})


def legacy_spec_paths() -> list[str]:
    """L 樹中 `docs/` 下任一層全部 `*_SPEC*.md`（casefold，排序）。"""
    return sorted({p.lower() for p in _tree_paths(design_freeze_commit()) if is_spec_style(p)})


def window_additions() -> list[str]:
    """L..W（無 W 時 L..HEAD）區間內任一 commit 新增之路徑（--no-renames）。"""
    hi = effective_commit() or "HEAD"
    out = _git("log", "--no-renames", "--diff-filter=A", "--name-only", "--format=",
               f"{design_freeze_commit()}..{hi}").stdout
    return sorted({ln for ln in out.splitlines() if ln.strip()})


def literal_block(text: str, begin: str, end: str) -> list[str]:
    """取腳本中 `# BEGIN <begin>` 與 `# END <end>` 之間、單引號字串內之非空行。"""
    lines = text.splitlines()
    try:
        s = next(i for i, ln in enumerate(lines) if ln.startswith(f"# BEGIN {begin}"))
        e = next(i for i, ln in enumerate(lines) if ln.startswith(f"# END {end}"))
    except StopIteration as exc:
        raise AnchorError(f"找不到字面清單區塊：{begin}") from exc
    return [ln.strip() for ln in lines[s + 1:e] if ln.strip() and "'" not in ln]


def invariant_lines() -> list[tuple[str, str, str]]:
    """L 之本 SPEC 中行首為 INV_PREFIX 之行，拆為（項, 所屬檔, 片段）；非四欄即 AnchorError。"""
    text = show(design_freeze_commit(), SPEC)
    if text is None:
        raise AnchorError("L 中不存在本 SPEC")
    rows: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if not line.startswith(INV_PREFIX):
            continue
        parts = line.split(" || ")
        if len(parts) != 4:
            raise AnchorError(f"不變式行不為四欄：{line!r}")
        rows.append((parts[1], parts[2], parts[3]))
    return rows


if __name__ == "__main__":
    # 一次性陣列生成（於 W 寫入 hook 與 gate.sh 之字面清單）：
    #   venv/bin/python -m tests.governance._todofmt_anchor legacy-todos|legacy-specs
    _cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if _cmd == "legacy-todos":
        print("\n".join(legacy_todo_paths()))
    elif _cmd == "legacy-specs":
        print("\n".join(legacy_spec_paths()))
    else:
        print("用法: python -m tests.governance._todofmt_anchor legacy-todos|legacy-specs", file=sys.stderr)
        sys.exit(2)
