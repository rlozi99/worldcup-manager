"""
대진표 만들기 로직 (tournament_maker_v3.py 이식) + 라운드 이미지 찾기 + 썸네일 생성

⚠️ PHOTOS_PER_PERSON(1인당 사진 장수) 지원:
   매치(match)와 조편성 데이터는 이제 항상 '리스트' 기반(files_a/paths_a 등)으로 다룸.
   대신 PHOTOS_PER_PERSON=1(기본값)일 땐 file_a/path_a 같은 예전 단일값 키도 그대로
   같이 채워둬서, 아직 카드 UI로 안 바뀐 화면 코드도 예전처럼 동작함 (하위호환).
"""

import os
import shutil
import random

from config import (
    BASE_DIR, TOURNA_NAME, LABEL_A, LABEL_B, CANDIDATE_A, CANDIDATE_B,
    VALID_ROUNDS, PHOTOS_PER_PERSON, get_bonsun_dir, get_whole_dir, get_all_photos_dir,
)
from logic.common import (
    get_ext, find_group_files, group_source_files_by_person,
    find_person_files, build_labeled_names,
)
from logic.prelim import get_prelim_bonsun_dir, count_prelim_matches


def compute_default_source(round_size):
    """'새로 만들기'에서 소스 폴더 기본값 계산: 이전 라운드 본선이 있으면 이번 라운드 '전체' 폴더,
    없으면(=대회 처음 시작) 원본 사진 전체 폴더"""
    prev_round_size = round_size * 2
    prev_bonsun_dir = get_bonsun_dir(prev_round_size) if prev_round_size in VALID_ROUNDS else None
    if prev_bonsun_dir and os.path.exists(prev_bonsun_dir):
        return get_whole_dir(round_size)
    return get_all_photos_dir()


