#!/usr/bin/env bash
# write_committee_accepted.sh — Phase 7 Task 7.1：委員語意審後產 committee_accepted.json
#
# 餵 Oracle⑤ residual = |union_ids \ accepted_ids|
# schema: {"accepted_ids":[...]}
#
# 用法:
#   bash scripts/write_committee_accepted.sh \
#     --session handoffs/reconcile/<session> \
#     --review <semantic_review.md>
#
# 鐵律:
#   - 只在 Fresh findings: NONE 時寫 final accepted（0 新 finding → 收斂）
#   - 結構化 charter parser：Fresh 唯一狀態 / 語意欄位 / 拒裸 ID 清單 / Verdict+機械 precondition
#   - 禁列漏掉的 ID（機械層活）；偵測到 missing-ID 清單型段落 → 拒
#   - accepted_ids = 鎖定 sources 的 canonical ID union
#   - write-once：既有 committee_accepted.json 拒覆寫（--force 僅 GOVERNANCE_TEST_HARNESS=1）
set -u

SESSION=""
REVIEW=""
FORCE=0

usage() {
  cat <<'EOF'
用法:
  bash scripts/write_committee_accepted.sh --session <session_dir> --review <semantic_review.md>
選項:
  --force   允許覆寫既有 committee_accepted.json（僅 GOVERNANCE_TEST_HARNESS=1）
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session)
      SESSION="${2:-}"; shift 2 ;;
    --review)
      REVIEW="${2:-}"; shift 2 ;;
    --force)
      FORCE=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "ERROR: 未知參數: $1" >&2; usage; exit 2 ;;
  esac
done

[ -n "${SESSION}" ] || { echo "ERROR: 必填 --session" >&2; usage; exit 2; }
[ -n "${REVIEW}" ] || { echo "ERROR: 必填 --review" >&2; usage; exit 2; }

