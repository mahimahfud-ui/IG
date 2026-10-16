"""Public, rate-limited MahiCloud quick-add endpoint (no OpenAI API calls)."""
from __future__ import annotations
import ast, base64, hashlib, hmac, html, os, re, threading, time
from urllib.parse import urlsplit, urlunsplit
from flask import Blueprint, jsonify, request
from mahi_ai import MahiAIError, _check_bat_safety, _fetch_public, _github, _github_token, _insert_js_array_item, _metadata_for_url, _normalise_public_url, _repo_file, _repo_name, _slug

mahi_catalog_bp = Blueprint("mahi_catalog", __name__)
_lock = threading.Lock()
_events: dict[str, list[float]] = {}
_global: list[float] = []


def _limited():
    now, key = time.monotonic(), request.remote_addr or "unknown"
    with _lock:
        recent = _events.setdefault(key, [])
        recent[:] = [t for t in recent if now-t < 600]
        _global[:] = [t for t in _global if now-t < 3600]
        if len(recent) >= 8:
            return max(1, int(600-(now-recent[0])))
        if len(_global) >= 40:
            return max(1, int(3600-(now-_global[0])))
        recent.append(now); _global.append(now)
        return 0


_verify_lock = threading.Lock()
_verify_events: dict[str, list[float]] = {}
_verify_global: list[float] = []


def _limited_verify_pin():
    now, key = time.monotonic(), request.remote_addr or "unknown"
    with _verify_lock:
        recent = _verify_events.setdefault(key, [])
        recent[:] = [t for t in recent if now-t < 600]
        _verify_global[:] = [t for t in _verify_global if now-t < 3600]
        if len(recent) >= 5:
            return max(1, int(600-(now-recent[0])))
        if len(_verify_global) >= 100:
            return max(1, int(3600-(now-_verify_global[0])))
        recent.append(now)
        _verify_global.append(now)
        return 0


def _url(value):
    m = re.search(r'https?://[^\s<>"\']+', value, re.I)
    if m:
        return m.group(0).rstrip(".,;)")
    if re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?", value.strip()):
        return value.strip()
    return None


def _name(meta):
    value = html.unescape(str(meta.get("site_name") or meta.get("title") or "")).strip()
    value = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", value))
    value = re.split(r"\s+(?:[-|:–—])\s+", value, maxsplit=1)[0].strip(" -|:–—")
    if not value:
        value = str(meta.get("domain") or "New Site").split(".")[0].replace("-", " ").title()
    return value[:80] or "New Site"


def _logo_ext(kind, body):
    kind = (kind or "").split(";", 1)[0].lower()
    if body.startswith(b"\x89PNG\r\n\x1a\n"): return ".png"
    if body.startswith(b"\xff\xd8\xff"): return ".jpg"
    if body.startswith((b"GIF87a", b"GIF89a")): return ".gif"
    if len(body)>12 and body[:4]==b"RIFF" and body[8:12]==b"WEBP": return ".webp"
    if body.startswith(b"\x00\x00\x01\x00"): return ".ico"
    if kind=="image/svg+xml" or re.match(rb"(?is)^\s*(?:<\?xml[^>]*>\s*)?<svg[\s>]", body[:400]):
        lower=body.lower()
        if any(x in lower for x in (b"<script",b"<foreignobject",b"javascript:",b"onload=",b"onerror=",b"@import",b"url(")):
            return None
        if re.search(rb"""(?:href|xlink:href)\s*=\s*["']https?://""",lower): return None
        return ".svg"
    return None


def _download_logo(meta, url):
    for source in (meta.get("logo_sources") or [])[:10]:
        try:
            final, kind, body = _fetch_public(str(source), max_bytes=300000)
            ext = _logo_ext(kind, body)
            if ext:
                key = hashlib.sha256((url+"|"+final).encode()).hexdigest()[:10]
                return "web/assets/submitted-logos/"+_slug(meta.get("domain","site"))+"-"+key+ext, body
        except (MahiAIError, ValueError):
            pass
    raise MahiAIError("Couldn't safely download a logo from that page. Nothing was published; try its official homepage.")


