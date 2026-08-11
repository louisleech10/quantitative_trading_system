"""GOVB0 `B4` — dispatch gate 的四個 fail-open 修復（站 5）。

出處：`docs/GOVB0_FRICTION_TODO.md` Task 2.3／2.4 ＋ 站 5 探路實測。
收斂：`handoffs/reconcile/20260811-govb0-b4-review-r1/synth.md`。

本檔每條「必須 BLOCK」的斷言都配一條 mutation，證明對應的實作要素是**承重**的。
🔴 `CODEX-R1-P1-04` 指出：B4 新增的家族分支原本只有文字錨點被 `_DRIFT` 釘住，
   **沒有任何正向行為測試與定向 mutation** ⇒ 未來刪掉它只會由字面錨點失敗揭露，
   而非語意測試。本檔補齊。
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

# 實作字面（mutation 錨點；漂移即 assert 失敗，不靜默改用較弱的變異）
WRAPPER = (
    "((eval|xargs|env|exec|command|nohup)[[:space:]]+"
    "(([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*"
    "|-[^[:space:];&|]*([[:space:]]+[^-[:space:];&|][^[:space:];&|]*)?"
    "|[0-9]+)[[:space:]]+)*)*"
)
SCRIPT_CLAUSE = "(cx_run|committee_run)\\\\.sh${_GL_TOKEND}"
NET_FAMILY_COND = (
    '_famtok="claude[^|]*(-p|--print)|(^|[[:space:];&|(\\`=])${_GL_FAMS}${_GL_TOKEND}"'
)


def _got(cmd: str, gate_dir: Path, script: Path = GATE_CHECK) -> str:
    """把指令字串餵給 gate_check 取判定。

    🔴 只餵字串，**絕不執行**——驗旁路不得真的派工（硬規矩）。
    """
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": cmd}}, ensure_ascii=False
    )
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
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


def _mut(tmp_path: Path, name: str, old: str, new: str) -> Path:
    """複製 gate_check.sh ＋ 變異後的 _gate_lex.sh 到同目錄；錨點失配即 fail。"""
    text = GATE_LEX.read_text(encoding="utf-8")
    assert old in text, f"mutation 錨點漂移：{name}"
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    gate = d / "mut_gate.sh"
    gate.write_text(GATE_CHECK.read_text(encoding="utf-8"), encoding="utf-8")
    gate.chmod(0o755)
    (d / "_gate_lex.sh").write_text(text.replace(old, new, 1), encoding="utf-8")
    return gate


# ---------------------------------------------------------------------------
# ① wrapper 前綴：eval／xargs／env／exec／command／nohup ＋ 其選項引數
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "env FOO=bar codex exec hi",
        "env -u FOO codex exec hi",          # CODEX-R1-P0-01：選項**的值**
        "env -i codex exec hi",
        "echo hi | xargs -n 1 codex exec",
        "xargs -I {} codex exec hi",         # CODEX-R1-P0-01
        "xargs -I {} -n 1 codex exec hi",
        "nohup codex exec hi",
        "command codex exec hi",
        "exec codex exec hi",
    ],
)
def test_b4_wrapper_prefixed_dispatch_blocks(tmp_path: Path, cmd: str) -> None:
    """wrapper 後面夾旗標／選項值／賦值，家族 CLI 仍須被擋。"""
    assert _got(cmd, tmp_path / "w") == "BLOCK", f"漏放：{cmd}"


def test_b4_wrapper_does_not_overblock_argument_position(tmp_path: Path) -> None:
    """wrapper 後的**裸 token** 不是旗標的值時，不得吃掉它去命中家族名。

    `xargs grep codex file` 實際跑的是 `grep`，`codex` 是搜尋字串 ⇒ 必須 ALLOW。
    這條擋住「把 wrapper 寫成吃任意 token」那種偷懶解法。
    """
    assert _got("xargs grep codex file", tmp_path / "wn") == "ALLOW"


def test_b4_mut_wrapper_drops_option_argument(tmp_path: Path) -> None:
    """mutation：wrapper 不再允許「旗標＋其值」⇒ `env -u FOO codex` 轉 ALLOW。"""
    old = "-[^[:space:];&|]*([[:space:]]+[^-[:space:];&|][^[:space:];&|]*)?"
    mut = _mut(tmp_path, "w_optarg", old, "-[^[:space:];&|]*")
    victim = "env -u FOO codex exec hi"
    assert _got(victim, tmp_path / "wob") == "BLOCK"
    assert _got(victim, tmp_path / "wom", script=mut) == "ALLOW"


# ---------------------------------------------------------------------------
# ② Task 2.4：官方外層派工腳本的呼叫點
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "bash scripts/cx_run.sh composer b.md o.md",
        "bash ./scripts/cx_run.sh composer b.md o.md",
        "bash scripts//cx_run.sh composer b.md o.md",
        "ROUND_ID=x bash scripts/cx_run.sh composer b.md o.md",
        "/bin/bash scripts/cx_run.sh composer b.md o.md",       # CODEX-R1-P0-02
        "env bash scripts/cx_run.sh composer b.md o.md",        # CODEX-R1-P0-02
        "xargs -n 1 bash scripts/cx_run.sh composer b.md o.md",  # CODEX-R1-P0-02
        "exec bash scripts/cx_run.sh composer b.md o.md",       # CODEX-R1-P0-02
        "bash -x scripts/cx_run.sh composer b.md o.md",
        "bash scripts/committee_run.sh --session s b.md o codex -- --task-id T",
        'bash -c "bash scripts/cx_run.sh composer b.md o.md"',  # 遞迴涵蓋
    ],
)
def test_b4_dispatch_script_callsite_blocks(tmp_path: Path, cmd: str) -> None:
    """直接叫派工腳本（含直譯器路徑前綴與 wrapper）須有 token 才放行。

    病：`cx_run.sh`／`committee_run.sh` **本身就是派工工具**，
    修前直接執行它們反而不需要 token ⇒ 用閘自己的工具就能繞過閘。
    """
    assert _got(cmd, tmp_path / "s") == "BLOCK", f"漏放：{cmd}"


@pytest.mark.parametrize(
    "cmd",
    [
        "sed -n '1,40p' scripts/cx_run.sh",
        "grep -n timeout scripts/cx_run.sh",
        "wc -l scripts/committee_run.sh",
        'echo "run cx_run.sh later"',
        "cat ./scripts/cx_run.sh",
        "./scripts/check_decoupling_phase4.sh",
    ],
)
def test_b4_dispatch_script_readonly_view_allows(tmp_path: Path, cmd: str) -> None:
    """唯讀查看派工腳本、或引數位置提到它，不得被擋。"""
    assert _got(cmd, tmp_path / "sn") == "ALLOW", f"誤擋：{cmd}"


def test_b4_gate_sh_stays_allowed(tmp_path: Path) -> None:
    """🔴 `gate.sh` 必須維持放行——它是取 token 的唯一路徑，納入會鎖死整個流程。"""
    assert _got("bash scripts/gate.sh dispatch --intent x --risk low", tmp_path / "g") == "ALLOW"
    assert _got("bash scripts/gate_check.sh", tmp_path / "g2") == "ALLOW"


def test_b4_mut_remove_script_callsite(tmp_path: Path) -> None:
    """mutation：拿掉腳本呼叫點判定 ⇒ 直接叫 cx_run.sh 轉 ALLOW。"""
    mut = _mut(tmp_path, "s_off", SCRIPT_CLAUSE, "(__never_matches__)\\\\.sh${_GL_TOKEND}")
    victim = "bash scripts/cx_run.sh composer b.md o.md"
    assert _got(victim, tmp_path / "sb") == "BLOCK"
    assert _got(victim, tmp_path / "sm", script=mut) == "ALLOW"


def test_b4_mut_script_callsite_bare_interpreter_only(tmp_path: Path) -> None:
    """mutation：直譯器不許帶路徑前綴 ⇒ `/bin/bash scripts/cx_run.sh` 轉 ALLOW。

    這條釘死 `CODEX-R1-P0-02` 的修法本體（初版只認裸 `bash|sh|zsh`）。
    """
    old = "((\\\\S*/)?(bash|sh|zsh)[[:space:]]+(-[^[:space:];&|]*[[:space:]]+)*)?"
    mut = _mut(tmp_path, "s_bare", old, "((bash|sh|zsh)[[:space:]]+)?")
    victim = "/bin/bash scripts/cx_run.sh composer b.md o.md"
    assert _got(victim, tmp_path / "sbb") == "BLOCK"
    assert _got(victim, tmp_path / "sbm", script=mut) == "ALLOW"


# ---------------------------------------------------------------------------
# ③ fail-closed 網的家族條件（argv[0] 由展開產生時）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "C=codex; $C exec hi",
        "$(printf codex) exec hi",
        "${FOO} exec hi; codex",
    ],
)
def test_b4_expansion_net_family_blocks(tmp_path: Path, cmd: str) -> None:
    """命令位置 token 由展開產生（argv[0] 靜態決定不了）＋ 出現家族名 ⇒ fail-closed。"""
    assert _got(cmd, tmp_path / "n") == "BLOCK", f"漏放：{cmd}"


@pytest.mark.parametrize(
    "cmd",
    [
        "$(printf echo) sp_codex.txt",        # CODEX-R1-P1-03：家族名只是檔名的一段
        "$(printf echo) /tmp/grok/notes.md",  # CODEX-R1-P1-03：家族名只是路徑的一段
        "$(printf echo) harmless",
        "cat sp_codex.txt",
        "mycodex --version",
        "pgrep -fl 'codex exec|cursor-agent|grok '",
    ],
)
def test_b4_expansion_net_does_not_overblock(tmp_path: Path, cmd: str) -> None:
    """家族名須為**獨立 token** 才算數；檔名／路徑中段不得觸發。

    出處 `CODEX-R1-P1-03`：初版條件 (b) 是整條找子字串，
    使 `$(printf echo) sp_codex.txt` 這種 argv[0] 明明是 `echo` 的指令被誤擋。
    """
    assert _got(cmd, tmp_path / "nn") == "ALLOW", f"誤擋：{cmd}"


def test_b4_mut_remove_net_family_condition(tmp_path: Path) -> None:
    """mutation：把網的家族條件拿掉（還原成只保護 claude）⇒ 動態賦值轉 ALLOW。

    🔴 這正是 `CODEX-R1-P1-04` 要求的定向 mutation：
       沒有它，未來刪掉家族條件只會由字面錨點失敗揭露，而非語意測試。
    """
    mut = _mut(tmp_path, "n_off", NET_FAMILY_COND, '_famtok="claude[^|]*(-p|--print)"')
    victim = "C=codex; $C exec hi"
    assert _got(victim, tmp_path / "nb") == "BLOCK"
    assert _got(victim, tmp_path / "nm", script=mut) == "ALLOW"


# ---------------------------------------------------------------------------
# ④ RSTART：bash -c 遞迴不得受前綴影響
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        'bash -c "codex exec hi"',
        ' bash -c "codex exec hi"',          # 只多一個開頭空格
        'a bash -c "codex exec hi"',
        'true; bash -c "codex exec hi"',
        '/bin/bash -c "codex exec hi"',
        '/bin/sh -c "codex exec hi"',
        '/usr/bin/env bash -c "codex exec hi"',
        'eval "codex exec hi"',
        'x; eval "codex exec hi"',
    ],
)
def test_b4_inner_extraction_is_prefix_independent(tmp_path: Path, cmd: str) -> None:
    """`bash -c`／`eval` 的內層抽取不得因前面有東西而失效。

    病：`j = i + RLENGTH` 未加 `RSTART - 1` ⇒ 只有落在掃描起點才正確。
    抽出來的是 `-c` 而非內層指令 ⇒ **開頭多一個空格就能繞過整道閘**。
    """
    assert _got(cmd, tmp_path / "r") == "BLOCK", f"漏放：{cmd}"


def test_b4_mut_drop_rstart_reintroduces_bypass(tmp_path: Path) -> None:
    """mutation：把 `RSTART - 1` 拿掉 ⇒ 帶前綴的 `bash -c` 派工轉 ALLOW。"""
    mut = _mut(
        tmp_path,
        "r_off",
        "j = i + RSTART - 1 + RLENGTH\n          if (j > n) break",
        "j = i + RLENGTH\n          if (j > n) break",
    )
    victim = 'true; bash -c "codex exec hi"'
    assert _got(victim, tmp_path / "rb") == "BLOCK"
    assert _got(victim, tmp_path / "rm", script=mut) == "ALLOW"
