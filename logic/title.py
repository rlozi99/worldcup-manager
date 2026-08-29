"""
제목 생성 로직 (title_maker_v2.py 이식) - 일반 라운드 + 예선전(매치 개수가 그때그때 다름)
"""

import os

from config import TITLE_ROUNDS, TOURNA_NAME, OUTPUT_FILE_PREFIX, get_round_dir
from logic.common import round_label
from logic.prelim import get_prelim_round_dir, count_prelim_matches


def build_title_lines(title_text, round_num):
    """해당 라운드에 들어갈 제목 줄 목록을 만듦"""
    if round_num == 2:
        return [f"{title_text} - 3,4위전", f"{title_text} - 결승전"]
    elif round_num == 4:
        group_count = round_num // 2
        return [f"{title_text} - 준결승전 {i}조" for i in range(1, group_count + 1)]
    else:
        group_count = round_num // 2
        return [f"{title_text} - {round_num}강 {i}조" for i in range(1, group_count + 1)]


def build_title_plan(title_text, start_round):
    """실제 생성 전에, 어떤 폴더/파일이 만들어질지 계획만 세움.
    폴더/파일 이름은 항상 설정의 대회명(TOURNA_NAME) 기준 - load_titles_for_round가 읽는 위치와
    정확히 일치해야 대진표 만들기/자동 업로드 등 다른 기능들이 이 제목을 제대로 찾아 쓸 수 있음.
    반환: [(round_num, folder_path, file_path, lines), ...]"""
    target_rounds = [r for r in TITLE_ROUNDS if r <= start_round]
    plan = []
    for round_num in target_rounds:
        lines = build_title_lines(title_text, round_num)
        folder_path = get_round_dir(round_num)
        file_path = os.path.join(folder_path, f"{OUTPUT_FILE_PREFIX}({round_num}).txt")
        plan.append((round_num, folder_path, file_path, lines))
    return plan


def build_prelim_title_plan(title_text):
    """예선전 제목 계획. 매치 개수가 고정이 아니라 그때그때 실제로 만들어진 예선전 폴더를 세어서 정함.
    반환: (match_count, folder_path, file_path, lines) / 예선전 대진표가 아직 없으면 match_count=0"""
    match_count = count_prelim_matches()
    lines = [f"{title_text} - 예선전 {i}조" for i in range(1, match_count + 1)]
    folder_path = get_prelim_round_dir()
    file_path = os.path.join(folder_path, f"{TOURNA_NAME}_title(예선전).txt")
    return match_count, folder_path, file_path, lines


def load_titles_for_round(round_num):
    """제목생성 메뉴에서 만든 title(N).txt 파일을 읽어옴 (없으면 None).
    round_num == "prelim"이면 예선전 제목 파일을 읽음 (개수가 고정이 아니라 그때그때 다름)."""
    if round_num == "prelim":
        title_path = os.path.join(get_prelim_round_dir(), f"{TOURNA_NAME}_title(예선전).txt")
    else:
        title_path = os.path.join(get_round_dir(round_num), f"{OUTPUT_FILE_PREFIX}({round_num}).txt")
    if not os.path.exists(title_path):
        return None, title_path
    with open(title_path, "r", encoding="utf-8") as f:
        titles = [line.strip() for line in f.read().split("\n\n") if line.strip()]
    return titles, title_path