# 反 bypass：--force 僅測試 harness
if [ "${FORCE}" = "1" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
  echo "ERROR: --force 僅允許 GOVERNANCE_TEST_HARNESS=1（正式路徑 fail-closed）" >&2
  exit 1
fi

if [ ! -d "${SESSION}" ]; then
  echo "ERROR: session 目錄不存在: ${SESSION}" >&2
  exit 1
fi
SESSION="$(cd "${SESSION}" && pwd -P)"

if [ ! -f "${REVIEW}" ]; then
  echo "ERROR: review 檔不存在: ${REVIEW}" >&2
  exit 1
fi
REVIEW="$(cd "$(dirname "${REVIEW}")" && pwd -P)/$(basename "${REVIEW}")"

LOCK_PATH="${SESSION}/sources.lock"
OUT_PATH="${SESSION}/committee_accepted.json"

if [ ! -f "${LOCK_PATH}" ]; then
  echo "ERROR: sources.lock 不存在: ${LOCK_PATH}" >&2
  exit 1
fi

if [ -f "${OUT_PATH}" ] && [ "${FORCE}" != "1" ]; then
  echo "ERROR: committee_accepted.json 已存在，拒覆寫（write-once）: ${OUT_PATH}" >&2
  exit 1
fi

python3 - "${SESSION}" "${REVIEW}" "${LOCK_PATH}" "${OUT_PATH}" <<'PY'
"""Validate semantic review charter (structured parser) + write committee_accepted.json.

Charter gates (CODEX-B6-P1-01):
  ① Fresh findings 唯一狀態：NONE 或有具體語意 finding，不得混淆
  ② semantic finding 須有 polarity + 必要語意欄位（**斷言**/**碼證**；非只 ID）
  ③ 拒絕未具語意主張的 canonical-ID 清單（裸 ## FAM-R1-Pn-NN / 裸 bullet ID）
  ④ Verdict APPROVED + Mechanical precondition（completeness PASS + lock FROZEN 敘述）
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

session = Path(sys.argv[1])
review_path = Path(sys.argv[2])
lock_path = Path(sys.argv[3])
out_path = Path(sys.argv[4])

HEADING = re.compile(r"^(#{1,6})\s+(\S.*)$")
CANON = re.compile(r"^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$")
DEGRADE = re.compile(r"^DEGRADE-[A-Z]+-[0-9]{2,}$")
FAM = {"CODEX", "COMPOSER", "GROK", "CLAUDE", "AGY"}

# 禁：機械掉項清單段落（委員禁列漏掉的 ID）
FORBIDDEN_MECH = re.compile(
    r"(?im)(?:"
    r"#{1,6}\s*(?:漏掉的?\s*ID|missing[_\s-]*ids?|dropped[_\s-]*ids?|未收錄\s*ID|機械掉項)"
    r"|(?:^|\n)\s*(?:漏掉的?\s*ID|missing[_\s-]*ids?)\s*[:=]"
    r")"
)

# Fresh NONE 書寫
FRESH_NONE_LINE = re.compile(
    r"(?im)^\s*(?:"
    r"none\b"
    r"|fresh\s*findings?\s*[:=]\s*none\b"
    r"|fresh\s*[:=]\s*none\b"
    r"|0\s*(?:new\s+)?findings?\b"
    r")\s*$"
)
FRESH_NONE_INLINE = re.compile(
    r"(?im)fresh\s*findings?\s*[:=]\s*none\b|fresh\s*[:=]\s*none\b"
)

# Semantic finding block title (SEM-01 …)
SEM_HEADING = re.compile(
    r"(?im)^#{1,6}\s+(SEM-\d+)\b(?:\s+(.*))?$"
)
# polarity 關鍵詞（語意主張方向）
POLARITY_RE = re.compile(
    r"(?i)(?:"
    r"講水|假證據|假\s*body|錯併|不當降級|降級|水貨|假造|"
    r"polarity|severity|false\s*evidence|mis-?merge|wrong\s*merge|"
    r"\bP[0-3]\b|blocking|conditional|approved|reject"
    r")"
)
ASSERT_RE = re.compile(r"\*\*斷言\*\*|斷言\s*[:=]")
CODE_RE = re.compile(r"\*\*碼證\*\*|碼證\s*[:=]")

# Verdict
VERDICT_APPROVED = re.compile(
    r"(?im)(?:^|\n)\s*(?:[-*]\s*\[[xX]\]\s*)?(?:Verdict\s*[:：]\s*)?APPROVED\b"
)
VERDICT_CONDITIONAL = re.compile(
    r"(?im)(?:^|\n)\s*(?:[-*]\s*\[[xX]\]\s*)?(?:Verdict\s*[:：]\s*)?CONDITIONAL\b"
)

# Mechanical precondition markers
MECH_COMPLETENESS = re.compile(
    r"(?im)completeness\s*[:：]?\s*(?:PASS|rc\s*=\s*0)|"
    r"機械\s*(?:層|precondition)?\s*[:：]?\s*PASS|"
    r"completeness.*(?:rc\s*=\s*0|PASS)"
)
MECH_LOCK = re.compile(
    r"(?im)sources\.lock\s*[:：]?\s*FROZEN|lock\s*[:：]?\s*FROZEN|closure_state\s*[:：]?\s*FROZEN"
)

# Bare bullet / numbered list of only canonical IDs
BARE_BULLET_ID = re.compile(
    r"^\s*(?:[-*]|\d+[.)])\s+([A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,})\s*$"
)


def fail(msg: str) -> None:
    print(f"COMMITTEE_ACCEPTED FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ids_of_text(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        m = HEADING.match(line)
        if not m:
            continue
        raw = m.group(2).strip()
        tok = re.sub(r"[^A-Za-z0-9_-].*$", "", raw.split()[0] if raw.split() else "")
        if DEGRADE.match(tok):
            continue
        if CANON.match(tok) and tok.split("-", 1)[0] in FAM:
            out.add(tok)
    return out


def _first_token(heading_rest: str) -> str:
    parts = heading_rest.strip().split()
    if not parts:
        return ""
    return re.sub(r"[^A-Za-z0-9_-].*$", "", parts[0])


def parse_sections(text: str) -> list[tuple[int, str, str, str]]:
    """Return list of (level, title_raw, first_token, body)."""
    lines = text.splitlines()
    sections: list[tuple[int, str, str, list[str]]] = []
    cur_level = 0
    cur_title = ""
    cur_tok = ""
    cur_body: list[str] = []
    # preamble before first heading
    preamble: list[str] = []
    seen_heading = False

    for line in lines:
        m = HEADING.match(line)
        if m:
            if seen_heading:
                sections.append((cur_level, cur_title, cur_tok, cur_body))
            else:
                # drop preamble into synthetic
                if preamble:
                    sections.append((0, "__preamble__", "", preamble))
                seen_heading = True
            cur_level = len(m.group(1))
            cur_title = m.group(2).strip()
            cur_tok = _first_token(cur_title)
            cur_body = []
        else:
            if seen_heading:
                cur_body.append(line)
            else:
                preamble.append(line)
    if seen_heading:
        sections.append((cur_level, cur_title, cur_tok, cur_body))
    elif preamble:
        sections.append((0, "__preamble__", "", preamble))

    return [(lv, t, tok, "\n".join(body).strip()) for lv, t, tok, body in sections]


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def section_key(title: str) -> str:
    n = normalize_title(title)
    if re.search(r"fresh\s*findings?", n) or n in {"fresh", "fresh findings"}:
        return "fresh"
    if re.search(r"semantic\s*findings?", n) or re.search(r"語意\s*finding", n):
        return "semantic"
    if re.search(r"mechanical\s*precondition", n) or re.search(r"機械\s*(precondition|前置)", n):
        return "mechanical"
    if re.search(r"^verdict\b", n) or n == "verdict" or "裁決" in n:
        return "verdict"
    if re.search(r"\bfindings?\b", n) and "fresh" not in n and "semantic" not in n:
        return "findings_generic"
    return "other"


def body_is_none(body: str) -> bool:
    if not body or not body.strip():
        return False
    # every non-empty line must match NONE-like
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if not lines:
        return False
    for ln in lines:
        if not FRESH_NONE_LINE.match(ln):
            # allow trailing parenthetical after NONE
            if re.match(r"(?i)^\s*none\b", ln):
                continue
            return False
    return True


def body_has_substantive_content(body: str) -> bool:
    """True if body has content that is not empty/placeholder/NONE."""
    if not body or not body.strip():
        return False
    stripped = body.strip()
    if body_is_none(stripped):
        return False
    # placeholders
    if re.fullmatch(
        r"(?is)\s*(?:（?無則整節省略[^）\n]*）?|\(none\)|n/a|—|-|…|\.{3})\s*",
        stripped,
    ):
        return False
    return True


def collect_bare_bullet_ids(text: str) -> list[str]:
    found: list[str] = []
    # consecutive bare-ID bullets count as a list if ≥1 in findings-like context,
    # or always if the line is only an ID bullet
    for line in text.splitlines():
        m = BARE_BULLET_ID.match(line)
        if not m:
            continue
        tok = m.group(1)
        if CANON.match(tok) and tok.split("-", 1)[0] in FAM:
            found.append(tok)
    return found


def semantic_fields_ok(body: str, title: str = "") -> tuple[bool, str]:
    """Require polarity + **斷言** + **碼證** for a semantic finding body."""
    blob = f"{title}\n{body}"
    if not ASSERT_RE.search(blob):
        return False, "缺 **斷言**（必要語意欄位）"
    if not CODE_RE.search(blob):
        return False, "缺 **碼證**（必要語意欄位）"
    if not POLARITY_RE.search(blob):
        return False, "缺 polarity/語意主張方向（講水/錯併/降級/P0-P3 等）"
    return True, ""


def validate_charter(review: str) -> None:
    if FORBIDDEN_MECH.search(review):
        fail(
            "語意審禁列漏掉的 ID（那是機械層 Phase4 的活）；"
            "只審語意（講水/降級/錯併）。見 templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md"
        )

    sections = parse_sections(review)
    if not sections:
        fail("語意審為空或無法解析 section")

    fresh_bodies: list[str] = []
    semantic_blocks: list[tuple[str, str]] = []  # (title, body)
    mech_bodies: list[str] = []
    verdict_bodies: list[str] = []
    generic_findings_bodies: list[str] = []
    bare_canon_headings: list[tuple[str, str]] = []  # (id, body)

    for _lv, title, tok, body in sections:
        if title == "__preamble__":
            continue
        key = section_key(title)

        # SEM-NN headings always semantic finding blocks
        sm = SEM_HEADING.match(f"## {title}")
        if sm:
            semantic_blocks.append((title, body))
            continue

        # bare canonical ID heading (## CODEX-R1-P0-01)
        if CANON.match(tok) and tok.split("-", 1)[0] in FAM:
            bare_canon_headings.append((tok, body))
            continue

        if key == "fresh":
            fresh_bodies.append(body)
        elif key == "semantic":
            # container section: either NONE-like empty, or holds nested content / prose findings
            if body_has_substantive_content(body):
                # treat whole body as one block if no nested SEM (nested already separate)
                # if body only has list of IDs → bare list handled later
                semantic_blocks.append((title, body))
        elif key == "mechanical":
            mech_bodies.append(body if body else title)
        elif key == "verdict":
            verdict_bodies.append(body if body else title)
        elif key == "findings_generic":
            generic_findings_bodies.append(body)

    # Also scan whole doc for inline Fresh findings: NONE (when not in section form)
    whole_fresh_none = bool(FRESH_NONE_INLINE.search(review))

    # ── ③ 拒絕裸 canonical-ID 清單（先於 fresh，防 ID 冒充語意審） ──
    bare_bullets = collect_bare_bullet_ids(review)
    if bare_bullets:
        fail(
            "非法語意審：偵測到裸列 canonical-ID 清單（無語意正文）: "
            + ", ".join(bare_bullets[:8])
            + " — 禁以 ID 清單冒充語意審（CODEX-B6-P1-01）"
        )

    for cid, body in bare_canon_headings:
        ok, reason = semantic_fields_ok(body, title=cid)
        if not ok:
            fail(
                f"非法語意審：裸列 canonical ID heading ## {cid} 無語意正文"
                f"（{reason}）— 不得冒充語意審 / 不得寫 accepted"
            )
        # 即使有欄位，語意審也不得以 source canonical ID heading 充當 finding
        fail(
            f"非法語意審：語意審不得以 source canonical ID heading（## {cid}）"
            "充當 finding；只允許 SEM-* 語意 finding 或 Fresh findings: NONE"
        )

    # ── ② semantic finding 必要欄位 / polarity（有 SEM 殼即驗） ─────
    for title, body in semantic_blocks:
        if SEM_HEADING.match(f"## {title}"):
            ok, reason = semantic_fields_ok(body, title=title)
            if not ok:
                fail(
                    f"semantic finding 缺必要語意欄位/polarity: {title} — {reason}"
                )
        elif body_has_substantive_content(body):
            ok, reason = semantic_fields_ok(body, title=title)
            if not ok:
                fail(
                    f"Semantic findings 區段缺必要語意欄位/polarity — {reason}"
                )

    # ── ① Fresh findings 唯一狀態 ─────────────────────────────────────
    if not fresh_bodies and not whole_fresh_none:
        fail(
            "須宣告 Fresh findings: NONE（0 新 finding）才可寫 final accepted_ids；"
            "有語意 finding 時不得蓋收斂章"
        )

    fresh_is_none = False
    fresh_has_content = False
    if fresh_bodies:
        for fb in fresh_bodies:
            if body_is_none(fb) or (not fb.strip() and whole_fresh_none):
                fresh_is_none = True
            elif body_has_substantive_content(fb):
                fresh_has_content = True
            elif not fb.strip():
                pass
            else:
                fresh_has_content = True
        if not fresh_is_none and not fresh_has_content:
            if whole_fresh_none:
                fresh_is_none = True
            else:
                fail(
                    "Fresh findings 區段非唯一 NONE 狀態（空區段且無 Fresh findings: NONE）"
                )
    else:
        fresh_is_none = whole_fresh_none

    if fresh_is_none and fresh_has_content:
        fail(
            "Fresh findings 狀態混淆：同時宣告 NONE 又有具體 fresh 內容（唯一狀態違規）"
        )

    real_sem: list[tuple[str, str]] = []
    for title, body in semantic_blocks:
        if SEM_HEADING.match(f"## {title}") or body_has_substantive_content(body):
            real_sem.append((title, body))

    if fresh_is_none and real_sem:
        fail(
            "Fresh findings 狀態混淆：宣告 NONE 卻含 Semantic findings / SEM-* "
            f"（{', '.join(t for t, _ in real_sem[:5])}）— 不得蓋 final accepted"
        )

    if not fresh_is_none:
        fail(
            "須宣告 Fresh findings: NONE（0 新 finding）才可寫 final accepted_ids；"
            "有語意 finding 時不得蓋收斂章"
        )

    # Generic ## Findings with substantive content while fresh=NONE → confusion
    for gb in generic_findings_bodies:
        if body_has_substantive_content(gb):
            fail(
                "Fresh findings: NONE 卻含 ## Findings 實質內容 — 狀態混淆，拒寫 accepted"
            )

    # ── ④ Verdict + Mechanical precondition ──────────────────────────
    verdict_blob = "\n".join(verdict_bodies)
    if not verdict_blob.strip():
        verdict_blob = review

    if VERDICT_CONDITIONAL.search(verdict_blob) and not VERDICT_APPROVED.search(
        verdict_blob
    ):
        fail("Verdict 為 CONDITIONAL — 有語意 finding 未結，不得寫 final accepted")

    if not VERDICT_APPROVED.search(verdict_blob):
        fail(
            "須宣告 Verdict: APPROVED（Fresh findings: NONE → 收斂蓋章）才可寫 accepted"
        )

    mech_blob = "\n".join(mech_bodies) if mech_bodies else ""
    scan_mech = mech_blob if mech_blob.strip() else review
    if not MECH_COMPLETENESS.search(scan_mech):
        fail(
            "缺 Mechanical precondition：須宣告 completeness: PASS（rc=0）"
            "（機器出口核實由 gate；本檔須有 precondition 敘述）"
        )
    if not MECH_LOCK.search(scan_mech):
        fail(
            "缺 Mechanical precondition：須宣告 sources.lock: FROZEN"
        )


# ── main ─────────────────────────────────────────────────────────────
review = review_path.read_text(encoding="utf-8")
validate_charter(review)

try:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
except Exception as e:
    fail(f"sources.lock 無法解析: {e}")

if not isinstance(lock, dict) or lock.get("version") != 1:
    fail("sources.lock version 須為 1")

sources = lock.get("sources")
if not isinstance(sources, list) or not sources:
    fail("sources.lock.sources 不可空")

union: set[str] = set()
for ent in sources:
    if not isinstance(ent, dict):
        fail("sources.lock.sources[] 須為 object")
    rp = ent.get("realpath")
    if not rp:
        fail("sources 缺 realpath")
    p = Path(rp)
    if not p.is_file():
        fail(f"source 不存在: {rp}")
    union |= ids_of_text(p.read_text(encoding="utf-8"))

if not union:
    fail("union 空（sources 無 canonical finding ID）— 不可 vacuous PASS")

accepted = sorted(union)
payload = {"accepted_ids": accepted}
# write-once 競態：O_EXCL
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

if out_path.is_file():
    # force 已在 bash 放行；此處覆寫
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
else:
    try:
        fd = os.open(str(out_path), flags, 0o644)
    except FileExistsError:
        fail(f"committee_accepted.json 已存在（write-once）: {out_path}")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

print(
    f"COMMITTEE_ACCEPTED PASS: wrote {out_path} accepted_ids={len(accepted)}",
    file=sys.stderr,
)
print(json.dumps(payload, ensure_ascii=False))
sys.exit(0)
PY
rc=$?
exit "${rc}"
