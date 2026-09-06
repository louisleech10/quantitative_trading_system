"""IC 掃描結果立方體（`(k,h) × feature × metric`）之讀寫。

SPEC：`docs/GAP3_SCAN_CUBE_SPEC.md`　TODO：`docs/GAP3_SCAN_CUBE_TODO.md`

## 這個模組在解什麼

使用者原話：「不論IC分析是有幾種參數組合計算出來，不同參數組合計算出來的
每個特徵的每個數據，在前端每個數據表格和圖像，都要能讓使用者能看到分析」。

現況（本票之前）：掃描每格跑完整分析，但**只留一個 `n_events` 摘要，其餘算完就丟**。

## 兩層（R1 P0 之裁決）

- **Tier A**＝`summary_table`（15 欄指標）。實測 **463 B/特徵**。
- **Tier B**＝七個圖表節。實測 **36,808 B/特徵**（是 Tier A 的 **80 倍**）。
  ⇒ 全節保存於 110 格 × 300 特徵 ＝ **1,158 MB**，故 Tier B 有位元組預算，
  超出即整層 fail-closed（Tier A 不受影響）。

實測出處：`handoffs/20260907-probe-report-sections.py`（讀真實報告，rc=0）。

## 🔴 三條不變式（R2 三家獨立命中而立）

1. **逐列/逐節原樣**：`rows[i] == report["summary_table"][i]`、
   `sections[x] == report[x]`。一欄不增不減、不改名、不重算、不重排序。
2. **路徑只在檔案成功提交後才填**：`tier_x.stored is False ⇒ 該層所有路徑為 None`。
   否則會出現「manifest 宣稱有圖、磁碟無檔」。
3. **Tier B 預算看實測累加，不看估計**：`_sample_rolling_series` 依序列長度抽樣，
   跨報告實測 per-feature 為 3,225／19,931／26,637 B（差 8 倍）
   ⇒ 用「第一格外推」會放行超量或誤擋合法帶。

## 解耦

本模組為純函式，**不 import `api/`**（R1）。由 `api/services/ic_analysis_service.py` 呼叫。
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from momentum.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_ROOT = Path("data_cache/ic_scan_cubes")

#: Tier B 收哪些節。**per-feature** 者才收。
#: 🔴 `correlation_matrix` 刻意排除：它是 per-**pair**（O(N²)），且 GAP-6 已登記其無 cap。
CHART_SECTIONS: tuple[str, ...] = (
    "ic_decay",
    "quantile_returns",
    "rolling_ic_series",
    "grouped_ic",
    "turnover_analysis",
    "coverage_analysis",
    "marginal_ic",
)

#: 明確告訴前端「這一節不在瀏覽器內」，不得靜默省略。
EXCLUDED_SECTIONS: tuple[str, ...] = ("correlation_matrix",)

_JSON_KW = dict(ensure_ascii=False, sort_keys=False, separators=(",", ":"))


def _dumps(obj: Any) -> str:
    """序列化。`sort_keys=False` 是為了保留原欄序（golden 逐位元組比對）。"""
    return json.dumps(obj, **_JSON_KW)


def _nbytes(obj: Any) -> int:
    return len(_dumps(obj).encode("utf-8"))


def cell_filename(k: int, h: int, *, tier: str = "a") -> str:
    """Tier A ＝ `cell_k<k>_h<h>.json`；Tier B ＝ `charts_k<k>_h<h>.json`。"""
    prefix = "cell" if tier == "a" else "charts"
    return f"{prefix}_k{int(k)}_h{int(h)}.json"


def _rows_of(cell: dict) -> list:
    """該格之 `summary_table`；不可用之格一律視為 0 列（不寫檔）。"""
    if cell.get("capability") != "available":
        return []
    report = cell.get("report")
    if not isinstance(report, dict):
        return []
    rows = report.get("summary_table")
    return rows if isinstance(rows, list) else []


def _sections_of(cell: dict) -> dict:
    """該格之圖表節**原樣**切片；只取 report 中實際存在者（不發明節）。"""
    report = cell.get("report")
    if not isinstance(report, dict):
        return {}
    return {name: report[name] for name in CHART_SECTIONS if name in report}


def _fits_hint(bytes_per_feature: float, max_bytes: int) -> Optional[dict]:
    """「幾格 × 幾特徵存得下」——由**本次實測**導出，不寫死常數。

    SPEC §C-9：「圖表完整帶」＝ `chart_max_bytes ÷ 實測 per-feature bytes`。
    per-feature bytes 跨報告差 8 倍，寫死一個 `12×300` 就是下一個會過期的值。
    """
    if bytes_per_feature <= 0:
        return None
    total_feature_cells = int(max_bytes // bytes_per_feature)
    return {
        "bytes_per_feature": round(bytes_per_feature, 1),
        "max_feature_cells": total_feature_cells,
        "examples": [
            {"cells": c, "features_per_cell": total_feature_cells // c}
            for c in (1, 12, 110)
            if total_feature_cells // c > 0
        ],
    }


def _prune_locked(root: Path, keep: int) -> list[str]:
    """把既有 task 目錄修剪到 `keep - 1` 個，回傳被刪的 task_id（由舊到新）。

    🔴 修剪到 `keep - 1` 而非 `keep`：本函式在**寫入新 task 之前**呼叫，
    語意是「寫完之後恰為 `keep`」。原設計寫成「> keep 才刪」，
    在恰好 keep 個時不刪、寫完變 keep+1，與驗收條文直接矛盾（`CODEX-R1-P1-06`）。

    🔴 呼叫端須持有 root lock——兩個並行 build 各讀同一快照、各刪一個、各寫一個
    ⇒ 最終 keep+1 個（`CODEX-R2-P1-04`／`GROK-R2-P2-01`）。
    """
    if keep <= 0:
        return []
    entries: list[tuple[str, str]] = []
    for child in root.iterdir():
        if not child.is_dir() or child.name.startswith("."):
            continue
        created = ""
        manifest = child / "manifest.json"
        if manifest.is_file():
            try:
                created = str(json.loads(manifest.read_text(encoding="utf-8")).get("created_at") or "")
            except (OSError, ValueError, json.JSONDecodeError):
                created = ""  # 壞掉的目錄排最舊、優先清掉，且不中止
        entries.append((created, child.name))

    entries.sort()  # created_at 空字串排最前 ⇒ 最舊
    excess = len(entries) - (keep - 1)
    removed: list[str] = []
    for _, name in entries[: max(excess, 0)]:
        try:
            shutil.rmtree(root / name)
            removed.append(name)
        except OSError as exc:
            # 清理失敗不該讓分析失敗
            logger.warning("scan cube prune failed for %s: %s", name, exc)
    return removed


def _publish(tmp: Path, final: Path) -> None:
    """把 temp 目錄提交為正式名。

    🔴 `os.replace` 對**非空**目標目錄在 Darwin 直接失敗
    （`OSError: [Errno 66] Directory not empty`，`CODEX-R2-P1-04` 實測）
    ⇒ 必須先 `rmtree` 掉既有的 final。
    """
    if final.exists():
        shutil.rmtree(final)
    os.replace(tmp, final)


def build_cube(
    task_id: str,
    symbol: Optional[str],
    timeframe: Optional[str],
    cells: list[dict],
    *,
    max_rows: int,
    max_rows_per_cell: int,
    chart_max_bytes: int,
    keep_tasks: int,
    root: Path | str = DEFAULT_ROOT,
) -> dict:
    """寫出立方體並回傳 manifest。

    `cells` 每筆＝`{k, h, capability, reason, n_events, report}`。
    `report` **只在行程內傳遞**，絕不進 HTTP（呼叫端須在本函式回傳後立刻剝除）。
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    rows_per_cell = [len(_rows_of(c)) for c in cells]
    total_rows = sum(rows_per_cell)
    max_cell_rows = max(rows_per_cell) if rows_per_cell else 0

    # ── Tier A 之兩個閘（總列數、單格列數），任一超過即整層不寫 ──────────────
    tier_a: dict[str, Any] = {"stored": True, "truncated": False, "reason": None,
                              "requested_rows": total_rows, "max_rows": max_rows,
                              "max_rows_per_cell": max_rows_per_cell}
    if total_rows > max_rows:
        tier_a.update(stored=False, truncated=True, reason="scan_cube_rows_exceeded")
    elif max_cell_rows > max_rows_per_cell:
        tier_a.update(stored=False, truncated=True,
                      reason="scan_cube_rows_per_cell_exceeded",
                      observed_max_rows_per_cell=max_cell_rows)

    created_at = datetime.now(timezone.utc).isoformat()
    tmp = Path(tempfile.mkdtemp(prefix=f".tmp_{task_id}_", dir=str(root)))
    try:
        cell_entries: list[dict] = []
        # ── Tier A 寫入 ──────────────────────────────────────────────────
        written_a: dict[tuple[int, int], str] = {}
        if tier_a["stored"]:
            for cell, n in zip(cells, rows_per_cell):
                if cell.get("capability") != "available":
                    continue  # 🔴 不可用之格不寫檔（不得用空 rows 冒充有資料）
                name = cell_filename(cell["k"], cell["h"], tier="a")
                payload = {
                    "k": int(cell["k"]), "h": int(cell["h"]),
                    "analysis_status": (cell.get("report") or {}).get("analysis_status"),
                    "oos_guarantees": (cell.get("report") or {}).get("oos_guarantees"),
                    "n_events": cell.get("n_events"),
                    "rows": _rows_of(cell),   # 🔴 原樣，不排序不裁欄
                }
                (tmp / name).write_text(_dumps(payload), encoding="utf-8")
                written_a[(int(cell["k"]), int(cell["h"]))] = name

        # ── Tier B：估計只作預檢，判定看**實測累加** ─────────────────────────
        tier_b, written_b = _write_tier_b(
            tmp, cells, rows_per_cell, total_rows, chart_max_bytes,
        )

        metrics = _metrics_axis(cells, rows_per_cell)
        chart_sections = _chart_sections_axis(cells, rows_per_cell)

        for cell, n in zip(cells, rows_per_cell):
            key = (int(cell["k"]), int(cell["h"]))
            cell_entries.append({
                "k": key[0], "h": key[1],
                "capability": cell.get("capability"),
                "reason": cell.get("reason"),
                "n_events": cell.get("n_events"),
                "rows": n,
                # 🔴 路徑**只在該檔已成功提交後**才填；未存之層一律 None
                "path": written_a.get(key),
                "chart_path": written_b.get(key),
            })

        manifest = {
            "task_id": task_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "created_at": created_at,
            "k_axis": sorted({int(c["k"]) for c in cells}),
            "h_axis": sorted({int(c["h"]) for c in cells}),
            "metrics": metrics,
            "chart_sections": chart_sections,
            "excluded_sections": list(EXCLUDED_SECTIONS),
            "tier_a": tier_a,
            "tier_b": tier_b,
            "cells": cell_entries,
        }
        (tmp / "manifest.json").write_text(_dumps(manifest), encoding="utf-8")

        # ── prune + publish 在同一把 root lock 內 ────────────────────────
        lock_path = root / ".lock"
        with open(lock_path, "a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                _prune_locked(root, keep_tasks)
                _publish(tmp, root / task_id)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        tmp = None  # type: ignore[assignment]  已被 replace 掉
        return manifest
    finally:
        if tmp is not None and Path(tmp).exists():
            shutil.rmtree(tmp, ignore_errors=True)


def _write_tier_b(
    tmp: Path,
    cells: list[dict],
    rows_per_cell: list[int],
    total_rows: int,
    chart_max_bytes: int,
) -> tuple[dict, dict[tuple[int, int], str]]:
    """逐格序列化、逐格累加**真正的 bytes**；超限即刪掉已寫的、整層不存。

    🔴 為什麼不用「第一格外推」（`COMPOSER-R2-P1-02`／`GROK-R2-P1-02`／`CODEX-R2-P1-01`）：
    `_sample_rolling_series` 依序列長度抽樣，跨真實報告實測 per-feature 為
    **3,225／19,931／26,637 B**（差 8 倍）。首格偏小 ⇒ 放行超量落盤；偏大 ⇒ 誤擋合法帶。

    🔴 RAM 上界＝**一格**：逐格 dump 逐格寫，不把全部格同時序列化（那是 1,158 MB 級）。
    """
    written: dict[tuple[int, int], str] = {}
    observed = 0
    observed_features = 0

    for cell, n in zip(cells, rows_per_cell):
        if not n:
            continue
        sections = _sections_of(cell)
        if not sections:
            continue
        payload = _dumps({"k": int(cell["k"]), "h": int(cell["h"]), "sections": sections})
        size = len(payload.encode("utf-8"))
        if observed + size > chart_max_bytes:
            # 一格都不留（禁止部分保存）
            for name in written.values():
                (tmp / name).unlink(missing_ok=True)
            per_feat = (observed + size) / max(observed_features + n, 1)
            return ({
                "stored": False, "truncated": True,
                "reason": "scan_cube_chart_bytes_exceeded",
                "max_bytes": chart_max_bytes,
                # 🔴 已知「至少超過」，不謊報一個精確的 requested_bytes
                "observed_bytes_at_stop": observed + size,
                "chart_bytes_observed_per_feature": round(per_feat, 1),
                "fits_hint": _fits_hint(per_feat, chart_max_bytes),
            }, {})
        name = cell_filename(cell["k"], cell["h"], tier="b")
        (tmp / name).write_text(payload, encoding="utf-8")
        written[(int(cell["k"]), int(cell["h"]))] = name
        observed += size
        observed_features += n

    per_feat = observed / observed_features if observed_features else 0.0
    return ({
        "stored": True, "truncated": False, "reason": None,
        "max_bytes": chart_max_bytes,
        "observed_bytes": observed,
        "chart_bytes_observed_per_feature": round(per_feat, 1),
        "fits_hint": _fits_hint(per_feat, chart_max_bytes),
    }, written)


def _metrics_axis(cells: list[dict], rows_per_cell: list[int]) -> list[str]:
    """指標軸＝第一個非空格之欄集減去 `feature_name`；全空 ⇒ `[]`（不發明欄名）。"""
    for cell, n in zip(cells, rows_per_cell):
        if n:
            first = _rows_of(cell)[0]
            if isinstance(first, dict):
                return [k for k in first.keys() if k != "feature_name"]
    return []


def _chart_sections_axis(cells: list[dict], rows_per_cell: list[int]) -> list[str]:
    """圖表節軸＝第一個非空格之 report 中**實際存在**的節（不列不存在者）。"""
    for cell, n in zip(cells, rows_per_cell):
        if n:
            sections = _sections_of(cell)
            if sections:
                return list(sections.keys())
    return []


# ══════════════════════════════════════════════════════════════════════════
# 讀取
# ══════════════════════════════════════════════════════════════════════════


class CubeNotFound(Exception):
    """找不到該 task 的立方體。**與「查詢結果為空」不同**，故用不同型別。"""


class CubeTierNotStored(Exception):
    """該層 fail-closed 未保存。帶 manifest 之 tier 資訊供路由回 409。"""

    def __init__(self, tier: str, info: dict):
        super().__init__(f"tier {tier} not stored: {info.get('reason')}")
        self.tier = tier
        self.info = info


def load_manifest(root: Path | str, task_id: str) -> dict:
    path = Path(root) / task_id / "manifest.json"
    if not path.is_file():
        raise CubeNotFound(f"scan cube not found: {task_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _sort_key_factory(field: str, descending: bool):
    """排序鍵：`None` 一律排末尾（升冪降冪皆然）——「沒有值」不是「最小值」。"""

    def key(row: dict):
        value = row.get(field)
        missing = value is None
        if missing:
            return (1, 0)
        # descending 時把值取負以維持 `sorted(reverse=False)` 之穩定 tie-break
        try:
            numeric = -float(value) if descending else float(value)
            return (0, numeric)
        except (TypeError, ValueError):
            return (0, 0)

    return key


def query_cube(
    root: Path | str,
    task_id: str,
    *,
    k: Optional[Iterable[int]] = None,
    h: Optional[Iterable[int]] = None,
    feature: Optional[str] = None,
    metrics: Optional[list[str]] = None,
    sort: Optional[tuple[str, str]] = None,
    offset: int = 0,
    limit: int = 100,
) -> dict:
    """Tier A 之分頁查詢。`total` 是**篩選後的真實總數**，不是本頁筆數。"""
    root = Path(root)
    manifest = load_manifest(root, task_id)
    tier_a = manifest.get("tier_a") or {}
    if not tier_a.get("stored"):
        raise CubeTierNotStored("a", tier_a)

    k_set = {int(x) for x in k} if k else None
    h_set = {int(x) for x in h} if h else None
    needle = feature.lower() if feature else None

    rows: list[dict] = []
    for entry in manifest.get("cells") or []:
        if not entry.get("path"):
            continue
        if k_set is not None and int(entry["k"]) not in k_set:
            continue
        if h_set is not None and int(entry["h"]) not in h_set:
            continue
        cell_path = root / task_id / entry["path"]
        if not cell_path.is_file():
            continue
        payload = json.loads(cell_path.read_text(encoding="utf-8"))
        for row in payload.get("rows") or []:
            name = str(row.get("feature_name") or "")
            if needle and needle not in name.lower():
                continue
            out = {"k": payload["k"], "h": payload["h"], "feature_name": name}
            if metrics:
                out.update({m: row.get(m) for m in metrics})
            else:
                out.update({key: value for key, value in row.items() if key != "feature_name"})
            rows.append(out)

    # 🔴 tie-breaker 固定為 (k, h, feature_name)，否則跨頁會重複／漏
    rows.sort(key=lambda r: (r["k"], r["h"], r["feature_name"]))
    if sort:
        field, direction = sort
        rows.sort(key=_sort_key_factory(field, direction == "desc"))

    total = len(rows)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": rows[offset: offset + limit],
    }


def load_charts(root: Path | str, task_id: str, k: int, h: int, feature: str) -> dict:
    """Tier B 之單格單特徵切片。

    回傳**與主分析 report 同形狀**之切片，讓前端既有圖表元件可直接吃：
    `{"ic_decay": {<feature>: …}, "grouped_ic": {<group>: {<feature>: …}}, …}`
    ——`grouped_ic` 是巢狀 map，不是扁平單 feature 物件（`COMPOSER-R2-P2-01`）。
    節本身可能是 `{status, reason}` 形狀（`SectionStatusObject`）⇒ **原樣**傳遞。
    """
    root = Path(root)
    manifest = load_manifest(root, task_id)
    tier_b = manifest.get("tier_b") or {}
    if not tier_b.get("stored"):
        raise CubeTierNotStored("b", tier_b)

    entry = next(
        (c for c in manifest.get("cells") or []
         if int(c["k"]) == int(k) and int(c["h"]) == int(h)),
        None,
    )
    if entry is None or not entry.get("chart_path"):
        raise CubeNotFound(f"cell not found or charts not stored: k={k} h={h}")
    path = root / task_id / entry["chart_path"]
    if not path.is_file():
        raise CubeNotFound(f"chart file missing: {entry['chart_path']}")

    sections = json.loads(path.read_text(encoding="utf-8")).get("sections") or {}
    sliced: dict[str, Any] = {}
    for name, section in sections.items():
        sliced[name] = _slice_section(name, section, feature)
    return {"k": int(k), "h": int(h), "feature_name": feature, "sections": sliced}


def _slice_section(name: str, section: Any, feature: str) -> Any:
    """取單特徵切片，但**保留原形狀**。

    - `grouped_ic` 之形狀是 `{group: {feature: …}}` ⇒ 逐 group 取該 feature。
    - 其餘 per-feature 節是 `{feature: …}` ⇒ 直接取。
    - `{status, reason}` 之 section status object ⇒ 原樣回傳（前端沿用 `sectionSplit`）。
    """
    if not isinstance(section, dict):
        return section
    if "status" in section and "reason" in section:
        return section
    if name == "grouped_ic":
        return {
            group: {feature: members[feature]}
            for group, members in section.items()
            if isinstance(members, dict) and feature in members
        }
    return {feature: section[feature]} if feature in section else {}
