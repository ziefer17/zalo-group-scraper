# test_vision.py
# Mục đích: Kiểm tra toàn bộ Phase 2 — chụp màn hình, OCR, detect, vẽ bounding box
# Phương pháp: Chạy từng bước và in kết quả ra console, lưu ảnh debug có bounding box

import time
import pyautogui
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

from vision.screenshot import capture_fullscreen, capture_region, compare_screenshots
from vision.ocr import extract_text, extract_regions, regions_to_text, merge_regions_into_lines
from vision.detector import (
    find_zalo_in_lines,
    find_next_button,
    print_all_regions,
)

DEBUG_DIR = Path("debug_screenshots")
DEBUG_DIR.mkdir(exist_ok=True)


def draw_bounding_boxes(img: Image.Image, regions, output_path: str) -> None:
    """
    Mục đích: Vẽ bounding box màu xanh lá lên ảnh để kiểm tra OCR nhận đúng vùng không.
    Vùng chứa 'zalo.me/g/' sẽ được tô màu đỏ để phân biệt.
    """
    draw = ImageDraw.Draw(img.copy())
    result = img.copy()
    draw = ImageDraw.Draw(result)

    for r in regions:
        # Màu đỏ nếu là Zalo URL, xanh lá cho các region thường
        color = "red" if "zalo.me" in r.text.lower() else "lime"
        draw.rectangle([r.x, r.y, r.x + r.w, r.y + r.h], outline=color, width=2)

        # Label nhỏ phía trên bounding box
        label = r.text[:20] + "..." if len(r.text) > 20 else r.text
        draw.text((r.x, max(0, r.y - 12)), label, fill=color)

    result.save(output_path)
    print(f"[test] Đã lưu ảnh debug: {output_path}")


def test_fullscreen_ocr():
    """
    Mục đích: Test cơ bản — chụp toàn màn hình và OCR toàn bộ.
    Bước 1: Xác nhận pipeline screenshot → OCR hoạt động.
    """
    print("\n" + "="*60)
    print("TEST 1: Fullscreen OCR")
    print("="*60)

    # Chụp màn hình và lưu bản gốc
    img = capture_fullscreen(save=True)

    # Extract text thuần để scan nhanh
    raw_text = extract_text(img)
    print(f"\n--- Raw text (200 ký tự đầu) ---\n{raw_text[:200]}\n")

    # Extract regions có tọa độ
    regions = extract_regions(img)
    print_all_regions(regions)

    # Lưu ảnh có bounding box
    draw_bounding_boxes(img, regions, str(DEBUG_DIR / "test1_bboxes.png"))


def test_zalo_detection():
    """
    Mục đích: Test phát hiện Zalo URL trong kết quả tìm kiếm.
    Bước 2: Mở browser, vào trang search có Zalo link rồi chạy test này.
    Phương pháp mới: gom region thành dòng → strip space → regex tìm URL.
    Xử lý được: URL bị space, bị wrap xuống dòng, bị cắt ngắn.
    """
    print("\n" + "="*60)
    print("TEST 2: Zalo URL Detection (merged lines)")
    print("="*60)
    print("Hãy mở browser đến trang có chứa zalo.me/g/ trước...")
    time.sleep(3)

    img = capture_fullscreen(save=True)
    regions = extract_regions(img)

    # In tất cả region để debug — xem OCR nhận ra những gì
    print_all_regions(regions)

    # In các merged line để thấy kết quả gom
    lines = merge_regions_into_lines(regions)
    print(f"\n--- MERGED LINES ({len(lines)} dòng) ---")
    for i, line in enumerate(lines):
        print(f"[{i:03d}] '{line.text}'")
    print("---\n")

    # Tìm Zalo URL từ các dòng đã gom
    found = find_zalo_in_lines(regions)

    if found:
        print(f"\n✅ Tìm thấy {len(found)} Zalo URL:")
        for url, line in found:
            status = "TRUNCATED" if url.endswith("...") else "COMPLETE"
            print(f"   [{status}] '{url}'  →  click tại ({line.center_x}, {line.center_y})")
    else:
        print("\n⚠️  Không tìm thấy Zalo URL nào trên màn hình hiện tại")

    draw_bounding_boxes(img, regions, str(DEBUG_DIR / "test2_zalo.png"))


def test_next_button():
    """
    Mục đích: Test phát hiện nút Next / Tiếp theo trên trang kết quả tìm kiếm.
    Bước 3: Mở trang search results rồi chạy test này.
    """
    print("\n" + "="*60)
    print("TEST 3: Next Button Detection")
    print("="*60)
    print("Hãy mở browser đến trang search results...")
    time.sleep(3)

    img = capture_fullscreen(save=True)
    regions = extract_regions(img)

    btn = find_next_button(regions)
    if btn:
        print(f"\n✅ Nút Next: '{btn.text}' → click tại ({btn.center_x}, {btn.center_y})")
    else:
        print("\n⚠️  Không tìm thấy nút Next")

    draw_bounding_boxes(img, regions, str(DEBUG_DIR / "test3_next.png"))


