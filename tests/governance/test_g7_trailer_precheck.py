"""G-7 前移檢查（commit-msg 階段）之行為釘死。

為何存在（S6.1）：
    `docs/GOV_ENFORCEMENT_REGISTRY.md` 之 `E-005` 原本登記
    「本票不存在可前移的靜態子集」——那句是錯的。
    「這次 staged 的路徑在不在 scope 白名單內」只需 manifest 與路徑，commit 當下完全可算；
    缺的只是「訊息有沒有帶 trailer」，而 commit-msg 拿得到訊息檔。

    代價實證：2026-08-14 同一天內兩次因新建 `docs/GOV_*.md`／`scripts/*.sh` 後
    commit 未帶 trailer，G-7 直到十分鐘級的 pre-push 才紅；而 G-7 的豁免是
    「該路徑在範圍內**只**被帶 trailer 的 commit 觸及」⇒ 補後續 commit 解不掉，
    只能 `reset --mixed` ＋ `--amend` 重寫歷史。

🔴 五條缺一不可：
    · 只驗「該擋的擋了」⇒ 無法排除它恆紅（那會擋掉所有 commit）
    · 只驗「該放的放了」⇒ 無法排除它恆綠（等於沒有檢查）
    · trailer 放中間段那條單獨存在：git **只解析最末段**，這是實際踩過的坑
    · 白名單導不出來時**必須要求 trailer**（fail-closed），否則刪掉 gate 腳本即繞過
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "g7_trailer_precheck.sh"

IN_SCOPE = "scripts/in_scope_file.sh"
OUT_SCOPE = "docs/OUT_OF_SCOPE.md"


def _stub_gate(repo: Path, *, ok: bool = True) -> None:
    """替身 govb1_final_gate.sh：只實作 --print-scope。

    用替身而非真檔，是為了讓白名單成為**測試的自變數**——
    綁真 manifest 會使本測試隨 scope 變更而漂，那正是本專案反覆吃虧的形態。
    """
    body = (
        "#!/usr/bin/env bash\n"
        'if [ "${1:-}" = "--print-scope" ]; then\n'
        + (f'  printf "%s\\n" "{IN_SCOPE}"\n  exit 0\n' if ok
           else '  echo "G-7 FAIL: scope manifest 雜湊不符" >&2\n  exit 1\n')
        + "fi\nexit 2\n"
    )
    p = repo / "scripts" / "govb1_final_gate.sh"
    p.write_text(body, encoding="utf-8")
    p.chmod(0o755)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    (r / "scripts").mkdir(parents=True)
    (r / "docs").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=r, check=True)
    shutil.copy2(SCRIPT, r / "scripts" / SCRIPT.name)
    _stub_gate(r)
    (r / IN_SCOPE).write_text("# in scope\n", encoding="utf-8")
    (r / OUT_SCOPE).write_text("# out of scope\n", encoding="utf-8")
    return r


def _run(repo: Path, msg: str, staged: list[str]) -> subprocess.CompletedProcess:
    subprocess.run(["git", "add", "--"] + staged, cwd=repo, check=True)
    m = repo / "msg.txt"
    m.write_text(msg, encoding="utf-8")
    return subprocess.run(
        ["bash", "scripts/g7_trailer_precheck.sh", str(m)],
        cwd=repo, capture_output=True, text=True,
    )


def test_out_of_scope_without_trailer_is_blocked(repo: Path) -> None:
    r = _run(repo, "test: 無 trailer\n\n第二段。\n", [OUT_SCOPE])
    assert r.returncode != 0, f"scope 外路徑無 trailer 卻放行 ⇒ 前移形同未做：{r.stdout}{r.stderr}"
    assert OUT_SCOPE in r.stderr, f"未具名是哪條路徑 ⇒ 訊息無法據以行動：{r.stderr}"


def test_trailer_in_middle_paragraph_is_still_blocked(repo: Path) -> None:
    """git 只解析**最末段**——放中間等於沒放，這是實際踩過的坑。"""
    msg = (
        "test: trailer 放中間\n\n"
        "Governance-Scope: out-of-epic 這行在中間段\n\n"
        "最後一段是別的內容。\n"
    )
    r = _run(repo, msg, [OUT_SCOPE])
    assert r.returncode != 0, (
        f"trailer 在中間段卻被當成有帶 ⇒ 與 git 的解析不一致，會放出 G-7 會紅的 commit："
        f"{r.stdout}{r.stderr}"
    )


def test_trailer_in_last_paragraph_passes(repo: Path) -> None:
    msg = "test: 合規\n\n說明。\n\nGovernance-Scope: out-of-epic 新增檔案\n"
    r = _run(repo, msg, [OUT_SCOPE])
    assert r.returncode == 0, f"合規訊息被擋 ⇒ 誤擋：{r.stdout}{r.stderr}"


def test_in_scope_only_passes_without_trailer(repo: Path) -> None:
    """鑑別力：只動 scope 內檔時不該要求 trailer，否則本檢查等於恆紅。"""
    r = _run(repo, "test: 只動 scope 內檔\n", [IN_SCOPE])
    assert r.returncode == 0, f"只動 scope 內檔卻要求 trailer ⇒ 恆紅：{r.stdout}{r.stderr}"


def test_trailer_followed_by_garbage_is_blocked(repo: Path) -> None:
    """末段有 trailer 但後面接非 trailer 行 ⇒ git 不認，本檢查也不能認。

    〔CODEX-R2-P0-03 實構〕原以 awk 取末段再 grep，此例判「有 trailer」放行，
    而 `git interpret-trailers --parse` 無輸出 ⇒ 判準與 G-7 消費端不一致，
    放行的正是之後會在 pre-push 紅掉的 commit。
    """
    msg = "test: 末段有雜訊\n\n說明。\n\nGovernance-Scope: out-of-epic 理由\ngarbage\n"
    r = _run(repo, msg, [OUT_SCOPE])
    parsed = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        cwd=repo, input=msg, capture_output=True, text=True,
    ).stdout
    assert "Governance-Scope" not in parsed, "前提不成立：git 竟認這是 trailer，本測試需重新設計"
    assert r.returncode != 0, f"git 不認的 trailer 卻被本檢查認了 ⇒ 判準與消費端不一致：{r.stderr}"


def test_type_change_is_not_skipped(repo: Path) -> None:
    """type change（檔案改成 symlink）不得被 diff-filter 漏掉。

    〔CODEX-R2-P0-03 實構〕原 `--diff-filter=ACMRD` 不含 `T`。
    """
    subprocess.run(["git", "add", "--", OUT_SCOPE], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base", "--no-verify"], cwd=repo, check=True)
    target = repo / OUT_SCOPE
    target.unlink()
    target.symlink_to("../" + IN_SCOPE)
    r = _run(repo, "test: type change 無 trailer\n", [OUT_SCOPE])
    assert r.returncode != 0, f"type change 被漏掉 ⇒ scope 外路徑可用改型別的方式繞過：{r.stdout}{r.stderr}"


def test_rename_from_out_of_scope_keeps_old_name(repo: Path) -> None:
    """rename 之**舊名**必須納入判定。

    〔GROK-R2-P2-01 實構〕`--name-only` 對 rename 隱去舊名 ⇒
    把 scope 外檔 `git mv` 進 scope 內時，無 trailer 也會放行。
    改用 `--name-status` 後舊名新名都納入。
    """
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base", "--no-verify"], cwd=repo, check=True)
    subprocess.run(["git", "mv", OUT_SCOPE, IN_SCOPE.replace(".sh", "_moved.sh")],
                   cwd=repo, check=True)
    m = repo / "msg.txt"
    m.write_text("test: rename 進 scope 內、無 trailer\n", encoding="utf-8")
    r = subprocess.run(["bash", "scripts/g7_trailer_precheck.sh", str(m)],
                       cwd=repo, capture_output=True, text=True)
    assert r.returncode != 0, (
        f"rename 舊名被隱去 ⇒ 把 scope 外檔搬進 scope 內即可繞過：{r.stdout}{r.stderr}"
    )
    assert OUT_SCOPE in r.stderr, f"未具名舊名 ⇒ 使用者看不出擋的是什麼：{r.stderr}"


def test_unreadable_index_is_fail_closed(repo: Path) -> None:
    """git diff 失敗時不得靜默放行。

    〔CODEX-R2-P0-03 實構〕原本 `git diff | tr` 把 git 的 rc 吃掉，
    `GIT_INDEX_FILE` 指向壞檔時整個檢查靜默通過。
    """
    (repo / "bad_index").write_text("not an index\n", encoding="utf-8")
    m = repo / "msg.txt"
    m.write_text("test: 壞 index\n", encoding="utf-8")
    r = subprocess.run(
        ["bash", "scripts/g7_trailer_precheck.sh", str(m)],
        cwd=repo, capture_output=True, text=True,
        env={**__import__("os").environ, "GIT_INDEX_FILE": str(repo / "bad_index")},
    )
    assert r.returncode != 0, (
        f"git diff 失敗卻放行 ⇒ rc 被吞，弄壞 index 即可繞過：{r.stdout}{r.stderr}"
    )


def test_scope_derivation_failure_requires_trailer(repo: Path) -> None:
    """白名單導不出來 ⇒ 保守要求 trailer（fail-closed），不得靜默放行。

    否則「把 gate 腳本弄壞」就成了繞過本檢查的最短路徑。
    """
    _stub_gate(repo, ok=False)
    r = _run(repo, "test: 白名單導出失敗\n", [IN_SCOPE])
    assert r.returncode != 0, (
        f"白名單導不出來卻放行 ⇒ fail-open，弄壞 gate 腳本即可繞過：{r.stdout}{r.stderr}"
    )
    assert "白名單導出失敗" in r.stderr, f"rc≠0 但未說明原因：{r.stderr}"
