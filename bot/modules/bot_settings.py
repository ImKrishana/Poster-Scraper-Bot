from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    sleep,
)
from functools import partial
from io import BytesIO
from os import getcwd
from time import time

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from aioshutil import rmtree
from pyrogram.filters import create
from pyrogram.handlers import MessageHandler

from .. import (
    LOGGER,
    cpu_eater_lock,
    shortener_dict,
    auth_chats,
    sudo_users,
)
from ..helper.ext_utils.bot_utils import (
    new_task,
)
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..core.startup import update_variables
from ..helper.ext_utils.db_handler import database
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_file,
    send_message,
)

start = 0
state = "view"
handler_dict = {}
DEFAULT_VALUES = {
    "LEECH_SPLIT_SIZE": TgClient.MAX_SPLIT_SIZE,
    "UPSTREAM_BRANCH": "master",
    "CONCURRENT_CPU_TASKS": 1,
}


async def get_buttons(key=None, edit_type=None, edit_mode=False):
    buttons = ButtonMaker()
    if key is None:
        buttons.data_button("Config Variables", "botset var")
        buttons.data_button("Private Files", "botset private open")
        buttons.data_button("Close", "botset close")
        msg = "Bot Settings:"
    elif edit_type is not None:
        if edit_type == "botvar":
            msg = ""
            buttons.data_button("Back", "botset var")
            if key not in ["TELEGRAM_HASH", "TELEGRAM_API", "OWNER_ID", "BOT_TOKEN"]:
                buttons.data_button("Default", f"botset resetvar {key}")
            buttons.data_button("Close", "botset close")
            if key in [
                "CMD_SUFFIX",
                "OWNER_ID",
                "USER_SESSION_STRING",
                "TELEGRAM_HASH",
                "TELEGRAM_API",
                "BOT_TOKEN",
                "TG_PROXY",
            ]:
                msg += "Restart required for this edit to take effect! You will not see the changes in bot vars, the edit will be in database only!\n\n"
            msg += f"Send a valid value for {key}. Current value is '{Config.get(key)}'. Timeout: 60 sec"
    elif key == "var":
        conf_dict = Config.get_all()
        for k in list(conf_dict.keys())[start : 10 + start]:
            if k == "DATABASE_URL" and state != "view":
                continue
            buttons.data_button(k, f"botset botvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit var")
        else:
            buttons.data_button("View", "botset view var")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(conf_dict), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start var {x}", position="footer"
            )
        msg = f"Config Variables | Page: {int(start / 10)} | State: {state}"
    elif key == "private":
        if edit_mode:
            buttons.data_button("Stop Invoke File", "botset private stop", "header")
        else:
            buttons.data_button("Create New File", "botset private new")
            buttons.data_button("Add/Delete File", "botset private edit")
        buttons.data_button("Back", "botset back", position="footer")
        buttons.data_button("Close", "botset close", position="footer")
        txt = "\n┠ ".join(
            [
                f"<code>{fn}</code> → <b>{'Exists' if await aiopath.isfile(fn) else 'Not Exists'}</b>"
                for fn in [
                    "config.py",
                    "shortener.txt",
                    ".netrc",
                ]
            ]
        )
        msg = f"""⌬ <b>Private File Settings</b>
┠ <b>Dashboard :</b> 
┃
┠ {txt}
┃
┠ <b>Delete File</b> → Send the file name as text message, Like <code>rclone.conf</code>.
┃
┖ <b>Note:</b> Changing .netrc will not take effect for aria2c until restart."""
        if edit_mode:
            msg += "\n\n<i>Send the file name to delete the file, file to save the file & for new file create, follow below format.</i> \n\n<b>Format:</b> \nfile_name\n\ncontents of file</i>\n\n<b>Time Left :</b> <code>60 sec</code>"

    return msg, buttons.build_menu(1 if key is None else 2)


async def update_buttons(message, key=None, edit_type=None, edit_mode=False):
    msg, button = await get_buttons(key, edit_type, edit_mode)
    await edit_message(message, msg, button)


@new_task
async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif key == "LEECH_SPLIT_SIZE":
        value = min(int(value), TgClient.MAX_SPLIT_SIZE)
    elif key == "CONCURRENT_CPU_TASKS":
        value = int(value)
        cpu_eater_lock.update_limit(value)
    elif key == "BASE_URL_PORT":
        value = int(value)
        if Config.BASE_URL:
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
            await create_subprocess_shell(
                f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{value}"
            )
    elif key == "AUTHORIZED_CHATS":
        aid = value.split()
        auth_chats.clear()
        for id_ in aid:
            chat_id, *thread_ids = id_.split("|")
            chat_id = int(chat_id.strip())
            if thread_ids:
                thread_ids = list(map(lambda x: int(x.strip()), thread_ids))
                auth_chats[chat_id] = thread_ids
            else:
                auth_chats[chat_id] = []
    elif key == "SUDO_USERS":
        sudo_users.clear()
        aid = value.split()
        for id_ in aid:
            sudo_users.append(int(id_.strip()))
    elif value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        value = eval(value)
    elif value.startswith("{") and value.endswith("}"):
        value = eval(value)
    Config.set(key, value)
    await update_buttons(pre_message, "var")
    await delete_message(message)
    await database.update_config({key: value})


