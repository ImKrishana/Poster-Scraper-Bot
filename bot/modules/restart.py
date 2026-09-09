from asyncio import create_subprocess_exec, gather
from datetime import datetime
from os import execl as osexecl
from sys import executable

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove
from pytz import timezone

from bot.version import get_version

from .. import LOGGER, intervals, scheduler
from ..core.config_manager import Config, BinConfig
from ..core.tg_client import TgClient
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.files_utils import clean_all
from ..helper.telegram_helper import button_build
from ..helper.telegram_helper.message_utils import (
    delete_message,
    send_message,
)


@new_task
async def restart_bot(_, message):
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", "botrestart confirm")
    buttons.data_button("No!", "botrestart cancel")
    button = buttons.build_menu(2)
    await send_message(
        message, "<i>Are you really sure you want to restart the bot ?</i>", button
    )


@new_task
async def restart_sessions(_, message):
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", "sessionrestart confirm")
    buttons.data_button("No!", "sessionrestart cancel")
    button = buttons.build_menu(2)
    await send_message(
        message,
        "<i>Are you really sure you want to restart the session(s) ?!</>",
        button,
    )

async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    now = datetime.now(timezone("Asia/Kolkata"))

    if await aiopath.isfile(".restartmsg"):
        try:
            await TgClient.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"""⌬ <b><i>Restarted Successfully!</i></b>
┟ <b>Date:</b> {now.strftime("%d/%m/%y")}
┠ <b>Time:</b> {now.strftime("%I:%M:%S %p")}
┠ <b>TimeZone:</b> Asia/Kolkata
┖ <b>Version:</b> {get_version()}""",
            )
        except Exception as e:
            LOGGER.error(e)
        await remove(".restartmsg")
        
@new_task
async def confirm_restart(_, query):
    await query.answer()
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    await delete_message(message)
    if data[1] == "confirm":
        intervals["stopAll"] = True
        restart_message = await send_message(reply_to, "<i>Restarting...</i>")
        await delete_message(message)
        await TgClient.stop()
        if scheduler.running:
            scheduler.shutdown(wait=False)
        if st := intervals["status"]:
            for intvl in list(st.values()):
                intvl.cancel()
        await clean_all()
        proc1 = await create_subprocess_exec(
            "pkill",
            "-9",
            "-f",
            f"gunicorn|{BinConfig.FFMPEG_NAME}|7z|split",
        )
        proc2 = await create_subprocess_exec("python3", "update.py")
        await gather(proc1.wait(), proc2.wait())
        async with aiopen(".restartmsg", "w") as f:
            await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
        osexecl(executable, executable, "-m", "bot")
    else:
        await delete_message(message, reply_to)
