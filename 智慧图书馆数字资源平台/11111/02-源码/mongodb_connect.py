# -*- coding: utf-8 -*-
"""统一连接模块：连接串与库名从 config.json 读取，支持环境变量覆盖。"""
import json
import os
import re

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import gridfs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULTS = {"db": "smart_library"}


def _mask(uri):
    """输出时隐藏密码"""
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\\1:***@", uri)


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update({k: v for k, v in json.load(f).items() if not k.startswith("_")})

    # 环境变量覆盖
    cfg["uri"] = os.environ.get("MONGODB_URI") or cfg.get("uri")
    cfg["db"] = os.environ.get("MONGODB_DB") or cfg.get("db") or "smart_library"
    cfg["admin_uri"] = os.environ.get("MONGODB_ADMIN_URI") or cfg.get("admin_uri")
    cfg["standalone_uri"] = os.environ.get("MONGODB_STANDALONE_URI") or cfg.get("standalone_uri")
    cfg["shard_uri"] = os.environ.get("MONGODB_SHARD_URI") or cfg.get("shard_uri")
    cfg["shard_admin_uri"] = os.environ.get("MONGODB_SHARD_ADMIN_URI") or cfg.get("shard_admin_uri")

    if not cfg["uri"]:
        raise RuntimeError("未找到连接串：请在 config.json 中配置 uri，或设置环境变量 MONGODB_URI")

    if "CHANGE_ME" in (cfg["uri"] or ""):
        # 开发 / 单机演示模式：尚未配置认证，优先使用 standalone_uri
        if cfg["standalone_uri"] and "CHANGE_ME" not in cfg["standalone_uri"]:
            print("[提示] 检测到 config.json 中密码为占位符 CHANGE_ME。")
            print(f"       单机模式下将使用 standalone_uri: {_mask(cfg['standalone_uri'])}")
            cfg["uri"] = cfg["standalone_uri"]
        else:
            print("[提示] config.json 中的密码仍是占位符 CHANGE_ME。")
            print("       请按 03-数据库与配置/启动与部署说明.md 第 2 节创建账号，")
            print("       再把 config.json 里连接串的 CHANGE_ME 替换成实际密码。")
            raise SystemExit(2)

    return cfg


CONFIG = load_config()
MONGO_URI = CONFIG["uri"]
MONGO_DB = CONFIG["db"]

_client = None


def get_client():
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            _client.admin.command("ping")
        except ConnectionFailure as e:
            print("[错误] 无法连接 MongoDB，请确认服务已启动、config.json 配置正确：%s" % e)
            raise
    return _client


def get_db():
    return get_client()[MONGO_DB]


def get_collection(name):
    return get_db()[name]


def get_fs():
    return gridfs.GridFS(get_db())


def close_client():
    global _client
    if _client is not None:
        _client.close()
        _client = None


def print_connection_status():
    db = get_db()
    print("=" * 55)
    print("MongoDB 连接状态：已连接 %s" % _mask(MONGO_URI))
    print("当前数据库：%s" % MONGO_DB)
    print("-" * 55)
    for name in sorted(db.list_collection_names()):
        try:
            if name.startswith("fs."):
                continue
            print("  集合 %-20s 文档数：%d" % (name, db[name].count_documents({})))
        except Exception as e:
            print("  集合 %-20s 读取失败：%s" % (name, e))
    print("=" * 55)