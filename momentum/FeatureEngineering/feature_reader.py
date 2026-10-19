"""FeatureReader — 讀取 V2 版面（`<base>/<symbol>/<timeframe>/<config_hash>/feature_manifest.json`）之唯讀介面。

讀取模式（皆以 V2 manifest 為準；V2 manifest 不存在 ⇒ FileNotFoundError，不退回舊版面）：
  1. Metadata-Only（`load_manifest_v2`／`list_features_v2`，零資料 I/O）
  2. Column-Projected（`load_columns_v2`，只讀所需欄）
  3. Per-Group Streaming（`stream_groups_v2`，逐組產出以限記憶體）
  4. 逐欄執行紀錄（`load_provenance_v2`，FFDSTAR Task 1.5；只讀紀錄檔並驗 sha256，不讀特徵檔）

Design reference: FEATURE_STORAGE_ARCHITECTURE_V7.md §11
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from momentum.FeatureEngineering import feature_naming
from momentum.FeatureEngineering.consumer_gate import (
    ConsumerPolicy,
    assert_consumer_run_status,
)
from momentum.FeatureEngineering.feature_storage import (
    GAUSSIAN_INT16_ENCODING,
    L7_ENCODING_REGISTRY_METADATA_KEY,
    RANK_UINT16_ENCODING,
    ZSCORE_INT16_ENCODING,
    decode_rank_from_uint16,
    decode_zscore_from_int16,
    resolve_run_status as merge_manifest_run_status,
)
from momentum.core.icfirstalign_errors import RowIndexArtifactMissingError, RowIndexLengthMismatchError
from momentum.core.logging import get_logger

logger = get_logger(__name__)

V2_MANIFEST_NAME = "feature_manifest.json"


class NonCanonicalFeaturePathError(ValueError):
    """特徵檔路徑無法解析為 canonical run（FF-NAME Task 3.4）：於產生任何 DataFrame 之前拒收。"""


@dataclass(frozen=True)
class CanonicalRun:
    """canonical run＝特徵根下 `<symbol>/<timeframe>/<config_hash>/` 且 registry 有對應條目（SPEC v13 Task 3.4）。"""

    feature_root: Path
    symbol: str
    timeframe: str
    config_hash: str

    @property
    def run_dir(self) -> Path:
        return self.feature_root / self.symbol / self.timeframe / self.config_hash

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / V2_MANIFEST_NAME


def resolve_canonical_run(
    path: Any,
    *,
    feature_root: Any,
    registry_get: Callable[[str, str, str], Optional[Mapping[str, Any]]],
) -> CanonicalRun:
    """特徵檔路徑 → `CanonicalRun`；只接受 run 目錄或其 `feature_manifest.json`，且須位於 `feature_root` 下恰三層
    （symbol／timeframe／config_hash）並於 registry 有條目；否則 `NonCanonicalFeaturePathError`。
    純路徑判定：不開啟任何特徵檔（任意 `.parquet`／`.h5` 一律拒收，無退路）。"""
    if path is None or not str(path).strip():
        raise NonCanonicalFeaturePathError("特徵路徑為空，無法解析為 canonical run")
    candidate = Path(str(path)).expanduser()
    if candidate.name == V2_MANIFEST_NAME:
        run_dir = candidate.parent
    elif candidate.is_dir():
        run_dir = candidate
    else:
        raise NonCanonicalFeaturePathError(
            f"特徵路徑 {candidate} 非 canonical run（只接受 <symbol>/<timeframe>/<config_hash>/ 或其 "
            f"{V2_MANIFEST_NAME}；任意 .parquet／.h5 不接受）")
    root = Path(str(feature_root)).expanduser().resolve()
    try:
        relative = run_dir.resolve().relative_to(root)
    except ValueError:
        raise NonCanonicalFeaturePathError(f"特徵路徑 {candidate} 不在特徵根 {root} 下") from None
    if len(relative.parts) != 3:
        raise NonCanonicalFeaturePathError(
            f"特徵路徑 {candidate} 相對特徵根之層數 {len(relative.parts)} ≠ 3（<symbol>/<timeframe>/<config_hash>）")
    symbol, timeframe, config_hash = relative.parts
    if registry_get(symbol, timeframe, config_hash) is None:
        raise NonCanonicalFeaturePathError(
            f"特徵路徑 {candidate} 之 ({symbol}, {timeframe}, {config_hash}) 於 registry 無條目，非 canonical run")
    return CanonicalRun(feature_root=root, symbol=symbol, timeframe=timeframe, config_hash=config_hash)


class FeatureRunView:
    """單一 run 之已驗證 manifest 與其群組 parquet 之讀取（FF-NAME Task 3.4）。

    只能由 `FeatureReader.open_run_v2` 建立（manifest 已過命名世代閘）；瀏覽端以此讀群組之欄、footer 與 schema，
    不另開任何 run 內檔案。路徑只接受本 run manifest 所列之群組檔與時間軸 sidecar。"""

    def __init__(self, manifest: dict, run_dir: Path) -> None:
        self.manifest = manifest
        self.run_dir = Path(run_dir)
        self._allowed: set = set()
        row_indexes = [manifest.get("row_index")]
        for artifact in (manifest.get("artifacts") or {}).values():
            if not isinstance(artifact, dict):
                continue
            row_indexes.append(artifact.get("row_index"))
            for info in (artifact.get("groups") or {}).values():
                if isinstance(info, dict) and (info.get("path") or info.get("file")):
                    resolved = FeatureReader._resolve_manifest_relative_path(self.run_dir, info.get("path") or info.get("file"))
                    self._allowed.add(resolved)
        for row_index in row_indexes:  # 時間軸 sidecar（raw 根軸與 processed 自身軸）亦屬本 run 之檔
            if isinstance(row_index, dict) and row_index.get("path"):
                self._allowed.add(FeatureReader._resolve_manifest_relative_path(self.run_dir, row_index.get("path")))

    def group_path(self, relative: Optional[str]) -> Path:
        """manifest 群組之相對路徑 → run 內絕對路徑（不安全路徑 ⇒ ValueError）。"""
        return FeatureReader._resolve_manifest_relative_path(self.run_dir, relative)

    def _require_member(self, path: Any) -> Path:
        resolved = Path(str(path))
        if resolved not in self._allowed:
            raise ValueError(f"{resolved} 非本 run（{self.run_dir}）manifest 所列之群組檔")
        return resolved

    def read_table(self, path: Any, columns: Optional[List[str]] = None) -> pa.Table:
        """讀群組 parquet（可選欄），L7 編碼解碼同 `load_columns_v2`。"""
        member = self._require_member(path)
        return FeatureReader._decode_l7_encoded_table(pq.read_table(str(member), columns=columns))

    def read_footer(self, path: Any) -> Tuple[pa.Schema, Any]:
        """群組 parquet 之 (arrow schema, FileMetaData)（只讀 footer，不解碼資料）。"""
        handle = pq.ParquetFile(str(self._require_member(path)))
        return handle.schema_arrow, handle.metadata

    def read_metadata(self, path: Any) -> Any:
        """群組 parquet 之 FileMetaData（含 key-value metadata）。"""
        return pq.read_metadata(str(self._require_member(path)))


class FeatureReader:
    """V7 unified feature read interface — Parquet-only, no HDF5."""

    V2_MANIFEST_NAME = "feature_manifest.json"

    def __init__(self, feature_base_path: str = "data_cache/features") -> None:
        self._base = Path(feature_base_path)

    def feature_run_dir(self, symbol: str, tf: str, config_hash: str) -> Path:
        """Return the canonical V2 run directory for one symbol/timeframe/config."""
        safe_symbol = self._safe_path_segment(symbol, "symbol")
        safe_tf = self._safe_path_segment(tf, "tf")
        safe_config_hash = self._safe_path_segment(config_hash, "config_hash")
        return self._base / safe_symbol / safe_tf / safe_config_hash

    def load_manifest_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
        *,
        consumer: ConsumerPolicy = "browse",
        allow_partial: bool = False,
    ) -> dict:
        """Load a complete V2 manifest（V2 manifest 不存在 ⇒ FileNotFoundError）."""
        manifest, _base_dir = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
            consumer=consumer,
            allow_partial=allow_partial,
        )
        return manifest

    def load_provenance_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
    ) -> pd.DataFrame:
        """FFDSTAR Task 1.5：唯一之逐欄執行紀錄讀取入口（經 `_parse_manifest_file` 之單一 manifest 邊界）。

        依 manifest 該 artifact 節點之 `provenance` 物件讀紀錄檔：驗宣告檔存在、路徑在 run 內、sha256 與契約版本相符，
        回 DataFrame。artifact 節點不存在 ⇒ FileNotFoundError；無 `provenance` 物件之舊 run ⇒ `ProvenanceMissingError`；
        不符 ⇒ `ProvenanceIntegrityError`。只讀紀錄檔本身，不重算特徵檔雜湊（§C 嚴禁慢閘）；raw 已回收之 run 亦可讀
        （紀錄檔位於 `provenance/`）。"""
        from momentum.FeatureEngineering import run_provenance

        run_dir = self.feature_run_dir(symbol, tf, config_hash)
        manifest = self._parse_manifest_file(run_dir / self.V2_MANIFEST_NAME)
        artifact = self._get_v2_artifact(manifest, artifact_kind)
        pointer = artifact.get("provenance")
        if pointer is None:
            raise run_provenance.ProvenanceMissingError(
                f"V2 artifact {artifact_kind!r} 無 provenance 物件（舊 run）：{run_dir / self.V2_MANIFEST_NAME}"
            )
        return run_provenance.read_provenance_table(run_dir, pointer)

    @staticmethod
    def resolve_run_status(manifest: dict) -> str:
        """解析 run-level quality status（含未遷移 V2 偵測）。"""
        return merge_manifest_run_status(manifest)

    def stream_groups_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
        *,
        consumer: ConsumerPolicy = "browse",
        allow_partial: bool = False,
        sort_groups: bool = False,
        before_read: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_read_error: Optional[Callable[[str, Path, Exception], None]] = None,
    ) -> Iterator[Tuple[str, pd.DataFrame]]:
        """Yield V2 groups one at a time from raw or processed canonical paths.

        `sort_groups`：依群組名排序（預設 manifest 順序）。`before_read(group, info)`：每組讀檔前呼叫（呼叫端之
        配置前預算判定）。`on_read_error(group, path, exc)`：給定時，讀檔失敗（含檔缺）交由它處置並略過該組
        （它可自行拋出）；未給定 ⇒ 原樣拋出。
        """
        manifest, base_dir = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
            consumer=consumer,
            allow_partial=allow_partial,
        )
        artifact = self._get_v2_artifact(manifest, artifact_kind)
        groups = artifact.get("groups", {}) or {}
        names = sorted(groups) if sort_groups else list(groups)
        for group_name in names:
            group_info = groups[group_name]
            path = self._resolve_manifest_relative_path(base_dir, group_info.get("path") or group_info.get("file"))
            if before_read is not None:
                before_read(group_name, group_info)
            try:
                if not path.exists():
                    raise FileNotFoundError(f"Parquet file missing: {path}")
                table = self._decode_l7_encoded_table(pq.read_table(str(path)))
                box = [table.to_pandas()]
                del table
            except Exception as exc:
                if on_read_error is None:
                    raise
                on_read_error(group_name, path, exc)
                continue
            # 產出後本產生器不再持有該組之 DataFrame／Arrow 表（呼叫端釋放即回收，峰值記憶體不因串流而倍增）
            yield group_name, box.pop()

    def load_columns_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        columns: List[str],
        artifact_kind: str = "raw",
        *,
        consumer: ConsumerPolicy = "browse",
        allow_partial: bool = False,
        attach_row_index: bool = False,
    ) -> pd.DataFrame:
        """Column projection for V2 raw/processed artifacts.

        `attach_row_index=True`（ICFIRSTALIGN Task 1.2）：回傳以該 artifact_kind 之 sidecar 時間戳為索引；
        sidecar 缺 ⇒ `RowIndexArtifactMissingError`；無符合欄 ⇒ 空 DataFrame 帶長度 0 之 DatetimeIndex。
        預設 False 維持既有 caller 行為（RangeIndex，逐位元組不變）。
        """
        manifest, base_dir = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
            consumer=consumer,
            allow_partial=allow_partial,
        )
        row_index = (
            self._require_row_index(symbol, tf, config_hash, artifact_kind) if attach_row_index else None
        )

        artifact = self._get_v2_artifact(manifest, artifact_kind)
        col_to_group: Dict[str, List[str]] = {}
        for group_name, group_info in artifact.get("groups", {}).items():
            group_cols = set(group_info.get("columns", []))
            needed = [column for column in columns if column in group_cols]
            if needed:
                col_to_group[group_name] = needed

        if not col_to_group:
            logger.warning("No V2 columns matched in any group: %s...", columns[:5])
            return pd.DataFrame(index=pd.DatetimeIndex([])) if attach_row_index else pd.DataFrame()

        frames: List[pd.DataFrame] = []
        for group_name, needed_cols in col_to_group.items():
            group_info = artifact["groups"][group_name]
            path = self._resolve_manifest_relative_path(base_dir, group_info.get("path") or group_info.get("file"))
            if not path.exists():
                raise FileNotFoundError(f"Parquet file missing: {path}")
            table = pq.read_table(str(path), columns=needed_cols)
            table = self._decode_l7_encoded_table(table)
            frames.append(table.to_pandas())

        result = pd.concat(frames, axis=1) if frames else pd.DataFrame()
        if row_index is None:
            return result
        if len(result) != len(row_index):
            raise RowIndexLengthMismatchError(
                f"選欄讀回列數 {len(result)} 與 {artifact_kind} sidecar 列數 {len(row_index)} 不符"
            )
        return result.set_axis(row_index, axis=0)

    def _require_row_index(self, symbol: str, tf: str, config_hash: str, artifact_kind: str) -> pd.DatetimeIndex:
        """嚴格讀回時間軸：未宣告或檔案缺 ⇒ `RowIndexArtifactMissingError`（經 `load_row_index_v2`，供 mutant 替換）。"""
        row_index = self.load_row_index_v2(symbol, tf, config_hash, artifact_kind=artifact_kind)
        if row_index is None:
            raise RowIndexArtifactMissingError(
                f"{artifact_kind} 成品未宣告時間軸 sidecar（{symbol}/{tf}/{config_hash}）"
            )
        return row_index

    def load_row_index_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
    ) -> Optional[pd.DatetimeIndex]:
        """Load the persisted V2 timestamp axis of the given artifact kind.

        raw：manifest 根之 ``row_index``；未宣告視為舊 run（回 None）。
        processed（ICFIRSTALIGN Task 1.3）：只讀 processed artifact 節點之 ``row_index``；
        未宣告即 `RowIndexArtifactMissingError`，不得退回根軸。
        已宣告之 sidecar 檔缺 ⇒ `RowIndexArtifactMissingError`（ValueError 子類，與既有 caller 相容）；
        列數須與宣告相符。
        """
        manifest, base_dir = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
        )
        if artifact_kind == "processed":
            node = (manifest.get("artifacts") or {}).get("processed") or {}
            row_index = node.get("row_index")
            if row_index is None:
                raise RowIndexArtifactMissingError(
                    f"processed 成品未宣告自身時間軸 sidecar（{symbol}/{tf}/{config_hash}）；不得退回 raw 根軸"
                )
        else:
            row_index = manifest.get("row_index")
            if row_index is None:
                return None
        if not isinstance(row_index, dict):
            raise ValueError("row_index metadata must be a dictionary")

        raw_path = row_index.get("path")
        path = self._resolve_manifest_relative_path(base_dir, raw_path)
        if not path.exists():
            raise RowIndexArtifactMissingError(f"row_index declared but file missing: {path}")

        try:
            table = pq.read_table(str(path), columns=["timestamp"])
            values = table.column("timestamp").to_numpy()
        except Exception as exc:
            raise ValueError(f"Failed to read row_index artifact: {path}") from exc

        try:
            expected_count = int(row_index.get("count"))
        except (TypeError, ValueError) as exc:
            raise ValueError("row_index count must be a non-null integer") from exc
        if len(values) != expected_count:
            raise ValueError(
                f"row_index length mismatch: {len(values)} != {expected_count}"
            )
        return pd.DatetimeIndex(pd.to_datetime(values, unit="s"))

    def list_features_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str = "raw",
        *,
        consumer: ConsumerPolicy = "browse",
        allow_partial: bool = False,
    ) -> List[str]:
        """List feature names for a V2 run (symbol/timeframe/config_hash)."""
        manifest, _base_dir = self._resolve_manifest_v2(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            artifact_kind=artifact_kind,
            consumer=consumer,
            allow_partial=allow_partial,
        )
        artifact = self._get_v2_artifact(manifest, artifact_kind)
        columns: List[str] = []
        for group_info in artifact.get("groups", {}).values():
            if isinstance(group_info, dict):
                columns.extend(group_info.get("columns", []))
        return columns

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_manifest_v2(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        artifact_kind: str,
        *,
        consumer: ConsumerPolicy = "browse",
        allow_partial: bool = False,
    ) -> Tuple[dict, Path]:
        """讀並驗證 V2 manifest，回傳 (manifest, run_dir)；V2 manifest 不存在 ⇒ FileNotFoundError（不退回舊版面）。"""
        run_dir = self.feature_run_dir(symbol, tf, config_hash)
        manifest = self._parse_manifest_file(run_dir / self.V2_MANIFEST_NAME)
        manifest_path = run_dir / self.V2_MANIFEST_NAME
        self._validate_manifest_v2(
            manifest,
            artifact_kind,
            manifest_path,
            consumer=consumer,
            allow_partial=allow_partial,
        )
        return manifest, run_dir

    @staticmethod
    def _parse_manifest_file(manifest_path: Path) -> dict:
        """全部 V2 讀取之單一 manifest 解析邊界（FF-NAME Task 3.4）：檔不存在 ⇒ FileNotFoundError；
        `feature_naming_version` 缺鍵、舊版／未知版、無法解析 ⇒ `FeatureNamingVersionError`（不自動改名、不別名）。"""
        if not manifest_path.exists():
            raise FileNotFoundError(f"V2 feature manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        feature_naming.assert_feature_naming_version(manifest, where=str(manifest_path))
        return manifest

    def load_run_manifest_v2(self, symbol: str, tf: str, config_hash: str) -> dict:
        """只過命名世代閘之 manifest（不驗 artifact 完整度與 consumer 政策；多標的合併點之版本一致性檢查、
        瀏覽端 run 檢視用）。"""
        manifest_path = self.feature_run_dir(symbol, tf, config_hash) / self.V2_MANIFEST_NAME
        manifest = self._parse_manifest_file(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError(f"Invalid V2 manifest: {manifest_path}")
        return manifest

    def open_run_v2(self, symbol: str, tf: str, config_hash: str) -> FeatureRunView:
        """已過命名世代閘之 run 檢視（瀏覽端用；不驗 artifact 完整度與 consumer 政策，與既有瀏覽語意同）。"""
        manifest = self.load_run_manifest_v2(symbol, tf, config_hash)
        return FeatureRunView(manifest, self.feature_run_dir(symbol, tf, config_hash))

    @staticmethod
    def _validate_manifest_v2(
        manifest: dict,
        artifact_kind: str,
        manifest_path: Path,
        *,
        consumer: ConsumerPolicy = "browse",
        allow_partial: bool = False,
    ) -> str:
        if not isinstance(manifest, dict):
            raise ValueError(f"Invalid V2 manifest: {manifest_path}")
        if not manifest.get("complete"):
            raise ValueError(f"Incomplete V2 manifest is not readable: {manifest_path}")
        artifact = FeatureReader._get_v2_artifact(manifest, artifact_kind)
        if not artifact.get("complete"):
            raise ValueError(f"Incomplete V2 artifact is not readable: {artifact_kind}")
        return assert_consumer_run_status(
            manifest,
            consumer=consumer,
            allow_partial=allow_partial,
        )

    @staticmethod
    def get_v2_artifact(manifest: Dict[str, Any], kind: str) -> Dict[str, Any]:
        """Stable public API for resolving a V2 manifest artifact."""

        return FeatureReader._get_v2_artifact(manifest, kind)

    @staticmethod
    def _get_v2_artifact(manifest: dict, artifact_kind: str) -> Dict[str, Any]:
        artifacts = manifest.get("artifacts", {})
        artifact = artifacts.get(artifact_kind)
        if not isinstance(artifact, dict):
            raise FileNotFoundError(f"V2 artifact not found: {artifact_kind}")
        return artifact

    @staticmethod
    def _resolve_manifest_relative_path(base_dir: Path, raw_path: Optional[str]) -> Path:
        if not raw_path:
            raise ValueError("Manifest group path is missing")
        relative_path = Path(str(raw_path))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"Unsafe manifest path: {raw_path}")
        return base_dir / relative_path

    @staticmethod
    def _decode_l7_encoded_table(table: pa.Table) -> pa.Table:
        metadata = table.schema.metadata or {}
        raw_registry = metadata.get(L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8"))
        if not raw_registry:
            return table

        try:
            registry = json.loads(raw_registry.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid l7_encoding_registry metadata") from exc

        arrays: List[Any] = []
        names: List[str] = []
        for column_name in table.column_names:
            column_registry = registry.get(column_name)
            if not column_registry:
                arrays.append(table[column_name])
                names.append(column_name)
                continue

            encoding_type = column_registry.get("encoding_type")
            column_values = table[column_name].to_pandas().to_numpy()
            if encoding_type == RANK_UINT16_ENCODING:
                window = int(column_registry.get("window") or 0)
                arrays.append(pa.array(decode_rank_from_uint16(column_values, window)))
            elif encoding_type in {ZSCORE_INT16_ENCODING, GAUSSIAN_INT16_ENCODING}:
                arrays.append(pa.array(decode_zscore_from_int16(column_values)))
            else:
                arrays.append(table[column_name])
            names.append(column_name)

        decoded_table = pa.Table.from_arrays(arrays, names=names)
        return decoded_table.replace_schema_metadata(metadata)

    @staticmethod
    def _safe_path_segment(value: str, field_name: str) -> str:
        segment = str(value).strip()
        if not segment or segment in {".", ".."} or "/" in segment or "\\" in segment:
            raise ValueError(f"Invalid {field_name}: {value!r}")
        return segment
