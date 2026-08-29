"""
예선전 로직 (참가자 수가 128/64/32... 딱 안 맞을 때 - 예: 100개 → 부전승 28 + 예선전 72)

⚠️ PHOTOS_PER_PERSON(1인당 사진 장수) 지원:
   '사람 키'는 그 사람의 첫 번째 사진 파일명을 씀. PHOTOS_PER_PERSON=1일 땐 파일명 자체가
   키라서, 화면(picker UI) 쪽 코드는 예전과 완전히 동일하게 동작함 (하위호환).
"""

import os
import re
import shutil
import random

from config import BASE_DIR, TOURNA_NAME, LABEL_A, LABEL_B, PHOTOS_PER_PERSON, get_whole_dir, get_bonsun_dir
from logic.common import (
    get_ext, find_group_files, group_source_files_by_person,
    find_person_files, build_labeled_names,
)


def get_prelim_round_dir():
    """다른 라운드들(BASE_DIR/{대회명}_N강)이랑 같은 구조로, 예선전도 상위 폴더 하나를 둠.
    여기 바로 아래에 제목 파일도 놓임 (title_maker의 get_round_dir(N)에 대응하는 예선전 버전)."""
    return os.path.join(BASE_DIR, f"{TOURNA_NAME}_예선전")


def get_prelim_bonsun_dir():
    return os.path.join(get_prelim_round_dir(), f"{TOURNA_NAME}_예선전(본선)")


def get_prelim_byes_dir():
    return os.path.join(get_prelim_round_dir(), f"{TOURNA_NAME}_예선전(부전승)")


def count_prelim_matches():
    """예선전 본선 폴더에 실제로 몇 조가 만들어져 있는지 셈 (고정 숫자가 아니라 그때그때 다름)"""
    source_dir = get_prelim_bonsun_dir()
    if not os.path.isdir(source_dir):
        return 0
    prefix_re = re.compile(rf"^{re.escape(TOURNA_NAME)}_예선전_(\d+)조_")
    group_nums = set()
    for f in os.listdir(source_dir):
        m = prefix_re.match(f)
        if m:
            group_nums.add(int(m.group(1)))
    return len(group_nums)


def group_prelim_source_files(all_files):
    """예선전 소스 폴더 파일들을 PHOTOS_PER_PERSON 기준으로 사람 단위로 묶음 (화면에서 부전승 고를 때 씀).
    반환: (groups, leftover) - group_source_files_by_person과 동일 형식."""
    return group_source_files_by_person(all_files, PHOTOS_PER_PERSON)


def compute_prelim_plan(total, target_round):
    """총 참가자 수(total, 사람 기준)를 target_round강에 정확히 맞추려면 부전승이 몇 명 필요한지 계산.
    반환: (byes_count, prelim_count, matches_count) / 조건이 안 맞으면 None
    공식: byes = 2*target - total (예: 100명, 64강 목표 → byes = 128-100 = 28)"""
    if total <= target_round:
        return None
    byes_count = 2 * target_round - total
    if not (0 <= byes_count < total):
        return None
    prelim_count = total - byes_count
    if prelim_count % 2 != 0:
        return None
    return byes_count, prelim_count, prelim_count // 2


