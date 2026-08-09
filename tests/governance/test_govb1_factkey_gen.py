"""票 B-25 / Task 2.1 — fact-key 生成器守衛測試。

測什麼：`scripts/gen_fact_key_blocks.sh` 的三種模式（emit／--check／--write）
與其 fail-closed 邊界。通過條件＝下列每條 rc／輸出契約成立。

🔴 本檔的 mutation 是**行為引信**，不是字面比對：
   把生成器複製到 tmp、實際改壞它、再跑一次，看決定性 oracle 是否真的轉紅。
   （字面斷言「原始碼含 LC_ALL=C」同時會產生假綠與假紅——B5 已踩過，見
    handoffs/reconcile/20260809-govb1-b5-review-r2/synth.md。）
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "scripts" / "gen_fact_key_blocks.sh"
REG = REPO / "scripts" / "fact_keys.json"
FIX = REPO / "tests" / "governance" / "fixtures" / "govb1"
CLEAN = FIX / "factkey_clean"
DRIFTED = FIX / "factkey_drifted"

KEY = "governance-execution-order"
TARGET_REL = "docs/GOVERNANCE_EXECUTION_ORDER.md"
BEGIN = f"<!-- BEGIN GENERATED: {KEY} -->"
END = f"<!-- END GENERATED: {KEY} -->"


def _run(args, *, cwd: Path = REPO, env_extra: dict | None = None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _gen(*args, cwd: Path = REPO, env_extra: dict | None = None):
    return _run([str(GEN), *args], cwd=cwd, env_extra=env_extra)


# --------------------------------------------------------------------------
# 基本存在性與 ASSERT rc 對照（TODO Task 2.1 驗證欄逐條）
# --------------------------------------------------------------------------


def test_generator_and_registry_exist_and_executable():
    assert GEN.is_file(), f"缺生成器 {GEN}"
    assert os.access(GEN, os.X_OK), "生成器須可執行（gov_check 以 [ -x ] 判定）"
    assert REG.is_file(), f"缺註冊表 {REG}"


def test_registry_is_valid_json_object_with_the_single_initial_key():
    data = json.loads(REG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    fact_keys = [k for k in data if k != "_schema"]
    assert fact_keys == [KEY], (
        f"TODO 實作要點 1：初始只收 {KEY} 一項，實得 {fact_keys}"
    )
    assert data[KEY]["target"] == TARGET_REL
    rows = data[KEY]["rows"]
    assert rows and all(
        isinstance(r, list) and all(isinstance(c, str) for c in r) for r in rows
    )


def test_t21_assert_clean_fixture_rc_zero():
    """ASSERT --check WHEN GOVB1_FACTKEY_ROOT=...factkey_clean THEN rc=0"""
    r = _gen("--check", env_extra={"GOVB1_FACTKEY_ROOT": str(CLEAN)})
    assert r.returncode == 0, f"clean fixture 應 rc=0，實得 {r.returncode}\n{r.stderr}"


def test_t21_assert_drifted_fixture_rc_nonzero_with_key_and_file():
    """ASSERT --check WHEN GOVB1_FACTKEY_ROOT=...factkey_drifted THEN rc!=0

    邊界②要求訊息含檔名與 key——否則 push 被擋時無從得知該修哪一份。
    """
    r = _gen("--check", env_extra={"GOVB1_FACTKEY_ROOT": str(DRIFTED)})
    assert r.returncode != 0, "drifted fixture 應 rc≠0（漂移未被偵測＝機制失效）"
    assert KEY in r.stderr, f"訊息須含 key，實得: {r.stderr}"
    assert TARGET_REL in r.stderr, f"訊息須含檔名，實得: {r.stderr}"


def test_real_repo_check_passes():
    """真實 repo 必須自洽——否則 Task 2.2 掛上去會把每一次 push 擋死。"""
    r = _gen("--check")
    assert r.returncode == 0, f"repo 根 --check 應 rc=0，實得 {r.returncode}\n{r.stderr}"


# --------------------------------------------------------------------------
# T-2.1-D1 決定性
# --------------------------------------------------------------------------


def test_t21_d1_deterministic_three_runs_identical():
    outs = [_gen().stdout for _ in range(3)]
    assert outs[0] == outs[1] == outs[2], "連跑 3 次輸出不同 ⇒ 機制退化為噪音"
    assert outs[0].strip(), "輸出不得為空"


def test_output_has_no_bom_no_crlf_no_timestamp():
    raw = subprocess.run(
        ["bash", str(GEN)], cwd=str(REPO), capture_output=True
    ).stdout
    assert not raw.startswith(b"\xef\xbb\xbf"), "輸出不得含 BOM"
    assert b"\r\n" not in raw, "輸出須全程 LF"
    # 時間戳會使 diff 恆紅：任何 4 位年份樣式皆視為違規訊號
    text = raw.decode("utf-8")
    import re

    assert not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text), (
        f"輸出疑似含時間戳:\n{text}"
    )


def test_generator_runs_under_two_seconds():
    t0 = time.monotonic()
    _gen()
    elapsed = time.monotonic() - t0
    assert elapsed < 2.0, f"生成器單次須 <2s，實測 {elapsed:.2f}s"


# --------------------------------------------------------------------------
# tmp 沙箱：可任意改壞的生成器副本
# --------------------------------------------------------------------------

# C 與 UTF-8 collation 對這三列的排序不同（本機實測：
#   LC_ALL=C          → B-x _z a-y
#   LC_ALL=en_US.UTF-8 → _z a-y B-x）
_LOCALE_PROBE_ROWS = [["a-y", "x"], ["B-x", "x"], ["_z", "x"]]


def _sandbox(tmp_path: Path, registry: dict) -> Path:
    """把生成器與一份自訂註冊表複製到 tmp；回傳該 scripts 目錄。"""
    sdir = tmp_path / "scripts"
    sdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GEN, sdir / GEN.name)
    (sdir / "fact_keys.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return sdir


def _mutate(sdir: Path, old: str, new: str) -> None:
    p = sdir / GEN.name
    src = p.read_text(encoding="utf-8")
    assert old in src, f"mutation 目標字串不存在，測試已與實作脫節: {old!r}"
    p.write_text(src.replace(old, new, 1), encoding="utf-8")


def _discriminating_locale() -> str | None:
    """找一個與 C 排序結果不同的 locale；找不到回 None。"""
    probe = "a-y\nB-x\n_z\n"
    base = subprocess.run(
        ["sort"], input=probe, capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"},
    ).stdout
    for cand in ("en_US.UTF-8", "en_US.utf8", "C.UTF-8", "en_GB.UTF-8"):
        got = subprocess.run(
            ["sort"], input=probe, capture_output=True, text=True,
            env={**os.environ, "LC_ALL": cand},
        )
        if got.returncode == 0 and got.stdout != base:
            return cand
    return None


# --------------------------------------------------------------------------
# T-2.1-M1 — 排序改為未指定 locale ⇒ 決定性測試轉紅（行為引信）
# --------------------------------------------------------------------------


def test_t21_m1a_sort_is_load_bearing(tmp_path):
    """環境無關的引信：拿掉排序即輸出改變 ⇒ 證明 `sort` 真的承重。

    註冊表 rows 刻意亂序；有排序 ⇒ 輸出照序數，無排序 ⇒ 照 JSON 原序。
    """
    reg = {"k": {"target": "t.md", "rows": [["030", "c"], ["010", "a"], ["020", "b"]]}}
    good = _sandbox(tmp_path / "good", reg)
    bad = _sandbox(tmp_path / "bad", reg)
    _mutate(bad, "| LC_ALL=C sort", "| cat")

    out_good = _run([str(good / GEN.name)]).stdout
    out_bad = _run([str(bad / GEN.name)]).stdout
    assert out_good != out_bad, "拿掉排序輸出未變 ⇒ 這條 mutation 是空心的"
    assert out_good.splitlines()[1].startswith("010"), out_good


def test_t21_m1b_locale_pin_removal_breaks_determinism(tmp_path):
    """TODO 指定之 mutation：把排序改為未指定 locale ⇒ 決定性 oracle 轉紅。

    判準＝同一支腳本在兩種環境 locale 下輸出是否一致。
    釘住版：一致（綠）。拿掉釘子：不一致（紅）⇒ 證明釘子承重。
    """
    loc = _discriminating_locale()
    if loc is None:
        pytest.skip(
            "本機無任何與 C 排序不同的 locale ⇒ 此差分引信無鑑別力。"
            "環境能力限制，非機制放行；同一條 mutation 另由 m1a 以環境無關方式守住。"
        )

    reg = {"k": {"target": "t.md", "rows": _LOCALE_PROBE_ROWS}}
    pinned = _sandbox(tmp_path / "pinned", reg)
    unpinned = _sandbox(tmp_path / "unpinned", reg)
    _mutate(unpinned, "| LC_ALL=C sort", "| sort")

    def out(sdir: Path, lc: str) -> str:
        return _run([str(sdir / GEN.name)], env_extra={"LC_ALL": lc}).stdout

    assert out(pinned, "C") == out(pinned, loc), (
        "釘住 LC_ALL=C 後輸出仍隨環境改變 ⇒ 決定性契約未成立"
    )
    assert out(unpinned, "C") != out(unpinned, loc), (
        f"拿掉 LC_ALL=C 後輸出未隨 {loc} 改變 ⇒ 這條 mutation 是空心的"
    )


# --------------------------------------------------------------------------
# fail-closed 邊界
# --------------------------------------------------------------------------


def test_empty_registry_is_rc_zero_not_failure(tmp_path):
    """邊界①：註冊表為空物件 ⇒ rc=0（無事可做，不得 fail）。"""
    sdir = _sandbox(tmp_path, {})
    for args in ([], ["--check"]):
        r = _run([str(sdir / GEN.name), *args])
        assert r.returncode == 0, f"空註冊表 {args} 應 rc=0，實得 {r.returncode}\n{r.stderr}"


def test_missing_registry_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {})
    (sdir / "fact_keys.json").unlink()
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0 and "fail-closed" in r.stderr


def test_malformed_registry_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {})
    (sdir / "fact_keys.json").write_text("[1,2,3]", encoding="utf-8")
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0 and "fail-closed" in r.stderr


@pytest.mark.parametrize(
    "badkey",
    ["Governance-Order", "with space", "under_score", "-leading", "中文鍵"],
)
def test_illegal_key_name_is_fail_closed(tmp_path, badkey):
    """key 字元集合是安全前提：它會被嵌進 grep/sed 正則。"""
    sdir = _sandbox(tmp_path / badkey.replace(" ", "_"), {badkey: {"target": "t.md", "rows": []}})
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0, f"非法 key {badkey!r} 應 fail-closed"
    assert "fail-closed" in r.stderr


def test_reserved_schema_key_is_skipped_not_treated_as_fact_key(tmp_path):
    sdir = _sandbox(tmp_path, {"_schema": {"about": "doc"}})
    r = _run([str(sdir / GEN.name)])
    assert r.returncode == 0, r.stderr
    assert r.stdout == "", "保留鍵不得產生 block"


@pytest.mark.parametrize("bad_target", ["/etc/passwd", "../outside.md", "a/../../b.md"])
def test_target_path_escape_is_fail_closed(tmp_path, bad_target):
    sdir = _sandbox(tmp_path / bad_target.replace("/", "_"), {"k": {"target": bad_target, "rows": []}})
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0, f"target {bad_target!r} 應被拒"


def test_missing_target_key_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {"k": {"rows": []}})
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0 and "fail-closed" in r.stderr


@pytest.mark.parametrize("bad_rows", [{"rows": "notalist"}, {"rows": [["a"], "b"]}, {"rows": [[1]]}])
def test_rows_type_violation_is_fail_closed(tmp_path, bad_rows):
    reg = {"k": {"target": "t.md", **bad_rows}}
    sdir = _sandbox(tmp_path / str(abs(hash(str(bad_rows)))), reg)
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0, f"rows={bad_rows!r} 應 fail-closed"


def test_missing_target_file_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/nope.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--check"], cwd=tmp_path)
    assert r.returncode != 0
    assert "MISSING TARGET" in r.stderr and "docs/nope.md" in r.stderr


def test_no_marker_is_fail_closed_not_silent_pass(tmp_path):
    """🔴 TODO 邊界②：宿主檔缺邊界標記 ⇒ rc≠0（本條若失守，機制形同關閉）。"""
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "t.md").write_text("沒有任何標記\n", encoding="utf-8")
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, "缺標記竟放行 ⇒ fail-open"
    assert "MARKER" in r.stderr and "docs/t.md" in r.stderr


def test_duplicate_markers_are_fail_closed(tmp_path):
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "t.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n"
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n",
        encoding="utf-8",
    )
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0 and "MARKER" in r.stderr


def test_write_refuses_when_markers_absent(tmp_path):
    """--write 不得憑空追加：位置不明的寫入比不寫更危險。"""
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    tgt = root / "docs" / "t.md"
    tgt.write_text("原文\n", encoding="utf-8")
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--write"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0
    assert tgt.read_text(encoding="utf-8") == "原文\n", "被拒時不得留下任何修改"


def test_write_then_check_round_trip(tmp_path):
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    tgt = root / "docs" / "t.md"
    tgt.write_text(
        "前言\n<!-- BEGIN GENERATED: k -->\n舊內容\n<!-- END GENERATED: k -->\n後記\n",
        encoding="utf-8",
    )
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["020", "b"], ["010", "a"]]}})
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    assert _run([str(sdir / GEN.name), "--check"], env_extra=env).returncode != 0
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    assert _run([str(sdir / GEN.name), "--check"], env_extra=env).returncode == 0
    body = tgt.read_text(encoding="utf-8")
    assert body.startswith("前言\n") and body.endswith("後記\n"), "標記外的內容不得被動到"
    assert "舊內容" not in body
    assert body.index("010\ta") < body.index("020\tb")


@pytest.mark.parametrize("args", [["--bogus"], ["--check", "--write"], ["check"]])
def test_unknown_or_extra_args_are_fail_closed(args):
    r = _gen(*args)
    assert r.returncode == 2, f"{args} 應 rc=2，實得 {r.returncode}\n{r.stderr}"


def test_fixtures_differ_only_in_block_content():
    """正反 fixture 的鑑別力來源必須是「block 內容」，不是「有沒有標記」。"""
    c = (CLEAN / TARGET_REL).read_text(encoding="utf-8").splitlines()
    d = (DRIFTED / TARGET_REL).read_text(encoding="utf-8").splitlines()
    assert len(c) == len(d), "兩份 fixture 列數不同 ⇒ 對照失去鑑別力"
    assert BEGIN in c and END in c and BEGIN in d and END in d
    diff = [i for i, (a, b) in enumerate(zip(c, d)) if a != b]
    assert len(diff) == 1, f"drifted 應恰一列不同，實得 {len(diff)} 列"
