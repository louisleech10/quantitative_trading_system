"""R2/R3 AST import scanner 的 fail-closed regression 矩陣。"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNER_PATH = REPO_ROOT / "scripts" / "check_decoupling_imports.py"
SPEC = importlib.util.spec_from_file_location("check_decoupling_imports", SCANNER_PATH)
assert SPEC is not None and SPEC.loader is not None
scanner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scanner
SPEC.loader.exec_module(scanner)


def _manifest_table(rows: Iterable[tuple[str, str, str, str, str]]) -> str:
    """建立與 production 相同 schema 的獨立 fixture manifest。"""
    lines = [
        "# Fixture allowlist",
        "",
        "| module | allowed_symbols | module_import | owner | contract |",
        "|---|---|---|---|---|",
    ]
    lines.extend(f"| {' | '.join(row)} |" for row in rows)
    lines.extend(("", "## 戳記", ""))
    return "\n".join(lines)


def _write_tree(
    tmp_path: Path,
    source: str,
    *,
    domain: str = "A",
    rows: Iterable[tuple[str, str, str, str, str]] | None = None,
) -> tuple[Path, list[Path], Path]:
    """建立隔離的 momentum/api roots 與 fixture manifest。"""
    momentum_root = tmp_path / "momentum"
    source_dir = momentum_root / domain
    source_dir.mkdir(parents=True)
    (source_dir / "source.py").write_text(source, encoding="utf-8")
    api_root = tmp_path / "api" / "services"
    api_root.mkdir(parents=True)
    manifest = tmp_path / "allowlist.md"
    default_rows = [("momentum.B.util", "ok_fn", "deny", "fixture-owner", "fixture contract")]
    manifest.write_text(_manifest_table(rows or default_rows), encoding="utf-8")
    return momentum_root, [api_root], manifest


def _scan(
    momentum_root: Path,
    api_roots: list[Path],
    manifest: Path,
) -> scanner.ScanResult:
    """測試只在函式層注入 stamp verifier。"""
    return scanner.scan(
        momentum_root,
        api_roots,
        manifest,
        stamp_verifier=lambda _: (True, "fixture stamp PASS"),
    )


def _scan_service(tmp_path: Path, source: str, relative: str = "foo.py") -> scanner.ScanResult:
    """建立可解析 repo-relative module 的隔離 service tree。"""
    momentum_root, api_roots, manifest = _write_tree(tmp_path, "x = 1\n")
    service_file = api_roots[0] / relative
    service_file.parent.mkdir(parents=True, exist_ok=True)
    service_file.write_text(source, encoding="utf-8")
    return _scan(momentum_root, api_roots, manifest)


def test_allowed_module_and_symbol_pass(tmp_path: Path) -> None:
    """矩陣①：精準 module+symbol 白名單通過。"""
    roots = _write_tree(tmp_path, "from momentum.B.util import ok_fn\n")
    result = _scan(*roots)
    assert result.count("R2") == 0
    assert result.violations == ()


def test_allowed_module_rejects_runlease_symbol(tmp_path: Path) -> None:
    """矩陣②：module 已列入仍不得放行未列的 RunLease。"""
    rows = [
        (
            "momentum.FeatureEngineering.run_locks",
            "RunBusyError,is_run_active",
            "deny",
            "fixture-owner",
            "fixture contract",
        )
    ]
    roots = _write_tree(
        tmp_path,
        "from momentum.FeatureEngineering.run_locks import RunLease\n",
        rows=rows,
    )
    result = _scan(*roots)
    assert result.count("R2") == 1
    assert result.violations[0].target.endswith("run_locks.RunLease")


@pytest.mark.parametrize(
    "source,form",
    [
        ("from momentum.FeatureEngineering.feature_library import FeatureLibrary\n", "from"),
        ("import momentum.FeatureEngineering.feature_library\n", "import"),
    ],
)
def test_non_allowlisted_feature_library_rejected(
    tmp_path: Path,
    source: str,
    form: str,
) -> None:
    """矩陣③：feature_library 的 from/import 兩形式皆紅。"""
    result = _scan(*_write_tree(tmp_path, source))
    assert result.count("R2") == 1
    assert result.violations[0].form == form


@pytest.mark.parametrize("indent", ["", "  ", "    ", "        ", "\t"])
@pytest.mark.parametrize(
    "statement",
    [
        "from momentum.B.blocked import bad_fn",
        "import momentum.B.blocked",
    ],
)
def test_all_legal_indentation_forms_are_scanned(
    tmp_path: Path,
    indent: str,
    statement: str,
) -> None:
    """矩陣④：top/2/4/8/tab 的 from/import 都被 AST 掃描。"""
    source = f"{statement}\n" if not indent else f"def deferred():\n{indent}{statement}\n"
    result = _scan(*_write_tree(tmp_path, source))
    assert result.count("R2") == 1


def test_inline_multiple_aliases_are_individually_checked(tmp_path: Path) -> None:
    """矩陣⑤：同行多 alias 不得因第一個安全 import 而漏掃。"""
    result = _scan(
        *_write_tree(tmp_path, "import os, momentum.FeatureEngineering.feature_library\n")
    )
    assert result.count("R2") == 1
    assert result.violations[0].target == "momentum.FeatureEngineering.feature_library"


@pytest.mark.parametrize(
    "source",
    [
        "from momentum.FeatureEngineering.consumer_gate_v2 import allowed_fn\n",
        "from momentum.FeatureEngineeringXconsumer_gate import allowed_fn\n",
    ],
)
def test_near_miss_module_names_are_rejected(tmp_path: Path, source: str) -> None:
    """矩陣⑥：prefix/regex near-miss 不得命中精準 module。"""
    rows = [
        (
            "momentum.FeatureEngineering.consumer_gate",
            "allowed_fn",
            "deny",
            "fixture-owner",
            "fixture contract",
        )
    ]
    result = _scan(*_write_tree(tmp_path, source, rows=rows))
    assert result.count("R2") == 1


def test_wildcard_import_is_rejected(tmp_path: Path) -> None:
    """矩陣⑦：白名單 module 仍拒絕 wildcard。"""
    result = _scan(*_write_tree(tmp_path, "from momentum.B.util import *\n"))
    assert result.count("R2") == 1
    assert result.violations[0].target == "momentum.B.util.*"


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "zero-byte",
        "unreadable",
        "comments-only",
        "duplicate",
        "invalid-module",
        "empty-owner",
        "empty-symbols",
    ],
)
def test_malformed_manifest_full_spectrum_fails_closed(tmp_path: Path, case: str) -> None:
    """矩陣⑧：manifest 八種 malformed 輸入全 fail-closed。"""
    momentum_root, api_roots, manifest = _write_tree(tmp_path, "x = 1\n")
    valid = ("momentum.B.util", "ok_fn", "deny", "fixture-owner", "fixture contract")
    if case == "missing":
        manifest.unlink()
    elif case == "zero-byte":
        manifest.write_text("", encoding="utf-8")
    elif case == "unreadable":
        manifest.unlink()
        manifest.mkdir()
    elif case == "comments-only":
        manifest.write_text("# no table\n<!-- comment -->\n", encoding="utf-8")
    elif case == "duplicate":
        manifest.write_text(_manifest_table([valid, valid]), encoding="utf-8")
    elif case == "invalid-module":
        manifest.write_text(
            _manifest_table([("momentum.bad-name", *valid[1:])]), encoding="utf-8"
        )
    elif case == "empty-owner":
        manifest.write_text(
            _manifest_table([(valid[0], valid[1], valid[2], "", valid[4])]), encoding="utf-8"
        )
    elif case == "empty-symbols":
        manifest.write_text(
            _manifest_table([(valid[0], "", valid[2], valid[3], valid[4])]), encoding="utf-8"
        )
    with pytest.raises(scanner.ScannerError):
        _scan(momentum_root, api_roots, manifest)


def test_r2_same_domain_passes_and_cross_domain_fails(tmp_path: Path) -> None:
    """矩陣⑨：同域 import 綠，跨域未豁免 import 紅。"""
    source = "from momentum.A.util import same_domain\nfrom momentum.B.blocked import cross_domain\n"
    result = _scan(*_write_tree(tmp_path, source))
    assert result.count("R2") == 1
    assert result.violations[0].target == "momentum.B.blocked.cross_domain"


def test_cli_rejects_stamp_bypass_option() -> None:
    """矩陣⑩：production CLI 不存在 stamp bypass。"""
    completed = subprocess.run(
        [sys.executable, str(SCANNER_PATH), "--skip-stamp-check"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "unrecognized arguments" in completed.stderr


def test_real_manifest_schema_is_valid_and_supports_both_tables() -> None:
    """真 manifest 僅驗 schema，不讓 fixture 語義受 production 內容影響。"""
    entries = scanner.load_manifest(REPO_ROOT / "scripts" / "decouple_allowlist.md")
    assert entries
    assert all(scanner.MODULE_RE.fullmatch(module) for module in entries)
    assert len(entries) == len(set(entries))


def test_syntax_error_in_scanned_python_fails_closed(tmp_path: Path) -> None:
    """語法錯誤的 Python 檔不得被靜默跳過。"""
    roots = _write_tree(tmp_path, "def broken(:\n")
    with pytest.raises(scanner.ScannerError, match="Python 檔無法解析"):
        _scan(*roots)


def test_rejected_stamp_verifier_fails_before_scanning(tmp_path: Path) -> None:
    """production 同語意的 stamp 拒絕會 fail-closed。"""
    momentum_root, api_roots, manifest = _write_tree(tmp_path, "x = 1\n")
    with pytest.raises(scanner.ScannerError, match="戳記驗證失敗"):
        scanner.scan(
            momentum_root,
            api_roots,
            manifest,
            stamp_verifier=lambda _: (False, "fixture rejected"),
        )


@pytest.mark.parametrize(
    "source",
    [
        "from api.services.bar import Service\n",
        "import api.services.bar\n",
        "from api.services import bar\n",
        "from api import services\n",
    ],
)
def test_r4_other_service_and_package_forms_are_rejected(
    tmp_path: Path, source: str
) -> None:
    """R4 矩陣①-④：他 service 與兩種 package 聚合形式全紅。"""
    result = _scan_service(tmp_path, source)
    assert result.count("R4") == 1


@pytest.mark.parametrize(
    "source",
    [
        "from api.routes.config import router\n",
        "from api import routes\n",
        "from ..routes import config\n",
    ],
)
def test_r4_routes_absolute_aggregate_and_relative_are_rejected(
    tmp_path: Path, source: str
) -> None:
    """R4 矩陣⑤-⑦：routes 絕對、聚合、相對三式全紅。"""
    result = _scan_service(tmp_path, source)
    assert result.count("R4") == 1


@pytest.mark.parametrize(
    "source",
    ["from .bar import Service\n", "from . import bar\n"],
)
def test_r4_relative_service_forms_resolve_then_reject(
    tmp_path: Path, source: str
) -> None:
    """R4 矩陣⑧-⑨：相對 import 先 resolve 再判紅。"""
    result = _scan_service(tmp_path, source)
    assert result.count("R4") == 1
    assert result.violations[0].target == "api.services.bar"


def test_r4_nested_same_basename_is_not_self(tmp_path: Path) -> None:
    """R4 矩陣⑩：nested foo 不得用 basename 誤豁免頂層 foo。"""
    result = _scan_service(
        tmp_path,
        "from api.services.foo import Service\n",
        relative="sub/foo.py",
    )
    assert result.count("R4") == 1


def test_r4_init_has_no_special_exemption(tmp_path: Path) -> None:
    """R4 矩陣⑪：services/__init__.py 沒有 package 特權。"""
    result = _scan_service(
        tmp_path,
        "from api.services.foo import Service\n",
        relative="__init__.py",
    )
    assert result.count("R4") == 1


def test_r4_init_package_import_is_still_rejected(tmp_path: Path) -> None:
    """R4 矩陣⑪b：__init__ 內 import api.services 仍屬 package-level 紅。"""
    result = _scan_service(tmp_path, "import api.services\n", relative="__init__.py")
    assert result.count("R4") == 1


def test_r4_exact_absolute_self_is_only_self_exemption(tmp_path: Path) -> None:
    """R4 矩陣⑫：絕對完整 module 精確等值的 self from/import 綠。"""
    result = _scan_service(
        tmp_path,
        "from api.services.foo import Service\nimport api.services.foo\n",
    )
    assert result.count("R4") == 0


def test_r4_package_level_self_spelling_is_still_rejected(tmp_path: Path) -> None:
    """R4 矩陣⑬：from api.services import foo 即使在 foo.py 仍紅。"""
    result = _scan_service(tmp_path, "from api.services import foo\n")
    assert result.count("R4") == 1


def test_r4_api_models_import_is_green(tmp_path: Path) -> None:
    """R4 矩陣⑭：非禁止面的 api.models import 綠。"""
    result = _scan_service(tmp_path, "import api.models.case_models\n")
    assert result.count("R4") == 0


def test_r4_multi_alias_and_semicolon_are_all_scanned(tmp_path: Path) -> None:
    """R4 矩陣⑮：多 alias/分號行不漏掃。"""
    result = _scan_service(
        tmp_path,
        "import api.models.case_models, api.services.bar; import api.routes.config\n",
    )
    assert result.count("R4") == 2


def test_r4_type_checking_import_is_rejected(tmp_path: Path) -> None:
    """R4 TYPE_CHECKING 獨立測：條件式型別 import 仍是依賴。"""
    result = _scan_service(
        tmp_path,
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from .bar import Service\n",
    )
    assert result.count("R4") == 1


def test_r4_overlevel_relative_import_resolves_before_check(tmp_path: Path) -> None:
    """R4 邊界：越層 from ...api import services resolve 後仍紅。"""
    result = _scan_service(tmp_path, "from ...api import services\n")
    assert result.count("R4") == 1


def _scan_model(
    tmp_path: Path,
    source: str,
    rows: Iterable[tuple[str, str, str, str, str]] | None = None,
) -> scanner.ScanResult:
    """建立含 api/models root 的 R3 隔離樹。"""
    momentum_root, api_roots, manifest = _write_tree(tmp_path, "x = 1\n", rows=rows)
    models_root = tmp_path / "api" / "models"
    models_root.mkdir(parents=True)
    (models_root / "model.py").write_text(source, encoding="utf-8")
    return _scan(momentum_root, [*api_roots, models_root], manifest)


def test_r3_models_non_allowlisted_momentum_import_is_rejected(tmp_path: Path) -> None:
    """R3 models 矩陣①：未白名單的 momentum concrete import 紅。"""
    result = _scan_model(
        tmp_path,
        "from momentum.FeatureEngineering.feature_library import FeatureLibrary\n",
    )
    assert result.count("R3") == 1


@pytest.mark.parametrize(
    "source",
    [
        "from momentum.core.config import FeatureConfig\n",
        "from momentum.factories import create_feature_factory\n",
    ],
)
def test_r3_models_core_and_factories_imports_are_green(
    tmp_path: Path, source: str
) -> None:
    """R3 models 矩陣②-③：canonical core/factories 邊界維持綠。"""
    result = _scan_model(tmp_path, source)
    assert result.count("R3") == 0


def test_r3_models_supported_timeframes_precise_symbol_is_allowed(tmp_path: Path) -> None:
    """R3 models 矩陣④：SUPPORTED_TIMEFRAMES 僅精準 symbol 放行。"""
    rows = [
        (
            "momentum.FeatureEngineering.feature_config",
            "SUPPORTED_TIMEFRAMES",
            "deny",
            "committee/DECOUPLE-SCAN2",
            "fixture contract",
        )
    ]
    result = _scan_model(
        tmp_path,
        "from momentum.FeatureEngineering.feature_config import SUPPORTED_TIMEFRAMES\n",
        rows=rows,
    )
    assert result.count("R3") == 0
