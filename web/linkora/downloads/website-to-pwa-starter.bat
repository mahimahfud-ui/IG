@echo off
cls
setlocal EnableExtensions
title WinForge - PWA Starter Setup

echo ============================================================
echo   WinForge - Convert Your Website into a PWA Starter
echo ============================================================
echo.
echo Run this BAT from your website's ROOT folder (where index.html is).
echo It creates PWA files without overwriting existing files.
echo.

if not exist "index.html" (
  echo [ERROR] index.html was not found in the current folder.
  echo Open your website project folder, then run this BAT there.
  echo.
  pause
  exit /b 1
)

set "APP_NAME="
set "SHORT_NAME="
set "START_URL=/"
set "THEME_COLOR=#10130F"
set "BG_COLOR=#10130F"

set /p "APP_NAME=App name (example: My Website): "
if not defined APP_NAME set "APP_NAME=My Website"
set /p "SHORT_NAME=Short name (up to 12 characters, example: MyApp): "
if not defined SHORT_NAME set "SHORT_NAME=MyApp"
set /p "START_URL=Start URL [/] : "
if not defined START_URL set "START_URL=/"
set /p "THEME_COLOR=Theme color hex [#10130F]: "
if not defined THEME_COLOR set "THEME_COLOR=#10130F"
set /p "BG_COLOR=Background color hex [#10130F]: "
if not defined BG_COLOR set "BG_COLOR=#10130F"

