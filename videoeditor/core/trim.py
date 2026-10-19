"""Videoni sifatni yo'qotmasdan (qayta kodlashsiz) qirqish.

ffmpeg `-c copy` rejimida ishlaydi: siqilgan video/audio paketlar o'zgarishsiz
yangi faylga ko'chiriladi, shuning uchun sifat 100% saqlanadi va jarayon juda
tez. Cheklov: video faqat kalit kadrdan boshlanishi mumkin, shuning uchun
boshlanish nuqtasi `media.keyframe_before` bilan oldingi kalit kadrga suriladi.
"""

from __future__ import annotations

import os
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass

from .ffmpeg import ffmpeg_exe, popen_kwargs
from .media import KEYFRAME_EPS

_FASTSTART_EXT = {".mp4", ".m4v", ".mov", ".3gp"}


class TrimError(RuntimeError):
    pass


class TrimCancelled(TrimError):
    pass


@dataclass(frozen=True)
class TrimPlan:
    src: str
    dst: str
    start: float  # kalit kadrga surilgan boshlanish
    end: float
    duration: float  # manba videoning umumiy davomiyligi

    @property
    def length(self) -> float:
        return max(0.0, self.end - self.start)


def build_command(plan: TrimPlan, *, all_streams: bool = True, ffmpeg: str | None = None) -> list[str]:
    cmd = [ffmpeg or ffmpeg_exe(), "-hide_banner", "-nostdin", "-y", "-loglevel", "error"]
    seek = plan.start + KEYFRAME_EPS if plan.start > 0 else 0.0
    if seek > 0:
        cmd += ["-ss", f"{seek:.6f}"]
    cmd += ["-i", plan.src]
    if plan.end < plan.duration - 1e-3:
        cmd += ["-t", f"{plan.end - seek:.6f}"]
    if all_streams:
        cmd += ["-map", "0", "-dn", "-ignore_unknown"]
    else:
        cmd += ["-map", "0:v?", "-map", "0:a?"]
    cmd += ["-c", "copy", "-map_metadata", "0"]
    if os.path.splitext(plan.dst)[1].lower() in _FASTSTART_EXT:
        cmd += ["-movflags", "+faststart"]
    cmd += ["-progress", "pipe:1", "-nostats", plan.dst]
    return cmd


def _run(cmd: list[str], plan: TrimPlan, progress, cancel) -> tuple[int, str]:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **popen_kwargs(),
    )
    stderr_chunks: list[str] = []
    reader = threading.Thread(target=lambda: stderr_chunks.append(proc.stderr.read()), daemon=True)
    reader.start()
    length = plan.length or 1.0
    for line in proc.stdout:
        if cancel is not None and cancel.is_set():
            proc.kill()
            proc.wait()
            raise TrimCancelled("bekor qilindi")
        key, _, value = line.strip().partition("=")
        if key == "out_time_us" and progress and value.lstrip("-").isdigit():
            progress(min(1.0, max(0.0, int(value) / 1e6 / length)))
    proc.wait()
    reader.join(timeout=5)
    return proc.returncode, "".join(stderr_chunks).strip()


def trim(
    plan: TrimPlan,
    progress: Callable[[float], None] | None = None,
    cancel: threading.Event | None = None,
) -> str:
    """Qirqadi va yaratilgan fayl yo'lini qaytaradi."""
    if plan.length <= 0:
        raise TrimError("Tugash vaqti boshlanishdan keyin bo'lishi kerak")
    if os.path.abspath(plan.src) == os.path.abspath(plan.dst):
        raise TrimError("Natijani asl faylning ustiga yozib bo'lmaydi")
    try:
        code, err = _run(build_command(plan), plan, progress, cancel)
        if code != 0:
            # Ba'zi qo'shimcha oqimlar (subtitr, maxsus ma'lumot) yangi konteynerga
            # sig'masligi mumkin — faqat video va audio bilan qayta urinamiz.
            code, err2 = _run(build_command(plan, all_streams=False), plan, progress, cancel)
            if code != 0:
                raise TrimError(err2 or err or f"ffmpeg xatosi (kod {code})")
    except TrimCancelled:
        _remove_quietly(plan.dst)
        raise
    except Exception:
        _remove_quietly(plan.dst)
        raise
    if progress:
        progress(1.0)
    return plan.dst


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def suggest_output_path(src: str, start: float, end: float) -> str:
    folder, name = os.path.split(src)
    stem, ext = os.path.splitext(name)

    def stamp(t: float) -> str:
        t = int(t)
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{h}-{m:02d}-{s:02d}" if h else f"{m:02d}-{s:02d}"

    base = f"{stem}_qirqim_{stamp(start)}_{stamp(end)}"
    candidate = os.path.join(folder, base + ext)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{base}_{n}{ext}")
        n += 1
    return candidate
