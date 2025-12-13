from pyrogram import Client
from pyrogram.enums import ParseMode
from asyncio import Lock
from logging import getLogger
from config import Config

LOGGER = getLogger(__name__)


class EchoClient:
    _lock = Lock()

    bot: Client | None = None
    ID = 0
    USERNAME = ""

    @classmethod
    async def start_bot(cls):
        async with cls._lock:
            LOGGER.info("Starting Echo bot client")
            cls.bot = Client(
                "EchoBotz",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=Config.BOT_TOKEN,
                workers=100,
                parse_mode=ParseMode.HTML,
            )
            await cls.bot.start()
            me = cls.bot.me
            cls.ID = me.id
            cls.USERNAME = me.username
            LOGGER.info(f"Echo Bot Started as @{cls.USERNAME}")

    @classmethod
    async def stop(cls):
        async with cls._lock:
            if cls.bot:
                await cls.bot.stop()
                cls.bot = None
                LOGGER.info("Echo Bot stopped")
