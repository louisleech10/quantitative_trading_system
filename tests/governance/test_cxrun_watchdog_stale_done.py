# -*- coding: utf-8 -*-
"""cx_run 看門狗：重跑時舊產出檔之 `STATUS: DONE` 不得觸發 killed_after_done。

🔴 背景（review-r43 `CODEX-R43-P1-01` 同根漏項，主委修補時自查）：`_run_cli_watched` 以產出檔含
   `STATUS: DONE` 判「委員已寫完、行程卡死」，逾 grace 即殺子樹並回 0。同輪同家重跑時，產出路徑可能仍是
   前次 attempt 之舊檔（其中已有 `STATUS: DONE`）⇒ 看門狗會在 grace 後殺掉**仍在工作**之 CLI。
   修法：有重跑快照（`_pre_attempt_out_sig`）時，只認寫入簽章已變之 DONE。
   在此之前 `_run_cli_watched` 零測試覆蓋。

測試直接抽出 cx_run.sh 內之四個函式，以真實子行程（`sleep`）驅動；每條約 10–15 秒。
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CX_RUN = REPO_ROOT / "scripts" / "cx_run.sh"
_FUNCS = ("_compute_output_sha", "_output_write_sig", "_kill_tree", "_terminate_cli_group", "_run_cli_watched")


def _extract_functions(src: str) -> str:
    parts = []
    for name in _FUNCS:
        m = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", src, re.M | re.S)
        assert m, f"cx_run.sh 找不到函式 {name}（錨點變了）"
        parts.append(m.group(0))
    return "\n".join(parts)


def _write_watchdog_script(tmp_path: Path, *, stale_done: bool, snapshot: bool, cli: str,
                           grace: int = 1, max_sec: int = 60) -> Path:
    out = tmp_path / "o.md"
    if stale_done:
        out.write_text("## CODEX-R1-P3-00\n\n前次 attempt 之舊檔\n\nSTATUS: DONE\n", encoding="utf-8")
    cli_file = tmp_path / "cli.sh"
    cli_file.write_text(cli, encoding="utf-8")
    body = _extract_functions(CX_RUN.read_text(encoding="utf-8"))
    lines = [
        "set -u",
        body,
        f'out="{out}"',
        f'export OUT="{out}"',
        '_pre_attempt_out_sig=""',
    ]
    if snapshot:
        lines.append('_pre_attempt_out_sig="$(_output_write_sig "${out}")"')
    lines += [
        f'CX_DONE_GRACE_SEC={grace} CX_MAX_SEC={max_sec} _run_cli_watched "${{out}}" -- bash "{cli_file}"',
        'echo "RC=$?"',
    ]
    script = tmp_path / "wd.sh"
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script


def _run_watchdog(tmp_path: Path, *, stale_done: bool, snapshot: bool, cli: str,
                  grace: int = 1, max_sec: int = 60):
    script = _write_watchdog_script(tmp_path, stale_done=stale_done, snapshot=snapshot, cli=cli,
                                    grace=grace, max_sec=max_sec)
    t0 = time.monotonic()
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=120)
    return r, time.monotonic() - t0


def test_stale_done_in_old_output_does_not_kill_live_cli_on_retry(tmp_path: Path) -> None:
    """重跑＋舊檔已含 STATUS: DONE ⇒ 看門狗不得提早殺；CLI 自然結束（12 秒）後才返回。"""
    r, elapsed = _run_watchdog(tmp_path, stale_done=True, snapshot=True, cli="sleep 12\n")
    assert "RC=0" in r.stdout, r.stdout + r.stderr
    assert "killed_after_done" not in r.stderr, r.stderr
    assert elapsed >= 12, f"CLI 被提早終止（{elapsed:.1f}s）"


def test_fresh_done_written_this_attempt_still_triggers_watchdog(tmp_path: Path) -> None:
    """可證偽之另一半：重跑中 CLI **本次**寫入 STATUS: DONE 後卡住 ⇒ 看門狗照常殺（上一條不是靠「重跑一律不殺」通過）。"""
    cli = 'sleep 6\nprintf "%s\\n" "本次 attempt" "STATUS: DONE" > "$OUT"\nsleep 40\n'
    r, elapsed = _run_watchdog(tmp_path, stale_done=True, snapshot=True, cli=cli)
    assert "killed_after_done" in r.stderr, r.stderr
    assert "RC=0" in r.stdout, r.stdout + r.stderr
    assert elapsed < 40, f"看門狗沒有在 grace 後終止卡住之 CLI（{elapsed:.1f}s）"


def test_first_attempt_without_snapshot_keeps_original_done_semantics(tmp_path: Path) -> None:
    """首次派工（無快照）⇒ 既有語意不變：檔含 STATUS: DONE 且 CLI 不退 ⇒ grace 後殺。"""
    r, elapsed = _run_watchdog(tmp_path, stale_done=True, snapshot=False, cli="sleep 40\n")
    assert "killed_after_done" in r.stderr, r.stderr
    assert elapsed < 40, f"首次派工之看門狗語意被改變（{elapsed:.1f}s）"


def test_watchdog_kills_whole_process_group_including_orphaned_grandchild(tmp_path: Path) -> None:
    """🔴 review-r44 `CODEX-R44-P1-01`：看門狗須終止**整個 process group**，不得依賴 `pgrep -P` 樹走訪。

    該家在沙箱實跑：`pgrep` 失敗被靜默吞掉 ⇒ 只殺 root，子孫續跑。本條以雙重 fork 造一個已被
    reparent 之孫行程（`pgrep -P` 樹走訪找不到、但仍在同一群組），CLI 寫入 STATUS: DONE 後卡住 ⇒
    看門狗終止後，該孫行程必須也已結束。在 pgrep 可用之環境下，只靠樹走訪之實作仍會漏殺它，故本條不依賴環境。
    """
    # 🔴 自證時抓到本條初版是假綠：子孫繼承 stdout pipe ⇒ `subprocess.run` 被迫等到它們自然結束才返回，
    #    屆時孫行程（當時只睡 60 秒）早已自己結束 ⇒「改成不整組殺」照樣綠。修：CLI 先把輸出導到 /dev/null
    #    （不占 pipe），子孫睡 300 秒並記 pid，斷言在看門狗返回當下檢查，finally 一律清掉。
    gpid_file = tmp_path / "grandchild.pid"
    cpid_file = tmp_path / "child.pid"
    cli = (
        "exec >/dev/null 2>&1\n"
        f'( sleep 300 & echo $! > "{gpid_file}" )\n'
        'printf "%s\\n" "本次 attempt" "STATUS: DONE" > "$OUT"\n'
        "sleep 300 &\n"
        f'echo $! > "{cpid_file}"\n'
        "wait\n"
    )
    r, elapsed = _run_watchdog(tmp_path, stale_done=False, snapshot=False, cli=cli)
    pids = [int(f.read_text(encoding="utf-8").strip()) for f in (gpid_file, cpid_file) if f.exists()]
    try:
        assert "killed_after_done" in r.stderr, r.stderr
        assert elapsed < 60, f"看門狗未在 grace 後返回（{elapsed:.1f}s）"
        assert gpid_file.exists(), "fixture 前提變了：孫行程 pid 檔未寫出"
        time.sleep(1)
        gpid = int(gpid_file.read_text(encoding="utf-8").strip())
        try:
            os.kill(gpid, 0)
            alive = True
        except ProcessLookupError:
            alive = False
        assert not alive, f"孫行程 {gpid} 在看門狗終止後仍存活（只殺了 root 或子樹，未殺整個群組）"
    finally:
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_sigint_to_wrapper_group_terminates_detached_cli_group(tmp_path: Path) -> None:
    """🔴 review-r45 `CODEX-R45-P1-01`：終端 Ctrl-C 之 SIGINT 只送到前景群組（wrapper），CLI 已 setsid 脫離。

    wrapper 須攔 INT、把終止轉發給 CLI 群組，並以 130 返回（由 caller 照常寫 failed 結果列）。
    本測以 `start_new_session=True` 讓 wrapper 自成群組，再對該群組送 SIGINT，模擬終端 Ctrl-C；
    看門狗 grace／上限刻意設大，確保終止只可能來自訊號轉發。
    """
    cpid_file = tmp_path / "cli.pid"
    spid_file = tmp_path / "sleep.pid"
    cli = (
        "exec >/dev/null 2>&1\n"
        f'echo $$ > "{cpid_file}"\n'
        "sleep 300 &\n"
        f'echo $! > "{spid_file}"\n'
        "wait\n"
    )
    script = _write_watchdog_script(tmp_path, stale_done=False, snapshot=False, cli=cli,
                                    grace=300, max_sec=600)
    proc = subprocess.Popen(["bash", str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    pids: list = []
    try:
        deadline = time.monotonic() + 15
        while not spid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        assert spid_file.exists(), "fixture 前提變了：CLI 未啟動"
        time.sleep(1)
        pids = [int(f.read_text(encoding="utf-8").strip()) for f in (cpid_file, spid_file)]
        os.killpg(proc.pid, signal.SIGINT)
        out, err = proc.communicate(timeout=30)
        assert "RC=130" in out, out + err
        time.sleep(1)
        alive = []
        for pid in pids:
            try:
                os.kill(pid, 0)
                alive.append(pid)
            except ProcessLookupError:
                pass
        assert not alive, f"wrapper 收到 SIGINT 後 CLI 群組仍存活：{alive}"
    finally:
        if proc.poll() is None:
            proc.kill()
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
