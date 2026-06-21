"""Top-level smoke worker for B1 multiprocess logging tests (picklable)."""

from __future__ import annotations

import json
import logging
import os

from api.core.logging import init_worker_logging

_SMOKE_PADDING = "x" * 200


def _flush_root_handlers() -> None:
    for logger_name in ("momentum", "api", ""):
        for handler in logging.getLogger(logger_name).handlers:
            handler.flush()


def smoke_worker(args: tuple[str, str]) -> str:
    """在子進程寫入唯一 JSON log line（真 FileHandler）。"""
    log_path, worker_id = args
    init_worker_logging(log_path, "SMOKE", "1h")
    payload = {
        "id": worker_id,
        "pid": os.getpid(),
        "padding": _SMOKE_PADDING,
    }
    logging.getLogger("momentum.smoke").info(json.dumps(payload))
    _flush_root_handlers()
    return worker_id
