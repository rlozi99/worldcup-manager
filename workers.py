"""
백그라운드 자동화 스레드
====================================
제목/사진 자동 업로드, 댓글 자동 수집은 마우스/키보드를 실제로 조작하면서
time.sleep()으로 대기하는 구간이 많아서, 메인 GUI 스레드에서 그대로 실행하면
화면이 멈춰버림. QThread로 분리해서 백그라운드에서 돌리고, 진행 상황은
시그널로 GUI에 전달함.
"""

import os
import time

from PySide6.QtCore import QThread, Signal

from app_state import pyautogui, pyperclip, HAS_AUTOMATION
from logic.tournament import find_title_images, find_group_images
from logic.automation import (
    upload_paths_recursive,
    AFTER_PASTE_DELAY, AFTER_TAB_SWITCH_DELAY, AFTER_WINDOW_SWITCH_DELAY,
    AFTER_SELECT_ALL_DELAY, AFTER_COPY_DELAY,
    COMMENTS_AFTER_TAB_SWITCH_DELAY, COMMENTS_AFTER_WINDOW_SWITCH_DELAY,
)


class UploadWorker(QThread):
    """실제 마우스/키보드 자동화를 수행하는 백그라운드 스레드 (GUI가 멈추지 않도록)"""

    log_signal = Signal(str)
    finished_signal = Signal(bool)  # True=정상 완료, False=중단/오류

    def __init__(self, titles, round_num, group_size, coords, num_windows, parent=None):
        super().__init__(parent)
        self.titles = titles
        self.round_num = round_num
        self.group_size = group_size
        self.coords = coords
        self.num_windows = num_windows
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            title_img_a, title_img_b = find_title_images()
            icon_pos = self.coords["brave_icon"]
            title_pos = self.coords["title_field"]
            align_center_pos = self.coords["align_center"]
            upload_button_pos = self.coords["upload_button"]
            filename_field_pos = self.coords["filename_field"]
            # 1번째 창은 이미 포커스되어 있어서 썸네일 좌표가 없음 (2번째 창부터 존재)
            window_positions = [self.coords[f"thumb_{self.num_windows}win_{w}"]
                                 for w in range(2, self.num_windows + 1)]

            if title_img_a and title_img_b:
                self.log_signal.emit(f"✅ 타이틀 이미지 찾음: {os.path.basename(title_img_a)} / {os.path.basename(title_img_b)}")
            else:
                self.log_signal.emit("⚠️ 타이틀 이미지를 못 찾았어요. 조 사진만 업로드합니다.")

            window_index = 0
            total = len(self.titles)

            for i, title in enumerate(self.titles, 1):
                if self._stop:
                    self.log_signal.emit("⏹ 사용자가 중지했어요.")
                    self.finished_signal.emit(False)
                    return

                pyperclip.copy(title)

                pyautogui.click(*title_pos)
                time.sleep(0.2)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.hotkey("ctrl", "v")

                pyautogui.click(*align_center_pos)

                paths_a, paths_b = find_group_images(self.round_num, i)
                if paths_a and paths_b:
                    # 한 사람씩 따로 업로드하고, 두 사람 사이에 엔터 2번(빈 줄 하나)을 넣어서
                    # 게시글 본문에서 두 후보 사진 묶음이 확실히 구분되도록 함.
                    upload_paths_recursive([title_img_a] + paths_a, upload_button_pos, filename_field_pos)
                    pyautogui.press("enter")
                    pyautogui.press("enter")
                    time.sleep(0.2)
                    upload_paths_recursive([title_img_b] + paths_b, upload_button_pos, filename_field_pos)
                else:
                    self.log_signal.emit(f"   ⚠️ {i}조 이미지 파일을 못 찾았어요. 이미지 업로드는 건너뜁니다.")

                self.log_signal.emit(f"[{i}/{total}] 완료: {title}")
                time.sleep(AFTER_PASTE_DELAY)

                if i < total:
                    if i % self.group_size == 0:
                        window_index += 1
                        pyautogui.click(*icon_pos)
                        time.sleep(0.6)
                        pyautogui.click(*window_positions[window_index - 1])
                        time.sleep(AFTER_WINDOW_SWITCH_DELAY)
                    else:
                        pyautogui.hotkey("ctrl", "tab")
                        time.sleep(AFTER_TAB_SWITCH_DELAY)

            self.log_signal.emit("🎉 전부 붙여넣기 완료!")
            self.finished_signal.emit(True)

        except Exception as e:
            if HAS_AUTOMATION and isinstance(e, pyautogui.FailSafeException):
                self.log_signal.emit("⏹ 마우스를 화면 모서리로 이동해서 중단했어요. 안전하게 멈췄어요.")
            else:
                self.log_signal.emit(f"❌ 오류 발생: {e}")
            self.finished_signal.emit(False)


class CommentsCollectWorker(QThread):
    """각 탭에서 전체선택→복사→N조.txt 저장을 반복하는 백그라운드 스레드"""

    log_signal = Signal(str)
    finished_signal = Signal(bool)

    def __init__(self, vote_folder, total, group_size, coords, num_windows, parent=None):
        super().__init__(parent)
        self.vote_folder = vote_folder
        self.total = total
        self.group_size = group_size
        self.coords = coords
        self.num_windows = num_windows
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            os.makedirs(self.vote_folder, exist_ok=True)
            icon_pos = self.coords["brave_icon"]
            # 1번째 창은 이미 포커스되어 있어서 썸네일 좌표가 없음 (2번째 창부터 존재)
            window_positions = [self.coords[f"thumb_{self.num_windows}win_{w}"]
                                 for w in range(2, self.num_windows + 1)]

            window_index = 0

            for i in range(1, self.total + 1):
                if self._stop:
                    self.log_signal.emit("⏹ 사용자가 중지했어요.")
                    self.finished_signal.emit(False)
                    return

                pyautogui.hotkey("ctrl", "a")
                time.sleep(AFTER_SELECT_ALL_DELAY)
                pyautogui.hotkey("ctrl", "c")
                time.sleep(AFTER_COPY_DELAY)

                content = pyperclip.paste()
                file_path = os.path.join(self.vote_folder, f"{i}조.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.log_signal.emit(f"[{i}/{self.total}] {i}조.txt 저장 완료 ({len(content)}자)")

                if i < self.total:
                    if i % self.group_size == 0:
                        window_index += 1
                        pyautogui.click(*icon_pos)
                        time.sleep(0.6)
                        pyautogui.click(*window_positions[window_index - 1])
                        time.sleep(COMMENTS_AFTER_WINDOW_SWITCH_DELAY)
                    else:
                        pyautogui.hotkey("ctrl", "tab")
                        time.sleep(COMMENTS_AFTER_TAB_SWITCH_DELAY)

            self.log_signal.emit("🎉 전체 조 댓글 수집 완료!")
            self.log_signal.emit(f"📁 저장 위치: {self.vote_folder}")
            self.finished_signal.emit(True)

        except Exception as e:
            if HAS_AUTOMATION and isinstance(e, pyautogui.FailSafeException):
                self.log_signal.emit("⏹ 마우스를 화면 모서리로 이동해서 중단했어요. 안전하게 멈췄어요.")
            else:
                self.log_signal.emit(f"❌ 오류 발생: {e}")
            self.finished_signal.emit(False)