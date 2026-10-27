"""FRAMEPATH 受影響測試閘（SPEC v21 D8、諮詢 r5；v20 D6 之歸屬與錨點防護沿用）：A 組全綠＋B／C 組只跑本批
改動可能影響其結果之 nodeid（測試影響分析），其餘逐項收據；完整性機械比對、失敗逐項與錨點碼態比對歸屬。

流程（單組串行）：
1. A 組＝本票具名驗收（`A_GROUP_BY_PHASE`），須全部 passed（不適用既有紅豁免）。
2. B／C 組：manifest `affected_tests phase=<P>` 所列檔扣 A 組，逐檔 `pytest --collect-only -qq`（rc 須 0，否則拒跑）；
   應跑集合 E 由 `plan` 挑選（S1 處置操作所及／S2 會走被刪或被改分支／S3 靜態輕量檔整檔／必跑／對齊觸發），
   未選者逐項記 `skipped` 封閉理由；C 組（`affected_groups phase=<P> C=…`）排在 B 組之後，只影響順序。
   `--plan` 只產挑選與 admission 收據（不執行測試本體），供執行前估時。
3. 逐檔執行寫 junit xml；結果檔附狀態指紋（排除後之 HEAD 檔案樹身分〔路徑＋blob，排除 numba 快取、handoffs/、生成之清冊〕、同排除之相對 HEAD diff、未追蹤檔路徑＋內容雜湊、資料輸入 kline_cache.h5 內容雜湊、該測試檔內容、
   pytest 參數、phase、有效環境），指紋相同且結果完整才沿用（中斷後接續），否則重跑；pytest rc 非 0／1 ⇒ 該檔視為未完成。
4. 非綠 nodeid 於錨點工作樹重跑同 nodeid；錨點＝本票最晚一筆實作許可之 round_start_head（`.claude/gate/audit.log`，
   與處置驗證器 ⓪ 同一函式），工作樹由本腳本自建（或 `--anchor-worktree` 指定）並驗：HEAD＝錨點、工作樹乾淨、
   被忽略之實體輸入不存在（SPEC v23 D12.1：錨點碼態由許可錨點界定，不比對寫死之 6e07e0ad）。結果類別＋例外型別＋訊息首行（只遮暫存路徑與位址、
   數字不遮）皆同者歸「HEAD 既有紅」，其餘一律「本批造成」。
5. 通過＝A 組全綠、E 完整、無多出之 nodeid、本批造成＝0。收據寫 `--receipt`。

用法（各批同一命令；批次取自本票最晚實作許可之 batch 欄，phase＝b1→1、b2→2、b3→3、b4→3，收據寫
`handoffs/run_receipts/framepath-b<N>-affected.json`；`--anchor-worktree` 省略則自建於系統暫存）：
  PYTHONPATH=. venv/bin/python scripts/framepath_affected_gate.py
"""

from __future__ import annotations

import argparse
import ast
import copy
import datetime
import hashlib
import importlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
MANIFEST_REL = "docs/manifests/FRAMEPATH.json"
PRODUCTION_ROOTS = ("momentum", "api", "config")
A_FILES = (
    "tests/feature_engineering/test_framepath_disposition.py",
    "tests/feature_engineering/test_framepath_cgsa_only.py",
    "tests/feature_engineering/test_framepath_invariance.py",
    "tests/api/test_framepath_api_h5.py",
)
A_GROUP = A_FILES  # 自 B／C 扣除之集合（不分 phase）
A_GROUP_BY_PHASE = {1: A_FILES[:3], 2: A_FILES, 3: A_FILES}
# 須於乾淨工作樹先單獨呼叫之 A 組測試（檢查工作樹改動者；同檔他測之 collect-only 會改寫已追蹤清冊）
A_ISOLATED_FIRST = {"tests/feature_engineering/test_framepath_disposition.py": ("test_check_7_changed_paths_in_scope",)}
PYTEST_FLAGS = ("-q", "-p", "no:cacheprovider", "-o", "log_cli=false", "--log-level=WARNING", "--tb=short")
RUN_RC_OK = (0, 1)  # pytest：0 全過、1 有測試失敗；其餘（中斷、內部錯誤、用法、無測試）＝未完成


class GateError(RuntimeError):
    """閘之前置不成立（具名拒跑）。"""


def manifest_groups(manifest: Mapping, phase: int) -> Tuple[List[str], List[str]]:
    """(B 組, C 組)：affected_tests phase=P 扣除 A 組；C 組＝affected_groups phase=P C=… 所列（須為 affected 之子集）。"""
    rows = manifest["batch_card"]["risk_mitigation"]
    affected = _row_paths(rows, f"affected_tests phase={phase} ")
    c_rows = [r for r in rows if r.startswith(f"affected_groups phase={phase} C=")]
    if len(c_rows) != 1:
        raise GateError(f"manifest 缺或重複 affected_groups phase={phase} C=…")
    c_group = [p for p in c_rows[0].split("C=", 1)[1].split() if p]
    stray = sorted(set(c_group) - set(affected))
    if stray:
        raise GateError(f"C 組含非 affected_tests 之檔：{stray}")
    rest = [p for p in affected if p not in A_GROUP]
    return [p for p in rest if p not in c_group], [p for p in rest if p in c_group]


def _row_paths(rows: Sequence[str], prefix: str) -> List[str]:
    hits = [r for r in rows if r.startswith(prefix)]
    if len(hits) != 1:
        raise GateError(f"manifest 缺或重複 {prefix.strip()}")
    return [p for p in hits[0][len(prefix):].split() if p]


def junit_results(xml_text: str, test_file: str) -> Dict[str, Dict[str, str]]:
    """junit xml → {nodeid: {"outcome", "type", "message"}}；nodeid 由 classname（模組點路徑＋類別）與 name 重建。"""
    module = test_file[:-3].replace("/", ".")
    out: Dict[str, Dict[str, str]] = {}
    for case in ET.fromstring(xml_text).iter("testcase"):
        cls = case.get("classname", "")
        if not (cls == module or cls.startswith(module + ".")):
            continue
        inner = cls[len(module):].lstrip(".")
        nodeid = "::".join([test_file, *[p for p in inner.split(".") if p], case.get("name", "")])
        outcome, etype, msg = "passed", "", ""
        for tag in ("failure", "error", "skipped"):
            el = case.find(tag)
            if el is not None:
                outcome = "failed" if tag == "failure" else tag
                etype = el.get("type", "") or ""
                msg = el.get("message", "") or (el.text or "")
                break
        out[nodeid] = {"outcome": outcome, "type": etype, "message": msg}
    return out


def junit_from_ledger(test_file: str, recs: Sequence[Mapping[str, object]]) -> str:
    """D18：由 TESTREG 紀錄器逐 nodeid 紀錄重建 junit，形狀同 pytest junitxml（`_pytest/junitxml.py`）：call 失敗為
    `<failure message="<型別>: <訊息首行>">`、setup／teardown 失敗為 `<error message='failed on setup with "<型別>: <首行>"'>`、
    passed 無子節點；skipped／xfailed／xpassed ⇒ ValueError（紀錄器不存原因，審查 r74）；皆不寫 failure／error 之 type 屬性（pytest 不寫）。setup／teardown 例外為多行者，pytest
    首行缺結尾引號而紀錄器只存首行、無從得知 ⇒ 不符、錨點歸屬判本批造成（偏嚴）。訊息首行＝紀錄器
    exception_head（str(例外) 首行、截 300 字；逾 300 字者與 pytest 原文不同 ⇒ 錨點歸屬判本批造成，偏嚴）。"""
    module = test_file[:-3].replace("/", ".")
    suite = ET.Element("testsuite", name="pytest")
    for r in recs:
        parts = str(r["nodeid"]).split("::")
        case = ET.SubElement(suite, "testcase", classname=".".join([module, *parts[1:-1]]), name=parts[-1],
                             time=str(r.get("duration_s") or 0))
        outcome, phase = r.get("outcome"), r.get("phase_failed")
        etype, head = str(r.get("exception_type") or ""), str(r.get("exception_head") or "")
        reason = f"{etype}: {head}" if head else etype
        # pytest ExceptionInfo：AssertionError 之 repr 以 "AssertionError('assert " 起首（訊息不含單引號）⇒ 去
        # "AssertionError: " 前綴；首行以外之單引號紀錄器不可見 ⇒ 判斷不符時錨點歸屬判本批造成（偏嚴）
        if etype == "AssertionError" and head.startswith("assert ") and "'" not in head:
            reason = head
        if outcome in ("failed", "error") and phase in ("setup", "teardown"):
            ET.SubElement(case, "error", message=f'failed on {phase} with "{reason}"')
        elif outcome in ("failed", "error"):
            ET.SubElement(case, "failure", message=reason)
        elif outcome != "passed":
            # 審查 r74：skipped／xfailed／xpassed 之原因紀錄器不存，無從重建與 pytest 同形之 junit ⇒ 拒絕（呼叫端不還原、閘重跑）
            raise ValueError(f"{r['nodeid']} outcome={outcome} 無法由紀錄重建")
    root = ET.Element("testsuites", name="pytest tests")
    root.append(suite)
    return ET.tostring(root, encoding="unicode")


_MASKS = (
    (re.compile(r"/(?:private/)?(?:var|tmp)/[^\s'\"]+"), "<tmp>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<hex>"),
)


def failure_identity(result: Mapping[str, str]) -> Tuple[str, str, str]:
    """(結果類別, 例外型別, 正規化訊息首行)；只遮暫存路徑與記憶體位址（每次執行必不同之非語意差異）。數字不遮：
    同一既有紅測試之數值改變即視為本批造成（寧可誤報須人工判讀，不得吞掉數值回歸）。"""
    first = (result.get("message") or "").strip().splitlines()[0] if (result.get("message") or "").strip() else ""
    for pat, rep in _MASKS:
        first = pat.sub(rep, first)
    return result.get("outcome", ""), result.get("type", "") or "", first


def classify(expected: Iterable[str], batch: Mapping[str, Mapping[str, str]],
             anchor: Mapping[str, Mapping[str, str]]) -> Dict[str, object]:
    """完整性與歸屬（純函式）。回傳 {"missing", "unexpected", "caused", "head_red", "passed"}；通過條件見 `verdict`。"""
    exp = list(dict.fromkeys(expected))
    missing = [n for n in exp if n not in batch]
    unexpected = sorted(set(batch) - set(exp))
    caused, head_red, passed = [], [], []
    for n in exp:
        if n not in batch:
            continue
        res = batch[n]
        if res.get("outcome") == "passed":
            passed.append(n)
            continue
        ref = anchor.get(n)
        if ref is not None and failure_identity(ref) == failure_identity(res):
            head_red.append(n)
        else:
            caused.append(n)
    return {"missing": missing, "unexpected": unexpected, "caused": caused, "head_red": head_red, "passed": passed}


def anchor_usable(rc: int, res: Mapping[str, Mapping[str, str]], requested: Sequence[str]) -> Dict[str, Dict[str, str]]:
    """審查 r48：錨點重跑之結果只在 pytest rc ∈ {0,1} 且所請 nodeid 皆有結果時採用；否則整批不採（相關 nodeid
    因錨點無結果而歸本批造成，不得以不完整之錨點吸收）。"""
    if rc not in RUN_RC_OK or set(requested) - set(res):
        return {}
    return {n: dict(res[n]) for n in requested}


def verdict(result: Mapping[str, Sequence[str]], a_failures: Sequence[str], incomplete_files: Sequence[str],
            residual_unexecuted: Sequence[str] = ()) -> bool:
    """通過＝A 組全綠、無未完成檔、無缺、無多出、本批造成＝0、CGSA 殘差定義皆於 A 組不變性比對中被執行（純函式）。"""
    return not (a_failures or incomplete_files or result["missing"] or result["unexpected"] or result["caused"]
                or residual_unexecuted)


# ── TESTREG Task 2.3：隔離失敗（契約 tests/registry/testreg_schema.json `gate_report`）──────────────────────────────
QUARANTINE_FIELDS = ("exception_type", "exception_head", "exception_origin", "fail_line")


def _ledger_records(p: Path) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """ledger 檔 → (session 紀錄, test 紀錄清單)；不可讀或損毀之列略過。"""
    sess: Dict[str, object] = {}
    tests: List[Dict[str, object]] = []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return sess, tests
    for line in lines:
        try:
            rec = json.loads(line) if line.strip() else None
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("kind") == "session" and not sess:
            sess = rec
        elif isinstance(rec, dict) and rec.get("kind") == "test":
            tests.append(rec)
    return sess, tests


def current_failures(ledger_dir: Path, before_names: Iterable[str], test_file: str) -> Dict[str, Dict[str, object]]:
    """契約 `gate_report.current_failure_source`：呼叫前不存在（檔名不在 before_names）、且 argv_raw 有 token 等於該
    測試檔或以「該測試檔::」開頭之 session 之 outcome∈{failed, error} test_record → {nodeid: 紀錄}。"""
    before = set(before_names)
    out: Dict[str, Dict[str, object]] = {}
    for p in sorted(Path(ledger_dir).glob("*.jsonl")) if Path(ledger_dir).is_dir() else []:
        if p.name in before:
            continue
        sess, tests = _ledger_records(p)
        argv = sess.get("argv_raw") if isinstance(sess.get("argv_raw"), list) else []
        if not any(isinstance(t, str) and (t == test_file or t.startswith(test_file + "::")) for t in argv):
            continue
        out.update({str(r["nodeid"]): r for r in tests if r.get("outcome") in ("failed", "error")})
    return out


def quarantine_active(q: Mapping[str, object], today: datetime.date) -> bool:
    """未逾期：expires（YYYY-MM-DD）≥ 今日（V11 之反面）。"""
    return isinstance(q.get("expires"), str) and str(q["expires"]) >= today.isoformat()


def quarantine_match(q: Mapping[str, object], current: Mapping[str, object], ledger_dir: Path) -> bool:
    """契約 `gate_report.quarantine_match`：當前失敗之四欄等於 q.evidence 所指之某筆 failed／error 紀錄之同四欄。"""
    for ev in q.get("evidence") or []:
        if not isinstance(ev, dict):
            continue
        for r in _ledger_records(Path(ledger_dir) / f"{ev.get('session_id')}.jsonl")[1]:
            if r.get("nodeid") == ev.get("nodeid") and r.get("outcome") in ("failed", "error") and \
                    all(r.get(k) == current.get(k) for k in QUARANTINE_FIELDS):
                return True
    return False


def split_quarantined(caused: Sequence[str], current: Mapping[str, Mapping[str, object]], catalog: Mapping,
                      ledger_dir: Path, today: datetime.date) -> Tuple[List[str], List[Dict[str, object]]]:
    """caused → (仍擋者, quarantined_failures)。以函式層 nodeid 比對 quarantine；current 中無紀錄者一律不吸收；
    逾期（`quarantine_active` 為假）或四欄不符（`quarantine_match`）者照擋。"""
    still: List[str] = []
    absorbed: List[Dict[str, object]] = []
    entries = catalog.get("entries", {}) if isinstance(catalog, Mapping) else {}
    for n in caused:
        base = re.sub(r"\[.*\]$", "", n)
        qs = [q for q in ((entries.get(n.split("::", 1)[0]) or {}).get("quarantine") or [])
              if isinstance(q, dict) and q.get("nodeid") == base and quarantine_active(q, today)]
        hit = next((q for q in qs if n in current and quarantine_match(q, current[n], ledger_dir)), None)
        if hit is None:
            still.append(n)
        else:
            absorbed.append({"nodeid": n, "quarantine_expires": hit["expires"], "disposition_ref": hit["disposition_ref"]})
    return still, absorbed


