"""DOCROT2 Task 3.1–3.2（票 B-63）— finding 類別雙填與適用門檻、收案量測事件、擋下事件、成效報表。

測什麼：`docs/DOCROT2_TODO.md` Task 3.1、3.2 驗證欄之 fixture 逐條 rc 對照，外加邊界與原因碼。
fixture 形態：一律在 tmp 建隔離 repo 並複製被測腳本（門檻值寫入副本之 governance_verdicts.json），不觸及本 repo audit。
門檻判定只看開債事件之 audit 序號：以「開輪後取其序號、再把副本門檻設成序號或序號減一」決定該輪屬門檻前或後。
🔴 後加守衛遮蔽先前守衛之防範：同一情境可能被兩道守衛擋下者，一律斷言原因碼（COMPLETENESS FAIL 字樣、
   `DOCROT2_METRIC_REASON=`、`⑦`），不只斷言 rc。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from tests.governance import test_debt_clear as _tdc
from tests.governance import test_docrot2_write_guard as _wg
from tests.governance import test_govb1_b31_recovery as _b31

REPO = Path(__file__).resolve().parents[2]
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
CATS = json.loads((REPO / "scripts" / "governance_verdicts.json").read_text(encoding="utf-8"))["finding_category_values"]
CATEGORY_HELPERS = ("_finding_category.py", "governance_verdicts.json")
METRIC_HELPERS = CATEGORY_HELPERS + ("_docrot2_metrics.py", "docrot2_metric_contract.json", "reconcile_body_hash.sh",
                                     "_synth_attr.py", "_live_doc_write_guard.py", "_live_doc_registry.py")


def _copy(scripts: Path, names) -> None:
    for name in names:
        src = REPO / "scripts" / name
        shutil.copy2(src, scripts / name)
        if name.endswith(".sh"):
            (scripts / name).chmod(0o755)


def _set_threshold(scripts: Path, value: int) -> None:
    p = scripts / "governance_verdicts.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["category_required_after_audit_sequence"] = value
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _events(audit: Path, name: str) -> list[dict]:
    out = []
    if not audit.is_file():
        return out
    for ln in audit.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("{"):
            rec = json.loads(s)
            if rec.get("event") == name:
                out.append(rec)
    return out


def _open_seq(audit: Path, rid: str) -> int:
    opens = [e for e in _events(audit, "committee_round_open") if e.get("round_id") == rid]
    assert len(opens) == 1
    return opens[0]["sequence"]


def _place(scripts: Path, audit: Path, rid: str, *, post: bool) -> None:
    """把副本門檻設在該輪開債序號之前（post）或恰等於它（pre）。"""
    seq = _open_seq(audit, rid)
    _set_threshold(scripts, seq - 1 if post else seq)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env={**os.environ, **GIT_ENV})


# ================================================================ Task 3.1：completeness_check --single

P1_NO_CAT = (
    "## CODEX-R1-P1-01\n\n"
    "**斷言**: 門檻判定只看開債序號之探針\n\n"
    "**碼證**: scripts/completeness_check.sh:1 探針\n"
    "CODE-ANCHOR: scripts/completeness_check.sh:1\n"
    "MUTATION: 門檻比較改恆真\n\n"
    "**來源摘要**: scripts/completeness_check.sh#0123456789ab\n\n"
    "VERDICT: blocked\nBLOCKED-BY: CODEX-R1-P1-01\nCLOSED:\n"
)


def _with_cat(text: str, cat: str) -> str:
    return text.replace("**來源摘要**", f"**類別**: {cat}\n\n**來源摘要**", 1)


def _cc_harness(tmp_path: Path) -> dict:
    h = _b31._harness(tmp_path)
    _copy(h["scripts"], CATEGORY_HELPERS)
    return h


def _open(h: dict, *, kind: str = "review", fams=("codex",), name: str | None = None) -> tuple[str, str]:
    rid = str(uuid.uuid4())
    name = name or rid[:8]
    out_prefix = f"handoffs/d2c-{name}"
    _b31._open_round(h, round_id=rid, session=f"s-{name}", fams=list(fams), out_prefix=out_prefix, brief_kind=kind)
    return rid, out_prefix


def _single(h: dict, path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(h["scripts"] / "completeness_check.sh"), "--single", str(path), "--family", "codex", *extra],
                          cwd=h["root"], env=h["env"], capture_output=True, text=True)


def _write(h: dict, rel: str, text: str) -> Path:
    p = h["root"] / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_round_after_threshold_p1_without_category_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    rid, _ = _open(h)
    _place(h["scripts"], h["audit"], rid, post=True)
    r = _single(h, _write(h, "handoffs/f-codex.md", P1_NO_CAT), "--round-id", rid)
    assert r.returncode == 1 and "finding 缺類別" in r.stderr, r.stderr


def test_round_before_threshold_p1_without_category_rc0(tmp_path):
    """mutation ④（門檻比較改恆真）之靶：同一 bytes 以門檻前輪送入須 rc=0。"""
    h = _cc_harness(tmp_path)
    rid, _ = _open(h)
    _place(h["scripts"], h["audit"], rid, post=False)
    r = _single(h, _write(h, "handoffs/f-codex.md", P1_NO_CAT), "--round-id", rid)
    assert r.returncode == 0, r.stderr


def test_same_bytes_two_round_ids_rc0_rc1(tmp_path):
    """邊界②：同一交件 bytes 以門檻前、後兩個 round id 送入 ⇒ rc 0／1。"""
    h = _cc_harness(tmp_path)
    pre, _ = _open(h, name="pre")
    post, _ = _open(h, name="post")
    _set_threshold(h["scripts"], _open_seq(h["audit"], pre))
    f = _write(h, "handoffs/f-codex.md", P1_NO_CAT)
    assert _single(h, f, "--round-id", pre).returncode == 0
    r = _single(h, f, "--round-id", post)
    assert r.returncode == 1 and "finding 缺類別" in r.stderr, r.stderr


def test_no_round_id_p1_without_category_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    _set_threshold(h["scripts"], 10 ** 9)                      # 門檻再高，未給 round id 仍須類別
    r = _single(h, _write(h, "handoffs/f-codex.md", P1_NO_CAT))
    assert r.returncode == 1 and "finding 缺類別" in r.stderr, r.stderr


def test_unknown_round_id_requires_category_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    _set_threshold(h["scripts"], 10 ** 9)
    r = _single(h, _write(h, "handoffs/f-codex.md", P1_NO_CAT), "--round-id", "no-such-round")
    assert r.returncode == 1 and "finding 缺類別" in r.stderr, r.stderr


def test_category_outside_set_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    r = _single(h, _write(h, "handoffs/f-codex.md", _with_cat(P1_NO_CAT, "docsync")))
    assert r.returncode == 1 and "類別不在封閉值集" in r.stderr, r.stderr


@pytest.mark.parametrize("cat", CATS)
def test_each_closed_value_accepted_rc0(tmp_path, cat):
    h = _cc_harness(tmp_path)
    r = _single(h, _write(h, "handoffs/f-codex.md", _with_cat(P1_NO_CAT, cat)))
    assert r.returncode == 0, r.stderr


def test_duplicate_category_lines_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    text = _with_cat(_with_cat(P1_NO_CAT, "doc-sync"), "other")
    r = _single(h, _write(h, "handoffs/f-codex.md", text))
    assert r.returncode == 1 and "類別行重複" in r.stderr, r.stderr


def test_category_inside_fence_does_not_count_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    text = P1_NO_CAT.replace("**來源摘要**", "```\n**類別**: doc-sync\n```\n\n**來源摘要**", 1)
    r = _single(h, _write(h, "handoffs/f-codex.md", text))
    assert r.returncode == 1 and "finding 缺類別" in r.stderr, r.stderr


def test_sentinel_without_category_after_threshold_rc1(tmp_path):
    """邊界①：零 findings sentinel 亦須類別。"""
    h = _cc_harness(tmp_path)
    text = "## CODEX-R1-P3-00\n\n**斷言**: 本輪逐項核對後無 finding\n\n**碼證**: pytest 探針 rc=0\n\nVERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n"
    r = _single(h, _write(h, "handoffs/f-codex.md", text))
    assert r.returncode == 1 and "finding 缺類別" in r.stderr, r.stderr
    r = _single(h, _write(h, "handoffs/g-codex.md", text.replace("**碼證**", "**類別**: other\n\n**碼證**")))
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("line,ok", [
    ("**類別**: doc-sync", True),
    ("**類別**：doc-sync", True),
    ("**類別**:doc-sync  ", True),
    ("**類別** : doc-sync", True),
    ("**類別**: doc-sync（理由）", False),
    ("**類別**: Doc-Sync", False),
    ("**類別**: doc-sync **類別**: other", False),
    ("**類別**:", False),
    ("**類別**: doc-sync\r", True),                         # review-r1 COMPOSER-R1-P2-01：行尾 CR
    ("<!-- **類別**: doc-sync -->", False),                 # review-r1 CODEX-R1-P1-01：註解內不算
    ("**類別**: doc-sync<!-- 說明 -->", True),
    ("　**類別**: doc-sync", True),
])
def test_label_grammar_same_in_awk_and_python(tmp_path, line, ok):
    """completeness_check.sh（awk）與 _finding_category.py（收斂檔／量測）對同一行之判定須一致。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("fcat", REPO / "scripts" / "_finding_category.py")
    fcat = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fcat)
    h = _cc_harness(tmp_path)
    text = P1_NO_CAT.replace("**來源摘要**", f"{line}\n\n**來源摘要**", 1)
    awk_ok = _single(h, _write(h, "handoffs/f-codex.md", text)).returncode == 0
    val, err = fcat.single_category([line], CATS)
    assert awk_ok is ok and (err is None) is ok, (awk_ok, val, err)


