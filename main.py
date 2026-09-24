# main.py
# Mục đích: Entry point — chạy UI hoặc CLI
# Cách dùng:
#   python main.py              → mở UI
#   python main.py --cli -k spa -t 100  → chạy CLI không UI

import os
import sys

if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"

def run_ui():
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
