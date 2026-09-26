import socket
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk


DEFAULT_CODES = {
    "SN": "55N2617FNH00336",
    "DSN": "G5T1234567890123",
    "3TE": "3TE12345678901234567890",
    "NO READ": "NO READ",
}

NOISE_CODES = [
    "RUIDO123",
    "55N2617FN",
    "55N2617FNH00336###",
    "ABC-123-XYZ",
]


class TcpPortSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador TCP iVMS/IDVMS")
        self.geometry("610x520")
        self.resizable(False, False)

        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.stop_event = threading.Event()
        self.accept_thread = None
        self.auto_after_id = None
        self.auto_index = 0

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        ttk.Label(self, text="IP local:").place(x=24, y=24)
        ttk.Label(self, text="Puerto:").place(x=280, y=24)

        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="6000")
        self.code_type_var = tk.StringVar(value="SN")
        self.newline_var = tk.BooleanVar(value=True)
        self.include_noise_var = tk.BooleanVar(value=True)
        self.include_no_read_var = tk.BooleanVar(value=True)
        self.interval_var = tk.StringVar(value="3")

        self.host_entry = ttk.Entry(self, textvariable=self.host_var)
        self.host_entry.place(x=86, y=20, width=170, height=26)

        self.port_entry = ttk.Entry(self, textvariable=self.port_var)
        self.port_entry.place(x=335, y=20, width=80, height=26)

        self.start_button = ttk.Button(self, text="Iniciar puerto", command=self._start_server)
        self.start_button.place(x=430, y=18, width=105, height=30)

        self.stop_button = ttk.Button(self, text="Parar puerto", command=self._stop_server, state=tk.DISABLED)
        self.stop_button.place(x=430, y=55, width=105, height=30)

        ttk.Label(self, text="Tipo:").place(x=24, y=78)
        self.type_combo = ttk.Combobox(
            self,
            textvariable=self.code_type_var,
            values=list(DEFAULT_CODES.keys()),
            state="readonly",
        )
        self.type_combo.place(x=86, y=74, width=170, height=28)
        self.type_combo.bind("<<ComboboxSelected>>", self._load_default_code)

        self.newline_check = ttk.Checkbutton(self, text="Enviar con salto de linea", variable=self.newline_var)
        self.newline_check.place(x=280, y=76)

        ttk.Label(self, text="Codigo:").place(x=24, y=120)
        self.code_entry = ttk.Entry(self)
        self.code_entry.place(x=86, y=116, width=330, height=28)
        self.code_entry.insert(0, DEFAULT_CODES["SN"])

        self.send_button = ttk.Button(self, text="Enviar", command=self._send_code, state=tk.DISABLED)
        self.send_button.place(x=430, y=115, width=105, height=30)

        self.close_client_button = ttk.Button(
            self,
            text="Cortar cliente",
            command=self._close_client,
            state=tk.DISABLED,
        )
        self.close_client_button.place(x=430, y=152, width=105, height=30)

        self.send_sequence_button = ttk.Button(
            self,
            text="Secuencia",
            command=self._send_sequence,
            state=tk.DISABLED,
        )
        self.send_sequence_button.place(x=430, y=189, width=105, height=30)

        ttk.Label(self, text="Auto cada:").place(x=24, y=165)
        self.interval_entry = ttk.Entry(self, textvariable=self.interval_var)
        self.interval_entry.place(x=95, y=161, width=55, height=26)
        ttk.Label(self, text="seg.").place(x=156, y=165)

        self.noise_check = ttk.Checkbutton(self, text="Incluir ruido", variable=self.include_noise_var)
        self.noise_check.place(x=205, y=163)

        self.no_read_check = ttk.Checkbutton(self, text="Incluir NO READ", variable=self.include_no_read_var)
        self.no_read_check.place(x=315, y=163)

        self.auto_button = ttk.Button(
            self,
            text="Auto iniciar",
            command=self._toggle_auto_send,
            state=tk.DISABLED,
        )
        self.auto_button.place(x=430, y=226, width=105, height=30)

        ttk.Label(self, text="Log:").place(x=24, y=205)
        self.log_text = tk.Text(self, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.place(x=24, y=231, width=390, height=235)

        self.status_label = ttk.Label(self, text="Puerto detenido. Sin cliente.")
        self.status_label.place(x=24, y=488)

    def _load_default_code(self, _event=None):
        code = DEFAULT_CODES.get(self.code_type_var.get(), "")
        self.code_entry.delete(0, tk.END)
        self.code_entry.insert(0, code)

    def _start_server(self):
        if self.server_socket is not None:
            return

        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            self._log("Puerto invalido.")
            return

        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(1)
            server_socket.settimeout(1)
        except OSError as exc:
            self._log(f"No se pudo iniciar el puerto: {exc}")
            return

        self.server_socket = server_socket
        self.stop_event.clear()
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.host_entry.configure(state=tk.DISABLED)
        self.port_entry.configure(state=tk.DISABLED)
        self._set_client_controls(False)
        self._set_status(f"Escuchando en {host}:{port}.")
        self._log(f"Puerto iniciado en {host}:{port}.")

    def _accept_loop(self):
        while not self.stop_event.is_set():
            try:
                client_socket, address = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            self.after(0, lambda sock=client_socket, addr=address: self._client_connected(sock, addr))

    def _client_connected(self, client_socket, address):
        self._close_client(log=False)
        self.client_socket = client_socket
        self.client_address = address
        self._set_client_controls(True)
        self._set_status(f"Cliente conectado: {address[0]}:{address[1]}")
        self._log(f"Cliente conectado desde {address[0]}:{address[1]}.")

    def _send_code(self):
        code = self.code_entry.get()
        self._send_text(code)

    def _send_sequence(self):
        for code in DEFAULT_CODES.values():
            self._send_text(code)

    def _toggle_auto_send(self):
        if self.auto_after_id is None:
            self._start_auto_send()
        else:
            self._stop_auto_send()

    def _start_auto_send(self):
        if self.client_socket is None:
            self._log("No hay cliente conectado para auto envio.")
            return
        self.auto_index = 0
        self.auto_button.configure(text="Auto parar")
        self._log("Auto envio iniciado.")
        self._run_auto_send()

    def _stop_auto_send(self):
        if self.auto_after_id is not None:
            try:
                self.after_cancel(self.auto_after_id)
            except tk.TclError:
                pass
            self.auto_after_id = None
        self.auto_button.configure(text="Auto iniciar")
        self._log("Auto envio detenido.")

    def _run_auto_send(self):
        self.auto_after_id = None
        if self.client_socket is None:
            self._stop_auto_send()
            return

        messages = self._build_auto_messages()
        message = messages[self.auto_index % len(messages)]
        self.auto_index += 1
        self._send_text(message)

        try:
            interval_seconds = float(self.interval_var.get().strip())
        except ValueError:
            interval_seconds = 3
        interval_ms = max(1, int(interval_seconds * 1000))
        self.auto_after_id = self.after(interval_ms, self._run_auto_send)

    def _build_auto_messages(self):
        code_type = self.code_type_var.get()
        messages = [DEFAULT_CODES.get(code_type, self.code_entry.get())]
        if self.include_noise_var.get():
            messages.extend(NOISE_CODES)
        if self.include_no_read_var.get():
            messages.append(DEFAULT_CODES["NO READ"])
        return messages or [self.code_entry.get()]

    def _send_text(self, text):
        if self.client_socket is None:
            self._log("No hay cliente conectado.")
            return

        payload = text + ("\r\n" if self.newline_var.get() else "")
        try:
            self.client_socket.sendall(payload.encode("ascii", errors="ignore"))
            self._log(f"Enviado: {repr(payload)}")
        except OSError as exc:
            self._log(f"Error enviando, se corta cliente: {exc}")
            self._close_client(log=False)

    def _close_client(self, log=True):
        if self.auto_after_id is not None:
            self._stop_auto_send()
        sock = self.client_socket
        self.client_socket = None
        self.client_address = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
            if log:
                self._log("Cliente desconectado por el simulador.")
        self._set_client_controls(False)
        if self.server_socket is not None:
            self._set_status("Escuchando. Sin cliente conectado.")

    def _stop_server(self):
        if self.auto_after_id is not None:
            self._stop_auto_send()
        self.stop_event.set()
        self._close_client()
        sock = self.server_socket
        self.server_socket = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.host_entry.configure(state=tk.NORMAL)
        self.port_entry.configure(state=tk.NORMAL)
        self._set_status("Puerto detenido. Sin cliente.")
        self._log("Puerto detenido.")

    def _set_client_controls(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.send_button.configure(state=state)
        self.close_client_button.configure(state=state)
        self.send_sequence_button.configure(state=state)
        self.auto_button.configure(state=state)

    def _set_status(self, text):
        self.status_label.configure(text=text)

    def _log(self, message):
        line = f"{datetime.now():%H:%M:%S.%f}"[:-3] + f" | {message}"
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _on_close(self):
        self._stop_server()
        self.destroy()


if __name__ == "__main__":
    TcpPortSimulator().mainloop()