def classify_quarantine(caused: Sequence[str], runner: "Runner", catalog: Mapping, ledger_dir: Path,
                        today: datetime.date) -> Tuple[List[str], List[Dict[str, object]]]:
    """編排：每個 caused 所在測試檔以 Runner 於該檔呼叫前所記之 ledger 檔名集合呼叫 `current_failures`（未經 Runner
    呼叫之檔無當前紀錄），再交 `split_quarantined`。"""
    current: Dict[str, Dict[str, object]] = {}
    for f in dict.fromkeys(n.split("::", 1)[0] for n in caused):
        if f in runner.ledger_snapshots:
            current.update(current_failures(ledger_dir, runner.ledger_snapshots[f], f))
    return split_quarantined(caused, current, catalog, ledger_dir, today)


def quarantined_verdict(result: Mapping[str, Sequence[str]], a_failures: Sequence[str], incomplete: Sequence[str],
                        unexecuted: Sequence[str], runner: "Runner", catalog: Mapping, ledger_dir: Path,
                        today: datetime.date) -> Tuple[bool, List[Dict[str, object]]]:
    """main 之唯一裁決組合：caused 經隔離分流（`classify_quarantine`）後之 `verdict`；其餘失敗輸入不受隔離影響。"""
    still, absorbed = classify_quarantine(result["caused"], runner, catalog, ledger_dir, today)
    return verdict(dict(result, caused=still), a_failures, incomplete, unexecuted), absorbed


PROBE_DIR_ENV = "FRAMEPATH_DEF_PROBE_DIR"
PROBE_DEFS_ENV = "FRAMEPATH_DEF_PROBE_DEFS"


def install_def_probe() -> None:
    """環境變數 `FRAMEPATH_DEF_PROBE_DIR`／`_DEFS`（`模組:限定名` 逗號分隔）已設 ⇒ 以保留描述子型別之包裝記錄各定義
    是否被呼叫，行程結束寫 `<dir>/<pid>.json`（不改回傳值與例外）。由 `scripts/freeze_framepath_baseline.py` 之子行程
    呼叫（A 組不變性比對之 11 格皆於子行程生成）。重複呼叫無作用。"""
    import atexit
    import functools
    import importlib
    import inspect

    out_dir, specs = os.environ.get(PROBE_DIR_ENV, "").strip(), os.environ.get(PROBE_DEFS_ENV, "").strip()
    if not out_dir or not specs or getattr(install_def_probe, "_installed", False):
        return
    install_def_probe._installed = True  # type: ignore[attr-defined]
    hit: set = set()
    for spec in [s for s in specs.split(",") if s]:
        mod_name, qual = spec.split(":", 1)
        owner = importlib.import_module(mod_name)
        parts = qual.split(".")
        for p in parts[:-1]:
            owner = getattr(owner, p)
        raw = inspect.getattr_static(owner, parts[-1])
        fn = raw.__func__ if isinstance(raw, (staticmethod, classmethod)) else raw

        def _wrap(fn=fn, spec=spec):
            @functools.wraps(fn)
            def wrapper(*a, **k):
                hit.add(spec)
                return fn(*a, **k)
            return wrapper

        w = _wrap()
        setattr(owner, parts[-1], type(raw)(w) if isinstance(raw, (staticmethod, classmethod)) else w)

    def _flush() -> None:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / f"{os.getpid()}.json").write_text(json.dumps(sorted(hit)), encoding="utf-8")

    atexit.register(_flush)
    install_def_probe._flush = _flush  # type: ignore[attr-defined]


def pytest_configure(config) -> None:  # noqa: ARG001 — 以 `-p framepath_affected_gate` 載入時之 pytest 鉤子
    """受影響測試閘以本模組為 pytest 外掛（`-p framepath_affected_gate`，PYTHONPATH 含 scripts/）執行 A／B／C 時，
    於測試行程內裝殘差定義探針（環境變數未設則無作用）。"""
    install_def_probe()


PROBE_PLUGIN_ARGS = ("-p", "framepath_affected_gate")