echo.
echo [1/5] Creating manifest.json...
if exist "manifest.json" (
  echo [SKIP] manifest.json already exists. It was not changed.
) else (
  >"manifest.json" echo {
  >>"manifest.json" echo   "id": "%START_URL%",
  >>"manifest.json" echo   "name": "%APP_NAME%",
  >>"manifest.json" echo   "short_name": "%SHORT_NAME%",
  >>"manifest.json" echo   "description": "%APP_NAME% web application",
  >>"manifest.json" echo   "start_url": "%START_URL%",
  >>"manifest.json" echo   "scope": "/",
  >>"manifest.json" echo   "display": "standalone",
  >>"manifest.json" echo   "orientation": "portrait",
  >>"manifest.json" echo   "theme_color": "%THEME_COLOR%",
  >>"manifest.json" echo   "background_color": "%BG_COLOR%",
  >>"manifest.json" echo   "icons": [
  >>"manifest.json" echo     {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
  >>"manifest.json" echo     {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
  >>"manifest.json" echo     {"src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
  >>"manifest.json" echo     {"src": "/pwa-icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
  >>"manifest.json" echo   ]
  >>"manifest.json" echo }
)

echo [2/5] Creating an SVG app icon...
if exist "pwa-icon.svg" (
  echo [SKIP] pwa-icon.svg already exists. It was not changed.
) else (
  >"pwa-icon.svg" echo ^<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"^>
  >>"pwa-icon.svg" echo ^<rect width="512" height="512" rx="112" fill="%THEME_COLOR%"/^>
  >>"pwa-icon.svg" echo ^<path d="M140 112h232v52H192v72h156v52H192v112h-52z" fill="#C9F77A"/^>
  >>"pwa-icon.svg" echo ^</svg^>
)

echo [2b/5] Generating PNG app icons...
if not exist "icons" mkdir "icons"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Drawing; $bg=[System.Drawing.ColorTranslator]::FromHtml('%BG_COLOR%'); $fg=[System.Drawing.Color]::FromArgb(201,247,122); foreach($s in @(192,512)){ $bmp=New-Object System.Drawing.Bitmap($s,$s); $g=[System.Drawing.Graphics]::FromImage($bmp); $g.SmoothingMode='AntiAlias'; $g.Clear($bg); $font=New-Object System.Drawing.Font('Segoe UI',$s*0.58,[System.Drawing.FontStyle]::Bold,[System.Drawing.GraphicsUnit]::Pixel); $brush=New-Object System.Drawing.SolidBrush($fg); $g.DrawString('W',$font,$brush,($s*0.08),($s*0.10)); $bmp.Save((Join-Path 'icons' ('icon-'+$s+'.png')),[System.Drawing.Imaging.ImageFormat]::Png); if($s -eq 512){ $bmp.Save((Join-Path 'icons' 'icon-maskable-512.png'),[System.Drawing.Imaging.ImageFormat]::Png) }; $brush.Dispose(); $font.Dispose(); $g.Dispose(); $bmp.Dispose() }"
if errorlevel 1 echo [WARNING] PNG icon generation failed. You may need to add valid PNG icons manually.

echo [3/5] Creating service-worker.js...
if exist "service-worker.js" (
  echo [SKIP] service-worker.js already exists. It was not changed.
) else (
  >"service-worker.js" echo const CACHE_NAME = "pwa-cache-v1";
  >>"service-worker.js" echo self.addEventListener("install", event =^> {
  >>"service-worker.js" echo   event.waitUntil(caches.open(CACHE_NAME));
  >>"service-worker.js" echo   self.skipWaiting();
  >>"service-worker.js" echo });
  >>"service-worker.js" echo self.addEventListener("activate", event =^> {
  >>"service-worker.js" echo   event.waitUntil((async () =^> {
  >>"service-worker.js" echo     const keys = await caches.keys();
  >>"service-worker.js" echo     await Promise.all(keys.filter(key =^> key !== CACHE_NAME).map(key =^> caches.delete(key)));
  >>"service-worker.js" echo     await self.clients.claim();
  >>"service-worker.js" echo   })());
  >>"service-worker.js" echo });
  >>"service-worker.js" echo self.addEventListener("fetch", event =^> {
  >>"service-worker.js" echo   if (event.request.method !== "GET" ^|^| new URL(event.request.url).origin !== self.location.origin) return;
  >>"service-worker.js" echo   event.respondWith(fetch(event.request).catch(() =^> caches.match(event.request)));
  >>"service-worker.js" echo });
)

echo [4/5] Creating the HTML integration snippet...
if exist "pwa-setup-snippet.html" (
  echo [SKIP] pwa-setup-snippet.html already exists. It was not changed.
) else (
  >"pwa-setup-snippet.html" echo ^<!-- Add these lines inside the ^<head^> of index.html --^>
  >>"pwa-setup-snippet.html" echo ^<link rel="manifest" href="/manifest.json"^>
  >>"pwa-setup-snippet.html" echo ^<meta name="theme-color" content="%THEME_COLOR%"^>
  >>"pwa-setup-snippet.html" echo ^<!-- Add this script before ^</body^> --^>
  >>"pwa-setup-snippet.html" echo ^<script^>
  >>"pwa-setup-snippet.html" echo if ("serviceWorker" in navigator) {
  >>"pwa-setup-snippet.html" echo   window.addEventListener("load", () =^> navigator.serviceWorker.register("/service-worker.js").catch(console.error));
  >>"pwa-setup-snippet.html" echo }
  >>"pwa-setup-snippet.html" echo ^</script^>
)

echo [5/5] Checking required files...
echo.
echo ============================================================
echo SETUP FILES CREATED
echo ============================================================
echo.
echo 1. Open pwa-setup-snippet.html and copy its lines into index.html
echo    as the comments describe.
echo 2. Deploy the website over HTTPS, then open it in a browser.
echo 3. Visit https://pwabuilder.com and enter your LIVE website URL.
echo 4. Use Package For Stores ^> Google Play Store and follow its checks.
echo 5. Test the generated Android package before Play Console upload.
echo.
echo IMPORTANT:
echo - This is a PWA starter, not a finished Play Store release.
echo - PWABuilder may require PNG icons (192x192 and 512x512), screenshots,
echo   privacy policy, signing details and other store metadata.
echo - Google Play requires a Play Console developer account and review.
echo - Existing files are never overwritten by this script.
echo.
pause
endlocal
