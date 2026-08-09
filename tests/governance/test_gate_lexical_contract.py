"""GOVB0 Task 2.0 — 詞法契約（語料 B）＋ mutation。

TEST-2.0-* 對應 docs/GOVB0_FRICTION_TODO.md Phase 2 / Task 2.0。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.sh"
GATE_LEX = REPO_ROOT / "scripts" / "_gate_lex.sh"
CORPUS_B = (
    REPO_ROOT / "tests" / "governance" / "fixtures" / "gate_decision_corpus.txt"
)
CORPUS_B_SHA = Path(str(CORPUS_B) + ".sha256")
PROTO5 = REPO_ROOT / "handoffs" / "govb0_probes" / "b15probe5.sh"

# 契約 11 項 id
CONTRACT_IDS = ("1", "1b", "2", "3", "4", "5", "6", "7", "8", "9", "10")


def _run_gate(
    payload: str,
    *,
    gate_dir: Path,
    script: Path = GATE_CHECK,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    return subprocess.run(
        ["bash", str(script)],
        input=payload,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _parse_meta_line(raw: str) -> tuple[str, str] | None:
    s = raw.strip()
    if not s.startswith("#"):
        return None
    body = s.lstrip("#").strip()
    if body.startswith("@contract "):
        return ("contract", body[len("@contract ") :].strip().split()[0])
    if body.startswith("@want "):
        return ("want", body[len("@want ") :].strip().split()[0].upper())
    if body.startswith("@case "):
        return ("case", body[len("@case ") :].strip().split()[0].upper())
    if body.startswith("@id "):
        return ("id", body[len("@id ") :].strip().split()[0])
    return None


def _load_corpus_b(path: Path = CORPUS_B) -> list[dict]:
    """回傳 [{contract, want, case, id, payload}, ...]。"""
    out: list[dict] = []
    pending: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            parsed = _parse_meta_line(line)
            if parsed is not None:
                pending[parsed[0]] = parsed[1]
            continue
        json.loads(line)
        entry = {
            "contract": pending.get("contract", ""),
            "want": pending.get("want", ""),
            "case": pending.get("case", ""),
            "id": pending.get("id", f"row{len(out)}"),
            "payload": line,
        }
        out.append(entry)
        pending = {}
    assert out, f"corpus B empty: {path}"
    return out


def _decision(payload: str, gate_dir: Path, script: Path = GATE_CHECK) -> str:
    proc = _run_gate(payload, gate_dir=gate_dir, script=script)
    return "BLOCK" if proc.returncode != 0 else "ALLOW"


# ---------------------------------------------------------------------------
# TEST-2.0-CONTRACT-22
# ---------------------------------------------------------------------------


def test_20_contract_22_coverage_and_direction(tmp_path: Path) -> None:
    """契約 11 項各 ≥1 TP＋1 TN，總條數 ≥22，且實際判定 == @want。"""
    entries = _load_corpus_b()
    assert len(entries) >= 22, f"語料 B 條數 {len(entries)} < 22"

    by_c: dict[str, dict[str, int]] = {c: {"TP": 0, "TN": 0} for c in CONTRACT_IDS}
    failures: list[str] = []

    for i, e in enumerate(entries):
        cid = e["contract"]
        if cid not in by_c:
            # 2.1 等附錄 id 不計入 11 項門檻
            if cid in CONTRACT_IDS:
                pass
            else:
                # 仍驗證 want
                got = _decision(e["payload"], tmp_path / f"x{i}")
                if e["want"] and got != e["want"]:
                    failures.append(f"{e['id']}: want={e['want']} got={got}")
                continue
        case = e["case"]
        if case in ("TP", "TN"):
            by_c[cid][case] = by_c[cid].get(case, 0) + 1
        got = _decision(e["payload"], tmp_path / f"e{i}")
        if e["want"] and got != e["want"]:
            failures.append(f"{e['id']} (c{cid}): want={e['want']} got={got}")

    missing = []
    for cid in CONTRACT_IDS:
        if by_c[cid]["TP"] < 1:
            missing.append(f"contract {cid} missing TP")
        if by_c[cid]["TN"] < 1:
            missing.append(f"contract {cid} missing TN")
    assert not missing, "契約覆蓋不足: " + "; ".join(missing)
    assert not failures, "判定不符:\n" + "\n".join(failures)


def test_20_corpus_b_sha256_sidecar() -> None:
    """語料 B 與 .sha256 sidecar 一致。"""
    assert CORPUS_B.is_file()
    assert CORPUS_B_SHA.is_file(), "缺 gate_decision_corpus.txt.sha256"
    actual = _file_sha256(CORPUS_B)
    expected = CORPUS_B_SHA.read_text(encoding="utf-8").strip().split()[0]
    assert actual == expected, f"sidecar 不符: {actual} != {expected}"


# ---------------------------------------------------------------------------
# TEST-2.0-PROTO-PARITY（26 條；差異具名）
# ---------------------------------------------------------------------------

# 原型③ 26 條（label, cmd, want）— 與 b15probe5.sh 對齊
_PROTO5_CASES: list[tuple[str, str, str]] = [
    ("裸 codex exec", 'codex exec -s workspace-write "p"', "BLOCK"),
    ("絕對路徑", "/opt/homebrew/bin/codex exec hi", "BLOCK"),
    ("bash -c 包住", 'bash -c "codex exec x"', "BLOCK"),
    ("sh -c 包住", "sh -c 'grok -m grok-4.5 -p x'", "BLOCK"),
    ("分號後", 'echo go; grok -m grok-4.5 -p "x"', "BLOCK"),
    ("管線後", 'cat b.md | codex exec "p"', "BLOCK"),
    ("eval 包住", 'eval "codex exec x"', "BLOCK"),
    ("命令替換 $()", "out=$(codex exec x)", "BLOCK"),
    ("反引號", "out=`codex exec x`", "BLOCK"),
    ("子 shell 括號", "(codex exec x)", "BLOCK"),
    ("&& 之後", "true && codex exec x", "BLOCK"),
    ("|| 之後", "false || grok -m x -p y", "BLOCK"),
    ("claude -p", 'claude -p "do it"', "BLOCK"),
    ("claude 命令替換", 'v=$(claude -p "hi")', "BLOCK"),
    ("claude 絕對路徑", '/usr/local/bin/claude --print "x"', "BLOCK"),
    ("xargs 後", "echo x | xargs codex exec", "BLOCK"),
    ("pgrep 引號內分隔符", "pgrep -fl 'codex exec|cursor-agent|grok '", "ALLOW"),
    ("commit 訊息含分號", 'git commit -m "fix: x; codex closure done"', "ALLOW"),
    ("檔名子字串", "cat sp_codex.txt", "ALLOW"),
    (
        "scratchpad + rev-parse",
        "head -3 /private/tmp/claude-501/x.out; git rev-parse HEAD",
        "ALLOW",
    ),
    (".claude + porcelain", "ls .claude/tmp; git status --porcelain", "ALLOW"),
    ("find -print", 'find .claude/tmp -name "*.md" -print', "ALLOW"),
    ("grep 委員名", "grep -rn 'grok' docs/ORCH.md", "ALLOW"),
    ("claude 在檔名中段", "cat my-claude-notes.md", "ALLOW"),
    ("目錄名為 grok", "ls /tmp/grok/notes.md", "ALLOW"),
    ("唯讀查 cx_run", 'sed -n "1,40p" scripts/cx_run.sh', "ALLOW"),
]

# 具名差異表（原型③ 期望 vs 本實作實際）。
# B3（Task 2.1）期間有 3 條：claude 段仍為子字串比對，故 scratchpad／.claude 路徑
# 誤擋。GOVB0 Task 2.2（＝GOVB1 Task 3.2，票 B-26 重號）收窄 claude 段後**三條全部消除**
# ⇒ 本表清空，26 條與原型③ 逐條相同。
# 🔴 清空是**收緊**：期望值由 BLOCK 改回原型③ 的 ALLOW，gate 必須真的放行才過。
_PROTO5_NAMED_DIFFS: dict[str, str] = {}


def test_20_proto_named_diffs_empty() -> None:
    """Task 2.2 後具名差異表須為空——26/26 與原型③ 一致。

    本測是**防回填**護欄：任何人想靠往本表加列讓 test_20_proto_parity_26
    轉綠（而非修 gate），會先在這裡紅。
    """
    assert _PROTO5_NAMED_DIFFS == {}, (
        "具名差異表非空 ⇒ 有 case 靠改期望值而非改實作轉綠: "
        f"{_PROTO5_NAMED_DIFFS}"
    )


def test_20_proto_parity_26(tmp_path: Path) -> None:
    """TEST-2.0-PROTO-PARITY：26 條與原型③逐條相同；具名差異除外。"""
    assert PROTO5.is_file(), f"缺原型③: {PROTO5}"
    assert len(_PROTO5_CASES) == 26
    mismatches: list[str] = []
    for i, (label, cmd, want) in enumerate(_PROTO5_CASES):
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            ensure_ascii=False,
        )
        got = _decision(payload, tmp_path / f"p{i}")
        expected = _PROTO5_NAMED_DIFFS.get(label, want)
        if got != expected:
            mismatches.append(f"{label}: want={expected} got={got} (proto3={want})")
    assert not mismatches, "proto parity 失敗:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# TEST-2.0-HEREDOC-*
# ---------------------------------------------------------------------------


def _bash_payload(cmd: str) -> str:
    return json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": cmd}},
        ensure_ascii=False,
    )


def test_20_heredoc_failclosed_five(tmp_path: Path) -> None:
    """TEST-2.0-HEREDOC-FC：五向量全部 BLOCK。"""
    vectors = [
        "cat <<E'O'F\nx\nE'O'F",
        'cat <<E"O"F\nx\nE"O"F',
        "cat <<$'EOF'\nx\nEOF",
        "cat <<E\\ F\nx",
        "cat <<EOF$(\n",
    ]
    for i, cmd in enumerate(vectors):
        got = _decision(_bash_payload(cmd), tmp_path / f"hf{i}")
        assert got == "BLOCK", f"HEREDOC-FC vector {i} got {got}: {cmd!r}"


def test_20_heredoc_allowlist_ok(tmp_path: Path) -> None:
    """TEST-2.0-HEREDOC-OK：允許清單內 delimiter 正確開 span。"""
    vectors = [
        "cat <<EOF-1\ncodex exec\nEOF-1\ntrue",
        "cat <<'EOF-1'\ncodex exec\nEOF-1\ntrue",
        "cat <<EOF~1\nx\nEOF~1\ntrue",
    ]
    for i, cmd in enumerate(vectors):
        got = _decision(_bash_payload(cmd), tmp_path / f"ho{i}")
        assert got == "ALLOW", f"HEREDOC-OK vector {i} got {got}: {cmd!r}"


def test_20_heredoc_nest_attack(tmp_path: Path) -> None:
    """TEST-2.0-HEREDOC-NEST：body 假 marker + 後接真派工 → BLOCK。"""
    cmd = "cat <<EOF-1\n<<INNER\nfoo\nINNER\nEOF-1\ncodex exec x"
    got = _decision(_bash_payload(cmd), tmp_path / "hn")
    assert got == "BLOCK"


# ---------------------------------------------------------------------------
# Mutations（11 項各一 + allowlist）
# ---------------------------------------------------------------------------


def _mutated_script(dest: Path, mutator) -> Path:
    """複製 gate_check.sh + _gate_lex.sh 到 dest 同目錄，mutator 可改兩者。

    mutator 簽名：``(gate_text, lex_text) -> (gate_text, lex_text)`` 或
    舊式 ``(text) -> text``（只改 gate 或只改 concat 視內容）。
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    gate_text = GATE_CHECK.read_text(encoding="utf-8")
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    # 支援單檔或雙檔 mutator
    try:
        new_gate, new_lex = mutator(gate_text, lex_text)  # type: ignore[misc]
    except TypeError:
        # 舊式：對 gate+lex 串接後改，再拆回（以 lex 檔頭為界）
        combined = gate_text + "\n###LEX###\n" + lex_text
        new_combined = mutator(combined)  # type: ignore[misc]
        assert new_combined != combined, "mutator 未改變腳本"
        if "###LEX###" in new_combined:
            new_gate, new_lex = new_combined.split("###LEX###\n", 1)
        else:
            new_gate, new_lex = new_combined, lex_text
    else:
        assert (new_gate, new_lex) != (gate_text, lex_text), "mutator 未改變腳本"
    dest.write_text(new_gate, encoding="utf-8")
    dest.chmod(0o755)
    lex_dest = dest.parent / "_gate_lex.sh"
    lex_dest.write_text(new_lex, encoding="utf-8")
    return dest


