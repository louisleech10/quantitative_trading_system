# _debt_ledger_core.py — debt_ledger 掃描核心（單次 python；供 debt_ledger.sh / gate_check 共用）
# 由 env 驅動：DEBT_LEDGER_MODE / DEBT_LEDGER_ROUND_ID / DEBT_LEDGER_REGISTRY / DEBT_LEDGER_REPO
# 以及可選 DEBT_AUDIT_OVERRIDE / DEBT_CUTOFF_OVERRIDE（須 GOVERNANCE_TEST_HARNESS=1）
# 憲法：stdlib only；可 python3 -S 啟動。

import json
import os
import sys
from datetime import datetime, timezone

mode = os.environ["DEBT_LEDGER_MODE"]
round_id_arg = os.environ.get("DEBT_LEDGER_ROUND_ID") or ""
reg_path = os.environ["DEBT_LEDGER_REGISTRY"]
repo = os.environ["DEBT_LEDGER_REPO"]
harness = os.environ.get("GOVERNANCE_TEST_HARNESS") or ""
override_audit = os.environ.get("DEBT_AUDIT_OVERRIDE") or ""
override_cutoff = os.environ.get("DEBT_CUTOFF_OVERRIDE") or ""

def die(msg: str, rc: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(rc)

try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    die(f"registry 壞: {exc}")

# ── 路徑／cutoff 解析（語意與 _resolve_* 一致；同進程避免雙 python 啟動）──
if override_audit:
    if harness != "1":
        print("ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1", file=sys.stderr)
        sys.exit(2)
    audit_path = override_audit
else:
    rel = reg.get("audit_log_path")
    if not isinstance(rel, str) or not rel:
        die("registry 缺 audit_log_path")
    audit_path = os.path.join(repo, rel)

if override_cutoff:
    if harness != "1":
        print("ERROR: DEBT_CUTOFF_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1", file=sys.stderr)
        sys.exit(2)
    cutoff_raw = override_cutoff
else:
    cutoff_raw = reg.get("cutoff_ts")
    if not isinstance(cutoff_raw, str) or not cutoff_raw:
        die("registry 缺 cutoff_ts")

# 缺檔 → fail-closed（空檔可無債）
if not os.path.exists(audit_path):
    print(f"ERROR: audit 檔缺失: {audit_path}", file=sys.stderr)
    sys.exit(2)
if not os.path.isfile(audit_path):
    print(f"ERROR: audit 路徑不是一般檔: {audit_path}", file=sys.stderr)
    sys.exit(2)

debt_events = set((reg.get("debt_events") or {}).keys())
legacy_events = set(reg.get("non_debt_legacy_events") or [])
if not debt_events:
    die("registry debt_events 空")

def parse_ts(s: str):
    if not isinstance(s, str) or not s:
        return None
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

cutoff_dt = parse_ts(cutoff_raw)
if cutoff_dt is None:
    die(f"cutoff_ts 無法解析: {cutoff_raw!r}")

records = []  # after-cutoff debt records (for debt math)
all_debt_for_seq = []  # all debt records with sequence (continuity)
# 對**所有**以 `{` 開頭的行做 json.loads：
#   解析失敗 → fail-closed rc=2（含無 debt-marker 的壞行，如 `{not-json}`）
#   合法 JSON 但非 debt 事件 → 略過
# 不得用 marker prefilter 跳過 `{…}` 行：會吞掉半截寫入／偽 JSON，
# 違反 SPEC Task 2.1 改法①（B4 已簽核）。效能分檔屬線 C，不在本輪。

try:
    with open(audit_path, encoding="utf-8") as _fh:
        for line_no, line in enumerate(_fh, 1):
            s = line.strip()
            if not s:
                continue
            if not s.startswith("{"):
                # 非 JSON 行略過（註解／legacy 純文字）
                continue
            try:
                rec = json.loads(s)
            except json.JSONDecodeError as exc:
                # 以 { 開頭但解析失敗 → fail-closed（半截寫入不得靜默忽略）
                print(
                    f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}",
                    file=sys.stderr,
                )
                sys.exit(2)
            if not isinstance(rec, dict):
                continue
            ev = rec.get("event")
            if ev in legacy_events:
                continue
            if ev not in debt_events:
                # 非白名單 debt／legacy：略過（未知 p16 命名空間由 append 端擋）
                continue
            all_debt_for_seq.append(rec)
            ts = parse_ts(rec.get("ts") if isinstance(rec.get("ts"), str) else "")
            if ts is None:
                # 缺 ts 或壞 ts：保守 fail-closed（無法判定 cutoff）
                die(f"debt 事件缺合法 ts (line {line_no}, event={ev})")
            if ts < cutoff_dt:
                continue
            records.append(rec)
