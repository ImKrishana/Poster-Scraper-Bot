from asyncio import create_subprocess_exec, create_subprocess_shell, sleep
from importlib import import_module
from os import environ, getenv, path as ospath

from aiofiles import open as aiopen
from aiofiles.os import makedirs, remove, path as aiopath
from aioshutil import rmtree

from .. import (
    LOGGER,
    cpu_eater_lock,
    auth_chats,
    shortener_dict,
    var_list,
    user_data,
    sudo_users,
)
from ..helper.ext_utils.db_handler import database
from .config_manager import Config
from .tg_client import TgClient

async def load_settings():
    if not Config.DATABASE_URL:
        return

    await database.connect()

    if database.db is not None:
        BOT_ID = Config.BOT_TOKEN.split(":", 1)[0]

        try:
            settings = import_module("config")
            config_file = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in vars(settings).items()
                if not key.startswith("__")
            }
        except ModuleNotFoundError:
            config_file = {}

        config_file.update(
            {
                key: value.strip() if isinstance(value, str) else value
                for key, value in environ.items()
                if key in var_list
            }
        )

        old_config = await database.db.settings.deployConfig.find_one(
            {"_id": BOT_ID}, {"_id": 0}
        )

        if old_config is None:
            await database.db.settings.deployConfig.replace_one(
                {"_id": BOT_ID}, config_file, upsert=True
            )

        if old_config and old_config != config_file:
            LOGGER.info("Saving.. Deploy Config imported from Bot")
            await database.db.settings.deployConfig.replace_one(
                {"_id": BOT_ID}, config_file, upsert=True
            )

            config_dict = (
                await database.db.settings.config.find_one(
                    {"_id": BOT_ID}, {"_id": 0}
                )
                or {}
            )

            config_dict.update(config_file)

            if config_dict:
                Config.load_dict(config_dict)
        else:
            LOGGER.info("Updating.. Saved Config imported from MongoDB")

            config_dict = await database.db.settings.config.find_one(
                {"_id": BOT_ID}, {"_id": 0}
            )

            if config_dict:
                Config.load_dict(config_dict)

        if pf_dict := await database.db.settings.files.find_one(
            {"_id": BOT_ID}, {"_id": 0}
        ):
            for key, value in pf_dict.items():
                if value:
                    file_ = key.replace("__", ".")
                    async with aiopen(file_, "wb+") as f:
                        await f.write(value)

        if await database.db.users[BOT_ID].find_one():
            rows = database.db.users[BOT_ID].find({})

            async for row in rows:
                uid = row["_id"]
                del row["_id"]
                user_data[uid] = row

            LOGGER.info("Users Data has been imported from MongoDB")
            
async def save_settings():
    if database.db is None:
        return

    config_file = Config.get_all()

    await database.db.settings.config.update_one(
        {"_id": TgClient.ID},
        {"$set": config_file},
        upsert=True,
    )


async def update_variables():
    cpu_eater_lock.update_limit(Config.CONCURRENT_CPU_TASKS)

    if (
        Config.LEECH_SPLIT_SIZE > TgClient.MAX_SPLIT_SIZE
        or Config.LEECH_SPLIT_SIZE == 2097152000
        or not Config.LEECH_SPLIT_SIZE
    ):
        Config.LEECH_SPLIT_SIZE = TgClient.MAX_SPLIT_SIZE

    Config.HYBRID_LEECH = bool(Config.HYBRID_LEECH and TgClient.IS_PREMIUM_USER)
    Config.USER_TRANSMISSION = bool(
        Config.USER_TRANSMISSION and TgClient.IS_PREMIUM_USER
    )

    if Config.AUTHORIZED_CHATS:
        aid = Config.AUTHORIZED_CHATS.split()
        for id_ in aid:
            chat_id, *thread_ids = id_.split("|")
            chat_id = int(chat_id.strip())
            if thread_ids:
                thread_ids = list(map(lambda x: int(x.strip()), thread_ids))
                auth_chats[chat_id] = thread_ids
            else:
                auth_chats[chat_id] = []

    if Config.SUDO_USERS:
        aid = Config.SUDO_USERS.split()
        for id_ in aid:
            sudo_users.append(int(id_.strip()))

    if await aiopath.exists("shortener.txt"):
        async with aiopen("shortener.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    shortener_dict[temp[0]] = temp[1]

async def load_configurations():
    PORT = getenv("PORT", "") or Config.BASE_URL_PORT

    if PORT:
        await create_subprocess_shell(
            f"gunicorn -k uvicorn.workers.UvicornWorker "
            f"-w 1 web.wserver:app --bind 0.0.0.0:{PORT}"
        )
