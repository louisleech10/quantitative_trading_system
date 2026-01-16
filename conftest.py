"""
Pytest configuration file

設定測試環境和 Python 路徑
"""

import sys
import os
import importlib.util
from pathlib import Path

# 將專案根目錄加入 Python 路徑
project_root = Path(__file__).parent.absolute()
tests_path = project_root / "tests"

# 移除 tests 路徑，避免與專案模組命名衝突
if str(tests_path) in sys.path:
    sys.path.remove(str(tests_path))

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
else:
    sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))

# 不再加入 tests 路徑，避免 momentum 命名衝突
    
print(f"[conftest.py] Python path configured: {project_root}")
print(f"[conftest.py] sys.path[0]: {sys.path[0]}")


def _ensure_package(name: str, package_path: Path) -> None:
    if not package_path.exists():
        return

    if name in sys.modules:
        del sys.modules[name]

    spec = importlib.util.spec_from_file_location(
        name,
        package_path / "__init__.py",
        submodule_search_locations=[str(package_path)]
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module


_ensure_package("momentum", project_root / "momentum")
_ensure_package("api", project_root / "api")
