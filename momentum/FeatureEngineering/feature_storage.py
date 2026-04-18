"""
Feature Storage - 特徵儲存管理

使用 HDF5 格式儲存和讀取特徵數據

Author: AI Agent
Date: 2026-01-10
"""

import os
import h5py
import pandas as pd
import numpy as np
import json
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from momentum.core.logging import get_logger

if TYPE_CHECKING:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

logger = get_logger(__name__)


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

    def persist_registry_to_parquet(
        self,
        symbol: str,
        config_hash: str,
        registry: "ColumnGroupRegistry",
        cleanup_intermediate: bool = False,
    ) -> List[str]:
        """Persist CGSA registry groups to per-group parquet files."""
        output_dir = self.base_path / symbol / config_hash
        output_dir.mkdir(parents=True, exist_ok=True)

        staging_dir = output_dir / f".staging_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        staging_dir.mkdir(parents=True, exist_ok=False)

        staged_pairs: List[Tuple[str, Path, Path]] = []
        persisted_paths: List[str] = []
        parquet_path_map: Dict[str, str] = {}

        try:
            for group_id, group in registry.iter_all():
                group_data = np.asarray(registry.load_data(group_id), dtype=np.float32)
                if group_data.ndim != 2:
                    raise ValueError(f"Group {group_id} data must be 2D, got shape={group_data.shape}")
                if group_data.shape[1] != len(group.columns):
                    raise ValueError(
                        f"Group {group_id} columns mismatch: expected {len(group.columns)}, got {group_data.shape[1]}"
                    )

                staged_path = staging_dir / f"{group_id}.parquet"
                final_path = output_dir / f"{group_id}.parquet"
                group_frame = pd.DataFrame(group_data, columns=list(group.columns), copy=False)
                group_frame.to_parquet(staged_path, index=False, compression="gzip")
                staged_pairs.append((group_id, staged_path, final_path))

            for group_id, staged_path, final_path in staged_pairs:
                os.replace(staged_path, final_path)
                resolved_path = str(final_path.resolve())
                persisted_paths.append(resolved_path)
                parquet_path_map[group_id] = resolved_path

            if parquet_path_map:
                registry.set_group_parquet_paths(parquet_path_map)

            if cleanup_intermediate:
                removed_count = 0
                for _, group in registry.iter_all():
                    if group.disk_path and group.disk_path.exists():
                        group.disk_path.unlink()
                        removed_count += 1
                self.logger.info(
                    "CGSA intermediate .npy cleanup completed: %d files removed",
                    removed_count,
                )

            self.logger.info(
                "CGSA per-group parquet persist completed: symbol=%s config_hash=%s groups=%d",
                symbol,
                config_hash,
                len(persisted_paths),
            )
            return persisted_paths
        except Exception as e:
            self.logger.error(
                "CGSA per-group parquet persist failed: symbol=%s config_hash=%s error=%s",
                symbol,
                config_hash,
                str(e),
                exc_info=True,
            )
            raise
        finally:
            if staging_dir.exists():
                for child in staging_dir.iterdir():
                    if child.is_file():
                        child.unlink()
                staging_dir.rmdir()

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
