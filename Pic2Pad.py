import requests
import json
import os
import time
import threading
import socket
import struct
import ssl
import uuid
import ipaddress
import hashlib
import mimetypes
import tkinter as tk
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from tkinter import ttk, filedialog, messagebox
import urllib3
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from requests.adapters import HTTPAdapter

from PIL import Image, ImageDraw
import pystray, base64, io

VER = "1.3.0"
CONFIG_FILE = "piconfig.json"
CLIENT_CERT_FILE = "pic2pad_cert.pem"
CLIENT_KEY_FILE = "pic2pad_key.pem"
DEFAULT_CONFIG = {
    "ip_addr": "192.168.1.1",
    "port": 53317,
    "user": "",
    "device_name": "",
    "folder_path": r"",
    "fingerprint": "",
    "target_protocol": "http",
    "target_fingerprint": "",
}

MULTICAST_GROUP = "224.0.0.167"
DISCOVERY_TIMEOUT_SEC = 2.0
HTTP_SCAN_WORKERS = 50
HTTP_SCAN_MAX_INTERFACES = 3
SMART_SCAN_LEGACY_DELAY_SEC = 1.0
HTTP_DISCOVERY_TIMEOUT_SEC = 0.5
MULTICAST_ANNOUNCE_DELAYS_SEC = (0.1, 0.5, 2.0)

