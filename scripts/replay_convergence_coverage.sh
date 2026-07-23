#!/usr/bin/env bash
# replay_convergence_coverage.sh — B5 Task 6.1 / R6 水位量測（B5 fix：非循環 coverage）
#
# 鐵律：
#   - union 與 synth **獨立來源**（禁止同源 retrofit 構造 coverage=1.0）
#   - 預設 dogfood：union=3 家 review heading ID；synth=RECONCILE 內提及之來源 ID
#   - 可覆寫為構造 fixture（REPLAY_UNION_FILES / REPLAY_SYNTH_FILE）
#   - 分別抽 ID、拒 duplicate / unknown、coverage.json 一律列 missing_ids[]
#   - retrofit（可選 TC10）僅在 tmp 或明確 IN_PLACE；已 retrofit 不重加；拒同檔 dup
#   - body-hash canonicalizer = strip heading-ID 行 → 正規化換行 → sha256
#   - P0/P1 missing 獨立 hard gate；PASS 下限 90%（可 REPLAY_MIN_COVERAGE 覆寫）
#
# 環境：
#   REPLAY_REPO_ROOT     預設=腳本所在 repo root
#   REPLAY_OUT_DIR       預設=$REPO/handoffs/reconcile/replay-b5-coverage
#   REPLAY_UNION_FILES   逗號分隔相對 repo 路徑（覆寫預設 3 家 review）
#   REPLAY_SYNTH_FILE    相對 repo 路徑（覆寫預設 RECONCILE）
#   REPLAY_RETROFIT_FILES 逗號分隔；空=不做 retrofit（預設仍跑 TC10 兩寫死檔於 out 副本）
#   REPLAY_IN_PLACE=1    對 retrofit 目標就地寫（預設 0=只寫 OUT_DIR 副本）
#   REPLAY_MIN_COVERAGE  預設 0.90
#   REPLAY_SKIP_RETROFIT=1  略過 retrofit 段（純 coverage 稽核）
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPLAY_REPO_ROOT:-${DEFAULT_ROOT}}"
OUT_DIR="${REPLAY_OUT_DIR:-${REPO_ROOT}/handoffs/reconcile/replay-b5-coverage}"
IN_PLACE="${REPLAY_IN_PLACE:-0}"
MIN_COV="${REPLAY_MIN_COVERAGE:-0.90}"
SKIP_RETROFIT="${REPLAY_SKIP_RETROFIT:-0}"

# 預設 dogfood：獨立 source→synth（本 epic 真語料）
DEFAULT_UNION="handoffs/20260722-convergence-spec-review-codex.md,handoffs/20260722-convergence-spec-review-composer.md,handoffs/20260722-convergence-spec-review-grok.md"
DEFAULT_SYNTH="handoffs/20260722-convergence-spec-review-RECONCILE.md"
DEFAULT_RETROFIT="handoffs/20260722-ic-map-WHOLEMAP-v2.md,handoffs/20260722-pipeline-design-review-UNION.md"

UNION_CSV="${REPLAY_UNION_FILES:-${DEFAULT_UNION}}"
SYNTH_REL="${REPLAY_SYNTH_FILE:-${DEFAULT_SYNTH}}"
RETROFIT_CSV="${REPLAY_RETROFIT_FILES:-${DEFAULT_RETROFIT}}"

mkdir -p "${OUT_DIR}"

python3 - "${REPO_ROOT}" "${OUT_DIR}" "${IN_PLACE}" "${MIN_COV}" \
  "${SKIP_RETROFIT}" "${UNION_CSV}" "${SYNTH_REL}" "${RETROFIT_CSV}" <<'PY'
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

repo = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
in_place = sys.argv[3] == "1"
min_cov = float(sys.argv[4])
skip_retrofit = sys.argv[5] == "1"
union_csv = sys.argv[6]
synth_rel = sys.argv[7]
retrofit_csv = sys.argv[8]

ID_HEADING_RE = re.compile(
    r"^[ \t]*##(?!#)[ \t]+([A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,})[ \t]*$"
)
# 任意 ## heading（恰 h2，不含 ###）
ANY_H2_RE = re.compile(r"^[ \t]*##(?!#)[ \t]+(.+?)\s*$")
CANON_ID_TOKEN_RE = re.compile(r"\b([A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,})\b")
FAM = "CLAUDE"
SEV = "P2"

errors: list[str] = []


