"""批次 B manifest validator 可證偽測試。"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_doc_manifest_b import (
    ARCH_SOURCE_NAME,
    DEV_SOURCE_NAME,
    content_hash,
    extract_blocks,
    main,
    normalize_content,
    parse_markdown,
    validate_coverage,
    validate_post_state,
)


FIXTURES = Path(__file__).parent / "fixtures_b"


def _views() -> tuple[str, str]:
    return (
        (FIXTURES / "dev_view.md").read_text(encoding="utf-8"),
        (FIXTURES / "arch_view.md").read_text(encoding="utf-8"),
    )


def _manifest(
    dev: str,
    arch: str,
    overrides: dict[str, tuple[str, str]] | None = None,
    omit: set[str] | None = None,
) -> str:
    blocks = extract_blocks(dev, DEV_SOURCE_NAME) + extract_blocks(
        arch, ARCH_SOURCE_NAME
    )
    lines = [
        "# fixture manifest",
        "",
        "## Disposition Inventory",
        "",
        "| ID | 原 heading | content-hash@line-span | 分類 | 承載 | 理由 | 備註 |",
        "|---|---|---|---|---|---|---|",
    ]
    for block in blocks:
        if omit and block.block_id in omit:
            continue
        disposition, carrier = (overrides or {}).get(
            block.block_id, ("原樣留", "N/A")
        )
        lines.append(
            f"| {block.block_id} | {block.heading} | {block.content_hash}@"
            f"L{block.start_line}-L{block.end_line} | {disposition} | {carrier} | fixture | |"
        )
    return "\n".join(lines) + "\n"


def _id(blocks: list, suffix: str) -> str:
    return next(block.block_id for block in blocks if block.block_id.endswith(suffix))


def _cli_post_state(
    tmp_path: Path,
    manifest: str,
    dev: str,
    arch: str,
    live_dev: str,
    live_arch: str,
) -> int:
    paths = {
        "manifest": manifest,
        "dev": dev,
        "arch": arch,
        "live_dev": live_dev,
        "live_arch": live_arch,
    }
    for name, content in paths.items():
        (tmp_path / f"{name}.md").write_text(content, encoding="utf-8")
    return main(
        [
            "--post-state",
            "--live-dev",
            str(tmp_path / "live_dev.md"),
            "--live-arch",
            str(tmp_path / "live_arch.md"),
            str(tmp_path / "manifest.md"),
            str(tmp_path / "dev.md"),
            str(tmp_path / "arch.md"),
        ]
    )


def test_lang_push_ignores_heading_inside_fence() -> None:
    parsed = parse_markdown("## A\n```python\n### hidden\n```\n### visible\n")
    assert [heading.text for heading in parsed.headings] == ["A", "visible"]
    assert parsed.unclosed == 0
    assert parsed.nested_errors == 0


def test_lang_push_reports_nested_and_unclosed() -> None:
    parsed = parse_markdown("```python\n```json\n```\n")
    assert parsed.nested_errors == 1
    assert parsed.unclosed == 1


def test_bare_fence_opens_only_when_stack_is_empty() -> None:
    parsed = parse_markdown("## A\n```\nplain code\n```\n### visible\n")
    assert parsed.unclosed == 0
    assert parsed.nested_errors == 0
    assert len(parsed.fences) == 1
    assert [heading.text for heading in parsed.headings] == ["A", "visible"]


def test_normalization_ignores_trailing_whitespace() -> None:
    assert content_hash("a  \n") == content_hash("a\n")


def test_normalization_ignores_newline_style() -> None:
    assert normalize_content("a\r\nb\r\n") == normalize_content("a\nb\n")


def test_coverage_passes_complete_manifest() -> None:
    dev, arch = _views()
    assert validate_coverage(_manifest(dev, arch), dev, arch) == []


def test_coverage_rejects_missing_row() -> None:
    dev, arch = _views()
    blocks = extract_blocks(dev, DEV_SOURCE_NAME)
    errors = validate_coverage(_manifest(dev, arch, omit={blocks[0].block_id}), dev, arch)
    assert any(error.startswith("missing:") for error in errors)


def test_coverage_rejects_duplicate_row() -> None:
    dev, arch = _views()
    manifest = _manifest(dev, arch)
    row = next(line for line in manifest.splitlines() if line.startswith("| DEVELOPMENT"))
    errors = validate_coverage(manifest + row + "\n", dev, arch)
    assert any(error.startswith("duplicate:") for error in errors)


def test_coverage_rejects_hash_mismatch_after_body_edit() -> None:
    dev, arch = _views()
    manifest = _manifest(dev, arch)
    errors = validate_coverage(manifest, dev.replace("baseline body", "changed body"), arch)
    assert any("content-hash mismatch" in error for error in errors)


def test_post_state_rejects_preserved_block_tampering(tmp_path: Path) -> None:
    dev, arch = _views()
    manifest = _manifest(dev, arch)
    live_arch = arch.replace("preserve this", "tampered")
    errors = validate_post_state(
        manifest, dev, arch, dev, live_arch
    )
    assert any("preserved block hash mismatch" in error for error in errors)
    assert _cli_post_state(tmp_path, manifest, dev, arch, dev, live_arch) == 1


def test_post_state_rejects_unauthorized_deletion(tmp_path: Path) -> None:
    dev, arch = _views()
    live = dev.replace("### 範例\n\nkeep me\n\n", "")
    manifest = _manifest(dev, arch)
    errors = validate_post_state(manifest, dev, arch, live, arch)
    assert any("unauthorized deletion" in error for error in errors)
    assert _cli_post_state(tmp_path, manifest, dev, arch, live, arch) == 1


def test_post_state_rejects_authorized_deletion_still_present(tmp_path: Path) -> None:
    dev, arch = _views()
    blocks = extract_blocks(dev, DEV_SOURCE_NAME)
    target = _id(blocks, "範例::heading1")
    manifest = _manifest(dev, arch, {target: ("刪", "N/A")})
    errors = validate_post_state(manifest, dev, arch, dev, arch)
    assert any("authorized deletion still present" in error for error in errors)
    assert _cli_post_state(tmp_path, manifest, dev, arch, dev, arch) == 1


def test_post_state_accepts_authorized_deletion() -> None:
    dev, arch = _views()
    blocks = extract_blocks(dev, DEV_SOURCE_NAME)
    target = _id(blocks, "範例::heading1")
    child = _id(blocks, "範例::fence1")
    manifest = _manifest(
        dev,
        arch,
        {target: ("刪", "N/A"), child: ("刪", "N/A")},
    )
    live = dev.replace("### 範例\n\nkeep me\n\n", "")
    errors = validate_post_state(manifest, dev, arch, live, arch)
    assert not any("unauthorized deletion" in error for error in errors)
    assert not any("authorized deletion still present" in error for error in errors)


def test_post_state_rejects_unregistered_new_block(tmp_path: Path) -> None:
    dev, arch = _views()
    live = dev + "\n## 前端開發規範\n\nnew body\n"
    manifest = _manifest(dev, arch)
    errors = validate_post_state(manifest, dev, arch, live, arch)
    assert any("unregistered new block" in error for error in errors)
    assert _cli_post_state(tmp_path, manifest, dev, arch, live, arch) == 1


def test_inv_anchor_moved_to_unbound_block_still_fails_global_hit(tmp_path: Path) -> None:
    dev, arch = _views()
    blocks = extract_blocks(dev, DEV_SOURCE_NAME)
    source = _id(blocks, "範例::heading1")
    post = source
    manifest = _manifest(
        dev, arch, {source: ("壓縮留", f"{source} → {post} → INV-01 anchor")}
    )
    live = dev.replace("keep me", "compressed").replace(
        "baseline body", "baseline body INV-01 anchor"
    )
    errors = validate_post_state(manifest, dev, arch, live, arch)
    assert any("INV anchor missing from bound block" in error for error in errors)
    assert _cli_post_state(tmp_path, manifest, dev, arch, live, arch) == 1


def test_inv_anchor_missing_from_bound_block_fails(tmp_path: Path) -> None:
    dev, arch = _views()
    blocks = extract_blocks(dev, DEV_SOURCE_NAME)
    source = _id(blocks, "範例::heading1")
    manifest = _manifest(
        dev, arch, {source: ("壓縮留", f"{source} → {source} → INV-02 absent")}
    )
    errors = validate_post_state(manifest, dev, arch, dev, arch)
    assert any("INV anchor missing from bound block" in error for error in errors)
    assert _cli_post_state(tmp_path, manifest, dev, arch, dev, arch) == 1


def test_duplicate_heading_paths_receive_occurrence_suffixes() -> None:
    text = "## 代碼質量規範\n### 範例\none\n### 範例\ntwo\n"
    blocks = extract_blocks(text, DEV_SOURCE_NAME)
    ids = [block.block_id for block in blocks if "範例" in block.block_id]
    assert any("範例-1" in block_id for block_id in ids)
    assert any("範例-2" in block_id for block_id in ids)


@pytest.mark.parametrize("line_end", ["\n", "\r\n"])
def test_hash_fixture_is_line_ending_stable(line_end: str) -> None:
    assert content_hash(line_end.join(["x", "y", ""])) == content_hash("x\ny\n")