def _commit(changes, expected):
    if not _github_token():
        raise MahiAIError("GitHub publishing needs MAHI_AI_GITHUB_TOKEN on the Flask hosting service.", 503)
    repo=_repo_name()
    ref=_github("GET",f"/repos/{repo}/git/ref/heads/main")
    head=(ref.get("object") or {}).get("sha")
    if not head: raise MahiAIError("Could not read the current main branch.",502)
    parent=_github("GET",f"/repos/{repo}/git/commits/{head}")
    base=(parent.get("tree") or {}).get("sha")
    if not base: raise MahiAIError("Could not read the current Git tree.",502)
    for path,wanted in expected.items():
        try: actual=_repo_file(path,ref=head).get("sha")
        except MahiAIError as e:
            if e.status!=404: raise
            actual=None
        if actual!=wanted: raise MahiAIError("The catalog changed during this submission. Please retry.",409)
    items=[]
    for path,data in changes.items():
        if isinstance(data,bytes):
            body={"content":base64.b64encode(data).decode("ascii"),"encoding":"base64"}
        else:
            body={"content":data,"encoding":"utf-8"}
        blob=_github("POST",f"/repos/{repo}/git/blobs",payload=body)
        items.append({"path":path,"mode":"100644","type":"blob","sha":blob["sha"]})
    tree=_github("POST",f"/repos/{repo}/git/trees",payload={"base_tree":base,"tree":items})
    commit=_github("POST",f"/repos/{repo}/git/commits",payload={"message":"Add MahiCloud catalog entry","tree":tree["sha"],"parents":[head]})
    sha=commit.get("sha")
    if not sha: raise MahiAIError("GitHub did not return a commit SHA.",502)
    _github("PATCH",f"/repos/{repo}/git/refs/heads/main",payload={"sha":sha,"force":False})
    return "https://github.com/"+repo+"/commit/"+sha


def _catalog_display_name(value) -> str:
    if not isinstance(value, str):
        raise MahiAIError("Enter the display name for this item.", 400)
    name = re.sub(r"\s+", " ", value).strip()
    if not name:
        raise MahiAIError("Enter the display name for this item.", 400)
    if len(name) > 80:
        raise MahiAIError("Display names are limited to 80 characters.", 400)
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise MahiAIError("The display name contains unsupported control characters.", 400)
    return name


_LINK_CATEGORIES = {
    "app": ("other_app", "otherApps", "web/apps/index.html", "Apps", ["Apps", "Tools"]),
    "movie_website": ("movie_website", "S", "web/mahiflix/index.html", "Movie Websites", ["Movies", "Streaming"]),
    "movie_app": ("movie_app", "movieApps", "web/apps/index.html", "Movie Apps", ["Movie", "Android/iOS"]),
    "music_app": ("music_app", "musicApps", "web/apps/index.html", "Music Apps", ["Music", "Audio"]),
}


def _fallback_logo(name: str, category: str, url: str):
    palettes = {
        "movie_website": ("#ff7779", "#961b35"),
        "movie_app": ("#b8a2ff", "#4b36a8"),
        "music_app": ("#73e6ef", "#3259a7"),
    }
    c1, c2 = palettes.get(category, ("#f15d6a", "#4b3a91"))
    initials = "".join(word[0] for word in re.findall(r"[A-Za-z0-9]+", name)[:2]).upper() or "M"
    key = hashlib.sha256((url + "|" + name + "|" + category).encode("utf-8")).hexdigest()[:12]
    path = "web/assets/submitted-logos/" + _slug(name) + "-" + key + ".svg"
    mark = html.escape(initials)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop stop-color="' + c1 + '"/><stop offset="1" stop-color="' + c2 + '"/>'
        '</linearGradient><linearGradient id="shine" x1="0" y1="0" x2="0" y2="1">'
        '<stop stop-color="#fff" stop-opacity=".32"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        '</linearGradient></defs><rect width="128" height="128" rx="30" fill="url(#g)"/>'
        '<circle cx="104" cy="22" r="32" fill="#fff" fill-opacity=".08"/>'
        '<rect x="8" y="8" width="112" height="112" rx="25" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="2"/>'
        '<rect x="15" y="15" width="98" height="98" rx="22" fill="#fff" fill-opacity=".07" stroke="#fff" stroke-opacity=".16"/>'
        '<rect width="128" height="128" rx="30" fill="url(#shine)"/>'
        '<text x="64" y="77" text-anchor="middle" fill="#fff" font-family="Arial,sans-serif" font-weight="800" font-size="40" letter-spacing="-2">' + mark + '</text>'
        '</svg>'
    )
    return path, svg.encode("utf-8")



