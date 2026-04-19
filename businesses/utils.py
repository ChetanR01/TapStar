"""Helpers for parsing Google Place IDs out of whatever users paste.

Customers get confused by the Google Place ID lookup tool, so we accept
any of these inputs and try to normalise them:

  - Raw place ID:        ChIJN1t_tDeuEmsRUsoyG83frY4
  - Review URL:          https://search.google.com/local/writereview?placeid=ChIJ...
  - Maps place URL:      https://www.google.com/maps/place/.../data=!3m1!4b1!4m6!...!1s0x...:0x...
  - Maps with cid:       https://www.google.com/maps?cid=1234567890
  - Short share link:    https://g.page/r/ABC, https://maps.app.goo.gl/xyz

For short links we follow the redirect server-side (see resolve_and_parse)
so we can dig a ChIJ / ftid out of the expanded Google Maps URL.
"""
import logging
import re
from urllib.parse import parse_qs, urlparse

import requests


log = logging.getLogger(__name__)

PLACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{20,}$")
CHIJ_RE = re.compile(r"\b(ChIJ[A-Za-z0-9_-]{20,})\b")
GHIJ_RE = re.compile(r"\b(GhIJ[A-Za-z0-9_-]{20,})\b")
EIJ_RE = re.compile(r"\b(Ei[A-Za-z0-9_-]{20,})\b")
FTID_RE = re.compile(r"!1s(0x[0-9a-fA-F]+):(0x[0-9a-fA-F]+)")

SHORT_HOSTS = ("maps.app.goo.gl", "g.page", "goo.gl")
RESOLVE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
RESOLVE_TIMEOUT = 6  # seconds — keep short; form submit is waiting on us


def build_review_url_from_place_id(place_id: str) -> str:
    return f"https://search.google.com/local/writereview?placeid={place_id}"


def build_review_url_from_cid(cid: str) -> str:
    # Google redirects /maps?cid=... → the review page once the user taps "Write a review".
    return f"https://maps.google.com/?cid={cid}"


def parse_place_input(value: str) -> dict:
    """Return {place_id, review_url, raw, note} from user input.

    Never raises — if we can't parse anything useful, returns raw input
    and lets the view decide whether to reject it.
    """
    out = {"place_id": "", "review_url": "", "raw": value or "", "note": ""}
    if not value:
        return out

    text = value.strip()

    # 1. Looks like a raw place ID already
    if text.startswith(("ChIJ", "GhIJ")) and PLACE_ID_RE.match(text):
        out["place_id"] = text
        out["review_url"] = build_review_url_from_place_id(text)
        return out

    # 2. If it's a URL, pull it apart
    if text.startswith(("http://", "https://")):
        parsed = urlparse(text)
        qs = parse_qs(parsed.query)

        # writereview?placeid=... (the ideal case)
        if "placeid" in qs and qs["placeid"]:
            pid = qs["placeid"][0]
            out["place_id"] = pid
            out["review_url"] = build_review_url_from_place_id(pid)
            return out

        # ?cid=... (numeric customer ID — different from place_id, but routable)
        if "cid" in qs and qs["cid"]:
            out["review_url"] = build_review_url_from_cid(qs["cid"][0])
            out["note"] = (
                "Saved the link, but we couldn't extract a Place ID. "
                "Reviews will still open on Google."
            )
            return out

        # ?ludocid=... (legacy)
        if "ludocid" in qs and qs["ludocid"]:
            out["review_url"] = build_review_url_from_cid(qs["ludocid"][0])
            out["note"] = (
                "Saved the link, but we couldn't extract a Place ID. "
                "Reviews will still open on Google."
            )
            return out

        # Scan anywhere in the URL for a ChIJ / GhIJ place ID token
        for rex in (CHIJ_RE, GHIJ_RE, EIJ_RE):
            m = rex.search(text)
            if m:
                pid = m.group(1)
                out["place_id"] = pid
                out["review_url"] = build_review_url_from_place_id(pid)
                return out

        # Short links — can't resolve without an HTTP call. Save the URL;
        # we'll still redirect customers there on submit.
        host = (parsed.netloc or "").lower()
        if host in ("g.page", "maps.app.goo.gl", "goo.gl") or host.endswith(".page.link"):
            out["review_url"] = text
            out["note"] = (
                "Short share link saved. For best results, paste the full "
                "Google Maps review URL (with ChIJ… in it) when you have it."
            )
            return out

        # Any other Google URL — save as-is so at minimum the button opens something
        if "google." in host:
            out["review_url"] = text
            out["note"] = "We couldn't find a Place ID in that link, but saved the URL."
            return out

    # 3. Non-URL, non-ChIJ — might be a bare place ID variant
    if PLACE_ID_RE.match(text):
        out["place_id"] = text
        out["review_url"] = build_review_url_from_place_id(text)
        return out

    return out


# ------------------- Short-URL resolution (network) -------------------

