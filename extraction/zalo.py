# extraction/zalo.py
# Mục đích: Nhận text thô từ clipboard → trả về list ZaloURL có status rõ ràng
# Phương pháp: Wrap logic từ clipboard.find_zalo_in_text() thành object có type,
#              thêm normalize() và dedup theo group ID

import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse


# ID Zalo group: chỉ lowercase + số + gạch ngang/dưới
# Không có uppercase, không có tiếng Việt, không có space
# Dừng ngay khi gặp ký tự không thuộc bộ này
_ID_PATTERN = r'[a-z0-9_\-]{4,}'


@dataclass
class ZaloURL:
    """
    Mục đích: Đại diện cho 1 Zalo group URL tìm được.
    status: COMPLETE = có full ID, TRUNCATED = cần mở post để lấy đầy đủ.
    source_text: đoạn text gốc — dùng để debug khi regex lấy sai.
    """
    url: str            # URL chuẩn hóa: "https://zalo.me/g/abc123"
    status: str         # "COMPLETE" hoặc "TRUNCATED"
    source_text: str    # đoạn text gốc chứa URL này (tối đa 80 ký tự)

    @property
    def group_id(self) -> str | None:
        """
        Mục đích: Trích group ID từ URL — dùng để dedup.
        "https://zalo.me/g/abc123" → "abc123"
        "https://zalo.me/g/..."    → None (TRUNCATED)
        """
        m = re.search(r'/g/([a-z0-9_\-]{4,})$', self.url)
        return m.group(1) if m else None

    def __repr__(self):
        return f"ZaloURL({self.status}, '{self.url}')"


def normalize_url(raw: str) -> str:
    """
    Mục đích: Chuẩn hóa URL Zalo về dạng thống nhất.
    Phương pháp:
      1. URL decode — xử lý Facebook redirect "%2F%2Fzalo.me%2Fg%2F..."
      2. Đảm bảo có https://
      3. Bỏ tracking param (?utm_source=..., ?fbclid=..., v.v.)
      4. Lowercase toàn bộ path (ID là lowercase)

    Ví dụ:
      "http://zalo.me/g/Abc123?utm_source=fb"  → "https://zalo.me/g/abc123"
      "zalo.me/g/abc123"                        → "https://zalo.me/g/abc123"
    """
    decoded = unquote(raw).strip()

    # Thêm https:// nếu thiếu
    if not decoded.startswith("http"):
        decoded = "https://" + decoded

    # Parse URL
    parsed = urlparse(decoded)

    # Lowercase path — ID luôn lowercase
    clean_path = parsed.path.lower()

    # Bỏ hết query param (tracking)
    clean = urlunparse((
        "https",
        "zalo.me",
        clean_path,
        "",   # params
        "",   # query — bỏ hết
        "",   # fragment
    ))

    return clean