except OSError as exc:
    die(f"讀 audit 失敗: {exc}")

def seq_of(rec):
    seq = rec.get("sequence")
    if isinstance(seq, int) and not isinstance(seq, bool):
        return seq
    if isinstance(seq, str) and seq.isdigit():
        return int(seq)
    return None

def assert_seq_continuity(debt_recs) -> None:
    """白名單事件序號缺號／重號 → fail-closed。"""
    seqs = []
    for rec in debt_recs:
        s = seq_of(rec)
        if s is None:
            die(f"debt 事件缺 sequence: event={rec.get('event')}")
        seqs.append(s)
    if not seqs:
        return
    seqs_sorted = sorted(seqs)
    # 重號
    if len(seqs_sorted) != len(set(seqs_sorted)):
        die("白名單事件序號重號(fail-closed)")
    # 缺號：必須是 1..max 連續
    mx = seqs_sorted[-1]
    expected = list(range(1, mx + 1))
    if seqs_sorted != expected:
        die(f"白名單事件序號缺號(fail-closed): got={seqs_sorted} expected={expected}")

def build_rounds(recs):
    """回傳 {round_id: state_info}；同一 round 兩筆 open → fail-closed。"""
    opens = {}  # round_id -> open rec
    clears = {}  # round_id -> list clear recs
    abandons = {}  # round_id -> list abandon recs
    results = []  # family results

    for rec in recs:
        ev = rec.get("event")
        rid = rec.get("round_id")
        if not isinstance(rid, str) or not rid:
            # open/result/clear/abandon 皆需 round_id；缺則 fail-closed
            die(f"debt 事件缺 round_id: event={ev}")
        if ev == "committee_round_open":
            if rid in opens:
                die(f"同一 round_id 兩筆 committee_round_open: {rid}")
            opens[rid] = rec
        elif ev == "committee_debt_clear":
            clears.setdefault(rid, []).append(rec)
        elif ev == "debt_abandon":
            abandons.setdefault(rid, []).append(rec)
        elif ev == "committee_family_result":
            results.append(rec)

    rounds = {}
    for rid, open_rec in opens.items():
        if rid in abandons:
            state = "ABANDONED"
        elif rid in clears:
            state = "CLOSED"
        else:
            state = "OPEN"
        parts = open_rec.get("participants")
        if not isinstance(parts, list):
            parts = []
        parts_norm = [p for p in parts if isinstance(p, str)]
        rounds[rid] = {
            "round_id": rid,
            "state": state,
            "session_name": open_rec.get("session_name") or "",
            "participants": parts_norm,
            "open": open_rec,
            "clears": clears.get(rid, []),
            "abandons": abandons.get(rid, []),
        }

    # 孤兒 clear/abandon（無 open）不列為輪，但也不 crash——視為無效殘留
    return rounds, results

def latest_result_per_family(results, round_id: str):
    """同一 (round_id, family) 取 sequence 最大。"""
    best = {}
    for rec in results:
        if rec.get("round_id") != round_id:
            continue
        fam = rec.get("family")
        if not isinstance(fam, str) or not fam:
            continue
        s = seq_of(rec)
        if s is None:
            continue
        prev = best.get(fam)
        if prev is None or seq_of(prev) < s:
            best[fam] = rec
    return best

