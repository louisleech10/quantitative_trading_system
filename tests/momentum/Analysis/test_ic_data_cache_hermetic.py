"""撤除 redirect 時 digest canary 必能偵測 sacrificial production write。"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.fixtures.ic_persist_redirect as redirect
from tests.fixtures.ic_persist_redirect import RedirectPatchSet


def test_mutation_redirect_disabled_caught(
    redirect_patch_set: RedirectPatchSet,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    fake_production = (work / "data_cache").resolve()
    redirect_patch_set.production_prefix = fake_production
    ctx = redirect_patch_set.activate(tmp_path / "redirect", owner="hermetic-mutation")
    try:
        production_path = fake_production / "features/canary.txt"
        redirected = redirect._redirect_path(production_path)
        assert redirected.resolve().is_relative_to(ctx.redirect_root)
        monkeypatch.setenv("IC_PERSIST_REDIRECT_DISABLE", "1")
        mutated = redirect._redirect_path(production_path)
        mutated.parent.mkdir(parents=True, exist_ok=True)
        mutated.write_text("canary", encoding="utf-8")
        assert mutated.resolve().is_relative_to(work)
        assert not mutated.resolve().is_relative_to(ctx.redirect_root)
    finally:
        monkeypatch.delenv("IC_PERSIST_REDIRECT_DISABLE", raising=False)
        redirect_patch_set.deactivate(ctx)
    print("MUTATION_CANARY=1")
