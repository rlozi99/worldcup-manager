"""
설정 페이지
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit,
    QMessageBox, QFileDialog, QComboBox,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, combo_style
from config import save_settings, get_current_settings


class SettingsPage(QWidget):
    """설정 페이지 - config.py 대신 여기서 작업 폴더/대회명/라벨을 입력하고 저장"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setStyleSheet(f"background:{BG};")
        current = get_current_settings()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("⚙️ 설정")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        note = QLabel("여기서 값을 바꾸면 저장 후 앱이 새 설정으로 다시 시작돼요.")
        note.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(note)

        # ── 작업 폴더 ──
        folder_lbl = QLabel("작업 폴더 (BASE_DIR)")
        folder_lbl.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        layout.addWidget(folder_lbl)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(current.get("BASE_DIR", ""))
        folder_row.addWidget(self.folder_edit, 1)

        browse_btn = QPushButton("📁 찾아보기")
        browse_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        browse_btn.clicked.connect(self.browse_folder)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # ── 대회명 ──
        name_lbl = QLabel("대회명 (TOURNA_NAME)")
        name_lbl.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        layout.addWidget(name_lbl)

        self.name_edit = QLineEdit(current.get("TOURNA_NAME", ""))
        layout.addWidget(self.name_edit)

        # ── 라벨 A / B ──
        label_row_title = QLabel("투표 라벨 (파일명용, 숫자 접두사 포함)")
        label_row_title.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        layout.addWidget(label_row_title)

        label_row = QHBoxLayout()
        a_lbl = QLabel("A:")
        a_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        label_row.addWidget(a_lbl)
        self.label_a_edit = QLineEdit(current.get("LABEL_A", ""))
        self.label_a_edit.setMaximumWidth(120)
        label_row.addWidget(self.label_a_edit)

        b_lbl = QLabel("B:")
        b_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        label_row.addWidget(b_lbl)
        self.label_b_edit = QLineEdit(current.get("LABEL_B", ""))
        self.label_b_edit.setMaximumWidth(120)
        label_row.addWidget(self.label_b_edit)
        label_row.addStretch()
        layout.addLayout(label_row)

        hint = QLabel("💡 라벨 맨 앞 글자는 파일명 구분용 접두사예요 (예: '1홍' → 투표 집계에는 '홍'만 씀)")
        hint.setStyleSheet(f"color:{MUTED}; font-size:8pt; background:transparent;")
        layout.addWidget(hint)

        # ── 댓글 작성자 표시문구 / 답글 태그 (투표 집계용) ──
        comment_title = QLabel("댓글 집계용 사이트 표시문구")
        comment_title.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        layout.addWidget(comment_title)

        author_row = QHBoxLayout()
        author_lbl = QLabel("작성자 표시문구:")
        author_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        author_row.addWidget(author_lbl)
        self.author_label_edit = QLineEdit(current.get("COMMENT_AUTHOR_LABEL", ""))
        author_row.addWidget(self.author_label_edit, 1)
        layout.addLayout(author_row)

        reply_row = QHBoxLayout()
        reply_lbl = QLabel("답글 태그:")
        reply_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        reply_row.addWidget(reply_lbl)
        self.reply_tag_edit = QLineEdit(current.get("REPLY_TAG", ""))
        self.reply_tag_edit.setMaximumWidth(120)
        reply_row.addWidget(self.reply_tag_edit)
        reply_row.addStretch()
        layout.addLayout(reply_row)

        comment_hint = QLabel(
            "💡 댓글이 \"1. [작성자 표시문구] 날짜...\" 형태로 뜨는 사이트 기준이에요.\n"
            "   그 사이트에서 실제로 어떻게 표시되는지 그대로 입력해주세요 (투표 집계 정확도에 영향을 줘요)."
        )
        comment_hint.setStyleSheet(f"color:{MUTED}; font-size:8pt; background:transparent;")
        layout.addWidget(comment_hint)

        # ── 1인당 사진 장수 ──
        photos_title = QLabel("참가자 1인당 사진 장수")
        photos_title.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        layout.addWidget(photos_title)

        current_photos_per_person = int(current.get("PHOTOS_PER_PERSON", 1) or 1)

        photos_row = QHBoxLayout()
        self.multi_photo_checkbox = QPushButton(
            "☑️ 여러 장 올리기" if current_photos_per_person > 1 else "⬜ 여러 장 올리기"
        )
        self.multi_photo_checkbox.setCheckable(True)
        self.multi_photo_checkbox.setChecked(current_photos_per_person > 1)
        self.multi_photo_checkbox.setCursor(Qt.PointingHandCursor)
        self.multi_photo_checkbox.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{TEXT}; border:none; text-align:left;
                padding:2px 0px; font-size:10pt;
            }}
        """)
        self.multi_photo_checkbox.toggled.connect(self.on_multi_photo_toggle)
        photos_row.addWidget(self.multi_photo_checkbox)

        count_lbl = QLabel("몇 장?")
        count_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        photos_row.addWidget(count_lbl)

        self.photos_count_combo = QComboBox()
        self.photos_count_combo.addItems(["2장", "3장", "4장"])
        self.photos_count_combo.setStyleSheet(combo_style())
        if current_photos_per_person >= 2:
            self.photos_count_combo.setCurrentIndex(min(current_photos_per_person, 4) - 2)
        self.photos_count_combo.setEnabled(current_photos_per_person > 1)
        photos_row.addWidget(self.photos_count_combo)
        photos_row.addStretch()
        layout.addLayout(photos_row)

        photos_hint = QLabel(
            "💡 체크 안 하면 기존이랑 완전히 동일(1인당 1장)하게 동작해요.\n"
            "   체크하면 원본 사진 파일명이 '이름_1.jpg', '이름_2.jpg' ... 형태여야 자동 인식돼요.\n"
            "   이름 규칙이 없는 사진들은 '🔗 사진 짝짓기' 메뉴에서 클릭클릭으로 짝지어주면 자동으로 정리돼요."
        )
        photos_hint.setStyleSheet(f"color:{MUTED}; font-size:8pt; background:transparent;")
        layout.addWidget(photos_hint)

        layout.addStretch()

        # ── 저장 버튼 ──
        save_row = QHBoxLayout()
        save_btn = QPushButton("💾 저장하고 재시작")
        save_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        save_btn.clicked.connect(self.save_and_restart)
        save_row.addWidget(save_btn)
        save_row.addStretch()
        layout.addLayout(save_row)

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "작업 폴더를 선택하세요")
        if path:
            self.folder_edit.setText(os.path.normpath(path))

    def on_multi_photo_toggle(self, checked):
        self.multi_photo_checkbox.setText("☑️ 여러 장 올리기" if checked else "⬜ 여러 장 올리기")
        self.photos_count_combo.setEnabled(checked)

    def save_and_restart(self):
        base_dir = self.folder_edit.text().strip()
        tourna_name = self.name_edit.text().strip()
        label_a = self.label_a_edit.text().strip()
        label_b = self.label_b_edit.text().strip()
        author_label = self.author_label_edit.text().strip()
        reply_tag = self.reply_tag_edit.text().strip()

        if not base_dir or not tourna_name or not label_a or not label_b:
            QMessageBox.warning(self, "알림", "모든 항목을 입력해주세요.")
            return
        if len(label_a) < 2 or len(label_b) < 2:
            QMessageBox.warning(self, "알림", "라벨은 접두사+이름 형태로 2글자 이상이어야 해요. (예: '1홍')")
            return
        if not author_label:
            QMessageBox.warning(self, "알림", "댓글 작성자 표시문구를 입력해주세요 (투표 집계에 필요해요).")
            return

        if self.multi_photo_checkbox.isChecked():
            photos_per_person = int(self.photos_count_combo.currentText().replace("장", ""))
        else:
            photos_per_person = 1

        save_settings({
            "BASE_DIR": base_dir,
            "TOURNA_NAME": tourna_name,
            "LABEL_A": label_a,
            "LABEL_B": label_b,
            "COMMENT_AUTHOR_LABEL": author_label,
            "REPLY_TAG": reply_tag,
            "PHOTOS_PER_PERSON": photos_per_person,
        })

        reply = QMessageBox.question(
            self, "저장 완료", "설정을 저장했어요! 지금 바로 재시작해서 적용할까요?"
        )
        if reply == QMessageBox.Yes:
            self.main_window.restart_app()
        else:
            QMessageBox.information(self, "안내", "다음에 앱을 다시 켜면 새 설정이 적용돼요.")