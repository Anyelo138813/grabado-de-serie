import re
import socket
import threading

import send_keys_manager


CONNECT_TIMEOUT_SECONDS = 10


class TcpClientApp:
    def __init__(self, ui):
        self.ui = ui
        self.sock = None
        self.reader_thread = None
        self.stop_event = threading.Event()
        self.expected_len = 15
        self.code_type = "SN"

    def connect(self, ip, port, code_type=None, expected_len=None):
        self.disconnect()
        # Al conectar se congela el filtro elegido. En reconexiones se reutiliza
        # el mismo tipo para no depender del estado visual del combo.
        self.code_type = code_type if code_type is not None else self.ui.get_code_type()
        self.expected_len = expected_len if expected_len is not None else self.ui.get_expected_length()
        self.stop_event.clear()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.settimeout(CONNECT_TIMEOUT_SECONDS)
        sock.connect((ip, port))
        sock.settimeout(None)
        self.sock = sock
        if hasattr(self.ui, "append_connection_log"):
            self.ui.append_connection_log(f"Socket conectado: local={sock.getsockname()} remoto={sock.getpeername()}")

        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()

    def disconnect(self):
        self.stop_event.set()
        sock = self.sock
        self.sock = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def _read_loop(self):
        disconnect_reason = "Conexion TCP finalizada."
        try:
            while not self.stop_event.is_set():
                data = self.sock.recv(1024)
                if not data:
                    disconnect_reason = "Conexion TCP cerrada por el servidor/remoto."
                    break

                chunk = data.decode("ascii", errors="ignore")
                if hasattr(self.ui, "append_received_log"):
                    self.ui.append_received_log(chunk)
                self._process_chunk(chunk)
        except OSError as exc:
            if not self.stop_event.is_set():
                disconnect_reason = f"Error recepcion TCP: {exc}"
            else:
                disconnect_reason = "Conexion TCP cerrada localmente."
        finally:
            self.disconnect()
            self.ui.call_on_ui(lambda reason=disconnect_reason: self._notify_disconnected(reason))

    def _notify_disconnected(self, reason):
        if hasattr(self.ui, "on_client_disconnected"):
            self.ui.on_client_disconnected(reason)
        else:
            self.ui.append_log(reason)
            self.ui.set_connect_enabled(True)

    def _process_chunk(self, chunk):
        # Cada lectura recibida se valida como registro completo. No se guardan
        # pedazos en buffer ni se limpian separadores para intentar completarla.
        records = re.split(r"[\r\n]+", chunk)
        for record in records:
            self._process_record(record)

    def _process_record(self, record):
        raw = record.strip()
        if not raw:
            return

        # Filtro de lectura fallida para registros completos recibidos con salto de linea.
        if self._contains_no_read(self._clean(raw)):
            self.ui.call_on_ui(lambda: self.ui.append_log("NO READ (descartado)"))
            return

        # Filtro de formato: longitud, caracteres permitidos y prefijo segun tipo.
        if self._is_code_valid(raw):
            self.ui.call_on_ui(lambda code=raw: self._handle_code(code))
            return

        self.ui.call_on_ui(lambda raw=raw: self.ui.append_log("Codigo rechazado: " + raw))

    def _handle_code(self, code):
        # Ultima validacion antes de enviar el codigo a la ventana destino.
        if self._contains_no_read(code):
            self.ui.append_log("Bloque con NO READ descartado")
        elif self._is_code_valid(code):
            sent = send_keys_manager.send(code)
            if sent:
                if hasattr(self.ui, "append_sent_log"):
                    self.ui.append_sent_log(code)
                self.ui.append_log("Codigo OK: " + code)
            else:
                self.ui.append_log("Codigo valido, pero no se encontro HSmartTest: " + code)
        else:
            self.ui.append_log("Codigo rechazado: " + code)

    @staticmethod
    def _clean(raw):
        # Deja solo caracteres alfanumericos para poder filtrar datos continuos del lector.
        return "".join(ch for ch in raw if ch.isalnum())

    @staticmethod
    def _contains_no_read(text):
        # Detecta respuestas de lectura fallida sin importar mayusculas/minusculas.
        return "NOREAD" in text.upper()

    def _is_code_valid(self, code):
        # Usa la validacion de la UI para mantener un solo criterio de filtros.
        if hasattr(self.ui, "is_code_valid_for_type"):
            return self.ui.is_code_valid_for_type(code, self.code_type, self.expected_len)
        # Respaldo: longitud exacta y caracteres A-Z/0-9.
        if len(code) != self.expected_len or CODE_PATTERN.match(code) is None:
            return False
        # Respaldo SN: inicio valido y H en el caracter 10.
        if self.code_type == "SN":
            starts_with_sn_pattern = (
                (code[0:2].isdigit() and code[2].isalpha())
                or (code[0] in ("A", "B") and code[1].isdigit())
            )
            if not starts_with_sn_pattern or code[9] != "H":
                return False
        # Respaldo DSN: debe iniciar con G5T.
        if self.code_type == "DSN" and not code.startswith("G5T"):
            return False
        # Respaldo: el tipo 3TE debe iniciar con "3TE".
        if self.code_type == "3TE" and not code.startswith("3TE"):
            return False
        return True


# Patron usado por el filtro de formato: solo letras mayusculas y numeros.
CODE_PATTERN = re.compile(r"^[A-Z0-9]+$")
