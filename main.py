# main.py
# Mục đích: Entry point — chạy UI hoặc CLI
# Cách dùng:
#   python main.py              → mở UI
#   python main.py --cli -k spa -t 100  → chạy CLI không UI

import os
import sys
import shutil

if "DISPLAY" not in os.environ and sys.platform != "win32":
    os.environ["DISPLAY"] = ":0"

def _check_tesseract():
    """Kiểm tra Tesseract đã cài chưa — hiện thông báo rõ nếu chưa."""
    import pytesseract
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        if sys.platform == "win32":
            msg = (
                "Tesseract chưa được cài đặt!\n\n"
                "Tải tại: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "Trong installer, tích thêm 'Vietnamese' language data."
            )
        else:
            msg = (
                "Tesseract chưa được cài đặt!\n\n"
                "Chạy: sudo pacman -S tesseract tesseract-data-vie tesseract-data-eng"
            )
        import tkinter.messagebox as mb
        import tkinter as tk
        r = tk.Tk(); r.withdraw()
        mb.showerror("Thiếu Tesseract", msg)
        r.destroy()
        return False

def run_ui():
    if not _check_tesseract():
        sys.exit(1)
    from ui.main_window import run
    run()

def run_cli():
    import argparse
    from pathlib import Path
    from automation.search_runner import SearchRunner

    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", "-k", default="spa")
    parser.add_argument("--target",  "-t", type=int, default=100)
    parser.add_argument("--output",  "-o", default="zalo_groups.txt")
    parser.add_argument("--min-wait", type=float, default=0.0)
    parser.add_argument("--max-wait", type=float, default=5.0)
    args = parser.parse_args()

    print(f"Zalo Group Finder CLI")
    print(f"  Keyword : {args.keyword}")
    print(f"  Target  : {args.target}")
    print(f"  Output  : {args.output}")
    print(f"\n⚠️  Click vào Chrome trong vòng 5 giây sau khi nhấn Enter!")
    input("Nhấn Enter để bắt đầu...")

    runner = SearchRunner(
        keyword=args.keyword,
        target=args.target,
        output_file=Path(args.output),
        min_wait=args.min_wait,
        max_wait=args.max_wait,
    )
    runner.run()

if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        run_cli()
    else:
        run_ui()
