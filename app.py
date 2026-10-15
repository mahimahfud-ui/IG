import json
import os
import random
import re
import threading
import time
import uuid
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

import requests

from flask import Flask, jsonify, redirect, request, send_from_directory
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
    return send_from_directory(os.path.join(app.root_path, "web"), "index.html")


@app.get("/mahiflix")
def mahiflix_redirect():
    return redirect("/mahiflix/", code=308)


@app.get("/mahiflix/")
def mahiflix_index():
    return send_from_directory(os.path.join(app.root_path, "web", "mahiflix"), "index.html")


@app.get("/linkora")
def linkora_redirect():
    return redirect("/linkora/", code=308)


@app.get("/linkora/")
def linkora_index():
    return send_from_directory(os.path.join(app.root_path, "web", "linkora"), "index.html")


@app.get("/apps")
def apps_redirect():
    return redirect("/apps/", code=308)


@app.get("/apps/")
def apps_index():
    return send_from_directory(os.path.join(app.root_path, "web", "apps"), "index.html")


# Friendly MahiCloud route aliases. Canonical project routes remain unchanged.
@app.get("/windows-tools")
def windows_tools_redirect():
    return redirect("/linkora/", code=308)


@app.get("/windows-tools/")
def windows_tools_index():
    return redirect("/linkora/", code=308)


@app.get("/gallery")
def gallery_redirect():
    return redirect("/lumr/", code=308)


@app.get("/gallery/")
def gallery_index():
    return redirect("/lumr/", code=308)


@app.get("/social-tools")
def social_tools_redirect():
    return redirect("/instagram-cleaner.html", code=308)


@app.get("/social-tools/")
def social_tools_index():
    # Redirect to the existing root URL so relative assets and browser paths behave exactly as before.
    return redirect("/instagram-cleaner.html", code=308)


@app.get("/social-tools/instagram-cleaner")
def social_tools_cleaner_redirect():
    return redirect("/instagram-cleaner.html", code=308)


@app.get("/unfollowers")
def unfollowers_redirect():
    return redirect("/unfollowers/", code=308)


@app.get("/unfollowers/")
def unfollowers_index():
    return send_from_directory(os.path.join(app.root_path, "web", "unfollowers"), "index.html")


@app.get("/lumr")
def lumr_redirect():
    return redirect("/lumr/", code=308)


@app.get("/lumr/")
def lumr_index():
    return send_from_directory(os.path.join(app.root_path, "web", "lumr"), "index.html")


@app.get("/@<username>")
def lumr_public_profile(username):
    """Serve LUMR for the original public profile route /@username."""
    return send_from_directory(os.path.join(app.root_path, "web", "lumr"), "index.html")


@app.get("/api/config")
@app.get("/lumr/api/config")
def lumr_config():
    return jsonify({
        "supabaseUrl": os.environ.get("SUPABASE_URL", ""),
        "publishableKey": os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", ""),
        "youtubeUrl": os.environ.get("YOUTUBE_URL", ""),
    })



