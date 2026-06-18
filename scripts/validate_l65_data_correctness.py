"""Claude 自產 — L65(移 legacy + 釘死 causal)資料正確性驗證(三方簽核之一)。

依「三方數據正確性簽核鐵律」+ SPEC §V 不變量。真實 kline,read-only。
本任務改動 = 移除 legacy L6.5(IC-First 唯一) + causal 釘死 True。資料正確性宣稱:
  V1 byte parity:移 legacy 後 IC-First L6.5 輸出與移除前 byte 一致(交 golden --check)。
  V2 causal PIT 無洩漏(核心):外部 causal=False 被強制 True 且輸出==顯式 True;
     竄改未來 bar 不改變過去輸出(no look-ahead)。
  V3 跨 symbol 隔離:多 symbol L6.5 schema 一致、無跨 symbol 狀態污染。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from momentum.factories import create_feature_factory
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

SYMBOLS = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT"]
TF = "1h"

WINSOR_CFG = {
    "mode": "replace",
    "winsorization": {"enabled": True, "method": "quantile", "quantile_range": [0.05, 0.95], "window": 252, "apply_to": "all"},
    "rank_transform": {"enabled": False},
    "adaptive_zscore": {"enabled": False},
    "gaussian_normalize": {"enabled": True, "clip_range": [0.001, 0.999], "apply_to": "all"},
    "fractional_differencing": {"enabled": False},
    "adf_differencing": {"enabled": False},
}


def _l1_frame(f, cfg, sym: str) -> pd.DataFrame:
    l0 = f._layer0_data_ingestion(sym, TF, cfg)
    l1 = f._execute_layer1_6("Layer 1", f._layer1_atomic_indicators, l0, cfg).data
    num = [c for c in l1.columns if np.issubdtype(l1[c].dtype, np.number)]
    return l1[num[:40]].astype(float)  # 取樣 40 欄控時間


def v2_causal_pit(frame: pd.DataFrame) -> dict:
    """外部 False==顯式 True;竄改未來不改過去。"""
    forced = FeaturePreprocessor({**WINSOR_CFG, "causal_preprocessing": False}).transform(frame)
    causal = FeaturePreprocessor({**WINSOR_CFG, "causal_preprocessing": True}).transform(frame)
    forced_eq_causal = np.allclose(forced.to_numpy(np.float64), causal.to_numpy(np.float64),
                                   atol=1e-9, equal_nan=True)
    # PIT:竄改最後 50 bar,前段(到 n-100)輸出不得變
    n = len(frame)
    cut = n - 100
    tampered = frame.copy()
    tampered.iloc[n - 50:] = tampered.iloc[n - 50:] * 3.0 + 1e6
    out_orig = FeaturePreprocessor({**WINSOR_CFG, "causal_preprocessing": True}).transform(frame)
    out_tamp = FeaturePreprocessor({**WINSOR_CFG, "causal_preprocessing": True}).transform(tampered)
    pit_ok = np.allclose(out_orig.to_numpy(np.float64)[:cut], out_tamp.to_numpy(np.float64)[:cut],
                         atol=1e-9, equal_nan=True)
    return {"forced_eq_causal": bool(forced_eq_causal), "pit_no_lookahead": bool(pit_ok)}


def main() -> None:
    f = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
    cfg = f._resolve_config(None)
    frames = {s: _l1_frame(f, cfg, s) for s in SYMBOLS}

    print("\n===== V2 causal PIT 無洩漏 (核心) =====")
    v2_all = True
    for s in SYMBOLS:
        r = v2_causal_pit(frames[s])
        ok = r["forced_eq_causal"] and r["pit_no_lookahead"]
        v2_all &= ok
        print(f"  {s}: forced==causal={r['forced_eq_causal']} PIT_no_lookahead={r['pit_no_lookahead']} -> {'PASS' if ok else 'FAIL'}")

    print("\n===== V3 跨 symbol 隔離 =====")
    # schema 一致(同 config 下欄名集合相同) + 無跨 symbol 污染(交錯處理 vs 獨立處理一致)
    outs = {s: FeaturePreprocessor({**WINSOR_CFG, "causal_preprocessing": True}).transform(frames[s]) for s in SYMBOLS}
    cols0 = list(outs[SYMBOLS[0]].columns)
    schema_ok = all(list(outs[s].columns) == cols0 for s in SYMBOLS)
    # 污染檢查:同一 preprocessor 實例連續處理 A,B vs 各自新實例,B 結果應一致
    pp_shared = FeaturePreprocessor({**WINSOR_CFG, "causal_preprocessing": True})
    _ = pp_shared.transform(frames["BTCUSDT"])
    b_after_a = pp_shared.transform(frames["ETHUSDT"])
    b_clean = FeaturePreprocessor({**WINSOR_CFG, "causal_preprocessing": True}).transform(frames["ETHUSDT"])
    no_contam = np.allclose(b_after_a.to_numpy(np.float64), b_clean.to_numpy(np.float64),
                            atol=1e-9, equal_nan=True)
    print(f"  schema 跨 5 symbol 一致={schema_ok}")
    print(f"  無跨 symbol 狀態污染(shared-instance B==clean B)={no_contam}")

    print("\n===== 結論 =====")
    overall = v2_all and schema_ok and no_contam
    print(f"  V2 causal PIT: {'PASS' if v2_all else 'FAIL'}")
    print(f"  V3 跨 symbol 隔離: {'PASS' if (schema_ok and no_contam) else 'FAIL'}")
    print(f"  V1 byte parity: 交 scripts/build_l65_golden_baseline.py --check(另跑)")
    print(f"  Claude 簽核: {'資料正確 (V2+V3 PASS)' if overall else '有疑慮,需查'}")


if __name__ == "__main__":
    main()
