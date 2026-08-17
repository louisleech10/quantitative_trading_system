"""ICHC Task 2.0 — Phase 2 golden 凍結（§G）。

Frozen inputs（TODO 定死）：symbol=ETHUSDT、timeframe=12h、
features=tests/golden/la0/inputs/ETHUSDT_12h_*_a0_tail2000.h5（真實 kline 衍生 fixture）、
config=repo 預設（不帶 override）、kline=data_cache/feature_klines/kline_cache.h5。

Canonical serialization spec（TODO 定死；本模組同時是 T-G1 測試的共用 helper，禁另寫）：
  1. 數值位 NaN 一律寫 null，另存平行 bool 陣列 nan_mask（等長同序）。
  2. json.dumps(sort_keys=True, separators=(",", ":"), allow_nan=False)。
  3. float 以 format(x, ".17g") 正規化後回寫（json 內為數值非字串）。
  4. 凍結範圍＝report["quantile_returns"] 子樹全量；不含 generated_at。
  5. 巢狀（改前）與扁平（改後）兩形皆可抽取——mapping 表內建於 extract_quantile_canonical。

用法：source venv/bin/activate && python scripts/ichc_freeze_p2_golden.py
輸出：handoffs/run_receipts/ichc_p2_golden_pre.json（重跑必須 byte 相同）。
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SYMBOL = "ETHUSDT"
TIMEFRAME = "12h"
LA0_INPUTS = REPO / "tests/golden/la0/inputs"
H5_GLOB = f"{SYMBOL}_{TIMEFRAME}_*_a0_tail2000.h5"
KLINE_CACHE_DIR = "data_cache/feature_klines"
RECEIPT_PATH = REPO / "handoffs/run_receipts/ichc_p2_golden_pre.json"


def _norm_float(value: Any) -> Any:
    """float 正規化：.17g 回寫；NaN → None（呼叫端負責 mask）。非數值原樣。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    if isinstance(value, int):
        return value
    if math.isnan(value):
        return None
    return float(format(value, ".17g"))


def _split_nan(values: list) -> tuple[list, list]:
    """值列表 → (正規化值列表(NaN=null), nan_mask 等長同序)。"""
    normed, mask = [], []
    for v in values:
        is_nan = isinstance(v, float) and math.isnan(v)
        mask.append(bool(is_nan))
        normed.append(None if is_nan else _norm_float(v))
    return normed, mask


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ensure_ascii=False,
    ).encode("utf-8")


def extract_quantile_canonical(qr_tree: dict) -> dict:
    """report['quantile_returns'] → per-feature canonical payload（巢狀/扁平皆可抽）。

    巢狀（改前）：feature → {quantile_returns:{qmr,cum,lss,lst}, monotonicity_score, long_short}
    扁平（改後）：feature → {qmr,cum,long_short_spread,long_short_tstat,monotonicity_score}
    """
    out: dict[str, Any] = {}
    for feature in sorted(qr_tree.keys()):
        node = qr_tree.get(feature)
        if not isinstance(node, dict):
            out[feature] = {"non_dict": True}
            continue
        inner = node.get("quantile_returns") if isinstance(node.get("quantile_returns"), dict) else node
        qmr = inner.get("quantile_mean_returns", {}) or {}
        cum = inner.get("cumulative_returns", {}) or {}
        lss = inner.get("long_short_spread")
        lst = inner.get("long_short_tstat")
        if lss is None and isinstance(node.get("long_short"), dict):
            lss = node["long_short"].get("spread")
        if lst is None and isinstance(node.get("long_short"), dict):
            lst = node["long_short"].get("tstat")
        mono = node.get("monotonicity_score", inner.get("monotonicity_score"))

        qmr_keys = sorted(qmr.keys())
        qmr_vals, qmr_mask = _split_nan([qmr[k] for k in qmr_keys])
        cum_canon = {}
        for key in sorted(cum.keys()):
            series = cum.get(key) or []
            vals, mask = _split_nan(list(series))
            cum_canon[key] = {"values": vals, "nan_mask": mask, "length": len(vals)}
        scalars, scalar_mask = _split_nan([lss, lst, mono])
        payload = {
            "key_set": sorted(inner.keys() | ({"monotonicity_score"} if mono is not None else set())),
            "quantile_mean_returns": {
                "keys": qmr_keys, "values": qmr_vals, "nan_mask": qmr_mask,
            },
            "cumulative_returns": cum_canon,
            "long_short_spread": scalars[0],
            "long_short_tstat": scalars[1],
            "monotonicity_score": scalars[2],
            "scalar_nan_mask": scalar_mask,
        }
        payload["canonical_sha256"] = hashlib.sha256(
            canonical_json_bytes(payload)
        ).hexdigest()
        out[feature] = payload
    return out


