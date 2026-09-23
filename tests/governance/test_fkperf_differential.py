"""FKPERF 差分驗收（docs/FKPERF_SPEC.md Task 0.1、1.1、1.2、2.1、3.1、3.2、3.3）。

每條 SPEC 邊界恰對應一支 `test_boundary_NN_*`（編號對照見各測試 docstring）。
每筆語料先斷言 oracle 命中預期分支標籤（標籤由 `exit_catalog()` 自 oracle 原始碼列舉；成功分支標 "ok"），
再斷言新實作與 oracle 逐位元組相同（C-1）。實作前本檔應為紅（helper 與核心皆為空殼）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Sequence

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
            assert first == case.expect_first_line, (case.case_id, first)


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


def test_exit_sites_cover_every_stderr_line_of_oracle() -> None:
    """Task 0.1 驗證④之獨立錨（r5 grok P1-01）：以本測試自帶之正則掃 oracle 原始碼中每一條寫 stderr 之行
    （`>&2` 或 `_fk_die `），`exit_sites()` 須恰逐行歸類——歸到出口標籤、"continuation"（多行訊息之後續行）
    或 "helper"（`_fk_die` 定義行）；每個出口標籤至少有一行歸入。出口清單少列一個出口 ⇒ 該行無歸類即紅。"""
    import re
    import subprocess
    src = subprocess.run(["git", "-C", str(fo.REPO), "show", f"{fo.ORACLE_COMMIT}:scripts/gen_fact_key_blocks.sh"],
                         capture_output=True, text=True, check=True).stdout
    lines = {n for n, l in enumerate(src.splitlines(), 1) if re.search(r">&2|_fk_die ", l)}
    sites = fo.exit_sites()
    cat = fo.exit_catalog()
    assert set(sites) == lines, (sorted(lines - set(sites))[:10], sorted(set(sites) - lines)[:10])
    assert set(sites.values()) <= set(cat) | {"continuation", "helper"}
    assert set(cat) <= set(sites.values()), sorted(set(cat) - set(sites.values()))


def test_corpus_covers_all_five_kinds_and_help_variants() -> None:
    """Task 0.1 改法：五類語料皆非空；語料①含 `--help`（經入口、相對路徑、同目錄 symlink）與 C-5 前置例外配對。"""
    for kind in ("real", "sandbox", "exit", "key_order", "bytes"):
        assert fo.corpus(kind), kind
    real_ids = {c.case_id for c in fo.corpus("real")}
    for need in ("help-entry", "help-relative", "help-symlink", "preflight-missing-interpreter"):
        assert need in real_ids, need


def test_mutation_one_extra_byte_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 0.1 驗證③：新實作 stdout 多一個位元組 ⇒ 差分報差異。"""
    case = fo.corpus("real")[0]
    orig = fo.run_new

    def broken(root: Path, c: fo.Case) -> fo.RunOut:
        out = orig(root, c)
        return fo.RunOut(out.rc, out.stdout + b"x", out.stderr, out.files)

    monkeypatch.setattr(fo, "run_new", broken)
    assert fo.check_case(tmp_path, case) != []


# ---------------------------------------------------------------- 邊界（Task 0.1）

def test_boundary_01_missing_dependency_both_fail_closed(tmp_path: Path) -> None:
    """Task 0.1 邊界①：沙箱缺 rows_source 來源、receipt 或 settings.json ⇒ 兩實作同樣 fail-closed。"""
    for i, (omit, label) in enumerate((
        (("scripts/governance_families.json",), "rows_source_missing"),
        (("handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md",), "mechanism_receipt_missing"),
        ((".claude/settings.json",), "enforcement_settings_missing"),
    )):
        _assert_same(tmp_path / str(i), _case(f"b01-{i}", ["--check"], _tree(omit=omit), label))


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
    _assert_same(tmp_path, _case("b09", ["--check"], _tree(_write("白話說明/a\nb.md", "WL-01 收案\n")), "handwritten_status"))


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
                                 "handwritten_status"))


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
