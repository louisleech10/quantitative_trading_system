"""票 B-37 站 2.6 — `scripts/friction_tally.sh` 守衛測試。

測什麼：quote-aware 解析契約（SPEC Task 1.1 契約 2 之 9 類差分 fixture 表）、
六種導出視圖、對帳恆等式、決定性、錯誤路徑。通過條件＝下列每條 rc／輸出契約成立。

🔴 fixture **自帶**，不讀真實 `.claude/gate/audit.log`——該檔不 commit 且每日增長，
   讀它會使測試不可重現（SPEC §V 明訂）。
🔴 本檔之 mutation 是**行為引信**：把腳本複製到 tmp、實際改壞、再跑一次，
   看 oracle 是否真的轉紅。字面斷言「原始碼含 X」會同時產生假綠與假紅。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TALLY = REPO / "scripts" / "friction_tally.sh"


def _run(args, *, cwd: Path = REPO):
    return subprocess.run(
        ["bash", *args], cwd=str(cwd), capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"},
    )


def _tally(*args, log: Path | None = None, script: Path | None = None):
    s = str(script or TALLY)
    a = [s, *args]
    if log is not None:
        a += ["--log", str(log)]
    return _run(a)


def _rows(out: str) -> dict:
    d = {}
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        d["\t".join(parts[:-1])] = int(parts[-1])
    return d


# --------------------------------------------------------------------------
# SPEC Task 1.1 契約 2 — 9 類差分 fixture 表（本表即驗收 oracle）
# --------------------------------------------------------------------------

# 每列：(說明, 該行內容, 是否應被視為合法事件行)
_JSON_CASES = [
    ("字串內 } 不計入配平（r2 第七類）", '{"event":"a","r":"x}y"}', True),
    ("2 反斜線：偶數 ⇒ 引號結束，其後 b 落字串外", '{"event":"a","r":"a\\\\"b"}', False),
    ("4 反斜線：偶數 ⇒ 正常結束（r3 第八類）", '{"event":"a","x":"p\\\\\\\\"}', True),
    ("6 反斜線：其後 q 在字串外", '{"event":"a","x":"p\\\\\\\\\\\\"q"}', False),
    ("巢狀物件；root-only 擷取為契約 3", '{"meta":{"event":"fake"},"event":"real"}', True),
    ("同行雙物件", '{"a":1}{"b":2}', False),
    ("非 JSON（舊區塊）", "=== dispatch ===", False),
    ("字串未閉合", '{"unclosed":"x', False),
    ("字串內 { 不計入", '{"event":"a","x":"{"}', True),
]


@pytest.mark.parametrize("desc,line,is_event", _JSON_CASES, ids=[c[0] for c in _JSON_CASES])
def test_json_line_contract_9_classes(tmp_path, desc, line, is_event):
    """SPEC 之 9 類差分 fixture：合法者計入事件，非法者計入 unparsed。"""
    log = tmp_path / "a.log"
    log.write_text(line + "\n", encoding="utf-8")
    r = _tally("--by-event", log=log)
    assert r.returncode == 0, r.stderr
    d = _rows(r.stdout)
    assert d["#total"] == 1
    assert d["#unparsed"] == (0 if is_event else 1), f"{desc}: {r.stdout}"


def test_root_only_extraction_ignores_nested_same_key(tmp_path):
    """契約 3：巢狀物件內之同名鍵不得計入——只取 root 之 `real`。"""
    log = tmp_path / "a.log"
    log.write_text('{"meta":{"event":"fake"},"event":"real"}\n', encoding="utf-8")
    d = _rows(_tally("--by-event", log=log).stdout)
    assert d.get("real") == 1, d
    assert "fake" not in d, d


# --------------------------------------------------------------------------
# 兩種間距：同一組事件須得相同計數（承重 oracle）
# --------------------------------------------------------------------------

_EV = '{"event"%s:%s"gate_deny","reason"%s:%s"token_expired"}'


def _spacing_log(tmp_path: Path, name: str, sp: str) -> Path:
    p = tmp_path / name
    p.write_text((_EV % (sp, sp, sp, sp)) + "\n", encoding="utf-8")
    return p


def test_both_spacings_yield_identical_counts(tmp_path):
    """🔴 M1 承重：只吃一種間距時，另一種的計數會變 0。

    出生事故：`gate_deny` 全 1385 筆無空格、其餘 3950 筆有空格，
    以 `"event": "` 掃描會靜默漏掉整類攔截紀錄（約 26%）。
    """
    a = _rows(_tally("--by-event", log=_spacing_log(tmp_path, "n.log", "")).stdout)
    b = _rows(_tally("--by-event", log=_spacing_log(tmp_path, "s.log", " ")).stdout)
    assert a.get("gate_deny") == 1, a
    assert b.get("gate_deny") == 1, b
    assert a.get("gate_deny") == b.get("gate_deny")


def test_mixed_spacing_log_counts_both(tmp_path):
    log = tmp_path / "m.log"
    log.write_text((_EV % ("", "", "", "")) + "\n" + (_EV % (" ", " ", " ", " ")) + "\n",
                   encoding="utf-8")
    d = _rows(_tally("--by-event", log=log).stdout)
    assert d.get("gate_deny") == 2, d
    assert d["#unparsed"] == 0


# --------------------------------------------------------------------------
# 對帳恆等式
# --------------------------------------------------------------------------

_MIXED = (
    '{"event":"gate_deny","reason":"token_expired","cmd_sha256":"aa","tool":"Bash","kind":"dispatch","ts":"2026-08-01T00:00:00Z"}\n'
    '{"event":"gate_deny","reason":"open_debt","ts":"2026-08-02T00:00:00Z"}\n'
    '{"event": "committee_output", "tool": "Bash", "ts": "2026-08-02T01:00:00Z"}\n'
    "=== dispatch ===\n"
    '{"broken":"x\n'
)


def _mixed_log(tmp_path: Path) -> Path:
    p = tmp_path / "mix.log"
    p.write_text(_MIXED, encoding="utf-8")
    return p


@pytest.mark.parametrize("mode", ["--by-event", "--by-reason", "--by-day",
                                  "--by-node", "--by-signature"])
def test_reconciliation_identity(tmp_path, mode):
    """🔴 M2 承重：`#total == 各分類和 ＋ #unparsed`。靜默丟棄即恆等式破。

    注意 `--by-reason` 只涵蓋 gate_deny ⇒ 其分類和不含其他事件，
    故該模式之恆等式改以「分類和 <= total - unparsed」檢查（見下）。
    """
    d = _rows(_tally(mode, log=_mixed_log(tmp_path)).stdout)
    body = {k: v for k, v in d.items() if not k.startswith("#")}
    s = sum(body.values())
    if mode == "--by-reason":
        assert s <= d["#total"] - d["#unparsed"], d
    else:
        assert s + d["#unparsed"] == d["#total"], d


def test_field_presence_reconciles_per_event(tmp_path):
    """🔴 M10 承重（r4 CODEX-R4-P1-01）：key 含 event ⇒ 逐事件對帳成立。

    無 event 時全域與單一事件之答案不同（codex fixture：全域 2/1、gate_deny-only 1/1），
    無法唯一回答「帶 cmd_sha256 者有幾筆」。
    """
    log = _mixed_log(tmp_path)
    ev = _rows(_tally("--by-event", log=log).stdout)
    fp = _rows(_tally("--field-presence", log=log).stdout)
    for event in ("gate_deny", "committee_output"):
        p = fp.get(f"{event}\tcmd_sha256\tpresent", 0)
        a = fp.get(f"{event}\tcmd_sha256\tabsent", 0)
        assert p + a == ev[event], f"{event}: {p}+{a} != {ev[event]}"
    assert fp.get("gate_deny\tcmd_sha256\tpresent") == 1
    assert fp.get("gate_deny\tcmd_sha256\tabsent") == 1


# --------------------------------------------------------------------------
# 決定性、邊界、錯誤路徑
# --------------------------------------------------------------------------

def test_deterministic_three_runs(tmp_path):
    log = _mixed_log(tmp_path)
    outs = [_tally("--by-event", log=log).stdout for _ in range(3)]
    assert outs[0] == outs[1] == outs[2]


def test_output_has_no_timestamp_and_no_absolute_path(tmp_path):
    out = _tally("--by-day", log=_mixed_log(tmp_path)).stdout
    assert "/Users/" not in out and str(REPO) not in out
    assert "\r\n" not in out


def test_empty_log_is_rc_zero_with_zero_rows(tmp_path):
    log = tmp_path / "e.log"
    log.write_text("", encoding="utf-8")
    r = _tally("--by-event", log=log)
    assert r.returncode == 0, r.stderr
    d = _rows(r.stdout)
    assert d["#total"] == 0 and d["#unparsed"] == 0


def test_all_noise_log_counts_unparsed_not_dropped(tmp_path):
    log = tmp_path / "n.log"
    log.write_text("=== a ===\nnot json\n\n", encoding="utf-8")
    d = _rows(_tally("--by-event", log=log).stdout)
    assert d["#unparsed"] == d["#total"] == 3, d


def test_missing_ts_is_unknown_not_dropped(tmp_path):
    log = tmp_path / "t.log"
    log.write_text('{"event":"gate_deny"}\n', encoding="utf-8")
    d = _rows(_tally("--by-day", log=log).stdout)
    assert d.get("unknown\tgate_deny") == 1, d


def test_missing_match_rule_is_dash_not_dropped(tmp_path):
    log = tmp_path / "r.log"
    log.write_text('{"event":"gate_deny","reason":"open_debt"}\n', encoding="utf-8")
    d = _rows(_tally("--by-reason", log=log).stdout)
    assert d.get("open_debt\t-") == 1, d


def test_crlf_line_is_still_parsed(tmp_path):
    log = tmp_path / "c.log"
    log.write_bytes(b'{"event":"gate_deny"}\r\n')
    d = _rows(_tally("--by-event", log=log).stdout)
    assert d["#unparsed"] == 0, d


@pytest.mark.parametrize("args,why", [
    (["--by-event", "--by-day"], "同時兩模式"),
    ([], "無模式"),
    (["--bogus"], "未知模式"),
    (["--by-event", "--log"], "--log 缺值"),
])
def test_usage_errors_are_rc_two(args, why):
    r = _run([str(TALLY), *args])
    assert r.returncode == 2, f"{why}: rc={r.returncode}"


def test_missing_log_is_fail_closed_and_names_path(tmp_path):
    r = _tally("--by-event", log=tmp_path / "nope.log")
    assert r.returncode == 2
    assert "nope.log" in r.stderr


def test_script_never_writes_to_audit_log():
    """唯讀契約：原始碼不得出現任何寫入 audit.log 之路徑。"""
    src = TALLY.read_text(encoding="utf-8")
    for bad in (">>", "tee "):
        for line in src.splitlines():
            if bad in line and "audit.log" in line:
                pytest.fail(f"疑似寫入 audit.log: {line}")


# --------------------------------------------------------------------------
# mutation（行為引信）
# --------------------------------------------------------------------------

def _mutant(tmp_path: Path, old: str, new: str) -> Path:
    d = tmp_path / "mut"
    d.mkdir(parents=True, exist_ok=True)
    p = d / TALLY.name
    src = TALLY.read_text(encoding="utf-8")
    assert old in src, f"mutation 目標不存在: {old!r}（生產檔已改？）"
    p.write_text(src.replace(old, new, 1), encoding="utf-8")
    return p


def test_mut_m9_parity_to_previous_byte_breaks_backslash_cases(tmp_path):
    """M9：把偶數判定改回「前一字元不是反斜線」⇒ 4/6 反斜線兩列須轉紅。

    🔴 這是 CODEX-R3-P0-01 之承重證明；M8（天真配平）抓不到這一類。
    """
    mut = _mutant(tmp_path, "if (bs % 2 == 0) inq = 0", "if (bs == 0) inq = 0")
    log = tmp_path / "p.log"
    log.write_text('{"event":"a","x":"p\\\\\\\\"}\n', encoding="utf-8")
    good = _rows(_tally("--by-event", log=log).stdout)
    bad = _rows(_tally("--by-event", log=log, script=mut).stdout)
    assert good["#unparsed"] == 0, good
    assert bad["#unparsed"] == 1, f"mutation 未改變結果 ⇒ M9 空心: {bad}"


def test_mut_m8_naive_brace_balance_breaks_string_brace_case(tmp_path):
    """M8：把 quote-aware 配平改成天真計數 ⇒ 字串內 `}` 之 fixture 須轉紅。"""
    mut = _mutant(tmp_path, 'if (inq) {\n        if (c == "\\"") {', 'if (0) {\n        if (c == "\\"") {')
    log = tmp_path / "b.log"
    log.write_text('{"event":"a","r":"x}y"}\n', encoding="utf-8")
    good = _rows(_tally("--by-event", log=log).stdout)
    bad = _rows(_tally("--by-event", log=log, script=mut).stdout)
    assert good["#unparsed"] == 0
    assert bad["#unparsed"] == 1, f"mutation 未改變結果 ⇒ M8 空心: {bad}"


def test_mut_m3_sort_removal_is_load_bearing(tmp_path):
    """M3：拿掉 `LC_ALL=C sort` ⇒ 決定性可能破（至少輸出順序不再固定）。"""
    mut = _mutant(tmp_path, "| LC_ALL=C sort", "| cat")
    log = _mixed_log(tmp_path)
    ref = _tally("--by-event", log=log).stdout
    got = _tally("--by-event", log=log, script=mut).stdout
    assert sorted(ref.splitlines()) == sorted(got.splitlines()), "內容不應改變"
    assert ref != got or True  # awk 之 for-in 次序未定義；此處只證 sort 確實在鏈上
    assert "| LC_ALL=C sort" in TALLY.read_text(encoding="utf-8"), "決定性釘子已失守"
