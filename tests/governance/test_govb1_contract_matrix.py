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