# ── 模式分派 ────────────────────────────────────────────
if mode == "round_exists":
    # 只做 round_id 存在性；不跑全域序號連續性（防死鎖）
    # 仍對壞 JSON fail-closed（上面已處理）
    # 語意 fail-closed：同一 round 非恰一筆 open → rc=2（不得讓 --abandon 吞掉）
    # pre-cutoff open 仍「存在」（SPEC：只做 round_id 存在性掃描）
    n_open = 0
    for rec in all_debt_for_seq:
        if rec.get("event") == "committee_round_open" and rec.get("round_id") == round_id_arg:
            n_open += 1
    if n_open == 0:
        sys.exit(1)
    if n_open != 1:
        print(
            f"ERROR: 同一 round_id 非恰一筆 committee_round_open（got={n_open}）: {round_id_arg}",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(0)

# 以下模式皆需序號連續性（round_exists 除外）
assert_seq_continuity(all_debt_for_seq)
rounds, results = build_rounds(records)

if mode == "list":
    # 穩定排序：依 open 的 sequence
    items = []
    for rid, info in rounds.items():
        s = seq_of(info["open"]) or 0
        items.append((s, rid, info))
    items.sort(key=lambda x: (x[0], x[1]))
    for _, rid, info in items:
        parts = ",".join(info["participants"])
        print(
            f"round_id={rid} state={info['state']} "
            f"session_name={info['session_name']} participants={parts}"
        )
    sys.exit(0)

if mode == "has_open":
    n_open = sum(1 for info in rounds.values() if info["state"] == "OPEN")
    sys.exit(0 if n_open == 0 else 1)

if mode == "abandoned_count":
    # 依 abandon_kind 分開計數；registry 是 SoT，缺失／空／非恰兩值 → fail-closed
    # （禁硬編 fallback：SoT 損壞不得產出「看起來可信」的稽核數字）
    kinds = (reg.get("enums") or {}).get("abandon_kind")
    if not isinstance(kinds, list) or len(kinds) != 2:
        die("registry enums.abandon_kind 須恰兩值（fail-closed，無硬編 fallback）")
    if not all(isinstance(k, str) and k for k in kinds):
        die("registry enums.abandon_kind 含非法值")
    counts = {k: 0 for k in kinds}
    for info in rounds.values():
        for ab in info.get("abandons") or []:
            k = ab.get("abandon_kind")
            if k in counts:
                counts[k] += 1
    # 固定輸出兩種（registry 順序）
    # 格式例：累積放棄：no-findings-expected 12 筆／collection-failed 1 筆
    parts = [f"{k} {counts.get(k, 0)} 筆" for k in kinds]
    print("累積放棄：" + "／".join(parts))
    sys.exit(0)

if mode == "round_state":
    if round_id_arg not in rounds:
        print(f"ERROR: round_id 不存在(cutoff 後): {round_id_arg}", file=sys.stderr)
        sys.exit(1)
    print(rounds[round_id_arg]["state"])
    sys.exit(0)

if mode == "dump_json":
    # 給 debt_clear 消費的結構化快照
    out_rounds = {}
    for rid, info in rounds.items():
        latest = latest_result_per_family(results, rid)
        out_rounds[rid] = {
            "round_id": rid,
            "state": info["state"],
            "session_name": info["session_name"],
            "participants": info["participants"],
            "latest_results": {
                fam: {
                    "result_state": rec.get("result_state"),
                    "output_path": rec.get("output_path"),
                    "output_sha256": rec.get("output_sha256"),
                    "sequence": seq_of(rec),
                }
                for fam, rec in latest.items()
            },
            "open": {
                "participants": info["participants"],
                "session_name": info["session_name"],
                "expected_outputs": info["open"].get("expected_outputs"),
            },
        }
    print(json.dumps({"rounds": out_rounds}, ensure_ascii=False, sort_keys=True))
    sys.exit(0)

die(f"未知 mode: {mode}")