def test_20_mut_allowlist_turns_fc_allow(tmp_path: Path) -> None:
    """TEST-2.0-MUT-ALLOWLIST：⑥ 改回寬鬆 token + 去邊界 → FC 至少一條 ALLOW。"""

    def mut(text: str) -> str:
        t2 = text
        # 不再用 is_allow_delim 拒絕（排除清單式寬鬆）
        t2 = t2.replace(
            'if (tok == "" || !is_allow_delim(tok)) fail()',
            'if (tok == "") fail()',
            1,
        )
        # token 收集改「非空白即收」（排除清單語意）
        t2 = t2.replace(
            "if (c ~ /[A-Za-z0-9_.:+=,%@^~{}[\\]!*?-]/) { tok = tok c; i++; continue }",
            'if (c != " " && c != "\\t" && c != "\\n") { tok = tok c; i++; continue }',
            1,
        )
        # 移除完整 token 邊界 fail
        t2 = t2.replace(
            'if (c != " " && c != "\\t" && c != "\\n" && c != "\\r") fail()',
            "if (0) fail()",
            1,
        )
        assert t2 != text
        return t2

    script = _mutated_script(tmp_path / "mut_allowlist.sh", mut)
    vectors = [
        "cat <<E'O'F\nx\nE'O'F",
        'cat <<E"O"F\nx\nE"O"F',
        "cat <<$'EOF'\nx\nEOF",
        "cat <<E\\ F\nx",
        "cat <<EOF$(\n",
    ]
    allows = 0
    details = []
    for i, cmd in enumerate(vectors):
        got = _decision(_bash_payload(cmd), tmp_path / f"ma{i}", script=script)
        details.append(f"{i}:{got}")
        if got == "ALLOW":
            allows += 1
    assert allows >= 1, "MUT-ALLOWLIST 未使任一 FC 向量轉 ALLOW: " + ",".join(details)


