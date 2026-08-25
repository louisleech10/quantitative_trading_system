"""GAP-3 UX Task 1.2 驗證（-k gap3_csv_import）：`POST /api/v1/case/import-events/csv`。

SPEC L1414–1422／TODO Task 1.2。判準字面之唯一來源＝SPEC 該 Task「驗證」欄：
`pytest tests/api -q -k gap3_csv_import` ≥8 條全綠；共用性以 **V-3 兩重 oracle** 證
（①靜態 AST：CSV route 呼叫 `/import-events` 之同名驗證函式；②行為 mutation：改壞共用點 ⇒ 兩路同紅）。

本檔承載 V-3 之①（AST 靜態）與②之**斷言面**（`test_gap3_csv_import_shared_validator_behaviour`
對 CSV／JSON 兩路徑各一條，改壞共用點時兩條同時紅；另寫一份檢核時只有 CSV 那條紅）。
"""

from __future__ import annotations

import ast
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.factories import create_event_sample_pipeline
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)
REPO = Path(__file__).resolve().parents[2]
ROUTES = REPO / "api" / "routes" / "case.py"
SERVICE = REPO / "api" / "services" / "case_import_service.py"

#: 使用者自有欄名（刻意不等於契約欄名——1.2 的存在理由就是免除「先改標頭」）
USER_HEADER = ["我的編號", "幣種", "K線週期", "毫秒時間", "是不是正例", "備註"]
MAPPING = {"event_id": "我的編號", "symbol": "幣種", "timeframe": "K線週期", "t0": "毫秒時間", "label": "是不是正例"}
DEFAULT_FIELDS = ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                  "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _defaults(**over) -> dict:
    base = make_event(0)
    out = {k: base[k] for k in DEFAULT_FIELDS}
    out.update(over)
    return out


def _csv(rows, header=None) -> bytes:
    head = header if header is not None else USER_HEADER
    lines = [",".join(head)] + [",".join(str(c) for c in r) for r in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _rows(n=2):
    """CSV 列；`event_id` 依 D-2 由**唯一實作**產生（Task 1.3；不在測試裡重寫公式）。"""
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    base = make_event(0)
    out = []
    for i in range(n):
        t0 = base["t0"] + i * 43200000
        out.append([canonical_event_id("ETHUSDT", "12h", t0), "ETHUSDT", "12h", str(t0), str(i % 2), f"note{i}"])
    return out


def _post_csv(content: bytes, mapping=None, defaults=None, **params):
    data = {"column_mapping": json.dumps(MAPPING if mapping is None else mapping, ensure_ascii=False)}
    if defaults is not False:
        data["batch_defaults"] = json.dumps(_defaults() if defaults is None else defaults)
    return client.post(
        "/api/v1/case/import-events/csv",
        files={"file": ("mine.csv", io.BytesIO(content), "text/csv")},
        data=data,
        params=params,
    )


def _stored_count() -> int:
    return client.get("/api/v1/case/events").json()["total"]


def _reasons(r) -> set:
    return {f["reason"] for f in r.json()["detail"]["failures"]}


# ---------------------------------------------------------------------------
# 行為
# ---------------------------------------------------------------------------
def test_gap3_csv_import_user_column_names_accepted_and_stored(_isolated_storage):
    """① 使用者欄名 ＋ column_mapping ⇒ 落檔；標頭不必先改成契約欄名。"""
    r = _post_csv(_csv(_rows(2)))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] and body["n_valid"] == 2 and body["import_id"]
    det = client.get(f"/api/v1/case/events/{body['import_id']}").json()
    assert [rec["event_id"] for rec in det["records"]] == [r[0] for r in _rows(2)]
    assert [rec["label"] for rec in det["records"]] == [0, 1]
    assert _stored_count() == 1


def test_gap3_csv_import_missing_column_mapping_rejected(_isolated_storage):
    """② 未提供 column_mapping ⇒ column_mapping_missing、**落檔數 == 0**（不做任何預設對映；A-4′）。"""
    r = _post_csv(_csv(_rows(2)), mapping={})
    assert r.status_code == 422, r.text
    assert _reasons(r) == {"column_mapping_missing"}
    assert _stored_count() == 0


