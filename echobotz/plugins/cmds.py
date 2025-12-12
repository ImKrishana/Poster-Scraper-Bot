from time import monotonic
from pyrogram.enums import ChatType

from .. import LOGGER
from ..eco import echo
from ..helper.utils.btns import EchoButtons
from ..helper.utils.msg_util import send_message, edit_message
from ..helper.utils.db import database
from ..helper.utils.xtra import _task

@_task
async def _strt(client, message):
    try:
        if message.chat.type == ChatType.PRIVATE:
            user = message.from_user or message.sender_chat
            if user:
                await database._set_pm_user(user.id)
        btns = (
            EchoButtons()
            .url_button(echo.UP_BTN, echo.UPDTE)
            .url_button(echo.SP_BTN, echo.SP_GR)
            .url_button(echo.ST_BTN, echo.REPO)
            .build(2)
        )
        await send_message(
            message,
            echo.ABC,
            buttons=btns,
            photo=echo.IMG,
            has_spoiler=True,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        LOGGER.error(str(e))

@_task      
async def _ping(client, message):
    try:
        start_time = monotonic()
        reply = await send_message(message, "<i>Starting Ping..</i>")
        end_time = monotonic()
        await edit_message(
            reply,
            f"<i>Pong!</i>\n<code>{int((end_time - start_time) * 1000)} ms</code>",
        )
    except Exception as e:
        LOGGER.error(str(e))
