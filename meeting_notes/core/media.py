"""Media file metadata, external program lookup, and process suspend/resume."""

from __future__ import annotations

import contextlib
import ctypes
import os
import shutil
import signal
import subprocess
import sys
import uuid
import wave
from pathlib import Path
from typing import Iterable, Optional, Union

# GUI apps started from Finder do not inherit the shell PATH, so also look where
# Homebrew and common package managers install command-line tools.
EXTRA_PROGRAM_DIRS = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/snap/bin")
_FFPROBE_TIMEOUT_SECONDS = 30

_PKEY_MEDIA_DURATION = ("64440490-4C8B-11D1-8B70-080036B11A03", 3)
_IID_IPROPERTYSTORE = "886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"
_VT_UI8 = 21
_HUNDRED_NANOSECONDS = 10_000_000
_PROCESS_SUSPEND_RESUME = 0x0800


def find_program(names: Iterable[str], search_first: Optional[Path] = None) -> Optional[Path]:
    """Return the first of ``names`` found in ``search_first``, on PATH, or in common folders."""
    names = list(names)
    if search_first is not None:
        for name in names:
            if (search_first / name).is_file():
                return search_first / name
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    for folder in EXTRA_PROGRAM_DIRS:
        for name in names:
            candidate = Path(folder) / name
            if candidate.is_file() and os.access(str(candidate), os.X_OK):
                return candidate
    return None


def media_duration_seconds(path: Union[str, Path]) -> Optional[float]:
    """Return the playback length of an audio or video file, or ``None`` if unknown."""
    media = Path(path)
    if media.suffix.lower() == ".wav":
        with contextlib.suppress(wave.Error, OSError, EOFError):
            with wave.open(str(media), "rb") as reader:
                return reader.getnframes() / float(reader.getframerate())
    if sys.platform == "win32":
        with contextlib.suppress(OSError, ValueError):
            return _shell_duration(media.resolve())
        return None
    return _ffprobe_duration(media)


def _ffprobe_duration(media: Path) -> Optional[float]:
    ffprobe = find_program(["ffprobe"])
    if ffprobe is None:
        return None
    command = [
        str(ffprobe), "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(media),
    ]
    try:
        completed = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=_FFPROBE_TIMEOUT_SECONDS, check=False,
        )
        duration = float(completed.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return duration if duration > 0 else None


class _Guid(ctypes.Structure):
    _fields_ = [("bytes", ctypes.c_ubyte * 16)]

    @classmethod
    def parse(cls, text: str) -> "_Guid":
        guid = cls()
        ctypes.memmove(guid.bytes, uuid.UUID(text).bytes_le, 16)
        return guid


class _PropertyKey(ctypes.Structure):
    _fields_ = [("fmtid", _Guid), ("pid", ctypes.c_ulong)]


class _PropVariant(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("reserved", ctypes.c_ushort * 3),
        ("value", ctypes.c_ulonglong),
        ("padding", ctypes.c_ulonglong),
    ]


def _shell_duration(path: Path) -> Optional[float]:
    """Read ``System.Media.Duration`` through the Windows property system."""
    ole32 = ctypes.windll.ole32
    initialized = ole32.CoInitializeEx(None, 0) in (0, 1)
    store = ctypes.c_void_p()
    try:
        result = ctypes.windll.shell32.SHGetPropertyStoreFromParsingName(
            ctypes.c_wchar_p(str(path)), None, 0,
            ctypes.byref(_Guid.parse(_IID_IPROPERTYSTORE)), ctypes.byref(store),
        )
        if result != 0 or not store:
            return None
        vtable = ctypes.cast(store, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        get_value = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p,
            ctypes.POINTER(_PropertyKey), ctypes.POINTER(_PropVariant),
        )(vtable[5])
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[2])

        key = _PropertyKey(_Guid.parse(_PKEY_MEDIA_DURATION[0]), _PKEY_MEDIA_DURATION[1])
        variant = _PropVariant()
        try:
            if get_value(store, ctypes.byref(key), ctypes.byref(variant)) != 0:
                return None
            if variant.vt != _VT_UI8 or variant.value == 0:
                return None
            return variant.value / _HUNDRED_NANOSECONDS
        finally:
            release(store)
    finally:
        if initialized:
            ole32.CoUninitialize()


def set_process_suspended(pid: int, suspended: bool) -> None:
    """Suspend or resume a running process (Windows threads, or SIGSTOP/SIGCONT on POSIX)."""
    if sys.platform != "win32":
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGSTOP if suspended else signal.SIGCONT)
        return
    kernel32 = ctypes.WinDLL("kernel32")
    ntdll = ctypes.WinDLL("ntdll")
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    action = ntdll.NtSuspendProcess if suspended else ntdll.NtResumeProcess
    action.argtypes = [ctypes.c_void_p]

    handle = kernel32.OpenProcess(_PROCESS_SUSPEND_RESUME, False, pid)
    if not handle:
        return
    try:
        action(handle)
    finally:
        kernel32.CloseHandle(handle)
