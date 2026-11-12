"""分批、每批新行程跑一份 pytest 選取（docs/TEST_SELECTION.md §5 過渡工具 6；NOCAP Task 0.3c ④）。

為何：同一 pytest 行程跑久了，重型特徵生成測試釋放之記憶體不歸還作業系統（2026-11-12 實測：單條
`test_dual_start_convergence_default_config[1d]` 後 phys_footprint 停約 3 GB，系統 malloc 使用中 79 MB、保留 5,063 MB），
後續大量呼叫 `gc.collect()` 之測試因而變慢（同一測試單獨 8.5 秒、其後 15.4 秒、L1c 長跑 8.1 GB 時 55.7 秒）。業界同類
作法：測試依檔分片、各片獨立行程（CI 依檔分片；pytest-xdist 以 worker 行程分攤）。

規劃（`plan`）：ledger 紀錄耗時 ≥60 秒（§4 重型）之 nodeid 各自一批；其餘依選取順序按測試檔聚批，同一檔不拆
（module 等共用 fixture 只付一次），一批累計保守估時達 `--chunk-seconds` 即收批。各批估時＝
`scripts/ledger_durations.py` 之 `conservative_estimate`（只採通過紀錄、含共用 fixture 建置成本轉移）＋每行程開銷
`PROCESS_OVERHEAD_S`。
執行：每批以共用監看（`run_watched`）跑 `pytest @<該批 nodeid 參數檔>`；同時最多 `--jobs` 批。重型批獨占（不與
任何批同時跑：單條重型特徵生成測試併跑時實測 footprint 達 6.8 GB、swap 由 3.9 GB 升至 11.4 GB，8 GB 機器不可併）；
快速層併發時，剩餘可用記憶體（`momentum/FeatureEngineering/memory_budget.py` 之 darwin VM 快照，非 darwin 為 psutil；
讀不到視為不足）須 ≥ `--min-free-gb` ×（執行中批數＋1）——快照時點執行中批未必已到峰值，故逐批預留（審碼 r5）。
停止：任一批卡住（hang／memory）⇒ 不再開新批、等執行中者結束、整跑回該原因 rc（4 hang、5 memory；NOCAP：不自動
重跑）；pytest rc 非 0／1（中斷、內部錯誤、用法錯誤、未收集到）或該批啟動／讀 log 拋例外 ⇒ 同樣停開新批、回 3（該批
記 `status: error`，不得消失）。測試失敗（rc 1）照常續跑。
完整性：每批 pytest 摘要之 passed＋failed＋errors＋skipped＋xfailed＋xpassed 須等於該批條數，否則記 `incomplete`、rc 3。

估時偏差早期標示（2026-11-12 事故：估時工具少估，跑 3 小時 35 分才發現只完成 12%）：每批結束算實際／估時；
實際 > `DEVIATION_RATIO`×估時 **且** 實際−估時 > `DEVIATION_MIN_EXCESS_S` 秒 ⇒ stdout 印 `[chunked] ⚠ 估時偏差 …`（批號、
實際、估時、倍數），summary.json `deviations` 記一筆（scope＝chunk）。已完成批之合計實際／合計估時首次越過同門檻
⇒ 另標示一次（scope＝cumulative，附剩餘批估時×倍數之量級推估）。**只標示**：不停止、不殺行程、不改 rc（NOCAP：
估時只作量級估計，不得作停止條件）——目的是第一批就讓人看見估時模型失準，而不是跑完才發現。
選取後改檔偵測（同日事故：選完測試範圍後又改檔，事後補跑 3,035 條）：規劃時記錄工作樹指紋（HEAD＋「已追蹤檔
相對 HEAD 之變更＋未追蹤檔」各檔 git blob 雜湊；只雜湊有變更之檔；排除 `FRESH_EXCLUDES`、任一層 `__pycache__`／
`.claude` 與本次 `--out` 目錄）
寫入 plan.json `fingerprint`；全部批結束時重算比對，計畫後才被改動／新增／刪除之 repo 檔 ⇒ stdout
`[chunked] ⚠ 計畫後 repo 有變更 …`、summary.json `changed_after_plan`（不改 rc）。`--check-fresh <out 目錄>`：重算並
比對該次 plan 之指紋，有變更 ⇒ 印檔名、rc 1；無 ⇒ rc 0；plan.json 無指紋或讀不到 ⇒ rc 2（給提交前人工或 hook）。

用法：`venv/bin/python scripts/run_chunked.py --select <nodeid 清單> --out <目錄> [--jobs 1] [--min-free-gb 3]
  [--chunk-seconds 900] [--traces <讀檔追蹤.jsonl>...] [--plan-only] [-- <每批額外 pytest 參數>]`
  `venv/bin/python scripts/run_chunked.py --check-fresh <out 目錄>`
輸出：`<目錄>/plan.json`、`chunk_NNN.args`、`chunk_NNN.log`、`summary.json`；stdout 每批一行 `[chunked]`。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
#: 每批新行程之固定開銷（Python 啟動、import、收集）：2026-11-12 三次單條實測 total−call＝7.0、8.0、7.0 秒
PROCESS_OVERHEAD_S = 8.0
#: 快速層併發時每批預留之剩餘記憶體（GB）：依據為單條重型特徵生成測試 tracemalloc 峰值 2,959 MB——快速層批之峰值
#: 未逐批實測，此值為上限參考而非實測保證；重型批不併發（見檔頭）
DEFAULT_MIN_FREE_GB = 3.0
#: 估時偏差標示門檻（兩條件須同時成立）。倍數 2：批估時本已取保守值（只採通過紀錄＋fixture 成本＋行程開銷），
#: 實際仍逾兩倍即表示估時模型對此類批失準，而非一般抖動；超出秒數 300：小批（估時數十秒）之絕對誤差主要來自
#: 行程啟動與機器負載，倍數易破 2 卻無礙整跑排程，5 分鐘以上之落差才值得人看——本日事故實際／估時約 8 倍、
#: 落差以小時計，遠在門檻之上。只標示，不作停止條件（NOCAP）。
DEVIATION_RATIO = 2.0
DEVIATION_MIN_EXCESS_S = 300.0
#: 選取後改檔偵測之排除（repo 相對路徑前綴；以 `/` 結尾者為目錄）：執行產物、交接信箱、工具狀態、資料快取與
#: 跑測試必然改動之 golden inventory（`restore_golden_inventory.sh` 還原對象），非受測程式
FRESH_EXCLUDES = ("runs/", "handoffs/", ".claude/", ".testreg/", "data_cache/", "tests/golden/l65/test_inventory.txt")
#: 任一層目錄名皆排除：`__pycache__`；`.claude`（子目錄亦有工具狀態，如實測 `frontend/.claude/gate/dispatch.token`）
_ANY_LEVEL_EXCLUDES = {"__pycache__", ".claude"}
_SUMMARY =re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected)")


def _load(name: str, path: Path) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _ld() -> Any:
    return _load("run_chunked_ld", REPO / "scripts" / "ledger_durations.py")


def plan(selection: List[str], durations: Dict[str, float], gaps: Dict[str, float],
         shared: Optional[Dict[str, List[str]]], chunk_seconds: float, fast_limit: float,
         fixture_costs: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """選取 → 批次清單（見檔頭「規劃」）。每批：{"kind": "heavy"|"fast", "nodeids": [...], "estimate_s": 秒}；各批獨立
    估（每批新行程各付共用 fixture 與開銷）。"""
    ld = _ld()

    def est(nodes: List[str]) -> float:
        return ld.conservative_estimate(nodes, durations, gaps, shared, fixture_costs)[0] + PROCESS_OVERHEAD_S

    def make(kind: str, nodes: List[str]) -> Dict[str, Any]:
        total, det = ld.conservative_estimate(nodes, durations, gaps, shared, fixture_costs)
        # 獨占：重型、或本批須重建之共用 fixture 實測成本達重型門檻、或成本未知、或含無通過紀錄之 nodeid（新測試／
        # 從未通過，耗時未知；保守）——歷史秒數短而 fixture 重建重者亦須獨占（審碼 r6、r7）
        exclusive = (kind == "heavy" or bool(det["fixture_cost_unknown"]) or bool(det["unknown"])
                     or any(v >= fast_limit for v in det["fixture_cost_added"].values()))
        return {"kind": kind, "nodeids": nodes, "estimate_s": total + PROCESS_OVERHEAD_S, "exclusive": exclusive,
                "unknown": det["unknown"], "fixture_cost_unknown": det["fixture_cost_unknown"]}

    chunks: List[Dict[str, Any]] = []
    by_file: Dict[str, List[str]] = {}
    for n in dict.fromkeys(selection):
        if durations.get(n, 0.0) >= fast_limit:
            chunks.append(make("heavy", [n]))
        else:
            by_file.setdefault(n.split("::", 1)[0], []).append(n)
    cur: List[str] = []
    for nodes in by_file.values():
        cand = cur + nodes
        if cur and est(cand) > chunk_seconds + PROCESS_OVERHEAD_S:
            chunks.append(make("fast", cur))
            cur = list(nodes)
        else:
            cur = cand
    if cur:
        chunks.append(make("fast", cur))
    return chunks


def plan_uncertainty(chunks: List[Dict[str, Any]]) -> Dict[str, int]:
    """分批後之估時未知項計數（守衛 `uncertain_ack` 與 plan.json 同源；審碼 r6）：unknown＝無通過紀錄之 nodeid 數
    （不重複）；fixture_cost_unknown＝各批成本未知之共用 fixture／檔之**逐批實例數**（每批新行程各重付一次）。"""
    return {"unknown": len({n for c in chunks for n in c.get("unknown", [])}),
            "fixture_cost_unknown": sum(len(c.get("fixture_cost_unknown", [])) for c in chunks)}


def parse_summary(text: str) -> Dict[str, int]:
    """pytest 最後一行摘要（`= 3 failed, 10 passed, 1 error in 5.0s =`）→ 計數；無摘要 ⇒ 空 dict。"""
    lines = [ln for ln in text.splitlines() if ln.startswith("=") and " in " in ln and _SUMMARY.search(ln)]
    if not lines:
        return {}
    out: Dict[str, int] = {}
    for num, kind in _SUMMARY.findall(lines[-1]):
        key = "errors" if kind.startswith("error") else kind
        out[key] = out.get(key, 0) + int(num)
    return out


def failed_nodeids(text: str) -> List[str]:
    """`-rfE` 短摘要之 FAILED／ERROR 列 → nodeid。"""
    out = []
    for ln in text.splitlines():
        m = re.match(r"^(FAILED|ERROR) (\S+)", ln)
        if m:
            out.append(f"{m.group(1)} {m.group(2)}")
    return out


def available_gb() -> Optional[float]:
    """剩餘可用記憶體（GB）；讀不到 ⇒ None（不以讀不到放行併發：呼叫端視為不足）。"""
    try:
        sys.path.insert(0, str(REPO))
        from momentum.FeatureEngineering import memory_budget as mb

        return float(mb.admission_snapshot()["available_bytes"]) / 2 ** 30
    except Exception:  # noqa: BLE001
        return None


def deviation(wall_s: float, estimate_s: float) -> bool:
    """實際是否偏離估時達標示門檻（見 `DEVIATION_RATIO`／`DEVIATION_MIN_EXCESS_S`；兩者皆嚴格大於）。"""
    return wall_s > DEVIATION_RATIO * estimate_s and wall_s - estimate_s > DEVIATION_MIN_EXCESS_S


def _git(repo: Path, *args: str) -> bytes:
    # noglob：檔名中之 `*?[` 不當萬用字元；`:(exclude)` 等 pathspec magic 仍有效（--literal-pathspecs 會連 magic 一併關掉）
    return subprocess.run(["git", "-C", str(repo), "--noglob-pathspecs", *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def _excluded(path: str, excludes: Sequence[str]) -> bool:
    if set(path.split("/")) & _ANY_LEVEL_EXCLUDES:
        return True
    return any(path.startswith(e) if e.endswith("/") else path == e for e in excludes)


def _blob_id(path: Path) -> Optional[str]:
    """工作樹檔之 git blob id（與 `git ls-tree` 同一雜湊，故可與任一 commit 之內容直接比）；不存在 ⇒ None；
    目錄（子模組等）⇒ `<dir>`。"""
    try:
        if path.is_symlink():
            data = os.readlink(str(path)).encode()
            return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        if path.is_dir():
            return "<dir>"
        h = hashlib.sha1(b"blob %d\0" % path.stat().st_size)
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    except FileNotFoundError:
        return None


def fingerprint(repo: Path, excludes: Sequence[str] = FRESH_EXCLUDES) -> Dict[str, Any]:
    """工作樹指紋：{"head": HEAD sha 或 None, "files": {相對 HEAD 有變更之已追蹤檔＋未追蹤檔: blob id 或 None（已刪）},
    "excludes": [...]}。只雜湊有變更之檔（未變更檔之內容＝HEAD，由 head 涵蓋）。"""
    excludes = list(excludes)
    spec = ["--", "."] + [f":(exclude){e.rstrip('/')}" for e in excludes]
    try:
        head: Optional[str] = _git(repo, "rev-parse", "--verify", "-q", "HEAD").decode().strip()
    except subprocess.CalledProcessError:
        head = None
    if head:
        tracked = _git(repo, "diff", "--name-only", "--no-renames", "-z", "HEAD", *spec).split(b"\0")
    else:
        tracked = _git(repo, "ls-files", "-z", *spec).split(b"\0")
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "-z", *spec).split(b"\0")
    files: Dict[str, Optional[str]] = {}
    for raw in tracked + untracked:
        p = raw.decode("utf-8", "surrogateescape")
        if p and not _excluded(p, excludes):
            files[p] = _blob_id(repo / p)
    return {"head": head, "files": files, "excludes": excludes}


def _tree_blobs(repo: Path, head: Optional[str], paths: List[str]) -> Dict[str, str]:
    """commit `head` 中各 path 之 blob id（不存在者不列）。"""
    out: Dict[str, str] = {}
    if not head or not paths:
        return out
    for k in range(0, len(paths), 500):
        for ent in _git(repo, "ls-tree", "-r", "-z", head, "--", *paths[k:k + 500]).split(b"\0"):
            if b"\t" in ent:
                meta, name = ent.split(b"\t", 1)
                out[name.decode("utf-8", "surrogateescape")] = meta.split()[2].decode()
    return out


def compare_fingerprints(repo: Path, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """計畫時指紋 vs 現在 → {"changed": [...], "added": [...], "removed": [...], "head_changed": bool}：逐檔比「計畫時
    內容」與「現在內容」（不在變更集者＝其 HEAD 內容），故涵蓋計畫後改檔、新增、刪除、還原、以及其間之 commit。"""
    excludes = old.get("excludes", list(FRESH_EXCLUDES))
    cand = set(old["files"]) | set(new["files"])
    head_changed = old["head"] != new["head"]
    if head_changed and old["head"] and new["head"]:
        cand |= {p for p in _git(repo, "diff", "--name-only", "--no-renames", "-z", old["head"], new["head"])
                 .decode("utf-8", "surrogateescape").split("\0") if p}
    cand = {p for p in cand if not _excluded(p, excludes)}
    before = _tree_blobs(repo, old["head"], sorted(cand - set(old["files"])))
    after = _tree_blobs(repo, new["head"], sorted(cand - set(new["files"])))
    res: Dict[str, Any] = {"changed": [], "added": [], "removed": [], "head_changed": head_changed}
    for p in sorted(cand):
        a = old["files"][p] if p in old["files"] else before.get(p)
        b = new["files"][p] if p in new["files"] else after.get(p)
        if a == b:
            continue
        res["added" if a is None else "removed" if b is None else "changed"].append(p)
    return res


def _fresh_lines(diff: Dict[str, Any], limit: int = 20) -> List[str]:
    lines = []
    for kind in ("changed", "added", "removed"):
        for p in diff[kind][:limit]:
            lines.append(f"  {kind}: {p}")
        if len(diff[kind]) > limit:
            lines.append(f"  {kind}: …其餘 {len(diff[kind]) - limit} 檔見 summary.json")
    return lines


def _n_changed(diff: Optional[Dict[str, Any]]) -> int:
    if not diff or "error" in diff:
        return 0
    return len(diff["changed"]) + len(diff["added"]) + len(diff["removed"])


def check_fresh(out: Path, repo: Optional[Path] = None) -> int:
    """`--check-fresh`：比對 `<out>/plan.json` 之指紋與現況；有變更 ⇒ rc 1，無 ⇒ 0，無指紋／讀不到 ⇒ 2。"""
    repo = REPO if repo is None else repo
    try:
        old = json.loads((out / "plan.json").read_text(encoding="utf-8"))["fingerprint"]
        if not old:
            raise KeyError("fingerprint")
        diff = compare_fingerprints(repo, old, fingerprint(repo, old["excludes"]))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"[chunked] check-fresh 無法比對（{out / 'plan.json'}）：{exc!r}", flush=True)
        return 2
    n = _n_changed(diff)
    if not n:
        print(f"[chunked] check-fresh ok：計畫後 repo 無變更（{out}）", flush=True)
        return 0
    print(f"[chunked] ⚠ check-fresh：計畫後 repo 有變更 {n} 檔（head_changed={diff['head_changed']}）——該次結果"
          f"不一定對應現行程式", flush=True)
    for ln in _fresh_lines(diff, limit=10 ** 9):
        print(ln, flush=True)
    return 1


def run(chunks: List[Dict[str, Any]], out: Path, jobs: int, min_free_gb: float, extra: List[str],
        runner: Optional[Callable[..., Any]] = None, avail: Callable[[], Optional[float]] = available_gb,
        sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
        freshness: Optional[Callable[[], Optional[Dict[str, Any]]]] = None) -> Dict[str, Any]:
    """依序開批（同時最多 `jobs`）；見檔頭「執行／停止／完整性／估時偏差／選取後改檔」。`runner(cmd, log_path,
    expected_seconds)` 回 (status, returncode, cause)；預設為共用監看 `run_watched`。`freshness()` 於全部批結束後
    呼叫，回 `compare_fingerprints` 結果（None＝未比對）。"""
    wd = _load("nocap_shared_watchdog", REPO / "handoffs" / "run_receipts" / "numview_probes" / "_watchdog.py")
    if runner is None:
        sys.path.insert(0, str(REPO))
        from tests.feature_engineering import numview_helpers as nh

        config = wd.load_config(json.loads(nh.current_criteria_path().read_text(encoding="utf-8")))

        def runner(cmd: List[str], log_path: Path, expected_seconds: float):  # type: ignore[misc]
            res = wd.run_watched(cmd, log_path=log_path, config=config, expected_seconds=expected_seconds,
                                 cwd=str(REPO))
            return res.status, res.returncode, res.cause

    results: List[Dict[str, Any]] = []
    lock = threading.Lock()
    stop = {"rc": 0, "why": ""}
    deviations: List[Dict[str, Any]] = []
    cum = {"wall": 0.0, "est": 0.0, "n": 0, "flagged": False}
    finished: set = set()

    def flag_deviation(i: int, chunk: Dict[str, Any], wall: float) -> None:
        """估時偏差標示（只標示；呼叫端持鎖）。"""
        est = float(chunk["estimate_s"])
        finished.add(i)
        cum["wall"] += wall
        cum["est"] += est
        cum["n"] += 1
        if deviation(wall, est):
            ratio = wall / est if est > 0 else float("inf")
            deviations.append({"scope": "chunk", "chunk": i, "kind": chunk["kind"], "wall_s": round(wall),
                               "estimate_s": round(est), "ratio": round(ratio, 2)})
            print(f"[chunked] ⚠ 估時偏差 chunk {i} {chunk['kind']} 實際 {wall:.0f}s／估 {est:.0f}s ＝ {ratio:.1f} 倍"
                  f"（門檻：>{DEVIATION_RATIO:g} 倍且多 >{DEVIATION_MIN_EXCESS_S:.0f}s；只標示、不停止）", flush=True)
        if not cum["flagged"] and deviation(cum["wall"], cum["est"]):
            cum["flagged"] = True
            ratio = cum["wall"] / cum["est"] if cum["est"] > 0 else float("inf")
            rest = sum(float(c["estimate_s"]) for k, c in enumerate(chunks) if k not in finished)
            deviations.append({"scope": "cumulative", "after_chunk": i, "chunks_done": cum["n"],
                               "wall_s": round(cum["wall"]), "estimate_s": round(cum["est"]), "ratio": round(ratio, 2),
                               "remaining_estimate_s": round(rest), "remaining_projected_s": round(rest * ratio)})
            print(f"[chunked] ⚠ 累計估時偏差（已完成 {cum['n']}/{len(chunks)} 批）實際 {cum['wall']:.0f}s／估 "
                  f"{cum['est']:.0f}s ＝ {ratio:.1f} 倍；剩餘批估 {rest:.0f}s，依此倍數量級約 {rest * ratio:.0f}s"
                  f"（只標示、不停止）", flush=True)

    def one(i: int, chunk: Dict[str, Any]) -> None:
        try:
            _one(i, chunk)
        except Exception as exc:  # noqa: BLE001 — 啟動／讀 log 失敗不得使該批消失（r5 CODEX-R5-P1-01）
            with lock:
                results.append({"chunk": i, "kind": chunk["kind"], "n": len(chunk["nodeids"]),
                                "estimate_s": round(chunk["estimate_s"]), "wall_s": 0, "status": "error", "rc": None,
                                "cause": repr(exc), "counts": {}, "failures": [], "log": "", "incomplete": True})
                if not stop["rc"]:
                    stop.update(rc=3, why=f"chunk {i} error {exc!r}")
            print(f"[chunked] chunk {i} error {exc!r}", flush=True)

    def _one(i: int, chunk: Dict[str, Any]) -> None:
        args = out / f"chunk_{i:03d}.args"
        args.write_text("".join(f"{n}\n" for n in chunk["nodeids"]), encoding="utf-8")
        log = out / f"chunk_{i:03d}.log"
        cmd = [str(REPO / "venv" / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE",
               *extra, f"@{args}"]
        t0 = clock()
        status, rc, cause = runner(cmd, log, chunk["estimate_s"])
        wall = clock() - t0
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        counts = parse_summary(text)
        ran = sum(v for k, v in counts.items() if k != "deselected")
        rec = {"chunk": i, "kind": chunk["kind"], "n": len(chunk["nodeids"]), "estimate_s": round(chunk["estimate_s"]),
               "wall_s": round(wall), "status": status, "rc": rc, "cause": cause, "counts": counts,
               "failures": failed_nodeids(text), "log": str(log)}
        rec["incomplete"] = status == wd.EXITED and rc in (0, 1) and ran != len(chunk["nodeids"])
        with lock:
            results.append(rec)
            if status == wd.STALLED and not stop["rc"]:
                stop.update(rc=4 if cause == wd.CAUSE_HANG else 5, why=f"chunk {i} stalled（{cause}）")
            elif status == wd.EXITED and rc not in (0, 1) and not stop["rc"]:
                stop.update(rc=3, why=f"chunk {i} pytest rc={rc}")
            print(f"[chunked] chunk {i} {chunk['kind']} n={len(chunk['nodeids'])} {status} rc={rc} "
                  f"{rec['wall_s']}s/估{rec['estimate_s']}s {counts}", flush=True)
            flag_deviation(i, chunk, wall)

    pending = list(enumerate(chunks))
    running: Dict[Future, Dict[str, Any]] = {}

    def reap() -> None:
        done, _ = wait(list(running), return_when=FIRST_COMPLETED)
        for f in done:
            running.pop(f)
            f.result()  # one() 已攔例外；此處再拋即程式錯誤，不得吞

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        while pending and not stop["rc"]:
            i, chunk = pending[0]
            if running:
                # 重型批獨占（單條重型實測 footprint 達 6.8 GB，8 GB 機器不併跑；r5 CODEX-R5-P1-04）；快速層併發時，
                # 剩餘記憶體須夠「每個執行中批＋新批」各 min_free_gb（快照時點執行中批未必已到峰值，故逐批預留）
                heavy_involved = chunk.get("exclusive", chunk["kind"] == "heavy") or any(
                    c.get("exclusive", c["kind"] == "heavy") for c in running.values())
                free = avail()
                if (len(running) >= max(1, jobs) or heavy_involved or free is None
                        or free < min_free_gb * (len(running) + 1)):
                    reap()
                    continue
            pending.pop(0)
            running[pool.submit(one, i, chunk)] = chunk
        while running:
            reap()
    results.sort(key=lambda r: r["chunk"])
    totals: Dict[str, int] = {}
    for r in results:
        for k, v in r["counts"].items():
            totals[k] = totals.get(k, 0) + v
    incomplete = [r["chunk"] for r in results if r["incomplete"]]
    rc = stop["rc"] or (3 if incomplete or pending else (1 if any(r["rc"] == 1 for r in results) else 0))
    changed: Optional[Dict[str, Any]] = None
    if freshness is not None:
        try:
            changed = freshness()
        except Exception as exc:  # noqa: BLE001 — 比對失敗不得吞：記錄並醒目標示（不改 rc，同偵測之定位）
            changed = {"error": repr(exc)}
            print(f"[chunked] ⚠ 計畫後改檔偵測失敗（無法確認結果對應現行程式）：{exc!r}", flush=True)
        if changed and "error" not in changed and _n_changed(changed):
            print(f"[chunked] ⚠ 計畫後 repo 有變更 {_n_changed(changed)} 檔（head_changed={changed['head_changed']}）"
                  f"——本次結果不一定對應現行程式，受影響者須重跑", flush=True)
            for ln in _fresh_lines(changed):
                print(ln, flush=True)
    summary = {"rc": rc, "stopped": stop["why"], "not_started": [i for i, _ in pending], "incomplete": incomplete,
               "totals": totals, "deviations": deviations, "changed_after_plan": changed, "chunks": results}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra: List[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--select")
    ap.add_argument("--out")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--min-free-gb", type=float, default=DEFAULT_MIN_FREE_GB)
    ap.add_argument("--chunk-seconds", type=float, default=900.0)
    ap.add_argument("--traces", nargs="*", default=[])
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--check-fresh", metavar="OUT", help="比對該次 plan 之工作樹指紋：有變更 rc 1、無 rc 0、無法比對 rc 2")
    args = ap.parse_args(argv)
    if args.check_fresh:
        return check_fresh(REPO / args.check_fresh)
    if not args.select or not args.out:
        ap.error("--select 與 --out 為必填（--check-fresh 模式除外）")
    ld = _ld()
    selection = [ln.strip() for ln in (REPO / args.select).read_text(encoding="utf-8").splitlines() if ln.strip()]
    durations, never, gaps = ld.load_all_detail()
    shared = ld.load_shared(REPO / t for t in args.traces) if args.traces else None
    costs = ld.load_fixture_costs(REPO / t for t in args.traces) if args.traces else None
    chunks = plan(selection, durations, gaps, shared, args.chunk_seconds, ld.FAST_LIMIT_S, costs)
    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)
    excludes = list(FRESH_EXCLUDES)
    try:
        excludes.append(out.resolve().relative_to(REPO.resolve()).as_posix().rstrip("/") + "/")
    except ValueError:
        pass  # --out 在 repo 外：不會出現在 git 變更集
    try:
        fp: Optional[Dict[str, Any]] = fingerprint(REPO, excludes)
    except (OSError, subprocess.CalledProcessError) as exc:
        fp = None
        print(f"[chunked] ⚠ 無法記錄工作樹指紋（計畫後改檔偵測停用）：{exc!r}", flush=True)
    unknown = [n for n in selection if n not in durations]
    (out / "plan.json").write_text(json.dumps({
        "fingerprint": fp,
        "selection": args.select, "n": len(selection), "chunks": len(chunks),
        "heavy_chunks": sum(1 for c in chunks if c["kind"] == "heavy"),
        "estimate_s_serial": round(sum(c["estimate_s"] for c in chunks)), "unknown": unknown,
        "never_passed": sorted(set(selection) & never),
        "fixture_cost_unknown": [x for c in chunks for x in c["fixture_cost_unknown"]],
        "uncertain_ack_needed": plan_uncertainty(chunks), "exclusive_chunks": sum(1 for c in chunks if c["exclusive"]),
        "jobs": args.jobs, "min_free_gb": args.min_free_gb,
        "chunk_list": [{"kind": c["kind"], "exclusive": c["exclusive"], "n": len(c["nodeids"]),
                        "estimate_s": round(c["estimate_s"]), "first": c["nodeids"][0]} for c in chunks]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[chunked] plan n={len(selection)} chunks={len(chunks)} heavy={sum(1 for c in chunks if c['kind'] == 'heavy')}"
          f" estimate_serial={sum(c['estimate_s'] for c in chunks):.0f}s unknown={len(unknown)}"
          f" fingerprint={'-' if fp is None else (fp['head'] or '-')[:12] + '+' + str(len(fp['files'])) + 'dirty'}",
          flush=True)
    if args.plan_only:
        return 0
    fresh = (lambda: compare_fingerprints(REPO, fp, fingerprint(REPO, excludes))) if fp is not None else None
    summary = run(chunks, out, args.jobs, args.min_free_gb, extra, freshness=fresh)
    print(f"[chunked] done rc={summary['rc']} totals={summary['totals']} stopped={summary['stopped'] or '-'} "
          f"incomplete={summary['incomplete']} not_started={len(summary['not_started'])} "
          f"deviations={len(summary['deviations'])} changed_after_plan={_n_changed(summary['changed_after_plan'])}",
          flush=True)
    return int(summary["rc"])


if __name__ == "__main__":
    raise SystemExit(main())
