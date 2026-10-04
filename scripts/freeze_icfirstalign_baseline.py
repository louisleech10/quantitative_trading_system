"""ICFIRSTALIGN 乙之改前基準凍結（docs/ICFIRSTALIGN_SPEC.md v18 §G、Task 4.0、Task 4.1）。

只准以 HEAD（改前生產碼）執行；真實 kline、一切寫入隔離於暫存目錄。
stage：
- `l3-default`：S2（預設 L3 臂：numba 多窗串流）之 raw L3 欄逐欄 float32 bytes sha256 ⇒
  tests/_golden/icfirstalign/l3_default_arm.json（Task 4.0「預設臂之 registry L3 群組與改前逐位元組相等」）。
- `probe`、`calibration`：§G 預熱探測與校準封包之 HEAD 甲／乙基準（Task 4.1），見各 stage 函式。

用法：env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python scripts/freeze_icfirstalign_baseline.py <stage>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import numpy as np

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "tests" / "_golden" / "icfirstalign"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def column_digest(values: Any) -> str:
    arr = np.ascontiguousarray(np.asarray(values, dtype=np.float32))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def l3_digests(root: Path, config_hash: str) -> Dict[str, str]:
    """raw 成品中 L3 群組之全部欄 → float32 bytes sha256（依欄名排序）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from tests.feature_engineering import icfirstalign_helpers as h

    reader = FeatureReader(str(root))
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, config_hash, artifact_kind="raw")
    cols = sorted(c for name, g in manifest["artifacts"]["raw"]["groups"].items() if "_L3_" in name
                  for c in g.get("columns", []))
    frame = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, config_hash, cols)
    return {c: column_digest(frame[c].to_numpy()) for c in cols}


def stage_l3_default() -> Dict[str, Any]:
    import pytest

    from tests.feature_engineering import icfirstalign_helpers as h

    mp = pytest.MonkeyPatch()
    try:
        tmp = Path(tempfile.mkdtemp(prefix="icfa_freeze_l3_"))
        root = h.isolated(mp, tmp)
        for key in ("FFACT_USE_NUMBA_ROLLING", "FFACT_L3_STREAMING", "FFACT_L3_MULTI_WINDOW", "FFACT_L3_PERSIST_MODE"):
            mp.delenv(key, raising=False)
        _, result = h.generate_s2(root)
        digests = l3_digests(root, str(result.metadata["config_hash"]))
    finally:
        mp.undo()
    return {"schema_version": 1, "setting": "S2 預設 L3 臂（numba 多窗串流）", "window": list(h.S2_WINDOW),
            "column_count": len(digests), "columns": digests}


# ---------------------------------------------------------------- §G 預熱探測與校準封包（Task 4.1）

P1_WINDOW = ("2026-04-13", "2026-04-27")


def p1_payload() -> Dict[str, Any]:
    from tests.feature_engineering import icfirstalign_helpers as h

    return h.s2_payload(["12h", "1h"])


def p2_payload() -> Dict[str, Any]:
    """P2：12h 單週期、預設 L1 子集（trend 之預設指標；峰值 < 2 GB 之設定，實測記於收據——trend＋momentum 實測 4.18 GB 超限）。"""
    from tests.feature_engineering import icfirstalign_helpers as h

    payload = h.s2_payload()
    payload["atomic_indicators"] = {c: {"enabled": c == "trend"} for c in
                                    ("trend", "momentum", "volatility", "volume", "cycle", "pattern", "statistics",
                                     "microstructure", "entropy", "tail_risk")}
    return payload


