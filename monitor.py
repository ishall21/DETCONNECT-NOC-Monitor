import os
import platform
import subprocess
import time
import threading
from datetime import datetime, timezone

import requests
import yaml
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "devices.yaml")
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Monitor:
    def __init__(self, store):
        self.store = store
        self.devices = []
        self.status = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.reload_config()

    def reload_config(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}
        self.devices = [d for d in self.config.get("devices", []) if d.get("enabled", False)]
        self.interval = max(10, int(self.config.get("poll_interval_seconds", 30)))
        self.timeout = max(1, int(self.config.get("timeout_seconds", 2)))

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.stop_event.is_set():
            for device in self.devices:
                if self.stop_event.is_set():
                    break
                result = self.check_device(device)
                self._record_transition(device, result)
                with self.lock:
                    self.status[device["name"]] = result
            self.stop_event.wait(self.interval)

    def check_device(self, device):
        host = str(device.get("host", "")).strip()
        start = time.perf_counter()
        if not host:
            return {"state": "UNKNOWN", "latency_ms": None, "checked_at": now(), "error": "Missing host"}
        # Host is sourced from a local administrator-controlled YAML inventory.
        count_flag = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_flag = "-w" if platform.system().lower() == "windows" else "-W"
        timeout_value = str(max(1, self.timeout * 1000 if platform.system().lower() == "windows" else self.timeout))
        cmd = ["ping", count_flag, "1", timeout_flag, timeout_value, host]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 3)
            latency = round((time.perf_counter() - start) * 1000, 2) if proc.returncode == 0 else None
            state = "UP" if proc.returncode == 0 else "DOWN"
            return {"state": state, "latency_ms": latency, "checked_at": now(), "error": None}
        except Exception as exc:
            return {"state": "DOWN", "latency_ms": None, "checked_at": now(), "error": str(exc)[:180]}

    def _record_transition(self, device, result):
        name = device["name"]
        previous = self.status.get(name, {}).get("state")
        state = result["state"]
        if previous != state:
            message = f'{device["name"]} ({device.get("host", "unknown")}) changed: {previous or "NO DATA"} → {state}'
            self.store.add_event(name, device.get("host", ""), state, message, result.get("latency_ms"))
            if previous is not None:
                send_telegram(message)

    def snapshot(self):
        with self.lock:
            current = dict(self.status)
        rows = []
        for d in self.devices:
            r = current.get(d["name"], {"state": "PENDING", "latency_ms": None, "checked_at": None, "error": None})
            rows.append({**d, **r})
        return rows

def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": f"🚨 DETCONNECT NOC\n{message}"},
            timeout=5,
        ).raise_for_status()
    except requests.RequestException:
        # Monitoring must continue even if Telegram is temporarily unavailable.
        pass
