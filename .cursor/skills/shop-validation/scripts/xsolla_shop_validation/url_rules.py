"""URL and identifier rules the editor applies to block values.

These back the component checks: a lightbox action's url has to be something a
player can open, a link action's url has to be a url at all, a lead or sidebar
store button has to point at the right storefront's host, and a site name and
page path have their own character rules.

``validate_url_with_relative`` and ``validate_lead_platform_url`` follow the
current implementations, which parse the url rather than pattern-match it — an
earlier regex-based version of both accepted inputs the editor now rejects
(whitespace, protocol-relative ``//host``, backslashes, hosts with no real TLD).
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

YOUTUBE_HOST = re.compile(r"^https?://(?:www\.)?(youtu\.be|youtube\.com)", re.IGNORECASE)
YOUTUBE_ID = re.compile(
    r"^(?:https?://)?(?:www\.)?"
    r"(?:youtu\.be/|youtube\.com/(?:embed/|v/|watch\?v=|watch\?.+&v=))"
    r"([\w-]{11})(?:\S*)$"
)
VIMEO = re.compile(r"^(?:https?://)?(www\.)?vimeo\.com/(\d+)/?$", re.IGNORECASE)
STEAM_VIDEO_ID = re.compile(r"\d+(?!%)(.)(?=/movie)")
EPIC_GAMES = re.compile(r"^https?://([a-zA-Z0-9-]+\.)*epicgames\.com/.*$")

SITE_NAME = re.compile(r"^[a-z0-9-]{1,80}$")
PAGE_PATH = re.compile(r"^/[a-z0-9-/:]{1,80}$")

# Exactly what the editor accepts as an absolute url's scheme.
ABSOLUTE_URL_PROTOCOLS = frozenset(["http", "https", "ftp"])

# The only two the uploader accepts. Not an extended guess: a `.mov` url is
# rejected, so accepting one here would pass a payload the editor refuses.
ACCEPT_VIDEO_FORMATS = (".mp4", ".webm")

# A lead or sidebar store button must point at its own storefront. The check is
# host equality against these, so a Steam button carrying a Google Play link is
# an error rather than a working link to the wrong shop.
PLATFORM_DEFAULT_URLS = {
    "amazon": "https://www.amazon.com/",
    "app_store": "https://apps.apple.com/",
    "epic": "https://store.epicgames.com/",
    "galaxy": "https://www.galaxystore.samsung.com/",
    "google": "https://play.google.com/",
    "app_gallery": "https://appgallery.huawei.com/",
    "microsoft": "https://apps.microsoft.com/",
    "playstation": "https://store.playstation.com/",
    "steam": "https://store.steampowered.com/",
    "xbox": "https://www.xbox.com/",
}


def youtube_id(url):
    match = YOUTUBE_ID.match(url or "")
    return match.group(1) if match else ""


def steam_video_id(url):
    match = STEAM_VIDEO_ID.search(url or "")
    return match.group(0) if match else ""


def is_youtube_url(url):
    return bool(YOUTUBE_HOST.match(url or ""))


def validate_youtube_video_url(url):
    return bool(youtube_id(url))


def validate_vimeo_url(url):
    return bool(VIMEO.match(url or ""))


def validate_steam_video_url(url):
    return bool(steam_video_id(url))


def validate_epic_games_url(url):
    return bool(EPIC_GAMES.match(url or ""))


def validate_lightbox_url(url):
    """A lightbox opens a player, so the url has to be one a player understands."""
    return (
        validate_youtube_video_url(url)
        or validate_vimeo_url(url)
        or validate_steam_video_url(url)
        or validate_epic_games_url(url)
    )


def _has_invalid_url_input(value):
    """Rejected before anything else is considered.

    Whitespace anywhere, a protocol-relative ``//host`` (which inherits the
    page's scheme and breaks in preview), or a backslash.
    """
    return bool(re.search(r"\s", value)) or value.startswith("//") or "\\" in value


def _is_non_empty_relative_path(value):
    return len(value) > 1 and not re.search(r"\s", value)


def _has_valid_tld(hostname):
    parts = hostname.split(".")
    if len(parts) < 2:
        return False
    return len(parts[-1]) >= 2


def _parse_absolute(value):
    """What ``new URL(value)`` accepts: an absolute url with a scheme.

    Returns ``(scheme, hostname)`` or ``None``.  A bare ``example.com/x`` has no
    scheme and is rejected, which is the behaviour being mirrored.
    """
    parts = urlsplit(value)
    if not parts.scheme:
        return None
    return parts.scheme.lower(), (parts.hostname or "")


def validate_url_with_relative(url):
    """An absolute url, a relative path, an anchor, or a mail/phone link."""
    trimmed = (url or "").strip()
    if not trimmed or _has_invalid_url_input(trimmed):
        return False

    if trimmed.startswith("/") or trimmed.startswith("#"):
        return _is_non_empty_relative_path(trimmed)

    if trimmed.startswith("mailto:") or trimmed.startswith("tel:"):
        parsed = _parse_absolute(trimmed)
        return parsed is not None

    parsed = _parse_absolute(trimmed)
    if parsed is None:
        return False
    scheme, hostname = parsed
    if scheme not in ABSOLUTE_URL_PROTOCOLS:
        return False
    return _has_valid_tld(hostname)


def validate_video_url(url):
    without_query = re.sub(r"[?#].*$", "", url or "").lower()
    return any(without_query.endswith(ext) for ext in ACCEPT_VIDEO_FORMATS)


def validate_video(url):
    if is_youtube_url(url):
        return bool(youtube_id(url))
    return validate_video_url(url)


def validate_site_name(value):
    return bool(SITE_NAME.match(value or ""))


def validate_page_path(value):
    return value == "/" or bool(PAGE_PATH.match(value or ""))


def validate_lead_platform_url(item):
    """A store button's url must be that storefront's own host, over https.

    ``item`` is ``{platform, url}``.  Four ways to fail: no url, an unknown
    platform, the untouched preset (the field was never filled in), or a host
    that belongs to a different storefront.
    """
    if not isinstance(item, dict):
        return False
    url = (item.get("url") or "").strip()
    if not url or _has_invalid_url_input(url):
        return False

    preset = PLATFORM_DEFAULT_URLS.get(item.get("platform"))
    if not preset or url == preset:
        return False

    parsed = urlsplit(url)
    if not parsed.scheme:
        return False
    if parsed.netloc != urlsplit(preset).netloc:
        return False
    if parsed.scheme.lower() != "https":
        return False
    return True
