"""IC artifact Parquet writer and streaming reader."""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from momentum.core.contracts import ICArtifactSchema, ICResult
from momentum.core.logging import get_logger

logger = get_logger(__name__)

SCHEMA_VERSION = 1
ARTIFACT_COLUMNS = [
    "feature_name",
    "horizon",
    "ic_mean",
    "ic_std",
    "icir",
    "p_value",
    "ic_hit_rate",
    "eval_status",
    "selection_scope_id",
    "schema_version",
]

ARROW_SCHEMA = pa.schema(
    [
        pa.field("feature_name", pa.string(), nullable=False),
        pa.field("horizon", pa.int64(), nullable=False),
        pa.field("ic_mean", pa.float64(), nullable=True),
        pa.field("ic_std", pa.float64(), nullable=True),
        pa.field("icir", pa.float64(), nullable=True),
        pa.field("p_value", pa.float64(), nullable=True),
        pa.field("ic_hit_rate", pa.float64(), nullable=True),
        pa.field("eval_status", pa.string(), nullable=False),
        pa.field("selection_scope_id", pa.string(), nullable=False),
        pa.field("schema_version", pa.int64(), nullable=False),
    ],
    metadata={b"schema_version": str(SCHEMA_VERSION).encode("ascii")},
)


def build_ic_artifact_rows(
    results: Iterable[ICResult],
    default_horizon: int,
    selection_scope_id: str,
) -> list[ICArtifactSchema]:
    """將單 horizon ICResult 映射成 artifact long-layout rows。"""
    return [
        ICArtifactSchema(
            feature_name=result.feature_name,
            horizon=int(default_horizon),
            ic_mean=float(result.ic_mean),
            ic_std=float(result.ic_std),
            icir=float(result.icir),
            p_value=float(result.p_value),
            ic_hit_rate=float(result.ic_hit_rate),
            eval_status=str(result.eval_status.value),
            selection_scope_id=selection_scope_id,
            schema_version=SCHEMA_VERSION,
        )
        for result in results
    ]


def write(rows: Iterable[ICArtifactSchema | dict[str, Any]], path: str | Path) -> None:
    """以 atomic temp+replace 寫出 IC artifact Parquet。"""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    row_dicts = [_row_to_dict(row) for row in rows]
    table = _table_from_rows(row_dicts)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        pq.write_table(table, temp_path, compression="zstd")
        os.replace(temp_path, destination)
        logger.info("IC artifact written: path=%s rows=%s", destination, table.num_rows)
    except BaseException:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise


def read(
    path: str | Path,
    filters: Optional[Any] = None,
    columns: Optional[Sequence[str]] = None,
    page: Optional[int | dict[str, int]] = None,
) -> list[dict[str, Any]]:
    """用 pyarrow dataset scanner 分批讀取 artifact，支援 predicate pushdown。"""
    dataset = ds.dataset(str(path), format="parquet")
    expression = _normalize_filters(filters)
    limit = _page_limit(page)
    offset = _page_offset(page)
    scanner = dataset.scanner(
        columns=list(columns) if columns is not None else None,
        filter=expression,
        batch_size=limit or 8192,
    )

    rows: list[dict[str, Any]] = []
    skipped = 0
    for batch in scanner.to_batches():
        batch_rows = batch.to_pylist()
        if offset and skipped < offset:
            remaining_skip = offset - skipped
            if remaining_skip >= len(batch_rows):
                skipped += len(batch_rows)
                continue
            batch_rows = batch_rows[remaining_skip:]
            skipped = offset
        if limit is None:
            rows.extend(batch_rows)
            continue
        remaining = limit - len(rows)
        if remaining <= 0:
            break
        rows.extend(batch_rows[:remaining])
        if len(rows) >= limit:
            break
    return rows


class ICArtifactWriter:
    """Factory-friendly wrapper around module-level IC artifact functions."""

    def build_ic_artifact_rows(
        self,
        results: Iterable[ICResult],
        default_horizon: int,
        selection_scope_id: str,
    ) -> list[ICArtifactSchema]:
        """建立 artifact rows。"""
        return build_ic_artifact_rows(results, default_horizon, selection_scope_id)

    def write(self, rows: Iterable[ICArtifactSchema | dict[str, Any]], path: str | Path) -> None:
        """寫出 artifact。"""
        write(rows, path)

    def read(
        self,
        path: str | Path,
        filters: Optional[Any] = None,
        columns: Optional[Sequence[str]] = None,
        page: Optional[int | dict[str, int]] = None,
    ) -> list[dict[str, Any]]:
        """讀取 artifact。"""
        return read(path, filters=filters, columns=columns, page=page)


def _row_to_dict(row: ICArtifactSchema | dict[str, Any]) -> dict[str, Any]:
    """正規化 dataclass/dict row 並限制欄位順序。"""
    raw = asdict(row) if is_dataclass(row) else dict(row)
    return {column: raw[column] for column in ARTIFACT_COLUMNS}


def _table_from_rows(rows: list[dict[str, Any]]) -> pa.Table:
    """用固定 Arrow schema 建立 table，空 rows 仍保留 schema。"""
    columns = {
        column: [row[column] for row in rows]
        for column in ARTIFACT_COLUMNS
    }
    return pa.Table.from_pydict(columns, schema=ARROW_SCHEMA)


def _normalize_filters(filters: Optional[Any]) -> Optional[ds.Expression]:
    """將 tuple filter 正規化為 pyarrow dataset expression。"""
    if filters is None:
        return None
    if isinstance(filters, ds.Expression):
        return filters
    expressions: list[ds.Expression] = []
    for column, op, value in filters:
        field = ds.field(column)
        if op in {"=", "=="}:
            expressions.append(field == value)
        elif op == "!=":
            expressions.append(field != value)
        elif op == "<":
            expressions.append(field < value)
        elif op == "<=":
            expressions.append(field <= value)
        elif op == ">":
            expressions.append(field > value)
        elif op == ">=":
            expressions.append(field >= value)
        elif op == "in":
            expressions.append(field.isin(value))
        else:
            raise ValueError(f"Unsupported filter operator: {op}")
    if not expressions:
        return None
    expression = expressions[0]
    for next_expression in expressions[1:]:
        expression = expression & next_expression
    return expression


def _page_limit(page: Optional[int | dict[str, int]]) -> Optional[int]:
    """解析 page limit；None 表示讀完整個 filtered result。"""
    if page is None:
        return None
    if isinstance(page, int):
        if page <= 0:
            raise ValueError("page must be positive")
        return page
    limit = int(page.get("limit", page.get("page_size", 0)))
    if limit <= 0:
        raise ValueError("page limit must be positive")
    return limit


def _page_offset(page: Optional[int | dict[str, int]]) -> int:
    """解析 page offset。"""
    if page is None or isinstance(page, int):
        return 0
    offset = int(page.get("offset", 0))
    if offset < 0:
        raise ValueError("page offset must be non-negative")
    return offset
