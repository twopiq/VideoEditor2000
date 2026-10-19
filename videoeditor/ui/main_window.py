"""Asosiy oyna: video tanlash, ko'rish va qirqish."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QSettings, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME
from ..core import media, trim
from ..core.timefmt import format_size, format_time, parse_time
from .timeline import Timeline

VIDEO_EXTS = ("mp4", "mov", "m4v", "mkv", "webm", "avi", "mts", "m2ts", "ts", "flv", "wmv", "3gp", "mpg", "mpeg")
VIDEO_FILTER = "Videolar (" + " ".join(f"*.{e}" for e in VIDEO_EXTS) + ");;Barcha fayllar (*)"


class _Bridge(QObject):
    """Fon oqimidan asosiy oqimga xabar yetkazish."""

    done = Signal(object, object)  # callback, natija
    progress = Signal(float)


def _run_async(bridge: _Bridge, fn: Callable, on_done: Callable, on_error: Callable) -> None:
    def work():
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 — xatoni UI ga uzatamiz
            bridge.done.emit(on_error, exc)
        else:
            bridge.done.emit(on_done, result)

    threading.Thread(target=work, daemon=True).start()


def _reveal_in_folder(path: str) -> None:
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))


class DropZone(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(10)
        icon = QLabel("✂")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 40px; color: #f2c94c;")
        title = QLabel("Videoni shu yerga tashlang")
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignCenter)
        sub = QLabel("yoki tanlash uchun bosing  ·  Ctrl+O")
        sub.setObjectName("dropSub")
        sub.setAlignment(Qt.AlignCenter)
        btn = QPushButton("Video tanlash")
        btn.setObjectName("primary")
        btn.clicked.connect(self.clicked)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        btn_row.addStretch()
        for w in (icon, title, sub):
            lay.addWidget(w)
        lay.addSpacing(8)
        lay.addLayout(btn_row)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 760)
        self.setMinimumSize(720, 520)
        self.setAcceptDrops(True)
        self.settings = QSettings(APP_NAME, APP_NAME)

        self.info: media.MediaInfo | None = None
        self.keyframes: list[float] = []
        self.start = 0.0  # kalit kadrga surilgan boshlanish
        self.requested_start = 0.0  # foydalanuvchi tanlagan boshlanish
        self.end = 0.0
        self._preview = False
        self._load_token = 0
        self._cancel: threading.Event | None = None
        self._last_output: str | None = None

        self._bridge = _Bridge()
        self._bridge.done.connect(lambda cb, value: cb(value))
        self._bridge.progress.connect(self._on_progress)

        self._build_ui()
        self._build_player()
        self._build_shortcuts()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 20)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)
        self.setCentralWidget(root)

        self.drop = DropZone()
        self.drop.clicked.connect(self.open_dialog)
        self.stack.addWidget(self.drop)

        editor = QWidget()
        lay = QVBoxLayout(editor)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        top = QHBoxLayout()
        names = QVBoxLayout()
        names.setSpacing(2)
        self.title = QLabel()
        self.title.setObjectName("title")
        self.meta = QLabel()
        self.meta.setObjectName("meta")
        names.addWidget(self.title)
        names.addWidget(self.meta)
        top.addLayout(names, 1)
        other = QPushButton("Boshqa video…")
        other.setObjectName("ghost")
        other.clicked.connect(self.open_dialog)
        top.addWidget(other, 0, Qt.AlignTop)
        lay.addLayout(top)

        self.video = QVideoWidget()
        self.video.setObjectName("video")
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video.setMinimumHeight(200)
        lay.addWidget(self.video, 1)

        panel = QFrame()
        panel.setObjectName("panel")
        p = QVBoxLayout(panel)
        p.setContentsMargins(16, 12, 16, 14)
        p.setSpacing(10)

        transport = QHBoxLayout()
        transport.setSpacing(8)
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("icon")
        self.play_btn.setToolTip("O'ynatish / to'xtatish  (Bo'sh joy)")
        self.play_btn.clicked.connect(self.toggle_play)
        self.timecode = QLabel("00:00.000 / 00:00.000")
        self.timecode.setObjectName("timecode")
        preview = QPushButton("Tanlovni ko'rish")
        preview.setToolTip("Tanlangan qismni boshidan o'ynatish  (P)")
        preview.clicked.connect(self.preview_selection)
        transport.addWidget(self.play_btn)
        transport.addWidget(self.timecode)
        transport.addStretch()
        transport.addWidget(preview)
        p.addLayout(transport)

        self.timeline = Timeline()
        self.timeline.seekRequested.connect(self.seek)
        self.timeline.rangeChanged.connect(self._on_range_dragged)
        self.timeline.rangeEdited.connect(self._on_range_released)
        p.addWidget(self.timeline)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.start_edit = self._time_field("Boshlanish vaqti")
        self.start_edit.editingFinished.connect(lambda: self._on_field_edited("start"))
        self.end_edit = self._time_field("Tugash vaqti")
        self.end_edit.editingFinished.connect(lambda: self._on_field_edited("end"))
        set_in = QPushButton("[  Shu yerdan")
        set_in.setToolTip("Boshlanishni kursor turgan joyga qo'yish  (I)")
        set_in.clicked.connect(self.set_in_here)
        set_out = QPushButton("Shu yergacha  ]")
        set_out.setToolTip("Tugashni kursor turgan joyga qo'yish  (O)")
        set_out.clicked.connect(self.set_out_here)
        self.length_lbl = QLabel()
        self.length_lbl.setObjectName("meta")
        self.export_btn = QPushButton("Qirqib saqlash")
        self.export_btn.setObjectName("primary")
        self.export_btn.setToolTip("Sifatni yo'qotmasdan saqlash  (Ctrl+S)")
        self.export_btn.clicked.connect(self.export)

        controls.addWidget(set_in)
        controls.addWidget(self.start_edit)
        controls.addWidget(QLabel("—"))
        controls.addWidget(self.end_edit)
        controls.addWidget(set_out)
        controls.addSpacing(10)
        controls.addWidget(self.length_lbl)
        controls.addStretch()
        controls.addWidget(self.export_btn)
        p.addLayout(controls)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setTextFormat(Qt.PlainText)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(220)
        self.progress.hide()
        self.cancel_btn = QPushButton("Bekor qilish")
        self.cancel_btn.setObjectName("ghost")
        self.cancel_btn.clicked.connect(self.cancel_export)
        self.cancel_btn.hide()
        self.reveal_btn = QPushButton("Papkada ko'rsatish")
        self.reveal_btn.setObjectName("link")
        self.reveal_btn.setCursor(Qt.PointingHandCursor)
        self.reveal_btn.clicked.connect(lambda: self._last_output and _reveal_in_folder(self._last_output))
        self.reveal_btn.hide()
        footer.addWidget(self.status)
        footer.addWidget(self.reveal_btn)
        footer.addStretch()
        footer.addWidget(self.progress)
        footer.addWidget(self.cancel_btn)
        p.addLayout(footer)

        lay.addWidget(panel)
        self.stack.addWidget(editor)

    def _time_field(self, tip: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setToolTip(f"{tip} — masalan 1:23.5 yoki 83.5")
        edit.setFixedWidth(110)
        edit.setAlignment(Qt.AlignCenter)
        edit.returnPressed.connect(lambda: self.setFocus())
        return edit

    def _build_player(self) -> None:
        self.audio = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.errorOccurred.connect(self._on_player_error)

    def _build_shortcuts(self) -> None:
        def sc(keys: str, fn: Callable) -> None:
            QShortcut(QKeySequence(keys), self, activated=fn)

        sc("Ctrl+O", self.open_dialog)
        sc("Ctrl+S", self.export)
        sc("Space", self.toggle_play)
        sc("K", self.toggle_play)
        sc("P", self.preview_selection)
        sc("I", self.set_in_here)
        sc("O", self.set_out_here)
        sc("Left", lambda: self.step_frames(-1))
        sc("Right", lambda: self.step_frames(1))
        sc("Shift+Left", lambda: self.step_seconds(-1))
        sc("Shift+Right", lambda: self.step_seconds(1))
        sc("J", lambda: self.step_seconds(-5))
        sc("L", lambda: self.step_seconds(5))
        sc("Home", lambda: self.seek(self.start))
        sc("End", lambda: self.seek(self.end))
        sc("Escape", self.cancel_export)

    # ----------------------------------------------------------- yuklash --
    def open_dialog(self) -> None:
        if self._busy():
            return
        start_dir = self.settings.value("last_dir", os.path.expanduser("~"))
        path, _ = QFileDialog.getOpenFileName(self, "Video tanlash", start_dir, VIDEO_FILTER)
        if path:
            self.load(path)

    def load(self, path: str) -> None:
        if self._busy():
            return
        self.settings.setValue("last_dir", os.path.dirname(path))
        self._load_token += 1
        token = self._load_token
        self._set_status("Ochilmoqda…")
        _run_async(
            self._bridge,
            lambda: media.probe(path),
            lambda info: token == self._load_token and self._on_probed(info),
            lambda exc: token == self._load_token and self._set_status(f"Faylni ochib bo'lmadi: {exc}", "error"),
        )

    def _on_probed(self, info: media.MediaInfo) -> None:
        if info.duration <= 0:
            self._set_status("Videoning davomiyligini aniqlab bo'lmadi", "error")
            return
        self.info = info
        self.keyframes = []
        self.requested_start, self.start, self.end = 0.0, 0.0, info.duration
        self._preview = False
        self._last_output = None
        self.reveal_btn.hide()

        self.title.setText(os.path.basename(info.path))
        self.setWindowTitle(f"{os.path.basename(info.path)} — {APP_NAME}")
        bits = []
        if info.has_video:
            bits.append(f"{info.width}×{info.height}")
            bits.append(info.video_codec)
            if info.fps:
                bits.append(f"{info.fps:.3g} fps")
        if info.audio_codec:
            bits.append(info.audio_codec)
        bits += [format_time(info.duration, millis=False), format_size(info.size)]
        self.meta.setText("  ·  ".join(bits))

        self.timeline.set_duration(info.duration)
        self._sync_range()
        self.stack.setCurrentIndex(1)
        self.player.setSource(QUrl.fromLocalFile(info.path))
        self.player.pause()  # birinchi kadrni ko'rsatish uchun
        self._update_timecode(0.0)
        self.setFocus()

        if info.has_video:
            self._set_status("Kalit kadrlar tahlil qilinmoqda…")
            token = self._load_token
            _run_async(
                self._bridge,
                lambda: media.scan_keyframes(info.path),
                lambda kfs: token == self._load_token and self._on_keyframes(kfs),
                lambda exc: token == self._load_token and self._set_status(""),
            )
        else:
            self._set_status("")

    def _on_keyframes(self, keyframes: list[float]) -> None:
        self.keyframes = keyframes
        self.timeline.set_keyframes(keyframes)
        self._apply_snap()
        self._set_status("")
        self._update_hint()

    # ------------------------------------------------------------ oraliq --
    def _apply_snap(self) -> None:
        self.start = media.snap_to_keyframe(self.keyframes, self.requested_start) if self.keyframes else self.requested_start
        self._sync_range()

    def _sync_range(self) -> None:
        self.timeline.set_range(self.start, self.end)
        for edit, value in ((self.start_edit, self.start), (self.end_edit, self.end)):
            edit.setProperty("invalid", "false")
            edit.style().unpolish(edit)
            edit.style().polish(edit)
            if not edit.hasFocus():
                edit.setText(format_time(value))
        self.length_lbl.setText(f"Davomiylik  {format_time(self.end - self.start)}")
        self.export_btn.setEnabled(self.end - self.start > 0.01 and not self._busy())

    def _update_hint(self) -> None:
        if self._busy() or self.status.property("kind") in ("ok", "error"):
            return
        if self.keyframes and abs(self.start - self.requested_start) > 0.0005:
            self._set_status(
                f"Boshlanish eng yaqin kalit kadrga surildi ({format_time(self.requested_start)} → "
                f"{format_time(self.start)}) — shu tufayli sifat 100% saqlanadi"
            )
        else:
            self._set_status("")

    def _set_start(self, t: float) -> None:
        self.requested_start = min(max(0.0, t), self.end)
        self._apply_snap()
        self._clear_result()
        self._update_hint()

    def _set_end(self, t: float) -> None:
        if not self.info:
            return
        self.end = min(max(t, self.start), self.info.duration)
        self._sync_range()
        self._clear_result()

    def _on_range_dragged(self, start: float, end: float) -> None:
        self.requested_start, self.start, self.end = start, start, end
        self._sync_range()

    def _on_range_released(self, which: str) -> None:
        if which == "start":
            self._set_start(self.requested_start)
            self.seek(self.start)
        else:
            self._set_end(self.end)

    def _on_field_edited(self, which: str) -> None:
        if not self.info:
            return
        edit = self.start_edit if which == "start" else self.end_edit
        try:
            value = parse_time(edit.text())
        except ValueError:
            edit.setProperty("invalid", "true")
            edit.style().unpolish(edit)
            edit.style().polish(edit)
            return
        if which == "start":
            self._set_start(value)
            self.seek(self.start)
        else:
            self._set_end(value)
            self.seek(self.end)
        edit.setText(format_time(self.start if which == "start" else self.end))

    def set_in_here(self) -> None:
        if self.info:
            self._set_start(self._position())
            self.seek(self.start)

    def set_out_here(self) -> None:
        if self.info:
            self._set_end(self._position())

    # --------------------------------------------------------- o'ynatish --
    def _position(self) -> float:
        return self.player.position() / 1000.0

    def seek(self, t: float) -> None:
        if not self.info:
            return
        t = min(max(0.0, t), self.info.duration)
        self.player.setPosition(int(round(t * 1000)))
        self.timeline.set_position(t)
        self._update_timecode(t)

    def step_frames(self, n: int) -> None:
        if self.info:
            self.player.pause()
            self.seek(self._position() + n * self.info.frame_duration)

    def step_seconds(self, s: float) -> None:
        if self.info:
            self.seek(self._position() + s)

    def toggle_play(self) -> None:
        if not self.info:
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self._preview = False
            if self._position() >= self.info.duration - 0.05:
                self.seek(0)
            self.player.play()

    def preview_selection(self) -> None:
        if not self.info:
            return
        self.seek(self.start)
        self._preview = True
        self.player.play()

    def _on_position(self, ms: int) -> None:
        t = ms / 1000.0
        if self._preview and t >= self.end:
            self._preview = False
            self.player.pause()
            t = self.end
        self.timeline.set_position(t)
        self._update_timecode(t)

    def _on_state(self, state) -> None:
        self.play_btn.setText("❚❚" if state == QMediaPlayer.PlayingState else "▶")

    def _on_player_error(self, _error, message: str) -> None:
        self._set_status(f"Oldindan ko'rish imkoni yo'q ({message}), lekin qirqish ishlaydi", "error")

    def _update_timecode(self, t: float) -> None:
        total = self.info.duration if self.info else 0.0
        self.timecode.setText(f"{format_time(t)} / {format_time(total)}")

    # ------------------------------------------------------------ saqlash --
    def _busy(self) -> bool:
        return self._cancel is not None

    def export(self) -> None:
        if not self.info or self._busy() or self.end - self.start <= 0.01:
            return
        self.player.pause()
        info = self.info
        suggested = trim.suggest_output_path(info.path, self.start, self.end)
        ext = os.path.splitext(info.path)[1]
        dst, _ = QFileDialog.getSaveFileName(
            self, "Qirqilgan videoni saqlash", suggested, f"Video (*{ext});;Barcha fayllar (*)"
        )
        if not dst:
            return
        if not os.path.splitext(dst)[1]:
            dst += ext

        cancel = threading.Event()
        self._cancel = cancel
        keyframes, requested, end = self.keyframes, self.requested_start, self.end

        def job() -> str:
            start = media.snap_to_keyframe(keyframes, requested) if keyframes else media.keyframe_before(info.path, requested)
            plan = trim.TrimPlan(src=info.path, dst=dst, start=start, end=end, duration=info.duration)
            return trim.trim(plan, progress=self._bridge.progress.emit, cancel=cancel)

        self._clear_result()
        self.export_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_btn.show()
        self._set_status("Saqlanmoqda…")
        _run_async(self._bridge, job, self._on_export_done, self._on_export_failed)

    def cancel_export(self) -> None:
        if self._cancel is not None:
            self._cancel.set()

    def _on_progress(self, fraction: float) -> None:
        self.progress.setValue(int(fraction * 1000))
        self._set_status(f"Saqlanmoqda…  {int(fraction * 100)}%")

    def _finish_export(self) -> None:
        self._cancel = None
        self.progress.hide()
        self.cancel_btn.hide()
        self._sync_range()

    def _on_export_done(self, path: str) -> None:
        self._finish_export()
        self._last_output = path
        size = format_size(os.path.getsize(path)) if os.path.exists(path) else ""
        self._set_status(f"✓  Saqlandi: {os.path.basename(path)}  ·  {size}", "ok")
        self.reveal_btn.show()

    def _on_export_failed(self, exc: Exception) -> None:
        self._finish_export()
        if isinstance(exc, trim.TrimCancelled):
            self._set_status("Bekor qilindi")
        else:
            self._set_status(f"Saqlab bo'lmadi: {exc}", "error")

    def _clear_result(self) -> None:
        self.reveal_btn.hide()
        if self.status.property("kind") in ("ok", "error"):
            self._set_status("")

    # ------------------------------------------------------------- yordam --
    def _set_status(self, text: str, kind: str = "") -> None:
        self.status.setText(text)
        self.status.setProperty("kind", kind)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    # ------------------------------------------------------ sudrab tashlash --
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and not self._busy():
            e.acceptProposedAction()
            self.drop.set_active(True)

    def dragLeaveEvent(self, _e):
        self.drop.set_active(False)

    def dropEvent(self, e):
        self.drop.set_active(False)
        for url in e.mimeData().urls():
            if url.isLocalFile():
                self.load(url.toLocalFile())
                break

    def closeEvent(self, e):
        self.cancel_export()
        self.player.stop()
        super().closeEvent(e)
