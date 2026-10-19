"""Video faylni tahlil qilish (PyAV orqali)."""

from __future__ import annotations

import bisect
import os
import threading
from dataclasses import dataclass, field

import av

# Kesish boshlanishini kalit kadrdan sal keyinroq beramiz: ffmpeg undan oldingi
# eng yaqin kalit kadrga qaytadi, ya'ni aynan shu kadrdan boshlaydi. Yaxlitlash
# tufayli oldingi kalit kadrga tushib qolmaslik uchun kerak (1 ms < 1 kadr).
KEYFRAME_EPS = 0.001


@dataclass
class MediaInfo:
    path: str
    duration: float
    size: int
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    audio_codec: str = ""
    container: str = ""
    keyframes: list[float] = field(default_factory=list)

    @property
    def has_video(self) -> bool:
        return bool(self.video_codec)

    @property
    def frame_duration(self) -> float:
        return 1.0 / self.fps if self.fps > 0 else 1.0 / 30


def _start_offset(container) -> float:
    return (container.start_time or 0) / av.time_base


def probe(path: str) -> MediaInfo:
    with av.open(path) as c:
        duration = (c.duration or 0) / av.time_base
        info = MediaInfo(
            path=path,
            duration=duration,
            size=os.path.getsize(path),
            container=c.format.name,
        )
        if c.streams.video:
            vs = c.streams.video[0]
            ctx = vs.codec_context
            info.video_codec = ctx.name or ""
            info.width, info.height = ctx.width, ctx.height
            rate = vs.average_rate or vs.guessed_rate
            info.fps = float(rate) if rate else 0.0
            if not duration and vs.duration:
                info.duration = float(vs.duration * vs.time_base)
        if c.streams.audio:
            info.audio_codec = c.streams.audio[0].codec_context.name or ""
    return info


def scan_keyframes(path: str, cancel: threading.Event | None = None) -> list[float]:
    """Barcha video kalit kadrlar vaqtlari (soniya, fayl boshidan)."""
    result: list[float] = []
    with av.open(path) as c:
        if not c.streams.video:
            return result
        vs = c.streams.video[0]
        base = _start_offset(c)
        for i, pkt in enumerate(c.demux(vs)):
            if cancel is not None and i % 256 == 0 and cancel.is_set():
                return []
            if pkt.is_keyframe and pkt.pts is not None:
                result.append(float(pkt.pts * vs.time_base) - base)
    result.sort()
    return result


def keyframe_before(path: str, t: float) -> float:
    """t dan oldingi (yoki aynan t dagi) kalit kadr — ffmpeg qayerdan boshlashi."""
    with av.open(path) as c:
        if not c.streams.video:
            return t
        vs = c.streams.video[0]
        base = _start_offset(c)
        target = int((t + base + KEYFRAME_EPS) / vs.time_base)
        c.seek(target, stream=vs, backward=True, any_frame=False)
        for pkt in c.demux(vs):
            if pkt.pts is not None and pkt.is_keyframe:
                return min(t, max(0.0, float(pkt.pts * vs.time_base) - base))
    return 0.0


def snap_to_keyframe(keyframes: list[float], t: float) -> float:
    """Ro'yxatdagi t dan oldingi eng yaqin kalit kadr."""
    if not keyframes:
        return t
    i = bisect.bisect_right(keyframes, t + KEYFRAME_EPS)
    return max(0.0, keyframes[i - 1]) if i else 0.0
