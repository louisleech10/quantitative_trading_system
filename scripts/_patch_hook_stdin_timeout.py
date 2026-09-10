"""一次性修補：五個 hook 腳本的 stdin 讀取加上逾時，避免永遠掛住。

事故（2026-09-11 使用者發現）：`factkey_write_guard.sh` 有兩個實例從 9/10 22:45／22:51
掛到隔天 07:00，共 **8 小時**，狀態 S、CPU 0%。根因是 hook 在
「stdin 不是 tty」時就假設 payload 會來，於是 `json.load(sys.stdin)`／`cat` 無限等待——
`[ -t 0 ]` 分得出「終端機 vs 非終端機」，**分不出「等一下會有資料的管道」與
「永遠不會有資料、也永遠不關閉的管道」**。兩個掛住的 hook 讓它們所屬的
背景任務（HANDOFF commit）整整 8 小時沒有完成，且**完全無聲**。

修法：讀 stdin 之處一律加 `signal.alarm(_HOOK_STDIN_TIMEOUT)`（預設 5 秒）。
逾時 ⇒ python 被 SIGALRM 殺掉 ⇒ 既有的 `|| true` 讓變數為空 ⇒ 走各腳本**既有的**
「取不到目標就放行」分支。**語意不變，只是不再無限等**。
（不改成 fail-closed 的理由：掛住時該工具呼叫本來就永遠不會完成＝最糟的形態；
而這些腳本原本在「stdin 是 tty」時就已經是放行語意，逾時走同一條路才一致。）

用法：`venv/bin/python scripts/_patch_hook_stdin_timeout.py`（冪等；已修補者跳過）。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: 逾時秒數——hook 的 payload 若真的要來，是同一個 process 在毫秒內寫入的。
TIMEOUT = 5

PY_OLD = "python3 -c 'import json,sys\n"
PY_NEW = (
    "python3 -c 'import json,signal,sys\n"
    f"signal.alarm({TIMEOUT})   # hook stdin 逾時：永不關閉的管道曾讓本 hook 掛住 8 小時\n"
)

PY_OLD_MULTILINE = "python3 -c '\nimport json, sys\n"
PY_NEW_MULTILINE = (
    "python3 -c '\nimport json, signal, sys\n"
    f"signal.alarm({TIMEOUT})   # hook stdin 逾時：永不關閉的管道曾讓本 hook 掛住 8 小時\n"
)

CAT_OLD = 'payload="$(cat)"'
CAT_NEW = (
    'payload="$(python3 -c \'import signal,sys\n'
    f"signal.alarm({TIMEOUT})   # 同上：bare cat 對永不關閉的管道會無限等\n"
    "sys.stdout.write(sys.stdin.read())' 2>/dev/null || true)\""
)

TARGETS = [
    "scripts/status_marker_check.sh",
    "scripts/doc_format_precheck.sh",
    "scripts/factkey_write_guard.sh",
    "scripts/list_active_mechanisms.sh",
    "scripts/narrow_check_router.sh",
]


def main() -> int:
    changed = 0
    for rel in TARGETS:
        path = REPO / rel
        src = path.read_text(encoding="utf-8")
        original = src
        if "signal.alarm" in src:
            print(f"  = {rel}（已修補，跳過）")
            continue
        src = src.replace(PY_OLD, PY_NEW)
        src = src.replace(PY_OLD_MULTILINE, PY_NEW_MULTILINE)
        src = src.replace(CAT_OLD, CAT_NEW)
        if src == original:
            print(f"  ✗ {rel}：**沒有命中任何錨點**——請手動確認（不靜默略過）")
            return 1
        path.write_text(src, encoding="utf-8")
        changed += 1
        print(f"  ✓ {rel}")
    print(f"\nPATCHED={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
