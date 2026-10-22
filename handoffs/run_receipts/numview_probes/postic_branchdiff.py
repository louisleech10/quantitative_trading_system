"""NUMVIEW post-IC 分支差 HEAD 重量與翻轉（docs/NUMVIEW_SPEC.md Task 1.1，C5）。

母集：`tests/_golden/icpostleak/contract.json` 之分支與七組合，另加探針專用候選臂 `polars_float64`（Polars post-IC
轉換全程 Float64：`pandas_to_polars(use_float64=True)`、rank `map_batches` 之 `return_dtype` Float64、rank UDF 緩衝區
與逐值寫入 float64、`_polars_mask_columns` 中間保留 Float64、gaussian 分支與 `_gaussian_2d` 回傳與最終回傳攜帶
compute dtype，輸出於落盤前轉 float32；探針內 monkeypatch，不改產品碼；收據記中間 dtype 以證全程 Float64）。
輸入：(i) ICPOSTLEAK §G 輸入集建法套用於每個 symbol×tf；(ii) 格 A／B 之 IC-first 實際選欄之 raw 欄（Task 0.5 保留之 run）。
參照＝測試端獨立 numpy float64 實作（rank→gaussian→zscore、窗未滿 NaN），另列 legacy 臂。
輸出（欄名依判準檔）：格級 max_abs／p99_abs／max_rel（近零格另列）／NaN 遮罩差；IC 層逐欄 IC、正負號翻轉數、
Kendall τ-b（未定義 ⇒ material）、`material`；速度：各臂轉換牆鐘三次與中位數。生成型輸入啟動前呼叫
`_estimate_gate.require("postic_branchdiff", cells)`。收據 `handoffs/run_receipts/<date>-numview-postic-branchdiff.json`，
含 `criteria_sha256`。

純函式 `cell_diff`／`ic_material` 已隨 Task 0.3 判準實作（NUMVIEW b1；判準檔 `material` 之參考判定）；`main`（量測）待 Task 1.1。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import numpy as np

#: 探針專用候選臂名（SPEC Task 1.1；非產品臂，不入 post_ic_arm_values）
CANDIDATE_ARM = "polars_float64"


def cell_diff(reference: np.ndarray, output: np.ndarray) -> Dict[str, Any]:
    """格級差（SPEC Task 1.1；邊界①）：`max_abs`、`p99_abs`、`max_rel`（|ref| < float32 tiny 之近零格不計相對差）、
    `near_zero_cells` 與 `near_zero_max_abs`（近零格另列絕對差）、`nan_mask_diff`（兩者 NaN 遮罩不同之格數）。

    差值只對兩者皆有限之格計（float64）；無此類格 ⇒ 差值欄為 None。形狀不同 ⇒ ValueError（不廣播）。
    任一邊含 ±inf ⇒ ValueError（非有限值 fail-closed，不得併入中性摘要；NaN 為窗未滿等預期缺值，由 `nan_mask_diff` 計）。"""
    ref = np.asarray(reference, dtype=np.float64)
    out = np.asarray(output, dtype=np.float64)
    if ref.shape != out.shape:
        raise ValueError(f"cell_diff 形狀不同：{ref.shape} vs {out.shape}")
    n_inf = int(np.count_nonzero(np.isinf(ref))) + int(np.count_nonzero(np.isinf(out)))
    if n_inf:
        raise ValueError(f"cell_diff 輸入含 ±inf 共 {n_inf} 格（非有限值 fail-closed）")
    nan_mask_diff = int(np.count_nonzero(np.isnan(ref) != np.isnan(out)))
    both = np.isfinite(ref) & np.isfinite(out)
    absdiff = np.abs(out[both] - ref[both])
    ref_both = np.abs(ref[both])
    tiny = float(np.finfo(np.float32).tiny)
    near = ref_both < tiny
    far = ~near
    return {
        "max_abs": float(absdiff.max()) if absdiff.size else None,
        "p99_abs": float(np.percentile(absdiff, 99)) if absdiff.size else None,
        "max_rel": float((absdiff[far] / ref_both[far]).max()) if np.any(far) else None,
        "near_zero_cells": int(np.count_nonzero(near)),
        "near_zero_max_abs": float(absdiff[near].max()) if np.any(near) else None,
        "nan_mask_diff": nan_mask_diff,
    }


def _kendall_tau_b(x: np.ndarray, y: np.ndarray) -> float:
    """Kendall τ-b；有效對數 < 2 或任一邊全 ties（分母 0）⇒ NaN（不發警告、不回 0）。

    τ-b＝1 之判定以 exact 排序比較為準（兩邊 dense rank 逐元素相等 ⇔ 每一對之大小關係〔含相等〕皆一致 ⇔ τ-b＝1），
    回傳恰 1.0；不以浮點 `tau < 1` 判（scipy 之開方捨入可得 0.9999999999999998，會把同序誤判為翻轉）。"""
    if x.size < 2:
        return float("nan")
    import warnings

    from scipy.stats import kendalltau, rankdata

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tau = float(kendalltau(x, y, variant="b")[0])
    if np.isfinite(tau) and np.array_equal(rankdata(x, method="dense"), rankdata(y, method="dense")):
        return 1.0
    return tau


def ic_material(ic_reference: Sequence[float], ic_variant: Sequence[float]) -> Dict[str, Any]:
    """IC 層翻轉（SPEC Task 1.1、設計選擇⑥、R2-D）：`tau_b`（只對兩者 IC 皆有限之欄對計算；全 ties、全 NaN、有效對數
    < 2 ⇒ NaN）、`sign_flips`、`material`（任一正負號翻轉、τ-b < 1、或 τ-b 非有限 ⇒ True）、`reason`（判定原因）。
    非有限統計量一律 `material=True`（fail-closed），不得以 `NaN < 1 == False` 判未翻轉。

    判準依 `tests/_golden/numview/preregistered_criteria.json` 之 `material`：IC 之 NaN 遮罩（有限與否）不同、兩者皆有限
    之欄 IC 正負號不同、或 τ-b < 1／非有限 ⇒ material。選欄數為零之格由呼叫端於呼叫前處理（Task 1.1 邊界②）。"""
    a = np.asarray(ic_reference, dtype=np.float64)
    b = np.asarray(ic_variant, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"ic_material 長度不同：{a.shape} vs {b.shape}")
    reasons = []
    mask_diff = int(np.count_nonzero(np.isfinite(a) != np.isfinite(b)))
    if mask_diff:
        reasons.append(f"nan_mask_diff={mask_diff}")
    both = np.isfinite(a) & np.isfinite(b)
    sign_flips = int(np.count_nonzero(np.sign(a[both]) != np.sign(b[both])))
    if sign_flips:
        reasons.append(f"ic_sign_flip={sign_flips}")
    tau = _kendall_tau_b(a[both], b[both])
    if not np.isfinite(tau):
        reasons.append("tau_b_undefined")
    elif tau < 1.0:
        reasons.append(f"tau_b_below_1={tau!r}")
    return {"tau_b": tau, "sign_flips": sign_flips, "material": bool(reasons),
            "reason": ";".join(reasons) if reasons else "none"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """量測主入口；rc 0＝收據寫出；重現檢查（BTCUSDT 1h 輸入 (i) 之 legacy 對 optimized 七組合皆 0 差）不符 ⇒ rc≠0。"""
    raise NotImplementedError("NUMVIEW Task 1.1")


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
