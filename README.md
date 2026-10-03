# Quran — Read & Listen

An installable, **fully offline** Quran reader. Read the whole Quran in Arabic
alongside a translation, and listen to recorded recitations — with no internet
connection required once the content is in place.

It runs as a [Progressive Web App](https://web.dev/learn/pwa) served over HTTPS,
so **one copy of the app serves every device on your network**: phones, tablets,
and desktops all read and listen to the same files — and because the app is a
secure context, every browser offers a proper *Install* option.

---

## Features

### Reading

- **All 604 pages** of the Quran, using the standard 604-page numbering that matches
  a printed mushaf, so page numbers line up with a printed Quran.
- **Two languages at once.** Arabic is always the primary text; pick one
  translation to appear under each paragraph. Arabic is rendered with full
  Uthmani diacritics.
- **Bilingual paragraph view.** Verses are grouped into paragraphs that break at
  ruku boundaries, surah starts, and on length limits (max 7 verses / 900
  characters), so long pages stay readable.
- **Surah & Juz browsing.** Jump to any of the 114 surahs or the 30 juz'
  directly from the dashboard, with verse counts and Meccan/Medinan labels.
- **Continue reading.** The app remembers the exact page you left off on and
  offers it front-and-centre next time.
- **Bookmarks.** Press and hold anywhere on a page to bookmark it. Bookmarks are
  listed and removable from the dashboard, and sync with the app's shortcuts.

### Listening

- **Recorded recitations for every verse.** Arabic, English, and Urdu ship with
  complete verse-by-verse recordings — 18,708 audio files in total — *when your
  server copy includes them* (see "Where the content lives" below).
- **Two listening languages.** Pick up to two; the first plays for a paragraph,
  then the second plays for the same paragraph.
- **Per-language voice choice.** For each translation, switch between
  *Recitation* (a human recording, works offline) and *Device voice* (your
  device's text-to-speech, which also works offline but sounds less natural).
- **Tap-to-seek.** While audio plays, tap any line or word to continue
  playback from that exact spot.
- **Follows the text.** The currently-recited verse is highlighted and scrolled
  into view automatically.
- **Graceful fallback.** If a recording is missing or blocked, the app says so
  and falls back to the device voice rather than stopping.

### Offline & sharing

- **Works with or without bundled content.** If your server copy carries the
  Quran text and recitations, every device uses them directly — nothing is
  downloaded per-browser, so there's no storage quota and no eviction. If it
  doesn't (like this repository), any device can save its own copy from inside
  the app in one tap.
- **Per-device downloads.** Settings → *Downloads on this device* saves the
  Quran text (a few MB per language) and any recitation (~500 MB per language)
  into the browser's own storage, with progress and cancel. A device with saved
  copies keeps reading and listening even when the server is off.
- **Device voice by default.** Until a recitation is saved or available on the
  server, translations fall back to your device's text-to-speech — so the app
  is fully usable the moment it opens.
- **Installable.** Add it to your home screen and it opens full-screen, with its
  own icon and app shortcuts ("Continue reading", "Bookmarks").
- **Per-language downloads.** If you add a translation beyond the bundled three,
  "Download all pages" saves its text to this device for offline use.
- **Backup & restore.** Export every downloaded page, all bookmarks, and all
  settings into one JSON file, and merge it back onto another device with Import.

### Reading experience

- **Themes:** Light, Dark, or Match device.
- **Text size:** slider in Settings, pinch-to-zoom on the page, `+`/`-` keys, or
  `Ctrl` + scroll wheel.
- **Page turning:** configurable swipe direction (swipe left *or* right for the
  next page) plus arrow-key navigation.
- **Keyboard:** `←`/`→` turn pages, `Space` plays or pauses, `Esc` goes back.
- **Press-and-hold the page** for a quick sheet: jump to the dashboard, bookmark
  the page, flip the theme, stop audio, or change reading/listening languages.
- **Double-tap** on desktop opens the same sheet.

---

## Getting started

You only need a way to serve the folder over HTTP (a service worker and the PWA
manifest require `http(s)`, not `file://`).

### Option 1 — the launcher (recommended)

```bash
bash quran.sh
```

This serves the app over **HTTPS on a fixed port (7860)** using a self-signed
certificate (generated automatically on first run) and prints the addresses:

```
 Quran app is running

  Local:      https://localhost:7860/
  Network:    https://192.168.0.43:7860/   ← use this from another device
```

HTTPS matters: browsers require a *secure context* for PWA installation, which
means plain HTTP won't work for network addresses.

**The certificate must also be trusted.** `quran.sh` generates a local
Certificate Authority and signs the server certificate with it. The first time
you open the app from a new device, it shows a friendly prompt guiding you
through a simple one-time setup:

1. Tap **"Trust Certificate"** in the app
2. Choose **"Install certificate → CA certificate"** when your device prompts
3. Reload the page

That's it! The certificate warning disappears and you can install the app. This
is a **one-time step per device** — once trusted, it stays trusted even when
your network IP changes.

The port is fixed at 7860 by design — the app's origin (`host:port`) is what
the browser uses to key stored data and the installed PWA, so a shifting port
would orphan everything. To use a different port: `PORT=8000 bash quran.sh`.

### Option 2 — any static server

```bash
python3 -m http.server 7860
# or:  npx serve .        php -S 0.0.0.0:7860
```

### Installing it

Open the URL in your browser and choose *Add to Home screen* / *Install*.
On Android (Chrome) the prompt appears in the menu; on desktop (Chrome/Edge)
use the install icon in the address bar. Once installed, it opens in its own
window with no browser chrome.

---

## Where the content lives

```
index.html          ← the entire app: markup, styles, and logic in one file
manifest.json       ← PWA identity, icons, app shortcuts
sw.js               ← service worker: app shell + stale-while-revalidate caches
serve.py            ← HTTPS static server (local CA + signed cert, Range support)
Note: Service worker removed — the app uses the manifest for PWA installation
      and relies on browser's native caching. Simpler and works everywhere.
quran.sh            ← one-command launcher (fixed port, prints URLs)
assets/
├── icon-192.png, icon-512.png, maskable-*.png, icon.svg, favicon-32.png
├── meta.json                  ← 114 surah names, verse counts, Meccan/Medinan
└── editions.json              ← 118 translations, for "Add a language"

# optional, not in this repository (would add ~1.5 GB):
assets/pages/                 ← Quran text, one JSON file per page
│   ├── quran-uthmani/        ← Arabic   (604 pages, 2.4 MB)
│   ├── en.sahih/             ← English  (604 pages, 2.4 MB)
│   └── ur.jalandhry/         ← Urdu     (604 pages, 2.4 MB)
assets/audio/                 ← recitations, one MP3 per verse
    ├── ar/                    ← Arabic   (6,236 files, ~520 MB, mono 40 kbps)
    ├── en/                    ← English  (6,236 files, ~510 MB, mono 64 kbps)
    └── ur/                    ← Urdu     (6,236 files, ~500 MB)
```

The repository ships only the **app** (~1 MB): code, icons, and metadata. The
Quran text and recitations are content, and every device can fetch its own
copy — so there's no single right place for them to live:

1. **Server bundle (optional).** If `assets/pages/` and `assets/audio/` exist
   on the machine running the server, every device on the network uses them
   directly — no per-browser storage, no quota. This is how a personal copy
   that was populated once behaves.
2. **Per-device downloads (always available).** Settings → *Downloads on this
   device* saves text packs and recitations into the browser's IndexedDB from
   the server bundle, with progress and cancel. Works even when the server
   copy is empty, as long as *some* source is reachable.
3. **Public APIs (fallback).** Whatever is missing is fetched from
   api.alquran.cloud / cdn.islamic.network / everyayah.com on demand.
4. **Device voice (last resort).** Translations can always be spoken by the
   device's own text-to-speech.

The app tries these in order, per page and per verse, so a device always shows
the best content it can get.

Text and audio follow a **local-first** order: the device's own download, then
the server bundle at `assets/pages/<edition>/<page>.json` and
`assets/audio/<language>/SSSVVV.mp3` (surah and verse number packed as three
digits each), then the public APIs — so the app never breaks because of a gap
in any one source.

The service worker precaches the app shell, metadata, and translations list at
install, then serves cached content instantly while refreshing in the
background. Bundled audio and page text stream straight from the server with
no browser cache — the server's disk is the single shared copy; devices that
want their own use the in-app Downloads manager.

---

## Data sources

All content is freely available. Where a network lookup is used at all, it comes
from:

- **Quran text & translations** — [api.alquran.cloud](https://alquran.cloud)
- **Arabic recitation** — Mishary Rashid Alafasy, via
  [cdn.islamic.network](https://islamic.network)
- **Translation recitations** — [EveryAyah](https://everyayah.com):
  English by Ibrahim Walk (Sahih International), Urdu by Shamshad Ali Khan

Recitations are bundled as mono MP3s at 40–64 kbps — speech-grade bitrates that
keep the whole Quran's audio under 1.6 GB with no perceptible loss for spoken
text. The full Quran's text is under 8 MB.

---

## Customising

- **Add a translation:** Settings → *Add a language* → search any of the 118
  available translations, then pick it to read and/or listen.
- **Remove one:** Settings lists your added languages with a *Remove* button.
- **Change the port:** `PORT=8000 bash quran.sh`.
- **Trim disk usage:** any of the three audio languages can be deleted from
  `assets/audio/` to save ~500 MB; devices then use their own downloaded copy
  or stream from the CDN for that language.
- **Populate the bundle later:** create `assets/pages/<edition>/` and
  `assets/audio/<lang>/` with the layouts above and the server picks them up
  automatically — no app changes needed.

---

## License

MIT License — see below. Use it, fork it, share it, improve it.

```
MIT License

Copyright (c) 2026 Quran — Read & Listen contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The Quranic text, translations, and recitations remain the property of their
respective reciters and the sources above; this license covers the application
code only.
