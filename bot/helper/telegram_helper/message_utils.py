from asyncio import sleep, gather
from random import choice

from pyrogram.types import (
    Message,
    InputMediaPhoto,
    LinkPreviewOptions,
    ReplyParameters,
)
from pyrogram.enums import ParseMode
from pyrogram.errors import (
    FloodWait,
    MessageNotModified,
    MessageEmpty,
    MessageTooLong,
    MessageDeleteForbidden,
    ReplyMarkupInvalid,
    PhotoInvalidDimensions,
    WebpageCurlFailed,
    WebpageMediaEmpty,
    MediaEmpty,
    MediaCaptionTooLong,
    EntityBoundsInvalid,
    PeerIdInvalid,
)

from ... import LOGGER
from ...core.config_manager import Config
from ...core.tg_client import TgClient
from ..ext_utils.bot_utils import download_image_url

async def send_message(message, text, buttons=None, block=True, photo=None, **kwargs):
    try:
        if photo:
            try:
                if photo == "IMAGES":
                    if Config.USE_IMAGES and Config.IMAGES:
                        photo = choice(Config.IMAGES)
                    else:
                        photo = None
                if photo is None:
                    if isinstance(message, Message):
                        return await message.reply(
                            text=text,
                            reply_parameters=ReplyParameters(message_id=message.id),
                            link_preview_options=LinkPreviewOptions(is_disabled=True),
                            disable_notification=True,
                            reply_markup=buttons,
                            **kwargs,
                        )
                    return await TgClient.bot.send_message(
                        chat_id=message,
                        text=text,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                        disable_notification=True,
                        reply_markup=buttons,
                    )
                if isinstance(message, Message):
                    return await message.reply_photo(
                        photo=photo,
                        caption=text,
                        reply_parameters=ReplyParameters(message_id=message.id),
                        reply_markup=buttons,
                        disable_notification=True,
                        **kwargs,
                    )
                return await TgClient.bot.send_photo(
                    chat_id=message,
                    photo=photo,
                    caption=text,
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
            except (
                PhotoInvalidDimensions,
                WebpageCurlFailed,
                WebpageMediaEmpty,
                MediaEmpty,
            ):
                try:
                    des_dir = await download_image_url(photo)
                    if des_dir:
                        msg = await send_message(message, text, buttons, block, des_dir)
                        from aiofiles.os import remove as aioremove

                        await aioremove(des_dir)
                        return msg
                except Exception:
                    LOGGER.error("Failed to send fallback photo", exc_info=True)
                return
            except Exception:
                LOGGER.error("Error while sending photo", exc_info=True)
                return
        if isinstance(message, Message):
            return await message.reply(
                text=text,
                reply_parameters=ReplyParameters(message_id=message.id),
                link_preview_options=LinkPreviewOptions(is_disabled=True),
                disable_notification=True,
                reply_markup=buttons,
                **kwargs,
            )
        return await TgClient.bot.send_message(
            chat_id=int(message),
            text=text,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
            disable_notification=True,
            reply_markup=buttons,
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
    except MessageTooLong:
        return await send_message(message, text[:4096], buttons, block, photo)
    except (MessageEmpty, EntityBoundsInvalid):
        return await send_message(message, text, parse_mode=ParseMode.DISABLED)
    except PeerIdInvalid:
        LOGGER.warning(f"PeerIdInvalid {type(message)}")  # My Debug Style
        if isinstance(message, (int, str)):
            return await send_message(int(message), text, buttons, block, photo)
    except ConnectionError:
        return
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return str(e)


async def edit_message(message, text, buttons=None, block=True, photo=None):
    try:
        if not isinstance(text, str):
            return await TgClient.bot.edit_message_text(
                message.chat.id,
                message.id,
                "",
                rich_text=text,
                reply_markup=buttons,
            )
        if message.media:
            if photo:
                if photo == "IMAGES":
                    if Config.USE_IMAGES and Config.IMAGES:
                        photo = choice(Config.IMAGES)
                    else:
                        photo = None
                if photo:
                    try:
                        return await message.edit_media(
                            InputMediaPhoto(photo, text), reply_markup=buttons
                        )
                    except (
                        PhotoInvalidDimensions,
                        WebpageCurlFailed,
                        WebpageMediaEmpty,
                        MediaEmpty,
                    ):
                        des_dir = await download_image_url(photo)
                        if des_dir:
                            msg = await message.edit_media(
                                InputMediaPhoto(des_dir, text), reply_markup=buttons
                            )
                            from aiofiles.os import remove as aioremove

                            await aioremove(des_dir)
                            return msg
                        return await message.edit_caption(
                            caption=text, reply_markup=buttons
                        )
            return await message.edit_caption(caption=text, reply_markup=buttons)
        return await message.edit(
            text=text,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
            reply_markup=buttons,
        )
    except (MessageNotModified, MessageEmpty):
        pass
    except ReplyMarkupInvalid as rmi:
        LOGGER.warning(str(rmi))
        return await edit_message(message, text, None, block, photo)
    except FloodWait as f:
        LOGGER.warning(str(f))
        if not block:
            return str(f)
        await sleep(f.value * 1.2)
        return await edit_message(message, text, buttons, block, photo)
    except OSError:
        return
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
    except OSError:
        return
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return str(e)


async def send_file(message, file, caption="", buttons=None):
    try:
        return await message.reply_document(
            document=file,
            reply_parameters=ReplyParameters(message_id=message.id),
            caption=caption,
            disable_notification=True,
            reply_markup=buttons,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await send_file(message, file, caption)
    except ConnectionError:
        return
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return str(e)

async def delete_message(*args):
    tasks = [msg.delete() for msg in args if isinstance(msg, Message)]
    if not tasks:
        return
    results = await gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, MessageDeleteForbidden):
            pass
        elif isinstance(result, Exception):
            LOGGER.error(result)


async def auto_delete_message(*args, stime=90):
    await sleep(stime)
    await delete_message(*args)
