"""
Feature Storage - 特徵儲存管理

使用 HDF5 格式儲存和讀取特徵數據

Author: AI Agent
Date: 2026-01-10
"""

import os
import queue
import threading
import time
import h5py
import pandas as pd
import numpy as np
import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = None
    pq = None

from momentum.FeatureEngineering.core.column_group_registry import FailureType
from momentum.core.logging import get_logger

if TYPE_CHECKING:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

logger = get_logger(__name__)


def _require_pyarrow() -> Tuple[Any, Any]:
    """Return pyarrow modules or raise a clear dependency error."""
    if pa is None or pq is None:
        raise ImportError("pyarrow is required for parquet persistence")
    return pa, pq


class AsyncParquetCompactor:
    """Background compactor that merges small parquet column partitions."""

    def __init__(
        self,
        staging_dir: Path,
        final_dir: Path,
        target_rows: int = 100_000,
        min_files_to_compact: int = 8,
    ) -> None:
        self._staging_dir = Path(staging_dir)
        self._final_dir = Path(final_dir)
        self._target_rows = max(1, int(target_rows))
        self._min_files_to_compact = max(2, int(min_files_to_compact))
        self._queue: "queue.Queue[Optional[Tuple[str, Path]]]" = queue.Queue()
        self._pending: List[Tuple[str, Path, int]] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._error: Optional[BaseException] = None
        self._merged_outputs: List[Path] = []
        self._merged_sources: Dict[str, List[str]] = {}
        self._part_to_final_path: Dict[str, str] = {}
        self._merge_index = 0

    @property
    def merged_sources(self) -> Dict[str, List[str]]:
        """Return merged parquet filename -> source part ids mapping."""
        with self._lock:
            return {key: list(value) for key, value in self._merged_sources.items()}

    @property
    def part_to_final_path(self) -> Dict[str, str]:
        """Return source part id -> final parquet path mapping."""
        with self._lock:
            return dict(self._part_to_final_path)

    def start(self) -> None:
        """Start the background compactor worker."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="l7-parquet-compactor", daemon=True)
        self._thread.start()

    def enqueue(self, item: Tuple[str, Path]) -> None:
        """Queue one staging parquet file for background compaction."""
        if self._error is not None:
            raise RuntimeError("AsyncParquetCompactor already failed") from self._error
        part_id, staging_path = item
        self._queue.put((part_id, Path(staging_path)))

    def finalize(self) -> List[Path]:
        """Flush remaining files, stop the worker, and return final parquet paths."""
        if self._thread is None:
            return []
        self._queue.put(None)
        self._thread.join()
        if self._error is not None:
            raise RuntimeError("AsyncParquetCompactor failed during finalize") from self._error
        with self._lock:
            return list(self._merged_outputs)

    def _run(self) -> None:
        try:
            while True:
                item = self._queue.get()
                if item is None:
                    self._flush_pending(force=True)
                    return

                part_id, staging_path = item
                row_count = self._read_row_count(staging_path)

                if row_count >= self._target_rows:
                    self._compact_batch([(part_id, staging_path, row_count)])
                    continue

                self._pending.append((part_id, staging_path, row_count))
                if len(self._pending) >= self._min_files_to_compact:
                    self._flush_pending(force=False)
        except BaseException as exc:
            self._error = exc

    def _flush_pending(self, force: bool) -> None:
        if not self._pending:
            return
        if not force and len(self._pending) < self._min_files_to_compact:
            return
        batch = list(self._pending)
        self._pending.clear()
        self._compact_batch(batch)

    def _compact_batch(self, batch: List[Tuple[str, Path, int]]) -> None:
        start_time = time.perf_counter()
        final_path, source_ids = self._merge_batch(batch)
        elapsed = time.perf_counter() - start_time
        with self._lock:
            self._merged_outputs.append(final_path)
            self._merged_sources[final_path.name] = list(source_ids)
            resolved_path = str(final_path.resolve())
            for part_id in source_ids:
                self._part_to_final_path[part_id] = resolved_path
        logger.info(
            "[L7] Compactor merged %d parts into %s in %.2fs",
            len(source_ids),
            final_path.name,
            elapsed,
        )

    def _merge_batch(self, batch: List[Tuple[str, Path, int]]) -> Tuple[Path, List[str]]:
        _, pq_module = _require_pyarrow()
        final_path = self._next_output_path()
        temp_path = self._next_temp_path(final_path)
        source_ids = [part_id for part_id, _path, _rows in batch]

        if len(batch) == 1:
            part_id, staging_path, _row_count = batch[0]
            os.replace(staging_path, final_path)
            return final_path, [part_id]

        try:
            merged_table = self._merge_tables(batch)
            pq_module.write_table(
                merged_table,
                str(temp_path),
                compression="zstd",
                compression_level=1,
            )
            os.replace(temp_path, final_path)
            for _part_id, staging_path, _row_count in batch:
                if staging_path.exists():
                    staging_path.unlink()
            return final_path, source_ids
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _merge_tables(self, batch: List[Tuple[str, Path, int]]):
        pa_module, pq_module = _require_pyarrow()
        expected_rows: Optional[int] = None
        arrays: List[Any] = []
        names: List[str] = []

        for _part_id, staging_path, row_count in batch:
            table = pq_module.read_table(staging_path)
            if expected_rows is None:
                expected_rows = row_count
            elif row_count != expected_rows:
                raise ValueError(
                    f"Compactor row mismatch: expected {expected_rows}, got {row_count} for {staging_path.name}"
                )

            for column_name in table.column_names:
                if column_name in names:
                    raise ValueError(f"Compactor duplicate column detected: {column_name}")
                names.append(column_name)
                arrays.append(table[column_name])

        return pa_module.Table.from_arrays(arrays, names=names)

    def _read_row_count(self, staging_path: Path) -> int:
        _, pq_module = _require_pyarrow()
        parquet_file = pq_module.ParquetFile(str(staging_path))
        return int(parquet_file.metadata.num_rows)

    def _next_output_path(self) -> Path:
        self._merge_index += 1
        return self._final_dir / f"merged_{self._merge_index:04d}.parquet"

    @staticmethod
    def _next_temp_path(final_path: Path) -> Path:
        return final_path.parent / f".{final_path.stem}.tmp{final_path.suffix}"


class FeatureStorage:
    """
    特徵儲存管理器
    
    使用 HDF5 格式儲存特徵，支持元數據管理
    
    Storage Format:
        data_cache/features/{case_id}.h5
        /{symbol}/{timeframe}/
            /features          # (n_samples, n_features) float32
            /feature_names     # Attribute: List[str]
            /labels            # (n_samples,) int32 (可選)
            /timestamps        # (n_samples,) int64
            /metadata          # Attributes
    """
    
    def __init__(self, base_path: str = "data_cache/features"):
        """
        Args:
            base_path: 特徵儲存根目錄
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._chunk_rows = self._resolve_positive_env("FFACT_HDF5_CHUNK_ROWS", 256)
        self._chunk_cols = self._resolve_positive_env("FFACT_HDF5_CHUNK_COLS", 512)
        self._gzip_level = self._resolve_bounded_env("FFACT_HDF5_GZIP_LEVEL", 4, 0, 9)
    
    def save_features_to_hdf5(
        self,
        case_id: str,
        symbol: str,
        timeframe: str,
        features_df: pd.DataFrame,
        feature_names: List[str],
        labels: Optional[np.ndarray] = None,
        strategy_params: Optional[Dict] = None
    ) -> str:
        """
        儲存特徵至 HDF5
        
        Args:
            case_id: 案例 ID (e.g., "ETHUSDT_1735905600_1")
            symbol: 交易標的 (e.g., "ETHUSDT")
            timeframe: 時間週期 (e.g., "1h", "12h")
            features_df: 特徵 DataFrame (必須包含 timestamp 和所有特徵)
            feature_names: 特徵名稱列表
            labels: 標籤數組 (可選, 1=盈利, 0=虧損)
            strategy_params: 策略參數 (用於記錄元數據)
            
        Returns:
            檔案路徑
        """
        file_path = self.base_path / f"{case_id}.h5"
        
        self.logger.info(f"開始儲存特徵 - 案例: {case_id}, 檔案: {file_path}")
        
        try:
            with h5py.File(file_path, 'w') as f:
                # 建立群組
                group_path = f"{symbol}/{timeframe}"
                group = f.create_group(group_path)
                
                # 儲存特徵矩陣
                feature_matrix = features_df[feature_names].values.astype(np.float32)
                group.create_dataset(
                    'features',
                    data=feature_matrix,
                    compression='gzip',
                    compression_opts=4
                )
                
                # 儲存特徵名稱 (作為屬性)
                group.attrs['feature_names'] = feature_names
                group.attrs['feature_count'] = len(feature_names)
                
                # 儲存時間戳
                timestamps = features_df['timestamp'].values.astype(np.int64)
                group.create_dataset(
                    'timestamps',
                    data=timestamps,
                    compression='gzip'
                )
                
                # 儲存標籤 (如果有)
                if labels is not None:
                    group.create_dataset(
                        'labels',
                        data=labels.astype(np.int32),
                        compression='gzip'
                    )
                
                # 儲存元數據
                group.attrs['extraction_time'] = datetime.now().isoformat()
                group.attrs['case_id'] = case_id
                group.attrs['symbol'] = symbol
                group.attrs['timeframe'] = timeframe
                group.attrs['n_samples'] = len(features_df)
                group.attrs['generation_method'] = 'dynamic'
                
                if strategy_params:
                    group.attrs['strategy_type'] = strategy_params.get('strategy_type', 'unknown')
                    # 將策略參數序列化為字串
                    import json
                    group.attrs['strategy_params'] = json.dumps(
                        strategy_params.get('params', {})
                    )
                
                self.logger.info(
                    f"特徵儲存完成 - 樣本數: {len(features_df)}, "
                    f"特徵數: {len(feature_names)}, 檔案大小: {file_path.stat().st_size / 1024:.2f} KB"
                )
                
                return str(file_path)
                
        except Exception as e:
            self.logger.error(f"特徵儲存失敗: {str(e)}", exc_info=True)
            raise
    
    def load_features_from_hdf5(
        self,
        case_id: str,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Tuple[pd.DataFrame, List[str], Dict]:
        """
        從 HDF5 讀取特徵
        
        Args:
            case_id: 案例 ID
            symbol: 交易標的（可選，未提供時自動偵測）
            timeframe: 時間週期（可選，未提供時自動偵測）
            
        Returns:
            (features_df, feature_names, metadata)
        """
        file_path = self.base_path / f"{case_id}.h5"
        
        if not file_path.exists():
            raise FileNotFoundError(f"特徵檔案不存在: {file_path}")
        
        self.logger.info(f"開始讀取特徵 - 案例: {case_id}, 檔案: {file_path}")
        
        try:
            with h5py.File(file_path, 'r') as f:
                if symbol is None or timeframe is None:
                    symbols = list(f.keys())
                    if not symbols:
                        raise KeyError("HDF5 檔案沒有任何群組")
                    symbol = symbols[0]
                    timeframes = list(f[symbol].keys())
                    if not timeframes:
                        raise KeyError(f"群組不存在: {symbol}")
                    timeframe = timeframes[0]
                    if len(symbols) > 1 or len(timeframes) > 1:
                        self.logger.warning(
                            f"未指定 symbol/timeframe，使用第一個群組: {symbol}/{timeframe}"
                        )

                group_path = f"{symbol}/{timeframe}"

                if group_path not in f:
                    raise KeyError(f"群組不存在: {group_path}")

                group = f[group_path]
                
                # 讀取特徵矩陣
                feature_matrix = group['features'][:]
                
                # 讀取特徵名稱
                raw_feature_names = list(group.attrs['feature_names'])
                feature_names = [
                    n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                    for n in raw_feature_names
                ]
                
                # 讀取時間戳
                timestamps = group['timestamps'][:]
                
                # 建立 DataFrame
                features_df = pd.DataFrame(
                    feature_matrix,
                    columns=feature_names
                )
                features_df['timestamp'] = timestamps
                
                # 讀取標籤 (如果有)
                if 'labels' in group:
                    labels = group['labels'][:]
                    features_df['label'] = labels
                
                # 讀取元數據
                metadata = {
                    'case_id': group.attrs.get('case_id'),
                    'symbol': group.attrs.get('symbol'),
                    'timeframe': group.attrs.get('timeframe'),
                    'extraction_time': group.attrs.get('extraction_time'),
                    'n_samples': group.attrs.get('n_samples'),
                    'feature_count': group.attrs.get('feature_count'),
                    'generation_method': group.attrs.get('generation_method'),
                    'strategy_type': group.attrs.get('strategy_type'),
                }
                
                # 解析策略參數
                if 'strategy_params' in group.attrs:
                    import json
                    metadata['strategy_params'] = json.loads(group.attrs['strategy_params'])
                
                self.logger.info(
                    f"特徵讀取完成 - 樣本數: {len(features_df)}, 特徵數: {len(feature_names)}"
                )
                
                return features_df, feature_names, metadata
                
        except Exception as e:
            self.logger.error(f"特徵讀取失敗: {str(e)}", exc_info=True)
            raise

    def save_factory_output(self, symbol: str, timeframe: str, result) -> str:
        """儲存工廠輸出：features.h5 + meta.json"""
        file_path = self.base_path / f"{symbol}_{timeframe}_factory.h5"
        self.save_metadata_json(symbol, timeframe, result.metadata or {})

        self.logger.info(f"開始儲存工廠輸出 - {symbol}/{timeframe}")

        features_df = result.features_df
        labels_df = result.labels_df

        feature_names = list(features_df.columns)
        label_names = list(labels_df.columns) if labels_df is not None else []

        if "timestamp" in features_df.columns:
            timestamps = features_df["timestamp"].to_numpy(dtype=np.int64)
        else:
            timestamps = features_df.index.to_numpy()
            if isinstance(features_df.index, pd.DatetimeIndex):
                timestamps = features_df.index.view("int64")

        try:
            with h5py.File(file_path, "w") as f:
                group = f.create_group(f"{symbol}/{timeframe}")

                # Use .values to get underlying array directly (memmap if
                # disk-backed) instead of .to_numpy() which may force a copy.
                features_arr = features_df.values
                if features_arr.dtype != np.float32:
                    features_arr = np.asarray(features_arr, dtype=np.float32)
                feature_chunks = self._build_2d_chunks(features_arr.shape)
                group.create_dataset(
                    "features",
                    data=features_arr,
                    compression="gzip",
                    compression_opts=self._gzip_level,
                    chunks=feature_chunks,
                )

                timestamp_chunks = self._build_1d_chunks(timestamps.shape)
                group.create_dataset(
                    "timestamps",
                    data=timestamps,
                    compression="gzip",
                    compression_opts=self._gzip_level,
                    chunks=timestamp_chunks,
                )

                if labels_df is not None and not labels_df.empty:
                    labels_arr = labels_df.to_numpy(dtype=np.float32)
                    label_chunks = self._build_2d_chunks(labels_arr.shape)
                    group.create_dataset(
                        "labels",
                        data=labels_arr,
                        compression="gzip",
                        compression_opts=self._gzip_level,
                        chunks=label_chunks,
                    )
                    group.attrs["label_names"] = label_names

                str_dtype = h5py.string_dtype(encoding="utf-8")
                group.create_dataset(
                    "feature_names",
                    data=np.array(feature_names, dtype=object),
                    dtype=str_dtype,
                )

                if label_names:
                    group.create_dataset(
                        "label_names",
                        data=np.array(label_names, dtype=object),
                        dtype=str_dtype,
                    )

                group.attrs["feature_count"] = len(feature_names)
                group.attrs["label_count"] = len(label_names)
                group.attrs["metadata_json"] = json.dumps(result.metadata or {})

            self.logger.info(
                f"工廠輸出儲存完成 - 特徵數: {len(feature_names)}, 標籤數: {len(label_names)}"
            )
            return str(file_path)
        except Exception as e:
            self.logger.error(f"工廠輸出儲存失敗: {str(e)}", exc_info=True)
            raise

    # V7 §12 P0: max columns before auto-splitting a group
    MAX_GROUP_COLUMNS = 5000

    @staticmethod
    def _classify_persist_failure(error: BaseException) -> FailureType:
        """Classify parquet persistence failures for logging and diagnostics."""
        if isinstance(error, MemoryError):
            return FailureType.OOM
        if isinstance(error, (OSError, IOError)):
            return FailureType.IO_ERROR
        if isinstance(error, (ValueError, TypeError)):
            return FailureType.VALIDATION
        return FailureType.CONFIG

    def _persist_parts_parallel(
        self,
        parts_queue: List[Tuple[str, Any, Path, Path]],
        n_workers: int,
        compactor: Optional[AsyncParquetCompactor] = None,
    ) -> List[str]:
        """Persist parquet parts with optional parallel writes and async compaction."""
        _, pq_module = _require_pyarrow()
        if not parts_queue:
            return []

        start_time = time.perf_counter()

        def _write_one(item: Tuple[str, Any, Path, Path]) -> str:
            part_id, table, final_path, staging_path = item
            pq_module.write_table(
                table,
                str(staging_path),
                compression="zstd",
                compression_level=1,
            )
            if compactor is not None:
                compactor.enqueue((part_id, staging_path))
            else:
                os.replace(staging_path, final_path)
            return str(final_path.resolve())

        try:
            if n_workers <= 1 or len(parts_queue) == 1:
                results = [_write_one(item) for item in parts_queue]
            else:
                with ThreadPoolExecutor(max_workers=n_workers) as pool:
                    results = list(pool.map(_write_one, parts_queue))
        except Exception as exc:
            failure_type = self._classify_persist_failure(exc)
            self.logger.error(
                "[L7] Parallel persist failed: failure_type=%s error=%s",
                failure_type.value,
                str(exc),
                exc_info=True,
            )
            raise

        elapsed = time.perf_counter() - start_time
        self.logger.info(
            "[L7] Parallel persist: %d parts in %.2fs, %d workers",
            len(results),
            elapsed,
            max(1, int(n_workers)),
        )
        return results

    def persist_registry_to_parquet(
        self,
        symbol: str,
        config_hash: str,
        registry: "ColumnGroupRegistry",
        cleanup_intermediate: bool = False,
    ) -> List[str]:
        """Persist CGSA registry groups to per-group parquet files.

        V7 enhancements:
        - float16 cast before writing (halves storage, IC delta < 1e-5)
        - Auto-split groups with > MAX_GROUP_COLUMNS columns
        - Write manifest.json + columns.json.gz after all groups persisted

        Uses bounded batched staging: groups are converted to parquet-ready parts,
        flushed through the L7 writer, and their backing .npy files are deleted
        once the batch is durably accepted.
        """
        pa_module, _ = _require_pyarrow()
        from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config

        output_dir = self.base_path / symbol / config_hash
        output_dir.mkdir(parents=True, exist_ok=True)

        staging_dir = output_dir / f".staging_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        staging_dir.mkdir(parents=True, exist_ok=False)

        persisted_paths: List[str] = []
        parquet_path_map: Dict[str, str] = {}
        # V7 manifest groups metadata
        manifest_groups: Dict[str, Dict] = {}
        all_columns: List[str] = []
        total_rows: int = 0
        npy_freed = 0
        preserve_staging = False
        part_to_group_id: Dict[str, str] = {}
        first_part_by_group: Dict[str, str] = {}

        try:
            groups_list = list(registry.iter_all())
            total_groups = len(groups_list)
            max_group_columns = max((len(group.columns) for _group_id, group in groups_list), default=0)
            tier = get_memory_tier()
            tier_cfg = get_tier_config(tier)
            n_workers = self._resolve_positive_env(
                "FFACT_L7_WORKERS",
                int(tier_cfg["l7_workers"]),
            )
            compactor_enabled = os.getenv("FFACT_L7_COMPACTOR_ENABLED", "1").strip() != "0"
            target_rows = self._resolve_positive_env("FFACT_L7_COMPACTOR_TARGET_ROWS", 100_000)
            chunk_bars = tier_cfg.get("chunk_bars")
            use_compactor = (
                compactor_enabled
                and n_workers > 1
                and chunk_bars is not None
                and max_group_columns <= self.MAX_GROUP_COLUMNS
                and total_groups > 1
            )
            compactor: Optional[AsyncParquetCompactor] = None
            if use_compactor:
                compactor = AsyncParquetCompactor(
                    staging_dir=staging_dir,
                    final_dir=output_dir,
                    target_rows=target_rows,
                )
                compactor.start()

            pending_parts: List[Tuple[str, Any, Path, Path]] = []
            pending_disk_paths: Dict[str, Path] = {}
            batch_limit = max(1, n_workers * 2)

            def _flush_pending_parts() -> None:
                nonlocal pending_parts, pending_disk_paths, npy_freed, persisted_paths
                if not pending_parts:
                    return
                batch_results = self._persist_parts_parallel(
                    pending_parts,
                    n_workers=n_workers,
                    compactor=compactor,
                )
                if compactor is None:
                    persisted_paths.extend(batch_results)

                for group_id, disk_path in pending_disk_paths.items():
                    if disk_path.exists():
                        disk_path.unlink()
                        npy_freed += 1
                pending_parts = []
                pending_disk_paths = {}

            for idx, (group_id, group) in enumerate(groups_list, 1):
                group_data = np.asarray(registry.load_data(group_id), dtype=np.float32)
                if group_data.ndim != 2:
                    raise ValueError(f"Group {group_id} data must be 2D, got shape={group_data.shape}")
                if group_data.shape[1] != len(group.columns):
                    raise ValueError(
                        f"Group {group_id} columns mismatch: expected {len(group.columns)}, got {group_data.shape[1]}"
                    )

                if total_rows == 0 and group_data.shape[0] > 0:
                    total_rows = group_data.shape[0]

                columns_list = list(group.columns)

                # Auto-split groups exceeding MAX_GROUP_COLUMNS (V7 §12 P0)
                parts = self._split_large_group(group_id, columns_list, group_data)

                for part_id, part_cols, part_data in parts:
                    # Cast to float16 for storage (V7 §12 P0)
                    data_f16 = part_data.astype(np.float16)

                    staged_path = staging_dir / f"{part_id}.parquet"
                    final_path = output_dir / f"{part_id}.parquet"

                    arrays = [pa_module.array(data_f16[:, ci]) for ci in range(len(part_cols))]
                    table = pa_module.Table.from_arrays(arrays, names=list(part_cols))
                    pending_parts.append((part_id, table, final_path, staged_path))
                    part_to_group_id[part_id] = group_id
                    first_part_by_group.setdefault(group_id, part_id)

                    manifest_groups[part_id] = {
                        "file": f"{part_id}.parquet",
                        "column_count": len(part_cols),
                        "columns": list(part_cols),
                    }
                    all_columns.extend(part_cols)
                    del data_f16

                if group.disk_path and group.disk_path.exists():
                    pending_disk_paths[group_id] = group.disk_path

                del group_data

                if len(pending_parts) >= batch_limit:
                    _flush_pending_parts()

                if idx % 100 == 0 or idx == total_groups:
                    self.logger.info(
                        "[L7] Persisted %d/%d groups (%d .npy freed)",
                        idx, total_groups, npy_freed,
                    )

            _flush_pending_parts()

            compaction_manifest: Dict[str, List[str]] = {}
            part_to_final_path: Dict[str, str]
            if compactor is not None:
                merged_paths = compactor.finalize()
                persisted_paths = [str(path.resolve()) for path in merged_paths]
                part_to_final_path = compactor.part_to_final_path
                compaction_manifest = compactor.merged_sources
            else:
                part_to_final_path = {
                    part_id: str((output_dir / f"{part_id}.parquet").resolve())
                    for part_id in manifest_groups
                }

            for part_id, group_metadata in manifest_groups.items():
                resolved_path = part_to_final_path.get(part_id)
                if resolved_path:
                    group_metadata["file"] = Path(resolved_path).name

            for group_id, first_part_id in first_part_by_group.items():
                resolved_path = part_to_final_path.get(first_part_id)
                if resolved_path:
                    parquet_path_map[group_id] = resolved_path

            if parquet_path_map:
                registry.set_group_parquet_paths(parquet_path_map)

            # Write V7 manifest.json + columns.json.gz
            self._write_v7_manifest(
                output_dir=output_dir,
                symbol=symbol,
                config_hash=config_hash,
                total_features=len(all_columns),
                total_rows=total_rows,
                groups=manifest_groups,
                compaction_sources=compaction_manifest,
            )
            self._write_columns_json_gz(output_dir, all_columns)

            self.logger.info(
                "CGSA per-group parquet persist completed: symbol=%s config_hash=%s "
                "groups=%d npy_freed=%d total_features=%d dtype=float16",
                symbol,
                config_hash,
                len(persisted_paths),
                npy_freed,
                len(all_columns),
            )
            return persisted_paths
        except Exception as e:
            preserve_staging = True
            failure_type = self._classify_persist_failure(e)
            self.logger.error(
                "CGSA per-group parquet persist failed: symbol=%s config_hash=%s failure_type=%s error=%s",
                symbol,
                config_hash,
                failure_type.value,
                str(e),
                exc_info=True,
            )
            raise
        finally:
            if staging_dir.exists() and not preserve_staging:
                for child in staging_dir.iterdir():
                    if child.is_file():
                        child.unlink()
                staging_dir.rmdir()

    @classmethod
    def _split_large_group(
        cls,
        group_id: str,
        columns: List[str],
        data: np.ndarray,
    ) -> List[Tuple[str, List[str], np.ndarray]]:
        """Split a group into sub-parts when column count exceeds MAX_GROUP_COLUMNS.

        Returns list of (part_id, part_columns, part_data_slice).
        Groups with <= MAX_GROUP_COLUMNS columns are returned as-is.
        """
        max_cols = cls.MAX_GROUP_COLUMNS
        if len(columns) <= max_cols:
            return [(group_id, columns, data)]

        parts: List[Tuple[str, List[str], np.ndarray]] = []
        for i, chunk_start in enumerate(range(0, len(columns), max_cols)):
            chunk_end = min(chunk_start + max_cols, len(columns))
            part_cols = columns[chunk_start:chunk_end]
            part_data = data[:, chunk_start:chunk_end]
            part_id = f"{group_id}_part{i + 1}"
            parts.append((part_id, part_cols, part_data))
        return parts

    @staticmethod
    def _write_v7_manifest(
        output_dir: Path,
        symbol: str,
        config_hash: str,
        total_features: int,
        total_rows: int,
        groups: Dict[str, Dict],
        compaction_sources: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """Write V7-format manifest.json (without full column names inline)."""
        manifest = {
            "version": "7.0",
            "symbol": symbol,
            "config_hash": config_hash,
            "created_at": datetime.utcnow().isoformat(),
            "total_features": total_features,
            "total_rows": total_rows,
            "dtype": "float16",
            "groups": groups,
        }
        if compaction_sources:
            manifest["compaction"] = {
                "merged_files": compaction_sources,
            }
        manifest_path = output_dir / "manifest.json"
        temp_path = output_dir / "manifest.json.tmp"
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, manifest_path)

    @staticmethod
    def _write_columns_json_gz(output_dir: Path, all_columns: List[str]) -> None:
        """Write compressed columns.json.gz containing all feature names."""
        import gzip as _gzip

        gz_path = output_dir / "columns.json.gz"
        temp_path = output_dir / "columns.json.gz.tmp"
        with _gzip.open(temp_path, "wt", encoding="utf-8") as f:
            json.dump(all_columns, f)
        os.replace(temp_path, gz_path)

    def _build_2d_chunks(self, shape: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        if len(shape) != 2:
            return None
        rows, cols = int(shape[0]), int(shape[1])
        if rows <= 0 or cols <= 0:
            return None
        return (min(rows, self._chunk_rows), min(cols, self._chunk_cols))

    def _build_1d_chunks(self, shape: Tuple[int, ...]) -> Optional[Tuple[int]]:
        if len(shape) != 1:
            return None
        rows = int(shape[0])
        if rows <= 0:
            return None
        return (min(rows, self._chunk_rows),)

    @staticmethod
    def _resolve_positive_env(env_name: str, default_value: int) -> int:
        raw = os.getenv(env_name, str(default_value)).strip()
        try:
            parsed = int(raw)
        except ValueError:
            parsed = default_value
        return max(1, parsed)

    @staticmethod
    def _resolve_bounded_env(env_name: str, default_value: int, lower: int, upper: int) -> int:
        raw = os.getenv(env_name, str(default_value)).strip()
        try:
            parsed = int(raw)
        except ValueError:
            parsed = default_value
        return max(lower, min(upper, parsed))

    def load_factory_output(self, symbol: str, timeframe: str):
        """載入工廠輸出"""
        file_path = self.base_path / f"{symbol}_{timeframe}_factory.h5"
        if not file_path.exists():
            return None

        try:
            with h5py.File(file_path, "r") as f:
                group_path = f"{symbol}/{timeframe}"
                if group_path not in f:
                    return None
                group = f[group_path]

                features = group["features"][:]
                timestamps = group["timestamps"][:]
                feature_names = []
                if "feature_names" in group:
                    raw_feature_names = list(group["feature_names"][:])
                    feature_names = [
                        n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                        for n in raw_feature_names
                    ]
                else:
                    raw_feature_names = list(group.attrs.get("feature_names", []))
                    feature_names = [
                        n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                        for n in raw_feature_names
                    ]

                features_df = pd.DataFrame(features, columns=feature_names)
                features_df.index = pd.Index(timestamps, name="timestamp")

                labels_df = pd.DataFrame(index=features_df.index)
                if "labels" in group:
                    labels = group["labels"][:]
                    label_names: List[str] = []
                    if "label_names" in group:
                        raw_label_names = list(group["label_names"][:])
                        label_names = [
                            n.decode("utf-8") if isinstance(n, (bytes, np.bytes_)) else str(n)
                            for n in raw_label_names
                        ]
                    labels_df = pd.DataFrame(labels, columns=label_names, index=features_df.index)

                metadata = {}
                metadata_json = group.attrs.get("metadata_json")
                if metadata_json:
                    try:
                        metadata = json.loads(metadata_json)
                    except json.JSONDecodeError:
                        metadata = {}

            from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult

            result = FeatureGenerationResult(
                features_df=features_df,
                labels_df=labels_df,
                metadata=metadata,
                feature_count=features_df.shape[1],
                generation_time=metadata.get("generation_time", 0.0),
                layer_counts=metadata.get("layer_counts", {}),
                config_used=metadata.get("config_used", {}),
                hdf5_path=str(file_path),
            )

            numeric_cols = result.features_df.select_dtypes(include=["float64"]).columns
            if len(numeric_cols) > 0:
                result.features_df[numeric_cols] = result.features_df[numeric_cols].astype(np.float32)

            return result
        except Exception as e:
            self.logger.error(f"工廠輸出讀取失敗: {str(e)}", exc_info=True)
            raise

    def save_metadata_json(self, symbol: str, timeframe: str, metadata: Dict) -> str:
        """儲存 features_meta.json"""
        file_path = self.base_path / f"{symbol}_{timeframe}_factory_meta.json"
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=True, indent=2)
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Metadata 儲存失敗: {str(e)}", exc_info=True)
            raise
    
    def feature_file_exists(self, case_id: str) -> bool:
        """檢查特徵檔案是否存在"""
        file_path = self.base_path / f"{case_id}.h5"
        return file_path.exists()
    
    def get_feature_summary(
        self,
        case_id: str,
        symbol: str,
        timeframe: str
    ) -> Dict:
        """
        獲取特徵摘要統計
        
        Args:
            case_id: 案例 ID
            symbol: 交易標的
            timeframe: 時間週期
            
        Returns:
            特徵統計摘要
        """
        features_df, feature_names, metadata = self.load_features_from_hdf5(
            case_id, symbol, timeframe
        )
        
        # 計算統計量
        feature_stats = {}
        for feature in feature_names:
            stats = features_df[feature].describe()
            feature_stats[feature] = {
                'mean': float(stats['mean']),
                'std': float(stats['std']),
                'min': float(stats['min']),
                'max': float(stats['max']),
                '25%': float(stats['25%']),
                '50%': float(stats['50%']),
                '75%': float(stats['75%'])
            }
        
        # 計算相關矩陣 (只保存對角線以上部分)
        corr_matrix = features_df[feature_names].corr()
        correlation_pairs = []
        for i in range(len(feature_names)):
            for j in range(i + 1, len(feature_names)):
                corr = abs(corr_matrix.iloc[i, j])
                if corr > 0.7:  # 只記錄中高相關性
                    correlation_pairs.append({
                        'feature1': feature_names[i],
                        'feature2': feature_names[j],
                        'correlation': float(corr)
                    })
        
        # 排序 (由高到低)
        correlation_pairs.sort(key=lambda x: x['correlation'], reverse=True)
        
        summary = {
            'case_id': case_id,
            'symbol': symbol,
            'timeframe': timeframe,
            'feature_count': len(feature_names),
            'sample_count': len(features_df),
            'feature_names': feature_names,
            'feature_stats': feature_stats,
            'high_correlation_pairs': correlation_pairs[:20],  # 只返回前 20 對
            'metadata': metadata
        }
        
        return summary
    
    def delete_features(self, case_id: str) -> bool:
        """
        刪除特徵檔案
        
        Args:
            case_id: 案例 ID
            
        Returns:
            是否成功刪除
        """
        file_path = self.base_path / f"{case_id}.h5"
        
        if not file_path.exists():
            self.logger.warning(f"特徵檔案不存在，無法刪除: {file_path}")
            return False
        
        try:
            file_path.unlink()
            self.logger.info(f"特徵檔案已刪除: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"刪除特徵檔案失敗: {str(e)}", exc_info=True)
            return False
    
    def list_feature_files(self) -> List[Dict]:
        """
        列出所有特徵檔案
        
        Returns:
            特徵檔案列表，每個元素包含 case_id, file_path, file_size, modified_time
        """
        feature_files = []
        
        for file_path in self.base_path.glob("*.h5"):
            case_id = file_path.stem  # 檔名 (不含副檔名)
            
            feature_files.append({
                'case_id': case_id,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        # 按修改時間排序 (最新的在前)
        feature_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return feature_files
