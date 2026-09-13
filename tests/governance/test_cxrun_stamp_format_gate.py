"""cx_run：stamp 輪亦跑 completeness --single（2026-09-13，DOCROT stamp-r3 死鎖之根因修補）。

病根：cx_run 之格式檢查只對 review|consult|closure 跑，stamp 輪空殼交件（codex 寫 `**核對**`
無 `**碼證**`、`VERDICT: APPROVED`）照記 success；reconcile_build／debt_clear 對同檔會跑同一支
checker ⇒ 紅；success 檔不得改、C-9 不得 abandon、cx_run 拒重派 ⇒ 無出路。
本檔驗：stamp 輪空殼交件 ⇒ `format-failed`（走既有解鎖路徑）；合法 sentinel ⇒ `success`；
checker 缺檔 ⇒ fail-closed（非 success）。沿用 test_govb1_b31_recovery 之真實 cx_run harness。
"""

from __future__ import annotations

from pathlib import Path

from tests.governance.test_govb1_b31_recovery import _deliver, _harness

_SENTINEL_OK = (
    "## CODEX-R1-P3-00\n\n**斷言**: 零 findings sentinel。\n\n**碼證**: 對照組。\n\n"
    "VERDICT: proceed\nBLOCKED-BY:\nCLOSED:\nSTATUS: DONE\n"
)
# 逐字重現 stamp-r3 codex 交件形態：有 **斷言**、無 **碼證**（寫成 **核對**）
_HOLLOW_LIKE_CODEX = (
    "## CODEX-R1-P3-00\n\n**斷言**: 收斂如實反映原文。\n\n**核對**: r2／r3 一致。\n\n"
    "VERDICT: proceed\nBLOCKED-BY:\nCLOSED:\nSTATUS: DONE\n"
)


def test_stamp_hollow_delivery_is_format_failed(tmp_path: Path) -> None:
    """ASSERT stamp 輪交件缺 **碼證** ⇒ result_state=format-failed、rc≠0（前版記 success）。

    mutation：把 cx_run 的 stamp 分支拿掉 ⇒ 本條紅（回到 success）。
    """
    h = _harness(tmp_path, kind="stamp")
    proc, latest = _deliver(h, name="hollow", content=_HOLLOW_LIKE_CODEX, family="codex", stub="preserve")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert latest.get("result_state") == "format-failed", latest
    assert "缺 **斷言**/**碼證**" in proc.stderr or "empty-shell" in proc.stderr, proc.stderr[-800:]


def test_stamp_legal_sentinel_is_success(tmp_path: Path) -> None:
    """ASSERT 合法 sentinel ⇒ success（證明不是 stamp 輪恆紅）。"""
    h = _harness(tmp_path, kind="stamp")
    proc, latest = _deliver(h, name="legal", content=_SENTINEL_OK, family="codex", stub="preserve")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert latest.get("result_state") == "success", latest


def test_stamp_stub_success_output_passes_own_gate(tmp_path: Path) -> None:
    """ASSERT harness `CX_STUB_MODE=success` 對 stamp 寫出的 stub 本身過閘（success）。

    否則所有以 stamp 骨架跑 cx_run 的既有 harness 會因 stub 改壞而假紅。
    """
    h = _harness(tmp_path, kind="stamp")
    proc, latest = _deliver(h, name="stub", content="", family="codex", stub="success")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert latest.get("result_state") == "success", latest
    out = (h["root"] / "handoffs" / "b31-stub-codex.md").read_text(encoding="utf-8")
    assert "## CODEX-R1-P3-00" in out and "**碼證**" in out, out


def test_stamp_register_guarded_by_format_rc() -> None:
    """〔CODEX-R1-P2-02〕ASSERT `_maybe_register_stamp_output` 在 `_fmt_rc≠0` 時不登記 stamp-target。

    誠實邊界：端到端需 gate.sh＋reconcile_body_hash 全套 harness（本檔沿用之 b31 harness 未複製），
    故此處為**源碼結構**斷言＋codex 於閉合輪重跑其 interaction 探針（COMMITTEE_OUTPUT_COUNT 1→0）。
    mutation：刪該 guard ⇒ 本條紅。
    """
    src = (Path(__file__).resolve().parents[2] / "scripts" / "cx_run.sh").read_text(encoding="utf-8")
    fn = src[src.index("_maybe_register_stamp_output() {"):]
    fn = fn[: fn.index("\n}\n")]
    assert '[ "${_fmt_rc:-0}" -ne 0 ]' in fn, "stamp register 缺 _fmt_rc 守衛"
    assert fn.index('[ "${_fmt_rc:-0}" -ne 0 ]') < fn.index("reconcile_body_hash.sh"), "守衛須在 body_hash／register 之前"


def test_stamp_missing_checker_is_fail_closed(tmp_path: Path) -> None:
    """ASSERT checker 缺檔 ⇒ 非 success（缺工具＝檢查沒跑，不得記 success）。"""
    h = _harness(tmp_path, kind="stamp")
    (h["scripts"] / "completeness_check.sh").unlink()
    proc, latest = _deliver(h, name="nochk", content=_SENTINEL_OK, family="codex", stub="preserve")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert latest.get("result_state") != "success", latest
