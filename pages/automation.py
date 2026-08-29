"""
제목/사진 자동 업로드 + 댓글 자동 수집 페이지
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QVBoxLayout, QHBoxLayout,
    QTextEdit, QMessageBox, QScrollArea, QSpinBox,
)

from theme import BG, PANEL, ACCENT, ACCENT2, TEXT, SIDEBAR_TEXT, MUTED, button_style, combo_style, result_box_style
from config import TITLE_ROUNDS, VALID_ROUNDS
from logic.common import round_label
from logic.title import load_titles_for_round
from logic.automation import DEFAULT_GROUP_SIZE, compute_num_windows, coord_items_for, window_nav_coord_items, build_vote_folder
from app_state import HAS_AUTOMATION
from position_cache import load_cache
from widgets import CoordCaptureRow
from workers import UploadWorker, CommentsCollectWorker


class TitleImageUploadPage(QWidget):
    """제목/사진 자동 업로드 페이지 - auto_title_v3.py를 마우스 좌표 캡처 + 백그라운드 자동화로 이식"""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        self.cache = load_cache()
        self.titles = None
        self.coord_rows = {}
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("📤 제목/사진 자동 업로드")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        if not HAS_AUTOMATION:
            warn = QLabel("⚠️ pyautogui / pyperclip이 설치되어 있지 않아요. 터미널에서:\npip install pyautogui pyperclip")
            warn.setStyleSheet(f"color:#b33; background:{ACCENT2}; padding:8px; border-radius:4px;")
            layout.addWidget(warn)

        desc = QLabel("브라우저 화면에서 제목 붙여넣기 + 사진 업로드를 마우스로 직접 하는 대신 자동으로 반복해줘요.\n"
                       "처음 한 번은 화면 좌표를 캡처해둬야 하고, 그 다음부턴 저장된 좌표를 계속 재사용해요.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(desc)

        # ── 1. 라운드 + 그룹사이즈 + 제목 불러오기 ──
        setting_row = QHBoxLayout()
        round_lbl = QLabel("대상 라운드:")
        round_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        setting_row.addWidget(round_lbl)

        self.round_label_map = {r: round_label(r) for r in TITLE_ROUNDS}
        self.round_label_map["prelim"] = "예선전"
        self.round_label_to_num = {v: k for k, v in self.round_label_map.items()}
        self.round_combo = QComboBox()
        self.round_combo.addItems(["예선전"] + [self.round_label_map[r] for r in TITLE_ROUNDS])
        self.round_combo.setStyleSheet(combo_style())
        setting_row.addWidget(self.round_combo)

        size_lbl = QLabel("창당 탭 개수:")
        size_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        setting_row.addWidget(size_lbl)

        self.group_size_spin = QSpinBox()
        self.group_size_spin.setRange(1, 50)
        self.group_size_spin.setValue(DEFAULT_GROUP_SIZE)
        self.group_size_spin.setStyleSheet(f"background:white; color:{TEXT}; padding:2px; border-radius:4px;")
        setting_row.addWidget(self.group_size_spin)

        load_btn = QPushButton("📄 제목 불러오기")
        load_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        load_btn.clicked.connect(self.load_titles)
        setting_row.addWidget(load_btn)
        setting_row.addStretch()
        layout.addLayout(setting_row)

        self.status_label = QLabel("라운드를 선택하고 '제목 불러오기'를 눌러주세요.")
        self.status_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.status_label)

        # ── 2. 좌표 캡처 영역 ──
        coord_header_row = QHBoxLayout()
        coord_title = QLabel("📍 화면 좌표 설정")
        coord_title.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        coord_header_row.addWidget(coord_title)

        self.capture_all_btn = QPushButton("🚀 전체 순서대로 캡처")
        self.capture_all_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        self.capture_all_btn.clicked.connect(self.start_capture_all)
        coord_header_row.addWidget(self.capture_all_btn)

        reset_all_btn = QPushButton("🗑️ 전체 좌표 리셋")
        reset_all_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        reset_all_btn.clicked.connect(self.reset_all_coords)
        coord_header_row.addWidget(reset_all_btn)
        coord_header_row.addStretch()
        layout.addLayout(coord_header_row)

        self.capture_all_status = QLabel("")
        self.capture_all_status.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.capture_all_status)

        self.coord_scroll = QScrollArea()
        self.coord_scroll.setWidgetResizable(True)
        self.coord_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.coord_container = QWidget()
        self.coord_container.setStyleSheet("background:transparent;")
        self.coord_layout = QVBoxLayout(self.coord_container)
        self.coord_layout.setContentsMargins(0, 0, 0, 0)
        self.coord_layout.setSpacing(4)
        self.coord_scroll.setWidget(self.coord_container)
        self.coord_scroll.setMinimumHeight(160)
        layout.addWidget(self.coord_scroll, 2)

        # ── 3. 시작 / 중지 ──
        run_row = QHBoxLayout()
        self.start_btn = QPushButton("▶ 자동 업로드 시작")
        self.start_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        self.start_btn.clicked.connect(self.start_upload)
        run_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        self.stop_btn.clicked.connect(self.stop_upload)
        self.stop_btn.setEnabled(False)
        run_row.addWidget(self.stop_btn)
        run_row.addStretch()
        layout.addLayout(run_row)

        safety = QLabel("⚠️ 중간에 멈추려면 마우스를 화면 맨 왼쪽 위 모서리로 빠르게 이동하세요 (안전장치).")
        safety.setStyleSheet(f"color:{MUTED}; font-size:8pt; background:transparent;")
        layout.addWidget(safety)

        # ── 4. 로그 ──
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        self.result_box.setPlainText("여기에 진행 상황이 표시됩니다.")
        layout.addWidget(self.result_box, 1)

        self.rebuild_coord_rows()

    # ------------------------------------------------------------

    def current_round(self):
        return self.round_label_to_num[self.round_combo.currentText()]

    def load_titles(self):
        round_num = self.current_round()
        titles, path = load_titles_for_round(round_num)
        if titles is None:
            self.status_label.setText(f"❌ 제목 파일을 찾을 수 없어요: {path}\n먼저 '제목 생성' 메뉴에서 만들어주세요.")
            self.titles = None
            return

        self.titles = titles
        num_windows = compute_num_windows(len(titles), self.group_size_spin.value())
        self.status_label.setText(
            f"✅ {len(titles)}개 제목을 불러왔어요. 창 {num_windows}개가 필요해요 "
            f"(창당 최대 {self.group_size_spin.value()}개)."
        )
        self.rebuild_coord_rows()

    def rebuild_coord_rows(self):
        while self.coord_layout.count():
            item = self.coord_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.coord_rows = {}

        total = len(self.titles) if self.titles else 1
        num_windows = compute_num_windows(total, self.group_size_spin.value())
        self.current_num_windows = num_windows

        for key, desc in coord_items_for(num_windows):
            row = CoordCaptureRow(key, desc, self.cache)
            self.coord_layout.addWidget(row)
            self.coord_rows[key] = row
        self.coord_layout.addStretch()

    def reset_all_coords(self):
        if not self.coord_rows:
            return
        reply = QMessageBox.question(
            self, "확인", f"지금 보이는 좌표 {len(self.coord_rows)}개를 전부 (0, 0)으로 리셋할까요?"
        )
        if reply != QMessageBox.Yes:
            return
        for row in self.coord_rows.values():
            row.reset_value()

    def start_capture_all(self):
        """좌표 항목들을 순서대로 하나씩: '2초 안에 마우스 옮기세요' 안내 → 3초 캡처 → 다음 항목, 반복"""
        if not HAS_AUTOMATION:
            QMessageBox.warning(self, "알림", "pyautogui가 설치되어 있지 않아요.\n터미널에서 'pip install pyautogui pyperclip' 실행해주세요.")
            return
        if not self.coord_rows:
            QMessageBox.warning(self, "알림", "먼저 '제목 불러오기'로 필요한 좌표 목록을 만들어주세요.")
            return

        self.capture_all_btn.setEnabled(False)
        # 창 미리보기 썸네일은 브레이브 아이콘에 마우스를 올려야만 잠깐 보이는 팝업이라
        # 자동 순서 진행(대기 후 캡처)이랑 궁합이 안 좋아서, 전체 순서 캡처에서는 제외하고
        # 각자 '3초 후 캡처' 버튼으로 개별 캡처하도록 함.
        self._capture_queue = [row for row in self.coord_rows.values() if not row.cache_key.startswith("thumb_")]
        self._capture_total = len(self._capture_queue)
        self._process_next_capture()

    def _process_next_capture(self):
        for row in self.coord_rows.values():
            row.set_highlight(False)

        if not self._capture_queue:
            self.capture_all_status.setText("🎉 전체 좌표 캡처가 끝났어요!")
            self.capture_all_btn.setEnabled(True)
            return

        row = self._capture_queue.pop(0)
        done_count = self._capture_total - len(self._capture_queue)
        row.set_highlight(True)
        self.coord_scroll.ensureWidgetVisible(row)
        self.capture_all_status.setText(
            f"👉 ({done_count}/{self._capture_total}) {row.desc} — 마우스를 그 위치로 옮겨주세요! 2초 후 캡처 시작됩니다."
        )
        QTimer.singleShot(2000, lambda r=row: self._trigger_row_capture(r))

    def _trigger_row_capture(self, row):
        def on_done():
            row.captured.disconnect(on_done)
            QTimer.singleShot(300, self._process_next_capture)

        row.captured.connect(on_done)
        row.start_capture()

    def start_upload(self):
        if not HAS_AUTOMATION:
            QMessageBox.warning(self, "알림", "pyautogui / pyperclip이 설치되어 있지 않아요.")
            return
        if not self.titles:
            QMessageBox.warning(self, "알림", "먼저 '제목 불러오기'를 눌러주세요.")
            return

        missing = [desc for key, desc in coord_items_for(self.current_num_windows)
                   if self.coord_rows[key].get_value() is None]
        if missing:
            QMessageBox.warning(self, "알림", "아직 캡처 안 된 좌표가 있어요:\n" + "\n".join(missing))
            return

        round_num = self.current_round()
        reply = QMessageBox.question(
            self, "확인",
            f"{len(self.titles)}개 제목을 자동으로 붙여넣을게요.\n"
            f"1번째 창의 1번째 탭에 미리 포커스를 맞춰두셨나요? 5초 후 시작합니다."
        )
        if reply != QMessageBox.Yes:
            return

        coords = {key: self.coord_rows[key].get_value() for key in self.coord_rows}
        group_size = self.group_size_spin.value()

        self.result_box.setPlainText("5초 후 시작합니다... (지금 브라우저 1번째 탭 본문을 클릭해두세요!)")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        QTimer.singleShot(5000, lambda: self._launch_worker(round_num, group_size, coords))

    def _launch_worker(self, round_num, group_size, coords):
        self.worker = UploadWorker(self.titles, round_num, group_size, coords, self.current_num_windows)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text):
        self.result_box.append(text)

    def on_finished(self, success):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def stop_upload(self):
        if self.worker:
            self.worker.stop()


class CommentsCollectPage(QWidget):
    """댓글 자동 수집 페이지 - auto_comments.py를 좌표 캡처 + 백그라운드 자동화로 이식"""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        self.cache = load_cache()
        self.coord_rows = {}
        self.worker = None
        self.vote_folder = None
        self.total = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("💬 댓글 자동 수집")
        title.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:bold; background:transparent;")
        layout.addWidget(title)

        if not HAS_AUTOMATION:
            warn = QLabel("⚠️ pyautogui / pyperclip이 설치되어 있지 않아요. 터미널에서:\npip install pyautogui pyperclip")
            warn.setStyleSheet(f"color:#b33; background:{ACCENT2}; padding:8px; border-radius:4px;")
            layout.addWidget(warn)

        desc = QLabel("각 조 게시글 탭에서 전체선택(Ctrl+A) → 복사(Ctrl+C) → N조.txt 저장을 순서대로 반복해요.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(desc)

        # ── 1. 라운드 + 그룹사이즈 ──
        setting_row = QHBoxLayout()
        round_lbl = QLabel("대상 라운드:")
        round_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        setting_row.addWidget(round_lbl)

        self.round_label_map = {r: round_label(r) for r in VALID_ROUNDS}
        self.round_label_map["prelim"] = "예선전"
        self.round_label_to_num = {v: k for k, v in self.round_label_map.items()}
        self.round_combo = QComboBox()
        self.round_combo.addItems(["예선전"] + [self.round_label_map[r] for r in VALID_ROUNDS])
        self.round_combo.setStyleSheet(combo_style())
        setting_row.addWidget(self.round_combo)

        size_lbl = QLabel("창당 탭 개수:")
        size_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        setting_row.addWidget(size_lbl)

        self.group_size_spin = QSpinBox()
        self.group_size_spin.setRange(1, 50)
        self.group_size_spin.setValue(DEFAULT_GROUP_SIZE)
        self.group_size_spin.setStyleSheet(f"background:white; color:{TEXT}; padding:2px; border-radius:4px;")
        setting_row.addWidget(self.group_size_spin)

        prep_btn = QPushButton("🔍 확인하기")
        prep_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        prep_btn.clicked.connect(self.prepare)
        setting_row.addWidget(prep_btn)
        setting_row.addStretch()
        layout.addLayout(setting_row)

        self.status_label = QLabel("라운드를 선택하고 '확인하기'를 눌러주세요.")
        self.status_label.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.status_label)

        # ── 2. 좌표 캡처 영역 (아이콘 + 창별 썸네일만 필요) ──
        coord_header_row = QHBoxLayout()
        coord_title = QLabel("📍 화면 좌표 설정")
        coord_title.setStyleSheet(f"color:{TEXT}; font-weight:bold; background:transparent;")
        coord_header_row.addWidget(coord_title)

        self.capture_all_btn = QPushButton("🚀 전체 순서대로 캡처")
        self.capture_all_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        self.capture_all_btn.clicked.connect(self.start_capture_all)
        coord_header_row.addWidget(self.capture_all_btn)

        reset_all_btn = QPushButton("🗑️ 전체 좌표 리셋")
        reset_all_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        reset_all_btn.clicked.connect(self.reset_all_coords)
        coord_header_row.addWidget(reset_all_btn)
        coord_header_row.addStretch()
        layout.addLayout(coord_header_row)

        self.capture_all_status = QLabel("")
        self.capture_all_status.setStyleSheet(f"color:{MUTED}; font-size:9pt; background:transparent;")
        layout.addWidget(self.capture_all_status)

        self.coord_scroll = QScrollArea()
        self.coord_scroll.setWidgetResizable(True)
        self.coord_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.coord_container = QWidget()
        self.coord_container.setStyleSheet("background:transparent;")
        self.coord_layout = QVBoxLayout(self.coord_container)
        self.coord_layout.setContentsMargins(0, 0, 0, 0)
        self.coord_layout.setSpacing(4)
        self.coord_scroll.setWidget(self.coord_container)
        self.coord_scroll.setMinimumHeight(160)
        layout.addWidget(self.coord_scroll, 2)

        # ── 3. 시작 / 중지 ──
        run_row = QHBoxLayout()
        self.start_btn = QPushButton("▶ 자동 수집 시작")
        self.start_btn.setStyleSheet(button_style(ACCENT, ACCENT2, bold=True))
        self.start_btn.clicked.connect(self.start_collect)
        run_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setStyleSheet(button_style(PANEL, SIDEBAR_TEXT))
        self.stop_btn.clicked.connect(self.stop_collect)
        self.stop_btn.setEnabled(False)
        run_row.addWidget(self.stop_btn)
        run_row.addStretch()
        layout.addLayout(run_row)

        safety = QLabel("⚠️ 중간에 멈추려면 마우스를 화면 맨 왼쪽 위 모서리로 빠르게 이동하세요 (안전장치).\n"
                         "⚠️ 각 탭에서 댓글창(페이지 본문)에 클릭해서 포커스가 가 있어야 Ctrl+A가 먹혀요.")
        safety.setStyleSheet(f"color:{MUTED}; font-size:8pt; background:transparent;")
        layout.addWidget(safety)

        # ── 4. 로그 ──
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(result_box_style())
        self.result_box.setPlainText("여기에 진행 상황이 표시됩니다.")
        layout.addWidget(self.result_box, 1)

        self.current_num_windows = 1
        self.rebuild_coord_rows()

    # ------------------------------------------------------------

    def current_round(self):
        return self.round_label_to_num[self.round_combo.currentText()]

    def prepare(self):
        round_num = self.current_round()
        self.vote_folder, group_count = build_vote_folder(round_num)
        self.total = group_count
        num_windows = compute_num_windows(self.total, self.group_size_spin.value())
        self.current_num_windows = num_windows
        round_display = "예선전" if round_num == "prelim" else f"{round_label(round_num)}"
        self.status_label.setText(
            f"✅ {round_display} = {self.total}개 조(탭) / 창 {num_windows}개 필요해요 "
            f"(창당 최대 {self.group_size_spin.value()}개)\n📁 저장 위치: {self.vote_folder}"
        )
        self.rebuild_coord_rows()

    def rebuild_coord_rows(self):
        while self.coord_layout.count():
            item = self.coord_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.coord_rows = {}

        num_windows = getattr(self, "current_num_windows", 1)
        for key, desc in window_nav_coord_items(num_windows):
            row = CoordCaptureRow(key, desc, self.cache)
            self.coord_layout.addWidget(row)
            self.coord_rows[key] = row
        self.coord_layout.addStretch()

    def reset_all_coords(self):
        if not self.coord_rows:
            return
        reply = QMessageBox.question(
            self, "확인", f"지금 보이는 좌표 {len(self.coord_rows)}개를 전부 (0, 0)으로 리셋할까요?"
        )
        if reply != QMessageBox.Yes:
            return
        for row in self.coord_rows.values():
            row.reset_value()

    def start_capture_all(self):
        if not HAS_AUTOMATION:
            QMessageBox.warning(self, "알림", "pyautogui가 설치되어 있지 않아요.\n터미널에서 'pip install pyautogui pyperclip' 실행해주세요.")
            return
        if not self.coord_rows:
            QMessageBox.warning(self, "알림", "먼저 '확인하기'로 필요한 좌표 목록을 만들어주세요.")
            return

        self.capture_all_btn.setEnabled(False)
        self._capture_queue = [row for row in self.coord_rows.values() if not row.cache_key.startswith("thumb_")]
        self._capture_total = len(self._capture_queue)
        self._process_next_capture()

    def _process_next_capture(self):
        for row in self.coord_rows.values():
            row.set_highlight(False)

        if not self._capture_queue:
            self.capture_all_status.setText("🎉 전체 좌표 캡처가 끝났어요!")
            self.capture_all_btn.setEnabled(True)
            return

        row = self._capture_queue.pop(0)
        done_count = self._capture_total - len(self._capture_queue)
        row.set_highlight(True)
        self.coord_scroll.ensureWidgetVisible(row)
        self.capture_all_status.setText(
            f"👉 ({done_count}/{self._capture_total}) {row.desc} — 마우스를 그 위치로 옮겨주세요! 2초 후 캡처 시작됩니다."
        )
        QTimer.singleShot(2000, lambda r=row: self._trigger_row_capture(r))

    def _trigger_row_capture(self, row):
        def on_done():
            row.captured.disconnect(on_done)
            QTimer.singleShot(300, self._process_next_capture)

        row.captured.connect(on_done)
        row.start_capture()

    def start_collect(self):
        if not HAS_AUTOMATION:
            QMessageBox.warning(self, "알림", "pyautogui / pyperclip이 설치되어 있지 않아요.")
            return
        if not self.vote_folder or not self.total:
            QMessageBox.warning(self, "알림", "먼저 '확인하기'를 눌러주세요.")
            return

        missing = [desc for key, desc in window_nav_coord_items(self.current_num_windows)
                   if self.coord_rows[key].get_value() is None]
        if missing:
            QMessageBox.warning(self, "알림", "아직 캡처 안 된 좌표가 있어요:\n" + "\n".join(missing))
            return

        reply = QMessageBox.question(
            self, "확인",
            f"{self.total}개 조 댓글을 순서대로 복사해서 저장할게요.\n"
            f"1번째 창의 1번째 탭 본문을 미리 클릭해두셨나요? 5초 후 시작합니다."
        )
        if reply != QMessageBox.Yes:
            return

        coords = {key: self.coord_rows[key].get_value() for key in self.coord_rows}
        group_size = self.group_size_spin.value()

        self.result_box.setPlainText("5초 후 시작합니다... (지금 브라우저 1번째 탭 본문 클릭!)")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        QTimer.singleShot(5000, lambda: self._launch_worker(coords, group_size))

    def _launch_worker(self, coords, group_size):
        self.worker = CommentsCollectWorker(self.vote_folder, self.total, group_size, coords, self.current_num_windows)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text):
        self.result_box.append(text)

    def on_finished(self, success):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def stop_collect(self):
        if self.worker:
            self.worker.stop()
