# automation/navigation.py
# Mục đích: Điều hướng trong search result — click vào post, next page
# Phương pháp: OCR tìm vị trí element → pyautogui click
# Hoạt động trên: Windows và Linux X11

import time
import pyautogui

from vision.screenshot import capture_fullscreen, compare_screenshots
from vision.ocr import extract_regions
from vision.detector import find_next_button, find_by_keyword
from automation import input as inp

CLICK_WAIT = 2.0


def click_at(x: int, y: int, wait: float = CLICK_WAIT) -> None:
    """Mục đích: Click tại (x, y) và chờ trang phản hồi."""
    inp.click(x, y)
    time.sleep(wait)


def click_search_result(index: int = 0) -> bool:
    """
    Mục đích: Click vào kết quả tìm kiếm thứ N trên trang Google.
    Phương pháp: OCR tìm "facebook.com" → sort theo y → click index thứ N.
    Bỏ qua top 20% màn hình để tránh search bar.
    """
    img = capture_fullscreen()
    screen_h = img.size[1]
    top_limit = int(screen_h * 0.20)
    regions = extract_regions(img)

    fb_regions = [
        r for r in find_by_keyword(regions, "facebook.com")
        if r.y > top_limit
    ]
    fb_regions.sort(key=lambda r: r.y)

    if not fb_regions:
        print("[nav] Không tìm thấy kết quả Facebook nào")
        return False

    if index >= len(fb_regions):
        print(f"[nav] Index {index} vượt quá số kết quả ({len(fb_regions)})")
        return False

    target = fb_regions[index]
    print(f"[nav] Click result #{index}: '{target.text}' tại ({target.center_x}, {target.center_y})")
    inp.click(target.center_x, target.center_y)
    time.sleep(2.0)
    return True


def go_to_next_page() -> bool:
    """
    Mục đích: Chuyển sang trang kết quả tiếp theo.
    Phương pháp: Scroll xuống → OCR tìm nút Next → click → verify.
    """
    _scroll_to_bottom()
    time.sleep(0.5)

    img_before = capture_fullscreen()
    regions = extract_regions(img_before)

    next_btn = find_next_button(regions)
    if not next_btn:
        print("[nav] Không tìm thấy nút Next — hết trang")
        return False

    print(f"[nav] Click Next: '{next_btn.text}' tại ({next_btn.center_x}, {next_btn.center_y})")
    inp.click(next_btn.center_x, next_btn.center_y)
    time.sleep(2.5)

    img_after = capture_fullscreen()
    changed = compare_screenshots(img_before, img_after)
    print(f"[nav] {'✅ Chuyển trang thành công' if changed else '⚠️  Trang không thay đổi'}")
    return changed


def _scroll_to_bottom() -> None:
    """Mục đích: Cuộn xuống cuối trang để nút Next hiện ra."""
    cx, cy = pyautogui.size()
    pyautogui.moveTo(cx // 2, cy // 2)
    for _ in range(5):
        pyautogui.press("pagedown")
        time.sleep(0.2)
    print("[nav] Cuộn xuống cuối trang")


def _scroll_to_top() -> None:
    """Mục đích: Cuộn lên đầu trang."""
    pyautogui.hotkey("ctrl", "Home")
    time.sleep(0.3)


def get_all_result_positions(screen_h: int) -> list[tuple[int, int]]:
    """
    Mục đích: Lấy tọa độ tất cả result Facebook trên trang.
    Bỏ qua top 20% màn hình (search bar).
    Dedup result gần nhau theo y.
    """
    img = capture_fullscreen()
    top_limit = int(screen_h * 0.20)
    regions = extract_regions(img)

    fb_regions = [
        r for r in find_by_keyword(regions, "facebook.com")
        if r.y > top_limit
    ]
    fb_regions.sort(key=lambda r: r.y)

    positions = []
    last_y = -999
    for r in fb_regions:
        if r.y - last_y > 30:
            positions.append((r.center_x, r.center_y))
            last_y = r.y

    print(f"[nav] Tìm thấy {len(positions)} result Facebook")
    return positions
