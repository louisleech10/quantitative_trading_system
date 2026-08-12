"""GOVB1 Task 0.1 — 契約矩陣／fixture／final gate 機械驗收。

對應 TODO 驗證欄 T-0.1-C1～C3、T-0.1-F1～F5。
禁寫死份數／列數（G-2）；矩陣內容不得硬編碼進測試。
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
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

# ── 票 B-49：永久 path grant（git 物件身分綁定）──────────────────────────
# 被授權路徑之 `<mode> <type> <oid>` 逐字寫死；任一位元組變動即失去豁免。
# 🔴 誠實邊界：本機制只防**意外與遺忘**，不防具寫入權者蓄意（SPEC §C-6／§C-9-7／§C-11）。
_B49_GRANT_IDENTITY: dict[str, str] = {
    "docs/GOVB1_INPUT_QUALITY_TODO.md": "100644 blob f5980dacc7e1689b4a546b6fb3555417ae0941ef",
    "tests/governance/test_result_state_format_failed.py": "100644 blob 1b01812c71df498150e9391e6b7bb7b3e98e374e",
    "tests/governance/test_rolegate_predispatch.py": "100644 blob 60b3efab0eb00605b32e3dc98d0ae1137c3bb0ec",
    "tests/governance/test_stamp_taskid_inject.py": "100644 blob 62e48627323af6d58f8257d1c3eb8976528498cd",
}
_B49_HARNESS_GRANT = frozenset(_B49_GRANT_IDENTITY)


def _b49_object_identity(path: str) -> str | None:
    """`git ls-tree HEAD -- <path>` 之 `<mode> <type> <oid>`；取不到一律 None（fail-closed）。"""
    p = _run(["git", "ls-tree", "HEAD", "--", path])
    if p.returncode != 0:
        return None
    line = p.stdout.strip()
    if not line:
        return None
    meta = line.split("\t", 1)[0].split()
    if len(meta) != 3:
        return None
    return " ".join(meta)


def _b49_worktree_shape_ok(fp: Path, want_mode: str) -> bool:
    """工作樹**形狀**是否與授權 mode 相符：regular file、非 symlink、exec bit 一致。

    〔`CODEX-R2-P1-02`〕原本只比對 grant 常數字串裡的 mode，**沒有看工作樹真實 mode**
    ⇒ `chmod +x` 一個授權檔，身分三元組（來自 `ls-tree HEAD`）不變、位元組不變，
    豁免照樣成立。SPEC 明定 `100644→100755` 須拒，故改為**兩邊都比**。
    獨立成純函式（吃 path，不吃全域），mutation 才能用真實 `chmod`／symlink／gitlink
    去打**同一個**判定，而不是另寫一份 assert 自證。
    """
    if want_mode not in ("100644", "100755"):
        return False  # gitlink(160000)／symlink(120000)／未知 ⇒ fail-closed
    try:
        st = fp.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        return False
    if (fp / ".git").exists():  # gitlink/submodule 目錄形狀
        return False
    return bool(st.st_mode & 0o111) == (want_mode == "100755")


def _b49_worktree_bytes_match(path: str) -> bool:
    """授權 blob 與工作樹**逐位元組**比對；不經 index ⇒ skip-worktree 打不敗。"""
    want = _B49_GRANT_IDENTITY.get(path)
    if not want:
        return False
    parts = want.split()
    if len(parts) != 3 or parts[1] != "blob":
        return False
    fp = REPO / path
    if not _b49_worktree_shape_ok(fp, parts[0]):
        return False
    if not fp.is_file():
        return False
    blob = subprocess.run(
        ["git", "cat-file", "blob", parts[2]],
        cwd=str(REPO),
        capture_output=True,
        check=False,
    )
    if blob.returncode != 0:
        return False
    return blob.stdout == fp.read_bytes()


def _b49_granted(path: str) -> bool:
    """身分三元組相符 **且** 工作樹位元組相符，才算被授權。"""
    want = _B49_GRANT_IDENTITY.get(path)
    if not want:
        return False
    return _b49_object_identity(path) == want and _b49_worktree_bytes_match(path)


def _rename_old_names(rng: str) -> set[str]:
    """`--name-only` **隱去 rename/copy 舊名** ⇒ 改名即可把受保護檔洗出保護範圍。

    〔`CODEX-CONSULT-R1-P0-02`〕本函式以 `--name-status -M -C` 補回舊名，供三道守衛
    聯集進 `names`。**原 `--name-only` 判定逐字保留**（TODO §0-3），本函式只做加法。
    取不到一律 fail-closed 拋錯，不得靜默回空集合（那等於改名就放行）。
    """
    p = _run(["git", "diff", "--name-status", "-M", "-C", rng])
    if p.returncode != 0:
        raise AssertionError(f"rename 偵測失敗（fail-closed）：{rng}: {p.stderr}")
    out: set[str] = set()
    for ln in p.stdout.splitlines():
        cols = ln.rstrip("\n").split("\t")
        if len(cols) >= 3 and cols[0][:1] in ("R", "C"):
            out.add(cols[1].strip())
    return out

BEHAVIOR_SPEC = REPO / "docs" / "GOV_DISPATCH_FLOW_FIX_SPEC.md"
FIXTURE_ROOT = REPO / "tests" / "governance" / "fixtures" / "govb1"


def _run(args: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    kw.setdefault("cwd", str(REPO))
    return subprocess.run(
        args,
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


# 凍結檔封閉 key 集合〔CODEX-R2-P1-03〕：禁重複／未知／跳號／非法值
#
# 〔20260808-GOVB1-B4-REVIEW-R1 · CODEX-R1-P1-03 NEW-CLASS〕
# 初版把封閉集寫死為「恰四 key」⇒ B5 開工需要 b5_start 時會**第五次撞同一個死鎖**
# （parser 拒新錨點 ⇒ 錨點寫不進去 ⇒ 上一窗的 waiver 收不了口）。
# 修法＝把封閉集改成**封閉但可導出**的批次錨點列舉 b3_start…b10_start
# （對應 GOVB1 第 1 批之 B3–B10）。仍是封閉集：b11_start／third: 一律拒。
# 這樣 B5–B10 只需「寫錨點＋收上一窗上界」，**不必再改 parser**。
_FROZEN_ANCHOR_KEYS = tuple(f"b{n}_start" for n in range(3, 11))  # b3_start … b10_start
_FROZEN_REQUIRED_KEYS = frozenset({"base_commit", "scope_manifest", "b3_start"})
_FROZEN_OPTIONAL_KEYS = frozenset(_FROZEN_ANCHOR_KEYS) - {"b3_start"}
_FROZEN_CLOSED_KEYS = _FROZEN_REQUIRED_KEYS | _FROZEN_OPTIONAL_KEYS
# 40-hex commit 值之 key（其餘＝scope_manifest 為 12-hex 摘要）
_FROZEN_SHA40_KEYS = frozenset({"base_commit"}) | frozenset(_FROZEN_ANCHOR_KEYS)
# regex **由封閉集導出**，杜絕「集合改了但 regex 沒改」之漂移
_FROZEN_LINE_RE = re.compile(
    r"^(" + "|".join(sorted(_FROZEN_CLOSED_KEYS)) + r"): (.+)$"
)


def _parse_frozen_hashes(text: str, *, require_b3_start: bool = True) -> dict[str, str]:
    """解析 govb1_frozen_hashes.txt：封閉 key 集合，各 key 至多一行。

    重複 key／未知 key（third:／b11_start: 等）／非法值 ⇒ AssertionError（測試轉紅）。
    require_b3_start=True（HEAD／工作樹）：三必備 key 全齊；b4_start… 可有可無。
    require_b3_start=False（歷史錨點樹）：base+scope 必備，b3_start 可缺。
    錨鏈 fail-closed：批次錨點須**自 b3_start 起連續無跳號**
    （例：有 b5_start 卻無 b4_start ⇒ 拒）。
    """
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    seen: dict[str, str] = {}
    for ln in lines:
        m = _FROZEN_LINE_RE.match(ln)
        assert m, f"frozen_hashes 未知/非法行（closed key set 拒額外 key）: {ln!r}"
        key, val = m.group(1), m.group(2)
        assert key not in seen, f"frozen_hashes 重複 key: {key}"
        if key in _FROZEN_SHA40_KEYS:
            assert re.fullmatch(r"[0-9a-f]{40}", val), (
                f"frozen_hashes {key} 須為 40 hex，got {val!r}"
            )
        else:
            assert re.fullmatch(r"[0-9a-f]{12}", val), (
                f"frozen_hashes scope_manifest 須為 12 hex，got {val!r}"
            )
        seen[key] = val
    assert "base_commit" in seen and "scope_manifest" in seen, (
        f"frozen_hashes 缺 base_commit／scope_manifest: {set(seen)}"
    )
    assert set(seen) <= _FROZEN_CLOSED_KEYS
    # 錨鏈連續性（取代「b4 無 b3」單例檢查，並涵蓋 b5…b10 之跳號）
    present_anchors = [k for k in _FROZEN_ANCHOR_KEYS if k in seen]
    assert present_anchors == list(_FROZEN_ANCHOR_KEYS[: len(present_anchors)]), (
        f"frozen_hashes 錨鏈須自 b3_start 起連續無跳號（fail-closed），got {present_anchors}"
    )
    if require_b3_start:
        assert _FROZEN_REQUIRED_KEYS <= set(seen), (
            f"frozen_hashes 須含三必備 key（closed），got {set(seen)}:\n{text}"
        )
    # 〔COMPOSER-R1-P2-01 SAME-CLASS-VARIANT〕原有之
    # `assert len(lines) == len(seen)` 已刪：迴圈內每行非「regex 不命中而轉紅」
    # 即「重複 key 而轉紅」即「恰新增一唯一 key」⇒ 該式**恆真**，
    # mutation 無法使其獨立失敗，屬票 B-43 同型之假綠錯覺。
    return seen


def _base_commit() -> str:
    text = FROZEN.read_text(encoding="utf-8")
    return _parse_frozen_hashes(text)["base_commit"]


def _b3_start() -> str:
    """主委錨點 b3_start（只讀；實作端不得寫入 govb1_frozen_hashes.txt）。

    封閉格式：恰好一行 b3_start，禁重複／額外 key〔CODEX-R2-P1-03〕。
    """
    text = FROZEN.read_text(encoding="utf-8")
    return _parse_frozen_hashes(text)["b3_start"]


def _b4_start() -> str | None:
    """主委錨點 b4_start（只讀；實作端不得寫入 govb1_frozen_hashes.txt）。

    缺席 ⇒ None（B4 尚未開工；此時 B3 waiver 仍以開放區間 b3_start..HEAD 全程看守，
    **無保護真空**）。存在 ⇒ B3 waiver 上界收斂為 b4_start，b4_start..HEAD 改由
    test_waiver_b4_range_does_not_touch_forbidden 接手看守。
    〔20260808-GOVB1-B4-STAMP-R2 三家 APPROVED〕
    """
    text = FROZEN.read_text(encoding="utf-8")
    return _parse_frozen_hashes(text).get("b4_start")


def _b5_start() -> str | None:
    """主委錨點 `b5_start`（只讀）。存在 ⇒ B4 窗上界收斂為 `b5_start`，
    `b5_start..HEAD` 改由 `test_waiver_b5_range_does_not_touch_forbidden` 接手。"""
    text = FROZEN.read_text(encoding="utf-8")
    return _parse_frozen_hashes(text).get("b5_start")


def _assert_anchor_chain_sane() -> None:
    """錨鏈健全性：base_commit → b3_start → b4_start → … 皆合法且祖先序正確、且為 HEAD 祖先。

    〔20260808-GOVB1-B4-REVIEW-R1 · CODEX-R1-P1-02 NEW-CLASS〕
    原本僅 B3 waiver 內聯此檢查，**B4 waiver 本體未做** ⇒ 錨點指向非祖先 commit 時，
    B4-only 與耦合測皆仍放行（codex 造 `6e35a1f8d643` 實證）。抽為共用，兩窗各自呼叫。
    """
    parsed = _parse_frozen_hashes(FROZEN.read_text(encoding="utf-8"))
    prev, prev_name = parsed["base_commit"], "base_commit"
    rp0 = _run(["git", "rev-parse", "--verify", f"{prev}^{{commit}}"])
    assert rp0.returncode == 0, f"base_commit 非合法 commit: {prev}\n{rp0.stderr}"
    for name in _FROZEN_ANCHOR_KEYS:
        cur = parsed.get(name)
        if cur is None:
            break  # 錨鏈連續性已由 parser 保證，故首個缺席即結尾
        rp = _run(["git", "rev-parse", "--verify", f"{cur}^{{commit}}"])
        assert rp.returncode == 0, f"{name} 非合法 commit: {cur}\n{rp.stderr}"
        anc = _run(["git", "merge-base", "--is-ancestor", prev, cur])
        assert anc.returncode == 0, f"{prev_name} 須為 {name} 之祖先（錨鏈順序）"
        anc_h = _run(["git", "merge-base", "--is-ancestor", cur, "HEAD"])
        assert anc_h.returncode == 0, f"{name} 須為 HEAD 之祖先"
        prev, prev_name = cur, name


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
    parsed = _parse_frozen_hashes(text)
    assert not (REPO / "scripts" / "govb1_baseline_dirty.txt").exists()
    cat = _run(["git", "cat-file", "-e", f"{parsed['base_commit']}^{{commit}}"])
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
    """重算 scope_manifest hash-lock；**其餘 key 逐字保留**。

    🔴 原版只寫回 `base_commit` ＋ `scope_manifest` 兩行，會**抹掉批次錨點**
    （`b3_start`／`b4_start`…）。§0 把封閉集擴為 `b3..b10` 之後，該兩行格式
    已無法通過 `_parse_frozen_hashes(require_b3_start=True)` ⇒ 是主委 §0 埋下的地雷
    （13 個呼叫點皆靠 `finally` 還原才沒炸）。改為**只替換 `scope_manifest` 那一行**。
    """
    h = _run(
        ["bash", "-c", "shasum -a 256 scripts/govb1_scope.manifest | cut -c1-12"]
    )
    assert h.returncode == 0 and h.stdout.strip(), h.stderr
    new_hash = h.stdout.strip()
    out = []
    for ln in FROZEN.read_text(encoding="utf-8").splitlines():
        out.append(
            f"scope_manifest: {new_hash}" if ln.startswith("scope_manifest: ") else ln
        )
    FROZEN.write_text("\n".join(out) + "\n", encoding="utf-8")


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
    assert len(decl) == 50, f"V1 期望 50 條 decl，得 {len(decl)}"
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
    assert len([ln for ln in ok.stdout.splitlines() if ln.strip()]) == 50


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
    assert len(decl) == 50, f"期望 decl 50，得 {len(decl)}"


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


def test_b2r3_c1_current_manifest_meta_count_6() -> None:
    """C1：現行 manifest ⇒ `_g7_policy` rc=0；meta 列數 6；decl 36。"""
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(decl) == 50, f"decl 應恰 50，got {len(decl)}"
    meta_n = sum(
        1
        for ln in MANIFEST.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("meta ")
    )
    assert meta_n == 6, f"meta 列數應恰 6，got {meta_n}"


def test_b2r3_c2_duplicate_meta_rejected() -> None:
    """C2：重複 meta HANDOFF.md（列數 7）+ rehash ⇒ rc≠0，訊息指出重複路徑；移除 ⇒ rc=0。"""
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    try:
        MANIFEST.write_text(
            orig_m.rstrip("\n") + "\nmeta HANDOFF.md\n",
            encoding="utf-8",
        )
        _rehash_scope_manifest()
        bad = _call_g7_policy()
        assert bad.returncode != 0, "重複 meta 列應非零"
        combined = bad.stderr + bad.stdout
        assert "HANDOFF.md" in combined, combined
        assert "重複" in combined or "duplicate" in combined.lower(), combined
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_b2r3_c3_meta_order_independent() -> None:
    """C3：順序反轉 6 列 + rehash ⇒ rc=0（集合語義，不得拒絕）。"""
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    meta_lines = [
        ln for ln in orig_m.splitlines() if ln.strip().startswith("meta ")
    ]
    assert len(meta_lines) == 6
    reversed_meta = list(reversed(meta_lines))
    assert reversed_meta != meta_lines
    try:
        non_meta = [
            ln for ln in orig_m.splitlines() if not ln.strip().startswith("meta ")
        ]
        # 保留檔頭註解與 allow/deny；meta 區塊改為反序
        rebuilt = "\n".join(non_meta).rstrip("\n") + "\n" + "\n".join(reversed_meta) + "\n"
        MANIFEST.write_text(rebuilt, encoding="utf-8")
        _rehash_scope_manifest()
        ok = _call_g7_policy()
        assert ok.returncode == 0, (
            "順序反轉 6 列應 rc=0（集合語義）\n" + ok.stderr + ok.stdout
        )
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok2 = _call_g7_policy()
    assert ok2.returncode == 0, ok2.stderr + ok2.stdout


def test_b2r3_c4_meta_deviations_still_rejected() -> None:
    """C4：多一項／少一項／改一字／大小寫 ⇒ 各 rc≠0；還原 ⇒ rc=0。"""
    orig_m = MANIFEST.read_text(encoding="utf-8")
    orig_f = FROZEN.read_text(encoding="utf-8")
    cases: list[tuple[str, str]] = [
        ("extra", orig_m.rstrip("\n") + "\nmeta scripts/govb1_extra_probe.sh\n"),
        (
            "missing",
            "\n".join(
                ln
                for ln in orig_m.splitlines()
                if ln.strip() != "meta CLAUDE.md"
            )
            + "\n",
        ),
        (
            "typo",
            orig_m.replace("meta HANDOFF.md", "meta HANDOFF.MD", 1),
        ),
        (
            "case",
            orig_m.replace("meta CLAUDE.md", "meta claude.md", 1),
        ),
    ]
    try:
        for name, mutated in cases:
            assert mutated != orig_m, name
            MANIFEST.write_text(mutated, encoding="utf-8")
            _rehash_scope_manifest()
            bad = _call_g7_policy()
            assert bad.returncode != 0, f"{name} 應 expected-set 非零"
            combined = bad.stderr + bad.stdout
            # 多一項也可能走 expected-set；重複路徑訊息另案
            assert (
                "expected-set" in combined
                or "重複" in combined
            ), f"{name}: {combined}"
            MANIFEST.write_text(orig_m, encoding="utf-8")
            FROZEN.write_text(orig_f, encoding="utf-8")
    finally:
        MANIFEST.write_text(orig_m, encoding="utf-8")
        FROZEN.write_text(orig_f, encoding="utf-8")
    ok = _call_g7_policy()
    assert ok.returncode == 0, ok.stderr + ok.stdout


def test_b2r3_c5_undeclared_path_still_blocked() -> None:
    """C5：未宣告路徑仍被擋（假綠回歸保護）。"""
    proc = _call_g7_policy()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    decl = proc.stdout
    evil = "scripts/govb1_b2r3_c5_evil_undeclared.sh"
    assert evil not in {ln.strip() for ln in decl.splitlines() if ln.strip()}
    assert _g7_covered_rc(evil, decl) != 0, "未宣告 evil 不得被涵蓋"


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


# 批 3 開工 proxy 檔名（literal；須與凍結 TODO Task 1.2／1.4「新建」欄逐字相符——anti-drift）
_BATCH3_PROXY_PATHS = (
    "tests/governance/test_govb1_brief_id_pattern.py",
    "tests/governance/test_govb1_factverified.py",
)


def _batch3_started(base: str, *, cwd: Path | None = None, head: str = "HEAD") -> bool:
    """批3已開工 := base..HEAD 含 Task 1.2／1.4 具名新建測試（批2 Task 1.1 亦改 brief_conformance，不可用該檔作 proxy）。"""
    proc = _run(
        ["git", "diff", "--name-only", f"{base}..{head}"],
        cwd=str(cwd) if cwd is not None else str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    names = {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}
    return bool(names & set(_BATCH3_PROXY_PATHS))


# 批 3 開工時，**放寬 `_g7` 與更新到期測試須配對**；
# **只改測試不改守衛＝假綠。** 到期不變式由 `_g7_narrow_expiry_holds` ＋ 真實 range 測試護住。
# C3-c 設計骨架（本輪不放寬 _g7）：批 3 開工後 uncommitted 檢查應只對批 3 標的路徑
# 匹配 ` M|MM`，不得對 epic 全量 allow 匹配 M（gate_check.sh 等 ambient M 會誤紅）。
def _g7_narrow_expiry_holds(*, batch3_started: bool, narrow_guard: bool) -> bool:
    """斷言 NOT (批3已開工 AND 窄守衛仍在)。"""
    return not (batch3_started and narrow_guard)


def _todo_task_section(task_id: str, *, todo_text: str | None = None) -> str:
    """截取凍結 TODO 中 `### Task <id>` 至下一 `### Task`／檔尾。"""
    text = TODO.read_text(encoding="utf-8") if todo_text is None else todo_text
    pat = re.compile(
        rf"^### Task {re.escape(task_id)}\b.*?(?=^### Task |\Z)",
        re.M | re.S,
    )
    m = pat.search(text)
    assert m, f"TODO 缺 ### Task {task_id}"
    return m.group(0)


def _todo_new_paths(task_id: str, *, section: str | None = None) -> set[str]:
    """從 Task 區段解析「新建」欄內 backtick 路徑（機械可導出，非散文合取）。"""
    sec = section if section is not None else _todo_task_section(task_id)
    if "**新建**：" not in sec or "**只讀**" not in sec:
        return set()
    new_block = sec.split("**新建**：", 1)[1].split("**只讀**", 1)[0]
    return {m.group(1) for m in re.finditer(r"`([^`]+)`", new_block)}


def test_batch3_proxy_literals_anti_drift_in_todo() -> None:
    """C3-a：_batch3_started 兩個 proxy 字串須落在 TODO Task 1.2／1.4「新建」欄。"""
    assert _BATCH3_PROXY_PATHS[0] in _todo_new_paths("1.2"), (
        f"Task 1.2 新建欄須含 {_BATCH3_PROXY_PATHS[0]}"
    )
    assert _BATCH3_PROXY_PATHS[1] in _todo_new_paths("1.4"), (
        f"Task 1.4 新建欄須含 {_BATCH3_PROXY_PATHS[1]}"
    )
    # 字串亦須為 _batch3_started 所引用（rename protection：改一側即紅）
    src = Path(__file__).read_text(encoding="utf-8")
    for p in _BATCH3_PROXY_PATHS:
        assert p in src


def test_batch3_proxy_anti_drift_new_column_mutation_turns_red() -> None:
    """C3-a mutation：proxy 移至「只讀」欄後 _todo_new_paths 必須轉紅（禁只測現況綠）。

    舊斷言（「新建」∈section ∧ proxy∈section）在此 mutation 上仍綠——已由 review-r6 實跑。
    """
    proxy = _BATCH3_PROXY_PATHS[0]
    s12 = _todo_task_section("1.2")
    assert proxy in _todo_new_paths("1.2", section=s12)
    head, rest = s12.split("**新建**：", 1)
    new_b, ro = rest.split("**只讀**", 1)
    new_b2 = new_b.replace(f"`{proxy}`", "")
    if f"`{proxy}`" not in ro:
        ro = f" `{proxy}`、" + ro
    mut = head + "**新建**：" + new_b2 + "**只讀**" + ro
    # 舊弱斷言仍綠（對照；證明必須綁「新建」欄）
    assert "新建" in mut and proxy in mut
    # 新強斷言必須轉紅
    assert proxy not in _todo_new_paths("1.2", section=mut), (
        "proxy 移出新建欄後 _todo_new_paths 仍命中＝假綠"
    )


# 批 3 開工時，**放寬 `_g7` 與更新到期測試須配對**；
# **只改守衛不改測試、或只改測試不改守衛，皆為假綠。**
# 五例：no-proxy｜proxy+narrow ⇒ 不變式 false｜proxy+wide ⇒ 放行｜
#       target ` M` ⇒ 轉紅｜僅 ambient ` M gate_check.sh` ⇒ 不紅


def test_batch3_exporter_missing_todo_fail_closed(tmp_path: Path) -> None:
    """CODEX-R2-P0-02：缺／空／畸形 TODO ⇒ print-batch3-* 與 gate_b3 皆非零。"""
    import os

    missing = tmp_path / "no_such_todo.md"
    empty = tmp_path / "empty_todo.md"
    empty.write_text("", encoding="utf-8")
    malformed = tmp_path / "malformed_todo.md"
    malformed.write_text("# no Task 1.2 / 1.4 sections\n", encoding="utf-8")

    for label, path in (
        ("missing", missing),
        ("empty", empty),
        ("malformed", malformed),
    ):
        env = {**os.environ, "GOVB1_TODO": str(path)}
        for flag in ("--print-batch3-paths", "--print-batch3-targets"):
            proc = _run(
                ["bash", "scripts/govb1_final_gate.sh", flag],
                env=env,
            )
            assert proc.returncode != 0, (
                f"{label} {flag} 須非零，got rc=0\n{proc.stdout}\n{proc.stderr}"
            )
        proc_g = _run(
            ["bash", "scripts/govb1_final_gate.sh", "--only", "gate_b3"],
            env=env,
        )
        assert proc_g.returncode != 0, (
            f"{label} gate_b3 須非零，got rc=0\n{proc_g.stdout}\n{proc_g.stderr}"
        )


def _shell_batch3_proxy_paths() -> set[str]:
    """呼叫 production `_g7_batch3_proxy_paths`（--print-batch3-paths）。

    禁複製 parser：複製版在 production 漂移時仍綠（CODEX-R1-P1-04／R-5 同型）。
    不得 source govb1_final_gate.sh（會跑 main／_g0_tests 遞迴）。
    """
    proc = _run(["bash", "scripts/govb1_final_gate.sh", "--print-batch3-paths"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def _shell_batch3_target_paths() -> set[str]:
    """呼叫 production `_g7_batch3_target_paths`（--print-batch3-targets）。"""
    proc = _run(["bash", "scripts/govb1_final_gate.sh", "--print-batch3-targets"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def test_g7_narrow_guard_expiry_live_pass() -> None:
    """不變式：NOT (批3已開工 AND 窄守衛仍在)；live range 現況須通過。"""
    base = _base_commit()
    started = _batch3_started(base)
    narrow = _is_narrow_g7_status_case(GATE.read_text(encoding="utf-8"))
    assert _g7_narrow_expiry_holds(batch3_started=started, narrow_guard=narrow)


def test_g7_task_scoped_widen_paired_with_expiry() -> None:
    """放寬後 production 不得再判為窄守衛；與 batch3_started 配對不變式仍綠。"""
    gate_src = GATE.read_text(encoding="utf-8")
    narrow = _is_narrow_g7_status_case(gate_src)
    # 批 3 已 task-scoped 放寬：case 臂含 M
    assert not narrow, "B3 放寬後 _g7 status case 須含 M（不得仍為窄守衛）"
    assert "\\ M|M\\ |MM" in gate_src or r"\ M|M\ |MM" in gate_src, (
        "production _g7 須含 task-scoped M 臂"
    )
    base = _base_commit()
    started = _batch3_started(base)
    assert _g7_narrow_expiry_holds(batch3_started=started, narrow_guard=narrow)


def test_g7_narrow_guard_expiry_five_cases(tmp_path: Path) -> None:
    """五例：no-proxy｜proxy+narrow｜proxy+wide｜（range 真偽）＋不變式兩向。"""
    gate_src = GATE.read_text(encoding="utf-8")
    # ① no-proxy ⇒ started=false
    base = _base_commit()
    # production 在 commit ② 前 started=false；之後 true——以 temp range 證 no-proxy
    repo = tmp_path / "batch3_range"
    repo.mkdir()
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "govb1-test",
        "GIT_AUTHOR_EMAIL": "govb1-test@example.invalid",
        "GIT_COMMITTER_NAME": "govb1-test",
        "GIT_COMMITTER_EMAIL": "govb1-test@example.invalid",
    }

    def g(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    assert g("init", "--object-format=sha1").returncode == 0
    assert g("config", "user.name", "govb1-test").returncode == 0
    assert g("config", "user.email", "govb1-test@example.invalid").returncode == 0
    g("checkout", "-b", "main")
    (repo / "README").write_text("base\n", encoding="utf-8")
    assert g("add", "README").returncode == 0
    assert g("commit", "-m", "base").returncode == 0
    rp = g("rev-parse", "--verify", "HEAD")
    assert rp.returncode == 0, rp.stderr
    base_sha = rp.stdout.strip()
    # ① no-proxy
    assert not _batch3_started(base_sha, cwd=repo), "no-proxy ⇒ started=false"

    # ② proxy + narrow ⇒ 不變式 false
    proxy = repo / _BATCH3_PROXY_PATHS[0]
    proxy.parent.mkdir(parents=True, exist_ok=True)
    proxy.write_text("# batch3 proxy stub\n", encoding="utf-8")
    assert g("add", _BATCH3_PROXY_PATHS[0]).returncode == 0
    assert g("commit", "-m", "add batch3 proxy").returncode == 0
    assert _batch3_started(base_sha, cwd=repo), "proxy ⇒ started=true"
    assert not _g7_narrow_expiry_holds(batch3_started=True, narrow_guard=True), (
        "proxy+narrow ⇒ 不變式 false"
    )

    # ③ proxy + wide ⇒ 放行（production 已放寬）
    assert not _is_narrow_g7_status_case(gate_src), "production 為 wide"
    assert _g7_narrow_expiry_holds(batch3_started=True, narrow_guard=False), (
        "proxy+wide ⇒ 放行"
    )

    # ④ 構造窄／寬 case：proxy+narrow 不變式 false；wide 放行
    fake_narrow = """