_APP_DOWNLOAD_SUFFIXES = {".apk", ".aab", ".ipa", ".exe", ".msi", ".dmg", ".appx", ".msix", ".zip"}
_APP_LINK_CATEGORIES = {"app", "movie_app", "music_app"}


def _is_direct_app_download_url(url: str) -> bool:
    """Return True for explicitly supported, public app-installer/archive URL suffixes."""
    try:
        path = urlsplit(_normalise_public_url(url)).path.lower()
    except (MahiAIError, ValueError):
        return False
    return any(path.endswith(suffix) for suffix in _APP_DOWNLOAD_SUFFIXES)


def _app_metadata_page_url(url: str) -> str:
    """Resolve the publisher page to scrape when the submitted URL is a binary download."""
    normalised = _normalise_public_url(url)
    parts = urlsplit(normalised)
    segments = [part for part in parts.path.split("/") if part]
    host = (parts.hostname or "").lower()
    # A GitHub release asset belongs to its repository page, which provides a much
    # better title/logo than github.com's generic homepage.
    if host in {"github.com", "www.github.com"} and len(segments) >= 2:
        return urlunsplit((parts.scheme, parts.netloc, "/" + "/".join(segments[:2]), "", ""))
    # For other hosts, start from the public origin homepage.
    return urlunsplit((parts.scheme, parts.netloc, "/", "", ""))


def _add_link(raw, url, category_override=None, custom_name=None):
    if category_override and category_override not in _LINK_CATEGORIES:
        raise MahiAIError("Choose Apps, Movie Websites, Movie Apps, or Music Apps for a website or app download URL.", 400)
    direct_download = category_override in _APP_LINK_CATEGORIES and _is_direct_app_download_url(url)
    if direct_download:
        download_url = _normalise_public_url(url)
        # Fetch only a bounded prefix of the actual asset: confirms the public URL
        # resolves while avoiding downloading or executing the installer on the server.
        _fetch_public(download_url, max_bytes=1024, allow_truncate=True)
        metadata_page = _app_metadata_page_url(download_url)
        try:
            meta = dict(_metadata_for_url(metadata_page))
        except MahiAIError:
            # A direct file host may not expose an HTML homepage. The item remains
            # addable with a generated fallback mark when no publisher logo is available.
            meta = {
                "url": metadata_page,
                "domain": urlsplit(download_url).hostname or "",
                "title": "",
                "description": "",
                "content_hint": "",
                "logo_sources": [],
            }
        meta["url"] = download_url
        meta["domain"] = urlsplit(download_url).hostname or meta.get("domain", "")
    else:
        meta = _metadata_for_url(url)
    domain = str(meta.get("domain") or urlsplit(meta["url"]).hostname or "")
    source = " ".join([domain, str(meta.get("title") or ""), str(meta.get("description") or ""),
                       str(meta.get("content_hint") or ""), raw]).lower()

    if category_override:
        if category_override not in _LINK_CATEGORIES:
            raise MahiAIError("Choose Movie Websites, Movie Apps, or Music Apps for a website URL.", 400)
        cat, arr, path, label, tags = _LINK_CATEGORIES[category_override]
    else:
        music = any(x in source for x in ("music", "spotify", "soundcloud", "apple music", "youtube music",
                                           "deezer", "tidal", "bandcamp", "lyrics", "shazam", "song", "audio player"))
        movie = any(x in source for x in ("movie", "film", "cinema", "anime", "web series", "tv show",
                                           "tv series", "streaming", "watch online", "drama", "netflix",
                                           "prime video", "disney+", "crunchyroll", "plex", "hulu", "peacock",
                                           "hbo", "flix", "yts"))
        if music:
            cat, arr, path, label, tags = "music_app", "musicApps", "web/apps/index.html", "Music Apps", ["Music", "Audio"]
        elif movie:
            is_app = bool(re.search(r"\b(app|apk|android|ios|mobile|play store|app store)\b",
                                    raw.lower() + " " + str(meta.get("title", "")).lower() + " " + str(meta.get("description", "")).lower()))
            if re.search(r"\b(movie )?website\b", raw.lower()):
                is_app = False
            if is_app:
                cat, arr, path, label, tags = "movie_app", "movieApps", "web/apps/index.html", "Movie Apps", ["Movie", "Android/iOS"]
            else:
                cat, arr, path, label, tags = "movie_website", "S", "web/mahiflix/index.html", "Movie Websites", ["Movies", "Streaming"]
        else:
            raise MahiAIError("This link doesn't clearly fit Movie Websites, Movie Apps, or Music Apps. Send an official page from one of those categories.")

    name = _catalog_display_name(custom_name) if custom_name is not None else _name(meta)
    default_desc = name + (" direct app download." if direct_download else " official website.")
    desc = re.sub(r"\s+", " ", str(meta.get("description") or default_desc)).strip()[:240]
    try:
        logo_path, logo = _download_logo(meta, str(meta["url"]))
    except MahiAIError:
        # Keep URLs addable when a host does not expose a usable public logo.
        logo_path, logo = _fallback_logo(name, cat, str(meta["url"]))
    local_logo = "/" + logo_path.removeprefix("web/")
    record = {"name": name, "url": meta["url"], "domain": domain, "ads": 1, "pop": 70, "smooth": 70,
              "langs": 70, "new": True, "desc": desc, "logoSources": [local_logo]}
    if cat == "movie_app":
        record.update({"externalWebsite": not direct_download,
                       "linkLabel": "Download app" if direct_download else "Visit website",
                       "sublabel": "Direct app download · Verify before installing" if direct_download else "Official website · Verify downloads before installing", "tags": tags})
    elif cat == "music_app":
        record.update({"kind": "app", "linkLabel": "Download app" if direct_download else "Visit website",
                       "sublabel": "Direct app download · Verify before installing" if direct_download else "Official website", "tags": tags})
    elif cat == "other_app":
        record.update({"kind": "app", "linkLabel": "Download app" if direct_download else "Visit website",
                       "sublabel": "Direct app download · Verify before installing" if direct_download else "Official website", "tags": tags})
    page = _repo_file(path, ref="main")
    content = _insert_js_array_item(page["content"], arr, record)
    commit_url = _commit({path: content, logo_path: logo}, {path: page["sha"], logo_path: None})
    return {"ok": True, "name": name, "category_label": label,
            "message": f"Added {name} to {label}; its logo is ready in the collection.", "commit_url": commit_url}


