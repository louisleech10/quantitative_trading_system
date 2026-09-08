"""Shared momentum exceptions."""


class InsufficientDataError(ValueError):
    """Raised when sample size is insufficient for analysis."""


class InvalidQueryError(ValueError):
    """Raised when an event query expression is invalid."""


class InvalidInputError(ValueError):
    """Raised when input data format or schema is invalid."""


class ModuleUnavailableError(Exception):
    """模組刻意下架/不可用(非 skip 錯誤;不入 deep_analysis_errors)。

    用於 stopgap 等 fail-close 出口:父迴圈專屬 except 寫 §U union
    ``{status, value, reason}`` + module_summary=unavailable。
    """


class AnalysisCancelled(Exception):
    """協作式中止：progress callback 拋出即代表呼叫端要分析在**下一個回報點**停下（orchestrator `_report_progress` 不吞它）。

    出生事故（2026-09-08 UAT）：後端 Ctrl+C 後事件迴圈已關，分析執行緒仍跑完全程，每個回報點記一筆
    「Progress callback failed: Event loop is closed」洗版，且行程要等它跑完才退出。
    """