def test_gap3_csv_import_mapping_without_label_rejected(_isolated_storage):
    """③ 對映未指定 label ⇒ column_mapping_missing（正反例宣告不得由平台猜）。"""
    r = _post_csv(_csv(_rows(2)), mapping={k: v for k, v in MAPPING.items() if k != "label"})
    assert r.status_code == 422
    failures = r.json()["detail"]["failures"]
    assert [f["reason"] for f in failures] == ["column_mapping_missing"] and failures[0]["field"] == "label"
    assert _stored_count() == 0


def test_gap3_csv_import_column_not_found_in_file(_isolated_storage):
    """④ 對映指向 CSV 不存在之欄 ⇒ column_not_found_in_file、**落檔數 == 0**（SPEC 邊界②）。"""
    r = _post_csv(_csv(_rows(2)), mapping=dict(MAPPING, t0="不存在的欄"))
    assert r.status_code == 422
    failures = r.json()["detail"]["failures"]
    assert _reasons(r) == {"column_not_found_in_file"} and failures[0]["field"] == "t0"
    assert "不存在的欄" in failures[0]["message"]
    assert _stored_count() == 0


def test_gap3_csv_import_label_column_not_binary(_isolated_storage):
    """⑤ label 欄非 0/1 ⇒ label_column_not_binary、落檔數 == 0；True／yes 一律不轉換。"""
    rows = _rows(3)
    rows[1][4] = "yes"
    rows[2][4] = "True"
    r = _post_csv(_csv(rows))
    assert r.status_code == 422
    assert _reasons(r) == {"label_column_not_binary"}
    assert {f["row"] for f in r.json()["detail"]["failures"]} == {1, 2}
    assert _stored_count() == 0


def test_gap3_csv_import_unmapped_columns_ignored_loudly(_isolated_storage):
    """⑥ 未對映之欄被忽略，但**不靜默**：回應 warnings 具名列出被忽略的欄。"""
    r = _post_csv(_csv(_rows(2)))
    assert r.status_code == 200
    warnings = r.json()["warnings"]
    assert any("備註" in w for w in warnings), warnings


def test_gap3_csv_import_batch_defaults_fill_absent_only(_isolated_storage):
    """⑦ batch_defaults 填補 CSV 沒有的契約欄；**不覆蓋**列自帶值（自帶混值仍拒）。"""
    ok = _post_csv(_csv(_rows(2)), defaults=_defaults(scenario="C"))
    assert ok.status_code == 200 and ok.json()["n_valid"] == 2

    header = USER_HEADER + ["情境"]
    rows = [r + ["A" if i == 0 else "B"] for i, r in enumerate(_rows(4))]
    bad = _post_csv(_csv(rows, header), mapping=dict(MAPPING, scenario="情境"), defaults=_defaults(scenario="A"))
    assert bad.status_code == 422
    assert "heterogeneous_rows_in_batch" in _reasons(bad)
    assert _stored_count() == 1  # 只有上面那批成功落檔


def test_gap3_csv_import_validate_only_does_not_store(_isolated_storage):
    """⑧ validate_only ⇒ 通過檢核但不落檔（與既有端點同語意，因走同一 import_records）。"""
    r = _post_csv(_csv(_rows(2)), validate_only=True)
    assert r.status_code == 200 and r.json()["import_id"] is None and r.json()["stored_path"] is None
    assert _stored_count() == 0


def test_gap3_csv_import_existing_endpoints_behaviour_unchanged(_isolated_storage):
    """⑨ SPEC 邊界①：只新增端點，**不改** `/import-events` 與 `/import-events/json` 之行為。"""
    recs = [make_event(0, label=1), make_event(1, label=0)]
    j = client.post("/api/v1/case/import-events/json", json={"records": recs})
    assert j.status_code == 200 and j.json()["n_valid"] == 2
    raw = json.dumps({"records": recs}).encode("utf-8")
    f = client.post("/api/v1/case/import-events",
                    files={"file": ("ev.json", io.BytesIO(raw), "application/json")})
    assert f.status_code == 200 and f.json()["n_valid"] == 2


