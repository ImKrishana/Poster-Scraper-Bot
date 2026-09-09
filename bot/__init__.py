# ruff: noqa: E402

from uvloop import install

install()

from subprocess import run as srun
from os import getcwd
from asyncio import Lock, Semaphore, new_event_loop, set_event_loop
from contextvars import ContextVar
from logging import (
    ERROR,
    INFO,
    WARNING,
    FileHandler,
    StreamHandler,
    basicConfig,
    getLogger,
)
from os import cpu_count
from time import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler

getLogger("requests").setLevel(WARNING)
getLogger("urllib3").setLevel(WARNING)
getLogger("pyrogram").setLevel(ERROR)
getLogger("aiohttp").setLevel(ERROR)
getLogger("apscheduler").setLevel(ERROR)
getLogger("httpx").setLevel(WARNING)
getLogger("pymongo").setLevel(WARNING)
getLogger("aiohttp").setLevel(WARNING)


bot_start_time = time()

bot_loop = new_event_loop()
set_event_loop(bot_loop)

basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",  #  [%(filename)s:%(lineno)d]
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)

LOGGER = getLogger(__name__)
cpu_no = cpu_count()
threads = max(1, cpu_no // 2)
cores = ",".join(str(i) for i in range(threads))

bot_cache = {}
DOWNLOAD_DIR = "/usr/src/app/downloads/"
intervals = {"status": {}, "stopAll": False}
user_data = {}
shortener_dict = {}
var_list = [
    "BOT_TOKEN",
    "TELEGRAM_API",
    "TELEGRAM_HASH",
    "OWNER_ID",
    "DATABASE_URL",
    "BASE_URL",
    "UPSTREAM_REPO",
    "UPSTREAM_BRANCH",
    "UPDATE_PKGS",
]
auth_chats = {}
sudo_users = []

class CpuEaterLock:
    def __init__(self, limit=1):
        self._limit = limit
        self._semaphore = Semaphore(limit)
        self._acquired_sems = ContextVar("acquired_sems", default=[])

    async def acquire(self):
        sem = self._semaphore
        await sem.acquire()
        sems = self._acquired_sems.get().copy()
        sems.append(sem)
        self._acquired_sems.set(sems)

    def release(self):
        sems = self._acquired_sems.get().copy()
        if sems:
            sem = sems.pop()
            sem.release()
            self._acquired_sems.set(sems)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def update_limit(self, new_limit):
        if not isinstance(new_limit, int) or new_limit < 1:
            new_limit = 1
        if new_limit != self._limit:
            self._limit = new_limit
            self._semaphore = Semaphore(new_limit)

    @property
    def locked(self):
        return self._semaphore.locked()

cpu_eater_lock = CpuEaterLock()
scheduler = AsyncIOScheduler(event_loop=bot_loop)