def _check_python_source(script: str) -> None:
    if not script.strip() or len(script) > 60000:
        raise MahiAIError("The Python source must be non-empty and no larger than 60 KB.", 400)
    if "\x00" in script:
        raise MahiAIError("The Python source must be plain text, not binary data.", 400)
    try:
        ast.parse(script, filename="submitted_windows_tool.py")
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None)
        suffix = f" (line {line})" if line else ""
        raise MahiAIError("The Python source has a syntax error" + suffix + ". Fix it before publishing.", 400)
    unsafe_patterns = [
        (r"(?im)\bformat\s+[a-z]:", "drive formatting"),
        (r"(?im)\bdiskpart\b", "raw disk partition commands"),
        (r"(?im)\bbcdedit\b", "boot configuration changes"),
        (r"(?im)\breg(?:\.exe)?\s+delete\b", "registry deletion"),
        (r"(?im)\bvssadmin\b[^\r\n]*delete\s+shadows", "backup/shadow-copy deletion"),
        (r"(?is)\bshutil\.rmtree\s*\(\s*['\"](?:[a-z]:\\|/)", "recursive deletion of an entire drive or root"),
        (r"(?im)\b(?:powershell|pwsh)\b[^\r\n]*(?:-enc(?:odedcommand)?\s+[a-z0-9+/=]{24,})", "encoded PowerShell commands"),
    ]
    for pattern, label in unsafe_patterns:
        if re.search(pattern, script):
            raise MahiAIError("I blocked this Python file because it includes a high-risk operation: " + label + ". Nothing was uploaded.", 422)


