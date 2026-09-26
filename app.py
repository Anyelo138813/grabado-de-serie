import configparser
import ipaddress
import os
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from cloud_log_uploader import CloudLogUploader
from tcp_client_app import CODE_PATTERN, TcpClientApp


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
PROJECT_DIR = APP_DIR.parent / "WB+SNV2"
CONFIG_PATH = APP_DIR / "settings.ini"
LOG_DIR = APP_DIR / "Logs"
RECONNECT_DELAY_MS = 3000
CLOSE_PASSWORD = "1969"

TYPE_LEN = {
    # Filtro por longitud esperada segun el tipo seleccionado en "Code type".
    # SN debe tener 15 caracteres, DSN 16 caracteres y 3TE 23 caracteres.
    "SN": 15,
    "DSN": 16,
    "3TE": 23,
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TCP Client")
        self.geometry("500x550")
        self.resizable(False, False)

        self.client = TcpClientApp(self)
        self.connected = False
        self.connecting = False
        self.closing = False
        self.manual_disconnect_requested = False
        self.auto_reconnect_enabled = False
        self.reconnect_after_id = None
        self.reconnect_attempt = 0
        self.active_ip = None
        self.active_port = None
        self.active_code_type = None
        self.active_expected_length = None
        self.settings = self._load_settings()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.cloud_logger = CloudLogUploader(APP_DIR, self.settings)
        self.cloud_logger.start()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        logo_path = self._resource_path("HisenseLogo.png")
        if not logo_path.exists():
            logo_path = PROJECT_DIR / "HisenseLogo.png"
        self.logo_image = None
        if logo_path.exists():
            try:
                self.logo_image = self._load_logo_image(logo_path, max_width=300, max_height=48)
                logo = ttk.Label(self, image=self.logo_image)
                logo.place(x=33, y=12, width=self.logo_image.width(), height=self.logo_image.height())
            except Exception:
                pass

        ttk.Label(self, text="Server IP:").place(x=29, y=90)
        ttk.Label(self, text="Port:").place(x=29, y=135)
        ttk.Label(self, text="Code type:").place(x=29, y=182)
        ttk.Label(self, text="Log:").place(x=30, y=231)

        self.txt_server_ip = ttk.Entry(self)
        self.txt_server_ip.place(x=114, y=87, width=167, height=26)
        self.txt_server_ip.insert(0, self.settings.get("LastIP", "192.168."))

        self.txt_server_port = ttk.Entry(self)
        self.txt_server_port.place(x=114, y=132, width=167, height=26)
        self.txt_server_port.insert(0, self.settings.get("LastPort", "6000"))

        self.cmb_code_type = ttk.Combobox(self, values=list(TYPE_LEN.keys()), state="readonly")
        self.cmb_code_type.place(x=114, y=179, width=167, height=28)
        self.cmb_code_type.current(0)

        self.btn_connect = tk.Button(
            self,
            text="Connect",
            bg="teal",
            fg="white",
            activebackground="teal",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Times New Roman", 14, "bold"),
            command=self._connect_button_clicked,
        )
        self.btn_connect.place(x=316, y=88, width=131, height=73)

        self.txt_logs = tk.Text(self, state=tk.DISABLED, wrap=tk.WORD)
        self.txt_logs.place(x=50, y=258, width=397, height=196)

    def _connect_button_clicked(self):
        if self.connected:
            self._disconnect_clicked()
            return
        if self.connecting:
            return

        self._connect_clicked()

    def _connect_clicked(self):
        ip = self.txt_server_ip.get().strip()
        if not self._is_valid_ip(ip):
            self.append_log("IP invalida. Completa la direccion, ejemplo: 192.168.1.10")
            return

        try:
            port = int(self.txt_server_port.get())
        except ValueError:
            self.append_log("Puerto invalido.")
            return

        if port < 1 or port > 65535:
            self.append_log("Puerto invalido. Debe estar entre 1 y 65535.")
            return

        code_type = self.get_code_type()
        expected_length = TYPE_LEN.get(code_type, 15)
        self.manual_disconnect_requested = False
        self.auto_reconnect_enabled = False
        self._cancel_reconnect()
        self.connecting = True
        self.set_connect_enabled(False)
        self.btn_connect.configure(text="Connecting...")
        self.cmb_code_type.configure(state=tk.DISABLED)
        self.after(10, lambda: self._connect_background(ip, port, code_type, expected_length))

    def _disconnect_clicked(self):
        self.manual_disconnect_requested = True
        self.auto_reconnect_enabled = False
        self._cancel_reconnect()
        self.append_log("Desconectando por solicitud del usuario.")
        self.append_connection_log("Desconexion manual solicitada.")
        self.set_connect_enabled(False)
        self.client.disconnect()

    def _connect_background(self, ip, port, code_type, expected_length, is_reconnect=False):
        import threading

        def worker():
            try:
                self.client.connect(ip, port, code_type, expected_length)
                self.call_on_ui(lambda: self._connected_ok(ip, port, code_type, expected_length, is_reconnect))
            except Exception as exc:
                self.call_on_ui(lambda exc=exc: self._connected_error(exc, is_reconnect))

        threading.Thread(target=worker, daemon=True).start()

    def _connected_ok(self, ip, port, code_type, expected_length, is_reconnect=False):
        self.connecting = False
        self.connected = True
        self.manual_disconnect_requested = False
        self.auto_reconnect_enabled = True
        self.reconnect_attempt = 0
        self.active_ip = ip
        self.active_port = port
        self.active_code_type = code_type
        self.active_expected_length = expected_length
        self.cmb_code_type.set(code_type)
        self.append_log("Reconectado." if is_reconnect else "Conectado.")
        self.append_connection_log(f"Conexion activa: remoto={ip}:{port} tipo={code_type}")
        self.settings["LastIP"] = ip
        self.settings["LastPort"] = str(port)
        self._save_settings()
        self.btn_connect.configure(text="Disconnect")
        self.set_connect_enabled(True)
        self.cmb_code_type.configure(state=tk.DISABLED)

    def _connected_error(self, exc, is_reconnect=False):
        self.connecting = False
        self.connected = False
        if is_reconnect and self.auto_reconnect_enabled and not self.manual_disconnect_requested and not self.closing:
            self.append_connection_log(f"Fallo de reconexion: {exc}")
            self._schedule_reconnect()
            return

        self.append_log(f"Error al conectar: {exc}")
        self.append_connection_log(f"Error al conectar: {exc}")
        self.auto_reconnect_enabled = False
        self._set_disconnected_controls()

    def on_client_disconnected(self, reason="Conexion TCP finalizada."):
        if self.closing:
            return

        self.append_connection_log(reason)
        self.connecting = False
        self.connected = False

        if self.manual_disconnect_requested:
            self.append_log("Desconectado por solicitud del usuario.")
            self.append_connection_log("Reconexiones canceladas por desconexion manual.")
            self.manual_disconnect_requested = False
            self._set_disconnected_controls()
            return

        self.append_log(reason)
        self.append_log("Desconectado inesperado.")
        if (
            self.auto_reconnect_enabled
            and self.active_ip is not None
            and self.active_port is not None
            and self.active_code_type is not None
            and self.active_expected_length is not None
        ):
            self._schedule_reconnect()
        else:
            self._set_disconnected_controls()

    def _set_disconnected_controls(self):
        self.btn_connect.configure(text="Connect")
        self.set_connect_enabled(True)
        self.cmb_code_type.configure(state="readonly")

    def _schedule_reconnect(self):
        if self.reconnect_after_id is not None or self.closing or self.manual_disconnect_requested:
            return
        self.reconnect_attempt += 1
        self.btn_connect.configure(text="Reconnecting...")
        self.set_connect_enabled(False)
        self.cmb_code_type.configure(state=tk.DISABLED)
        self.append_log(f"Reintentando conexion en {RECONNECT_DELAY_MS // 1000} segundos...")
        self.append_connection_log(
            f"Reintento programado #{self.reconnect_attempt}: remoto={self.active_ip}:{self.active_port}"
        )
        self.reconnect_after_id = self.after(RECONNECT_DELAY_MS, self._run_reconnect)

    def _run_reconnect(self):
        self.reconnect_after_id = None
        if self.closing or self.manual_disconnect_requested or not self.auto_reconnect_enabled:
            return
        if (
            self.active_ip is None
            or self.active_port is None
            or self.active_code_type is None
            or self.active_expected_length is None
        ):
            self._set_disconnected_controls()
            return
        self.connecting = True
        self.cmb_code_type.set(self.active_code_type)
        self.append_connection_log(f"Ejecutando reintento #{self.reconnect_attempt} tipo={self.active_code_type}.")
        self._connect_background(
            self.active_ip,
            self.active_port,
            self.active_code_type,
            self.active_expected_length,
            is_reconnect=True,
        )

    def _cancel_reconnect(self):
        if self.reconnect_after_id is not None:
            try:
                self.after_cancel(self.reconnect_after_id)
            except tk.TclError:
                pass
            self.reconnect_after_id = None

    def append_log(self, msg):
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}"[:-3] + f" | {msg}"
        self.txt_logs.configure(state=tk.NORMAL)
        self.txt_logs.insert(tk.END, line + os.linesep)
        self.txt_logs.see(tk.END)
        self.txt_logs.configure(state=tk.DISABLED)
        try:
            with self._get_log_path().open("a", encoding="utf-8") as f:
                f.write(line + os.linesep)
        except OSError:
            pass
        self._record_cloud_event("app", msg)

    def append_received_log(self, raw):
        # Guarda lo recibido antes de cualquier validacion. repr muestra CR/LF y
        # caracteres especiales sin modificar el dato usado por el programa.
        self._append_file_log(self._get_received_log_path(), f"len={len(raw)} data={repr(raw)}")
        self._record_cloud_event("received", f"len={len(raw)} data={repr(raw)}")

    def append_sent_log(self, code, detail=""):
        code_type = self.active_code_type or self.get_code_type()
        extra = f" detalle={detail}" if detail else ""
        self._append_file_log(self._get_sent_log_path(), f"tipo={code_type} len={len(code)} data={code}{extra}")
        self._record_cloud_event("sent", detail or "Codigo enviado a HSmartTest", code=code)

    def append_connection_log(self, msg):
        self._append_file_log(self._get_connection_log_path(), msg)
        self._record_cloud_event("connection", msg)

    @staticmethod
    def _append_file_log(path, msg):
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}"[:-3] + f" | {msg}"
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(line + os.linesep)
        except OSError:
            pass

    def is_code_valid(self, code):
        # Valida el codigo usando el tipo seleccionado actualmente en la pantalla.
        return self.is_code_valid_for_type(code, self.get_code_type(), self.get_expected_length())

    def is_code_valid_for_type(self, code, code_type, expected_length):
        # Primer filtro: la longitud debe coincidir exactamente con el tipo seleccionado
        # y solo se permiten letras mayusculas A-Z y numeros 0-9.
        if len(code) != expected_length or CODE_PATTERN.match(code) is None:
            return False
        # SN: debe iniciar con 2 numeros y 1 letra, o A/B seguido de numero.
        # Ademas, el caracter 10 debe ser H.
        if code_type == "SN":
            starts_with_sn_pattern = (
                (code[0:2].isdigit() and code[2].isalpha())
                or (code[0] in ("A", "B") and code[1].isdigit())
            )
            if not starts_with_sn_pattern or code[9] != "H":
                return False
        # Segundo filtro: si el tipo es DSN, el codigo debe iniciar con "G5T".
        if code_type == "DSN" and not code.startswith("G5T"):
            return False
        # Tercer filtro: si el tipo es 3TE, el codigo debe iniciar con "3TE".
        if code_type == "3TE" and not code.startswith("3TE"):
            return False
        # Si pasa todos los filtros anteriores, el codigo se considera valido.
        return True

    def get_code_type(self):
        return self.cmb_code_type.get()

    def get_expected_length(self):
        return TYPE_LEN.get(self.get_code_type(), 15)

    @staticmethod
    def _is_valid_ip(value):
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    def set_connect_enabled(self, enabled):
        self.btn_connect.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def call_on_ui(self, callback):
        self.after(0, callback)

    @staticmethod
    def _load_logo_image(path, max_width, max_height):
        image = tk.PhotoImage(file=str(path))
        width_factor = (image.width() + max_width - 1) // max_width
        height_factor = (image.height() + max_height - 1) // max_height
        scale_factor = max(1, width_factor, height_factor)
        if scale_factor > 1:
            image = image.subsample(scale_factor, scale_factor)
        return image

    @staticmethod
    def _get_log_path():
        return LOG_DIR / f"TcpClientLog_{datetime.now():%Y-%m-%d}.txt"

    @staticmethod
    def _get_received_log_path():
        return LOG_DIR / f"ReceivedLog_{datetime.now():%Y-%m-%d}.txt"

    @staticmethod
    def _get_sent_log_path():
        return LOG_DIR / f"SentLog_{datetime.now():%Y-%m-%d}.txt"

    @staticmethod
    def _get_connection_log_path():
        return LOG_DIR / f"ConnectionLog_{datetime.now():%Y-%m-%d}.txt"

    @staticmethod
    def _resource_path(name):
        return RESOURCE_DIR / name

    def _load_settings(self):
        config = configparser.ConfigParser()
        if CONFIG_PATH.exists():
            config.read(CONFIG_PATH, encoding="utf-8")
        return {
            "LastIP": config.get("Settings", "LastIP", fallback="192.168."),
            "LastPort": config.get("Settings", "LastPort", fallback="6000"),
            "CloudLogsEnabled": config.get("CloudLogs", "Enabled", fallback="false"),
            "CloudMode": config.get("CloudLogs", "Mode", fallback="folder"),
            "CloudLineId": config.get("CloudLogs", "LineId", fallback="LINEA_1"),
            "CloudFolderPath": config.get("CloudLogs", "FolderPath", fallback=""),
            "CloudCopyTodayLogs": config.get("CloudLogs", "CopyTodayLogs", fallback="true"),
            "CloudUploadReceived": config.get("CloudLogs", "UploadReceived", fallback="false"),
            "CloudFlushIntervalSeconds": config.get("CloudLogs", "FlushIntervalSeconds", fallback="60"),
            "CloudBatchSize": config.get("CloudLogs", "BatchSize", fallback="25"),
            "CloudSupabaseUrl": config.get("CloudLogs", "SupabaseUrl", fallback=""),
            "CloudSupabaseKey": config.get("CloudLogs", "SupabaseKey", fallback=""),
            "CloudSupabaseTable": config.get("CloudLogs", "SupabaseTable", fallback="tcp_client_events"),
        }

    def _save_settings(self):
        config = configparser.ConfigParser()
        config["Settings"] = {
            "LastIP": self.settings.get("LastIP", "192.168."),
            "LastPort": self.settings.get("LastPort", "6000"),
        }
        config["CloudLogs"] = {
            "Enabled": self.settings.get("CloudLogsEnabled", "false"),
            "Mode": self.settings.get("CloudMode", "folder"),
            "LineId": self.settings.get("CloudLineId", "LINEA_1"),
            "FolderPath": self.settings.get("CloudFolderPath", ""),
            "CopyTodayLogs": self.settings.get("CloudCopyTodayLogs", "true"),
            "UploadReceived": self.settings.get("CloudUploadReceived", "false"),
            "FlushIntervalSeconds": self.settings.get("CloudFlushIntervalSeconds", "60"),
            "BatchSize": self.settings.get("CloudBatchSize", "25"),
            "SupabaseUrl": self.settings.get("CloudSupabaseUrl", ""),
            "SupabaseKey": self.settings.get("CloudSupabaseKey", ""),
            "SupabaseTable": self.settings.get("CloudSupabaseTable", "tcp_client_events"),
        }
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            config.write(f)

    def _record_cloud_event(self, event_type, message, code=""):
        if not hasattr(self, "cloud_logger"):
            return
        try:
            self.cloud_logger.record(
                event_type=event_type,
                message=message,
                code_type=self.active_code_type or self.get_code_type(),
                code=code,
                ip=self.active_ip or self.txt_server_ip.get().strip(),
                port=self.active_port or self.txt_server_port.get().strip(),
            )
        except Exception:
            pass

    def _on_close(self):
        password = simpledialog.askstring(
            "Cerrar aplicacion",
            "Ingrese la contrasena para cerrar:",
            show="*",
            parent=self,
        )
        if password != CLOSE_PASSWORD:
            if password is not None:
                messagebox.showerror("Contrasena incorrecta", "La contrasena no es correcta.", parent=self)
            return

        self.closing = True
        self.auto_reconnect_enabled = False
        self._cancel_reconnect()
        self.cloud_logger.flush_once()
        self.cloud_logger.stop()
        self.client.disconnect()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
