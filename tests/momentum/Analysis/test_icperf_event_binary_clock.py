"""ICPERF Task 0.4 ㊵：事件路徑二元標籤之時鐘單位（`docs/ICPERF_SPEC.md` v5.56 Task 0.4 擴列表 ㊵）。

## 這批測試在防什麼

事件匯入批之二元標籤鍵＝特徵列時間戳之 **epoch 毫秒**；IC 交接 h5 之 `timestamps` 為 **epoch 秒**
（`ICFilterOrchestrator._load_features_hdf5`），而 stage0 只在帶 labels 檔時才把特徵索引換成 DatetimeIndex。
⇒ 事件路徑（labels_path 空）之切分預覽以秒索引去比毫秒鍵，全表命中 0；stage3 以 DatetimeIndex 之事件列與
原始 int 秒之 `test_timestamps` 取交集，交集空 ⇒ `label_mode` auto 靜默退回報酬版、明示 `imported_binary` 誤拒，
皆不報錯（真實 L 格事件批實測：`n_pos_batch` 95／`n_neg_batch` 97 而 `n_pos_selection`／`n_neg_selection` 0／0）。

## 路徑覆蓋（每條分支／邊界一案；oracle 皆為測試自寫之整數毫秒集合計數，不經產品 helper）

- `count_binary_classes_in_rows`：DatetimeIndex（ns／s／ms／us 四種解析度、tz-aware）、int 毫秒——兩類數量等於
  oracle；int 秒、標籤鍵為秒、混合單位、含 NaN、非整毫秒 DatetimeIndex、NaT ⇒ fail-closed（ValueError）。
- stage3 `_resolve_label_mode_and_bind_binary`：`test_timestamps` 為 int 秒（舊切分預覽之產物）、tz-aware UTC、
  DatetimeIndex ⇒ 交集與兩類數量等於 oracle、effective＝imported_binary；int 毫秒（與 IC 主線 int＝秒之約定不符）
  ⇒ fail-closed（AlignmentViolationError）。
- 真實資料（requires_kline）：L 格事件匯入批經服務事件路徑實跑——切分預覽與 stage3 兩類數量等於以 h5 原始秒
  時間戳與測試段界獨立計數之 oracle、effective＝imported_binary、二元三入口 calls ≥ 1。

mutation：還原 `count_binary_classes_in_rows` 之「非 DatetimeIndex 原值比對」或 stage3 之「原型別交集」或切分預覽
之「原始索引」任一 ⇒ 對應案紅。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.core.contracts import AlignmentViolationError
from momentum.core.split_preview import count_binary_classes_in_rows

REPO = Path(__file__).resolve().parents[3]
FREEZE_SCRIPT = REPO / "scripts" / "icperf_freeze_baseline.py"
HEAVY_MARKERS = ("slow", "requires_kline")

#: 明列邊界輸入：4 小時 K 線之 epoch 毫秒（2025-05-29 16:00 UTC 起，與真實 L 格事件批同量級）
BAR_MS = 4 * 3_600_000
BASE_MS = 1_748_534_400_000
N_BARS = 12
BAR_KEYS_MS: List[int] = [BASE_MS + i * BAR_MS for i in range(N_BARS)]
#: 測試段＝位置 6..11；標籤：位置 1、3（訓練段）與 6–11（測試段）之 0/1，另一鍵不在索引上
LABELS_MS: Dict[int, int] = {
    BAR_KEYS_MS[1]: 1, BAR_KEYS_MS[3]: 0,
    BAR_KEYS_MS[6]: 1, BAR_KEYS_MS[7]: 0, BAR_KEYS_MS[8]: 1,
    BAR_KEYS_MS[9]: 1, BAR_KEYS_MS[10]: 0, BAR_KEYS_MS[11]: 1,
    BASE_MS - BAR_MS: 1,
}
TEST_ROWS = list(range(6, 12))


def _oracle_counts(labels: Mapping[int, int], selected_ms: Sequence[int]) -> Dict[str, int]:
    """獨立 oracle：整數毫秒集合上之兩類計數（純 Python，不經 pandas 換算）。"""
    sel = {int(v) for v in selected_ms}
    return {"n_pos": sum(1 for k, v in labels.items() if int(v) == 1 and int(k) in sel),
            "n_neg": sum(1 for k, v in labels.items() if int(v) == 0 and int(k) in sel)}


def _dt_index(unit: str, tz: Any = None) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(np.array(BAR_KEYS_MS, dtype="datetime64[ms]").astype(f"datetime64[{unit}]"))
    if tz is not None:
        idx = idx.tz_localize("UTC").tz_convert(tz)
    return idx


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """同 test_icperf_correctness.py：本檔真實資料測試須經共用監看（`scripts/run_watched.py`）執行。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


