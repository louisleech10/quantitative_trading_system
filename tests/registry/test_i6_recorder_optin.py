"""TESTSEL I6 驗收（docs/TESTSEL_I6_SPEC.md Task 1.1／1.2）：記錄器每 session 照寫 ledger、不再讀驗寫 60 MB summary；
摘要讀者改由 ledger 讀時彙總（演算法同原 `_rebuild`：任一行損毀整檔略過、無 session 紀錄略過、每 nodeid 依 started 保留最近 k 筆；
合法性同原 `read_summary`：彙總結果不符 schema `summary.shape` ⇒ 視同不存在）。

開 SPEC 前原型（runs/testsel_route/i6/i6_facts.md，3 次中位）：現行 12.15 秒、只寫 ledger 5.55 秒、不載記錄器 5.11 秒。
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RECORDER_MOD = "tests.fixtures.testreg_recorder_plugin"
LEDGER = REPO / ".testreg" / "ledger"
SUMMARY = REPO / ".testreg" / "summary.json"
SUBSET = REPO / "tests" / "registry" / "fixtures" / "i6_ledger_subset"  # 真實 .testreg/ledger 24 檔逐位元組複本
FAILING = ("failed", "error", "xpassed")
sys.path.insert(0, str(REPO / "scripts"))


def _pytest_plugins(conftest: Path) -> list[str]:
    tree = ast.parse(conftest.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in node.targets):
            return [ast.literal_eval(e) for e in node.value.elts]  # type: ignore[attr-defined]
    return []


def test_i6_recorder_still_registered() -> None:
    """記錄器載入點不變（ledger 照寫供 heavy_run_guard、framepath 閘、清單審之 V 規則使用；規格審 r2）。"""
    assert RECORDER_MOD in _pytest_plugins(REPO / "tests" / "conftest.py")


def test_i6_daily_pytest_writes_ledger_not_summary() -> None:
    """非巢狀日常 pytest：恰新增 1 個 ledger 檔、`summary.json` mtime 不變。"""
    env = {k: v for k, v in os.environ.items() if k != "TESTREG_PARENT_SESSION"}
    before = set(LEDGER.glob("*.jsonl")) if LEDGER.is_dir() else set()
    mtime = SUMMARY.stat().st_mtime_ns if SUMMARY.exists() else None
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
         "tests/registry/test_i6_recorder_optin.py::test_i6_recorder_still_registered"],
        cwd=REPO, env=env, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    after = set(LEDGER.glob("*.jsonl")) if LEDGER.is_dir() else set()
    assert len(after - before) == 1, sorted(str(p) for p in after - before)
    assert (SUMMARY.stat().st_mtime_ns if SUMMARY.exists() else None) == mtime


def _sid(n: int) -> str:
    """合 schema `uuid` 格式且字典序可控之 session_id。"""
    return f"00000000-0000-4000-8000-{n:012x}"


def _nid(name: str) -> str:
    return f"tests/test_i6_cells.py::test_{name}"


def _write_session(d: Path, sid: str, started: str, tests: list[tuple[str, str]], *, corrupt: bool = False,
                   fname: str | None = None, session: bool = True) -> None:
    lines = [json.dumps({"kind": "session", "session_id": sid, "started": started, "fingerprint": "a" * 64,
                         "duration_class": "b" * 64})] if session else []
    for nid, outcome in tests:
        lines.append(json.dumps({"kind": "test", "nodeid": nid, "outcome": outcome, "duration_s": 0.1,
                                 "exception_type": None, "exception_head": None}))
    if corrupt:
        lines.append("{not json")
    (d / f"{fname or sid}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _k() -> int:
    return json.loads((REPO / "tests" / "registry" / "testreg_schema.json").read_text(encoding="utf-8"))["summary"]["k"]


def _reference(d: Path, k: int) -> dict:
    """獨立參考計算（不呼叫受測函式）：全收、依 (started, session_id) 穩定排序、取末 k 筆。"""
    nodes: dict = {}
    for f in sorted(d.glob("*.jsonl")):
        try:
            lines = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        except ValueError:
            continue
        sess = [x for x in lines if x.get("kind") == "session"]
        if not sess:
            continue
        for x in lines:
            if x.get("kind") == "test":
                nodes.setdefault(x["nodeid"], []).append(
                    {"session_id": sess[0]["session_id"], "started": sess[0]["started"],
                     "fingerprint": sess[0]["fingerprint"], "duration_class": sess[0]["duration_class"],
                     "outcome": x["outcome"], "duration_s": x["duration_s"], "exception_type": x["exception_type"],
                     "exception_head": x["exception_head"]})
    return {n: sorted(v, key=lambda r: (r["started"], r["session_id"]))[-k:] for n, v in nodes.items()}


def _legacy_replay(tmp_path: Path, src: Path):
    """舊路徑 oracle：逐 session（檔名序）先落 ledger 檔、再以記錄器保留之 `merge_summary` 累積（首次為 `_rebuild`），
    最後以舊讀者 `read_summary` 讀回（不合法 ⇒ None）。不呼叫受測之 `scripts/testreg.py` 彙總。"""
    sys.path.insert(0, str(REPO / "tests" / "fixtures"))
    import testreg_recorder_plugin as rec  # 舊合併演算法（TESTSEL I6 起不在收尾呼叫，保留作對照）
    from tests.registry.testreg_helpers import schema

    sch = schema()
    ledger = tmp_path / sch["ledger"]["dir"]
    ledger.mkdir(parents=True)
    for f in sorted(src.glob("*.jsonl")):
        (ledger / f.name).write_bytes(f.read_bytes())
        lines = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        rec.merge_summary(tmp_path, sch, lines, next(x for x in lines if x.get("kind") == "session"))
    obj = rec.read_summary(tmp_path / sch["summary"]["path"], sch)
    return None if obj is None else obj["nodes"]


def _legacy_prev_failed(nodes) -> list:
    return sorted(n for n, recs in (nodes or {}).items()
                  if max(recs, key=lambda r: (r["started"], r["session_id"]))["outcome"] in FAILING)


def test_i6_summary_from_ledger_equals_legacy_merge(tmp_path: Path) -> None:
    """真實 ledger 子集：舊 `merge_summary` 逐 session 累積後舊讀者讀回之 nodes == `summary_from_ledger` 逐鍵逐筆相等；
    子集內至少一個 nodeid 紀錄數 > k（故「保留最舊／最先 k 筆」改壞會轉紅）。"""
    import testreg as tr

    legacy = _legacy_replay(tmp_path, SUBSET)
    counts: dict = {}
    for f in SUBSET.glob("*.jsonl"):
        for l in f.read_text(encoding="utf-8").splitlines():
            x = json.loads(l)
            if x.get("kind") == "test":
                counts[x["nodeid"]] = counts.get(x["nodeid"], 0) + 1
    assert max(counts.values()) > _k()
    assert legacy is not None
    assert tr.summary_from_ledger(REPO, SUBSET) == legacy


def test_i6_previously_failed_unchanged(tmp_path: Path) -> None:
    """真實 ledger 子集：previously_failed（各 nodeid 最近一筆 outcome∈{failed, error, xpassed}）與舊 summary 算法相等且非空。"""
    import testreg as tr

    expect = _legacy_prev_failed(_legacy_replay(tmp_path, SUBSET))
    assert expect
    assert tr.previously_failed_from_summary(REPO, SUBSET) == expect


def test_i6_invalid_nodeid_whole_summary_absent_like_legacy(tmp_path: Path) -> None:
    """含不符 `nodeid_param` 之 nodeid（真實 ledger 實有：倉庫外暫存檔之 `::test_x`）⇒ 舊讀者整份視同不存在；
    新讀者同（None、previously_failed＝[]），不改可觀察行為。"""
    import testreg as tr

    d = tmp_path / "src"
    d.mkdir()
    _write_session(d, _sid(1), "2026-01-01T00:00:00Z", [(_nid("ok"), "failed")])
    _write_session(d, _sid(2), "2026-01-02T00:00:00Z", [("::test_outside_repo", "failed")])
    assert _legacy_replay(tmp_path / "legacy", d) is None
    assert tr.summary_from_ledger(REPO, d) is None
    assert tr.previously_failed_from_summary(REPO, d) == []


def test_i6_summary_boundaries_match_reference(tmp_path: Path) -> None:
    """邊界格對獨立參考計算與舊 oracle：超 k 留最新、同 started 依 session_id（與檔名序相反）、壞檔／無 session 檔略過、
    各 outcome；空目錄 ⇒ {}、不存在目錄 ⇒ None。"""
    import testreg as tr

    k = _k()
    d = tmp_path / "ledger"
    d.mkdir()
    assert tr.summary_from_ledger(REPO, d) == {} and tr.summary_from_ledger(REPO, tmp_path / "nope") is None
    for i in range(k + 1):
        _write_session(d, _sid(i), f"2026-02-{i + 1:02d}T00:00:00Z", [(_nid("many"), "passed")])
    _write_session(d, _sid(0xb00), "2026-03-01T00:00:00Z", [(_nid("tie"), "passed")], fname="a-file")
    _write_session(d, _sid(0xa00), "2026-03-01T00:00:00Z", [(_nid("tie"), "failed")], fname="z-file")
    _write_session(d, _sid(0xc00), "2026-03-02T00:00:00Z", [(_nid("tie"), "error")], corrupt=True)
    _write_session(d, _sid(0xd00), "2026-03-03T00:00:00Z", [(_nid("tie"), "error")], session=False)
    outcomes = ("failed", "error", "xpassed", "passed", "skipped", "xfailed")
    for j, o in enumerate(outcomes):
        _write_session(d, _sid(0xe00 + j), "2026-04-01T00:00:00Z", [(_nid(o), o)])
    got = tr.summary_from_ledger(REPO, d)
    assert got == _reference(d, k)
    assert [r["session_id"] for r in got[_nid("many")]] == [_sid(i) for i in range(1, k + 1)]
    assert [r["session_id"] for r in got[_nid("tie")]] == [_sid(0xa00), _sid(0xb00)]
    assert tr.previously_failed_from_summary(REPO, d) == sorted(_nid(o) for o in FAILING)  # tie 最近＝b（passed）
    # 舊 oracle（壞檔與無 session 檔不經記錄器累積：真實流程中 ledger 為原子寫入，故以可解析之 session 回放）
    clean = tmp_path / "clean"
    clean.mkdir()
    for f in d.glob("*.jsonl"):
        if f.stem not in (_sid(0xc00), _sid(0xd00)):
            (clean / f.name).write_bytes(f.read_bytes())
    assert _legacy_replay(tmp_path / "legacy", clean) == got


def test_i6_summary_from_ledger_semantics(tmp_path: Path) -> None:
    """讀時彙總：最近 k 筆（依 started、同 started 以 session_id）、壞行整檔略過、previously_failed 取最近一筆。"""
    import testreg as tr  # scripts/testreg.py

    d = tmp_path / ".testreg" / "ledger"
    d.mkdir(parents=True)
    _write_session(d, _sid(1), "2026-01-01T00:00:00Z", [(_nid("a"), "passed"), (_nid("b"), "failed")])
    _write_session(d, _sid(2), "2026-01-02T00:00:00Z", [(_nid("a"), "failed"), (_nid("b"), "passed")])
    _write_session(d, _sid(3), "2026-01-03T00:00:00Z", [(_nid("a"), "passed")], corrupt=True)  # 整檔略過
    nodes = tr.summary_from_ledger(REPO, d)  # schema 取主 repo、ledger 取暫存目錄
    assert [r["session_id"] for r in nodes[_nid("a")]] == [_sid(1), _sid(2)]
    assert [r["outcome"] for r in nodes[_nid("b")]] == ["failed", "passed"]
    assert tr.previously_failed_from_summary(REPO, d) == [_nid("a")]
