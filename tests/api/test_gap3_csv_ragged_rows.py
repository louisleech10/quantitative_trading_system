"""GAP-3 UX B4 R1 群集 D（-k gap3_csv_ragged）：欄數不齊之 CSV 一律 fail-closed。

R1 三家共提（`GROK-R1-P1-01`／`COMPOSER-R1-P1-01`／`CODEX-R1-P2-05`）：
標頭五欄、資料六欄時，`pd.read_csv` **預設會把第一欄當 index、整列左移，且零 warning**
——`label` 實測由 `0` 翻成 `1`。使用者在確認畫面看到「反例 1 筆」，後端 ingest 到的是正例。

本檔把該行為釘成**拒收**，並附「不修就會怎樣」之對照組——否則這條閘看起來像恆綠。
🔴 `on_bad_lines="error"` **無效**（實測仍左移）；有效組合＝`index_col=False` ＋ 把
`ParserWarning` 升為例外，兩者缺一不可（見 `EventImportService._read_csv_chunks`）。
"""

from __future__ import annotations

import io
import json
import warnings

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from momentum.Analysis.event_samples.import_contract import canonical_event_id
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)

HEADER = ["我的編號", "幣種", "K線週期", "毫秒時間", "是不是正例", "來源檔雜湊"]
MAPPING = {
    "event_id": "我的編號", "symbol": "幣種", "timeframe": "K線週期",
    "t0": "毫秒時間", "label": "是不是正例", "source_file_digest": "來源檔雜湊",
}
DEFAULT_FIELDS = ("decision_offset_bars", "entry_price_semantic", "direction", "scenario",
                  "label_definition", "control_kind", "data_snapshot_digest")
DIGEST = "a" * 64


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _defaults() -> dict:
    base = make_event(0)
    return {k: base[k] for k in DEFAULT_FIELDS}


def _csv(extra_cells: int = 0, missing_cells: int = 0) -> bytes:
    """兩列 CSV；`extra_cells`／`missing_cells` 套用於**所有**資料列。

    🔴 必須每一列都多一格才會重現左移：pandas 只有在「**全部**資料列都比標頭多」時
    才推論首欄是 index；只有某一列多出來時它會直接 `ParserError`（那條路本來就擋得住）。
    這個區別是本群集的關鍵——擋得住的那半不是問題，靜默左移的那半才是。
    """
    base = make_event(0)
    lines = [",".join(HEADER)]
    for i in range(2):
        t0 = base["t0"] + i * 43200000
        cells = [canonical_event_id("ETHUSDT", "12h", t0), "ETHUSDT", "12h", str(t0), str(i % 2), DIGEST]
        if extra_cells:
            cells = cells + ["1"] * extra_cells
        if missing_cells:
            cells = cells[: len(cells) - missing_cells]
        lines.append(",".join(cells))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _post(content: bytes):
    return client.post(
        "/api/v1/case/import-events/csv",
        files={"file": ("mine.csv", io.BytesIO(content), "text/csv")},
        data={"column_mapping": json.dumps(MAPPING, ensure_ascii=False),
              "batch_defaults": json.dumps(_defaults())},
    )


def _stored_count(svc) -> int:
    return len(list(svc.storage_dir.glob("*.json"))) if svc.storage_dir.is_dir() else 0


# ── ① 長列 ⇒ 拒收、落檔 0 ────────────────────────────────────────────────────
def test_gap3_csv_ragged_long_row_rejected(_isolated_storage):
    r = _post(_csv(extra_cells=1))
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["kind"] == "parse_error"
    assert _stored_count(_isolated_storage) == 0


# ── ①b 對照組：不修的話會怎樣（證明①擋的是真東西，不是恆紅） ────────────────
def test_gap3_csv_ragged_default_pandas_would_shift_left_silently():
    """🔴 本條**不呼叫產品碼**，只證明「預設參數會靜默錯位」這個前提為真。

    若哪天 pandas 改掉這個行為，本條會轉紅 ⇒ 提醒重新評估 `_read_csv_chunks` 的參數。
    """
    content = _csv(extra_cells=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        chunk = next(iter(pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False, chunksize=5000)))
    # 每列都多一格 ⇒ 首欄被當 index、整列左移：`是不是正例` 欄讀到的是**右邊那一格**（此處為 digest）
    assert chunk["是不是正例"].tolist() == [DIGEST, DIGEST]  # 真值為 ["0", "1"]——label 已完全不是 label
    assert chunk.index.tolist()[0].startswith("ETHUSDT:")   # index 被 event_id 佔用＝左移之指紋


