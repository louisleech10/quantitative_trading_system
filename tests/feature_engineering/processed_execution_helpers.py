"""直接呼叫 `FeatureStorage.write_processed` 之單元情境所需之 post-IC 紀錄（FFDSTAR Task 1.4：`execution` 為必填）。

這些測試未經 post-IC 前處理器、直接把群組寫成 processed；故紀錄如實記「未做任何前處理」：每欄六步驟皆為契約
`named_values.preprocessing_master_off` 之值、終態「已寫出」、群組臂為「無前處理」。值一律經 `run_provenance` 之紀錄函式
與契約查值，不另列舉狀態值集。
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

import pandas as pd

from momentum.FeatureEngineering import run_provenance as rp


def direct_write_execution(
    groups: Mapping[str, pd.DataFrame],
    timeframe: str = "1h",
) -> Tuple[Dict[Tuple[str, str], Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """回 (`execution_records()` 同形, `execution_groups()` 同形)：群組內每欄一筆紀錄。"""
    master_off = str(rp.load_contract()["named_values"]["preprocessing_master_off"])
    records: Dict[Tuple[str, str], Dict[str, Any]] = {}
    group_table: Dict[str, Dict[str, Any]] = {}
    for group_id, frame in groups.items():
        keys = [(str(timeframe), str(column)) for column in frame.columns]
        rp.record_all_steps(records, keys, master_off, layer=None, group_id=str(group_id))
        for key in keys:
            records[key]["terminal"] = "written"
        rp.record_group(group_table, str(group_id), arm="no_preprocessing", status="ok")
    return records, group_table