def _add_custom_script(source: str, title: str, category: str) -> dict:
    if category == "windows_bat":
        _check_bat_safety(source)
        extension = ".bat"
        language = "BAT"
    elif category == "windows_python":
        _check_python_source(source)
        extension = ".py"
        language = "Python"
    else:
        raise MahiAIError("Choose a Windows BAT or Python automation category.", 400)

    filename = _slug(title) + extension
    script_path = "web/linkora/downloads/" + filename
    page_path = "web/linkora/index.html"
    page = _repo_file(page_path, ref="main")
    existing = page["content"]
    if re.search(r"""(?i)["']file["']\s*:\s*["']""" + re.escape(filename) + r"""["']""", existing):
        raise MahiAIError("A Windows tool with that filename already exists. Choose a different name.", 409)
    if re.search(r"""(?i)["']title["']\s*:\s*["']""" + re.escape(title) + r"""["']""", existing):
        raise MahiAIError("A Windows tool with that name already exists. Choose a different name.", 409)

    script = source.replace("\r\n", "\n").replace("\r", "\n")
    if language == "BAT":
        script = script.replace("\n", "\r\n")
    record = {
        "title": title,
        "category": "productivity",
        "description": f"Custom {language} Windows automation script. Review the source and all commands before running.",
        "file": filename,
        "path": "/linkora/downloads/" + filename,
        "tags": ["Windows", language, "Automation", "Review before running"],
        "bangla": "চালানোর আগে স্ক্রিপ্টের সব কমান্ড পড়ে নাও। এটি server-এ চালানো হয় না।"
    }
    updated = _insert_js_array_item(existing, "SCRIPTS", record)
    commit_url = _commit({script_path: script.encode("utf-8"), page_path: updated},
                         {script_path: None, page_path: page["sha"]})
    return {"ok": True, "name": title, "category_label": "Windows Automation",
            "message": f"Added {title} as a downloadable {language} file. Review it before running.",
            "commit_url": commit_url}

def _bat_template(raw):
    text=raw.lower()
    if "dns" in text and any(w in text for w in ("flush","clear","reset","cache")):
        title,cat,desc,tags="Flush DNS Cache","network","Flushes the local DNS cache.",["DNS","Network","Windows"]
        script="@echo off\r\nsetlocal\r\ntitle Flush DNS Cache\r\necho This only flushes the local Windows DNS resolver cache.\r\nipconfig /flushdns\r\nif errorlevel 1 echo Try opening this file as Administrator.\r\npause\r\n"
    elif "network" in text and any(w in text for w in ("info","details","status","configuration")):
        title,cat,desc,tags="Show Network Information","network","Displays adapter configuration without changing settings.",["Network","Diagnostics","Read-only"]
        script="@echo off\r\nsetlocal\r\ntitle Network Information\r\nipconfig /all\r\npause\r\n"
    elif any(w in text for w in ("internet test","test internet","check internet","ping test","network test")):
        title,cat,desc,tags="Test Internet Connection","network","Tests basic public IP connectivity and DNS resolution.",["Internet","Ping","Diagnostics"]
        script="@echo off\r\nsetlocal\r\ntitle Internet Connection Test\r\nping 1.1.1.1 -n 4\r\nnslookup example.com\r\npause\r\n"
    elif "battery" in text and any(w in text for w in ("report","health","check")):
        title,cat,desc,tags="Create Battery Report","system","Creates a battery report on the current user's Desktop.",["Battery","Diagnostics","Windows"]
        script='@echo off\r\nsetlocal\r\ntitle Battery Report\r\nset "REPORT=%USERPROFILE%\\Desktop\\battery-report.html"\r\npowercfg /batteryreport /output "%REPORT%"\r\nif not errorlevel 1 start "" "%REPORT%"\r\npause\r\n'
    else:
        raise MahiAIError("Safe BAT templates currently support flush DNS, network information, internet test, and battery report. Other text tasks need a direct review before adding.")
    _check_bat_safety(script)
    return title,cat,desc,tags,script


def _add_bat(raw):
    title,cat,desc,tags,script=_bat_template(raw)
    filename=_slug(title)+".bat"
    bat_path,page_path="web/linkora/downloads/"+filename,"web/linkora/index.html"
    page=_repo_file(page_path,ref="main")
    record={"title":title,"category":cat,"description":desc,"file":filename,"path":"/linkora/downloads/"+filename,"tags":tags+["Review before running"],"bangla":"চালানোর আগে স্ক্রিপ্টের সব কমান্ড পড়ে নাও।"}
    updated=_insert_js_array_item(page["content"],"SCRIPTS",record)
    url=_commit({bat_path:script,page_path:updated},{bat_path:None,page_path:page["sha"]})
    return {"ok":True,"name":title,"category_label":"Windows Tools","message":f"Added {title}. Review the commands before running the BAT file.","commit_url":url}


