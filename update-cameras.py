#!/usr/bin/env python3
"""
update-cameras.py — refresh the NZ road-camera list.

Run this whenever you want to pick up cameras NZTA has added or removed:

    python3 tools/update-cameras.py

It does two things:
  1. downloads the current camera list from NZTA's Traffic & Travel API
  2. writes `cameras.json` and re-bakes the same list into `index.html`
     (between the <script id="baked-cameras"> … </script> markers)

Only the Python standard library is used — nothing to install.
The list is also re-read at runtime by the "Reload camera list" button, so if
you only commit cameras.json the live site still picks it up on next click.
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

API = "https://trafficnz.info/service/traffic/rest/4/cameras/all"
ROOT = Path(__file__).resolve().parent.parent
JSON_OUT = ROOT / "cameras.json"
HTML = ROOT / "index.html"
START = '<script id="baked-cameras" type="application/json">'
END = "</script>"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nz-webcam-wall/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def parse(xml_bytes: bytes) -> list:
    root = ET.fromstring(xml_bytes)
    out = []
    for cam in root.findall("camera"):
        def txt(tag, node=cam):
            el = node.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""

        cid = txt("id")
        if not cid:
            continue
        out.append({
            "i": cid,                                  # camera id (image URL is /camera/{id}.jpg)
            "n": txt("name") or f"Camera {cid}",        # name
            "d": txt("description"),                    # direction / description
            "r": txt("region/name"),                    # region
            "h": txt("highway"),                        # highway
            "la": txt("latitude"),
            "lo": txt("longitude"),
            "o": 1 if txt("offline").lower() == "true" else 0,
            "m": 1 if txt("underMaintenance").lower() == "true" else 0,
        })
    # road cameras first in a sensible order, then by name
    out.sort(key=lambda c: (c["r"] or "zz", c["n"].lower()))
    return out


def bake(cams: list) -> None:
    if not HTML.exists():
        print(f"! {HTML.name} not found — wrote cameras.json only")
        return
    html = HTML.read_text(encoding="utf-8")
    payload = json.dumps(cams, separators=(",", ":")).replace("<", "\\u003c")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(html):
        print(f"! couldn't find the baked-cameras block in {HTML.name} — skipping bake")
        return
    html = pattern.sub(lambda _: START + payload + END, html, count=1)
    HTML.write_text(html, encoding="utf-8")
    print(f"baked {len(cams)} cameras into {HTML.name} ({len(payload) / 1024:.1f} KB)")


def main() -> int:
    print(f"fetching {API}")
    try:
        cams = parse(fetch(API))
    except Exception as e:                                    # noqa: BLE001
        print(f"! download/parse failed: {e}")
        print("  (network down, or NZTA changed the endpoint — the site keeps working off its baked copy)")
        return 1
    if not cams:
        print("! NZTA returned an empty list — refusing to overwrite good data")
        return 1

    live = [c for c in cams if not c["o"]]
    regions = sorted({c["r"] for c in cams if c["r"]})
    print(f"got {len(cams)} cameras ({len(live)} online) across {len(regions)} regions")

    JSON_OUT.write_text(json.dumps(cams, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {JSON_OUT.relative_to(ROOT)} ({JSON_OUT.stat().st_size / 1024:.1f} KB)")
    bake(cams)
    print("done — commit cameras.json" + (" and index.html" if HTML.exists() else "") + " and push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
