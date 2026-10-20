"""FeatureLibrary - unified read-only interface for consuming generated features."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from momentum.core.contracts import FeatureLibraryEntry, FeatureNotFoundError
from momentum.core.logging import get_logger
from momentum.FeatureEngineering.consumer_gate import (
    TrainingReadError,
    assert_consumer_run_status,
    assert_required_columns_present,
)
from momentum.FeatureEngineering import feature_naming
from momentum.FeatureEngineering import run_provenance
from momentum.FeatureEngineering.run_provenance import RunIdentity
from momentum.FeatureEngineering.feature_reader import CanonicalRun, FeatureReader, resolve_canonical_run
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage

logger = get_logger(__name__)


class FeatureLibrary:
    """Read-only facade for accessing generated features.

    只經 FeatureReader 讀 V2 run（feature_manifest.json）；無可讀 V2 run ⇒ FeatureNotFoundError。
    """

    def __init__(
        self,
        registry: FeatureRegistry,
        storage: FeatureStorage,
        feature_reader: Optional[FeatureReader] = None,
    ) -> None:
        self._registry = registry
        self._storage = storage
        self._reader = feature_reader or FeatureReader(str(storage.base_path))

    def list_available(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> List[FeatureLibraryEntry]:
        """List all available feature sets, optionally filtered."""
        entries = self._registry.list_all()
        if symbol:
            entries = [entry for entry in entries if entry.get("symbol") == symbol]
        if timeframe:
            entries = [entry for entry in entries if entry.get("timeframe") == timeframe]
        return [self._to_entry(entry) for entry in entries]

    def reload_registry(self) -> None:
        """重讀 registry（長壽命 service 於每次解析 run 前呼叫，避免看不到啟動後新生成的 run）。"""
        self._registry.reload()

    def get_entry(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """無寫方法的轉發 façade；不承諾回傳物 immutability。

        ``FeatureRegistry.get`` 回傳 copy；本方法維持底層既有語意，
        不額外轉換、過濾或加上 defensive copy。
        """
        return self._registry.get(symbol, timeframe, config_hash)

    def find_latest_materialized(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[Dict[str, Any]]:
        """無寫方法的轉發 façade；不承諾回傳物 immutability。

        底層目前回傳 registry 內部 dict，mutable leak 是既有現況；
        本零行為變更票不加 defensive copy。
        """
        return self._registry.find_latest_materialized(symbol, timeframe)

    def load(
        self,
        symbol: str,
        timeframe: str,
        *,
        config_hash: Optional[str] = None,
        for_training: bool = False,
        allow_partial_training: bool = False,
    ) -> pd.DataFrame:
        """Load latest features for a symbol/timeframe pair.

        只讀 V2（FeatureReader）；無可讀 V2 run ⇒ FeatureNotFoundError。
        """
        features_df, _manifest = self._load_internal(
            symbol,
            timeframe,
            config_hash=config_hash,
            for_training=for_training,
            allow_partial_training=allow_partial_training,
        )
        return features_df

    def load_with_identity(
        self,
        symbol: str,
        timeframe: str,
        *,
        config_hash: Optional[str] = None,
        for_training: bool = False,
        allow_partial_training: bool = False,
    ) -> Tuple[pd.DataFrame, RunIdentity]:
        """FFDSTAR Task 2.1：同 `load`（參數與 DataFrame 逐位元相同），另回 run 身分。

        身分取自本次讀取據以判定可讀與 consumer 政策之**同一次** manifest 解析（`load_manifest_v2` 所回者），不另解析；
        `config_hash` 未指定 ⇒ 先依 registry 解析 latest，身分之 `config_hash` 為解析後之真值。舊 run（無
        `content_sha256`）⇒ 身分 `legacy`（呼叫端快取不得沿用）。"""
        features_df, manifest = self._load_internal(
            symbol,
            timeframe,
            config_hash=config_hash,
            for_training=for_training,
            allow_partial_training=allow_partial_training,
        )
        return features_df, run_provenance.resolve_run_identity(manifest, "raw")

    def load_for_training(
        self,
        symbol: str,
        timeframe: str,
        *,
        allow_partial_training: bool = False,
    ) -> pd.DataFrame:
        """Strict consumer load for ML/training paths."""
        features_df, _manifest = self._load_internal(
            symbol,
            timeframe,
            for_training=True,
            allow_partial_training=allow_partial_training,
        )
        return features_df

    def _load_internal(
        self,
        symbol: str,
        timeframe: str,
        *,
        config_hash: Optional[str] = None,
        for_training: bool,
        allow_partial_training: bool,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """回 (特徵, 本次讀取之 manifest)；manifest 為 `load_manifest_v2` 之同一次解析（FFDSTAR Task 2.1 身分來源）。"""
        if config_hash:
            entry = self._registry.get(symbol, timeframe, config_hash)
            if entry is None:
                raise FeatureNotFoundError(
                    symbol,
                    timeframe,
                    f"config_hash not found: {config_hash}",
                )
        else:
            entry = self._registry.find_latest_materialized(symbol, timeframe)
            if entry is None:
                raise FeatureNotFoundError(
                    symbol,
                    timeframe,
                    "No materialized registry entry",
                )

        resolved_hash = entry.get("config_hash", "")
        explicit_hash = bool(config_hash)

        if resolved_hash:
            try:
                manifest = self._reader.load_manifest_v2(
                    symbol,
                    timeframe,
                    resolved_hash,
                    artifact_kind="raw",
                    consumer="strict" if for_training else "browse",
                    allow_partial=allow_partial_training,
                )
                columns = self._reader.list_features_v2(
                    symbol,
                    timeframe,
                    resolved_hash,
                    artifact_kind="raw",
                    consumer="strict" if for_training else "browse",
                    allow_partial=allow_partial_training,
                )
                if columns:
                    features_df = self._reader.load_columns_v2(
                        symbol,
                        timeframe,
                        resolved_hash,
                        columns,
                        artifact_kind="raw",
                        consumer="strict" if for_training else "browse",
                        allow_partial=allow_partial_training,
                    )
                    if not features_df.empty:
                        if for_training:
                            assert_consumer_run_status(
                                manifest,
                                consumer="strict",
                                allow_partial=allow_partial_training,
                                error_type=TrainingReadError,
                            )
                        self._attach_row_index(
                            symbol, timeframe, resolved_hash, features_df
                        )
                        logger.info(
                            "Loaded features via FeatureReader for %s/%s: %d rows x %d cols "
                            "(run_status=%s)",
                            symbol,
                            timeframe,
                            len(features_df),
                            len(features_df.columns),
                            manifest.get("run_status", manifest.get("quality_status")),
                        )
                        return features_df, manifest
            except FileNotFoundError:
                if explicit_hash:
                    raise FeatureNotFoundError(
                        symbol,
                        timeframe,
                        f"V2 artifacts missing for config_hash: {resolved_hash}",
                    ) from None

        # FRAMEPATH Task 2.2：只讀 V2；無可讀 V2 run 即 FeatureNotFoundError（舊特徵檔後備已刪）
        raise FeatureNotFoundError(
            symbol,
            timeframe,
            f"artifacts missing for config_hash: {resolved_hash}",
        )

    def _attach_row_index(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        df: pd.DataFrame,
    ) -> None:
        """貼回 V2 持久化的主時間軸(row_index sidecar)。

        鏡像 ``feature_factory_service._attach_cgsa_row_index``:manifest 無
        ``row_index``(舊 run)→ no-op 維持原 index;長度不符 → 拒絕靜默貼錯位。
        只改 ``df.index``,不動任何特徵值/欄位/列數。
        """
        row_index = self._reader.load_row_index_v2(
            symbol, timeframe, config_hash, artifact_kind="raw"
        )
        if row_index is None:
            return
        if len(row_index) != len(df):
            raise ValueError(
                f"row_index length mismatch for {symbol}/{timeframe}/{config_hash}: "
                f"{len(row_index)} != {len(df)}"
            )
        df.index = row_index
        df.index.name = "timestamp"

    def load_multi(
        self,
        symbols: List[str],
        timeframe: str,
        *,
        config_hashes: Optional[Dict[str, str]] = None,
        for_training: bool = False,
        allow_partial_training: bool = False,
        feature_columns: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Load features for multiple symbols. Raises if any symbol is missing.

        FF-NAME Task 3.4：載入任何矩陣前，各標的 manifest（經 reader 共同邊界）之命名世代須一致
        （`assert_single_feature_naming_version`），混世代 ⇒ `FeatureNamingVersionError`。
        """
        for symbol in symbols:
            if config_hashes is not None and symbol not in config_hashes:
                logger.warning(
                    "config_hashes missing symbol %s/%s; falling back to find_latest",
                    symbol,
                    timeframe,
                )
        manifests = self.load_manifests_for_merge(symbols, timeframe, config_hashes=config_hashes)
        if manifests:
            feature_naming.assert_single_feature_naming_version(manifests)
        loaded: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            symbol_hash = (config_hashes or {}).get(symbol)
            loaded[symbol] = self.load(
                symbol,
                timeframe,
                config_hash=symbol_hash,
                for_training=for_training,
                allow_partial_training=allow_partial_training,
            )
        if feature_columns:
            assert_required_columns_present(loaded, feature_columns, error_type=TrainingReadError)
        return loaded

    def load_manifests_for_merge(
        self,
        symbols: List[str],
        timeframe: str,
        *,
        config_hashes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """多標的合併點之 manifest 蒐集（FF-NAME Task 3.4）：每標的依 `load` 同一解析規則取 run，經 reader 共同
        邊界讀 manifest（只過命名世代閘，不讀矩陣；consumer 政策仍由後續 `load` 判定）。無 registry 條目或 V2 檔缺
        之標的略過——其錯誤由後續 `load` 以原有例外拋出；回傳 {symbol: manifest} 供
        `assert_single_feature_naming_version`。"""
        manifests: Dict[str, Dict[str, Any]] = {}
        for symbol in symbols:
            symbol_hash = (config_hashes or {}).get(symbol)
            entry = (
                self._registry.get(symbol, timeframe, symbol_hash)
                if symbol_hash
                else self._registry.find_latest_materialized(symbol, timeframe)
            )
            resolved_hash = (entry or {}).get("config_hash", "")
            if not resolved_hash:
                continue
            try:
                manifests[symbol] = self._reader.load_run_manifest_v2(symbol, timeframe, resolved_hash)
            except FileNotFoundError:
                continue
        return manifests

    def resolve_canonical_run(self, path: Any) -> CanonicalRun:
        """特徵檔路徑 → canonical run（特徵根＝本 library 之 storage 根；registry 須有條目）；否則
        `NonCanonicalFeaturePathError`（不開啟任何檔，FF-NAME Task 3.4）。"""
        return resolve_canonical_run(path, feature_root=self._storage.base_path, registry_get=self._registry.get)

    def load_canonical_path(
        self,
        path: Any,
        *,
        for_training: bool = False,
        allow_partial_training: bool = False,
    ) -> pd.DataFrame:
        """以特徵檔路徑載入：先解析為 canonical run 再經 `load`（任意 `.parquet`／`.h5` 一律拒收）。"""
        run = self.resolve_canonical_run(path)
        return self.load(
            run.symbol,
            run.timeframe,
            config_hash=run.config_hash,
            for_training=for_training,
            allow_partial_training=allow_partial_training,
        )

    def ensure_fresh(self, symbol: str, timeframe: str, current_config_hash: str) -> bool:
        """Return whether latest cached entry matches given config hash."""
        entry = self._registry.find_latest_materialized(symbol, timeframe)
        if entry is None:
            return False
        return entry.get("config_hash") == current_config_hash

    @staticmethod
    def _to_entry(raw: Dict) -> FeatureLibraryEntry:
        return FeatureLibraryEntry(
            symbol=raw.get("symbol", ""),
            timeframe=raw.get("timeframe", ""),
            config_hash=raw.get("config_hash", ""),
            feature_count=raw.get("feature_count", 0),
            row_count=raw.get("row_count", 0),
            created_at=raw.get("created_at", 0.0),
            hdf5_relative_path=raw.get("hdf5_relative_path", ""),
        )
