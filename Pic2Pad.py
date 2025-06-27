import requests
import json
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageDraw
import pystray, base64, io

VER = "1.1"
CONFIG_FILE = "piconfig.json"
DEFAULT_CONFIG = {
    "ip_addr": "192.168.1.1",
    "port": 53317,
    "user": "",
    "device_name": "",
    "folder_path": r""
}

ICON_BASE64 = (
    "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"
)

class LocalSendGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()

        self.title(f"Pic2Pad")
        raw = base64.b64decode(ICON_BASE64)
        pil_icon = Image.open(io.BytesIO(raw))

        bio = io.BytesIO()
        pil_icon.save(bio, format='PNG')
        bio.seek(0)
        self._tk_icon = tk.PhotoImage(data=bio.read(), format='PNG')
        self.iconphoto(False, self._tk_icon)
        
        self.resizable(False, False)
        # self.geometry("300x100")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # 加载配置
        self.config_data = self.load_config()

        # ---------------- 顶部行：IP -----------------
        ttk.Label(self, text="IP 地址:", anchor="center").grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.ip_var = tk.StringVar(value=self.config_data["ip_addr"])
        ttk.Entry(self, textvariable=self.ip_var, width=22, justify="center").grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # ---------------- 按钮行 ----------------------
        self.btn_settings = ttk.Button(self, text="设置", command=self.toggle_settings)
        self.btn_settings.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.start_btn = ttk.Button(self, text="启动", command=self.start_monitor)
        self.start_btn.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # ---------------- 折叠设置区 ------------------
        self.settings_frame = ttk.Frame(self, relief="solid", padding=(4, 4))
        self.settings_frame.columnconfigure(0, weight=1)
        self.settings_frame.columnconfigure(1, weight=1)
        self.settings_frame.columnconfigure(2, weight=1)
        self.settings_frame.columnconfigure(3, weight=1)

        # 用户
        ttk.Label(self.settings_frame, text="用户名:", anchor="center").grid(row=0, column=0, sticky="ew")
        self.user_var = tk.StringVar(value=self.config_data["user"])
        ttk.Entry(self.settings_frame, textvariable=self.user_var, width=15, justify="center").grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 设备名
        ttk.Label(self.settings_frame, text="设备名:", anchor="center").grid(row=1, column=0, sticky="ew")
        self.device_var = tk.StringVar(value=self.config_data["device_name"])
        ttk.Entry(self.settings_frame, textvariable=self.device_var, width=15, justify="center").grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 文件夹
        ttk.Label(self.settings_frame, text="截图路径:", anchor="center").grid(row=2, column=0, sticky="ew")
        self.folder_var = tk.StringVar(value=self.config_data["folder_path"])
        ttk.Entry(self.settings_frame, textvariable=self.folder_var, width=20, justify="center").grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # 按钮
        ttk.Button(self.settings_frame, text="选择文件夹…", command=self.choose_folder).grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        self.save_btn = ttk.Button(self.settings_frame, text="保存", command=self.save_settings)
        self.save_btn.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # 版本
        self.version_label = ttk.Label(self.settings_frame, text=f"Version: {VER}", anchor="center", foreground="gray")
        self.version_label.grid(row=4, column=0, columnspan=4, padx=5, pady=0, sticky="ew")

        # 默认隐藏
        self.settings_visible = False

        # 状态
        self.status_var = tk.StringVar(value="等待启动")
        ttk.Label(self, textvariable=self.status_var, anchor="center").grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # 监控线程
        self.monitor_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

        # 系统托盘
        self.protocol('WM_DELETE_WINDOW', self.quit_window)
        self.bind("<Unmap>", self.handle_minimize)
        self.setup_tray_icon()

        self.update_idletasks()
        self.deiconify()

    # ------------------------------------------------------------------
    # 系统托盘
    # ------------------------------------------------------------------
    def create_icon_image(self):
        raw = base64.b64decode(ICON_BASE64)
        return Image.open(io.BytesIO(raw))

    def setup_tray_icon(self):
        image = self.create_icon_image()
        menu = (pystray.MenuItem('显示', self.show_window, default=True),
                pystray.MenuItem('退出', self.quit_window))
        self.tray_icon = pystray.Icon("Pic2Pad", image, "Pic2Pad", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.state('normal')

    def quit_window(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.stop()
        self.stop_event.set()
        self.destroy()

    def handle_minimize(self, event):
        if self.state() == 'iconic':
            self.hide_window()

    # ------------------------------------------------------------------
    # 配置文件读写
    # ------------------------------------------------------------------
    def load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {**DEFAULT_CONFIG, **data}
            except json.JSONDecodeError:
                messagebox.showwarning("配置错误", "配置文件损坏")
        else:
            messagebox.showinfo("提示", "初次使用请先进行设置")
        return DEFAULT_CONFIG.copy()

    def write_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # GUI 事件
    # ------------------------------------------------------------------
    def toggle_settings(self):
        if self.settings_visible:
            self.settings_frame.grid_remove()
            self.settings_visible = False
            self.btn_settings.configure(text="设置")
        else:
            self.settings_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")
            self.settings_visible = True

    def choose_folder(self):
        path = filedialog.askdirectory(initialdir=self.folder_var.get() or os.getcwd())
        if path:
            self.folder_var.set(path)

    def save_settings(self):
        # 更新并写入配置
        self.config_data.update({
            "ip_addr": self.ip_var.get().strip(),
            "user": self.user_var.get().strip(),
            "device_name": self.device_var.get().strip(),
            "folder_path": self.folder_var.get().strip(),
        })
        self.write_config()
        self.status_var.set("设置已保存")

    def start_monitor(self):
        if self.monitor_thread and self.monitor_thread.is_alive():
            # 停止
            self.stop_event.set()
            self.start_btn.config(text="启动")
            self.status_var.set("等待启动")
            
        else:
            # 启动
            self.save_settings()
            folder_path = self.config_data["folder_path"]
            if not os.path.isdir(folder_path):
                messagebox.showerror("路径错误", "监控文件夹不存在！")
                return
            
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(target=self.monitor_folder, daemon=True)
            self.monitor_thread.start()
            self.start_btn.config(text="停止")
            self.status_var.set("监控中…")

    # ------------------------------------------------------------------
    # 文件监控与上传
    # ------------------------------------------------------------------
    def monitor_folder(self):
        folder_path = self.config_data["folder_path"]
        seen = set(os.listdir(folder_path))
        while not self.stop_event.is_set():
            time.sleep(1)
            current = set(os.listdir(folder_path))
            for fname in current - seen:
                full = os.path.join(folder_path, fname)
                self.status_var.set(f"发现新文件: {fname}")
                self.send_file(full)
            seen = current

    def send_file(self, filename: str):
        ip_addr = self.config_data["ip_addr"]
        port = self.config_data["port"]
        user = self.config_data["user"]
        device_name = self.config_data["device_name"]
        url1 = f"http://{ip_addr}:{port}/api/localsend/v2/prepare-upload"
        payload = {
            "info": {
                "alias": user,
                "version": "2.0",
                "deviceModel": device_name,
                "deviceType": "desktop",
                "fingerprint": "114514",
                "port": port,
                "protocol": "https",
                "download": "true",
            },
            "files": {
                "id": {
                    "id": "myfile",
                    "fileName": os.path.basename(filename),
                    "size": os.path.getsize(filename),
                    "fileType": "image/jpeg",
                    "sha256": "",
                    "preview": "",
                }
            },
        }
        try:
            r = requests.post(url1, json=payload, timeout=5)
            r.raise_for_status()
            data = r.json()
            url2 = (
                f"http://{ip_addr}:{port}/api/localsend/v2/upload?sessionId="
                f"{data['sessionId']}&fileId=myfile&token={data['files']['myfile']}"
            )
            with open(filename, "rb") as f:
                res = requests.post(url2, data=f, timeout=10)
                res.raise_for_status()
            self.status_var.set(f"传输完成: {os.path.basename(filename)}")
        except Exception as exc:
            self.status_var.set(f"传输失败！请尝试重启平板端Localsend")

if __name__ == "__main__":
    app = LocalSendGUI()
    app.mainloop()
