import asyncio
import re
import time
from html import escape
from urllib.parse import unquote

from niquests import AsyncSession
from pyrogram.enums import ButtonStyle

from .. import LOGGER
from ..core.config_manager import Config
from ..helper.telegram_helper.message_utils import send_message
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.ext_utils.bot_utils import new_task

BASE_DIRECT = "https://api.themoviedb.org/3"
BASE_WORKER = "https://tmdbapi.the-zake.workers.dev/3"
IMG = "https://image.tmdb.org/t/p/"
CACHE_TTL = 900
CACHE_LIMIT = 200

_quality_tags = re.compile(
    r"\b(?:\d{3,4}p|4k|x26[45]|h\.?26[45]|hevc|avc|xvid|divx|aac\d?|ac3|eac3|ddp?\d(?:\.\d)?|dts(?:-hd)?|truehd|atmos|hdr\d*|10bit|8bit|web-?dl|web-?rip|blu-?ray|bd-?rip|br-?rip|dvd-?rip|hdts|cam-?rip|hdtv|remux|repack|esubs?|msubs?|subbed|dubbed|dsnp|amzn|hmax|hotstar|mkv|mp4|m4v|avi|webm|mpe?g|rar|zip|7z|part\d+)\b",
    re.IGNORECASE,
)
_site_prefix = re.compile(
    r"^\W*(?:www\.)?[\w-]+\.(?:com|net|org|xyz|me|in|to|co|cc|info|tv|link|app|online|site|club|work|icu|top|vip|pro|party|fun|cam|lol|sbs|ws)(?:\s*[-–—]+\s*|\s+)",
    re.IGNORECASE,
)

_cache = {}


def _cache_get(key):
    item = _cache.get(key)
    if not item:
        return None
    if time.monotonic() - item[0] > CACHE_TTL:
        _cache.pop(key, None)
        return None
    return item[1]


def _cache_set(key, value):
    if len(_cache) >= CACHE_LIMIT:
        oldest = min(_cache, key=lambda item: _cache[item][0])
        _cache.pop(oldest, None)
    _cache[key] = (time.monotonic(), value)


def _tidy_title(title):
    title = re.sub(r"\s-+\s", " ", title)
    return re.sub(r"\s+", " ", title).strip(" -_.")


def _clean_title(title):
    title = unquote(str(title or ""))
    title = re.sub(r"https?://\S+", " ", title)
    title = re.sub(r"\b(?:t|telegram)\.me/\S+", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\[[^\]]*\]", " ", title)
    title = re.sub(r"[\[\](){}]", " ", title)
    title = _site_prefix.sub("", title)
    title = re.sub(r"\bwww\S*", " ", title, flags=re.IGNORECASE)
    title = title.replace("_", " ")

    year = None
    years = list(re.finditer(r"\b(?:19|20)\d{2}\b", title))
    if years:
        match = years[-1]
        year = match.group(0)
        title = f"{title[:match.start()]} {title[match.end():]}"

    title = _quality_tags.sub(" ", title)
    title = re.sub(r"(?:^|\s)(?:S\d{1,2}E\d{1,3}|S\d{1,2}|E(?:PISODE)?\s?\d{1,4})(?=$|\s)", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:season|episode)\s*\d{1,4}\b", " ", title, flags=re.IGNORECASE)
    title = _tidy_title(title)
    return title, year


