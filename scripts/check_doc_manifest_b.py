#!/usr/bin/env python3
"""批次 B 文檔 disposition manifest 驗證器。"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


DEV_SOURCE_NAME = "DEVELOPMENT_GUIDE.md"
ARCH_SOURCE_NAME = "ARCHITECTURE.md"
DEV_SCOPE_HEADINGS = {
    "First Principle思考和Ultra Think三步驟流程",
    "代碼質量規範",
    "日誌規範",
    "錯誤處理規範",
    "LLM Coding規範",
    "性能優化規範",
    "Python開發規範",
    "前端開發規範",
    "註釋規範",
}
ARCH_SCOPE_HEADINGS = {"解耦架構原則"}
HEADING_RE = re.compile(r"^(#{1,6}) (.+?)\s*$")
FENCE_RE = re.compile(r"^```([^`]*)\s*$")


@dataclass(frozen=True)
class Heading:
    line_index: int
    level: int
    text: str
    path: tuple[str, ...]


@dataclass(frozen=True)
class Fence:
    start: int
    end: int | None
    path: tuple[str, ...]


@dataclass(frozen=True)
class ParseResult:
    headings: tuple[Heading, ...]
    fences: tuple[Fence, ...]
    nested_errors: int
    unclosed: int


@dataclass(frozen=True)
class Block:
    block_id: str
    heading: str
    kind: str
    start_line: int
    end_line: int
    content: str
    content_hash: str


@dataclass(frozen=True)
class ManifestRow:
    block_id: str
    heading: str
    content_hash: str
    line_span: str
    disposition: str
    carrier: str
    reason: str


def normalize_content(content: str) -> str:
    """正規化換行與行尾空白，並保留唯一檔尾換行。"""

    unified = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in unified.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def content_hash(content: str) -> str:
    """回傳 manifest 使用的 SHA-256。"""

    return hashlib.sha256(normalize_content(content).encode("utf-8")).hexdigest()


def parse_markdown(text: str) -> ParseResult:
    """以 lang-push 語意解析 fence 與 fence 外 heading。"""

    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    stack: list[tuple[int, tuple[str, ...]]] = []
    fences: list[Fence] = []
    raw_headings: list[tuple[int, int, str]] = []
    nested_errors = 0
    path_stack: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            language = fence_match.group(1).strip()
            if language:
                if stack:
                    nested_errors += 1
                path = tuple(item[1] for item in path_stack)
                stack.append((index, path))
            elif stack:
                start, path = stack.pop()
                fences.append(Fence(start=start, end=index, path=path))
            else:
                path = tuple(item[1] for item in path_stack)
                stack.append((index, path))
            continue

        if stack:
            continue
        heading_match = HEADING_RE.match(line)
        if not heading_match:
            continue
        level = len(heading_match.group(1))
        heading_text = heading_match.group(2).strip()
        while path_stack and path_stack[-1][0] >= level:
            path_stack.pop()
        path_stack.append((level, heading_text))
        raw_headings.append((index, level, heading_text))

    for start, path in stack:
        fences.append(Fence(start=start, end=None, path=path))

    occurrence_totals: dict[tuple[tuple[str, ...], int, str], int] = {}
    occurrence_seen: dict[tuple[tuple[str, ...], int, str], int] = {}
    parent_stack: list[tuple[int, str]] = []
    raw_with_parent: list[tuple[int, int, str, tuple[str, ...]]] = []
    for index, level, heading_text in raw_headings:
        while parent_stack and parent_stack[-1][0] >= level:
            parent_stack.pop()
        parent = tuple(item[1] for item in parent_stack)
        key = (parent, level, heading_text)
        occurrence_totals[key] = occurrence_totals.get(key, 0) + 1
        raw_with_parent.append((index, level, heading_text, parent))
        parent_stack.append((level, heading_text))

    headings: list[Heading] = []
    resolved_stack: list[tuple[int, str]] = []
    for index, level, heading_text, parent in raw_with_parent:
        while resolved_stack and resolved_stack[-1][0] >= level:
            resolved_stack.pop()
        key = (parent, level, heading_text)
        occurrence_seen[key] = occurrence_seen.get(key, 0) + 1
        suffix = (
            f"-{occurrence_seen[key]}" if occurrence_totals[key] > 1 else ""
        )
        component = f"{heading_text}{suffix}"
        resolved_stack.append((level, component))
        headings.append(
            Heading(
                line_index=index,
                level=level,
                text=heading_text,
                path=tuple(item[1] for item in resolved_stack),
            )
        )

    return ParseResult(
        headings=tuple(headings),
        fences=tuple(sorted(fences, key=lambda item: item.start)),
        nested_errors=nested_errors,
        unclosed=len(stack),
    )


def _scope_for(source_name: str) -> set[str]:
    if source_name == DEV_SOURCE_NAME:
        return DEV_SCOPE_HEADINGS
    if source_name == ARCH_SOURCE_NAME:
        return ARCH_SCOPE_HEADINGS
    raise ValueError(f"unsupported source name: {source_name}")


def extract_blocks(text: str, source_name: str) -> list[Block]:
    """抽出指定文件範圍內 H2/H3/H4、表格與 fenced block。"""

    parsed = parse_markdown(text)
    if parsed.unclosed or parsed.nested_errors:
        raise ValueError(
            f"{source_name}: invalid fences: unclosed={parsed.unclosed}, "
            f"nested={parsed.nested_errors}"
        )
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    scoped_h2 = _scope_for(source_name)

    def scoped_path(path: tuple[str, ...]) -> tuple[str, ...]:
        for index, component in enumerate(path):
            if component in scoped_h2:
                return path[index:]
        return ()

    scoped_headings = [
        (heading, scoped_path(heading.path))
        for heading in parsed.headings
        if heading.level in {2, 3, 4} and scoped_path(heading.path)
    ]
    all_heading_lines = [heading.line_index for heading in parsed.headings]
    blocks: list[Block] = []
    kind_counts: dict[tuple[tuple[str, ...], str], int] = {}

    def add_block(
        path: tuple[str, ...], kind: str, start: int, end: int, heading: str
    ) -> None:
        key = (path, kind)
        kind_counts[key] = kind_counts.get(key, 0) + 1
        ordinal = kind_counts[key]
        block_id = f"{source_name}::{' > '.join(path)}::{kind}{ordinal}"
        body = "\n".join(lines[start : end + 1]) + "\n"
        blocks.append(
            Block(
                block_id=block_id,
                heading=heading,
                kind=kind,
                start_line=start + 1,
                end_line=end + 1,
                content=body,
                content_hash=content_hash(body),
            )
        )

    for heading, path in scoped_headings:
        later = [index for index in all_heading_lines if index > heading.line_index]
        end = (later[0] - 1) if later else (len(lines) - 1)
        add_block(path, "heading", heading.line_index, end, heading.text)

    heading_by_line = {heading.line_index: heading for heading in parsed.headings}
    active_path: tuple[str, ...] = ()
    fence_by_start = {fence.start: fence for fence in parsed.fences}
    index = 0
    while index < len(lines):
        if index in heading_by_line:
            active_path = scoped_path(heading_by_line[index].path)
        if active_path:
            fence = fence_by_start.get(index)
            if fence and fence.end is not None:
                add_block(active_path, "fence", index, fence.end, active_path[-1])
                index = fence.end + 1
                continue
            if re.match(r"^\s*\|.*\|\s*$", lines[index]):
                start = index
                while index + 1 < len(lines) and re.match(
                    r"^\s*\|.*\|\s*$", lines[index + 1]
                ):
                    index += 1
                add_block(active_path, "table", start, index, active_path[-1])
        index += 1

    return blocks


def _split_markdown_row(line: str) -> list[str]:
    sentinel = "\0PIPE\0"
    protected = line.strip().strip("|").replace(r"\|", sentinel)
    return [cell.strip().replace(sentinel, "|") for cell in protected.split("|")]


def parse_manifest(text: str) -> list[ManifestRow]:
    """解析 `## Disposition Inventory` 下的七欄 Markdown 表格。"""

    in_section = False
    rows: list[ManifestRow] = []
    for line in text.splitlines():
        if line == "## Disposition Inventory":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.lstrip().startswith("|"):
            continue
        cells = _split_markdown_row(line)
        if len(cells) != 7 or cells[0] in {"ID", "---"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        hash_span = cells[2].split("@", 1)
        if len(hash_span) != 2:
            raise ValueError(f"manifest row lacks hash@line-span: {cells[0]}")
        rows.append(
            ManifestRow(
                block_id=cells[0],
                heading=cells[1],
                content_hash=hash_span[0],
                line_span=hash_span[1],
                disposition=cells[3],
                carrier=cells[4],
                reason=cells[5] + (f" | {cells[6]}" if cells[6] else ""),
            )
        )
    if not in_section:
        raise ValueError("manifest missing '## Disposition Inventory'")
    return rows


def _rows_by_id(rows: Iterable[ManifestRow]) -> tuple[dict[str, ManifestRow], list[str]]:
    result: dict[str, ManifestRow] = {}
    duplicates: list[str] = []
    for row in rows:
        if row.block_id in result:
            duplicates.append(row.block_id)
        result[row.block_id] = row
    return result, duplicates


def validate_coverage(
    manifest_text: str, dev_text: str, arch_text: str
) -> list[str]:
    """驗證 view 全量覆蓋、無重複且 content hash 一致。"""

    rows = parse_manifest(manifest_text)
    row_map, duplicates = _rows_by_id(rows)
    blocks = extract_blocks(dev_text, DEV_SOURCE_NAME) + extract_blocks(
        arch_text, ARCH_SOURCE_NAME
    )
    block_map = {block.block_id: block for block in blocks}
    errors = [f"duplicate: {item}" for item in duplicates]
    errors.extend(f"missing: {item}" for item in sorted(set(block_map) - set(row_map)))
    errors.extend(f"unknown: {item}" for item in sorted(set(row_map) - set(block_map)))
    for block_id in sorted(set(row_map) & set(block_map)):
        if row_map[block_id].content_hash != block_map[block_id].content_hash:
            errors.append(f"content-hash mismatch: {block_id}")
        if row_map[block_id].disposition == "壓縮留" and not _parse_mappings(
            row_map[block_id]
        ):
            errors.append(f"compression mapping missing: {block_id}")
    return errors


def _parse_mappings(row: ManifestRow) -> list[tuple[str, str, str]]:
    if row.disposition != "壓縮留":
        return []
    mappings: list[tuple[str, str, str]] = []
    for item in re.split(r"\s*<br\s*/?>\s*|\s*;;\s*", row.carrier):
        parts = [part.strip() for part in item.split("→", 2)]
        if len(parts) == 3 and parts[0] and parts[1] and parts[2].startswith("INV-"):
            mappings.append((parts[0], parts[1], parts[2]))
    return mappings


def validate_post_state(
    manifest_text: str,
    dev_view_text: str,
    arch_view_text: str,
    live_dev_text: str,
    live_arch_text: str,
) -> list[str]:
    """驗證 live 文件的 disposition、hash、INV 綁定及新增封閉。"""

    coverage_errors = validate_coverage(manifest_text, dev_view_text, arch_view_text)
    if coverage_errors:
        return [f"baseline {error}" for error in coverage_errors]
    rows = parse_manifest(manifest_text)
    row_map, _ = _rows_by_id(rows)
    baseline_blocks = extract_blocks(dev_view_text, DEV_SOURCE_NAME) + extract_blocks(
        arch_view_text, ARCH_SOURCE_NAME
    )
    live_blocks = extract_blocks(live_dev_text, DEV_SOURCE_NAME) + extract_blocks(
        live_arch_text, ARCH_SOURCE_NAME
    )
    baseline_map = {block.block_id: block for block in baseline_blocks}
    live_map = {block.block_id: block for block in live_blocks}
    errors: list[str] = []
    mapped_sources: set[str] = set()
    registered_post_ids: set[str] = set()

    for row in rows:
        mappings = _parse_mappings(row)
        if row.disposition == "壓縮留" and not mappings:
            errors.append(f"compression mapping missing: {row.block_id}")
        for source_id, post_id, anchor in mappings:
            mapped_sources.add(source_id)
            registered_post_ids.add(post_id)
            post_block = live_map.get(post_id)
            if post_block is None:
                errors.append(f"mapped post-state block missing: {post_id}")
            elif anchor not in post_block.content:
                errors.append(f"INV anchor missing from bound block: {post_id}::{anchor}")

    for block_id, row in row_map.items():
        if row.disposition == "刪" and block_id in live_map:
            errors.append(f"authorized deletion still present: {block_id}")
        if row.disposition == "原樣留":
            live = live_map.get(block_id)
            if live is None:
                errors.append(f"preserved block missing: {block_id}")
            elif live.content_hash != row.content_hash:
                errors.append(f"preserved block hash mismatch: {block_id}")

    missing = set(baseline_map) - set(live_map)
    authorized_missing = {
        block_id for block_id, row in row_map.items() if row.disposition == "刪"
    } | mapped_sources
    for block_id in sorted(missing - authorized_missing):
        errors.append(f"unauthorized deletion: {block_id}")

    added = set(live_map) - set(baseline_map)
    for block_id in sorted(added - registered_post_ids):
        errors.append(f"unregistered new block: {block_id}")
    return errors


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post-state", action="store_true")
    parser.add_argument("--live-dev", type=Path)
    parser.add_argument("--live-arch", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("dev_view", type=Path)
    parser.add_argument("arch_view", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.post_state:
            live_dev = args.live_dev or Path("docs/DEVELOPMENT_GUIDE.md")
            live_arch = args.live_arch or Path("docs/ARCHITECTURE.md")
            errors = validate_post_state(
                _read(args.manifest),
                _read(args.dev_view),
                _read(args.arch_view),
                _read(live_dev),
                _read(live_arch),
            )
        else:
            errors = validate_coverage(
                _read(args.manifest), _read(args.dev_view), _read(args.arch_view)
            )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("manifest validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
