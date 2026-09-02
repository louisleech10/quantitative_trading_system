"""GAP-3 UX Task 1.3 之**後端側**驗證（-k gap3_source_digest）：`source_file_digest` 綁完整 CaseData。

SPEC L1424–1565。本檔證三件事，並**產生 vitest 用之 golden fixture**
（`frontend/src/lib/__fixtures__/canonicalSourceGolden.json`）：

①刪除 ②改名 ③改值 任一 `future_*` 欄 ⇒ digest **改變**（改名攻擊之證據面閉合）；
序列化依 §G S-9（`repr(float)` lexeme／NaN±Inf→null／`-0.0` 保留／無尾端 newline／UTF-8 無 BOM）；
`/search` 結果端點回應**增兩鍵**且 `sha256(source_file_text.encode()) == source_file_digest`。

🔴 golden 由本檔生成而非手寫：後端序列化一旦被改壞（如改回五欄子集），
   golden 會同批塌陷 ⇒ 前端 `canonicalSourceCoverage` 之三條同時轉紅（SPEC mutation ①）。
"""

from __future__ import annotations

import hashlib
import json

from pathlib import Path

import pytest

from momentum.factories import create_event_sample_pipeline
from tests.api._gap3_declaration import declaration_for_timeframes

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "frontend" / "src" / "lib" / "__fixtures__" / "canonicalSourceGolden.json"
TARGET_COLUMN = "future_2bar_return"


def _payload(cases):
    return create_event_sample_pipeline().canonical_source_payload(cases)


def _base_cases():
    """兩列「完整 CaseData」形狀之序列化列（含多個 future_* 欄；鍵刻意非排序輸入）。"""
    return [
        {
            "symbol": "ETHUSDT",
            "timestamp": "2024-01-01T00:00:00Z",
            "trigger_idx": 10,
            "open": 2000.0, "high": 2100.0, "low": 1990.0, "close": 2050.0,
            "volume": 1234.5, "price_change": 2.5, "market_phase": "bull",
            "positive_case": True,
            "timeframe": "12h",
            "future_1bar_return": 0.011,
            TARGET_COLUMN: 0.0123,
            "future_3bar_return": -0.004,
            "future_2bar_max_drawdown": -0.02,
        },
        {
            "symbol": "ETHUSDT",
            "timestamp": "2024-01-01T12:00:00Z",
            "trigger_idx": 11,
            "open": 2050.0, "high": 2080.0, "low": 2010.0, "close": 2020.0,
            "volume": 999.0, "price_change": -1.5, "market_phase": "bear",
            "positive_case": False,
            "timeframe": "12h",
            "future_1bar_return": -0.007,
            TARGET_COLUMN: 0.0456,
            "future_3bar_return": 0.002,
            "future_2bar_max_drawdown": -0.05,
        },
    ]


def _variants():
    base = _base_cases()

    deleted = [dict(c) for c in base]
    for c in deleted:
        c.pop(TARGET_COLUMN)

    renamed = [dict(c) for c in base]
    for c in renamed:
        c[f"{TARGET_COLUMN}_renamed"] = c.pop(TARGET_COLUMN)

    changed = [dict(c) for c in base]
    changed[0][TARGET_COLUMN] = base[0][TARGET_COLUMN] + 1e-9

    # 驗收 (c)：含 `-0.0`／極大極小浮點之 fixture ⇒ 位元組相等仍成立。
    # 🔴 另刻意混入**非 ASCII**：前端沒有獨立的 digest oracle（它不准自算），
    #    唯一能獨立檢查的是「收到的 text 本身是否符合 S-9 之可觀察規則」
    #    （separators 無空白／非 ASCII 字面輸出／無尾端 newline）。
    #    少了這個，後端換成 `json.dumps` 預設參數時前端會完全看不見（mutation 1.3-M3b 實跑抓到）。
    floats = [dict(base[0], **{
        "market_phase": "多頭é",
        "future_1bar_return": -0.0,
        TARGET_COLUMN: 5e-324,
        "future_3bar_return": 1.7976931348623157e308,
        "future_2bar_max_drawdown": 0.1 + 0.2,
    })]

    return {"base": base, "deleted": deleted, "renamed": renamed, "changed": changed, "floats": floats}


