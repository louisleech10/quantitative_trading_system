"""手動 baseline generator 的非 pytest redirect context manager。"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from tests.fixtures.ic_persist_redirect import RedirectPatchSet, assert_context_clean


@contextmanager
def run_with_manual_redirect(root: Path | None = None) -> Iterator[Path]:
    """以顯式 root 或 IC_PERSIST_REDIRECT_ROOT bracket 完整 generator body。"""

    configured = root or (
        Path(os.environ["IC_PERSIST_REDIRECT_ROOT"])
        if os.environ.get("IC_PERSIST_REDIRECT_ROOT")
        else None
    )
    if configured is None:
        raise SystemExit(2)
    patch_set = RedirectPatchSet()
    patch_set.install_once()
    ctx = patch_set.activate(configured, owner="manual-generator")
    try:
        yield ctx.redirect_root
        assert_context_clean(ctx)
    finally:
        patch_set.deactivate(ctx)

