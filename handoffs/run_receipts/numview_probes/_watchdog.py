"""NUMVIEW 重型子行程之卡住偵測（預設開、無旗標；使用者 2026-10-22：C 格實測卡 78 分鐘無人察覺——「每次都問了你才看，
浪費那麼多時間，監看有什麼用」）。

`run_watched` 啟動子行程並每 `check_interval_seconds` 檢查一次，任一成立即終止子行程、回 `stalled`（附理由）：
(a) 子行程之 log 檔 `log_stall_seconds` 秒未增長；(b) 系統 swap 已用量自子行程啟動時之基線增長 > `swap_growth_fraction_of_ram` × 實體
記憶體（MB；跨記憶體級距同一規則）連續 `swap_consecutive_checks` 次（macOS `sysctl vm.swapusage`、Linux `/proc/meminfo`；讀不到 ⇒ 該次不計；基線讀不到 ⇒ 以首次讀到者
為基線；實體記憶體讀不到 ⇒ 本跑不判 swap 條件，(a)(c) 照判。系統既有 swap 不計——判準 v4 之使用比例條件於系統既有 85% swap 時 60 秒即誤殺，見判準 `_basis`）；(c) 牆鐘逾 `wall_multiple_of_expected` × 預期
單格秒數（有預期時），否則逾 `wall_ceiling_seconds`。門檻唯一來源＝現行判準檔 `cell_rules.watchdog`（`load_config`），不另寫。

使用者：估時器 `estimate._run_target`（現行）；凍結腳本 `scripts/numview_freeze_baseline.py` 與生成型探針實作時同用本模組
（`run_watched` 或其 in-process 版本須由實作者接上同一門檻）。
"""

from __future__ import annotations

import platform
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

#: 全域開關（預設開）；mutation 測試以 monkeypatch 關之以證「關掉即紅」
ENABLED = True
STALLED = "stalled"
EXITED = "exited"
WATCHDOG_KEYS = ("check_interval_seconds", "log_stall_seconds", "swap_growth_fraction_of_ram", "swap_consecutive_checks",
                 "wall_multiple_of_expected", "wall_ceiling_seconds")


@dataclass(frozen=True)
class WatchdogConfig:
    check_interval_seconds: float
    log_stall_seconds: float
    swap_growth_fraction_of_ram: float
    swap_consecutive_checks: int
    wall_multiple_of_expected: float
    wall_ceiling_seconds: float


@dataclass
class WatchResult:
    status: str  # EXITED／STALLED
    returncode: Optional[int]
    reason: Optional[str]
    wall_seconds: float
    swap_growth_max_mb: Optional[float] = None  # 本跑觀測到之最大 swap 增長（MB；門檻校準依據）
    swap_growth_threshold_mb: Optional[float] = None  # 本跑之 swap 增長門檻（MB；實體記憶體讀不到 ⇒ None）


def load_config(criteria: Mapping[str, Any]) -> WatchdogConfig:
    """判準檔 `cell_rules.watchdog`（封閉物件，鍵恰為 `WATCHDOG_KEYS`）；缺或多鍵 ⇒ ValueError（fail-closed）。"""
    node = (criteria.get("cell_rules") or {}).get("watchdog")
    if not isinstance(node, Mapping):
        raise ValueError("判準檔缺 cell_rules.watchdog")
    keys = {k for k in node if not str(k).startswith("_")}
    if keys != set(WATCHDOG_KEYS):
        raise ValueError(f"cell_rules.watchdog 之鍵 {sorted(keys)} ≠ {sorted(WATCHDOG_KEYS)}")
    return WatchdogConfig(**{k: node[k] for k in WATCHDOG_KEYS})


def swap_used_mb() -> Optional[float]:
    """系統 swap 已用量（MB）；讀不到 ⇒ None（該次檢查不計）。"""
    try:
        if platform.system() == "Darwin":
            text = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, timeout=5).stdout
            used = re.search(r"used\s*=\s*([\d.]+)M", text)
            return float(used.group(1)) if used else None
        info = Path("/proc/meminfo").read_text(encoding="utf-8")
        total_kb = int(re.search(r"SwapTotal:\s+(\d+)", info).group(1))  # type: ignore[union-attr]
        free_kb = int(re.search(r"SwapFree:\s+(\d+)", info).group(1))  # type: ignore[union-attr]
        return (total_kb - free_kb) / 1024.0
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None


def physical_memory_mb() -> Optional[float]:
    """實體記憶體（MB；macOS `sysctl -n hw.memsize`、Linux `/proc/meminfo` MemTotal）；讀不到 ⇒ None。"""
    try:
        if platform.system() == "Darwin":
            text = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5).stdout
            return int(text.strip()) / (1024.0 * 1024.0) if text.strip().isdigit() else None
        info = Path("/proc/meminfo").read_text(encoding="utf-8")
        return int(re.search(r"MemTotal:\s+(\d+)", info).group(1)) / 1024.0  # type: ignore[union-attr]
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None


