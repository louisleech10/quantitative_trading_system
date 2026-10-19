"""特徵產出之逐欄執行紀錄（provenance）與 run 身分之單一實作（docs/FFDSTAR_SPEC.md Task 1.3／1.5／2.1）。

純函式、無狀態：紀錄表組裝與窮盡性檢查、紀錄檔寫讀與 sha256 驗證、run 內容身分 `content_sha256` 之計算、
自 manifest 解析 run 身分物件。欄位、狀態值集、manifest `provenance` 物件與 run 身分之鍵一律取自契約
`momentum/FeatureEngineering/contracts/run_provenance.json`（SPEC §C 契約單一真相源），本模組不另列舉。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import pandas as pd

CONTRACT_PATH: Path = Path(__file__).resolve().parent / "contracts" / "run_provenance.json"


class ProvenanceError(RuntimeError):
    """逐欄紀錄之共同基底錯誤（SPEC Task 1.2／1.3／1.5）。"""


class ProvenanceConflictError(ProvenanceError):
    """同鍵紀錄合併時值不逐項相同（SPEC Task 1.2；改前為後寫勝）。"""


class ProvenanceExhaustivenessError(ProvenanceError):
    """紀錄之輸出欄名集合 ≠ manifest 群組欄聯集 ∪ dead-drop 欄，或有重複（SPEC Task 1.3 ②）。"""


class ProvenanceMissingError(ProvenanceError):
    """manifest artifact 節點無 `provenance` 物件（舊 run；SPEC Task 1.5、§C D6）。"""


class ProvenanceIntegrityError(ProvenanceError):
    """紀錄檔缺、路徑逃逸 run 目錄、sha256 或契約版本不符（SPEC Task 1.5）。"""


@dataclasses.dataclass(frozen=True)
class ContentEntry:
    """`content_sha256` 之一個組成項（SPEC Task 1.3 ③；排序與序列化方式見契約）。"""

    relative_path: str
    columns: Tuple[str, ...]
    row_count: int
    dtype: str
    file_sha256: str


@dataclasses.dataclass(frozen=True)
class ProvenancePointer:
    """manifest artifact 節點之 `provenance` 物件（鍵見契約；SPEC Task 1.3 ⑦）。"""

    path: str
    sha256: str
    row_count: int
    contract_version: int
    summary: Mapping[str, Any]
    groups: Mapping[str, Mapping[str, Any]]


@dataclasses.dataclass(frozen=True)
class RunIdentity:
    """IC 讀取之 run 身分（SPEC Task 2.1；鍵見契約）。`content_sha256` 為 None ⇒ 舊 run（legacy），快取不得沿用。"""

    symbol: str
    tf: str
    config_hash: str
    feature_schema_hash: Optional[str]
    feature_naming_version: int
    artifact_kind: str
    content_sha256: Optional[str]
    provenance_sha256: Optional[str]

    @property
    def legacy(self) -> bool:
        raise NotImplementedError("FFDSTAR Task 2.1")

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("FFDSTAR Task 2.1")


def load_contract() -> Dict[str, Any]:
    """讀契約 JSON（SPEC Task 1.1）。"""
    raise NotImplementedError("FFDSTAR Task 1.1")


def build_provenance_table(
    records: Mapping[Tuple[str, str], Mapping[str, Any]],
    *,
    output_columns: Sequence[str],
    column_group: Mapping[str, str],
    dropped_columns: Mapping[str, str],
) -> pd.DataFrame:
    """由前處理器之 run 層級紀錄（鍵＝(原生週期, L6.5 所見欄名)）組逐欄紀錄表，鍵換為落盤欄名
    （FF-NAME `tag_timeframe`）；dead-drop 欄記終態（SPEC Task 1.3 ②）。"""
    raise NotImplementedError("FFDSTAR Task 1.3")


def check_exhaustive(
    table: pd.DataFrame,
    manifest_columns: Iterable[str],
    dropped_columns: Iterable[str],
) -> None:
    """紀錄輸出欄名集合須逐名等於 manifest 群組欄聯集 ∪ dead-drop 欄且無重複，否則拋
    `ProvenanceExhaustivenessError`（SPEC Task 1.3 ②、§V oracle ①）。"""
    raise NotImplementedError("FFDSTAR Task 1.3")


def file_sha256(path: Path) -> str:
    """檔案位元組之 sha256（串流讀，不整檔載入）。"""
    raise NotImplementedError("FFDSTAR Task 1.3")


def compute_content_sha256(entries: Sequence[ContentEntry], row_index_sha256: str) -> str:
    """run 內容身分（SPEC Task 1.3 ③；與 `config_hash`、`feature_schema_hash` 正交）。"""
    raise NotImplementedError("FFDSTAR Task 1.3")


def write_provenance_table(
    table: pd.DataFrame,
    staging_dir: Path,
    artifact_kind: str,
    groups: Mapping[str, Mapping[str, Any]],
) -> ProvenancePointer:
    """以 zstd parquet 寫紀錄檔至暫存 `provenance/`，回 manifest 用之指標（SPEC Task 1.3 ④、1.4）。
    寫入失敗一律上拋（不得吞例外）。"""
    raise NotImplementedError("FFDSTAR Task 1.3")


def read_provenance_table(run_dir: Path, pointer: Mapping[str, Any]) -> pd.DataFrame:
    """依 manifest 宣告讀紀錄檔：存在、路徑在 run 內、sha256 與契約版本相符，否則拋
    `ProvenanceIntegrityError`；不重算特徵檔雜湊（SPEC Task 1.5）。"""
    raise NotImplementedError("FFDSTAR Task 1.5")


def resolve_run_identity(manifest: Mapping[str, Any], artifact_kind: str) -> RunIdentity:
    """自同一次 manifest 解析取 run 身分（SPEC Task 2.1）。"""
    raise NotImplementedError("FFDSTAR Task 2.1")
