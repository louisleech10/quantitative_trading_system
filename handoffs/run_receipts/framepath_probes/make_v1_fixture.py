"""SPEC v17 Task 2.5／2.6 驗收用：以錨點 6e07e0ad 碼態之 V1 寫入器（`FeatureStorage.persist_registry_to_parquet`）
產生一份最小 V1 版面 fixture（`<base>/<symbol>/<config_hash>/manifest.json`＋`columns.json.gz`＋逐組 parquet）。

只准於生產碼與錨點相同之碼態執行（V1 寫入器於 Task 2.5 刪除後即不存在）；輸出入版控於
`tests/_golden/framepath/v1_layout/`，供「V2 讀者不退回 V1」「coverage 不讀 V1」之可證偽驗收（錨點碼態下讀得到 V1 ⇒
驗收紅；實作後讀不到 ⇒ 綠）。
用法：PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/make_v1_fixture.py <out_dir>
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

SYMBOL = "FPV1USDT"
CONFIG_HASH = "cfgv1fixture"


def main() -> int:
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    out = Path(sys.argv[1])
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"輸出目錄非空：{out}")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        registry = ColumnGroupRegistry(work_dir=work)
        data = np.arange(12, dtype=np.float32).reshape(4, 3)
        npy = work / "g1.npy"
        np.save(npy, data)
        registry.register(ColumnGroup(
            group_id="g1", layer=LayerSource.L1, timeframe="1h", data_source="close", indicator="fpv1",
            columns=("fpv1_a", "fpv1_b", "fpv1_c"), shape=data.shape, dtype="float32", disk_path=npy,
        ))
        storage = FeatureStorage(base_path=str(out))
        storage.persist_registry_to_parquet(SYMBOL, CONFIG_HASH, registry)
    for p in sorted(out.rglob("*")):
        if p.is_file():
            print(p.relative_to(out), p.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
