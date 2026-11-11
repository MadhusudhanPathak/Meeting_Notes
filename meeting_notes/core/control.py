"""Thread-safe pause and cancel signals shared between the UI and a running job."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Callable, Iterator, Optional

Hook = Optional[Callable[[], None]]


class JobCancelled(Exception):
    """Raised inside a job when the user cancels it."""


class JobControl:
    """
    Lets one thread pause, resume, or cancel work running on another.

    Long-running operations call :meth:`checkpoint` between steps and may
    :meth:`attach` hooks that act immediately (for example suspending or
    killing a subprocess, or closing a socket).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._running.set()
        self._cancelled = threading.Event()
        self._pause_hook: Hook = None
        self._resume_hook: Hook = None
        self._abort_hook: Hook = None

    @property
    def is_paused(self) -> bool:
        return not self._running.is_set() and not self._cancelled.is_set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def pause(self) -> None:
        with self._lock:
            if self._cancelled.is_set() or not self._running.is_set():
                return
            self._running.clear()
            _call(self._pause_hook)

    def resume(self) -> None:
        with self._lock:
            if self._running.is_set():
                return
            self._running.set()
            _call(self._resume_hook)

    def cancel(self) -> None:
        with self._lock:
            if self._cancelled.is_set():
                return
            self._cancelled.set()
            if not self._running.is_set():
                _call(self._resume_hook)
            self._running.set()
            _call(self._abort_hook)

    def checkpoint(self) -> None:
        """Block while paused; raise :class:`JobCancelled` once cancelled."""
        self._running.wait()
        if self._cancelled.is_set():
            raise JobCancelled()

    @contextmanager
    def attach(self, pause: Hook = None, resume: Hook = None, abort: Hook = None) -> Iterator[None]:
        """Register hooks for the duration of a block, applying the current state at once."""
        with self._lock:
            self._pause_hook, self._resume_hook, self._abort_hook = pause, resume, abort
            if self._cancelled.is_set():
                _call(abort)
            elif not self._running.is_set():
                _call(pause)
        try:
            yield
        finally:
            with self._lock:
                self._pause_hook = self._resume_hook = self._abort_hook = None


def _call(hook: Hook) -> None:
    if hook is not None:
        hook()


def checkpoint(control: Optional[JobControl]) -> None:
    """Call :meth:`JobControl.checkpoint` when a control is present."""
    if control is not None:
        control.checkpoint()
