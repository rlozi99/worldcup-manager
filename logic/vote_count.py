"""
투표 집계 로직 (comments_count_v4.py 이식)
"""

import re

from config import CANDIDATE_A, CANDIDATE_B, COMMENT_AUTHOR_LABEL, REPLY_TAG

METADATA_PATTERN = re.compile(rf'^(\d+)\.\s+{re.escape(COMMENT_AUTHOR_LABEL)}(.*)$')
REPLY_PATTERN = re.compile(rf'=\s*\[?(\d+){re.escape(REPLY_TAG)}\]?')


def count_votes_from_file(file_path):
    a_count = 0
    b_count = 0
    others = []
    reply_flags = []

    with open(file_path, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()

    comment_start_pattern = re.compile(r'댓글\s*\d+개')
    comment_end_pattern = re.compile(r'새\s*댓글\s*확인하기')

    start_idx = None
    end_idx = None
    for idx, raw_line in enumerate(raw_lines):
        if start_idx is None and comment_start_pattern.search(raw_line):
            start_idx = idx + 1
            continue
        if start_idx is not None and comment_end_pattern.search(raw_line):
            end_idx = idx
            break

    if start_idx is not None:
        lines = raw_lines[start_idx:end_idx] if end_idx is not None else raw_lines[start_idx:]
    else:
        lines = raw_lines

    current_is_reply = False
    reply_target_no = None
    current_comment_no = None
    awaiting_content = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        meta_match = METADATA_PATTERN.match(line)
        if meta_match:
            current_comment_no = meta_match.group(1)
            rest = meta_match.group(2)
            reply_match = REPLY_PATTERN.search(rest)
            if reply_match:
                current_is_reply = True
                reply_target_no = reply_match.group(1)
            else:
                current_is_reply = False
                reply_target_no = None
            awaiting_content = True
            continue

        if not awaiting_content:
            continue
        awaiting_content = False

        if current_is_reply:
            reply_flags.append((current_comment_no, reply_target_no, line))
            current_is_reply = False

        if line == CANDIDATE_A:
            a_count += 1
        elif line == CANDIDATE_B:
            b_count += 1
        else:
            others.append((current_comment_no, line))

    return a_count, b_count, others, reply_flags
