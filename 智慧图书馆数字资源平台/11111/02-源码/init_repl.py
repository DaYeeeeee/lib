# -*- coding: utf-8 -*-
"""副本集初始化脚本：读取 config.json 中的成员列表，自动初始化副本集。
使用方法：三个 mongod 都已用同一 --replSet / 同一 keyFile 启动后，执行 python init_repl.py。"""
import json
import os
from pymongo import MongoClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    members_str = os.environ.get("MONGODB_REPL_MEMBERS") or ""
    if members_str:
        cfg["repl_members"] = [m.strip() for m in members_str.split(",") if m.strip()]
    cfg["repl_set"] = os.environ.get("MONGODB_REPL_SET") or cfg.get("repl_set", "rs0")
    return cfg


def main():
    cfg = load_config()
    members = cfg["repl_members"]
    repl_set = cfg["repl_set"]
    standalone_uri = os.environ.get("MONGODB_STANDALONE_URI") or cfg.get(
        "standalone_uri", "mongodb://127.0.0.1:27017/?directConnection=true"
    )

    print(f"副本集名: {repl_set}")
    print(f"成员列表: {members}")
    print(f"连接: {standalone_uri}\n")

    client = MongoClient(standalone_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print(f"[错误] 无法连接 {standalone_uri}: {e}")
        return

    try:
        status = client.admin.command("replSetGetStatus")
        print("副本集已初始化，当前角色：")
        for m in status.get("members", []):
            print(f"  {m['name']} -> {m.get('stateStr', '?')}")
        return
    except Exception:
        print("副本集未初始化，正在初始化...")

    config = {
        "_id": repl_set,
        "members": [],
    }
    for i, addr in enumerate(members):
        config["members"].append({
            "_id": i,
            "host": addr,
            "priority": 2 if i == 0 else 1,
        })

    try:
        result = client.admin.command("replSetInitiate", config)
        print(f"✅ 副本集初始化成功：{result.get('ok')}")
    except Exception as e:
        print(f"[错误] 初始化失败：{e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()