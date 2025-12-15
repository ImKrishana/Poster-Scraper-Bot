from contextlib import suppress
from re import IGNORECASE, findall, search

import cloudscraper  # noqa: F401
from imdbinfo import search_title, get_movie
from pycountry import countries as conn
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from config import Config
from ..core.EchoClient import EchoBot
from ..helper.utils.btns import EchoButtons
from ..helper.utils.msg_util import send_message, edit_message, delete_message
from ..helper.utils.xtra import _get_readable_time, _sync_to_async, _task

IMDB_GENRE_EMOJI = {
    "Action": "🚀",
    "Adult": "🔞",
    "Adventure": "🌋",
    "Animation": "🎠",
    "Biography": "📜",
    "Comedy": "🪗",
    "Crime": "🔪",
    "Documentary": "🎞",
    "Drama": "🎭",
    "Family": "👨‍👩‍👧‍👦",
    "Fantasy": "🫧",
    "Film Noir": "🎯",
    "Game Show": "🎮",
    "History": "🏛",
    "Horror": "🧟",
    "Musical": "🎻",
    "Music": "🎸",
    "Mystery": "🧳",
    "News": "📰",
    "Reality-TV": "🖥",
    "Romance": "🥰",
    "Sci-Fi": "🌠",
    "Short": "📝",
    "Sport": "⛳",
    "Talk-Show": "👨‍🍳",
    "Thriller": "🗡",
    "War": "⚔",
    "Western": "🪩",
}
LIST_ITEMS = 4

@_task
async def _imdb_search(client, message):
    if " " in message.text:
        k = await send_message(message, "<i>Searching IMDB ...</i>")
        title = message.text.split(" ", 1)[1]
        user_id = message.from_user.id
        buttons = EchoButtons()
        result = search(r"tt(\d+)", title, IGNORECASE)
        if result:
            movieid = result.group(1)
            movie = await _sync_to_async(get_movie, movieid)
            if movie:
                buttons.data_button(
                    f"🎬 {movie.title} ({getattr(movie, 'year', 'N/A')})",
                    f"imdb {user_id} movie {movieid}",
                )
            else:
                return await edit_message(k, "<i>No Results Found</i>")
        else:
            movies = _get_poster(title, bulk=True)
            if not movies:
                return await edit_message(
                    k, "<i>No Results Found</i>, Try Again or Use <b>Title ID</b>"
                )
            for movie in movies:
                buttons.data_button(
                    f"🎬 {movie.title} ({getattr(movie, 'year', 'N/A')})",
                    f"imdb {user_id} movie {movie.id}",
                )
        buttons.data_button("🚫 Close 🚫", f"imdb {user_id} close")
        await edit_message(
            k,
            "<b><i>Search Results found on IMDb.com</i></b>",
            buttons.build(1),
        )
    else:
        await send_message(
            message,
            "<i>Send Movie / TV Series Name along with /imdb Command or send IMDB URL</i>",
        )


def _get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = query.strip().lower()
        title = query
        year = findall(r"[1-2]\d{3}$", query, IGNORECASE)
        if year:
            year = _list_to_str(year[:1])
            title = query.replace(year, "").strip()
        elif file is not None:
            year = findall(r"[1-2]\d{3}", file, IGNORECASE)
            if year:
                year = _list_to_str(year[:1])
        else:
            year = None
        movieid = search_title(title.lower()).titles
        if not movieid:
            return None
        if year:
            filtered = list(
                filter(lambda k: str(k.year or "") == str(year), movieid)
            ) or movieid
        else:
            filtered = movieid
        movieid = (
            list(filter(lambda k: k.kind in ["movie", "tvSeries"], filtered))
            or filtered
        )
        if bulk:
            return movieid
        movieid = movieid[0].id
    else:
        movieid = query
    movie = get_movie(movieid)
    if getattr(movie, "release_date", None):
        date = movie.release_date
    elif getattr(movie, "year", None):
        date = movie.year
    else:
        date = "N/A"
    plot = None
    for keyword in ["plot", "summaries", "synopses"]:
        plot_data = getattr(movie, keyword, None)
        if isinstance(plot_data, list):
            plot = plot_data[0]
        else:
            plot = plot_data
        if plot:
            break
    if plot and len(plot) > 300:
        plot = f"{plot[:300]}..."
    trailer_list = getattr(movie, "trailers", None)
    trailer = trailer_list[-1] if trailer_list else None
    return {
        "title": movie.title,
        "trailer": trailer or "https://imdb.com/",
        "votes": str(getattr(movie, "votes", "N/A") or "N/A"),
        "aka": _list_to_str(getattr(movie, "title_akas", []) or []) or "N/A",
        "seasons": (
            len(movie.info_series.display_seasons)
            if getattr(movie, "info_series", None)
            and getattr(movie.info_series, "display_seasons", None)
            else "N/A"
        ),
        "box_office": getattr(movie, "worldwide_gross", "N/A") or "N/A",
        "localized_title": getattr(movie, "title_localized", "N/A") or "N/A",
        "kind": (getattr(movie, "kind", "N/A") or "N/A").capitalize(),
        "imdb_id": f"tt{movie.imdb_id}",
        "cast": _list_to_str([i.name for i in getattr(movie, "stars", [])]) or "N/A",
        "runtime": _get_readable_time(
            int(getattr(movie, "duration", 0) or "0") * 60
        )
        or "N/A",
        "countries": _list_to_hash(getattr(movie, "countries", []) or []) or "N/A",
        "languages": _list_to_hash(
            getattr(movie, "languages_text", []) or []
        )
        or "N/A",
        "director": _list_to_str(
            [i.name for i in getattr(movie, "directors", [])]
        )
        or "N/A",
        "writer": _list_to_str(
            [i.name for i in getattr(movie, "categories", []).get("writer", [])]
        )
        or "N/A",
        "producer": _list_to_str(
            [i.name for i in getattr(movie, "categories", []).get("producer", [])]
        )
        or "N/A",
        "composer": _list_to_str(
            [i.name for i in getattr(movie, "categories", []).get("composer", [])]
        )
        or "N/A",
        "cinematographer": _list_to_str(
            [
                i.name
                for i in getattr(movie, "categories", []).get("cinematographer", [])
            ]
        )
        or "N/A",
        "music_team": _list_to_str(
            [
                i.name
                for i in getattr(movie, "categories", []).get("music_department", [])
            ]
        )
        or "N/A",
        "release_date": getattr(movie, "release_date", "N/A") or "N/A",
        "year": str(getattr(movie, "year", "N/A") or "N/A"),
        "genres": _list_to_hash(getattr(movie, "genres", []) or [], emoji=True)
        or "N/A",
        "poster": getattr(
            movie,
            "cover_url",
            "https://telegra.ph/file/5af8d90a479b0d11df298.jpg",
        )
        or "https://telegra.ph/file/5af8d90a479b0d11df298.jpg",
        "plot": plot or "N/A",
        "rating": str(getattr(movie, "rating", "N/A") or "N/A") + " / 10",
        "url": getattr(movie, "url", "N/A") or "N/A",
        "url_cast": f"https://www.imdb.com/title/tt{movieid}/fullcredits#cast",
        "url_releaseinfo": f"https://www.imdb.com/title/tt{movieid}/releaseinfo",
    }