def test_page_change():
    """
    Mục đích: Test so sánh 2 screenshot để phát hiện trang đã chuyển.
    Bước 4: Xác nhận compare_screenshots() hoạt động đúng.
    """
    print("\n" + "="*60)
    print("TEST 4: Page Change Detection")
    print("="*60)

    print("Chụp screenshot A...")
    img_a = capture_fullscreen()

    print("Chờ 3 giây — hãy chuyển trang hoặc cuộn trong lúc này...")
    time.sleep(3)

    print("Chụp screenshot B...")
    img_b = capture_fullscreen()

    from vision.screenshot import compare_screenshots
    changed = compare_screenshots(img_a, img_b)
    print(f"\n{'✅ Trang đã thay đổi' if changed else '⚠️  Trang không thay đổi'}")


def test_checkpoint_detection():
    """
    Mục đích: Test này đã bị bỏ — detect_checkpoint gây false positive với
    text bình thường như "Log in", "Đăng nhập" trên trang Facebook/Google.
    Checkpoint detection đã bị xóa khỏi project.
    """
    print("\n" + "="*60)
    print("TEST 5: Checkpoint detection — ĐÃ BỎ")
    print("="*60)
    print("Checkpoint detector bị xóa vì false positive quá nhiều.")
    print("Tool sẽ chạy liên tục không dừng giữa chừng.")


def test_clipboard_extract(mock: bool = True):
    """
    Mục đích: Test extract_zalo_from_clipboard() — xử lý các dạng URL clipboard trả về.
    mock=True: chạy với chuỗi giả — không cần browser.
    mock=False: đọc clipboard thực — copy 1 link Zalo vào clipboard trước khi chạy.
    """
    print("\n" + "="*60)
    print("TEST 6: Clipboard Zalo URL Extraction")
    print("="*60)

    from automation.clipboard import extract_zalo_from_clipboard

    if mock:
        # Các case thực tế clipboard có thể trả về
        test_cases = [
            # URL trực tiếp — đơn giản nhất
            ("https://zalo.me/g/rimxkg652",
             "https://zalo.me/g/rimxkg652"),

            # Facebook redirect URL — clipboard thường trả dạng này
            ("https://l.facebook.com/l.php?u=https%3A%2F%2Fzalo.me%2Fg%2Fabc123xyz&h=AT...",
             "https://zalo.me/g/abc123xyz"),

            # URL có tracking param
            ("https://zalo.me/g/rimxkg652?utm_source=fb&utm_medium=post",
             "https://zalo.me/g/rimxkg652"),

            # Không phải Zalo URL
            ("https://www.facebook.com/groups/123456",
             None),
        ]

        all_pass = True
        for raw, expected in test_cases:
            result = extract_zalo_from_clipboard(raw)
            ok = result == expected
            all_pass = all_pass and ok
            status = "✅" if ok else "❌"
            print(f"{status} Input:    '{raw[:60]}'")
            print(f"   Expected: {expected}")
            print(f"   Got:      {result}\n")

        print(f"\n{'✅ Tất cả test case pass' if all_pass else '❌ Có test case thất bại'}")

    else:
        # Đọc clipboard thực — copy 1 link Zalo vào clipboard trước
        import pyperclip
        raw = pyperclip.paste().strip()
        print(f"Clipboard hiện tại: '{raw}'")
        result = extract_zalo_from_clipboard(raw)
        print(f"Zalo URL: {result}")


def test_ctrlA_search_result():
    """
    Mục đích: Ctrl+A toàn bộ text trang search result → parse → tìm Zalo URL.
    Workflow:
      hyprctl focus Chrome → wtype Ctrl+A → wtype Ctrl+C → wl-paste → parse

    Hướng dẫn:
      1. Mở Chrome, search: site:facebook.com "zalo.me/g/" spa
      2. Chạy test 7 — script tự focus Chrome và Ctrl+A, không cần làm gì thêm
    """
    print("\n" + "="*60)
    print("TEST 7: Ctrl+A search result → tìm Zalo URL")
    print("="*60)
    print("Đảm bảo Chrome đang mở trang search result...")
    print("Script tự focus Chrome sau 3 giây\n")
    time.sleep(3)

    from automation.clipboard import copy_page_text_ctrlA, find_zalo_in_text

    raw_text = copy_page_text_ctrlA()
    if not raw_text:
        print("❌ Clipboard rỗng")
        return

    print(f"\n--- TEXT ({len(raw_text)} ký tự, 300 đầu) ---")
    print(raw_text[:300])
    print("---\n")

    urls = find_zalo_in_text(raw_text)

    if urls:
        print(f"\n✅ Tìm thấy {len(urls)} Zalo URL:")
        for url in urls:
            status = "TRUNCATED" if url.endswith("...") else "COMPLETE"
            print(f"   [{status}] {url}")
    else:
        print("\n⚠️  Không tìm thấy Zalo URL")



