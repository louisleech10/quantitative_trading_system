"""特徵產出之逐欄執行紀錄（provenance）與 run 身分之單一實作（docs/FFDSTAR_SPEC.md Task 1.3／1.5／2.1）。

純函式、無狀態：紀錄表組裝與窮盡性檢查、紀錄檔寫讀與 sha256 驗證、run 內容身分 `content_sha256` 之計算、
自 manifest 解析 run 身分物件。欄位、狀態值集、manifest `provenance` 物件與 run 身分之鍵一律取自契約
`momentum/FeatureEngineering/contracts/run_provenance.json`（SPEC §C 契約單一真相源），本模組不另列舉。

本模組不寫任何狀態值字面：值一律由寫入路徑（`feature_preprocessor.py`、`feature_storage.py`）之紀錄呼叫帶入
（契約 `_sources` 指向該等呼叫點）；本模組只依契約驗值、組表與序列化。
"""

from __future__ import annotations

import dataclasses
import functools
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from momentum.FeatureEngineering import feature_naming

CONTRACT_PATH: Path = Path(__file__).resolve().parent / "contracts" / "run_provenance.json"

#: 契約 `record_columns` 之型別字面 → Arrow 型別（`enum:<值集>` 一律為字串）
_ARROW_TYPES: Dict[str, Any] = {
    "str": pa.string(),
    "float64": pa.float64(),
    "int64": pa.int64(),
    "bool": pa.bool_(),
    "list<str>": pa.list_(pa.string()),
}
#: 平穩化決策欄（逐欄紀錄中只對實際進入平穩化步驟之輸入欄非空；SPEC §K K-2 040）
_DECISION_FIELDS: Tuple[str, ...] = (
    "adf_pvalue", "n", "calibration_start", "calibration_end", "fracdiff", "d", "adf_differenced", "dstar_source",
)


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

    def to_manifest(self) -> Dict[str, Any]:
        """manifest `provenance` 物件（鍵＝契約 `manifest_provenance_keys`，依契約順序）。"""
        values = {
            "path": str(self.path),
            "sha256": str(self.sha256),
            "row_count": int(self.row_count),
            "contract_version": int(self.contract_version),
            "summary": json.loads(json.dumps(dict(self.summary), default=str)),
            "groups": json.loads(json.dumps({str(k): dict(v) for k, v in dict(self.groups).items()}, default=str)),
        }
        return {key: values[key] for key in load_contract()["manifest_provenance_keys"]}


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
        """舊 run（artifact 節點無 `content_sha256`；§C D6）⇒ True：IC 快取一律不沿用。"""
        return self.content_sha256 is None

    def to_dict(self) -> Dict[str, Any]:
        """身分物件（鍵與順序＝契約 `run_identity_keys`；一切輸出中之鍵名為 `ff_run_identity`）。
        本型別欄位集合須恰等於契約鍵集，否則拋 `ProvenanceError`（契約為唯一真相源，不得靜默增減）。"""
        values = dataclasses.asdict(self)
        keys = list(load_contract()["run_identity_keys"])
        if set(keys) != set(values):
            raise ProvenanceError(f"RunIdentity 欄位 {sorted(values)} ≠ 契約 run_identity_keys {sorted(keys)}")
        return {key: values[key] for key in keys}


# ---------------------------------------------------------------------------------------------- 契約


def load_contract() -> Dict[str, Any]:
    """讀契約 JSON（SPEC Task 1.1；每次讀檔，不另組、不快取）。"""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def contract_value_set(contract: Mapping[str, Any], path: str) -> List[str]:
    """契約值集路徑（如 `step_status_values.winsorization`）之值清單。"""
    node: Any = contract
    for part in str(path).split("."):
        node = node[part]
    return [str(v) for v in node["values"]]


@functools.lru_cache(maxsize=1)
def _record_field_names() -> Tuple[str, ...]:
    """契約 `record_columns` 去 `output_column`（逐欄紀錄於熱路徑建立，欄位名於行程內讀契約一次）。"""
    return tuple(name for name in load_contract()["record_columns"] if name != "output_column")