def s3_payload(winsor: bool) -> Dict[str, Any]:
    from tests.feature_engineering import icfirstalign_helpers as h

    payload = h.s2_payload()
    payload["preprocessing"] = {**payload["preprocessing"], "winsorization": {"enabled": winsor},
                                "fractional_differencing": {"enabled": True},
                                "calibration_bars": 200, "calibration_bars_by_timeframe": {"12h": 200}}
    return payload


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _jia_compute_calibration_domain(self: Any, symbol: str, timeframe: str, config: Any, klines: Any) -> Any:
    """HEAD 甲：HEAD `_compute_calibration_domain`（eb1aae1e 起未變）之逐字複本，只加兩處測試端替換——
    (i) 最末合併之 L2 欄值改用逐類別 `compute_category`（公開 registry 所落之值），L3–L6 仍吃回傳表；
    (ii) 只此最末合併強制 `concat_with_memmap` 之 float32 分支（threshold_bytes=1）。"""
    import shutil

    import pandas as pd

    from momentum.FeatureEngineering.feature_factory import FeatureFactory, _derived_operator_engine_cls
    from momentum.core.contracts import LayerStatus
    from momentum.FeatureEngineering.memmap_utils import concat_with_memmap
    from momentum.FeatureEngineering.preprocessing.calibration import CALIBRATION_TMP_PREFIX, CalibrationError
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    calib = FeatureFactory(self._config_manager, self._adapter_registry)
    calib._current_symbol = symbol
    calib._current_timeframe = timeframe
    calib._current_raw_data = klines
    calib._calibration_domain = True
    tmp_dir = tempfile.mkdtemp(prefix=CALIBRATION_TMP_PREFIX)
    try:
        def _run(name: str, func: Any, *args: Any) -> Any:
            result = calib._execute_layer1_6(name, func, *args)
            if result.status == LayerStatus.layer_failed:
                raise CalibrationError(f"校準域 {name} 失敗：{result.reason}", timeframe=timeframe, field="compute")
            return result.data

        layer1 = _run("Layer 1", calib._layer1_atomic_indicators, klines, config)
        layer2 = _run("Layer 2", calib._layer2_derived_features, layer1, klines, config)
        engine_cls = _derived_operator_engine_cls()
        engine = engine_cls(calib._filter_operators_config(config.operators))
        specs = calib._build_indicator_specs(layer1, config)
        parts = [engine.compute_category(layer1, klines, specs, c) for c in engine_cls.OPERATOR_CATEGORIES]
        parts = [p for p in parts if p is not None and not p.empty]
        layer2_cat = pd.concat(parts, axis=1) if parts else pd.DataFrame(index=layer2.index)
        if set(layer2_cat.columns) != set(layer2.columns):
            raise RuntimeError("甲：逐類別 L2 欄集合與回傳表不同，無法逐欄替換")
        layer2_cat = layer2_cat.loc[:, list(layer2.columns)].set_axis(layer2.index, axis=0)
        layer2 = calib._spill_to_memmap(layer2, "calib_layer2", dir=tmp_dir)
        layer3 = _run("Layer 3", calib._layer3_rolling_aggregation, layer1, layer2, config)
        layer4 = _run("Layer 4", calib._layer4_lag_features, layer1, layer2, layer3, klines, config)
        layer5 = _run("Layer 5", calib._layer5_cross_sectional, layer1, layer2, config)
        layer6 = _run("Layer 6", calib._layer6_meta_features, layer1, layer2, klines, config)
        layers = [d for d in (layer1, layer2_cat, layer3, layer4, layer5, layer6) if d is not None and not d.empty]
        frame = concat_with_memmap(layers, threshold_bytes=1)
        if len(frame.index) == len(klines.index):
            frame = frame.set_axis(klines.index, axis=0)
        if config.preprocessing.winsorization.enabled:
            from momentum.FeatureEngineering.preprocessing._native_tf_helpers import scale_preprocessing_config_for_native

            winsor_config = scale_preprocessing_config_for_native(
                self._build_l7_raw_preprocessing_config(config), timeframe, config.timeframes.primary)
            frame = FeaturePreprocessor(winsor_config)._apply_winsorization(frame)
        return frame
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _first_finite_record(factory: Any, frame: Any, timeframe: str) -> Dict[str, Any]:
    from momentum.FeatureEngineering.preprocessing import calibration as cal

    idx = factory._calibration_datetime_index(frame.index)
    values = frame.to_numpy(dtype=np.float64)
    finite = np.isfinite(values)
    has = finite.any(axis=0)
    first_row = np.argmax(finite, axis=0)
    pairs = sorted((cal.tagged_column_name(str(c), timeframe), str(idx[first_row[i]]) if has[i] else None)
                   for i, c in enumerate(frame.columns))
    return {"timeframe": timeframe, "rows": int(len(frame)), "columns": int(frame.shape[1]), "first_finite_sha256": _sha(pairs)}


