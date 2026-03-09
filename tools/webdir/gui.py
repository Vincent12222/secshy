import os
import threading
import webbrowser
from collections import Counter

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from scanner import ScanResult, run_scan


class WebDirGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WebDir 目录扫描 - 独立版")
        self.geometry("900x600")

        self.scan_thread = None
        self.stop_event = threading.Event()
        self._ui_queue = []
        self._stats = Counter()
        self._all_results: list[ScanResult] = []
        self._bg_image = None

        self._setup_background()
        self._build_ui()
        self._setup_ui_updater()

    def _setup_background(self):
        base_dir = Path(__file__).resolve().parent
        img_path = base_dir / "background.png"
        if not img_path.is_file():
            return
        try:
            self._bg_image = tk.PhotoImage(file=str(img_path))
            lbl = tk.Label(self, image=self._bg_image, borderwidth=0)
            lbl.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception:
            self._bg_image = None

    def _build_ui(self):
        padding = {"padx": 8, "pady": 4}

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        row = 0
        ttk.Label(main_frame, text="目标 URL：").grid(row=row, column=0, sticky=tk.W, **padding)
        self.entry_url = ttk.Entry(main_frame)
        self.entry_url.grid(row=row, column=1, columnspan=5, sticky=tk.EW, **padding)
        main_frame.columnconfigure(1, weight=1)

        base_dir = Path(__file__).resolve().parent

        row += 1
        ttk.Label(main_frame, text="字典文件（留空=默认使用内置字典）：").grid(row=row, column=0, sticky=tk.W, **padding)
        self.entry_dict = ttk.Entry(main_frame)
        self.entry_dict.grid(row=row, column=1, sticky=tk.EW, **padding)
        btn_dict = ttk.Button(main_frame, text="浏览...", command=self._choose_dict)
        btn_dict.grid(row=row, column=2, sticky=tk.W, **padding)

        row += 1
        ttk.Label(main_frame, text="最大线程(可选)：").grid(row=row, column=0, sticky=tk.W, **padding)
        self.entry_threads = ttk.Entry(main_frame, width=10)
        self.entry_threads.grid(row=row, column=1, sticky=tk.W, **padding)

        ttk.Label(main_frame, text="当前并发：").grid(row=row, column=2, sticky=tk.E, **padding)
        self.var_concurrency = tk.IntVar(value=50)
        self.spin_concurrency = ttk.Spinbox(main_frame, from_=1, to=500, textvariable=self.var_concurrency, width=8)
        self.spin_concurrency.grid(row=row, column=3, sticky=tk.W, **padding)

        self.var_insecure = tk.BooleanVar(value=False)
        chk_insecure = ttk.Checkbutton(main_frame, text="忽略 HTTPS 证书校验", variable=self.var_insecure)
        chk_insecure.grid(row=row, column=4, sticky=tk.W, **padding)

        row += 1
        self.var_recursion = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="递归扫描", variable=self.var_recursion).grid(
            row=row, column=0, sticky=tk.W, **padding
        )
        ttk.Label(main_frame, text="深度：").grid(row=row, column=1, sticky=tk.E, **padding)
        self.var_depth = tk.IntVar(value=2)
        ttk.Spinbox(main_frame, from_=0, to=10, textvariable=self.var_depth, width=6).grid(
            row=row, column=2, sticky=tk.W, **padding
        )
        ttk.Label(main_frame, text="模式：").grid(row=row, column=3, sticky=tk.E, **padding)
        self.var_rec_mode = tk.StringVar(value="dir_listing")
        ttk.Combobox(
            main_frame,
            textvariable=self.var_rec_mode,
            values=["dir_listing", "html_links"],
            width=12,
            state="readonly",
        ).grid(row=row, column=4, sticky=tk.W, **padding)

        row += 1
        self.var_random_ua = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="随机 UA", variable=self.var_random_ua).grid(
            row=row, column=0, sticky=tk.W, **padding
        )
        ttk.Label(main_frame, text="UA文件(可选)：").grid(row=row, column=1, sticky=tk.E, **padding)
        self.entry_ua = ttk.Entry(main_frame)
        self.entry_ua.grid(row=row, column=2, columnspan=2, sticky=tk.EW, **padding)
        btn_ua = ttk.Button(main_frame, text="浏览...", command=self._choose_ua)
        btn_ua.grid(row=row, column=4, sticky=tk.W, **padding)

        row += 1
        self.var_proxy = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="启用代理池", variable=self.var_proxy).grid(
            row=row, column=0, sticky=tk.W, **padding
        )
        ttk.Label(main_frame, text="代理文件：").grid(row=row, column=1, sticky=tk.E, **padding)
        self.entry_proxy = ttk.Entry(main_frame)
        self.entry_proxy.grid(row=row, column=2, columnspan=2, sticky=tk.EW, **padding)
        btn_proxy = ttk.Button(main_frame, text="浏览...", command=self._choose_proxy)
        btn_proxy.grid(row=row, column=4, sticky=tk.W, **padding)

        row += 1
        self.var_fw = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="自动识别框架/组件", variable=self.var_fw).grid(
            row=row, column=0, sticky=tk.W, **padding
        )

        row += 1
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=6, sticky=tk.EW, **padding)

        self.btn_start = ttk.Button(btn_frame, text="开始扫描", command=self.start_scan)
        self.btn_start.pack(side=tk.LEFT, padx=4)

        self.btn_stop = ttk.Button(btn_frame, text="停止", command=self.stop_scan, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=4)

        row += 1
        self.lbl_stats = ttk.Label(main_frame, text="状态：就绪")
        self.lbl_stats.grid(row=row, column=0, columnspan=3, sticky=tk.W, **padding)
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate", length=180)
        self.progress.grid(row=row, column=3, columnspan=3, sticky=tk.E, **padding)

        row += 1
        ttk.Label(main_frame, text="状态码筛选：").grid(row=row, column=0, sticky=tk.W, **padding)
        self.var_filter_status = tk.StringVar(value="")
        entry_filter = ttk.Entry(main_frame, textvariable=self.var_filter_status, width=10)
        entry_filter.grid(row=row, column=1, sticky=tk.W, **padding)
        ttk.Label(main_frame, text="（留空=显示全部）").grid(row=row, column=2, columnspan=2, sticky=tk.W, **padding)
        self.var_filter_status.trace_add("write", lambda *_: self._refresh_results_view())

        row += 1
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=row, column=0, columnspan=6, sticky=tk.NSEW, padx=8, pady=(0, 8))
        main_frame.rowconfigure(row, weight=1)

        # Results tab
        tab_res = ttk.Frame(notebook)
        notebook.add(tab_res, text="结果")
        tab_res.rowconfigure(0, weight=1)
        tab_res.columnconfigure(0, weight=1)

        cols = ("status", "url", "tags", "frameworks", "depth")
        self.tree = ttk.Treeview(tab_res, columns=cols, show="headings")
        self.tree.heading("status", text="状态码")
        self.tree.heading("url", text="URL")
        self.tree.heading("tags", text="标签")
        self.tree.heading("frameworks", text="框架/组件")
        self.tree.heading("depth", text="深度")
        self.tree.column("status", width=70, anchor=tk.CENTER, stretch=False)
        self.tree.column("url", width=420, anchor=tk.W)
        self.tree.column("tags", width=160, anchor=tk.W)
        self.tree.column("frameworks", width=160, anchor=tk.W)
        self.tree.column("depth", width=60, anchor=tk.CENTER, stretch=False)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        self.tree.bind("<Double-1>", self._open_selected_url)

        scroll_tree = ttk.Scrollbar(tab_res, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_tree.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscrollcommand=scroll_tree.set)

        # Logs tab
        tab_log = ttk.Frame(notebook)
        notebook.add(tab_log, text="日志")
        tab_log.rowconfigure(0, weight=1)
        tab_log.columnconfigure(0, weight=1)
        self.text = tk.Text(tab_log, wrap=tk.NONE, height=20)
        self.text.grid(row=0, column=0, sticky=tk.NSEW)
        scroll_y = ttk.Scrollbar(tab_log, orient=tk.VERTICAL, command=self.text.yview)
        scroll_y.grid(row=0, column=1, sticky=tk.NS)
        self.text.configure(yscrollcommand=scroll_y.set)

        # Stats tab
        tab_stats = ttk.Frame(notebook)
        notebook.add(tab_stats, text="统计")
        tab_stats.columnconfigure(0, weight=1)
        tab_stats.columnconfigure(1, weight=1)
        tab_stats.rowconfigure(1, weight=1)

        ttk.Label(tab_stats, text="状态码分布").grid(row=0, column=0, sticky=tk.W, padx=8, pady=(8, 4))
        ttk.Label(tab_stats, text="框架/组件命中").grid(row=0, column=1, sticky=tk.W, padx=8, pady=(8, 4))

        self.tree_status = ttk.Treeview(tab_stats, columns=("code", "count"), show="headings", height=12)
        self.tree_status.heading("code", text="状态码")
        self.tree_status.heading("count", text="数量")
        self.tree_status.column("code", width=90, anchor=tk.CENTER, stretch=False)
        self.tree_status.column("count", width=90, anchor=tk.CENTER, stretch=False)
        self.tree_status.grid(row=1, column=0, sticky=tk.NSEW, padx=(8, 4), pady=(0, 8))

        self.tree_fw = ttk.Treeview(tab_stats, columns=("fw", "count"), show="headings", height=12)
        self.tree_fw.heading("fw", text="名称")
        self.tree_fw.heading("count", text="数量")
        self.tree_fw.column("fw", width=220, anchor=tk.W)
        self.tree_fw.column("count", width=90, anchor=tk.CENTER, stretch=False)
        self.tree_fw.grid(row=1, column=1, sticky=tk.NSEW, padx=(4, 8), pady=(0, 8))

    def _setup_ui_updater(self):
        self.after(100, self._flush_ui_queue)

    def _flush_ui_queue(self):
        if self._ui_queue:
            for item in self._ui_queue:
                kind = item.get("type")
                if kind == "log":
                    msg = item.get("msg", "")
                    self.text.insert(tk.END, msg + "\n")
                    self.text.see(tk.END)
                elif kind == "result":
                    r: ScanResult = item["data"]
                    self._all_results.append(r)
                    self._stats["total"] += 1
                    self._stats[str(r.status)] += 1
                    if r.frameworks:
                        for fw in r.frameworks:
                            self._stats[f"fw:{fw}"] += 1
                elif kind == "status":
                    self.lbl_stats.config(text=item.get("msg", ""))
            self._ui_queue.clear()
            self._refresh_results_view()
            self._refresh_stats_views()

        self.after(100, self._flush_ui_queue)

    def _refresh_stats_views(self):
        # status codes
        for i in self.tree_status.get_children():
            self.tree_status.delete(i)
        for code, cnt in sorted(
            ((k, v) for k, v in self._stats.items() if str(k).isdigit()),
            key=lambda x: (-x[1], int(x[0])),
        ):
            self.tree_status.insert("", tk.END, values=(code, cnt))

        # frameworks
        for i in self.tree_fw.get_children():
            self.tree_fw.delete(i)
        fw_items = sorted(
            ((k[3:], v) for k, v in self._stats.items() if str(k).startswith("fw:")),
            key=lambda x: (-x[1], x[0]),
        )
        for fw, cnt in fw_items[:200]:
            self.tree_fw.insert("", tk.END, values=(fw, cnt))

    def _refresh_results_view(self):
        # 清空当前视图
        for i in self.tree.get_children():
            self.tree.delete(i)

        flt = (self.var_filter_status.get() or "").strip()
        code_filter: int | None = None
        prefix: str | None = None
        if flt:
            try:
                code_filter = int(flt)
            except ValueError:
                prefix = flt

        for r in self._all_results:
            if code_filter is not None and r.status != code_filter:
                continue
            if prefix is not None and not str(r.status).startswith(prefix):
                continue
            self.tree.insert(
                "",
                tk.END,
                values=(
                    r.status,
                    r.url,
                    " ".join(r.tags),
                    ", ".join(r.frameworks),
                    r.depth,
                ),
            )

    def _append_log(self, line: str):
        self._ui_queue.append({"type": "log", "msg": line})

    def _append_result(self, r: ScanResult):
        self._ui_queue.append({"type": "result", "data": r})

    def _open_selected_url(self, _event=None):
        item = self.tree.focus()
        if not item:
            return
        vals = self.tree.item(item, "values")
        if not vals or len(vals) < 2:
            return
        url = vals[1]
        try:
            webbrowser.open(str(url))
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("错误", f"打开链接失败：{e}")

    def _choose_dict(self):
        path = filedialog.askopenfilename(
            title="选择字典文件",
            filetypes=[("文本文件", "*.txt;*.lst;*.dic"), ("所有文件", "*.*")],
        )
        if path:
            self.entry_dict.delete(0, tk.END)
            self.entry_dict.insert(0, path)

    def _choose_proxy(self):
        path = filedialog.askopenfilename(
            title="选择代理文件",
            filetypes=[("文本文件", "*.txt;*.lst;*.dic"), ("所有文件", "*.*")],
        )
        if path:
            self.entry_proxy.delete(0, tk.END)
            self.entry_proxy.insert(0, path)

    def _choose_ua(self):
        path = filedialog.askopenfilename(
            title="选择 UA 文件",
            filetypes=[("文本文件", "*.txt;*.lst;*.dic"), ("所有文件", "*.*")],
        )
        if path:
            self.entry_ua.delete(0, tk.END)
            self.entry_ua.insert(0, path)

    def start_scan(self):
        if self.scan_thread and self.scan_thread.is_alive():
            messagebox.showwarning("提示", "扫描正在进行中。")
            return

        url = self.entry_url.get().strip()
        if not url:
            messagebox.showerror("错误", "请填写目标 URL。")
            return

        dict_path = self.entry_dict.get().strip() or None

        threads_override = None
        threads_str = self.entry_threads.get().strip()
        if threads_str:
            try:
                threads_override = int(threads_str)
            except ValueError:
                messagebox.showerror("错误", "线程数必须是整数。")
                return

        insecure = self.var_insecure.get()
        max_threads = threads_override
        if not max_threads:
            # 如果用户没填，先用并发框的值作为上限，避免“并发>线程”无效
            try:
                max_threads = int(self.var_concurrency.get())
            except Exception:  # noqa: BLE001
                max_threads = None

        # 约束并发不超过最大线程
        try:
            cur_c = int(self.var_concurrency.get())
        except Exception:  # noqa: BLE001
            cur_c = 50
        if max_threads:
            cur_c = max(1, min(int(max_threads), int(cur_c)))
            self.var_concurrency.set(cur_c)

        self.text.delete("1.0", tk.END)
        for i in self.tree.get_children():
            self.tree.delete(i)
        for i in self.tree_status.get_children():
            self.tree_status.delete(i)
        for i in self.tree_fw.get_children():
            self.tree_fw.delete(i)
        self._stats.clear()
        self._all_results.clear()
        self.lbl_stats.config(text="状态：扫描中...")
        self._append_log(f"[+] 开始扫描：{url}")

        self.stop_event.clear()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        try:
            self.progress.start(80)
        except Exception:
            pass

        settings_override = {
            "recursion": bool(self.var_recursion.get()),
            "recursion_mode": str(self.var_rec_mode.get()),
            "max_depth": int(self.var_depth.get()),
            "random_ua": bool(self.var_random_ua.get()),
            "ua_file": (self.entry_ua.get().strip() or None),
            "proxy_enable": bool(self.var_proxy.get()),
            "proxy_file": (self.entry_proxy.get().strip() or None),
            "framework_detect": bool(self.var_fw.get()),
        }

        def worker():
            try:
                run_scan(
                    url=url,
                    config_path=None,
                    finger_path=None,
                    dict_file=dict_path,
                    threads_override=max_threads,
                    insecure=insecure,
                    on_result=self._append_log,
                    stop_event=self.stop_event,
                    on_scan_result=self._append_result,
                    on_log=self._append_log,
                    concurrency_getter=lambda: int(self.var_concurrency.get()),
                    settings_override=settings_override,
                )
            except Exception as e:  # noqa: BLE001
                self._append_log(f"[!] 扫描异常：{e}")
            finally:
                self._append_log("[*] 扫描结束。")
                self.lbl_stats.config(text="状态：已完成")
                self.btn_start.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                try:
                    self.progress.stop()
                    self.progress["value"] = 0
                except Exception:
                    pass

        self.scan_thread = threading.Thread(target=worker, daemon=True)
        self.scan_thread.start()

    def stop_scan(self):
        if self.stop_event:
            self.stop_event.set()
            self._append_log("[*] 正在请求停止扫描...")


def main():
    app = WebDirGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