_g7() {
  case "${_st}" in
    \\?\\?|A\\ |A?|A*)
      : ;;
  esac
}
"""
    assert _is_narrow_g7_status_case(fake_narrow), "構造之窄守衛須被偵測"
    assert not _g7_narrow_expiry_holds(batch3_started=True, narrow_guard=True)

    fake_wide = """
_g7() {
  case "${_st}" in
    \\?\\?|A\\ |A?|A*)
      : ;;
    \\ M|M\\ |MM)
      : ;;
  esac
}
"""
    assert not _is_narrow_g7_status_case(fake_wide), "含 M 不得判窄"
    assert _g7_narrow_expiry_holds(batch3_started=True, narrow_guard=False)


def test_g7_ambient_m_gate_check_not_red() -> None:
    """僅 ambient ` M scripts/gate_check.sh` ⇒ 不紅（task-scoped；禁 epic-wide）。"""
    st = _run(["git", "status", "--porcelain", "--", "scripts/gate_check.sh"])
    # 現況可為 M 或乾淨；若為 M，g7 必須仍綠
    proc = _run(["bash", "scripts/govb1_final_gate.sh", "--only", "g7"])
    assert proc.returncode == 0, (
        f"ambient M 不得使 g7 轉紅（task-scoped）\n"
        f"status={st.stdout!r}\n{proc.stdout}\n{proc.stderr}"
    )
    # 機械：gate_check 在 allow 且不在批 3 標的
    targets = _shell_batch3_target_paths()
    assert "scripts/gate_check.sh" not in targets
    allow = {
        ln.split(None, 1)[1]
        for ln in MANIFEST.read_text(encoding="utf-8").splitlines()
        if ln.startswith("allow ")
    }
    assert "scripts/gate_check.sh" in allow


def test_g7_target_m_turns_red_when_batch3_started() -> None:
    """批3開工後，標的路徑 ` M` ⇒ G-7 轉紅（與 ambient 對照）。"""
    base = _base_commit()
    if not _batch3_started(base):
        pytest.skip("批 3 proxy 尚未進 range；target-M 轉紅待 proxy 交付後驗")
    target = REPO / "scripts" / "brief_conformance_check.sh"
    original = target.read_text(encoding="utf-8")
    try:
        target.write_text(original + "\n# g7-target-m-probe\n", encoding="utf-8")
        proc = _run(["bash", "scripts/govb1_final_gate.sh", "--only", "g7"])
        assert proc.returncode != 0, "標的 M 於批3開工後須使 g7 轉紅"
        blob = (proc.stdout or "") + (proc.stderr or "")
        assert "UNCOMMITTED" in blob or "brief_conformance" in blob
    finally:
        target.write_text(original, encoding="utf-8")


def test_batch3_shell_export_anti_drift_triple() -> None:
    """三方 anti-drift：shell 導出 ≡ _BATCH3_PROXY_PATHS ≡ TODO 新建欄。"""
    shell_set = _shell_batch3_proxy_paths()
    py_set = set(_BATCH3_PROXY_PATHS)
    todo_set = _todo_new_paths("1.2") | _todo_new_paths("1.4")
    assert shell_set == py_set == todo_set, (
        f"anti-drift 失敗 shell={shell_set} py={py_set} todo={todo_set}"
    )
    # 標的集合須含 brief_conformance + 兩 proxy
    targets = _shell_batch3_target_paths()
    assert "scripts/brief_conformance_check.sh" in targets
    assert targets >= py_set


# ── WAIVER-B45-B3-IMPL 機械邊界 ──────────────────────────────────────
# 凍結：B3 開工前 kind case 區塊 hash（不得因 B3 改 membership）
_B3_KIND_CASE_SHA256 = (
    "62714abffa416968b8b00085ee344e6e86a9d166defc49902457f86c2d0b883f"
)
_B45_HARNESS = (
    "tests/governance/test_cxrun_stamp_prompt.py",
    "tests/governance/test_stamp_taskid_inject.py",
    "tests/governance/test_rolegate_predispatch.py",
    "tests/governance/test_result_state_format_failed.py",
    "tests/governance/test_completeness_idlike_fp.py",
)
_B45_FORBIDDEN_PREFIXES = (
    "scripts/govb1_scope.manifest",
    "scripts/govb1_frozen_hashes.txt",
    "docs/GOVB1_",
    "scripts/cx_run.sh",
    "scripts/govflow_lifecycle.json",
)

# B4 窗（b4_start..HEAD）之禁改前綴〔20260808-GOVB1-B4-STAMP-R2 三家 APPROVED〕。
# **由 _B45_FORBIDDEN_PREFIXES 機械導出**，僅移除下列二項必要共變檔
# （Task 1.3 須令 embed ≡ JSON，二檔皆為授權變更）；
# harness 五檔／scope.manifest／docs/GOVB1_／frozen 封閉集比對 **一項不得少**
# 〔grok STAMP-R2 前提 3〕。以推導而非手抄，杜絕「順手多移一項」。
_B4_ALLOWED_COVARIANT = ("scripts/cx_run.sh", "scripts/govflow_lifecycle.json")
_B4_FORBIDDEN_PREFIXES = tuple(
    p for p in _B45_FORBIDDEN_PREFIXES if p not in _B4_ALLOWED_COVARIANT
)


def _kind_case_block(src: str) -> str:
    m = re.search(r'case "\$\{_bk\}" in\n.*?\nesac', src, re.S)
    assert m, "brief_conformance 缺 kind case 區塊"
    return m.group(0)


def _kind_case_sha256(src: str) -> str:
    import hashlib

    return hashlib.sha256(_kind_case_block(src).encode()).hexdigest()


def test_waiver_b45_kind_case_block_hash_frozen() -> None:
    """waiver 邊界：kind case membership 區塊 hash 不變。"""
    src = (REPO / "scripts" / "brief_conformance_check.sh").read_text(encoding="utf-8")
    got = _kind_case_sha256(src)
    assert got == _B3_KIND_CASE_SHA256, (
        f"kind case block hash 漂移（B-45 禁改 membership）want={_B3_KIND_CASE_SHA256} got={got}"
    )


def test_waiver_b45_b3_range_does_not_touch_forbidden() -> None:
    """B3 range 不得觸及 B-45 禁改清單（harness／manifest／SPEC／embed）。

    範圍＝git diff --name-only b3_start..<上界>（禁 --grep 圈定；CODEX-R1-P0-01）。
    🔴 上界〔20260808-GOVB1-B4-STAMP-R2 三家 APPROVED〕：
      b4_start 存在 ⇒ 收斂為 b3_start..b4_start（B3 只看守自己的交付窗）；
      b4_start 缺席 ⇒ 維持 b3_start..HEAD（**與收斂前逐字相同**）。
    收斂之反向風險（硬規矩 9「該擋的從此不受檢」）由
    test_waiver_b4_range_does_not_touch_forbidden 接手，且由
    test_waiver_b4_active_when_b4_start_anchored 機械強制「不得 skip」。
    frozen_hashes 封閉 key 集合（base_commit／scope_manifest／b3_start 必備、b4_start 可選）；
    範圍內僅允許 b3_start／b4_start 值差，禁重複／未知／額外行〔CODEX-R2-P1-03〕。
    具名殘留：移動 b3_start 本身仍屬票 B-44（repo 內無解）。
    """
    base = _base_commit()
    b3 = _b3_start()
    b4 = _b4_start()
    upper = b4 if b4 is not None else "HEAD"

    # 錨鏈健全性（合法 commit＋祖先序＋皆為 HEAD 祖先）；共用函式，B4 窗亦呼叫
    _assert_anchor_chain_sane()

    # 批3 開工 proxy 須已在 epic range
    epic = _run(["git", "diff", "--name-only", f"{base}..HEAD"])
    assert epic.returncode == 0, epic.stderr
    epic_names = {ln.strip() for ln in epic.stdout.splitlines() if ln.strip()}
    if not (epic_names & set(_BATCH3_PROXY_PATHS)):
        pytest.skip("批 3 proxy 尚未進 range；waiver range 檢查待 B3 交付後生效")

    # 完整 B3 range（外部錨點；非 commit message）；上界依 b4_start 收斂
    diff = _run(["git", "diff", "--name-only", f"{b3}..{upper}"])
    assert diff.returncode == 0, diff.stderr
    names = {ln.strip() for ln in diff.stdout.splitlines() if ln.strip()}
    # 票 B-49：--name-only 隱去 rename 舊名 ⇒ 改名可洗出保護範圍（CODEX-CONSULT-R1-P0-02）
    names |= _rename_old_names(f"{b3}..{upper}")
    assert names, f"b3_start..{upper} 應有 B3 改動"

    hit_harness = names & set(_B45_HARNESS)
    # 票 B-49：通過 git 物件身分比對之授權路徑扣除；其餘一律仍拒。
    unexcused = {p for p in hit_harness if not _b49_granted(p)}
    assert not unexcused, f"B3 range 觸及未授權之 B-45 harness: {unexcused}"
    for pref in _B45_FORBIDDEN_PREFIXES:
        if pref == "scripts/govb1_frozen_hashes.txt":
            # 允許檔進 range（主委 b3_start 錨點）；內容走封閉集合比對
            continue
        bad = {
            n
            for n in names
            if (n == pref or n.startswith(pref)) and not _b49_granted(n)
        }
        assert not bad, f"B3 range 觸及禁改前綴 {pref}: {bad}"

    # 封閉 key 集合：HEAD 須三 key 全齊；b3 錨點樹可缺 b3_start 行（主委後掛）
    # 僅 b3_start 值可差；重複／third: 兩側皆拒
    def _frozen_at(rev: str, *, require_b3_start: bool) -> dict[str, str]:
        sh = _run(["git", "show", f"{rev}:scripts/govb1_frozen_hashes.txt"])
        assert sh.returncode == 0, sh.stderr
        return _parse_frozen_hashes(sh.stdout, require_b3_start=require_b3_start)

    fb = _frozen_at(b3, require_b3_start=False)
    fh = _frozen_at(upper, require_b3_start=True)
    assert fb["base_commit"] == fh["base_commit"], (
        f"base_commit: 於 b3_start..{upper} 不得變"
    )
    assert fb["scope_manifest"] == fh["scope_manifest"], (
        f"scope_manifest: 於 b3_start..{upper} 不得變"
    )
    # b3_start／b4_start 值允許差；key 集合已由 parser 保證無未知 key／重複

    # embed 常數：B3 觸及 brief_conformance 時，與 b3_start 樹比對
    if "scripts/brief_conformance_check.sh" in names:
        b = _run(["git", "show", f"{b3}:scripts/brief_conformance_check.sh"])
        h = _run(["git", "show", f"{upper}:scripts/brief_conformance_check.sh"])
        assert b.returncode == 0 and h.returncode == 0

        def _embed(s: str) -> str:
            m = re.search(r"^_LIFECYCLE_EMBED_B64='(.*)'$", s, re.M)
            return m.group(1) if m else ""

        assert _embed(b.stdout) == _embed(h.stdout), (
            "brief_conformance embed 被改（B-45 禁）"
        )
    assert "scripts/cx_run.sh" not in names


def test_b4_forbidden_prefixes_removes_exactly_two() -> None:
    """B4 清單＝B-45 清單「僅移除二項必要共變」〔grok STAMP-R2 前提 3〕。

    機械斷言，杜絕日後順手多移一項而靜默失去保護。
    mutation：把 _B4_ALLOWED_COVARIANT 多加一項 ⇒ 本測轉紅（已實跑驗證）。

    🔴 **oracle 必須是字面期望集合**：若改成
    `removed == set(_B4_ALLOWED_COVARIANT)`，因 _B4_FORBIDDEN_PREFIXES 即由
    _B4_ALLOWED_COVARIANT 導出，該式為**同義反覆恆真**——主委初版即犯此誤，
    由 mutation probe 當場抓出（票 B-43 同型：檢查存在但恆真）。
    """
    # 字面凍結：B4 窗禁改前綴之期望值（committee STAMP-R2 定案）
    expected_b4_forbidden = {
        "scripts/govb1_scope.manifest",
        "scripts/govb1_frozen_hashes.txt",
        "docs/GOVB1_",
    }
    assert set(_B4_FORBIDDEN_PREFIXES) == expected_b4_forbidden, (
        f"B4 禁改前綴漂移：want={expected_b4_forbidden} got={set(_B4_FORBIDDEN_PREFIXES)}"
    )
    # 且必為 B-45 清單之真子集，僅少掉二項必要共變檔
    assert set(_B4_FORBIDDEN_PREFIXES) < set(_B45_FORBIDDEN_PREFIXES)
    assert set(_B45_FORBIDDEN_PREFIXES) - set(_B4_FORBIDDEN_PREFIXES) == {
        "scripts/cx_run.sh",
        "scripts/govflow_lifecycle.json",
    }
    # harness 清單於 B4 窗一項不得少（B4 直接沿用同一常數）
    assert len(_B45_HARNESS) == 5


def test_waiver_b4_range_does_not_touch_forbidden() -> None:
    """B4 窗（b4_start..HEAD）不得觸及禁改清單。

    B3 waiver 上界收斂為 b4_start 後，b4_start..HEAD 由本測接手看守
    ——硬規矩 9：收窄型修法不得使「該擋的從此不受檢」
    〔20260808-GOVB1-B4-STAMP-R2 三家 APPROVED〕。
    b4_start 缺席 ⇒ skip 是安全的：此時 B3 waiver 仍以開放區間 b3_start..HEAD
    全程看守，**無保護真空**；一旦錨定，
    test_waiver_b4_active_when_b4_start_anchored 機械強制本測不得 skip。
    """
    b4 = _b4_start()
    if b4 is None:
        pytest.skip("b4_start 尚未錨定；B3 waiver 之開放區間仍全程看守（無保護真空）")

    # 〔CODEX-R1-P1-02〕本窗自身亦須驗錨鏈，不得倚賴 B3 窗代驗
    _assert_anchor_chain_sane()

    # 上界依 b5_start 收斂（同 B3 之於 b4_start）；缺席 ⇒ 維持 HEAD，行為逐字不變
    b5 = _b5_start()
    upper = b5 if b5 is not None else "HEAD"

    diff = _run(["git", "diff", "--name-only", f"{b4}..{upper}"])
    assert diff.returncode == 0, diff.stderr
    names = {ln.strip() for ln in diff.stdout.splitlines() if ln.strip()}
    # 票 B-49：--name-only 隱去 rename 舊名 ⇒ 改名可洗出保護範圍（CODEX-CONSULT-R1-P0-02）
    names |= _rename_old_names(f"{b4}..{upper}")

    hit_harness = names & set(_B45_HARNESS)
    # 票 B-49：通過 git 物件身分比對之授權路徑扣除；其餘一律仍拒。
    unexcused = {p for p in hit_harness if not _b49_granted(p)}
    assert not unexcused, f"B4 range 觸及未授權之 B-45 harness: {unexcused}"
    for pref in _B4_FORBIDDEN_PREFIXES:
        if pref == "scripts/govb1_frozen_hashes.txt":
            # 允許檔進 range（主委 b4_start 錨點）；內容走封閉集合比對（見下）
            continue
        bad = {
            n
            for n in names
            if (n == pref or n.startswith(pref)) and not _b49_granted(n)
        }
        assert not bad, f"B4 range 觸及禁改前綴 {pref}: {bad}"

    # 封閉 key 集合：b4_start..HEAD 內三既有錨值皆不得變
    def _frozen_at(rev: str) -> dict[str, str]:
        sh = _run(["git", "show", f"{rev}:scripts/govb1_frozen_hashes.txt"])
        assert sh.returncode == 0, sh.stderr
        return _parse_frozen_hashes(sh.stdout)

    f4 = _frozen_at(b4)
    fh = _frozen_at(upper)
    for key in ("base_commit", "scope_manifest", "b3_start"):
        assert f4[key] == fh[key], f"{key}: 於 b4_start..{upper} 不得變"
    # 具名殘留：移動 b4_start 本身仍屬票 B-44（repo 內無可信存放處）


def test_waiver_b4_active_when_b4_start_anchored() -> None:
    """耦合 fail-closed〔codex STAMP-R2：「B4 waiver 路徑須缺席即 fail-closed」〕。

    b4_start 一旦錨定 ⇒ B3 waiver 上界已收斂 ⇒ b4_start..HEAD 必須由 B4 waiver
    **實跑**看守。若 B4 waiver 因任何理由 skip，本測轉紅（保護真空 fail-closed）。
    mutation：於 B4 waiver 首行插入無條件 pytest.skip ⇒ 本測須轉紅。
    """
    if _b4_start() is None:
        pytest.skip("b4_start 尚未錨定；B3 waiver 仍以開放區間 b3_start..HEAD 全程看守")
    try:
        test_waiver_b4_range_does_not_touch_forbidden()
    except pytest.skip.Exception as exc:
        raise AssertionError(
            f"b4_start 已錨定但 B4 waiver 仍 skip ⇒ b4_start..HEAD 保護真空: {exc}"
        ) from exc


# ── B5 窗（b5_start..HEAD）─────────────────────────────────────────────
# 🔴 使用者 2026-08-09 **逐字授權**：把 scripts/governance_families.json 加進 manifest，
#    以解「GOVB1 epic 期間委員名冊完全改不了」之死鎖（第七次結構性死鎖）。
#    ⇒ B5 窗之禁改前綴由 _B4_FORBIDDEN_PREFIXES 機械導出，**僅移除 manifest 一項**。
# 🔴 移除 ≠ 解除保護：改由 test_b5_manifest_extension_is_exactly_authorized
#    釘死「manifest 只准新增被授權的那一行」——比「整檔禁改」**更精確**，
#    且擋得住「順手多加幾行」這種 scope accretion。
_B5_MANIFEST_UNLOCKED = ("scripts/govb1_scope.manifest",)
_B5_FORBIDDEN_PREFIXES = tuple(
    p for p in _B4_FORBIDDEN_PREFIXES if p not in _B5_MANIFEST_UNLOCKED
)
# 字面凍結：使用者授權新增之 manifest 條目（**只有這一行**）
_B5_MANIFEST_AUTHORIZED_ADDITIONS = frozenset(
    {
        "allow scripts/governance_families.json",
        "allow docs/GOVB1_INPUT_QUALITY_TODO.md",
        "allow tests/governance/test_brief_conformance.py",
        "allow tests/governance/test_completeness_idlike_fp.py",
        "allow tests/governance/test_cxrun_selfcheck_prompt.py",
        "allow tests/governance/test_cxrun_stamp_prompt.py",
        "allow tests/governance/test_debt_emit.py",
        "allow tests/governance/test_doc_format_precheck.py",
        "allow tests/governance/test_gov_check_dep_failclosed.py",
        "allow tests/governance/test_result_state_format_failed.py",
        "allow tests/governance/test_rolegate_predispatch.py",
        "allow tests/governance/test_stamp_taskid_inject.py",
        "allow tests/governance/test_verify_gate_b3.py",
        # 票 B-49 Task 2.3 之閉合證據檔（新建）
        "allow tests/governance/test_govb49_path_grant.py",
        # 票 B-49 as-built 差異文件（新建）——本檔未登記時 G-7 會紅，r3 由 codex 實跑抓到
        "allow docs/GOV_B49_ASBUILT_DELTA.md",
    }
)


def test_b5_forbidden_prefixes_removes_exactly_manifest() -> None:
    """B5 清單＝B4 清單「僅移除 manifest 一項」。

    🔴 oracle 為**字面期望集合**：若寫成 `removed == set(_B5_MANIFEST_UNLOCKED)`，
    因 _B5_FORBIDDEN_PREFIXES 即由該常數導出，該式**同義反覆恆真**
    （主委在 B4 犯過一次，由 mutation probe 抓出）。
    """
    expected_b5_forbidden = {
        "scripts/govb1_frozen_hashes.txt",
        "docs/GOVB1_",
    }
    assert set(_B5_FORBIDDEN_PREFIXES) == expected_b5_forbidden, (
        f"B5 禁改前綴漂移：want={expected_b5_forbidden} got={set(_B5_FORBIDDEN_PREFIXES)}"
    )
    assert set(_B5_FORBIDDEN_PREFIXES) < set(_B4_FORBIDDEN_PREFIXES)
    assert set(_B4_FORBIDDEN_PREFIXES) - set(_B5_FORBIDDEN_PREFIXES) == {
        "scripts/govb1_scope.manifest"
    }
    assert len(_B45_HARNESS) == 5  # harness 於 B5 窗一項不得少


def test_b5_manifest_extension_is_exactly_authorized() -> None:
    """🔴 manifest 於 B5 窗**只准新增被授權之條目，且不得刪任何行**。

    這是「解除整檔禁改」之替代保護：比禁改更精確——允許授權的那一行，
    但擋住任何其他新增（scope accretion）與任何刪除（偷偷放寬既有 deny）。
    mutation：在 _B5_MANIFEST_AUTHORIZED_ADDITIONS 之外多加一行 manifest ⇒ 本測轉紅。
    """
    b5 = _b5_start()
    if b5 is None:
        pytest.skip("b5_start 尚未錨定；manifest 仍受 B4 窗整檔禁改保護")

    def _manifest_lines(rev: str) -> set[str]:
        sh = _run(["git", "show", f"{rev}:scripts/govb1_scope.manifest"])
        assert sh.returncode == 0, sh.stderr
        return {
            ln.strip()
            for ln in sh.stdout.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        }

    before, after = _manifest_lines(b5), _manifest_lines("HEAD")
    added, removed = after - before, before - after
    assert not removed, f"manifest 於 b5_start..HEAD 不得刪行: {sorted(removed)}"
    assert added <= _B5_MANIFEST_AUTHORIZED_ADDITIONS, (
        f"manifest 新增未經授權之條目: {sorted(added - _B5_MANIFEST_AUTHORIZED_ADDITIONS)}"
    )


def test_waiver_b5_range_does_not_touch_forbidden() -> None:
    """B5 窗（b5_start..HEAD）不得觸及禁改清單。

    B4 窗上界收斂為 b5_start 後，b5_start..HEAD 由本測接手看守
    ——硬規矩 9：收窄型修法不得使「該擋的從此不受檢」。
    """
    b5 = _b5_start()
    if b5 is None:
        pytest.skip("b5_start 尚未錨定；B4 窗之開放區間仍全程看守（無保護真空）")

    _assert_anchor_chain_sane()

    diff = _run(["git", "diff", "--name-only", f"{b5}..HEAD"])
    assert diff.returncode == 0, diff.stderr
    names = {ln.strip() for ln in diff.stdout.splitlines() if ln.strip()}
    # 票 B-49：--name-only 隱去 rename 舊名 ⇒ 改名可洗出保護範圍（CODEX-CONSULT-R1-P0-02）
    names |= _rename_old_names(f"{b5}..HEAD")

    hit_harness = names & set(_B45_HARNESS)
    # 票 B-49：通過 git 物件身分比對之授權路徑扣除；其餘一律仍拒。
    unexcused = {p for p in hit_harness if not _b49_granted(p)}
    assert not unexcused, f"B5 range 觸及未授權之 B-45 harness: {unexcused}"
    for pref in _B5_FORBIDDEN_PREFIXES:
        if pref == "scripts/govb1_frozen_hashes.txt":
            continue  # 允許檔進 range（主委 b5_start 錨點）；內容走封閉集合比對
        bad = {
            n
            for n in names
            if (n == pref or n.startswith(pref)) and not _b49_granted(n)
        }
        assert not bad, f"B5 range 觸及禁改前綴 {pref}: {bad}"

    def _frozen_at(rev: str) -> dict[str, str]:
        sh = _run(["git", "show", f"{rev}:scripts/govb1_frozen_hashes.txt"])
        assert sh.returncode == 0, sh.stderr
        return _parse_frozen_hashes(sh.stdout)

    f5, fh = _frozen_at(b5), _frozen_at("HEAD")
    # 🔴 scope_manifest **允許**於本窗變動（授權擴充之必然結果）；三個既有錨值不得變
    for key in ("base_commit", "b3_start", "b4_start"):
        assert f5[key] == fh[key], f"{key}: 於 b5_start..HEAD 不得變"


def test_waiver_b5_active_when_b5_start_anchored() -> None:
    """耦合 fail-closed：b5_start 一旦錨定，B5 waiver 不得 skip（否則保護真空）。"""
    if _b5_start() is None:
        pytest.skip("b5_start 尚未錨定；B4 窗仍以開放區間看守")
    try:
        test_waiver_b5_range_does_not_touch_forbidden()
    except pytest.skip.Exception as exc:
        raise AssertionError(
            f"b5_start 已錨定但 B5 waiver 仍 skip ⇒ b5_start..HEAD 保護真空: {exc}"
        ) from exc


# ── out-of-epic 通道（2026-08-09 使用者授權）──────────────────────────
# 讓「epic 期間穿插修別的問題」不被 manifest 白名單擋死；代價是 G-7 對那些路徑放行，
# 故硬保護集**必須**仍然擋得住，否則通道就成了萬能旁路。
_G7_OOE_HARD_PROTECTED = (
    "docs/GOVB1_",
    "scripts/govb1_scope.manifest",
    "scripts/govb1_frozen_hashes.txt",
)


def test_ooe_hard_protected_set_is_frozen() -> None:
    """硬保護集（out-of-epic 亦禁）須與 `govb1_final_gate.sh` 逐字一致。

    🔴 oracle 為**字面期望集合**；並比對 shell 端常數，兩處漂移即紅。
    刻意**不含** `_B45_HARNESS` 五檔——out-of-epic 工作正是治理 harness 之維護，
    那五檔的真正守衛是 pre-push 全套 pytest，檔案凍結只是 epic 內防 scope creep。
    """
    expected = {
        "docs/GOVB1_",
        "scripts/govb1_scope.manifest",
        "scripts/govb1_frozen_hashes.txt",
    }
    assert set(_G7_OOE_HARD_PROTECTED) == expected

    src = (REPO / "scripts" / "govb1_final_gate.sh").read_text(encoding="utf-8")
    m = re.search(r"_G7_OOE_HARD_PROTECTED='([^']*)'", src)
    assert m, "govb1_final_gate.sh 缺 _G7_OOE_HARD_PROTECTED 常數"
    shell_set = {ln.strip() for ln in m.group(1).splitlines() if ln.strip()}
    assert shell_set == expected, (
        f"shell 端硬保護集漂移：want={expected} got={shell_set}"
    )
    # 五 harness 不得混入硬保護集（否則 out-of-epic 修不了治理 harness）
    assert not (shell_set & set(_B45_HARNESS))


def test_ooe_lane_requires_trailer_and_respects_hard_protected() -> None:
    """通道之兩條不變式（讀碼層；行為層由 g7 實跑 mutation 驗證）。

    ① 豁免須以 commit trailer 為條件——不得無條件放行
    ② 硬保護集於 `_g7_path_only_ooe` 內仍 return 1（即不豁免）
    """
    src = (REPO / "scripts" / "govb1_final_gate.sh").read_text(encoding="utf-8")
    assert "_g7_path_only_ooe" in src
    assert re.search(
        r"_g7_covered \"\$\{p\}\" \"\$\{decl\}\" \|\| _g7_path_only_ooe \"\$\{p\}\"", src
    ), "G-7 豁免須為『manifest 未覆蓋 **且** 僅由 out-of-epic commit 觸及』"
    assert "Governance-Scope:" in src, "豁免須以 commit trailer 為條件"
    # 硬保護集比對須在豁免判定內（直接引用常數，或呼叫封裝之 _g7_ooe_is_protected）
    body = src.split("_g7_path_only_ooe()", 1)[1].split("\n_g7()", 1)[0]
    assert ("_G7_OOE_HARD_PROTECTED" in body) or ("_g7_ooe_is_protected" in body), (
        "硬保護集比對須在豁免判定內"
    )
    # 🔴 rename/copy 舊名守衛亦須在豁免判定內〔CODEX-R1-P0-01〕：
    #    git diff --name-only 隱去 rename 舊名 ⇒ 改名即可把硬保護檔搬出保護範圍
    assert "_g7_ooe_rename_hits_protected" in body, (
        "豁免判定須含 rename/copy 舊名守衛（否則硬保護可被改名繞過）"
    )
    assert "--name-status" in src, "rename 守衛須用 --name-status（--name-only 隱去舊名）"


# ── R-18：trailer 須以 git 原生解析，禁 `--grep` ─────────────────────────
# 封閉集，恰 2 筆——本通道上線當日、慣例訂立前之 commit（trailer 與 Co-Authored-By
# 之間空了一行 ⇒ 原生解析認不得）。**不得增長**：多一筆＝再開一次 --grep 後門。
_G7_OOE_GRANDFATHER = (
    "d0dc68245e967380965e6b2ee18349e74a34ca5d",
    "28b586a8224f1338b6a445f66e6e782e06c3d013",
)


def _gate_src() -> str:
    return (REPO / "scripts" / "govb1_final_gate.sh").read_text(encoding="utf-8")


# ── consult-r1 C1/C2 落地：三道機制互不相通，且文件不得再誤導 ──────────
# 裁決出處：handoffs/reconcile/20260809-govb1-x-consult-r1/synth.md（codex+composer APPROVED）
_WAIVER_GUARD_FNS = (
    "test_waiver_b45_b3_range_does_not_touch_forbidden",
    "test_waiver_b4_range_does_not_touch_forbidden",
    "test_waiver_b5_range_does_not_touch_forbidden",
)
# commit 訊息解析的痕跡——窗守衛內出現任一即違反 C1 裁決
_MSG_PARSE_MARKERS = ("--grep", "%(trailers", "Governance-Scope", "%B", "%s", "log_message")


# ── 定時炸彈：`_B45_HARNESS` 凍結解除 ⇒ 必須同時處理票 B-49 ────────────
# 出處：consult-r1 落地清單 §3，採 composer Q2 之強化版（字面關閉條件 + 耦合測試）。
_B49_TICKET = "handoffs/20260801-GOV-AMEND-BACKLOG.md"
_B49_ID = "GOV-ROLES-SOT-CANNOT-EXPRESS-ORCHESTRATOR"


def _b45_freeze_still_active() -> bool:
    """🔴 **行為層**引信：真的把窗守衛跑一次，餵它含 harness 檔的假 diff，看它拒不拒。

    初版用字面比對（`"assert not hit_harness" in body`），**兩家從相反方向打穿**：
      · `CODEX-R3-P1-01`（假綠）：保留 `_B45_HARNESS` 與該 assert，另加
        `hit_harness = set()` ⇒ 守衛實質失效但引信報「仍凍結」⇒ 炸彈不炸。
      · `COMPOSER-R3-P2-01`（假紅）：無辜重構（改名／`assert len(...)==0`／抽 helper）
        ⇒ 引信誤判「已解凍」⇒ 炸彈假紅，逼人關一張其實還不能關的票。
    兩者同根：**量的是長相，不是行為**。

    現行判準（實質）：
      ① 至少有**一道 live 守衛**，餵它「diff 含 harness 檔」時**真的拒絕**
      ② **沒有任何 live 守衛**在同樣輸入下放行
      ③ `_B45_HARNESS` 仍是 5 檔
    `pytest.skip` 之守衛視為 dormant（設計上由另一窗接手），不計入①也不判②。
    """
    import unittest.mock as _mock

    mod = sys.modules[__name__]
    real_run = _run

    def _fake_run(cmd, *a, **kw):
        # 只攔 `git diff --name-only <range>`；其餘（anchor/frozen_hashes）走真指令
        if list(cmd[:3]) == ["git", "diff", "--name-only"]:
            # 票 B-49：餵**未授權**之 harness；差集空 ⇒ 無可偵測對象（下方回 False）
            _rest = sorted(set(_B45_HARNESS) - _B49_HARNESS_GRANT)
            _probe = _rest[0] if _rest else ""
            return subprocess.CompletedProcess(list(cmd), 0, _probe + "\n", "")
        return real_run(cmd, *a, **kw)

    rejected = 0
    for fn in _WAIVER_GUARD_FNS:
        guard = getattr(mod, fn, None)
        if guard is None:
            return False  # 守衛不見了 ⇒ 視為已解凍（保守方向＝炸）
        with _mock.patch.object(mod, "_run", _fake_run):
            try:
                guard()
            except AssertionError as exc:
                if "harness" in str(exc):
                    rejected += 1
                    continue
                return False  # 因別的原因失敗 ⇒ 引信不可信，保守判已解凍
            except BaseException as exc:  # noqa: BLE001
                if type(exc).__name__ == "Skipped":
                    continue  # dormant：由另一窗看守，不作判斷依據
                return False
            else:
                return False  # 🔴 餵了 harness 檔卻放行 ⇒ 凍結實質失效
    return rejected >= 1 and len(_B45_HARNESS) == 5


# 🔴 錨定 `## B-49 ` heading 起算〔`CODEX-R3-P1-02`〕：
#   初版用 `text.find(_B49_ID)` 取**第一個出現處**再無界 `re.search`，
#   於 canonical heading 之前任意處補一行同 ID + 假 `TICKET-STATUS:` 即可 spoof。
_B49_HEADING_RE = re.compile(rf"^## B-49 票 `{re.escape(_B49_ID)}`\s*$", re.M)


def _b49_ticket_status() -> str:
    """回票 B-49 的 `TICKET-STATUS`（缺票／重複票 → 'MISSING'，保守方向＝炸）。"""
    text = (REPO / _B49_TICKET).read_text(encoding="utf-8")
    heads = list(_B49_HEADING_RE.finditer(text))
    if len(heads) != 1:
        return "MISSING"  # 0=票沒了；>1=重複 heading，狀態有歧義 ⇒ 一律不採信
    section = text[heads[0].end():]
    nxt = re.search(r"^## ", section, re.M)  # 只在本票 section 內找，不跨到下一張票
    if nxt:
        section = section[: nxt.start()]
    found = re.findall(r"^TICKET-STATUS:\s*(\S+)\s*$", section, re.M)
    if len(found) != 1:
        return "MISSING"  # 本 section 內 0 或多個狀態行 ⇒ 有歧義，不採信
    return found[0]


# 票 B-49 之閉合證據：六格具名 selector（SPEC/TODO Task 2.3）。
# 🔴 **逐字列出**——改名或刪除任一格即紅（`CODEX-R1-P1-02`：不得以整檔 exit 0 充當證據）。
_B49_CLOSURE_FILE = "tests/governance/test_govb49_path_grant.py"
_B49_CLOSURE_SELECTORS = (
    "test_v12_body_has_no_skip_escape",
    "test_v12_four_kinds_all_visited",
    "test_stamp_path_invalid_implementer_turns_red",
    "test_impl_path_works_for_every_cli_family",
    "test_dispatch_set_equals_review_families",
    "test_review_families_subset_of_eligible",
)
# 每格的**固定** receipt 契約（六格皆非參數化 ⇒ 各恰 1）。寫字面，不由集合長度導出。
_B49_CLOSURE_EXPECTED = {
    "test_v12_body_has_no_skip_escape": 1,
    "test_v12_four_kinds_all_visited": 1,
    "test_stamp_path_invalid_implementer_turns_red": 1,
    "test_impl_path_works_for_every_cli_family": 1,
    "test_dispatch_set_equals_review_families": 1,
    "test_review_families_subset_of_eligible": 1,
}


def _b49_selector_is_substantive(src: str, fn: str) -> bool:
    """具名 selector 是否**有實質斷言**（≥1 個 `assert` 或 `pytest.raises`）。

    〔`CODEX-R2-P0-01` 第二病；主委反向驗證實測命中〕
    把 selector 的 body 換成只剩 docstring，它照樣 `1 passed` ⇒ 只驗 rc/passed
    擋不住「掏空」。本函式以 AST 檢查該函式**自身**的 body。

    🔴 **誠實邊界**：`assert True` 仍會通過。本檢查只防**意外掏空與重構失手**，
    不防蓄意（SPEC §C-6 已具名排除；與整套 B-49 機制同一誠實邊界）。
    """
    import ast

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False

    # 🔴 只認**模組層**同名定義，且須恰好一個〔`CODEX-R3-P0-01` 探針 2〕：
    #    `ast.walk` 取到的是**第一個**，而 Python 實際生效的是**最後一個**
    #    ⇒ 「前面放真的、後面放空的」可騙過檢查。數量不等於 1 一律 fail-closed。
    defs = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn
    ]
    if len(defs) != 1:
        return False

    # 🔴 只看**自身可達 body**〔`CODEX-R3-P0-01` 探針 1〕：
    #    巢狀函式／類別／lambda 內的 assert 是死碼，不得充當實質性。
    def _own_nodes(node: ast.AST):
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
            ):
                continue
            yield child
            yield from _own_nodes(child)

    for sub in _own_nodes(defs[0]):
        if isinstance(sub, ast.Assert):
            return True
        if isinstance(sub, ast.With):
            for item in sub.items:
                call = item.context_expr
                if isinstance(call, ast.Call):
                    name = getattr(call.func, "attr", None) or getattr(
                        call.func, "id", None
                    )
                    if name == "raises":
                        return True
    return False


def _assert_b49_closure_evidence() -> None:
    """票 B-49 關票前提：六格閉合證據**逐格於實體隔離副本實跑**，各自驗 rc／passed／skipped。

    🔴 **不得寫成字面比對**（TODO Task 2.2「不可做」）：檔案裡有那六個函式名，
    不代表它們跑得過——`CODEX-R3-P1-01` 那型假綠正是「保留字面、實質失效」。

    🔴 **也不得用整檔 receipt 代替**〔`CODEX-R2-P0-01`／`GROK-R2-P1-01`〕：
    初版寫 `整檔 passed == 6`，而該檔加入 mutation 矩陣與 Task 3.2 後有 33 格
    ⇒ 條件**恆不成立**，關票路徑結構上不可達——主委親手造出自己正要修的那個死結。
    整檔 receipt 還有第二個病：**六格被替換成空測試也照樣綠**。
    ⇒ 改為逐格具名執行，缺 selector／逾時／snapshot 失敗一律 fail-closed。
    """
    assert len(_B49_CLOSURE_SELECTORS) == 6
    sel = REPO / _B49_CLOSURE_FILE
    assert sel.is_file(), f"閉合證據檔不存在：{_B49_CLOSURE_FILE} ⇒ 票不得 CLOSED"
    src = sel.read_text(encoding="utf-8")
    missing = [fn for fn in _B49_CLOSURE_SELECTORS if f"def {fn}(" not in src]
    assert not missing, f"閉合證據缺具名 selector（改名／刪除？）：{missing}"
    hollow = [fn for fn in _B49_CLOSURE_SELECTORS if not _b49_selector_is_substantive(src, fn)]
    assert not hollow, f"閉合證據 selector 被掏空（無任何斷言）：{hollow}"

    # 隔離工具的單一定義處＝證據檔本身；函式內 import 以免模組級循環相依
    import tempfile

    from tests.governance import test_govb49_path_grant as _ev

    tmp = Path(tempfile.mkdtemp(prefix="b49-closure-"))
    iso = _ev._make_iso(tmp)
    for fn in _B49_CLOSURE_SELECTORS:
        r = _ev._run_iso(iso, f"{_B49_CLOSURE_FILE}::{fn}")
        assert r["rc"] == 0, f"閉合證據 {fn} 未通過 ⇒ 票不得 CLOSED：\n{r['out'][-2000:]}"
        # 🔴 固定 receipt 契約〔`CODEX-R3-P0-01`〕：`>= 1` 太鬆——多塞一格或少跑一格都看不出來。
        want = _B49_CLOSURE_EXPECTED[fn]
        assert r["passed"] == want, (
            f"閉合證據 {fn} 應恰 {want} 格，得 {r['passed']}：\n{r['out'][-1200:]}"
        )
        assert r["skipped"] == 0, f"閉合證據 {fn} 不得有 skip，得 {r['skipped']}"


def test_b45_unfreeze_requires_roles_sot_closure() -> None:
    """🔴 定時炸彈：`_B45_HARNESS` 凍結一被解除／放寬，本測即紅。

    為什麼要炸彈：`票 B-49`（roles SoT 無法表達編排端自任、`:769` fail-open 假綠）
    **本 epic 內修不掉**——修它要動 `test_stamp_taskid_inject.py`，而該檔在
    `_B45_HARNESS` 內，`20260809-govb1-x-consult-r1` 裁決 (C) 維持凍結。
    若只寫進 HANDOFF／backlog，就是**靠記憶**，使用者 2026-08-02 已定死不准。

    引信＝凍結本身。凍結仍在 ⇒ 本測通過（時候未到）；
    凍結一解除／放寬 ⇒ 除非票 B-49 已 CLOSED，否則**紅**，pre-push 當場擋。

    🔴 **字面關閉條件**（composer Q2 要求，缺一不可）：
      ① `test_stamp_taskid_inject.py:769` 之 `pytest.skip` 改為 fail-closed
      ② invalid mutation 轉紅 ＋ 三個合法 implementer 值通過 ＋ 該檔 `skipped=0`
      ③ `eligible` 與測試內家族集合機械連動
      ④ 票 B-49 之 `TICKET-STATUS` 改為 `CLOSED`
    ⇒ 本測只機械驗 ④（前三項是 ④ 的前提，由該票之非實作者覆核把關）。

    誠實邊界：兩家委員皆判此炸彈**只防意外與遺忘，不防蓄意**——
    主委對本檔有寫入權，可連炸彈一併改掉。與任何 waiver 測試同型。
    """
    status = _b49_ticket_status()
    assert status != "MISSING", (
        f"票 {_B49_ID} 不在 {_B49_TICKET} ⇒ 炸彈失去標的（票被刪或改名？）"
    )
    if _b45_freeze_still_active():
        if status == "CLOSED":
            # 🔴 Task 2.2（狀態機 R-A）：B-49 的修法**只解凍三檔**，另兩檔設計上維持凍結
            #    ⇒ 引信恆為 active。若沿用「凍結期間一律不得關票」，這張票**永遠關不掉**
            #    （狀態機無可達終態，是 r3／r6 之後第四個同型死結）。
            #    改為：凍結期間允許 CLOSED，但**必須**附閉合證據——且是**實跑**，非字面。
            _assert_b49_closure_evidence()
            return
        assert status == "OPEN", (
            f"凍結仍生效但票已 {status}——B-49 之修法須動 _B45_HARNESS，"
            "不可能在凍結期間真正完成。請確認不是提早關票。"
        )
        return
    assert status == "CLOSED", (
        f"🔴 `_B45_HARNESS` 凍結已解除／放寬，但票 {_B49_ID} 仍為 {status}。\n"
        "解凍是 B-49 唯一的施工窗口——現在不做就沒有下一個引信了。\n"
        "關閉條件（缺一不可）：① :769 改 fail-closed ② mutation 轉紅 + skipped=0\n"
        "③ eligible 與測試家族集合機械連動 ④ 本票 TICKET-STATUS 改 CLOSED"
    )


def test_b45_bomb_cannot_be_defused_by_skip() -> None:
    """耦合：炸彈**不得**用 skip 拆除〔比照 `test_waiver_b5_active_when_b5_start_anchored`〕。

    composer Q2：「否則只是延後爆炸、可被 skip 拆掉」。
    本測直接讀炸彈函式原文，確認它沒有任何 `pytest.skip`／`return` 早退以外的
    逃生路徑，且**引信與斷言都還在**。
    """
    src = (REPO / "tests" / "governance" / "test_govb1_contract_matrix.py").read_text(
        encoding="utf-8"
    )
    m = re.search(
        r"^def test_b45_unfreeze_requires_roles_sot_closure\(.*?(?=\n@|\ndef |\Z)",
        src, re.S | re.M,
    )
    assert m, "炸彈函式不見了（被拆？）"
    body = _strip_docstring_and_comments(m.group(0))
    assert "pytest.skip" not in body, "🔴 炸彈被 skip 拆除（skip 是 fail-open）"
    assert "_b45_freeze_still_active()" in body, "🔴 引信被拿掉（不再偵測解凍）"
    assert 'status == "CLOSED"' in body, "🔴 解凍後的關票斷言被拿掉"

    # 🔴 引信本身**不得**退回字面比對〔CODEX-R3-P1-01 假綠／COMPOSER-R3-P2-01 假紅〕
    fm = re.search(
        r"^def _b45_freeze_still_active\(.*?(?=\n@|\ndef |\Z)", src, re.S | re.M
    )
    assert fm, "引信函式不見了"
    fuse = _strip_docstring_and_comments(fm.group(0))
    assert "assert not hit_harness" not in fuse, (
        "🔴 引信退回字面比對：`hit_harness = set()` 可保留字面而實質失效（假綠），"
        "無辜重構又會誤判解凍（假紅）。引信須**實跑守衛**。"
    )
    assert "_fake_run" in fuse and "AssertionError" in fuse, (
        "🔴 引信不再實跑守衛（須以假 diff 餵入並檢查是否真的拒絕）"
    )


def _strip_docstring_and_comments(fn_src: str) -> str:
    """去掉函式的 docstring 與 `#` 註解，只留程式碼行（供「證明缺席」類斷言用）。"""
    out, in_doc = [], False
    for ln in fn_src.splitlines():
        s = ln.strip()
        if in_doc:
            if s.endswith('"""') or s.endswith("'''"):
                in_doc = False
            continue
        if s.startswith('"""') or s.startswith("'''"):
            # 單行 docstring（開頭結尾同一行且長度>3）⇒ 不進入多行模式
            if not (len(s) > 5 and (s.endswith('"""') or s.endswith("'''"))):
                in_doc = True
            continue
        if s.startswith("#"):
            continue
        out.append(ln)
    return "\n".join(out)


