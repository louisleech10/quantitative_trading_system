"""Feature run identity and canonical path helpers."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from momentum.FeatureEngineering.feature_storage import FeatureStorage


_CONFIG_HASH_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def validate_config_hash(token: str) -> str:
    """驗證可安全作為 run identity 的 config hash。"""
    if not _CONFIG_HASH_PATTERN.fullmatch(token) or set(token) == {"."}:
        raise ValueError(f"Invalid config hash: {token!r}")
    return token


def safe_token(text: str) -> str:
    """依既有 CGSA 規則清理檔名 token。"""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def features_run_dir(root: Path, symbol: str, timeframe: str, config_hash: str) -> Path:
    """回傳 FeatureStorage canonical run 目錄，不執行 IO。"""
    validate_config_hash(config_hash)
    storage = FeatureStorage.__new__(FeatureStorage)
    storage.base_path = Path(root)
    return storage.feature_run_dir(symbol, timeframe, config_hash)


#: `config_hash` 為空時之層名後綴（無法建立身分 ⇒ 一律全新、不續跑；NUMVIEW D7 ④）
NOHASH_TOKEN = "nohash"


def cgsa_config_layer_dir(root: Path, symbol: str, timeframe: str, config_hash: str) -> Path:
    """CGSA 工作目錄之 `<root>/<symbol>_<tf>_<完整 config_hash>` 層（NUMVIEW D7；run 刪除單位）；不執行 IO。"""
    token = validate_config_hash(config_hash) if config_hash else NOHASH_TOKEN
    return (Path(root).expanduser() / f"{safe_token(symbol)}_{safe_token(timeframe)}_{token}").resolve()


def cgsa_work_dir(root: Path, symbol: str, timeframe: str, config_hash: str, algorithm_id: str) -> Path:
    """CGSA 工作目錄葉＝`cgsa_config_layer_dir(...)/<完整 algorithm_id>`（NUMVIEW D7；`FFACT_CGSA_WORK_DIR` 一律為
    `root`）；不執行 IO。`algorithm_id` 須為非空之檔名安全字串。"""
    if not algorithm_id or safe_token(algorithm_id) != algorithm_id or set(algorithm_id) == {"."}:
        raise ValueError(f"Invalid algorithm_id: {algorithm_id!r}")
    return cgsa_config_layer_dir(root, symbol, timeframe, config_hash) / algorithm_id


def utc_stamp() -> str:
    """UTC 時間戳（`.stale-` 目錄名與標記檔時間之唯一來源）。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _atomic_write_json(path: Path, payload: Mapping[str, Any], tmp_dir: Optional[Path] = None) -> Path:
    """暫存檔（預設同目錄；`tmp_dir` 須同一檔案系統）寫入後 `os.replace`；失敗（含 `OSError`）原樣上拋並清除暫存檔。"""
    tmp = Path(tmp_dir or path.parent) / f".{path.parent.name}.{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise
    return path


def write_route_switch_marker(work_dir: Path, entry: Mapping[str, Any]) -> Path:
    """未認證換臂標記檔（NUMVIEW Task 4.1 R6-A；檔名與鍵讀契約 `cgsa_work_identity.marker_file／marker_keys`）：
    原子寫入 `work_dir`；`time` 缺則補 UTC 時間戳。寫入失敗之例外原樣上拋（R7-B）。"""
    from momentum.FeatureEngineering import numeric_view

    section = numeric_view.load_contract()["cgsa_work_identity"]
    payload = {key: entry.get(key) for key in section["marker_keys"]}
    if payload.get("time") is None:
        payload["time"] = utc_stamp()
    return _atomic_write_json(Path(work_dir) / section["marker_file"], payload)


def _cgsa_identity_section() -> Mapping[str, Any]:
    from momentum.FeatureEngineering import numeric_view

    return numeric_view.load_contract()["cgsa_work_identity"]


def cgsa_identity_payload(symbol: str, timeframe: str, config_hash: str, algorithm_id: str) -> Dict[str, str]:
    """CGSA 葉身分檔內容（NUMVIEW D7；鍵＝契約 `cgsa_work_identity.identity_keys`）。"""
    values = {"symbol": symbol, "tf": timeframe, "config_hash": config_hash, "algorithm_id": algorithm_id}
    keys = list(_cgsa_identity_section()["identity_keys"])
    if set(keys) != set(values):
        raise ValueError(f"契約 cgsa_work_identity.identity_keys {keys} ≠ D7 四鍵")
    return {key: values[key] for key in keys}


def read_cgsa_identity(leaf: Path) -> Optional[Dict[str, Any]]:
    """只讀葉之身分檔；缺、空、非 JSON 或非物件 ⇒ None（視同不符；D7 ③、邊界③）。"""
    path = Path(leaf) / _cgsa_identity_section()["identity_file"]
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def has_route_switch_marker(leaf: Path) -> bool:
    """葉內是否有未認證換臂標記檔（只 stat，不讀內容；R6-A）。"""
    return (Path(leaf) / _cgsa_identity_section()["marker_file"]).exists()


def write_cgsa_identity(leaf: Path, payload: Mapping[str, Any]) -> Path:
    """原子寫葉之身分檔；暫存檔置於上一層（層目錄），葉內除身分檔外無任何開檔。"""
    leaf = Path(leaf)
    return _atomic_write_json(leaf / _cgsa_identity_section()["identity_file"], payload, tmp_dir=leaf.parent)


def move_to_stale(leaf: Path) -> Path:
    """葉目錄改名移出為 `<葉>.stale-<UTC 時間>`（只 rename、不讀內容）；目的名已存在 ⇒ 加序號，不覆蓋（邊界④）。"""
    leaf = Path(leaf)
    base = f"{leaf.name}.stale-{utc_stamp()}"
    target = leaf.with_name(base)
    sequence = 0
    while target.exists() or target.is_symlink():
        sequence += 1
        target = leaf.with_name(f"{base}-{sequence}")
    os.rename(leaf, target)
    return target
