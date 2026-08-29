"""
공용 위젯 / 다이얼로그
====================================
여러 페이지(제목생성, 대진표만들기, 예선전, 자동업로드, 댓글수집)에서
반복해서 쓰이는 작은 UI 조각들을 모아둠.
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QMessageBox, QDialog, QFrame, QScrollArea,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, result_box_style
from app_state import pyautogui, HAS_AUTOMATION, _floating_windows
from position_cache import save_cache


class TitleEditDialog(QDialog):
    """제목 만들기 / 수정 공용 팝업"""

    def __init__(self, parent, is_edit, initial_name="", initial_title=""):
        super().__init__(parent)
        self.setWindowTitle("제목 수정" if is_edit else "제목 만들기")
        self.setStyleSheet(f"background:{BG};")
        self.resize(420, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(4)

        name_lbl = QLabel("파일 이름:")
        name_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        layout.addWidget(name_lbl)

        self.name_edit = QLineEdit(initial_name)
        layout.addWidget(self.name_edit)
        layout.addSpacing(10)

        title_lbl = QLabel("월드컵 제목:")
        title_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        layout.addWidget(title_lbl)

        self.title_edit = QLineEdit(initial_title)
        layout.addWidget(self.title_edit)

        hint = QLabel("💡 이모티콘/특수문자도 자유롭게 입력하실 수 있어요.")
        hint.setStyleSheet(f"color:{MUTED}; font-size:8pt; background:transparent;")
        layout.addWidget(hint)
        layout.addStretch()

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("저장" if is_edit else "생성")
        ok_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        ok_btn.clicked.connect(self.try_accept)
        btn_row.addWidget(ok_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.name_edit.setFocus()

    def try_accept(self):
        if not self.name_edit.text().strip() or not self.title_edit.text().strip():
            QMessageBox.warning(self, "알림", "파일 이름과 제목을 모두 입력해주세요.")
            return
        self.accept()

    def get_values(self):
        return self.name_edit.text().strip(), self.title_edit.text().strip()


class ConfirmDialog(QDialog):
    """생성 전 미리보기 확인 팝업"""

    def __init__(self, parent, preview_text):
        super().__init__(parent)
        self.setWindowTitle("생성 전 확인")
        self.setStyleSheet(f"background:{BG};")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        head = QLabel("이렇게 만들 예정이에요. 진행할까요?")
        head.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        layout.addWidget(head)

        box = QTextEdit()
        box.setReadOnly(True)
        box.setPlainText(preview_text)
        box.setStyleSheet(result_box_style())
        layout.addWidget(box, 1)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("✅ 확인, 생성할게요")
        ok_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


def build_photo_frame(image_paths, display_name, highlighted):
    """뷰어 창 전용: 클릭 안 되는 사진(1~4장 카드)+이름 표시. highlighted면 선택된 것처럼 강조 테두리.
    image_paths는 리스트여야 함 (1장이면 원소 1개짜리 리스트)."""
    if isinstance(image_paths, str):
        image_paths = [image_paths]  # 예전 방식(문자열 하나)으로 호출해도 동작하게

    n = max(1, len(image_paths))
    photo_w = 190 if n == 1 else max(90, 190 // n)

    frame = QFrame()
    border_width = "3px" if highlighted else "2px"
    border_color = ACCENT if highlighted else PANEL
    bg = ACCENT2 if highlighted else "white"
    frame.setStyleSheet(f"QFrame {{ background:{bg}; border:{border_width} solid {border_color}; border-radius:8px; }}")
    frame.setFixedSize(max(220, photo_w * n + 20 + (n - 1) * 4), 230)

    v = QVBoxLayout(frame)
    v.setContentsMargins(8, 8, 8, 8)

    photos_row = QHBoxLayout()
    photos_row.setSpacing(4)
    for path in image_paths[:4]:
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(photo_w, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_lbl.setPixmap(pixmap)
        photos_row.addWidget(img_lbl)
    v.addLayout(photos_row)

    short_name = display_name if len(display_name) <= 30 else display_name[:27] + "..."
    name_lbl = QLabel(short_name)
    name_lbl.setAlignment(Qt.AlignCenter)
    name_lbl.setWordWrap(True)
    weight = "bold" if highlighted else "normal"
    name_lbl.setStyleSheet(f"color:{TEXT}; font-size:8pt; font-weight:{weight}; background:transparent;")
    v.addWidget(name_lbl)

    return frame


def show_match_viewer(parent, matches, title_text):
    """지금까지 입력한 선택을 사진으로 보여주는 확인용 별도 창 (클릭 안 됨, 보기 전용).
    승자입력/예선전 둘 다 이 함수를 공용으로 씀."""
    if not matches:
        QMessageBox.warning(parent, "알림", "먼저 매치를 불러와주세요.")
        return

    win = QWidget()
    win.setWindowTitle(title_text)
    win.setStyleSheet(f"background:{BG};")
    win.resize(560, 640)
    win_layout = QVBoxLayout(win)
    win_layout.setContentsMargins(16, 16, 16, 16)

    header = QLabel("입력하신 숫자대로 어떤 사진이 선택됐는지 보여드려요. (클릭은 안 돼요)")
    header.setStyleSheet(f"color:{TEXT}; background:transparent;")
    header.setWordWrap(True)
    win_layout.addWidget(header)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
    container = QWidget()
    container.setStyleSheet("background:transparent;")
    v = QVBoxLayout(container)
    v.setSpacing(10)

    for m in matches:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        group_lbl = QLabel(f"{m['group_num']}조")
        group_lbl.setFixedWidth(50)
        group_lbl.setStyleSheet(f"color:{TEXT}; font-weight:bold; font-size:11pt; background:transparent;")
        row_layout.addWidget(group_lbl)

        paths_a = m.get("paths_a") or [m["path_a"]]
        paths_b = m.get("paths_b") or [m["path_b"]]
        name_a = m["file_a"] if len(paths_a) == 1 else f"{m['file_a']} 외 {len(paths_a) - 1}장"
        name_b = m["file_b"] if len(paths_b) == 1 else f"{m['file_b']} 외 {len(paths_b) - 1}장"

        row_layout.addWidget(build_photo_frame(paths_a, name_a, m.get("selected") == "A"))
        row_layout.addWidget(build_photo_frame(paths_b, name_b, m.get("selected") == "B"))
        row_layout.addStretch()

        v.addWidget(row_widget)

    v.addStretch()
    scroll.setWidget(container)
    win_layout.addWidget(scroll, 1)

    win.show()
    _floating_windows.append(win)


class PhotoChoiceButton(QFrame):
    """썸네일(1~4장 카드) + 이름을 보여주고, 클릭하면 선택 표시가 되는 위젯 (부전승 선택용).
    QToolButton은 아이콘을 1개만 가질 수 있어서, 여러 장을 나란히 보여주려고 QFrame 기반으로 직접 구현함."""

    clicked = Signal()

    def __init__(self, image_paths, display_name, size=140):
        super().__init__()
        if isinstance(image_paths, str):
            image_paths = [image_paths]  # 예전 방식(문자열 하나)으로 호출해도 동작하게

        self._checked = False
        self.setCursor(Qt.PointingHandCursor)

        n = max(1, len(image_paths))
        photo_w = size if n == 1 else max(int(size * 0.55), size // n)
        self.setFixedSize(photo_w * n + 16 + (n - 1) * 4, size + 46)

        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(2)

        photos_row = QHBoxLayout()
        photos_row.setSpacing(4)
        for path in image_paths[:4]:
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(photo_w, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl.setPixmap(pixmap)
            photos_row.addWidget(img_lbl)
        v.addLayout(photos_row)

        max_name_len = 34 if size >= 220 else 16
        short_name = display_name if len(display_name) <= max_name_len else display_name[:max_name_len - 3] + "..."
        self.name_lbl = QLabel(short_name)
        self.name_lbl.setAlignment(Qt.AlignCenter)
        font_size = 8 if size >= 220 else 7
        self.name_lbl.setStyleSheet(f"color:{TEXT}; font-size:{font_size}pt; background:transparent;")
        v.addWidget(self.name_lbl)

        self._apply_style()

    def _apply_style(self):
        if self._checked:
            self.setStyleSheet(f"QFrame {{ background:{ACCENT2}; border:3px solid {ACCENT}; border-radius:8px; }}")
        else:
            self.setStyleSheet(f"QFrame {{ background:white; border:2px solid {PANEL}; border-radius:8px; }}")

    def isChecked(self):
        return self._checked

    def setChecked(self, value):
        self._checked = bool(value)
        self._apply_style()

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        self.clicked.emit()
        super().mousePressEvent(event)


class CoordCaptureRow(QWidget):
    """좌표 캡처 한 줄: 설명 + 저장된 값 표시 + '캡처' 버튼(3초 카운트다운)"""

    captured = Signal()  # 캡처가 끝나면 알림 (전체 순서대로 캡처 기능이 이걸 듣고 다음으로 넘어감)

    def __init__(self, cache_key, desc, cache_dict):
        super().__init__()
        self.cache_key = cache_key
        self.desc = desc
        self.cache_dict = cache_dict
        self.countdown = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        self.desc_lbl = QLabel(desc)
        self.desc_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        self.desc_lbl.setFixedWidth(260)
        row.addWidget(self.desc_lbl)

        cached = cache_dict.get(cache_key)
        self.value_label = QLabel(f"({cached[0]}, {cached[1]})" if cached else "미설정")
        self.value_label.setStyleSheet(f"color:{MUTED}; background:transparent;")
        self.value_label.setFixedWidth(120)
        row.addWidget(self.value_label)

        self.capture_btn = QPushButton("🎯 3초 후 캡처")
        self.capture_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        self.capture_btn.clicked.connect(self.start_capture)
        row.addWidget(self.capture_btn)
        row.addStretch()

    def set_highlight(self, on):
        """'전체 순서대로 캡처' 진행 중, 지금 차례인 항목을 눈에 띄게 표시"""
        if on:
            self.desc_lbl.setStyleSheet(f"color:{TEXT}; background:{ACCENT2}; font-weight:bold; border-radius:4px; padding:2px 4px;")
        else:
            self.desc_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")

    def start_capture(self):
        if not HAS_AUTOMATION:
            QMessageBox.warning(self, "알림", "pyautogui가 설치되어 있지 않아요.\n터미널에서 'pip install pyautogui pyperclip' 실행해주세요.")
            return
        self.countdown = 3
        self.capture_btn.setEnabled(False)
        self.capture_btn.setText(f"{self.countdown}초...")
        self.timer.start(1000)

    def _tick(self):
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer.stop()
            pos = pyautogui.position()
            self.cache_dict[self.cache_key] = [pos.x, pos.y]
            save_cache(self.cache_dict)
            self.value_label.setText(f"({pos.x}, {pos.y})")
            self.capture_btn.setText("🎯 3초 후 캡처")
            self.capture_btn.setEnabled(True)
            self.captured.emit()
        else:
            self.capture_btn.setText(f"{self.countdown}초...")

    def get_value(self):
        v = self.cache_dict.get(self.cache_key)
        return tuple(v) if v else None

    def reset_value(self):
        """이 좌표를 (0, 0)으로 리셋함"""
        self.cache_dict[self.cache_key] = [0, 0]
        save_cache(self.cache_dict)
        self.value_label.setText("(0, 0)")