def new_execution_record(timeframe: str, layer: Optional[str], group_id: Optional[str]) -> Dict[str, Any]:
    """一欄執行紀錄之空白形（鍵＝契約 `record_columns` 去 `output_column`；步驟狀態與終態未定為 None）。"""
    record: Dict[str, Any] = dict.fromkeys(_record_field_names())
    record.update({"native_timeframe": str(timeframe), "layer": layer, "group_id": group_id, "events": []})
    return record


# ---------------------------------------------------------------------------------------------- 寫入端紀錄（storage 呼叫）


def record_terminal(terminals: MutableMapping[str, str], columns: Iterable[str], value: str) -> None:
    """記落盤欄名之終態（寫入端；同名不同值 ⇒ `ProvenanceConflictError`，同值冪等）。"""
    for column in columns:
        name = str(column)
        previous = terminals.get(name)
        if previous is not None and previous != value:
            raise ProvenanceConflictError(f"欄 {name} 之終態衝突：{previous!r} ≠ {value!r}")
        terminals[name] = str(value)


def record_all_steps(
    records: MutableMapping[Tuple[str, str], Dict[str, Any]],
    keys: Iterable[Tuple[str, str]],
    value: str,
    *,
    layer: Optional[str],
    group_id: Optional[str],
) -> None:
    """記一批 (原生週期, L6.5 所見欄名) 之全部步驟狀態為同一值（前處理總開關關閉時之寫入端紀錄；同鍵冪等、異值拒收）。"""
    steps = list(load_contract()["steps"])
    for timeframe, column in keys:
        key = (str(timeframe), str(column))
        record = records.get(key)
        if record is None:
            record = new_execution_record(key[0], layer, group_id)
            records[key] = record
        for step in steps:
            if record.get(step) is not None and record[step] != value:
                raise ProvenanceConflictError(f"{key} 之 {step} 狀態衝突：{record[step]!r} ≠ {value!r}")
            record[step] = str(value)


def record_group(
    groups: MutableMapping[str, Dict[str, Any]],
    group_id: str,
    *,
    arm: Optional[str] = None,
    status: Optional[str] = None,
    fallback: Optional[str] = None,
    failure_reason: Optional[str] = None,
    override_status: bool = False,
) -> None:
    """記群組表一列：臂與狀態先寫者為準（`override_status` ⇒ 狀態以本次為準，如寫入端判定群組全被 dead-drop）、
    回退依發生序附加。"""
    entry = groups.setdefault(str(group_id), {"arm": None, "fallback": [], "status": None, "failure_reason": None})
    if arm is not None and entry.get("arm") is None:
        entry["arm"] = str(arm)
    if status is not None and (override_status or entry.get("status") is None):
        entry["status"] = str(status)
    if fallback is not None:
        entry.setdefault("fallback", []).append(str(fallback))
    if failure_reason is not None:
        entry["failure_reason"] = str(failure_reason)


def merge_groups(into: MutableMapping[str, Dict[str, Any]], more: Mapping[str, Mapping[str, Any]]) -> None:
    """群組表合併：`more` 之回退依序接於 `into` 之後；臂、狀態先寫者為準；失敗原因取後者（非空時）。"""
    for gid, info in more.items():
        entry = into.setdefault(str(gid), {"arm": None, "fallback": [], "status": None, "failure_reason": None})
        for key in ("arm", "status"):
            if entry.get(key) is None and info.get(key) is not None:
                entry[key] = info[key]
        entry["fallback"] = list(entry.get("fallback") or []) + list(info.get("fallback") or [])
        if info.get("failure_reason") is not None:
            entry["failure_reason"] = info["failure_reason"]


# ---------------------------------------------------------------------------------------------- 組表與窮盡性


def _output_name(column: str, timeframe: str) -> str:
    """L6.5 所見欄名 → 落盤欄名（唯一標記實作 `feature_naming.tag_timeframe`；週期不屬週期鍵 ⇒ 原名）。"""
    if str(timeframe) in feature_naming.timeframe_keys():
        return feature_naming.tag_timeframe(str(column), str(timeframe))
    return str(column)