def _normalize(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _tokenize(value):
    return set(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _tmdb_token():
    return str(Config.TMDB_ACCESS_TOKEN or "").strip()


def _api_targets():
    token = _tmdb_token()
    headers = {"accept": "application/json"}
    params = {}

    if token:
        if len(token) < 50:
            params["api_key"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"
        return [(BASE_DIRECT, headers, params), (BASE_WORKER, {"accept": "application/json"}, {})]

    return [(BASE_WORKER, headers, params)]


async def _request_json(path, params=None):
    request_params = dict(params or {})

    for base, headers, auth_params in _api_targets():
        query_params = {**request_params, **auth_params}
        for attempt in range(3):
            try:
                async with AsyncSession(timeout=15) as client:
                    response = await client.get(
                        f"{base}{path}",
                        headers=headers,
                        params=query_params,
                    )

                if response.status_code == 401:
                    LOGGER.warning("TMDB authentication failed for %s", base)
                    break
                if response.status_code >= 500:
                    LOGGER.warning(
                        "TMDB server error %s, attempt %s/3",
                        response.status_code,
                        attempt + 1,
                    )
                    await _sleep_before_retry(attempt)
                    continue
                if response.status_code >= 400:
                    LOGGER.warning("TMDB returned %s for %s", response.status_code, path)
                    break

                payload = response.json()
                return payload if isinstance(payload, dict) else None
            except Exception as error:
                LOGGER.warning(
                    "TMDB request failed for %s, attempt %s/3: %s",
                    base,
                    attempt + 1,
                    error,
                )
                await _sleep_before_retry(attempt)

    return None


async def _sleep_before_retry(attempt):
    if attempt < 2:
        await asyncio.sleep(0.5 * (2**attempt))


def _result_title(result):
    return (
        result.get("title")
        or result.get("name")
        or result.get("original_title")
        or result.get("original_name")
        or ""
    )


def _score_result(result, query, year):
    title = _result_title(result)
    normalized_query = _normalize(query)
    normalized_title = _normalize(title)
    if not normalized_query or not normalized_title:
        return None

    score = 0
    if normalized_title == normalized_query:
        score += 10000
    elif normalized_title.startswith(normalized_query):
        score += 6000
    elif normalized_query in normalized_title:
        score += 3500
    else:
        query_tokens = _tokenize(query)
        title_tokens = _tokenize(title)
        overlap = len(query_tokens & title_tokens)
        if not query_tokens or overlap == 0:
            return None
        score += int(2500 * overlap / len(query_tokens))

    release_date = result.get("release_date") or result.get("first_air_date") or ""
    result_year = release_date[:4]
    if year:
        if result_year == year:
            score += 7000
        else:
            score -= 2500

    if result.get("original_title") == query or result.get("original_name") == query:
        score += 1000

    score += min(float(result.get("popularity") or 0), 100) * 2
    score += min(int(result.get("vote_count") or 0), 10000) * 0.1
    return score


async def _search_tmdb(query):
    title, year = _clean_title(query)
    if len(title) < 2:
        return None

    cache_key = ("search", _normalize(title), year)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    LOGGER.info("TMDB search query: %s", title)
    data = await _request_json(
        "/search/multi",
        {
            "query": title,
            "include_adult": "false",
            "language": "en-US",
            "page": 1,
        },
    )
    if not data:
        return None

    results = [
        item for item in data.get("results", [])
        if item.get("media_type") in ("movie", "tv")
    ]
    if not results:
        return None

    if year:
        matching_year = [
            item for item in results
            if (item.get("release_date") or item.get("first_air_date") or "").startswith(year)
        ]
        if matching_year:
            results = matching_year

    scored = [
        (score, item)
        for item in results
        if (score := _score_result(item, title, year)) is not None
    ]
    if not scored:
        return None

    _, best = max(scored, key=lambda item: item[0])
    result = (
        best.get("media_type"),
        best.get("id"),
        _result_title(best),
        (best.get("release_date") or best.get("first_air_date") or "")[:4],
        best.get("poster_path"),
        best.get("backdrop_path"),
    )
    _cache_set(cache_key, result)
    LOGGER.info("TMDB selected: %s", result[:4])
    return result


def _image_sort_key(item):
    return (
        int(item.get("vote_count") or 0),
        int(item.get("width") or 0) * int(item.get("height") or 0),
    )


def _select_images(items, language_order):
    groups = []
    for language in language_order:
        groups.append([item for item in items if item.get("iso_639_1") == language])
    groups.append([item for item in items if item.get("iso_639_1") not in language_order])

    selected = []
    seen = set()
    for group in groups:
        for item in sorted(group, key=_image_sort_key, reverse=True):
            path = item.get("file_path")
            if path and path not in seen:
                selected.append(item)
                seen.add(path)
    return selected


async def _fetch_images(kind, media_id):
    cache_key = ("images", kind, media_id)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    data = await _request_json(
        f"/{kind}/{media_id}/images",
        {"include_image_language": "en,null,hi,ta,te,ml,kn,bn,mr,gu,pa,ur,fr,es,de,it,ja,ko,zh"},
    )
    result = {"posters": [], "backdrops": [], "logos": []}
    if not data:
        return result

    posters = _select_images(data.get("posters", []) or [], ("en", None))[:10]
    backdrops = [item for item in data.get("backdrops", []) or [] if float(item.get("aspect_ratio") or 0) >= 1.6]
    backdrops = _select_images(backdrops, ("en", None))[:10]
    logos = _select_images(data.get("logos", []) or [], ("en", None))[:10]

    result["posters"] = [f"{IMG}w780{item['file_path']}" for item in posters]
    result["backdrops"] = [f"{IMG}original{item['file_path']}" for item in backdrops]
    result["logos"] = [f"{IMG}w500{item['file_path']}" for item in logos]
    _cache_set(cache_key, result)
    return result


def _fallback_images(poster_path, backdrop_path):
    return {
        "posters": [f"{IMG}w780{poster_path}"] if poster_path else [],
        "backdrops": [f"{IMG}original{backdrop_path}"] if backdrop_path else [],
        "logos": [],
    }


@new_task
async def tmdb(_, message):
    if len(message.command) < 2:
        return await send_message(
            message,
            "<b>New ?:</b> <code>/poster Movie or Series Name</code>\n\n"
            "<i>Examples:</i>\n"
            "<code>/poster Avatar</code>\n"
            "<code>/poster Avatar: The Way of Water</code>\n"
            "<code>/poster Avatar 2025</code>",
        )

    query = " ".join(message.command[1:]).strip()
    if not query:
        return await send_message(message, "<b>Invalid query.</b> Send a valid movie/TV show name.")

    waiting = await send_message(message, f"<i>Searching:</i>\n<code>{escape(query)}</code>")

    try:
        result = await _search_tmdb(query)
    except Exception:
        LOGGER.exception("TMDB search task failed")
        result = None

    if not result:
        text = "<b>Not Found</b>\n\n<i>No matching movie/TV show found.</i>"
    else:
        media_type, media_id, title, year, poster_path, backdrop_path = result
        try:
            images = await _fetch_images(media_type, media_id)
        except Exception:
            LOGGER.exception("TMDB images task failed")
            images = {"posters": [], "backdrops": [], "logos": []}

        if not any(images.values()):
            images = _fallback_images(poster_path, backdrop_path)

        lines = [
            f"🎬 <b>{escape(title)}</b>" + (f" ({escape(year)})" if year else ""),
            f"<b>📺 Type:</b> {escape(media_type.upper())}",
            "",
        ]

        for label, key in (("Landscape", "backdrops"), ("Logos", "logos"), ("Posters", "posters")):
            lines.append(f"<b>• {label}:</b>")
            if images[key]:
                for index, image_url in enumerate(images[key], 1):
                    lines.append(
                        f'{index}. <a href="{escape(image_url, quote=True)}">Click Here</a>'
                    )
            else:
                lines.append(f"No {label} Found")
            lines.append("")

        lines.append("<blockquote>Bot By ➤ @TheZake</blockquote>")
        text = "\n".join(lines)

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
                disable_web_page_preview=False,
            )
        except Exception:
            LOGGER.exception("Failed to edit TMDB waiting message")

    try:
        return await send_message(message, text, reply_markup=buttons.build_menu(2))
    except Exception:
        LOGGER.exception("Unexpected TMDB command failure while sending final message")