@new_task
async def update_private_file(_, message, pre_message, key, new_file=False):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        if new_file:
            file_name, content = file_name.split("\n", 1)
            file_name = file_name.strip()
            async with aiopen(file_name, "w") as f:
                await f.write(content.strip())
        else:
            if await aiopath.isfile(file_name) and file_name != "config.py":
                await remove(file_name)
            if file_name in [".netrc", "netrc"]:
                await (await create_subprocess_exec("touch", ".netrc")).wait()
                await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
                await (
                    await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
                ).wait()
        await delete_message(message)
    elif doc := message.document:
        file_name = doc.file_name
        fpath = f"{getcwd()}/{file_name}"
        if await aiopath.exists(fpath):
            await remove(fpath)
        await message.download(file_name=fpath)
        if file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == "config.py":
            await load_config()
        if "@github.com" in Config.UPSTREAM_REPO:
            buttons = ButtonMaker()
            msg = "Push to UPSTREAM_REPO ?"
            buttons.data_button("Yes!", f"botset push {file_name}")
            buttons.data_button("No", "botset close")
            await send_message(message, msg, buttons.build_menu(2))
        else:
            await delete_message(message)
    if file_name == "shortener.txt" and await aiopath.exists("shortener.txt"):
        async with aiopen("shortener.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    shortener_dict[temp[0]] = temp[1]
    await update_buttons(pre_message, key)
    await database.update_private_file(file_name)


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = update_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user.id == query.from_user.id
            and event.chat.id == chat_id
            and (event.text or event.document and document)
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[chat_id]:
        await sleep(0.5)

        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
        elif document:
            if time() - update_time > 6 and handler_dict[chat_id]:
                update_time = time()
                msg = await client.get_messages(chat_id, query.message.id)
                text = msg.text.split("\n")
                text[-1] = (
                    f"<b>Time Left :</b> <code>{round(60 - (time() - start_time), 2)} sec</code>"
                )
                await edit_message(msg, "\n".join(text), msg.reply_markup)
    client.remove_handler(*handler)


@new_task
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    handler_dict[message.chat.id] = False
    if data[1] == "close":
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)
    elif data[1] == "back":
        await query.answer()
        globals()["start"] = 0
        await update_buttons(message, None)
    elif data[1] == "var":
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        await query.answer()
        value = ""
        if data[2] in DEFAULT_VALUES:
            value = DEFAULT_VALUES[data[2]]
        elif data[2] == "BASE_URL":
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
        elif data[2] == "BASE_URL_PORT":
            value = 80
            if Config.BASE_URL:
                await (
                    await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
                ).wait()
                await create_subprocess_shell(
                    f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{value}"
                )
        elif data[2] == "AUTHORIZED_CHATS":
            auth_chats.clear()
        elif data[2] == "SUDO_USERS":
            sudo_users.clear()
        Config.set(data[2], value)
        await update_buttons(message, "var")
        if data[2] == "DATABASE_URL":
            await database.disconnect()
        await database.update_config({data[2]: value})
    elif data[1] == "private":
        await query.answer()
        if data[2] in ("open", "stop"):
            await update_buttons(message, data[1])
        elif data[2] in ("edit", "new"):
            await update_buttons(message, data[1], edit_mode=True)
            pfunc = partial(
                update_private_file,
                pre_message=message,
                key=data[1],
                new_file=data[2] == "new",
            )
            rfunc = partial(update_buttons, message, data[1])
            await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == "botvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_variable, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "var")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "botvar" and state == "view":
        OWNER_ONLY_KEYS = {
            "BOT_TOKEN",
            "DATABASE_URL",
            "HELPER_TOKENS",
            "TELEGRAM_HASH",
            "TELEGRAM_API",
            "UPSTREAM_BRANCH",
            "UPSTREAM_REPO",
            "USER_SESSION_STRING",
        }
        if data[2] in OWNER_ONLY_KEYS and query.from_user.id != Config.OWNER_ID:
            await query.answer("⛔ Only the owner can view this setting.", show_alert=True)
            return
        value = f"{Config.get(data[2])}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "edit":
        await query.answer()
        globals()["state"] = "edit"
        await update_buttons(message, data[2])
    elif data[1] == "view":
        await query.answer()
        globals()["state"] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        if start != int(data[3]):
            globals()["start"] = int(data[3])
            await update_buttons(message, data[2])
    elif data[1] == "push":
        await query.answer()
        filename = data[2].rsplit(".zip", 1)[0]
        if await aiopath.exists(filename):
            await (
                await create_subprocess_shell(
                    f"git add -f {filename} \
                    && git commit -sm botsettings -q \
                    && git push origin {Config.UPSTREAM_BRANCH} -qf"
                )
            ).wait()
        else:
            await (
                await create_subprocess_shell(
                    f"git rm -r --cached {filename} \
                    && git commit -sm botsettings -q \
                    && git push origin {Config.UPSTREAM_BRANCH} -qf"
                )
            ).wait()
        await delete_message(message.reply_to_message)
        await delete_message(message)


@new_task
async def send_bot_settings(_, message):
    handler_dict[message.chat.id] = False
    msg, button = await get_buttons()
    globals()["start"] = 0
    await send_message(message, msg, button)


async def load_config():
    Config.load()
    cpu_eater_lock.update_limit(Config.CONCURRENT_CPU_TASKS)
    await update_variables()

    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    if Config.BASE_URL:
        await create_subprocess_shell(
            f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{Config.BASE_URL_PORT}"
        )

    if Config.DATABASE_URL:
        await database.connect()
        config_dict = Config.get_all()
        await database.update_config(config_dict)
    else:
        await database.disconnect()
