"""治理家族 SoT(governance_families.json)+ grok 全鏈接線的可證偽測試。

事故(2026-07-23 使用者抓):grok 散在 4 檔 11 處缺漏/被誤記 composer,逐處手補必漏
(連 SPEC「完整清單」都漏 gate.sh:296)。修法=單一 SoT,4 檔全讀。
本測試釘死:①SoT 可讀+fail-closed ②雙語 parity ③grok 在每個接點真的被認得
④gate_check 熱路徑寫死清單 == SoT(防漂移)。任一 grok 接點被 revert → 對應測試紅。
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
SOT = SCRIPTS / "governance_families.json"


def _bash(snippet: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-c", snippet], cwd=REPO, capture_output=True, text=True, check=False)


# ---- SoT 本體 ----
def test_sot_exists_and_has_grok() -> None:
    d = json.loads(SOT.read_text(encoding="utf-8"))
    assert "grok" in d["families"]
    assert "grok" in d["review_families"]
    assert "grok" in d["executor_clis"]


def test_bash_getter_and_failclosed() -> None:
    ok = _bash(". scripts/governance_families.sh && families_get review_families")
    assert ok.returncode == 0 and "grok" in ok.stdout
    bad = _bash(". scripts/governance_families.sh && families_get nonexistent")
    assert bad.returncode != 0  # 缺 key → fail-closed


def test_bilingual_parity() -> None:
    b = _bash(". scripts/governance_families.sh && families_get families ' '").stdout.split()
    p = subprocess.run(
        ["python3", str(SCRIPTS / "governance_families_loader.py"), "families", " "],
        cwd=REPO, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert sorted(b) == sorted(p) and "grok" in b


# ---- grok 在各接點被認得 ----
def test_gate_check_gates_grok() -> None:
    """grok 命令無 token → deny(exit 2)。revert(移 grok)→ exit 0 → 本測試紅。"""
    payload = '{"tool_name":"Bash","tool_input":{"command":"grok -p hi"}}'
    p = _bash(f"printf '%s' '{payload}' | GATE_DIR_OVERRIDE=/tmp/frtest.$$ bash scripts/gate_check.sh")
    assert p.returncode == 2


def test_stamp_default_requires_grok(tmp_path: Path) -> None:
    """不傳 roster → 預設含 grok;只有兩家戳記 → FAIL 缺 grok。"""
    f = tmp_path / "r.md"
    f.write_text("body\n## 戳記\n", encoding="utf-8")
    h = _bash(f"bash scripts/reconcile_body_hash.sh {f}").stdout.strip()
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"RECONCILE-STAMP: codex APPROVED 2026-07-23 sha256:{h} task:x\n")
        fh.write(f"RECONCILE-STAMP: composer APPROVED 2026-07-23 sha256:{h} task:x\n")
    p = _bash(f"bash scripts/reconcile_stamps_check.sh {f}")
    assert p.returncode != 0 and "grok" in (p.stdout + p.stderr)


def test_adv_path_re_recognizes_grok() -> None:
    p = subprocess.run(
        ["python3", "-c",
         "import sys; sys.path.insert(0,'scripts'); import verify_task_provenance as v; "
         "print(bool(v.ADV_PATH_RE.match('handoffs/x-ADV-GROK.md')), bool(v.ADV_PATH_RE.match('handoffs/x-ADV-CODEX.md')))"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert p.stdout.strip() == "True True"


def test_gate_family_derivation_labels_grok(tmp_path: Path) -> None:
    """派 grok 任務 → audit family=grok(非 composer)。revert → composer → 本測試紅。"""
    gate_dir = tmp_path / "g"
    out = REPO / "handoffs" / "frtest-grok.md"
    out.write_text("x\n", encoding="utf-8")
    try:
        _bash(
            f"GATE_DIR_OVERRIDE={gate_dir} bash scripts/gate.sh dispatch "
            f"--task-id frtest-grok --output handoffs/frtest-grok.md --intent t --risk low "
            f"--facts-asked none-needed:t --review-role stamp:grok --template n/a:t"
        )
        audit = (gate_dir / "audit.log").read_text(encoding="utf-8")
        fams = [json.loads(l)["family"] for l in audit.splitlines()
                if l.strip() and '"frtest-grok"' in l]
        assert fams and all(f == "grok" for f in fams)
    finally:
        out.unlink(missing_ok=True)


# ---- 防漂移:所有寫死家族清單的消費者 == SoT(委員 B;取代脆弱 regex group 抽取,委員 RC-6) ----
import pytest  # noqa: E402

_UNIVERSE = {"codex", "composer", "grok", "claude", "agy", "cursor-agent"}


def _fams_in_lines(fname: str, locate: str) -> list[set[str]]:
    """回**所有**含 locate 的行各自的 family token 集合(涵蓋重複 site,如 completeness 105/678)。

    找不到任何行(pattern 被重構)→ AssertionError(逼更新 drift 測試,非靜默漏)。
    """
    text = (SCRIPTS / fname).read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if locate in ln]
    assert lines, f"{fname}: 找不到含 '{locate}' 的家族清單行(refactor?→須更新 drift 測試)"
    out = []
    for ln in lines:
        low = ln.lower()
        out.append({u for u in _UNIVERSE if re.search(rf"(?<![a-z-]){re.escape(u)}(?![a-z-])", low)})
    return out


# (檔, 定位子字串, SoT key, 排除):寫死清單**每個 site** 須 == SoT[key]-排除。加/減家族未同步 → 紅。
# gate_check 同行含 `claude -p` 特例(非 executor_clis)→ 排除 claude。
# completeness_check 有 6 個 site(委員 codex B:單釘一行不夠)→ 全涵蓋。
_DRIFT = [
    ("gate_check.sh", "grok|agy)[", "executor_clis", {"claude"}),
    ("_gate_lex.sh", "grok|agy)[", "executor_clis", {"claude"}),  # GOVB0 Task 2.1 詞法判定
    ("completeness_check.sh", "FAMILY_ALLOW_RE=", "families", set()),
    ("completeness_check.sh", "FAMILY_FILE_RE=", "families", set()),
    ("completeness_check.sh", 'fam["CODEX"]', "families", set()),
    ("completeness_check.sh", "allow = {", "families", set()),
    ("completeness_check.sh", 're.match(r"^.+-(codex', "families", set()),
    ("completeness_check.sh", "FAM = {", "families", set()),  # 913/1029/1103(委員 codex round2)
    ("completeness_check.sh", "allowlist 外家族", "families", set()),  # 557 訊息
    ("review_quorum_check.sh", "codex|composer|grok) :", "review_families", set()),
    ("write_sources_lock.sh", "allow = {", "families", set()),
    ("write_sources_lock.sh", "family_re = ", "families", set()),
    ("cx_run.sh", "family 須為", "review_families", set()),
    ("write_committee_accepted.sh", "FAM = {", "families", set()),
]

_CONSUMER_FILES = [
    "gate_check.sh", "_gate_lex.sh", "completeness_check.sh", "review_quorum_check.sh",
    "write_sources_lock.sh", "cx_run.sh", "write_committee_accepted.sh",
]


# 已知 doc 行(訊息/usage 範例;非功能碼)——**明確**白名單,非靜默 substring 排除(委員 codex round3)。
# 只有這幾行 doc 免 SoT-pin;任何**功能行**(含帶 echo/--roster 者)未 pin 一律紅。
_DOC_ALLOW = [
    "非實作者家族 code review",          # review_quorum echo 訊息
    "--roster codex,composer,grok",      # write_sources_lock usage 範例
    "cx_run.sh <codex|grok|composer>",   # cx_run usage 訊息
]


def test_no_unpinned_family_list_line() -> None:
    """反 whack-a-mole:除 #註解 與 _DOC_ALLOW 明列 doc 外,任何 ≥3 家族 token 的行都須被 _DRIFT 釘到。

    委員 codex round3:移除粗 substring 排除(echo/--roster/bash),否則功能行含這些字會被誤排漏網。
    未釘 → 紅(逼加入 _DRIFT 或 _DOC_ALLOW)。不再靠委員一輪輪找漏。
    """
    locates = [loc for _, loc, _, _ in _DRIFT]
    unpinned: list[str] = []
    for fname in _CONSUMER_FILES:
        for i, ln in enumerate((SCRIPTS / fname).read_text(encoding="utf-8").splitlines(), 1):
            if ln.lstrip().startswith("#"):  # 純註解 auto-skip(doc)
                continue
            fams = {u for u in _UNIVERSE if re.search(rf"(?<![a-z-]){re.escape(u)}(?![a-z-])", ln.lower())}
            if len(fams) < 3:
                continue
            if any(loc in ln for loc in locates):  # 已 pin
                continue
            if any(d in ln for d in _DOC_ALLOW):  # 明列 doc
                continue
            unpinned.append(f"{fname}:{i}: {ln.strip()[:72]}")
    assert not unpinned, "未釘 family 清單行(加入 _DRIFT 或明列 _DOC_ALLOW):\n" + "\n".join(unpinned)


@pytest.mark.parametrize("fname,locate,key,exclude", _DRIFT)
def test_consumer_family_list_matches_sot(fname: str, locate: str, key: str, exclude: set) -> None:
    expected = set(json.loads(SOT.read_text(encoding="utf-8"))[key])
    for got in _fams_in_lines(fname, locate):
        assert (got - exclude) == expected, (
            f"{fname} 家族清單 {got - exclude} != SoT {key} {expected}(漂移;改 SoT 須同步或反之)"
        )


# ---- fail-closed 邊界(委員 A/D):SoT 缺/壞 → 拒,不 fallback ----
def test_getter_failclosed_sot_missing(tmp_path: Path) -> None:
    """getter 複製到無 json 的 tmp → families_get fail-closed(不動真 SoT)。"""
    (tmp_path / "governance_families.sh").write_text(
        (SCRIPTS / "governance_families.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    p = _bash(f". {tmp_path}/governance_families.sh && families_get families")
    assert p.returncode != 0


def test_getter_failclosed_sot_malformed(tmp_path: Path) -> None:
    (tmp_path / "governance_families.sh").write_text(
        (SCRIPTS / "governance_families.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "governance_families.json").write_text("{bad json", encoding="utf-8")
    p = _bash(f". {tmp_path}/governance_families.sh && families_get families")
    assert p.returncode != 0


def test_provenance_failclosed_on_sot_import(tmp_path: Path) -> None:
    """verify_task_provenance 從無 SoT 的 dir import → 拋錯(fail-closed,非 fallback)。"""
    for f in ("verify_task_provenance.py", "governance_families_loader.py"):
        (tmp_path / f).write_text((SCRIPTS / f).read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run(
        ["python3", "-c", f"import sys; sys.path.insert(0,'{tmp_path}'); import verify_task_provenance"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert p.returncode != 0 and "fail-closed" in p.stderr


def test_review_role_substring_no_false_positive(tmp_path: Path) -> None:
    """`stamp:codexx` 不得誤判 codex(詞界);→ unknown(委員 codex C)。"""
    gate_dir = tmp_path / "g"
    out = REPO / "handoffs" / "frtest-cxx.md"
    out.write_text("x\n", encoding="utf-8")
    try:
        _bash(
            f"GATE_DIR_OVERRIDE={gate_dir} bash scripts/gate.sh dispatch "
            f"--task-id frtest-cxx --output handoffs/frtest-cxx.md --intent t --risk low "
            f"--facts-asked none-needed:t --review-role stamp:codexx --template n/a:t"
        )
        audit = (gate_dir / "audit.log").read_text(encoding="utf-8")
        fams = [json.loads(l)["family"] for l in audit.splitlines()
                if l.strip() and '"frtest-cxx"' in l]
        assert fams and all(f == "unknown" for f in fams), f"codexx 誤判: {fams}"
    finally:
        out.unlink(missing_ok=True)


def test_getter_failclosed_partial_families_key(tmp_path: Path) -> None:
    """families key null/壞但 review_families 好 → families_get families 仍 fail-closed(委員 codex A)。"""
    (tmp_path / "governance_families.sh").write_text(
        (SCRIPTS / "governance_families.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "governance_families.json").write_text(
        '{"families": null, "review_families": ["codex","composer","grok"]}', encoding="utf-8"
    )
    p = _bash(f". {tmp_path}/governance_families.sh && families_get families")
    assert p.returncode != 0


def test_gate_unknown_family_is_unknown_not_composer(tmp_path: Path) -> None:
    """未知 review_role → family=unknown(非 composer);歧義多家 → unknown。"""
    gate_dir = tmp_path / "g"
    out = REPO / "handoffs" / "frtest-unk.md"
    out.write_text("x\n", encoding="utf-8")
    try:
        _bash(
            f"GATE_DIR_OVERRIDE={gate_dir} bash scripts/gate.sh dispatch "
            f"--task-id frtest-unk --output handoffs/frtest-unk.md --intent t --risk low "
            f"--facts-asked none-needed:t --review-role single-executor:n/a --template n/a:t"
        )
        audit = (gate_dir / "audit.log").read_text(encoding="utf-8")
        fams = [json.loads(l)["family"] for l in audit.splitlines()
                if l.strip() and '"frtest-unk"' in l]
        assert fams and all(f == "unknown" for f in fams)
    finally:
        out.unlink(missing_ok=True)