def swap_used_fraction() -> Optional[float]:
    """系統 swap 使用比例（0–1）；讀不到或無 swap ⇒ None（該次檢查不計）。"""
    try:
        if platform.system() == "Darwin":
            text = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, timeout=5).stdout
            total = re.search(r"total\s*=\s*([\d.]+)M", text)
            used = re.search(r"used\s*=\s*([\d.]+)M", text)
            if not total or not used or float(total.group(1)) <= 0:
                return None
            return float(used.group(1)) / float(total.group(1))
        info = Path("/proc/meminfo").read_text(encoding="utf-8")
        total_kb = int(re.search(r"SwapTotal:\s+(\d+)", info).group(1))  # type: ignore[union-attr]
        free_kb = int(re.search(r"SwapFree:\s+(\d+)", info).group(1))  # type: ignore[union-attr]
        return None if total_kb <= 0 else (total_kb - free_kb) / total_kb
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None


def wall_cap_seconds(config: WatchdogConfig, expected_seconds: Optional[float]) -> float:
    return (config.wall_multiple_of_expected * float(expected_seconds) if expected_seconds
            else config.wall_ceiling_seconds)


def _terminate(proc: "subprocess.Popen[Any]") -> Optional[int]:
    proc.terminate()
    try:
        return proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        return proc.wait()


def run_watched(cmd: Sequence[str], *, log_path: Path, config: WatchdogConfig, expected_seconds: Optional[float] = None,
                cwd: Optional[str] = None, env: Optional[Mapping[str, str]] = None,
                probe_swap: Callable[[], Optional[float]] = swap_used_mb,
                probe_ram: Callable[[], Optional[float]] = physical_memory_mb,
                clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep) -> WatchResult:
    """啟動 `cmd`（stdout／stderr 寫入 `log_path`），依 `config` 監看；卡住 ⇒ 終止並回 STALLED＋理由，否則回 EXITED＋rc。
    `probe_swap` 回系統 swap 已用量（MB）；啟動前讀一次為基線，之後只計增長。門檻＝`swap_growth_fraction_of_ram` ×
    `probe_ram()`（MB）；後者讀不到 ⇒ 本跑不判 swap 條件。"""
    log_path = Path(log_path)
    baseline = probe_swap()
    ram = probe_ram()
    threshold = None if ram is None else config.swap_growth_fraction_of_ram * ram
    growth_max: Optional[float] = None
    started = clock()
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(list(cmd), cwd=cwd, env=dict(env) if env is not None else None,
                                stdout=log, stderr=subprocess.STDOUT)
        last_size, last_growth, swap_hits = -1, started, 0
        cap = wall_cap_seconds(config, expected_seconds)
        while True:
            rc = proc.poll()
            if rc is not None:
                return WatchResult(EXITED, rc, None, clock() - started, growth_max, threshold)
            sleep(config.check_interval_seconds)
            if not ENABLED:
                continue
            now = clock()
            size = log_path.stat().st_size if log_path.exists() else 0
            if size != last_size:
                last_size, last_growth = size, now
            reason = None
            if now - last_growth >= config.log_stall_seconds:
                reason = f"log 檔 {now - last_growth:.0f} 秒未增長（門檻 {config.log_stall_seconds:.0f} 秒）"
            used = probe_swap()
            if used is not None and baseline is None:
                baseline = used
            growth = None if used is None or baseline is None else used - baseline
            if growth is not None:
                growth_max = growth if growth_max is None else max(growth_max, growth)
            swap_hits = swap_hits + 1 if growth is not None and threshold is not None and growth > threshold else 0
            if reason is None and swap_hits >= config.swap_consecutive_checks:
                reason = (f"swap 自啟動增長 {growth:.0f} MB > 門檻 {threshold:.0f} MB 連續 {swap_hits} 次"
                          if growth is not None and threshold is not None else "swap 增長逾門檻")
            if reason is None and now - started >= cap:
                reason = f"牆鐘 {now - started:.0f} 秒逾上限 {cap:.0f} 秒"
            if reason is not None and proc.poll() is None:
                rc = _terminate(proc)
                return WatchResult(STALLED, rc, reason, clock() - started, growth_max, threshold)


def summary_line(target: str, result: WatchResult) -> str:
    """卡住時之單行摘要（fail-fast 前印出）。"""
    return f"[watchdog] {target}: {result.status}（{result.reason}；{result.wall_seconds:.0f} 秒）— 停止後續目標，不寫收據"