def test_zalo_extractor():
    """
    Mục đích: Test Phase 3 — extract_all() phân loại COMPLETE/TRUNCATED đúng không.
    Phương pháp: Chạy với text mẫu (mock) — không cần browser.
    """
    print("\n" + "="*60)
    print("TEST 8: Zalo Extractor (mock)")
    print("="*60)

    from extraction.zalo import extract_all, normalize_url

    # Test normalize_url
    print("--- normalize_url ---")
    cases = [
        "http://zalo.me/g/abc123?utm_source=fb",
        "zalo.me/g/abc123",
        "https://zalo.me/g/ABC123",  # uppercase → lowercase
        "https://l.facebook.com/l.php?u=https%3A%2F%2Fzalo.me%2Fg%2Fxyz999",
    ]
    for c in cases:
        print(f"  IN:  '{c}'")
        print(f"  OUT: '{normalize_url(c)}'\n")

    # Test extract_all với text thực tế
    print("--- extract_all ---")
    sample_text = """
    Kết quả tìm kiếm cho zalo.me/g/ spa

    Nhóm Spa Hà Nội - Tham gia: https://zalo.me/g/ce8ecqtjvco0ky1gwvzv Sau khi
    tham gia bạn sẽ nhận được ưu đãi.

    Spa Quận 1 https://zalo.me/g/boxucp252 Facebook group liên kết

    Link nhóm bị cắt: https://zalo.me/g/...

    zalo .me /g/ rimxkg652 (bị tách space)

    https://zalo.me/g/ce8ecqtjvco0ky1gwvzv (duplicate — phải bỏ)
    """

    results = extract_all(sample_text)
    print(f"\nKết quả ({len(results)} URL):")
    for r in results:
        print(f"  [{r.status}] {r.url}")
        print(f"           group_id: {r.group_id}")
        print(f"           source: '{r.source_text[:50]}'")


def test_browser_search():
    """
    Mục đích: Test Phase 4 browser.py — mở Chrome và search query.
    Hướng dẫn: Chrome phải đang mở sẵn.
    """
    print("\n" + "="*60)
    print("TEST 9: Browser search")
    print("="*60)
    print("Chrome phải đang mở... script tự focus và search sau 3 giây\n")
    time.sleep(3)

    from automation.browser import open_search
    ok = open_search("spa")
    print(f"\n{'✅ Search thành công' if ok else '❌ Search thất bại'}")


def test_next_page():
    """
    Mục đích: Test Phase 4 navigation.py — click Next page và verify.
    Hướng dẫn: Chrome đang mở trang search result Google.
    """
    print("\n" + "="*60)
    print("TEST 10: Next page navigation")
    print("="*60)
    print("Chrome phải đang mở Google search result... chờ 3 giây\n")
    time.sleep(3)

    from automation.navigation import go_to_next_page
    ok = go_to_next_page()
    print(f"\n{'✅ Chuyển trang thành công' if ok else '❌ Không chuyển được trang'}")