def normalize_newlines(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in t.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")


def strip_heading_id_lines(text: str) -> str:
    """strip canonical ## ID heading 行後正規化換行（body-hash canonicalizer）。"""
    out_lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if ID_HEADING_RE.match(line):
            continue
        out_lines.append(line.rstrip())
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    return "\n".join(out_lines) + ("\n" if out_lines else "")


def body_hash(text: str) -> str:
    return hashlib.sha256(strip_heading_id_lines(text).encode("utf-8")).hexdigest()


def extract_heading_ids(text: str) -> list[str]:
    """只從 ## canonical heading 抽 ID（union 來源用；保留重複供 dup 偵測）。"""
    ids = []
    for line in text.splitlines():
        m = ID_HEADING_RE.match(line)
        if m:
            ids.append(m.group(1))
    return ids


def extract_mentioned_ids(text: str) -> list[str]:
    """從正文提及抽 canonical ID（RECONCILE 表格用；保留出現序與重複）。"""
    return CANON_ID_TOKEN_RE.findall(text)


def reject_duplicates(ids: list[str], label: str) -> None:
    ctr = Counter(ids)
    dups = sorted([i for i, n in ctr.items() if n > 1])
    if dups:
        errors.append("%s duplicate ID(s): %s" % (label, dups))


def retrofit(text: str, start_n: int):
    """對每個非-canonical ## heading 單元，若尚未有 ID 標記則在其前插入 ## FAM-R1-Pn-NN。

    冪等：
      - 本行已是 pure canonical ID heading → 保留，不重加
      - 非-ID ## 若緊接在已輸出的 pure-ID heading 之後（中間無 body）→ 視為已 retrofit，不重加
    只新增 ID heading 行；不改其他正文。
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ends_nl = text.endswith("\n") or text.endswith("\r\n")

    out: list[str] = []
    n = start_n
    i = 0
    # 追蹤 out 末尾是否為「剛寫入、尚無 body 的 pure-ID heading」
    pending_id_marker = False

    while i < len(lines):
        line = lines[i]
        m = ANY_H2_RE.match(line)
        if not m:
            out.append(line)
            if line.strip() != "":
                pending_id_marker = False
            i += 1
            continue

        # 本行已是 canonical ID heading → 保留；標記 pending（供下一非-ID h2 冪等）
        if ID_HEADING_RE.match(line):
            out.append(line)
            pending_id_marker = True
            i += 1
            continue

        # 非 canonical ## section
        if pending_id_marker:
            # 已有前導 ID → 不重加（冪等）
            out.append(line)
            pending_id_marker = False
            i += 1
            while i < len(lines):
                if ANY_H2_RE.match(lines[i]):
                    break
                out.append(lines[i])
                i += 1
            continue

        fid = "%s-R1-%s-%02d" % (FAM, SEV, n)
        n += 1
        out.append("## %s" % fid)
        out.append(line)
        pending_id_marker = False
        i += 1
        while i < len(lines):
            if ANY_H2_RE.match(lines[i]):
                break
            out.append(lines[i])
            i += 1

    result = "\n".join(out)
    if ends_nl and not result.endswith("\n"):
        result += "\n"
    return result, n


def split_csv(s: str) -> list[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


# ---------------------------------------------------------------------------
# 1) 獨立 union / synth coverage（核心；非循環）
# ---------------------------------------------------------------------------
union_rels = split_csv(union_csv)
if not union_rels:
    errors.append("union sources empty (REPLAY_UNION_FILES)")
if not synth_rel.strip():
    errors.append("synth source empty (REPLAY_SYNTH_FILE)")

union_ids_ordered: list[str] = []
union_owner: dict[str, str] = {}
for rel in union_rels:
    path = repo / rel
    if not path.is_file():
        errors.append("missing union source: %s" % path)
        continue
    text = path.read_text(encoding="utf-8")
    ids = extract_heading_ids(text)
    if not ids:
        errors.append("union source produced zero heading IDs (vacuous): %s" % rel)
    reject_duplicates(ids, "union file %s same-file" % rel)
    for iid in ids:
        if iid in union_owner and union_owner[iid] != rel:
            errors.append(
                "union cross-source duplicate ID %s (%s vs %s)"
                % (iid, union_owner[iid], rel)
            )
        union_owner[iid] = rel
    union_ids_ordered.extend(ids)

# 全域 union 內 dup（含跨檔已報；同檔已報）— 用 set 前再驗一次 list 級
reject_duplicates(union_ids_ordered, "union aggregate")

synth_path = repo / synth_rel
synth_ids_ordered: list[str] = []
if not synth_path.is_file():
    errors.append("missing synth source: %s" % synth_path)
else:
    synth_text = synth_path.read_text(encoding="utf-8")
    # RECONCILE 多為表格提及；若有 ## heading 亦併入
    heading_ids = extract_heading_ids(synth_text)
    if heading_ids:
        synth_ids_ordered = heading_ids
        reject_duplicates(heading_ids, "synth same-file heading")
    else:
        # 提及序：保留首次出現為「合成側 ID 集合」的穩定代表
        seen = set()
        for iid in extract_mentioned_ids(synth_text):
            if iid not in seen:
                seen.add(iid)
                synth_ids_ordered.append(iid)
        # 提及允許表格重複；不對 mention 計 dup，但 unknown 仍擋

union_set = set(union_ids_ordered)
synth_set = set(synth_ids_ordered)

# unknown = synth 有、union 無
unknown = sorted(synth_set - union_set)
if unknown:
    errors.append("synth unknown ID(s) not in union: %s" % unknown)

if not union_set and not errors:
    errors.append("union empty → 守衛不算 PASS（vacuous）")

present = union_set & synth_set
missing = sorted(union_set - synth_set)
coverage = (len(present) / len(union_set)) if union_set else 0.0
p0p1_missing = [m for m in missing if re.search(r"-P[01]-", m)]

# ---------------------------------------------------------------------------
# 2) 可選 retrofit（TC10；預設寫 OUT 副本，不改原檔）
# ---------------------------------------------------------------------------
pre_hashes = {}
post_hashes = {}
if not skip_retrofit:
    seq = 1
    for rel in split_csv(retrofit_csv):
        path = repo / rel
        if not path.is_file():
            # 回放目標可能 gitignore；缺檔不擋 coverage（僅 WARN）
            print("REPLAY WARN: retrofit target missing (skip): %s" % path)
            continue
        original = path.read_text(encoding="utf-8")
        pre = body_hash(original)
        pre_hashes[rel] = pre

        # 冪等：跑兩次結果一致
        retro1, seq1 = retrofit(original, seq)
        retro2, seq2 = retrofit(retro1, seq)
        if retro1 != retro2:
            errors.append("retrofit not idempotent: %s" % rel)
        retro = retro1
        seq = seq1

        post = body_hash(retro)
        post_hashes[rel] = post
        if pre != post:
            errors.append(
                "body-hash drift after retrofit (must only add ID headings): %s pre=%s post=%s"
                % (rel, pre, post)
            )

        ids = extract_heading_ids(retro)
        reject_duplicates(ids, "retrofit output %s" % rel)
        if not ids:
            errors.append("retrofit produced zero canonical IDs (vacuous): %s" % rel)

        if in_place:
            path.write_text(retro, encoding="utf-8")
            print("REPLAY retrofit in-place: %s (+heading IDs unique=%d)" % (rel, len(set(ids))))
        else:
            dest = out_dir / Path(rel).name
            dest.write_text(retro, encoding="utf-8")
            print("REPLAY retrofit copy: %s -> %s (unique IDs=%d)" % (rel, dest, len(set(ids))))

# ---------------------------------------------------------------------------
# 3) gates + coverage.json（一律 missing_ids）
# ---------------------------------------------------------------------------
if p0p1_missing and not errors:
    # p0p1 仍寫入 JSON；exit 由下方統一
    pass

session_id = "replay-b5-coverage"
coverage_obj = {
    "session": session_id,
    "union_size": len(union_set),
    "synth_size": len(synth_set),
    "coverage": coverage,
    "p0p1_missing": p0p1_missing,
    "missing_ids": missing,  # B5C4：不論比例一律列出
    "unknown_ids": unknown,
    "union_sources": union_rels,
    "synth_source": synth_rel,
}
cov_path = out_dir / "coverage.json"
cov_path.write_text(
    json.dumps(coverage_obj, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

if errors:
    for e in errors:
        print("REPLAY FAIL: %s" % e, file=sys.stderr)
    print("REPLAY coverage.json -> %s (coverage=%.4f missing=%s)" % (
        cov_path, coverage, missing
    ), file=sys.stderr)
    sys.exit(1)

if p0p1_missing:
    print(
        "REPLAY FAIL: p0p1_missing hard gate (not diluted): %s" % p0p1_missing,
        file=sys.stderr,
    )
    print("REPLAY missing_ids=%s" % missing, file=sys.stderr)
    sys.exit(1)

if coverage < min_cov:
    print(
        "REPLAY FAIL: id_coverage=%.4f < %.2f (union=%d synth_hit=%d missing=%s)"
        % (coverage, min_cov, len(union_set), len(present), missing),
        file=sys.stderr,
    )
    sys.exit(1)

acc_path = out_dir / "committee_accepted.json"
acc_path.write_text(
    json.dumps({"accepted_ids": sorted(union_set)}, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print(
    "REPLAY PASS: coverage=%.4f union_size=%d synth_size=%d missing_ids=%s p0p1_missing=[]"
    % (coverage, len(union_set), len(synth_set), missing)
)
print("REPLAY coverage.json -> %s" % cov_path)
print(
    "REPLAY sources independent: union=%s synth=%s"
    % (union_rels, synth_rel)
)
for rel, h in pre_hashes.items():
    print("REPLAY body-hash preserved %s sha256=%s" % (rel, h))
sys.exit(0)
PY
rc=$?
exit "${rc}"