def test_round_id_without_single_rc2(tmp_path):
    h = _cc_harness(tmp_path)
    r = subprocess.run(["bash", str(h["scripts"] / "completeness_check.sh"), "--round-id", "x"],
                       cwd=h["root"], env=h["env"], capture_output=True, text=True)
    assert r.returncode == 2 and "--round-id 只與 --single 併用" in r.stderr, r.stderr


def test_category_helper_missing_fail_closed_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    (h["scripts"] / "_finding_category.py").unlink()
    r = _single(h, _write(h, "handoffs/f-codex.md", _with_cat(P1_NO_CAT, "doc-sync")))
    assert r.returncode == 1 and "缺 scripts/_finding_category.py" in r.stderr, r.stderr


def test_category_config_invalid_fail_closed_rc1(tmp_path):
    h = _cc_harness(tmp_path)
    p = h["scripts"] / "governance_verdicts.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["finding_category_values"] = ["doc sync"]
    p.write_text(json.dumps(d), encoding="utf-8")
    r = _single(h, _write(h, "handoffs/f-codex.md", _with_cat(P1_NO_CAT, "doc-sync")))
    assert r.returncode == 1, r.stderr


def test_lock_path_unchanged_by_category():
    """G-1 三入口矩陣：類別閘只在 --single 區塊呼叫 check-single；--lock／synth 之 _validate_finding_body 不含類別判定。"""
    src = (REPO / "scripts" / "completeness_check.sh").read_text(encoding="utf-8")
    assert src.count("_finding_category.py\" check-single") == 2
    single = src[src.index('if [ -n "${SINGLE_ARG}" ]; then'):src.index('if [ -n "${LOCK_ARG}" ]; then')]
    assert single.count("_finding_category.py\" check-single") == 2
    body = src[src.index("_validate_finding_body() {"):src.index("_validate_anchors() {")]
    assert "類別" not in body


# ── review-r1 CODEX-R1-P1-01：類別只有一份文法；P1 兩 token 只在碼證欄位內

def _probe(h: dict, name: str, text: str) -> subprocess.CompletedProcess:
    return _single(h, _write(h, f"handoffs/{name}-codex.md", text))


def test_category_in_html_comment_rejected(tmp_path):
    h = _cc_harness(tmp_path)
    text = P1_NO_CAT.replace("**來源摘要**", "<!--\n**類別**: doc-sync\n-->\n\n**來源摘要**", 1)
    r = _probe(h, "cmt", text)
    assert r.returncode == 1 and "finding 缺類別" in r.stderr, r.stderr
    import importlib.util
    spec = importlib.util.spec_from_file_location("fcat", REPO / "scripts" / "_finding_category.py")
    fcat = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fcat)
    assert fcat.single_category(text.splitlines(), CATS)[0] is None


def test_p1_tokens_outside_code_field_rejected(tmp_path):
    h = _cc_harness(tmp_path)
    text = (
        "## CODEX-R1-P1-01\n\n**斷言**: 兩 token 寫在碼證欄外之探針\n\n**碼證**: 見某章節用詞差異。\n\n"
        "**類別**: code-contract\n\n**來源摘要**: scripts/x.sh#0123456789ab\n\n"
        "正文。\nCODE-ANCHOR: scripts/completeness_check.sh:1\nMUTATION: 刪掉判定會紅。\n"
    )
    r = _probe(h, "outside", text)
    assert r.returncode == 1 and "has_anchor=0 has_mutation=0" in r.stderr, r.stderr
    inside = text.replace("**碼證**: 見某章節用詞差異。", "**碼證**: 見某章節用詞差異。\nCODE-ANCHOR: scripts/completeness_check.sh:1\nMUTATION: 刪掉判定會紅。")
    assert _probe(h, "inside", inside).returncode == 0


def test_p1_tokens_in_html_comment_rejected(tmp_path):
    h = _cc_harness(tmp_path)
    text = (
        "## CODEX-R1-P1-01\n\n**斷言**: 兩 token 寫在註解內之探針\n\n**碼證**: 見下。\n"
        "<!-- CODE-ANCHOR: scripts/completeness_check.sh:1\nMUTATION: 刪掉判定會紅。 -->\n\n"
        "**類別**: code-contract\n\n**來源摘要**: scripts/x.sh#0123456789ab\n"
    )
    r = _probe(h, "tokcmt", text)
    assert r.returncode == 1 and "has_anchor=0 has_mutation=0" in r.stderr, r.stderr


def test_unicode_fence_parser_agreement(tmp_path):
    """U+3000 前導之 ``` 不是 fence（與 awk LC_ALL=C 之 [[:space:]] 同）：--single 與收斂檔解析判定一致。"""
    h = _cc_harness(tmp_path)
    text = P1_NO_CAT.replace("**來源摘要**", "　```\n**類別**: doc-sync\n　```\n\n**來源摘要**", 1)
    single_ok = _probe(h, "u3000", text).returncode == 0
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="doc-sync")
    synth_text = synth.read_text(encoding="utf-8").replace("**類別**: doc-sync", "　```\n**類別**: doc-sync\n　```")
    synth.write_text(synth_text, encoding="utf-8")
    synth_ok = _attr(synth, ctx).returncode == 0
    assert single_ok is True and synth_ok is True, (single_ok, synth_ok)
    ascii_fence = P1_NO_CAT.replace("**來源摘要**", "```\n**類別**: doc-sync\n```\n\n**來源摘要**", 1)
    assert _probe(h, "asciifence", ascii_fence).returncode == 1


