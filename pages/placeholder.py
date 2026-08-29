"""
자리표시자 페이지 (아직 구현 안 된 메뉴용)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

from theme import BG, PANEL, TEXT, MUTED


class PlaceholderPage(QWidget):
    """아직 구현 안 된 기능 자리표시자"""

    def __init__(self, emoji, name, desc):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")

        outer = QVBoxLayout(self)
        outer.addStretch()

        emoji_lbl = QLabel(emoji)
        emoji_lbl.setAlignment(Qt.AlignCenter)
        emoji_lbl.setStyleSheet(f"color:{TEXT}; font-size:40px; background:transparent;")
        outer.addWidget(emoji_lbl)

        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(f"color:{TEXT}; font-size:16px; font-weight:bold; background:transparent;")
        outer.addWidget(name_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setMaximumWidth(420)
        desc_lbl.setStyleSheet(f"color:{MUTED}; background:transparent;")
        outer.addWidget(desc_lbl, alignment=Qt.AlignHCenter)

        note_lbl = QLabel("🚧 다음 버전에서 이 자리에 실제 기능이 들어갑니다")
        note_lbl.setAlignment(Qt.AlignCenter)
        note_lbl.setStyleSheet(f"color:{PANEL}; background:transparent;")
        outer.addWidget(note_lbl)

        outer.addStretch()
