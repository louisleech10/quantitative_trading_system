"""PRE-PROV（docs/FFDSTAR_SPEC.md Task 2.3）：IC-first JSON 快取（`ic_selected_features_*.json`）之沿用須值身分相符。

改前缺陷：`CACHE_IDENTITY_FIELDS`（ic_engine.py:39-50）十欄皆為設定／請求身分，無 run 內容身分 ⇒ 同 config_hash
重生而值改變之 run 仍沿用舊 IC 分數；`_build_data_fingerprint` 之 `source_checksum` 取 manifest 不存在之鍵。

驗證（SPEC Task 2.3）：同身分沿用；`content_sha256` 不同 ⇒ 拒用並拋既有 `ICCacheRawUnavailableError`；
舊 JSON 無該欄 ⇒ 拒用。邊界（⇒ boundary_01–02）：①raw 已刪且 manifest raw 節點無 `content_sha256`；
②threshold 不同而其餘相同（仍沿用）。mutation：自 `CACHE_IDENTITY_FIELDS` 移除新欄 ⇒ 不同身分案翻轉。

資料：真實 kline 短窗 IC-first 格（`preprov_helpers` 之 `ic_first`：`cleanup_raw=True` ⇒ raw 已刪、JSON 快取在）。
請求以生成期間觀測到之那一次 `compute_ic_from_l7_raw` 呼叫原樣重放（同 label 物件、同選窗、同 horizon），
故十欄身分與快取逐欄相同；「內容身分不同」以改寫該 run manifest 之 raw `content_sha256` 表示同 config_hash 重生
（快取本身不動），每案前自備份還原 manifest 與 JSON。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterator

import numpy as np
import pytest

from momentum.Analysis import ic_engine as ice
from momentum.Analysis.ic_engine import ICEngine
from momentum.core.icfirstalign_errors import ICCacheRawUnavailableError
from momentum.FeatureEngineering.feature_reader import FeatureReader
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.timeout(1800)

NEW_FIELD = "content_sha256"
# 改前碼態之十欄（ic_engine.py:39-50）；本 Task 不得放寬任一欄
HEAD_IDENTITY_FIELDS = ("symbol", "tf", "config_hash", "method", "label_horizon", "selection_window_start",
                        "selection_window_end", "split_id", "feature_axis_sha256", "label_sha256")
OTHER_CONTENT = "e" * 64


@pytest.fixture(scope="module")
def cached(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    """IC-first 真實短窗 run：生成期間 IC 已全算並落 JSON 快取、raw 已刪；備份 manifest 與 JSON 供每案還原。"""
    run = ph.generate_short_run(tmp_path_factory.mktemp("preprov_ic_cache"), "ic_first")
    calls = ph.observation(run).ic_calls
    assert len(calls) == 1, f"前提不成立：IC-first 生成期間 compute_ic_from_l7_raw 呼叫 {len(calls)} 次"
    run_dir = Path(run.run_dir)
    selected = run_dir / f"ic_selected_features_{run.symbol}_{run.tf}.json"
    manifest = run_dir / FeatureReader.V2_MANIFEST_NAME
    assert not (run_dir / "raw").exists(), "前提不成立：cleanup_raw 後 raw 仍在（快取沿用路徑不會觸發）"
    assert selected.is_file(), "前提不成立：IC-first 未落 JSON 快取"
    backup = tmp_path_factory.mktemp("preprov_ic_cache_backup")
    shutil.copy2(selected, backup / "selected.json")
    shutil.copy2(manifest, backup / "manifest.json")
    return {"run": run, "call": calls[0], "selected": selected, "manifest": manifest, "backup": backup}


@pytest.fixture()
def c(cached: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    shutil.copy2(cached["backup"] / "selected.json", cached["selected"])
    shutil.copy2(cached["backup"] / "manifest.json", cached["manifest"])
    yield cached
    shutil.copy2(cached["backup"] / "selected.json", cached["selected"])
    shutil.copy2(cached["backup"] / "manifest.json", cached["manifest"])


def replay(c: Dict[str, Any], **overrides: Any) -> Any:
    """原樣重放生成期間之那一次 IC 請求（`overrides` 只覆寫指定 kwargs）。"""
    args, kwargs = c["call"]
    merged = dict(kwargs)
    merged.update(overrides)
    return ICEngine({"methods": ["spearman"]}).compute_ic_from_l7_raw(*args, **merged)


def manifest_raw_content(c: Dict[str, Any]) -> Any:
    return json.loads(c["manifest"].read_text(encoding="utf-8"))["artifacts"]["raw"].get(NEW_FIELD)


def set_manifest_raw_content(c: Dict[str, Any], value: Any) -> None:
    """改寫 manifest raw 節點之內容身分（`None` ⇒ 刪鍵，表舊 run）；其餘位元不動之語意。"""
    manifest = json.loads(c["manifest"].read_text(encoding="utf-8"))
    if value is None:
        manifest["artifacts"]["raw"].pop(NEW_FIELD, None)
    else:
        manifest["artifacts"]["raw"][NEW_FIELD] = value
    c["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def cached_fingerprint(c: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(c["selected"].read_text(encoding="utf-8"))["data_fingerprint"]


def _different_content_case(c: Dict[str, Any]) -> str:
    """不同身分案：同 config_hash 重生而內容改變（manifest raw `content_sha256` 換值、快取不動）；回 cache_status 或 'rejected'。"""
    original = manifest_raw_content(c)
    assert original and original != OTHER_CONTENT, "前提不成立：manifest raw 節點無 content_sha256（Task 1.3 未落地）"
    set_manifest_raw_content(c, OTHER_CONTENT)
    try:
        return str(replay(c).data_fingerprint["cache_status"])
    except ICCacheRawUnavailableError:
        return "rejected"


# ---------------------------------------------------------------- 驗證


def test_identity_fields_extended_not_relaxed() -> None:
    """身分欄加 `content_sha256`，且改前十欄一欄不少（不得放寬）。"""
    assert NEW_FIELD in ice.CACHE_IDENTITY_FIELDS
    assert set(HEAD_IDENTITY_FIELDS) <= set(ice.CACHE_IDENTITY_FIELDS)


def test_cache_written_with_content_identity(c: Dict[str, Any]) -> None:
    """全算時快取 fingerprint 寫入 `content_sha256`＝manifest raw 節點之值；`source_checksum` 來源改為同值。"""
    fp = cached_fingerprint(c)
    expected = manifest_raw_content(c)
    assert expected, "前提不成立：manifest raw 節點無 content_sha256（Task 1.3 未落地）"
    assert fp.get(NEW_FIELD) == expected
    assert fp.get("source_checksum") == expected


def test_same_identity_reused(c: Dict[str, Any]) -> None:
    """同身分（十欄＋內容身分皆同）⇒ 沿用快取，不需 raw。"""
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    result = replay(c)
    assert result.data_fingerprint["cache_status"] == "reused_from_cache"
    assert result.data_fingerprint.get(NEW_FIELD) == manifest_raw_content(c)
    assert result.ic_scores == payload["ic_scores"]


def test_different_content_sha256_rejected(c: Dict[str, Any]) -> None:
    """`content_sha256` 不同（同設定重生、值已變）⇒ 拒用並拋既有 `ICCacheRawUnavailableError`。"""
    assert _different_content_case(c) == "rejected"


def test_old_json_without_field_rejected(c: Dict[str, Any]) -> None:
    """舊 JSON（fingerprint 無 `content_sha256`）⇒ 拒用。"""
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    payload["data_fingerprint"].pop(NEW_FIELD, None)
    c["selected"].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ICCacheRawUnavailableError):
        replay(c)


# ---------------------------------------------------------------- 邊界


def test_boundary_01_raw_deleted_manifest_lacks_content_sha256(c: Dict[str, Any]) -> None:
    """邊界①：raw 已刪且 manifest raw 節點無 `content_sha256`（舊 run）⇒ 缺即拒用，拋 `ICCacheRawUnavailableError`。"""
    assert not (Path(c["run"].run_dir) / "raw").exists()
    set_manifest_raw_content(c, None)
    with pytest.raises(ICCacheRawUnavailableError):
        replay(c)


def test_boundary_02_threshold_only_differs_still_reused(c: Dict[str, Any]) -> None:
    """邊界②：只 threshold 不同 ⇒ 仍沿用，且只依快取分數重選。"""
    payload = json.loads(c["selected"].read_text(encoding="utf-8"))
    result = replay(c, ic_threshold=0.05)
    assert result.data_fingerprint["cache_status"] == "reused_from_cache"
    expected = sorted(f for f, v in payload["ic_scores"].items()
                      if v is not None and np.isfinite(v) and abs(v) >= 0.05)
    assert sorted(result.selected) == expected


# ---------------------------------------------------------------- mutation


def test_mutation_new_field_removed_from_identity(c: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：自 `CACHE_IDENTITY_FIELDS` 移除 `content_sha256` ⇒ 不同身分案被沿用（拒用斷言翻轉）。"""
    monkeypatch.setattr(ice, "CACHE_IDENTITY_FIELDS", tuple(f for f in ice.CACHE_IDENTITY_FIELDS if f != NEW_FIELD))
    assert _different_content_case(c) == "reused_from_cache"
