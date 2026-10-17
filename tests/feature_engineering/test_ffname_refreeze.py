"""FF-NAME Task 4.3 — golden 重凍與全量 reference（docs/FFNAME_SPEC.md Task 4.3）。

重凍對象＝事實盤點 §E 所列 golden（清單之單一落點：`tests/_golden/ffname/contract.json` 之 `refreeze.goldens`）。
驗證：每檔重凍收據附「值雜湊不變、只欄名與名雜湊變」之對照；全量 reference（1h＋12h，設定沿用既有 reference）
100% `parse` 往返；failopen 系列測試綠（gate_cmd 另跑）。
邊界：重凍前之值雜湊若有任一不同 ⇒ 停、回 Phase 2（收據不得含值不符項）。
收據落點 `refreeze.receipt`（SPEC 未指名，TODO 定；收據由重凍程序產生，本檔只驗其內容並綁定現行 golden 位元組）。
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import momentum.FeatureEngineering.feature_naming as fn
from tests.feature_engineering.ffname_helpers import CONTRACT, REPO

REFREEZE = CONTRACT["refreeze"]
RECEIPT = REPO / REFREEZE["receipt"]


def _receipt() -> Dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refreeze_violations(receipt: Dict[str, Any]) -> List[str]:
    """收據違規：缺檔、值雜湊不符、名稱未變卻重凍、現行位元組與收據不符。"""
    bad: List[str] = []
    files = {e["path"]: e for e in receipt.get("files", [])}
    for rel in REFREEZE["goldens"]:
        entry = files.get(rel)
        if entry is None:
            bad.append(f"missing:{rel}")
            continue
        if entry.get("value_hash_mismatch", 1) != 0:
            bad.append(f"value_changed:{rel}")
        if entry.get("renamed_columns", 0) <= 0 and not entry.get("name_hash_changed", False):
            bad.append(f"no_name_change:{rel}")
        if entry.get("new_sha256") != _sha(REPO / rel):
            bad.append(f"bytes_unbound:{rel}")
    return bad


def test_receipt_shape():
    receipt = _receipt()
    for key in ("schema_version", "command", "exit_code", "files", "full_reference"):
        assert key in receipt, key
    assert receipt["exit_code"] == 0


def test_every_golden_refrozen_with_values_unchanged():
    assert refreeze_violations(_receipt()) == []


def test_full_reference_parse_roundtrip_100pct():
    full = _receipt()["full_reference"]
    assert sorted(full["timeframes"]) == sorted(REFREEZE["full_reference"]["timeframes"])
    assert full["total_columns"] > 0
    assert full["parse_failures"] == 0 and full["roundtrip_failures"] == 0
    assert full["feature_naming_version"] == fn.CURRENT_FEATURE_NAMING_VERSION


def test_boundary_01_value_hash_difference_stops_refreeze():
    receipt = copy.deepcopy(_receipt())
    victim = receipt["files"][0]
    victim["value_hash_mismatch"] = 1
    assert f"value_changed:{victim['path']}" in refreeze_violations(receipt)


def test_mutation_unbound_golden_bytes_detected(monkeypatch, tmp_path):
    """mutant：重凍後另改 golden 位元組（收據未綁定）⇒ bytes_unbound。"""
    receipt = _receipt()
    target = REFREEZE["goldens"][0]
    fake = tmp_path / "golden_copy.json"
    fake.write_bytes((REPO / target).read_bytes() + b"\n")
    real_sha = _sha
    monkeypatch.setattr(sys.modules[__name__], "_sha", lambda p: real_sha(fake) if str(p).endswith(target) else real_sha(p))
    assert f"bytes_unbound:{target}" in refreeze_violations(receipt)
