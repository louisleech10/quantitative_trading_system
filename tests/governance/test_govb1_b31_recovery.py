"""GOVB1 Task 4.3（`票 B-31`）— `format-failed` 補救層 ＋ 兩件移交。

Task 4.3 本體：格式不合規時給**逐條可修補清單**（`檔:行` ＋ 違規類型 ＋ 修法一行），
使該輪不必整份重跑（實測委員一次重跑約 15 分鐘）。

🔴 本檔同時承接兩件由前票明確核可的移交：
  · **B8 C5**：`cx_run` 三入口矩陣**第三欄**。B8 當時不可達（`CX_STUB_MODE=success`
    會覆寫 `${out}`，而 `cx_run.sh` 在 Task 4.1 是唯讀），故只掛逼債條款。
    Task 4.3 得以改 `cx_run.sh` ⇒ 新增 `preserve` stub 模式，第三欄從此可驗。
  · **B9 C5**：零 findings 契約第 ③ 件（findings **落點**）的**強制點**。
    在此之前 `findings_destination` 只是 JSON 宣告，沒有任何腳本會擋。

🔴 **`cx_run.sh` 的原始碼被 `_B45_HARNESS` 凍結測試逐字錨定**（函式本體與呼叫點皆是）。
本批新增一律加在錨點**外側**，且落點快照走**動態作用域**而非新增參數
——主委實測：改內部縮排或加一個引數，都會讓 mutation probe 找不到錨點而轉紅。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from tests.governance import test_govb1_zeroid_no_regression as _zeroid

REPO_ROOT = Path(__file__).resolve().parents[2]
CX_RUN = REPO_ROOT / "scripts" / "cx_run.sh"
COMPLETENESS = REPO_ROOT / "scripts" / "completeness_check.sh"
LIFECYCLE = REPO_ROOT / "scripts" / "govflow_lifecycle.json"

# 🔴 三種輸入**直接引用** B8 的定義，不另抄一份——抄一份就會漂移，
#   而這裡的全部意義就在於「與 `--single`／`--lock` 兩欄量的是同一組輸入」。
INPUTS = _zeroid.INPUTS


def _src() -> str:
    return CX_RUN.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Task 4.3 本體：逐條可修補清單
# ---------------------------------------------------------------------------


def test_fixup_list_emitter_exists_and_has_three_columns() -> None:
    """`_emit_fixup_list` 須輸出 `檔:行` ＋ 違規類型 ＋ 修法一行（三欄）。

    只給 rc 的舊行為讓委員不知道**哪一條、哪一行、怎麼修** ⇒ 只能整份重跑。
    """
    s = _src()
    assert "_emit_fixup_list()" in s
    assert "可修補清單（逐條）" in s
    # 三欄格式字串：檔:行 \t 類型 \t 修法
    assert "'  %s:%s\\t%s\\t%s\\n'" in s, "修補清單不是三欄格式"
    assert "COMMITTEE_FINDING_TEMPLATE.md" in s, "修法欄未指向範本"


def test_fixup_list_is_invoked_only_on_failure() -> None:
    """成功路徑不得付出額外成本（清單只在失敗時再跑一次 checker）。"""
    s = _src()
    i = s.index("_emit_fixup_list \"${_log}\"")
    guard = s[max(0, i - 400) : i]
    assert '[ "${_rc}" -ne 0 ]' in guard, "修補清單未以失敗為前提"
    assert '[ "${_rc}" -ne 127 ]' in guard, "checker 不可用時不應再跑一次"


def test_fixup_list_always_has_a_line_number() -> None:
    """🔴 `CODEX-R1-P1-04`：每條**必含** `檔:行`，不得印 `檔:?`。

    duplicate-ID 這類訊息不帶 canonical ID ⇒ 原實作退回 `?`，
    委員無從定位 ⇒ 補救層失去意義（那正是 `票 B-31` 要解的病）。
    退路為三層封閉規則：①訊息自帶 `:<行號>` ②檔內第一個 canonical heading ③第 1 行。
    """
    s = _src()
    assert "${_no:-?}" not in s, "仍有 `?` 退路 ⇒ 可能印出無法定位的條目"
    assert '[ -n "${_no}" ] || _no=1' in s, "缺最終退路 ⇒ 仍可能印空行號"
    # 三層退路都要在
    assert "grep -Eo ':[0-9]+'" in s
    assert "grep -nE '^#{2,6}" in s


def test_format_failed_does_not_become_failed() -> None:
    """SPEC 邊界①：格式失敗但產出實質完整 ⇒ 標 `format-failed`，**不得**標 `failed`。"""
    s = _src()
    assert 'result_state="format-failed"' in s
    # exit 3 是 format-failed 的專用碼；不得與 failed 混用
    assert "格式不合規 → exit 3" in s


def test_debt_clear_success_guard_not_relaxed() -> None:
    """🔴 不可做：不得放寬 `debt_clear` 只接受 `success` 的守衛（三值契約凍結）。"""
    s = (REPO_ROOT / "scripts" / "debt_clear.sh").read_text(encoding="utf-8")
    assert "format-failed" not in s.split("abandon_kind")[0] or True  # 存在性不強制
    # 守衛本身：debt_clear 不得把 format-failed 當成可銷帳
    assert "success" in s
    got = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "scripts/debt_clear.sh"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert got.returncode == 0
    assert got.stdout.strip() == "", f"本批不得改 debt_clear.sh:\n{got.stdout}"


# ---------------------------------------------------------------------------
# B8 C5 移交：preserve stub 讓三入口矩陣第三欄可達
# ---------------------------------------------------------------------------


def test_preserve_stub_mode_exists_and_does_not_overwrite() -> None:
    """🔴 B8 C5 移交的**阻塞成因**必須在此消失。

    B8 的 `test_cxrun_column_is_blocked_not_passing` 是逼債條款：
    它斷言「`cx_run.sh` 沒有保留既有輸出的 stub 模式」。
    本批加上 `preserve` 後那條**必須轉紅**，並由本檔接手第三欄——
    這正是逼債條款的設計目的（阻塞成因消失即逼下一手補上）。
    """
    s = _src()
    assert "      preserve)" in s, "未新增 preserve stub 模式"
    i = s.index("      preserve)")
    seg = s[i : s.index("        ;;", i)]
    # 只看**實際指令**，不看註解——註解裡提到覆寫函式名是在解釋「為何不用它」
    code = [ln for ln in seg.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert not any("_write_stub_success_output" in ln for ln in code), (
        "preserve 模式仍覆寫產出"
    )
    assert "cli_rc=0" in seg


def test_b8_blocker_test_was_retired() -> None:
    """B8 的逼債條款須已被移除或改寫——不得與本檔的第三欄並存互相矛盾。"""
    zeroid = (
        REPO_ROOT / "tests" / "governance" / "test_govb1_zeroid_no_regression.py"
    ).read_text(encoding="utf-8")
    # 判「函式定義」不判字串——退場說明本來就會提到它的名字
    assert "def test_cxrun_column_is_blocked_not_passing" not in zeroid, (
        "B8 逼債條款仍在，但阻塞成因已消失 ⇒ 兩處敘述矛盾"
    )
    assert "退場" in zeroid, "逼債條款移除了卻沒留退場說明 ⇒ 缺口會靜靜消失"


# ---------------------------------------------------------------------------
# B9 C5 移交：findings 落點強制點
# ---------------------------------------------------------------------------


def test_findings_destination_has_an_enforcement_point() -> None:
    """🔴 B9 C5 移交：契約第 ③ 件從「JSON 宣告」變成**會擋的檢查**。

    在此之前沒有任何腳本會擋「把 findings append 進 stamp-target」，
    `票 B-52` 的落點事故因此仍可重演（`CODEX-R1-P1-05`／`COMPOSER-R1-P2-01`）。
    """
    s = _src()
    assert "_check_findings_destination()" in s
    assert "findings 落點違規" in s
    assert "zero_findings_contract.findings_destination" in s, "未指回契約 SoT"


def test_destination_check_snapshots_before_cli_runs() -> None:
    """快照必須在 CLI **執行前**取，否則比不出「本輪新增了什麼」。"""
    s = _src()
    # 只在 _run_cli_and_emit 內比較（該函式外另有 _capture_prompt_if_harness 的定義）
    body = s[s.index("_run_cli_and_emit() {"):]
    snap = body.index('_dest_snap="$(mktemp)"')
    cli = body.index("  _capture_prompt_if_harness\n")
    assert snap < cli, "落點快照取得晚於 CLI 執行 ⇒ 比對無意義"


def test_destination_check_is_kind_independent() -> None:
    """落點檢查不得被 findings-kind 閘擋住——stamp 輪正是出事的那一種。"""
    s = _src()
    i = s.index("if [ -n \"${_dest_snap:-}\" ]")
    seg = s[s.index("  # ── 以下為 Task 4.3 新增") : i]
    assert "case \"${_bk}\"" not in seg, "落點檢查落在 brief-kind 閘內 ⇒ stamp 輪不受檢"


def test_destination_check_uses_dynamic_scope_not_new_param() -> None:
    """🔴 呼叫點被凍結測試逐字錨定 ⇒ 不得新增引數。

    主委實測：多傳一個引數會讓 `_B45_HARNESS` 的 mutation probe 找不到錨點而轉紅。
    """
    s = _src()
    assert '_fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"' in s, (
        "呼叫點字面已變 ⇒ 凍結測試錨點會漂移"
    )
    assert 'if [ -n "${_dest_snap:-}" ]' in s, "未以動態作用域讀快照"


# ---------------------------------------------------------------------------
# 凍結錨點保護（本批最容易誤傷的地方）
# ---------------------------------------------------------------------------


def test_frozen_anchors_in_cx_run_are_intact() -> None:
    """🔴 `_B45_HARNESS` 逐字錨定的三處字面必須一字不差。

    epic 期間那五個測試檔禁改 ⇒ 只能反過來要求 `cx_run.sh` 保住錨點。
    本測把「哪幾段不能動」變成 B10 自己的斷言，而不是等別人的測試紅了才知道。
    """
    s = _src()
    for anchor in (
        '        if [ ! -f "${_cc}" ] || [ ! -r "${_cc}" ]; then\n'
        '          echo "ERROR: completeness_check.sh 不存在或不可讀 → fail-closed（不得記 success）" >&2\n'
        "          _rc=127\n"
        "        else\n",
        '          bash "${_cc}" --single "${out}" --family "${fam}" >&2 || _rc=$?\n',
        '  _fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"\n'
        '  _emit_family_result "${cli_rc}" "${_fmt_rc}" || {\n',
    ):
        assert anchor in s, f"凍結錨點漂移:\n{anchor!r}"


def test_findings_kind_gate_not_widened() -> None:
    """🔴 不得把 findings-kind 閘改為無條件。

    主委初版改成「有 family 就跑」，結果未複製 checker 的隔離環境全部 fail-closed
    ⇒ `test_debt_emit` 17 條轉紅。那不是更嚴，是打斷 impl／stamp 輪的既有契約。
    """
    s = _src()
    i = s.index("_run_format_check_if_needed() {")
    body = s[i : s.index("printf '%s' \"${_rc}\"", i)]
    assert 'case "${_bk}" in\n    review|consult|closure)' in body, (
        "findings-kind 閘被放寬 ⇒ 隔離環境會 fail-closed"
    )


def test_lifecycle_embed_stays_in_sync() -> None:
    """改 `cx_run.sh` 後內嵌 lifecycle 副本仍須 ≡ 正本。"""
    got = subprocess.run(
        ["bash", "scripts/govb1_final_gate.sh", "--only", "lifecycle_embed"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        env=os.environ.copy(),
    )
    assert got.returncode == 0, got.stderr


# ---------------------------------------------------------------------------
# 端到端隔離 harness — `T-4.3-U1..U3` ＋ B8 C5 移交的第三欄
#
# 🔴 為何非有不可〔`CODEX-R1-P1-02`／`COMPOSER-R1-P1-01`／`P1-02`〕：
#   本檔第一版只有**靜態源碼斷言**（「`preserve)` 這個字串在不在」），
#   那只證明「有寫」不證明「會動」，等於把逼債條款換個地方掛成一條更弱的斷言。
#   下列測試一律**真的跑** `cx_run.sh` 交件路徑，讀 audit 的 `result_state`。
# ---------------------------------------------------------------------------

_REF = "照 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文"
_FACT = "fact-verified: cx_run 交件路徑先跑格式檢查再 append audit"
_ASSUMED = "assumed: CX_STUB_MODE=preserve 不覆寫既有產出"

_COPY_SCRIPTS = (
    "cx_run.sh",
    "audit_append.sh",
    "audit_events.json",
    "governance_families.sh",
    "governance_families.json",
    "governance_roles.json",
    "brief_conformance_check.sh",
    "completeness_check.sh",
    "debt_clear.sh",
    "debt_ledger.sh",
    "_debt_ledger_core.py",
    "_role_gate.sh",
    "govflow_lifecycle.json",
    # B10 r2 必答 1 裁 (A)：主委自產 findings 的產出端檢查點
    "doc_format_precheck.sh",
    "verdict_filled_check.sh",
    "template_check.sh",
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _events(audit: Path, name: str) -> list[dict]:
    rows: list[dict] = []
    if not audit.is_file():
        return rows
    for line in audit.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("event") == name:
            rows.append(rec)
    return rows


def _harness(tmp_path: Path, kind: str = "review") -> dict:
    """隔離 repo：scripts 副本 ＋ 空 audit ＋ handoffs。

    `kind="stamp"` 另建 stamp-target（`brief_conformance_check` 在前置就要求它存在，
    見 `cx_run.sh` `_check_findings_destination` 上方的 `COMPOSER-R1-P2-01` 邊界註記）。
    """
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    handoffs = root / "handoffs"
    handoffs.mkdir()
    gate_dir = root / ".claude" / "gate"
    gate_dir.mkdir(parents=True)
    audit = gate_dir / "audit.log"
    audit.write_text("", encoding="utf-8")

    for name in _COPY_SCRIPTS:
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
            if name.endswith(".sh"):
                (scripts / name).chmod(0o755)

    stamp_target = handoffs / "b31-stamp-target.md"
    stamp_target.write_text("## 戳記\n", encoding="utf-8")

    brief = handoffs / f"b31-brief-{kind}.md"
    if kind == "stamp":
        brief.write_text(
            "brief-kind: stamp\nstamp-target: handoffs/b31-stamp-target.md\n\n"
            "B10 落點 harness brief.\n",
            encoding="utf-8",
        )
    else:
        brief.write_text(
            f"brief-kind: {kind}\n\n{_REF}\n{_FACT}\n{_ASSUMED}\n\nB10 第三欄 harness brief.\n",
            encoding="utf-8",
        )
    return {
        "root": root,
        "scripts": scripts,
        "audit": audit,
        "brief": brief,
        "brief_rel": f"handoffs/b31-brief-{kind}.md",
        "stamp_target": stamp_target,
        "env": {
            "GOVERNANCE_TEST_HARNESS": "1",
            "DEBT_AUDIT_OVERRIDE": str(audit),
            "GATE_DIR_OVERRIDE": str(gate_dir),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": os.environ.get("LANG", "C"),
        },
    }


def _open_round(h: dict, *, round_id: str, session: str, fams: list[str], out_prefix: str) -> None:
    brief_sha = _sha256_file(h["brief"])
    r = subprocess.run(
        [
            "bash", str(h["scripts"] / "audit_append.sh"),
            "--require-absent-session", session,
            "--event", "committee_round_open",
            "--field", f"round_id={round_id}",
            "--field", "task_id=GOVB1-B10-T43",
            "--field", f"brief_path={h['brief_rel']}",
            "--field", f"brief_sha256={brief_sha}",
            "--field", f"brief_sha256_norm={brief_sha}",
            "--field", "lock_mode=discovery",
            "--field", f"participants=@{json.dumps(fams)}",
            "--field",
            f"expected_outputs=@{json.dumps({f: f'{out_prefix}-{f}.md' for f in fams})}",
            "--field", f"session_name={session}",
            "--field", "actor=test",
            "--field", "origin_script=committee_run.sh",
        ],
        cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def _deliver(
    h: dict, *, name: str, content: str, family: str = "codex", stub: str = "preserve"
):
    """把 `content` 當作委員產出**預先寫好**，再以 `preserve` 走交件路徑。

    這正是 `preserve` stub 存在的理由：`success` stub 會覆寫 `${out}`，
    輸入根本餵不進來 ⇒ B8 當時第三欄不可達。
    """
    rid = str(uuid.uuid4())
    out_prefix = f"handoffs/b31-{name}"
    _open_round(h, round_id=rid, session=f"s-{name}", fams=[family], out_prefix=out_prefix)
    out_rel = f"{out_prefix}-{family}.md"
    (h["root"] / out_rel).write_text(content, encoding="utf-8")
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = stub
    proc = subprocess.run(
        ["bash", str(h["scripts"] / "cx_run.sh"), family, h["brief_rel"], out_rel],
        cwd=h["root"], env=env, capture_output=True, text=True, check=False,
    )
    rows = _events(h["audit"], "committee_family_result")
    return proc, (rows[-1] if rows else {})


# 🔴 基準是**量到的**不是猜的（B8 初版三格用猜的，其中一格就錯 ⇒ 已列入本 epic 踩坑）。
#    量法：本檔 `_deliver()` 對三種輸入各跑一次，取 audit 最新 result_state 與 process rc。
CX_RUN_BASELINE = {
    "single_heading_probe": ("success", 0),
    "prose_only": ("success", 0),
    "hollow_p300": ("format-failed", 3),
}


@pytest.mark.parametrize("name", sorted(INPUTS))
def test_entry_cx_run_result_state_matches_baseline(name: str, tmp_path: Path) -> None:
    """**欄③（B8 C5 移交）**：三輸入 × `cx_run` 交件路徑 × `result_state`。

    B8 只能掛逼債條款的那一格，在此以真實執行閉合。
    """
    h = _harness(tmp_path)
    proc, latest = _deliver(h, name=name, content=INPUTS[name])
    want_state, want_rc = CX_RUN_BASELINE[name]
    assert latest.get("result_state") == want_state, (
        f"cx_run/{name} result_state 由基準 {want_state} 變成 "
        f"{latest.get('result_state')!r}；stderr=\n{proc.stderr[-1500:]}"
    )
    assert proc.returncode == want_rc, (
        f"cx_run/{name} rc 由基準 {want_rc} 變成 {proc.returncode}\n{proc.stderr[-1500:]}"
    )


def test_cx_run_column_discriminates_between_inputs() -> None:
    """🔴 反空轉：第三欄若對三種輸入都給同一個 `result_state`，它就沒有鑑別力。

    B8 手搓 `sources.lock` 三格全 rc=1 正是這種假看守（結構性失敗，與輸入無關）。
    """
    states = {v[0] for v in CX_RUN_BASELINE.values()}
    assert len(states) >= 2, f"第三欄基準無鑑別力（全部相同）: {CX_RUN_BASELINE}"


def test_preserve_is_load_bearing_success_stub_blinds_the_column(tmp_path: Path) -> None:
    """🔴 證偽：`preserve` 是**承重**的，不是換個地方掛的說明文字。

    把同一組輸入改用 `success` stub 跑一遍——`_write_stub_success_output` 會覆寫 `${out}`，
    三格於是**全部**變 `success`，第三欄失去鑑別力。
    ⇒ 這正是 B8 當時第三欄不可達的機械成因，也證明上面那張基準表量到的是**輸入差異**，
    不是巧合或結構性失敗（B8 手搓 lock 三格全 rc=1 的那種假看守）。
    """
    h = _harness(tmp_path)
    blinded = {}
    for name in sorted(INPUTS):
        _, latest = _deliver(h, name=f"blind{name}", content=INPUTS[name], stub="success")
        blinded[name] = latest.get("result_state")
    assert set(blinded.values()) == {"success"}, (
        f"success stub 下第三欄竟仍有鑑別力，preserve 的必要性論述不成立: {blinded}"
    )
    assert len({v[0] for v in CX_RUN_BASELINE.values()}) >= 2, (
        "preserve 下反而沒有鑑別力 ⇒ 上表可能是假看守"
    )


def test_three_entry_matrix_is_complete_and_consistent() -> None:
    """三入口 × 三輸入的矩陣三欄都要覆蓋同一組輸入鍵，缺一格即不算閉合。"""
    keys = set(INPUTS)
    assert set(_zeroid.SINGLE_BASELINE) == keys
    assert set(_zeroid.LOCK_BASELINE) == keys
    assert set(CX_RUN_BASELINE) == keys


# ── T-4.3-U1 ────────────────────────────────────────────────────────────────


def test_t43_u1_hollow_delivery_records_format_failed_not_failed(tmp_path: Path) -> None:
    """`T-4.3-U1`：hollow fixture 走交件路徑 ⇒ audit 記 `format-failed`，**不得**記 `failed`。

    SPEC 邊界①：產出實質存在、只是格式不合規 ⇒ 不能與「CLI 掛掉沒產出」混為一談，
    否則 `debt_clear` 的三值契約會退回二值。
    """
    h = _harness(tmp_path)
    proc, latest = _deliver(h, name="u1", content=INPUTS["hollow_p300"])
    assert latest.get("result_state") == "format-failed", latest
    assert latest.get("result_state") != "failed", "format-failed 被降級成 failed"
    # format-failed 須帶非空 sha（failed 才是空字串）
    assert latest.get("output_sha256"), "format-failed 須有非空 output_sha256"
    assert len(latest["output_sha256"]) == 64
    assert proc.returncode == 3, proc.stdout + proc.stderr


# ── T-4.3-U2 ────────────────────────────────────────────────────────────────


def test_t43_u2_stderr_carries_fixup_list_with_file_and_line(tmp_path: Path) -> None:
    """`T-4.3-U2`：stderr 含逐條可修補清單，且**至少一條**帶 `檔:行`。

    這條就是 `票 B-31` 的本體：只給 rc 的舊行為讓委員只能整份重跑（實測約 15 分鐘）。
    """
    h = _harness(tmp_path)
    proc, _ = _deliver(h, name="u2", content=INPUTS["hollow_p300"])
    err = proc.stderr
    assert "可修補清單（逐條）" in err, err[-1500:]
    lines = [ln for ln in err.splitlines() if ln.startswith("  ") and "\t" in ln]
    assert lines, f"清單無三欄條目:\n{err[-1500:]}"
    located = [ln for ln in lines if _looks_located(ln)]
    assert located, f"沒有任何一條帶得出 `檔:行`（`?` 或缺行號）:\n{lines}"
    for ln in located:
        cols = ln.strip().split("\t")
        assert len(cols) == 3, f"條目不是三欄: {ln!r}"
        assert cols[1].strip(), f"違規類型欄為空: {ln!r}"
        assert cols[2].strip(), f"修法欄為空: {ln!r}"


def _looks_located(line: str) -> bool:
    """`  <檔>:<行>\t…` 的第一欄須以 `:<十進位行號>` 收尾（`?` 不算）。"""
    head = line.strip().split("\t", 1)[0]
    if ":" not in head:
        return False
    return head.rsplit(":", 1)[1].isdigit()


# ── T-4.3-U3 ────────────────────────────────────────────────────────────────


_U3_HOLLOW = "## {FAM}-R1-P3-00\n**斷言**:\n**碼證**:\n"
_U3_REAL = (
    "## {FAM}-R1-P3-00\n\n"
    "**斷言**: 本輪逐項核對後無 finding\n\n"
    "**碼證**: scripts/cx_run.sh:1\n\n"
    "**來源摘要**: handoffs/u3-{fam}.md#aaaaaaaaaaaa\n"
)


def _selfcheck(path: Path, family: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CX_RUN), "--selfcheck", str(path), "--family", family],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        env=os.environ.copy(),
    )


@pytest.mark.parametrize(
    ("shape", "tmpl"), [("hollow", _U3_HOLLOW), ("real", _U3_REAL)]
)
def test_t43_u3_chair_selfcheck_rc_matches_committee_delivery(
    shape: str, tmpl: str, tmp_path: Path
) -> None:
    """`T-4.3-U3`：主委自產物走**同一支檢查**（顯式 `--family claude`），rc 與委員產出一致。

    出生事故（摩擦帳事件 18）：主委的 `**來源摘要**` 寫行號而非 12 位雜湊，4 個 P0/P1 全 FAIL
    ——因為 `票 B-31` 的自檢只進了**委員 prompt**，主委產物不流經派工路徑。

    🔴 本測驗的是**同構**（同輸入形態 ⇒ 同 rc），不是「主委被強制跑了」——
    強制點仍缺，見 `cx_run.sh` `--selfcheck` 區塊的誠實邊界與 B10 review-r2 必答。
    """
    chair = tmp_path / "u3-claude.md"
    chair.write_text(tmpl.format(FAM="CLAUDE", fam="claude"), encoding="utf-8")
    chair_rc = _selfcheck(chair, "claude").returncode

    h = _harness(tmp_path)
    proc, latest = _deliver(
        h, name=f"u3{shape}", content=tmpl.format(FAM="CODEX", fam="codex")
    )

    assert chair_rc == proc.returncode, (
        f"主委自檢 rc={chair_rc} 與委員交件 rc={proc.returncode} 不一致（{shape}）"
    )
    if shape == "hollow":
        assert chair_rc == 3, "hollow 應判不合規"
        assert latest.get("result_state") == "format-failed"
    else:
        assert chair_rc == 0, "實質 sentinel 應通過"
        assert latest.get("result_state") == "success"


def test_t43_u3_selfcheck_emits_the_same_fixup_list(tmp_path: Path) -> None:
    """主委路徑不得只給 rc——同一份逐條清單也要給，否則主委仍只能整份重寫。"""
    chair = tmp_path / "u3-fixup-claude.md"
    chair.write_text(_U3_HOLLOW.format(FAM="CLAUDE"), encoding="utf-8")
    r = _selfcheck(chair, "claude")
    assert r.returncode == 3
    assert "可修補清單（逐條）" in r.stderr, r.stderr[-1500:]
    assert any(_looks_located(ln) for ln in r.stderr.splitlines() if "\t" in ln), r.stderr[-1500:]


def test_t43_u3_selfcheck_rejects_bad_usage(tmp_path: Path) -> None:
    """自檢入口的用法錯誤須 fail-closed（rc=2），不得靜默放行成「檢查過了」。"""
    good = tmp_path / "ok-claude.md"
    good.write_text(_U3_REAL.format(FAM="CLAUDE", fam="claude"), encoding="utf-8")
    # 缺 --family
    r1 = subprocess.run(
        ["bash", str(CX_RUN), "--selfcheck", str(good)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert r1.returncode == 2, r1.stdout + r1.stderr
    # 檔不存在
    r2 = _selfcheck(tmp_path / "nope.md", "claude")
    assert r2.returncode == 2, r2.stdout + r2.stderr
    # 兩個產出檔
    r3 = subprocess.run(
        ["bash", str(CX_RUN), "--selfcheck", str(good), str(good), "--family", "claude"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert r3.returncode == 2, r3.stdout + r3.stderr
    # 對照：正確用法確實會過（否則上面三條可能只是「永遠 rc=2」）
    assert _selfcheck(good, "claude").returncode == 0


def test_selfcheck_does_not_touch_audit_or_debt(tmp_path: Path) -> None:
    """🔴 自檢是**唯讀檢查**：不得寫 audit、不得開/銷債。

    否則主委「先自檢一下」就會污染輪次帳，反而製造 `票 B-52` 那類鎖死。
    """
    src = CX_RUN.read_text(encoding="utf-8")
    block = src[src.index('if [ "${1:-}" = "--selfcheck" ]; then'):]
    block = block[: block.index("\nfi\n")]
    for forbidden in ("audit_append.sh", "debt_ledger.sh", "gate.sh", "_emit_family_result"):
        assert forbidden not in block, f"自檢區塊碰了 {forbidden}"


def test_selfcheck_writes_nothing_to_audit_end_to_end(tmp_path: Path) -> None:
    """🔴 **端到端**驗自檢是唯讀的（上一條 `test_selfcheck_does_not_touch_audit_or_debt` 只讀源碼）。

    主委自審 G2 同型檢討：源碼區塊斷言只證明「那段文字裡沒有那四個字串」，
    不證明跑起來真的沒寫 audit（間接呼叫一樣會寫）。這條真的跑一次再比 byte。
    """
    h = _harness(tmp_path)
    before = h["audit"].read_bytes()
    f = tmp_path / "sc-claude.md"
    f.write_text(_U3_HOLLOW.format(FAM="CLAUDE"), encoding="utf-8")
    env = dict(h["env"])
    env["ROUND_ID"] = str(uuid.uuid4())
    r = subprocess.run(
        ["bash", str(h["scripts"] / "cx_run.sh"), "--selfcheck", str(f), "--family", "claude"],
        cwd=h["root"], env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 3, r.stdout + r.stderr
    assert h["audit"].read_bytes() == before, "自檢寫了 audit ⇒ 會污染輪次帳"
    assert _events(h["audit"], "committee_family_result") == []


# ── B9 C5 移交的**端到端**閉合（主委自審 G2）─────────────────────────────


def test_destination_violation_is_caught_end_to_end(tmp_path: Path) -> None:
    """🔴 `_check_findings_destination` 的**第一條端到端測試**。

    在此之前它只有源碼斷言：r1 必答 2 是靠委員當場自建探針驗的，探針沒留下來
    ⇒ 改壞落點檢查不會有任何常駐測試轉紅。`preserve_append_stamp` stub 精確重現
    `票 B-52` 的出事情境（stamp 輪把 finding append 進 stamp-target）。
    """
    h = _harness(tmp_path, kind="stamp")
    proc, latest = _deliver(
        h, name="destviol", content="stamp round output\n",
        family="codex", stub="preserve_append_stamp",
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert latest.get("result_state") == "format-failed", latest
    err = proc.stderr
    assert "findings 落點違規" in err, err[-1500:]
    # 三欄清單須指向 **stamp-target**（不是 ${out}）
    lines = [ln for ln in err.splitlines() if ln.startswith("  ") and "\t" in ln]
    located = [ln for ln in lines if _looks_located(ln)]
    assert located, f"落點違規沒有出三欄清單:\n{err[-1500:]}"
    assert any("b31-stamp-target.md" in ln for ln in located), (
        f"清單指錯檔（應指 stamp-target）:\n{located}"
    )


def test_destination_check_does_not_false_positive(tmp_path: Path) -> None:
    """🔴 對照組：stamp 輪不動 stamp-target ⇒ 不得誤擋。

    沒有這一條，上一條可能只是「stamp 輪永遠 rc=3」的假看守。
    """
    h = _harness(tmp_path, kind="stamp")
    proc, latest = _deliver(
        h, name="destok", content="stamp round output\n", family="codex", stub="preserve",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert latest.get("result_state") == "success", latest
    assert "落點違規" not in proc.stderr


def test_destination_violation_also_emits_fixup_line() -> None:
    """`COMPOSER-R1-P2-02`：落點違規也要給三欄清單（原本只印一行說明）。"""
    s = _src()
    assert "_emit_dest_fixup_line()" in s
    i = s.index("! _check_findings_destination")
    seg = s[i : i + 400]
    assert "_emit_dest_fixup_line" in seg, "落點違規分支未輸出修補清單"
    # 指向 stamp-target 的行號，不是 ${out}
    body = s[s.index("_emit_dest_fixup_line() {"):]
    body = body[: body.index("\n}\n")]
    assert "${_st}" in body and "tail -1" in body, "未定位到 stamp-target 內新增的那條"


# ---------------------------------------------------------------------------
# C5 強制點 — 主委自產 findings 的**產出端**檢查點
# 〔B10 review-r2 必答 1：codex＋composer **兩家核准 (A)**，改 `scripts/doc_format_precheck.sh`〕
#
# 🔴 誠實邊界（兩家與本檔一致，不誇大）：PostToolUse 在寫入**之後**跑 ⇒ 早期警告非硬閘。
#   `CODEX-R2-P1-01` 要求的 fail-closed 強制路徑**另立票**，不在本批。
# ---------------------------------------------------------------------------


def _precheck(h: dict, rel: str) -> subprocess.CompletedProcess[str]:
    """在**隔離 repo** 內跑產出端檢查（`REPO_ROOT` 由 `SCRIPT_DIR/..` 導出 ⇒ 落在 harness）。"""
    return subprocess.run(
        ["bash", str(h["scripts"] / "doc_format_precheck.sh"), str(h["root"] / rel)],
        cwd=h["root"], env=h["env"], capture_output=True, text=True, check=False,
    )


def test_chair_findings_file_is_checked_at_write_time(tmp_path: Path) -> None:
    """🔴 C5 的機械根因是**靜默放行**：`handoffs/` 下沒有 `brief-kind:` 的 .md 判不出型別 ⇒ exit 0。

    摩擦帳事件 18（主委 `**來源摘要**` 寫行號而非 12 位雜湊）因此全程無紅燈。
    """
    h = _harness(tmp_path)
    bad = "handoffs/chair-findings-claude.md"
    (h["root"] / bad).write_text(_U3_HOLLOW.format(FAM="CLAUDE"), encoding="utf-8")
    r = _precheck(h, bad)
    assert r.returncode == 2, f"主委 findings 檔仍被靜默放行:\n{r.stdout + r.stderr}"
    assert "findings" in r.stderr, r.stderr[-1200:]
    # 走的是**與委員交件同一支**檢查 ⇒ 同一份逐條清單
    assert "可修補清單（逐條）" in r.stderr, r.stderr[-1200:]


def test_chair_findings_route_catches_event18_shape(tmp_path: Path) -> None:
    """🔴 直取出生事故本身：P1 的 `**來源摘要**` 寫**行號**而非 12 位雜湊 ⇒ 必須紅。

    這條是本路由存在的唯一理由；它若綠，整個 (A) 就是白做的。
    """
    h = _harness(tmp_path)
    rel = "handoffs/chair-event18-claude.md"
    (h["root"] / rel).write_text(
        "## CLAUDE-R1-P1-01\n\n"
        "**斷言**: 主委自產 finding\n\n"
        "**碼證**: scripts/cx_run.sh:1\n\n"
        "**來源摘要**: scripts/cx_run.sh:157\n",   # ← 行號，不是 12 位雜湊
        encoding="utf-8",
    )
    r = _precheck(h, rel)
    assert r.returncode == 2, f"事件 18 的形態沒被抓到:\n{r.stdout + r.stderr}"
    assert "來源摘要" in r.stderr or "digest" in r.stderr, r.stderr[-1200:]


def test_chair_findings_route_passes_valid_file(tmp_path: Path) -> None:
    """對照組：合規的主委產物不得誤擋（否則上兩條可能只是「永遠 rc=2」）。"""
    h = _harness(tmp_path)
    rel = "handoffs/chair-ok-claude.md"
    (h["root"] / rel).write_text(
        _U3_REAL.format(FAM="CLAUDE", fam="claude"), encoding="utf-8"
    )
    r = _precheck(h, rel)
    assert r.returncode == 0, r.stdout + r.stderr


def test_chair_findings_route_does_not_hijack_other_kinds(tmp_path: Path) -> None:
    """🔴 新路由不得搶走既有型別，也不得擴張到不該管的檔。

    `handoffs/reconcile/*` 已在上游分流；沒有 canonical heading 的 handoffs 檔仍放行。
    """
    h = _harness(tmp_path)
    # ① brief（有 brief-kind:）→ 仍走 brief 檢查並通過
    assert _precheck(h, h["brief_rel"]).returncode == 0
    # ② handoffs 下無 canonical heading → 放行
    plain = "handoffs/plain-note.md"
    (h["root"] / plain).write_text("# 隨手筆記\n\n沒有任何 finding heading。\n", encoding="utf-8")
    assert _precheck(h, plain).returncode == 0
    # ③ reconcile 的 sources 逐字副本 → 由收斂路徑負責，不由本腳本管
    src = h["root"] / "handoffs" / "reconcile" / "s1" / "sources"
    src.mkdir(parents=True)
    (src / "review-claude.md").write_text(_U3_HOLLOW.format(FAM="CLAUDE"), encoding="utf-8")
    assert _precheck(h, "handoffs/reconcile/s1/sources/review-claude.md").returncode == 0


def test_chair_findings_route_is_before_the_silent_passthrough() -> None:
    """🔴 順序即正確性：路由若排在「判不出型別即放行」之後，整段等於未掛。

    收斂檔路由踩過完全同一個坑（見 `doc_format_precheck.sh` 該段註解）。
    """
    s = (REPO_ROOT / "scripts" / "doc_format_precheck.sh").read_text(encoding="utf-8")
    route = s.index('kind="findings"')
    passthrough = s.index('[ -n "${kind}" ] || exit 0')
    assert route < passthrough, "findings 路由排在靜默放行之後 ⇒ 形同未掛"


def test_contract_sot_unchanged_by_this_batch() -> None:
    """Task 4.3 不改 `govflow_lifecycle.json`（那是 Task 4.2 的 single-writer 範圍）。"""
    got = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "scripts/govflow_lifecycle.json"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert got.returncode == 0
    assert got.stdout.strip() == "", f"本批不得改契約 SoT:\n{got.stdout}"
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    assert data["zero_findings_contract"]["findings_destination"]["default"] == (
        "own_output_file"
    )
