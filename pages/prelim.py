"""
예선전 대진표 페이지 - 참가자 수가 128/64/32...에 딱 안 맞을 때 (독립된 페이지)
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QFileDialog, QMessageBox, QScrollArea, QGridLayout,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, combo_style, result_box_style
from config import BASE_DIR, VALID_ROUNDS, get_all_photos_dir, get_bonsun_dir
from logic.common import round_label
from logic.prelim import (
    compute_prelim_plan, build_prelim_plan, apply_prelim_plan,
    load_prelim_matches, apply_prelim_merge, get_prelim_byes_dir, get_prelim_bonsun_dir,
    group_prelim_source_files,
)
from widgets import PhotoChoiceButton, show_match_viewer
from swap_editor import open_swap_editor


class PrelimPage(QWidget):
    """예선전 대진표 페이지 - 참가자 수가 128/64/32...에 딱 안 맞을 때 (독립된 페이지)"""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        title = QLabel("🎯 예선전 대진표")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        sub = QLabel(f"작업 폴더: {BASE_DIR}")
        sub.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(sub)

        # ── 목표 라운드 + 소스 폴더 ──
        round_row = QHBoxLayout()
        round_lbl = QLabel("목표 라운드:")
        round_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        round_row.addWidget(round_lbl)

        self.round_label_map = {r: round_label(r) for r in VALID_ROUNDS}
        self.round_label_to_num = {v: k for k, v in self.round_label_map.items()}
        self.round_combo = QComboBox()
        self.round_combo.addItems([self.round_label_map[r] for r in VALID_ROUNDS])
        self.round_combo.setStyleSheet(combo_style())
        round_row.addWidget(self.round_combo)
        round_row.addStretch()
        layout.addLayout(round_row)

        src_row = QHBoxLayout()
        src_lbl = QLabel("소스 폴더:")
        src_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        src_row.addWidget(src_lbl)

        self.prelim_source_label = QLabel(get_all_photos_dir())
        self.prelim_source_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        self.prelim_source_label.setWordWrap(True)
        src_row.addWidget(self.prelim_source_label, 1)

        change_src_btn = QPushButton("📁 다른 폴더 선택")
        change_src_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        change_src_btn.clicked.connect(self.choose_prelim_source_folder)
        src_row.addWidget(change_src_btn)
        layout.addLayout(src_row)

        load_row = QHBoxLayout()
        load_btn = QPushButton("🔍 불러오기")
        load_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        load_btn.clicked.connect(self.load_prelim_source)
        load_row.addWidget(load_btn)

        self.prelim_status_label = QLabel("소스 폴더를 확인하고 '불러오기'를 눌러주세요.")
        self.prelim_status_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        load_row.addWidget(self.prelim_status_label, 1)
        layout.addLayout(load_row)

        # ── 부전승 선택용 사진 그리드 ──
        self.byes_picked_label = QLabel("")
        self.byes_picked_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.byes_picked_label)

        self.byes_scroll = QScrollArea()
        self.byes_scroll.setWidgetResizable(True)
        self.byes_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.byes_container = QWidget()
        self.byes_container.setStyleSheet("background:transparent;")
        self.byes_grid = QGridLayout(self.byes_container)
        self.byes_grid.setContentsMargins(0, 0, 0, 0)
        self.byes_grid.setSpacing(6)
        self.byes_scroll.setWidget(self.byes_container)
        self.byes_scroll.setMinimumHeight(380)
        layout.addWidget(self.byes_scroll, 7)

        layout.addSpacing(10)

        make_prelim_btn = QPushButton("✅ 부전승 확정 + 예선전 대진표 만들기")
        make_prelim_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        make_prelim_btn.clicked.connect(self.confirm_prelim_bracket)
        layout.addWidget(make_prelim_btn, alignment=Qt.AlignLeft)

        layout.addSpacing(6)

        # ── 예선전 매치 승자 입력 ──
        prelim_match_row = QHBoxLayout()
        reload_matches_btn = QPushButton("🔄 예선전 매치 불러오기")
        reload_matches_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        reload_matches_btn.clicked.connect(self.load_prelim_matches_ui)
        prelim_match_row.addWidget(reload_matches_btn)

        self.prelim_match_status = QLabel("")
        self.prelim_match_status.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        prelim_match_row.addWidget(self.prelim_match_status, 1)
        layout.addLayout(prelim_match_row)

        self.prelim_matches_scroll = QScrollArea()
        self.prelim_matches_scroll.setWidgetResizable(True)
        self.prelim_matches_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.prelim_matches_container = QWidget()
        self.prelim_matches_container.setStyleSheet("background:transparent;")
        self.prelim_matches_layout = QVBoxLayout(self.prelim_matches_container)
        self.prelim_matches_layout.setContentsMargins(0, 0, 0, 0)
        self.prelim_matches_layout.setSpacing(6)
        self.prelim_matches_scroll.setWidget(self.prelim_matches_container)
        layout.addWidget(self.prelim_matches_scroll, 3)

        merge_row = QHBoxLayout()
        self.merge_btn = QPushButton("🔀 부전승과 합쳐서 목표 라운드 만들기")
        self.merge_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        self.merge_btn.clicked.connect(self.confirm_prelim_merge)
        merge_row.addWidget(self.merge_btn)
        merge_row.addStretch()

        prelim_viewer_btn = QPushButton("🔎 뷰어로 확인")
        prelim_viewer_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        prelim_viewer_btn.clicked.connect(lambda: show_match_viewer(self, self.prelim_matches, "🔎 예선전 확인 뷰어"))
        merge_row.addWidget(prelim_viewer_btn)

        swap_btn = QPushButton("🔄 예선전 대진표 수정")
        swap_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        swap_btn.setToolTip("이미 만들어진 예선전 매치에서, 두 사람의 자리를 클릭클릭으로 골라 맞바꿀 수 있어요.")
        swap_btn.clicked.connect(lambda: open_swap_editor("prelim"))
        merge_row.addWidget(swap_btn)
        layout.addLayout(merge_row)

        # ── 결과 로그 ──
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        self.result_box.setMaximumHeight(80)
        self.result_box.setPlainText("여기에 생성 결과가 표시됩니다.")
        layout.addWidget(self.result_box)

        self.prelim_source_dir = get_all_photos_dir()
        self.prelim_all_files = []
        self.prelim_groups = []     # 사람 단위로 묶인 파일 그룹들
        self.byes_buttons = {}      # person_key(첫 파일명) -> PhotoChoiceButton
        self.prelim_matches = []
        self.prelim_match_inputs = []

    def current_round(self):
        return self.round_label_to_num[self.round_combo.currentText()]

    def choose_prelim_source_folder(self):
        path = QFileDialog.getExistingDirectory(self, "예선전 원본 사진 폴더를 선택하세요", self.prelim_source_dir)
        if path:
            self.prelim_source_dir = os.path.normpath(path)
            self.prelim_source_label.setText(self.prelim_source_dir)

    def load_prelim_source(self):
        if not os.path.isdir(self.prelim_source_dir):
            QMessageBox.critical(self, "오류", f"폴더를 찾을 수 없어요:\n{self.prelim_source_dir}")
            return

        self.prelim_all_files = [f for f in os.listdir(self.prelim_source_dir)
                                  if os.path.isfile(os.path.join(self.prelim_source_dir, f)) and not f.startswith('.')]

        groups, leftover = group_prelim_source_files(self.prelim_all_files)
        self.prelim_groups = groups
        total = len(groups)
        target_round = self.current_round()
        plan = compute_prelim_plan(total, target_round)

        while self.byes_grid.count():
            item = self.byes_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.byes_buttons = {}

        leftover_note = f" (⚠️ {len(leftover)}개 파일은 사진 장수 규칙에 안 맞아서 제외됨)" if leftover else ""

        if plan is None:
            self.prelim_status_label.setText(
                f"❌ 총 {total}명은 {round_label(target_round)} 예선전 조건에 안 맞아요. "
                f"(목표 라운드보다 많고, 2배 이하여야 해요){leftover_note}"
            )
            self.byes_picked_label.setText("")
            return

        byes_count, prelim_count, matches_count = plan
        self.prelim_needed_byes = byes_count
        self.prelim_status_label.setText(
            f"✅ 총 {total}명 → 부전승 {byes_count}명 필요, 예선전 {prelim_count}명({matches_count}경기) → "
            f"{round_label(target_round)} 완성{leftover_note}"
        )

        cols = 4
        for idx, person_files in enumerate(groups):
            paths = [os.path.join(self.prelim_source_dir, f) for f in person_files]
            key = person_files[0]  # 사람 키 = 첫 번째 사진 파일명
            display_name = person_files[0] if len(person_files) == 1 else f"{person_files[0]} 외 {len(person_files) - 1}장"
            btn = PhotoChoiceButton(paths, display_name, size=140)
            btn.clicked.connect(self.update_byes_picked_count)
            self.byes_grid.addWidget(btn, idx // cols, idx % cols)
            self.byes_buttons[key] = btn

        self.update_byes_picked_count()

        # 사진을 나중에(동적으로) 채워 넣으면 Qt가 이 영역의 실제 크기를 즉시 다시 계산 안 해서
        # 아래 버튼들이 옛날 위치에 남아 사진 위에 겹쳐 보이는 버그가 있음 -> 강제로 다시 계산시킴
        self.byes_container.adjustSize()
        self.byes_scroll.updateGeometry()
        self.layout().activate()
        self.updateGeometry()

    def update_byes_picked_count(self):
        picked = sum(1 for b in self.byes_buttons.values() if b.isChecked())
        need = getattr(self, "prelim_needed_byes", 0)
        color = ACCENT if picked == need else MUTED
        self.byes_picked_label.setText(f"선택됨: {picked} / {need}개")
        self.byes_picked_label.setStyleSheet(f"color:{color}; font-size:9pt; font-weight:bold; background:transparent;")

    def confirm_prelim_bracket(self):
        if not self.byes_buttons:
            QMessageBox.warning(self, "알림", "먼저 '불러오기'로 사진들을 불러와주세요.")
            return

        picked = [key for key, btn in self.byes_buttons.items() if btn.isChecked()]
        need = getattr(self, "prelim_needed_byes", 0)
        if len(picked) != need:
            QMessageBox.warning(self, "알림", f"부전승을 정확히 {need}명 선택해주세요. (지금 {len(picked)}명 선택됨)")
            return

        target_round = self.current_round()
        total_people = len(self.prelim_groups)
        reply = QMessageBox.question(
            self, "확인",
            f"부전승 {len(picked)}명 확정하고, 나머지 {total_people - len(picked)}명으로 "
            f"예선전 대진표를 만들게요. 진행할까요?"
        )
        if reply != QMessageBox.Yes:
            return

        byes_list, pairs, leftover = build_prelim_plan(self.prelim_all_files, set(picked))
        log = apply_prelim_plan(self.prelim_source_dir, byes_list, pairs)
        log.append("")
        log.append(f"📁 부전승 저장 위치: {get_prelim_byes_dir()}")
        log.append(f"📁 예선전 저장 위치: {get_prelim_bonsun_dir()}")
        self.result_box.setPlainText("\n".join(log))

        self.load_prelim_matches_ui()

    def load_prelim_matches_ui(self):
        source_dir, matches = load_prelim_matches()

        while self.prelim_matches_layout.count():
            item = self.prelim_matches_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.prelim_match_inputs = []

        if matches is None:
            self.prelim_match_status.setText(f"❌ 예선전 폴더를 찾을 수 없어요: {source_dir}")
            self.prelim_matches = []
            return
        if not matches:
            self.prelim_match_status.setText("⚠️ 예선전 매치를 찾지 못했어요. 먼저 위에서 대진표를 만들어주세요.")
            self.prelim_matches = []
            return

        self.prelim_matches = matches
        self.prelim_match_status.setText(f"{len(matches)}개 매치를 불러왔어요. 숫자 입력하고 Enter로 진행하세요.")

        for m in self.prelim_matches:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            group_lbl = QLabel(f"{m['group_num']}조")
            group_lbl.setFixedWidth(50)
            group_lbl.setStyleSheet(f"color:{TEXT}; font-weight:bold; font-size:11pt; background:transparent;")
            row_layout.addWidget(group_lbl)

            name_a = m["file_a"] if len(m.get("files_a", [m["file_a"]])) == 1 else f"{m['file_a']} 외 {len(m['files_a']) - 1}장"
            name_b = m["file_b"] if len(m.get("files_b", [m["file_b"]])) == 1 else f"{m['file_b']} 외 {len(m['files_b']) - 1}장"
            names_lbl = QLabel(f"1: {name_a}\n2: {name_b}")
            names_lbl.setStyleSheet(f"color:{TEXT}; font-size:9pt; background:transparent;")
            row_layout.addWidget(names_lbl, 1)

            input_edit = QLineEdit()
            input_edit.setValidator(QIntValidator(1, 2))
            input_edit.setMaxLength(1)
            input_edit.setFixedWidth(50)
            input_edit.setAlignment(Qt.AlignCenter)
            input_edit.setPlaceholderText("1/2")
            input_edit.setStyleSheet(f"background:white; color:{TEXT}; border:2px solid {PANEL}; border-radius:4px; padding:4px; font-size:11pt;")
            input_edit.returnPressed.connect(lambda mm=m, edit=input_edit: self._on_prelim_match_input(mm, edit))
            row_layout.addWidget(input_edit)

            self.prelim_matches_layout.addWidget(row_widget)
            self.prelim_match_inputs.append(input_edit)

        self.prelim_matches_layout.addStretch()
        if self.prelim_match_inputs:
            self.prelim_match_inputs[0].setFocus()

    def _on_prelim_match_input(self, match, edit):
        text = edit.text().strip()
        if text not in ("1", "2"):
            edit.setStyleSheet(f"background:#ffe0e0; color:{TEXT}; border:2px solid #e08080; border-radius:4px; padding:4px; font-size:11pt;")
            return

        match["selected"] = "A" if text == "1" else "B"
        edit.setStyleSheet(f"background:{ACCENT2}; color:{TEXT}; border:2px solid {ACCENT}; border-radius:4px; padding:4px; font-size:11pt;")

        idx = self.prelim_match_inputs.index(edit)
        if idx + 1 < len(self.prelim_match_inputs):
            next_edit = self.prelim_match_inputs[idx + 1]
            next_edit.setFocus()
            self.prelim_matches_scroll.ensureWidgetVisible(next_edit)
        else:
            self.merge_btn.setFocus()
            self.prelim_match_status.setText("✅ 마지막 매치까지 입력했어요! '부전승과 합쳐서 만들기'를 눌러주세요.")

    def confirm_prelim_merge(self):
        if not self.prelim_matches:
            QMessageBox.warning(self, "알림", "먼저 예선전 매치를 불러와주세요.")
            return

        not_selected = [m["group_num"] for m in self.prelim_matches if not m["selected"]]
        if not_selected:
            QMessageBox.warning(self, "알림", f"아직 승자를 선택 안 한 조가 있어요: {', '.join(map(str, not_selected))}조")
            return

        target_round = self.current_round()
        reply = QMessageBox.question(
            self, "확인",
            f"예선전 승자 {len(self.prelim_matches)}명 + 부전승을 합쳐서 "
            f"{round_label(target_round)} 대진표를 완성할게요. 진행할까요?"
        )
        if reply != QMessageBox.Yes:
            return

        log = apply_prelim_merge(self.prelim_matches, target_round)
        log.append("")
        log.append(f"📁 저장 위치: {get_bonsun_dir(target_round)}")
        self.result_box.setPlainText("\n".join(log))