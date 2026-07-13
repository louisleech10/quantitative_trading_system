#!/usr/bin/env bash
set -euo pipefail

python3 - "$@" <<'PY'
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import unquote


EXCLUDED_ROOTS = ("docs/Archived/", "handoffs/")
HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")
INLINE_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))")
REFERENCE_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\s*\[([^\]]*)\]")
REFERENCE_DEF_RE = re.compile(r'^ {0,3}\[([^\]]+)\]:\s*(?:<([^>]+)>|([^\s]+))', re.MULTILINE)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed")
    return result.stdout


def excluded(path: str) -> bool:
    normalized = path.lstrip("./")
    return any(normalized.startswith(root) for root in EXCLUDED_ROOTS)


def slug(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", text).strip().lower()
    text = re.sub(r"[`*~]", "", text)
    # GitHub 保留字內的 literal underscore，但不把 emphasis delimiter 放進 slug。
    text = re.sub(r"(?<!\w)_{1,2}(?=\S)|(?<=\S)_{1,2}(?!\w)", "", text)
    chars: list[str] = []
    for char in text:
        if char.isspace():
            chars.append("-")
        elif char in "-_" or not unicodedata.category(char).startswith(("P", "S")):
            chars.append(char)
    return "".join(chars)


def anchors(text: str) -> set[str]:
    result: set[str] = set()
    counts: Counter[str] = Counter()
    in_fence = False
    fence_char = ""
    for line in text.splitlines():
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)[0]
            if not in_fence:
                in_fence, fence_char = True, marker
            elif marker == fence_char:
                in_fence = False
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = slug(match.group(1))
        occurrence = counts[base]
        counts[base] += 1
        result.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return result


def normalize_reference(label: str) -> str:
    return " ".join(label.strip().lower().split())


def link_targets(text: str) -> list[tuple[int, str]]:
    definitions = {
        normalize_reference(match.group(1)): match.group(2) or match.group(3)
        for match in REFERENCE_DEF_RE.finditer(text)
    }
    found: list[tuple[int, str]] = []
    for match in INLINE_LINK_RE.finditer(text):
        found.append((text.count("\n", 0, match.start()) + 1, match.group(1) or match.group(2)))
    for match in REFERENCE_LINK_RE.finditer(text):
        label = match.group(2) or match.group(1)
        target = definitions.get(normalize_reference(label))
        if target:
            found.append((text.count("\n", 0, match.start()) + 1, target))
    return found


def resolve(source: str, target: str) -> tuple[str, str] | None:
    target = target.strip()
    if "#" not in target or target.startswith("#"):
        return None
    path_part, fragment = target.split("#", 1)
    if not path_part or not fragment:
        return None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", path_part) or path_part.startswith("//"):
        return None
    decoded_path = unquote(path_part).replace("\\", "/")
    joined = PurePosixPath(source).parent / decoded_path
    normalized = os.path.normpath(str(joined)).replace("\\", "/")
    return normalized.lstrip("./"), unquote(fragment).lower()


def worktree_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return None


def head_text(path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return result.stdout if result.returncode == 0 else None


def dead_links(paths: list[str], revision: str) -> set[tuple[str, int, str, str]]:
    reader = worktree_text if revision == "worktree" else head_text
    anchor_cache: dict[str, set[str] | None] = {}
    dead: set[tuple[str, int, str, str]] = set()
    for source in paths:
        text = reader(source)
        if text is None:
            continue
        for line, raw_target in link_targets(text):
            resolved = resolve(source, raw_target)
            if resolved is None:
                continue
            destination, fragment = resolved
            if destination not in anchor_cache:
                destination_text = reader(destination)
                anchor_cache[destination] = (
                    anchors(destination_text) if destination_text is not None else None
                )
            destination_anchors = anchor_cache[destination]
            if destination_anchors is None or fragment not in destination_anchors:
                dead.add((source, line, raw_target, f"{destination}#{fragment}"))
    return dead


def markdown_files(revision: str) -> list[str]:
    if revision == "head":
        paths = git("ls-tree", "-r", "--name-only", "HEAD", check=False).splitlines()
    else:
        tracked = git("ls-files", "*.md", check=False).splitlines()
        untracked = git("ls-files", "--others", "--exclude-standard", "*.md", check=False).splitlines()
        paths = tracked + untracked
    return sorted({path for path in paths if path.endswith(".md") and not excluded(path)})


def changed_files(explicit: str | None) -> list[str]:
    if explicit is not None:
        candidates = [item.strip() for item in explicit.split(",") if item.strip()]
    else:
        candidates = git("diff", "--name-only", "HEAD", "--", "*.md", check=False).splitlines()
    return sorted({path.lstrip("./") for path in candidates if path.endswith(".md") and not excluded(path)})


parser = argparse.ArgumentParser(description="Check local Markdown file#fragment links")
parser.add_argument("--files", help="comma-separated changed-file override")
args = parser.parse_args()

try:
    changed = changed_files(args.files)
    head_all = dead_links(markdown_files("head"), "head")
    current_all = dead_links(markdown_files("worktree"), "worktree")
    current_changed = dead_links(changed, "worktree")
    previous_changed = dead_links(changed, "head")
except RuntimeError as error:
    print(f"ERROR: {error}", file=sys.stderr)
    sys.exit(2)

previous_keys = {(source, raw, resolved) for source, _line, raw, resolved in previous_changed}
new_dead = {
    item for item in current_changed
    if (item[0], item[2], item[3]) not in previous_keys
}

print(f"Baseline dead links (HEAD): {len(head_all)}")
print(f"Current repo dead links: {len(current_all)}")
print(f"Delta: {len(current_all) - len(head_all):+d}")
print(f"Changed Markdown files checked: {len(changed)}")
if new_dead:
    print(f"New dead links: {len(new_dead)}")
    for source, line, raw, resolved in sorted(new_dead):
        print(f"{source}:{line}: {raw} -> {resolved}")
    sys.exit(1)
print("New dead links: 0")
PY