def test_category_audit_registry_invalid_fails_closed(tmp_path):
    """review-r1 CODEX-R1-P1-02：給了 round id 而 audit 不可讀 ⇒ FAIL（不得降級為「須類別」而放行合規檔）。"""
    h = _cc_harness(tmp_path)
    rid, _ = _open(h)
    env = {**h["env"], "DEBT_AUDIT_OVERRIDE": str(h["root"] / "no-such-audit.log")}
    f = _write(h, "handoffs/f-codex.md", _with_cat(P1_NO_CAT, "doc-sync"))
    r = subprocess.run(["bash", str(h["scripts"] / "completeness_check.sh"), "--single", str(f), "--family", "codex",
                        "--round-id", rid], cwd=h["root"], env=env, capture_output=True, text=True)
    assert r.returncode == 1 and "類別判定設定不可用" in r.stderr, r.stderr


def test_category_malformed_audit_line_fails_closed(tmp_path):
    h = _cc_harness(tmp_path)
    rid, _ = _open(h)
    text = h["audit"].read_text(encoding="utf-8")
    h["audit"].write_text("{broken json\n" + text, encoding="utf-8")
    f = _write(h, "handoffs/f-codex.md", _with_cat(P1_NO_CAT, "doc-sync"))
    r = _single(h, f, "--round-id", rid)
    assert r.returncode == 1 and "JSON 無法解析" in r.stderr, r.stderr


# ================================================================ Task 3.1：cx_run.sh 四個 --single 呼叫面

NO_CAT_P2 = (
    "## CODEX-R1-P2-01\n\n**斷言**: 交件路徑門檻前後判定之探針\n\n**碼證**: scripts/cx_run.sh:1 探針\n\n"
    # 不帶裁決塊：本檔只驗格式閘之 round id 傳遞，不觸發自動註冊（隔離沙箱未複製 gate.sh）
    "**來源摘要**: scripts/cx_run.sh#0123456789ab\n"
)
HOLLOW_NO_CAT = NO_CAT_P2.replace("**碼證**: scripts/cx_run.sh:1 探針", "**碼證**: 。")


def _cx_harness(tmp_path: Path, kind: str) -> dict:
    h = _b31._harness(tmp_path, kind=kind)
    _copy(h["scripts"], CATEGORY_HELPERS)
    return h


def _cx_deliver(h: dict, kind: str, content: str, *, post: bool, family: str = "codex"):
    rid, out_prefix = _open(h, kind=kind, fams=(family,))
    _place(h["scripts"], h["audit"], rid, post=post)
    out_rel = f"{out_prefix}-{family}.md"
    _write(h, out_rel, content)
    env = {**h["env"], "ROUND_ID": rid, "CX_STUB_MODE": "preserve"}
    proc = subprocess.run(["bash", str(h["scripts"] / "cx_run.sh"), family, h["brief_rel"], out_rel],
                          cwd=h["root"], env=env, capture_output=True, text=True)
    rows = [e for e in _events(h["audit"], "committee_family_result") if e.get("round_id") == rid]
    return proc, (rows[-1] if rows else {})


@pytest.mark.parametrize("post,state", [(False, "success"), (True, "format-failed")])
def test_cx_run_review_collection_passes_round_id(tmp_path, post, state):
    h = _cx_harness(tmp_path, "review")
    proc, latest = _cx_deliver(h, "review", NO_CAT_P2, post=post)
    assert latest.get("result_state") == state, proc.stderr[-2000:]


@pytest.mark.parametrize("post,state", [(False, "success"), (True, "format-failed")])
def test_cx_run_stamp_collection_passes_round_id(tmp_path, post, state):
    h = _cx_harness(tmp_path, "stamp")
    text = "## CODEX-R1-P3-00\n\n**斷言**: 本輪逐項核對後無 finding\n\n**碼證**: 探針 rc=0\n"
    proc, latest = _cx_deliver(h, "stamp", text, post=post)
    assert latest.get("result_state") == state, proc.stderr[-2000:]


def _fixup_rows(stderr: str) -> list[str]:
    m = re.search(r"── 可修補清單（逐條）──\n(.*?)\[cx_run\] ── 清單結束", stderr, re.S)
    return m.group(1).splitlines() if m else []


@pytest.mark.parametrize("post", [False, True])
def test_cx_run_format_fail_rerun_passes_round_id(tmp_path, post):
    """格式失敗重跑（逐條可修補清單）亦帶同一 round id：門檻前輪之清單不得出現「缺類別」列。"""
    h = _cx_harness(tmp_path, "review")
    proc, latest = _cx_deliver(h, "review", HOLLOW_NO_CAT, post=post)
    assert latest.get("result_state") == "format-failed", proc.stderr[-2000:]
    rows = _fixup_rows(proc.stderr)
    assert rows, proc.stderr[-2000:]
    has_cat = any("finding 缺類別" in r for r in rows)
    assert has_cat is post, rows


@pytest.mark.parametrize("post,rc", [(False, 0), (True, 3)])
def test_cx_run_selfcheck_passes_round_id(tmp_path, post, rc):
    h = _cx_harness(tmp_path, "review")
    rid, _ = _open(h)
    _place(h["scripts"], h["audit"], rid, post=post)
    f = _write(h, "handoffs/self-codex.md", NO_CAT_P2)
    r = subprocess.run(["bash", str(h["scripts"] / "cx_run.sh"), "--selfcheck", str(f), "--family", "codex", "--round-id", rid],
                       cwd=h["root"], env=h["env"], capture_output=True, text=True)
    assert r.returncode == rc, r.stderr


def test_cx_run_selfcheck_without_round_id_requires_category_rc3(tmp_path):
    h = _cx_harness(tmp_path, "review")
    _set_threshold(h["scripts"], 10 ** 9)
    f = _write(h, "handoffs/self-codex.md", NO_CAT_P2)
    r = subprocess.run(["bash", str(h["scripts"] / "cx_run.sh"), "--selfcheck", str(f), "--family", "codex"],
                       cwd=h["root"], env=h["env"], capture_output=True, text=True)
    assert r.returncode == 3 and "finding 缺類別" in r.stderr, r.stderr


def test_cx_run_prompt_selfcheck_carries_round_id():
    """委員自檢指示與交件檢查同一組參數（review／consult／closure 與 stamp 兩段 prompt）。"""
    src = (REPO / "scripts" / "cx_run.sh").read_text(encoding="utf-8")
    bare = "completeness_check.sh --single ${out} --family ${fam} 並確認"
    full = "completeness_check.sh --single ${out} --family ${fam} --round-id ${ROUND_ID:-} 並確認"
    assert src.count(full) == 2 and bare not in src


# ================================================================ Task 3.1：_synth_attr.py check_category

