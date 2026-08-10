"""票 B-50 `GOV-EXECUTOR-WORKSPACE-NOT-RESTORED` — 派工前後工作區快照比對。

出生事故（本 epic 內兩次，形態不同；出處 `20260809-govb1-b5-review-r2` 收斂檔）：
  ① 執行端跑 mutation 遭中斷、**未還原**即結束，在 `template_check.sh` 留下 `# MUTATION:`
  ② 執行端誤對 tracked 檔 `git checkout`，把 ambient M 檔還原成 HEAD ⇒ `g0_tests` 連帶紅

兩次都**沒有任何機制通知任何人**。本檔驗的就是「現在會不會講話」。

🔴 測試策略：**不讀原始碼字串**（那是 B10 review-r1 判過的病：源碼斷言冒充端到端）。
把兩支函式抽出來，在**真的 git repo** 裡製造每一種形態，斷言 stderr 真的講出來。
對照組（無變動 ⇒ 完全安靜）是必要的——否則「永遠都在叫」也會讓上面每一條變綠。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMITTEE_RUN = REPO_ROOT / "scripts" / "committee_run.sh"


def _fn_src() -> str:
    """抽出 `_ws_snapshot` 與 `_report_workspace_drift` 兩支函式（不執行主流程）。"""
    s = COMMITTEE_RUN.read_text(encoding="utf-8")
    parts = []
    for name in ("_ws_snapshot", "_report_workspace_drift"):
        start = s.index(f"{name}() {{")
        end = s.index("\n}\n", start) + len("\n}\n")
        parts.append(s[start:end])
    return "\n".join(parts)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo, capture_output=True, text=True, check=False,
    )


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "wsrepo"
    repo.mkdir()
    assert _git(repo, "init", "-q").returncode == 0
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    (repo / "白話.txt").write_text("中文路徑\n", encoding="utf-8")
    assert _git(repo, "add", "-A").returncode == 0
    assert _git(repo, "commit", "-q", "-m", "init").returncode == 0
    return repo


def _run(repo: Path, mutate: str) -> subprocess.CompletedProcess[str]:
    """快照 → 執行 `mutate` → 比對回報。回傳 process（stderr 是本檔的 oracle）。"""
    script = (
        "set -u\n"
        + _fn_src()
        + '\n_WS_BEFORE="$(_ws_snapshot)"\n'
        + mutate
        + "\n_report_workspace_drift\n"
        + 'echo "REPORT_RC=$?"\n'
    )
    return subprocess.run(
        ["bash", "-c", script], cwd=repo, capture_output=True, text=True, check=False
    )


# ── 對照組：先驗「不會亂叫」，否則下面每一條都可能是假綠 ──────────────────


def test_no_drift_is_completely_silent(tmp_path: Path) -> None:
    """🔴 派工期間工作區沒動 ⇒ **一個字都不印**。

    沒有這一條，「永遠都在叫」也會讓下面每一條斷言通過。
    """
    repo = _repo(tmp_path)
    r = _run(repo, ":")
    assert "票 B-50" not in r.stderr, f"無變動卻報告了:\n{r.stderr}"
    assert r.stderr.strip() == "", f"無變動時 stderr 非空:\n{r.stderr}"


def test_preexisting_ambient_modification_alone_is_silent(tmp_path: Path) -> None:
    """派工前就存在的 ambient M（本 repo 常態，如 `governance_families.json`）不得誤報。"""
    repo = _repo(tmp_path)
    (repo / "tracked.txt").write_text("ambient\n", encoding="utf-8")
    r = _run(repo, ":")
    assert r.stderr.strip() == "", f"既有 ambient M 被誤報:\n{r.stderr}"


# ── 形態②：ambient M 被還原成 HEAD（實際事故 #2）────────────────────────


def test_form2_ambient_modification_restored_to_head_is_reported(tmp_path: Path) -> None:
    """🔴 執行端對 tracked 檔 `git checkout` ⇒ ambient 修改消失 ⇒ 必須講話。

    這正是 `phase2_expected_flips.txt` 被還原、與其 `.sha256`／產生器三者不一致那次。
    """
    repo = _repo(tmp_path)
    (repo / "tracked.txt").write_text("ambient\n", encoding="utf-8")
    r = _run(repo, "git checkout -- tracked.txt")
    assert "形態②" in r.stderr, f"ambient 消失未被回報:\n{r.stderr}"
    assert "tracked.txt" in r.stderr, f"未指出是哪個檔:\n{r.stderr}"
    assert "git checkout" in r.stderr, "未指出違反的是哪條執行端合約"


def test_form2_handles_non_ascii_paths(tmp_path: Path) -> None:
    """🔴 中文路徑不得因 git 的 quotePath 轉義而對不上（本 repo 有 `白話說明/`）。"""
    repo = _repo(tmp_path)
    (repo / "白話.txt").write_text("被改過\n", encoding="utf-8")
    r = _run(repo, "git checkout -- 白話.txt")
    assert "形態②" in r.stderr, f"中文路徑的 ambient 消失未被回報:\n{r.stderr}"
    assert "白話.txt" in r.stderr, f"路徑被轉義成 \\NNN 而認不出:\n{r.stderr}"


# ── 形態③：mutation 未還原（實際事故 #1）──────────────────────────────


def test_form3_unrestored_mutation_marker_is_reported(tmp_path: Path) -> None:
    """🔴 執行端跑 mutation 被中斷、未還原 ⇒ 工作區留下 `MUTATION` 標記 ⇒ 必須講話。"""
    repo = _repo(tmp_path)
    r = _run(repo, "printf '# MUTATION: remove function-name brace form\\n' >> tracked.txt")
    assert "形態③" in r.stderr, f"未還原的 mutation 標記未被回報:\n{r.stderr}"
    assert "MUTATION" in r.stderr, f"未把該行秀出來:\n{r.stderr}"


def test_form3_does_not_fire_on_the_word_alone_in_untracked_file(tmp_path: Path) -> None:
    """🔴 形態③ 判準綁 `git diff`（tracked 檔的新增行），未追蹤檔不算。

    否則委員產出檔裡提到 MUTATION 兩個字就會誤報——本 repo 的收斂檔常常提到。
    """
    repo = _repo(tmp_path)
    r = _run(repo, "printf 'MUTATION 這個詞出現在未追蹤檔\\n' > note.md")
    assert "形態③" not in r.stderr, f"未追蹤檔誤觸形態③:\n{r.stderr}"
    # 但它仍應被列進「其餘變動」——不判違規，只是不得靜默
    assert "note.md" in r.stderr, f"新增檔完全沒被提到:\n{r.stderr}"


# ── 契約：只回報，不擋 ────────────────────────────────────────────────


def test_reporter_never_changes_rc(tmp_path: Path) -> None:
    """🔴 票 B-50 閉合條件逐字：「**不必擋，但不得靜默**」⇒ 回報函式必須 rc=0。

    若它回非 0，`committee_run` 尾段的 `rc_all` 判斷會被污染，
    正常輪次會被誤判成失敗——那比靜默更糟。
    """
    repo = _repo(tmp_path)
    for mutate in (
        ":",
        "git checkout -- tracked.txt",
        "printf '# MUTATION: x\\n' >> tracked.txt",
    ):
        r = _run(repo, mutate)
        assert "REPORT_RC=0" in r.stdout, f"回報函式改了 rc（mutate={mutate!r}）:\n{r.stdout}"


def test_snapshot_is_taken_before_any_dispatch() -> None:
    """🔴 順序即正確性：快照若取在派工之後，比對永遠是空的。

    這是「檢查存在但由構造上永遠通過」那一類假閘（本專案已犯過，見 GOVB1 recon）。
    """
    s = COMMITTEE_RUN.read_text(encoding="utf-8")
    snap = s.index('_WS_BEFORE="$(_ws_snapshot)"')
    # 🔴 錨定**真正的派工那一行**，不能用 `for f in ${fams}; do`
    #   ——那個字串在 `_build_open_json_fields()` 裡也有一個，`str.index` 會抓到前面那個
    #   （主委初版即如此，測試因而誤紅；這正是「量到的東西 ≠ 想證明的東西」）。
    dispatch = s.index('ROUND_ID="${round_id}" bash "${SCRIPT_DIR}/cx_run.sh"')
    report = s.index("_report_workspace_drift\n\nif [")
    assert snap < dispatch, "快照取在派工迴圈之後 ⇒ 比對永遠為空"
    assert dispatch < report, "回報排在派工之前 ⇒ 比不到執行端的改動"


def test_form1_limitation_is_declared_not_silently_dropped() -> None:
    """🔴 形態①（改動是否逸出該輪允許清單）本層做不到——**必須寫成具名殘留**。

    「做不到」與「沒寫」的差別就是這條：碼註解裡要講清楚為什麼做不到、殘留在哪張票。
    """
    s = COMMITTEE_RUN.read_text(encoding="utf-8")
    seg = s[s.index("票 B-50 `GOV-EXECUTOR-WORKSPACE-NOT-RESTORED`") : s.index("_ws_snapshot() {")]
    assert "形態①" in seg, "未宣告形態① 的限制"
    assert "brief" in seg and "清單" in seg, "未說明做不到的機械原因"
    assert "票 B-50" in seg, "未指回殘留票"


@pytest.mark.parametrize("form", ["形態②", "形態③"])
def test_each_form_is_independently_falsifiable(form: str, tmp_path: Path) -> None:
    """🔴 每個形態都要有「不該觸發時不觸發」的反向對照，否則無法區分真判定與恆真。"""
    repo = _repo(tmp_path)
    # 只新增一個未追蹤檔：兩種形態都不該觸發
    r = _run(repo, "printf 'plain\\n' > plain.md")
    assert form not in r.stderr, f"{form} 在不該觸發時觸發了:\n{r.stderr}"
