"""Kernel-backed per-run leases."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from momentum.FeatureEngineering.run_paths import safe_token, validate_config_hash


class RunBusyError(RuntimeError):
    """Run 已由另一個工作持有 exclusive lease。"""


class RunLease:
    """以 ``flock`` 持有的 per-run exclusive lease。"""

    def __init__(self, fd: int, path: Path) -> None:
        self._fd: Optional[int] = fd
        self.path = path

    @classmethod
    def acquire(
        cls,
        locks_dir: Path,
        symbol: str,
        timeframe: str,
        config_hash: str,
        timeout: float = 0.0,
    ) -> "RunLease":
        """取得 run lease；timeout 內未取得則回報 busy。"""
        validate_config_hash(config_hash)
        directory = Path(locks_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{safe_token(symbol)}_{safe_token(timeframe)}_{config_hash}.lock"
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                os.close(fd)
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                    raise
                if time.monotonic() >= deadline:
                    raise RunBusyError(f"Run is busy: {symbol}/{timeframe}/{config_hash}") from exc
                time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
                continue
            payload = json.dumps(
                {"pid": os.getpid(), "ts": datetime.now(timezone.utc).isoformat()}
            ).encode("utf-8")
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, payload)
            return cls(fd, path)

    @property
    def active(self) -> bool:
        """回傳 lease 是否仍由此物件持有。"""
        return self._fd is not None

    def release(self) -> None:
        """釋放 lease；重複呼叫安全。"""
        fd = self._fd
        if fd is None:
            return
        self._fd = None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def __enter__(self) -> "RunLease":
        return self

    def __exit__(self, *_args: object) -> None:
        self.release()


def is_run_active(locks_dir: Path, symbol: str, timeframe: str, config_hash: str) -> bool:
    """以 non-blocking try-flock 探測 run 是否活躍。"""
    validate_config_hash(config_hash)
    directory = Path(locks_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{safe_token(symbol)}_{safe_token(timeframe)}_{config_hash}.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                return True
            raise
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)
