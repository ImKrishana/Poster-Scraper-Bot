from asyncio import sleep, gather
from re import match as re_match
from time import time

from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import (
    FloodWait,
    MessageNotModified,
    MessageEmpty,
    ReplyMarkupInvalid,
    PhotoInvalidDimensions,
    WebpageCurlFailed,
    MediaEmpty,
    MediaCaptionTooLong,
    EntityBoundsInvalid,
)

try:
    from pyrogram.errors import FloodPremiumWait
except ImportError:
    FloodPremiumWait = FloodWait

from ... import LOGGER, intervals
from ...core.config_manager import Config
from ...core.tg_client import TgClient
from ..ext_utils.bot_utils import SetInterval
from ..ext_utils.exceptions import TgLinkException
import random

STICKERS = [
    "CAACAgUAAxkBAAEQzC9pvtLHw56fQ9iJ_bF_J6McnnsPNAACQR0AAuxcmFUirgsGQ7bX2zoE",
    "CAACAgIAAxkBAAEPXchoxaqjIeZPTNBNy92zlKmfnEqgwAACLg8AAs28SUl9CNyuoTnGkzYE",
    "CAACAgUAAxkBAAEQzKxpv81c8d2KWh_xJUEUFs0lfoMw5QACBQ8AAluo4VVQqtbqZmibAzoE",
    "CAACAgUAAxkBAAEQzK5pv81fNLscl68tx_EcU66NfTwRQQACdQ4AAvsZ6VVQw768KGEZoDoE",
    "CAACAgUAAxkBAAEQzLBpv81iub2HV_PUtaJV__0j75vgqwACGR0AAm4H6VUOFUeACbFJXzoE",
    "CAACAgUAAxkBAAEQzLJpv81qHGR9wBHaEQNdV5WtyARoGwAC8A4AAqsCAVexoakLWE8JKDoE",
    "CAACAgUAAxkBAAEQzLRpv81vEeP-De_6cTlpuBQZwrwhxAAC6A4AAlvtOVe1sgu1BTTEqToE",
    "CAACAgUAAxkBAAEQzLZpv813UxNu8z9lXrXxVqIG57xMYAACJQ8AAhuraVTy0E2u4E6gbDoE",
    "CAACAgUAAxkBAAEQzLhpv82HT_kZO53ZtDojBhPrsEjUBwACqBIAAu8e-VRfJVeoE-7VFjoE",
    "CAACAgUAAxkBAAEQzLppv82MgheCWtvwM-AQgmKi2YZtAQACrA8AAt5geFXy7DsVAlmTZToE",
    "CAACAgUAAxkBAAEQzLxpv82y32ni_w_2Knks5YZutVqh6wACZRYAAluoWFWIpxeikmDBKDoE",
    "CAACAgUAAxkBAAEQzL5pv83I-CoEGyPe2_GPO2NDc1Kb7wAC3xMAArINWVW3XLNlsu9-3DoE",
    "CAACAgUAAxkBAAEQzMBpv83KP6qLLFX2pM7c3460uqtIzwACARcAAuF6CFauI2BHVHa9ZjoE",
    "CAACAgQAAxkBAAEQzMJpv83ZkqJX9NHXJFtWigNFo8aajgACPxgAAqbxcR4lSV03aK6BaToE",
    "CAACAgQAAxkBAAEQzMRpv83gQFYHBf4G4vBUwUkL1J2gSAACkRgAAqbxcR7GB8r-c9UGkDoE",
    "CAACAgUAAxkBAAEQzMZpv850WPH8K6n7Gbes4Z8bRC2C1wACJxEAAvPWIVbSNHeRTtyzAzoE",
    "CAACAgUAAxkBAAEQzMhpv853XR6C2GdACNWm97vTGsu3CAACFRMAAoIFIFaIUyRyII07AjoE",
    "CAACAgUAAxkBAAEQzMppv8549u_XfEJ_9YSy8_flFoB1aQAC5BMAAheuKVazuvUqXP_fuToE",
    "CAACAgUAAxkBAAEQzMxpv858YpfWEG42HFXWJgaw1fwljAACzBQAAgy3IVbAx2sz_tzURDoE",
    "CAACAgUAAxkBAAEQzNBpv86SfvKsbCKD4aYvrdQsld2YoQAC-BUAAudbKFYJ-Qonb6Ny2ToE",
    "CAACAgUAAxkBAAEQzNJpv86Wulo8nkxcJqt7aHiXeU5p8AACaRMAAoX5KVbWIetd2mKFkDoE",
    "CAACAgUAAxkBAAEQzNRpv86iUj4DRsvNKfOK5HtWkiT27gACaBIAAodTaVZax1YbK6C5AToE",
    "CAACAgUAAxkBAAEQzNZpv86kgX3WKeSd9d-W7PA7p1YP6QACJxIAAmT7aVaHLy0fcWr6NzoE",
    "CAACAgUAAxkBAAEQzNhpv86kEh9sy0M9PsyIXZ2u9_X0ZgACDRIAAjv1aVZZ1el0UuLfBToE",
    "CAACAgUAAxkBAAEQzNppv86yez9N31neAlgy2LJh9ZcNTAACNRQAArYsGVfRZcF6FpllWjoE",
    "CAACAgUAAxkBAAEQzNxpv8610Wkp5Ct7j7YZ6oE03sFH-gACUxYAAgfZ0VStVK44p150HDoE"
]

