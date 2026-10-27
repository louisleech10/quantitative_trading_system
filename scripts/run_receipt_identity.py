"""NOCAP Task 0.3b／0.3c／0.4（docs/NOCAP_SPEC.md）：成長曲線、估時、四項平衡三種收據之共用身分 `identity`——
比對欄 `match`（下指令當下重算、逐欄相等才可沿用）與紀錄欄 `meta`（producer、created_at，不參與比對）。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
MATCH_KEYS = ("entrypoint", "target_argv", "code_sha256", "data", "config_sha256", "hardware")
META_KEYS = ("producer", "created_at")
#: 輸入檔 sha256 之快取（鍵＝絕對路徑、size、mtime_ns；大檔不必每次重讀）；不進版控
DATA_CACHE = REPO / ".claude" / "tmp" / "receipt_data_sha256.json"  # .claude/tmp/ 已列 .gitignore
_BUDGET_HEADING = "## §B 驗證運算預算"


def _rel(path: str, repo: Path) -> str:
    """repo 內之絕對路徑轉相對路徑；其餘原樣。"""
    try:
        return str(Path(path).resolve().relative_to(repo.resolve())) if os.path.isabs(path) else path
    except ValueError:
        return path


def normalize_argv(argv: Sequence[str], repo: Path = REPO) -> str:
    """以 `shlex.join` 正規化；repo 內絕對路徑轉相對路徑。"""
    return shlex.join([_rel(str(a), repo) for a in argv])


def _blob_sha1(data: bytes) -> str:
    """與 `git hash-object`（無 filter）相同之 blob 雜湊。"""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def code_sha256(paths: Sequence[str], repo: Path = REPO) -> str:
    """各檔**工作樹實際內容**之 `git hash-object` 依路徑排序串接後之 sha256（含未提交改動）；檔不存在記 `missing`。"""
    parts = []
    for rel in sorted({_rel(p, repo) for p in paths}):
        f = repo / rel
        parts.append(f"{rel}:{_blob_sha1(f.read_bytes()) if f.is_file() else 'missing'}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_identity(paths: Sequence[str], repo: Path = REPO, cache_path: Optional[Path] = None) -> list:
    """每個輸入檔 {path, size, sha256}；sha256 以 (path, size, mtime_ns) 快取。檔不存在 ⇒ size −1、sha256 `missing`。"""
    cache_file = cache_path or (DATA_CACHE if repo == REPO else repo / ".receipt_data_sha256.json")
    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache = {}
    out, dirty = [], False
    for rel in sorted({_rel(p, repo) for p in paths}):
        f = repo / rel
        if not f.is_file():
            out.append({"path": rel, "size": -1, "sha256": "missing"})
            continue
        st = f.stat()
        key = f"{f.resolve()}|{st.st_size}|{st.st_mtime_ns}"
        if key not in cache:
            cache[key], dirty = _file_sha256(f), True
        out.append({"path": rel, "size": st.st_size, "sha256": cache[key]})
    if dirty:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=0, sort_keys=True), encoding="utf-8")
    return out


def _cpu_model() -> str:
    if platform.system() == "Darwin":
        r = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def hardware() -> Dict[str, Any]:
    """CPU 型號、核數、RAM、OS（三種收據皆為耗時／記憶體量測，硬體不同即不可沿用）。"""
    try:
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        ram = None
    return {"cpu": _cpu_model(), "cores": os.cpu_count(), "ram_bytes": ram,
            "os": f"{platform.system()} {platform.release()}"}


def compute_match(entrypoint: str, target_argv: Sequence[str], code_paths: Sequence[str], data_paths: Sequence[str],
                  config_paths: Sequence[str], repo: Path = REPO) -> Dict[str, Any]:
    """下指令當下之 `match`（鍵恰為 `MATCH_KEYS`）。`code_paths` 恆含 `entrypoint`（若為檔）。"""
    entry = _rel(entrypoint, repo)
    codes = list(code_paths) + ([entry] if (repo / entry).is_file() else [])
    return {"entrypoint": entry, "target_argv": normalize_argv(target_argv, repo),
            "code_sha256": code_sha256(codes, repo), "data": data_identity(data_paths, repo),
            "config_sha256": code_sha256(config_paths, repo), "hardware": hardware()}


def make_identity(match: Mapping[str, Any], producer: str) -> Dict[str, Any]:
    return {"match": dict(match), "meta": {"producer": producer,
                                          "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}}


def receipt_matches(receipt: Mapping[str, Any], current_match: Mapping[str, Any]) -> bool:
    """收據 `identity.match` 與當下 `match` 逐欄相等；`identity.meta` 不比對。"""
    match = ((receipt or {}).get("identity") or {}).get("match")
    if not isinstance(match, Mapping):
        return False
    return all(k in match and k in current_match and match[k] == current_match[k] for k in MATCH_KEYS)


def budget_ids(spec_text: str) -> List[str]:
    """SPEC `## §B 驗證運算預算` 表之列 id（首欄；表頭與分隔列除外）。"""
    ids = []
    for line in (_section(spec_text, _BUDGET_HEADING) or "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if cells and cells[0] and cells[0] != "id" and not set(cells[0]) <= set("-: "):
            ids.append(cells[0])
    return ids


def coverage_ids_valid(estimate_receipt: Mapping[str, Any], spec_text: str) -> bool:
    """估時收據之 `coverage_path_ids` 皆為該 SPEC `## §B` 預算表某列之 id（Task 0.3c）；空串列 ⇒ 無效。"""
    ids = (estimate_receipt or {}).get("coverage_path_ids")
    valid = set(budget_ids(spec_text))
    return isinstance(ids, list) and bool(ids) and all(i in valid for i in ids)


def _nonneg(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0


def estimate_receipt_problems(receipt: Mapping[str, Any], repo: Path = REPO) -> List[str]:
    """Task 0.3c 估時收據必填欄（SPEC：identity、scale、estimate_seconds、basis、spec_path、coverage_path_ids）。"""
    out = []
    if not isinstance(((receipt.get("identity") or {}).get("match")), Mapping):
        out.append("缺 identity.match")
    if receipt.get("scale") in (None, ""):
        out.append("缺 scale")
    if not _nonneg(receipt.get("estimate_seconds")):
        out.append("estimate_seconds 須為有限非負數")
    if not isinstance(receipt.get("basis"), list):
        out.append("basis 須為串列（所依之成長曲線或前次實跑收據路徑）")
    if not (repo / str(receipt.get("spec_path") or "")).is_file() or not receipt.get("spec_path"):
        out.append("spec_path 不存在")
    if not isinstance(receipt.get("coverage_path_ids"), list) or not receipt.get("coverage_path_ids"):
        out.append("coverage_path_ids 須為非空串列")
    return out


def scale_receipt_problems(receipt: Mapping[str, Any]) -> List[str]:
    """Task 0.3b 成長曲線收據必填欄（SPEC：≥ 3 相異規模點各含 scale／unit／seconds／peak_rss_bytes；fit 含 model／exponent／
    r2；projection 含 scale／seconds／peak_rss_bytes；未標 extrapolation_unreliable）。"""
    out = []
    pts = receipt.get("points")
    if not isinstance(pts, list) or len(pts) < 3:
        out.append("points 須 ≥ 3 個")
        pts = pts if isinstance(pts, list) else []
    for i, p in enumerate(pts):
        if not isinstance(p, Mapping) or not all(_nonneg(p.get(k)) for k in ("scale", "seconds", "peak_rss_bytes")) \
                or not p.get("unit"):
            out.append(f"points[{i}] 須含 scale／unit／seconds／peak_rss_bytes（有限非負）")
    if len({p.get("scale") for p in pts if isinstance(p, Mapping)}) < 3:
        out.append("規模點須 ≥ 3 個相異值")
    fit = receipt.get("fit") or {}
    if not (isinstance(fit, Mapping) and fit.get("model") and isinstance(fit.get("exponent"), (int, float))
            and isinstance(fit.get("r2"), (int, float))):
        out.append("fit 須含 model／exponent／r2")
    proj = receipt.get("projection") or {}
    if not (isinstance(proj, Mapping) and all(_nonneg(proj.get(k)) for k in ("scale", "seconds", "peak_rss_bytes"))):
        out.append("projection 須含 scale／seconds／peak_rss_bytes（有限非負）")
    if receipt.get("extrapolation_unreliable") is not False:
        out.append("extrapolation_unreliable 須明確為 false")
    return out


#: 成長曲線收據與全規模命令之身分比對欄（規模點之 argv 與全規模命令不同，故不比 target_argv）
SCALE_MATCH_KEYS = tuple(k for k in MATCH_KEYS if k != "target_argv")


BALANCE_HEADING = "## §B 四項平衡實測"
BUDGET_LIMIT_SECONDS = 2 * 3600
_UNIT_SECONDS = {"秒": 1, "s": 1, "分鐘": 60, "分": 60, "min": 60, "小時": 3600, "h": 3600}
_DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*(?:[–\-~～]\s*(\d+(?:\.\d+)?)\s*)?(小時|分鐘|分|秒|min|h|s)(?![A-Za-z])")


def _section(spec_text: str, heading: str) -> Optional[str]:
    """行首標題 `heading` 至下一個 `## ` 標題之內文（內文中引用該標題字樣者不算）；無 ⇒ None。"""
    m = re.search(rf"^{re.escape(heading)}[ \t]*$", spec_text, re.M)
    if not m:
        return None
    body = spec_text[m.end():]
    end = re.search(r"^## ", body, re.M)
    return body[:end.start()] if end else body


def budget_total_seconds(spec_text: str) -> float:
    """§B 預算表「估時」欄逐列取最大之時長（區間取上界）後加總；無表 ⇒ 0。"""
    body = _section(spec_text, _BUDGET_HEADING) or ""
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in body.splitlines() if ln.startswith("|")]
    if not rows:
        return 0.0
    col = next((i for i, c in enumerate(rows[0]) if c.startswith("估時")), None)
    total = 0.0
    for cells in rows[1:]:
        if col is None or col >= len(cells) or set(cells[0]) <= set("-: "):
            continue
        vals = [float(m.group(2) or m.group(1)) * _UNIT_SECONDS[m.group(3)] for m in _DURATION.finditer(cells[col])]
        total += max(vals) if vals else 0.0
    return total


def spec_budget_problems(spec_text: str) -> List[str]:
    """Task 0.3c／0.4 之 SPEC 必填（`template_check.sh spec` 呼叫；既有凍結 SPEC 不溯及，由呼叫端以清單豁免）：
    `## §B 驗證運算預算` 表至少一列、`## §B 四項平衡實測` 節存在；預算合計逾 2 小時須附「不降驗證之省法」與
    「小規模驗不到」之理由。"""
    problems = []
    if not budget_ids(spec_text):
        problems.append(f"缺 `{_BUDGET_HEADING}` 表（每個重型跑一列：id、獨有覆蓋路徑、規模、估時與依據、沿用來源）")
    if _section(spec_text, BALANCE_HEADING) is None:
        problems.append(f"缺 `{BALANCE_HEADING}` 節（耗時、峰值 RSS、精度差、檔案大小；不涉計算者標 N/A 附理由）")
    total = budget_total_seconds(spec_text)
    body = _section(spec_text, _BUDGET_HEADING) or ""
    if total > BUDGET_LIMIT_SECONDS and not ("不降驗證之省法" in body and "小規模驗不到" in body):
        problems.append(f"§B 預算合計約 {total / 3600:.1f} 小時 > 2 小時，須附「不降驗證之省法」與「小規模驗不到」之理由")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != "spec-budget":
        print("用法：python3 scripts/run_receipt_identity.py spec-budget <SPEC 檔>", file=sys.stderr)
        return 2
    problems = spec_budget_problems(Path(args[1]).read_text(encoding="utf-8"))
    for p in problems:
        print(f"  · {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
