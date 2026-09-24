# vision/ocr.py
# Mục đích: Nhận PIL Image → tiền xử lý → chạy Tesseract → trả về text và tọa độ các vùng
# Phương pháp: Grayscale + adaptive threshold để tăng độ tương phản trước khi OCR

import re
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
from dataclasses import dataclass, field


@dataclass
class TextRegion:
    """
    Mục đích: Đại diện cho 1 vùng text tìm được trên màn hình.
    Lưu cả tọa độ lẫn nội dung để detector.py có thể dùng để click.
    """
    x: int       # tọa độ góc trên-trái trên màn hình gốc
    y: int
    w: int       # chiều rộng vùng text
    h: int       # chiều cao vùng text
    text: str    # nội dung text OCR nhận ra
    conf: float  # độ tin cậy (0–100), lọc bỏ các vùng quá thấp

    @property
    def center_x(self) -> int:
        """Tọa độ x trung tâm — dùng để PyAutoGUI click"""
        return self.x + self.w // 2

    @property
    def center_y(self) -> int:
        """Tọa độ y trung tâm — dùng để PyAutoGUI click"""
        return self.y + self.h // 2

    def __repr__(self):
        return f"TextRegion('{self.text[:30]}' @ ({self.x},{self.y}) conf={self.conf:.0f})"


@dataclass
class MergedLine:
    """
    Mục đích: Đại diện cho 1 dòng text đã được gom từ nhiều TextRegion liền nhau.
    Phương pháp: Gom các region có y gần nhau và x liên tiếp → nối text lại.
    Dùng để detect Zalo URL bị cắt thành nhiều word hoặc xuống dòng.
    """
    text: str              # toàn bộ text của dòng, đã nối, không khoảng trắng thừa
    regions: list          # danh sách TextRegion gốc tạo ra dòng này
    x: int                 # tọa độ x đầu dòng
    y: int                 # tọa độ y đầu dòng
    w: int                 # chiều rộng tổng
    h: int                 # chiều cao tổng

    @property
    def center_x(self) -> int:
        return self.x + self.w // 2

    @property
    def center_y(self) -> int:
        return self.y + self.h // 2

    def __repr__(self):
        return f"MergedLine('{self.text[:50]}' @ ({self.x},{self.y}))"


# Ngôn ngữ OCR: tiếng Việt + tiếng Anh — quan trọng vì Facebook có cả 2
OCR_LANG = "vie+eng"

# Ngưỡng confidence tối thiểu để giữ lại một text region
MIN_CONFIDENCE = 30

# Khoảng cách tối đa (pixel) giữa 2 region để coi là cùng dòng theo trục Y
LINE_Y_TOLERANCE = 10

# Khoảng cách tối đa (pixel) giữa 2 region để coi là liền nhau theo trục X
LINE_X_GAP = 80


