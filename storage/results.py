# storage/results.py
# Mục đích: Lưu trữ Zalo URL đã tìm được, dedup, ghi ra file txt
# Phương pháp: Set để dedup trong memory, file txt mỗi dòng 1 URL
# Format file: 1 URL/dòng, không có header, không có metadata
#   https://zalo.me/g/abc123
#   https://zalo.me/g/xyz999
#   ...

from pathlib import Path
from extraction.zalo import ZaloURL

# File lưu kết quả — chỉ COMPLETE URL, mỗi dòng 1 link
DEFAULT_OUTPUT_FILE = Path("zalo_groups.txt")

# Auto-save sau mỗi N URL mới được thêm
AUTO_SAVE_EVERY = 10


class ResultStore:
    """
    Mục đích: Quản lý toàn bộ URL đã tìm được trong 1 run.
    Tự động load từ file nếu file đã tồn tại — resume được run dang dở.
    Tự động save sau mỗi AUTO_SAVE_EVERY URL mới — tránh mất dữ liệu khi crash.
    """

    def __init__(self, output_file: Path = DEFAULT_OUTPUT_FILE):
        self.output_file = output_file

        # Set chứa group_id đã có — dùng để dedup O(1)
        self._seen_ids: set[str] = set()

        # List URL theo thứ tự tìm thấy — dùng để export
        self._urls: list[str] = []

        # Đếm số URL mới kể từ lần save cuối
        self._unsaved_count = 0

        # Load từ file nếu đã tồn tại — resume run dang dở
        self._load()

    def _load(self) -> None:
        """
        Mục đích: Load URL từ file txt khi khởi động.
        Cho phép resume run bị interrupt — không bị mất URL đã tìm.
        """
        if not self.output_file.exists():
            print(f"[store] File mới: {self.output_file}")
            return

        loaded = 0
        with open(self.output_file, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if not url or not url.startswith("https://zalo.me/g/"):
                    continue
                gid = self._extract_id(url)
                if gid and gid not in self._seen_ids:
                    self._seen_ids.add(gid)
                    self._urls.append(url)
                    loaded += 1

        print(f"[store] Đã load {loaded} URL từ {self.output_file}")

    def _extract_id(self, url: str) -> str | None:
        """Mục đích: Trích group_id từ URL để dedup."""
        import re
        m = re.search(r'/g/([a-z0-9_\-]{4,})$', url)
        return m.group(1) if m else None

    def _save(self) -> None:
        """
        Mục đích: Ghi toàn bộ URL ra file txt — ghi đè hoàn toàn.
        Mỗi dòng 1 URL, không có ký tự thừa.
        """
        with open(self.output_file, "w", encoding="utf-8") as f:
            for url in self._urls:
                f.write(url + "\n")
        print(f"[store] Đã lưu {len(self._urls)} URL → {self.output_file}")

    def add(self, zalo_url: ZaloURL) -> bool:
        """
        Mục đích: Thêm 1 URL vào store nếu chưa có.
        Chỉ nhận COMPLETE URL — TRUNCATED bỏ qua (chưa có ID đầy đủ).
        Trả về True nếu URL mới, False nếu duplicate.
        Auto-save sau mỗi AUTO_SAVE_EVERY URL mới.
        """
        if zalo_url.status != "COMPLETE":
            return False

        gid = zalo_url.group_id
        if not gid:
            return False

        if gid in self._seen_ids:
            print(f"[store] Duplicate: '{zalo_url.url}'")
            return False

        # URL mới — thêm vào
        self._seen_ids.add(gid)
        self._urls.append(zalo_url.url)
        self._unsaved_count += 1

        print(f"[store] ✅ Thêm #{len(self._urls)}: '{zalo_url.url}'")

        # Auto-save
        if self._unsaved_count >= AUTO_SAVE_EVERY:
            self._save()
            self._unsaved_count = 0

        return True

    def add_url(self, url: str) -> bool:
        """
        Mục đích: Thêm URL dạng string thay vì ZaloURL object.
        Tiện dụng khi gọi từ SearchRunner.
        """
        from extraction.zalo import ZaloURL
        return self.add(ZaloURL(url=url, status="COMPLETE", source_text=""))

    def save(self) -> None:
        """Mục đích: Force save ngay lập tức — gọi khi kết thúc run."""
        self._save()
        self._unsaved_count = 0

    @property
    def count(self) -> int:
        """Số URL unique đã tìm được."""
        return len(self._urls)

    @property
    def urls(self) -> list[str]:
        """Danh sách URL theo thứ tự tìm thấy."""
        return list(self._urls)

    def progress(self, target: int) -> str:
        """
        Mục đích: Trả về chuỗi thống kê tiến độ để in ra console.
        Ví dụ: "[store] Tiến độ: 45/100 (45.0%)"
        """
        pct = self.count / target * 100 if target > 0 else 0
        return f"[store] Tiến độ: {self.count}/{target} ({pct:.1f}%)"

    def is_done(self, target: int) -> bool:
        """Mục đích: Kiểm tra đã đủ target chưa."""
        return self.count >= target
