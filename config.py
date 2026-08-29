import os
import sys
import json

# =============================================
#  전역 설정
#  ⚠️ 이제 여기 직접 안 고쳐도 돼요!
#     GUI의 '⚙️ 설정' 메뉴에서 입력하면 settings.json에 저장되고,
#     여기서는 그 파일이 있으면 우선적으로 읽어옵니다.
#     settings.json이 없으면 아래 기본값을 씁니다.
# =============================================


def _app_dir():
    """settings.json을 저장할 기준 폴더.
    exe로 패키징된 상태(PyInstaller)면 실행파일이 있는 폴더를 씀 -
    __file__ 기준으로 하면 실행할 때마다 풀렸다 사라지는 임시 폴더를 가리켜서 설정이 매번 초기화됨.
    일반 파이썬 실행(.py)일 때는 원래대로 이 파일이 있는 폴더를 씀."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


_SETTINGS_PATH = os.path.join(_app_dir(), "settings.json")

_DEFAULTS = {
    "BASE_DIR": r"C:\WorldCup\예시월드컵",
    "TOURNA_NAME": "예시월드컵",
    "LABEL_A": "1가",
    "LABEL_B": "2나",
    # 댓글 목록에서 "번호. 이 표시문구 날짜..." 형태로 작성자를 표시하는 사이트의 그 표시문구.
    # 사이트마다 다르므로(예: '무명의 OOO' 등) 직접 확인해서 설정 페이지에 입력해야 함.
    "COMMENT_AUTHOR_LABEL": "익명의 사용자",
    # 답글로 투표한 걸 표시할 때 쓰는 태그 (예: '=113번' 처럼 번호 뒤에 붙는 문구). 사이트마다 다름.
    "REPLY_TAG": "님",
    # 참가자 1명당 사진 몇 장을 같이 묶어서 다룰지 (1~4). 1이면 기존이랑 완전히 동일하게 동작함.
    "PHOTOS_PER_PERSON": 1,
}


def _load_settings():
    if os.path.exists(_SETTINGS_PATH):
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(_DEFAULTS)
            merged.update({k: v for k, v in data.items() if v})
            if merged.get("BASE_DIR"):
                merged["BASE_DIR"] = os.path.normpath(merged["BASE_DIR"])
            return merged
        except Exception:
            return dict(_DEFAULTS)
    return dict(_DEFAULTS)


def save_settings(new_values: dict):
    """GUI의 '설정' 페이지에서 호출. 기존 값과 합쳐서 settings.json에 저장함.
    BASE_DIR는 '/'와 '\\'가 섞이면 나중에 파일 경로 관련 오류가 나므로 항상 정규화해서 저장함."""
    current = _load_settings()
    if new_values.get("BASE_DIR"):
        new_values = dict(new_values)
        new_values["BASE_DIR"] = os.path.normpath(new_values["BASE_DIR"])
    current.update(new_values)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current


def get_current_settings():
    """GUI에서 현재 값들을 입력칸에 미리 채워 넣을 때 씀."""
    return _load_settings()


_settings = _load_settings()

# 대회 폴더가 들어있는 최상위 경로
BASE_DIR = _settings["BASE_DIR"]

# 대회 이름 (폴더 이름에 그대로 사용됨: 예 '테스트컵' -> 테스트컵_128강)
TOURNA_NAME = _settings["TOURNA_NAME"]

# 투표 라벨 (파일명용, 숫자 접두사 포함) / 투표 집계용 후보 이름은 자동으로 숫자만 뗌
LABEL_A = _settings["LABEL_A"]
LABEL_B = _settings["LABEL_B"]
CANDIDATE_A = LABEL_A[1:] if LABEL_A else ""   # 예: '가'
CANDIDATE_B = LABEL_B[1:] if LABEL_B else ""   # 예: '나'

# 댓글 목록에서 작성자를 표시하는 문구 (사이트마다 다름, 설정 페이지에서 직접 입력)
COMMENT_AUTHOR_LABEL = _settings["COMMENT_AUTHOR_LABEL"]
REPLY_TAG = _settings["REPLY_TAG"]

# 참가자 1명당 사진 몇 장인지 (1~4). 1이면 예전이랑 완전히 동일한 동작.
try:
    PHOTOS_PER_PERSON = max(1, min(4, int(_settings.get("PHOTOS_PER_PERSON", 1))))
except (TypeError, ValueError):
    PHOTOS_PER_PERSON = 1

# 대회 시작 시 사용할, 라운드 번호가 붙지 않은 원본 사진 전체 폴더
# (몇 강으로 시작하든 이 폴더를 기본 소스로 씀)
ALL_PHOTOS_DIR_NAME = f"{TOURNA_NAME}(전체)"

# 제목 원본 파일 이름(확장자 제외) / 생성될 결과 파일 접두사
TITLE_FILE_NAME = f"{TOURNA_NAME}_title"
OUTPUT_FILE_PREFIX = f"{TITLE_FILE_NAME}"

# 대진표 스크립트가 다루는 전체 라운드 (4강/2강 포함)
VALID_ROUNDS = [128, 64, 32, 16, 8, 4, 2]

# 제목생성 스크립트가 다루는 라운드 (4강 = 준결승전, 2강 = 결승전/3,4위전 까지 포함)
TITLE_ROUNDS = [128, 64, 32, 16, 8, 4, 2]

# 2강만 폴더 이름을 "N강" 대신 이걸로 표시 (결승전 + 3,4위전이라 "2강"이 안 맞아서)
FINAL_ROUND_LABEL = "결승·3,4위"


# =============================================
#  폴더 경로 헬퍼 (5개 스크립트 전부 이걸로 통일)
#  구조: BASE_DIR / {TOURNA_NAME}_{강}강 / (전체 | 본선 | 썸네일)
# =============================================

def get_round_label(round_size):
    """폴더/파일명에 쓸 라운드 표기: 2강만 특별 라벨, 나머지는 'N강'"""
    if round_size == 2:
        return FINAL_ROUND_LABEL
    return f"{round_size}강"


def get_round_dir(round_size):
    """해당 라운드의 상위 폴더"""
    return os.path.join(BASE_DIR, f"{TOURNA_NAME}_{get_round_label(round_size)}")


def get_whole_dir(round_size):
    """'전체' 폴더 (승자 전원이 원본 파일명으로 백업되는 곳)"""
    label = get_round_label(round_size)
    return os.path.join(get_round_dir(round_size), f"{TOURNA_NAME}_{label}(전체)")


def get_bonsun_dir(round_size):
    """'본선' 폴더 (조 편성 + 라벨링된 대진표가 저장되는 곳)"""
    label = get_round_label(round_size)
    return os.path.join(get_round_dir(round_size), f"{TOURNA_NAME}_{label}(본선)")


def get_thumbnail_dir(round_size):
    """썸네일 저장 폴더"""
    label = get_round_label(round_size)
    return os.path.join(get_round_dir(round_size), f"{TOURNA_NAME}_{label}(썸네일)")


def get_all_photos_dir():
    """대회 시작용 원본 사진 전체 폴더 (라운드 번호 없음, 예: 테스트컵(전체))"""
    return os.path.join(BASE_DIR, ALL_PHOTOS_DIR_NAME)


def get_vote_base_dir():
    """투표 집계용 최상위 폴더 (그 안에 '{강}강_{조}조' 형태 하위 폴더들이 생김)"""
    return os.path.join(BASE_DIR, f"{TOURNA_NAME}(투표집계)")