def test_waiver_guards_never_parse_commit_message() -> None:
    """🔴 窗守衛**不得**解析 commit 訊息 ⇒ OOE trailer 在此**無效**〔C1 裁決〕。

    codex `CODEX-R1-P0-01` [BLOCKING]：G-7 的 scope 豁免與窗守衛的 oracle 凍結
    目的不同。若用一行自宣告 trailer 統一兩者，同一 commit 就能同批改
    **驗證治理機器的 oracle** 與**被驗的機器本身**，當輪綠燈即失去證據力。

    本測釘住「不讀訊息」這個**不變式本身**——不是釘實作長相：
    三個窗守衛函式內出現任何 commit-message 解析痕跡即紅。
    這是「證明缺席」，源碼層是正確的 oracle（行為層無法窮舉證明不存在）。
    """
    src = (REPO / "tests" / "governance" / "test_govb1_contract_matrix.py").read_text(
        encoding="utf-8"
    )
    for fn in _WAIVER_GUARD_FNS:
        m = re.search(rf"^def {re.escape(fn)}\(.*?(?=\n@|\ndef |\Z)", src, re.S | re.M)
        assert m, f"找不到窗守衛 {fn}（refactor?→須更新本測）"
        # 🔴 只掃**程式碼行**：docstring 與註解本來就會寫「禁 --grep」之類的字樣，
        #   連文件一起掃會把「說明不准用」誤判成「用了」（與 gov_check 那次同型）。
        body = _strip_docstring_and_comments(m.group(0))
        hits = [k for k in _MSG_PARSE_MARKERS if k in body]
        assert not hits, (
            f"{fn} 出現 commit 訊息解析痕跡 {hits}\n"
            "🔴 窗守衛認 OOE trailer ＝ 主委可單方面解除三家蓋章之凍結"
            "（20260808-GOVB1-B4-STAMP-R2）。要放寬須先取得新裁決。"
        )
        # 正向：仍以原始 path diff 為判準
        assert "--name-only" in body and "_B45_HARNESS" in body, (
            f"{fn} 已不再以原始 path diff 比對 _B45_HARNESS（保護真空？）"
        )


