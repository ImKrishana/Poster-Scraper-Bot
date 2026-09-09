from importlib import import_module
from os import getenv


class Config:
    AUTHORIZED_CHATS = ""
    AUTHOR_NAME = "TheZake"
    AUTHOR_URL = "https://t.me/TheZake"
    BOT_TOKEN = ""
    BASE_URL = ""
    BASE_URL_PORT = 80
    CMD_SUFFIX = ""
    CONCURRENT_CPU_TASKS = 1
    DATABASE_URL = ""
    DEFAULT_LANG = "en"
    HELPER_TOKENS = ""
    HYBRID_LEECH = True
    LEECH_SPLIT_SIZE = 2097152000
    OWNER_ID = 0
    POSTER_API_URL = "https://thezakeapi.vercel.app"
    POSTER_API_TOKEN = "thezake"
    PROTECTED_API = ""
    PUBLIC_MODE = True 
    SUDO_USERS = ""
    SET_COMMANDS = True
    TELEGRAM_API = 0
    TELEGRAM_HASH = ""
    TG_PROXY = None
    TIMEZONE = "Asia/Kolkata"
    UPSTREAM_REPO = "https://github.com/ImKrishana/Poster-Scraper-Bot"
    UPSTREAM_BRANCH = "main"
    UPDATE_PKGS = True
    USER_SESSION_STRING = ""
    USER_TRANSMISSION = False 
    VERIFY_TIMEOUT = 0

    @classmethod
    def get(cls, key):
        return getattr(cls, key) if hasattr(cls, key) else None

    @classmethod
    def set(cls, key, value):
        if hasattr(cls, key):
            value = cls._convert_env_type(key, value)
            setattr(cls, key, value)
        else:
            raise KeyError(f"{key} is not a valid configuration key.")

    @classmethod
    def get_all(cls):
        return {
            key: getattr(cls, key)
            for key in cls.__dict__.keys()
            if not key.startswith("__") and not callable(getattr(cls, key))
        }

    @classmethod
    def load(cls):
        cls.load_config()
        cls.load_env()

    @classmethod
    def load_config(cls):
        try:
            settings = import_module("config")
        except ModuleNotFoundError:
            settings = None

        if settings:
            for attr in dir(settings):
                if hasattr(cls, attr):
                    value = getattr(settings, attr)
                    if not value:
                        continue
                    if isinstance(value, str):
                        value = value.strip()
                    if attr == "DEFAULT_UPLOAD" and value != "gd":
                        value = "rc"
                    elif attr == "BASE_URL":
                        try:
                            if value:
                                value = value.strip("/")
                        except Exception:
                            continue
                    setattr(cls, attr, value)

        for key in ["BOT_TOKEN", "OWNER_ID", "TELEGRAM_API", "TELEGRAM_HASH"]:
            value = getattr(cls, key)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                raise ValueError(f"{key} variable is missing!")

    @classmethod
    def load_env(cls):
        config_vars = cls.get_all()
        for key in config_vars:
            env_value = getenv(key)
            if env_value is not None:
                converted_value = cls._convert_env_type(key, env_value)
                cls.set(key, converted_value)

    @classmethod
    def _convert_env_type(cls, key, value):
        original_value = getattr(cls, key, None)
        if original_value is None:
            return value
        if isinstance(original_value, bool):
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes")
        if isinstance(original_value, int):
            try:
                return int(value)
            except (ValueError, TypeError):
                return original_value
        if isinstance(original_value, float):
            try:
                return float(value)
            except (ValueError, TypeError):
                return original_value
        return value

    @classmethod
    def load_dict(cls, config_dict):
        for key, value in config_dict.items():
            if hasattr(cls, key):
                if key == "DEFAULT_UPLOAD" and value != "gd":
                    value = "rc"
                elif key == "BASE_URL":
                    try:
                        if value:
                            value = value.strip("/")
                    except Exception:
                        continue
                value = cls._convert_env_type(key, value)
                setattr(cls, key, value)

        for key in ["BOT_TOKEN", "OWNER_ID", "TELEGRAM_API", "TELEGRAM_HASH"]:
            value = getattr(cls, key)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                raise ValueError(f"{key} variable is missing!")

class BinConfig:
    FFMPEG_NAME = "flash"
