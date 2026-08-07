"""GOVB1 Task 0.1 — 契約矩陣／fixture／final gate 機械驗收。

對應 TODO 驗證欄 T-0.1-C1～C3、T-0.1-F1～F5。
禁寫死份數／列數（G-2）；矩陣內容不得硬編碼進測試。
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "scripts" / "gen_govb1_contract_matrix.sh"
GATE = REPO / "scripts" / "govb1_final_gate.sh"
FROZEN = REPO / "scripts" / "govb1_frozen_hashes.txt"
MANIFEST = REPO / "scripts" / "govb1_scope.manifest"
SPEC = REPO / "docs" / "GOVB1_INPUT_QUALITY_SPEC.md"
TODO = REPO / "docs" / "GOVB1_INPUT_QUALITY_TODO.md"
BEHAVIOR_SPEC = REPO / "docs" / "GOV_DISPATCH_FLOW_FIX_SPEC.md"
FIXTURE_ROOT = REPO / "tests" / "governance" / "fixtures" / "govb1"


def _run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
        **kw,  # type: ignore[arg-type]
    )


def _docs_ref_paths() -> set[str]:
    """現跑 grep 導出的 docs/ path 集合（與 gen 同一關鍵字）。"""
    proc = _run(
        [
            "bash",
            "-c",
            "grep -rln 'doc_format_precheck\\|completeness_check\\|cx_run' docs/*.md | LC_ALL=C sort",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def _contract_lines_live(path: str) -> int:
    """單檔現算 contract_lines（與 gen 同一關鍵字）。"""
    proc = _run(
        ["grep", "-cE", "doc_format_precheck|completeness_check|cx_run", path]
    )
    # grep -c：無命中 rc=1 仍 stdout=0
    text = (proc.stdout or "").strip() or "0"
    return int(text.splitlines()[-1])


def _behavior_rows_from_file(text: str) -> list[str]:
    """與 gen／final_gate 同一 pattern（含前導空白＋可選粗體 rc）。"""
    # Python 無 [[:space:]]；改用 \s
    pat = re.compile(r"^\s*\| `.*` \| (\*\*)?rc==", re.M)
    return [ln for ln in text.splitlines() if pat.match(ln)]


def _base_commit() -> str:
    text = FROZEN.read_text(encoding="utf-8")
    m = re.search(r"^base_commit: ([0-9a-f]{40})$", text, re.M)
    assert m, "frozen_hashes 缺 base_commit"
    return m.group(1)


def _is_narrow_g7_status_case(gate_src: str) -> bool:
    """機械判定：_g7 內 status case 僅匹配 ?? / A*（不含 M 類）。

    抽取 `_g7()` 函式體中 `case "${_st}" in ... esac` 的 pattern 臂；
    若所有 pattern 皆為 untracked/added 變體且無 M 字元 ⇒ 窄守衛。
    """
    # 取 _g7() { ... } 至頂層閉合（下一頂層函式或檔尾）
    m = re.search(r"^_g7\(\)\s*\{", gate_src, re.M)
    if not m:
        return False
    rest = gate_src[m.end() :]
    # 下一頂層定義（行首 _name() 或 _name() {）
    nxt = re.search(r"\n_[a-zA-Z0-9]+\(\)", rest)
    body = rest[: nxt.start()] if nxt else rest
    cm = re.search(
        r'case\s+"\$\{_st\}"\s+in\s*(.*?)\s*esac',
        body,
        re.S,
    )
    if not cm:
        return False
    case_body = cm.group(1)
    # 取 pattern 臂：行內 `pat)` 在 `;;` 前
    patterns: list[str] = []
    for arm in re.finditer(r"(?m)^\s*([^\n]+?)\)\s*$", case_body):
        pat = arm.group(1).strip()
        # 跳過通配 catch-all 若有
        patterns.append(pat)
    if not patterns:
        return False
    # 窄＝每個 pattern 只含 ?? 與 A* 變體，且整體無 M
    joined = "|".join(patterns)
    if "M" in joined:
        return False
    # 必須實際覆蓋 ?? 與 A（否則不是「已知窄守衛」而是別的東西）
    has_untracked = any("?" in p for p in patterns)
    has_added = any("A" in p for p in patterns)
    return has_untracked and has_added


# ── T-0.1-C* ──────────────────────────────────────────────────────────


def test_t01_c1_docs_count_matches_live_grep() -> None:
    """T-0.1-C1：矩陣 docs/ 集合 == 現跑 grep 集合；四欄 schema；contract_lines 現算。"""
    proc = _run(["bash", str(GEN)])
    assert proc.returncode == 0, proc.stderr
    matrix_paths: set[str] = set()
    for ln in proc.stdout.splitlines():
        if not ln.startswith("docs/"):
            continue
        parts = ln.split("|")
        assert len(parts) == 4, f"四欄 schema 不符: {ln!r}"
        path, contract_lines, _touched, _evidence = parts
        assert path.startswith("docs/"), path
        assert contract_lines.isdigit(), contract_lines
        live_n = _contract_lines_live(path)
        assert int(contract_lines) == live_n, (
            f"{path}: matrix contract_lines={contract_lines} live={live_n}"
        )
        matrix_paths.add(path)
    ref_paths = _docs_ref_paths()
    assert matrix_paths == ref_paths, (
        f"path 集合不一致 only_matrix={sorted(matrix_paths - ref_paths)} "
        f"only_ref={sorted(ref_paths - matrix_paths)}"
    )


def test_t01_c1_mutation_fake_path_fails() -> None:
    """mutation D：每列 path 換成 docs/fake ⇒ C1 轉紅（非只比列數）。"""
    original = GEN.read_text(encoding="utf-8")
    # 把 printf path 換成固定 docs/fake（保留四欄與 lines 數以維持列數）
    old = 'printf \'%s|%s|%s|%s\\n\' "${f}" "${lines}" "0" "keyword-hit"'
    new = 'printf \'%s|%s|%s|%s\\n\' "docs/fake" "${lines}" "0" "keyword-hit"'
    assert old in original, "mutation 錨點未找到"
    try:
        GEN.write_text(original.replace(old, new, 1), encoding="utf-8")
        proc = _run(["bash", str(GEN)])
        assert proc.returncode == 0, proc.stderr
        matrix_paths = {
            ln.split("|", 1)[0]
            for ln in proc.stdout.splitlines()
            if ln.startswith("docs/")
        }
        ref_paths = _docs_ref_paths()
        # 列數可仍相等，但集合必須不等
        assert matrix_paths != ref_paths, "docs/fake mutation 應使 path 集合不一致"
        assert "docs/fake" in matrix_paths
    finally:
        GEN.write_text(original, encoding="utf-8")


def test_t01_c2_behavior_expected_rc_matches_live() -> None:
    """T-0.1-C2：行為表與 base oracle（git show ${base}:）逐列相符——自身可證偽。"""
    base = _base_commit()
    proc = _run(["bash", str(GEN), "--behavior-only"])
    assert proc.returncode == 0, proc.stderr
    from_gen = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert from_gen, "行為表不得為空"
    # 獨立 oracle：base 樹上的行為表（非自 row 反解析）
    show = _run(["git", "show", f"{base}:docs/GOV_DISPATCH_FLOW_FIX_SPEC.md"])
    assert show.returncode == 0, show.stderr
    from_base = _behavior_rows_from_file(show.stdout)
    assert from_base, "base oracle 行為表不得為空"
    assert from_gen == from_base, (
        "生成器行為表與 base oracle 不一致 "
        f"(gen={len(from_gen)} base={len(from_base)})"
    )
    # 工作樹現讀亦須一致（漂移由本斷言與 _g5 雙重捕捉）
    from_file = _behavior_rows_from_file(BEHAVIOR_SPEC.read_text(encoding="utf-8"))
    assert from_gen == from_file, "生成器行為表與現讀檔不一致"


def test_t01_c2_mutation_row_rc_fails() -> None:
    """mutation B：改行為表任一列 rc==N ⇒ C2 對 base oracle 轉紅。"""
    base = _base_commit()
    original = BEHAVIOR_SPEC.read_text(encoding="utf-8")
    rows = _behavior_rows_from_file(original)
    assert rows, "行為表空，無法 mutation"
    # 將第一列修後欄 rc 改成不可能的 999
    first = rows[0]
    mut_row = re.sub(r"rc==(\d+)", "rc==999", first, count=2)
    assert mut_row != first, "mutation 未改到 rc"
    try:
        BEHAVIOR_SPEC.write_text(original.replace(first, mut_row, 1), encoding="utf-8")
        proc = _run(["bash", str(GEN), "--behavior-only"])
        assert proc.returncode == 0, proc.stderr
        from_gen = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        show = _run(["git", "show", f"{base}:docs/GOV_DISPATCH_FLOW_FIX_SPEC.md"])
        from_base = _behavior_rows_from_file(show.stdout)
        assert from_gen != from_base, "改 rc 後 gen 應與 base oracle 不一致（C2 轉紅）"
    finally:
        BEHAVIOR_SPEC.write_text(original, encoding="utf-8")


def test_t01_c3_behavior_rows_nonempty() -> None:
    """T-0.1-C3：行為表現讀 > 0（擋空轉）。"""
    proc = _run(["bash", str(GEN), "--behavior-only"])
    assert proc.returncode == 0, proc.stderr
    n = sum(1 for ln in proc.stdout.splitlines() if ln.strip())
    assert n > 0


def test_t01_c3_mutation_pattern_without_leading_space_fails() -> None:
    """mutation ①：pattern 改回 ^\\|（無前導空白）⇒ 行為表現讀轉 0 ⇒ FAIL。"""
    src = GEN.read_text(encoding="utf-8")
    # 暫時換成無前導空白的 pattern
    bad = src.replace(
        r"/^[[:space:]]*\| `.*` \| (\*\*)?rc==/",
        r"/^\| `.*` \| (\*\*)?rc==/",
    )
    assert bad != src, "mutation 未改到 pattern"
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
        fh.write(bad)
        path = fh.name
    try:
        os.chmod(path, 0o755)
        proc = _run(["bash", path, "--behavior-only"])
        assert proc.returncode != 0, "無前導空白 pattern 應使行為表 0 行並 FAIL"
        assert "行為表現讀 0 行" in (proc.stderr + proc.stdout)
    finally:
        os.unlink(path)


# ── T-0.1-F1 fixture 逐名存在 ─────────────────────────────────────────


def _fixture_names_live() -> list[str]:
    proc = _run(["bash", str(GEN), "--list-fixtures"])
    assert proc.returncode == 0, proc.stderr
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def test_t01_f1_each_fixture_exists_by_name() -> None:
    """T-0.1-F1：SPEC 現讀清單逐名 test -e，缺一即 FAIL（非數量）。"""
    names = _fixture_names_live()
    assert names, "fixture 清單不得為空"
    missing = [n for n in names if not (FIXTURE_ROOT / n).exists()]
    assert not missing, f"缺 fixture: {missing}"


def test_t01_f1_fixture_floor_holds_live() -> None:
    """群集 A 正例：heading 正常時 --list-fixtures／--check-fixtures 皆 rc=0。"""
    listed = _run(["bash", str(GEN), "--list-fixtures"])
    assert listed.returncode == 0, listed.stderr + listed.stdout
    n = sum(1 for ln in listed.stdout.splitlines() if ln.strip())
    assert n > 0
    chk = _run(["bash", str(GEN), "--check-fixtures"])
    assert chk.returncode == 0, chk.stderr + chk.stdout


def test_t01_f1_mutation_heading_mismatch_fails() -> None:
    """mutation A（composer RECHECK）：改 SPEC 標題使 awk 不匹配 ⇒ 下界守衛 FAIL。

    path 錨點下界仍 ≥ fence 現算項數；heading 失配只剩 supplemental ⇒ n < floor ⇒ 非零。
    """
    original = SPEC.read_text(encoding="utf-8")
    # 標題「fixture 清單」→ 使 /fixture 清單/ 失配；path 錨點 fence 不動
    assert "fixture 清單" in original
    mutated = original.replace("fixture 清單", "fixture inventory", 1)
    assert mutated != original
    try:
        SPEC.write_text(mutated, encoding="utf-8")
        listed = _run(["bash", str(GEN), "--list-fixtures"])
        assert listed.returncode != 0, (
            "heading 失配時 --list-fixtures 應因下界守衛非零，"
            f"stdout={listed.stdout!r} stderr={listed.stderr!r}"
        )
        assert "低於現算下界" in (listed.stderr + listed.stdout) or (
            "path 錨點已失效" in (listed.stderr + listed.stdout)
        )
        chk = _run(["bash", str(GEN), "--check-fixtures"])
        assert chk.returncode != 0, "heading 失配時 --check-fixtures 亦應非零"
    finally:
        SPEC.write_text(original, encoding="utf-8")


# ── T-0.1-F2 動工前基準 ───────────────────────────────────────────────


def test_t01_f2_frozen_hashes_self_consistent() -> None:
    """T-0.1-F2：frozen_hashes 欄位完整 + baseline_dirty 不存在 + g7 可過。"""
    assert FROZEN.is_file() and FROZEN.stat().st_size > 0
    text = FROZEN.read_text(encoding="utf-8")
    n_base = len(re.findall(r"^base_commit: [0-9a-f]{40}$", text, re.M))
    n_scope = len(re.findall(r"^scope_manifest: [0-9a-f]{12}$", text, re.M))
    assert n_base == 1, text
    assert n_scope == 1, text
    assert not (REPO / "scripts" / "govb1_baseline_dirty.txt").exists()
    base = re.search(r"^base_commit: ([0-9a-f]{40})$", text, re.M)
    assert base
    cat = _run(["git", "cat-file", "-e", f"{base.group(1)}^{{commit}}"])
    assert cat.returncode == 0
    # g7 需本批已 commit；若尚未 commit 則 skip 由 post-commit 實跑補
    g7 = _run(["bash", str(GATE), "--only", "g7"])
    if g7.returncode != 0 and "UNSUPPORTED-DELIVERY-SHAPE" in (g7.stderr + g7.stdout):
        pytest.skip("本批尚未 commit；交付語義要求 commit 後 g7 才綠")
    assert g7.returncode == 0, g7.stderr + g7.stdout


# ── T-0.1-F3 commit-range G-7 ─────────────────────────────────────────


def test_t01_f3_print_plan_nonempty() -> None:
    """T-0.1-F3：--print-plan rc=0 且輸出非空。"""
    proc = _run(["bash", str(GATE), "--print-plan"])
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip(), "print-plan 不得為空"


def test_t01_f3_g7_when_committed() -> None:
    """T-0.1-F3：commit 後 --only g7 rc=0；主樹 dirty 數不被 oracle 汙染。"""
    before = _run(["bash", "-c", "git status --porcelain | wc -l"])
    assert before.returncode == 0
    n_before = int(before.stdout.strip())
    g7 = _run(["bash", str(GATE), "--only", "g7"])
    if g7.returncode != 0 and "UNSUPPORTED-DELIVERY-SHAPE" in (g7.stderr + g7.stdout):
        pytest.skip("本批尚未 commit")
    assert g7.returncode == 0, g7.stderr + g7.stdout
    after = _run(["bash", "-c", "git status --porcelain | wc -l"])
    n_after = int(after.stdout.strip())
    assert n_after == n_before, f"g7 汙染主樹 dirty: {n_before} → {n_after}"


# ── T-0.1-F4 G-2 consumer 定義域 ──────────────────────────────────────


def test_t01_f4_prose_literal_not_scanned() -> None:
    """T-0.1-F4：TODO 散文附加字面量分母 ⇒ g2 仍 rc=0（散文不掃）。"""
    original = TODO.read_text(encoding="utf-8")
    marker = "\n<!-- T01-F4-PROSE-INJECT: 18 份文件 -->\n"
    try:
        TODO.write_text(original + marker, encoding="utf-8")
        proc = _run(["bash", str(GATE), "--only", "g2"])
        assert proc.returncode == 0, proc.stderr + proc.stdout
    finally:
        TODO.write_text(original, encoding="utf-8")


def test_t01_f4_consumer_literal_blocked() -> None:
    """T-0.1-F4：final_gate 寫入字面量分母 ⇒ g2 rc≠0。"""
    original = GATE.read_text(encoding="utf-8")
    # 注入不破壞函式結構的註解列（仍會被 grep 掃到）
    inject = "\n# T01-F4-INJECT: 14 個 fixture\n"
    try:
        GATE.write_text(original + inject, encoding="utf-8")
        proc = _run(["bash", str(GATE), "--only", "g2"])
        assert proc.returncode != 0, "consumer 內字面量分母應使 g2 FAIL"
    finally:
        GATE.write_text(original, encoding="utf-8")


# ── T-0.1-F5 manifest 漂移 lint ───────────────────────────────────────


def _f5_shell() -> str:
    """F5 lint 可重跑片段（與 TODO 驗證欄同語義）。"""
    return r"""
