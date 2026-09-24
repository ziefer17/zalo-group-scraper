# vision/detector.py
# Mục đích: Nhận danh sách TextRegion từ OCR, tìm các element cụ thể theo keyword
# Phương pháp: Gom region thành dòng → strip space → regex tìm Zalo URL

import re
from vision.ocr import TextRegion, MergedLine, merge_regions_into_lines


# Các nhãn nút "Trang kế tiếp" trên Facebook
NEXT_PAGE_LABELS = [
    "Tiếp theo", "tiếp theo", "Tiếp", "tiếp", "next", "›", ">>",
    "xem thêm kết quả", "more results", "next page", "trang tiếp"
]

# Regex tìm Zalo group URL — xử lý các biến thể OCR bị lỗi:
#   "zalo.me/g/abc123"         → chuẩn
#   "zalo. me/g/abc123"        → space sau dấu chấm (đã clean ở merge)
#   "zalo .me/g/abc123"        → space trước dấu chấm (đã clean ở merge)
#   "https://zalo.me/g/abc123" → có https
#   "zalo.me/g/abc..."         → bị cắt ngắn (truncated)
#
# Pattern: tìm "zalo" + "." + "me" + "/" + "g" + "/" + phần ID (nếu có)
ZALO_URL_PATTERN = re.compile(
    r'(?:https?://)?'           # http:// hoặc https:// (tuỳ chọn)
    r'zalo\.me/g/'              # domain cố định
    r'([A-Za-z0-9_\-]{4,})?',  # group ID — ít nhất 4 ký tự, None nếu bị cắt
    re.IGNORECASE
)

# Regex detect mảnh Zalo — dùng để gom các word fragment trước khi build URL
# Khớp với bất kỳ mảnh nào của URL: "zalo", "zalo.me", "/g/", "zalo.me/g"
ZALO_FRAGMENT_PATTERN = re.compile(
    r'zalo|zalo\.me|/g/|zalo\.me/g',
    re.IGNORECASE
)


def find_zalo_in_lines(regions: list[TextRegion]) -> list[tuple[str, MergedLine]]:
    """
    Mục đích: Tìm tất cả Zalo URL (đầy đủ hoặc bị cắt) trong danh sách region.
    Phương pháp:
      1. Gom region thành MergedLine (xử lý URL bị wrap xuống dòng, bị space)
      2. Với mỗi dòng, chạy regex ZALO_URL_PATTERN trên text đã clean
      3. Trả về list (url_found, merged_line) để caller biết tọa độ để click

    Trả về list tuple:
      - url_found: chuỗi URL tìm được (có thể bị cắt — kết thúc bằng "...")
      - merged_line: MergedLine chứa tọa độ để click vào post nếu cần
    """
    lines = merge_regions_into_lines(regions)
    results = []

    for line in lines:
        # Bỏ space giữa các ký tự một lần nữa cho chắc — OCR đôi khi thêm space lạ
        text_clean = re.sub(r'\s*([./:@])\s*', r'\1', line.text)

        matches = ZALO_URL_PATTERN.finditer(text_clean)
        for m in matches:
            url = m.group(0)
            group_id = m.group(1)

            # Bỏ qua match rỗng (chỉ khớp prefix mà không có gì)
            if not url or len(url) < 10:
                continue

            # Đánh dấu truncated nếu không có group ID hoặc ID quá ngắn
            if not group_id or len(group_id) < 4:
                url = url.rstrip('/') + "/..."

            # Đảm bảo có https://
            if not url.startswith("http"):
                url = "https://" + url

            results.append((url, line))
            print(f"[detector] Zalo URL: '{url}' tại ({line.center_x}, {line.center_y})")

    # Thử thêm: gom 2 dòng liên tiếp nếu dòng trên có "zalo" mà không có "/g/"
    # Xử lý trường hợp URL bị wrap: dòng 1 = "zalo.me" | dòng 2 = "/g/abc123"
    results += _find_zalo_across_lines(lines)

    if not results:
        print("[detector] Không tìm thấy Zalo URL nào")

    return results