def _parent_of(name: str, by_output: Mapping[str, Any]) -> Optional[str]:
    """append 模式衍生欄之父欄落盤名：最長之「已記錄輸出欄名＋底線」前綴（逐段由長至短查表）。"""
    parts = str(name).split("_")
    for k in range(len(parts) - 1, 0, -1):
        prefix = "_".join(parts[:k])
        if prefix in by_output:
            return prefix
    return None


def _check_value(contract: Mapping[str, Any], path: str, value: Any, where: str) -> None:
    if value is not None and str(value) not in set(contract_value_set(contract, path)):
        raise ProvenanceError(f"{where}：值 {value!r} 不屬契約 {path}")


def build_provenance_table(
    records: Mapping[Tuple[str, str], Mapping[str, Any]],
    *,
    output_columns: Sequence[str],
    column_group: Mapping[str, str],
    dropped_columns: Mapping[str, str],
    terminals: Optional[Mapping[str, str]] = None,
    events: Optional[Mapping[str, Sequence[str]]] = None,
    column_keys: Optional[Mapping[str, Tuple[str, str]]] = None,
) -> pd.DataFrame:
    """由前處理器之 run 層級紀錄（鍵＝(原生週期, L6.5 所見欄名)）組逐欄紀錄表，鍵換為落盤欄名
    （FF-NAME `tag_timeframe`）；dead-drop 欄記終態（SPEC Task 1.3 ②）。

    列之母體＝`output_columns`（已落盤）∪ `dropped_columns`（dead-drop）∪ 終態已定而未落盤之紀錄（如 post-IC 入口
    剔除者）。append 模式衍生欄（無直接紀錄者）以最長父欄前綴關聯：步驟狀態承父欄、平穩化決策欄為 null、
    `parent_column`＝父欄落盤名。終態：dead-drop 欄取寫入端紀錄；其餘取前處理器紀錄（非 null 時）否則寫入端紀錄。
    任一列缺紀錄、缺步驟狀態、缺終態、值不屬契約、或落盤名重複 ⇒ 具名例外（fail-closed）。

    `column_keys`（寫入端給定時）：落盤名 → (來源群組 id, L6.5 所見欄名)，為寫入端實際落盤之對照（唯一權威）；紀錄以
    (紀錄之群組 id, 欄名) 對應，衍生欄之父欄於同群組內以最長「欄名＋底線」前綴關聯。未給 ⇒ 以紀錄鍵之週期經
    `tag_timeframe` 推落盤名。"""
    contract = load_contract()
    steps = list(contract["steps"])
    columns = list(contract["record_columns"])
    terminals = dict(terminals or {})
    extra_events = {str(k): list(v) for k, v in dict(events or {}).items()}
    dropped = {str(k): str(v) for k, v in dict(dropped_columns).items()}
    groups_of = {str(k): str(v) for k, v in dict(column_group).items()}
    keys_of = None if column_keys is None else {str(k): (str(v[0]), str(v[1])) for k, v in dict(column_keys).items()}

    by_output: Dict[str, Tuple[Tuple[str, str], Mapping[str, Any]]] = {}
    if keys_of is not None:
        # 寫入端對照：(群組 id, L6.5 欄名) → 落盤名；紀錄依其群組 id 與欄名對應（未落盤者以推得之名列入，供終態／孤兒判定）
        out_of = {value: name for name, value in keys_of.items()}
        for key, record in records.items():
            timeframe, column = str(key[0]), str(key[1])
            name = out_of.get((str(record.get("group_id")), column), _output_name(column, timeframe))
            if name in by_output:
                raise ProvenanceConflictError(f"紀錄鍵 {key} 與 {by_output[name][0]} 之落盤名相同：{name}")
            by_output[name] = ((timeframe, column), record)
    else:
        for key, record in records.items():
            timeframe, column = str(key[0]), str(key[1])
            name = _output_name(column, timeframe)
            if name in by_output:
                raise ProvenanceConflictError(f"紀錄鍵 {key} 與 {by_output[name][0]} 之落盤名相同：{name}")
            by_output[name] = ((timeframe, column), record)

    def parent_name(name: str) -> Optional[str]:
        if keys_of is None or name not in keys_of:
            return _parent_of(name, by_output)
        group, column = keys_of[name]
        parts = column.split("_")
        for k in range(len(parts) - 1, 0, -1):
            candidate = out_of.get((group, "_".join(parts[:k])))
            if candidate is not None and candidate in by_output:
                return candidate
        return None

    names: List[str] = [str(c) for c in output_columns]
    if len(names) != len(set(names)):
        raise ProvenanceExhaustivenessError("落盤欄名重複")
    seen = set(names)
    for name in dropped:
        if name in seen:
            raise ProvenanceExhaustivenessError(f"欄 {name} 同時為落盤欄與 dead-drop 欄")
        names.append(name)
        seen.add(name)
    for name, (_key, record) in sorted(by_output.items()):
        if name not in seen and record.get("terminal") is not None:
            names.append(name)
            seen.add(name)

    used = set()
    rows: List[Dict[str, Any]] = []
    for name in sorted(names):
        parent: Optional[str] = None
        if name in by_output:
            key, record = by_output[name]
            used.add(name)
        else:
            parent = parent_name(name)
            if parent is None:
                raise ProvenanceExhaustivenessError(f"落盤欄 {name} 無執行紀錄亦無可關聯之父欄紀錄")
            key, record = by_output[parent]
        row: Dict[str, Any] = {column: None for column in columns}
        row.update({
            "output_column": name,
            "native_timeframe": key[0],
            "layer": None if record.get("layer") is None else str(record.get("layer")),
            "group_id": groups_of.get(name, dropped.get(name, record.get("group_id"))),
            "parent_column": parent,
        })
        for step in steps:
            value = record.get(step)
            if value is None:
                raise ProvenanceExhaustivenessError(f"欄 {name} 缺步驟狀態 {step}")
            _check_value(contract, f"step_status_values.{step}", value, f"欄 {name}.{step}")
            row[step] = str(value)
        if name in dropped:
            terminal = terminals.get(name)
        else:
            terminal = record.get("terminal") if parent is None and record.get("terminal") is not None \
                else terminals.get(name)
        if terminal is None:
            raise ProvenanceExhaustivenessError(f"欄 {name} 無終態")
        _check_value(contract, "terminal_values", terminal, f"欄 {name}.terminal")
        row["terminal"] = str(terminal)
        if parent is None:
            for field in _DECISION_FIELDS:
                row[field] = record.get(field)
            _check_value(contract, "dstar_source_values", row.get("dstar_source"), f"欄 {name}.dstar_source")
            own_events = list(record.get("events") or [])
        else:
            own_events = []
        row["events"] = sorted(set(own_events) | set(extra_events.get(name, [])))
        rows.append(row)

    orphans = sorted(set(by_output) - used)
    if orphans:
        raise ProvenanceExhaustivenessError(f"{len(orphans)} 欄有執行紀錄而未落盤、非 dead-drop 亦無終態（例 {orphans[:3]}）")
    return pd.DataFrame(rows, columns=columns)


