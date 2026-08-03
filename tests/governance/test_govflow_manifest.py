"""Phase 0 — gen_govflow_manifest.sh 驗收（Task 0.1）。

Test ID 與 docs/GOV_DISPATCH_FLOW_FIX_TODO.md Phase 0 測試表一一對應。
探針一律用 .claude/tmp/ 下隔離副本；禁直接變異 repo 內 scripts/** 或 tests/**。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GEN_SCRIPT = REPO_ROOT / "scripts" / "gen_govflow_manifest.sh"
TODO_PATH = REPO_ROOT / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md"
ISO_ROOT = REPO_ROOT / ".claude" / "tmp"

# phase-base.tsv schema（G-MANIFEST consumer 契約）
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_ISO8601_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_PHASE_N_OK = frozenset({"0", "1", "2", "3", "4"})


def _run_gen(
    cwd: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """執行生成器；rc 直接取，不經 pipe。"""
    cmd = ["bash", str(cwd / "scripts" / "gen_govflow_manifest.sh"), *args]
    # 若 isolation 內已有腳本副本，用副本；否則用 repo 腳本但 cwd=isolation
    local = cwd / "scripts" / "gen_govflow_manifest.sh"
    if local.is_file():
        cmd = ["bash", str(local), *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=env or os.environ.copy(),
    )


def _manifest_rows(stdout: str) -> list[str]:
    return [ln for ln in stdout.splitlines() if ln.strip() and "|" in ln]


def _iso_tree(label: str) -> Path:
    """在 .claude/tmp/ 建隔離複製樹（scripts + tests/governance + TODO + handoffs）。"""
    ISO_ROOT.mkdir(parents=True, exist_ok=True)
    dest = ISO_ROOT / f"govflow_b0_{label}_{int(time.time() * 1000)}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    # scripts
    shutil.copytree(
        REPO_ROOT / "scripts",
        dest / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    # tests/governance
    (dest / "tests").mkdir()
    shutil.copytree(
        REPO_ROOT / "tests" / "governance",
        dest / "tests" / "governance",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    # TODO
    (dest / "docs").mkdir()
    shutil.copy2(TODO_PATH, dest / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md")
    # handoffs（--record-base 用）
    (dest / "handoffs").mkdir()
    # 最小 git 以便 --record-base 的 rev-parse；無則略（預設模式不需）
    subprocess.run(
        ["git", "init"],
        cwd=str(dest),
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "config", "user.email", "govflow-b0@test.local"],
        cwd=str(dest),
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "config", "user.name", "govflow-b0"],
        cwd=str(dest),
        capture_output=True,
        check=False,
    )
    # 至少一個 commit 讓 rev-parse HEAD 可用
    subprocess.run(
        ["git", "add", "-A"],
        cwd=str(dest),
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "commit", "-m", "iso", "--allow-empty"],
        cwd=str(dest),
        capture_output=True,
        check=False,
    )
    return dest


def _cleanup_iso(path: Path) -> None:
    if path.exists() and path.is_relative_to(ISO_ROOT):
        shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# T0-U1 — 生成器 rc==0 且輸出非空
# ---------------------------------------------------------------------------
def test_t0_u1_generator_rc0_nonempty() -> None:
    """T0-U1: 生成器 rc==0 且輸出非空。"""
    proc = _run_gen(REPO_ROOT)
    assert proc.returncode == 0, (
        f"T0-U1 expected rc==0, got {proc.returncode}; stderr={proc.stderr!r}"
    )
    rows = _manifest_rows(proc.stdout)
    assert rows, "T0-U1 expected non-empty manifest"


# ---------------------------------------------------------------------------
# T0-B1 — C 類缺檔時標 MISSING 而非跳過
# ---------------------------------------------------------------------------
def test_t0_b1_c_missing_listed() -> None:
    """T0-B1: C 類缺檔時標 MISSING 而非跳過。"""
    proc = _run_gen(REPO_ROOT)
    assert proc.returncode == 0, proc.stderr
    rows = _manifest_rows(proc.stdout)
    # _role_gate.sh 尚未建立（Phase 3）→ 必須列出且 MISSING
    hit = [r for r in rows if r.startswith("scripts/_role_gate.sh|")]
    assert len(hit) == 1, f"C 類 _role_gate.sh 必須列出: {hit}"
    parts = hit[0].split("|")
    assert parts[3] == "MISSING", f"缺檔應標 MISSING，得 {parts[3]}"


# ---------------------------------------------------------------------------
# T0-B2 — pattern 命中 0 筆 ⇒ 非零離開
# ---------------------------------------------------------------------------
def test_t0_b2_zero_a_hits_nonzero() -> None:
    """T0-B2: A 類 pattern 命中 0 筆 ⇒ 非零離開。

    變異路徑（封閉「只匹配自身仍綠」假綠口）：
    1) 把 A_PATTERN 改成「執行期拼接」的 never-match token
       （完整 token 不落在任何 source 字面量 → 不會被 grep 掃到自身／測試檔）
    2) grep 加 --exclude=gen_govflow_manifest.sh，排除 $自身
    → 實質 0 命中 ⇒ 生成器必須非零。

    若只把 pattern 改成字面 never-match 卻不排除自身／不拆字面量，
    腳本或本測檔會假命中 → rc=0 假綠（composer M16）。
    """
    iso = _iso_tree("b2")
    try:
        script = iso / "scripts" / "gen_govflow_manifest.sh"
        text = script.read_text(encoding="utf-8")
        old_pat = (
            "A_PATTERN='completeness_check|result_state|"
            "committee_process_exempt|STAMP-MODE'"
        )
        # 執行期拼接：完整 token 不出現在任何檔案字面量中
        new_pat = (
            'A_PATTERN="ZZZZ_GOVFLOW_T0B2_"$(printf %s NEVER_MATCH_0HITS)'
        )
        assert old_pat in text, "找不到 A_PATTERN 定義"
        text = text.replace(old_pat, new_pat, 1)
        old_grep = 'grep -rlE "${A_PATTERN}" scripts tests/governance'
        new_grep = (
            'grep -rlE --exclude=gen_govflow_manifest.sh '
            '"${A_PATTERN}" scripts tests/governance'
        )
        assert old_grep in text, "找不到 A 類 grep 指令"
        text = text.replace(old_grep, new_grep, 1)
        script.write_text(text, encoding="utf-8")
        proc = _run_gen(iso)
        assert proc.returncode != 0, (
            f"T0-B2: pattern 0 命中應非零，got rc={proc.returncode} "
            f"out={proc.stdout!r} err={proc.stderr!r}"
        )
        assert "0 筆" in proc.stderr or "pattern" in proc.stderr.lower()
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# T0-N1 — 刪一個 B-only 項 ⇒ 列數少 1
# 探針：gov_check.sh（B-only；禁用 doc_format_precheck — 它在 A∩B）
# ---------------------------------------------------------------------------
def test_t0_n1_remove_b_only_decrements_count() -> None:
    """T0-N1: 從 B 表刪 gov_check.sh（B-only）⇒ 列數少 1。"""
    iso = _iso_tree("n1")
    try:
        base = _run_gen(iso)
        assert base.returncode == 0, base.stderr
        base_n = len(_manifest_rows(base.stdout))

        script = iso / "scripts" / "gen_govflow_manifest.sh"
        text = script.read_text(encoding="utf-8")
        # 從 B 固定表刪除 gov_check.sh 一行
        mutated = text.replace("scripts/gov_check.sh\n", "")
        assert mutated != text, "mutation 未生效（B 表找不到 gov_check.sh）"
        # 同步從 PHASE_MAP 移除，否則反向收斂／未映射檢查會先炸（我們要測的是列數）
        # 但若仍留在 PHASE_MAP 且 phases=2，反向守衛會因不在 BCD 而失敗。
        # T0-N1 語意＝刪 B-only 項使聯集少 1；一併從 PHASE_MAP_KEYS 與 phase_of 拿掉。
        mutated = mutated.replace("scripts/gov_check.sh)                            echo \"2\" ;;\n", "")
        mutated = mutated.replace("scripts/gov_check.sh\n", "")
        script.write_text(mutated, encoding="utf-8")

        proc = _run_gen(iso)
        assert proc.returncode == 0, (
            f"T0-N1 mutation 後生成器應仍可跑（只少 B 項）; rc={proc.returncode} stderr={proc.stderr!r}"
        )
        new_n = len(_manifest_rows(proc.stdout))
        assert new_n == base_n - 1, (
            f"T0-N1: 刪 B-only 後列數應 {base_n}-1={base_n - 1}，得 {new_n}"
        )
        # 確認 gov_check 不再出現
        assert not any(
            r.startswith("scripts/gov_check.sh|") for r in _manifest_rows(proc.stdout)
        )
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# T0-N2 — 隔離副本新增含 result_state 的檔 ⇒ 列數多 1
# ---------------------------------------------------------------------------
def test_t0_n2_new_a_hit_increments_count() -> None:
    """T0-N2: 於隔離副本新增含 result_state 的檔 ⇒ 列數多 1。"""
    iso = _iso_tree("n2")
    try:
        base = _run_gen(iso)
        assert base.returncode == 0, base.stderr
        base_n = len(_manifest_rows(base.stdout))

        probe = iso / "scripts" / "_govflow_probe_result_state.sh"
        probe.write_text(
            "#!/usr/bin/env bash\n# probe for T0-N2\n# result_state=success\n",
            encoding="utf-8",
        )
        proc = _run_gen(iso)
        assert proc.returncode == 0, proc.stderr
        new_n = len(_manifest_rows(proc.stdout))
        assert new_n == base_n + 1, (
            f"T0-N2: 新增 A 命中檔後列數應 {base_n}+1={base_n + 1}，得 {new_n}"
        )
        hit = [
            r
            for r in _manifest_rows(proc.stdout)
            if "scripts/_govflow_probe_result_state.sh|" in r
        ]
        assert len(hit) == 1
        parts = hit[0].split("|")
        assert parts[1] == "-", f"純 A 旁觀者 phases 應為 -，得 {parts[1]}"
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# T0-C1 — cx_run.sh phases 為 2,3
# ---------------------------------------------------------------------------
def test_t0_c1_cx_run_phases_2_3() -> None:
    """T0-C1: scripts/cx_run.sh 的 phases 欄為 2,3。"""
    proc = _run_gen(REPO_ROOT)
    assert proc.returncode == 0, proc.stderr
    hit = [r for r in _manifest_rows(proc.stdout) if r.startswith("scripts/cx_run.sh|")]
    assert len(hit) == 1, hit
    phases = hit[0].split("|")[1]
    assert phases == "2,3", f"T0-C1 expected phases=2,3 got {phases!r}"


# ---------------------------------------------------------------------------
# T0-C2 — A 類未映射 ⇒ phases=-（不是 0），且非零離開不適用
# ---------------------------------------------------------------------------
def test_t0_c2_a_unmapped_bystander() -> None:
    """T0-C2: A 類命中但不在 PHASE_MAP ⇒ phases=-，rc==0。"""
    proc = _run_gen(REPO_ROOT)
    assert proc.returncode == 0, proc.stderr
    # audit_append.sh 為純 A 類（不在 PHASE_MAP 具名表）
    hit = [
        r for r in _manifest_rows(proc.stdout) if r.startswith("scripts/audit_append.sh|")
    ]
    assert len(hit) == 1, f"A 類 audit_append 應列出: {hit}"
    phases = hit[0].split("|")[1]
    assert phases == "-", f"旁觀者 phases 應為 -（不是 0），得 {phases!r}"


# ---------------------------------------------------------------------------
# T0-N3 — D 類 fail-closed：修改檔案欄插入未映射 path ⇒ 非零
# ---------------------------------------------------------------------------
def test_t0_n3_d_unmapped_failclosed() -> None:
    """T0-N3: 於隔離副本 Task 修改檔案欄插入不在 PHASE_MAP 的 path ⇒ 非零。"""
    iso = _iso_tree("n3")
    try:
        todo = iso / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md"
        text = todo.read_text(encoding="utf-8")
        # 在第一個「修改檔案」bullet 後插入一個幽靈 path
        needle = "- **修改檔案**：新建 `scripts/gen_govflow_manifest.sh`（無既有 caller）。"
        insert = (
            needle
            + "\n  另含 `scripts/_govflow_d_unmapped_probe.sh`（T0-N3 探針，不在 PHASE_MAP）。"
        )
        assert needle in text, "找不到 Task 0.1 修改檔案錨點"
        todo.write_text(text.replace(needle, insert, 1), encoding="utf-8")

        proc = _run_gen(iso)
        assert proc.returncode != 0, (
            f"T0-N3: D 類未映射應非零，got rc=0 out={proc.stdout!r}"
        )
        assert "未映射" in proc.stderr or "PHASE_MAP" in proc.stderr
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# T0-N4 — D 類優先於 A：拿掉 audit_events.json 的 PHASE_MAP ⇒ 非零
# ---------------------------------------------------------------------------
def test_t0_n4_d_priority_over_a() -> None:
    """T0-N4: 把 audit_events.json 從 PHASE_MAP 拿掉 ⇒ 非零，不得降級 phases=-。"""
    iso = _iso_tree("n4")
    try:
        script = iso / "scripts" / "gen_govflow_manifest.sh"
        text = script.read_text(encoding="utf-8")
        # 移除 phase_of 對 audit_events 的映射（變未映射）
        line = '    scripts/audit_events.json)                       echo "2" ;;\n'
        assert line in text, "找不到 audit_events PHASE_MAP 行"
        mutated = text.replace(line, "")
        # 也從 KEYS 列表移除（避免反向掃到空 phase_of）
        mutated = mutated.replace("scripts/audit_events.json\n", "")
        script.write_text(mutated, encoding="utf-8")

        proc = _run_gen(iso)
        assert proc.returncode != 0, (
            "T0-N4: 拿掉 D 類 PHASE_MAP 應非零，不得降級為旁觀者 rc=0"
        )
        # 確認不是「成功輸出 phases=-」
        rows = _manifest_rows(proc.stdout)
        soft = [r for r in rows if r.startswith("scripts/audit_events.json|-|")]
        assert not soft, f"T0-N4 不得降級為 phases=-: {soft}"
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# T0-N5 — 錨點完整性：刪「不可做」bullet ⇒ 非零
# ---------------------------------------------------------------------------
def test_t0_n5_anchor_integrity() -> None:
    """T0-N5: 隔離副本刪掉任一 Task 的「不可做」bullet ⇒ 生成器非零。"""
    iso = _iso_tree("n5")
    try:
        todo = iso / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md"
        text = todo.read_text(encoding="utf-8")
        # 刪 Task 0.1 的不可做行（保留其他 Task 錨點 → 計數失衡）
        target = "- **不可做**：不得把 `§M` 表格當成真相源；不得手寫任何列數。"
        assert target in text, "找不到 Task 0.1 不可做錨點"
        todo.write_text(text.replace(target, "", 1), encoding="utf-8")

        proc = _run_gen(iso)
        assert proc.returncode != 0, (
            f"T0-N5: 錨點失衡應非零，got rc=0 stderr={proc.stderr!r}"
        )
        assert "錨點" in proc.stderr or "完整性" in proc.stderr
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# T0-N6 — PHASE_MAP 反向收斂：旁觀者映射成數字 ⇒ 非零
# ---------------------------------------------------------------------------
def test_t0_n6_reverse_convergence() -> None:
    """T0-N6: 把純 A 旁觀者 audit_append.sh 映射成 2 ⇒ 非零。"""
    iso = _iso_tree("n6")
    try:
        script = iso / "scripts" / "gen_govflow_manifest.sh"
        text = script.read_text(encoding="utf-8")
        # 在 phase_of 加一條 audit_append → 2
        anchor = '    scripts/gate.sh)                                 echo "-" ;;\n'
        assert anchor in text
        injection = (
            anchor
            + '    scripts/audit_append.sh)                         echo "2" ;;\n'
        )
        mutated = text.replace(anchor, injection, 1)
        # 同步加入 PHASE_MAP_KEYS 讓反向掃描掃到
        keys_anchor = "scripts/gate.sh\n"
        mutated = mutated.replace(
            keys_anchor, keys_anchor + "scripts/audit_append.sh\n", 1
        )
        script.write_text(mutated, encoding="utf-8")

        proc = _run_gen(iso)
        assert proc.returncode != 0, (
            f"T0-N6: 反向收斂應非零，got rc=0 out={proc.stdout!r}"
        )
        assert "反向" in proc.stderr or "B∪C∪D" in proc.stderr or "BCD" in proc.stderr or "旁觀者" in proc.stderr
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# G-MANIFEST consumer（phase-base lookup）— 精確 schema，禁弱判準
# 契約：三欄 TSV、40-hex HEAD、ISO8601Z timestamp；缺列／壞 schema ⇒ FAIL
# ---------------------------------------------------------------------------
def _parse_phase_base_row(line: str) -> tuple[str, str, str] | None:
    """解析並驗證 phase-base 一列。schema 不合 ⇒ None（Gate 必須 FAIL）。"""
    cols = line.split("\t")
    if len(cols) != 3:
        return None
    n, sha, ts = cols[0], cols[1], cols[2]
    if n not in _PHASE_N_OK:
        return None
    if not _SHA40_RE.fullmatch(sha):
        return None
    if not _ISO8601_Z_RE.fullmatch(ts):
        return None
    return n, sha, ts


def _gmanifest_base_lookup(base_tsv: Path, phase_n: str) -> str | None:
    """真實 G-MANIFEST phase-base lookup。

    缺列、欄數錯、壞 SHA、壞 timestamp ⇒ None（呼叫端必須 Gate FAIL）。
    不得猜 parent、不得只檢查第 2 欄非空。
    """
    if not base_tsv.is_file():
        return None
    for line in base_tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        if not cols or cols[0] != phase_n:
            continue
        # 命中 Phase N 列：必須通過完整 schema，否則視為 FAIL
        parsed = _parse_phase_base_row(line)
        if parsed is None:
            return None
        return parsed[1]
    return None


def test_t0_c3_missing_phase_base_fails_gmanifest() -> None:
    """T0-C3: handoffs/govflow_phase_base.tsv 缺 Phase N 列 ⇒ G-MANIFEST(N) FAIL。

    同時鎖精確 schema：--record-base 寫入列必須為
    ``<N>\\t<40-hex>\\t<ISO8601Z>``；壞 schema 不得被 lookup 當成有效 base。
    """
    iso = _iso_tree("c3")
    try:
        base_tsv = iso / "handoffs" / "govflow_phase_base.tsv"
        # 確保沒有 Phase 1 列
        if base_tsv.exists():
            base_tsv.unlink()

        phase_n = "1"
        head = _gmanifest_base_lookup(base_tsv, phase_n)
        # 契約：缺列 ⇒ Gate FAIL（不得跳過、不得回退猜 parent）
        gmanifest_ok = head is not None
        assert not gmanifest_ok, (
            "T0-C3: 缺 Phase 1 base 時 G-MANIFEST 必須 FAIL，不得視為通過"
        )

        # 正向：--record-base 寫入後可取到，且 schema 嚴格合規
        rec = _run_gen(iso, "--record-base", phase_n)
        assert rec.returncode == 0, rec.stderr
        raw_lines = [
            ln
            for ln in base_tsv.read_text(encoding="utf-8").splitlines()
            if ln.startswith(f"{phase_n}\t")
        ]
        assert len(raw_lines) == 1, raw_lines
        parsed = _parse_phase_base_row(raw_lines[0])
        assert parsed is not None, (
            f"T0-C3: --record-base 寫入列 schema 不合規: {raw_lines[0]!r}"
        )
        head2 = _gmanifest_base_lookup(base_tsv, phase_n)
        assert head2 is not None and head2 == parsed[1]
        assert _SHA40_RE.fullmatch(head2)

        # append-only：同一 N 再 record ⇒ 非零
        rec2 = _run_gen(iso, "--record-base", phase_n)
        assert rec2.returncode != 0, "T0-C3: 重複 --record-base 同一 N 應非零"

        # 無效 N
        rec3 = _run_gen(iso, "--record-base", "9")
        assert rec3.returncode != 0

        # --- 精確 schema oracle：壞 timestamp／壞 SHA／欄數錯 ⇒ lookup FAIL ---
        good_sha = "a" * 40
        good_ts = "2026-08-03T12:00:00Z"

        base_tsv.write_text(f"2\t{good_sha}\tnot-an-iso8601-timestamp\n", encoding="utf-8")
        assert _gmanifest_base_lookup(base_tsv, "2") is None, (
            "T0-C3: 壞 timestamp 不得通過 G-MANIFEST lookup"
        )

        base_tsv.write_text(f"2\tnot_a_valid_sha\t{good_ts}\n", encoding="utf-8")
        assert _gmanifest_base_lookup(base_tsv, "2") is None, (
            "T0-C3: 壞 SHA 不得通過 G-MANIFEST lookup"
        )

        base_tsv.write_text(f"2\t{good_sha}\n", encoding="utf-8")
        assert _gmanifest_base_lookup(base_tsv, "2") is None, (
            "T0-C3: 欄數不足不得通過 G-MANIFEST lookup"
        )

        base_tsv.write_text(f"2\t{good_sha}\t{good_ts}\textra\n", encoding="utf-8")
        assert _gmanifest_base_lookup(base_tsv, "2") is None, (
            "T0-C3: 欄數過多不得通過 G-MANIFEST lookup"
        )

        # 有效列 ⇒ lookup 成功
        base_tsv.write_text(f"2\t{good_sha}\t{good_ts}\n", encoding="utf-8")
        assert _gmanifest_base_lookup(base_tsv, "2") == good_sha
        # 缺列仍 FAIL
        assert _gmanifest_base_lookup(base_tsv, "3") is None
    finally:
        _cleanup_iso(iso)


# ---------------------------------------------------------------------------
# T0-C4 — nodeid 欄契約（四欄之第三欄不得形同虛設）
# ---------------------------------------------------------------------------
def test_t0_c4_nodeid_contract() -> None:
    """T0-C4: 獨立 expected-nodeid assertion。

    - 至少一個 present ``tests/**/*.py`` → nodeid == path
    - 至少一個 MISSING C 項（尚未存在的測試檔）→ nodeid == ``-``
    ``nodeid_of()`` 若退化為全 ``-``，本測必須轉紅。
    """
    proc = _run_gen(REPO_ROOT)
    assert proc.returncode == 0, proc.stderr
    rows = _manifest_rows(proc.stdout)
    by_path = {r.split("|")[0]: r.split("|") for r in rows}

    present_py = "tests/governance/test_govflow_manifest.py"
    assert present_py in by_path, f"manifest 缺 present 測試檔列: {present_py}"
    p_parts = by_path[present_py]
    assert len(p_parts) == 4, p_parts
    assert p_parts[3] == "present", p_parts
    assert p_parts[2] == present_py, (
        f"T0-C4: present .py 的 nodeid 應為 path，得 {p_parts[2]!r}"
    )

    # C 類尚未建立的測試檔（B1 已交付 test_completeness_idlike_fp.py ⇒
    # 探針改指仍 MISSING 的 Phase 2 檔；契約不變：MISSING C ⇒ nodeid == '-'）
    missing_c = "tests/governance/test_result_state_format_failed.py"
    assert missing_c in by_path, f"manifest 缺 MISSING C 項: {missing_c}"
    m_parts = by_path[missing_c]
    assert len(m_parts) == 4, m_parts
    assert m_parts[3] == "MISSING", m_parts
    assert m_parts[2] == "-", (
        f"T0-C4: MISSING C 項 nodeid 應為 '-'，得 {m_parts[2]!r}"
    )


# ---------------------------------------------------------------------------
# T0-N7 — D 類抽取全毀：tmp_d 空 ⇒ 生成器非零
# ---------------------------------------------------------------------------
def test_t0_n7_d_empty_extraction_nonzero() -> None:
    """T0-N7: 隔離副本破壞 awk/grep 抽取 pattern 使 D 空 ⇒ 生成器非零。

    與 T0-N5（錨點計數失衡）正交：此測鎖定「抽取 pattern 寫錯 → tmp_d 空」
    的 fail-closed 守衛（gen_govflow_manifest.sh D-empty 分支）。
    """
    iso = _iso_tree("n7")
    try:
        script = iso / "scripts" / "gen_govflow_manifest.sh"
        text = script.read_text(encoding="utf-8")
        old = "grep -oE '(scripts|tests|docs)/[A-Za-z0-9_./-]+'"
        new = "grep -oE 'XXX_NEVER_MATCH_D_EXTRACT_/[A-Za-z0-9_./-]+'"
        assert old in text, "找不到 D 類 path 抽取 grep"
        script.write_text(text.replace(old, new, 1), encoding="utf-8")
        proc = _run_gen(iso)
        assert proc.returncode != 0, (
            f"T0-N7: D 抽取為空應非零，got rc=0 out={proc.stdout!r}"
        )
        assert (
            "D" in proc.stderr
            or "空" in proc.stderr
            or "抽取" in proc.stderr
        ), proc.stderr
    finally:
        _cleanup_iso(iso)


