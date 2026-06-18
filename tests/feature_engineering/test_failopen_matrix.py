"""Task 6.1 — 故障注入矩陣 [V-4][V-8]：真實 generate 五情境 quality_status/run_status。"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import types
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.factories import create_feature_factory, create_kline_storage_manager


ROOT = Path(__file__).resolve().parents[2]
KLINE_CACHE_DIR = "data_cache/feature_klines"
KLINE_PATH = ROOT / KLINE_CACHE_DIR / "kline_cache.h5"
MATRIX_SYMBOL = "BTCUSDT"
MATRIX_TF = "12h"
SHORT_WINDOW_DAYS = 21
FROZEN_DOC = ROOT / "docs/FF_FAILOPEN_FROZEN_TESTS.md"
BASELINE_COMMIT = "d654237"
ASSERTION_RE = re.compile(
    r"^\s*(assert\b|pytest\.raises|with pytest\.raises|assert_frame_equal|assert_series_equal)"
)


def _freeze_baseline_module():
    spec = importlib.util.spec_from_file_location(
        "freeze_failopen_baseline",
        ROOT / "scripts/freeze_failopen_baseline.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _apply_baseline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    freeze = _freeze_baseline_module()
    for name, value in freeze.FIXED_ENV.items():
        monkeypatch.setenv(name, value)


def _short_window_dates() -> tuple[str, str]:
    """短視窗：末 21 天，避免全寬 L6.5 ADF 爆炸。"""
    with h5py.File(KLINE_PATH, "r") as handle:
        ts = np.asarray(handle[f"/{MATRIX_SYMBOL}/{MATRIX_TF}/data"]["timestamp"], dtype=np.int64)
    end_epoch = int(ts.max())
    end = pd.Timestamp(end_epoch, unit="s", tz="UTC")
    start = end - pd.Timedelta(days=SHORT_WINDOW_DAYS)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _fast_config_payload(**overrides: object) -> dict:
    """關閉 L6.5 重預處理；矩陣 ①–④ 用此配置控時長。"""
    payload = {
        "timeframes": {
            "primary": MATRIX_TF,
            "training": [MATRIX_TF],
            "alignment_mode": "open_minus",
        },
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "preprocessing": {"enabled": False},
    }
    payload.update(overrides)
    return payload


def _multi_tf_config_payload(**overrides: object) -> dict:
    base = _fast_config_payload()
    base["timeframes"] = {
        "primary": "12h",
        "training": ["12h", "1h"],
        "alignment_mode": "open_minus",
    }
    base.update(overrides)
    return base


def _make_factory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, feature_root: Path | None = None):
    if not KLINE_PATH.is_file():
        pytest.skip(f"missing real kline cache: {KLINE_PATH}")
    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR, validate_continuity=False)
    storage_root = feature_root or (tmp_path / "features")
    factory._storage = FeatureStorage(str(storage_root))
    return factory


def _status_pair(metadata: dict) -> tuple[str, str]:
    quality = str(metadata.get("quality_status", ""))
    run_status = str(metadata.get("run_status", quality))
    return quality, run_status


def _git_output(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return proc.stdout


def _function_ranges(source: str) -> tuple[list[tuple[int, int, str]], dict[str, set[str]]]:
    tree = ast.parse(source)
    ranges: list[tuple[int, int, str]] = []
    callers: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        ranges.append((node.lineno, node.end_lineno or node.lineno, node.name))
        if node.name.startswith("test_"):
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    callers.setdefault(child.func.id, set()).add(node.name)
    return ranges, callers


def _owner_for_line(ranges: list[tuple[int, int, str]], line_no: int) -> str | None:
    owners = [name for start, end, name in ranges if start <= line_no <= end]
    return owners[-1] if owners else None


def _changed_assertion_tests(path: str) -> set[str]:
    old_source = _git_output("show", f"{BASELINE_COMMIT}:{path}")
    new_source = _git_output("show", f"HEAD:{path}")
    old_ranges, _ = _function_ranges(old_source)
    new_ranges, callers = _function_ranges(new_source)
    diff = _git_output("diff", "-U0", f"{BASELINE_COMMIT}..HEAD", "--", path)

    changed: set[str] = set()
    old_line = new_line = 0
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            assert match is not None, raw
            old_line, new_line = int(match.group(1)), int(match.group(2))
            continue
        if raw.startswith(("---", "+++")) or not raw:
            continue
        sign, line = raw[0], raw[1:]
        if sign == "-":
            if ASSERTION_RE.search(line):
                owner = _owner_for_line(old_ranges, old_line)
                if owner:
                    changed.add(owner)
            old_line += 1
        elif sign == "+":
            if ASSERTION_RE.search(line):
                owner = _owner_for_line(new_ranges, new_line)
                if owner:
                    changed.update(callers.get(owner, {owner}))
            new_line += 1
        else:
            old_line += 1
            new_line += 1
    return {name for name in changed if name.startswith("test_")}


def test_v8_frozen_doc_covers_every_existing_assertion_change() -> None:
    """[V-8] d654237..HEAD 每個既有 test assertion owner 都須列在 frozen doc。"""
    assert FROZEN_DOC.is_file()
    frozen = FROZEN_DOC.read_text(encoding="utf-8")
    wildcard_paths = {
        match.group(1)
        for line in frozen.splitlines()
        if (match := re.match(r"^\|\s*`([^`]+\.py)`\s*\|", line))
    }
    baseline_files = set(
        _git_output("ls-tree", "-r", "--name-only", BASELINE_COMMIT, "tests/").splitlines()
    )
    changed_files = _git_output("diff", "--name-only", f"{BASELINE_COMMIT}..HEAD", "--", "tests/")

    missing: list[str] = []
    for path in changed_files.splitlines():
        if path not in baseline_files or not path.endswith(".py"):
            continue
        for test_name in sorted(_changed_assertion_tests(path)):
            if path not in wildcard_paths and (path not in frozen or test_name not in frozen):
                missing.append(f"{path}::{test_name}")
    assert not missing, "frozen doc missing assertion changes:\n" + "\n".join(missing)


@pytest.fixture
def _require_kline() -> None:
    if not KLINE_PATH.is_file():
        pytest.skip(f"missing real kline cache: {KLINE_PATH}")


def test_matrix_whole_layer_failure_fail_closed(
    _require_kline: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """① 整層失敗：required engine 例外，預設 fail-closed → raise。"""
    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates()

    def _boom(self, ohlcv):  # noqa: ANN001
        del self, ohlcv
        raise RuntimeError("injected required trend failure")

    monkeypatch.setattr(TrendIndicatorEngine, "compute_all", _boom)

    with pytest.raises(RuntimeError, match="Layer 1 failed"):
        factory.generate_features(
            MATRIX_SYMBOL,
            MATRIX_TF,
            config_override=_fast_config_payload(),
            force_regenerate=True,
            start_date=start,
            end_date=end,
            persist=False,
        )


def test_matrix_whole_layer_failure_partial_status(
    _require_kline: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """① 整層失敗 + allow_partial_layers：續行並標 partial。"""
    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates()

    def _boom(self, ohlcv):  # noqa: ANN001
        del self, ohlcv
        raise RuntimeError("injected required trend failure")

    monkeypatch.setattr(TrendIndicatorEngine, "compute_all", _boom)

    result = factory.generate_features(
        MATRIX_SYMBOL,
        MATRIX_TF,
        config_override=_fast_config_payload(allow_partial_layers=True),
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    quality, run_status = _status_pair(result.metadata)
    assert quality == "partial"
    assert run_status == "partial"
    assert any("L1" in layer for layer in result.metadata.get("failed_layers", []))


def test_matrix_nan_ratio_exceeds_marks_partial(
    _require_kline: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """② NaN 超標：真實 generate + max_nan_ratio=0 → partial。"""
    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates()

    result = factory.generate_features(
        MATRIX_SYMBOL,
        MATRIX_TF,
        config_override=_fast_config_payload(max_nan_ratio=0.0),
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    quality, run_status = _status_pair(result.metadata)
    assert quality == "partial"
    assert run_status == "partial"
    assert result.metadata.get("quality_thresholds")


def test_matrix_partial_tf_failure_fail_closed_and_partial(
    _require_kline: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """③ 部分 TF 失敗：預設 raise；allow_partial_timeframes → partial + failed_timeframes。"""
    start, end = _short_window_dates()
    factory = _make_factory(monkeypatch, tmp_path)
    original_l1 = factory._layer1_atomic_indicators

    def _fail_1h(self, data, config):  # noqa: ANN001
        if str(getattr(self, "_current_timeframe", "")) == "1h":
            raise RuntimeError("injected 1h TF pipeline failure")
        return original_l1(data, config)

    monkeypatch.setattr(factory, "_layer1_atomic_indicators", types.MethodType(_fail_1h, factory))

    with pytest.raises(RuntimeError, match="Timeframe 1h failed"):
        factory.generate_features(
            MATRIX_SYMBOL,
            "12h",
            config_override=_multi_tf_config_payload(),
            force_regenerate=True,
            start_date=start,
            end_date=end,
            persist=False,
        )

    factory = _make_factory(monkeypatch, tmp_path)
    monkeypatch.setattr(factory, "_layer1_atomic_indicators", types.MethodType(_fail_1h, factory))
    result = factory.generate_features(
        MATRIX_SYMBOL,
        "12h",
        config_override=_multi_tf_config_payload(allow_partial_timeframes=True),
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    quality, run_status = _status_pair(result.metadata)
    assert quality == "partial"
    assert run_status == "partial"
    assert "1h" in result.metadata.get("failed_timeframes", [])


def test_matrix_cgsa_tf_failure_rollback_state(
    _require_kline: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """④ CGSA TF 失敗：rollback 後 registry 無該 TF 殘留 group / 檔案。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    start, end = _short_window_dates()
    factory = _make_factory(monkeypatch, tmp_path)
    original_l1 = factory._layer1_atomic_indicators
    work_dir = Path(tmp_path / "cgsa_work")

    def _fail_1h(self, data, config):  # noqa: ANN001
        if str(getattr(self, "_current_timeframe", "")) == "1h":
            raise RuntimeError("injected CGSA 1h TF failure")
        return original_l1(data, config)

    monkeypatch.setattr(factory, "_layer1_atomic_indicators", types.MethodType(_fail_1h, factory))

    with pytest.raises(RuntimeError, match="Timeframe 1h failed"):
        factory.generate_features(
            MATRIX_SYMBOL,
            "12h",
            config_override=_multi_tf_config_payload(),
            force_regenerate=True,
            start_date=start,
            end_date=end,
            persist=False,
        )

    registry = factory._cgsa_registry
    assert registry is not None
    remaining = set(registry._groups.keys())
    assert not any(group_id.startswith("1h_") for group_id in remaining)
    assert not list(work_dir.glob("*1h*"))


def test_matrix_l65_failure_degrades_metadata(
    _require_kline: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """⑤ L6.5 失敗：降級續行，preprocessing_applied=False + partial。"""
    factory = _make_factory(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    start, end = _short_window_dates()

    def _boom(_frame, _config):  # noqa: ANN001
        raise RuntimeError("injected preprocessing failure")

    monkeypatch.setattr(factory, "_layer6_5_pre_ic", _boom)

    result = factory.generate_features(
        MATRIX_SYMBOL,
        MATRIX_TF,
        config_override={
            **_fast_config_payload(),
            "preprocessing": {"enabled": True},
        },
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    quality, run_status = _status_pair(result.metadata)
    assert result.metadata.get("preprocessing_applied") is False
    assert result.metadata.get("effective_preprocessing_config")
    assert quality == "partial"
    assert run_status == "partial"
    assert any("L6.5" in reason for reason in result.metadata.get("failure_reasons", []))
