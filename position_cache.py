import json
import os
import sys


def _app_dir():
    """position_cache.json을 저장할 기준 폴더 (exe 패키징 시에도 안정적인 위치를 쓰기 위함).
    config.py의 _app_dir()과 동일한 이유로 필요함."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CACHE_FILE = os.path.join(_app_dir(), "position_cache.json")


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)