def build_prelim_plan(all_files, byes_keys):
    """all_files: 소스 폴더의 전체 파일명 목록, byes_keys: 사용자가 고른 부전승의 '사람 키' 집합(set)
    (사람 키 = 그 사람의 첫 번째 사진 파일명. 1인 1장 모드면 파일명 자체와 동일해서 예전이랑 똑같이 동작함)
    나머지 사람들을 셔플해서 예선전 매치로 짝지음.
    반환: (byes_list, pairs, leftover)
      byes_list: 부전승으로 뽑힌 사람들의 원본 파일 전체 목록 (사진 여러 장이면 다 포함)
      pairs: [(group_num, files_a, new_names_a, files_b, new_names_b), ...]
      leftover: 사진 장수 규칙에 안 맞아서 묶이지 못한 파일들 (경고용)
    """
    groups, leftover = group_source_files_by_person(all_files, PHOTOS_PER_PERSON)

    byes_groups = [g for g in groups if g[0] in byes_keys]
    remaining = [g for g in groups if g[0] not in byes_keys]
    random.shuffle(remaining)

    pairs = []
    for i in range(0, len(remaining), 2):
        group_num = (i // 2) + 1
        person_a = remaining[i]
        person_b = remaining[i + 1]

        prefix_a = f"{TOURNA_NAME}_예선전_{group_num}조_{LABEL_A}"
        prefix_b = f"{TOURNA_NAME}_예선전_{group_num}조_{LABEL_B}"
        new_names_a = build_labeled_names(prefix_a, [get_ext(f) for f in person_a])
        new_names_b = build_labeled_names(prefix_b, [get_ext(f) for f in person_b])

        pairs.append((group_num, person_a, new_names_a, person_b, new_names_b))

    byes_list = [f for g in byes_groups for f in g]
    return byes_list, pairs, leftover


def apply_prelim_plan(source_dir, byes_list, pairs):
    """부전승 파일들은 '예선전(부전승)' 폴더에 원본 이름 그대로 보관,
    예선전 매치는 '예선전(본선)' 폴더에 라벨링해서 저장"""
    byes_dir = get_prelim_byes_dir()
    os.makedirs(byes_dir, exist_ok=True)
    log = []
    for fname in byes_list:
        shutil.copy(os.path.join(source_dir, fname), os.path.join(byes_dir, fname))
    log.append(f"📁 부전승 파일 {len(byes_list)}개 → {os.path.basename(byes_dir)} 저장 완료")

    target_dir = get_prelim_bonsun_dir()
    os.makedirs(target_dir, exist_ok=True)
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


def load_prelim_matches():
    """예선전(본선) 폴더에서 매치 목록을 불러옴 (일반 라운드와 폴더명 규칙이 달라서 별도 함수)"""
    source_dir = get_prelim_bonsun_dir()
    if not os.path.isdir(source_dir):
        return source_dir, None

    prefix_re = re.compile(rf"^{re.escape(TOURNA_NAME)}_예선전_(\d+)조_")
    group_nums = set()
    for f in os.listdir(source_dir):
        m = prefix_re.match(f)
        if m:
            group_nums.add(int(m.group(1)))

    matches = []
    for group_num in sorted(group_nums):
        prefix_a = f"{TOURNA_NAME}_예선전_{group_num}조_{LABEL_A}"
        prefix_b = f"{TOURNA_NAME}_예선전_{group_num}조_{LABEL_B}"
        files_a = find_person_files(source_dir, prefix_a)
        files_b = find_person_files(source_dir, prefix_b)
        if not files_a or not files_b:
            continue
        paths_a = [os.path.join(source_dir, f) for f in files_a]
        paths_b = [os.path.join(source_dir, f) for f in files_b]
        matches.append({
            "group_num": group_num,
            "files_a": files_a, "paths_a": paths_a,
            "files_b": files_b, "paths_b": paths_b,
            "file_a": files_a[0], "path_a": paths_a[0],
            "file_b": files_b[0], "path_b": paths_b[0],
            "selected": None,
        })
    return source_dir, matches


def apply_prelim_merge(matches, target_round):
    """예선전 승자 + 부전승을 합쳐서 target_round강 본선 폴더를 완성함 (셔플 후 표준 라운드 폴더에 저장)"""
    winners = []  # [(files, paths), ...] - 한 명 분량씩
    for m in matches:
        if m["selected"] == "A":
            winners.append((m["files_a"], m["paths_a"]))
        elif m["selected"] == "B":
            winners.append((m["files_b"], m["paths_b"]))

    byes_dir = get_prelim_byes_dir()
    byes_entries = []
    if os.path.isdir(byes_dir):
        byes_files = [f for f in os.listdir(byes_dir) if os.path.isfile(os.path.join(byes_dir, f))]
        byes_groups, _leftover = group_source_files_by_person(byes_files, PHOTOS_PER_PERSON)
        for g in byes_groups:
            byes_entries.append((g, [os.path.join(byes_dir, f) for f in g]))

    combined = winners + byes_entries
    log = [f"예선전 승자 {len(winners)}명 + 부전승 {len(byes_entries)}명 = 총 {len(combined)}명"]

    whole_dir = get_whole_dir(target_round)
    os.makedirs(whole_dir, exist_ok=True)
    for files, paths in combined:
        for name, path in zip(files, paths):
            shutil.copy(path, os.path.join(whole_dir, name))
    log.append(f"📁 전체 보관: {os.path.basename(whole_dir)}")

    random.shuffle(combined)
    target_dir = get_bonsun_dir(target_round)
    os.makedirs(target_dir, exist_ok=True)

    for i in range(0, len(combined), 2):
        group_num = (i // 2) + 1
        files_a, paths_a = combined[i]
        files_b, paths_b = combined[i + 1]

        prefix_a = f"{TOURNA_NAME}_{target_round}강_{group_num}조_{LABEL_A}"
        prefix_b = f"{TOURNA_NAME}_{target_round}강_{group_num}조_{LABEL_B}"
        new_names_a = build_labeled_names(prefix_a, [get_ext(f) for f in files_a])
        new_names_b = build_labeled_names(prefix_b, [get_ext(f) for f in files_b])

        for path, name in zip(paths_a, new_names_a):
            shutil.copy(path, os.path.join(target_dir, name))
        for path, name in zip(paths_b, new_names_b):
            shutil.copy(path, os.path.join(target_dir, name))

        a_desc = new_names_a[0] if len(new_names_a) == 1 else f"{new_names_a[0]} 외 {len(new_names_a) - 1}장"
        b_desc = new_names_b[0] if len(new_names_b) == 1 else f"{new_names_b[0]} 외 {len(new_names_b) - 1}장"
        log.append(f"{group_num}조 → {LABEL_A}: {a_desc}  /  {LABEL_B}: {b_desc}")

    log.append(f"🎉 {target_round}강 대진표 완성!")
    return log