def _follow_redirects(url: str) -> tuple[str, str]:
    """Return (final_url, page_html_snippet) after following redirects.

    page_html_snippet is only the first ~32 KB — enough to scrape
    og:image or fallback place_id tokens without reading a full MB page.
    Returns ("", "") on failure.
    """
    try:
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=RESOLVE_TIMEOUT,
            headers={"User-Agent": RESOLVE_USER_AGENT, "Accept-Language": "en"},
            stream=True,
        )
        final = resp.url or url
        snippet = b""
        # Only read a bit of the body — we just want the head/meta tags.
        for chunk in resp.iter_content(chunk_size=8192, decode_unicode=False):
            snippet += chunk
            if len(snippet) >= 32_000:
                break
        resp.close()
        return final, snippet.decode("utf-8", errors="replace")
    except requests.RequestException as e:
        log.warning("Failed to resolve %s: %s", url, e)
        return "", ""


def _extract_from_maps_url(url: str) -> dict:
    """Pull place_id / ftid / cid out of an *expanded* Google Maps URL."""
    out = {"place_id": "", "review_url": "", "note": ""}
    for rex in (CHIJ_RE, GHIJ_RE, EIJ_RE):
        m = rex.search(url)
        if m:
            out["place_id"] = m.group(1)
            out["review_url"] = build_review_url_from_place_id(out["place_id"])
            return out

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "placeid" in qs and qs["placeid"]:
        out["place_id"] = qs["placeid"][0]
        out["review_url"] = build_review_url_from_place_id(out["place_id"])
        return out

    m = FTID_RE.search(url)
    if m:
        try:
            cid = int(m.group(2), 16)
            out["review_url"] = build_review_url_from_cid(str(cid))
            out["note"] = "Resolved from Google Maps link."
            return out
        except ValueError:
            pass

    if "cid" in qs and qs["cid"]:
        out["review_url"] = build_review_url_from_cid(qs["cid"][0])
        return out
    if "ludocid" in qs and qs["ludocid"]:
        out["review_url"] = build_review_url_from_cid(qs["ludocid"][0])
        return out

    return out


OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _extract_og_image(html: str) -> str:
    if not html:
        return ""
    m = OG_IMAGE_RE.search(html)
    return m.group(1) if m else ""


def resolve_and_parse(value: str) -> dict:
    """parse_place_input + network-side resolution of short links.

    Also extracts an og:image from the resolved page when available
    (returned in the ``photo_url`` key). Safe to call with any value;
    network errors fall back to best-effort local parsing.
    """
    parsed = parse_place_input(value)
    parsed.setdefault("photo_url", "")

    if parsed["place_id"]:
        # Already have a place_id from local parsing — done.
        return parsed

    raw = (value or "").strip()
    if not raw.startswith(("http://", "https://")):
        return parsed

    host = (urlparse(raw).netloc or "").lower()
    needs_resolve = (
        host in SHORT_HOSTS
        or host.endswith(".page.link")
        or "google." in host
    )
    if not needs_resolve:
        return parsed

    final_url, html = _follow_redirects(raw)
    if not final_url:
        # Couldn't reach Google; keep local parse as-is.
        return parsed

    expanded = _extract_from_maps_url(final_url)
    if not (expanded["place_id"] or expanded["review_url"]):
        # Try scanning the HTML body too (some ChIJ tokens sit in scripts)
        expanded = _extract_from_maps_url(html)

    if expanded["place_id"]:
        parsed["place_id"] = expanded["place_id"]
        parsed["review_url"] = expanded["review_url"]
        parsed["note"] = expanded["note"] or "Resolved Place ID from your Google link."
    elif expanded["review_url"]:
        parsed["review_url"] = expanded["review_url"]
        parsed["note"] = expanded["note"] or (
            "Saved the resolved Google Maps link. Reviews will open on Google."
        )

    parsed["photo_url"] = _extract_og_image(html)
    return parsed


# ------------------- Google Places photo (optional, API-key gated) -------------------

def fetch_place_photo_url(place_id: str) -> str:
    """Return a direct googleusercontent.com image URL for the place's primary photo.

    Requires ``GOOGLE_PLACES_API_KEY`` in Django settings. Returns "" on any
    failure (missing key, network issue, no photos, API quota, etc.) so the
    caller can silently fall back to logo/gradient.
    """
    if not place_id:
        return ""
    try:
        from django.conf import settings
        key = getattr(settings, "GOOGLE_PLACES_API_KEY", "") or ""
    except Exception:
        key = ""
    if not key:
        return ""

    try:
        details = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={"place_id": place_id, "fields": "photo", "key": key},
            timeout=RESOLVE_TIMEOUT,
        )
        data = details.json()
        photos = (data.get("result") or {}).get("photos") or []
        if not photos:
            return ""
        ref = photos[0].get("photo_reference")
        if not ref:
            return ""

        # The photo endpoint returns a 302 → the final googleusercontent URL.
        # Follow it manually so we can cache the direct CDN URL on the model.
        photo_resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/photo",
            params={"maxwidth": "800", "photo_reference": ref, "key": key},
            allow_redirects=False,
            timeout=RESOLVE_TIMEOUT,
        )
        if photo_resp.status_code in (301, 302, 303, 307, 308):
            return photo_resp.headers.get("Location", "") or ""
        if photo_resp.status_code == 200 and photo_resp.url:
            return photo_resp.url
    except requests.RequestException as e:
        log.warning("Places photo fetch failed for %s: %s", place_id, e)
    except Exception as e:
        log.warning("Places photo unexpected error for %s: %s", place_id, e)
    return ""
