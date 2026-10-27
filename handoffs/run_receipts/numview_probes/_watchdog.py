"""NUMVIEW 重型子行程之卡住偵測（預設開、無旗標；使用者 2026-10-22：C 格實測卡 78 分鐘無人察覺——「每次都問了你才看，
浪費那麼多時間，監看有什麼用」）。

🔴 全專案規則（使用者 2026-10-27：「講幾千次不準再因為時間上限問題被停掉」「判停一律重跑，不先查停止的原因，直接重跑不也會停?」）：
- **不因時間終止**：(c) 牆鐘逾預期只記錄（`over_expected`）並於 log 寫一行，不終止。
- **卡死＝無進度**：(a) 須「log 未增長」且「子行程樹 CPU 未前進」（窗內平均 < `CPU_PROGRESS_FRACTION` 核）同時持續
  `log_stall_seconds` 秒；長時間無 log 之計算只要在用 CPU 即不判卡死。讀不到 CPU（psutil 失敗）⇒ **不判卡死**（無從證明
  無進度），記 `monitor_degraded` 續跑，記憶體證據照判（NOCAP Task 0.1 v4 增修①）。
- **終止整個子行程樹**：子行程以新 session 啟動而自成行程群組，終止時整組送信號並補殺脫離群組之子孫（增修②）。
- **終止前先留現場、判原因**（`diagnose`）：向子行程樹送 SIGUSR1（Python 子行程經注入之 sitecustomize 以 faulthandler 把
  全部執行緒之堆疊寫入每行程一檔 `<log>.stacks.<pid>.txt`）、macOS 以 `sample` 取各行程原生堆疊（`<log>.sample.<pid>.txt`；
  失敗時記 rc 與 stderr，不靜默），並記各行程狀態／CPU／RSS、swap 增長與 log 尾段；`cause`＝`memory`（swap 逾門檻終止、或
  swap 增長 ≥ 實體記憶體之半、或行程樹 RSS ≥ 實體記憶體 85%）或 `hang`（其餘：程式卡住）。**呼叫端不得對 `hang` 自動
  重跑**——須依堆疊查原因、修好再跑。
- **判準檔說明已被取代**：`tests/_golden/numview/preregistered_criteria_v9.json` 之 `cell_rules.watchdog._doc`／`_basis` 為 NUMVIEW
  凍結檔（其雜湊綁定既有收據，不得改），其中「log 靜默即終止」「牆鐘上限兜底」之敘述描述 2026-10-27 前之語意；鍵之數值
  照用，終止語意以本模組為準（FFPROD b3 審碼 r9 COMPOSER-R9-P1-01 部分採納）。

`run_watched` 啟動子行程並每 `check_interval_seconds` 檢查一次，任一成立即留現場後終止子行程、回 `stalled`（附理由）：
(a) 子行程之 log 檔 `log_stall_seconds` 秒未增長且 CPU 無進度；(b) 系統 swap 已用量自子行程啟動時之基線增長 > `swap_growth_fraction_of_ram` × 實體
記憶體（MB；跨記憶體級距同一規則）連續 `swap_consecutive_checks` 次（macOS `sysctl vm.swapusage`、Linux `/proc/meminfo`；讀不到 ⇒ 該次不計；基線讀不到 ⇒ 以首次讀到者
為基線；實體記憶體讀不到 ⇒ 本跑不判 swap 條件，(a) 照判；`swap_growth_fraction_of_ram` 為 None ⇒ 停用 swap 條件、只記錄
增長——判準 v6 現行即停用：8 GB 機上正常全特徵生成之 swap 增長與卡住同量級，見判準 `_basis`）。系統既有 swap 不計——判準 v4 之使用比例條件於系統既有 85% swap 時 60 秒即誤殺，見判準 `_basis`）；(c) 牆鐘逾 `wall_multiple_of_expected` × 預期
單格秒數（有預期時），否則逾 `wall_ceiling_seconds` ⇒ 只記錄、不終止（見上）。門檻唯一來源＝現行判準檔 `cell_rules.watchdog`（`load_config`），不另寫。

使用者：估時器 `estimate._run_target`（現行）；凍結腳本 `scripts/numview_freeze_baseline.py` 與生成型探針實作時同用本模組
（`run_watched` 或其 in-process 版本須由實作者接上同一門檻）。
"""

from __future__ import annotations

import math
import os
import platform
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

