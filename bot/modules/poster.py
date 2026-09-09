# bot/modules/poster.py

from html import escape
from urllib.parse import urlparse

from httpx import AsyncClient, HTTPError

from .. import LOGGER
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task
from ..helper.telegram_helper.message_utils import send_message
from ..helper.telegram_helper.button_build import ButtonMaker


PLATFORM_DOMAINS = {
    "aaonxt": ("aaonxt.com",),
    "addatimes": ("addatimes.com",),
    "aha": ("aha.video", "ahavideo.com"),
    "airtel": ("airtelxstream.in", "airtel.tv"),
    "amazon": ("primevideo.com", "amazon.com"),
    "apple": ("tv.apple.com",),
    "atrangii": ("atrangii.com",),
    "bms": ("bookmyshow.com",),
    "chaupal": ("chaupal.tv",),
    "crunchyroll": ("crunchyroll.com",),
    "dangal": ("dangalplay.com",),
    "erosnow": ("erosnow.com",),
    "hoichoi": ("hoichoi.tv", "hoichoi.com"),
    "hulu": ("hulu.com",),
    "hungama": ("hungama.com",),
    "iqyi": ("iq.com", "iqiyi.com"),
    "jojo": ("jojoapp.in", "jojo.app"),
    "lionsgate": ("lionsgateplay.com",),
    "mubi": ("mubi.com",),
    "mxplayer": ("mxplayer.in",),
    "nf": ("netflix.com",),
    "playflix": ("playflix.in",),
    "plex": ("plex.tv",),
    "sainaplay": ("sainaplay.com",),
    "shemaroo": ("shemaroome.com", "shemaroo.com"),
    "sonyliv": ("sonyliv.com",),
    "sunnxt": ("sunnxt.com",),
    "tataplay": ("tataplay.com",),
    "ticketnew": ("ticketnew.com",),
    "tubi": ("tubitv.com",),
    "ultra": ("ultratv.com", "ultraplay.com"),
    "ultrajhakaas": ("ultrajhakaas.com",),
    "viki": ("viki.com",),
    "viu": ("viu.com",),
    "viva": ("vivamax.net", "vivamax.com"),
    "wetv": ("wetv.vip",),
    "youku": ("youku.tv", "youku.com"),
    "youtube": ("youtube.com", "youtu.be", "youtube-nocookie.com"),
    "zee5": ("zee5.com",),
}


PLATFORM_NAMES = {
    "aaonxt": "AAO NXT",
    "addatimes": "Addatimes",
    "aha": "Aha Video",
    "airtel": "Airtel Xstream",
    "amazon": "Prime Video",
    "apple": "Apple TV+",
    "atrangii": "Atrangii",
    "bms": "BookMyShow",
    "chaupal": "Chaupal",
    "crunchyroll": "Crunchyroll",
    "dangal": "Dangal Play",
    "erosnow": "Eros Now",
    "hoichoi": "Hoichoi",
    "hulu": "Hulu",
    "hungama": "Hungama",
    "iqyi": "iQIYI",
    "jojo": "JOJO",
    "lionsgate": "Lionsgate Play",
    "mubi": "MUBI",
    "mxplayer": "MX Player",
    "nf": "Netflix",
    "playflix": "Playflix",
    "plex": "Plex TV",
    "sainaplay": "Saina Play",
    "shemaroo": "ShemarooMe",
    "sonyliv": "SonyLIV",
    "sunnxt": "Sun NXT",
    "tataplay": "Tata Play",
    "ticketnew": "TicketNew",
    "tubi": "Tubi",
    "ultra": "Ultra",
    "ultrajhakaas": "Ultra Jhakaas",
    "viki": "Viki",
    "viu": "Viu",
    "viva": "Vivamax",
    "wetv": "WeTV",
    "youku": "Youku",
    "youtube": "YouTube",
    "zee5": "ZEE5",
}


