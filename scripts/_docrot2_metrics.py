#!/usr/bin/env python3
"""_docrot2_metrics.py — DOCROT2 Task 3.2（票 B-63）：收案量測事件與成效報表之唯一實作。

契約唯一來源＝scripts/docrot2_metric_contract.json；類別值集與門檻＝scripts/governance_verdicts.json（經 _finding_category）。

子命令：
  emit-round --round-id <rid> --session <name> --lock <sources.lock>
      呼叫端＝scripts/debt_clear.sh（收案前）。該輪不須類別（門檻前）⇒ rc=0 不寫；已有同輪事件 ⇒ rc=0 不再寫；
      否則由收斂檔、audit、git 計算欄位並經 scripts/audit_append.sh 寫 docrot2_round_metric。
      缺欄（類別、主委欄、開債事件欄位、HEAD、戳記本體快照）或寫入失敗 ⇒ rc=1，stderr 帶 DOCROT2_METRIC_REASON=<碼>。
  report
      呼叫端＝scripts/docrot2_metrics.sh。只讀 audit 與契約（交接重放另以契約命令對 git 物件執行）；
      契約不合法、cohort 未定、缺事件、重複事件、事件欄位不合法 ⇒ rc=1；四條及格全過 ⇒ rc=0，任一不過 ⇒ rc=1。

戳記標的（stamps）：本輪 task_id 出現於 `RECONCILE-STAMP:` 行（整詞 `task:<task_id>`）之檔，搜尋範圍封閉＝
  開債事件 brief 之 `stamp-target:` 宣告 ∪ scripts/stampable_artifacts.txt ∪ scripts/live_doc_registry.json 之 LIVE-SPEC exact。
  本體＝scripts/reconcile_body_hash.sh 之區間（首個 `## 戳記` 標題之前）；本體文字以 sha256 為名寫入
  handoffs/docrot2_body_snapshots/（write-once），供下次同標的戳記比對 history_only。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import _finding_category as fcat  # noqa: E402

CONTRACT = os.path.join(HERE, "docrot2_metric_contract.json")
VALUES = os.path.join(HERE, "governance_verdicts.json")
EVENT = "docrot2_round_metric"
OPEN_EVENT = "committee_round_open"
SNAPSHOT_DIR = os.path.join("handoffs", "docrot2_body_snapshots")
STAMP_HEADING_RE = re.compile(r"^##[ \t\r\v\f]*戳記")
UNAVAILABLE = "unavailable"


class MetricError(Exception):
    def __init__(self, reason: str, msg: str):
        super().__init__(msg)
        self.reason = reason


# ────────────────────────────────────────────────────────────── 契約

def load_contract(path: str = CONTRACT) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            c = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise MetricError("contract-invalid", f"{path} 讀取失敗：{exc}")
    def need(cond: bool, what: str) -> None:
        if not cond:
            raise MetricError("contract-invalid", f"{path}：{what}")
    tk = c.get("ticket_key") or {}
    need(tk.get("source_field") == "task_id" and isinstance(tk.get("separator"), str) and tk.get("separator")
         and isinstance(tk.get("segments"), int) and tk["segments"] >= 1, "ticket_key 不合法")
    co = c.get("cohort") or {}
    need(isinstance(co.get("brief_kind"), str) and co["brief_kind"]
         and isinstance(co.get("rounds"), int) and co["rounds"] >= 2, "cohort 不合法（rounds ≥ 2）")
    fs = c.get("finding_scope") or {}
    need(isinstance(fs.get("exclude_id_suffix"), str) and fs["exclude_id_suffix"], "finding_scope 不合法")
    nu = c.get("numerator") or {}
    need(isinstance(nu.get("committee_category"), str) and nu["committee_category"], "numerator 不合法")
    need(c.get("denominator") == "canonical_count", "denominator 只准 canonical_count")
    need(isinstance(c.get("zero_denominator"), int) and not isinstance(c.get("zero_denominator"), bool)
         and c["zero_denominator"] == 0, "zero_denominator 只准 0")
    need(c.get("comparator") == "second_le_first", "comparator 只准 second_le_first")
    need(isinstance(c.get("max_findings_per_round"), int) and not isinstance(c.get("max_findings_per_round"), bool)
         and c["max_findings_per_round"] >= 0, "max_findings_per_round 不合法")
    hr = c.get("handoff_replay") or {}
    need(isinstance(hr.get("command"), list) and all(isinstance(x, str) for x in hr["command"])
         and "{commit}" in hr["command"] and isinstance(hr.get("expect_rc"), int), "handoff_replay 不合法")
    ho = c.get("history_only_restamp") or {}
    need(isinstance(ho.get("max"), int) and not isinstance(ho.get("max"), bool) and ho["max"] >= 0
         and isinstance(ho.get("body_hash_script"), str), "history_only_restamp 不合法")
    cs = c.get("closure_sequence")
    need(cs is None or (isinstance(cs, int) and not isinstance(cs, bool) and cs >= 0), "closure_sequence 須為 null 或非負整數")
    return c


def ticket_key(task_id: object, contract: dict) -> Optional[str]:
    if not isinstance(task_id, str):
        return None
    tk = contract["ticket_key"]
    parts = task_id.split(tk["separator"])
    if len(parts) < tk["segments"] or not all(parts[: tk["segments"]]):
        return None
    return tk["separator"].join(parts[: tk["segments"]])


def _int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


# ────────────────────────────────────────────────────────────── 戳記本體

def body_bytes(path: str) -> bytes:
    """reconcile_body_hash.sh 之本體區間（首個 `## 戳記` 標題行之前之全部行，含行尾換行）。"""
    with open(path, "rb") as fh:
        data = fh.read()
    lines = data.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if STAMP_HEADING_RE.match(ln.decode("utf-8", "replace")):
            return b"".join(lines[:i])
    raise MetricError("stamp-body-missing", f"{path}：缺『## 戳記』區段標題，無法取本體")


def _script_body_sha(repo: str, contract: dict, path: str) -> str:
    script = os.path.join(repo, contract["history_only_restamp"]["body_hash_script"])
    r = subprocess.run(["bash", script, path], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0 or not re.fullmatch(r"[0-9a-f]{64}", r.stdout.strip()):
        raise MetricError("stamp-body-missing", f"{path}：{contract['history_only_restamp']['body_hash_script']} rc={r.returncode}")
    return r.stdout.strip()


def _history_mask(text: str) -> List[bool]:
    import _live_doc_write_guard as ldw  # 延遲載入：歷史專區判定唯一實作
    lines = ldw.split_lines(text)
    reg = ldw.regions(lines, set())
    return [reg["hist"][i] or reg["marker"][i] for i in range(len(lines))]


def history_only(old_text: str, new_text: str) -> bool:
    """有差異且差異行於兩版皆落在 HISTORY-BEGIN..END（含標記行）內 ⇒ True。"""
    import _live_doc_write_guard as ldw
    old_l, new_l = ldw.split_lines(old_text), ldw.split_lines(new_text)
    old_m, new_m = _history_mask(old_text), _history_mask(new_text)
    changed = False
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_l, new_l, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        changed = True
        if not all(old_m[i] for i in range(i1, i2)) or not all(new_m[j] for j in range(j1, j2)):
            return False
    return changed


def _stamp_search_space(repo: str, open_rec: dict) -> List[str]:
    cands: List[str] = []
    brief = open_rec.get("brief_path")
    if isinstance(brief, str) and brief and not os.path.isabs(brief):
        bp = os.path.join(repo, brief)
        if os.path.isfile(bp):
            with open(bp, encoding="utf-8", errors="replace") as fh:
                for ln in fh:
                    m = re.match(r"^stamp-target:[ \t]*(\S+)[ \t]*$", ln.rstrip("\n"))
                    if m:
                        cands.append(m.group(1))
    sa = os.path.join(repo, "scripts", "stampable_artifacts.txt")
    if os.path.isfile(sa):
        with open(sa, encoding="utf-8") as fh:
            for ln in fh:
                s = ln.strip()
                if s and not s.startswith("#"):
                    cands.append(s)
    reg = os.path.join(repo, "scripts", "live_doc_registry.json")
    if os.path.isfile(reg):
        with open(reg, encoding="utf-8") as fh:
            for item in (json.load(fh).get("exact") or []):
                if isinstance(item, list) and len(item) == 2 and item[1] == "LIVE-SPEC":
                    cands.append(item[0])
    out: List[str] = []
    for c in cands:
        parts = c.split("/")
        if c.startswith("/") or ".." in parts or c in out:
            continue
        out.append(c)
    return sorted(out)


def stamp_targets(repo: str, open_rec: dict, task_id: str) -> List[str]:
    tok = re.compile(r"(?:^|\s)task:" + re.escape(task_id) + r"(?=\s|$)")
    hits: List[str] = []
    for rel in _stamp_search_space(repo, open_rec):
        full = os.path.join(repo, rel)
        if os.path.islink(full) or not os.path.isfile(full):
            continue
        with open(full, encoding="utf-8", errors="replace") as fh:
            if any("RECONCILE-STAMP:" in ln and tok.search(ln) for ln in fh):
                hits.append(rel)
    return hits


def _snapshot_path(repo: str, sha: str) -> str:
    return os.path.join(repo, SNAPSHOT_DIR, f"{sha}.md")


def compute_stamps(repo: str, contract: dict, open_rec: dict, task_id: str, prior_events: List[dict]) -> List[dict]:
    out: List[dict] = []
    for rel in stamp_targets(repo, open_rec, task_id):
        full = os.path.join(repo, rel)
        body = body_bytes(full)
        after = hashlib.sha256(body).hexdigest()
        if _script_body_sha(repo, contract, rel) != after:
            raise MetricError("stamp-body-mismatch", f"{rel}：本體雜湊與 {contract['history_only_restamp']['body_hash_script']} 不一致")
        before = "none"
        for ev in prior_events:
            for st in ev.get("stamps") or []:
                if isinstance(st, dict) and st.get("stamp_target") == rel and isinstance(st.get("body_sha_after"), str):
                    before = st["body_sha_after"]
        ho = 0
        if before != "none":
            snap = _snapshot_path(repo, before)
            try:
                with open(snap, "rb") as fh:
                    old = fh.read()
            except OSError as exc:
                raise MetricError("snapshot-missing", f"{rel}：前次戳記本體快照不可讀（{snap}）：{exc}")
            if hashlib.sha256(old).hexdigest() != before:
                raise MetricError("snapshot-missing", f"{rel}：前次戳記本體快照雜湊不符（{snap}）")
            ho = 1 if history_only(old.decode("utf-8", "replace"), body.decode("utf-8", "replace")) else 0
        snap_new = _snapshot_path(repo, after)
        if os.path.exists(snap_new):
            with open(snap_new, "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() != after:
                    raise MetricError("snapshot-missing", f"{snap_new}：既有快照內容與檔名雜湊不符")
        else:
            os.makedirs(os.path.dirname(snap_new), exist_ok=True)
            tmp = snap_new + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(body)
            os.replace(tmp, snap_new)
        out.append({"stamp_target": rel, "body_sha_before": before, "body_sha_after": after, "history_only": ho})
    return out


# ────────────────────────────────────────────────────────────── emit-round

def emit_round(rid: str, session: str, lock: str, repo: str = REPO) -> int:
    try:
        if not fcat.category_required(rid, VALUES):
            print(f"[docrot2_metrics] round {rid} 屬門檻前（不須類別）⇒ 不寫 {EVENT}")
            return 0
        cats, _thr = fcat.load_config(VALUES)
        contract = load_contract()
        audit = fcat.resolve_audit_path()
        events = list(fcat.iter_audit(audit)) if os.path.isfile(audit) else []
        if any(e.get("event") == EVENT and e.get("round_id") == rid for e in events):
            print(f"[docrot2_metrics] round {rid} 已有 {EVENT} ⇒ 不再寫（同輪只一筆）")
            return 0
        opens = [e for e in events if e.get("event") == OPEN_EVENT and e.get("round_id") == rid]
        if len(opens) != 1:
            raise MetricError("round-open-missing", f"round {rid} 之 {OPEN_EVENT} 須恰一筆（實得 {len(opens)}）")
        op = opens[0]
        task_id, sess, seq, bk = op.get("task_id"), op.get("session_name"), op.get("sequence"), op.get("brief_kind")
        if not (isinstance(task_id, str) and task_id and isinstance(sess, str) and sess and _int(seq)
                and isinstance(bk, str) and bk):
            raise MetricError("round-open-field-missing", f"round {rid} 之 {OPEN_EVENT} 缺 task_id／session_name／sequence／brief_kind")
        if sess != session:
            raise MetricError("session-mismatch", f"--session {session} 與開債事件 session_name {sess} 不一致")
        participants = op.get("participants")
        if not (isinstance(participants, list) and all(isinstance(p, str) and p for p in participants)):
            raise MetricError("round-open-field-missing", f"round {rid} 之 participants 不合法")

        import _synth_attr as sa  # 延遲載入：收斂檔解析唯一實作
        synth = os.path.join(os.path.dirname(os.path.abspath(lock)), "synth.md")
        try:
            with open(synth, encoding="utf-8") as fh:
                doc = sa.parse_synth(fh.read(), os.path.relpath(synth, repo))
        except OSError as exc:
            raise MetricError("synth-missing", f"收斂檔不可讀：{exc}")
        suffix = contract["finding_scope"]["exclude_id_suffix"]
        counts: Dict[str, int] = {c: 0 for c in cats}
        mismatch = 0
        missing: List[str] = []
        scope = [f for f in doc.findings if not f.id.endswith(suffix)]
        for f in scope:
            committee, cerr = fcat.single_category(f.block_lines, cats)
            chair = {r.cells[4] for r in sa.rows_for(doc, f.id)
                     if not r.placeholder and len(r.cells) >= 5 and r.cells[4] in cats}
            if cerr:
                missing.append(f"{f.id} 委員類別：{cerr}")
            if len(chair) != 1:
                missing.append(f"{f.id} 主委類別（群集表第 5 欄）缺或不一致：{sorted(chair)}")
            if committee is not None:
                counts[committee] += 1
                if len(chair) == 1 and committee != next(iter(chair)):
                    mismatch += 1
        if missing:
            raise MetricError("category-missing", "收斂檔缺類別計數所需之值：" + "；".join(missing))

        r = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "HEAD^{commit}"], capture_output=True, text=True)
        head = r.stdout.strip()
        if r.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
            raise MetricError("head-missing", "取不到 HEAD commit（handoff_tree_commit）")
        prior = [e for e in events if e.get("event") == EVENT]
        stamps = compute_stamps(repo, contract, op, task_id, prior)
        models = {p: {"model": UNAVAILABLE, "reasoning_effort": UNAVAILABLE} for p in participants}
    except MetricError as exc:
        print(f"[docrot2_metrics] 🔴 {exc}", file=sys.stderr)
        print(f"DOCROT2_METRIC_REASON={exc.reason}", file=sys.stderr)
        return 1
    except fcat.ConfigError as exc:
        print(f"[docrot2_metrics] 🔴 設定不可用：{exc}", file=sys.stderr)
        print("DOCROT2_METRIC_REASON=config-invalid", file=sys.stderr)
        return 1

    append = os.path.join(repo, "scripts", "audit_append.sh")
    cmd = ["bash", append, "--event", EVENT,
           "--field", f"round_id={rid}", "--field", f"task_id={task_id}", "--field", f"session_name={sess}",
           "--field", f"round_open_sequence=@{seq}", "--field", f"brief_kind={bk}",
           "--field", f"canonical_count=@{len(scope)}",
           "--field", "category_counts=@" + json.dumps(counts, ensure_ascii=False, sort_keys=True),
           "--field", f"mismatch_count=@{mismatch}", "--field", f"handoff_tree_commit={head}",
           "--field", "committee_models=@" + json.dumps(models, ensure_ascii=False, sort_keys=True),
           "--field", "stamps=@" + json.dumps(stamps, ensure_ascii=False, sort_keys=True),
           "--field", "actor=debt_clear", "--field", "origin_script=debt_clear.sh"]
    w = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    if w.returncode != 0:
        print(f"[docrot2_metrics] 🔴 {EVENT} 寫入失敗 rc={w.returncode}：{w.stderr.strip()}", file=sys.stderr)
        print("DOCROT2_METRIC_REASON=append-failed", file=sys.stderr)
        return 1
    print(f"[docrot2_metrics] ✓ 已寫 {EVENT} round={rid} canonical={len(scope)} counts={counts} mismatch={mismatch} stamps={len(stamps)}")
    return 0


# ────────────────────────────────────────────────────────────── report

def _valid_metric(ev: dict, cats: List[str]) -> Optional[str]:
    cc = ev.get("category_counts")
    if not (isinstance(cc, dict) and set(cc) == set(cats) and all(_int(v) and v >= 0 for v in cc.values())):
        return "category_counts 鍵集須恰為類別值集且值為非負整數"
    n = ev.get("canonical_count")
    if not (_int(n) and n >= 0 and sum(cc.values()) == n):
        return "canonical_count 須為非負整數且等於各類別計數之和"
    if not (_int(ev.get("mismatch_count")) and 0 <= ev["mismatch_count"] <= n):
        return "mismatch_count 不合法"
    if not (isinstance(ev.get("handoff_tree_commit"), str) and re.fullmatch(r"[0-9a-f]{7,40}", ev["handoff_tree_commit"])):
        return "handoff_tree_commit 不合法"
    st = ev.get("stamps")
    if not isinstance(st, list):
        return "stamps 須為陣列"
    for s in st:
        if not (isinstance(s, dict) and set(s) == {"stamp_target", "body_sha_before", "body_sha_after", "history_only"}
                and s.get("history_only") in (0, 1) and not isinstance(s.get("history_only"), bool)):
            return "stamps 項不合法"
    return None


def report(repo: str = REPO) -> int:
    fails: List[str] = []
    try:
        contract = load_contract()
        cats, _thr = fcat.load_config(VALUES)
        if contract["numerator"]["committee_category"] not in cats:
            raise MetricError("contract-invalid", "numerator.committee_category 不在 finding_category_values")
        closure = contract["closure_sequence"]
        if closure is None:
            raise MetricError("cohort-unknown", "closure_sequence 未寫入（本票尚未收票）⇒ cohort 未定")
        audit = fcat.resolve_audit_path()
        if not os.path.isfile(audit):
            raise MetricError("audit-missing", f"audit 不存在：{audit}")
        events = list(fcat.iter_audit(audit))
        opens = [e for e in events if e.get("event") == OPEN_EVENT]
        for e in opens:
            if _int(e.get("sequence")) and e["sequence"] > closure and not (isinstance(e.get("brief_kind"), str) and e["brief_kind"]):
                raise MetricError("brief-kind-missing", f"round {e.get('round_id')}（序號 {e['sequence']}）缺 brief_kind ⇒ cohort 無法判定")
        want = contract["cohort"]["brief_kind"]
        first: Dict[str, int] = {}
        by_ticket: Dict[str, List[dict]] = {}
        for e in opens:
            if e.get("brief_kind") != want or not _int(e.get("sequence")):
                continue
            tk = ticket_key(e.get("task_id"), contract)
            if tk is None:
                continue
            by_ticket.setdefault(tk, []).append(e)
            first[tk] = min(first.get(tk, e["sequence"]), e["sequence"])
        eligible = sorted((s, tk) for tk, s in first.items() if s > closure)
        if not eligible:
            raise MetricError("cohort-unknown", f"序號 {closure} 之後尚無首個 {want} 輪之票 ⇒ cohort 未定")
        cohort_ticket = eligible[0][1]
        rounds = sorted(by_ticket[cohort_ticket], key=lambda e: e["sequence"])[: contract["cohort"]["rounds"]]
        if len(rounds) < contract["cohort"]["rounds"]:
            raise MetricError("cohort-incomplete", f"票 {cohort_ticket} 之 {want} 輪僅 {len(rounds)} 輪（須 {contract['cohort']['rounds']}）")
        metrics = [e for e in events if e.get("event") == EVENT]
        ticket_round_ids = {e.get("round_id") for e in opens if ticket_key(e.get("task_id"), contract) == cohort_ticket}
        ticket_metrics: Dict[str, List[dict]] = {}
        for m in metrics:
            if m.get("round_id") in ticket_round_ids:
                ticket_metrics.setdefault(m["round_id"], []).append(m)
        for rid_, ms in ticket_metrics.items():
            if len(ms) > 1:
                raise MetricError("duplicate-event", f"round {rid_} 有 {len(ms)} 筆 {EVENT}（同輪只准一筆）")
        chosen: List[dict] = []
        for op in rounds:
            ms = ticket_metrics.get(op.get("round_id")) or []
            if not ms:
                raise MetricError("event-missing", f"cohort 輪 {op.get('round_id')}（{op.get('session_name')}）缺 {EVENT}")
            bad = _valid_metric(ms[0], cats)
            if bad:
                raise MetricError("event-invalid", f"cohort 輪 {op.get('round_id')} 之 {EVENT}：{bad}")
            chosen.append(ms[0])
        for rid_, ms in ticket_metrics.items():
            bad = _valid_metric(ms[0], cats)
            if bad:
                raise MetricError("event-invalid", f"票內輪 {rid_} 之 {EVENT}：{bad}")
    except MetricError as exc:
        print(f"[docrot2_metrics] 🔴 {exc}", file=sys.stderr)
        print(f"DOCROT2_METRIC_REASON={exc.reason}", file=sys.stderr)
        return 1
    except fcat.ConfigError as exc:
        print(f"[docrot2_metrics] 🔴 設定不可用：{exc}", file=sys.stderr)
        print("DOCROT2_METRIC_REASON=config-invalid", file=sys.stderr)
        return 1

    num = contract["numerator"]["committee_category"]
    print(f"[docrot2_metrics] cohort 票＝{cohort_ticket}；輪＝{[m.get('session_name') for m in chosen]}")
    # ① 每輪 canonical ≤ 上限
    for m in chosen:
        if m["canonical_count"] > contract["max_findings_per_round"]:
            fails.append(f"① {m.get('session_name')} canonical={m['canonical_count']} > {contract['max_findings_per_round']}")
    # ② 文件同步類占比 第二輪 ≤ 第一輪
    def ratio(m: dict) -> Fraction:
        n = m["canonical_count"]
        return Fraction(contract["zero_denominator"]) if n == 0 else Fraction(m["category_counts"][num], n)
    r1, r2 = ratio(chosen[0]), ratio(chosen[1])
    print(f"[docrot2_metrics] {num} 占比：第一輪 {r1}、第二輪 {r2}")
    if not r2 <= r1:
        fails.append(f"② {num} 占比第二輪 {r2} > 第一輪 {r1}")
    # ③ 交接檔重放
    for m in chosen:
        cmd = [x.replace("{commit}", m["handoff_tree_commit"]) for x in contract["handoff_replay"]["command"]]
        rr = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        if rr.returncode != contract["handoff_replay"]["expect_rc"]:
            fails.append(f"③ {m.get('session_name')} 交接重放 rc={rr.returncode}（須 {contract['handoff_replay']['expect_rc']}）：{rr.stderr.strip()[:300]}")
    # ④ 只動歷史區之重蓋章
    ho = sum(s["history_only"] for ms in ticket_metrics.values() for s in ms[0]["stamps"])
    print(f"[docrot2_metrics] 只動歷史區之重蓋章＝{ho}")
    if ho > contract["history_only_restamp"]["max"]:
        fails.append(f"④ 只動歷史區之重蓋章 {ho} > {contract['history_only_restamp']['max']}")
    if fails:
        print("[docrot2_metrics] 🔴 不及格：", file=sys.stderr)
        for f in fails:
            print(f"   {f}", file=sys.stderr)
        print("DOCROT2_METRIC_REASON=criteria-failed", file=sys.stderr)
        return 1
    print("[docrot2_metrics] ✓ 四條及格全過")
    return 0


def main(argv: List[str]) -> int:
    if argv[:1] == ["report"] and len(argv) == 1:
        return report()
    if argv[:1] == ["emit-round"]:
        args: Dict[str, str] = {}
        rest = argv[1:]
        i = 0
        while i < len(rest):
            if rest[i] in ("--round-id", "--session", "--lock") and i + 1 < len(rest) and rest[i] not in args:
                args[rest[i]] = rest[i + 1]
                i += 2
            else:
                print(f"_docrot2_metrics: 未知或重複參數 {rest[i]}", file=sys.stderr)
                return 2
        if set(args) != {"--round-id", "--session", "--lock"} or not all(args.values()):
            print("用法: _docrot2_metrics.py emit-round --round-id <rid> --session <name> --lock <sources.lock>", file=sys.stderr)
            return 2
        return emit_round(args["--round-id"], args["--session"], args["--lock"])
    print("用法: _docrot2_metrics.py report | emit-round --round-id <rid> --session <name> --lock <sources.lock>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
