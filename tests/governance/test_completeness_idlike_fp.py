"""Phase 1 — completeness_check heading 判準（Task 1.1 / GOV-COMPLETENESS-IDLIKE-FP）。

Test ID 與 docs/GOV_DISPATCH_FLOW_FIX_TODO.md Phase 1 測試表對應：
  T1-U1..U18  行為表 18 列參數化
  T1-M1       mutation（rev2 三方向取代四步 ⇒ ADV-CODEX-1 轉紅；恢復後轉綠）
  T1-B1       全形／～ 截斷
  T1-B2       空 heading
  T1-R1       表外 ≥20 token 無 current=1→new=0 漏網
  T1-I1       G-MANIFEST production-path integration（B1 硬前置）
  T1-S1       phases==0 例外收窄（僅具名 test_govflow_manifest.py）
  T1-S2       隔離：Phase 1 動 gen 腳本 ⇒ scope 外洩；動具名例外 ⇒ 通過

Production G-MANIFEST consumer 亦定義於本檔（``run_gmanifest_gate`` / CLI
``--gmanifest-gate <N>``）。放在本檔的理由：PHASE_MAP 僅允許本檔與
``scripts/completeness_check.sh`` 為 Phase 1 可改路徑；新建 ``scripts/*`` 會
迫使改 ``gen_govflow_manifest.sh``（phases=0）而自身踩破 G-MANIFEST。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"
GEN_SCRIPT = REPO_ROOT / "scripts" / "gen_govflow_manifest.sh"
SPEC_PATH = REPO_ROOT / "docs" / "GOV_DISPATCH_FLOW_FIX_SPEC.md"
BASE_TSV = REPO_ROOT / "handoffs" / "govflow_phase_base.tsv"
ISO_ROOT = REPO_ROOT / ".claude" / "tmp"

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_ISO8601_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_PHASE_N_OK = frozenset({"0", "1", "2", "3", "4"})

# ---------------------------------------------------------------------------
# SPEC 行為表（機械從 SPEC 抽取 heading + 修後必須 rc；禁手寫列數）
# ---------------------------------------------------------------------------
_ROW_RE = re.compile(
    r"^\s+\| `(#{2,6} .+?)` \|.*?\| \*\*rc==([01])\*\* \|"
)


def _load_behavior_rows() -> list[tuple[str, int]]:
    """從 SPEC 行為表機械抽取 (heading_line, expected_rc)。"""
    text = SPEC_PATH.read_text(encoding="utf-8")
    rows: list[tuple[str, int]] = []
    in_table = False
    for line in text.splitlines():
        if "| heading | 現行 | 修後" in line or "| heading | 現行 | 修後**必須** |" in line:
            in_table = True
            continue
        if in_table and line.startswith("  |---"):
            continue
        if in_table:
            m = _ROW_RE.match(line)
            if m:
                rows.append((m.group(1), int(m.group(2))))
            elif line.startswith("  | `") or line.startswith("| `"):
                # fallback: 更寬鬆解析
                parts = [p.strip() for p in line.strip().strip("|").split("|")]
                if len(parts) >= 3 and parts[0].startswith("`") and "rc==" in parts[2]:
                    heading = parts[0].strip("`")
                    rc_m = re.search(r"rc==([01])", parts[2])
                    if rc_m:
                        rows.append((heading, int(rc_m.group(1))))
            elif in_table and line.strip() and not line.strip().startswith("|"):
                break
            elif in_table and line.startswith("- "):
                break
    if len(rows) < 10:
        raise RuntimeError(
            f"SPEC 行為表抽取異常：只得 {len(rows)} 列（應 ≈18）。"
            f" 請檢查 SPEC 表格格式。"
        )
    return rows


BEHAVIOR_ROWS = _load_behavior_rows()


def _run_single(
    heading_md_line: str,
    *,
    script: Path = COMPLETENESS_SH,
    family: str = "codex",
    tmp_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """對單一 heading 跑 completeness_check --single；rc 直接取。"""
    if tmp_dir is None:
        tmp_dir = ISO_ROOT / f"idlike_single_{int(time.time() * 1000)}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        cleanup = True
    else:
        cleanup = False
    try:
        f = tmp_dir / "probe.md"
        # heading 可能已含 ### / ## 前綴
        body = heading_md_line if heading_md_line.lstrip().startswith("#") else f"## {heading_md_line}"
        f.write_text(body + "\n", encoding="utf-8")
        return subprocess.run(
            ["bash", str(script), "--single", str(f), "--family", family],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if cleanup and tmp_dir.exists() and tmp_dir.is_relative_to(ISO_ROOT):
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _iso_copy_script(label: str) -> Path:
    """隔離副本：只複製 completeness_check.sh 到 .claude/tmp/。"""
    ISO_ROOT.mkdir(parents=True, exist_ok=True)
    dest = ISO_ROOT / f"idlike_{label}_{int(time.time() * 1000)}"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(COMPLETENESS_SH, dest / "completeness_check.sh")
    return dest


# ===========================================================================
# T1-U1..U18 — 行為表 18 列逐列
# ===========================================================================
@pytest.mark.parametrize(
    "heading,expected_rc",
    BEHAVIOR_ROWS,
    ids=[f"T1-U{i + 1}" for i in range(len(BEHAVIOR_ROWS))],
)
def test_t1_u_behavior_row(heading: str, expected_rc: int) -> None:
    """T1-U*: SPEC 行為表逐列 rc 契約。"""
    proc = _run_single(heading)
    assert proc.returncode == expected_rc, (
        f"heading={heading!r} expected_rc={expected_rc} got={proc.returncode}\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )


# ===========================================================================
# T1-M1 — mutation：rev2 三方向「完全取代」四步程序
# ===========================================================================
# 突變目標（SPEC 逐字重述，僅供 mutation，不得回到正文）：
#   ① 家族前綴候選額外要求含 -R[0-9]+-
#   ② 含 -P[0-3]- 但缺 -R[0-9]+- 仍判畸形
#   ③ 治理關鍵字（含 STAMP／RECONCILE）明列必擋
_MUTATION_OLD = """\
      # (1) 整行命中 canonical → family-binding
      if (line ~ /^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$/) {
        split(line, segs, "-")
        family=segs[1]
        if (!(family in fam)) {
          print "COMPLETENESS FAIL: invalid family in ID: " line " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
          next
        }
        # family-binding：來源檔家族 vs heading FAMILY 前綴（堵冒充）
        if (expected_fam != "" && family != expected_fam) {
          print "COMPLETENESS FAIL: family-binding mismatch: heading " line " family=" family " ≠ file family=" expected_fam " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
          next
        }
        print line
        next
      }
      # (2) 【完整 heading 文字】∈ ALLOWLIST → 放行（鍵必須是完整 heading，不是首 token）
      if (line == "E-1～E-7 逐條 Verdict") {
        next
      }
      n=split(line, parts, /[[:space:]]+/)
      tok=parts[1]
      sub(/[^A-Za-z0-9_-].*$/, "", tok)
      # (3a) near-canonical 守衛 — 首 token 已是 finding ID 形狀（含位數錯／尾綴）
      if (tok ~ /^[A-Z]+-R[0-9]+-P/) {
        print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
        next
      }
      # (3a2) 首 token 內含合法家族名 → 判畸形（不論 arity）
      for (f in fam) {
        if (index(tok, f) > 0) {
          print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
          next
        }
      }
      # (3b) 跨 brief 固定段名 → 結構標題放行
      if (tok in struct_ok) next
      # (3c) arity — 裸 id-like 視為誤寫的 finding ID；帶尾綴視為結構標題
      if (tok ~ /^[A-Z]+(-[A-Z0-9]+)+$/ && n == 1) {
        print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
        next
      }
      # (4) 不命中 → 放行
      next
