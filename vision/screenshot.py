# vision/screenshot.py
# Mục đích: Chụp màn hình (toàn bộ hoặc 1 vùng) và lưu file để debug
# Phương pháp: pyautogui.screenshot() — hoạt động trên cả Windows và Linux X11

import pyautogui
from PIL import Image
from datetime import datetime
from pathlib import Path

SCREENSHOT_DIR = Path("debug_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def capture_fullscreen(save: bool = False) -> Image.Image:
    """
    Mục đích: Chụp toàn bộ màn hình, trả về PIL Image.
    save=True thì lưu file .png có timestamp vào debug_screenshots/
    """
    img = pyautogui.screenshot()

    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOT_DIR / f"full_{timestamp}.png"
        img.save(path)
        print(f"[screenshot] Đã lưu: {path}")

    print(f"[screenshot] Kích thước màn hình: {img.size[0]}x{img.size[1]} px")
    return img


def capture_region(x: int, y: int, width: int, height: int, save: bool = False) -> Image.Image:
    """
    Mục đích: Chụp một vùng chỉ định trên màn hình.
    Phương pháp: Chụp toàn màn hình rồi crop theo tọa độ.
    """
    full = pyautogui.screenshot()
    region = full.crop((x, y, x + width, y + height))

    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOT_DIR / f"region_{timestamp}.png"
        region.save(path)
        print(f"[screenshot] Đã lưu vùng: {path}")

    print(f"[screenshot] Vùng chụp: x={x} y={y} w={width} h={height}")
    return region


def compare_screenshots(img_before: Image.Image, img_after: Image.Image, threshold: float = 0.02) -> bool:
    """
    Mục đích: So sánh 2 screenshot để phát hiện trang đã thay đổi chưa.
    Phương pháp: Tính tỷ lệ pixel khác nhau — vượt ngưỡng thì coi là trang mới.
    """
    import numpy as np

    if img_before.size != img_after.size:
        img_after = img_after.resize(img_before.size)

    arr_before = np.array(img_before.convert("RGB"))
    arr_after  = np.array(img_after.convert("RGB"))

    diff = np.any(arr_before != arr_after, axis=2)
    ratio = diff.sum() / diff.size

    changed = ratio > threshold
    print(f"[screenshot] So sánh: {ratio:.2%} pixel thay đổi → {'ĐÃ ĐỔI' if changed else 'CHƯA ĐỔI'}")
    return changed