#: 全域開關（預設開）；mutation 測試以 monkeypatch 關之以證「關掉即紅」
ENABLED = True
STALLED = "stalled"
EXITED = "exited"
#: 子行程樹 CPU 進度門檻：一檢查窗內 CPU 秒數前進 ≥ 此比例 × 窗秒數 ⇒ 視為有進度（不判卡死）。依據（收據
#: handoffs/run_receipts/20261027-nocap-cpu-threshold.json，探針 nocap_probes/idle_cpu.py，30 秒窗實測）：睡眠／等鎖／阻塞讀
#: 皆 0 核、監看自身之 0.5 秒 psutil 取樣執行緒 0.024 核、實際計算約 1 核 ⇒ 0.05 核（監看開銷之 2 倍、低於計算 20 倍）
CPU_PROGRESS_FRACTION = 0.05
CAUSE_MEMORY = "memory"
CAUSE_HANG = "hang"
#: 注入 Python 子行程之 sitecustomize：以 faulthandler 註冊 SIGUSR1 把全部執行緒堆疊寫入 WATCHDOG_STACK_FILE，再串接
#: sys.path 上原本會載入之 sitecustomize（不取代呼叫端既有之探針注入）
_SITECUSTOMIZE = '''\
import faulthandler, importlib.util, os, signal, sys
_wd_path = os.environ.get("WATCHDOG_STACK_FILE")
if _wd_path and hasattr(signal, "SIGUSR1"):
    _wd_file = open(_wd_path + "." + str(os.getpid()) + ".txt", "a")
    faulthandler.register(signal.SIGUSR1, file=_wd_file, all_threads=True, chain=False)
_wd_here = os.path.dirname(os.path.abspath(__file__))
for _wd_p in list(sys.path):
    if os.path.abspath(_wd_p or ".") == _wd_here:
        continue
    _wd_cand = os.path.join(_wd_p or ".", "sitecustomize.py")
    if os.path.isfile(_wd_cand):
        _wd_spec = importlib.util.spec_from_file_location("_wd_chained_sitecustomize", _wd_cand)
        _wd_mod = importlib.util.module_from_spec(_wd_spec)
        _wd_spec.loader.exec_module(_wd_mod)
        break
'''
WATCHDOG_KEYS = ("check_interval_seconds", "log_stall_seconds", "swap_growth_fraction_of_ram", "swap_consecutive_checks",
                 "wall_multiple_of_expected", "wall_ceiling_seconds")


@dataclass(frozen=True)
class WatchdogConfig:
    check_interval_seconds: float
    log_stall_seconds: float
    swap_growth_fraction_of_ram: Optional[float]  # None ⇒ 停用 swap 終止條件（只記錄）
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
    over_expected: bool = False  # 牆鐘逾 (c) 之預期上限（只記錄，不終止）
    cause: Optional[str] = None  # STALLED 時：CAUSE_MEMORY／CAUSE_HANG（`diagnose`）
    diagnosis: Dict[str, Any] = field(default_factory=dict)  # STALLED 時之現場（堆疊檔、各行程狀態、swap、log 尾段）


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


def _tree(pid: int) -> List[Any]:
    """`pid` 與其存活子孫之 psutil.Process；psutil 不可用或列舉失敗 ⇒ 盡力而為（至少本行程）／空。"""
    try:
        import psutil

        root = psutil.Process(pid)
    except Exception:  # noqa: BLE001
        return []
    try:
        return [root] + root.children(recursive=True)
    except Exception:  # noqa: BLE001 — 沙箱／權限不可列舉子孫
        return [root]


def tree_cpu_seconds(pid: int) -> Optional[float]:
    """子行程樹（存活者）之 CPU 秒數（user＋system）；讀不到 ⇒ None（本跑退回只看 log）。"""
    procs = _tree(pid)
    if not procs:
        return None
    total = 0.0
    for p in procs:
        try:
            t = p.cpu_times()
            total += t.user + t.system
        except Exception:  # noqa: BLE001 — 列舉後已結束
            pass
    return total