@pytest.mark.parametrize("path", ["csv", "json"])
def test_gap3_csv_import_shared_validator_behaviour(_isolated_storage, path):
    """⑩ **V-3 之行為 oracle**：同一契約違規在 CSV 與 JSON 兩路徑得到**相同 reason**。

    🔴 改壞共用檢核點 ⇒ 本測之兩個 param **同時**轉紅；
       若只有 `csv` 轉紅，代表 CSV 走了另一份檢核（存在平行實作）。
    """
    contract = create_event_sample_pipeline().import_contract()
    bad_tf = "not-a-timeframe"
    if path == "json":
        recs = [make_event(0, label=1, entry_price_semantic=bad_tf), make_event(1, label=0)]
        r = client.post("/api/v1/case/import-events/json", json={"records": recs})
    else:
        r = _post_csv(_csv(_rows(2)), defaults=_defaults(entry_price_semantic=bad_tf))
    assert r.status_code == 422, r.text
    got = _reasons(r)
    assert "enum_violation" in got and got <= set(contract["import_failure_reasons"])
    assert _stored_count() == 0


# ---------------------------------------------------------------------------
# V-3 ①：AST 靜態 oracle（非 grep）
# ---------------------------------------------------------------------------
def _func(tree: ast.AST, name: str) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"找不到函式 {name!r}")


def _called_attrs(node: ast.AST) -> set:
    return {n.func.attr for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}


def test_gap3_csv_import_ast_oracle_shared_entrypoints():
    """V-3 ①：三個匯入 route **都**呼叫同名之 `import_records`；對映層不含任何契約檢核呼叫。"""
    routes = ast.parse(ROUTES.read_text(encoding="utf-8"))
    for handler in ("import_events_file", "import_events_json", "import_events_csv"):
        assert "import_records" in _called_attrs(_func(routes, handler)), f"{handler} 未呼叫共用之 import_records"

    service = ast.parse(SERVICE.read_text(encoding="utf-8"))
    mapping_layer = _called_attrs(_func(service, "csv_records_from_mapping"))
    for forbidden in ("validate", "validate_event_import", "import_records"):
        assert forbidden not in mapping_layer, f"對映層不得自行檢核／落檔（發現 {forbidden}）"


def test_gap3_csv_import_ast_oracle_import_records_definition_is_unique():
    """V-3 ①強化（CODEX-R1-P2-02）：只比對 attribute 名稱**不足**以證「同一 function object」。

    一份 verbatim copy（例如 `class CsvEventImportService(EventImportService)` 自帶
    `import_records`）可同時通過舊 AST 與 `1.2-M1/M2`。故錨點改落在**定義面**：
    全 `api/`＋`momentum/` 之 `def import_records` 須**恰一個**，且其所屬 class 為
    `EventImportService`；三個 route handler 取得 service 之方式須為同一個工廠呼叫。
    """
    defs = []
    for base in ("api", "momentum"):
        for path in sorted((REPO / base).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef):
                    continue
                for item in cls.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "import_records":
                        defs.append((str(path.relative_to(REPO)), cls.name))
            for node in tree.body:  # module-level def（非 method）亦算一份實作
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "import_records":
                    defs.append((str(path.relative_to(REPO)), "<module>"))
    assert defs == [("api/services/case_import_service.py", "EventImportService")], defs

    routes = ast.parse(ROUTES.read_text(encoding="utf-8"))
    factories = set()
    for handler in ("import_events_file", "import_events_json", "import_events_csv"):
        fn = _func(routes, handler)
        got = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        factories.add(frozenset(got & {"get_event_import_service", "get_case_import_service"}))
    assert factories == {frozenset({"get_event_import_service"})}, factories


def test_gap3_csv_import_ast_oracle_single_validation_and_unit_detection_site():
    """V-3 ①（含 Task 1.4 覆蓋面）：`import_records` 是**唯一**呼叫 validate 與 t0 單位偵測之處。

    🔴 Task 1.4「覆蓋風險」明訂：AST oracle 之涵蓋面**須包含偵測函式**，
    不得只證 schema 檢核共用——否則兩路徑會各自演化出不同單位判定。
    """
    service = ast.parse(SERVICE.read_text(encoding="utf-8"))
    holders = {"validate": [], "normalize_t0_units": []}
    for node in ast.walk(service):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        called = _called_attrs(node)
        for attr in holders:
            if attr in called:
                holders[attr].append(node.name)
    assert holders["validate"] == ["import_records"], holders["validate"]
    assert holders["normalize_t0_units"] == ["import_records"], holders["normalize_t0_units"]
