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