"""

_MUTATION_NEW = """\
      # MUTATION: rev2 三方向「完全取代」四步（非疊加）— T1-M1 only
      # 保留 (1) canonical family-binding（canonical 正則不得改）
      if (line ~ /^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$/) {
        split(line, segs, "-")
        family=segs[1]
        if (!(family in fam)) {
          print "COMPLETENESS FAIL: invalid family in ID: " line " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
          next
        }
        if (expected_fam != "" && family != expected_fam) {
          print "COMPLETENESS FAIL: family-binding mismatch: heading " line " family=" family " ≠ file family=" expected_fam " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
          next
        }
        print line
        next
      }
      # ③ 治理關鍵字（含 STAMP／RECONCILE）明列必擋
      if (line ~ /STAMP/ || line ~ /RECONCILE/) {
        print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
        next
      }
      # ② 含 -P[0-3]- 但缺 -R[0-9]+- 仍判畸形
      if (line ~ /-P[0-3]-/ && line !~ /-R[0-9]+-/) {
        print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
        next
      }
      # ① 家族前綴候選額外要求含 -R[0-9]+-（無 -R- 的 id-like 不擋 ⇒ ADV-CODEX-1 漏網）
      n=split(line, parts, /[[:space:]]+/)
      tok=parts[1]
      sub(/[^A-Za-z0-9_-].*$/, "", tok)
      if (tok ~ /^[A-Z]+(-[A-Z0-9]+)+$/ && tok ~ /-R[0-9]+-/) {
        print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
        next
      }
      next
