"""
앱 전역에서 공유하는 작은 상태들
====================================
- pyautogui / pyperclip: 마우스/키보드 자동화 라이브러리. 설치 안 되어 있어도
  나머지 기능(대진표, 제목생성, 투표집계 등)은 그대로 동작해야 하므로 감싸서 처리.
- _floating_windows: '별도 창으로 열기' 기능으로 띄운 창들을 붙잡아두는 목록.
  파이썬 참조가 없으면 창이 바로 닫혀버려서 필요함 (VoteCountPage, 뷰어 창 등에서 공용으로 씀).
"""

try:
    import pyautogui
    import pyperclip
    HAS_AUTOMATION = True
except Exception:
    pyautogui = None
    pyperclip = None
    HAS_AUTOMATION = False

_floating_windows = []