def test_full_pipeline():
    """
    Mục đích: Test toàn bộ pipeline Phase 3+4 — search → Ctrl+A → extract → next page.
    Đây là test gần nhất với SearchRunner thực tế sẽ làm ở Phase 6.
    Hướng dẫn: Chrome đang mở, chưa cần search sẵn.
    """
    print("\n" + "="*60)
    print("TEST 11: Full pipeline (search → extract → next page)")
    print("="*60)
    print("Chrome phải đang mở... chờ 3 giây\n")
    time.sleep(3)

    from automation.browser import open_search
    from automation.clipboard import copy_page_text_ctrlA
    from automation.navigation import go_to_next_page
    from extraction.zalo import extract_all

    # Bước 1: Search
    print("--- Bước 1: Search ---")
    open_search("spa")
    time.sleep(2)

    # Bước 2: Ctrl+A lấy text trang 1
    print("\n--- Bước 2: Ctrl+A trang 1 ---")
    text = copy_page_text_ctrlA()
    results_p1 = extract_all(text)
    print(f"Trang 1: {len(results_p1)} URL")
    for r in results_p1:
        print(f"  [{r.status}] {r.url}")

    # Bước 3: Next page
    print("\n--- Bước 3: Next page ---")
    ok = go_to_next_page()
    if not ok:
        print("Không chuyển được trang — dừng test")
        return

    time.sleep(1)

    # Bước 4: Ctrl+A lấy text trang 2
    print("\n--- Bước 4: Ctrl+A trang 2 ---")
    text2 = copy_page_text_ctrlA()
    results_p2 = extract_all(text2)
    print(f"Trang 2: {len(results_p2)} URL")
    for r in results_p2:
        print(f"  [{r.status}] {r.url}")

    total = len(results_p1) + len(results_p2)
    print(f"\n✅ Tổng 2 trang: {total} Zalo URL")


    """
    Mục đích: Test scroll xuống cuối trang để nút Next hiện ra.
    Phương pháp: focus Chrome → pyautogui press End → chụp screenshot so sánh.
    Hướng dẫn: Chrome mở Google search result, chạy test này.
    """
    print("\n" + "="*60)
    print("TEST 12: Scroll down")
    print("="*60)
    print("Chrome phải đang mở Google search result... chờ 3 giây\n")
    time.sleep(3)

    from automation.clipboard import focus_chrome
    from vision.screenshot import capture_fullscreen, compare_screenshots
    from vision.ocr import extract_regions
    from vision.detector import find_next_button

    # Chụp trước khi scroll
    focus_chrome()
    time.sleep(0.3)
    img_before = capture_fullscreen(save=True)
    print("Screenshot trước khi scroll đã chụp")

    # Scroll xuống cuối trang bằng End
    print("Gửi phím End...")
    pyautogui.press("end")
    time.sleep(1.0)

    # Chụp sau khi scroll
    img_after = capture_fullscreen(save=True)
    changed = compare_screenshots(img_before, img_after)
    print(f"Trang có thay đổi sau scroll: {'✅ CÓ' if changed else '❌ KHÔNG'}")

    # OCR tìm nút Next sau khi đã scroll xuống
    print("\nOCR tìm nút Next...")
    regions = extract_regions(img_after)
    btn = find_next_button(regions)

    if btn:
        print(f"✅ Tìm thấy nút Next: '{btn.text}' tại ({btn.center_x}, {btn.center_y})")
    else:
        print("⚠️  Vẫn không thấy nút Next — thử scroll thêm hoặc zoom out trang")
        # Thử scroll thêm 3 lần nữa
        print("Scroll thêm 3 lần bằng Space...")
        for i in range(3):
            pyautogui.press("space")
            time.sleep(0.4)

        img_final = capture_fullscreen(save=True)
        regions2 = extract_regions(img_final)
        btn2 = find_next_button(regions2)
        if btn2:
            print(f"✅ Tìm thấy sau scroll thêm: '{btn2.text}' tại ({btn2.center_x}, {btn2.center_y})")
        else:
            print("❌ Vẫn không thấy — in toàn bộ region để debug:")
            print_all_regions(regions2)
    """
    Mục đích: Test toàn bộ pipeline Phase 3+4 — search → Ctrl+A → extract → next page.
    Đây là test gần nhất với SearchRunner thực tế sẽ làm ở Phase 6.
    Hướng dẫn: Chrome đang mở, chưa cần search sẵn.
    """
    print("\n" + "="*60)
    print("TEST 11: Full pipeline (search → extract → next page)")
    print("="*60)
    print("Chrome phải đang mở... chờ 3 giây\n")
    time.sleep(3)

    from automation.browser import open_search
    from automation.clipboard import copy_page_text_ctrlA
    from automation.navigation import go_to_next_page
    from extraction.zalo import extract_all

    # Bước 1: Search
    print("--- Bước 1: Search ---")
    open_search("spa")
    time.sleep(2)

    # Bước 2: Ctrl+A lấy text trang 1
    print("\n--- Bước 2: Ctrl+A trang 1 ---")
    text = copy_page_text_ctrlA()
    results_p1 = extract_all(text)
    print(f"Trang 1: {len(results_p1)} URL")
    for r in results_p1:
        print(f"  [{r.status}] {r.url}")

    # Bước 3: Next page
    print("\n--- Bước 3: Next page ---")
    ok = go_to_next_page()
    if not ok:
        print("Không chuyển được trang — dừng test")
        return

    time.sleep(1)

    # Bước 4: Ctrl+A lấy text trang 2
    print("\n--- Bước 4: Ctrl+A trang 2 ---")
    text2 = copy_page_text_ctrlA()
    results_p2 = extract_all(text2)
    print(f"Trang 2: {len(results_p2)} URL")
    for r in results_p2:
        print(f"  [{r.status}] {r.url}")

    total = len(results_p1) + len(results_p2)
    print(f"\n✅ Tổng 2 trang: {total} Zalo URL")


