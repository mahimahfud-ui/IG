import json
import os
import random
import threading
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__, static_folder="web", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MiB upload limit.

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

CONFIG_LIMITS = {
    "delay_min": (0, 3600),
    "delay_max": (0, 3600),
    "break_probability": (0, 0.50),
    "break_min": (0, 21600),
    "break_max": (0, 21600),
    "max_retries": (1, 10),
    "retry_delay": (0, 900),
}

TERMINAL_STATUSES = {"complete", "error", "cancelled"}
JOB_TTL_SECONDS = 6 * 60 * 60
MAX_LIKED_POSTS = 50_000


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def media_id_from_url(url: str) -> int:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Missing media URL.")

    charmap = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    code = url.rstrip("/").split("/")[-1]
    if not code:
        raise ValueError("Invalid media URL.")

    try:
        return sum(charmap.index(ch) * (64 ** i) for i, ch in enumerate(reversed(code)))
    except ValueError as exc:
        raise ValueError("Media URL contains unsupported characters.") from exc


def cleanup_old_jobs():
    now = time.time()
    with jobs_lock:
        stale_ids = [
            job_id
            for job_id, job in jobs.items()
            if job.get("status") in TERMINAL_STATUSES
            and now - float(job.get("_created_epoch", now)) > JOB_TTL_SECONDS
        ]
        for job_id in stale_ids:
            jobs.pop(job_id, None)


def set_job(job_id, **values):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(values)


def get_job(job_id):
    with jobs_lock:
        snapshot = dict(jobs.get(job_id, {}))
    return {key: value for key, value in snapshot.items() if not key.startswith("_")}


def wait_with_cancel(job_id, seconds):
    end = time.monotonic() + max(0.0, float(seconds))
    while True:
        if get_job(job_id).get("cancelled"):
            set_job(job_id, status="cancelled", message="Run stopped.")
            return True

        remaining = end - time.monotonic()
        if remaining <= 0:
            return False

        time.sleep(min(1.0, remaining))


def worker(job_id, username, password, liked_data, config):
    try:
        from ensta import Web
    except Exception:
        set_job(
            job_id,
            status="error",
            error="The Instagram client could not be loaded on the server.",
        )
        return

    try:
        set_job(
            job_id,
            status="connecting",
            message="Connecting to Instagram…",
        )
        client = Web(username, password)
        account = client.private_info()
        display_name = getattr(account, "username", username)

        posts = liked_data.get("likes_media_likes", [])
        if not isinstance(posts, list):
            set_job(
                job_id,
                status="error",
                error="The uploaded JSON has an invalid liked-posts structure.",
            )
            return

        if len(posts) > MAX_LIKED_POSTS:
            set_job(
                job_id,
                status="error",
                error=f"The uploaded file contains more than {MAX_LIKED_POSTS:,} liked posts.",
            )
            return

        posts = list(posts)
        total = len(posts)
        if not total:
            set_job(
                job_id,
                status="complete",
                progress=100,
                total=0,
                completed=0,
                message="No liked posts were found in the uploaded JSON.",
                finished_at=utc_now_iso(),
            )
            return

        set_job(
            job_id,
            status="running",
            total=total,
            completed=0,
            progress=0,
            account=display_name,
            message=f"Found {total} liked posts.",
        )

        completed = 0
        while posts:
            if get_job(job_id).get("cancelled"):
                set_job(job_id, status="cancelled", message="Run stopped.")
                return

            current = posts.pop(0)
            if not isinstance(current, dict):
                continue

            data = current.get("string_list_data")
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                continue

            href = data[0].get("href")
            try:
                media_id = media_id_from_url(href)
            except ValueError:
                continue

            delay = random.uniform(
                float(config["delay_min"]),
                float(config["delay_max"]),
            )
            set_job(
                job_id,
                status="waiting",
                wait_seconds=round(delay),
                message="Respecting your configured delay…",
            )
            if wait_with_cancel(job_id, delay):
                return

            last_error = None
            for attempt in range(int(config["max_retries"])):
                if get_job(job_id).get("cancelled"):
                    set_job(job_id, status="cancelled", message="Run stopped.")
                    return

                try:
                    client.unlike(media_id)
                    last_error = None
                    break
                except Exception:
                    last_error = True
                    if attempt + 1 < int(config["max_retries"]):
                        set_job(
                            job_id,
                            status="retrying",
                            message=f"Request failed. Retrying ({attempt + 1}/{config['max_retries'] - 1})…",
                        )
                        if wait_with_cancel(job_id, config["retry_delay"]):
                            return

            if last_error:
                set_job(
                    job_id,
                    status="error",
                    error="Instagram rejected a cleanup request after the configured retries.",
                )
                return

            completed += 1
            percent = round(completed * 100 / total)
            set_job(
                job_id,
                status="running",
                completed=completed,
                progress=percent,
                message=f"Unliked {completed} of {total} posts.",
            )

            if random.random() < float(config["break_probability"]) and posts:
                break_seconds = random.uniform(
                    float(config["break_min"]),
                    float(config["break_max"]),
                )
                set_job(
                    job_id,
                    status="break",
                    wait_seconds=round(break_seconds),
                    message="Taking the configured break…",
                )
                if wait_with_cancel(job_id, break_seconds):
                    return

        set_job(
            job_id,
            status="complete",
            progress=100,
            completed=completed,
            message=f"Finished. {completed} posts were unliked.",
            finished_at=utc_now_iso(),
        )
    except Exception:
        set_job(
            job_id,
            status="error",
            error="Unexpected server error. The run was stopped.",
        )


