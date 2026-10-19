"""Ranglar va umumiy uslub (qorong'i, minimalistik)."""

BG = "#0f1012"
SURFACE = "#17181b"
SURFACE_2 = "#1f2024"
BORDER = "#2a2b30"
TRACK = "#232428"
TEXT = "#ececee"
MUTED = "#8b8d94"
ACCENT = "#f2c94c"
ACCENT_HOVER = "#ffdb70"
ACCENT_TEXT = "#141414"
SUCCESS = "#5ccf8a"
DANGER = "#ef6b6b"

QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, #root {{ background: {BG}; }}
QToolTip {{
    background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 4px 6px; border-radius: 4px;
}}
#title {{ font-size: 14px; font-weight: 600; }}
#meta, #hint {{ color: {MUTED}; }}
#hint {{ font-size: 12px; }}
#status {{ color: {MUTED}; }}
#status[kind="ok"] {{ color: {SUCCESS}; }}
#status[kind="error"] {{ color: {DANGER}; }}
#timecode {{ font-family: "Cascadia Mono", "JetBrains Mono", "Consolas", monospace; color: {MUTED}; }}

#dropZone {{
    background: {SURFACE}; border: 1.5px dashed {BORDER}; border-radius: 16px;
}}
#dropZone[active="true"] {{ border-color: {ACCENT}; background: {SURFACE_2}; }}
#dropTitle {{ font-size: 20px; font-weight: 600; }}
#dropSub {{ color: {MUTED}; }}

#video {{ background: #000; border-radius: 12px; }}
#panel {{ background: {SURFACE}; border-radius: 14px; }}

QPushButton {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 7px 14px;
}}
QPushButton:hover {{ border-color: #3a3b42; background: #26272c; }}
QPushButton:pressed {{ background: #2d2e33; }}
QPushButton:disabled {{ color: #55575d; }}
QPushButton#primary {{
    background: {ACCENT}; color: {ACCENT_TEXT}; border: none; font-weight: 600;
    padding: 9px 20px;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: #5a5136; color: #2a2a2a; }}
QPushButton#ghost {{ background: transparent; border: none; color: {MUTED}; padding: 6px 8px; }}
QPushButton#ghost:hover {{ color: {TEXT}; }}
QPushButton#icon {{
    min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px;
    padding: 0; border-radius: 18px; font-size: 14px;
}}
QPushButton#link {{
    background: transparent; border: none; color: {ACCENT}; padding: 0;
}}
QPushButton#link:hover {{ text-decoration: underline; }}

QLineEdit {{
    background: {BG}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 6px 8px; selection-background-color: {ACCENT}; selection-color: {ACCENT_TEXT};
    font-family: "Cascadia Mono", "JetBrains Mono", "Consolas", monospace;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QLineEdit[invalid="true"] {{ border-color: {DANGER}; }}

QCheckBox {{ color: {MUTED}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid {BORDER}; background: {BG};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QProgressBar {{
    background: {TRACK}; border: none; border-radius: 3px; max-height: 6px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
"""