def test_ooe_comment_doc_smoke_not_behavior_guarantee() -> None:
    """🔴 **文件 smoke check，非行為保證**〔`CODEX-R3-P2-05` 具名〕。

    codex 判定成立：本測比對的是**註解字串**，屬「用散文測散文」——
    把三道機制的敘述**互相錯置**但保留關鍵詞，本測仍會綠。
    主委接受此指正，**不宣稱它是語意 oracle**，改名以反映真實效力。

    真正的語意 oracle 是行為層測試，不是這一條：
      ① 「窗守衛不讀 trailer」→ `test_waiver_guards_never_parse_commit_message`
      ② 「G-7 排除五檔」→ `test_ooe_hard_protected_set_is_frozen`
      ③ 「pytest 非來源保證」→ **無行為 oracle**（要證明它須比對凍結基準，
         而那正是 `票 B-49` 解凍後才做得到的事）⇒ **具名殘留**。

    本測仍保留的價值：擋住「整段誤導文字原封不動回歸」這一種**退化**。
    更強判準（codex 建議：三個具名機制 clause 的 exact contract）**未採用**，
    理由＝那會把散文再鎖死一層，違反使用者「文字問題用白名單機械卡、
    別耗回合列舉」之定調；此處以誠實標示效力邊界取代。

    ── 以下為原始意圖（`CODEX-R1-P1-02`：舊文為誤導性文件）──

    舊文寫「五檔的真正守衛是 pre-push 全套 pytest（改壞即紅）」——**為假**：
    `pre-push` → `gov_check.sh` 只對當前 checkout 跑 pytest，不比對凍結基準，
    同批改 harness 與被測物即全綠。該錯誤前提正是主委當初把五檔排除
    G-7 硬保護的**唯一理由**，也是 composer 主張放寬窗守衛的依據①。
    """
    src = _gate_src()
    seg = src.split("out-of-epic 通道", 1)[1].split("_G7_OOE_HARD_PROTECTED=", 1)[0]
    assert "不讀 trailer" in seg or "不解析 commit 訊息" in seg, (
        "註解須明說窗守衛不讀 trailer（否則維護者會以為兩閘同語意）"
    )
    assert "不比對任何凍結基準" in seg or "≠ 來源不可變保證" in seg, (
        "註解須明說 pre-push pytest 不是來源不可變保證"
    )
    assert "改壞即紅" not in seg or "為假" in seg, (
        "🔴 註解仍宣稱「改壞即紅」而未標為假 ⇒ 誤導性文件回歸"
    )