def _synth_fixture(tmp_path: Path, *, post: bool, committee: str | None, chair: str | None,
                   listed: str | None = None, heading: bool = True) -> tuple[Path, dict]:
    base = tmp_path / "attr"
    scripts = base / "scripts"
    scripts.mkdir(parents=True)
    _copy(scripts, CATEGORY_HELPERS + ("audit_events.json",))
    audit = base / "audit.log"
    rid = str(uuid.uuid4())
    audit.write_text(json.dumps({"event": "committee_round_open", "round_id": rid, "sequence": 7,
                                 "brief_kind": "review"}) + "\n", encoding="utf-8")
    _set_threshold(scripts, 6 if post else 7)
    sess = base / "handoffs" / "reconcile" / "20260916-docrot2-b3-review-r1"
    sess.mkdir(parents=True)
    (sess / "sources.lock").write_text(json.dumps({"round_id": rid}), encoding="utf-8")
    fid = "CODEX-R1-P2-01"
    assertion = "收斂檔主委類別與委員類別對照之探針斷言"
    header = "| 群集 | 嚴重度 | 來源 ID | 處置 |" + (" 主委類別 |" if chair is not None else "")
    sep = "|---|---|---|---|" + ("---|" if chair is not None else "")
    row = f"| 「{assertion}」 | P2 | {fid} | 採納（理由） |" + (f" {chair} |" if chair is not None else "")
    parts = ["# Reconcile", "", "## 群集 / 處置", "", header, sep, row, ""]
    if listed is not None:
        parts += (["### 類別不一致", ""] if heading else []) + [listed, ""]
    parts += ["**Verdict**: 可合併", "", "---", "", "## 附錄：findings 逐字保留", "", f"## {fid}", "",
              f"**斷言**: {assertion}", "", "**碼證**: scripts/_synth_attr.py:1", ""]
    if committee is not None:
        parts += [f"**類別**: {committee}", ""]
    parts += ["**來源摘要**: x#0123456789ab", ""]
    synth = sess / "synth.md"
    synth.write_text("\n".join(parts), encoding="utf-8")
    env = {**os.environ, "GOVERNANCE_TEST_HARNESS": "1", "DEBT_AUDIT_OVERRIDE": str(audit)}
    return synth, {"env": env, "values": scripts / "governance_verdicts.json"}


def _attr(synth: Path, ctx: dict, mode: str = "gate") -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(REPO / "scripts" / "_synth_attr.py"), str(synth), "--mode", mode,
                           "--values", str(ctx["values"])], cwd=str(REPO), env=ctx["env"], capture_output=True, text=True)


def test_category_mismatch_unlisted_rc1(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="code-contract")
    r = _attr(synth, ctx)
    assert r.returncode == 1 and "⑦ CODEX-R1-P2-01 委員類別「doc-sync」≠ 主委類別「code-contract」" in r.stderr, r.stderr


def test_category_mismatch_listed_with_disposition_rc0(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="code-contract",
                                listed="- CODEX-R1-P2-01：委員 doc-sync／主委 code-contract ⇒ 採納（依碼證屬行為缺陷）")
    r = _attr(synth, ctx)
    assert r.returncode == 0, r.stderr


def test_category_mismatch_listed_without_disposition_rc1(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="code-contract",
                                listed="- CODEX-R1-P2-01：委員 doc-sync／主委 code-contract")
    assert _attr(synth, ctx).returncode == 1


def test_category_mismatch_listed_outside_section_rc1(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="code-contract",
                                listed="- CODEX-R1-P2-01：委員 doc-sync／主委 code-contract ⇒ 採納", heading=False)
    assert _attr(synth, ctx).returncode == 1


def test_category_mismatch_table_row_in_section_not_cluster_row_rc0(tmp_path):
    table = "| ID | 委員 | 主委 | 處置 |\n|---|---|---|---|\n| CODEX-R1-P2-01 | doc-sync | code-contract | 採納 |"
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="code-contract", listed=table)
    r = _attr(synth, ctx)
    assert r.returncode == 0, r.stderr


def test_synth_before_threshold_without_column5_not_judged_rc0(tmp_path):
    """邊界②：門檻前舊收斂檔群集表無第 5 欄 ⇒ 不判。"""
    synth, ctx = _synth_fixture(tmp_path, post=False, committee=None, chair=None)
    r = _attr(synth, ctx)
    assert r.returncode == 0, r.stderr


def test_synth_after_threshold_without_column5_rc1(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair=None)
    r = _attr(synth, ctx)
    assert r.returncode == 1 and "第 5 欄（主委類別）" in r.stderr, r.stderr


def test_synth_after_threshold_committee_category_missing_rc1(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee=None, chair="doc-sync")
    r = _attr(synth, ctx)
    assert r.returncode == 1 and "附錄區塊之委員類別" in r.stderr, r.stderr


def test_synth_hook_mode_judges_done_rows(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="code-contract")
    assert _attr(synth, ctx, "hook").returncode == 1


def test_synth_lock_without_round_id_rc1(tmp_path):
    synth, ctx = _synth_fixture(tmp_path, post=True, committee="doc-sync", chair="doc-sync")
    (synth.parent / "sources.lock").write_text("{}", encoding="utf-8")
    r = _attr(synth, ctx)
    assert r.returncode == 1 and "sources.lock 缺 round_id" in r.stderr, r.stderr


# ================================================================ Task 3.2：debt_clear 收案量測事件

def _clear_harness(tmp_path: Path, *, post: bool, bodies: dict[str, str], chair: dict[str, str]):
    root, audit = _tdc._setup(tmp_path)
    _copy(root / "scripts", METRIC_HELPERS)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-qm", "base")
    session = "20260916-docrot2-b3-review-r1"
    fams = sorted(bodies)
    rid = str(uuid.uuid4())
    _tdc._open_round(root, audit, round_id=rid, session=session, participants=fams)
    _place(root / "scripts", audit, rid, post=post)
    for fam in fams:
        p, sha = _tdc._write_output(root, session, fam, bodies[fam])
        _tdc._result(root, audit, round_id=rid, family=fam, out_path=str(p.relative_to(root)), out_sha=sha)
    lock = _tdc._build_session(root, session=session, round_id=rid, families=fams, bodies=bodies)
    synth = lock.parent / "synth.md"
    text = synth.read_text(encoding="utf-8")
    text = text.replace("| 群集 | 嚴重度 | 來源 ID | 處置 |\n|---|---|---|---|",
                        "| 群集 | 嚴重度 | 來源 ID | 處置 | 主委類別 |\n|---|---|---|---|---|")
    for fid, cat in chair.items():
        text = re.sub(rf"(\| {re.escape(fid)} \| 採納 \|)", rf"\1 {cat} |", text)
    synth.write_text(text, encoding="utf-8")
    return root, audit, rid, session, lock


def _body(fid: str, cat: str | None) -> str:
    b = _tdc._finding(fid)
    return b + (f"\n**類別**: {cat}\n" if cat else "")


def _clear(root: Path, audit: Path, rid: str, session: str, lock: Path) -> subprocess.CompletedProcess:
    return _tdc._clear(root, audit, "--round-id", rid, "--session", session, "--lock", str(lock))


def test_valid_round_emits_metric_before_clear_rc0(tmp_path):
    bodies = {"codex": _body("CODEX-R1-P0-01", "doc-sync"), "composer": _body("COMPOSER-R1-P0-01", "code-contract")}
    chair = {"CODEX-R1-P0-01": "doc-sync", "COMPOSER-R1-P0-01": "doc-sync"}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=True, bodies=bodies, chair=chair)
    synth = lock.parent / "synth.md"
    synth.write_text(synth.read_text(encoding="utf-8").replace(
        "\n\n## 附錄", "\n\n### 類別不一致\n\n- COMPOSER-R1-P0-01：委員 code-contract／主委 doc-sync ⇒ 駁回（委員欄為準）\n\n## 附錄", 1),
        encoding="utf-8")
    r = _clear(root, audit, rid, session, lock)
    assert r.returncode == 0, r.stderr + r.stdout
    metrics = _events(audit, "docrot2_round_metric")
    clears = _events(audit, "committee_debt_clear")
    assert len(metrics) == 1 and len(clears) == 1
    m = metrics[0]
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    assert m["round_id"] == rid and m["task_id"] == "t-clear" and m["session_name"] == session
    assert m["round_open_sequence"] == _open_seq(audit, rid) and m["brief_kind"] == "review"
    assert m["canonical_count"] == 2 and m["mismatch_count"] == 1
    assert m["category_counts"] == {c: {"doc-sync": 1, "code-contract": 1}.get(c, 0) for c in CATS}
    assert m["handoff_tree_commit"] == head and m["stamps"] == []
    assert m["committee_models"] == {f: {"model": "unavailable", "reasoning_effort": "unavailable"} for f in ("codex", "composer")}
    assert m["origin_script"] == "debt_clear.sh" and m["sequence"] < clears[0]["sequence"]


