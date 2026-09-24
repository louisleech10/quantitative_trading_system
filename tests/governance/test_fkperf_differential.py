"""FKPERF 差分驗收（docs/FKPERF_SPEC.md Task 0.1、1.1、1.2、2.1、3.1、3.2、3.3）。

每條 SPEC 邊界恰對應一支 `test_boundary_NN_*`（編號對照見各測試 docstring）。
每筆語料先斷言 oracle 命中預期分支標籤（標籤由 `exit_catalog()` 自 oracle 原始碼列舉；成功分支標 "ok"），
再斷言新實作與 oracle 逐位元組相同（C-1）。實作前本檔應為紅（helper 與核心皆為空殼）。
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import pytest

from tests.governance import _fkperf_oracle as fo

REG_REL = "scripts/fact_keys.json"


# ---------------------------------------------------------------- 沙箱建法（建樹＋對註冊表／宿主之單點改動）

def _edit_registry(root: Path, fn: Callable[[dict], None]) -> None:
    p = root / REG_REL
    data = json.loads(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tree(*edits: Callable[[Path], None], omit: Sequence[str] = (), git_init: bool = True,
          minimal: bool = False) -> Callable[[Path], None]:
    def build(root: Path) -> None:
        fo.build_sandbox_tree(root, omit=omit, git_init=git_init, minimal=minimal)
        for e in edits:
            e(root)
    return build


def _write(rel: str, text: str) -> Callable[[Path], None]:
    def edit(root: Path) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return edit


def _reg(fn: Callable[[dict], None]) -> Callable[[Path], None]:
    return lambda root: _edit_registry(root, fn)


def _sync(root: Path) -> None:
    """合規之註冊表改動後，以該沙箱自身之入口 `--write` 同步宿主區塊；否則 `--check` 首行為漂移而非目標出口
    （2026-09-23 主委以現行生成器實測：未同步時 b12 首行為 FACTKEY DRIFT）。"""
    import subprocess
    r = subprocess.run(["bash", "scripts/gen_fact_key_blocks.sh", "--write"], cwd=str(root), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def _case(case_id: str, args: Sequence[str], build: Callable[[Path], None], label: str, first: str = None,
          **kw) -> fo.Case:
    """label＝`exit_catalog()` 之出口標籤，或 "ok"（rc=0）。
    "ok" 須以 `first` 給 oracle stdout 首行之字面（空輸出為 ""；2026-09-23 主委以現行生成器實測），
    成功分支亦釘首行（r5 grok P1-01）。"""
    cat = fo.exit_catalog()
    if label == "ok":
        assert first is not None, f"{case_id}：成功分支須給 stdout 首行字面"
        return fo.Case(case_id, tuple(args), build, 0, first, **kw)
    assert label in cat, f"出口標籤 {label!r} 不在 oracle 出口清單（Task 0.1 須列舉之）"
    if first is not None:
        # 訊息含輸入之動態段（檔名、receipt 路徑）者，同一出口於不同輸入之首行不同：以本邊界之實跑字面為準，
        # 並須與 catalog 值共用同一靜態前綴（至第一個動態段為止）
        assert first.split("：")[0].split(":")[0] == cat[label].split("：")[0].split(":")[0], (first, cat[label])
        return fo.Case(case_id, tuple(args), build, 1, first, **kw)
    return fo.Case(case_id, tuple(args), build, 1, cat[label], **kw)


def _assert_same(tmp_path: Path, case: fo.Case) -> None:
    diffs = fo.check_case(tmp_path, case)
    assert diffs == [], f"{case.case_id}：新實作與 oracle 不同：{diffs}"


def _first_status_row(data: dict, key: str) -> list:
    return list(data[key]["rows"][0])


# ---------------------------------------------------------------- Task 0.1 驗證項

def test_oracle_self_zero_diff_and_real_check_rc0(tmp_path: Path) -> None:
    """Task 0.1 驗證①：oracle 對 oracle 差異 0，且至少一筆為真實 repo 之 `--check` rc=0（證明沙箱完整）。"""
    real = [c for c in fo.corpus("real") if c.args == ("--check",)]
    assert real, "語料①缺真實 repo 之 --check"
    oroot, _ = fo.make_pair(tmp_path, real[0])
    a = fo.run_oracle(oroot, real[0])
    b = fo.run_oracle(oroot, real[0])
    assert a.rc == 0, a.stderr.decode("utf-8", "replace")
    assert fo.diff(a, b) == []


def test_every_case_hits_its_expected_branch(tmp_path: Path) -> None:
    """Task 0.1 驗證②：每筆語料之 oracle 命中其預期分支標籤（共同前置失敗不得充數）。"""
    for kind in ("real", "sandbox", "exit", "key_order", "bytes"):
        for case in fo.corpus(kind):
            oroot, _ = fo.make_pair(tmp_path / case.case_id, case)
            out = fo.run_oracle(oroot, case)
            assert out.rc == case.expect_rc, case.case_id
            stream = out.stderr if case.expect_rc else out.stdout
            first = stream.decode("utf-8", "replace").splitlines()[0] if stream else ""
            assert first == fo.expected_first(case, oroot), (case.case_id, first)
            shutil.rmtree(tmp_path / case.case_id, ignore_errors=True)  # 逐筆即刪：409 筆沙箱累積為 GB 級


@pytest.mark.parametrize("kind", ["real", "sandbox", "exit", "key_order", "bytes"])
def test_every_corpus_case_new_equals_oracle(tmp_path: Path, kind: str) -> None:
    """Task 0.1 改法（r5 grok P1-01）：五類語料之每一筆，新實作與 oracle 逐位元組相同（C-1）——
    不只邊界 01–18 點名者；`check_case` 先斷言 oracle 命中預期分支再比差異。"""
    cases = fo.corpus(kind)
    assert cases, kind
    for case in cases:
        diffs = fo.check_case(tmp_path / case.case_id, case)
        assert diffs == [], f"{case.case_id}：新實作與 oracle 不同：{diffs}"


def test_exit_catalog_equals_corpus_labels() -> None:
    """Task 0.1 驗證④：出口清單與「exit」類語料之分支標籤集合相等（少列一個出口或多一筆無主語料即紅）。
    `corpus("exit")` 之每筆以手寫建法與字面首行構成，不得由 `exit_catalog()` 轉手產生（否則集合恆等；r5 grok P1-01）。"""
    cat = fo.exit_catalog()
    labels = {c.expect_first_line for c in fo.corpus("exit")}
    assert set(cat.values()) == labels


_SITE_LIT = re.compile(r"""(?:echo|_fk_die)\s+"([^"]*)|printf\s+'([^']*)'""")
_SITE_TERM = re.compile(r"return 1|exit [1-9]|_rc=1|_fk_die ")
# oracle 內部工具（jq／awk／mktemp 子程序）自身失敗之出口：新實作不呼叫這些子程序（C-2 目標），無對應分支，
# 不建差分語料（manifest not_executable 同名項）。封閉字面集；2026-09-24 主委對 oracle 實跑恰命中 24 行（測試釘此數）：
# L213 216 218 221 234 256 419 691 695 706 1440 1496 1553 1587 1626 1706 1730 1754 1816 1842 1937 1954 1983 2035。
# 另實測：L218 可由 TMPDIR 不可用觸發、L2035 可由宿主目錄唯讀觸發，但兩者 oracle 之 stderr 首行皆為子程序／bash 自身
# 訊息且含隨機字尾或 PID（mktemp: mkdtemp failed on …XXXXXX；…factkey-blk.<pid>: Permission denied），本質不可逐位元組比對。
_TOOL_FAILURE = re.compile(r"jq 非零|jq 失敗|讀取[^→]*失敗|判定執行失敗|無法建立暫存目錄|無法寫暫存註冊表|寫入失敗"
                           r"|無法解析 repo 根|GEN FAILED|驗證無法執行")


