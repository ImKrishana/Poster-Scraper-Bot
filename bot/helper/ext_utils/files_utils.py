from asyncio.subprocess import create_subprocess_exec
from aiofiles.os import makedirs as aiomakedirs
from psutil import disk_usage

from ... import DOWNLOAD_DIR, LOGGER
from .bot_utils import sync_to_async

async def clean_all():
    LOGGER.info("Cleaning Download Directory")
    await (await create_subprocess_exec("rm", "-rf", DOWNLOAD_DIR)).wait()
    await aiomakedirs(DOWNLOAD_DIR, exist_ok=True)

async def check_storage_threshold(size, threshold, io_task=False, alloc=False):
    free = (await sync_to_async(disk_usage, DOWNLOAD_DIR)).free
    return free >= (threshold + (size * (2 if io_task else 1) if not alloc else 0))
