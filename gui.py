import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os
from PIL import Image, ImageTk
import time

class DramaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("剧集信息查看器")
        self.root.geometry("1300x800")

        self.data_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.is_running = False
        self._lock = threading.Lock()

        self.drama_data = []
        self.image_references = []

        self.setup_ui()
        self.start_queue_check()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.setup_search_area(main_frame)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.setup_image_gallery(content_frame)
        self.setup_log_area(content_frame)

    def setup_search_area(self, parent):
        search_frame = ttk.LabelFrame(parent, text="搜索设置", padding=10)
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="剧集名称:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, padx=5)
        self.search_entry.bind("<Return>", lambda event: self.start_search())

        button_frame = ttk.Frame(search_frame)
        button_frame.grid(row=0, column=2, padx=(20, 0))

        self.start_btn = ttk.Button(button_frame, text="开始搜索", command=self.start_search)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_search, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.progress_label = ttk.Label(search_frame, text="就绪", foreground="gray")
        self.progress_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

    def setup_image_gallery(self, parent):
        gallery_frame = ttk.LabelFrame(parent, text="剧集展示", padding=10)
        gallery_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.canvas = tk.Canvas(gallery_frame, bg='#f5f5f5', highlightthickness=0)

        v_scrollbar = ttk.Scrollbar(gallery_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(gallery_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self._on_inner_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel(self.canvas)

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_inner_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def setup_log_area(self, parent):
        log_frame = ttk.LabelFrame(parent, text="日志信息", padding=10)
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=40,
            height=30,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_drama_card(self, parent, drama_item, row, col):
        card = ttk.Frame(parent, borderwidth=1, relief="solid")
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        img_label = ttk.Label(card, text="加载中...", anchor="center")
        img_label.pack(padx=5, pady=(5, 0))

        title_text = drama_item['title']
        if len(title_text) > 12:
            title_text = title_text[:12] + "..."
        ttk.Label(card, text=title_text, font=('Microsoft YaHei', 9, 'bold')).pack(pady=(3, 0))

        ttk.Label(card, text=drama_item['episodes_num'], foreground="gray").pack(pady=(0, 5))

        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, d=drama_item: self.on_drama_click(d))
        card.bind("<Button-1>", lambda e, d=drama_item: self.on_drama_click(d))

        img_path = f".tmp/img_{drama_item['id']}.jpg"
        self.root.after(50, lambda: self.load_image_async(img_label, img_path, drama_item))

        return card

    def load_image_async(self, img_label, img_path, drama_item):
        try:
            if os.path.exists(img_path):
                image = Image.open(img_path)
                image = image.resize((180, 260), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)

                img_label.configure(image=photo, text="")
                img_label.image = photo
                self.image_references.append(photo)
                self.add_log(f"已加载图片: {drama_item['title']}")
            else:
                img_label.configure(text="无图片", foreground="gray")
        except Exception as e:
            img_label.configure(text="加载失败", foreground="red")
            self.add_log(f"图片加载失败 {drama_item['title']}: {str(e)}")

    def start_search(self, event=None):
        keyword = self.search_var.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return

        if self.is_running:
            return

        self.is_running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.drama_data = []
        self.image_references = []

        self.worker_thread = threading.Thread(
            target=self.search_worker,
            args=(keyword,),
            daemon=True
        )
        self.worker_thread.start()

        self.add_log(f"开始搜索: {keyword}")

    def search_worker(self, keyword):
        try:
            self.log_queue.put("正在初始化浏览器...")

            from dramaInfo import DramaInfo, DownloadImg

            drama_info = DramaInfo()
            drama_info.search(keyword)
            data_array = drama_info.get_drama_list()

            if self.stop_event.is_set():
                self.data_queue.put({"type": "stopped"})
                return

            self.log_queue.put(f"找到 {len(data_array)} 个结果")

            if not data_array:
                self.data_queue.put({"type": "no_data"})
                return

            self.log_queue.put("开始下载图片...")
            downloader = DownloadImg(data_array)

            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(downloader.scrape_all_img())
            finally:
                loop.close()

            if self.stop_event.is_set():
                self.data_queue.put({"type": "stopped"})
                return

            self.data_queue.put({
                "type": "data",
                "data": data_array
            })

        except Exception as e:
            self.data_queue.put({
                "type": "error",
                "msg": f"搜索过程中出错: {str(e)}"
            })

    def update_image_gallery(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.image_references.clear()

        cols = 4
        for i, item in enumerate(self.drama_data):
            r = i // cols
            c = i % cols
            self.create_drama_card(self.inner_frame, item, r, c)

        for r in range((len(self.drama_data) + cols - 1) // cols):
            self.inner_frame.grid_rowconfigure(r, weight=1)
        for c in range(cols):
            self.inner_frame.grid_columnconfigure(c, weight=1)

        self.root.after(100, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def on_drama_click(self, drama_data):
        messagebox.showinfo(
            "剧集详情",
            f"标题: {drama_data['title']}\n"
            f"集数: {drama_data['episodes_num']}\n"
            f"链接: {drama_data['href']}\n"
            f"图片URL: {drama_data['img_url']}"
        )

    def add_log(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def stop_search(self):
        self.stop_event.set()
        self.add_log("正在停止搜索...")

    def _reset_search_state(self):
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def process_queue_messages(self):
        try:
            while True:
                msg = self.data_queue.get_nowait()
                msg_type = msg.get("type")

                if msg_type == "data":
                    with self._lock:
                        self.drama_data = msg["data"]
                    self.update_image_gallery()
                    self.progress_label.config(
                        text=f"搜索完成，共找到 {len(self.drama_data)} 个结果", foreground="green"
                    )
                    self.add_log("搜索和图片下载完成")
                    self._reset_search_state()

                elif msg_type == "no_data":
                    self.progress_label.config(text="未找到相关结果", foreground="orange")
                    self.add_log("未找到匹配的剧集")
                    self._reset_search_state()

                elif msg_type == "error":
                    self.progress_label.config(text="搜索出错", foreground="red")
                    self.add_log(f"错误: {msg['msg']}")
                    messagebox.showerror("错误", msg["msg"])
                    self._reset_search_state()

                elif msg_type == "stopped":
                    self.progress_label.config(text="搜索已停止", foreground="gray")
                    self.add_log("搜索被用户停止")
                    self._reset_search_state()

        except queue.Empty:
            pass

        try:
            while True:
                log_msg = self.log_queue.get_nowait()
                self.add_log(log_msg)
                self.progress_label.config(text=log_msg, foreground="blue")
        except queue.Empty:
            pass

        if self.is_running:
            self.root.after(100, self.process_queue_messages)

    def start_queue_check(self):
        self.process_queue_messages()


def main():
    root = tk.Tk()
    app = DramaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