def test_synth_without_category_counts_rc_nonzero(tmp_path):
    bodies = {"codex": _body("CODEX-R1-P0-01", None), "composer": _body("COMPOSER-R1-P0-01", None)}
    chair = {"CODEX-R1-P0-01": "doc-sync", "COMPOSER-R1-P0-01": "doc-sync"}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=True, bodies=bodies, chair=chair)
    r = _clear(root, audit, rid, session, lock)
    assert r.returncode != 0
    assert "附錄區塊之委員類別" in r.stderr, r.stderr          # 先擋者＝群集歸戶閘（⑦）
    assert not _events(audit, "docrot2_round_metric") and not _events(audit, "committee_debt_clear")


def _emit(root: Path, audit: Path, rid: str, session: str, lock: Path) -> subprocess.CompletedProcess:
    env = _tdc._hermetic_env(audit)
    return subprocess.run(["python3", str(root / "scripts" / "_docrot2_metrics.py"), "emit-round", "--round-id", rid,
                           "--session", session, "--lock", str(lock)], cwd=root, env=env, capture_output=True, text=True)


def test_emit_round_category_missing_reason_rc1(tmp_path):
    """mutation ⑤（收案缺值改放行）之靶：量測寫入端自身之缺值判定（原因碼區分於群集歸戶閘）。"""
    bodies = {"codex": _body("CODEX-R1-P0-01", None), "composer": _body("COMPOSER-R1-P0-01", "doc-sync")}
    chair = {"CODEX-R1-P0-01": "doc-sync", "COMPOSER-R1-P0-01": "doc-sync"}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=True, bodies=bodies, chair=chair)
    r = _emit(root, audit, rid, session, lock)
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=category-missing" in r.stderr, r.stderr
    assert not _events(audit, "docrot2_round_metric")


def test_emit_round_chair_column_missing_reason_rc1(tmp_path):
    bodies = {"codex": _body("CODEX-R1-P0-01", "doc-sync"), "composer": _body("COMPOSER-R1-P0-01", "doc-sync")}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=True, bodies=bodies, chair={"CODEX-R1-P0-01": "doc-sync"})
    r = _emit(root, audit, rid, session, lock)
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=category-missing" in r.stderr and "COMPOSER-R1-P0-01 主委類別" in r.stderr, r.stderr


def test_pre_threshold_round_clears_without_metric_rc0(tmp_path):
    bodies = {"codex": _body("CODEX-R1-P0-01", None), "composer": _body("COMPOSER-R1-P0-01", None)}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=False, bodies=bodies, chair={})
    r = _clear(root, audit, rid, session, lock)
    assert r.returncode == 0, r.stderr
    assert not _events(audit, "docrot2_round_metric") and len(_events(audit, "committee_debt_clear")) == 1


def test_emit_round_idempotent_single_event(tmp_path):
    bodies = {"codex": _body("CODEX-R1-P0-01", "doc-sync"), "composer": _body("COMPOSER-R1-P0-01", "doc-sync")}
    chair = {"CODEX-R1-P0-01": "doc-sync", "COMPOSER-R1-P0-01": "doc-sync"}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=True, bodies=bodies, chair=chair)
    assert _emit(root, audit, rid, session, lock).returncode == 0
    assert _emit(root, audit, rid, session, lock).returncode == 0
    assert len(_events(audit, "docrot2_round_metric")) == 1


def test_emit_round_append_failure_blocks_clear(tmp_path):
    """邊界①：audit 寫入失敗 ⇒ 收案 rc!=0（登記檔移除事件定義使 audit_append 拒寫）。"""
    bodies = {"codex": _body("CODEX-R1-P0-01", "doc-sync"), "composer": _body("COMPOSER-R1-P0-01", "doc-sync")}
    chair = {"CODEX-R1-P0-01": "doc-sync", "COMPOSER-R1-P0-01": "doc-sync"}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=True, bodies=bodies, chair=chair)
    reg_p = root / "scripts" / "audit_events.json"
    reg = json.loads(reg_p.read_text(encoding="utf-8"))
    reg["required_fields_per_event"]["docrot2_round_metric"].append("field_never_written")
    reg_p.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    r = _clear(root, audit, rid, session, lock)
    assert r.returncode != 0 and "DOCROT2_METRIC_REASON=append-failed" in r.stderr, r.stderr
    assert not _events(audit, "committee_debt_clear")


def test_debt_clear_metric_helper_missing_fail_closed(tmp_path):
    bodies = {"codex": _body("CODEX-R1-P0-01", None), "composer": _body("COMPOSER-R1-P0-01", None)}
    root, audit, rid, session, lock = _clear_harness(tmp_path, post=False, bodies=bodies, chair={})
    (root / "scripts" / "_docrot2_metrics.py").unlink()
    r = _clear(root, audit, rid, session, lock)
    assert r.returncode != 0 and "DOCROT2_METRIC_REASON=helper-missing" in r.stderr, r.stderr


def test_committee_round_open_requires_brief_kind(tmp_path):
    root, audit = _tdc._setup(tmp_path)
    r = _tdc.helper.run_cmd(root / "scripts" / "audit_append.sh", "--event", "committee_round_open",
                            "--field", "round_id=r1", "--field", "task_id=t", "--field", "brief_path=b",
                            "--field", "brief_sha256=a", "--field", "brief_sha256_norm=b", "--field", "lock_mode=review",
                            "--field", "participants=@[\"codex\"]", "--field", "expected_outputs=@{}",
                            "--field", "session_name=s", "--field", "actor=t", "--field", "origin_script=committee_run.sh",
                            env=_tdc._hermetic_env(audit), cwd=root)
    assert r.returncode != 0 and "brief_kind" in r.stderr, r.stderr


# ================================================================ Task 3.2：擋下事件

def _guard_repo(tmp_path: Path, files: dict, exact, *, with_audit: bool = True) -> Path:
    root = _wg._repo(tmp_path, files, exact=exact)
    if with_audit:
        _copy(root / "scripts", ("audit_append.sh", "audit_events.json"))
    return root


def _guard_audit(root: Path) -> Path:
    return root / ".claude" / "gate" / "audit.log"


def _guard_env(root: Path) -> dict:
    """tests/governance/conftest.py 對每條測試設 DEBT_AUDIT_OVERRIDE；此處改指沙箱自己的 audit 以便逐筆對讀。"""
    return {**os.environ, "GOVERNANCE_TEST_HARNESS": "1", "DEBT_AUDIT_OVERRIDE": str(_guard_audit(root))}


def _guard(root: Path, *args: str, payload: dict | None = None, script: str = "live_doc_write_guard.sh") -> subprocess.CompletedProcess:
    data = json.dumps(payload, ensure_ascii=False) if payload is not None else None
    return subprocess.run(["bash", str(root / "scripts" / script), *args], cwd=str(root), input=data,
                          capture_output=True, text=True, env=_guard_env(root))


