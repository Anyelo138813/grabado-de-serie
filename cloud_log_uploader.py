import json
import os
import shutil
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_FLUSH_INTERVAL_SECONDS = 60
DEFAULT_BATCH_SIZE = 25
MAX_EVENT_CHARS = 1000


class CloudLogUploader:
    def __init__(self, app_dir, config):
        self.app_dir = Path(app_dir)
        self.config = config
        self.enabled = self._is_enabled()
        self.mode = config.get("CloudMode", "folder").strip().lower()
        self.upload_received = self._as_bool(config.get("CloudUploadReceived", "false"))
        self.line_id = config.get("CloudLineId", "LINEA_1")
        self.folder_path = Path(config.get("CloudFolderPath", "")).expanduser()
        self.copy_today_logs = self._as_bool(config.get("CloudCopyTodayLogs", "true"))
        self.table = config.get("CloudSupabaseTable", "tcp_client_events")
        self.supabase_url = config.get("CloudSupabaseUrl", "").rstrip("/")
        self.supabase_key = config.get("CloudSupabaseKey", "")
        self.flush_interval = self._as_int(
            config.get("CloudFlushIntervalSeconds", DEFAULT_FLUSH_INTERVAL_SECONDS),
            DEFAULT_FLUSH_INTERVAL_SECONDS,
        )
        self.batch_size = self._as_int(config.get("CloudBatchSize", DEFAULT_BATCH_SIZE), DEFAULT_BATCH_SIZE)
        self.queue_dir = self.app_dir / "CloudQueue"
        self.queue_path = self.queue_dir / "pending_events.jsonl"
        self.stop_event = threading.Event()
        self.thread = None
        self.lock = threading.Lock()

    def start(self):
        if not self.enabled:
            return
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=2)

    def record(self, event_type, message, code_type="", code="", ip="", port=""):
        if not self.enabled:
            return
        if event_type == "received" and not self.upload_received:
            return

        event = {
            "event_time": datetime.now().isoformat(timespec="milliseconds"),
            "line_id": self.line_id,
            "event_type": self._limit(event_type, 50),
            "code_type": self._limit(code_type, 20),
            "code": self._limit(code, 120),
            "message": self._limit(message, MAX_EVENT_CHARS),
            "ip": self._limit(ip, 50),
            "port": self._limit(str(port), 10),
        }
        self._append_event(event)

    def _run(self):
        while not self.stop_event.wait(self.flush_interval):
            self.flush_once()

    def flush_once(self):
        if self.mode == "folder":
            self._copy_log_files()
            return

        if not self._has_upload_config():
            return
        batch, remaining = self._read_batch()
        if not batch:
            return
        if self._upload_batch(batch):
            self._rewrite_queue(remaining)

    def _append_event(self, event):
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
        with self.lock:
            with self.queue_path.open("a", encoding="utf-8") as f:
                f.write(line + os.linesep)

    def _read_batch(self):
        with self.lock:
            if not self.queue_path.exists():
                return [], []
            try:
                lines = self.queue_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return [], []

        events = []
        valid_lines = []
        for line in lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            valid_lines.append(line)
            if len(events) < self.batch_size:
                events.append(event)

        remaining = valid_lines[len(events):]
        return events, remaining

    def _rewrite_queue(self, remaining_lines):
        with self.lock:
            if remaining_lines:
                tmp_path = self.queue_path.with_suffix(".tmp")
                tmp_path.write_text(os.linesep.join(remaining_lines) + os.linesep, encoding="utf-8")
                tmp_path.replace(self.queue_path)
            else:
                try:
                    self.queue_path.unlink()
                except OSError:
                    pass

    def _upload_batch(self, events):
        url = f"{self.supabase_url}/rest/v1/{self.table}"
        data = json.dumps(events, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return 200 <= response.status < 300
        except (OSError, urllib.error.URLError, urllib.error.HTTPError):
            return False

    def _has_upload_config(self):
        return bool(self.mode == "supabase" and self.supabase_url and self.supabase_key and self.table)

    def _copy_log_files(self):
        if not self.folder_path:
            return

        log_dir = self.app_dir / "Logs"
        if not log_dir.exists():
            return

        dates = [datetime.now().date()]
        yesterday = datetime.now().date() - timedelta(days=1)
        if yesterday not in dates:
            dates.append(yesterday)

        for log_date in dates:
            if log_date == datetime.now().date() and not self.copy_today_logs:
                continue
            date_text = log_date.strftime("%Y-%m-%d")
            destination_dir = self.folder_path / self.line_id / date_text
            for prefix in ("TcpClientLog", "ReceivedLog", "SentLog", "ConnectionLog"):
                source = log_dir / f"{prefix}_{date_text}.txt"
                if source.exists():
                    self._copy_file_atomic(source, destination_dir / source.name)

    @staticmethod
    def _copy_file_atomic(source, destination):
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp_destination = destination.with_suffix(destination.suffix + ".tmp")
            shutil.copy2(str(source), str(temp_destination))
            temp_destination.replace(destination)
        except OSError:
            pass

    def _is_enabled(self):
        return self._as_bool(self.config.get("CloudLogsEnabled", "false"))

    @staticmethod
    def _as_bool(value):
        return str(value).strip().lower() in ("1", "true", "yes", "si", "on")

    @staticmethod
    def _as_int(value, fallback):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        return max(1, parsed)

    @staticmethod
    def _limit(value, max_len):
        text = "" if value is None else str(value)
        if len(text) <= max_len:
            return text
        return text[:max_len]
