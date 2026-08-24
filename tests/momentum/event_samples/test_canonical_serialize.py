"""GAP-3 UX §G S-9 位元組 encoder 之驗收（SPEC L1263–1274 之 ①–⑦）。

🔴 ① 之 golden **不是**由被測函式自產——expected 是照 S-9 逐條**手寫**出來的位元組字面，
所以它是獨立 oracle：實作若偏離 S-9 任一條，逐位元組比對就會紅。
（自產 golden 只能證明「函式跟自己一致」，證不了「跟規則一致」。）
"""

from __future__ import annotations

import json
import math

import pytest

from momentum.Analysis.event_samples.canonical_serialize import (
    _json_dumps,
    canonical_event_table_bytes,
    canonical_event_table_sha256,
    normalize_for_canonical,
)
from momentum.Analysis.event_samples.tables import event_forward_return_table


def _fixture() -> dict:
    """S-9 要求之涵蓋面：非 ASCII、`"`、`\\`、控制字元、NaN／±Inf、-0.0、None、list 序、巢狀。"""
    return {
        "h": 1,
        "unicode": "é",
        "quote": 'a"b',
        "backslash": "a\\b",
        "control": "a\u0001b",
        "nan": float("nan"),
        "pinf": float("inf"),
        "ninf": float("-inf"),
        "negzero": -0.0,
        "none": None,
        "lst": [3, 1, 2],
        "nested": {"b": 1.5, "a": True},
    }


#: 照 S-9 第 2–6 條**手寫**之期望輸出（獨立 oracle，非被測函式自產）。
_EXPECTED_TEXT = (
    '{"h":1,'
    '"unicode":"é",'
    '"quote":"a\\"b",'
    '"backslash":"a\\\\b",'
    '"control":"a\\u0001b",'
    '"nan":null,'
    '"pinf":null,'
    '"ninf":null,'
    '"negzero":-0.0,'
    '"none":null,'
    '"lst":[3,1,2],'
    '"nested":{"b":1.5,"a":true}}'
)
_EXPECTED_BYTES = _EXPECTED_TEXT.encode("utf-8")


# ── ① fixture bytes 與 golden 逐位元組相等 ─────────────────────────────────
def test_canonical_serialize_01_bytes_equal_golden() -> None:
    got = canonical_event_table_bytes(_fixture())
    assert got == _EXPECTED_BYTES
    # 無 BOM、無尾端 whitespace
    assert not got.startswith(b"\xef\xbb\xbf")
    assert got[-1:] == b"}"


# ── ② separators 改成 (', ', ': ') ⇒ hash 變 ──────────────────────────────
def test_canonical_serialize_02_separators_change_hash() -> None:
    ours = canonical_event_table_sha256(_fixture())
    loose = json.dumps(
        normalize_for_canonical(_fixture()),
        ensure_ascii=False, separators=(", ", ": "), allow_nan=False, sort_keys=False,
    ).encode("utf-8")
    import hashlib
    assert hashlib.sha256(loose).hexdigest() != ours


# ── ③ 附加尾端 \n ⇒ hash 變 ────────────────────────────────────────────────
def test_canonical_serialize_03_trailing_newline_changes_hash() -> None:
    import hashlib
    base = canonical_event_table_bytes(_fixture())
    assert hashlib.sha256(base + b"\n").hexdigest() != canonical_event_table_sha256(_fixture())


# ── ④ ensure_ascii=True ⇒ hash 變 ─────────────────────────────────────────
def test_canonical_serialize_04_ensure_ascii_changes_hash() -> None:
    import hashlib
    escaped = json.dumps(
        normalize_for_canonical(_fixture()),
        ensure_ascii=True, separators=(",", ":"), allow_nan=False, sort_keys=False,
    ).encode("utf-8")
    assert hashlib.sha256(escaped).hexdigest() != canonical_event_table_sha256(_fixture())
    assert b"\\u00e9" in escaped  # 證明差異確實來自 \u 脫逃
    assert "é".encode("utf-8") in canonical_event_table_bytes(_fixture())


# ── ⑤ NaN 未轉 None ⇒ allow_nan=False 之 dumps **raise**（非靜默輸出 NaN 字面）─
def test_canonical_serialize_05_unnormalized_nan_raises() -> None:
    with pytest.raises(ValueError):
        _json_dumps({"nan": float("nan")})
    # 正規化後就不會 raise，且輸出 null（防「恆紅型假保證」）
    assert _json_dumps(normalize_for_canonical({"nan": float("nan")})) == '{"nan":null}'


# ── ⑥ -0.0 被正規化成 0.0 ⇒ hash 變 ───────────────────────────────────────
def test_canonical_serialize_06_negative_zero_preserved() -> None:
    assert canonical_event_table_bytes({"z": -0.0}) == b'{"z":-0.0}'
    assert canonical_event_table_sha256({"z": -0.0}) != canonical_event_table_sha256({"z": 0.0})
    assert math.copysign(1.0, normalize_for_canonical(-0.0)) == -1.0


# ── ⑦ 重複 horizon ⇒ event_forward_return_table raise ValueError ──────────
def test_canonical_serialize_07_duplicate_horizon_raises() -> None:
    with pytest.raises(ValueError):
        event_forward_return_table(None, None, None, None, {"horizons": [1, 3, 3, 7]})
    # 對照組：不重複時**不得**因本守衛而擋（否則是恆紅）
    with pytest.raises(Exception) as ei:
        event_forward_return_table(None, None, None, None, {"horizons": [1, 3, 7]})
    assert "不得重複" not in str(ei.value)


# ── 型別白名單：非白名單型別須 raise，禁依賴 encoder 隱式轉換 ────────────────
def test_canonical_serialize_08_type_whitelist_fail_closed() -> None:
    from decimal import Decimal

    with pytest.raises(TypeError):
        canonical_event_table_bytes({"d": Decimal("1.5")})
    with pytest.raises(TypeError):
        canonical_event_table_bytes({1: "int key"})


# ── 缺席鍵保持缺席（不得補 null）＋ 鍵序不得被重排 ──────────────────────────
def test_canonical_serialize_09_absent_key_and_key_order() -> None:
    assert canonical_event_table_bytes({}) == b"{}"
    # S-2 已保證鍵序；encoder 不得再 sort（b 在 a 之前須原樣保留）
    assert canonical_event_table_bytes({"b": 1, "a": 2}) == b'{"b":1,"a":2}'