def test_hook_block_writes_one_gate_block_event(tmp_path):
    root = _guard_repo(tmp_path, {"HANDOFF.md": _wg.HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, [_wg.HANDOFF, _wg.SPEC])
    r = _guard(root, payload=_wg._edit(root, "HANDOFF.md", "- 一般教訓 ANCHOR-PIT", "- 一般教訓 ANCHOR-PIT\n- B-63 部分完成 待補"))
    assert r.returncode == 2, r.stderr
    evs = _events(_guard_audit(root), "docrot2_gate_block")
    assert len(evs) == 1, (evs, r.stderr)
    assert (evs[0]["rule_id"], evs[0]["path"], evs[0]["class"], evs[0]["origin_script"]) == \
        ("status-literal", "HANDOFF.md", "LIVE-HANDOFF", "live_doc_write_guard.sh")


def test_hook_block_two_rules_two_events(tmp_path):
    root = _guard_repo(tmp_path, {"docs/A_SPEC.md": "# A\n\n正文\n"}, [_wg.SPEC])
    r = _guard(root, payload=_wg._edit(root, "docs/A_SPEC.md", "正文", "正文\n~~舊~~\nD2B 進行中"))
    assert r.returncode == 2, r.stderr
    evs = _events(_guard_audit(root), "docrot2_gate_block")
    assert sorted(e["rule_id"] for e in evs) == ["archaeology", "status-literal"], (evs, r.stderr)


def test_hook_block_event_write_failure_still_blocks(tmp_path):
    """邊界②：擋下事件寫入失敗 ⇒ 仍 exit 2。"""
    root = _guard_repo(tmp_path, {"HANDOFF.md": _wg.HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, [_wg.HANDOFF, _wg.SPEC], with_audit=False)
    r = _guard(root, payload=_wg._edit(root, "HANDOFF.md", "- 一般教訓 ANCHOR-PIT", "- 一般教訓 ANCHOR-PIT\n- B-63 部分完成 待補"))
    assert r.returncode == 2 and "擋下事件未寫入" in r.stderr, r.stderr


def test_hook_block_event_append_rejected_still_blocks(tmp_path):
    """邊界②：audit_append 拒寫（登記檔移除事件定義）⇒ 仍 exit 2，且 stderr 具名寫入失敗。"""
    root = _guard_repo(tmp_path, {"HANDOFF.md": _wg.HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, [_wg.HANDOFF, _wg.SPEC])
    reg_p = root / "scripts" / "audit_events.json"
    reg = json.loads(reg_p.read_text(encoding="utf-8"))
    del reg["debt_events"]["docrot2_gate_block"]
    reg_p.write_text(json.dumps(reg, ensure_ascii=False), encoding="utf-8")
    r = _guard(root, payload=_wg._edit(root, "HANDOFF.md", "- 一般教訓 ANCHOR-PIT", "- 一般教訓 ANCHOR-PIT\n- B-63 部分完成 待補"))
    assert r.returncode == 2 and "擋下事件寫入失敗" in r.stderr, r.stderr


def test_hook_allow_writes_no_event(tmp_path):
    root = _guard_repo(tmp_path, {"HANDOFF.md": _wg.HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, [_wg.HANDOFF, _wg.SPEC])
    r = _guard(root, payload=_wg._edit(root, "HANDOFF.md", "- 一般教訓 ANCHOR-PIT", "- 一般教訓 ANCHOR-PIT 補充"))
    assert r.returncode == 0 and not _events(_guard_audit(root), "docrot2_gate_block"), r.stderr


def test_staged_violation_writes_event_tree_replay_does_not(tmp_path):
    root = _guard_repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, [_wg.SPEC])
    (root / "docs" / "A_SPEC.md").write_text("# A\nD2B 進行中\n", encoding="utf-8")
    _git(root, "add", "docs/A_SPEC.md")
    r = _guard(root, "--staged")
    assert r.returncode == 1, r.stderr
    assert [e["rule_id"] for e in _events(_guard_audit(root), "docrot2_gate_block")] == ["status-literal"], r.stderr
    text = _wg.HANDOFF_OK.replace("<!-- ENTRY: B-63 -->", "<!-- ENTRY: D2A -->").replace("：B-63 →", "：D2A →")
    root2 = _guard_repo(tmp_path / "t2", {"HANDOFF.md": text, "docs/A_SPEC.md": "# A\n"}, [_wg.HANDOFF, _wg.SPEC])
    assert _guard(root2, "--tree", "HEAD", "--path", "HANDOFF.md").returncode == 1
    assert not _events(_guard_audit(root2), "docrot2_gate_block")


def test_registry_staged_unregistered_writes_event(tmp_path):
    root = _guard_repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, [_wg.SPEC])
    (root / "docs" / "NEW.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "docs/NEW.md")
    r = _guard(root, "--staged", script="live_doc_registry_check.sh")
    assert r.returncode == 1, r.stderr
    evs = _events(_guard_audit(root), "docrot2_gate_block")
    assert [(e["rule_id"], e["path"], e["class"], e["origin_script"]) for e in evs] == \
        [("unregistered-md", "docs/NEW.md", "UNREGISTERED", "live_doc_registry_check.sh")], r.stderr


def test_gate_block_rule_id_closed_enum(tmp_path):
    root = _guard_repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, [_wg.SPEC])
    r = subprocess.run(["bash", str(root / "scripts" / "audit_append.sh"), "--event", "docrot2_gate_block",
                        "--field", "rule_id=made-up", "--field", "path=x", "--field", "class=LIVE-SPEC",
                        "--field", "actor=t", "--field", "origin_script=live_doc_write_guard.sh"],
                       cwd=str(root), capture_output=True, text=True, env=_guard_env(root))
    assert r.returncode != 0 and "rule_id" in r.stderr, r.stderr


# ================================================================ Task 3.2：docrot2_metrics.sh 報表

TICKET = "20260917-NEXTEPIC"


def _metrics_repo(tmp_path: Path, *, closure: int | None = 10) -> tuple[Path, Path, str]:
    root = _guard_repo(tmp_path, {"HANDOFF.md": _wg.HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, [_wg.HANDOFF, _wg.SPEC])
    _copy(root / "scripts", METRIC_HELPERS + ("docrot2_metrics.sh",))
    c = json.loads((root / "scripts" / "docrot2_metric_contract.json").read_text(encoding="utf-8"))
    c["closure_sequence"] = closure
    (root / "scripts" / "docrot2_metric_contract.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    audit = root / ".claude" / "gate" / "audit.log"
    audit.parent.mkdir(parents=True, exist_ok=True)
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    return root, audit, head


def _ev_open(seq: int, rid: str, task: str, session: str, kind: str | None = "review") -> dict:
    d = {"event": "committee_round_open", "sequence": seq, "round_id": rid, "task_id": task, "session_name": session,
         "participants": ["codex"]}
    if kind is not None:
        d["brief_kind"] = kind
    return d


def _ev_metric(seq: int, rid: str, task: str, session: str, commit: str, *, n: int = 0, doc: int = 0,
               stamps: list | None = None, kind: str = "review") -> dict:
    counts = {c: 0 for c in CATS}
    counts["doc-sync"] = doc
    counts["other"] = n - doc
    return {"event": "docrot2_round_metric", "sequence": seq, "round_id": rid, "task_id": task, "session_name": session,
            "round_open_sequence": seq - 1, "brief_kind": kind, "canonical_count": n, "category_counts": counts,
            "mismatch_count": 0, "handoff_tree_commit": commit,
            "committee_models": {"codex": {"model": "unavailable", "reasoning_effort": "unavailable"}},
            "stamps": stamps or []}


def _write_audit(audit: Path, events: list[dict]) -> None:
    audit.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")


def _report(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(root / "scripts" / "docrot2_metrics.sh")], cwd=str(root),
                          capture_output=True, text=True, env={k: v for k, v in os.environ.items()
                                                              if k not in ("DEBT_AUDIT_OVERRIDE", "GOVERNANCE_TEST_HARNESS")})


def _two_rounds(head: str, *, n1=4, d1=2, n2=4, d2=1, stamps2=None) -> list[dict]:
    return [_ev_open(11, "r1", f"{TICKET}-B1-REVIEW-R1", "s1"), _ev_metric(12, "r1", f"{TICKET}-B1-REVIEW-R1", "s1", head, n=n1, doc=d1),
            _ev_open(13, "r2", f"{TICKET}-B1-REVIEW-R2", "s2"),
            _ev_metric(14, "r2", f"{TICKET}-B1-REVIEW-R2", "s2", head, n=n2, doc=d2, stamps=stamps2)]


def test_metrics_valid_cohort_rc0(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head))
    r = _report(root)
    assert r.returncode == 0 and "四條及格全過" in r.stdout, r.stdout + r.stderr


def test_both_rounds_zero_doc_sync_rc0(tmp_path):
    """邊界①：兩輪文件同步類皆 0 ⇒ comparator 過（含零分母輪）。"""
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head, n1=3, d1=0, n2=0, d2=0))
    r = _report(root)
    assert r.returncode == 0, r.stdout + r.stderr


