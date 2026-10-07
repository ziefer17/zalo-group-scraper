# automation/search_runner.py
# Mục đích: Vòng lặp chính — search → Ctrl+A → extract → next page → lặp đến target
# Workflow đơn giản: không Ctrl+Click, chỉ lấy link từ snippet

import time
import random
import pyautogui
from pathlib import Path

from automation.browser import open_search, scroll_down
from automation.clipboard import copy_page_text_ctrlA
from automation.navigation import go_to_next_page, _scroll_to_top
from extraction.zalo import extract_all
from storage.results import ResultStore

TARGET_MIN = 10
TARGET_MAX = 99999

# Sau bao nhiêu trang thì nghỉ dài để tránh captcha
PAGES_BEFORE_BREAK = 7
# Default break time range (giây)
BREAK_MIN_DEFAULT = 5 * 60   # 5 phút
BREAK_MAX_DEFAULT = 6 * 60   # 6 phút


class SearchRunner:
    def __init__(
        self,
        keyword: str,
        target: int = 100,
        output_file: Path = Path("zalo_groups.txt"),
        min_wait: float = 0.0,
        max_wait: float = 5.0,
        break_min: float = BREAK_MIN_DEFAULT,
        break_max: float = BREAK_MAX_DEFAULT,
        on_progress=None,
        on_break=None,   # callback(remaining_seconds) để update UI countdown
    ):
        if not (TARGET_MIN <= target <= TARGET_MAX):
            raise ValueError(f"Target phải từ {TARGET_MIN} đến {TARGET_MAX}")

        self.keyword   = keyword
        self.target    = target
        self.store     = ResultStore(output_file)
        self.min_wait  = min_wait
        self.max_wait  = max_wait
        self.break_min = break_min
        self.break_max = break_max
        self.on_progress = on_progress
        self.on_break    = on_break

        self.pages_scanned = 0
        self.running       = True  # set False để dừng giữa chừng

    def stop(self):
        """Mục đích: Dừng loop từ bên ngoài (nút Stop trên UI)."""
        self.running = False

    def resume(self) -> None:
        """
        Mục đích: Tiếp tục từ trang hiện tại sau khi giải captcha.
        Khác run(): không gọi open_search() — giữ nguyên trang đang mở.
        Chờ 5s để user kịp click vào Chrome.
        """
        print(f"\n{'='*60}")
        print(f"RESUME — tiếp tục từ trang hiện tại")
        print(f"Đã có: {self.store.count}/{self.target} URL")
        print(f"{'='*60}\n")

        if self.store.is_done(self.target):
            print("✅ Đã đủ target")
            return

        self.running = True

        # Chờ user switch sang Chrome
        print("Chờ 5s — click vào Chrome ngay...")
        import time as _time
        _time.sleep(5)

        # Tiếp tục loop từ trang hiện tại
        while self.running and not self.store.is_done(self.target):
            print(f"\n--- Trang {self.pages_scanned + 1} ---")
            self._process_page()
            self.pages_scanned += 1
            print(self.store.progress(self.target))

            if self.store.is_done(self.target) or not self.running:
                break

            if self.pages_scanned % PAGES_BEFORE_BREAK == 0:
                break_secs = random.uniform(self.break_min, self.break_max)
                print(f"\n⏸️  Nghỉ {break_secs/60:.1f} phút để tránh captcha...")
                self._do_break(break_secs)
                if not self.running:
                    break

            wait = random.uniform(self.min_wait, self.max_wait)
            if wait > 0:
                print(f"Chờ {wait:.1f}s...")
                import time as _t
                _t.sleep(wait)

            if not go_to_next_page():
                print("⚠️  Hết trang — dừng")
                break

        self.store.save()
        self._print_summary()

    def run(self) -> None:
        """Mục đích: Chạy search loop đến khi đủ target hoặc hết trang."""
        print(f"\n{'='*60}")
        print(f"Keyword: '{self.keyword}' | Target: {self.target}")
        print(f"Đã có: {self.store.count} URL | Wait: {self.min_wait}-{self.max_wait}s")
        print(f"{'='*60}\n")

        if self.store.is_done(self.target):
            print("✅ Đã đủ target từ file trước")
            return

        if not open_search(self.keyword):
            print("❌ Không mở được search")
            return

        time.sleep(2.0)

        while self.running and not self.store.is_done(self.target):
            print(f"\n--- Trang {self.pages_scanned + 1} ---")
            self._process_page()
            self.pages_scanned += 1
            print(self.store.progress(self.target))

            if self.store.is_done(self.target) or not self.running:
                break

            # Anti-captcha: nghỉ dài sau mỗi PAGES_BEFORE_BREAK trang
            if self.pages_scanned % PAGES_BEFORE_BREAK == 0:
                break_secs = random.uniform(self.break_min, self.break_max)
                print(f"\n⏸️  Nghỉ {break_secs/60:.1f} phút để tránh captcha...")
                self._do_break(break_secs)
                if not self.running:
                    break

            # Random wait ngắn giữa các trang
            wait = random.uniform(self.min_wait, self.max_wait)
            if wait > 0:
                print(f"Chờ {wait:.1f}s trước trang tiếp...")
                time.sleep(wait)

            if not go_to_next_page():
                print("⚠️  Hết trang — dừng")
                break

        self.store.save()
        self._print_summary()

    def _do_break(self, seconds: float) -> None:
        """
        Mục đích: Nghỉ dài để tránh captcha — đếm ngược từng giây.
        Gọi on_break(remaining) mỗi giây để UI hiện countdown.
        """
        remaining = int(seconds)
        while remaining > 0 and self.running:
            if self.on_break:
                self.on_break(remaining)
            time.sleep(1)
            remaining -= 1
        if self.on_break:
            self.on_break(0)

    def _process_page(self) -> None:
        """
        Mục đích: Ctrl+A trang hiện tại → extract → lưu link mới.
        """
        _scroll_to_top()
        time.sleep(0.3)

        text = copy_page_text_ctrlA()
        if not text:
            print("[runner] Không lấy được text — bỏ qua trang")
            return

        found = extract_all(text)
        print(f"[runner] Tìm thấy {len(found)} URL trên trang")

        for u in found:
            if not self.running or self.store.is_done(self.target):
                break
            if u.status == "COMPLETE":
                is_new = self.store.add(u)
                if is_new and self.on_progress:
                    self.on_progress(self.store.count, self.target, u.url)

    def _print_summary(self) -> None:
        print(f"\n{'='*60}")
        print(f"✅ KẾT THÚC")
        print(f"   Trang đã scan : {self.pages_scanned}")
        print(f"   URL unique    : {self.store.count}")
        print(f"   File output   : {self.store.output_file}")
        print(f"{'='*60}\n")
