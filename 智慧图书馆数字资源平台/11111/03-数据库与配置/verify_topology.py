# -*- coding: utf-8 -*-
"""拓扑核验脚本：一条命令检查副本集、分片集群的全部 TCP 端口监听状态、节点角色与数据分布。
使用方式：在 03-数据库与配置 目录下执行 python verify_topology.py。
依赖：pymongo。"""

import json
import os
import socket
import sys

# 源码目录（config.json 所在位置）
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "02-源码")
CONFIG_PATH = os.path.join(SRC_DIR, "config.json")


def load_cfg():
    if not os.path.exists(CONFIG_PATH):
        print(f"[错误] 找不到 {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def check_port(port):
    """检查本机 TCP 端口是否在监听。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    return result == 0


def main():
    cfg = load_cfg()
    from pymongo import MongoClient

    # ── 一、端口监听检查 ──
    ports = {
        27017: "副本集节点 1",
        27018: "副本集节点 2",
        27019: "副本集节点 3",
        27200: "配置服务器 (config)",
        27301: "分片 shard1",
        27302: "分片 shard2",
        27300: "mongos 路由",
    }
    print("=" * 60)
    print("一、端口监听检查")
    print("-" * 60)
    ok_count = 0
    for port, label in sorted(ports.items()):
        alive = check_port(port)
        status = "监听中" if alive else "未监听"
        print(f"  端口 {port:<6} {label:<22} {status}")
        if alive:
            ok_count += 1
    print(f"  合计：{ok_count} / {len(ports)} 个端口在监听")

    # ── 二、副本集检查 ──
    print()
    print("=" * 60)
    print("二、副本集 rs0：成员、角色与优先级")
    print("-" * 60)
    admin_uri = os.environ.get("MONGODB_ADMIN_URI") or cfg.get("admin_uri")
    if not admin_uri or "CHANGE_ME" in admin_uri:
        print("[跳过] admin_uri 未配置或密码为占位符，请先创建管理员账号。")
    else:
        try:
            client = MongoClient(admin_uri, serverSelectionTimeoutMS=5000)
            status = client.admin.command("replSetGetStatus")
            print(f"  集合名：{status.get('set', '?')}  成员数：{len(status.get('members', []))}")
            for m in status.get("members", []):
                print(f"    {m['name']:<22} {m.get('stateStr', '?'):<12} health={m.get('health', 0)}")
            priorities = {m['name']: m.get('config', {}).get('priority', 1)
                          for m in status.get('members', [])}
            print(f"  优先级：{', '.join(f'{k}={v}' for k, v in priorities.items())}")
            primaries = [m['name'] for m in status.get('members', [])
                         if m.get('stateStr') == 'PRIMARY']
            print(f"  结论：{sum(1 for m in status.get('members', []) if m.get('stateStr')=='SECONDARY')} 从 "
                  f"1 主，主节点 {primaries[0] if primaries else '?'}")
            client.close()
        except Exception as e:
            print(f"[副本集检查失败] {e}")

    # ── 三、分片集群检查 ──
    print()
    print("=" * 60)
    print("三、分片集群：分片清单与数据分布")
    print("-" * 60)
    shard_admin_uri = os.environ.get("MONGODB_SHARD_ADMIN_URI") or cfg.get("shard_admin_uri")
    if not shard_admin_uri or "CHANGE_ME" in shard_admin_uri:
        print("[跳过] shard_admin_uri 未配置或密码为占位符。")
    else:
        try:
            client = MongoClient(shard_admin_uri, serverSelectionTimeoutMS=5000)
            shards = list(client.admin.command("listShards").get("shards", []))
            print(f"  分片数：{len(shards)}")
            for s in shards:
                print(f"    分片 {s.get('_id', '?')}   {s.get('host', '?')}   state={s.get('state', '?')}")

            db_name = cfg.get("db", "smart_library")
            coll_name = "borrow_logs"
            try:
                stats = client[db_name].command("collStats", coll_name)
                shard_stats = stats.get("shards", {})
                total = sum(s.get("count", 0) for s in shard_stats.values())
                print(f"  {db_name}.{coll_name} 共 {total} 条，分布：")
                for sname, sinfo in shard_stats.items():
                    pct = sinfo.get("count", 0) / total * 100 if total else 0
                    print(f"    {sname}  {sinfo.get('count', 0)} 条 ({pct:.1f}%)")
                print(f"  结论：{'两个分片都有数据（分片键生效）' if len(shard_stats) >= 2 else '分片数量不足'}")
            except Exception as e:
                print(f"[集合统计失败] {e}")
            client.close()
        except Exception as e:
            print(f"[分片集群检查失败] {e}")

    print()
    print("=" * 60)
    print("核验完成。")


if __name__ == "__main__":
    main()