"""PRE-RED Task 2.0 消融探針：把 d229336e 之差異分成「預熱」與「演算法變更」。

兩模式（cwd＝對應 worktree；須 PYTHONHASHSEED=0）：
  new <out_prefix> [symbol] [tf]
      於新版（d229336e）跑凍結腳本同設定之生成；記 OutputWindow.ingest_start／output_start／end、
      公開窗時間戳；輸出 final_L7 全欄之公開窗值（<prefix>.npz）與 meta（<prefix>.json：各層欄名、時間戳）。
  old <out_prefix> <new_meta.json> [symbol] [tf]
      於舊版（d229336e^）以與新版相同之 start_date（公開起點）生成，並以 FFACT_WARMUP_TRIM=1 及替換
      feature_factory 模組內之 resolve_output_window 注入新版之 OutputWindow（同 ingest_start；禁把 start_date
      改成 ingest_start）；依新版公開窗時間戳逐列取值（時間戳對齊，不取末 N 列；任一公開時間戳缺即拋錯）。
registry 之列與 L0 ingest index 列數不等 ⇒ 拋錯。
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
LAYERS = ("L1", "L2", "L3", "L4", "L5", "L6")


def _freeze():
    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", ROOT / "scripts/freeze_failopen_baseline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for k, v in mod.FIXED_ENV.items():
        os.environ[k] = v
    return mod


def _generate(freeze, symbol, tf, start, end, tmp):
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.factories import create_feature_factory

    os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "registry")
    factory = create_feature_factory(cache_dir=str(freeze.KLINE_PATH.parent), validate_continuity=False)
    factory._storage = FeatureStorage(str(Path(tmp) / "features"))
    payload = freeze._fixed_config_payload([tf], tf)
    factory.generate_features(symbol=symbol, timeframe=tf, config_override=payload, force_regenerate=True,
                              start_date=start, end_date=end, persist=False)
    return factory, payload


def _collect(freeze, factory, payload, symbol, tf, ingest_start, end, public_ts):
    import numpy as np

    from momentum.FeatureEngineering.core.column_group import LayerSource

    reg = factory._cgsa_registry
    ingest = factory._layer0_data_ingestion(symbol, tf, factory._resolve_config(payload), start_date=ingest_start, end_date=end)
    ingest_ts = np.asarray(ingest.index, dtype=np.int64)
    pos = {int(t): i for i, t in enumerate(ingest_ts)}
    missing = [int(t) for t in public_ts if int(t) not in pos]
    if missing:
        raise RuntimeError(f"公開時間戳 {len(missing)} 個不在 ingest index（首個 {missing[0]}）")
    rows = np.array([pos[int(t)] for t in public_ts], dtype=np.int64)
    # SPEC v4：輸出全 ingest 窗（含預熱列）；公開列位置另記於 meta
    _collect.public_rows = rows.tolist()
    _collect.ingest_ts = ingest_ts.tolist()
    # 大單元（1h）用兩段式：PRERED_HASH_ONLY=1 只記逐欄雜湊（全窗／公開窗）；PRERED_COLS=<檔> 只存列名單內之欄陣列
    import hashlib

    hash_only = os.environ.get("PRERED_HASH_ONLY") == "1"
    # 尾段雜湊（C1 等價式）：新版記 fv（首個有限值列）與 sha(col[fv:])；舊版以新版之 fv 計算同式。
    # C1 ⇔ 兩版 sha(col[fv_new:]) 相等（fv_new 之前新版全 NaN，舊版任意）。全窗與公開窗各一組。
    ref_hash = None
    if os.environ.get("PRERED_REF_META"):
        ref_hash = json.loads(Path(os.environ["PRERED_REF_META"]).read_text(encoding="utf-8"))["hashes"]
    keep = None
    if os.environ.get("PRERED_COLS"):
        keep = set(Path(os.environ["PRERED_COLS"]).read_text(encoding="utf-8").split())
    _collect.hashes = {}
    layer_cols, arrays = {}, {}
    for i, src in enumerate((LayerSource.L1, LayerSource.L2, LayerSource.L3, LayerSource.L4, LayerSource.L5, LayerSource.L6)):
        names = []
        for g in freeze._ordered_groups(reg, reg.list_by_layer(src)):
            data = np.asarray(reg.load_data_native(g.group_id))
            if data.shape[0] != len(ingest_ts):
                raise RuntimeError(f"registry 列數 {data.shape[0]} ≠ ingest index {len(ingest_ts)}（{g.group_id}）")
            for j, name in enumerate(g.columns):
                names.append(str(name))
                col = np.ascontiguousarray(data[:, j], dtype=np.float64)
                col[np.isnan(col)] = np.nan
                if hash_only:
                    pub = col[rows]
                    if ref_hash is not None and str(name) in ref_hash:
                        fv_f, fv_p = ref_hash[str(name)][0], ref_hash[str(name)][2]
                    else:
                        ff, fp = ~np.isnan(col), ~np.isnan(pub)
                        fv_f = int(np.argmax(ff)) if ff.any() else len(col)
                        fv_p = int(np.argmax(fp)) if fp.any() else len(pub)
                    _collect.hashes[str(name)] = [fv_f, hashlib.sha256(col[fv_f:].tobytes()).hexdigest()[:24],
                                                  fv_p, hashlib.sha256(pub[fv_p:].tobytes()).hexdigest()[:24]]
                elif keep is None or str(name) in keep:
                    arrays[str(name)] = np.asarray(data[:, j])
        layer_cols[LAYERS[i]] = names
    return layer_cols, arrays


def main() -> int:
    assert os.environ.get("PYTHONHASHSEED") == "0"
    import numpy as np

    mode, prefix = sys.argv[1], sys.argv[2]
    freeze = _freeze()
    start, end = freeze._window_dates()
    with tempfile.TemporaryDirectory() as tmp:
        if mode == "new":
            symbol = sys.argv[3] if len(sys.argv) > 3 else "BTCUSDT"
            tf = sys.argv[4] if len(sys.argv) > 4 else "12h"
            factory, payload = _generate(freeze, symbol, tf, start, end, tmp)
            w = factory._current_output_window
            assert w is not None and w.warmup_enabled, "新版預期預熱啟用"
            public = factory._layer0_data_ingestion(symbol, tf, factory._resolve_config(payload), start_date=start, end_date=end)
            public_ts = np.asarray(public.index, dtype=np.int64)
            layer_cols, arrays = _collect(freeze, factory, payload, symbol, tf, w.ingest_start, end, public_ts)
            agg = getattr(factory, "_last_l3_aggregator", None)
            dead = {**(dict(agg.dead_reasons) if agg is not None else {}),
                    **dict(getattr(factory, "_l7_dead_reasons", None) or {})}
            meta = {"symbol": symbol, "tf": tf, "ingest_start": w.ingest_start, "output_start": start, "end": end,
                    "max_warmup_bars": int(w.max_warmup_bars), "public_ts": public_ts.tolist(), "layer_cols": layer_cols,
                    "dead_reasons": {str(k): str(v) for k, v in dead.items()}}
        else:
            ref = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
            symbol, tf = ref["symbol"], ref["tf"]
            # SPEC v3 Task 2.0 ②(2)：start_date 與新版相同（公開起點）；只注入 L0 載入起點（替換模組內 resolve_output_window）
            os.environ["FFACT_WARMUP_TRIM"] = "1"
            import momentum.FeatureEngineering.feature_factory as _ff
            from momentum.FeatureEngineering.warmup_window import OutputWindow

            _win = OutputWindow(ingest_start=ref["ingest_start"], output_start=ref["output_start"],
                                output_end=ref["end"], max_warmup_bars=int(ref["max_warmup_bars"]), warmup_enabled=True)
            _ff.resolve_output_window = lambda *a, **k: _win
            factory, payload = _generate(freeze, symbol, tf, ref["output_start"], ref["end"], tmp)
            assert factory._current_output_window == _win, "舊版之輸出窗未被注入"
            layer_cols, arrays = _collect(freeze, factory, payload, symbol, tf, ref["ingest_start"], ref["end"],
                                          np.asarray(ref["public_ts"], dtype=np.int64))
            meta = {"symbol": symbol, "tf": tf, "ingest_start": ref["ingest_start"], "end": ref["end"],
                    "public_ts": ref["public_ts"], "layer_cols": layer_cols}
    meta["public_rows"] = _collect.public_rows
    meta["ingest_ts"] = _collect.ingest_ts
    if _collect.hashes:
        meta["hashes"] = _collect.hashes
    np.savez(prefix + ".npz", **arrays)
    Path(prefix + ".json").write_text(json.dumps(meta), encoding="utf-8")
    print("ablation", mode, "cols", len(arrays), "rows", len(meta["public_ts"]), "ingest_start", meta["ingest_start"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
