#!/usr/bin/env python3
"""_live_doc_registry.py — DOCROT2 Task 1.1：活文件類別登記之共用判定（唯一實作）。

呼叫端（薄包裝，不得另寫判定）：
  scripts/live_doc_registry_check.sh   → check --path <p> | --all | --staged
  scripts/live_doc_registry_update.sh  → update --add <path> [--class <類別>]

登記檔＝<repo>/scripts/live_doc_registry.json；類別集合、範圍根、路徑對照、規則旗標皆只定義於該檔。

判定（封閉、可證偽）：
  範圍      ＝ `_schema.scope_roots` 下全部層級之 `.md` ＋ repo 根目錄之 `.md`；範圍外一律不登記亦不擋。
  探索      ＝ discover_live_docs：`git ls-files --cached --others --exclude-standard -z`，以 UTF-8 位元組排序（同 LC_ALL=C）。
  分類      ＝ exact 優先；否則取最長之 prefix；皆不命中＝未登記。
  登記檔錯誤＝類別不屬 class_enum、prefix 不以 / 結尾、exact 以 / 結尾、含 wildcard 字元、
              同一 exact 或 prefix 重複宣告、exact 落在 HIST 類 prefix 之下、登記路徑在範圍外、class_flags 鍵集≠class_enum。
  --all     ＝ 登記檔錯誤 ∪ 探索所得路徑未登記／非 regular file ∪ exact 登記之路徑不在探索結果
              ∪ fact_keys.json `_schema.status_scope` 項未被登記涵蓋。
  --staged  ＝ 暫存之新增或重新命名 `.md`（範圍內）未登記。
  --migration（Task 4.1）＝ `new_line_status_check`＝true 類之登記活文件全檔（豁免區同寫入前守衛）經
              `gen_fact_key_blocks.sh --status-hits` 一次判定：命中檔 ∉ `scripts/docrot2_migration_residuals.json`
              ⇒ 違規；清單列之檔已無命中或不在判定範圍 ⇒ 違規（清單過期）；清單檔不合規 ⇒ rc=2。
              加 `--index`（pre-commit 用）＝清冊、內容、登記檔、fact_keys、殘留清單與判定碼皆取暫存快照，不含未追蹤檔。
rc：0＝合規或範圍外；1＝違規；2＝用法或環境錯誤。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Tuple

REGISTRY_REL = os.path.join("scripts", "live_doc_registry.json")
FACT_KEYS_REL = os.path.join("scripts", "fact_keys.json")
WILDCARD_CHARS = ("*", "?", "[", "]")

# 〔CODEX-R1-P1-03（D2B）〕類別旗標語意矩陣寫死於此（非由登記檔自證）：登記檔之 class_flags 須逐類逐旗標相等，
#   否則把某類旗標改成 false 即可讓寫入前守衛對整類活文件放行。定義出處＝DOCROT2 TODO Task 1.1 要點 3。
_ON = {"new_line_status_check": True, "archaeology_check": True, "concept_removal_xref": False, "handoff_grammar": False}
_OFF = {"new_line_status_check": False, "archaeology_check": False, "concept_removal_xref": False, "handoff_grammar": False}
CLASS_FLAG_MATRIX = {
    "LIVE-HANDOFF": {**_ON, "handoff_grammar": True},
    "LIVE-CONTRACT": dict(_ON),
    "LIVE-SPEC": {**_ON, "concept_removal_xref": True},
    "LIVE-PLAIN": dict(_ON),
    "LIVE-GUIDE": dict(_ON),
    "LOG": dict(_OFF),
    "HIST": dict(_OFF),
    "OTHER-DORMANT": dict(_ON),
}


def _die(msg: str, rc: int = 2) -> "NoReturn":  # type: ignore[name-defined]
    print(f"live_doc_registry: {msg}", file=sys.stderr)
    sys.exit(rc)


def repo_root() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        _die("非 git 工作樹 ⇒ fail-closed")
    return out.decode("utf-8").strip()


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise ValueError(f"讀不到 {path}：{exc}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} 非合法 JSON：{exc}")
    if not isinstance(data, dict):
        raise ValueError(f"{path} 頂層須為物件")
    return data


def _byte_key(s: str) -> bytes:
    return s.encode("utf-8")


def in_scope(path: str, scope_roots: Sequence[str]) -> bool:
    # 〔CODEX-R2-P1-01（D2B）〕副檔名不分大小寫：`.MD` 不得逃出登記範圍
    if not path.casefold().endswith(".md"):
        return False
    if "/" not in path:
        return True
    return any(path.startswith(r) for r in scope_roots)


def discover_live_docs(root: str, scope_roots: Sequence[str]) -> List[str]:
    """範圍內全部 `.md`（含未追蹤、排除 ignore），UTF-8 位元組排序。"""
    try:
        out = subprocess.run(
            ["git", "-C", root, "-c", "core.quotePath=false", "ls-files",
             "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        _die("git ls-files 失敗 ⇒ fail-closed")
    paths = {p for p in out.decode("utf-8").split("\0") if p}
    return sorted((p for p in paths if in_scope(p, scope_roots)), key=_byte_key)


def _pairs(reg: dict, key: str, errs: List[str]) -> List[Tuple[str, str]]:
    raw = reg.get(key)
    if not isinstance(raw, list):
        errs.append(f"`{key}` 須為 [路徑, 類別] 陣列")
        return []
    pairs: List[Tuple[str, str]] = []
    for item in raw:
        if (not isinstance(item, list) or len(item) != 2
                or not all(isinstance(x, str) and x for x in item)):
            errs.append(f"`{key}` 項目須為兩個非空字串：{item!r}")
            continue
        pairs.append((item[0], item[1]))
    return pairs


def validate_registry(reg: dict) -> Tuple[List[str], dict]:
    """回傳 (錯誤列表, 正規化結構)。"""
    errs: List[str] = []
    schema = reg.get("_schema")
    if not isinstance(schema, dict):
        return (["缺 `_schema` 物件"], {})
    class_enum = schema.get("class_enum")
    scope_roots = schema.get("scope_roots")
    hist_classes = schema.get("hist_classes")
    if not (isinstance(class_enum, list) and class_enum and all(isinstance(c, str) and c for c in class_enum)):
        errs.append("`_schema.class_enum` 須為非空字串陣列")
        class_enum = []
    if not (isinstance(scope_roots, list) and scope_roots
            and all(isinstance(r, str) and r.endswith("/") for r in scope_roots)):
        errs.append("`_schema.scope_roots` 須為以 / 結尾之字串陣列")
        scope_roots = []
    if not (isinstance(hist_classes, list) and all(c in class_enum for c in hist_classes)):
        errs.append("`_schema.hist_classes` 須為 class_enum 子集")
        hist_classes = []
    flags = reg.get("class_flags")
    if not isinstance(flags, dict) or set(flags) != set(class_enum):
        errs.append("`class_flags` 之鍵集須恰等於 class_enum")
    elif flags != CLASS_FLAG_MATRIX:
        bad = sorted(c for c in CLASS_FLAG_MATRIX if flags.get(c) != CLASS_FLAG_MATRIX[c])
        errs.append(f"`class_flags` 須逐類逐旗標等於寫死之語意矩陣（不符之類別：{'、'.join(bad) or '類別集合不同'}）")
    if class_enum and set(class_enum) != set(CLASS_FLAG_MATRIX):
        errs.append("`_schema.class_enum` 須恰等於語意矩陣之類別集合")

    exact = _pairs(reg, "exact", errs)
    prefix = _pairs(reg, "prefix", errs)

    seen_exact: dict = {}
    for path, cls in exact:
        if cls not in class_enum:
            errs.append(f"exact {path}：類別 {cls} 不屬 class_enum")
        if path.endswith("/"):
            errs.append(f"exact {path}：不得以 / 結尾")
        if any(ch in path for ch in WILDCARD_CHARS):
            errs.append(f"exact {path}：禁 wildcard")
        if scope_roots and not in_scope(path, scope_roots):
            errs.append(f"exact {path}：在範圍外（只准 scope_roots 下或 repo 根目錄之 .md）")
        seen_exact.setdefault(path, []).append(cls)
    for path, classes in seen_exact.items():
        if len(classes) > 1:
            errs.append(f"exact {path}：重複登記 {len(classes)} 次（{'、'.join(classes)}）")

    seen_prefix: dict = {}
    for path, cls in prefix:
        if cls not in class_enum:
            errs.append(f"prefix {path}：類別 {cls} 不屬 class_enum")
        if not path.endswith("/"):
            errs.append(f"prefix {path}：須以 / 結尾")
        if any(ch in path for ch in WILDCARD_CHARS):
            errs.append(f"prefix {path}：禁 wildcard")
        if scope_roots and not any(path.startswith(r) for r in scope_roots):
            errs.append(f"prefix {path}：在範圍外")
        seen_prefix.setdefault(path, []).append(cls)
    for path, classes in seen_prefix.items():
        if len(classes) > 1:
            errs.append(f"prefix {path}：重複登記 {len(classes)} 次（{'、'.join(classes)}）")

    hist_prefixes = [p for p, c in prefix if c in hist_classes]
    for path, cls in exact:
        for hp in hist_prefixes:
            if path.startswith(hp):
                errs.append(f"exact {path}（{cls}）落在歷史類 prefix {hp} 之下")

    norm = {
        "class_enum": class_enum,
        "scope_roots": scope_roots,
        "exact": dict((p, c) for p, c in exact),
        "prefix": prefix,
        "schema": schema,
    }
    return errs, norm


def classify(path: str, norm: dict) -> Optional[str]:
    if path in norm["exact"]:
        return norm["exact"][path]
    best: Optional[Tuple[str, str]] = None
    for p, c in norm["prefix"]:
        if path.startswith(p) and (best is None or len(p) > len(best[0])):
            best = (p, c)
    return best[1] if best else None


def _covered(entry: str, norm: dict) -> bool:
    if entry.endswith("/"):
        return any(p == entry or entry.startswith(p) for p, _ in norm["prefix"])
    return classify(entry, norm) is not None


def _load(root: str) -> Tuple[List[str], dict]:
    try:
        reg = load_json(os.path.join(root, REGISTRY_REL))
    except ValueError as exc:
        return [str(exc)], {}
    return validate_registry(reg)


def check_all(root: str) -> List[str]:
    errs, norm = _load(root)
    if not norm:
        return errs
    discovered = discover_live_docs(root, norm["scope_roots"])
    discovered_set = set(discovered)
    for path in discovered:
        full = os.path.join(root, path)
        if os.path.islink(full):
            errs.append(f"{path}：symlink ⇒ fail-closed")
            continue
        if not os.path.isfile(full):
            errs.append(f"{path}：非 regular file（已刪未暫存或非檔案）⇒ fail-closed")
            continue
        if classify(path, norm) is None:
            errs.append(f"{path}：未登記（以 live_doc_registry_update.sh --add 登記）")
    for path in norm["exact"]:
        if path not in discovered_set:
            errs.append(f"exact {path}：登記之路徑不存在於探索結果（檔案已刪或被 ignore）")
    try:
        fk = load_json(os.path.join(root, FACT_KEYS_REL))
        status_scope = (fk.get("_schema") or {}).get("status_scope")
    except ValueError as exc:
        errs.append(str(exc))
        status_scope = None
    if not isinstance(status_scope, list):
        errs.append("fact_keys.json `_schema.status_scope` 缺失或非陣列")
    else:
        for entry in status_scope:
            if not isinstance(entry, str) or not _covered(entry, norm):
                errs.append(f"fact_keys.json status_scope 項 {entry!r} 未被活文件登記涵蓋")
    return errs


def check_path(root: str, path: str) -> Tuple[List[str], str]:
    errs, norm = _load(root)
    if not norm:
        return errs, ""
    if not in_scope(path, norm["scope_roots"]):
        return errs, f"{path}：範圍外，不登記亦不擋"
    # 〔CODEX-R1-P1-02〕與 check_all 同一檔案系統邊界：已存在之 symlink／非 regular file ⇒ fail-closed。
    # 尚不存在之路徑（登記先於建檔）不在此判；建檔後由 --all／--staged 判。
    full = os.path.join(root, path)
    if os.path.islink(full):
        errs.append(f"{path}：symlink ⇒ fail-closed")
        return errs, ""
    if os.path.lexists(full) and not os.path.isfile(full):
        errs.append(f"{path}：非 regular file ⇒ fail-closed")
        return errs, ""
    cls = classify(path, norm)
    if cls is None:
        errs.append(f"{path}：未登記（以 live_doc_registry_update.sh --add 登記）")
        return errs, ""
    return errs, f"{path}：{cls}"


UNREGISTERED_CLASS = "UNREGISTERED"


def emit_block_event(root: str, origin_script: str, path: str, cls: Optional[str], rule_ids: Sequence[str]) -> bool:
    """DOCROT2 Task 3.2：擋下事件之唯一寫入實作（兩支守衛共用）。每個相異 rule_id 寫一筆 docrot2_gate_block。

    寫入點固定為被守衛 repo（cwd 之 git 根）之 scripts/audit_append.sh；rule_id 值集由 audit_events.json 之
    enums.rule_id 於寫入時驗證。寫入失敗只回 False 並印 stderr，**不改變呼叫端之擋下結果**。
    """
    append = os.path.join(root, "scripts", "audit_append.sh")
    if not os.path.isfile(append):
        print(f"{origin_script}: ⚠ 擋下事件未寫入（缺 scripts/audit_append.sh）；擋下結果不變", file=sys.stderr)
        return False
    ok = True
    for rule in sorted(set(rule_ids)):
        cmd = ["bash", append, "--event", "docrot2_gate_block",
               "--field", f"rule_id={rule}", "--field", f"path={path}",
               "--field", f"class={cls or UNREGISTERED_CLASS}",
               "--field", f"actor={origin_script}", "--field", f"origin_script={origin_script}"]
        try:
            r = subprocess.run(cmd, cwd=root, capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"{origin_script}: ⚠ 擋下事件寫入失敗（{exc}）；擋下結果不變", file=sys.stderr)
            ok = False
            continue
        if r.returncode != 0:
            print(f"{origin_script}: ⚠ 擋下事件寫入失敗 rc={r.returncode}："
                  + r.stderr.decode("utf-8", "replace").strip() + "；擋下結果不變", file=sys.stderr)
            ok = False
    return ok


def _staged_new_paths(root: str) -> List[str]:
    try:
        out = subprocess.run(
            ["git", "-C", root, "-c", "core.quotePath=false", "diff", "--cached",
             "--name-status", "-z", "--diff-filter=AR"],
            capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        _die("git diff --cached 失敗 ⇒ fail-closed")
    tokens = out.decode("utf-8").split("\0")
    paths: List[str] = []
    i = 0
    while i < len(tokens) and tokens[i]:
        status = tokens[i]
        if status.startswith("R"):
            if i + 2 >= len(tokens):
                break
            paths.append(tokens[i + 2])
            i += 3
        else:
            if i + 1 >= len(tokens):
                break
            paths.append(tokens[i + 1])
            i += 2
    return paths


def _staged_mode(root: str, path: str) -> str:
    """暫存區中該路徑之 git 模式（100644／100755＝regular，120000＝symlink）；取不到回空字串。"""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "-s", "-z", "--", f":(literal){path}"],
            capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        _die("git ls-files -s 失敗 ⇒ fail-closed")
    entry = out.decode("utf-8").split("\0")[0]
    return entry.split(" ", 1)[0] if entry else ""


def check_staged(root: str) -> List[str]:
    errs, norm = _load(root)
    if errs or not norm:
        # DOCROT2 Task 3.2：登記檔不合規而擋下 commit ⇒ 擋下事件（無單一路徑，記登記檔本身）
        emit_block_event(root, "live_doc_registry_check.sh", REGISTRY_REL, UNREGISTERED_CLASS, ["registry-error"])
    if not norm:
        return errs
    for path in _staged_new_paths(root):
        if not in_scope(path, norm["scope_roots"]):
            continue
        mode = _staged_mode(root, path)
        if mode not in ("100644", "100755"):
            errs.append(f"{path}（暫存新增）：暫存模式 {mode or '取不到'} 非 regular file（symlink＝120000）⇒ fail-closed")
            emit_block_event(root, "live_doc_registry_check.sh", path, UNREGISTERED_CLASS, ["registry-error"])
            continue
        if classify(path, norm) is None:
            errs.append(f"{path}（暫存新增）：未登記（以 live_doc_registry_update.sh --add 登記）")
            emit_block_event(root, "live_doc_registry_check.sh", path, UNREGISTERED_CLASS, ["unregistered-md"])
    return errs


# ────────────────────────────────────────────────────────────── DOCROT2 Task 4.1：全專案遷移判定

MIGRATION_RESIDUALS_REL = os.path.join("scripts", "docrot2_migration_residuals.json")
# 殘留理由類別三值（使用者 2026-08-17 定：殘留只准這三種理由）寫死於此，不由清單檔自證
RESIDUAL_REASON_CLASSES = ("blocked-by", "user-ruling", "needs-research")
RESIDUAL_FIELDS = ("id", "path", "reason_class", "why", "owner", "trigger")


class MigrationConfigError(Exception):
    """殘留清單或判定環境不合規（呼叫端 rc=2，fail-closed）。"""


def load_migration_residuals(root: str, text: Optional[str] = None) -> List[dict]:
    try:
        if text is None:
            data = load_json(os.path.join(root, MIGRATION_RESIDUALS_REL))
        else:
            data = _json_object(text, MIGRATION_RESIDUALS_REL)
    except ValueError as exc:
        raise MigrationConfigError(str(exc))
    extra = sorted(set(data) - {"_schema", "residuals"})
    if extra:
        raise MigrationConfigError(f"{MIGRATION_RESIDUALS_REL} 頂層含未定義鍵：{extra}")
    rows = data.get("residuals")
    if not isinstance(rows, list):
        raise MigrationConfigError(f"{MIGRATION_RESIDUALS_REL} 缺 residuals 陣列")
    errs: List[str] = []
    seen_path: set = set()
    seen_id: set = set()
    for n, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != set(RESIDUAL_FIELDS):
            errs.append(f"第 {n} 列：鍵集須恰為 {list(RESIDUAL_FIELDS)}")
            continue
        blank = [f for f in RESIDUAL_FIELDS if not isinstance(row[f], str) or not row[f].strip()]
        if blank:
            errs.append(f"第 {n} 列：{blank} 須為非空字串")
            continue
        if row["reason_class"] not in RESIDUAL_REASON_CLASSES:
            errs.append(f"第 {n} 列：reason_class「{row['reason_class']}」不屬 {list(RESIDUAL_REASON_CLASSES)}")
        if row["path"] in seen_path:
            errs.append(f"第 {n} 列：path {row['path']} 重複")
        if row["id"] in seen_id:
            errs.append(f"第 {n} 列：id {row['id']} 重複")
        seen_path.add(row["path"])
        seen_id.add(row["id"])
    if errs:
        raise MigrationConfigError(f"{MIGRATION_RESIDUALS_REL} 不合規：" + "；".join(errs))
    return rows


def _json_object(text: str, rel: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{rel} 非合法 JSON：{exc}")
    if not isinstance(data, dict):
        raise ValueError(f"{rel} 頂層須為物件")
    return data


def _index_text(root: str, rel: str) -> str:
    """暫存區版本之文字檔；缺失或非 UTF-8 ⇒ MigrationConfigError（不退回工作樹）。"""
    spec = ":" + rel.replace(os.sep, "/")
    r = subprocess.run(["git", "-C", root, "cat-file", "blob", spec], capture_output=True)
    if r.returncode != 0:
        raise MigrationConfigError(f"暫存區缺 {rel}")
    try:
        return r.stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise MigrationConfigError(f"暫存區之 {rel} 非 UTF-8")


def _index_entries(root: str) -> List[Tuple[str, str, str]]:
    """暫存區清冊（mode, blob sha, path）；未解決衝突 ⇒ MigrationConfigError。"""
    try:
        out = subprocess.run(["git", "-C", root, "-c", "core.quotePath=false", "ls-files", "-s", "-z"],
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        raise MigrationConfigError("git ls-files -s 失敗")
    entries: List[Tuple[str, str, str]] = []
    for rec in out.split(b"\0"):
        if not rec:
            continue
        meta, _tab, raw = rec.partition(b"\t")
        mode, sha, stage = meta.decode("ascii").split(" ")
        path = raw.decode("utf-8")
        if stage != "0":
            raise MigrationConfigError(f"暫存區有未解決衝突：{path}")
        entries.append((mode, sha, path))
    return entries


def _cat_blobs(root: str, shas: Sequence[str]) -> Dict[str, bytes]:
    uniq = sorted(set(shas))
    if not uniq:
        return {}
    r = subprocess.run(["git", "-C", root, "cat-file", "--batch"], input=("\n".join(uniq) + "\n").encode("ascii"),
                       capture_output=True)
    if r.returncode != 0:
        raise MigrationConfigError("git cat-file --batch 失敗")
    out, pos, blobs = r.stdout, 0, {}
    for _ in uniq:
        nl = out.index(b"\n", pos)
        head = out[pos:nl].decode("ascii").split(" ")
        if len(head) != 3 or head[1] != "blob":
            raise MigrationConfigError(f"git cat-file --batch 回傳非 blob：{' '.join(head)}")
        size = int(head[2])
        blobs[head[0]] = out[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
    return blobs


def _migration_judged(ctx, rel: str, errs: List[str]) -> bool:
    """已登記且屬 new_line_status_check 類 ⇒ 須判定；未登記 ⇒ 記違規。"""
    cls, flags = ctx.cls_flags(rel)
    if cls is None:
        errs.append(f"{rel}：未登記 ⇒ 無法判定（以 live_doc_registry_update.sh --add 登記）")
        return False
    return bool(flags.get("new_line_status_check"))


def migration_hits(root: str, snapshot: str = "worktree") -> Tuple[Dict[str, List[Tuple[str, str, str]]], set, List[str]]:
    """登記之 new_line_status_check＝true 類活文件全檔（去豁免區，豁免與寫入前守衛同一 regions）經共用判定入口
    一次判定。回（{路徑: [(行號, 識別碼, 狀態)]}、已判定路徑集合、無法判定之違規）。
    snapshot＝"worktree"：清冊同 --all（含未追蹤）、內容與登記讀工作樹；
    snapshot＝"index"：清冊、內容、登記檔、fact_keys 與判定碼皆取暫存區（將被 commit 之快照；D2D review-r1）。"""
    import _live_doc_write_guard as ldw  # 延遲載入：守衛模組於載入時 import 本模組

    try:
        if snapshot == "index":
            ctx = ldw.Context(root, _index_text(root, FACT_KEYS_REL), registry_text=_index_text(root, REGISTRY_REL),
                              snapshot_prefix=":")
        else:
            ctx = ldw.Context(root)
    except (ldw.GuardError, ValueError) as exc:
        raise MigrationConfigError(str(exc))
    try:
        return _migration_hits(root, ctx, snapshot)
    finally:
        ctx.close()


def _migration_hits(root: str, ctx, snapshot: str) -> Tuple[Dict[str, List[Tuple[str, str, str]]], set, List[str]]:
    import _live_doc_write_guard as ldw

    errs: List[str] = []
    judged: List[Tuple[str, str]] = []
    if snapshot == "index":
        entries = sorted((e for e in _index_entries(root) if in_scope(e[2], ctx.norm["scope_roots"])),
                         key=lambda e: _byte_key(e[2]))
        todo: List[Tuple[str, str]] = []
        for mode, sha, rel in entries:
            if not _migration_judged(ctx, rel, errs):
                continue
            if mode not in ("100644", "100755"):
                errs.append(f"{rel}：暫存模式 {mode} 非 regular file ⇒ 無法判定")
                continue
            todo.append((rel, sha))
        blobs = _cat_blobs(root, [sha for _rel, sha in todo])
        for rel, sha in todo:
            try:
                judged.append((rel, blobs[sha].decode("utf-8")))
            except UnicodeDecodeError:
                errs.append(f"{rel}：暫存版非 UTF-8 ⇒ 無法判定")
    else:
        for rel in discover_live_docs(root, ctx.norm["scope_roots"]):
            if not _migration_judged(ctx, rel, errs):
                continue
            full = os.path.join(root, rel)
            if os.path.islink(full) or not os.path.isfile(full):
                errs.append(f"{rel}：非 regular file ⇒ 無法判定")
                continue
            try:
                with open(full, encoding="utf-8", newline="") as fh:
                    judged.append((rel, fh.read()))
            except (OSError, UnicodeDecodeError) as exc:
                errs.append(f"{rel}：讀取失敗（{exc.__class__.__name__}）⇒ 無法判定")
    scanned: set = set()
    by_label: Dict[str, str] = {}
    items: List[Tuple[str, str]] = []
    for fi, (rel, text) in enumerate(judged):
        scanned.add(rel)
        lines = ldw.split_lines(text)
        reg = ldw.regions(lines, ctx.legal_keys(rel))
        for i, ln in enumerate(lines):
            if reg["gen"][i] or reg["hist"][i] or reg["fence"][i] or reg["marker"][i]:
                continue
            label = f"{fi}:{i + 1}"
            by_label[label] = rel
            items.append((label, ln))
    try:
        rows = ldw.status_hit_rows(ctx, items)
    except ldw.GuardError as exc:
        raise MigrationConfigError(str(exc))
    hits: Dict[str, List[Tuple[str, str, str]]] = {}
    for label, ident, st in rows:
        rel = by_label.get(label)
        if rel is None:
            raise MigrationConfigError(f"判定入口回傳未知標籤 {label!r}")
        hits.setdefault(rel, []).append((label.split(":", 1)[1], ident, st))
    return hits, scanned, errs


def check_migration(root: str, snapshot: str = "worktree") -> Tuple[List[str], str]:
    text = _index_text(root, MIGRATION_RESIDUALS_REL) if snapshot == "index" else None
    residuals = load_migration_residuals(root, text)
    hits, scanned, errs = migration_hits(root, snapshot)
    listed = {r["path"] for r in residuals}
    for rel in sorted(hits, key=_byte_key):
        if rel in listed:
            continue
        sample = "、".join(f"L{n}「{ident}」＋「{st}」" for n, ident, st in hits[rel][:3])
        more = f" 等 {len(hits[rel])} 行" if len(hits[rel]) > 3 else ""
        errs.append(f"{rel}：全檔命中（{sample}{more}）且不在殘留清單 ⇒ 狀態改生成區塊，"
                    f"或具名列入 {MIGRATION_RESIDUALS_REL}")
    for r in residuals:
        if r["path"] in hits:
            continue
        why = "已無命中" if r["path"] in scanned else "不在判定範圍（不存在、未登記或屬不適用類別）"
        errs.append(f"殘留清單列 {r['id']}（{r['path']}）：{why} ⇒ 清單過期，刪除該列")
    where = "暫存快照" if snapshot == "index" else "工作樹"
    return errs, f"遷移判定合規（{where}）：命中檔 {len(hits)} 個皆列於殘留清單，殘留 {len(residuals)} 列皆仍命中"


def _default_class(path: str, schema: dict) -> str:
    pred = schema.get("live_spec_predicate") or {}
    parent = pred.get("parent", "docs/")
    tokens = pred.get("name_tokens") or []
    rest = path[len(parent):] if path.startswith(parent) else None
    if rest is not None and "/" not in rest and any(t in rest for t in tokens):
        return pred.get("class", "LIVE-SPEC")
    return schema.get("default_class", "OTHER-DORMANT")


def update_add(root: str, path: str, cls: Optional[str]) -> Tuple[int, str]:
    reg_path = os.path.join(root, REGISTRY_REL)
    try:
        reg = load_json(reg_path)
    except ValueError as exc:
        return 1, str(exc)
    errs, norm = validate_registry(reg)
    if errs:
        return 1, "登記檔本身不合規：" + "；".join(errs)
    if not in_scope(path, norm["scope_roots"]):
        return 1, f"{path}：在範圍外，不得登記"
    if path in norm["exact"]:
        return 1, f"{path}：已登記為 {norm['exact'][path]}"
    if cls is None:
        covering = classify(path, norm)
        if covering is not None:
            return 0, f"{path}：已由 prefix 涵蓋為 {covering}，不需登記"
        cls = _default_class(path, norm["schema"])
    if cls not in norm["class_enum"]:
        return 1, f"類別 {cls} 不屬 class_enum"
    exact = [list(item) for item in reg["exact"]] + [[path, cls]]
    trial = dict(reg)
    trial["exact"] = exact
    terrs, _ = validate_registry(trial)
    if terrs:
        return 1, "登記後不合規：" + "；".join(terrs)
    trial["exact"] = sorted(exact, key=lambda it: (_byte_key(it[1]), _byte_key(it[0])))
    text = json.dumps(trial, ensure_ascii=False, indent=2) + "\n"
    tmp = reg_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, reg_path)
    return 0, f"{path}：已登記為 {cls}"


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="_live_doc_registry.py", add_help=True)
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--path")
    g.add_argument("--all", action="store_true")
    g.add_argument("--staged", action="store_true")
    g.add_argument("--migration", action="store_true")
    c.add_argument("--index", action="store_true")
    u = sub.add_parser("update")
    u.add_argument("--add", required=True)
    u.add_argument("--class", dest="cls")
    f = sub.add_parser("flag")
    f.add_argument("--name", required=True)
    f.add_argument("--path", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 2
    if args.cmd is None:
        ap.print_usage(sys.stderr)
        return 2
    if args.cmd == "check" and args.index and not args.migration:
        print("live_doc_registry_check: --index 只與 --migration 併用 ⇒ fail-closed", file=sys.stderr)
        return 2
    root = repo_root()
    if args.cmd == "flag":
        # DOCROT2 Task 2.5：供既有檢查依類別旗標路由。stdout 恰一詞：true｜false｜unregistered｜out-of-scope
        errs, norm = _load(root)
        if errs or not norm:
            print("live_doc_registry_check: 登記檔不合規 ⇒ fail-closed：" + "；".join(errs), file=sys.stderr)
            return 2
        if not in_scope(args.path, norm["scope_roots"]):
            print("out-of-scope")
            return 0
        cls = classify(args.path, norm)
        if cls is None:
            print("unregistered")
            return 0
        flags = (load_json(os.path.join(root, REGISTRY_REL)).get("class_flags") or {}).get(cls) or {}
        if args.name not in flags or not isinstance(flags[args.name], bool):
            print(f"live_doc_registry_check: 類別 {cls} 無布林旗標 {args.name} ⇒ fail-closed", file=sys.stderr)
            return 2
        print("true" if flags[args.name] else "false")
        return 0
    if args.cmd == "update":
        rc, msg = update_add(root, args.add, args.cls)
        print(f"live_doc_registry_update: {msg}", file=sys.stderr if rc else sys.stdout)
        return rc
    if args.path is not None:
        errs, msg = check_path(root, args.path)
    elif args.all:
        errs, msg = check_all(root), ""
    elif args.migration:
        try:
            errs, msg = check_migration(root, "index" if args.index else "worktree")
        except MigrationConfigError as exc:
            print(f"live_doc_registry_check: --migration 無法判定 ⇒ fail-closed：{exc}", file=sys.stderr)
            return 2
    else:
        errs, msg = check_staged(root), ""
    if errs:
        print("live_doc_registry_check: 🔴 違規", file=sys.stderr)
        for e in errs:
            print(f"  · {e}", file=sys.stderr)
        return 1
    if msg:
        print(f"live_doc_registry_check: {msg}")
    else:
        print("live_doc_registry_check: ✓ 合規")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