async def send_message(message, text, buttons=None, block=True, photo=None, **kwargs):
    try:
        if photo:
            try:
                if isinstance(message, int):
                    return await TgClient.bot.send_photo(
                        chat_id=message,
                        photo=photo,
                        caption=text,
                        reply_markup=buttons,
                        disable_notification=True,
                        **kwargs,
                    )
                return await message.reply_photo(
                    photo=photo,
                    reply_to_message_id=message.id,
                    caption=text,
                    quote=True,
                    reply_markup=buttons,
                    disable_notification=True,
                    **kwargs,
                )
            except FloodWait as f:
                LOGGER.warning(str(f))
                if not block:
                    return str(f)
                await sleep(f.value * 1.2)
                return await send_message(message, text, buttons, block, photo)
            except MediaCaptionTooLong:
                return await send_message(
                    message,
                    text[:1024],
                    buttons,
                    block,
                    photo,
                )
            except (PhotoInvalidDimensions, WebpageCurlFailed, MediaEmpty):
                LOGGER.error("Invalid photo dimensions or empty media", exc_info=True)
                return
            except Exception:
                LOGGER.error("Error while sending photo", exc_info=True)
                return
        if isinstance(message, int):
            return await TgClient.bot.send_message(
                chat_id=message,
                text=text,
                disable_web_page_preview=True,
                disable_notification=True,
                reply_markup=buttons,
            )
        return await message.reply(
            text=text,
            quote=True,
            disable_web_page_preview=True,
            disable_notification=True,
            reply_markup=buttons,
            **kwargs,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        if not block:
            return str(f)
        await sleep(f.value * 1.2)
        return await send_message(message, text, buttons)
    except ReplyMarkupInvalid as rmi:
        LOGGER.warning(str(rmi))
        return await send_message(message, text, None)
    except (MessageEmpty, EntityBoundsInvalid):
        return await send_message(message, text, parse_mode=ParseMode.DISABLED)
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return str(e)


async def edit_message(message, text, buttons=None, block=True):
    try:
        return await message.edit(
            text=text,
            disable_web_page_preview=True,
            reply_markup=buttons,
        )
    except (MessageNotModified, MessageEmpty):
        pass
    except ReplyMarkupInvalid as rmi:
        LOGGER.warning(str(rmi))
        return await edit_message(message, text, None)
    except FloodWait as f:
        LOGGER.warning(str(f))
        if not block:
            return str(f)
        await sleep(f.value * 1.2)
        return await edit_message(message, text, buttons)
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return str(e)


async def edit_reply_markup(message, buttons):
    try:
        return await message.edit_reply_markup(reply_markup=buttons)
    except MessageNotModified:
        pass
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await edit_reply_markup(message, buttons)
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return str(e)


async def send_file(message, file, caption="", buttons=None):
    try:
        return await message.reply_document(
            document=file,
            quote=True,
            caption=caption,
            disable_notification=True,
            reply_markup=buttons,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await send_file(message, file, caption)
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return str(e)

async def delete_message(*args):
    tasks = [msg.delete() for msg in args if isinstance(msg, Message)]
    if not tasks:
        return
    results = await gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            LOGGER.error(result)


async def auto_delete_message(*args, stime=90):
    await sleep(stime)
    await delete_message(*args)

async def send_sticker(message, sticker_id=None):
    sticker = sticker_id if sticker_id else random.choice(STICKERS)
    return await message.reply_sticker(sticker, quote=True)
