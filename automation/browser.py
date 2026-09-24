# automation/browser.py
# Mục đích: Điều khiển Chrome — mở trang, search, back, wait load
# Phương pháp: pyautogui — hoạt động trên Windows và Linux X11

import time
import subprocess
import pyautogui

from automation.clipboard import copy_from_address_bar
from vision.screenshot import capture_fullscreen, compare_screenshots

PAGE_LOAD_WAIT    = 2.5
PAGE_LOAD_TIMEOUT = 10


def open_url(url: str) -> bool:
    """
    Mục đích: Mở URL trong Chrome bằng Ctrl+L → gõ URL → Enter.
    """
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.typewrite(url, interval=0.02)
    time.sleep(0.2)
    pyautogui.press("enter")
    print(f"[browser] Mở URL: '{url}'")
    wait_for_load()
    return True


def open_search(keyword: str, initial_wait: float = 5.0) -> bool:
    """
    Mục đích: Search Google với query chuẩn cho project.
    initial_wait: giây chờ để người dùng kịp click vào Chrome trước khi gửi keypress.
    Query: site:facebook.com "zalo.me/g/" <keyword>
    """
    if initial_wait > 0:
        print(f"[browser] Chờ {initial_wait:.0f}s — click vào Chrome ngay...")
        time.sleep(initial_wait)

    query = f'site:facebook.com "zalo.me/g/" {keyword}'
    encoded = query.replace(" ", "+").replace('"', '%22')
    url = f"https://www.google.com/search?q={encoded}"
    print(f"[browser] Search: '{query}'")
    return open_url(url)


def go_back() -> bool:
    """
    Mục đích: Quay lại trang trước — Alt+Left.
    Trả về True nếu trang đã thay đổi.
    """
    img_before = capture_fullscreen()
    pyautogui.hotkey("alt", "left")
    print("[browser] Go back")
    time.sleep(PAGE_LOAD_WAIT)

    img_after = capture_fullscreen()
    changed = compare_screenshots(img_before, img_after)
    if not changed:
        print("[browser] ⚠️  Go back có vẻ không thành công")
    return changed


def wait_for_load(timeout: float = PAGE_LOAD_TIMEOUT) -> bool:
    """
    Mục đích: Chờ trang Chrome load xong.
    Phương pháp: So sánh screenshot liên tiếp — khi trang ngừng thay đổi = load xong.
    """
    print("[browser] Chờ trang load...")
    time.sleep(0.5)

    start = time.time()
    img_prev = capture_fullscreen()

    while time.time() - start < timeout:
        time.sleep(0.8)
        img_curr = capture_fullscreen()
        if not compare_screenshots(img_prev, img_curr, threshold=0.005):
            print(f"[browser] Trang load xong sau {time.time()-start:.1f}s")
            return True
        img_prev = img_curr

    print(f"[browser] ⚠️  Timeout {timeout}s")
    return False


def scroll_down(times: int = 3) -> None:
    """
    Mục đích: Cuộn trang xuống.
    Phương pháp: pyautogui.press("pagedown").
    """
    cx, cy = pyautogui.size()
    pyautogui.moveTo(cx // 2, cy // 2)
    for _ in range(times):
        pyautogui.press("pagedown")
        time.sleep(0.3)
    print(f"[browser] Cuộn xuống {times} lần")


def get_current_url() -> str | None:
    """Mục đích: Lấy URL trang hiện tại từ address bar."""
    return copy_from_address_bar()