def build_post_ic_table(
    records: Mapping[Tuple[str, str], Mapping[str, Any]],
    *,
    column_group: Mapping[str, str],
) -> pd.DataFrame:
    """processed（post-IC）逐欄紀錄表（SPEC Task 1.4）：母體＝紀錄鍵之欄名全集（＝IC 選欄全集；post-IC 所見欄名即
    raw 落盤名，故落盤名＝紀錄欄名，不經 `tag_timeframe`）。`column_group`＝processed 落盤欄名 → processed 群組 id。

    窮盡性：processed 群組欄聯集 ⊆ 紀錄欄名（post-IC 不產衍生欄，不做父欄關聯）；紀錄欄名＝processed 群組欄聯集 ∪
    未寫出者（選欄不在 raw、入口剔除之 ratio-unsafe 等，各記其終態），逐名、無重複；已寫出與未寫出兩類之終態值不得
    相交（未各記其終態 ⇒ 拒收）。任一不符 ⇒ 具名例外（fail-closed）。"""
    names_by_record: Dict[str, Tuple[str, str]] = {}
    column_keys: Dict[str, Tuple[str, str]] = {}
    for key, record in records.items():
        column = str(key[1])
        if column in names_by_record:
            raise ProvenanceConflictError(f"post-IC 紀錄鍵 {key} 與 {names_by_record[column]} 之欄名相同：{column}")
        names_by_record[column] = (str(key[0]), column)
        column_keys[column] = (str(record.get("group_id")), column)
    output_columns = [str(c) for c in column_group]
    missing = sorted(set(output_columns) - set(names_by_record))
    if missing:
        raise ProvenanceExhaustivenessError(f"processed 落盤欄無 post-IC 紀錄（例 {missing[:3]}）")
    table = build_provenance_table(records, output_columns=output_columns, column_group=dict(column_group),
                                   dropped_columns={}, column_keys=column_keys)
    not_written = sorted(set(names_by_record) - set(output_columns))
    check_exhaustive(table, output_columns, not_written)
    terminal_of = dict(zip((str(n) for n in table["output_column"]), (str(t) for t in table["terminal"])))
    overlap = {terminal_of[c] for c in output_columns} & {terminal_of[c] for c in not_written}
    if overlap:
        raise ProvenanceExhaustivenessError(f"已寫出與未寫出之選欄終態相同 {sorted(overlap)}（未各記其終態）")
    return table


