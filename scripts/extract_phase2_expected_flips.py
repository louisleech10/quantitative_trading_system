#!/usr/bin/env python3
"""自 docs/GOVB0_FRICTION_TODO.md 機械抽取 Phase 2 預期轉向清單。

輸出：tests/governance/fixtures/phase2_expected_flips.txt ＋ .sha256 sidecar
禁手挑：只認 TODO 驗證段中可機械辨識的方向標記與反引號命令。

方向標記（產品行為，不含 mutation「轉回」）：
  - 由 BLOCK 轉 ALLOW / 全由 BLOCK 轉 ALLOW / 四條全由 BLOCK 轉 ALLOW …
  - 由 ALLOW 轉 BLOCK / 全部由 ALLOW 轉 BLOCK / 三條由 ALLOW 轉 BLOCK …
  - 維持 BLOCK / 維持 ALLOW
  - 絕對態（C5 選 (a)）：皆 BLOCK／須 BLOCK／六條皆 BLOCK／兩條須 BLOCK → maintain

重跑：
  python3 scripts/extract_phase2_expected_flips.py
  # 或 --check：與現有 fixture 比對（含 sha256）
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TODO = REPO / "docs" / "GOVB0_FRICTION_TODO.md"
OUT = REPO / "tests" / "governance" / "fixtures" / "phase2_expected_flips.txt"
OUT_SHA = Path(str(OUT) + ".sha256")

# 產品轉向／維持（禁 mutation「轉回」）
# 第三類（C5 選 (a)）：絕對態「皆 BLOCK／須 BLOCK／六條皆 BLOCK」→ maintain
_DIR_RE = re.compile(
    r"(?P<label>"
    r"(?:全|全部|三條|四條|五條)?全?由\s*(?P<from1>BLOCK|ALLOW)\s*轉\s*(?P<to1>BLOCK|ALLOW)"
    r"|(?P<maintain>維持)\s*(?P<from2>BLOCK|ALLOW)"
    r"|(?:[一二三四五六七八九十兩\d]+條)?(?P<abs_all>皆)\s*(?P<a1>BLOCK|ALLOW)"
    r"|(?:[一二三四五六七八九十兩\d]+條)?(?P<abs_must>須)\s*(?P<a2>BLOCK|ALLOW)"
    r")"
)

# 驗證 bullet：以 TEST-2.x-… 開頭的狀態列（略過 MUT）
_BULLET_START = re.compile(
    r"^\s*-\s*`(?P<tid>TEST-2\.[0-9]+-[A-Z0-9-]+)`（(?P<kind>[^）]+)）[：:](?P<body>.*)$"
)

def _is_command_token(s: str) -> bool:
    s = s.strip()
    if not s or s.startswith("TEST-"):
        return False
    if s.startswith("票 ") or s.startswith("F-") or s.startswith("D-") or s.startswith("E-"):
        return False
    # 純錨點／簡寫（非命令）
    if re.fullmatch(r"[A-Za-z0-9_.:+=,-]+", s) and not re.search(
        r"\b(codex|grok|claude|bash|pgrep|git)\b", s
    ):
        return False
    # 命令／路徑樣貌：含空白、shell 字元、或明確家族名
    if re.search(r"[\s/|$;()\"'=]", s) or re.search(
        r"\b(codex|grok|claude|cursor-agent|agy|bash|sh|pgrep|git|cat|find|ls|head|eval|out=)\b",
        s,
    ):
        return True
    return False


def _normalize_ellipsis(cmd: str) -> str:
    """統一省略號為 ASCII 三點，便於後續比對。"""
    return cmd.replace("…", "...").replace("\u2026", "...")


def _extract_backtick_cmds(blob: str) -> list[str]:
    """抽取命令反引號；先處理 markdown 雙反引號 `` ... ``（可內含 `）。"""
    cmds: list[str] = []
    i = 0
    n = len(blob)
    while i < n:
        # 雙反引號 span
        if blob.startswith("``", i):
            j = blob.find("``", i + 2)
            if j < 0:
                break
            inner = blob[i + 2 : j].strip()
            if _is_command_token(inner):
                cmds.append(_normalize_ellipsis(inner))
            i = j + 2
            continue
        if blob[i] == "`":
            j = blob.find("`", i + 1)
            if j < 0:
                break
            inner = blob[i + 1 : j]
            if _is_command_token(inner):
                cmds.append(_normalize_ellipsis(inner))
            i = j + 1
            continue
        i += 1
    return cmds

