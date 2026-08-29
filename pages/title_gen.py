"""
제목 생성 페이지
"""

import os

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QVBoxLayout, QHBoxLayout,
    QTextEdit, QMessageBox, QDialog,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, combo_style, result_box_style
from config import BASE_DIR, TITLE_ROUNDS
from logic.common import round_label
from logic.title import build_title_plan, build_prelim_title_plan
from widgets import TitleEditDialog, ConfirmDialog


class TitleGenPage(QWidget):
    """제목 생성 페이지 - 작업 폴더 선택 → 제목 파일 만들기/선택 → 라운드별 폴더/파일 생성"""

    def __init__(self):
        super().__init__()
        self.work_dir = BASE_DIR
        os.makedirs(self.work_dir, exist_ok=True)
        self.round_label_map = {r: round_label(r) for r in TITLE_ROUNDS}
        self.round_label_to_num = {v: k for k, v in self.round_label_map.items()}
        self.setStyleSheet(f"background:{BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("📝 제목 생성")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        # ── 1. 작업 폴더 표시 (설정 페이지에서 지정한 폴더를 그대로 씀) ──
        sub = QLabel(f"대상 폴더: {self.work_dir}")
        sub.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(sub)

        # ── 2. 제목 만들기 / 수정 / 파일 선택 ────────────
        make_row = QHBoxLayout()
        create_btn = QPushButton("🆕 제목 만들기")
        create_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        create_btn.clicked.connect(self.open_create_dialog)
        make_row.addWidget(create_btn)

        edit_btn = QPushButton("✏️ 수정")
        edit_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        edit_btn.clicked.connect(self.open_edit_dialog)
        make_row.addWidget(edit_btn)

        file_lbl = QLabel("제목 파일:")
        file_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        make_row.addWidget(file_lbl)

        self.file_combo = QComboBox()
        self.file_combo.setStyleSheet(combo_style())
        self.file_combo.currentTextChanged.connect(self.load_selected_title)
        make_row.addWidget(self.file_combo)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        refresh_btn.clicked.connect(self.refresh_title_files)
        make_row.addWidget(refresh_btn)
        make_row.addStretch()
        layout.addLayout(make_row)

        # ── 3. 미리보기 ────────────────────────────────
        preview_title = QLabel("읽어온 제목:")
        preview_title.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        layout.addWidget(preview_title)

        self.preview_label = QLabel("(제목 파일을 먼저 선택하거나 만들어주세요)")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(f"background:{ACCENT2}; color:{TEXT}; padding:8px; border-radius:4px; font-size:11pt;")
        layout.addWidget(self.preview_label)

        # ── 4. 시작 라운드 + 생성하기 ────────────────────
        round_row = QHBoxLayout()
        round_lbl = QLabel("몇 강부터 시작할까요?")
        round_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        round_row.addWidget(round_lbl)

        self.round_combo = QComboBox()
        self.round_combo.addItems([self.round_label_map[r] for r in TITLE_ROUNDS])
        self.round_combo.setStyleSheet(combo_style())
        round_row.addWidget(self.round_combo)

        gen_btn = QPushButton("✅ 생성하기")
        gen_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        gen_btn.clicked.connect(self.open_confirm_dialog)
        round_row.addWidget(gen_btn)
        round_row.addStretch()
        layout.addLayout(round_row)

        # ── 4-1. 예선전 제목은 따로 (매치 개수가 그때그때 달라서 일반 라운드 캐스케이드랑 별도로 처리) ──
        prelim_row = QHBoxLayout()
        prelim_btn = QPushButton("🎯 예선전 제목 만들기")
        prelim_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        prelim_btn.setToolTip("'예선전 대진표' 메뉴에서 먼저 예선전 대진표를 만들어두면,\n거기서 실제로 만들어진 매치 개수를 세어서 그만큼 제목을 만들어요.")
        prelim_btn.clicked.connect(self.open_prelim_confirm_dialog)
        prelim_row.addWidget(prelim_btn)

        self.prelim_hint_label = QLabel("")
        self.prelim_hint_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        prelim_row.addWidget(self.prelim_hint_label, 1)
        layout.addLayout(prelim_row)

        # ── 5. 결과 로그 ──────────────────────────────
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        self.result_box.setPlainText("여기에 생성 결과가 표시됩니다.")
        layout.addWidget(self.result_box, 1)

        self.refresh_title_files()

    # ---------------------------------------------------

    def refresh_title_files(self):
        if not self.work_dir:
            QMessageBox.warning(self, "알림", "먼저 폴더를 선택해주세요.")
            return
        files = [f for f in os.listdir(self.work_dir)
                 if f.lower().endswith(".txt") and os.path.isfile(os.path.join(self.work_dir, f))]
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItems(files)
        self.file_combo.blockSignals(False)
        if files:
            self.file_combo.setCurrentIndex(0)
            self.load_selected_title()
        else:
            self.preview_label.setText("(이 폴더엔 아직 제목 파일이 없어요. '제목 만들기'로 만들어보세요)")

    def load_selected_title(self, *_):
        fname = self.file_combo.currentText()
        if not fname or not self.work_dir:
            return
        path = os.path.join(self.work_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            self.preview_label.setText(content if content else "(파일 내용이 비어있어요)")
        except Exception as e:
            self.preview_label.setText(f"(읽기 실패: {e})")

    def open_create_dialog(self):
        self.open_title_dialog()

    def open_edit_dialog(self):
        fname = self.file_combo.currentText()
        if not fname:
            QMessageBox.warning(self, "알림", "수정할 제목 파일을 먼저 선택해주세요.")
            return
        self.open_title_dialog(edit_filename=fname)

    def open_title_dialog(self, edit_filename=None):
        """제목 만들기/수정 공용. edit_filename이 있으면 '수정 모드'로,
        입력칸에 기존 파일이름/제목을 미리 채워두고 저장 시 파일이름이 바뀌면
        기존 파일은 지우고 새 이름으로 저장함."""
        if not self.work_dir:
            QMessageBox.warning(self, "알림", "먼저 작업 폴더를 선택해주세요.")
            return

        initial_name = ""
        initial_title = ""
        if edit_filename:
            initial_name = os.path.splitext(edit_filename)[0]
            try:
                with open(os.path.join(self.work_dir, edit_filename), "r", encoding="utf-8") as f:
                    initial_title = f.read().strip()
            except Exception:
                initial_title = ""

        dlg = TitleEditDialog(self, edit_filename is not None, initial_name, initial_title)
        if dlg.exec() != QDialog.Accepted:
            return

        fname, ttl = dlg.get_values()
        if fname.lower().endswith(".txt"):
            fname = fname[:-4]

        new_path = os.path.join(self.work_dir, f"{fname}.txt")
        old_path = os.path.join(self.work_dir, edit_filename) if edit_filename else None
        is_rename = old_path is not None and os.path.normpath(old_path) != os.path.normpath(new_path)

        if os.path.exists(new_path) and (old_path is None or is_rename):
            reply = QMessageBox.question(self, "확인", f"'{fname}.txt' 파일이 이미 있어요. 덮어쓸까요?")
            if reply != QMessageBox.Yes:
                return

        try:
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(ttl)
            if is_rename and os.path.exists(old_path):
                os.remove(old_path)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일을 저장하지 못했어요: {e}")
            return

        self.refresh_title_files()
        new_name = f"{fname}.txt"
        idx = self.file_combo.findText(new_name)
        if idx >= 0:
            self.file_combo.setCurrentIndex(idx)
            self.load_selected_title()

    def open_confirm_dialog(self):
        if not self.work_dir:
            QMessageBox.warning(self, "알림", "먼저 작업 폴더를 선택해주세요.")
            return
        fname = self.file_combo.currentText()
        if not fname:
            QMessageBox.warning(self, "알림", "제목 파일을 선택해주세요.")
            return

        title_text = self.preview_label.text()
        if not title_text or title_text.startswith("("):
            QMessageBox.warning(self, "알림", "제목 내용이 비어있어요.")
            return

        round_label_selected = self.round_combo.currentText()
        start_round = self.round_label_to_num.get(round_label_selected)
        if start_round is None:
            QMessageBox.warning(self, "알림", "시작 라운드를 선택해주세요.")
            return

        contest_name = os.path.splitext(fname)[0]
        plan = build_title_plan(self.work_dir, contest_name, title_text, start_round)

        preview_lines = [
            f"작업 폴더: {self.work_dir}",
            f"대회명(파일명 기준): {contest_name}",
            f"제목: {title_text}",
            f"시작 라운드: {round_label_selected}",
            "",
            "생성될 폴더 / 파일:",
            "-" * 50,
        ]
        for round_num, folder_path, file_path, lines in plan:
            preview_lines.append(f"📁 {os.path.basename(folder_path)}/")
            preview_lines.append(f"   └ 📄 {os.path.basename(file_path)}  ({len(lines)}개 제목)")

        dlg = ConfirmDialog(self, "\n".join(preview_lines))
        if dlg.exec() == QDialog.Accepted:
            self.generate_titles(plan)

    def generate_titles(self, plan):
        out = ["🎬 생성을 시작합니다...", "=" * 45, ""]

        for round_num, folder_path, file_path, lines in plan:
            try:
                os.makedirs(folder_path, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(lines))
                out.append(
                    f"✅ {round_label(round_num)} 완료! ({len(lines)}개 제목) → "
                    f"{os.path.basename(folder_path)}/{os.path.basename(file_path)}"
                )
            except Exception as e:
                out.append(f"❌ {round_label(round_num)} 실패: {e}")

        out.append("")
        out.append("=" * 45)
        out.append(f"🎉 {len(plan)}개 파일 생성 완료!")
        self.result_box.setPlainText("\n".join(out))

    def open_prelim_confirm_dialog(self):
        title_text = self.preview_label.text()
        if not title_text or title_text.startswith("("):
            QMessageBox.warning(self, "알림", "제목 내용이 비어있어요. 먼저 제목 파일을 선택하거나 만들어주세요.")
            return

        match_count, folder_path, file_path, lines = build_prelim_title_plan(title_text)
        if match_count == 0:
            QMessageBox.warning(
                self, "알림",
                "예선전 대진표를 아직 못 찾았어요.\n"
                "먼저 '대진표 만들기' → '예선전' 탭에서 예선전 대진표를 만들어주세요."
            )
            return

        preview_lines = [
            f"제목: {title_text}",
            f"예선전 매치 개수: {match_count}개 (실제로 만들어진 대진표 기준)",
            "",
            "생성될 폴더 / 파일:",
            "-" * 50,
            f"📁 {os.path.basename(folder_path)}/",
            f"   └ 📄 {os.path.basename(file_path)}  ({len(lines)}개 제목)",
        ]

        dlg = ConfirmDialog(self, "\n".join(preview_lines))
        if dlg.exec() != QDialog.Accepted:
            return

        out = ["🎬 예선전 제목 생성을 시작합니다...", "=" * 45, ""]
        try:
            os.makedirs(folder_path, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(lines))
            out.append(f"✅ 예선전 완료! ({len(lines)}개 제목) → {os.path.basename(folder_path)}/{os.path.basename(file_path)}")
        except Exception as e:
            out.append(f"❌ 예선전 실패: {e}")

        out.append("")
        out.append("=" * 45)
        out.append("🎉 예선전 제목 파일 생성 완료!")
        self.result_box.setPlainText("\n".join(out))
        self.prelim_hint_label.setText(f"✅ 방금 {match_count}개 예선전 제목을 만들었어요.")