def _run_generation(payload: Dict[str, Any], window: Any, mode: str, capture: Dict[str, Any]) -> None:
    import pytest

    from momentum.FeatureEngineering import feature_factory as ff
    from momentum.FeatureEngineering.preprocessing import calibration as cal
    from tests.feature_engineering import icfirstalign_helpers as h

    mp = pytest.MonkeyPatch()
    try:
        tmp = Path(tempfile.mkdtemp(prefix=f"icfa_freeze_{mode}_"))
        root = h.isolated(mp, tmp)
        if mode == "jia":
            mp.setattr(ff.FeatureFactory, "_compute_calibration_domain", _jia_compute_calibration_domain)
        real_domain = cal.compute_calibration_domain
        calls: list = []

        def domain(factory: Any, symbol: str, timeframe: str, config: Any, klines: Any) -> Any:
            frame = real_domain(factory, symbol, timeframe, config, klines)
            calls.append(_first_finite_record(factory, frame, str(timeframe)))
            return frame

        mp.setattr(cal, "compute_calibration_domain", domain)
        real_preflight = ff.FeatureFactory.run_calibration_preflight
        packets: Dict[str, Any] = {}

        def preflight(self: Any, *args: Any, **kwargs: Any) -> Any:
            out = real_preflight(self, *args, **kwargs)
            packets.update(out.get("packets", {}))
            return out

        mp.setattr(ff.FeatureFactory, "run_calibration_preflight", preflight)
        factory = h.make_factory(root)
        factory.generate_features(h.SYMBOL, h.PRIMARY, config_override=payload, force_regenerate=True,
                                  start_date=window[0], end_date=window[1], persist=True)
        late = getattr(factory, "_public_warmup_late", None)
        capture["probe"] = {
            "rounds": list(getattr(factory, "_public_warmup_probe", [])),
            "window": {k: str(getattr(factory._current_output_window, k, None))
                       for k in ("output_start", "output_end", "ingest_start", "max_warmup_bars", "warmup_enabled")},
            "late_names_sha256": _sha(sorted(late[1])) if late else None,
            "domain_calls": calls,
        }
        capture["packets"] = {tf: _packet_record(p) for tf, p in packets.items()}
    finally:
        mp.undo()


def _packet_record(packet: Any) -> Dict[str, Any]:
    extras = packet.extras or {}
    return {
        "values": {k: hashlib.sha256(np.asarray(v, dtype=np.float64).tobytes()).hexdigest()
                   for k, v in sorted(packet.values.items())},
        "last_ts": {k: str(v) for k, v in sorted(packet.last_calibration_ts.items())},
        "first_ts": {k: str(v) for k, v in sorted((extras.get("first_calibration_ts") or {}).items())},
        "empty_columns": sorted(extras.get("empty_columns") or []),
        "shortfall": {k: int(v) for k, v in sorted((extras.get("calibration_shortfall") or {}).items())},
        "column_set_digest": packet.key.column_set_digest,
        "source_sha256": packet.calibration_source_sha256,
        "rows": int(extras.get("calibration_rows", 0)),
    }