def test_scroll_down():
    """
    Mục đích: Test scroll xuống cuối trang để nút Next hiện ra.
    Phương pháp: focus Chrome → wtype Page_Down → chụp screenshot so sánh.
    pyautogui.press/scroll không hoạt động trên Hyprland — dùng wtype thay thế.
    Hướng dẫn: Chrome mở Google search result, chạy test này.
    """
    print("\n" + "="*60)
    print("TEST 12: Scroll down")
    print("="*60)
    print("Chrome phải đang mở Google search result... chờ 3 giây\n")
    time.sleep(3)

    import os
    import subprocess
    from automation.clipboard import focus_chrome
    from vision.screenshot import capture_fullscreen, compare_screenshots
    from vision.ocr import extract_regions
    from vision.detector import find_next_button

    _env = {**os.environ, "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", "wayland-1")}

    # Chụp trước khi scroll
    focus_chrome()
    time.sleep(0.3)
    img_before = capture_fullscreen(save=True)
    print("Screenshot trước khi scroll đã chụp")

    # Scroll xuống bằng wtype Page_Down
    print("Gửi Page_Down x5...")
    for _ in range(5):
        subprocess.run(["wtype", "-k", "Page_Down"], capture_output=True, env=_env)
        time.sleep(0.2)
    time.sleep(0.5)

    # Chụp sau khi scroll
    img_after = capture_fullscreen(save=True)
    changed = compare_screenshots(img_before, img_after)
    print(f"Trang có thay đổi sau scroll: {'✅ CÓ' if changed else '❌ KHÔNG'}")

    # OCR tìm nút Next sau khi đã scroll xuống
    print("\nOCR tìm nút Next...")
    regions = extract_regions(img_after)
    btn = find_next_button(regions)

    if btn:
        print(f"✅ Tìm thấy nút Next: '{btn.text}' tại ({btn.center_x}, {btn.center_y})")
    else:
        print("⚠️  Vẫn không thấy nút Next — thử scroll thêm 5 lần nữa")
        for _ in range(5):
            subprocess.run(["wtype", "-k", "Page_Down"], capture_output=True, env=_env)
            time.sleep(0.2)

        img_final = capture_fullscreen(save=True)
        regions2 = extract_regions(img_final)
        btn2 = find_next_button(regions2)
        if btn2:
            print(f"✅ Tìm thấy sau scroll thêm: '{btn2.text}' tại ({btn2.center_x}, {btn2.center_y})")
        else:
            print("❌ Vẫn không thấy — in toàn bộ region để debug:")
            print_all_regions(regions2)


def test_ydotool():
    """
    Mục đích: Test ydotool click, scroll, và next page trên Chrome thật.
    Chạy từng bước riêng để debug chính xác cái nào hoạt động.
    Hướng dẫn: Chrome đang mở Google search result.
    """
    print("\n" + "="*60)
    print("TEST 15: ydotool click / scroll / next page")
    print("="*60)
    print("Chrome phải đang mở Google search result...")
    print("Chọn bước muốn test:")
    print("  a - Click giữa màn hình")
    print("  b - Scroll xuống")
    print("  c - Click vào result đầu tiên (OCR)")
    print("  d - Next page (scroll + OCR + click)")

    step = input("Chọn (a/b/c/d): ").strip().lower()
    print(f"\nChờ 3 giây — chuyển sang Chrome...\n")
    time.sleep(3)

    from automation import input as inp
    from automation.clipboard import focus_chrome

    if step == "a":
        # Test click giữa màn hình
        cx, cy = inp.screen_center()
        print(f"Screen center từ hyprctl: ({cx}, {cy})")
        focus_chrome()
        time.sleep(0.3)
        inp.click(cx, cy)
        print("✅ Click xong — chuột có di chuyển đúng chỗ không?")

    elif step == "b":
        # Test scroll xuống
        cx, cy = inp.screen_center()
        focus_chrome()
        time.sleep(0.3)
        print(f"Scroll xuống tại ({cx}, {cy})...")
        for _ in range(3):
            inp.scroll_down(cx, cy, steps=5)
            time.sleep(0.3)
        print("✅ Scroll xong — trang có cuộn không?")

    elif step == "c":
        # Test click vào result đầu tiên
        from automation.navigation import click_search_result
        ok = click_search_result(index=0)
        print(f"\n{'✅ Click thành công' if ok else '❌ Không tìm thấy result'}")

    elif step == "d":
        # Test next page đầy đủ
        from automation.navigation import go_to_next_page
        ok = go_to_next_page()
        print(f"\n{'✅ Chuyển trang thành công' if ok else '❌ Không chuyển được'}")
    """
    Mục đích: Test Phase 5 — ResultStore dedup, save, load từ txt.
    Mock — không cần browser.
    """
    print("\n" + "="*60)
    print("TEST 13: Result Store (mock)")
    print("="*60)

    import tempfile
    from pathlib import Path
    from storage.results import ResultStore
    from extraction.zalo import ZaloURL

    tmp_path = Path("test_store_tmp.txt")

    store = ResultStore(output_file=tmp_path)

    urls = [
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/xyz999", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="duplicate"),
        ZaloURL(url="https://zalo.me/g/...",    status="TRUNCATED", source_text="truncated"),
    ]

    results = [store.add(u) for u in urls]
    print(f"\nThêm 4 URL:")
    print(f"  abc123 (mới)   : {'✅ thêm' if results[0] else '❌'}")
    print(f"  xyz999 (mới)   : {'✅ thêm' if results[1] else '❌'}")
    print(f"  abc123 (dup)   : {'✅ bỏ qua đúng' if not results[2] else '❌ thêm nhầm'}")
    print(f"  truncated      : {'✅ bỏ qua đúng' if not results[3] else '❌ thêm nhầm'}")
    print(f"\nStore count: {store.count} (expected: 2)")

    store.save()
    store2 = ResultStore(output_file=tmp_path)
    print(f"Load lại từ file: {store2.count} URL (expected: 2)")
    print(f"URLs: {store2.urls}")
    print(f"\n{store.progress(target=10)}")

    tmp_path.unlink(missing_ok=True)
    print("\n✅ Test store xong")