def test_cohort_missing_second_round_event_rc1(tmp_path):
    """邊界②：只剩一輪事件 ⇒ rc=1。"""
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head)[:3])
    r = _report(root)
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=event-missing" in r.stderr, r.stderr


def test_cohort_only_one_review_round_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head)[:2])
    r = _report(root)
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=cohort-incomplete" in r.stderr, r.stderr


def test_duplicate_round_metric_event_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    evs = _two_rounds(head)
    dup = dict(evs[1], sequence=15)
    _write_audit(audit, evs + [dup])
    r = _report(root)
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=duplicate-event" in r.stderr, r.stderr


def test_cohort_round_open_missing_brief_kind_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    evs = _two_rounds(head) + [_ev_open(16, "r3", "20260918-OTHER-B1-REVIEW-R1", "s3", kind=None)]
    _write_audit(audit, evs)
    r = _report(root)
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=brief-kind-missing" in r.stderr, r.stderr


def test_closure_sequence_null_cohort_unknown_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path, closure=None)
    _write_audit(audit, _two_rounds(head))
    r = _report(root)
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=cohort-unknown" in r.stderr, r.stderr


def test_ticket_with_review_before_closure_is_not_cohort(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    old = [_ev_open(5, "o1", "20260910-OLD-B1-REVIEW-R1", "o1"), _ev_open(9, "o0", "20260910-OLD-B1-REVIEW-R2", "o0")]
    later_old = [_ev_open(20, "o2", "20260910-OLD-B1-REVIEW-R3", "o2")]
    _write_audit(audit, old + _two_rounds(head) + later_old)
    r = _report(root)
    assert r.returncode == 0 and TICKET in r.stdout, r.stdout + r.stderr


def test_ratio_increase_fails_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head, n1=4, d1=1, n2=4, d2=2))
    r = _report(root)
    assert r.returncode == 1 and "② doc-sync 占比第二輪" in r.stderr, r.stderr


def test_round_over_20_findings_fails_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head, n1=21, d1=0, n2=0, d2=0))
    r = _report(root)
    assert r.returncode == 1 and "① s1 canonical=21" in r.stderr, r.stderr


def test_handoff_replay_failure_fails_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    (root / "HANDOFF.md").write_text(_wg.HANDOFF_OK.replace("## 坑", "## 雜項"), encoding="utf-8")
    _git(root, "commit", "-qam", "bad handoff")
    bad = _git(root, "rev-parse", "HEAD").stdout.strip()
    evs = _two_rounds(head)
    evs[3]["handoff_tree_commit"] = bad
    _write_audit(audit, evs)
    r = _report(root)
    assert r.returncode == 1 and "③ s2 交接重放" in r.stderr, r.stderr


def test_history_only_restamp_in_cohort_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    stamps = [{"stamp_target": "docs/A_SPEC.md", "body_sha_before": "a" * 64, "body_sha_after": "b" * 64, "history_only": 1}]
    evs = _two_rounds(head) + [_ev_open(15, "r3", f"{TICKET}-X-STAMP-R1", "s3", kind="closure"),
                               _ev_metric(16, "r3", f"{TICKET}-X-STAMP-R1", "s3", head, stamps=stamps, kind="closure")]
    _write_audit(audit, evs)
    r = _report(root)
    assert r.returncode == 1 and "④ 只動歷史區之重蓋章 1" in r.stderr, r.stderr


# ── review-r1 CODEX-R1-P1-02：報表對 audit／事件／契約之封閉驗證

def _report_reason(root: Path) -> tuple[int, str]:
    r = _report(root)
    m = re.search(r"DOCROT2_METRIC_REASON=(\S+)", r.stderr)
    return r.returncode, (m.group(1) if m else "")


def test_report_duplicate_open_same_round_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    evs = _two_rounds(head)
    evs[2] = _ev_open(13, "r1", f"{TICKET}-B1-REVIEW-R2", "s2")          # 第二筆開債沿用 r1
    evs[3] = _ev_metric(14, "r1", f"{TICKET}-B1-REVIEW-R2", "s2", head)
    _write_audit(audit, evs)
    assert _report_reason(root) == (1, "duplicate-open")


@pytest.mark.parametrize("patch", [
    {"stamp_target": 7},
    {"body_sha_after": "not-a-sha"},
    {"body_sha_before": "abc"},
    {"history_only": True},
    {"history_only": 2},
])
def test_report_invalid_stamp_rc1(tmp_path, patch):
    root, audit, head = _metrics_repo(tmp_path)
    stamp = {"stamp_target": "docs/A_SPEC.md", "body_sha_before": "none", "body_sha_after": "b" * 64, "history_only": 0}
    stamp.update(patch)
    _write_audit(audit, _two_rounds(head, stamps2=[stamp]))
    assert _report_reason(root) == (1, "event-invalid")


@pytest.mark.parametrize("field,value", [
    ("task_id", None), ("session_name", "other-session"), ("round_open_sequence", 99),
    ("brief_kind", "closure"), ("committee_models", {}),
])
def test_report_metric_identity_mismatch_rc1(tmp_path, field, value):
    root, audit, head = _metrics_repo(tmp_path)
    evs = _two_rounds(head)
    if value is None:
        del evs[1][field]
    else:
        evs[1][field] = value
    _write_audit(audit, evs)
    assert _report_reason(root) == (1, "event-invalid")


def test_report_metric_orphan_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head) + [_ev_metric(30, "ghost", f"{TICKET}-B9-REVIEW-R1", "sg", head)])
    assert _report_reason(root) == (1, "metric-orphan")


def test_report_malformed_audit_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    _write_audit(audit, _two_rounds(head))
    audit.write_text("{not json\n" + audit.read_text(encoding="utf-8"), encoding="utf-8")
    assert _report_reason(root) == (1, "audit-malformed")


def test_report_string_sequence_missing_brief_rc1(tmp_path):
    root, audit, head = _metrics_repo(tmp_path)
    bad = _ev_open(16, "r3", "20260918-OTHER-B1-REVIEW-R1", "s3", kind=None)
    bad["sequence"] = "16"
    _write_audit(audit, _two_rounds(head) + [bad])
    assert _report_reason(root) == (1, "audit-malformed")