def build_bracket_plan(source_dir, round_size):
    """소스 폴더의 파일들을 '사람 단위'(PHOTOS_PER_PERSON장씩)로 묶은 다음 셔플해서 2명씩 짝지음.
    반환: (total_people, pairs, dropped, leftover)
      total_people: 정상적으로 인식된 사람 수
      pairs: [(group_num, files_a, new_names_a, files_b, new_names_b), ...]
             files_*는 원본 파일명 리스트, new_names_*는 저장될 새 파일명 리스트 (둘 다 순서 대응)
      dropped: 인원이 홀수라 마지막 1명 제외됐는지
      leftover: 사진 장수 규칙에 안 맞아서 묶이지 못한 파일들 (경고용)
    """
    files = [f for f in os.listdir(source_dir)
             if os.path.isfile(os.path.join(source_dir, f)) and not f.startswith('.')]

    groups, leftover = group_source_files_by_person(files, PHOTOS_PER_PERSON)
    random.shuffle(groups)

    dropped = False
    if len(groups) % 2 != 0:
        groups = groups[:-1]
        dropped = True

    pairs = []
    for i in range(0, len(groups), 2):
        group_num = (i // 2) + 1
        person_a_files = groups[i]
        person_b_files = groups[i + 1]

        prefix_a = f"{TOURNA_NAME}_{round_size}강_{group_num}조_{LABEL_A}"
        prefix_b = f"{TOURNA_NAME}_{round_size}강_{group_num}조_{LABEL_B}"
        new_names_a = build_labeled_names(prefix_a, [get_ext(f) for f in person_a_files])
        new_names_b = build_labeled_names(prefix_b, [get_ext(f) for f in person_b_files])

        pairs.append((group_num, person_a_files, new_names_a, person_b_files, new_names_b))

    return len(groups), pairs, dropped, leftover


def apply_bracket_plan(source_dir, target_dir, pairs):
    os.makedirs(target_dir, exist_ok=True)
    log = []
    for group_num, files_a, new_names_a, files_b, new_names_b in pairs:
        try:
            for src, new_name in zip(files_a, new_names_a):
                shutil.copy(os.path.join(source_dir, src), os.path.join(target_dir, new_name))
            for src, new_name in zip(files_b, new_names_b):
                shutil.copy(os.path.join(source_dir, src), os.path.join(target_dir, new_name))
            a_desc = new_names_a[0] if len(new_names_a) == 1 else f"{new_names_a[0]} 외 {len(new_names_a) - 1}장"
            b_desc = new_names_b[0] if len(new_names_b) == 1 else f"{new_names_b[0]} 외 {len(new_names_b) - 1}장"
            log.append(f"✅ {group_num}조 → {LABEL_A}: {a_desc}  /  {LABEL_B}: {b_desc}")
        except Exception as e:
            log.append(f"❌ {group_num}조 실패: {e}")
    return log


def _build_match_entry(group_num, files_a, paths_a, files_b, paths_b):
    """matches 리스트의 원소 하나를 만듦. 예전 단일값 키(file_a/path_a 등)도 같이 채워서
    아직 카드 UI로 안 바뀐 화면 코드가 그대로 동작하게 함 (files_a[0]과 동일한 값)."""
    return {
        "group_num": group_num,
        "files_a": files_a, "paths_a": paths_a,
        "files_b": files_b, "paths_b": paths_b,
        "file_a": files_a[0], "path_a": paths_a[0],
        "file_b": files_b[0], "path_b": paths_b[0],
        "selected": None,
    }


def load_matches_for_round(round_size):
    """'승자 입력'에서, 이 라운드를 만들기 위해 참고할 이전(더 큰) 라운드의 매치 목록을 불러옴.
    반환: (prev_round_size, source_dir, matches) — source_dir이 없으면 matches=None"""
    if round_size == 2:
        prev_round_size = 4
        match_count = 2
    else:
        prev_round_size = round_size * 2
        match_count = prev_round_size // 2

    source_dir = get_bonsun_dir(prev_round_size)
    if not os.path.isdir(source_dir):
        return prev_round_size, source_dir, None

    matches = []
    for group_num in range(1, match_count + 1):
        prefix_a = f"{TOURNA_NAME}_{prev_round_size}강_{group_num}조_{LABEL_A}"
        prefix_b = f"{TOURNA_NAME}_{prev_round_size}강_{group_num}조_{LABEL_B}"
        files_a = find_person_files(source_dir, prefix_a)
        files_b = find_person_files(source_dir, prefix_b)
        if not files_a or not files_b:
            continue
        paths_a = [os.path.join(source_dir, f) for f in files_a]
        paths_b = [os.path.join(source_dir, f) for f in files_b]
        matches.append(_build_match_entry(group_num, files_a, paths_a, files_b, paths_b))
    return prev_round_size, source_dir, matches


def apply_next_round(matches, next_round_size):
    """일반 라운드(2강이 아닌 경우): 선택된 승자들을 모아서 다음 라운드 폴더를 만듦"""
    winners = []  # [(files, paths), ...] - 한 명 분량씩
    for m in matches:
        if m["selected"] == "A":
            winners.append((m["files_a"], m["paths_a"]))
        elif m["selected"] == "B":
            winners.append((m["files_b"], m["paths_b"]))

    log = []
    if len(winners) % 2 != 0:
        log.append(f"⚠️ 승자가 홀수({len(winners)}명)입니다. 마지막 1명은 제외하고 진행합니다.")
        winners = winners[:len(winners) - 1]

    whole_dir = get_whole_dir(next_round_size)
    os.makedirs(whole_dir, exist_ok=True)
    for files, paths in winners:
        for name, path in zip(files, paths):
            shutil.copy(path, os.path.join(whole_dir, name))
    log.append(f"📁 승자 {len(winners)}명 → {os.path.basename(whole_dir)} 저장 완료")

    random.shuffle(winners)
    target_dir = get_bonsun_dir(next_round_size)
    os.makedirs(target_dir, exist_ok=True)

    for i in range(0, len(winners), 2):
        group_num = (i // 2) + 1
        files_a, paths_a = winners[i]
        files_b, paths_b = winners[i + 1]

        prefix_a = f"{TOURNA_NAME}_{next_round_size}강_{group_num}조_{LABEL_A}"
        prefix_b = f"{TOURNA_NAME}_{next_round_size}강_{group_num}조_{LABEL_B}"
        new_names_a = build_labeled_names(prefix_a, [get_ext(f) for f in files_a])
        new_names_b = build_labeled_names(prefix_b, [get_ext(f) for f in files_b])

        for path, new_name in zip(paths_a, new_names_a):
            shutil.copy(path, os.path.join(target_dir, new_name))
        for path, new_name in zip(paths_b, new_names_b):
            shutil.copy(path, os.path.join(target_dir, new_name))

        a_desc = new_names_a[0] if len(new_names_a) == 1 else f"{new_names_a[0]} 외 {len(new_names_a) - 1}장"
        b_desc = new_names_b[0] if len(new_names_b) == 1 else f"{new_names_b[0]} 외 {len(new_names_b) - 1}장"
        log.append(f"  {group_num}조 → {LABEL_A}: {a_desc}  /  {LABEL_B}: {b_desc}")

    log.append(f"🎉 {next_round_size}강 대진표 구성 완료!")
    return log


def apply_final_and_third(matches):
    """2강(결승전 + 3,4위전) 전용: 4강 매치 2개에서 승자→결승, 패자→3,4위전"""
    winners, losers = [], []  # [(files, paths), ...]
    for m in matches:
        if m["selected"] == "A":
            winners.append((m["files_a"], m["paths_a"]))
            losers.append((m["files_b"], m["paths_b"]))
        else:
            winners.append((m["files_b"], m["paths_b"]))
            losers.append((m["files_a"], m["paths_a"]))

    log = []
    whole_dir = get_whole_dir(2)
    os.makedirs(whole_dir, exist_ok=True)
    for files, paths in winners:
        for name, path in zip(files, paths):
            shutil.copy(path, os.path.join(whole_dir, name))
    log.append(f"📁 결승 진출자 {len(winners)}명 → {os.path.basename(whole_dir)} 저장 완료")

    target_dir = get_bonsun_dir(2)
    os.makedirs(target_dir, exist_ok=True)

    random.shuffle(winners)
    (w1_files, w1_paths), (w2_files, w2_paths) = winners
    final_a_names = build_labeled_names(f"{TOURNA_NAME}_결승전_{LABEL_A}", [get_ext(f) for f in w1_files])
    final_b_names = build_labeled_names(f"{TOURNA_NAME}_결승전_{LABEL_B}", [get_ext(f) for f in w2_files])
    for path, name in zip(w1_paths, final_a_names):
        shutil.copy(path, os.path.join(target_dir, name))
    for path, name in zip(w2_paths, final_b_names):
        shutil.copy(path, os.path.join(target_dir, name))
    log.append(f"🏆 결승전 → {LABEL_A}: {final_a_names[0]}  /  {LABEL_B}: {final_b_names[0]}")

    random.shuffle(losers)
    (l1_files, l1_paths), (l2_files, l2_paths) = losers
    third_a_names = build_labeled_names(f"{TOURNA_NAME}_3,4위전_{LABEL_A}", [get_ext(f) for f in l1_files])
    third_b_names = build_labeled_names(f"{TOURNA_NAME}_3,4위전_{LABEL_B}", [get_ext(f) for f in l2_files])
    for path, name in zip(l1_paths, third_a_names):
        shutil.copy(path, os.path.join(target_dir, name))
    for path, name in zip(l2_paths, third_b_names):
        shutil.copy(path, os.path.join(target_dir, name))
    log.append(f"🥉 3,4위전 → {LABEL_A}: {third_a_names[0]}  /  {LABEL_B}: {third_b_names[0]}")

    log.append("🎉 결승전 + 3,4위전 대진표 구성 완료!")
    return log


def find_group_images(round_num, group_num):
    """본선 폴더에서 group_num조에 해당하는 두 사람의 사진 경로 리스트를 찾음.
    round_num == "prelim"이면 예선전 본선 폴더에서 찾음.
    반환: (paths_a, paths_b) - 둘 다 리스트 (1인당 사진 장수만큼). 못 찾으면 (None, None)."""
    if round_num == "prelim":
        bonsun_dir = get_prelim_bonsun_dir()
        prefix_a = f"{TOURNA_NAME}_예선전_{group_num}조_{LABEL_A}"
        prefix_b = f"{TOURNA_NAME}_예선전_{group_num}조_{LABEL_B}"
    else:
        bonsun_dir = get_bonsun_dir(round_num)
        if round_num == 2:
            label_map = {1: "3,4위전", 2: "결승전"}
            match_label = label_map.get(group_num)
            if match_label is None:
                return None, None
            prefix_a = f"{TOURNA_NAME}_{match_label}_{LABEL_A}"
            prefix_b = f"{TOURNA_NAME}_{match_label}_{LABEL_B}"
        else:
            prefix_a = f"{TOURNA_NAME}_{round_num}강_{group_num}조_{LABEL_A}"
            prefix_b = f"{TOURNA_NAME}_{round_num}강_{group_num}조_{LABEL_B}"

    if not os.path.exists(bonsun_dir):
        return None, None

    files_a = find_person_files(bonsun_dir, prefix_a)
    files_b = find_person_files(bonsun_dir, prefix_b)
    if not files_a or not files_b:
        return None, None

    paths_a = [os.path.join(bonsun_dir, f) for f in files_a]
    paths_b = [os.path.join(bonsun_dir, f) for f in files_b]
    return paths_a, paths_b


def find_title_images():
    """대회 최상위 폴더(BASE_DIR)에서 후보 이름이 들어간 타이틀 이미지 2개를 찾음"""
    file_a = file_b = None
    if os.path.exists(BASE_DIR):
        for f in os.listdir(BASE_DIR):
            if not os.path.isfile(os.path.join(BASE_DIR, f)):
                continue
            if CANDIDATE_A in f:
                file_a = f
            elif CANDIDATE_B in f:
                file_b = f
    path_a = os.path.join(BASE_DIR, file_a) if file_a else None
    path_b = os.path.join(BASE_DIR, file_b) if file_b else None
    return path_a, path_b


def generate_thumbnails_for_round(round_size):
    """somenail_maker.py 로직 이식. 방금 만든 본선 폴더(get_bonsun_dir)의 GIF들을
    JPG 썸네일로 변환해서 '...(썸네일본선)' 폴더에 저장함."""
    try:
        from PIL import Image
    except ImportError:
        return ["❌ 썸네일 생성 실패: Pillow 라이브러리가 없어요. 'pip install Pillow' 실행 후 다시 시도해주세요."]

    source_dir = get_bonsun_dir(round_size)
    if not os.path.isdir(source_dir):
        return [f"⚠️ 썸네일 생성 건너뜀: {source_dir} 폴더가 없어요."]

    gif_files = [f for f in os.listdir(source_dir) if f.lower().endswith(".gif")]
    if not gif_files:
        return [f"⚠️ 썸네일 생성 건너뜀: '{os.path.basename(source_dir)}' 안에 GIF 파일이 없어요."]

    target_dir = os.path.join(os.path.dirname(source_dir), f"{TOURNA_NAME}_{round_size}강(썸네일본선)")
    os.makedirs(target_dir, exist_ok=True)

    log = [f"🖼️ 썸네일 생성 시작... ({len(gif_files)}개 GIF)"]
    count = 0
    for filename in gif_files:
        gif_path = os.path.join(source_dir, filename)
        try:
            img = Image.open(gif_path)
            rgb_im = img.convert("RGB")
            name_without_ext, _ = os.path.splitext(filename)
            new_filename = f"{name_without_ext}_썸네일.jpg"
            save_path = os.path.join(target_dir, new_filename)
            rgb_im.save(save_path, "JPEG", quality=85)
            count += 1
        except Exception as e:
            log.append(f"❌ {filename} 변환 실패: {e}")

    log.append(f"✅ 총 {count}개 GIF → JPG 썸네일 변환 완료")
    log.append(f"📁 썸네일 저장 위치: {target_dir}")
    return log


# =============================================
#  대진표 스왑(맞바꾸기) 기능
#  "얘네 둘은 진짜 결승감인데 초반에 만났네" 싶을 때, 이미 만들어진 대진표에서
#  두 사람의 자리를 실제 파일명을 바꿔서 영구적으로 맞바꿔줌.
#  round_key: 일반 라운드는 정수(예: 32), 결승/3,4위는 2, 예선전은 문자열 "prelim"
# =============================================

def get_round_bonsun_dir_for(round_key):
    """round_key에 맞는 본선 폴더 경로 (일반 라운드/결승/예선전 전부 지원)"""
    if round_key == "prelim":
        return get_prelim_bonsun_dir()
    return get_bonsun_dir(round_key)


def slot_prefix(round_key, group_num, side):
    """이 라운드의 group_num조, side(A/B) 자리에 해당하는 파일명 접두사"""
    label = LABEL_A if side == "A" else LABEL_B
    if round_key == "prelim":
        return f"{TOURNA_NAME}_예선전_{group_num}조_{label}"
    if round_key == 2:
        match_label = {1: "3,4위전", 2: "결승전"}.get(group_num)
        return f"{TOURNA_NAME}_{match_label}_{label}"
    return f"{TOURNA_NAME}_{round_key}강_{group_num}조_{label}"


def load_round_bracket(round_key):
    """이미 만들어진 '이 라운드 자기 자신'의 본선 폴더를 직접 읽어서 매치 목록을 만듦
    (스왑 편집 화면용. load_matches_for_round와 달리 '이전 라운드'가 아니라 이 라운드 자체를 봄).
    반환: (source_dir, matches) — 폴더가 없으면 matches=None"""
    source_dir = get_round_bonsun_dir_for(round_key)
    if not os.path.isdir(source_dir):
        return source_dir, None

    if round_key == "prelim":
        match_count = count_prelim_matches()
    elif round_key == 2:
        match_count = 2
    else:
        match_count = round_key // 2

    matches = []
    for group_num in range(1, match_count + 1):
        prefix_a = slot_prefix(round_key, group_num, "A")
        prefix_b = slot_prefix(round_key, group_num, "B")
        files_a = find_person_files(source_dir, prefix_a)
        files_b = find_person_files(source_dir, prefix_b)
        if not files_a or not files_b:
            continue
        paths_a = [os.path.join(source_dir, f) for f in files_a]
        paths_b = [os.path.join(source_dir, f) for f in files_b]
        matches.append(_build_match_entry(group_num, files_a, paths_a, files_b, paths_b))
    return source_dir, matches


def swap_bracket_slots(round_key, slot_a, slot_b):
    """두 자리(slot_a, slot_b: {"group_num":, "side":, "paths":[...]})에 있는 사람을 서로 맞바꿈.
    실제 파일 이름을 바꿔서 디스크에 영구 반영함 (임시 이름을 거쳐서 충돌 없이 안전하게 처리)."""
    source_dir = get_round_bonsun_dir_for(round_key)
    prefix_a = slot_prefix(round_key, slot_a["group_num"], slot_a["side"])
    prefix_b = slot_prefix(round_key, slot_b["group_num"], slot_b["side"])

    exts_a = [get_ext(p) for p in slot_a["paths"]]
    exts_b = [get_ext(p) for p in slot_b["paths"]]

    # slot_b의 사람 사진들 -> slot_a 자리 이름으로, slot_a의 사람 사진들 -> slot_b 자리 이름으로
    names_for_b_at_a = build_labeled_names(prefix_a, exts_b)
    names_for_a_at_b = build_labeled_names(prefix_b, exts_a)

    # 이름이 겹칠 수 있어서(예: 같은 파일명 패턴) 임시 이름을 거쳐 안전하게 처리
    tmp_a = []
    for p in slot_a["paths"]:
        tmp = p + ".swaptmp"
        os.rename(p, tmp)
        tmp_a.append(tmp)
    tmp_b = []
    for p in slot_b["paths"]:
        tmp = p + ".swaptmp"
        os.rename(p, tmp)
        tmp_b.append(tmp)

    for tmp, new_name in zip(tmp_b, names_for_b_at_a):
        os.rename(tmp, os.path.join(source_dir, new_name))
    for tmp, new_name in zip(tmp_a, names_for_a_at_b):
        os.rename(tmp, os.path.join(source_dir, new_name))

    label_a = "A" if slot_a["side"] == "A" else "B"
    label_b = "A" if slot_b["side"] == "A" else "B"
    return f"🔄 {slot_a['group_num']}조({label_a}) ↔ {slot_b['group_num']}조({label_b}) 자리를 맞바꿨어요."