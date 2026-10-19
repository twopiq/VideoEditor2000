"""Dasturni ishga tushirish."""

from __future__ import annotations

import os
import sys


def self_test() -> int:
    """Yig'ilgan .exe da kerakli qismlar borligini tekshirish (CI uchun)."""
    import subprocess

    import av
    from PySide6.QtMultimedia import QMediaPlayer  # noqa: F401

    from . import __version__
    from .core.ffmpeg import ffmpeg_exe, popen_kwargs

    out = subprocess.run([ffmpeg_exe(), "-version"], capture_output=True, text=True, **popen_kwargs())
    if out.returncode != 0:
        return 1
    print(f"VideoEditor2000 {__version__} | {out.stdout.splitlines()[0]} | PyAV {av.__version__}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    if "--self-test" in argv:
        return self_test()
    from PySide6.QtWidgets import QApplication

    from . import APP_NAME
    from .ui import style
    from .ui.main_window import MainWindow

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(style.QSS)
    window = MainWindow()
    window.show()
    files = [a for a in argv[1:] if os.path.isfile(a)]
    if files:
        window.load(files[0])
    return app.exec()
