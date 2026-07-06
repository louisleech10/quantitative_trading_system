#!/usr/bin/env python3
"""verification_claim_check.py — claim-object 偵測與 provenance 判定（router，非 judge）。

誠實邊界：careless-proof + tamper-evident，非防惡意偽造；分類器只路由語境與
provenance，不判斷「人對結果的詮釋是否正確」。法官是 receipt / audit / ledger 對不對得上。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

DEFAULT_RECEIPTS_DIR = Path("handoffs/run_receipts")
DEFAULT_AUDIT_LOG_PATH = Path(".claude/gate/verify_audit.log")
DEFAULT_COMMITTEE_AUDIT_LOG_PATH = Path(".claude/gate/audit.log")
DEFAULT_PENDING_LEDGER = Path("handoffs/pending_verifications.jsonl")
RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
COMMITTEE_AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"

ZWSP_CHARS = "\u200b\u200c\u200d\ufeff"
HYPHEN_CHARS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

STRONG_POLARITY_RE = re.compile(
    r"(?:"
    r"已驗|驗收.{0,12}通過|全綠|綠燈|真紅|真跑|也正確紅|正確紅|探針紅|搞定|"
    r"無\s*look[- ]?ahead|runtime\s+PASS|signoff|"
    r"已完成.{0,20}(?:mutation|慢測|回歸|adversarial|code\s*review)"
    r")",
    re.IGNORECASE,
)
WEAK_POLARITY_RE = re.compile(r"(?:\bpassed\b|通過)", re.IGNORECASE)
DONE_READY_RE = re.compile(r"(?:\bDONE\b|(?<!-)\bready\b)", re.IGNORECASE)

VERIFY_RE = re.compile(r"(?:VERIFY|REF):([A-Za-z0-9_.\-:]+(?:/[\w./\-]+)?)")
SIGNOFF_RE = re.compile(r"SIGNOFF:([A-Za-z0-9_.\-:]+(?::[A-Za-z0-9_.\-:]+)*)")
SUPERSEDED_RE = re.compile(
    r"SUPERSEDED[:\s\]]|取代.{0,20}VERIFY:",
    re.IGNORECASE,
)
DISCUSSION_MARKER_RE = re.compile(
    r"<\!\-\-\s*claim-context:\s*discussion\s*\-\->",
    re.IGNORECASE,
)
ATTRIBUTION_RE = re.compile(
    r"把.{0,60}寫成|宣稱|不實|捏造|誤讀|事故|SUPERSEDED|假綠|無牙齒",
    re.IGNORECASE,
)
GATE_META_DISCUSSION_RE = re.compile(
    r"quoted-polarity|"
    r"假歸屬|"
    r"citation/discussion|"
    r"discussion 豁免|"
    r"VERIFY/REF/SIGNOFF|"
    r"operational claim|"
    r"已驗/真紅|已驗/.*/(?:真紅|綠燈)|"
    r"不能證明|"
    r"\b(?:BOUNDARY|BROKEN|HOLDS|CLOSED)\b|"
    r"verify[_-]?gate|checker|"
    r"B-CLASS|B-LEDGER|#7 RESULT|W8|"
    r"pytest tests/governance|"
    r"全回歸|"
    r"workflow|後盾|緊急逃生|"
    r"signoff 帶|MEMORY PASS",
    re.IGNORECASE,
)
ATTRIBUTION_SOURCE_RE = re.compile(
    r"(?:寫道|檔案說|檔案寫道|報告稱|according\s+to)",
    re.IGNORECASE,
)
QUOTED_VERDICT_RE = re.compile(
    r"(?:已驗|真紅|APPROVED|綠燈|全綠|\bPASS\b|\bDONE\b)",
    re.IGNORECASE,
)
EXEMPT_RE = re.compile(
    r"VERIFY-EXEMPT:(typo|doc-example|migration-note|template-drift|tooling-blocked|spec-ambiguity):([A-Za-z0-9_.\-]+)",
    re.IGNORECASE,
)

EXCLUSION_PATTERNS = [
    re.compile(r"`[^`]*passed[^`]*`", re.IGNORECASE),
    re.compile(r"passed\s+through", re.IGNORECASE),
    re.compile(r"通過層\s*6\.5"),
]

RUNTIME_CLAIM_RE = re.compile(
    r"(?:mutation|慢測|真跑|requires_kline|runtime|test_mutation_|真紅)",
    re.IGNORECASE,
)
MUTATION_CLAIM_RE = re.compile(r"(?:mutation|test_mutation_|真紅|也正確紅)", re.IGNORECASE)
NODE_ID_RE = re.compile(r"[\w./-]+::test_[\w]+")
MARKER_RE = re.compile(r"\brequires_kline\b")
TASK_ID_RE = re.compile(r"\b([A-Z]{1,3}\d+-[A-Za-z0-9_.\-]+|[A-Za-z0-9]{6,12})\b")

OPERATIONAL_SECTION_RE = re.compile(
    r"^#{1,3}\s*(?:正在做|待辦|已完成|現役任務|STATUS)|^(?:STATUS|RESULT)\s*:",
    re.IGNORECASE | re.MULTILINE,
)

RUNTIME_CLASS_RANK = {
    "static_only": 0,
    "helper_smoke": 1,
    "requires_kline_runtime": 2,
    "mutation_runtime": 3,
}

RESULT_FIELD_RE = re.compile(
    r"^(STATIC_CHECK|RUNTIME_CHECK|MUTATION_CHECK|RECEIPTS|OPEN_PENDING)\s*=\s*(.+)$",
    re.MULTILINE,
)
CHECK_ENUM_RE = re.compile(r"^(NOT_RUN|PASS|FAIL|N/A:.+)$")
REQUIRED_RESULT_FIELDS = (
    "STATIC_CHECK",
    "RUNTIME_CHECK",
    "MUTATION_CHECK",
    "RECEIPTS",
    "OPEN_PENDING",
)

@dataclass
class Unit:
    """可掃描的文字單位。"""

    text: str
    source_file: str
    source_line: int
    in_fenced: bool = False
    in_quote: bool = False
    in_backtick: bool = False
    section_operational: bool = False


@dataclass
class ClaimObject:
    """從單位抽取的 claim-object。"""

    polarity: str  # success|failure|supersede|pending|discussion|none
    scope: list[str] = field(default_factory=list)
    runtime_expectation: str = "none"
    source_context: str = "discussion_quote"
    backing_ids: list[str] = field(default_factory=list)
    source_line_text: str = ""
    task_id: str = ""
    is_operational: bool = False
    has_strong_polarity: bool = False
    has_done_ready: bool = False


@dataclass
class Violation:
    """違規記錄。"""

    file: str
    line: int
    message: str
    unit_text: str


def _receipts_dir() -> Path:
    override = os.environ.get(RECEIPTS_DIR_ENV)
    return Path(override) if override else DEFAULT_RECEIPTS_DIR


def _audit_log_path() -> Path:
    override = os.environ.get(AUDIT_LOG_ENV)
    return Path(override) if override else DEFAULT_AUDIT_LOG_PATH


def _pending_ledger_path() -> Path:
    override = os.environ.get(PENDING_LEDGER_ENV)
    return Path(override) if override else DEFAULT_PENDING_LEDGER


def _is_test_isolation() -> bool:
    return bool(os.environ.get(RECEIPTS_DIR_ENV) or os.environ.get(AUDIT_LOG_ENV))


def normalize(text: str) -> str:
    """NFKC + 去零寬 + 統一 hyphen/空白。"""
    normalized = unicodedata.normalize("NFKC", text)
    for ch in ZWSP_CHARS:
        normalized = normalized.replace(ch, "")
    for ch in HYPHEN_CHARS:
        normalized = normalized.replace(ch, "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _strip_exclusions(text: str) -> str:
    """扣除白名單片段後再掃極性。"""
    cleaned = text
    for pattern in EXCLUSION_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned


def _strip_inline_backticks(text: str) -> str:
    """移除反引號內容（引用 pytest 輸出等）。"""
    return re.sub(r"`[^`]*`", " ", text)


def _strip_chinese_quotes(text: str) -> str:
    """移除中文引號內容（規格示例/討論引用）。"""
    return re.sub(r"「[^」]*」", " ", text)


def _strip_all_quotes(text: str) -> str:
    """移除各類引號與反引號內容（citation 判定用）。"""
    cleaned = text
    for pattern in (
        r"「[^」]*」",
        r"『[^』]*』",
        r'"[^"]*"',
        r"'[^']*'",
        r"`[^`]*`",
    ):
        cleaned = re.sub(pattern, " ", cleaned)
    return cleaned


def _has_polarity_outside_quotes(text: str) -> bool:
    """極性詞是否出現在引號外（作者新宣稱）。"""
    outside = _strip_all_quotes(text)
    scan = _claim_polarity_text(outside)
    norm = normalize(scan)
    return bool(STRONG_POLARITY_RE.search(norm) or STRONG_POLARITY_RE.search(norm.casefold()))


def _polarity_scan_text(text: str) -> str:
    """極性掃描用淨化文字。"""
    cleaned = _strip_inline_backticks(text)
    cleaned = _strip_chinese_quotes(cleaned)
    cleaned = _strip_exclusions(cleaned)
    return cleaned


def split_units(content: str, source_file: str) -> list[Unit]:
    """段切分：markdown block、列表項、表格列各自為單位。"""
    units: list[Unit] = []
    lines = content.splitlines()
    in_fenced = False
    in_blockquote = False
    block_lines: list[str] = []
    block_start = 1
    block_fenced = False
    block_quote = False

    def flush_block(end_line: int) -> None:
        nonlocal block_lines, block_start, block_fenced, block_quote
        if not block_lines:
            return
        text = "\n".join(block_lines).strip()
        if text:
            units.append(
                Unit(
                    text=text,
                    source_file=source_file,
                    source_line=block_start,
                    in_fenced=block_fenced,
                    in_quote=block_quote,
                    section_operational=_line_in_operational_section(content, block_start),
                )
            )
        block_lines = []

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_block(idx)
            in_fenced = not in_fenced
            block_start = idx + 1
            block_fenced = in_fenced
            block_quote = False
            continue

        is_quote = stripped.startswith(">") or in_blockquote
        if stripped.startswith(">"):
            in_blockquote = True
        elif stripped == "":
            in_blockquote = False
        elif not stripped.startswith("|") and not stripped.startswith(("-", "*", "+")):
            in_blockquote = False

        if stripped == "" and not in_fenced:
            flush_block(idx)
            block_start = idx + 1
            block_fenced = False
            block_quote = False
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            flush_block(idx)
            units.append(
                Unit(
                    text=stripped,
                    source_file=source_file,
                    source_line=idx,
                    in_fenced=False,
                    in_quote=False,
                    section_operational=_line_in_operational_section(content, idx),
                )
            )
            block_start = idx + 1
            continue

        if re.match(r"^[-*+]\s+", stripped) and not in_fenced:
            flush_block(idx)
            units.append(
                Unit(
                    text=stripped,
                    source_file=source_file,
                    source_line=idx,
                    in_fenced=False,
                    in_quote=is_quote,
                    section_operational=_line_in_operational_section(content, idx),
                )
            )
            block_start = idx + 1
            continue

        if not block_lines:
            block_start = idx
            block_fenced = in_fenced
            block_quote = is_quote or in_fenced
        block_lines.append(line)

    flush_block(len(lines))
    return units


def _line_in_operational_section(content: str, line_no: int) -> bool:
    """判斷行是否落在 operational 標題段內。"""
    current_operational = False
    for idx, line in enumerate(content.splitlines(), start=1):
        if OPERATIONAL_SECTION_RE.search(line):
            current_operational = True
        elif re.match(r"^#{1,2}\s+", line) and not OPERATIONAL_SECTION_RE.search(line):
            current_operational = False
        if idx == line_no:
            return current_operational
    return False


def _has_claim_signals_outside_exempt_regions(text: str) -> bool:
    """非 inline-code 區域是否含 VERIFY/REF/SIGNOFF 或強極性/DONE。"""
    outside = _strip_inline_backticks(text)
    if VERIFY_RE.search(outside) or SIGNOFF_RE.search(outside):
        return True
    scan = VERIFY_RE.sub(" ", outside)
    scan = SIGNOFF_RE.sub(" ", scan)
    scan = NODE_ID_RE.sub(" ", scan)
    norm = normalize(scan)
    if STRONG_POLARITY_RE.search(norm) or STRONG_POLARITY_RE.search(norm.casefold()):
        return True
    if DONE_READY_RE.search(norm):
        return True
    return False


def _is_content_discussion_exempt(unit: Unit) -> bool:
    """O3 內容級豁免：僅 fenced / blockquote / inline-code / 引號內範例字串。"""
    if unit.in_fenced or unit.in_quote:
        return True
    return not _has_claim_signals_outside_exempt_regions(unit.text)


def _committee_audit_path() -> Path:
    """回傳 committee dispatch/output 審計 log 路徑。"""
    override = os.environ.get(COMMITTEE_AUDIT_ENV)
    return Path(override) if override else DEFAULT_COMMITTEE_AUDIT_LOG_PATH


def _committee_output_rel(path: str) -> str:
    """正規化 committee output path 到 handoffs/ 相對段。"""
    norm = path.replace("\\", "/")
    marker = "handoffs/"
    idx = norm.find(marker)
    if idx >= 0:
        return norm[idx:]
    return norm


def _committee_registered_files() -> dict[str, set[str]]:
    """讀 committee audit log，回傳 {output_path: raw_sha256集合}。"""
    audit_log = _committee_audit_path()
    if not audit_log.is_file():
        return {}
    registered: dict[str, set[str]] = {}
    for raw in audit_log.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") not in {"committee_dispatch", "committee_output"}:
            continue
        output_path = _committee_output_rel(str(event.get("output_path", "")))
        output_sha256 = str(event.get("output_sha256", ""))
        if not output_path.startswith("handoffs/"):
            continue
        if not output_sha256 or output_sha256 == "pending":
            continue
        registered.setdefault(output_path, set()).add(output_sha256)
    return registered


def _is_committee_process_exempt(rel: str, source_path: Path) -> bool:
    """已註冊且 raw bytes hash 相符的 handoffs 委員會過程檔可豁免 prose claim。"""
    if os.environ.get("VERIFY_GATE_O3_FILECLASS", "1") == "0":
        return False
    norm = _committee_output_rel(rel)
    if not norm.startswith("handoffs/"):
        return False
    if Path(norm).name == "HANDOFF.md":
        return False
    hashes = _committee_registered_files().get(norm, set())
    if not hashes or not source_path.is_file():
        return False
    actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return actual in hashes


def _is_docs_operational_unit(unit: Unit) -> bool:
    """docs/* 內 operational 段（## 已完成 / STATUS: / RESULT 硬欄位）。"""
    path = unit.source_file.replace("\\", "/")
    if not (path.startswith("docs/") or "/docs/" in path):
        return False
    if unit.section_operational:
        return True
    stripped = unit.text.strip()
    if re.match(r"^(?:STATUS|RESULT)\s*:", stripped, re.IGNORECASE):
        return True
    return False


def _detect_source_context(unit: Unit) -> str:
    """依檔案路徑與段落決定 source_context。"""
    path = unit.source_file.replace("\\", "/")
    name = Path(path).name

    if path.endswith("COMMIT_MSG") or "commit" in path.lower():
        return "commit_msg"

    if name == "HANDOFF.md":
        return "root_handoff_status"

    if name.endswith("-RESULT.md") or "RESULT" in name:
        return "operational_result"

    if path.startswith("docs/") or "/docs/" in path:
        if _is_docs_operational_unit(unit):
            return "operational_result"
        return "docs_spec"

    if unit.section_operational:
        return "operational_result"

    return "discussion_quote"


def _extract_scope(text: str) -> list[str]:
    """從文字抽取 scope 線索。"""
    scope: list[str] = []
    for match in NODE_ID_RE.finditer(text):
        scope.append(match.group(0))
    for match in MARKER_RE.finditer(text):
        scope.append(match.group(0))
    for match in re.finditer(r"test_[A-Za-z0-9_]+", text):
        scope.append(match.group(0))
    for match in re.finditer(r"tests/[\w./\-]+\.py", text):
        scope.append(match.group(0))
    return list(dict.fromkeys(scope))


def _extract_task_id(text: str, source_file: str) -> str:
    """抽取 task_id（優先 P0-FF-3 樣式、檔名、括號內 id）。"""
    stem = Path(source_file).stem
    stem = re.sub(r"-RESULT$", "", stem, flags=re.IGNORECASE)
    blob = f"{stem} {text}"
    for pattern in (
        r"\b(P\d+-FF-\d+)\b",
        r"\b(P\d+-[A-Z]+-\d+)\b",
        r"\b([A-Z]{1,3}\d+-[A-Za-z0-9_.\-]+)\b",
        r"(\d{8}-[A-Z0-9][A-Z0-9\-]+)",
    ):
        match = re.search(pattern, blob)
        if match:
            return match.group(1)
    paren_match = re.search(r"\(([a-z0-9]{6,12})\)", text)
    if paren_match:
        return paren_match.group(1)
    return ""


def _runtime_expectation_from_text(text: str) -> str:
    """由 claim 文字推導 runtime_expectation。"""
    if MUTATION_CLAIM_RE.search(text):
        return "mutation"
    if re.search(r"慢測|真跑|requires_kline", text, re.IGNORECASE):
        return "requires_kline"
    if re.search(r"smoke|helper", text, re.IGNORECASE):
        return "smoke"
    if re.search(r"static|讀碼", text, re.IGNORECASE):
        return "static"
    if RUNTIME_CLAIM_RE.search(text):
        return "requires_kline"
    return "none"


def _claim_polarity_text(text: str) -> str:
    """極性掃描用文字（排除 VERIFY id、node-id 避免誤判）。"""
    cleaned = VERIFY_RE.sub(" ", text)
    cleaned = SIGNOFF_RE.sub(" ", cleaned)
    cleaned = NODE_ID_RE.sub(" ", cleaned)
    return _polarity_scan_text(cleaned)


def extract_claim(unit: Unit) -> ClaimObject:
    """從單位抽取 claim-object。"""
    scan_text = _claim_polarity_text(unit.text)
    norm_text = normalize(scan_text)
    casefold_text = norm_text.casefold()

    backing_ids = [m.group(1) for m in VERIFY_RE.finditer(unit.text)]
    signoff_ids = [m.group(1) for m in SIGNOFF_RE.finditer(unit.text)]

    has_strong = bool(STRONG_POLARITY_RE.search(norm_text) or STRONG_POLARITY_RE.search(casefold_text))
    source_context = _detect_source_context(unit)
    weak_allowed = source_context in {
        "operational_result",
        "commit_msg",
        "root_handoff_status",
    }
    has_weak = weak_allowed and bool(
        WEAK_POLARITY_RE.search(norm_text) or WEAK_POLARITY_RE.search(casefold_text)
    )
    has_done_ready = bool(DONE_READY_RE.search(norm_text))

    polarity = "none"
    if SUPERSEDED_RE.search(unit.text):
        polarity = "supersede"
    elif has_strong or has_weak:
        if re.search(r"紅燈", scan_text, re.IGNORECASE) or re.search(
            r"\bfailed\b", scan_text, re.IGNORECASE
        ):
            polarity = "failure"
        else:
            polarity = "success"

    runtime_expectation = _runtime_expectation_from_text(unit.text)
    scope = _extract_scope(unit.text)
    task_id = _extract_task_id(unit.text, unit.source_file)

    is_operational = source_context in {
        "operational_result",
        "commit_msg",
        "root_handoff_status",
    }

    return ClaimObject(
        polarity=polarity,
        scope=scope,
        runtime_expectation=runtime_expectation,
        source_context=source_context,
        backing_ids=backing_ids + [f"SIGNOFF:{sid}" for sid in signoff_ids],
        source_line_text=unit.text.strip(),
        task_id=task_id,
        is_operational=is_operational,
        has_strong_polarity=has_strong or has_weak,
        has_done_ready=has_done_ready,
    )


def claim_fingerprint(claim: ClaimObject) -> str:
    """計算 claim_fingerprint（供 ledger / 衝突檢查）。

    使用 canonical 主題項（scope + runtime_expectation + task_id），
    剝除 VERIFY/SUPERSEDED/極性詞/收據 id 等狀態文字差異。
    """
    scope_blob = ",".join(claim.scope)
    payload = normalize(f"{scope_blob}|{claim.runtime_expectation}|{claim.task_id}")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_result_file(path: str) -> bool:
    """是否為 RESULT handoff 檔。"""
    name = Path(path).name
    return name.endswith("-RESULT.md") or "RESULT" in name.upper()


def parse_result_fields(content: str) -> dict[str, str]:
    """解析 RESULT 結構欄位（枚舉值）。"""
    fields: dict[str, str] = {}
    for match in RESULT_FIELD_RE.finditer(content):
        key = match.group(1)
        value = match.group(2).strip()
        fields[key] = value
    return fields


def _parse_receipts_list(value: str) -> list[str]:
    """解析 RECEIPTS=[...] 為 id 清單。"""
    cleaned = value.strip()
    if cleaned in ("[]", ""):
        return []
    inner = cleaned.strip("[]").strip()
    if not inner:
        return []
    items: list[str] = []
    for part in inner.split(","):
        token = part.strip().strip('"').strip("'")
        if token:
            items.append(token)
    return items


def _line_of_result_field(content: str, field_name: str) -> int:
    """找 RESULT 結構欄位所在行號。"""
    for idx, line in enumerate(content.splitlines(), start=1):
        if line.strip().startswith(f"{field_name}="):
            return idx
    return 1


def _validate_check_enum(field_name: str, value: str) -> str | None:
    """驗證 RESULT 檢查欄位枚舉值；不合規回傳錯誤訊息。"""
    if CHECK_ENUM_RE.match(value):
        return None
    return (
        f"RESULT {field_name} 枚舉外值: {value}"
        f"（允許 NOT_RUN|PASS|FAIL|N/A:reason）"
    )


def _validate_receipts_format(value: str) -> str | None:
    """驗證 RECEIPTS 為 [...] 陣列格式。"""
    cleaned = value.strip()
    if not cleaned.startswith("[") or not cleaned.endswith("]"):
        return "RESULT RECEIPTS 格式須為 [...] 陣列"
    inner = cleaned[1:-1].strip()
    if not inner:
        return None
    try:
        parsed = json.loads(cleaned.replace("'", '"'))
    except json.JSONDecodeError:
        _parse_receipts_list(cleaned)
        return None
    if not isinstance(parsed, list):
        return "RESULT RECEIPTS 須為字串 id 陣列"
    if not all(isinstance(item, str) for item in parsed):
        return "RESULT RECEIPTS 陣列元素須為字串 receipt id"
    return None


def check_result_structured_fields(source_file: str, content: str) -> list[Violation]:
    """RESULT 硬欄位交叉驗證（P5-1）。"""
    violations: list[Violation] = []
    if not _is_result_file(source_file):
        return violations

    fields = parse_result_fields(content)

    for field_name in REQUIRED_RESULT_FIELDS:
        if field_name not in fields:
            violations.append(
                Violation(
                    file=source_file,
                    line=_line_of_result_field(content, field_name),
                    message=f"RESULT 缺必填欄位 {field_name}",
                    unit_text=content[:200],
                )
            )

    for field_name in ("STATIC_CHECK", "RUNTIME_CHECK", "MUTATION_CHECK"):
        if field_name not in fields:
            continue
        enum_error = _validate_check_enum(field_name, fields[field_name])
        if enum_error:
            violations.append(
                Violation(
                    file=source_file,
                    line=_line_of_result_field(content, field_name),
                    message=enum_error,
                    unit_text=f"{field_name}={fields[field_name]}",
                )
            )

    if "RECEIPTS" in fields:
        receipts_error = _validate_receipts_format(fields["RECEIPTS"])
        if receipts_error:
            violations.append(
                Violation(
                    file=source_file,
                    line=_line_of_result_field(content, "RECEIPTS"),
                    message=receipts_error,
                    unit_text=f"RECEIPTS={fields['RECEIPTS']}",
                )
            )

    if violations:
        return violations

    runtime_check = fields.get("RUNTIME_CHECK", "")
    receipts = _parse_receipts_list(fields.get("RECEIPTS", "[]"))
    if runtime_check == "PASS" and not receipts:
        violations.append(
            Violation(
                file=source_file,
                line=_line_of_result_field(content, "RUNTIME_CHECK"),
                message="RESULT RUNTIME_CHECK=PASS 但 RECEIPTS=[]",
                unit_text=(
                    f"RUNTIME_CHECK={runtime_check}\n"
                    f"RECEIPTS={fields.get('RECEIPTS', '[]')}"
                ),
            )
        )

    mutation_check = fields.get("MUTATION_CHECK", "")
    if mutation_check == "NOT_RUN":
        for unit in split_units(content, source_file):
            claim = extract_claim(unit)
            if claim.has_strong_polarity and claim.is_operational:
                violations.append(
                    Violation(
                        file=source_file,
                        line=unit.source_line,
                        message="RESULT MUTATION_CHECK=NOT_RUN 但同 task 含已驗/極性宣稱",
                        unit_text=unit.text,
                    )
                )
                break
    return violations


def _is_failure_record(unit: Unit, claim: ClaimObject) -> bool:
    """是否為 FAIL/紅燈紀錄（供 #6 衝突檢查）。"""
    if claim.polarity == "failure":
        return True
    if re.search(r"紅燈", unit.text, re.IGNORECASE):
        return True
    if re.search(r"\bFAIL\b", unit.text):
        return True
    fields = parse_result_fields(unit.text)
    for key in ("STATIC_CHECK", "RUNTIME_CHECK", "MUTATION_CHECK"):
        if fields.get(key, "").startswith("FAIL"):
            return True
    return False


def _is_green_verify(unit: Unit, claim: ClaimObject) -> bool:
    """是否為 VERIFY 支撐的綠 claim。"""
    return bool(VERIFY_RE.search(unit.text)) and claim.polarity == "success"


def check_fingerprint_conflicts(
    units_with_claims: list[tuple[Unit, ClaimObject]],
) -> list[Violation]:
    """#6 衝突檢查：同 fingerprint 有 FAIL/紅燈後，舊 VERIFY 綠未標 SUPERSEDED → FAIL。"""
    violations: list[Violation] = []
    by_fp: dict[str, list[tuple[Unit, ClaimObject]]] = {}
    for unit, claim in units_with_claims:
        fp = claim_fingerprint(claim)
        by_fp.setdefault(fp, []).append((unit, claim))

    for records in by_fp.values():
        has_failure = any(_is_failure_record(u, c) for u, c in records)
        if not has_failure:
            continue
        for unit, claim in records:
            if _is_green_verify(unit, claim) and not SUPERSEDED_RE.search(unit.text):
                violations.append(
                    Violation(
                        file=unit.source_file,
                        line=unit.source_line,
                        message=(
                            "claim_fingerprint 衝突：曾有 FAIL/紅燈紀錄，"
                            "舊 VERIFY 綠 claim 未標 SUPERSEDED"
                        ),
                        unit_text=unit.text,
                    )
                )
    return violations


def _has_quoted_polarity(text: str) -> bool:
    """中文引號內含驗收判詞（假歸屬自我認證偵測用）。"""
    for pattern in (r"「([^」]+)」", r"『([^』]+)』"):
        for match in re.finditer(pattern, text):
            inner = match.group(1)
            scan = normalize(_claim_polarity_text(inner))
            if QUOTED_VERDICT_RE.search(scan) or STRONG_POLARITY_RE.search(scan):
                return True
    return False


def _resolve_attributed_path(text: str) -> Path | None:
    """從歸屬語句解析被引用檔案路徑（若存在）。"""
    for match in re.finditer(r"(?:handoffs|docs)/[\w./\-]+\.md", text):
        candidate = Path(match.group(0))
        if candidate.is_file():
            return candidate
    return None


def _file_content_has_backing(content: str) -> bool:
    """檔案內容是否含 receipt/戳記/委員閉合判詞（REF 檔案 backing 判定）。"""
    if VERIFY_RE.search(content) or SIGNOFF_RE.search(content) or "RECONCILE-STAMP:" in content:
        return True
    if re.search(r"\b(?:CLOSED|APPROVED)\b", content):
        return True
    return False


def _attributed_file_has_backing(text: str) -> bool:
    """被歸屬檔案實含 VERIFY/REF/SIGNOFF、reconcile 戳記或委員閉合判詞。"""
    path = _resolve_attributed_path(text)
    if path is None:
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return _file_content_has_backing(content)


def _is_ref_file_path(backing_id: str) -> bool:
    """REF token 是否為 handoffs/docs 檔案路徑（非 receipt id）。"""
    return "/" in backing_id or backing_id.endswith(".md")


def _is_fake_attribution_self_cert(unit: Unit) -> bool:
    """假歸屬 citation：引號內判詞 + X 寫道/檔案說，無真 backing。"""
    outside = _strip_inline_backticks(unit.text)
    if not ATTRIBUTION_SOURCE_RE.search(outside):
        return False
    if not _has_quoted_polarity(outside):
        return False
    if VERIFY_RE.search(outside) or SIGNOFF_RE.search(outside):
        return False
    if _attributed_file_has_backing(outside):
        return False
    return True


def _claim_has_parseable_scope(claim: ClaimObject) -> bool:
    """claim 是否有可解析 scope（node-id/檔案）或 runtime 線索。"""
    if claim.scope:
        return True
    if claim.runtime_expectation != "none":
        return True
    return False


def _is_citation(unit: Unit) -> bool:
    """引用/討論原文（非作者 operational 新宣稱）。"""
    if _is_fake_attribution_self_cert(unit):
        return False
    if unit.in_fenced or unit.in_quote:
        return True
    if DISCUSSION_MARKER_RE.search(unit.text) and (unit.in_fenced or unit.in_quote):
        return True
    if GATE_META_DISCUSSION_RE.search(unit.text):
        return True
    if not _has_polarity_outside_quotes(unit.text):
        if STRONG_POLARITY_RE.search(normalize(_claim_polarity_text(unit.text))):
            return True
    if ATTRIBUTION_RE.search(unit.text):
        return True
    return False


def classify_mode(unit: Unit, claim: ClaimObject) -> str:
    """模式判定：citation|supersede|discussion|operational|neutral。"""
    if SUPERSEDED_RE.search(unit.text):
        return "supersede"
    if _is_content_discussion_exempt(unit):
        return "discussion"
    if _is_fake_attribution_self_cert(unit):
        return "operational"
    if _is_citation(unit):
        return "discussion"
    if claim.source_context == "docs_spec":
        return "discussion"
    if claim.has_strong_polarity and not claim.backing_ids:
        return "operational"
    if VERIFY_RE.search(unit.text) or SIGNOFF_RE.search(unit.text):
        return "citation"
    if claim.is_operational and claim.has_strong_polarity:
        return "operational"
    if claim.is_operational and claim.has_done_ready:
        return "operational"
    return "neutral"


def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_git_bytes(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    """binary-safe git 子程序（避免非 UTF-8 blob 在 subprocess 層 decode crash）。"""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
    )


def _is_tracked_or_staged(path: Path) -> bool:
    """W12：receipt 須已 tracked 或 staged；測試隔離模式跳過。"""
    if _is_test_isolation():
        return path.is_file()
    if not path.is_file():
        return False
    rel = path.as_posix()
    staged = _run_git(["diff", "--cached", "--name-only", "--", rel])
    if staged.returncode == 0 and rel in staged.stdout.splitlines():
        return True
    tracked = _run_git(["ls-files", "--error-unmatch", rel])
    return tracked.returncode == 0


def _load_audit_events() -> list[dict[str, Any]]:
    audit_path = _audit_log_path()
    if not audit_path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _find_receipt_path(receipt_id: str) -> Path | None:
    """依 receipt_id 或 claim_id 後綴找 receipt JSON。"""
    receipts_dir = _receipts_dir()
    direct = receipts_dir / f"{receipt_id}.json"
    if direct.is_file():
        return direct
    matches = sorted(receipts_dir.glob(f"*-{receipt_id}.json"))
    if matches:
        return matches[-1]
    for path in sorted(receipts_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("receipt_id") == receipt_id or data.get("claim_id") == receipt_id:
            return path
    return None


def _load_receipt(receipt_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    path = _find_receipt_path(receipt_id)
    if path is None:
        return None, None
    return path, json.loads(path.read_text(encoding="utf-8"))


def _node_id_matches(claim_node: str, receipt_nodes: Iterable[str]) -> bool:
    """node-id 須全等或 test 函式名後綴一致；共用檔路徑不足。"""
    nodes = list(receipt_nodes)
    if claim_node in nodes:
        return True
    claim_suffix = claim_node.split("::", 1)[-1]
    return any(rn.split("::", 1)[-1] == claim_suffix for rn in nodes)


def _scope_intersects(claim: ClaimObject, receipt: dict[str, Any]) -> bool:
    """claim scope 與 receipt node/markers 須有非空交集；無 scope 線索時放行。"""
    if not claim.scope:
        return True
    receipt_nodes = list(receipt.get("selected_node_ids") or [])
    receipt_markers = set(receipt.get("markers") or [])
    claim_nodes = [item for item in claim.scope if "::" in item]
    claim_other = [item for item in claim.scope if "::" not in item]

    if claim_nodes:
        if not receipt_nodes:
            return False
        if not all(_node_id_matches(node, receipt_nodes) for node in claim_nodes):
            return False
        if not claim_other:
            return True

    if not claim_other:
        return True

    receipt_scope: set[str] = set(receipt_nodes)
    receipt_scope.update(receipt_markers)
    receipt_scope.add(str(receipt.get("claim_id", "")))
    for item in claim_other:
        matched = False
        for candidate in receipt_scope:
            if item == candidate or item in candidate or candidate in item:
                matched = True
                break
        if not matched:
            return False
    return True


def _runtime_class_sufficient(claim: ClaimObject, runtime_class: str) -> bool:
    """runtime_class 是否足以支撐 claim 語意。"""
    if claim.runtime_expectation == "none" and not MUTATION_CLAIM_RE.search(claim.source_line_text):
        if not re.search(r"慢測|真跑|requires_kline", claim.source_line_text, re.IGNORECASE):
            return True
    if claim.runtime_expectation == "static":
        return runtime_class == "static_only"
    if claim.runtime_expectation == "smoke":
        return runtime_class in {"helper_smoke", "requires_kline_runtime", "mutation_runtime"}
    if claim.runtime_expectation == "requires_kline":
        return runtime_class in {"requires_kline_runtime", "mutation_runtime"}
    if claim.runtime_expectation == "mutation" or MUTATION_CLAIM_RE.search(claim.source_line_text):
        return runtime_class == "mutation_runtime"
    if RUNTIME_CLAIM_RE.search(claim.source_line_text):
        return RUNTIME_CLASS_RANK.get(runtime_class, 0) >= RUNTIME_CLASS_RANK["requires_kline_runtime"]
    return True


def _polarity_matches(claim: ClaimObject, receipt: dict[str, Any]) -> bool:
    """極性與 receipt exit/summary 須一致。"""
    exit_code = int(receipt.get("exit_code", 1))
    failed = int(receipt.get("failed", 0))
    if claim.polarity == "failure":
        return exit_code != 0 or failed > 0
    if claim.polarity == "success":
        return exit_code == 0 and failed == 0
    return True


def check_backing(claim: ClaimObject, backing_id: str) -> tuple[bool, str]:
    """驗證 VERIFY/REF backing；回傳 (ok, reason)。"""
    if backing_id.startswith("SIGNOFF:"):
        if claim.runtime_expectation in {"mutation", "requires_kline"}:
            return False, "SIGNOFF 不得支撐 runtime/mutation claim"
        if MUTATION_CLAIM_RE.search(claim.source_line_text) and re.search(
            r"慢測|真跑|mutation", claim.source_line_text, re.IGNORECASE
        ):
            return False, "SIGNOFF 不得支撐慢測/mutation claim"
        return True, ""

    if _is_ref_file_path(backing_id):
        ref_path = Path(backing_id)
        if not ref_path.is_file():
            return False, f"REF 檔案不存在: {backing_id}"
        try:
            ref_content = ref_path.read_text(encoding="utf-8")
        except OSError:
            return False, f"REF 檔案無法讀取: {backing_id}"
        if not _file_content_has_backing(ref_content):
            return False, f"REF 檔案無 backing 內容: {backing_id}"
        return True, ""

    receipt_path, receipt = _load_receipt(backing_id)
    if receipt_path is None or receipt is None:
        return False, f"receipt 不存在: {backing_id}"

    log_path = Path(str(receipt.get("log_path", "")))
    if not log_path.is_file():
        alt_log = receipt_path.with_suffix(".log")
        if alt_log.is_file():
            log_path = alt_log
        else:
            return False, f"receipt log 不存在: {backing_id}"

    if not _is_tracked_or_staged(receipt_path) or not _is_tracked_or_staged(log_path):
        return False, f"receipt/log 未 tracked 或 staged: {backing_id}"

    events = _load_audit_events()
    receipt_id = str(receipt.get("receipt_id", receipt_path.stem))
    audit = next((ev for ev in events if ev.get("receipt_id") == receipt_id), None)
    if audit is None:
        return False, f"審計事件缺失: {receipt_id}"

    receipt_digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    log_digest = hashlib.sha256(log_path.read_bytes()).hexdigest()
    if audit.get("receipt_sha256") != receipt_digest:
        return False, f"receipt_sha256 不符: {receipt_id}"
    if audit.get("log_sha256") != log_digest:
        return False, f"log_sha256 不符: {receipt_id}"

    runtime_class = str(receipt.get("runtime_class", "static_only"))
    if not _runtime_class_sufficient(claim, runtime_class):
        return False, f"runtime_class 不足: {runtime_class} vs {claim.runtime_expectation}"

    if not _polarity_matches(claim, receipt):
        return False, f"極性與 receipt 不符: exit={receipt.get('exit_code')}"

    if claim.polarity == "success" and not _claim_has_parseable_scope(claim):
        return (
            False,
            "模糊 scope：claim 無 node-id/檔案/runtime 線索，不得用任意 receipt 洗白",
        )

    if not _scope_intersects(claim, receipt):
        return False, f"scope 無交集: {claim.scope}"

    return True, ""


def _close_event_valid(open_event: dict[str, Any], close_event: dict[str, Any]) -> bool:
    """close 須與 open 指紋/scope/runtime 一致，且 receipt 有審計事件。"""
    if close_event.get("claim_fingerprint") != open_event.get("claim_fingerprint"):
        return False
    if close_event.get("required_runtime_class") != open_event.get("required_runtime_class"):
        return False
    if list(close_event.get("required_node_ids") or []) != list(
        open_event.get("required_node_ids") or []
    ):
        return False
    if list(close_event.get("required_markers") or []) != list(
        open_event.get("required_markers") or []
    ):
        return False

    receipt_id = str(close_event.get("receipt_id", ""))
    if not receipt_id:
        return False
    receipt_path, receipt = _load_receipt(receipt_id)
    if receipt_path is None or receipt is None:
        return False

    audit_rid = str(receipt.get("receipt_id", receipt_path.stem))
    audit = next((ev for ev in _load_audit_events() if ev.get("receipt_id") == audit_rid), None)
    if audit is None:
        return False

    required_class = str(open_event.get("required_runtime_class", ""))
    runtime_class = str(receipt.get("runtime_class", ""))
    if required_class and runtime_class != required_class:
        return False

    required_nodes = list(open_event.get("required_node_ids") or [])
    if required_nodes:
        receipt_nodes = list(receipt.get("selected_node_ids") or [])
        if not all(_node_id_matches(node, receipt_nodes) for node in required_nodes):
            return False

    return True


def reduce_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """reducer：求有 open 無有效 close 的未結 pending。"""
    open_map: dict[str, dict[str, Any]] = {}
    closed: set[str] = set()
    for event in events:
        pending_id = str(event.get("pending_id", ""))
        if not pending_id:
            continue
        if event.get("event") == "open":
            open_map[pending_id] = event
        elif event.get("event") == "close":
            open_event = open_map.get(pending_id)
            if open_event and _close_event_valid(open_event, event):
                closed.add(pending_id)
    return [ev for pid, ev in open_map.items() if pid not in closed]


def load_open_pending() -> list[dict[str, Any]]:
    """讀取 ledger 未結 pending。"""
    ledger_path = _pending_ledger_path()
    if not ledger_path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return reduce_events(events)


def _open_pending_blocks(claim: ClaimObject, open_pending: list[dict[str, Any]]) -> str | None:
    """同 task 有未結 pending 時擋 DONE/已驗/ready claim。"""
    if not claim.task_id:
        return None
    if not (claim.has_strong_polarity or claim.has_done_ready):
        return None
    if not claim.is_operational:
        return None
    for pending in open_pending:
        if pending.get("task_id") == claim.task_id:
            return str(pending.get("pending_id", ""))
    return None


def _pending_closed_allows(claim: ClaimObject, open_pending: list[dict[str, Any]]) -> bool:
    """pending 已關閉後，DONE/ready 狀態宣稱可放行。"""
    if open_pending:
        return False
    if claim.has_done_ready and not claim.has_strong_polarity:
        return True
    return False


def _exempt_allowed(unit: Unit, claim: ClaimObject, *, file_verify_exempt: bool = False) -> bool:
    """VERIFY-EXEMPT 窄類別；HANDOFF/commit/RESULT 零豁免。"""
    if claim.source_context in {"root_handoff_status", "commit_msg", "operational_result"}:
        return False
    if file_verify_exempt:
        return True
    return bool(EXEMPT_RE.search(unit.text))


def _split_subclaims(text: str) -> list[str]:
    """同段多 claim 以分號切分。"""
    parts = [part.strip() for part in text.split(";")]
    return [part for part in parts if part]


def _file_verify_exempt_allowed(rel: str, content: str) -> bool:
    """檔案標頭 VERIFY-EXEMPT 對全檔 discussion 單位生效（零豁免路徑除外）。"""
    name = Path(rel).name
    if name == "HANDOFF.md" or name.endswith("-RESULT.md") or "RESULT" in name:
        return False
    return bool(EXEMPT_RE.search(content))


def check_unit(
    unit: Unit,
    open_pending: list[dict[str, Any]],
    *,
    file_verify_exempt: bool = False,
    committee_process_exempt: bool = False,
) -> list[Violation]:
    """檢查單一文字單位，回傳違規清單。"""
    violations: list[Violation] = []
    claim = extract_claim(unit)
    mode = classify_mode(unit, claim)

    pending_id = _open_pending_blocks(claim, open_pending)
    if pending_id:
        violations.append(
            Violation(
                file=unit.source_file,
                line=unit.source_line,
                message=f"task {claim.task_id} 有未結 pending {pending_id}",
                unit_text=unit.text,
            )
        )
        return violations

    if _pending_closed_allows(claim, open_pending):
        return violations

    if mode == "supersede" or mode == "discussion":
        return violations

    if committee_process_exempt and claim.source_context not in {
        "root_handoff_status",
        "commit_msg",
    }:
        return violations

    if _exempt_allowed(unit, claim, file_verify_exempt=file_verify_exempt):
        return violations

    subclaims = _split_subclaims(unit.text) if ";" in unit.text else [unit.text]
    if len(subclaims) > 1:
        for sub in subclaims:
            sub_unit = Unit(
                text=sub,
                source_file=unit.source_file,
                source_line=unit.source_line,
                in_fenced=unit.in_fenced,
                in_quote=unit.in_quote,
                section_operational=unit.section_operational,
            )
            violations.extend(
                check_unit(
                    sub_unit,
                    open_pending,
                    file_verify_exempt=file_verify_exempt,
                    committee_process_exempt=committee_process_exempt,
                )
            )
        return violations

    if mode == "neutral":
        return violations

    sub_claim = extract_claim(unit)
    sub_mode = classify_mode(unit, sub_claim)

    if sub_mode == "citation":
        if not sub_claim.backing_ids:
            violations.append(
                Violation(
                    file=unit.source_file,
                    line=unit.source_line,
                    message="citation 模式但無 backing id",
                    unit_text=unit.text,
                )
            )
            return violations
        for backing_id in sub_claim.backing_ids:
            ok, reason = check_backing(sub_claim, backing_id)
            if not ok:
                violations.append(
                    Violation(
                        file=unit.source_file,
                        line=unit.source_line,
                        message=reason or f"backing 無效: {backing_id}",
                        unit_text=unit.text,
                    )
                )
        return violations

    if sub_mode == "operational" or (sub_claim.is_operational and sub_claim.has_strong_polarity):
        violations.append(
            Violation(
                file=unit.source_file,
                line=unit.source_line,
                message="operational claim 缺少 VERIFY/REF/SIGNOFF backing",
                unit_text=unit.text,
            )
        )
    return violations


def _unknown_polarity_warn(unit: Unit) -> None:
    """未知近似詞 WARN（不 exit 1）。"""
    suspects = ["驗證通過", "測試綠", "runtime綠"]
    text = unit.text
    for word in suspects:
        if word in text and not STRONG_POLARITY_RE.search(_polarity_scan_text(text)):
            print(
                f"WARN: 疑似極性詞 '{word}' 未收錄 — {unit.source_file}:{unit.source_line}",
                file=sys.stderr,
            )


class FileReadError(Exception):
    """無法讀取待掃描檔（非 UTF-8 或 I/O 錯誤）。"""

    def __init__(self, rel_path: str, detail: str) -> None:
        self.rel_path = rel_path
        self.detail = detail
        super().__init__(f"{rel_path}: {detail}")


def _unit_touches_added_lines(unit: Unit, added_lines: set[int]) -> bool:
    """單位是否落在 staged 新增行範圍內。"""
    if not added_lines:
        return False
    span_end = unit.source_line + unit.text.count("\n")
    return any(line_no in added_lines for line_no in range(unit.source_line, span_end + 1))


def _scan_file_content(
    rel: str,
    content: str,
    source_path: Path,
    open_pending: list[dict[str, Any]],
    all_units_claims: list[tuple[Unit, ClaimObject]],
    *,
    added_lines: set[int] | None = None,
) -> list[Violation]:
    """掃描單檔文字內容，累積 claim units 並回傳違規。"""
    violations: list[Violation] = []
    file_verify_exempt = _file_verify_exempt_allowed(rel, content)
    committee_process_exempt = _is_committee_process_exempt(rel, source_path)
    for unit in split_units(content, rel):
        if added_lines is not None and not _unit_touches_added_lines(unit, added_lines):
            continue
        _unknown_polarity_warn(unit)
        claim = extract_claim(unit)
        all_units_claims.append((unit, claim))
        violations.extend(
            check_unit(
                unit,
                open_pending,
                file_verify_exempt=file_verify_exempt,
                committee_process_exempt=committee_process_exempt,
            )
        )
    if _is_result_file(rel) and added_lines is None:
        violations.extend(check_result_structured_fields(rel, content))
    return violations


def check_files(
    paths: list[Path],
    *,
    content_map: dict[str, str] | None = None,
    added_lines_map: dict[str, set[int]] | None = None,
) -> list[Violation]:
    """掃描多檔，回傳全部違規。

    content_map 若提供，以 map 內容取代 working tree read_text（供 --staged index blob）。
    added_lines_map 若提供，僅掃描各檔 staged 相對 HEAD 的新增行（--staged 增量模式）。
    """
    violations: list[Violation] = []
    open_pending = load_open_pending()
    all_units_claims: list[tuple[Unit, ClaimObject]] = []
    for path in paths:
        raw = path.as_posix()
        rel = _scannable_rel_path(raw) if _is_scannable_path(raw) else raw
        if content_map is not None and rel in content_map:
            content = content_map[rel]
        else:
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise FileReadError(rel, f"not valid UTF-8: {exc}") from exc
            except OSError as exc:
                raise FileReadError(rel, str(exc)) from exc
        added_lines = added_lines_map.get(rel) if added_lines_map is not None else None
        if added_lines_map is not None and not added_lines:
            continue
        violations.extend(
            _scan_file_content(
                rel,
                content,
                path,
                open_pending,
                all_units_claims,
                added_lines=added_lines,
            )
        )
    violations.extend(check_fingerprint_conflicts(all_units_claims))
    return violations


def _git_staged_scannable_paths() -> list[str]:
    """回傳 staged index 內可掃描 markdown 路徑（ACMR，跳過 delete）。"""
    proc = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"])
    if proc.returncode != 0:
        return []
    paths: list[str] = []
    for entry in proc.stdout.split("\0"):
        if entry and _is_scannable_path(entry):
            paths.append(entry)
    return paths


def _decode_utf8_blob(rel_path: str, raw: bytes) -> str:
    """strict UTF-8 decode；失敗時 raise FileReadError（與 working tree 契約一致）。"""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FileReadError(rel_path, "not valid UTF-8 (staged blob)") from exc


def _git_staged_blob(rel_path: str) -> str | None:
    """從 index blob 讀 staged 內容（非 working tree）。"""
    proc = _run_git_bytes(["show", f":{rel_path}"])
    if proc.returncode != 0:
        return None
    return _decode_utf8_blob(rel_path, proc.stdout)


def _git_staged_added_line_numbers(rel_path: str) -> set[int]:
    """從 git diff --cached -U0 取 staged 相對 HEAD 的新增行行號（1-based）。"""
    proc = _run_git_bytes(["diff", "--cached", "-U0", "--", rel_path])
    if proc.returncode != 0 or not proc.stdout.strip():
        return set()
    try:
        diff_text = proc.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FileReadError(rel_path, "not valid UTF-8 (staged blob)") from exc
    added: set[int] = set()
    new_line = 0
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match:
                new_line = int(match.group(1))
            continue
        if line.startswith(("diff ", "---", "+++")):
            continue
        if line.startswith("+"):
            added.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue
        else:
            new_line += 1
    return added


def _git_staged_markdown_files() -> tuple[list[Path], dict[str, str], dict[str, set[int]]]:
    """回傳 staged scannable paths、index blob 內容 map 與新增行行號 map。"""
    rel_paths = _git_staged_scannable_paths()
    paths: list[Path] = []
    content_map: dict[str, str] = {}
    added_lines_map: dict[str, set[int]] = {}
    for rel in rel_paths:
        blob = _git_staged_blob(rel)
        if blob is None:
            continue
        paths.append(Path(rel))
        content_map[rel] = blob
        added_lines_map[rel] = _git_staged_added_line_numbers(rel)
    return paths, content_map, added_lines_map


def _git_range_files(range_spec: str) -> list[Path]:
    proc = _run_git(["diff", "--name-only", range_spec])
    if proc.returncode != 0:
        return []
    return [Path(line) for line in proc.stdout.splitlines() if _is_scannable_path(line)]


def _is_scannable_path(path_str: str) -> bool:
    norm = path_str.replace("\\", "/")
    if norm == "HANDOFF.md" or norm.endswith("/HANDOFF.md"):
        return True
    for marker in ("handoffs/", "docs/"):
        idx = norm.find(marker)
        if idx >= 0:
            suffix = norm[idx:]
            if suffix.endswith(".md"):
                return True
    return False


def _scannable_rel_path(path_str: str) -> str:
    """正規化為 checker 使用的相對路徑（支援絕對路徑）。"""
    norm = path_str.replace("\\", "/")
    if norm == "HANDOFF.md" or norm.endswith("/HANDOFF.md"):
        return "HANDOFF.md"
    for marker in ("handoffs/", "docs/"):
        idx = norm.find(marker)
        if idx >= 0:
            return norm[idx:]
    return norm


def list_open_pending() -> int:
    """印出未結 pending；供 list-open 子指令。"""
    open_events = load_open_pending()
    for event in open_events:
        print(json.dumps(event, ensure_ascii=False, sort_keys=True))
    return 0 if open_events else 0


def _stdin_operational_unit(unit: Unit, norm_path: str) -> bool:
    """PreToolUse 增量掃描：判斷單位是否落在 operational 區段。"""
    if norm_path == "HANDOFF.md":
        return True
    if norm_path.startswith("docs/") and _is_docs_operational_unit(unit):
        return True
    if unit.section_operational:
        return True
    stripped = unit.text.strip()
    return bool(re.match(r"^(?:STATUS|RESULT)\s*:", stripped))


def check_stdin_operational(source_file: str, content: str) -> list[Violation]:
    """掃描 PreToolUse 增量 operational 文字（僅本次新增/修改行）。"""
    if not content.strip():
        return []
    norm_path = source_file.replace("\\", "/").lstrip("./")
    violations: list[Violation] = []
    open_pending = load_open_pending()
    all_units_claims: list[tuple[Unit, ClaimObject]] = []
    for unit in split_units(content, norm_path):
        if unit.in_fenced or unit.in_quote:
            continue
        if not _stdin_operational_unit(unit, norm_path):
            continue
        _unknown_polarity_warn(unit)
        claim = extract_claim(unit)
        all_units_claims.append((unit, claim))
        violations.extend(check_unit(unit, open_pending))
    violations.extend(check_fingerprint_conflicts(all_units_claims))
    return violations


def _print_violation(v: Violation) -> None:
    """印出違規行；缺 backing 的 operational claim 追加可貼修法提示。"""
    print(f"{v.file}:{v.line}: {v.message}", file=sys.stderr)
    if v.message == "operational claim 缺少 VERIFY/REF/SIGNOFF backing":
        print(
            "  → 建議加 VERIFY:<receipt-id> 或 "
            "VERIFY-EXEMPT:<類別>:<id>（例：VERIFY-EXEMPT:doc-example:phase-b）",
            file=sys.stderr,
        )
    print(v.unit_text, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """CLI 進入點。"""
    parser = argparse.ArgumentParser(description="Verification claim checker (router, not judge).")
    parser.add_argument("--staged", action="store_true", help="Scan git staged markdown files")
    parser.add_argument("--files", nargs="*", default=[], help="Explicit files to scan")
    parser.add_argument("--range", dest="range_spec", default="", help="Git diff range A...B")
    parser.add_argument("--commit-msg", dest="commit_msg", default="", help="Commit message file")
    parser.add_argument(
        "--stdin-operational",
        dest="stdin_operational_file",
        default="",
        help="Scan incremental operational text from stdin for PreToolUse hook",
    )
    parser.add_argument("command", nargs="?", default="", help="Subcommand: list-open")
    args = parser.parse_args(argv)

    if args.command == "list-open":
        return list_open_pending()

    if args.stdin_operational_file:
        try:
            stdin_content = sys.stdin.read()
        except OSError as exc:
            print(f"verification_claim_check.py: stdin read failed: {exc}", file=sys.stderr)
            return 2
        violations = check_stdin_operational(args.stdin_operational_file, stdin_content)
        if violations:
            for v in violations:
                _print_violation(v)
            return 1
        return 0

    paths: list[Path] = []
    staged_content_map: dict[str, str] | None = None
    staged_added_lines_map: dict[str, set[int]] | None = None
    if args.staged:
        try:
            staged_paths, staged_content_map, staged_added_lines_map = _git_staged_markdown_files()
        except FileReadError as exc:
            print(
                f"verification_claim_check.py: cannot read {exc.rel_path}: {exc.detail}",
                file=sys.stderr,
            )
            return 2
        paths.extend(staged_paths)
    if args.range_spec:
        paths.extend(_git_range_files(args.range_spec))
    for file_arg in args.files:
        norm = file_arg.replace("\\", "/")
        if _is_scannable_path(norm):
            paths.append(Path(file_arg))
    if args.commit_msg:
        msg_path = Path(args.commit_msg)
        if msg_path.is_file():
            paths.append(msg_path)
            # commit-msg 以單一 operational 單位掃描
            content = msg_path.read_text(encoding="utf-8")
            unit = Unit(
                text=content,
                source_file="COMMIT_MSG",
                source_line=1,
                section_operational=True,
            )
            open_pending = load_open_pending()
            violations = check_unit(unit, open_pending)
            if violations:
                for v in violations:
                    _print_violation(v)
                return 1
            return 0

    if not paths:
        if args.staged and not args.range_spec and not args.files:
            return 0
        print("verification_claim_check.py: no input files", file=sys.stderr)
        return 2

    # 去重保序
    seen: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)

    content_map = staged_content_map if args.staged else None
    added_lines_map = staged_added_lines_map if args.staged else None
    try:
        violations = check_files(
            unique_paths,
            content_map=content_map,
            added_lines_map=added_lines_map,
        )
    except FileReadError as exc:
        print(
            f"verification_claim_check.py: cannot read {exc.rel_path}: {exc.detail}",
            file=sys.stderr,
        )
        return 2
    if violations:
        for v in violations:
            _print_violation(v)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
