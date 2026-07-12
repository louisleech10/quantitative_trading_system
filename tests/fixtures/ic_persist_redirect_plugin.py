"""pytest fixtures for opt-in IC persistence redirect."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import pytest

from tests.fixtures.ic_persist_redirect import (
    RedirectContext,
    RedirectPatchSet,
    assert_context_clean,
    get_activation_count,
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "ic_persist_redirect: opt in to hermetic IC persistence redirect"
    )


@pytest.fixture(scope="session")
def redirect_patch_set() -> RedirectPatchSet:
    patch_set = RedirectPatchSet()
    patch_set.install_once()
    return patch_set


@pytest.fixture(scope="session")
def redirect_root_session(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("ic_redirect")


@pytest.fixture(scope="module")
def redirect_root_module(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("ic_redirect_module")


@pytest.fixture
def ic_persist_redirect(
    redirect_patch_set: RedirectPatchSet,
    redirect_root_session: Path,
    request: pytest.FixtureRequest,
) -> Iterator[RedirectContext]:
    ctx = redirect_patch_set.activate(redirect_root_session, owner=request.node.nodeid)
    try:
        yield ctx
        assert_context_clean(ctx)
    finally:
        redirect_patch_set.deactivate(ctx)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if os.environ.get("IC_PERSIST_ASSERT_NO_ACTIVATION") != "1":
        return
    probe = os.environ.get("IC_PERSIST_PROBE_JSON")
    payload = {"activation_count": get_activation_count(), "violations": []}
    if probe:
        Path(probe).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    if payload["activation_count"] != 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED

