from collections import OrderedDict
from datetime import datetime
from calendar import month_name
from html import escape
from random import choice
from re import sub
from time import time

from markdown import markdown
from niquests import AsyncSession
from pycountry import countries
from pyrogram.enums import ButtonStyle

from .. import LOGGER
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import get_readable_time
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import edit_message, send_message
from ..helper.telegram_helper.bot_commands import BotCommands

ANILIST_URL = "https://graphql.anilist.co"
ANILIST_IMAGE = "https://img.anili.st/media/{}"
FALLBACK_IMAGE = "https://telegra.ph/file/8a5155c0fc61cc2b9728c.jpg"
TIMEOUT = 20
CACHE_TTL = 300
CACHE_MAX = 32
SPOILER_LIMIT = 900
CHARACTER_LIMIT = 700
_cache = OrderedDict()

GENRES_EMOJI = {
    "Action": "👊",
    "Adventure": choice(["🪂", "🧗‍♀"]),
    "Comedy": "🤣",
    "Drama": " 🎭",
    "Ecchi": choice(["💋", "🥵"]),
    "Fantasy": choice(["🧞", "🧞‍♂", "🧞‍♀", "🌗"]),
    "Hentai": "🔞",
    "Horror": "☠",
    "Mahou Shoujo": "☯",
    "Mecha": "🤖",
    "Music": "🎸",
    "Mystery": "🔮",
    "Psychological": "♟",
    "Romance": "💞",
    "Sci-Fi": "🛸",
    "Slice of Life": choice(["☘", "🍁"]),
    "Sports": "⚽️",
    "Supernatural": "🫧",
    "Thriller": choice(["🥶", "🔪", "🤯"]),
}

ANIME_GRAPHQL_QUERY = """
query ($id: Int, $idMal: Int, $search: String) {
  Media(id: $id, idMal: $idMal, type: ANIME, search: $search) {
    id
    idMal
    title { romaji english native }
    type
    format
    status(version: 2)
    description(asHtml: false)
    startDate { year month day }
    endDate { year month day }
    season
    seasonYear
    episodes
    duration
    chapters
    volumes
    countryOfOrigin
    source
    hashtag
    trailer { id site thumbnail }
    updatedAt
    coverImage { large }
    bannerImage
    genres
    synonyms
    averageScore
    meanScore
    popularity
    trending
    favourites
    tags { name description rank }
    relations {
      edges {
        node {
          id
          title { romaji english native }
          format
          status
          source
          averageScore
          siteUrl
        }
        relationType
      }
    }
    characters {
      edges {
        role
        node { name { full native } siteUrl }
      }
    }
    studios { nodes { name siteUrl } }
    isAdult
    nextAiringEpisode { airingAt timeUntilAiring episode }
    airingSchedule { edges { node { airingAt timeUntilAiring episode } } }
    externalLinks { url site }
    rankings { rank year context }
    reviews {
      nodes { summary rating score siteUrl user { name } }
    }
    siteUrl
  }
}
"""

CHARACTER_QUERY = """
query ($id: Int, $search: String) {
    Character (id: $id, search: $search) {
        id
        name { first last full native }
        siteUrl
        image { large }
        description
    }
}
"""

MANGA_QUERY = """
query ($id: Int, $search: String) {
    Media (id: $id, type: MANGA, search: $search) {
        id
        title { romaji english native }
        description(asHtml: false)
        startDate { year }
        type
        format
        status
        siteUrl
        averageScore
        genres
        bannerImage
    }
}
"""

DEFAULT_ANIME_TEMPLATE = """<b>{ro_title}</b>({na_title})
<b>Format</b>: <code>{format}</code>
<b>Status</b>: <code>{status}</code>
<b>Start Date</b>: <code>{startdate}</code>
<b>End Date</b>: <code>{enddate}</code>
<b>Season</b>: <code>{season}</code>
<b>Country</b>: {country}
<b>Episodes</b>: <code>{episodes}</code>
<b>Duration</b>: <code>{duration}</code>
<b>Average Score</b>: <code>{avgscore}</code>
<b>Genres</b>: {genres}
<b>Hashtag</b>: {hashtag}
<b>Studios</b>: {studios}
<b>Description</b>: <i>{description}</i>"""


def _cached(key):
    hit = _cache.get(key)
    if hit is None:
        return None
    stamp, value = hit
    if time() - stamp > CACHE_TTL:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return value


def _store(key, value):
    if value is None:
        return value
    _cache[key] = (time(), value)
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)
    return value


def cache_clear(aggressive=False):
    if aggressive:
        _cache.clear()
        return
    while len(_cache) > CACHE_MAX // 2:
        _cache.popitem(last=False)


async def _graphql(query, variables):
    try:
        async with AsyncSession() as session:
            response = await session.post(
                ANILIST_URL,
                json={"query": query, "variables": variables},
                timeout=TIMEOUT,
            )
            if response.status_code != 200:
                LOGGER.error(f"anilist: HTTP {response.status_code}")
                return None
            payload = response.json()
    except Exception as error:
        LOGGER.error(f"anilist: {error}")
        return None
    if not isinstance(payload, dict):
        return None
    for problem in payload.get("errors") or []:
        LOGGER.error(f"anilist: {problem.get('message')}")
    return payload.get("data")


async def fetch_anime(**variables):
    key = ("anime", variables.get("id"), variables.get("idMal"), variables.get("search"))
    hit = _cached(key)
    if hit is not None:
        return hit
    data = await _graphql(ANIME_GRAPHQL_QUERY, variables)
    return _store(key, (data or {}).get("Media"))


async def fetch_character(**variables):
    key = ("character", variables.get("id"), variables.get("search"))
    hit = _cached(key)
    if hit is not None:
        return hit
    data = await _graphql(CHARACTER_QUERY, variables)
    return _store(key, (data or {}).get("Character"))


async def fetch_manga(**variables):
    data = await _graphql(MANGA_QUERY, variables)
    return (data or {}).get("Media")


def _date(block):
    if not block or not block.get("day") or not block.get("year"):
        return ""
    return f"{month_name[block['month']]} {block['day']}, {block['year']}"


def _country(code):
    if not code:
        return ""
    entry = countries.get(alpha_2=code)
    if entry is None:
        return f"#{code}"
    tag = f"#{entry.name.replace(' ', '_').replace('-', '_')}"
    flag = getattr(entry, "flag", "")
    return f"{flag} {tag}" if flag else tag


def _genres(names):
    return ", ".join(
        f"{GENRES_EMOJI.get(name, '')} #{name.replace(' ', '_').replace('-', '_')}"
        for name in names or []
    )


def _clip(text, limit):
    text = text or ""
    return f"{text[:limit]}...." if len(text) > limit else text


def anime_fields(media, description_limit=500):
    trailer = media.get("trailer") or {}
    if trailer.get("site") == "youtube" and trailer.get("id"):
        trailer = f"https://youtu.be/{trailer['id']}"
    else:
        trailer = ""
    season = media.get("season")
    duration = media.get("duration")
    title = media.get("title") or {}
    return {
        "ro_title": escape(title.get("romaji") or ""),
        "na_title": escape(title.get("native") or ""),
        "en_title": escape(title.get("english") or ""),
        "format": escape((media.get("format") or "").capitalize()),
        "status": escape((media.get("status") or "").capitalize()),
        "year": media.get("seasonYear") or "N/A",
        "startdate": _date(media.get("startDate")),
        "enddate": _date(media.get("endDate")),
        "season": f"{season.capitalize()} {media.get('seasonYear')}" if season else "",
        "country": _country(media.get("countryOfOrigin")),
        "episodes": media.get("episodes") or "N/A",
        "duration": get_readable_time(duration * 60) if duration else "N/A",
        "avgscore": f"{media['averageScore']}%" if media.get("averageScore") else "",
        "genres": _genres(media.get("genres")),
        "studios": ", ".join(
            f'<a href="{escape(node["siteUrl"], quote=True)}">{escape(node["name"])}</a>'
            for node in (media.get("studios") or {}).get("nodes") or []
        ),
        "source": media.get("source") or "-",
        "hashtag": escape(media.get("hashtag") or "N/A"),
        "synonyms": ", ".join(escape(item) for item in media.get("synonyms") or []),
        "siteurl": media.get("siteUrl") or "",
        "trailer": trailer,
        "postup": datetime.fromtimestamp(media["updatedAt"]).strftime("%d %B, %Y")
        if media.get("updatedAt")
        else "",
        "description": escape(_clip(media.get("description"), description_limit)),
        "popularity": media.get("popularity") or "",
        "trending": media.get("trending") or "",
        "favourites": media.get("favourites") or "",
        "siteid": media.get("id"),
        "bannerimg": media.get("bannerImage") or "",
        "coverimg": (media.get("coverImage") or {}).get("large") or "",
    }


def fill(template, fields):
    try:
        return template.format(**fields).replace("<br>", "")
    except Exception:
        return DEFAULT_ANIME_TEMPLATE.format(**fields).replace("<br>", "")


def _plain(text):
    return markdown(text or "").replace("<p>", "").replace("</p>", "")


def _template():
    return DEFAULT_ANIME_TEMPLATE


async def _anime_view(media, user_id):
    fields = anime_fields(media)
    buttons = ButtonMaker()
    site_id = fields["siteid"]
    if fields["siteurl"]:
        buttons.url_button("AniList Info 🎬", fields["siteurl"], position="header")
    if fields["trailer"]:
        buttons.url_button("Trailer 🎞", fields["trailer"], position="header")
    for label, key in (
        ("Reviews 📑", "rev"),
        ("Tags 🎯", "tags"),
        ("Relations 🧬", "rel"),
        ("Streaming Sites 📊", "sts"),
        ("Characters 👥", "cha"),
    ):
        buttons.data_button(label, f"anime {user_id} {key} {site_id}")
    buttons.data_button("Close", f"anime {user_id} close {site_id}", style=ButtonStyle.DANGER)
    return fill(_template(), fields), buttons.build_menu(3)


def _command_name(command_key):
    commands = getattr(BotCommands, f"{command_key}Command", None)
    if isinstance(commands, (list, tuple)):
        commands = commands[0] if commands else None
    return f"/{escape(commands)}" if commands else ""


@new_task
async def anime_command(_, message):
    parts = (message.text or "").split(" ", 1)
    if len(parts) == 1 or not parts[1].strip():
        return await send_message(
            message,
            "<b>Usage:</b> Send an anime title, AniList ID, or <code>mal:&lt;id&gt;</code>.\n\n"
            "<b>Examples:</b>\n"
            f"<code>{_command_name('Anime')} Attack on Titan</code>\n"
            f"<code>{_command_name('Anime')} mal:5114</code>",
        )
    query = parts[1].strip()
    if query.lower().startswith("mal:") and query[4:].strip().isdigit():
        variables = {"idMal": int(query[4:].strip())}
    elif query.isdigit():
        variables = {"id": int(query)}
    else:
        variables = {"search": query}
    media = await fetch_anime(**variables)
    if not media:
        return await send_message(message, "<i>Nothing found on AniList.</i>")
    text, markup = await _anime_view(media, message.from_user.id)
    image = media.get("bannerImage") or (media.get("coverImage") or {}).get("large")
    try:
        await send_message(message, text, markup, photo=image or FALLBACK_IMAGE)
    except Exception:
        await send_message(message, text, markup, photo=FALLBACK_IMAGE)


def _tags(media):
    rows = [
        f'<a href="https://anilist.co/search/anime?genres={escape(tag["name"], quote=True)}">'
        f'{escape(tag["name"])}</a> {tag.get("rank", 0)}%'
        for tag in (media.get("tags") or [])[:20]
    ]
    return "<b>Tags :</b>\n\n" + ("\n".join(rows) or "No tags found.")


def _links(media):
    rows = [
        f'<a href="{escape(link["url"], quote=True)}">{escape(link["site"])}</a>'
        for link in media.get("externalLinks") or []
        if link.get("url") and link.get("site")
    ]
    return "<b>External &amp; Streaming Links :</b>\n\n" + ("\n".join(rows) or "No links found.")


def _reviews(media):
    rows = []
    for item in ((media.get("reviews") or {}).get("nodes") or [])[:8]:
        user = (item.get("user") or {}).get("name") or "Unknown"
        rows.append(
            f'<a href="{escape(item.get("siteUrl") or "", quote=True)}">{escape(item.get("summary") or "Review")}</a>\n'
            f"<b>Score :</b> <code>{item.get('score') or 'N/A'} / 100</code>\n"
            f"<i>By {escape(user)}</i>"
        )
    return "<b>Reviews :</b>\n\n" + ("\n\n".join(rows) or "No reviews found.")


def _relations(media):
    rows = []
    for edge in ((media.get("relations") or {}).get("edges") or []):
        node = edge.get("node") or {}
        title = node.get("title") or {}
        rows.append(
            f'<a href="{escape(node.get("siteUrl") or "", quote=True)}">'
            f'{escape(title.get("english") or title.get("romaji") or "Unknown")}</a>'
            f" ({escape(title.get('romaji') or 'N/A')})\n"
            f"<b>Format</b>: <code>{escape(str(node.get('format') or 'N/A').capitalize())}</code>\n"
            f"<b>Status</b>: <code>{escape(str(node.get('status') or 'N/A').capitalize())}</code>\n"
            f"<b>Average Score</b>: <code>{node.get('averageScore') or 'N/A'}%</code>\n"
            f"<b>Source</b>: <code>{escape(str(node.get('source') or 'N/A').capitalize())}</code>\n"
            f"<b>Relation Type</b>: <code>{escape(str(edge.get('relationType') or 'N/A').capitalize())}</code>"
        )
    return "<b>Relations :</b>\n\n" + ("\n\n".join(rows) or "No relations found.")


def _characters(media):
    rows = []
    for edge in ((media.get("characters") or {}).get("edges") or [])[:8]:
        node = edge.get("node") or {}
        name = node.get("name") or {}
        rows.append(
            f'<a href="{escape(node.get("siteUrl") or "", quote=True)}">'
            f'{escape(name.get("full") or "Unknown")}</a>'
            f' (<code>{escape(name.get("native") or "N/A")}</code>)\n'
            f"<b>Role :</b> {escape(str(edge.get('role') or 'N/A').capitalize())}"
        )
    return "<b>List of Characters :</b>\n\n" + ("\n\n".join(rows) or "No characters found.")


SECTIONS = {
    "tags": _tags,
    "sts": _links,
    "rev": _reviews,
    "rel": _relations,
    "cha": _characters,
}


@new_task
async def anilist_callback(_, query):
    data = query.data.split()
    if len(data) < 4 or query.from_user.id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)
    action, site_id = data[2], data[3]
    await query.answer()
    if action == "close":
        return await query.message.delete()
    media = await fetch_anime(id=int(site_id))
    if not media:
        return await edit_message(query.message, "<i>AniList did not answer.</i>")
    if action == "home":
        text, markup = await _anime_view(media, data[1])
        return await edit_message(query.message, text, markup)
    builder = SECTIONS.get(action)
    if builder is None:
        return
    buttons = ButtonMaker()
    buttons.data_button("⌫ Back", f"anime {data[1]} home {site_id}")
    await edit_message(query.message, builder(media), buttons.build_menu(1))


def _spoiler_of(description):
    if "~!" not in description or "!~" not in description:
        return "", description
    hidden = (
        description.split("~!", 1)[1]
        .rsplit("!~", 1)[0]
        .replace("~!", "")
        .replace("!~", "")
    )
    return hidden, description.split("~!", 1)[0]


async def _character_view(person, user_id):
    name = person.get("name") or {}
    header = f"<b>{escape(name.get('full') or 'Unknown')}</b> (<code>{escape(name.get('native') or 'N/A')}</code>)\n\n"
    hidden, visible = _spoiler_of(person.get("description") or "")
    buttons = ButtonMaker()
    if hidden:
        buttons.data_button("🔍 View Spoiler", f"cha {user_id} spoil {person.get('id')}")
    markup = buttons.build_menu(1) if hidden else None
    if len(visible) > CHARACTER_LIMIT:
        visible = f"{visible[:CHARACTER_LIMIT]}...."
    return header + _plain(visible), markup