def test_ooe_grandfather_set_is_frozen_and_closed() -> None:
    """grandfather 為**字面凍結封閉集**，恰 2 筆；shell 端漂移或增長即紅。

    為何存在（2026-08-09 裁定）：正解的第 ③ 步是改寫**非 HEAD** commit 訊息並
    force-push main——不可逆，且會使已引用的 sha 全數失效。使用者鐵律
    「面向未來不溯及既往」(2026-08-05) ⇒ 舊的兩筆以 sha 具名放行，新的一律走原生解析。
    此測是該例外的**唯一出口管制**：多加一筆就等於重新打開 `--grep` 後門。
    """
    src = _gate_src()
    m = re.search(r"_G7_OOE_GRANDFATHER='([^']*)'", src)
    assert m, "govb1_final_gate.sh 缺 _G7_OOE_GRANDFATHER 常數"
    shell_set = {ln.strip() for ln in m.group(1).splitlines() if ln.strip()}
    assert shell_set == set(_G7_OOE_GRANDFATHER), (
        f"grandfather 集漂移／增長：want={set(_G7_OOE_GRANDFATHER)} got={shell_set}\n"
        "🔴 新增例外須經委員裁定並同步本字面集合；預設答案是『不新增，改把 trailer 寫對』。"
    )
    assert len(shell_set) == 2, "grandfather 恰 2 筆（封閉集）"
    assert all(re.fullmatch(r"[0-9a-f]{40}", s) for s in shell_set), "須為完整 40 位 sha"


