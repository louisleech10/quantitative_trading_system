#!/usr/bin/env python3
"""以 AST 檢查 canonical Rule 2 / Rule 3 / Rule 4 的具體 import。"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


MODULE_RE = re.compile(r"^momentum(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
REQUIRED_COLUMNS = ("module", "allowed_symbols", "module_import", "owner", "contract")
StampVerifier = Callable[[Path], tuple[bool, str]]


class ScannerError(RuntimeError):
    """Scanner 輸入或原始碼無法安全判讀。"""


@dataclass(frozen=True)
class AllowEntry:
    """單一 module 的精準豁免。"""

    symbols: frozenset[str]
    module_import: bool


@dataclass(frozen=True)
class Violation:
    """一筆可定位的 import 違規。"""

    path: Path
    line: int
    rule: str
    form: str
    target: str

    def render(self) -> str:
        """輸出穩定且可供 receipt 歸因的單行格式。"""
        return f"{self.path}:{self.line}:{self.rule}:{self.form}:{self.target}"


@dataclass(frozen=True)
class ScanResult:
    """掃描結果與分規則計數。"""

    violations: tuple[Violation, ...]

    def count(self, rule: str) -> int:
        """回傳指定規則的違規數。"""
        return sum(item.rule == rule for item in self.violations)


def verify_manifest_stamp(manifest_path: Path) -> tuple[bool, str]:
    """用專案 canonical verifier 驗 manifest 戳記。"""
    script = Path(__file__).with_name("reconcile_stamps_check.sh")
    completed = subprocess.run(
        ["bash", str(script), str(manifest_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    message = (completed.stdout + completed.stderr).strip()
    return completed.returncode == 0, message


def load_manifest(manifest_path: Path) -> dict[str, AllowEntry]:
    """讀取並嚴格驗證 Markdown manifest 表格。"""
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ScannerError(f"manifest 不可讀: {manifest_path}: {exc}") from exc
    if not text.strip():
        raise ScannerError(f"manifest 為空: {manifest_path}")

    table_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if not table_lines:
        raise ScannerError(f"manifest 僅註解或缺 Markdown 表格: {manifest_path}")

    entries: dict[str, AllowEntry] = {}
    expecting_separator = False
    saw_header = False
    for row_number, row in enumerate(table_lines, start=1):
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if tuple(cells) == REQUIRED_COLUMNS:
            if expecting_separator:
                raise ScannerError(f"manifest 第 {row_number} 列缺表格分隔列")
            saw_header = True
            expecting_separator = True
            continue
        if expecting_separator:
            if len(cells) != len(REQUIRED_COLUMNS) or any(
                not cell or set(cell) != {"-"} for cell in cells
            ):
                raise ScannerError(f"manifest 第 {row_number} 列表格分隔格式錯誤")
            expecting_separator = False
            continue
        if not saw_header:
            raise ScannerError(
                f"manifest 欄位錯誤: 預期 {'/'.join(REQUIRED_COLUMNS)}, 實得 {'/'.join(cells)}"
            )
        if len(cells) != len(REQUIRED_COLUMNS):
            raise ScannerError(f"manifest 第 {row_number} 列欄數錯誤")
        module, symbols_text, module_import_text, owner, contract = cells
        if not MODULE_RE.fullmatch(module):
            raise ScannerError(f"manifest module 名非法: {module or '<empty>'}")
        if module in entries:
            raise ScannerError(f"manifest module 重複: {module}")
        symbols = [symbol.strip() for symbol in symbols_text.split(",") if symbol.strip()]
        if not symbols:
            raise ScannerError(f"manifest allowed_symbols 空白: {module}")
        if "*" in symbols or any(not symbol.isidentifier() for symbol in symbols):
            raise ScannerError(f"manifest allowed_symbols 非顯式合法 symbol: {module}")
        if module_import_text not in {"allow", "deny"}:
            raise ScannerError(f"manifest module_import 須為 allow/deny: {module}")
        if not owner:
            raise ScannerError(f"manifest owner 空白: {module}")
        if not contract:
            raise ScannerError(f"manifest contract 空白: {module}")
        entries[module] = AllowEntry(frozenset(symbols), module_import_text == "allow")
    if expecting_separator:
        raise ScannerError(f"manifest 表格缺分隔列: {manifest_path}")
    if not entries:
        raise ScannerError(f"manifest 表格無條目: {manifest_path}")
    return entries


def _python_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.exists():
            yield from sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _parse(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ScannerError(f"Python 檔無法解析: {path}: {exc}") from exc


def _is_exempt_target(module: str) -> bool:
    return module == "momentum.factories" or module.startswith("momentum.core.")


def _manifest_decision(
    module: str,
    symbol: str | None,
    entries: dict[str, AllowEntry],
) -> bool:
    entry = entries.get(module)
    if entry is None:
        return False
    if symbol is None:
        return entry.module_import
    return symbol != "*" and symbol in entry.symbols


def _node_targets(
    node: ast.Import | ast.ImportFrom,
    entries: dict[str, AllowEntry],
) -> Iterable[tuple[str, str | None, str]]:
    """展開 AST node；包層級 from-import module 依 module_import 判定。"""
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name, None, "import"
        return
    if node.level or not node.module:
        return
    for alias in node.names:
        nested_module = f"{node.module}.{alias.name}"
        if nested_module in entries:
            yield nested_module, None, "from-module"
        else:
            yield node.module, alias.name, "from"


def _source_domain(path: Path, momentum_root: Path) -> str | None:
    try:
        relative = path.relative_to(momentum_root)
    except ValueError:
        return None
    if not relative.parts or relative.parts[0] in {"core", "tests"}:
        return None
    if relative.name in {"factories.py", "contracts.py"}:
        return None
    return relative.parts[0]


def _target_domain(module: str) -> str | None:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "momentum" else None


def _source_module(path: Path, repo_root: Path) -> tuple[str, bool]:
    """以 repo-relative path 算出完整 source module 與 package 身分。"""
    try:
        relative = path.relative_to(repo_root)
    except ValueError as exc:
        raise ScannerError(f"R4 source 不在 repo root 下: {path}") from exc
    parts = list(relative.with_suffix("").parts)
    is_package = bool(parts and parts[-1] == "__init__")
    if is_package:
        parts.pop()
    if not parts:
        raise ScannerError(f"R4 source module 無法解析: {path}")
    return ".".join(parts), is_package


def _resolve_relative_module(
    node: ast.ImportFrom,
    source_module: str,
    source_is_package: bool,
) -> str:
    """依 Python package 語意先把相對 ImportFrom resolve 成絕對 module。"""
    if node.level == 0:
        return node.module or ""
    package = source_module if source_is_package else source_module.rpartition(".")[0]
    parts = package.split(".") if package else []
    ascend = node.level - 1
    if ascend > len(parts):
        base_parts: list[str] = []
    elif ascend:
        base_parts = parts[:-ascend]
    else:
        base_parts = parts
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _is_r4_module(module: str) -> bool:
    """判斷目標是否落在 R4 的 services/routes 禁止面。"""
    return module == "api.services" or module.startswith("api.services.") or (
        module == "api.routes" or module.startswith("api.routes.")
    )


def _scan_r4_file(path: Path, repo_root: Path) -> list[Violation]:
    """掃描單一 service；相對 import 必先 resolve，self 僅精確 module 等值。"""
    source_module, source_is_package = _source_module(path, repo_root)
    violations: list[Violation] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                package_level = alias.name in {"api.services", "api.routes"}
                if _is_r4_module(alias.name) and (
                    package_level or alias.name != source_module
                ):
                    violations.append(Violation(path, node.lineno, "R4", "import", alias.name))
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        base = _resolve_relative_module(node, source_module, source_is_package)
        for alias in node.names:
            package_level = base in {"api", "api.services", "api.routes"}
            if base == "api" and alias.name in {"services", "routes"}:
                target = f"api.{alias.name}"
            elif base in {"api.services", "api.routes"}:
                target = f"{base}.{alias.name}"
            else:
                target = base
            if not _is_r4_module(target):
                continue
            if not package_level and target == source_module:
                continue
            violations.append(Violation(path, node.lineno, "R4", "from", target))
    return violations


def _scan_file(
    path: Path,
    rule: str,
    entries: dict[str, AllowEntry],
    source_domain: str | None = None,
) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(_parse(path)):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for module, symbol, form in _node_targets(node, entries):
            if not module.startswith("momentum.") or _is_exempt_target(module):
                continue
            if rule == "R2" and _target_domain(module) == source_domain:
                continue
            if not _manifest_decision(module, symbol, entries):
                target = module if symbol is None else f"{module}.{symbol}"
                violations.append(Violation(path, node.lineno, rule, form, target))
    return violations


def scan(
    momentum_root: Path,
    api_roots: Sequence[Path],
    manifest_path: Path,
    stamp_verifier: StampVerifier = verify_manifest_stamp,
    service_root: Path | None = None,
) -> ScanResult:
    """掃描 R2/R3/R4；測試可在函式層注入 verifier，CLI 永遠用真 verifier。"""
    ok, message = stamp_verifier(manifest_path)
    if not ok:
        raise ScannerError(f"戳記驗證失敗: {message or manifest_path}")
    entries = load_manifest(manifest_path)
    violations: list[Violation] = []
    for path in _python_files([momentum_root]):
        domain = _source_domain(path, momentum_root)
        if domain is not None:
            violations.extend(_scan_file(path, "R2", entries, domain))
    for path in _python_files(api_roots):
        violations.extend(_scan_file(path, "R3", entries))
    if service_root is None:
        service_root = next(
            (root for root in api_roots if root.name == "services" and root.parent.name == "api"),
            None,
        )
    if service_root is not None:
        repo_root = momentum_root.parent
        for path in _python_files([service_root]):
            violations.extend(_scan_r4_file(path, repo_root))
    return ScanResult(tuple(sorted(violations, key=lambda item: (str(item.path), item.line, item.target))))


def main(argv: Sequence[str] | None = None) -> int:
    """Production CLI；刻意不提供任何 stamp bypass。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    try:
        result = scan(
            repo_root / "momentum",
            [
                repo_root / "api" / name
                for name in ("services", "routes", "websocket", "models")
            ],
            repo_root / "scripts" / "decouple_allowlist.md",
            service_root=repo_root / "api" / "services",
        )
    except ScannerError as exc:
        print(f"DECOUPLING IMPORT SCANNER ERROR: {exc}", file=sys.stderr)
        return 1
    for violation in result.violations:
        print(violation.render())
    print(f"R2={result.count('R2')} R3={result.count('R3')} R4={result.count('R4')}")
    return 1 if result.violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
