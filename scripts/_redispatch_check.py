#!/usr/bin/env python3
"""_redispatch_check.py — 同輪同家重派之唯一判定實作（票 B-64，SPEC v12 Task 1.1–1.8）。

六個模式：
  issue            發放綁定許可（gate.sh redispatch 早分支呼叫）
  consume          PreToolUse 放行並消費許可（gate_check.sh 呼叫；指令自 stdin 原樣讀入）
  exhausted-check  重派上限耗盡查核（debt_clear.sh --abandon collection-failed 呼叫）
  path-check       路徑 token 文法（供 committee_run.sh 之內嵌 bash 版做語意對照）
  lease            派工器行程租約與認領（cx_run.sh re-exec 呼叫）
  archive-check    銷帳時保存檔之逐條處置查核（debt_clear.sh 呼叫）

單一真相源：事件名／欄位／常數只定義於 scripts/audit_events.json；
路徑 token 文法、嘗試狀態、租約路徑、認領規則、已交件判準、前次產出查核、
保存檔處置查核只定義於本檔（SPEC §C）。
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
FAMILY_RE = re.compile(r"[a-z]+")
BARE_RE = re.compile(r"[A-Za-z0-9._/+][A-Za-z0-9._/+-]*")
_TOKEN = r"(?:[A-Za-z0-9._/+][A-Za-z0-9._/+-]*|'[^'\r\n\x00\-][^'\r\n\x00]*')"
CMD_RE = re.compile(
    r"ROUND_ID=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}) "
    r"bash scripts/cx_run\.sh ([a-z]+) (" + _TOKEN + r") (" + _TOKEN + r")"
)
BLOCKING = {"pending", "launching", "running"}
NON_SUCCESS = {"failed", "format-failed", "verdict_rejected"}
# 已交件判準呼叫 completeness_check.sh 時須濾除之逃生口旗標（SPEC §A：會翻轉同一檔之 rc）
_ENV_DROP_PREFIX = "COMPLETENESS_"
_ENV_DROP_KEYS = {"ID_PATTERN", "ALLOW_ID_PATTERN_OVERRIDE"}


# ── 基礎 ────────────────────────────────────────────────────────────────
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def registry(repo: Path) -> dict:
    return json.loads((repo / "scripts" / "audit_events.json").read_text(encoding="utf-8"))


def constants(repo: Path) -> dict:
    return registry(repo).get("constants") or {}


def harness() -> bool:
    return os.environ.get("GOVERNANCE_TEST_HARNESS") == "1"


def audit_path(repo: Path) -> Path:
    override = os.environ.get("DEBT_AUDIT_OVERRIDE")
    if override:
        if not harness():
            die("DEBT_AUDIT_OVERRIDE 僅允許 GOVERNANCE_TEST_HARNESS=1（fail-closed）")
        return Path(override)
    rel = registry(repo).get("audit_log_path") or ".claude/gate/audit.log"
    return repo / rel


def gate_dir(repo: Path) -> Path:
    """回傳閘目錄；**不建立**（早分支在輸入驗證通過前不得觸碰檔案系統）。"""
    override = os.environ.get("GATE_DIR_OVERRIDE")
    return Path(override) if override else repo / ".claude" / "gate"


def die(msg: str, rc: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(rc)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def test_hook(name: str) -> None:
    """僅測試用之掛鉤：執行 env 指定之指令（供驗證「查核與動作之間」之不變式）。

    未綁 GOVERNANCE_TEST_HARNESS=1 而設定 ⇒ fail-closed（rc=2），不得成為正式路徑之逃生口。
    """
    cmd = os.environ.get(name)
    if not cmd:
        return
    if not harness():
        die(f"{name} 僅允許 GOVERNANCE_TEST_HARNESS=1（fail-closed）")
    subprocess.run(["bash", "-c", cmd])


def fault(point: str) -> None:
    """僅測試用故障注入點；未綁 harness 而設定 ⇒ fail-closed。"""
    want = os.environ.get("REDISPATCH_FAULT_POINT")
    if not want:
        return
    if not harness():
        die("REDISPATCH_FAULT_POINT 僅允許 GOVERNANCE_TEST_HARNESS=1（fail-closed）")
    if want == point:
        os._exit(137)


# ── 路徑 token 文法 ─────────────────────────────────────────────────────
def path_token_ok(p: str) -> bool:
    if not p or p.startswith("-"):
        return False
    return not any(c in p for c in ("'", "\r", "\n", "\x00"))


def render_path_token(p: str) -> str:
    return p if BARE_RE.fullmatch(p) else "'" + p + "'"


def unquote(tok: str) -> str:
    return tok[1:-1] if len(tok) >= 2 and tok[0] == "'" and tok[-1] == "'" else tok


# ── 讀取層 ──────────────────────────────────────────────────────────────
def load_events(p: Path) -> List[dict]:
    if not p.is_file():
        return []
    out: List[dict] = []
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s.startswith("{"):
            continue
        try:
            out.append(json.loads(s))
        except json.JSONDecodeError:
            continue
    return out


def ledger_rounds(repo: Path) -> Dict[str, dict]:
    """債務帳本之輪層資訊（state／participants／open.expected_outputs）。

    🔴 其 latest_results 投影只有四欄（SPEC §A：_debt_ledger_core.py:313-326），
       **不得**作為結果列來源；結果列一律用 latest_result()。
    """
    env = dict(os.environ)
    env.update(
        DEBT_LEDGER_MODE="dump_json",
        DEBT_LEDGER_ROUND_ID="",
        DEBT_LEDGER_REGISTRY=str(repo / "scripts" / "audit_events.json"),
        DEBT_LEDGER_REPO=str(repo),
    )
    proc = subprocess.run(
        [sys.executable, "-S", str(repo / "scripts" / "_debt_ledger_core.py")],
        capture_output=True, text=True, env=env,
    )
    if proc.returncode != 0:
        die(f"讀帳本失敗（rc={proc.returncode}）：{(proc.stderr or '')[-300:]}")
    try:
        rounds = (json.loads(proc.stdout) or {}).get("rounds") or {}
    except json.JSONDecodeError as exc:
        die(f"帳本輸出非 JSON：{exc}")
        return {}
    # 欄位可能以 JSON 字串形態寫入 audit（--field k=v）或以物件形態（--field k=@json）⇒ 統一正規化
    for info in rounds.values():
        for holder, key in ((info, "participants"), (info.get("open") or {}, "participants"),
                            (info.get("open") or {}, "expected_outputs")):
            val = holder.get(key)
            if isinstance(val, str):
                try:
                    holder[key] = json.loads(val)
                except json.JSONDecodeError:
                    pass
    return rounds


def stampers(repo: Path) -> List[str]:
    """本期實際要求蓋章之家族（三態，同 families_active_stampers）。"""
    fams = json.loads((repo / "scripts" / "governance_families.json").read_text(encoding="utf-8"))
    review = fams.get("review_families") or []
    if "active_stampers" not in fams:
        return list(review)                      # 缺 key ⇒ 回退 review_families
    active = fams.get("active_stampers")
    ok = (
        isinstance(active, list) and active
        and all(isinstance(x, str) and x for x in active)
        and len(set(active)) == len(active)
        and set(active) <= set(review)
    )
    if not ok:
        die("active_stampers 不合法（fail-closed，不回退全員）")
    return list(active)


def review_families(repo: Path) -> List[str]:
    fams = json.loads((repo / "scripts" / "governance_families.json").read_text(encoding="utf-8"))
    return list(fams.get("review_families") or [])


def latest_result(events: Sequence[dict], rid: str, fam: str) -> Optional[dict]:
    """該（輪、家族）最後一筆 committee_family_result（含非必填欄）。"""
    rec = None
    for e in events:
        if e.get("event") == "committee_family_result" and e.get("round_id") == rid and e.get("family") == fam:
            rec = e
    return rec


def outputs_of(events: Sequence[dict], rid: str, fam: str) -> List[dict]:
    return [
        e for e in events
        if e.get("event") == "committee_output" and e.get("round_id") == rid and e.get("family") == fam
    ]


def epoch_of(ev: dict) -> float:
    ts = (ev.get("ts") or ev.get("timestamp") or "").replace("Z", "+00:00")
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(ts).timestamp()
    except Exception:
        return 0.0


# ── 鎖與租約 ────────────────────────────────────────────────────────────
@contextmanager
def permit_lock(gdir: Path, rid: str, fam: str):
    gdir.mkdir(parents=True, exist_ok=True)
    lock = gdir / f"redispatch.{rid}.{fam}.lock"
    fh = open(lock, "a")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def lease_path(repo: Path, rid: str, fam: str) -> Path:
    digest = hashlib.sha256(f"{rid}\0{fam}".encode("utf-8")).hexdigest()[:32]
    return audit_path(repo).parent / f"redispatch.lease.{digest}"


def lease_held(repo: Path, rid: str, fam: str) -> bool:
    lp = lease_path(repo, rid, fam)
    lp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lp), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


# ── 嘗試狀態 ────────────────────────────────────────────────────────────
def attempt_states(repo: Path, events: Sequence[dict], rid: str, fam: str,
                   now_epoch: float, consts: dict) -> List[Tuple[dict, str]]:
    ttl = float(consts.get("redispatch_token_ttl_seconds", 900))
    grace = float(consts.get("redispatch_launch_grace_seconds", 120))
    issued = [e for e in events
              if e.get("event") == "redispatch_token_issued"
              and e.get("round_id") == rid and e.get("family") == fam]
    consumed = {e.get("issue_nonce"): e for e in events if e.get("event") == "redispatch_token_consumed"}
    claimed = {e.get("issue_nonce"): e for e in events if e.get("event") == "redispatch_token_claimed"}
    results = [e for e in events
               if e.get("event") == "committee_family_result"
               and e.get("round_id") == rid and e.get("family") == fam]
    out: List[Tuple[dict, str]] = []
    for e in issued:
        nonce = e.get("issue_nonce")
        c = consumed.get(nonce)
        k = claimed.get(nonce)
        if c is None:
            out.append((e, "pending" if now_epoch - epoch_of(e) <= ttl else "unused"))
            continue
        if k is None:
            out.append((e, "launching" if now_epoch - epoch_of(c) <= grace else "not_launched"))
            continue
        kseq = k.get("sequence") or 0
        if any((r.get("sequence") or 0) > kseq for r in results):
            out.append((e, "done"))
        elif lease_held(repo, rid, fam):
            out.append((e, "running"))
        else:
            out.append((e, "lost"))
    return out


# ── 已交件判準與前次產出查核 ────────────────────────────────────────────
def _clean_env() -> dict:
    return {
        k: v for k, v in os.environ.items()
        if not k.startswith(_ENV_DROP_PREFIX) and k not in _ENV_DROP_KEYS
    }


def delivered(repo: Path, events: Sequence[dict], rounds: Dict[str, dict], rid: str, fam: str) -> bool:
    """該家是否已交件（三判準全滿足才算）。"""
    outs = outputs_of(events, rid, fam)
    if not outs:
        return False
    ev = outs[-1]
    expected = ((rounds.get(rid) or {}).get("open") or {}).get("expected_outputs") or {}
    out_rel = ev.get("output_path") or ""
    if not out_rel or out_rel != expected.get(fam):
        return False                              # (i) 路徑須等於該輪 expected
    q = repo / out_rel
    try:
        if q.is_symlink() or not q.is_file():
            return False
        q.resolve().relative_to(repo.resolve())
    except (OSError, ValueError):
        return False
    try:
        if sha256_file(q) != (ev.get("output_sha256") or ""):
            return False                          # (ii) 實體檔雜湊須等於登記值
    except OSError:
        return False
    proc = subprocess.run(                        # (iii) 與銷帳出口同一命令；cwd 固定 repo、濾除逃生口旗標
        ["bash", str(repo / "scripts" / "completeness_check.sh"), "--single", str(q), "--family", fam],
        capture_output=True, text=True, cwd=str(repo), env=_clean_env(),
    )
    return proc.returncode == 0


def archive_path(repo: Path, rid: str, fam: str, attempt: int) -> Path:
    return repo / "handoffs" / "redispatch_archive" / rid / f"{fam}-attempt{attempt}.md"


def prev_output_check(repo: Path, latest: dict, out_rel: str) -> Tuple[Optional[str], Optional[str]]:
    """回傳 (違規字串 or None, 產出檔實際 sha256 or None)。"""
    expect = (latest.get("output_sha256") or "") or (latest.get("partial_output_sha256") or "")
    q = repo / out_rel
    if not expect:
        return (None, None)                       # 無前次產出
    try:
        if q.is_symlink() or not q.is_file() or q.stat().st_size == 0:
            return (f"⑤前次產出已登記雜湊但檔案缺失、截零或不可讀：{out_rel}", None)
        q.resolve().relative_to(repo.resolve())
    except (OSError, ValueError):
        return (f"⑤前次產出路徑不可用或不在 repo 內：{out_rel}", None)
    actual = sha256_file(q)
    if actual != expect:
        return (f"⑤產出檔於結果列後被改動：{out_rel}", None)
    return (None, actual)


# ── 發放條件 ────────────────────────────────────────────────────────────
def issue_violations(repo: Path, events: Sequence[dict], rounds: Dict[str, dict], rid: str,
                     fam: str, now_epoch: float, consts: dict, active: Sequence[str]) -> List[str]:
    v: List[str] = []
    open_set = {r for r, info in rounds.items() if (info.get("state") or "") == "OPEN"}
    if open_set != {rid}:
        v.append(f"①OPEN 集合須恰為該輪：{sorted(open_set)}")
    info = rounds.get(rid) or {}
    opens = [e for e in events if e.get("event") == "committee_round_open" and e.get("round_id") == rid]
    expected = (info.get("open") or {}).get("expected_outputs") or {}
    participants = info.get("participants") or []
    if len(opens) != 1:
        v.append(f"②該輪 committee_round_open 須唯一（實得 {len(opens)}）")
    if fam not in participants or fam not in expected:
        v.append(f"②家族不在該輪 participants／expected_outputs：{fam}")
    latest = latest_result(events, rid, fam)
    if latest is None or (latest.get("result_state") or "") not in NON_SUCCESS:
        v.append(f"③該家最新結果須為 {sorted(NON_SUCCESS)}（實得 {latest and latest.get('result_state')}）")
    if delivered(repo, events, rounds, rid, fam):
        v.append("④該家已交件（出路為既有銷帳，不得重派）")
    out_rel = expected.get(fam) or ""
    if latest is not None and out_rel:
        bad, _ = prev_output_check(repo, latest, out_rel)
        if bad:
            v.append(bad)
    if fam not in set(active):
        v.append(f"⑥家族不在 active_stampers：{fam}")
    issued = [e for e in events
              if e.get("event") == "redispatch_token_issued"
              and e.get("round_id") == rid and e.get("family") == fam]
    if len(issued) >= int(consts.get("redispatch_max_attempts", 6)):
        v.append(f"⑦重派次數已達上限 {consts.get('redispatch_max_attempts')}（已發 {len(issued)}）")
    if issued:
        gap = now_epoch - epoch_of(issued[-1])
        need = float(consts.get("redispatch_min_interval_seconds", 600))
        if gap < need:
            v.append(f"⑧距前次發放未逾 {int(need)} 秒（已過 {int(gap)} 秒）")
    states = [s for _, s in attempt_states(repo, events, rid, fam, now_epoch, consts)]
    if "pending" in states:
        v.append("⑨已有待用之許可")
    brief_path = (opens[0].get("brief_path") if opens else "") or ""
    if out_rel:
        q = repo / out_rel
        if q.is_symlink():
            v.append(f"⑩登記產出路徑為 symlink：{out_rel}")
    if "launching" in states or "running" in states or lease_held(repo, rid, fam):
        v.append("⑪同（輪、家族）有啟動中／執行中之派工器")
    if not brief_path or not path_token_ok(brief_path) or not out_rel or not path_token_ok(out_rel):
        v.append("⑫該輪 brief 或產出路徑無法以放行文法表示")
    return v


# ── issue ───────────────────────────────────────────────────────────────
def cmd_issue(argv: List[str]) -> int:
    rid = fam = reason = ""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--round-id" and i + 1 < len(argv):
            rid = argv[i + 1]; i += 2
        elif a == "--family" and i + 1 < len(argv):
            fam = argv[i + 1]; i += 2
        elif a == "--reason" and i + 1 < len(argv):
            reason = argv[i + 1]; i += 2
        else:
            print(f"ERROR: redispatch 未知或不完整之參數：{a}", file=sys.stderr)
            return 2
    repo = repo_root()
    consts = constants(repo)
    if not UUID_RE.fullmatch(rid):
        print("ERROR: --round-id 須為小寫 UUID", file=sys.stderr); return 2
    if not FAMILY_RE.fullmatch(fam) or fam not in review_families(repo):
        print(f"ERROR: --family 不在 review_families：{fam}", file=sys.stderr); return 2
    if len(reason) < int(consts.get("reason_min_chars", 20)):
        print(f"ERROR: --reason 須至少 {consts.get('reason_min_chars', 20)} 字", file=sys.stderr); return 2

    gdir = gate_dir(repo)
    ap = audit_path(repo)
    with permit_lock(gdir, rid, fam):
        events = load_events(ap)
        rounds = ledger_rounds(repo)
        active = stampers(repo)
        now = time.time()
        viol = issue_violations(repo, events, rounds, rid, fam, now, consts, active)
        if viol:
            for x in viol:
                print(f"ERROR: {x}", file=sys.stderr)
            if any(x.startswith("⑦") for x in viol):
                print(
                    "提示：上限已耗盡 ⇒ 改走棄置："
                    f"bash scripts/debt_clear.sh --abandon --round-id {rid} "
                    "--kind collection-failed --reason <文字> --approver <文字>",
                    file=sys.stderr,
                )
            return 1

        info = rounds.get(rid) or {}
        opens = [e for e in events if e.get("event") == "committee_round_open" and e.get("round_id") == rid]
        brief_path = opens[0].get("brief_path") or ""
        brief_sha = opens[0].get("brief_sha256") or ""
        out_rel = ((info.get("open") or {}).get("expected_outputs") or {}).get(fam) or ""
        latest = latest_result(events, rid, fam) or {}
        attempt = len([e for e in events
                       if e.get("event") == "redispatch_token_issued"
                       and e.get("round_id") == rid and e.get("family") == fam]) + 1

        # 🔴 第二次查核之違規不得忽略（b1 review-r1 CODEX-R1-P1-02）：
        #    條件判定與保存之間若產出檔被刪或截零，忽略 bad 會誤判成「無前次產出」而不保存。
        bad, actual = prev_output_check(repo, latest, out_rel)
        if bad:
            print(f"ERROR: {bad}", file=sys.stderr)
            return 1
        test_hook("REDISPATCH_TEST_BEFORE_ARCHIVE_CMD")   # 僅測試：於查核後、保存前插入動作
        bad, actual = prev_output_check(repo, latest, out_rel)
        if bad:
            print(f"ERROR: {bad}", file=sys.stderr)
            return 1
        if actual is None:
            prev_sha, prev_arc = "none", "none"
        else:
            arc = archive_path(repo, rid, fam, attempt)
            arc.parent.mkdir(parents=True, exist_ok=True)
            fd0, tmp0 = tempfile.mkstemp(dir=str(arc.parent), suffix=".tmp")
            os.close(fd0)
            shutil.copyfile(str(repo / out_rel), tmp0)
            os.replace(tmp0, str(arc))
            fault("after_archive_write")
            if sha256_file(arc) != actual:
                arc.unlink(missing_ok=True)
                print("ERROR: 保存檔雜湊與產出檔不符（已刪保存檔）", file=sys.stderr)
                return 1
            prev_sha, prev_arc = actual, str(arc.relative_to(repo))

        nonce = str(uuid.uuid4())
        secret = secrets.token_hex(32)
        token_path = gdir / f"redispatch.{rid}.{fam}.token"
        fd, tmp = tempfile.mkstemp(dir=str(gdir), prefix=f"redispatch.{rid}.{fam}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for k, val in (
                ("nonce", nonce), ("secret", secret), ("round_id", rid), ("family", fam),
                ("brief_path", brief_path), ("brief_sha256", brief_sha), ("output_path", out_rel),
                ("attempt_no", str(attempt)), ("issued_epoch", str(int(now))),
                ("prev_output_sha256", prev_sha), ("prev_output_archive", prev_arc),
            ):
                fh.write(f"{k}={val}\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, str(token_path))
        fault("after_token_write")
        rc = subprocess.run(
            ["bash", str(repo / "scripts" / "audit_append.sh"),
             "--event", "redispatch_token_issued",
             "--field", f"round_id={rid}", "--field", f"family={fam}",
             "--field", f"attempt_no={attempt}",
             "--field", f"brief_path={brief_path}", "--field", f"brief_sha256={brief_sha}",
             "--field", f"output_path={out_rel}", "--field", f"reason={reason}",
             "--field", f"issue_nonce={nonce}",
             "--field", f"permit_secret_sha256={sha256_bytes(secret.encode())}",
             "--field", f"prev_output_sha256={prev_sha}",
             "--field", f"prev_output_archive={prev_arc}",
             "--field", "actor=gate", "--field", "origin_script=gate.sh"],
        ).returncode
        if rc != 0:
            token_path.unlink(missing_ok=True)
            print("ERROR: 發放事件寫入失敗（已刪許可檔）", file=sys.stderr)
            return 1
    print(f"ROUND_ID={rid} bash scripts/cx_run.sh {fam} "
          f"{render_path_token(brief_path)} {render_path_token(out_rel)}")
    return 0


# ── consume ─────────────────────────────────────────────────────────────
def parse_command(raw: str, fams: Sequence[str]) -> Optional[Tuple[str, str, str, str]]:
    m = CMD_RE.fullmatch(raw)
    if not m or m.group(2) not in fams:
        return None
    return m.group(1), m.group(2), unquote(m.group(3)), unquote(m.group(4))


def _read_token(p: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        k, _, v = line.partition("=")
        out[k] = v
    return out


def cmd_consume(_argv: List[str]) -> int:
    raw = sys.stdin.read()
    repo = repo_root()
    parsed = parse_command(raw, review_families(repo))
    if parsed is None:
        return 3                                   # 不適用本路徑（照既有判定）
    rid, fam, brief, out_rel = parsed
    consts = constants(repo)
    gdir = gate_dir(repo)
    ap = audit_path(repo)
    with permit_lock(gdir, rid, fam):
        token_path = gdir / f"redispatch.{rid}.{fam}.token"
        if not token_path.is_file():
            print("ERROR: 無對應之重派許可檔", file=sys.stderr); return 1
        tok = _read_token(token_path)
        if (tok.get("round_id"), tok.get("family"), tok.get("brief_path"), tok.get("output_path")) != (rid, fam, brief, out_rel):
            print("ERROR: 許可四欄與指令不符", file=sys.stderr); return 1
        events = load_events(ap)
        issued = [e for e in events
                  if e.get("event") == "redispatch_token_issued" and e.get("issue_nonce") == tok.get("nonce")]
        if len(issued) != 1:
            print("ERROR: 許可 nonce 之發放事件不唯一", file=sys.stderr); return 1
        now = time.time()
        states = {id(e): s for e, s in attempt_states(repo, events, rid, fam, now, consts)}
        if states.get(id(issued[0])) != "pending":
            cur = states.get(id(issued[0]))
            print(f"ERROR: 許可非待用狀態（{cur}）", file=sys.stderr); return 1
        if sha256_bytes((tok.get("secret") or "").encode()) != (issued[0].get("permit_secret_sha256") or ""):
            print("ERROR: 許可秘密不符", file=sys.stderr); return 1
        # 🔴 許可檔之所有綁定欄須與**發放事件**逐欄相等（B-64 b1 review-r1 CODEX-R1-P1-01）：
        #    只比對「許可 vs 指令」不足——竄改許可檔之 prev_output_* 即可讓保存檔綁定失效。
        _ev = issued[0]
        for _k in ("round_id", "family", "brief_path", "brief_sha256", "output_path",
                   "attempt_no", "prev_output_sha256", "prev_output_archive"):
            if (tok.get(_k) or "") != str(_ev.get(_k) or ""):
                print(f"ERROR: 許可欄位與發放事件不符：{_k}", file=sys.stderr); return 1
        try:
            if sha256_file(repo / brief) != (tok.get("brief_sha256") or ""):
                print("ERROR: brief 已於發放後改動", file=sys.stderr); return 1
        except OSError:
            print("ERROR: brief 讀取失敗", file=sys.stderr); return 1
        rounds = ledger_rounds(repo)
        active = stampers(repo)
        viol = [x for x in issue_violations(repo, events, rounds, rid, fam, now, consts, active)
                if not x.startswith(("⑦", "⑧", "⑨"))]
        # ⑨（待用）本身即本許可，⑦⑧為發放端節流，消費端不再套用
        if viol:
            for x in viol:
                print(f"ERROR: {x}", file=sys.stderr)
            return 1
        prev_arc = tok.get("prev_output_archive") or "none"
        if prev_arc != "none":
            arc = repo / prev_arc
            try:
                if arc.is_symlink() or not arc.is_file() or sha256_file(arc) != (tok.get("prev_output_sha256") or ""):
                    print("ERROR: 保存檔缺失或已被改動", file=sys.stderr); return 1
                arc.resolve().relative_to(repo.resolve())
            except (OSError, ValueError):
                print("ERROR: 保存檔不可讀或不在 repo 內", file=sys.stderr); return 1
        try:
            os.rename(str(token_path), str(token_path) + ".consumed")
        except OSError as exc:
            print(f"ERROR: 許可改名失敗：{exc}", file=sys.stderr); return 1
        fault("after_rename")
        rc = subprocess.run(
            ["bash", str(repo / "scripts" / "audit_append.sh"),
             "--event", "redispatch_token_consumed",
             "--field", f"round_id={rid}", "--field", f"family={fam}",
             "--field", f"issue_nonce={tok.get('nonce')}",
             "--field", f"command_sha256={sha256_bytes(raw.encode())}",
             "--field", "actor=gate_check", "--field", "origin_script=gate_check.sh"],
        ).returncode
        if rc != 0:
            print("ERROR: 消費事件寫入失敗", file=sys.stderr); return 1
    return 0


# ── exhausted-check ─────────────────────────────────────────────────────
def exhausted_violations(repo: Path, events: Sequence[dict], rounds: Dict[str, dict], rid: str,
                         now_epoch: float, consts: dict, active: Sequence[str]) -> Dict[str, List[str]]:
    info = rounds.get(rid) or {}
    out: Dict[str, List[str]] = {}
    expected = (info.get("open") or {}).get("expected_outputs") or {}
    for fam in info.get("participants") or []:
        v: List[str] = []
        if (info.get("state") or "") != "OPEN":
            v.append("輪非 OPEN")
        if fam not in set(active):
            v.append("家族不在 active_stampers")
        issued = [e for e in events
                  if e.get("event") == "redispatch_token_issued"
                  and e.get("round_id") == rid and e.get("family") == fam]
        if len(issued) < int(consts.get("redispatch_max_attempts", 6)):
            v.append(f"重派次數未達上限（{len(issued)}）")
        states = [s for _, s in attempt_states(repo, events, rid, fam, now_epoch, consts)]
        if set(states) & BLOCKING or lease_held(repo, rid, fam):
            v.append("仍有待用／啟動中／執行中之嘗試")
        latest = latest_result(events, rid, fam)
        if latest is None or (latest.get("result_state") or "") not in NON_SUCCESS:
            v.append("最新結果非 failed／format-failed／verdict_rejected")
        if delivered(repo, events, rounds, rid, fam):
            v.append("該家已交件")
        out_rel = expected.get(fam) or ""
        if latest is not None and out_rel:
            bad, _ = prev_output_check(repo, latest, out_rel)
            if bad:
                v.append(bad)
            if (repo / out_rel).is_symlink():
                v.append("登記產出路徑為 symlink")
        out[fam] = v
    return out


def cmd_exhausted_check(argv: List[str]) -> int:
    rid = ""
    i = 0
    while i < len(argv):
        if argv[i] == "--round-id" and i + 1 < len(argv):
            rid = argv[i + 1]; i += 2
        else:
            i += 1
    repo = repo_root()
    if not UUID_RE.fullmatch(rid):
        print("ERROR: --round-id 須為小寫 UUID", file=sys.stderr); return 2
    events = load_events(audit_path(repo))
    rounds = ledger_rounds(repo)
    consts = constants(repo)
    active = stampers(repo)
    # 🔴 查核與快照須在（輪、家族）鎖內完成（b1 review-r1 CODEX-R1-P1-03）：
    #    否則查核期間可並發發放／認領；寫入端另以 --require-round-unchanged 擋查核後之遲到事件。
    from contextlib import ExitStack
    gdir = gate_dir(repo)
    with ExitStack() as stack:
        for fam in (rounds.get(rid) or {}).get("participants") or []:
            stack.enter_context(permit_lock(gdir, rid, fam))
        test_hook("REDISPATCH_TEST_IN_EXHAUSTED_LOCK_CMD")   # 僅測試：於鎖內觀測鎖是否真被持有
        per_family = exhausted_violations(repo, events, rounds, rid, time.time(), consts, active)
        ok_fams = [f for f, v in per_family.items() if not v]
        if ok_fams:
            seqs = [e.get("sequence") or 0 for e in events if e.get("round_id") == rid]
            print(f"snapshot_sequence={max(seqs) if seqs else 0}")
            # 🔴 快照另綁該家產出檔雜湊（b1 review-r2 CODEX-R2-P1-01）：
            #    只綁 audit 序號時，查核後改寫產出仍可棄置；寫入端於同一鎖內重驗此綁定。
            fam0 = ok_fams[0]
            out_rel = ((rounds.get(rid) or {}).get("open") or {}).get("expected_outputs", {}).get(fam0) or ""
            q = repo / out_rel
            # 🔴 路徑與雜湊分兩行輸出（b1 review-r3 CODEX-R3-P1-02）：合法路徑可含 `@`，
            #    以單一 <path>@<sha> 傳遞會與路徑文法衝突而誤擋合法棄置。
            try:
                st = q.lstat()
                sha = sha256_file(q) if (not q.is_symlink() and st.st_size > 0) else "none"
            except OSError:
                sha = "none"
            print(f"snapshot_output_path={out_rel}")
            print(f"snapshot_output_sha={sha}")
            return 0
    for fam, v in per_family.items():
        for x in v:
            print(f"ERROR: [{fam}] {x}", file=sys.stderr)
    return 1


# ── path-check ──────────────────────────────────────────────────────────
def cmd_path_check(argv: List[str]) -> int:
    for p in argv:
        if not path_token_ok(p):
            print(f"ERROR: 路徑無法以重派放行文法表示：{p!r}", file=sys.stderr)
            return 2
    return 0


# ── lease ───────────────────────────────────────────────────────────────
def claim_if_pending(repo: Path, gdir: Path, rid: str, fam: str, now_epoch: float, consts: dict) -> int:
    if not (UUID_RE.fullmatch(rid) and FAMILY_RE.fullmatch(fam)):
        return 0
    with permit_lock(gdir, rid, fam):
        p = gdir / f"redispatch.{rid}.{fam}.token.consumed"
        if not p.is_file():
            return 0
        nonce = _read_token(p).get("nonce") or ""
        events = load_events(audit_path(repo))
        c = next((e for e in events
                  if e.get("event") == "redispatch_token_consumed" and e.get("issue_nonce") == nonce), None)
        k = next((e for e in events
                  if e.get("event") == "redispatch_token_claimed" and e.get("issue_nonce") == nonce), None)
        if c is None or k is not None:
            p.unlink(missing_ok=True)
            return 0
        grace = float(consts.get("redispatch_launch_grace_seconds", 120))
        if now_epoch - epoch_of(c) > grace:
            os.rename(str(p), str(p)[: -len(".consumed")] + ".expired")
            print("ERROR: 重派許可已逾啟動寬限，不執行", file=sys.stderr)
            return 2
        rc = subprocess.run(
            ["bash", str(repo / "scripts" / "audit_append.sh"),
             "--event", "redispatch_token_claimed",
             "--field", f"round_id={rid}", "--field", f"family={fam}",
             "--field", f"issue_nonce={nonce}",
             "--field", "actor=cx_run", "--field", "origin_script=cx_run.sh"],
        ).returncode
        if rc != 0:
            return 2
        os.rename(str(p), str(p)[: -len(".consumed")] + ".claimed")
        return 0


def cmd_lease(argv: List[str]) -> int:
    rid = fam = ""
    cmd: List[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--round-id" and i + 1 < len(argv):
            rid = argv[i + 1]; i += 2
        elif a == "--family" and i + 1 < len(argv):
            fam = argv[i + 1]; i += 2
        elif a == "--":
            cmd = list(argv[i + 1:]); break
        else:
            i += 1
    if not rid or not fam or not cmd:
        print("用法: _redispatch_check.py lease --round-id <id> --family <fam> -- <cmd...>", file=sys.stderr)
        return 2
    repo = repo_root()
    lp = lease_path(repo, rid, fam)
    lp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lp), os.O_CREAT | os.O_RDWR, 0o600)
    for _ in range(20):
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            time.sleep(0.1)
    else:
        print("ERROR: 同（輪、家族）已有派工器執行中", file=sys.stderr)
        os.close(fd)
        return 2
    if claim_if_pending(repo, gate_dir(repo), rid, fam, time.time(), constants(repo)) != 0:
        return 2
    os.set_inheritable(fd, True)
    env = dict(os.environ, CX_RUN_LEASE_HELD="1")
    os.execvpe(cmd[0], cmd, env)
    return 2                                       # unreachable


# ── archive-check ───────────────────────────────────────────────────────
def archive_violations(repo: Path, events: Sequence[dict], rid: str, synth_text: str,
                       values: Sequence[str]) -> List[str]:
    sys.path.insert(0, str(repo / "scripts"))
    import _synth_attr as SA                        # 只用既有 API，不改該檔

    evs = [e for e in events
           if e.get("event") == "redispatch_token_issued" and e.get("round_id") == rid
           and (e.get("prev_output_archive") or "none") not in ("", "none")]
    if not evs:
        return []
    head = synth_text.partition("## 附錄")[0]
    doc = SA.parse_synth(synth_text, "")
    errs: List[str] = []
    for e in evs:
        p = e.get("prev_output_archive")
        q = repo / p
        try:
            if q.is_symlink() or not q.is_file():
                errs.append(f"保存檔缺失或非一般檔：{p}"); continue
            q.resolve().relative_to(repo.resolve())
            raw = q.read_bytes()
        except (OSError, ValueError):
            errs.append(f"保存檔不可讀或不在 repo 內：{p}"); continue
        if sha256_bytes(raw) != (e.get("prev_output_sha256") or ""):
            errs.append(f"保存檔已被改動：{p}"); continue
        if p not in head:
            errs.append(f"收斂檔群集段未引用保存檔：{p}")
        try:
            body = raw.decode("utf-8"); lossy = False
        except UnicodeDecodeError:
            body = raw.decode("utf-8", errors="replace"); lossy = True
        fs = SA.parse_synth("## 附錄\n" + body, "").findings
        disp_rows = [r for r in doc.rows
                     if not r.placeholder and len(r.cells) >= 4
                     and any(SA._token_whole(r.cells[3], v) for v in values)]
        if lossy and not fs:
            if not any(p in " ".join(r.cells) for r in disp_rows):
                errs.append(f"保存檔解碼有損且無標號 ⇒ 收斂檔須有同時含其路徑與處置 token 之群集列：{p}")
        for f in fs:
            rows = [r for r in disp_rows if SA._id_in(" ".join(r.cells), f.id)]
            if not rows:
                errs.append(f"保存檔 {p} 之 {f.id} 無含處置 token 之非佔位群集列"); continue
            qq = SA.nfc_strip(f.assertion)[: SA.QUOTE_N]
            if lossy or not qq:
                continue                            # 空字串／替代字元不得進入引用比對
            if not any(qq in SA.nfc_strip(" ".join(r.cells)) for r in rows):
                errs.append(f"保存檔 {p} 之 {f.id} 無逐字引用斷言前 {SA.QUOTE_N} 字之群集列")
    return errs


def cmd_archive_check(argv: List[str]) -> int:
    rid = synth = ""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--round-id" and i + 1 < len(argv):
            rid = argv[i + 1]; i += 2
        elif a == "--synth" and i + 1 < len(argv):
            synth = argv[i + 1]; i += 2
        else:
            i += 1
    repo = repo_root()
    if not UUID_RE.fullmatch(rid):
        print("ERROR: --round-id 須為小寫 UUID", file=sys.stderr); return 2
    try:
        synth_text = Path(synth).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: 收斂檔讀取失敗：{exc}", file=sys.stderr); return 2
    sys.path.insert(0, str(repo / "scripts"))
    import _synth_attr as SA
    values = SA.load_values(str(repo / "scripts" / "governance_verdicts.json"))
    errs = archive_violations(repo, load_events(audit_path(repo)), rid, synth_text, values)
    for x in errs:
        print(f"ERROR: {x}", file=sys.stderr)
    return 1 if errs else 0


_MODES = {
    "issue": cmd_issue,
    "consume": cmd_consume,
    "exhausted-check": cmd_exhausted_check,
    "path-check": cmd_path_check,
    "lease": cmd_lease,
    "archive-check": cmd_archive_check,
}


def main(argv: List[str]) -> int:
    if not argv or argv[0] not in _MODES:
        print(f"用法: _redispatch_check.py <{'|'.join(_MODES)}> [...]", file=sys.stderr)
        return 2
    return _MODES[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
