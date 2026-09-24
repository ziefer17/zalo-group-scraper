# automation/input.py
# Mục đích: Mouse và keyboard control
# Phương pháp: pyautogui — hoạt động trên Windows và Linux X11

import pyautogui
import time

# Tốc độ di chuyển chuột (giây)
MOVE_DURATION = 0.2


def move_to(x: int, y: int) -> None:
    """Mục đích: Di chuyển chuột đến tọa độ (x, y)."""
    pyautogui.moveTo(x, y, duration=MOVE_DURATION)


def click(x: int, y: int, delay: float = 0.1) -> None:
    """Mục đích: Di chuyển chuột đến (x, y) và click trái."""
    pyautogui.moveTo(x, y, duration=MOVE_DURATION)
    time.sleep(delay)
    pyautogui.click()
    print(f"[input] Click tại ({x}, {y})")


def ctrl_click(x: int, y: int) -> None:
    """
    Mục đích: Ctrl+Click vào (x, y) để mở link trong tab mới.
    Phương pháp: pyautogui.keyDown('ctrl') → click → keyUp('ctrl').
    """
    pyautogui.moveTo(x, y, duration=MOVE_DURATION)
    time.sleep(0.1)
    pyautogui.keyDown('ctrl')
    time.sleep(0.05)
    pyautogui.click()
    time.sleep(0.05)
    pyautogui.keyUp('ctrl')
    print(f"[input] Ctrl+Click tại ({x}, {y})")


def scroll_down(x: int, y: int, steps: int = 5) -> None:
    """
    Mục đích: Scroll xuống tại vị trí (x, y).
    Phương pháp: pyautogui.scroll() — số âm = scroll xuống.
    """
    pyautogui.moveTo(x, y, duration=MOVE_DURATION)
    time.sleep(0.1)
    pyautogui.scroll(-steps)
    print(f"[input] Scroll down {steps} tại ({x}, {y})")


def scroll_up(x: int, y: int, steps: int = 5) -> None:
    """Mục đích: Scroll lên tại vị trí (x, y)."""
    pyautogui.moveTo(x, y, duration=MOVE_DURATION)
    time.sleep(0.1)
    pyautogui.scroll(steps)
    print(f"[input] Scroll up {steps} tại ({x}, {y})")


def screen_center() -> tuple[int, int]:
    """Mục đích: Lấy tọa độ giữa màn hình."""
    w, h = pyautogui.size()
    return w // 2, h // 2
