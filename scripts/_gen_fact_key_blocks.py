#!/usr/bin/env python3
"""fact-key 生成器之 Python 核心（FKPERF，docs/FKPERF_SPEC.md）。

取代 `scripts/gen_fact_key_blocks.sh` 之 bash 判定邏輯，使外部程序數與登記規模無關；
六種呼叫形態之 stdout、stderr、rc 與寫檔結果須與 oracle（`git show 4bdc2d562543:scripts/gen_fact_key_blocks.sh`）
逐位元組相同（SPEC C-1；具名例外四項見 C-1）。只用標準庫、以系統 python3（3.9）執行（C-5）。

移植原則：每個 bash 函式對應同名（去 `_fk_` 前綴）之方法，訊息逐字照抄；bash 之命令替換會去尾端換行、
`jq -r` 逐值加換行、`while read` 略過空行等語意，以本檔之小工具明確重現（見「jq／shell 語意」一節），
不以「看起來等價」之 Python 慣用法替代。外部程序只剩三處、次數與登記規模無關：`git`（範圍列舉與工作樹判定）
與 `bash scripts/ticket_universe.sh --check`（票全集對帳，主控端才跑）。
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

Row = List[str]

_FK_RESERVED = "_schema"
_FK_KEY_RE = "^[a-z0-9][a-z0-9-]*$"
_FK_KEY_PAT = re.compile(rb"^[a-z0-9][a-z0-9-]*$")
_FK_RENDER_MODES = "tsv table"
_FK_SCHEMA_SETS = ("status_enum", "status_keys", "status_scope", "status_scope_grandfathered")
_FK_RC_CLAIM_RES = (rb"rc[ \t\n\v\f\r]*(=|==|\xe2\x89\xa0|!=|:|\xe6\x98\xaf|\xe7\x82\xba)|rc[ \t\n\v\f\r]*\xe4\xb8\x8d\xe8\xae\x8a"
                    rb"|returncode[ \t\n\v\f\r]*(=|==|\xe2\x89\xa0|!=)|[Ee]xit[ \t\n\v\f\r]*[Cc]ode|exit[ \t\n\v\f\r]+[0-9]+"
                    rb"|\xe9\x80\x80\xe5\x87\xba\xe7\xa2\xbc|\xe7\xb5\x90\xe6\x9d\x9f\xe7\xa2\xbc|\xe9\x9d\x9e\xe9\x9b\xb6\xe9\x80\x80\xe5\x87\xba")
_FK_RC_CLAIM_PAT = re.compile(_FK_RC_CLAIM_RES)
# 涵蓋形態之具名清單（與 _FK_RC_CLAIM_RES 之分支一一對應，測試以集合相等鎖死；擴充須同改兩者）
_FK_RC_CLAIM_FORMS = "rc-op rc-unchanged returncode-op exit-code exit-n exitcode-zh endcode-zh nonzero-zh"
_FK_CRITERIA_SCHEMA_FIELDS = ("criteria_keys", "criteria_status_enum", "criteria_column_roles", "criteria_live_status")
_FK_MECHANISM_SCHEMA_FIELDS = ("mechanism_keys", "mechanism_status_enum", "mechanism_live_status",
                               "mechanism_column_roles", "mechanism_scope", "mechanism_tokens")
_FK_EVIDENCE_FORMS = "receipt assumed"
_FK_ENFORCEMENT_SCHEMA_FIELDS = ("enforcement_keys", "enforcement_side_enum", "enforcement_producer_side",
                                 "enforcement_column_roles", "enforcement_settings_path", "enforcement_closed_status",
                                 "enforcement_ticket_roles", "enforcement_ticket_allowlist")
_FK_CLOSED_STATUS = "收案"
_FK_COMPLETED_STATUSES = ("收案", "已落地", "已完成")
_FK_WAIVER_PLACEHOLDERS = ("—", "-", "無", "n/a", "N/A", "TBD", "tbd", "待填", "?")
_FK_ENF_MARK_PRE = "PreToolUse不可："
_FK_ENF_MARK_POST = "PostToolUse不可："
_FK_ENF_MARK_PART = "部分閘："
_FK_ENF_MARK_IMPL = "實作位置："
_FK_TICKET_BASIS_MARKERS = "還缺： 無殘留"
_FK_D2_NEXT_PLACEHOLDERS = ["—", "-", "無", "n/a", "N/A", "TBD", "待填"]
_WORD_BYTE = re.compile(rb"[0-9A-Za-z_-]")
_START_GAIFA = re.compile(rb"^[ \t\n\v\f\r]*- (\xf0\x9f\x94\xb4[ \t\n\v\f\r]+)?(\*\*)?\xe6\x94\xb9\xe6\xb3\x95")
_LEAD_WS = re.compile(rb"^[ \t\n\v\f\r]*")
_ALL_WS = re.compile(rb"^[ \t\n\v\f\r]*$")
_BEGIN_ANY = re.compile(rb"^<!-- BEGIN GENERATED: .* -->$", re.S)
_END_ANY = re.compile(rb"^<!-- END GENERATED: .* -->$", re.S)
_REF_PAT = re.compile(rb"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:[0-9]+")
_GOV_TOKEN = re.compile(rb"governance-[a-z0-9-]+")


# ---------------------------------------------------------------- jq／shell 語意

class JqError(Exception):
    """jq 程式之執行期錯誤（對應 jq rc=5）。"""


@dataclass(frozen=True)
class Registry:
    """已載入並物化之註冊表（rows_source／rows_filter 已展開為靜態 rows）。"""

    path: Path          # 訊息顯示用之註冊表路徑（使用者要改的檔，非暫存物化檔）
    data: Dict[str, object]
    keys: Tuple[str, ...]  # jq `keys[]` 碼點序，已排除 `_schema`（SPEC C-3）


@dataclass(frozen=True)
class Outcome:
    """一次呼叫之結果：rc 與逐位元組之 stdout／stderr。"""

    rc: int
    stdout: bytes
    stderr: bytes


def jtype(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    return "object"


def jlength(v: Any) -> Any:
    t = jtype(v)
    if t == "null":
        return 0
    if t == "boolean":
        raise JqError("boolean has no length")
    if t == "number":
        return abs(v)
    return len(v)


def _jq_num(v: Any) -> str:
    if isinstance(v, float):
        if math.isnan(v):
            return "null"
        if math.isinf(v):
            return "1.7976931348623157e+308" if v > 0 else "-1.7976931348623157e+308"
        if v.is_integer() and abs(v) < 1e17:
            return str(int(v))
        return repr(v)
    return str(v)


def _jq_str(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif o < 0x20 or o == 0x7F:
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def jdump(v: Any) -> str:
    """jq -c 之緊湊輸出。"""
    t = jtype(v)
    if t == "null":
        return "null"
    if t == "boolean":
        return "true" if v else "false"
    if t == "number":
        return _jq_num(v)
    if t == "string":
        return _jq_str(v)
    if t == "array":
        return "[" + ",".join(jdump(x) for x in v) + "]"
    return "{" + ",".join(_jq_str(k) + ":" + jdump(x) for k, x in v.items()) + "}"


def jraw(v: Any) -> str:
    """jq -r 之單值輸出（不含換行）。"""
    return v if isinstance(v, str) else jdump(v)


def jraw_lines(values: Sequence[Any]) -> str:
    """jq -r 對一串值之完整輸出（每值後接換行）。"""
    return "".join(jraw(v) + "\n" for v in values)


def cmdsub(text: str) -> str:
    """bash 命令替換：去尾端全部換行。"""
    return text.rstrip("\n")


def read_lines(text: str) -> List[str]:
    """`while IFS= read -r x; do [ -n "$x" ] || continue` 之逐行（略空行）。"""
    return [line for line in text.split("\n") if line != ""]


def _type_rank(v: Any) -> int:
    return {"null": 0, "boolean": 1, "number": 3, "string": 4, "array": 5, "object": 6}[jtype(v)] + (
        1 if isinstance(v, bool) and v else 0)


def jsort_key(v: Any) -> Any:
    t = jtype(v)
    if t == "array":
        return (_type_rank(v), [jsort_key(x) for x in v])
    if t == "object":
        return (_type_rank(v), sorted(v.keys()), [jsort_key(v[k]) for k in sorted(v.keys())])
    if t in ("null", "boolean"):
        return (_type_rank(v), 0)
    return (_type_rank(v), v)


def junique(values: Sequence[Any]) -> List[Any]:
    out: List[Any] = []
    for v in sorted(values, key=jsort_key):
        if not out or jdump(out[-1]) != jdump(v):
            out.append(v)
    return out


def jindex(arr: Any, x: Any) -> Optional[int]:
    """jq `index(x)` 於陣列輸入、非陣列參數之語意：第一個相等元素之位置。"""
    if jtype(arr) == "null":
        return None
    if jtype(arr) != "array":
        raise JqError("index on non-array")
    for i, v in enumerate(arr):
        if jeq(v, x):
            return i
    return None


def jeq(a: Any, b: Any) -> bool:
    if jtype(a) != jtype(b):
        return False
    return jdump(a) == jdump(b)


def jget(obj: Any, key: Any) -> Any:
    """jq `.[key]`：物件取鍵、陣列取索引、null 得 null；其餘型別拋錯。"""
    if obj is None:
        return None
    if isinstance(key, str):
        if isinstance(obj, dict):
            return obj.get(key)
        raise JqError("Cannot index %s with string" % jtype(obj))
    if isinstance(key, (int, float)) and not isinstance(key, bool):
        if isinstance(obj, list):
            i = int(key)
            if i < 0:
                i += len(obj)
            return obj[i] if 0 <= i < len(obj) else None
        raise JqError("Cannot index %s with number" % jtype(obj))
    raise JqError("Cannot index %s with %s" % (jtype(obj), jtype(key)))


def jiter(v: Any) -> List[Any]:
    """jq `.[]`。"""
    if isinstance(v, list):
        return list(v)
    if isinstance(v, dict):
        return list(v.values())
    raise JqError("Cannot iterate over %s" % jtype(v))


def jhas(obj: Any, key: str) -> bool:
    if not isinstance(obj, dict):
        raise JqError("Cannot check whether %s has a string key" % jtype(obj))
    return key in obj


def jtruthy(v: Any) -> bool:
    return not (v is None or v is False)


def is_cntrl(s: str) -> bool:
    """Oniguruma `[[:cntrl:]]`（UTF-8）＝Unicode Cc：U+0000–001F、U+007F–009F（2026-09-24 主委以 jq 1.7.1 實測）。"""
    return any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F for c in s)


def jstr_len_ok(v: Any) -> bool:
    return isinstance(v, str) and len(v) > 0


def tsv_escape(v: Any) -> str:
    """jq `@tsv`（rows 已驗為字串）。"""
    if isinstance(v, str):
        return v.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return _jq_num(v)
    raise JqError("is not valid in a csv row")


def to_b(s: str) -> bytes:
    return s.encode("utf-8", "surrogateescape")


def from_b(b: bytes) -> str:
    return b.decode("utf-8", "surrogateescape")


def _load_json_text(raw: bytes) -> Any:
    """jq 1.7.1 可接受之單一 JSON 值（含 NaN／Infinity 字面；無效 UTF-8 以 U+FFFD 取代）。"""
    text = raw.decode("utf-8", "replace")
    dec = json.JSONDecoder()
    i = 0
    n = len(text)
    ws = " \t\n\r"
    while i < n and text[i] in ws:
        i += 1
    val, j = dec.raw_decode(text, i)
    while j < n and text[j] in ws:
        j += 1
    if j != n:
        raise ValueError("trailing data")
    return val


def json_value_count(raw: bytes) -> int:
    """`jq -s 'length'`：檔內 JSON 值之個數；非法 ⇒ ValueError。"""
    text = raw.decode("utf-8", "replace")
    dec = json.JSONDecoder()
    i, n, count = 0, len(text), 0
    ws = " \t\n\r"
    while True:
        while i < n and text[i] in ws:
            i += 1
        if i >= n:
            return count
        _, i = dec.raw_decode(text, i)
        count += 1


def jinterp(v: Any) -> str:
    """jq 字串內插 `\\(x)`：字串原樣、其餘 tojson。"""
    return v if isinstance(v, str) else jdump(v)


def jjoin(values: Sequence[Any], sep: str) -> str:
    parts = []
    for v in values:
        if v is None:
            parts.append("")
        elif isinstance(v, str):
            parts.append(v)
        elif isinstance(v, bool) or isinstance(v, (int, float)):
            parts.append(jdump(v))
        else:
            raise JqError("Cannot join with %s" % jtype(v))
    return sep.join(parts)


def jgroup_by(items: Sequence[Any], keyf) -> List[List[Any]]:
    decorated = sorted(((jsort_key(keyf(x)), jdump(keyf(x)), i, x) for i, x in enumerate(items)),
                       key=lambda t: (t[0], t[2]))
    groups: List[List[Any]] = []
    last = None
    for _, dumped, _, x in decorated:
        if groups and dumped == last:
            groups[-1].append(x)
        else:
            groups.append([x])
            last = dumped
    return groups


def sort_u_lines(text: str) -> str:
    """`… | LC_ALL=C sort -u` 之輸出（含每行換行）。"""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    uniq = sorted(set(to_b(x) for x in lines))
    return "".join(from_b(x) + "\n" for x in uniq)


def sed_indent(text: str) -> str:
    """`printf '%s\\n' "$x" | sed 's/^/    /'`。"""
    return "".join("    " + line + "\n" for line in text.split("\n"))


class Exit(Exception):
    def __init__(self, rc: int) -> None:
        super().__init__(rc)
        self.rc = rc


def _has_token(s: bytes, t: bytes) -> bool:
    """awk has_token：以原始行＋絕對位置判整詞（位元組；鄰接位元組不屬 [0-9A-Za-z_-] 即邊界）。"""
    off = 0
    rest = s
    while True:
        p = rest.find(t)
        if p < 0 or not t:
            return False
        st = off + p  # 0-based
        pre = s[st - 1:st] if st > 0 else b""
        post = s[st + len(t):st + len(t) + 1]
        if not _WORD_BYTE.fullmatch(pre or b"!") and not _WORD_BYTE.fullmatch(post or b"!"):
            return True
        off = st + len(t) - 1 + 1
        rest = s[off:]


def status_hit(s: bytes, ids: Sequence[bytes], enum: Sequence[bytes]) -> Optional[Tuple[bytes, bytes]]:
    """`_FK_HIT_AWK` 之 fk_status_hit：先取第一個出現之狀態字面，再取第一個整詞識別碼。"""
    hit_e = None
    for e in enum:
        if e and e in s:
            hit_e = e
            break
    if hit_e is None:
        return None
    for i in ids:
        if i and _has_token(s, i):
            return i, hit_e
    return None


def awk_lines(data: bytes) -> List[bytes]:
    """awk 逐記錄：以 \\n 切，末段無換行仍為一行。"""
    if not data:
        return []
    parts = data.split(b"\n")
    if parts[-1] == b"":
        parts.pop()
    return parts


class Gen:
    """一次呼叫之狀態：註冊表（原始與物化）、輸出緩衝。對應 oracle 之全域變數。"""

    def __init__(self, script_dir: str) -> None:
        self.script_dir = script_dir
        self.reg = script_dir + "/fact_keys.json"
        self.reg_src = self.reg
        self.orig: Any = None
        self.data: Any = None
        self.out = bytearray()
        self.errbuf = bytearray()
        self._files: Dict[bytes, bytes] = {}
        self._lines: Dict[bytes, List[bytes]] = {}
        self._marks: Dict[bytes, Dict[bytes, List[int]]] = {}
        self._targets: Dict[str, Tuple[List[str], Optional[str]]] = {}

    # ------------------------------------------------------------ 讀檔快取（SPEC Task 4.4：開檔數與登記規模無關）
    def read_bytes(self, path: Any) -> bytes:
        """同一次呼叫內每個路徑只開一次；`--write` 改寫後以新內容更新（oracle 每次重讀，語意相同）。"""
        key = os.fsencode(path)
        if key not in self._files:
            with open(key, "rb") as fh:
                self._files[key] = fh.read()
        return self._files[key]

    def remember(self, path: Any, data: bytes) -> None:
        key = os.fsencode(path)
        self._files[key] = data
        self._lines.pop(key, None)
        self._marks.pop(key, None)

    # FKPERF Task 4.4（規模驗收實測：每 key 重切整份宿主為行，成本隨 key 數平方成長）：每路徑只切一次行、
    # 只建一次標記索引；語意與逐次重切相同（快取隨 remember 失效）。
    def lines_of(self, path: Any) -> List[bytes]:
        key = os.fsencode(path)
        if key not in self._lines:
            self._lines[key] = awk_lines(self.read_bytes(path))
        return self._lines[key]

    def marks_of(self, path: Any) -> Dict[bytes, List[int]]:
        """生成區塊標記行 → 其行號（升冪）。"""
        key = os.fsencode(path)
        if key not in self._marks:
            idx: Dict[bytes, List[int]] = {}
            for i, ln in enumerate(self.lines_of(path)):
                if ln.startswith(b"<!-- BEGIN GENERATED: ") or ln.startswith(b"<!-- END GENERATED: "):
                    idx.setdefault(ln, []).append(i)
            self._marks[key] = idx
        return self._marks[key]

    # ------------------------------------------------------------ 輸出
    def err(self, s: str) -> None:
        self.errbuf += to_b(s) + b"\n"

    def err_raw(self, s: str) -> None:
        self.errbuf += to_b(s)

    def err_b(self, b: bytes) -> None:
        self.errbuf += b

    def die(self, s: str) -> None:
        self.err(s)
        raise Exit(1)

    def root(self) -> str:
        return os.environ.get("GOVB1_FACTKEY_ROOT") or "."

    def repo_logical(self) -> str:
        """`cd -- "${SCRIPT_DIR}/.." && pwd`（邏輯路徑）。"""
        return os.path.normpath(self.script_dir + "/..")

    def repo_physical(self) -> str:
        """`cd -- "${SCRIPT_DIR}/.." && pwd -P`。"""
        return os.path.realpath(self.script_dir + "/..")

    # ------------------------------------------------------------ preflight／物化
    def preflight(self) -> None:
        if not os.path.isfile(self.reg):
            self.die("gen_fact_key_blocks: 缺註冊表 %s → fail-closed" % self.reg)
        try:
            with open(self.reg, "rb") as fh:
                val = _load_json_text(fh.read())
        except (OSError, ValueError):
            val = None
        if not isinstance(val, dict):
            self.die("gen_fact_key_blocks: 註冊表 %s 非合法 JSON 物件 → fail-closed" % self.reg)
        self.orig = val
        self.data = val

    def rows_source_rows(self, k: str, repo: str) -> Optional[list]:
        v = self.orig.get(k)
        if jhas(v, "rows") or jhas(v, "rows_filter"):
            self.err("gen_fact_key_blocks: key %s 之 rows_source 與 rows／rows_filter 並存（三者擇一）→ fail-closed" % k)
            return None
        rs = v.get("rows_source")
        ok = (isinstance(rs, dict) and sorted(rs.keys()) == ["file", "path"]
              and jstr_len_ok(rs.get("file")) and not is_cntrl(rs["file"])
              and isinstance(rs.get("path"), list) and len(rs["path"]) > 0
              and all(jstr_len_ok(x) for x in rs["path"]))
        if not ok:
            self.err("gen_fact_key_blocks: key %s 之 rows_source 形式不符（須恰為 {file: 非空字串, path: 非空字串陣列}）→ fail-closed" % k)
            return None
        f = rs["file"]
        if f.startswith("/"):
            self.err("gen_fact_key_blocks: key %s 之 rows_source.file 為絕對路徑（%s）→ fail-closed" % (k, f))
            return None
        wrapped = "/" + f + "/"
        if "/../" in wrapped or "/./" in wrapped or "//" in wrapped:
            self.err("gen_fact_key_blocks: key %s 之 rows_source.file 含 .／.. 或空路徑段（%s）→ fail-closed" % (k, f))
            return None
        path = repo + "/" + f
        if os.path.islink(path):
            self.err("gen_fact_key_blocks: key %s 之 rows_source.file 為 symlink（%s）→ fail-closed" % (k, f))
            return None
        if not os.path.isfile(path):
            self.err("gen_fact_key_blocks: key %s 之 rows_source.file 不存在或非一般檔（%s）→ fail-closed" % (k, f))
            return None
        real = os.path.realpath(os.path.dirname(path))
        if not (real + "/").startswith(repo + "/"):
            self.err("gen_fact_key_blocks: key %s 之 rows_source.file 實體路徑在 repo 外（%s）→ fail-closed" % (k, f))
            return None
        try:
            raw = self.read_bytes(path)
            count = json_value_count(raw)
        except (OSError, ValueError):
            count = -1
        if count != 1:
            self.err("gen_fact_key_blocks: key %s 之 rows_source.file 非單一合法 JSON 值（%s）→ fail-closed" % (k, f))
            return None
        doc = _load_json_text(raw)
        p = rs["path"]
        cur = doc
        found = True
        for seg in p:
            if isinstance(cur, dict) and seg in cur:
                cur = cur[seg]
            else:
                found = False
                break
        if not found:
            self.err("gen_fact_key_blocks: key %s 之 rows_source.path %s 在 %s 中不存在 → fail-closed" % (k, jdump(p), f))
            return None
        if not (isinstance(cur, list) and all(isinstance(x, str) for x in cur)):
            self.err("gen_fact_key_blocks: key %s 之 rows_source 所指值非字串陣列（%s %s）→ fail-closed" % (k, f, jdump(p)))
            return None
        if len(cur) > 999:
            self.err("gen_fact_key_blocks: key %s 之 rows_source 元素逾 999（三位序號不足以保序）→ fail-closed" % k)
            return None
        return [[("00" + str(i + 1))[-3:], x] for i, x in enumerate(cur)]

    def rows_filter_rows(self, k: str, cur: dict) -> Optional[list]:
        v = self.orig.get(k)
        if jhas(v, "rows") or jhas(v, "rows_source"):
            self.err("gen_fact_key_blocks: key %s 之 rows_filter 與 rows／rows_source 並存（三者擇一）→ fail-closed" % k)
            return None

        def names(x: Any) -> bool:
            return (isinstance(x, list) and len(x) > 0 and all(jstr_len_ok(e) for e in x)
                    and len(x) == len(set(x)))

        rf = v.get("rows_filter")
        ok = (isinstance(rf, dict) and sorted(rf.keys()) == ["allow", "source_keys", "status_column"]
              and names(rf.get("source_keys")) and names(rf.get("allow")) and jstr_len_ok(rf.get("status_column")))
        if not ok:
            self.err("gen_fact_key_blocks: key %s 之 rows_filter 形式不符（須恰為 {source_keys, status_column, allow}；陣列非空、元素非空不重複）→ fail-closed" % k)
            return None
        try:
            enum = jget(jget(self.orig, "_schema"), "status_enum")
            if jtype(enum) != "array":
                raise JqError("status_enum")
            bad = [a for a in rf["allow"] if not any(jeq(a, e) for e in enum)]
        except JqError:
            self.err("gen_fact_key_blocks: key %s 之 rows_filter.allow 無法對照 _schema.status_enum（缺席或非陣列）→ fail-closed" % k)
            return None
        if bad:
            self.err("gen_fact_key_blocks: key %s 之 rows_filter.allow 含 status_enum 以外之值：%s→ fail-closed"
                     % (k, cmdsub(jraw_lines(bad)).replace("\n", " ")))
            return None
        cols = v.get("columns")
        if not (isinstance(cols, list) and len(cols) >= 2 and jeq(cols[0], "序")):
            self.err("gen_fact_key_blocks: key %s 用 rows_filter 須宣告 columns 且首欄為『序』、至少一個投影欄（唯一排序點會重排列，序號欄保存來源順序）→ fail-closed" % k)
            return None
        rc = 0
        for s in read_lines(cmdsub(jraw_lines(rf["source_keys"]))):
            if s == k or s == _FK_RESERVED:
                self.err("gen_fact_key_blocks: key %s 之 rows_filter 來源 key 不得為自身或保留鍵（%s）→ fail-closed" % (k, s))
                rc = 1
                continue
            if not (s in cur and isinstance(cur[s], dict)):
                self.err("gen_fact_key_blocks: key %s 之 rows_filter 來源 key 不存在：%s → fail-closed" % (k, s))
                rc = 1
                continue
            if "rows_filter" in cur[s]:
                self.err("gen_fact_key_blocks: key %s 之 rows_filter 來源 key %s 本身亦為 rows_filter（不支援串接）→ fail-closed" % (k, s))
                rc = 1
                continue
            col = cur[k]["rows_filter"]["status_column"]
            need = cur[k]["columns"][1:]
            sc = cur[s].get("columns")
            if jtype(sc) != "array":
                miss = "（來源未宣告 columns）"
            else:
                miss = " ".join(c for c in junique([col] + list(need)) if jindex(sc, c) is None)
            if miss:
                self.err("gen_fact_key_blocks: key %s 之 rows_filter 來源 key %s 缺欄：%s → fail-closed" % (k, s, miss))
                rc = 1
                continue
            width = len(sc)
            rows = cur[s].get("rows")
            if not (isinstance(rows, list) and all(isinstance(r, list) and len(r) == width for r in rows)):
                self.err("gen_fact_key_blocks: key %s 之 rows_filter 來源 key %s 之 rows 缺席或列長與 columns 不符 → fail-closed" % (k, s))
                rc = 1
                continue
        if rc:
            return None
        srcs = rf["source_keys"]
        if not (len(srcs) <= 99 and all(jlength(cur[s].get("rows")) <= 999 for s in srcs)):
            self.err("gen_fact_key_blocks: key %s 之 rows_filter 逾序號位數（來源 key 數限兩位、單一來源列數限三位）→ fail-closed" % k)
            return None
        need = cur[k]["columns"][1:]
        out = []
        for si, s in enumerate(srcs):
            sc = cur[s]["columns"]
            sti = jindex(sc, rf["status_column"])
            for ri, row in enumerate(cur[s]["rows"]):
                if jindex(rf["allow"], jget(row, sti)) is None:
                    continue
                seq = ("0" + str(si + 1))[-2:] + "-" + ("00" + str(ri + 1))[-3:]
                out.append([seq] + [jget(row, jindex(sc, c)) for c in need])
        return out

    def materialize(self) -> None:
        decl = []
        for key, val in self.orig.items():
            if key != "_schema" and isinstance(val, dict):
                if "rows_source" in val:
                    decl.append(("S", key))
                elif "rows_filter" in val:
                    decl.append(("F", key))
        if not decl:
            return
        repo = self.repo_physical()
        cur = json.loads(json.dumps(self.orig))
        rc = 0
        for kind in ("S", "F"):
            for t, k in decl:
                if t != kind:
                    continue
                rows = self.rows_source_rows(k, repo) if kind == "S" else self.rows_filter_rows(k, cur)
                if rows is None:
                    rc = 1
                    continue
                cur[k]["rows"] = rows
        if rc:
            raise Exit(1)
        self.data = cur

    # ------------------------------------------------------------ keys／targets／rows／shape
    def raw_keys(self) -> List[str]:
        return read_lines(cmdsub(jraw_lines(sorted(self.data.keys()))))

    def validate_keys(self) -> bool:
        bad = ""
        for k in self.raw_keys():
            if k == _FK_RESERVED:
                continue
            if not _FK_KEY_PAT.match(to_b(k)) or b"\n" in to_b(k):
                bad += k + "\n"
        if bad:
            self.err_raw("gen_fact_key_blocks: fact-key 名稱不合法（須符 %s）→ fail-closed:\n%s" % (_FK_KEY_RE, bad))
            return False
        return True

    def keys(self) -> List[str]:
        return [k for k in self.raw_keys() if k != _FK_RESERVED]

    def targets(self, k: str, quiet: bool = False) -> Optional[str]:
        """`_fk_targets`：成功回傳清單文字（命令替換後），失敗回傳 None（`quiet`＝2>/dev/null）。
        結果依 key 記憶（註冊表於一次呼叫內不變）；oracle 每次呼叫都重印訊息，故非 quiet 時照樣重放。"""
        if k not in self._targets:
            msgs: List[str] = []
            self._targets[k] = (msgs, self._targets_compute(k, msgs.append))
        msgs, result = self._targets[k]
        if not quiet:
            for m in msgs:
                self.err(m)
        return result

    def _targets_compute(self, k: str, say) -> Optional[str]:
        try:
            t = jget(jget(self.data, k), "target")
            ty = jtype(t)
        except JqError:
            ty = ""
            t = None
        if ty == "string":
            lst = cmdsub(jraw_lines([t] if jtruthy(t) else []))
        elif ty == "array":
            if not all(isinstance(x, str) for x in t):
                say("gen_fact_key_blocks: key %s 之 target 陣列含非字串元素 → fail-closed" % k)
                return None
            lst = cmdsub(jraw_lines(t))
        else:
            say("gen_fact_key_blocks: key %s 之 target 型別不符（須 string 或 array of string）→ fail-closed" % k)
            return None
        if lst == "":
            say("gen_fact_key_blocks: key %s 缺 target 或 target 為空陣列 → fail-closed" % k)
            return None
        lines = lst.split("\n")
        if len(lines) != len(set(to_b(x) for x in lines)):
            say("gen_fact_key_blocks: key %s 之 target 含重複路徑 → fail-closed" % k)
            return None
        rc = 0
        for line in lines:
            if not line:
                continue
            if line.startswith("/"):
                say("gen_fact_key_blocks: key %s 之 target 不得為絕對路徑：%s" % (k, line))
                rc = 1
            elif ".." in line:
                say("gen_fact_key_blocks: key %s 之 target 不得含 ..：%s" % (k, line))
                rc = 1
        if rc:
            return None
        return lst

    def validate_rows(self, k: str) -> bool:
        try:
            rows = jget(jget(self.data, k), "rows")
            ok = isinstance(rows, list) and all(isinstance(r, list) and all(isinstance(c, str) for c in r) for r in rows)
        except JqError:
            ok = False
        if not ok:
            self.err("gen_fact_key_blocks: key %s 之 rows 型別不符（須為字串陣列之陣列）→ fail-closed" % k)
        return ok

    def shape_codes(self, k: str) -> List[str]:
        def ok(f) -> bool:
            try:
                return bool(jtruthy(f()))
            except (JqError, TypeError, KeyError, IndexError):
                return False

        obj = jget(self.data, k)
        try:
            rty = (jtype(obj["render"]) if "render" in obj else "absent") if isinstance(obj, dict) else jhas(obj, "render")
        except JqError:
            rty = ""
        try:
            cty = (jtype(obj["columns"]) if "columns" in obj else "absent") if isinstance(obj, dict) else jhas(obj, "columns")
        except JqError:
            cty = ""
        rv = obj["render"] if rty == "string" else None
        mode = rv if (rty == "string" and (" " + rv + " ") in (" " + _FK_RENDER_MODES + " ")) else "tsv"
        codes: List[str] = []
        if rty == "absent":
            pass
        elif rty == "string":
            if mode != rv:
                codes.append("render-mode")
        else:
            codes.append("render-type")

        def cols_ok() -> bool:
            c = jget(obj, "columns")
            return (jtype(c) == "array" and len(c) > 0
                    and all(isinstance(e, str) and len(e) > 0 and not (("|" in e) or is_cntrl(e)) for e in c)
                    and len(c) == len(junique(c)))

        def width_ok() -> bool:
            n = jlength(jget(obj, "columns"))
            rows = jget(obj, "rows")
            return all(jlength(r) == n for r in jiter(rows))

        if cty == "absent":
            if mode == "table":
                codes.append("table-no-columns")
        else:
            if not ok(cols_ok):
                codes.append("columns")
            if not ok(width_ok):
                codes.append("row-width")

        def cells(pred) -> bool:
            rows = jget(obj, "rows")
            for r in jiter(rows):
                for c in jiter(r):
                    if not isinstance(c, str):
                        raise JqError("test on non-string")
                    if pred(c):
                        return False
            return True

        if not ok(lambda: cells(is_cntrl)):
            codes.append("cell-cntrl")
        if mode == "table" and not ok(lambda: cells(lambda c: "|" in c)):
            codes.append("cell-pipe")
        return codes

    def validate_shape(self, k: str) -> bool:
        codes = self.shape_codes(k)
        for c in codes:
            if c == "render-mode":
                self.err("gen_fact_key_blocks: key %s 之 render='%s' 不在 {%s} → fail-closed"
                         % (k, jraw(jget(jget(self.data, k), "render")), _FK_RENDER_MODES))
            elif c == "render-type":
                self.err("gen_fact_key_blocks: key %s 之 render 型別不符（須字串）→ fail-closed" % k)
            elif c == "table-no-columns":
                self.err("gen_fact_key_blocks: key %s render=table 但未宣告 columns（無表頭）→ fail-closed" % k)
            elif c == "columns":
                self.err("gen_fact_key_blocks: key %s 之 columns 非法（須非空字串陣列；元素非空、不重複、不含 | 或任何控制字元）→ fail-closed" % k)
            elif c == "row-width":
                self.err("gen_fact_key_blocks: key %s 有列之欄數與 columns 宣告不符 → fail-closed" % k)
            elif c == "cell-cntrl":
                self.err("gen_fact_key_blocks: key %s 之儲存格含控制字元（破壞逐列語義）→ fail-closed" % k)
            elif c == "cell-pipe":
                self.err("gen_fact_key_blocks: key %s render=table 之儲存格含 |（會切碎表格）→ fail-closed" % k)
        return not codes

    def render_of(self, k: str) -> str:
        r = jget(jget(self.data, k), "render")
        return jraw(r) if jtruthy(r) else "tsv"

    # ------------------------------------------------------------ 生成
    def rows_tsv(self, k: str) -> List[bytes]:
        rows = jget(jget(self.data, k), "rows")
        lines = [to_b("\t".join(tsv_escape(c) for c in jiter(r))) for r in jiter(rows)]
        return sorted(lines)

    def gen_block_bytes(self, k: str) -> bytes:
        out = bytearray(to_b("<!-- BEGIN GENERATED: %s -->\n" % k))
        mode = self.render_of(k)
        if mode == "table":
            cols = jget(jget(self.data, k), "columns")
            out += to_b("| " + jjoin(cols, " | ") + " |\n")
            out += to_b("|" + "|".join("---" for _ in cols) + "|\n")
            for line in self.rows_tsv(k):
                fields = line.split(b"\t") if line else []
                out += b"|" + b"".join(b" " + f + b" |" for f in fields) + b"\n"
        else:
            for line in self.rows_tsv(k):
                out += line + b"\n"
        out += to_b("<!-- END GENERATED: %s -->\n" % k)
        return bytes(out)

    # ------------------------------------------------------------ 宿主
    def markers_ok(self, k: str, path: str, rel: str) -> bool:
        b = to_b("<!-- BEGIN GENERATED: %s -->" % k)
        e = to_b("<!-- END GENERATED: %s -->" % k)
        try:
            marks = self.marks_of(path)
        except OSError:
            marks = {}
        nb = len(marks.get(b, ()))
        ne = len(marks.get(e, ()))
        if nb == 1 and ne == 1:
            return True
        self.err("FACTKEY MARKER: %s in %s（BEGIN=%d END=%d，須各恰 1）→ fail-closed" % (k, rel, nb, ne))
        return False

    def all_targets(self) -> Optional[List[str]]:
        out = ""
        rc = 0
        for k in self.keys():
            t = self.targets(k)
            if t is None:
                rc = 1
                continue
            out += t + "\n"
        if rc:
            return None
        return read_lines(sort_u_lines(out))

    def reject_unregistered_blocks(self) -> bool:
        root = self.root()
        rc = 0
        keys = self.keys()
        tgts = self.all_targets()
        if tgts is None:
            return False
        keyset = set(keys)
        for tgt in tgts:
            path = root + "/" + tgt
            if not os.path.isfile(path):
                continue
            data = self.read_bytes(path)
            for ln in awk_lines(data):
                m = re.match(rb"^<!-- BEGIN GENERATED: (.*) -->$", ln, re.S)
                if not m:
                    continue
                found = from_b(m.group(1))
                for f in read_lines(found):
                    if f in keyset:
                        continue
                    self.err("FACTKEY UNREGISTERED BLOCK: '%s' in %s（不在 %s）→ fail-closed" % (f, tgt, self.reg_src))
                    rc = 1
        return rc == 0

    def scope_files(self) -> Optional[List[bytes]]:
        root = self.root()
        r = subprocess.run(["git", "-C", root, "rev-parse", "--is-inside-work-tree"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode != 0:
            self.err("FACTKEY SCAN: %s 非 git 工作樹 ⇒ fail-closed（不得靜默退回只掃 target）" % root)
            return None
        schema = jget(self.data, "_schema")
        scope = [to_b(x) for x in read_lines(cmdsub(jraw_lines(jiter(jget(schema, "status_scope")))))]
        gf_list = [to_b(x) for x in read_lines(cmdsub(jraw_lines(jiter(jget(schema, "status_scope_grandfathered")))))]
        ls = subprocess.run(["git", "-C", root, "-c", "core.quotePath=false", "ls-files", "--cached", "--others",
                             "--exclude-standard", "-z"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        encoded = ls.stdout.replace(b"\n", b"\x01").replace(b"\0", b"\n")
        ex = set(gf_list)
        exa = [q for q in gf_list if q.endswith(b"/")]
        out: List[bytes] = []
        for p in awk_lines(cmdsub_b(encoded)):
            if p == b"" or p in ex:
                continue
            if any(p.startswith(q) for q in exa):
                continue
            hit = False
            for s in scope:
                if s.endswith(b"/"):
                    if p.startswith(s):
                        hit = True
                elif p == s:
                    hit = True
            if hit:
                out.append(p)
        return out

    def status_ids(self) -> List[bytes]:
        vals = []
        for k in jiter(jget(jget(self.data, "_schema"), "status_keys")):
            for row in jiter(jget(jget(self.data, k), "rows")):
                vals.append(jget(row, 1))
        text = sort_u_lines(jraw_lines(vals))
        return [x for x in awk_lines(to_b(text)) if x]

    def enum_list(self) -> List[bytes]:
        return [x for x in awk_lines(to_b(jraw_lines(jiter(jget(jget(self.data, "_schema"), "status_enum"))))) if x]

    def legal_keys_for(self, rel: str, keys: Sequence[str]) -> set:
        legal = set()
        for k in keys:
            t = self.targets(k, quiet=True)
            if t is not None and rel in t.split("\n"):
                legal.add(k)
        return legal

    def reject_handwritten_status(self) -> bool:
        keys = self.keys()
        if not keys:
            return True
        root = self.root()
        files = self.scope_files()
        if files is None:
            return False
        if not files:
            return True
        rc = 0
        for f in files:
            p = to_b(root) + b"/" + f.replace(b"\x01", b"\n")
            if os.path.islink(p):
                self.err("FACTKEY SCAN: %s 為 symlink ⇒ fail-closed" % from_b(f))
                rc = 1
                continue
            if not os.path.isfile(p):
                self.err("FACTKEY SCAN: %s 非 regular file（submodule／缺檔）⇒ fail-closed" % from_b(f))
                rc = 1
        if rc:
            return False
        try:
            ids = self.status_ids()
            enum = self.enum_list()
        except JqError:
            return False
        out = bytearray()
        for f in files:
            real = f.replace(b"\x01", b"\n")
            legal = self.legal_keys_for(from_b(real), keys)
            rel = f.replace(b"\x01", b"<LF>")
            lines = awk_lines(self.read_bytes(to_b(root) + b"/" + real))
            inblk = False
            for n, ln in enumerate(lines, 1):
                if _BEGIN_ANY.match(ln):
                    k = re.sub(rb"^<!-- BEGIN GENERATED: ", b"", ln, count=1)
                    k = re.sub(rb" -->$", b"", k, count=1)
                    if from_b(k) in legal:
                        inblk = True
                        continue
                    out += b"FACTKEY FAKE BLOCK: " + rel + b":" + str(n).encode() + b" \xe6\x9c\xaa\xe7\x99\xbb\xe8\xa8\x98\xe6\x88\x96\xe9\x9d\x9e\xe6\x9c\xac\xe6\xaa\x94\xe4\xb9\x8b\xe7\x94\x9f\xe6\x88\x90\xe6\xa8\x99\xe8\xa8\x98 '" + k + b"' \xe2\x86\x92 fail-closed\n"
                    continue
                if _END_ANY.match(ln):
                    k = re.sub(rb"^<!-- END GENERATED: ", b"", ln, count=1)
                    k = re.sub(rb" -->$", b"", k, count=1)
                    if from_b(k) in legal:
                        inblk = False
                    continue
                if inblk:
                    continue
                hit = status_hit(ln, ids, enum)
                if hit:
                    out += (b"FACTKEY HANDWRITTEN STATUS: " + rel + b":" + str(n).encode() + to_b(" 識別碼=")
                            + hit[0] + to_b(" 狀態=") + hit[1] + b"\n")
        text = bytes(out).rstrip(b"\n")
        if text:
            self.err_b(text + b"\n")
            self.err("FACTKEY: 區塊外手寫狀態／假生成標記（改資料檔＋--write，或改為指向區塊之指標）→ fail-closed")
            return False
        return True


def cmdsub_b(b: bytes) -> bytes:
    return b.rstrip(b"\n")


def _schema_has(data: Any, f: str) -> bool:
    try:
        return jhas(jget(data, "_schema"), f)
    except JqError:
        return False


def _sch(data: Any, f: str) -> Any:
    return jget(jget(data, "_schema"), f)


def _gen_role_idx(self: "Gen", k: str, role: str, rf: str) -> Optional[int]:
    """`_fk_role_idx_of`：角色 → columns 內之 0-based 索引；未宣告或查無 ⇒ None。"""
    try:
        name = jget(_sch(self.data, rf), role)
        if name is None:
            return None
        cols = jget(jget(self.data, k), "columns")
        if isinstance(cols, str):
            if not isinstance(name, str):
                return None
            pos = cols.find(name)
            return pos if pos >= 0 else None
        idx = jindex(cols, name)
        return idx
    except JqError:
        return None


Gen.role_idx_of = _gen_role_idx  # type: ignore[attr-defined]


def _keys_opt(self: "Gen", field: str) -> List[str]:
    """`jq -r '._schema.<field>[]? // empty'`。"""
    try:
        v = _sch(self.data, field)
    except JqError:
        return []
    try:
        vals = jiter(v)
    except JqError:
        vals = []
    vals = [x for x in vals if jtruthy(x)]
    return read_lines(cmdsub(jraw_lines(vals)))


def _validate_criteria(self: "Gen") -> bool:
    if not any(_schema_has(self.data, f) for f in _FK_CRITERIA_SCHEMA_FIELDS):
        return True
    rc = 0
    for f in _FK_CRITERIA_SCHEMA_FIELDS:
        if not _schema_has(self.data, f):
            self.err("gen_fact_key_blocks: _schema 已宣告部分判準欄，但缺 %s → fail-closed（判準 schema 為一整組，不得單獨刪）" % f)
            rc = 1
    if rc:
        return False
    ckeys = _keys_opt(self, "criteria_keys")
    if not ckeys:
        self.err("gen_fact_key_blocks: _schema.criteria_keys 為空 → fail-closed（空清單會使三道判準檢查全部靜默停用）")
        return False
    enum = _sch(self.data, "criteria_status_enum")
    if not (isinstance(enum, list) and len(enum) > 0 and all(isinstance(x, str) for x in enum)):
        self.err("gen_fact_key_blocks: _schema.criteria_status_enum 非法 → fail-closed")
        return False
    live_v = _sch(self.data, "criteria_live_status")
    live = cmdsub(jraw(live_v) + "\n") if jtruthy(live_v) else ""
    if not live:
        self.err("gen_fact_key_blocks: _schema.criteria_live_status 缺席或為空 → fail-closed")
        return False
    if jindex(enum, live) is None:
        self.err("gen_fact_key_blocks: criteria_live_status='%s' 不在 criteria_status_enum 內 → fail-closed" % live)
        return False
    allk = set(self.keys())
    for k in ckeys:
        if k not in allk:
            self.err("gen_fact_key_blocks: criteria_keys 含未註冊 key '%s' → fail-closed" % k)
            rc = 1
            continue
        bad = "".join(" " + r for r in ("id", "scope", "condition", "expect", "status", "oracle")
                      if self.role_idx_of(k, r, "criteria_column_roles") is None)
        if bad:
            self.err("gen_fact_key_blocks: key %s 缺角色欄（criteria_column_roles 未宣告或 columns 無該欄）:%s → fail-closed" % (k, bad))
            rc = 1
            continue
        si = self.role_idx_of(k, "status", "criteria_column_roles")
        rows = jiter(jget(jget(self.data, k), "rows"))
        unknown = [jget(r, si) for r in rows if not any(jeq(jget(r, si), e) for e in enum)]
        unk = cmdsub(sort_u_lines(jraw_lines(unknown)))
        if unk:
            self.err("gen_fact_key_blocks: key %s 之狀態值不在 criteria_status_enum 內 → fail-closed:" % k)
            self.err_raw(sed_indent(unk))
            rc = 1
        sci = self.role_idx_of(k, "scope", "criteria_column_roles")
        ci = self.role_idx_of(k, "condition", "criteria_column_roles")
        ei = self.role_idx_of(k, "expect", "criteria_column_roles")
        live_rows = [r for r in rows if jeq(jget(r, si), live)]
        lines = []
        for g in jgroup_by(live_rows, lambda r: [jget(r, sci), jget(r, ci)]):
            exps = junique([jget(r, ei) for r in g])
            if len(exps) > 1:
                lines.append("  %s ／ %s ⇒ 期望值 %s" % (jinterp(jget(g[0], sci)), jinterp(jget(g[0], ci)), jjoin(exps, "、")))
        conf = cmdsub(jraw_lines(lines))
        if conf:
            self.err("gen_fact_key_blocks: key %s 有互斥判準（同適用範圍同條件、狀態為現行、期望相異）→ fail-closed:" % k)
            self.err(conf)
            rc = 1
    return rc == 0


Gen.validate_criteria = _validate_criteria  # type: ignore[attr-defined]


def _awk_block_scan(data: bytes, legal: set):
    """合法生成區塊外之行（逐行 yield (行號, 內容)）；標記行本身不 yield。"""
    inblk = False
    for n, ln in enumerate(awk_lines(data), 1):
        if _BEGIN_ANY.match(ln):
            k = re.sub(rb" -->$", b"", re.sub(rb"^<!-- BEGIN GENERATED: ", b"", ln, count=1), count=1)
            if from_b(k) in legal:
                inblk = True
            continue
        if _END_ANY.match(ln):
            k = re.sub(rb" -->$", b"", re.sub(rb"^<!-- END GENERATED: ", b"", ln, count=1), count=1)
            if from_b(k) in legal:
                inblk = False
            continue
        if inblk:
            continue
        yield n, ln


def _reject_rc_claims_outside_blocks(self: "Gen") -> bool:
    ckeys = _keys_opt(self, "criteria_keys")
    if not ckeys:
        return True
    root = self.root()
    rc = 0
    allk = self.keys()
    for k in ckeys:
        tg = self.targets(k)
        if tg is None:
            rc = 1
            continue
        for t in read_lines(tg):
            p = root + "/" + t
            if not os.path.isfile(p):
                continue
            legal = self.legal_keys_for(t, allk)
            data = self.read_bytes(p)
            hits = [b"  " + to_b(t) + b":" + str(n).encode() + b" " + ln
                    for n, ln in _awk_block_scan(data, legal) if _FK_RC_CLAIM_PAT.search(ln)]
            if hits:
                self.err("gen_fact_key_blocks: 判準宿主 %s 於生成區塊外陳述期望結束狀態（改寫為判準 ID 指標）→ fail-closed:" % t)
                self.err_b(b"\n".join(hits).rstrip(b"\n") + b"\n")
                rc = 1
    return rc == 0


Gen.reject_rc_claims_outside_blocks = _reject_rc_claims_outside_blocks  # type: ignore[attr-defined]


def _registered_tokens(self: "Gen") -> Optional[List[str]]:
    live_v = _sch(self.data, "mechanism_live_status")
    live = jraw(live_v) if jtruthy(live_v) else ""
    out = []
    for k in _keys_opt(self, "mechanism_keys"):
        ti = self.role_idx_of(k, "token", "mechanism_column_roles")
        si = self.role_idx_of(k, "status", "mechanism_column_roles")
        if ti is None or si is None:
            return None
        for r in jiter(jget(jget(self.data, k), "rows")):
            if jeq(jget(r, si), live):
                out.append(jget(r, ti))
    return out


Gen.registered_tokens = _registered_tokens  # type: ignore[attr-defined]


# WL-03（票 B-25 機制證據登記）：平台機制 token 以 _schema.mechanism_tokens 字面封閉表比對，不做任何可執行檔探測
def _validate_mechanism(self: "Gen") -> bool:
    if not any(_schema_has(self.data, f) for f in _FK_MECHANISM_SCHEMA_FIELDS):
        return True
    rc = 0
    for f in _FK_MECHANISM_SCHEMA_FIELDS:
        if not _schema_has(self.data, f):
            self.err("gen_fact_key_blocks: _schema 已宣告部分機制欄，但缺 %s → fail-closed（機制 schema 為一整組，不得單獨刪）" % f)
            rc = 1
    if rc:
        return False
    for f in ("mechanism_keys", "mechanism_status_enum", "mechanism_scope", "mechanism_tokens"):
        v = _sch(self.data, f)
        if not (isinstance(v, list) and len(v) > 0 and all(jstr_len_ok(x) for x in v)):
            self.err("gen_fact_key_blocks: _schema.%s 非法（須非空字串陣列）→ fail-closed" % f)
            rc = 1
    if rc:
        return False
    live_v = _sch(self.data, "mechanism_live_status")
    live = jraw(live_v) if jtruthy(live_v) else ""
    if not live:
        self.err("gen_fact_key_blocks: _schema.mechanism_live_status 缺席或為空 → fail-closed")
        return False
    if jindex(_sch(self.data, "mechanism_status_enum"), live) is None:
        self.err("gen_fact_key_blocks: mechanism_live_status='%s' 不在 mechanism_status_enum 內 → fail-closed" % live)
        return False
    for sc in read_lines(cmdsub(jraw_lines(_sch(self.data, "mechanism_scope")))):
        if "*" in sc or "?" in sc or "[" in sc:
            self.err("gen_fact_key_blocks: _schema.mechanism_scope 不得含 wildcard：%s → fail-closed" % sc)
            rc = 1
        elif sc.endswith("/"):
            self.err("gen_fact_key_blocks: _schema.mechanism_scope 須為 exact path，不得為目錄前綴：%s → fail-closed（opt-in 必須逐檔顯式）" % sc)
            rc = 1
        elif sc.startswith("/") or ".." in sc:
            self.err("gen_fact_key_blocks: _schema.mechanism_scope 不得為絕對路徑或含 ..：%s → fail-closed" % sc)
            rc = 1
    allk = set(self.keys())
    for k in _keys_opt(self, "mechanism_keys"):
        if k not in allk:
            self.err("gen_fact_key_blocks: mechanism_keys 含未註冊 key '%s' → fail-closed" % k)
            rc = 1
            continue
        bad = "".join(" " + r for r in ("id", "token", "scope", "evidence", "finding", "status")
                      if self.role_idx_of(k, r, "mechanism_column_roles") is None)
        if bad:
            self.err("gen_fact_key_blocks: key %s 缺角色欄（mechanism_column_roles 未宣告或 columns 無該欄）:%s → fail-closed" % (k, bad))
            rc = 1
            continue
        ii = self.role_idx_of(k, "id", "mechanism_column_roles")
        ti = self.role_idx_of(k, "token", "mechanism_column_roles")
        ei = self.role_idx_of(k, "evidence", "mechanism_column_roles")
        si = self.role_idx_of(k, "status", "mechanism_column_roles")
        rows = jiter(jget(jget(self.data, k), "rows"))
        senum = _sch(self.data, "mechanism_status_enum")
        unk = cmdsub(sort_u_lines(jraw_lines([jget(r, si) for r in rows if not any(jeq(jget(r, si), e) for e in senum)])))
        if unk:
            self.err("gen_fact_key_blocks: key %s 之狀態值不在 mechanism_status_enum 內 → fail-closed:" % k)
            self.err_raw(sed_indent(unk))
            rc = 1
        toks = _sch(self.data, "mechanism_tokens")
        off = cmdsub(sort_u_lines(jraw_lines([jget(r, ti) for r in rows if not any(jeq(jget(r, ti), t) for t in toks)])))
        if off:
            self.err("gen_fact_key_blocks: key %s 之平台機制不在 _schema.mechanism_tokens 封閉表內 → fail-closed:" % k)
            self.err_raw(sed_indent(off))
            rc = 1
        dups = [g[0] for g in jgroup_by(rows, lambda r: jget(r, ii)) if len(g) > 1]
        dup = cmdsub(sort_u_lines(jraw_lines([jget(g, ii) for g in dups])))
        if dup:
            self.err("gen_fact_key_blocks: key %s 有重複機制ID → fail-closed:" % k)
            self.err_raw(sed_indent(dup))
            rc = 1
        for ev in read_lines(cmdsub(jraw_lines([jget(r, ei) for r in rows]))):
            pfx = ev.split(":", 1)[0]
            val = ev.split(":", 1)[1] if ":" in ev else ev
            if (" " + pfx + " ") not in (" " + _FK_EVIDENCE_FORMS + " "):
                self.err("gen_fact_key_blocks: key %s 之證據 '%s' 前綴不在 {%s} → fail-closed" % (k, ev, _FK_EVIDENCE_FORMS))
                rc = 1
                continue
            if not (val and val != ev):
                self.err("gen_fact_key_blocks: key %s 之證據 '%s' 缺冒號後之內容 → fail-closed" % (k, ev))
                rc = 1
                continue
            if pfx != "receipt":
                continue
            if val.startswith("/") or ".." in val:
                self.err("gen_fact_key_blocks: key %s 之 receipt 路徑不得為絕對路徑或含 ..：%s → fail-closed" % (k, val))
                rc = 1
                continue
            rp = self.root() + "/" + val
            if os.path.islink(rp):
                self.err("gen_fact_key_blocks: key %s 之 receipt 為 symlink：%s → fail-closed（可指向 repo 外，證據不可稽核）" % (k, val))
                rc = 1
                continue
            if not os.path.isfile(rp):
                self.err("gen_fact_key_blocks: key %s 之 receipt 指向不存在之檔：%s → fail-closed（宣稱實跑但無物可查）" % (k, val))
                rc = 1
    return rc == 0


Gen.validate_mechanism = _validate_mechanism  # type: ignore[attr-defined]


def _reject_unregistered_mechanisms(self: "Gen") -> bool:
    if not any(_schema_has(self.data, f) for f in _FK_MECHANISM_SCHEMA_FIELDS):
        return True
    root = self.root()
    rc = 0
    # awk `split(s, A, " ")`＝預設欄分隔：以空白／tab／換行之連續段切開，頭尾略去
    toks = _awk_split(to_b(jraw_lines(jiter(_sch(self.data, "mechanism_tokens")))))
    reg = self.registered_tokens()
    if reg is None:
        return False
    regset = set(_awk_split(to_b(sort_u_lines(jraw_lines(reg)))))
    try:
        scope = read_lines(cmdsub(jraw_lines(jiter(_sch(self.data, "mechanism_scope")))))
    except JqError:
        scope = []
    for f in scope:
        p = root + "/" + f
        if not os.path.isfile(p):
            self.err("gen_fact_key_blocks: mechanism_scope 所列宿主不存在：%s → fail-closed（缺檔不得靜默略過）" % f)
            rc = 1
            continue
        lines = awk_lines(self.read_bytes(p))
        insub = False
        start_indent = 0
        hits = []
        for n, ln in enumerate(lines, 1):
            is_start = bool(_START_GAIFA.search(ln))
            if is_start:
                rl = len(_LEAD_WS.match(ln).group(0))
                if not insub or rl <= start_indent:
                    start_indent = rl
                insub = True
            if insub and not is_start:
                if not _ALL_WS.match(ln):
                    rl = len(_LEAD_WS.match(ln).group(0))
                    if rl <= start_indent:
                        insub = False
            if insub:
                for t in toks:
                    if t == b"" or not _has_token(ln, t):
                        continue
                    if t in regset:
                        continue
                    hits.append(b"  " + to_b(f) + b":" + str(n).encode() + to_b(" 平台機制 ") + t + to_b(" 未登記為現行"))
        if hits:
            self.err("gen_fact_key_blocks: opt-in 宿主 %s 之改法子樹使用未登記之平台機制（登記到 governance-mechanism 並附 receipt: 或 assumed:）→ fail-closed:" % f)
            self.err_b(b"\n".join(hits) + b"\n")
            rc = 1
    return rc == 0


Gen.reject_unregistered_mechanisms = _reject_unregistered_mechanisms  # type: ignore[attr-defined]


def _has_closed_ticket(self: "Gen") -> bool:
    try:
        sk = _sch(self.data, "status_keys")
        sk = [] if sk is None or sk is False else sk
        vals = []
        for k in jiter(sk):
            rows = jget(jget(self.data, k), "rows")
            rows = [] if rows is None or rows is False else rows
            for r in jiter(rows):
                vals.extend(jiter(r))
        return any(jindex(vals, c) is not None for c in _FK_COMPLETED_STATUSES)
    except JqError:
        return False


def _mount_exists(self: "Gen", mount: str) -> int:
    ev = mount.split(":", 1)[0]
    rest = mount.split(":", 1)[1] if ":" in mount else mount
    mt = rest.split(":", 1)[0]
    cmd = rest.split(":", 1)[1] if ":" in rest else rest
    if not (ev and mt and cmd):
        return 1
    if cmd == rest:
        return 1
    try:
        sp = jraw(_sch(self.data, "enforcement_settings_path"))
    except JqError:
        return 1
    repo = self.repo_logical()
    path = repo + "/" + sp
    if not os.path.isfile(path):
        return 3 if os.path.isdir(os.path.dirname(path)) else 2
    head = cmd.split(" ", 1)[0]
    if not head.endswith(".sh"):
        return 1
    if not os.path.isfile(repo + "/" + head):
        return 1
    mt_pipe = mt.replace(",", "|")
    try:
        settings = _load_json_text(self.read_bytes(path))
        hooks = jget(jget(settings, "hooks"), ev)
        hooks = [] if hooks is None or hooks is False else hooks
        for item in jiter(hooks):
            matcher = jget(item, "matcher")
            m_ok = (matcher is None) if mt_pipe == "-" else jeq(matcher, mt_pipe)
            if not m_ok:
                continue
            inner = jget(item, "hooks")
            inner = [] if inner is None or inner is False else inner
            for h in jiter(inner):
                c = jget(h, "command")
                c = "" if c is None or c is False else c
                if not isinstance(c, str):
                    raise JqError("startswith")
                if c.startswith("bash " + cmd):
                    return 0
        return 1
    except (JqError, OSError, ValueError):
        return 1


def _validate_ticket_universe(self: "Gen") -> bool:
    repo = self.repo_logical()
    bl = repo + "/handoffs/20260801-GOV-AMEND-BACKLOG.md"
    sh = repo + "/scripts/ticket_universe.sh"
    if not (os.path.isfile(bl) and os.path.isfile(sh)):
        return True
    r = subprocess.run(["bash", sh, "--check"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        self.err("gen_fact_key_blocks: 票全集對帳未過（ticket_universe --check rc=%d）→ fail-closed" % r.returncode)
        self.err_b(to_b(sed_indent(from_b(cmdsub_b(r.stdout)))))
        self.err("  這道擋的是「把整列票刪掉就沒有還缺什麼可填」——刪列不等於票不存在。")
        return False
    return True


def _enf_rows_tsv(self: "Gen", k: str, idxs: Sequence[int]) -> str:
    out = []
    for r in jiter(jget(jget(self.data, k), "rows")):
        out.append("\t".join(tsv_escape(jget(r, i)) for i in idxs))
    return cmdsub(jraw_lines(out))


def _read_tsv_fields(line: str, n: int) -> List[str]:
    """`IFS=$'\\t' read -r a b c d`：tab 為空白類 IFS ⇒ 連續 tab 合併、頭尾 tab 去除；末欄收剩餘。"""
    s = line.strip("\t")
    fields: List[str] = []
    while len(fields) < n - 1 and s:
        i = s.find("\t")
        if i < 0:
            fields.append(s)
            s = ""
            break
        fields.append(s[:i])
        s = s[i:].lstrip("\t")
    if len(fields) < n:
        fields.append(s.rstrip("\t") if s else "")
    while len(fields) < n:
        fields.append("")
    return fields


def _validate_enforcement(self: "Gen") -> bool:
    present = any(_schema_has(self.data, f) for f in _FK_ENFORCEMENT_SCHEMA_FIELDS)
    if _has_closed_ticket(self):
        if not present:
            self.err("gen_fact_key_blocks: 票表存在標為『%s』之列，但 _schema 完全沒有產出端覆蓋宣告 → fail-closed" % _FK_CLOSED_STATUS)
            self.err("  規則（使用者 2026-08-13 定死）：治理票要標收案，其檢查必須擋在產出端；刪掉 schema 不等於關閉本規則。")
            return False
    elif not present:
        return True
    rc = 0
    for f in _FK_ENFORCEMENT_SCHEMA_FIELDS:
        if not _schema_has(self.data, f):
            self.err("gen_fact_key_blocks: _schema 已宣告部分產出端覆蓋欄，但缺 %s → fail-closed（本 schema 為一整組）" % f)
            rc = 1
    if rc:
        return False
    cs = cmdsub(jraw(_sch(self.data, "enforcement_closed_status")) + "\n")
    if cs != _FK_CLOSED_STATUS:
        self.err("gen_fact_key_blocks: enforcement_closed_status='%s' 不等於生成器寫死之收案字面 '%s' → fail-closed（改字面即脫鉤，已由委員實構）" % (cs, _FK_CLOSED_STATUS))
        return False
    senum = _sch(self.data, "status_enum")
    try:
        in_enum = jindex(senum, _FK_CLOSED_STATUS) is not None
    except JqError:
        in_enum = False
    if not in_enum:
        self.err("gen_fact_key_blocks: 收案字面 '%s' 不在 status_enum 內 → fail-closed" % _FK_CLOSED_STATUS)
        return False
    cslist_v = sorted(_FK_COMPLETED_STATUSES)
    cslist = jdump(cslist_v)
    try:
        d = _sch(self.data, "enforcement_completed_statuses")
        d = [] if d is None or d is False else d
        if jtype(d) != "array":
            raise JqError("sort")
        declared = jdump(sorted(d, key=jsort_key))
    except JqError:
        self.err("gen_fact_key_blocks: 讀取 enforcement_completed_statuses 失敗 → fail-closed")
        return False
    if declared != cslist:
        self.err("gen_fact_key_blocks: enforcement_completed_statuses=%s 不等於生成器寫死之完成語意集合 %s → fail-closed" % (declared, cslist))
        self.err("  （S2.1：綁定改認集合而非單一字面；改資料即脫鉤之路徑一併封死）")
        return False
    try:
        allin = all(jindex(senum, c) is not None for c in cslist_v)
    except JqError:
        allin = False
    if not allin:
        self.err("gen_fact_key_blocks: 完成語意集合中有值不在 status_enum 內 → fail-closed")
        return False
    side = cmdsub(jraw(_sch(self.data, "enforcement_producer_side")) + "\n")
    try:
        side_ok = jindex(_sch(self.data, "enforcement_side_enum"), side) is not None
    except JqError:
        side_ok = False
    if not side_ok:
        self.err("gen_fact_key_blocks: enforcement_producer_side='%s' 不在 enforcement_side_enum 內 → fail-closed" % side)
        return False
    ekeys = _keys_opt(self, "enforcement_keys")
    if not ekeys:
        self.err("gen_fact_key_blocks: _schema.enforcement_keys 為空 → fail-closed（空清單會使四道檢查全部靜默停用）")
        return False
    allk = self.keys()
    allset = set(allk)
    for k in ekeys:
        if k not in allset:
            self.err("gen_fact_key_blocks: enforcement_keys 含未註冊 key '%s' → fail-closed" % k)
            rc = 1
            continue
        bad = "".join(" " + r for r in ("id", "ticket", "mount", "side", "waiver")
                      if self.role_idx_of(k, r, "enforcement_column_roles") is None)
        if bad:
            self.err("gen_fact_key_blocks: key %s 缺角色欄（enforcement_column_roles）:%s → fail-closed" % (k, bad))
            rc = 1
            continue
        ii = self.role_idx_of(k, "id", "enforcement_column_roles")
        mi = self.role_idx_of(k, "mount", "enforcement_column_roles")
        si = self.role_idx_of(k, "side", "enforcement_column_roles")
        wi = self.role_idx_of(k, "waiver", "enforcement_column_roles")
        rows = jiter(jget(jget(self.data, k), "rows"))
        seenum = _sch(self.data, "enforcement_side_enum")
        unk = cmdsub(sort_u_lines(jraw_lines([jget(r, si) for r in rows if not any(jeq(jget(r, si), e) for e in jiter(seenum))])))
        if unk:
            self.err("gen_fact_key_blocks: key %s 之強制側不在 enforcement_side_enum 內 → fail-closed:" % k)
            self.err_raw(sed_indent(unk))
            rc = 1
        for line in _enf_rows_tsv(self, k, (ii, mi, si, wi)).split("\n"):
            rid, mount, sd, wv = _read_tsv_fields(line, 4)
            if not rid:
                continue
            if sd == side:
                code = _mount_exists(self, mount)
                if code == 0:
                    pass
                elif code == 2:
                    self.err("gen_fact_key_blocks: %s 之掛載點未對證——本樹無 hook 設定之承載目錄（非主控端環境）⇒ 略過對證。真主控端仍會驗。" % rid)
                elif code == 3:
                    self.err("gen_fact_key_blocks: %s 之掛載點無法對證——hook 設定之承載目錄存在，但設定檔缺失 → fail-closed" % rid)
                    self.err("  這不是「非主控端環境」，而是設定檔被刪或改名；此路徑原與略過合流，")
                    self.err("  等於刪掉設定檔即可跳過全部掛載點對證（S1.2 已封）。")
                    rc = 1
                else:
                    self.err("gen_fact_key_blocks: %s 宣告為%s，但掛載點在 settings.json 內不存在：%s → fail-closed（禁自我宣稱）" % (rid, side, mount))
                    rc = 1
            else:
                if not wv or wv in _FK_WAIVER_PLACEHOLDERS:
                    self.err("gen_fact_key_blocks: %s 為豁免但豁免理由為空或佔位符 → fail-closed" % rid)
                    rc = 1
    tk = jraw(jget(_sch(self.data, "enforcement_ticket_roles"), "key"))
    if tk not in allset:
        self.err("gen_fact_key_blocks: enforcement_ticket_roles.key '%s' 未註冊 → fail-closed" % tk)
        return False
    schema = jget(self.data, "_schema")
    roles = jget(schema, "enforcement_column_roles")
    tr = jget(schema, "enforcement_ticket_roles")
    try:
        tcol = jget(roles, "ticket")
        covered = []
        for ek in jiter(jget(schema, "enforcement_keys")):
            e = jget(self.data, ek)
            ti = jindex(jget(e, "columns"), tcol)
            for r in jiter(jget(e, "rows")):
                covered.append(jget(r, ti))
        tcols = jget(jget(self.data, tk), "columns")
        idi = jindex(tcols, jget(tr, "id"))
        sti = jindex(tcols, jget(tr, "status"))
        closed = [jget(r, idi) for r in jiter(jget(jget(self.data, tk), "rows"))
                  if jindex(cslist_v, jget(r, sti)) is not None]
        missing_v = [t for t in closed if jindex(covered, t) is None]
        missing = jjoin(missing_v, "\n")
    except JqError:
        self.err("gen_fact_key_blocks: 收案綁定檢查之 jq 失敗 → fail-closed（不得當成『沒有未覆蓋的票』）")
        return False
    if missing:
        self.err("gen_fact_key_blocks: 下列票已標『%s』但未在 %s-enforcement 登記產出端覆蓋 → fail-closed:"
                 % (cmdsub(jraw(jget(schema, "enforcement_closed_status")) + "\n"), tk.split("-", 1)[0]))
        self.err_raw(sed_indent(missing))
        self.err("  規則（使用者 2026-08-13 定死）：治理票要標收案，其檢查必須擋在產出端；")
        self.err("  擋不了就在 governance-enforcement 具名寫出為什麼（如 G-7 需 commit、pytest 十分鐘級）。")
        return False
    try:
        kcol = jget(roles, "kind")
        kenum = jget(schema, "enforcement_kind_enum")
        scol = jget(roles, "side")
        icol = jget(roles, "id")
        pside = jget(schema, "enforcement_producer_side")
        bad_rows = []
        for ek in jiter(jget(schema, "enforcement_keys")):
            e = jget(self.data, ek)
            ki = jindex(jget(e, "columns"), kcol)
            si2 = jindex(jget(e, "columns"), scol)
            ii2 = jindex(jget(e, "columns"), icol)
            for r in jiter(jget(e, "rows")):
                row = {"id": jget(r, ii2), "kind": jget(r, ki), "side": jget(r, si2)}
                if (row["kind"] is None or jindex(kenum, row["kind"]) is None
                        or (jeq(row["side"], pside) and jeq(row["kind"], "n/a"))
                        or (not jeq(row["side"], pside) and not jeq(row["kind"], "n/a"))):
                    kind_s = jinterp(row["kind"]) if jtruthy(row["kind"]) else "缺"
                    bad_rows.append("%s（強制側=%s 判定型=%s）" % (jinterp(row["id"]), jinterp(row["side"]), kind_s))
        kindbad = "\n".join(bad_rows)
    except JqError:
        self.err("gen_fact_key_blocks: 判定型分類檢查之 jq 失敗 → fail-closed")
        return False
    if kindbad:
        self.err("gen_fact_key_blocks: 下列列之「判定型」不合法或與強制側不一致 → fail-closed:")
        self.err_raw(sed_indent(kindbad))
        self.err("  規則（S3.2）：產出端列須為 內容型 或 一致性型；豁免列須為 n/a。")
        self.err("  判準：只看這一次的編輯內容能否判定對錯？能＝內容型，否＝一致性型。")
        return False
    repo2 = self.repo_logical()
    formbad = ""
    refbad = ""
    try:
        wrows = []
        for ek in jiter(jget(schema, "enforcement_keys")):
            e = jget(self.data, ek)
            ii3 = jindex(jget(e, "columns"), jget(roles, "id"))
            si3 = jindex(jget(e, "columns"), jget(roles, "side"))
            wi3 = jindex(jget(e, "columns"), jget(roles, "waiver"))
            for r in jiter(jget(e, "rows")):
                wrows.append("\t".join(tsv_escape(jget(r, i)) for i in (ii3, si3, wi3)))
        wtext = cmdsub("\n".join(wrows) + "\n")
    except JqError:
        self.err("gen_fact_key_blocks: 豁免理由体例檢查之 jq 失敗 → fail-closed")
        return False
    have_settings = os.path.isfile(repo2 + "/.claude/settings.json")
    for line in wtext.split("\n"):
        wid, wsd, wtx = _read_tsv_fields(line, 3)
        if not wid:
            continue
        if wsd == side:
            if _FK_ENF_MARK_IMPL not in wtx:
                formbad += "%s（產出端列缺「%s」）\n" % (wid, _FK_ENF_MARK_IMPL)
        else:
            for mk in (_FK_ENF_MARK_PRE, _FK_ENF_MARK_POST, _FK_ENF_MARK_PART):
                if mk not in wtx:
                    formbad += "%s（豁免列缺「%s」）\n" % (wid, mk)
        if not have_settings:
            continue
        tail = ""
        if _FK_ENF_MARK_PART in wtx:
            tail = wtx.split(_FK_ENF_MARK_PART, 1)[1]
        if _FK_ENF_MARK_IMPL in wtx:
            tail = tail + " " + wtx.split(_FK_ENF_MARK_IMPL, 1)[1]
        if not tail:
            continue
        need = (_FK_ENF_MARK_IMPL in wtx) or ((_FK_ENF_MARK_PART + "有") in wtx)
        refs_b = cmdsub_b(b"".join(m.group(0) + b"\n" for m in _REF_PAT.finditer(to_b(tail))))
        refs = from_b(refs_b)
        if need and not refs:
            refbad += "%s: 具名段宣稱有實作／部分閘，卻無任何 <檔>:<行> 引用\n" % wid
        for ref in refs.split():
            rf = ref.split(":", 1)[0]
            rl = ref.rsplit(":", 1)[1]
            fp = repo2 + "/" + rf
            if not os.path.isfile(fp):
                refbad += "%s: %s → 檔案不存在\n" % (wid, ref)
                continue
            flines = awk_lines(self.read_bytes(fp))
            n = int(rl)
            rtxt = from_b(flines[n - 1]) if 1 <= n <= len(flines) else ""
            if _is_comment_or_blank(rtxt):
                near = ""
                for j in range(max(n, 1), len(flines) + 1):
                    ln = flines[j - 1]
                    if not re.match(rb"^[ \t\n\v\f\r]*#", ln) and re.search(rb"[^ \t\n]", ln):  # awk NF>0（預設 FS）
                        near = str(j)
                        break
                refbad += "%s: %s → 該行為註解或空行（最近可執行碼＝:%s）\n" % (wid, ref, near or "無")
    if formbad:
        self.err("gen_fact_key_blocks: 下列列之理由不符 S6.1 体例 → fail-closed:")
        self.err_raw("".join("    " + x + "\n" for x in formbad.split("\n")[:-1]))
        self.err("  豁免列須同時寫「%s…」「%s…」「%s…」；" % (_FK_ENF_MARK_PRE, _FK_ENF_MARK_POST, _FK_ENF_MARK_PART))
        self.err("  產出端列須寫「%s<檔:行>」。" % _FK_ENF_MARK_IMPL)
        self.err("  理由：只說「輸入是完整文件」僅證明不能 PreToolUse，不能證明不能 PostToolUse。")
        rc = 1
    if refbad:
        self.err("gen_fact_key_blocks: 下列引用之行號落在註解／空行或檔案不存在 → fail-closed:")
        self.err_raw("".join("    " + x + "\n" for x in refbad.split("\n")[:-1]))
        self.err("  引用要指向**可執行碼**；指到註解等於沒有碼證（S4.4 已打回一次，S6.1 又抓到四處）。")
        rc = 1
    note_v = jget(schema, "enforcement_note")
    note = jraw(note_v) if jtruthy(note_v) else ""
    ghost = ""
    for tok in sorted({m.group(0) for m in _GOV_TOKEN.finditer(to_b(note))}):
        if from_b(tok) not in allset:
            ghost += from_b(tok) + " "
    if ghost:
        self.err("gen_fact_key_blocks: enforcement_note 提及不存在之 fact-key → fail-closed: %s" % ghost)
        self.err("  schema 的散文不得保留作廢來源（連「原文指向 X」這種歷史括註也不行——grep 仍會找到）。")
        self.err("  歷史敘事寫進 docs/GOV_ENFORCEMENT_REGISTRY.md，不要留在 schema。")
        rc = 1
    try:
        bm = jget(schema, "ticket_basis_markers")
        bm = [] if bm is None or bm is False else bm
        if jtype(bm) != "array":
            raise JqError("sort")
        bdecl = jdump(sorted(bm, key=jsort_key))
    except JqError:
        self.err("gen_fact_key_blocks: 讀取 ticket_basis_markers 失敗 → fail-closed")
        return False
    bwant = jdump(sorted(_FK_TICKET_BASIS_MARKERS.split(" ")))
    if bdecl != bwant:
        self.err("gen_fact_key_blocks: ticket_basis_markers=%s 不等於生成器寫死之集合 %s → fail-closed" % (bdecl, bwant))
        self.err("  （刪除／改 null／清空即可讓 S6.2 閘整段停用，三家 r1 各自實構過；故改為集合相等。）")
        return False
    marks = jget(schema, "ticket_basis_markers")
    if len(marks) > 0:
        try:
            t = jget(self.data, jget(tr, "key"))
            ii4 = jindex(jget(t, "columns"), jget(tr, "id"))
            bi = jindex(jget(t, "columns"), jget(tr, "basis"))
            nob = []
            for r in jiter(jget(t, "rows")):
                if bi is None:
                    nob.append(jget(r, ii4))
                    continue
                b = jget(r, bi)
                b = "" if b is None or b is False else b
                good = False
                for m in marks:
                    if isinstance(b, str) and m in b:
                        last = b.split(m)[-1]
                        if len(re.sub(r"^\s+|\s+$", "", last)) >= 6:
                            good = True
                    elif not isinstance(b, str):
                        raise JqError("contains")
                if not good:
                    nob.append(jget(r, ii4))
            nobasis = jjoin(nob, " ")
        except JqError:
            self.err("gen_fact_key_blocks: 票之狀態依據檢查 jq 失敗 → fail-closed")
            return False
        if nobasis:
            self.err("gen_fact_key_blocks: 下列票之「狀態依據」未寫出還缺什麼 → fail-closed:")
            self.err_raw("    %s\n" % nobasis)
            self.err("  規則（S6.2）：每張票須含 %s。" % jjoin(marks, " 或 "))
            self.err("  只寫「r3 三家一致」是**來源**不是**內容**——那會逼人回去翻已作廢的 backlog。")
            rc = 1
    if rc:
        return False
    try:
        tcol = jget(roles, "ticket")
        covered = []
        for ek in jiter(jget(schema, "enforcement_keys")):
            e = jget(self.data, ek)
            ti = jindex(jget(e, "columns"), tcol)
            for r in jiter(jget(e, "rows")):
                covered.append(jget(r, ti))
        tcols = jget(jget(self.data, tk), "columns")
        idi = jindex(tcols, jget(tr, "id"))
        sti = jindex(tcols, jget(tr, "status"))
        pend = [jget(r, idi) for r in jiter(jget(jget(self.data, tk), "rows")) if jeq(jget(r, sti), "部分完成")]
        pending = jjoin([t for t in pend if jindex(covered, t) is None], " ")
    except JqError:
        pending = ""
    if pending:
        self.err("gen_fact_key_blocks: 〔S2.2 預警・不判紅〕下列票為『部分完成』，其產出端覆蓋尚未在登記表列出：")
        self.err("    %s" % pending)
        self.err("    ⇒ 這些票**現在**不受阻擋；但要標完成前必須先在 governance-enforcement 補列，")
        self.err("      否則屆時會被第④道收案綁定擋下。提前告知，避免最後一刻才發現。")
    allow = jget(schema, "enforcement_ticket_allowlist")
    if not (isinstance(allow, list) and all(jstr_len_ok(x) for x in allow)):
        self.err("gen_fact_key_blocks: _schema.enforcement_ticket_allowlist 缺席或非字串陣列 → fail-closed")
        return False
    try:
        tcol = jget(roles, "ticket")
        idi = jindex(jget(jget(self.data, jget(tr, "key")), "columns"), jget(tr, "id"))
        universe = [jget(r, idi) for r in jiter(jget(jget(self.data, jget(tr, "key")), "rows"))]
        vals = []
        for ek in jiter(jget(schema, "enforcement_keys")):
            e = jget(self.data, ek)
            ti = jindex(jget(e, "columns"), tcol)
            for r in jiter(jget(e, "rows")):
                vals.append(jget(r, ti))
        ghost_v = [v for v in junique(vals) if jindex(universe, v) is None and jindex(allow, v) is None]
        ghosts = jjoin(ghost_v, "\n")
    except JqError:
        self.err("gen_fact_key_blocks: 幽靈票檢查之 jq 失敗 → fail-closed（不得當成『沒有幽靈票』）")
        return False
    if ghosts:
        self.err("gen_fact_key_blocks: governance-enforcement 之「對應票」欄含**票全集外之值** → fail-closed:")
        self.err_raw(sed_indent(ghosts))
        self.err("  修：①若為真票，先登記進 %s（票 SoT）②若為非票標的（如判準代號、測試套件），" % tk)
        self.err("  　　須顯式加入 _schema.enforcement_ticket_allowlist 並在測試之集合相等表同步（禁靜默新增）。")
        return False
    return rc == 0


def _is_comment_or_blank(s: str) -> bool:
    """bash `case "$x" in ''|[[:space:]]*'#'*|'#'*)`：空字串、以 `#` 起頭、或首字元為空白類且其後某處含 `#`。"""
    if s == "" or s.startswith("#"):
        return True
    return s[0] in " \t\n\v\f\r" and "#" in s[1:]


def _awk_split(b: bytes) -> List[bytes]:
    """awk `split(s, A, " ")`：以空白／tab／換行之連續段切開、頭尾略去。"""
    return [t for t in re.split(rb"[ \t\n]+", b) if t]


Gen.validate_enforcement = _validate_enforcement  # type: ignore[attr-defined]
Gen.validate_ticket_universe = _validate_ticket_universe  # type: ignore[attr-defined]


def _jnames(x: Any) -> bool:
    return (isinstance(x, list) and len(x) > 0 and all(jstr_len_ok(e) for e in x)
            and len(x) == len(junique(x)))


def _validate_docrot2_status(self: "Gen") -> bool:
    if not (_schema_has(self.data, "docrot2_status_keys") or _schema_has(self.data, "docrot2_status_values")):
        return True
    if not (_jnames(_sch(self.data, "docrot2_status_keys")) and _jnames(_sch(self.data, "docrot2_status_values"))):
        self.err("gen_fact_key_blocks: _schema.docrot2_status_keys／docrot2_status_values 須兩者並存且為非空不重複字串陣列 → fail-closed")
        return False
    rc = 0
    enum = _sch(self.data, "status_enum")
    enum = [] if enum is None or enum is False else enum
    try:
        bad_v = [v for v in _sch(self.data, "docrot2_status_values") if not any(jeq(v, e) for e in jiter(enum))]
    except JqError:
        return False
    bad = cmdsub(jraw_lines(bad_v))
    if bad:
        self.err("gen_fact_key_blocks: _schema.docrot2_status_values 含 status_enum 以外之值：%s→ fail-closed" % bad.replace("\n", " "))
        rc = 1
    done = list(_FK_COMPLETED_STATUSES)
    vals = _sch(self.data, "docrot2_status_values")
    sk = _sch(self.data, "status_keys")
    sk = [] if sk is None or sk is False else sk
    for k in read_lines(cmdsub(jraw_lines(_sch(self.data, "docrot2_status_keys")))):
        if not (k != "_schema" and k in self.data and isinstance(self.data[k], dict)):
            self.err("gen_fact_key_blocks: _schema.docrot2_status_keys 含未註冊 key：%s → fail-closed" % k)
            rc = 1
            continue
        try:
            in_sk = jindex(sk, k) is not None
        except JqError:
            in_sk = True
        if in_sk:
            self.err("gen_fact_key_blocks: key %s 不得同時列於 status_keys 與 docrot2_status_keys → fail-closed" % k)
            rc = 1
            continue
        c = self.data[k].get("columns")
        cols_ok = (isinstance(c, list) and len(c) >= 5 and jeq(c[0], "序") and jeq(c[1], "識別碼")
                   and jindex(c, "狀態") is not None and jindex(c, "權威路徑") is not None
                   and jindex(c, "下一步") is not None)
        if not cols_ok:
            self.err("gen_fact_key_blocks: key %s 之 columns 須首欄『序』、第二欄『識別碼』，並含『狀態』『權威路徑』『下一步』→ fail-closed" % k)
            rc = 1
            continue
        si, pi, ni = jindex(c, "狀態"), jindex(c, "權威路徑"), jindex(c, "下一步")
        try:
            rows = self.data[k].get("rows")
            rows = [] if rows is None or rows is False else rows
            viol = []
            for r in jiter(rows):
                sv = jget(r, si)
                pv = jget(r, pi)
                nv = jget(r, ni)
                pv = "" if pv is None or pv is False else pv
                nv2 = "" if nv is None or nv is False else nv
                if not any(jeq(sv, x) for x in vals):
                    viol.append("%s：狀態「%s」不在 docrot2_status_values" % (jinterp(jget(r, 1)), jinterp(sv)))
                elif jlength(pv) == 0:
                    viol.append("%s：權威路徑為空" % jinterp(jget(r, 1)))
                elif jlength(nv2) == 0:
                    viol.append("%s：下一步為空" % jinterp(jget(r, 1)))
                elif (not any(jeq(sv, x) for x in done)) and any(jeq(nv, x) for x in _FK_D2_NEXT_PLACEHOLDERS):
                    viol.append("%s：未完成列之下一步為佔位符「%s」" % (jinterp(jget(r, 1)), jinterp(nv)))
        except JqError:
            self.err("gen_fact_key_blocks: key %s 之列讀取失敗（jq 非零）→ fail-closed" % k)
            rc = 1
            continue
        v = cmdsub(jraw_lines(viol))
        if v:
            self.err("gen_fact_key_blocks: key %s 之列違規 → fail-closed:" % k)
            self.err_raw(sed_indent(v))
            rc = 1
    try:
        ids = []
        for kk in list(jiter(sk)) + list(jiter(_sch(self.data, "docrot2_status_keys"))):
            obj = jget(self.data, kk)
            if not isinstance(obj, dict):
                continue
            rows = obj.get("rows")
            rows = [] if rows is None or rows is False else rows
            for r in jiter(rows):
                ids.append(jget(r, 1))
        dups = [g[0] for g in jgroup_by(ids, lambda x: x) if len(g) > 1]
    except JqError:
        self.err("gen_fact_key_blocks: 讀取 docrot2 狀態識別碼失敗（jq 非零）→ fail-closed")
        return False
    dup = cmdsub(jraw_lines(dups))
    if dup:
        self.err("gen_fact_key_blocks: status_keys 與 docrot2_status_keys 之識別碼跨 key 重複：%s→ fail-closed" % dup.replace("\n", " "))
        rc = 1
    return rc == 0


def _validate_handoff_projection(self: "Gen") -> bool:
    regp = self.script_dir + "/live_doc_registry.json"
    if not os.path.isfile(regp):
        return True
    try:
        live = _load_json_text(self.read_bytes(regp))
        ok = jhas(live, "handoff_projection") and jhas(jget(live, "handoff") or {}, "section_projection_keys")
    except (JqError, OSError, ValueError):
        ok = False
    if not ok:
        return True
    try:
        p = live["handoff_projection"]
        skm = live["handoff"]["section_projection_keys"]
        r = self.data
        out = []
        for sec, ak in (("## 現況", "current_allow"), ("## 待辦", "todo_allow")):
            k = jget(skm, sec)
            if k is None:
                out.append("%s：section_projection_keys 缺對應 key" % sec)
            elif not jhas(r, k):
                out.append("%s：fact_keys.json 缺交接投影 key" % jinterp(k))
            else:
                s = jget(r, k)
                ks = jinterp(k)
                if not jeq(jget(s, "target"), "HANDOFF.md"):
                    out.append("%s：target 須為 HANDOFF.md" % ks)
                pcols = jget(p, "columns")
                if not (isinstance(pcols, list) and jeq(jget(s, "columns"), ["序"] + pcols)):
                    if not isinstance(pcols, list):
                        raise JqError("array+null")
                    out.append("%s：columns 須為 序＋登記投影欄" % ks)
                rf = jget(s, "rows_filter")
                sk = jget(rf, "source_keys")
                if not jeq(sk, jget(p, "source_keys")):
                    out.append("%s：rows_filter.source_keys 與登記不符" % ks)
                if not jeq(jget(rf, "status_column"), "狀態"):
                    out.append("%s：rows_filter.status_column 須為 狀態" % ks)
                if not jeq(jget(rf, "allow"), jget(p, ak)):
                    out.append("%s：rows_filter.allow 與登記 %s 不符" % (ks, ak))
    except (JqError, KeyError, TypeError):
        self.err("gen_fact_key_blocks: 交接投影對讀失敗（jq 非零）→ fail-closed")
        return False
    text = cmdsub(jraw_lines(out))
    if text:
        self.err("gen_fact_key_blocks: 交接投影與活文件登記不符 → fail-closed:")
        self.err_raw(sed_indent(text))
        return False
    return True


Gen.validate_docrot2_status = _validate_docrot2_status  # type: ignore[attr-defined]
Gen.validate_handoff_projection = _validate_handoff_projection  # type: ignore[attr-defined]


def _emit_all(self: "Gen") -> int:
    if not self.validate_keys():
        return 1
    for check in (self.validate_criteria, self.validate_mechanism, self.validate_enforcement,
                  self.validate_docrot2_status, self.validate_handoff_projection):
        if not check():
            return 1
    rc = 0
    reg = Registry(Path(self.reg_src), self.data, tuple(self.keys()))
    for k in self.keys():
        if not self.validate_rows(k):
            rc = 1
            continue
        if not self.validate_shape(k):
            rc = 1
            continue
        self.out += gen_block(reg, k)
    return rc


def _validate_schema_sets(self: "Gen") -> bool:
    keys = self.keys()
    if not keys:
        return True
    rc = 0
    for f in _FK_SCHEMA_SETS:
        try:
            v = _sch(self.data, f)
            ok = isinstance(v, list) and len(v) > 0 and all(isinstance(x, str) for x in v)
        except JqError:
            ok = False
        if not ok:
            self.err("gen_fact_key_blocks: _schema.%s 缺席／非陣列／為空／含非字串 → fail-closed" % f)
            rc = 1
    if rc:
        return False
    keyset = set(keys)
    for sk in read_lines(cmdsub(jraw_lines(_sch(self.data, "status_keys")))):
        if sk not in keyset:
            self.err("gen_fact_key_blocks: _schema.status_keys 含未註冊 key '%s' → fail-closed" % sk)
            rc = 1
    for sc in read_lines(cmdsub(jraw_lines(_sch(self.data, "status_scope")))):
        if "*" in sc or "?" in sc or "[" in sc:
            self.err("gen_fact_key_blocks: _schema.status_scope 不得含 wildcard：%s → fail-closed" % sc)
            rc = 1
    return rc == 0


Gen.emit_all = _emit_all  # type: ignore[attr-defined]
Gen.validate_schema_sets = _validate_schema_sets  # type: ignore[attr-defined]


def _sed_block_indexed(self: "Gen", path: str, k: str) -> bytes:
    """同 `_sed_block(self.read_bytes(path), k)`，以標記索引直取區段（每 key 不再掃整份宿主）：
    sed 區段自每個 BEGIN 行起、至其後第一個 END 行止（區段內之 BEGIN 行照印），無 END 則至檔尾。"""
    lines = self.lines_of(path)
    marks = self.marks_of(path)
    bs = marks.get(to_b("<!-- BEGIN GENERATED: %s -->" % k), [])
    es = marks.get(to_b("<!-- END GENERATED: %s -->" % k), [])
    out: List[bytes] = []
    p = 0
    bi = ei = 0
    while True:
        while bi < len(bs) and bs[bi] < p:
            bi += 1
        if bi >= len(bs):
            break
        s = bs[bi]
        while ei < len(es) and es[ei] <= s:
            ei += 1
        if ei >= len(es):
            out.extend(lines[s:])
            break
        t = es[ei]
        out.extend(lines[s:t + 1])
        p = t + 1
    return b"".join(x + b"\n" for x in out)


Gen.sed_block_of = _sed_block_indexed  # type: ignore[attr-defined]


def _sed_block(data: bytes, k: str) -> bytes:
    """`sed -n '/^BEGIN$/,/^END$/p'`（命令替換前）。"""
    b = to_b("<!-- BEGIN GENERATED: %s -->" % k)
    e = to_b("<!-- END GENERATED: %s -->" % k)
    out = []
    inr = False
    for ln in awk_lines(data):
        if not inr:
            if ln == b:
                inr = True
                out.append(ln)
        else:
            out.append(ln)
            if ln == e:
                inr = False
    return b"".join(x + b"\n" for x in out)


def _check(self: "Gen") -> int:
    if not self.validate_keys():
        return 1
    if not self.validate_schema_sets():
        return 1
    root = self.root()
    rc = 0
    reg = Registry(Path(self.reg_src), self.data, tuple(self.keys()))
    for k in self.keys():
        if not self.validate_rows(k):
            rc = 1
            continue
        if not self.validate_shape(k):  # --check 之形狀驗證（WL-01；mutation 錨）
            rc = 1
            continue
        tg = self.targets(k)
        if tg is None:
            rc = 1
            continue
        want = gen_block(reg, k).rstrip(b"\n")
        for tgt in read_lines(tg):
            path = root + "/" + tgt
            if not os.path.isfile(path):
                self.err("FACTKEY MISSING TARGET: %s → %s → fail-closed" % (k, path))
                rc = 1
                continue
            if not self.markers_ok(k, path, tgt):
                rc = 1
                continue
            cur = self.sed_block_of(path, k).rstrip(b"\n")
            if cur != want:
                self.err("FACTKEY DRIFT: %s in %s（宿主檔與 %s 不一致；跑 --write 重生成）" % (k, tgt, self.reg_src))
                rc = 1
    for check in (self.reject_unregistered_blocks, self.reject_handwritten_status, self.validate_criteria,
                  self.reject_rc_claims_outside_blocks, self.validate_mechanism, self.validate_enforcement,
                  self.validate_docrot2_status, self.validate_handoff_projection, self.validate_ticket_universe,
                  self.reject_unregistered_mechanisms):
        if not check():
            rc = 1
    return rc


def _write(self: "Gen") -> int:
    if not self.validate_keys():
        return 1
    for check in (self.validate_schema_sets, self.validate_criteria, self.validate_mechanism,
                  self.validate_enforcement, self.validate_docrot2_status, self.validate_handoff_projection,
                  self.reject_unregistered_mechanisms):
        if not check():
            return 1
    root = self.root()
    reg = Registry(Path(self.reg_src), self.data, tuple(self.keys()))
    fast = _write_batched(self, root, reg)
    if fast is not None:
        return fast
    return _write_sequential(self, root, reg)


def _write_batched(self: "Gen", root: str, reg: "Registry") -> Optional[int]:
    """FKPERF Task 4.4：規劃全部替換後每宿主只寫一次（開檔數與 key 數無關）。

    與逐 key 路徑（`_write_sequential`＝oracle 語意）逐位元組等價之前提：每個待寫 (key, 宿主) 之 BEGIN／END 標記
    於原宿主各恰一處且 BEGIN 在前、同宿主各區段互不重疊、生成內容不含任何生成區塊標記行——此時逐 key 替換不改變
    其後 key 之標記計數與位置。任一前提不成立即回 None，由呼叫端改走逐 key 路徑（輸出緩衝還原至進入前）。"""
    out_mark, err_mark = len(self.out), len(self.errbuf)
    rc = 0
    plan: List[Tuple[str, str, str, int, int, List[bytes]]] = []
    for k in self.keys():
        if not self.validate_rows(k):
            rc = 1
            continue
        if not self.validate_shape(k):
            rc = 1
            continue
        tg = self.targets(k)
        if tg is None:
            rc = 1
            continue
        for tgt in read_lines(tg):
            path = root + "/" + tgt
            if not os.path.isfile(path):
                self.err("FACTKEY MISSING TARGET: %s → %s → fail-closed" % (k, path))
                rc = 1
                continue
            try:
                marks = self.marks_of(path)
            except OSError:
                marks = {}
            bl = marks.get(to_b("<!-- BEGIN GENERATED: %s -->" % k), [])
            el = marks.get(to_b("<!-- END GENERATED: %s -->" % k), [])
            block_lines = awk_lines(gen_block(reg, k))
            if len(bl) != 1 or len(el) != 1 or el[0] < bl[0] or any(
                    x.startswith(b"<!-- BEGIN GENERATED: ") or x.startswith(b"<!-- END GENERATED: ")
                    for x in block_lines[1:-1]):
                del self.out[out_mark:]
                del self.errbuf[err_mark:]
                return None
            plan.append((k, tgt, path, bl[0], el[0], block_lines))
    by_path: Dict[str, List[Tuple[int, int, List[bytes]]]] = {}
    order: List[str] = []
    real_of: Dict[Tuple[int, int], str] = {}
    for _k, _t, path, bpos, epos, block_lines in plan:
        # 不同字面 target 指向同一實體宿主（`./host.md`、symlink、大小寫不敏感檔案系統之大小寫別名、硬連結）⇒ 分組會
        # 各自規劃、後寫蓋先寫：以檔案實體身分（裝置號＋inode）比對，同實體不同字面即退回逐 key 路徑
        try:
            st = os.stat(path)
        except OSError:  # 無法取得實體身分 ⇒ 無法證明不互蓋：退回逐 key 路徑（該路徑自行處理存取失敗）
            del self.out[out_mark:]
            del self.errbuf[err_mark:]
            return None
        if real_of.setdefault((st.st_dev, st.st_ino), path) != path:
            del self.out[out_mark:]
            del self.errbuf[err_mark:]
            return None
        if path not in by_path:
            by_path[path] = []
            order.append(path)
        by_path[path].append((bpos, epos, block_lines))
    new_bytes: Dict[str, bytes] = {}
    for path in order:
        regions = sorted(by_path[path], key=lambda r: r[0])
        for a, b2 in zip(regions, regions[1:]):
            if b2[0] <= a[1]:
                del self.out[out_mark:]
                del self.errbuf[err_mark:]
                return None
        lines = self.lines_of(path)
        buf = bytearray()
        cur = 0
        for bpos, epos, block_lines in regions:
            for ln in lines[cur:bpos]:
                buf += ln + b"\n"
            for ln in block_lines:
                buf += ln + b"\n"
            cur = epos + 1
        for ln in lines[cur:]:
            buf += ln + b"\n"
        new_bytes[path] = bytes(buf)
    failed: set = set()
    for path in order:
        try:
            _atomic_write(path, new_bytes[path])
            self.remember(path, new_bytes[path])
        except OSError:
            self.err("gen_fact_key_blocks: 寫入失敗 %s" % path)
            try:
                os.unlink(path + ".factkey.%d" % os.getpid())
            except OSError:
                pass
            failed.add(path)
            rc = 1
    for k, tgt, path, _b, _e, _bl in plan:
        if path not in failed:
            self.out += to_b("FACTKEY WROTE: %s → %s\n" % (k, tgt))
    return rc


def _atomic_write(path: str, data: bytes) -> None:
    """暫存檔寫完全部位元組後 `os.replace`（os.write 可短寫；只呼叫一次會以截斷內容覆蓋宿主；b2 r1 codex P1-01）。"""
    tmp = path + ".factkey.%d" % os.getpid()
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o666)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
    finally:
        os.close(fd)
    os.replace(tmp, path)


def _write_sequential(self: "Gen", root: str, reg: "Registry") -> int:
    """逐 key 寫入（oracle 語意；僅於 `_write_batched` 之等價前提不成立時使用）。"""
    rc = 0
    for k in self.keys():
        if not self.validate_rows(k):
            rc = 1
            continue
        if not self.validate_shape(k):
            rc = 1
            continue
        tg = self.targets(k)
        if tg is None:
            rc = 1
            continue
        for tgt in read_lines(tg):
            path = root + "/" + tgt
            if not os.path.isfile(path):
                self.err("FACTKEY MISSING TARGET: %s → %s → fail-closed" % (k, path))
                rc = 1
                continue
            if not self.markers_ok(k, path, tgt):
                rc = 1
                continue
            block_lines = awk_lines(gen_block(reg, k))
            b = to_b("<!-- BEGIN GENERATED: %s -->" % k)
            e = to_b("<!-- END GENERATED: %s -->" % k)
            try:
                src = self.lines_of(path)
                out = bytearray()
                skip = False
                for ln in src:
                    if ln == b:
                        for bl in block_lines:
                            out += bl + b"\n"
                        skip = True
                        continue
                    if skip and ln == e:
                        skip = False
                        continue
                    if skip:
                        continue
                    out += ln + b"\n"
                _atomic_write(path, bytes(out))
                self.remember(path, bytes(out))
            except OSError:
                self.err("gen_fact_key_blocks: 寫入失敗 %s" % path)
                try:
                    os.unlink(path + ".factkey.%d" % os.getpid())
                except OSError:
                    pass
                rc = 1
                continue
            self.out += to_b("FACTKEY WROTE: %s → %s\n" % (k, tgt))
    return rc


Gen.check = _check  # type: ignore[attr-defined]
Gen.write = _write  # type: ignore[attr-defined]


def _status_hits_in_lines(self: "Gen", path: str) -> int:
    try:
        sk = _sch(self.data, "status_keys")
        sk = [] if sk is None or sk is False else sk
        dk = _sch(self.data, "docrot2_status_keys")
        dk = [] if dk is None or dk is False else dk
        vals = []
        for k in list(jiter(sk)) + list(jiter(dk)):
            rows = jget(jget(self.data, k), "rows")
            rows = [] if rows is None or rows is False else rows
            for r in jiter(rows):
                vals.append(jget(r, 1))
        idtext = jraw_lines(vals)
    except JqError:
        self.err("gen_fact_key_blocks: --status-hits 讀取識別碼失敗 → fail-closed")
        return 2
    if not idtext:
        self.err("gen_fact_key_blocks: --status-hits 識別碼集合為空 → fail-closed")
        return 2
    try:
        etext = jraw_lines(jiter(_sch(self.data, "status_enum")))
    except JqError:
        self.err("gen_fact_key_blocks: --status-hits 讀取 status_enum 失敗 → fail-closed")
        return 2
    ids = [x for x in awk_lines(to_b(idtext)) if x]
    enum = [x for x in awk_lines(to_b(etext)) if x]
    try:
        lines = awk_lines(self.read_bytes(path))
    except OSError:
        self.err("gen_fact_key_blocks: --status-hits 判定執行失敗 → fail-closed")
        return 2
    for ln in lines:
        t = ln.find(b"\t")
        if t < 0:
            continue
        n, s = ln[:t], ln[t + 1:]
        hit = status_hit(s, ids, enum)
        if hit:
            self.out += n + b"\t" + hit[0] + b"\t" + hit[1] + b"\n"
    return 0


Gen.status_hits_in_lines = _status_hits_in_lines  # type: ignore[attr-defined]


# ---------------------------------------------------------------- 模組層介面（可測性契約見 gen_block）

def gen_block(reg: Registry, key: str) -> bytes:
    """產出單一 key 之生成區塊內容（tsv／table render；SPEC Task 1.2）。

    🔴 可測性契約（r5 三家 P1）：`emit_all`／`write_all`／`check_hosts` 之每 key 渲染一律在**呼叫當下**以模組全域名
    `gen_block(reg, key)` 呼叫——不得以模組層別名（`_x = gen_block`）、預設參數或閉包綁定，亦不得改走另一私有渲染函式。
    規模邊界 23／24 之 mutant 以覆寫此全域名注入每 key 迴圈；
    `tests/governance/test_fkperf_scale.py::test_gen_block_injection_reaches_every_key` 以行為驗證此契約。"""
    g = Gen.__new__(Gen)
    g.data = reg.data
    return g.gen_block_bytes(key)


def print_help(entry_path: Path) -> Outcome:
    """印入口檔第 2–20 行（`sed -n '2,20p'`）；於 preflight 之後呼叫（SPEC Task 4.1）。"""
    with open(entry_path, "rb") as fh:
        lines = awk_lines(fh.read())
    return Outcome(0, b"".join(x + b"\n" for x in lines[1:20]), b"")


def _script_dir() -> str:
    """`cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd`：核心所在目錄之邏輯絕對路徑。"""
    d = os.path.dirname(sys.argv[0]) or "."
    if os.path.isabs(d):
        return os.path.normpath(d)
    pwd = os.environ.get("PWD")
    base = pwd if pwd and os.path.isdir(pwd) and os.path.samefile(pwd, ".") else os.getcwd()
    return os.path.normpath(os.path.join(base, d))


def run(argv: Sequence[str], script_dir: str) -> Outcome:
    g = Gen(script_dir)
    rc = 0
    try:
        g.preflight()
        if argv and argv[0] == "--status-hits":
            if not (len(argv) == 2 and os.path.isfile(argv[1])):
                g.err("gen_fact_key_blocks: --status-hits 需恰一個存在之行檔 → fail-closed")
                raise Exit(2)
            g.materialize()
            if not g.validate_keys() or not g.validate_schema_sets():
                raise Exit(2)
            dk = _sch(g.data, "docrot2_status_keys")
            if not (isinstance(dk, list) and len(dk) > 0):
                g.err("gen_fact_key_blocks: --status-hits 需 _schema.docrot2_status_keys 為非空陣列 → fail-closed")
                raise Exit(2)
            if not g.validate_docrot2_status():
                raise Exit(2)
            raise Exit(g.status_hits_in_lines(argv[1]))
        if len(argv) > 1:
            g.err("gen_fact_key_blocks: 只接受 0 或 1 個參數（收到 %d）→ fail-closed" % len(argv))
            raise Exit(2)
        mode = argv[0] if argv else ""
        if mode in ("", "--check", "--write"):
            g.materialize()
        if mode == "":
            rc = g.emit_all()
        elif mode == "--check":
            rc = g.check()
        elif mode == "--write":
            rc = g.write()
        elif mode in ("-h", "--help"):
            h = print_help(Path(script_dir) / "gen_fact_key_blocks.sh")
            g.out += h.stdout
            rc = 0
        else:
            g.err("gen_fact_key_blocks: 未知參數 '%s'（可用：--check｜--write｜--help）→ fail-closed" % mode)
            rc = 2
    except Exit as ex:
        rc = ex.rc
    return Outcome(rc, bytes(g.out), bytes(g.errbuf))


def main(argv: Sequence[str]) -> int:
    """六種呼叫形態之分派（emit／--check／--write／--status-hits／--help／錯誤參數；SPEC C-1）。"""
    res = run(argv, _script_dir())
    sys.stdout.buffer.write(res.stdout)
    sys.stdout.buffer.flush()
    sys.stderr.buffer.write(res.stderr)
    sys.stderr.buffer.flush()
    return res.rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