def test_truncated_post():
    """
    Mục đích: Test workflow mở post có truncated link → lấy URL đầy đủ → back.
    Hướng dẫn:
      1. Mở Chrome, search: site:facebook.com "zalo.me/g/" spa
      2. Scroll đến thấy 1 result có link bị cắt "zalo.me/g/abc..."
      3. Chạy test này — script tự tìm result đó và xử lý
    """
    print("\n" + "="*60)
    print("TEST 16: Truncated link → mở post → lấy URL đầy đủ → back")
    print("="*60)
    print("Chrome phải đang mở search result có link truncated...")
    print("Chờ 3 giây\n")
    time.sleep(3)

    from automation.clipboard import copy_page_text_ctrlA
    from extraction.zalo import extract_all
    from automation.search_runner import SearchRunner

    # Bước 1: Ctrl+A lấy text trang search result
    print("--- Bước 1: Ctrl+A trang search result ---")
    text = copy_page_text_ctrlA()
    if not text:
        print("❌ Không lấy được text")
        return

    # Bước 2: Extract — tìm TRUNCATED URL
    print("\n--- Bước 2: Extract URLs ---")
    found = extract_all(text)
    truncated = [u for u in found if u.status == "TRUNCATED"]
    complete  = [u for u in found if u.status == "COMPLETE"]

    print(f"COMPLETE:  {len(complete)}")
    for u in complete:
        print(f"  {u.url}")
    print(f"TRUNCATED: {len(truncated)}")
    for u in truncated:
        print(f"  source: '{u.source_text[:60]}'")

    if not truncated:
        print("\n⚠️  Không có URL truncated trên trang này")
        print("Thử trang khác hoặc search khác keyword")
        return

    # Bước 3: Mở post cho URL truncated đầu tiên
    print(f"\n--- Bước 3: Mở post cho truncated URL đầu tiên ---")
    runner = SearchRunner.__new__(SearchRunner)
    runner.posts_opened = 0

    result = runner._get_url_from_post(truncated[0])

    if result:
        print(f"\n✅ Lấy được URL đầy đủ: '{result}'")
    else:
        print("\n❌ Không lấy được URL đầy đủ từ post")
    """
    Mục đích: Test Phase 5 — ResultStore dedup, save, load từ txt.
    Mock — không cần browser.
    """
    print("\n" + "="*60)
    print("TEST 13: Result Store (mock)")
    print("="*60)

    from pathlib import Path
    from storage.results import ResultStore
    from extraction.zalo import ZaloURL

    tmp_path = Path("test_store_tmp.txt")
    store = ResultStore(output_file=tmp_path)

    urls = [
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/xyz999", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="duplicate"),
        ZaloURL(url="https://zalo.me/g/...",    status="TRUNCATED", source_text="truncated"),
    ]

    results = [store.add(u) for u in urls]
    print(f"\nThêm 4 URL:")
    print(f"  abc123 (mới)   : {'✅ thêm' if results[0] else '❌'}")
    print(f"  xyz999 (mới)   : {'✅ thêm' if results[1] else '❌'}")
    print(f"  abc123 (dup)   : {'✅ bỏ qua đúng' if not results[2] else '❌ thêm nhầm'}")
    print(f"  truncated      : {'✅ bỏ qua đúng' if not results[3] else '❌ thêm nhầm'}")
    print(f"\nStore count: {store.count} (expected: 2)")

    store.save()
    store2 = ResultStore(output_file=tmp_path)
    print(f"Load lại từ file: {store2.count} URL (expected: 2)")
    print(f"URLs: {store2.urls}")
    print(f"\n{store.progress(target=10)}")

    tmp_path.unlink(missing_ok=True)
    print("\n✅ Test store xong")


