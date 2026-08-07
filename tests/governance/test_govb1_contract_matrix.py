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


def _docs_ref_count() -> int:
    proc = _run(
        [
            "bash",
            "-c",
            "grep -rln 'doc_format_precheck\\|completeness_check\\|cx_run' docs/*.md | wc -l",
        ]
    )
    assert proc.returncode == 0, proc.stderr
    return int(proc.stdout.strip())


def _behavior_rows_from_file(text: str) -> list[str]:
    """與 gen／final_gate 同一 pattern（含前導空白＋可選粗體 rc）。"""
    # Python 無 [[:space:]]；改用 \s
    pat = re.compile(r"^\s*\| `.*` \| (\*\*)?rc==", re.M)
    return [ln for ln in text.splitlines() if pat.match(ln)]


def _parse_expected_rc(row: str) -> str:
    """取行為表「修後必須」欄的 rc 值（第三個 rc==N）。"""
    # 列形態：| `heading` | rc==X | **rc==Y** | 理由 |
    m = re.findall(r"rc==(\d+)", row)
    assert m, f"列無 rc==N：{row!r}"
    # 修後欄為最後一個 rc（或倒數第二若理由無）；表固定：現行、修後
    return m[-1] if len(m) == 1 else m[1] if len(m) >= 2 else m[0]


# ── T-0.1-C* ──────────────────────────────────────────────────────────


def test_t01_c1_docs_count_matches_live_grep() -> None:
    """T-0.1-C1：矩陣 docs/ 列數 == 現跑 grep 列數（兩者同時現跑）。"""
    proc = _run(["bash", str(GEN)])
    assert proc.returncode == 0, proc.stderr
    matrix_n = sum(1 for ln in proc.stdout.splitlines() if ln.startswith("docs/"))
    ref_n = _docs_ref_count()
    assert matrix_n == ref_n, f"matrix={matrix_n} ref={ref_n}"


def test_t01_c2_behavior_expected_rc_matches_live() -> None:
    """T-0.1-C2：行為表每一列 expected_rc 與現讀值逐列相符。"""
    proc = _run(["bash", str(GEN), "--behavior-only"])
    assert proc.returncode == 0, proc.stderr
    from_gen = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    from_file = _behavior_rows_from_file(BEHAVIOR_SPEC.read_text(encoding="utf-8"))
    assert from_gen == from_file, "生成器行為表與現讀檔不一致"
    assert from_gen, "行為表不得為空"
    for row in from_gen:
        # 自身一致性：解析出的 expected 再對同一列 regex 覆核
        exp = _parse_expected_rc(row)
        assert re.search(rf"rc=={re.escape(exp)}", row), row


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