# ---------------------------------------------------------------------------
# ①②③ 完整列 digest 之鑑別力
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("variant", ["deleted", "renamed", "changed"])
def test_gap3_source_digest_changes_on_future_column_mutation(variant):
    """①刪除／②改名／③改值任一 `future_*` 欄 ⇒ digest 必改變（只取五欄子集時本測轉紅）。"""
    v = _variants()
    _, base_digest = _payload(v["base"])
    _, other_digest = _payload(v[variant])
    assert other_digest != base_digest, f"{variant}：digest 未改變 ⇒ 改名攻擊之證據面未閉合"


def test_gap3_source_digest_covers_every_own_key():
    """完整列覆蓋：`source_file_text` 含每一列之**所有** own key（不改名、不篩欄、不省略）。"""
    cases = _base_cases()
    text, _ = _payload(cases)
    parsed = json.loads(text)
    assert len(parsed) == len(cases)
    for got, want in zip(parsed, cases):
        assert set(got) == set(want), set(want) ^ set(got)


def test_gap3_source_digest_keys_sorted_utf8_ascending():
    """S-2：鍵序為 UTF-8 位元組升冪（跨執行環境唯一序）。"""
    text, _ = _payload(_base_cases())
    for row in json.loads(text):
        keys = list(row)
        assert keys == sorted(keys, key=lambda k: k.encode("utf-8"))


def test_gap3_source_digest_s9_serialization_rules():
    """S-9：NaN／±Inf → null、`-0.0` 保留、無尾端 newline、無 BOM、`repr(float)` lexeme。"""
    cases = [{
        "symbol": "ét\"h\\", "nan": float("nan"), "pinf": float("inf"), "ninf": float("-inf"),
        "neg_zero": -0.0, "pos_zero": 0.0, "tiny": 5e-324, "big": 1.7976931348623157e308,
        "ctrl": "ab", "nested": {"z": [1, 2, {"b": 2, "a": 1}]},
    }]
    text, digest = _payload(cases)
    raw = text.encode("utf-8")
    assert not text.endswith("\n") and not raw.startswith(b"\xef\xbb\xbf")
    assert hashlib.sha256(raw).hexdigest() == digest
    assert '"nan":null' in text and '"pinf":null' in text and '"ninf":null' in text
    assert '"neg_zero":-0.0' in text and '"pos_zero":0.0' in text
    assert '"tiny":5e-324' in text and f'"big":{repr(1.7976931348623157e308)}' in text
    assert "é" in text and '\\"h\\\\' in text and "\\u0001" in text
    assert ", " not in text.replace('"a\\u0001b"', "")  # separators=(',',':')


def test_gap3_source_digest_verify_only_compares_never_recomputes():
    """`verify_source_digest`：只比對來源檔位元組，不重算 canonical 序列化。"""
    from momentum.Analysis.event_samples.import_contract import verify_source_digest

    text, digest = _payload(_base_cases())
    assert verify_source_digest(text.encode("utf-8"), digest) is True
    assert verify_source_digest(text.encode("utf-8"), digest.upper()) is True
    assert verify_source_digest((text + " ").encode("utf-8"), digest) is False
    assert verify_source_digest(text.encode("utf-8"), "not-a-digest") is False


