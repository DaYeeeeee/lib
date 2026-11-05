# -*- coding: utf-8 -*-
"""副本集故障转移测试脚本。
使用方法：先运行本脚本，按提示手动停止主节点进程，脚本自动计时到新主接管。"""
import os
import time
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConnectionFailure

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def main():
    import json
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    uri = os.environ.get("MONGODB_URI") or cfg.get("uri")
    admin_uri = os.environ.get("MONGODB_ADMIN_URI") or cfg.get("admin_uri")

    client = MongoClient(uri if "CHANGE_ME" not in uri else admin_uri,
                         serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print(f"[错误] 无法连接: {e}")
        return

    # 获取当前主节点
    status = client.admin.command("replSetGetStatus")
    primary = None
    for m in status.get("members", []):
        if m.get("stateStr") == "PRIMARY":
            primary = m["name"]
            break

    if not primary:
        print("[错误] 未找到主节点。")
        return

    print(f"当前主节点: {primary}")
    print(f"当前成员:")
    for m in status.get("members", []):
        print(f"  {m['name']} -> {m.get('stateStr', '?')}")
    print()
    print(f"⚠️  请手动停止主节点进程 {primary}")
    print("   然后按 Enter 继续...")
    input()

    print("\n正在等待新主选出...")
    start = time.time()
    attempts = 0
    new_primary = None

    while time.time() - start < 60:
        attempts += 1
        try:
            client = MongoClient(uri if "CHANGE_ME" not in uri else admin_uri,
                                 serverSelectionTimeoutMS=2000)
            s = client.admin.command("replSetGetStatus")
            for m in s.get("members", []):
                if m.get("stateStr") == "PRIMARY":
                    new_primary = m["name"]
                    break
            if new_primary and new_primary != primary:
                break
        except (AutoReconnect, ConnectionFailure):
            pass
        except Exception:
            pass
        time.sleep(0.5)

    elapsed = time.time() - start
    if new_primary:
        print(f"\n✅ 故障转移完成！")
        print(f"   新主节点: {new_primary}")
        print(f"   耗时: {elapsed:.1f} 秒")
        print(f"   重试次数: {attempts}")
        print(f"\n重启原主节点 {primary} 后，它将作为 SECONDARY 重新加入。")
    else:
        print(f"\n❌ 60秒内未选出新主。")
    client.close()


if __name__ == "__main__":
    main()