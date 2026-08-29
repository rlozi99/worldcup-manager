"""
사진 짝짓기 페이지
====================================
이름 규칙(이름_1.jpg, 이름_2.jpg ...)을 안 지키고 아무렇게나 가져온 사진들을,
화면에서 클릭클릭으로 "이 여러 장은 같은 사람"이라고 묶어주면
자동으로 표준 이름 규칙에 맞게 정리해주는 화면.
정리된 폴더는 그대로 '대진표 만들기'의 소스 폴더로 쓸 수 있음.
"""

import os
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit,
    QFileDialog, QMessageBox, QScrollArea, QGridLayout, QInputDialog,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, result_box_style
from config import BASE_DIR, PHOTOS_PER_PERSON
from logic.common import get_ext, build_labeled_names
from widgets import PhotoChoiceButton


class PhotoPairingPage(QWidget):
    """사진 짝짓기 페이지 - PHOTOS_PER_PERSON 장씩 클릭해서 묶으면 자동으로 이름_1.ext, 이름_2.ext ... 로 정리"""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        self.source_dir = BASE_DIR
        self.output_dir = None
        self.unpaired_buttons = {}  # filename -> PhotoChoiceButton
        self.paired_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        title = QLabel("🔗 사진 짝짓기")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        if PHOTOS_PER_PERSON <= 1:
            note = QLabel(
                "지금 설정은 '1인당 1장'이라 이 화면은 필요 없어요.\n"
                "'⚙️ 설정' 메뉴에서 '여러 장 올리기'를 켜시면 여기서 사진들을 짝지을 수 있어요."
            )
            note.setStyleSheet(f"color:{MUTED}; background:transparent;")
            note.setWordWrap(True)
            layout.addWidget(note)
            layout.addStretch()
            return

        desc = QLabel(
            f"지금 설정은 1인당 {PHOTOS_PER_PERSON}장이에요. "
            f"같은 사람 사진을 {PHOTOS_PER_PERSON}장씩 클릭해서 선택한 다음 '이 사람으로 묶기'를 눌러주세요."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(desc)

        # ── 소스 폴더 ──
        src_row = QHBoxLayout()
        src_lbl = QLabel("원본 폴더:")
        src_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        src_row.addWidget(src_lbl)

        self.source_label = QLabel(self.source_dir)
        self.source_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        self.source_label.setWordWrap(True)
        src_row.addWidget(self.source_label, 1)

        change_src_btn = QPushButton("📁 다른 폴더 선택")
        change_src_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        change_src_btn.clicked.connect(self.choose_source_folder)
        src_row.addWidget(change_src_btn)
        layout.addLayout(src_row)

        load_row = QHBoxLayout()
        load_btn = QPushButton("🔍 불러오기")
        load_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        load_btn.clicked.connect(self.load_source)
        load_row.addWidget(load_btn)

        self.status_label = QLabel("원본 폴더를 확인하고 '불러오기'를 눌러주세요.")
        self.status_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        load_row.addWidget(self.status_label, 1)
        layout.addLayout(load_row)

        self.picked_label = QLabel("")
        self.picked_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.picked_label)

        # ── 짝 안 지어진 사진 그리드 ──
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background:transparent;")
        self.photo_grid = QGridLayout(self.grid_container)
        self.photo_grid.setContentsMargins(0, 0, 0, 0)
        self.photo_grid.setSpacing(6)
        self.grid_scroll.setWidget(self.grid_container)
        self.grid_scroll.setMinimumHeight(360)
        layout.addWidget(self.grid_scroll, 6)

        layout.addSpacing(8)

        pair_btn = QPushButton(f"✅ 선택한 {PHOTOS_PER_PERSON}장을 한 사람으로 묶기")
        pair_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        pair_btn.clicked.connect(self.commit_pair)
        layout.addWidget(pair_btn, alignment=Qt.AlignLeft)

        # ── 결과 로그 ──
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        self.result_box.setMaximumHeight(150)
        self.result_box.setPlainText(
            "여기에 묶인 결과가 표시됩니다.\n다 묶고 나면 정리된 폴더를 '대진표 만들기'의 소스 폴더로 선택하시면 돼요."
        )
        layout.addWidget(self.result_box)

    # ------------------------------------------------------------

    def choose_source_folder(self):
        path = QFileDialog.getExistingDirectory(self, "원본 사진 폴더를 선택하세요", self.source_dir)
        if path:
            self.source_dir = os.path.normpath(path)
            self.source_label.setText(self.source_dir)

    def load_source(self):
        if not os.path.isdir(self.source_dir):
            QMessageBox.critical(self, "오류", f"폴더를 찾을 수 없어요:\n{self.source_dir}")
            return

        self.output_dir = self.source_dir.rstrip("\\/") + "(정리됨)"
        self.paired_count = 0

        files = [f for f in os.listdir(self.source_dir)
                 if os.path.isfile(os.path.join(self.source_dir, f)) and not f.startswith('.')]
        self._rebuild_grid(files)
        self.status_label.setText(f"✅ {len(files)}장 불러왔어요. {PHOTOS_PER_PERSON}장씩 선택해서 묶어주세요.")
        self.result_box.setPlainText(f"📁 정리된 파일은 여기에 저장돼요: {self.output_dir}\n")

    def _rebuild_grid(self, files):
        while self.photo_grid.count():
            item = self.photo_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.unpaired_buttons = {}

        cols = 5
        for idx, fname in enumerate(sorted(files)):
            btn = PhotoChoiceButton([os.path.join(self.source_dir, fname)], fname, size=110)
            btn.clicked.connect(self.update_picked_count)
            self.photo_grid.addWidget(btn, idx // cols, idx % cols)
            self.unpaired_buttons[fname] = btn

        self.update_picked_count()

        self.grid_container.adjustSize()
        self.grid_scroll.updateGeometry()
        self.layout().activate()
        self.updateGeometry()

    def update_picked_count(self):
        picked = sum(1 for b in self.unpaired_buttons.values() if b.isChecked())
        color = ACCENT if picked == PHOTOS_PER_PERSON else MUTED
        self.picked_label.setText(f"선택됨: {picked} / {PHOTOS_PER_PERSON}장  (남은 사진: {len(self.unpaired_buttons)}장)")
        self.picked_label.setStyleSheet(f"color:{color}; font-size:9pt; font-weight:bold; background:transparent;")

    def commit_pair(self):
        if not self.unpaired_buttons:
            QMessageBox.warning(self, "알림", "먼저 '불러오기'로 사진들을 불러와주세요.")
            return

        picked = [fname for fname, btn in self.unpaired_buttons.items() if btn.isChecked()]
        if len(picked) != PHOTOS_PER_PERSON:
            QMessageBox.warning(self, "알림", f"정확히 {PHOTOS_PER_PERSON}장을 선택해주세요. (지금 {len(picked)}장 선택됨)")
            return

        name, ok = QInputDialog.getText(self, "이름 입력", "이 사람 이름(또는 별명)을 입력해주세요:")
        name = (name or "").strip()
        if not ok or not name:
            return
        for ch in '\\/:*?"<>|_':
            name = name.replace(ch, "")
        if not name:
            QMessageBox.warning(self, "알림", "사용할 수 있는 문자가 없는 이름이에요. 다시 입력해주세요.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        exts = [get_ext(f) for f in picked]
        new_names = build_labeled_names(name, exts)

        try:
            for src, new_name in zip(picked, new_names):
                shutil.copy(os.path.join(self.source_dir, src), os.path.join(self.output_dir, new_name))
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일 복사 중 오류가 났어요: {e}")
            return

        self.paired_count += 1
        self.result_box.append(f"✅ {self.paired_count}. {name} → {', '.join(new_names)}")

        # 그리드에서 방금 묶은 사진들 제거
        remaining = [f for f in self.unpaired_buttons.keys() if f not in picked]
        self._rebuild_grid(remaining)
        self.status_label.setText(f"'{name}' 묶기 완료! 남은 사진: {len(remaining)}장")

        if not remaining:
            self.result_box.append("")
            self.result_box.append(f"🎉 전부 다 묶었어요! 정리된 폴더: {self.output_dir}")
            self.result_box.append("이제 '대진표 만들기'에서 소스 폴더로 이 폴더를 선택하시면 돼요.")