from flask import Flask, render_template, request, jsonify
from datetime import datetime, timezone
import json, secrets, threading, time, random
app=Flask(__name__); app.config["MAX_CONTENT_LENGTH"]=25*1024*1024
SESSIONS={}; JOBS={}; LOCK=threading.Lock()

def media_id_from_shortcode(code):
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"; code=code.rstrip("/").split("/")[-1]; value=0
    for ch in code: value=value*64+alphabet.index(ch)
    return value
def parse_ts(raw):
    try:return datetime.fromtimestamp(int(raw),tz=timezone.utc)
    except:return None
def normalize_item(item,i):
    d=item.get("string_list_data") or []; first=d[0] if d else {}; href=str(first.get("href") or "").strip()
    if not href:return None
    dt=parse_ts(first.get("timestamp")); path=href.lower(); kind="reel" if "/reel/" in path else ("post" if "/p/" in path else "other")
    shortcode=href.rstrip("/").split("/")[-1]
    try:mid=media_id_from_shortcode(shortcode)
    except:mid=None
    return {"id":f"{i}-{shortcode}","media_id":mid,"url":href,"shortcode":shortcode,"kind":kind,
            "timestamp":int(first["timestamp"]) if str(first.get("timestamp","")).isdigit() else None,
            "date":dt.strftime("%Y-%m-%d") if dt else "","time":dt.strftime("%H:%M:%S UTC") if dt else "",
            "value":str(first.get("value") or "")}
def parse_likes(payload):
    raw=payload.get("likes_media_likes") if isinstance(payload,dict) else payload
    if raw is None and isinstance(payload,dict):
        for v in payload.values():
            if isinstance(v,list): raw=v; break
    if not isinstance(raw,list): raise ValueError("likes_media_likes was not found.")
    return [x for i,v in enumerate(raw) if isinstance(v,dict) and (x:=normalize_item(v,i)) and x["media_id"] is not None]
def job(token): 
    with LOCK:return JOBS.get(token,{"running":False,"processed":0,"total":0,"success":0,"failed":0,"remaining":0,"message":"Idle"})

@app.get("/")
def index():return render_template("index.html")
@app.post("/api/login")
def login():
    b=request.get_json(silent=True) or {}; u=str(b.get("username") or "").strip(); p=str(b.get("password") or "")
    if not u or not p:return jsonify(ok=False,error="Username and password are required."),400
    try:
        from ensta import Web
        c=Web(u,p); a=c.private_info(); t=secrets.token_urlsafe(32)
        with LOCK:SESSIONS[t]={"username":u,"password":p,"client":c,"likes":[]}
        return jsonify(ok=True,token=t,username=getattr(a,"username",u))
    except Exception as e:return jsonify(ok=False,error=f"Instagram login failed: {e}"),401
@app.post("/api/import")
def imp():
    t=request.headers.get("X-Mahi-Token","")
    with LOCK:s=SESSIONS.get(t)
    if not s:return jsonify(ok=False,error="Please log in first."),401
    f=request.files.get("file")
    if not f:return jsonify(ok=False,error="Upload liked_posts.json first."),400
    try:
        likes=parse_likes(json.load(f.stream))
        with LOCK:s["likes"]=likes
        return jsonify(ok=True,total=len(likes),reels=sum(x["kind"]=="reel" for x in likes),posts=sum(x["kind"]=="post" for x in likes))
    except Exception as e:return jsonify(ok=False,error=f"Invalid Instagram export: {e}"),400
@app.get("/api/items")
def items():
    t=request.headers.get("X-Mahi-Token","")
    with LOCK:s=SESSIONS.get(t); likes=list(s.get("likes",[])) if s else []
    if not s:return jsonify(ok=False,error="Please log in first."),401
    kind=request.args.get("kind","reel"); start=request.args.get("start",""); end=request.args.get("end",""); q=request.args.get("q","").lower().strip()
    out=[x for x in likes if (kind=="all" or x["kind"]==kind) and (not start or not x["date"] or x["date"]>=start) and (not end or not x["date"] or x["date"]<=end) and (not q or q in (x["value"]+" "+x["url"]).lower())]
    return jsonify(ok=True,total=len(out),items=out)
@app.post("/api/unlike")
def unlike():
    t=request.headers.get("X-Mahi-Token",""); b=request.get_json(silent=True) or {}
    with LOCK:s=SESSIONS.get(t); likes=list(s.get("likes",[])) if s else []
    if not s:return jsonify(ok=False,error="Please log in first."),401
    ids=list(dict.fromkeys(b.get("ids") or [])); limit=max(1,min(100,int(b.get("limit") or len(ids) or 1)))
    mn=max(.5,min(300,float(b.get("minDelay") or 2))); mx=max(mn,min(300,float(b.get("maxDelay") or 5))); ids=ids[:limit]
    byid={x["id"]:x for x in likes}; chosen=[byid[x] for x in ids if x in byid and byid[x].get("media_id")]
    if not chosen:return jsonify(ok=False,error="No valid items selected."),400
    with LOCK:
        if JOBS.get(t,{}).get("running"):return jsonify(ok=False,error="An unlike job is already running."),409
        JOBS[t]={"running":True,"processed":0,"total":len(chosen),"success":0,"failed":0,"remaining":len(chosen),"message":"Starting…"}
    def worker():
        client=s["client"]; okids=[]
        for i,item in enumerate(chosen):
            try:client.unlike(item["media_id"]); ok=True; err=""; okids.append(item["id"])
            except Exception as e:ok=False; err=str(e)
            with LOCK:
                j=JOBS[t]; j["processed"]=i+1; j["success"]+=int(ok); j["failed"]+=int(not ok); j["remaining"]=len(chosen)-i-1
                j["message"]=("Unliked" if ok else "Failed")+" · "+item["date"]+" · "+item["url"]+((" · "+err) if err else "")
            if i<len(chosen)-1:time.sleep(random.uniform(mn,mx))
        with LOCK:
            s["likes"]=[x for x in s["likes"] if x["id"] not in okids]; JOBS[t]["running"]=False; JOBS[t]["message"]="Complete"
    threading.Thread(target=worker,daemon=True).start(); return jsonify(ok=True,total=len(chosen))
@app.get("/api/progress")
def progress():
    t=request.headers.get("X-Mahi-Token","")
    if t not in SESSIONS:return jsonify(ok=False,error="Not authenticated."),401
    return jsonify(ok=True,**job(t))
@app.post("/api/logout")
def logout():
    t=request.headers.get("X-Mahi-Token","")
    with LOCK:SESSIONS.pop(t,None); JOBS.pop(t,None)
    return jsonify(ok=True)
if __name__=="__main__":app.run(host="127.0.0.1",port=5050,debug=False)