def probe_hits(probe_dir: Path) -> set:
    hits: set = set()
    for p in sorted(Path(probe_dir).glob("*.json")) if Path(probe_dir).is_dir() else []:
        try:
            hits |= set(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return hits


TESTREG_SCHEMA_REL = "tests/registry/testreg_schema.json"
TESTREG_CATALOG_REL = "tests/registry/catalog.json"


def _testreg_schema(repo: Path) -> Dict[str, object]:
    return json.loads((Path(repo) / TESTREG_SCHEMA_REL).read_text(encoding="utf-8"))


# TESTREG Task 2.3：單一來源＝契約 `ledger.env_prefixes`（記錄器之 fingerprint 同表；PYTEST＝PYTEST_ADDOPTS 等，審查 r55）
ENV_PREFIXES = tuple(_testreg_schema(REPO)["ledger"]["env_prefixes"])


# ── SPEC v25 D16：結果沿用以「該次 pytest 呼叫實際讀到之檔」為準（執行期記錄；業界 pytest-testmon／Bazel 同理）──────
# 每次 A／B／C 呼叫之子行程環境帶 FRAMEPATH_TRACE_DIR 並把 scripts/framepath_trace_site 置於 PYTHONPATH 首位，
# 由其 sitecustomize 於每個 Python 行程（含 multiprocessing worker）裝 scripts/framepath_trace.py 之讀取記錄器。
# 呼叫結束後於 meta 記 trace：讀取之 repo 檔（內容 sha256；不存在亦記）、列舉之 repo 目錄（項目名清單 sha256）、
# venv 套件清單指紋、記錄工具本身指紋。沿用條件（Runner.run）：state_key 相同（原規則），或 call_id 相同且 trace
# 中每項於目前狀態皆不變。任一行程未正常結束、有無法追蹤之子行程（非 Python 或環境未帶記錄器）、記錄器例外 ⇒
# trace＝None（只能依 state_key 沿用，偏多跑）。
TRACE_SITE_DIR = REPO / "scripts" / "framepath_trace_site"
TRACE_DIR_ENV = "FRAMEPATH_TRACE_DIR"
TRACE_TOOL_FILES = ("scripts/framepath_affected_gate.py", "scripts/framepath_trace.py",
                    "scripts/framepath_trace_site/sitecustomize.py")
_TRACE_SKIP_PREFIXES = ("venv/", ".git/")


def _trace_tool_hash(repo: Path) -> str:
    """記錄工具指紋：記錄器與 sitecustomize 全文＋閘於測試行程內載入之外掛函式原始碼（閘其餘部分不在測試行程執行）。"""
    h = hashlib.sha256()
    for rel in TRACE_TOOL_FILES[1:]:
        p = Path(repo) / rel
        h.update(p.read_bytes() if p.is_file() else b"<missing>")
    gp = Path(repo) / TRACE_TOOL_FILES[0]
    src = gp.read_text(encoding="utf-8") if gp.is_file() else ""
    fns = {n.name: ast.get_source_segment(src, n) or "" for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    for name in ("install_def_probe", "pytest_configure"):
        h.update(fns.get(name, "").encode("utf-8"))
    return h.hexdigest()


def venv_fingerprint(repo: Path) -> str:
    """venv 已安裝套件（site-packages 下 *.dist-info 目錄名，含版本）＋ Python 版本。"""
    names = sorted(p.name for p in (Path(repo) / "venv" / "lib").glob("python*/site-packages/*.dist-info"))
    return hashlib.sha256(("\n".join(names) + "\n" + sys.version).encode("utf-8")).hexdigest()


def _path_state(p: Path) -> str:
    if p.is_dir():
        return "<dir>"
    return _file_sha(p) if p.is_file() else "<missing>"


def _listing_state(p: Path) -> str:
    if not p.is_dir():
        return "<notdir>"
    return hashlib.sha256("\n".join(sorted(os.listdir(p))).encode("utf-8")).hexdigest()


def _trace_rel(path: str, root: str) -> Optional[str]:
    if not path.startswith(root):
        return None
    rel = path[len(root):]
    if rel.startswith(_TRACE_SKIP_PREFIXES) or "/__pycache__/" in f"/{rel}" or rel in TRACE_TOOL_FILES:
        return None
    return rel


def trace_record(trace_dir: Path, repo: Path) -> Optional[Dict[str, object]]:
    """彙整該次呼叫各行程之讀取記錄；不可沿用之情形回 None（見上方說明）。"""
    recs = []
    for p in sorted(Path(trace_dir).glob("*.json")) if Path(trace_dir).is_dir() else []:
        try:
            recs.append(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            return None
    if not recs or any(not r.get("complete") or r.get("untraced") or r.get("errors") for r in recs):
        return None
    root = str(Path(repo).resolve()) + os.sep
    files = {rel for r in recs for p in r.get("files", []) if (rel := _trace_rel(p, root)) is not None}
    dirs = {rel for r in recs for p in r.get("dirs", []) if (rel := _trace_rel(p, root)) is not None}
    return {"files": {rel: _path_state(Path(repo) / rel) for rel in sorted(files)},
            "dirs": {rel: _listing_state(Path(repo) / rel) for rel in sorted(dirs)},
            "venv": venv_fingerprint(repo), "tool": _trace_tool_hash(repo), "processes": len(recs)}


# r69（GROK-R69-P0-01、CODEX-R69-P1-01、GROK-R69-P1-02）：C 層 I/O（h5py／polars／pyarrow 等）之讀取不經 Python open、
# 不入 trace ⇒ 沿用改以「呼叫開始時之內容快照 vs 目前」之改動路徑判定：改動須全數屬「未讀之文字類檔」方得沿用；
# 資料類副檔名、DATA_INPUTS、pytest 設定類檔、測試相關目錄增刪之 .py 一律失效（偏多跑）。
DATA_SUFFIXES = (".h5", ".hdf5", ".parquet", ".arrow", ".feather", ".npy", ".npz", ".pkl", ".pickle", ".csv", ".tsv",
                 ".db", ".sqlite", ".zip", ".gz", ".bz2", ".xz", ".bin", ".joblib", ".nc", ".zarr")
CONFIG_NAMES = frozenset({"conftest.py", "pytest.ini", "setup.cfg", "tox.ini", "pyproject.toml", "sitecustomize.py",
                          "usercustomize.py"})


# r70：被 git 忽略之資料類檔（如 data_cache/kline_cache.h5 經 h5py 讀取）不在已追蹤集合、C 層讀取亦不入 trace ⇒ 全數入快照
IGNORED_DATA_SUFFIXES = DATA_SUFFIXES + (".json",)
IGNORED_SKIP_PREFIXES = ("venv/", ".git/", "handoffs/", ".testreg/", ".claude/", ".agent_logs/", ".ruff_cache/",
                         ".pytest_cache/", ".codex/", ".gstack/", ".antigravitycli/", "node_modules/",
                         "frontend/node_modules/")


def snapshot_map(repo: Path) -> Dict[str, str]:
    """內容快照：已追蹤（工作樹內容；不存在＝<missing>）＋未追蹤未忽略檔（皆扣 FP_EXCLUDES）＋ DATA_INPUTS（鍵 data:<路徑>）
    ＋被忽略之資料類檔（IGNORED_DATA_SUFFIXES；扣工具／日誌目錄與 __pycache__；鍵 ign:<路徑>；內容 sha256，實測約 1.3 GB／1.3 秒）。"""
    rels = set(_git(repo, "ls-files", "--", ".", *FP_EXCLUDES).splitlines())
    rels |= set(_git(repo, "ls-files", "--others", "--exclude-standard", "--", ".", *FP_EXCLUDES).splitlines())
    out = {rel: _path_state(Path(repo) / rel) for rel in sorted(p for p in rels if p)}
    for rel in DATA_INPUTS:
        out[f"data:{rel}"] = _path_state(Path(repo) / rel)
    ignored = _git(repo, "ls-files", "--others", "--ignored", "--exclude-standard", "--", ".").splitlines()
    for rel in sorted(p for p in ignored if p.endswith(IGNORED_DATA_SUFFIXES) and not p.startswith(IGNORED_SKIP_PREFIXES)
                      and "/__pycache__/" not in f"/{p}" and f"data:{p}" not in out):
        # 二進位資料類（C 層讀取可能）以 ign: 鍵 ⇒ 改動一律失效；.json 由 Python 讀取必入 trace ⇒ 以原路徑為鍵，讀過才失效
        st = _path_state(Path(repo) / rel)
        if rel.endswith(DATA_SUFFIXES):
            out[f"ign:{rel}"] = st
        else:  # .json：原路徑鍵（文字類）＋ ignt: 鍵（供無 trace 結果綁定，D18 審查 r73）
            out[rel] = st
            out[f"ignt:{rel}"] = st
    return out


def _parent(p: str) -> str:
    return p.rsplit("/", 1)[0] if "/" in p else ""


def changes_reusable(then: Mapping[str, str], now: Mapping[str, str], rec: Mapping[str, object], test_file: str) -> bool:
    """純函式：快照之間之改動路徑全數可忽略（未讀之文字類檔）⇒ True；見上方規則。"""
    read = set(dict(rec.get("files") or {}))
    listed = set(dict(rec.get("dirs") or {}))
    read_dirs = {_parent(p) for p in read}
    near, d = {""}, _parent(test_file)  # 測試檔所在目錄及其各上層（conftest／套件探索之範圍）
    while d:
        near.add(d)
        d = _parent(d)
    for key in set(then) | set(now):
        if then.get(key) == now.get(key):
            continue
        p = key[len("ignt:"):] if key.startswith("ignt:") else key  # 被忽略之 .json：文字類，以原路徑比對讀取
        name = p.rsplit("/", 1)[-1]
        if (key.startswith(("data:", "ign:")) or p in read or p.endswith(DATA_SUFFIXES) or name in CONFIG_NAMES
                or name.endswith(".pth") or _parent(p) in listed):
            return False
        if (key in then) != (key in now) and p.endswith(".py") and (_parent(p) in read_dirs or _parent(p) in near):
            return False
    return True


UNTRACED_BOUND_PREFIXES = ("data:", "ign:", "ignt:")


def untraced_inputs_unchanged(then: Mapping[str, str], now: Mapping[str, str]) -> bool:
    """純函式（D18，審查 r73）：無 trace 之結果（D15 沿用、D18 還原）不知實際讀取 ⇒ 被 git 忽略之資料（DATA_INPUTS、
    被忽略之二進位資料類與 .json）任一自快照後改動即不得沿用（已追蹤檔與未追蹤未忽略檔由 state_key 綁定）。"""
    keys = {k for k in set(then) | set(now) if k.startswith(UNTRACED_BOUND_PREFIXES)}
    return all(then.get(k) == now.get(k) for k in keys)


def trace_valid(rec: Mapping[str, object], repo: Path) -> bool:
    """trace 中每項於目前狀態皆不變（檔內容、目錄項目、venv 套件、記錄工具）。"""
    try:
        return (all(_path_state(Path(repo) / rel) == st for rel, st in dict(rec["files"]).items())
                and all(_listing_state(Path(repo) / rel) == st for rel, st in dict(rec["dirs"]).items())
                and rec["venv"] == venv_fingerprint(repo) and rec["tool"] == _trace_tool_hash(repo))
    except (KeyError, TypeError, ValueError, OSError):
        return False


def env_fingerprint(env: Mapping[str, str]) -> str:
    """有效執行環境（審查 r48）：影響生成／測試之環境變數前綴之鍵值、Python 執行檔與版本。"""
    keys = sorted(k for k in env if k.startswith(ENV_PREFIXES))
    return json.dumps({"env": {k: env[k] for k in keys}, "python": sys.executable, "version": sys.version},
                      sort_keys=True, ensure_ascii=False)


# 指紋排除集合（實作期 b1；審查 r58）：已追蹤 numba 快取（任一測試執行即改寫）、`handoffs/`（收據與交接）、
# collect-only 時 `tests/conftest.py` 改寫之已追蹤清冊（生成物）——皆非測試輸入
GENERATED_TRACKED = ("tests/golden/l65/test_inventory.txt",)
FP_EXCLUDES = (":(exclude,glob)**/__pycache__/**", ":(exclude,glob)handoffs/**",
               *(f":(exclude){p}" for p in GENERATED_TRACKED))


# 被 git 忽略、但測試讀取之資料輸入（審查 r60）：內容入指紋
DATA_INPUTS = ("data_cache/feature_klines/kline_cache.h5",)

# SPEC v25 D14：大機器專用測試登記（RM-FULLSCALE）；機器實體記憶體低於 min_memory_gib 之檔不選入
HARDWARE_REQUIREMENTS_REL = "tests/hardware_requirements.json"
_GIB = 1 << 30


def machine_memory_bytes() -> int:
    """本機實體記憶體位元組（POSIX sysconf；darwin 與 linux 皆可用）。"""
    return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))


def load_hardware_requirements(repo: Path) -> List[Dict[str, object]]:
    """讀並驗大機器專用測試登記；格式不符、路徑非既有 tests/ 下 test_*.py、ticket 非 RM-FULLSCALE、需求非正整數或
    路徑重複 ⇒ GateError（fail-closed）。檔案不存在 ⇒ 空清單（不排除任何檔＝全照常選入，偏多跑之安全方向）。"""
    p = Path(repo) / HARDWARE_REQUIREMENTS_REL
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise GateError(f"{HARDWARE_REQUIREMENTS_REL} 非合法 JSON：{exc}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise GateError(f"{HARDWARE_REQUIREMENTS_REL} 缺 entries 清單")
    seen: set = set()
    for e in entries:
        path = e.get("path") if isinstance(e, dict) else None
        mem = e.get("min_memory_gib") if isinstance(e, dict) else None
        ok = (isinstance(path, str) and re.fullmatch(r"tests/(?:[\w.-]+/)*test_[\w-]+\.py", path)
              and (Path(repo) / path).is_file() and e.get("ticket") == "RM-FULLSCALE"
              and isinstance(mem, int) and not isinstance(mem, bool) and mem > 0
              and isinstance(e.get("reason"), str) and e["reason"].strip() and path not in seen)
        if not ok:
            raise GateError(f"{HARDWARE_REQUIREMENTS_REL} 條目不合格式：{e!r}")
        seen.add(path)
    return entries


def hardware_blocked(entries: Sequence[Mapping[str, object]], memory_bytes: int) -> Dict[str, Dict[str, object]]:
    """純函式：機器記憶體低於需求之登記檔 → {path: {ticket, item, min_memory_gib, machine_memory_gib}}；達標者不列。"""
    return {str(e["path"]): {"ticket": e["ticket"], "item": e.get("item"), "min_memory_gib": e["min_memory_gib"],
                             "machine_memory_gib": round(memory_bytes / _GIB, 1)}
            for e in entries if memory_bytes < int(e["min_memory_gib"]) * _GIB}


def _file_sha(p: Path) -> str:
    """檔案內容 sha256；每次實讀位元組（審查 r61：不以大小／mtime 快取——metadata 可被保留而內容已換）。"""
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def content_inputs(repo: Path, extra_excludes: Sequence[str] = ()) -> str:
    """未追蹤檔（排除 FP_EXCLUDES 與 extra_excludes〔pathspec〕）之路徑＋內容雜湊，及 DATA_INPUTS 之內容雜湊（審查
    r60：路徑未變不等於內容未變）。"""
    rows = []
    for rel in sorted(p for p in _git(repo, "ls-files", "--others", "--exclude-standard", "--", ".",
                                      *FP_EXCLUDES, *extra_excludes).splitlines() if p):
        f = repo / rel
        rows.append(f"{rel}\t{_file_sha(f) if f.is_file() else '<non-file>'}")
    for rel in DATA_INPUTS:
        f = repo / rel
        rows.append(f"data:{rel}\t{_file_sha(f) if f.is_file() else '<missing>'}")
    return "\n".join(rows)


def tree_identity(repo: Path) -> str:
    """HEAD 之檔案樹身分（排除 FP_EXCLUDES）：以路徑＋blob 雜湊取代提交編號——只改排除路徑之提交（如交接）不改身分，
    任何輸入檔之提交仍改（審查 r58）。"""
    lines = _git(repo, "ls-tree", "-r", "HEAD").splitlines()  # ls-tree 不支援 pathspec magic，改於此過濾
    return "\n".join(ln for ln in lines if not _fp_excluded(ln.split("\t", 1)[-1]))


def _fp_excluded(path: str) -> bool:
    return "/__pycache__/" in f"/{path}" or path.startswith("handoffs/") or path in GENERATED_TRACKED


def restore_generated(repo: Path) -> None:
    """把 collect-only 生成之已追蹤清冊還原為 HEAD 版本（每次 pytest 呼叫前；處置驗證器 ⑦ 不因生成物而紅）。"""
    for rel in GENERATED_TRACKED:
        blob = subprocess.run(["git", "-C", str(repo), "show", f"HEAD:{rel}"], capture_output=True)
        p = repo / rel
        if blob.returncode == 0 and (not p.is_file() or p.read_bytes() != blob.stdout):
            p.write_bytes(blob.stdout)


def state_key(repo: Path, test_file: str, phase: int, env: Optional[Mapping[str, str]] = None) -> str:
    """結果檔沿用之狀態指紋：HEAD 檔案樹身分、相對 HEAD 之完整 diff、未追蹤檔路徑＋內容與資料輸入內容（content_inputs）、測試檔內容、pytest 參數、phase、
    有效環境；皆排除 FP_EXCLUDES——否則中斷後接續永遠無法沿用（實作期 b1；審查 r58）。"""
    h = hashlib.sha256()
    skip = FP_EXCLUDES
    for part in (
        tree_identity(repo),
        _git(repo, "diff", "--binary", "HEAD", "--", ".", *skip),
        content_inputs(repo),  # 審查 r60：未追蹤檔路徑＋內容與資料輸入內容
        (repo / test_file).read_bytes().decode("utf-8", "replace") if (repo / test_file).is_file() else "",
        json.dumps(PYTEST_FLAGS), str(phase), env_fingerprint(env if env is not None else os.environ),
    ):
        h.update(part.encode("utf-8", "replace"))
        h.update(b"\0")
    return h.hexdigest()


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} rc={proc.returncode}：{proc.stderr[-300:]}")
    return proc.stdout


_SCRIPTS_DIR = Path(__file__).resolve().parent
_WATCHDOG_PATH = _SCRIPTS_DIR.parent / "handoffs" / "run_receipts" / "numview_probes" / "_watchdog.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _wd():
    return sys.modules.get("framepath_gate_watchdog") or _load_module("framepath_gate_watchdog", _WATCHDOG_PATH)


def watchdog_config():
    """共用監看設定（判準檔 `cell_rules.watchdog`，與 `scripts/run_watched.py` 同源；NOCAP Task 2.1）。"""
    rw = sys.modules.get("framepath_gate_run_watched") or _load_module("framepath_gate_run_watched",
                                                                         _SCRIPTS_DIR / "run_watched.py")
    return _wd().load_config(rw._criteria())


class Stalled(GateError):
    """pytest 子行程經共用監看判卡死（無 log 亦無 CPU 進度）：已留現場（堆疊檔）並終止整個子行程樹。"""


def run_watched(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> subprocess.CompletedProcess:
    """pytest 子行程一律經共用監看（NOCAP Task 2.1：不依牆鐘停止；卡死以無 log 亦無 CPU 進度判定、終止前留現場）。
    輸出（stdout＋stderr）寫入監看 log，回傳時讀回為 `stdout`；卡死 ⇒ `Stalled`（訊息含堆疊檔路徑）。"""
    runner = globals().get("_RUNNER")
    log_dir = Path(runner.out) / "watch_logs" if runner is not None else Path(tempfile.mkdtemp(prefix="gate-watch-"))
    log_dir.mkdir(parents=True, exist_ok=True)
    fd, log_name = tempfile.mkstemp(prefix="pytest-", suffix=".log", dir=str(log_dir))
    os.close(fd)  # 只取唯一檔名；監看器自行以路徑開檔（不關則每次呼叫洩漏一個 fd；b3 審碼 r1 CODEX-R1-P1-03）
    log = Path(log_name)
    cmd = [sys.executable, "-m", "pytest", *args]
    wd = _wd()
    res = wd.run_watched(cmd, log_path=log, config=watchdog_config(), cwd=str(cwd), env=dict(env))
    out = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    if res.status != wd.EXITED:
        stacks = (res.diagnosis or {}).get("stacks_file") or f"{log}.stacks.txt"
        raise Stalled(f"pytest 子行程卡死（{res.reason}；原因 {res.cause}）：已留現場 {stacks} （log {log}；"
                      f"依堆疊查因修好再跑，不得直接重跑）")
    return subprocess.CompletedProcess(cmd, res.returncode, out, "")


_pytest = run_watched  # 舊名（testreg 等呼叫端沿用）


PYTEST_RC_NO_TESTS = 5  # pytest ExitCode.NO_TESTS_COLLECTED
NO_TESTS_MARKER = "no tests collected"


def is_empty_collect(rc: int, output: str) -> bool:
    """SPEC v22 D11.12：檔內無測試函式之測試檔＝rc 5 且輸出含「no tests collected」（兩者皆須成立）。"""
    return rc == PYTEST_RC_NO_TESTS and NO_TESTS_MARKER in output


class EmptyCollect(GateError):
    """SPEC v22 D11.12：檔內無測試函式（rc 5＋no tests collected）。屬 GateError ⇒ A 組直呼 `collect` 時仍 fail-closed；
    plan 經 `collect_or_empty` 捕捉後記入收據 `empty_collect`。"""


def collect_or_empty(test_file: str, cwd: Path, env: Mapping[str, str], empty_sink: List[str]) -> List[str]:
    """plan 之 B／C／清單外／impact 檔：D11.12 空檔回 [] 並記入 sink。`collect` 以模組屬性呼叫且維持三參數介面
    （審查 r63 實跑：TESTREG 凍結驗收以三參數替身替換 `collect`，四參數呼叫使其 10 項 TypeError）。"""
    try:
        return collect(test_file, cwd, env)
    except EmptyCollect:
        empty_sink.append(test_file)
        return []


def collect(test_file: str, cwd: Path, env: Mapping[str, str],
            empty_sink: Optional[List[str]] = None) -> List[str]:
    """單檔 collect-only → nodeid 清單。D11.12 空檔 ⇒ 給 `empty_sink` 時回 [] 並記入，未給 ⇒ EmptyCollect；其餘非 0
    rc／收集為空 ⇒ GateError（fail-closed）。plan 一律經 `collect_or_empty` 以三參數呼叫本函式。"""
    if empty_sink is not None:
        return collect_or_empty(test_file, cwd, env, empty_sink)
    # 諮詢 r5 CODEX-R5-P1-01：本專案 pytest.ini 下 `-q` 輸出表頭與 `<Function …>`，`-qq` 才逐行輸出 nodeid
    # 審查 r59：collect 前後亦寫 progress.json（挑選與 A 組收集階段可監看）；NOCAP Task 2.1：不設牆鐘，經共用監看
    # 判卡死（無 log 亦無 CPU 進度）並留現場後具名停下
    runner = globals().get("_RUNNER")
    if runner is not None:
        runner.progress("collect", test_file, [])
    # 逐行 nodeid 之輸出所需 verbosity 依 pytest.ini 之 addopts 而異（本 repo 含 -v ⇒ -qq；無 -v 之倉 ⇒ -q；原 testreg
    # `_subbatch_collect` 之相容邏輯併入此處，兩入口共用同一實作；NOCAP Task 2.1）
    for q in ("-qq", "-q"):
        try:
            proc = run_watched(["--collect-only", q, "-p", "no:cacheprovider", test_file], cwd, env)
        except Stalled as exc:
            restore_generated(cwd)
            if runner is not None:
                runner.progress("collect", test_file, [], state="collect-stalled")
            raise GateError(f"{test_file} collect 卡死（匯入或收集無進度）：{exc}") from exc
        restore_generated(cwd)  # 審查 r58：collect-only 會改寫已追蹤清冊（tests/conftest.py），立即還原
        ids = [ln.strip() for ln in proc.stdout.splitlines() if ln.startswith(test_file + "::")]
        if ids and proc.returncode == 0:
            break
        if not ids and is_empty_collect(proc.returncode, proc.stdout + proc.stderr):
            break
    if runner is not None:
        runner.progress("collect", test_file, [], state="finished-call")
    if not ids and is_empty_collect(proc.returncode, proc.stdout + proc.stderr):
        raise EmptyCollect(f"{test_file} 無測試函式（rc={proc.returncode}、{NO_TESTS_MARKER}）")
    if proc.returncode != 0 or not ids:
        raise GateError(f"{test_file} 收集失敗或為空 rc={proc.returncode}：{proc.stdout[-500:]}{proc.stderr[-500:]}")
    return ids


def run_file(test_file: str, xml_path: Path, cwd: Path, env: Mapping[str, str],
             nodeids: Optional[Sequence[str]] = None, extra: Sequence[str] = ()) -> Tuple[int, Dict[str, Dict[str, str]]]:
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    if xml_path.exists():
        xml_path.unlink()
    try:
        proc = run_watched([*PYTEST_FLAGS, *extra, f"--junitxml={xml_path}", *(nodeids or [test_file])], cwd, env)
    except Stalled as exc:
        raise GateError(f"{test_file} 執行卡死（測試無進度）：{exc}") from exc
    res = junit_results(xml_path.read_text(encoding="utf-8"), test_file) if xml_path.is_file() else {}
    return proc.returncode, res


class Paused(Exception):
    """已達本段時間預算：於兩次 pytest 呼叫之間正常停下（已完成之結果檔保留，下次以同一命令接續）。"""


class Runner:
    """逐次 pytest 呼叫之執行器（實作期 b1；使用者 2026-10-10「不要莫名被什麼時間上限砍掉，然後又重來」「卡住沒動或
    跑太久也不知道也不允許」）：①同狀態指紋之結果檔沿用（中斷後接續不重跑）②已用時間逾 `max_seconds` 即不再開新呼叫、
    丟 `Paused`（停在呼叫之間，不砍進行中之測試）③每次呼叫前後寫 `<out>/progress.json`（目前檔／nodeid、開始時刻、
    已完成數、行程 pid），供外部監看判斷是否卡住。"""

    def __init__(self, out: Path, max_seconds: Optional[float], total: int, ledger_dir: Optional[Path] = None):
        self.out, self.max_seconds, self.total = out, max_seconds, total
        self.start = time.monotonic()
        self.done = 0
        # TESTREG Task 2.3：每檔最近一次（非錨點）呼叫前之 ledger 檔名集合，供 current_failures 取本次呼叫之 session
        self.ledger_dir = Path(ledger_dir) if ledger_dir is not None else None
        self.ledger_snapshots: Dict[str, set] = {}

    def _ledger_names(self) -> set:
        d = self.ledger_dir
        return {p.name for p in d.glob("*.jsonl")} if d is not None and d.is_dir() else set()

    def _check_budget(self) -> None:
        """分段上限只在使用者明示時生效（使用者自設之預算，登記 B；NOCAP Task 2.1：預設 None 不分段）。"""
        if self.max_seconds is not None and time.monotonic() - self.start > self.max_seconds:
            raise Paused(f"本段已用 {round(time.monotonic() - self.start)} 秒 ≥ {self.max_seconds}")

    def progress(self, phase: str, test_file: str, nodeids: Sequence[str], state: str = "running") -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "progress.json").write_text(json.dumps({
            "state": state, "phase": phase, "file": test_file, "nodeids": list(nodeids)[:5], "n_nodeids": len(nodeids),
            "done": self.done, "total": self.total, "pid": os.getpid(), "updated_at": time.time(),
            "segment_elapsed": round(time.monotonic() - self.start, 1)}, ensure_ascii=False), encoding="utf-8")

    def _snapshot_path(self, ref: str) -> Path:
        return self.out / "snapshots" / f"{ref}.json"

    def reusable(self, m: Mapping[str, object], key: str, call_id: Optional[str], cwd: Path, test_file: str) -> bool:
        """SPEC v25 D16（r69 修正）：meta 帶 trace ⇒ trace 必須仍有效，且（state_key 相同，或 call_id 相同且呼叫開始時
        快照至今之改動全數可忽略〔changes_reusable〕）；meta 無 trace（未記錄、未完成、untraced）⇒ 只依 state_key。"""
        rec = m.get("trace")
        if not isinstance(rec, dict):
            if m.get("state_key") != key:
                return False
            if not (m.get("recovered_from") or m.get("carried_over")):
                return True
            # D18（審查 r73）：沿用／還原之結果另須被忽略之資料自寫入當下快照後未變（缺快照 ⇒ 不沿用）
            snap = self._snapshot_path(str(m.get("snapshot") or ""))
            if not m.get("snapshot") or not snap.is_file():
                return False
            try:
                then = json.loads(snap.read_text(encoding="utf-8"))
            except ValueError:
                return False
            return untraced_inputs_unchanged(then, snapshot_map(cwd))
        if not trace_valid(rec, cwd):
            return False
        if m.get("state_key") == key:
            return True
        snap = self._snapshot_path(str(m.get("snapshot") or ""))
        if call_id is None or m.get("call_id") != call_id or not m.get("snapshot") or not snap.is_file():
            return False
        try:
            then = json.loads(snap.read_text(encoding="utf-8"))
        except ValueError:
            return False
        return changes_reusable(then, snapshot_map(cwd), rec, test_file)

    def run(self, test_file: str, xml: Path, cwd: Path, env: Mapping[str, str], nodeids: Optional[Sequence[str]],
            extra: Sequence[str], key: str, count_ids: Sequence[str], phase: str = "BC",
            probe_dir: Optional[Path] = None, trace_dir: Optional[Path] = None,
            call_id: Optional[str] = None) -> Tuple[int, Dict[str, Dict[str, str]]]:
        meta = xml.with_suffix(".meta.json")
        if xml.is_file() and meta.is_file():
            # 審查 r57：結果檔或 meta 損毀（中斷於寫入中）一律視為未命中、重跑該呼叫，不得使接續崩潰
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                res = junit_results(xml.read_text(encoding="utf-8"), test_file) \
                    if isinstance(m, dict) and m.get("rc") in RUN_RC_OK and self.reusable(m, key, call_id, cwd, test_file) \
                    else None
            except (ValueError, ET.ParseError, OSError):
                res = None
            if res is not None and not set(count_ids) - set(res):
                self.done += len(count_ids)
                if phase != "anchor" and self.ledger_dir is not None:
                    # 沿用之結果：其呼叫所產之 session 記於 meta（ledger_new），視為本次之「呼叫後新增」
                    self.ledger_snapshots[test_file] = self._ledger_names() - set(m.get("ledger_new") or [])
                return m["rc"], res
        self._check_budget()
        if probe_dir is not None:
            probe_dir.mkdir(parents=True, exist_ok=True)
            for stale in probe_dir.glob("*.json"):
                stale.unlink()
        if trace_dir is not None:
            trace_dir.mkdir(parents=True, exist_ok=True)
            for stale in trace_dir.glob("*.json*"):
                stale.unlink()
        restore_generated(cwd)  # 審查 r58／r59：本次呼叫之工作樹（主或錨點）之清冊先還原
        snap_ref = None
        if trace_dir is not None:  # SPEC v25 D16（r69）：呼叫開始時之內容快照，供日後判定改動是否可忽略
            snap = json.dumps(snapshot_map(cwd), sort_keys=True, ensure_ascii=False)
            snap_ref = hashlib.sha256(snap.encode("utf-8")).hexdigest()
            sp = self._snapshot_path(snap_ref)
            if not sp.is_file():
                sp.parent.mkdir(parents=True, exist_ok=True)
                sp.with_suffix(".tmp").write_text(snap, encoding="utf-8")
                os.replace(sp.with_suffix(".tmp"), sp)
        self.progress(phase, test_file, count_ids)
        t0 = time.monotonic()
        if meta.exists():
            meta.unlink()  # 先撤舊 meta：本次呼叫中斷時不得留下與新結果檔不符之舊 meta
        before = self._ledger_names()
        if phase != "anchor" and self.ledger_dir is not None:
            self.ledger_snapshots[test_file] = before  # 錨點呼叫不記、不覆寫（其恆在 B／C 呼叫之後）
        rc, res = run_file(test_file, xml, cwd, env, nodeids, extra)
        tmp = meta.with_suffix(".tmp")
        tmp.write_text(json.dumps({"state_key": key, "rc": rc, "file": test_file,
                                   "seconds": round(time.monotonic() - t0, 1),
                                   "ledger_new": sorted(self._ledger_names() - before),
                                   "call_id": call_id, "snapshot": snap_ref,  # SPEC v25 D16
                                   "trace": trace_record(trace_dir, cwd) if trace_dir is not None else None}),
                       encoding="utf-8")
        os.replace(tmp, meta)  # 審查 r57：原子替換
        self.done += len(count_ids)
        self.progress(phase, test_file, count_ids, state="finished-call")
        return rc, res


def resolve_anchor() -> str:
    """本票最晚一筆實作許可之 round_start_head（與處置驗證器 ⓪ 同一函式）。"""
    from tests.feature_engineering.test_framepath_disposition import AUDIT_REL, approval_anchor

    anchor = approval_anchor((REPO / AUDIT_REL).read_text(encoding="utf-8", errors="replace").splitlines())
    if not anchor:
        raise GateError("審計紀錄無本票實作許可（impl_token_issued）")
    return anchor


def _benign_status(line: str) -> bool:
    """錨點工作樹乾淨判定之封閉豁免：本腳本建立之 `data_cache` symlink（未追蹤），與已追蹤之 `__pycache__/` 位元組碼／
    numba 快取（任一測試執行即改寫；同處置驗證器⑤⑦之過濾）。其餘任何改動或未追蹤檔皆不乾淨。"""
    path = line[3:]
    return line == "?? data_cache" or "/__pycache__/" in path


def verify_anchor_worktree(wt: Path, anchor: str) -> None:
    """錨點工作樹：HEAD＝錨點（本票最晚一筆實作許可之 round_start_head）、工作樹乾淨（無追蹤檔改動、無未追蹤檔）、
    被忽略之實體輸入不存在。SPEC v23 D12.1：錨點之碼態即「本批動工前之碼態」，由許可錨點本身界定，不再比對寫死之
    6e07e0ad（b2 起許可錨點已含 b1 生產碼改動；b1 之等值性已由 b1 許可錨點之 HEAD 條件涵蓋）。"""
    head = _git(wt, "rev-parse", "HEAD").strip()
    if head != anchor:
        raise GateError(f"錨點工作樹 HEAD {head[:8]} ≠ 本票實作許可錨點 {anchor[:8]}")
    dirty = [ln for ln in _git(wt, "status", "--porcelain").splitlines() if ln.strip() and not _benign_status(ln)]
    if dirty:
        raise GateError(f"錨點工作樹不乾淨：{dirty[:10]}")
    # 審查 r48：被 git 忽略之實體輸入（實體 data_cache 等）不得存在；data_cache 只准指向主工作樹之 symlink 或不存在
    dc = wt / "data_cache"
    if dc.exists() or dc.is_symlink():
        if not (dc.is_symlink() and dc.resolve() == (REPO / "data_cache").resolve()):
            raise GateError(f"錨點工作樹之 data_cache 須為指向 {REPO / 'data_cache'} 之 symlink：{dc}")
    ignored = [ln[3:] for ln in _git(wt, "status", "--porcelain", "--ignored").splitlines()
               if ln.startswith("!! ") and not _benign_ignored(ln[3:])]
    if ignored:
        raise GateError(f"錨點工作樹含被忽略之檔：{ignored[:10]}")


def _benign_ignored(path: str) -> bool:
    """錨點工作樹之被忽略檔封閉豁免：位元組碼與 numba 快取（`__pycache__/`、`.pyc`）。"""
    return "__pycache__/" in path or path.endswith(".pyc")


def make_anchor_worktree(anchor: str, wt: Optional[Path] = None) -> Path:
    """錨點工作樹：指定路徑已存在則沿用（接續時同一棵；仍由 `verify_anchor_worktree` 核驗），否則新建。"""
    wt = wt or Path(tempfile.mkdtemp(prefix="framepath_anchor_")) / "wt"
    if not wt.exists():
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", str(wt), anchor], check=True,
                       capture_output=True)
    return wt


