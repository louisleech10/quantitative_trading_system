"""IC/ML/Feature Factory 測試落盤的行程級暫存目錄重導。"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


REQUIRED_SEAM_IDS = frozenset(f"S{i}" for i in range(1, 12))
MIN_INSTALLER_ARITY = {"S1": 2, "S2": 3, "S10": 2}
_LOCK = threading.RLock()
_ACTIVE: ActiveRedirect | None = None


class RedirectCompletenessError(RuntimeError):
    """redirect manifest 不完整或無法原子安裝。"""


@dataclass
class ProductionWriteSpy:
    """記錄 active gate 仍把 production path 當成最終路徑的違規。"""

    production_prefix: Path
    violations: list[str] = field(default_factory=list)

    def record(self, original: Path, rewritten: Path) -> None:
        original_resolved = original.resolve()
        rewritten_resolved = rewritten.resolve()
        prefix = self.production_prefix.resolve()
        if _under(original_resolved, prefix) and _under(rewritten_resolved, prefix):
            self.violations.append(str(rewritten_resolved))


@dataclass(frozen=True)
class ActiveRedirect:
    root: Path
    production_prefix: Path
    spy: ProductionWriteSpy
    owner: str


@dataclass(frozen=True)
class RedirectContext:
    active: ActiveRedirect

    @property
    def redirect_root(self) -> Path:
        return self.active.root

    @property
    def spy(self) -> ProductionWriteSpy:
        return self.active.spy


@dataclass(frozen=True)
class ResolvedSeam:
    seam_id: str
    installers: tuple[Callable[[], Callable[[], None]], ...]
    probe: Callable[[Path], tuple[Path, ...]]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _under(path: Path, prefix: Path) -> bool:
    return path == prefix or path.is_relative_to(prefix)


def get_active_redirect() -> ActiveRedirect | None:
    """回傳跨 worker thread 可見的 active redirect。"""

    if os.environ.get("IC_PERSIST_REDIRECT_DISABLE") == "1":
        return None
    with _LOCK:
        return _ACTIVE


def get_active_redirect_root() -> Path | None:
    active = get_active_redirect()
    return None if active is None else active.root


def get_activation_count() -> int:
    with _LOCK:
        return int(_ACTIVE is not None)


def _redirect_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    active = get_active_redirect()
    if active is None:
        return path
    resolved = path.resolve()
    prefix = active.production_prefix.resolve()
    if not _under(resolved, prefix):
        return path
    relative = resolved.relative_to(prefix)
    rewritten = active.root / relative
    active.spy.record(path, rewritten)
    return rewritten


def digest_data_cache() -> dict[str, str]:
    """逐檔 SHA-256；只掃 production features/reports/models。"""

    data_root = _repo_root() / "data_cache"
    result: dict[str, str] = {}
    for child in ("features", "reports", "models"):
        root = data_root / child
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(data_root))
                result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _patch_attr(
    target: object, name: str, replacement: object
) -> Callable[[], Callable[[], None]]:
    def install() -> Callable[[], None]:
        original = getattr(target, name)
        setattr(target, name, replacement)

        def undo() -> None:
            setattr(target, name, original)

        return undo

    return install


def _method_path_resolver(original: Callable[..., Any], bucket: str) -> Callable[..., Any]:
    def wrapped(self: object, metadata: dict[str, Any]) -> Any:
        active = get_active_redirect()
        if active is None:
            return original(self, metadata)
        symbol = metadata.get("symbol") if metadata else None
        timeframe = metadata.get("timeframe") if metadata else None
        name = f"{symbol}_{timeframe}_filtered.h5" if symbol and timeframe else "filtered_features.h5"
        path = active.root / bucket / name
        active.spy.record(active.production_prefix / bucket / name, path)
        original_value = original(self, metadata)
        return str(path) if isinstance(original_value, str) else path

    return wrapped


def _function_path_resolver(original: Callable[..., Any], bucket: str) -> Callable[..., Any]:
    def wrapped(metadata: dict[str, Any]) -> Path:
        active = get_active_redirect()
        if active is None:
            return original(metadata)
        symbol = metadata.get("symbol") if metadata else None
        timeframe = metadata.get("timeframe") if metadata else None
        name = f"{symbol}_{timeframe}_filtered.h5" if symbol and timeframe else "filtered_features.h5"
        path = active.root / bucket / name
        active.spy.record(active.production_prefix / bucket / name, path)
        return path

    return wrapped


def _reporter_wrapper(original: Callable[..., Any], argument: str, bucket: str) -> Callable[..., Any]:
    signature = inspect.signature(original)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        active = get_active_redirect()
        if active is not None:
            bound = signature.bind_partial(*args, **kwargs)
            value = bound.arguments.get(argument)
            if value is not None:
                original_path = Path(value)
                candidate = _redirect_path(original_path)
                if candidate == original_path and _under(original_path.resolve(), active.production_prefix):
                    candidate = active.root / bucket / original_path.name
                bound.arguments[argument] = str(candidate)
                return original(*bound.args, **bound.kwargs)
        return original(*args, **kwargs)

    return wrapped


class _RedirectingReporter:
    """讓 orchestrator 內硬編的 report 路徑也經 active redirect。"""

    def __init__(self, reporter: object) -> None:
        self._reporter = reporter

    def __getattr__(self, name: str) -> Any:
        return getattr(self._reporter, name)

    def save_report(self, report: dict, output_dir: str, case_id: str) -> Any:
        return self._reporter.save_report(report, str(_redirect_path(output_dir)), case_id)

    def save_filter_log(self, filter_log: dict, output_dir: str, case_id: str) -> Any:
        return self._reporter.save_filter_log(
            filter_log, str(_redirect_path(output_dir)), case_id
        )

    def save_filtered_features(
        self,
        features_df: Any,
        feature_names: list[str],
        output_path: str,
        **kwargs: Any,
    ) -> Any:
        return self._reporter.save_filtered_features(
            features_df,
            feature_names,
            str(_redirect_path(output_path)),
            **kwargs,
        )


def _orchestrator_persist_wrapper(original: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(self: object, *args: Any, **kwargs: Any) -> Any:
        if get_active_redirect() is None:
            return original(self, *args, **kwargs)
        reporter = getattr(self, "_reporter")
        setattr(self, "_reporter", _RedirectingReporter(reporter))
        try:
            return original(self, *args, **kwargs)
        finally:
            setattr(self, "_reporter", reporter)

    return wrapped


def _model_wrapper(original: Callable[..., Path]) -> Callable[..., Path]:
    def wrapped(self: object, path: str) -> Path:
        active = get_active_redirect()
        if active is None:
            return original(self, path)
        target = Path(path).expanduser().resolve()
        allowed = active.production_prefix / "models"
        redirected_allowed = active.root / "models"
        if target.suffix != ".pkl":
            raise ValueError("模型檔案必須為 .pkl")
        if _under(target, redirected_allowed.resolve()):
            target.parent.mkdir(parents=True, exist_ok=True)
            return target
        if not _under(target, allowed.resolve()):
            raise ValueError("模型路徑必須在 data_cache/models/ 下")
        rewritten = active.root / "models" / target.relative_to(allowed.resolve())
        active.spy.record(target, rewritten)
        rewritten.parent.mkdir(parents=True, exist_ok=True)
        return rewritten

    return wrapped


class RedirectPatchSet:
    """解析 S1–S11，原子安裝 inactive pass-through wrappers。"""

    def __init__(self) -> None:
        self.production_prefix = (_repo_root() / "data_cache").resolve()
        self._resolved: dict[str, ResolvedSeam] | None = None
        self._undos: list[Callable[[], None]] = []
        self._installed_ids: frozenset[str] = frozenset()

    @property
    def installed_ids(self) -> frozenset[str]:
        return self._installed_ids

    def _build_manifest(self) -> dict[str, ResolvedSeam]:
        orchestrator_mod = importlib.import_module("momentum.Analysis.ic_filter_orchestrator")
        reporter_mod = importlib.import_module("momentum.Analysis.ic_reporter")
        service_mod = importlib.import_module("api.services.ic_analysis_service")
        route_mod = importlib.import_module("api.routes.ic_analysis")
        lgb_mod = importlib.import_module("momentum.Analysis.lightgbm_analyzer")
        xgb_mod = importlib.import_module("momentum.Analysis.xgboost_analyzer")
        export_mod = importlib.import_module("tests.api.test_export_api")
        ff_test_mod = importlib.import_module("tests.test_feature_factory_e2e")

        def seam(
            seam_id: str,
            installers: Iterable[Callable[[], Callable[[], None]]],
            bucket: str,
        ) -> ResolvedSeam:
            def probe(root: Path) -> tuple[Path, ...]:
                return (root / bucket / f"{seam_id.lower()}_probe",)

            return ResolvedSeam(seam_id, tuple(installers), probe)

        orch_cls = orchestrator_mod.ICFilterOrchestrator
        reporter_cls = reporter_mod.ICReporter
        service_cls = service_mod.ICAnalysisService
        lgb_cls = lgb_mod.LightGBMAnalyzer
        xgb_cls = xgb_mod.XGBoostAnalyzer
        return {
            "S1": seam("S1", [
                _patch_attr(orch_cls, "_resolve_filtered_path", _method_path_resolver(orch_cls._resolve_filtered_path, "features")),
                _patch_attr(orch_cls, "_persist_outputs", _orchestrator_persist_wrapper(orch_cls._persist_outputs)),
            ], "features"),
            "S2": seam("S2", [
                _patch_attr(reporter_cls, "save_report", _reporter_wrapper(reporter_cls.save_report, "output_dir", "reports")),
                _patch_attr(reporter_cls, "save_filter_log", _reporter_wrapper(reporter_cls.save_filter_log, "output_dir", "reports")),
                _patch_attr(reporter_cls, "save_filtered_features", _reporter_wrapper(reporter_cls.save_filtered_features, "output_path", "features")),
            ], "reports"),
            "S3": seam("S3", [_patch_attr(service_cls, "_resolve_filtered_path", _method_path_resolver(service_cls._resolve_filtered_path, "features"))], "features"),
            "S4": seam("S4", [_patch_attr(service_mod, "Path", _redirect_path)], "reports/ic_ingest_cache"),
            "S5": seam("S5", [lambda: (lambda: None)], "reports/ic_ingest_cache"),
            "S6": seam("S6", [lambda: (lambda: None)], "reports"),
            "S7": seam("S7", [_patch_attr(route_mod, "_resolve_filtered_path", _function_path_resolver(route_mod._resolve_filtered_path, "features"))], "features"),
            "S8": seam("S8", [_patch_attr(route_mod, "Path", _redirect_path)], "reports"),
            "S9": seam("S9", [lambda: (lambda: None)] if callable(export_mod._export_fixture_filtered_path) else [], "features"),
            "S10": seam("S10", [
                _patch_attr(lgb_cls, "_resolve_model_path", _model_wrapper(lgb_cls._resolve_model_path)),
                _patch_attr(xgb_cls, "_resolve_model_path", _model_wrapper(xgb_cls._resolve_model_path)),
            ], "models"),
            "S11": seam("S11", [lambda: (lambda: None)] if callable(ff_test_mod._create_e2e_factory) else [], "features"),
        }

    def _validate(self, manifest: dict[str, ResolvedSeam]) -> None:
        if set(manifest) != REQUIRED_SEAM_IDS:
            raise RedirectCompletenessError(
                f"manifest IDs mismatch: {sorted(manifest)}"
            )
        for seam_id, resolved in manifest.items():
            if resolved.seam_id != seam_id or not resolved.installers or not callable(resolved.probe):
                raise RedirectCompletenessError(f"invalid seam: {seam_id}")
            minimum = MIN_INSTALLER_ARITY.get(seam_id, 1)
            if len(resolved.installers) < minimum:
                raise RedirectCompletenessError(
                    f"incomplete seam: {seam_id} requires at least {minimum} installers, "
                    f"got {len(resolved.installers)}"
                )

    def resolve_all(self) -> dict[str, ResolvedSeam]:
        try:
            manifest = self._build_manifest()
            self._validate(manifest)
        except RedirectCompletenessError:
            raise
        except Exception as exc:
            raise RedirectCompletenessError(str(exc)) from exc
        self._resolved = manifest
        return manifest

    def install_once(self) -> None:
        if self._installed_ids:
            return
        manifest = self.resolve_all()
        undos: list[Callable[[], None]] = []
        try:
            for seam_id in sorted(manifest, key=lambda item: int(item[1:])):
                for installer in manifest[seam_id].installers:
                    undos.append(installer())
        except Exception as exc:
            for undo in reversed(undos):
                undo()
            raise RedirectCompletenessError(f"atomic install failed: {exc}") from exc
        self._undos = undos
        self._installed_ids = frozenset(manifest)

    def activate(self, root: Path, *, owner: str) -> RedirectContext:
        global _ACTIVE
        with _LOCK:
            if _ACTIVE is not None:
                raise RuntimeError("redirect already active; pytest must remain serial")
            if self._installed_ids != REQUIRED_SEAM_IDS:
                self.install_once()
            if self._installed_ids != REQUIRED_SEAM_IDS:
                raise RedirectCompletenessError("not all seams are installed")
            redirect_root = root.resolve()
            redirect_root.mkdir(parents=True, exist_ok=True)
            for bucket in ("features", "reports", "models"):
                (redirect_root / bucket).mkdir(parents=True, exist_ok=True)
            active = ActiveRedirect(
                root=redirect_root,
                production_prefix=self.production_prefix,
                spy=ProductionWriteSpy(self.production_prefix),
                owner=owner,
            )
            _ACTIVE = active
            return RedirectContext(active)

    def deactivate(self, ctx: RedirectContext) -> None:
        global _ACTIVE
        with _LOCK:
            if _ACTIVE is not ctx.active:
                raise RuntimeError("redirect teardown ownership mismatch")
            _ACTIVE = None


def assert_context_clean(ctx: RedirectContext) -> None:
    if ctx.spy.violations:
        raise AssertionError(f"production write violations: {ctx.spy.violations}")