def stage_probe() -> Dict[str, Any]:
    from tests.feature_engineering import icfirstalign_helpers as h

    out: Dict[str, Any] = {"schema_version": 1, "settings": {"P1": ["12h", "1h", list(P1_WINDOW)],
                                                            "P2": ["12h", "trend", list(h.S2_WINDOW)]}}
    for mode in ("jia", "yi"):
        out[mode] = {}
        for name, payload, window in (("P1", p1_payload(), P1_WINDOW), ("P2", p2_payload(), h.S2_WINDOW)):
            cap: Dict[str, Any] = {}
            _run_generation(payload, window, mode, cap)
            out[mode][name] = cap["probe"]
    return out


def stage_calibration() -> Dict[str, Any]:
    from tests.feature_engineering import icfirstalign_helpers as h

    out: Dict[str, Any] = {"schema_version": 1, "settings": {"S3": ["12h", "fracdiff", "N=200", list(h.S2_WINDOW)]}}
    for mode in ("jia", "yi"):
        out[mode] = {}
        for winsor in (True, False):
            cap: Dict[str, Any] = {}
            _run_generation(s3_payload(winsor), h.S2_WINDOW, mode, cap)
            out[mode][f"S3_winsor_{'on' if winsor else 'off'}"] = cap["packets"]
    return out


def worker_record(result: Dict[str, Any]) -> Dict[str, Any]:
    """`_tf_worker_entry` 回傳之 counts／failed／status／來源時間戳／群組（層、欄集合）摘要；值不入（值守恆由 Task 4.0／4.1 基準另驗）。"""
    groups = sorted((str(g["layer"]), _sha(sorted(g["columns"]))) for g in result.get("groups", []))
    return {"error": result.get("error"), "layer_counts": result.get("layer_counts"),
            "failed_layers": result.get("failed_layers"), "layer_statuses": result.get("layer_statuses"),
            "source_timestamps_sha256": hashlib.sha256(np.ascontiguousarray(np.asarray(
                result.get("source_timestamps_ms", []), dtype=np.int64)).tobytes()).hexdigest(),
            "groups_sha256": _sha(groups), "group_count": len(groups)}


def stage_worker_counts() -> Dict[str, Any]:
    """多週期 worker（S2m 之 4h）於 HEAD 之 layer_counts 與群組摘要（Task 4.2 層結果存活修碼之行為不變 oracle）。"""
    import pytest

    from momentum.FeatureEngineering.timeframe.multi_tf_generator import _tf_worker_entry
    from tests.feature_engineering import icfirstalign_helpers as h

    mp = pytest.MonkeyPatch()
    try:
        root = h.isolated(mp, Path(tempfile.mkdtemp(prefix="icfa_freeze_worker_")))
        mp.setenv("NUMBA_NUM_THREADS", os.environ.get("NUMBA_NUM_THREADS", "1"))
        payload = h.make_factory(root)._resolve_config(h.s2_payload(["12h", "4h"])).model_dump(by_alias=True)
        result = _tf_worker_entry(h.SYMBOL, "4h", payload, h.S2_WINDOW[0], h.S2_WINDOW[1], cache_dir=str(h.KLINE_DIR))
        return {"schema_version": 1, "setting": ["S2m", "4h", list(h.S2_WINDOW)], "worker": worker_record(result)}
    finally:
        mp.undo()


STAGES = {"l3-default": ("l3_default_arm.json", stage_l3_default),
          "probe": ("probe_baseline.json", stage_probe),
          "calibration": ("calibration_baseline.json", stage_calibration),
          "worker-counts": ("worker_counts.json", stage_worker_counts)}


def main(argv: Any = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1 or args[0] not in STAGES:
        print(f"用法：{Path(__file__).name} <{'|'.join(STAGES)}>", file=sys.stderr)
        return 2
    name, fn = STAGES[args[0]]
    os.environ.setdefault("PYTHONHASHSEED", "0")
    payload = fn()
    GOLDEN.mkdir(parents=True, exist_ok=True)
    (GOLDEN / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {GOLDEN / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
