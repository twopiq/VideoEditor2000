import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")


def _wait(app, cond, timeout=15):
    end = time.monotonic() + timeout
    while not cond():
        if time.monotonic() > end:
            raise TimeoutError
        app.processEvents()
        time.sleep(0.01)


def test_load_select_and_export(sample_video, tmp_path, monkeypatch):
    from videoeditor.ui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w = MainWindow()
    w.load(sample_video)
    _wait(app, lambda: w.keyframes)
    assert w.stack.currentIndex() == 1

    w.start_edit.setText("5.3")
    w._on_field_edited("start")
    w.end_edit.setText("0:09.5")
    w._on_field_edited("end")
    assert w.start == pytest.approx(4)  # kalit kadrga surildi
    assert w.end == pytest.approx(9.5)
    assert "kalit kadr" in w.status.text()

    dst = str(tmp_path / "ui_out.mp4")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (dst, "")))
    w.export()
    _wait(app, lambda: not w._busy())
    assert os.path.exists(dst), w.status.text()
    assert w.status.property("kind") == "ok"
    w.close()
