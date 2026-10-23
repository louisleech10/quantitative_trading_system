"""NUMVIEW L2 兩臂矩陣（docs/NUMVIEW_SPEC.md Task 1.3，C7）。

承 `handoffs/run_receipts/icfirstalign_probes/l2_arm_pipeline_probe.py`，參數化至格 A＋格 B 全部格：每格記 L1 輸入
dtype、兩臂（L5／L6 所吃之 `compute_all_polars` 表 vs 公開落盤之 `compute_category`）之欄集合、NaN 遮罩、float32
有限值差格數（`f32diff`）、max_abs、max_rel，及 `FFACT_USE_POLARS=0` 時 pandas 臂之同表。某類別 `compute_category`
拋錯 ⇒ 記錯誤，不以缺欄計 0 差（邊界②）。啟動前呼叫 `_estimate_gate.require("l2_arm_matrix", cells)`。
格與生成依判準檔 `run_coverage.l2_arm_matrix`（路徑覆蓋）：凍結已生成之 (格, 環境) 一律讀凍結生成所掛 L2 spy 之紀錄、
不重生；只有凍結無該環境之生成（格 B、格 C 之 `FFACT_USE_POLARS=0`）才生成。
BTCUSDT 12h 格須重現 freeze-baselines 收據之 f32diff=0（不符 ⇒ rc≠0，停下歸因）。
收據 `handoffs/run_receipts/<date>-numview-l2-arm-matrix.json`，含 `criteria_sha256`。

`compare_l2_arms` 與擷取 spy `L2Capture` 於 Task 0.5 建立（凍結生成時掛之）；`main` 為 Task 1.3 實作。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

#: 擷取紀錄之 schema 版本（Task 1.3 讀之）
L2_CAPTURE_SCHEMA = 1


def compare_l2_arms(returned: pd.DataFrame, category: pd.DataFrame) -> Dict[str, Any]:
    """兩臂比較：`common_cols`、`only_returned`、`only_category`、`nan_mask_diff`、`f64diff`、`f32diff`、`max_abs`、
    `max_rel`；只比兩者皆有限之格之值差，NaN 遮罩差另列。`only_returned`／`only_category` 為欄名清單（排序；Task 1.3 驗收
    契約），`common_cols` 為共同欄數。列數不同 ⇒ `row_mismatch`（不比值）。"""
    ret_cols = [str(c) for c in returned.columns]
    cat_cols = [str(c) for c in category.columns]
    ret_set, cat_set = set(ret_cols), set(cat_cols)
    common = [c for c in cat_cols if c in ret_set]
    out: Dict[str, Any] = {"common_cols": len(common), "only_returned": sorted(ret_set - cat_set),
                           "only_category": sorted(cat_set - ret_set), "nan_mask_diff": 0, "f64diff": 0, "f32diff": 0,
                           "max_abs": 0.0, "max_rel": 0.0, "row_mismatch": None}
    if returned.shape[0] != category.shape[0]:
        out["row_mismatch"] = [int(returned.shape[0]), int(category.shape[0])]
        return out
    if not common:
        return out
    a = returned.loc[:, common].to_numpy(dtype=np.float64)
    b = category.loc[:, common].to_numpy(dtype=np.float64)
    nan_a, nan_b = np.isnan(a), np.isnan(b)
    both = np.isfinite(a) & np.isfinite(b)
    diff = np.abs(np.where(both, a - b, 0.0))
    scale = np.where(both, np.maximum(np.abs(a), np.abs(b)), 0.0)
    rel = np.divide(diff, scale, out=np.zeros_like(diff), where=scale > 0)
    out.update(nan_mask_diff=int((nan_a != nan_b).sum()), f64diff=int((both & (a != b)).sum()),
               f32diff=int((both & (a.astype(np.float32) != b.astype(np.float32))).sum()),
               max_abs=float(diff.max()) if diff.size else 0.0, max_rel=float(rel.max()) if rel.size else 0.0)
    return out


def _merge(stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """逐類別比較之合計（計數相加、max 取最大；任一類別列數不符 ⇒ 列出）。"""
    out: Dict[str, Any] = {"common_cols": 0, "only_category": [], "nan_mask_diff": 0, "f64diff": 0, "f32diff": 0,
                           "max_abs": 0.0, "max_rel": 0.0, "row_mismatch": []}
    only_category: Set[str] = set()
    for s in stats:
        for key in ("common_cols", "nan_mask_diff", "f64diff", "f32diff"):
            out[key] += int(s[key])
        only_category |= set(s.get("only_category") or [])
        out["max_abs"] = max(out["max_abs"], float(s["max_abs"]))
        out["max_rel"] = max(out["max_rel"], float(s["max_rel"]))
        if s.get("row_mismatch"):
            out["row_mismatch"].append(s["row_mismatch"])
    out["only_category"] = sorted(only_category)
    return out


class L2Capture:
    """凍結生成所掛之 L2 兩臂擷取 spy（SPEC Task 0.5、Task 1.3）：包 `FeatureFactory._layer2_derived_features`，對其回傳表
    （L5／L6 所吃者：Polars 臂為 `compute_all_polars`、pandas 臂為 pandas 實作）與同一輸入之逐類別 `compute_category`
    （公開落盤路徑）逐類別比較、只累積統計量（全特徵格不同時持有兩份全表）。每個 (domain, 列數) 只記第一次呼叫
    （domain＝calibration／main；多週期格之各週期列數不同而各記一次）。比較本身之例外記入紀錄、不影響生成。"""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []
        self._seen: Set[Tuple[str, int]] = set()

    def __enter__(self) -> "L2Capture":
        from momentum.FeatureEngineering import feature_factory as ff

        self._ff = ff
        self._real = ff.FeatureFactory._layer2_derived_features
        capture = self

        def spy(this: Any, layer1: pd.DataFrame, data: pd.DataFrame, config: Any) -> Any:
            result = capture._real(this, layer1, data, config)
            domain = "calibration" if getattr(this, "_calibration_domain", False) else "main"
            key = (domain, int(layer1.shape[0]))
            if key not in capture._seen:
                capture._seen.add(key)
                capture.records.append(capture._record(this, layer1, data, config, result, domain))
            return result

        ff.FeatureFactory._layer2_derived_features = spy  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: Any) -> None:
        self._ff.FeatureFactory._layer2_derived_features = self._real  # type: ignore[assignment]

    def _record(self, this: Any, layer1: pd.DataFrame, data: pd.DataFrame, config: Any, result: Any,
                domain: str) -> Dict[str, Any]:
        started = time.perf_counter()
        returned = getattr(result, "data", None)
        base: Dict[str, Any] = {"schema": L2_CAPTURE_SCHEMA, "domain": domain, "rows": int(layer1.shape[0]),
                                "l1_cols": int(layer1.shape[1]), "l1_dtypes": sorted({str(t) for t in layer1.dtypes})}
        try:
            from momentum.FeatureEngineering.polars_adapter import polars_enabled

            base["returned_arm"] = "polars" if polars_enabled() else "pandas"
            base["returned_cols"] = int(returned.shape[1]) if returned is not None else None
            base["returned_dtypes"] = sorted({str(t) for t in returned.dtypes}) if returned is not None else []
            eng_cls = self._ff._derived_operator_engine_cls()
            engine = eng_cls(this._filter_operators_config(config.operators))
            specs = this._build_indicator_specs(layer1, config)
            stats: List[Dict[str, Any]] = []
            covered: Set[str] = set()
            errors: Dict[str, str] = {}
            per_category: Dict[str, Dict[str, Any]] = {}
            for category in eng_cls.OPERATOR_CATEGORIES:
                try:
                    frame = engine.compute_category(layer1, data, specs, category)
                except Exception as exc:  # noqa: BLE001 — 邊界②：記錯誤，不以缺欄計 0 差
                    errors[str(category)] = f"{type(exc).__name__}: {exc}"[:500]
                    continue
                if frame is None or frame.empty:
                    continue
                one = compare_l2_arms(returned, frame)
                stats.append(one)
                # 逐類別之「只在回傳表」為其他類別之欄，不存（全特徵格過大）；合計後另算
                per_category[str(category)] = {k: v for k, v in one.items() if k != "only_returned"}
                covered |= {str(c) for c in frame.columns}
                del frame
            merged = _merge(stats)
            merged["only_returned"] = sorted({str(c) for c in returned.columns} - covered) if returned is not None else None
            base.update(merged, per_category=per_category, category_errors=errors)
        except Exception as exc:  # noqa: BLE001 — 比較失敗記錄、不影響生成
            base["capture_error"] = f"{type(exc).__name__}: {exc}"[:1000]
        base["compare_seconds"] = time.perf_counter() - started
        return base


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出；BTCUSDT 12h 重現檢查不符 ⇒ rc≠0。"""
    raise NotImplementedError("NUMVIEW Task 1.3")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
