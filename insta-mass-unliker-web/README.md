# Mahi Reel Unliker — Local Web UI

Built around the public InstaMassUnliker project by Taha Gorme:
https://github.com/TahaGorme/InstaMassUnliker

Features:
- Instagram login validation using ensta==5.2.9.
- Import liked_posts.json.
- Reels / posts / all likes filter.
- Custom start/end date filtering and search.
- Select visible items and bulk unlike.
- Per-run limit and min/max delay.
- Live progress with processed, success, failed, remaining.

Important: the source project reads liked_posts.json for the historical liked library; login alone does not fetch the entire historical likes list. This UI preserves that source behavior.

Credentials are held only in local process memory, the password field is cleared after login, and the server binds to 127.0.0.1. Do not expose this app publicly.

Run:
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python app.py

Then open http://127.0.0.1:5050

The upstream project is MIT licensed. Keep its attribution when redistributing substantial portions.
