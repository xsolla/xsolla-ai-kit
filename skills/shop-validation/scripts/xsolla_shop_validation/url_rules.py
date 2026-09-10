"""URL and identifier rules the editor applies to block values.

These back the component checks: a lightbox action's url has to be a video url
the player can actually open, a link action's url has to be a url at all, a site
name and a page path have their own character rules.

The patterns are permissive on purpose -- they mirror what the editor accepts,
not what a strict url parser would.  Tightening them here would reject values
the platform stores happily, which is the expensive direction of wrong.
"""

from __future__ import annotations

import re

YOUTUBE_HOST = re.compile(r"^https?://(?:www\.)?(youtu\.be|youtube\.com)", re.IGNORECASE)
YOUTUBE_ID = re.compile(
    r"^(?:https?://)?(?:www\.)?"
    r"(?:youtu\.be/|youtube\.com/(?:embed/|v/|watch\?v=|watch\?.+&v=))"
    r"([\w-]{11})(?:\S*)$"
)
VIMEO = re.compile(r"^(?:https?://)?(www\.)?vimeo\.com/(\d+)/?$", re.IGNORECASE)
STEAM_VIDEO_ID = re.compile(r"\d+(?!%)(.)(?=/movie)")
EPIC_GAMES = re.compile(r"^https?://([a-zA-Z0-9-]+\.)*epicgames\.com/.*$")

# Absolute, protocol-relative, or one of the local forms the editor allows.
URL_WITH_RELATIVE = re.compile(
    r"^((?:http(s)?|ftp)://)?[\w.-]+(?:\.[\w.-]+)+[\w\-._~:/?#\[\]@!$&'()*+,;=.]+$"
    r"|^(/|#|mailto:|tel:)+([\w\-._~:/?#\[\]@%!$&'()*+,;=.]*)+$"
)

SITE_NAME = re.compile(r"^[a-z0-9-]{1,80}$")
PAGE_PATH = re.compile(r"^/[a-z0-9-/]{1,80}$")

ACCEPT_VIDEO_FORMATS = (".mp4", ".webm", ".ogg", ".mov", ".m4v")


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


def validate_url_with_relative(url):
    return bool(URL_WITH_RELATIVE.match(url or ""))


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