def test_new_workflow():
    """
    Mục đích: Test workflow mới — Ctrl+Click result → tab mới → extract → Ctrl+W.
    Hướng dẫn: Chrome mở sẵn — runner tự search sau delay 5s.
    """
    print("\n" + "="*60)
    print("TEST 17: Workflow mới — Ctrl+Click tab mới (target=20)")
    print("="*60)

    from pathlib import Path
    from automation.search_runner import SearchRunner

    tmp = Path("test_new_workflow_output.txt")

    # Xóa file cũ để test từ đầu
    if tmp.exists():
        tmp.unlink()
        print(f"Đã xóa file cũ: {tmp}")

    runner = SearchRunner(keyword="spa", target=20, output_file=tmp)
    runner.run()

    if tmp.exists():
        content = tmp.read_text(encoding="utf-8").strip()
        urls = [l for l in content.splitlines() if l.strip()]
        print(f"\nFile output ({len(urls)} URL):")
        for url in urls:
            print(f"  {url}")
    """
    Mục đích: Test Phase 5 — ResultStore dedup, save, load từ txt. Mock.
    """
    print("\n" + "="*60)
    print("TEST 13: Result Store (mock)")
    print("="*60)

    from pathlib import Path
    from storage.results import ResultStore
    from extraction.zalo import ZaloURL

    tmp_path = Path("test_store_tmp.txt")
    store = ResultStore(output_file=tmp_path)

    urls = [
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/xyz999", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="duplicate"),
        ZaloURL(url="https://zalo.me/g/...",    status="TRUNCATED", source_text="truncated"),
    ]

    results = [store.add(u) for u in urls]
    print(f"  abc123 (mới)   : {'✅ thêm' if results[0] else '❌'}")
    print(f"  xyz999 (mới)   : {'✅ thêm' if results[1] else '❌'}")
    print(f"  abc123 (dup)   : {'✅ bỏ qua đúng' if not results[2] else '❌ thêm nhầm'}")
    print(f"  truncated      : {'✅ bỏ qua đúng' if not results[3] else '❌ thêm nhầm'}")
    print(f"Store count: {store.count} (expected: 2)")

    store.save()
    store2 = ResultStore(output_file=tmp_path)
    print(f"Load lại: {store2.count} URL (expected: 2)")
    print(f"URLs: {store2.urls}")
    print(f"{store.progress(target=10)}")

    tmp_path.unlink(missing_ok=True)
    print("✅ Test store xong")


def test_result_store():
    """
    Mục đích: Test Phase 5 — ResultStore dedup, save, load từ txt. Mock.
    """
    print("\n" + "="*60)
    print("TEST 13: Result Store (mock)")
    print("="*60)

    from pathlib import Path
    from storage.results import ResultStore
    from extraction.zalo import ZaloURL

    tmp_path = Path("test_store_tmp.txt")
    store = ResultStore(output_file=tmp_path)

    urls = [
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/xyz999", status="COMPLETE",  source_text="test"),
        ZaloURL(url="https://zalo.me/g/abc123", status="COMPLETE",  source_text="duplicate"),
        ZaloURL(url="https://zalo.me/g/...",    status="TRUNCATED", source_text="truncated"),
    ]

    results = [store.add(u) for u in urls]
    print(f"  abc123 (mới)   : {'✅ thêm' if results[0] else '❌'}")
    print(f"  xyz999 (mới)   : {'✅ thêm' if results[1] else '❌'}")
    print(f"  abc123 (dup)   : {'✅ bỏ qua đúng' if not results[2] else '❌ thêm nhầm'}")
    print(f"  truncated      : {'✅ bỏ qua đúng' if not results[3] else '❌ thêm nhầm'}")
    print(f"Store count: {store.count} (expected: 2)")

    store.save()
    store2 = ResultStore(output_file=tmp_path)
    print(f"Load lại: {store2.count} URL (expected: 2)")
    print(f"URLs: {store2.urls}")
    print(f"{store.progress(target=10)}")

    tmp_path.unlink(missing_ok=True)
    print("✅ Test store xong")


