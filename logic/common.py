"""
여러 logic 모듈이 공통으로 쓰는 아주 작은 헬퍼들.
다른 logic 모듈에 의존하지 않아야 순환 임포트가 안 생기므로 따로 뺌.
"""

import os
import re

from config import FINAL_ROUND_LABEL


def round_label(round_num):
    """폴더/파일명에 쓸 라운드 표기: 2강만 특별 라벨, 나머지는 'N강'"""
    return FINAL_ROUND_LABEL if round_num == 2 else f"{round_num}강"


def get_ext(filename):
    return os.path.splitext(filename)[1]


def find_group_files(source_dir, prefix_a, prefix_b):
    """폴더 안에서 prefix_a/prefix_b로 시작하는 파일을 각각 찾음 (대진표/예선전 공용).
    1인 1장(PHOTOS_PER_PERSON=1) 전용. 여러 장일 땐 find_person_files를 씀."""
    file_a = file_b = None
    for f in os.listdir(source_dir):
        if f.startswith(prefix_a):
            file_a = f
        elif f.startswith(prefix_b):
            file_b = f
    return file_a, file_b


# =============================================
#  1인당 사진 여러 장(PHOTOS_PER_PERSON > 1) 지원용 헬퍼
# =============================================

_NUMBERED_SUFFIX_RE = re.compile(r'^(.*)_(\d+)(\.[^.]+)$')


def group_source_files_by_person(files, photos_per_person):
    """원본 폴더의 파일 목록을 '사람 단위'로 묶음.

    photos_per_person == 1 이면 각 파일을 독립된 1인으로 취급 (기존 동작 그대로).
    2 이상이면 파일명이 '{이름}_{번호}.ext' 패턴이어야 하고 (예: 홍길동_1.jpg, 홍길동_2.jpg),
    번호가 1~photos_per_person까지 정확히 다 있는 이름끼리만 한 세트로 묶음.

    반환: (groups, leftover)
      groups: [[file1, file2, ...], ...] - 각 원소가 한 명 분량 파일 목록 (번호 순 정렬됨)
      leftover: 규칙에 안 맞거나 개수가 안 맞아서 묶이지 못한 파일들 (사용자에게 경고용)
    """
    if photos_per_person <= 1:
        return [[f] for f in files], []

    buckets = {}
    unmatched = []
    for f in files:
        m = _NUMBERED_SUFFIX_RE.match(f)
        if not m:
            unmatched.append(f)
            continue
        name, num = m.group(1), int(m.group(2))
        buckets.setdefault(name, {})[num] = f

    groups = []
    leftover = list(unmatched)
    for name, numbered in buckets.items():
        expected = list(range(1, photos_per_person + 1))
        if sorted(numbered.keys()) == expected:
            groups.append([numbered[n] for n in expected])
        else:
            leftover.extend(numbered.values())

    return groups, leftover


def find_person_files(source_dir, prefix):
    """본선 폴더 등에서 prefix로 시작하는 파일들을 전부 찾아서,
    파일명 끝의 '_숫자' 순서대로 정렬해 반환함 (1장이면 원소 1개짜리 리스트).
    한 사람의 사진 세트를 통째로 가져올 때 씀. 없으면 빈 리스트."""
    matches = [f for f in os.listdir(source_dir) if f.startswith(prefix)]
    if not matches:
        return []

    def sort_key(f):
        rest = f[len(prefix):]
        m = re.match(r'_(\d+)', rest)
        return int(m.group(1)) if m else 0

    return sorted(matches, key=sort_key)


def build_labeled_names(base_prefix, exts):
    """base_prefix(예: '테스트컵_64강_3조_1가') + 사진들의 확장자 리스트를 받아서
    실제 저장할 파일명 목록을 만듦.
    1장이면 ['{base_prefix}{ext}'], 여러 장이면 ['{base_prefix}_1{ext}', '{base_prefix}_2{ext}', ...]."""
    if len(exts) == 1:
        return [f"{base_prefix}{exts[0]}"]
    return [f"{base_prefix}_{i + 1}{ext}" for i, ext in enumerate(exts)]