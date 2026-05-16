import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os
import re
import asyncio
import aiohttp
import aiofiles
import random
import time
from bs4 import BeautifulSoup
from PIL import Image, ImageTk

from dramaInfo import DramaInfo, DataProcess, DownloadImg


def url_process(base_url, episodes_num):
    episode_urls = []
    for i in range(1, episodes_num + 1):
        prefix = (i - 1) // 3
        url = f"{base_url}/episode/{prefix}-{i}"
        episode_urls.append(url)
    episode_urls[0] = episode_urls[0].replace("/0-1", "/")
    return episode_urls


class DramaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("剧集信息查看器")
        self.root.geometry("1300x800")

        self.data_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.is_running = False
        self.is_scraping = False
        self._lock = threading.Lock()

        self.drama_data = []
        self.image_references = []

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.setup_ui()
        self.start_queue_check()

        self.drama_info = DramaInfo()
        self.add_log("正在初始化浏览器...")
        self.drama_info.init_browser()
        self.add_log("浏览器初始化完成")

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
        gallery_frame = ttk.LabelFrame(parent, text="搜索结果 - 点击剧集卡片爬取剧情摘要", padding=10)
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
            child.bind("<Button-1>", lambda e, d=drama_item: self.start_scrape(d))
        card.bind("<Button-1>", lambda e, d=drama_item: self.start_scrape(d))

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

        if self.is_running or self.is_scraping:
            return

        self.is_running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        self._clear_tmp_images()

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
            self.drama_info.search(keyword)
            data_array = self.drama_info.get_drama_list()

            if self.stop_event.is_set():
                self.data_queue.put({"type": "stopped"})
                return

            self.log_queue.put(f"找到 {len(data_array)} 个结果")

            if not data_array:
                self.data_queue.put({"type": "no_data"})
                return

            self.log_queue.put("开始下载图片...")
            downloader = DownloadImg(data_array)

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

    def start_scrape(self, drama_item):
        if self.is_scraping or self.is_running:
            return

        processor = DataProcess(drama_item)
        processor.process()
        data = processor.get_process_data()

        title = data['title']
        episodes_num = data['episodes_num']
        base_url = data['base_url']

        if episodes_num == 0:
            messagebox.showerror("错误", f"无法解析集数: {drama_item['episodes_num']}")
            return

        self.is_scraping = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        self.add_log(f"开始爬取《{title}》剧情摘要，共 {episodes_num} 集")
        self.progress_label.config(text=f"正在爬取《{title}》...", foreground="blue")

        threading.Thread(
            target=self.summary_worker,
            args=(data,),
            daemon=True
        ).start()

    async def _scrape_one(self, session, url, episode_num):
        try:
            await asyncio.sleep(random.uniform(0.2, 0.5))
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                main_left_div = soup.find('div', class_='main-left')
                title_tag = main_left_div.find('p', class_='epi_t')
                title = title_tag.get_text(strip=True) if title_tag else f"第{episode_num}集"

                article_tag = main_left_div.find('article', class_='epi_c')
                if article_tag:
                    paragraphs = article_tag.find_all('p')
                    content = '\n'.join(p.get_text(strip=True) for p in paragraphs)
                else:
                    content = "未找到剧情内容"

                return episode_num, title, content
        except Exception as e:
            return episode_num, f"第{episode_num}集", f"错误: {str(e)}"

    def summary_worker(self, data):
        collected = {}
        try:
            title = data['title']
            base_url = data['base_url']
            episodes_num = data['episodes_num']

            episode_urls = url_process(base_url, episodes_num)

            async def run():
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                async with aiohttp.ClientSession(headers=headers) as session:
                    tasks = [self._scrape_one(session, url, i + 1)
                             for i, url in enumerate(episode_urls)]

                    results = {}
                    filename = f'{self._sanitize_filename(title)}_episodes_summary.txt'
                    async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
                        current = 1
                        completed = 0
                        for coro in asyncio.as_completed(tasks):
                            ep_num, ep_title, content = await coro
                            results[ep_num] = (ep_title, content)

                            while current in results:
                                t, c = results[current]
                                await file.write(f"{t}:\n{c}\n\n")
                                collected[current] = (t, c)
                                del results[current]
                                current += 1

                            if self.stop_event.is_set():
                                self.data_queue.put({"type": "summary_stopped"})
                                return

                            completed += 1
                            self.log_queue.put(f"爬取进度: {completed}/{episodes_num}")

                    self.data_queue.put({
                        "type": "summary_complete",
                        "title": title,
                        "total": episodes_num,
                        "filename": filename,
                        "episodes": collected
                    })

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run())
            finally:
                loop.close()

        except Exception as e:
            self.data_queue.put({
                "type": "summary_error",
                "msg": f"爬取剧情时出错: {str(e)}"
            })

    def _clear_tmp_images(self):
        tmp_dir = ".tmp"
        if os.path.isdir(tmp_dir):
            for f in os.listdir(tmp_dir):
                if f.endswith(".jpg"):
                    try:
                        os.remove(os.path.join(tmp_dir, f))
                    except OSError:
                        pass

    def _sanitize_filename(self, name):
        return re.sub(r'[\\/:*?"<>|]', '_', name)

    def show_episode_window(self, title, total, filename, episodes):
        win = tk.Toplevel(self.root)
        win.title(f"《{title}》剧情摘要 - 共 {total} 集")
        win.geometry("900x700")

        top_bar = ttk.Frame(win)
        top_bar.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(top_bar, text=f"《{title}》共 {total} 集",
                  font=('Microsoft YaHei', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Label(top_bar, text=f"已保存至: {filename}", foreground="gray").pack(side=tk.RIGHT)

        text_area = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=('Microsoft YaHei', 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        for ep_num in sorted(episodes.keys()):
            ep_title, content = episodes[ep_num]
            text_area.insert(tk.END, f"{ep_title}\n", "title")
            text_area.insert(tk.END, f"{content}\n\n", "body")

        text_area.tag_configure("title", font=('Microsoft YaHei', 11, 'bold'), foreground="#1a5276")
        text_area.tag_configure("body", font=('Microsoft YaHei', 10))
        text_area.config(state=tk.DISABLED)

        close_btn = ttk.Button(win, text="关闭", command=win.destroy)
        close_btn.pack(pady=(0, 10))

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

    def add_log(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def stop_search(self):
        self.stop_event.set()
        self.add_log("正在停止...")

    def _on_close(self):
        self.stop_event.set()
        self.add_log("正在关闭浏览器...")
        self.drama_info.close()
        self.root.destroy()

    def _reset_search_state(self):
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _reset_scrape_state(self):
        self.is_scraping = False
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

                elif msg_type == "summary_complete":
                    self.progress_label.config(
                        text=f"《{msg['title']}》爬取完成，共 {msg['total']} 集", foreground="green"
                    )
                    self.add_log(f"剧情摘要已保存至: {msg['filename']}")
                    self.show_episode_window(
                        msg['title'], msg['total'], msg['filename'], msg['episodes']
                    )
                    self._reset_scrape_state()

                elif msg_type == "summary_error":
                    self.progress_label.config(text="爬取出错", foreground="red")
                    self.add_log(f"错误: {msg['msg']}")
                    messagebox.showerror("错误", msg["msg"])
                    self._reset_scrape_state()

                elif msg_type == "summary_stopped":
                    self.progress_label.config(text="爬取已停止", foreground="gray")
                    self.add_log("爬取被用户停止")
                    self._reset_scrape_state()

        except queue.Empty:
            pass

        try:
            while True:
                log_msg = self.log_queue.get_nowait()
                self.add_log(log_msg)
                self.progress_label.config(text=log_msg, foreground="blue")
        except queue.Empty:
            pass

        self.root.after(100, self.process_queue_messages)

    def start_queue_check(self):
        self.process_queue_messages()


def main():
    root = tk.Tk()
    DramaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