def test_ooe_uses_native_trailer_parsing_not_grep() -> None:
    """`_g7_ooe_commits` 須用 `%(trailers:...)`，**不得**用 `--grep`〔CODEX-R1-P1-02〕。"""
    src = _gate_src()
    m = re.search(r"_g7_ooe_commits\(\) \{.*?\n\}", src, re.S)
    assert m, "找不到 _g7_ooe_commits（refactor?→須更新本測）"
    body = m.group(0)
    assert "%(trailers:key=Governance-Scope" in body, (
        "須用 git 原生 trailer 解析（只認訊息最後一段）"
    )
    assert "--grep" not in body, (
        "禁 --grep：它匹配訊息任何位置 ⇒ body 中段／引用的舊訊息亦被誤判為豁免"
    )


def _git(cwd: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", *args],
        cwd=cwd, capture_output=True, text=True, check=True,
    )
    return p.stdout


def test_ooe_body_mention_does_not_grant_exemption(tmp_path: Path) -> None:
    """🔴 行為層可證偽：把**生產程式碼原文**跑在受控 repo 上，驗四種訊息形態之選取結果。

    R-18 之洞：`--grep` 匹配訊息**任何位置**，故 body 中段、或**引用前一則 commit
    訊息**（本專案訊息經常這麼寫）內之同形字串，都會讓該 commit 取得豁免。
    本測建臨時 repo，取 `govb1_final_gate.sh` 內 `_g7_ooe_commits` 的**函式原文**
    （連同兩個常數）重跑，只把 `_base` 換成臨時 repo 的 base ⇒ 驗的是真碼，不是複製品。

    mutation 反例：把該函式改回 `git log --grep=...` ⇒ `body 中段` 與 `引用舊訊息`
    兩筆會被選入，斷言的集合相等當場失敗。
    """
    src = _gate_src()
    fn = re.search(r"_g7_ooe_commits\(\) \{.*?\n\}", src, re.S)
    val = re.search(r"_G7_OOE_VALUE_RE='[^']*'", src)
    gf = re.search(r"_G7_OOE_GRANDFATHER='[^']*'", src)
    sep = re.search(r"_G7_OOE_MULTI_SEP=\$'[^']*'", src)
    assert fn and val and gf and sep, "找不到 _g7_ooe_commits／常數（refactor?→須更新本測）"

    r, base, shas = _build_ooe_probe_repo(tmp_path)

    snippet = (
        f"{val.group(0)}\n{gf.group(0)}\n{sep.group(0)}\n"
        f"_base() {{ printf '%s' {base}; }}\n"
        f"{fn.group(0)}\n_g7_ooe_commits\n"
    )
    p = subprocess.run(["bash", "-c", snippet], cwd=r, capture_output=True, text=True, check=False)
    assert p.returncode == 0, f"_g7_ooe_commits 執行失敗: {p.stderr}"
    got = {ln.strip() for ln in p.stdout.splitlines() if ln.strip()}
    selected = {n for n, s in shas.items() if s in got}

    assert selected == {"ok_trailer", "tab_subject"}, (
        f"選取結果錯誤：want={{'ok_trailer','tab_subject'}} got={selected}\n"
        "body_middle／quoted_prev 被選中 ⇒ 退回 --grep 語意（R-18 未修）；\n"
        "dup_valid_first 被選中 ⇒ 重複 key 未拒（CODEX-R2-P1-02 未修）；\n"
        "ok_trailer 未被選中 ⇒ 慣例（trailer 與 Co-Authored-By 同段）被破壞。\n"
        f"stdout={p.stdout}"
    )
    # grandfather 恆輸出（不在此 repo 內故無害）——確認它沒被順手拿掉
    assert set(_G7_OOE_GRANDFATHER) <= got, "grandfather 未被輸出（例外集被移除？）"