def _site_rules(src: List[str], n: int) -> Tuple[Set[str], Optional[str]]:
    """oracle 第 n 行（寫 stderr 者）之允許歸類與其靜態訊息字面（r6 codex／grok P1-01）。
    回傳 ({"helper"}|{"warning"}|{"LABEL"}|{"LABEL","continuation"}|{"LABEL","tool_failure"}, 字面或 None)；LABEL＝須為 exit_catalog 之鍵。
    - tool_failure：出口首行之字面合 `_TOOL_FAILURE` 封閉集（oracle 內部子程序失敗；不入 catalog、不建語料）。
    - helper：只准 `_fk_die()` 定義行。
    - 含 `_fk_die "` ⇒ LABEL。字面以 `gen_fact_key_blocks:`／`FACTKEY` 開頭者 ⇒ LABEL，唯上一物理行為未終止分支之
      stderr 行時亦可為 continuation（如 L792 接於 L791 之後；r7 grok P1-01）；字面不含 `fail-closed` 且同一分支
      （至 `;;`、行尾 `}` 或 `fi`，至多 8 行）無 return 1／exit／_rc=1 者為 warning。
    - 其餘：字面以兩空白開頭、`>&2` 落在上一行以 `\\` 續行之下一物理行、或 `printf '%s\\n'` 類變數明細且上一物理行為
      未終止分支之 stderr 行 ⇒ 可為 continuation；否則須為 LABEL（如 L791 為出口首行，r7 grok P1-01）。"""
    def lit(k: int) -> Optional[str]:
        m = _SITE_LIT.search(src[k - 1])
        if m:
            return m.group(1) if m.group(1) is not None else m.group(2)
        return lit(k - 1) if k >= 2 and src[k - 2].rstrip().endswith("\\") else None

    def branch_exits(k: int) -> bool:
        for j in range(k, min(k + 8, len(src)) + 1):
            t = src[j - 1]
            if _SITE_TERM.search(t):
                return True
            if ";;" in t or t.rstrip().endswith("}") or t.strip() == "fi":
                return False
        return True

    def prev_open(k: int) -> bool:
        """上一物理行為 stderr 行且未終止分支（無 return／exit／_rc=1／_fk_die／`;;`）——r7 grok P1-01。"""
        p = src[k - 2] if k >= 2 else ""
        return bool(re.search(r">&2|_fk_die ", p)) and not _SITE_TERM.search(p) and ";;" not in p

    t, s = src[n - 1], lit(n)
    if re.match(r"\s*_fk_die\(\)", t):
        return {"helper"}, s
    text = s or ""
    head = '_fk_die "' in t or text.startswith(("gen_fact_key_blocks:", "FACTKEY"))
    if head and _TOOL_FAILURE.search(text) and not prev_open(n):
        return {"LABEL", "tool_failure"}, s
    if '_fk_die "' in t:
        return {"LABEL"}, s
    if head:
        if "fail-closed" not in text and not branch_exits(n):
            return {"warning"}, s
        return ({"LABEL", "continuation"} if prev_open(n) else {"LABEL"}), s
    cont = (text.startswith("  ") or (n >= 2 and src[n - 2].rstrip().endswith("\\"))
            or (re.search(r"printf\s+'\s*%s(\\n)?'", t) and prev_open(n)))
    return ({"LABEL", "continuation"} if cont else {"LABEL"}), s


