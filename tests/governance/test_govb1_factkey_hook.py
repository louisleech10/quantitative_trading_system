"""票 B-25 / Task 2.2 — fact-key 檢查掛進 gov_check.sh 的強制層守衛測試。

測什麼：
  1. `_gov_check_factkey()` 存在且真的被呼叫（不是寫了函式沒接線）
  2. 正反宿主檔的 rc 對照（TODO Task 2.2 驗證欄兩條 ASSERT 之**意圖**）
  3. 🔴 `GOVB1_FACTKEY_ROOT` **不得**改變強制層的檢查對象（CODEX-R1-P1-01 回歸）
  4. 生成器缺失／不可執行 ⇒ fail-closed（刪掉腳本不得變成假綠）
  5. 段號分母**現算**——加一段就自動變 n+1，且全檔無寫死分母
  6. `scripts/git_hooks/pre-push` 未被本 Task 改動，但其**委派鏈**確實會走到第 3 段

🔴 為何不直接跑真 repo 的 `bash scripts/gov_check.sh --no-probe`：
   該模式的**第 5 段**會跑 `pytest tests/governance`，而本檔就在其中 ⇒ **無限遞迴**。
   （2026-08-12 段序改「便宜先」後，pytest 由第 2 段移為第 5 段；此處同步更新。）
   改為在 tmp 建一個只含所需腳本、**不含 tests/governance** 的 git repo，
   跑真正的 gov_check.sh（非 stub、非片段），該段自然走「略過」分支。

🔴 為何正反對照改用「把宿主檔放進 tmp repo 的真實路徑」而非 `GOVB1_FACTKEY_ROOT`：
   TODO 那兩條 ASSERT 以 env 傳 fixture 根，但強制層若照收該 env，
   任何殘留的 export 就能把 push 前的檢查導去乾淨 fixture（codex 實證）。
   強制層改為一律清掉該 env ⇒ 測試改以真實路徑安裝正反宿主檔，**驗的是同一件事**。
   偏離已記入 docs/GOV_B6_SCOPE_AMENDMENT.md。
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

TARGET_REL = "docs/GOVERNANCE_EXECUTION_ORDER.md"

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


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(root), check=True, env={**os.environ, **_GIT_ENV},
        capture_output=True,
    )


def _mk_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts" / "git_hooks").mkdir(parents=True)
    for name in _DEPS:
        src = REPO / "scripts" / name
        assert src.is_file(), f"依賴不存在: {src}"
        shutil.copy2(src, root / "scripts" / name)
    shutil.copy2(PRE_PUSH, root / "scripts" / "git_hooks" / "pre-push")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _install_host(root: Path, fixture: Path) -> None:
    """把正／反宿主檔安裝到 tmp repo 的**真實路徑**，並 commit。

    commit 的理由：gov_check 第 1b 段會對「本次改動之 docs/*.md」跑 doc_format_precheck，
    留成未追蹤檔會讓格式檢查介入，使正反對照因**無關原因**變紅。
    """
    # 🔴 票 B-25 站 2.5 Task 1.1（多宿主）／r5 CODEX-R5-P1-03：
    #   本 helper 前版只安裝 TARGET_REL 一份，新增雙宿主 target 後
    #   clean 驗證會先因新宿主缺檔而報 MISSING TARGET（與正反鑑別力無關的紅）。
    #   ⇒ 改為**安裝 fixture 內全部檔案**（fixture 即已登記 target 之投影）。
    #   clean/drifted 之原有斷言不得放寬——鑑別力仍來自 block 內容差異。
    installed = 0
    for src in sorted(fixture.rglob("*")):
        if not src.is_file() or src.name == "README.md":
            continue
        rel = src.relative_to(fixture)
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        installed += 1
    assert installed, f"fixture {fixture} 內無可安裝之宿主檔"
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "host")


def _run_gov(root: Path, *args: str, env_extra: dict | None = None):
    env = {**os.environ, **_GIT_ENV}
    env.pop("GOVB1_FACTKEY_ROOT", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", "scripts/gov_check.sh", *args],
        cwd=str(root), env=env, capture_output=True, text=True,
    )


def _run_prepush(root: Path, env_extra: dict | None = None):
    env = {**os.environ, **_GIT_ENV}
    env.pop("GOVB1_FACTKEY_ROOT", None)
    env.pop("GOVERNANCE_SKIP_PREPUSH", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", "scripts/git_hooks/pre-push"],
        cwd=str(root), env=env, capture_output=True, text=True, input="",
    )


# --------------------------------------------------------------------------
# 接線本身
# --------------------------------------------------------------------------


def test_function_name_is_exactly_as_specified():
    """TODO Task 2.2 指定函式名 `_gov_check_factkey`——改名會讓規格與實作對不上。"""
    src = GOV_CHECK.read_text(encoding="utf-8")
    assert "_gov_check_factkey()" in src, "缺 _gov_check_factkey() 定義"
    assert re.search(r"^\s*if _gov_check_factkey;", src, re.M), (
        "定義了函式卻沒有呼叫點 ⇒ 未接線（寫了等於沒寫）"
    )


def test_generator_is_invoked_with_check_flag_and_env_stripped():
    src = GOV_CHECK.read_text(encoding="utf-8")
    assert "gen_fact_key_blocks.sh --check" in src
    assert "env -u GOVB1_FACTKEY_ROOT" in src, (
        "強制層未清掉 GOVB1_FACTKEY_ROOT ⇒ 檢查對象可由呼叫端指定（CODEX-R1-P1-01）"
    )


def test_pre_push_is_not_modified_by_this_task():
    """TODO 明列：不得改 pre-push 本身。"""
    body = PRE_PUSH.read_text(encoding="utf-8")
    assert "fact_key" not in body and "factkey" not in body, (
        "pre-push 出現 fact-key 字樣 ⇒ 掛載點被改到 pre-push，違反 Task 2.2 不可做"
    )
    assert "gov_check.sh --no-probe" in body, "pre-push 仍須委派 gov_check.sh --no-probe"


# --------------------------------------------------------------------------
# 正反對照（在不含 tests/governance 的 tmp repo 內跑真正的 gov_check.sh）
# --------------------------------------------------------------------------


def test_t22_clean_host_rc_zero(tmp_path):
    root = _mk_repo(tmp_path)
    _install_host(root, CLEAN)
    r = _run_gov(root, "--no-probe")
    assert "事實單一來源" in r.stdout, f"第 3 段未執行:\n{r.stdout}"
    assert r.returncode == 0, f"clean 應 rc=0，實得 {r.returncode}\n{r.stdout}\n{r.stderr}"


def test_t22_drifted_host_rc_nonzero(tmp_path):
    root = _mk_repo(tmp_path)
    _install_host(root, DRIFTED)
    r = _run_gov(root, "--no-probe")
    assert r.returncode != 0, f"drifted 應 rc≠0（漂移未擋 push ⇒ 機制失效）\n{r.stdout}"
    assert "FACTKEY DRIFT" in r.stderr, f"未見漂移訊息:\n{r.stderr}"


def test_env_var_cannot_redirect_the_enforcement_check(tmp_path):
    """🔴 CODEX-R1-P1-01 回歸：宿主檔已漂移時，把 env 指向乾淨 fixture **不得**放行。

    這是真實可發生的意外——shell 裡殘留一行 export，push 前檢查就靜默失效。
    """
    root = _mk_repo(tmp_path)
    _install_host(root, DRIFTED)
    r = _run_gov(root, "--no-probe", env_extra={"GOVB1_FACTKEY_ROOT": str(CLEAN)})
    assert r.returncode != 0, (
        "env 指向乾淨 fixture 就放行 ⇒ 強制層的檢查對象可被呼叫端指定（fail-open）"
    )
    assert "FACTKEY DRIFT" in r.stderr


def test_missing_host_is_fail_closed_not_silent_pass(tmp_path):
    """宿主檔不存在 ⇒ 必須紅。綠代表「檔案不見了」被當成「沒事可做」＝fail-open。"""
    root = _mk_repo(tmp_path)
    r = _run_gov(root, "--no-probe")
    assert r.returncode != 0, f"宿主檔不存在竟放行:\n{r.stdout}"
    assert "MISSING TARGET" in r.stderr


@pytest.mark.parametrize("how", ["delete", "chmod"])
def test_generator_absent_or_not_executable_is_fail_closed(tmp_path, how):
    root = _mk_repo(tmp_path / how)
    _install_host(root, CLEAN)
    gen = root / "scripts" / "gen_fact_key_blocks.sh"
    if how == "delete":
        gen.unlink()
    else:
        gen.chmod(0o644)
    r = _run_gov(root, "--no-probe")
    assert r.returncode != 0, "生成器缺失/不可執行竟放行 ⇒ 刪掉腳本就能假綠"
    assert "fail-closed" in r.stderr


def test_fast_mode_contract_is_unchanged(tmp_path):
    """誠實邊界：--fast 是秒級語法自檢，不含第 3 段；push 路徑走 --no-probe，會含。

    🔴 2026-08-12 段序改為「便宜先」時**刻意保留**本契約不動：--fast 跑在
       不含 govb1 資料檔的隔離副本上（見 test_gov_check_dep_failclosed.py），
       把 fact-key／白話／G-7 併進 --fast 會讓那些副本因缺資料檔而紅 ⇒ 假紅。
       fact-key 前移的收益全在 push 路徑（--no-probe），與 --fast 無關。
    """
    root = _mk_repo(tmp_path)
    _install_host(root, DRIFTED)
    r = _run_gov(root, "--fast")
    assert "事實單一來源" not in r.stdout, "--fast 不應執行第 3 段"
    assert r.returncode == 0, f"--fast 不應因 fact-key 漂移而紅:\n{r.stdout}{r.stderr}"


# --------------------------------------------------------------------------
# pre-push 委派鏈（CODEX-R1-P2-05：先前只測 gov_check，未測真正的 push 前路徑）
# --------------------------------------------------------------------------


def test_pre_push_delegation_reaches_factkey_segment(tmp_path):
    root = _mk_repo(tmp_path)
    _install_host(root, CLEAN)
    r = _run_prepush(root)
    assert "委派" in r.stdout, f"pre-push 未委派:\n{r.stdout}"
    assert "事實單一來源" in r.stdout, f"委派鏈未走到第 3 段:\n{r.stdout}"
    assert r.returncode == 0, f"clean 下 pre-push 應放行:\n{r.stdout}\n{r.stderr}"


def test_pre_push_rejects_on_factkey_drift(tmp_path):
    """真正的 push 前路徑：宿主檔漂移 ⇒ 拒 push。"""
    root = _mk_repo(tmp_path)
    _install_host(root, DRIFTED)
    r = _run_prepush(root)
    assert r.returncode != 0, f"漂移竟允許 push:\n{r.stdout}\n{r.stderr}"
    assert "拒 push" in r.stderr, r.stderr


def test_pre_push_escape_hatch_still_documented_and_working(tmp_path):
    """逃生口是既有設計（明示且留痕）；本 Task 不得使它失效，也不得悄悄擴大。"""
    root = _mk_repo(tmp_path)
    _install_host(root, DRIFTED)
    r = _run_prepush(root, env_extra={"GOVERNANCE_SKIP_PREPUSH": "1"})
    assert r.returncode == 0
    assert "略過治理檢查" in r.stderr


# --------------------------------------------------------------------------
# 段號：現算，非寫死
# --------------------------------------------------------------------------

_SEG_LINE = re.compile(r"\[gov_check\] (\d+[a-z]?)/(\d+) ")


def test_no_hardcoded_denominator_anywhere_in_source():
    """🔴 分母寫死是本 Task 的病因：10 處寫死 ⇒ 自己就不一致（1/3 與 4/4 並存）。"""
    src = GOV_CHECK.read_text(encoding="utf-8")
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    hits = re.findall(r"\[gov_check\] \d+[a-z]?/\d+", code)
    assert not hits, f"仍有寫死的段號分母: {hits}"


def test_all_printed_denominators_equal_registered_segment_count(tmp_path):
    root = _mk_repo(tmp_path)
    _install_host(root, CLEAN)
    r = _run_gov(root, "--no-probe")
    seen = _SEG_LINE.findall(r.stdout)
    assert seen, f"未印出任何段號:\n{r.stdout}"
    denoms = {d for _, d in seen}
    assert denoms == {"6"}, f"分母不一致（本 Task 要治的正是這個）: {denoms}"
    assert "3" in {n for n, _ in seen}, "fact-key 段未編號為 3"


def test_denominator_is_computed_not_literal(tmp_path):
    """行為引信：在副本多登記一段 ⇒ 印出的分母必須自己 +1。

    若分母是寫死的字面值，加一段之後它會維持原值 ⇒ 本測試轉紅。
    """
    root = _mk_repo(tmp_path)
    _install_host(root, CLEAN)
    p = root / "scripts" / "gov_check.sh"
    src = p.read_text(encoding="utf-8")
    old = "_GC_SEG_IDS='1 1b 2 3 4 5 6'"
    assert old in src, "測試與實作脫節：找不到段號宣告"
    p.write_text(src.replace(old, "_GC_SEG_IDS='1 1b 2 3 4 5 6 7'", 1), encoding="utf-8")
    r = _run_gov(root, "--no-probe")
    denoms = {d for _, d in _SEG_LINE.findall(r.stdout)}
    assert denoms == {"7"}, f"加了一段但分母沒跟著變 ⇒ 分母不是現算的: {denoms}"


def test_letter_suffixed_segment_does_not_inflate_total(tmp_path):
    """`1b` 須併入第 1 段：登記 `1c` 之後總數不得變。"""
    root = _mk_repo(tmp_path)
    _install_host(root, CLEAN)
    p = root / "scripts" / "gov_check.sh"
    src = p.read_text(encoding="utf-8")
    old = "_GC_SEG_IDS='1 1b 2 3 4 5 6'"
    assert old in src, "測試與實作脫節：找不到段號宣告"
    p.write_text(
        src.replace(old, "_GC_SEG_IDS='1 1b 1c 2 3 4 5 6'", 1),
        encoding="utf-8",
    )
    r = _run_gov(root, "--no-probe")
    denoms = {d for _, d in _SEG_LINE.findall(r.stdout)}
    assert denoms == {"6"}, f"帶字母後綴的段被多算了一段: {denoms}"


def test_unregistered_segment_id_is_fail_closed(tmp_path):
    """新增一段卻忘了登記 ⇒ 當場炸，而不是靜默印出錯的分母。"""
    root = _mk_repo(tmp_path)
    p = root / "scripts" / "gov_check.sh"
    src = p.read_text(encoding="utf-8")
    p.write_text(
        src.replace('_gc_seg 1 "shell 語法', '_gc_seg 9 "shell 語法', 1), encoding="utf-8"
    )
    r = _run_gov(root, "--fast")
    assert r.returncode == 2, f"未登記段號應 rc=2，實得 {r.returncode}"
    assert "未登記的段號" in r.stderr


def test_generator_wiring_survives_in_real_repo():
    """真 repo 的生成器 --check 必須是綠的——否則本機制上線即擋死所有人的 push。"""
    env = {k: v for k, v in os.environ.items() if k != "GOVB1_FACTKEY_ROOT"}
    r = subprocess.run(
        ["bash", str(GEN), "--check"], cwd=str(REPO), capture_output=True, text=True, env=env
    )
    assert r.returncode == 0, f"repo 根 --check 非零:\n{r.stderr}"