def test_gap3_source_digest_rule_digest_path_is_separate():
    """🔴 `rule_digest`（綁 search_rule_summary）與 `source_file_digest`（綁完整列）不得共用序列化路徑。

    錨點落在**真正要判斷的東西**上——該出口實際「呼叫了什麼／回傳幾個值」（AST），
    而不是它附近的散文（散文含 `rule_digest` 三字並不代表它產出 rule_digest）。
    """
    import ast

    from momentum.Analysis.event_samples import pipeline as pipeline_mod

    tree = ast.parse(Path(pipeline_mod.__file__).read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "canonical_source_payload")
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)} | \
            {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    assert "canonical_source_bytes" in names
    assert not [n for n in names if "rule" in n.lower()], names
    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
    assert len(returns) == 1 and isinstance(returns[0].value, ast.Tuple) and len(returns[0].value.elts) == 2


# ---------------------------------------------------------------------------
# 承載點：/search 結果端點回應增兩鍵（**不新增 route**）
# ---------------------------------------------------------------------------
def test_gap3_source_digest_attached_to_search_result_response(monkeypatch):
    """SPEC「承載（R13 定案）」：既有結果端點回應增 `source_file_text`／`source_file_digest`。"""
    from api.models.responses import SearchResultData
    from api.routes import case_search as route_mod

    data = SearchResultData(
        cases=_base_cases(),
        summary={"total_cases": 2, "positive_cases": 1, "negative_cases": 1, "unique_symbols": 1,
                 "time_range": {"start": "2024-01-01", "end": "2024-01-02"}, "market_phase_distribution": {"bull": 1, "bear": 1}},
        sampling_quality={"time_separation_score": 1.0, "symbol_diversity_score": 1.0,
                          "market_phase_balance": 1.0, "overall_quality_score": 1.0},
        execution_time=0.1,
        cache_used=False,
    )
    assert data.source_file_digest is None
    route_mod._attach_canonical_source(data)
    assert len(data.source_file_digest) == 64
    assert hashlib.sha256(data.source_file_text.encode("utf-8")).hexdigest() == data.source_file_digest
    # 綁的是**回應實際送出的** case 列（pydantic 過濾後），故逐列鍵集合相等
    for row in json.loads(data.source_file_text):
        assert set(row) == set(data.cases[0].model_dump(mode="json"))


def test_gap3_source_digest_one_byte_change_flips_digest():
    """SPEC Task 1.3 驗證：改 1 byte 重傳 ⇒ `source_file_digest !=` 原值。"""
    text, digest = _payload(_base_cases())
    flipped = text[:-1] + ("]" if text[-1] != "]" else " ")
    assert hashlib.sha256(flipped.encode("utf-8")).hexdigest() != digest


def test_gap3_source_digest_event_id_template_is_single_source(monkeypatch):
    """D-2（CODEX-R1-P1-01）：`event_id` 公式只住契約，後端只有一份實作。"""
    import ast

    from momentum.Analysis.event_samples import import_contract as mod
    from momentum.Analysis.event_samples.import_contract import canonical_event_id, event_id_template

    tpl = event_id_template()
    assert tpl == "{symbol}:{timeframe}:{t0}"
    assert canonical_event_id("ETHUSDT", "12h", 1704067200000) == "ETHUSDT:12h:1704067200000"
    # 契約被改 ⇒ 產出跟著改（證明不是硬編字串）
    fake = dict(create_event_sample_pipeline().import_contract(), event_id_template="{t0}|{symbol}|{timeframe}")
    assert canonical_event_id("ETHUSDT", "12h", 1, contract=fake) == "1|ETHUSDT|12h"
    # 全模組只有一處 `.format(` 於 canonical_event_id 內；沒有第二份手寫拼接
    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    holders = [n.name for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef)
               and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "format"
                       for c in ast.walk(n))]
    assert holders == ["canonical_event_id"], holders