@new_task
async def character_command(_, message):
    parts = (message.text or "").split(" ", 1)
    if len(parts) == 1 or not parts[1].strip():
        return await send_message(
            message,
            "<b>Usage:</b> Search AniList characters by name.\n\n"
            "<b>Example:</b>\n"
            f"<code>{_command_name('Character')} Satoru Gojo</code>",
        )
    person = await fetch_character(search=parts[1].strip())
    if not person:
        return await send_message(message, "<i>No character found.</i>")
    text, markup = await _character_view(person, message.from_user.id)
    image = (person.get("image") or {}).get("large")
    if image:
        return await send_message(message, text, markup, photo=image)
    return await send_message(message, text, markup)


@new_task
async def character_callback(_, query):
    data = query.data.split()
    if len(data) < 4 or query.from_user.id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)
    person = await fetch_character(id=int(data[3]))
    if not person:
        await query.answer()
        return await edit_message(query.message, "<i>AniList did not answer.</i>")
    if data[2] == "home":
        await query.answer()
        text, markup = await _character_view(person, data[1])
        return await edit_message(query.message, text, markup)
    await query.answer("Alert !! Shh")
    hidden, _ = _spoiler_of(person.get("description") or "")
    if len(hidden) > SPOILER_LIMIT:
        hidden = f"{hidden[:SPOILER_LIMIT]}..."
    buttons = ButtonMaker()
    buttons.data_button("⌫ Back", f"cha {data[1]} home {data[3]}")
    await edit_message(
        query.message,
        f"<b>Spoiler Ahead :</b>\n\n<tg-spoiler>{_plain(hidden)}</tg-spoiler>",
        buttons.build_menu(1),
    )


@new_task
async def manga_command(_, message):
    parts = (message.text or "").split(" ", 1)
    if len(parts) == 1 or not parts[1].strip():
        return await send_message(
            message,
            "<b>Usage:</b> Search AniList manga by title.\n\n"
            "<b>Example:</b>\n"
            f"<code>{_command_name('Manga')} Berserk</code>",
        )
    media = await fetch_manga(search=parts[1].strip())
    if not media:
        return await send_message(message, "<i>No manga found.</i>")
    title = media.get("title") or {}
    lines = [f"<b>{escape(title.get('romaji') or '')}</b>"]
    if title.get("native"):
        lines[0] += f" (<code>{escape(title['native'])}</code>)"
    if (media.get("startDate") or {}).get("year"):
        lines.append(f"<b>Start Date</b> → <code>{media['startDate']['year']}</code>")
    if media.get("status"):
        lines.append(f"<b>Status</b> → <code>{escape(str(media['status']))}</code>")
    if media.get("averageScore"):
        lines.append(f"<b>Score</b> → <code>{media['averageScore']}</code>")
    if media.get("genres"):
        lines.append("<b>Genres</b> → " + ", ".join(f"#{escape(g)}" for g in media["genres"]))
    description = escape(media.get("description") or "").replace("<br>", "")
    if description:
        lines.append(f"\n<i>{description}</i>")
    buttons = ButtonMaker()
    if media.get("siteUrl"):
        buttons.url_button("AniList Info", media["siteUrl"])
    text = "\n".join(lines)
    image = media.get("bannerImage")
    try:
        return await send_message(message, text, buttons.build_menu(1), photo=image or FALLBACK_IMAGE)
    except Exception:
        return await send_message(message, text, buttons.build_menu(1))


@new_task
async def animehelp_command(_, message):
    await send_message(
        message,
        "⌬ <b><u>AniList Help</u></b>\n\n"
        "<b>Anime search</b> — title, AniList ID, or MAL ID:\n"
        f"<code>{_command_name('Anime')} Attack on Titan</code>\n"
        f"<code>{_command_name('Anime')} mal:5114</code>\n\n"
        "<b>Character search</b> — search by name:\n"
        f"<code>{_command_name('Character')} Satoru Gojo</code>\n\n"
        "<b>Manga search</b> — search by title:\n"
        f"<code>{_command_name('Manga')} Berserk</code>",
    )


anylist_callback = anilist_callback
