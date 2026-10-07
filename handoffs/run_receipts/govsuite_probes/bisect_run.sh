#!/bin/bash
# git bisect run 用：BISECT_FILE、BISECT_K 指定測試；全綠 rc=0（good），有紅 rc=1（bad）
venv/bin/python -m pytest -q -p no:cacheprovider "$BISECT_FILE" -k "$BISECT_K" > /dev/null 2>&1
[ $? -eq 0 ] && exit 0 || exit 1
