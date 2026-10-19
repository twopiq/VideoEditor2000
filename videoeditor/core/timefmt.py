"""Vaqtni matnga va matndan soniyaga o'girish."""

from __future__ import annotations


def format_time(seconds: float, *, millis: bool = True) -> str:
    """12.345 -> '00:12.345', 3723.5 -> '1:02:03.500'."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    base = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    return f"{base}.{ms:03d}" if millis else base


def parse_time(text: str) -> float:
    """'1:02:03.5', '02:03', '83.25', '83,25' kabi yozuvlarni soniyaga o'giradi.

    Noto'g'ri yozuvda ValueError ko'taradi.
    """
    text = text.strip().replace(",", ".")
    if not text:
        raise ValueError("bo'sh vaqt")
    parts = text.split(":")
    if len(parts) > 3:
        raise ValueError(f"noto'g'ri vaqt: {text!r}")
    total = 0.0
    for i, part in enumerate(parts):
        if not part:
            raise ValueError(f"noto'g'ri vaqt: {text!r}")
        value = float(part)
        if value < 0 or (i > 0 and value >= 60):
            raise ValueError(f"noto'g'ri vaqt: {text!r}")
        total = total * 60 + value
    return total


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
