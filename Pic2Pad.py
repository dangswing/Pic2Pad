import requests
import json
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

VER = "1.0"
CONFIG_FILE = "piconfig.json"
DEFAULT_CONFIG = {
    "ip_addr": "192.168.1.1",
    "port": 53317,
    "user": "",
    "device_name": "",
    "folder_path": r""
}

class LocalSendGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Pic2Pad")
        
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
        self.save_settings()  # 启动前保存一次
        folder_path = self.config_data["folder_path"]
        if not os.path.isdir(folder_path):
            messagebox.showerror("路径错误", "监控文件夹不存在！")
            return
        if self.monitor_thread and self.monitor_thread.is_alive():
            messagebox.showinfo("正在运行", "监控已在进行中")
            return
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self.monitor_folder, daemon=True)
        self.monitor_thread.start()
        self.start_btn.config(state="disabled")
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
            self.status_var.set(f"传输失败！")


if __name__ == "__main__":
    app = LocalSendGUI()
    app.mainloop()