def _remove_search_bar_text(text: str) -> str:
    """
    Mục đích: Bỏ phần text search bar ở đầu clipboard.
    Ctrl+A trên Google luôn bắt đầu bằng "Bỏ qua...site:facebook.com zalo.me/g/ <keyword>"
    Phần này không phải kết quả thực — bỏ đi để tránh nhận nhầm thành TRUNCATED.
    Phương pháp: Tìm pattern search bar → cắt bỏ từ đầu đến hết dòng đó.
    """
    # Pattern search bar Google: có "site:facebook.com" hoặc query search
    # Tìm dòng đầu tiên có chứa search query → bỏ đến hết dòng đó
    patterns = [
        r'site:facebook\.com[^\n]*\n',   # "site:facebook.com ..." 
        r'"zalo\.me/g/"[^\n]*\n',         # query có "zalo.me/g/"
        r'Hỗ trợ truy cập[^\n]*\n',       # header accessibility Google
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            # Cắt bỏ từ đầu đến hết match này
            text = text[m.end():]
            break
    return text


def extract_all(text: str) -> list[ZaloURL]:
    """
    Mục đích: Tìm tất cả Zalo URL trong text từ Ctrl+A clipboard.
    Phương pháp 2 bước:
      1. Regex trực tiếp → COMPLETE
      2. Window 80 ký tự quanh "zalo" → compress prefix trước /g/ → lấy ID từ phần sau
         - Chỉ compress phần "https zalo .me /g/" (trước ID)
         - ID bắt đầu sau "/g/" → lấy [a-z0-9_-]+ từ đầu, dừng khi gặp uppercase/space
         - Không compress phần sau ID → tránh nối "Sau khi" vào ID

    Trả về list ZaloURL đã dedup theo group_id, giữ thứ tự tìm thấy.
    """
    if not text:
        return []

    # Bỏ text search bar ở đầu clipboard — tránh nhận nhầm query search thành TRUNCATED
    text = _remove_search_bar_text(text)
    decoded = unquote(text)
    results: list[ZaloURL] = []
    seen_ids: set[str] = set()
    seen_truncated = False

    def _add(url: str, status: str, source: str) -> None:
        """Thêm ZaloURL vào results, dedup theo group_id."""
        normalized = normalize_url(url)
        m = re.search(r'/g/([a-z0-9_\-]{4,})$', normalized)
        gid = m.group(1) if m else None

        if status == "TRUNCATED":
            nonlocal seen_truncated
            if seen_truncated:
                return
            seen_truncated = True
            results.append(ZaloURL(url=normalized, status="TRUNCATED", source_text=source[:80]))
            return

        if gid and gid not in seen_ids:
            seen_ids.add(gid)
            results.append(ZaloURL(url=normalized, status="COMPLETE", source_text=source[:80]))
            print(f"[zalo] COMPLETE: '{normalized}'")

    # Bước 1: Regex trực tiếp — URL đầy đủ không bị tách
    for m in re.finditer(
        r'https?://zalo\.me/g/(' + _ID_PATTERN + r')',
        decoded
    ):
        url = f"https://zalo.me/g/{m.group(1)}"
        _add(url, "COMPLETE", m.group(0))

    # Bước 2: Window compress — xử lý prefix bị tách space/newline
    for zalo_match in re.finditer(r'zalo', decoded, re.IGNORECASE):
        start = zalo_match.start()
        window = decoded[max(0, start - 10): start + 80]

        # Tách tại "/g/" — compress phần trước, giữ nguyên phần sau
        slash_g = re.search(r'/g/', window, re.IGNORECASE)
        if slash_g:
            prefix = window[:slash_g.end()]
            rest   = window[slash_g.end():]

            # Compress prefix: bỏ space giữa "https", "zalo", ".me", "/g/"
            compressed_prefix = re.sub(r'\s+', '', prefix)

            # Đảm bảo prefix đúng pattern sau khi compress
            if not re.search(r'zalo\.me/g/$', compressed_prefix, re.IGNORECASE):
                continue

            # Lấy ID từ đầu phần rest — chỉ lowercase+số, dừng khi gặp uppercase/space
            id_match = re.match(_ID_PATTERN, rest.strip())
            if id_match:
                group_id = id_match.group(0)
                url = f"https://zalo.me/g/{group_id}"
                _add(url, "COMPLETE", window.strip())
            else:
                # Có "/g/" nhưng không lấy được ID → cần mở post
                _add("https://zalo.me/g/...", "TRUNCATED", window.strip())

        else:
            # Không có "/g/" trong window 80 ký tự — URL bị cắt nhiều hơn
            # Compress toàn bộ và thử lại
            compressed = re.sub(r'\s+', '', window)
            m2 = re.search(
                r'(?:https?://)?zalo\.me/g/(' + _ID_PATTERN + r')',
                compressed
            )
            if m2:
                url = f"https://zalo.me/g/{m2.group(1)}"
                _add(url, "COMPLETE", window.strip())

    print(f"[zalo] Tổng: {len(results)} URL ({sum(1 for r in results if r.status=='COMPLETE')} complete, "
          f"{sum(1 for r in results if r.status=='TRUNCATED')} truncated)")
    return results