@mahi_catalog_bp.post("/api/catalog-add/verify")
def catalog_add_verify():
    delay = _limited_verify_pin()
    if delay:
        response = jsonify({"ok": False, "error": "Too many PIN attempts. Please try again later."})
        response.status_code = 429
        response.headers["Retry-After"] = str(delay)
        return response
    data = request.get_json(silent=True) or {}
    password = str(data.get("password") or "")
    expected = os.environ.get("MAHI_CATALOG_PASSWORD", "6993").strip()
    if not hmac.compare_digest(password, expected):
        return jsonify({"ok": False, "error": "Incorrect password."}), 401
    return jsonify({"ok": True})


@mahi_catalog_bp.post("/api/catalog-add")
def catalog_add():
    delay = _limited()
    if delay:
        response = jsonify({"ok": False, "error": "Too many attempts. Please try again later."})
        response.status_code = 429
        response.headers["Retry-After"] = str(delay)
        return response

    data = request.get_json(silent=True) or {}
    password = str(data.get("password") or "")
    expected = os.environ.get("MAHI_CATALOG_PASSWORD", "6993").strip()
    if not hmac.compare_digest(password, expected):
        return jsonify({"ok": False, "error": "Incorrect password."}), 401

    raw = data.get("input")
    if not isinstance(raw, str) or not raw.strip():
        return jsonify({"ok": False, "error": "Paste a link or a script source."}), 400
    raw = raw.strip()
    category = str(data.get("category") or "").strip().lower()

    # Explicit category-first flow used by the new Quick Add wizard.
    if category:
        allowed = set(_LINK_CATEGORIES) | {"windows_bat", "windows_python"}
        if category not in allowed:
            return jsonify({"ok": False, "error": "Choose one of the supported Quick Add categories."}), 400
        try:
            name = _catalog_display_name(data.get("name"))
            url = None
            if category in _LINK_CATEGORIES:
                if len(raw) > 2400:
                    return jsonify({"ok": False, "error": "Website URLs are limited to 2400 characters."}), 413
                url = _url(raw)
                if not url:
                    return jsonify({"ok": False, "error": "Enter a valid public website URL starting with http:// or https://."}), 400
            elif category == "windows_bat":
                _check_bat_safety(raw)
            else:
                _check_python_source(raw)
        except MahiAIError as exc:
            return jsonify({"ok": False, "error": exc.message}), exc.status

        if not _github_token():
            return jsonify({"ok": False, "error": "Set MAHI_AI_GITHUB_TOKEN on the Flask host. OpenAI API billing is not needed."}), 503
        try:
            result = _add_link(raw, url, category, name) if category in _LINK_CATEGORIES else _add_custom_script(raw, name, category)
            return jsonify(result)
        except MahiAIError as exc:
            return jsonify({"ok": False, "error": exc.message}), exc.status
        except Exception:
            return jsonify({"ok": False, "error": "Could not publish this item. Check hosting logs and try again."}), 500

    # Backwards-compatible path for older clients that still send a free-form input.
    if len(raw) > 2400:
        return jsonify({"ok": False, "error": "Input is limited to 2400 characters."}), 413
    if not _github_token():
        return jsonify({"ok": False, "error": "Set MAHI_AI_GITHUB_TOKEN on the Flask host. OpenAI API billing is not needed."}), 503
    try:
        url = _url(raw)
        if url and re.search(r"(?i)\.bat(?:$|[?#])", urlsplit(url).path + ("?" + urlsplit(url).query if urlsplit(url).query else "")):
            raise MahiAIError("Use a task description for one of the reviewed BAT templates; arbitrary BAT imports are disabled for safety.")
        result = _add_link(raw, url) if url else _add_bat(raw)
        return jsonify(result)
    except MahiAIError as exc:
        return jsonify({"ok": False, "error": exc.message}), exc.status
    except Exception:
        return jsonify({"ok": False, "error": "Could not publish this item. Check hosting logs and try again."}), 500
