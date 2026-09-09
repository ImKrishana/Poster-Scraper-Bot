from importlib import import_module

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from pymongo.server_api import ServerApi

from ... import LOGGER, user_data
from ...core.config_manager import Config
from ...core.tg_client import TgClient


class DbManager:
    def __init__(self):
        self._return = True
        self._conn = None
        self.db = None

    async def connect(self):
        try:
            if self._conn is not None:
                await self._conn.close()
            self._conn = AsyncMongoClient(
                Config.DATABASE_URL, server_api=ServerApi("1")
            )
            self.db = self._conn.flashmirror
            self._return = False
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self.db = None
            self._return = True
            self._conn = None

    async def disconnect(self):
        self._return = True
        if self._conn is not None:
            await self._conn.close()
        self._conn = None

    async def update_deploy_config(self):
        if self._return:
            return
        settings = import_module("config")
        config_file = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in vars(settings).items()
            if not key.startswith("__")
        }
        await self.db.settings.deployConfig.replace_one(
            {"_id": TgClient.ID}, config_file, upsert=True
        )

    async def update_config(self, dict_):
        if self._return:
            return
        await self.db.settings.config.update_one(
            {"_id": TgClient.ID}, {"$set": dict_}, upsert=True
        )

    async def update_private_file(self, path):
        if self._return:
            return
        db_path = path.replace(".", "__")
        if await aiopath.exists(path):
            async with aiopen(path, "rb+") as pf:
                pf_bin = await pf.read()
            await self.db.settings.files.update_one(
                {"_id": TgClient.ID}, {"$set": {db_path: pf_bin}}, upsert=True
            )
            if path == "config.py":
                await self.update_deploy_config()
        else:
            await self.db.settings.files.update_one(
                {"_id": TgClient.ID}, {"$unset": {db_path: ""}}, upsert=True
            )

    async def update_user_data(self, user_id):
        if self._return:
            return
        data = user_data.get(user_id, {})
        data = data.copy()
    
        await self.db.users[TgClient.ID].update_one({"_id": user_id}, {"$set": data}, upsert=True)

    async def update_user_doc(self, user_id, key, path=""):
        if self._return:
            return
        if path:
            async with aiopen(path, "rb+") as doc:
                doc_bin = await doc.read()
            await self.db.users[TgClient.ID].update_one(
                {"_id": user_id}, {"$set": {key: doc_bin}}, upsert=True
            )
        else:
            await self.db.users[TgClient.ID].update_one(
                {"_id": user_id}, {"$unset": {key: ""}}, upsert=True
            )

    async def get_pm_uids(self):
        if self._return:
            return
        return [doc["_id"] async for doc in self.db.pm_users[TgClient.ID].find({})]

    async def set_pm_users(self, user_id):
        if self._return:
            return
        if not bool(await self.db.pm_users[TgClient.ID].find_one({"_id": user_id})):
            await self.db.pm_users[TgClient.ID].insert_one({"_id": user_id})
            LOGGER.info(f"New PM User Added : {user_id}")

    async def rm_pm_user(self, user_id):
        if self._return:
            return
        await self.db.pm_users[TgClient.ID].delete_one({"_id": user_id})

    async def trunc_table(self, name):
        if self._return:
            return
        await self.db[name][TgClient.ID].drop()


database = DbManager()