@pytest.mark.parametrize("endpoint", ["json", "csv"])
def test_gap3_source_digest_non_canonical_event_id_rejected(tmp_path, monkeypatch, endpoint):
    """D-2 identity 契約：symbol／timeframe／t0 正確但 `event_id` 自訂 ⇒ **拒且落檔數 == 0**。

    🔴 CODEX-R1-P1-01：先前兩端點皆接受任意 `event_id`，下游 split／dedupe／receipt 會把
    錯誤 identity 當真；「JSON 匯出 vs CSV 回灌集合相等」只證明同一個錯誤輸入被保留。
    """
    import io

    from fastapi.testclient import TestClient

    from api.main import app
    from api.services import case_import_service as svc_mod
    from tests.momentum.event_samples.test_import_contract import canonical_event

    monkeypatch.setattr(svc_mod, "_event_import_service", svc_mod.EventImportService(storage_dir=tmp_path / "events"))
    client = TestClient(app)

    good = canonical_event(0, label=1)
    bad = canonical_event(1, label=0, event_id="my-own-id-001")   # 其餘欄位完全合法

    if endpoint == "json":
        r = client.post("/api/v1/case/import-events/json", json={"records": [good, bad]})
    else:
        header = "eid,sym,tf,ts,ans"
        body = "\n".join(f"{x['event_id']},{x['symbol']},{x['timeframe']},{x['t0']},{x['label']}" for x in (good, bad))
        mapping = {"event_id": "eid", "symbol": "sym", "timeframe": "tf", "t0": "ts", "label": "ans"}
        defaults = {k: good[k] for k in ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                                         "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")}
        r = client.post("/api/v1/case/import-events/csv",
                        files={"file": ("x.csv", io.BytesIO((header + "\n" + body + "\n").encode("utf-8")), "text/csv")},
                        data={"column_mapping": json.dumps(mapping), "batch_defaults": json.dumps(defaults),
                              "lookahead_declaration": declaration_for_timeframes([good["timeframe"]])})

    assert r.status_code == 422, r.text
    failures = [f for f in r.json()["detail"]["failures"] if f["field"] == "event_id"]
    assert len(failures) == 1 and failures[0]["row"] == 1
    assert failures[0]["reason"] in set(create_event_sample_pipeline().import_contract()["import_failure_reasons"])
    assert bad["event_id"] in failures[0]["message"] and good["symbol"] in failures[0]["message"]
    assert client.get("/api/v1/case/events").json()["total"] == 0


def test_gap3_source_digest_canonical_event_id_not_enforced_on_platform_path():
    """平台產生器路徑**不**受 D-2 約束（其 ID 帶 label 後綴）——與 Task 1.8 同型之 scope 收斂。"""
    from momentum.Analysis.event_samples.import_contract import validate_event_import
    from tests.momentum.event_samples.test_import_contract import make_event

    rows = [make_event(0, label=1, event_id="ETHUSDT:12h:1738627200000:up5"),
            make_event(1, label=0, event_id="ETHUSDT:12h:1738670400000:up5")]
    assert len(validate_event_import(rows)) == 2                       # 預設不強制
    with pytest.raises(Exception):
        validate_event_import(rows, enforce_canonical_event_id=True)   # 顯式開啟才拒


