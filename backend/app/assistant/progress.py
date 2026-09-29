"""Optional progress listeners, so smoke scripts show what a long agent run is doing."""

import time
from collections.abc import Callable

ProgressListener = Callable[[str], None]

_listeners: list[ProgressListener] = []
_started_at = time.perf_counter()


def reset_progress_clock() -> None:
    global _started_at
    _started_at = time.perf_counter()


def elapsed_seconds() -> float:
    return time.perf_counter() - _started_at


def add_progress_listener(listener: ProgressListener) -> None:
    _listeners.append(listener)


def clear_progress_listeners() -> None:
    _listeners.clear()


def report_progress(message: str) -> None:
    for listener in _listeners:
        listener(message)
