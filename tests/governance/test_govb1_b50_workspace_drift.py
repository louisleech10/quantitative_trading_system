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
    """抽出偵測層的三支函式（不執行主流程）。"""
    s = COMMITTEE_RUN.read_text(encoding="utf-8")
    parts = []
    for name in ("_ws_snapshot", "_ws_git_ok", "_report_workspace_drift"):
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


def _run(
    repo: Path, mutate: str, *, prelude: str = "", before_ok: str = "1"
) -> subprocess.CompletedProcess[str]:
    """快照 → 執行 `mutate` → 比對回報。回傳 process（stderr 是本檔的 oracle）。

    `prelude` 在快照**之前**執行（用於建立既有 dirty 狀態）；
    `before_ok` 模擬 `_WS_BEFORE_OK` 旗標（`CODEX-R1-P2-05` 的 checker-unavailable 路徑）。
    """
    script = (
        "set -u\n"
        + _fn_src()
        + "\n"
        + prelude
        + '\n_WS_BEFORE="$(_ws_snapshot)"\n'
        + f'_WS_BEFORE_OK={before_ok}\n'
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
    # 🔴 `CODEX-R1-P2-03`／`COMPOSER-R1-P1-02` 修補後：②③ 未命中 ⇒ 壓成一行低噪摘要，
    #    **不再**逐項列出（每輪都紅 ⇒ 人會養成忽略的習慣 ⇒ 等於沒做）。
    assert "無污染跡象" in r.stderr, f"未給低噪摘要:\n{r.stderr}"
    assert "🔴" not in r.stderr, f"未命中②③ 卻用了紅色告警:\n{r.stderr}"


# ── r1 findings 的修補驗證 ─────────────────────────────────────────────


def test_form2_is_not_masked_by_prefix_path(tmp_path: Path) -> None:
    """🔴 `CODEX-R1-P1-02`（BLOCKING）：前綴關係曾使形態② **靜默漏報**。

    codex 的反例逐字重現：before=` M a`；派工期間還原 `a` 並新增 `a-new`。
    舊版對整份 status 文字做 `grep -qF "a"`，會在 `a-new` 上命中 ⇒ 判定「a 還在」⇒ 不報。
    修法＝逐筆 **exact record** 比對（`grep -qxF` 對路徑集合）。
    """
    repo = _repo(tmp_path)
    (repo / "a").write_text("base\n", encoding="utf-8")
    assert _git(repo, "add", "a").returncode == 0
    assert _git(repo, "commit", "-q", "-m", "add a").returncode == 0
    (repo / "a").write_text("ambient\n", encoding="utf-8")
    r = _run(repo, "git checkout -- a\nprintf 'new\\n' > a-new")
    assert "形態②" in r.stderr, f"前綴關係造成靜默漏報（r1 BLOCKING 復發）:\n{r.stderr}"
    assert "\n      a\n" in r.stderr or r.stderr.count("      a\n") >= 1, (
        f"未指出消失的是 `a`:\n{r.stderr}"
    )


def test_form2_handles_paths_with_space(tmp_path: Path) -> None:
    """含空白的路徑不得因 `git status` 加引號而對不上（`-z` records 不加引號）。"""
    repo = _repo(tmp_path)
    (repo / "with space.txt").write_text("base\n", encoding="utf-8")
    assert _git(repo, "add", "with space.txt").returncode == 0
    assert _git(repo, "commit", "-q", "-m", "add spaced").returncode == 0
    (repo / "with space.txt").write_text("ambient\n", encoding="utf-8")
    r = _run(repo, "git checkout -- 'with space.txt'")
    assert "形態②" in r.stderr, f"含空白路徑的形態② 漏報:\n{r.stderr}"
    assert "with space.txt" in r.stderr, r.stderr


def test_form2_newline_in_path_does_not_collide(tmp_path: Path) -> None:
    """🔴 `CODEX-R2-P1-02`（BLOCKING）：路徑含換行時與同名前段路徑**碰撞** ⇒ 形態② 靜默漏報。

    codex 反例：ambient 是 `line1\\nline2`；派工期間把它還原，另外新增 `line1`。
    舊版先把 NUL 轉成換行，`line1\\nline2` 被切成兩行，`line1` 那半剛好被新檔佔住
    ⇒ 判定「還在」⇒ 不報。修法＝先把真換行換成 \\001，再轉 record 分隔符。
    """
    repo = _repo(tmp_path)
    weird = "line1\nline2"
    (repo / weird).write_text("base\n", encoding="utf-8")
    assert _git(repo, "add", "--", weird).returncode == 0
    assert _git(repo, "commit", "-q", "-m", "add newline path").returncode == 0
    (repo / weird).write_text("ambient\n", encoding="utf-8")
    r = _run(repo, "git checkout -- $'line1\\nline2'\nprintf 'x\\n' > line1")
    assert "形態②：" in r.stderr, f"含換行路徑造成碰撞漏報:\n{r.stderr}"


def test_rename_second_record_is_not_a_false_positive(tmp_path: Path) -> None:
    """🔴 `CODEX-R2-P2-03`：rename 的第二筆是**裸路徑**，砍前 3 字元會誤報形態②。

    合法的 staged rename（`R  new\\0old\\0`）不是執行端污染。**假紅燈比漏報更傷信號可信度**
    ——它會讓人學會忽略這一層。主委在 r2 brief 裡判「只會少一個比對項」，**被反例推翻**。
    """
    repo = _repo(tmp_path)
    (repo / "old.txt").write_text("base\n", encoding="utf-8")
    assert _git(repo, "add", "old.txt").returncode == 0
    assert _git(repo, "commit", "-q", "-m", "add old").returncode == 0
    (repo / "old.txt").write_text("ambient\n", encoding="utf-8")
    r = _run(repo, "git add old.txt && git mv old.txt new.txt")
    assert "形態②：" not in r.stderr, f"合法 rename 被誤報成執行端污染:\n{r.stderr}"


def test_checker_unavailable_leaves_a_receipt(tmp_path: Path) -> None:
    """🔴 `CODEX-R1-P2-05`：git 不可用時**不得靜默**——否則「沒告警」會被誤讀成「乾淨」。"""
    repo = _repo(tmp_path)
    r = _run(repo, "git checkout -- tracked.txt", before_ok="0")
    assert "未完成" in r.stderr, f"checker 不可用卻沒留 receipt:\n{r.stderr}"
    assert "REPORT_RC=0" in r.stdout


def test_normal_round_stays_low_noise(tmp_path: Path) -> None:
    """🔴 `COMPOSER-R1-P1-02`：正常輪（只產生新檔）必須是**一行**，不得紅色告警＋逐項列出。

    委員實測舊版每輪固定印 banner ＋ 明細 ⇒ 訊噪比過低會被習慣性忽略。
    """
    repo = _repo(tmp_path)
    r = _run(repo, "printf 'out\\n' > handoffs-out.md\nprintf 'log\\n' > run.log")
    lines = [ln for ln in r.stderr.splitlines() if ln.strip()]
    assert len(lines) == 1, f"正常輪不是一行低噪摘要:\n{r.stderr}"
    assert "無污染跡象" in lines[0]


def test_content_only_change_on_dirty_path_limit_is_declared(tmp_path: Path) -> None:
    """🔴 `CODEX-R1-P2-04`：已是 dirty 的檔再被改一次，status 行不變 ⇒ **本層看不到**。

    這是本層可及的上界，**必須明寫**而不是藏起來。本測同時驗
    ①行為確實如此（不假裝有偵測）②上界宣告存在於原始碼。
    """
    repo = _repo(tmp_path)
    r = _run(
        repo,
        "printf 'second change\\n' >> tracked.txt",
        prelude="printf 'ambient\\n' >> tracked.txt",
    )
    assert r.stderr.strip() == "", f"本層宣稱看不到內容增量，卻印了東西:\n{r.stderr}"
    s = COMMITTEE_RUN.read_text(encoding="utf-8")
    assert "不偵測既有 dirty path 的內容增量" in s, "上界未明寫 ⇒ 缺口會被誤以為已覆蓋"


def test_quotepath_false_is_a_non_removable_invariant() -> None:
    """🔴 `COMPOSER-R1-P2-02`：`core.quotePath=false` 一旦被刪，中文路徑全部對不上。"""
    s = COMMITTEE_RUN.read_text(encoding="utf-8")
    start = s.index("_ws_snapshot() {")
    body = s[start : s.index("\n}\n", start)]
    assert "core.quotePath=false" in body, "快照命令缺 core.quotePath=false"
    assert "--porcelain -z" in body, "未用 NUL records ⇒ 含空白/引號路徑會被轉義"
    assert "不可刪 invariant" in s, "未標記為不可刪 invariant"


def test_exact_record_match_is_not_downgraded() -> None:
    """🔴 `grep -qxF` 退回 `grep -qF` 就會讓 r1 的 BLOCKING 復發——釘住這一個字元。"""
    s = COMMITTEE_RUN.read_text(encoding="utf-8")
    start = s.index("_gone=\"$(")
    seg = s[start : s.index('\n  )"', start)]
    assert "grep -qxF" in seg, "形態② 的比對退回子字串比對 ⇒ 前綴漏報會復發"
    assert "_after_paths" in seg, "未對**路徑集合**比對，而是對整份 status 文字"


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
    # 🔴 錨定**觸發訊息**（`形態②：`／`形態③：` 帶全形冒號），不能用裸字串——
    #   低噪摘要那行寫著「形態②③ 皆未命中」，裸字串比對會把「沒觸發」誤判成「觸發了」。
    #   （主委初版即如此；這正是「量到的東西 ≠ 想證明的東西」，本 epic 反覆出現的那一類。）
    assert f"{form}：" not in r.stderr, f"{form} 在不該觸發時觸發了:\n{r.stderr}"