# ── SPEC v21 D8（諮詢 r5）：應跑集合 E＝A∪S1∪S2∪S3∪必跑；其餘逐項收據 ─────────────────────────────────────────
FFACT_KEY = "FFACT_USE_CGSA"
_TRUTHY = frozenset({"1", "true", "yes", "on"})
ALIGN_TRIGGER_FILES = frozenset({"momentum/FeatureEngineering/timeframe/tf_aligner.py"})
ALIGN_TRIGGER_SYMBOLS = frozenset({"TimeframeAligner", "build_asof_index_map", "_align_group_array",
                                   "_capture_multi_tf_alignment"})
ALIGN_TEST_NAMES = frozenset({"TimeframeAligner", "build_asof_index_map", "FFACT_MULTI_TF_COMPACT_ALIGNMENT",
                              "_capture_multi_tf_alignment"})
HEAVY_NAMES = frozenset({"requires_kline", "requires_kline_data", "FEATURE_KLINE_H5_PATH", "generate_features",
                         "generate_multi_tf", "run_stat", "run_generation", "generate_cell", "run_ic_first",
                         "kline_close"})
HEAVY_SUBSTRINGS = ("kline_cache",)
SKIP_REASONS = ("invariance_envelope", "align_static_proof")
INVARIANCE_BASELINE_REL = "tests/_golden/framepath/cgsa_fingerprint.json"
DISPOSITION_REL = "tests/_golden/framepath/test_disposition.json"


def _is_keyconst(node: Optional[ast.AST]) -> bool:
    return isinstance(node, ast.Constant) and node.value == FFACT_KEY


def _is_truthy(node: Optional[ast.AST]) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip().lower() in _TRUTHY


def ffact_unproven(node: ast.AST) -> bool:
    """節點內出現 `FFACT_USE_CGSA`（字串常數或關鍵字引數）且並非每一處皆可證為真值常數 ⇒ True（fail-closed：
    值經變數、CondExp、dict 展開、delenv 等無法靜態決定者一律視為可能走 frame）。"""
    total = proven = 0
    for n in ast.walk(node):
        if _is_keyconst(n):
            total += 1
        if isinstance(n, ast.keyword) and n.arg == FFACT_KEY:
            total += 1
            proven += _is_truthy(n.value)
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "setenv"
                and len(n.args) > 1 and _is_keyconst(n.args[0])):
            proven += _is_truthy(n.args[1])
        if isinstance(n, ast.Dict):
            # 審查 r53：其後有 `**展開`（keys 中之 None）者可覆寫該鍵 ⇒ 不得計為已證真值
            keys = list(n.keys)
            proven += sum(1 for i, (k, v) in enumerate(zip(keys, n.values))
                          if _is_keyconst(k) and _is_truthy(v) and None not in keys[i + 1:])
        if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript)
                and _is_keyconst(_slice(n.targets[0]))):
            proven += _is_truthy(n.value)
    return total > proven


def _slice(node: ast.Subscript) -> ast.AST:
    sl = node.slice
    return sl.value if isinstance(sl, ast.Index) else sl  # type: ignore[attr-defined]  # python<3.9


def refs_of(node: ast.AST) -> set:
    """節點引用之名稱：Name、Attribute 屬性名、字串常數（setattr 以字串指名者）、參數名（fixture）、關鍵字名。"""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.add(n.value)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.keyword) and n.arg:
            out.add(n.arg)
    return out


def _defs(tree: ast.Module) -> Dict[str, ast.AST]:
    """頂層函式／類別與類別方法 → {qualname: node}（類別本身亦列，方法為 `Cls.meth`）。"""
    out: Dict[str, ast.AST] = {}
    for st in tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[st.name] = st
        elif isinstance(st, ast.ClassDef):
            out[st.name] = st
            for m in st.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{st.name}.{m.name}"] = m
    return out


def _module_path(dotted: str, level: int, here: str, source_of) -> Optional[str]:
    """測試輔助模組之 repo 相對路徑（只解析 tests/ 下且來源存在者；第三方與生產模組回 None）。"""
    if level:
        base = Path(here).parent
        for _ in range(level - 1):
            base = base.parent
        parts = [*base.parts, *(dotted.split(".") if dotted else [])]
    else:
        parts = dotted.split(".")
    if not parts or parts[0] != "tests":
        return None
    for cand in ("/".join(parts) + ".py", "/".join(parts) + "/__init__.py"):
        if source_of(cand) is not None:
            return cand
    return None


def module_taint(path: str, source_of, symbols: frozenset, _cache: Optional[dict] = None,
                 _stack: Tuple[str, ...] = (), ffact: bool = True, substrings: Tuple[str, ...] = ()) -> Dict[str, set]:
    """S2：模組內各定義（含 fixture）之 taint 理由——直接（`ffact`／`sym:<名>`）、經模組層名稱（`name:<名>`）、
    經同模組或 tests/ 下輔助模組之被 taint 定義（`call:<模組>:<名>`）傳遞，至不動點。conftest 由呼叫端併入。"""
    cache = _cache if _cache is not None else {}
    graph = cache.setdefault(("__taint_graph__", ffact, tuple(substrings), symbols), _TaintGraph(
        source_of, symbols, ffact, tuple(substrings)))
    return graph.reasons_of(path)


def _tainted_names(reasons: Mapping[str, set]) -> Dict[str, str]:
    """被 taint 定義之可引用名 → 限定名：末段名，以及方法所屬之類別名（審查 r53：經匯入類別再呼叫其方法者亦須傳遞）。"""
    out: Dict[str, str] = {}
    for q, r in reasons.items():
        if not r:
            continue
        parts = q.split(".")
        out.setdefault(parts[-1], q)
        if len(parts) > 1:
            out.setdefault(parts[0], q)
    return out


