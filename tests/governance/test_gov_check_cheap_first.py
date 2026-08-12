"""gov_check.sh 段序「便宜先」＋ ASSERT 路 A 的守衛測試（2026-08-12）。

測什麼：
  A. 便宜段（1–4）任一紅 ⇒ **不得**進入 pytest 段（早退）。反面：拿掉早退就會跑到。
  B. 失敗原因必須進最末摘要，且帶可 grep 的固定前綴 `GOV-CHECK-FAILED:`。
  C. legacy backlog 掃描（不擋門、實測約 75 秒）**不得**排在擋門的段之前。
  D. 路 A：`_run_assert_lines` 在 `TEMPLATE_CHECK_NO_EXEC=1` 下不執行文件內命令，
     且**所有** `scripts/*.sh` 呼叫端都必須帶該環境變數（機械強制，非紀律）。

🔴 每條都附反面（mutation）：拿掉受測機制必須讓對應斷言轉紅，否則是廉價綠燈。

🔴 為何 tmp repo 內要放一個假的 tests/governance：
   早退的可觀測後果＝「pytest 段沒印出來」。若 tmp repo 沒有 tests/governance，
   該段本來就走「略過」分支 ⇒ 印或不印都一樣，測不出早退。必須讓它「本來會跑」。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOV_CHECK = REPO / "scripts" / "gov_check.sh"
TC = REPO / "scripts" / "template_check.sh"

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

_PYTEST_SEG_MARK = "governance 守衛測試"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(root), check=True,
        env={**os.environ, **_GIT_ENV}, capture_output=True,
    )


def _mk_repo(tmp_path: Path, *, with_tests: bool = True) -> Path:
    """最小 repo；with_tests=True 時放一個**真的會跑且會通過**的 pytest 目錄。"""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for name in _DEPS:
        shutil.copy2(REPO / "scripts" / name, root / "scripts" / name)
    if with_tests:
        (root / "tests" / "governance").mkdir(parents=True)
        (root / "tests" / "governance" / "test_marker.py").write_text(
            "def test_marker():\n    assert True\n", encoding="utf-8"
        )
    # 🔴 基線用**空**註冊表：真 repo 的 fact_keys.json 登記了本 tmp repo 不存在的宿主檔，
    #   照抄會讓「乾淨基線」因 MISSING TARGET 而紅 ⇒ 紅在無關原因（第一版即如此）。
    #   空物件之 --check 須 rc=0，是 fact_keys.json 明載的不變式。
    (root / "scripts" / "fact_keys.json").write_text("{}\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _install_drift(root: Path) -> None:
    """裝一份會讓第 3 段（fact-key）判紅的宿主檔：登記了 target 但檔案不存在。"""
    (root / "scripts" / "fact_keys.json").write_text(
        '{\n  "demo-key": {\n    "target": "docs/DEMO.md",\n'
        '    "rows": [["010", "a", "b"]]\n  }\n}\n',
        encoding="utf-8",
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "drift")


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **_GIT_ENV}
    env.pop("GOVB1_FACTKEY_ROOT", None)
    return subprocess.run(
        ["bash", "scripts/gov_check.sh", *args],
        cwd=str(root), env=env, capture_output=True, text=True, timeout=300,
    )


# ── A. 便宜段紅 ⇒ 早退，不跑 pytest ──────────────────────────────────


def test_cheap_gate_failure_skips_pytest_segment(tmp_path: Path) -> None:
    """第 3 段紅時，第 5 段（pytest）不得執行——那 678 秒必定白跑。"""
    root = _mk_repo(tmp_path)
    _install_drift(root)
    r = _run(root, "--no-probe")
    assert r.returncode != 0, f"fact-key 漂移竟放行:\n{r.stdout}\n{r.stderr}"
    assert _PYTEST_SEG_MARK not in r.stdout, (
        "便宜段已紅卻仍跑 pytest ⇒ 早退失效，那一輪的 678 秒必定白跑\n" + r.stdout
    )


def test_all_green_still_reaches_pytest_segment(tmp_path: Path) -> None:
    """基線：便宜段全綠時 pytest 段照跑。沒有這條，上面那條可能綠在別的原因。"""
    root = _mk_repo(tmp_path)
    r = _run(root, "--no-probe")
    assert r.returncode == 0, f"乾淨 repo 竟未過:\n{r.stdout}\n{r.stderr}"
    assert _PYTEST_SEG_MARK in r.stdout, "全綠時 pytest 段未執行 ⇒ 早退把該跑的也擋掉了"


def test_mutation_removing_early_exit_makes_pytest_run(tmp_path: Path) -> None:
    """反面：把早退閘掏空 ⇒ 便宜段紅時又會跑到 pytest（重現修法前的行為）。

    若不做此變異也無法讓上面那條轉綠，代表它測的不是早退這件事。
    """
    root = _mk_repo(tmp_path)
    _install_drift(root)
    p = root / "scripts" / "gov_check.sh"
    src = p.read_text(encoding="utf-8")
    old = '  _gc_summary "便宜段(第 1–4 段,合計約 10 秒)已失敗 → 早退,不跑 pytest(省約 700 秒)。修好後重跑。"\n  exit "${rc_all}"\n'
    assert old in src, "早退閘錨點不存在（重構?→須更新本測，不得靜默略過）"
    p.write_text(src.replace(old, "  :  # MUTATED: 早退失效\n", 1), encoding="utf-8")
    r = _run(root, "--no-probe")
    assert _PYTEST_SEG_MARK in r.stdout, (
        "變異後應重現「便宜段紅仍跑 pytest」；若仍沒跑，"
        "表示上面那條綠的原因不是早退\n" + r.stdout
    )


def test_mutation_removing_g7_script_turns_red(tmp_path: Path) -> None:
    """🔴〔CODEX-R1-P1-01〕刪掉 G-7 腳本但留下 manifest ⇒ 必須紅。

    第一版寫成「腳本不在就略過」＝刪檔即可讓新增的 G-7 覆蓋靜默消失，
    是 fail-open 的標準形態。本測釘住修法：manifest 在＝閘必須跑得起來。
    """
    root = _mk_repo(tmp_path)
    (root / "scripts" / "govb1_scope.manifest").write_text(
        "allow scripts/\n", encoding="utf-8"
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "manifest")
    r = _run(root, "--no-probe")
    assert r.returncode != 0, (
        "有 manifest 卻缺 govb1_final_gate.sh 竟放行 ⇒ 刪腳本即可關掉 G-7 覆蓋\n" + r.stdout
    )
    assert any(
        "govb1_final_gate.sh" in ln for ln in r.stderr.splitlines()
        if ln.startswith("GOV-CHECK-FAILED:")
    ), f"摘要未具名指出缺哪支:\n{r.stderr}"


def test_g7_segment_skipped_only_when_not_a_govb1_repo(tmp_path: Path) -> None:
    """基線：manifest 與腳本皆不在（非 govb1 repo）⇒ 合法略過，不得誤擋。"""
    root = _mk_repo(tmp_path)
    r = _run(root, "--no-probe")
    assert r.returncode == 0, f"非 govb1 repo 竟被 G-7 誤擋:\n{r.stdout}\n{r.stderr}"
    assert "G-7 不適用" in r.stdout, f"略過理由未具名:\n{r.stdout}"


# ── B. 失敗摘要 ────────────────────────────────────────────────────


def test_failure_reason_lands_in_greppable_summary(tmp_path: Path) -> None:
    """失敗原因須進最末摘要且帶固定前綴——否則 1600 行輸出裡 tail 看不到。"""
    root = _mk_repo(tmp_path)
    _install_drift(root)
    r = _run(root, "--no-probe")
    hits = [ln for ln in r.stderr.splitlines() if ln.startswith("GOV-CHECK-FAILED:")]
    assert hits, f"未見可 grep 之失敗摘要行:\n{r.stderr}"
    assert any("段 3" in ln for ln in hits), f"摘要未具名指出是第 3 段:\n{hits}"


def test_no_segment_sets_rc_all_directly(tmp_path: Path) -> None:
    """🔴 直接寫 `rc_all=1` ⇒ 該原因不會進摘要，退回「tail 看不到」的老問題。

    封閉集合檢查：全檔僅允許 `_gc_fail` 內那一處賦值。
    """
    code = [
        ln for ln in GOV_CHECK.read_text(encoding="utf-8").splitlines()
        if not ln.lstrip().startswith("#")
    ]
    hits = [ln for ln in code if re.search(r"(?<![\w-])rc_all=1\b", ln)]
    assert len(hits) == 1, (
        "rc_all=1 只允許出現在 _gc_fail 內；其餘段落一律走 _gc_fail 才會進摘要。\n"
        f"實得 {len(hits)} 處: {hits}"
    )


# ── C. 不擋門的東西不得排在擋門的東西前面 ──────────────────────────


def test_backlog_scan_is_after_all_gating_segments() -> None:
    """legacy backlog 掃全庫 216 檔（實測讓 --fast 由約 1.4s 變 80s）且**永不擋門**。

    它若排在便宜段之前，等於每次都先付那筆錢才知道 0 秒的閘紅了沒。
    """
    src = GOV_CHECK.read_text(encoding="utf-8")
    backlog = src.index("既有未合規 backlog")
    factkey = src.index('_gc_seg 3 "事實單一來源')
    pytest_seg = src.index(f'_gc_seg 5 "{_PYTEST_SEG_MARK}')
    assert backlog > factkey, "backlog 掃描排在 fact-key 閘之前 ⇒ 每次先白付約 75 秒"
    assert backlog > pytest_seg, "backlog 掃描須排在所有擋門段之後"


def test_fast_mode_does_not_run_backlog_scan(tmp_path: Path) -> None:
    """--fast 的契約是秒級；backlog 掃描不得出現在該路徑。"""
    root = _mk_repo(tmp_path)
    r = _run(root, "--fast")
    assert r.returncode == 0, f"--fast 基線未過:\n{r.stdout}\n{r.stderr}"
    assert "backlog" not in r.stdout, f"--fast 竟跑了 backlog 掃描:\n{r.stdout}"


# ── D. 路 A：ASSERT 不得在檢查文件時被執行 ──────────────────────────


def _mk_assert_doc(tmp_path: Path, marker_rel: str) -> Path:
    """造一份含行首 ASSERT 的文件；該 ASSERT 會建立 marker 檔（可觀測副作用）。

    🔴 marker 必須是 **repo 相對路徑**：`_run_assert_lines` 的 token 白名單直接把
       `/*` 與 `*..*` 判為 unsafe 而**不執行**（見 template_check.sh 之 _ra_tok 迴圈）。
       第一版用 tmp_path 絕對路徑 ⇒ 正反兩邊都沒執行，測試「因為沒跑」而假綠。
    """
    script = REPO / "scripts" / "_probe_assert_marker.sh"
    doc = tmp_path / "probe.md"
    doc.write_text(
        f"# probe\n\nASSERT bash {script.relative_to(REPO)} {marker_rel} THEN rc=0\n",
        encoding="utf-8",
    )
    return doc


def test_no_exec_env_suppresses_document_assert_execution(tmp_path: Path) -> None:
    """路 A 的核心：帶 NO_EXEC=1 時，文件內 ASSERT 不得被執行。

    附反面——不帶該變數時 marker 必須產生，證明本測不是在測空氣。
    """
    script = REPO / "scripts" / "_probe_assert_marker.sh"
    script.write_text('#!/usr/bin/env bash\n: > "$1"\n', encoding="utf-8")
    script.chmod(0o755)
    # 🔴 TEMPLATE_CHECK_EXT_SCOPE=force：ASSERT 擴充判準只對 docs/*SPEC*.md 自動命中，
    #   本測的探針文件在 tmp_path ⇒ 不 force 的話 _run_assert_lines 根本不會被呼叫，
    #   兩邊都不產生 marker，測試會「因為沒跑」而假綠（第一版即踩此坑）。
    env_base = {**os.environ, "TEMPLATE_CHECK_EXT_SCOPE": "force"}
    # .claude/tmp/ 已列入 .gitignore，marker 不會弄髒工作區
    stem = tmp_path.name
    m1_rel, m2_rel = f".claude/tmp/{stem}_m1", f".claude/tmp/{stem}_m2"
    m1, m2 = REPO / m1_rel, REPO / m2_rel
    try:
        # 反面：不帶 NO_EXEC ⇒ ASSERT 真的跑，marker 出現
        subprocess.run(
            ["bash", str(TC), "spec", str(_mk_assert_doc(tmp_path, m1_rel))],
            cwd=REPO, capture_output=True, text=True, timeout=120, env=env_base,
        )
        assert m1.exists(), "不帶 NO_EXEC 時 ASSERT 未執行 ⇒ 本測失去鑑別力（測空氣）"

        # 正面：帶 NO_EXEC ⇒ 不執行
        subprocess.run(
            ["bash", str(TC), "spec", str(_mk_assert_doc(tmp_path, m2_rel))],
            cwd=REPO, capture_output=True, text=True, timeout=120,
            env={**env_base, "TEMPLATE_CHECK_NO_EXEC": "1"},
        )
        assert not m2.exists(), "帶 NO_EXEC=1 仍執行了文件內命令 ⇒ 路 A 失效，自鎖會重演"
    finally:
        script.unlink(missing_ok=True)
        m1.unlink(missing_ok=True)
        m2.unlink(missing_ok=True)


_FROZEN_EXECUTABLE_ASSERTS = {
    "docs/GOV_B6_SCOPE_AMENDMENT.md",
    "docs/P16_COMMITTEE_DEBT_SPEC.md",
}


def test_executable_assert_lines_are_a_frozen_named_set() -> None:
    """🔴〔CODEX-R1-P1-02〕路 A 讓「文法對但結果會錯」的 ASSERT 不再被判失。

    該語意損失無法在路 A 下復原，但**可以被封住**：受影響的行集合凍結為具名清單，
    新增一行就轉紅 ⇒ 逼作者當場決定（改寫成非執行形態，或明知故犯地加進清單）。
    沒有這條，損失會隨新文件靜默增生，那才是真正的缺口。

    判準與生產一致：行首錨定 `^[[:blank:]]*ASSERT[[:space:]]`
    **且**整行以 `THEN rc=<數字>` 收尾（`rc!=0` 不符 ⇒ 生產判文法錯，不執行）。
    """
    pat_anchor = re.compile(r"^[ \t]*ASSERT[ \t\f\v]")
    pat_tail = re.compile(r"THEN[ \t\f\v]+rc=\d+[ \t]*$")
    hits: dict[str, int] = {}
    for md in sorted((REPO / "docs").rglob("*.md")):
        for ln in md.read_text(encoding="utf-8", errors="replace").splitlines():
            if pat_anchor.match(ln) and pat_tail.search(ln):
                rel = str(md.relative_to(REPO))
                hits[rel] = hits.get(rel, 0) + 1
    assert set(hits) == _FROZEN_EXECUTABLE_ASSERTS, (
        "可執行 ASSERT 的檔案集合變了 ⇒ 路 A 的未驗證面積在無人裁定下改變。\n"
        f"實得: {sorted(hits)}\n期望: {sorted(_FROZEN_EXECUTABLE_ASSERTS)}\n"
        "新增者請改寫成非執行形態（縮排不算，需讓行尾非 `THEN rc=<數字>`），"
        "或明示理由後把檔案加進本清單。"
    )


def test_no_exec_mode_announces_unverified_asserts(tmp_path: Path) -> None:
    """未驗證必須**看得見**：NO_EXEC 下須印出具名提示，不得靜默略過。"""
    script = REPO / "scripts" / "_probe_assert_marker.sh"
    script.write_text('#!/usr/bin/env bash\n: > "$1"\n', encoding="utf-8")
    m_rel = f".claude/tmp/{tmp_path.name}_m3"
    try:
        r = subprocess.run(
            ["bash", str(TC), "spec", str(_mk_assert_doc(tmp_path, m_rel))],
            cwd=REPO, capture_output=True, text=True, timeout=120,
            env={**os.environ, "TEMPLATE_CHECK_EXT_SCOPE": "force",
                 "TEMPLATE_CHECK_NO_EXEC": "1"},
        )
        assert "ASSERT 未驗證" in (r.stdout + r.stderr), (
            "NO_EXEC 下未印出「未驗證」提示 ⇒ 看起來像驗過了（codex P1-02 的核心）\n"
            + r.stdout + r.stderr
        )
    finally:
        script.unlink(missing_ok=True)
        (REPO / m_rel).unlink(missing_ok=True)


def test_every_shell_caller_of_template_check_passes_no_exec() -> None:
    """🔴 把殘留②由紀律轉成機制：呼叫端漏帶 NO_EXEC ⇒ 本測轉紅。

    封閉集合＝`scripts/*.sh` 內所有實際呼叫 template_check.sh 的行
    （排除註解與字串內的提及）。新增呼叫端而忘記帶環境變數會當場被抓。
    """
    offenders: list[str] = []
    for sh in sorted((REPO / "scripts").glob("*.sh")):
        if sh.name == "template_check.sh":
            continue
        for i, ln in enumerate(sh.read_text(encoding="utf-8").splitlines(), 1):
            s = ln.strip()
            if s.startswith("#") or "template_check.sh" not in s:
                continue
            # 只認「真的執行它」的形態：bash …/template_check.sh
            if not re.search(r"bash\s+\S*template_check\.sh", s):
                continue
            if "TEMPLATE_CHECK_NO_EXEC=1" not in s:
                offenders.append(f"{sh.name}:{i}: {s}")
    assert not offenders, (
        "以下呼叫端未帶 TEMPLATE_CHECK_NO_EXEC=1 ⇒ 文件自鎖會在該路徑重演:\n"
        + "\n".join(offenders)
    )
