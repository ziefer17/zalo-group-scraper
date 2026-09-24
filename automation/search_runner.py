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


class SearchRunner:
    def __init__(
        self,
        keyword: str,
        target: int = 100,
        output_file: Path = Path("zalo_groups.txt"),
        min_wait: float = 0.0,
        max_wait: float = 5.0,
        on_progress=None,  # callback(count, total, url) để update UI
    ):
        if not (TARGET_MIN <= target <= TARGET_MAX):
            raise ValueError(f"Target phải từ {TARGET_MIN} đến {TARGET_MAX}")

        self.keyword    = keyword
        self.target     = target
        self.store      = ResultStore(output_file)
        self.min_wait   = min_wait
        self.max_wait   = max_wait
        self.on_progress = on_progress

        self.pages_scanned = 0
        self.running       = True  # set False để dừng giữa chừng

    def stop(self):
        """Mục đích: Dừng loop từ bên ngoài (nút Stop trên UI)."""
        self.running = False

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

            # Random wait giữa các trang
            wait = random.uniform(self.min_wait, self.max_wait)
            if wait > 0:
                print(f"Chờ {wait:.1f}s trước trang tiếp...")
                time.sleep(wait)

            if not go_to_next_page():
                print("⚠️  Hết trang — dừng")
                break

        self.store.save()
        self._print_summary()

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