"""


def test_t1_m1_mutation_three_directions_turns_adv_red() -> None:
    """T1-M1: 以 rev2 三方向完全取代四步 ⇒ ## ADV-CODEX-1 由 rc=1 轉 rc=0（用例轉紅）；
    恢復修法後同一 node 轉綠。

    兩段 receipt 以 assert 鎖死；隔離副本，禁改 repo 內腳本。
    """
    # --- 段 1：修法（現行）⇒ ADV-CODEX-1 必須 rc==1（綠）---
    healthy = _run_single("## ADV-CODEX-1")
    assert healthy.returncode == 1, (
        f"T1-M1 pre: 修法後 ADV-CODEX-1 應 rc==1，got {healthy.returncode}; "
        f"stderr={healthy.stderr!r}"
    )

    # --- 段 2：隔離副本突變（三方向取代）⇒ ADV-CODEX-1 應 rc==0（轉紅）---
    iso = _iso_copy_script("m1")
    try:
        script = iso / "completeness_check.sh"
        text = script.read_text(encoding="utf-8")
        assert _MUTATION_OLD in text, (
            "T1-M1: 找不到四步程序區塊，mutation 錨點漂移——須更新 _MUTATION_OLD"
        )
        mutated = text.replace(_MUTATION_OLD, _MUTATION_NEW, 1)
        assert mutated != text, "T1-M1: mutation 未生效"
        script.write_text(mutated, encoding="utf-8")

        probe = iso / "probe.md"
        probe.write_text("## ADV-CODEX-1\n", encoding="utf-8")
        mut_proc = subprocess.run(
            ["bash", str(script), "--single", str(probe), "--family", "codex"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        # 突變 receipt：rc 必須為 0（三方向抓不到 ADV-CODEX-1）
        assert mut_proc.returncode == 0, (
            f"T1-M1 mutation: 三方向應放掉 ADV-CODEX-1（rc==0 使用例轉紅），"
            f"got rc={mut_proc.returncode} stderr={mut_proc.stderr!r} "
            f"stdout={mut_proc.stdout!r}"
        )
        # 行為表期望 rc==1 ⇒ 此 node 在突變下轉紅
        assert mut_proc.returncode != 1, "T1-M1: mutation 後 ADV 用例應轉紅"

    finally:
        if iso.exists() and iso.is_relative_to(ISO_ROOT):
            shutil.rmtree(iso, ignore_errors=True)

    # --- 段 3：恢復修法（repo 內腳本未動）⇒ 再轉綠 ---
    restored = _run_single("## ADV-CODEX-1")
    assert restored.returncode == 1, (
        f"T1-M1 post: 恢復後 ADV-CODEX-1 應再轉綠 rc==1，got {restored.returncode}"
    )


# ===========================================================================
# T1-B1 — 全形／～ 截斷
# ===========================================================================
def test_t1_b1_fullwidth_tilde_truncation() -> None:
    """T1-B1: heading 含全形字元或 ～ 時，截斷點須與行為表一致。

    - 完整 allowlist 句（含 ～）→ rc==0（全行 allowlist）
    - 僅首 token ``E-1``（～ 被截斷後的假象）裸標題 → rc==1（arity n==1）
    - 半形 tilde 變體 → rc==0（**2026-08-06 B-39 E2b 更新**：由 arity n>1 放行，
      不再經 allowlist；理由與保護未減弱的實測見下方斷言處的註解）
    """
    full = _run_single("### E-1～E-7 逐條 Verdict")
    assert full.returncode == 0, f"完整 allowlist 應 rc==0: {full.stderr!r}"

    bare = _run_single("## E-1")
    assert bare.returncode == 1, f"裸 E-1 應 rc==1: {bare.stderr!r}"

    # 🔴 2026-08-06 B-39 E2b 契約更新（主委改動，已列為 code review 首要攻擊標的）
    #
    # 原斷言：半形 `~` 變體不在 ALLOWLIST ⇒ 應 rc==1。
    # 該斷言的前提是「allowlist 是唯一放行途徑」，故防的是「用相似字元冒充 allowlist 鍵」。
    # E2b 之後前提不再成立：帶尾綴（n>1）的 heading 由 arity 規則放行，
    # **不需要也不經過 allowlist** ⇒ 「冒充 allowlist」這條攻擊路徑本身消失。
    #
    # 保護是否減弱？實測否：
    #   - 帶尾綴的 finding ID `## CODEX-R4-P0-01 附加標題` → (3a) near-canonical 守衛，rc==1
    #     （行為表第 146 列，`test_t1_u_behavior_row` 逐列比對，2026-08-06 實跑 23 passed）
    #   - 裸 id-like（`## A-1`／`## E-1`／`## RECONCILE-STAMP` 等）→ (3c) arity n==1，rc==1
    #   ⇒ 放行「帶尾綴的非 finding 形狀」不會讓任何 finding ID 逃脫。
    #
    # 🔴 若 review 認定此更新是「改斷言取綠燈」，本行應退回並改為擋下半形變體；
    #    屆時須同時說明 `### G-1 extra` 這類帶尾綴結構標題要如何放行。
    half = _run_single("### E-1~E-7 逐條 Verdict")
    assert half.returncode == 0, (
        f"半形 tilde 變體為帶尾綴結構標題，E2b 下應由 arity 放行（rc==0），"
        f"got {half.returncode}; stderr={half.stderr!r}"
    )


# ===========================================================================
# T1-B2 — 空 heading
# ===========================================================================
def test_t1_b2_empty_heading() -> None:
    """T1-B2: heading 為空或僅 ## ⇒ 不進候選、放行 (rc==0)。"""
    iso = ISO_ROOT / f"idlike_b2_{int(time.time() * 1000)}"
    iso.mkdir(parents=True, exist_ok=True)
    try:
        for body, label in (
            ("##\n", "bare-hashes"),
            ("##   \n", "hashes-spaces"),
            ("# only-h1-not-scanned\n", "h1-ignored"),
            ("\n\n", "empty-file"),
        ):
            f = iso / f"{label}.md"
            f.write_text(body, encoding="utf-8")
            proc = subprocess.run(
                ["bash", str(COMPLETENESS_SH), "--single", str(f), "--family", "codex"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            assert proc.returncode == 0, (
                f"T1-B2 {label}: 空/非掃描 heading 應 rc==0，got {proc.returncode}; "
                f"stderr={proc.stderr!r}"
            )
    finally:
        shutil.rmtree(iso, ignore_errors=True)


# ===========================================================================
# T1-R1 — 表外 ≥20 token 無 current=1→new=0 漏網
# （修法後已無「current」對照本；以「修後仍須 rc==1」鎖真陽性邊界）
# ===========================================================================
_OUT_OF_TABLE_MUST_STAY_FAIL: tuple[str, ...] = (
    "## B-2",
    "## C-3",
    "## D-4",
    "## F-5",
    "## G-6",
    "## H-7",
    "## J-8",
    "## K-9",
    "## M-10",
    "## N-11",
    "## P-12",
    "## Q-13",
    "## S-14",
    "## T-15",
    "## V-16",
    "## W-17",
    "## X-18",
    "## Y-19",
    "## AA-1",
    "## BB-02",
    "## CODEX-OTHER",
    "## GROK-NOTES",
    "## COMPOSER-BAR",
    "## ADV-GROK-2",
    "## UNION-99",
    "## STAMP-MODE",
)


def test_t1_r1_out_of_table_no_leak() -> None:
    """T1-R1: ≥20 個未列入行為表的 heading，確認無 rc 由 1 漏成 0。

    表外 id-like 真陽性在修法後仍必須 rc==1（不得因 allowlist/收窄而放行）。
    """
    assert len(_OUT_OF_TABLE_MUST_STAY_FAIL) >= 20
    leaks: list[str] = []
    results: list[str] = []
    for h in _OUT_OF_TABLE_MUST_STAY_FAIL:
        proc = _run_single(h)
        results.append(f"{h}|rc={proc.returncode}")
        if proc.returncode == 0:
            leaks.append(h)
    assert not leaks, (
        f"T1-R1 漏網（表外 id-like 被放行 rc==0）: {leaks}\n全表: {results}"
    )


# ===========================================================================
# Production G-MANIFEST consumer（T1-I1 的真實路徑；非 T0-C3 的 test-local reimpl）
# ===========================================================================
def _parse_phase_base_row(line: str) -> tuple[str, str, str] | None:
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


def gmanifest_base_lookup(base_tsv: Path, phase_n: str) -> str | None:
    """Production phase-base lookup。缺列／壞 schema ⇒ None（Gate FAIL）。"""
    if not base_tsv.is_file():
        return None
    for line in base_tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        if not cols or cols[0] != phase_n:
            continue
        parsed = _parse_phase_base_row(line)
        if parsed is None:
            return None
        return parsed[1]
    return None


def _manifest_rows_map(cwd: Path) -> dict[str, str]:
    """path → phases 字串（來自 gen_govflow_manifest）。"""
    script = cwd / "scripts" / "gen_govflow_manifest.sh"
    if not script.is_file():
        script = GEN_SCRIPT
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    out: dict[str, str] = {}
    for ln in proc.stdout.splitlines():
        if not ln.strip() or "|" not in ln:
            continue
        parts = ln.split("|")
        if len(parts) < 2:
            continue
        out[parts[0]] = parts[1]
    return out


# 具名 phases==0 例外：僅 T0-C4 探針檔可在 Phase 1–4 與 phases-N 路徑一併維護。
# 禁止「所有 phases==0 放行」（CODEX-R5-P1-01 fail-open）。
_PHASE0_SCOPE_EXCEPTION: frozenset[str] = frozenset(
    {
        "tests/governance/test_govflow_manifest.py",
    }
)


def _manifest_allowed_for_phase(phase_n: str, cwd: Path) -> set[str]:
    """允許集合 = phases 欄含 N 的 path ∪ 具名 phases==0 例外路徑。

    具名例外理由：B1 交付 C 類檔後，Phase 0 的 MISSING 探針（T0-C4）必須
    改指仍 MISSING 的下游 C 檔；該維護只允許
    ``tests/governance/test_govflow_manifest.py`` 一路徑。
    其他 phases==0（如 ``scripts/gen_govflow_manifest.sh``）在 Phase N≠0
    仍屬 scope 外洩。
    """
    allowed: set[str] = set()
    for path, phases in _manifest_rows_map(cwd).items():
        if phases == "-":
            continue
        phase_set = {p.strip() for p in phases.split(",") if p.strip()}
        if phase_n in phase_set:
            allowed.add(path)
        elif "0" in phase_set and path in _PHASE0_SCOPE_EXCEPTION:
            allowed.add(path)
    return allowed


def _git_changed_since(base_sha: str, cwd: Path) -> set[str]:
    """實改集合：base..HEAD ＋ working tree 相對 base 的 tracked 變更。"""
    changed: set[str] = set()
    for args in (
        ["git", "diff", "--name-only", f"{base_sha}..HEAD"],
        ["git", "diff", "--name-only", base_sha],
        ["git", "diff", "--name-only", "--cached", base_sha],
    ):
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            for ln in proc.stdout.splitlines():
                if ln.strip():
                    changed.add(ln.strip())
    # untracked（非 gitignore）— 新檔也算實改
    proc = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        for ln in proc.stdout.splitlines():
            if ln.strip():
                changed.add(ln.strip())
    return changed


def run_gmanifest_gate(
    phase_n: str,
    *,
    repo_root: Path | None = None,
    base_tsv: Path | None = None,
    require_t1_i1: bool = True,
    skip_scope_check: bool = False,
) -> int:
    """Production G-MANIFEST Gate consumer。

    回傳 0 = 通過；非 0 = FAIL。
    - 缺 Phase N 列 / 壞 schema ⇒ rc!=0
    - 實改 ∖ 允許 ≠ ∅ ⇒ rc!=0
    - phase_n==1 且 require_t1_i1：機械檢查 T1-I1 **存在且通過**（實際 subprocess
      執行 pytest node；本函式被 T1-I1 自身呼叫時必須傳 require_t1_i1=False，
      否則會無限遞迴）
    """
    root = repo_root or REPO_ROOT
    tsv = base_tsv if base_tsv is not None else root / "handoffs" / "govflow_phase_base.tsv"

    base = gmanifest_base_lookup(tsv, phase_n)
    if base is None:
        print(
            f"G-MANIFEST FAIL: phase-base 缺 Phase {phase_n} 列或 schema 不合 "
            f"(file={tsv})",
            file=sys.stderr,
        )
        return 1

    if not skip_scope_check:
        allowed = _manifest_allowed_for_phase(phase_n, root)
        changed = _git_changed_since(base, root)
        # 實作面：scripts/ + tests/governance/（epic 攻擊面）
        # 排除 handoffs/（phase-base／報告）、.claude/、tests/golden/（pytest 副作用，
        # 由 restore_golden_inventory.sh 還原）、docs/ 測試表同步（brief 允許加列）。
        impl_changed = {
            p
            for p in changed
            if (
                p.startswith("scripts/")
                or p.startswith("tests/governance/")
            )
        }
        leaked = sorted(impl_changed - allowed)
        if leaked:
            print(
                f"G-MANIFEST FAIL: 實改超出 Phase {phase_n} 允許集合: {leaked}",
                file=sys.stderr,
            )
            print(f"  allowed={sorted(allowed)}", file=sys.stderr)
            print(f"  impl_changed={sorted(impl_changed)}", file=sys.stderr)
            return 1

    if phase_n == "1" and require_t1_i1:
        # 機械：T1-I1 必須存在於本檔，且實際執行通過（非僅字串存在）。
        # 遞迴邊界：T1-I1 內呼叫本 gate 一律 require_t1_i1=False。
        src_path = Path(__file__).resolve()
        src = src_path.read_text(encoding="utf-8")
        m = re.search(r"^def (test_t1_i1_\w+)\s*\(", src, re.MULTILINE)
        if m is None:
            print(
                "G-MANIFEST FAIL: T1-I1 不存在（缺 def test_t1_i1_*）",
                file=sys.stderr,
            )
            return 1
        nodeid = f"{src_path}::{m.group(1)}"
        # pytest cwd 固定為本檔所在 repo 根（非 iso root），T1-I1 自建隔離樹。
        pytest_cwd = src_path.parents[2]
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", nodeid, "-q", "--tb=line"],
            cwd=str(pytest_cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(
                f"G-MANIFEST FAIL: T1-I1 未通過（pytest rc={proc.returncode} "
                f"node={nodeid}）",
                file=sys.stderr,
            )
            if proc.stdout:
                print(proc.stdout, file=sys.stderr)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)
            return 1

    print(f"G-MANIFEST PASS: phase={phase_n} base={base}")
    return 0


# ===========================================================================
# T1-I1 — production-path integration
# ===========================================================================
def test_t1_i1_gmanifest_production_path() -> None:
    """T1-I1: 以 repo 內真實 G-MANIFEST consumer 對 phase-base 端到端驗證。

    - 缺 Phase 1 列 ⇒ Gate rc!=0
    - 有效列 ⇒ 取得 base 且 rc==0（scope 在隔離 git 樹內驗證）
    - mutation：壞 SHA／壞 ISO8601／欄數 !=3 各一 ⇒ rc!=0
    """
    ISO_ROOT.mkdir(parents=True, exist_ok=True)
    iso = ISO_ROOT / f"gmanifest_t1i1_{int(time.time() * 1000)}"
    if iso.exists():
        shutil.rmtree(iso)
    iso.mkdir(parents=True)

    try:
        # 最小 git 樹 + 必要腳本
        (iso / "scripts").mkdir()
        (iso / "handoffs").mkdir()
        (iso / "docs").mkdir()
        (iso / "tests" / "governance").mkdir(parents=True)
        shutil.copy2(GEN_SCRIPT, iso / "scripts" / "gen_govflow_manifest.sh")
        shutil.copy2(COMPLETENESS_SH, iso / "scripts" / "completeness_check.sh")
        shutil.copy2(SPEC_PATH, iso / "docs" / "GOV_DISPATCH_FLOW_FIX_SPEC.md")
        # gen 需要 TODO
        todo_src = REPO_ROOT / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md"
        shutil.copy2(todo_src, iso / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md")
        # 複製足夠 scripts 讓 gen 的 A 類掃描不致 0 命中
        for name in (
            "cx_run.sh",
            "committee_run.sh",
            "gate.sh",
            "audit_events.json",
            "audit_append.sh",
            "gov_check.sh",
            "doc_format_precheck.sh",
            "brief_conformance_check.sh",
            "govflow_lifecycle.json",
            "verdict_filled_check.sh",
            "debt_clear.sh",
            "reconcile_build.sh",
            "verification_claim_check.py",
        ):
            src = REPO_ROOT / "scripts" / name
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, iso / "scripts" / name)
                else:
                    shutil.copy2(src, iso / "scripts" / name)
        # git hooks path referenced by PHASE_MAP
        hooks = REPO_ROOT / "scripts" / "git_hooks"
        if hooks.is_dir():
            shutil.copytree(hooks, iso / "scripts" / "git_hooks")
        # 複製 tests/governance 讓 A 類掃描有內容
        for p in (REPO_ROOT / "tests" / "governance").glob("*.py"):
            shutil.copy2(p, iso / "tests" / "governance" / p.name)

        subprocess.run(["git", "init"], cwd=str(iso), capture_output=True, check=False)
        subprocess.run(
            ["git", "config", "user.email", "t1i1@test.local"],
            cwd=str(iso),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.name", "t1i1"],
            cwd=str(iso),
            capture_output=True,
            check=False,
        )
        subprocess.run(["git", "add", "-A"], cwd=str(iso), capture_output=True, check=False)
        subprocess.run(
            ["git", "commit", "-m", "t1i1-base", "--allow-empty"],
            cwd=str(iso),
            capture_output=True,
            check=False,
        )

        base_tsv = iso / "handoffs" / "govflow_phase_base.tsv"

        # --- 缺 Phase 1 列 ⇒ FAIL ---
        rc_missing = run_gmanifest_gate(
            "1",
            repo_root=iso,
            base_tsv=base_tsv,
            require_t1_i1=False,
            skip_scope_check=True,
        )
        assert rc_missing != 0, "T1-I1: 缺 Phase 1 列應 rc!=0"

        # --- --record-base 寫入後有效列 ⇒ PASS（skip scope：iso 內無 phase1 實改契約）---
        rec = subprocess.run(
            ["bash", str(iso / "scripts" / "gen_govflow_manifest.sh"), "--record-base", "1"],
            cwd=str(iso),
            capture_output=True,
            text=True,
            check=False,
        )
        assert rec.returncode == 0, f"record-base 失敗: {rec.stderr!r}"
        head = gmanifest_base_lookup(base_tsv, "1")
        assert head is not None and _SHA40_RE.fullmatch(head), head
        rc_ok = run_gmanifest_gate(
            "1",
            repo_root=iso,
            base_tsv=base_tsv,
            require_t1_i1=False,
            skip_scope_check=True,
        )
        assert rc_ok == 0, "T1-I1: 有效列應 rc==0"

        # --- mutation：壞 SHA / 壞 ISO8601 / 欄數 !=3 各一 ⇒ rc!=0 ---
        good_sha = "b" * 40
        good_ts = "2026-08-03T00:00:00Z"

        base_tsv.write_text(f"1\tnot_a_valid_sha_value_here_pad\t{good_ts}\n", encoding="utf-8")
        assert (
            run_gmanifest_gate(
                "1",
                repo_root=iso,
                base_tsv=base_tsv,
                require_t1_i1=False,
                skip_scope_check=True,
            )
            != 0
        ), "T1-I1: 壞 SHA 應 rc!=0"

        base_tsv.write_text(f"1\t{good_sha}\tnot-iso8601\n", encoding="utf-8")
        assert (
            run_gmanifest_gate(
                "1",
                repo_root=iso,
                base_tsv=base_tsv,
                require_t1_i1=False,
                skip_scope_check=True,
            )
            != 0
        ), "T1-I1: 壞 ISO8601 應 rc!=0"

        base_tsv.write_text(f"1\t{good_sha}\n", encoding="utf-8")
        assert (
            run_gmanifest_gate(
                "1",
                repo_root=iso,
                base_tsv=base_tsv,
                require_t1_i1=False,
                skip_scope_check=True,
            )
            != 0
        ), "T1-I1: 欄數!=3 應 rc!=0"

        base_tsv.write_text(f"1\t{good_sha}\t{good_ts}\textra\n", encoding="utf-8")
        assert (
            run_gmanifest_gate(
                "1",
                repo_root=iso,
                base_tsv=base_tsv,
                require_t1_i1=False,
                skip_scope_check=True,
            )
            != 0
        ), "T1-I1: 欄數>3 應 rc!=0"

        # 恢復有效列
        base_tsv.write_text(f"1\t{good_sha}\t{good_ts}\n", encoding="utf-8")
        assert (
            run_gmanifest_gate(
                "1",
                repo_root=iso,
                base_tsv=base_tsv,
                require_t1_i1=False,
                skip_scope_check=True,
            )
            == 0
        )

    finally:
        if iso.exists() and iso.is_relative_to(ISO_ROOT):
            shutil.rmtree(iso, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI：production 入口
#   venv/bin/python tests/governance/test_completeness_idlike_fp.py --gmanifest-gate 1
# ---------------------------------------------------------------------------
def _cli_main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "--gmanifest-gate":
        phase = argv[1] if len(argv) > 1 else ""
        if phase not in _PHASE_N_OK:
            print(f"用法: --gmanifest-gate <N>  N∈{{0,1,2,3,4}}", file=sys.stderr)
            return 2
        # N=1 時 Gate 內機械執行 T1-I1 並要求通過；scope 檢查開
        return run_gmanifest_gate(phase, require_t1_i1=(phase == "1"))
    print(
        "用法: python tests/governance/test_completeness_idlike_fp.py --gmanifest-gate <N>",
        file=sys.stderr,
    )
    return 2


# ===========================================================================
# T1-S1 — G-MANIFEST phases==0 例外收窄（CODEX-R5-P1-01）
# ===========================================================================
def test_t1_s1_phase0_exception_is_named_single_path() -> None:
    """T1-S1: Phase 1 允許集合僅含具名 phases==0 例外，不含 gen 腳本。

    證偽契約：若恢復「所有 phases==0 放行」，本測仍綠但 isolation 外洩探針會紅；
    本測直接鎖 allowed 集合語意。
    """
    allowed = _manifest_allowed_for_phase("1", REPO_ROOT)
    assert "tests/governance/test_govflow_manifest.py" in allowed, (
        "具名 T0-C4 例外路徑必須在 Phase 1 允許集合內"
    )
    assert "scripts/gen_govflow_manifest.sh" not in allowed, (
        "phases==0 的 gen 腳本不得被併入 Phase 1 允許集合（fail-open）"
    )
    assert "tests/governance/test_completeness_idlike_fp.py" in allowed
    assert "scripts/completeness_check.sh" in allowed
    # 其他 phase 的 path 不得因 phases==0 例外而被誤納
    for p in sorted(allowed):
        if p in _PHASE0_SCOPE_EXCEPTION:
            continue
        # 允許集合內非例外路徑，其 phases 欄必須含 1
        rows = _manifest_rows_map(REPO_ROOT)
        assert p in rows, p
        phase_set = {x.strip() for x in rows[p].split(",") if x.strip()}
        assert "1" in phase_set, f"{p} phases={rows[p]!r} 無 1 卻進允許集合"


def test_t1_s2_phase0_gen_script_is_scope_leak_on_phase1() -> None:
    """T1-S2: 隔離模擬 Phase 1 只動 gen 腳本 ⇒ G-MANIFEST scope 外洩；
    動具名例外檔 ⇒ 不因 phases==0 而外洩（允許集合含該 path）。
    """
    ISO_ROOT.mkdir(parents=True, exist_ok=True)
    iso = ISO_ROOT / f"gmanifest_s2_{int(time.time() * 1000)}"
    if iso.exists():
        shutil.rmtree(iso)
    iso.mkdir(parents=True)

    try:
        (iso / "scripts").mkdir()
        (iso / "handoffs").mkdir()
        (iso / "docs").mkdir()
        (iso / "tests" / "governance").mkdir(parents=True)
        shutil.copy2(GEN_SCRIPT, iso / "scripts" / "gen_govflow_manifest.sh")
        shutil.copy2(COMPLETENESS_SH, iso / "scripts" / "completeness_check.sh")
        shutil.copy2(SPEC_PATH, iso / "docs" / "GOV_DISPATCH_FLOW_FIX_SPEC.md")
        todo_src = REPO_ROOT / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md"
        shutil.copy2(todo_src, iso / "docs" / "GOV_DISPATCH_FLOW_FIX_TODO.md")
        for name in (
            "cx_run.sh",
            "committee_run.sh",
            "gate.sh",
            "audit_events.json",
            "audit_append.sh",
            "gov_check.sh",
            "doc_format_precheck.sh",
            "brief_conformance_check.sh",
            "govflow_lifecycle.json",
            "verdict_filled_check.sh",
            "debt_clear.sh",
            "reconcile_build.sh",
            "verification_claim_check.py",
        ):
            src = REPO_ROOT / "scripts" / name
            if src.exists() and src.is_file():
                shutil.copy2(src, iso / "scripts" / name)
        hooks = REPO_ROOT / "scripts" / "git_hooks"
        if hooks.is_dir():
            shutil.copytree(hooks, iso / "scripts" / "git_hooks")
        for p in (REPO_ROOT / "tests" / "governance").glob("*.py"):
            shutil.copy2(p, iso / "tests" / "governance" / p.name)

        subprocess.run(["git", "init"], cwd=str(iso), capture_output=True, check=False)
        subprocess.run(
            ["git", "config", "user.email", "t1s2@test.local"],
            cwd=str(iso),
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.name", "t1s2"],
            cwd=str(iso),
            capture_output=True,
            check=False,
        )
        subprocess.run(["git", "add", "-A"], cwd=str(iso), capture_output=True, check=False)
        subprocess.run(
            ["git", "commit", "-m", "t1s2-base"],
            cwd=str(iso),
            capture_output=True,
            check=False,
        )
        base_tsv = iso / "handoffs" / "govflow_phase_base.tsv"
        rec = subprocess.run(
            ["bash", str(iso / "scripts" / "gen_govflow_manifest.sh"), "--record-base", "1"],
            cwd=str(iso),
            capture_output=True,
            text=True,
            check=False,
        )
        assert rec.returncode == 0, rec.stderr

        # 確保 iso 內的 consumer 使用本檔已收窄的 _manifest_allowed（copy 的是當前檔）
        # --- A：只改 gen 腳本（phases=0 非例外）⇒ 外洩 ---
        gen_path = iso / "scripts" / "gen_govflow_manifest.sh"
        gen_path.write_text(
            gen_path.read_text(encoding="utf-8") + "\n# t1s2-leak-probe\n",
            encoding="utf-8",
        )
        # 以 iso 樹內複製的本檔邏輯：直接 import 當前模組函式，但 cwd=iso
        rc_leak = run_gmanifest_gate(
            "1",
            repo_root=iso,
            base_tsv=base_tsv,
            require_t1_i1=False,
            skip_scope_check=False,
        )
        assert rc_leak != 0, (
            "T1-S2: Phase 1 動到 scripts/gen_govflow_manifest.sh 應 scope 外洩 rc!=0"
        )

        # 還原 gen，改具名例外檔 ⇒ 允許
        shutil.copy2(GEN_SCRIPT, gen_path)
        exc_path = iso / "tests" / "governance" / "test_govflow_manifest.py"
        exc_path.write_text(
            exc_path.read_text(encoding="utf-8") + "\n# t1s2-exception-ok\n",
            encoding="utf-8",
        )
        rc_ok = run_gmanifest_gate(
            "1",
            repo_root=iso,
            base_tsv=base_tsv,
            require_t1_i1=False,
            skip_scope_check=False,
        )
        assert rc_ok == 0, (
            "T1-S2: Phase 1 動到具名例外 test_govflow_manifest.py 應通過 "
            f"(rc={rc_ok})"
        )
    finally:
        if iso.exists() and iso.is_relative_to(ISO_ROOT):
            shutil.rmtree(iso, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(_cli_main(sys.argv[1:]))
