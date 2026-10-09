#!/usr/bin/env python3
"""
update-webcams.py — refresh the NZ webcam directory (online-australia.net).

    python3 tools/update-webcams.py            # verify images, then write
    python3 tools/update-webcams.py --no-verify  # skip image checks (faster)

online-australia.net is a public directory of New Zealand webcams. Its NZ pages
run from https://online-australia.net/nz/{region}/{city}/{camera}/ and each page
publishes one camera still image. Many of those cameras are not available from
any other source we use (council, surf-club and community feeds), which is why
they're worth including.

What this script does:
  1. reads the site's sitemap.xml
  2. visits every NZ camera page and pulls the title + image URL
  3. skips feeds we already cover from NZTA's road-camera list
  4. optionally verifies that each image really returns an image
  5. writes webcams.json and bakes the same list into index.html

Only the Python standard library is used. Images stay hosted by their original
operators — this script records URLs, it does not copy any imagery.
"""

import argparse
import concurrent.futures as cf
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SITEMAP = "https://online-australia.net/sitemap.xml"
BASE = "https://online-australia.net"
UA = "Mozilla/5.0 (compatible; nz-webcam-wall/1.0; +https://github.com/)"

ROOT = Path(__file__).resolve().parent.parent
JSON_OUT = ROOT / "webcams.json"
HTML = ROOT / "index.html"
START = '<script id="baked-webcams" type="application/json">'
END = "</script>"

REGION_NAMES = {
    "ackl": "Auckland", "bp": "Bay of Plenty", "cntb": "Canterbury",
    "hb": "Hawke's Bay", "mrlbr": "Marlborough", "mw": "Manawatū-Whanganui",
    "nls": "Nelson", "nrthl": "Northland", "sthl": "Southland", "tg": "Otago",
    "trn": "Taranaki", "tsmn": "Tasman", "waikato": "Waikato",
    "west-coast": "West Coast", "wllng": "Wellington",
}
CITY_FIXES = {
    "danidin": "Dunedin",              # typo on the source site
    "arthurs-pass-village": "Arthur's Pass",
    "whakapapa-village": "Whakapapa Village",
    "upper-hutt": "Upper Hutt",
    "te-anau": "Te Anau",
    "taieri-mouth": "Taieri Mouth",
    "foxton": "Foxton",
    "pongaroa": "Pongaroa",
}


def fetch(url: str, referer: str | None = None, timeout: int = 30) -> bytes:
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def titleise(slug: str) -> str:
    if slug in CITY_FIXES:
        return CITY_FIXES[slug]
    return " ".join(w.capitalize() if not w.startswith("mc") else w.capitalize()
                    for w in slug.replace("_", "-").split("-"))


def nz_camera_urls() -> list:
    xml = fetch(SITEMAP).decode("utf-8", "replace")
    urls = re.findall(r"<loc>(.*?)</loc>", xml)
    out = []
    for u in urls:
        parts = [p for p in u.rstrip("/").split("/") if p]
        # ['https:', 'online-australia.net', 'nz', region, city, camera]
        if len(parts) == 6 and parts[2] == "nz":
            out.append(u)
    return out


def parse_page(url: str) -> dict:
    parts = [p for p in url.rstrip("/").split("/") if p]
    region_slug, city_slug, cam_slug = parts[3], parts[4], parts[5]
    try:
        html = fetch(url).decode("utf-8", "replace")
    except Exception as e:                                    # noqa: BLE001
        return {"error": f"{e}", "src": url}

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    img_tag = re.search(r'<img[^>]*id="onlineaustralia"[^>]*>', html)
    image = None
    if img_tag:
        m = re.search(r'src="([^"]+)"', img_tag.group(0))
        if m:
            image = m.group(1)
    if not image:
        return {"error": "no camera image on page", "src": url}
    if image.startswith("/"):
        image = BASE + image

    windy_id = None
    m = re.search(r"images-webcams\.windy\.com/\d+/(\d+)/", image)
    if m:
        windy_id = m.group(1)

    title = re.sub(r"\s+", " ", h1.group(1)).strip() if h1 else cam_slug.replace("-", " ").title()
    title = re.sub(r"\s*(Webcam|Cam)\s*$", "", title, flags=re.I).strip() or title

    return {
        "i": cam_slug,
        "t": title,
        "c": titleise(city_slug),
        "r": REGION_NAMES.get(region_slug, titleise(region_slug)),
        "u": image,
        "p": url,
        "w": windy_id,
    }