def find_platform(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")

    for platform, domains in PLATFORM_DOMAINS.items():
        if any(
            host == domain or host.endswith(f".{domain}")
            for domain in domains
        ):
            return platform

    return None


def format_result(data: dict, platform: str, url: str) -> str:
    title = escape(str(data.get("title") or "N/A"))
    year = escape(str(data.get("year") or "N/A"))

    header = [
        f"<b>✺ Source:</b> {PLATFORM_NAMES.get(platform, platform)}",
        f"<b>🎬 Title:</b> {title}",
        f"<b>📅 Year:</b> {year}",
        "",
        "<b>✺ Original URL:</b>",
        f"<code>{escape(url)}</code>",
    ]

    labels = {
        "landscape": "Landscape",
        "portrait": "Portrait",
        "cover": "Cover",
        "logo": "Logo",
        "thumbnail": "Thumbnail",
        "maxres": "Max resolution",
    }

    poster_lines = []

    for key, label in labels.items():
        value = data.get(key)

        if isinstance(value, str) and value.startswith(
            ("http://", "https://")
        ):
            poster_lines.append(
                f'• {label}: '
                f'<a href="{escape(value, quote=True)}">Click Here</a>'
            )

    if not poster_lines:
        for key, value in data.items():
            if isinstance(value, str) and value.startswith(
                ("http://", "https://")
            ):
                poster_lines.append(
                    f'• {escape(key.title())}: '
                    f'<a href="{escape(value, quote=True)}">Click Here</a>'
                )

    return (
        "\n".join(header)
        + "\n\n<b>⧉ Posters:</b>\n"
        + (
            "\n".join(poster_lines)
            if poster_lines
            else "• No posters found."
        )
        + "\n\n<blockquote>Bot By ➤ @TheZake</blockquote>"
    )


@new_task
async def poster(_, message):
    if len(message.command) < 2:
        return await send_message(
            message,
            "<b>New ?:</b> "
            "<code>/poster https://example.com</code>\n\n"
            "Send a supported OTT url after <code>/poster</code>.",
        )

    url = message.command[1].strip()

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return await send_message(
            message,
            "<b>Invalid URL.</b> "
            "Send a complete http(s) link.",
        )

    platform = find_platform(url)

    if not platform:
        supported = ", ".join(sorted(PLATFORM_DOMAINS))

        return await send_message(
            message,
            "<b>Unsupported platform.</b>\n\n"
            "Supported Platforms: "
            + escape(supported),
        )

    api_url = (
        Config.POSTER_API_URL
        or "https://thezakeapi.vercel.app"
    ).rstrip("/")

    token = (
        Config.POSTER_API_TOKEN
        or "thezake"
    ).strip()

    if not token:
        LOGGER.error(
            "POSTER_API_TOKEN is not configured"
        )

        return await send_message(
            message,
            "<b>Poster service is not configured.</b> "
            "Please contact the bot owner.",
        )

    waiting = await send_message(
        message,
        f"<i>Fetching poster for:</i>\n"
        f"<code>{escape(url)}</code>",
    )

    try:
        async with AsyncClient(
            timeout=45,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                f"{api_url}/posters/{platform}",
                params={"url": url},
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        if response.status_code == 401:
            text = (
                "<b>Error:</b> "
                "<code>Poster API authentication failed. "
                "Check POSTER_API_TOKEN.</code>"
            )

        elif response.status_code == 404:
            text = (
                "<b>Error:</b> "
                "<code>No poster route found for this platform.</code>"
            )

        elif response.status_code >= 400:
            text = (
                f"<b>Error:</b> "
                f"<code>Poster API error "
                f"{response.status_code}</code>"
            )

        else:
            data = response.json()

            if isinstance(data, dict):
                text = format_result(
                    data,
                    platform,
                    url,
                )
            else:
                text = (
                    "<b>Error:</b> "
                    "<code>Unexpected API response.</code>"
                )

    except (HTTPError, ValueError) as error:
        LOGGER.error(
            "Poster API request failed: %s",
            error,
        )

        text = (
            "<b>Error:</b> "
            "<code>Could not fetch poster links right now.</code>"
        )

    except Exception:
        LOGGER.exception(
            "Unexpected /poster command failure"
        )

        text = (
            "<b>Error:</b> "
            "<code>Could not fetch poster links right now.</code>"
        )

    buttons = ButtonMaker()

    buttons.url_button(
        "Developer",
        "https://t.me/Leechbots",
    )

    buttons.url_button(
        "⭐ Source Code",
        "https://github.com/ImKrishana/Poster-Scraper-Bot",
    )

    if waiting:
        try:
            return await waiting.edit(
                text=text,
                reply_markup=buttons.build_menu(2),
                disable_web_page_preview=False,
            )

        except Exception:
            pass

    return await send_message(
        message,
        text,
        reply_markup=buttons.build_menu(2),
    )


__all__ = ["poster"]
