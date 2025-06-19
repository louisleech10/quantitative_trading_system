#!/usr/bin/env python3
"""
Case Search API 啟動腳本
用於啟動FastAPI開發服務器
"""

import sys
import os
from pathlib import Path

# 確保項目根目錄在Python路徑中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函數"""
    try:
        # 導入API模組
        from api.main import run_server
        
        print("正在啟動 Case Search API 服務器...")
        print("按 Ctrl+C 停止服務器")
        print("-" * 50)
        
        # 運行服務器
        run_server()
        
    except KeyboardInterrupt:
        print("\n服務器已停止")
    except ImportError as e:
        print(f"導入錯誤: {e}")
        print("請確保所有依賴都已安裝: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"啟動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()