def verify(cam: dict) -> bool:
    """True if the image URL really serves an image to a third-party site."""
    try:
        req = urllib.request.Request(cam["u"], headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
            "Referer": "https://example.github.io/nz-webcam-wall/",
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            r.read(64)                                        # touch the body
            return r.status == 200 and "image" in ctype
    except Exception:                                         # noqa: BLE001
        return False


def build(do_verify: bool = True) -> list:
    urls = nz_camera_urls()
    print(f"camera pages listed in the sitemap: {len(urls)}")

    pages = []
    with cf.ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(parse_page, urls)):
            pages.append(r)
            if (i + 1) % 50 == 0:
                print(f"  read {i + 1}/{len(urls)} pages", flush=True)

    errs = [p for p in pages if p.get("error")]
    cams = [p for p in pages if not p.get("error")]

    # drop road cameras we already carry from NZTA, and any duplicates
    kept, seen = [], set()
    dropped_road = 0
    for c in cams:
        if re.search(r"trafficnz\.info/camera/\d+\.jpg", c["u"]):
            dropped_road += 1
            continue
        if c["u"] in seen:
            continue
        seen.add(c["u"])
        kept.append(c)
    print(f"usable pages: {len(cams)} (skipped {len(errs)} unreadable, "
          f"{dropped_road} already covered by NZTA)")

    if do_verify:
        print("checking that each image still loads…")
        good = []
        with cf.ThreadPoolExecutor(8) as ex:
            for i, (c, ok) in enumerate(zip(kept, ex.map(verify, kept))):
                if ok:
                    good.append(c)
                if (i + 1) % 40 == 0:
                    print(f"  checked {i + 1}/{len(kept)}", flush=True)
        print(f"images that load: {len(good)} of {len(kept)} "
              f"(dropped {len(kept) - len(good)} dead or hotlink-blocked)")
        kept = good

    kept.sort(key=lambda c: (c["r"], c["c"], c["t"].lower()))
    return kept


def bake(cams: list) -> None:
    if not HTML.exists():
        print(f"! {HTML.name} not found — wrote webcams.json only")
        return
    html = HTML.read_text(encoding="utf-8")
    payload = json.dumps(cams, separators=(",", ":")).replace("<", "\\u003c")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(html):
        print(f"! couldn't find the baked-webcams block in {HTML.name} — skipping bake")
        return
    html = pattern.sub(lambda _: START + payload + END, html, count=1)
    HTML.write_text(html, encoding="utf-8")
    print(f"baked {len(cams)} webcams into {HTML.name} ({len(payload) / 1024:.1f} KB)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Refresh the NZ webcam directory from online-australia.net")
    ap.add_argument("--no-verify", action="store_true", help="skip checking every image URL")
    args = ap.parse_args()

    try:
        cams = build(do_verify=not args.no_verify)
    except Exception as e:                                    # noqa: BLE001
        print(f"! failed: {e}")
        print("  (the site was unreachable, or its page layout changed)")
        return 1
    if not cams:
        print("! nothing usable came back — refusing to overwrite good data")
        return 1

    JSON_OUT.write_text(json.dumps(cams, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {JSON_OUT.relative_to(ROOT)} ({JSON_OUT.stat().st_size / 1024:.1f} KB)")
    bake(cams)
    print("done — commit webcams.json and index.html, then push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
