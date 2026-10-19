"""Vaqt chizig'i: tanlangan oraliq, ikki tutqich, o'ynatish kursori va kalit kadrlar."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from ..core.timefmt import format_time
from . import style

_PAD = 10  # chetdagi bo'sh joy (tutqichlar to'liq ko'rinishi uchun)
_HANDLE_W = 10
_GRAB = 12  # tutqichni ushlash uchun sezgir masofa (px)


class Timeline(QWidget):
    seekRequested = Signal(float)
    rangeChanged = Signal(float, float)
    rangeEdited = Signal(str)  # "start" yoki "end" tutqichi qo'yib yuborilganda

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(64)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)
        self._duration = 0.0
        self._start = 0.0
        self._end = 0.0
        self._pos = 0.0
        self._keyframes: list[float] = []
        self._drag: str | None = None  # "start" | "end" | "seek"
        self._hover: str | None = None

    # --- holat ---------------------------------------------------------------
    def set_duration(self, duration: float) -> None:
        self._duration = max(0.0, duration)
        self._start, self._end, self._pos = 0.0, self._duration, 0.0
        self._keyframes = []
        self.update()

    def set_keyframes(self, keyframes: list[float]) -> None:
        self._keyframes = keyframes
        self.update()

    def set_position(self, t: float) -> None:
        self._pos = min(max(0.0, t), self._duration)
        self.update()

    def set_range(self, start: float, end: float) -> None:
        self._start, self._end = start, end
        self.update()

    # --- koordinatalar -------------------------------------------------------
    def _track(self) -> QRectF:
        return QRectF(_PAD, 14, self.width() - 2 * _PAD, self.height() - 28)

    def _x(self, t: float) -> float:
        tr = self._track()
        return tr.left() + (t / self._duration * tr.width() if self._duration else 0)

    def _t(self, x: float) -> float:
        tr = self._track()
        if tr.width() <= 0 or not self._duration:
            return 0.0
        return min(max(0.0, (x - tr.left()) / tr.width() * self._duration), self._duration)

    def _hit(self, x: float) -> str | None:
        ds, de = abs(x - self._x(self._start)), abs(x - self._x(self._end))
        if min(ds, de) > _GRAB:
            return None
        if ds == de:  # tutqichlar ustma-ust: chapdan bossa boshlanish
            return "start" if x <= self._x(self._start) else "end"
        return "start" if ds < de else "end"

    # --- chizish -------------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        tr = self._track()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(style.TRACK))
        p.drawRoundedRect(tr, 8, 8)
        if not self._duration:
            return

        xs, xe = self._x(self._start), self._x(self._end)
        sel = QRectF(xs, tr.top(), max(0.0, xe - xs), tr.height())
        accent = QColor(style.ACCENT)
        fill = QColor(accent)
        fill.setAlpha(46)
        p.setBrush(fill)
        p.drawRect(sel)
        p.setPen(QPen(accent, 2))
        p.drawLine(QPointF(xs, tr.top() + 1), QPointF(xe, tr.top() + 1))
        p.drawLine(QPointF(xs, tr.bottom() - 1), QPointF(xe, tr.bottom() - 1))

        # kalit kadrlar — pastki qismda kichik chiziqchalar
        if self._keyframes and tr.width() / max(1, len(self._keyframes)) >= 2:
            p.setPen(QPen(QColor(style.MUTED), 1))
            for k in self._keyframes:
                x = self._x(k)
                p.drawLine(QPointF(x, tr.bottom() - 6), QPointF(x, tr.bottom() - 2))

        for name, x in (("start", xs), ("end", xe)):
            r = QRectF(x - _HANDLE_W / 2, tr.top() - 4, _HANDLE_W, tr.height() + 8)
            color = QColor(style.ACCENT_HOVER if self._hover == name or self._drag == name else style.ACCENT)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(r, 4, 4)
            p.setPen(QPen(QColor(style.BG), 1.5))
            p.drawLine(QPointF(x, r.center().y() - 6), QPointF(x, r.center().y() + 6))

        # o'ynatish kursori
        xp = self._x(self._pos)
        p.setPen(QPen(QColor(style.TEXT), 2))
        p.drawLine(QPointF(xp, 4), QPointF(xp, self.height() - 4))
        tri = QPainterPath()
        tri.moveTo(xp - 5, 2)
        tri.lineTo(xp + 5, 2)
        tri.lineTo(xp, 8)
        tri.closeSubpath()
        p.fillPath(tri, QColor(style.TEXT))

    # --- sichqoncha ----------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or not self._duration:
            return
        x = e.position().x()
        self._drag = self._hit(x) or "seek"
        self._apply_drag(x)

    def mouseMoveEvent(self, e):
        x = e.position().x()
        if self._drag:
            self._apply_drag(x)
            QToolTip.showText(e.globalPosition().toPoint(), format_time(self._t(x)), self)
        else:
            hover = self._hit(x)
            if hover != self._hover:
                self._hover = hover
                self.setCursor(Qt.SizeHorCursor if hover else Qt.PointingHandCursor)
                self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._drag:
            drag, self._drag = self._drag, None
            if drag in ("start", "end"):
                self.rangeEdited.emit(drag)
            QToolTip.hideText()
            self.update()

    def leaveEvent(self, _e):
        self._hover = None
        self.update()

    def _apply_drag(self, x: float) -> None:
        t = self._t(x)
        if self._drag == "start":
            self._start = min(t, self._end)
            self.rangeChanged.emit(self._start, self._end)
            self.seekRequested.emit(self._start)
        elif self._drag == "end":
            self._end = max(t, self._start)
            self.rangeChanged.emit(self._start, self._end)
            self.seekRequested.emit(self._end)
        else:
            self.seekRequested.emit(t)
        self.update()
