#!/usr/bin/env python3
"""Download official site/app icons and cache small local WebP files for MahiFlix."""
from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "web" / "mahiflix" / "logo-sources.json"
LOGO_DIR = ROOT / "web" / "mahiflix" / "logos"
BRAND_SOURCE = ROOT / "web" / "Firefly (1).png"
BRAND_OUTPUT = ROOT / "web" / "brand-m.webp"
USER_AGENT = "MahiCloud-LogoCache/1.0 (+https://mahicloud.onrender.com)"
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
TIMEOUT = 15


def as_webp(data: bytes, size: int) -> bytes:
    with Image.open(io.BytesIO(data)) as source:
        source.seek(0)
        image = source.convert("RGBA")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
        out = io.BytesIO()
        canvas.save(out, "WEBP", quality=89, method=6, exact=True)
        return out.getvalue()


def download_candidate(session: requests.Session, url: str) -> bytes | None:
    if not isinstance(url, str) or urlparse(url).scheme != "https":
        return None
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
        try:
            if response.status_code != 200 or urlparse(response.url).scheme != "https":
                return None
            content_type = response.headers.get("Content-Type", "").lower()
            if not content_type.startswith("image/") and "octet-stream" not in content_type:
                return None
            chunks, total = [], 0
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    return None
                chunks.append(chunk)
            data = b"".join(chunks)
            if not data:
                return None
            # Confirm that Pillow can decode it before selecting this candidate.
            with Image.open(io.BytesIO(data)) as check:
                check.verify()
            return data
        finally:
            response.close()
    except (requests.RequestException, OSError, ValueError, UnidentifiedImageError):
        return None


def main() -> None:
    if not BRAND_SOURCE.is_file():
        raise SystemExit(f"Uploaded MahiCloud logo is missing: {BRAND_SOURCE}")
    BRAND_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(BRAND_SOURCE) as image:
        image.seek(0)
        image = image.convert("RGBA")
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        image.save(BRAND_OUTPUT, "WEBP", quality=91, method=6, exact=True)
    print(f"Optimized MahiCloud logo: {BRAND_OUTPUT.relative_to(ROOT)} ({BRAND_OUTPUT.stat().st_size:,} bytes)")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "image/avif,image/webp,image/png,image/*;q=0.8"})
    ok, failed = [], []
    for category in ("sites", "apps"):
        for item in manifest.get(category, []):
            domain = item["domain"]
            sources = list(item.get("sources", []))
            sources.extend([
                f"https://www.google.com/s2/favicons?sz=256&domain={domain}",
                f"https://icons.duckduckgo.com/ip3/{domain}.ico",
                f"https://{domain}/favicon.ico",
                f"https://{domain}/favicon.png",
            ])
            output = LOGO_DIR / (item["id"] + ".webp")
            downloaded = None
            selected_url = None
            for url in sources:
                downloaded = download_candidate(session, url)
                if downloaded:
                    selected_url = url
                    break
            if downloaded is None:
                failed.append(item["id"])
                print(f"FALLBACK {item['id']}: no decodable image found; browser will use safe fallback")
                continue
            try:
                output.write_bytes(as_webp(downloaded, 128))
                ok.append(item["id"])
                print(f"OK {item['id']}: {urlparse(selected_url).netloc} -> {output.stat().st_size:,} bytes")
            except (OSError, ValueError, UnidentifiedImageError) as exc:
                failed.append(item["id"])
                print(f"FALLBACK {item['id']}: conversion failed ({type(exc).__name__})")
                if output.exists():
                    output.unlink()

    page_path = ROOT / "web" / "index.html"
    page = page_path.read_text(encoding="utf-8")
    page = page.replace("/Firefly%20(1).png", "/brand-m.webp")
    page = page.replace("/Firefly (1).png", "/brand-m.webp")
    page = page.replace('href="/brand-m.webp" type="image/png"', 'href="/brand-m.webp" type="image/webp"')
    page = page.replace('href="/brand-m.webp" type="image/svg+xml"', 'href="/brand-m.webp" type="image/webp"')
    page_path.write_text(page, encoding="utf-8")
    print(f"Logo asset summary: {len(ok)} cached, {len(failed)} fallback(s)")
    if failed:
        print("Items without a local logo:", ", ".join(failed))


if __name__ == "__main__":
    main()
