# ui/main_window.py
# Mục đích: Giao diện người dùng — dark, compact, monospace
# Phương pháp: tkinter — có sẵn trên cả Windows và Linux

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from pathlib import Path

# ── Màu sắc ────────────────────────────────────────────────
BG          = "#0a0a0a"   # true black background
BG_PANEL    = "#141414"   # panel hơi sáng hơn
BG_INPUT    = "#1a1a1a"   # input background
FG          = "#f0f0f0"   # white text
FG_DIM      = "#555555"   # dimmed text
FG_URL      = "#60a5fa"   # blue — URL links
FG_NEW      = "#34d399"   # green — URL mới tìm được
ACCENT      = "#3b82f6"   # blue accent — nút Start
ACCENT_STOP = "#ef4444"   # red — nút Stop
BORDER      = "#2a2a2a"   # subtle border
FONT_MONO   = ("JetBrains Mono", 9)
FONT_MONO_S = ("JetBrains Mono", 8)
FONT_LABEL  = ("JetBrains Mono", 8)
FONT_BTN    = ("JetBrains Mono", 9, "bold")
FONT_COUNT  = ("JetBrains Mono", 22, "bold")


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Zalo Group Finder")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # State
        self.runner = None
        self.runner_thread = None
        self.output_file = Path("zalo_groups.txt")
        self.url_count = 0

        self._build_ui()
        self._center_window()

    def _build_ui(self):
        root = self.root
        pad = dict(padx=12, pady=4)

        # ── Header ──────────────────────────────────────────
        hdr = tk.Frame(root, bg=BG, pady=8)
        hdr.pack(fill="x", padx=12)

        tk.Label(hdr, text="ZALO GROUP FINDER",
                 font=("JetBrains Mono", 10, "bold"),
                 fg=FG, bg=BG).pack(side="left")

        self.status_dot = tk.Label(hdr, text="●", font=("JetBrains Mono", 10),
                                   fg=FG_DIM, bg=BG)
        self.status_dot.pack(side="right")

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

        # ── Keyword input ───────────────────────────────────
        row1 = tk.Frame(root, bg=BG, pady=8)
        row1.pack(fill="x", padx=12)

        tk.Label(row1, text="keyword", font=FONT_LABEL,
                 fg=FG_DIM, bg=BG).pack(anchor="w")

        self.keyword_var = tk.StringVar(value="spa")
        kw_entry = tk.Entry(row1, textvariable=self.keyword_var,
                            font=FONT_MONO, bg=BG_INPUT, fg=FG,
                            insertbackground=FG, relief="flat",
                            bd=0, highlightthickness=1,
                            highlightbackground=BORDER,
                            highlightcolor=ACCENT, width=30)
        kw_entry.pack(fill="x", pady=(2, 0))

        # ── Target input ────────────────────────────────────
        row2 = tk.Frame(root, bg=BG, pady=4)
        row2.pack(fill="x", padx=12)

        tk.Label(row2, text="target links", font=FONT_LABEL,
                 fg=FG_DIM, bg=BG).pack(anchor="w")

        self.target_var = tk.StringVar(value="100")
        tgt_entry = tk.Entry(row2, textvariable=self.target_var,
                             font=FONT_MONO, bg=BG_INPUT, fg=FG,
                             insertbackground=FG, relief="flat",
                             bd=0, highlightthickness=1,
                             highlightbackground=BORDER,
                             highlightcolor=ACCENT, width=10)
        tgt_entry.pack(anchor="w", pady=(2, 0))

        # ── Wait slider ─────────────────────────────────────
        row3 = tk.Frame(root, bg=BG, pady=4)
        row3.pack(fill="x", padx=12)

        wait_hdr = tk.Frame(row3, bg=BG)
        wait_hdr.pack(fill="x")
        tk.Label(wait_hdr, text="wait between pages",
                 font=FONT_LABEL, fg=FG_DIM, bg=BG).pack(side="left")
        self.wait_label = tk.Label(wait_hdr, text="0 – 5s",
                                   font=FONT_LABEL, fg=FG, bg=BG)
        self.wait_label.pack(side="right")

        slider_frame = tk.Frame(row3, bg=BG)
        slider_frame.pack(fill="x", pady=(4, 0))

        self.wait_min = tk.DoubleVar(value=0)
        self.wait_max = tk.DoubleVar(value=5)

        # Min slider
        tk.Label(slider_frame, text="min", font=FONT_LABEL,
                 fg=FG_DIM, bg=BG, width=3).pack(side="left")
        min_slider = tk.Scale(slider_frame, from_=0, to=10,
                              variable=self.wait_min, orient="horizontal",
                              resolution=0.5, showvalue=False,
                              bg=BG, fg=FG, troughcolor=BG_INPUT,
                              highlightthickness=0, bd=0,
                              activebackground=ACCENT,
                              command=self._update_wait_label)
        min_slider.pack(side="left", fill="x", expand=True)

        # Max slider
        tk.Label(slider_frame, text="max", font=FONT_LABEL,
                 fg=FG_DIM, bg=BG, width=3).pack(side="left")
        max_slider = tk.Scale(slider_frame, from_=0, to=10,
                              variable=self.wait_max, orient="horizontal",
                              resolution=0.5, showvalue=False,
                              bg=BG, fg=FG, troughcolor=BG_INPUT,
                              highlightthickness=0, bd=0,
                              activebackground=ACCENT,
                              command=self._update_wait_label)
        max_slider.pack(side="left", fill="x", expand=True)

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", pady=4)

        # ── Counter ─────────────────────────────────────────
        counter_frame = tk.Frame(root, bg=BG)
        counter_frame.pack(fill="x", padx=12, pady=4)

        self.count_label = tk.Label(counter_frame, text="0",
                                    font=FONT_COUNT, fg=FG, bg=BG)
        self.count_label.pack(side="left")

        count_sub = tk.Frame(counter_frame, bg=BG)
        count_sub.pack(side="left", padx=8)
        tk.Label(count_sub, text="links found", font=FONT_LABEL,
                 fg=FG_DIM, bg=BG).pack(anchor="w")
        self.page_label = tk.Label(count_sub, text="page 0",
                                   font=FONT_LABEL, fg=FG_DIM, bg=BG)
        self.page_label.pack(anchor="w")

        # File path label
        self.file_label = tk.Label(counter_frame, text=str(self.output_file),
                                   font=FONT_MONO_S, fg=FG_DIM, bg=BG,
                                   cursor="hand2")
        self.file_label.pack(side="right")
        self.file_label.bind("<Button-1>", self._choose_output_file)

        # ── URL list panel ───────────────────────────────────
        panel = tk.Frame(root, bg=BG_PANEL, bd=0,
                         highlightthickness=1,
                         highlightbackground=BORDER)
        panel.pack(fill="both", padx=12, pady=4, expand=True)

        self.url_list = tk.Listbox(panel,
                                   font=FONT_MONO_S,
                                   bg=BG_PANEL, fg=FG_URL,
                                   selectbackground=ACCENT,
                                   selectforeground=FG,
                                   relief="flat", bd=0,
                                   highlightthickness=0,
                                   height=12,
                                   activestyle="none")
        self.url_list.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(panel, orient="vertical",
                                 command=self.url_list.yview,
                                 bg=BG_PANEL, troughcolor=BG_PANEL,
                                 width=8)
        scrollbar.pack(side="right", fill="y")
        self.url_list.config(yscrollcommand=scrollbar.set)

        # Double-click copy URL
        self.url_list.bind("<Double-Button-1>", self._copy_selected_url)

        # ── Log line ─────────────────────────────────────────
        self.log_label = tk.Label(root, text="ready",
                                  font=FONT_MONO_S, fg=FG_DIM, bg=BG,
                                  anchor="w")
        self.log_label.pack(fill="x", padx=12, pady=(2, 4))

        # ── Buttons ───────────────────────────────────────────
        btn_frame = tk.Frame(root, bg=BG, pady=8)
        btn_frame.pack(fill="x", padx=12)

        self.start_btn = tk.Button(btn_frame, text="START",
                                   font=FONT_BTN,
                                   bg=ACCENT, fg=FG,
                                   activebackground="#2563eb",
                                   activeforeground=FG,
                                   relief="flat", bd=0,
                                   padx=16, pady=6,
                                   cursor="hand2",
                                   command=self._on_start)
        self.start_btn.pack(side="left")

        self.stop_btn = tk.Button(btn_frame, text="STOP",
                                  font=FONT_BTN,
                                  bg=BG_INPUT, fg=FG_DIM,
                                  activebackground=ACCENT_STOP,
                                  activeforeground=FG,
                                  relief="flat", bd=0,
                                  padx=16, pady=6,
                                  cursor="hand2",
                                  state="disabled",
                                  command=self._on_stop)
        self.stop_btn.pack(side="left", padx=(8, 0))

        self.copy_btn = tk.Button(btn_frame, text="COPY ALL",
                                  font=FONT_BTN,
                                  bg=BG_INPUT, fg=FG_DIM,
                                  activebackground=BG_PANEL,
                                  activeforeground=FG,
                                  relief="flat", bd=0,
                                  padx=16, pady=6,
                                  cursor="hand2",
                                  command=self._copy_all_urls)
        self.copy_btn.pack(side="right")

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def _update_wait_label(self, _=None):
        mn = self.wait_min.get()
        mx = self.wait_max.get()
        # Đảm bảo min <= max
        if mn > mx:
            self.wait_max.set(mn)
            mx = mn
        self.wait_label.config(text=f"{mn:.1f} – {mx:.1f}s")

    def _choose_output_file(self, _=None):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="zalo_groups.txt"
        )
        if path:
            self.output_file = Path(path)
            self.file_label.config(text=str(self.output_file))

    def _on_start(self):
        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showwarning("Thiếu keyword", "Nhập keyword trước khi bắt đầu")
            return

        try:
            target = int(self.target_var.get())
            from automation.search_runner import TARGET_MIN, TARGET_MAX
            if not (TARGET_MIN <= target <= TARGET_MAX):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Target không hợp lệ",
                                   f"Target phải từ 10 đến 99999")
            return

        # Reset UI
        self.url_list.delete(0, "end")
        self.url_count = 0
        self.count_label.config(text="0")
        self.page_label.config(text="page 0")
        self._set_status("running", ACCENT)
        self._log("Chờ 5s — click vào Chrome...")

        # Disable/enable buttons
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal", bg=ACCENT_STOP, fg=FG)

        # Khởi động runner trong thread riêng
        from automation.search_runner import SearchRunner
        self.runner = SearchRunner(
            keyword=keyword,
            target=target,
            output_file=self.output_file,
            min_wait=self.wait_min.get(),
            max_wait=self.wait_max.get(),
            on_progress=self._on_progress,
        )

        self.runner_thread = threading.Thread(
            target=self._run_thread, daemon=True
        )
        self.runner_thread.start()

    def _run_thread(self):
        """Chạy runner trong background thread."""
        try:
            self.runner.run()
        except Exception as e:
            self.root.after(0, lambda: self._log(f"Lỗi: {e}"))
        finally:
            self.root.after(0, self._on_done)

    def _on_stop(self):
        if self.runner:
            self.runner.stop()
            self._log("Đang dừng...")
            self.stop_btn.config(state="disabled")

    def _on_done(self):
        self._set_status("done", FG_NEW)
        self._log(f"Xong — {self.url_count} links → {self.output_file}")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled", bg=BG_INPUT, fg=FG_DIM)

    def _on_progress(self, count: int, total: int, url: str):
        """Callback từ runner — chạy trong background thread, dùng after() để update UI."""
        self.url_count = count
        self.root.after(0, lambda: self._update_ui(count, total, url))

    def _update_ui(self, count: int, total: int, url: str):
        self.count_label.config(text=str(count))
        self.page_label.config(text=f"page {self.runner.pages_scanned}")

        # Thêm URL vào list
        self.url_list.insert("end", url)
        self.url_list.itemconfig("end", fg=FG_NEW)
        self.url_list.see("end")

        self._log(f"[{count}/{total}] {url}")

    def _log(self, msg: str):
        """Cập nhật dòng log ở dưới cùng."""
        # Cắt ngắn nếu quá dài
        if len(msg) > 60:
            msg = msg[:57] + "..."
        self.log_label.config(text=msg)

    def _set_status(self, state: str, color: str):
        self.status_dot.config(fg=color)

    def _copy_selected_url(self, _=None):
        """Double-click để copy URL được chọn."""
        sel = self.url_list.curselection()
        if sel:
            url = self.url_list.get(sel[0])
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self._log(f"Đã copy: {url}")

    def _copy_all_urls(self):
        """Copy tất cả URL trong list."""
        items = self.url_list.get(0, "end")
        if not items:
            self._log("Chưa có link nào")
            return
        text = "\n".join(items)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log(f"Đã copy {len(items)} links")


def run():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    run()