def build_receipt(report: dict, config_hash: str) -> dict:
    qr_tree = report.get("quantile_returns") or {}
    per_feature = extract_quantile_canonical(qr_tree)
    feature_names = sorted(per_feature.keys())
    return {
        "_doc": "ICHC Task 2.0 golden（§G）。重跑本腳本必須 byte 相同；T-G1 以同 helper 比對。",
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "config_hash": config_hash,
        "feature_set_sha256": hashlib.sha256(
            "\n".join(feature_names).encode("utf-8")
        ).hexdigest(),
        "n_features": len(feature_names),
        "per_feature": per_feature,
    }


def run_analyze() -> tuple[dict, str]:
    """與 T-G1 共用的 entrypoint：預設 config 跑主流程，persist 導 tmp。"""
    import tempfile

    from momentum.factories import create_ic_analyzer, create_kline_storage_manager
    from momentum.Analysis.ic_config_schema import ICConfig

    matches = sorted(LA0_INPUTS.glob(H5_GLOB))
    if not matches:
        raise FileNotFoundError(
            f"找不到 features fixture：{LA0_INPUTS}/{H5_GLOB}（真實 kline 衍生；勿合成）"
        )
    h5_path = matches[0]
    meta_path = h5_path.with_name(h5_path.stem + "_meta.json")
    if not meta_path.exists():
        raise FileNotFoundError(f"meta 檔缺席：{meta_path}")

    config_hash = hashlib.sha256(
        canonical_json_bytes(ICConfig().model_dump(mode="json"))
    ).hexdigest()

    orchestrator = create_ic_analyzer()
    tmp = Path(tempfile.mkdtemp(prefix="ichc_golden_sidefx_"))
    reporter = orchestrator._reporter
    orig_save_report = reporter.save_report
    orig_save_filter_log = reporter.save_filter_log
    orig_save_filtered = reporter.save_filtered_features
    def _save_report(report, output_dir=None, case_id=None, **kwargs):
        return orig_save_report(
            report, output_dir=str(tmp / "reports"), case_id=case_id, **kwargs
        )

    def _save_filter_log(filter_log, output_dir=None, case_id=None, **kwargs):
        return orig_save_filter_log(
            filter_log, output_dir=str(tmp / "reports"), case_id=case_id, **kwargs
        )

    def _save_filtered(df, columns, output_path, **kwargs):
        redirected = tmp / "features" / Path(str(output_path)).name
        return orig_save_filtered(df, columns, str(redirected), **kwargs)

    reporter.save_report = _save_report
    reporter.save_filter_log = _save_filter_log
    reporter.save_filtered_features = _save_filtered
    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    report = orchestrator.analyze(
        features_path=str(h5_path.resolve()),
        labels_path="",
        meta_path=str(meta_path.resolve()),
        config_override=None,
        kline_reader=kline_reader,
    )
    return report, config_hash


def main() -> int:
    report, config_hash = run_analyze()
    receipt = build_receipt(report, config_hash)
    RECEIPT_PATH.write_bytes(canonical_json_bytes(receipt) + b"\n")
    print(
        f"[ichc_freeze] wrote {RECEIPT_PATH} n_features={receipt['n_features']} "
        f"feature_set_sha={receipt['feature_set_sha256'][:16]} config_hash={config_hash[:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
