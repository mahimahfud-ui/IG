from flask import Flask, render_template, request, jsonify
from datetime import datetime, timezone
import json, secrets, threading

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

SESSIONS = {}
JOBS = {}
LOCK = threading.Lock()

def media_id_from_shortcode(code):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    code = code.rstrip("/").split("/")[-1]
    value = 0
    for ch in code:
        value = value * 64 + alphabet.index(ch)
    return value

def parse_ts(raw):
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc)
    except Exception:
        return None

def normalize_item(item, i):
    data = item.get("string_list_data") or []
    first = data[0] if data else {}
    href = str(first.get("href") or "").strip()
    if not href:
        return None
    dt = parse_ts(first.get("timestamp"))
    path = href.lower()
    kind = "reel" if "/reel/" in path else ("post" if "/p/" in path else "other")
    shortcode = href.rstrip("/").split("/")[-1]
    try:
        media_id = media_id_from_shortcode(shortcode)
    except Exception:
        media_id = None
    if media_id is None:
        return None
    raw_ts = first.get("timestamp")
    timestamp = int(raw_ts) if str(raw_ts).isdigit() else None
    return {
        "id": f"{i}-{shortcode}",
        "media_id": media_id,
        "url": href,
        "shortcode": shortcode,
        "kind": kind,
        "timestamp": timestamp,
        "date": dt.strftime("%Y-%m-%d") if dt else "",
        "time": dt.strftime("%H:%M:%S UTC") if dt else "",
        "value": str(first.get("value") or ""),
    }

def parse_likes(payload):
    raw = payload.get("likes_media_likes") if isinstance(payload, dict) else payload
    if raw is None and isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                raw = value
                break
    if not isinstance(raw, list):
        raise ValueError("likes_media_likes was not found in this export.")
    output = []
    for i, value in enumerate(raw):
        if isinstance(value, dict):
            item = normalize_item(value, i)
            if item:
                output.append(item)
    return output

def get_session(token):
    with LOCK:
        return SESSIONS.get(token)

def get_job(token, job_id):
    with LOCK:
        session_jobs = JOBS.get(token, {})
        return session_jobs.get(job_id)

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/session")
def create_session():
    token = secrets.token_urlsafe(32)
    with LOCK:
        SESSIONS[token] = {"likes": []}
        JOBS[token] = {}
    return jsonify(ok=True, token=token)

@app.post("/api/import")
def import_likes():
    token = request.headers.get("X-Mahi-Token", "")
    session = get_session(token)
    if not session:
        return jsonify(ok=False, error="Session expired. Reload the page."), 401

    file = request.files.get("file")
    if not file:
        return jsonify(ok=False, error="Choose liked_posts.json first."), 400

    try:
        likes = parse_likes(json.load(file.stream))
        with LOCK:
            session["likes"] = likes
        return jsonify(
            ok=True,
            total=len(likes),
            reels=sum(x["kind"] == "reel" for x in likes),
            posts=sum(x["kind"] == "post" for x in likes),
        )
    except Exception as exc:
        return jsonify(ok=False, error=f"Invalid Instagram export: {exc}"), 400

@app.get("/api/items")
def items():
    token = request.headers.get("X-Mahi-Token", "")
    session = get_session(token)
    if not session:
        return jsonify(ok=False, error="Session expired. Reload the page."), 401

    kind = request.args.get("kind", "reel")
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    query = request.args.get("q", "").lower().strip()

    with LOCK:
        likes = list(session["likes"])

    filtered = [
        item for item in likes
        if (kind == "all" or item["kind"] == kind)
        and (not start or not item["date"] or item["date"] >= start)
        and (not end or not item["date"] or item["date"] <= end)
        and (not query or query in (item["value"] + " " + item["url"]).lower())
    ]
    return jsonify(ok=True, total=len(filtered), items=filtered)

@app.post("/api/queue")
def queue():
    token = request.headers.get("X-Mahi-Token", "")
    session = get_session(token)
    if not session:
        return jsonify(ok=False, error="Session expired. Reload the page."), 401

    body = request.get_json(silent=True) or {}
    ids = list(dict.fromkeys(body.get("ids") or []))
    limit = max(1, min(100, int(body.get("limit") or len(ids) or 1)))
    min_delay = max(1.0, min(300.0, float(body.get("minDelay") or 2)))
    max_delay = max(min_delay, min(300.0, float(body.get("maxDelay") or 5)))
    ids = ids[:limit]

    with LOCK:
        by_id = {item["id"]: item for item in session["likes"]}
        chosen = [by_id[value] for value in ids if value in by_id]
        if not chosen:
            return jsonify(ok=False, error="No valid items selected."), 400
        job_id = secrets.token_urlsafe(18)
        JOBS[token][job_id] = {
            "id": job_id,
            "running": True,
            "processed": 0,
            "total": len(chosen),
            "success": 0,
            "failed": 0,
            "remaining": len(chosen),
            "message": "Waiting for Mahi Browser Helper…",
            "items": chosen,
            "minDelay": min_delay,
            "maxDelay": max_delay,
            "doneIds": [],
        }

    return jsonify(ok=True, jobId=job_id, total=len(chosen), items=chosen,
                   minDelay=min_delay, maxDelay=max_delay)

@app.get("/api/queue/<job_id>")
def queue_status(job_id):
    token = request.headers.get("X-Mahi-Token", "")
    if not get_session(token):
        return jsonify(ok=False, error="Session expired. Reload the page."), 401
    job = get_job(token, job_id)
    if not job:
        return jsonify(ok=False, error="Job not found."), 404
    with LOCK:
        data = {k: v for k, v in job.items() if k != "items"}
    return jsonify(ok=True, **data)

@app.post("/api/queue/<job_id>/event")
def queue_event(job_id):
    token = request.headers.get("X-Mahi-Token", "")
    if not get_session(token):
        return jsonify(ok=False, error="Session expired."), 401
    body = request.get_json(silent=True) or {}
    item_id = str(body.get("itemId") or "")
    success = bool(body.get("success"))
    message = str(body.get("message") or "")
    with LOCK:
        job = JOBS.get(token, {}).get(job_id)
        if not job or not job["running"]:
            return jsonify(ok=False, error="Job is not running."), 404
        if item_id and item_id not in job["doneIds"]:
            job["doneIds"].append(item_id)
            job["processed"] += 1
            job["success"] += int(success)
            job["failed"] += int(not success)
            job["remaining"] = max(0, job["total"] - job["processed"])
        job["message"] = message or ("Unliked" if success else "Failed")
        if job["processed"] >= job["total"]:
            job["running"] = False
            job["message"] = "Complete"
    return jsonify(ok=True)

@app.post("/api/queue/<job_id>/cancel")
def queue_cancel(job_id):
    token = request.headers.get("X-Mahi-Token", "")
    with LOCK:
        job = JOBS.get(token, {}).get(job_id)
        if not job:
            return jsonify(ok=False, error="Job not found."), 404
        job["running"] = False
        job["message"] = "Cancelled"
    return jsonify(ok=True)

@app.post("/api/logout")
def logout():
    token = request.headers.get("X-Mahi-Token", "")
    with LOCK:
        SESSIONS.pop(token, None)
        JOBS.pop(token, None)
    return jsonify(ok=True)

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5050")), debug=False)
