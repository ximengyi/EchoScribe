from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_tcl_tk() -> None:
    if not getattr(sys, "frozen", False) or not hasattr(sys, "_MEIPASS"):
        return
    base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    tcl = base / "tcl" / "tcl8.6"
    tk = base / "tcl" / "tk8.6"
    if tcl.exists():
        os.environ.setdefault("TCL_LIBRARY", str(tcl))
    if tk.exists():
        os.environ.setdefault("TK_LIBRARY", str(tk))


def main() -> None:
    _configure_tcl_tk()
    from echoscribe.ui.main_window import run_app

    run_app()


if __name__ == "__main__":
    main()
