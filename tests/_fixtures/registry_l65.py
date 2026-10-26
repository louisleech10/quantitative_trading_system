"""registry 之 L6.5 轉換經生產入口（FFPROD Task 1.1）。

原 registry 原地覆寫入口生產無呼叫者已刪；測試改經生產之
`transform_registry_groups_to_sink`（raw 串流寫入之唯一 L6.5 入口），以收集式 sink 承接各群組（含分塊）輸出，再依來源
群組依序併欄並寫回 registry，使既有測試之「轉換後讀 registry」斷言照舊適用。只承接原地替換（replace 模式：輸出欄＝來源
群組欄、同序）；欄不符 ⇒ AssertionError（不靜默改形狀）。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

import numpy as np


def apply_l65_via_sink(preprocessor: Any, registry: Any, n_workers: int = 1) -> int:
    """以生產 sink 入口對 `registry` 全部群組做 L6.5，輸出寫回原群組；回傳入口回報之完成群組數。"""
    parts: Dict[str, List[Tuple[List[str], np.ndarray]]] = defaultdict(list)

    def sink(group_id: str, columns: List[str], data: np.ndarray, source_group_id: str, source_disk_path: Any,
             cleanup_source: bool) -> None:
        del group_id, source_disk_path, cleanup_source  # 收集式 sink：不刪來源、不落盤
        parts[str(source_group_id)].append((list(columns), np.array(data, dtype=np.float32, copy=True)))

    completed = preprocessor.transform_registry_groups_to_sink(registry, sink, n_workers=n_workers)
    for source_id, chunks in parts.items():
        columns = [name for cols, _ in chunks for name in cols]
        expected = list(registry.get(source_id).columns)
        assert columns == expected, f"{source_id}：sink 輸出欄 {columns[:5]} ≠ 來源群組欄 {expected[:5]}（非原地替換）"
        registry.overwrite_data(source_id, np.concatenate([data for _, data in chunks], axis=1))
    return completed