def stack_dump_env(env: Optional[Mapping[str, str]], log_path: Path) -> Dict[str, str]:
    """回注入堆疊傾印之子行程環境：sitecustomize 目錄前置 PYTHONPATH、`WATCHDOG_STACK_FILE`＝`<log>.stacks`（各 Python 行程寫
    `<log>.stacks.<pid>.txt`，多行程不互相交錯）。"""
    out = dict(os.environ if env is None else env)
    site = Path(str(log_path) + ".wdsite")
    site.mkdir(parents=True, exist_ok=True)
    (site / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")
    out["PYTHONPATH"] = os.pathsep.join([str(site)] + ([out["PYTHONPATH"]] if out.get("PYTHONPATH") else []))
    out["WATCHDOG_STACK_FILE"] = str(log_path) + ".stacks"
    return out


def diagnose(pid: int, log_path: Path, *, swap_growth_mb: Optional[float], swap_threshold_mb: Optional[float],
             swap_hit: bool, ram_mb: Optional[float], settle_seconds: float = 3.0,
             sampler: Optional[Callable[[int, Path], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """終止前留現場並判原因（見模組說明）。回 {cause, processes, stacks_files（pid→檔）, stacks_file（主行程）, native_stacks
    （pid→{path, rc, stderr, error}）, swap_growth_mb, log_tail}。"""
    log_path = Path(log_path)
    procs = _tree(pid)
    info = []
    rss_total = 0
    for p in procs:
        row: Dict[str, Any] = {"pid": p.pid}
        try:
            row.update(status=p.status(), cmdline=" ".join(p.cmdline())[:200], rss_bytes=p.memory_info().rss,
                       cpu_seconds=round(sum(p.cpu_times()[:2]), 2))
            rss_total += row["rss_bytes"]
        except Exception as exc:  # noqa: BLE001
            row["error"] = f"{type(exc).__name__}: {exc}"[:200]
        info.append(row)
    for p in procs:  # Python 子行程（經注入之 sitecustomize）把全部執行緒堆疊寫入 <log>.stacks.<pid>.txt
        try:
            os.kill(p.pid, signal.SIGUSR1)
        except Exception:  # noqa: BLE001
            pass
    time.sleep(settle_seconds)
    sample = sampler or _native_sample
    native = {str(p.pid): sample(p.pid, log_path) for p in procs}
    stacks = {str(p.pid): str(f) for p in procs
              for f in [Path(f"{log_path}.stacks.{p.pid}.txt")] if f.is_file() and f.stat().st_size}
    try:
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
    except OSError:
        tail = []
    memory = swap_hit or (ram_mb is not None and swap_growth_mb is not None and swap_growth_mb >= 0.5 * ram_mb) or \
        (ram_mb is not None and rss_total >= 0.85 * ram_mb * 1024 * 1024)
    return {"cause": CAUSE_MEMORY if memory else CAUSE_HANG, "processes": info, "rss_tree_bytes": rss_total,
            "swap_growth_mb": swap_growth_mb, "swap_threshold_mb": swap_threshold_mb, "ram_mb": ram_mb,
            "stacks_files": stacks, "stacks_file": stacks.get(str(pid)),
            "native_stacks": native, "log_tail": tail}


def _native_sample(pid: int, log_path: Path) -> Dict[str, Any]:
    """macOS `sample <pid> 2`（免 root，同使用者行程）之原生堆疊：{path（成功時）, rc, stderr, error}；失敗照記原因、不靜默。
    非 macOS ⇒ {error: "unsupported_platform"}。"""
    if platform.system() != "Darwin":
        return {"path": None, "error": "unsupported_platform"}
    out = Path(f"{log_path}.sample.{pid}.txt")
    try:
        done = subprocess.run(["sample", str(pid), "2", "-file", str(out)], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"path": None, "error": f"{type(exc).__name__}: {exc}"[:300]}
    ok = out.is_file() and out.stat().st_size > 0
    return {"path": str(out) if ok else None, "rc": done.returncode, "stderr": (done.stderr or "")[-500:],
            "error": None if ok else f"sample 未產出檔（rc={done.returncode}）"}


def _signal_all(pgid: Optional[int], pids: Sequence[int], sig: int) -> None:
    if pgid is not None:
        try:
            os.killpg(pgid, sig)
        except OSError:  # 群組已空或無權限
            pass
    for pid in pids:
        try:
            os.kill(pid, sig)
        except OSError:  # 已結束或無權限
            pass


def _alive(pids: Sequence[int]) -> List[int]:
    """仍存活（非殭屍）之 pid；psutil 不可用 ⇒ 以 os.kill(pid, 0) 判。"""
    out = []
    for pid in pids:
        try:
            import psutil

            if psutil.Process(pid).status() != psutil.STATUS_ZOMBIE:
                out.append(pid)
        except ImportError:
            try:
                os.kill(pid, 0)
                out.append(pid)
            except OSError:
                pass
        except Exception:  # noqa: BLE001 — 已結束
            pass
    return out


def _terminate(proc: "subprocess.Popen[Any]") -> Optional[int]:
    """終止整個子行程樹（NOCAP Task 0.1 v4／v5 增修②）：子行程以新 session 啟動而自成行程群組 ⇒ 對整個群組送 SIGTERM
    （涵蓋快照後才 fork 者），寬限後 SIGKILL；另於送信號前後各取子孫快照、對已脫離群組（自行 setsid）者逐一送信號，
    重複至無存活子孫為止。無權限或已結束者略過。"""
    pids = [p.pid for p in _tree(proc.pid)]
    try:
        pgid: Optional[int] = os.getpgid(proc.pid)
        if pgid == os.getpgid(0):  # 未自成群組（例：呼叫端覆寫 Popen）⇒ 不得對自身群組送信號
            pgid = None
    except OSError:
        pgid = None
    _signal_all(pgid, pids, signal.SIGTERM)
    try:
        rc: Optional[int] = proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        rc = None
    pids = sorted(set(pids) | {p.pid for p in _tree(proc.pid)})
    _signal_all(pgid, pids, signal.SIGKILL)
    if rc is None:
        rc = proc.wait()
    for _ in range(100):  # 已決定終止後之收尾：補殺仍存活之子孫（脫離群組者）
        left = _alive(pids)
        if not left:
            break
        _signal_all(None, left, signal.SIGKILL)
        time.sleep(0.05)
    return rc


def run_watched(cmd: Sequence[str], *, log_path: Path, config: WatchdogConfig, expected_seconds: Optional[float] = None,
                cwd: Optional[str] = None, env: Optional[Mapping[str, str]] = None,
                probe_swap: Callable[[], Optional[float]] = swap_used_mb,
                probe_ram: Callable[[], Optional[float]] = physical_memory_mb,
                clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                probe_cpu: Callable[[int], Optional[float]] = tree_cpu_seconds,
                diagnose_fn: Optional[Callable[..., Dict[str, Any]]] = None,
                stderr_path: Optional[Path] = None) -> WatchResult:
    """啟動 `cmd`（stdout／stderr 寫入 `log_path`；給 `stderr_path` 則 stderr 另寫該檔、進度只計 stdout log 與 CPU），
    依 `config` 監看；卡住（無 log 亦無 CPU 進度、或 swap 逾門檻）⇒ 留現場（`diagnose`）後終止並回 STALLED＋理由＋原因，
    否則回 EXITED＋rc；牆鐘逾預期只記錄。
    `probe_swap` 回系統 swap 已用量（MB）；啟動前讀一次為基線，之後只計增長。門檻＝`swap_growth_fraction_of_ram` ×
    `probe_ram()`（MB）；後者讀不到 ⇒ 本跑不判 swap 條件。"""
    log_path = Path(log_path)
    baseline = probe_swap()
    ram = probe_ram()
    frac = config.swap_growth_fraction_of_ram
    threshold = None if ram is None or frac is None else frac * ram
    started = clock()
    run_env = stack_dump_env(env, log_path)
    with open(log_path, "w", encoding="utf-8") as log, \
            (open(stderr_path, "w", encoding="utf-8") if stderr_path is not None else _NullCtx()) as err:
        # 自成行程群組（新 session）：卡死終止時整組送信號，涵蓋子孫與快照後才 fork 者（NOCAP Task 0.1 增修②）
        proc = subprocess.Popen(list(cmd), cwd=cwd, env=run_env, stdout=log,
                                stderr=err if stderr_path is not None else subprocess.STDOUT, start_new_session=True)
        try:
            # stderr 分檔時監看自身之註記寫 stderr 檔（stdout 留給呼叫端解析）；進度仍以 stdout log 大小與 CPU 判定
            return _watch_loop(proc, err if stderr_path is not None else log, log_path, config, expected_seconds,
                               baseline, ram, threshold, started,
                               probe_swap, clock, sleep, probe_cpu, diagnose_fn)
        except BaseException:  # 呼叫端中斷（Ctrl-C 不再傳到新 session 之子行程）⇒ 一併終止整樹，不留孤兒
            if proc.poll() is None:
                _terminate(proc)
            raise


class _NullCtx:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: Any) -> None:
        return None


NAP_STEP_SECONDS = 0.05  # 檢查間隔內每隔此秒數查一次子行程是否已結束


def _nap(proc: "subprocess.Popen[Any]", seconds: float, sleep: Callable[[float], None]) -> None:
    """睡至下一次檢查；子行程先結束即提早返回——否則每個短命令（秒級 collect、hook）都要空等滿一個檢查間隔
    （判準 30 秒；NOCAP b3 實測閘門改經共用監看時發現）。切成等長小段，總睡眠量與原單次 sleep 相同（注入時鐘之測試不變）。"""
    n = max(1, math.ceil(seconds / NAP_STEP_SECONDS))
    for _ in range(n):
        if proc.poll() is not None:
            return
        sleep(seconds / n)


def _watch_loop(proc: "subprocess.Popen[Any]", log: Any, log_path: Path, config: WatchdogConfig,
                expected_seconds: Optional[float], baseline: Optional[float], ram: Optional[float],
                threshold: Optional[float], started: float, probe_swap: Callable[[], Optional[float]],
                clock: Callable[[], float], sleep: Callable[[float], None], probe_cpu: Callable[[int], Optional[float]],
                diagnose_fn: Optional[Callable[..., Dict[str, Any]]]) -> WatchResult:
    growth_max: Optional[float] = None
    last_size, last_growth, swap_hits = -1, started, 0
    cap = wall_cap_seconds(config, expected_seconds)
    over = False
    degraded: Optional[Dict[str, Any]] = None
    prev_cpu, prev_t = probe_cpu(proc.pid), started
    while True:
        rc = proc.poll()
        if rc is not None:
            return WatchResult(EXITED, rc, None, clock() - started, growth_max, threshold, over,
                               diagnosis={"monitor_degraded": degraded} if degraded else {})
        _nap(proc, config.check_interval_seconds, sleep)
        if not ENABLED:
            continue
        now = clock()
        size = log_path.stat().st_size if log_path.exists() else 0
        if size != last_size:
            last_size, last_growth = size, now
        cpu = probe_cpu(proc.pid)
        if cpu is None:
            # 讀不到 CPU ⇒ 無從證明無進度：不以 log 停滯判卡死（無輸出之計算不得被監看器誤殺；NOCAP Task 0.1 增修①），
            # 記監看降級並續跑；記憶體證據照判
            last_growth = now
            if degraded is None:
                degraded = {"reason": "CPU 讀不到（psutil 失敗）", "since_seconds": round(now - started, 3)}
                log.write("[watchdog] 監看降級：CPU 讀不到，log 停滯不判卡死（記憶體證據照判）\n")
                log.flush()
                last_size = log_path.stat().st_size if log_path.exists() else last_size
        elif prev_cpu is not None and now > prev_t and cpu - prev_cpu >= CPU_PROGRESS_FRACTION * (now - prev_t):
            last_growth = now  # CPU 有進度 ⇒ 不是卡死（長時間無 log 之計算）
        prev_cpu, prev_t = cpu, now
        reason = None
        if now - last_growth >= config.log_stall_seconds:
            reason = f"log 檔 {now - last_growth:.0f} 秒未增長且 CPU 無進度（門檻 {config.log_stall_seconds:.0f} 秒）"
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
        if not over and now - started >= cap:  # 只記錄、不終止
            over = True
            log.write(f"[watchdog] 牆鐘 {now - started:.0f} 秒逾預期 {cap:.0f} 秒（只記錄，不終止；CPU 進度持續監看）\n")
            log.flush()
            last_size = log_path.stat().st_size if log_path.exists() else last_size
        if reason is not None and proc.poll() is None:
            diag = (diagnose_fn or diagnose)(proc.pid, log_path, swap_growth_mb=growth_max, swap_threshold_mb=threshold,
                                             swap_hit=swap_hits >= config.swap_consecutive_checks, ram_mb=ram)
            if degraded:
                diag["monitor_degraded"] = degraded
            rc = _terminate(proc)
            return WatchResult(STALLED, rc, reason, clock() - started, growth_max, threshold, over,
                               diag.get("cause"), diag)


def summary_line(target: str, result: WatchResult) -> str:
    """卡住時之單行摘要（fail-fast 前印出）。"""
    stacks = (result.diagnosis or {}).get("stacks_file")
    return (f"[watchdog] {target}: {result.status}（{result.reason}；原因 {result.cause}；{result.wall_seconds:.0f} 秒；"
            f"堆疊 {stacks}）— 停止後續目標，不寫收據；hang 須依堆疊查因修好再跑，不得直接重跑")
