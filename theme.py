"""
컬러 팔레트 + 공용 스타일시트 헬퍼
====================================
앱 전체에서 쓰는 색상 상수와, 버튼/드롭다운/결과창 등에 반복해서 쓰이는
Qt 스타일시트 문자열을 만들어주는 함수들을 모아둠.
"""

# =============================================
#  컬러 팔레트: Old Copper / Butter Yellow / Nebula / Seashell
# =============================================
BG = "#FAE9B7"            # 메인 배경
PANEL = "#BEE1D8"         # 사이드바 배경
ACCENT = "#6E9BA0"        # 선택된 메뉴 / 강조 버튼 배경
ACCENT2 = "#F9EDDC"       # 결과창 배경 등 보조 강조색
TEXT = "#7C5337"          # 밝은 배경 위 기본 글자색
SIDEBAR_TEXT = "#7C5337"  # 사이드바 위 글자색
MUTED = "#A0876E"         # 흐린 안내 문구용


def button_style(bg, fg, bold=False):
    weight = "bold" if bold else "normal"
    return f"""
        QPushButton {{
            background:{bg}; color:{fg}; border:none; border-radius:6px;
            padding:6px 14px; font-weight:{weight}; font-size:10pt;
        }}
        QPushButton:disabled {{ background:#dddddd; color:#999999; }}
    """


def nav_button_style(selected):
    bg = ACCENT if selected else PANEL
    fg = ACCENT2 if selected else SIDEBAR_TEXT
    return f"""
        QPushButton {{
            background:{bg}; color:{fg}; border:none; text-align:left;
            padding:10px 10px; border-radius:6px; font-size:11pt;
        }}
        QPushButton:hover {{ background:{ACCENT}; color:{ACCENT2}; }}
    """


def combo_style():
    return f"""
        QComboBox {{
            background:white; color:{TEXT}; padding:4px 8px; border-radius:4px;
            min-width:170px; font-size:10pt;
        }}
    """


def result_box_style():
    return f"""
        QTextEdit {{
            background:{ACCENT2}; color:{TEXT}; border:none; border-radius:4px;
            font-family:Consolas; font-size:10pt; padding:8px;
        }}
    """