@app.get("/")
def index():
    return send_from_directory("web", "index.html")


@app.get("/api/config")
def config():
    return jsonify(DEFAULT_CONFIG)


@app.post("/api/start")
def start():
    cleanup_old_jobs()

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    upload = request.files.get("liked_posts")

    if not username or not password:
        return jsonify({"error": "Username and password are required for the run."}), 400

    if len(username) > 75:
        return jsonify({"error": "Username is too long."}), 400

    if len(password) > 512:
        return jsonify({"error": "Password is too long."}), 400

    if not upload:
        return jsonify({"error": "Upload your liked_posts.json export first."}), 400

    if upload.filename and not upload.filename.lower().endswith(".json"):
        return jsonify({"error": "The uploaded file must be a JSON file."}), 400

    try:
        liked_data = json.load(upload.stream)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return jsonify({"error": "The uploaded file is not valid UTF-8 JSON."}), 400
    except Exception:
        return jsonify({"error": "The uploaded JSON could not be read."}), 400

    if not isinstance(liked_data, dict):
        return jsonify({"error": "The uploaded JSON must contain an object at the top level."}), 400

    config_values = {}
    for key, default in DEFAULT_CONFIG.items():
        raw = request.form.get(key, default)
        try:
            value = float(raw) if isinstance(default, float) else int(raw)
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid value for {key}."}), 400

        low, high = CONFIG_LIMITS[key]
        if value < low or value > high:
            return jsonify({"error": f"{key} must be between {low} and {high}."}), 400
        config_values[key] = value

    if config_values["delay_min"] > config_values["delay_max"]:
        return jsonify({"error": "Minimum delay cannot be greater than maximum delay."}), 400

    if config_values["break_min"] > config_values["break_max"]:
        return jsonify({"error": "Minimum break cannot be greater than maximum break."}), 400

    job_id = uuid.uuid4().hex
    set_job(
        job_id,
        status="queued",
        progress=0,
        completed=0,
        total=0,
        message="Run queued.",
        created_at=utc_now_iso(),
        _created_epoch=time.time(),
    )

    thread = threading.Thread(
        target=worker,
        args=(job_id, username, password, liked_data, config_values),
        daemon=True,
        name=f"like-cleanup-{job_id[:8]}",
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
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404

    if job.get("status") in TERMINAL_STATUSES:
        return jsonify({"ok": True, "already_finished": True})

    set_job(job_id, cancelled=True, message="Stopping run…")
    return jsonify({"ok": True})


@app.get("/privacy")
def privacy():
    return send_from_directory("web", "privacy.html")


@app.get("/health")
def health():
    cleanup_old_jobs()
    with jobs_lock:
        active = sum(1 for job in jobs.values() if job.get("status") not in TERMINAL_STATUSES)
    return jsonify({"ok": True, "service": "Mahi Social Cleaner", "active_jobs": active})


@app.errorhandler(RequestEntityTooLarge)
def handle_upload_too_large(_error):
    return jsonify({"error": "Upload is too large. Maximum file size is 10 MiB."}), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
