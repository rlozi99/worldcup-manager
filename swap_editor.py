"""
대진표 스왑(자리 맞바꾸기) 편집 창
====================================
"이 두 사람은 진짜 결승감인데 너무 일찍 만났다" 싶을 때, 이미 만들어진 대진표에서
두 사람의 자리를 클릭클릭으로 골라서 실제로 맞바꿔주는 별도 창.
디스크의 실제 파일 이름을 바꿔서 반영하기 때문에, 창을 닫아도 계속 유지됨.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit,
    QMessageBox, QScrollArea, QGridLayout,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, result_box_style
from logic.tournament import load_round_bracket, swap_bracket_slots
from logic.common import round_label
from widgets import PhotoChoiceButton
from app_state import _floating_windows


class SwapEditorWindow(QWidget):
    """이미 만들어진 라운드의 대진표를 자리(슬롯) 단위로 보여주고, 두 자리를 골라 맞바꾸는 창"""

    def __init__(self, round_key):
        super().__init__()
        self.round_key = round_key
        round_display = "예선전" if round_key == "prelim" else round_label(round_key)

        self.setWindowTitle(f"🔄 {round_display} 대진표 수정")
        self.setStyleSheet(f"background:{BG};")
        self.resize(720, 720)

        self.selected = []  # [(slot_dict, button), ...] 최대 2개

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QLabel(
            "자리를 바꾸고 싶은 두 사람을 클릭해서 선택한 다음, 아래 '맞바꾸기' 버튼을 눌러주세요.\n"
            "바뀐 내용은 실제 파일에 바로 반영되고, 이 창을 닫아도 계속 유지돼요."
        )
        header.setStyleSheet(f"color:{TEXT}; background:transparent;")
        header.setWordWrap(True)
        layout.addWidget(header)

        self.status_label = QLabel("선택됨: 0 / 2")
        self.status_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background:transparent;")
        self.grid = QGridLayout(self.grid_container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(6)
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll, 1)

        swap_btn = QPushButton("🔄 선택한 두 자리 맞바꾸기")
        swap_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        swap_btn.clicked.connect(self.do_swap)
        layout.addWidget(swap_btn, alignment=Qt.AlignLeft)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        self.result_box.setMaximumHeight(120)
        self.result_box.setPlainText("여기에 맞바꾼 기록이 표시됩니다.")
        layout.addWidget(self.result_box)

        self.reload_matches()

    def reload_matches(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.selected = []
        self.status_label.setText("선택됨: 0 / 2")

        source_dir, matches = load_round_bracket(self.round_key)
        if matches is None:
            self.grid.addWidget(QLabel(f"❌ 본선 폴더를 찾을 수 없어요: {source_dir}"), 0, 0)
            return
        if not matches:
            self.grid.addWidget(QLabel("⚠️ 이 라운드에서 매치를 찾지 못했어요. 먼저 대진표를 만들어주세요."), 0, 0)
            return

        cols = 4
        idx = 0
        for m in matches:
            for side in ("A", "B"):
                files = m[f"files_{side.lower()}"]
                paths = m[f"paths_{side.lower()}"]
                display = files[0] if len(files) == 1 else f"{files[0]} 외 {len(files) - 1}장"
                slot = {"group_num": m["group_num"], "side": side, "paths": paths}

                btn = PhotoChoiceButton(paths, f"{m['group_num']}조-{side}\n{display}", size=120)
                btn.clicked.connect(lambda checked=False, s=slot, b=btn: self.on_slot_clicked(s, b))
                self.grid.addWidget(btn, idx // cols, idx % cols)
                idx += 1

    def on_slot_clicked(self, slot, btn):
        if btn.isChecked():
            if len(self.selected) >= 2:
                btn.setChecked(False)  # 이미 2개 선택된 상태면 3번째 클릭은 무시
                return
            self.selected.append((slot, btn))
        else:
            self.selected = [(s, b) for s, b in self.selected if b is not btn]
        self.status_label.setText(f"선택됨: {len(self.selected)} / 2")

    def do_swap(self):
        if len(self.selected) != 2:
            QMessageBox.warning(self, "알림", "정확히 두 자리를 선택해주세요.")
            return

        (slot_a, _), (slot_b, _) = self.selected
        if slot_a["group_num"] == slot_b["group_num"] and slot_a["side"] == slot_b["side"]:
            QMessageBox.warning(self, "알림", "같은 자리를 두 번 선택했어요.")
            return

        msg = swap_bracket_slots(self.round_key, slot_a, slot_b)
        self.result_box.append(msg)
        self.reload_matches()  # 바뀐 상태로 새로고침 (선택도 초기화됨)


def open_swap_editor(round_key):
    """새 창으로 스왑 편집기를 띄움 (호출한 페이지가 사라져도 창은 유지됨)"""
    win = SwapEditorWindow(round_key)
    win.show()
    _floating_windows.append(win)
    return win