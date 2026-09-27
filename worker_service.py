import os
import threading

from flask import Flask, jsonify

from worker import SMSWorker


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# WORKER
# =========================================================

worker = SMSWorker()


_worker_started = False
_worker_lock = threading.Lock()


def start_worker():
    global _worker_started

    with _worker_lock:

        if _worker_started:
            return

        _worker_started = True

        thread = threading.Thread(
            target=worker.run,
            name="sms-worker",
            daemon=True,
        )

        thread.start()

        print(
            "[WORKER SERVICE] Background SMS worker started."
        )


# =========================================================
# START WORKER
# =========================================================

start_worker()


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def home():

    return jsonify({
        "service": "KarumeSMS Worker",
        "status": "running",
    })


@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "worker": "running",
    })


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )
