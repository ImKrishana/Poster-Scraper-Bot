from ast import literal_eval
from pyrogram import Client, enums
from pyrogram.errors import FloodWait
from asyncio import Lock, gather, sleep
from hashlib import sha256
from inspect import signature

from .. import LOGGER, bot_loop
from .config_manager import Config

_DB_PARTITION_SALT = b"wzmlx_v3_db_partition_salt"


def db_partition_id(bot_id):
    raw = sha256(_DB_PARTITION_SALT + str(bot_id).encode("utf-8")).hexdigest()
    return f"p_{raw[:24]}"


class TgClient:
    _lock = Lock()

    bot = None
    user = None

    BNAME = ""
    ID = 0
    PARTITION = ""
    IS_PREMIUM_USER = False
    MAX_SPLIT_SIZE = 2097152000

    @classmethod
    def wztgClient(cls, *args, proxy=None, **kwargs):
        kwargs["api_id"] = Config.TELEGRAM_API
        kwargs["api_hash"] = Config.TELEGRAM_HASH
        kwargs["proxy"] = (Config.TG_PROXY if proxy is None else proxy) or None
        kwargs["parse_mode"] = enums.ParseMode.HTML
        kwargs["in_memory"] = True
        for param, value in {
            "max_concurrent_transmissions": 100,
            "skip_updates": False,
        }.items():
            if param in signature(Client.__init__).parameters:
                kwargs[param] = value
        return Client(*args, **kwargs)

    @classmethod
    def _parse_proxies(cls, raw):
        if not raw:
            return []
        proxies = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                proxies.append(None)
                continue
            try:
                parsed = literal_eval(line)
                proxies.append(parsed if isinstance(parsed, dict) else None)
            except (ValueError, SyntaxError):
                proxies.append(None)
        return proxies

    @classmethod
    async def start_bot(cls):
        LOGGER.info("Generating client from BOT_TOKEN")
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        cls.PARTITION = db_partition_id(cls.ID)
        cls.bot = cls.wztgClient(
            f"zake-Bot{cls.ID}",
            bot_token=Config.BOT_TOKEN,
            workdir="/usr/src/app",
        )
        while True:
            try:
                await cls.bot.start()
                break
            except FloodWait as e:
                LOGGER.warning(f"FloodWait: Sleeping for {e.value} seconds...")
                await sleep(e.value)
        cls.BNAME = cls.bot.me.username
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        LOGGER.info(f"zake Bot : [@{cls.BNAME}] Started!")

    @classmethod
    async def _retry_user(cls, delay):
        await sleep(delay)
        try:
            cls.user = cls.wztgClient(
                "zake-User",
                session_string=Config.USER_SESSION_STRING,
                sleep_threshold=60,
                no_updates=True,
            )
            await cls.user.start()
            cls.IS_PREMIUM_USER = cls.user.me.is_premium
            if cls.IS_PREMIUM_USER:
                cls.MAX_SPLIT_SIZE = 4194304000
            uname = cls.user.me.username or cls.user.me.first_name
            LOGGER.info(f"zake User : [{uname}] Started!")
        except FloodWait as e:
            LOGGER.warning(f"User client FloodWait: Retrying in {e.value}s...")
            bot_loop.create_task(cls._retry_user(e.value))
        except Exception as e:
            LOGGER.error(f"Failed to start client from USER_SESSION_STRING. {e}")
            cls.IS_PREMIUM_USER = False
            cls.MAX_SPLIT_SIZE = 2097152000
            cls.user = None

    @classmethod
    async def start_user(cls):
        if Config.USER_SESSION_STRING:
            LOGGER.info("Generating client from USER_SESSION_STRING")
            try:
                cls.user = cls.wztgClient(
                    "zake-User",
                    session_string=Config.USER_SESSION_STRING,
                    sleep_threshold=60,
                    no_updates=True,
                )
                await cls.user.start()
                cls.IS_PREMIUM_USER = cls.user.me.is_premium
                if cls.IS_PREMIUM_USER:
                    cls.MAX_SPLIT_SIZE = 4194304000
                uname = cls.user.me.username or cls.user.me.first_name
                LOGGER.info(f"zake User : [{uname}] Started!")
            except FloodWait as e:
                LOGGER.warning(
                    f"User client FloodWait: Retrying in {e.value}s (non-blocking)..."
                )
                bot_loop.create_task(cls._retry_user(e.value))
            except Exception as e:
                LOGGER.error(f"Failed to start client from USER_SESSION_STRING. {e}")
                cls.IS_PREMIUM_USER = False
                cls.MAX_SPLIT_SIZE = 2097152000
                cls.user = None

    @classmethod
    async def stop(cls):
        async with cls._lock:
            clients = []
            if cls.bot:
                clients.append(cls.bot.stop())
                cls.bot = None
            if cls.user:
                clients.append(cls.user.stop())
                cls.user = None
            if clients:
                await gather(*clients, return_exceptions=True)
            LOGGER.info("All Client(s) stopped")

    @classmethod
    async def reload(cls):
        async with cls._lock:
            await cls.bot.restart()
            if cls.user:
                await cls.user.restart()
            LOGGER.info("All Client(s) restarted")
