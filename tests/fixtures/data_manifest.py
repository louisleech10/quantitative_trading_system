"""DATA_MANIFEST 校驗器：比對真實 kline 指紋與凍結 manifest。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py

from momentum.factories import create_kline_storage_manager

MANIFEST_PATH = Path(__file__).resolve().parent / "DATA_MANIFEST.json"
DEFAULT_CACHE_DIR = "data_cache/feature_klines"
EXPECTED_TIMEFRAMES = frozenset({"1h", "4h", "12h"})


@dataclass(frozen=True)
class ManifestEntry:
    """單一 symbol×TF 的 manifest 條目。"""

    symbol: str
    timeframe: str
    min_row_count: int
    sha256: str


@dataclass(frozen=True)
class DatasetFingerprint:
    """實際 kline dataset 指紋。"""

    symbol: str
    timeframe: str
    row_count: int
    sha256: str


class ManifestValidationError(Exception):
    """Manifest 與實際 kline 不一致。"""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def load_manifest(manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    """載入 DATA_MANIFEST.json。"""
    path = manifest_path or MANIFEST_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def parse_manifest_entries(manifest: Dict[str, Any]) -> List[ManifestEntry]:
    """解析 manifest entries 為結構化列表。"""
    entries: List[ManifestEntry] = []
    for raw in manifest.get("entries", []):
        entries.append(
            ManifestEntry(
                symbol=str(raw["symbol"]),
                timeframe=str(raw["timeframe"]),
                min_row_count=int(raw["min_row_count"]),
                sha256=str(raw["sha256"]),
            )
        )
    return entries


def resolve_h5_path(
    cache_dir: str = DEFAULT_CACHE_DIR,
    h5_file: str = "kline_cache.h5",
    manifest: Optional[Dict[str, Any]] = None,
) -> Path:
    """解析 kline h5 路徑。"""
    if manifest is not None:
        cache_dir = str(manifest.get("cache_dir", cache_dir))
        h5_file = str(manifest.get("h5_file", h5_file))
    return Path(cache_dir) / h5_file


def compute_dataset_fingerprint(
    symbol: str,
    timeframe: str,
    *,
    cache_dir: str = DEFAULT_CACHE_DIR,
    h5_path: Optional[Path] = None,
) -> DatasetFingerprint:
    """計算單一 symbol×TF 的 row_count 與 sha256（h5py structured array bytes）。"""
    path = h5_path or resolve_h5_path(cache_dir=cache_dir)
    if not path.is_file():
        raise FileNotFoundError(f"kline cache file not found: {path}")

    dataset_path = f"/{symbol}/{timeframe}/data"
    with h5py.File(path, "r") as handle:
        if symbol not in handle or timeframe not in handle[symbol]:
            raise KeyError(f"missing dataset {symbol}/{timeframe} in {path}")
        dataset = handle[symbol][timeframe]["data"]
        raw = dataset[()].tobytes()
        row_count = len(dataset)

    return DatasetFingerprint(
        symbol=symbol,
        timeframe=timeframe,
        row_count=row_count,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def list_actual_datasets(
    *,
    cache_dir: str = DEFAULT_CACHE_DIR,
    h5_path: Optional[Path] = None,
) -> Dict[str, List[str]]:
    """列出實際 h5 內 symbol→timeframes（僅 1h/4h/12h）。"""
    storage = create_kline_storage_manager(cache_dir=cache_dir)
    index = storage.get_cache_index()
    filtered: Dict[str, List[str]] = {}
    for symbol, timeframes in index.items():
        if symbol.startswith("_"):
            continue
        kept = sorted(tf for tf in timeframes if tf in EXPECTED_TIMEFRAMES)
        if kept:
            filtered[symbol] = kept
    if filtered:
        return filtered

    path = h5_path or resolve_h5_path(cache_dir=cache_dir)
    if not path.is_file():
        return {}
    with h5py.File(path, "r") as handle:
        for symbol in sorted(handle.keys()):
            if symbol.startswith("_"):
                continue
            kept = sorted(
                tf
                for tf in handle[symbol].keys()
                if tf in EXPECTED_TIMEFRAMES and "data" in handle[symbol][tf]
            )
            if kept:
                filtered[symbol] = kept
    return filtered


def validate_manifest(
    *,
    cache_dir: str = DEFAULT_CACHE_DIR,
    manifest_path: Optional[Path] = None,
    manifest: Optional[Dict[str, Any]] = None,
) -> None:
    """校驗 manifest 與實際 kline；不一致時拋 ManifestValidationError。"""
    doc = manifest if manifest is not None else load_manifest(manifest_path)
    entries = parse_manifest_entries(doc)
    effective_cache_dir = str(doc.get("cache_dir", cache_dir))
    h5_path = resolve_h5_path(manifest=doc)

    if not h5_path.is_file():
        raise ManifestValidationError([f"missing kline cache file: {h5_path}"])

    errors: List[str] = []
    manifest_keys = {(e.symbol, e.timeframe) for e in entries}
    actual_index = list_actual_datasets(cache_dir=effective_cache_dir, h5_path=h5_path)
    actual_keys = {
        (symbol, tf)
        for symbol, timeframes in actual_index.items()
        for tf in timeframes
    }

    for symbol, timeframe in sorted(manifest_keys - actual_keys):
        errors.append(f"manifest entry missing in kline cache: {symbol}/{timeframe}")

    for symbol, timeframe in sorted(actual_keys - manifest_keys):
        errors.append(f"kline cache dataset missing from manifest: {symbol}/{timeframe}")

    for entry in entries:
        try:
            fp = compute_dataset_fingerprint(
                entry.symbol,
                entry.timeframe,
                cache_dir=effective_cache_dir,
                h5_path=h5_path,
            )
        except (FileNotFoundError, KeyError) as exc:
            errors.append(f"{entry.symbol}/{entry.timeframe}: {exc}")
            continue

        if fp.row_count < entry.min_row_count:
            errors.append(
                f"{entry.symbol}/{entry.timeframe}: row_count {fp.row_count} "
                f"< min_row_count {entry.min_row_count}"
            )
        if fp.sha256 != entry.sha256:
            errors.append(
                f"{entry.symbol}/{entry.timeframe}: sha256 mismatch "
                f"(expected {entry.sha256}, got {fp.sha256})"
            )

    return _raise_if_errors(errors)


def verify_kline_entry(
    symbol: str,
    timeframe: str,
    *,
    cache_dir: str = DEFAULT_CACHE_DIR,
    manifest_path: Optional[Path] = None,
    min_rows: Optional[int] = None,
) -> DatasetFingerprint:
    """校驗單一 symbol×TF；失敗拋 ManifestValidationError 或 FileNotFoundError。"""
    doc = load_manifest(manifest_path)
    entries = {
        (e.symbol, e.timeframe): e for e in parse_manifest_entries(doc)
    }
    key = (symbol, timeframe)
    if key not in entries:
        raise ManifestValidationError([f"no manifest entry for {symbol}/{timeframe}"])

    entry = entries[key]
    effective_cache_dir = str(doc.get("cache_dir", cache_dir))
    h5_path = resolve_h5_path(manifest=doc)
    fp = compute_dataset_fingerprint(
        symbol,
        timeframe,
        cache_dir=effective_cache_dir,
        h5_path=h5_path,
    )

    errors: List[str] = []
    required_rows = min_rows if min_rows is not None else entry.min_row_count
    if fp.row_count < required_rows:
        errors.append(
            f"{symbol}/{timeframe}: row_count {fp.row_count} < required {required_rows}"
        )
    if fp.sha256 != entry.sha256:
        errors.append(
            f"{symbol}/{timeframe}: sha256 mismatch "
            f"(expected {entry.sha256}, got {fp.sha256})"
        )
    _raise_if_errors(errors)
    return fp


def _raise_if_errors(errors: List[str]) -> None:
    if errors:
        raise ManifestValidationError(errors)
