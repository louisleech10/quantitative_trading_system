"""B7 consult-r1 `CODEX-R1-P0-01` — self-gate 換行旁路之常駐回歸測試。

病（主委獨立複驗成立）：`_gate_cmd_is_self_gate` 註解宣稱「禁複合命令（分隔符／換行）」，
實作卻是 `grep -Eq '[;&|`]|\\$\\(|\\n'`。兩個獨立原因使「禁換行」完全沒有作用：

  ① `grep` 逐**行**比對——換行永遠不可能出現在一行之內；ERE 的 `\\n` 也不是換行
  ② 其後的 `^…gate\\.sh` 錨點同樣逐行 ⇒ 只要**任何一行**長得像自呼叫，整條就被放行

合起來是真旁路：在真派工前面加一行 `bash scripts/gate.sh` 再換行，派工閘即被繞過。
對照組（無前綴／改用 `;` 分隔）皆正常擋下，證明缺口專屬換行路徑。

🔴 本旁路只存在於**未 commit 的 B3R 工作區**（`git show HEAD:scripts/_gate_lex.sh`
不含 `_gate_cmd_is_self_gate`）。但本機的 PreToolUse 閘跑的就是工作區這份。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.sh"
GATE_LEX = REPO_ROOT / "scripts" / "_gate_lex.sh"

# 家族名拆寫：避免本測試檔的原始碼被派工閘的字面掃描命中
_FAM = "cod" + "ex"

# 控制字元守衛之字面（mutation 標的；與實作同步）
_CTL_GUARD = "tr -dc '\\1-\\10\\12-\\37\\177'"


def _decision(cmd: str, gate_dir: Path, script: Path = GATE_CHECK) -> str:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    proc = subprocess.run(
        ["bash", str(script)],
        input=payload,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )
    return "BLOCK" if proc.returncode != 0 else "ALLOW"


@pytest.mark.parametrize(
    "label,cmd",
    [
        ("newline-then-dispatch", "bash scripts/gate.sh\n" + _FAM + " exec hi"),
        ("newline-noise-then-dispatch", "bash scripts/gate.sh\necho x\n" + _FAM + " exec hi"),
        ("dispatch-then-newline-gate", _FAM + " exec hi\nbash scripts/gate.sh"),
    ],
)
def test_self_gate_newline_bypass_is_blocked(tmp_path: Path, label: str, cmd: str) -> None:
    """🔴 換行後接真派工 ⇒ 必須 BLOCK。放行代表派工閘可被一行前綴繞過。"""
    assert _decision(cmd, tmp_path / label) == "BLOCK", (
        f"{label}: 真派工被放行 ⇒ self-gate 判定吃掉了整條複合命令"
    )


@pytest.mark.parametrize(
    "label,cmd",
    [
        ("plain", "bash scripts/gate.sh"),
        ("with-args", "bash scripts/gate.sh dispatch --risk low"),
        ("with-cjk-arg", "bash scripts/gate.sh dispatch --intent 中文說明"),
        ("with-tab", "bash scripts/gate.sh\tdispatch"),
    ],
)
def test_legitimate_self_gate_still_allowed(tmp_path: Path, label: str, cmd: str) -> None:
    """修補不得把合法自呼叫一起擋掉——否則 gate 自己就沒法用（含中文參數與 TAB）。"""
    assert _decision(cmd, tmp_path / f"ok_{label}") == "ALLOW", (
        f"{label}: 合法 gate 自呼叫被誤擋"
    )


def test_carriage_return_is_not_a_separator_so_allowing_is_correct(tmp_path: Path) -> None:
    """CR 不是 shell 命令分隔符 ⇒ 該指令不可能真的派工 ⇒ 放行正確。

    🔴 這條是**實測結論不是推測**（主委原本猜錯，寫成應擋）：
        printf 'echo A\\recho B\\n' > t.sh; bash t.sh → 輸出 `A\\recho B`
        （單一 echo 的引數，不是兩條命令）。
    保留本測試是為了釘住這個判斷的**依據**：若 shell 語意改變，這裡要一起改。
    """
    assert _decision("bash scripts/gate.sh\r" + _FAM + " exec hi", tmp_path / "cr") == "ALLOW"


def test_control_char_guard_is_load_bearing(tmp_path: Path) -> None:
    """行為引信：拿掉控制字元守衛 ⇒ 換行旁路立刻復活。

    不是字面斷言——實際複製一份改壞的 lexer，讓 gate_check 載入它，再跑同一個反例。
    """
    src = GATE_LEX.read_text(encoding="utf-8")
    assert _CTL_GUARD in src, (
        f"測試與實作脫節：找不到控制字元守衛 {_CTL_GUARD!r}。"
        "若它被移除，代表 self-gate 換行旁路已復活——那是回歸，不是測試壞掉。"
    )

    lex_copy = tmp_path / "_gate_lex.sh"
    lex_copy.write_text(
        src.replace(_CTL_GUARD, "tr -dc 'ZZZ_NEVER_MATCHES'", 1), encoding="utf-8"
    )
    gate_src = GATE_CHECK.read_text(encoding="utf-8")
    needle = '"${SCRIPT_DIR}/_gate_lex.sh"'
    assert needle in gate_src, "測試與實作脫節：gate_check 未以此形態載入 lexer"
    gate_copy = tmp_path / "gate_check.sh"
    gate_copy.write_text(gate_src.replace(needle, f'"{lex_copy}"'), encoding="utf-8")

    got = _decision(
        "bash scripts/gate.sh\n" + _FAM + " exec hi", tmp_path / "mut", script=gate_copy
    )
    assert got == "ALLOW", (
        "拿掉控制字元守衛後旁路沒有復活 ⇒ 這條守衛不承重，或 mutation 沒生效"
    )