def _list_to_str(k):
    if not k:
        return ""
    if len(k) == 1:
        return str(k[0])
    if LIST_ITEMS:
        k = k[: int(LIST_ITEMS)]
        return " ".join(f"{elem}," for elem in k)[:-1] + " ..."
    return " ".join(f"{elem}," for elem in k)[:-1]


def _list_to_hash(k, flagg=False, emoji=False):
    listing = ""
    if not k:
        return ""
    if len(k) == 1:
        if not flagg:
            if emoji:
                return str(
                    IMDB_GENRE_EMOJI.get(k[0], "")
                    + " #"
                    + k[0].replace(" ", "_").replace("-", "_")
                )
            return str("#" + k[0].replace(" ", "_").replace("-", "_"))
        try:
            conflag = conn.get(name=k[0]).flag
            return str(f"{conflag} #" + k[0].replace(" ", "_").replace("-", "_"))
        except AttributeError:
            return str("#" + k[0].replace(" ", "_").replace("-", "_"))
    if LIST_ITEMS:
        k = k[: int(LIST_ITEMS)]
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                with suppress(AttributeError):
                    conflag = conn.get(name=elem).flag
                    listing += f"{conflag} "
            if emoji:
                listing += f"{IMDB_GENRE_EMOJI.get(elem, '')} "
            listing += f"#{ele}, "
        return listing[:-2]
    for elem in k:
        ele = elem.replace(" ", "_").replace("-", "_")
        if flagg:
            conflag = conn.get(name=elem).flag
            listing += f"{conflag} "
        listing += f"#{ele}, "
    return listing[:-2]

@_task
async def _imdb_callback(client, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)
    if data[2] == "movie":
        await query.answer("Processing...")
        imdb = _get_poster(query=data[3], id=True)
        buttons = EchoButtons()
        if imdb.get("trailer"):
            if isinstance(imdb["trailer"], list):
                buttons.url_button("▶️ IMDb Trailer ", imdb["trailer"][-1])
                imdb["trailer"] = _list_to_str(imdb["trailer"])
            else:
                buttons.url_button("▶️ IMDb Trailer ", imdb["trailer"])
        buttons.data_button("🚫 Close 🚫", f"imdb {user_id} close")
        kb = buttons.build(1)
        template = Config.IMDB_TEMPLATE
        if imdb and template:
            cap = template.format(**imdb, **locals())
        else:
            cap = "No Results"
        target_msg = message.reply_to_message
        if imdb.get("poster"):
            try:
                await EchoBot.bot.send_photo(
                    chat_id=target_msg.chat.id,
                    photo=imdb["poster"],
                    caption=cap,
                    reply_to_message_id=target_msg.id,
                    reply_markup=kb,
                )
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                poster = imdb.get("poster").replace(".jpg", "._V1_UX360.jpg")
                await send_message(target_msg, cap, kb, photo=poster)
        else:
            await send_message(
                target_msg,
                cap,
                kb,
                photo="https://telegra.ph/file/5af8d90a479b0d11df298.jpg",
            )
        await delete_message(message, message.reply_to_message)
    else:
        await query.answer()
        await delete_message(message, message.reply_to_message)
