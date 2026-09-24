# automation/clipboard.py
# Mục đích: Lấy URL từ browser bằng clipboard
# Phương pháp: pyautogui.hotkey() gửi keypress + pyperclip đọc clipboard
# Hoạt động trên: Windows và Linux X11

import re
import time
import pyautogui
import pyperclip
from urllib.parse import unquote

CLIPBOARD_SETTLE_WAIT = 0.5


def focus_chrome() -> bool:
    """
    Mục đích: Focus Chrome window bằng cách click vào nó.
    Trên X11/Windows pyautogui tự handle focus — không cần hyprctl.
    Trả về True luôn vì không cần verify trên X11.
    """
    # Trên X11 chỉ cần đảm bảo Chrome đang có focus
    # Caller nên đảm bảo Chrome đang ở foreground trước khi gọi
    print("[clipboard] Focus Chrome")
    return True


def _wtype_key(modifier: str, key: str) -> None:
    """
    Mục đích: Gửi tổ hợp phím qua pyautogui.hotkey().
    Thay thế wtype trên Wayland — pyautogui hoạt động trên X11/Windows.
    """
    pyautogui.hotkey(modifier, key)
    time.sleep(0.05)


def read_clipboard() -> str:
    """Mục đích: Đọc clipboard bằng pyperclip — hoạt động trên X11/Windows."""
    try:
        content = pyperclip.paste().strip()
        print(f"[clipboard] Đọc được: '{content[:80]}'")
        return content
    except Exception as e:
        print(f"[clipboard] Lỗi đọc clipboard: {e}")
        return ""


def copy_page_text_ctrlA(initial_wait: float = 0) -> str:
    """
    Mục đích: Lấy toàn bộ text trang bằng Ctrl+A → Ctrl+C → pyperclip.
    initial_wait: giây chờ trước khi gửi keypress — dùng lần đầu để người dùng
                  kịp click vào Chrome. Các lần sau (trong loop) không cần chờ.
    """
    if initial_wait > 0:
        print(f"[clipboard] Chờ {initial_wait:.0f}s — click vào Chrome ngay...")
        time.sleep(initial_wait)

    pyperclip.copy("")
    time.sleep(0.1)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(CLIPBOARD_SETTLE_WAIT)

    text = read_clipboard()
    print(f"[clipboard] Ctrl+A lấy được {len(text)} ký tự")
    return text


def copy_from_address_bar() -> str | None:
    """
    Mục đích: Lấy URL trang hiện tại từ address bar.
    Phương pháp: Ctrl+L → Ctrl+A → Ctrl+C → Escape.
    """
    pyperclip.copy("")
    time.sleep(0.1)

    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(CLIPBOARD_SETTLE_WAIT)
    pyautogui.press("escape")
    time.sleep(0.2)

    url = read_clipboard()
    if url and url.startswith("http"):
        print(f"[clipboard] Address bar: '{url}'")
        return url

    print("[clipboard] Address bar không trả về URL hợp lệ")
    return None


def find_zalo_in_text(text: str) -> list[str]:
    """
    Mục đích: Tìm tất cả Zalo URL trong text từ Ctrl+A clipboard.
    Phương pháp: Regex trực tiếp + window compress cho URL bị tách.
    """
    if not text:
        return []

    decoded = unquote(text)
    found_urls: list[str] = []

    for m in re.finditer(r'https?://zalo\.me/g/([a-z0-9_\-]{4,})', decoded):
        url = f"https://zalo.me/g/{m.group(1)}"
        found_urls.append(url)

    for zalo_match in re.finditer(r'zalo', decoded, re.IGNORECASE):
        start = zalo_match.start()
        window = decoded[max(0, start - 10): start + 80]
        slash_g = re.search(r'/g/', window, re.IGNORECASE)
        if slash_g:
            rest = window[slash_g.end():]
            id_match = re.match(r'[a-z0-9_\-]{4,}', rest.strip())
            if id_match:
                url = f"https://zalo.me/g/{id_match.group(0)}"
                if url not in found_urls:
                    found_urls.append(url)

    seen: set[str] = set()
    unique = [u for u in found_urls if not (u in seen or seen.add(u))]  # type: ignore
    return unique


def extract_zalo_from_clipboard(raw: str) -> str | None:
    """Mục đích: Trích xuất Zalo URL từ chuỗi raw — xử lý Facebook redirect."""
    if not raw:
        return None
    decoded = unquote(raw)
    m = re.search(r'https?://zalo\.me/g/([a-z0-9_\-]+)', decoded)
    if m:
        return f"https://zalo.me/g/{m.group(1)}"
    return None