class _TaintGraph:
    """S2／重型判定之跨模組傳遞（審查 r52：循環引用不得以不完整結果入快取）。先載入 `path` 之 tests/ 匯入閉包
    （每模組只解析一次），再對全部已載入模組以「同模組定義、模組層名稱、匯入之輔助模組定義」三種邊做全域不動點
    迭代；結果與掃描順序無關。"""

    def __init__(self, source_of, symbols: frozenset, ffact: bool, substrings: Tuple[str, ...]):
        self.source_of, self.symbols, self.ffact, self.substrings = source_of, symbols, ffact, substrings
        self.mods: Dict[str, Dict[str, object]] = {}
        self.reasons: Dict[str, Dict[str, set]] = {}
        self._fresh: List[str] = []

    def _load(self, path: str) -> None:
        if path in self.mods:
            return
        src = self.source_of(path)
        if src is None:
            self.mods[path] = {"defs": {}, "refs": {}, "names": set(), "ext": {}}
            self.reasons[path] = {}
            return
        tree = ast.parse(src)
        defs = {q: n for q, n in _defs(tree).items() if not isinstance(n, ast.ClassDef)}
        refs = {q: refs_of(n) for q, n in defs.items()}
        reasons: Dict[str, set] = {q: set() for q in defs}
        for q, node in defs.items():
            if self.ffact and ffact_unproven(node):
                reasons[q].add("ffact")
            reasons[q] |= {f"sym:{s}" for s in refs[q] & self.symbols}
            reasons[q] |= {f"str:{s}" for s in self.substrings if any(s in r for r in refs[q])}
        names = set()
        for st in tree.body:
            targets = st.targets if isinstance(st, ast.Assign) else [st.target] if isinstance(st, ast.AnnAssign) else []
            value = getattr(st, "value", None)
            if value is None:
                continue
            vrefs = refs_of(value)
            if ((self.ffact and ffact_unproven(value)) or vrefs & self.symbols
                    or any(s in r for s in self.substrings for r in vrefs)):
                names |= {t.id for t in targets if isinstance(t, ast.Name)}
        ext: Dict[str, Tuple[str, str]] = {}  # 本地名 → (輔助模組路徑, 該模組中之名；"" 表整個模組)
        for st in ast.walk(tree):
            if isinstance(st, ast.Import):
                for a in st.names:
                    mp = _module_path(a.name, 0, path, self.source_of)
                    if mp:
                        ext[a.asname or a.name.split(".")[0]] = (mp, "")
            elif isinstance(st, ast.ImportFrom):
                for a in st.names:
                    sub = _module_path(f"{st.module}.{a.name}" if st.module else a.name, st.level, path, self.source_of)
                    if sub:
                        ext[a.asname or a.name] = (sub, "")
                        continue
                    mp = _module_path(st.module or "", st.level, path, self.source_of)
                    if mp:
                        ext[a.asname or a.name] = (mp, a.name)
        self.mods[path] = {"defs": defs, "refs": refs, "names": names, "ext": ext}
        self.reasons[path] = reasons
        self._fresh.append(path)
        for mp, _ in ext.values():
            self._load(mp)

    def _fixpoint(self, paths: Sequence[str]) -> None:
        """只迭代本次新載入者：既有模組之閉包已穩定，且不匯入新載入者（否則先前已一併載入）。"""
        changed = True
        while changed:
            changed = False
            for path in paths:
                mod = self.mods[path]
                reasons = self.reasons[path]
                live = _tainted_names(reasons)
                for q, refs in mod["refs"].items():
                    add = {f"name:{n}" for n in refs & mod["names"]}
                    add |= {f"call:{path}:{live[b]}" for b in refs & set(live) if live[b] != q}
                    for local, (mp, name) in mod["ext"].items():
                        if local not in refs:
                            continue
                        bad = set(_tainted_names(self.reasons.get(mp, {})))
                        hits = ({name} & bad) if name else (refs & bad)
                        add |= {f"call:{mp}:{h}" for h in hits}
                    if not add <= reasons[q]:
                        reasons[q] |= add
                        changed = True

    def reasons_of(self, path: str) -> Dict[str, set]:
        if path not in self.mods:
            self._fresh: List[str] = []
            self._load(path)
            self._fixpoint(self._fresh)
        return self.reasons[path]


def _conftests(test_file: str, source_of) -> List[str]:
    parts = Path(test_file).parts[:-1]
    out = []
    for i in range(1, len(parts) + 1):
        cand = "/".join(parts[:i]) + "/conftest.py"
        if source_of(cand) is not None:
            out.append(cand)
    return out


def file_scan(test_file: str, source_of, symbols: frozenset, cache: Optional[dict] = None,
              heavy_cache: Optional[dict] = None, want_heavy: bool = True) -> Dict[str, object]:
    """單一測試檔之 {"refs": {qualname: 名稱集}, "taint": {qualname: 理由集}, "heavy": bool}；fixture 引用
    conftest 之被 taint fixture 亦傳遞。`cache`／`heavy_cache` 可於同一 source_of 與符號表之多檔掃描間共用（輔助模組
    只解析一次）；`want_heavy=False` 時 heavy 恆 True（不計算，只供不得整檔之清單外檔）。"""
    src = source_of(test_file)
    if src is None:
        return {"refs": {}, "taint": {}, "heavy": False}
    tree = ast.parse(src)
    defs = _defs(tree)
    refs = {q: refs_of(n) for q, n in defs.items()}
    cache = {} if cache is None else cache
    taint = {q: set(r) for q, r in module_taint(test_file, source_of, symbols, cache).items()}
    for cf in _conftests(test_file, source_of):
        bad = set(_tainted_names(module_taint(cf, source_of, symbols, cache)))
        for q in defs:
            hits = refs[q] & bad
            if hits:
                taint.setdefault(q, set()).update(f"call:{cf}:{h}" for h in hits)
    heavy = is_heavy(test_file, source_of, heavy_cache) if want_heavy else True
    return {"refs": refs, "taint": {q: r for q, r in taint.items() if r}, "heavy": heavy}


def is_heavy(test_file: str, source_of, cache: Optional[dict] = None) -> bool:
    """重型（不得 S3 整檔）：檔內或其經 tests/ 輔助模組（含 conftest）傳遞之定義引用 `HEAVY_NAMES`（真實 kline／
    生成入口），或其字串常數含 `kline_cache`——字串規則與符號規則同經輔助模組定義、模組層名稱與 conftest 傳遞
    （審查 r51：只呼叫內含 kline 路徑字面之 helper 者亦屬重型）。與 S2 同一傳遞分析（ffact 關閉）。"""
    src = source_of(test_file)
    if src is None:
        return True
    tree = ast.parse(src)
    module_refs = refs_of(tree)
    if module_refs & HEAVY_NAMES or any(s in r for s in HEAVY_SUBSTRINGS for r in module_refs):
        return True
    cache = {} if cache is None else cache
    if any(module_taint(test_file, source_of, HEAVY_NAMES, cache, ffact=False, substrings=HEAVY_SUBSTRINGS).values()):
        return True
    for cf in _conftests(test_file, source_of):
        bad = set(_tainted_names(module_taint(cf, source_of, HEAVY_NAMES, cache, ffact=False,
                                              substrings=HEAVY_SUBSTRINGS)))
        if module_refs & bad:
            return True
    return False


def nodeid_qualname(nodeid: str) -> str:
    """`path::Cls::test_x[p]` → `Cls.test_x`。"""
    parts = nodeid.split("::")[1:]
    if parts:
        parts[-1] = parts[-1].split("[", 1)[0]
    return ".".join(parts)


def s1_targets(disposition: Mapping, phase: int, scans: Mapping[str, Mapping]) -> Tuple[Dict[str, Dict[str, set]], Dict[str, set]]:
    """S1：處置表 phase≤N 之操作 → ({檔: {qualname: {OP-id}}}, {nodeid: {OP-id}})。locator 有 qualname 者取該函式；
    `target`（模組層 dict／序列）與 `import_alias` 取引用該名之函式；顯式 nodeids 與 rename 之 new_nodeid 另列
    （其所屬函式之其餘參數化 nodeid 亦選入）。空 nodeids 不等於「沒有測試」（CODEX-R5-P1-02）。"""
    funcs: Dict[str, Dict[str, set]] = {}
    nodes: Dict[str, set] = {}
    for op in disposition.get("operations", []):
        if int(op.get("phase", 99)) > phase:
            continue
        path, oid, loc = op["path"], op["id"], op.get("locator") or {}
        quals = set()
        if loc.get("qualname"):
            quals.add(loc["qualname"])
        name = loc.get("target") or (loc.get("name") if loc.get("category") == "import_alias" else None)
        if name:
            quals |= {q for q, r in scans.get(path, {}).get("refs", {}).items() if name in r}
        for nid in op.get("nodeids") or []:
            nodes.setdefault(nid, set()).add(oid)
            quals.add(nodeid_qualname(nid))
        for q in quals:
            funcs.setdefault(path, {}).setdefault(q, set()).add(oid)
    for row in disposition.get("nodeids", []):
        if row.get("disposition") == "rename" and int(row.get("phase", 99)) <= phase and row.get("new_nodeid"):
            nid = row["new_nodeid"]
            nodes.setdefault(nid, set()).add(row.get("op", "rename"))
            funcs.setdefault(nid.split("::", 1)[0], {}).setdefault(nodeid_qualname(nid), set()).add(row.get("op", "rename"))
    return funcs, nodes


def select_expected(collected: Mapping[str, Sequence[str]], scans: Mapping[str, Mapping],
                    s1_funcs: Mapping[str, Mapping[str, set]], s1_nodes: Mapping[str, set],
                    must: Sequence[str], heavy_pinned: Iterable[str], align_triggered: bool,
                    ) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """把 collected 之每個 nodeid 分入「選入（理由清單）」或「未跑（封閉理由）」——兩者互斥且聯集＝collected。
    S1＝處置操作所及函式；S2＝taint；S3＝靜態輕量檔（無 kline／生成呼叫且不在釘扎重型表）整檔；必跑＝manifest
    `affected_must`；對齊觸發時引用對齊名之函式選入，否則該等函式未跑理由為 `align_static_proof`。"""
    heavy_pinned = set(heavy_pinned)
    selected: Dict[str, List[str]] = {}
    skipped: Dict[str, str] = {}
    must_set = set(must)
    for f, ids in collected.items():
        scan = scans.get(f, {"refs": {}, "taint": {}, "heavy": True})
        light = not scan.get("heavy", True) and f not in heavy_pinned
        for nid in ids:
            q = nodeid_qualname(nid)
            why: List[str] = []
            if nid in must_set:
                why.append("must")
            if q in s1_funcs.get(f, {}) or nid in s1_nodes:
                why += sorted(f"S1:{o}" for o in s1_funcs.get(f, {}).get(q, set()) | s1_nodes.get(nid, set()))
            if q in scan.get("taint", {}):
                why += sorted(f"S2:{r}" for r in scan["taint"][q])
            if light:
                why.append("S3:light")
            aligned = bool(scan.get("refs", {}).get(q, set()) & ALIGN_TEST_NAMES)
            if aligned and align_triggered:
                why.append("align_trigger")
            if why:
                selected[nid] = why
            else:
                skipped[nid] = "align_static_proof" if aligned else "invariance_envelope"
    return selected, skipped


# ── CGSA 模式等價（審查 r51）：假設 CGSA 開啟且 registry 已建立，把錨點與工作樹之定義正規化後比對 ──────────────
def _is_enabled_call(n: ast.AST) -> bool:
    return (isinstance(n, ast.Call) and not n.args and not n.keywords
            and ((isinstance(n.func, ast.Attribute) and n.func.attr == "_cgsa_enabled")
                 or (isinstance(n.func, ast.Name) and n.func.id == "_cgsa_enabled")))


def _is_registry_expr(n: ast.AST) -> bool:
    if isinstance(n, ast.Attribute) and n.attr == "_cgsa_registry":
        return True
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2
            and isinstance(n.args[1], ast.Constant) and n.args[1].value == "_cgsa_registry")


def _is_guard_stmt(st: ast.stmt) -> bool:
    return (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute)
            and st.value.func.attr == "_require_cgsa_registry")


def _const_bool(n: ast.AST) -> bool:
    return isinstance(n, ast.Constant) and isinstance(n.value, bool)


class _CgsaFold(ast.NodeTransformer):
    """`*._cgsa_enabled()`→True；`<registry> is not None`→True、`is None`→False；not／and／or 常數折疊。"""

    def visit_Call(self, n: ast.Call) -> ast.AST:
        self.generic_visit(n)
        return ast.Constant(True) if _is_enabled_call(n) else n

    def visit_Compare(self, n: ast.Compare) -> ast.AST:
        self.generic_visit(n)
        if (len(n.ops) == 1 and isinstance(n.ops[0], (ast.Is, ast.IsNot)) and isinstance(n.comparators[0], ast.Constant)
                and n.comparators[0].value is None and _is_registry_expr(n.left)):
            return ast.Constant(isinstance(n.ops[0], ast.IsNot))
        return n

    def visit_UnaryOp(self, n: ast.UnaryOp) -> ast.AST:
        self.generic_visit(n)
        if isinstance(n.op, ast.Not):
            n.operand = _truthy_fold(n.operand)
            if _const_bool(n.operand):
                return ast.Constant(not n.operand.value)
        return n

    def visit_BoolOp(self, n: ast.BoolOp) -> ast.AST:
        """值語意折疊（審查 r52：`x and True` 之值不等於 `x`）：只去除**開頭**之布林常數——and 開頭 True 去除、開頭
        False 即 False；or 開頭 False 去除、開頭 True 即 True。非開頭常數保留。"""
        self.generic_visit(n)
        vals = list(n.values)
        absorbing = isinstance(n.op, ast.Or)  # or：True 吸收；and：False 吸收
        while vals and _const_bool(vals[0]) and len(vals) > 1:
            if vals[0].value is absorbing:
                return ast.Constant(absorbing)
            vals = vals[1:]
        return vals[0] if len(vals) == 1 else ast.BoolOp(op=n.op, values=vals)

    def _test(self, n: ast.AST) -> ast.AST:
        self.generic_visit(n)
        n.test = _truthy_fold(n.test)
        return n

    visit_If = visit_While = visit_IfExp = visit_Assert = _test


def _truthy_fold(e: ast.AST) -> ast.AST:
    """只看真假值之位置（if／while／三元／assert 條件、not 與其內之 and／or 運算元）：非吸收之布林常數任一位置可去除；
    吸收常數（and 之 False、or 之 True）只在其前無其他運算元時整式化為常數——其前之運算元仍會被求值（可能有副作用，
    審查 r53），故保留為 `前段 and/or 常數`，其後運算元不會被求值而去除。"""
    if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
        inner = _truthy_fold(e.operand)
        return ast.Constant(not inner.value) if _const_bool(inner) else ast.UnaryOp(op=e.op, operand=inner)
    if not isinstance(e, ast.BoolOp):
        return e
    absorbing = isinstance(e.op, ast.Or)
    vals = []
    for v in (_truthy_fold(x) for x in e.values):
        if _const_bool(v):
            if v.value is absorbing:
                if not vals:
                    return ast.Constant(absorbing)
                return ast.BoolOp(op=e.op, values=[*vals, ast.Constant(absorbing)])
            continue
        vals.append(v)
    if not vals:
        return ast.Constant(not absorbing)
    return vals[0] if len(vals) == 1 else ast.BoolOp(op=e.op, values=vals)