DISCOVERY_IDLE_INTERVAL_SEC = 1.0
DISCOVERY_ACTIVE_INTERVAL_SEC = 4.0
DISCOVERY_ERROR_RETRY_INTERVAL_SEC = 2.0
FILE_RETRY_INTERVAL_SEC = 5.0

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FingerprintAdapter(HTTPAdapter):
    """Pin a self-signed HTTPS peer to its LocalSend certificate fingerprint."""

    def __init__(self, fingerprint: str, *args, **kwargs):
        self.fingerprint = fingerprint
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["assert_fingerprint"] = self.fingerprint
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def cert_verify(self, conn, url, verify, cert):
        super().cert_verify(conn, url, verify, cert)
        # requests 2.32 may rebuild TLS pool attributes per request, so set the
        # urllib3 pool property here as well as during pool initialization.
        conn.assert_fingerprint = self.fingerprint

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
        self.ensure_fingerprint()
        self.tls_fingerprint = self.ensure_tls_identity()

        # ---------------- 顶部行：IP -----------------
        ttk.Label(self, text="IP 地址:", anchor="center").grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.ip_var = tk.StringVar(value=self.config_data["ip_addr"])
        self.ip_combo = ttk.Combobox(self, textvariable=self.ip_var, width=22, justify="center", state="normal")
        self.ip_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.ip_combo.bind("<<ComboboxSelected>>", self.on_device_selected)
        self.discovered_devices: dict[str, dict] = {}
        self.update_device_menu([])

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
        self.last_error = None  # 保存错误内容

        self.status_var = tk.StringVar(value="等待启动")
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor="center")
        self.status_label.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.status_label.bind("<Button-1>", lambda e: self.last_error and messagebox.showerror("错误详情", self.last_error))

        # 监控线程
        self.monitor_thread: threading.Thread | None = None
        self.discovery_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.shutdown_event = threading.Event()

        # 系统托盘
        self.protocol('WM_DELETE_WINDOW', self.quit_window)
        self.bind("<Unmap>", self.handle_minimize)
        self.setup_tray_icon()

        self.update_idletasks()
        self.deiconify()
        self.after(400, self.start_discovery_loop)

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
        self.shutdown_event.set()
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

    def ensure_fingerprint(self):
        fingerprint = str(self.config_data.get("fingerprint", "")).strip()
        if not fingerprint:
            fingerprint = uuid.uuid4().hex
            self.config_data["fingerprint"] = fingerprint
            self.write_config()
        return fingerprint

    def ensure_tls_identity(self) -> str:
        """Load or create the persistent mTLS identity required by LocalSend."""
        if os.path.exists(CLIENT_CERT_FILE) and os.path.exists(CLIENT_KEY_FILE):
            with open(CLIENT_CERT_FILE, "rb") as cert_file:
                cert = x509.load_pem_x509_certificate(cert_file.read())
            with open(CLIENT_KEY_FILE, "rb") as key_file:
                private_key = serialization.load_pem_private_key(key_file.read(), password=None)

            cert_public_key = cert.public_key().public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            key_public_key = private_key.public_key().public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            if cert_public_key != key_public_key:
                raise ValueError("Pic2Pad 客户端证书与私钥不匹配")
            return cert.fingerprint(hashes.SHA256()).hex().upper()

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "LocalSend User"),
        ])
        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=3650))
            .sign(private_key, hashes.SHA256())
        )

        key_bytes = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
        key_tmp = f"{CLIENT_KEY_FILE}.tmp"
        cert_tmp = f"{CLIENT_CERT_FILE}.tmp"
        with open(key_tmp, "wb") as key_file:
            key_file.write(key_bytes)
        with open(cert_tmp, "wb") as cert_file:
            cert_file.write(cert_bytes)
        os.replace(key_tmp, CLIENT_KEY_FILE)
        os.replace(cert_tmp, CLIENT_CERT_FILE)
        return cert.fingerprint(hashes.SHA256()).hex().upper()

    @staticmethod
    def normalize_fingerprint(value: str | None) -> str:
        fingerprint = str(value or "").replace(":", "").strip().upper()
        if len(fingerprint) != 64:
            return ""
        try:
            bytes.fromhex(fingerprint)
        except ValueError:
            return ""
        return fingerprint

    def create_http_session(
        self,
        protocol: str,
        target_fingerprint: str | None = None,
    ) -> requests.Session:
        session = requests.Session()
        # LocalSend is LAN-only; OS proxy settings can break direct peer/IP
        # binding and must never receive local transfer metadata or contents.
        session.trust_env = False
        if protocol == "https":
            session.cert = (CLIENT_CERT_FILE, CLIENT_KEY_FILE)
            fingerprint = self.normalize_fingerprint(target_fingerprint)
            if fingerprint:
                session.mount("https://", FingerprintAdapter(fingerprint))
        return session

    def get_https_peer_fingerprint(self, ip_addr: str, port: int, timeout: float = 3.0) -> str:
        """Read the peer identity over mTLS for first-use/manual-IP connections."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.load_cert_chain(CLIENT_CERT_FILE, CLIENT_KEY_FILE)
        with socket.create_connection((ip_addr, port), timeout=timeout) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=ip_addr) as tls_socket:
                cert_der = tls_socket.getpeercert(binary_form=True)
        if not cert_der:
            raise ssl.SSLError("对端未提供 TLS 证书")
        return hashlib.sha256(cert_der).hexdigest().upper()

    def get_port(self) -> int:
        try:
            return int(self.config_data.get("port", 53317))
        except (TypeError, ValueError):
            return 53317

    @staticmethod
    def protocol_candidates(preferred: str | None = None) -> list[str]:
        preferred = str(preferred or "").lower()
        protocols = []
        if preferred in ("http", "https"):
            protocols.append(preferred)
        for protocol in ("https", "http"):
            if protocol not in protocols:
                protocols.append(protocol)
        return protocols

    def build_discovery_payload(self, announce: bool = False) -> dict:
        payload = {
            "alias": self.config_data.get("user", "").strip() or "Pic2Pad",
            "version": "2.0",
            "deviceModel": self.config_data.get("device_name", "").strip() or socket.gethostname(),
            "deviceType": "desktop",
            "fingerprint": self.config_data.get("fingerprint", ""),
            "port": self.get_port(),
            "protocol": "http",
            "download": False,
        }
        if announce:
            payload["announce"] = True
        return payload

    @staticmethod
    def is_valid_ipv4(ip: str) -> bool:
        try:
            return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def is_usable_local_ipv4(ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except (TypeError, ValueError):
            return False
        return (
            isinstance(addr, ipaddress.IPv4Address)
            and not addr.is_loopback
            and not addr.is_link_local
            and not addr.is_multicast
            and not addr.is_unspecified
        )

    def get_local_ipv4s(self) -> list[str]:
        ips: list[str] = []
        seen: set[str] = set()

        def add_ip(ip: str):
            if self.is_usable_local_ipv4(ip) and ip not in seen:
                seen.add(ip)
                ips.append(ip)

        # 先通过系统路由表拿首选网卡地址。UDP connect 不会实际发包。
        for host, port in (("8.8.8.8", 80), ("1.1.1.1", 80), (MULTICAST_GROUP, self.get_port())):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                    probe.connect((host, port))
                    add_ip(probe.getsockname()[0])
            except OSError:
                pass

        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                add_ip(info[4][0])
        except OSError:
            pass

        return ips

    def normalize_discovered_device(
        self,
        payload: dict,
        ip_addr: str,
        default_port: int,
        default_protocol: str = "http",
    ) -> dict | None:
        if not isinstance(payload, dict):
            return None

        if not self.is_valid_ipv4(ip_addr):
            return None

        fingerprint = str(payload.get("fingerprint", "")).strip()
        own_fingerprints = {
            str(self.config_data.get("fingerprint", "")).upper(),
            str(self.tls_fingerprint).upper(),
        }
        if fingerprint and fingerprint.upper() in own_fingerprints:
            return None

        try:
            port = int(payload.get("port", default_port))
        except (TypeError, ValueError):
            port = default_port

        protocol = str(payload.get("protocol", default_protocol)).lower()
        if protocol not in ("http", "https"):
            protocol = "http"

        alias = str(payload.get("alias", "")).strip() or f"LocalSend@{ip_addr}"
        device_model = str(payload.get("deviceModel", "")).strip()
        device_type = str(payload.get("deviceType", "")).strip() or "desktop"

        return {
            "alias": alias,
            "ip": ip_addr,
            "port": port,
            "protocol": protocol,
            "deviceModel": device_model,
            "deviceType": device_type,
            "fingerprint": fingerprint,
        }

    @staticmethod
    def merge_device(devices: dict[str, dict], device: dict):
        key = device.get("fingerprint") or f"{device['protocol']}://{device['ip']}:{device['port']}"
        devices[key] = device

    def discover_via_multicast(self, timeout_sec: float = DISCOVERY_TIMEOUT_SEC) -> list[dict]:
        devices: dict[str, dict] = {}
        port = self.get_port()
        local_ips = self.get_local_ipv4s()
        payload = self.build_discovery_payload(announce=True)
        raw_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        listener = None
        sender = None
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(("", port))
            except OSError:
                listener.bind(("", 0))
            joined = False
            for ip in local_ips:
                try:
                    membership = struct.pack(
                        "4s4s",
                        socket.inet_aton(MULTICAST_GROUP),
                        socket.inet_aton(ip),
                    )
                    listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
                    joined = True
                except OSError:
                    continue

            if not joined:
                try:
                    membership = struct.pack(
                        "4s4s",
                        socket.inet_aton(MULTICAST_GROUP),
                        socket.inet_aton("0.0.0.0"),
                    )
                    listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
                except OSError:
                    pass
            listener.settimeout(0.2)

            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

            def send_announcement() -> bool:
                sent = False
                for ip in local_ips:
                    try:
                        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip))
                        sender.sendto(raw_payload, (MULTICAST_GROUP, port))
                        sent = True
                    except OSError:
                        continue
                if not sent:
                    try:
                        sender.sendto(raw_payload, (MULTICAST_GROUP, port))
                        sent = True
                    except OSError:
                        pass
                return sent

            start = time.time()
            deadline = start + max(0.5, timeout_sec)
            next_announce = 0
            while time.time() < deadline and not self.shutdown_event.is_set():
                elapsed = time.time() - start
                while (
                    next_announce < len(MULTICAST_ANNOUNCE_DELAYS_SEC)
                    and elapsed >= MULTICAST_ANNOUNCE_DELAYS_SEC[next_announce]
                ):
                    if not send_announcement():
                        return []
                    next_announce += 1

                try:
                    data, addr = listener.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    payload = json.loads(data.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                device = self.normalize_discovered_device(payload, addr[0], port, "http")
                if device:
                    self.merge_device(devices, device)
        finally:
            if listener:
                listener.close()
            if sender:
                sender.close()

        return list(devices.values())

    def discover_via_http_scan(self, request_timeout_sec: float = HTTP_DISCOVERY_TIMEOUT_SEC) -> list[dict]:
        devices: dict[str, dict] = {}
        port = self.get_port()
        local_ips = self.get_local_ipv4s()[:HTTP_SCAN_MAX_INTERFACES]
        local_ip_set = set(local_ips)

        candidates: list[str] = []
        seen_candidates: set[str] = set()

        def add_candidate(ip: str):
            if not self.is_valid_ipv4(ip):
                return
            if ip in local_ip_set or ip in seen_candidates:
                return
            seen_candidates.add(ip)
            candidates.append(ip)

        for local_ip in local_ips:
            prefix = ".".join(local_ip.split(".")[:3])
            for host in range(256):
                add_candidate(f"{prefix}.{host}")

        protocols = self.protocol_candidates(self.config_data.get("target_protocol"))
        discovery_payload = self.build_discovery_payload()

        def probe(target_ip: str) -> dict | None:
            if self.shutdown_event.is_set():
                return None
            for protocol in protocols:
                url = f"{protocol}://{target_ip}:{port}/api/localsend/v2/register"
                try:
                    request_payload = dict(discovery_payload)
                    request_payload["protocol"] = protocol
                    request_payload["fingerprint"] = (
                        self.tls_fingerprint
                        if protocol == "https"
                        else self.config_data.get("fingerprint", "")
                    )
                    with self.create_http_session(protocol) as session:
                        response = session.post(
                            url,
                            json=request_payload,
                            timeout=(0.2, request_timeout_sec),
                            verify=protocol != "https",
                        )
                    if response.status_code != 200:
                        continue
                    payload = response.json()
                    if protocol == "https":
                        payload["fingerprint"] = self.get_https_peer_fingerprint(
                            target_ip,
                            port,
                            timeout=max(2.0, request_timeout_sec),
                        )
                except Exception:
                    continue
                return self.normalize_discovered_device(payload, target_ip, port, protocol)
            return None

        if not candidates:
            return []

        pool = ThreadPoolExecutor(max_workers=HTTP_SCAN_WORKERS)
        pending: set = set()
        candidate_iter = iter(candidates)
        try:
            warmup = min(len(candidates), HTTP_SCAN_WORKERS)
            for _ in range(warmup):
                target_ip = next(candidate_iter, None)
                if not target_ip:
                    break
                pending.add(pool.submit(probe, target_ip))

            while pending and not self.shutdown_event.is_set():
                done, _ = wait(
                    pending,
                    timeout=0.25,
                    return_when=FIRST_COMPLETED,
                )
                if not done:
                    continue

                for future in done:
                    pending.discard(future)
                    try:
                        device = future.result()
                    except Exception:
                        device = None
                    if device:
                        self.merge_device(devices, device)

                    next_ip = next(candidate_iter, None)
                    if next_ip and not self.shutdown_event.is_set():
                        pending.add(pool.submit(probe, next_ip))
        finally:
            for future in pending:
                future.cancel()
            pool.shutdown(wait=False, cancel_futures=True)

        return list(devices.values())

    def update_device_menu(self, devices: list[dict], scanning: bool = False):
        self.discovered_devices = {}
        labels = []
        for item in sorted(devices, key=lambda d: (d["alias"].lower(), d["ip"])):
            label = f"{item['alias']} ({item['ip']}:{item['port']})"
            if item.get("deviceType"):
                label += f" [{item['deviceType']}]"
            base = label
            idx = 2
            while label in self.discovered_devices:
                label = f"{base} #{idx}"
                idx += 1
            self.discovered_devices[label] = item
            labels.append(label)
        self.ip_combo.configure(values=tuple(labels))

    def start_discovery_loop(self):
        if self.discovery_thread and self.discovery_thread.is_alive():
            return
        self.update_device_menu([], scanning=True)
        self.discovery_thread = threading.Thread(target=self.discovery_loop_worker, daemon=True)
        self.discovery_thread.start()

    def discovery_loop_worker(self):
        known_devices: dict[str, dict] = {}
        first_round = True

        while not self.shutdown_event.is_set():
            round_devices: dict[str, dict] = {}
            error_text = None

            try:
                multicast_timeout = SMART_SCAN_LEGACY_DELAY_SEC if not known_devices else DISCOVERY_TIMEOUT_SEC
                for device in self.discover_via_multicast(timeout_sec=multicast_timeout):
                    self.merge_device(round_devices, device)

                # Match LocalSend Smart Scan: only run legacy subnet scan when multicast found nothing.
                if not round_devices and not known_devices:
                    for device in self.discover_via_http_scan():
                        self.merge_device(round_devices, device)
            except Exception as exc:
                error_text = str(exc)

            if round_devices:
                known_devices = round_devices

            self.after(0, self.on_discovery_tick, list(known_devices.values()), error_text, first_round)

            first_round = False

            if error_text:
                sleep_sec = DISCOVERY_ERROR_RETRY_INTERVAL_SEC
            elif known_devices:
                sleep_sec = DISCOVERY_ACTIVE_INTERVAL_SEC
            else:
                sleep_sec = DISCOVERY_IDLE_INTERVAL_SEC

            for _ in range(max(1, int(sleep_sec * 10))):
                if self.shutdown_event.is_set():
                    break
                time.sleep(0.1)

    def on_discovery_tick(self, devices: list[dict], error_text: str | None, first_round: bool):
        self.update_device_menu(devices, scanning=not devices)

        if devices:
            if self.status_var.get() in ("等待启动", "未发现设备，后台持续扫描中"):
                self.status_var.set(f"已发现 {len(devices)} 台设备")
            return

        if error_text and first_round:
            self.last_error = error_text
            if self.status_var.get() == "等待启动":
                self.status_var.set("设备扫描异常 [点击查看详情]")
        elif self.status_var.get() == "等待启动":
            self.status_var.set("未发现设备，后台持续扫描中")

    def on_device_selected(self, event=None):
        selected_label = self.ip_var.get().strip()
        item = self.discovered_devices.get(selected_label)
        if not item:
            return
        self.ip_var.set(item["ip"])
        self.config_data["ip_addr"] = item["ip"]
        self.config_data["port"] = item["port"]
        self.config_data["target_protocol"] = item.get("protocol", "http")
        self.config_data["target_fingerprint"] = item.get("fingerprint", "")

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
        self.last_error = None
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
        retry_after: dict[str, float] = {}
        while not self.stop_event.is_set():
            time.sleep(1)
            current = set(os.listdir(folder_path))
            for fname in current - seen:
                if time.time() < retry_after.get(fname, 0):
                    continue
                full = os.path.join(folder_path, fname)
                if not os.path.isfile(full):
                    seen.add(fname)
                    continue
                self.after(0, self.status_var.set, f"发现新文件: {fname}")
                if self.send_file(full):
                    seen.add(fname)
                    retry_after.pop(fname, None)
                else:
                    retry_after[fname] = time.time() + FILE_RETRY_INTERVAL_SEC
            seen.intersection_update(current)
            for fname in list(retry_after):
                if fname not in current:
                    retry_after.pop(fname, None)

    @staticmethod
    def sha256_file(filename: str) -> str:
        digest = hashlib.sha256()
        with open(filename, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def wait_for_file_ready(filename: str, attempts: int = 10, interval: float = 0.2):
        """Wait until a newly-created screenshot has stopped growing."""
        previous_size = -1
        for _ in range(attempts):
            current_size = os.path.getsize(filename)
            if current_size > 0 and current_size == previous_size:
                return
            previous_size = current_size
            time.sleep(interval)
        raise TimeoutError("文件仍在写入，稍后自动重试")

    def send_file(self, filename: str) -> bool:
        self.last_error = None
        ip_addr = self.config_data["ip_addr"]
        port = self.get_port()
        user = self.config_data["user"] or "Pic2Pad"
        device_name = self.config_data["device_name"] or socket.gethostname()
        try:
            self.wait_for_file_ready(filename)
            file_id = uuid.uuid4().hex
            file_name = os.path.basename(filename)
            file_size = os.path.getsize(filename)
            file_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
            file_sha256 = self.sha256_file(filename)
        except Exception as exc:
            self.last_error = f"读取文件失败: {exc}"
            self.after(0, self.status_var.set, "读取文件失败，稍后重试 [点击查看详情]")
            return False

        def build_payload(protocol: str) -> dict:
            return {
                "info": {
                    "alias": user,
                    "version": "2.2",
                    "deviceModel": device_name,
                    "deviceType": "desktop",
                    "fingerprint": (
                        self.tls_fingerprint
                        if protocol == "https"
                        else self.config_data.get("fingerprint", "")
                    ),
                    "port": port,
                    "protocol": protocol,
                    "download": False,
                },
                "files": {
                    file_id: {
                        "id": file_id,
                        "fileName": file_name,
                        "size": file_size,
                        "fileType": file_type,
                        "sha256": file_sha256,
                        "preview": None,
                    }
                },
            }

        def try_send(protocol: str, payload: dict) -> str:
            target_fingerprint = ""
            if protocol == "https":
                observed_fingerprint = self.get_https_peer_fingerprint(ip_addr, port)
                saved_protocol = self.config_data.get("target_protocol")
                saved_fingerprint = self.normalize_fingerprint(
                    self.config_data.get("target_fingerprint")
                )
                if (
                    saved_protocol == "https"
                    and saved_fingerprint
                    and saved_fingerprint != observed_fingerprint
                ):
                    raise ssl.SSLError(
                        "iPad 的 TLS 证书指纹已变化；请在设备列表中重新选择该设备"
                    )
                target_fingerprint = observed_fingerprint

            url1 = f"{protocol}://{ip_addr}:{port}/api/localsend/v2/prepare-upload"
            with self.create_http_session(protocol, target_fingerprint) as session:
                response = session.post(
                    url1,
                    json=payload,
                    timeout=(3, 60),
                    verify=protocol != "https",
                )
                if response.status_code == 204:
                    return "skipped"
                response.raise_for_status()
                try:
                    data = response.json()
                except requests.exceptions.JSONDecodeError as exc:
                    body_preview = response.text[:200].strip() or "<空响应>"
                    raise ValueError(
                        f"prepare-upload 返回 HTTP {response.status_code}，"
                        f"但响应不是 JSON：{body_preview}"
                    ) from exc

                file_token = data.get("files", {}).get(file_id)
                if not file_token:
                    return "skipped"

                url2 = f"{protocol}://{ip_addr}:{port}/api/localsend/v2/upload"
                with open(filename, "rb") as file_obj:
                    upload_response = session.post(
                        url2,
                        params={
                            "sessionId": data["sessionId"],
                            "fileId": file_id,
                            "token": file_token,
                        },
                        data=file_obj,
                        timeout=(3, 60),
                        verify=protocol != "https",
                    )
                    upload_response.raise_for_status()
            return "uploaded"

        errors = []
        for protocol in self.protocol_candidates(self.config_data.get("target_protocol")):
            payload = build_payload(protocol)
            try:
                result = try_send(protocol, payload)
                config_changed = self.config_data.get("target_protocol") != protocol
                if config_changed:
                    self.config_data["target_protocol"] = protocol
                if protocol == "https":
                    current_fingerprint = self.get_https_peer_fingerprint(ip_addr, port)
                    if self.config_data.get("target_fingerprint") != current_fingerprint:
                        self.config_data["target_fingerprint"] = current_fingerprint
                        config_changed = True
                if config_changed:
                    self.write_config()
                if result == "skipped":
                    status = f"无需传输（接收端已处理）: {file_name}"
                else:
                    status = f"传输完成: {file_name}"
                self.after(0, self.status_var.set, status)
                return True
            except Exception as exc:
                errors.append(f"{protocol}: {exc}")
                if not isinstance(
                    exc,
                    (requests.exceptions.ConnectionError, requests.exceptions.SSLError),
                ):
                    break

        # except Exception as exc:
        #     self.status_var.set(f"传输失败！请尝试重启平板端Localsend")
        self.last_error = "\n".join(errors)
        self.after(0, self.status_var.set, "传输失败 [点击查看详情]")
        return False

if __name__ == "__main__":
    app = LocalSendGUI()
    app.mainloop()
