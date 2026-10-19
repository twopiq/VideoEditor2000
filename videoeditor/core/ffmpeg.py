"""ffmpeg dasturini topish va ishga tushirish."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def ffmpeg_exe() -> str:
    """ffmpeg yo'li: VIDEOEDITOR_FFMPEG > imageio-ffmpeg ichidagi > PATH dagi."""
    env = os.environ.get("VIDEOEDITOR_FFMPEG")
    if env:
        return env
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError("ffmpeg topilmadi")


def popen_kwargs() -> dict:
    """Windows'da qora konsol oynasi chiqmasligi uchun."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}