def test_gap3_source_digest_event_id_set_equal_json_export_vs_csv_reimport(tmp_path, monkeypatch):
    """SPEC Task 1.3 驗證（V-4）：同一批事件之「JSON 匯出檔」與「CSV 回灌」之 `event_id` 集合 `==`。"""
    import io

    from fastapi.testclient import TestClient

    from api.main import app
    from api.services import case_import_service as svc_mod
    from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

    monkeypatch.setattr(svc_mod, "_event_import_service", svc_mod.EventImportService(storage_dir=tmp_path / "events"))
    client = TestClient(app)

    base = make_event(0)
    recs = [dict(make_event(i, label=i % 2), event_id=f"ETHUSDT:12h:{base['t0'] + i * 43200000}") for i in range(2)]

    j = client.post("/api/v1/case/import-events/json", json={"records": recs})
    assert j.status_code == 200, j.text
    json_ids = {r["event_id"] for r in client.get(f"/api/v1/case/events/{j.json()['import_id']}").json()["records"]}

    header = "eid,sym,tf,ts,ans"
    body = "\n".join(f"{r['event_id']},{r['symbol']},{r['timeframe']},{r['t0']},{r['label']}" for r in recs)
    mapping = {"event_id": "eid", "symbol": "sym", "timeframe": "tf", "t0": "ts", "label": "ans"}
    defaults = {k: base[k] for k in ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                                     "label_definition", "control_kind", "source_file_digest", "data_snapshot_digest")}
    c = client.post("/api/v1/case/import-events/csv",
                    files={"file": ("back.csv", io.BytesIO((header + "\n" + body + "\n").encode("utf-8")), "text/csv")},
                    data={"column_mapping": json.dumps(mapping), "batch_defaults": json.dumps(defaults),
                          "lookahead_declaration": declaration_for_timeframes([base["timeframe"]])})
    assert c.status_code == 200, c.text
    csv_ids = {r["event_id"] for r in client.get(f"/api/v1/case/events/{c.json()['import_id']}").json()["records"]}

    assert json_ids == csv_ids and len(json_ids) == 2


# ---------------------------------------------------------------------------
# golden fixture 生成（供前端 canonicalSourceCoverage）
# ---------------------------------------------------------------------------
def test_gap3_source_digest_regenerates_frontend_golden():
    """由**後端**產生 vitest 之 golden；內容未變則不寫檔（避免工作區無謂 dirty）。"""
    out = {
        "_doc": ("由 tests/api/test_gap3_source_digest.py 生成，勿手改。"
                 "digest 一律由後端 §G S-9 參考實作計算；前端只驗「拿到的就是後端算的那一個」。"),
        "target_column": TARGET_COLUMN,
        "variants": {},
    }
    for name, cases in _variants().items():
        text, digest = _payload(cases)
        out["variants"][name] = {"cases": cases, "source_file_text": text, "source_file_digest": digest}

    # 🔴 **先寫檔，再斷言**：順序反過來的話，後端序列化被改壞時本測會在寫檔前 raise，
    #    golden 停留在變異前的值 ⇒ 前端 canonicalSourceCoverage 假綠（mutation 實跑抓到）。
    blob = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    if not GOLDEN.is_file() or GOLDEN.read_text(encoding="utf-8") != blob:
        GOLDEN.write_text(blob, encoding="utf-8")

    digests = [v["source_file_digest"] for v in out["variants"].values()]
    assert json.loads(GOLDEN.read_text(encoding="utf-8"))["variants"]["base"]["source_file_digest"] == digests[0]
    assert len(set(digests)) == len(digests), "五個 variant 之 digest 須兩兩相異"


