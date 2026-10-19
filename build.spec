# PyInstaller: pyinstaller --noconfirm build.spec
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files("imageio_ffmpeg")  # ichidagi ffmpeg dasturi
binaries = collect_dynamic_libs("av")

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=["PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3DCore"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VideoEditor2000",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="VideoEditor2000")
