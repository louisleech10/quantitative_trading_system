"""Shared momentum exceptions."""


class InsufficientDataError(ValueError):
    """Raised when sample size is insufficient for analysis."""


class InvalidQueryError(ValueError):
    """Raised when an event query expression is invalid."""


class InvalidInputError(ValueError):
    """Raised when input data format or schema is invalid."""