set -u
: "${GOVB1_SCOPE_MANIFEST:=scripts/govb1_scope.manifest}"
_g7_policy() {
  awk '$1=="deny"{d[$2]=1} $1=="allow"{a[$2]=1}
       END{ for (p in a) if (!(p in d)) print p }' "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u
}
_g7_task_decl() {
  awk '
    /^- \*\*修改檔案\*\*/  { m=1 }
    /\*\*只讀\*\*/         { m=0 }
    /\*\*既有 caller\*\*/  { m=0 }
    /^#/                   { m=0 }
    m                      { print }
  ' docs/GOVB1_INPUT_QUALITY_TODO.md \
    | grep -oE '`(scripts|tests|templates|docs)/[A-Za-z0-9_./-]+`' | tr -d '`' \
    | grep -vxF -f <(awk '$1=="deny"{print $2}' "${GOVB1_SCOPE_MANIFEST}") \
    | LC_ALL=C sort -u
}
_g7_deny_conflict() {
  _m="${GOVB1_SCOPE_MANIFEST}"
  _dup="$(comm -12 <(awk '$1=="allow"{print $2}' "${_m}" | LC_ALL=C sort -u) \
                   <(awk '$1=="deny"{print $2}'  "${_m}" | LC_ALL=C sort -u))"
  [ -z "${_dup}" ] || { printf 'F5 FAIL: manifest 同一路徑既 allow 又 deny:\n%s\n' "${_dup}" >&2; return 1; }
}
_g7_deny_conflict \
  && diff <(_g7_policy | LC_ALL=C sort -u) <(_g7_task_decl | LC_ALL=C sort -u)
"""


def test_t01_f5_manifest_matches_task_decl() -> None:
    """T-0.1-F5：allow（deny 優先）集合 == 各 Task 修改∪新建（剔除 deny）。"""
    proc = _run(["bash", "-c", _f5_shell()])
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_t01_f5_mutation_extra_allow_fails() -> None:
    """mutation F5：manifest 增未出現於 Task 欄之 allow ⇒ lint 轉紅。"""
    original = MANIFEST.read_text(encoding="utf-8")
    # 不可改 frozen hash 所鎖之檔而不還原——本測試結束後還原
    try:
        MANIFEST.write_text(
            original + "\nallow scripts/not_in_any_task_column.sh\n",
            encoding="utf-8",
        )
        proc = _run(["bash", "-c", _f5_shell()])
        assert proc.returncode != 0, "多餘 allow 應使 F5 lint FAIL"
    finally:
        MANIFEST.write_text(original, encoding="utf-8")


# ── 方案 B：manifest `meta` 動詞（r5）──────────────────────────────────


def _rehash_scope_manifest() -> None:
    """重算 scope_manifest hash-lock；base_commit 不變。"""
    base = _base_commit()
    h = _run(
        ["bash", "-c", "shasum -a 256 scripts/govb1_scope.manifest | cut -c1-12"]
    )
    assert h.returncode == 0 and h.stdout.strip(), h.stderr
    FROZEN.write_text(
        f"base_commit: {base}\nscope_manifest: {h.stdout.strip()}\n",
        encoding="utf-8",
    )


# meta 精確凍結集合（與 _g7_policy expected-set 字面一致；合成 manifest 須附齊）
_META_FROZEN_LINES = (
    "meta HANDOFF.md\n"
    "meta CLAUDE.md\n"
    "meta handoffs/20260801-GOV-AMEND-BACKLOG.md\n"
    "meta 白話說明/\n"
    "meta scripts/govb1_task_tickets.tsv\n"
    "meta scripts/govb1_single_source_check.sh\n"
)
_META_FROZEN_SET = frozenset(
    ln[5:] for ln in _META_FROZEN_LINES.splitlines() if ln.startswith("meta ")
)


def _call_g7_policy() -> subprocess.CompletedProcess[str]:
    """呼叫 production `_g7_policy`（含 hash／未知動詞守衛）。"""
    return _run(
        [
            "bash",
            "-c",
            r"""
set -u
eval "$(sed -n '/^_g7_policy()/,/^}/p' scripts/govb1_final_gate.sh)"
_g7_policy
""",
        ]
    )


def _g7_covered_rc(path: str, decl: str) -> int:
    """production `_g7_covered`：$path 是否被 $decl 涵蓋 → rc 0/1。"""
    proc = _run(
        [
            "bash",
            "-c",
            r"""
set -u
eval "$(sed -n '/^_g7_covered()/,/^}/p' scripts/govb1_final_gate.sh)"
_g7_covered "$1" "$2"
""",
            "_",
            path,
            decl,
        ]
    )
    return proc.returncode


def test_meta_t1_paths_covered_by_g7_policy() -> None:
    """T1：`meta` 路徑被 `_g7_policy` 涵蓋；移除該列 ⇒ expected-set 非零。"""
    # 正例：六條 meta 皆在 decl（W′ 增 TSV + single_source_check 讀取端）
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl_lines = {ln for ln in proc.stdout.splitlines() if ln.strip()}
    for p in (
        "HANDOFF.md",
        "CLAUDE.md",
        "handoffs/20260801-GOV-AMEND-BACKLOG.md",
        "白話說明/",
        "scripts/govb1_task_tickets.tsv",
        "scripts/govb1_single_source_check.sh",
    ):
        assert p in decl_lines, f"meta 路徑應在 decl: {p}"
        assert _g7_covered_rc(p.rstrip("/"), "\n".join(sorted(decl_lines))) == 0 or (
            p.endswith("/") and _g7_covered_rc("白話說明/README.md", "\n".join(sorted(decl_lines))) == 0
        )

    # 反例（b2-r2 B3）：移除 HANDOFF.md 之 meta 列 ⇒ expected-set 拒收（非零）
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        mutated = "\n".join(
            ln
            for ln in orig_m.splitlines()
            if ln.strip() != "meta HANDOFF.md"
        ) + "\n"
        assert mutated != orig_m
        MANIFEST.write_text(mutated, encoding="utf-8")
        _rehash_scope_manifest()
        proc2 = _call_g7_policy()
        assert proc2.returncode != 0, "移除 meta 列應使 expected-set 非零"
        combined = proc2.stderr + proc2.stdout
        assert "expected-set" in combined, combined
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    # 還原後回綠
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_meta_t2_undeclared_path_still_fails_g7() -> None:
    """T2：偵測力不減——既不在 allow 也不在 meta 的路徑 ⇒ g7 差集仍 FAIL。

    正向：模擬 actual 含 `scripts/evil.sh` ⇒ extra 非空（≡ g7 FAIL）。
    反例對照（b2-r2）：同一路徑若寫入 `meta` ⇒ expected-set 拒收（不可旁路）。
    """
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = proc.stdout
    evil = "scripts/evil.sh"
    assert evil not in {ln.strip() for ln in decl.splitlines() if ln.strip()}
    assert _g7_covered_rc(evil, decl) != 0, "evil 不得被現行 decl 涵蓋"

    # 與 production `_g7` 同一差集語意：未涵蓋 ⇒ extra 非空 ⇒ 應 FAIL
    sim = _run(
        [
            "bash",
            "-c",
            r"""
set -u
eval "$(sed -n '/^_g7_policy()/,/^}/p' scripts/govb1_final_gate.sh)"
eval "$(sed -n '/^_g7_covered()/,/^}/p' scripts/govb1_final_gate.sh)"
decl="$(_g7_policy)" || exit 2
extra=""
while IFS= read -r p; do
  [ -n "${p}" ] || continue
  _g7_covered "${p}" "${decl}" || extra="${extra}${p}"$'\n'
done <<'EOF'
scripts/evil.sh
EOF
[ -n "${extra}" ] || { echo "T2 FAIL: evil 應使 extra 非空" >&2; exit 1; }
printf 'EXTRA:%s' "${extra}"
""",
        ]
    )
    assert sim.returncode == 0, sim.stderr + sim.stdout
    assert "scripts/evil.sh" in sim.stdout

    # 反例（B2）：把 evil 寫進 meta + rehash ⇒ expected-set 非零（不得旁路進 decl）
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        MANIFEST.write_text(orig_m + f"\nmeta {evil}\n", encoding="utf-8")
        _rehash_scope_manifest()
        sim2 = _run(
            [
                "bash",
                "-c",
                r"""
set -u
eval "$(sed -n '/^_g7_policy()/,/^}/p' scripts/govb1_final_gate.sh)"
_g7_policy
""",
            ]
        )
        assert sim2.returncode != 0, "任意 meta 旁路應使 expected-set 非零"
        assert "expected-set" in (sim2.stderr + sim2.stdout)
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_meta_t3_unknown_verb_fail_closed() -> None:
    """T3：未知動詞 ⇒ `_g7_policy` 非零；合法動詞集合下 rc=0。"""
    # 正例：現行 manifest 全綠
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout

    # 反例：allowx foo
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        MANIFEST.write_text(orig_m + "\nallowx foo\n", encoding="utf-8")
        _rehash_scope_manifest()
        bad = _call_g7_policy()
        assert bad.returncode != 0, "未知動詞應使 _g7_policy 非零"
        assert "未知動詞" in (bad.stderr + bad.stdout)
        # --only g7 亦應紅
        g7 = _run(["bash", str(GATE), "--only", "g7"])
        assert g7.returncode != 0, "未知動詞應使 g7 FAIL"
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")


def test_meta_t4_deny_wins_over_meta() -> None:
    """T4：同路徑同時 meta 與 deny ⇒ 不得出現在 decl；僅 meta 則在 decl。

    b2-r2：不得再以任意 probe 擴 meta（expected-set）；改以凍結集合內路徑驗 deny 優先。
    """
    frozen = "HANDOFF.md"
    # 僅 meta（現行）⇒ 在 decl
    only = _call_g7_policy()
    assert only.returncode == 0, only.stderr + only.stdout
    assert frozen in {ln.strip() for ln in only.stdout.splitlines()}

    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        # meta（凍結集合）+ deny 同路徑 ⇒ 不在 decl；policy 仍綠（meta 集合未變）
        MANIFEST.write_text(
            orig_m.rstrip("\n") + f"\ndeny {frozen}\n",
            encoding="utf-8",
        )
        _rehash_scope_manifest()
        both = _call_g7_policy()
        assert both.returncode == 0, both.stderr + both.stdout
        assert frozen not in {ln.strip() for ln in both.stdout.splitlines()}
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")


def test_meta_t5_f5_still_allow_only() -> None:
    """T5：`T-0.1-F5` 仍只比 allow（meta 不混入）；既有 F5 不斷言轉紅。"""
    # 正例：F5 與 production policy 並存——F5 只讀 allow，現行應 PASS
    f5 = _run(["bash", "-c", _f5_shell()])
    assert f5.returncode == 0, f5.stderr + f5.stdout

    # meta 在 production decl 中，但 F5 內嵌 _g7_policy 不含 meta
    prod = _call_g7_policy()
    assert prod.returncode == 0, prod.stderr + prod.stdout
    assert "HANDOFF.md" in prod.stdout
    f5_policy = _run(
        [
            "bash",
            "-c",
            r"""
set -u
: "${GOVB1_SCOPE_MANIFEST:=scripts/govb1_scope.manifest}"
awk '$1=="deny"{d[$2]=1} $1=="allow"{a[$2]=1}
     END{ for (p in a) if (!(p in d)) print p }' "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u
""",
        ]
    )
    assert f5_policy.returncode == 0
    assert "HANDOFF.md" not in f5_policy.stdout
    assert "白話說明/" not in f5_policy.stdout

    # 反例方向：多餘 allow 仍使 F5 轉紅（既有 mutation 契約）
    original = MANIFEST.read_text(encoding="utf-8")
    try:
        MANIFEST.write_text(
            original + "\nallow scripts/not_in_any_task_column.sh\n",
            encoding="utf-8",
        )
        proc = _run(["bash", "-c", _f5_shell()])
        assert proc.returncode != 0, "多餘 allow 應使 F5 lint FAIL"
    finally:
        MANIFEST.write_text(original, encoding="utf-8")


# ── CODEX-R4-P1-01：空白／雙引號路徑 NUL-safe（r6）────────────────────


def _policy_decl_from_manifest_text(manifest_body: str) -> set[str]:
    """以 production `_g7_policy` 解析任意 manifest 文字 → decl 集合。

    透過暫存檔 + 暫時重寫 frozen hash-lock；呼叫端負責還原主樹。
    合成 body 若未含 meta，自動附齊精確凍結 6 項（expected-set 硬性要求）。
    """
    body = manifest_body if manifest_body.endswith("\n") else manifest_body + "\n"
    # 已有 meta 列者（例如以 production 為底）不重複附加
    if not any(ln.startswith("meta ") for ln in body.splitlines()):
        body = body + _META_FROZEN_LINES
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        MANIFEST.write_text(body, encoding="utf-8")
        _rehash_scope_manifest()
        proc = _call_g7_policy()
        assert proc.returncode == 0, proc.stderr + proc.stdout
        return {ln for ln in proc.stdout.splitlines() if ln.strip()}
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")


def _legacy_awk_decl(manifest_body: str) -> set[str]:
    """舊版 `$2` 截斷 parser（r6 修法前）— 供反例方向證假紅根因。"""
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".manifest", delete=False
    ) as fh:
        fh.write(manifest_body)
        path = fh.name
    try:
        proc = _run(
            [
                "bash",
                "-c",
                r"""
set -u
awk '$1=="deny"{d[$2]=1}
     $1=="allow"||$1=="meta"{a[$2]=1}
     END{ for (p in a) if (!(p in d)) print p }' "$1" | LC_ALL=C sort -u
""",
                "_",
                path,
            ]
        )
        assert proc.returncode == 0, proc.stderr
        return {ln for ln in proc.stdout.splitlines() if ln.strip()}
    finally:
        Path(path).unlink(missing_ok=True)


def test_r6_u1_space_path_declared_in_policy() -> None:
    """U1：已宣告含空白路徑 ⇒ production policy 完整輸出；舊 `$2` 截斷。"""
    body = (
        "allow scripts/foo.sh\n"
        "allow scripts/space probe.sh\n"
    )
    decl = _policy_decl_from_manifest_text(body)
    assert "scripts/space probe.sh" in decl
    assert "scripts/space" not in decl
    # 反例：舊 parser 截斷 ⇒ 假路徑在 decl、真路徑不在
    legacy = _legacy_awk_decl(body)
    assert "scripts/space" in legacy
    assert "scripts/space probe.sh" not in legacy


def test_r6_u2_quote_path_declared_in_policy() -> None:
    """U2：已宣告含雙引號路徑 ⇒ production policy 完整輸出。"""
    body = 'allow scripts/foo.sh\nallow scripts/quote"probe.sh\n'
    decl = _policy_decl_from_manifest_text(body)
    assert 'scripts/quote"probe.sh' in decl
    legacy = _legacy_awk_decl(body)
    # `$2` 對無空白的 quote 路徑通常仍完整（截斷問題在空白）；仍須在 production 保留
    assert 'scripts/quote"probe.sh' in legacy


def test_r6_u3_cjk_path_still_in_policy() -> None:
    """U3：CJK meta 路徑回歸——仍完整出現於 decl。"""
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = {ln for ln in proc.stdout.splitlines() if ln.strip()}
    assert "白話說明/" in decl
    assert _g7_covered_rc("白話說明/README.md", "\n".join(sorted(decl))) == 0


def test_r6_u4_undeclared_space_path_not_covered() -> None:
    """U4：未宣告含空白路徑不得被涵蓋（修假紅不得變假綠）。"""
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = proc.stdout
    evil = "scripts/evil probe.sh"
    assert evil not in {ln.strip() for ln in decl.splitlines() if ln.strip()}
    assert _g7_covered_rc(evil, decl) != 0
    # 對照：寫入 allow 後 rehash ⇒ covered
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        MANIFEST.write_text(orig_m + f"\nallow {evil}\n", encoding="utf-8")
        _rehash_scope_manifest()
        proc2 = _call_g7_policy()
        assert proc2.returncode == 0, proc2.stderr + proc2.stdout
        assert evil in {ln.strip() for ln in proc2.stdout.splitlines()}
        assert _g7_covered_rc(evil, proc2.stdout) == 0
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")


def test_r6_u1u2u4_g7_worktree_space_quote_paths() -> None:
    """U1/U2/U4 整合：臨時 worktree 真實 commit 空白／引號路徑；主樹無殘留。

    - 已宣告 space／quote ⇒ --only g7 rc=0
    - 未宣告 evil space ⇒ --only g7 rc≠0
    """
    import shutil
    import uuid

    wt = Path(tempfile.mkdtemp(prefix="govb1-r6-wt-", dir="/tmp"))
    branch = f"govb1-r6-probe-{uuid.uuid4().hex[:8]}"
    before_porcelain = _run(["bash", "-c", "git status --porcelain | wc -l"])
    n_before = int(before_porcelain.stdout.strip())
    try:
        add = _run(["git", "worktree", "add", "-b", branch, str(wt), "HEAD"])
        assert add.returncode == 0, add.stderr + add.stdout

        def wt_run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                args,
                cwd=str(wt),
                capture_output=True,
                text=True,
                check=False,
                **kw,  # type: ignore[arg-type]
            )

        # worktree 自 HEAD 長出；覆寫為工作區現行 gate（含本輪 NUL-safe 修法）
        shutil.copy2(GATE, wt / "scripts" / "govb1_final_gate.sh")

        # 三條 probe 檔（含空白、雙引號、evil 空白）
        space_rel = "scripts/space probe.sh"
        quote_rel = 'scripts/quote"probe.sh'
        evil_rel = "scripts/evil probe.sh"
        for rel, body in (
            (space_rel, "#!/bin/sh\necho space\n"),
            (quote_rel, "#!/bin/sh\necho quote\n"),
            (evil_rel, "#!/bin/sh\necho evil\n"),
        ):
            p = wt / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")

        man = (wt / "scripts" / "govb1_scope.manifest").read_text(encoding="utf-8")
        # 只宣告 space + quote；evil 未宣告
        man2 = man + f"\nallow {space_rel}\nallow {quote_rel}\n"
        (wt / "scripts" / "govb1_scope.manifest").write_text(man2, encoding="utf-8")
        h = wt_run(
            ["bash", "-c", "shasum -a 256 scripts/govb1_scope.manifest | cut -c1-12"]
        )
        assert h.returncode == 0 and h.stdout.strip(), h.stderr
        base = _base_commit()
        (wt / "scripts" / "govb1_frozen_hashes.txt").write_text(
            f"base_commit: {base}\nscope_manifest: {h.stdout.strip()}\n",
            encoding="utf-8",
        )

        # commit 1：已宣告之 space + quote（+ manifest/hash + 覆寫之 gate）
        # 註：gate 覆寫僅供本 worktree 執行；若 uncommitted 則交付守衛可能擋——
        # 故將 gate 一併 commit 進 probe 分支（拋棄用，不進 main）。
        add1 = wt_run(
            [
                "git",
                "add",
                "--",
                space_rel,
                quote_rel,
                "scripts/govb1_scope.manifest",
                "scripts/govb1_frozen_hashes.txt",
                "scripts/govb1_final_gate.sh",
            ]
        )
        assert add1.returncode == 0, add1.stderr
        c1 = wt_run(
            ["git", "commit", "-m", "test: r6 probe declared space+quote paths"]
        )
        assert c1.returncode == 0, c1.stderr + c1.stdout

        g7_ok = wt_run(["bash", "scripts/govb1_final_gate.sh", "--only", "g7"])
        assert g7_ok.returncode == 0, (
            f"U1/U2 已宣告 space/quote 應 g7 綠\n"
            f"stdout={g7_ok.stdout}\nstderr={g7_ok.stderr}"
        )

        # commit 2：未宣告 evil space ⇒ 須紅
        add2 = wt_run(["git", "add", "--", evil_rel])
        assert add2.returncode == 0, add2.stderr
        c2 = wt_run(["git", "commit", "-m", "test: r6 probe undeclared evil space"])
        assert c2.returncode == 0, c2.stderr + c2.stdout

        g7_bad = wt_run(["bash", "scripts/govb1_final_gate.sh", "--only", "g7"])
        assert g7_bad.returncode != 0, "U4 未宣告 evil space 應 g7 紅"
        combined = g7_bad.stderr + g7_bad.stdout
        assert "evil probe.sh" in combined or "未宣告" in combined, combined
    finally:
        # 拆除 worktree + 分支；主樹不得殘留 probe
        _run(["git", "worktree", "remove", "-f", str(wt)])
        _run(["git", "branch", "-D", branch])
        shutil.rmtree(wt, ignore_errors=True)
        after = _run(["bash", "-c", "git status --porcelain | wc -l"])
        n_after = int(after.stdout.strip())
        assert n_after == n_before, f"worktree 汙染主樹 dirty: {n_before}→{n_after}"
        # 主樹不得出現 probe 檔
        for rel in (
            "scripts/space probe.sh",
            'scripts/quote"probe.sh',
            "scripts/evil probe.sh",
        ):
            assert not (REPO / rel).exists(), f"主樹殘留 probe: {rel}"


# ── CODEX-R5-P1-01：manifest grammar fail-closed（r7）──────────────────
# 有界解：不支援前導/尾端空白與控制字元路徑 ⇒ 顯式拒絕（非靜默誤判）。
# 不得「支援」那些形態；合法 34 條 decl 須逐字不變。


def _r7_baseline_decl() -> list[str]:
    """修法前／後皆應不變之 34 條 decl（現跑 production policy）。"""
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _r7_mutate_manifest_line(extra_line: str) -> tuple[str, str]:
    """暫加一列並 rehash；回傳 (orig_m, orig_f)。呼叫端必須 finally 還原。"""
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    body = orig_m if orig_m.endswith("\n") else orig_m + "\n"
    MANIFEST.write_text(body + extra_line + ("\n" if not extra_line.endswith("\n") else ""), encoding="utf-8")
    _rehash_scope_manifest()
    return orig_m, orig_f


def test_r7_v1_current_manifest_decl_34_stable() -> None:
    """V1：現行 manifest ⇒ policy rc=0 且 decl 恰 36 條、集合封閉。

    W′：meta 由 4→6（+TSV ＋ single_source 讀取端）⇒ decl 34→36。
    single_source 不在任何 Task 欄 ⇒ 禁 allow（F5），故 meta。
    反例方向：若 grammar 誤拒任一合法列 ⇒ rc≠0 或條數變動即 FAIL。
    """
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(decl) == 36, f"V1 期望 36 條 decl，得 {len(decl)}"
    # 與第二次現跑逐字相同（穩定；非快取）
    again = _r7_baseline_decl()
    assert decl == again
    # 六 meta + 30 allow（deny 一條不進 decl）
    for p in (
        "HANDOFF.md",
        "CLAUDE.md",
        "handoffs/20260801-GOV-AMEND-BACKLOG.md",
        "白話說明/",
        "scripts/govb1_task_tickets.tsv",
        "scripts/govb1_single_source_check.sh",
        "scripts/govb1_final_gate.sh",
        "scripts/govb1_scope.manifest",
    ):
        assert p in decl, f"V1 合法路徑須在 decl: {p}"
    # deny 路徑不得出現
    assert "scripts/govb1_baseline_dirty.txt" not in decl


def test_r7_v2_leading_whitespace_path_rejected() -> None:
    """V2：路徑前導空白 ⇒ policy 非零且訊息含 leading-whitespace；移除後回 rc=0。"""
    # 正例（反紅）：兩空白分隔 ≡ 恰好一 sep 後 raw 仍以空白起始
    orig_m, orig_f = _r7_mutate_manifest_line("allow  scripts/leading-space-probe.sh")
    try:
        bad = _call_g7_policy()
        assert bad.returncode != 0, "前導空白路徑應使 _g7_policy 非零"
        combined = bad.stderr + bad.stdout
        assert "leading-whitespace" in combined, combined
        assert "路徑形態不支援" in combined or "fail-closed" in combined, combined
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    # 反例方向：移除該列 ⇒ 回 rc=0
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout
    assert len([ln for ln in ok.stdout.splitlines() if ln.strip()]) == 36


def test_r7_v3_trailing_whitespace_path_rejected() -> None:
    """V3：路徑尾端空白 ⇒ policy 非零且訊息含 trailing-whitespace；移除後回 rc=0。"""
    orig_m, orig_f = _r7_mutate_manifest_line("allow scripts/trailing-space-probe.sh ")
    try:
        bad = _call_g7_policy()
        assert bad.returncode != 0, "尾端空白路徑應使 _g7_policy 非零"
        combined = bad.stderr + bad.stdout
        assert "trailing-whitespace" in combined, combined
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_r7_v4_control_char_path_rejected() -> None:
    """V4：路徑含控制字元（C0 除 tab）⇒ policy 非零且訊息含 control-char；移除後回 rc=0。"""
    # BEL (0x07) 嵌入路徑
    orig_m, orig_f = _r7_mutate_manifest_line("allow scripts/ctrl\x07probe.sh")
    try:
        bad = _call_g7_policy()
        assert bad.returncode != 0, "控制字元路徑應使 _g7_policy 非零"
        combined = bad.stderr + bad.stdout
        assert "control-char" in combined, combined
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_r7_v5_undeclared_space_quote_still_fails_g7() -> None:
    """V5：未宣告含空白／引號路徑進 base..HEAD ⇒ --only g7 仍 rc≠0（假綠回歸保護）。

    臨時 worktree 實 commit；主樹無 probe 殘留。
    """
    import shutil
    import uuid

    wt = Path(tempfile.mkdtemp(prefix="govb1-r7-wt-", dir="/tmp"))
    branch = f"govb1-r7-probe-{uuid.uuid4().hex[:8]}"
    before_porcelain = _run(["bash", "-c", "git status --porcelain | wc -l"])
    n_before = int(before_porcelain.stdout.strip())
    try:
        add = _run(["git", "worktree", "add", "-b", branch, str(wt), "HEAD"])
        assert add.returncode == 0, add.stderr + add.stdout

        def wt_run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                args,
                cwd=str(wt),
                capture_output=True,
                text=True,
                check=False,
                **kw,  # type: ignore[arg-type]
            )

        # 覆寫為工作區現行 gate（含 r7 grammar 守衛）
        shutil.copy2(GATE, wt / "scripts" / "govb1_final_gate.sh")

        evil_space = "scripts/r7 evil space.sh"
        evil_quote = 'scripts/r7evil"quote.sh'
        for rel, body in (
            (evil_space, "#!/bin/sh\necho r7-evil-space\n"),
            (evil_quote, "#!/bin/sh\necho r7-evil-quote\n"),
        ):
            p = wt / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")

        # 不宣告 evil；僅 commit gate 覆寫 + 兩個 evil 檔
        add1 = wt_run(
            [
                "git",
                "add",
                "--",
                evil_space,
                evil_quote,
                "scripts/govb1_final_gate.sh",
            ]
        )
        assert add1.returncode == 0, add1.stderr
        c1 = wt_run(["git", "commit", "-m", "test: r7 probe undeclared space+quote"])
        assert c1.returncode == 0, c1.stderr + c1.stdout

        g7_bad = wt_run(["bash", "scripts/govb1_final_gate.sh", "--only", "g7"])
        assert g7_bad.returncode != 0, (
            "V5 未宣告 space/quote 應 g7 紅（不得因 grammar 守衛假綠）\n"
            f"stdout={g7_bad.stdout}\nstderr={g7_bad.stderr}"
        )
        combined = g7_bad.stderr + g7_bad.stdout
        assert (
            "r7 evil space.sh" in combined
            or 'r7evil"quote.sh' in combined
            or "未宣告" in combined
        ), combined
    finally:
        _run(["git", "worktree", "remove", "-f", str(wt)])
        _run(["git", "branch", "-D", branch])
        shutil.rmtree(wt, ignore_errors=True)
        after = _run(["bash", "-c", "git status --porcelain | wc -l"])
        n_after = int(after.stdout.strip())
        assert n_after == n_before, f"worktree 汙染主樹 dirty: {n_before}→{n_after}"
        for rel in (
            "scripts/r7 evil space.sh",
            'scripts/r7evil"quote.sh',
        ):
            assert not (REPO / rel).exists(), f"主樹殘留 probe: {rel}"


def test_r7_v6_r6_and_meta_suite_still_importable() -> None:
    """V6 錨點：r6 u1–u4 與 meta t1–t5 函式仍存在（全綠由全套 pytest 承擔）。"""
    import inspect
    import sys

    mod = sys.modules[__name__]
    for name in (
        "test_r6_u1_space_path_declared_in_policy",
        "test_r6_u2_quote_path_declared_in_policy",
        "test_r6_u3_cjk_path_still_in_policy",
        "test_r6_u4_undeclared_space_path_not_covered",
        "test_meta_t1_paths_covered_by_g7_policy",
        "test_meta_t2_undeclared_path_still_fails_g7",
        "test_meta_t3_unknown_verb_fail_closed",
        "test_meta_t4_deny_wins_over_meta",
        "test_meta_t5_f5_still_allow_only",
        "test_t01_f5_manifest_matches_task_decl",
        "test_t01_f3_g7_when_committed",
        "test_t01_f3_print_plan_nonempty",
    ):
        assert hasattr(mod, name), f"V6 既有測試不得刪除: {name}"
        assert inspect.isfunction(getattr(mod, name))


# ── W′ 歸屬 TSV（批 2 前置；A1–A7 雙向）─────────────────────────────

SS = REPO / "scripts" / "govb1_single_source_check.sh"
TICKETS = REPO / "scripts" / "govb1_task_tickets.tsv"

_W_PRIME_TASKS = (
    "0.1",
    "1.1",
    "1.2",
    "1.3",
    "1.4",
    "1.5",
    "2.1",
    "2.2",
    "3.1",
    "3.2",
    "4.1",
    "4.2",
    "4.3",
)


def _ss(*extra: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(
        ["bash", str(SS), *extra],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
        env=e,
    )


def _todo_task_ids() -> list[str]:
    text = TODO.read_text(encoding="utf-8")
    found = re.findall(r"^### Task ([0-9]+\.[0-9]+)", text, re.M)
    return sorted(set(found))


def test_wprime_a1_all_thirteen_tasks_pass_task_mode() -> None:
    """A1 正：13 個 Task 之 --task 皆 rc=0。"""
    for t in _W_PRIME_TASKS:
        proc = _ss("--task", t)
        assert proc.returncode == 0, f"Task {t} 應 PASS:\n{proc.stderr}{proc.stdout}"
    assert set(_W_PRIME_TASKS) == set(_todo_task_ids())


def test_wprime_a1_counterexample_pending_ticket_fails() -> None:
    """A1 反：TSV 某列 ticket 改為「待確認」⇒ 該 Task 轉紅；還原後回綠。"""
    orig = TICKETS.read_text(encoding="utf-8")
    try:
        mutated = re.sub(
            r"^(2\t1\.1\t)—\t",
            r"\1待確認\t",
            orig,
            count=1,
            flags=re.M,
        )
        assert mutated != orig, "突變未生效"
        TICKETS.write_text(mutated, encoding="utf-8")
        bad = _ss("--task", "1.1")
        assert bad.returncode != 0, "待確認 應使 Task 1.1 轉紅"
        assert "待確認" in (bad.stderr + bad.stdout) or "未標註" in (bad.stderr + bad.stdout)
        assert _ss("--task", "1.2").returncode == 0
    finally:
        TICKETS.write_text(orig, encoding="utf-8")
    assert _ss("--task", "1.1").returncode == 0


def test_wprime_a2_missing_task_row_fails_full_mode() -> None:
    """A2：TSV 缺某 Task ⇒ 全表 rc≠0 且訊息指名；補回 ⇒ rc=0。"""
    orig = TICKETS.read_text(encoding="utf-8")
    try:
        lines = [ln for ln in orig.splitlines() if not re.match(r"^[0-9]+\t3\.2\t", ln)]
        mutated = "\n".join(lines) + "\n"
        assert mutated != orig
        TICKETS.write_text(mutated, encoding="utf-8")
        bad = _ss()
        assert bad.returncode != 0, "缺 Task 3.2 應使全表轉紅"
        assert "3.2" in (bad.stderr + bad.stdout)
    finally:
        TICKETS.write_text(orig, encoding="utf-8")
    assert _ss().returncode == 0


def test_wprime_a3_em_dash_ticket_is_pass() -> None:
    """A3 正：ticket 為 — ⇒ PASS。"""
    for t in ("0.1", "1.1", "4.1"):
        assert _ss("--task", t).returncode == 0, f"Task {t} (—) 應 PASS"


def test_wprime_a3_counterexample_empty_ticket_fails() -> None:
    """A3 反：ticket 改為空字串 ⇒ 轉紅；還原後回綠。"""
    orig = TICKETS.read_text(encoding="utf-8")
    try:
        mutated = re.sub(
            r"^(2\t1\.1\t)—\t",
            r"\1\t",
            orig,
            count=1,
            flags=re.M,
        )
        assert mutated != orig
        TICKETS.write_text(mutated, encoding="utf-8")
        bad = _ss("--task", "1.1")
        assert bad.returncode != 0, "空 ticket 應轉紅"
    finally:
        TICKETS.write_text(orig, encoding="utf-8")
    assert _ss("--task", "1.1").returncode == 0


def test_wprime_a4_no_longer_reads_section_01a() -> None:
    """A4：GOVB1_TODO 指向無 §0.1a 之暫存副本，--task 仍能運作。"""
    text = TODO.read_text(encoding="utf-8")
    stripped = re.sub(
        r"^### 0\.1a .*?(?=^### )",
        "",
        text,
        count=1,
        flags=re.M | re.S,
    )
    assert "### 0.1a " not in stripped
    assert "### 0.1b " in stripped
    with tempfile.TemporaryDirectory() as td:
        tmp_todo = Path(td) / "todo_no_01a.md"
        tmp_todo.write_text(stripped, encoding="utf-8")
        env = {"GOVB1_TODO": str(tmp_todo)}
        for t in ("1.1", "0.1", "4.2"):
            proc = _ss("--task", t, env=env)
            assert proc.returncode == 0, (
                f"無 §0.1a 時 Task {t} 仍應 PASS:\n{proc.stderr}{proc.stdout}"
            )


def test_wprime_a5_meta_tickets_in_decl_count_36() -> None:
    """A5 正：meta TSV（及 single_source 讀取端）在 decl；decl 恰 36 條。"""
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert "scripts/govb1_task_tickets.tsv" in decl
    assert "scripts/govb1_single_source_check.sh" in decl
    assert len(decl) == 36, f"期望 decl 36，得 {len(decl)}"


def test_wprime_a5_counterexample_remove_meta_uncovers_tsv() -> None:
    """A5 反／B3：移除 TSV meta 列 + rehash ⇒ expected-set 非零。"""
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        mutated = (
            "\n".join(
                ln
                for ln in orig_m.splitlines()
                if ln.strip() != "meta scripts/govb1_task_tickets.tsv"
            )
            + "\n"
        )
        assert mutated != orig_m
        MANIFEST.write_text(mutated, encoding="utf-8")
        _rehash_scope_manifest()
        proc = _call_g7_policy()
        assert proc.returncode != 0, "移除凍結 meta 應 expected-set 非零"
        assert "expected-set" in (proc.stderr + proc.stdout)
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_wprime_a6_undeclared_path_still_blocked() -> None:
    """A6／B5：未宣告路徑仍被擋；B2：寫入 meta 旁路 ⇒ expected-set 非零。"""
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = proc.stdout
    evil = "scripts/govb1_a6_evil_undeclared.sh"
    assert evil not in {ln.strip() for ln in decl.splitlines() if ln.strip()}
    assert _g7_covered_rc(evil, decl) != 0, "未宣告 evil 不得被涵蓋"

    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        MANIFEST.write_text(orig_m.rstrip("\n") + f"\nmeta {evil}\n", encoding="utf-8")
        _rehash_scope_manifest()
        proc2 = _call_g7_policy()
        assert proc2.returncode != 0, "任意 meta 旁路應 expected-set 非零"
        assert "expected-set" in (proc2.stderr + proc2.stdout)
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_b2r2_b4_meta_path_rename_rejected() -> None:
    """B4：將某 meta 路徑改字 + rehash ⇒ 非零；還原 ⇒ rc=0。"""
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        mutated = orig_m.replace(
            "meta scripts/govb1_task_tickets.tsv",
            "meta scripts/govb1_task_tickets_renamed.tsv",
            1,
        )
        assert mutated != orig_m
        MANIFEST.write_text(mutated, encoding="utf-8")
        _rehash_scope_manifest()
        bad = _call_g7_policy()
        assert bad.returncode != 0, "改字 meta 應 expected-set 非零"
        assert "expected-set" in (bad.stderr + bad.stdout)
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_b2r2_b6_gate_msg_points_to_tsv_not_01a() -> None:
    """B6：gate.sh 失敗訊息含 govb1_task_tickets.tsv，不含 §0.1a 字面。"""
    text = (REPO / "scripts" / "gate.sh").read_text(encoding="utf-8")
    # 全檔不得殘留 0.1a（歷史說明亦禁；本輪一次改齊）
    assert "0.1a" not in text, "gate.sh 仍含 0.1a 字面"
    assert "§0.1a" not in text
    # 失敗訊息指向 TSV
    assert "govb1_task_tickets.tsv" in text
    assert "歸屬" in text and "TSV" in text


def test_wprime_a7_existing_suite_still_present() -> None:
    """A7：既有 meta/r6/r7/f5/f3 測試函式仍在（全套 pytest 另驗通過）。"""
    import inspect
    import sys

    mod = sys.modules[__name__]
    for name in (
        "test_meta_t1_paths_covered_by_g7_policy",
        "test_meta_t2_undeclared_path_still_fails_g7",
        "test_meta_t3_unknown_verb_fail_closed",
        "test_meta_t4_deny_wins_over_meta",
        "test_meta_t5_f5_still_allow_only",
        "test_r6_u1_space_path_declared_in_policy",
        "test_r6_u2_quote_path_declared_in_policy",
        "test_r6_u3_cjk_path_still_in_policy",
        "test_r6_u4_undeclared_space_path_not_covered",
        "test_r7_v1_current_manifest_decl_34_stable",
        "test_r7_v5_undeclared_space_quote_still_fails_g7",
        "test_t01_f5_manifest_matches_task_decl",
        "test_t01_f3_g7_when_committed",
    ):
        assert hasattr(mod, name), f"A7 既有測試不得刪除: {name}"
        assert inspect.isfunction(getattr(mod, name))


# ── ASSERT 列 + CLI 契約 ──────────────────────────────────────────────


def test_gen_matrix_rc0() -> None:
    proc = _run(["bash", str(GEN)])
    assert proc.returncode == 0, proc.stderr


def test_gate_only_nosuchcheck_rc2() -> None:
    proc = _run(["bash", str(GATE), "--only", "nosuchcheck"])
    assert proc.returncode == 2


def test_gate_only_g5_g6_green() -> None:
    """_g5／_g6 非空守衛 + 與 base 雜湊一致。"""
    for name in ("g5", "g6"):
        proc = _run(["bash", str(GATE), "--only", name])
        assert proc.returncode == 0, f"{name}: {proc.stderr}{proc.stdout}"


def test_mutation_g5_g6_empty_extract_fails() -> None:
    """mutation ②：抽取器改成必然抽空 ⇒ 須 FAIL 而非 PASS。"""
    original = GATE.read_text(encoding="utf-8")
    # 把 _behavior_rows pattern 改壞（g5）；把 _g6_func 函式名打錯
    bad = original.replace(
        r"/^[[:space:]]*\| `.*` \| (\*\*)?rc==/",
        r"/^___NO_MATCH_BEHAVIOR___/",
    ).replace(
        r"/^_maybe_register_stamp_output\(\)/",
        r"/^_maybe_register_stamp_output_TYPO\(\)/",
    )
    assert bad != original
    try:
        GATE.write_text(bad, encoding="utf-8")
        g5 = _run(["bash", str(GATE), "--only", "g5"])
        g6 = _run(["bash", str(GATE), "--only", "g6"])
        assert g5.returncode != 0, "g5 空抽取應 FAIL"
        assert g6.returncode != 0, "g6 空抽取應 FAIL"
        assert "抽取結果為空" in (g5.stderr + g6.stderr + g5.stdout + g6.stdout)
    finally:
        GATE.write_text(original, encoding="utf-8")


def test_check_fixtures_rc0() -> None:
    proc = _run(["bash", str(GEN), "--check-fixtures"])
    assert proc.returncode == 0, proc.stderr


# ── 群集 C：_g7 窄守衛到期閘 ─────────────────────────────────────────


def _batch3_started(base: str) -> bool:
    """批3已開工 := base..HEAD 含 scripts/brief_conformance_check.sh。"""
    proc = _run(["git", "diff", "--name-only", f"{base}..HEAD"])
    assert proc.returncode == 0, proc.stderr
    return "scripts/brief_conformance_check.sh" in {
        ln.strip() for ln in proc.stdout.splitlines() if ln.strip()
    }


# 批 3 開工時，**放寬 `_g7` 與更新到期測試須配對**；
# **只改測試不改守衛＝假綠。** 到期不變式由 `_g7_narrow_expiry_holds` ＋ 模擬測試護住。
def _g7_narrow_expiry_holds(*, batch3_started: bool, narrow_guard: bool) -> bool:
    """斷言 NOT (批3已開工 AND 窄守衛仍在)。"""
    return not (batch3_started and narrow_guard)


# 批 3 開工時，**放寬 `_g7` 與更新到期測試須配對**；
# **只改測試不改守衛＝假綠。** 到期不變式由 `_g7_narrow_expiry_holds` ＋ 模擬測試護住。
def test_g7_narrow_guard_expiry_live_pass() -> None:
    """不變式：NOT (批3已開工 AND 窄守衛仍在)；三種狀態皆由本斷言＋模擬測試護住。"""
    base = _base_commit()
    started = _batch3_started(base)
    narrow = _is_narrow_g7_status_case(GATE.read_text(encoding="utf-8"))
    assert _g7_narrow_expiry_holds(batch3_started=started, narrow_guard=narrow)


def test_g7_narrow_guard_expiry_simulated_batch3_fails() -> None:
    """模擬批 3 已開工且窄守衛仍在 ⇒ 到期閘 FAIL（兩個方向皆須可證）。"""
    gate_src = GATE.read_text(encoding="utf-8")
    narrow = _is_narrow_g7_status_case(gate_src)
    assert narrow, "窄守衛偵測須為 True 才有模擬意義"
    # 模擬：diff 集合強行含批 3 標的檔
    assert not _g7_narrow_expiry_holds(batch3_started=True, narrow_guard=True)
    # 對照：批 3 開工但已放寬守衛（含 M）⇒ 到期閘應放行
    wide_src = gate_src.replace(
        r"\?\?|A\ |A?|A*)",
        r"\?\?|A\ |A?|A*| M|M |M?)",
        1,
    )
    # 若 replace 未命中（跳脫差異），改插 M 進 case 臂字串
    if wide_src == gate_src:
        wide_src = gate_src.replace(
            r"\?\?|A\ |A?|A*",
            r"\?\?|A\ |A?|A*| M|MM",
            1,
        )
    assert wide_src != gate_src, "寬守衛 mutation 未改到 case pattern"
    assert not _is_narrow_g7_status_case(wide_src), "含 M 後不得判為窄守衛"
    assert _g7_narrow_expiry_holds(batch3_started=True, narrow_guard=False)