# Direct APK resolver ported from the original MahiFlix download workflow.
# Resolved URLs must be HTTPS, APK/XAPK files, and served by an explicitly allow-listed host.
APP_DOWNLOADS = {
    "7reel": {"page":"https://7reels.cc/download","fallback":None,"allowed_hosts":["7reels.cc"],"patterns":[r"https?://[^\"']+\.apk(?:\?[^\"']*)?"]},
    "filmtv": {"page":"https://www.filmtvapp.com/","fallback":None,"allowed_hosts":["www.filmtvapp.com","filmtvapp.com"],"patterns":[r"https?://[^\"'\s<>]+\.apk(?:\?[^\"'\s<>]*)?"]},
    "nuvix": {"page":"https://www.nuvixapp.in/","fallback":None,"allowed_hosts":["www.nuvixapp.in","nuvixapp.in"],"patterns":[r"https?://[^\"'\s<>]+\.apk(?:\?[^\"'\s<>]*)?"]},
    "vega": {"page":"https://api.github.com/repos/vega-org/vega-app/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r"\.apk$"},
    "netmirror": {"page":"https://netmirror.gg/10/en-us","fallback":"https://netmirror.gg/NetMirror.apk","allowed_hosts":["netmirror.gg"],"patterns":[r"https?://[^\"'\s<>]+\.apk[^\"'\s<>]*"]},
    "cinehd": {"page":"https://cinehd.dev/","fallback":None,"allowed_hosts":["cinehd.dev"],"patterns":[r"https?://[^\"'\s<>]*CineHD[^\"'\s<>]*Universal[^\"'\s<>]*\.apk[^\"'\s<>]*"]},
    "moviboxapk": {"page":"https://moviboxapk.com/","fallback":None,"allowed_hosts":["moviboxapk.com","file.dxmaxapk.com"],"patterns":[r"https?://[^\"'\s<>]+moviebox[^\"'\s<>]*\.apk[^\"'\s<>]*"]},
    "pvrplay": {"page":"https://pvrplay.online/","fallback":"https://stream.phoasy.com/app/PvrPlay.apk","allowed_hosts":["pvrplay.online","stream.phoasy.com"],"patterns":[r"https?://[^\"'\s<>]*PvrPlay[^\"'\s<>]*\.apk[^\"'\s<>]*"]},
    "hdghartv": {"page":"https://hdghartv.com.pk/apk/","fallback":None,"allowed_hosts":["watch.hdghartv.com.pk","hdghartv.com.pk","download.hdghartv.com.pk"],"patterns":[r"https?://[^\"'\s<>]+HDGharTV[^\"'\s<>]*\.apk[^\"'\s<>]*"]},
    "anivortex": {"page":"https://anivortex.in/","fallback":None,"allowed_hosts":["anivortex.in"],"patterns":[r"https?://[^\"'\s<>]*/apk/[^\"'\s<>]+\.apk[^\"'\s<>]*"]},
    "nxsha": {"page":"https://api.github.com/repos/dev-alessiorizzo/nxsha-apk/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r".*\.Universal\.apk$"},
    "dooflix": {"page":"https://dooflixapk.com/","fallback":None,"allowed_hosts":["dooflixapk.com","www.dooflixapk.com"],"patterns":[]},
    "bitchord": {"page":"https://api.github.com/repos/kushagrasinghx/BitChord/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r"BitChord-v[^_]*\.apk$"},
    "echo-music": {"page":"https://api.github.com/repos/EchoMusicApp/Echo-Music/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r"EchoMusic\.apk$"},
    "echo-nightly": {"page":"https://api.github.com/repos/itsmechinmoy/echo-nightly/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r"app-release\.apk$"},
    "spotube": {"page":"https://api.github.com/repos/team-spotube/spotube/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r"Spotube-android-all-arch\.apk$"},
    "outertune": {"page":"https://api.github.com/repos/OuterTune/OuterTune/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r".*full-release-.*\.apk$"},
    "lastwave": {"page":"https://api.github.com/repos/Clash-Projects/LastWave-Native/releases/latest","allowed_hosts":["github.com","objects.githubusercontent.com","release-assets.githubusercontent.com"],"github_latest":True,"asset_pattern":r".*-universal\.apk$"},
}
_APP_DOWNLOAD_CACHE = {}
_APP_DOWNLOAD_CACHE_TTL = 300
_APP_DOWNLOAD_NEGATIVE_TTL = 15
_APP_DOWNLOAD_TIMEOUT = 12
_APP_DOWNLOAD_HEADERS = {"User-Agent":"MahiCloud-App-Download-Resolver/1.0","Accept":"text/html,application/xhtml+xml,application/json"}


def _normalise_download_url(raw_url, base_url=None):
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    value = raw_url.replace("&amp;", "&").replace("\\", "").strip().rstrip(".,;")
    if base_url:
        value = urljoin(base_url, value)
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    return parsed


def _allowed_apk_url(raw_url, config, base_url=None):
    parsed = _normalise_download_url(raw_url, base_url)
    if not parsed or parsed.hostname.lower() not in config["allowed_hosts"]:
        return None
    if not parsed.path.lower().endswith((".apk", ".xapk")):
        return None
    return parsed.geturl()


def _fetch_download_page(config):
    current = config["page"]
    for _ in range(6):
        parsed = urlparse(current)
        if parsed.scheme.lower() != "https" or parsed.hostname not in config["allowed_hosts"]:
            return None, None
        try:
            response = requests.get(current, headers=_APP_DOWNLOAD_HEADERS, timeout=_APP_DOWNLOAD_TIMEOUT, allow_redirects=False)
        except requests.RequestException:
            return None, None
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location")
            if not location:
                return None, None
            next_url = urljoin(current, location)
            next_parsed = urlparse(next_url)
            if next_parsed.scheme.lower() != "https" or next_parsed.hostname not in config["allowed_hosts"]:
                return None, None
            current = next_url
            continue
        if response.status_code < 200 or response.status_code >= 300:
            return None, None
        return response.text, current
    return None, None


def _resolve_app_download_uncached(slug, config):
    if config.get("github_latest"):
        try:
            response = requests.get(config["page"], headers={"User-Agent":_APP_DOWNLOAD_HEADERS["User-Agent"],"Accept":"application/vnd.github+json"}, timeout=_APP_DOWNLOAD_TIMEOUT, allow_redirects=False)
            if 200 <= response.status_code < 300:
                payload = response.json()
                matcher = re.compile(config["asset_pattern"], re.IGNORECASE)
                assets = payload.get("assets", []) if isinstance(payload, dict) else []
                for asset in assets:
                    if not isinstance(asset, dict):
                        continue
                    name = str(asset.get("name") or "")
                    target = asset.get("browser_download_url")
                    if target and matcher.search(name):
                        safe_target = _allowed_apk_url(target, config)
                        if safe_target:
                            return safe_target
        except (requests.RequestException, ValueError, TypeError):
            pass
        return None

    html, final_url = _fetch_download_page(config)
    if html is not None and final_url:
        candidates = []
        for pattern in config.get("patterns", []):
            candidates.extend(re.findall(pattern, html, re.IGNORECASE))
        candidates.extend(re.findall(r"""(?:href|src|data-href|data-url)\s*=\s*["']([^"']+\.(?:apk|xapk)(?:\?[^"']*)?)["']""", html, re.IGNORECASE))
        candidates.extend(re.findall(r"""["']((?:https?://|/)[^"'\s<>]+?\.(?:apk|xapk)(?:\?[^"'\s<>]*)?)["']""", html, re.IGNORECASE))
        safe_candidates = []
        for candidate in candidates:
            safe_target = _allowed_apk_url(candidate, config, final_url)
            if safe_target and safe_target not in safe_candidates:
                safe_candidates.append(safe_target)
        if safe_candidates:
            safe_candidates.sort(key=lambda url: 0 if "universal" in url.lower() else 1)
            return safe_candidates[0]
    fallback = config.get("fallback")
    return _allowed_apk_url(fallback, config) if fallback else None


def resolve_app_download(slug):
    config = APP_DOWNLOADS.get(slug)
    if not config:
        return None
    now = time.monotonic()
    cached = _APP_DOWNLOAD_CACHE.get(slug)
    if cached:
        value, checked_at = cached
        max_age = _APP_DOWNLOAD_CACHE_TTL if value else _APP_DOWNLOAD_NEGATIVE_TTL
        if now - checked_at < max_age:
            return value
    target = _resolve_app_download_uncached(slug, config)
    _APP_DOWNLOAD_CACHE[slug] = (target, now)
    return target


@app.get("/download/app/<slug>")
def download_app_redirect(slug):
    app_id = str(slug or "").strip().lower()
    if app_id not in APP_DOWNLOADS:
        return ("App not found.", 404, {"Content-Type":"text/plain; charset=utf-8","Cache-Control":"no-store"})
    target = resolve_app_download(app_id)
    if target:
        return redirect(target, code=302)
    message = "A verified direct download is not available from the app source right now. Please try again later."
    return (message, 502, {"Content-Type":"text/plain; charset=utf-8","Cache-Control":"no-store"})


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
    return send_from_directory(os.path.join(app.root_path, "web"), "privacy.html")


@app.get("/terms")
def terms():
    return send_from_directory(os.path.join(app.root_path, "web"), "terms.html")


@app.errorhandler(404)
def page_not_found(_error):
    # Preserve JSON error responses for API consumers.
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found."}), 404
    return send_from_directory(os.path.join(app.root_path, "web"), "404.html"), 404


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # Render terminates TLS at its edge; only advertise HSTS on HTTPS requests.
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    if request.is_secure or forwarded_proto == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


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
