"""GOVB0 Task 2.2 ＝ GOVB1 Task 3.2 — `claude` 段收窄（票 B-26 重號，同一件工作）。

TEST-2.2-* 對應 docs/GOVB0_FRICTION_TODO.md Phase 2 / Task 2.2；
T-3.2-* 對應 docs/GOVB1_INPUT_QUALITY_TODO.md Phase 3 / Task 3.2。

判定實作位於 ``scripts/_gate_lex.sh`` 之 ``_gate_lex_match_scan``
（非兩份 TODO 所寫的 ``gate_check.sh:86``——B3R 已把詞法移出，
``gate_check.sh:116`` 自承；20260809-govb1-b7-consult-r1 兩家裁定 (A)）。

本檔每個 mutation 都證明「拿掉某條實作要素 ⇒ 某條斷言由綠轉紅」，
即該要素是**承重**的，非裝飾。
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
FIX = REPO_ROOT / "tests" / "governance" / "fixtures" / "govb1"

# _gate_lex.sh 內 claude 段正則之字面（mutation 錨點；漂移即 assert 失敗）
# 🔴 GOVB0 B4 r3：claude 段原本自寫命令位置與 wrapper，是**第五個消費點**
#    （`CODEX-R3-P0-02`／`COMPOSER-R3-P1-01` 兩家獨立找到）⇒ 已改為引用共用式。
#    錨點隨之更新為組裝行全文；`$` 因在雙引號內故為 `\$`。
CLAUDE_PAT = (
    '_pat="${_GL_CMDPOS}${_GL_WRAPPER}((\\\\S*/)?)claude'
    '([[:space:]][^;&|]*)?[[:space:]](-p|--print([[:space:]=]|\\$))"'
)
# 旗標尾段之字面（MUT-e 錨點）
FLAG_TAIL = "[[:space:]](-p|--print([[:space:]=]|\\$))"

# fail-closed 網之字面（CODEX-R1-P0-01 修法；stamp-r1 收窄觸發條件）
# NET_TRIGGER＝「命令位置 token 含展開／萬用字元 metachar」之判準（MUT-k 錨點）
# 🔴 GOVB0 B4 r3：命令位置／wrapper／家族清單／後界四個子式已收斂成
#    `_gate_lex.sh` 頂部的**單一定義**（`_GL_CMDPOS` 等，`CODEX-R2-P0-01` 之修法）。
#    mutation 錨點隨之改為釘**變數定義那一行**，而不是釘組裝後的整串正則：
#    整串正則每次擴充都會漂（本 epic 已因此改過四次錨點），變數定義不會。
# 🔴 GOVB0 B4 r4（`CODEX-R3-P1-04`）：下列常數在 r3 被引入為「錨點」，但**從未被任何測試使用**
#    ⇒ 死重。更糟的是 `GL_TOKEND_DEF` 的字面停在 r3 修 `CODEX-R3-P0-01`（`$IFS` 拆詞）**之前**
#    的舊值——沒人用，所以漂了也沒人發現。**看似有錨點，實則既不承重也不正確。**
#    r4 的處置不是刪掉它們，而是把它們接上下方 `_DIRECTED_MUTATIONS`，變成真正的承重錨點。
# `GL_WRAPPER_DEF = "_GL_WRAPPER='"` 已刪（`GROK-R5-P2-01`）：它只是個前綴字串，
# 既無法當取代錨點、也從未被使用；承重錨點改由下方 `GL_WRAPPER_ALT` 承擔。
GL_WRAPPER_ALT = "(eval|xargs|env|exec|command|nohup)"
GL_FAMS_DEF = "_GL_FAMS='(codex|cursor-agent|grok|agy)'"
GL_TOKEND_DEF = "_GL_TOKEND='([[:space:];&|()<>`$]|$)'"  # r4 更正：補回 `$`
GL_DASHC_TAIL = "[[:space:]]+)*-[a-zA-Z]*c'"
# 網的家族條件（組裝點）——mutation 需單獨剝除它以還原「只剩一層保護」的前提。
NET_FAMILY_COND = (
    '_famtok="claude[^|]*(-p|--print)|(^|[[:space:];&|(\\`=])${_GL_FAMS}${_GL_TOKEND}"'
)
# 網的觸發條件（組裝點）
NET_TRIGGER = '_pat="${_GL_CMDPOS}${_GL_WRAPPER}[^[:space:];&|]*[\\$\\`!*?~[]"'
NET_BLOCK = (
    "  " + NET_TRIGGER + "\n"
    "  " + NET_FAMILY_COND + "\n"
    '  if printf \'%s\' "$s" | grep -Eq "${_pat}" \\\n'
    '    && printf \'%s\' "$s" | grep -Eq "${_famtok}"; then\n'
    "    return 0\n"
    "  fi\n"
)


def _run_gate(
    payload: str,
    *,
    gate_dir: Path,
    script: Path = GATE_CHECK,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    return subprocess.run(
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


def _got(cmd: str, gate_dir: Path, *, script: Path = GATE_CHECK) -> str:
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": cmd}},
        ensure_ascii=False,
    )
    gate_dir.mkdir(parents=True, exist_ok=True)
    proc = _run_gate(payload, gate_dir=gate_dir, script=script)
    return "ALLOW" if proc.returncode == 0 else "BLOCK"


def _got_fixture(name: str, gate_dir: Path) -> str:
    gate_dir.mkdir(parents=True, exist_ok=True)
    payload = (FIX / f"{name}.json").read_text(encoding="utf-8")
    proc = _run_gate(payload, gate_dir=gate_dir)
    return "ALLOW" if proc.returncode == 0 else "BLOCK"


def _mut_lex(tmp: Path, name: str, old: str, new: str) -> Path:
    """複製 gate_check.sh + 改壞的 _gate_lex.sh 到同目錄，回傳 gate 路徑。"""
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    assert old in lex_text, f"mutation 錨點漂移: {old!r}"
    lex_m = lex_text.replace(old, new, 1)
    assert lex_m != lex_text
    gate = d / "mut_gate.sh"
    gate.write_text(GATE_CHECK.read_text(encoding="utf-8"), encoding="utf-8")
    gate.chmod(0o755)
    (d / "_gate_lex.sh").write_text(lex_m, encoding="utf-8")
    return gate


# ---------------------------------------------------------------------------
# TEST-2.2-FP4 — 四條現場唯讀指令由 BLOCK 轉 ALLOW
# ---------------------------------------------------------------------------

_FP4 = [
    "head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD",
    "cat .claude/tmp/x.txt; git rev-parse HEAD",
    "ls /private/tmp/claude-501/; git status --porcelain",
    'find .claude/tmp -name "*.md" -print',
]


def test_22_fp4_four_read_only_now_allow(tmp_path: Path) -> None:
    """TEST-2.2-FP4：四條全由 BLOCK 轉 ALLOW。

    誤擋成因（收窄前）：``claude[^|]*(-p|--print)`` 是子字串比對，
    路徑中的 ``claude`` 配上句中的 ``rev-parse``／``--porcelain``／``-print``
    即命中。收窄後 ``claude`` 不在命令位置 ⇒ 不再進入旗標判定。
    """
    for i, cmd in enumerate(_FP4):
        assert _got(cmd, tmp_path / f"fp{i}") == "ALLOW", cmd


def test_22_tp_real_claude_still_block(tmp_path: Path) -> None:
    """TEST-2.2-TP：真的子代理派工維持 BLOCK。"""
    assert _got('claude -p "x"', tmp_path / "tp0") == "BLOCK"
    assert _got('claude --print "x"', tmp_path / "tp1") == "BLOCK"


def test_22_pipe_after_pipe_still_block(tmp_path: Path) -> None:
    """TEST-2.2-PIPE：管線後真派工 BLOCK。

    🔴 **凍結 TODO 的 from 態有誤**：
    ``phase2_expected_flips.txt:26`` 記 ``flip ALLOW BLOCK``，
    但實測 **pre-phase2 快照 gate 已是 BLOCK**
    （``tests/governance/fixtures/gate_check_pre_phase2/gate_check.sh``）——
    ``[^|]*`` 擋的是 claude **右側**的 ``|``，本例的 ``|`` 在 claude **左側**，
    故舊式子字串比對本來就命中。⇒ 這條是 maintain 而非 flip。
    to 態（BLOCK）不受影響，本測即以 to 態為準。
    詳見 docs/GOV_B7_SCOPE_AMENDMENT.md §2。
    """
    assert _got('cat x | claude -p "y"', tmp_path / "pipe0") == "BLOCK"


def test_22_regress_cmdsub_and_abspath_still_block(tmp_path: Path) -> None:
    """TEST-2.2-REGRESS：收窄到命令位置後，命令替換／絕對路徑不得退化為 ALLOW。"""
    assert _got('v=$(claude -p "hi")', tmp_path / "rg0") == "BLOCK"
    assert _got('/usr/local/bin/claude --print "x"', tmp_path / "rg1") == "BLOCK"


# ---------------------------------------------------------------------------
# 邊界（GOVB0 2.2 邊界 ①②③ ＋ GOVB1 3.2 邊界 ①②）
# ---------------------------------------------------------------------------


def test_22_boundaries(tmp_path: Path) -> None:
    """邊界五條。"""
    # GOVB0 ①：claude 在檔名中段 → ALLOW
    assert _got("cat my-claude-notes.md", tmp_path / "b0") == "ALLOW"
    # GOVB0 ②：絕對路徑 → BLOCK（已於 REGRESS 覆蓋，此處為邊界欄具名）
    assert _got("/usr/local/bin/claude -p x", tmp_path / "b1") == "BLOCK"
    # GOVB0 ③：-p 為他人旗標且無 claude → ALLOW
    assert _got("grep -p foo bar.txt", tmp_path / "b2") == "ALLOW"
    # GOVB1 ①：--print 出現在引號內 → ALLOW
    assert (
        _got('git commit -m "claude --print 說明"', tmp_path / "b3") == "ALLOW"
    )
    # GOVB1 ②：路徑（帶前綴）即 claude 本身且有獨立旗標 → 仍須擋
    assert _got("./bin/claude --print x", tmp_path / "b4") == "BLOCK"


def test_22_flag_must_follow_claude_in_same_segment(tmp_path: Path) -> None:
    """旗標須在 claude **之後**且**同一分隔符區段**內。

    兩條都是 ALLOW：claude 有出現在命令位置，但該段內其後沒有 print 旗標
    （無旗標的 claude ＝ 互動式，非 headless 派工；收窄前後語意一致）。
    """
    # 旗標在 claude 之前
    assert _got("grep -p foo; claude bar", tmp_path / "s0") == "ALLOW"
    # 旗標在 claude 之後但跨到下一段
    assert _got("claude foo; grep -p bar", tmp_path / "s1") == "ALLOW"


def test_32_govb1_assert_pair(tmp_path: Path) -> None:
    """GOVB1 Task 3.2 兩條 ASSERT。

    ``gatecmd_claude_path`` → rc=0（ALLOW）；``gatecmd_claude_p_real`` → rc!=0（BLOCK）。
    """
    assert _got_fixture("gatecmd_claude_path", tmp_path / "f0") == "ALLOW"
    assert _got_fixture("gatecmd_claude_p_real", tmp_path / "f1") == "BLOCK"


def test_22_recursion_into_bash_c_preserved(tmp_path: Path) -> None:
    """-c 遞迴內的 claude 派工維持 BLOCK（與語料 t21-recurse-claude-c 同案）。"""
    assert _got('bash -c "claude -p x"', tmp_path / "rc0") == "BLOCK"


# ---------------------------------------------------------------------------
# TEST-2.2-MUT — 每條實作要素都證明承重
# ---------------------------------------------------------------------------


def test_22_mut_restore_substring_reblocks_fp4(tmp_path: Path) -> None:
    """MUT-a（TODO 指定）：還原子字串比對 → FP4 四條轉回 BLOCK。

    這是本 Task 存在理由的可證偽證據：若實作沒真的收窄，本測的 base
    與 mut 兩側會一樣，斷言即失效。
    """
    # 🔴 B4 r3：CLAUDE_PAT 現在是一整行**賦值**，替換後必須仍是合法賦值，
    #    否則 `_pat` 未定義、grep 收到空樣式 ⇒ 測到的是「腳本壞掉」而非「還原子字串比對」。
    mut = _mut_lex(tmp_path, "muta", CLAUDE_PAT, '_pat="claude[^|]*(-p|--print)"')
    for i, cmd in enumerate(_FP4):
        assert _got(cmd, tmp_path / f"mabase{i}") == "ALLOW", f"base {cmd}"
        assert _got(cmd, tmp_path / f"mamut{i}", script=mut) == "BLOCK", f"mut {cmd}"
    # 真派工在 mutation 下仍 BLOCK（mutation 未把 gate 整個關掉）
    assert _got('claude -p "x"', tmp_path / "matp", script=mut) == "BLOCK"


def test_22_mut_drop_cmdsub_position_allows_regress(tmp_path: Path) -> None:
    """MUT-b（TODO 指定）：命令替換形態受**三層**保護，逐層剝除才會漏放。

    三層：① claude 段正則的命令位置含 ``$(`` 與裸 ``(``（``$(`` 的左括號本身就落在
    分隔符集合，故 ① 須同時拿掉兩者）② ``_gate_lex_extract_cmdsubs`` 會把
    ``claude -p hi`` 抽出另行掃描，行首即命中 ③ 展開標記 fail-closed 網
    （`CODEX-R1-P0-01` 修法；``v=$(...)`` 含 ``$``）。

    🔴 本測同時斷言**縱深防禦**：只剝 ①② 仍 BLOCK（③ 接住），三層全剝才 ALLOW。
    TODO 原文只寫「移除 ``$(`` ⇒ 轉 ALLOW」，那是 ③ 尚不存在時的敘述。
    """
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    # 🔴 B4 r3：命令位置定義已收斂成 `_GL_CMDPOS`，① 改為縮該定義（不再改 claude 段本身）。
    cmdpos_def = "_GL_CMDPOS='(^|[;&|(`]|\\$\\()[[:space:]]*'"
    cmdpos_narrow = "_GL_CMDPOS='(^|[;&|`])[[:space:]]*'"
    assert cmdpos_def in lex_text, "MUT-b 錨點漂移：_GL_CMDPOS 定義"
    assert CLAUDE_PAT in lex_text, "MUT-b 錨點漂移：claude 段組裝行"
    anchor_sub = 'cmdsubs="$(_gate_lex_extract_cmdsubs "$raw")"'
    assert anchor_sub in lex_text, "MUT-b 錨點漂移：cmdsubs 抽取"
    assert NET_BLOCK in lex_text, "MUT-b 錨點漂移：fail-closed 網"

    def _install(text: str, name: str) -> Path:
        d = tmp_path / name
        d.mkdir(parents=True, exist_ok=True)
        gate = d / "mut_gate.sh"
        gate.write_text(GATE_CHECK.read_text(encoding="utf-8"), encoding="utf-8")
        gate.chmod(0o755)
        (d / "_gate_lex.sh").write_text(text, encoding="utf-8")
        return gate

    two_layers = lex_text.replace(cmdpos_def, cmdpos_narrow, 1).replace(
        anchor_sub, 'cmdsubs=""', 1
    )
    all_layers = two_layers.replace(NET_BLOCK, "", 1)
    assert all_layers != two_layers != lex_text

    victim = 'v=$(claude -p "hi")'
    assert _got(victim, tmp_path / "mbbase") == "BLOCK"
    gate2 = _install(two_layers, "mutb2")
    assert _got(victim, tmp_path / "mb2", script=gate2) == "BLOCK", "③ 應接住"
    gate3 = _install(all_layers, "mutb3")
    assert _got(victim, tmp_path / "mb3", script=gate3) == "ALLOW"
    # 裸派工不受此 mutation 影響 → 仍 BLOCK（證明 mutation 是定向的）
    assert _got('claude -p "x"', tmp_path / "mbtp", script=gate3) == "BLOCK"


def test_22_mut_drop_path_prefix_allows_abspath(tmp_path: Path) -> None:
    """MUT-c：拿掉路徑前綴 ``(\\S*/)?`` → 絕對／相對路徑 claude 轉 ALLOW。

    證明路徑前綴是承重的（否則 ``/usr/local/bin/claude -p x`` 會漏放）。
    """
    # B4 r3：claude 段改為變數組裝後，檔內字面為 `((\\S*/)?)claude`（雙引號內的跳脫）。
    mut = _mut_lex(
        tmp_path, "mutc", "((\\\\S*/)?)claude", "claude"
    )
    assert (
        _got('/usr/local/bin/claude --print "x"', tmp_path / "mcbase") == "BLOCK"
    )
    assert (
        _got('/usr/local/bin/claude --print "x"', tmp_path / "mcmut", script=mut)
        == "ALLOW"
    )
    assert _got('claude -p "x"', tmp_path / "mctp", script=mut) == "BLOCK"


def test_22_mut_drop_segment_bound_overblocks(tmp_path: Path) -> None:
    """MUT-d：把 ``[^;&|]*`` 放寬成 ``.*`` → 跨段旗標開始誤擋。

    證明「同一分隔符區段」這個限制是承重的（否則 ``claude foo; grep -p bar``
    這種無關指令會被擋）。
    """
    mut = _mut_lex(
        tmp_path,
        "mutd",
        "claude([[:space:]][^;&|]*)?" + FLAG_TAIL,
        "claude([[:space:]].*)?" + FLAG_TAIL,
    )
    assert _got("claude foo; grep -p bar", tmp_path / "mdbase") == "ALLOW"
    assert (
        _got("claude foo; grep -p bar", tmp_path / "mdmut", script=mut) == "BLOCK"
    )


def test_22_mut_exact_token_flag_regresses_glued_form(tmp_path: Path) -> None:
    """MUT-e（🔴 硬規矩 9 證據）：旗標改為 grep -qx 式**全等** → 併寫形態漏放。

    凍結 TODO 的 ``_has_flag()`` 參考實作用 ``grep -qx -e '-p' -e '--print'``
    ＝ token 全等。但 shell 會把 ``claude -p"do it"`` 併成單一 token
    ``-pdo it``，全等版比對不到 ⇒ 這條**現行 BLOCK 的真派工**會退化為 ALLOW，
    正是「收窄型修法不得使該擋的從此不受檢」所禁止的。
    本實作故採 token **起始**比對；本測是該偏離的承重證據。
    偏離理由與委員裁決見 docs/GOV_B7_SCOPE_AMENDMENT.md §3。
    """
    mut = _mut_lex(
        tmp_path,
        "mute",
        FLAG_TAIL,
        "[[:space:]](-p|--print)([[:space:]]|$)",
    )
    assert _got('claude -p"do it"', tmp_path / "mebase") == "BLOCK"
    assert _got('claude -p"do it"', tmp_path / "memut", script=mut) == "ALLOW"
    # 分開寫的形態在全等版下仍 BLOCK ⇒ 差異確實只出在併寫
    assert _got('claude -p "x"', tmp_path / "mesep", script=mut) == "BLOCK"


def test_22_r1_p1_03_long_flag_is_closed(tmp_path: Path) -> None:
    """CODEX-R1-P1-03：長旗標須封閉——`--printable` 不得命中。

    短旗標 `-p` 的值可併寫（POSIX）⇒ 必須 prefix-open；
    長旗標 `--print` 的值只能以 `=` 或另一 token 給 ⇒ 後面須是 `=`／空白／行尾。
    這條不對稱可由 CLI 選項語法導出，不是為了讓某個 case 轉綠而挑的。
    """
    for cmd in ("claude --print x", "claude --print=x", "claude --print"):
        assert _got(cmd, tmp_path / f"lf{abs(hash(cmd)) % 9973}") == "BLOCK", cmd
    for cmd in ("claude --printable x", "claude --printer foo"):
        assert _got(cmd, tmp_path / f"la{abs(hash(cmd)) % 9973}") == "ALLOW", cmd


def test_22_r1_p1_03_mut_open_long_flag_overblocks(tmp_path: Path) -> None:
    """MUT-i：長旗標改回 prefix-open → `--printable` 轉 BLOCK（承重）。"""
    mut = _mut_lex(tmp_path, "muti", FLAG_TAIL, "[[:space:]](-p|--print)")
    assert _got("claude --printable x", tmp_path / "mib") == "ALLOW"
    assert _got("claude --printable x", tmp_path / "mim", script=mut) == "BLOCK"


def test_22_glued_flag_forms_block(tmp_path: Path) -> None:
    """併寫／等號形態的 print 旗標維持 BLOCK（硬規矩 9 正向斷言）。"""
    for i, cmd in enumerate(
        [
            'claude -p"do it"',
            "claude --print=x",
            "claude --model sonnet -p y",
        ]
    ):
        assert _got(cmd, tmp_path / f"g{i}") == "BLOCK", cmd


# ---------------------------------------------------------------------------
# review-r1 findings 之回歸（每條都附承重 mutation）
# ---------------------------------------------------------------------------


def test_22_r1_p0_01_dynamic_command_name_blocks(tmp_path: Path) -> None:
    """CODEX-R1-P0-01 [REGRESSION]：命令名由展開產生時不得漏放。

    這兩條在收窄前被舊式子字串比對**偶然**擋住；只做命令位置判定會使它們
    由 BLOCK 退化為 ALLOW。fail-closed 網（展開標記 ⇒ 退回子字串）補回。
    """
    assert _got("$(printf claude) -p x", tmp_path / "d0") == "BLOCK"
    assert _got("claude${IFS}-p x", tmp_path / "d1") == "BLOCK"
    assert _got("c=claude; $c -p x", tmp_path / "d2") == "BLOCK"


def test_22_r1_p0_01_mut_drop_expansion_net_regresses(tmp_path: Path) -> None:
    """MUT-f：拿掉 fail-closed 網 → P0-01 兩條轉回 ALLOW（承重）。"""
    mut = _mut_lex(tmp_path, "mutf", NET_BLOCK, "")
    for i, cmd in enumerate(["$(printf claude) -p x", "claude${IFS}-p x"]):
        assert _got(cmd, tmp_path / f"mfb{i}") == "BLOCK", f"base {cmd}"
        assert _got(cmd, tmp_path / f"mfm{i}", script=mut) == "ALLOW", f"mut {cmd}"
    # 網拿掉後，本票要修的 6 條放寬仍是 ALLOW ⇒ 證明網不是靠誤擋達標
    for i, cmd in enumerate(_FP4):
        assert _got(cmd, tmp_path / f"mff{i}", script=mut) == "ALLOW", cmd


def test_22_r1_p0_01_expansion_net_does_not_reblock_the_six(tmp_path: Path) -> None:
    """fail-closed 網不得吃掉本票的 6 條放寬（全部不含 `$`／反引號）。"""
    widened = _FP4 + [
        'git commit -m "claude --print 說明"',
        "ls .claude/tmp; git status --porcelain",
    ]
    for i, cmd in enumerate(widened):
        assert "$" not in cmd and "`" not in cmd, f"cohort 前提破了: {cmd}"
        assert _got(cmd, tmp_path / f"w{i}") == "ALLOW", cmd


_MULTILINE = [
    'claude "prompt\ntext" -p x',
    'v=$(claude "prompt\ntext" -p x)',
    'claude \\\n-p "x"',
]


def test_22_r1_p0_02_multiline_dispatch_blocks(tmp_path: Path) -> None:
    """CODEX-R1-P0-02 ＋ COMPOSER-R1-P2-01 [NEW-CLASS]：跨行真派工須 BLOCK。

    成因：`grep` 逐行比對，而 claude 段是**名稱＋旗標**的兩 token 規則
    ——引號內換行／反斜線續行會把兩者拆到不同行。家族 CLI 因為是**單 token**
    規則所以不受影響（實測 codex/grok 同型三條皆 BLOCK）⇒ 本病專屬 claude 段。
    修法在前處理：引號內換行比照空白中性化為 US；引號外 `\\`+LF 依 bash 語意移除。
    🔴 pre-phase2、HEAD、本版**三個版本**實測：前兩者 ALLOW ⇒ 屬既有缺口非 B7 回歸，
    本票一併修掉。
    """
    for i, cmd in enumerate(_MULTILINE):
        assert _got(cmd, tmp_path / f"ml{i}") == "BLOCK", repr(cmd)


def test_22_r1_p0_02_mut_drop_quoted_newline_regresses(tmp_path: Path) -> None:
    """MUT-g：引號內換行不中性化 → 跨行引號派工轉 ALLOW（承重）。"""
    # B3R Phase 3 起，引號內字元映射的**唯一定義**是 XFORM_Q（批次快路徑與逐字
    # 分支都呼叫它）。錨點隨之改到該函式。
    # 🔴 錨點改動未弱化本 mutation，反而變強：舊錨點只改逐字分支，
    #    快路徑仍會照常中性化換行 ⇒ 該 mutation 對重寫後的碼已失去鑑別力。
    mut = _mut_lex(
        tmp_path,
        "mutg",
        'gsub(/[ \\t\\n]/, "\\037", t)',
        'gsub(/[ \\t]/, "\\037", t)',
    )
    cmd = 'claude "prompt\ntext" -p x'
    assert _got(cmd, tmp_path / "mgb") == "BLOCK"
    assert _got(cmd, tmp_path / "mgm", script=mut) == "ALLOW"


def test_22_r1_p0_02_mut_drop_line_continuation_regresses(tmp_path: Path) -> None:
    """MUT-h：不處理 `\\`+LF 續行 → 續行派工轉 ALLOW（承重）。"""
    mut = _mut_lex(
        tmp_path,
        "muth",
        # B3R Phase 3：逐字存取改走視窗 helper CH()，錨點隨之更新（語義未變）。
        'if (c == "\\\\" && i < n && CH(i+1) == "\\n") { i += 2; continue }\n',
        "",
    )
    cmd = 'claude \\\n-p "x"'
    assert _got(cmd, tmp_path / "mhb") == "BLOCK"
    assert _got(cmd, tmp_path / "mhm", script=mut) == "ALLOW"


# ---------------------------------------------------------------------------
# 凍結 TODO 事實勘誤層（CODEX-R1-P1-04 ＋ COMPOSER-R1-P2-02 兩家共識）
# ---------------------------------------------------------------------------

EXTRACT_FLIPS = REPO_ROOT / "scripts" / "extract_phase2_expected_flips.py"
FLIPS = REPO_ROOT / "tests" / "governance" / "fixtures" / "phase2_expected_flips.txt"
ERRATA = REPO_ROOT / "tests" / "governance" / "fixtures" / "phase2_flips_errata.tsv"


def _load_extractor():
    import importlib.util

    spec = importlib.util.spec_from_file_location("extract_flips_b7", EXTRACT_FLIPS)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_errata_layer_is_non_empty() -> None:
    """勘誤層存在且至少一列——否則本節其餘斷言全部 vacuous。"""
    assert ERRATA.is_file(), "缺勘誤層 fixture"
    rows = _load_extractor().load_errata()
    assert rows, "勘誤層為空 ⇒ 下列斷言空轉"


def test_errata_rows_are_empirically_true(tmp_path: Path) -> None:
    """🔴 強制點：每一列勘誤都以實跑證明，寫錯的勘誤當場紅。

    ``corrected_from`` 須等於 ``receipt_gate`` 那個版本對該指令的判定；
    ``corrected_to`` 須等於**現行** gate 的判定。
    ⇒ 勘誤層不是「宣稱」，是**可證偽的量測**。
    """
    rows = _load_extractor().load_errata()
    for i, e in enumerate(rows):
        receipt = REPO_ROOT / e["receipt_gate"]
        assert receipt.is_file(), f"receipt_gate 不存在: {e['receipt_gate']}"
        got_from = _got(e["command"], tmp_path / f"ef{i}", script=receipt)
        assert got_from == e["from"], (
            f"{e['test_id']} 勘誤 from 態與實跑不符: "
            f"宣稱={e['from']} 實測={got_from} gate={e['receipt_gate']}"
        )
        got_to = _got(e["command"], tmp_path / f"et{i}")
        assert got_to == e["to"], (
            f"{e['test_id']} 勘誤 to 態與現行 gate 不符: "
            f"宣稱={e['to']} 實測={got_to}"
        )


def test_errata_rows_are_not_stale() -> None:
    """每一列勘誤都必須對應到凍結 TODO 中真實存在的一列（禁殘留死列）。"""
    mod = _load_extractor()
    todo = (REPO_ROOT / "docs" / "GOVB0_FRICTION_TODO.md").read_text(encoding="utf-8")
    # extract() 出口已套勘誤 ⇒ 以未套版比對是否命中
    raw_rows = mod.extract(todo)
    _rows, unmatched = mod.apply_errata(raw_rows, mod.load_errata())
    assert not unmatched, f"勘誤列在 TODO 中找不到對應: {unmatched}"


def test_errata_is_applied_to_generated_fixture() -> None:
    """勘誤確實反映在機械可讀的 fixture 上（而非只在人類可讀的延伸檔）。"""
    mod = _load_extractor()
    text = FLIPS.read_text(encoding="utf-8")
    for e in mod.load_errata():
        want = f"{e['kind']}\t{e['test_id']}\t{e['from']}\t{e['to']}\t{e['command']}"
        assert want in text, f"fixture 未套用勘誤: {want!r}"


def test_errata_kind_is_derived_not_declared(tmp_path: Path) -> None:
    """🔴 `CODEX-STAMP-R1 ERRATA_RECHECK`：kind 不得只是宣告值。

    codex 實測出的洞：一列 from/to 皆與實跑相符、但 kind 寫成 `maintain`
    （實際 from≠to ⇒ 應為 flip）的假勘誤，當時**全部測試都綠**
    ——因為沒有任何斷言把 kind 綁回 from/to。
    改為由 from/to **導出**後，該類假勘誤在讀檔當下即 ValueError。
    """
    mod = _load_extractor()
    bad = tmp_path / "bad_errata.tsv"
    bad.write_text(
        "# 假勘誤：from≠to 卻宣告 maintain\n"
        "TEST-X\tsome cmd\tmaintain\tALLOW\tBLOCK\tsome/gate.sh\n",
        encoding="utf-8",
    )
    try:
        mod.load_errata(bad)
    except ValueError as exc:
        assert "kind" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("kind 與 from/to 不符的假勘誤竟然被接受")

    # 反向：一致的宣告可正常讀入
    good = tmp_path / "good_errata.tsv"
    good.write_text(
        "TEST-X\tsome cmd\tmaintain\tBLOCK\tBLOCK\tsome/gate.sh\n", encoding="utf-8"
    )
    rows = mod.load_errata(good)
    assert len(rows) == 1 and rows[0]["kind"] == "maintain"

    # from/to 非法枚舉亦須擋
    ugly = tmp_path / "ugly_errata.tsv"
    ugly.write_text(
        "TEST-X\tsome cmd\tmaintain\tMAYBE\tMAYBE\tsome/gate.sh\n", encoding="utf-8"
    )
    try:
        mod.load_errata(ugly)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("from/to 非 ALLOW|BLOCK 竟然被接受")


def test_mut_drop_errata_application_drifts(tmp_path: Path) -> None:
    """承重 mutation：拿掉抽取出口的勘誤套用 → `--check` 由 0 轉非 0。

    證明勘誤層是**機械強制**的，不是裝飾性文件。
    """
    src = EXTRACT_FLIPS.read_text(encoding="utf-8")
    anchor = "    rows, _unmatched = apply_errata(rows)\n"
    assert anchor in src, "勘誤套用錨點漂移"
    mut = tmp_path / "extract_mut.py"
    mut.write_text(src.replace(anchor, "", 1), encoding="utf-8")

    base = subprocess.run(
        ["venv/bin/python", str(EXTRACT_FLIPS), "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert base.returncode == 0, f"base --check 應為 0: {base.stderr}"
    got = subprocess.run(
        ["venv/bin/python", str(mut), "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert got.returncode != 0, "拿掉勘誤套用後 --check 仍為 0 ⇒ 勘誤層未承重"


# ---------------------------------------------------------------------------
# stamp-r1 findings 之回歸（codex 複驗輪）
# ---------------------------------------------------------------------------


def test_22_s1_heredoc_multiline_cmdsub_blocks(tmp_path: Path) -> None:
    """`CODEX-STAMP-R1 NEW-P0-01`：heredoc body 內的**跨行**命令替換須 BLOCK。

    heredoc body 在前處理 Pass 1 被遮蔽（契約 10），唯一還看得到它的是
    `_gate_lex_extract_cmdsubs`——而它原本逐行掃描，跨行的 `$( ... )` 找不到右括號。
    修法＝抽取器改為整份輸入單一 record，emit 時換行轉 `;`（保留命令位置語意）。
    單行 heredoc 變體與引號 delimiter 變體本來就擋得住，一併釘死防回歸。
    """
    assert (
        _got('cat <<EOF\n$(claude "prompt\ntext" -p x)\nEOF', tmp_path / "h0")
        == "BLOCK"
    )
    assert _got("cat <<EOF\n$(claude -p x)\nEOF", tmp_path / "h1") == "BLOCK"
    assert _got("cat <<'EOF'\n$(claude -p x)\nEOF", tmp_path / "h2") == "BLOCK"


def test_22_s1_mut_line_based_cmdsub_regresses(tmp_path: Path) -> None:
    """MUT-j：抽取器改回逐行 → heredoc 跨行命令替換轉 ALLOW（承重）。"""
    mut = _mut_lex(
        tmp_path,
        "mutj",
        "LC_ALL=C awk -v RS='\\001' '\n"
        "    function emit(s) { if (s != \"\") { gsub(/\\n/, \";\", s); print s } }",
        "LC_ALL=C awk '\n"
        "    function emit(s) { if (s != \"\") print s }",
    )
    cmd = 'cat <<EOF\n$(claude "prompt\ntext" -p x)\nEOF'
    assert _got(cmd, tmp_path / "mjb") == "BLOCK"
    assert _got(cmd, tmp_path / "mjm", script=mut) == "ALLOW"


def test_22_s1_backslash_split_word_blocks(tmp_path: Path) -> None:
    """`CODEX-STAMP-R1 NEW-P0-02b`：`clau\\de -p x` 執行起來就是 claude ⇒ 須 BLOCK。

    引號外的 `\\X` 依 bash 語意等同 `X`。原本前處理只在指令含引號／heredoc 時才跑，
    這條不含引號 ⇒ 跳脫語意從未被解析。修法＝反斜線亦列入前處理觸發條件。
    """
    assert _got("clau\\de -p x", tmp_path / "bs0") == "BLOCK"
    assert _got("cla\\ude --print x", tmp_path / "bs1") == "BLOCK"


def test_22_s1_history_bang_blocks(tmp_path: Path) -> None:
    """`CODEX-STAMP-R1 NEW-P2-04c`：`!claude -p x` —— 🔴 這是**回歸**不是殘留。

    pre-phase2 與 HEAD 皆 BLOCK（舊式子字串比對命中），初版收窄後 ALLOW。
    codex 把它歸在 P2「conditional residual」，主委三版對照後**上修為回歸**並修掉。
    修法＝fail-closed 網的觸發條件由「整條含 `$`／反引號」改為
    「**命令位置的 token** 含展開／萬用字元 metachar」，`!` 納入該封閉集合。
    """
    assert _got("!claude -p x", tmp_path / "hb0") == "BLOCK"


def test_22_s1_net_trigger_is_command_position_scoped(tmp_path: Path) -> None:
    """網的觸發限於**命令位置 token** —— 兼顧不漏放與不誤擋。

    初版「整條含 `$`／反引號」同時太窄（漏 `!`）又太寬（誤擋唯讀指令）。
    """
    # 命令名是 echo／git（inert）⇒ 即使字串裡有 $( 與 claude 路徑也不該擋
    assert (
        _got('echo "$(cat .claude/tmp/x)"; git rev-parse HEAD', tmp_path / "n0")
        == "ALLOW"
    )
    # 命令名含展開 metachar ⇒ 退回子字串比對
    assert _got("$(printf claude) -p x", tmp_path / "n1") == "BLOCK"
    assert _got("claude${IFS}-p x", tmp_path / "n2") == "BLOCK"


def test_22_s1_mut_widen_net_to_whole_command_overblocks(tmp_path: Path) -> None:
    """MUT-k：網的觸發改回「整條含 `$`／反引號」→ 唯讀指令轉 BLOCK（承重）。"""
    # 🔴 B4 r3：NET_TRIGGER 現在是一整行**賦值**，替換時必須仍是合法賦值，
    #    否則 `_pat` 未定義、grep 收到空樣式 ⇒ 測到的不是「網被放寬」而是「腳本壞掉」。
    mut = _mut_lex(tmp_path, "mutk", NET_TRIGGER, "_pat='[$`]'")
    victim = 'echo "$(cat .claude/tmp/x)"; git rev-parse HEAD'
    assert _got(victim, tmp_path / "mkb") == "ALLOW"
    assert _got(victim, tmp_path / "mkm", script=mut) == "BLOCK"


def test_22_s1_crlf_continuation_is_correctly_allowed(tmp_path: Path) -> None:
    """🔴 `CODEX-STAMP-R1 NEW-P0-03` 是**誤判**——ALLOW 才是正確判定。

    codex 主張 `claude \\`+CRLF+`-p x` 是 fail-open。實跑否證
    （`.claude/tmp/crlf_semantics.sh`，以 `echo` 代打不執行派工）：

        printf 'echo A \\\\\\r\\n-p x\\n' | bash   →   `A ^M`
                                                       `-p: command not found`

    亦即 bash **不把 `\\`+CRLF 當續行**：`\\` 跳脫的是 CR（成為一個字面 CR 引數），
    LF 才是真正的指令結束。所以該字串執行起來是「`claude <CR>`（無 print 旗標，
    非 headless 派工）」＋「一條不存在的指令」，**本來就不是派工** ⇒ 判 ALLOW 正確。
    對照組 LF 續行則確實是同一條指令，故必須 BLOCK。
    """
    assert _got("claude \\\r\n-p x", tmp_path / "cr0") == "ALLOW"
    assert _got('claude \\\n-p "x"', tmp_path / "cr1") == "BLOCK"


def test_22_r1_multiline_does_not_break_contract_1b(tmp_path: Path) -> None:
    """跨行前處理改動不得動到契約 1b 的既有四條（B3R 的 TEST-2.1-1B）。"""
    cases = [
        ('git commit -m "fix: something\ncodex 並獨立重跑探針確認\ndone"', "ALLOW"),
        ('git commit -m "line1\ngrok 那邊已複核\nline3"', "ALLOW"),
        ('echo start\ncodex exec -s workspace-write "p"', "BLOCK"),
        ('set -e\ngrok -m grok-4.5 -p "x"', "BLOCK"),
    ]
    for i, (cmd, want) in enumerate(cases):
        assert _got(cmd, tmp_path / f"c1b{i}") == want, repr(cmd)


# ---------------------------------------------------------------------------
# GOVB0 B4 r4 — 共用式之定向 mutation（`CODEX-R3-P1-04`）
# ---------------------------------------------------------------------------
#
# 為何存在：r3 把判定式收斂成五個共用變數後，mutation 只釘了 `_GL_CMDPOS`（MUT-b）
#   與 fail-closed 網，`_GL_TOKEND`／`_GL_DASHC` **沒有定向 mutation**
#   ⇒ 測試可以全綠而不證明那兩式承重（codex 逐字：「鑑別力下降」）。
#
# 每格三個判準，缺一不可：
#   ① 錨點字面存在 —— 漂移即 assert 失敗（fail-closed，不得靜默跳過）
#   ② 該式縮窄後，**對應那條 TP** 由 BLOCK 翻 ALLOW
#   ③ **對照 TP** 不受影響（仍 BLOCK）—— 證明 mutation 是定向的，不是整體弱化
#
# 🔴 `_GL_CMDPOS` 之第五格 —— 主委原判「不需要」，**被 codex 於 r5 以反例推翻**。
#   主委原本的理由是：MUT-b 已證明「只縮 `_GL_CMDPOS` 仍 BLOCK（②③ 兩層接住）」，
#   故不存在「只靠 CMDPOS 才 BLOCK」的 TP。該推論**錯在只試了 `$( )` 形態**——
#   實跑佐證：`echo $(codex exec hi)` 縮窄 `_GL_CMDPOS` 後仍 BLOCK（走 metachar 網），
#   於是主委誤以為整式都沒有直接承重面。
#
#   codex 指出真正的鑑別面是 **`^` 起始分支**：拿掉它，**行首**的裸派工就翻。
#   （三家在此分歧：grok 與 composer 同意主委「不需第五格」，只有 codex 附了可重現反例。
#    依「看碼證不數人頭、附反例者勝、不決採較嚴版」⇒ 採 codex。）
#
#   🔴 但 codex 提的**對照組是錯的**。它預期 `$(printf codex) exec hi` 會被展開網接住而維持
#   BLOCK；實測**兩條一起翻**。原因：展開網的 `_pat` 自己也以 `${_GL_CMDPOS}` 起頭，
#   行首命令同樣靠 `^` ⇒ 拿掉 `^` 連網的錨點一併失效。
#   正確對照＝**命令不在行首**（走 `[;&|(`]` 分支），實測維持 BLOCK。

_DIRECTED_MUTATIONS = [
    # (名稱, 錨點字面, 縮窄後字面, 應翻 ALLOW 的 TP, 應維持 BLOCK 的對照 TP)
    (
        "TOKEND",
        GL_TOKEND_DEF,
        "_GL_TOKEND='([[:space:];&|()<>`]|$)'",  # ＝ r3 修 `$IFS` 之前的舊值
        "codex$IFS exec hi",
        "codex exec hi",
    ),
    (
        "DASHC",
        GL_DASHC_TAIL,
        "[[:space:]]+)*-c'",
        'bash -xc "codex exec hi"',
        'bash -c "codex exec hi"',
    ),
    (
        "WRAPPER",
        GL_WRAPPER_ALT,
        "(eval|xargs)",
        "env codex exec hi",
        "codex exec hi",
    ),
    (
        "FAMS",
        GL_FAMS_DEF,
        "_GL_FAMS='(codex|cursor-agent|agy)'",
        "grok -p hi",
        "codex exec hi",
    ),
    (
        # `CODEX-R5-*`：移除 `^` 起始分支 ⇒ 行首裸派工翻；非行首者不受影響。
        "CMDPOS_CARET",
        "_GL_CMDPOS='(^|[;&|(`]|\\$\\()[[:space:]]*'",
        "_GL_CMDPOS='([;&|(`]|\\$\\()[[:space:]]*'",
        "codex exec hi",
        "echo x; codex exec hi",
    ),
]


@pytest.mark.parametrize(
    "name,anchor,narrow,victim,control",
    _DIRECTED_MUTATIONS,
    ids=[m[0] for m in _DIRECTED_MUTATIONS],
)
def test_directed_mutation_each_shared_expr_bears_load(
    tmp_path: Path, name: str, anchor: str, narrow: str, victim: str, control: str
) -> None:
    """五式各自承重：縮窄該式 ⇒ 對應 TP 翻 ALLOW，對照 TP 不動。"""
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    assert anchor in lex_text, f"{name} mutation 錨點漂移：{anchor!r}"

    assert _got(victim, tmp_path / f"{name}_base") == "BLOCK", f"{name} 基準線：TP 應 BLOCK"
    assert _got(control, tmp_path / f"{name}_cbase") == "BLOCK", f"{name} 基準線：對照應 BLOCK"

    gate = _mut_lex(tmp_path, f"{name}_mut", anchor, narrow)
    assert _got(victim, tmp_path / f"{name}_mv", script=gate) == "ALLOW", (
        f"{name} 縮窄後 TP 仍 BLOCK ⇒ 該式未承重，或另有一層在接住"
    )
    assert _got(control, tmp_path / f"{name}_mc", script=gate) == "BLOCK", (
        f"{name} 縮窄後對照 TP 也翻了 ⇒ mutation 非定向，鑑別力無效"
    )