# ── ② 等寬列 ⇒ 收（正例對照，防「恆紅型假保證」） ───────────────────────────
def test_gap3_csv_ragged_even_rows_accepted(_isolated_storage):
    r = _post(_csv())
    assert r.status_code == 200, r.text
    assert _stored_count(_isolated_storage) == 1


# ── ③ 短列：本層擋不住（pandas 靜默補空），由契約層逐欄拒 ⇒ 落檔仍為 0 ──────
def test_gap3_csv_ragged_short_row_rejected(_isolated_storage):
    """欄數**比標頭少**之列同樣拒收。

    pandas 對這種列是靜默補空字串（不 raise、不 warn），擋它的是以 `csv` 標準庫
    獨立驗列寬的那道守衛——規則只有一條「每列欄數 == 標頭欄數」，長短兩側同一條。
    """
    r = _post(_csv(missing_cells=2))
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["kind"] == "parse_error"
    assert _stored_count(_isolated_storage) == 0


# ── ⑤ R2 `CODEX-R2-P1-02`：**尾端空欄**亦拒收（pandas 對這種列完全靜默） ─────
def test_gap3_csv_ragged_trailing_empty_is_fail_closed(_isolated_storage):
    """🔴 `a,b\\n1,2,\\n` 這種「每列多一個空格子」pandas **一聲不吭地吞掉**（不 raise、不 warn）。

    吞掉的雖是空值、不造成錯位，但這代表「欄數不齊」在後端不是一條規則而是三種行為
    （多非空 ⇒ warning／多一空 ⇒ 靜默／只有某列多 ⇒ error），於是前端擋、後端收 ⇒ 兩端規則不一致。
    修法＝以 `csv` 標準庫獨立驗列寬（單一規則、與 pandas 版本無關），本條即該守衛之反例。
    """
    base = make_event(0)
    t0 = base["t0"]
    lines = [",".join(HEADER)]
    for i in range(2):
        cells = [canonical_event_id("ETHUSDT", "12h", t0 + i * 43200000), "ETHUSDT", "12h",
                 str(t0 + i * 43200000), str(i % 2), DIGEST, ""]      # 尾端多一個空格子
        lines.append(",".join(cells))
    r = _post(("\n".join(lines) + "\n").encode("utf-8"))
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["kind"] == "parse_error"
    assert "欄數不齊" in r.json()["detail"]["message"]
    assert _stored_count(_isolated_storage) == 0


# ── ⑥ 只有標頭、沒有資料列 ⇒ 走既有 `empty_import`，列寬守衛不得誤擋 ─────────
def test_gap3_csv_ragged_header_only_not_blocked_by_width_guard(_isolated_storage):
    """正例對照之一：沒有資料列時列寬守衛**沒有可比對的列**，不得因此報「欄數不齊」。

    （擋它的是契約層之 `empty_import`——本條要證的是「守衛沒有把合法輸入一起擋掉」。）
    """
    r = _post((",".join(HEADER) + "\n").encode("utf-8"))
    assert r.status_code == 422, r.text
    assert "欄數不齊" not in json.dumps(r.json(), ensure_ascii=False)
    assert _stored_count(_isolated_storage) == 0


# ── ④ 引號內之 CR 由後端原樣保留（前端預覽解析須一致） ──────────────────────
def test_gap3_csv_ragged_quoted_cr_preserved_by_backend(_isolated_storage):
    content = ('我的編號,幣種,是不是正例\n"E1\r",ETHUSDT,1\n').encode("utf-8")
    records, _ = _isolated_storage.csv_records_from_mapping(
        content, {"event_id": "我的編號", "symbol": "幣種", "label": "是不是正例"}, None)
    assert records[0]["event_id"] == "E1\r"
