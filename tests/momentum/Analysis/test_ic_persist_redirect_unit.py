"""S1–S11 redirect manifest、生命週期與 mutation 單元測試。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

import pytest

import tests.fixtures.ic_persist_redirect as redirect
from tests.fixtures.ic_persist_redirect import (
    REQUIRED_SEAM_IDS,
    RedirectCompletenessError,
    RedirectPatchSet,
    ResolvedSeam,
    assert_context_clean,
    get_activation_count,
)


@pytest.mark.parametrize("seam_id", sorted(REQUIRED_SEAM_IDS, key=lambda item: int(item[1:])))
def test_seam_probe_redirect_only(
    seam_id: str,
    redirect_patch_set: RedirectPatchSet,
    tmp_path: Path,
) -> None:
    ctx = redirect_patch_set.activate(tmp_path / seam_id, owner=seam_id)
    try:
        seam = redirect_patch_set.resolve_all()[seam_id]
        outputs = seam.probe(ctx.redirect_root)
        assert outputs
        assert all(path.resolve().is_relative_to(ctx.redirect_root) for path in outputs)
        assert_context_clean(ctx)
    finally:
        redirect_patch_set.deactivate(ctx)


@pytest.mark.parametrize("seam_id", sorted(REQUIRED_SEAM_IDS, key=lambda item: int(item[1:])))
def test_missing_target_refuses_activate(
    seam_id: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    patch_set = RedirectPatchSet()
    original = patch_set._build_manifest

    def missing() -> dict[str, ResolvedSeam]:
        manifest = original()
        manifest.pop(seam_id)
        return manifest

    monkeypatch.setattr(patch_set, "_build_manifest", missing)
    with pytest.raises(RedirectCompletenessError):
        patch_set.activate(tmp_path / seam_id, owner="missing")
    assert get_activation_count() == 0
    assert patch_set.installed_ids == frozenset()


@pytest.mark.parametrize(
    ("seam_id", "index", "target_path", "attribute"),
    [
        (
            "S1",
            0,
            "momentum.Analysis.ic_filter_orchestrator.ICFilterOrchestrator",
            "_resolve_filtered_path",
        ),
        (
            "S2",
            0,
            "momentum.Analysis.ic_reporter.ICReporter",
            "save_report",
        ),
        (
            "S10",
            0,
            "momentum.Analysis.lightgbm_analyzer.LightGBMAnalyzer",
            "_resolve_model_path",
        ),
    ],
)
def test_missing_subtarget_refuses_activate(
    seam_id: str,
    index: int,
    target_path: str,
    attribute: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    patch_set = RedirectPatchSet()
    original = patch_set._build_manifest
    module_path, target_name = target_path.rsplit(".", 1)
    target = getattr(__import__(module_path, fromlist=[target_name]), target_name)
    production_function = getattr(target, attribute)

    def missing() -> dict[str, ResolvedSeam]:
        manifest = original()
        resolved = manifest[seam_id]
        installers = list(resolved.installers)
        installers.pop(index)
        manifest[seam_id] = ResolvedSeam(seam_id, tuple(installers), resolved.probe)
        return manifest

    monkeypatch.setattr(patch_set, "_build_manifest", missing)
    with pytest.raises(RedirectCompletenessError):
        patch_set.activate(tmp_path / seam_id, owner=f"missing-{seam_id}")
    assert get_activation_count() == 0
    assert patch_set.installed_ids == frozenset()
    assert getattr(target, attribute) is production_function


def test_missing_target_after_install_refuses_activate(
    redirect_patch_set: RedirectPatchSet,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(redirect_patch_set, "_installed_ids", frozenset({"S1"}))
    monkeypatch.setattr(
        redirect_patch_set,
        "install_once",
        lambda: (_ for _ in ()).throw(RedirectCompletenessError("missing")),
    )
    with pytest.raises(RedirectCompletenessError):
        redirect_patch_set.activate(tmp_path, owner="after-install")
    assert get_activation_count() == 0


def test_installer_mid_fail_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_set = RedirectPatchSet()
    events: list[str] = []

    def good() -> Callable[[], None]:
        events.append("install")
        return lambda: events.append("undo")

    def bad() -> Callable[[], None]:
        raise RuntimeError("boom")

    def manifest() -> dict[str, ResolvedSeam]:
        result: dict[str, ResolvedSeam] = {}
        for seam_id in REQUIRED_SEAM_IDS:
            if seam_id == "S2":
                installers = (good, bad, good)
            elif seam_id in {"S1", "S10"}:
                installers = (good, good)
            else:
                installers = (good,)
            result[seam_id] = ResolvedSeam(seam_id, installers, lambda root: (root,))
        return result

    monkeypatch.setattr(patch_set, "_build_manifest", manifest)
    with pytest.raises(RedirectCompletenessError):
        patch_set.install_once()
    assert events[-1] == "undo"
    assert events.count("install") == events.count("undo")
    assert patch_set.installed_ids == frozenset()


@pytest.mark.parametrize("mode", ["missing", "extra", "empty_installer", "empty_probe"])
def test_manifest_extra_or_missing_id(mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_set = RedirectPatchSet()
    original = patch_set._build_manifest

    def malformed() -> dict[str, ResolvedSeam]:
        manifest = original()
        if mode == "missing":
            manifest.pop("S11")
        elif mode == "extra":
            manifest["S12"] = ResolvedSeam("S12", (lambda: lambda: None,), lambda root: (root,))
        elif mode == "empty_installer":
            manifest["S1"] = ResolvedSeam("S1", (), lambda root: (root,))
        else:
            manifest["S1"] = ResolvedSeam("S1", (lambda: lambda: None,), None)  # type: ignore[arg-type]
        return manifest

    monkeypatch.setattr(patch_set, "_build_manifest", malformed)
    with pytest.raises(RedirectCompletenessError):
        patch_set.resolve_all()


def test_s1_orchestrator_report_literals_redirect(
    redirect_patch_set: RedirectPatchSet, tmp_path: Path
) -> None:
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    class ReporterProbe:
        def __init__(self) -> None:
            self.paths: list[Path] = []

        def save_report(self, report: dict, output_dir: str, case_id: str) -> dict[str, str]:
            self.paths.append(Path(output_dir))
            return {}

        def save_filter_log(self, filter_log: dict, output_dir: str, case_id: str) -> str:
            self.paths.append(Path(output_dir))
            return str(Path(output_dir) / "filter.json")

    ctx = redirect_patch_set.activate(tmp_path / "s1-report", owner="s1-report")
    try:
        orchestrator = object.__new__(ICFilterOrchestrator)
        reporter = ReporterProbe()
        orchestrator._reporter = reporter
        orchestrator._persist_outputs(None, None, {}, {}, {})
        assert reporter.paths
        assert all(path.resolve().is_relative_to(ctx.redirect_root) for path in reporter.paths)
        assert_context_clean(ctx)
    finally:
        redirect_patch_set.deactivate(ctx)


def test_to_thread_polluter_writes_under_redirect(
    redirect_patch_set: RedirectPatchSet, tmp_path: Path
) -> None:
    ctx = redirect_patch_set.activate(tmp_path / "thread", owner="thread")
    try:
        path = asyncio.run(asyncio.to_thread(redirect._redirect_path, Path("data_cache/features/thread.h5")))
        assert path.resolve().is_relative_to(ctx.redirect_root)
        assert_context_clean(ctx)
    finally:
        redirect_patch_set.deactivate(ctx)


def test_non_opt_in_not_redirected() -> None:
    assert get_activation_count() == 0
    assert redirect._redirect_path(Path("data_cache/features/plain.h5")) == Path(
        "data_cache/features/plain.h5"
    )


def test_nested_activate_rejected(
    redirect_patch_set: RedirectPatchSet, tmp_path: Path
) -> None:
    first = redirect_patch_set.activate(tmp_path / "first", owner="first")
    try:
        assert get_activation_count() == 1
        with pytest.raises(RuntimeError):
            redirect_patch_set.activate(tmp_path / "second", owner="second")
        assert get_activation_count() == 1
    finally:
        redirect_patch_set.deactivate(first)
    assert get_activation_count() == 0


def test_mutation_disable_redirect_internal(
    redirect_patch_set: RedirectPatchSet,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    ctx = redirect_patch_set.activate(tmp_path / "redirect", owner="mutation")
    try:
        monkeypatch.setenv("IC_PERSIST_REDIRECT_DISABLE", "1")
        path = redirect._redirect_path(Path("data_cache/features/mutated.txt"))
        assert path == Path("data_cache/features/mutated.txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("mutation", encoding="utf-8")
        assert path.exists()
    finally:
        monkeypatch.delenv("IC_PERSIST_REDIRECT_DISABLE", raising=False)
        redirect_patch_set.deactivate(ctx)