def _find_zalo_across_lines(lines: list[MergedLine]) -> list[tuple[str, MergedLine]]:
    """
    Mục đích: Xử lý trường hợp URL bị wrap xuống 2 dòng khác nhau.
    Phương pháp: Nếu dòng N có "zalo" và dòng N+1 có "/g/" → nối lại thành URL.
    Chỉ gom nếu 2 dòng cách nhau dưới 30px theo Y (thực sự cùng 1 URL).
    """
    results = []
    for i in range(len(lines) - 1):
        line_a = lines[i]
        line_b = lines[i + 1]

        # Khoảng cách dọc giữa 2 dòng
        y_gap = line_b.y - (line_a.y + line_a.h)
        if y_gap > 30:
            continue

        has_zalo = "zalo" in line_a.text.lower()
        has_g    = "/g/" in line_b.text.lower() or "g/" in line_b.text.lower()

        if has_zalo and has_g:
            # Nối 2 dòng, bỏ space
            combined = re.sub(r'\s', '', line_a.text + line_b.text)
            m = ZALO_URL_PATTERN.search(combined)
            if m:
                url = m.group(0)
                group_id = m.group(1)
                if not group_id:
                    url = url.rstrip('/') + "/..."
                if not url.startswith("http"):
                    url = "https://" + url

                # Dùng tọa độ dòng đầu để click
                results.append((url, line_a))
                print(f"[detector] Zalo URL (2 dòng): '{url}' tại ({line_a.center_x}, {line_a.center_y})")

    return results


def find_by_keyword(regions: list[TextRegion], keyword: str, partial: bool = True) -> list[TextRegion]:
    """
    Mục đích: Tìm tất cả TextRegion có chứa keyword (không phân biệt hoa thường).
    """
    keyword_lower = keyword.lower()
    results = []
    for region in regions:
        text_lower = region.text.lower()
        match = keyword_lower in text_lower if partial else keyword_lower == text_lower
        if match:
            results.append(region)
    print(f"[detector] Tìm '{keyword}': {len(results)} kết quả")
    return results


def find_next_button(regions: list[TextRegion]) -> TextRegion | None:
    """
    Mục đích: Tìm nút chuyển sang trang kết quả tiếp theo.
    """
    for label in NEXT_PAGE_LABELS:
        matches = find_by_keyword(regions, label)
        if matches:
            btn = matches[-1]
            print(f"[detector] Tìm thấy nút Next: '{btn.text}' tại ({btn.center_x}, {btn.center_y})")
            return btn
    print("[detector] Không tìm thấy nút Next")
    return None



def find_search_results(regions: list[TextRegion]) -> list[TextRegion]:
    """
    Mục đích: Nhóm các TextRegion thành các khối kết quả tìm kiếm.
    """
    RESULT_DOMAINS = ["facebook.com", "fb.com", "zalo.me", "m.facebook.com"]
    result_regions = []
    for domain in RESULT_DOMAINS:
        result_regions.extend(find_by_keyword(regions, domain))

    seen = set()
    unique = []
    for r in result_regions:
        key = (r.x, r.y)
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"[detector] Tìm thấy {len(unique)} search result entries")
    return unique


def print_all_regions(regions: list[TextRegion]) -> None:
    """
    Mục đích: In toàn bộ danh sách TextRegion ra console để debug.
    """
    print(f"\n{'='*60}")
    print(f"TỔNG SỐ REGION: {len(regions)}")
    print(f"{'='*60}")
    for i, r in enumerate(regions):
        print(f"[{i:03d}] ({r.x:4d},{r.y:4d}) {r.w:3d}x{r.h:3d}  conf={r.conf:5.1f}  '{r.text}'")
    print(f"{'='*60}\n")
