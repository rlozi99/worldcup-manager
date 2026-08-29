"""
제목/사진 자동 업로드 + 댓글 자동 수집 - 공통 로직 (auto_title_v3.py / auto_comments.py 이식)
"""

import os
import math
import time

from config import get_vote_base_dir
from logic.prelim import count_prelim_matches
from app_state import pyautogui, pyperclip

DEFAULT_GROUP_SIZE = 10
MAX_DIALOG_LENGTH = 260

AFTER_PASTE_DELAY = 0.3
AFTER_TAB_SWITCH_DELAY = 0.5
AFTER_WINDOW_SWITCH_DELAY = 1.0
AFTER_UPLOAD_BUTTON_DELAY = 1.0
AFTER_UPLOAD_CONFIRM_DELAY = 1.0

AFTER_SELECT_ALL_DELAY = 0.3
AFTER_COPY_DELAY = 0.3
COMMENTS_AFTER_TAB_SWITCH_DELAY = 1.0
COMMENTS_AFTER_WINDOW_SWITCH_DELAY = 1.5

# 좌표 캡처가 필요한 항목들 (순서대로). "동적"인 썸네일 좌표는 따로 계산해서 앞에 붙임.
FIXED_COORD_ITEMS = [
    ("title_field", "제목 입력창 위치"),
    ("align_center", "가운데 정렬 버튼 위치"),
    ("upload_button", "'사진 업로드' 버튼 위치"),
    ("filename_field", "파일 열기 창의 '파일 이름' 입력창 위치"),
]


def build_dialog_path_string(paths):
    """윈도우 '파일 이름' 입력창에 넣을 문자열: "경로1" "경로2" 형태로 조합
    경로에 '/'와 '\\'가 섞여 있으면 윈도우 파일 열기 창이 '파일 이름이 올바르지 않습니다' 오류를 내므로
    normpath로 항상 OS에 맞는 구분자로 통일해서 넣음."""
    return " ".join(f'"{os.path.normpath(p)}"' for p in paths if p)


def compute_num_windows(total, group_size):
    return math.ceil(total / group_size) if group_size > 0 else 1


def window_nav_coord_items(num_windows):
    """창/탭 이동에 필요한 좌표: 브레이브 아이콘 + 창별 미리보기 썸네일. 자동 업로드/댓글 수집 둘 다 씀.
    1번째 창은 시작 전에 이미 사용자가 클릭해서 포커스를 맞춰두기 때문에 썸네일 좌표가 필요 없어서 2번째 창부터 넣음."""
    items = [("brave_icon", "브레이브 작업표시줄 아이콘 위치")]
    for w in range(2, num_windows + 1):
        items.append((f"thumb_{num_windows}win_{w}", f"{w}번째 창 미리보기 썸네일 위치"))
    return items


def coord_items_for(num_windows):
    """제목/사진 자동 업로드에 필요한 좌표 항목 전체 목록: 창 이동용 + 업로드 관련 4개"""
    return window_nav_coord_items(num_windows) + FIXED_COORD_ITEMS


def upload_paths_recursive(paths, upload_button_pos, filename_field_pos):
    """paths를 한 번에 올리되, 다이얼로그 문자열이 너무 길면 반으로 나눠서 재귀 처리"""
    dialog_path_str = build_dialog_path_string(paths)

    if len(dialog_path_str) > MAX_DIALOG_LENGTH and len(paths) > 1:
        mid = len(paths) // 2
        upload_paths_recursive(paths[:mid], upload_button_pos, filename_field_pos)
        upload_paths_recursive(paths[mid:], upload_button_pos, filename_field_pos)
        return

    pyautogui.click(*upload_button_pos)
    time.sleep(AFTER_UPLOAD_BUTTON_DELAY)

    pyperclip.copy(dialog_path_str)
    pyautogui.click(*filename_field_pos)
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")
    time.sleep(AFTER_UPLOAD_CONFIRM_DELAY)


def build_vote_folder(round_num):
    """이 라운드의 댓글을 저장할 폴더 경로와, 몇 개 탭(조)을 돌아야 하는지 계산.
    round_num == "prelim"이면 실제로 만들어진 예선전 매치 개수를 세어서 씀 (고정 아님)."""
    if round_num == "prelim":
        group_count = count_prelim_matches()
        folder = os.path.join(get_vote_base_dir(), f"예선전_{group_count}조")
        return folder, group_count
    group_count = round_num // 2
    folder = os.path.join(get_vote_base_dir(), f"{round_num}강_{group_count}조")
    return folder, group_count
