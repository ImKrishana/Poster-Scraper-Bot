# ruff: noqa: E402

import faulthandler
from sys import stderr
from logging import FileHandler, getLogger

faulthandler.enable(file=stderr, all_threads=True)

from .core.config_manager import Config

Config.load()

from datetime import datetime
from logging import Formatter
from time import localtime

from pytz import timezone

from . import LOGGER, bot_loop

for _h in getLogger().handlers:
    if isinstance(_h, FileHandler):
        try:
            faulthandler.enable(file=_h.stream.fileno(), all_threads=True)
        except Exception:
            pass
        break
from .core.tg_client import TgClient

_clean_task = None


async def main():
    from asyncio import gather

    from .core.startup import (
        load_configurations,
        update_variables,
        load_settings,
        save_settings,
    )

    await load_settings()

    try:
        tz = timezone(Config.TIMEZONE)
    except Exception:
        from pytz import utc

        tz = utc

    def changetz(*args):
        try:
            return datetime.now(tz).timetuple()
        except Exception:
            return localtime()

    Formatter.converter = changetz

    await gather(
        TgClient.start_bot(), TgClient.start_user()
    )
    await gather(load_configurations(), update_variables())

    from .helper.ext_utils.files_utils import clean_all
    from .helper.ext_utils.telegraph_helper import telegraph
    from .modules import get_packages_version

    global _clean_task
    _clean_task = bot_loop.create_task(clean_all())

    await gather(
        save_settings(),
        get_packages_version(),
        telegraph.create_account(),
    )


bot_loop.run_until_complete(main())


def _handle_asyncio_exception(loop, context):
    exc = context.get("exception")
    if exc and isinstance(exc, (KeyError, ValueError)):
        msg = str(exc)
        msg_lower = msg.lower()
        if "unknown constructor" in msg_lower or "server sent an unknown" in msg_lower:
            LOGGER.warning(f"Pyrogram schema mismatch (tg side): {msg}")
            return
    loop.default_exception_handler(context)


bot_loop.set_exception_handler(_handle_asyncio_exception)

from .core.handlers import add_handlers
from .helper.ext_utils.bot_utils import create_help_buttons

create_help_buttons()
bot_loop.run_until_complete(add_handlers())

from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from .core.handlers import add_handlers
from .helper.ext_utils.bot_utils import new_task
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)


@new_task
async def restart_sessions_confirm(_, query):
    data = query.data.split()
    message = query.message
    if data[1] == "confirm":
        reply_to = message.reply_to_message
        restart_message = await send_message(reply_to, "Restarting Session(s)...")
        await delete_message(message)
        await TgClient.reload()
        await add_handlers()
        TgClient.bot.add_handler(
            CallbackQueryHandler(
                restart_sessions_confirm,
                filters=regex("^sessionrestart") & CustomFilters.sudo,
            )
        )
        await edit_message(restart_message, "Session(s) Restarted Successfully!")
    else:
        await delete_message(message)


TgClient.bot.add_handler(
    CallbackQueryHandler(
        restart_sessions_confirm,
        filters=regex("^sessionrestart") & CustomFilters.sudo,
    )
)

from .modules import restart_notification

if _clean_task is not None:
    try:
        bot_loop.run_until_complete(_clean_task)
    except Exception as e:
        LOGGER.error(f"clean_all error: {e}")
try:
    bot_loop.run_until_complete(restart_notification())
except Exception as e:
    LOGGER.error(f"restart_notification error: {e}")

LOGGER.info("Zake Client(s) & Services Started !")
bot_loop.run_forever()