def check_exhaustive(
    table: pd.DataFrame,
    manifest_columns: Iterable[str],
    dropped_columns: Iterable[str],
) -> None:
    """紀錄輸出欄名集合須逐名等於 manifest 群組欄聯集 ∪ dead-drop 欄且無重複，否則拋
    `ProvenanceExhaustivenessError`（SPEC Task 1.3 ②、§V oracle ①）。"""
    names = [str(n) for n in table["output_column"]] if "output_column" in table.columns else []
    if len(names) != len(set(names)):
        raise ProvenanceExhaustivenessError("紀錄輸出欄名重複")
    manifest = [str(c) for c in manifest_columns]
    if len(manifest) != len(set(manifest)):
        raise ProvenanceExhaustivenessError("manifest 群組欄重複")
    expected = set(manifest) | {str(c) for c in dropped_columns}
    extra, missing = sorted(set(names) - expected), sorted(expected - set(names))
    if extra or missing:
        raise ProvenanceExhaustivenessError(f"紀錄與 manifest 群組欄 ∪ dead-drop 欄不符：多 {extra[:3]}、缺 {missing[:3]}")


# ---------------------------------------------------------------------------------------------- 內容身分


def file_sha256(path: Path) -> str:
    """檔案位元組之 sha256（串流讀，不整檔載入）。"""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def arrow_dtype_summary(schema: Any, columns: Sequence[str]) -> str:
    """契約 `content_sha256.dtype_doc`：該檔各欄 Arrow 型別字串去重、升冪排序後以 `|` 連接。"""
    return "|".join(sorted({str(schema.field(str(c)).type) for c in columns}))


def content_entry_for_file(path: Path, relative_path: str, columns: Sequence[str], row_count: int) -> ContentEntry:
    """寫入端於群組檔寫畢當下組其內容身分項（檔案 sha256 與 footer 之 Arrow 型別；不讀資料頁）。"""
    schema = pq.read_schema(str(path))
    return ContentEntry(relative_path=str(relative_path), columns=tuple(str(c) for c in columns),
                        row_count=int(row_count), dtype=arrow_dtype_summary(schema, columns),
                        file_sha256=file_sha256(path))


def compute_content_sha256(entries: Sequence[ContentEntry], row_index_sha256: str) -> str:
    """run 內容身分（SPEC Task 1.3 ③；與 `config_hash`、`feature_schema_hash` 正交）。序列化見契約 `content_sha256._doc`。"""
    ordered = sorted(entries, key=lambda entry: entry.relative_path)
    payload = {
        "entries": [[e.relative_path, list(e.columns), int(e.row_count), e.dtype, e.file_sha256] for e in ordered],
        "row_index_sha256": row_index_sha256,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------------------------------------- 紀錄檔寫讀


def _arrow_schema(contract: Mapping[str, Any]) -> pa.Schema:
    fields = []
    for name, spec in contract["record_columns"].items():
        kind = str(spec["type"])
        arrow_type = pa.string() if kind.startswith("enum:") else _ARROW_TYPES[kind]
        fields.append(pa.field(str(name), arrow_type, nullable=bool(spec.get("nullable", True))))
    return pa.schema(fields)


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and value != value)


