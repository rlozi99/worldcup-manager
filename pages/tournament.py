"""
대진표 만들기 페이지 - '새로 만들기' / '승자 입력하기' 두 모드
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QFileDialog, QMessageBox, QDialog, QScrollArea,
    QStackedWidget,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, combo_style, result_box_style
from config import BASE_DIR, VALID_ROUNDS, LABEL_A, LABEL_B, get_bonsun_dir
from logic.common import round_label
from logic.tournament import (
    compute_default_source, build_bracket_plan, apply_bracket_plan,
    load_matches_for_round, apply_next_round, apply_final_and_third,
    generate_thumbnails_for_round,
)
from widgets import ConfirmDialog, show_match_viewer
from swap_editor import open_swap_editor


class TournamentPage(QWidget):
    """대진표 만들기 페이지 - '새로 만들기' / '승자 입력하기' 두 모드"""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        self.source_dir = None       # 새로 만들기 모드에서 쓸 소스 폴더
        self.bracket_pairs = None    # 새로 만들기 모드: 마지막으로 계산한 짝
        self.matches = []            # 승자 입력 모드: 매치 목록
        self.match_group = None      # 현재 렌더링된 QButtonGroup들

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("🏆 대진표 만들기")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        sub = QLabel(f"작업 폴더: {BASE_DIR}")
        sub.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(sub)

        # ── 모드 전환 탭 ──
        mode_row = QHBoxLayout()
        self.create_mode_btn = QPushButton("🆕 새로 만들기")
        self.create_mode_btn.clicked.connect(lambda: self.switch_mode(0))
        mode_row.addWidget(self.create_mode_btn)

        self.winners_mode_btn = QPushButton("🏅 승자 입력하기")
        self.winners_mode_btn.clicked.connect(lambda: self.switch_mode(1))
        mode_row.addWidget(self.winners_mode_btn)

        mode_row.addStretch()
        layout.addLayout(mode_row)

        # ── 라운드 선택 ('새로 만들기' 모드에서만 보임 - 승자입력 모드는 아래 '가져올 라운드'를 씀) ──
        self.round_row_container = QWidget()
        round_row = QHBoxLayout(self.round_row_container)
        round_row.setContentsMargins(0, 0, 0, 0)
        round_lbl = QLabel("생성할 라운드:")
        round_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        round_row.addWidget(round_lbl)

        self.round_label_map = {r: round_label(r) for r in VALID_ROUNDS}
        self.round_label_to_num = {v: k for k, v in self.round_label_map.items()}
        self.round_combo = QComboBox()
        self.round_combo.addItems([self.round_label_map[r] for r in VALID_ROUNDS])
        self.round_combo.setStyleSheet(combo_style())
        self.round_combo.currentTextChanged.connect(self.on_round_changed)
        round_row.addWidget(self.round_combo)
        round_row.addStretch()
        layout.addWidget(self.round_row_container)

        # ── 지금 썸네일/스왑 버튼이 대상으로 삼는 라운드가 어디인지 항상 보여줌
        #     (새로 만들기 모드: 위 드롭다운 값 / 승자입력 모드: '가져올 라운드'로 계산된 목표 라운드) ──
        self.effective_round_label = QLabel("")
        self.effective_round_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.effective_round_label)

        # ── 썸네일 같이 생성 체크박스 (기본 체크 안 됨) + 나중에 따로 다시 만들기 ──
        thumb_row = QHBoxLayout()
        self.thumbnail_checkbox = QPushButton("⬜ 썸네일 생성")
        self.thumbnail_checkbox.setCheckable(True)
        self.thumbnail_checkbox.setChecked(False)
        self.thumbnail_checkbox.setCursor(Qt.PointingHandCursor)
        self.thumbnail_checkbox.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{TEXT}; border:none; text-align:left;
                padding:2px 0px; font-size:10pt;
            }}
        """)
        self.thumbnail_checkbox.toggled.connect(self.on_thumbnail_toggle)
        thumb_row.addWidget(self.thumbnail_checkbox)

        redo_thumb_btn = QPushButton("🖼️ 이 라운드 썸네일만 다시 만들기")
        redo_thumb_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        redo_thumb_btn.setToolTip("체크박스를 깜빡했을 때를 위한 버튼이에요.\n대진표(조 편성)는 전혀 건드리지 않고, 이미 만들어진 본선 폴더의 GIF만 다시 읽어서 JPG로 뽑아요.")
        redo_thumb_btn.clicked.connect(self.redo_thumbnails_only)
        thumb_row.addWidget(redo_thumb_btn)
        thumb_row.addStretch()
        layout.addLayout(thumb_row)

        swap_row = QHBoxLayout()
        swap_btn = QPushButton("🔄 이 라운드 대진표 수정 (자리 맞바꾸기)")
        swap_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        swap_btn.setToolTip("이미 만들어진 대진표에서, 두 사람의 자리를 클릭클릭으로 골라 맞바꿀 수 있어요.\n(예: 결승감인 두 사람이 초반에 붙었을 때)")
        swap_btn.clicked.connect(self.open_swap_editor)
        swap_row.addWidget(swap_btn)
        swap_row.addStretch()
        layout.addLayout(swap_row)

        # ── 모드별 패널 ──
        self.stack = QStackedWidget()
        self.create_panel = self._build_create_panel()
        self.winners_panel = self._build_winners_panel()
        self.stack.addWidget(self.create_panel)
        self.stack.addWidget(self.winners_panel)
        layout.addWidget(self.stack, 1)

        # ── 결과 로그 ──
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        self.result_box.setMaximumHeight(140)
        self.result_box.setPlainText("여기에 생성 결과가 표시됩니다.")
        layout.addWidget(self.result_box)

        self.switch_mode(0)
        self.recompute_default_source()

    # ------------------------------------------------------------
    #  공통
    # ------------------------------------------------------------

    def current_round(self):
        return self.round_label_to_num[self.round_combo.currentText()]

    def winners_target_round(self):
        """'가져올 라운드'(소스)로 선택한 값으로부터, 실제로 만들어질 목표 라운드를 계산함.
        예: 64강을 가져오면 -> 32강이 만들어짐. 4강을 가져오면 -> 2강(결승·3,4위)이 만들어짐."""
        import_round = self.import_round_label_to_num[self.import_round_combo.currentText()]
        return import_round // 2

    def effective_round(self):
        """지금 썸네일/스왑 버튼이 대상으로 삼을 라운드.
        새로 만들기 모드: 위 '생성할 라운드' 드롭다운 값 / 승자입력 모드: '가져올 라운드'로 계산된 목표 라운드"""
        if self.stack.currentIndex() == 1:
            return self.winners_target_round()
        return self.current_round()

    def update_effective_round_label(self):
        self.effective_round_label.setText(f"📍 지금 썸네일/수정 버튼이 대상으로 삼는 라운드: {round_label(self.effective_round())}")

    def update_winners_target_hint(self, *_):
        target = self.winners_target_round()
        self.winners_target_hint.setText(f"→ {round_label(target)}이 만들어져요")
        self.update_effective_round_label()

    def switch_mode(self, index):
        self.stack.setCurrentIndex(index)
        self.round_row_container.setVisible(index == 0)  # 승자입력 모드에선 '가져올 라운드'만 보이면 되니 숨김
        self.create_mode_btn.setStyleSheet(button_style(ACCENT if index == 0 else PANEL,
                                                          ACCENT2 if index == 0 else SIDEBAR_TEXT, bold=(index == 0)))
        self.winners_mode_btn.setStyleSheet(button_style(ACCENT if index == 1 else PANEL,
                                                           ACCENT2 if index == 1 else SIDEBAR_TEXT, bold=(index == 1)))
        self.update_effective_round_label()

    def on_round_changed(self, *_):
        if self.stack.currentIndex() == 0:
            self.recompute_default_source()
        self.update_effective_round_label()

    def on_thumbnail_toggle(self, checked):
        self.thumbnail_checkbox.setText("☑️ 썸네일 생성" if checked else "⬜ 썸네일 생성")

    def redo_thumbnails_only(self):
        """대진표(조 편성)는 절대 건드리지 않고, 선택된 라운드의 본선 폴더에서 썸네일만 다시 생성함.
        '썸네일 생성' 체크를 깜빡했을 때 셔플을 다시 안 하고 안전하게 복구할 수 있게 하기 위한 버튼."""
        round_size = self.effective_round()
        target_dir = get_bonsun_dir(round_size)
        if not os.path.isdir(target_dir):
            QMessageBox.warning(self, "알림", f"아직 이 라운드의 본선 폴더가 없어요:\n{target_dir}\n\n먼저 대진표를 만들어주세요.")
            return

        log = generate_thumbnails_for_round(round_size)
        log.insert(0, f"🔒 대진표(조 편성)는 그대로 두고, 썸네일만 다시 만들었어요. ({round_label(round_size)})")
        self.result_box.setPlainText("\n".join(log))

    def open_swap_editor(self):
        round_size = self.effective_round()
        open_swap_editor(round_size)

    # ------------------------------------------------------------
    #  ① 새로 만들기 패널
    # ------------------------------------------------------------

    def _build_create_panel(self):
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(8)

        desc = QLabel("원본 사진들이 있는 폴더에서 무작위로 셔플해서 조를 편성해요.")
        desc.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        v.addWidget(desc)

        src_row = QHBoxLayout()
        src_lbl = QLabel("소스 폴더:")
        src_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        src_row.addWidget(src_lbl)

        self.source_label = QLabel("-")
        self.source_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        self.source_label.setWordWrap(True)
        src_row.addWidget(self.source_label, 1)

        change_src_btn = QPushButton("📁 다른 폴더 선택")
        change_src_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        change_src_btn.clicked.connect(self.choose_source_folder)
        src_row.addWidget(change_src_btn)
        v.addLayout(src_row)

        make_btn = QPushButton("🆕 대진표 만들기")
        make_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        make_btn.clicked.connect(self.open_bracket_confirm)
        v.addWidget(make_btn, alignment=Qt.AlignLeft)

        v.addStretch()
        return panel

    def recompute_default_source(self):
        round_size = self.current_round()
        self.source_dir = compute_default_source(round_size)
        self.source_label.setText(self.source_dir)

    def choose_source_folder(self):
        path = QFileDialog.getExistingDirectory(self, "소스 폴더를 선택하세요", self.source_dir or BASE_DIR)
        if path:
            self.source_dir = os.path.normpath(path)
            self.source_label.setText(self.source_dir)

    def open_bracket_confirm(self):
        round_size = self.current_round()
        if not self.source_dir or not os.path.isdir(self.source_dir):
            QMessageBox.critical(self, "오류", f"소스 폴더를 찾을 수 없어요:\n{self.source_dir}")
            return

        total, pairs, dropped, leftover = build_bracket_plan(self.source_dir, round_size)

        if leftover:
            reply = QMessageBox.question(
                self, "확인",
                f"사진 장수 규칙에 안 맞아서 묶이지 못한 파일이 {len(leftover)}개 있어요 "
                f"(예: {', '.join(leftover[:3])}{' ...' if len(leftover) > 3 else ''}).\n"
                f"이 파일들은 빼고, 정상 인식된 {total}명으로만 진행할까요?"
            )
            if reply != QMessageBox.Yes:
                return

        if total != round_size:
            reply = QMessageBox.question(
                self, "확인",
                f"인식된 인원이 {total}명이에요. {round_size}강을 하려면 정확히 {round_size}명이 필요한데,\n"
                f"그래도 계속 진행할까요? ({len(pairs)}개 조가 만들어져요)"
            )
            if reply != QMessageBox.Yes:
                return

        if not pairs:
            QMessageBox.warning(self, "알림", "짝지을 수 있는 파일이 없어요.")
            return

        target_dir = get_bonsun_dir(round_size)
        preview_lines = [
            f"소스 폴더: {self.source_dir}",
            f"저장 위치: {target_dir}",
            f"대상: {round_label(round_size)} ({len(pairs)}개 조)",
        ]
        if dropped:
            preview_lines.append("⚠️ 파일 개수가 홀수라 마지막 1개는 제외돼요.")
        preview_lines.append("")
        preview_lines.append("생성될 조 편성:")
        preview_lines.append("-" * 50)
        for group_num, files_a, new_names_a, files_b, new_names_b in pairs:
            a_desc = new_names_a[0] if len(new_names_a) == 1 else f"{new_names_a[0]} 외 {len(new_names_a) - 1}장"
            b_desc = new_names_b[0] if len(new_names_b) == 1 else f"{new_names_b[0]} 외 {len(new_names_b) - 1}장"
            preview_lines.append(f"{group_num}조 → {LABEL_A}: {a_desc}")
            preview_lines.append(f"       {LABEL_B}: {b_desc}")

        dlg = ConfirmDialog(self, "\n".join(preview_lines))
        if dlg.exec() == QDialog.Accepted:
            log = apply_bracket_plan(self.source_dir, target_dir, pairs)
            log.append("")
            log.append(f"📁 저장 위치: {target_dir}")

            if self.thumbnail_checkbox.isChecked():
                log.append("")
                log.extend(generate_thumbnails_for_round(round_size))

            self.result_box.setPlainText("\n".join(log))

    # ------------------------------------------------------------
    #  ② 승자 입력 패널
    # ------------------------------------------------------------

    def _build_winners_panel(self):
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(8)

        desc = QLabel("이전 라운드 매치가 나오면, 숫자 1 또는 2를 입력하고 Enter를 누르며 쭉쭉 진행해주세요.")
        desc.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        v.addWidget(desc)

        # ── '가져올 라운드' - 방금 끝낸(승자를 뽑아올) 라운드를 그대로 고르면 됨.
        #     ("생성할 라운드"는 목표 라운드라 헷갈린다는 피드백 반영 - 여기선 반대로 소스 라운드를 고름)
        import_row = QHBoxLayout()
        import_lbl = QLabel("가져올 라운드:")
        import_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        import_row.addWidget(import_lbl)

        # 2강(결승)은 더 아래 라운드가 없어서 '가져올' 대상이 될 수 없으므로 제외
        self.import_rounds = [r for r in VALID_ROUNDS if r != 2]
        self.import_round_label_map = {r: round_label(r) for r in self.import_rounds}
        self.import_round_label_to_num = {v: k for k, v in self.import_round_label_map.items()}
        self.import_round_combo = QComboBox()
        self.import_round_combo.addItems([self.import_round_label_map[r] for r in self.import_rounds])
        self.import_round_combo.setStyleSheet(combo_style())
        import_row.addWidget(self.import_round_combo)

        self.winners_target_hint = QLabel("")
        self.winners_target_hint.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        import_row.addWidget(self.winners_target_hint, 1)
        self.import_round_combo.currentTextChanged.connect(self.update_winners_target_hint)
        v.addLayout(import_row)
        self.update_winners_target_hint()

        load_row = QHBoxLayout()
        load_btn = QPushButton("🔄 불러오기")
        load_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        load_btn.clicked.connect(self.load_matches)
        load_row.addWidget(load_btn)

        self.winners_status_label = QLabel("라운드를 선택하고 '불러오기'를 눌러주세요.")
        self.winners_status_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        load_row.addWidget(self.winners_status_label, 1)
        v.addLayout(load_row)

        self.matches_scroll = QScrollArea()
        self.matches_scroll.setWidgetResizable(True)
        self.matches_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.matches_container = QWidget()
        self.matches_container.setStyleSheet("background:transparent;")
        self.matches_layout = QVBoxLayout(self.matches_container)
        self.matches_layout.setSpacing(6)
        self.matches_scroll.setWidget(self.matches_container)
        v.addWidget(self.matches_scroll, 1)

        confirm_row = QHBoxLayout()
        self.build_next_btn = QPushButton("✅ 다음 라운드 만들기")
        self.build_next_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        self.build_next_btn.clicked.connect(self.confirm_and_build_next_round)
        confirm_row.addWidget(self.build_next_btn)
        confirm_row.addStretch()

        self.viewer_btn = QPushButton("🔎 뷰어로 확인")
        self.viewer_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        self.viewer_btn.clicked.connect(self.open_viewer)
        confirm_row.addWidget(self.viewer_btn)
        v.addLayout(confirm_row)

        return panel

    def load_matches(self):
        round_size = self.winners_target_round()
        prev_round_size, source_dir, matches = load_matches_for_round(round_size)

        # 기존 매치 입력줄 지우기
        while self.matches_layout.count():
            item = self.matches_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.match_inputs = []

        if matches is None:
            self.winners_status_label.setText(f"❌ 폴더를 찾을 수 없어요: {source_dir}")
            self.matches = []
            return
        if not matches:
            self.winners_status_label.setText(f"⚠️ '{os.path.basename(source_dir)}' 안에서 매치를 찾지 못했어요.")
            self.matches = []
            return

        self.matches = matches
        self.winners_status_label.setText(
            f"'{os.path.basename(source_dir)}' 에서 {len(matches)}개 매치를 불러왔어요. "
            f"숫자 입력하고 Enter → 자동으로 다음 칸으로 넘어가요."
        )

        for m in self.matches:
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
            input_edit.returnPressed.connect(lambda mm=m, edit=input_edit: self._on_match_input(mm, edit))
            row_layout.addWidget(input_edit)

            self.matches_layout.addWidget(row_widget)
            self.match_inputs.append(input_edit)

        self.matches_layout.addStretch()
        if self.match_inputs:
            self.match_inputs[0].setFocus()

    def _on_match_input(self, match, edit):
        text = edit.text().strip()
        if text not in ("1", "2"):
            edit.setStyleSheet(f"background:#ffe0e0; color:{TEXT}; border:2px solid #e08080; border-radius:4px; padding:4px; font-size:11pt;")
            return

        match["selected"] = "A" if text == "1" else "B"
        edit.setStyleSheet(f"background:{ACCENT2}; color:{TEXT}; border:2px solid {ACCENT}; border-radius:4px; padding:4px; font-size:11pt;")

        idx = self.match_inputs.index(edit)
        if idx + 1 < len(self.match_inputs):
            next_edit = self.match_inputs[idx + 1]
            next_edit.setFocus()
            self.matches_scroll.ensureWidgetVisible(next_edit)
        else:
            self.build_next_btn.setFocus()
            self.winners_status_label.setText("✅ 마지막 매치까지 입력했어요! '다음 라운드 만들기'를 눌러주세요.")

    def open_viewer(self):
        show_match_viewer(self, self.matches, "🔎 승자 확인 뷰어")

    def confirm_and_build_next_round(self):
        if not self.matches:
            QMessageBox.warning(self, "알림", "먼저 '불러오기'로 매치를 불러와주세요.")
            return

        not_selected = [m["group_num"] for m in self.matches if not m["selected"]]
        if not_selected:
            QMessageBox.warning(self, "알림", f"아직 승자를 선택 안 한 조가 있어요: {', '.join(map(str, not_selected))}조")
            return

        round_size = self.winners_target_round()
        reply = QMessageBox.question(
            self, "확인",
            f"{len(self.matches)}개 매치의 승자로 {round_label(round_size)} 대진표를 만들게요. 진행할까요?"
        )
        if reply != QMessageBox.Yes:
            return

        if round_size == 2:
            log = apply_final_and_third(self.matches)
        else:
            log = apply_next_round(self.matches, round_size)

        log.append("")
        log.append(f"📁 저장 위치: {get_bonsun_dir(round_size)}")

        if self.thumbnail_checkbox.isChecked():
            log.append("")
            log.extend(generate_thumbnails_for_round(round_size))

        self.result_box.setPlainText("\n".join(log))

        # 방금 만든 라운드를 상단 '생성할 라운드'에도 반영 -> 썸네일/스왑 버튼이 바로 이 라운드를 가리키게 됨
        if round_size in self.round_label_map:
            self.round_combo.setCurrentText(self.round_label_map[round_size])