def _build_ooe_probe_repo(tmp_path: Path) -> tuple[Path, str, dict[str, str]]:
    """建臨時 repo，每種 commit 訊息形態各一筆。回 (repo, base_sha, {形態: sha})。"""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "a.txt").write_text("0\n", encoding="utf-8")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-q", "-m", "base")
    base = _git(r, "rev-parse", "HEAD").strip()

    TRAILER = "Governance-Scope: out-of-epic 理由"
    COAUTH = "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
    cases = {
        # 合法：trailer 與 Co-Authored-By 同段（本專案慣例）
        "ok_trailer": f"subject\n\nbody\n\n{TRAILER}\n{COAUTH}\n",
        # 🔴 洞：同形字串出現在 body 中段（後面還有別的段落）
        "body_middle": f"subject\n\n{TRAILER}\n\nbody 後續說明\n\n{COAUTH}\n",
        # 🔴 洞：引用前一則 commit 訊息（本專案訊息經常整段引用）。
        #   刻意**不縮排**——縮排版兩種實作都會拒（`^` 對不上），沒有鑑別力。
        "quoted_prev": f"subject\n\n前一則寫的是：\n{TRAILER}\n——本則並非 out-of-epic\n\n{COAUTH}\n",
        # 值不符：結尾界線須擋掉 -extra
        "value_extra": f"subject\n\nbody\n\nGovernance-Scope: out-of-epic-extra\n{COAUTH}\n",
        # 🔴 重複 key，**首項合法**〔CODEX-R2-P1-02〕：同一 commit 同時宣告
        #   out-of-epic 與另一矛盾 scope。前版只比對串接後的首項 ⇒ 誤放行。
        "dup_valid_first": f"subject\n\nbody\n\n{TRAILER}\nGovernance-Scope: b3-task\n{COAUTH}\n",
        # 重複 key，首項不合法 ⇒ 兩版皆拒（列出以示對稱，非鑑別用例）
        "dup_invalid_first": f"subject\n\nbody\n\nGovernance-Scope: b3-task\n{TRAILER}\n{COAUTH}\n",
        # subject 含 tab（稽核清單解析用；此處確認不影響閘的選取）
        "tab_subject": f"subject\twith\ttab\n\nbody\n\n{TRAILER}\n{COAUTH}\n",
        # 無 trailer
        "plain": f"subject\n\nbody\n\n{COAUTH}\n",
    }
    shas = {}
    for name, msg in cases.items():
        (r / "a.txt").write_text(name + "\n", encoding="utf-8")
        _git(r, "add", "a.txt")
        (tmp_path / "msg.txt").write_text(msg, encoding="utf-8")
        _git(r, "commit", "-q", "-F", str(tmp_path / "msg.txt"))
        shas[name] = _git(r, "rev-parse", "HEAD").strip()
    return r, base, shas


