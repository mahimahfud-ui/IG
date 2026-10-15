"""Public, rate-limited MahiCloud quick-add endpoint (no OpenAI API calls)."""
from __future__ import annotations
import base64, hashlib, hmac, html, os, re, threading, time
from urllib.parse import urlsplit
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
    for source in (meta.get("logo_sources") or [])[:8]:
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


def _add_link(raw, url):
    meta=_metadata_for_url(url)
    domain=str(meta.get("domain") or urlsplit(meta["url"]).hostname or "")
    source=" ".join([domain,str(meta.get("title") or ""),str(meta.get("description") or ""),str(meta.get("content_hint") or ""),raw]).lower()
    music=any(x in source for x in ("music","spotify","soundcloud","apple music","youtube music","deezer","tidal","bandcamp","lyrics","shazam","song","audio player"))
    movie=any(x in source for x in ("movie","film","cinema","anime","web series","tv show","tv series","streaming","watch online","drama","netflix","prime video","disney+","crunchyroll","plex","hulu","peacock","hbo","flix","yts"))
    if music:
        cat, arr, path, label, tags = "music_app","musicApps","web/apps/index.html","Music Apps",["Music","Audio"]
    elif movie:
        is_app=bool(re.search(r"\b(app|apk|android|ios|mobile|play store|app store)\b",raw.lower()+" "+str(meta.get("title","")).lower()+" "+str(meta.get("description","")).lower()))
        if re.search(r"\b(movie )?website\b",raw.lower()): is_app=False
        if is_app:
            cat,arr,path,label,tags="movie_app","movieApps","web/apps/index.html","Movie Apps",["Movie","Android/iOS"]
        else:
            cat,arr,path,label,tags="movie_website","S","web/mahiflix/index.html","Movie Websites",["Movies","Streaming"]
    else:
        raise MahiAIError("This link doesn't clearly fit Movie Websites, Movie Apps, or Music Apps. Send an official page from one of those categories.")
    name=_name(meta)
    desc=re.sub(r"\s+"," ",str(meta.get("description") or (name+" official website."))).strip()[:240]
    logo_path,logo=_download_logo(meta,str(meta["url"]))
    local_logo="/"+logo_path.removeprefix("web/")
    record={"name":name,"url":meta["url"],"domain":domain,"ads":1,"pop":70,"smooth":70,"langs":70,"new":True,"desc":desc,"logoSources":[local_logo]}
    if cat=="movie_app":
        record.update({"externalWebsite":True,"linkLabel":"Visit website","sublabel":"Official website · Verify downloads before installing","tags":tags})
    elif cat=="music_app":
        record.update({"kind":"app","linkLabel":"Visit website","sublabel":"Official website","tags":tags})
    page=_repo_file(path,ref="main")
    content=_insert_js_array_item(page["content"],arr,record)
    commit_url=_commit({path:content,logo_path:logo},{path:page["sha"],logo_path:None})
    return {"ok":True,"name":name,"category_label":label,"message":f"Added {name} to {label}; the logo is stored in GitHub.","commit_url":commit_url}


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


@mahi_catalog_bp.post("/api/catalog-add")
def catalog_add():
    delay=_limited()
    if delay:
        response=jsonify({"ok":False,"error":"Too many attempts. Please try again later."})
        response.status_code=429; response.headers["Retry-After"]=str(delay)
        return response
    data=request.get_json(silent=True) or {}
    password=str(data.get("password") or "")
    expected=os.environ.get("MAHI_CATALOG_PASSWORD","6993").strip()
    if not hmac.compare_digest(password,expected):
        return jsonify({"ok":False,"error":"Incorrect password."}),401
    raw=data.get("input")
    if not isinstance(raw,str) or not raw.strip():
        return jsonify({"ok":False,"error":"Paste a link or describe a supported BAT task."}),400
    raw=raw.strip()
    if len(raw)>2400: return jsonify({"ok":False,"error":"Input is limited to 2400 characters."}),413
    if not _github_token():
        return jsonify({"ok":False,"error":"Set MAHI_AI_GITHUB_TOKEN on the Flask host. OpenAI API billing is not needed."}),503
    try:
        url=_url(raw)
        if url and re.search(r"(?i)\.bat(?:$|[?#])",urlsplit(url).path+("?"+urlsplit(url).query if urlsplit(url).query else "")):
            raise MahiAIError("Use a task description for one of the reviewed BAT templates; arbitrary BAT imports are disabled for safety.")
        result=_add_link(raw,url) if url else _add_bat(raw)
        return jsonify(result)
    except MahiAIError as exc:
        return jsonify({"ok":False,"error":exc.message}),exc.status
    except Exception:
        return jsonify({"ok":False,"error":"Could not publish this item. Check hosting logs and try again."}),500
