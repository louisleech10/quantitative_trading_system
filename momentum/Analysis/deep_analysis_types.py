"""Shared data structures for deep analysis modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SkippedResult:
    module_name: str
    reason: str
    error_type: str
    details: dict[str, Any] | None = None
    retryable: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DeepAnalysisReport:
    results: dict[str, Any] = field(default_factory=dict)
    deep_analysis_errors: list[SkippedResult] = field(default_factory=list)
    # module_summary 值合法枚舉（scalar str）：
    # completed / completed_partial / skipped / unavailable / not_run
    # completed_partial：模組本體有效（如 exposure/concentration），子項不可用
    # （如 factor_attribution unavailable）；計入 completed_count（D-12）。
    module_summary: dict[str, str] = field(default_factory=dict)
    total_modules: int = 10
    # ICPERF Task 0.4 ⑩：請求明示之模組開關蓋過具名 preset 者（{模組: {"requested", "preset"}}；無則空）
    tier_module_overrides: dict[str, dict] = field(default_factory=dict)
    completed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_execution_time_s: float = 0.0