def test_ooe_audit_list_behavioral_parity_with_gate(tmp_path: Path) -> None:
    """🔴 行為層等價〔CODEX-R2-P2-03〕：稽核清單選出的 commit 集合須**恰等於**閘的。

    源碼比對（`test_ooe_audit_list_matches_gate`）擋不住這一類：前版
    `gov_check.sh` 把自由文字的 `%s` 放在 trailer **之前**再取 `$3`，
    subject 含 tab 的 commit 便整筆漏列——閘放行、稽核看不見，正好是
    「非靜默旁路」這個設計目標的反面。codex 實測 `tab_subject` 出現此落差。

    本測把兩邊的解析**原文**各自跑在同一個受控 repo 上，比對選出的 sha 集合。
    mutation 反例：把 gov_check 的 format 改回 `%h\\t%s\\t<trailers>` 並取 `$3`
    ⇒ `tab_subject` 只出現在閘側，集合不等 ⇒ 紅。
    """
    r, base, shas = _build_ooe_probe_repo(tmp_path)

    gate = _gate_src()
    fn = re.search(r"_g7_ooe_commits\(\) \{.*?\n\}", gate, re.S)
    val = re.search(r"_G7_OOE_VALUE_RE='[^']*'", gate)
    sep = re.search(r"_G7_OOE_MULTI_SEP=\$'[^']*'", gate)
    assert fn and val and sep, "找不到閘側解析原文（refactor?→須更新本測）"
    gate_snippet = (
        f"{val.group(0)}\n{sep.group(0)}\n_G7_OOE_GRANDFATHER=''\n"
        f"_base() {{ printf '%s' {base}; }}\n{fn.group(0)}\n_g7_ooe_commits\n"
    )
    gp = subprocess.run(["bash", "-c", gate_snippet], cwd=r, capture_output=True, text=True, check=False)
    assert gp.returncode == 0, f"閘側執行失敗: {gp.stderr}"
    gate_sel = {n for n, s in shas.items() if s in gp.stdout.split()}

    # 稽核側：抽 gov_check.sh 的 `_ooe_raw=`／`_ooe_list=` 兩段賦值原文
    gov = (REPO / "scripts" / "gov_check.sh").read_text(encoding="utf-8")
    raw = re.search(r"_ooe_raw=\"\$\(git log --format=.*?\)\"", gov, re.S)
    lst = re.search(r"_ooe_list=\"\$\(printf.*?\)\"\n", gov, re.S)
    assert raw and lst, "找不到稽核側解析原文（refactor?→須更新本測）"
    gov_snippet = (
        f'_ooe_base={base}\n'
        + raw.group(0).replace('"${_ooe_base}..HEAD"', f'{base}..HEAD')
        + "\n" + lst.group(0)
        + 'printf "%s\\n" "${_ooe_list}"\n'
    )
    vp = subprocess.run(["bash", "-c", gov_snippet], cwd=r, capture_output=True, text=True, check=False)
    assert vp.returncode == 0, f"稽核側執行失敗: {vp.stderr}\n{gov_snippet}"
    short = {n: s[:7] for n, s in shas.items()}
    gov_sel = {n for n, s in short.items() if any(ln.startswith(s) for ln in vp.stdout.splitlines())}

    assert gate_sel == gov_sel, (
        f"稽核清單與閘不等價：gate={gate_sel} audit={gov_sel}\n"
        "差集在 audit 側 ⇒ 已豁免路徑看不見（靜默旁路）；在 gate 側 ⇒ 稽核誤報。\n"
        f"gate_stdout={gp.stdout}\naudit_stdout={vp.stdout}"
    )
    assert gate_sel == {"ok_trailer", "tab_subject"}, f"基準錯：{gate_sel}"


def test_ooe_audit_list_matches_gate() -> None:
    """`gov_check.sh` 的稽核清單須與閘的實際豁免集**同法**，否則稽核會誤導。

    稽核清單若比閘寬（如沿用 `--grep`），使用者會看到「已豁免」但閘其實沒放行的
    commit；若比閘窄，真正被豁免的 commit 就成了靜默旁路。兩個方向都不可接受。
    """
    gov = (REPO / "scripts" / "gov_check.sh").read_text(encoding="utf-8")
    gate = _gate_src()
    raw_block = gov.split("0b)", 1)[1].split("--- 1)", 1)[0]
    # 只看功能行：註解裡本來就會提到 `--grep`（說明為何不用它）
    ooe_block = "\n".join(
        ln for ln in raw_block.splitlines() if not ln.lstrip().startswith("#")
    )
    assert "%(trailers:key=Governance-Scope" in ooe_block, "稽核清單須用原生 trailer 解析"
    assert "--grep" not in ooe_block, "稽核清單禁 --grep（會比閘寬）"
    # 值判準逐字一致
    gate_re = re.search(r"_G7_OOE_VALUE_RE='([^']*)'", gate).group(1)
    assert gate_re in ooe_block, f"gov_check 之值判準與閘不一致（閘為 {gate_re}）"
    # grandfather 兩筆 sha 須同時出現在稽核清單側
    for sha in _G7_OOE_GRANDFATHER:
        assert sha in ooe_block, f"稽核清單漏列 grandfather {sha[:7]}"


def test_frozen_hashes_closed_key_rejects_duplicate_and_third() -> None:
    """封閉 key 集合之負向用例〔CODEX-R2-P1-03；B4-REVIEW-R1 CODEX-R1-P1-01 修正〕。

    🔴 **禁用 try/except AssertionError ＋ 自拋 sentinel** 的寫法：
    該寫法會**接住自己拋的 sentinel**，守衛被移除後 sentinel 訊息仍含關鍵字
    ⇒ 測試照樣綠（codex 於隔離 clone 實證：移除 duplicate guard 後仍 `1 passed`）。
    一律用 `pytest.raises(AssertionError, match=...)`，讓「沒有拋例外」直接轉紅。
    """
    good = FROZEN.read_text(encoding="utf-8")
    _parse_frozen_hashes(good)  # 現行檔須可解析

    sha_a = "a" * 40
    # 用例基底一律去掉所有批次錨點（b3 除外），使本測不受「哪些錨點已寫入」影響
    base3 = (
        "\n".join(
            ln
            for ln in good.splitlines()
            if ln.strip()
            and not any(
                ln.startswith(f"{k}: ") for k in _FROZEN_ANCHOR_KEYS if k != "b3_start"
            )
        )
        + "\n"
    )

    # 反向：重複 key
    dup = base3.rstrip("\n") + "\nb3_start: " + sha_a + "\n"
    with pytest.raises(AssertionError, match="重複"):
        _parse_frozen_hashes(dup)

    # 反向：未知 key（非批次錨點命名）
    third = base3.rstrip("\n") + "\nthird: deadbeef\n"
    with pytest.raises(AssertionError, match="未知|非法"):
        _parse_frozen_hashes(third)

    # 正向：b4_start 為合法可選錨點 ⇒ 通過
    with_b4 = base3.rstrip("\n") + "\nb4_start: " + sha_a + "\n"
    assert _parse_frozen_hashes(with_b4)["b4_start"] == sha_a

    # 正向：錨鏈連續（b3→b4→b5）⇒ 通過；證明 B5 開工**不必再改 parser**
    with_b5 = with_b4.rstrip("\n") + "\nb5_start: " + ("c" * 40) + "\n"
    assert _parse_frozen_hashes(with_b5)["b5_start"] == "c" * 40

    # 反向：封閉集仍封閉——b11_start 超出 B3–B10 之列舉範圍
    eleventh = with_b4.rstrip("\n") + "\nb11_start: " + sha_a + "\n"
    with pytest.raises(AssertionError, match="未知|非法"):
        _parse_frozen_hashes(eleventh)

    # 反向：錨鏈跳號——有 b5_start 卻無 b4_start
    gap = base3.rstrip("\n") + "\nb5_start: " + sha_a + "\n"
    with pytest.raises(AssertionError, match="連續無跳號"):
        _parse_frozen_hashes(gap)

    # 反向：重複 b4_start
    dup4 = with_b4.rstrip("\n") + "\nb4_start: " + ("b" * 40) + "\n"
    with pytest.raises(AssertionError, match="重複"):
        _parse_frozen_hashes(dup4)

    # 反向：錨鏈斷裂——有 b4_start 卻無 b3_start（歷史樹情境亦須 fail-closed）
    no_b3 = (
        "\n".join(
            ln for ln in with_b4.splitlines() if not ln.startswith("b3_start: ")
        )
        + "\n"
    )
    with pytest.raises(AssertionError, match="連續無跳號"):
        _parse_frozen_hashes(no_b3, require_b3_start=False)

    # 反向：錨點值須為 40 hex
    bad_len = base3.rstrip("\n") + "\nb4_start: deadbeef\n"
    with pytest.raises(AssertionError, match="40 hex"):
        _parse_frozen_hashes(bad_len)