def _cgsa_block(stmts: List[ast.stmt]) -> List[ast.stmt]:
    """常數條件 if 展開、守衛敘述（`_require_cgsa_registry`，registry 已建立時無作用）移除、return／raise 後截斷（遞迴）。"""
    out: List[ast.stmt] = []
    for st in stmts:
        if _is_guard_stmt(st):
            continue
        if isinstance(st, ast.If) and _const_bool(st.test):
            out.extend(_cgsa_block(st.body if st.test.value else st.orelse))
            if out and isinstance(out[-1], (ast.Return, ast.Raise)):
                break
            continue
        for field in ("body", "orelse", "finalbody"):
            if isinstance(getattr(st, field, None), list):
                setattr(st, field, _cgsa_block(getattr(st, field)))
        if isinstance(st, ast.Try):
            for h in st.handlers:
                h.body = _cgsa_block(h.body) or [ast.Pass()]
        if isinstance(st, ast.If) and not st.body and not st.orelse:
            continue  # 守衛移除後成空殼之 if（條件為無副作用之比較／名稱）
        if hasattr(st, "body") and isinstance(st.body, list) and not st.body:
            st.body = [ast.Pass()]
        out.append(st)
        if isinstance(st, (ast.Return, ast.Raise)):
            break
    return out


def _cgsa_propagate(fn: ast.AST) -> bool:
    """布林常數區域名稱代入並刪除該賦值——只限可證支配全部讀取者（審查 r54）：賦值為函式本體**最外層**敘述、該名於
    函式內恰一次綁定（含 for／with／except／walrus 等任何 Store、參數、global／nonlocal 皆計），且每一處讀取皆位於該
    賦值之後。分支內、迴圈內或讀取先於賦值者一律不代入（保守保留，判不等價）。"""
    stores: Dict[str, int] = {}
    loads: Dict[str, List[Tuple[int, int]]] = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                loads.setdefault(n.id, []).append((n.lineno, n.col_offset))
            else:
                stores[n.id] = stores.get(n.id, 0) + 1
        elif isinstance(n, ast.arg):
            stores[n.arg] = stores.get(n.arg, 0) + 1
        elif isinstance(n, ast.ExceptHandler) and n.name:  # 審查 r55：`except … as 名` 以字串保存
            stores[n.name] = stores.get(n.name, 0) + 1
        elif isinstance(n, ast.alias):  # 函式內 import（含 as 別名）
            nm = n.asname or n.name.split(".")[0]
            stores[nm] = stores.get(nm, 0) + 1
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not fn:
            stores[n.name] = stores.get(n.name, 0) + 1
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            for nm in n.names:
                stores[nm] = stores.get(nm, 0) + 2
    consts: Dict[str, bool] = {}
    top: Dict[str, ast.Assign] = {}
    for st in getattr(fn, "body", []):
        if (isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name)
                and _const_bool(st.value)):
            name = st.targets[0].id
            end = (getattr(st, "end_lineno", st.lineno), getattr(st, "end_col_offset", 0))
            if stores.get(name) == 1 and all(pos > end for pos in loads.get(name, [])):
                consts[name] = st.value.value
                top[name] = st
    if not consts:
        return False
    assigns = {k: [top[k]] for k in consts}

    class _Sub(ast.NodeTransformer):
        def visit_Name(self, n: ast.Name) -> ast.AST:
            return ast.Constant(consts[n.id]) if isinstance(n.ctx, ast.Load) and n.id in consts else n

    _Sub().visit(fn)
    drop = {id(assigns[k][0]) for k in consts}
    for parent in ast.walk(fn):
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(parent, field, None)
            if isinstance(lst, list):
                setattr(parent, field, [s for s in lst if id(s) not in drop])
    return True


def cgsa_normal_form(fn: ast.AST) -> str:
    """CGSA 開啟且 registry 已建立之假設下之正規形（去 docstring、折疊、代入、展開至不動點）。"""
    fn = copy.deepcopy(fn)
    body = getattr(fn, "body", [])
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        fn.body = body[1:] or [ast.Pass()]
    for _ in range(8):
        _CgsaFold().visit(fn)
        changed = _cgsa_propagate(fn)
        _CgsaFold().visit(fn)
        fn.body = _cgsa_block(fn.body) or [ast.Pass()]
        if not changed:
            break
    return ast.dump(fn)


def _module_of(path: str) -> str:
    return path[:-3].replace("/", ".")


def production_changes(repo: Path, anchor: str) -> Tuple[set, set, List[str], List[str]]:
    """錨點 → 工作樹之生產碼（momentum／api／config 之 .py）：(被刪定義名, CGSA 殘差定義名, 改動檔, 殘差定義規格
    `模組:限定名`)。本體改變之定義經 `cgsa_normal_form` 比對：正規形相同（CGSA 開啟下等價，例如只拿掉
    `_cgsa_enabled()` 判斷、加 registry 守衛）者不入殘差；不同者（不論公開或私有）入殘差。另：被刪且於全部生產碼
    已無定義之名稱若仍被引用 ⇒ GateError（懸空引用）。名稱取末段。"""
    files = [p for p in _git(repo, "diff", "--name-only", anchor, "--", *PRODUCTION_ROOTS).splitlines()
             if p.endswith(".py") and "/__pycache__/" not in p]
    deleted, residual, specs = set(), set(), set()
    deleted_defs = set()
    for f in files:
        old = _git_show(repo, anchor, f)
        new = (repo / f).read_text(encoding="utf-8") if (repo / f).is_file() else None
        old_tree = ast.parse(old) if old is not None else ast.Module(body=[], type_ignores=[])
        new_tree = ast.parse(new) if new is not None else ast.Module(body=[], type_ignores=[])
        od, nd = _defs(old_tree), _defs(new_tree)
        for q, node in od.items():
            bare = q.split(".")[-1]
            if q not in nd:
                deleted.add(bare)
                deleted_defs.add(bare)
            elif isinstance(node, ast.ClassDef):
                if _class_header(node) != _class_header(nd[q]):
                    raise GateError(f"{f}:{q} 類別標頭（基底／decorator／keywords）改變，無法機械判定影響範圍")
            elif ast.dump(node) != ast.dump(nd[q]) and cgsa_normal_form(node) != cgsa_normal_form(nd[q]):
                residual.add(bare)
                specs.add(f"{_module_of(f)}:{q}")
        # 審查 r52：模組層與類別層之非定義綁定（常數、匯入、類別屬性）亦比對；值改變之名入殘差，且新碼中引用該名之
        # 定義一併入殘差規格（以執行探針觀測）；其他無法以名稱歸屬之模組層敘述改變 ⇒ 拒跑
        scopes = [("", old_tree.body, new_tree.body)]
        scopes += [(q, od[q].body, nd[q].body) for q in od if isinstance(od[q], ast.ClassDef) and q in nd]
        for owner, old_body, new_body in scopes:
            ob, o_other = _bindings(old_body)
            nb, n_other = _bindings(new_body)
            if o_other != n_other:
                raise GateError(f"{f}{':' + owner if owner else ''} 之非定義、非綁定敘述改變，無法機械判定影響範圍")
            # SPEC v24 D13：只自非生產模組（標準庫／第三方）匯入之綁定名之增刪改不入 S2——拿掉未用之 `np`／`Path` 等
            # 匯入不改任何行為，裸名比對卻會命中幾乎全部測試（b2 實測選入 8,304 項）；自生產模組匯入者照舊計入
            ext = _external_import_names(old_body) | _external_import_names(new_body)
            gone = (set(ob) - set(nb)) - ext
            changed_names = {k for k in set(ob) & set(nb) if ob[k] != nb[k]} - ext
            deleted |= gone
            residual |= changed_names
            for q, node in nd.items():
                if isinstance(node, ast.ClassDef) or (owner and not q.startswith(owner + ".")):
                    continue
                if refs_of(node) & (changed_names | gone):
                    residual.add(q.split(".")[-1])
                    specs.add(f"{_module_of(f)}:{q}")
    dangling = _dangling_refs(repo, deleted_defs)
    if dangling:
        raise GateError(f"生產碼仍引用已無定義之被刪名稱：{dangling[:10]}")
    return deleted, residual, files, sorted(specs)


def _class_header(node: ast.ClassDef) -> str:
    return "|".join(ast.dump(x) for x in [*node.bases, *node.keywords, *node.decorator_list])


def _bindings(body: Sequence[ast.stmt]) -> Tuple[Dict[str, str], List[str]]:
    """非定義敘述 → ({綁定名: 該名所有綁定敘述之 dump 串接}, [其他敘述 dump])。賦值（含解構、註記、增量）以目標名
    歸屬；匯入以本地名歸屬（逐別名）；docstring 與 pass 不計；其餘（模組層 if／try／呼叫等）入「其他」。"""
    named: Dict[str, str] = {}
    other: List[str] = []
    for i, st in enumerate(body):
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Pass)):
            continue
        if i == 0 and isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
            continue
        if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = st.targets if isinstance(st, ast.Assign) else [st.target]
            names = [n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)]
            if names:
                for nm in names:
                    named[nm] = named.get(nm, "") + ast.dump(st)
                continue
        if isinstance(st, (ast.Import, ast.ImportFrom)):
            for a in st.names:
                local = a.asname or a.name.split(".")[0]
                src = f"{getattr(st, 'module', '') or ''}|{getattr(st, 'level', 0)}|{a.name}"
                named[local] = named.get(local, "") + src
            continue
        other.append(ast.dump(st))
    return named, other


def _external_import_names(body: Sequence[ast.stmt]) -> set:
    """SPEC v24 D13：本層 Import／ImportFrom 中，來源為非生產模組（絕對匯入且頂層套件不在 PRODUCTION_ROOTS）之本地綁定名；
    相對匯入與自 momentum／api／config 匯入者不算（照舊入 S2）。同名另有非匯入綁定者亦不算（保守）。"""
    roots = {r.strip("/").split("/")[0] for r in PRODUCTION_ROOTS}
    ext, non_ext = set(), set()
    for st in body:
        if isinstance(st, ast.Import):
            for a in st.names:
                local = a.asname or a.name.split(".")[0]
                (non_ext if a.name.split(".")[0] in roots else ext).add(local)
        elif isinstance(st, ast.ImportFrom):
            top = (st.module or "").split(".")[0]
            for a in st.names:
                local = a.asname or a.name
                (non_ext if st.level or top in roots else ext).add(local)
        elif isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = st.targets if isinstance(st, ast.Assign) else [st.target]
            non_ext.update(n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name))
        elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            non_ext.add(st.name)
    return ext - non_ext


def _dangling_refs(repo: Path, deleted: Iterable[str]) -> List[str]:
    """全部生產碼（工作樹）中，被刪且已無任何定義之名稱之引用（`檔:名`）。"""
    deleted = set(deleted)
    if not deleted:
        return []
    trees = {}
    for root in PRODUCTION_ROOTS:
        for p in sorted((repo / root).rglob("*.py")) if (repo / root).is_dir() else []:
            if "__pycache__" in p.parts:
                continue
            try:
                trees[str(p.relative_to(repo))] = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
    defined = {n.name for t in trees.values() for n in ast.walk(t)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    gone = deleted - defined
    return sorted(f"{f}:{n}" for f, t in trees.items() for n in (refs_of(t) & gone))


def s2_symbols(deleted: Iterable[str], residual: Iterable[str]) -> frozenset:
    """S2 符號表：被刪定義 ∪ CGSA 殘差定義（不分公開私有）。CGSA 下可證等價之改動不入表；殘差定義經公開入口之執行由
    A 組不變性比對之殘差探針（`FRAMEPATH_DEF_PROBE_*`）證明已被執行。"""
    return frozenset(set(deleted) | set(residual))


def _git_show(repo: Path, rev: str, path: str) -> Optional[str]:
    proc = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), "show", f"{rev}:{path}"],
                          capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None


def _row_nodeids(rows: Sequence[str], prefix: str) -> List[str]:
    hits = [r for r in rows if r.startswith(prefix)]
    if len(hits) > 1:
        raise GateError(f"manifest 重複 {prefix.strip()}")
    return [p for p in hits[0][len(prefix):].split() if p] if hits else []


def out_exclusion(repo: Path, out_dir: Optional[Path]) -> Optional[str]:
    """本次 `--out` 位於 repo 內 ⇒ 排除其下未追蹤內容之 pathspec（前綴由參數導出）；位於 repo 外或未給 ⇒ None。"""
    if out_dir is None:
        return None
    try:
        rel = Path(out_dir).resolve().relative_to(Path(repo).resolve())
    except ValueError:
        return None
    return f":(exclude){rel.as_posix()}/**" if rel.parts else None


def default_out_dir(repo: Path, batch: int) -> Path:
    """SPEC v25 D18：結果目錄預設於 repo 內被 git 忽略之 `.testreg/framepath_gate_b<N>`（重開機不清；原預設系統暫存區
    於 macOS 開機時清空，2026-10-16 實際因重開機遺失全部已跑結果）。"""
    return Path(repo) / ".testreg" / f"framepath_gate_b{batch}"


def check_out_dir(out_dir: Path, repo: Path) -> None:
    """`--out` 不得為 repo 根或其祖先（排除前綴會吞掉全部未追蹤內容）。"""
    o, r = Path(out_dir).resolve(), Path(repo).resolve()
    if o == r or o in r.parents:
        raise GateError(f"--out 不得為 repo 根或其上層：{o}")


def _within(d: Path, out_dir: Optional[Path]) -> bool:
    if out_dir is None:
        return False
    d, o = Path(d).resolve(), Path(out_dir).resolve()
    return d == o or o in d.parents