@pytest.mark.parametrize("patch", [
    {"expect_rc": 1},
    {"command": ["bash", "-c", "true", "{commit}"]},
])
def test_contract_replay_semantics_closed_rc1(tmp_path, patch):
    root, audit, head = _metrics_repo(tmp_path)
    p = root / "scripts" / "docrot2_metric_contract.json"
    c = json.loads(p.read_text(encoding="utf-8"))
    c["handoff_replay"].update(patch)
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    _write_audit(audit, _two_rounds(head))
    assert _report_reason(root) == (1, "contract-invalid")


# ── 只動歷史區之重蓋章：以寫入端實算（mutation ⑪：改用整檔差異 ⇒ 應轉紅）

STAMP_DOC = "# 標的\n\n正文不變\n\n<!-- HISTORY-BEGIN -->\n- 2026-09-16：v1 → `docs/A_SPEC.md`\n<!-- HISTORY-END -->\n\n## 戳記\n"


def _stamp_round(root: Path, audit: Path, seq: int, rid: str, task: str, session: str) -> None:
    sess = root / "handoffs" / "reconcile" / session
    sess.mkdir(parents=True, exist_ok=True)
    (sess / "synth.md").write_text("# Reconcile\n\n## 群集 / 處置\n\n**Verdict**: 可合併\n\n## 附錄\n", encoding="utf-8")
    (sess / "sources.lock").write_text(json.dumps({"round_id": rid}), encoding="utf-8")
    brief = root / "handoffs" / f"{session}-BRIEF.md"
    brief.write_text("brief-kind: review\n\nstamp-target: handoffs/stamp-target.md\n", encoding="utf-8")
    op = _ev_open(seq, rid, task, session)
    op["brief_path"] = str(brief.relative_to(root))
    with audit.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(op, ensure_ascii=False) + "\n")


def _emit_in(root: Path, rid: str, session: str) -> subprocess.CompletedProcess:
    lock = root / "handoffs" / "reconcile" / session / "sources.lock"
    return subprocess.run(["python3", str(root / "scripts" / "_docrot2_metrics.py"), "emit-round", "--round-id", rid,
                           "--session", session, "--lock", str(lock)], cwd=str(root), capture_output=True, text=True,
                          env={k: v for k, v in os.environ.items() if k not in ("DEBT_AUDIT_OVERRIDE", "GOVERNANCE_TEST_HARNESS")})


def test_history_only_restamp_hidden_by_stamp_lines_rc1(tmp_path):
    root, audit, _head = _metrics_repo(tmp_path)
    _copy(root / "scripts", ("governance_families.json",))
    _set_threshold(root / "scripts", 0)
    audit.write_text("", encoding="utf-8")
    target = root / "handoffs" / "stamp-target.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    t1, t2 = f"{TICKET}-B1-REVIEW-R1", f"{TICKET}-B1-REVIEW-R2"
    target.write_text(STAMP_DOC + f"RECONCILE-STAMP: codex APPROVED 2026-09-17 sha256:{'0' * 64} task:{t1}\n", encoding="utf-8")
    _stamp_round(root, audit, 11, "r1", t1, "20260917-nextepic-b1-review-r1")
    r1 = _emit_in(root, "r1", "20260917-nextepic-b1-review-r1")
    assert r1.returncode == 0, r1.stderr
    # 第二次戳記：本體只改歷史專區；戳記區另追加一行（整檔差異含歷史區外之戳記行）
    changed = STAMP_DOC.replace("<!-- HISTORY-END -->", "- 2026-09-17：v2 → `docs/A_SPEC.md`\n<!-- HISTORY-END -->")
    target.write_text(changed + f"RECONCILE-STAMP: codex APPROVED 2026-09-17 sha256:{'0' * 64} task:{t1}\n"
                      + f"RECONCILE-STAMP: codex APPROVED 2026-09-17 sha256:{'1' * 64} task:{t2}\n", encoding="utf-8")
    _stamp_round(root, audit, 13, "r2", t2, "20260917-nextepic-b1-review-r2")
    r2 = _emit_in(root, "r2", "20260917-nextepic-b1-review-r2")
    assert r2.returncode == 0, r2.stderr
    metrics = _events(audit, "docrot2_round_metric")
    assert [m["stamps"][0]["history_only"] for m in metrics] == [0, 1], metrics
    assert metrics[1]["stamps"][0]["body_sha_before"] == metrics[0]["stamps"][0]["body_sha_after"]
    r = _report(root)
    assert r.returncode == 1 and "④ 只動歷史區之重蓋章 1" in r.stderr, r.stdout + r.stderr


def test_restamp_body_change_outside_history_not_counted(tmp_path):
    root, audit, _head = _metrics_repo(tmp_path)
    _copy(root / "scripts", ("governance_families.json",))
    _set_threshold(root / "scripts", 0)
    audit.write_text("", encoding="utf-8")
    target = root / "handoffs" / "stamp-target.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    t1, t2 = f"{TICKET}-B1-REVIEW-R1", f"{TICKET}-B1-REVIEW-R2"
    target.write_text(STAMP_DOC + f"RECONCILE-STAMP: codex APPROVED 2026-09-17 sha256:x task:{t1}\n", encoding="utf-8")
    _stamp_round(root, audit, 11, "r1", t1, "s-r1")
    assert _emit_in(root, "r1", "s-r1").returncode == 0
    target.write_text(STAMP_DOC.replace("正文不變", "正文已改") + f"RECONCILE-STAMP: codex APPROVED 2026-09-17 sha256:y task:{t2}\n",
                      encoding="utf-8")
    _stamp_round(root, audit, 13, "r2", t2, "s-r2")
    assert _emit_in(root, "r2", "s-r2").returncode == 0
    assert [m["stamps"][0]["history_only"] for m in _events(audit, "docrot2_round_metric")] == [0, 0]


def test_restamp_snapshot_missing_fail_closed(tmp_path):
    root, audit, _head = _metrics_repo(tmp_path)
    _copy(root / "scripts", ("governance_families.json",))
    _set_threshold(root / "scripts", 0)
    audit.write_text("", encoding="utf-8")
    target = root / "handoffs" / "stamp-target.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    t1, t2 = f"{TICKET}-B1-REVIEW-R1", f"{TICKET}-B1-REVIEW-R2"
    target.write_text(STAMP_DOC + f"RECONCILE-STAMP: codex APPROVED 2026-09-17 sha256:x task:{t1}\n", encoding="utf-8")
    _stamp_round(root, audit, 11, "r1", t1, "s-r1")
    assert _emit_in(root, "r1", "s-r1").returncode == 0
    shutil.rmtree(root / "handoffs" / "docrot2_body_snapshots")
    target.write_text(STAMP_DOC + f"RECONCILE-STAMP: codex APPROVED 2026-09-17 sha256:y task:{t2}\n", encoding="utf-8")
    _stamp_round(root, audit, 13, "r2", t2, "s-r2")
    r = _emit_in(root, "r2", "s-r2")
    assert r.returncode == 1 and "DOCROT2_METRIC_REASON=snapshot-missing" in r.stderr, r.stderr


def test_contract_json_is_registered_and_valid():
    import importlib.util
    spec = importlib.util.spec_from_file_location("m", REPO / "scripts" / "_docrot2_metrics.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    c = m.load_contract(str(REPO / "scripts" / "docrot2_metric_contract.json"))
    assert c["numerator"]["committee_category"] in CATS and c["max_findings_per_round"] == 20