# ── count_binary_classes_in_rows：可換算之輸入 ⇒ 兩類數量等於 oracle ─────────────────────────────────────
@pytest.mark.parametrize("case", ["dt_ns", "dt_s", "dt_ms", "dt_us", "dt_tz_taipei_ns", "dt_tz_utc_ms", "int_ms"])
def test_count_binary_classes_matches_oracle(case: str) -> None:
    if case == "int_ms":
        index: Any = pd.Index(np.array(BAR_KEYS_MS, dtype="int64"))
    elif case == "dt_tz_taipei_ns":
        index = _dt_index("ns", tz="Asia/Taipei")
    elif case == "dt_tz_utc_ms":
        index = _dt_index("ms", tz="UTC")
    else:
        index = _dt_index(case.split("_")[1])
    expected = _oracle_counts(LABELS_MS, [BAR_KEYS_MS[i] for i in TEST_ROWS])
    assert expected == {"n_pos": 4, "n_neg": 2}
    assert count_binary_classes_in_rows(LABELS_MS, index, TEST_ROWS) == expected


# ── count_binary_classes_in_rows：單位不明或錯誤 ⇒ fail-closed ─────────────────────────────────────────
@pytest.mark.parametrize("case", ["int_seconds", "label_keys_seconds", "mixed_units", "float_nan",
                                  "dt_sub_millisecond", "dt_nat"])