def _sha_file_or_empty(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


def plan_inputs_digest(repo: Path, anchor: str, phase: int, timing_dirs: Iterable[Path] = (),
                       env: Optional[Mapping[str, str]] = None, *, out: Optional[Path] = None,
                       manifest: Optional[Mapping] = None, previously_failed: Optional[Sequence[str]] = None) -> str:
    """挑選之輸入指紋：錨點、phase、排除後之 HEAD 檔案樹身分、相對 HEAD 之 diff、未追蹤檔路徑＋內容與資料輸入內容（content_inputs）、manifest、處置表、本執行器原始碼、
    admission 估時來源（各目錄下 junit xml 之路徑與內容，審查 r53）。`--admit` 須等於此值方得於估時未知或逾預算時執行
    （批准綁定確切輸入）。TESTREG Task 2.3（契約 `impact.gate_wiring`）：另納 plan 實際收到之 manifest 物件之正規
    JSON、catalog／schema／scripts/testreg.py 之 sha256、previously_failed 之排序清單；本次 `--out` 之下之未追蹤內容與
    估時目錄（等於 out 或位於其下者）不納入（`out_exclusion`）。"""
    h = hashlib.sha256()
    excl = out_exclusion(repo, out)
    for part in (anchor, str(phase), tree_identity(repo),  # 審查 r58：檔案樹身分取代提交編號
                 _git(repo, "diff", "--binary", "HEAD", "--", ".", *FP_EXCLUDES),
                 content_inputs(repo, (excl,) if excl else ())):  # 審查 r52／r60：未追蹤檔路徑＋內容、資料輸入內容
        h.update(part.encode("utf-8", "replace"))
        h.update(b"\0")
    for rel in (MANIFEST_REL, DISPOSITION_REL, "scripts/framepath_affected_gate.py"):
        h.update((repo / rel).read_bytes() if (repo / rel).is_file() else b"")
        h.update(b"\0")
    # 審查 r55：子行程有效環境（含 PYTEST_ADDOPTS 等會改變收集與執行者）綁入
    h.update(b"env\0" + env_fingerprint(env if env is not None else os.environ).encode("utf-8", "replace") + b"\0")
    for d in timing_dirs:
        d = Path(d).resolve()
        if _within(d, out):
            continue
        h.update(b"timings\0" + str(d).encode("utf-8", "replace") + b"\0")
        for x in sorted(d.rglob("*.xml")) if d.is_dir() else []:
            h.update(str(x.relative_to(d)).encode("utf-8", "replace") + b"\0" + hashlib.sha256(x.read_bytes()).digest())
    if manifest is not None:
        h.update(b"manifest\0" + json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                 .encode("utf-8") + b"\0")
    for rel in (TESTREG_CATALOG_REL, TESTREG_SCHEMA_REL, "scripts/testreg.py"):
        h.update(f"{rel}\0{_sha_file_or_empty(Path(repo) / rel)}\0".encode("utf-8"))
    h.update(b"previously_failed\0" + json.dumps(sorted(previously_failed or [])).encode("utf-8") + b"\0")
    h.update(f"machine_memory\0{machine_memory_bytes()}\0".encode("utf-8"))  # SPEC v25 D14：選入依機器記憶體
    return h.hexdigest()


# ── TESTREG Task 2.3：plan 吃 impact、碑解析、must 核對（契約 `impact.gate_feed`、`gate_report`）────────────────────


def _testreg():
    """`scripts.testreg`（模組屬性取用，`monkeypatch.setattr(testreg, "impact", …)` 生效）。"""
    return importlib.import_module("scripts.testreg")


def changed_paths(repo: Path, anchor: str) -> List[str]:
    """契約 `impact.gate_wiring`：排序去重之（`git diff --name-only <anchor>` ∪ `git diff --name-only HEAD` ∪
    `git ls-files --others --exclude-standard`），三者皆扣除 FP_EXCLUDES，不限 tests/。"""
    out = set()
    for args in (("diff", "--name-only", "--no-renames", anchor), ("diff", "--name-only", "--no-renames", "HEAD"),
                 ("ls-files", "--others", "--exclude-standard")):
        out |= {p for p in _git(repo, *args, "--", ".", *FP_EXCLUDES).splitlines() if p}
    return sorted(p for p in out if not _fp_excluded(p))


def resolve_tombstones(repo: Path, items: Sequence[str], catalog: Mapping) -> Tuple[List[str], List[Dict[str, object]]]:
    """契約 `impact.gate_feed` 第一步：items（nodeid 或測試檔路徑）中已立碑者以 replaced_by 遞迴取代（循環 ⇒
    GateError）、E0 除去並記；路徑有碑而檔已不存在 ⇒ 以取代者所在檔取代。回傳 (解析後 items, tombstone_resolutions)。"""
    try:
        return _testreg().resolve_tomb_items(list(items), (catalog or {}).get("tombstones", []),
                                             exists=lambda p: (Path(repo) / p).is_file())
    except _testreg().TestregError as exc:
        raise GateError(str(exc)) from exc


def must_missing(must: Sequence[str], collected: Mapping[str, Sequence[str]]) -> List[str]:
    """collect 後核對：must nodeid 不在收集結果者（缺 ⇒ 閘拒跑）。"""
    have = {n for ids in collected.values() for n in ids}
    return [m for m in must if m not in have]


def expanded_nodeids(selected: Iterable[str], collected: Mapping[str, Sequence[str]],
                     whole_files: Iterable[str]) -> set:
    """新計畫之 nodeid 集合：原計畫選入者 ∪ 整檔執行之檔（impact.selected）之全部收集 nodeid。"""
    out = set(selected)
    for f in whole_files:
        out |= set(collected.get(f, ()))
    return out


def impact_universe_errors(impact: Mapping, tree_tests: Iterable[str]) -> List[str]:
    """契約 `gate_report.impact_universe`：selected／excluded 之 path 各自無重複、互斥、聯集＝受驗之樹之測試檔集合。"""
    errs: List[str] = []
    sel = [x.get("path") for x in impact.get("selected", []) if isinstance(x, dict)]
    exc = [x.get("path") for x in impact.get("excluded", []) if isinstance(x, dict)]
    for name, xs in (("selected", sel), ("excluded", exc)):
        dup = sorted({p for p in xs if xs.count(p) > 1})
        if dup:
            errs.append(f"impact {name} 重複：{dup[:5]}")
    both = sorted(set(sel) & set(exc))
    if both:
        errs.append(f"impact selected 與 excluded 重疊：{both[:5]}")
    tree = set(tree_tests)
    if set(sel) | set(exc) != tree:
        errs.append(f"impact 涵蓋 ≠ 受驗之樹之測試檔：缺 {sorted(tree - set(sel) - set(exc))[:5]} "
                    f"多 {sorted((set(sel) | set(exc)) - tree)[:5]}")
    return errs


def _tree_tests(repo: Path) -> List[str]:
    tr = _testreg()
    pat = _testreg_schema(repo)["formats"]["test_path"]
    return sorted(f for f in tr._Tree(Path(repo), "worktree").files() if re.fullmatch(pat, f))


def validate_plan_receipt(fields: Mapping[str, object], repo: Path) -> List[str]:
    """契約 `gate_report.validation`：所給之 plan 收據欄依 `plan_receipt_fields` 驗形（V17 同法，testreg.validate_shape），
    testreg_impact 必備並驗 impact_universe。"""
    tr = _testreg()
    schema = _testreg_schema(repo)
    spec = schema["gate_report"]["plan_receipt_fields"]
    errs: List[str] = []
    if "testreg_impact" not in fields:
        errs.append("plan 收據缺 testreg_impact")
    for k, v in fields.items():
        if k not in spec:
            errs.append(f"plan 收據未知欄 {k}")
            continue
        errs += [f"{k}: {e}" for e in tr.validate_shape(v, spec[k], schema, k)]
    imp = fields.get("testreg_impact")
    if isinstance(imp, dict) and not errs:
        errs += impact_universe_errors(imp, _tree_tests(repo))
    return errs


def _load_catalog(repo: Path) -> Dict[str, object]:
    p = Path(repo) / TESTREG_CATALOG_REL
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GateError(f"{TESTREG_CATALOG_REL} 不存在或不可解析") from exc


def junit_times(xml_text: str, repo: Path) -> Dict[str, float]:
    """junit xml → {nodeid: 秒}；classname 之模組段以 repo 內存在之 `.py` 判定，其後為類別段。"""
    out: Dict[str, float] = {}
    for case in ET.fromstring(xml_text).iter("testcase"):
        parts = case.get("classname", "").split(".")
        for i in range(len(parts), 0, -1):
            path = "/".join(parts[:i]) + ".py"
            if (repo / path).is_file():
                try:
                    t = float(case.get("time", ""))
                except ValueError:
                    break
                if math.isfinite(t) and t >= 0:  # 審查 r52：非有限、負值、缺值一律不採（該 nodeid 估時未知）
                    out["::".join([path, *parts[i:], case.get("name", "")])] = t
                break
    return out


def admission(selected: Iterable[str], times: Mapping[str, float], budget: Optional[float] = None
              ) -> Dict[str, object]:
    """執行前估時（純函式）：已知估時總和、估時未知之 nodeid；status＝within（全部已知且未逾明示預算）｜over（只在呼叫端
    明示 `budget` 時）｜unknown。NOCAP Task 2.1：預設無預算、閘門只印估時不拒跑。非有限或負值之估時視為未知。"""
    sel = list(selected)
    ok = {n: times[n] for n in sel if n in times and math.isfinite(times[n]) and times[n] >= 0}
    known = round(sum(ok.values()), 3)
    unknown = sorted(n for n in sel if n not in ok)
    status = "over" if budget is not None and known > budget else ("unknown" if unknown else "within")
    return {"budget_seconds": budget, "known_seconds": known, "unknown": unknown, "status": status}


def load_times(repo: Path, dirs: Iterable[Path]) -> Dict[str, float]:
    """估時來源：給定目錄下全部 junit xml（本執行器先前之結果檔與歷次收據）；同 nodeid 取最大值（保守）。"""
    times: Dict[str, float] = {}
    for d in dirs:
        for x in sorted(Path(d).rglob("*.xml")) if Path(d).is_dir() else []:
            try:
                for n, t in junit_times(x.read_text(encoding="utf-8"), repo).items():
                    times[n] = max(t, times.get(n, 0.0))
            except ET.ParseError:
                continue
    return times


def plan(repo: Path, anchor: str, phase: int, manifest: Mapping, env: Mapping[str, str],
         timing_dirs: Sequence[Path] = (), out: Optional[Path] = None) -> Dict[str, object]:
    """D8 挑選（不執行測試本體；耗時主要為逐檔 collect）：collect B／C 檔、靜態掃描錨點與工作樹兩版之測試檔並取聯集。
    須於本批完整改動（生產碼＋測試處置）套上後執行；任一檔 collect 失敗 ⇒ 拒跑。

    TESTREG Task 2.3（契約 `impact.gate_feed`）：①collect 之前，B／C 組與 must 之已立碑項以碑之 replaced_by 取代並
    留原組（`resolve_tombstones`）②於行程內呼叫 `scripts.testreg.impact`（changed_paths、must、previously_failed），
    其 selected 之檔整檔執行（不在 A／B／C 者併入 extra_files）③collect 後逐一核對 must 皆被收集（`must_missing`）
    ④plan 收據欄（`plan_receipt_fields`）驗形與 impact_universe 不符 ⇒ GateError。"""
    rows = manifest["batch_card"]["risk_mitigation"]
    catalog = _load_catalog(repo)
    b_raw, c_raw = manifest_groups(manifest, phase)
    a_group, res_a = resolve_tombstones(repo, list(A_GROUP_BY_PHASE[phase]), catalog)
    b_group, res_b = resolve_tombstones(repo, b_raw, catalog)
    c_group, res_c = resolve_tombstones(repo, c_raw, catalog)
    must, res_m = resolve_tombstones(repo, _row_nodeids(rows, f"affected_must phase={phase} "), catalog)
    resolutions = list({r["from"]: r for r in [*res_a, *res_b, *res_c, *res_m]}.values())
    resolutions.sort(key=lambda r: str(r["from"]))
    a_group = [p.split("::", 1)[0] for p in a_group]
    a_group = list(dict.fromkeys(a_group))
    c_group = [p for p in c_group if p not in A_GROUP and p not in a_group]
    b_group = [p for p in b_group if p not in A_GROUP and p not in a_group and p not in c_group]
    heavy_pinned = _row_nodeids(rows, f"heavy_files phase={phase} ")
    tr = _testreg()
    previously_failed = tr.previously_failed_from_summary(repo)
    try:
        impact = tr.impact(repo, changed_paths(repo, anchor), list(must), list(previously_failed),
                           production_taint=False)
    except tr.TestregError as exc:
        raise GateError(f"testreg impact 拒跑：{exc}") from exc
    if not isinstance(impact, dict):
        impact = {}
    pre_errs = validate_plan_receipt({"testreg_impact": impact}, repo)
    if pre_errs:
        raise GateError(f"plan 收據驗證不符：{pre_errs[:5]}")
    deleted, residual, prod_files, residual_specs = production_changes(repo, anchor)
    symbols = s2_symbols(deleted, residual)
    align_triggered = bool(set(prod_files) & ALIGN_TRIGGER_FILES or (deleted | residual) & ALIGN_TRIGGER_SYMBOLS)

    def post(p: str) -> Optional[str]:
        return (repo / p).read_text(encoding="utf-8") if (repo / p).is_file() else None

    # 錨點版只對錨點→工作樹有改動（含刪除）之 tests/ 檔讀 git，其餘與工作樹同
    changed_tests = set(_git(repo, "diff", "--name-only", anchor, "--", "tests").splitlines())

    def pre(p: str) -> Optional[str]:
        return _git_show(repo, anchor, p) if p in changed_tests else post(p)

    caches: Dict[str, dict] = {"pre": {}, "post": {}, "heavy_pre": {}, "heavy_post": {}}

    def merged_scan(f: str, want_heavy: bool = True) -> Dict[str, object]:
        a = file_scan(f, pre, symbols, caches["pre"], caches["heavy_pre"], want_heavy)
        b = file_scan(f, post, symbols, caches["post"], caches["heavy_post"], want_heavy)
        refs = {q: set(a["refs"].get(q, set())) | set(b["refs"].get(q, set())) for q in {*a["refs"], *b["refs"]}}
        taint = {q: set(a["taint"].get(q, set())) | set(b["taint"].get(q, set())) for q in {*a["taint"], *b["taint"]}}
        return {"refs": refs, "taint": taint, "heavy": bool(a["heavy"] or b["heavy"])}

    empty: List[str] = []  # SPEC v22 D11.12：無測試函式之檔（rc 5、no tests collected）＝空集合，不選入，收據 empty_collect
    collected = {f: collect_or_empty(f, repo, env, empty) for f in b_group + c_group}
    scans: Dict[str, Dict[str, object]] = {f: merged_scan(f) for f in collected}
    # 清單外之測試檔亦受 S2 約束（審查 r51）：全部 tests/ 下 test_*.py 經同一傳遞分析，有 taint 者納入（只選 taint 之
    # nodeid，不整檔），收據記 extra_files。
    known = set(collected) | set(A_GROUP) | set(a_group)
    extra: List[str] = []
    for p in sorted((repo / "tests").rglob("test_*.py")):
        rel = str(p.relative_to(repo))
        if rel in known or "__pycache__" in p.parts:
            continue
        scan = merged_scan(rel, want_heavy=False)
        if scan["taint"]:
            scan["heavy"] = True
            scans[rel] = scan
            extra.append(rel)
    for rel in extra:
        collected[rel] = collect_or_empty(rel, repo, env, empty)
    # impact.selected 之檔整檔執行（gate_feed 第二步）；不在 A／B／C／extra 者併入 extra_files
    impact_files = {x["path"]: list(x["reasons"]) for x in impact["selected"]}
    for rel in sorted(impact_files):
        if rel not in collected and rel not in A_GROUP and rel not in a_group:
            collected[rel] = collect_or_empty(rel, repo, env, empty)
            extra.append(rel)
    missing = must_missing(must, collected)
    if missing:
        raise GateError(f"manifest affected_must（碑解析後）之 nodeid 未被收集：{missing}")
    disposition = json.loads((repo / DISPOSITION_REL).read_text(encoding="utf-8"))
    s1_funcs, s1_nodes = s1_targets(disposition, phase, scans)
    selected, skipped = select_expected(collected, scans, s1_funcs, s1_nodes, must, heavy_pinned, align_triggered)
    for rel, reasons in impact_files.items():
        for nid in collected.get(rel, []):
            selected.setdefault(nid, [])
            selected[nid] += [f"impact:{r}" for r in reasons]
            skipped.pop(nid, None)
    # SPEC v25 D14：本機記憶體不足之大機器專用測試（RM-FULLSCALE 登記）不選入；must 落入其中 ⇒ 拒跑
    blocked = hardware_blocked(load_hardware_requirements(repo), machine_memory_bytes())
    blocked_must = [n for n in must if n.split("::", 1)[0] in blocked]
    if blocked_must:
        raise GateError(f"manifest affected_must 落入本機跑不動之大機器專用測試：{blocked_must}")
    for path, row in blocked.items():
        row["nodeids"] = sorted(n for n in selected if n.split("::", 1)[0] == path)
        for nid in row["nodeids"]:
            selected.pop(nid)
            skipped[nid] = f"hardware_blocked:{row['ticket']}"
    baseline = repo / INVARIANCE_BASELINE_REL
    fields = {"testreg_impact": impact, "catalog_sha256": _sha_file_or_empty(repo / TESTREG_CATALOG_REL),
              "previously_failed": list(previously_failed), "tombstone_resolutions": resolutions,
              "must_check": {"must": list(must), "missing": missing}}
    errs = validate_plan_receipt(fields, repo)
    if errs:
        raise GateError(f"plan 收據驗證不符：{errs[:5]}")
    return {
        "groups": {"A": a_group, "B": b_group, "C": c_group}, "collected": collected, "selected": selected, "skipped": skipped,
        "s2_symbols": sorted(symbols), "production_files": prod_files, "align_triggered": align_triggered,
        "residual_defs": residual_specs,
        "inputs_digest": plan_inputs_digest(repo, anchor, phase, timing_dirs, env, out=out, manifest=manifest,
                                            previously_failed=previously_failed),
        "extra_files": extra,
        "empty_collect": sorted(set(empty)),
        "hardware_blocked": blocked,
        "light_files": sorted(f for f, s in scans.items() if not s["heavy"] and f not in set(heavy_pinned)),
        "invariance_baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest() if baseline.is_file() else None,
        **fields,
    }


BATCH_PHASE = {1: 1, 2: 2, 3: 3, 4: 3}


def current_batch() -> int:
    """本票最晚一筆實作許可之批次（審計 `impl_token_issued` 之 batch 欄；與錨點同一筆）。"""
    from tests.feature_engineering.test_framepath_disposition import AUDIT_REL, TICKET_ROOT

    batch = None
    for line in (REPO / AUDIT_REL).read_text(encoding="utf-8", errors="replace").splitlines():
        if '"impl_token_issued"' not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("event") == "impl_token_issued" and ev.get("root") == TICKET_ROOT:
            batch = ev.get("batch")
    if batch is None or int(batch) not in BATCH_PHASE:
        raise GateError(f"審計紀錄無本票實作許可或批次不合法：{batch!r}")
    return int(batch)


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None, help="結果目錄（預設 .testreg/framepath_gate_b<N>，repo 內被 git 忽略、重開機不清，供接續）")
    ap.add_argument("--anchor-worktree", default=None)
    ap.add_argument("--plan", action="store_true",
                    help="只產出 D8 挑選（選入／未跑逐項理由、估時與 admission）收據，不執行測試本體")
    ap.add_argument("--timings", action="append", default=[],
                    help="估時來源目錄（其下 junit xml；可重複）；本執行器之結果目錄恆納入")
    ap.add_argument("--admit", default=None,
                    help="admission 非 within（估時未知或逾預算）時，呈報後以該次挑選之 inputs_digest 批准執行")
    ap.add_argument("--max-seconds", type=float, default=None,
                    help="選填之分段：使用者明示時，已用逾此值即不再開新 pytest 呼叫、於呼叫之間停下（rc 3），同命令接續；"
                         "未給 ⇒ 不分段（NOCAP Task 2.1）")
    args = ap.parse_args(argv)
    batch = current_batch()
    args.phase = BATCH_PHASE[batch]
    args.receipt = str(REPO / f"handoffs/run_receipts/framepath-b{batch}-affected.json")
    out = Path(args.out or default_out_dir(REPO, batch)).resolve()
    check_out_dir(out, REPO)
    anchor = resolve_anchor()
    global _RUNNER
    # TESTREG Task 2.3：ledger_dir 與 catalog 一律由模組屬性 REPO 導出（契約 gate_report.current_failure_source）
    ledger_dir = REPO / _testreg_schema(REPO)["ledger"]["dir"]
    runner = _RUNNER = Runner(out, args.max_seconds, 0, ledger_dir=ledger_dir)  # 審查 r59：挑選與收集階段即寫 progress.json
    env = dict(os.environ, FRAMEPATH_PHASE=str(args.phase), PYTHONPATH=str(REPO))
    manifest = json.loads((REPO / MANIFEST_REL).read_text(encoding="utf-8"))
    timing_dirs = [out, *[Path(t) for t in args.timings]]
    sel = plan(REPO, anchor, args.phase, manifest, env, timing_dirs, out=out)
    # TESTREG v41（諮詢 r2 CODEX-R2-P1-03）：A 組亦經碑解析，以 plan 回傳之解析後 A 收集與執行
    a_files = list(sel["groups"].get("A", A_GROUP_BY_PHASE[args.phase]))
    a_ids = [n for f in a_files for n in collect(f, REPO, env)]
    times = load_times(REPO, timing_dirs)
    adm = admission([*a_ids, *sel["selected"]], times)
    if args.plan:
        plan_path = REPO / f"handoffs/run_receipts/framepath-b{batch}-affected-plan.json"
        plan_path.write_text(json.dumps({"spec": "docs/FRAMEPATH_SPEC.md v22 D8＋D11", "phase": args.phase, "anchor": anchor,
                                         **sel, "admission": adm}, ensure_ascii=False, indent=1, default=sorted) + "\n",
                             encoding="utf-8")
        print(f"FRAMEPATH affected plan：collected={sum(len(v) for v in sel['collected'].values())} "
              f"selected={len(sel['selected'])} skipped={len(sel['skipped'])} admission={adm['status']} "
              f"known={adm['known_seconds']}s unknown={len(adm['unknown'])} inputs_digest={sel['inputs_digest']} "
              f"→ {plan_path.relative_to(REPO)}")
        return 0
    # NOCAP Task 2.1：估時只印不拒跑（不依預計耗時擋下運算；卡死由共用監看依進度判定）
    print(f"FRAMEPATH affected 估時：已知 {adm['known_seconds']} 秒、估時未知 {len(adm['unknown'])} 項（status={adm['status']}）")
    anchor_wt = (Path(args.anchor_worktree).resolve() if args.anchor_worktree
                 else make_anchor_worktree(anchor, out / f"anchor_{anchor[:12]}" / "wt"))
    verify_anchor_worktree(anchor_wt, anchor)
    if not (anchor_wt / "data_cache").exists():
        (anchor_wt / "data_cache").symlink_to(REPO / "data_cache")
    anchor_env = dict(os.environ, PYTHONPATH=str(anchor_wt))
    b_group, c_group = sel["groups"]["B"], sel["groups"]["C"]
    runner.total = len(a_ids) + len(sel["selected"])

    a_failures: List[str] = []
    a_results: Dict[str, Dict[str, str]] = {}
    # 殘差定義探針（審查 r52：A 組與選入之 B／C 皆記；證據為「定義被呼叫」，非改動行之執行）：每檔獨立目錄，
    # 重跑時清空、沿用舊結果檔時一併沿用其觀測
    probe_root = out / "def_probe"

    def probe_env(name: str, fresh: bool) -> Dict[str, str]:
        d = probe_root / name
        d.mkdir(parents=True, exist_ok=True)
        if fresh:
            for stale in d.glob("*.json"):
                stale.unlink()
        return dict(env, PYTHONPATH=f"{TRACE_SITE_DIR}{os.pathsep}{REPO}{os.pathsep}{REPO / 'scripts'}",
                    FRAMEPATH_DEF_PROBE_DIR=str(d), FRAMEPATH_DEF_PROBE_DEFS=",".join(sel["residual_defs"]),
                    **{TRACE_DIR_ENV: str(d / "trace")})  # SPEC v25 D16

    def call_id(f: str, ids: Sequence[str], label: str) -> str:
        """SPEC v25 D16：同一呼叫之身分（檔、nodeid、旗標、phase、組別、有效環境）。"""
        return hashlib.sha256(json.dumps([f, list(ids), list(PYTEST_FLAGS), list(PROBE_PLUGIN_ARGS), args.phase, label,
                                          env_fingerprint(env)]).encode("utf-8")).hexdigest()

    probe_dirs: List[Path] = []
    for f in a_files:
        ids = collect(f, REPO, env)
        # 實作期 b1：處置驗證器 ⑦ 檢查工作樹改動，而同檔之 check_1／check_2 以 collect-only 子行程改寫已追蹤清冊
        # （tests/conftest.py 之副作用）⇒ 同一呼叫中 ⑦ 見到生成物而紅。把「檢查工作樹」之 nodeid 先於乾淨樹單獨
        # 呼叫（呼叫前已還原清冊），其餘再一次呼叫；不跳過、不放寬任何斷言
        first = [n for n in ids if nodeid_qualname(n) in A_ISOLATED_FIRST.get(f, ())]
        rest = [n for n in ids if n not in first]
        res, rcs = {}, []
        for part, suffix in ((first, "__first"), (rest, "")):
            if not part:
                continue
            name = "A_" + f.replace("/", "_") + suffix
            probe_dirs.append(probe_root / name)
            prc, pres = runner.run(f, out / "a_junit" / (f.replace("/", "_") + suffix + ".xml"), REPO,
                                   probe_env(name, False), None if (part is rest and not first) else part,
                                   PROBE_PLUGIN_ARGS, state_key(REPO, f, args.phase, env) + "|" + "|".join(part),
                                   part, phase="A", probe_dir=probe_root / name, trace_dir=probe_root / name / "trace",
                                   call_id=call_id(f, part, "A" + suffix))
            rcs.append(prc)
            res.update(pres)
        rc = max(rcs) if all(r in RUN_RC_OK for r in rcs) else next(r for r in rcs if r not in RUN_RC_OK)
        a_results.update(res)
        a_failures += [n for n in ids if res.get(n, {}).get("outcome") != "passed"]
        if rc not in RUN_RC_OK:
            a_failures.append(f"{f}（pytest rc={rc}）")

    expected: List[str] = []
    batch: Dict[str, Dict[str, str]] = {}
    per_file: Dict[str, Dict[str, object]] = {}
    incomplete: List[str] = []
    light = set(sel["light_files"])
    for f in b_group + c_group + list(sel["extra_files"]):
        all_ids = sel["collected"][f]
        ids = [n for n in all_ids if n in sel["selected"]]
        expected += ids
        if not ids:
            per_file[f] = {"collected": len(all_ids), "expected": 0, "results": 0, "rc": None}
            continue
        whole = len(ids) == len(all_ids)
        # 每檔一次呼叫（整檔或選入之 nodeid 子集，同 D8 原語意；審查 r57：逐 nodeid 拆呼叫會改變 fixture 生命週期與
        # 模組共享狀態，未證等價不採）；接續之粒度＝檔
        tag = f.replace("/", "_")
        name = "BC_" + tag
        probe_dirs.append(probe_root / name)
        rc, res = runner.run(f, out / "junit" / (tag + ".xml"), REPO, probe_env(name, False), None if whole else ids,
                             PROBE_PLUGIN_ARGS, state_key(REPO, f, args.phase, env) + "|" + "|".join(ids), ids,
                             probe_dir=probe_root / name, trace_dir=probe_root / name / "trace",
                             call_id=call_id(f, ids, "BC"))
        if rc not in RUN_RC_OK or set(ids) - set(res):
            incomplete.append(f)
        # 只計入選入之 nodeid（沿用之舊結果檔可能含整檔結果）；junit 名稱對不上者以 missing 擋下
        batch.update({n: r for n, r in res.items() if n in sel["selected"] or n not in all_ids})
        per_file[f] = {"collected": len(all_ids), "expected": len(ids), "results": len(set(ids) & set(res)), "rc": rc}

    not_passed = [n for n in expected if n in batch and batch[n]["outcome"] != "passed"]
    anchor_res: Dict[str, Dict[str, str]] = {}
    for f in dict.fromkeys(n.split("::", 1)[0] for n in not_passed):
        ids = [n for n in not_passed if n.startswith(f + "::")]
        if (anchor_wt / f).is_file():
            # 審查 r57：錨點結果之沿用綁錨點工作樹狀態指紋（HEAD、樹、測試檔、pytest 參數、有效環境）＋所請 nodeid
            akey = "anchor|" + state_key(anchor_wt, f, args.phase, anchor_env) + "|" + "|".join(ids)
            arc, res = runner.run(f, out / "anchor_junit" / (f.replace("/", "_") + ".xml"), anchor_wt, anchor_env,
                                  ids, (), akey, ids, phase="anchor")
            anchor_res.update(anchor_usable(arc, res, ids))
    runner.progress("done", "", [])
    result = classify(expected, batch, anchor_res)
    hits = set().union(*(probe_hits(d) for d in probe_dirs)) if probe_dirs else set()
    unexecuted = sorted(set(sel["residual_defs"]) - hits)
    catalog = _load_catalog(REPO)
    passed, quarantined = quarantined_verdict(result, a_failures, incomplete, unexecuted, runner, catalog, ledger_dir,
                                              datetime.date.today())
    tomb_rows = list(sel.get("tombstone_resolutions", []))
    tr = _testreg()
    schema = _testreg_schema(REPO)
    bad = [f"{k}: {e}" for k, v in (("quarantined_failures", quarantined), ("tombstone_resolutions", tomb_rows))
           for e in tr.validate_shape(v, schema["gate_report"]["fields"][k], schema, k)]
    if bad:
        raise GateError(f"verdict 收據欄驗證不符：{bad[:5]}")
    receipt = {
        "spec": "docs/FRAMEPATH_SPEC.md v22 D8＋D11", "phase": args.phase, "repo_head": _git(REPO, "rev-parse", "HEAD").strip(),
        "selection": {"selected": sel["selected"], "skipped": sel["skipped"], "s2_symbols": sel["s2_symbols"],
                      "align_triggered": sel["align_triggered"], "light_files": sel["light_files"],
                      "invariance_baseline_sha256": sel["invariance_baseline_sha256"],
                      "inputs_digest": sel["inputs_digest"], "admission": adm, "admitted": args.admit is not None,
                      "empty_collect": sel.get("empty_collect", []),  # 審查 r63 CODEX-R63-P2-02
                      "hardware_blocked": sel.get("hardware_blocked", {})},  # SPEC v25 D14
        "residual_defs": sel["residual_defs"], "residual_executed": sorted(hits & set(sel["residual_defs"])),
        "residual_unexecuted": unexecuted,
        "anchor": anchor, "anchor_worktree": str(anchor_wt), "groups": {"A": list(a_files),
                                                                        "B": b_group, "C": c_group},
        "a_failures": a_failures, "incomplete_files": incomplete, "per_file": per_file,
        "expected_count": len(expected), "result_count": len(set(expected) & set(batch)),
        **result,
        "head_red_identity": {n: list(failure_identity(batch[n])) for n in result["head_red"]},
        "caused_detail": {n: {"batch": list(failure_identity(batch[n])),
                              "anchor": list(failure_identity(anchor_res[n])) if n in anchor_res else None}
                          for n in result["caused"]},
        "quarantined_failures": quarantined, "tombstone_resolutions": tomb_rows,
        "pass": passed,
    }
    Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"FRAMEPATH affected gate：A_fail={len(a_failures)} expected={len(expected)} incomplete={len(incomplete)} "
          f"missing={len(result['missing'])} unexpected={len(result['unexpected'])} caused={len(result['caused'])} "
          f"head_red={len(result['head_red'])} pass={passed}")
    return 0 if passed else 1


_RUNNER: Optional[Runner] = None
PAUSED_RC = 3

if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Paused as exc:
        if _RUNNER is not None:
            _RUNNER.progress("paused", "", [], state="paused")
        print(f"FRAMEPATH affected gate：PAUSED（{exc}）；已完成之結果已保留，以同一命令接續")
        raise SystemExit(PAUSED_RC)
