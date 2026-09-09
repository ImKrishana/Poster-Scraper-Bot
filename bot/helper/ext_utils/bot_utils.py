from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    run_coroutine_threadsafe,
    sleep,
)
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps

from httpx import AsyncClient

from ... import bot_loop, user_data
from ...core.config_manager import Config
from ..telegram_helper.button_build import ButtonMaker
from .telegraph_helper import telegraph
from .help_messages import BASIC_HELP_DICT

COMMAND_USAGE = {}

THREAD_POOL = ThreadPoolExecutor(max_workers=500)


class SetInterval:
    def __init__(self, interval, action, *args, **kwargs):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self._set_interval(*args, **kwargs))

    async def _set_interval(self, *args, **kwargs):
        while True:
            await sleep(self.interval)
            await self.action(*args, **kwargs)

    def cancel(self):
        self.task.cancel()


def _build_command_usage(help_dict, command_key):
    buttons = ButtonMaker()
    cmd_list = list(help_dict.keys())[1:]
    temp_store = []
    cmd_pages = [cmd_list[i : i + 10] for i in range(0, len(cmd_list), 10)]
    for i in range(1, len(cmd_pages) + 1):
        for name in cmd_pages[i]:
            buttons.data_button(name, f"help {command_key} {name}")
        buttons.data_button("Prev", f"help pre {command_key} {i - 1}")
        buttons.data_button("Next", f"help nex {command_key} {i + 1}")
        buttons.data_button("Close", "help close", "footer")
        temp_store.append(buttons.build_menu(2))
    COMMAND_USAGE[command_key] = [help_dict["main"], *temp_store]
    buttons.reset()


def _build_command_usage(help_dict, command_key):
    buttons = ButtonMaker()
    cmd_list = list(help_dict.keys())[1:]
    cmd_pages = [cmd_list[i : i + 10] for i in range(0, len(cmd_list), 10)]
    temp_store = []

    for i, page in enumerate(cmd_pages):
        for name in page:
            buttons.data_button(name, f"help {command_key} {name} {i}")
        if len(cmd_pages) > 1:
            if i > 0:
                buttons.data_button("⫷", f"help pre {command_key} {i - 1}")
            if i < len(cmd_pages) - 1:
                buttons.data_button("⫸", f"help nex {command_key} {i + 1}")
        buttons.data_button("Close", "help close", "footer")
        temp_store.append(buttons.build_menu(2))
        buttons.reset()

    COMMAND_USAGE[command_key] = [help_dict["main"], *temp_store]


def create_help_buttons():
    _build_command_usage(BASIC_HELP_DICT, "basic")
    # Add more accordingly 

def compare_versions(v1, v2):
    v1, v2 = (list(map(int, v.split("-")[0][1:].split("."))) for v in (v1, v2))
    return (
        "New Version Update is Available! Check Now!"
        if v1 < v2
        else (
            "More Updated! Kindly Contribute in Official"
            if v1 > v2
            else "Already up to date with latest version"
        )
    )


async def get_telegraph_list(telegraph_content):
    path = [
        (
            await telegraph.create_page(
                title="Mirror-Leech-Bot Drive Search", content=content
            )
        )["path"]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await telegraph.edit_telegraph(path, telegraph_content)
    buttons = ButtonMaker()
    buttons.url_button("🔎 VIEW", f"https://telegra.ph/{path[0]}")
    return buttons.build_menu(1)

def update_user_ldata(id_, key, value):
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    try:
        stdout = stdout.decode().strip()
    except Exception:
        stdout = "Unable to decode the response!"
    try:
        stderr = stderr.decode().strip()
    except Exception:
        stderr = "Unable to decode the error!"
    return stdout, stderr, proc.returncode


def new_task(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        task = bot_loop.create_task(func(*args, **kwargs))
        return task

    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREAD_POOL, pfunc)
    return await future if wait else future


def async_to_sync(func, *args, wait=True, **kwargs):
    future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
    return future.result() if wait else future


def loop_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future

    return wrapper


def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