# ---------------------------------------------------------------------------
def test_gap3_source_digest_present_on_live_http_route(monkeypatch):
    """🔴 **走真的 HTTP route**，不是直呼 `_attach_canonical_source`。

    為什麼補這條（2026-08-29 使用者 UAT B5 回報「匯出失敗：source_file_digest 必須由後端提供」）：
    上一條測試只證明**那個函式**會算出 digest，**沒有證明 route 真的呼叫它**——
    「宣告了不等於執行期有」是本 epic 反覆踩的同一個坑（交接 §6.2）。
    route 若哪天把 `_attach_canonical_source(response.data)` 那行刪掉／搬到早退分支之後，
    上一條照樣綠，而使用者按匯出必然失敗（前端 fail-closed，見 `eventExport.ts::requireBackendSource`）。

    本條把 search service 換成回傳固定結果的替身 ⇒ 只測 route 之接線，不跑真實搜尋。
    """
    from fastapi.testclient import TestClient

    from api.main import app
    from api.models.responses import SearchResultData
    from api.routes import case_search as route_mod

    class _Info:
        class _S:
            value = "completed"
        status = _S()

    result = SearchResultData(
        cases=_base_cases(),
        summary={"total_cases": 2, "positive_cases": 1, "negative_cases": 1, "unique_symbols": 1,
                 "time_range": {"start": "2024-01-01", "end": "2024-01-02"},
                 "market_phase_distribution": {"bull": 1, "bear": 1}},
        sampling_quality={"time_separation_score": 1.0, "symbol_diversity_score": 1.0,
                          "market_phase_balance": 1.0, "overall_quality_score": 1.0},
        execution_time=0.1,
        cache_used=False,
    )
    monkeypatch.setattr(route_mod.search_service, "get_task_status", lambda _t: _Info(), raising=False)
    monkeypatch.setattr(route_mod.search_service, "get_task_result", lambda _t: result, raising=False)

    body = TestClient(app).get("/api/v1/search/task/probe-task/result").json()
    data = body["data"]
    # 🔴 斷言的是**回應 JSON**（response_model 過濾之後），不是 python 物件——
    #    模型沒宣告該欄時會被靜默濾掉（§4.2 假綠形態 5），那種漏法只有讀 JSON 才看得到。
    assert isinstance(data.get("source_file_text"), str) and data["source_file_text"] != ""
    digest = data.get("source_file_digest")
    assert isinstance(digest, str) and len(digest) == 64
    # 前端之 fail-closed 判準逐字相同（`eventExport.ts::requireBackendSource` 的正則）
    assert all(ch in "0123456789abcdef" for ch in digest)
    assert hashlib.sha256(data["source_file_text"].encode("utf-8")).hexdigest() == digest


# ---------------------------------------------------------------------------
def test_gap3_source_digest_every_search_result_route_attaches_digest():
    """🔴 **機械枚舉**：所有回傳 `SearchResultData` 給匯出流程的 route，都必須帶兩鍵。

    出生事故（2026-08-31 使用者 UAT B5）：Task 1.3 只把 `_attach_canonical_source`
    掛在 `/search/task/{id}/result` 一條上，而前端**兩階段搜尋**走的是
    `/two-stage/combined/{pos}/{neg}` ⇒ 那條回應缺兩鍵，使用者按匯出必然被前端
    fail-closed 擋下。**後端有實作、前端有守衛，中間沒接上。**

    🔴 判準刻意是**從 app 之 route 表導出**，不是人工列舉兩條路徑——
    人工清單的下場就是這次：新增 route 的人不會回來加一行。
    """
    import ast
    import inspect
    import textwrap

    from api.main import app
    from api.models.responses import SearchResponse

    def _calls_attach(src: str) -> bool:
        """🔴 判準是 **AST 上真的有一個呼叫節點**，不是原始碼含該字串。

        第一版寫成子字串比對，結果 `from .case_search import _attach_canonical_source`
        這一行就足以讓它通過——把呼叫刪掉、只留 import，閘照樣綠（實測）。
        那正是本 epic 反覆記名之「廉價綠燈」。
        """
        tree = ast.parse(textwrap.dedent(src))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            if name == "_attach_canonical_source":
                return True
        return False

    def _returns_result(src: str) -> bool:
        return "SearchResponse(" in src

    offenders = []
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None or getattr(route, "response_model", None) is not SearchResponse:
            continue
        if "GET" not in (getattr(route, "methods", None) or set()):
            continue
        src = inspect.getsource(endpoint)
        if _returns_result(src) and not _calls_attach(src):
            offenders.append(getattr(route, "path", str(route)))

    # 正向對照：真的有掃到 route（全部被過濾掉時 `offenders == []` 會空洞地通過）
    assert any(
        getattr(r, "response_model", None) is SearchResponse
        and "GET" in (getattr(r, "methods", None) or set())
        for r in app.routes
    ), "沒有掃到任何回傳 SearchResponse 之 GET route——過濾條件寫壞了"

    assert offenders == [], (
        "下列 route 回傳 SearchResultData 但沒有附 source_file_digest ⇒ "
        f"使用者在該路徑按匯出必然失敗：{offenders}"
    )