def test_search_runner():
    """
    Mục đích: Test Phase 6 — SearchRunner chạy thật với Chrome, target nhỏ.
    Hướng dẫn: Chrome đang mở — runner tự search sau 3 giây.
    """
    print("\n" + "="*60)
    print("TEST 14: Search Runner (target=5)")
    print("="*60)
    print("Chrome phải đang mở... runner tự search sau 3 giây\n")
    time.sleep(3)

    from pathlib import Path
    from automation.search_runner import SearchRunner

    tmp = Path("test_runner_output.txt")
    runner = SearchRunner(keyword="spa", target=10, output_file=tmp)
    runner.run()

    if tmp.exists():
        print(f"\nNội dung {tmp}:")
        print(tmp.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print("🔍 Zalo Group Finder — Full Test Suite")
    print("Chọn test muốn chạy:")
    print("  1  - Fullscreen OCR")
    print("  2  - Zalo URL detection (cần browser)")
    print("  3  - Next button detection (cần browser)")
    print("  4  - Page change detection")
    print("  5  - Checkpoint detection (đã bỏ)")
    print("  6  - Clipboard URL extraction (mock)")
    print("  7  - Ctrl+A search result (cần Chrome)")
    print("  8  - Zalo extractor (mock)")
    print("  9  - Browser search (cần Chrome)")
    print("  10 - Next page navigation (cần Chrome)")
    print("  11 - Full pipeline (cần Chrome)")
    print("  12 - Scroll down (cần Chrome)")
    print("  13 - Result store (mock) ← Phase 5")
    print("  14 - Search runner target=5 (cần Chrome) ← Phase 6")
    print("  15 - ydotool click/scroll/next page (cần Chrome)")
    print("  16 - Truncated link → mở post → URL đầy đủ → back (cần Chrome)")
    print("  17 - Workflow mới Ctrl+Click tab mới target=5 (cần Chrome)")
    print("  all - Chạy test không cần browser (1, 6, 8, 13)")

    choice = input("\nNhập lựa chọn: ").strip().lower()

    tests = {
        "1":  test_fullscreen_ocr,
        "2":  test_zalo_detection,
        "3":  test_next_button,
        "4":  test_page_change,
        "5":  test_checkpoint_detection,
        "6":  test_clipboard_extract,
        "7":  test_ctrlA_search_result,
        "8":  test_zalo_extractor,
        "9":  test_browser_search,
        "10": test_next_page,
        "11": test_full_pipeline,
        "12": test_scroll_down,
        "13": test_result_store,
        "14": test_search_runner,
        "15": test_ydotool,
        "16": test_truncated_post,
        "17": test_new_workflow,
    }

    if choice in tests:
        tests[choice]()
    elif choice == "all":
        test_fullscreen_ocr()
        test_clipboard_extract()
        test_zalo_extractor()
        test_result_store()
        print("\n⚠️  Test 2,3,4,7,9,10,11,12,14 cần Chrome — chạy riêng")
    else:
        print("Lựa chọn không hợp lệ")
    print("Chọn test muốn chạy:")
    print("  1  - Fullscreen OCR")
    print("  2  - Zalo URL detection (merged lines, cần browser)")
    print("  3  - Next button detection (cần browser)")
    print("  4  - Page change detection")
    print("  5  - Checkpoint detection (mock)")
    print("  6  - Clipboard URL extraction (mock)")
    print("  7  - Ctrl+A search result (cần Chrome mở search)")
    print("  8  - Zalo extractor (mock) ← Phase 3")
    print("  9  - Browser search ← Phase 4")
    print("  10 - Next page navigation ← Phase 4")
    print("  11 - Full pipeline search→extract→next ← Phase 3+4")
    print("  12 - Scroll down test ← Phase 4")
    print("  all - Chạy test không cần browser (1, 5, 6, 8)")

    choice = input("\nNhập lựa chọn: ").strip().lower()

    tests = {
        "1": test_fullscreen_ocr,
        "2": test_zalo_detection,
        "3": test_next_button,
        "4": test_page_change,
        "5": test_checkpoint_detection,
        "6": test_clipboard_extract,
        "7": test_ctrlA_search_result,
        "8": test_zalo_extractor,
        "9": test_browser_search,
        "10": test_next_page,
        "11": test_full_pipeline,
        "12": test_scroll_down,
    }

    if choice in tests:
        tests[choice]()
    elif choice == "all":
        test_fullscreen_ocr()
        test_checkpoint_detection()
        test_clipboard_extract()
        test_zalo_extractor()
        print("\n⚠️  Test 2,3,4,7,9,10,11 cần browser — chạy riêng từng cái")
    else:
        print("Lựa chọn không hợp lệ")