def extract(todo_text: str) -> list[dict[str, str]]:
    """回傳 [{test_id, kind, from, to, command}, ...]；kind=flip|maintain。"""
    lines = todo_text.splitlines()
    rows: list[dict[str, str]] = []
    i = 0
    while i < len(lines):
        m = _BULLET_START.match(lines[i])
        if not m:
            i += 1
            continue
        tid = m.group("tid")
        kind_zh = m.group("kind")
        # 略過 mutation 列（「轉回」屬 mutation 預期，非產品 Phase 2 轉向）
        if "mutation" in kind_zh.lower() or "MUT" in tid:
            i += 1
            continue
        # 收集本 bullet 延續行（縮排且非新 bullet）
        blob = m.group("body")
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if re.match(r"^\s*-\s*`", nxt):
                break
            if re.match(r"^### ", nxt) or re.match(r"^## ", nxt):
                break
            # 延續行：較深縮排或以 ` 開頭的命令列
            if nxt.startswith("    ") or nxt.startswith("\t"):
                blob += " " + nxt.strip()
                j += 1
                continue
            break
        i = j

        dm = _DIR_RE.search(blob)
        if not dm:
            # 無機械可辨方向（如「4/4 通過」）— 略過
            continue
        if dm.group("maintain"):
            fr = dm.group("from2")
            to = fr
            kind = "maintain"
        elif dm.group("abs_all") or dm.group("abs_must"):
            # C5 絕對態：皆／須 X → maintain X→X
            fr = dm.group("a1") or dm.group("a2")
            to = fr
            kind = "maintain"
        else:
            fr = dm.group("from1")
            to = dm.group("to1")
            kind = "flip"
            if fr == to:
                kind = "maintain"

        # 方向標記之前的反引號命令
        head = blob[: dm.start()]
        cmds = _extract_backtick_cmds(head)
        if not cmds:
            # 標記後不該有命令；若 head 無命令則整段再掃一次（防格式變異）
            cmds = _extract_backtick_cmds(blob)
        for cmd in cmds:
            rows.append(
                {
                    "test_id": tid,
                    "kind": kind,
                    "from": fr,
                    "to": to,
                    "command": cmd,
                }
            )
    return rows


def render(rows: list[dict[str, str]]) -> str:
    header = (
        "# phase2_expected_flips.txt — 機械抽取自 docs/GOVB0_FRICTION_TODO.md\n"
        "# 重跑: python3 scripts/extract_phase2_expected_flips.py\n"
        "# 格式: kind\\ttest_id\\tfrom\\tto\\tcommand\n"
        "# kind=flip|maintain；mutation「轉回」不入此檔\n"
        "# 禁手編；改 TODO 後重跑本腳本並更新 .sha256\n"
    )
    body_lines = []
    for r in rows:
        # TSV：command 內 tab 置換（理論上不應出現）
        cmd = r["command"].replace("\t", " ").replace("\n", "\\n")
        body_lines.append(
            f"{r['kind']}\t{r['test_id']}\t{r['from']}\t{r['to']}\t{cmd}"
        )
    return header + "\n".join(body_lines) + ("\n" if body_lines else "")


def write_fixture(text: str) -> str:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    OUT_SHA.write_text(f"{digest}  {OUT.name}\n", encoding="utf-8")
    return digest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="只比對現有 fixture 是否與 TODO 抽取結果一致",
    )
    args = ap.parse_args()
    if not TODO.is_file():
        print(f"MISSING {TODO}", file=sys.stderr)
        return 2
    rows = extract(TODO.read_text(encoding="utf-8"))
    text = render(rows)
    if args.check:
        if not OUT.is_file():
            print(f"MISSING fixture {OUT}", file=sys.stderr)
            return 2
        cur = OUT.read_text(encoding="utf-8")
        if cur != text:
            print("DRIFT: fixture != re-extract from TODO", file=sys.stderr)
            print(f"  fixture lines={len(cur.splitlines())} extract lines={len(text.splitlines())}")
            return 1
        side = OUT_SHA.read_text(encoding="utf-8").strip().split()[0]
        got = hashlib.sha256(cur.encode("utf-8")).hexdigest()
        if side != got:
            print(f"SHA mismatch: sidecar={side} actual={got}", file=sys.stderr)
            return 1
        print(f"OK rows={len(rows)} sha256={got}")
        return 0
    digest = write_fixture(text)
    flips = sum(1 for r in rows if r["kind"] == "flip")
    maint = sum(1 for r in rows if r["kind"] == "maintain")
    print(f"wrote {OUT.relative_to(REPO)} rows={len(rows)} flip={flips} maintain={maint}")
    print(f"sha256={digest}")
    for r in rows:
        print(f"  {r['kind']:8} {r['test_id']:20} {r['from']}->{r['to']} | {r['command'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
