import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, render_template
from monitor import Monitor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "events.db")

app = Flask(__name__)

class Store:
    def connect(self):
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self):
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                device TEXT NOT NULL,
                host TEXT,
                state TEXT NOT NULL,
                message TEXT NOT NULL,
                latency_ms REAL
            )""")

    def add_event(self, device, host, state, message, latency):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO events(created_at,device,host,state,message,latency_ms) VALUES(?,?,?,?,?,?)",
                (datetime.now().astimezone().isoformat(timespec="seconds"), device, host, state, message, latency),
            )

    def recent_events(self, limit=50):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

store = Store()
store.init()
monitor = Monitor(store)
monitor.start()

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/status")
def api_status():
    devices = monitor.snapshot()
    counts = {"UP": 0, "DOWN": 0, "PENDING": 0, "UNKNOWN": 0}
    for d in devices:
        counts[d["state"]] = counts.get(d["state"], 0) + 1
    return jsonify({"devices": devices, "counts": counts, "updated_at": datetime.now().astimezone().isoformat(timespec="seconds")})

@app.get("/api/events")
def api_events():
    return jsonify(store.recent_events())

if __name__ == "__main__":
    # Keep this bound to localhost for local testing. For Docker, use the internal container port.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=False)
