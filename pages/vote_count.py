"""
투표 집계 페이지
"""

import os

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QVBoxLayout, QHBoxLayout,
    QTextEdit, QMessageBox,
)

from theme import BG, PANEL, ACCENT, TEXT, SIDEBAR_TEXT, MUTED, button_style, combo_style, result_box_style
from config import CANDIDATE_A, CANDIDATE_B, get_vote_base_dir
from logic.vote_count import count_votes_from_file
from app_state import _floating_windows


class VoteCountPage(QWidget):
    """투표 집계 페이지 - 실제로 동작하는 기능"""

    def __init__(self):
        super().__init__()
        self.base_path = get_vote_base_dir()
        self.setStyleSheet(f"background:{BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        title = QLabel("📊 투표 집계")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        sub = QLabel(f"대상 폴더: {self.base_path}")
        sub.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(sub)

        toolbar = QHBoxLayout()
        lbl = QLabel("집계할 폴더:")
        lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        toolbar.addWidget(lbl)

        self.folder_combo = QComboBox()
        self.folder_combo.setStyleSheet(combo_style())
        toolbar.addWidget(self.folder_combo)

        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        refresh_btn.clicked.connect(self.refresh_folders)
        toolbar.addWidget(refresh_btn)

        count_btn = QPushButton("✅ 집계하기")
        count_btn.setStyleSheet(button_style(ACCENT, TEXT, bold=True))
        count_btn.clicked.connect(self.run_count)
        toolbar.addWidget(count_btn)

        popout_btn = QPushButton("🔗 별도 창으로 열기")
        popout_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        popout_btn.clicked.connect(self.open_in_new_window)
        toolbar.addWidget(popout_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        layout.addWidget(self.result_box, 1)

        self.refresh_folders()

    def refresh_folders(self):
        os.makedirs(self.base_path, exist_ok=True)
        folders = [f for f in os.listdir(self.base_path)
                   if os.path.isdir(os.path.join(self.base_path, f))]
        self.folder_combo.clear()
        self.folder_combo.addItems(folders)
        if not folders:
            QMessageBox.information(self, "알림", f"'{self.base_path}' 안에 아직 집계할 폴더가 없어요.")

    def open_in_new_window(self):
        """독립된 창으로 투표 집계 화면을 하나 더 띄움 - 메인 창에서 다른 메뉴(대진표 만들기 등)로
        이동해도 이 창은 계속 떠 있어서, 결과를 보면서 다른 작업을 동시에 할 수 있음."""
        win = QWidget()
        win.setWindowTitle("📊 투표 집계 결과 (별도 창)")
        win.setStyleSheet(f"background:{BG};")
        win.resize(560, 640)
        win_layout = QVBoxLayout(win)
        win_layout.setContentsMargins(0, 0, 0, 0)
        win_layout.addWidget(VoteCountPage())
        win.show()
        _floating_windows.append(win)  # 참조를 붙잡아두지 않으면 파이썬이 바로 정리해버려서 창이 사라짐

    def run_count(self):
        folder_name = self.folder_combo.currentText()
        if not folder_name:
            QMessageBox.warning(self, "알림", "먼저 집계할 폴더를 선택해주세요.")
            return

        try:
            group_count = int(folder_name.split('_')[1].replace('조', ''))
        except (IndexError, ValueError):
            QMessageBox.critical(self, "오류", "폴더 이름 형식을 해석할 수 없어요 (예: 8강_4조).")
            return

        is_prelim = folder_name.startswith("예선전")
        folder_path = os.path.join(self.base_path, folder_name)

        if is_prelim:
            out = [f"👑 [예선전] 전체 투표 집계 결과 👑", "=" * 45, ""]
        else:
            round_num = group_count * 2
            out = [f"👑 [{round_num}강] 전체 투표 집계 결과 👑", "=" * 45, ""]

        for i in range(1, group_count + 1):
            file_path = os.path.join(folder_path, f"{i}조.txt")

            if not os.path.exists(file_path):
                out.append(f"[{i}조] ⚠️ 파일 없음, 건너뜀\n")
                continue

            a_count, b_count, others, reply_flags = count_votes_from_file(file_path)

            if a_count > b_count:
                winner = f"🏆 승자: [{CANDIDATE_A}]"
            elif b_count > a_count:
                winner = f"🏆 승자: [{CANDIDATE_B}]"
            else:
                winner = "🤝 동점!"

            out.append(f"[ {i}조 ]")
            out.append(f"  ▶ {CANDIDATE_A}: {a_count}표   ▶ {CANDIDATE_B}: {b_count}표   {winner}")

            if others:
                grouped = {}
                for comment_no, text in others:
                    grouped.setdefault(text, []).append(comment_no)
                out.append("  ⚠️ 무효표:")
                for text, nos in sorted(grouped.items(), key=lambda x: -len(x[1])):
                    nos_str = ', '.join(f"{n}번" for n in nos if n is not None)
                    out.append(f"     - {text} ({len(nos)}번) → {nos_str}")

            if reply_flags:
                out.append(f"  🚩 답글 투표 {len(reply_flags)}건 (중복 의심)")

            out.append("-" * 45)
            out.append("")

        out.append("✅ 집계 완료!")
        self.result_box.setPlainText("\n".join(out))
