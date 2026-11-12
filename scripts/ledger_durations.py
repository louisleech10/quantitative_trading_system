"""TESTREG ledger 逐 nodeid 紀錄耗時：估時依據與 TEST_SELECTION §4 快速層／重型分流（TESTSEL 上線前之過渡工具）。

業界同類：pytest-split 以 `--store-durations` 存 `.test_durations`（最近一次之耗時）、依此估時與分組。本專案之
歷史耗時即 TESTREG 記錄器（`tests/fixtures/testreg_recorder_plugin.py`）寫入之 `.testreg/ledger/*.jsonl`（每檔一個
session：`kind=session` 列含 `argv_raw`，其餘列 `nodeid`、`duration_s`、`outcome`）。取值：每個 nodeid 取**最近一次通過
且無量測負擔**之 session 紀錄；帶覆蓋（`--cov`）、讀檔追蹤（`readtrace_plugin`）或 testmon 之 session 有額外負擔，僅於
無其他通過紀錄時採用；從未通過者取全部紀錄最大值（另列）；同一 session 內重複取最大。pytest-split 存最近一次且不分
結果——其用途為分組平衡，估錯只是不均；本專案作「不得低估」之守衛，故只採通過紀錄（2026-11-12 事故：採最近一次失敗
紀錄致 104 條少估 18,671 秒）。選取之總估時用 `conservative_estimate`（共用 fixture 建置成本隨選取轉移之保守上界）。
token 之路徑部分先正規化為 repo 相對（`./tests`、絕對路徑、`tests/x/.` 皆同 `tests/x`）。

用法（CLI）：`venv/bin/python scripts/ledger_durations.py <清單檔> <輸出前綴> [--traces <讀檔追蹤.jsonl>...]`
  清單檔每行一個 nodeid（建議：以 `--collect-only` 收集之完整 nodeid 清單）、或測試檔／目錄；輸出
  `<前綴>_fast.txt`（紀錄耗時 < 60 秒，每批跑）、`<前綴>_heavy.txt`（≥ 60 秒，收案才跑）、`<前綴>_all.tsv`
  （nodeid\t秒）、`<前綴>_unmatched.txt`（清單中 ledger 無任何紀錄之項，§3-1 必跑、耗時未知）、
  `<前綴>_unexpanded.txt`（檔案／目錄 token：其中 ledger 外之新測試不會出現在任何輸出，須改以收集之 nodeid 清單
  為輸入才完整）、`<前綴>_never_passed.txt`（從未通過、耗時取最大紀錄之項），摘要印 stdout（含快速層／重型之
  `conservative_estimate`；給 `--traces` 則依追蹤之 fixture 資訊判共用，未給者一律視為有用到〔更保守〕）。
函式：`load_durations`、`matched`、`conservative_estimate`、`load_shared`（`scripts/heavy_run_guard.py` 之估時收據交叉
檢查與 `scripts/run_chunked.py` 共用）。
事故：2026-11-11 L1c 讀檔追蹤以類比估 10,800 秒，ledger 實含重型 64,155 秒（`docs/TEST_SELECTION.md` §4）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
LEDGER_DIR = REPO / ".testreg" / "ledger"
FAST_LIMIT_S = 60.0  # docs/TEST_SELECTION.md §4 每批門檻


#: 有量測負擔之 session（argv 含任一）：其耗時偏高，僅於無其他紀錄時採用
_INSTRUMENTED = ("--cov", "readtrace_plugin", "--testmon")
_INDEX_VERSION = 3  # v3：逐檔另存通過紀錄（pass）


def _file_of(token: str) -> str:
    return token.split("::", 1)[0].split("[", 1)[0]


def normalize(token: str, root: Optional[Path] = None) -> str:
    """token 之路徑部分正規化為 repo 相對（去 `./`、絕對路徑轉相對、`a/.`、尾斜線），`::` 後綴原樣保留。"""
    tok = token.strip()
    path, sep, rest = tok.partition("::")
    base = Path(root or REPO)
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.resolve().relative_to(base.resolve())
        except ValueError:
            return tok
    norm = os.path.normpath(str(p))
    return norm + (sep + rest if sep else "")


def _owners(nodeid: str) -> List[str]:
    """nodeid 所屬之全部 token 形式：本身、去參數、各層 `::` 前綴（檔案、類別）、檔案之各層上層目錄。"""
    base = nodeid.split("[", 1)[0]
    parts = base.split("::")
    out = [nodeid, base] + ["::".join(parts[:i]) for i in range(1, len(parts))]
    segs = parts[0].split("/")
    out += ["/".join(segs[:i]) for i in range(1, len(segs))]
    return out


def _read_file(path: Path) -> dict:
    """單一 session 檔 → {"dur": nodeid→該 session 內最大耗時（不分結果）, "pass": nodeid→該 session 內通過紀錄之最大
    耗時, "instr": 是否有量測負擔}。失敗／錯誤／跳過之紀錄常於數秒內中止（2026-11-12 實踩：
    `test_dual_start_convergence_default_config[4h]` 失敗紀錄 1.9 秒、通過 2,068 秒），不代表跑完之耗時。"""
    out: Dict[str, float] = {}
    passed: Dict[str, float] = {}
    instr = False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"dur": out, "pass": passed, "instr": instr}
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        if rec.get("kind") == "session":
            argv = " ".join(str(a) for a in (rec.get("argv_raw") or []))
            instr = instr or any(m in argv for m in _INSTRUMENTED)
            continue
        node = rec.get("nodeid")
        if isinstance(node, str):
            d = float(rec.get("duration_s") or 0.0)
            out[node] = max(out.get(node, 0.0), d)
            if rec.get("outcome") == "passed":
                passed[node] = max(passed.get(node, 0.0), d)
    return {"dur": out, "pass": passed, "instr": instr}


def load_all(ledger_dir: Optional[Path] = None) -> Dict[str, float]:
    """全部 nodeid → 估時用耗時：最近一次**通過**之無量測負擔 session 紀錄（無則最近一次通過之有負擔者）。從未通過
    者**不在表內**——其失敗／錯誤紀錄常數秒即中止，不是跑完之耗時（審碼 r5 GROK-R5-P1-01），與無紀錄者同為估時未知
    （`load_all_detail` 另列 never）。"""
    return load_all_detail(ledger_dir)[0]


def load_all_detail(ledger_dir: Optional[Path] = None) -> Tuple[Dict[str, float], Set[str], Dict[str, float]]:
    """(`load_all` 之耗時表〔只含有通過紀錄者〕, 有紀錄而從未通過之 nodeid 集合, nodeid → 歷次通過紀錄之「最大−最小」
    耗時差距)。增量索引
    `<ledger 上層>/durations_index.json`（逐檔 mtime_ns＋大小＋該檔之耗時表與負擔旗標）：只重讀新增或變動之 ledger
    檔，刪除之檔自索引移除；索引壞、版本不符或讀不到 ⇒ 全量重建。原子寫回。"""
    d = Path(ledger_dir or LEDGER_DIR)
    index_path = d.parent / "durations_index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        ok = index.get("ledger_dir") == str(d.resolve()) and index.get("version") == _INDEX_VERSION
        files = index["files"] if ok else {}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        files = {}
    current: Dict[str, dict] = {}
    changed = False
    for path in d.glob("*.jsonl"):
        try:
            st = path.stat()
        except OSError:
            continue
        sig = [st.st_mtime_ns, st.st_size]
        old = files.get(path.name)
        if isinstance(old, dict) and old.get("sig") == sig:
            current[path.name] = old
        else:
            current[path.name] = {"sig": sig, **_read_file(path)}
            changed = True
    if changed or set(current) != set(files):
        tmp = index_path.with_name(index_path.name + f".tmp-{os.getpid()}")
        try:
            tmp.write_text(json.dumps({"ledger_dir": str(d.resolve()), "version": _INDEX_VERSION, "files": current}),
                           encoding="utf-8")
            os.replace(tmp, index_path)
        except OSError:
            tmp.unlink(missing_ok=True)
    # 依 (無負擔優先, mtime, 檔名) 排序後依序覆寫 ⇒ 每個 nodeid 留下最優先之最近通過紀錄
    passed: Dict[str, float] = {}
    anymax: Dict[str, float] = {}
    lo: Dict[str, float] = {}
    hi: Dict[str, float] = {}
    for _name, entry in sorted(current.items(), key=lambda kv: (not kv[1].get("instr", False), kv[1]["sig"][0], kv[0])):
        passed.update(entry.get("pass") or {})
        for n, v in (entry.get("pass") or {}).items():
            lo[n] = min(lo.get(n, v), v)
            hi[n] = max(hi.get(n, v), v)
        for n, v in (entry.get("dur") or {}).items():
            anymax[n] = max(anymax.get(n, 0.0), v)
    never = set(anymax) - set(passed)
    return dict(passed), never, {n: hi[n] - lo[n] for n in hi}


def conservative_estimate(selection: Iterable[str], durations: Dict[str, float], gaps: Dict[str, float],
                          shared: Optional[Dict[str, List[str]]] = None,
                          fixture_costs: Optional[Dict[str, float]] = None) -> Tuple[float, Dict[str, object]]:
    """選取（nodeid）之保守估時（秒）與明細。共用 fixture（module／class／package 範圍）只由同 session 第一個使用者付
    建置成本，ledger 把它記在當時之付費者上；選取子集時付費者可能未被選、成本轉由被選者付（2026-11-12 實測：
    `test_ffname_dead_code.py::test_mutation_unmapped_stationarity_keys_detected` ledger 0.02 秒、子集選取 239 秒）。
    建置成本反映為同一測試「當付費者」與「不當付費者」之耗時差距 ⇒ 某測試檔只選部分、且被選者用到非 function／非
    session 範圍 fixture（`shared` 為讀檔追蹤之 nodeid→fixture 清單；無追蹤資訊者視為有用到）⇒ 該檔另加一次「檔內
    各測試歷次通過紀錄最大−最小（`gaps`）之最大值」；其餘照被選者加總。不用「整檔加總」：檔內被刻意排除之重型
    測試會被整條算入而爆量（L1c 剩餘快速層實測 31,667 秒對被選加總 5,975 秒）。session 範圍 fixture 每個行程付一次，
    不在此列（分批執行器另計每批開銷）。ledger 無紀錄之 nodeid 不計（另列 `unknown`）。
    驗證（`runs/limit_audit/l1c/eval_fixture_rules2.py`，只用被驗之跑以前之 ledger）：ICPERF L1c 前 900 條實耗 1,498
    秒；被選者加總 703 秒、整檔估 1,727 秒、本估法 1,565 秒。
    **耗時差距不是上界**（審碼 r5 CODEX-R5-P1-03）：付費者每次都同一條時差距為 0。故有實測建置耗時者優先：
    `fixture_costs`（讀檔追蹤之 `fixture_setup_s`，fixture id → 秒）涵蓋該檔被選者所用之全部共用 fixture ⇒ 加其成本
    （同一 fixture 於本選取只計一次）、不用差距；否則以差距代並列入 `fixture_cost_unknown`（估時依據缺口，守衛要求收據
    明示）。專案自訂之 session 範圍 fixture 同理（每行程付一次；pytest／pytest-asyncio 內建者 `_BUILTIN_SESSION` 成本
    可忽略、不計）。ledger 無通過紀錄之 nodeid（無紀錄或從未通過）不計入，列 `unknown`。"""
    sel = [n for n in dict.fromkeys(selection)]
    costs = fixture_costs or {}
    by_file: Dict[str, List[str]] = {}
    for n in durations:
        by_file.setdefault(n.split("::", 1)[0], []).append(n)
    picked: Dict[str, List[str]] = {}
    for n in sel:
        picked.setdefault(n.split("::", 1)[0], []).append(n)
    total = 0.0
    added: Dict[str, float] = {}
    paid: Set[str] = set()
    cost_unknown: List[str] = []
    for f, nodes in picked.items():
        total += sum(durations.get(n, 0.0) for n in nodes)
        chosen = set(nodes)
        partial = any(n not in chosen for n in by_file.get(f, []))
        traced = shared is not None and all(n in shared for n in nodes)
        fixtures = sorted({str(x) for n in nodes for x in ((shared or {}).get(n) or [])
                           if str(x).rsplit("::", 1)[-1] not in _BUILTIN_SESSION})
        session_fx = [x for x in fixtures if x.startswith("session:")]
        file_fx = [x for x in fixtures if not x.startswith("session:")]
        for x in session_fx:  # 專案 session fixture：每行程付一次（同一選取＝同一行程）
            if x in paid:
                continue
            paid.add(x)
            if x in costs:
                added[x] = costs[x]
                total += costs[x]
            else:
                cost_unknown.append(x)
        if not partial:
            continue  # 整檔皆選 ⇒ ledger 已含付費者之建置成本
        if traced and not file_fx:
            continue  # 追蹤顯示未用檔內共用 fixture
        if traced and all(x in costs for x in file_fx):
            for x in file_fx:
                if x not in paid:
                    paid.add(x)
                    added[x] = costs[x]
                    total += costs[x]
            continue
        gap = max((gaps.get(n, 0.0) for n in by_file[f]), default=0.0)
        added[f] = gap
        total += gap
        cost_unknown.append(f)
    unknown = [n for n in sel if n not in durations]
    return total, {"selected_sum": sum(durations.get(n, 0.0) for n in sel), "fixture_cost_added": added,
                   "fixture_cost_unknown": cost_unknown, "unknown": unknown}


#: pytest／pytest-asyncio 內建之 session 範圍 fixture：建置成本可忽略（每條測試幾乎都用；計入會使每個選取皆「成本未知」）
_BUILTIN_SESSION = frozenset({"tmp_path_factory", "event_loop_policy", "cache", "worker_id", "testrun_uid"})


def load_fixture_costs(trace_paths: Iterable[Path]) -> Dict[str, float]:
    """讀檔追蹤 JSONL → 非 function 範圍 fixture id（同 `shared` 之格式）→ 實測建置秒數（多筆取最大）。"""
    out: Dict[str, float] = {}
    for p in trace_paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and isinstance(rec.get("fixture_setup_s"), dict):
                for k, v in rec["fixture_setup_s"].items():
                    out[str(k)] = max(out.get(str(k), 0.0), float(v))
    return out


def load_shared(trace_paths: Iterable[Path]) -> Dict[str, List[str]]:
    """讀檔追蹤 JSONL（`scripts/readtrace_plugin.py`）→ nodeid → 非 function 範圍 fixture 清單（同 nodeid 取最後一筆；
    無 `shared` 欄之舊紀錄不收，即視為無追蹤資訊）。"""
    out: Dict[str, List[str]] = {}
    for p in trace_paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and isinstance(rec.get("nodeid"), str) and isinstance(rec.get("shared"), list):
                out[rec["nodeid"]] = [str(x) for x in rec["shared"]]
    return out


def load_durations(tokens: Iterable[str], ledger_dir: Optional[Path] = None) -> Dict[str, float]:
    """ledger 中屬於任一 token（nodeid、參數化變體、類別、檔案或目錄；路徑先正規化）之 nodeid → 紀錄耗時（秒）。"""
    toks = {normalize(t) for t in tokens if t and t.strip()}
    if not toks:
        return {}
    return {n: d for n, d in load_all(ledger_dir).items() if not toks.isdisjoint(_owners(n))}


def matched(tokens: Iterable[str], durations: Dict[str, float]) -> List[str]:
    """tokens 中於 durations 有對應 nodeid 者。"""
    owned = {o for n in durations for o in _owners(n)}
    return [t for t in tokens if normalize(t) in owned]


def token_durations(tokens: Iterable[str], durations: Dict[str, float]) -> Tuple[Dict[str, float], List[str]]:
    """選取 token → 估時用耗時（輸出**原 token**，不展開成 ledger 之 nodeid）。nodeid 級 token（含 `::`）：ledger 有
    同名紀錄取之；否則（含聚合 token：參數化基名、`file::Class`——pytest 以之選取全部子項）⇒ unmatched（估時未知、
    須以 `--collect-only` 展開成葉 nodeid 再估）：ledger 只知曾通過之子項、不知現有子項全集——取子項最大值會低估
    （兩子項各 40 秒得 40）、取加總亦漏未跑過之新子項（審碼 r9、r10）。檔案／目錄 token：展開為 ledger 中所屬 nodeid——
    其中可能含已不存在之舊 nodeid、亦缺 ledger 外之新測試 ⇒ 作 pytest 選取前須與 `--collect-only` 收集之 nodeid
    取交集（`_unexpanded.txt`／stderr 提示）。
    不展開之理由（2026-11-12 實踩）：ledger 留有已不存在之舊參數化變體（`test_ratiounsafe_registry.py::
    test_all_unsafe_group_with_stationarity_needs_no_packet[inplace]`），展開後作選取 ⇒ pytest「not found」用法錯誤。"""
    out: Dict[str, float] = {}
    unmatched: List[str] = []
    owners: Dict[str, List[str]] = {}
    for n in durations:
        for o in _owners(n):
            owners.setdefault(o, []).append(n)
    for tok in tokens:
        t = normalize(tok)
        if "::" in t:
            if t in durations:
                out[t] = durations[t]
            else:  # 無同名紀錄（含聚合 token）⇒ 估時未知、須以 --collect-only 展開成葉 nodeid
                unmatched.append(tok)
        else:
            hits = owners.get(t) or []
            if not hits:
                unmatched.append(tok)
            for n in hits:
                out[n] = durations[n]
    return out, unmatched


def main(argv: List[str]) -> int:
    traces: List[str] = []
    flag = "--traces" in argv
    if flag:
        i = argv.index("--traces")
        traces, argv = argv[i + 1:], argv[:i]
    if len(argv) != 2 or (flag and not traces):
        print(__doc__, file=sys.stderr)
        return 2
    tokens = [line.strip() for line in Path(argv[0]).read_text(encoding="utf-8").splitlines() if line.strip()]
    prefix = argv[1]
    every, never, gaps = load_all_detail()
    dur, unmatched = token_durations(tokens, every)
    fast = sorted(n for n, d in dur.items() if d < FAST_LIMIT_S)
    heavy = sorted(n for n, d in dur.items() if d >= FAST_LIMIT_S)
    Path(f"{prefix}_fast.txt").write_text("".join(f"{n}\n" for n in fast), encoding="utf-8")
    Path(f"{prefix}_heavy.txt").write_text("".join(f"{n}\n" for n in heavy), encoding="utf-8")
    Path(f"{prefix}_all.tsv").write_text("".join(f"{n}\t{dur[n]:.3f}\n" for n in sorted(dur)), encoding="utf-8")
    Path(f"{prefix}_unmatched.txt").write_text("".join(f"{t}\n" for t in unmatched), encoding="utf-8")
    unexpanded = [t for t in tokens if "::" not in t]
    Path(f"{prefix}_unexpanded.txt").write_text("".join(f"{t}\n" for t in unexpanded), encoding="utf-8")
    print(f"nodeids_logged={len(dur)} fast={len(fast)} heavy={len(heavy)} unmatched={len(unmatched)} "
          f"unexpanded={len(unexpanded)}")
    if unexpanded:
        print("注意：檔案／目錄輸入係依 ledger 展開——ledger 外之新測試不在輸出內（§3-1 必跑），且可能含已不存在之舊"
              " nodeid（作 pytest 選取會 not found）；作選取前須與 --collect-only 收集之 nodeid 取交集，或直接以收集之"
              " nodeid 清單為輸入", file=sys.stderr)
    print(f"fast_total_s={sum(dur[n] for n in fast):.0f} heavy_total_s={sum(dur[n] for n in heavy):.0f}")
    shared = load_shared(Path(t) for t in traces) if traces else None
    costs = load_fixture_costs(Path(t) for t in traces) if traces else None
    est_durs = {**every, **dur}  # 以參數化變體估時之 token 亦有值
    est_fast, det_fast = conservative_estimate(fast, est_durs, gaps, shared, costs)
    est_heavy, det_heavy = conservative_estimate(heavy, est_durs, gaps, shared, costs)
    toks = {normalize(t) for t in tokens}
    nev = sorted(n for n in never if not toks.isdisjoint(_owners(n)))
    Path(f"{prefix}_never_passed.txt").write_text("".join(f"{n}\n" for n in nev), encoding="utf-8")
    print(f"fast_conservative_s={est_fast:.0f} heavy_conservative_s={est_heavy:.0f} "
          f"fixture_cost_unknown={len(det_fast['fixture_cost_unknown']) + len(det_heavy['fixture_cost_unknown'])} "
          f"never_passed={len(nev)}（估時未知，同 unmatched 必跑）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