def _coerce_cell(value: Any, arrow_type: Any) -> Any:
    """單格依契約型別正規化（pandas 於數值欄以 NaN 代 None：非 float64 欄之 NaN 一律視為 null）。"""
    if pa.types.is_list(arrow_type):
        return None if value is None else [str(x) for x in list(value)]
    if _is_missing(value):
        return None
    if pa.types.is_floating(arrow_type):
        return float(value)
    if pa.types.is_integer(arrow_type):
        return int(value)
    if pa.types.is_boolean(arrow_type):
        return bool(value)
    return str(value)


def _to_arrow(table: pd.DataFrame, contract: Mapping[str, Any]) -> pa.Table:
    schema = _arrow_schema(contract)
    arrays = []
    for field in schema:
        values = list(table[field.name]) if field.name in table.columns else [None] * len(table)
        arrays.append(pa.array([_coerce_cell(v, field.type) for v in values], type=field.type))
    return pa.Table.from_arrays(arrays, schema=schema)


def summarize_table(table: pd.DataFrame, contract: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """manifest 摘要：各步驟各狀態計數與終態計數（不內嵌逐欄紀錄）。"""
    contract = contract or load_contract()
    steps = {step: {str(k): int(v) for k, v in sorted(table[step].value_counts().items())} if len(table) else {}
             for step in contract["steps"]}
    terminal = {str(k): int(v) for k, v in sorted(table["terminal"].value_counts().items())} if len(table) else {}
    return {"steps": steps, "terminal": terminal}


def normalize_groups(groups: Mapping[str, Mapping[str, Any]],
                     contract: Optional[Mapping[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """群組表正規化（鍵＝契約 `manifest_group_keys`；`fallback` 為清單）並驗值屬契約。"""
    contract = contract or load_contract()
    out: Dict[str, Dict[str, Any]] = {}
    for gid in sorted(groups):
        info = dict(groups[gid])
        entry = {
            "arm": info.get("arm"),
            "fallback": [str(v) for v in list(info.get("fallback") or [])],
            "status": info.get("status"),
            "failure_reason": None if info.get("failure_reason") is None else str(info.get("failure_reason")),
        }
        _check_value(contract, "group_arm_values", entry["arm"], f"群組 {gid}.arm")
        _check_value(contract, "group_status_values", entry["status"], f"群組 {gid}.status")
        for value in entry["fallback"]:
            _check_value(contract, "fallback_values", value, f"群組 {gid}.fallback")
        out[str(gid)] = {key: entry[key] for key in contract["manifest_group_keys"]}
    return out


def write_provenance_table(
    table: pd.DataFrame,
    staging_dir: Path,
    artifact_kind: str,
    groups: Mapping[str, Mapping[str, Any]],
    summary_extra: Optional[Mapping[str, Any]] = None,
) -> ProvenancePointer:
    """以 zstd parquet 寫紀錄檔至暫存 `provenance/`，回 manifest 用之指標（SPEC Task 1.3 ④、1.4）。
    寫入失敗一律上拋（不得吞例外）。`summary_extra`：併入摘要之額外鍵（processed 之 `selected_columns`，
    SPEC Task 1.4；與既有摘要鍵同名 ⇒ `ProvenanceConflictError`）。"""
    contract = load_contract()
    relative = str(contract["files"][artifact_kind])
    target = Path(staging_dir) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(_to_arrow(table, contract), str(target), compression=str(contract["parquet_compression"]))
    summary = summarize_table(table, contract)
    for key, value in dict(summary_extra or {}).items():
        if key in summary:
            raise ProvenanceConflictError(f"摘要鍵 {key!r} 與既有摘要鍵衝突")
        summary[str(key)] = value
    return ProvenancePointer(path=relative, sha256=file_sha256(target), row_count=int(len(table)),
                             contract_version=int(contract["version"]), summary=summary,
                             groups=normalize_groups(groups, contract))


def read_provenance_table(run_dir: Path, pointer: Mapping[str, Any], *,
                          artifact_kind: Optional[str] = None) -> pd.DataFrame:
    """依 manifest 宣告讀紀錄檔：存在、路徑在 run 內、路徑等於契約之紀錄檔名、sha256、列數、契約版本與紀錄欄位
    皆相符，否則拋 `ProvenanceIntegrityError`；不重算特徵檔雜湊（SPEC Task 1.5）。`artifact_kind` 給定時路徑須恰為
    契約 `files[artifact_kind]`，未給時須屬契約 `files` 之值（審碼 b2 r1 CODEX-R1-P1-02：指標改指特徵群組檔即拒）。"""
    contract = load_contract()
    if not isinstance(pointer, Mapping) or any(key not in pointer for key in contract["manifest_provenance_keys"]):
        raise ProvenanceIntegrityError(f"provenance 物件缺鍵（契約 {contract['manifest_provenance_keys']}）")
    raw = str(pointer.get("path") or "")
    allowed = ({str(contract["files"][artifact_kind])} if artifact_kind is not None
               else {str(v) for v in contract["files"].values()})
    if raw not in allowed:
        raise ProvenanceIntegrityError(f"紀錄檔路徑 {raw!r} 不屬契約紀錄檔名 {sorted(allowed)}")
    relative = Path(raw)
    if not raw or relative.is_absolute() or ".." in relative.parts:
        raise ProvenanceIntegrityError(f"紀錄檔路徑不安全：{raw!r}")
    root = Path(run_dir).resolve()
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ProvenanceIntegrityError(f"紀錄檔路徑逃逸 run 目錄：{raw!r}")
    if not target.is_file():
        raise ProvenanceIntegrityError(f"紀錄檔不存在：{target}")
    if int(pointer.get("contract_version", -1)) != int(contract["version"]):
        raise ProvenanceIntegrityError(
            f"紀錄契約版本 {pointer.get('contract_version')!r} ≠ 現行 {contract['version']!r}")
    if file_sha256(target) != str(pointer.get("sha256")):
        raise ProvenanceIntegrityError(f"紀錄檔 sha256 ≠ manifest 宣告：{target}")
    table = pq.read_table(str(target))
    if int(table.num_rows) != int(pointer.get("row_count", -1)):
        raise ProvenanceIntegrityError(f"紀錄檔列數 {table.num_rows} ≠ manifest 宣告 {pointer.get('row_count')!r}")
    expected_columns = set(contract["record_columns"])
    if set(table.column_names) != expected_columns:
        raise ProvenanceIntegrityError(
            f"紀錄檔欄位 ≠ 契約 record_columns：多 {sorted(set(table.column_names) - expected_columns)}、"
            f"缺 {sorted(expected_columns - set(table.column_names))}")
    return table.to_pandas()


def resolve_run_identity(manifest: Mapping[str, Any], artifact_kind: str) -> RunIdentity:
    """自同一次 manifest 解析（呼叫端傳入其解析所得之 dict，本函式不讀檔）取 run 身分（SPEC Task 2.1）。

    `feature_schema_hash` 取該 artifact 節點之值，節點無此鍵則取 manifest 頂層；`content_sha256` 與
    `provenance_sha256`（節點 `provenance.sha256`）缺 ⇒ None（舊 run，`legacy`）。artifact 節點不存在 ⇒
    `ProvenanceMissingError`。"""
    if not isinstance(manifest, Mapping):
        raise ProvenanceIntegrityError(f"manifest 非物件：{type(manifest).__name__}")
    node = (manifest.get("artifacts") or {}).get(str(artifact_kind))
    if not isinstance(node, Mapping):
        raise ProvenanceMissingError(f"manifest 無 artifact 節點 {artifact_kind!r}")
    pointer = node.get("provenance")
    content = node.get("content_sha256")
    provenance_sha256 = pointer.get("sha256") if isinstance(pointer, Mapping) else None
    return RunIdentity(
        symbol=manifest.get("symbol"),
        tf=manifest.get("tf"),
        config_hash=manifest.get("config_hash"),
        feature_schema_hash=(node["feature_schema_hash"] if "feature_schema_hash" in node
                             else manifest.get("feature_schema_hash")),
        feature_naming_version=manifest.get("feature_naming_version"),
        artifact_kind=str(artifact_kind),
        content_sha256=None if content is None else str(content),
        provenance_sha256=None if provenance_sha256 is None else str(provenance_sha256),
    )
