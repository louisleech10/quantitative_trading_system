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


def _is_package_module(module: str, repo_root: Path) -> bool:
    """依 repo 路徑判斷 module 是否為任意深度 package。"""
    return (repo_root.joinpath(*module.split("."))).is_dir()


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
            package_level = base == "api" or (
                _is_r4_module(base) and _is_package_module(base, repo_root)
            )
            if package_level:
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


BASELINE_HEADER = """\
# decouple_baseline.txt — canonical Rule 2/3/4 之**既有債** baseline（自動生成，勿手改）
#
# 這份檔案的意思是：下列違反是 CLAUDE.md 記載的既有 P2 債，**已知、已具名、待清**；
# scanner 掛上自動路徑後只擋「不在本清單內的新增違反」，不會因既有債而擋死日常編輯。
#
# 🔴 這不是豁免，是**債的清單**。每還一條就會印 BASELINE RESOLVED，屆時應把該列刪掉。
# 🔴 鍵不含行號（否則每次編輯就整批失效）；代價＝同檔同標的再多加一個 import 抓不到。
#
# 重生成：venv/bin/python scripts/check_decoupling_imports.py \\
#           --baseline scripts/decouple_baseline.txt --update-baseline
# 該指令會把當下所有違反吸收成「可接受」⇒ 其 diff 必須經 review 才可 commit。
"""


def baseline_key(violation: Violation, repo_root: Path) -> str:
    """單筆違反的**群組**鍵：`<repo 相對路徑>|<規則>|<形式>|<標的>`。不含行號。

    🔴 不含行號的理由：既有債散在會被日常編輯的檔裡，
    含行號的 baseline 每改一行就整批失效，等於沒有 baseline。

    🔴 但只有群組鍵**不夠**〔`CODEX-R1-P1-05`〕：同一檔對同一標的**再多加一個** import
    會落在同一個鍵上，被誤當成既有債放行。⇒ 對外的 baseline 鍵由
    `baseline_keys()` 產生，會在群組鍵後綴 occurrence 序號。本函式只負責群組。
    """
    try:
        rel = violation.path.resolve().relative_to(repo_root)
    except ValueError:
        rel = violation.path
    return f"{rel}|{violation.rule}|{violation.form}|{violation.target}"


def baseline_keys(violations: Iterable[Violation], repo_root: Path) -> list[str]:
    """完整 baseline 鍵集合：群組鍵 ＋ `|#<序號>`。

    序號 ＝ 同一群組內依**行號排序**後的序位（1 起算）。

    為什麼這樣既穩又準〔`CODEX-R1-P1-05`〕：
      · 行號整批位移（上面插了幾行）⇒ 群組成員與序位皆不變 ⇒ baseline 仍成立
      · 同一檔對同一標的**多加一個** import ⇒ 該群組多出 `#N+1` ⇒ **判為新增**
      · 還掉一個 ⇒ 少一個序號 ⇒ 印 BASELINE RESOLVED
    """
    grouped: dict[str, list[Violation]] = {}
    for v in violations:
        grouped.setdefault(baseline_key(v, repo_root), []).append(v)
    keys: list[str] = []
    for gkey, items in grouped.items():
        for idx, _ in enumerate(sorted(items, key=lambda x: x.line), start=1):
            keys.append(f"{gkey}|#{idx}")
    return sorted(keys)


def load_baseline(path: Path) -> set[str]:
    """讀 baseline；缺檔即 ScannerError（fail-closed，不得靜默視為空集合）。

    🔴 「檔不在就當成沒有 baseline 然後放行」正是本專案 S1.2 抓到的 fail-open 病灶。
    空檔（0 筆）是**合法且最嚴格**的 baseline：任何違反都算新增。
    """
    if not path.is_file():
        raise ScannerError(f"baseline 檔不存在: {path}（缺檔不得視為零違反）")
    keys = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        keys.add(line)
    return keys


def main(argv: Sequence[str] | None = None) -> int:
    """Production CLI；刻意不提供任何 stamp bypass。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        help="既有債之 baseline 檔；觀測集合為其子集即通過（只擋新增違反）",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="把現況寫回 --baseline 指定之檔（大聲印出；產出須經 review 才可 commit）",
    )
    args = parser.parse_args(argv)
    if args.update_baseline and not args.baseline:
        print("ERROR: --update-baseline 須同時指定 --baseline", file=sys.stderr)
        return 2
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

    if not args.baseline:
        return 1 if result.violations else 0

    bpath = Path(args.baseline)
    if not bpath.is_absolute():
        bpath = repo_root / bpath
    observed = set(baseline_keys(result.violations, repo_root))

    if args.update_baseline:
        body = BASELINE_HEADER + "\n".join(sorted(observed)) + ("\n" if observed else "")
        bpath.write_text(body, encoding="utf-8")
        print(f"BASELINE UPDATED: {bpath} ({len(observed)} 筆)")
        print("🔴 這個動作會把現有違反全部吸收成『可接受』——產出必須經 review 才可 commit。")
        return 0

    try:
        known = load_baseline(bpath)
    except ScannerError as exc:
        print(f"DECOUPLING IMPORT SCANNER ERROR: {exc}", file=sys.stderr)
        return 1

    new_keys = sorted(set(observed) - known)
    resolved = sorted(known - set(observed))
    for key in resolved:
        print(f"BASELINE RESOLVED（債已還，可自 baseline 移除）: {key}")
    if new_keys:
        print(
            f"DECOUPLING NEW VIOLATIONS: {len(new_keys)} 筆不在 baseline 內 → 拒絕",
            file=sys.stderr,
        )
        for key in new_keys:
            print(f"  NEW: {key}", file=sys.stderr)
        print(
            "  修：把違反改掉（canonical Rule 2/3/4，見 CLAUDE.md）。"
            "確定要納入既有債才跑 --update-baseline，且該 diff 須經 review。",
            file=sys.stderr,
        )
        return 1
    print(f"BASELINE OK: 觀測 {len(observed)} 筆全在 baseline（{len(known)} 筆）內，無新增違反")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
