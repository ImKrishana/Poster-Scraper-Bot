from html import escape
from json import dumps
from re import search as re_search
from urllib.parse import urlparse
from pyrogram.enums import ButtonStyle
from niquests import AsyncSession

from .. import LOGGER
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task
from ..helper.telegram_helper.message_utils import send_message
from ..helper.telegram_helper.button_build import ButtonMaker


def extract_url_from_text(text: str) -> str | None:
    if not text:
        return None
    match = re_search(r"https?://\S+", text)
    return match.group(0) if match else None


def display_label(key: str) -> str:
    return key.replace("_", " ").strip().title()


def format_value(value) -> str:
    if isinstance(value, (dict, list)):
        value = dumps(value, ensure_ascii=False)
    return escape(str(value))


def format_result(data: dict, platform: str, url: str) -> str:
    metadata = []
    poster_lines = []

    for key, value in data.items():
        if value is None or value == "" or key == "platform":
            continue

        if isinstance(value, str) and value.startswith(("http://", "https://")):
            poster_lines.append(
                f'• {display_label(key)}: '
                f'<a href="{escape(value, quote=True)}">Click Here</a>'
            )
            continue

        metadata.append(
            f"<b>{display_label(key)}:</b> {format_value(value)}"
        )

    header = [
        f"<b>✺ Source:</b> {escape(str(platform))}",
        *metadata,
        "",
        "<b>✺ Original URL:</b>",
        f"<code>{escape(url)}</code>",
    ]

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
    url = None

    if len(message.command) >= 2:
        url = message.command[1].strip()
    elif message.reply_to_message:
        replied = message.reply_to_message
        url = extract_url_from_text(replied.text or replied.caption)

    if not url:
        return await send_message(
            message,
            "<b>New ?:</b> "
            "<code>/ott https://example.com</code>\n\n"
            "Send a supported OTT url after <code>/ott</code>, "
            "or reply to a message containing a link.",
        )

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return await send_message(
            message,
            "<b>Invalid URL.</b> "
            "Send a complete http(s) link.",
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
        async with AsyncSession(timeout=30) as client:
            response = await client.get(
                f"{api_url}/poster",
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
                "<code>Unsupported platform or no poster route found.</code>"
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
                platform = data.get("platform", "unknown")
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

    except ValueError as error:
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
    buttons.url_button("Developer", "https://t.me/TheZake", style=ButtonStyle.PRIMARY)
    buttons.url_button("⭐ Source Code", "https://github.com/ImKrishana/Poster-Scraper-Bot", style=ButtonStyle.SUCCESS)


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
