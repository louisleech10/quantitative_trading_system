"""
Pytest configuration file

設定測試環境和 Python 路徑
"""

import sys
import os
from pathlib import Path

# 將專案根目錄加入 Python 路徑
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
print(f"[conftest.py] Python path configured: {project_root}")
print(f"[conftest.py] sys.path[0]: {sys.path[0]}")