def test_count_binary_classes_fail_closed_on_unknown_unit(case: str) -> None:
    labels: Dict[int, int] = dict(LABELS_MS)
    index: Any
    if case == "int_seconds":
        index = pd.Index(np.array(BAR_KEYS_MS, dtype="int64") // 1000)
    elif case == "label_keys_seconds":
        index = pd.Index(np.array(BAR_KEYS_MS, dtype="int64"))
        labels = {int(k) // 1000: v for k, v in LABELS_MS.items()}
    elif case == "mixed_units":
        arr = np.array(BAR_KEYS_MS, dtype="int64")
        arr[7] //= 1000
        index = pd.Index(arr)
    elif case == "float_nan":
        arr = np.array(BAR_KEYS_MS, dtype="float64")
        arr[8] = np.nan
        index = pd.Index(arr)
    elif case == "dt_sub_millisecond":
        index = _dt_index("ns") + pd.Timedelta(microseconds=1)
    else:
        index = pd.DatetimeIndex(list(_dt_index("ns")[:8]) + [pd.NaT] * 4)
    with pytest.raises(ValueError):
        count_binary_classes_in_rows(labels, index, TEST_ROWS)


# ── stage3：測試段時間戳與事件列同一時鐘交集 ──────────────────────────────────────────────────────────────
#: stage3 之事件列＝全部 12 根，每列皆有 0/1（綁定要求每個被選事件列都有標籤）；測試段 6..11 為 4 正 2 反
STAGE3_PATTERN = (1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1)


def _stage3_inputs() -> tuple:
    feats = pd.DataFrame({"f1": np.linspace(0.0, 1.0, N_BARS)}, index=_dt_index("ns"))
    labels = {int(t): int(v) for t, v in zip(BAR_KEYS_MS, STAGE3_PATTERN)}
    owners = {int(t): f"e{i}" for i, t in enumerate(BAR_KEYS_MS)}
    return feats, labels, owners


def _bind(test_timestamps: Any, *, requested: str = "auto", floor: int = 2) -> dict:
    feats, labels, owners = _stage3_inputs()
    orch = ICFilterOrchestrator(ICConfig.model_validate({"event_filter": {"min_events_per_class": floor}}))
    return orch._resolve_label_mode_and_bind_binary(
        {"label_source": "event_label_value"},
        filtered_features=feats,
        event_binary_labels=labels,
        label_mode_requested=requested,
        label_mode_hint=None,
        split_context={"test_timestamps": test_timestamps},
        event_label_owners=owners,
        config=orch._config,
        label_source="event_label_value",
        event_label_binary_meta={"import_id": "imp-clock", "label_origin_values": ["0", "1"]},
    )


@pytest.mark.parametrize("case", ["int_seconds", "dt_ns", "dt_tz_utc"])
@pytest.mark.parametrize("requested", ["auto", "imported_binary"])
def test_stage3_selection_intersection_same_clock(case: str, requested: str) -> None:
    test_ms = [BAR_KEYS_MS[i] for i in TEST_ROWS]
    if case == "int_seconds":
        stamps: Any = pd.Index(np.array(test_ms, dtype="int64") // 1000)
    elif case == "dt_ns":
        stamps = _dt_index("ns")[TEST_ROWS]
    else:
        stamps = _dt_index("ns", tz="UTC")[TEST_ROWS]
    _, labels, _ = _stage3_inputs()
    expected = _oracle_counts(labels, test_ms)
    out = _bind(stamps, requested=requested)
    lm = out["label_mode"]
    assert (lm["n_pos_selection"], lm["n_neg_selection"]) == (expected["n_pos"], expected["n_neg"])
    assert lm["selection_scope"] == "test"
    assert lm["effective"] == "imported_binary", lm


def test_stage3_test_timestamps_in_milliseconds_fail_closed() -> None:
    """IC 主線之 int 索引約定為 epoch 秒（`_normalize_ic_time_index`）；毫秒 int 之測試段時間戳＝單位不符 ⇒ 拒。"""
    stamps = pd.Index(np.array([BAR_KEYS_MS[i] for i in TEST_ROWS], dtype="int64"))
    with pytest.raises(AlignmentViolationError):
        _bind(stamps)


# ── 真實資料（requires_kline）：L 格事件匯入批經服務事件路徑 ──────────────────────────────────────────────
#: 事件匯入批請求之欄數（feature_filter 排序前綴；欄數不影響二元計數，只影響耗時）
REAL_N_COLS = 20


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _epoch_seconds(value: Any) -> int:
    """時刻 → epoch 秒（tz-naive 視為 UTC；以 Timedelta 整除，不經 asi8 解析度假設）。"""
    ts = pd.Timestamp(value)
    if ts.tz is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return int((ts - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


def _h5_seconds(features_path: str) -> np.ndarray:
    """交接 h5 之原始 `timestamps`（h5py 直讀，不經產品讀取器）。"""
    found: List[np.ndarray] = []

    def _visit(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Dataset) and name.rsplit("/", 1)[-1] == "timestamps":
            found.append(np.asarray(obj[:], dtype="int64"))

    with h5py.File(features_path, "r") as f:
        f.visititems(_visit)
    assert len(found) == 1, f"交接 h5 之 timestamps 資料集須恰一份，實得 {len(found)}"
    return found[0]


@pytest.mark.requires_kline
def test_event_import_binary_counts_on_real_l_cell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import momentum.Analysis.ic_filter_orchestrator as orch_mod

    fb = _load("icperf_freeze_baseline", FREEZE_SCRIPT)
    request = fb.small_request("event_import_report", fb.default_request("event_import_report"), REAL_N_COLS)
    cwd = fb._prepare_cwd(tmp_path / "cwd")
    monkeypatch.chdir(cwd)

    calls = {"mann_whitney_table": 0, "block_permutation_table": 0, "_run_binary_permutation_and_negative_control": 0}
    captured: Dict[str, Any] = {}
    for name in ("mann_whitney_table", "block_permutation_table"):
        orig = getattr(orch_mod, name)

        def _spy(*a: Any, _orig: Any = orig, _name: str = name, **k: Any) -> Any:
            calls[_name] += 1
            return _orig(*a, **k)

        monkeypatch.setattr(orch_mod, name, _spy)
    orig_perm = ICFilterOrchestrator._run_binary_permutation_and_negative_control

    def _perm(self: Any, *a: Any, **k: Any) -> Any:
        calls["_run_binary_permutation_and_negative_control"] += 1
        return orig_perm(self, *a, **k)

    monkeypatch.setattr(ICFilterOrchestrator, "_run_binary_permutation_and_negative_control", _perm)
    orig_analyze = ICFilterOrchestrator.analyze

    def _analyze(self: Any, features_path: str, *a: Any, **k: Any) -> Any:
        captured.setdefault("features_path", str(features_path))
        captured.setdefault("event_binary_labels", dict(k.get("event_binary_labels") or {}))
        return orig_analyze(self, features_path, *a, **k)

    monkeypatch.setattr(ICFilterOrchestrator, "analyze", _analyze)

    info = fb.event_import_run(request, tmp_path / "registry.json")
    report, analyzer = info["result"], info["analyzer"]
    labels = {int(k): int(v) for k, v in captured["event_binary_labels"].items()}
    assert labels and {0, 1} <= set(labels.values()), "事件批無兩類 0/1 標籤（資料不足，須補批）"

    # oracle：h5 原始秒時間戳 × 1000 落於測試段界（切分計畫之 time_bounds：UTC 時刻）內之列
    sc = analyzer._ic_cache["split_context"]
    lo, hi = (_epoch_seconds(v) for v in sc["test_plan"].time_bounds)
    secs = _h5_seconds(captured["features_path"])
    test_ms = [int(s) * 1000 for s in secs if lo <= int(s) <= hi]
    assert len(test_ms) == len(sc["test_plan"].row_index), "測試段界內之列數與切分計畫列數不等"
    expected = _oracle_counts(labels, test_ms)
    assert min(expected.values()) > 0, f"測試段兩類 oracle {expected}（資料不足，須補批）"

    assert sc["selection_preview"] == expected, (sc["selection_preview"], expected)
    lm = report["metadata"]["event_filter"]["label_mode"]
    assert (lm["n_pos_selection"], lm["n_neg_selection"]) == (expected["n_pos"], expected["n_neg"]), lm
    assert lm["effective"] == "imported_binary", lm
    assert all(n >= 1 for n in calls.values()), calls
