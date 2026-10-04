from html import escape
from json import dumps
from re import search as re_search
from urllib.parse import urlparse

from niquests import AsyncSession
from pyrogram.enums import ButtonStyle

from .. import LOGGER
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import send_message


def extract_url_from_text(text: str) -> str | None:
    if not text:
        return None
    match = re_search(r"https?://\S+", text)
    return match.group(0) if match else None


def format_label(key: str) -> str:
    return key.replace("_", " ").strip().title()


def format_value(value) -> str:
    if isinstance(value, (dict, list)):
        value = dumps(value, ensure_ascii=False)
    return escape(str(value))


def format_bypass_result(data: dict, url: str) -> str:
    direct_link = data.get("direct_link")
    lines = ["<b>✺ Direct Link:</b>"]

    if isinstance(direct_link, str) and direct_link:
        lines.append(
            f'<a href="{escape(direct_link, quote=True)}">Click Here</a>'
        )
    else:
        lines.append("<code>No direct link found.</code>")

    details = []
    for key, value in data.items():
        if key in {"url", "direct_link", "headers", "credits"} or value in (None, ""):
            continue
        details.append(f"<b>{format_label(key)}:</b> {format_value(value)}")

    if details:
        lines.extend(["", *details])

    lines.extend(["", "<b>✺ Original URL:</b>", f"<code>{escape(url)}</code>"])
    return "\n".join(lines)


@new_task
async def bypass(_, message):
    url = None

    if len(message.command) >= 2:
        url = message.command[1].strip()
    elif message.reply_to_message:
        replied = message.reply_to_message
        url = extract_url_from_text(replied.text or replied.caption)

    if not url:
        return await send_message(
            message,
            "<b>Usage:</b> <code>/bypass https://example.com/file</code>\n\n"
            "Send a supported DDL URL after <code>/bypass</code> or <code>/b</code>, "
            "or reply to a message containing a link.",
        )

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return await send_message(
            message,
            "<b>Invalid URL.</b> Send a complete http(s) link.",
        )

    api_url = (
        Config.POSTER_API_URL
        or "https://thezakeapi.vercel.app"
    ).rstrip("/")
    token = (Config.POSTER_API_TOKEN or "thezake").strip()

    if not token:
        LOGGER.error("POSTER_API_TOKEN is not configured")
        return await send_message(
            message,
            "<b>Bypass service is not configured.</b> "
            "Please contact the bot owner.",
        )

    waiting = await send_message(
        message,
        f"<i>Resolving direct link for:</i>\n<code>{escape(url)}</code>",
    )

    try:
        async with AsyncSession(timeout=30) as client:
            response = await client.get(
                f"{api_url}/bypass",
                params={"url": url},
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code == 401:
            text = (
                "<b>Error:</b> <code>Poster API authentication failed. "
                "Check POSTER_API_TOKEN.</code>"
            )
        elif response.status_code == 404:
            text = "<b>Error:</b> <code>Unsupported DDL host.</code>"
        elif response.status_code >= 400:
            text = f"<b>Error:</b> <code>Poster API error {response.status_code}</code>"
        else:
            data = response.json()
            if isinstance(data, dict):
                text = format_bypass_result(data, url)
            else:
                text = "<b>Error:</b> <code>Unexpected API response.</code>"

    except ValueError as error:
        LOGGER.error("Bypass API request failed: %s", error)
        text = "<b>Error:</b> <code>Could not resolve the direct link right now.</code>"
    except Exception:
        LOGGER.exception("Unexpected /bypass command failure")
        text = "<b>Error:</b> <code>Could not resolve the direct link right now.</code>"

    buttons = ButtonMaker()
    buttons.url_button("Developer", "https://t.me/TheZake", style=ButtonStyle.PRIMARY)
    buttons.url_button(
        "⭐ Source Code",
        "https://github.com/ImKrishana/Poster-Scraper-Bot",
        style=ButtonStyle.SUCCESS,
    )

    if waiting:
        try:
            return await waiting.edit(
                text=text,
                reply_markup=buttons.build_menu(2),
            )
        except Exception:
            pass

    return await send_message(
        message,
        text,
        reply_markup=buttons.build_menu(2),
    )