def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Mục đích: Tăng chất lượng ảnh trước khi OCR.
    Phương pháp: Grayscale → contrast → sharpen → scale 2x.
    Giữ đơn giản — scipy adaptive threshold gây noise và artifact trên màn hình browser.
    Scale 2x đủ để Tesseract nhận font 12-14px trên browser.
    """
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    return img


def preprocess_url_region(img: Image.Image) -> Image.Image:
    """
    Mục đích: Preprocessing mạnh hơn cho vùng ảnh nhỏ chứa URL.
    Scale 4x + contrast cao hơn — tối ưu cho monospace URL text.
    """
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    w, h = img.size
    img = img.resize((w * 4, h * 4), Image.LANCZOS)
    return img


def extract_text(img: Image.Image) -> str:
    """
    Mục đích: OCR toàn bộ ảnh, trả về chuỗi text thuần.
    Dùng để scan nhanh — phát hiện có 'zalo.me/g/' không trước khi làm gì nặng hơn.
    """
    processed = preprocess_image(img)
    text = pytesseract.image_to_string(processed, lang=OCR_LANG, config="--psm 6")
    print(f"[ocr] Đã extract text: {len(text)} ký tự")
    return text


def extract_regions(img: Image.Image, offset_x: int = 0, offset_y: int = 0) -> list[TextRegion]:
    """
    Mục đích: OCR ảnh và trả về danh sách TextRegion có tọa độ thực trên màn hình.
    Phương pháp: Dùng image_to_data() của pytesseract — trả về từng word với bounding box.
    offset_x/y: tọa độ góc trên-trái của ảnh trên màn hình thực — dùng khi capture_region().
    """
    processed = preprocess_image(img)

    data = pytesseract.image_to_data(
        processed,
        lang=OCR_LANG,
        config="--psm 6",
        output_type=pytesseract.Output.DICT
    )

    regions = []
    n = len(data["text"])

    for i in range(n):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])

        if not text or conf < MIN_CONFIDENCE:
            continue

        # Tọa độ từ Tesseract là tương đối trong ảnh đã scale 2x → chia 2 về gốc
        x = data["left"][i]   // 2 + offset_x
        y = data["top"][i]    // 2 + offset_y
        w = data["width"][i]  // 2
        h = data["height"][i] // 2

        regions.append(TextRegion(x=x, y=y, w=w, h=h, text=text, conf=conf))

    print(f"[ocr] Tìm thấy {len(regions)} text region (conf >= {MIN_CONFIDENCE})")
    return regions


def merge_regions_into_lines(regions: list[TextRegion]) -> list[MergedLine]:
    """
    Mục đích: Gom các TextRegion rời nhau thành các dòng liên tục.
    Phương pháp:
      1. Sắp xếp region theo y (trên xuống) rồi x (trái sang phải)
      2. Nhóm region có y gần nhau (± LINE_Y_TOLERANCE) vào cùng 1 dòng
      3. Trong mỗi dòng, gom tiếp các region x liên tiếp (gap <= LINE_X_GAP)
      4. Nối text lại, bỏ khoảng trắng thừa giữa các mảnh URL

    Xử lý được các trường hợp:
      - "zalo." + "me/g/" + "abc123"  → "zalo.me/g/abc123"
      - "https" + "zalo." + "me/g/"   → "httpszalo.me/g/"  (regex sẽ clean)
      - URL xuống 2 dòng              → 2 MergedLine riêng, detect từng dòng
    """
    if not regions:
        return []

    # Bước 1: Sắp xếp theo y trước, x sau
    sorted_regions = sorted(regions, key=lambda r: (r.y, r.x))

    # Bước 2: Nhóm theo dòng (y gần nhau)
    lines_raw: list[list[TextRegion]] = []
    current_line: list[TextRegion] = [sorted_regions[0]]

    for r in sorted_regions[1:]:
        prev = current_line[-1]
        # Cùng dòng nếu y trung tâm chênh lệch nhỏ hơn tolerance
        if abs(r.y - prev.y) <= LINE_Y_TOLERANCE:
            current_line.append(r)
        else:
            lines_raw.append(current_line)
            current_line = [r]
    lines_raw.append(current_line)

    # Bước 3: Trong mỗi dòng, gom tiếp các cụm x liên tiếp thành MergedLine
    merged_lines: list[MergedLine] = []

    for line_regions in lines_raw:
        # Sắp theo x trong dòng
        line_regions = sorted(line_regions, key=lambda r: r.x)

        # Gom cụm x — nếu gap quá lớn thì cắt thành MergedLine mới
        clusters: list[list[TextRegion]] = [[line_regions[0]]]

        for r in line_regions[1:]:
            prev = clusters[-1][-1]
            gap = r.x - (prev.x + prev.w)
            if gap <= LINE_X_GAP:
                clusters[-1].append(r)
            else:
                clusters.append([r])

        # Bước 4: Mỗi cluster → 1 MergedLine
        for cluster in clusters:
            # Nối text, bỏ khoảng trắng — URL không có space
            # Nhưng giữ space nếu không phải URL fragment
            raw_text = " ".join(r.text for r in cluster)

            # Chuẩn hóa: bỏ space giữa các mảnh URL
            # "zalo. me/g/" → "zalo.me/g/"
            # "zalo .me/g/" → "zalo.me/g/"
            # "https ://zalo" → "https://zalo"
            clean_text = re.sub(r'\s+', ' ', raw_text).strip()
            # Bỏ space xung quanh các ký tự URL đặc biệt
            clean_text = re.sub(r'\s*([./:])\s*', r'\1', clean_text)

            x1 = cluster[0].x
            y1 = min(r.y for r in cluster)
            x2 = cluster[-1].x + cluster[-1].w
            y2 = max(r.y + r.h for r in cluster)

            merged_lines.append(MergedLine(
                text=clean_text,
                regions=cluster,
                x=x1,
                y=y1,
                w=x2 - x1,
                h=y2 - y1,
            ))

    print(f"[ocr] Gom thành {len(merged_lines)} merged line từ {len(regions)} region")
    return merged_lines


def regions_to_text(regions: list[TextRegion]) -> str:
    """
    Mục đích: Ghép danh sách TextRegion thành chuỗi text đầy đủ để regex scan.
    Dùng trong extraction/zalo.py để tìm zalo.me/g/ trong toàn bộ kết quả OCR.
    """
    return " ".join(r.text for r in regions)
