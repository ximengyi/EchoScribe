from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from typing import Any


def windows_no_window_creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0


def run_hidden(command: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    kwargs.setdefault("creationflags", windows_no_window_creationflags())
    return subprocess.run(command, **kwargs)


def popen_hidden(command: Sequence[str], **kwargs: Any) -> subprocess.Popen[str]:
    kwargs.setdefault("creationflags", windows_no_window_creationflags())
    return subprocess.Popen(command, **kwargs)
