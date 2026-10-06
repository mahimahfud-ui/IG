import json
import os
import random
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="web", static_url_path="")

jobs = {}
jobs_lock = threading.Lock()

DEFAULT_CONFIG = {
    "delay_min": 60,
    "delay_max": 300,
    "break_probability": 0.10,
    "break_min": 900,
    "break_max": 3600,
    "max_retries": 3,
    "retry_delay": 60,
}


def media_id_from_url(url: str) -> int:
    charmap = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    code = url.rstrip("/").split("/")[-1]
    return sum(charmap.index(ch) * (64 ** i) for i, ch in enumerate(reversed(code)))


def set_job(job_id, **values):
    with jobs_lock:
        jobs.setdefault(job_id, {}).update(values)


def get_job(job_id):
    with jobs_lock:
        return dict(jobs.get(job_id, {}))


def worker(job_id, username, password, liked_data, config):
    try:
        from ensta import Web
    except Exception as exc:
        set_job(job_id, status="error", error=f"ensta could not be loaded: {exc}")
        return

    try:
        set_job(job_id, status="connecting", message="Connecting to Instagram…")
        client = Web(username, password)
        account = client.private_info()
        display_name = getattr(account, "username", username)

        posts = list(liked_data.get("likes_media_likes", []))
        total = len(posts)
        if not total:
            set_job(job_id, status="complete", progress=100, total=0, completed=0,
                    message="No liked posts were found in the uploaded JSON.")
            return

        set_job(job_id, status="running", total=total, completed=0, progress=0,
                account=display_name, message=f"Found {total} liked posts.")

        completed = 0
        while posts:
            current = posts[0]
            href = current.get("string_list_data", [{}])[0].get("href")
            if not href:
                posts.pop(0)
                continue

            delay = random.uniform(float(config["delay_min"]), float(config["delay_max"]))
            set_job(job_id, status="waiting", wait_seconds=round(delay),
                    message="Respecting your configured delay…")
            for _ in range(max(1, int(delay))):
                if get_job(job_id).get("cancelled"):
                    set_job(job_id, status="cancelled", message="Run stopped.")
                    return
                time.sleep(1)

            media_id = media_id_from_url(href)
            last_error = None
            for attempt in range(int(config["max_retries"])):
                try:
                    client.unlike(media_id)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = str(exc)
                    if attempt + 1 < int(config["max_retries"]):
                        time.sleep(int(config["retry_delay"]))
            if last_error:
                set_job(job_id, status="error",
                        error=f"Failed to unlike a post after retries: {last_error}")
                return

            posts.pop(0)
            completed += 1
            percent = round(completed * 100 / total)
            set_job(job_id, status="running", completed=completed, progress=percent,
                    message=f"Unliked {completed} of {total} posts.")

            if random.random() < float(config["break_probability"]) and posts:
                break_seconds = random.uniform(float(config["break_min"]), float(config["break_max"]))
                set_job(job_id, status="break", wait_seconds=round(break_seconds),
                        message="Taking the configured break…")
                for _ in range(max(1, int(break_seconds))):
                    if get_job(job_id).get("cancelled"):
                        set_job(job_id, status="cancelled", message="Run stopped.")
                        return
                    time.sleep(1)

        set_job(job_id, status="complete", progress=100, completed=completed,
                message=f"Finished. {completed} posts were unliked.",
                finished_at=datetime.utcnow().isoformat() + "Z")
    except Exception as exc:
        set_job(job_id, status="error", error=str(exc))


@app.get("/")
def index():
    return send_from_directory("web", "index.html")


@app.get("/api/config")
def config():
    return jsonify(DEFAULT_CONFIG)


@app.post("/api/start")
def start():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    upload = request.files.get("liked_posts")

    if not username or not password:
        return jsonify({"error": "Username and password are required for the run."}), 400
    if not upload:
        return jsonify({"error": "Upload your liked_posts.json export first."}), 400

    try:
        liked_data = json.load(upload.stream)
    except Exception as exc:
        return jsonify({"error": f"Invalid JSON file: {exc}"}), 400

    config = {}
    for key, default in DEFAULT_CONFIG.items():
        raw = request.form.get(key, default)
        try:
            config[key] = float(raw) if isinstance(default, float) else int(raw)
        except (TypeError, ValueError):
            config[key] = default

    job_id = uuid.uuid4().hex
    set_job(job_id, status="queued", progress=0, completed=0, total=0,
            message="Run queued.", created_at=datetime.utcnow().isoformat() + "Z")

    # Credentials exist only inside this worker invocation and are never persisted.
    thread = threading.Thread(
        target=worker,
        args=(job_id, username, password, liked_data, config),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.get("/api/status/<job_id>")
def status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(job)


@app.post("/api/stop/<job_id>")
def stop(job_id):
    if not get_job(job_id):
        return jsonify({"error": "Job not found."}), 404
    set_job(job_id, cancelled=True)
    return jsonify({"ok": True})


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "Mahi Unliker"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
