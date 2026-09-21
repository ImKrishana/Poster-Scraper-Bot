import re

import requests
from pyrogram.enums import ButtonStyle

from .. import LOGGER
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task, sync_to_async
from ..helper.telegram_helper.message_utils import send_message
from ..helper.telegram_helper.button_build import ButtonMaker


BASE_DIRECT = "https://api.themoviedb.org/3"
BASE_WORKER = "https://tmdbapi.the-zake.workers.dev/3"

IMG = "https://image.tmdb.org/t/p/"


def _get_base_and_headers():
    if Config.TMDB_ACCESS_TOKEN:
        base = BASE_DIRECT
        headers = {
            "Authorization": f"Bearer {Config.TMDB_ACCESS_TOKEN}",
            "accept": "application/json",
        }
    else:
        base = BASE_WORKER
        headers = {"accept": "application/json"}
    return base, headers


def _normalize(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def _search_tmdb(query):
    LOGGER.info(f"TMDB SEARCH QUERY: {query}")

    base, headers = _get_base_and_headers()

    text = query.strip()
    year = None

    try:
        match = re.search(r"(19|20)\d{2}$", text)
        if match:
            year = match.group(0)
            text = text[:-4].strip()
            LOGGER.info(f"YEAR DETECTED: {year}")
    except Exception as e:
        LOGGER.error(f"TMDB year detection failed: {e}")

    if not text:
        LOGGER.warning("TMDB SEARCH TEXT EMPTY AFTER YEAR STRIP")
        return None

    params = {
        "query": text,
        "include_adult": "false",
        "language": "en-US",
        "page": 1,
    }

    try:
        resp = requests.get(
            f"{base}/search/multi", headers=headers, params=params, timeout=45
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        LOGGER.error("TMDB search request timed out")
        return None
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"TMDB search request failed: {e}")
        return None
    except ValueError as e:
        LOGGER.error(f"TMDB search response not valid JSON: {e}")
        return None
    except Exception as e:
        LOGGER.error(f"TMDB search unexpected error: {e}")
        return None

    try:
        results = data.get("results") or []
        results = [r for r in results if r.get("media_type") in ("movie", "tv")]
    except Exception as e:
        LOGGER.error(f"TMDB search results parsing failed: {e}")
        return None

    LOGGER.info(f"TMDB RESULTS FOUND (raw movie+tv): {len(results)}")

    if not results:
        LOGGER.warning("TMDB SEARCH RETURNED EMPTY")
        return None

    if year:
        try:
            filtered = []
            for r in results:
                rd = r.get("release_date") or r.get("first_air_date") or ""
                yr = rd[:4] if rd else ""
                if yr == year:
                    filtered.append(r)
            if filtered:
                results = filtered
                LOGGER.info(
                    f"YEAR FILTER APPLIED: {year}, RESULTS AFTER FILTER: {len(results)}"
                )
        except Exception as e:
            LOGGER.error(f"TMDB year filter failed: {e}")

    nq = _normalize(text)
    best = None
    best_score = -1

    try:
        for r in results:
            media_type = r.get("media_type")
            title = (
                r.get("title")
                or r.get("name")
                or r.get("original_title")
                or r.get("original_name")
                or ""
            )
            nt = _normalize(title)

            rd = r.get("release_date") or r.get("first_air_date") or ""
            yr = rd[:4] if rd else ""
            vote_count = r.get("vote_count", 0) or 0
            popularity = r.get("popularity", 0) or 0

            score = 0

            if len(nq) <= 3:
                if nt == nq:
                    score += 1000
                elif nq in nt:
                    score += 500
            else:
                if nt == nq:
                    score += 4000
                elif nt.startswith(nq):
                    score += 2500
                elif nq in nt:
                    score += 1500

            if year and yr == year:
                score += 5000

            score += vote_count * 2
            score += popularity * 10

            if score > best_score:
                best_score = score
                best = (media_type, r.get("id"), title, yr)
    except Exception as e:
        LOGGER.error(f"TMDB scoring failed: {e}")
        return None

    LOGGER.info(f"TMDB SELECTED: {best} WITH SCORE: {best_score}")

    return best


def _pick_sets(items):
    en, oth, nul = [], [], []
    try:
        for x in items:
            lang = x.get("iso_639_1")
            if lang == "en":
                en.append(x)
            elif lang in (None, "", "xx"):
                nul.append(x)
            else:
                oth.append(x)
        for lst in (en, oth, nul):
            lst.sort(key=lambda z: z.get("vote_count", 0), reverse=True)
    except Exception as e:
        LOGGER.error(f"TMDB pick_sets failed: {e}")
        return items
    return en or oth or nul


def _fetch_images(kind, media_id):
    base, headers = _get_base_and_headers()

    url = f"{base}/tv/{media_id}/images" if kind == "tv" else f"{base}/movie/{media_id}/images"

    LOGGER.info(f"TMDB IMAGE FETCH URL: {url}")

    result = {"posters": [], "backdrops": [], "logos": []}

    try:
        resp = requests.get(
            url,
            headers=headers,
            params={
                "include_image_language": "en,null,hi,ta,te,ml,kn,bn,mr,gu,pa,ur,fr,es,de,it,ja,ko,zh",
            },
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        LOGGER.error("TMDB image fetch timed out")
        return result
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"TMDB image fetch failed: {e}")
        return result
    except ValueError as e:
        LOGGER.error(f"TMDB image response not valid JSON: {e}")
        return result
    except Exception as e:
        LOGGER.error(f"TMDB image fetch unexpected error: {e}")
        return result

    try:
        posters_raw = data.get("posters", []) or []
        backs_raw = data.get("backdrops", []) or []
        logos_raw = data.get("logos", []) or []

        LOGGER.info(
            f"TMDB IMAGES RAW → Posters: {len(posters_raw)}, "
            f"Backdrops: {len(backs_raw)}, Logos: {len(logos_raw)}"
        )

        for x in _pick_sets(posters_raw)[:10]:
            if x.get("file_path"):
                result["posters"].append(IMG + "w500" + x["file_path"])

        backs_raw = [x for x in backs_raw if x.get("aspect_ratio", 0) >= 1.6]
        for x in _pick_sets(backs_raw)[:10]:
            if x.get("file_path"):
                result["backdrops"].append(IMG + "original" + x["file_path"])

        for x in _pick_sets(logos_raw)[:10]:
            if x.get("file_path"):
                result["logos"].append(IMG + "w500" + x["file_path"])
    except Exception as e:
        LOGGER.error(f"TMDB images parsing failed: {e}")
        return {"posters": [], "backdrops": [], "logos": []}

    LOGGER.info(
        f"TMDB IMAGES SELECTED → Posters: {len(result['posters'])}, "
        f"Backdrops: {len(result['backdrops'])}, Logos: {len(result['logos'])}"
    )

    return result


@new_task
async def tmdb(_, message):
    if len(message.command) < 2:
        return await send_message(
            message,
            "<b>New ?:</b> "
            "<code>/tmdb Movie or Series Name</code>\n\n"
            "<i>Examples:</i>\n"
            "<code>/tmdb Avatar</code>\n"
            "<code>/tmdb Avatar: The Way of Water</code>\n"
            "<code>/tmdb Avatar 2025</code>",
        )

    query = " ".join(message.command[1:]).strip()

    if not query:
        return await send_message(
            message,
            "<b>Invalid query.</b> Send a valid movie/TV show name.",
        )

    waiting = await send_message(message, f"<i>Searching:</i>\n<code>{query}</code>")

    try:
        result = await sync_to_async(_search_tmdb, query)
    except Exception as e:
        LOGGER.exception(f"TMDB search task failed: {e}")
        result = None

    if not result:
        text = "<b>Not Found</b>\n\n<i>No matching movie/TV show found.</i>"
    else:
        media_type, media_id, title, year = result

        if not media_id:
            text = "<b>Error:</b> <code>Could not resolve TMDB ID.</code>"
        else:
            try:
                images = await sync_to_async(_fetch_images, media_type, media_id)
            except Exception as e:
                LOGGER.exception(f"TMDB images task failed: {e}")
                images = {"posters": [], "backdrops": [], "logos": []}

            header = f"🎬 <b>{title}</b>"
            if year:
                header += f" ({year})"

            lines = [header, f"<b>📺 Type:</b> {media_type.upper()}", ""]

            if images["backdrops"]:
                lines.append("<b>• Landscape:</b>")
                for i, x in enumerate(images["backdrops"], 1):
                    lines.append(f'{i}. <a href="{x}">Click Here</a>')
                lines.append("")

            lines.append("<b>• Logos:</b>")
            if images["logos"]:
                for i, x in enumerate(images["logos"], 1):
                    lines.append(f'{i}. <a href="{x}">Click Here</a>')
            else:
                lines.append("No Logos Found")
            lines.append("")

            lines.append("<b>• Posters:</b>")
            if images["posters"]:
                for i, x in enumerate(images["posters"], 1):
                    lines.append(f'{i}. <a href="{x}">Click Here</a>')
            else:
                lines.append("No Posters Found")

            lines.append("\n<blockquote>Bot By ➤ @TheZake</blockquote>")

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
        except Exception as e:
            LOGGER.error(f"Failed to edit waiting message: {e}")

    try:
        return await send_message(
            message,
            text,
            reply_markup=buttons.build_menu(2),
        )
    except Exception:
        LOGGER.exception("Unexpected /tmdb command failure while sending final message")
