"""
월드컵 매니저 (PySide6 버전) - 진입점
====================================
실제 기능들은 각자 모듈로 나뉘어 있음:
    theme.py        - 색상/스타일
    app_state.py    - 자동화 라이브러리 감지, 전역 공유 상태
    logic/          - 순수 로직 (파일/폴더 조작, 계산) - Qt에 의존 안 함
    workers.py      - 백그라운드 자동화 스레드
    widgets.py      - 여러 페이지가 공용으로 쓰는 다이얼로그/버튼
    pages/          - 사이드바 메뉴 각각에 대응하는 화면
    config.py       - 사용자 설정값 (BASE_DIR, 라벨 등)
    position_cache.py - 마우스 좌표 캐시

설치 (한 번만):
    pip install PySide6 Pillow pyautogui pyperclip
실행:
    python main_app.py
"""

import os
import sys

# 윈도우에서 "SetProcessDpiAwarensesContext() failed" 경고가 뜨는 걸 조용히 시킴.
# (Qt가 더 정밀한 DPI 인식으로 재설정하려다 파이썬이 이미 정해둔 값이랑 충돌해서 뜨는 정보성 경고일 뿐,
#  실제 화면 표시나 동작에는 영향 없음 - 그냥 로그만 안 보이게 끔)
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget,
)

from theme import BG, PANEL, SIDEBAR_TEXT, nav_button_style
from pages.settings import SettingsPage
from pages.title_gen import TitleGenPage
from pages.tournament import TournamentPage
from pages.photo_pairing import PhotoPairingPage
from pages.prelim import PrelimPage
from pages.automation import TitleImageUploadPage, CommentsCollectPage
from pages.vote_count import VoteCountPage
from pages.placeholder import PlaceholderPage


class MainWindow(QMainWindow):
    MENU_ITEMS = [
        ("⚙️", "설정", "settings", "작업 폴더 / 대회명 / 라벨 등을 여기서 입력하고 저장"),
        ("📝", "제목 생성", "title", "title.txt 읽어서 라운드별 제목 파일 자동 생성"),
        ("🏆", "대진표 만들기", "tournament", "원본 사진 셔플 → 조 편성, 승자 입력 → 다음 라운드 진행"),
        ("🔗", "사진 짝짓기", "photo_pairing", "이름 규칙 없는 사진들을 클릭클릭으로 묶어서 자동 정리 (1인당 여러 장일 때)"),
        ("🎯", "예선전 대진표", "prelim", "참가자 수가 딱 안 맞을 때(예: 100명 → 64강) 부전승+예선전으로 맞춤"),
        ("📤", "제목/사진 자동 업로드", "auto_title", "브라우저에서 제목+이미지 자동으로 붙여넣기 (좌표 자동화)"),
        ("💬", "댓글 자동 수집", "auto_comments", "각 조 게시글 댓글 전체 복사해서 파일로 저장 (좌표 자동화)"),
        ("📊", "투표 집계", "count", "저장된 댓글에서 득표수 세고 승자 판정"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("월드컵 매니저 (예시)")
        self.resize(880, 900)
        self.setMinimumSize(600, 650)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 사이드바 ──
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background:{PANEL};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(2)

        logo = QLabel("🎪 월드컵 매니저")
        logo.setStyleSheet(f"color:{SIDEBAR_TEXT}; font-size:14px; font-weight:bold; background:transparent;")
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(14)

        self.nav_buttons = {}
        for emoji, name, key, _ in self.MENU_ITEMS:
            btn = QPushButton(f"  {emoji}  {name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self.show_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        sidebar_layout.addStretch()
        root_layout.addWidget(sidebar)

        # ── 컨텐츠 영역 ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{BG};")
        root_layout.addWidget(self.stack, 1)

        self.pages = {}  # key -> 이미 만들어둔 페이지 인스턴스 (재방문 시 상태 유지하려고 재사용함)
        self.show_page("settings")

    def show_page(self, key):
        for k, btn in self.nav_buttons.items():
            btn.setStyleSheet(nav_button_style(selected=(k == key)))

        if key not in self.pages:
            if key == "count":
                page = VoteCountPage()
            elif key == "title":
                page = TitleGenPage()
            elif key == "settings":
                page = SettingsPage(self)
            elif key == "tournament":
                page = TournamentPage()
            elif key == "photo_pairing":
                page = PhotoPairingPage()
            elif key == "prelim":
                page = PrelimPage()
            elif key == "auto_title":
                page = TitleImageUploadPage()
            elif key == "auto_comments":
                page = CommentsCollectPage()
            else:
                emoji, name, _, desc = next(m for m in self.MENU_ITEMS if m[2] == key)
                page = PlaceholderPage(emoji, name, desc)

            self.pages[key] = page
            self.stack.addWidget(page)

        self.stack.setCurrentWidget(self.pages[key])
        self.current_page = self.pages[key]

    def restart_app(self):
        """설정 저장 후 새 설정으로 앱을 통째로 다시 시작함"""
        os.execl(sys.executable, sys.executable, *sys.argv)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())