"""票 B-25 / Task 2.2 — fact-key 檢查掛進 gov_check.sh 的強制層守衛測試。

測什麼：
  1. `_gov_check_factkey()` 存在且真的被呼叫（不是寫了函式沒接線）
  2. 正反 fixture 的 rc 對照（TODO Task 2.2 驗證欄兩條 ASSERT）
  3. 生成器缺失／不可執行 ⇒ fail-closed（刪掉腳本不得變成假綠）
  4. 段號分母**現算**——加一段就自動變 n+1，且全檔無寫死分母
  5. `scripts/git_hooks/pre-push` 未被本 Task 改動（TODO 明列不可做）

🔴 為何不直接跑 `bash scripts/gov_check.sh --no-probe`：
   該模式的第 2 段會跑 `pytest tests/governance`，而本檔就在其中 ⇒ **無限遞迴**。
   改為在 tmp 建一個只含所需腳本、**不含 tests/governance** 的 git repo，
   跑真正的 gov_check.sh（非 stub、非片段），第 2 段自然走「略過」分支。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GOV_CHECK = REPO / "scripts" / "gov_check.sh"
GEN = REPO / "scripts" / "gen_fact_key_blocks.sh"
PRE_PUSH = REPO / "scripts" / "git_hooks" / "pre-push"
FIX = REPO / "tests" / "governance" / "fixtures" / "govb1"
CLEAN = FIX / "factkey_clean"
DRIFTED = FIX / "factkey_drifted"

# gov_check.sh 於 tmp repo 內執行時仍需存在的依賴（缺一即 fail-closed）
_DEPS = (
    "gov_check.sh",
    "gen_fact_key_blocks.sh",
    "fact_keys.json",
    "doc_format_precheck.sh",
    "template_check.sh",
    "brief_conformance_check.sh",
)

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _mk_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for name in _DEPS:
        src = REPO / "scripts" / name
        assert src.is_file(), f"依賴不存在: {src}"
        shutil.copy2(src, root / "scripts" / name)
    env = {**os.environ, **_GIT_ENV}
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"], cwd=root, check=True, env=env
    )
    return root


def _run_gov(root: Path, *args: str, factkey_root: Path | None = None):
    env = {**os.environ, **_GIT_ENV}
    if factkey_root is not None:
        env["GOVB1_FACTKEY_ROOT"] = str(factkey_root)
    else:
        env.pop("GOVB1_FACTKEY_ROOT", None)
    return subprocess.run(
        ["bash", "scripts/gov_check.sh", *args],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )


# --------------------------------------------------------------------------
# 接線本身
# --------------------------------------------------------------------------


def test_function_name_is_exactly_as_specified():
    """TODO Task 2.2 指定函式名 `_gov_check_factkey`——改名會讓規格與實作對不上。"""
    src = GOV_CHECK.read_text(encoding="utf-8")
    assert "_gov_check_factkey()" in src, "缺 _gov_check_factkey() 定義"
    calls = re.findall(r"^\s*if _gov_check_factkey;", src, re.M)
    assert calls, "定義了函式卻沒有呼叫點 ⇒ 未接線（寫了等於沒寫）"


def test_generator_is_invoked_with_check_flag():
    src = GOV_CHECK.read_text(encoding="utf-8")
    assert "gen_fact_key_blocks.sh --check" in src


def test_pre_push_is_not_modified_by_this_task():
    """TODO 明列：不得改 pre-push 本身。"""
    body = PRE_PUSH.read_text(encoding="utf-8")
    assert "fact_key" not in body and "factkey" not in body, (
        "pre-push 出現 fact-key 字樣 ⇒ 掛載點被改到 pre-push，違反 Task 2.2 不可做"
    )
    assert "gov_check.sh" in body, "pre-push 仍須經 gov_check.sh 委派"


# --------------------------------------------------------------------------
# ASSERT rc 對照（在不含 tests/governance 的 tmp repo 內跑真正的 gov_check.sh）
# --------------------------------------------------------------------------


def test_t22_assert_clean_fixture_rc_zero(tmp_path):
    root = _mk_repo(tmp_path)
    r = _run_gov(root, "--no-probe", factkey_root=CLEAN)
    assert "事實單一來源" in r.stdout, f"第 5 段未執行:\n{r.stdout}"
    assert r.returncode == 0, f"clean 應 rc=0，實得 {r.returncode}\n{r.stdout}\n{r.stderr}"


def test_t22_assert_drifted_fixture_rc_nonzero(tmp_path):
    root = _mk_repo(tmp_path)
    r = _run_gov(root, "--no-probe", factkey_root=DRIFTED)
    assert r.returncode != 0, f"drifted 應 rc≠0（漂移未擋 push ⇒ 機制失效）\n{r.stdout}"
    assert "事實單一來源" in r.stdout
    assert "FACTKEY DRIFT" in r.stderr, f"未見漂移訊息:\n{r.stderr}"


def test_missing_target_is_fail_closed_not_silent_pass(tmp_path):
    """不設 GOVB1_FACTKEY_ROOT 且 repo 內無宿主檔 ⇒ 必須紅。

    若這裡是綠的，代表「宿主檔不見了」被當成「沒事可做」——那正是 fail-open。
    """
    root = _mk_repo(tmp_path)
    r = _run_gov(root, "--no-probe")
    assert r.returncode != 0, f"宿主檔不存在竟放行:\n{r.stdout}"
    assert "MISSING TARGET" in r.stderr


@pytest.mark.parametrize("how", ["delete", "chmod"])
def test_generator_absent_or_not_executable_is_fail_closed(tmp_path, how):
    root = _mk_repo(tmp_path / how)
    gen = root / "scripts" / "gen_fact_key_blocks.sh"
    if how == "delete":
        gen.unlink()
    else:
        gen.chmod(0o644)
    r = _run_gov(root, "--no-probe", factkey_root=CLEAN)
    assert r.returncode != 0, "生成器缺失/不可執行竟放行 ⇒ 刪掉腳本就能假綠"
    assert "fail-closed" in r.stderr


def test_fast_mode_contract_is_unchanged(tmp_path):
    """誠實邊界：--fast 是秒級語法自檢，不含第 5 段；push 路徑走 --no-probe，會含。"""
    root = _mk_repo(tmp_path)
    r = _run_gov(root, "--fast", factkey_root=DRIFTED)
    assert "事實單一來源" not in r.stdout, "--fast 不應執行第 5 段"
    assert r.returncode == 0, f"--fast 不應因 fact-key 漂移而紅:\n{r.stdout}{r.stderr}"


# --------------------------------------------------------------------------
# 段號：現算，非寫死
# --------------------------------------------------------------------------

_SEG_LINE = re.compile(r"\[gov_check\] (\d+[a-z]?)/(\d+) ")


def test_no_hardcoded_denominator_anywhere_in_source():
    """🔴 分母寫死是本 Task 的病因：10 處寫死 ⇒ 自己就不一致（1/3 與 4/4 並存）。"""
    src = GOV_CHECK.read_text(encoding="utf-8")
    code = "\n".join(
        ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
    )
    hits = re.findall(r"\[gov_check\] \d+[a-z]?/\d+", code)
    assert not hits, f"仍有寫死的段號分母: {hits}"


def test_all_printed_denominators_equal_registered_segment_count(tmp_path):
    root = _mk_repo(tmp_path)
    r = _run_gov(root, "--no-probe", factkey_root=CLEAN)
    seen = _SEG_LINE.findall(r.stdout)
    assert seen, f"未印出任何段號:\n{r.stdout}"
    denoms = {d for _, d in seen}
    assert denoms == {"5"}, f"分母不一致（本 Task 要治的正是這個）: {denoms}"
    numerators = {n for n, _ in seen}
    assert "5" in numerators, f"fact-key 段未編號為 5: {numerators}"


def test_denominator_is_computed_not_literal(tmp_path):
    """行為引信：在副本登記第 6 段 ⇒ 印出的分母必須自己變成 6。

    若分母是寫死的字面值，加一段之後它會維持 5 ⇒ 本測試轉紅。
    """
    root = _mk_repo(tmp_path)
    p = root / "scripts" / "gov_check.sh"
    src = p.read_text(encoding="utf-8")
    old = "_GC_SEG_IDS='1 1b 2 3 4 5'"
    assert old in src, "測試與實作脫節：找不到段號宣告"
    p.write_text(src.replace(old, "_GC_SEG_IDS='1 1b 2 3 4 5 6'", 1), encoding="utf-8")

    r = _run_gov(root, "--no-probe", factkey_root=CLEAN)
    denoms = {d for _, d in _SEG_LINE.findall(r.stdout)}
    assert denoms == {"6"}, f"加了一段但分母沒跟著變 ⇒ 分母不是現算的: {denoms}"


def test_letter_suffixed_segment_does_not_inflate_total(tmp_path):
    """`1b` 須併入第 1 段：登記 `1c` 之後總數不得變。"""
    root = _mk_repo(tmp_path)
    p = root / "scripts" / "gov_check.sh"
    src = p.read_text(encoding="utf-8")
    p.write_text(
        src.replace("_GC_SEG_IDS='1 1b 2 3 4 5'", "_GC_SEG_IDS='1 1b 1c 2 3 4 5'", 1),
        encoding="utf-8",
    )
    r = _run_gov(root, "--no-probe", factkey_root=CLEAN)
    denoms = {d for _, d in _SEG_LINE.findall(r.stdout)}
    assert denoms == {"5"}, f"帶字母後綴的段被多算了一段: {denoms}"


def test_unregistered_segment_id_is_fail_closed(tmp_path):
    """新增一段卻忘了登記 ⇒ 當場炸，而不是靜默印出錯的分母。"""
    root = _mk_repo(tmp_path)
    p = root / "scripts" / "gov_check.sh"
    src = p.read_text(encoding="utf-8")
    p.write_text(
        src.replace('_gc_seg 1 "shell 語法', '_gc_seg 9 "shell 語法', 1),
        encoding="utf-8",
    )
    r = _run_gov(root, "--fast", factkey_root=CLEAN)
    assert r.returncode == 2, f"未登記段號應 rc=2，實得 {r.returncode}"
    assert "未登記的段號" in r.stderr


def test_generator_wiring_survives_in_real_repo():
    """真 repo 的生成器 --check 必須是綠的——否則本機制上線即擋死所有人的 push。"""
    r = subprocess.run(
        ["bash", str(GEN), "--check"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "GOVB1_FACTKEY_ROOT"},
    )
    assert r.returncode == 0, f"repo 根 --check 非零:\n{r.stderr}"