def test_20_mut_11_contract_reverts(tmp_path: Path) -> None:
    """TEST-2.0-MUT-11：11 項各一 mutation → 對應語料轉錯誤方向。

    每項以「關閉該契約相關邏輯」的最小補丁驗證至少一條語料翻轉。
    """
    entries = _load_corpus_b()

    def pick(cid: str, case: str) -> dict:
        for e in entries:
            if e["contract"] == cid and e["case"] == case:
                return e
        raise AssertionError(f"no {case} for contract {cid}")

    mutations: list[tuple[str, object, dict, str]] = []
    # (name, mutator, entry, expected_wrong_direction)

    # 1：LEGACY 路徑（無引號感知）→ pgrep 轉 BLOCK
    def m1(t: str) -> str:
        return t.replace(
            '[ "${GATE_LEGACY_DECISION:-0}" = "1" ]',
            '[ "${GATE_LEGACY_DECISION:-0}" = "0" ] || true; if true',
            1,
        ).replace(
            "elif _gate_cmd_is_dispatch",
            "elif false && _gate_cmd_is_dispatch",
            1,
        )

    # 更穩：強制 LEGACY
    def m1b_legacy(t: str) -> str:
        return t.replace(
            '[ "${GATE_LEGACY_DECISION:-0}" = "1" ]',
            "[ 1 -eq 1 ]",
            1,
        )

    mutations.append(("c1", m1b_legacy, pick("1", "TN"), "BLOCK"))

    # 1b：sed 行內剝引號
    def m1b(t: str) -> str:
        return re.sub(
            r"_gate_lex_preprocess\(\) \{.*?\n\}",
            '_gate_lex_preprocess() {\n'
            '  printf \'%s\' "${1-}" | sed -E "s/\'[^\']*\'//g; s/\\"[^\\"]*\\"//g"\n'
            "}",
            t,
            count=1,
            flags=re.DOTALL,
        )

    mutations.append(("c1b", m1b, pick("1b", "TN"), "BLOCK"))

    # 2：縮回 R2 命令位置（僅 ^ ; & |）；並關 C3 cmdsub 抽取（否則 $() 仍遞迴命中）
    def m2(t: str) -> str:
        old = (
            "(^|[;&|(`]|\\$\\()[[:space:]]*((eval|xargs)[[:space:]]+)?"
            "((\\S*/)?)((codex|cursor-agent|grok|agy)[[:space:]]|(codex|cursor-agent|grok|agy)$)"
        )
        new = "(^|[;&|][[:space:]]*)((codex|cursor-agent|grok|agy)[[:space:]]|(codex|cursor-agent|grok|agy)$)"
        t2 = t.replace(old, new, 1)
        if t2 == t:
            # 後備：拿掉 ( ` $( eval xargs
            t2 = t.replace("[;&|(`]|\\$\\(", "[;&|]", 1)
            t2 = t2.replace("((eval|xargs)[[:space:]]+)?", "", 1)
        t2 = t2.replace(
            'cmdsubs="$(_gate_lex_extract_cmdsubs "$raw")"',
            'cmdsubs=""',
            1,
        )
        assert t2 != t
        return t2

    mutations.append(("c2", m2, pick("2", "TP"), "ALLOW"))

    # 3：移除 extract inners 遞迴
    def m3(t: str) -> str:
        t2 = t.replace(
            'inners="$(_gate_lex_extract_inners "$raw")"',
            'inners=""',
            1,
        )
        if t2 == t:
            t2 = t.replace(
                'inners="$(_gate_lex_extract_inners "$cmd")"',
                'inners=""',
                1,
            )
        assert t2 != t
        return t2

    mutations.append(("c3", m3, pick("3", "TP"), "ALLOW"))

    # 4：路徑前綴拿掉 + 引號內空白改 X → 引號路徑不再命中
    def m4(t: str) -> str:
        t2 = t.replace("((\\S*/)?)((codex|cursor-agent|grok|agy)", "((codex|cursor-agent|grok|agy)", 1)
        t2 = t2.replace(
            'if (c == " " || c == "\\t") { out = out "\\037"; i++; continue }',
            'if (c == " " || c == "\\t") { out = out "X"; i++; continue }',
            2,
        )
        assert t2 != t
        return t2

    mutations.append(("c4", m4, pick("4", "TP"), "ALLOW"))

    # 5：禁用 abs path 家族（\S*/ 前綴）
    def m5(t: str) -> str:
        t2 = t.replace("((\\S*/)?)((codex|cursor-agent|grok|agy)", "((codex|cursor-agent|grok|agy)", 1)
        assert t2 != t
        return t2

    mutations.append(("c5", m5, pick("5", "TP"), "ALLOW"))

    # 6：未閉合不 fail-closed
    def m6(t: str) -> str:
        return t.replace("if (inq) fail()", "if (0) fail()", 1)

    mutations.append(("c6", m6, pick("6", "TP"), "ALLOW"))

    # 7：unquoted -c 不 emit
    def m7(t: str) -> str:
        t2 = t.replace("# unquoted -c（契約 7）", "# unquoted -c DISABLED", 1)
        # 跳過 unquoted 抽取：把 emit(tok) 在 unquoted 段前改寫
        t2 = t2.replace(
            "          # unquoted -c DISABLED\n          tok = \"\"\n"
            "          while (j <= n) {\n"
            "            c = substr($0, j, 1)\n"
            '            if (c == " " || c == "\\t" || c == "\\n" || c == ";" || c == "&" || c == "|") break\n'
            "            tok = tok c; j++\n"
            "          }\n"
            "          emit(tok)",
            "          # unquoted -c DISABLED\n          tok = \"\"\n          j = n + 1",
            1,
        )
        if t2 == t:
            # 後備：直接清空 extract
            t2 = t.replace(
                'inners="$(_gate_lex_extract_inners "$cmd")"',
                'inners=""',
                1,
            )
            # 但這與 c3 相同；改為 unquoted 路徑：match 後不 emit
            t2 = t.replace("emit(tok)\n          i = j\n          continue\n        }\n        # eval",
                           "i = j\n          continue\n        }\n        # eval", 1)
        assert t2 != t
        return t2

    mutations.append(("c7", m7, pick("7", "TP"), "ALLOW"))

    # 8：逾深改 ALLOW（return 1）；用 depth-over 條目
    def m8(t: str) -> str:
        return t.replace(
            'if [ "$depth" -gt "$_GATE_LEX_MAX_DEPTH" ]; then\n    return 0\n  fi',
            'if [ "$depth" -gt "$_GATE_LEX_MAX_DEPTH" ]; then\n    return 1\n  fi',
            1,
        )

    mutations.append(("c8", m8, pick("8", "TP"), "ALLOW"))  # will re-pick depth-over below

    # 9：關閉 fail() 整體 → 未閉合/跳脫邊界不再 fail-closed
    def m9(t: str) -> str:
        t2 = t.replace(
            'function fail() { print "FAILCLOSED"; exit 1 }',
            'function fail() { print ""; exit 0 }',
            1,
        )
        assert t2 != t
        return t2

    mutations.append(("c9", m9, pick("9", "TP"), "ALLOW"))

    # 10：heredoc 解析全關
    def m10(t: str) -> str:
        return t.replace(
            'if (c == "<" && i < n && substr(src, i+1, 1) == "<") {',
            'if (0 && c == "<" && i < n && substr(src, i+1, 1) == "<") {',
            1,
        )

    mutations.append(("c10", m10, pick("10", "TN"), "BLOCK"))

    # c8 用 depth-over 條目（第二個 TP）
    c8_entries = [e for e in entries if e["contract"] == "8" and e["case"] == "TP"]
    assert len(c8_entries) >= 2
    mutations = [
        (n, m, (c8_entries[1] if n == "c8" else e), w)
        for (n, m, e, w) in mutations
    ]

    report: list[str] = []
    for name, mut, entry, wrong in mutations:
        try:
            script = _mutated_script(tmp_path / f"{name}.sh", mut)
        except AssertionError as exc:
            report.append(f"{name}: mutator no-op ({exc})")
            continue
        got = _decision(entry["payload"], tmp_path / f"mut_{name}", script=script)
        base = _decision(entry["payload"], tmp_path / f"base_{name}")
        if base == wrong:
            report.append(f"{name}: baseline already {wrong} for {entry['id']}")
            continue
        if got != wrong:
            report.append(
                f"{name}: {entry['id']} mut got={got} expected_wrong={wrong} base={base}"
            )
        else:
            report.append(f"{name}: OK mut {entry['id']} {base}->{got}")

    bad = [r for r in report if "OK mut" not in r]
    assert not bad, "MUT-11 failures:\n" + "\n".join(report)