def _static_prefix(s: str) -> str:
    return re.split(r"[$%]", s, maxsplit=1)[0]


# 首行字面與他出口相同之標籤 → 其所在 oracle 函式（2026-09-24 主委讀 oracle 原始碼：L1848 在 _fk_check、L2014 在 _fk_write）
_DUP_LABEL_FUNC = {"missing_target_check": "_fk_check", "missing_target_write": "_fk_write"}


def _enclosing_func(src: Sequence[str], n: int) -> str:
    """oracle 第 n 行所在之 bash 函式名（往上找最近之 `name() {`）；不在任何函式內回傳空字串。"""
    for line in reversed(src[: n - 1]):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\(\) *\{", line)
        if m:
            return m.group(1)
    return ""


def test_mutation_duplicate_literal_exit_sites_swapped_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """r1 codex P2-06：互換兩個同字面出口（L1848 ↔ L2014）之標籤 ⇒ 出口完整性測試必紅。"""
    orig = fo.exit_sites
    swapped = {**orig(), 1848: orig()[2014], 2014: orig()[1848]}
    monkeypatch.setattr(fo, "exit_sites", lambda: swapped)
    with pytest.raises(AssertionError):
        test_exit_sites_cover_every_stderr_line_of_oracle()


def test_exit_sites_cover_every_stderr_line_of_oracle() -> None:
    """Task 0.1 驗證④之獨立錨（r5 grok P1-01；r6 codex／grok P1-01 收緊）：以本測試自帶之正則掃 oracle 每一條寫 stderr
    之行（`>&2` 或 `_fk_die `），`exit_sites()` 須逐行歸類且合 `_site_rules`；出口首行不得歸為 continuation／helper，
    出口首行之標籤兩兩相異，且 `exit_catalog()[標籤]` 以該行靜態字面（至首個 `$`／`%` 為止）開頭；每個出口標籤至少一行。
    出口清單少列一個出口 ⇒ 該行不得為續行而又無標籤可用即紅（2026-09-23 主委以本規則實跑 oracle：187 行＝helper 1、
    warning 2〔L1505、L1786，皆不退出〕、tool_failure 24、須標籤 119〔含 L791〕、可續行 41〔含 L792、L1689、L1696〕；2026-09-24 實作時重跑）。"""
    import subprocess
    src = subprocess.run(["git", "-C", str(fo.REPO), "show", f"{fo.ORACLE_COMMIT}:scripts/gen_fact_key_blocks.sh"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    lines = {n for n, l in enumerate(src, 1) if re.search(r">&2|_fk_die ", l)}
    sites = fo.exit_sites()
    cat = fo.exit_catalog()
    assert set(sites) == lines, (sorted(lines - set(sites))[:10], sorted(set(sites) - lines)[:10])
    label_lines: Dict[str, int] = {}
    for n in sorted(lines):
        allowed, s = _site_rules(src, n)
        v = sites[n]
        if v in ("helper", "warning", "continuation", "tool_failure"):
            assert v in allowed, (n, v, sorted(allowed))
            continue
        assert "LABEL" in allowed and v in cat, (n, v)
        if allowed == {"LABEL"}:
            assert v not in label_lines, (n, label_lines.get(v), v)
            label_lines[v] = n
        if s:
            assert cat[v].startswith(_static_prefix(s)), (n, v, cat[v], s)
    # 同字面之出口首行（如 L1848／L2014 皆印 MISSING TARGET）：字面擋不住兩標籤互換，改以所在 oracle 函式定位（r1 codex P2-06）
    by_prefix: Dict[str, List[str]] = {}
    for v, n in label_lines.items():  # 整行字面、變數名一律視同（兩行只差區域變數名即同字面）
        literal = re.sub(r"\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*", "$", src[n - 1].strip())
        by_prefix.setdefault(literal, []).append(v)
    dups = {v for vs in by_prefix.values() if len(vs) > 1 for v in vs}
    assert dups == set(_DUP_LABEL_FUNC), (sorted(dups), sorted(_DUP_LABEL_FUNC))
    for v in sorted(dups):
        assert _enclosing_func(src, label_lines[v]) == _DUP_LABEL_FUNC[v], (v, label_lines[v], _enclosing_func(src, label_lines[v]))
    tool_lines = [n for n in sorted(lines) if "tool_failure" in _site_rules(src, n)[0]]
    assert tool_lines == [213, 216, 218, 221, 234, 256, 419, 691, 695, 706, 1440, 1496, 1553, 1587, 1626, 1706, 1730,
                          1754, 1816, 1842, 1937, 1954, 1983, 2035], tool_lines  # 逐行釘死（r11 codex P2-03：只釘數量擋不住同數量換位）
    assert set(cat) <= set(sites.values()), sorted(set(cat) - set(sites.values()))


def test_new_impl_host_write_failure_is_fail_closed(tmp_path: Path) -> None:
    """SPEC v7 Task 0.1 ③：宿主寫入失敗（L2035 屬 tool_failure、訊息不比對）時，新實作仍須 rc=1 fail-closed，
    且宿主檔位元組不變（不留半寫）。以宿主所在目錄唯讀觸發（2026-09-24 主委以 oracle 實測可觸發）。"""
    import os
    import stat

    def add(d: dict) -> None:
        d["eventscan-banner"]["rows"].append(["997", "zz", "x", "y"])

    case = _case("wfail", ["--write"], _tree(_reg(add)), "ok", first="")
    _, nroot = fo.make_pair(tmp_path, case)
    data = json.loads((nroot / REG_REL).read_text(encoding="utf-8"))
    tgt = data["eventscan-banner"]["target"]
    host = nroot / (tgt[0] if isinstance(tgt, list) else tgt)
    before = host.read_bytes()
    mode = host.parent.stat().st_mode
    os.chmod(host.parent, stat.S_IRUSR | stat.S_IXUSR)
    try:
        out = fo.run_new(nroot, case)
    finally:
        os.chmod(host.parent, mode)
    assert out.rc == 1, out.stderr.decode("utf-8", "replace")
    assert host.read_bytes() == before


@pytest.mark.parametrize("args", [(), ("--check",), ("--status-hits", "lines.txt")])
def test_new_impl_tmpdir_unusable_still_succeeds(tmp_path: Path, args: tuple) -> None:
    """SPEC C-1 例外②：TMPDIR 不存在時，新實作照常執行，且 stdout、stderr、rc 等於 oracle 於可用 TMPDIR 下之結果
    （oracle 於不可用 TMPDIR 下 mktemp／暫存重導向失敗：r11 codex 實跑 L691 首行 `…line 687: …<PID>: No such file…`）。"""
    import dataclasses
    case = _case("tmpdir", list(args), _tree(_write("lines.txt", "L1\tWL-01 收案\n")), "ok",
                 first="L1\tWL-01\t收案" if args[:1] == ("--status-hits",) else
                 ("" if args else "<!-- BEGIN GENERATED: committee-roster -->"))
    oroot, nroot = fo.make_pair(tmp_path, case)
    good = fo.run_oracle(oroot, case)
    bad_env = dataclasses.replace(case, env={**case.env, "TMPDIR": str(tmp_path / "no_such_dir" / "x")})
    new = fo.normalize(fo.run_new(nroot, bad_env), nroot, oroot)
    assert good.rc == 0
    assert fo.diff(good, new) == []


def test_new_impl_unreadable_status_hits_file_rc2(tmp_path: Path) -> None:
    """SPEC C-1 例外④：`--status-hits` 行檔存在但不可讀 ⇒ 新實作 rc=2、stdout 無命中、行檔位元組與權限不變
    （oracle 同情境 rc=2，stderr 首行為 awk 自身訊息 `awk: can't open file lines.txt`，r11 codex 實跑；stderr 不比對）。"""
    import os
    case = _case("unreadable", ["--status-hits", "lines.txt"], _tree(_write("lines.txt", "L1\tWL-01 收案\n")), "ok",
                 first="L1\tWL-01\t收案")
    oroot, nroot = fo.make_pair(tmp_path, case)
    lines = nroot / "lines.txt"
    before = lines.read_bytes()
    os.chmod(lines, 0)
    try:
        out = fo.run_new(nroot, case)
        mode_after = lines.stat().st_mode & 0o777
    finally:
        os.chmod(lines, 0o644)
    assert out.rc == 2, out.stderr.decode("utf-8", "replace")
    assert out.stdout == b""
    assert mode_after == 0 and lines.read_bytes() == before


def test_mutation_exit_site_hidden_as_continuation_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """鑑別力（r6 codex／grok P1-01 之反例）：把 L44（`_fk_die "…缺 jq…"`）歸為 continuation ⇒ 歸類規則即紅。"""
    import subprocess
    src = subprocess.run(["git", "-C", str(fo.REPO), "show", f"{fo.ORACLE_COMMIT}:scripts/gen_fact_key_blocks.sh"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    n = next(k for k, l in enumerate(src, 1) if '_fk_die "gen_fact_key_blocks: 缺 jq' in l)
    allowed, _ = _site_rules(src, n)
    assert "continuation" not in allowed and allowed == {"LABEL"}
    orig = fo.exit_sites
    monkeypatch.setattr(fo, "exit_sites", lambda: {**orig(), n: "continuation"})
    with pytest.raises(AssertionError):
        test_exit_sites_cover_every_stderr_line_of_oracle()


def _recorded_coverage_gaps() -> List[Tuple[str, str]]:
    from tests.governance import _fkperf_record as fr
    seen = {(e["nodeid"].split("::")[0], e["nodeid"].split("::")[1].split("[")[0])
            for e in fr.recorded()["log"] if "::" in e["nodeid"]}
    return [(f, t) for f, tests in fr.helper_tests().items() for t in tests if (f, t) not in seen]


def test_recorded_sandbox_corpus_covers_every_helper_test() -> None:
    """Task 0.1 語料②「以 helper 建樹、逐一列入」（r1 codex P1-03、composer P2-01）：既有兩檔中直接或經包裝呼叫
    `_sandbox`／`_mkroot`／`_fk_sandbox`／`_d2_sandbox` 之每一支 test（AST 呼叫圖閉包，獨立於錄製）皆有生成器呼叫之錄製
    紀錄；略過者只准「變異本」與「真 repo 入口」兩類；錄得之每筆以語料 `rec-*` 進入分支斷言與新舊逐筆比對。"""
    from tests.governance import _fkperf_record as fr
    data = fr.recorded()
    assert data["records"], data["tail"]
    assert _recorded_coverage_gaps() == []
    reasons = {e.get("reason") for e in data["log"] if e["status"] == "skipped"}
    assert reasons <= {"mutated", "repo-entry"}, reasons
    assert len([c for c in fo.corpus("sandbox") if c.case_id.startswith("rec-")]) == len(data["records"])


def test_recorded_files_invoke_generator_only_via_subprocess_run() -> None:
    """錄製只攔 `subprocess.run(["bash", …gen_fact_key_blocks.sh, …])`：兩檔不得以其他 API 啟動子程序（否則漏錄）。"""
    import ast
    from tests.governance import _fkperf_record as fr
    other = {"Popen", "check_output", "call", "check_call", "system", "popen", "spawnv", "execv"}
    for rel in fr.RECORD_FILES:
        tree = ast.parse((fo.REPO / rel).read_text(encoding="utf-8"))
        bad = [n.lineno for n in ast.walk(tree)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in other]
        assert bad == [], (rel, bad)


def test_mutation_recorded_corpus_missing_test_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """鑑別力：helper 閉包多出一支未錄之測試 ⇒ 逐一列入之對證必紅。"""
    from tests.governance import _fkperf_record as fr
    orig = fr.helper_tests
    monkeypatch.setattr(fr, "helper_tests", lambda: {**orig(), fr.RECORD_FILES[0]: orig()[fr.RECORD_FILES[0]] + ["test_zz_not_recorded"]})
    with pytest.raises(AssertionError):
        test_recorded_sandbox_corpus_covers_every_helper_test()


def test_jq_error_line_filter_is_exact_and_oracle_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC v8 C-1 ⑤：只刪恰符合 `jq: error (at …): …` 之整行；相近形、行內片段不刪；
    新實作印出此形之行 ⇒ 仍報差異（過濾只套用於 oracle 側）。"""
    raw = (b"gen_fact_key_blocks: a\njq: error (at /tmp/x/fact_keys.json:3742): Cannot iterate over null (null)\n"
           b"xjq: error (at y): z\njq: error: compile\n  jq: error (at y): z\ngen_fact_key_blocks: b\n")
    assert fo.drop_jq_error_lines(raw) == (b"gen_fact_key_blocks: a\nxjq: error (at y): z\njq: error: compile\n"
                                           b"  jq: error (at y): z\ngen_fact_key_blocks: b\n")
    case = next(c for c in fo.corpus("real") if c.case_id == "real-check")
    orig = fo.run_new

    def oracle_plus_jq_line(root: Path, c: fo.Case) -> fo.RunOut:
        (root / c.script_rel).write_bytes(fo._oracle_blob(fo.ENTRY_REL))
        out = fo._run(root, ["bash", c.invoke, *c.args], c, fo._env(root, c.env, c.oracle_env, unset=c.unset_env))
        return fo.RunOut(out.rc, out.stdout, out.stderr + b"jq: error (at x:1): y\n", out.files)

    monkeypatch.setattr(fo, "run_new", oracle_plus_jq_line)
    assert fo.check_case(tmp_path / "jqline", case) != []
    monkeypatch.setattr(fo, "run_new", orig)


def test_corpus_covers_all_five_kinds_and_help_variants() -> None:
    """Task 0.1 改法：五類語料皆非空；語料①含 `--help`（經入口、相對路徑、同目錄 symlink）與 C-5 前置例外配對。"""
    for kind in ("real", "sandbox", "exit", "key_order", "bytes"):
        assert fo.corpus(kind), kind
    real_ids = {c.case_id for c in fo.corpus("real")}
    for need in ("help-entry", "help-relative", "help-symlink", "preflight-missing-interpreter"):
        assert need in real_ids, need


def test_mutation_one_extra_byte_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 0.1 驗證③：新實作之 stdout、stderr、監視宿主檔、或未列於 watch_files 之其他檔各多一個位元組 ⇒ 差分皆報差異
    （r6 grok P1-03：只改 stdout 時，只比 rc／stdout 之 `diff` 亦過）。先以 oracle 充當新實作證零差異基線，
    否則恆報失敗之 `diff` 亦使本測試過（r1 codex P1-02）；未列檔之變異證全樹快照（r1 codex P1-01）。
    C-5 前置例外配對另證：具名訊息行以外多印 stdout／stderr 亦報差異（r1 codex P2-04）。"""
    watched = [c for c in fo.corpus("bytes") if c.watch_files]
    assert watched, "bytes 類語料須至少一筆帶 watch_files（--write 之宿主檔）"
    c5 = next(c for c in fo.corpus("real") if c.expect_new is not None)

    def oracle_as_new(root: Path, c: fo.Case) -> fo.RunOut:
        (root / c.script_rel).write_bytes(fo._oracle_blob(fo.ENTRY_REL))
        return fo._run(root, ["bash", c.invoke, *c.args], c, fo._env(root, c.env, c.oracle_env, unset=c.unset_env))

    def c5_as_new(root: Path, c: fo.Case) -> fo.RunOut:
        out = oracle_as_new(root, c)
        named = fo.first_line(out.stderr).encode("utf-8")
        return fo.RunOut(c.expect_new[0], out.stdout, out.stderr.replace(named, c.expect_new[1].encode("utf-8"), 1), out.files)

    def bump(base: Callable[[Path, fo.Case], fo.RunOut], field: str) -> Callable[[Path, fo.Case], fo.RunOut]:
        def broken(root: Path, c: fo.Case) -> fo.RunOut:
            out = base(root, c)
            if field == "stdout":
                return fo.RunOut(out.rc, out.stdout + b"x", out.stderr, out.files)
            if field == "stderr":
                return fo.RunOut(out.rc, out.stdout, out.stderr + b"x", out.files)
            files = dict(out.files)
            k = c.watch_files[0] if field == "watched" else sorted(set(files) - set(c.watch_files))[0]
            files[k] = (files[k][0] + b"x", files[k][1])
            return fo.RunOut(out.rc, out.stdout, out.stderr, files)
        return broken

    real0 = fo.corpus("real")[0]
    for name, base, case in (("real", oracle_as_new, real0), ("write", oracle_as_new, watched[0]), ("c5", c5_as_new, c5)):
        monkeypatch.setattr(fo, "run_new", base)
        assert fo.check_case(tmp_path / f"base-{name}", case) == [], name
    for field, base, case in (("stdout", oracle_as_new, real0), ("stderr", oracle_as_new, real0),
                              ("watched", oracle_as_new, watched[0]), ("unwatched", oracle_as_new, watched[0]),
                              ("stdout", c5_as_new, c5), ("stderr", c5_as_new, c5)):
        monkeypatch.setattr(fo, "run_new", bump(base, field))
        assert fo.check_case(tmp_path / f"{field}-{case.case_id}", case) != [], (field, case.case_id)


# ---------------------------------------------------------------- 邊界（Task 0.1）

# b01-1 之 receipt 路徑為動態段，首行與 catalog（receipt 指向 __fkperf_missing__）不同：以實跑字面為準（2026-09-24 主委實跑）
_B01_FIRST = {1: "gen_fact_key_blocks: key governance-mechanism 之 receipt 指向不存在之檔："
                  "handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md → fail-closed（宣稱實跑但無物可查）"}


def test_boundary_01_missing_dependency_both_fail_closed(tmp_path: Path) -> None:
    """Task 0.1 邊界①：沙箱缺 rows_source 來源、receipt 或 settings.json ⇒ 兩實作同樣 fail-closed。"""
    for i, (omit, label) in enumerate((
        (("scripts/governance_families.json",), "rows_source_missing"),
        (("handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md",), "mechanism_receipt_missing"),  # 首行見下
        ((".claude/settings.json",), "enforcement_settings_missing"),
    )):
        _assert_same(tmp_path / str(i), _case(f"b01-{i}", ["--check"], _tree(omit=omit), label, first=_B01_FIRST.get(i)))


def test_boundary_02_status_hits_line_with_tab_and_soh(tmp_path: Path) -> None:
    """Task 0.1 邊界②：`--status-hits` 行檔內含 TAB 或 `\\001` ⇒ 照樣比對。"""
    lines = "L1\tWL-01 收案\nL2\tx\x01WL-01 收案\n"
    _assert_same(tmp_path, _case("b02", ["--status-hits", "lines.txt"], _tree(_write("lines.txt", lines)), "ok",
                                 first="L1\tWL-01\t收案"))


def test_boundary_03_non_git_root_both_fail_closed(tmp_path: Path) -> None:
    """Task 0.1 邊界③：非 git 的 ROOT ⇒ 兩實作同樣 fail-closed。"""
    _assert_same(tmp_path, _case("b03", ["--check"], _tree(git_init=False), "scope_not_git_tree"))


# ---------------------------------------------------------------- 邊界（Task 1.1）

def test_boundary_04_empty_registry_rc0(tmp_path: Path) -> None:
    """Task 1.1 邊界①：空註冊表 ⇒ rc=0 契約不變（最小沙箱，比照 `test_empty_registry_is_rc_zero_not_failure`）。"""
    _assert_same(tmp_path, _case("b04", [], _tree(_write(REG_REL, "{}\n"), minimal=True), "ok", first=""))


def test_boundary_05_rows_filter_sequence_overflow(tmp_path: Path) -> None:
    """Task 1.1 邊界②：rows_filter 序號位數溢位（來源 `handoff-pending` 逾三位列數）⇒ 同訊息 fail-closed。
    以 `--write` 跑：註冊表不合規時 `--write` 先驗證即拒，首行為目標出口（`--check` 會先報漂移）。"""
    def grow(d: dict) -> None:
        d["handoff-pending"]["rows"] = [
            [f"{i % 1000:03d}", f"HP-OVF{i:04d}", "進行中", "docs/FKPERF_SPEC.md", f"做 OVF{i}"] for i in range(1000)
        ]
    _assert_same(tmp_path, _case("b05", ["--write"], _tree(_reg(grow)), "rows_filter_seq_overflow"))


def test_boundary_06_nan_literal_rejected(tmp_path: Path) -> None:
    """Task 1.1 邊界③：註冊表含 `NaN` 字面 ⇒ 與 oracle 同訊息 fail-closed——jq 接受 NaN，由 rows 型別檢查拒絕（C-5）。"""
    _assert_same(tmp_path, _case("b06", [], _tree(_write(REG_REL, '{"x": NaN}\n'), minimal=True), "rows_type_mismatch"))


# ---------------------------------------------------------------- 邊界（Task 1.2）

def test_boundary_07_cell_with_control_char_or_pipe(tmp_path: Path) -> None:
    """Task 1.2 邊界①：儲存格含控制字元或 `|` ⇒ 同訊息 fail-closed。"""
    for i, (bad, label) in enumerate((("a\x01b", "cell_control_char"), ("a|b", "cell_pipe_in_table"))):
        def put(d: dict, bad: str = bad) -> None:
            d["eventscan-banner"]["rows"][0][2] = bad
        _assert_same(tmp_path / str(i), _case(f"b07-{i}", [], _tree(_reg(put)), label))


def test_boundary_08_rows_differing_only_by_case_sort_like_oracle(tmp_path: Path) -> None:
    """Task 1.2 邊界②：兩列只差大小寫 ⇒ 排序與 oracle 相同（C collation）。"""
    def add(d: dict) -> None:
        d["eventscan-banner"]["rows"] += [["998", "b", "x", "y"], ["998", "B", "x", "y"]]
    _assert_same(tmp_path, _case("b08", [], _tree(_reg(add)), "ok",
                                 first="<!-- BEGIN GENERATED: committee-roster -->"))


# ---------------------------------------------------------------- 邊界（Task 2.1）

def test_boundary_09_filename_with_newline(tmp_path: Path) -> None:
    """Task 2.1 邊界①：範圍內檔名含換行 ⇒ 與 oracle 同判。"""
    _assert_same(tmp_path, _case("b09", ["--check"], _tree(_write("白話說明/a\nb.md", "WL-01 收案\n")), "handwritten_status",
                                 first="FACTKEY HANDWRITTEN STATUS: 白話說明/a<LF>b.md:1 識別碼=WL-01 狀態=收案"))


def test_boundary_10_check_on_non_git_root(tmp_path: Path) -> None:
    """Task 2.1 邊界②：`--check` 之 ROOT 非 git 工作樹 ⇒ 同訊息 fail-closed（經 GOVB1_FACTKEY_ROOT 顯式指定）。
    ROOT 須為宿主檔齊全之樹：指向空目錄時首行為「找不到宿主檔」而非「非 git 樹」（2026-09-23 主委實測）。"""
    case = _case("b10", ["--check"], _tree(git_init=False), "scope_not_git_tree", env={"GOVB1_FACTKEY_ROOT": "."})
    _assert_same(tmp_path, case)


def test_boundary_11_identifier_boundary_b3rb3r(tmp_path: Path) -> None:
    """Task 2.1 邊界③：識別碼邊界（`B3RB3R` 不得被判為 `B3R`）⇒ 與 oracle 同判。"""
    _assert_same(tmp_path, _case("b11", ["--check"], _tree(_write("白話說明/x.md", "B3RB3R 收案\n")), "ok", first=""))


def test_boundary_12_multibyte_identifier_neighbours(tmp_path: Path) -> None:
    """Task 2.1 邊界④：識別碼含多位元組字元、鄰接字元屬或不屬 `A-Za-z0-9_-` ⇒ 與 oracle 同判（C-3 位元組語意）。"""
    def add(d: dict) -> None:  # 手寫狀態偵測之識別碼取自 _schema.status_keys（governance-worklist 在內）
        d["governance-worklist"]["rows"].append(["999", "WL-識別碼", "未開工", "FKPERF 探針"])
    doc = "前WL-識別碼後 未開工\n_WL-識別碼 未開工\nxWL-識別碼 未開工\n"
    _assert_same(tmp_path, _case("b12", ["--check"], _tree(_reg(add), _sync, _write("白話說明/mb.md", doc)),
                                 "handwritten_status",
                                 first="FACTKEY HANDWRITTEN STATUS: 白話說明/mb.md:1 識別碼=WL-識別碼 狀態=未開工"))


# ---------------------------------------------------------------- 邊界（Task 3.1）

def test_boundary_13_mechanism_receipt_path_missing(tmp_path: Path) -> None:
    """Task 3.1 邊界①：機制表 receipt 路徑不存在 ⇒ 同訊息 fail-closed（receipt 相對 ROOT）。"""
    def point(d: dict) -> None:
        key = d["_schema"]["mechanism_keys"][0]
        for row in d[key]["rows"]:
            for j, cell in enumerate(row):
                if cell.startswith("receipt:"):
                    row[j] = "receipt:handoffs/run_receipts/__fkperf_missing__.json"
                    return
    _assert_same(tmp_path, _case("b13", ["--write"], _tree(_reg(point)), "mechanism_receipt_missing"))


def test_boundary_14_criteria_conflicting_expectation(tmp_path: Path) -> None:
    """Task 3.1 邊界②：判準表同範圍同條件相異期望 ⇒ 同判拒絕。"""
    def dup(d: dict) -> None:
        key = d["_schema"]["criteria_keys"][0]
        roles = d["_schema"]["criteria_column_roles"]
        cols = d[key]["columns"]
        row = list(d[key]["rows"][0])
        row[cols.index(roles["id"])] = "C-999"
        e = cols.index(roles["expect"])
        row[e] = "1" if row[e] == "0" else "0"
        d[key]["rows"].append(row)
    _assert_same(tmp_path, _case("b14", ["--write"], _tree(_reg(dup)), "criteria_conflict"))


# ---------------------------------------------------------------- 邊界（Task 3.2）

def test_boundary_15_settings_missing_dir_present(tmp_path: Path) -> None:
    """Task 3.2 邊界①：settings.json 缺失而 `.claude/` 目錄存在 ⇒ 同訊息 fail-closed。"""
    def keep_dir(root: Path) -> None:
        (root / ".claude").mkdir(exist_ok=True)
    _assert_same(tmp_path, _case("b15", ["--check"], _tree(keep_dir, omit=(".claude/settings.json",)),
                                 "enforcement_settings_missing"))


def test_boundary_16_citation_points_at_comment_line(tmp_path: Path) -> None:
    """Task 3.2 邊界②：產出端覆蓋之實作位置引用指向註解行 ⇒ 同判拒絕。"""
    def cite_comment(d: dict) -> None:
        key = d["_schema"]["enforcement_keys"][0]
        for row in d[key]["rows"]:
            for j, cell in enumerate(row):
                if "gen_fact_key_blocks.sh:" in cell:
                    row[j] = cell.split("gen_fact_key_blocks.sh:")[0] + "gen_fact_key_blocks.sh:2"
                    return
    _assert_same(tmp_path, _case("b16", ["--write"], _tree(_reg(cite_comment)), "enforcement_citation_comment_line"))


# ---------------------------------------------------------------- 邊界（Task 3.3）

def test_boundary_17_same_id_in_two_status_keys(tmp_path: Path) -> None:
    """Task 3.3 邊界①：同一識別碼出現在兩個狀態鍵 ⇒ 同訊息 fail-closed。"""
    def clash(d: dict) -> None:
        row = _first_status_row(d, "roadmap-status")
        row[0], row[1] = "996", d["handoff-pending"]["rows"][0][1]
        d["roadmap-status"]["rows"].append(row)
    _assert_same(tmp_path, _case("b17", ["--write"], _tree(_reg(clash)), "status_id_duplicate"))


def test_boundary_18_b9_vs_b9a_token_boundary(tmp_path: Path) -> None:
    """Task 3.3 邊界②：`B9` 與 `B9A` 之識別碼邊界 ⇒ 與 oracle 同判（B9A 不得命中 B9）。"""
    _assert_same(tmp_path, _case("b18", ["--check"], _tree(_write("白話說明/b9.md", "B9A 已完成之前情\n")), "ok", first=""))


# ---------------------------------------------------------------- Task 1.1／1.2 驗證項

def test_key_iteration_order_matches_jq_keys(tmp_path: Path) -> None:
    """Task 1.1 驗證：核心之 fact-key 迭代序＝`jq -r 'keys[]'` 之序（語料④：非排序插入序之註冊表）。"""
    for case in fo.corpus("key_order"):
        assert fo.check_case(tmp_path / case.case_id, case) == []


def test_core_emit_deterministic_no_bom_no_crlf(tmp_path: Path) -> None:
    """Task 1.2 驗證：直呼核心之 emit 連跑三次逐位元組相同、無 BOM、無 CRLF。"""
    case = [c for c in fo.corpus("real") if c.args == ()][0]
    _, nroot = fo.make_pair(tmp_path, case)
    outs: Dict[int, bytes] = {i: fo.run_new(nroot, case).stdout for i in range(3)}
    assert outs[0] == outs[1] == outs[2]
    assert not outs[0].startswith(b"\xef\xbb\xbf") and b"\r\n" not in outs[0]
